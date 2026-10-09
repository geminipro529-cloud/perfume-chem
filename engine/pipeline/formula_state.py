"""Canonical formula state used by the gate-first pipeline.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every perceptibility claim must be backed by OAV. No exceptions.

The important invariant is that raw dose and active dose are both preserved.
Older scoring paths sometimes renormalize dilution-adjusted materials back to
the raw total.  That is useful for some style heuristics but dangerous for
physics.  FormulaState keeps the physical chain explicit:

raw uL -> active uL -> mass -> moles -> mole fraction -> headspace ppm -> OAV.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Mapping, Sequence

from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.ingredient_intelligence import MaterialProfile
from engine.material_resolver import (
    resolve_material,
    resolved_logp,
    resolved_mw_g_mol,
    resolved_vp_25c_pa,
)
from engine.mixer.prebonding import get_functional_groups
from engine.odor_thresholds import lookup_odt_entry, verify_odt
from engine.perception.oav import oav, perceived_intensity_stevens
from engine.pipeline.natural_absolute_decomposition import (
    NaturalCompositeHeadspace,
    NaturalCompositeMetadata,
    composite_headspace,
    composite_replacement_moles,
    get_composite_metadata,
)
from engine.science_data import get_science_profile
from engine.thermo.activity import gamma, mixture_hsp
from engine.thermo.antoine import (
    DEFAULT_DHVAP_ESTIMATE_KJ_MOL,
    VP25_DHVAP_CORRELATION_SOURCE,
    VP_REFERENCE_T_K,
    estimate_dhvap_from_vp_25c,
    vp_pa,
)
from engine.uncertainty import (
    FieldUncertainty,
    FormulaUncertainty,
    combine_uncertainties,
    field_uncertainty,
)

P_ATM_PA = 101_325.0
DEFAULT_DENSITY_G_ML = 1.0
DEFAULT_MW_G_MOL = 200.0
DEFAULT_TEMPERATURE_K = 305.0


OPAQUE_PREBLEND_TOKENS = (
    " ftec",
    " f-tec",
    " fleuressence",
    " fragrance oil",
    " fo",
    " accord",
    " base",
    " core",
    " reconstitution",
)

NATURAL_MIXTURE_TOKENS = (
    " eo",
    " essential oil",
    " oil",
    " absolute",
    " resinoid",
    " balsam",
    " extract",
    " co2",
    " tincture",
)


def _authoritative_active_mass(
    *,
    raw_ul: float,
    dilution: float,
    modeled_active_g: float,
    density_source: str,
    fraction_basis: str,
    declared: bool,
) -> tuple[float | None, str]:
    if not declared:
        return None, "unavailable:stock_fraction_not_declared"
    if fraction_basis == "mass_per_volume":
        # x% w/v means x g per 100 mL, numerically fraction g per mL.
        return raw_ul / 1000.0 * dilution, "exact:declared_w_v"
    if fraction_basis in {"neat", "volume_fraction"}:
        if density_source == "fallback:default_1_g_ml":
            return None, "unavailable:material_density"
        return modeled_active_g, "exact:declared_volume_and_density"
    if fraction_basis == "mass_fraction":
        return None, "unavailable:stock_solution_density_for_w_w"
    return None, "unavailable:stock_fraction_basis_unspecified"


def _physics_projection_authority(
    *,
    formula_mass_chain_complete: bool,
    formula_mw_chain_complete: bool,
    vp_available: bool,
    odt_available: bool,
    composite_available: bool,
    composite_canonical_complete: bool,
    requires_composite: bool,
    gamma_source: str,
    screening_partial_pressure_pa: float | None,
    screening_vapor_ppm: float | None,
    screening_oav: float | None,
    screening_intensity: float | None,
) -> dict[str, object]:
    """Separate diagnostic sensitivity values from input-complete model values.

    The current headspace model remains heuristic even when every input is
    present.  ``canonical_*`` here therefore means an input-complete modeled
    result, never a measured sensory or release-authoritative endpoint.
    """

    headspace_blockers: list[str] = []
    if not formula_mass_chain_complete:
        headspace_blockers.append("ACTIVE_MASS_CHAIN_INCOMPLETE")
    if not formula_mw_chain_complete:
        headspace_blockers.append("MOLECULAR_WEIGHT_CHAIN_INCOMPLETE")
    if requires_composite and not composite_available:
        headspace_blockers.append("NATURAL_COMPOSITE_UNAVAILABLE")
    if composite_available and not composite_canonical_complete:
        # A characterized constituent subtotal remains useful as a screening
        # sensitivity result, but unresolved material and non-batch-specific
        # literature profiles cannot become a complete whole-natural result.
        headspace_blockers.append("NATURAL_COMPOSITE_PARTIAL")
    if not vp_available and not composite_available:
        headspace_blockers.append("VAPOR_PRESSURE_UNAVAILABLE")
    if gamma_source.startswith("fallback:") and not composite_available:
        headspace_blockers.append("ACTIVITY_COEFFICIENT_FALLBACK")

    oav_blockers = list(headspace_blockers)
    if not odt_available and not composite_available:
        oav_blockers.append("COMPATIBLE_AIR_ODT_UNAVAILABLE")

    if screening_vapor_ppm is None:
        status = "WITHHELD"
    elif headspace_blockers or oav_blockers:
        status = "SCREENING_SENSITIVITY_ONLY"
    else:
        status = "MODELED_INPUT_COMPLETE"

    return {
        "physics_status": status,
        "physics_blockers": tuple(dict.fromkeys(oav_blockers)),
        "screening_partial_pressure_pa": screening_partial_pressure_pa,
        "screening_vapor_ppm": screening_vapor_ppm,
        "screening_oav": screening_oav,
        "screening_intensity": screening_intensity,
        "canonical_partial_pressure_pa": (
            screening_partial_pressure_pa if not headspace_blockers else None
        ),
        "canonical_vapor_ppm": screening_vapor_ppm if not headspace_blockers else None,
        "canonical_oav": screening_oav if not oav_blockers else None,
        "canonical_intensity": screening_intensity if not oav_blockers else None,
    }


@dataclass(frozen=True, slots=True)
class MaterialState:
    name: str
    canonical_name: str
    raw_ul: float
    dilution: float
    active_ul: float
    density_g_ml: float
    density_source: str
    active_g: float
    authoritative_active_g: float | None
    active_mass_authority: str
    stock_fraction_basis: str
    stock_carrier: str
    stock_declared: bool
    active_concentrate_ppm_w_w: float | None
    mw_g_mol: float | None
    moles: float
    mole_fraction: float
    logp: float | None
    vp_pure_pa: float | None
    vp_temperature_factor: float | None
    gamma: float
    gamma_source: str
    partial_pressure_pa: float
    vapor_ppm: float
    odt_air_ppm: float | None
    oav: float | None
    intensity: float | None
    family: str | None
    note: str
    role: str
    texture: str
    profile_name: str | None
    registry_name: str | None
    ifra_limit_pct: float | None
    is_known: bool
    is_opaque_preblend: bool
    functional_groups: tuple[str, ...] = ()
    hsp: tuple[float, float, float] | None = None
    hsp_source: str = "missing"
    sources: dict[str, str] = field(default_factory=dict)
    missing_fields: tuple[str, ...] = ()
    active_finished_product_ppm_w_w: float | None = None
    natural_composite_metadata: dict[str, object] = field(default_factory=dict)
    physics_status: str = "SCREENING_SENSITIVITY_ONLY"
    physics_blockers: tuple[str, ...] = ()
    screening_partial_pressure_pa: float | None = None
    screening_vapor_ppm: float | None = None
    screening_oav: float | None = None
    screening_intensity: float | None = None
    canonical_partial_pressure_pa: float | None = None
    canonical_vapor_ppm: float | None = None
    canonical_oav: float | None = None
    canonical_intensity: float | None = None
    formula_optimization_authority: bool = field(default=False, init=False)

    @property
    def has_constituent_resolved_oav(self) -> bool:
        """Whether an actual constituent model, rather than bulk proxy data, produced OAV."""

        return (
            self.sources.get("oav_model") == "modeled:natural_constituent_composite"
            and bool(self.natural_composite_metadata)
            and self.oav is not None
        )

    @property
    def has_odt_authority(self) -> bool:
        """True for a bulk ODT or a constituent-resolved natural ODT model."""

        return self.odt_air_ppm is not None or (
            self.has_constituent_resolved_oav
            and self.sources.get("odt") == "modeled:natural_composite_constituent_odt"
        )

    @property
    def has_vp_authority(self) -> bool:
        """True for bulk VP or constituent-resolved natural headspace physics."""

        return (
            self.vp_pure_pa is not None and self.vp_pure_pa > 0.0
        ) or (
            self.has_constituent_resolved_oav
            and self.sources.get("vp") == "literature:natural_composite_constituent_vp"
        )

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "canonical_name": self.canonical_name,
            "raw_ul": round(self.raw_ul, 4),
            "dilution": self.dilution,
            "active_ul": round(self.active_ul, 4),
            "density_g_ml": self.density_g_ml,
            "density_source": self.density_source,
            "active_g": round(self.active_g, 8),
            "active_g_role": (
                "AUTHORITATIVE"
                if self.authoritative_active_g is not None
                else "MODELED_SENSITIVITY_PROXY"
            ),
            "authoritative_active_g": self.authoritative_active_g,
            "active_mass_authority": self.active_mass_authority,
            "stock_fraction_basis": self.stock_fraction_basis,
            "stock_carrier": self.stock_carrier,
            "stock_declared": self.stock_declared,
            "active_concentrate_ppm_w_w": self.active_concentrate_ppm_w_w,
            "active_finished_product_ppm_w_w": self.active_finished_product_ppm_w_w,
            "mw_g_mol": self.mw_g_mol,
            "moles": self.moles,
            "mole_fraction": self.mole_fraction,
            "logp": self.logp,
            "vp_pure_pa": self.vp_pure_pa,
            "vp_temperature_factor": self.vp_temperature_factor,
            "gamma": self.gamma,
            "gamma_source": self.gamma_source,
            "partial_pressure_pa": self.screening_partial_pressure_pa,
            "vapor_ppm": self.screening_vapor_ppm,
            "odt_air_ppm": self.odt_air_ppm,
            "oav": self.screening_oav,
            "intensity": self.screening_intensity,
            "physics_status": self.physics_status,
            "physics_blockers": list(self.physics_blockers),
            "screening_partial_pressure_pa": self.screening_partial_pressure_pa,
            "screening_vapor_ppm": self.screening_vapor_ppm,
            "screening_oav": self.screening_oav,
            "screening_intensity": self.screening_intensity,
            "canonical_partial_pressure_pa": self.canonical_partial_pressure_pa,
            "canonical_vapor_ppm": self.canonical_vapor_ppm,
            "canonical_oav": self.canonical_oav,
            "canonical_intensity": self.canonical_intensity,
            "formula_optimization_authority": self.formula_optimization_authority,
            "family": self.family,
            "note": self.note,
            "role": self.role,
            "texture": self.texture,
            "profile_name": self.profile_name,
            "registry_name": self.registry_name,
            "ifra_limit_pct": self.ifra_limit_pct,
            "is_known": self.is_known,
            "is_opaque_preblend": self.is_opaque_preblend,
            "functional_groups": list(self.functional_groups),
            "hsp": list(self.hsp) if self.hsp is not None else None,
            "hsp_source": self.hsp_source,
            "sources": dict(self.sources),
            "missing_fields": list(self.missing_fields),
            "natural_composite_metadata": dict(self.natural_composite_metadata),
        }


@dataclass(frozen=True, slots=True)
class FormulaState:
    materials: tuple[MaterialState, ...]
    total_raw_ul: float
    total_active_ul: float
    batch_volume_ml: float
    temperature_K: float  # noqa: N815
    context: str
    uncertainty: FormulaUncertainty
    odorant_active_ul: float = 0.0
    matrix_components_moles: tuple[tuple[str, float], ...] = ()
    matrix_mass_g: float = 0.0
    matrix_source: str = "omitted"
    dose_receipt_sha256: str | None = None
    dose_receipt_status: str | None = None

    @property
    def material_count(self) -> int:
        return len(self.materials)

    @property
    def perceptible_materials(self) -> tuple[MaterialState, ...]:
        return tuple(m for m in self.materials if (m.oav or 0.0) >= 1.0)

    @property
    def total_vapor_ppm(self) -> float:
        return sum(m.vapor_ppm for m in self.materials)

    @property
    def screening_total_vapor_ppm(self) -> float | None:
        """Return a total only when every row has a supported screening value."""

        values = [material.screening_vapor_ppm for material in self.materials]
        if not values or any(value is None for value in values):
            return None
        return sum(float(value) for value in values if value is not None)

    @property
    def canonical_total_vapor_ppm(self) -> float | None:
        values = [material.canonical_vapor_ppm for material in self.materials]
        if not values or any(value is None for value in values):
            return None
        return sum(float(value) for value in values if value is not None)

    @property
    def exact_mass_ppm_available(self) -> bool:
        return bool(self.materials) and all(
            material.active_concentrate_ppm_w_w is not None for material in self.materials
        )

    @property
    def exact_finished_product_ppm_available(self) -> bool:
        return bool(self.materials) and all(
            material.active_finished_product_ppm_w_w is not None for material in self.materials
        )

    @property
    def headspace_basis(self) -> str:
        """Describe which liquid composition the modeled headspace represents.

        Headspace OAV is always a model, but a finished-product model with an
        explicit solvent matrix is materially different from the historical
        active-concentrate-only screen.  Keep that distinction machine-readable
        so reports cannot silently imply finished-bottle authority.
        """

        source = self.matrix_source.strip().casefold()
        if source == "explicit":
            return "MODELED_FINISHED_PRODUCT_EXPLICIT_MATRIX"
        if source == "incomplete_stock_carrier":
            return "MODELED_FINISHED_PRODUCT_PARTIAL_MATRIX"
        if self.matrix_moles > 0.0:
            return "MODELED_FINISHED_PRODUCT_MATRIX_PROXY"
        return "MODELED_ACTIVE_CONCENTRATE_SCREEN"

    @property
    def stock_carrier_inclusion(self) -> str:
        diluted = any(material.dilution < 1.0 for material in self.materials)
        if not diluted:
            return "NOT_APPLICABLE"
        if self.matrix_source == "explicit":
            return "EXPLICITLY_INCLUDED"
        return "UNRESOLVED"

    @property
    def quantitative_authority(self) -> dict[str, object]:
        unavailable = [
            material.name for material in self.materials if material.authoritative_active_g is None
        ]
        density_fallbacks = [
            material.name
            for material in self.materials
            if material.density_source == "fallback:default_1_g_ml"
            and material.authoritative_active_g is None
        ]
        physics_blockers = sorted(
            {
                blocker
                for material in self.materials
                for blocker in material.physics_blockers
            }
        )
        physics_statuses = {material.physics_status for material in self.materials}
        if "WITHHELD" in physics_statuses:
            headspace_input_status = "WITHHELD"
        elif "SCREENING_SENSITIVITY_ONLY" in physics_statuses:
            headspace_input_status = "SCREENING_SENSITIVITY_ONLY"
        else:
            headspace_input_status = "MODELED_INPUT_COMPLETE"
        return {
            "active_concentrate_ppm_w_w": (
                "EXACT_INPUT_CHAIN" if self.exact_mass_ppm_available else "UNAVAILABLE"
            ),
            "active_finished_product_ppm_w_w": (
                "EXACT_INPUT_CHAIN" if self.exact_finished_product_ppm_available else "UNAVAILABLE"
            ),
            "headspace_oav": self.headspace_basis,
            "headspace_model_class": "HEURISTIC_NOT_MEASURED",
            "headspace_input_status": headspace_input_status,
            "headspace_input_blockers": physics_blockers,
            "screening_total_vapor_ppm": self.screening_total_vapor_ppm,
            "canonical_total_vapor_ppm": self.canonical_total_vapor_ppm,
            "formula_optimization_authority": False,
            "sensory_endpoint_authority": {
                "character": False,
                "measured_intensity": False,
                "pleasantness": False,
                "liking": False,
            },
            "measured_curve_input_authority": False,
            "modeled_delivery_status": "MODELED_HEADSPACE_NOT_MEASURED_DELIVERY",
            "matrix_source": self.matrix_source,
            "stock_carrier_inclusion": self.stock_carrier_inclusion,
            "unavailable_active_mass_materials": unavailable,
            "density_fallback_materials": density_fallbacks,
        }

    def active_mass_percentages(self) -> dict[str, float] | None:
        if not self.exact_mass_ppm_available:
            return None
        return {
            material.name: float(material.active_concentrate_ppm_w_w or 0.0) / 10_000.0
            for material in self.materials
        }

    @property
    def matrix_moles(self) -> float:
        return sum(moles for _, moles in self.matrix_components_moles)

    def active_percentages(self) -> dict[str, float]:
        total = self.total_active_ul or 1.0
        return {m.name: 100.0 * m.active_ul / total for m in self.materials}

    def raw_percentages(self) -> dict[str, float]:
        total = self.total_raw_ul or 1.0
        return {m.name: 100.0 * m.raw_ul / total for m in self.materials}

    def note_distribution(self) -> dict[str, float]:
        totals = {"top": 0.0, "heart": 0.0, "base": 0.0}
        for m in self.materials:
            note = m.note if m.note in totals else "heart"
            totals[note] += m.active_ul
        denom = sum(totals.values()) or 1.0
        return {k: round(v / denom * 100.0, 1) for k, v in totals.items()}

    @classmethod
    def from_base(
        cls,
        base: FormulaState,
        *,
        new_raw_ul: dict[str, float],
        new_matrix_moles: tuple[tuple[str, float], ...] | None = None,
    ) -> FormulaState:
        """Create a new FormulaState with different raw_ul amounts, reusing constant fields.

        Amount-dependent fields (raw_ul, active_g, moles, mole_fraction,
        gamma, partial_pressure, vapor_ppm, oav, intensity) are recomputed.
        Constant material properties (MW, VP, HSP, ODT, etc.) are copied from
        the base state. This avoids redundant material resolution and property
        lookups without freezing a composition-dependent activity coefficient.

        ``new_matrix_moles`` replaces the matrix component moles (the temporal
        simulator passes the evaporated matrix, diagnosis M1a); omitted, the
        base matrix is kept. ``matrix_mass_g`` stays the declared
        finished-product matrix mass either way.
        """
        materials: list[MaterialState] = []
        total_raw = sum(new_raw_ul.values())
        matrix_components_moles = (
            base.matrix_components_moles
            if new_matrix_moles is None
            else tuple((str(name), float(moles)) for name, moles in new_matrix_moles)
        )
        mole_inputs: dict[str, float] = dict(matrix_components_moles)
        authoritative_masses: dict[str, tuple[float | None, str]] = {}
        composite_rows: list[tuple[str, str, float, float]] = []
        for m in base.materials:
            raw_ul = new_raw_ul.get(m.name, 0.0)
            active_ul = raw_ul * m.dilution
            density = m.density_g_ml
            modeled_active_g = active_ul * density / 1000.0
            mw = float(m.mw_g_mol or DEFAULT_MW_G_MOL)
            authoritative_masses[m.name] = _authoritative_active_mass(
                raw_ul=raw_ul,
                dilution=m.dilution,
                modeled_active_g=modeled_active_g,
                density_source=m.density_source,
                fraction_basis=m.stock_fraction_basis,
                declared=m.stock_declared,
            )
            authoritative_active_g, _authority = authoritative_masses[m.name]
            active_g = (
                float(authoritative_active_g)
                if authoritative_active_g is not None
                else modeled_active_g
            )
            moles = active_g / mw if active_g > 0 else 0.0
            canonical = m.canonical_name
            mole_inputs[canonical] = mole_inputs.get(canonical, 0.0) + moles
            composite_rows.append((canonical, m.name, active_g, moles))

        total_moles = sum(mole_inputs.values())
        composite_replacements = tuple(
            _composite_replacement_moles_for_row(*row) for row in composite_rows
        )
        composite_total_moles = _composite_formula_total_moles_from_replacements(
            total_moles,
            tuple(composite_rows),
            composite_replacements,
        )
        all_active_masses_authoritative = all(
            mass is not None for mass, _authority in authoritative_masses.values()
        )
        formula_mw_chain_complete = all(
            material.mw_g_mol is not None or replacement is not None
            for material, replacement in zip(
                base.materials,
                composite_replacements,
                strict=True,
            )
        )
        total_authoritative_active_g = sum(
            float(mass or 0.0) for mass, _authority in authoritative_masses.values()
        )
        finished_mass_g = total_authoritative_active_g + base.matrix_mass_g
        mole_fractions = {
            name: (moles / total_moles if total_moles > 0 else 0.0)
            for name, moles in mole_inputs.items()
        }
        hsp_table = {m.canonical_name: m.hsp for m in base.materials if m.hsp is not None}
        mixture_hsp_value = mixture_hsp(
            _concentrate_mole_fractions(mole_inputs, matrix_components_moles),
            hsp_table=hsp_table,
        )

        for m in base.materials:
            raw_ul = new_raw_ul.get(m.name, 0.0)
            active_ul = raw_ul * m.dilution
            density = m.density_g_ml
            modeled_active_g = active_ul * density / 1000.0
            authoritative_active_g, active_mass_authority = authoritative_masses[m.name]
            active_g = (
                float(authoritative_active_g)
                if authoritative_active_g is not None
                else modeled_active_g
            )
            mw = float(m.mw_g_mol or DEFAULT_MW_G_MOL)
            moles = active_g / mw if active_g > 0 else 0.0
            x_i = mole_fractions.get(m.canonical_name, 0.0)

            gamma_value = m.gamma
            gamma_source = m.gamma_source
            if gamma_source != "profile:ingredient_intelligence.activity_coef":
                try:
                    gamma_value = gamma(
                        m.canonical_name,
                        mole_fractions,
                        base.temperature_K,
                        hsp_table=hsp_table,
                        mixture_hsp_override=mixture_hsp_value,
                    )
                    gamma_source = "heuristic:hansen_distance"
                except Exception:
                    gamma_value = m.gamma
            partial_pressure = gamma_value * x_i * m.vp_pure_pa if m.vp_pure_pa is not None else 0.0
            vapor_ppm = 1e6 * partial_pressure / P_ATM_PA
            oav_value = (
                oav(vapor_ppm, m.odt_air_ppm)
                if m.vp_pure_pa is not None and m.odt_air_ppm is not None
                else None
            )

            # RULE 1b — Natural Absolute Decomposition:
            # For known natural absolutes, replace the monomolecular OAV
            # with modeled contributions from the available constituent profile.
            # Profile metadata retains incomplete coverage and input authority.
            composite_result, composite_metadata, composite_lookup_name = (
                _lookup_composite_headspace(
                    m.canonical_name,
                    m.name,
                    active_g,
                    composite_total_moles,
                    temperature_K=base.temperature_K,
                )
            )
            requires_composite = m.is_opaque_preblend or _is_natural_mixture(m.name)
            if composite_result is not None:
                partial_pressure = composite_result.partial_pressure_pa
                vapor_ppm = composite_result.vapor_ppm
                oav_value = composite_result.oav
            elif requires_composite:
                # Unsupported naturals and opaque preblends must fail closed.
                # Their bulk MW/VP is not a defensible odor authority proxy.
                oav_value = None
            intensity = (
                perceived_intensity_stevens(oav_value, m.family) if oav_value is not None else None
            )
            screening_headspace_available = composite_result is not None or (
                not requires_composite and m.vp_pure_pa is not None
            )
            projection = _physics_projection_authority(
                formula_mass_chain_complete=all_active_masses_authoritative,
                formula_mw_chain_complete=formula_mw_chain_complete,
                vp_available=m.vp_pure_pa is not None,
                odt_available=m.odt_air_ppm is not None,
                composite_available=composite_result is not None,
                composite_canonical_complete=_composite_supports_canonical_projection(
                    composite_metadata
                ),
                requires_composite=requires_composite,
                gamma_source=gamma_source,
                screening_partial_pressure_pa=(
                    float(partial_pressure) if screening_headspace_available else None
                ),
                screening_vapor_ppm=(
                    float(vapor_ppm) if screening_headspace_available else None
                ),
                screening_oav=oav_value,
                screening_intensity=intensity,
            )

            sources = dict(m.sources)
            sources["oav_model"] = _oav_model_source(
                composite_result,
                requires_composite,
            )
            if composite_metadata is not None:
                sources["mw"] = "literature:natural_composite_constituent_mw"
                sources["vp"] = "literature:natural_composite_constituent_vp"
                sources["gamma"] = "modeled:natural_composite_constituent_gamma"
                sources["odt"] = "modeled:natural_composite_constituent_odt"
                sources["natural_composite"] = (
                    f"{composite_metadata.composition_authority};"
                    f"profile={composite_metadata.profile_key};"
                    f"coverage={composite_metadata.characterized_fraction:.6f};"
                    f"resolution={composite_metadata.resolution};"
                    f"lookup={composite_lookup_name};"
                    "batch_specific=false"
                )
            materials.append(
                # Exact mass-fraction ppm requires every active material density.
                MaterialState(
                    name=m.name,
                    canonical_name=m.canonical_name,
                    raw_ul=raw_ul,
                    dilution=m.dilution,
                    active_ul=active_ul,
                    density_g_ml=density,
                    density_source=m.density_source,
                    active_g=active_g,
                    authoritative_active_g=authoritative_active_g,
                    active_mass_authority=active_mass_authority,
                    stock_fraction_basis=m.stock_fraction_basis,
                    stock_carrier=m.stock_carrier,
                    stock_declared=m.stock_declared,
                    active_concentrate_ppm_w_w=(
                        1e6 * float(authoritative_active_g or 0.0) / total_authoritative_active_g
                        if all_active_masses_authoritative and total_authoritative_active_g > 0
                        else None
                    ),
                    mw_g_mol=m.mw_g_mol,
                    moles=moles,
                    mole_fraction=x_i,
                    logp=m.logp,
                    vp_pure_pa=m.vp_pure_pa,
                    vp_temperature_factor=m.vp_temperature_factor,
                    gamma=gamma_value,
                    gamma_source=gamma_source,
                    partial_pressure_pa=float(partial_pressure),
                    vapor_ppm=float(vapor_ppm),
                    odt_air_ppm=m.odt_air_ppm,
                    oav=oav_value,
                    intensity=intensity,
                    family=m.family,
                    note=m.note,
                    role=m.role,
                    texture=m.texture,
                    profile_name=m.profile_name,
                    registry_name=m.registry_name,
                    ifra_limit_pct=m.ifra_limit_pct,
                    is_known=m.is_known,
                    is_opaque_preblend=m.is_opaque_preblend,
                    functional_groups=m.functional_groups,
                    hsp=m.hsp,
                    hsp_source=m.hsp_source,
                    sources=sources,
                    missing_fields=m.missing_fields,
                    natural_composite_metadata=(
                        composite_metadata.as_dict() if composite_metadata else {}
                    ),
                    active_finished_product_ppm_w_w=(
                        1e6 * float(authoritative_active_g or 0.0) / finished_mass_g
                        if all_active_masses_authoritative
                        and base.matrix_source == "explicit"
                        and finished_mass_g > 0
                        else None
                    ),
                    **projection,
                )
            )

        from engine.units.concentration import classify_material_category

        original_raw_ul = {material.name: material.raw_ul for material in base.materials}
        dose_receipt_unchanged = original_raw_ul == {
            str(name): float(value or 0.0)
            for name, value in new_raw_ul.items()
            if float(value or 0.0) > 0.0
        }
        return cls(
            materials=tuple(materials),
            total_raw_ul=total_raw,
            total_active_ul=sum(m.active_ul for m in materials),
            odorant_active_ul=sum(
                material.active_ul
                for material in materials
                if classify_material_category(material.name) == "odorant"
            ),
            batch_volume_ml=base.batch_volume_ml,
            temperature_K=base.temperature_K,
            context=base.context,
            uncertainty=base.uncertainty,
            matrix_components_moles=matrix_components_moles,
            matrix_mass_g=base.matrix_mass_g,
            matrix_source=base.matrix_source,
            dose_receipt_sha256=base.dose_receipt_sha256,
            dose_receipt_status=(
                base.dose_receipt_status
                if dose_receipt_unchanged
                else "INVALIDATED_BY_RECOMPUTE"
            ),
        )

    def as_dict(self) -> dict:
        return {
            "total_raw_ul": round(self.total_raw_ul, 4),
            "total_active_ul": round(self.total_active_ul, 4),
            "odorant_active_ul": round(self.odorant_active_ul, 4),
            "batch_volume_ml": self.batch_volume_ml,
            "temperature_K": self.temperature_K,
            "context": self.context,
            "matrix_moles": self.matrix_moles,
            "matrix_mass_g": self.matrix_mass_g,
            "matrix_source": self.matrix_source,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "dose_receipt_status": self.dose_receipt_status,
            "headspace_basis": self.headspace_basis,
            "total_vapor_ppm": (
                None
                if self.screening_total_vapor_ppm is None
                else round(self.screening_total_vapor_ppm, 6)
            ),
            "legacy_numeric_total_vapor_ppm": round(self.total_vapor_ppm, 6),
            "quantitative_authority": self.quantitative_authority,
            "note_distribution": self.note_distribution(),
            "uncertainty": {
                "relative_uncertainty": self.uncertainty.relative_uncertainty,
                "confidence_score": self.uncertainty.confidence_score,
                "confidence_grade": self.uncertainty.confidence_grade,
            },
            "materials": [m.as_dict() for m in self.materials],
        }


def _odt_source_label(data: dict) -> str:
    vfy = str(data.get("vfy", "")).upper().strip()
    if not data.get("sources"):
        return "unverified:odor_thresholds.odt_air"
    if vfy == "DERIVED":
        return "derived:odor_thresholds.odt_air"
    if vfy == "UNVERIFIED":
        return "unverified:odor_thresholds.odt_air"
    if vfy == "PEER_EST":
        return "estimated:odor_thresholds.odt_air"
    if vfy in {"PEER_CROSS", "PEER_SINGLE"}:
        return "literature:peer_reviewed.odt_air"
    if vfy == "MULTI_SOURCE_LITERATURE":
        return "literature:odor_thresholds.odt_air"
    return "unverified:odor_thresholds.odt_air"


def odt_lookup_key(name: str, registry_material=None) -> str:
    """Return the ODT_DATA key the release gate uses for a material label."""
    # The resolved registry identity decides the threshold, so two labels that
    # resolve to one material (e.g. "Vertofix" and "Vertofix Coeur (neat)")
    # cannot carry different ODTs. The raw label is the fallback only when that
    # identity has no ODT entry.
    registry_name = getattr(registry_material, "canonical_name", None)
    if registry_name and lookup_odt_entry(registry_name) is not None:
        return registry_name
    return name


def lookup_odt_air_ppb(
    name: str, profile: MaterialProfile | None, registry_material=None
) -> tuple[float | None, str]:
    """Return the air ODT (ppb) the release gate uses, with its source label."""
    odt_key = odt_lookup_key(name, registry_material)
    verification = verify_odt(odt_key)
    data = lookup_odt_entry(odt_key)
    if data is not None:
        odt_air_ppb = data.get("odt_air")
        if odt_air_ppb is not None:
            source_data = verification or data
            return float(odt_air_ppb), _odt_source_label(source_data)
    if (
        registry_material is not None
        and getattr(registry_material, "odt_air_ppb", None) is not None
    ):
        return float(registry_material.odt_air_ppb), "registry:data_spine.odt_air_ppb"
    if profile and profile.odt is not None:
        return float(profile.odt), "profile:ingredient_intelligence.odt"
    return None, "missing"


def _lookup_odt(
    name: str, profile: MaterialProfile | None, registry_material=None
) -> tuple[float | None, str]:
    odt_air_ppb, source = lookup_odt_air_ppb(name, profile, registry_material)
    return (odt_air_ppb / 1000.0 if odt_air_ppb is not None else None), source


def _is_opaque_preblend(name: str, profile: MaterialProfile | None) -> bool:
    # A declared mixture remains opaque even when its trade name lacks "base".
    if profile is not None and profile.material_kind == "OPAQUE_PREBLEND":
        return True
    low = f" {name.lower()} "
    if any(token in low for token in OPAQUE_PREBLEND_TOKENS):
        return True
    if profile and profile.name.lower() != name.lower():
        prof_low = f" {profile.name.lower()} "
        if any(token in prof_low for token in OPAQUE_PREBLEND_TOKENS):
            return True
    return False


def _is_natural_mixture(name: str) -> bool:
    low = f" {name.lower()} "
    return any(token in low for token in NATURAL_MIXTURE_TOKENS)


def _oav_model_source(composite: object | None, requires_composite: bool) -> str:
    if composite is not None:
        return "modeled:natural_constituent_composite"
    if requires_composite:
        return "unknown:composite_decomposition_missing"
    return "heuristic:monomolecular_headspace"


def _lookup_composite_headspace(
    canonical_name: str,
    stock_label: str,
    active_g: float,
    total_moles: float,
    *,
    temperature_K: float,  # noqa: N803
) -> tuple[
    NaturalCompositeHeadspace | None,
    NaturalCompositeMetadata | None,
    str,
]:
    """Resolve natural composites without losing stock-label identity.

    Material canonicalization can intentionally map a stock label to a broader
    profile name (for example Nagarmortha Oil -> Cypriol EO). Composite profiles
    are sometimes batch/extraction-label specific, so both identities must be
    tried before declaring the natural unsupported.
    """

    candidates = tuple(
        dict.fromkeys(value for value in (canonical_name, stock_label) if str(value or "").strip())
    )
    for candidate in candidates:
        metadata = get_composite_metadata(candidate)
        composite = composite_headspace(
            candidate,
            active_g,
            total_moles,
            temperature_K=temperature_K,
        )
        if composite is not None or metadata is not None:
            return composite, metadata, candidate
    return None, None, ""


def _composite_supports_canonical_projection(
    metadata: NaturalCompositeMetadata | None,
) -> bool:
    """Require explicit complete, batch-specific composition authority."""

    if metadata is None:
        return False
    return (
        metadata.batch_specific
        and metadata.quantitative_evaluability == "COMPLETE_INPUT_COVERAGE"
        and metadata.unresolved_fraction <= 1e-9
        and not metadata.unresolved_constituents
        and metadata.composition_authority
        in {"MEASURED_BATCH_SPECIFIC", "MEASURED_WHOLE_PRODUCT"}
    )


def _composite_formula_total_moles(
    total_moles: float,
    material_rows: tuple[tuple[str, str, float, float], ...],
) -> float:
    """Replace every modeled natural parent in one shared formula mole pool."""
    replacements = tuple(
        _composite_replacement_moles_for_row(*row) for row in material_rows
    )
    return _composite_formula_total_moles_from_replacements(
        total_moles,
        material_rows,
        replacements,
    )


def _composite_formula_total_moles_from_replacements(
    total_moles: float,
    material_rows: tuple[tuple[str, str, float, float], ...],
    replacements: tuple[float | None, ...],
) -> float:
    """Apply pre-resolved natural constituent mole replacements once."""

    effective_total = float(total_moles)
    for row, replacement in zip(material_rows, replacements, strict=True):
        parent_moles = row[3]
        if replacement is not None:
            effective_total += replacement - max(0.0, parent_moles)
    return max(0.0, effective_total)


def _composite_replacement_moles_for_row(
    canonical_name: str,
    stock_label: str,
    active_g: float,
    parent_moles: float,
) -> float | None:
    """Return a real constituent mole replacement, never a family proxy."""

    candidates = tuple(
        dict.fromkeys(
            value
            for value in (canonical_name, stock_label)
            if str(value or "").strip()
        )
    )
    for candidate in candidates:
        replacement = composite_replacement_moles(
            candidate,
            active_g,
            parent_moles,
        )
        if replacement is not None:
            return float(replacement)
    return None


def _concentrate_mole_fractions(
    mole_inputs: Mapping[str, float],
    matrix_mole_items: Sequence[tuple[str, float]],
) -> dict[str, float]:
    """Return mole fractions over the concentrate alone, for the activity model.

    Only the few materials with Hansen data get a gamma that follows the
    mixture HSP; every other row keeps a fixed value. Letting the declared or
    default ethanol/water matrix shift the mixture HSP therefore boosted just
    those few (Iso E Super 1.05 -> 5.3 in ethanol) over everything else. The
    matrix still dilutes each x_i and evaporates; it does not enter the HSP.
    """
    matrix: dict[str, float] = {}
    for name, moles in matrix_mole_items:
        matrix[name] = matrix.get(name, 0.0) + float(moles)
    concentrate = {
        name: moles - matrix.get(name, 0.0)
        for name, moles in mole_inputs.items()
        if moles - matrix.get(name, 0.0) > 0.0
    }
    total = sum(concentrate.values())
    if total <= 0.0:
        return {}
    return {name: moles / total for name, moles in concentrate.items()}


def _registry_hsp(material) -> tuple[float, float, float] | None:
    if material is None or material.hsp is None:
        return None
    hsp = material.hsp
    if hsp.delta_d is None or hsp.delta_p is None or hsp.delta_h is None:
        return None
    return (float(hsp.delta_d), float(hsp.delta_p), float(hsp.delta_h))


def _fallback_hsp(
    *candidates: str | None,
) -> tuple[tuple[float, float, float] | None, str]:
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = str(candidate).strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        profile = get_science_profile(key)
        hsp = (profile.hansen_dd, profile.hansen_dp, profile.hansen_dh)
        if all(value is not None for value in hsp):
            return (
                float(hsp[0]),
                float(hsp[1]),
                float(hsp[2]),
            ), "fallback:science_data.hsp"
    return None, "missing"


def _functional_groups(material, *candidates: str | None) -> tuple[str, ...]:
    groups: list[str] = []
    if material is not None:
        for group in getattr(material, "functional_groups", []) or []:
            value = str(group).strip().lower()
            if value and value not in groups:
                groups.append(value)
    for candidate in candidates:
        if not candidate:
            continue
        for group in get_functional_groups(str(candidate)):
            value = str(group).strip().lower()
            if value and value not in groups:
                groups.append(value)
    return tuple(groups)


def _registry_antoine(material) -> tuple[float, float, float] | None:
    if material is None or material.antoine is None:
        return None
    ant = material.antoine
    if ant.A is None or ant.B is None or ant.C is None:
        return None
    return (float(ant.A), float(ant.B), float(ant.C))


def _freeze_mapping(
    mapping: Mapping[str, float] | None, default: float
) -> tuple[tuple[str, float], ...]:
    if not mapping:
        return ()
    return tuple(
        (str(name), float(value if value is not None else default))
        for name, value in sorted(
            mapping.items(),
            key=lambda item: str(item[0]).casefold(),
        )
    )


def _freeze_stock_specs(
    mapping: Mapping[str, Mapping[str, object]] | None,
) -> tuple[tuple[str, str, str, bool, bool], ...]:
    if not mapping:
        return ()
    return tuple(
        (
            str(name),
            str((spec or {}).get("fraction_basis", "unspecified")),
            str((spec or {}).get("carrier", "")),
            bool((spec or {}).get("approximate", False)),
            bool((spec or {}).get("declared", False)),
        )
        for name, spec in sorted(
            mapping.items(),
            key=lambda item: str(item[0]).casefold(),
        )
    )


@lru_cache(maxsize=256)
def _build_formula_state_cached(
    ingredient_items: tuple[tuple[str, float], ...],
    dilution_items: tuple[tuple[str, float], ...],
    stock_spec_items: tuple[tuple[str, str, str, bool, bool], ...],
    batch_volume_ml: float,
    temperature_K: float,  # noqa: N803
    context: str,
    matrix_mole_items: tuple[tuple[str, float], ...],
    matrix_mass_g: float,
    matrix_source: str,
) -> FormulaState:
    """Build a canonical physical state from a raw uL formula table."""
    ingredients_ul = dict(ingredient_items)
    dilutions = dict(dilution_items)
    stock_specs = {
        name: {
            "fraction_basis": fraction_basis,
            "carrier": carrier,
            "approximate": approximate,
            "declared": declared,
        }
        for name, fraction_basis, carrier, approximate, declared in stock_spec_items
    }

    raw_rows = []
    total_moles = sum(moles for _, moles in matrix_mole_items)
    uncertainty_fields: list[FieldUncertainty] = []
    mole_inputs: dict[str, float] = dict(matrix_mole_items)
    hsp_table: dict[str, tuple[float, float, float]] = {}

    for name, raw_amount in ingredients_ul.items():
        raw_ul = max(0.0, float(raw_amount or 0.0))
        dilution = float(dilutions.get(name, 1.0) or 1.0)
        active_ul = raw_ul * dilution
        identity = resolve_material(name)
        profile = identity.profile
        reg_mat = identity.registry_material

        mw, mw_source = resolved_mw_g_mol(identity)
        logp, logp_source = resolved_logp(identity)
        registry_density = getattr(reg_mat, "density_25c_g_ml", None)
        if registry_density is None:
            density = DEFAULT_DENSITY_G_ML
            density_source = "fallback:default_1_g_ml"
        else:
            density = float(registry_density)
            density_source = "registry:data_spine.density_25c"
        modeled_active_g = active_ul * density / 1000.0
        stock_spec = stock_specs.get(name, {})
        stock_fraction_basis = str(stock_spec.get("fraction_basis", "unspecified"))
        stock_carrier = str(stock_spec.get("carrier", ""))
        stock_declared = bool(stock_spec.get("declared", False))
        authoritative_active_g, active_mass_authority = _authoritative_active_mass(
            raw_ul=raw_ul,
            dilution=dilution,
            modeled_active_g=modeled_active_g,
            density_source=density_source,
            fraction_basis=stock_fraction_basis,
            declared=stock_declared,
        )
        active_g = (
            float(authoritative_active_g)
            if authoritative_active_g is not None
            else modeled_active_g
        )
        moles = active_g / float(mw or DEFAULT_MW_G_MOL) if active_g > 0 else 0.0
        canonical = identity.canonical_name
        total_moles += moles
        mole_inputs[canonical] = mole_inputs.get(canonical, 0.0) + moles

        hsp = _registry_hsp(reg_mat)
        hsp_source = "registry:data_spine.hsp" if hsp is not None else "missing"
        if hsp is None:
            hsp, hsp_source = _fallback_hsp(
                identity.registry_name,
                identity.profile_name,
                name,
            )
        if hsp is not None:
            hsp_table[canonical] = hsp
        functional_groups = _functional_groups(
            reg_mat,
            canonical,
            identity.registry_name,
            identity.profile_name,
            name,
        )

        raw_rows.append(
            (
                name,
                raw_ul,
                dilution,
                active_ul,
                active_g,
                authoritative_active_g,
                active_mass_authority,
                stock_fraction_basis,
                stock_carrier,
                stock_declared,
                density,
                density_source,
                moles,
                identity,
                profile,
                reg_mat,
                mw,
                mw_source,
                logp,
                logp_source,
                functional_groups,
                hsp,
                hsp_source,
            )
        )
        uncertainty_fields.extend(
            [
                field_uncertainty(f"{name}.density", density_source),
                field_uncertainty(f"{name}.mw", mw_source if mw is not None else "missing"),
                field_uncertainty(f"{name}.logp", logp_source if logp is not None else "missing"),
            ]
        )

    mole_fractions = {
        name: (moles / total_moles if total_moles > 0 else 0.0)
        for name, moles in mole_inputs.items()
    }
    composite_rows = tuple(
        (
            row[13].canonical_name,
            row[0],
            row[4],
            row[12],
        )
        for row in raw_rows
    )
    composite_replacements = tuple(
        _composite_replacement_moles_for_row(*row) for row in composite_rows
    )
    composite_total_moles = _composite_formula_total_moles_from_replacements(
        total_moles,
        composite_rows,
        composite_replacements,
    )
    all_active_masses_authoritative = all(row[5] is not None for row in raw_rows)
    formula_mw_chain_complete = all(
        row[16] is not None or replacement is not None
        for row, replacement in zip(raw_rows, composite_replacements, strict=True)
    )
    total_authoritative_active_g = sum(float(row[5] or 0.0) for row in raw_rows)
    finished_mass_g = total_authoritative_active_g + matrix_mass_g
    mixture_hsp_value = mixture_hsp(
        _concentrate_mole_fractions(mole_inputs, matrix_mole_items),
        hsp_table=hsp_table,
    )

    materials: list[MaterialState] = []
    for (
        name,
        raw_ul,
        dilution,
        active_ul,
        active_g,
        authoritative_active_g,
        active_mass_authority,
        stock_fraction_basis,
        stock_carrier,
        stock_declared,
        density,
        density_source,
        moles,
        identity,
        profile,
        reg_mat,
        mw,
        mw_source,
        logp,
        logp_source,
        functional_groups,
        hsp,
        hsp_source,
    ) in raw_rows:
        canonical = identity.canonical_name
        x_i = mole_fractions.get(canonical, 0.0)
        ant = _registry_antoine(reg_mat)
        vp_25, vp_source = resolved_vp_25c_pa(identity)
        dhvap = getattr(reg_mat, "dhvap_kj_mol", None)
        vp_temperature_source = "unavailable:no_vp"
        dhvap_source = "unavailable:not_used"
        vp_temperature_factor: float | None = None
        try:
            if ant is not None:
                vp = vp_pa(temperature_K, A=ant[0], B=ant[1], C=ant[2])
                reference_vp = vp_pa(
                    VP_REFERENCE_T_K,
                    A=ant[0],
                    B=ant[1],
                    C=ant[2],
                )
                if reference_vp > 0:
                    vp_temperature_factor = float(vp) / float(reference_vp)
                vp_source = "measured:data_spine.antoine"
                vp_temperature_source = "measured:data_spine.antoine"
                dhvap_source = "not_required:antoine"
            elif vp_25 is not None:
                effective_dhvap = float(dhvap) if dhvap is not None else None
                if effective_dhvap is not None:
                    dhvap_source = "registry:data_spine.dhvap"
                    vp_temperature_source = "literature:clausius_clapeyron"
                elif abs(float(temperature_K) - VP_REFERENCE_T_K) <= 1e-9:
                    dhvap_source = "not_required:vp_25c_reference_temperature"
                    vp_temperature_source = "reference:vp_25c"
                else:
                    try:
                        effective_dhvap = estimate_dhvap_from_vp_25c(float(vp_25))
                        dhvap_source = f"literature_correlation:{VP25_DHVAP_CORRELATION_SOURCE}"
                        vp_temperature_source = (
                            "heuristic:clausius_clapeyron_vp25_dhvap_correlation"
                        )
                    except ValueError:
                        effective_dhvap = DEFAULT_DHVAP_ESTIMATE_KJ_MOL
                        dhvap_source = f"heuristic:shared_{DEFAULT_DHVAP_ESTIMATE_KJ_MOL:g}_kj_mol"
                        vp_temperature_source = "heuristic:clausius_clapeyron_shared_dhvap"
                vp = vp_pa(
                    temperature_K,
                    vp_25c_pa=float(vp_25),
                    dhvap_kj_mol=effective_dhvap,
                )
                if float(vp_25) > 0:
                    vp_temperature_factor = float(vp) / float(vp_25)
            else:
                vp = None
        except Exception:
            vp = None
            vp_temperature_source = "unavailable:temperature_correction_failed"
            dhvap_source = "unavailable:temperature_correction_failed"

        gamma_source = "heuristic:hansen_distance"
        profile_activity_coef = getattr(profile, "activity_coef", None)
        if hsp_source == "missing" and profile_activity_coef is not None:
            gamma_value = float(profile_activity_coef)
            gamma_source = "profile:ingredient_intelligence.activity_coef"
        else:
            try:
                gamma_value = gamma(
                    canonical,
                    mole_fractions,
                    temperature_K,
                    hsp_table=hsp_table,
                    mixture_hsp_override=mixture_hsp_value,
                )
            except Exception:
                gamma_value = 1.0
                gamma_source = "fallback:ideal_gamma"

        partial_pressure = (gamma_value * x_i * vp) if vp is not None else 0.0
        vapor_ppm = 1e6 * partial_pressure / P_ATM_PA
        odt_air_ppm, odt_source = _lookup_odt(name, profile, reg_mat)
        oav_value = oav(vapor_ppm, odt_air_ppm) if vp is not None and odt_air_ppm else None

        # RULE 1b — Natural Absolute Decomposition
        composite_result, composite_metadata, composite_lookup_name = _lookup_composite_headspace(
            canonical,
            name,
            active_g,
            composite_total_moles,
            temperature_K=temperature_K,
        )
        is_opaque_preblend = _is_opaque_preblend(name, profile)
        requires_composite = is_opaque_preblend or _is_natural_mixture(name)
        if composite_result is not None:
            partial_pressure = composite_result.partial_pressure_pa
            vapor_ppm = composite_result.vapor_ppm
            oav_value = composite_result.oav
            composite_reference, _, _ = _lookup_composite_headspace(
                canonical,
                name,
                active_g,
                composite_total_moles,
                temperature_K=VP_REFERENCE_T_K,
            )
            if composite_reference is not None and composite_reference.partial_pressure_pa > 0:
                vp_temperature_factor = (
                    composite_result.partial_pressure_pa / composite_reference.partial_pressure_pa
                )
        elif requires_composite:
            # Unsupported naturals and opaque preblends must fail closed.
            # Their bulk MW/VP is not a defensible odor authority proxy.
            oav_value = None
        family = getattr(profile, "or_family", None) if profile else None
        intensity = (
            perceived_intensity_stevens(oav_value, family) if oav_value is not None else None
        )
        screening_headspace_available = composite_result is not None or (
            not requires_composite and vp is not None
        )
        projection = _physics_projection_authority(
            formula_mass_chain_complete=all_active_masses_authoritative,
            formula_mw_chain_complete=formula_mw_chain_complete,
            vp_available=vp is not None,
            odt_available=odt_air_ppm is not None,
            composite_available=composite_result is not None,
            composite_canonical_complete=_composite_supports_canonical_projection(
                composite_metadata
            ),
            requires_composite=requires_composite,
            gamma_source=gamma_source,
            screening_partial_pressure_pa=(
                float(partial_pressure) if screening_headspace_available else None
            ),
            screening_vapor_ppm=(
                float(vapor_ppm) if screening_headspace_available else None
            ),
            screening_oav=oav_value,
            screening_intensity=intensity,
        )
        note = getattr(profile, "note", None) or "heart"
        role = getattr(profile, "role", None) or "modifier"
        texture = getattr(profile, "texture", None) or ""
        reg_name = identity.registry_name
        profile_name = identity.profile_name
        ifra_limit = IFRA_CAT4_LIMITS.get(name) or IFRA_CAT4_LIMITS.get(profile_name or "")
        missing = tuple(
            field_name
            for field_name, value in (
                ("density", None if density_source.startswith("fallback:") else density),
                ("mw", mw),
                ("logp", logp),
                ("vp", vp),
                ("odt_air_ppm", odt_air_ppm),
            )
            if value is None
        )

        sources = {
            "density": density_source,
            "mw": mw_source if mw is not None else "missing",
            "logp": logp_source if logp is not None else "missing",
            "vp": vp_source if vp is not None else "missing",
            "vp_temperature": vp_temperature_source,
            "dhvap": dhvap_source,
            "gamma": gamma_source,
            "odt": odt_source,
            "ifra": "ifra_cat4_table:51"
            if ifra_limit is not None
            else "missing_or_unrestricted",
            "oav_model": _oav_model_source(composite_result, requires_composite),
        }
        if composite_metadata is not None and composite_result is not None:
            sources["mw"] = "literature:natural_composite_constituent_mw"
            sources["vp"] = "literature:natural_composite_constituent_vp"
            sources["vp_temperature"] = composite_result.temperature_model
            sources["dhvap"] = composite_result.dhvap_model
            sources["gamma"] = "modeled:natural_composite_constituent_gamma"
            sources["odt"] = "modeled:natural_composite_constituent_odt"
            sources["natural_composite"] = (
                f"{composite_metadata.composition_authority};"
                f"profile={composite_metadata.profile_key};"
                f"coverage={composite_metadata.characterized_fraction:.6f};"
                f"resolution={composite_metadata.resolution};"
                f"lookup={composite_lookup_name};"
                "batch_specific=false"
            )
        uncertainty_fields.extend(
            [
                field_uncertainty(f"{name}.vp", sources["vp"]),
                field_uncertainty(
                    f"{name}.vp_temperature",
                    sources["vp_temperature"],
                ),
                field_uncertainty(f"{name}.dhvap", sources["dhvap"]),
                field_uncertainty(f"{name}.gamma", sources["gamma"]),
                field_uncertainty(f"{name}.odt", sources["odt"]),
            ]
        )

        materials.append(
            MaterialState(
                name=name,
                canonical_name=canonical,
                raw_ul=raw_ul,
                dilution=dilution,
                active_ul=active_ul,
                density_g_ml=density,
                density_source=density_source,
                active_g=active_g,
                authoritative_active_g=authoritative_active_g,
                active_mass_authority=active_mass_authority,
                stock_fraction_basis=stock_fraction_basis,
                stock_carrier=stock_carrier,
                stock_declared=stock_declared,
                active_concentrate_ppm_w_w=(
                    1e6 * float(authoritative_active_g or 0.0) / total_authoritative_active_g
                    if all_active_masses_authoritative and total_authoritative_active_g > 0
                    else None
                ),
                mw_g_mol=float(mw) if mw is not None else None,
                moles=moles,
                mole_fraction=x_i,
                logp=float(logp) if logp is not None else None,
                vp_pure_pa=float(vp) if vp is not None else None,
                vp_temperature_factor=vp_temperature_factor,
                gamma=float(gamma_value),
                gamma_source=gamma_source,
                partial_pressure_pa=float(partial_pressure),
                vapor_ppm=float(vapor_ppm),
                odt_air_ppm=odt_air_ppm,
                oav=oav_value,
                intensity=intensity,
                family=family,
                note=note,
                role=role,
                texture=texture,
                profile_name=profile_name,
                registry_name=reg_name,
                ifra_limit_pct=ifra_limit,
                is_known=identity.is_known or composite_metadata is not None,
                is_opaque_preblend=is_opaque_preblend,
                functional_groups=functional_groups,
                hsp=hsp,
                hsp_source=hsp_source,
                sources=sources,
                missing_fields=missing,
                natural_composite_metadata=(
                    composite_metadata.as_dict() if composite_metadata else {}
                ),
                active_finished_product_ppm_w_w=(
                    1e6 * float(authoritative_active_g or 0.0) / finished_mass_g
                    if all_active_masses_authoritative
                    and matrix_source == "explicit"
                    and finished_mass_g > 0
                    else None
                ),
                **projection,
            )
        )

    # FIX: DPG and carriers are NOT odorant-active. Use engine.units.concentration.classify_material_category().
    from engine.units.concentration import classify_material_category

    odorant_active_ul = sum(
        m.active_ul for m in materials if classify_material_category(m.name) == "odorant"
    )

    return FormulaState(
        materials=tuple(materials),
        total_raw_ul=sum(float(v or 0.0) for v in ingredients_ul.values()),
        total_active_ul=sum(m.active_ul for m in materials),
        odorant_active_ul=odorant_active_ul,
        batch_volume_ml=float(batch_volume_ml),
        temperature_K=float(temperature_K),
        context=context,
        uncertainty=combine_uncertainties(uncertainty_fields),
        matrix_components_moles=matrix_mole_items,
        matrix_mass_g=matrix_mass_g,
        matrix_source=matrix_source,
    )


def build_formula_state(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float] | None = None,
    *,
    stock_specs: Mapping[str, Mapping[str, object]] | None = None,
    batch_volume_ml: float = 30.0,
    temperature_K: float = DEFAULT_TEMPERATURE_K,  # noqa: N803
    context: str = "skin",
    matrix_moles: Mapping[str, float] | None = None,
    matrix_mass_g: float = 0.0,
    matrix_source: str = "omitted",
) -> FormulaState:
    """Build a canonical physical state from a raw uL formula table."""
    matrix_source_value = str(matrix_source).strip()
    if not matrix_source_value:
        raise ValueError("matrix_source must be a non-empty authority label")
    matrix_mass_value = float(matrix_mass_g)
    if not math.isfinite(matrix_mass_value) or matrix_mass_value < 0:
        raise ValueError("matrix_mass_g must be finite and nonnegative")
    matrix_values = {
        str(name).strip(): float(value)
        for name, value in (matrix_moles or {}).items()
    }
    if any(not name for name in matrix_values):
        raise ValueError("matrix component identities must be non-empty")
    if any(not math.isfinite(value) or value < 0 for value in matrix_values.values()):
        raise ValueError("matrix moles must be finite and nonnegative")
    if matrix_source_value.casefold() == "explicit":
        if matrix_mass_value <= 0.0 or sum(matrix_values.values()) <= 0.0:
            raise ValueError(
                "explicit matrix authority requires positive matrix mass and component moles"
            )
    return _build_formula_state_cached(
        _freeze_mapping(ingredients_ul, 0.0),
        _freeze_mapping(dilutions, 1.0),
        _freeze_stock_specs(stock_specs),
        float(batch_volume_ml),
        float(temperature_K),
        str(context),
        _freeze_mapping(matrix_values, 0.0),
        matrix_mass_value,
        matrix_source_value,
    )


build_formula_state.cache_clear = (  # type: ignore[attr-defined]
    _build_formula_state_cached.cache_clear
)
