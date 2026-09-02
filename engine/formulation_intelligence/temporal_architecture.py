"""Immutable temporal subject hypotheses with a physical/sensory firewall.

Predicted physical evolution and participant-linked observed perception are
different record types and different claim keys.  Missing observations remain
explicit unknowns.  This module does not interpolate them, infer them from OAV,
or authorize formula, sensory, safety, performance, or release decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping

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
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _payload,
)

_MODULE_ID = "formulation_intelligence.temporal_architecture"


def _stable_id(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _unique_texts(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda item: (item.casefold(), item)))


def _reject_empirical_certainty(support: UnitInterval, field_name: str) -> None:
    if support.lower == 1.0:
        raise ValueError(f"{field_name} cannot declare empirical certainty")


class TemporalWindow(str, Enum):
    OPENING = "opening"
    MINUTE_5 = "5_minute"
    MINUTE_30 = "30_minute"
    HOUR_2 = "2_hour"
    HOUR_4 = "4_hour"
    HOUR_8 = "8_hour"
    HOUR_24 = "24_hour"


CANONICAL_TEMPORAL_SEQUENCE: tuple[TemporalWindow, ...] = (
    TemporalWindow.OPENING,
    TemporalWindow.MINUTE_5,
    TemporalWindow.MINUTE_30,
    TemporalWindow.HOUR_2,
    TemporalWindow.HOUR_4,
    TemporalWindow.HOUR_8,
    TemporalWindow.HOUR_24,
)
_WINDOW_ORDER = {window: index for index, window in enumerate(CANONICAL_TEMPORAL_SEQUENCE)}


class TemporalTransitionKind(str, Enum):
    CONTINUITY = "continuity"
    TRANSFORMATION = "transformation"
    BRIDGE_HANDOFF = "bridge_handoff"
    DELAYED_REVEAL = "delayed_reveal"
    DISCONTINUITY = "discontinuity"
    TAKEOVER = "takeover"
    GENERIC_RESIDUE_FAILURE = "generic_residue_failure"

    @property
    def is_handoff(self) -> bool:
        return self is TemporalTransitionKind.BRIDGE_HANDOFF


class WithinSniffPhase(str, Enum):
    ONSET = "onset"
    PEAK = "peak"
    OFFSET = "offset"


@dataclass(frozen=True, slots=True)
class TemporalHypothesisScope(_CanonicalRecord):
    """Exact target, concentration, temporal window, and matrix scope."""

    SCHEMA_VERSION = "temporal_hypothesis_scope_v2"

    target_scope: str
    subject_scope: str
    concentration_scope: str
    temporal_window: TemporalWindow
    matrix_scope: str
    condition_scope: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_scope",
            _normalized_identifier(self.target_scope, "target_scope"),
        )
        object.__setattr__(
            self,
            "subject_scope",
            _normalized_identifier(self.subject_scope, "subject_scope"),
        )
        object.__setattr__(
            self,
            "concentration_scope",
            _normalized_identifier(self.concentration_scope, "concentration_scope"),
        )
        object.__setattr__(
            self,
            "temporal_window",
            TemporalWindow(self.temporal_window),
        )
        object.__setattr__(
            self,
            "matrix_scope",
            _normalized_identifier(self.matrix_scope, "matrix_scope"),
        )
        object.__setattr__(
            self,
            "condition_scope",
            _normalized_identifier(self.condition_scope, "condition_scope"),
        )

    @property
    def base_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.target_scope,
            self.subject_scope,
            self.concentration_scope,
            self.matrix_scope,
            self.condition_scope,
        )

    @property
    def key(self) -> tuple[str, str, str, str, str, str]:
        return (*self.base_key, self.temporal_window.value)

    @property
    def plane_matrix_scope(self) -> str:
        subject = self.subject_scope
        matrix = self.matrix_scope
        concentration = self.concentration_scope
        condition = self.condition_scope
        return (
            f"subject[{len(subject)}]={subject};matrix[{len(matrix)}]={matrix};"
            f"concentration[{len(concentration)}]={concentration};"
            f"condition[{len(condition)}]={condition}"
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalHypothesisScope:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            target_scope=data["target_scope"],
            subject_scope=data["subject_scope"],
            concentration_scope=data["concentration_scope"],
            temporal_window=TemporalWindow(data["temporal_window"]),
            matrix_scope=data["matrix_scope"],
            condition_scope=data["condition_scope"],
        )


@dataclass(frozen=True, slots=True)
class PredictedPhysicalEvolution(_CanonicalRecord):
    """A physical-model prediction that cannot stand in for observed perception."""

    SCHEMA_VERSION = "predicted_physical_evolution_v2"

    prediction_id: str
    scope: TemporalHypothesisScope
    description: str
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]
    observed_perception: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "prediction_id",
            _normalized_identifier(self.prediction_id, "prediction_id"),
        )
        if not isinstance(self.scope, TemporalHypothesisScope):
            raise TypeError("scope must be a TemporalHypothesisScope")
        object.__setattr__(
            self,
            "description",
            _normalized_text(self.description, "description"),
        )
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be a UnitInterval")
        _reject_empirical_certainty(self.support, "physical predictions")
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("predicted physical evolution requires provenance")
        observed_classes = {
            EvidenceClass.DIRECT_OBSERVATION,
            EvidenceClass.USER_REPORT,
        }
        if any(item.evidence_class in observed_classes for item in provenance):
            raise ValueError("prediction provenance cannot be direct observation or user report")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PredictedPhysicalEvolution:
        data = _payload(payload, cls.SCHEMA_VERSION)
        flags = (
            "observed_perception",
            "sensory_authority",
            "liking_authority",
            "performance_authority",
        )
        if any(data.get(flag) is not False for flag in flags):
            raise ValueError("predicted physical authority flags must all remain false")
        return cls(
            prediction_id=data["prediction_id"],
            scope=TemporalHypothesisScope.from_dict(data["scope"]),
            description=data["description"],
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def _observed_provenance(
    values: tuple[ProvenanceRef, ...],
    field_name: str,
) -> tuple[ProvenanceRef, ...]:
    provenance = _merged_provenance(values)
    if not provenance:
        raise ValueError(f"{field_name} requires provenance")
    allowed = {EvidenceClass.DIRECT_OBSERVATION, EvidenceClass.USER_REPORT}
    if any(item.evidence_class not in allowed for item in provenance):
        raise ValueError(f"{field_name} provenance must be direct observation or user report")
    return provenance


@dataclass(frozen=True, slots=True)
class ParticipantLinkedObservation(_CanonicalRecord):
    """One descriptive observation bound to participant, repeat, and endpoint."""

    SCHEMA_VERSION = "participant_linked_temporal_observation_v2"

    observation_id: str
    scope: TemporalHypothesisScope
    participant_id: str
    repeat_id: str
    endpoint_id: str
    description: str
    provenance_refs: tuple[ProvenanceRef, ...]
    interpolated: bool = field(default=False, init=False)
    causal_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "observation_id",
            "participant_id",
            "repeat_id",
            "endpoint_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        if not isinstance(self.scope, TemporalHypothesisScope):
            raise TypeError("scope must be a TemporalHypothesisScope")
        object.__setattr__(
            self,
            "description",
            _normalized_text(self.description, "description"),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _observed_provenance(self.provenance_refs, "observed perception"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ParticipantLinkedObservation:
        data = _payload(payload, cls.SCHEMA_VERSION)
        flags = (
            "interpolated",
            "causal_authority",
            "liking_authority",
            "release_authority",
        )
        if any(data.get(flag) is not False for flag in flags):
            raise ValueError("participant observation authority flags must remain false")
        return cls(
            observation_id=data["observation_id"],
            scope=TemporalHypothesisScope.from_dict(data["scope"]),
            participant_id=data["participant_id"],
            repeat_id=data["repeat_id"],
            endpoint_id=data["endpoint_id"],
            description=data["description"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class WithinSniffObservation(_CanonicalRecord):
    """Optional participant-linked onset, peak, or offset observation."""

    SCHEMA_VERSION = "within_sniff_temporal_observation_v2"

    observation_id: str
    scope: TemporalHypothesisScope
    phase: WithinSniffPhase
    participant_id: str
    repeat_id: str
    endpoint_id: str
    description: str
    provenance_refs: tuple[ProvenanceRef, ...]
    interpolated: bool = field(default=False, init=False)
    causal_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_id",
            _normalized_identifier(self.observation_id, "observation_id"),
        )
        if not isinstance(self.scope, TemporalHypothesisScope):
            raise TypeError("scope must be a TemporalHypothesisScope")
        object.__setattr__(self, "phase", WithinSniffPhase(self.phase))
        for field_name in ("participant_id", "repeat_id", "endpoint_id"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "description",
            _normalized_text(self.description, "description"),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _observed_provenance(self.provenance_refs, "within-sniff observation"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WithinSniffObservation:
        data = _payload(payload, cls.SCHEMA_VERSION)
        flags = (
            "interpolated",
            "causal_authority",
            "liking_authority",
            "release_authority",
        )
        if any(data.get(flag) is not False for flag in flags):
            raise ValueError("within-sniff authority flags must remain false")
        return cls(
            observation_id=data["observation_id"],
            scope=TemporalHypothesisScope.from_dict(data["scope"]),
            phase=WithinSniffPhase(data["phase"]),
            participant_id=data["participant_id"],
            repeat_id=data["repeat_id"],
            endpoint_id=data["endpoint_id"],
            description=data["description"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def _canonical_observations(
    values: tuple[ParticipantLinkedObservation, ...],
) -> tuple[ParticipantLinkedObservation, ...]:
    by_id: dict[str, ParticipantLinkedObservation] = {}
    for value in values:
        if not isinstance(value, ParticipantLinkedObservation):
            raise TypeError("observed_perceptions must contain ParticipantLinkedObservation values")
        previous = by_id.get(value.observation_id)
        if previous is not None and previous != value:
            raise ValueError(f"observation_id {value.observation_id!r} has conflicting records")
        by_id[value.observation_id] = value
    return tuple(
        sorted(by_id.values(), key=lambda item: (item.content_sha256, item.observation_id))
    )


@dataclass(frozen=True, slots=True)
class TemporalWindowHypothesis(_CanonicalRecord):
    """Subject hypothesis and separated evidence at one required time window."""

    SCHEMA_VERSION = "temporal_window_hypothesis_v2"

    hypothesis_id: str
    scope: TemporalHypothesisScope
    subject_hypothesis: str
    predicted_physical: PredictedPhysicalEvolution | None
    observed_perceptions: tuple[ParticipantLinkedObservation, ...]
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]
    uncertainty: str
    counterfactual: str
    failure_mode: str
    minimum_resolving_experiment: str
    missing_observation_interpolated: bool = field(default=False, init=False)
    oav_as_observed_perception: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hypothesis_id",
            _normalized_identifier(self.hypothesis_id, "hypothesis_id"),
        )
        if not isinstance(self.scope, TemporalHypothesisScope):
            raise TypeError("scope must be a TemporalHypothesisScope")
        object.__setattr__(
            self,
            "subject_hypothesis",
            _normalized_text(self.subject_hypothesis, "subject_hypothesis"),
        )
        if self.predicted_physical is not None and not isinstance(
            self.predicted_physical,
            PredictedPhysicalEvolution,
        ):
            raise TypeError("predicted_physical must be a PredictedPhysicalEvolution or None")
        if self.predicted_physical is not None and self.predicted_physical.scope != self.scope:
            raise ValueError("predicted_physical must match the exact window scope")
        object.__setattr__(
            self,
            "observed_perceptions",
            _canonical_observations(tuple(self.observed_perceptions)),
        )
        if any(item.scope != self.scope for item in self.observed_perceptions):
            raise ValueError("observed_perceptions must match the exact window scope")
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be a UnitInterval")
        _reject_empirical_certainty(self.support, "temporal subject hypotheses")
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("temporal window hypotheses require provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        for field_name in (
            "uncertainty",
            "counterfactual",
            "failure_mode",
            "minimum_resolving_experiment",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @property
    def all_provenance(self) -> tuple[ProvenanceRef, ...]:
        predicted = (
            self.predicted_physical.provenance_refs if self.predicted_physical is not None else ()
        )
        return _merged_provenance(
            (
                *self.provenance_refs,
                *predicted,
                *(
                    ref
                    for observation in self.observed_perceptions
                    for ref in observation.provenance_refs
                ),
            )
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalWindowHypothesis:
        data = _payload(payload, cls.SCHEMA_VERSION)
        flags = ("missing_observation_interpolated", "oav_as_observed_perception")
        if any(data.get(flag) is not False for flag in flags):
            raise ValueError("temporal window firewall flags must remain false")
        return cls(
            hypothesis_id=data["hypothesis_id"],
            scope=TemporalHypothesisScope.from_dict(data["scope"]),
            subject_hypothesis=data["subject_hypothesis"],
            predicted_physical=(
                PredictedPhysicalEvolution.from_dict(data["predicted_physical"])
                if data.get("predicted_physical") is not None
                else None
            ),
            observed_perceptions=tuple(
                ParticipantLinkedObservation.from_dict(item)
                for item in data["observed_perceptions"]
            ),
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            uncertainty=data["uncertainty"],
            counterfactual=data["counterfactual"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


@dataclass(frozen=True, slots=True)
class TemporalTransitionSpec(_CanonicalRecord):
    """Sequence-position transition evidence before directional binding."""

    SCHEMA_VERSION = "temporal_transition_spec_v2"

    transition_spec_id: str
    kind: TemporalTransitionKind
    bridge_or_handoff: str | None
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]
    uncertainty: str
    counterfactual: str
    failure_mode: str
    minimum_resolving_experiment: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_spec_id",
            _normalized_identifier(self.transition_spec_id, "transition_spec_id"),
        )
        kind = TemporalTransitionKind(self.kind)
        object.__setattr__(self, "kind", kind)
        if self.bridge_or_handoff is not None:
            object.__setattr__(
                self,
                "bridge_or_handoff",
                _normalized_text(self.bridge_or_handoff, "bridge_or_handoff"),
            )
        if kind.is_handoff and self.bridge_or_handoff is None:
            raise ValueError("bridge_handoff transitions require bridge_or_handoff")
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be a UnitInterval")
        _reject_empirical_certainty(self.support, "temporal transition hypotheses")
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("temporal transitions require provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        for field_name in (
            "uncertainty",
            "counterfactual",
            "failure_mode",
            "minimum_resolving_experiment",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalTransitionSpec:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            transition_spec_id=data["transition_spec_id"],
            kind=TemporalTransitionKind(data["kind"]),
            bridge_or_handoff=data.get("bridge_or_handoff"),
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            uncertainty=data["uncertainty"],
            counterfactual=data["counterfactual"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


@dataclass(frozen=True, slots=True)
class TemporalTransitionHypothesis(_CanonicalRecord):
    """A transition spec bound to an ordered pair of windows and subjects."""

    SCHEMA_VERSION = "temporal_transition_hypothesis_v2"

    transition_id: str
    from_window: TemporalWindow
    to_window: TemporalWindow
    kind: TemporalTransitionKind
    from_subject: str
    to_subject: str
    bridge_or_handoff: str | None
    support: UnitInterval
    provenance_refs: tuple[ProvenanceRef, ...]
    uncertainty: str
    counterfactual: str
    failure_mode: str
    minimum_resolving_experiment: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_id",
            _normalized_identifier(self.transition_id, "transition_id"),
        )
        object.__setattr__(self, "from_window", TemporalWindow(self.from_window))
        object.__setattr__(self, "to_window", TemporalWindow(self.to_window))
        if self.from_window is self.to_window:
            raise ValueError("temporal transitions require distinct windows")
        kind = TemporalTransitionKind(self.kind)
        object.__setattr__(self, "kind", kind)
        for field_name in ("from_subject", "to_subject"):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )
        if self.bridge_or_handoff is not None:
            object.__setattr__(
                self,
                "bridge_or_handoff",
                _normalized_text(self.bridge_or_handoff, "bridge_or_handoff"),
            )
        if kind.is_handoff and self.bridge_or_handoff is None:
            raise ValueError("bridge_handoff transitions require bridge_or_handoff")
        if not isinstance(self.support, UnitInterval):
            raise TypeError("support must be a UnitInterval")
        _reject_empirical_certainty(self.support, "temporal transition hypotheses")
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("temporal transition hypotheses require provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        for field_name in (
            "uncertainty",
            "counterfactual",
            "failure_mode",
            "minimum_resolving_experiment",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @property
    def claim_value(self) -> str:
        bridge = f"; bridge={self.bridge_or_handoff}" if self.bridge_or_handoff is not None else ""
        return (
            f"{self.from_window.value}->{self.to_window.value}: {self.kind.value}; "
            f"subject={self.from_subject}->{self.to_subject}{bridge}"
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalTransitionHypothesis:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            transition_id=data["transition_id"],
            from_window=TemporalWindow(data["from_window"]),
            to_window=TemporalWindow(data["to_window"]),
            kind=TemporalTransitionKind(data["kind"]),
            from_subject=data["from_subject"],
            to_subject=data["to_subject"],
            bridge_or_handoff=data.get("bridge_or_handoff"),
            support=UnitInterval.from_dict(data["support"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            uncertainty=data["uncertainty"],
            counterfactual=data["counterfactual"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


def _canonical_sniff_observations(
    values: tuple[WithinSniffObservation, ...],
) -> tuple[WithinSniffObservation, ...]:
    by_id: dict[str, WithinSniffObservation] = {}
    for value in values:
        if not isinstance(value, WithinSniffObservation):
            raise TypeError("within_sniff_observations must contain WithinSniffObservation values")
        previous = by_id.get(value.observation_id)
        if previous is not None and previous != value:
            raise ValueError(f"observation_id {value.observation_id!r} has conflicting records")
        by_id[value.observation_id] = value
    return tuple(
        sorted(by_id.values(), key=lambda item: (item.content_sha256, item.observation_id))
    )


@dataclass(frozen=True, slots=True)
class TemporalArchitecture(_CanonicalRecord):
    """Seven-window subject architecture plus a semantic declared sequence."""

    SCHEMA_VERSION = "temporal_architecture_v2"

    architecture_id: str
    windows: tuple[TemporalWindowHypothesis, ...]
    declared_sequence: tuple[TemporalWindow, ...]
    transition_specs: tuple[TemporalTransitionSpec, ...]
    within_sniff_requested: bool
    within_sniff_scope: TemporalHypothesisScope | None
    within_sniff_observations: tuple[WithinSniffObservation, ...]
    observation_interpolation_used: bool = field(default=False, init=False)
    predicted_perception_substitution_used: bool = field(default=False, init=False)
    formula_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "architecture_id",
            _normalized_identifier(self.architecture_id, "architecture_id"),
        )
        by_window: dict[TemporalWindow, TemporalWindowHypothesis] = {}
        by_id: dict[str, TemporalWindowHypothesis] = {}
        for window_hypothesis in self.windows:
            if not isinstance(window_hypothesis, TemporalWindowHypothesis):
                raise TypeError("windows must contain TemporalWindowHypothesis values")
            window = window_hypothesis.scope.temporal_window
            if window in by_window:
                raise ValueError(f"duplicate temporal window {window.value!r}")
            previous = by_id.get(window_hypothesis.hypothesis_id)
            if previous is not None and previous != window_hypothesis:
                raise ValueError(f"hypothesis_id {window_hypothesis.hypothesis_id!r} conflicts")
            by_window[window] = window_hypothesis
            by_id[window_hypothesis.hypothesis_id] = window_hypothesis
        if set(by_window) != set(CANONICAL_TEMPORAL_SEQUENCE):
            raise ValueError("windows must contain all seven temporal windows exactly once")
        object.__setattr__(
            self,
            "windows",
            tuple(by_window[window] for window in CANONICAL_TEMPORAL_SEQUENCE),
        )

        sequence = tuple(TemporalWindow(item) for item in self.declared_sequence)
        if (
            len(sequence) != len(CANONICAL_TEMPORAL_SEQUENCE)
            or len(set(sequence)) != len(sequence)
            or set(sequence) != set(CANONICAL_TEMPORAL_SEQUENCE)
        ):
            raise ValueError(
                "declared_sequence must contain all seven temporal windows exactly once"
            )
        object.__setattr__(self, "declared_sequence", sequence)

        base_scopes = {item.scope.base_key for item in self.windows}
        if len(base_scopes) != 1:
            raise ValueError(
                "temporal target, subject, concentration, matrix, or condition "
                "scope mismatch; emit separate PlaneAssessment packets"
            )

        specs = tuple(self.transition_specs)
        if len(specs) != len(sequence) - 1 or any(
            not isinstance(item, TemporalTransitionSpec) for item in specs
        ):
            raise ValueError("transition_specs must contain one spec per sequence edge")
        spec_ids = tuple(item.transition_spec_id for item in specs)
        if len(spec_ids) != len(set(spec_ids)):
            raise ValueError("transition_spec_id values must be unique")
        object.__setattr__(self, "transition_specs", specs)

        if not isinstance(self.within_sniff_requested, bool):
            raise TypeError("within_sniff_requested must be bool")
        if self.within_sniff_scope is not None and not isinstance(
            self.within_sniff_scope,
            TemporalHypothesisScope,
        ):
            raise TypeError("within_sniff_scope must be a TemporalHypothesisScope or None")
        if self.within_sniff_requested and self.within_sniff_scope is None:
            raise ValueError("within_sniff_requested requires an exact within_sniff_scope")
        if not self.within_sniff_requested and self.within_sniff_scope is not None:
            raise ValueError("within_sniff_scope requires within_sniff_requested to be true")
        object.__setattr__(
            self,
            "within_sniff_observations",
            _canonical_sniff_observations(tuple(self.within_sniff_observations)),
        )
        expected_base_scope = self.windows[0].scope.base_key
        if (
            self.within_sniff_scope is not None
            and self.within_sniff_scope.base_key != expected_base_scope
        ):
            raise ValueError("within_sniff_scope must match the architecture base scope")
        if self.within_sniff_observations and self.within_sniff_scope is None:
            raise ValueError("within_sniff_observations require an exact within_sniff_scope")
        if any(item.scope != self.within_sniff_scope for item in self.within_sniff_observations):
            raise ValueError("within_sniff_observations must match the exact within_sniff_scope")
        prediction_ids = tuple(
            item.predicted_physical.prediction_id
            for item in self.windows
            if item.predicted_physical is not None
        )
        if len(prediction_ids) != len(set(prediction_ids)):
            raise ValueError("prediction_id values must be unique across windows")
        observation_ids = tuple(
            item.observation_id
            for window_hypothesis in self.windows
            for item in window_hypothesis.observed_perceptions
        )
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("observation_id values must be unique across windows")

    @property
    def window_map(self) -> dict[TemporalWindow, TemporalWindowHypothesis]:
        return {item.scope.temporal_window: item for item in self.windows}

    @property
    def transitions(self) -> tuple[TemporalTransitionHypothesis, ...]:
        windows = self.window_map
        result: list[TemporalTransitionHypothesis] = []
        for index, (left, right, spec) in enumerate(
            zip(
                self.declared_sequence,
                self.declared_sequence[1:],
                self.transition_specs,
            )
        ):
            payload = {
                "architecture_id": self.architecture_id,
                "index": index,
                "from_window": left.value,
                "to_window": right.value,
                "spec": spec.as_dict(),
            }
            result.append(
                TemporalTransitionHypothesis(
                    transition_id=_stable_id("temporal-transition", payload),
                    from_window=left,
                    to_window=right,
                    kind=spec.kind,
                    from_subject=windows[left].subject_hypothesis,
                    to_subject=windows[right].subject_hypothesis,
                    bridge_or_handoff=spec.bridge_or_handoff,
                    support=spec.support,
                    provenance_refs=spec.provenance_refs,
                    uncertainty=spec.uncertainty,
                    counterfactual=spec.counterfactual,
                    failure_mode=spec.failure_mode,
                    minimum_resolving_experiment=spec.minimum_resolving_experiment,
                )
            )
        return tuple(result)

    @property
    def assessment_scope(self) -> AssessmentScope:
        first = self.windows[0].scope
        temporal = "sequence[" + ">".join(item.value for item in self.declared_sequence) + "]"
        return AssessmentScope(
            target_scope=first.target_scope,
            temporal_scope=temporal,
            matrix_scope=first.plane_matrix_scope,
        )

    def reversed(self) -> TemporalArchitecture:
        """Reverse the semantic sequence while preserving raw evidence records."""

        return TemporalArchitecture(
            architecture_id=self.architecture_id,
            windows=self.windows,
            declared_sequence=tuple(reversed(self.declared_sequence)),
            transition_specs=tuple(reversed(self.transition_specs)),
            within_sniff_requested=self.within_sniff_requested,
            within_sniff_scope=self.within_sniff_scope,
            within_sniff_observations=self.within_sniff_observations,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalArchitecture:
        data = _payload(payload, cls.SCHEMA_VERSION)
        flags = (
            "observation_interpolation_used",
            "predicted_perception_substitution_used",
            "formula_authority",
            "sensory_authority",
            "release_authority",
        )
        if any(data.get(flag) is not False for flag in flags):
            raise ValueError("temporal architecture authority flags must remain false")
        return cls(
            architecture_id=data["architecture_id"],
            windows=tuple(TemporalWindowHypothesis.from_dict(item) for item in data["windows"]),
            declared_sequence=tuple(TemporalWindow(item) for item in data["declared_sequence"]),
            transition_specs=tuple(
                TemporalTransitionSpec.from_dict(item) for item in data["transition_specs"]
            ),
            within_sniff_requested=data["within_sniff_requested"],
            within_sniff_scope=(
                TemporalHypothesisScope.from_dict(data["within_sniff_scope"])
                if data["within_sniff_scope"] is not None
                else None
            ),
            within_sniff_observations=tuple(
                WithinSniffObservation.from_dict(item) for item in data["within_sniff_observations"]
            ),
        )


def _bounded_authority(requested: AuthorityCeiling) -> AuthorityCeiling:
    return AuthorityCeiling.minimum((AuthorityCeiling(requested), AuthorityCeiling.DESIGN_ONLY))


def _prediction_observation_conflicts(
    architecture: TemporalArchitecture,
) -> tuple[PlaneConflict, ...]:
    conflicts: list[PlaneConflict] = []
    for window_hypothesis in architecture.windows:
        prediction = window_hypothesis.predicted_physical
        observations = window_hypothesis.observed_perceptions
        if prediction is None or not observations:
            continue
        window = window_hypothesis.scope.temporal_window
        alternatives = _unique_texts(
            (
                f"predicted physical: {prediction.description}",
                *(f"observed perception: {item.description}" for item in observations),
            )
        )
        if len(alternatives) < 2:
            continue
        payload = {
            "window": window.value,
            "prediction": prediction.content_sha256,
            "observations": [item.content_sha256 for item in observations],
        }
        conflicts.append(
            PlaneConflict(
                conflict_id=_stable_id("physical-observation-firewall", payload),
                claim_key=f"temporal.window.{window.value}.evidence_domain",
                alternatives=alternatives,
                reason=(
                    "predicted physical evolution and participant-linked observed "
                    "perception remain separate evidence domains"
                ),
                claim_ids=(
                    f"predicted:{prediction.prediction_id}",
                    *(f"observed:{item.observation_id}" for item in observations),
                ),
                provenance_refs=_merged_provenance(
                    (
                        *prediction.provenance_refs,
                        *(
                            ref
                            for observation in observations
                            for ref in observation.provenance_refs
                        ),
                    )
                ),
            )
        )
    return tuple(conflicts)


def _standard_transition_failures(
    transitions: tuple[TemporalTransitionHypothesis, ...],
) -> tuple[str, ...]:
    labels = {
        TemporalTransitionKind.DISCONTINUITY: "declared subject discontinuity",
        TemporalTransitionKind.TAKEOVER: "supporting-system takeover",
        TemporalTransitionKind.GENERIC_RESIDUE_FAILURE: "generic residue failure",
    }
    return tuple(labels[item.kind] for item in transitions if item.kind in labels)


def build_temporal_plane_assessment(
    architecture: TemporalArchitecture,
    *,
    assessment_id: str | None = None,
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.DESIGN_ONLY,
) -> PlaneAssessment:
    """Emit one TEMPORAL packet with all observations and unknowns preserved."""

    if not isinstance(architecture, TemporalArchitecture):
        raise TypeError("architecture must be a TemporalArchitecture")
    authority = _bounded_authority(authority_ceiling)
    claims: list[ScopedClaim] = []
    intervals: list[SupportInterval] = []
    unknowns: list[UnknownFact] = []
    provenance_values: list[ProvenanceRef] = []

    for window_hypothesis in architecture.windows:
        window = window_hypothesis.scope.temporal_window
        provenance_values.extend(window_hypothesis.all_provenance)
        subject_claim_id = f"subject:{window_hypothesis.hypothesis_id}"
        claims.append(
            ScopedClaim(
                claim_id=subject_claim_id,
                claim_key=f"temporal.window.{window.value}.subject",
                claim_value=window_hypothesis.subject_hypothesis,
                claim_kind=ClaimKind.HYPOTHESIS,
                authority_ceiling=authority,
                provenance_refs=window_hypothesis.provenance_refs,
            )
        )
        intervals.append(
            SupportInterval(
                interval_id=f"support:{subject_claim_id}",
                claim_id=subject_claim_id,
                lower=window_hypothesis.support.lower,
                upper=window_hypothesis.support.upper,
                provenance_refs=window_hypothesis.provenance_refs,
                support_measure=SupportMeasure.EVIDENCE_SUPPORT,
            )
        )
        prediction = window_hypothesis.predicted_physical
        if prediction is None:
            unknowns.append(
                UnknownFact(
                    unknown_id=f"unknown:predicted:{window.value}",
                    field_key=f"temporal.window.{window.value}.predicted_physical",
                    reason="no exact-scope physical prediction was supplied",
                    needed_evidence="provenance-bound exact-scope physical model output",
                    provenance_refs=window_hypothesis.provenance_refs,
                )
            )
        else:
            prediction_claim_id = f"predicted:{prediction.prediction_id}"
            claims.append(
                ScopedClaim(
                    claim_id=prediction_claim_id,
                    claim_key=f"temporal.window.{window.value}.predicted_physical",
                    claim_value=prediction.description,
                    claim_kind=ClaimKind.DIAGNOSTIC,
                    authority_ceiling=authority,
                    provenance_refs=prediction.provenance_refs,
                )
            )
            intervals.append(
                SupportInterval(
                    interval_id=f"support:{prediction_claim_id}",
                    claim_id=prediction_claim_id,
                    lower=prediction.support.lower,
                    upper=prediction.support.upper,
                    provenance_refs=prediction.provenance_refs,
                    support_measure=SupportMeasure.EVIDENCE_SUPPORT,
                )
            )
        if not window_hypothesis.observed_perceptions:
            unknowns.append(
                UnknownFact(
                    unknown_id=f"unknown:observed:{window.value}",
                    field_key=f"temporal.window.{window.value}.observed_perception",
                    reason="no participant-linked observation exists at this window",
                    needed_evidence=window_hypothesis.minimum_resolving_experiment,
                    provenance_refs=window_hypothesis.provenance_refs,
                )
            )
        for observation in window_hypothesis.observed_perceptions:
            claims.append(
                ScopedClaim(
                    claim_id=f"observed:{observation.observation_id}",
                    claim_key=(
                        f"temporal.window.{window.value}.observed_perception."
                        f"{observation.participant_id}.{observation.repeat_id}."
                        f"{observation.endpoint_id}"
                    ),
                    claim_value=observation.description,
                    claim_kind=ClaimKind.OBSERVATION,
                    authority_ceiling=authority,
                    provenance_refs=observation.provenance_refs,
                )
            )

    transitions = architecture.transitions
    for index, transition in enumerate(transitions):
        provenance_values.extend(transition.provenance_refs)
        claim_id = f"transition:{transition.transition_id}"
        claims.append(
            ScopedClaim(
                claim_id=claim_id,
                claim_key=f"temporal.transition.{index:02d}",
                claim_value=transition.claim_value,
                claim_kind=ClaimKind.HYPOTHESIS,
                authority_ceiling=authority,
                provenance_refs=transition.provenance_refs,
            )
        )
        intervals.append(
            SupportInterval(
                interval_id=f"support:{claim_id}",
                claim_id=claim_id,
                lower=transition.support.lower,
                upper=transition.support.upper,
                provenance_refs=transition.provenance_refs,
                support_measure=SupportMeasure.EVIDENCE_SUPPORT,
            )
        )
        unknowns.append(
            UnknownFact(
                unknown_id=f"uncertainty:{transition.transition_id}",
                field_key=f"temporal.transition.{index:02d}.resolution",
                reason=transition.uncertainty,
                needed_evidence=transition.minimum_resolving_experiment,
                provenance_refs=transition.provenance_refs,
            )
        )

    sniff_by_phase = {
        observation.phase: observation for observation in architecture.within_sniff_observations
    }
    for sniff_observation in architecture.within_sniff_observations:
        provenance_values.extend(sniff_observation.provenance_refs)
        claims.append(
            ScopedClaim(
                claim_id=f"within-sniff:{sniff_observation.observation_id}",
                claim_key=(
                    f"temporal.within_sniff."
                    f"{sniff_observation.scope.temporal_window.value}."
                    f"{sniff_observation.phase.value}."
                    f"{sniff_observation.participant_id}."
                    f"{sniff_observation.repeat_id}."
                    f"{sniff_observation.endpoint_id}"
                ),
                claim_value=sniff_observation.description,
                claim_kind=ClaimKind.OBSERVATION,
                authority_ceiling=authority,
                provenance_refs=sniff_observation.provenance_refs,
            )
        )
    if architecture.within_sniff_requested:
        sniff_scope = architecture.within_sniff_scope
        if sniff_scope is None:  # Constructor validation makes this unreachable.
            raise RuntimeError("validated within-sniff scope is missing")
        fallback_provenance = _merged_provenance(provenance_values)
        for phase in WithinSniffPhase:
            if phase not in sniff_by_phase:
                unknowns.append(
                    UnknownFact(
                        unknown_id=f"unknown:within-sniff:{phase.value}",
                        field_key=(
                            f"temporal.within_sniff."
                            f"{sniff_scope.temporal_window.value}."
                            f"{phase.value}.observation"
                        ),
                        reason=(
                            f"no participant-linked within-sniff {phase.value} observation exists"
                        ),
                        needed_evidence=("qualified, participant-linked within-sniff observation"),
                        provenance_refs=fallback_provenance,
                    )
                )

    provenance = _merged_provenance(provenance_values)
    criteria = (
        ParetoCriterion(
            criterion_id="temporal_subject_continuity",
            direction=CriterionDirection.MAXIMIZE,
            value=CriterionValue.unknown(
                "continuity requires participant-linked adjudication across declared windows"
            ),
            unit="participant-linked temporal criterion",
            authority_ceiling=authority,
            provenance_refs=provenance,
        ),
        ParetoCriterion(
            criterion_id="temporal_generic_residue",
            direction=CriterionDirection.MINIMIZE,
            value=CriterionValue.unknown(
                "generic residue requires participant-linked drydown adjudication"
            ),
            unit="participant-linked residue criterion",
            authority_ceiling=authority,
            provenance_refs=provenance,
        ),
    )
    failures = _unique_texts(
        (
            *(item.failure_mode for item in architecture.windows),
            *(item.failure_mode for item in transitions),
            *_standard_transition_failures(transitions),
        )
    )
    experiments = _unique_texts(
        (
            *(item.minimum_resolving_experiment for item in architecture.windows),
            *(item.minimum_resolving_experiment for item in transitions),
        )
    )
    resolved_assessment_id = assessment_id or _stable_id(
        "temporal-assessment",
        {"architecture_sha256": architecture.content_sha256},
    )
    freshness = (
        *(item.content_sha256 for item in architecture.windows),
        *(item.content_sha256 for item in architecture.transition_specs),
        *(item.content_sha256 for item in architecture.within_sniff_observations),
    )
    return PlaneAssessment(
        assessment_id=resolved_assessment_id,
        module_id=_MODULE_ID,
        plane_id=PlaneId.TEMPORAL,
        scope=architecture.assessment_scope,
        claims=tuple(claims),
        support_intervals=tuple(intervals),
        conflicts=_prediction_observation_conflicts(architecture),
        unknowns=tuple(unknowns),
        failure_modes=failures,
        proposed_experiments=experiments,
        provenance_refs=provenance,
        authority_ceiling=authority,
        freshness_hashes=freshness,
        native_criteria=criteria,
    )


__all__ = [
    "CANONICAL_TEMPORAL_SEQUENCE",
    "ParticipantLinkedObservation",
    "PredictedPhysicalEvolution",
    "TemporalArchitecture",
    "TemporalHypothesisScope",
    "TemporalTransitionHypothesis",
    "TemporalTransitionKind",
    "TemporalTransitionSpec",
    "TemporalWindow",
    "TemporalWindowHypothesis",
    "WithinSniffObservation",
    "WithinSniffPhase",
    "build_temporal_plane_assessment",
]
