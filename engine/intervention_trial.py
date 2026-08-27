"""Deterministic planning for a separate, measurable intervention trial."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from math import isfinite

from engine.bottle_addition import (
    AdditionRequest,
    AdditionResult,
    AdditionSolver,
    BottleSnapshot,
    PipetteProfile,
    StockSolution,
)
from engine.material_resolver import resolve_material
from engine.name_utils import names_match
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


@dataclass(frozen=True, slots=True)
class BatchRescueContext:
    """Provenance required before calculating an addition-only rescue trial."""

    batch_id: str
    formula_state_sha256: str
    immutable_ledger_complete: bool
    previous_additions_complete: bool
    observed_defect: str
    preserve_attributes: tuple[str, ...]
    stock_identity: str
    stock_fraction_basis: str
    stock_fraction_source: str
    stock_carrier: str
    stock_density_source: str
    bottle_mass_source: str
    product_category: str

    def __post_init__(self) -> None:
        for field_name in (
            "batch_id",
            "formula_state_sha256",
            "observed_defect",
            "stock_identity",
            "stock_fraction_basis",
            "stock_fraction_source",
            "stock_carrier",
            "stock_density_source",
            "bottle_mass_source",
            "product_category",
        ):
            object.__setattr__(
                self,
                field_name,
                str(getattr(self, field_name) or "").strip(),
            )
        object.__setattr__(
            self,
            "preserve_attributes",
            tuple(
                str(value).strip()
                for value in self.preserve_attributes
                if str(value).strip()
            ),
        )


@dataclass(frozen=True, slots=True)
class BatchRescueReadiness:
    status: str
    missing_inputs: tuple[str, ...]
    source_bottle_addition_authorized: bool
    separate_aliquot_plan_authorized: bool
    skin_application_authorized: bool
    next_action: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BatchRescuePlan:
    readiness: BatchRescueReadiness
    trial: InterventionTrialResult | None

    def as_dict(self) -> dict[str, object]:
        return {
            "readiness": self.readiness.as_dict(),
            "trial": self.trial.as_dict() if self.trial is not None else None,
        }


def assess_batch_rescue_readiness(
    context: BatchRescueContext,
    trial_request: InterventionTrialRequest,
) -> BatchRescueReadiness:
    """Fail closed unless the source state and candidate stock are traceable."""
    missing: list[str] = []
    if not context.batch_id:
        missing.append("batch_id")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", context.formula_state_sha256):
        missing.append("formula_state_sha256")
    if not context.immutable_ledger_complete:
        missing.append("immutable_ledger_complete")
    if not context.previous_additions_complete:
        missing.append("previous_additions_complete")
    if not context.observed_defect:
        missing.append("observed_defect")
    if not context.preserve_attributes:
        missing.append("preserve_attributes")
    if not context.stock_identity or not names_match(
        context.stock_identity, trial_request.material
    ):
        missing.append("stock_identity_matches_candidate")
    if context.stock_fraction_basis.casefold() not in {
        "neat",
        "mass_fraction",
        "mass_per_volume",
        "volume_fraction",
    }:
        missing.append("stock_fraction_basis")
    if not context.stock_fraction_source:
        missing.append("stock_fraction_source")
    if (
        trial_request.stock.active_mass_fraction < 1.0
        and not context.stock_carrier
    ):
        missing.append("stock_carrier")
    if trial_request.stock.density_g_ml is None:
        missing.append("stock_density_g_ml")
    if not context.stock_density_source:
        missing.append("stock_density_source")
    if not context.bottle_mass_source:
        missing.append("bottle_mass_source")
    if not context.product_category:
        missing.append("product_category")
    if trial_request.pipette is None:
        missing.append("pipette_profile")

    unique_missing = tuple(dict.fromkeys(missing))
    if unique_missing:
        return BatchRescueReadiness(
            status="NEEDS_INPUT",
            missing_inputs=unique_missing,
            source_bottle_addition_authorized=False,
            separate_aliquot_plan_authorized=False,
            skin_application_authorized=False,
            next_action=(
                "Complete the immutable batch and stock record; do not add to "
                "the source bottle."
            ),
        )
    return BatchRescueReadiness(
        status="ALIQUOT_INPUTS_READY",
        missing_inputs=(),
        source_bottle_addition_authorized=False,
        separate_aliquot_plan_authorized=True,
        skin_application_authorized=False,
        next_action=(
            "Calculate and prepare a separate coded non-skin aliquot; retain an "
            "unaltered control and do not modify the source bottle."
        ),
    )


def plan_finished_batch_rescue(
    context: BatchRescueContext,
    trial_request: InterventionTrialRequest,
    *,
    addition_solver: AdditionSolver | None = None,
) -> BatchRescuePlan:
    """Create an addition-only aliquot trial while keeping the bottle immutable."""
    readiness = assess_batch_rescue_readiness(context, trial_request)
    if not readiness.separate_aliquot_plan_authorized:
        return BatchRescuePlan(readiness=readiness, trial=None)

    trial = plan_intervention_trial(
        trial_request,
        addition_solver=addition_solver,
    )
    if not trial.addition.pipette_feasible:
        readiness = BatchRescueReadiness(
            status="ALIQUOT_PLAN_NOT_MEASURABLE",
            missing_inputs=("measurable_delivery_plan",),
            source_bottle_addition_authorized=False,
            separate_aliquot_plan_authorized=False,
            skin_application_authorized=False,
            next_action=(
                "Prepare a lower-concentration candidate stock or use calibrated "
                "equipment that can deliver the calculated amount."
            ),
        )
    else:
        readiness = BatchRescueReadiness(
            status="ALIQUOT_TRIAL_READY",
            missing_inputs=(),
            source_bottle_addition_authorized=False,
            separate_aliquot_plan_authorized=True,
            skin_application_authorized=False,
            next_action=readiness.next_action,
        )
    return BatchRescuePlan(readiness=readiness, trial=trial)


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
    "BatchRescueContext",
    "BatchRescuePlan",
    "BatchRescueReadiness",
    "EvaluationProtocol",
    "InterventionTrialRequest",
    "InterventionTrialResult",
    "assess_batch_rescue_readiness",
    "plan_finished_batch_rescue",
    "plan_intervention_trial",
]
