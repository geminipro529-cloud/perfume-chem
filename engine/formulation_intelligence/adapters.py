"""Lazy, fail-closed adapters for legacy formulation-intelligence outputs.

The adapter surface is deliberately declarative.  It never imports a legacy
module, executes a formula parser, or converts an old scalar into hedonic,
sensory, safety, OAV, or release authority.  Callers provide a closed source
mapping plus a hash-bound import-closure declaration.  Every source field is
then either mapped to a structural claim, preserved as an explicit unknown or
conflict, copied to a non-authoritative protocol/failure surface, or quarantined
with a reason.  The complete canonical source mapping remains embedded in the
result, so adaptation cannot silently discard source state or context.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar, Iterable, Mapping, cast

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _exact_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return value


def _identifier(value: object, field_name: str) -> str:
    text = _exact_text(value, field_name)
    normalized = " ".join(unicodedata.normalize("NFKC", text).split()).casefold()
    if not normalized:
        raise ValueError(f"{field_name} must be a nonblank identifier")
    return normalized


def _field_name(value: object, field_name: str) -> str:
    text = _exact_text(value, field_name)
    if text != text.strip() or any(character.isspace() for character in text):
        raise ValueError(f"{field_name} must be an exact non-whitespace field name")
    return text


def _digest(value: object, field_name: str) -> str:
    text = _exact_text(value, field_name).casefold()
    if not _SHA256_RE.fullmatch(text):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _relative_path(value: object, field_name: str) -> str:
    text = _exact_text(value, field_name).replace("\\", "/")
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or not candidate.parts:
        raise ValueError(f"{field_name} must be a repository-relative path")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(f"{field_name} cannot contain traversal components")
    if ":" in candidate.parts[0]:
        raise ValueError(f"{field_name} must not be drive-qualified")
    return candidate.as_posix()


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _AdapterRecord):
        return value.as_dict()
    if isinstance(value, (PlaneAssessment, ProvenanceRef)):
        return value.as_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)
        }
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical mappings require text keys")
        return {
            key: _to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: pair[0])
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


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _to_primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_sha256(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _closed_payload(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    expected_fields: Iterable[str],
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("canonical payload must be a mapping")
    expected = {"schema_version", *expected_fields}
    received = set(payload)
    if received != expected:
        missing = sorted(expected - received)
        extra = sorted(received - expected)
        raise ValueError(
            f"{schema_version} payload does not match the closed schema; "
            f"missing={missing!r}, extra={extra!r}"
        )
    if payload["schema_version"] != schema_version:
        raise ValueError(
            f"schema_version must be {schema_version!r}, "
            f"received {payload['schema_version']!r}"
        )
    return payload


class _AdapterRecord:
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
        return _canonical_sha256(self.as_dict())


class LegacySourceStateClass(str, Enum):
    """Coarse governance class; ``source_state`` retains the exact live label."""

    ADMITTED = "admitted"
    GUARDRAIL = "guardrail"
    SHADOW = "shadow"
    FUTURE = "future"
    RESEARCH_ONLY = "research_only"
    HISTORICAL = "historical"
    UNSUPPORTED = "unsupported"
    RETIRED = "retired"


class AdapterAdmissionState(str, Enum):
    ADMITTED_READ_ONLY = "admitted_read_only"
    QUARANTINED = "quarantined"
    HOLD = "hold"


class ClosureRelation(str, Enum):
    SOURCE_ROOT = "source_root"
    DIRECT_IMPORT = "direct_import"
    TRANSITIVE_IMPORT = "transitive_import"


class FieldDisposition(str, Enum):
    CLAIM = "claim"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    FAILURE_MODE = "failure_mode"
    PROPOSED_EXPERIMENT = "proposed_experiment"
    EXCLUDE = "exclude"


@dataclass(frozen=True, slots=True)
class ImportClosureEntry(_AdapterRecord):
    SCHEMA_VERSION = "legacy_import_closure_entry_v1"

    relative_path: str
    sha256: str
    relation: ClosureRelation

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relative_path",
            _relative_path(self.relative_path, "relative_path"),
        )
        object.__setattr__(self, "sha256", _digest(self.sha256, "sha256"))
        object.__setattr__(self, "relation", ClosureRelation(self.relation))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ImportClosureEntry:
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            expected_fields=("relative_path", "sha256", "relation"),
        )
        return cls(
            relative_path=data["relative_path"],
            sha256=data["sha256"],
            relation=ClosureRelation(data["relation"]),
        )


@dataclass(frozen=True, slots=True)
class LegacyFieldRule(_AdapterRecord):
    """One exhaustive disposition for one top-level legacy output field."""

    SCHEMA_VERSION = "legacy_adapter_field_rule_v1"

    source_field: str
    disposition: FieldDisposition
    claim_key: str | None = None
    claim_kind: ClaimKind | None = None
    cardinality: ClaimCardinality | None = None
    reason: str | None = None
    needed_evidence: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_field",
            _field_name(self.source_field, "source_field"),
        )
        disposition = FieldDisposition(self.disposition)
        object.__setattr__(self, "disposition", disposition)
        claim_key = (
            None
            if self.claim_key is None
            else _identifier(self.claim_key, "claim_key")
        )
        object.__setattr__(self, "claim_key", claim_key)
        reason = None if self.reason is None else _exact_text(self.reason, "reason")
        needed = (
            None
            if self.needed_evidence is None
            else _exact_text(self.needed_evidence, "needed_evidence")
        )
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "needed_evidence", needed)

        if disposition is FieldDisposition.CLAIM:
            if claim_key is None or self.claim_kind is None or self.cardinality is None:
                raise ValueError(
                    "claim field rules require claim_key, claim_kind, and cardinality"
                )
            if reason is not None or needed is not None:
                raise ValueError("claim field rules cannot carry quarantine metadata")
            object.__setattr__(self, "claim_kind", ClaimKind(self.claim_kind))
            object.__setattr__(
                self,
                "cardinality",
                ClaimCardinality(self.cardinality),
            )
            return

        if self.claim_kind is not None or self.cardinality is not None:
            raise ValueError("non-claim field rules cannot declare claim shape")
        if disposition is FieldDisposition.UNKNOWN:
            if claim_key is None or reason is None or needed is None:
                raise ValueError(
                    "unknown field rules require claim_key, reason, and needed_evidence"
                )
        elif disposition is FieldDisposition.CONFLICT:
            if claim_key is None or reason is None or needed is not None:
                raise ValueError(
                    "conflict field rules require claim_key and reason only"
                )
        elif disposition is FieldDisposition.EXCLUDE:
            if claim_key is not None or reason is None or needed is not None:
                raise ValueError("excluded field rules require a reason only")
        else:
            if claim_key is not None or reason is not None or needed is not None:
                raise ValueError(
                    "failure-mode and experiment field rules carry values directly"
                )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LegacyFieldRule:
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            expected_fields=(
                "source_field",
                "disposition",
                "claim_key",
                "claim_kind",
                "cardinality",
                "reason",
                "needed_evidence",
            ),
        )
        return cls(
            source_field=data["source_field"],
            disposition=FieldDisposition(data["disposition"]),
            claim_key=data["claim_key"],
            claim_kind=(
                None if data["claim_kind"] is None else ClaimKind(data["claim_kind"])
            ),
            cardinality=(
                None
                if data["cardinality"] is None
                else ClaimCardinality(data["cardinality"])
            ),
            reason=data["reason"],
            needed_evidence=data["needed_evidence"],
        )


_FORCED_WITHHELD_STATES = frozenset(
    {
        LegacySourceStateClass.HISTORICAL,
        LegacySourceStateClass.UNSUPPORTED,
        LegacySourceStateClass.RETIRED,
    }
)
_NON_ADMITTED_STATES = frozenset(
    {
        LegacySourceStateClass.SHADOW,
        LegacySourceStateClass.FUTURE,
        LegacySourceStateClass.RESEARCH_ONLY,
        LegacySourceStateClass.HISTORICAL,
        LegacySourceStateClass.UNSUPPORTED,
        LegacySourceStateClass.RETIRED,
    }
)


@dataclass(frozen=True, slots=True)
class LegacyAdapterDefinition(_AdapterRecord):
    """Versioned, exhaustive, hash-bound conversion contract for one source."""

    SCHEMA_VERSION = "legacy_adapter_definition_v1"

    adapter_id: str
    source_module_id: str
    source_path: str
    source_schema_version: str
    source_state: str
    source_state_class: LegacySourceStateClass
    adapter_admission_state: AdapterAdmissionState
    plane_id: PlaneId
    source_authority_ceiling: AuthorityCeiling
    adapter_authority_ceiling: AuthorityCeiling
    import_closure: tuple[ImportClosureEntry, ...]
    transitive_closure_complete: bool
    source_provenance: tuple[ProvenanceRef, ...]
    subject_field: str
    target_scope_field: str
    temporal_scope_field: str
    matrix_scope_field: str
    condition_field: str
    output_state_field: str
    field_rules: tuple[LegacyFieldRule, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", _identifier(self.adapter_id, "adapter_id"))
        object.__setattr__(
            self,
            "source_module_id",
            _identifier(self.source_module_id, "source_module_id"),
        )
        source_path = _relative_path(self.source_path, "source_path")
        object.__setattr__(self, "source_path", source_path)
        object.__setattr__(
            self,
            "source_schema_version",
            _exact_text(self.source_schema_version, "source_schema_version"),
        )
        object.__setattr__(self, "source_state", _exact_text(self.source_state, "source_state"))
        state_class = LegacySourceStateClass(self.source_state_class)
        admission = AdapterAdmissionState(self.adapter_admission_state)
        source_ceiling = AuthorityCeiling(self.source_authority_ceiling)
        adapter_ceiling = AuthorityCeiling(self.adapter_authority_ceiling)
        object.__setattr__(self, "source_state_class", state_class)
        object.__setattr__(self, "adapter_admission_state", admission)
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        object.__setattr__(self, "source_authority_ceiling", source_ceiling)
        object.__setattr__(self, "adapter_authority_ceiling", adapter_ceiling)

        if AuthorityCeiling.minimum((source_ceiling, adapter_ceiling)) is not adapter_ceiling:
            raise ValueError("adapter authority ceiling cannot exceed its source ceiling")
        if state_class in _FORCED_WITHHELD_STATES and adapter_ceiling is not AuthorityCeiling.WITHHELD:
            raise ValueError(
                f"{state_class.value} source adapters must remain withheld"
            )
        if admission is AdapterAdmissionState.HOLD and adapter_ceiling is not AuthorityCeiling.WITHHELD:
            raise ValueError("an adapter on HOLD must remain withheld")
        if admission is AdapterAdmissionState.ADMITTED_READ_ONLY and state_class in _NON_ADMITTED_STATES:
            raise ValueError(
                "a non-admitted source cannot have an admitted read-only adapter"
            )

        closure_by_path: dict[str, ImportClosureEntry] = {}
        for entry in self.import_closure:
            if not isinstance(entry, ImportClosureEntry):
                raise TypeError("import_closure must contain ImportClosureEntry values")
            if entry.relative_path in closure_by_path:
                raise ValueError("import_closure paths must be unique")
            closure_by_path[entry.relative_path] = entry
        if not closure_by_path:
            raise ValueError("import_closure must bind at least the source root")
        roots = tuple(
            entry
            for entry in closure_by_path.values()
            if entry.relation is ClosureRelation.SOURCE_ROOT
        )
        if len(roots) != 1 or roots[0].relative_path != source_path:
            raise ValueError("import_closure must contain one exact source root")
        object.__setattr__(
            self,
            "import_closure",
            tuple(closure_by_path[path] for path in sorted(closure_by_path)),
        )
        if self.transitive_closure_complete is not True:
            raise ValueError("transitive_closure_complete must be explicitly true")

        provenance_by_id: dict[str, ProvenanceRef] = {}
        for reference in self.source_provenance:
            if not isinstance(reference, ProvenanceRef):
                raise TypeError("source_provenance must contain ProvenanceRef values")
            current = provenance_by_id.get(reference.provenance_id)
            if current is not None and current != reference:
                raise ValueError("source provenance IDs must have one definition")
            if current is not None:
                raise ValueError("source provenance IDs must be unique")
            provenance_by_id[reference.provenance_id] = reference
        if not provenance_by_id:
            raise ValueError("source_provenance must not be empty")
        root_digest = roots[0].sha256
        if not any(
            reference.source_sha256 == root_digest
            for reference in provenance_by_id.values()
        ):
            raise ValueError("source provenance must bind the source-root SHA-256")
        object.__setattr__(
            self,
            "source_provenance",
            tuple(provenance_by_id[key] for key in sorted(provenance_by_id)),
        )

        context_fields = (
            "subject_field",
            "target_scope_field",
            "temporal_scope_field",
            "matrix_scope_field",
            "condition_field",
            "output_state_field",
        )
        context_values = tuple(
            _field_name(getattr(self, name), name) for name in context_fields
        )
        if len(context_values) != len(set(context_values)):
            raise ValueError("context and state field names must be unique")
        for name, value in zip(context_fields, context_values, strict=True):
            object.__setattr__(self, name, value)

        rule_by_field: dict[str, LegacyFieldRule] = {}
        for rule in self.field_rules:
            if not isinstance(rule, LegacyFieldRule):
                raise TypeError("field_rules must contain LegacyFieldRule values")
            if rule.source_field in rule_by_field:
                raise ValueError("field_rules require a unique source_field")
            if rule.source_field in context_values or rule.source_field == "schema_version":
                raise ValueError("a source field cannot be both context and a field rule")
            rule_by_field[rule.source_field] = rule
        if not rule_by_field:
            raise ValueError("field_rules must account for at least one source field")
        object.__setattr__(
            self,
            "field_rules",
            tuple(rule_by_field[key] for key in sorted(rule_by_field)),
        )

    @property
    def expected_source_fields(self) -> frozenset[str]:
        return frozenset(
            {
                "schema_version",
                self.subject_field,
                self.target_scope_field,
                self.temporal_scope_field,
                self.matrix_scope_field,
                self.condition_field,
                self.output_state_field,
                *(rule.source_field for rule in self.field_rules),
            }
        )

    @property
    def import_closure_manifest_sha256(self) -> str:
        return _canonical_sha256(
            {
                "schema_version": "legacy_import_closure_manifest_v1",
                "source_path": self.source_path,
                "transitive_closure_complete": self.transitive_closure_complete,
                "entries": [entry.as_dict() for entry in self.import_closure],
            }
        )

    def constructor_dict(self) -> dict[str, Any]:
        """Return constructor values, useful for explicit immutable variants."""

        return {item.name: getattr(self, item.name) for item in fields(self)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LegacyAdapterDefinition:
        names = tuple(item.name for item in fields(cls))
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            expected_fields=names,
        )
        return cls(
            adapter_id=data["adapter_id"],
            source_module_id=data["source_module_id"],
            source_path=data["source_path"],
            source_schema_version=data["source_schema_version"],
            source_state=data["source_state"],
            source_state_class=LegacySourceStateClass(data["source_state_class"]),
            adapter_admission_state=AdapterAdmissionState(
                data["adapter_admission_state"]
            ),
            plane_id=PlaneId(data["plane_id"]),
            source_authority_ceiling=AuthorityCeiling(
                data["source_authority_ceiling"]
            ),
            adapter_authority_ceiling=AuthorityCeiling(
                data["adapter_authority_ceiling"]
            ),
            import_closure=tuple(
                ImportClosureEntry.from_dict(item) for item in data["import_closure"]
            ),
            transitive_closure_complete=data["transitive_closure_complete"],
            source_provenance=tuple(
                ProvenanceRef.from_dict(item) for item in data["source_provenance"]
            ),
            subject_field=data["subject_field"],
            target_scope_field=data["target_scope_field"],
            temporal_scope_field=data["temporal_scope_field"],
            matrix_scope_field=data["matrix_scope_field"],
            condition_field=data["condition_field"],
            output_state_field=data["output_state_field"],
            field_rules=tuple(
                LegacyFieldRule.from_dict(item) for item in data["field_rules"]
            ),
        )


@dataclass(frozen=True, slots=True)
class LegacyAdapterContext(_AdapterRecord):
    """Exact, unnormalized source context retained beside normalized scope."""

    SCHEMA_VERSION = "legacy_adapter_context_v1"

    subject: str
    target_scope: str
    temporal_scope: str
    matrix_scope: str
    condition: str

    def __post_init__(self) -> None:
        for field_name in (
            "subject",
            "target_scope",
            "temporal_scope",
            "matrix_scope",
            "condition",
        ):
            object.__setattr__(
                self,
                field_name,
                _exact_text(getattr(self, field_name), field_name),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LegacyAdapterContext:
        names = tuple(item.name for item in fields(cls))
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            expected_fields=names,
        )
        return cls(**{name: data[name] for name in names})


@dataclass(frozen=True, slots=True)
class LegacyQuarantinedField(_AdapterRecord):
    SCHEMA_VERSION = "legacy_quarantined_field_v1"

    source_field: str
    disposition: FieldDisposition
    canonical_value_json: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_field",
            _field_name(self.source_field, "source_field"),
        )
        disposition = FieldDisposition(self.disposition)
        if disposition not in {FieldDisposition.UNKNOWN, FieldDisposition.EXCLUDE}:
            raise ValueError("only unknown or excluded fields are quarantined")
        object.__setattr__(self, "disposition", disposition)
        canonical = _exact_text(self.canonical_value_json, "canonical_value_json")
        try:
            decoded = json.loads(canonical)
        except json.JSONDecodeError as exc:
            raise ValueError("canonical_value_json must be valid JSON") from exc
        if _canonical_json(decoded) != canonical:
            raise ValueError("canonical_value_json must use canonical JSON encoding")
        object.__setattr__(self, "canonical_value_json", canonical)
        object.__setattr__(self, "reason", _exact_text(self.reason, "reason"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LegacyQuarantinedField:
        names = tuple(item.name for item in fields(cls))
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            expected_fields=names,
        )
        return cls(
            source_field=data["source_field"],
            disposition=FieldDisposition(data["disposition"]),
            canonical_value_json=data["canonical_value_json"],
            reason=data["reason"],
        )


@dataclass(frozen=True, slots=True)
class LegacyAdapterResult(_AdapterRecord):
    SCHEMA_VERSION = "legacy_adapter_result_v1"

    definition: LegacyAdapterDefinition
    context: LegacyAdapterContext
    source_output_state: str
    source_payload_canonical_json: str
    source_payload_sha256: str
    import_closure_manifest_sha256: str
    assessment: PlaneAssessment
    quarantined_fields: tuple[LegacyQuarantinedField, ...]
    formula_authority: bool = False
    sensory_authority: bool = False
    safety_authority: bool = False
    release_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.definition, LegacyAdapterDefinition):
            raise TypeError("definition must be a LegacyAdapterDefinition")
        if not isinstance(self.context, LegacyAdapterContext):
            raise TypeError("context must be a LegacyAdapterContext")
        if not isinstance(self.assessment, PlaneAssessment):
            raise TypeError("assessment must be a PlaneAssessment")
        object.__setattr__(
            self,
            "source_output_state",
            _exact_text(self.source_output_state, "source_output_state"),
        )
        canonical_payload = _exact_text(
            self.source_payload_canonical_json,
            "source_payload_canonical_json",
        )
        try:
            decoded = json.loads(canonical_payload)
        except json.JSONDecodeError as exc:
            raise ValueError("source_payload_canonical_json must be valid JSON") from exc
        if not isinstance(decoded, dict):
            raise TypeError("source_payload_canonical_json must encode a mapping")
        if _canonical_json(decoded) != canonical_payload:
            raise ValueError("source payload must use canonical JSON encoding")
        expected_payload_digest = sha256(canonical_payload.encode("utf-8")).hexdigest()
        actual_payload_digest = _digest(
            self.source_payload_sha256,
            "source_payload_sha256",
        )
        if actual_payload_digest != expected_payload_digest:
            raise ValueError("source_payload_sha256 does not bind the canonical payload")
        object.__setattr__(self, "source_payload_sha256", actual_payload_digest)

        closure_digest = _digest(
            self.import_closure_manifest_sha256,
            "import_closure_manifest_sha256",
        )
        if closure_digest != self.definition.import_closure_manifest_sha256:
            raise ValueError("import closure manifest does not match the adapter definition")
        object.__setattr__(self, "import_closure_manifest_sha256", closure_digest)

        source_context = (
            decoded[self.definition.subject_field],
            decoded[self.definition.target_scope_field],
            decoded[self.definition.temporal_scope_field],
            decoded[self.definition.matrix_scope_field],
            decoded[self.definition.condition_field],
        )
        if source_context != (
            self.context.subject,
            self.context.target_scope,
            self.context.temporal_scope,
            self.context.matrix_scope,
            self.context.condition,
        ):
            raise ValueError("adapter context does not match the preserved source payload")
        if decoded[self.definition.output_state_field] != self.source_output_state:
            raise ValueError("source output state does not match the preserved source payload")
        if decoded["schema_version"] != self.definition.source_schema_version:
            raise ValueError("preserved source schema does not match the adapter definition")
        if self.assessment.plane_id is not self.definition.plane_id:
            raise ValueError("assessment plane does not match the adapter definition")
        if AuthorityCeiling.minimum(
            (
                self.definition.adapter_authority_ceiling,
                self.assessment.authority_ceiling,
            )
        ) is not self.assessment.authority_ceiling:
            raise ValueError("assessment authority exceeds the adapter ceiling")

        quarantined_by_field: dict[str, LegacyQuarantinedField] = {}
        for item in self.quarantined_fields:
            if not isinstance(item, LegacyQuarantinedField):
                raise TypeError(
                    "quarantined_fields must contain LegacyQuarantinedField values"
                )
            if item.source_field in quarantined_by_field:
                raise ValueError("quarantined source fields must be unique")
            quarantined_by_field[item.source_field] = item
        object.__setattr__(
            self,
            "quarantined_fields",
            tuple(quarantined_by_field[key] for key in sorted(quarantined_by_field)),
        )
        for field_name in (
            "formula_authority",
            "sensory_authority",
            "safety_authority",
            "release_authority",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"{field_name} cannot be promoted by an adapter")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LegacyAdapterResult:
        names = tuple(item.name for item in fields(cls))
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            expected_fields=names,
        )
        candidate = cls(
            definition=LegacyAdapterDefinition.from_dict(data["definition"]),
            context=LegacyAdapterContext.from_dict(data["context"]),
            source_output_state=data["source_output_state"],
            source_payload_canonical_json=data["source_payload_canonical_json"],
            source_payload_sha256=data["source_payload_sha256"],
            import_closure_manifest_sha256=data["import_closure_manifest_sha256"],
            assessment=PlaneAssessment.from_dict(data["assessment"]),
            quarantined_fields=tuple(
                LegacyQuarantinedField.from_dict(item)
                for item in data["quarantined_fields"]
            ),
            formula_authority=data["formula_authority"],
            sensory_authority=data["sensory_authority"],
            safety_authority=data["safety_authority"],
            release_authority=data["release_authority"],
        )
        decoded = json.loads(candidate.source_payload_canonical_json)
        if not isinstance(decoded, dict):
            raise TypeError("source_payload_canonical_json must encode a mapping")
        derived = _derive_legacy_result(
            candidate.definition,
            decoded,
            candidate.import_closure_manifest_sha256,
        )
        if candidate != derived:
            raise ValueError(
                "serialized legacy adapter result does not match derived state"
            )
        return derived


def verify_import_closure(
    definition: LegacyAdapterDefinition,
    repository_root: str | Path,
) -> str:
    """Verify all declared closure bytes without importing or executing them."""

    if not isinstance(definition, LegacyAdapterDefinition):
        raise TypeError("definition must be a LegacyAdapterDefinition")
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise ValueError("repository_root must be an existing directory")
    for entry in definition.import_closure:
        candidate = (root / Path(*PurePosixPath(entry.relative_path).parts)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("import closure path resolves outside repository_root") from exc
        if not candidate.is_file():
            raise ValueError(
                f"import closure file is missing: {entry.relative_path}"
            )
        actual = sha256(candidate.read_bytes()).hexdigest()
        if actual != entry.sha256:
            raise ValueError(
                "import closure hash mismatch for "
                f"{entry.relative_path}: expected {entry.sha256}, received {actual}"
            )
    return definition.import_closure_manifest_sha256


def _closed_source_payload(
    definition: LegacyAdapterDefinition,
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("legacy source output must be a mapping")
    if not all(isinstance(key, str) for key in payload):
        raise TypeError("legacy source output requires text field names")
    received = set(payload)
    expected = set(definition.expected_source_fields)
    if received != expected:
        missing = sorted(expected - received)
        extra = sorted(received - expected)
        raise ValueError(
            "legacy output does not match the closed source schema; "
            f"missing={missing!r}, extra={extra!r}"
        )
    if payload["schema_version"] != definition.source_schema_version:
        raise ValueError(
            "source schema_version must be "
            f"{definition.source_schema_version!r}, "
            f"received {payload['schema_version']!r}"
        )
    _to_primitive(payload)
    return payload


def _collection_values(
    value: Any,
    *,
    field_name: str,
    cardinality: ClaimCardinality,
) -> tuple[tuple[str, str, int | None], ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{cardinality.value} field {field_name!r} requires an array")
    if not value:
        raise ValueError(f"{field_name!r} collection must not be empty")
    canonical_values = tuple(_canonical_json(item) for item in value)
    if any(item == "null" for item in canonical_values):
        raise ValueError(f"{field_name!r} claim members cannot be null")
    if len(canonical_values) != len(set(canonical_values)):
        raise ValueError(f"{field_name!r} requires unique canonical members")
    if cardinality is ClaimCardinality.SET_MEMBER:
        ordered = tuple(sorted(canonical_values))
        return tuple(
            (item, f"{field_name}:{sha256(item.encode()).hexdigest()[:16]}", None)
            for item in ordered
        )
    return tuple(
        (
            item,
            f"{field_name}:{sha256(item.encode()).hexdigest()[:16]}",
            index,
        )
        for index, item in enumerate(canonical_values)
    )


def _claim_value(canonical_value: str) -> str:
    decoded = json.loads(canonical_value)
    return decoded if isinstance(decoded, str) else canonical_value


def _claim_records(
    definition: LegacyAdapterDefinition,
    rule: LegacyFieldRule,
    value: Any,
    authority_ceiling: AuthorityCeiling,
) -> tuple[ScopedClaim, ...]:
    assert rule.claim_key is not None
    assert rule.claim_kind is not None
    assert rule.cardinality is not None
    members: tuple[tuple[str, str | None, int | None], ...]
    if rule.cardinality is ClaimCardinality.SINGLE:
        if value is None or isinstance(value, (list, tuple, Mapping)):
            raise TypeError(
                f"single claim field {rule.source_field!r} requires a non-null scalar"
            )
        canonical = _canonical_json(value)
        members = ((canonical, None, None),)
    else:
        members = _collection_values(
            value,
            field_name=rule.source_field,
            cardinality=rule.cardinality,
        )
    records: list[ScopedClaim] = []
    for canonical, member_id, order_index in members:
        item_digest = sha256(canonical.encode("utf-8")).hexdigest()[:16]
        records.append(
            ScopedClaim(
                claim_id=(
                    f"legacy:{definition.adapter_id}:{rule.source_field}:{item_digest}"
                ),
                claim_key=rule.claim_key,
                claim_value=_claim_value(canonical),
                claim_kind=rule.claim_kind,
                authority_ceiling=authority_ceiling,
                provenance_refs=definition.source_provenance,
                cardinality=rule.cardinality,
                member_id=member_id,
                order_index=order_index,
            )
        )
    return tuple(records)


def _text_surface(value: Any, source_field: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (_exact_text(value, source_field),)
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{source_field!r} requires text or an array of text")
    result = tuple(_exact_text(item, source_field) for item in value)
    if len(result) != len(set(result)):
        raise ValueError(f"{source_field!r} must contain unique text values")
    return result


def _is_explicit_hold(output_state: str) -> bool:
    tokens = {
        token
        for token in re.split(r"[^A-Z0-9]+", output_state.upper())
        if token
    }
    return bool(tokens.intersection({"HOLD", "WITHHELD", "BLOCKED"}))


def _derive_legacy_result(
    definition: LegacyAdapterDefinition,
    payload: Mapping[str, Any],
    closure_manifest_sha256: str,
) -> LegacyAdapterResult:
    """Purely derive every adapter-owned field from one closed source mapping."""

    if not isinstance(definition, LegacyAdapterDefinition):
        raise TypeError("definition must be a LegacyAdapterDefinition")
    closure_manifest = _digest(
        closure_manifest_sha256,
        "closure_manifest_sha256",
    )
    if closure_manifest != definition.import_closure_manifest_sha256:
        raise ValueError("import closure manifest does not match the adapter definition")
    source = _closed_source_payload(definition, payload)
    canonical_payload = _canonical_json(source)
    payload_digest = sha256(canonical_payload.encode("utf-8")).hexdigest()
    context = LegacyAdapterContext(
        subject=_exact_text(source[definition.subject_field], "subject"),
        target_scope=_exact_text(
            source[definition.target_scope_field],
            "target_scope",
        ),
        temporal_scope=_exact_text(
            source[definition.temporal_scope_field],
            "temporal_scope",
        ),
        matrix_scope=_exact_text(
            source[definition.matrix_scope_field],
            "matrix_scope",
        ),
        condition=_exact_text(source[definition.condition_field], "condition"),
    )
    output_state = _exact_text(
        source[definition.output_state_field],
        "source_output_state",
    )
    effective_ceiling = (
        AuthorityCeiling.WITHHELD
        if _is_explicit_hold(output_state)
        else definition.adapter_authority_ceiling
    )

    claims: list[ScopedClaim] = []
    unknowns: list[UnknownFact] = []
    conflicts: list[PlaneConflict] = []
    quarantined: list[LegacyQuarantinedField] = []
    failure_modes: list[str] = []
    experiments: list[str] = []
    for rule in definition.field_rules:
        value = source[rule.source_field]
        if rule.disposition is FieldDisposition.CLAIM:
            claims.extend(
                _claim_records(definition, rule, value, effective_ceiling)
            )
        elif rule.disposition is FieldDisposition.UNKNOWN:
            assert rule.claim_key is not None
            assert rule.reason is not None
            assert rule.needed_evidence is not None
            unknowns.append(
                UnknownFact(
                    unknown_id=f"legacy:{definition.adapter_id}:{rule.source_field}",
                    field_key=rule.claim_key,
                    reason=rule.reason,
                    needed_evidence=rule.needed_evidence,
                    provenance_refs=definition.source_provenance,
                )
            )
            quarantined.append(
                LegacyQuarantinedField(
                    source_field=rule.source_field,
                    disposition=rule.disposition,
                    canonical_value_json=_canonical_json(value),
                    reason=rule.reason,
                )
            )
        elif rule.disposition is FieldDisposition.CONFLICT:
            assert rule.claim_key is not None
            assert rule.reason is not None
            alternatives = _text_surface(value, rule.source_field)
            if len(alternatives) < 2:
                raise ValueError(
                    f"conflict field {rule.source_field!r} requires two alternatives"
                )
            conflicts.append(
                PlaneConflict(
                    conflict_id=(
                        f"legacy:{definition.adapter_id}:{rule.source_field}:conflict"
                    ),
                    claim_key=rule.claim_key,
                    alternatives=alternatives,
                    reason=rule.reason,
                    provenance_refs=definition.source_provenance,
                )
            )
        elif rule.disposition is FieldDisposition.FAILURE_MODE:
            failure_modes.extend(_text_surface(value, rule.source_field))
        elif rule.disposition is FieldDisposition.PROPOSED_EXPERIMENT:
            experiments.extend(_text_surface(value, rule.source_field))
        else:
            assert rule.reason is not None
            quarantined.append(
                LegacyQuarantinedField(
                    source_field=rule.source_field,
                    disposition=rule.disposition,
                    canonical_value_json=_canonical_json(value),
                    reason=rule.reason,
                )
            )

    if definition.source_state_class is not LegacySourceStateClass.ADMITTED:
        failure_modes.append(
            "source module is not admitted: "
            f"{definition.source_state} ({definition.source_state_class.value})"
        )
    if definition.adapter_admission_state is not AdapterAdmissionState.ADMITTED_READ_ONLY:
        failure_modes.append(
            "adapter admission state is "
            f"{definition.adapter_admission_state.value}"
        )
    if _is_explicit_hold(output_state):
        failure_modes.append(f"source output state is {output_state}")

    assessment_seed = {
        "schema_version": "legacy_adapter_assessment_seed_v1",
        "definition_sha256": definition.content_sha256,
        "source_payload_sha256": payload_digest,
        "effective_authority_ceiling": effective_ceiling.value,
    }
    assessment_digest = _canonical_sha256(assessment_seed)
    assessment = PlaneAssessment(
        assessment_id=f"legacy-adapter-assessment:{assessment_digest}",
        module_id=f"legacy-adapter:{definition.adapter_id}",
        plane_id=definition.plane_id,
        scope=AssessmentScope(
            target_scope=context.target_scope,
            temporal_scope=context.temporal_scope,
            matrix_scope=context.matrix_scope,
        ),
        claims=tuple(claims),
        support_intervals=(),
        conflicts=tuple(conflicts),
        unknowns=tuple(unknowns),
        failure_modes=tuple(dict.fromkeys(failure_modes)),
        proposed_experiments=tuple(dict.fromkeys(experiments)),
        provenance_refs=definition.source_provenance,
        authority_ceiling=effective_ceiling,
        freshness_hashes=(
            definition.content_sha256,
            payload_digest,
            closure_manifest,
            *(entry.sha256 for entry in definition.import_closure),
        ),
        native_criteria=(),
    )
    return LegacyAdapterResult(
        definition=definition,
        context=context,
        source_output_state=output_state,
        source_payload_canonical_json=canonical_payload,
        source_payload_sha256=payload_digest,
        import_closure_manifest_sha256=closure_manifest,
        assessment=assessment,
        quarantined_fields=tuple(quarantined),
    )


def adapt_legacy_output(
    definition: LegacyAdapterDefinition,
    payload: Mapping[str, Any],
    *,
    repository_root: str | Path,
) -> LegacyAdapterResult:
    """Adapt one exact legacy output mapping without importing its source module."""

    if not isinstance(definition, LegacyAdapterDefinition):
        raise TypeError("definition must be a LegacyAdapterDefinition")
    closure_manifest = verify_import_closure(definition, repository_root)
    return _derive_legacy_result(definition, payload, closure_manifest)


__all__ = [
    "AdapterAdmissionState",
    "ClosureRelation",
    "FieldDisposition",
    "ImportClosureEntry",
    "LegacyAdapterContext",
    "LegacyAdapterDefinition",
    "LegacyAdapterResult",
    "LegacyFieldRule",
    "LegacyQuarantinedField",
    "LegacySourceStateClass",
    "adapt_legacy_output",
    "verify_import_closure",
]
