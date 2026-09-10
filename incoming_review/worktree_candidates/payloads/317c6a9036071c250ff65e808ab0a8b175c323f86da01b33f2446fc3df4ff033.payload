"""Prior-free evidence-value selection for the next perfume experiment.

The selector chooses zero or one admissible experiment.  It does not invent
outcome probabilities, convert composition into liking, or optimize a synthetic
beauty score.  When calibrated priors and predictive likelihoods are absent,
the contract uses conservative model discrimination: maximize the hypotheses
eliminated by the least informative declared outcome, then minimize burden.

Every result is experiment-design evidence only.  It grants no compounding,
formula, sensory, hedonic, safety, purchase, physical-execution, or release
authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Z][A-Z0-9_.:-]*$")

EVIDENCE_VALUE_AUTHORITY_FLAGS = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


class EvidenceValueState(str, Enum):
    """Selector outcome for one exact decision scope."""

    SELECTED = "SELECTED"
    NO_CHANGE = "NO_CHANGE"
    HOLD = "HOLD"


class ExperimentDomain(str, Enum):
    """Kinds of evidence-producing work, not perfume quality rankings."""

    EVIDENCE_AUDIT = "EVIDENCE_AUDIT"
    FORMULA_DELTA = "FORMULA_DELTA"
    TEMPORAL_OBSERVATION = "TEMPORAL_OBSERVATION"
    PAIRWISE_PREFERENCE = "PAIRWISE_PREFERENCE"
    NARY_INTERACTION = "NARY_INTERACTION"


class DecisionImpact(str, Enum):
    """Declared relation of a candidate to the pending decision."""

    BLOCKING = "BLOCKING"
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _identifier(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).upper()
    if not _IDENTIFIER_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a stable upper-case identifier")
    return normalized


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lower-case SHA-256 digest")
    return value


def _bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be boolean")
    return value


def _nonnegative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _nonnegative_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0:
        raise ValueError(f"{field_name} must be finite and nonnegative")
    return normalized


def _optional_limit(value: object, field_name: str, *, integer: bool) -> int | float | None:
    if value is None:
        return None
    if integer:
        return _nonnegative_int(value, field_name)
    return _nonnegative_number(value, field_name)


def _text_tuple(
    values: tuple[str, ...],
    field_name: str,
    *,
    identifiers: bool = False,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    normalizer = _identifier if identifiers else _text
    normalized = tuple(normalizer(value, field_name) for value in tuple(values))
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must be nonempty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


@dataclass(frozen=True, slots=True)
class ExperimentBurden:
    """Physical and operational burden, considered only after discrimination."""

    physical_sample_count: int = 0
    scarce_material_mg: float = 0.0
    total_active_material_mg: float = 0.0
    assessor_sessions: int = 0
    instrument_minutes: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "physical_sample_count",
            _nonnegative_int(self.physical_sample_count, "physical_sample_count"),
        )
        object.__setattr__(
            self,
            "scarce_material_mg",
            _nonnegative_number(self.scarce_material_mg, "scarce_material_mg"),
        )
        object.__setattr__(
            self,
            "total_active_material_mg",
            _nonnegative_number(
                self.total_active_material_mg,
                "total_active_material_mg",
            ),
        )
        object.__setattr__(
            self,
            "assessor_sessions",
            _nonnegative_int(self.assessor_sessions, "assessor_sessions"),
        )
        object.__setattr__(
            self,
            "instrument_minutes",
            _nonnegative_number(self.instrument_minutes, "instrument_minutes"),
        )

    def as_dict(self) -> dict[str, int | float]:
        return {
            "physical_sample_count": self.physical_sample_count,
            "scarce_material_mg": self.scarce_material_mg,
            "total_active_material_mg": self.total_active_material_mg,
            "assessor_sessions": self.assessor_sessions,
            "instrument_minutes": self.instrument_minutes,
        }


@dataclass(frozen=True, slots=True)
class ExperimentBudget:
    """Optional hard resource ceilings; absence does not imply infinite authority."""

    max_physical_sample_count: int | None = None
    max_scarce_material_mg: float | None = None
    max_total_active_material_mg: float | None = None
    max_assessor_sessions: int | None = None
    max_instrument_minutes: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_physical_sample_count",
            _optional_limit(
                self.max_physical_sample_count,
                "max_physical_sample_count",
                integer=True,
            ),
        )
        object.__setattr__(
            self,
            "max_scarce_material_mg",
            _optional_limit(
                self.max_scarce_material_mg,
                "max_scarce_material_mg",
                integer=False,
            ),
        )
        object.__setattr__(
            self,
            "max_total_active_material_mg",
            _optional_limit(
                self.max_total_active_material_mg,
                "max_total_active_material_mg",
                integer=False,
            ),
        )
        object.__setattr__(
            self,
            "max_assessor_sessions",
            _optional_limit(
                self.max_assessor_sessions,
                "max_assessor_sessions",
                integer=True,
            ),
        )
        object.__setattr__(
            self,
            "max_instrument_minutes",
            _optional_limit(
                self.max_instrument_minutes,
                "max_instrument_minutes",
                integer=False,
            ),
        )

    def as_dict(self) -> dict[str, int | float | None]:
        return {
            "max_physical_sample_count": self.max_physical_sample_count,
            "max_scarce_material_mg": self.max_scarce_material_mg,
            "max_total_active_material_mg": self.max_total_active_material_mg,
            "max_assessor_sessions": self.max_assessor_sessions,
            "max_instrument_minutes": self.max_instrument_minutes,
        }


@dataclass(frozen=True, slots=True)
class ExperimentOutcome:
    """One predeclared observable outcome and what it can falsify."""

    outcome_id: str
    eliminated_hypothesis_ids: tuple[str, ...]
    resolves_decision: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome_id", _identifier(self.outcome_id, "outcome_id"))
        object.__setattr__(
            self,
            "eliminated_hypothesis_ids",
            _text_tuple(
                self.eliminated_hypothesis_ids,
                "eliminated_hypothesis_ids",
                identifiers=True,
            ),
        )
        object.__setattr__(
            self,
            "resolves_decision",
            _bool(self.resolves_decision, "resolves_decision"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "outcome_id": self.outcome_id,
            "eliminated_hypothesis_ids": list(self.eliminated_hypothesis_ids),
            "resolves_decision": self.resolves_decision,
        }


@dataclass(frozen=True, slots=True)
class EvidenceValueCandidate:
    """A complete candidate experiment submitted before results are observed."""

    candidate_id: str
    source_receipt_sha256: str
    exact_scope_sha256: str
    criterion_id: str
    domain: ExperimentDomain
    decision_impact: DecisionImpact
    outcomes: tuple[ExperimentOutcome, ...]
    protocol_qualified: bool
    lineage_complete: bool
    inventory_executable: bool
    constant_total: bool
    blinded: bool
    isolated_arms_complete: bool
    physical_required: bool
    burden: ExperimentBurden
    safety_review_required: bool
    safety_review_complete: bool
    blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _text(self.candidate_id, "candidate_id"))
        for name in ("source_receipt_sha256", "exact_scope_sha256"):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        object.__setattr__(
            self,
            "criterion_id",
            _identifier(self.criterion_id, "criterion_id"),
        )
        object.__setattr__(self, "domain", ExperimentDomain(self.domain))
        object.__setattr__(
            self,
            "decision_impact",
            DecisionImpact(self.decision_impact),
        )
        outcomes = tuple(self.outcomes)
        if not outcomes or any(not isinstance(item, ExperimentOutcome) for item in outcomes):
            raise TypeError("outcomes must contain at least one ExperimentOutcome")
        outcome_ids = tuple(item.outcome_id for item in outcomes)
        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError("outcome_id must be unique within a candidate")
        object.__setattr__(self, "outcomes", outcomes)
        for name in (
            "protocol_qualified",
            "lineage_complete",
            "inventory_executable",
            "constant_total",
            "blinded",
            "isolated_arms_complete",
            "physical_required",
            "safety_review_required",
            "safety_review_complete",
        ):
            object.__setattr__(self, name, _bool(getattr(self, name), name))
        if not isinstance(self.burden, ExperimentBurden):
            raise TypeError("burden must be an ExperimentBurden")
        object.__setattr__(
            self,
            "blockers",
            _text_tuple(self.blockers, "blockers", identifiers=True),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "source_receipt_sha256": self.source_receipt_sha256,
            "exact_scope_sha256": self.exact_scope_sha256,
            "criterion_id": self.criterion_id,
            "domain": self.domain.value,
            "decision_impact": self.decision_impact.value,
            "outcomes": [item.as_dict() for item in self.outcomes],
            "protocol_qualified": self.protocol_qualified,
            "lineage_complete": self.lineage_complete,
            "inventory_executable": self.inventory_executable,
            "constant_total": self.constant_total,
            "blinded": self.blinded,
            "isolated_arms_complete": self.isolated_arms_complete,
            "physical_required": self.physical_required,
            "burden": self.burden.as_dict(),
            "safety_review_required": self.safety_review_required,
            "safety_review_complete": self.safety_review_complete,
            "blockers": list(self.blockers),
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


@dataclass(frozen=True, slots=True)
class EvidenceValueRequest:
    """Exact unresolved decision and the predeclared candidate set."""

    decision_id: str
    exact_scope_sha256: str
    criterion_id: str
    unresolved_hypothesis_ids: tuple[str, ...]
    predeclared_plan_sha256: str
    candidates: tuple[EvidenceValueCandidate, ...]
    decision_resolved: bool = False
    budget: ExperimentBudget = field(default_factory=ExperimentBudget)

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _text(self.decision_id, "decision_id"))
        object.__setattr__(
            self,
            "exact_scope_sha256",
            _sha256(self.exact_scope_sha256, "exact_scope_sha256"),
        )
        object.__setattr__(
            self,
            "criterion_id",
            _identifier(self.criterion_id, "criterion_id"),
        )
        hypotheses = _text_tuple(
            self.unresolved_hypothesis_ids,
            "unresolved_hypothesis_ids",
            identifiers=True,
            allow_empty=self.decision_resolved,
        )
        object.__setattr__(self, "unresolved_hypothesis_ids", hypotheses)
        object.__setattr__(
            self,
            "predeclared_plan_sha256",
            _sha256(self.predeclared_plan_sha256, "predeclared_plan_sha256"),
        )
        candidates = tuple(self.candidates)
        if any(not isinstance(item, EvidenceValueCandidate) for item in candidates):
            raise TypeError("candidates must contain EvidenceValueCandidate records")
        candidate_ids = tuple(item.candidate_id for item in candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate_id must be unique within a request")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(
            self,
            "decision_resolved",
            _bool(self.decision_resolved, "decision_resolved"),
        )
        if not isinstance(self.budget, ExperimentBudget):
            raise TypeError("budget must be an ExperimentBudget")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "evidence_value_request_v1",
            "decision_id": self.decision_id,
            "exact_scope_sha256": self.exact_scope_sha256,
            "criterion_id": self.criterion_id,
            "unresolved_hypothesis_ids": list(self.unresolved_hypothesis_ids),
            "predeclared_plan_sha256": self.predeclared_plan_sha256,
            "candidates": [
                item.as_dict()
                for item in sorted(self.candidates, key=lambda candidate: candidate.candidate_id)
            ],
            "decision_resolved": self.decision_resolved,
            "budget": self.budget.as_dict(),
            "authority_flags": dict(EVIDENCE_VALUE_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    candidate_id: str
    candidate_record_sha256: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _text(self.candidate_id, "candidate_id"))
        object.__setattr__(
            self,
            "candidate_record_sha256",
            _sha256(self.candidate_record_sha256, "candidate_record_sha256"),
        )
        object.__setattr__(
            self,
            "reasons",
            _text_tuple(self.reasons, "reasons", identifiers=True, allow_empty=False),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_record_sha256": self.candidate_record_sha256,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class CandidateEvidenceScore:
    """Auditable lexicographic evidence score; never a hedonic score."""

    candidate_id: str
    candidate_record_sha256: str
    worst_case_hypotheses_eliminated: int
    decision_resolving_outcome_count: int
    distinct_hypotheses_covered: int
    decision_impact: DecisionImpact
    physical_required: bool
    burden: ExperimentBurden

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _text(self.candidate_id, "candidate_id"))
        object.__setattr__(
            self,
            "candidate_record_sha256",
            _sha256(self.candidate_record_sha256, "candidate_record_sha256"),
        )
        for name in (
            "worst_case_hypotheses_eliminated",
            "decision_resolving_outcome_count",
            "distinct_hypotheses_covered",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        object.__setattr__(
            self,
            "decision_impact",
            DecisionImpact(self.decision_impact),
        )
        object.__setattr__(
            self,
            "physical_required",
            _bool(self.physical_required, "physical_required"),
        )
        if not isinstance(self.burden, ExperimentBurden):
            raise TypeError("burden must be an ExperimentBurden")

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_record_sha256": self.candidate_record_sha256,
            "worst_case_hypotheses_eliminated": (
                self.worst_case_hypotheses_eliminated
            ),
            "decision_resolving_outcome_count": self.decision_resolving_outcome_count,
            "distinct_hypotheses_covered": self.distinct_hypotheses_covered,
            "decision_impact": self.decision_impact.value,
            "physical_required": self.physical_required,
            "burden": self.burden.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class EvidenceValueResult:
    """One deterministic selection receipt with an all-false authority envelope."""

    SCHEMA_VERSION: ClassVar[str] = "evidence_value_result_v1"

    state: EvidenceValueState
    request_sha256: str
    decision_id: str
    exact_scope_sha256: str
    criterion_id: str
    predeclared_plan_sha256: str
    selected_candidate: EvidenceValueCandidate | None
    candidate_scores: tuple[CandidateEvidenceScore, ...]
    rejections: tuple[CandidateRejection, ...]
    next_action: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", EvidenceValueState(self.state))
        object.__setattr__(
            self,
            "request_sha256",
            _sha256(self.request_sha256, "request_sha256"),
        )
        object.__setattr__(self, "decision_id", _text(self.decision_id, "decision_id"))
        object.__setattr__(
            self,
            "exact_scope_sha256",
            _sha256(self.exact_scope_sha256, "exact_scope_sha256"),
        )
        object.__setattr__(
            self,
            "criterion_id",
            _identifier(self.criterion_id, "criterion_id"),
        )
        object.__setattr__(
            self,
            "predeclared_plan_sha256",
            _sha256(self.predeclared_plan_sha256, "predeclared_plan_sha256"),
        )
        if self.selected_candidate is not None and not isinstance(
            self.selected_candidate,
            EvidenceValueCandidate,
        ):
            raise TypeError("selected_candidate must be an EvidenceValueCandidate or None")
        scores = tuple(self.candidate_scores)
        if any(not isinstance(item, CandidateEvidenceScore) for item in scores):
            raise TypeError("candidate_scores must contain CandidateEvidenceScore records")
        object.__setattr__(self, "candidate_scores", scores)
        rejections = tuple(self.rejections)
        if any(not isinstance(item, CandidateRejection) for item in rejections):
            raise TypeError("rejections must contain CandidateRejection records")
        object.__setattr__(self, "rejections", rejections)
        object.__setattr__(self, "next_action", _text(self.next_action, "next_action"))
        if self.state is EvidenceValueState.SELECTED and self.selected_candidate is None:
            raise ValueError("SELECTED requires one selected_candidate")
        if self.state is not EvidenceValueState.SELECTED and self.selected_candidate is not None:
            raise ValueError("only SELECTED may contain a selected_candidate")

    @property
    def ranked_candidate_ids(self) -> tuple[str, ...]:
        return tuple(item.candidate_id for item in self.candidate_scores)

    @property
    def authority_flags(self) -> dict[str, bool]:
        return dict(EVIDENCE_VALUE_AUTHORITY_FLAGS)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "state": self.state.value,
            "request_sha256": self.request_sha256,
            "decision_id": self.decision_id,
            "exact_scope_sha256": self.exact_scope_sha256,
            "criterion_id": self.criterion_id,
            "predeclared_plan_sha256": self.predeclared_plan_sha256,
            "selected_candidate": (
                None
                if self.selected_candidate is None
                else self.selected_candidate.as_dict()
            ),
            "candidate_scores": [item.as_dict() for item in self.candidate_scores],
            "rejections": [item.as_dict() for item in self.rejections],
            "next_action": self.next_action,
            "authority_flags": self.authority_flags,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


_IMPACT_RANK = {
    DecisionImpact.BLOCKING: 3,
    DecisionImpact.PRIMARY: 2,
    DecisionImpact.SECONDARY: 1,
}


def _budget_reasons(
    burden: ExperimentBurden,
    budget: ExperimentBudget,
) -> tuple[str, ...]:
    checks = (
        (
            burden.physical_sample_count,
            budget.max_physical_sample_count,
            "PHYSICAL_SAMPLE_BUDGET_EXCEEDED",
        ),
        (
            burden.scarce_material_mg,
            budget.max_scarce_material_mg,
            "SCARCE_MATERIAL_BUDGET_EXCEEDED",
        ),
        (
            burden.total_active_material_mg,
            budget.max_total_active_material_mg,
            "ACTIVE_MATERIAL_BUDGET_EXCEEDED",
        ),
        (
            burden.assessor_sessions,
            budget.max_assessor_sessions,
            "ASSESSOR_SESSION_BUDGET_EXCEEDED",
        ),
        (
            burden.instrument_minutes,
            budget.max_instrument_minutes,
            "INSTRUMENT_BUDGET_EXCEEDED",
        ),
    )
    return tuple(reason for observed, limit, reason in checks if limit is not None and observed > limit)


def _admissibility_reasons(
    request: EvidenceValueRequest,
    candidate: EvidenceValueCandidate,
) -> tuple[str, ...]:
    reasons: list[str] = list(candidate.blockers)
    if candidate.exact_scope_sha256 != request.exact_scope_sha256:
        reasons.append("EXACT_SCOPE_MISMATCH")
    if candidate.criterion_id != request.criterion_id:
        reasons.append("CRITERION_MISMATCH")
    if not candidate.protocol_qualified:
        reasons.append("PROTOCOL_NOT_QUALIFIED")
    if not candidate.lineage_complete:
        reasons.append("LINEAGE_INCOMPLETE")

    physical_design = candidate.domain is not ExperimentDomain.EVIDENCE_AUDIT
    if physical_design and not candidate.inventory_executable:
        reasons.append("INVENTORY_NOT_EXECUTABLE")
    if physical_design and not candidate.constant_total:
        reasons.append("CONSTANT_TOTAL_NOT_PROVEN")
    if candidate.domain in {
        ExperimentDomain.FORMULA_DELTA,
        ExperimentDomain.PAIRWISE_PREFERENCE,
        ExperimentDomain.NARY_INTERACTION,
    } and not candidate.blinded:
        reasons.append("BLINDING_NOT_DECLARED")
    if candidate.domain in {
        ExperimentDomain.FORMULA_DELTA,
        ExperimentDomain.NARY_INTERACTION,
    } and not candidate.isolated_arms_complete:
        reasons.append("ISOLATED_ARMS_INCOMPLETE")
    if candidate.safety_review_required and not candidate.safety_review_complete:
        reasons.append("SAFETY_REVIEW_INCOMPLETE")
    if candidate.physical_required and candidate.burden.physical_sample_count == 0:
        reasons.append("PHYSICAL_SAMPLE_COUNT_MISSING")

    unresolved = set(request.unresolved_hypothesis_ids)
    for outcome in candidate.outcomes:
        eliminated = set(outcome.eliminated_hypothesis_ids)
        if not eliminated.issubset(unresolved):
            reasons.append("UNKNOWN_HYPOTHESIS_REFERENCE")
        if not eliminated and not outcome.resolves_decision:
            reasons.append("NON_DISCRIMINATING_OUTCOME")

    reasons.extend(_budget_reasons(candidate.burden, request.budget))
    return tuple(sorted(set(reasons)))


def _score_candidate(
    request: EvidenceValueRequest,
    candidate: EvidenceValueCandidate,
) -> CandidateEvidenceScore:
    unresolved = set(request.unresolved_hypothesis_ids)
    elimination_counts = tuple(
        len(unresolved.intersection(outcome.eliminated_hypothesis_ids))
        for outcome in candidate.outcomes
    )
    covered = set().union(
        *(set(outcome.eliminated_hypothesis_ids) for outcome in candidate.outcomes)
    )
    return CandidateEvidenceScore(
        candidate_id=candidate.candidate_id,
        candidate_record_sha256=candidate.record_sha256,
        worst_case_hypotheses_eliminated=min(elimination_counts),
        decision_resolving_outcome_count=sum(
            int(outcome.resolves_decision) for outcome in candidate.outcomes
        ),
        distinct_hypotheses_covered=len(unresolved.intersection(covered)),
        decision_impact=candidate.decision_impact,
        physical_required=candidate.physical_required,
        burden=candidate.burden,
    )


def _ranking_key(score: CandidateEvidenceScore) -> tuple[object, ...]:
    burden = score.burden
    return (
        -score.worst_case_hypotheses_eliminated,
        -score.decision_resolving_outcome_count,
        -score.distinct_hypotheses_covered,
        -_IMPACT_RANK[score.decision_impact],
        int(score.physical_required),
        burden.physical_sample_count,
        burden.scarce_material_mg,
        burden.total_active_material_mg,
        burden.assessor_sessions,
        burden.instrument_minutes,
        score.candidate_id,
    )


def select_evidence_value_experiment(
    request: EvidenceValueRequest,
) -> EvidenceValueResult:
    """Select the most discriminating admissible experiment, then the least burdensome.

    This is not expected utility.  No priors, outcome probabilities, sensory
    values, or beauty scores are inferred.  Candidate outcomes and falsifiable
    consequences must be declared before the selector is called.
    """

    if not isinstance(request, EvidenceValueRequest):
        raise TypeError("request must be an EvidenceValueRequest")
    if request.decision_resolved:
        return EvidenceValueResult(
            state=EvidenceValueState.NO_CHANGE,
            request_sha256=request.record_sha256,
            decision_id=request.decision_id,
            exact_scope_sha256=request.exact_scope_sha256,
            criterion_id=request.criterion_id,
            predeclared_plan_sha256=request.predeclared_plan_sha256,
            selected_candidate=None,
            candidate_scores=(),
            rejections=(),
            next_action="No experiment: the scoped decision is already resolved.",
        )

    admissible: list[tuple[EvidenceValueCandidate, CandidateEvidenceScore]] = []
    rejections: list[CandidateRejection] = []
    for candidate in sorted(request.candidates, key=lambda item: item.candidate_id):
        reasons = _admissibility_reasons(request, candidate)
        if reasons:
            rejections.append(
                CandidateRejection(
                    candidate.candidate_id,
                    candidate.record_sha256,
                    reasons,
                )
            )
            continue
        admissible.append((candidate, _score_candidate(request, candidate)))

    if not admissible:
        return EvidenceValueResult(
            state=EvidenceValueState.HOLD,
            request_sha256=request.record_sha256,
            decision_id=request.decision_id,
            exact_scope_sha256=request.exact_scope_sha256,
            criterion_id=request.criterion_id,
            predeclared_plan_sha256=request.predeclared_plan_sha256,
            selected_candidate=None,
            candidate_scores=(),
            rejections=tuple(rejections),
            next_action=(
                "HOLD: repair candidate scope, lineage, protocol, controls, safety, "
                "or outcome discrimination before spending material."
            ),
        )

    ranked = sorted(admissible, key=lambda item: _ranking_key(item[1]))
    selected, _ = ranked[0]
    scores = tuple(item[1] for item in ranked)
    return EvidenceValueResult(
        state=EvidenceValueState.SELECTED,
        request_sha256=request.record_sha256,
        decision_id=request.decision_id,
        exact_scope_sha256=request.exact_scope_sha256,
        criterion_id=request.criterion_id,
        predeclared_plan_sha256=request.predeclared_plan_sha256,
        selected_candidate=selected,
        candidate_scores=scores,
        rejections=tuple(rejections),
        next_action=(
            f"Run only {selected.candidate_id} under its frozen protocol; "
            "do not compound or infer sensory success from this receipt."
        ),
    )


__all__ = [
    "EVIDENCE_VALUE_AUTHORITY_FLAGS",
    "CandidateEvidenceScore",
    "CandidateRejection",
    "DecisionImpact",
    "EvidenceValueCandidate",
    "EvidenceValueRequest",
    "EvidenceValueResult",
    "EvidenceValueState",
    "ExperimentBudget",
    "ExperimentBurden",
    "ExperimentDomain",
    "ExperimentOutcome",
    "select_evidence_value_experiment",
]
