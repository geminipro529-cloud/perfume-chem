"""Immutable structural contracts for spatial-composition hypotheses.

This leaf module keeps aesthetic spatial design, predicted physical transport,
and participant-linked observation in separate evidence domains.  A transport
prediction never becomes observed space, sillage, projection, longevity, or
performance.  Records here do not select formulas or materials and carry no
scalar beauty, sensory, safety, physical-execution, or release authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping

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
    UnknownFact,
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _payload,
)

_MODULE_ID = "formulation_intelligence.spatial_architecture"
_SPATIAL_CEILING = AuthorityCeiling.DESIGN_ONLY


def _stable_id(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _false_authority_payload(data: Mapping[str, Any], names: Iterable[str]) -> None:
    if any(data.get(name) is not False for name in names):
        raise ValueError("spatial authority flags must all remain false")


def _condition_bound(
    provenance_refs: tuple[ProvenanceRef, ...],
    condition_id: str,
) -> tuple[ProvenanceRef, ...]:
    provenance = _merged_provenance(provenance_refs)
    if not provenance:
        raise ValueError("condition-bound provenance must not be empty")
    if any(item.independence_key != condition_id for item in provenance):
        raise ValueError("every provenance independence_key must equal the declared condition_id")
    return provenance


def _canonical_by_id(
    values: Iterable[Any],
    *,
    record_type: type[Any],
    id_attribute: str,
    field_name: str,
) -> tuple[Any, ...]:
    by_id: dict[str, Any] = {}
    by_hash: dict[str, Any] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} values")
        identifier = getattr(value, id_attribute)
        previous = by_id.get(identifier)
        if previous is not None and previous != value:
            raise ValueError(f"{field_name} has conflicting ID {identifier!r}")
        by_id[identifier] = value
        by_hash[value.content_sha256] = value
    return tuple(by_hash[digest] for digest in sorted(by_hash))


def _unique_texts(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda item: (item.casefold(), item)))


class SpatialDimension(str, Enum):
    """Independent target-linked axes; density and air are deliberately distinct."""

    FOCUS = "focus"
    WIDTH = "width"
    DENSITY = "density"
    APERTURE = "aperture"
    EDGE = "edge"
    DISTANCE = "distance"
    TEXTURE = "texture"
    CONTRAST = "contrast"
    SHADOW = "shadow"
    NEGATIVE_SPACE_AIR = "negative_space_air"
    PROJECTION_FIELD = "projection_field"
    RESIDUE_IDENTITY = "residue_identity"


class SpatialRelationKind(str, Enum):
    SPATIAL = "spatial"
    TRANSITION = "transition"
    CONTRAST = "contrast"
    HANDOFF = "handoff"
    SEPARATION = "separation"


@dataclass(frozen=True, slots=True)
class SpatialScope(_CanonicalRecord):
    """Exact target, subject, material, condition, and protocol packet scope."""

    SCHEMA_VERSION = "spatial_scope_v2"

    target_scope: str
    subject_id: str
    material_identity_id: str
    condition_id: str
    temporal_scope: str
    matrix_scope: str
    context_scope: str
    protocol_scope: str

    def __post_init__(self) -> None:
        for field_name in (
            "target_scope",
            "subject_id",
            "material_identity_id",
            "condition_id",
            "temporal_scope",
            "matrix_scope",
            "context_scope",
            "protocol_scope",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )

    @property
    def key(self) -> tuple[str, str, str, str, str, str, str, str]:
        return (
            self.target_scope,
            self.subject_id,
            self.material_identity_id,
            self.condition_id,
            self.temporal_scope,
            self.matrix_scope,
            self.context_scope,
            self.protocol_scope,
        )

    @property
    def assessment_scope(self) -> AssessmentScope:
        subject = self.subject_id
        material = self.material_identity_id
        condition = self.condition_id
        matrix = self.matrix_scope
        context = self.context_scope
        protocol = self.protocol_scope
        return AssessmentScope(
            target_scope=self.target_scope,
            temporal_scope=self.temporal_scope,
            matrix_scope=(
                f"matrix[{len(matrix)}]={matrix};"
                f"subject[{len(subject)}]={subject};"
                f"material[{len(material)}]={material};"
                f"condition[{len(condition)}]={condition};"
                f"context[{len(context)}]={context};"
                f"protocol[{len(protocol)}]={protocol}"
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SpatialScope:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            target_scope=data["target_scope"],
            subject_id=data["subject_id"],
            material_identity_id=data["material_identity_id"],
            condition_id=data["condition_id"],
            temporal_scope=data["temporal_scope"],
            matrix_scope=data["matrix_scope"],
            context_scope=data["context_scope"],
            protocol_scope=data["protocol_scope"],
        )


@dataclass(frozen=True, slots=True)
class SpatialDimensionHypothesis(_CanonicalRecord):
    """One qualitative design hypothesis for one and only one spatial axis."""

    SCHEMA_VERSION = "spatial_dimension_hypothesis_v2"

    hypothesis_id: str
    dimension: SpatialDimension
    scope: SpatialScope
    condition_id: str
    target_state: str
    support: SupportInterval
    uncertainty: str
    counterfactual: str
    failure_mode: str
    minimum_resolving_experiment: str
    formula_selection_authority: bool = field(default=False, init=False)
    material_selection_authority: bool = field(default=False, init=False)
    scalar_beauty_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hypothesis_id",
            _normalized_identifier(self.hypothesis_id, "hypothesis_id"),
        )
        object.__setattr__(self, "dimension", SpatialDimension(self.dimension))
        if not isinstance(self.scope, SpatialScope):
            raise TypeError("scope must be a SpatialScope")
        condition = _normalized_identifier(self.condition_id, "condition_id")
        object.__setattr__(self, "condition_id", condition)
        if condition != self.scope.condition_id:
            raise ValueError("condition_id must match the exact SpatialScope condition")
        object.__setattr__(
            self, "target_state", _normalized_text(self.target_state, "target_state")
        )
        if not isinstance(self.support, SupportInterval):
            raise TypeError("support must be a SupportInterval")
        _condition_bound(self.support.provenance_refs, condition)
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
    def provenance_refs(self) -> tuple[ProvenanceRef, ...]:
        return self.support.provenance_refs

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SpatialDimensionHypothesis:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(
            data,
            (
                "formula_selection_authority",
                "material_selection_authority",
                "scalar_beauty_authority",
                "sensory_authority",
                "release_authority",
            ),
        )
        return cls(
            hypothesis_id=data["hypothesis_id"],
            dimension=SpatialDimension(data["dimension"]),
            scope=SpatialScope.from_dict(data["scope"]),
            condition_id=data["condition_id"],
            target_state=data["target_state"],
            support=SupportInterval.from_dict(data["support"]),
            uncertainty=data["uncertainty"],
            counterfactual=data["counterfactual"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


@dataclass(frozen=True, slots=True)
class PredictedSpatialTransport(_CanonicalRecord):
    """A physical transport hypothesis with no participant-perception promotion."""

    SCHEMA_VERSION = "predicted_spatial_transport_v2"

    prediction_id: str
    dimension: SpatialDimension
    scope: SpatialScope
    condition_id: str
    prediction: str
    support: SupportInterval
    uncertainty: str
    failure_mode: str
    minimum_resolving_experiment: str
    observed_space_authority: bool = field(default=False, init=False)
    sillage_authority: bool = field(default=False, init=False)
    projection_authority: bool = field(default=False, init=False)
    longevity_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "prediction_id",
            _normalized_identifier(self.prediction_id, "prediction_id"),
        )
        object.__setattr__(self, "dimension", SpatialDimension(self.dimension))
        if not isinstance(self.scope, SpatialScope):
            raise TypeError("scope must be a SpatialScope")
        condition = _normalized_identifier(self.condition_id, "condition_id")
        object.__setattr__(self, "condition_id", condition)
        if condition != self.scope.condition_id:
            raise ValueError("condition_id must match the exact SpatialScope condition")
        object.__setattr__(self, "prediction", _normalized_text(self.prediction, "prediction"))
        if not isinstance(self.support, SupportInterval):
            raise TypeError("support must be a SupportInterval")
        _condition_bound(self.support.provenance_refs, condition)
        for field_name in (
            "uncertainty",
            "failure_mode",
            "minimum_resolving_experiment",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @property
    def provenance_refs(self) -> tuple[ProvenanceRef, ...]:
        return self.support.provenance_refs

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PredictedSpatialTransport:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(
            data,
            (
                "observed_space_authority",
                "sillage_authority",
                "projection_authority",
                "longevity_authority",
                "performance_authority",
                "sensory_authority",
            ),
        )
        return cls(
            prediction_id=data["prediction_id"],
            dimension=SpatialDimension(data["dimension"]),
            scope=SpatialScope.from_dict(data["scope"]),
            condition_id=data["condition_id"],
            prediction=data["prediction"],
            support=SupportInterval.from_dict(data["support"]),
            uncertainty=data["uncertainty"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


@dataclass(frozen=True, slots=True)
class ParticipantSpatialObservation(_CanonicalRecord):
    """One observed endpoint bound to participant, repeat, task, and condition."""

    SCHEMA_VERSION = "participant_spatial_observation_v2"

    observation_id: str
    participant_id: str
    repeat_id: str
    endpoint_id: str
    dimension: SpatialDimension
    scope: SpatialScope
    condition_id: str
    observed_state: str
    provenance_refs: tuple[ProvenanceRef, ...]
    interpolated: bool = field(default=False, init=False)
    physical_transport_authority: bool = field(default=False, init=False)
    general_population_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "observation_id",
            "participant_id",
            "repeat_id",
            "endpoint_id",
            "condition_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "dimension", SpatialDimension(self.dimension))
        if not isinstance(self.scope, SpatialScope):
            raise TypeError("scope must be a SpatialScope")
        if self.condition_id != self.scope.condition_id:
            raise ValueError("condition_id must match the exact SpatialScope condition")
        object.__setattr__(
            self,
            "observed_state",
            _normalized_text(self.observed_state, "observed_state"),
        )
        provenance = _condition_bound(self.provenance_refs, self.condition_id)
        allowed = {EvidenceClass.DIRECT_OBSERVATION, EvidenceClass.USER_REPORT}
        if any(item.evidence_class not in allowed for item in provenance):
            raise ValueError(
                "participant spatial observations require direct/user observation provenance"
            )
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ParticipantSpatialObservation:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(
            data,
            (
                "interpolated",
                "physical_transport_authority",
                "general_population_authority",
                "liking_authority",
            ),
        )
        return cls(
            observation_id=data["observation_id"],
            participant_id=data["participant_id"],
            repeat_id=data["repeat_id"],
            endpoint_id=data["endpoint_id"],
            dimension=SpatialDimension(data["dimension"]),
            scope=SpatialScope.from_dict(data["scope"]),
            condition_id=data["condition_id"],
            observed_state=data["observed_state"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class SpatialRelationHypothesis(_CanonicalRecord):
    """A falsifiable spatial relation or transition without formula selection."""

    SCHEMA_VERSION = "spatial_relation_hypothesis_v2"

    relation_id: str
    source_dimension: SpatialDimension
    target_dimension: SpatialDimension
    scope: SpatialScope
    relation_kind: SpatialRelationKind
    condition_id: str
    hypothesis: str
    support: SupportInterval
    uncertainty: str
    counterfactual: str
    failure_mode: str
    minimum_resolving_experiment: str
    causal_authority: bool = field(default=False, init=False)
    formula_selection_authority: bool = field(default=False, init=False)
    material_selection_authority: bool = field(default=False, init=False)
    scalar_beauty_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relation_id",
            _normalized_identifier(self.relation_id, "relation_id"),
        )
        object.__setattr__(self, "source_dimension", SpatialDimension(self.source_dimension))
        object.__setattr__(self, "target_dimension", SpatialDimension(self.target_dimension))
        if not isinstance(self.scope, SpatialScope):
            raise TypeError("scope must be a SpatialScope")
        object.__setattr__(self, "relation_kind", SpatialRelationKind(self.relation_kind))
        condition = _normalized_identifier(self.condition_id, "condition_id")
        object.__setattr__(self, "condition_id", condition)
        if condition != self.scope.condition_id:
            raise ValueError("condition_id must match the exact SpatialScope condition")
        object.__setattr__(self, "hypothesis", _normalized_text(self.hypothesis, "hypothesis"))
        if not isinstance(self.support, SupportInterval):
            raise TypeError("support must be a SupportInterval")
        _condition_bound(self.support.provenance_refs, condition)
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
    def provenance_refs(self) -> tuple[ProvenanceRef, ...]:
        return self.support.provenance_refs

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SpatialRelationHypothesis:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(
            data,
            (
                "causal_authority",
                "formula_selection_authority",
                "material_selection_authority",
                "scalar_beauty_authority",
            ),
        )
        return cls(
            relation_id=data["relation_id"],
            source_dimension=SpatialDimension(data["source_dimension"]),
            target_dimension=SpatialDimension(data["target_dimension"]),
            scope=SpatialScope.from_dict(data["scope"]),
            relation_kind=SpatialRelationKind(data["relation_kind"]),
            condition_id=data["condition_id"],
            hypothesis=data["hypothesis"],
            support=SupportInterval.from_dict(data["support"]),
            uncertainty=data["uncertainty"],
            counterfactual=data["counterfactual"],
            failure_mode=data["failure_mode"],
            minimum_resolving_experiment=data["minimum_resolving_experiment"],
        )


@dataclass(frozen=True, slots=True)
class SpatialArchitecture(_CanonicalRecord):
    """Complete exact-scope spatial hypothesis library for one target condition."""

    SCHEMA_VERSION = "spatial_architecture_v2"

    architecture_id: str
    scope: SpatialScope
    dimension_hypotheses: tuple[SpatialDimensionHypothesis, ...]
    predicted_transport: tuple[PredictedSpatialTransport, ...] = ()
    participant_observations: tuple[ParticipantSpatialObservation, ...] = ()
    relations: tuple[SpatialRelationHypothesis, ...] = ()
    physical_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    formula_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "architecture_id",
            _normalized_identifier(self.architecture_id, "architecture_id"),
        )
        if not isinstance(self.scope, SpatialScope):
            raise TypeError("scope must be a SpatialScope")
        dimensions = _canonical_by_id(
            self.dimension_hypotheses,
            record_type=SpatialDimensionHypothesis,
            id_attribute="hypothesis_id",
            field_name="dimension_hypotheses",
        )
        by_dimension = {item.dimension: item for item in dimensions}
        if len(dimensions) != len(SpatialDimension) or set(by_dimension) != set(SpatialDimension):
            raise ValueError(
                "spatial architecture requires exactly one hypothesis for every dimension"
            )
        ordered_dimensions = tuple(by_dimension[item] for item in SpatialDimension)
        object.__setattr__(self, "dimension_hypotheses", ordered_dimensions)
        predictions = _canonical_by_id(
            self.predicted_transport,
            record_type=PredictedSpatialTransport,
            id_attribute="prediction_id",
            field_name="predicted_transport",
        )
        observations = _canonical_by_id(
            self.participant_observations,
            record_type=ParticipantSpatialObservation,
            id_attribute="observation_id",
            field_name="participant_observations",
        )
        relations = _canonical_by_id(
            self.relations,
            record_type=SpatialRelationHypothesis,
            id_attribute="relation_id",
            field_name="relations",
        )
        if (
            any(item.scope.key != self.scope.key for item in dimensions)
            or any(item.scope.key != self.scope.key for item in predictions)
            or any(item.scope.key != self.scope.key for item in observations)
            or any(item.scope.key != self.scope.key for item in relations)
        ):
            raise ValueError("spatial record scope mismatch; emit separate PlaneAssessment packets")
        object.__setattr__(self, "predicted_transport", predictions)
        object.__setattr__(self, "participant_observations", observations)
        object.__setattr__(self, "relations", relations)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SpatialArchitecture:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(
            data,
            (
                "physical_authority",
                "sensory_authority",
                "hedonic_authority",
                "formula_authority",
                "safety_authority",
                "release_authority",
            ),
        )
        return cls(
            architecture_id=data["architecture_id"],
            scope=SpatialScope.from_dict(data["scope"]),
            dimension_hypotheses=tuple(
                SpatialDimensionHypothesis.from_dict(item) for item in data["dimension_hypotheses"]
            ),
            predicted_transport=tuple(
                PredictedSpatialTransport.from_dict(item)
                for item in data.get("predicted_transport", ())
            ),
            participant_observations=tuple(
                ParticipantSpatialObservation.from_dict(item)
                for item in data.get("participant_observations", ())
            ),
            relations=tuple(
                SpatialRelationHypothesis.from_dict(item) for item in data.get("relations", ())
            ),
        )


def _spatial_conflicts(
    observations: tuple[ParticipantSpatialObservation, ...],
) -> tuple[PlaneConflict, ...]:
    grouped: dict[
        tuple[SpatialDimension, str, str, str, str],
        list[ParticipantSpatialObservation],
    ] = {}
    for observation in observations:
        exact_subject_key = (
            observation.dimension,
            observation.participant_id,
            observation.repeat_id,
            observation.endpoint_id,
            observation.condition_id,
        )
        grouped.setdefault(exact_subject_key, []).append(observation)
    conflicts: list[PlaneConflict] = []
    for exact_subject_key, records in sorted(
        grouped.items(), key=lambda item: tuple(str(value) for value in item[0])
    ):
        dimension, participant, repeat, endpoint, condition = exact_subject_key
        alternatives = _unique_texts(item.observed_state for item in records)
        if len(alternatives) < 2:
            continue
        conflicts.append(
            PlaneConflict(
                conflict_id=_stable_id(
                    "spatial-observation-conflict",
                    {
                        "dimension": dimension.value,
                        "participant": participant,
                        "repeat": repeat,
                        "endpoint": endpoint,
                        "condition": condition,
                        "records": [item.content_sha256 for item in records],
                    },
                ),
                claim_key=(
                    f"spatial.observed_participant.{dimension.value}."
                    f"{participant}.{repeat}.{endpoint}.{condition}"
                ),
                alternatives=alternatives,
                reason=(
                    "the same participant/repeat/endpoint/condition record conflicts; "
                    "different participants remain heterogeneous observations instead"
                ),
                claim_ids=tuple(item.observation_id for item in records),
                provenance_refs=_merged_provenance(
                    ref for item in records for ref in item.provenance_refs
                ),
            )
        )
    return tuple(conflicts)


def _spatial_downstream_holds(
    provenance_refs: tuple[ProvenanceRef, ...],
) -> tuple[UnknownFact, ...]:
    """Keep structural spatial evidence below aesthetic and release authority."""

    return (
        UnknownFact(
            unknown_id="spatial-downstream-scalar-aesthetic-hold",
            field_key="spatial.downstream.scalar_aesthetic_authority",
            reason=(
                "HOLD: qualitative spatial relations and support intervals do not "
                "establish beauty, liking, richness, or a scalar aesthetic score"
            ),
            needed_evidence=(
                "Collect criterion-specific, participant-linked blinded observations; "
                "retain heterogeneous outcomes rather than averaging to beauty."
            ),
            provenance_refs=provenance_refs,
        ),
        UnknownFact(
            unknown_id="spatial-downstream-observed-performance-hold",
            field_key="spatial.downstream.observed_performance_authority",
            reason=(
                "HOLD: modeled transport and designed projection fields are not "
                "observed sillage, projection, longevity, or physical performance"
            ),
            needed_evidence=(
                "Pair condition-matched physical measurements with blinded, "
                "participant-linked spatial observations over explicit time windows."
            ),
            provenance_refs=provenance_refs,
        ),
        UnknownFact(
            unknown_id="spatial-downstream-safety-release-hold",
            field_key="spatial.downstream.safety_release_authority",
            reason=(
                "HOLD: spatial architecture has no safety, stability, compounding, "
                "or release authority"
            ),
            needed_evidence=(
                "Use the independent exact-build safety, stability, execution, and "
                "release-governance contracts."
            ),
            provenance_refs=provenance_refs,
        ),
    )


def build_spatial_plane_assessment(
    architecture: SpatialArchitecture,
    *,
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.DESIGN_ONLY,
) -> PlaneAssessment:
    """Emit one exact-scope SPATIAL packet without sensory promotion."""

    if not isinstance(architecture, SpatialArchitecture):
        raise TypeError("architecture must be a SpatialArchitecture")
    authority = AuthorityCeiling.minimum((AuthorityCeiling(authority_ceiling), _SPATIAL_CEILING))
    dimension_claims = tuple(
        ScopedClaim(
            claim_id=item.support.claim_id,
            claim_key=f"spatial.dimension.{item.dimension.value}",
            claim_value=item.target_state,
            claim_kind=ClaimKind.HYPOTHESIS,
            authority_ceiling=authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.dimension_hypotheses
    )
    prediction_authority = AuthorityCeiling.minimum((authority, AuthorityCeiling.HYPOTHESIS_ONLY))
    predicted_claims = tuple(
        ScopedClaim(
            claim_id=item.support.claim_id,
            claim_key=(
                f"spatial.predicted_physical_transport.{item.dimension.value}.{item.prediction_id}"
            ),
            claim_value=item.prediction,
            claim_kind=ClaimKind.DIAGNOSTIC,
            authority_ceiling=prediction_authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.predicted_transport
    )
    observed_claims = tuple(
        ScopedClaim(
            claim_id=item.observation_id,
            claim_key=(
                f"spatial.observed_participant.{item.dimension.value}."
                f"{item.participant_id}.{item.repeat_id}."
                f"{item.endpoint_id}.{item.condition_id}"
            ),
            claim_value=item.observed_state,
            claim_kind=ClaimKind.OBSERVATION,
            authority_ceiling=authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.participant_observations
    )
    relation_claims = tuple(
        ScopedClaim(
            claim_id=item.support.claim_id,
            claim_key=(
                f"spatial.relation.{item.source_dimension.value}."
                f"{item.target_dimension.value}.{item.relation_id}"
            ),
            claim_value=f"{item.relation_kind.value}: {item.hypothesis}",
            claim_kind=ClaimKind.HYPOTHESIS,
            authority_ceiling=prediction_authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.relations
    )
    intervals = (
        *(item.support for item in architecture.dimension_hypotheses),
        *(item.support for item in architecture.predicted_transport),
        *(item.support for item in architecture.relations),
    )
    observed_dimensions = {item.dimension for item in architecture.participant_observations}
    by_dimension = {item.dimension: item for item in architecture.dimension_hypotheses}
    observation_unknowns = tuple(
        UnknownFact(
            unknown_id=f"missing-observation:{dimension.value}",
            field_key=f"spatial.{dimension.value}.observed_perception",
            reason=(
                "no exact-scope participant-linked observation is present; "
                "missing is UNKNOWN, not zero"
            ),
            needed_evidence=by_dimension[dimension].minimum_resolving_experiment,
            provenance_refs=by_dimension[dimension].provenance_refs,
        )
        for dimension in SpatialDimension
        if dimension not in observed_dimensions
    )
    criteria = tuple(
        ParetoCriterion(
            criterion_id=f"spatial_{item.dimension.value}",
            direction=CriterionDirection.PRESERVE,
            value=CriterionValue.unknown(
                "qualitative target dimension has no authorized scalar measurement"
            ),
            unit="target-linked qualitative spatial dimension",
            authority_ceiling=authority,
            provenance_refs=item.provenance_refs,
        )
        for item in architecture.dimension_hypotheses
    )
    provenance = _merged_provenance(
        (
            *(ref for item in architecture.dimension_hypotheses for ref in item.provenance_refs),
            *(ref for item in architecture.predicted_transport for ref in item.provenance_refs),
            *(
                ref
                for item in architecture.participant_observations
                for ref in item.provenance_refs
            ),
            *(ref for item in architecture.relations for ref in item.provenance_refs),
        )
    )
    unknowns = (
        *observation_unknowns,
        *_spatial_downstream_holds(provenance),
    )
    return PlaneAssessment(
        assessment_id=architecture.architecture_id,
        module_id=_MODULE_ID,
        plane_id=PlaneId.SPATIAL_COMPOSITION,
        scope=architecture.scope.assessment_scope,
        claims=(
            *dimension_claims,
            *predicted_claims,
            *observed_claims,
            *relation_claims,
        ),
        support_intervals=intervals,
        conflicts=_spatial_conflicts(architecture.participant_observations),
        unknowns=unknowns,
        failure_modes=_unique_texts(
            (
                *(item.failure_mode for item in architecture.dimension_hypotheses),
                *(item.failure_mode for item in architecture.predicted_transport),
                *(item.failure_mode for item in architecture.relations),
            )
        ),
        proposed_experiments=_unique_texts(
            (
                *(item.minimum_resolving_experiment for item in architecture.dimension_hypotheses),
                *(item.minimum_resolving_experiment for item in architecture.predicted_transport),
                *(item.minimum_resolving_experiment for item in architecture.relations),
            )
        ),
        provenance_refs=provenance,
        authority_ceiling=authority,
        freshness_hashes=(architecture.content_sha256,),
        native_criteria=criteria,
    )


@dataclass(frozen=True, slots=True)
class SpatialPlaneAdapter:
    """Structural adapter for consumers that accept ``to_plane_assessment``."""

    architecture: SpatialArchitecture
    authority_ceiling: AuthorityCeiling = AuthorityCeiling.DESIGN_ONLY

    def __post_init__(self) -> None:
        if not isinstance(self.architecture, SpatialArchitecture):
            raise TypeError("architecture must be a SpatialArchitecture")
        object.__setattr__(
            self,
            "authority_ceiling",
            AuthorityCeiling.minimum((AuthorityCeiling(self.authority_ceiling), _SPATIAL_CEILING)),
        )

    def to_plane_assessment(self) -> PlaneAssessment:
        return build_spatial_plane_assessment(
            self.architecture,
            authority_ceiling=self.authority_ceiling,
        )


__all__ = [
    "ParticipantSpatialObservation",
    "PredictedSpatialTransport",
    "SpatialArchitecture",
    "SpatialDimension",
    "SpatialDimensionHypothesis",
    "SpatialPlaneAdapter",
    "SpatialRelationHypothesis",
    "SpatialRelationKind",
    "SpatialScope",
    "build_spatial_plane_assessment",
]
