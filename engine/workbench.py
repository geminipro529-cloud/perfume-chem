"""Canonical application boundary for evidence-labeled perfume analysis."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

from engine.bottle_addition import AdditionRequest, AdditionResult, AdditionSolver
from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.pipeline.simulator import DEFAULT_WINDOWS, SimulationFrame, simulate_formula
from engine.scientific_contract import EvidenceDescriptor, ScientificClass


@dataclass(frozen=True, slots=True)
class WorkbenchFormulaRequest:
    """Validated formula inputs for the canonical analysis path."""

    formula_name: str
    ingredients_ul: Mapping[str, float]
    batch_volume_ml: float
    dilutions: Mapping[str, float] | None = None
    temperature_K: float = 305.0
    context: str = "skin"
    windows: Sequence[tuple[str, float]] = DEFAULT_WINDOWS
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = self.formula_name.strip()
        if not name:
            raise ValueError("formula_name must not be empty")

        ingredients = {
            str(material).strip(): float(amount)
            for material, amount in self.ingredients_ul.items()
        }
        if not ingredients or any(not material for material in ingredients):
            raise ValueError("ingredients_ul must contain named materials")
        if any(not isfinite(amount) or amount <= 0 for amount in ingredients.values()):
            raise ValueError("ingredient volumes must be finite and greater than zero")

        dilutions = {
            str(material).strip(): float(fraction)
            for material, fraction in (self.dilutions or {}).items()
        }
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

        batch_volume_ml = float(self.batch_volume_ml)
        temperature_K = float(self.temperature_K)
        if not isfinite(batch_volume_ml) or batch_volume_ml <= 0:
            raise ValueError("batch_volume_ml must be finite and greater than zero")
        if not isfinite(temperature_K) or temperature_K <= 0:
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
        object.__setattr__(self, "temperature_K", temperature_K)
        object.__setattr__(self, "context", context)
        object.__setattr__(self, "windows", windows)
        object.__setattr__(self, "assumptions", tuple(self.assumptions))


@dataclass(frozen=True, slots=True)
class WorkbenchAnalysis:
    """Canonical state, temporal frames, and claim-level evidence posture."""

    request: WorkbenchFormulaRequest
    formula_state: FormulaState
    time_series: tuple[SimulationFrame, ...]
    evidence: dict[str, EvidenceDescriptor]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "analysis_engine": "engine.workbench.PerfumeWorkbench",
            "formula_name": self.request.formula_name,
            "formula_state": self.formula_state.as_dict(),
            "material_oav_table": [
                material.as_dict() for material in self.formula_state.materials
            ],
            "note_distribution": self.formula_state.note_distribution(),
            "time_series": [frame.as_dict() for frame in self.time_series],
            "evidence": {
                name: descriptor.as_dict()
                for name, descriptor in self.evidence.items()
            },
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
            "estimated_longevity_hours": None,
            "estimated_sillage": None,
        }


class PerfumeWorkbench:
    """One local-first service for deterministic and evidence-labeled outputs."""

    def __init__(self, addition_solver: AdditionSolver | None = None) -> None:
        self._addition_solver = addition_solver or AdditionSolver()

    def analyze(self, request: WorkbenchFormulaRequest) -> WorkbenchAnalysis:
        state = build_formula_state(
            request.ingredients_ul,
            request.dilutions,
            batch_volume_ml=request.batch_volume_ml,
            temperature_K=request.temperature_K,
            context=request.context,
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
        evidence = _evidence_for(state)
        assumptions = _analysis_assumptions(request)
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
        )

    def calculate_addition(self, request: AdditionRequest) -> AdditionResult:
        return self._addition_solver.reach_target_active_fraction(request)


def _analysis_assumptions(request: WorkbenchFormulaRequest) -> tuple[str, ...]:
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
    return _unique(assumptions)


def _evidence_for(state: FormulaState) -> dict[str, EvidenceDescriptor]:
    odt_sources = _unique(
        material.sources.get("odt", "missing") for material in state.materials
    )
    return {
        "dose_arithmetic": EvidenceDescriptor(
            classification=ScientificClass.EXACT,
            basis="raw active volume equals supplied stock volume multiplied by supplied active fraction",
            sources=("engine.pipeline.formula_state",),
            assumptions=("input volumes and stock fractions are supplied setpoints",),
            limitations=(
                "EXACT classifies arithmetic and does not imply calibrated dispensing accuracy",
            ),
        ),
        "headspace": EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis=(
                "modified-Raoult-style partial pressure using odorant-only mole fractions, "
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
                "the finished ethanol-water-solvent matrix is omitted from liquid-phase mole fractions",
                "reported vapor ppm is modeled rather than measured headspace concentration",
                "default density or molecular weight may be used where physical data are missing",
            ),
        ),
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
        "temporal_evolution": EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis="exponential material loss scaled by vapor pressure, activity coefficient, and molecular weight",
            sources=("engine.pipeline.simulator",),
            assumptions=("a single finite-film loss approximation applies to all materials",),
            limitations=(
                "not calibrated against measured skin or blotter evaporation curves",
                "does not model changing solvent matrix, diffusion, or skin absorption explicitly",
            ),
        ),
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
    }


def _unique(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


__all__ = ["PerfumeWorkbench", "WorkbenchAnalysis", "WorkbenchFormulaRequest"]
