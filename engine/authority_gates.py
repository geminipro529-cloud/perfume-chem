"""Typed, claim-specific permission and authority gates.

No result in this module is a certification or a scientific release. The
evaluators return the most permissive statement supported by the supplied
dimensions and stable reasons for every refusal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from engine.quantities import ConcentrationBasis


class ActorType(str, Enum):
    AI_ASSISTANT = "AI_ASSISTANT"
    HUMAN_OPERATOR = "HUMAN_OPERATOR"
    HUMAN_REVIEWER = "HUMAN_REVIEWER"
    ADMINISTRATOR = "ADMINISTRATOR"
    INSTRUMENT_IMPORT_SERVICE = "INSTRUMENT_IMPORT_SERVICE"
    AUTOMATED_VERIFIER = "AUTOMATED_VERIFIER"


class ActionState(str, Enum):
    PROPOSED = "PROPOSED"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    MEASURED = "MEASURED"
    COMMITTED = "COMMITTED"
    CORRECTED = "CORRECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OperatingMode(str, Enum):
    RECONSTRUCTION = "RECONSTRUCTION"
    CREATIVE_FORMULATION = "CREATIVE_FORMULATION"
    STRUCTURAL_CHASSIS = "STRUCTURAL_CHASSIS"
    FLANKER_MODULE = "FLANKER_MODULE"
    INVENTORY_MAPPING = "INVENTORY_MAPPING"
    LIVE_BATCH = "LIVE_BATCH"
    BATCH_RESCUE = "BATCH_RESCUE"
    SENSORY_EXPERIMENT = "SENSORY_EXPERIMENT"
    ANALYTICAL_INTERPRETATION = "ANALYTICAL_INTERPRETATION"
    COMPLIANCE_BUILD = "COMPLIANCE_BUILD"
    RELEASE_REVIEW = "RELEASE_REVIEW"


class ModeAction(str, Enum):
    EVIDENCE_CAPTURE = "EVIDENCE_CAPTURE"
    IDENTITY_HYPOTHESES = "IDENTITY_HYPOTHESES"
    RANK_PRIORS = "RANK_PRIORS"
    UNCERTAINTY_ENSEMBLES = "UNCERTAINTY_ENSEMBLES"
    ANTI_COMPRESSION = "ANTI_COMPRESSION"
    TARGET_VERSION = "TARGET_VERSION"
    REPORT = "REPORT"
    BRIEF_CONTRACT = "BRIEF_CONTRACT"
    FAMILY_ARCHETYPE = "FAMILY_ARCHETYPE"
    FUNCTIONAL_GRAPH = "FUNCTIONAL_GRAPH"
    CANDIDATE_GENERATION = "CANDIDATE_GENERATION"
    RECOGNIZER_SCORING = "RECOGNIZER_SCORING"
    REMOVAL_CURVES = "REMOVAL_CURVES"
    ANCHOR_FLOORS = "ANCHOR_FLOORS"
    SOCKETS = "SOCKETS"
    COMPENSATION_VECTORS = "COMPENSATION_VECTORS"
    RECOMBINATION_VALIDATION = "RECOMBINATION_VALIDATION"
    MODULE_ENVELOPE = "MODULE_ENVELOPE"
    DRIFT_CHECKS = "DRIFT_CHECKS"
    LOT_MATCHING = "LOT_MATCHING"
    STOCK_BASIS_CONVERSION = "STOCK_BASIS_CONVERSION"
    SUBSTITUTION = "SUBSTITUTION"
    MEASURABLE_BUILD_DRAFT = "MEASURABLE_BUILD_DRAFT"
    RESERVATION = "RESERVATION"
    PROPOSE_ACTION = "PROPOSE_ACTION"
    CAPTURE_CONFIRMATION = "CAPTURE_CONFIRMATION"
    MEASUREMENT = "MEASUREMENT"
    ATOMIC_COMMIT = "ATOMIC_COMMIT"
    REPLAY = "REPLAY"
    STATE_DIFF = "STATE_DIFF"
    CAUSE_ANALYSIS = "CAUSE_ANALYSIS"
    RESCUE_PROPOSAL = "RESCUE_PROPOSAL"
    STOP_CONDITION = "STOP_CONDITION"
    CORRECTION_EVENT = "CORRECTION_EVENT"
    PROTOCOL_VERSION = "PROTOCOL_VERSION"
    SAMPLE_CODES = "SAMPLE_CODES"
    RANDOMIZATION = "RANDOMIZATION"
    TIMED_OBSERVATION = "TIMED_OBSERVATION"
    OUTCOME = "OUTCOME"
    MISMATCH_EVIDENCE = "MISMATCH_EVIDENCE"
    METHOD_RECORD = "METHOD_RECORD"
    PEAK_RECORD = "PEAK_RECORD"
    IDENTITY_CANDIDATE = "IDENTITY_CANDIDATE"
    CALIBRATED_CONCENTRATION = "CALIBRATED_CONCENTRATION"
    EVIDENCE_CLAIM = "EVIDENCE_CLAIM"
    SCOPE_SNAPSHOT = "SCOPE_SNAPSHOT"
    CONSTITUENT_AGGREGATION = "CONSTITUENT_AGGREGATION"
    UNKNOWN_REPORT = "UNKNOWN_REPORT"
    COMPLIANT_VARIANT = "COMPLIANT_VARIANT"
    READ_ONLY_REVIEW = "READ_ONLY_REVIEW"
    CLAIM_DECISION = "CLAIM_DECISION"
    HUMAN_TRANSITION = "HUMAN_TRANSITION"
    TARGET_REWRITE = "TARGET_REWRITE"
    FORMULA_MUTATION = "FORMULA_MUTATION"
    CERTIFICATION = "CERTIFICATION"


class ClaimType(str, Enum):
    EXACT_MASS_BALANCE = "EXACT_MASS_BALANCE"
    IDENTITY = "IDENTITY"
    ACTIVE_CONCENTRATION = "ACTIVE_CONCENTRATION"
    ABOVE_THRESHOLD_LIKELIHOOD = "ABOVE_THRESHOLD_LIKELIHOOD"
    SENSORY_INTENSITY = "SENSORY_INTENSITY"
    TARGET_SIMILARITY = "TARGET_SIMILARITY"
    FAMILY_PRESERVATION = "FAMILY_PRESERVATION"
    REGULATORY_SCREEN = "REGULATORY_SCREEN"
    RELEASE = "RELEASE"


class ClaimDecision(str, Enum):
    ALLOW_EXACT = "ALLOW_EXACT"
    ALLOW_SCOPED = "ALLOW_SCOPED"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    WITHHOLD_UNKNOWN = "WITHHOLD_UNKNOWN"
    BLOCK = "BLOCK"


class RegulatoryDecision(str, Enum):
    PASS_FOR_DECLARED_SCOPE = "PASS_FOR_DECLARED_SCOPE"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_EVALUATED = "NOT_EVALUATED"


class GateReason(str, Enum):
    UNKNOWN_MODE = "UNKNOWN_MODE"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    ACTION_NOT_ALLOWED_IN_MODE = "ACTION_NOT_ALLOWED_IN_MODE"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    ACTOR_NOT_AUTHORIZED = "ACTOR_NOT_AUTHORIZED"
    AI_SELF_RELEASE_BLOCKED = "AI_SELF_RELEASE_BLOCKED"
    HUMAN_CONFIRMATION_REQUIRED = "HUMAN_CONFIRMATION_REQUIRED"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    SAFETY_NOT_CLEARED = "SAFETY_NOT_CLEARED"
    TARGET_ROW_COVERAGE_INCOMPLETE = "TARGET_ROW_COVERAGE_INCOMPLETE"
    SOURCE_COVERAGE_INCOMPLETE = "SOURCE_COVERAGE_INCOMPLETE"
    SOURCE_INDEPENDENCE_MISSING = "SOURCE_INDEPENDENCE_MISSING"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    QUANTITY_BASIS_INCOMPLETE = "QUANTITY_BASIS_INCOMPLETE"
    MISSING_ACTIVE_FRACTION = "MISSING_ACTIVE_FRACTION"
    MISSING_DENSITY = "MISSING_DENSITY"
    UNCERTAINTY_UNBOUNDED = "UNCERTAINTY_UNBOUNDED"
    CONTRADICTION_PRESENT = "CONTRADICTION_PRESENT"
    METHOD_NOT_VALIDATED = "METHOD_NOT_VALIDATED"
    ANALYTICAL_SUPPORT_MISSING = "ANALYTICAL_SUPPORT_MISSING"
    SENSORY_SUPPORT_MISSING = "SENSORY_SUPPORT_MISSING"
    MODEL_NOT_APPLICABLE = "MODEL_NOT_APPLICABLE"
    SAFETY_INCOMPLETE = "SAFETY_INCOMPLETE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    FAMILY_UNDEFINED = "FAMILY_UNDEFINED"
    FAMILY_EVIDENCE_MISSING = "FAMILY_EVIDENCE_MISSING"
    FAMILY_DRIFT_EXCEEDED = "FAMILY_DRIFT_EXCEEDED"
    GENRE_SHIFT = "GENRE_SHIFT"
    SNAPSHOT_INCOMPLETE = "SNAPSHOT_INCOMPLETE"
    STANDARD_NOT_FORMAL_EFFECTIVE = "STANDARD_NOT_FORMAL_EFFECTIVE"
    CRITICAL_UNKNOWN = "CRITICAL_UNKNOWN"
    REGULATORY_FAILURE = "REGULATORY_FAILURE"


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    allowed: bool
    decision: ClaimDecision | RegulatoryDecision | None = None
    reasons: tuple[GateReason, ...] = ()


@dataclass(frozen=True, slots=True)
class PermissionContext:
    actor: ActorType
    mode: OperatingMode
    current_state: ActionState
    requested_state: ActionState
    evidence_complete: bool
    safety_clear: bool
    human_confirmed: bool


@dataclass(frozen=True, slots=True)
class ClaimAuthorityInput:
    claim_type: ClaimType
    target_row_coverage_complete: bool
    source_coverage_complete: bool
    source_independence: bool
    identity_resolved: bool
    quantity_basis_complete: bool
    uncertainty_bounded: bool
    contradiction_present: bool
    method_validated: bool
    analytical_support: bool
    sensory_support: bool
    model_applicable: bool
    safety_complete: bool
    family_defined: bool
    family_evidence_complete: bool
    human_reviewed: bool
    scope_defined: bool
    exact_evidence: bool
    documentary_support: bool

    @classmethod
    def from_mapping(
        cls,
        claim_type: ClaimType | str,
        values: Mapping[str, Any],
    ) -> ClaimAuthorityInput:
        normalized_type = _claim_type(claim_type)
        fields = (
            "target_row_coverage_complete",
            "source_coverage_complete",
            "source_independence",
            "identity_resolved",
            "quantity_basis_complete",
            "uncertainty_bounded",
            "contradiction_present",
            "method_validated",
            "analytical_support",
            "sensory_support",
            "model_applicable",
            "safety_complete",
            "family_defined",
            "family_evidence_complete",
            "human_reviewed",
            "scope_defined",
            "exact_evidence",
            "documentary_support",
        )
        return cls(
            claim_type=normalized_type,
            **{
                name: values.get(name) is True
                for name in fields
            },
        )


@dataclass(frozen=True, slots=True)
class FamilyEvaluationInput:
    archetype_version: str | None
    protected_anchors: tuple[str, ...]
    allowed_uncertainty: float
    genre_shifting_materials: tuple[str, ...]
    target_values: Mapping[str, float]
    current_values: Mapping[str, float]
    unknowns: tuple[str, ...]
    evidence_complete: bool

    def __post_init__(self) -> None:
        uncertainty = float(self.allowed_uncertainty)
        if not isfinite(uncertainty) or uncertainty < 0:
            raise ValueError("allowed family uncertainty must be nonnegative")
        object.__setattr__(self, "allowed_uncertainty", uncertainty)


@dataclass(frozen=True, slots=True)
class ConcentrationGateInput:
    active_fraction: float | None
    basis: ConcentrationBasis | None
    density_required: bool
    density_present: bool
    carrier_present: bool

    def __post_init__(self) -> None:
        if self.active_fraction is not None:
            fraction = float(self.active_fraction)
            if not isfinite(fraction) or not 0 <= fraction <= 1:
                raise ValueError("active fraction must be between zero and one")
            object.__setattr__(self, "active_fraction", fraction)


@dataclass(frozen=True, slots=True)
class RegulatorySnapshot:
    standard_identifier: str
    amendment: str
    source_digest: str
    standard_state: str
    product_category: str
    jurisdiction: str
    formula_version: str
    constituent_basis: str
    natural_assumptions: tuple[str, ...]
    evaluation_date: date
    evaluator_version: str
    unresolved_items: tuple[str, ...]
    has_violation: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "standard_state",
            str(self.standard_state).strip().upper(),
        )


_MODE_ALLOWLIST: dict[OperatingMode, frozenset[ModeAction]] = {
    OperatingMode.RECONSTRUCTION: frozenset(
        {
            ModeAction.EVIDENCE_CAPTURE,
            ModeAction.IDENTITY_HYPOTHESES,
            ModeAction.RANK_PRIORS,
            ModeAction.UNCERTAINTY_ENSEMBLES,
            ModeAction.ANTI_COMPRESSION,
            ModeAction.TARGET_VERSION,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.CREATIVE_FORMULATION: frozenset(
        {
            ModeAction.BRIEF_CONTRACT,
            ModeAction.FAMILY_ARCHETYPE,
            ModeAction.FUNCTIONAL_GRAPH,
            ModeAction.CANDIDATE_GENERATION,
            ModeAction.TARGET_VERSION,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.STRUCTURAL_CHASSIS: frozenset(
        {
            ModeAction.RECOGNIZER_SCORING,
            ModeAction.REMOVAL_CURVES,
            ModeAction.ANCHOR_FLOORS,
            ModeAction.SOCKETS,
            ModeAction.COMPENSATION_VECTORS,
            ModeAction.RECOMBINATION_VALIDATION,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.FLANKER_MODULE: frozenset(
        {
            ModeAction.MODULE_ENVELOPE,
            ModeAction.SOCKETS,
            ModeAction.DRIFT_CHECKS,
            ModeAction.TARGET_VERSION,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.INVENTORY_MAPPING: frozenset(
        {
            ModeAction.LOT_MATCHING,
            ModeAction.STOCK_BASIS_CONVERSION,
            ModeAction.SUBSTITUTION,
            ModeAction.MEASURABLE_BUILD_DRAFT,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.LIVE_BATCH: frozenset(
        {
            ModeAction.RESERVATION,
            ModeAction.PROPOSE_ACTION,
            ModeAction.CAPTURE_CONFIRMATION,
            ModeAction.MEASUREMENT,
            ModeAction.ATOMIC_COMMIT,
            ModeAction.REPLAY,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.BATCH_RESCUE: frozenset(
        {
            ModeAction.STATE_DIFF,
            ModeAction.CAUSE_ANALYSIS,
            ModeAction.RESCUE_PROPOSAL,
            ModeAction.STOP_CONDITION,
            ModeAction.CORRECTION_EVENT,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.SENSORY_EXPERIMENT: frozenset(
        {
            ModeAction.PROTOCOL_VERSION,
            ModeAction.SAMPLE_CODES,
            ModeAction.RANDOMIZATION,
            ModeAction.TIMED_OBSERVATION,
            ModeAction.OUTCOME,
            ModeAction.MISMATCH_EVIDENCE,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.ANALYTICAL_INTERPRETATION: frozenset(
        {
            ModeAction.METHOD_RECORD,
            ModeAction.PEAK_RECORD,
            ModeAction.IDENTITY_CANDIDATE,
            ModeAction.CALIBRATED_CONCENTRATION,
            ModeAction.EVIDENCE_CLAIM,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.COMPLIANCE_BUILD: frozenset(
        {
            ModeAction.SCOPE_SNAPSHOT,
            ModeAction.CONSTITUENT_AGGREGATION,
            ModeAction.UNKNOWN_REPORT,
            ModeAction.COMPLIANT_VARIANT,
            ModeAction.REPORT,
        }
    ),
    OperatingMode.RELEASE_REVIEW: frozenset(
        {
            ModeAction.READ_ONLY_REVIEW,
            ModeAction.CLAIM_DECISION,
            ModeAction.HUMAN_TRANSITION,
            ModeAction.REPORT,
        }
    ),
}

_TRANSITIONS: dict[ActionState, frozenset[ActionState]] = {
    ActionState.PROPOSED: frozenset(
        {ActionState.REVIEWED, ActionState.CANCELLED, ActionState.FAILED}
    ),
    ActionState.REVIEWED: frozenset(
        {ActionState.CONFIRMED, ActionState.CANCELLED, ActionState.FAILED}
    ),
    ActionState.CONFIRMED: frozenset(
        {ActionState.MEASURED, ActionState.CANCELLED, ActionState.FAILED}
    ),
    ActionState.MEASURED: frozenset(
        {ActionState.COMMITTED, ActionState.FAILED}
    ),
    ActionState.COMMITTED: frozenset({ActionState.CORRECTED}),
    ActionState.CORRECTED: frozenset(),
    ActionState.CANCELLED: frozenset(),
    ActionState.FAILED: frozenset(),
}

_ACTORS_BY_STATE: dict[ActionState, frozenset[ActorType]] = {
    ActionState.REVIEWED: frozenset(
        {
            ActorType.HUMAN_OPERATOR,
            ActorType.HUMAN_REVIEWER,
            ActorType.ADMINISTRATOR,
            ActorType.AUTOMATED_VERIFIER,
        }
    ),
    ActionState.CONFIRMED: frozenset(
        {
            ActorType.HUMAN_OPERATOR,
            ActorType.HUMAN_REVIEWER,
            ActorType.ADMINISTRATOR,
        }
    ),
    ActionState.MEASURED: frozenset(
        {
            ActorType.HUMAN_OPERATOR,
            ActorType.INSTRUMENT_IMPORT_SERVICE,
            ActorType.ADMINISTRATOR,
        }
    ),
    ActionState.COMMITTED: frozenset(
        {ActorType.HUMAN_OPERATOR, ActorType.ADMINISTRATOR}
    ),
    ActionState.CORRECTED: frozenset(
        {ActorType.HUMAN_OPERATOR, ActorType.ADMINISTRATOR}
    ),
    ActionState.CANCELLED: frozenset(
        {
            ActorType.HUMAN_OPERATOR,
            ActorType.HUMAN_REVIEWER,
            ActorType.ADMINISTRATOR,
        }
    ),
    ActionState.FAILED: frozenset(ActorType),
}

_CLAIM_REQUIREMENTS: dict[
    ClaimType, tuple[tuple[str, GateReason], ...]
] = {
    ClaimType.EXACT_MASS_BALANCE: (
        (
            "target_row_coverage_complete",
            GateReason.TARGET_ROW_COVERAGE_INCOMPLETE,
        ),
        ("source_coverage_complete", GateReason.SOURCE_COVERAGE_INCOMPLETE),
        ("identity_resolved", GateReason.IDENTITY_UNRESOLVED),
        ("quantity_basis_complete", GateReason.QUANTITY_BASIS_INCOMPLETE),
        ("uncertainty_bounded", GateReason.UNCERTAINTY_UNBOUNDED),
    ),
    ClaimType.IDENTITY: (
        ("source_coverage_complete", GateReason.SOURCE_COVERAGE_INCOMPLETE),
        ("source_independence", GateReason.SOURCE_INDEPENDENCE_MISSING),
        ("identity_resolved", GateReason.IDENTITY_UNRESOLVED),
    ),
    ClaimType.ACTIVE_CONCENTRATION: (
        (
            "target_row_coverage_complete",
            GateReason.TARGET_ROW_COVERAGE_INCOMPLETE,
        ),
        ("source_coverage_complete", GateReason.SOURCE_COVERAGE_INCOMPLETE),
        ("identity_resolved", GateReason.IDENTITY_UNRESOLVED),
        ("quantity_basis_complete", GateReason.QUANTITY_BASIS_INCOMPLETE),
        ("uncertainty_bounded", GateReason.UNCERTAINTY_UNBOUNDED),
    ),
    ClaimType.ABOVE_THRESHOLD_LIKELIHOOD: (
        ("source_coverage_complete", GateReason.SOURCE_COVERAGE_INCOMPLETE),
        ("identity_resolved", GateReason.IDENTITY_UNRESOLVED),
        ("quantity_basis_complete", GateReason.QUANTITY_BASIS_INCOMPLETE),
        ("uncertainty_bounded", GateReason.UNCERTAINTY_UNBOUNDED),
        ("model_applicable", GateReason.MODEL_NOT_APPLICABLE),
    ),
    ClaimType.SENSORY_INTENSITY: (
        ("source_coverage_complete", GateReason.SOURCE_COVERAGE_INCOMPLETE),
        ("method_validated", GateReason.METHOD_NOT_VALIDATED),
        ("sensory_support", GateReason.SENSORY_SUPPORT_MISSING),
    ),
    ClaimType.TARGET_SIMILARITY: (
        (
            "target_row_coverage_complete",
            GateReason.TARGET_ROW_COVERAGE_INCOMPLETE,
        ),
        ("source_independence", GateReason.SOURCE_INDEPENDENCE_MISSING),
        ("method_validated", GateReason.METHOD_NOT_VALIDATED),
        ("sensory_support", GateReason.SENSORY_SUPPORT_MISSING),
    ),
    ClaimType.FAMILY_PRESERVATION: (
        ("family_defined", GateReason.FAMILY_UNDEFINED),
        ("family_evidence_complete", GateReason.FAMILY_EVIDENCE_MISSING),
        (
            "target_row_coverage_complete",
            GateReason.TARGET_ROW_COVERAGE_INCOMPLETE,
        ),
    ),
    ClaimType.REGULATORY_SCREEN: (
        ("source_coverage_complete", GateReason.SOURCE_COVERAGE_INCOMPLETE),
        ("identity_resolved", GateReason.IDENTITY_UNRESOLVED),
        ("quantity_basis_complete", GateReason.QUANTITY_BASIS_INCOMPLETE),
        ("uncertainty_bounded", GateReason.UNCERTAINTY_UNBOUNDED),
        ("safety_complete", GateReason.SAFETY_INCOMPLETE),
    ),
    ClaimType.RELEASE: (
        (
            "target_row_coverage_complete",
            GateReason.TARGET_ROW_COVERAGE_INCOMPLETE,
        ),
        ("source_coverage_complete", GateReason.SOURCE_COVERAGE_INCOMPLETE),
        ("source_independence", GateReason.SOURCE_INDEPENDENCE_MISSING),
        ("identity_resolved", GateReason.IDENTITY_UNRESOLVED),
        ("quantity_basis_complete", GateReason.QUANTITY_BASIS_INCOMPLETE),
        ("uncertainty_bounded", GateReason.UNCERTAINTY_UNBOUNDED),
        ("method_validated", GateReason.METHOD_NOT_VALIDATED),
        ("analytical_support", GateReason.ANALYTICAL_SUPPORT_MISSING),
        ("sensory_support", GateReason.SENSORY_SUPPORT_MISSING),
        ("model_applicable", GateReason.MODEL_NOT_APPLICABLE),
        ("safety_complete", GateReason.SAFETY_INCOMPLETE),
        ("human_reviewed", GateReason.HUMAN_REVIEW_REQUIRED),
    ),
}

_DECISION_RANK = {
    ClaimDecision.BLOCK: 0,
    ClaimDecision.WITHHOLD_UNKNOWN: 1,
    ClaimDecision.ADVISORY_ONLY: 2,
    ClaimDecision.ALLOW_SCOPED: 3,
    ClaimDecision.ALLOW_EXACT: 4,
}


def evaluate_mode_action(
    mode: OperatingMode | str,
    action: ModeAction | str,
) -> GateEvaluation:
    try:
        normalized_mode = OperatingMode(mode)
    except ValueError:
        return GateEvaluation(False, reasons=(GateReason.UNKNOWN_MODE,))
    try:
        normalized_action = ModeAction(action)
    except ValueError:
        return GateEvaluation(False, reasons=(GateReason.UNKNOWN_ACTION,))
    if normalized_action not in _MODE_ALLOWLIST[normalized_mode]:
        return GateEvaluation(
            False,
            reasons=(GateReason.ACTION_NOT_ALLOWED_IN_MODE,),
        )
    return GateEvaluation(True)


def evaluate_transition(context: PermissionContext) -> GateEvaluation:
    if context.requested_state not in _TRANSITIONS[context.current_state]:
        return GateEvaluation(
            False,
            reasons=(GateReason.INVALID_STATE_TRANSITION,),
        )
    reasons: list[GateReason] = []
    if context.actor not in _ACTORS_BY_STATE.get(
        context.requested_state, frozenset()
    ):
        reasons.append(GateReason.ACTOR_NOT_AUTHORIZED)
    if (
        context.actor is ActorType.AI_ASSISTANT
        and context.mode is OperatingMode.RELEASE_REVIEW
    ):
        reasons.append(GateReason.AI_SELF_RELEASE_BLOCKED)
    if context.requested_state in {
        ActionState.CONFIRMED,
        ActionState.COMMITTED,
        ActionState.CORRECTED,
    }:
        if not context.evidence_complete:
            reasons.append(GateReason.EVIDENCE_INCOMPLETE)
        if not context.safety_clear:
            reasons.append(GateReason.SAFETY_NOT_CLEARED)
        if not context.human_confirmed:
            reasons.append(GateReason.HUMAN_CONFIRMATION_REQUIRED)
    elif context.requested_state is ActionState.MEASURED:
        if not context.human_confirmed:
            reasons.append(GateReason.HUMAN_CONFIRMATION_REQUIRED)
    return GateEvaluation(not reasons, reasons=tuple(reasons))


def evaluate_claim_authority(
    authority: ClaimAuthorityInput,
) -> GateEvaluation:
    if authority.contradiction_present:
        return GateEvaluation(
            False,
            ClaimDecision.BLOCK,
            (GateReason.CONTRADICTION_PRESENT,),
        )
    reasons = tuple(
        reason
        for field_name, reason in _CLAIM_REQUIREMENTS[authority.claim_type]
        if getattr(authority, field_name) is not True
    )
    if reasons:
        return GateEvaluation(
            False,
            ClaimDecision.WITHHOLD_UNKNOWN,
            reasons,
        )
    if authority.exact_evidence:
        return GateEvaluation(True, ClaimDecision.ALLOW_EXACT)
    if authority.scope_defined:
        return GateEvaluation(True, ClaimDecision.ALLOW_SCOPED)
    if authority.documentary_support:
        return GateEvaluation(True, ClaimDecision.ADVISORY_ONLY)
    return GateEvaluation(
        False,
        ClaimDecision.WITHHOLD_UNKNOWN,
        (GateReason.EVIDENCE_INCOMPLETE,),
    )


def decision_within_authority(
    requested: ClaimDecision | str,
    maximum: ClaimDecision,
) -> bool:
    try:
        normalized = ClaimDecision(requested)
    except ValueError:
        return False
    return _DECISION_RANK[normalized] <= _DECISION_RANK[maximum]


def evaluate_family_gate(
    family: FamilyEvaluationInput,
) -> GateEvaluation:
    if not (family.archetype_version or "").strip():
        return GateEvaluation(
            False,
            ClaimDecision.WITHHOLD_UNKNOWN,
            (GateReason.FAMILY_UNDEFINED,),
        )
    reasons: list[GateReason] = []
    if not family.evidence_complete or family.unknowns:
        reasons.append(GateReason.FAMILY_EVIDENCE_MISSING)
    for anchor in family.protected_anchors:
        if anchor not in family.target_values or anchor not in family.current_values:
            if GateReason.FAMILY_EVIDENCE_MISSING not in reasons:
                reasons.append(GateReason.FAMILY_EVIDENCE_MISSING)
            continue
        if (
            abs(
                float(family.current_values[anchor])
                - float(family.target_values[anchor])
            )
            > family.allowed_uncertainty
        ):
            reasons.append(GateReason.FAMILY_DRIFT_EXCEEDED)
            break
    if any(
        float(family.current_values.get(material, 0.0)) > 0
        for material in family.genre_shifting_materials
    ):
        reasons.append(GateReason.GENRE_SHIFT)
    reasons = list(dict.fromkeys(reasons))
    if any(
        reason
        in {GateReason.FAMILY_DRIFT_EXCEEDED, GateReason.GENRE_SHIFT}
        for reason in reasons
    ):
        return GateEvaluation(False, ClaimDecision.BLOCK, tuple(reasons))
    if reasons:
        return GateEvaluation(
            False,
            ClaimDecision.WITHHOLD_UNKNOWN,
            tuple(reasons),
        )
    return GateEvaluation(True, ClaimDecision.ALLOW_SCOPED)


def evaluate_concentration_gate(
    concentration: ConcentrationGateInput,
) -> GateEvaluation:
    reasons: list[GateReason] = []
    if concentration.basis is None:
        reasons.append(GateReason.QUANTITY_BASIS_INCOMPLETE)
    if concentration.active_fraction is None:
        reasons.append(GateReason.MISSING_ACTIVE_FRACTION)
    if concentration.density_required and not concentration.density_present:
        reasons.append(GateReason.MISSING_DENSITY)
    if reasons:
        return GateEvaluation(
            False,
            ClaimDecision.WITHHOLD_UNKNOWN,
            tuple(reasons),
        )
    return GateEvaluation(True, ClaimDecision.ALLOW_SCOPED)


def evaluate_regulatory_gate(
    snapshot: RegulatorySnapshot,
) -> GateEvaluation:
    if snapshot.has_violation:
        return GateEvaluation(
            False,
            RegulatoryDecision.FAIL,
            (GateReason.REGULATORY_FAILURE,),
        )
    if snapshot.standard_state == "DRAFT":
        return GateEvaluation(
            False,
            RegulatoryDecision.NOT_EVALUATED,
            (GateReason.STANDARD_NOT_FORMAL_EFFECTIVE,),
        )
    if snapshot.standard_state != "EFFECTIVE":
        return GateEvaluation(
            False,
            RegulatoryDecision.UNKNOWN,
            (GateReason.STANDARD_NOT_FORMAL_EFFECTIVE,),
        )
    required_text = (
        snapshot.standard_identifier,
        snapshot.amendment,
        snapshot.product_category,
        snapshot.jurisdiction,
        snapshot.formula_version,
        snapshot.constituent_basis,
        snapshot.evaluator_version,
    )
    if any(not str(value).strip() for value in required_text) or not re.fullmatch(
        r"[0-9a-f]{64}", snapshot.source_digest
    ):
        return GateEvaluation(
            False,
            RegulatoryDecision.UNKNOWN,
            (GateReason.SNAPSHOT_INCOMPLETE,),
        )
    if snapshot.unresolved_items:
        return GateEvaluation(
            False,
            RegulatoryDecision.UNKNOWN,
            (GateReason.CRITICAL_UNKNOWN,),
        )
    return GateEvaluation(
        True,
        RegulatoryDecision.PASS_FOR_DECLARED_SCOPE,
    )


def _claim_type(value: ClaimType | str) -> ClaimType:
    aliases = {
        "FORMULA_IDENTITY": ClaimType.IDENTITY,
        "ANALYTICAL_IDENTITY": ClaimType.IDENTITY,
        "RELEASE_REVIEW": ClaimType.RELEASE,
    }
    if isinstance(value, ClaimType):
        return value
    normalized = str(value).strip().upper()
    try:
        return ClaimType(normalized)
    except ValueError:
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(
                f"unsupported claim authority type: {value}"
            ) from exc


__all__ = [
    "ActionState",
    "ActorType",
    "ClaimAuthorityInput",
    "ClaimDecision",
    "ClaimType",
    "ConcentrationGateInput",
    "FamilyEvaluationInput",
    "GateEvaluation",
    "GateReason",
    "ModeAction",
    "OperatingMode",
    "PermissionContext",
    "RegulatoryDecision",
    "RegulatorySnapshot",
    "decision_within_authority",
    "evaluate_claim_authority",
    "evaluate_concentration_gate",
    "evaluate_family_gate",
    "evaluate_mode_action",
    "evaluate_regulatory_gate",
    "evaluate_transition",
]
