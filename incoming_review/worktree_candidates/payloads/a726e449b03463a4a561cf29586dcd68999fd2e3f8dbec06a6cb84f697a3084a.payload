"""Closed scientific-source, construct, and transfer contracts for SolForge."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from engine.evidence_contracts import canonical_json_bytes, sha256_hex

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(
    r"^(doi|pmid|pmcid|iso|astm):\S+$", re.IGNORECASE
)
_RIGHTS = frozenset(
    {
        "METADATA_AND_DERIVED_SUMMARY_ONLY",
        "OPEN_ACCESS_METADATA_AND_DERIVED_SUMMARY_ONLY",
        "OPEN_ACCESS_RETAINED_BYTES",
        "PUBLIC_STANDARD_METADATA_ONLY",
    }
)

EVIDENCE_REVIEW_AUTHORITY_FLAGS = {
    "formula": False,
    "inventory_mutation": False,
    "liking": False,
    "physical_execution": False,
    "publication": False,
    "purchase": False,
    "release": False,
    "runtime": False,
    "safety": False,
    "scientific_claim": False,
    "sensory": False,
}

_CONSTRUCT_IDS = (
    "LIKING",
    "PERCEIVED_RICHNESS",
    "PERCEIVED_DEPTH",
    "CONFIGURATIONAL_INTEGRATION",
    "HIERARCHY_CONTRAST",
    "TEMPORAL_DIFFERENTIATION",
    "TARGET_FIDELITY",
    "INTENSITY",
    "FAMILIARITY",
    "DETECTABILITY",
    "WANTING_TO_RESMELL",
    "WEAR_ACCEPTANCE",
    "COMFORT",
    "FASCINATION",
    "TENSION",
    "RELIEF",
    "FATIGUE",
    "AVERSION",
    "PERSISTENCE",
)


class EvidenceSourceTier(str, Enum):
    DIRECT_FINE_FRAGRANCE = "DIRECT_FINE_FRAGRANCE"
    DIRECT_HUMAN_OLFACTION = "DIRECT_HUMAN_OLFACTION"
    SYSTEMATIC_SYNTHESIS = "SYSTEMATIC_SYNTHESIS"
    TRANSFERABLE_SENSORY_METHOD = "TRANSFERABLE_SENSORY_METHOD"
    STATISTICAL_FOUNDATION = "STATISTICAL_FOUNDATION"
    HYPOTHESIS_ONLY = "HYPOTHESIS_ONLY"


class TransferDisposition(str, Enum):
    DIRECT = "DIRECT"
    METHOD_ONLY = "METHOD_ONLY"
    NARROWER_SCOPE = "NARROWER_SCOPE"
    HOLD = "HOLD"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _texts(value: object, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a sequence")
    result = tuple(_text(item, field_name) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must be nonempty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be bool")
    return value


def _closed_payload(
    payload: object,
    *,
    schema_version: str,
    fields: frozenset[str],
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be an object")
    expected = fields | {"schema_version", "authority_flags"}
    if set(payload) != expected:
        raise ValueError("payload does not match the closed schema")
    if payload["schema_version"] != schema_version:
        raise ValueError(f"schema_version must be {schema_version}")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("authority_flags must be the exact all-false mapping")
    return {field: payload[field] for field in fields}


class _Record:
    SCHEMA_VERSION: ClassVar[str]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    def _envelope(self, values: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **values,
            "authority_flags": dict(EVIDENCE_REVIEW_AUTHORITY_FLAGS),
        }


@dataclass(frozen=True, slots=True)
class EvidenceSourceRecordV2(_Record):
    """One metadata/derived-summary source record with explicit transfer scope."""

    SCHEMA_VERSION: ClassVar[str] = "evidence_source_record_v2"
    source_id: str
    stable_identifier: str
    uri: str
    title: str
    publication_year: int
    retrieved_on: str
    source_kind: str
    study_design: str
    population: str
    matrix: str
    exposure: str
    endpoints: tuple[str, ...]
    result_used: str
    limitations: tuple[str, ...]
    source_tier: EvidenceSourceTier
    transfer_disposition: TransferDisposition
    rights: str
    code_requirements: tuple[str, ...]
    primary_source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "stable_identifier",
            "uri",
            "title",
            "retrieved_on",
            "source_kind",
            "study_design",
            "population",
            "matrix",
            "exposure",
            "result_used",
            "rights",
        ):
            object.__setattr__(
                self, field_name, _text(getattr(self, field_name), field_name)
            )
        if _IDENTIFIER_RE.fullmatch(self.stable_identifier) is None:
            raise ValueError("stable_identifier must use a supported stable prefix")
        parsed = urlparse(self.uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("uri must be an absolute HTTP(S) URI")
        if isinstance(self.publication_year, bool) or not isinstance(
            self.publication_year, int
        ):
            raise TypeError("publication_year must be an integer")
        if not 1800 <= self.publication_year <= 2100:
            raise ValueError("publication_year is invalid")
        try:
            date.fromisoformat(self.retrieved_on)
        except ValueError as exc:
            raise ValueError("retrieved_on must be an ISO date") from exc
        object.__setattr__(self, "endpoints", _texts(self.endpoints, "endpoints"))
        object.__setattr__(
            self, "limitations", _texts(self.limitations, "limitations")
        )
        object.__setattr__(
            self,
            "code_requirements",
            _texts(self.code_requirements, "code_requirements"),
        )
        object.__setattr__(
            self,
            "primary_source_ids",
            _texts(self.primary_source_ids, "primary_source_ids", allow_empty=True),
        )
        object.__setattr__(self, "source_tier", EvidenceSourceTier(self.source_tier))
        object.__setattr__(
            self,
            "transfer_disposition",
            TransferDisposition(self.transfer_disposition),
        )
        rights = self.rights.upper()
        if rights not in _RIGHTS:
            raise ValueError("rights is not an allowed evidence-rights state")
        object.__setattr__(self, "rights", rights)
        if (
            self.source_tier is EvidenceSourceTier.SYSTEMATIC_SYNTHESIS
            and not self.primary_source_ids
        ):
            raise ValueError("systematic synthesis requires primary source traceability")

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_id": self.source_id,
                "stable_identifier": self.stable_identifier,
                "uri": self.uri,
                "title": self.title,
                "publication_year": self.publication_year,
                "retrieved_on": self.retrieved_on,
                "source_kind": self.source_kind,
                "study_design": self.study_design,
                "population": self.population,
                "matrix": self.matrix,
                "exposure": self.exposure,
                "endpoints": list(self.endpoints),
                "result_used": self.result_used,
                "limitations": list(self.limitations),
                "source_tier": self.source_tier.value,
                "transfer_disposition": self.transfer_disposition.value,
                "rights": self.rights,
                "code_requirements": list(self.code_requirements),
                "primary_source_ids": list(self.primary_source_ids),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> EvidenceSourceRecordV2:
        fields = frozenset(
            {
                "source_id",
                "stable_identifier",
                "uri",
                "title",
                "publication_year",
                "retrieved_on",
                "source_kind",
                "study_design",
                "population",
                "matrix",
                "exposure",
                "endpoints",
                "result_used",
                "limitations",
                "source_tier",
                "transfer_disposition",
                "rights",
                "code_requirements",
                "primary_source_ids",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        for field_name in (
            "endpoints",
            "limitations",
            "code_requirements",
            "primary_source_ids",
        ):
            values[field_name] = tuple(values[field_name])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class SourceQualityAssessmentV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "source_quality_assessment_v1"
    source_id: str
    source_record_sha256: str
    tier: EvidenceSourceTier
    primary_source_ids: tuple[str, ...]
    population_declared: bool
    matrix_declared: bool
    endpoint_declared: bool
    order_control_reported: bool
    assessor_dependence_reported: bool
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _text(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "source_record_sha256",
            _sha(self.source_record_sha256, "source_record_sha256"),
        )
        object.__setattr__(self, "tier", EvidenceSourceTier(self.tier))
        object.__setattr__(
            self,
            "primary_source_ids",
            _texts(self.primary_source_ids, "primary_source_ids", allow_empty=True),
        )
        for field_name in (
            "population_declared",
            "matrix_declared",
            "endpoint_declared",
            "order_control_reported",
            "assessor_dependence_reported",
        ):
            object.__setattr__(
                self, field_name, _boolean(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self, "limitations", _texts(self.limitations, "limitations")
        )

    @property
    def failures(self) -> tuple[str, ...]:
        failures: list[str] = []
        if (
            self.tier is EvidenceSourceTier.SYSTEMATIC_SYNTHESIS
            and not self.primary_source_ids
        ):
            failures.append("PRIMARY_TRACE_MISSING")
        if not self.population_declared:
            failures.append("POPULATION_MISSING")
        if not self.matrix_declared:
            failures.append("MATRIX_MISSING")
        if not self.endpoint_declared:
            failures.append("ENDPOINT_MISSING")
        return tuple(failures)

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_id": self.source_id,
                "source_record_sha256": self.source_record_sha256,
                "tier": self.tier.value,
                "primary_source_ids": list(self.primary_source_ids),
                "population_declared": self.population_declared,
                "matrix_declared": self.matrix_declared,
                "endpoint_declared": self.endpoint_declared,
                "order_control_reported": self.order_control_reported,
                "assessor_dependence_reported": self.assessor_dependence_reported,
                "limitations": list(self.limitations),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> SourceQualityAssessmentV1:
        fields = frozenset(
            {
                "source_id",
                "source_record_sha256",
                "tier",
                "primary_source_ids",
                "population_declared",
                "matrix_declared",
                "endpoint_declared",
                "order_control_reported",
                "assessor_dependence_reported",
                "limitations",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        values["primary_source_ids"] = tuple(values["primary_source_ids"])
        values["limitations"] = tuple(values["limitations"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class OperativeEvidenceBindingV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "operative_evidence_binding_v1"
    requirement_id: str
    source_record_sha256: str
    source_tier: EvidenceSourceTier
    requested_claim: str
    demonstrated_scope: str
    transfer_disposition: TransferDisposition
    limitations: tuple[str, ...]
    population_match: bool
    matrix_match: bool
    endpoint_match: bool
    time_match: bool

    def __post_init__(self) -> None:
        for field_name in ("requirement_id", "requested_claim", "demonstrated_scope"):
            object.__setattr__(
                self, field_name, _text(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self,
            "source_record_sha256",
            _sha(self.source_record_sha256, "source_record_sha256"),
        )
        object.__setattr__(
            self, "source_tier", EvidenceSourceTier(self.source_tier)
        )
        object.__setattr__(
            self,
            "transfer_disposition",
            TransferDisposition(self.transfer_disposition),
        )
        object.__setattr__(
            self, "limitations", _texts(self.limitations, "limitations")
        )
        for field_name in (
            "population_match",
            "matrix_match",
            "endpoint_match",
            "time_match",
        ):
            object.__setattr__(
                self, field_name, _boolean(getattr(self, field_name), field_name)
            )
        if self.transfer_disposition is TransferDisposition.DIRECT:
            direct_tiers = {
                EvidenceSourceTier.DIRECT_FINE_FRAGRANCE,
                EvidenceSourceTier.DIRECT_HUMAN_OLFACTION,
            }
            scope = (
                self.population_match,
                self.matrix_match,
                self.endpoint_match,
                self.time_match,
            )
            if self.source_tier not in direct_tiers or not all(scope):
                raise ValueError("DIRECT transfer requires exact scope and a direct tier")

    @property
    def failures(self) -> tuple[str, ...]:
        if self.transfer_disposition is TransferDisposition.HOLD:
            return ("TRANSFER_HOLD",)
        return ()

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "requirement_id": self.requirement_id,
                "source_record_sha256": self.source_record_sha256,
                "source_tier": self.source_tier.value,
                "requested_claim": self.requested_claim,
                "demonstrated_scope": self.demonstrated_scope,
                "transfer_disposition": self.transfer_disposition.value,
                "limitations": list(self.limitations),
                "population_match": self.population_match,
                "matrix_match": self.matrix_match,
                "endpoint_match": self.endpoint_match,
                "time_match": self.time_match,
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> OperativeEvidenceBindingV1:
        fields = frozenset(
            {
                "requirement_id",
                "source_record_sha256",
                "source_tier",
                "requested_claim",
                "demonstrated_scope",
                "transfer_disposition",
                "limitations",
                "population_match",
                "matrix_match",
                "endpoint_match",
                "time_match",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        values["limitations"] = tuple(values["limitations"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class EvidenceReviewLedgerV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "evidence_review_ledger_v1"
    source_seed_manifest_sha256: str
    construct_registry_sha256: str
    assessments: tuple[SourceQualityAssessmentV1, ...]
    operative_bindings: tuple[OperativeEvidenceBindingV1, ...]
    unresolved_questions: tuple[str, ...]
    source_records: tuple[EvidenceSourceRecordV2, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_seed_manifest_sha256",
            _sha(self.source_seed_manifest_sha256, "source_seed_manifest_sha256"),
        )
        object.__setattr__(
            self,
            "construct_registry_sha256",
            _sha(self.construct_registry_sha256, "construct_registry_sha256"),
        )
        assessments = tuple(self.assessments)
        bindings = tuple(self.operative_bindings)
        records = tuple(self.source_records)
        if not assessments or any(
            not isinstance(item, SourceQualityAssessmentV1) for item in assessments
        ):
            raise TypeError("assessments must contain SourceQualityAssessmentV1 values")
        if not bindings or any(
            not isinstance(item, OperativeEvidenceBindingV1) for item in bindings
        ):
            raise TypeError("operative_bindings must contain OperativeEvidenceBindingV1 values")
        if any(not isinstance(item, EvidenceSourceRecordV2) for item in records):
            raise TypeError("source_records must contain EvidenceSourceRecordV2 values")
        object.__setattr__(self, "assessments", assessments)
        object.__setattr__(self, "operative_bindings", bindings)
        object.__setattr__(self, "source_records", records)
        object.__setattr__(
            self,
            "unresolved_questions",
            _texts(self.unresolved_questions, "unresolved_questions"),
        )

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_seed_manifest_sha256": self.source_seed_manifest_sha256,
                "construct_registry_sha256": self.construct_registry_sha256,
                "assessments": [item.as_dict() for item in self.assessments],
                "operative_bindings": [
                    item.as_dict() for item in self.operative_bindings
                ],
                "unresolved_questions": list(self.unresolved_questions),
                "source_records": [item.as_dict() for item in self.source_records],
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> EvidenceReviewLedgerV1:
        fields = frozenset(
            {
                "source_seed_manifest_sha256",
                "construct_registry_sha256",
                "assessments",
                "operative_bindings",
                "unresolved_questions",
                "source_records",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        values["assessments"] = tuple(
            SourceQualityAssessmentV1.from_dict(item)
            for item in values["assessments"]
        )
        values["operative_bindings"] = tuple(
            OperativeEvidenceBindingV1.from_dict(item)
            for item in values["operative_bindings"]
        )
        values["unresolved_questions"] = tuple(values["unresolved_questions"])
        values["source_records"] = tuple(
            EvidenceSourceRecordV2.from_dict(item) for item in values["source_records"]
        )
        return cls(**values)


def validate_evidence_review(ledger: EvidenceReviewLedgerV1) -> tuple[str, ...]:
    """Return all cross-record failures without promoting any scientific claim."""

    if not isinstance(ledger, EvidenceReviewLedgerV1):
        raise TypeError("ledger must be an EvidenceReviewLedgerV1")
    issues: list[str] = []
    source_ids = [item.source_id for item in ledger.assessments]
    if len(source_ids) != len(set(source_ids)):
        issues.append("duplicate source_id")
    hashes = [item.source_record_sha256 for item in ledger.assessments]
    if len(hashes) != len(set(hashes)):
        issues.append("duplicate source_record_sha256")
    requirement_ids = [item.requirement_id for item in ledger.operative_bindings]
    if len(requirement_ids) != len(set(requirement_ids)):
        issues.append("duplicate requirement_id")
    known_hashes = set(hashes)
    for binding in ledger.operative_bindings:
        if binding.source_record_sha256 not in known_hashes:
            issues.append(
                f"binding {binding.requirement_id} references an unknown source record"
            )
    if ledger.source_records:
        record_hashes = {item.record_sha256: item for item in ledger.source_records}
        stable_ids = [item.stable_identifier.casefold() for item in ledger.source_records]
        if len(stable_ids) != len(set(stable_ids)):
            issues.append("duplicate stable_identifier")
        for assessment in ledger.assessments:
            source = record_hashes.get(assessment.source_record_sha256)
            if source is None:
                issues.append(
                    f"assessment {assessment.source_id} references an unknown source record"
                )
            elif source.source_id != assessment.source_id:
                issues.append(
                    f"assessment {assessment.source_id} source identity mismatch"
                )
    return tuple(issues)


def load_construct_registry(path: Path) -> dict[str, object]:
    """Load and validate the closed complexity-construct registry."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "constructs",
        "authority_flags",
    }:
        raise ValueError("construct registry does not match the closed schema")
    if payload["schema_version"] != "complexity_construct_registry_v1":
        raise ValueError("construct registry schema_version is invalid")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("construct registry authority_flags are invalid")
    constructs = payload["constructs"]
    if not isinstance(constructs, list):
        raise TypeError("constructs must be a list")
    fields = {
        "construct_id",
        "definition",
        "anchors",
        "outcome_vocabulary",
        "required_scope_fields",
        "forbidden_inferences",
    }
    for construct in constructs:
        if not isinstance(construct, dict) or set(construct) != fields:
            raise ValueError("construct entry does not match the closed schema")
        _text(construct["definition"], "definition")
        for field_name in fields - {"construct_id", "definition"}:
            _texts(construct[field_name], field_name)
    observed = tuple(construct["construct_id"] for construct in constructs)
    if observed != _CONSTRUCT_IDS:
        raise ValueError("construct identifiers or order are invalid")
    return payload


def load_evidence_source_registry(path: Path) -> tuple[EvidenceSourceRecordV2, ...]:
    """Load the closed, source-sorted V2 literature and standards registry."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "sources",
        "authority_flags",
    }:
        raise ValueError("evidence source registry does not match the closed schema")
    if payload["schema_version"] != "complexity_evidence_sources_v2":
        raise ValueError("evidence source registry schema_version is invalid")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("evidence source registry authority_flags are invalid")
    if not isinstance(payload["sources"], list) or not payload["sources"]:
        raise ValueError("evidence source registry requires sources")
    records = tuple(EvidenceSourceRecordV2.from_dict(item) for item in payload["sources"])
    source_ids = tuple(item.source_id for item in records)
    if source_ids != tuple(sorted(source_ids)):
        raise ValueError("evidence sources must be sorted by source_id")
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("evidence sources contain duplicate source_id")
    stable_ids = tuple(item.stable_identifier.casefold() for item in records)
    if len(stable_ids) != len(set(stable_ids)):
        raise ValueError("evidence sources contain duplicate stable_identifier")
    return records


__all__ = [
    "EVIDENCE_REVIEW_AUTHORITY_FLAGS",
    "EvidenceReviewLedgerV1",
    "EvidenceSourceRecordV2",
    "EvidenceSourceTier",
    "OperativeEvidenceBindingV1",
    "SourceQualityAssessmentV1",
    "TransferDisposition",
    "load_construct_registry",
    "load_evidence_source_registry",
    "validate_evidence_review",
]
