"""Immutable contracts for Build D scientific-claim planning."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from typing import cast

from engine.calibration.hashing import stable_json_hash

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    if value != value.strip():
        raise ValueError(f"{field_name} must not contain surrounding whitespace")


def _require_unique(values: tuple[str, ...], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique")


class ClaimFamily(str, Enum):
    EXACT_BOTTLE_ARITHMETIC = "exact_bottle_arithmetic"
    EVENT_REPLAY = "event_replay"
    ANALYTICAL_IDENTITY = "analytical_identity"
    ANALYTICAL_QUANTITY = "analytical_quantity"
    EQUILIBRIUM_HEADSPACE_PREDICTION = "equilibrium_headspace_prediction"
    PHYSICAL_RELEASE_TRAJECTORY = "physical_release_trajectory"
    ABOVE_THRESHOLD_SCREENING = "above_threshold_screening"
    PERCEPTIBLE_DIFFERENCE = "perceptible_difference"
    SENSORY_SIMILARITY_EQUIVALENCE = "sensory_similarity_equivalence"
    DESCRIPTIVE_PROFILE_ACCURACY = "descriptive_profile_accuracy"
    TEMPORAL_PROFILE_ACCURACY = "temporal_profile_accuracy"
    RECONSTRUCTION_SIMILARITY = "reconstruction_similarity"
    INTERVENTION_EFFECTIVENESS = "intervention_effectiveness"
    PROTECTED_ATTRIBUTE_PRESERVATION = "protected_attribute_preservation"
    PREFERENCE_LIKING_PREDICTION = "preference_liking_prediction"
    LONGEVITY_PROJECTION_PROXY = "longevity_projection_proxy"
    REGULATORY_SCREENING = "regulatory_screening"


class ValidationMethodFamily(str, Enum):
    DETERMINISTIC_ARITHMETIC = "deterministic_arithmetic"
    EVENT_STREAM_REPLAY = "event_stream_replay"
    ANALYTICAL_IDENTITY = "analytical_identity"
    ANALYTICAL_QUANTITATION = "analytical_quantitation"
    HELD_OUT_HEADSPACE_BENCHMARK = "held_out_headspace_benchmark"
    HELD_OUT_PHYSICAL_RELEASE_BENCHMARK = "held_out_physical_release_benchmark"
    CONTEXTUAL_THRESHOLD_SCREENING = "contextual_threshold_screening"
    SENSORY_DISCRIMINATION = "sensory_discrimination"
    DIRECTIONAL_PAIRED_COMPARISON = "directional_paired_comparison"
    TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE = (
        "trained_quantitative_descriptive_profile"
    )
    REPEATED_TEMPORAL_INTENSITY_PROFILE = "repeated_temporal_intensity_profile"
    SENSOMICS_RECOMBINATION = "sensomics_recombination"
    CONTROLLED_CONSUMER_HEDONIC = "controlled_consumer_hedonic"
    REGULATORY_EVIDENCE_REVIEW = "regulatory_evidence_review"


class ClaimAuthorityState(str, Enum):
    PLANNING_ONLY = "planning_only"
    PREREGISTERED = "preregistered"
    DATA_LOCKED = "data_locked"
    SUPPORTED_EXACT_SCOPE = "supported_exact_scope"
    FAILED_EXACT_SCOPE = "failed_exact_scope"
    INCONCLUSIVE_EXACT_SCOPE = "inconclusive_exact_scope"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class AssessorType(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    TRAINED_DESCRIPTIVE_PANEL = "trained_descriptive_panel"
    DISCRIMINATION_ASSESSOR = "discrimination_assessor"
    CONSUMER = "consumer"
    GC_OLFACTOMETRY_ASSESSOR = "gc_olfactometry_assessor"


class BindingState(str, Enum):
    BOUND = "bound"
    REQUIRED_UNBOUND = "required_unbound"


class BindingAuthorityState(str, Enum):
    QUARANTINED = "quarantined"
    REFERENCE_ONLY = "reference_only"
    LOCK_CANDIDATE = "lock_candidate"
    VALIDATED_EXACT_SCOPE = "validated_exact_scope"


class MarginAuthority(str, Enum):
    PROVISIONAL_PREPILOT = "provisional_prepilot"
    PREREGISTERED_LOCKED = "preregistered_locked"


class EndpointRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY_PROTECTED = "secondary_protected"
    SECONDARY_SUPPORTIVE = "secondary_supportive"


class CriterionKind(str, Enum):
    MINIMUM_EFFECT = "minimum_effect"
    EQUIVALENCE = "equivalence"


@dataclass(frozen=True, slots=True)
class VersionBinding:
    """Exact content binding for a formula, model, or software claimant."""

    kind: str
    identifier: str
    version: str
    sha256: str
    authority_state: BindingAuthorityState

    def __post_init__(self) -> None:
        _require_text(self.kind, "kind")
        _require_text(self.identifier, "identifier")
        _require_text(self.version, "version")
        if not isinstance(self.sha256, str) or not _SHA256_RE.fullmatch(self.sha256):
            raise ValueError("sha256 must be a lowercase 64-character digest")


@dataclass(frozen=True, slots=True)
class ScopeValue:
    """One exact scope value or one explicit required-but-unbound fact."""

    state: BindingState
    value: str | None
    reason: str | None

    def __post_init__(self) -> None:
        if self.state is BindingState.BOUND:
            if not isinstance(self.value, str) or not self.value.strip():
                raise ValueError("bound scope value must be non-empty")
            if self.value != self.value.strip():
                raise ValueError("bound scope value must not have surrounding whitespace")
            if self.reason is not None:
                raise ValueError("bound scope value cannot carry an unbound reason")
            return
        if self.value is not None:
            raise ValueError("unbound scope value cannot carry a value")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("unbound scope value requires a reason")
        if self.reason != self.reason.strip():
            raise ValueError("unbound scope reason must not have surrounding whitespace")

    @classmethod
    def bound(cls, value: str) -> ScopeValue:
        return cls(state=BindingState.BOUND, value=value, reason=None)

    @classmethod
    def required_unbound(cls, reason: str) -> ScopeValue:
        return cls(
            state=BindingState.REQUIRED_UNBOUND,
            value=None,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class ClaimScope:
    population: ScopeValue
    product: ScopeValue
    formula: ScopeValue
    lot: ScopeValue
    matrix: ScopeValue
    substrate: ScopeValue
    condition: ScopeValue


@dataclass(frozen=True, slots=True)
class DecisionCriterion:
    criterion_id: str
    kind: CriterionKind
    lower_margin: Decimal
    upper_margin: Decimal | None
    unit: str
    margin_authority: MarginAuthority
    success_rule: str
    failure_rule: str
    inconclusive_rule: str

    def __post_init__(self) -> None:
        _require_text(self.criterion_id, "criterion_id")
        _require_text(self.unit, "unit")
        _require_text(self.success_rule, "success_rule")
        _require_text(self.failure_rule, "failure_rule")
        _require_text(self.inconclusive_rule, "inconclusive_rule")
        if not isinstance(self.lower_margin, Decimal) or not self.lower_margin.is_finite():
            raise ValueError("lower_margin must be a finite Decimal")
        if self.upper_margin is not None and (
            not isinstance(self.upper_margin, Decimal)
            or not self.upper_margin.is_finite()
        ):
            raise ValueError("upper_margin must be a finite Decimal or None")
        if self.kind is CriterionKind.MINIMUM_EFFECT:
            if self.lower_margin <= 0 or self.upper_margin is not None:
                raise ValueError(
                    "minimum-effect criterion requires a positive lower margin "
                    "and no upper margin"
                )
            return
        if (
            self.upper_margin is None
            or self.lower_margin >= 0
            or self.upper_margin <= 0
            or self.lower_margin >= self.upper_margin
        ):
            raise ValueError("equivalence criterion margins must straddle zero")


@dataclass(frozen=True, slots=True)
class EndpointDefinition:
    endpoint_id: str
    claim_family: ClaimFamily
    role: EndpointRole
    attribute: str
    method_family: ValidationMethodFamily
    timepoint: str
    scale: str
    estimand: str
    criterion: DecisionCriterion

    def __post_init__(self) -> None:
        _require_text(self.endpoint_id, "endpoint_id")
        _require_text(self.attribute, "attribute")
        _require_text(self.timepoint, "timepoint")
        _require_text(self.scale, "scale")
        _require_text(self.estimand, "estimand")


@dataclass(frozen=True, slots=True)
class ComparatorDefinition:
    comparator_id: str
    description: str
    binding: VersionBinding

    def __post_init__(self) -> None:
        _require_text(self.comparator_id, "comparator_id")
        _require_text(self.description, "description")


@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    evidence_id: str
    description: str

    def __post_init__(self) -> None:
        _require_text(self.evidence_id, "evidence_id")
        _require_text(self.description, "description")


@dataclass(frozen=True, slots=True)
class ClaimDefinition:
    """One immutable, versioned claim definition with no release authority."""

    claim_id: str
    version: int
    title: str
    family: ClaimFamily
    claimant_versions: tuple[VersionBinding, ...]
    assessor_type: AssessorType
    scope: ClaimScope
    primary_endpoint: EndpointDefinition
    secondary_endpoints: tuple[EndpointDefinition, ...]
    comparator: ComparatorDefinition
    required_evidence: tuple[EvidenceRequirement, ...]
    authority_state: ClaimAuthorityState
    expiration_triggers: tuple[str, ...]
    study_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    observed_outcome: str = field(default="unmeasured", init=False)

    def __post_init__(self) -> None:
        _require_text(self.claim_id, "claim_id")
        _require_text(self.title, "title")
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise ValueError("version must be a positive integer")
        if self.version <= 0:
            raise ValueError("version must be a positive integer")
        if not self.claimant_versions:
            raise ValueError("claimant_versions must not be empty")
        claimant_ids = tuple(
            f"{item.kind}:{item.identifier}:{item.version}:{item.sha256}"
            for item in self.claimant_versions
        )
        _require_unique(claimant_ids, "claimant versions")
        if self.primary_endpoint.role is not EndpointRole.PRIMARY:
            raise ValueError("primary endpoint must have the primary role")
        if self.primary_endpoint.claim_family is not self.family:
            raise ValueError("primary endpoint family must match the claim family")
        endpoints = (self.primary_endpoint, *self.secondary_endpoints)
        if any(item.role is EndpointRole.PRIMARY for item in self.secondary_endpoints):
            raise ValueError("secondary endpoints cannot have the primary role")
        _require_unique(
            tuple(item.endpoint_id for item in endpoints),
            "endpoint identifiers",
        )
        if not self.required_evidence:
            raise ValueError("required evidence must not be empty")
        _require_unique(
            tuple(item.evidence_id for item in self.required_evidence),
            "evidence identifiers",
        )
        if not self.expiration_triggers:
            raise ValueError("expiration_triggers must not be empty")
        for trigger in self.expiration_triggers:
            _require_text(trigger, "expiration trigger")
        _require_unique(self.expiration_triggers, "expiration triggers")

    def as_dict(self) -> dict[str, object]:
        return cast(dict[str, object], asdict(self))

    @property
    def content_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


__all__ = [
    "AssessorType",
    "BindingAuthorityState",
    "BindingState",
    "ClaimAuthorityState",
    "ClaimDefinition",
    "ClaimFamily",
    "ClaimScope",
    "ComparatorDefinition",
    "CriterionKind",
    "DecisionCriterion",
    "EndpointDefinition",
    "EndpointRole",
    "EvidenceRequirement",
    "MarginAuthority",
    "ScopeValue",
    "ValidationMethodFamily",
    "VersionBinding",
]
