"""Deterministic planning for a separate, measurable intervention trial."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
import re

from engine.bottle_addition import (
    AdditionRequest,
    AdditionResult,
    AdditionSolver,
    BottleSnapshot,
    PipetteProfile,
    StockSolution,
)
from engine.material_resolver import resolve_material
from engine.odor_thresholds import (
    lookup_odt_entry,
    odt_collision_names,
    verify_odt,
)
from engine.pipeline.natural_absolute_decomposition import get_constituents
from engine.safety_assessment import SafetyAssessmentStatus
from engine.scientific_contract import EvidenceDescriptor, ScientificClass


@dataclass(frozen=True, slots=True)
class InterventionTrialRequest:
    """Measured inputs for one candidate aliquot and its sensory comparison."""

    brief_name: str
    material: str
    bottle: BottleSnapshot
    stock: StockSolution
    target_active_ppm_w_w: float
    evaluation_attribute: str
    threshold_matrix: str = "unknown"
    pipette: PipetteProfile | None = None
    evaluation_times_seconds: tuple[int, ...] = (0, 300, 1800, 7200, 14400)

    def __post_init__(self) -> None:
        brief_name = self.brief_name.strip()
        material = self.material.strip()
        attribute = self.evaluation_attribute.strip()
        target = float(self.target_active_ppm_w_w)
        matrix = self.threshold_matrix.strip().casefold()
        times = tuple(int(value) for value in self.evaluation_times_seconds)
        if not brief_name:
            raise ValueError("brief_name must not be empty")
        if not material:
            raise ValueError("material must not be empty")
        if not isfinite(target) or not 0 < target <= 1_000_000:
            raise ValueError(
                "target_active_ppm_w_w must be finite, greater than zero, and at most 1000000"
            )
        if not attribute:
            raise ValueError("evaluation_attribute must not be empty")
        if matrix not in {"ethanol", "unknown"}:
            raise ValueError("threshold_matrix must be ethanol or unknown")
        if not times or any(value < 0 for value in times):
            raise ValueError("evaluation times must contain nonnegative seconds")
        if times != tuple(sorted(set(times))):
            raise ValueError("evaluation times must be unique and increasing")

        object.__setattr__(self, "brief_name", brief_name)
        object.__setattr__(self, "material", material)
        object.__setattr__(self, "target_active_ppm_w_w", target)
        object.__setattr__(self, "evaluation_attribute", attribute)
        object.__setattr__(self, "threshold_matrix", matrix)
        object.__setattr__(self, "evaluation_times_seconds", times)


@dataclass(frozen=True, slots=True)
class EvaluationProtocol:
    design: str
    attribute: str
    times_seconds: tuple[int, ...]
    control: str
    candidate: str
    instructions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterventionTrialResult:
    brief_name: str
    material: str
    target_active_ppm_w_w: float
    achieved_active_ppm_w_w: float
    odt_ethanol_ppm: float | None
    oav: float | None
    addition: AdditionResult
    safety_status: SafetyAssessmentStatus
    evaluation_protocol: EvaluationProtocol
    evidence: dict[str, EvidenceDescriptor]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "brief_name": self.brief_name,
            "material": self.material,
            "target_active_ppm_w_w": self.target_active_ppm_w_w,
            "achieved_active_ppm_w_w": self.achieved_active_ppm_w_w,
            "odt_ethanol_ppm": self.odt_ethanol_ppm,
            "oav": self.oav,
            "addition": self.addition.as_dict(),
            "safety_status": self.safety_status.value,
            "evaluation_protocol": asdict(self.evaluation_protocol),
            "evidence": {
                name: descriptor.as_dict() for name, descriptor in self.evidence.items()
            },
            "warnings": list(self.warnings),
        }


def plan_intervention_trial(
    request: InterventionTrialRequest,
    *,
    addition_solver: AdditionSolver | None = None,
) -> InterventionTrialResult:
    """Plan a separate candidate aliquot without mutating a bottle ledger."""

    solver = addition_solver or AdditionSolver()
    addition = solver.reach_target_active_fraction(
        AdditionRequest(
            bottle=request.bottle,
            stock=request.stock,
            target_active_mass_fraction=request.target_active_ppm_w_w / 1_000_000.0,
            pipette=request.pipette,
        )
    )
    achieved_ppm = addition.resulting_active_mass_fraction * 1_000_000.0
    odt, oav_value, odt_evidence, odt_warning = _odt_oav(
        request.material,
        achieved_ppm,
        request.threshold_matrix,
    )
    protocol = EvaluationProtocol(
        design="paired_directional_comparison",
        attribute=request.evaluation_attribute,
        times_seconds=request.evaluation_times_seconds,
        control="unaltered bottle aliquot",
        candidate="separate aliquot containing the planned addition",
        instructions=(
            "Prepare separate control and candidate aliquots; do not modify the source bottle.",
            "Assign blind codes and randomize left/right presentation order.",
            "Match substrate, application mass, environment, and observation times.",
            f"Judge the prespecified directional attribute: {request.evaluation_attribute}.",
            f"Record whether the named brief remains recognizable: {request.brief_name}.",
        ),
    )
    warnings = list(addition.warnings)
    if odt_warning:
        warnings.append(odt_warning)
    warnings.append(
        "Safety remains unverified; complete a versioned category-specific safety assessment "
        "before skin application or formula acceptance."
    )
    return InterventionTrialResult(
        brief_name=request.brief_name,
        material=request.material,
        target_active_ppm_w_w=request.target_active_ppm_w_w,
        achieved_active_ppm_w_w=achieved_ppm,
        odt_ethanol_ppm=odt,
        oav=oav_value,
        addition=addition,
        safety_status=SafetyAssessmentStatus.UNVERIFIED,
        evaluation_protocol=protocol,
        evidence={
            "odt_oav": odt_evidence,
            "safety": EvidenceDescriptor(
                classification=ScientificClass.UNKNOWN,
                basis="No versioned category-specific safety dataset was supplied.",
                sources=("engine.safety_assessment",),
                limitations=(
                    "This plan is not an IFRA certificate or permission for skin application.",
                ),
            ),
            "evaluation_protocol": EvidenceDescriptor(
                classification=ScientificClass.LITERATURE_DERIVED,
                basis=(
                    "Paired directional comparison with one prespecified sensory attribute."
                ),
                sources=("https://www.iso.org/standard/31621.html",),
                assumptions=(
                    "Control and candidate aliquots differ only by the planned intervention.",
                    "Application and observation conditions are matched.",
                ),
                limitations=(
                    "A paired comparison establishes direction of a perceptible difference, "
                    "not effect size, causal mechanism, or general preference.",
                ),
            ),
        },
        warnings=tuple(warnings),
    )


def _odt_oav(
    material: str,
    achieved_ppm: float,
    threshold_matrix: str,
) -> tuple[float | None, float | None, EvidenceDescriptor, str | None]:
    if threshold_matrix != "ethanol":
        reason = "OAV withheld because the threshold matrix was not declared as ethanol."
        return None, None, _unknown_odt_evidence(reason), reason

    resolved = resolve_material(material)
    if (
        get_constituents(material) is not None
        or get_constituents(resolved.canonical_name) is not None
        or _looks_like_composite(material)
    ):
        reason = (
            "OAV withheld for a natural or composite material; composite headspace OAV "
            "requires the complete formula mixture state."
        )
        return None, None, _unknown_odt_evidence(reason), reason

    collisions = odt_collision_names(material)
    if collisions:
        reason = "OAV withheld because normalized ODT entries collide: " + ", ".join(
            collisions
        )
        return None, None, _unknown_odt_evidence(reason), reason

    entry = lookup_odt_entry(material)
    if entry is None:
        reason = "OAV withheld because no ethanol ODT record exists for the material."
        return None, None, _unknown_odt_evidence(reason), reason
    try:
        odt = float(entry.get("odt_eth"))
    except (TypeError, ValueError):
        odt = 0.0
    if not isfinite(odt) or odt <= 0:
        reason = "OAV withheld because the ethanol ODT is missing or nonpositive."
        return None, None, _unknown_odt_evidence(reason), reason

    verification = verify_odt(material) or entry
    verification_class = str(verification.get("vfy", entry.get("vfy", "UNVERIFIED")))
    classification = (
        ScientificClass.LITERATURE_DERIVED
        if verification_class in {"PEER_CROSS", "PEER_SINGLE"}
        else ScientificClass.HEURISTIC
    )
    sources = _source_strings(verification.get("sources") or entry.get("sources"))
    return (
        odt,
        achieved_ppm / odt,
        EvidenceDescriptor(
            classification=classification,
            basis=(
                f"OAV = achieved active concentration ({achieved_ppm:.12g} ppm w/w) / "
                f"ethanol ODT ({odt:.12g} ppm); ODT verification={verification_class}."
            ),
            sources=("engine.odor_thresholds", *sources),
            assumptions=(
                "The finished trial matrix is sufficiently similar to the ethanol threshold matrix.",
            ),
            limitations=(
                "OAV is a threshold screening ratio, not a measured intensity or causal effect.",
                "Mixture suppression, adaptation, and individual sensitivity are not modeled here.",
            ),
        ),
        None,
    )


def _unknown_odt_evidence(reason: str) -> EvidenceDescriptor:
    return EvidenceDescriptor(
        classification=ScientificClass.UNKNOWN,
        basis=reason,
        sources=("engine.odor_thresholds",),
        limitations=(
            "No perceptibility claim may be made until a matrix-matched ODT or composite "
            "full-mixture calculation is available.",
        ),
    )


def _looks_like_composite(material: str) -> bool:
    tokens = set(re.findall(r"[a-z0-9]+", material.casefold()))
    return bool(
        tokens
        & {
            "absolute",
            "accord",
            "balsam",
            "base",
            "co2",
            "eo",
            "essential",
            "extract",
            "fleuressence",
            "fo",
            "fragrance",
            "ftec",
            "oil",
            "reconstitution",
            "resinoid",
            "tincture",
            "core",
        }
    )


def _source_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    return ()


__all__ = [
    "EvaluationProtocol",
    "InterventionTrialRequest",
    "InterventionTrialResult",
    "plan_intervention_trial",
]
