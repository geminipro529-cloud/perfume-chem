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

from dataclasses import dataclass, field
from typing import Mapping

from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.ingredient_intelligence import MaterialProfile
from engine.material_resolver import resolve_material
from engine.mixer.prebonding import get_functional_groups
from engine.name_utils import normalize_name
from engine.odor_thresholds import ODT_DATA
from engine.perception.oav import oav, perceived_intensity_stevens
from engine.science_data import get_science_profile
from engine.thermo.activity import gamma
from engine.thermo.antoine import R_GAS, vp_pa
from engine.uncertainty import FieldUncertainty, FormulaUncertainty, combine_uncertainties, field_uncertainty


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


@dataclass(frozen=True, slots=True)
class MaterialState:
    name: str
    canonical_name: str
    raw_ul: float
    dilution: float
    active_ul: float
    density_g_ml: float
    active_g: float
    mw_g_mol: float | None
    moles: float
    mole_fraction: float
    logp: float | None
    vp_pure_pa: float | None
    gamma: float
    gamma_source: str
    partial_pressure_pa: float
    vapor_ppm: float
    odt_air_ppm: float | None
    oav: float | None
    intensity: float | None
    family: str | None
    note: str
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

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "canonical_name": self.canonical_name,
            "raw_ul": round(self.raw_ul, 4),
            "dilution": self.dilution,
            "active_ul": round(self.active_ul, 4),
            "active_g": round(self.active_g, 8),
            "mw_g_mol": self.mw_g_mol,
            "moles": self.moles,
            "mole_fraction": self.mole_fraction,
            "logp": self.logp,
            "vp_pure_pa": self.vp_pure_pa,
            "gamma": self.gamma,
            "gamma_source": self.gamma_source,
            "partial_pressure_pa": self.partial_pressure_pa,
            "vapor_ppm": self.vapor_ppm,
            "odt_air_ppm": self.odt_air_ppm,
            "oav": self.oav,
            "intensity": self.intensity,
            "family": self.family,
            "note": self.note,
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
        }


@dataclass(frozen=True, slots=True)
class FormulaState:
    materials: tuple[MaterialState, ...]
    total_raw_ul: float
    total_active_ul: float
    batch_volume_ml: float
    temperature_K: float
    context: str
    uncertainty: FormulaUncertainty

    @property
    def material_count(self) -> int:
        return len(self.materials)

    @property
    def perceptible_materials(self) -> tuple[MaterialState, ...]:
        return tuple(m for m in self.materials if (m.oav or 0.0) >= 1.0)

    @property
    def total_vapor_ppm(self) -> float:
        return sum(m.vapor_ppm for m in self.materials)

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

    def as_dict(self) -> dict:
        return {
            "total_raw_ul": round(self.total_raw_ul, 4),
            "total_active_ul": round(self.total_active_ul, 4),
            "batch_volume_ml": self.batch_volume_ml,
            "temperature_K": self.temperature_K,
            "context": self.context,
            "total_vapor_ppm": round(self.total_vapor_ppm, 6),
            "note_distribution": self.note_distribution(),
            "uncertainty": {
                "relative_uncertainty": self.uncertainty.relative_uncertainty,
                "confidence_score": self.uncertainty.confidence_score,
                "confidence_grade": self.uncertainty.confidence_grade,
            },
            "materials": [m.as_dict() for m in self.materials],
        }


def _lookup_odt(name: str, profile: MaterialProfile | None, registry_material=None) -> tuple[float | None, str]:
    norm = normalize_name(name)
    for odt_name, data in ODT_DATA.items():
        if normalize_name(odt_name) == norm:
            odt_air_ppb = data.get("odt_air")
            if odt_air_ppb is not None:
                return float(odt_air_ppb) / 1000.0, "literature:odor_thresholds.odt_air"
    if registry_material is not None and getattr(registry_material, "odt_air_ppb", None) is not None:
        return float(registry_material.odt_air_ppb) / 1000.0, "registry:data_spine.odt_air_ppb"
    if profile and profile.odt is not None:
        return float(profile.odt) / 1000.0, "profile:ingredient_intelligence.odt"
    return None, "missing"


def _is_opaque_preblend(name: str, profile: MaterialProfile | None) -> bool:
    low = f" {name.lower()} "
    if any(token in low for token in OPAQUE_PREBLEND_TOKENS):
        return True
    if profile and profile.name.lower() != name.lower():
        prof_low = f" {profile.name.lower()} "
        if any(token in prof_low for token in OPAQUE_PREBLEND_TOKENS):
            return True
    return False


def _first_present(*values):
    for value, source in values:
        if value is not None:
            return value, source
    return None, "missing"


def _registry_hsp(material) -> tuple[float, float, float] | None:
    if material is None or material.hsp is None:
        return None
    hsp = material.hsp
    if hsp.delta_d is None or hsp.delta_p is None or hsp.delta_h is None:
        return None
    return (float(hsp.delta_d), float(hsp.delta_p), float(hsp.delta_h))


def _fallback_hsp(*candidates: str | None) -> tuple[tuple[float, float, float] | None, str]:
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
            return (float(hsp[0]), float(hsp[1]), float(hsp[2])), "fallback:science_data.hsp"
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


def build_formula_state(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float] | None = None,
    *,
    batch_volume_ml: float = 30.0,
    temperature_K: float = DEFAULT_TEMPERATURE_K,
    context: str = "skin",
) -> FormulaState:
    """Build a canonical physical state from a raw uL formula table."""
    dilutions = dilutions or {}

    raw_rows = []
    total_moles = 0.0
    uncertainty_fields: list[FieldUncertainty] = []
    mole_inputs: dict[str, float] = {}
    hsp_table: dict[str, tuple[float, float, float]] = {}

    for name, raw_amount in ingredients_ul.items():
        raw_ul = max(0.0, float(raw_amount or 0.0))
        dilution = float(dilutions.get(name, 1.0) or 1.0)
        active_ul = raw_ul * dilution
        identity = resolve_material(name)
        profile = identity.profile
        reg_mat = identity.registry_material

        mw, mw_source = _first_present(
            (getattr(reg_mat, "mw_g_mol", None), "registry:data_spine.mw"),
            (getattr(profile, "mw", None), "profile:ingredient_intelligence.mw"),
        )
        logp, logp_source = _first_present(
            (getattr(reg_mat, "logp", None), "registry:data_spine.logp"),
            (getattr(profile, "clogp", None), "profile:ingredient_intelligence.clogp"),
        )
        density = getattr(reg_mat, "density_25c_g_ml", None) or DEFAULT_DENSITY_G_ML
        active_g = active_ul * density / 1000.0
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

        raw_rows.append((
            name, raw_ul, dilution, active_ul, active_g, moles, identity, profile, reg_mat,
            mw, mw_source, logp, logp_source, functional_groups, hsp, hsp_source,
        ))
        uncertainty_fields.extend([
            field_uncertainty(f"{name}.mw", mw_source if mw is not None else "missing"),
            field_uncertainty(f"{name}.logp", logp_source if logp is not None else "missing"),
        ])

    mole_fractions = {
        name: (moles / total_moles if total_moles > 0 else 0.0)
        for name, moles in mole_inputs.items()
    }

    materials: list[MaterialState] = []
    for (
        name, raw_ul, dilution, active_ul, active_g, moles, identity, profile, reg_mat,
        mw, mw_source, logp, logp_source, functional_groups, hsp, hsp_source,
    ) in raw_rows:
        canonical = identity.canonical_name
        x_i = mole_fractions.get(canonical, 0.0)
        ant = _registry_antoine(reg_mat)
        vp_25, vp_source = _first_present(
            (getattr(reg_mat, "vp_25c_pa", None), "registry:data_spine.vp_25c"),
            (getattr(profile, "vp", None), "profile:ingredient_intelligence.vp"),
        )
        dhvap = getattr(reg_mat, "dhvap_kj_mol", None)
        try:
            if ant is not None:
                vp = vp_pa(temperature_K, A=ant[0], B=ant[1], C=ant[2])
                vp_source = "measured:data_spine.antoine"
            elif vp_25 is not None:
                vp = vp_pa(temperature_K, vp_25c_pa=float(vp_25), dhvap_kj_mol=dhvap)
            else:
                vp = None
        except Exception:
            vp = None

        gamma_source = "heuristic:hansen_distance"
        try:
            gamma_value = gamma(canonical, mole_fractions, temperature_K, hsp_table=hsp_table)
        except Exception:
            gamma_value = 1.0
            gamma_source = "fallback:ideal_gamma"

        partial_pressure = (gamma_value * x_i * vp) if vp is not None else 0.0
        vapor_ppm = 1e6 * partial_pressure / P_ATM_PA
        odt_air_ppm, odt_source = _lookup_odt(name, profile, reg_mat)
        oav_value = oav(vapor_ppm, odt_air_ppm) if odt_air_ppm else None
        family = getattr(profile, "or_family", None) if profile else None
        intensity = (
            perceived_intensity_stevens(oav_value, family)
            if oav_value is not None
            else None
        )
        note = getattr(profile, "note", None) or "heart"
        reg_name = identity.registry_name
        profile_name = identity.profile_name
        ifra_limit = IFRA_CAT4_LIMITS.get(name) or IFRA_CAT4_LIMITS.get(profile_name or "")
        missing = tuple(
            field_name
            for field_name, value in (
                ("mw", mw),
                ("logp", logp),
                ("vp", vp),
                ("odt_air_ppm", odt_air_ppm),
            )
            if value is None
        )

        sources = {
            "mw": mw_source if mw is not None else "missing",
            "logp": logp_source if logp is not None else "missing",
            "vp": vp_source if vp is not None else "missing",
            "gamma": gamma_source,
            "odt": odt_source,
            "ifra": "literature:ifra_safety" if ifra_limit is not None else "missing_or_unrestricted",
        }
        uncertainty_fields.extend([
            field_uncertainty(f"{name}.vp", sources["vp"]),
            field_uncertainty(f"{name}.gamma", sources["gamma"]),
            field_uncertainty(f"{name}.odt", sources["odt"]),
        ])

        materials.append(
            MaterialState(
                name=name,
                canonical_name=canonical,
                raw_ul=raw_ul,
                dilution=dilution,
                active_ul=active_ul,
                density_g_ml=float(getattr(reg_mat, "density_25c_g_ml", None) or DEFAULT_DENSITY_G_ML),
                active_g=active_g,
                mw_g_mol=float(mw) if mw is not None else None,
                moles=moles,
                mole_fraction=x_i,
                logp=float(logp) if logp is not None else None,
                vp_pure_pa=float(vp) if vp is not None else None,
                gamma=float(gamma_value),
                gamma_source=gamma_source,
                partial_pressure_pa=float(partial_pressure),
                vapor_ppm=float(vapor_ppm),
                odt_air_ppm=odt_air_ppm,
                oav=oav_value,
                intensity=intensity,
                family=family,
                note=note,
                profile_name=profile_name,
                registry_name=reg_name,
                ifra_limit_pct=ifra_limit,
                is_known=identity.is_known,
                is_opaque_preblend=_is_opaque_preblend(name, profile),
                functional_groups=functional_groups,
                hsp=hsp,
                hsp_source=hsp_source,
                sources=sources,
                missing_fields=missing,
            )
        )

    return FormulaState(
        materials=tuple(materials),
        total_raw_ul=sum(float(v or 0.0) for v in ingredients_ul.values()),
        total_active_ul=sum(m.active_ul for m in materials),
        batch_volume_ml=float(batch_volume_ml),
        temperature_K=float(temperature_K),
        context=context,
        uncertainty=combine_uncertainties(uncertainty_fields),
    )
