"""Hash-bound structural capability ontology for formulation intelligence.

The ontology describes software responsibilities and gaps.  Its declarations
are heuristic, its authority is structural-only, and its coverage states say
only whether exact code interfaces have been declared.  They are never proof of
smell, liking, performance, safety, stability, physical execution, or release.
No scalar score is produced because coverage in one architectural plane cannot
compensate for a missing or contradictory plane.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, cast

from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    EvidenceClass,
    PlaneId,
    ProvenanceRef,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


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
    identifiers: bool = False,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name, identifier=identifiers) for value in values)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _digest(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).casefold()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be boolean")
    return value


def _sequence(value: object, field_name: str) -> tuple[Any, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a sequence")
    return tuple(value)


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _OntologyRecord):
        return value.as_dict()
    if isinstance(value, ProvenanceRef):
        return value.as_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
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


class _OntologyRecord:
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


def _canonical_provenance(
    values: Iterable[ProvenanceRef],
    *,
    field_name: str = "provenance_refs",
) -> tuple[ProvenanceRef, ...]:
    by_id: dict[str, ProvenanceRef] = {}
    for value in values:
        if not isinstance(value, ProvenanceRef):
            raise TypeError(f"{field_name} must contain ProvenanceRef values")
        current = by_id.get(value.provenance_id)
        if current is not None and current != value:
            raise ValueError(f"provenance_id {value.provenance_id!r} is ambiguous")
        by_id[value.provenance_id] = value
    result = tuple(by_id[key] for key in sorted(by_id))
    if not result:
        raise ValueError(f"{field_name} must not be empty")
    if any(item.source_sha256 is None for item in result):
        raise ValueError(f"{field_name} must be bound to exact source SHA-256 values")
    if any(item.evidence_class is not EvidenceClass.HEURISTIC for item in result):
        raise ValueError("ontology and support declarations must remain HEURISTIC")
    return result


class ScopeMode(str, Enum):
    ALL = "all"
    EXPLICIT = "explicit"
    NOT_APPLICABLE = "not_applicable"


class CapabilityState(str, Enum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    MISSING = "missing"


class CapabilityGapKind(str, Enum):
    MISSING_SUPPORT = "missing_support"
    PARTIAL_SUPPORT = "partial_support"
    UNSATISFIED_PREREQUISITE = "unsatisfied_prerequisite"
    UNMET_EVIDENCE_NEED = "unmet_evidence_need"
    INCOMPATIBLE_ACTIVE_CAPABILITIES = "incompatible_active_capabilities"


@dataclass(frozen=True, slots=True)
class CapabilityApplicability(_OntologyRecord):
    """Open or explicit family and floral-subtype namespaces."""

    SCHEMA_VERSION = "capability_applicability_v1"

    family_mode: ScopeMode
    family_ids: tuple[str, ...]
    accepts_new_family_ids: bool
    floral_mode: ScopeMode
    floral_subtype_ids: tuple[str, ...]
    accepts_new_floral_subtype_ids: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "family_mode", ScopeMode(self.family_mode))
        object.__setattr__(
            self,
            "family_ids",
            _text_tuple(self.family_ids, "family_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "accepts_new_family_ids",
            _bool(self.accepts_new_family_ids, "accepts_new_family_ids"),
        )
        object.__setattr__(self, "floral_mode", ScopeMode(self.floral_mode))
        object.__setattr__(
            self,
            "floral_subtype_ids",
            _text_tuple(
                self.floral_subtype_ids,
                "floral_subtype_ids",
                identifiers=True,
            ),
        )
        object.__setattr__(
            self,
            "accepts_new_floral_subtype_ids",
            _bool(
                self.accepts_new_floral_subtype_ids,
                "accepts_new_floral_subtype_ids",
            ),
        )
        self._validate_axis(
            "family",
            self.family_mode,
            self.family_ids,
            self.accepts_new_family_ids,
        )
        self._validate_axis(
            "floral",
            self.floral_mode,
            self.floral_subtype_ids,
            self.accepts_new_floral_subtype_ids,
        )

    @staticmethod
    def _validate_axis(
        axis: str,
        mode: ScopeMode,
        identifiers: tuple[str, ...],
        accepts_new: bool,
    ) -> None:
        if mode is ScopeMode.ALL:
            if identifiers:
                raise ValueError(f"{axis} ALL scope must not enumerate identifiers")
            if not accepts_new:
                raise ValueError(f"{axis} ALL scope must accept new identifiers")
        elif mode is ScopeMode.EXPLICIT:
            if not identifiers:
                raise ValueError(f"{axis} EXPLICIT scope requires identifiers")
        elif identifiers or accepts_new:
            raise ValueError(f"{axis} NOT_APPLICABLE scope cannot enumerate or accept identifiers")

    @classmethod
    def all_extensible(cls) -> CapabilityApplicability:
        return cls(
            family_mode=ScopeMode.ALL,
            family_ids=(),
            accepts_new_family_ids=True,
            floral_mode=ScopeMode.ALL,
            floral_subtype_ids=(),
            accepts_new_floral_subtype_ids=True,
        )

    @staticmethod
    def _axis_applies(
        value: str | None,
        mode: ScopeMode,
        identifiers: tuple[str, ...],
        accepts_new: bool,
    ) -> bool:
        if value is None:
            return True
        normalized = _text(value, "scope identifier", identifier=True)
        if mode is ScopeMode.NOT_APPLICABLE:
            return False
        if mode is ScopeMode.ALL:
            return True
        return normalized in identifiers or accepts_new

    def applies_to(
        self,
        *,
        family_id: str | None = None,
        floral_subtype_id: str | None = None,
    ) -> bool:
        return self._axis_applies(
            family_id,
            self.family_mode,
            self.family_ids,
            self.accepts_new_family_ids,
        ) and self._axis_applies(
            floral_subtype_id,
            self.floral_mode,
            self.floral_subtype_ids,
            self.accepts_new_floral_subtype_ids,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityApplicability:
        data = cls._payload(payload)
        return cls(
            family_mode=ScopeMode(data["family_mode"]),
            family_ids=tuple(_sequence(data["family_ids"], "family_ids")),
            accepts_new_family_ids=data["accepts_new_family_ids"],
            floral_mode=ScopeMode(data["floral_mode"]),
            floral_subtype_ids=tuple(_sequence(data["floral_subtype_ids"], "floral_subtype_ids")),
            accepts_new_floral_subtype_ids=data["accepts_new_floral_subtype_ids"],
        )


@dataclass(frozen=True, slots=True)
class EvidenceNeed(_OntologyRecord):
    """Evidence interface the capability must preserve, not evidence observed."""

    SCHEMA_VERSION = "capability_evidence_need_v1"

    evidence_need_id: str
    description: str
    acceptable_evidence_classes: tuple[EvidenceClass, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_need_id",
            _text(self.evidence_need_id, "evidence_need_id", identifier=True),
        )
        object.__setattr__(self, "description", _text(self.description, "description"))
        classes = tuple(EvidenceClass(item) for item in self.acceptable_evidence_classes)
        if not classes:
            raise ValueError("acceptable_evidence_classes must not be empty")
        if len(classes) != len(set(classes)):
            raise ValueError("acceptable_evidence_classes must contain unique values")
        object.__setattr__(
            self,
            "acceptable_evidence_classes",
            tuple(sorted(classes, key=lambda item: item.value)),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EvidenceNeed:
        data = cls._payload(payload)
        return cls(
            evidence_need_id=data["evidence_need_id"],
            description=data["description"],
            acceptable_evidence_classes=tuple(
                EvidenceClass(item)
                for item in _sequence(
                    data["acceptable_evidence_classes"],
                    "acceptable_evidence_classes",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityDefinition(_OntologyRecord):
    SCHEMA_VERSION = "perfumery_capability_definition_v1"

    capability_id: str
    title: str
    plane_id: PlaneId
    structural_role: str
    applicability: CapabilityApplicability
    prerequisite_capability_ids: tuple[str, ...]
    evidence_needs: tuple[EvidenceNeed, ...]
    incompatible_capability_ids: tuple[str, ...]
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability_id",
            _text(self.capability_id, "capability_id", identifier=True),
        )
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        object.__setattr__(
            self,
            "structural_role",
            _text(self.structural_role, "structural_role"),
        )
        if not isinstance(self.applicability, CapabilityApplicability):
            raise TypeError("applicability must be CapabilityApplicability")
        prerequisites = _text_tuple(
            self.prerequisite_capability_ids,
            "prerequisite_capability_ids",
            identifiers=True,
        )
        incompatibilities = _text_tuple(
            self.incompatible_capability_ids,
            "incompatible_capability_ids",
            identifiers=True,
        )
        if self.capability_id in prerequisites:
            raise ValueError("capability cannot require itself")
        if self.capability_id in incompatibilities:
            raise ValueError("capability cannot be incompatible with itself")
        object.__setattr__(self, "prerequisite_capability_ids", prerequisites)
        object.__setattr__(self, "incompatible_capability_ids", incompatibilities)

        needs_by_id: dict[str, EvidenceNeed] = {}
        for need in self.evidence_needs:
            if not isinstance(need, EvidenceNeed):
                raise TypeError("evidence_needs must contain EvidenceNeed values")
            if need.evidence_need_id in needs_by_id:
                raise ValueError("evidence_need_id values must be unique")
            needs_by_id[need.evidence_need_id] = need
        if not needs_by_id:
            raise ValueError("evidence_needs must not be empty")
        object.__setattr__(
            self,
            "evidence_needs",
            tuple(needs_by_id[key] for key in sorted(needs_by_id)),
        )
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("capability authority cannot exceed STRUCTURAL_ONLY")
        object.__setattr__(self, "authority_ceiling", ceiling)
        object.__setattr__(
            self,
            "provenance_refs",
            _canonical_provenance(self.provenance_refs),
        )

    @property
    def evidence_need_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_need_id for item in self.evidence_needs)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityDefinition:
        data = cls._payload(payload)
        return cls(
            capability_id=data["capability_id"],
            title=data["title"],
            plane_id=PlaneId(data["plane_id"]),
            structural_role=data["structural_role"],
            applicability=CapabilityApplicability.from_dict(data["applicability"]),
            prerequisite_capability_ids=tuple(
                _sequence(
                    data["prerequisite_capability_ids"],
                    "prerequisite_capability_ids",
                )
            ),
            evidence_needs=tuple(
                EvidenceNeed.from_dict(item)
                for item in _sequence(data["evidence_needs"], "evidence_needs")
            ),
            incompatible_capability_ids=tuple(
                _sequence(
                    data["incompatible_capability_ids"],
                    "incompatible_capability_ids",
                )
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilitySupport(_OntologyRecord):
    """Exact-module declaration of code support, not empirical validation."""

    SCHEMA_VERSION = "capability_module_support_v1"

    support_id: str
    capability_id: str
    module_id: str
    module_path: str
    state: CapabilityState
    interface_ids: tuple[str, ...]
    required_evidence_need_ids: tuple[str, ...]
    covered_evidence_need_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    module_source_sha256: str | None
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        for field_name in ("support_id", "capability_id", "module_id"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name, identifier=True),
            )
        object.__setattr__(
            self,
            "module_path",
            _text(self.module_path, "module_path"),
        )
        state = CapabilityState(self.state)
        object.__setattr__(self, "state", state)
        interfaces = _text_tuple(
            self.interface_ids,
            "interface_ids",
            identifiers=True,
        )
        required = _text_tuple(
            self.required_evidence_need_ids,
            "required_evidence_need_ids",
            identifiers=True,
            allow_empty=False,
        )
        covered = _text_tuple(
            self.covered_evidence_need_ids,
            "covered_evidence_need_ids",
            identifiers=True,
        )
        if not set(covered).issubset(required):
            raise ValueError("covered evidence needs must be a subset of required needs")
        limitations = _text_tuple(self.limitations, "limitations")
        object.__setattr__(self, "interface_ids", interfaces)
        object.__setattr__(self, "required_evidence_need_ids", required)
        object.__setattr__(self, "covered_evidence_need_ids", covered)
        object.__setattr__(self, "limitations", limitations)

        if state is CapabilityState.MISSING:
            if interfaces or covered or self.module_source_sha256 is not None:
                raise ValueError(
                    "missing support cannot declare interfaces, covered evidence, or source"
                )
        else:
            if not interfaces:
                raise ValueError("implemented or partial support requires interfaces")
            if self.module_source_sha256 is None:
                raise ValueError("implemented or partial support requires module source SHA-256")
            object.__setattr__(
                self,
                "module_source_sha256",
                _digest(self.module_source_sha256, "module_source_sha256"),
            )
        if state is CapabilityState.IMPLEMENTED and covered != required:
            raise ValueError("implemented support must satisfy every declared evidence need")

        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("support authority cannot exceed STRUCTURAL_ONLY")
        object.__setattr__(self, "authority_ceiling", ceiling)
        provenance = _canonical_provenance(self.provenance_refs)
        if self.module_source_sha256 is not None and not any(
            item.source_sha256 == self.module_source_sha256 for item in provenance
        ):
            raise ValueError("support provenance must bind the exact module source SHA-256")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilitySupport:
        data = cls._payload(payload)
        return cls(
            support_id=data["support_id"],
            capability_id=data["capability_id"],
            module_id=data["module_id"],
            module_path=data["module_path"],
            state=CapabilityState(data["state"]),
            interface_ids=tuple(_sequence(data["interface_ids"], "interface_ids")),
            required_evidence_need_ids=tuple(
                _sequence(
                    data["required_evidence_need_ids"],
                    "required_evidence_need_ids",
                )
            ),
            covered_evidence_need_ids=tuple(
                _sequence(
                    data["covered_evidence_need_ids"],
                    "covered_evidence_need_ids",
                )
            ),
            limitations=tuple(_sequence(data["limitations"], "limitations")),
            module_source_sha256=data["module_source_sha256"],
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
        )


def _validate_acyclic(definitions: Mapping[str, CapabilityDefinition]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(capability_id: str, path: tuple[str, ...]) -> None:
        if capability_id in visiting:
            cycle = " -> ".join((*path, capability_id))
            raise ValueError(f"prerequisite cycle detected: {cycle}")
        if capability_id in visited:
            return
        visiting.add(capability_id)
        for prerequisite in definitions[capability_id].prerequisite_capability_ids:
            visit(prerequisite, (*path, capability_id))
        visiting.remove(capability_id)
        visited.add(capability_id)

    for capability_id in sorted(definitions):
        visit(capability_id, ())


@dataclass(frozen=True, slots=True)
class CapabilityOntology(_OntologyRecord):
    SCHEMA_VERSION = "capability_ontology_v1"

    ontology_id: str
    semantic_version: str
    capabilities: tuple[CapabilityDefinition, ...]
    module_support: tuple[CapabilitySupport, ...]
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "ontology_id",
            _text(self.ontology_id, "ontology_id", identifier=True),
        )
        version = _text(self.semantic_version, "semantic_version")
        if not _SEMVER_RE.fullmatch(version):
            raise ValueError("semantic_version must be MAJOR.MINOR.PATCH")
        object.__setattr__(self, "semantic_version", version)

        by_id: dict[str, CapabilityDefinition] = {}
        all_need_ids: set[str] = set()
        for definition in self.capabilities:
            if not isinstance(definition, CapabilityDefinition):
                raise TypeError("capabilities must contain CapabilityDefinition values")
            if definition.capability_id in by_id:
                raise ValueError("capability_id values must be unique")
            overlap = all_need_ids.intersection(definition.evidence_need_ids)
            if overlap:
                raise ValueError(f"evidence_need_id values must be globally unique: {overlap!r}")
            all_need_ids.update(definition.evidence_need_ids)
            by_id[definition.capability_id] = definition
        if not by_id:
            raise ValueError("capabilities must not be empty")

        for definition in by_id.values():
            unknown_prerequisites = set(definition.prerequisite_capability_ids).difference(by_id)
            if unknown_prerequisites:
                raise ValueError(
                    f"unknown prerequisite capability IDs: {sorted(unknown_prerequisites)!r}"
                )
            unknown_incompatibilities = set(definition.incompatible_capability_ids).difference(
                by_id
            )
            if unknown_incompatibilities:
                raise ValueError(
                    f"unknown incompatible capability IDs: {sorted(unknown_incompatibilities)!r}"
                )
            for incompatible_id in definition.incompatible_capability_ids:
                if (
                    definition.capability_id
                    not in by_id[incompatible_id].incompatible_capability_ids
                ):
                    raise ValueError("capability incompatibilities must be symmetric")
        _validate_acyclic(by_id)
        object.__setattr__(
            self,
            "capabilities",
            tuple(by_id[key] for key in sorted(by_id)),
        )

        support_by_id: dict[str, CapabilitySupport] = {}
        module_capability_pairs: set[tuple[str, str]] = set()
        for support in self.module_support:
            if not isinstance(support, CapabilitySupport):
                raise TypeError("module_support must contain CapabilitySupport values")
            if support.support_id in support_by_id:
                raise ValueError("support_id values must be unique")
            pair = (support.module_id, support.capability_id)
            if pair in module_capability_pairs:
                raise ValueError("one module may declare a capability only once")
            if support.capability_id not in by_id:
                raise ValueError(f"support references unknown capability {support.capability_id!r}")
            definition = by_id[support.capability_id]
            if support.required_evidence_need_ids != definition.evidence_need_ids:
                raise ValueError(
                    "support required evidence needs must exactly match its capability"
                )
            if not support.authority_ceiling.is_no_stronger_than(definition.authority_ceiling):
                raise ValueError("support authority cannot exceed capability authority")
            support_by_id[support.support_id] = support
            module_capability_pairs.add(pair)
        object.__setattr__(
            self,
            "module_support",
            tuple(support_by_id[key] for key in sorted(support_by_id)),
        )

        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("ontology authority cannot exceed STRUCTURAL_ONLY")
        if any(
            not definition.authority_ceiling.is_no_stronger_than(ceiling)
            for definition in by_id.values()
        ):
            raise ValueError("capability authority cannot exceed ontology authority")
        object.__setattr__(self, "authority_ceiling", ceiling)
        object.__setattr__(
            self,
            "provenance_refs",
            _canonical_provenance(self.provenance_refs),
        )

    def capability(self, capability_id: str) -> CapabilityDefinition:
        normalized = _text(capability_id, "capability_id", identifier=True)
        for definition in self.capabilities:
            if definition.capability_id == normalized:
                return definition
        raise KeyError(normalized)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityOntology:
        data = cls._payload(payload)
        return cls(
            ontology_id=data["ontology_id"],
            semantic_version=data["semantic_version"],
            capabilities=tuple(
                CapabilityDefinition.from_dict(item)
                for item in _sequence(data["capabilities"], "capabilities")
            ),
            module_support=tuple(
                CapabilitySupport.from_dict(item)
                for item in _sequence(data["module_support"], "module_support")
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityGap(_OntologyRecord):
    SCHEMA_VERSION = "capability_gap_v1"

    gap_id: str
    capability_id: str
    kind: CapabilityGapKind
    state: CapabilityState
    module_ids: tuple[str, ...]
    related_capability_ids: tuple[str, ...]
    evidence_need_ids: tuple[str, ...]
    detail: str
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        for field_name in ("gap_id", "capability_id"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name, identifier=True),
            )
        object.__setattr__(self, "kind", CapabilityGapKind(self.kind))
        object.__setattr__(self, "state", CapabilityState(self.state))
        for field_name in (
            "module_ids",
            "related_capability_ids",
            "evidence_need_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name, identifiers=True),
            )
        object.__setattr__(self, "detail", _text(self.detail, "detail"))
        object.__setattr__(
            self,
            "provenance_refs",
            _canonical_provenance(self.provenance_refs),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityGap:
        data = cls._payload(payload)
        return cls(
            gap_id=data["gap_id"],
            capability_id=data["capability_id"],
            kind=CapabilityGapKind(data["kind"]),
            state=CapabilityState(data["state"]),
            module_ids=tuple(_sequence(data["module_ids"], "module_ids")),
            related_capability_ids=tuple(
                _sequence(
                    data["related_capability_ids"],
                    "related_capability_ids",
                )
            ),
            evidence_need_ids=tuple(_sequence(data["evidence_need_ids"], "evidence_need_ids")),
            detail=data["detail"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityCoverage(_OntologyRecord):
    SCHEMA_VERSION = "capability_coverage_v1"

    capability_id: str
    plane_id: PlaneId
    state: CapabilityState
    implemented_module_ids: tuple[str, ...]
    partial_module_ids: tuple[str, ...]
    missing_module_ids: tuple[str, ...]
    authority_ceiling: AuthorityCeiling
    gaps: tuple[CapabilityGap, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability_id",
            _text(self.capability_id, "capability_id", identifier=True),
        )
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        object.__setattr__(self, "state", CapabilityState(self.state))
        for field_name in (
            "implemented_module_ids",
            "partial_module_ids",
            "missing_module_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name, identifiers=True),
            )
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("coverage authority cannot exceed STRUCTURAL_ONLY")
        object.__setattr__(self, "authority_ceiling", ceiling)
        gaps = tuple(
            sorted(
                self.gaps,
                key=lambda item: (item.kind.value, item.gap_id),
            )
        )
        if any(item.capability_id != self.capability_id for item in gaps):
            raise ValueError("coverage gaps must bind the same capability_id")
        object.__setattr__(self, "gaps", gaps)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityCoverage:
        data = cls._payload(payload)
        return cls(
            capability_id=data["capability_id"],
            plane_id=PlaneId(data["plane_id"]),
            state=CapabilityState(data["state"]),
            implemented_module_ids=tuple(
                _sequence(data["implemented_module_ids"], "implemented_module_ids")
            ),
            partial_module_ids=tuple(_sequence(data["partial_module_ids"], "partial_module_ids")),
            missing_module_ids=tuple(_sequence(data["missing_module_ids"], "missing_module_ids")),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            gaps=tuple(CapabilityGap.from_dict(item) for item in _sequence(data["gaps"], "gaps")),
        )


@dataclass(frozen=True, slots=True)
class CapabilityCoverageReport(_OntologyRecord):
    SCHEMA_VERSION = "capability_coverage_report_v1"

    report_id: str
    ontology_sha256: str
    required_capability_ids: tuple[str, ...]
    family_id: str | None
    floral_subtype_id: str | None
    coverage: tuple[CapabilityCoverage, ...]
    gaps: tuple[CapabilityGap, ...]
    authority_ceiling: AuthorityCeiling
    sensory_authority: bool = False
    liking_authority: bool = False
    performance_authority: bool = False
    safety_authority: bool = False
    stability_authority: bool = False
    physical_execution_authority: bool = False
    release_authority: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "report_id",
            _text(self.report_id, "report_id", identifier=True),
        )
        object.__setattr__(
            self,
            "ontology_sha256",
            _digest(self.ontology_sha256, "ontology_sha256"),
        )
        object.__setattr__(
            self,
            "required_capability_ids",
            _text_tuple(
                self.required_capability_ids,
                "required_capability_ids",
                identifiers=True,
            ),
        )
        for field_name in ("family_id", "floral_subtype_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _text(value, field_name, identifier=True),
                )
        coverage = tuple(sorted(self.coverage, key=lambda item: item.capability_id))
        if len({item.capability_id for item in coverage}) != len(coverage):
            raise ValueError("coverage capability IDs must be unique")
        object.__setattr__(self, "coverage", coverage)
        gaps = tuple(
            sorted(
                self.gaps,
                key=lambda item: (item.capability_id, item.kind.value, item.gap_id),
            )
        )
        expected_gaps = tuple(gap for item in coverage for gap in item.gaps)
        expected_gaps = tuple(
            sorted(
                expected_gaps,
                key=lambda item: (item.capability_id, item.kind.value, item.gap_id),
            )
        )
        if gaps != expected_gaps:
            raise ValueError("report gaps must exactly match nested coverage gaps")
        object.__setattr__(self, "gaps", gaps)
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("report authority cannot exceed STRUCTURAL_ONLY")
        object.__setattr__(self, "authority_ceiling", ceiling)
        for field_name in (
            "sensory_authority",
            "liking_authority",
            "performance_authority",
            "safety_authority",
            "stability_authority",
            "physical_execution_authority",
            "release_authority",
        ):
            if _bool(getattr(self, field_name), field_name):
                raise ValueError(f"{field_name} is permanently false for coverage reports")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityCoverageReport:
        data = cls._payload(payload)
        return cls(
            report_id=data["report_id"],
            ontology_sha256=data["ontology_sha256"],
            required_capability_ids=tuple(
                _sequence(
                    data["required_capability_ids"],
                    "required_capability_ids",
                )
            ),
            family_id=data["family_id"],
            floral_subtype_id=data["floral_subtype_id"],
            coverage=tuple(
                CapabilityCoverage.from_dict(item)
                for item in _sequence(data["coverage"], "coverage")
            ),
            gaps=tuple(CapabilityGap.from_dict(item) for item in _sequence(data["gaps"], "gaps")),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            sensory_authority=data["sensory_authority"],
            liking_authority=data["liking_authority"],
            performance_authority=data["performance_authority"],
            safety_authority=data["safety_authority"],
            stability_authority=data["stability_authority"],
            physical_execution_authority=data["physical_execution_authority"],
            release_authority=data["release_authority"],
        )


def _gap(
    definition: CapabilityDefinition,
    kind: CapabilityGapKind,
    state: CapabilityState,
    supports: tuple[CapabilitySupport, ...],
    *,
    related_capability_ids: tuple[str, ...] = (),
    evidence_need_ids: tuple[str, ...] = (),
    detail: str,
) -> CapabilityGap:
    provenance = _canonical_provenance(
        (
            *definition.provenance_refs,
            *(item for support in supports for item in support.provenance_refs),
        )
    )
    related_key = ":".join(related_capability_ids or evidence_need_ids) or "none"
    return CapabilityGap(
        gap_id=f"gap:{definition.capability_id}:{kind.value}:{related_key}",
        capability_id=definition.capability_id,
        kind=kind,
        state=state,
        module_ids=tuple(item.module_id for item in supports),
        related_capability_ids=related_capability_ids,
        evidence_need_ids=evidence_need_ids,
        detail=detail,
        provenance_refs=provenance,
    )


def analyze_capability_coverage(
    ontology: CapabilityOntology,
    *,
    required_capability_ids: Iterable[str] = (),
    family_id: str | None = None,
    floral_subtype_id: str | None = None,
) -> CapabilityCoverageReport:
    """Return deterministic vector coverage and gaps without scalar utility."""

    if not isinstance(ontology, CapabilityOntology):
        raise TypeError("ontology must be CapabilityOntology")
    definitions = {item.capability_id: item for item in ontology.capabilities}
    requested = _text_tuple(
        required_capability_ids,
        "required_capability_ids",
        identifiers=True,
    )
    unknown = set(requested).difference(definitions)
    if unknown:
        raise KeyError(f"unknown capability IDs: {sorted(unknown)!r}")
    if requested:
        selected = tuple(definitions[item] for item in requested)
    else:
        selected = tuple(
            item
            for item in ontology.capabilities
            if item.applicability.applies_to(
                family_id=family_id,
                floral_subtype_id=floral_subtype_id,
            )
        )

    supports_by_capability: dict[str, tuple[CapabilitySupport, ...]] = {}
    for capability_id in definitions:
        supports_by_capability[capability_id] = tuple(
            item for item in ontology.module_support if item.capability_id == capability_id
        )

    raw_states: dict[str, CapabilityState] = {}
    uncovered_needs: dict[str, tuple[str, ...]] = {}
    for capability_id, definition in definitions.items():
        supports = supports_by_capability[capability_id]
        states = {item.state for item in supports}
        if CapabilityState.IMPLEMENTED in states:
            raw_states[capability_id] = CapabilityState.IMPLEMENTED
        elif CapabilityState.PARTIAL in states:
            raw_states[capability_id] = CapabilityState.PARTIAL
        else:
            raw_states[capability_id] = CapabilityState.MISSING
        covered = {
            need_id
            for support in supports
            if support.state is not CapabilityState.MISSING
            for need_id in support.covered_evidence_need_ids
        }
        uncovered_needs[capability_id] = tuple(
            sorted(set(definition.evidence_need_ids).difference(covered))
        )

    effective_cache: dict[str, CapabilityState] = {}

    def effective_state(capability_id: str) -> CapabilityState:
        cached = effective_cache.get(capability_id)
        if cached is not None:
            return cached
        raw = raw_states[capability_id]
        if raw is CapabilityState.MISSING:
            effective_cache[capability_id] = raw
            return raw
        definition = definitions[capability_id]
        prerequisites_ready = all(
            effective_state(item) is CapabilityState.IMPLEMENTED
            for item in definition.prerequisite_capability_ids
        )
        incompatible_active = any(
            raw_states[item] is not CapabilityState.MISSING
            for item in definition.incompatible_capability_ids
        )
        if (
            raw is CapabilityState.PARTIAL
            or uncovered_needs[capability_id]
            or not prerequisites_ready
            or incompatible_active
        ):
            result = CapabilityState.PARTIAL
        else:
            result = CapabilityState.IMPLEMENTED
        effective_cache[capability_id] = result
        return result

    coverage_items: list[CapabilityCoverage] = []
    for definition in selected:
        supports = supports_by_capability[definition.capability_id]
        state = effective_state(definition.capability_id)
        gaps: list[CapabilityGap] = []
        if raw_states[definition.capability_id] is CapabilityState.MISSING:
            gaps.append(
                _gap(
                    definition,
                    CapabilityGapKind.MISSING_SUPPORT,
                    state,
                    supports,
                    detail="No implemented or partial exact-module support is declared.",
                )
            )
        elif raw_states[definition.capability_id] is CapabilityState.PARTIAL:
            gaps.append(
                _gap(
                    definition,
                    CapabilityGapKind.PARTIAL_SUPPORT,
                    state,
                    supports,
                    detail="Only partial exact-module support is declared.",
                )
            )
        unmet = uncovered_needs[definition.capability_id]
        if unmet and raw_states[definition.capability_id] is not CapabilityState.MISSING:
            gaps.append(
                _gap(
                    definition,
                    CapabilityGapKind.UNMET_EVIDENCE_NEED,
                    state,
                    supports,
                    evidence_need_ids=unmet,
                    detail="Declared module interfaces do not cover every evidence need.",
                )
            )
        unsatisfied_prerequisites = tuple(
            item
            for item in definition.prerequisite_capability_ids
            if effective_state(item) is not CapabilityState.IMPLEMENTED
        )
        if (
            unsatisfied_prerequisites
            and raw_states[definition.capability_id] is not CapabilityState.MISSING
        ):
            gaps.append(
                _gap(
                    definition,
                    CapabilityGapKind.UNSATISFIED_PREREQUISITE,
                    state,
                    supports,
                    related_capability_ids=unsatisfied_prerequisites,
                    detail="One or more prerequisite capabilities are not implemented.",
                )
            )
        active_incompatibilities = tuple(
            item
            for item in definition.incompatible_capability_ids
            if raw_states[item] is not CapabilityState.MISSING
        )
        if active_incompatibilities:
            gaps.append(
                _gap(
                    definition,
                    CapabilityGapKind.INCOMPATIBLE_ACTIVE_CAPABILITIES,
                    state,
                    supports,
                    related_capability_ids=active_incompatibilities,
                    detail="Mutually incompatible capability declarations are active.",
                )
            )

        coverage_items.append(
            CapabilityCoverage(
                capability_id=definition.capability_id,
                plane_id=definition.plane_id,
                state=state,
                implemented_module_ids=tuple(
                    item.module_id for item in supports if item.state is CapabilityState.IMPLEMENTED
                ),
                partial_module_ids=tuple(
                    item.module_id for item in supports if item.state is CapabilityState.PARTIAL
                ),
                missing_module_ids=tuple(
                    item.module_id for item in supports if item.state is CapabilityState.MISSING
                ),
                authority_ceiling=definition.authority_ceiling,
                gaps=tuple(gaps),
            )
        )

    all_gaps = tuple(gap for item in coverage_items for gap in item.gaps)
    filter_key = ":".join(
        (
            family_id or "all-families",
            floral_subtype_id or "all-floral-subtypes",
        )
    )
    return CapabilityCoverageReport(
        report_id=f"coverage:{ontology.ontology_id}:{filter_key}",
        ontology_sha256=ontology.content_sha256,
        required_capability_ids=requested,
        family_id=family_id,
        floral_subtype_id=floral_subtype_id,
        coverage=tuple(coverage_items),
        gaps=all_gaps,
        authority_ceiling=ontology.authority_ceiling,
    )


def query_capability_gaps(
    ontology: CapabilityOntology,
    *,
    required_capability_ids: Iterable[str] = (),
    family_id: str | None = None,
    floral_subtype_id: str | None = None,
) -> tuple[CapabilityGap, ...]:
    return analyze_capability_coverage(
        ontology,
        required_capability_ids=required_capability_ids,
        family_id=family_id,
        floral_subtype_id=floral_subtype_id,
    ).gaps


_ONTOLOGY_SOURCE = (
    "Perfume-Chem structural capability ontology v1; software declarations only; "
    "Open family and floral namespaces; no sensory, liking, performance, safety, "
    "stability, physical-execution, formula, or release authority."
)
_ONTOLOGY_SOURCE_SHA256 = sha256(_ONTOLOGY_SOURCE.encode("utf-8")).hexdigest()


def _ontology_provenance() -> tuple[ProvenanceRef, ...]:
    return (
        ProvenanceRef(
            provenance_id="capability-ontology:design:v1",
            source_ref="inline:capability-ontology-v1-design",
            evidence_class=EvidenceClass.HEURISTIC,
            independence_key="capability-ontology:design:v1",
            source_sha256=_ONTOLOGY_SOURCE_SHA256,
        ),
    )


def _definition(
    capability_id: str,
    title: str,
    plane_id: PlaneId,
    structural_role: str,
    prerequisites: tuple[str, ...],
    evidence_description: str,
    evidence_classes: tuple[EvidenceClass, ...],
) -> CapabilityDefinition:
    return CapabilityDefinition(
        capability_id=capability_id,
        title=title,
        plane_id=plane_id,
        structural_role=structural_role,
        applicability=CapabilityApplicability.all_extensible(),
        prerequisite_capability_ids=prerequisites,
        evidence_needs=(
            EvidenceNeed(
                evidence_need_id=f"{capability_id}:evidence-interface",
                description=evidence_description,
                acceptable_evidence_classes=evidence_classes,
            ),
        ),
        incompatible_capability_ids=(),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=_ontology_provenance(),
    )


def default_capability_ontology(
    module_support: Iterable[CapabilitySupport] = (),
) -> CapabilityOntology:
    """Return the deterministic thirteen-plane, family-extensible ontology."""

    evidence = "evidence.authority_firewall"
    identity = "identity.exact_subject_binding"
    morphology = "morphology.family_floral_lattice"
    function = "function.target_linked_roles"
    relation = "relation.typed_nonredundant_graph"
    mixture = "mixture.emergent_alternatives"
    physicochemical = "physicochemical.condition_bound_model"
    temporal = "temporal.multi_window_architecture"
    biological = "biological.sensitivity_firewall"
    hedonic = "hedonic.multiview_observation"
    inventory = "inventory.target_build_projection"

    capabilities = (
        _definition(
            evidence,
            "Evidence and authority firewall",
            PlaneId.EVIDENCE_AUTHORITY,
            "Keep source class, provenance, unknowns, and authority ceilings explicit.",
            (),
            "Exact provenance and declared evidence class for every promoted claim.",
            (
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.OFFICIAL_RECORD,
                EvidenceClass.PRIMARY_SOURCE,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            identity,
            "Exact subject and identity binding",
            PlaneId.IDENTITY,
            "Separate target, material, natural, grade, lot, and stock identities.",
            (evidence,),
            "A source-bound exact identity chain without generic alias collapse.",
            (
                EvidenceClass.OFFICIAL_RECORD,
                EvidenceClass.PRIMARY_SOURCE,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            morphology,
            "Family and floral morphology lattice",
            PlaneId.MORPHOLOGY,
            "Represent arbitrary perfume families and floral subtypes on extensible axes.",
            (evidence, identity),
            "Exact-scope morphology evidence or explicitly labeled hypothesis evidence.",
            (
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.PRIMARY_SOURCE,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            function,
            "Target-linked functional roles",
            PlaneId.FUNCTION,
            "Assign role, omission loss, overdose mode, and nonredundancy to target identity.",
            (evidence, identity, morphology),
            "Target-bound functional evidence with alternatives and failure modes.",
            (
                EvidenceClass.COMPUTATIONAL_MODEL,
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.PRIMARY_SOURCE,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            relation,
            "Typed nonredundant relation graph",
            PlaneId.RELATION,
            "Keep synergy, bridge, tension, contrast, redundancy, and exclusion as typed edges.",
            (evidence, function, identity),
            "Pairwise or higher-order evidence bound to exact identities and conditions.",
            (
                EvidenceClass.COMPUTATIONAL_MODEL,
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
            ),
        ),
        _definition(
            mixture,
            "Emergent mixture alternatives",
            PlaneId.MIXTURE,
            "Keep component predictions, mixture hypotheses, alternatives, and observations separate.",
            (evidence, identity, relation),
            "Exact-composition mixture evidence distinct from component-only evidence.",
            (
                EvidenceClass.COMPUTATIONAL_MODEL,
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            physicochemical,
            "Condition-bound physicochemical model",
            PlaneId.PHYSICOCHEMICAL,
            "Bind ppm, ODT, OAV, volatility, matrix, temperature, and natural composition to conditions.",
            (evidence, identity),
            "Condition-specific physical data with units, basis, model identity, and uncertainty.",
            (
                EvidenceClass.COMPUTATIONAL_MODEL,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.OFFICIAL_RECORD,
                EvidenceClass.PRIMARY_SOURCE,
            ),
        ),
        _definition(
            temporal,
            "Multi-window temporal architecture",
            PlaneId.TEMPORAL,
            "Preserve opening, heart, drydown, continuity, transition, residue, and missing windows.",
            (evidence, identity, mixture, physicochemical),
            "Time-stamped prediction or observation evidence bound to exact conditions.",
            (
                EvidenceClass.COMPUTATIONAL_MODEL,
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            "spatial.plume_and_surface_architecture",
            "Plume and surface spatial architecture",
            PlaneId.SPATIAL_COMPOSITION,
            "Separate near-field, far-field, trail, surface, diffusion, and substantivity hypotheses.",
            (evidence, identity, physicochemical, temporal),
            "Distance-, substrate-, environment-, and time-bound transport evidence.",
            (
                EvidenceClass.COMPUTATIONAL_MODEL,
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
            ),
        ),
        _definition(
            biological,
            "Biological sensitivity firewall",
            PlaneId.BIOLOGICAL_SENSITIVITY,
            "Keep receptor hypotheses, anosmia, adaptation, irritation, and participant sensitivity distinct.",
            (evidence, identity, physicochemical),
            "Identity- and participant-bound biological evidence without population overreach.",
            (
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.PRIMARY_SOURCE,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            hedonic,
            "Non-scalar hedonic observation platform",
            PlaneId.HEDONIC,
            "Retain liking, identity, fit, comfort, novelty, and assessor/population views separately.",
            (biological, evidence, identity, temporal),
            "Blinded participant observations with order, repetition, condition, and criterion identity.",
            (EvidenceClass.DIRECT_OBSERVATION, EvidenceClass.USER_REPORT),
        ),
        _definition(
            inventory,
            "Target-to-build inventory projection",
            PlaneId.INVENTORY_BUILD,
            "Keep ideal target independent from exact-stock build mappings and quantitative holds.",
            (evidence, identity),
            "Current exact-stock authority including basis, carrier, availability, and lineage.",
            (
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.OFFICIAL_RECORD,
                EvidenceClass.USER_REPORT,
            ),
        ),
        _definition(
            "experiment.controlled_discrimination",
            "Controlled discrimination and learning",
            PlaneId.EXPERIMENT,
            "Choose controlled, blinded, constant-total experiments by unresolved decision vector.",
            (evidence, hedonic, identity, inventory),
            "Protocol and observations with controls, order, blinding, repeats, stopping, and missingness.",
            (
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.USER_REPORT,
            ),
        ),
    )
    return CapabilityOntology(
        ontology_id="perfume-chem:formulation-intelligence-capabilities:v1",
        semantic_version="1.0.0",
        capabilities=capabilities,
        module_support=tuple(module_support),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=_ontology_provenance(),
    )


__all__ = [
    "CapabilityApplicability",
    "CapabilityCoverage",
    "CapabilityCoverageReport",
    "CapabilityDefinition",
    "CapabilityGap",
    "CapabilityGapKind",
    "CapabilityOntology",
    "CapabilityState",
    "CapabilitySupport",
    "EvidenceNeed",
    "ScopeMode",
    "analyze_capability_coverage",
    "default_capability_ontology",
    "query_capability_gaps",
]
