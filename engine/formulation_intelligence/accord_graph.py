"""Strict structural relation graphs for candidate perfume architecture.

This module stores caller-supplied architectural candidates without turning
them into a formula or an empirical conclusion.  Edges are typed relations,
not weighted votes.  A graph preserves exact target, condition, temporal, and
matrix scopes as well as the originating architectural planes.  In particular,
``HYPOTHESIS_SYNERGY`` remains a hypothesis: its presence does not establish
mixture synergy, smell, liking, safety, stability, or release suitability.

The legacy :mod:`engine.graphs.accord_graph` module is intentionally not
imported.  Legacy or external records can enter only when a caller serializes
and supplies them explicitly to :meth:`AccordRelationGraph.from_caller_records`.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, TypeVar, cast

from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)

_RecordT = TypeVar("_RecordT", bound="_GraphRecord")

MANDATORY_GRAPH_EXCLUSIONS: tuple[str, ...] = (
    "formula generation",
    "liking inference",
    "physical execution authority",
    "release authority",
    "safety inference",
    "smell inference",
    "stability inference",
)


def _text(value: object, field_name: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if identifier else normalized


def _text_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    allow_empty: bool = True,
    identifiers: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(
        _text(value, field_name, identifier=identifiers) for value in values
    )
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized, key=lambda value: (value.casefold(), value)))


def _planes(values: Iterable[PlaneId], field_name: str) -> tuple[PlaneId, ...]:
    normalized = tuple(PlaneId(value) for value in values)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique planes")
    return tuple(sorted(normalized, key=lambda value: value.value))


def _merged_provenance(
    values: Iterable[ProvenanceRef],
    *,
    allow_empty: bool = False,
) -> tuple[ProvenanceRef, ...]:
    by_id: dict[str, ProvenanceRef] = {}
    for value in values:
        if not isinstance(value, ProvenanceRef):
            raise TypeError("provenance_refs must contain ProvenanceRef values")
        current = by_id.get(value.provenance_id)
        if current is not None and current != value:
            raise ValueError(
                f"provenance_id {value.provenance_id!r} has conflicting definitions"
            )
        by_id[value.provenance_id] = value
    if not allow_empty and not by_id:
        raise ValueError("provenance_refs must not be empty")
    return tuple(by_id[key] for key in sorted(by_id))


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (_GraphRecord, ProvenanceRef)):
        return value.as_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not permit non-finite floats")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"{type(value).__name__} is not canonically serializable")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _to_primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_json_text(value: Any) -> str:
    return _canonical_json_bytes(value).decode("utf-8")


def _slug(value: str) -> str:
    normalized = _text(value, "identifier", identifier=True)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    if not slug:
        raise ValueError("identifier cannot normalize to an empty slug")
    return slug


class _GraphRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{
                item.name: _to_primitive(getattr(self, item.name))
                for item in fields(cast(Any, self))
            },
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()

    @classmethod
    def _payload(cls, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("canonical payload must be a mapping")
        expected = {
            "schema_version",
            *(item.name for item in fields(cast(Any, cls))),
        }
        received = set(payload)
        if received != expected:
            missing = sorted(expected - received)
            extra = sorted(received - expected)
            raise ValueError(
                f"{cls.SCHEMA_VERSION} payload does not match the closed schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {cls.SCHEMA_VERSION!r}, "
                f"received {payload['schema_version']!r}"
            )
        return payload


class NodeKind(str, Enum):
    TARGET = "target"
    ACCORD = "accord"
    MATERIAL_CANDIDATE = "material_candidate"
    FUNCTIONAL_ROLE = "functional_role"
    FACET = "facet"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class RelationKind(str, Enum):
    SUPPORTS = "supports"
    BRIDGES = "bridges"
    CONTRASTS = "contrasts"
    MASKS = "masks"
    CONFLICTS = "conflicts"
    SUCCESSION = "succession"
    PERSISTENCE = "persistence"
    SHARED_ROLE = "shared_role"
    HYPOTHESIS_SYNERGY = "hypothesis_synergy"


class EdgeOrientation(str, Enum):
    DIRECTED = "directed"
    UNDIRECTED = "undirected"


class EpistemicState(str, Enum):
    """Structural record state, deliberately excluding empirical promotion."""

    DECLARED = "declared"
    HYPOTHESIS = "hypothesis"
    UNKNOWN = "unknown"


_DIRECTED_RELATIONS = frozenset(
    {
        RelationKind.SUPPORTS,
        RelationKind.BRIDGES,
        RelationKind.MASKS,
        RelationKind.SUCCESSION,
        RelationKind.PERSISTENCE,
    }
)
_UNDIRECTED_RELATIONS = frozenset(
    {
        RelationKind.CONTRASTS,
        RelationKind.CONFLICTS,
        RelationKind.SHARED_ROLE,
        RelationKind.HYPOTHESIS_SYNERGY,
    }
)


@dataclass(frozen=True, slots=True)
class GraphScope(_GraphRecord):
    """Exact condition key for every record in one relation graph."""

    SCHEMA_VERSION = "formulation_accord_graph_scope_v1"

    target_scope: str
    condition_scope: str
    temporal_scope: str
    matrix_scope: str

    def __post_init__(self) -> None:
        for field_name in (
            "target_scope",
            "condition_scope",
            "temporal_scope",
            "matrix_scope",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name, identifier=True),
            )

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (
            self.target_scope,
            self.condition_scope,
            self.temporal_scope,
            self.matrix_scope,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GraphScope:
        data = cls._payload(payload)
        return cls(
            target_scope=data["target_scope"],
            condition_scope=data["condition_scope"],
            temporal_scope=data["temporal_scope"],
            matrix_scope=data["matrix_scope"],
        )


def _validate_epistemic_state(
    *,
    epistemic_state: EpistemicState,
    authority_ceiling: AuthorityCeiling,
    unknown_reason: str | None,
) -> str | None:
    if epistemic_state is EpistemicState.UNKNOWN:
        if unknown_reason is None:
            raise ValueError("UNKNOWN records require an unknown_reason")
        if authority_ceiling is not AuthorityCeiling.WITHHELD:
            raise ValueError("UNKNOWN records require a WITHHELD authority ceiling")
        return _text(unknown_reason, "unknown_reason")
    if unknown_reason is not None:
        raise ValueError("only UNKNOWN records may declare unknown_reason")
    if (
        epistemic_state is EpistemicState.HYPOTHESIS
        and not authority_ceiling.is_no_stronger_than(
            AuthorityCeiling.HYPOTHESIS_ONLY
        )
    ):
        raise ValueError(
            "hypothesis records cannot exceed HYPOTHESIS_ONLY authority"
        )
    return None


@dataclass(frozen=True, slots=True)
class GraphNode(_GraphRecord):
    SCHEMA_VERSION = "formulation_accord_graph_node_v1"

    node_id: str
    node_kind: NodeKind
    label: str
    scope: GraphScope
    plane_ids: tuple[PlaneId, ...]
    epistemic_state: EpistemicState
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]
    unknown_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _text(self.node_id, "node_id", identifier=True))
        object.__setattr__(self, "node_kind", NodeKind(self.node_kind))
        object.__setattr__(self, "label", _text(self.label, "label"))
        if not isinstance(self.scope, GraphScope):
            raise TypeError("scope must be a GraphScope")
        object.__setattr__(self, "plane_ids", _planes(self.plane_ids, "plane_ids"))
        state = EpistemicState(self.epistemic_state)
        authority = AuthorityCeiling(self.authority_ceiling)
        object.__setattr__(self, "epistemic_state", state)
        object.__setattr__(self, "authority_ceiling", authority)
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance(self.provenance_refs),
        )
        object.__setattr__(
            self,
            "unknown_reason",
            _validate_epistemic_state(
                epistemic_state=state,
                authority_ceiling=authority,
                unknown_reason=self.unknown_reason,
            ),
        )
        if self.node_kind is NodeKind.UNKNOWN and state is not EpistemicState.UNKNOWN:
            raise ValueError("UNKNOWN node kinds require UNKNOWN epistemic state")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GraphNode:
        data = cls._payload(payload)
        return cls(
            node_id=data["node_id"],
            node_kind=NodeKind(data["node_kind"]),
            label=data["label"],
            scope=GraphScope.from_dict(data["scope"]),
            plane_ids=tuple(PlaneId(value) for value in data["plane_ids"]),
            epistemic_state=EpistemicState(data["epistemic_state"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            unknown_reason=data["unknown_reason"],
        )


@dataclass(frozen=True, slots=True)
class GraphEdge(_GraphRecord):
    SCHEMA_VERSION = "formulation_accord_graph_edge_v1"

    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_kind: RelationKind
    orientation: EdgeOrientation
    scope: GraphScope
    plane_ids: tuple[PlaneId, ...]
    epistemic_state: EpistemicState
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]
    rationale: str
    unknown_reason: str | None = None
    alternative_group_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _text(self.edge_id, "edge_id", identifier=True))
        source = _text(self.source_node_id, "source_node_id", identifier=True)
        target = _text(self.target_node_id, "target_node_id", identifier=True)
        if source == target:
            raise ValueError("graph edges require distinct endpoints")
        relation = RelationKind(self.relation_kind)
        orientation = EdgeOrientation(self.orientation)
        expected_orientation = (
            EdgeOrientation.DIRECTED
            if relation in _DIRECTED_RELATIONS
            else EdgeOrientation.UNDIRECTED
        )
        if orientation is not expected_orientation:
            raise ValueError(
                f"{relation.value} requires {expected_orientation.value} orientation"
            )
        if orientation is EdgeOrientation.UNDIRECTED and target < source:
            source, target = target, source
        object.__setattr__(self, "source_node_id", source)
        object.__setattr__(self, "target_node_id", target)
        object.__setattr__(self, "relation_kind", relation)
        object.__setattr__(self, "orientation", orientation)
        if not isinstance(self.scope, GraphScope):
            raise TypeError("scope must be a GraphScope")
        object.__setattr__(self, "plane_ids", _planes(self.plane_ids, "plane_ids"))
        state = EpistemicState(self.epistemic_state)
        authority = AuthorityCeiling(self.authority_ceiling)
        object.__setattr__(self, "epistemic_state", state)
        object.__setattr__(self, "authority_ceiling", authority)
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance(self.provenance_refs),
        )
        object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
        object.__setattr__(
            self,
            "unknown_reason",
            _validate_epistemic_state(
                epistemic_state=state,
                authority_ceiling=authority,
                unknown_reason=self.unknown_reason,
            ),
        )
        if relation is RelationKind.HYPOTHESIS_SYNERGY:
            if state is not EpistemicState.HYPOTHESIS:
                raise ValueError("hypothesis synergy must remain a hypothesis")
            if not authority.is_no_stronger_than(AuthorityCeiling.HYPOTHESIS_ONLY):
                raise ValueError(
                    "hypothesis synergy cannot exceed HYPOTHESIS_ONLY authority"
                )
        if self.alternative_group_id is not None:
            object.__setattr__(
                self,
                "alternative_group_id",
                _text(
                    self.alternative_group_id,
                    "alternative_group_id",
                    identifier=True,
                ),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GraphEdge:
        data = cls._payload(payload)
        return cls(
            edge_id=data["edge_id"],
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            relation_kind=RelationKind(data["relation_kind"]),
            orientation=EdgeOrientation(data["orientation"]),
            scope=GraphScope.from_dict(data["scope"]),
            plane_ids=tuple(PlaneId(value) for value in data["plane_ids"]),
            epistemic_state=EpistemicState(data["epistemic_state"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            rationale=data["rationale"],
            unknown_reason=data["unknown_reason"],
            alternative_group_id=data["alternative_group_id"],
        )


@dataclass(frozen=True, slots=True)
class RelationAlternativeSet(_GraphRecord):
    """Explicitly non-collapsed alternative relation candidates."""

    SCHEMA_VERSION = "formulation_accord_graph_alternative_set_v1"

    alternative_set_id: str
    scope: GraphScope
    edge_ids: tuple[str, ...]
    reason: str
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "alternative_set_id",
            _text(self.alternative_set_id, "alternative_set_id", identifier=True),
        )
        if not isinstance(self.scope, GraphScope):
            raise TypeError("scope must be a GraphScope")
        edge_ids = _text_tuple(
            self.edge_ids,
            "edge_ids",
            allow_empty=False,
            identifiers=True,
        )
        if len(edge_ids) < 2:
            raise ValueError("alternative sets require at least two edge_ids")
        object.__setattr__(self, "edge_ids", edge_ids)
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance(self.provenance_refs),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RelationAlternativeSet:
        data = cls._payload(payload)
        return cls(
            alternative_set_id=data["alternative_set_id"],
            scope=GraphScope.from_dict(data["scope"]),
            edge_ids=tuple(data["edge_ids"]),
            reason=data["reason"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class GraphUnknown(_GraphRecord):
    """A graph-relevant missing fact; absence never becomes numeric zero."""

    SCHEMA_VERSION = "formulation_accord_graph_unknown_v1"

    unknown_id: str
    field_key: str
    scope: GraphScope
    reason: str
    needed_evidence: str
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "unknown_id", _text(self.unknown_id, "unknown_id", identifier=True)
        )
        object.__setattr__(
            self, "field_key", _text(self.field_key, "field_key", identifier=True)
        )
        if not isinstance(self.scope, GraphScope):
            raise TypeError("scope must be a GraphScope")
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        object.__setattr__(
            self,
            "needed_evidence",
            _text(self.needed_evidence, "needed_evidence"),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance(self.provenance_refs),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GraphUnknown:
        data = cls._payload(payload)
        return cls(
            unknown_id=data["unknown_id"],
            field_key=data["field_key"],
            scope=GraphScope.from_dict(data["scope"]),
            reason=data["reason"],
            needed_evidence=data["needed_evidence"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def _unique_records(
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
        identifier = cast(str, getattr(value, id_attribute))
        if identifier in by_id:
            raise ValueError(f"{field_name} must contain unique {id_attribute} values")
        by_id[identifier] = value
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class AccordRelationGraph(_GraphRecord):
    """Immutable, exact-scope, non-aggregating relation graph."""

    SCHEMA_VERSION = "formulation_accord_relation_graph_v1"

    graph_id: str
    scope: GraphScope
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    alternative_sets: tuple[RelationAlternativeSet, ...]
    unknowns: tuple[GraphUnknown, ...]
    provenance_refs: tuple[ProvenanceRef, ...]
    authority_ceiling: AuthorityCeiling
    authority_exclusions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "graph_id", _text(self.graph_id, "graph_id", identifier=True)
        )
        if not isinstance(self.scope, GraphScope):
            raise TypeError("scope must be a GraphScope")
        authority = AuthorityCeiling(self.authority_ceiling)
        if not authority.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError(
                "accord relation graph authority ceiling cannot exceed STRUCTURAL_ONLY"
            )
        object.__setattr__(self, "authority_ceiling", authority)
        exclusions = _text_tuple(
            self.authority_exclusions,
            "authority_exclusions",
            allow_empty=False,
            identifiers=True,
        )
        missing_exclusions = sorted(set(MANDATORY_GRAPH_EXCLUSIONS) - set(exclusions))
        if missing_exclusions:
            raise ValueError(
                "mandatory authority exclusions are missing: "
                + ", ".join(missing_exclusions)
            )
        object.__setattr__(self, "authority_exclusions", exclusions)

        nodes = _unique_records(
            self.nodes,
            record_type=GraphNode,
            id_attribute="node_id",
            field_name="nodes",
        )
        edges = _unique_records(
            self.edges,
            record_type=GraphEdge,
            id_attribute="edge_id",
            field_name="edges",
        )
        alternatives = _unique_records(
            self.alternative_sets,
            record_type=RelationAlternativeSet,
            id_attribute="alternative_set_id",
            field_name="alternative_sets",
        )
        unknowns = _unique_records(
            self.unknowns,
            record_type=GraphUnknown,
            id_attribute="unknown_id",
            field_name="unknowns",
        )
        scoped_records: tuple[
            GraphNode | GraphEdge | RelationAlternativeSet | GraphUnknown, ...
        ] = (*nodes, *edges, *alternatives, *unknowns)
        for record in scoped_records:
            if record.scope != self.scope:
                raise ValueError("all graph records must use the exact graph scope")
        authority_records: tuple[GraphNode | GraphEdge, ...] = (*nodes, *edges)
        for record in authority_records:
            if not record.authority_ceiling.is_no_stronger_than(authority):
                raise ValueError(
                    f"record {record.content_sha256!r} exceeds graph authority ceiling"
                )

        node_by_id = {node.node_id: node for node in nodes}
        edge_by_id = {edge.edge_id: edge for edge in edges}
        for edge in edges:
            missing_endpoints = sorted(
                endpoint
                for endpoint in (edge.source_node_id, edge.target_node_id)
                if endpoint not in node_by_id
            )
            if missing_endpoints:
                raise ValueError(
                    f"edge {edge.edge_id!r} has unknown endpoint(s): "
                    + ", ".join(missing_endpoints)
                )
            endpoint_planes = {
                *node_by_id[edge.source_node_id].plane_ids,
                *node_by_id[edge.target_node_id].plane_ids,
            }
            if not endpoint_planes.issubset(set(edge.plane_ids)):
                raise ValueError(
                    f"edge {edge.edge_id!r} must preserve endpoint planes"
                )

        alternatives_by_id = {
            item.alternative_set_id: item for item in alternatives
        }
        claimed_groups: dict[str, set[str]] = {}
        for edge in edges:
            if edge.alternative_group_id is not None:
                claimed_groups.setdefault(edge.alternative_group_id, set()).add(
                    edge.edge_id
                )
        for alternative in alternatives:
            missing_edges = sorted(set(alternative.edge_ids) - set(edge_by_id))
            if missing_edges:
                raise ValueError(
                    f"alternative group {alternative.alternative_set_id!r} "
                    "references unknown edges: "
                    + ", ".join(missing_edges)
                )
            declared = claimed_groups.get(alternative.alternative_set_id, set())
            if declared != set(alternative.edge_ids):
                raise ValueError(
                    f"alternative group {alternative.alternative_set_id!r} "
                    "does not exactly match edge declarations"
                )
        undeclared_groups = sorted(set(claimed_groups) - set(alternatives_by_id))
        if undeclared_groups:
            raise ValueError(
                "edge alternative group declarations have no alternative set: "
                + ", ".join(undeclared_groups)
            )

        nested_provenance = (
            *(item for node in nodes for item in node.provenance_refs),
            *(item for edge in edges for item in edge.provenance_refs),
            *(item for group in alternatives for item in group.provenance_refs),
            *(item for unknown in unknowns for item in unknown.provenance_refs),
        )
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "alternative_sets", alternatives)
        object.__setattr__(self, "unknowns", unknowns)
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance((*self.provenance_refs, *nested_provenance)),
        )

    def node(self, node_id: str) -> GraphNode:
        normalized = _text(node_id, "node_id", identifier=True)
        for node in self.nodes:
            if node.node_id == normalized:
                return node
        raise KeyError(normalized)

    def edge(self, edge_id: str) -> GraphEdge:
        normalized = _text(edge_id, "edge_id", identifier=True)
        for edge in self.edges:
            if edge.edge_id == normalized:
                return edge
        raise KeyError(normalized)

    def nodes_by_kind(self, node_kind: NodeKind) -> tuple[GraphNode, ...]:
        kind = NodeKind(node_kind)
        return tuple(node for node in self.nodes if node.node_kind is kind)

    def nodes_in_plane(self, plane_id: PlaneId) -> tuple[GraphNode, ...]:
        plane = PlaneId(plane_id)
        return tuple(node for node in self.nodes if plane in node.plane_ids)

    def edges_by_relation(self, relation_kind: RelationKind) -> tuple[GraphEdge, ...]:
        relation = RelationKind(relation_kind)
        return tuple(edge for edge in self.edges if edge.relation_kind is relation)

    def incident_edges(self, node_id: str) -> tuple[GraphEdge, ...]:
        node = self.node(node_id)
        return tuple(
            edge
            for edge in self.edges
            if node.node_id in (edge.source_node_id, edge.target_node_id)
        )

    def outgoing_edges(self, node_id: str) -> tuple[GraphEdge, ...]:
        node = self.node(node_id)
        return tuple(
            edge
            for edge in self.edges
            if edge.source_node_id == node.node_id
            or (
                edge.orientation is EdgeOrientation.UNDIRECTED
                and edge.target_node_id == node.node_id
            )
        )

    def incoming_edges(self, node_id: str) -> tuple[GraphEdge, ...]:
        node = self.node(node_id)
        return tuple(
            edge
            for edge in self.edges
            if edge.target_node_id == node.node_id
            or (
                edge.orientation is EdgeOrientation.UNDIRECTED
                and edge.source_node_id == node.node_id
            )
        )

    def neighbors(
        self,
        node_id: str,
        *,
        relation_kinds: Iterable[RelationKind] | None = None,
    ) -> tuple[GraphNode, ...]:
        node = self.node(node_id)
        allowed = (
            None
            if relation_kinds is None
            else {RelationKind(value) for value in relation_kinds}
        )
        neighbor_ids: set[str] = set()
        for edge in self.incident_edges(node.node_id):
            if allowed is not None and edge.relation_kind not in allowed:
                continue
            neighbor_ids.add(
                edge.target_node_id
                if edge.source_node_id == node.node_id
                else edge.source_node_id
            )
        return tuple(self.node(identifier) for identifier in sorted(neighbor_ids))

    def alternatives_for_edge(self, edge_id: str) -> RelationAlternativeSet | None:
        edge = self.edge(edge_id)
        if edge.alternative_group_id is None:
            return None
        return next(
            group
            for group in self.alternative_sets
            if group.alternative_set_id == edge.alternative_group_id
        )

    def conflicts_for_node(self, node_id: str) -> tuple[GraphEdge, ...]:
        return tuple(
            edge
            for edge in self.incident_edges(node_id)
            if edge.relation_kind is RelationKind.CONFLICTS
        )

    def reachable_from(
        self,
        node_id: str,
        *,
        relation_kinds: Iterable[RelationKind] | None = None,
    ) -> tuple[GraphNode, ...]:
        start = self.node(node_id)
        allowed = (
            None
            if relation_kinds is None
            else {RelationKind(value) for value in relation_kinds}
        )
        discovered: set[str] = set()
        frontier = [start.node_id]
        while frontier:
            current = frontier.pop(0)
            for edge in self.outgoing_edges(current):
                if allowed is not None and edge.relation_kind not in allowed:
                    continue
                neighbor = (
                    edge.target_node_id
                    if edge.source_node_id == current
                    else edge.source_node_id
                )
                if neighbor == start.node_id or neighbor in discovered:
                    continue
                discovered.add(neighbor)
                frontier.append(neighbor)
        return tuple(self.node(identifier) for identifier in sorted(discovered))

    def to_plane_assessment(self) -> PlaneAssessment:
        """Adapt this exact graph to a non-scalarized RELATION-plane packet."""

        return accord_graph_to_plane_assessment(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AccordRelationGraph:
        data = cls._payload(payload)
        return cls(
            graph_id=data["graph_id"],
            scope=GraphScope.from_dict(data["scope"]),
            nodes=tuple(GraphNode.from_dict(item) for item in data["nodes"]),
            edges=tuple(GraphEdge.from_dict(item) for item in data["edges"]),
            alternative_sets=tuple(
                RelationAlternativeSet.from_dict(item)
                for item in data["alternative_sets"]
            ),
            unknowns=tuple(GraphUnknown.from_dict(item) for item in data["unknowns"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            authority_exclusions=tuple(data["authority_exclusions"]),
        )

    @classmethod
    def from_caller_records(
        cls,
        *,
        graph_id: str,
        scope_record: Mapping[str, Any],
        node_records: Iterable[Mapping[str, Any]],
        edge_records: Iterable[Mapping[str, Any]],
        alternative_records: Iterable[Mapping[str, Any]],
        unknown_records: Iterable[Mapping[str, Any]],
        provenance_records: Iterable[Mapping[str, Any]],
        authority_ceiling: str | AuthorityCeiling,
        authority_exclusions: Iterable[str],
    ) -> AccordRelationGraph:
        """Build only from records explicitly supplied by the current caller."""

        return cls(
            graph_id=graph_id,
            scope=GraphScope.from_dict(scope_record),
            nodes=tuple(GraphNode.from_dict(item) for item in node_records),
            edges=tuple(GraphEdge.from_dict(item) for item in edge_records),
            alternative_sets=tuple(
                RelationAlternativeSet.from_dict(item)
                for item in alternative_records
            ),
            unknowns=tuple(GraphUnknown.from_dict(item) for item in unknown_records),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in provenance_records
            ),
            authority_ceiling=AuthorityCeiling(authority_ceiling),
            authority_exclusions=tuple(authority_exclusions),
        )


def _claim_authority(
    record_authority: AuthorityCeiling,
    assessment_authority: AuthorityCeiling,
) -> AuthorityCeiling:
    return AuthorityCeiling.minimum((record_authority, assessment_authority))


def _has_missing_evidence(provenance_refs: Iterable[ProvenanceRef]) -> bool:
    return any(
        ref.evidence_class is EvidenceClass.UNKNOWN or ref.source_sha256 is None
        for ref in provenance_refs
    )


def accord_graph_to_plane_assessment(graph: AccordRelationGraph) -> PlaneAssessment:
    """Emit a deterministic ``RELATION`` assessment without scalarization.

    The adapter is lossless at the record boundary: canonical graph, node, edge,
    and alternative-set payloads become collection members, conflict edges also
    remain explicit :class:`PlaneConflict` records, and unresolved records become
    :class:`UnknownFact` values.  Missing or unbound evidence lowers the complete
    packet to ``WITHHELD`` and records a ``HOLD`` instead of allowing structural
    declarations to masquerade as observations.
    """

    if not isinstance(graph, AccordRelationGraph):
        raise TypeError("graph must be an AccordRelationGraph")

    evidence_missing = _has_missing_evidence(graph.provenance_refs)
    assessment_authority = (
        AuthorityCeiling.WITHHELD if evidence_missing else graph.authority_ceiling
    )
    graph_metadata = {
        "schema_version": graph.SCHEMA_VERSION,
        "graph_id": graph.graph_id,
        "scope": graph.scope.as_dict(),
        "authority_ceiling": graph.authority_ceiling.value,
        "authority_exclusions": list(graph.authority_exclusions),
        "content_sha256": graph.content_sha256,
    }

    claims: list[ScopedClaim] = [
        ScopedClaim(
            claim_id=f"relation-graph-{_slug(graph.graph_id)}",
            claim_key="relation.graph",
            claim_value=_canonical_json_text(graph_metadata),
            claim_kind=ClaimKind.DIAGNOSTIC,
            authority_ceiling=assessment_authority,
            provenance_refs=graph.provenance_refs,
        )
    ]
    node_claim_ids: dict[str, str] = {}
    edge_claim_ids: dict[str, str] = {}
    for node in graph.nodes:
        claim_id = f"relation-node-{_slug(node.node_id)}"
        node_claim_ids[node.node_id] = claim_id
        claims.append(
            ScopedClaim(
                claim_id=claim_id,
                claim_key="relation.node",
                claim_value=_canonical_json_text(node.as_dict()),
                claim_kind=ClaimKind.HYPOTHESIS,
                authority_ceiling=_claim_authority(
                    node.authority_ceiling, assessment_authority
                ),
                provenance_refs=node.provenance_refs,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=node.node_id,
            )
        )
    for edge in graph.edges:
        claim_id = f"relation-edge-{_slug(edge.edge_id)}"
        edge_claim_ids[edge.edge_id] = claim_id
        claims.append(
            ScopedClaim(
                claim_id=claim_id,
                claim_key=f"relation.edge.{edge.relation_kind.value}",
                claim_value=_canonical_json_text(edge.as_dict()),
                claim_kind=ClaimKind.HYPOTHESIS,
                authority_ceiling=_claim_authority(
                    edge.authority_ceiling, assessment_authority
                ),
                provenance_refs=edge.provenance_refs,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=edge.edge_id,
            )
        )
    for alternative in graph.alternative_sets:
        claims.append(
            ScopedClaim(
                claim_id=(
                    "relation-alternative-"
                    f"{_slug(alternative.alternative_set_id)}"
                ),
                claim_key="relation.alternative_set",
                claim_value=_canonical_json_text(alternative.as_dict()),
                claim_kind=ClaimKind.HYPOTHESIS,
                authority_ceiling=assessment_authority,
                provenance_refs=alternative.provenance_refs,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=alternative.alternative_set_id,
            )
        )
    for exclusion in graph.authority_exclusions:
        claims.append(
            ScopedClaim(
                claim_id=f"relation-exclusion-{_slug(exclusion)}",
                claim_key="relation.authority_exclusion",
                claim_value=exclusion,
                claim_kind=ClaimKind.PROHIBITION,
                authority_ceiling=assessment_authority,
                provenance_refs=graph.provenance_refs,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"authority-exclusion:{_slug(exclusion)}",
            )
        )

    conflicts = tuple(
        PlaneConflict(
            conflict_id=f"relation-conflict-{_slug(edge.edge_id)}",
            claim_key="relation.edge.conflicts",
            alternatives=(edge.source_node_id, edge.target_node_id),
            reason=edge.rationale,
            claim_ids=(
                edge_claim_ids[edge.edge_id],
                node_claim_ids[edge.source_node_id],
                node_claim_ids[edge.target_node_id],
            ),
            provenance_refs=edge.provenance_refs,
        )
        for edge in graph.edges
        if edge.relation_kind is RelationKind.CONFLICTS
    )

    unknowns: list[UnknownFact] = [
        UnknownFact(
            unknown_id=unknown.unknown_id,
            field_key=unknown.field_key,
            reason=unknown.reason,
            needed_evidence=unknown.needed_evidence,
            provenance_refs=unknown.provenance_refs,
        )
        for unknown in graph.unknowns
    ]
    unknowns.extend(
        UnknownFact(
            unknown_id=f"relation-node-unknown-{_slug(node.node_id)}",
            field_key=f"relation.node.{node.node_id}",
            reason=cast(str, node.unknown_reason),
            needed_evidence="exact-scope evidence resolving the node identity or role",
            provenance_refs=node.provenance_refs,
        )
        for node in graph.nodes
        if node.epistemic_state is EpistemicState.UNKNOWN
    )
    unknowns.extend(
        UnknownFact(
            unknown_id=f"relation-edge-unknown-{_slug(edge.edge_id)}",
            field_key=f"relation.edge.{edge.edge_id}",
            reason=cast(str, edge.unknown_reason),
            needed_evidence="exact-scope evidence resolving the candidate relation",
            provenance_refs=edge.provenance_refs,
        )
        for edge in graph.edges
        if edge.epistemic_state is EpistemicState.UNKNOWN
    )
    if evidence_missing:
        unknowns.append(
            UnknownFact(
                unknown_id="relation-evidence-hold",
                field_key="relation.evidence",
                reason=(
                    "one or more graph provenance records have UNKNOWN evidence "
                    "class or no bound source SHA-256"
                ),
                needed_evidence=(
                    "source-classified, content-hash-bound evidence for every "
                    "relation graph record"
                ),
                provenance_refs=graph.provenance_refs,
            )
        )

    freshness_hashes = {
        graph.content_sha256,
        *(node.content_sha256 for node in graph.nodes),
        *(edge.content_sha256 for edge in graph.edges),
        *(group.content_sha256 for group in graph.alternative_sets),
        *(unknown.content_sha256 for unknown in graph.unknowns),
        *(
            ref.source_sha256
            for ref in graph.provenance_refs
            if ref.source_sha256 is not None
        ),
    }
    failure_modes = [
        *(f"Authority exclusion: {item}" for item in graph.authority_exclusions),
    ]
    state_records: tuple[GraphNode | GraphEdge, ...] = (*graph.nodes, *graph.edges)
    if graph.unknowns or any(
        record.epistemic_state is EpistemicState.UNKNOWN
        for record in state_records
    ):
        failure_modes.append("HOLD: unresolved relation graph facts")
    if evidence_missing:
        failure_modes.append("HOLD: relation evidence is missing or unbound")

    return PlaneAssessment(
        assessment_id=f"relation-assessment-{graph.content_sha256}",
        module_id="accord-relation-graph-v1",
        plane_id=PlaneId.RELATION,
        scope=AssessmentScope(
            target_scope=graph.scope.target_scope,
            temporal_scope=graph.scope.temporal_scope,
            matrix_scope=graph.scope.matrix_scope,
        ),
        claims=tuple(claims),
        support_intervals=(),
        conflicts=conflicts,
        unknowns=tuple(unknowns),
        failure_modes=tuple(failure_modes),
        proposed_experiments=(),
        provenance_refs=graph.provenance_refs,
        authority_ceiling=assessment_authority,
        freshness_hashes=tuple(sorted(freshness_hashes)),
        native_criteria=(),
    )


__all__ = [
    "MANDATORY_GRAPH_EXCLUSIONS",
    "AccordRelationGraph",
    "EdgeOrientation",
    "EpistemicState",
    "GraphEdge",
    "GraphNode",
    "GraphScope",
    "GraphUnknown",
    "NodeKind",
    "RelationAlternativeSet",
    "RelationKind",
    "accord_graph_to_plane_assessment",
]
