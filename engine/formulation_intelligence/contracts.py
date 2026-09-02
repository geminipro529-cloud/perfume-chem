"""Immutable structural contracts for multi-plane formulation intelligence.

The records in this module deliberately stop below perfume, sensory, safety, and
release authority.  Unit intervals are evidence-support bounds, not probabilities,
percent perceived contribution, hedonic scores, or observations of smell.
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

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RecordT = TypeVar("_RecordT", bound="_CanonicalRecord")


def _normalized_text(value: object, field_name: str, *, casefold: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if casefold else normalized


def _normalized_identifier(value: object, field_name: str) -> str:
    return _normalized_text(value, field_name, casefold=True)


def _normalized_text_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    allow_empty: bool = True,
    identifiers: bool = False,
) -> tuple[str, ...]:
    normalizer = _normalized_identifier if identifiers else _normalized_text
    normalized = tuple(normalizer(value, field_name) for value in values)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _unit_value(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_name} must be finite")
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{field_name} must be within [0, 1]")
    return normalized


def _finite_value(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field_name} must be finite")
    return normalized


def _sha256_digest(value: object, field_name: str) -> str:
    normalized = _normalized_text(value, field_name).casefold()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _CanonicalRecord):
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


def _payload(payload: Mapping[str, Any], schema_version: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("canonical payload must be a mapping")
    record_types = tuple(
        record_type
        for record_type in _CanonicalRecord.__subclasses__()
        if getattr(record_type, "SCHEMA_VERSION", None) == schema_version
    )
    field_sets = {
        frozenset(item.name for item in fields(cast(Any, record_type)))
        for record_type in record_types
    }
    if len(field_sets) != 1:
        raise RuntimeError(f"schema {schema_version!r} has no unique closed shape")
    expected_fields = {
        "schema_version",
        *next(iter(field_sets)),
    }
    received_fields = set(payload)
    if received_fields != expected_fields:
        missing = sorted(expected_fields - received_fields)
        extra = sorted(received_fields - expected_fields)
        raise ValueError(
            f"{schema_version} payload does not match the closed schema; "
            f"missing={missing!r}, extra={extra!r}"
        )
    declared = payload["schema_version"]
    if declared != schema_version:
        raise ValueError(
            f"schema_version must be {schema_version!r}, received {declared!r}"
        )
    return payload


class _CanonicalRecord:
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


class PlaneId(str, Enum):
    """The thirteen independent architectural planes in the design contract."""

    IDENTITY = "identity"
    MORPHOLOGY = "morphology"
    FUNCTION = "function"
    RELATION = "relation"
    MIXTURE = "mixture"
    TEMPORAL = "temporal"
    SPATIAL_COMPOSITION = "spatial_composition"
    PHYSICOCHEMICAL = "physicochemical"
    BIOLOGICAL_SENSITIVITY = "biological_sensitivity"
    HEDONIC = "hedonic"
    INVENTORY_BUILD = "inventory_build"
    EVIDENCE_AUTHORITY = "evidence_authority"
    EXPERIMENT = "experiment"


class AuthorityCeiling(str, Enum):
    """Ordered claim ceilings; none grants sensory, safety, or release authority."""

    WITHHELD = "withheld"
    STRUCTURAL_ONLY = "structural_only"
    HYPOTHESIS_ONLY = "hypothesis_only"
    DESIGN_ONLY = "design_only"
    EVIDENCE_LIMITED = "evidence_limited"

    @property
    def rank(self) -> int:
        return {
            AuthorityCeiling.WITHHELD: 0,
            AuthorityCeiling.STRUCTURAL_ONLY: 1,
            AuthorityCeiling.HYPOTHESIS_ONLY: 2,
            AuthorityCeiling.DESIGN_ONLY: 3,
            AuthorityCeiling.EVIDENCE_LIMITED: 4,
        }[self]

    @classmethod
    def minimum(cls, values: Iterable[AuthorityCeiling]) -> AuthorityCeiling:
        normalized = tuple(cls(value) for value in values)
        if not normalized:
            raise ValueError("at least one authority ceiling is required")
        result = normalized[0]
        for value in normalized[1:]:
            result = _AUTHORITY_MEET_TABLE[result][value]
        return result

    def is_no_stronger_than(self, ceiling: AuthorityCeiling) -> bool:
        """Check admission through the explicit meet, never through numeric rank."""

        admitted = AuthorityCeiling(ceiling)
        return AuthorityCeiling.minimum((self, admitted)) is self


# Composition is an explicit meet operation, not an inferred numeric score.  The
# current policy is conservative and happens to form a chain, but spelling out
# every pair makes future additions fail during import until their semantics are
# adjudicated rather than silently acquiring an order from ``rank``.
_AUTHORITY_MEET_TABLE: dict[
    AuthorityCeiling, dict[AuthorityCeiling, AuthorityCeiling]
] = {
    AuthorityCeiling.WITHHELD: {
        value: AuthorityCeiling.WITHHELD for value in AuthorityCeiling
    },
    AuthorityCeiling.STRUCTURAL_ONLY: {
        AuthorityCeiling.WITHHELD: AuthorityCeiling.WITHHELD,
        AuthorityCeiling.STRUCTURAL_ONLY: AuthorityCeiling.STRUCTURAL_ONLY,
        AuthorityCeiling.HYPOTHESIS_ONLY: AuthorityCeiling.STRUCTURAL_ONLY,
        AuthorityCeiling.DESIGN_ONLY: AuthorityCeiling.STRUCTURAL_ONLY,
        AuthorityCeiling.EVIDENCE_LIMITED: AuthorityCeiling.STRUCTURAL_ONLY,
    },
    AuthorityCeiling.HYPOTHESIS_ONLY: {
        AuthorityCeiling.WITHHELD: AuthorityCeiling.WITHHELD,
        AuthorityCeiling.STRUCTURAL_ONLY: AuthorityCeiling.STRUCTURAL_ONLY,
        AuthorityCeiling.HYPOTHESIS_ONLY: AuthorityCeiling.HYPOTHESIS_ONLY,
        AuthorityCeiling.DESIGN_ONLY: AuthorityCeiling.HYPOTHESIS_ONLY,
        AuthorityCeiling.EVIDENCE_LIMITED: AuthorityCeiling.HYPOTHESIS_ONLY,
    },
    AuthorityCeiling.DESIGN_ONLY: {
        AuthorityCeiling.WITHHELD: AuthorityCeiling.WITHHELD,
        AuthorityCeiling.STRUCTURAL_ONLY: AuthorityCeiling.STRUCTURAL_ONLY,
        AuthorityCeiling.HYPOTHESIS_ONLY: AuthorityCeiling.HYPOTHESIS_ONLY,
        AuthorityCeiling.DESIGN_ONLY: AuthorityCeiling.DESIGN_ONLY,
        AuthorityCeiling.EVIDENCE_LIMITED: AuthorityCeiling.DESIGN_ONLY,
    },
    AuthorityCeiling.EVIDENCE_LIMITED: {
        AuthorityCeiling.WITHHELD: AuthorityCeiling.WITHHELD,
        AuthorityCeiling.STRUCTURAL_ONLY: AuthorityCeiling.STRUCTURAL_ONLY,
        AuthorityCeiling.HYPOTHESIS_ONLY: AuthorityCeiling.HYPOTHESIS_ONLY,
        AuthorityCeiling.DESIGN_ONLY: AuthorityCeiling.DESIGN_ONLY,
        AuthorityCeiling.EVIDENCE_LIMITED: AuthorityCeiling.EVIDENCE_LIMITED,
    },
}


class EvidenceClass(str, Enum):
    DIRECT_OBSERVATION = "direct_observation"
    INSTRUMENTAL_OBSERVATION = "instrumental_observation"
    PRIMARY_SOURCE = "primary_source"
    OFFICIAL_RECORD = "official_record"
    COMPUTATIONAL_MODEL = "computational_model"
    HEURISTIC = "heuristic"
    HISTORICAL_PRIOR = "historical_prior"
    USER_REPORT = "user_report"
    UNKNOWN = "unknown"


class ClaimKind(str, Enum):
    REQUIREMENT = "requirement"
    PROHIBITION = "prohibition"
    HYPOTHESIS = "hypothesis"
    OBSERVATION = "observation"
    DIAGNOSTIC = "diagnostic"


class ClaimCardinality(str, Enum):
    """Whether a claim occupies one slot or is a member of a collection."""

    SINGLE = "single"
    SET_MEMBER = "set_member"
    ORDERED_MEMBER = "ordered_member"


class SupportMeasure(str, Enum):
    """The declared meaning of a support interval; values are never mixed."""

    EVIDENCE_SUPPORT = "evidence_support"
    DECLARATION_PRESENCE = "declaration_presence"


class CriterionDirection(str, Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"
    PRESERVE = "preserve"


class ValueState(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AssessmentScope(_CanonicalRecord):
    """Exact normalized target, temporal, and matrix key."""

    SCHEMA_VERSION = "assessment_scope_v1"

    target_scope: str
    temporal_scope: str
    matrix_scope: str

    def __post_init__(self) -> None:
        for field_name in ("target_scope", "temporal_scope", "matrix_scope"):
            object.__setattr__(
                self,
                field_name,
                _normalized_identifier(getattr(self, field_name), field_name),
            )

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.target_scope, self.temporal_scope, self.matrix_scope)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AssessmentScope:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            target_scope=data["target_scope"],
            temporal_scope=data["temporal_scope"],
            matrix_scope=data["matrix_scope"],
        )


@dataclass(frozen=True, slots=True)
class UnitInterval(_CanonicalRecord):
    """Closed unit interval with no implied probability semantics."""

    SCHEMA_VERSION = "unit_interval_v1"

    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = _unit_value(self.lower, "lower")
        upper = _unit_value(self.upper, "upper")
        if lower > upper:
            raise ValueError("lower must not exceed upper")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UnitInterval:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(lower=data["lower"], upper=data["upper"])


@dataclass(frozen=True, slots=True)
class ProvenanceRef(_CanonicalRecord):
    """One source reference and its declared independence/evidence class."""

    SCHEMA_VERSION = "plane_provenance_ref_v1"

    provenance_id: str
    source_ref: str
    evidence_class: EvidenceClass
    independence_key: str
    source_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provenance_id",
            _normalized_identifier(self.provenance_id, "provenance_id"),
        )
        object.__setattr__(
            self,
            "source_ref",
            _normalized_text(self.source_ref, "source_ref"),
        )
        object.__setattr__(self, "evidence_class", EvidenceClass(self.evidence_class))
        object.__setattr__(
            self,
            "independence_key",
            _normalized_identifier(self.independence_key, "independence_key"),
        )
        if self.source_sha256 is not None:
            object.__setattr__(
                self,
                "source_sha256",
                _sha256_digest(self.source_sha256, "source_sha256"),
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProvenanceRef:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            provenance_id=data["provenance_id"],
            source_ref=data["source_ref"],
            evidence_class=EvidenceClass(data["evidence_class"]),
            independence_key=data["independence_key"],
            source_sha256=data.get("source_sha256"),
        )


def _merged_provenance(values: Iterable[ProvenanceRef]) -> tuple[ProvenanceRef, ...]:
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
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class SupportInterval(_CanonicalRecord):
    """Provenance-bearing support bounds for one claim at its assessment scope."""

    SCHEMA_VERSION = "support_interval_v2"

    interval_id: str
    claim_id: str
    lower: float
    upper: float
    provenance_refs: tuple[ProvenanceRef, ...]
    support_measure: SupportMeasure = SupportMeasure.EVIDENCE_SUPPORT

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "interval_id",
            _normalized_identifier(self.interval_id, "interval_id"),
        )
        object.__setattr__(
            self,
            "claim_id",
            _normalized_identifier(self.claim_id, "claim_id"),
        )
        bounds = UnitInterval(self.lower, self.upper)
        object.__setattr__(self, "lower", bounds.lower)
        object.__setattr__(self, "upper", bounds.upper)
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("support intervals require provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        object.__setattr__(
            self, "support_measure", SupportMeasure(self.support_measure)
        )
        if (
            self.support_measure is SupportMeasure.EVIDENCE_SUPPORT
            and bounds.lower == 1.0
            and bounds.upper == 1.0
        ):
            raise ValueError(
                "evidence support cannot declare unqualified [1, 1] certainty; "
                "use declaration_presence only for record existence"
            )

    @property
    def bounds(self) -> UnitInterval:
        return UnitInterval(self.lower, self.upper)

    @property
    def evidence_atom_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(
                {
                    (item.evidence_class.value, item.independence_key)
                    for item in self.provenance_refs
                }
            )
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SupportInterval:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            interval_id=data["interval_id"],
            claim_id=data["claim_id"],
            lower=data["lower"],
            upper=data["upper"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            support_measure=SupportMeasure(data["support_measure"]),
        )


@dataclass(frozen=True, slots=True)
class ScopedClaim(_CanonicalRecord):
    """A claim that inherits the exact scope of its containing assessment."""

    SCHEMA_VERSION = "scoped_claim_v2"

    claim_id: str
    claim_key: str
    claim_value: str
    claim_kind: ClaimKind
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]
    cardinality: ClaimCardinality = ClaimCardinality.SINGLE
    member_id: str | None = None
    order_index: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim_id",
            _normalized_identifier(self.claim_id, "claim_id"),
        )
        object.__setattr__(
            self,
            "claim_key",
            _normalized_identifier(self.claim_key, "claim_key"),
        )
        object.__setattr__(
            self,
            "claim_value",
            _normalized_text(self.claim_value, "claim_value"),
        )
        object.__setattr__(self, "claim_kind", ClaimKind(self.claim_kind))
        object.__setattr__(
            self,
            "authority_ceiling",
            AuthorityCeiling(self.authority_ceiling),
        )
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("claims require provenance")
        object.__setattr__(self, "provenance_refs", provenance)
        cardinality = ClaimCardinality(self.cardinality)
        object.__setattr__(self, "cardinality", cardinality)
        member_id = self.member_id
        order_index = self.order_index
        if cardinality is ClaimCardinality.SINGLE:
            if member_id is not None or order_index is not None:
                raise ValueError(
                    "single claims cannot declare member_id or order_index"
                )
        else:
            if member_id is None:
                raise ValueError("collection members require a stable member_id")
            object.__setattr__(
                self,
                "member_id",
                _normalized_identifier(member_id, "member_id"),
            )
            if cardinality is ClaimCardinality.SET_MEMBER:
                if order_index is not None:
                    raise ValueError("set members cannot declare order_index")
            else:
                if isinstance(order_index, bool) or not isinstance(order_index, int):
                    raise TypeError("ordered members require an integer order_index")
                if order_index < 0:
                    raise ValueError("order_index must be nonnegative")

    @property
    def slot_key(self) -> tuple[str, str, str, int | None]:
        """Stable compatibility slot used by non-voting synthesis."""

        return (
            self.claim_key,
            self.cardinality.value,
            self.member_id or "",
            self.order_index,
        )

    @property
    def compatibility_key(self) -> tuple[str, str]:
        return (self.claim_kind.value, self.claim_value.casefold())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ScopedClaim:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            claim_id=data["claim_id"],
            claim_key=data["claim_key"],
            claim_value=data["claim_value"],
            claim_kind=ClaimKind(data["claim_kind"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            cardinality=ClaimCardinality(data["cardinality"]),
            member_id=data["member_id"],
            order_index=data["order_index"],
        )


@dataclass(frozen=True, slots=True)
class CriterionValue(_CanonicalRecord):
    """A finite native value or an explicit unknown; unknown is never numeric zero."""

    SCHEMA_VERSION = "criterion_value_v1"

    state: ValueState
    value: float | None
    reason: str | None

    def __post_init__(self) -> None:
        state = ValueState(self.state)
        object.__setattr__(self, "state", state)
        if state is ValueState.KNOWN:
            if self.value is None:
                raise ValueError("known criterion values require a value")
            object.__setattr__(self, "value", _finite_value(self.value, "value"))
            if self.reason is not None:
                raise ValueError("known criterion values cannot carry an unknown reason")
            return
        if self.value is not None:
            raise ValueError("unknown criterion values must not carry a numeric value")
        object.__setattr__(self, "reason", _normalized_text(self.reason, "reason"))

    @classmethod
    def known(cls, value: float) -> CriterionValue:
        return cls(state=ValueState.KNOWN, value=value, reason=None)

    @classmethod
    def unknown(cls, reason: str) -> CriterionValue:
        return cls(state=ValueState.UNKNOWN, value=None, reason=reason)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CriterionValue:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            state=ValueState(data["state"]),
            value=data.get("value"),
            reason=data.get("reason"),
        )


@dataclass(frozen=True, slots=True)
class UnknownFact(_CanonicalRecord):
    """One decision-relevant missing fact, represented independently of zero."""

    SCHEMA_VERSION = "plane_unknown_v1"

    unknown_id: str
    field_key: str
    reason: str
    needed_evidence: str
    provenance_refs: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "unknown_id",
            _normalized_identifier(self.unknown_id, "unknown_id"),
        )
        object.__setattr__(
            self,
            "field_key",
            _normalized_identifier(self.field_key, "field_key"),
        )
        object.__setattr__(self, "reason", _normalized_text(self.reason, "reason"))
        object.__setattr__(
            self,
            "needed_evidence",
            _normalized_text(self.needed_evidence, "needed_evidence"),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance(self.provenance_refs),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UnknownFact:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            unknown_id=data["unknown_id"],
            field_key=data["field_key"],
            reason=data["reason"],
            needed_evidence=data["needed_evidence"],
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item)
                for item in data.get("provenance_refs", ())
            ),
        )


@dataclass(frozen=True, slots=True)
class PlaneConflict(_CanonicalRecord):
    """An explicit within-plane conflict that must survive later synthesis."""

    SCHEMA_VERSION = "plane_conflict_v1"

    conflict_id: str
    claim_key: str
    alternatives: tuple[str, ...]
    reason: str
    claim_ids: tuple[str, ...] = ()
    provenance_refs: tuple[ProvenanceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "conflict_id",
            _normalized_identifier(self.conflict_id, "conflict_id"),
        )
        object.__setattr__(
            self,
            "claim_key",
            _normalized_identifier(self.claim_key, "claim_key"),
        )
        alternatives = _normalized_text_tuple(
            self.alternatives,
            "alternatives",
            allow_empty=False,
        )
        if len(alternatives) < 2:
            raise ValueError("conflicts require at least two alternatives")
        object.__setattr__(self, "alternatives", alternatives)
        object.__setattr__(self, "reason", _normalized_text(self.reason, "reason"))
        object.__setattr__(
            self,
            "claim_ids",
            _normalized_text_tuple(self.claim_ids, "claim_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance(self.provenance_refs),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlaneConflict:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            conflict_id=data["conflict_id"],
            claim_key=data["claim_key"],
            alternatives=tuple(data["alternatives"]),
            reason=data["reason"],
            claim_ids=tuple(data.get("claim_ids", ())),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item)
                for item in data.get("provenance_refs", ())
            ),
        )


_PROHIBITED_AGGREGATE_CRITERIA = frozenset(
    {"aggregate_score", "beauty", "beauty_score", "hedonic_score", "overall_score"}
)


@dataclass(frozen=True, slots=True)
class ParetoCriterion(_CanonicalRecord):
    """One native decision criterion; criteria are never averaged here."""

    SCHEMA_VERSION = "pareto_native_criterion_v1"

    criterion_id: str
    direction: CriterionDirection
    value: CriterionValue
    unit: str
    authority_ceiling: AuthorityCeiling
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        criterion_id = _normalized_identifier(self.criterion_id, "criterion_id")
        if criterion_id in _PROHIBITED_AGGREGATE_CRITERIA:
            raise ValueError(
                f"{criterion_id!r} is an unauthorized aggregate/hedonic criterion"
            )
        object.__setattr__(self, "criterion_id", criterion_id)
        object.__setattr__(self, "direction", CriterionDirection(self.direction))
        if not isinstance(self.value, CriterionValue):
            raise TypeError("value must be a CriterionValue")
        object.__setattr__(self, "unit", _normalized_text(self.unit, "unit"))
        object.__setattr__(
            self,
            "authority_ceiling",
            AuthorityCeiling(self.authority_ceiling),
        )
        provenance = _merged_provenance(self.provenance_refs)
        if not provenance:
            raise ValueError("native criteria require provenance")
        object.__setattr__(self, "provenance_refs", provenance)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ParetoCriterion:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            criterion_id=data["criterion_id"],
            direction=CriterionDirection(data["direction"]),
            value=CriterionValue.from_dict(data["value"]),
            unit=data["unit"],
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
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
        identifier = getattr(value, id_attribute)
        current = by_id.get(identifier)
        if current is not None and current != value:
            raise ValueError(f"{field_name} has conflicting record ID {identifier!r}")
        if current is not None:
            raise ValueError(f"{field_name} must contain unique {id_attribute} values")
        by_id[identifier] = value
    return tuple(
        sorted(by_id.values(), key=lambda item: (item.content_sha256, repr(item)))
    )


@dataclass(frozen=True, slots=True)
class PlaneAssessment(_CanonicalRecord):
    """One immutable, exact-scope assessment emitted by one architectural plane."""

    SCHEMA_VERSION = "plane_assessment_v2"

    assessment_id: str
    module_id: str
    plane_id: PlaneId
    scope: AssessmentScope
    claims: tuple[ScopedClaim, ...]
    support_intervals: tuple[SupportInterval, ...]
    conflicts: tuple[PlaneConflict, ...]
    unknowns: tuple[UnknownFact, ...]
    failure_modes: tuple[str, ...]
    proposed_experiments: tuple[str, ...]
    provenance_refs: tuple[ProvenanceRef, ...]
    authority_ceiling: AuthorityCeiling
    freshness_hashes: tuple[str, ...]
    native_criteria: tuple[ParetoCriterion, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_id",
            _normalized_identifier(self.assessment_id, "assessment_id"),
        )
        object.__setattr__(
            self,
            "module_id",
            _normalized_identifier(self.module_id, "module_id"),
        )
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        authority = AuthorityCeiling(self.authority_ceiling)
        object.__setattr__(self, "authority_ceiling", authority)

        claims = _unique_records(
            self.claims,
            record_type=ScopedClaim,
            id_attribute="claim_id",
            field_name="claims",
        )
        intervals = _unique_records(
            self.support_intervals,
            record_type=SupportInterval,
            id_attribute="interval_id",
            field_name="support_intervals",
        )
        conflicts = _unique_records(
            self.conflicts,
            record_type=PlaneConflict,
            id_attribute="conflict_id",
            field_name="conflicts",
        )
        unknowns = _unique_records(
            self.unknowns,
            record_type=UnknownFact,
            id_attribute="unknown_id",
            field_name="unknowns",
        )
        criteria = _unique_records(
            self.native_criteria,
            record_type=ParetoCriterion,
            id_attribute="criterion_id",
            field_name="native_criteria",
        )
        assessment_provenance = _merged_provenance(self.provenance_refs)
        claim_ids = {item.claim_id for item in claims}
        ordered_collections: dict[str, list[ScopedClaim]] = {}
        for claim in claims:
            if claim.cardinality is ClaimCardinality.ORDERED_MEMBER:
                ordered_collections.setdefault(claim.claim_key, []).append(claim)
        for claim_key, members in ordered_collections.items():
            member_ids = [item.member_id for item in members]
            positions = [item.order_index for item in members]
            if len(member_ids) != len(set(member_ids)):
                raise ValueError(
                    f"ordered collection {claim_key!r} repeats a member_id"
                )
            if len(positions) != len(set(positions)):
                raise ValueError(
                    f"ordered collection {claim_key!r} repeats an order_index"
                )
        dangling = sorted(
            item.claim_id for item in intervals if item.claim_id not in claim_ids
        )
        if dangling:
            raise ValueError(
                "support_intervals reference unknown claims: " + ", ".join(dangling)
            )
        for claim in claims:
            if claim.claim_kind is ClaimKind.OBSERVATION and not any(
                reference.evidence_class
                in {
                    EvidenceClass.DIRECT_OBSERVATION,
                    EvidenceClass.INSTRUMENTAL_OBSERVATION,
                    EvidenceClass.PRIMARY_SOURCE,
                    EvidenceClass.OFFICIAL_RECORD,
                    EvidenceClass.USER_REPORT,
                }
                for reference in claim.provenance_refs
            ):
                raise ValueError(
                    f"observation claim {claim.claim_id!r} requires "
                    "observation-eligible provenance"
                )
            if not claim.authority_ceiling.is_no_stronger_than(authority):
                raise ValueError(
                    f"claim {claim.claim_id!r} exceeds assessment authority ceiling"
                )
        for criterion in criteria:
            if not criterion.authority_ceiling.is_no_stronger_than(authority):
                raise ValueError(
                    f"criterion {criterion.criterion_id!r} exceeds assessment authority ceiling"
                )
        if authority is AuthorityCeiling.EVIDENCE_LIMITED and not any(
            reference.evidence_class
            in {
                EvidenceClass.DIRECT_OBSERVATION,
                EvidenceClass.INSTRUMENTAL_OBSERVATION,
                EvidenceClass.PRIMARY_SOURCE,
                EvidenceClass.OFFICIAL_RECORD,
                EvidenceClass.USER_REPORT,
            }
            for reference in (
                *assessment_provenance,
                *(ref for claim in claims for ref in claim.provenance_refs),
                *(ref for interval in intervals for ref in interval.provenance_refs),
            )
        ):
            raise ValueError(
                "evidence_limited assessment requires qualifying evidence provenance"
            )

        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "support_intervals", intervals)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "unknowns", unknowns)
        object.__setattr__(self, "native_criteria", criteria)
        object.__setattr__(
            self,
            "failure_modes",
            _normalized_text_tuple(self.failure_modes, "failure_modes"),
        )
        object.__setattr__(
            self,
            "proposed_experiments",
            _normalized_text_tuple(
                self.proposed_experiments,
                "proposed_experiments",
            ),
        )
        freshness = tuple(
            sorted(
                {
                    _sha256_digest(value, "freshness_hashes")
                    for value in self.freshness_hashes
                }
            )
        )
        object.__setattr__(self, "freshness_hashes", freshness)
        nested_provenance = (
            *(item for claim in claims for item in claim.provenance_refs),
            *(item for interval in intervals for item in interval.provenance_refs),
            *(item for conflict in conflicts for item in conflict.provenance_refs),
            *(item for unknown in unknowns for item in unknown.provenance_refs),
            *(item for criterion in criteria for item in criterion.provenance_refs),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            _merged_provenance((*assessment_provenance, *nested_provenance)),
        )

    @property
    def target_scope(self) -> str:
        return self.scope.target_scope

    @property
    def temporal_scope(self) -> str:
        return self.scope.temporal_scope

    @property
    def matrix_scope(self) -> str:
        return self.scope.matrix_scope

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlaneAssessment:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            assessment_id=data["assessment_id"],
            module_id=data["module_id"],
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
            claims=tuple(ScopedClaim.from_dict(item) for item in data["claims"]),
            support_intervals=tuple(
                SupportInterval.from_dict(item) for item in data["support_intervals"]
            ),
            conflicts=tuple(
                PlaneConflict.from_dict(item) for item in data["conflicts"]
            ),
            unknowns=tuple(UnknownFact.from_dict(item) for item in data["unknowns"]),
            failure_modes=tuple(data["failure_modes"]),
            proposed_experiments=tuple(data["proposed_experiments"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            freshness_hashes=tuple(data["freshness_hashes"]),
            native_criteria=tuple(
                ParetoCriterion.from_dict(item) for item in data["native_criteria"]
            ),
        )


@dataclass(frozen=True, slots=True)
class ScopedNativeCriterion(_CanonicalRecord):
    """A native Pareto criterion kept attached to its originating scope and plane."""

    SCHEMA_VERSION = "scoped_native_criterion_v1"

    assessment_id: str
    module_id: str
    plane_id: PlaneId
    scope: AssessmentScope
    criterion: ParetoCriterion

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_id",
            _normalized_identifier(self.assessment_id, "assessment_id"),
        )
        object.__setattr__(
            self,
            "module_id",
            _normalized_identifier(self.module_id, "module_id"),
        )
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        if not isinstance(self.criterion, ParetoCriterion):
            raise TypeError("criterion must be a ParetoCriterion")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ScopedNativeCriterion:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            assessment_id=data["assessment_id"],
            module_id=data["module_id"],
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
            criterion=ParetoCriterion.from_dict(data["criterion"]),
        )


@dataclass(frozen=True, slots=True)
class ScopedUnknown(_CanonicalRecord):
    """An unknown kept attached to its originating scope and plane."""

    SCHEMA_VERSION = "scoped_unknown_v1"

    assessment_id: str
    module_id: str
    plane_id: PlaneId
    scope: AssessmentScope
    unknown: UnknownFact

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assessment_id",
            _normalized_identifier(self.assessment_id, "assessment_id"),
        )
        object.__setattr__(
            self,
            "module_id",
            _normalized_identifier(self.module_id, "module_id"),
        )
        object.__setattr__(self, "plane_id", PlaneId(self.plane_id))
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        if not isinstance(self.unknown, UnknownFact):
            raise TypeError("unknown must be an UnknownFact")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ScopedUnknown:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            assessment_id=data["assessment_id"],
            module_id=data["module_id"],
            plane_id=PlaneId(data["plane_id"]),
            scope=AssessmentScope.from_dict(data["scope"]),
            unknown=UnknownFact.from_dict(data["unknown"]),
        )


__all__ = [
    "AssessmentScope",
    "AuthorityCeiling",
    "ClaimCardinality",
    "ClaimKind",
    "CriterionDirection",
    "CriterionValue",
    "EvidenceClass",
    "ParetoCriterion",
    "PlaneAssessment",
    "PlaneConflict",
    "PlaneId",
    "ProvenanceRef",
    "ScopedClaim",
    "ScopedNativeCriterion",
    "ScopedUnknown",
    "SupportInterval",
    "SupportMeasure",
    "UnitInterval",
    "UnknownFact",
    "ValueState",
]
