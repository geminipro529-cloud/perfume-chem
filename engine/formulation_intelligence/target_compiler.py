"""Fail-closed target compilation for formulation-intelligence planes.

This module preserves a requested perfume identity independently of inventory.
It emits structural declarations and explicit unknowns; it never emits materials,
doses, ratios, a formula, or sensory/release authority.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, NoReturn, cast

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    ParetoCriterion,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NON_IDENTIFIER = re.compile(r"[^a-z0-9]+")
_PROHIBITED_AGGREGATES = frozenset(
    {
        "aggregate score",
        "beauty",
        "beauty score",
        "hedonic score",
        "overall score",
    }
)
_TARGET_CLAIM_KEYS = frozenset(
    {
        "target_identity",
        "named_reference",
        "family_neighborhood",
        "abstraction_level",
        "expression",
        "exclusion",
        "protected_recognizer",
        "forbidden_drift",
        "temporal_transformation",
        "temporal_request",
        "matrix_context",
        "criterion",
        "target_resolution",
    }
)


def _text(value: object, field_name: str, *, casefold: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if casefold else normalized


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _exact_text(value: object, field_name: str) -> str:
    """Validate text while preserving every source character exactly."""

    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return value


def _nonnegative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _identifier(value: object, field_name: str) -> str:
    return _text(value, field_name)


def _slug(value: str) -> str:
    slug = _NON_IDENTIFIER.sub("-", _text(value, "scope")).strip("-")
    return slug or "unspecified"


def _text_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    reject_aggregates: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    if reject_aggregates:
        prohibited = sorted(set(normalized).intersection(_PROHIBITED_AGGREGATES))
        if prohibited:
            raise ValueError(
                f"{field_name} contains unauthorized aggregate criteria: "
                + ", ".join(prohibited)
            )
    return tuple(sorted(normalized))


def _sha256_digest(value: object, field_name: str) -> str:
    normalized = _text(value, field_name)
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        serializer = getattr(value, "as_dict", None)
        if callable(serializer):
            return serializer()
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
    if value is None or isinstance(value, (str, int, bool, float)):
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


def _payload(payload: Mapping[str, Any], record_type: type[Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    schema_version = record_type.SCHEMA_VERSION
    declared = payload.get("schema_version")
    if declared != schema_version:
        raise ValueError(
            f"schema_version must be {schema_version!r}, received {declared!r}"
        )
    expected = {"schema_version", *(item.name for item in fields(record_type))}
    supplied = set(payload)
    missing = sorted(expected - supplied)
    unexpected = sorted(supplied - expected)
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    if unexpected:
        raise ValueError("unexpected fields: " + ", ".join(unexpected))
    return payload


def _sequence(value: object, field_name: str) -> tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be a sequence")
    return tuple(value)


def _raise_type(message: str) -> NoReturn:
    raise TypeError(message)


def _strict_provenance_ref(payload: object) -> ProvenanceRef:
    if not isinstance(payload, Mapping):
        raise TypeError("provenance ref payload must be a mapping")
    data = _payload(payload, ProvenanceRef)
    return ProvenanceRef.from_dict(data)


class _CanonicalTargetRecord:
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


class TargetMode(str, Enum):
    NAMED_REFERENCE = "named_reference"
    CONCEPT_ONLY = "concept_only"
    HYBRID = "hybrid"
    FAMILY_ARCHITECTURE = "family_architecture"


class AbstractionLevel(str, Enum):
    UNSPECIFIED = "unspecified"
    LITERAL_REFERENCE = "literal_reference"
    RECOGNIZABLE_ABSTRACTION = "recognizable_abstraction"
    EVOCATIVE = "evocative"


class TargetResolution(str, Enum):
    RESOLVED_FOR_DESIGN = "resolved_for_design"
    PARTIAL_HOLD = "partial_hold"
    UNRESOLVED_HOLD = "unresolved_hold"


class ReferenceEvidenceTier(str, Enum):
    """Claim type, not a transferable quality ranking."""

    LEAD_ONLY = "lead_only"
    STRUCTURAL_DESCRIPTION = "structural_description"
    INSTRUMENTAL_OBSERVATION = "instrumental_observation"
    HUMAN_PERCEPTION = "human_perception"
    DIRECT_USER_REPORT = "direct_user_report"


class TargetAcceptanceState(str, Enum):
    UNACCEPTED = "unaccepted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class TargetSourceSpan(_CanonicalTargetRecord):
    """Half-open Unicode-character offsets into an exact source artifact."""

    SCHEMA_VERSION = "target_source_span_v1"

    start_char: int
    end_char: int

    def __post_init__(self) -> None:
        start = _nonnegative_int(self.start_char, "start_char")
        end = _nonnegative_int(self.end_char, "end_char")
        if end < start:
            raise ValueError("end_char must not precede start_char")
        object.__setattr__(self, "start_char", start)
        object.__setattr__(self, "end_char", end)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSourceSpan:
        data = _payload(payload, cls)
        return cls(start_char=data["start_char"], end_char=data["end_char"])


@dataclass(frozen=True, slots=True)
class TargetRequestSource(_CanonicalTargetRecord):
    """Exact request excerpt and the source coordinates from which it came."""

    SCHEMA_VERSION = "target_request_source_v1"

    raw_request: str
    source_ref: str
    source_sha256: str
    span: TargetSourceSpan
    origin: str

    def __post_init__(self) -> None:
        raw = _exact_text(self.raw_request, "raw_request")
        source_ref = _exact_text(self.source_ref, "source_ref")
        origin = _exact_text(self.origin, "origin")
        source_sha256 = _sha256_digest(self.source_sha256, "source_sha256")
        if not isinstance(self.span, TargetSourceSpan):
            raise TypeError("span must be a TargetSourceSpan")
        if self.span.end_char - self.span.start_char != len(raw):
            raise ValueError("span length must exactly match raw_request")
        object.__setattr__(self, "raw_request", raw)
        object.__setattr__(self, "source_ref", source_ref)
        object.__setattr__(self, "source_sha256", source_sha256)
        object.__setattr__(self, "origin", origin)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetRequestSource:
        data = _payload(payload, cls)
        span = data["span"]
        if not isinstance(span, Mapping):
            raise TypeError("span must be a mapping")
        return cls(
            raw_request=data["raw_request"],
            source_ref=data["source_ref"],
            source_sha256=data["source_sha256"],
            span=TargetSourceSpan.from_dict(span),
            origin=data["origin"],
        )


@dataclass(frozen=True, slots=True)
class TargetBranch(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_branch_v1"

    branch_id: str
    interpretation: str
    claim_keys: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "branch_id", _identifier(self.branch_id, "branch_id"))
        object.__setattr__(
            self,
            "interpretation",
            _text(self.interpretation, "interpretation"),
        )
        claim_keys = _text_tuple(self.claim_keys, "claim_keys")
        if not claim_keys:
            raise ValueError("target branches require claim_keys")
        object.__setattr__(self, "claim_keys", claim_keys)
        object.__setattr__(
            self,
            "evidence_ids",
            _text_tuple(self.evidence_ids, "evidence_ids"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetBranch:
        data = _payload(payload, cls)
        return cls(
            branch_id=data["branch_id"],
            interpretation=data["interpretation"],
            claim_keys=_sequence(data["claim_keys"], "claim_keys"),
            evidence_ids=_sequence(data["evidence_ids"], "evidence_ids"),
        )


@dataclass(frozen=True, slots=True)
class TargetConflict(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_conflict_v1"

    conflict_id: str
    claim_key: str
    branch_ids: tuple[str, ...]
    reason: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "conflict_id",
            _identifier(self.conflict_id, "conflict_id"),
        )
        object.__setattr__(self, "claim_key", _identifier(self.claim_key, "claim_key"))
        branch_ids = _text_tuple(self.branch_ids, "branch_ids")
        if len(branch_ids) < 2:
            raise ValueError("target conflicts require at least two branches")
        object.__setattr__(self, "branch_ids", branch_ids)
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        object.__setattr__(
            self,
            "evidence_ids",
            _text_tuple(self.evidence_ids, "evidence_ids"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetConflict:
        data = _payload(payload, cls)
        return cls(
            conflict_id=data["conflict_id"],
            claim_key=data["claim_key"],
            branch_ids=_sequence(data["branch_ids"], "branch_ids"),
            reason=data["reason"],
            evidence_ids=_sequence(data["evidence_ids"], "evidence_ids"),
        )


@dataclass(frozen=True, slots=True)
class TargetUnknown(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_unknown_v1"

    unknown_id: str
    field_key: str
    reason: str
    needed_evidence: str
    critical: bool
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "unknown_id", _identifier(self.unknown_id, "unknown_id"))
        object.__setattr__(self, "field_key", _identifier(self.field_key, "field_key"))
        object.__setattr__(self, "reason", _text(self.reason, "reason"))
        object.__setattr__(
            self,
            "needed_evidence",
            _text(self.needed_evidence, "needed_evidence"),
        )
        if not isinstance(self.critical, bool):
            raise TypeError("critical must be boolean")
        object.__setattr__(
            self,
            "evidence_ids",
            _text_tuple(self.evidence_ids, "evidence_ids"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetUnknown:
        data = _payload(payload, cls)
        return cls(
            unknown_id=data["unknown_id"],
            field_key=data["field_key"],
            reason=data["reason"],
            needed_evidence=data["needed_evidence"],
            critical=data["critical"],
            evidence_ids=_sequence(data["evidence_ids"], "evidence_ids"),
        )


@dataclass(frozen=True, slots=True)
class TargetAcceptance(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_acceptance_v1"

    acceptance_id: str
    state: TargetAcceptanceState
    accepted_branch_ids: tuple[str, ...]
    decision_basis: str
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "acceptance_id",
            _identifier(self.acceptance_id, "acceptance_id"),
        )
        state = TargetAcceptanceState(self.state)
        branch_ids = _text_tuple(self.accepted_branch_ids, "accepted_branch_ids")
        provenance = _provenance_refs(self.provenance_refs)
        if state is TargetAcceptanceState.ACCEPTED:
            if not branch_ids:
                raise ValueError("accepted target requires an accepted branch")
            if not provenance:
                raise ValueError("accepted target requires acceptance provenance")
        elif branch_ids:
            raise ValueError("unaccepted or rejected target cannot accept branches")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "accepted_branch_ids", branch_ids)
        object.__setattr__(
            self,
            "decision_basis",
            _text(self.decision_basis, "decision_basis"),
        )
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetAcceptance:
        data = _payload(payload, cls)
        return cls(
            acceptance_id=data["acceptance_id"],
            state=TargetAcceptanceState(data["state"]),
            accepted_branch_ids=_sequence(
                data["accepted_branch_ids"],
                "accepted_branch_ids",
            ),
            decision_basis=data["decision_basis"],
            provenance_refs=tuple(
                _strict_provenance_ref(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
        )


@dataclass(frozen=True, slots=True)
class TargetAuthorityFlags(_CanonicalTargetRecord):
    """Hard-false downstream authorities carried by target compilation."""

    SCHEMA_VERSION = "target_authority_flags_v1"

    strict_similarity: bool = False
    observed_smell: bool = False
    liking: bool = False
    physical_performance: bool = False
    safety: bool = False
    stability: bool = False
    physical_execution: bool = False
    release: bool = False

    def __post_init__(self) -> None:
        values = tuple(getattr(self, item.name) for item in fields(self))
        if any(not isinstance(value, bool) for value in values):
            raise TypeError("target authority flags must be boolean")
        if any(values):
            raise ValueError("target compiler authority cannot be promoted")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetAuthorityFlags:
        data = _payload(payload, cls)
        return cls(
            strict_similarity=data.get("strict_similarity", False),
            observed_smell=data.get("observed_smell", False),
            liking=data.get("liking", False),
            physical_performance=data.get("physical_performance", False),
            safety=data.get("safety", False),
            stability=data.get("stability", False),
            physical_execution=data.get("physical_execution", False),
            release=data.get("release", False),
        )


@dataclass(frozen=True, slots=True)
class TargetEvidenceRef(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_evidence_ref_v1"

    evidence_id: str
    source_ref: str
    tier: ReferenceEvidenceTier
    claim_scope: str
    source_sha256: str | None = None
    claim_keys: tuple[str, ...] = ()
    provenance_refs: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _identifier(self.evidence_id, "evidence_id"))
        object.__setattr__(
            self,
            "source_ref",
            _text(self.source_ref, "source_ref", casefold=False),
        )
        object.__setattr__(self, "tier", ReferenceEvidenceTier(self.tier))
        object.__setattr__(self, "claim_scope", _text(self.claim_scope, "claim_scope"))
        if self.source_sha256 is not None:
            object.__setattr__(
                self,
                "source_sha256",
                _sha256_digest(self.source_sha256, "source_sha256"),
            )
        claim_keys = _text_tuple(self.claim_keys, "claim_keys")
        if not claim_keys:
            raise ValueError("target evidence must be bound to claim_keys")
        unknown_claim_keys = sorted(set(claim_keys) - _TARGET_CLAIM_KEYS)
        if unknown_claim_keys:
            raise ValueError(
                "target evidence references unsupported claim_keys: "
                + ", ".join(unknown_claim_keys)
            )
        provenance = _provenance_refs(self.provenance_refs)
        if not provenance:
            raise ValueError("target evidence requires provenance")
        if any(item.source_ref != self.source_ref for item in provenance):
            raise ValueError("target evidence provenance must bind the same source_ref")
        if self.source_sha256 is not None and any(
            item.source_sha256 != self.source_sha256 for item in provenance
        ):
            raise ValueError("target evidence provenance must bind source_sha256")
        object.__setattr__(self, "claim_keys", claim_keys)
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetEvidenceRef:
        data = _payload(payload, cls)
        return cls(
            evidence_id=data["evidence_id"],
            source_ref=data["source_ref"],
            tier=ReferenceEvidenceTier(data["tier"]),
            claim_scope=data["claim_scope"],
            source_sha256=data.get("source_sha256"),
            claim_keys=_sequence(data["claim_keys"], "claim_keys"),
            provenance_refs=tuple(
                _strict_provenance_ref(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
        )


@dataclass(frozen=True, slots=True)
class TemporalTransformation(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_temporal_transformation_v1"

    transformation_id: str
    source_state: str
    destination_state: str
    temporal_window: str
    continuity_requirement: str

    def __post_init__(self) -> None:
        for field_name in (
            "transformation_id",
            "source_state",
            "destination_state",
            "temporal_window",
            "continuity_requirement",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TemporalTransformation:
        data = _payload(payload, cls)
        return cls(
            transformation_id=data["transformation_id"],
            source_state=data["source_state"],
            destination_state=data["destination_state"],
            temporal_window=data["temporal_window"],
            continuity_requirement=data["continuity_requirement"],
        )


def _unique_records(
    values: Iterable[Any],
    *,
    expected_type: type[Any],
    id_attribute: str,
    field_name: str,
) -> tuple[Any, ...]:
    by_id: dict[str, Any] = {}
    for value in values:
        if not isinstance(value, expected_type):
            raise TypeError(f"{field_name} must contain {expected_type.__name__} values")
        identifier = cast(str, getattr(value, id_attribute))
        previous = by_id.get(identifier)
        if previous is not None:
            if previous != value:
                raise ValueError(f"{field_name} has conflicting ID {identifier!r}")
            raise ValueError(f"{field_name} must contain unique IDs")
        by_id[identifier] = value
    return tuple(sorted(by_id.values(), key=lambda item: item.content_sha256))


def _provenance_refs(values: Iterable[ProvenanceRef]) -> tuple[ProvenanceRef, ...]:
    return cast(
        tuple[ProvenanceRef, ...],
        _unique_records(
            values,
            expected_type=ProvenanceRef,
            id_attribute="provenance_id",
            field_name="provenance_refs",
        ),
    )


@dataclass(frozen=True, slots=True)
class TargetBrief(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_brief_v2"

    request_id: str
    mode: TargetMode
    subject: str | None
    named_references: tuple[str, ...]
    family_neighborhoods: tuple[str, ...]
    abstraction_level: AbstractionLevel
    expression_terms: tuple[str, ...]
    exclusions: tuple[str, ...]
    protected_recognizers: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    transformations: tuple[TemporalTransformation, ...]
    temporal_requests: tuple[str, ...]
    matrix_context: str | None
    criterion_vocabulary: tuple[str, ...]
    reference_evidence: tuple[TargetEvidenceRef, ...]
    provenance_refs: tuple[ProvenanceRef, ...]
    request_source: TargetRequestSource | None = None
    branches: tuple[TargetBranch, ...] = ()
    conflicts: tuple[TargetConflict, ...] = ()
    unknowns: tuple[TargetUnknown, ...] = ()
    acceptance: TargetAcceptance | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _identifier(self.request_id, "request_id"))
        object.__setattr__(self, "mode", TargetMode(self.mode))
        object.__setattr__(self, "subject", _optional_text(self.subject, "subject"))
        object.__setattr__(
            self,
            "named_references",
            _text_tuple(self.named_references, "named_references"),
        )
        object.__setattr__(
            self,
            "family_neighborhoods",
            _text_tuple(self.family_neighborhoods, "family_neighborhoods"),
        )
        object.__setattr__(
            self,
            "abstraction_level",
            AbstractionLevel(self.abstraction_level),
        )
        for field_name in (
            "expression_terms",
            "exclusions",
            "protected_recognizers",
            "forbidden_drift",
            "temporal_requests",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "criterion_vocabulary",
            _text_tuple(
                self.criterion_vocabulary,
                "criterion_vocabulary",
                reject_aggregates=True,
            ),
        )
        object.__setattr__(
            self,
            "transformations",
            cast(
                tuple[TemporalTransformation, ...],
                _unique_records(
                    self.transformations,
                    expected_type=TemporalTransformation,
                    id_attribute="transformation_id",
                    field_name="transformations",
                ),
            ),
        )
        object.__setattr__(
            self,
            "reference_evidence",
            cast(
                tuple[TargetEvidenceRef, ...],
                _unique_records(
                    self.reference_evidence,
                    expected_type=TargetEvidenceRef,
                    id_attribute="evidence_id",
                    field_name="reference_evidence",
                ),
            ),
        )
        object.__setattr__(
            self,
            "matrix_context",
            _optional_text(self.matrix_context, "matrix_context"),
        )
        provenance = _provenance_refs(self.provenance_refs)
        if not provenance:
            raise ValueError("target brief requires provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        if self.request_source is not None and not isinstance(
            self.request_source,
            TargetRequestSource,
        ):
            raise TypeError("request_source must be a TargetRequestSource or None")
        branches = cast(
            tuple[TargetBranch, ...],
            _unique_records(
                self.branches,
                expected_type=TargetBranch,
                id_attribute="branch_id",
                field_name="branches",
            ),
        )
        conflicts = cast(
            tuple[TargetConflict, ...],
            _unique_records(
                self.conflicts,
                expected_type=TargetConflict,
                id_attribute="conflict_id",
                field_name="conflicts",
            ),
        )
        unknowns = cast(
            tuple[TargetUnknown, ...],
            _unique_records(
                self.unknowns,
                expected_type=TargetUnknown,
                id_attribute="unknown_id",
                field_name="unknowns",
            ),
        )
        if self.acceptance is not None and not isinstance(
            self.acceptance,
            TargetAcceptance,
        ):
            raise TypeError("acceptance must be a TargetAcceptance or None")

        evidence_ids = {item.evidence_id for item in self.reference_evidence}
        branch_ids = {item.branch_id for item in branches}
        for branch in branches:
            unsupported = sorted(set(branch.claim_keys) - _TARGET_CLAIM_KEYS)
            if unsupported:
                raise ValueError(
                    f"branch {branch.branch_id!r} has unsupported claim_keys: "
                    + ", ".join(unsupported)
                )
            dangling = sorted(set(branch.evidence_ids) - evidence_ids)
            if dangling:
                raise ValueError(
                    f"branch {branch.branch_id!r} references unknown evidence: "
                    + ", ".join(dangling)
                )
        for conflict in conflicts:
            dangling_branches = sorted(set(conflict.branch_ids) - branch_ids)
            if dangling_branches:
                raise ValueError(
                    f"conflict {conflict.conflict_id!r} references unknown branches: "
                    + ", ".join(dangling_branches)
                )
            dangling_evidence = sorted(set(conflict.evidence_ids) - evidence_ids)
            if dangling_evidence:
                raise ValueError(
                    f"conflict {conflict.conflict_id!r} references unknown evidence: "
                    + ", ".join(dangling_evidence)
                )
        for unknown in unknowns:
            dangling = sorted(set(unknown.evidence_ids) - evidence_ids)
            if dangling:
                raise ValueError(
                    f"unknown {unknown.unknown_id!r} references unknown evidence: "
                    + ", ".join(dangling)
                )
        if self.acceptance is not None:
            dangling = sorted(
                set(self.acceptance.accepted_branch_ids) - branch_ids
            )
            if dangling:
                raise ValueError(
                    "acceptance references unknown branches: " + ", ".join(dangling)
                )
        object.__setattr__(self, "branches", branches)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "unknowns", unknowns)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetBrief:
        data = _payload(payload, cls)
        return cls(
            request_id=data["request_id"],
            mode=TargetMode(data["mode"]),
            subject=data.get("subject"),
            named_references=_sequence(data["named_references"], "named_references"),
            family_neighborhoods=_sequence(
                data["family_neighborhoods"],
                "family_neighborhoods",
            ),
            abstraction_level=AbstractionLevel(data["abstraction_level"]),
            expression_terms=_sequence(data["expression_terms"], "expression_terms"),
            exclusions=_sequence(data["exclusions"], "exclusions"),
            protected_recognizers=_sequence(
                data["protected_recognizers"],
                "protected_recognizers",
            ),
            forbidden_drift=_sequence(data["forbidden_drift"], "forbidden_drift"),
            transformations=tuple(
                TemporalTransformation.from_dict(item)
                for item in _sequence(data["transformations"], "transformations")
            ),
            temporal_requests=_sequence(data["temporal_requests"], "temporal_requests"),
            matrix_context=data.get("matrix_context"),
            criterion_vocabulary=_sequence(
                data["criterion_vocabulary"],
                "criterion_vocabulary",
            ),
            reference_evidence=tuple(
                TargetEvidenceRef.from_dict(item)
                for item in _sequence(
                    data["reference_evidence"],
                    "reference_evidence",
                )
            ),
            provenance_refs=tuple(
                _strict_provenance_ref(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
            request_source=(
                TargetRequestSource.from_dict(data["request_source"])
                if isinstance(data["request_source"], Mapping)
                else None
                if data["request_source"] is None
                else _raise_type("request_source must be a mapping or null")
            ),
            branches=tuple(
                TargetBranch.from_dict(item)
                for item in _sequence(data["branches"], "branches")
            ),
            conflicts=tuple(
                TargetConflict.from_dict(item)
                for item in _sequence(data["conflicts"], "conflicts")
            ),
            unknowns=tuple(
                TargetUnknown.from_dict(item)
                for item in _sequence(data["unknowns"], "unknowns")
            ),
            acceptance=(
                TargetAcceptance.from_dict(data["acceptance"])
                if isinstance(data["acceptance"], Mapping)
                else None
                if data["acceptance"] is None
                else _raise_type("acceptance must be a mapping or null")
            ),
        )


@dataclass(frozen=True, slots=True)
class IdealTargetId(_CanonicalTargetRecord):
    SCHEMA_VERSION = "ideal_target_id_v1"

    digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "digest", _sha256_digest(self.digest, "digest"))

    @property
    def value(self) -> str:
        return f"ideal-target/{self.digest}"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IdealTargetId:
        data = _payload(payload, cls)
        return cls(digest=data["digest"])


def _resolution_fields(
    *,
    mode: TargetMode,
    subject: str | None,
    named_references: tuple[str, ...],
    family_neighborhoods: tuple[str, ...],
    abstraction_level: AbstractionLevel,
    expression_terms: tuple[str, ...],
    exclusions: tuple[str, ...],
    protected_recognizers: tuple[str, ...],
    forbidden_drift: tuple[str, ...],
    transformations: tuple[TemporalTransformation, ...],
    temporal_requests: tuple[str, ...],
    matrix_context: str | None,
    criterion_vocabulary: tuple[str, ...],
    reference_evidence: tuple[TargetEvidenceRef, ...],
    request_source: TargetRequestSource | None,
    branches: tuple[TargetBranch, ...],
    conflicts: tuple[TargetConflict, ...],
    unknowns: tuple[TargetUnknown, ...],
    acceptance: TargetAcceptance | None,
) -> tuple[TargetResolution, tuple[str, ...]]:
    missing: set[str] = set()
    critical: set[str] = set()

    if subject is None:
        missing.add("target_identity")
        critical.add("target_identity")
    if mode in {TargetMode.NAMED_REFERENCE, TargetMode.HYBRID}:
        if not named_references:
            missing.add("named_references")
            critical.add("named_references")
        if not reference_evidence:
            missing.add("reference_evidence")
    if mode is TargetMode.HYBRID and not expression_terms:
        missing.add("expression_terms")
        critical.add("expression_terms")
    if mode is TargetMode.CONCEPT_ONLY and subject is None and not expression_terms:
        missing.add("target_identity")
        critical.add("target_identity")
    if mode is TargetMode.FAMILY_ARCHITECTURE and not family_neighborhoods:
        missing.add("family_neighborhoods")
        critical.add("family_neighborhoods")
    if abstraction_level is AbstractionLevel.UNSPECIFIED:
        missing.add("abstraction_level")
    if not exclusions:
        missing.add("exclusions")
    if not protected_recognizers:
        missing.add("protected_recognizers")
    if not forbidden_drift:
        missing.add("forbidden_drift")
    if not transformations:
        missing.add("transformations")
    if not temporal_requests:
        missing.add("temporal_requests")
    if matrix_context is None:
        missing.add("matrix_context")
    if not criterion_vocabulary:
        missing.add("criterion_vocabulary")
    if request_source is None:
        missing.add("request_source")
        critical.add("request_source")
    if not branches:
        missing.add("branches")
        critical.add("branches")

    accepted_branch_ids: set[str] = set()
    if acceptance is None or acceptance.state is not TargetAcceptanceState.ACCEPTED:
        missing.add("target_acceptance")
    else:
        accepted_branch_ids.update(acceptance.accepted_branch_ids)
    for conflict in conflicts:
        selected = accepted_branch_ids.intersection(conflict.branch_ids)
        if len(selected) != 1:
            field_name = f"conflict:{conflict.conflict_id}"
            missing.add(field_name)
            critical.add(field_name)
    for unknown in unknowns:
        field_name = f"unknown:{unknown.field_key}"
        missing.add(field_name)
        if unknown.critical:
            critical.add(field_name)

    if critical:
        resolution = TargetResolution.UNRESOLVED_HOLD
    elif missing:
        resolution = TargetResolution.PARTIAL_HOLD
    else:
        resolution = TargetResolution.RESOLVED_FOR_DESIGN
    return resolution, tuple(sorted(missing))


def _identity_payload(
    *,
    mode: TargetMode,
    subject: str | None,
    named_references: tuple[str, ...],
    family_neighborhoods: tuple[str, ...],
    abstraction_level: AbstractionLevel,
    expression_terms: tuple[str, ...],
    exclusions: tuple[str, ...],
    protected_recognizers: tuple[str, ...],
    forbidden_drift: tuple[str, ...],
    transformations: tuple[TemporalTransformation, ...],
    temporal_requests: tuple[str, ...],
    matrix_context: str | None,
    criterion_vocabulary: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": "ideal_target_semantic_payload_v2",
        "mode": mode,
        "subject": subject,
        "named_references": named_references,
        "family_neighborhoods": family_neighborhoods,
        "abstraction_level": abstraction_level,
        "expression_terms": expression_terms,
        "exclusions": exclusions,
        "protected_recognizers": protected_recognizers,
        "forbidden_drift": forbidden_drift,
        "transformations": transformations,
        "temporal_requests": temporal_requests,
        "matrix_context": matrix_context,
        "criterion_vocabulary": criterion_vocabulary,
    }


def _intent_receipt_payload(
    *,
    ideal_target_id: IdealTargetId,
    brief: TargetBrief,
    resolution: TargetResolution,
    unresolved_fields: tuple[str, ...],
    authority_flags: TargetAuthorityFlags,
) -> dict[str, Any]:
    return {
        "schema_version": "target_intent_receipt_payload_v2",
        "ideal_target_id": ideal_target_id,
        **{
            item.name: getattr(brief, item.name)
            for item in fields(brief)
        },
        "resolution": resolution,
        "unresolved_fields": unresolved_fields,
        "authority_flags": authority_flags,
    }


@dataclass(frozen=True, slots=True)
class TargetIntent(_CanonicalTargetRecord):
    SCHEMA_VERSION = "target_intent_v2"

    ideal_target_id: IdealTargetId
    request_id: str
    mode: TargetMode
    subject: str | None
    named_references: tuple[str, ...]
    family_neighborhoods: tuple[str, ...]
    abstraction_level: AbstractionLevel
    expression_terms: tuple[str, ...]
    exclusions: tuple[str, ...]
    protected_recognizers: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    transformations: tuple[TemporalTransformation, ...]
    temporal_requests: tuple[str, ...]
    matrix_context: str | None
    criterion_vocabulary: tuple[str, ...]
    reference_evidence: tuple[TargetEvidenceRef, ...]
    provenance_refs: tuple[ProvenanceRef, ...]
    request_source: TargetRequestSource | None
    branches: tuple[TargetBranch, ...]
    conflicts: tuple[TargetConflict, ...]
    unknowns: tuple[TargetUnknown, ...]
    acceptance: TargetAcceptance | None
    resolution: TargetResolution
    unresolved_fields: tuple[str, ...]
    receipt_sha256: str
    authority_flags: TargetAuthorityFlags = TargetAuthorityFlags()

    def __post_init__(self) -> None:
        if not isinstance(self.ideal_target_id, IdealTargetId):
            raise TypeError("ideal_target_id must be an IdealTargetId")
        if not isinstance(self.authority_flags, TargetAuthorityFlags):
            raise TypeError("authority_flags must be TargetAuthorityFlags")
        normalized = TargetBrief(
            request_id=self.request_id,
            mode=self.mode,
            subject=self.subject,
            named_references=self.named_references,
            family_neighborhoods=self.family_neighborhoods,
            abstraction_level=self.abstraction_level,
            expression_terms=self.expression_terms,
            exclusions=self.exclusions,
            protected_recognizers=self.protected_recognizers,
            forbidden_drift=self.forbidden_drift,
            transformations=self.transformations,
            temporal_requests=self.temporal_requests,
            matrix_context=self.matrix_context,
            criterion_vocabulary=self.criterion_vocabulary,
            reference_evidence=self.reference_evidence,
            provenance_refs=self.provenance_refs,
            request_source=self.request_source,
            branches=self.branches,
            conflicts=self.conflicts,
            unknowns=self.unknowns,
            acceptance=self.acceptance,
        )
        for item in fields(normalized):
            object.__setattr__(self, item.name, getattr(normalized, item.name))

        expected_resolution, expected_unknowns = _resolution_fields(
            mode=normalized.mode,
            subject=normalized.subject,
            named_references=normalized.named_references,
            family_neighborhoods=normalized.family_neighborhoods,
            abstraction_level=normalized.abstraction_level,
            expression_terms=normalized.expression_terms,
            exclusions=normalized.exclusions,
            protected_recognizers=normalized.protected_recognizers,
            forbidden_drift=normalized.forbidden_drift,
            transformations=normalized.transformations,
            temporal_requests=normalized.temporal_requests,
            matrix_context=normalized.matrix_context,
            criterion_vocabulary=normalized.criterion_vocabulary,
            reference_evidence=normalized.reference_evidence,
            request_source=normalized.request_source,
            branches=normalized.branches,
            conflicts=normalized.conflicts,
            unknowns=normalized.unknowns,
            acceptance=normalized.acceptance,
        )
        if TargetResolution(self.resolution) is not expected_resolution:
            raise ValueError("resolution does not match fail-closed target state")
        supplied_unknowns = _text_tuple(self.unresolved_fields, "unresolved_fields")
        if supplied_unknowns != expected_unknowns:
            raise ValueError("unresolved_fields do not match fail-closed target state")
        object.__setattr__(self, "resolution", expected_resolution)
        object.__setattr__(self, "unresolved_fields", expected_unknowns)

        payload = _identity_payload(
            mode=normalized.mode,
            subject=normalized.subject,
            named_references=normalized.named_references,
            family_neighborhoods=normalized.family_neighborhoods,
            abstraction_level=normalized.abstraction_level,
            expression_terms=normalized.expression_terms,
            exclusions=normalized.exclusions,
            protected_recognizers=normalized.protected_recognizers,
            forbidden_drift=normalized.forbidden_drift,
            transformations=normalized.transformations,
            temporal_requests=normalized.temporal_requests,
            matrix_context=normalized.matrix_context,
            criterion_vocabulary=normalized.criterion_vocabulary,
        )
        expected_digest = sha256(_canonical_json_bytes(payload)).hexdigest()
        if self.ideal_target_id.digest != expected_digest:
            raise ValueError("ideal_target_id does not match target content")
        supplied_receipt = _sha256_digest(self.receipt_sha256, "receipt_sha256")
        expected_receipt = sha256(
            _canonical_json_bytes(
                _intent_receipt_payload(
                    ideal_target_id=self.ideal_target_id,
                    brief=normalized,
                    resolution=expected_resolution,
                    unresolved_fields=expected_unknowns,
                    authority_flags=self.authority_flags,
                )
            )
        ).hexdigest()
        if supplied_receipt != expected_receipt:
            raise ValueError("receipt_sha256 does not match exact target receipt")
        object.__setattr__(self, "receipt_sha256", supplied_receipt)

    @property
    def semantic_target_sha256(self) -> str:
        return self.ideal_target_id.digest

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetIntent:
        data = _payload(payload, cls)
        return cls(
            ideal_target_id=IdealTargetId.from_dict(data["ideal_target_id"]),
            request_id=data["request_id"],
            mode=TargetMode(data["mode"]),
            subject=data.get("subject"),
            named_references=_sequence(data["named_references"], "named_references"),
            family_neighborhoods=_sequence(
                data["family_neighborhoods"],
                "family_neighborhoods",
            ),
            abstraction_level=AbstractionLevel(data["abstraction_level"]),
            expression_terms=_sequence(data["expression_terms"], "expression_terms"),
            exclusions=_sequence(data["exclusions"], "exclusions"),
            protected_recognizers=_sequence(
                data["protected_recognizers"],
                "protected_recognizers",
            ),
            forbidden_drift=_sequence(data["forbidden_drift"], "forbidden_drift"),
            transformations=tuple(
                TemporalTransformation.from_dict(item)
                for item in _sequence(data["transformations"], "transformations")
            ),
            temporal_requests=_sequence(data["temporal_requests"], "temporal_requests"),
            matrix_context=data.get("matrix_context"),
            criterion_vocabulary=_sequence(
                data["criterion_vocabulary"],
                "criterion_vocabulary",
            ),
            reference_evidence=tuple(
                TargetEvidenceRef.from_dict(item)
                for item in _sequence(
                    data["reference_evidence"],
                    "reference_evidence",
                )
            ),
            provenance_refs=tuple(
                _strict_provenance_ref(item)
                for item in _sequence(data["provenance_refs"], "provenance_refs")
            ),
            request_source=(
                TargetRequestSource.from_dict(data["request_source"])
                if isinstance(data["request_source"], Mapping)
                else None
                if data["request_source"] is None
                else _raise_type("request_source must be a mapping or null")
            ),
            branches=tuple(
                TargetBranch.from_dict(item)
                for item in _sequence(data["branches"], "branches")
            ),
            conflicts=tuple(
                TargetConflict.from_dict(item)
                for item in _sequence(data["conflicts"], "conflicts")
            ),
            unknowns=tuple(
                TargetUnknown.from_dict(item)
                for item in _sequence(data["unknowns"], "unknowns")
            ),
            acceptance=(
                TargetAcceptance.from_dict(data["acceptance"])
                if isinstance(data["acceptance"], Mapping)
                else None
                if data["acceptance"] is None
                else _raise_type("acceptance must be a mapping or null")
            ),
            resolution=TargetResolution(data["resolution"]),
            unresolved_fields=_sequence(
                data["unresolved_fields"],
                "unresolved_fields",
            ),
            receipt_sha256=data["receipt_sha256"],
            authority_flags=TargetAuthorityFlags.from_dict(data["authority_flags"]),
        )

    def to_plane_assessment(self) -> PlaneAssessment:
        provenance = self.provenance_refs
        evidence_by_id = {item.evidence_id: item for item in self.reference_evidence}
        evidence_by_claim_key: dict[str, tuple[ProvenanceRef, ...]] = {}
        for evidence in self.reference_evidence:
            for claim_key in evidence.claim_keys:
                evidence_by_claim_key[claim_key] = _provenance_refs(
                    (
                        *evidence_by_claim_key.get(claim_key, ()),
                        *evidence.provenance_refs,
                    )
                )
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
            claim_id = f"target-{len(claims) + 1:02d}-{_slug(claim_key)}"
            claims.append(
                ScopedClaim(
                    claim_id=claim_id,
                    claim_key=claim_key,
                    claim_value=claim_value,
                    claim_kind=claim_kind,
                    authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                    provenance_refs=_provenance_refs(
                        (*provenance, *evidence_by_claim_key.get(claim_key, ()))
                    ),
                    cardinality=cardinality,
                    member_id=member_id,
                    order_index=order_index,
                )
            )

        if self.subject is not None:
            add_claim("target_identity", self.subject, ClaimKind.REQUIREMENT)
        for index, value in enumerate(self.named_references):
            add_claim(
                "named_reference",
                value,
                ClaimKind.REQUIREMENT,
                cardinality=ClaimCardinality.ORDERED_MEMBER,
                member_id=f"named-reference-{_slug(value)}",
                order_index=index,
            )
        for value in self.family_neighborhoods:
            add_claim(
                "family_neighborhood",
                value,
                ClaimKind.HYPOTHESIS,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"family-neighborhood-{_slug(value)}",
            )
        for value in self.expression_terms:
            add_claim(
                "expression",
                value,
                ClaimKind.REQUIREMENT,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"expression-{_slug(value)}",
            )
        for value in self.protected_recognizers:
            add_claim(
                "protected_recognizer",
                value,
                ClaimKind.REQUIREMENT,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"protected-recognizer-{_slug(value)}",
            )
        for value in self.exclusions:
            add_claim(
                "exclusion",
                value,
                ClaimKind.PROHIBITION,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"exclusion-{_slug(value)}",
            )
        for value in self.forbidden_drift:
            add_claim(
                "forbidden_drift",
                value,
                ClaimKind.PROHIBITION,
                cardinality=ClaimCardinality.SET_MEMBER,
                member_id=f"forbidden-drift-{_slug(value)}",
            )
        for index, transformation in enumerate(self.transformations):
            transformation_value = (
                f"{transformation.source_state} -> "
                f"{transformation.destination_state} during "
                f"{transformation.temporal_window}; preserve "
                f"{transformation.continuity_requirement}"
            )
            add_claim(
                "temporal_transformation",
                transformation_value,
                ClaimKind.HYPOTHESIS,
                cardinality=ClaimCardinality.ORDERED_MEMBER,
                member_id=f"temporal-transformation-{_slug(transformation_value)}",
                order_index=index,
            )
        add_claim("target_resolution", self.resolution.value, ClaimKind.DIAGNOSTIC)

        declared_unknowns = tuple(
            UnknownFact(
                unknown_id=item.unknown_id,
                field_key=item.field_key,
                reason=item.reason,
                needed_evidence=item.needed_evidence,
                provenance_refs=_provenance_refs(
                    (
                        *provenance,
                        *(
                            source_provenance
                            for evidence_id in item.evidence_ids
                            for source_provenance in evidence_by_id[
                                evidence_id
                            ].provenance_refs
                        ),
                    )
                ),
            )
            for item in self.unknowns
        )
        unresolved_unknowns = tuple(
            UnknownFact(
                unknown_id=f"target-field-{_slug(field_name)}",
                field_key=field_name,
                reason="explicit target field is unresolved; no generic fallback is allowed",
                needed_evidence=f"a target-specific declaration for {field_name}",
                provenance_refs=provenance,
            )
            for field_name in self.unresolved_fields
        )
        authority_unknowns = tuple(
            UnknownFact(
                unknown_id=f"target-authority-{field_name}",
                field_key=field_name,
                reason="target compilation is structural and cannot observe this endpoint",
                needed_evidence=evidence,
                provenance_refs=provenance,
            )
            for field_name, evidence in (
                ("observed_target_fidelity", "scoped blinded human comparison"),
                ("observed_smell", "direct sensory observation at exact conditions"),
                ("scoped_liking", "participant-linked criterion-specific preference data"),
                ("physical_performance", "condition-bound physical measurement"),
                ("safety", "current exact-formula safety assessment"),
                ("stability", "current exact-formula stability evidence"),
                ("release", "all required independent release evidence"),
            )
        )
        unknowns = (*declared_unknowns, *unresolved_unknowns, *authority_unknowns)

        branches_by_id = {item.branch_id: item for item in self.branches}
        plane_conflicts = tuple(
            PlaneConflict(
                conflict_id=item.conflict_id,
                claim_key=item.claim_key,
                alternatives=tuple(
                    branches_by_id[branch_id].interpretation
                    for branch_id in item.branch_ids
                ),
                reason=item.reason,
                claim_ids=tuple(
                    claim.claim_id
                    for claim in claims
                    if claim.claim_key == item.claim_key
                ),
                provenance_refs=_provenance_refs(
                    (
                        *provenance,
                        *(
                            source_provenance
                            for evidence_id in item.evidence_ids
                            for source_provenance in evidence_by_id[
                                evidence_id
                            ].provenance_refs
                        ),
                    )
                ),
            )
            for item in self.conflicts
        )

        criteria = tuple(
            ParetoCriterion(
                criterion_id=_slug(value),
                direction=CriterionDirection.PRESERVE,
                value=CriterionValue.unknown(
                    "target criterion declared but no candidate observation exists"
                ),
                unit="criterion-specific observation",
                authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
                provenance_refs=provenance,
            )
            for value in self.criterion_vocabulary
        )
        temporal_scope = (
            "multi-window-request"
            if len(self.temporal_requests) > 1
            else _slug(self.temporal_requests[0])
            if self.temporal_requests
            else "unspecified-temporal-scope"
        )
        matrix_scope = (
            _slug(self.matrix_context)
            if self.matrix_context is not None
            else "unspecified-matrix-scope"
        )
        return PlaneAssessment(
            assessment_id=f"target-compiler/{self.ideal_target_id.digest}",
            module_id="target-compiler-v1",
            plane_id=PlaneId.IDENTITY,
            scope=AssessmentScope(
                target_scope=self.ideal_target_id.value,
                temporal_scope=temporal_scope,
                matrix_scope=matrix_scope,
            ),
            claims=tuple(claims),
            support_intervals=(),
            conflicts=plane_conflicts,
            unknowns=tuple(unknowns),
            failure_modes=(
                "unresolved explicit target",
                "generic family substitution",
                "inventory rewrites ideal target",
                "numerical score displaces named identity",
            ),
            proposed_experiments=tuple(
                f"resolve target field with target-specific evidence: {field_name}"
                for field_name in self.unresolved_fields
            ),
            provenance_refs=provenance,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            freshness_hashes=(
                self.ideal_target_id.digest,
                self.receipt_sha256,
                *(
                    (self.request_source.source_sha256,)
                    if self.request_source is not None
                    else ()
                ),
                *(
                    item.source_sha256
                    for item in self.reference_evidence
                    if item.source_sha256 is not None
                ),
            ),
            native_criteria=criteria,
        )


@dataclass(frozen=True, slots=True)
class BuildProjectionId(_CanonicalTargetRecord):
    """Inventory-bound build identity that cannot alter its ideal target."""

    SCHEMA_VERSION = "build_projection_id_v1"

    projection_id: str
    ideal_target_id: IdealTargetId
    inventory_content_sha256: str
    stock_authority_snapshot_id: str
    projection_variant: str
    authority_flags: TargetAuthorityFlags = TargetAuthorityFlags()

    def __post_init__(self) -> None:
        if not isinstance(self.ideal_target_id, IdealTargetId):
            raise TypeError("ideal_target_id must be an IdealTargetId")
        if not isinstance(self.authority_flags, TargetAuthorityFlags):
            raise TypeError("authority_flags must be TargetAuthorityFlags")
        object.__setattr__(
            self,
            "inventory_content_sha256",
            _sha256_digest(self.inventory_content_sha256, "inventory_content_sha256"),
        )
        object.__setattr__(
            self,
            "stock_authority_snapshot_id",
            _identifier(self.stock_authority_snapshot_id, "stock_authority_snapshot_id"),
        )
        object.__setattr__(
            self,
            "projection_variant",
            _text(self.projection_variant, "projection_variant"),
        )
        expected = _projection_digest(
            self.ideal_target_id,
            self.inventory_content_sha256,
            self.stock_authority_snapshot_id,
            self.projection_variant,
        )
        supplied = _text(self.projection_id, "projection_id")
        if supplied != f"build-projection/{expected}":
            raise ValueError("projection_id does not match projection content")
        object.__setattr__(self, "projection_id", supplied)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BuildProjectionId:
        data = _payload(payload, cls)
        return cls(
            projection_id=data["projection_id"],
            ideal_target_id=IdealTargetId.from_dict(data["ideal_target_id"]),
            inventory_content_sha256=data["inventory_content_sha256"],
            stock_authority_snapshot_id=data["stock_authority_snapshot_id"],
            projection_variant=data["projection_variant"],
            authority_flags=TargetAuthorityFlags.from_dict(data["authority_flags"]),
        )


def _projection_digest(
    ideal_target_id: IdealTargetId,
    inventory_content_sha256: str,
    stock_authority_snapshot_id: str,
    projection_variant: str,
) -> str:
    return sha256(
        _canonical_json_bytes(
            {
                "schema_version": "build_projection_identity_payload_v1",
                "ideal_target_id": ideal_target_id,
                "inventory_content_sha256": inventory_content_sha256,
                "stock_authority_snapshot_id": stock_authority_snapshot_id,
                "projection_variant": projection_variant,
            }
        )
    ).hexdigest()


def compile_target_intent(brief: TargetBrief) -> TargetIntent:
    """Compile a normalized target without consulting or mutating inventory."""

    if not isinstance(brief, TargetBrief):
        raise TypeError("brief must be a TargetBrief")
    resolution, unresolved_fields = _resolution_fields(
        mode=brief.mode,
        subject=brief.subject,
        named_references=brief.named_references,
        family_neighborhoods=brief.family_neighborhoods,
        abstraction_level=brief.abstraction_level,
        expression_terms=brief.expression_terms,
        exclusions=brief.exclusions,
        protected_recognizers=brief.protected_recognizers,
        forbidden_drift=brief.forbidden_drift,
        transformations=brief.transformations,
        temporal_requests=brief.temporal_requests,
        matrix_context=brief.matrix_context,
        criterion_vocabulary=brief.criterion_vocabulary,
        reference_evidence=brief.reference_evidence,
        request_source=brief.request_source,
        branches=brief.branches,
        conflicts=brief.conflicts,
        unknowns=brief.unknowns,
        acceptance=brief.acceptance,
    )
    identity_payload = _identity_payload(
        mode=brief.mode,
        subject=brief.subject,
        named_references=brief.named_references,
        family_neighborhoods=brief.family_neighborhoods,
        abstraction_level=brief.abstraction_level,
        expression_terms=brief.expression_terms,
        exclusions=brief.exclusions,
        protected_recognizers=brief.protected_recognizers,
        forbidden_drift=brief.forbidden_drift,
        transformations=brief.transformations,
        temporal_requests=brief.temporal_requests,
        matrix_context=brief.matrix_context,
        criterion_vocabulary=brief.criterion_vocabulary,
    )
    ideal_target_id = IdealTargetId(
        sha256(_canonical_json_bytes(identity_payload)).hexdigest()
    )
    authority_flags = TargetAuthorityFlags()
    receipt_sha256 = sha256(
        _canonical_json_bytes(
            _intent_receipt_payload(
                ideal_target_id=ideal_target_id,
                brief=brief,
                resolution=resolution,
                unresolved_fields=unresolved_fields,
                authority_flags=authority_flags,
            )
        )
    ).hexdigest()
    return TargetIntent(
        ideal_target_id=ideal_target_id,
        request_id=brief.request_id,
        mode=brief.mode,
        subject=brief.subject,
        named_references=brief.named_references,
        family_neighborhoods=brief.family_neighborhoods,
        abstraction_level=brief.abstraction_level,
        expression_terms=brief.expression_terms,
        exclusions=brief.exclusions,
        protected_recognizers=brief.protected_recognizers,
        forbidden_drift=brief.forbidden_drift,
        transformations=brief.transformations,
        temporal_requests=brief.temporal_requests,
        matrix_context=brief.matrix_context,
        criterion_vocabulary=brief.criterion_vocabulary,
        reference_evidence=brief.reference_evidence,
        provenance_refs=brief.provenance_refs,
        request_source=brief.request_source,
        branches=brief.branches,
        conflicts=brief.conflicts,
        unknowns=brief.unknowns,
        acceptance=brief.acceptance,
        resolution=resolution,
        unresolved_fields=unresolved_fields,
        receipt_sha256=receipt_sha256,
        authority_flags=authority_flags,
    )


def create_build_projection_id(
    intent: TargetIntent,
    *,
    inventory_content_sha256: str,
    stock_authority_snapshot_id: str,
    projection_variant: str,
) -> BuildProjectionId:
    """Bind a build projection to inventory without changing target identity."""

    if not isinstance(intent, TargetIntent):
        raise TypeError("intent must be a TargetIntent")
    inventory_digest = _sha256_digest(
        inventory_content_sha256,
        "inventory_content_sha256",
    )
    authority_id = _identifier(
        stock_authority_snapshot_id,
        "stock_authority_snapshot_id",
    )
    variant = _text(projection_variant, "projection_variant")
    digest = _projection_digest(
        intent.ideal_target_id,
        inventory_digest,
        authority_id,
        variant,
    )
    return BuildProjectionId(
        projection_id=f"build-projection/{digest}",
        ideal_target_id=intent.ideal_target_id,
        inventory_content_sha256=inventory_digest,
        stock_authority_snapshot_id=authority_id,
        projection_variant=variant,
    )


__all__ = [
    "AbstractionLevel",
    "BuildProjectionId",
    "IdealTargetId",
    "ReferenceEvidenceTier",
    "TargetAcceptance",
    "TargetAcceptanceState",
    "TargetAuthorityFlags",
    "TargetBranch",
    "TargetBrief",
    "TargetConflict",
    "TargetEvidenceRef",
    "TargetIntent",
    "TargetMode",
    "TargetRequestSource",
    "TargetResolution",
    "TargetSourceSpan",
    "TargetUnknown",
    "TemporalTransformation",
    "compile_target_intent",
    "create_build_projection_id",
]
