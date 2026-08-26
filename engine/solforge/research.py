"""Canonical, non-promoting research evidence records for SolForge."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import ClassVar
from urllib.parse import urlparse

from engine.evidence_contracts import canonical_json_bytes, sha256_hex

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^(doi|pmid|pmcid|iso|nist):\S+$", re.IGNORECASE)
_RIGHTS = frozenset(
    {
        "METADATA_AND_DERIVED_SUMMARY_ONLY",
        "OPEN_ACCESS_METADATA_AND_DERIVED_SUMMARY_ONLY",
        "PUBLIC_GUIDANCE_METADATA_ONLY",
        "UNRESOLVED_NO_FULL_TEXT",
        "OPEN_ACCESS_RETAINED_BYTES",
    }
)

RESEARCH_AUTHORITY_FLAGS = {
    "formula": False,
    "hedonic": False,
    "release": False,
    "safety": False,
    "scientific_claim": False,
    "sensory": False,
}


class ResearchEvidenceClass(str, Enum):
    DIRECT_PERFUMERY_PSYCHOPHYSICS = "DIRECT_PERFUMERY_PSYCHOPHYSICS"
    GENERAL_OLFACTION_PSYCHOPHYSICS = "GENERAL_OLFACTION_PSYCHOPHYSICS"
    ADJACENT_FLAVOR_OR_PRODUCT_SENSORY = "ADJACENT_FLAVOR_OR_PRODUCT_SENSORY"
    RECEPTOR_OR_IN_VITRO = "RECEPTOR_OR_IN_VITRO"
    PHYSICOCHEMICAL = "PHYSICOCHEMICAL"
    SUPPLIER_OR_TRADE_DESCRIPTION = "SUPPLIER_OR_TRADE_DESCRIPTION"


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    return " ".join(value.split())


def _texts(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{name} must be a nonempty sequence")
    return tuple(_text(item, name) for item in value)


def _sha(value: object, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lower-case SHA-256 digest")
    return value


def _closed_payload(
    payload: object, schema: str, fields: set[str]
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise TypeError("record payload must be an object")
    expected = fields | {"schema_version", "authority_flags"}
    if set(payload) != expected:
        raise ValueError("record fields do not match the closed schema")
    if payload["schema_version"] != schema:
        raise ValueError(f"schema_version must be {schema}")
    if payload["authority_flags"] != RESEARCH_AUTHORITY_FLAGS:
        raise ValueError("authority_flags must be the exact all-false mapping")
    return {name: payload[name] for name in fields}


class _Record:
    SCHEMA_VERSION: ClassVar[str]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    def _envelope(self, fields: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **fields,
            "authority_flags": dict(RESEARCH_AUTHORITY_FLAGS),
        }


@dataclass(frozen=True, slots=True)
class ResearchEvidenceRecordV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "research_evidence_record_v1"
    source_id: str
    stable_identifier: str
    uri: str
    title: str
    authors: tuple[str, ...]
    publication_year: int
    retrieved_on: str
    source_kind: str
    evidence_class: ResearchEvidenceClass
    study_design: str
    stimuli: str
    population: str
    apparatus: str
    endpoints: tuple[str, ...]
    direct_result_summary: str
    limitations: tuple[str, ...]
    applicability: tuple[str, ...]
    rights: str
    retained_source_sha256: str | None = None
    short_extract: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "source_id",
            "stable_identifier",
            "uri",
            "title",
            "retrieved_on",
            "source_kind",
            "study_design",
            "stimuli",
            "population",
            "apparatus",
            "direct_result_summary",
            "rights",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if _IDENTIFIER_RE.fullmatch(self.stable_identifier) is None:
            raise ValueError("stable_identifier must use a stable DOI, PMID, PMCID, ISO, or NIST prefix")
        parsed = urlparse(self.uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("uri must be an absolute HTTP(S) URI")
        if isinstance(self.publication_year, bool) or not 1800 <= self.publication_year <= 2100:
            raise ValueError("publication_year is invalid")
        try:
            date.fromisoformat(self.retrieved_on)
        except ValueError as exc:
            raise ValueError("retrieved_on must be an ISO date") from exc
        object.__setattr__(self, "authors", _texts(self.authors, "authors"))
        object.__setattr__(self, "endpoints", _texts(self.endpoints, "endpoints"))
        object.__setattr__(self, "limitations", _texts(self.limitations, "limitations"))
        object.__setattr__(self, "applicability", _texts(self.applicability, "applicability"))
        object.__setattr__(self, "evidence_class", ResearchEvidenceClass(self.evidence_class))
        source_kind = self.source_kind.upper()
        object.__setattr__(self, "source_kind", source_kind)
        rights = self.rights.upper()
        if rights not in _RIGHTS:
            raise ValueError("rights is not an allowed evidence-rights state")
        object.__setattr__(self, "rights", rights)
        supplier_class = ResearchEvidenceClass.SUPPLIER_OR_TRADE_DESCRIPTION
        if (source_kind == "SUPPLIER") != (self.evidence_class is supplier_class):
            raise ValueError("supplier evidence must use only the supplier evidence class")
        object.__setattr__(
            self,
            "retained_source_sha256",
            _sha(
                self.retained_source_sha256,
                "retained_source_sha256",
                optional=True,
            ),
        )
        if (
            self.retained_source_sha256 is not None
            and self.rights != "OPEN_ACCESS_RETAINED_BYTES"
        ):
            raise ValueError("rights do not permit retained source bytes")
        if self.short_extract is not None:
            extract = _text(self.short_extract, "short_extract")
            if len(extract.split()) > 25:
                raise ValueError("short_extract must contain no more than 25 words")
            object.__setattr__(self, "short_extract", extract)

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_id": self.source_id,
                "stable_identifier": self.stable_identifier,
                "uri": self.uri,
                "title": self.title,
                "authors": list(self.authors),
                "publication_year": self.publication_year,
                "retrieved_on": self.retrieved_on,
                "source_kind": self.source_kind,
                "evidence_class": self.evidence_class.value,
                "study_design": self.study_design,
                "stimuli": self.stimuli,
                "population": self.population,
                "apparatus": self.apparatus,
                "endpoints": list(self.endpoints),
                "direct_result_summary": self.direct_result_summary,
                "limitations": list(self.limitations),
                "applicability": list(self.applicability),
                "rights": self.rights,
                "retained_source_sha256": self.retained_source_sha256,
                "short_extract": self.short_extract,
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> ResearchEvidenceRecordV1:
        fields = {
            "source_id",
            "stable_identifier",
            "uri",
            "title",
            "authors",
            "publication_year",
            "retrieved_on",
            "source_kind",
            "evidence_class",
            "study_design",
            "stimuli",
            "population",
            "apparatus",
            "endpoints",
            "direct_result_summary",
            "limitations",
            "applicability",
            "rights",
            "retained_source_sha256",
            "short_extract",
        }
        values = _closed_payload(payload, cls.SCHEMA_VERSION, fields)
        values["authors"] = tuple(values["authors"])
        values["endpoints"] = tuple(values["endpoints"])
        values["limitations"] = tuple(values["limitations"])
        values["applicability"] = tuple(values["applicability"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class ResearchConflictV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "research_conflict_v1"
    conflict_id: str
    linked_record_sha256: tuple[str, ...]
    question: str
    conflict_summary: str
    resolution_state: str

    def __post_init__(self) -> None:
        for name in ("conflict_id", "question", "conflict_summary", "resolution_state"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        refs = tuple(
            str(_sha(item, "linked_record_sha256"))
            for item in self.linked_record_sha256
        )
        if len(refs) < 2 or len(set(refs)) != len(refs):
            raise ValueError(
                "linked_record_sha256 must name at least two distinct records"
            )
        object.__setattr__(self, "linked_record_sha256", refs)
        state = self.resolution_state.upper()
        if state not in {"UNRESOLVED", "RESOLVED_SCOPE"}:
            raise ValueError("resolution_state is invalid")
        object.__setattr__(self, "resolution_state", state)

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "conflict_id": self.conflict_id,
                "linked_record_sha256": list(self.linked_record_sha256),
                "question": self.question,
                "conflict_summary": self.conflict_summary,
                "resolution_state": self.resolution_state,
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> ResearchConflictV1:
        fields = {
            "conflict_id",
            "linked_record_sha256",
            "question",
            "conflict_summary",
            "resolution_state",
        }
        values = _closed_payload(payload, cls.SCHEMA_VERSION, fields)
        values["linked_record_sha256"] = tuple(values["linked_record_sha256"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class ResearchLedgerV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "research_ledger_v1"
    source_seed_manifest_sha256: str
    records: tuple[ResearchEvidenceRecordV1, ...]
    conflicts: tuple[ResearchConflictV1, ...]
    unresolved_questions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_seed_manifest_sha256",
            _sha(self.source_seed_manifest_sha256, "source_seed_manifest_sha256"),
        )
        records = tuple(self.records)
        conflicts = tuple(self.conflicts)
        if any(not isinstance(item, ResearchEvidenceRecordV1) for item in records):
            raise TypeError("records must contain ResearchEvidenceRecordV1 values")
        if any(not isinstance(item, ResearchConflictV1) for item in conflicts):
            raise TypeError("conflicts must contain ResearchConflictV1 values")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(
            self,
            "unresolved_questions",
            _texts(self.unresolved_questions, "unresolved_questions"),
        )

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_seed_manifest_sha256": self.source_seed_manifest_sha256,
                "records": [item.as_dict() for item in self.records],
                "conflicts": [item.as_dict() for item in self.conflicts],
                "unresolved_questions": list(self.unresolved_questions),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> ResearchLedgerV1:
        fields = {
            "source_seed_manifest_sha256",
            "records",
            "conflicts",
            "unresolved_questions",
        }
        values = _closed_payload(payload, cls.SCHEMA_VERSION, fields)
        values["records"] = tuple(
            ResearchEvidenceRecordV1.from_dict(item) for item in values["records"]
        )
        values["conflicts"] = tuple(
            ResearchConflictV1.from_dict(item) for item in values["conflicts"]
        )
        values["unresolved_questions"] = tuple(values["unresolved_questions"])
        return cls(**values)


def validate_research_ledger(ledger: ResearchLedgerV1) -> tuple[str, ...]:
    """Return all cross-record integrity problems without promoting any claim."""

    if not isinstance(ledger, ResearchLedgerV1):
        raise TypeError("ledger must be a ResearchLedgerV1")
    issues: list[str] = []
    source_ids = [item.source_id for item in ledger.records]
    if len(source_ids) != len(set(source_ids)):
        issues.append("duplicate source_id")
    identifiers = [item.stable_identifier.casefold() for item in ledger.records]
    if len(identifiers) != len(set(identifiers)):
        issues.append("duplicate stable_identifier")
    record_hashes = {item.record_sha256 for item in ledger.records}
    conflict_ids = [item.conflict_id for item in ledger.conflicts]
    if len(conflict_ids) != len(set(conflict_ids)):
        issues.append("duplicate conflict_id")
    for conflict in ledger.conflicts:
        unknown = set(conflict.linked_record_sha256).difference(record_hashes)
        if unknown:
            issues.append(
                f"conflict {conflict.conflict_id} references unknown record hash"
            )
    return tuple(issues)


__all__ = [
    "RESEARCH_AUTHORITY_FLAGS",
    "ResearchConflictV1",
    "ResearchEvidenceClass",
    "ResearchEvidenceRecordV1",
    "ResearchLedgerV1",
    "validate_research_ledger",
]
