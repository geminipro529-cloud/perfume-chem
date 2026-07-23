"""Canonical application boundary for evidence-labeled perfume analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, Mapping, Sequence

from engine.bottle_addition import AdditionRequest, AdditionResult, AdditionSolver
from engine.intervention_hypotheses import (
    InterventionHypothesisRequest,
    InterventionHypothesisResult,
    generate_intervention_hypotheses,
)
from engine.intervention_trial import (
    InterventionTrialRequest,
    InterventionTrialResult,
    plan_intervention_trial,
)
from engine.interventions import InterventionRequest, InterventionResult, rank_interventions
from engine.mixture import MixtureComponent, MixtureState
from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.pipeline.simulator import DEFAULT_WINDOWS, SimulationFrame, simulate_formula
from engine.quantities import ConcentrationBasis
from engine.safety_assessment import (
    SafetyAssessmentRequest,
    SafetyAssessmentResult,
    assess_safety,
)
from engine.scientific_contract import EvidenceDescriptor, ScientificClass


class CalculationMode(str, Enum):
    """Whether a request permits disclosed compatibility assumptions."""

    STRICT = "strict"
    COMPATIBILITY = "compatibility"


def _stock_basis_name(
    value: ConcentrationBasis | str | None,
    *,
    fraction: float,
    declared: bool,
) -> str:
    if isinstance(value, ConcentrationBasis):
        return value.value
    if value is not None:
        return str(value)
    # An explicitly declared 100% stock is neat by definition; w/w, w/v, and
    # v/v distinctions only become material for a fractional stock solution.
    if declared and fraction == 1.0:
        return "neat"
    return "unspecified"


@dataclass(frozen=True, slots=True)
class WorkbenchFormulaRequest:
    """Validated formula inputs for the canonical analysis path."""

    formula_name: str
    ingredients_ul: Mapping[str, float]
    batch_volume_ml: float
    dilutions: Mapping[str, float] | None = None
    temperature_K: float = 305.0  # noqa: N815 - kelvin unit suffix
    context: str = "skin"
    windows: Sequence[tuple[str, float]] = DEFAULT_WINDOWS
    assumptions: tuple[str, ...] = ()
    matrix_components: tuple[MixtureComponent, ...] = ()
    mode: CalculationMode = CalculationMode.COMPATIBILITY
    stock_fraction_bases: Mapping[str, ConcentrationBasis | str] | None = None

    def __post_init__(self) -> None:
        name = self.formula_name.strip()
        if not name:
            raise ValueError("formula_name must not be empty")

        ingredients = _trimmed_mapping(self.ingredients_ul, "ingredients_ul")
        if not ingredients or any(not material for material in ingredients):
            raise ValueError("ingredients_ul must contain named materials")
        if any(not isfinite(amount) or amount <= 0 for amount in ingredients.values()):
            raise ValueError("ingredient volumes must be finite and greater than zero")

        dilutions = _trimmed_mapping(self.dilutions or {}, "dilutions")
        unknown_dilutions = set(dilutions).difference(ingredients)
        if unknown_dilutions:
            raise ValueError(
                "dilutions contains materials absent from ingredients_ul: "
                + ", ".join(sorted(unknown_dilutions))
            )
        if any(
            not isfinite(fraction) or not 0 < fraction <= 1
            for fraction in dilutions.values()
        ):
            raise ValueError("dilution fractions must be finite, greater than zero, and at most one")

        try:
            mode = CalculationMode(self.mode)
        except ValueError as exc:
            raise ValueError("mode must be strict or compatibility") from exc
        matrix_components = tuple(self.matrix_components)
        stock_fraction_bases = _normalized_fraction_bases(
            self.stock_fraction_bases or {}
        )
        unknown_bases = set(stock_fraction_bases).difference(ingredients)
        if unknown_bases:
            raise ValueError(
                "stock_fraction_bases contains materials absent from ingredients_ul: "
                + ", ".join(sorted(unknown_bases))
            )
        if mode is CalculationMode.STRICT:
            missing_dilutions = set(ingredients).difference(dilutions)
            if missing_dilutions:
                raise ValueError(
                    "strict mode requires explicit dilutions for every ingredient: "
                    + ", ".join(sorted(missing_dilutions))
                )
            if not matrix_components:
                raise ValueError(
                    "strict mode requires an explicit finished-product matrix"
                )
            missing_bases = set(ingredients).difference(stock_fraction_bases)
            if missing_bases:
                raise ValueError(
                    "strict mode requires an explicit stock fraction basis for every ingredient: "
                    + ", ".join(sorted(missing_bases))
                )
            unsupported = {
                name
                for name, basis in stock_fraction_bases.items()
                if basis is not ConcentrationBasis.VOLUME_FRACTION
            }
            if unsupported:
                raise ValueError(
                    "strict volume-dose analysis currently requires volume_fraction stock bases: "
                    + ", ".join(sorted(unsupported))
                )
            diluted_stocks = {
                name for name, fraction in dilutions.items() if fraction < 1.0
            }
            if diluted_stocks:
                raise ValueError(
                    "strict mode requires explicit stock carrier decomposition for diluted stocks: "
                    + ", ".join(sorted(diluted_stocks))
                )

        batch_volume_ml = float(self.batch_volume_ml)
        temperature_k = float(self.temperature_K)
        if not isfinite(batch_volume_ml) or batch_volume_ml <= 0:
            raise ValueError("batch_volume_ml must be finite and greater than zero")
        if not isfinite(temperature_k) or temperature_k <= 0:
            raise ValueError("temperature_K must be finite and greater than zero")

        context = self.context.strip()
        if not context:
            raise ValueError("context must not be empty")

        windows = tuple((str(label).strip(), float(seconds)) for label, seconds in self.windows)
        if not windows or any(
            not label or not isfinite(seconds) or seconds < 0
            for label, seconds in windows
        ):
            raise ValueError("windows must contain named, nonnegative finite times")
        if len({label for label, _ in windows}) != len(windows):
            raise ValueError("window labels must be unique")
        if any(
            later_seconds < earlier_seconds
            for (_, earlier_seconds), (_, later_seconds) in zip(windows, windows[1:])
        ):
            raise ValueError("windows must be ordered by increasing time")

        object.__setattr__(self, "formula_name", name)
        object.__setattr__(self, "ingredients_ul", ingredients)
        object.__setattr__(self, "dilutions", dilutions)
        object.__setattr__(self, "batch_volume_ml", batch_volume_ml)
        object.__setattr__(self, "temperature_K", temperature_k)
        object.__setattr__(self, "context", context)
        object.__setattr__(self, "windows", windows)
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "matrix_components", matrix_components)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "stock_fraction_bases", stock_fraction_bases)


@dataclass(frozen=True, slots=True)
class WorkbenchAnalysis:
    """Canonical state, temporal frames, and claim-level evidence posture."""

    request: WorkbenchFormulaRequest
    formula_state: FormulaState
    time_series: tuple[SimulationFrame, ...]
    evidence: dict[str, EvidenceDescriptor]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    mixture_state: MixtureState | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "analysis_engine": "engine.workbench.PerfumeWorkbench",
            "calculation_mode": self.request.mode.value,
            "formula_name": self.request.formula_name,
            "formula_state": self.formula_state.as_dict(),
            "material_oav_table": [
                material.as_dict() for material in self.formula_state.materials
            ],
            "note_distribution": self.formula_state.note_distribution(),
            "time_series": [frame.as_dict() for frame in self.time_series],
            "mixture_state": _mixture_payload(self.formula_state, self.mixture_state),
            "evidence": {
                name: descriptor.as_dict()
                for name, descriptor in self.evidence.items()
            },
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "regulatory_assessment": {
                "status": "unverified",
                "source_version": None,
                "reason": (
                    "No versioned IFRA category certificate and constituent-level "
                    "natural/preblend composition were supplied to this request."
                ),
            },
            "estimated_longevity_hours": None,
            "estimated_sillage": None,
        }


class PerfumeWorkbench:
    """One local-first service for deterministic and evidence-labeled outputs."""

    def __init__(self, addition_solver: AdditionSolver | None = None) -> None:
        self._addition_solver = addition_solver or AdditionSolver()

    def analyze(self, request: WorkbenchFormulaRequest) -> WorkbenchAnalysis:
        mixture_state = (
            MixtureState.from_components(request.matrix_components)
            if request.matrix_components
            else None
        )
        matrix_moles = None
        matrix_mass_g = 0.0
        matrix_source = "omitted"
        if mixture_state is not None:
            matrix_source = "explicit" if mixture_state.complete else "incomplete"
            if mixture_state.complete:
                matrix_moles = {
                    component.name: float(component.moles or 0.0)
                    for component in mixture_state.components
                }
                assert mixture_state.total_mass is not None
                matrix_mass_g = mixture_state.total_mass.g
                if any(
                    fraction < 1.0 for fraction in (request.dilutions or {}).values()
                ):
                    matrix_source = "incomplete_stock_carrier"
        if (
            request.mode is CalculationMode.STRICT
            and mixture_state is not None
            and not mixture_state.complete
        ):
            raise ValueError(
                "strict mode requires density and molar mass for every matrix component: "
                + ", ".join(mixture_state.missing_inputs)
            )
        fraction_bases = request.stock_fraction_bases or {}
        stock_specs = {}
        for name in request.ingredients_ul:
            fraction = float((request.dilutions or {}).get(name, 1.0))
            declared = name in (request.dilutions or {})
            stock_specs[name] = {
                "fraction": fraction,
                "fraction_basis": _stock_basis_name(
                    fraction_bases.get(name),
                    fraction=fraction,
                    declared=declared,
                ),
                "declared": declared,
            }
        state = build_formula_state(
            request.ingredients_ul,
            request.dilutions,
            stock_specs=stock_specs,
            batch_volume_ml=request.batch_volume_ml,
            temperature_K=request.temperature_K,
            context=request.context,
            matrix_moles=matrix_moles,
            matrix_mass_g=matrix_mass_g,
            matrix_source=matrix_source,
        )
        frames = tuple(
            simulate_formula(
                request.ingredients_ul,
                request.dilutions,
                batch_volume_ml=request.batch_volume_ml,
                temperature_K=request.temperature_K,
                context=request.context,
                windows=request.windows,
                initial_state=state,
            )
        )
        evidence = _evidence_for(state, mixture_state, request)
        assumptions = _analysis_assumptions(request, mixture_state)
        limitations = _unique(
            limitation
            for descriptor in evidence.values()
            for limitation in descriptor.limitations
        )
        return WorkbenchAnalysis(
            request=request,
            formula_state=state,
            time_series=frames,
            evidence=evidence,
            assumptions=assumptions,
            limitations=limitations,
            mixture_state=mixture_state,
        )

    def calculate_addition(self, request: AdditionRequest) -> AdditionResult:
        return self._addition_solver.reach_target_active_fraction(request)

    def assess_safety(self, request: SafetyAssessmentRequest) -> SafetyAssessmentResult:
        return assess_safety(request)

    def rank_interventions(self, request: InterventionRequest) -> InterventionResult:
        return rank_interventions(request)

    def generate_intervention_hypotheses(
        self, request: InterventionHypothesisRequest
    ) -> InterventionHypothesisResult:
        return generate_intervention_hypotheses(request)

    def plan_intervention_trial(
        self, request: InterventionTrialRequest
    ) -> InterventionTrialResult:
        return plan_intervention_trial(request, addition_solver=self._addition_solver)


def _analysis_assumptions(
    request: WorkbenchFormulaRequest,
    mixture_state: MixtureState | None,
) -> tuple[str, ...]:
    assumptions = list(request.assumptions)
    missing_dilutions = set(request.ingredients_ul).difference(request.dilutions or {})
    if missing_dilutions:
        assumptions.append(
            "Unspecified stock dilutions are treated as 1.0 active fraction: "
            + ", ".join(sorted(missing_dilutions))
        )
    assumptions.extend(
        (
            f"Temperature setpoint is {request.temperature_K:g} K.",
            f"Application context is {request.context}.",
            "Input microlitre volumes and dilution fractions are treated as supplied setpoints.",
        )
    )
    if mixture_state is None:
        assumptions.append("No explicit finished-product solvent matrix was supplied.")
    elif mixture_state.complete:
        assumptions.append(
            "Explicit matrix component mass and amount are included in liquid-phase fractions."
        )
    else:
        assumptions.append(
            "The supplied matrix is incomplete and is excluded from modeled liquid-phase fractions."
        )
    return _unique(assumptions)


def _evidence_for(
    state: FormulaState,
    mixture_state: MixtureState | None,
    request: WorkbenchFormulaRequest,
) -> dict[str, EvidenceDescriptor]:
    odt_sources = _unique(
        material.sources.get("odt", "missing") for material in state.materials
    )
    density_sources = _unique(
        material.sources.get("density", "missing") for material in state.materials
    )
    uses_assumed_dilution = bool(
        set(request.ingredients_ul).difference(request.dilutions or {})
    )
    uses_unqualified_fraction = any(
        (request.dilutions or {}).get(name, 1.0) < 1.0
        and name not in (request.stock_fraction_bases or {})
        for name in request.ingredients_ul
    )
    dose_inputs_are_explicit = not uses_assumed_dilution and not uses_unqualified_fraction
    ppm_is_exact = dose_inputs_are_explicit and all(
        material.active_concentrate_ppm_w_w is not None
        for material in state.materials
    )
    matrix_is_complete = mixture_state is not None and mixture_state.complete
    headspace = EvidenceDescriptor(
        classification=ScientificClass.HEURISTIC,
        basis=(
            "modified-Raoult-style partial pressure using "
            + ("solvent-inclusive" if matrix_is_complete else "odorant-only")
            + " mole fractions, "
            "vapor pressure, and activity-coefficient estimates"
        ),
        sources=(
            "engine.pipeline.formula_state",
            "https://goldbook.iupac.org/terms/view/15349",
        ),
        assumptions=(
            "thermodynamic properties and activity-coefficient fallbacks are applicable",
            "aromatic active volumes can be converted to mass using available or fallback density",
        ),
        limitations=(
            (
                "only explicitly supplied matrix components are included; stock-solution carriers may remain unresolved"
                if matrix_is_complete
                else "the finished ethanol-water-solvent matrix is omitted from liquid-phase mole fractions"
            ),
            "reported vapor ppm is modeled rather than measured headspace concentration",
            "default density or molecular weight may be used where physical data are missing",
        ),
    )
    temporal = EvidenceDescriptor(
        classification=ScientificClass.HEURISTIC,
        basis="exponential material loss scaled by vapor pressure, activity coefficient, and molecular weight",
        sources=("engine.pipeline.simulator",),
        assumptions=("a single finite-film loss approximation applies to all materials",),
        limitations=(
            "not calibrated against measured skin or blotter evaporation curves",
            "does not model changing solvent matrix, diffusion, or skin absorption explicitly",
            "activity coefficients are frozen at the opening composition for later temporal frames",
        ),
    )
    if mixture_state is None:
        finished_mixture = EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="no explicit finished-product matrix was supplied",
            sources=("engine.mixture",),
            limitations=("Finished-product mass and amount fractions are unavailable.",),
        )
    elif not mixture_state.complete:
        finished_mixture = EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="matrix arithmetic withheld because required physical inputs are missing",
            sources=("engine.mixture",),
            limitations=tuple(
                f"Missing explicit matrix input: {item}"
                for item in mixture_state.missing_inputs
            ),
        )
    elif state.matrix_source != "explicit":
        finished_mixture = EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="finished-product arithmetic withheld because diluted-stock carrier composition is unresolved",
            sources=("engine.mixture", "engine.pipeline.formula_state"),
            limitations=(
                "Decompose each diluted stock into active material and named carrier before requesting strict finished-product fractions.",
            ),
        )
    else:
        finished_ppm_is_exact = (
            state.matrix_source == "explicit"
            and dose_inputs_are_explicit
            and all(
                (request.dilutions or {}).get(name, 1.0) == 1.0
                for name in request.ingredients_ul
            )
            and all(
                material.active_finished_product_ppm_w_w is not None
                for material in state.materials
            )
        )
        finished_mixture = EvidenceDescriptor(
            classification=(
                ScientificClass.EXACT
                if finished_ppm_is_exact
                else ScientificClass.UNKNOWN
            ),
            basis=(
                "component volume multiplied by supplied density, then divided by supplied molar mass for amount fractions"
                if finished_ppm_is_exact
                else "finished-product fractions withheld because one or more odorant densities are missing"
            ),
            sources=("engine.mixture", "engine.pipeline.formula_state"),
            assumptions=("supplied component identities and physical properties apply",),
            limitations=(
                "EXACT classifies arithmetic for stated inputs, not measurement or property uncertainty",
            ),
        )

    return {
        "dose_arithmetic": EvidenceDescriptor(
            classification=(
                ScientificClass.HEURISTIC
                if uses_assumed_dilution or uses_unqualified_fraction
                else ScientificClass.EXACT
            ),
            basis=(
                "raw active volume uses an assumed or basis-unqualified stock fraction for one or more ingredients"
                if uses_assumed_dilution or uses_unqualified_fraction
                else "raw active volume equals supplied stock volume multiplied by supplied active fraction"
            ),
            sources=("engine.pipeline.formula_state",),
            assumptions=(
                (
                    "unspecified stock fractions are treated as neat in compatibility mode"
                    if uses_assumed_dilution
                    else (
                        "one or more supplied stock fractions lack an explicit physical basis"
                        if uses_unqualified_fraction
                        else "input volumes and stock fractions are supplied setpoints"
                    )
                ),
            ),
            limitations=(
                "EXACT classifies arithmetic and does not imply calibrated dispensing accuracy",
            ),
        ),
        "active_concentrate_ppm_w_w": EvidenceDescriptor(
            classification=(
                ScientificClass.EXACT
                if ppm_is_exact
                else (
                    ScientificClass.HEURISTIC
                    if uses_assumed_dilution or uses_unqualified_fraction
                    and all(
                        material.active_concentrate_ppm_w_w is not None
                        for material in state.materials
                    )
                    else ScientificClass.UNKNOWN
                )
            ),
            basis=(
                "active material mass divided by total active concentrate mass, multiplied by one million"
                if ppm_is_exact
                else (
                    "mass-fraction ppm uses an assumed neat stock fraction in compatibility mode"
                    if uses_assumed_dilution or uses_unqualified_fraction
                    else "mass-fraction ppm withheld because one or more material densities are missing"
                )
            ),
            sources=("engine.pipeline.formula_state", *density_sources),
            assumptions=(
                "stored 25 C densities and supplied active fractions are applicable",
            ),
            limitations=(
                (
                    "EXACT classifies arithmetic for stated densities and does not imply density measurement uncertainty is zero"
                    if ppm_is_exact
                    else "fallback density may support heuristic headspace calculations but is not accepted for exact mass-fraction ppm"
                ),
            ),
        ),
        "headspace": headspace,
        "finished_mixture": finished_mixture,
        "material_oav_table": headspace,
        "threshold_visibility": EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis="modeled vapor ppm divided by an air odor-detection threshold in ppm",
            sources=(
                "engine.pipeline.formula_state",
                "https://pubmed.ncbi.nlm.nih.gov/28231131/",
                *odt_sources,
            ),
            assumptions=(
                "the stored threshold is applicable to the modeled exposure context and matrix",
            ),
            limitations=(
                "threshold provenance varies by material",
                "detection thresholds are matrix- and method-dependent",
                "OAV is a screening ratio, not a direct prediction of perceived mixture intensity",
            ),
        ),
        "note_distribution": EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis="normalized active-volume shares grouped by configured top, heart, and base note tiers",
            sources=("engine.pipeline.formula_state",),
            assumptions=(
                "stored note tiers are applicable",
                "active volume is an appropriate structural weighting basis",
            ),
            limitations=(
                "does not account for odor threshold, headspace abundance, or mixture effects",
                "is not a measured perceptual note pyramid",
            ),
        ),
        "temporal_evolution": temporal,
        "time_series": temporal,
        "receptor_activation": EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="no material-specific receptor assay data are applied in production analysis",
            sources=(
                "https://pubmed.ncbi.nlm.nih.gov/32061665/",
                "https://pubmed.ncbi.nlm.nih.gov/32470365/",
            ),
            limitations=(
                "odor-family labels cannot substitute for receptor-specific affinity, efficacy, and mixture data",
            ),
        ),
        "regulatory_assessment": EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="no versioned regulatory assessment is emitted by the canonical workbench",
            sources=("engine.workbench",),
            limitations=(
                "requires product category, concentration basis, source version, and constituent-level composition",
                "composite natural OAV cannot substitute for regulatory constituent composition",
            ),
        ),
        "estimated_longevity_hours": EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="no calibrated longevity estimate is emitted by the canonical workbench",
            sources=("engine.workbench",),
            limitations=(
                "requires held-out skin or blotter persistence measurements for the relevant matrix and dose",
            ),
        ),
        "estimated_sillage": EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="no calibrated sillage estimate is emitted by the canonical workbench",
            sources=("engine.workbench",),
            limitations=(
                "requires a defined distance-time protocol and held-out measurements",
            ),
        ),
    }


def _trimmed_mapping(values: Mapping[str, float], label: str) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for raw_material, raw_value in values.items():
        material = str(raw_material).strip()
        if material in normalized:
            raise ValueError(
                f"{label} material names collide after trimming: {material!r}"
            )
        normalized[material] = float(raw_value)
    return normalized


def _unique(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _normalized_fraction_bases(
    values: Mapping[str, ConcentrationBasis | str],
) -> dict[str, ConcentrationBasis]:
    normalized: dict[str, ConcentrationBasis] = {}
    for raw_name, raw_basis in values.items():
        name = str(raw_name).strip()
        try:
            basis = ConcentrationBasis(raw_basis)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported stock fraction basis for {name}: {raw_basis}"
            ) from exc
        if name in normalized:
            raise ValueError(
                f"stock fraction basis names collide after trimming: {name!r}"
            )
        normalized[name] = basis
    return normalized


def _mixture_payload(
    state: FormulaState,
    mixture_state: MixtureState | None,
) -> dict[str, Any]:
    evidence_complete = bool(
        mixture_state is not None
        and mixture_state.complete
        and state.matrix_source == "explicit"
        and all(
            material.active_finished_product_ppm_w_w is not None
            for material in state.materials
        )
    )
    return {
        "matrix_supplied": mixture_state is not None,
        "complete": evidence_complete,
        "matrix_moles": state.matrix_moles,
        "matrix_mass_g": state.matrix_mass_g,
        "missing_inputs": (
            list(mixture_state.missing_inputs) if mixture_state is not None else []
        ),
        "matrix_components": (
            [component.as_dict() for component in mixture_state.components]
            if mixture_state is not None
            else []
        ),
    }


__all__ = [
    "CalculationMode",
    "PerfumeWorkbench",
    "WorkbenchAnalysis",
    "WorkbenchFormulaRequest",
]
