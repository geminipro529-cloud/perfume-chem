"""Versioned, target-first structural contracts for perfume families.

This module represents a family as a source-bounded architecture rather than a
generic label, an ingredient list, or a scalar score.  The exact named target is
kept separate from its family neighbourhood.  Custom and hybrid definitions
retain their own identities, and catalogue resolution is exact on
``(family_id, version)``: there is no nearest-family or latest-version fallback.

The records carry structural authority only.  They do not assert observed
smell, target fidelity, liking, physical performance, safety, stability,
compounding readiness, or release.  Definition provenance is therefore kept on
claims without manufacturing a numeric evidence-support interval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
    _canonical_json_bytes,
    _CanonicalRecord,
    _merged_provenance,
    _normalized_identifier,
    _normalized_text,
    _payload,
)

_MODULE_ID = "formulation_intelligence.family_architecture"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _stable_id(prefix: str, payload: object) -> str:
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{prefix}:{digest[:24]}"


def _slug(value: str) -> str:
    normalized = _SLUG_RE.sub("-", value.casefold()).strip("-")
    return normalized or "unnamed"


def _nonnegative_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _false_authority_payload(data: Mapping[str, Any]) -> None:
    fields = (
        "ingredient_count_complexity_authority",
        "empirical_smell_authority",
        "liking_authority",
        "safety_authority",
        "stability_authority",
        "release_authority",
    )
    if any(data.get(name) is not False for name in fields):
        raise ValueError("family architecture authority flags must all remain false")


def _canonical_by_id(
    values: Iterable[Any],
    *,
    record_type: type[Any],
    id_attribute: str,
    field_name: str,
) -> tuple[Any, ...]:
    by_id: dict[str, Any] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} values")
        identifier = getattr(value, id_attribute)
        current = by_id.get(identifier)
        if current is not None:
            if current != value:
                raise ValueError(f"{field_name} has conflicting ID {identifier!r}")
            raise ValueError(f"{field_name} must contain unique IDs")
        by_id[identifier] = value
    return tuple(by_id[key] for key in sorted(by_id))


def _unique_texts(values: Iterable[str]) -> tuple[str, ...]:
    normalized = {_normalized_text(value, "text") for value in values}
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


class FamilyDefinitionKind(str, Enum):
    """Definition identity; hybrids are never flattened into a parent label."""

    REFERENCE = "reference"
    CUSTOM = "custom"
    HYBRID = "hybrid"


class FamilyResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN_FAMILY = "unknown_family"
    UNSUPPORTED_FAMILY = "unsupported_family"
    UNSUPPORTED_VERSION = "unsupported_version"


@dataclass(frozen=True, slots=True)
class FamilyDefinitionRef(_CanonicalRecord):
    """Exact versioned identity for one family architecture definition."""

    SCHEMA_VERSION = "family_definition_ref_v1"

    family_id: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "family_id",
            _normalized_identifier(self.family_id, "family_id"),
        )
        object.__setattr__(
            self,
            "version",
            _normalized_identifier(self.version, "version"),
        )

    @property
    def key(self) -> tuple[str, str]:
        return (self.family_id, self.version)

    @property
    def qualified_name(self) -> str:
        return f"{self.family_id}@{self.version}"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyDefinitionRef:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(family_id=data["family_id"], version=data["version"])


@dataclass(frozen=True, slots=True)
class FamilyPlane(_CanonicalRecord):
    """One ordered, target-linked plane in a family architecture."""

    SCHEMA_VERSION = "family_plane_v1"

    plane_id: str
    order_index: int
    label: str
    structural_function: str
    temporal_window: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "plane_id",
            _normalized_identifier(self.plane_id, "plane_id"),
        )
        object.__setattr__(
            self,
            "order_index",
            _nonnegative_integer(self.order_index, "order_index"),
        )
        for field_name in ("label", "structural_function", "temporal_window"):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyPlane:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            plane_id=data["plane_id"],
            order_index=data["order_index"],
            label=data["label"],
            structural_function=data["structural_function"],
            temporal_window=data["temporal_window"],
        )


@dataclass(frozen=True, slots=True)
class FamilyRecognizer(_CanonicalRecord):
    """Protected family identity condition, not a claim of observed perception."""

    SCHEMA_VERSION = "family_recognizer_v1"

    recognizer_id: str
    label: str
    protected_function: str
    plane_ids: tuple[str, ...]
    absence_failure: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recognizer_id",
            _normalized_identifier(self.recognizer_id, "recognizer_id"),
        )
        for field_name in ("label", "protected_function", "absence_failure"):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )
        plane_ids = tuple(
            sorted(
                {
                    _normalized_identifier(value, "plane_ids")
                    for value in self.plane_ids
                }
            )
        )
        if not plane_ids:
            raise ValueError("plane_ids must not be empty")
        if len(plane_ids) != len(self.plane_ids):
            raise ValueError("plane_ids must contain unique values")
        object.__setattr__(self, "plane_ids", plane_ids)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyRecognizer:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            recognizer_id=data["recognizer_id"],
            label=data["label"],
            protected_function=data["protected_function"],
            plane_ids=tuple(data["plane_ids"]),
            absence_failure=data["absence_failure"],
        )


@dataclass(frozen=True, slots=True)
class ForbiddenFamilyDrift(_CanonicalRecord):
    """One target-conflicting direction the architecture must keep visible."""

    SCHEMA_VERSION = "forbidden_family_drift_v1"

    drift_id: str
    description: str
    conflict_with_target: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "drift_id",
            _normalized_identifier(self.drift_id, "drift_id"),
        )
        for field_name in ("description", "conflict_with_target"):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ForbiddenFamilyDrift:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            drift_id=data["drift_id"],
            description=data["description"],
            conflict_with_target=data["conflict_with_target"],
        )


@dataclass(frozen=True, slots=True)
class FamilyTemporalRelation(_CanonicalRecord):
    """One ordered handoff or transformation between exact declared planes."""

    SCHEMA_VERSION = "family_temporal_relation_v1"

    relation_id: str
    order_index: int
    source_plane_id: str
    destination_plane_id: str
    relation_kind: str
    continuity_requirement: str
    failure_mode: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relation_id",
            _normalized_identifier(self.relation_id, "relation_id"),
        )
        object.__setattr__(
            self,
            "order_index",
            _nonnegative_integer(self.order_index, "order_index"),
        )
        for field_name in (
            "source_plane_id",
            "destination_plane_id",
            "relation_kind",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        if self.source_plane_id == self.destination_plane_id:
            raise ValueError("temporal relations must connect distinct planes")
        for field_name in ("continuity_requirement", "failure_mode"):
            object.__setattr__(
                self,
                field_name,
                _normalized_text(getattr(self, field_name), field_name),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyTemporalRelation:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            relation_id=data["relation_id"],
            order_index=data["order_index"],
            source_plane_id=data["source_plane_id"],
            destination_plane_id=data["destination_plane_id"],
            relation_kind=data["relation_kind"],
            continuity_requirement=data["continuity_requirement"],
            failure_mode=data["failure_mode"],
        )


@dataclass(frozen=True, slots=True)
class FamilyDefinition(_CanonicalRecord):
    """A complete, versioned structural definition for one family identity."""

    SCHEMA_VERSION = "family_definition_v1"

    definition_ref: FamilyDefinitionRef
    label: str
    definition_kind: FamilyDefinitionKind
    component_definitions: tuple[FamilyDefinitionRef, ...]
    architecture_planes: tuple[FamilyPlane, ...]
    protected_recognizers: tuple[FamilyRecognizer, ...]
    forbidden_drift: tuple[ForbiddenFamilyDrift, ...]
    temporal_relations: tuple[FamilyTemporalRelation, ...]
    source_version: str
    definition_evidence_class: EvidenceClass
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.definition_ref, FamilyDefinitionRef):
            raise TypeError("definition_ref must be a FamilyDefinitionRef")
        object.__setattr__(self, "label", _normalized_text(self.label, "label"))
        kind = FamilyDefinitionKind(self.definition_kind)
        object.__setattr__(self, "definition_kind", kind)

        components_by_key: dict[tuple[str, str], FamilyDefinitionRef] = {}
        for component in self.component_definitions:
            if not isinstance(component, FamilyDefinitionRef):
                raise TypeError(
                    "component_definitions must contain FamilyDefinitionRef values"
                )
            if component.key in components_by_key:
                raise ValueError("component_definitions must contain unique values")
            if component == self.definition_ref:
                raise ValueError("a family definition cannot contain itself")
            components_by_key[component.key] = component
        components = tuple(components_by_key[key] for key in sorted(components_by_key))
        if kind is FamilyDefinitionKind.REFERENCE and components:
            raise ValueError("reference definitions cannot declare components")
        if kind is FamilyDefinitionKind.CUSTOM and components:
            raise ValueError("custom definitions cannot silently inherit components")
        if kind is FamilyDefinitionKind.HYBRID and len(components) < 2:
            raise ValueError("hybrid definitions require at least two component definitions")
        object.__setattr__(self, "component_definitions", components)

        planes_by_id: dict[str, FamilyPlane] = {}
        positions: set[int] = set()
        for plane in self.architecture_planes:
            if not isinstance(plane, FamilyPlane):
                raise TypeError("architecture_planes must contain FamilyPlane values")
            if plane.plane_id in planes_by_id:
                raise ValueError("architecture_planes must contain unique plane_id values")
            if plane.order_index in positions:
                raise ValueError("architecture_planes must contain unique order_index values")
            planes_by_id[plane.plane_id] = plane
            positions.add(plane.order_index)
        if not planes_by_id:
            raise ValueError("architecture_planes must not be empty")
        expected_positions = set(range(len(planes_by_id)))
        if positions != expected_positions:
            raise ValueError("architecture plane order_index values must be contiguous from zero")
        planes = tuple(sorted(planes_by_id.values(), key=lambda item: item.order_index))
        object.__setattr__(self, "architecture_planes", planes)

        recognizers = _canonical_by_id(
            self.protected_recognizers,
            record_type=FamilyRecognizer,
            id_attribute="recognizer_id",
            field_name="protected_recognizers",
        )
        if not recognizers:
            raise ValueError("protected_recognizers must not be empty")
        unknown_recognizer_planes = sorted(
            {
                plane_id
                for recognizer in recognizers
                for plane_id in recognizer.plane_ids
                if plane_id not in planes_by_id
            }
        )
        if unknown_recognizer_planes:
            raise ValueError(
                "protected_recognizers reference unknown architecture planes: "
                + ", ".join(unknown_recognizer_planes)
            )
        object.__setattr__(self, "protected_recognizers", recognizers)

        drifts = _canonical_by_id(
            self.forbidden_drift,
            record_type=ForbiddenFamilyDrift,
            id_attribute="drift_id",
            field_name="forbidden_drift",
        )
        if not drifts:
            raise ValueError("forbidden_drift must not be empty")
        object.__setattr__(self, "forbidden_drift", drifts)

        relations_by_id: dict[str, FamilyTemporalRelation] = {}
        relation_positions: set[int] = set()
        unknown_relation_planes: set[str] = set()
        plane_positions = {
            plane.plane_id: plane.order_index for plane in planes_by_id.values()
        }
        for relation in self.temporal_relations:
            if not isinstance(relation, FamilyTemporalRelation):
                raise TypeError(
                    "temporal_relations must contain FamilyTemporalRelation values"
                )
            if relation.relation_id in relations_by_id:
                raise ValueError("temporal_relations must contain unique relation_id values")
            if relation.order_index in relation_positions:
                raise ValueError("temporal_relations must contain unique order_index values")
            relations_by_id[relation.relation_id] = relation
            relation_positions.add(relation.order_index)
            for plane_id in (relation.source_plane_id, relation.destination_plane_id):
                if plane_id not in planes_by_id:
                    unknown_relation_planes.add(plane_id)
        if not relations_by_id:
            raise ValueError("temporal_relations must not be empty")
        if unknown_relation_planes:
            raise ValueError(
                "temporal_relations reference unknown architecture planes: "
                + ", ".join(sorted(unknown_relation_planes))
            )
        backward_relations = sorted(
            relation.relation_id
            for relation in relations_by_id.values()
            if plane_positions[relation.source_plane_id]
            >= plane_positions[relation.destination_plane_id]
        )
        if backward_relations:
            raise ValueError(
                "temporal_relations must move forward across architecture planes: "
                + ", ".join(backward_relations)
            )
        expected_relation_positions = set(range(len(relations_by_id)))
        if relation_positions != expected_relation_positions:
            raise ValueError("temporal relation order_index values must be contiguous from zero")
        relations = tuple(
            sorted(relations_by_id.values(), key=lambda item: item.order_index)
        )
        object.__setattr__(self, "temporal_relations", relations)

        object.__setattr__(
            self,
            "source_version",
            _normalized_text(self.source_version, "source_version"),
        )
        evidence_class = EvidenceClass(self.definition_evidence_class)
        object.__setattr__(self, "definition_evidence_class", evidence_class)
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("family definitions require provenance")
        if evidence_class not in {item.evidence_class for item in provenance}:
            raise ValueError(
                "definition_evidence_class must be represented by definition provenance"
            )
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyDefinition:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            definition_ref=FamilyDefinitionRef.from_dict(data["definition_ref"]),
            label=data["label"],
            definition_kind=FamilyDefinitionKind(data["definition_kind"]),
            component_definitions=tuple(
                FamilyDefinitionRef.from_dict(item)
                for item in data["component_definitions"]
            ),
            architecture_planes=tuple(
                FamilyPlane.from_dict(item) for item in data["architecture_planes"]
            ),
            protected_recognizers=tuple(
                FamilyRecognizer.from_dict(item)
                for item in data["protected_recognizers"]
            ),
            forbidden_drift=tuple(
                ForbiddenFamilyDrift.from_dict(item)
                for item in data["forbidden_drift"]
            ),
            temporal_relations=tuple(
                FamilyTemporalRelation.from_dict(item)
                for item in data["temporal_relations"]
            ),
            source_version=data["source_version"],
            definition_evidence_class=EvidenceClass(
                data["definition_evidence_class"]
            ),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class UnsupportedFamilyDefinition(_CanonicalRecord):
    """An explicit exact-version tombstone; it is not a generic substitute."""

    SCHEMA_VERSION = "unsupported_family_definition_v1"

    definition_ref: FamilyDefinitionRef
    reason: str
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.definition_ref, FamilyDefinitionRef):
            raise TypeError("definition_ref must be a FamilyDefinitionRef")
        object.__setattr__(self, "reason", _normalized_text(self.reason, "reason"))
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("unsupported family records require provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UnsupportedFamilyDefinition:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            definition_ref=FamilyDefinitionRef.from_dict(data["definition_ref"]),
            reason=data["reason"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class FamilyArchitectureRequest(_CanonicalRecord):
    """Exact named target plus a non-substitutive family neighbourhood."""

    SCHEMA_VERSION = "family_architecture_request_v1"

    request_id: str
    target_scope: str
    named_target: str
    requested_definition: FamilyDefinitionRef
    family_neighborhood: tuple[FamilyDefinitionRef, ...]
    temporal_scope: str
    matrix_scope: str
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _normalized_identifier(self.request_id, "request_id"),
        )
        object.__setattr__(
            self,
            "target_scope",
            _normalized_identifier(self.target_scope, "target_scope"),
        )
        object.__setattr__(
            self,
            "named_target",
            _normalized_text(self.named_target, "named_target"),
        )
        if not isinstance(self.requested_definition, FamilyDefinitionRef):
            raise TypeError("requested_definition must be a FamilyDefinitionRef")
        neighborhoods: dict[tuple[str, str], FamilyDefinitionRef] = {}
        for item in self.family_neighborhood:
            if not isinstance(item, FamilyDefinitionRef):
                raise TypeError(
                    "family_neighborhood must contain FamilyDefinitionRef values"
                )
            if item.key in neighborhoods:
                raise ValueError("family_neighborhood must contain unique values")
            neighborhoods[item.key] = item
        object.__setattr__(
            self,
            "family_neighborhood",
            tuple(neighborhoods[key] for key in sorted(neighborhoods)),
        )
        for field_name in ("temporal_scope", "matrix_scope"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("family architecture requests require provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyArchitectureRequest:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            request_id=data["request_id"],
            target_scope=data["target_scope"],
            named_target=data["named_target"],
            requested_definition=FamilyDefinitionRef.from_dict(
                data["requested_definition"]
            ),
            family_neighborhood=tuple(
                FamilyDefinitionRef.from_dict(item)
                for item in data["family_neighborhood"]
            ),
            temporal_scope=data["temporal_scope"],
            matrix_scope=data["matrix_scope"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class FamilyResolution(_CanonicalRecord):
    """Exact catalogue resolution, with every non-structural authority withheld."""

    SCHEMA_VERSION = "family_resolution_v1"

    resolution_id: str
    request: FamilyArchitectureRequest
    status: FamilyResolutionStatus
    definition: FamilyDefinition | None
    named_target: str
    family_neighborhood: tuple[FamilyDefinitionRef, ...]
    reason: str | None
    provenance_refs: tuple[ProvenanceRef, ...]
    ingredient_count_complexity_authority: bool = field(default=False, init=False)
    empirical_smell_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "resolution_id",
            _normalized_identifier(self.resolution_id, "resolution_id"),
        )
        if not isinstance(self.request, FamilyArchitectureRequest):
            raise TypeError("request must be a FamilyArchitectureRequest")
        status = FamilyResolutionStatus(self.status)
        object.__setattr__(self, "status", status)
        if self.definition is not None and not isinstance(self.definition, FamilyDefinition):
            raise TypeError("definition must be a FamilyDefinition or None")
        if status is FamilyResolutionStatus.RESOLVED:
            if self.definition is None:
                raise ValueError("resolved family architecture requires a definition")
            if self.definition.definition_ref != self.request.requested_definition:
                raise ValueError("resolved definition must exactly match requested_definition")
            if self.reason is not None:
                raise ValueError("resolved family architecture cannot declare a failure reason")
        else:
            if self.definition is not None:
                raise ValueError("unresolved family architecture cannot carry a definition")
            if self.reason is None:
                raise ValueError("unresolved family architecture requires a reason")
        named_target = _normalized_text(self.named_target, "named_target")
        if named_target != self.request.named_target:
            raise ValueError("named_target must exactly match the request")
        object.__setattr__(self, "named_target", named_target)
        neighborhoods = tuple(self.family_neighborhood)
        if neighborhoods != self.request.family_neighborhood:
            raise ValueError("family_neighborhood must exactly match the request")
        object.__setattr__(self, "family_neighborhood", neighborhoods)
        if self.reason is not None:
            object.__setattr__(self, "reason", _normalized_text(self.reason, "reason"))
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("family resolution requires provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @property
    def authority_ceiling(self) -> AuthorityCeiling:
        if self.status is FamilyResolutionStatus.RESOLVED:
            return AuthorityCeiling.STRUCTURAL_ONLY
        return AuthorityCeiling.WITHHELD

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyResolution:
        data = _payload(payload, cls.SCHEMA_VERSION)
        _false_authority_payload(data)
        definition_payload = data["definition"]
        return cls(
            resolution_id=data["resolution_id"],
            request=FamilyArchitectureRequest.from_dict(data["request"]),
            status=FamilyResolutionStatus(data["status"]),
            definition=(
                None
                if definition_payload is None
                else FamilyDefinition.from_dict(definition_payload)
            ),
            named_target=data["named_target"],
            family_neighborhood=tuple(
                FamilyDefinitionRef.from_dict(item)
                for item in data["family_neighborhood"]
            ),
            reason=data["reason"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


@dataclass(frozen=True, slots=True)
class FamilyArchitectureCatalog(_CanonicalRecord):
    """Exact-definition catalogue with explicit unsupported tombstones."""

    SCHEMA_VERSION = "family_architecture_catalog_v1"

    catalog_id: str
    definitions: tuple[FamilyDefinition, ...]
    unsupported_definitions: tuple[UnsupportedFamilyDefinition, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "catalog_id",
            _normalized_identifier(self.catalog_id, "catalog_id"),
        )
        definitions_by_key: dict[tuple[str, str], FamilyDefinition] = {}
        for definition in self.definitions:
            if not isinstance(definition, FamilyDefinition):
                raise TypeError("definitions must contain FamilyDefinition values")
            key = definition.definition_ref.key
            if key in definitions_by_key:
                raise ValueError("definitions must contain unique definition refs")
            definitions_by_key[key] = definition
        unsupported_by_key: dict[tuple[str, str], UnsupportedFamilyDefinition] = {}
        for unsupported in self.unsupported_definitions:
            if not isinstance(unsupported, UnsupportedFamilyDefinition):
                raise TypeError(
                    "unsupported_definitions must contain UnsupportedFamilyDefinition values"
                )
            key = unsupported.definition_ref.key
            if key in unsupported_by_key:
                raise ValueError(
                    "unsupported_definitions must contain unique definition refs"
                )
            if key in definitions_by_key:
                raise ValueError(
                    "one exact definition cannot be both supported and unsupported"
                )
            unsupported_by_key[key] = unsupported

        missing_components = sorted(
            {
                component.qualified_name
                for definition in definitions_by_key.values()
                for component in definition.component_definitions
                if component.key not in definitions_by_key
            }
        )
        if missing_components:
            raise ValueError(
                "hybrid definitions have missing component definitions: "
                + ", ".join(missing_components)
            )

        visit_state: dict[tuple[str, str], int] = {}

        def visit(definition_key: tuple[str, str]) -> None:
            state = visit_state.get(definition_key, 0)
            if state == 1:
                raise ValueError("cyclic hybrid component definitions are not allowed")
            if state == 2:
                return
            visit_state[definition_key] = 1
            definition = definitions_by_key[definition_key]
            for component in definition.component_definitions:
                visit(component.key)
            visit_state[definition_key] = 2

        for definition_key in sorted(definitions_by_key):
            visit(definition_key)
        object.__setattr__(
            self,
            "definitions",
            tuple(definitions_by_key[key] for key in sorted(definitions_by_key)),
        )
        object.__setattr__(
            self,
            "unsupported_definitions",
            tuple(unsupported_by_key[key] for key in sorted(unsupported_by_key)),
        )

    def resolve(self, request: FamilyArchitectureRequest) -> FamilyResolution:
        if not isinstance(request, FamilyArchitectureRequest):
            raise TypeError("request must be a FamilyArchitectureRequest")
        definitions = {item.definition_ref.key: item for item in self.definitions}
        unsupported = {
            item.definition_ref.key: item for item in self.unsupported_definitions
        }
        requested_key = request.requested_definition.key
        definition = definitions.get(requested_key)
        tombstone = unsupported.get(requested_key)
        provenance: tuple[ProvenanceRef, ...] = request.provenance_refs
        reason: str | None
        if definition is not None:
            status = FamilyResolutionStatus.RESOLVED
            reason = None
            provenance = _merged_provenance(
                (*provenance, *definition.provenance_refs)
            )
        elif tombstone is not None:
            status = FamilyResolutionStatus.UNSUPPORTED_FAMILY
            reason = tombstone.reason
            provenance = _merged_provenance(
                (*provenance, *tombstone.provenance_refs)
            )
        else:
            matching_definitions = tuple(
                item
                for item in self.definitions
                if item.definition_ref.family_id
                == request.requested_definition.family_id
            )
            matching_tombstones = tuple(
                item
                for item in self.unsupported_definitions
                if item.definition_ref.family_id
                == request.requested_definition.family_id
            )
            if matching_definitions or matching_tombstones:
                status = FamilyResolutionStatus.UNSUPPORTED_VERSION
                available_versions = sorted(
                    [
                        *(item.definition_ref.version for item in matching_definitions),
                        *(item.definition_ref.version for item in matching_tombstones),
                    ]
                )
                available = ", ".join(available_versions)
                reason = (
                    "The exact requested family version is unsupported; available "
                    f"versions are {available}. No version fallback was applied."
                )
                provenance = _merged_provenance(
                    (
                        *provenance,
                        *(
                            ref
                            for item in matching_definitions
                            for ref in item.provenance_refs
                        ),
                        *(
                            ref
                            for item in matching_tombstones
                            for ref in item.provenance_refs
                        ),
                    )
                )
            else:
                status = FamilyResolutionStatus.UNKNOWN_FAMILY
                reason = (
                    "The requested family identity is unknown to this catalogue. "
                    "No generic-family fallback was applied."
                )
        resolution_payload = {
            "catalog_id": self.catalog_id,
            "catalog_sha256": self.content_sha256,
            "request_sha256": request.content_sha256,
            "status": status.value,
        }
        return FamilyResolution(
            resolution_id=_stable_id("family-resolution", resolution_payload),
            request=request,
            status=status,
            definition=definition,
            named_target=request.named_target,
            family_neighborhood=request.family_neighborhood,
            reason=reason,
            provenance_refs=provenance,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FamilyArchitectureCatalog:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            catalog_id=data["catalog_id"],
            definitions=tuple(
                FamilyDefinition.from_dict(item) for item in data["definitions"]
            ),
            unsupported_definitions=tuple(
                UnsupportedFamilyDefinition.from_dict(item)
                for item in data["unsupported_definitions"]
            ),
        )


@dataclass(frozen=True, slots=True)
class FamilyArchitectureAdapter:
    """Deterministically project a family resolution onto the identity plane."""

    resolution: FamilyResolution

    def __post_init__(self) -> None:
        if not isinstance(self.resolution, FamilyResolution):
            raise TypeError("resolution must be a FamilyResolution")

    def to_plane_assessment(self) -> PlaneAssessment:
        resolution = self.resolution
        request = resolution.request
        provenance = resolution.provenance_refs
        authority = resolution.authority_ceiling
        claims: list[ScopedClaim] = []

        def add_claim(
            claim_key: str,
            claim_value: str,
            claim_kind: ClaimKind,
            *,
            cardinality: ClaimCardinality = ClaimCardinality.SINGLE,
            member_id: str | None = None,
            order_index: int | None = None,
        ) -> None:
            identity = {
                "key": claim_key,
                "value": claim_value,
                "cardinality": cardinality.value,
                "member_id": member_id,
                "order_index": order_index,
            }
            claims.append(
                ScopedClaim(
                    claim_id=_stable_id("family-claim", identity),
                    claim_key=claim_key,
                    claim_value=claim_value,
                    claim_kind=claim_kind,
                    authority_ceiling=authority,
                    provenance_refs=provenance,
                    cardinality=cardinality,
                    member_id=member_id,
                    order_index=order_index,
                )
            )

        add_claim("family.named_target", request.named_target, ClaimKind.REQUIREMENT)
        add_claim(
            "family.requested_definition",
            request.requested_definition.qualified_name,
            ClaimKind.REQUIREMENT,
        )
        for neighborhood in request.family_neighborhood:
            add_claim(
                "family.neighborhood",
                neighborhood.qualified_name,
                ClaimKind.HYPOTHESIS,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=(
                    "family-neighborhood-"
                    f"{_slug(neighborhood.family_id)}-{_slug(neighborhood.version)}"
                ),
            )

        definition = resolution.definition
        if definition is not None:
            add_claim(
                "family.definition_kind",
                definition.definition_kind.value,
                ClaimKind.DIAGNOSTIC,
            )
            add_claim(
                "family.source_version",
                definition.source_version,
                ClaimKind.DIAGNOSTIC,
            )
            add_claim(
                "family.definition_evidence_class",
                definition.definition_evidence_class.value,
                ClaimKind.DIAGNOSTIC,
            )
            for component in definition.component_definitions:
                add_claim(
                    "family.component_definition",
                    component.qualified_name,
                    ClaimKind.REQUIREMENT,
                    cardinality=ClaimCardinality.SET_MEMBER,
                    member_id=(
                        "family-component-"
                        f"{_slug(component.family_id)}-{_slug(component.version)}"
                    ),
                )
            for plane in definition.architecture_planes:
                add_claim(
                    "family.architecture_plane",
                    (
                        f"{plane.label}; function={plane.structural_function}; "
                        f"window={plane.temporal_window}"
                    ),
                    ClaimKind.REQUIREMENT,
                    cardinality=ClaimCardinality.ORDERED_MEMBER,
                    member_id=f"family-plane-{_slug(plane.plane_id)}",
                    order_index=plane.order_index,
                )
            for recognizer in definition.protected_recognizers:
                add_claim(
                    "family.protected_recognizer",
                    (
                        f"{recognizer.label}; function={recognizer.protected_function}; "
                        f"planes={','.join(recognizer.plane_ids)}; "
                        f"absence={recognizer.absence_failure}"
                    ),
                    ClaimKind.REQUIREMENT,
                    cardinality=ClaimCardinality.SET_MEMBER,
                    member_id=f"family-recognizer-{_slug(recognizer.recognizer_id)}",
                )
            for drift in definition.forbidden_drift:
                add_claim(
                    "family.forbidden_drift",
                    f"{drift.description}; conflict={drift.conflict_with_target}",
                    ClaimKind.PROHIBITION,
                    cardinality=ClaimCardinality.SET_MEMBER,
                    member_id=f"family-drift-{_slug(drift.drift_id)}",
                )
            for relation in definition.temporal_relations:
                add_claim(
                    "family.temporal_relation",
                    (
                        f"{relation.source_plane_id}->{relation.destination_plane_id}; "
                        f"kind={relation.relation_kind}; "
                        f"continuity={relation.continuity_requirement}; "
                        f"failure={relation.failure_mode}"
                    ),
                    ClaimKind.HYPOTHESIS,
                    cardinality=ClaimCardinality.ORDERED_MEMBER,
                    member_id=f"family-relation-{_slug(relation.relation_id)}",
                    order_index=relation.order_index,
                )

        unknown_specs = [
            (
                "observed_smell",
                "A structural family definition cannot establish observed smell.",
                "Direct sensory observation of the exact subject and conditions.",
            ),
            (
                "target_fidelity",
                "Definition conformance cannot establish named-target similarity.",
                "A scoped blinded comparison against the named target.",
            ),
            (
                "liking",
                "No participant-linked liking evidence is present.",
                "Participant-linked criterion-specific hedonic observations.",
            ),
            (
                "physical_performance",
                "Structural relations are not measured physical performance.",
                "Condition-bound physical performance measurements.",
            ),
            (
                "safety",
                "A family architecture is not an exact-formula safety assessment.",
                "Current jurisdiction- and formula-specific safety review.",
            ),
            (
                "stability",
                "A family architecture has no stability authority.",
                "Condition-bound stability observations for the exact build.",
            ),
            (
                "release",
                "No family definition grants release authority.",
                "All independently required release evidence and acceptance.",
            ),
        ]
        if resolution.status is not FamilyResolutionStatus.RESOLVED:
            unknown_specs.insert(
                0,
                (
                    "family_definition",
                    resolution.reason or "The exact family definition is unresolved.",
                    "An admitted exact-version family definition or explicit adjudication.",
                ),
            )
        unknowns = tuple(
            UnknownFact(
                unknown_id=_stable_id(
                    "family-unknown",
                    {
                        "resolution_id": resolution.resolution_id,
                        "field_key": field_key,
                    },
                ),
                field_key=field_key,
                reason=reason,
                needed_evidence=needed_evidence,
                provenance_refs=provenance,
            )
            for field_key, reason, needed_evidence in unknown_specs
        )
        failure_mode_values = [
            (
                "A family-neighbourhood label is substituted for the exact named target "
                "or requested definition."
            ),
            "Ingredient count is mistaken for target-linked architectural complexity.",
            "A structural definition is promoted into empirical sensory or release authority.",
        ]
        if definition is not None:
            failure_mode_values.extend(
                item.absence_failure for item in definition.protected_recognizers
            )
            failure_mode_values.extend(
                item.conflict_with_target for item in definition.forbidden_drift
            )
            failure_mode_values.extend(
                item.failure_mode for item in definition.temporal_relations
            )
        failure_modes = _unique_texts(failure_mode_values)
        proposed_experiments = (
            "Run a blinded target-specific recognizer comparison at declared temporal windows.",
            "Run a controlled forbidden-drift challenge against the exact named target.",
        )
        freshness_hashes = {
            request.content_sha256,
            resolution.content_sha256,
            *(item.source_sha256 for item in provenance if item.source_sha256 is not None),
        }
        return PlaneAssessment(
            assessment_id=_stable_id(
                "family-assessment",
                {
                    "resolution_id": resolution.resolution_id,
                    "resolution_sha256": resolution.content_sha256,
                },
            ),
            module_id=_MODULE_ID,
            plane_id=PlaneId.IDENTITY,
            scope=AssessmentScope(
                target_scope=request.target_scope,
                temporal_scope=request.temporal_scope,
                matrix_scope=request.matrix_scope,
            ),
            claims=tuple(claims),
            support_intervals=(),
            conflicts=(),
            unknowns=unknowns,
            failure_modes=failure_modes,
            proposed_experiments=proposed_experiments,
            provenance_refs=provenance,
            authority_ceiling=authority,
            freshness_hashes=tuple(sorted(freshness_hashes)),
            native_criteria=(),
        )


__all__ = [
    "FamilyArchitectureAdapter",
    "FamilyArchitectureCatalog",
    "FamilyArchitectureRequest",
    "FamilyDefinition",
    "FamilyDefinitionKind",
    "FamilyDefinitionRef",
    "FamilyPlane",
    "FamilyRecognizer",
    "FamilyResolution",
    "FamilyResolutionStatus",
    "FamilyTemporalRelation",
    "ForbiddenFamilyDrift",
    "UnsupportedFamilyDefinition",
]
