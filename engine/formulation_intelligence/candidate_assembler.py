"""Fail-closed structural assembly of caller-supplied candidate packets.

This module does not select ingredients, calculate quantities, generate a formula,
or claim observed perfume performance.  It binds exact-scope plane assessments,
candidate decisions, typed relation packets, alternatives, Pareto fronts, and
source receipts into one immutable design receipt while retaining every unknown,
conflict, hold, and exclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping, TypeVar

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _normalized_text_tuple,
    _payload,
    _sha256_digest,
)

_RecordT = TypeVar("_RecordT", bound=_CanonicalRecord)


def _optional_identifier(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalized_identifier(value, field_name)


def _identifier_tuple(
    values: Iterable[str], field_name: str, *, allow_empty: bool = True
) -> tuple[str, ...]:
    return _normalized_text_tuple(
        values,
        field_name,
        allow_empty=allow_empty,
        identifiers=True,
    )


def _freshness_hashes(values: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({_sha256_digest(value, "freshness_hashes") for value in values}))
    if not normalized:
        raise ValueError("freshness_hashes must not be empty")
    return normalized


def _records(
    values: Iterable[_RecordT],
    *,
    record_type: type[_RecordT],
    id_attribute: str,
    field_name: str,
) -> tuple[_RecordT, ...]:
    by_id: dict[str, _RecordT] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} values")
        identifier = getattr(value, id_attribute)
        if identifier in by_id:
            raise ValueError(f"{field_name} must contain unique {id_attribute} values")
        by_id[identifier] = value
    return tuple(by_id[key] for key in sorted(by_id))


class AssemblyLayer(str, Enum):
    TARGET_IDEAL = "target_ideal"
    CURRENT_INVENTORY_BUILD = "current_inventory_build"


class CandidateDisposition(str, Enum):
    SELECT = "select"
    REJECT = "reject"
    HOLD = "hold"


class RelationDisposition(str, Enum):
    PROPOSED = "proposed"
    HOLD = "hold"
    EXCLUDED = "excluded"


class SourceRecordKind(str, Enum):
    PLANE_ASSESSMENT = "plane_assessment"
    CANDIDATE_DECISION = "candidate_decision"
    RELATION_PACKET = "relation_packet"


@dataclass(frozen=True, slots=True)
class PlaneRequirement(_CanonicalRecord):
    """One exact plane/scope pair required by an assembly request."""

    SCHEMA_VERSION = "candidate_assembly_plane_requirement_v1"

    plane_id: PlaneId
    scope: AssessmentScope

    def __post_init__(self) -> None:
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")

    @property
    def key(self) -> tuple[str, tuple[str, str, str]]:
        return (self.plane_id.value, self.scope.key)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlaneRequirement:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
        )


@dataclass(frozen=True, slots=True)
class CandidateDecisionPacket(_CanonicalRecord):
    """A caller-supplied structural decision, never a formula selection command."""

    SCHEMA_VERSION = "candidate_decision_packet_v1"

    decision_id: str
    alternative_id: str
    target_ideal_id: str
    current_inventory_build_id: str | None
    layer: AssemblyLayer
    plane_id: PlaneId
    scope: AssessmentScope
    candidate_id: str
    disposition: CandidateDisposition
    target_linked_function: str
    omission_loss: str
    failure_mode: str
    provenance_refs: tuple[ProvenanceRef, ...]
    freshness_hashes: tuple[str, ...]
    authority_ceiling: AuthorityCeiling

    def __post_init__(self) -> None:
        for field_name in (
            "decision_id",
            "alternative_id",
            "target_ideal_id",
            "candidate_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        layer = AssemblyLayer(self.layer)
        object.__setattr__(self, "layer", layer)
        build_id = _optional_identifier(
            self.current_inventory_build_id, "current_inventory_build_id"
        )
        if layer is AssemblyLayer.TARGET_IDEAL:
            if build_id is not None:
                raise ValueError("target/ideal decisions cannot bind a current-inventory build")
        elif build_id is None:
            raise ValueError("current-inventory build decisions require a build ID")
        if build_id == self.target_ideal_id:
            raise ValueError("target/ideal and current-inventory build IDs must remain distinct")
        object.__setattr__(self, "current_inventory_build_id", build_id)
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        if self.scope.target_scope != self.target_ideal_id:
            raise ValueError("decision scope does not bind its target/ideal ID")
        object.__setattr__(self, "disposition", CandidateDisposition(self.disposition))
        for field_name in ("target_linked_function", "omission_loss", "failure_mode"):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("candidate decisions require provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        object.__setattr__(self, "freshness_hashes", _freshness_hashes(self.freshness_hashes))
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.DESIGN_ONLY):
            raise ValueError("candidate decision authority cannot exceed design_only")
        object.__setattr__(self, "authority_ceiling", ceiling)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateDecisionPacket:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            decision_id=data["decision_id"],
            alternative_id=data["alternative_id"],
            target_ideal_id=data["target_ideal_id"],
            current_inventory_build_id=data["current_inventory_build_id"],
            layer=AssemblyLayer(data["layer"]),
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
            candidate_id=data["candidate_id"],
            disposition=CandidateDisposition(data["disposition"]),
            target_linked_function=data["target_linked_function"],
            omission_loss=data["omission_loss"],
            failure_mode=data["failure_mode"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            freshness_hashes=tuple(data["freshness_hashes"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
        )


@dataclass(frozen=True, slots=True)
class RelationPacket(_CanonicalRecord):
    """A typed structural relation proposal with exact scope and provenance."""

    SCHEMA_VERSION = "candidate_relation_packet_v1"

    packet_id: str
    alternative_id: str
    target_ideal_id: str
    current_inventory_build_id: str | None
    layer: AssemblyLayer
    plane_id: PlaneId
    scope: AssessmentScope
    relation_kind: str
    subject_candidate_ids: tuple[str, ...]
    object_candidate_ids: tuple[str, ...]
    disposition: RelationDisposition
    rationale: str
    provenance_refs: tuple[ProvenanceRef, ...]
    freshness_hashes: tuple[str, ...]
    authority_ceiling: AuthorityCeiling

    def __post_init__(self) -> None:
        for field_name in ("packet_id", "alternative_id", "target_ideal_id", "relation_kind"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        layer = AssemblyLayer(self.layer)
        object.__setattr__(self, "layer", layer)
        build_id = _optional_identifier(
            self.current_inventory_build_id, "current_inventory_build_id"
        )
        if layer is AssemblyLayer.TARGET_IDEAL:
            if build_id is not None:
                raise ValueError("target/ideal relations cannot bind a current-inventory build")
        elif build_id is None:
            raise ValueError("current-inventory build relations require a build ID")
        if build_id == self.target_ideal_id:
            raise ValueError("target/ideal and current-inventory build IDs must remain distinct")
        object.__setattr__(self, "current_inventory_build_id", build_id)
        plane = PlaneId(self.plane_id)
        if plane is not PlaneId.RELATION:
            raise ValueError("relation packets must belong to the relation plane")
        object.__setattr__(self, "plane_id", plane)
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        if self.scope.target_scope != self.target_ideal_id:
            raise ValueError("relation scope does not bind its target/ideal ID")
        subjects = _identifier_tuple(
            self.subject_candidate_ids, "subject_candidate_ids", allow_empty=False
        )
        objects = _identifier_tuple(
            self.object_candidate_ids, "object_candidate_ids", allow_empty=False
        )
        object.__setattr__(self, "subject_candidate_ids", subjects)
        object.__setattr__(self, "object_candidate_ids", objects)
        object.__setattr__(self, "disposition", RelationDisposition(self.disposition))
        object.__setattr__(self, "rationale", _normalized_text(self.rationale, "rationale"))
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("relation packets require provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        object.__setattr__(self, "freshness_hashes", _freshness_hashes(self.freshness_hashes))
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.DESIGN_ONLY):
            raise ValueError("relation packet authority cannot exceed design_only")
        object.__setattr__(self, "authority_ceiling", ceiling)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RelationPacket:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            packet_id=data["packet_id"],
            alternative_id=data["alternative_id"],
            target_ideal_id=data["target_ideal_id"],
            current_inventory_build_id=data["current_inventory_build_id"],
            layer=AssemblyLayer(data["layer"]),
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
            relation_kind=data["relation_kind"],
            subject_candidate_ids=tuple(data["subject_candidate_ids"]),
            object_candidate_ids=tuple(data["object_candidate_ids"]),
            disposition=RelationDisposition(data["disposition"]),
            rationale=data["rationale"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            freshness_hashes=tuple(data["freshness_hashes"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
        )


@dataclass(frozen=True, slots=True)
class ArchitectureAlternative(_CanonicalRecord):
    """One unranked structural alternative and its exact source packet membership."""

    SCHEMA_VERSION = "candidate_architecture_alternative_v1"

    alternative_id: str
    label: str
    candidate_decision_ids: tuple[str, ...]
    relation_packet_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "alternative_id",
            _normalized_identifier(self.alternative_id, "alternative_id"),
        )
        object.__setattr__(self, "label", _normalized_text(self.label, "label"))
        object.__setattr__(
            self,
            "candidate_decision_ids",
            _identifier_tuple(
                self.candidate_decision_ids,
                "candidate_decision_ids",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "relation_packet_ids",
            _identifier_tuple(self.relation_packet_ids, "relation_packet_ids"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArchitectureAlternative:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            alternative_id=data["alternative_id"],
            label=data["label"],
            candidate_decision_ids=tuple(data["candidate_decision_ids"]),
            relation_packet_ids=tuple(data["relation_packet_ids"]),
        )


@dataclass(frozen=True, slots=True)
class ParetoFront(_CanonicalRecord):
    """An unranked set of alternatives evaluated on native, non-aggregated criteria."""

    SCHEMA_VERSION = "candidate_pareto_front_v1"

    front_id: str
    alternative_ids: tuple[str, ...]
    native_criterion_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "front_id", _normalized_identifier(self.front_id, "front_id")
        )
        object.__setattr__(
            self,
            "alternative_ids",
            _identifier_tuple(self.alternative_ids, "alternative_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "native_criterion_ids",
            _identifier_tuple(
                self.native_criterion_ids,
                "native_criterion_ids",
                allow_empty=False,
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ParetoFront:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            front_id=data["front_id"],
            alternative_ids=tuple(data["alternative_ids"]),
            native_criterion_ids=tuple(data["native_criterion_ids"]),
        )


@dataclass(frozen=True, slots=True)
class SourceReceipt(_CanonicalRecord):
    """Hash, exact-scope, provenance, and authority binding for one source record."""

    SCHEMA_VERSION = "candidate_assembly_source_receipt_v1"

    receipt_id: str
    record_kind: SourceRecordKind
    record_id: str
    record_sha256: str
    plane_id: PlaneId
    scope: AssessmentScope
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        for field_name in ("receipt_id", "record_id"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "record_kind", SourceRecordKind(self.record_kind))
        object.__setattr__(
            self,
            "record_sha256",
            _sha256_digest(self.record_sha256, "record_sha256"),
        )
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.DESIGN_ONLY):
            raise ValueError("source receipt authority cannot exceed design_only")
        object.__setattr__(self, "authority_ceiling", ceiling)
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("source receipts require provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @property
    def record_key(self) -> tuple[SourceRecordKind, str]:
        return (self.record_kind, self.record_id)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SourceReceipt:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            receipt_id=data["receipt_id"],
            record_kind=SourceRecordKind(data["record_kind"]),
            record_id=data["record_id"],
            record_sha256=data["record_sha256"],
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def _requirement_records(values: Iterable[PlaneRequirement]) -> tuple[PlaneRequirement, ...]:
    by_key: dict[tuple[str, tuple[str, str, str]], PlaneRequirement] = {}
    for value in values:
        if not isinstance(value, PlaneRequirement):
            raise TypeError("required_plane_scopes must contain PlaneRequirement values")
        if value.key in by_key:
            raise ValueError("required_plane_scopes must contain unique exact plane/scope pairs")
        by_key[value.key] = value
    if not by_key:
        raise ValueError("required_plane_scopes must not be empty")
    return tuple(by_key[key] for key in sorted(by_key))


def _source_record_map(
    assessments: tuple[PlaneAssessment, ...],
    decisions: tuple[CandidateDecisionPacket, ...],
    relations: tuple[RelationPacket, ...],
) -> dict[tuple[SourceRecordKind, str], _CanonicalRecord]:
    result: dict[tuple[SourceRecordKind, str], _CanonicalRecord] = {}
    for kind, values, id_attribute in (
        (SourceRecordKind.PLANE_ASSESSMENT, assessments, "assessment_id"),
        (SourceRecordKind.CANDIDATE_DECISION, decisions, "decision_id"),
        (SourceRecordKind.RELATION_PACKET, relations, "packet_id"),
    ):
        for value in values:
            result[(kind, getattr(value, id_attribute))] = value
    return result


def _record_plane_scope_authority(
    record: _CanonicalRecord,
) -> tuple[PlaneId, AssessmentScope, AuthorityCeiling]:
    return (
        PlaneId(getattr(record, "plane_id")),
        getattr(record, "scope"),
        AuthorityCeiling(getattr(record, "authority_ceiling")),
    )


def _derived_unresolved_ids(
    assessments: tuple[PlaneAssessment, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    conflicts = tuple(
        sorted(
            f"{assessment.assessment_id}:{conflict.conflict_id}"
            for assessment in assessments
            for conflict in assessment.conflicts
        )
    )
    unknowns = tuple(
        sorted(
            f"{assessment.assessment_id}:{unknown.unknown_id}"
            for assessment in assessments
            for unknown in assessment.unknowns
        )
    )
    return conflicts, unknowns


def _required_blockers(
    conflicts: tuple[str, ...],
    unknowns: tuple[str, ...],
    decisions: tuple[CandidateDecisionPacket, ...],
    relations: tuple[RelationPacket, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                *(f"conflict:{item}" for item in conflicts),
                *(f"unknown:{item}" for item in unknowns),
                *(
                    f"hold:{item.decision_id}"
                    for item in decisions
                    if item.disposition is CandidateDisposition.HOLD
                ),
                *(
                    f"hold:{item.packet_id}"
                    for item in relations
                    if item.disposition is RelationDisposition.HOLD
                ),
            }
        )
    )


def _required_exclusions(
    decisions: tuple[CandidateDecisionPacket, ...],
    relations: tuple[RelationPacket, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                *(
                    f"reject:{item.decision_id}"
                    for item in decisions
                    if item.disposition is CandidateDisposition.REJECT
                ),
                *(
                    f"excluded:{item.packet_id}"
                    for item in relations
                    if item.disposition is RelationDisposition.EXCLUDED
                ),
            }
        )
    )


def _derived_source_hashes(
    assessments: tuple[PlaneAssessment, ...],
    decisions: tuple[CandidateDecisionPacket, ...],
    relations: tuple[RelationPacket, ...],
    receipts: tuple[SourceReceipt, ...],
) -> tuple[str, ...]:
    values = {
        *(item.content_sha256 for item in assessments),
        *(digest for item in assessments for digest in item.freshness_hashes),
        *(item.content_sha256 for item in decisions),
        *(digest for item in decisions for digest in item.freshness_hashes),
        *(item.content_sha256 for item in relations),
        *(digest for item in relations for digest in item.freshness_hashes),
        *(item.content_sha256 for item in receipts),
    }
    return tuple(sorted(values))


_AUTHORITY_FLAGS = (
    "formula_generation_authorized",
    "formula_mutation_authorized",
    "inventory_mutation_authorized",
    "runtime_integration_authorized",
    "physical_execution_authorized",
    "compounding_authorized",
    "purchase_authority",
    "pass_fail_authority",
    "sensory_authority",
    "liking_authority",
    "beauty_authority",
    "hedonic_score_authorized",
    "similarity_authority",
    "performance_authority",
    "safety_authority",
    "stability_authority",
    "release_authority",
)


@dataclass(frozen=True, slots=True)
class CandidateAssemblyBlueprint(_CanonicalRecord):
    """Versioned structural blueprint with all execution and outcome authority withheld."""

    SCHEMA_VERSION = "candidate_assembly_blueprint_v1"

    assembly_id: str
    version: int
    predecessor_sha256: str | None
    target_ideal_id: str
    current_inventory_build_id: str
    required_plane_scopes: tuple[PlaneRequirement, ...]
    plane_assessments: tuple[PlaneAssessment, ...]
    candidate_decisions: tuple[CandidateDecisionPacket, ...]
    relation_packets: tuple[RelationPacket, ...]
    alternatives: tuple[ArchitectureAlternative, ...]
    pareto_fronts: tuple[ParetoFront, ...]
    source_receipts: tuple[SourceReceipt, ...]
    unresolved_conflict_ids: tuple[str, ...]
    unresolved_unknown_ids: tuple[str, ...]
    blockers: tuple[str, ...]
    exclusions: tuple[str, ...]
    source_hashes: tuple[str, ...]
    authority_ceiling: AuthorityCeiling
    formula_generation_authorized: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    inventory_mutation_authorized: bool = field(default=False, init=False)
    runtime_integration_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    compounding_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    pass_fail_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    beauty_authority: bool = field(default=False, init=False)
    hedonic_score_authorized: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer")
        if self.version < 1:
            raise ValueError("version must be at least 1")
        predecessor = (
            _sha256_digest(self.predecessor_sha256, "predecessor_sha256")
            if self.predecessor_sha256 is not None
            else None
        )
        if self.version == 1 and predecessor is not None:
            raise ValueError("version 1 must not declare a predecessor")
        if self.version > 1 and predecessor is None:
            raise ValueError("version successors require predecessor_sha256")
        object.__setattr__(self, "predecessor_sha256", predecessor)

        target = _normalized_identifier(self.target_ideal_id, "target_ideal_id")
        build = _normalized_identifier(
            self.current_inventory_build_id, "current_inventory_build_id"
        )
        if target == build:
            raise ValueError("target/ideal and current-inventory build IDs must remain distinct")
        object.__setattr__(self, "target_ideal_id", target)
        object.__setattr__(self, "current_inventory_build_id", build)

        requirements = _requirement_records(self.required_plane_scopes)
        assessments = _records(
            self.plane_assessments,
            record_type=PlaneAssessment,
            id_attribute="assessment_id",
            field_name="plane_assessments",
        )
        decisions = _records(
            self.candidate_decisions,
            record_type=CandidateDecisionPacket,
            id_attribute="decision_id",
            field_name="candidate_decisions",
        )
        relations = _records(
            self.relation_packets,
            record_type=RelationPacket,
            id_attribute="packet_id",
            field_name="relation_packets",
        )
        alternatives = _records(
            self.alternatives,
            record_type=ArchitectureAlternative,
            id_attribute="alternative_id",
            field_name="alternatives",
        )
        fronts = _records(
            self.pareto_fronts,
            record_type=ParetoFront,
            id_attribute="front_id",
            field_name="pareto_fronts",
        )
        receipts = _records(
            self.source_receipts,
            record_type=SourceReceipt,
            id_attribute="receipt_id",
            field_name="source_receipts",
        )
        if not assessments or not decisions or not relations or not receipts:
            raise ValueError("plane assessments, candidate decisions, relation packets, and receipts are required")
        if len(alternatives) < 2:
            raise ValueError("candidate assembly requires at least two architectural alternatives")
        if not fronts:
            raise ValueError("candidate assembly requires at least one Pareto front")

        requirement_keys = {item.key for item in requirements}
        represented_requirement_planes = {item.plane_id for item in requirements}
        if represented_requirement_planes != set(PlaneId):
            missing_planes = sorted(
                (item.value for item in set(PlaneId) - represented_requirement_planes)
            )
            raise ValueError(
                "required_plane_scopes must cover all 13 architectural planes; "
                f"missing={missing_planes!r}"
            )
        assessment_keys = {
            (item.plane_id.value, item.scope.key) for item in assessments
        }
        if assessment_keys != requirement_keys:
            raise ValueError("required plane/scope coverage is incomplete or incompatible")
        for requirement in requirements:
            if requirement.scope.target_scope != target:
                raise ValueError("required plane/scope does not bind the target/ideal ID")
        for assessment in assessments:
            if assessment.scope.target_scope != target:
                raise ValueError("plane assessment scope does not bind the target/ideal ID")
            has_substantive_evidence = bool(
                assessment.claims
                or assessment.support_intervals
                or assessment.conflicts
                or assessment.native_criteria
            )
            if not has_substantive_evidence and (
                assessment.authority_ceiling is not AuthorityCeiling.WITHHELD
                or not assessment.unknowns
            ):
                raise ValueError(
                    "no-evidence plane assessments require WITHHELD authority "
                    "and at least one explicit UnknownFact"
                )
        source_packets: tuple[CandidateDecisionPacket | RelationPacket, ...] = (
            *decisions,
            *relations,
        )
        for packet in source_packets:
            if packet.target_ideal_id != target:
                raise ValueError("source packet target/ideal ID is incompatible")
            if (
                packet.layer is AssemblyLayer.CURRENT_INVENTORY_BUILD
                and packet.current_inventory_build_id != build
            ):
                raise ValueError("source packet current-inventory build ID is incompatible")
            if (packet.plane_id.value, packet.scope.key) not in requirement_keys:
                raise ValueError("source packet does not match a required plane/scope")

        decision_by_id = {item.decision_id: item for item in decisions}
        relation_by_id = {item.packet_id: item for item in relations}
        alternative_by_id = {item.alternative_id: item for item in alternatives}
        used_decisions: list[str] = []
        used_relations: list[str] = []
        for alternative in alternatives:
            for decision_id in alternative.candidate_decision_ids:
                decision = decision_by_id.get(decision_id)
                if decision is None:
                    raise ValueError(f"alternative references unknown candidate decision {decision_id!r}")
                if decision.alternative_id != alternative.alternative_id:
                    raise ValueError("candidate decision alternative binding is incompatible")
                used_decisions.append(decision_id)
            for packet_id in alternative.relation_packet_ids:
                relation_packet = relation_by_id.get(packet_id)
                if relation_packet is None:
                    raise ValueError(f"alternative references unknown relation packet {packet_id!r}")
                if relation_packet.alternative_id != alternative.alternative_id:
                    raise ValueError("relation packet alternative binding is incompatible")
                used_relations.append(packet_id)
        if sorted(used_decisions) != sorted(decision_by_id):
            raise ValueError("every candidate decision must belong to exactly one alternative")
        if len(used_decisions) != len(set(used_decisions)):
            raise ValueError("candidate decisions cannot belong to multiple alternatives")
        if sorted(used_relations) != sorted(relation_by_id):
            raise ValueError("every relation packet must belong to exactly one alternative")
        if len(used_relations) != len(set(used_relations)):
            raise ValueError("relation packets cannot belong to multiple alternatives")

        criterion_ids = {
            criterion.criterion_id
            for assessment in assessments
            for criterion in assessment.native_criteria
        }
        used_alternatives: list[str] = []
        for front in fronts:
            for alternative_id in front.alternative_ids:
                if alternative_id not in alternative_by_id:
                    raise ValueError(f"Pareto front references unknown alternative {alternative_id!r}")
                used_alternatives.append(alternative_id)
            missing_criteria = sorted(set(front.native_criterion_ids) - criterion_ids)
            if missing_criteria:
                raise ValueError(
                    "Pareto front references unknown native criterion: "
                    + ", ".join(missing_criteria)
                )
        if sorted(used_alternatives) != sorted(alternative_by_id):
            raise ValueError("every alternative must belong to exactly one Pareto front")
        if len(used_alternatives) != len(set(used_alternatives)):
            raise ValueError("alternatives cannot belong to multiple Pareto fronts")

        source_records = _source_record_map(assessments, decisions, relations)
        receipts_by_key: dict[tuple[SourceRecordKind, str], SourceReceipt] = {}
        for receipt in receipts:
            if receipt.record_key in receipts_by_key:
                raise ValueError("source receipt coverage contains duplicate record bindings")
            receipts_by_key[receipt.record_key] = receipt
        if set(receipts_by_key) != set(source_records):
            raise ValueError("source receipt coverage is incomplete or contains extra records")
        for key, record in source_records.items():
            receipt = receipts_by_key[key]
            plane, scope, authority = _record_plane_scope_authority(record)
            if receipt.record_sha256 != record.content_sha256:
                raise ValueError(f"receipt hash does not bind {key!r}")
            if receipt.scope != scope or receipt.plane_id is not plane:
                raise ValueError(f"receipt scope does not bind {key!r}")
            if receipt.authority_ceiling is not authority:
                raise ValueError(f"receipt authority does not bind {key!r}")

        conflicts, unknowns = _derived_unresolved_ids(assessments)
        supplied_conflicts = _identifier_tuple(
            self.unresolved_conflict_ids, "unresolved_conflict_ids"
        )
        supplied_unknowns = _identifier_tuple(
            self.unresolved_unknown_ids, "unresolved_unknown_ids"
        )
        if supplied_conflicts != conflicts:
            raise ValueError("unresolved_conflict_ids omit or alter source conflicts")
        if supplied_unknowns != unknowns:
            raise ValueError("unresolved_unknown_ids omit or alter source unknowns")
        blockers = _normalized_text_tuple(self.blockers, "blockers", allow_empty=False)
        exclusions = _normalized_text_tuple(self.exclusions, "exclusions")
        required_blockers = set(_required_blockers(conflicts, unknowns, decisions, relations))
        if not required_blockers.issubset(blockers):
            raise ValueError("blockers omit unresolved conflicts, unknowns, or holds")
        required_exclusions = set(_required_exclusions(decisions, relations))
        if not required_exclusions.issubset(exclusions):
            raise ValueError("exclusions omit rejected or excluded source packets")
        source_hashes = tuple(
            sorted({_sha256_digest(item, "source_hashes") for item in self.source_hashes})
        )
        expected_hashes = _derived_source_hashes(assessments, decisions, relations, receipts)
        if source_hashes != expected_hashes:
            raise ValueError("source_hashes do not exactly preserve source and receipt hashes")

        expected_authority = AuthorityCeiling.minimum(
            (
                AuthorityCeiling.DESIGN_ONLY,
                *(item.authority_ceiling for item in assessments),
                *(item.authority_ceiling for item in decisions),
                *(item.authority_ceiling for item in relations),
                *(item.authority_ceiling for item in receipts),
            )
        )
        authority = AuthorityCeiling(self.authority_ceiling)
        if authority is not expected_authority:
            raise ValueError("authority_ceiling must be the explicit meet of all sources")

        object.__setattr__(self, "required_plane_scopes", requirements)
        object.__setattr__(self, "plane_assessments", assessments)
        object.__setattr__(self, "candidate_decisions", decisions)
        object.__setattr__(self, "relation_packets", relations)
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "pareto_fronts", fronts)
        object.__setattr__(self, "source_receipts", receipts)
        object.__setattr__(self, "unresolved_conflict_ids", conflicts)
        object.__setattr__(self, "unresolved_unknown_ids", unknowns)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "exclusions", exclusions)
        object.__setattr__(self, "source_hashes", source_hashes)
        object.__setattr__(self, "authority_ceiling", authority)
        for flag_name in _AUTHORITY_FLAGS:
            if getattr(self, flag_name) is not False:
                raise ValueError("candidate assembly authority flags must all remain false")

        expected_id = _assembly_id(
            version=self.version,
            predecessor_sha256=predecessor,
            target_ideal_id=target,
            current_inventory_build_id=build,
            required_plane_scopes=requirements,
            plane_assessments=assessments,
            candidate_decisions=decisions,
            relation_packets=relations,
            alternatives=alternatives,
            pareto_fronts=fronts,
            source_receipts=receipts,
            unresolved_conflict_ids=conflicts,
            unresolved_unknown_ids=unknowns,
            blockers=blockers,
            exclusions=exclusions,
            source_hashes=source_hashes,
            authority_ceiling=authority,
        )
        supplied_id = _normalized_text(self.assembly_id, "assembly_id")
        if supplied_id != expected_id:
            raise ValueError("assembly_id does not match candidate assembly content")
        object.__setattr__(self, "assembly_id", supplied_id)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CandidateAssemblyBlueprint:
        data = _payload(payload, cls.SCHEMA_VERSION)
        if any(data[field_name] is not False for field_name in _AUTHORITY_FLAGS):
            raise ValueError("candidate assembly authority flags must all remain false")
        return cls(
            assembly_id=data["assembly_id"],
            version=data["version"],
            predecessor_sha256=data["predecessor_sha256"],
            target_ideal_id=data["target_ideal_id"],
            current_inventory_build_id=data["current_inventory_build_id"],
            required_plane_scopes=tuple(
                PlaneRequirement.from_dict(item)
                for item in data["required_plane_scopes"]
            ),
            plane_assessments=tuple(
                PlaneAssessment.from_dict(item) for item in data["plane_assessments"]
            ),
            candidate_decisions=tuple(
                CandidateDecisionPacket.from_dict(item)
                for item in data["candidate_decisions"]
            ),
            relation_packets=tuple(
                RelationPacket.from_dict(item) for item in data["relation_packets"]
            ),
            alternatives=tuple(
                ArchitectureAlternative.from_dict(item) for item in data["alternatives"]
            ),
            pareto_fronts=tuple(
                ParetoFront.from_dict(item) for item in data["pareto_fronts"]
            ),
            source_receipts=tuple(
                SourceReceipt.from_dict(item) for item in data["source_receipts"]
            ),
            unresolved_conflict_ids=tuple(data["unresolved_conflict_ids"]),
            unresolved_unknown_ids=tuple(data["unresolved_unknown_ids"]),
            blockers=tuple(data["blockers"]),
            exclusions=tuple(data["exclusions"]),
            source_hashes=tuple(data["source_hashes"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
        )


def _assembly_id(
    *,
    version: int,
    predecessor_sha256: str | None,
    target_ideal_id: str,
    current_inventory_build_id: str,
    required_plane_scopes: tuple[PlaneRequirement, ...],
    plane_assessments: tuple[PlaneAssessment, ...],
    candidate_decisions: tuple[CandidateDecisionPacket, ...],
    relation_packets: tuple[RelationPacket, ...],
    alternatives: tuple[ArchitectureAlternative, ...],
    pareto_fronts: tuple[ParetoFront, ...],
    source_receipts: tuple[SourceReceipt, ...],
    unresolved_conflict_ids: tuple[str, ...],
    unresolved_unknown_ids: tuple[str, ...],
    blockers: tuple[str, ...],
    exclusions: tuple[str, ...],
    source_hashes: tuple[str, ...],
    authority_ceiling: AuthorityCeiling,
) -> str:
    digest = sha256(
        _canonical_json_bytes(
            {
                "schema_version": "candidate_assembly_identity_payload_v1",
                "version": version,
                "predecessor_sha256": predecessor_sha256,
                "target_ideal_id": target_ideal_id,
                "current_inventory_build_id": current_inventory_build_id,
                "required_plane_scopes": required_plane_scopes,
                "plane_assessments": plane_assessments,
                "candidate_decisions": candidate_decisions,
                "relation_packets": relation_packets,
                "alternatives": alternatives,
                "pareto_fronts": pareto_fronts,
                "source_receipts": source_receipts,
                "unresolved_conflict_ids": unresolved_conflict_ids,
                "unresolved_unknown_ids": unresolved_unknown_ids,
                "blockers": blockers,
                "exclusions": exclusions,
                "source_hashes": source_hashes,
                "authority_ceiling": authority_ceiling,
            }
        )
    ).hexdigest()
    return f"candidate-assembly/v{version}/{digest}"


def assemble_candidate_blueprint(
    *,
    target_ideal_id: str,
    current_inventory_build_id: str,
    required_plane_scopes: Iterable[PlaneRequirement],
    plane_assessments: Iterable[PlaneAssessment],
    candidate_decisions: Iterable[CandidateDecisionPacket],
    relation_packets: Iterable[RelationPacket],
    alternatives: Iterable[ArchitectureAlternative],
    pareto_fronts: Iterable[ParetoFront],
    source_receipts: Iterable[SourceReceipt],
    version: int,
    predecessor_sha256: str | None = None,
    caller_blockers: Iterable[str] = (),
    caller_exclusions: Iterable[str] = (),
) -> CandidateAssemblyBlueprint:
    """Create a versioned structural receipt without generating or mutating a formula."""

    target = _normalized_identifier(target_ideal_id, "target_ideal_id")
    build = _normalized_identifier(
        current_inventory_build_id, "current_inventory_build_id"
    )
    if target == build:
        raise ValueError("target/ideal and current-inventory build IDs must remain distinct")
    predecessor = (
        _sha256_digest(predecessor_sha256, "predecessor_sha256")
        if predecessor_sha256 is not None
        else None
    )
    if version == 1 and predecessor is not None:
        raise ValueError("version 1 must not declare a predecessor")
    if version > 1 and predecessor is None:
        raise ValueError("version successors require predecessor_sha256")

    requirements = _requirement_records(required_plane_scopes)
    assessments = _records(
        plane_assessments,
        record_type=PlaneAssessment,
        id_attribute="assessment_id",
        field_name="plane_assessments",
    )
    decisions = _records(
        candidate_decisions,
        record_type=CandidateDecisionPacket,
        id_attribute="decision_id",
        field_name="candidate_decisions",
    )
    relations = _records(
        relation_packets,
        record_type=RelationPacket,
        id_attribute="packet_id",
        field_name="relation_packets",
    )
    normalized_alternatives = _records(
        alternatives,
        record_type=ArchitectureAlternative,
        id_attribute="alternative_id",
        field_name="alternatives",
    )
    fronts = _records(
        pareto_fronts,
        record_type=ParetoFront,
        id_attribute="front_id",
        field_name="pareto_fronts",
    )
    receipts = _records(
        source_receipts,
        record_type=SourceReceipt,
        id_attribute="receipt_id",
        field_name="source_receipts",
    )
    conflicts, unknowns = _derived_unresolved_ids(assessments)
    blockers = _normalized_text_tuple(
        (*caller_blockers, *_required_blockers(conflicts, unknowns, decisions, relations)),
        "blockers",
        allow_empty=False,
    )
    exclusions = _normalized_text_tuple(
        (*caller_exclusions, *_required_exclusions(decisions, relations)),
        "exclusions",
    )
    source_hashes = _derived_source_hashes(assessments, decisions, relations, receipts)
    authority = AuthorityCeiling.minimum(
        (
            AuthorityCeiling.DESIGN_ONLY,
            *(item.authority_ceiling for item in assessments),
            *(item.authority_ceiling for item in decisions),
            *(item.authority_ceiling for item in relations),
            *(item.authority_ceiling for item in receipts),
        )
    )
    assembly_id = _assembly_id(
        version=version,
        predecessor_sha256=predecessor,
        target_ideal_id=target,
        current_inventory_build_id=build,
        required_plane_scopes=requirements,
        plane_assessments=assessments,
        candidate_decisions=decisions,
        relation_packets=relations,
        alternatives=normalized_alternatives,
        pareto_fronts=fronts,
        source_receipts=receipts,
        unresolved_conflict_ids=conflicts,
        unresolved_unknown_ids=unknowns,
        blockers=blockers,
        exclusions=exclusions,
        source_hashes=source_hashes,
        authority_ceiling=authority,
    )
    return CandidateAssemblyBlueprint(
        assembly_id=assembly_id,
        version=version,
        predecessor_sha256=predecessor,
        target_ideal_id=target,
        current_inventory_build_id=build,
        required_plane_scopes=requirements,
        plane_assessments=assessments,
        candidate_decisions=decisions,
        relation_packets=relations,
        alternatives=normalized_alternatives,
        pareto_fronts=fronts,
        source_receipts=receipts,
        unresolved_conflict_ids=conflicts,
        unresolved_unknown_ids=unknowns,
        blockers=blockers,
        exclusions=exclusions,
        source_hashes=source_hashes,
        authority_ceiling=authority,
    )


__all__ = [
    "ArchitectureAlternative",
    "AssemblyLayer",
    "CandidateAssemblyBlueprint",
    "CandidateDecisionPacket",
    "CandidateDisposition",
    "ParetoFront",
    "PlaneRequirement",
    "RelationDisposition",
    "RelationPacket",
    "SourceReceipt",
    "SourceRecordKind",
    "assemble_candidate_blueprint",
]
