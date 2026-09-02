"""Evidence-scoped preference views for the formulation-intelligence planes.

This module keeps predicted priors, exact participant observations, cluster
structure, criterion-specific evidence, and non-compensatory decisions in
separate immutable records.  It performs no formula, inventory, safety,
physical-performance, compounding, or release operation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Any, ClassVar, TypeVar

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    SupportInterval,
    SupportMeasure,
    UnitInterval,
    UnknownFact,
    ValueState,
    _canonical_json_bytes,
    _CanonicalRecord,
    _finite_value,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _normalized_text_tuple,
    _payload,
)

_ViewT = TypeVar("_ViewT", bound=_CanonicalRecord)


def _stable_id(prefix: str, payload: object) -> str:
    return f"{prefix}:{sha256(_canonical_json_bytes(payload)).hexdigest()[:24]}"


def _slug(value: str) -> str:
    normalized = _normalized_identifier(value, "identifier")
    raw = "".join(character if character.isalnum() else "-" for character in normalized)
    return "-".join(part for part in raw.split("-") if part)


def _optional_identifier(value: str | None, field_name: str) -> str | None:
    return None if value is None else _normalized_identifier(value, field_name)


def _canonical_views(
    values: Iterable[_ViewT],
    *,
    record_type: type[_ViewT],
    field_name: str,
) -> tuple[_ViewT, ...]:
    by_hash: dict[str, _ViewT] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} values")
        by_hash[value.content_sha256] = value
    return tuple(by_hash[key] for key in sorted(by_hash))


def _required_provenance(
    values: Iterable[ProvenanceRef],
    field_name: str = "provenance_refs",
) -> tuple[ProvenanceRef, ...]:
    provenance = _merged_provenance(values)
    if not provenance:
        raise ValueError(f"{field_name} must not be empty")
    return provenance


_HUMAN_EVIDENCE_CLASSES = frozenset(
    {EvidenceClass.DIRECT_OBSERVATION, EvidenceClass.USER_REPORT}
)


def _human_provenance(values: Iterable[ProvenanceRef]) -> tuple[ProvenanceRef, ...]:
    provenance = _required_provenance(values)
    if not any(item.evidence_class in _HUMAN_EVIDENCE_CLASSES for item in provenance):
        raise ValueError("human observation provenance is required")
    return provenance


class PreferenceOutcome(str, Enum):
    PREFER_A = "prefer_a"
    PREFER_B = "prefer_b"
    NO_PREFERENCE = "no_preference"
    NO_PERCEPTIBLE_DIFFERENCE = "no_perceptible_difference"
    CANNOT_JUDGE = "cannot_judge"
    PROTOCOL_ABORT = "protocol_abort"
    MISSING = "missing"

    @property
    def is_tie(self) -> bool:
        return self in {
            PreferenceOutcome.NO_PREFERENCE,
            PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE,
        }

    @property
    def is_abstention(self) -> bool:
        return self in {
            PreferenceOutcome.CANNOT_JUDGE,
            PreferenceOutcome.PROTOCOL_ABORT,
            PreferenceOutcome.MISSING,
        }


class HedonicCriterion(str, Enum):
    LIKING = "liking"
    COMFORT = "comfort"
    SENSUALITY = "sensuality"
    ELEGANCE = "elegance"
    INTEREST = "interest"
    NATURALNESS = "naturalness"
    TARGET_FIDELITY = "target_fidelity"
    DEPTH = "depth"
    RICHNESS = "richness"
    COHERENCE = "coherence"
    AVERSION = "aversion"
    DEFECT_INTENSITY = "defect_intensity"

    @property
    def direction(self) -> CriterionDirection:
        if self in {HedonicCriterion.AVERSION, HedonicCriterion.DEFECT_INTENSITY}:
            return CriterionDirection.MINIMIZE
        return CriterionDirection.MAXIMIZE


class ExpertiseLevel(str, Enum):
    UNREPORTED = "unreported"
    NAIVE = "naive"
    FAMILIAR = "familiar"
    TRAINED = "trained"
    EXPERT = "expert"


class SensitivityState(str, Enum):
    UNREPORTED = "unreported"
    UNSCREENED = "unscreened"
    SCREENED_TYPICAL = "screened_typical"
    LOW_SENSITIVITY = "low_sensitivity"
    HIGH_SENSITIVITY = "high_sensitivity"
    SPECIFIC_ANOSMIA_RISK = "specific_anosmia_risk"


class CarryoverState(str, Enum):
    NONE = "none"
    POSSIBLE = "possible"
    OBSERVED = "observed"
    UNKNOWN = "unknown"


class BlindingState(str, Enum):
    UNREPORTED = "unreported"
    OPEN_LABEL = "open_label"
    PARTICIPANT_BLINDED = "participant_blinded"
    ASSESSOR_BLINDED = "assessor_blinded"
    DOUBLE_BLIND = "double_blind"


class MissingnessKind(str, Enum):
    NONE = "none"
    CANNOT_JUDGE = "cannot_judge"
    PROTOCOL_ABORT = "protocol_abort"
    ITEM_NONRESPONSE = "item_nonresponse"
    SESSION_NONRESPONSE = "session_nonresponse"
    NOT_RECORDED = "not_recorded"


class PriorBasis(str, Enum):
    PRIMARY_LITERATURE = "primary_literature"
    MATERIAL_PANEL_PRIOR = "material_panel_prior"
    COMPUTATIONAL_PRIOR = "computational_prior"
    OAV_DIAGNOSTIC = "oav_diagnostic"
    SUPPLIER_PROSE = "supplier_prose"
    UNKNOWN = "unknown"


class MixtureExpectationMethod(str, Enum):
    LINEAR = "linear"
    INTENSITY_WEIGHTED = "intensity_weighted"
    DOMINANCE = "dominance"
    HEURISTIC = "heuristic"
    UNKNOWN = "unknown"


class ClusterStability(str, Enum):
    UNKNOWN = "unknown"
    PROVISIONAL = "provisional"
    STABLE = "stable"


class DecisionEvidenceBasis(str, Enum):
    HUMAN_OBSERVATION = "human_observation"
    PREDICTED = "predicted"
    GENERIC_SCORE = "generic_score"
    UNKNOWN = "unknown"


class AggregationMethod(str, Enum):
    CATEGORICAL_COUNTS = "categorical_counts"
    STRATIFIED_CATEGORICAL_COUNTS = "stratified_categorical_counts"


@dataclass(frozen=True, slots=True)
class NumericInterval(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_numeric_interval_v1"

    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = _finite_value(self.lower, "lower")
        upper = _finite_value(self.upper, "upper")
        if lower > upper:
            raise ValueError("lower must not exceed upper")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> NumericInterval:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(lower=data["lower"], upper=data["upper"])


@dataclass(frozen=True, slots=True)
class NumericEstimate(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_numeric_estimate_v1"

    value: CriterionValue
    unit: str
    uncertainty: NumericInterval | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, CriterionValue):
            raise TypeError("value must be a CriterionValue")
        object.__setattr__(self, "unit", _normalized_text(self.unit, "unit"))
        if self.value.state is ValueState.UNKNOWN:
            if self.uncertainty is not None:
                raise ValueError("unknown estimates cannot carry numeric uncertainty")
            return
        if self.uncertainty is not None:
            if not isinstance(self.uncertainty, NumericInterval):
                raise TypeError("uncertainty must be NumericInterval or None")
            assert self.value.value is not None
            if not self.uncertainty.lower <= self.value.value <= self.uncertainty.upper:
                raise ValueError("uncertainty must contain the estimate value")

    @classmethod
    def known(
        cls,
        value: float,
        *,
        unit: str,
        lower: float | None = None,
        upper: float | None = None,
    ) -> NumericEstimate:
        if (lower is None) != (upper is None):
            raise ValueError("lower and upper must be supplied together")
        if lower is None:
            interval = None
        else:
            assert upper is not None
            interval = NumericInterval(lower, upper)
        return cls(value=CriterionValue.known(value), unit=unit, uncertainty=interval)

    @classmethod
    def unknown(cls, reason: str, *, unit: str) -> NumericEstimate:
        return cls(value=CriterionValue.unknown(reason), unit=unit, uncertainty=None)

    @property
    def bounds(self) -> tuple[float, float] | None:
        if self.value.state is ValueState.UNKNOWN:
            return None
        assert self.value.value is not None
        if self.uncertainty is None:
            return (self.value.value, self.value.value)
        return (self.uncertainty.lower, self.uncertainty.upper)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> NumericEstimate:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            value=CriterionValue.from_dict(data["value"]),
            unit=data["unit"],
            uncertainty=(
                NumericInterval.from_dict(data["uncertainty"])
                if data.get("uncertainty") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ComparisonCondition(_CanonicalRecord):
    """Exact sample, concentration, matrix, time, endpoint, and context key."""

    SCHEMA_VERSION: ClassVar[str] = "hedonic_comparison_condition_v1"

    condition_id: str
    sample_a_id: str
    sample_b_id: str | None
    concentration_a: str
    concentration_b: str | None
    matrix: str
    temporal_window: str
    endpoint: HedonicCriterion
    context: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "condition_id",
            _normalized_identifier(self.condition_id, "condition_id"),
        )
        sample_a = _normalized_identifier(self.sample_a_id, "sample_a_id")
        sample_b = _optional_identifier(self.sample_b_id, "sample_b_id")
        if sample_b == sample_a:
            raise ValueError("sample_a_id and sample_b_id must differ")
        object.__setattr__(self, "sample_a_id", sample_a)
        object.__setattr__(self, "sample_b_id", sample_b)
        concentration_a = _normalized_identifier(self.concentration_a, "concentration_a")
        concentration_b = (
            None
            if self.concentration_b is None
            else _normalized_identifier(self.concentration_b, "concentration_b")
        )
        if (sample_b is None) != (concentration_b is None):
            raise ValueError("sample_b_id and concentration_b must be supplied together")
        object.__setattr__(self, "concentration_a", concentration_a)
        object.__setattr__(self, "concentration_b", concentration_b)
        for field_name in ("matrix", "temporal_window", "context"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "endpoint", HedonicCriterion(self.endpoint))

    @property
    def is_pair(self) -> bool:
        return self.sample_b_id is not None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ComparisonCondition:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            condition_id=data["condition_id"],
            sample_a_id=data["sample_a_id"],
            sample_b_id=data.get("sample_b_id"),
            concentration_a=data["concentration_a"],
            concentration_b=data.get("concentration_b"),
            matrix=data["matrix"],
            temporal_window=data["temporal_window"],
            endpoint=HedonicCriterion(data["endpoint"]),
            context=data["context"],
        )


@dataclass(frozen=True, slots=True)
class AssessorContext(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_assessor_context_v2"

    participant_id: str
    assessor_id: str
    cluster_id: str | None
    expertise: ExpertiseLevel
    sensitivity: SensitivityState
    sensitivity_detail: str
    blinding: BlindingState
    blinding_protocol_id: str | None
    session_id: str
    day_id: str
    order_sequence_id: str
    realized_order: tuple[str, ...]
    predecessor_sample_id: str | None
    carryover: CarryoverState
    repeat_index: int
    context: str

    def __post_init__(self) -> None:
        for field_name in (
            "participant_id",
            "assessor_id",
            "session_id",
            "day_id",
            "order_sequence_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "cluster_id",
            _optional_identifier(self.cluster_id, "cluster_id"),
        )
        object.__setattr__(self, "expertise", ExpertiseLevel(self.expertise))
        object.__setattr__(self, "sensitivity", SensitivityState(self.sensitivity))
        object.__setattr__(
            self,
            "sensitivity_detail",
            _normalized_text(self.sensitivity_detail, "sensitivity_detail"),
        )
        blinding = BlindingState(self.blinding)
        object.__setattr__(self, "blinding", blinding)
        protocol_id = _optional_identifier(
            self.blinding_protocol_id,
            "blinding_protocol_id",
        )
        if blinding in {
            BlindingState.PARTICIPANT_BLINDED,
            BlindingState.ASSESSOR_BLINDED,
            BlindingState.DOUBLE_BLIND,
        } and protocol_id is None:
            raise ValueError("a blinded assessment requires blinding_protocol_id")
        object.__setattr__(self, "blinding_protocol_id", protocol_id)
        order = tuple(
            _normalized_identifier(item, "realized_order") for item in self.realized_order
        )
        if not order or len(order) != len(set(order)):
            raise ValueError("realized_order must be a nonempty sequence of unique samples")
        object.__setattr__(self, "realized_order", order)
        object.__setattr__(
            self,
            "predecessor_sample_id",
            _optional_identifier(self.predecessor_sample_id, "predecessor_sample_id"),
        )
        object.__setattr__(self, "carryover", CarryoverState(self.carryover))
        if isinstance(self.repeat_index, bool) or not isinstance(self.repeat_index, int):
            raise TypeError("repeat_index must be an integer")
        if self.repeat_index < 1:
            raise ValueError("repeat_index must be positive")
        object.__setattr__(self, "context", _normalized_text(self.context, "context"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AssessorContext:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            participant_id=data["participant_id"],
            assessor_id=data["assessor_id"],
            cluster_id=data.get("cluster_id"),
            expertise=ExpertiseLevel(data["expertise"]),
            sensitivity=SensitivityState(data["sensitivity"]),
            sensitivity_detail=data["sensitivity_detail"],
            blinding=BlindingState(data["blinding"]),
            blinding_protocol_id=data.get("blinding_protocol_id"),
            session_id=data["session_id"],
            day_id=data["day_id"],
            order_sequence_id=data["order_sequence_id"],
            realized_order=tuple(data["realized_order"]),
            predecessor_sample_id=data.get("predecessor_sample_id"),
            carryover=CarryoverState(data["carryover"]),
            repeat_index=data["repeat_index"],
            context=data["context"],
        )


def _require_pair(condition: ComparisonCondition, view_name: str) -> None:
    if not condition.is_pair:
        raise ValueError(f"{view_name} requires a paired comparison condition")


@dataclass(frozen=True, slots=True)
class MaterialPriorView(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_material_prior_view_v1"

    view_id: str
    subject_id: str
    condition: ComparisonCondition
    basis: PriorBasis
    estimate: NumericEstimate
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _normalized_identifier(self.view_id, "view_id"))
        subject = _normalized_identifier(self.subject_id, "subject_id")
        object.__setattr__(self, "subject_id", subject)
        if not isinstance(self.condition, ComparisonCondition):
            raise TypeError("condition must be ComparisonCondition")
        if self.condition.is_pair:
            raise ValueError("material prior view requires a single-subject condition")
        if subject != self.condition.sample_a_id:
            raise ValueError("subject_id must match condition sample_a_id")
        basis = PriorBasis(self.basis)
        object.__setattr__(self, "basis", basis)
        if not isinstance(self.estimate, NumericEstimate):
            raise TypeError("estimate must be NumericEstimate")
        if (
            basis
            in {
                PriorBasis.OAV_DIAGNOSTIC,
                PriorBasis.SUPPLIER_PROSE,
                PriorBasis.UNKNOWN,
            }
            and self.estimate.value.state is ValueState.KNOWN
        ):
            raise ValueError(
                f"{basis.value} cannot carry a known numeric hedonic estimate"
            )
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be UnitInterval")
        object.__setattr__(self, "provenance_refs", _required_provenance(self.provenance_refs))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MaterialPriorView:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            subject_id=data["subject_id"],
            condition=ComparisonCondition.from_dict(data["condition"]),
            basis=PriorBasis(data["basis"]),
            estimate=NumericEstimate.from_dict(data["estimate"]),
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class MixtureExpectationView(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_mixture_expectation_view_v1"

    view_id: str
    condition: ComparisonCondition
    method: MixtureExpectationMethod
    expected_difference: NumericEstimate
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _normalized_identifier(self.view_id, "view_id"))
        if not isinstance(self.condition, ComparisonCondition):
            raise TypeError("condition must be ComparisonCondition")
        _require_pair(self.condition, "mixture expectation")
        object.__setattr__(self, "method", MixtureExpectationMethod(self.method))
        if not isinstance(self.expected_difference, NumericEstimate):
            raise TypeError("expected_difference must be NumericEstimate")
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be UnitInterval")
        object.__setattr__(self, "provenance_refs", _required_provenance(self.provenance_refs))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> MixtureExpectationView:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            condition=ComparisonCondition.from_dict(data["condition"]),
            method=MixtureExpectationMethod(data["method"]),
            expected_difference=NumericEstimate.from_dict(data["expected_difference"]),
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class TemporalPreferenceObservation(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_temporal_preference_observation_v3"

    view_id: str
    condition: ComparisonCondition
    assessor: AssessorContext
    outcome: PreferenceOutcome
    missingness: MissingnessKind
    missingness_reason: str | None
    rating_a: NumericEstimate
    rating_b: NumericEstimate
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _normalized_identifier(self.view_id, "view_id"))
        if not isinstance(self.condition, ComparisonCondition):
            raise TypeError("condition must be ComparisonCondition")
        _require_pair(self.condition, "temporal preference observation")
        if not isinstance(self.assessor, AssessorContext):
            raise TypeError("assessor must be AssessorContext")
        expected_order = {self.condition.sample_a_id, self.condition.sample_b_id}
        if len(self.assessor.realized_order) != 2 or set(self.assessor.realized_order) != expected_order:
            raise ValueError("realized_order must contain the two condition samples exactly once")
        outcome = PreferenceOutcome(self.outcome)
        object.__setattr__(self, "outcome", outcome)
        missingness = MissingnessKind(self.missingness)
        reason = (
            None
            if self.missingness_reason is None
            else _normalized_text(self.missingness_reason, "missingness_reason")
        )
        expected_missingness: Mapping[PreferenceOutcome, frozenset[MissingnessKind]] = {
            PreferenceOutcome.CANNOT_JUDGE: frozenset({MissingnessKind.CANNOT_JUDGE}),
            PreferenceOutcome.PROTOCOL_ABORT: frozenset({MissingnessKind.PROTOCOL_ABORT}),
            PreferenceOutcome.MISSING: frozenset(
                {
                    MissingnessKind.ITEM_NONRESPONSE,
                    MissingnessKind.SESSION_NONRESPONSE,
                    MissingnessKind.NOT_RECORDED,
                }
            ),
        }
        allowed = expected_missingness.get(outcome, frozenset({MissingnessKind.NONE}))
        if missingness not in allowed:
            raise ValueError(
                f"missingness {missingness.value!r} is incompatible with outcome "
                f"{outcome.value!r}"
            )
        if missingness is MissingnessKind.NONE and reason is not None:
            raise ValueError("complete outcomes cannot carry a missingness_reason")
        if missingness is not MissingnessKind.NONE and reason is None:
            raise ValueError("incomplete outcomes require a missingness_reason")
        object.__setattr__(self, "missingness", missingness)
        object.__setattr__(self, "missingness_reason", reason)
        for field_name in ("rating_a", "rating_b"):
            if not isinstance(getattr(self, field_name), NumericEstimate):
                raise TypeError(f"{field_name} must be NumericEstimate")
        if self.rating_a.unit != self.rating_b.unit:
            raise ValueError("rating units must match")
        if outcome.is_abstention and (
            self.rating_a.value.state is not ValueState.UNKNOWN
            or self.rating_b.value.state is not ValueState.UNKNOWN
        ):
            raise ValueError("abstention and missing outcomes require unknown ratings")
        bounds_a = self.rating_a.bounds
        bounds_b = self.rating_b.bounds
        if bounds_a is not None and bounds_b is not None:
            if self.condition.endpoint.direction is CriterionDirection.MAXIMIZE:
                a_clearly_better = bounds_a[0] > bounds_b[1]
                b_clearly_better = bounds_b[0] > bounds_a[1]
            else:
                a_clearly_better = bounds_a[1] < bounds_b[0]
                b_clearly_better = bounds_b[1] < bounds_a[0]
            if outcome is PreferenceOutcome.PREFER_A and not a_clearly_better:
                raise ValueError(
                    "prefer_a outcome contradicts or exceeds the numeric rating evidence"
                )
            if outcome is PreferenceOutcome.PREFER_B and not b_clearly_better:
                raise ValueError(
                    "prefer_b outcome contradicts or exceeds the numeric rating evidence"
                )
            if outcome.is_tie and (a_clearly_better or b_clearly_better):
                raise ValueError(
                    "tie outcome contradicts non-overlapping numeric rating evidence"
                )
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be UnitInterval")
        object.__setattr__(self, "provenance_refs", _human_provenance(self.provenance_refs))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalPreferenceObservation:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            condition=ComparisonCondition.from_dict(data["condition"]),
            assessor=AssessorContext.from_dict(data["assessor"]),
            outcome=PreferenceOutcome(data["outcome"]),
            missingness=MissingnessKind(data["missingness"]),
            missingness_reason=data.get("missingness_reason"),
            rating_a=NumericEstimate.from_dict(data["rating_a"]),
            rating_b=NumericEstimate.from_dict(data["rating_b"]),
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class InteractionResidualView(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_interaction_residual_view_v2"

    view_id: str
    condition: ComparisonCondition
    expectation_view_id: str
    observation_id: str
    residual: NumericEstimate
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        for field_name in ("view_id", "expectation_view_id", "observation_id"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.condition, ComparisonCondition):
            raise TypeError("condition must be ComparisonCondition")
        _require_pair(self.condition, "interaction residual")
        if not isinstance(self.residual, NumericEstimate):
            raise TypeError("residual must be NumericEstimate")
        object.__setattr__(self, "provenance_refs", _human_provenance(self.provenance_refs))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> InteractionResidualView:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            condition=ComparisonCondition.from_dict(data["condition"]),
            expectation_view_id=data["expectation_view_id"],
            observation_id=data["observation_id"],
            residual=NumericEstimate.from_dict(data["residual"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def derive_interaction_residual(
    view_id: str,
    expectation: MixtureExpectationView,
    observation: TemporalPreferenceObservation,
) -> InteractionResidualView:
    """Subtract an exact-condition expectation from one participant observation."""

    if not isinstance(expectation, MixtureExpectationView):
        raise TypeError("expectation must be MixtureExpectationView")
    if not isinstance(observation, TemporalPreferenceObservation):
        raise TypeError("observation must be TemporalPreferenceObservation")
    if expectation.condition != observation.condition:
        raise ValueError("interaction residual requires an exact condition match")
    units = {
        expectation.expected_difference.unit,
        observation.rating_a.unit,
        observation.rating_b.unit,
    }
    if len(units) != 1:
        raise ValueError("expectation and observation units must match")
    expected_bounds = expectation.expected_difference.bounds
    a_bounds = observation.rating_a.bounds
    b_bounds = observation.rating_b.bounds
    if expected_bounds is None or a_bounds is None or b_bounds is None:
        residual = NumericEstimate.unknown(
            "residual unavailable because an exact-condition input is unknown",
            unit=expectation.expected_difference.unit,
        )
    else:
        assert expectation.expected_difference.value.value is not None
        assert observation.rating_a.value.value is not None
        assert observation.rating_b.value.value is not None
        point = round(
            observation.rating_a.value.value
            - observation.rating_b.value.value
            - expectation.expected_difference.value.value,
            12,
        )
        lower = round(a_bounds[0] - b_bounds[1] - expected_bounds[1], 12)
        upper = round(a_bounds[1] - b_bounds[0] - expected_bounds[0], 12)
        residual = NumericEstimate.known(
            point,
            unit=expectation.expected_difference.unit,
            lower=lower,
            upper=upper,
        )
    return InteractionResidualView(
        view_id=view_id,
        condition=expectation.condition,
        expectation_view_id=expectation.view_id,
        observation_id=observation.view_id,
        residual=residual,
        provenance_refs=_merged_provenance(
            (*expectation.provenance_refs, *observation.provenance_refs)
        ),
    )


@dataclass(frozen=True, slots=True)
class LinkedOutcome(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_linked_outcome_v1"

    observation_id: str
    outcome: PreferenceOutcome

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _normalized_identifier(self.observation_id, "observation_id"),
        )
        object.__setattr__(self, "outcome", PreferenceOutcome(self.outcome))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LinkedOutcome:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            observation_id=data["observation_id"],
            outcome=PreferenceOutcome(data["outcome"]),
        )


@dataclass(frozen=True, slots=True)
class CriterionPreferenceView(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_criterion_preference_view_v2"

    view_id: str
    condition: ComparisonCondition
    outcomes: tuple[LinkedOutcome, ...]
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _normalized_identifier(self.view_id, "view_id"))
        if not isinstance(self.condition, ComparisonCondition):
            raise TypeError("condition must be ComparisonCondition")
        _require_pair(self.condition, "criterion preference view")
        outcomes = _canonical_views(
            self.outcomes,
            record_type=LinkedOutcome,
            field_name="outcomes",
        )
        ids = tuple(item.observation_id for item in outcomes)
        if not outcomes or len(ids) != len(set(ids)):
            raise ValueError("criterion preference outcomes require unique observation IDs")
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(self, "provenance_refs", _human_provenance(self.provenance_refs))

    @property
    def ties(self) -> tuple[LinkedOutcome, ...]:
        return tuple(item for item in self.outcomes if item.outcome.is_tie)

    @property
    def abstentions(self) -> tuple[LinkedOutcome, ...]:
        return tuple(item for item in self.outcomes if item.outcome.is_abstention)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CriterionPreferenceView:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            condition=ComparisonCondition.from_dict(data["condition"]),
            outcomes=tuple(LinkedOutcome.from_dict(item) for item in data["outcomes"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def build_criterion_preference_view(
    view_id: str,
    observations: Iterable[TemporalPreferenceObservation],
) -> CriterionPreferenceView:
    canonical = _canonical_views(
        observations,
        record_type=TemporalPreferenceObservation,
        field_name="observations",
    )
    if not canonical:
        raise ValueError("at least one observation is required")
    condition = canonical[0].condition
    if any(item.condition != condition for item in canonical):
        raise ValueError("criterion preference view requires one exact condition")
    ids = tuple(item.view_id for item in canonical)
    if len(ids) != len(set(ids)):
        raise ValueError("discordant observation IDs must be resolved before summary")
    return CriterionPreferenceView(
        view_id=view_id,
        condition=condition,
        outcomes=tuple(
            LinkedOutcome(observation_id=item.view_id, outcome=item.outcome)
            for item in canonical
        ),
        provenance_refs=_merged_provenance(
            item for observation in canonical for item in observation.provenance_refs
        ),
    )


@dataclass(frozen=True, slots=True)
class PopulationPreferenceView(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_population_preference_view_v1"

    view_id: str
    condition: ComparisonCondition
    cluster_id: str
    participant_ids: tuple[str, ...]
    stability: ClusterStability
    outcome: PreferenceOutcome
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _normalized_identifier(self.view_id, "view_id"))
        if not isinstance(self.condition, ComparisonCondition):
            raise TypeError("condition must be ComparisonCondition")
        _require_pair(self.condition, "population preference view")
        object.__setattr__(
            self,
            "cluster_id",
            _normalized_identifier(self.cluster_id, "cluster_id"),
        )
        object.__setattr__(
            self,
            "participant_ids",
            _normalized_text_tuple(
                self.participant_ids,
                "participant_ids",
                allow_empty=False,
                identifiers=True,
            ),
        )
        object.__setattr__(self, "stability", ClusterStability(self.stability))
        object.__setattr__(self, "outcome", PreferenceOutcome(self.outcome))
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be UnitInterval")
        object.__setattr__(self, "provenance_refs", _human_provenance(self.provenance_refs))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PopulationPreferenceView:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            condition=ComparisonCondition.from_dict(data["condition"]),
            cluster_id=data["cluster_id"],
            participant_ids=tuple(data["participant_ids"]),
            stability=ClusterStability(data["stability"]),
            outcome=PreferenceOutcome(data["outcome"]),
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class OutcomeCount(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_outcome_count_v1"

    outcome: PreferenceOutcome
    count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome", PreferenceOutcome(self.outcome))
        if isinstance(self.count, bool) or not isinstance(self.count, int):
            raise TypeError("count must be an integer")
        if self.count < 1:
            raise ValueError("count must be positive")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> OutcomeCount:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            outcome=PreferenceOutcome(data["outcome"]),
            count=data["count"],
        )


@dataclass(frozen=True, slots=True)
class AggregatePreferenceView(_CanonicalRecord):
    """Categorical aggregate that preserves missing/tie cells and never chooses a winner."""

    SCHEMA_VERSION: ClassVar[str] = "hedonic_aggregate_preference_view_v2"

    view_id: str
    condition: ComparisonCondition
    aggregation_method: AggregationMethod
    observation_ids: tuple[str, ...]
    participant_ids: tuple[str, ...]
    cluster_ids: tuple[str, ...]
    outcome_counts: tuple[OutcomeCount, ...]
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "view_id", _normalized_identifier(self.view_id, "view_id"))
        if not isinstance(self.condition, ComparisonCondition):
            raise TypeError("condition must be ComparisonCondition")
        _require_pair(self.condition, "aggregate preference view")
        method = AggregationMethod(self.aggregation_method)
        object.__setattr__(self, "aggregation_method", method)
        for field_name in ("observation_ids", "participant_ids", "cluster_ids"):
            values = _normalized_text_tuple(
                getattr(self, field_name),
                field_name,
                allow_empty=field_name == "cluster_ids",
                identifiers=True,
            )
            object.__setattr__(self, field_name, values)
        counts = _canonical_views(
            self.outcome_counts,
            record_type=OutcomeCount,
            field_name="outcome_counts",
        )
        outcomes = tuple(item.outcome for item in counts)
        if not counts or len(outcomes) != len(set(outcomes)):
            raise ValueError("outcome_counts require unique categorical outcomes")
        if sum(item.count for item in counts) != len(self.observation_ids):
            raise ValueError("outcome_counts must cover every aggregate observation exactly once")
        if (
            len(self.cluster_ids) > 1
            and method is not AggregationMethod.STRATIFIED_CATEGORICAL_COUNTS
        ):
            raise ValueError("multi-cluster aggregates must remain explicitly stratified")
        object.__setattr__(self, "outcome_counts", counts)
        object.__setattr__(self, "provenance_refs", _human_provenance(self.provenance_refs))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AggregatePreferenceView:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            condition=ComparisonCondition.from_dict(data["condition"]),
            aggregation_method=AggregationMethod(data["aggregation_method"]),
            observation_ids=tuple(data["observation_ids"]),
            participant_ids=tuple(data["participant_ids"]),
            cluster_ids=tuple(data["cluster_ids"]),
            outcome_counts=tuple(
                OutcomeCount.from_dict(item) for item in data["outcome_counts"]
            ),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def build_aggregate_preference_view(
    view_id: str,
    observations: Iterable[TemporalPreferenceObservation],
) -> AggregatePreferenceView:
    canonical = _canonical_views(
        observations,
        record_type=TemporalPreferenceObservation,
        field_name="observations",
    )
    if not canonical:
        raise ValueError("at least one observation is required")
    condition = canonical[0].condition
    if any(item.condition != condition for item in canonical):
        raise ValueError("aggregate preference view requires one exact condition")
    observation_ids = tuple(item.view_id for item in canonical)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("discordant observation IDs must be resolved before aggregation")
    counts: dict[PreferenceOutcome, int] = {}
    for observation in canonical:
        counts[observation.outcome] = counts.get(observation.outcome, 0) + 1
    cluster_ids = tuple(
        sorted(
            {
                observation.assessor.cluster_id
                for observation in canonical
                if observation.assessor.cluster_id is not None
            }
        )
    )
    method = (
        AggregationMethod.STRATIFIED_CATEGORICAL_COUNTS
        if len(cluster_ids) > 1
        else AggregationMethod.CATEGORICAL_COUNTS
    )
    return AggregatePreferenceView(
        view_id=view_id,
        condition=condition,
        aggregation_method=method,
        observation_ids=observation_ids,
        participant_ids=tuple(
            sorted({item.assessor.participant_id for item in canonical})
        ),
        cluster_ids=cluster_ids,
        outcome_counts=tuple(
            OutcomeCount(outcome=outcome, count=count)
            for outcome, count in sorted(counts.items(), key=lambda item: item[0].value)
        ),
        provenance_refs=_merged_provenance(
            item for observation in canonical for item in observation.provenance_refs
        ),
    )


@dataclass(frozen=True, slots=True)
class CandidateCriterionValue(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_candidate_criterion_value_v3"

    criterion: HedonicCriterion
    estimate: NumericEstimate
    evidence_basis: DecisionEvidenceBasis
    source_view_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "criterion", HedonicCriterion(self.criterion))
        if not isinstance(self.estimate, NumericEstimate):
            raise TypeError("estimate must be NumericEstimate")
        basis = DecisionEvidenceBasis(self.evidence_basis)
        object.__setattr__(self, "evidence_basis", basis)
        source_ids = _normalized_text_tuple(
            self.source_view_ids,
            "source_view_ids",
            identifiers=True,
        )
        if basis is DecisionEvidenceBasis.HUMAN_OBSERVATION and not source_ids:
            raise ValueError("human-observation criteria require source_view_ids")
        if basis in {
            DecisionEvidenceBasis.PREDICTED,
            DecisionEvidenceBasis.GENERIC_SCORE,
        } and not source_ids:
            raise ValueError("predicted and generic criteria require source_view_ids")
        if (
            self.estimate.value.state is ValueState.KNOWN
            and basis is not DecisionEvidenceBasis.HUMAN_OBSERVATION
        ):
            raise ValueError(
                "known decision criteria require linked HUMAN_OBSERVATION evidence"
            )
        object.__setattr__(self, "source_view_ids", source_ids)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateCriterionValue:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            criterion=HedonicCriterion(data["criterion"]),
            estimate=NumericEstimate.from_dict(data["estimate"]),
            evidence_basis=DecisionEvidenceBasis(data["evidence_basis"]),
            source_view_ids=tuple(data["source_view_ids"]),
        )


@dataclass(frozen=True, slots=True)
class DecisionCandidate(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_decision_candidate_v2"

    candidate_id: str
    criteria: tuple[CandidateCriterionValue, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            _normalized_identifier(self.candidate_id, "candidate_id"),
        )
        criteria = _canonical_views(
            self.criteria,
            record_type=CandidateCriterionValue,
            field_name="criteria",
        )
        criterion_ids = tuple(item.criterion for item in criteria)
        if not criteria or len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError("decision candidate requires unique native criteria")
        object.__setattr__(self, "criteria", criteria)

    @property
    def criteria_by_id(self) -> Mapping[HedonicCriterion, CandidateCriterionValue]:
        return MappingProxyType({item.criterion: item for item in self.criteria})

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DecisionCandidate:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            candidate_id=data["candidate_id"],
            criteria=tuple(
                CandidateCriterionValue.from_dict(item) for item in data["criteria"]
            ),
        )


@dataclass(frozen=True, slots=True)
class ParetoDecisionState(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "hedonic_pareto_decision_state_v4"

    view_id: str
    condition_scope_id: str
    candidates: tuple[DecisionCandidate, ...]
    pareto_front_ids: tuple[str, ...]
    dominated_ids: tuple[str, ...]
    unresolved_ids: tuple[str, ...]
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        for field_name in ("view_id", "condition_scope_id"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        candidates = _canonical_views(
            self.candidates,
            record_type=DecisionCandidate,
            field_name="candidates",
        )
        candidate_ids = tuple(item.candidate_id for item in candidates)
        if len(candidate_ids) != 2 or len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(
                "Pareto decision currently requires exactly two unique candidates"
            )
        object.__setattr__(self, "candidates", candidates)
        for field_name in ("pareto_front_ids", "dominated_ids", "unresolved_ids"):
            object.__setattr__(
                self,
                field_name,
                _normalized_text_tuple(
                    getattr(self, field_name),
                    field_name,
                    identifiers=True,
                ),
            )
        known_ids = set(candidate_ids)
        if set(self.pareto_front_ids) | set(self.dominated_ids) != known_ids:
            raise ValueError("front and dominated IDs must cover every candidate")
        if set(self.pareto_front_ids) & set(self.dominated_ids):
            raise ValueError("front and dominated IDs must not overlap")
        if not set(self.unresolved_ids) <= known_ids:
            raise ValueError("unresolved IDs must reference decision candidates")
        if set(self.unresolved_ids) & set(self.dominated_ids):
            raise ValueError("unresolved candidates cannot be declared dominated")
        object.__setattr__(self, "provenance_refs", _required_provenance(self.provenance_refs))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ParetoDecisionState:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            view_id=data["view_id"],
            condition_scope_id=data["condition_scope_id"],
            candidates=tuple(DecisionCandidate.from_dict(item) for item in data["candidates"]),
            pareto_front_ids=tuple(data["pareto_front_ids"]),
            dominated_ids=tuple(data["dominated_ids"]),
            unresolved_ids=tuple(data["unresolved_ids"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def _observation_index(
    observations: Iterable[TemporalPreferenceObservation],
) -> Mapping[str, tuple[TemporalPreferenceObservation, ...]]:
    by_id: dict[str, list[TemporalPreferenceObservation]] = {}
    for observation in observations:
        if not isinstance(observation, TemporalPreferenceObservation):
            raise TypeError(
                "linked_observations must contain TemporalPreferenceObservation values"
            )
        by_id.setdefault(observation.view_id, []).append(observation)
    return MappingProxyType(
        {view_id: tuple(values) for view_id, values in by_id.items()}
    )


def _linked_arm_observation(
    candidate: DecisionCandidate,
    value: CandidateCriterionValue,
    observations_by_id: Mapping[str, tuple[TemporalPreferenceObservation, ...]],
) -> TemporalPreferenceObservation | None:
    if value.evidence_basis is not DecisionEvidenceBasis.HUMAN_OBSERVATION:
        if value.estimate.value.state is ValueState.KNOWN:  # defensive
            raise ValueError(
                "known decision criteria require linked HUMAN_OBSERVATION evidence"
            )
        return None
    if len(value.source_view_ids) != 1:
        raise ValueError(
            "human decision criteria require exactly one temporal observation"
        )
    source_id = value.source_view_ids[0]
    matches = observations_by_id.get(source_id, ())
    if len(matches) != 1:
        raise ValueError(
            "human decision criteria must resolve one unique temporal observation"
        )
    observation = matches[0]
    if observation.condition.endpoint is not value.criterion:
        raise ValueError("decision criterion does not match observation endpoint")
    if candidate.candidate_id == observation.condition.sample_a_id:
        observed_rating = observation.rating_a
    elif candidate.candidate_id == observation.condition.sample_b_id:
        observed_rating = observation.rating_b
    else:
        raise ValueError(
            "decision candidate must match one exact temporal-observation sample arm"
        )
    if value.estimate != observed_rating:
        raise ValueError(
            "decision estimate must equal the exact linked observation arm rating"
        )
    return observation


@dataclass(frozen=True, slots=True)
class _ValidatedDecision:
    condition_scope_id: str
    pareto_front_ids: tuple[str, ...]
    dominated_ids: tuple[str, ...]
    unresolved_ids: tuple[str, ...]
    provenance_refs: tuple[ProvenanceRef, ...]


def _dominates(
    left: DecisionCandidate,
    right: DecisionCandidate,
) -> bool:
    left_map = left.criteria_by_id
    right_map = right.criteria_by_id
    if set(left_map) != set(right_map):
        return False
    strictly_better = False
    for criterion in sorted(left_map, key=lambda item: item.value):
        left_value = left_map[criterion]
        right_value = right_map[criterion]
        left_bounds = left_value.estimate.bounds
        right_bounds = right_value.estimate.bounds
        if left_bounds is None or right_bounds is None:
            return False
        if criterion.direction is CriterionDirection.MAXIMIZE:
            if left_bounds[0] < right_bounds[1]:
                return False
            strictly_better = strictly_better or left_bounds[0] > right_bounds[1]
        else:
            if left_bounds[1] > right_bounds[0]:
                return False
            strictly_better = strictly_better or left_bounds[1] < right_bounds[0]
    return strictly_better


def _validate_decision_candidates(
    candidates: tuple[DecisionCandidate, ...],
    observations: Iterable[TemporalPreferenceObservation],
) -> _ValidatedDecision:
    if len(candidates) != 2:
        raise ValueError(
            "hedonic Pareto derivation currently requires exactly two candidates"
        )
    criteria_sets = tuple(set(candidate.criteria_by_id) for candidate in candidates)
    if criteria_sets[0] != criteria_sets[1]:
        raise ValueError("paired decision candidates require identical native criteria")
    observations_by_id = _observation_index(observations)
    linked_conditions: dict[str, ComparisonCondition] = {}
    linked_observations: dict[str, TemporalPreferenceObservation] = {}
    unresolved_ids: set[str] = set()
    condition_scope_keys: set[tuple[str, ...]] = set()
    left, right = candidates
    for criterion in sorted(criteria_sets[0], key=lambda item: item.value):
        left_value = left.criteria_by_id[criterion]
        right_value = right.criteria_by_id[criterion]
        left_observation = _linked_arm_observation(
            left,
            left_value,
            observations_by_id,
        )
        right_observation = _linked_arm_observation(
            right,
            right_value,
            observations_by_id,
        )
        if (left_observation is None) != (right_observation is None):
            raise ValueError(
                "both candidate cells for one criterion must share one paired observation"
            )
        if left_observation is not None and right_observation is not None:
            if left_observation.content_sha256 != right_observation.content_sha256:
                raise ValueError(
                    "both candidate cells for one criterion must share one paired observation"
                )
            condition = left_observation.condition
            if {left.candidate_id, right.candidate_id} != {
                condition.sample_a_id,
                condition.sample_b_id,
            }:
                raise ValueError(
                    "paired decision candidate IDs must equal the observation sample pair"
                )
            linked_conditions[condition.content_sha256] = condition
            linked_observations[left_observation.content_sha256] = left_observation
            condition_scope_keys.add(
                (
                    condition.sample_a_id,
                    condition.sample_b_id or "",
                    condition.concentration_a,
                    condition.concentration_b or "",
                    condition.matrix,
                    condition.temporal_window,
                    condition.context,
                    left_observation.assessor.content_sha256,
                )
            )
        for candidate, value in ((left, left_value), (right, right_value)):
            if value.estimate.value.state is ValueState.UNKNOWN:
                unresolved_ids.add(candidate.candidate_id)
    if not linked_conditions:
        raise ValueError(
            "hedonic Pareto decisions require at least one exact paired observation"
        )
    if len(condition_scope_keys) != 1:
        raise ValueError(
            "all decision criteria must share the exact sample, concentration, matrix, "
            "time, context, participant, session, and assessor/protocol scope"
        )
    dominated = {
        candidate.candidate_id
        for candidate in candidates
        if any(
            other.candidate_id != candidate.candidate_id
            and _dominates(other, candidate)
            for other in candidates
        )
    }
    front = {item.candidate_id for item in candidates} - dominated
    condition_scope_id = _stable_id(
        "hedonic-condition-scope",
        {
            "condition_sha256s": tuple(sorted(linked_conditions)),
            "assessor_sha256": next(iter(condition_scope_keys))[-1],
        },
    )
    return _ValidatedDecision(
        condition_scope_id=condition_scope_id,
        pareto_front_ids=tuple(sorted(front)),
        dominated_ids=tuple(sorted(dominated)),
        unresolved_ids=tuple(sorted(unresolved_ids)),
        provenance_refs=_merged_provenance(
            ref
            for observation in linked_observations.values()
            for ref in observation.provenance_refs
        ),
    )


def derive_pareto_decision(
    view_id: str,
    *,
    candidates: Iterable[DecisionCandidate],
    linked_observations: Iterable[TemporalPreferenceObservation],
) -> ParetoDecisionState:
    canonical = _canonical_views(
        candidates,
        record_type=DecisionCandidate,
        field_name="candidates",
    )
    evidence_views = tuple(linked_observations)
    validated = _validate_decision_candidates(canonical, evidence_views)
    return ParetoDecisionState(
        view_id=view_id,
        condition_scope_id=validated.condition_scope_id,
        candidates=canonical,
        pareto_front_ids=validated.pareto_front_ids,
        dominated_ids=validated.dominated_ids,
        unresolved_ids=validated.unresolved_ids,
        provenance_refs=validated.provenance_refs,
    )


_HedonicView = (
    MaterialPriorView
    | MixtureExpectationView
    | InteractionResidualView
    | TemporalPreferenceObservation
    | CriterionPreferenceView
    | PopulationPreferenceView
    | AggregatePreferenceView
    | ParetoDecisionState
)


@dataclass(frozen=True, slots=True)
class HedonicEvidencePlatform(_CanonicalRecord):
    """Canonical eight-view packet; exact duplicates collapse, conflicts remain."""

    SCHEMA_VERSION: ClassVar[str] = "hedonic_evidence_platform_v4"

    material_priors: tuple[MaterialPriorView, ...] = ()
    mixture_expectations: tuple[MixtureExpectationView, ...] = ()
    interaction_residuals: tuple[InteractionResidualView, ...] = ()
    temporal_observations: tuple[TemporalPreferenceObservation, ...] = ()
    criterion_preferences: tuple[CriterionPreferenceView, ...] = ()
    population_views: tuple[PopulationPreferenceView, ...] = ()
    aggregate_views: tuple[AggregatePreferenceView, ...] = ()
    decision_states: tuple[ParetoDecisionState, ...] = ()

    def __post_init__(self) -> None:
        specifications = (
            ("material_priors", MaterialPriorView),
            ("mixture_expectations", MixtureExpectationView),
            ("interaction_residuals", InteractionResidualView),
            ("temporal_observations", TemporalPreferenceObservation),
            ("criterion_preferences", CriterionPreferenceView),
            ("population_views", PopulationPreferenceView),
            ("aggregate_views", AggregatePreferenceView),
            ("decision_states", ParetoDecisionState),
        )
        for field_name, record_type in specifications:
            object.__setattr__(
                self,
                field_name,
                _canonical_views(
                    getattr(self, field_name),
                    record_type=record_type,
                    field_name=field_name,
                ),
            )
        for decision in self.decision_states:
            validated = _validate_decision_candidates(
                decision.candidates,
                self.temporal_observations,
            )
            if decision.condition_scope_id != validated.condition_scope_id:
                raise ValueError(
                    "decision condition scope is not derived from platform observations"
                )
            if decision.provenance_refs != validated.provenance_refs:
                raise ValueError(
                    "decision provenance is not derived from platform observations"
                )
            if (
                decision.pareto_front_ids != validated.pareto_front_ids
                or decision.dominated_ids != validated.dominated_ids
                or decision.unresolved_ids != validated.unresolved_ids
            ):
                raise ValueError(
                    "decision partitions must be recomputed from platform observations"
                )

    @property
    def all_views(self) -> tuple[_HedonicView, ...]:
        return (
            *self.material_priors,
            *self.mixture_expectations,
            *self.interaction_residuals,
            *self.temporal_observations,
            *self.criterion_preferences,
            *self.population_views,
            *self.aggregate_views,
            *self.decision_states,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HedonicEvidencePlatform:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            material_priors=tuple(
                MaterialPriorView.from_dict(item) for item in data.get("material_priors", ())
            ),
            mixture_expectations=tuple(
                MixtureExpectationView.from_dict(item)
                for item in data.get("mixture_expectations", ())
            ),
            interaction_residuals=tuple(
                InteractionResidualView.from_dict(item)
                for item in data.get("interaction_residuals", ())
            ),
            temporal_observations=tuple(
                TemporalPreferenceObservation.from_dict(item)
                for item in data.get("temporal_observations", ())
            ),
            criterion_preferences=tuple(
                CriterionPreferenceView.from_dict(item)
                for item in data.get("criterion_preferences", ())
            ),
            population_views=tuple(
                PopulationPreferenceView.from_dict(item)
                for item in data.get("population_views", ())
            ),
            aggregate_views=tuple(
                AggregatePreferenceView.from_dict(item)
                for item in data.get("aggregate_views", ())
            ),
            decision_states=tuple(
                ParetoDecisionState.from_dict(item)
                for item in data.get("decision_states", ())
            ),
        )


def _design_provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="hedonic-platform:design-spec-v1",
        source_ref=(
            "repo://docs/superpowers/specs/"
            "2026-08-31-perfume-intelligence-plane-synthesis-design.md#6"
        ),
        evidence_class=EvidenceClass.OFFICIAL_RECORD,
        independence_key="design-contract:hedonic-platform-v1",
    )


_DESIGN_HASH = sha256(
    _canonical_json_bytes(
        {
            "criteria": tuple(item.value for item in HedonicCriterion),
            "outcomes": tuple(item.value for item in PreferenceOutcome),
            "views": (
                "material_prior",
                "mixture_expectation",
                "interaction_residual",
                "temporal_observation",
                "criterion_preference",
                "population_structure",
                "categorical_aggregate",
                "pareto_decision",
            ),
        }
    )
).hexdigest()


@dataclass(frozen=True, slots=True)
class _SupportAtom:
    atom_id: str
    bounds: UnitInterval
    support_measure: SupportMeasure
    provenance_refs: tuple[ProvenanceRef, ...]


def _direct_evidence_atom(view: Any) -> _SupportAtom:
    return _SupportAtom(
        atom_id=f"evidence:{view.view_id}:{view.content_sha256}",
        bounds=view.support,
        support_measure=SupportMeasure.EVIDENCE_SUPPORT,
        provenance_refs=view.provenance_refs,
    )


def _declaration_atom(view: Any) -> _SupportAtom:
    return _SupportAtom(
        atom_id=f"declaration:{view.view_id}:{view.content_sha256}",
        bounds=UnitInterval(1.0, 1.0),
        support_measure=SupportMeasure.DECLARATION_PRESENCE,
        provenance_refs=view.provenance_refs,
    )


def _canonical_support_atoms(values: Iterable[_SupportAtom]) -> tuple[_SupportAtom, ...]:
    by_id: dict[str, _SupportAtom] = {}
    for value in values:
        current = by_id.get(value.atom_id)
        if current is not None and current != value:
            raise ValueError(f"support atom {value.atom_id!r} has conflicting definitions")
        by_id[value.atom_id] = value
    return tuple(by_id[key] for key in sorted(by_id))


def _views_with_id(
    platform: HedonicEvidencePlatform,
    view_id: str,
) -> tuple[_HedonicView, ...]:
    return tuple(view for view in platform.all_views if view.view_id == view_id)


def _support_atoms_for_view(
    platform: HedonicEvidencePlatform,
    view: _HedonicView,
) -> tuple[_SupportAtom, ...]:
    if isinstance(
        view,
        (
            MaterialPriorView,
            MixtureExpectationView,
            TemporalPreferenceObservation,
            PopulationPreferenceView,
        ),
    ):
        return (_direct_evidence_atom(view),)
    linked_ids: tuple[str, ...]
    if isinstance(view, InteractionResidualView):
        linked_ids = (view.expectation_view_id, view.observation_id)
    elif isinstance(view, CriterionPreferenceView):
        linked_ids = tuple(item.observation_id for item in view.outcomes)
    elif isinstance(view, AggregatePreferenceView):
        linked_ids = view.observation_ids
    elif isinstance(view, ParetoDecisionState):
        linked_ids = tuple(
            source_id
            for candidate in view.candidates
            for value in candidate.criteria
            if value.evidence_basis is DecisionEvidenceBasis.HUMAN_OBSERVATION
            for source_id in value.source_view_ids
        )
    else:
        linked_ids = ()
    linked_atoms = (
        atom
        for linked_id in linked_ids
        for linked_view in _views_with_id(platform, linked_id)
        if not isinstance(linked_view, ParetoDecisionState)
        for atom in _support_atoms_for_view(platform, linked_view)
    )
    atoms: tuple[_SupportAtom, ...]
    if isinstance(view, ParetoDecisionState):
        atoms = (_declaration_atom(view), *tuple(linked_atoms))
    else:
        atoms = tuple(linked_atoms)
    return _canonical_support_atoms(atoms)


def _derived_support_complete(
    platform: HedonicEvidencePlatform,
    view: InteractionResidualView | CriterionPreferenceView | AggregatePreferenceView,
) -> bool:
    if isinstance(view, InteractionResidualView):
        expectations = tuple(
            item
            for item in _views_with_id(platform, view.expectation_view_id)
            if isinstance(item, MixtureExpectationView)
        )
        observations = tuple(
            item
            for item in _views_with_id(platform, view.observation_id)
            if isinstance(item, TemporalPreferenceObservation)
        )
        return len(expectations) == len(observations) == 1
    linked_ids = (
        tuple(item.observation_id for item in view.outcomes)
        if isinstance(view, CriterionPreferenceView)
        else view.observation_ids
    )
    return bool(linked_ids) and all(
        len(
            tuple(
                item
                for item in _views_with_id(platform, linked_id)
                if isinstance(item, TemporalPreferenceObservation)
            )
        )
        == 1
        for linked_id in linked_ids
    )


@dataclass(frozen=True, slots=True)
class _ClaimDraft:
    key: str
    value: str
    kind: ClaimKind
    authority: AuthorityCeiling
    support_atoms: tuple[_SupportAtom, ...]
    provenance_refs: tuple[ProvenanceRef, ...]


_AUTHORITY_HOLDS: Mapping[str, str] = MappingProxyType(
    {
        "strict_similarity": "NOT TESTED / HOLD: strict similarity is outside this evidence scope.",
        "observed_smell": "NOT TESTED / HOLD: a preference outcome does not establish odor identity.",
        "liking_generalization": "NOT TESTED / HOLD: exact participants and conditions cannot be generalized.",
        "physical_performance": "NOT TESTED / HOLD: physical performance is not measured here.",
        "safety": "NOT TESTED / HOLD: safety is outside this evidence plane.",
        "stability": "NOT TESTED / HOLD: stability is outside this evidence plane.",
        "compounding": "NOT TESTED / HOLD: compounding is not authorized by preference evidence.",
        "release": "NOT TESTED / HOLD: release is not authorized by preference evidence.",
    }
)


def _condition_text(condition: ComparisonCondition) -> str:
    sample_b = condition.sample_b_id or "none"
    concentration_b = condition.concentration_b or "none"
    return (
        f"condition {condition.condition_id}; A {condition.sample_a_id} at "
        f"{condition.concentration_a}; B {sample_b} at {concentration_b}; matrix "
        f"{condition.matrix}; time {condition.temporal_window}; endpoint "
        f"{condition.endpoint.value}; context {condition.context}"
    )


def _claim_drafts(
    platform: HedonicEvidencePlatform,
    authority: AuthorityCeiling,
    design_ref: ProvenanceRef,
) -> tuple[_ClaimDraft, ...]:
    drafts: list[_ClaimDraft] = []
    for prior in platform.material_priors:
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.material_prior.{_slug(prior.view_id)}",
                value=(
                    f"Predicted prior only for {prior.subject_id}; basis {prior.basis.value}; "
                    f"{_condition_text(prior.condition)}; estimate state "
                    f"{prior.estimate.value.state.value}."
                ),
                kind=ClaimKind.HYPOTHESIS,
                authority=AuthorityCeiling.HYPOTHESIS_ONLY,
                support_atoms=_support_atoms_for_view(platform, prior),
                provenance_refs=prior.provenance_refs,
            )
        )
    for expectation in platform.mixture_expectations:
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.mixture_expectation.{_slug(expectation.view_id)}",
                value=(
                    f"Predicted expectation only using {expectation.method.value}; "
                    f"{_condition_text(expectation.condition)}; estimate state "
                    f"{expectation.expected_difference.value.state.value}."
                ),
                kind=ClaimKind.HYPOTHESIS,
                authority=AuthorityCeiling.HYPOTHESIS_ONLY,
                support_atoms=_support_atoms_for_view(platform, expectation),
                provenance_refs=expectation.provenance_refs,
            )
        )
    for residual in platform.interaction_residuals:
        residual_authority = (
            AuthorityCeiling.EVIDENCE_LIMITED
            if _derived_support_complete(platform, residual)
            else AuthorityCeiling.HYPOTHESIS_ONLY
        )
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.interaction_residual.{_slug(residual.view_id)}",
                value=(
                    f"Exact-condition residual links expectation {residual.expectation_view_id} "
                    f"and observation {residual.observation_id}; "
                    f"{_condition_text(residual.condition)}; "
                    f"residual state {residual.residual.value.state.value}."
                ),
                kind=ClaimKind.DIAGNOSTIC,
                authority=residual_authority,
                support_atoms=_support_atoms_for_view(platform, residual),
                provenance_refs=residual.provenance_refs,
            )
        )
    for observation in platform.temporal_observations:
        assessor = observation.assessor
        order = " -> ".join(assessor.realized_order)
        predecessor = assessor.predecessor_sample_id or "none"
        cluster = assessor.cluster_id or "unassigned"
        blinding_protocol = assessor.blinding_protocol_id or "unreported"
        missingness_reason = observation.missingness_reason or "none"
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.temporal_observation.{_slug(observation.view_id)}",
                value=(
                    f"Observed exact-scope outcome {observation.outcome.value} for participant "
                    f"{assessor.participant_id}, assessor {assessor.assessor_id}, "
                    f"cluster {cluster}, expertise "
                    f"{assessor.expertise.value}, sensitivity {assessor.sensitivity.value} "
                    f"({assessor.sensitivity_detail}), blinding {assessor.blinding.value} "
                    f"under {blinding_protocol}, session {assessor.session_id}, "
                    f"{assessor.day_id}, order sequence {assessor.order_sequence_id}, "
                    f"repeat {assessor.repeat_index}, realized order "
                    f"{order}, predecessor {predecessor}, carryover {assessor.carryover.value}, "
                    f"missingness {observation.missingness.value} ({missingness_reason}), "
                    f"assessor context {assessor.context}; "
                    f"{_condition_text(observation.condition)}."
                ),
                kind=ClaimKind.OBSERVATION,
                authority=AuthorityCeiling.EVIDENCE_LIMITED,
                support_atoms=_support_atoms_for_view(platform, observation),
                provenance_refs=observation.provenance_refs,
            )
        )
    for criterion_view in platform.criterion_preferences:
        criterion_authority = (
            AuthorityCeiling.EVIDENCE_LIMITED
            if _derived_support_complete(platform, criterion_view)
            else AuthorityCeiling.HYPOTHESIS_ONLY
        )
        outcomes = ", ".join(
            f"{item.observation_id}={item.outcome.value}" for item in criterion_view.outcomes
        )
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.criterion_preference.{_slug(criterion_view.view_id)}",
                value=(
                    f"Criterion-isolated outcomes retained without tie or abstention deletion: "
                    f"{outcomes}; {_condition_text(criterion_view.condition)}."
                ),
                kind=ClaimKind.OBSERVATION,
                authority=criterion_authority,
                support_atoms=_support_atoms_for_view(platform, criterion_view),
                provenance_refs=criterion_view.provenance_refs,
            )
        )
    for population_view in platform.population_views:
        participants = ", ".join(population_view.participant_ids)
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.population.{_slug(population_view.view_id)}",
                value=(
                    f"Cluster {population_view.cluster_id} ({participants}) retains outcome "
                    f"{population_view.outcome.value} with stability "
                    f"{population_view.stability.value}; "
                    f"{_condition_text(population_view.condition)}."
                ),
                kind=ClaimKind.OBSERVATION,
                authority=AuthorityCeiling.EVIDENCE_LIMITED,
                support_atoms=_support_atoms_for_view(platform, population_view),
                provenance_refs=population_view.provenance_refs,
            )
        )
    for aggregate_view in platform.aggregate_views:
        aggregate_authority = (
            AuthorityCeiling.EVIDENCE_LIMITED
            if _derived_support_complete(platform, aggregate_view)
            else AuthorityCeiling.HYPOTHESIS_ONLY
        )
        counts = ", ".join(
            f"{item.outcome.value}={item.count}" for item in aggregate_view.outcome_counts
        )
        clusters = ", ".join(aggregate_view.cluster_ids) or "unassigned"
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.aggregate.{_slug(aggregate_view.view_id)}",
                value=(
                    f"Categorical aggregate only using "
                    f"{aggregate_view.aggregation_method.value}; counts {counts}; clusters "
                    f"{clusters}; no pooled winner or scalar utility is inferred; "
                    f"{_condition_text(aggregate_view.condition)}."
                ),
                kind=ClaimKind.OBSERVATION,
                authority=aggregate_authority,
                support_atoms=_support_atoms_for_view(platform, aggregate_view),
                provenance_refs=aggregate_view.provenance_refs,
            )
        )
    for decision in platform.decision_states:
        decision_authority = _decision_authority(decision, platform)
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.pareto_decision.{_slug(decision.view_id)}",
                value=(
                    f"Non-compensatory decision state for {decision.condition_scope_id}; "
                    f"front {', '.join(decision.pareto_front_ids)}; dominated "
                    f"{', '.join(decision.dominated_ids) or 'none'}; unresolved "
                    f"{', '.join(decision.unresolved_ids) or 'none'}."
                ),
                kind=ClaimKind.DIAGNOSTIC,
                authority=decision_authority,
                support_atoms=_support_atoms_for_view(platform, decision),
                provenance_refs=decision.provenance_refs,
            )
        )
    for key, value in _AUTHORITY_HOLDS.items():
        drafts.append(
            _ClaimDraft(
                key=f"hedonic.authority_hold.{key}",
                value=value,
                kind=ClaimKind.PROHIBITION,
                authority=AuthorityCeiling.WITHHELD,
                support_atoms=(
                    _SupportAtom(
                        atom_id=f"declaration:authority-hold:{key}",
                        bounds=UnitInterval(1.0, 1.0),
                        support_measure=SupportMeasure.DECLARATION_PRESENCE,
                        provenance_refs=(design_ref,),
                    ),
                ),
                provenance_refs=(design_ref,),
            )
        )
    if any(
        not draft.authority.is_no_stronger_than(authority)
        for draft in drafts
    ):
        raise ValueError("generated claim exceeds platform authority")
    return tuple(sorted(drafts, key=lambda item: (item.key, item.value)))


def _view_fields(platform: HedonicEvidencePlatform) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    return (
        ("material_prior", platform.material_priors),
        ("mixture_expectation", platform.mixture_expectations),
        ("interaction_residual", platform.interaction_residuals),
        ("temporal_observation", platform.temporal_observations),
        ("criterion_preference", platform.criterion_preferences),
        ("population", platform.population_views),
        ("aggregate", platform.aggregate_views),
        ("pareto_decision", platform.decision_states),
    )


def _conflicts(platform: HedonicEvidencePlatform) -> tuple[PlaneConflict, ...]:
    conflicts: list[PlaneConflict] = []
    for view_kind, records in _view_fields(platform):
        by_id: dict[str, list[Any]] = {}
        for record in records:
            by_id.setdefault(record.view_id, []).append(record)
        for view_id, variants in sorted(by_id.items()):
            if len(variants) < 2:
                continue
            conflicts.append(
                PlaneConflict(
                    conflict_id=_stable_id(
                        "hedonic-duplicate-conflict",
                        {"kind": view_kind, "variants": tuple(item.as_dict() for item in variants)},
                    ),
                    claim_key=f"hedonic.duplicate.{_slug(view_id)}",
                    alternatives=tuple(item.content_sha256 for item in variants),
                    reason=(
                        "Discordant duplicate record ID retained; provenance resolution is "
                        "required without averaging or double-counting."
                    ),
                    provenance_refs=_merged_provenance(
                        item for variant in variants for item in variant.provenance_refs
                    ),
                )
            )

    grouped_population: dict[str, list[PopulationPreferenceView]] = {}
    for view in platform.population_views:
        if view.stability is ClusterStability.STABLE:
            grouped_population.setdefault(view.condition.content_sha256, []).append(view)
    for variants in grouped_population.values():
        directional = {item.outcome for item in variants}
        if not {
            PreferenceOutcome.PREFER_A,
            PreferenceOutcome.PREFER_B,
        } <= directional:
            continue
        conflicts.append(
            PlaneConflict(
                conflict_id=_stable_id(
                    "hedonic-opposed-clusters",
                    tuple(item.as_dict() for item in variants),
                ),
                claim_key="hedonic.population.opposed-clusters",
                alternatives=tuple(
                    f"{item.cluster_id}:{item.outcome.value}" for item in variants
                ),
                reason="Stable opposing assessor clusters are retained rather than pooled.",
                provenance_refs=_merged_provenance(
                    item for variant in variants for item in variant.provenance_refs
                ),
            )
        )
    return tuple(conflicts)


def _unknowns(
    platform: HedonicEvidencePlatform,
    conflicts: tuple[PlaneConflict, ...],
    design_ref: ProvenanceRef,
) -> tuple[UnknownFact, ...]:
    unknowns: list[UnknownFact] = [
        UnknownFact(
            unknown_id="unknown:hedonic:liking-generalization",
            field_key="hedonic.liking_generalization",
            reason="Exact participant and condition evidence cannot establish broader preference.",
            needed_evidence="A prospectively scoped participant sample with grouped validation.",
            provenance_refs=(design_ref,),
        )
    ]
    for observation in platform.temporal_observations:
        if observation.outcome.is_abstention:
            unknowns.append(
                UnknownFact(
                    unknown_id=f"unknown:hedonic:outcome:{observation.view_id}",
                    field_key=f"hedonic.observation.{observation.view_id}",
                    reason=f"Outcome is {observation.outcome.value}, not a numeric zero.",
                    needed_evidence="A valid repeat under the same protocol if decision-relevant.",
                    provenance_refs=observation.provenance_refs,
                )
            )
    if any(
        conflict.claim_key == "hedonic.population.opposed-clusters"
        for conflict in conflicts
    ):
        provenance = _merged_provenance(
            item
            for conflict in conflicts
            if conflict.claim_key == "hedonic.population.opposed-clusters"
            for item in conflict.provenance_refs
        )
        unknowns.append(
            UnknownFact(
                unknown_id="unknown:hedonic:population-generalization",
                field_key="hedonic.population_generalization",
                reason="Stable clusters oppose, so a pooled population direction is undefined.",
                needed_evidence="Cluster-stratified replication or an explicit decision population.",
                provenance_refs=provenance,
            )
        )
    for conflict in conflicts:
        if conflict.claim_key.startswith("hedonic.duplicate."):
            unknowns.append(
                UnknownFact(
                    unknown_id=f"unknown:hedonic:duplicate:{_slug(conflict.conflict_id)}",
                    field_key=conflict.claim_key,
                    reason="Discordant duplicate evidence is unresolved.",
                    needed_evidence="Canonical-cell provenance adjudication.",
                    provenance_refs=conflict.provenance_refs,
                )
            )
    return tuple(unknowns)


def _native_criteria(
    authority: AuthorityCeiling,
    provenance_refs: tuple[ProvenanceRef, ...],
) -> tuple[ParetoCriterion, ...]:
    return tuple(
        ParetoCriterion(
            criterion_id=f"hedonic.{criterion.value}",
            direction=criterion.direction,
            value=CriterionValue.unknown(
                "Evidence remains candidate-, participant-, cluster-, condition-, and time-scoped."
            ),
            unit="exact-scope evidence state",
            authority_ceiling=authority,
            provenance_refs=provenance_refs,
        )
        for criterion in HedonicCriterion
    )


def _decision_authority(
    decision: ParetoDecisionState,
    platform: HedonicEvidencePlatform,
) -> AuthorityCeiling:
    validated = _validate_decision_candidates(
        decision.candidates,
        platform.temporal_observations,
    )
    has_human_receipt = any(
        item.evidence_class in _HUMAN_EVIDENCE_CLASSES
        for item in validated.provenance_refs
    )
    if has_human_receipt and not validated.unresolved_ids:
        return AuthorityCeiling.EVIDENCE_LIMITED
    return AuthorityCeiling.HYPOTHESIS_ONLY


def _authority(platform: HedonicEvidencePlatform) -> AuthorityCeiling:
    if (
        platform.temporal_observations
        or platform.population_views
        or any(
            _derived_support_complete(platform, view)
            for view in platform.interaction_residuals
        )
        or any(
            _derived_support_complete(platform, view)
            for view in platform.criterion_preferences
        )
        or any(
            _derived_support_complete(platform, view)
            for view in platform.aggregate_views
        )
        or any(
            _decision_authority(decision, platform)
            is AuthorityCeiling.EVIDENCE_LIMITED
            for decision in platform.decision_states
        )
    ):
        return AuthorityCeiling.EVIDENCE_LIMITED
    if (
        platform.material_priors
        or platform.mixture_expectations
        or platform.interaction_residuals
        or platform.criterion_preferences
        or platform.aggregate_views
        or platform.decision_states
    ):
        return AuthorityCeiling.HYPOTHESIS_ONLY
    return AuthorityCeiling.WITHHELD


def assess_hedonic_platform(
    platform: HedonicEvidencePlatform,
    *,
    scope: AssessmentScope,
) -> PlaneAssessment:
    """Translate the eight-view packet into one exact-scope HEDONIC assessment."""

    if not isinstance(platform, HedonicEvidencePlatform):
        raise TypeError("platform must be HedonicEvidencePlatform")
    if not isinstance(scope, AssessmentScope):
        raise TypeError("scope must be AssessmentScope")
    authority = _authority(platform)
    design_ref = _design_provenance()
    drafts = _claim_drafts(platform, authority, design_ref)
    claims: list[ScopedClaim] = []
    intervals: list[SupportInterval] = []
    for draft in drafts:
        claim_id = _stable_id(
            "hedonic-claim",
            {"key": draft.key, "value": draft.value, "kind": draft.kind.value},
        )
        claims.append(
            ScopedClaim(
                claim_id=claim_id,
                claim_key=draft.key,
                claim_value=draft.value,
                claim_kind=draft.kind,
                authority_ceiling=draft.authority,
                provenance_refs=draft.provenance_refs,
            )
        )
        for atom in draft.support_atoms:
            intervals.append(
                SupportInterval(
                    interval_id=_stable_id(
                        "hedonic-support",
                        {
                            "claim_id": claim_id,
                            "atom_id": atom.atom_id,
                            "support": atom.bounds.as_dict(),
                            "measure": atom.support_measure.value,
                        },
                    ),
                    claim_id=claim_id,
                    lower=atom.bounds.lower,
                    upper=atom.bounds.upper,
                    provenance_refs=atom.provenance_refs,
                    support_measure=atom.support_measure,
                )
            )
    conflicts = _conflicts(platform)
    unknowns = _unknowns(platform, conflicts, design_ref)
    provenance = _merged_provenance(
        (design_ref, *(item for view in platform.all_views for item in view.provenance_refs))
    )
    criteria = _native_criteria(authority, provenance)
    experiments = [
        (
            "Repeat exact-condition coded comparisons with participant, cluster, criterion, "
            "time, participant/assessor identity, blinding protocol, order sequence, realized "
            "order, predecessor, carryover, missingness, day, session, and repeat retained."
        )
    ]
    if any(conflict.claim_key.startswith("hedonic.duplicate.") for conflict in conflicts):
        experiments.append(
            "Adjudicate discordant duplicate canonical cells from source receipts before fitting."
        )
    if any(conflict.claim_key == "hedonic.population.opposed-clusters" for conflict in conflicts):
        experiments.append(
            "Run a cluster-stratified balanced-order repeat without pooling opposing clusters."
        )
    if any(item.outcome.is_abstention for item in platform.temporal_observations):
        experiments.append(
            "Repeat only decision-relevant missing or aborted cells under the unchanged protocol."
        )
    failure_modes = []
    if any(conflict.claim_key.startswith("hedonic.duplicate.") for conflict in conflicts):
        failure_modes.append("discordant duplicate evidence cell")
    if any(conflict.claim_key == "hedonic.population.opposed-clusters" for conflict in conflicts):
        failure_modes.append("stable opposing assessor clusters")
    if any(item.outcome.is_abstention for item in platform.temporal_observations):
        failure_modes.append("missing or protocol outcome retained")
    assessment_payload = {
        "scope": scope.as_dict(),
        "platform": platform.as_dict(),
        "claims": tuple(item.as_dict() for item in claims),
        "conflicts": tuple(item.as_dict() for item in conflicts),
        "unknowns": tuple(item.as_dict() for item in unknowns),
        "authority": authority.value,
    }
    return PlaneAssessment(
        assessment_id=_stable_id("hedonic-platform", assessment_payload),
        module_id="hedonic-platform-v1",
        plane_id=PlaneId.HEDONIC,
        scope=scope,
        claims=tuple(claims),
        support_intervals=tuple(intervals),
        conflicts=conflicts,
        unknowns=unknowns,
        failure_modes=tuple(failure_modes),
        proposed_experiments=tuple(experiments),
        provenance_refs=provenance,
        authority_ceiling=authority,
        freshness_hashes=(platform.content_sha256, scope.content_sha256, _DESIGN_HASH),
        native_criteria=criteria,
    )


@dataclass(frozen=True, slots=True)
class HedonicPlatformPlaneAdapter:
    """Read-only structural adapter for the generic plane-synthesis protocol."""

    platform: HedonicEvidencePlatform
    scope: AssessmentScope

    def __post_init__(self) -> None:
        if not isinstance(self.platform, HedonicEvidencePlatform):
            raise TypeError("platform must be HedonicEvidencePlatform")
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be AssessmentScope")

    def to_plane_assessment(self) -> PlaneAssessment:
        return assess_hedonic_platform(self.platform, scope=self.scope)


__all__ = [
    "AggregatePreferenceView",
    "AggregationMethod",
    "AssessorContext",
    "BlindingState",
    "CandidateCriterionValue",
    "CarryoverState",
    "ClusterStability",
    "ComparisonCondition",
    "CriterionPreferenceView",
    "DecisionCandidate",
    "DecisionEvidenceBasis",
    "ExpertiseLevel",
    "HedonicCriterion",
    "HedonicEvidencePlatform",
    "HedonicPlatformPlaneAdapter",
    "InteractionResidualView",
    "LinkedOutcome",
    "MaterialPriorView",
    "MissingnessKind",
    "MixtureExpectationMethod",
    "MixtureExpectationView",
    "NumericEstimate",
    "NumericInterval",
    "OutcomeCount",
    "ParetoDecisionState",
    "PopulationPreferenceView",
    "PreferenceOutcome",
    "PriorBasis",
    "SensitivityState",
    "TemporalPreferenceObservation",
    "assess_hedonic_platform",
    "build_aggregate_preference_view",
    "build_criterion_preference_view",
    "derive_interaction_residual",
    "derive_pareto_decision",
]
