"""Validated commands for canonical B1 source and provenance records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from engine.calibration.hashing import stable_json_hash

from app.models.lab_sources import (
    EVIDENCE_WORKFLOW_STATES,
    SOURCE_DERIVATION_RELATIONS,
    SOURCE_REVIEW_STATES,
    SOURCE_TYPES,
    SOURCE_USE_ACTIONS,
    SOURCE_USE_ARTIFACT_SCOPES,
    SOURCE_USE_DECISIONS,
    WORKFLOW_SUBJECT_TYPES,
    LabEvidenceWorkflowEvent,
    LabSourceDerivationLink,
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
    LabSourceUseConstraintVersion,
)

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.lab import LabRepository


class SourceAuthorityError(ValueError):
    """Base class for stable B1 source-authority rejections."""

    code = "SOURCE_AUTHORITY_ERROR"


class SourceAuthorityConflictError(SourceAuthorityError):
    """A valid command that conflicts with immutable source history."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise SourceAuthorityError(f"{field} must not be blank")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _choice(value: str, field: str, allowed: tuple[str, ...]) -> str:
    normalized = _text(value, field)
    if normalized not in allowed:
        raise SourceAuthorityError(
            f"{field} must be one of {', '.join(allowed)}"
        )
    return normalized


def _digest(value: str, field: str) -> str:
    normalized = _text(value, field).casefold()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise SourceAuthorityError(
            f"{field} must be a 64-character hexadecimal digest"
        )
    return normalized


def _date_or_none(value: date | None, field: str) -> date | None:
    if value is not None and not isinstance(value, date):
        raise SourceAuthorityError(f"{field} must be a date")
    return value


def _tuple_text(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field) for value in values)
    if len(normalized) != len(set(normalized)):
        raise SourceAuthorityError(f"{field} must not contain duplicates")
    return normalized


def _relative_artifact_path(value: str | None) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    windows_path = PureWindowsPath(normalized)
    posix_path = PurePosixPath(normalized.replace("\\", "/"))
    if windows_path.is_absolute() or posix_path.is_absolute() or ".." in posix_path.parts:
        raise SourceAuthorityError(
            "preserved_artifact_path must be repository-relative"
        )
    sensitive_parts = {
        ".env",
        ".env.local",
        "secret",
        "secrets",
        "credential",
        "credentials",
        "token",
        "tokens",
    }
    if any(part.casefold() in sensitive_parts for part in posix_path.parts):
        raise SourceAuthorityError(
            "preserved_artifact_path must not reference a sensitive path"
        )
    return posix_path.as_posix()


def _dated(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


_SOURCE_USE_CONSTRAINT_KEYS = {
    "plan_or_tier",
    "jurisdiction",
    "valid_from",
    "valid_until",
    "max_records",
    "max_bytes",
    "retention_days",
    "freshness_required",
    "attribution_required",
    "share_alike_required",
    "noncommercial_only",
    "no_sublicense",
    "no_competing_service",
    "deletion_or_tombstone_required",
    "rate_limit_max_requests",
    "rate_limit_period_seconds",
    "unmodeled_constraints",
}
_SENSITIVE_LOCATOR_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}


def _optional_positive_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SourceAuthorityError(f"{field} must be a positive integer")
    return int(value)


def _optional_nonnegative_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SourceAuthorityError(f"{field} must be a non-negative integer")
    return int(value)


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise SourceAuthorityError(f"{field} must be a boolean")
    return value


def _constraint_bool(raw: Mapping[str, Any], field: str) -> bool:
    if field not in raw:
        return False
    value = raw[field]
    if not isinstance(value, bool):
        raise SourceAuthorityError(f"constraints.{field} must be a boolean")
    return value


def _mapping_keys(value: object) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key).casefold() for key in value}
        for item in value.values():
            keys.update(_mapping_keys(item))
        return keys
    if isinstance(value, (list, tuple)):
        nested: set[str] = set()
        for item in value:
            nested.update(_mapping_keys(item))
        return nested
    return set()


def _normalize_artifact_locator(raw: Mapping[str, Any]) -> dict[str, Any]:
    locator = dict(raw)
    if not locator:
        raise SourceAuthorityError("artifact_locator must not be empty")
    sensitive = _mapping_keys(locator) & _SENSITIVE_LOCATOR_KEYS
    if sensitive:
        raise SourceAuthorityError(
            "artifact_locator must not contain credentials: "
            + ", ".join(sorted(sensitive))
        )
    return locator


def _constraint_date(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    normalized = _text(str(value), field)
    try:
        return date.fromisoformat(normalized).isoformat()
    except ValueError as exc:
        raise SourceAuthorityError(f"{field} must be an ISO date") from exc


def _normalize_source_use_constraints(
    raw: Mapping[str, Any] | None,
) -> dict[str, Any]:
    supplied = dict(raw or {})
    unexpected = sorted(set(supplied) - _SOURCE_USE_CONSTRAINT_KEYS)
    if unexpected:
        raise SourceAuthorityError(
            "constraints contains unsupported fields: " + ", ".join(unexpected)
        )
    valid_from = _constraint_date(
        supplied.get("valid_from"),
        "constraints.valid_from",
    )
    valid_until = _constraint_date(
        supplied.get("valid_until"),
        "constraints.valid_until",
    )
    if (
        valid_from is not None
        and valid_until is not None
        and valid_from > valid_until
    ):
        raise SourceAuthorityError(
            "constraints.valid_from must not be after valid_until"
        )
    rate_max = _optional_positive_int(
        supplied.get("rate_limit_max_requests"),
        "constraints.rate_limit_max_requests",
    )
    rate_period = _optional_positive_int(
        supplied.get("rate_limit_period_seconds"),
        "constraints.rate_limit_period_seconds",
    )
    if (rate_max is None) != (rate_period is None):
        raise SourceAuthorityError(
            "rate-limit request count and period must be supplied together"
        )
    raw_unmodeled = supplied.get("unmodeled_constraints", ())
    if isinstance(raw_unmodeled, str) or not isinstance(
        raw_unmodeled,
        (list, tuple, set),
    ):
        raise SourceAuthorityError(
            "constraints.unmodeled_constraints must be a list of strings"
        )
    unmodeled = tuple(
        sorted(
            {
                _text(value, "constraints.unmodeled_constraints")
                for value in raw_unmodeled
            }
        )
    )
    return {
        "plan_or_tier": _optional_text(supplied.get("plan_or_tier")),
        "jurisdiction": _optional_text(supplied.get("jurisdiction")),
        "valid_from": valid_from,
        "valid_until": valid_until,
        "max_records": _optional_positive_int(
            supplied.get("max_records"),
            "constraints.max_records",
        ),
        "max_bytes": _optional_positive_int(
            supplied.get("max_bytes"),
            "constraints.max_bytes",
        ),
        "retention_days": _optional_nonnegative_int(
            supplied.get("retention_days"),
            "constraints.retention_days",
        ),
        "freshness_required": _constraint_bool(supplied, "freshness_required"),
        "attribution_required": _constraint_bool(
            supplied,
            "attribution_required",
        ),
        "share_alike_required": _constraint_bool(
            supplied,
            "share_alike_required",
        ),
        "noncommercial_only": _constraint_bool(
            supplied,
            "noncommercial_only",
        ),
        "no_sublicense": _constraint_bool(supplied, "no_sublicense"),
        "no_competing_service": _constraint_bool(
            supplied,
            "no_competing_service",
        ),
        "deletion_or_tombstone_required": _constraint_bool(
            supplied,
            "deletion_or_tombstone_required",
        ),
        "rate_limit_max_requests": rate_max,
        "rate_limit_period_seconds": rate_period,
        "unmodeled_constraints": list(unmodeled),
    }


def _normalize_source_rights(
    raw: Mapping[str, Any] | None,
    *,
    legacy_restriction: str | None,
) -> dict[str, Any]:
    scalar = _optional_text(legacy_restriction)
    if raw is None:
        return {
            "reuse_status": "UNKNOWN",
            "license_or_reuse_restriction": (
                scalar or "UNVERIFIED_LEGACY_ROW"
            ),
            "license_url": None,
            "redistribution_allowed": False,
            "spdx_identifier": None,
            "notes": "No verified structured rights object was supplied.",
        }

    allowed = {
        "reuse_status",
        "license_or_reuse_restriction",
        "license_url",
        "redistribution_allowed",
        "spdx_identifier",
        "notes",
    }
    unexpected = sorted(set(raw) - allowed)
    if unexpected:
        raise SourceAuthorityError(
            "rights contains unsupported fields: " + ", ".join(unexpected)
        )
    status = _choice(
        str(raw.get("reuse_status") or "UNKNOWN").strip().upper(),
        "rights.reuse_status",
        ("PERMITTED", "RESTRICTED", "UNKNOWN"),
    )
    restriction = _text(
        str(raw.get("license_or_reuse_restriction") or ""),
        "rights.license_or_reuse_restriction",
    )
    redistribution = raw.get("redistribution_allowed")
    if not isinstance(redistribution, bool):
        raise SourceAuthorityError(
            "rights.redistribution_allowed must be a boolean"
        )
    if status == "UNKNOWN" and redistribution:
        raise SourceAuthorityError(
            "UNKNOWN rights cannot authorize redistribution"
        )
    if scalar is not None and scalar != restriction:
        raise SourceAuthorityError(
            "license_or_reuse_restriction disagrees with rights object"
        )
    return {
        "reuse_status": status,
        "license_or_reuse_restriction": restriction,
        "license_url": _optional_text(raw.get("license_url")),
        "redistribution_allowed": redistribution,
        "spdx_identifier": _optional_text(raw.get("spdx_identifier")),
        "notes": _optional_text(raw.get("notes")),
    }


def _normalize_relation_scopes(
    raw_scopes: tuple[Mapping[str, str], ...],
) -> tuple[dict[str, str], ...]:
    if not raw_scopes:
        raise SourceAuthorityError(
            "relation_scopes must contain at least one claim-scoped record"
        )
    required = {"support_scope", "supported_claim_path", "rationale"}
    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(raw_scopes):
        if set(raw) != required:
            raise SourceAuthorityError(
                f"relation_scopes[{index}] must contain exactly "
                "support_scope, supported_claim_path, and rationale"
            )
        normalized.append(
            {
                "support_scope": _text(
                    raw["support_scope"],
                    f"relation_scopes[{index}].support_scope",
                ),
                "supported_claim_path": _text(
                    raw["supported_claim_path"],
                    f"relation_scopes[{index}].supported_claim_path",
                ),
                "rationale": _text(
                    raw["rationale"],
                    f"relation_scopes[{index}].rationale",
                ),
            }
        )
    canonical = tuple(
        sorted(
            normalized,
            key=lambda row: (
                row["support_scope"],
                row["supported_claim_path"],
                row["rationale"],
            ),
        )
    )
    if len(canonical) != len(
        {
            (
                row["support_scope"],
                row["supported_claim_path"],
                row["rationale"],
            )
            for row in canonical
        }
    ):
        raise SourceAuthorityError("relation_scopes must not contain duplicates")
    return canonical


@dataclass(frozen=True, slots=True)
class SourceDocumentInput:
    schema_version: str
    source_type: str
    title: str
    artifact_sha256: str
    language: str
    review_state: str
    independence_group: str
    authors: tuple[str, ...] = ()
    issuing_organization: str | None = None
    container_title: str | None = None
    publisher_or_authority: str | None = None
    identifiers: dict[str, str] | None = None
    publication_date: date | None = None
    revision_date: date | None = None
    effective_date: date | None = None
    retrieval_date: date | None = None
    edition_or_amendment: str | None = None
    default_locator: dict[str, Any] | None = None
    license_or_reuse_restriction: str | None = None
    rights: dict[str, Any] | None = None
    original_unit: str | None = None
    original_terminology: str | None = None
    reviewer_pseudonym: str | None = None
    preserved_artifact_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "schema_version",
            _text(self.schema_version, "schema_version"),
        )
        object.__setattr__(
            self,
            "source_type",
            _choice(self.source_type, "source_type", SOURCE_TYPES),
        )
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(
            self,
            "artifact_sha256",
            _digest(self.artifact_sha256, "artifact_sha256"),
        )
        object.__setattr__(self, "language", _text(self.language, "language"))
        object.__setattr__(
            self,
            "review_state",
            _choice(self.review_state, "review_state", SOURCE_REVIEW_STATES),
        )
        object.__setattr__(
            self,
            "independence_group",
            _text(self.independence_group, "independence_group"),
        )
        authors = tuple(_text(author, "authors") for author in self.authors)
        if len(authors) != len(set(authors)):
            raise SourceAuthorityError("authors must not contain duplicates")
        organization = _optional_text(self.issuing_organization)
        if not authors and organization is None:
            raise SourceAuthorityError(
                "authors or issuing_organization must be provided"
            )
        identifiers = {
            _text(key, "identifier key"): _text(value, "identifier value")
            for key, value in (self.identifiers or {}).items()
        }
        object.__setattr__(self, "authors", authors)
        object.__setattr__(self, "issuing_organization", organization)
        object.__setattr__(
            self,
            "container_title",
            _optional_text(self.container_title),
        )
        object.__setattr__(
            self,
            "publisher_or_authority",
            _optional_text(self.publisher_or_authority),
        )
        object.__setattr__(self, "identifiers", identifiers)
        for field in (
            "publication_date",
            "revision_date",
            "effective_date",
            "retrieval_date",
        ):
            object.__setattr__(
                self,
                field,
                _date_or_none(getattr(self, field), field),
            )
        object.__setattr__(
            self,
            "edition_or_amendment",
            _optional_text(self.edition_or_amendment),
        )
        object.__setattr__(
            self,
            "default_locator",
            dict(self.default_locator or {}),
        )
        rights = _normalize_source_rights(
            self.rights,
            legacy_restriction=self.license_or_reuse_restriction,
        )
        object.__setattr__(self, "rights", rights)
        object.__setattr__(
            self,
            "license_or_reuse_restriction",
            rights["license_or_reuse_restriction"],
        )
        object.__setattr__(
            self,
            "original_unit",
            _optional_text(self.original_unit),
        )
        object.__setattr__(
            self,
            "original_terminology",
            _optional_text(self.original_terminology),
        )
        object.__setattr__(
            self,
            "reviewer_pseudonym",
            _optional_text(self.reviewer_pseudonym),
        )
        object.__setattr__(
            self,
            "preserved_artifact_path",
            _relative_artifact_path(self.preserved_artifact_path),
        )


@dataclass(frozen=True, slots=True)
class ExtractionRecordInput:
    source_version_id: str
    locator: dict[str, Any]
    structure_context: dict[str, Any]
    original_wording: str | None
    original_value: dict[str, Any] | None
    parsed_value: dict[str, Any] | None
    normalization: dict[str, Any]
    parser_or_model_version: str
    reviewer_pseudonym: str | None
    uncertainty: dict[str, Any]
    ambiguity: tuple[str, ...]
    output_observation_id: str | None
    input_sha256: str
    output_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_version_id",
            _text(self.source_version_id, "source_version_id"),
        )
        object.__setattr__(self, "locator", dict(self.locator))
        object.__setattr__(
            self,
            "structure_context",
            dict(self.structure_context),
        )
        original_wording = _optional_text(self.original_wording)
        original_value = (
            dict(self.original_value)
            if self.original_value is not None
            else None
        )
        if original_wording is None and original_value is None:
            raise SourceAuthorityError(
                "original wording or original value must be provided"
            )
        object.__setattr__(self, "original_wording", original_wording)
        object.__setattr__(self, "original_value", original_value)
        object.__setattr__(
            self,
            "parsed_value",
            dict(self.parsed_value) if self.parsed_value is not None else None,
        )
        object.__setattr__(
            self,
            "normalization",
            dict(self.normalization),
        )
        object.__setattr__(
            self,
            "parser_or_model_version",
            _text(
                self.parser_or_model_version,
                "parser_or_model_version",
            ),
        )
        object.__setattr__(
            self,
            "reviewer_pseudonym",
            _optional_text(self.reviewer_pseudonym),
        )
        object.__setattr__(self, "uncertainty", dict(self.uncertainty))
        object.__setattr__(
            self,
            "ambiguity",
            _tuple_text(self.ambiguity, "ambiguity"),
        )
        object.__setattr__(
            self,
            "output_observation_id",
            _optional_text(self.output_observation_id),
        )
        object.__setattr__(
            self,
            "input_sha256",
            _digest(self.input_sha256, "input_sha256"),
        )
        object.__setattr__(
            self,
            "output_sha256",
            _digest(self.output_sha256, "output_sha256"),
        )


@dataclass(frozen=True, slots=True)
class SourceUseConstraintInput:
    """One exact, source-declared operation constraint for B1 admission."""

    subject_source_version_id: str
    terms_source_version_id: str
    artifact_scope: str
    artifact_locator: dict[str, Any]
    channel: str
    intended_action: str
    purpose_context: str
    decision: str
    constraints: dict[str, Any]
    terms_retrieval_date: date
    review_state: str
    terms_effective_date: date | None = None
    reviewer_pseudonym: str | None = None
    legal_review_required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_source_version_id",
            _text(
                self.subject_source_version_id,
                "subject_source_version_id",
            ),
        )
        object.__setattr__(
            self,
            "terms_source_version_id",
            _text(self.terms_source_version_id, "terms_source_version_id"),
        )
        object.__setattr__(
            self,
            "artifact_scope",
            _choice(
                self.artifact_scope,
                "artifact_scope",
                SOURCE_USE_ARTIFACT_SCOPES,
            ),
        )
        object.__setattr__(
            self,
            "artifact_locator",
            _normalize_artifact_locator(self.artifact_locator),
        )
        object.__setattr__(self, "channel", _text(self.channel, "channel"))
        object.__setattr__(
            self,
            "intended_action",
            _choice(
                self.intended_action,
                "intended_action",
                SOURCE_USE_ACTIONS,
            ),
        )
        object.__setattr__(
            self,
            "purpose_context",
            _text(self.purpose_context, "purpose_context"),
        )
        object.__setattr__(
            self,
            "decision",
            _choice(self.decision, "decision", SOURCE_USE_DECISIONS),
        )
        object.__setattr__(
            self,
            "constraints",
            _normalize_source_use_constraints(self.constraints),
        )
        object.__setattr__(
            self,
            "terms_retrieval_date",
            _date_or_none(
                self.terms_retrieval_date,
                "terms_retrieval_date",
            ),
        )
        if self.terms_retrieval_date is None:
            raise SourceAuthorityError("terms_retrieval_date is required")
        object.__setattr__(
            self,
            "terms_effective_date",
            _date_or_none(self.terms_effective_date, "terms_effective_date"),
        )
        object.__setattr__(
            self,
            "review_state",
            _choice(self.review_state, "review_state", SOURCE_REVIEW_STATES),
        )
        reviewer = _optional_text(self.reviewer_pseudonym)
        if self.review_state == "REVIEWED" and reviewer is None:
            raise SourceAuthorityError(
                "reviewer_pseudonym is required for REVIEWED constraints"
            )
        object.__setattr__(self, "reviewer_pseudonym", reviewer)
        if not isinstance(self.legal_review_required, bool):
            raise SourceAuthorityError("legal_review_required must be boolean")


@dataclass(frozen=True, slots=True)
class SourceUseRequest:
    """Exact proposed source operation evaluated without legal promotion."""

    subject_source_version_id: str
    artifact_scope: str
    artifact_locator: dict[str, Any]
    channel: str
    intended_action: str
    purpose_context: str
    as_of_date: date
    plan_or_tier: str | None = None
    jurisdiction: str | None = None
    requested_records: int | None = None
    requested_bytes: int | None = None
    retention_days: int | None = None
    fresh_fetch: bool | None = None
    attribution_planned: bool | None = None
    share_alike_planned: bool | None = None
    commercial_use: bool | None = None
    sublicense: bool | None = None
    competing_service: bool | None = None
    deletion_or_tombstone_supported: bool | None = None
    rate_limit_compliance_confirmed: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_source_version_id",
            _text(
                self.subject_source_version_id,
                "subject_source_version_id",
            ),
        )
        object.__setattr__(
            self,
            "artifact_scope",
            _choice(
                self.artifact_scope,
                "artifact_scope",
                SOURCE_USE_ARTIFACT_SCOPES,
            ),
        )
        object.__setattr__(
            self,
            "artifact_locator",
            _normalize_artifact_locator(self.artifact_locator),
        )
        object.__setattr__(self, "channel", _text(self.channel, "channel"))
        object.__setattr__(
            self,
            "intended_action",
            _choice(
                self.intended_action,
                "intended_action",
                SOURCE_USE_ACTIONS,
            ),
        )
        object.__setattr__(
            self,
            "purpose_context",
            _text(self.purpose_context, "purpose_context"),
        )
        object.__setattr__(
            self,
            "as_of_date",
            _date_or_none(self.as_of_date, "as_of_date"),
        )
        if self.as_of_date is None:
            raise SourceAuthorityError("as_of_date is required")
        object.__setattr__(
            self,
            "plan_or_tier",
            _optional_text(self.plan_or_tier),
        )
        object.__setattr__(
            self,
            "jurisdiction",
            _optional_text(self.jurisdiction),
        )
        object.__setattr__(
            self,
            "requested_records",
            _optional_positive_int(self.requested_records, "requested_records"),
        )
        object.__setattr__(
            self,
            "requested_bytes",
            _optional_positive_int(self.requested_bytes, "requested_bytes"),
        )
        object.__setattr__(
            self,
            "retention_days",
            _optional_nonnegative_int(self.retention_days, "retention_days"),
        )
        for field in (
            "fresh_fetch",
            "attribution_planned",
            "share_alike_planned",
            "commercial_use",
            "sublicense",
            "competing_service",
            "deletion_or_tombstone_supported",
            "rate_limit_compliance_confirmed",
        ):
            object.__setattr__(
                self,
                field,
                _optional_bool(getattr(self, field), field),
            )


@dataclass(frozen=True, slots=True)
class SourceUseAssessment:
    """Deterministic source-declaration result; never a legal conclusion."""

    schema_version: str
    assessment_state: str
    authority_state: str
    subject_source_version_id: str
    reason_codes: tuple[str, ...]
    constraint_version_ids: tuple[str, ...]
    constraint_record_sha256s: tuple[str, ...]
    request_sha256: str
    assessment_sha256: str


def _source_payload(
    *,
    source_id: str,
    version_number: int,
    parent_record_sha256: str | None,
    command: SourceDocumentInput,
) -> dict[str, Any]:
    return {
        "schema": "lab-source-document-v2",
        "source_id": source_id,
        "version_number": version_number,
        "schema_version": command.schema_version,
        "source_type": command.source_type,
        "title": command.title,
        "authors": command.authors,
        "issuing_organization": command.issuing_organization,
        "container_title": command.container_title,
        "publisher_or_authority": command.publisher_or_authority,
        "identifiers": command.identifiers,
        "publication_date": _dated(command.publication_date),
        "revision_date": _dated(command.revision_date),
        "effective_date": _dated(command.effective_date),
        "retrieval_date": _dated(command.retrieval_date),
        "edition_or_amendment": command.edition_or_amendment,
        "default_locator": command.default_locator,
        "artifact_sha256": command.artifact_sha256,
        "license_or_reuse_restriction": command.license_or_reuse_restriction,
        "rights": command.rights,
        "language": command.language,
        "original_unit": command.original_unit,
        "original_terminology": command.original_terminology,
        "reviewer_pseudonym": command.reviewer_pseudonym,
        "review_state": command.review_state,
        "independence_group": command.independence_group,
        "preserved_artifact_path": command.preserved_artifact_path,
        "parent_record_sha256": parent_record_sha256,
    }


def _source_use_constraint_payload(
    *,
    constraint_id: str,
    version_number: int,
    subject_record_sha256: str,
    terms_record_sha256: str,
    parent_record_sha256: str | None,
    command: SourceUseConstraintInput,
) -> dict[str, Any]:
    return {
        "schema": "lab-source-use-constraint-v1",
        "constraint_id": constraint_id,
        "version_number": version_number,
        "subject_source_version_id": command.subject_source_version_id,
        "subject_record_sha256": subject_record_sha256,
        "terms_source_version_id": command.terms_source_version_id,
        "terms_record_sha256": terms_record_sha256,
        "artifact_scope": command.artifact_scope,
        "artifact_locator": command.artifact_locator,
        "channel": command.channel,
        "intended_action": command.intended_action,
        "purpose_context": command.purpose_context,
        "decision": command.decision,
        "constraints": command.constraints,
        "terms_effective_date": _dated(command.terms_effective_date),
        "terms_retrieval_date": _dated(command.terms_retrieval_date),
        "reviewer_pseudonym": command.reviewer_pseudonym,
        "review_state": command.review_state,
        "legal_review_required": command.legal_review_required,
        "parent_record_sha256": parent_record_sha256,
    }


def _source_use_request_payload(request: SourceUseRequest) -> dict[str, Any]:
    return {
        "schema": "lab-source-use-request-v1",
        "subject_source_version_id": request.subject_source_version_id,
        "artifact_scope": request.artifact_scope,
        "artifact_locator": request.artifact_locator,
        "channel": request.channel,
        "intended_action": request.intended_action,
        "purpose_context": request.purpose_context,
        "as_of_date": _dated(request.as_of_date),
        "plan_or_tier": request.plan_or_tier,
        "jurisdiction": request.jurisdiction,
        "requested_records": request.requested_records,
        "requested_bytes": request.requested_bytes,
        "retention_days": request.retention_days,
        "fresh_fetch": request.fresh_fetch,
        "attribution_planned": request.attribution_planned,
        "share_alike_planned": request.share_alike_planned,
        "commercial_use": request.commercial_use,
        "sublicense": request.sublicense,
        "competing_service": request.competing_service,
        "deletion_or_tombstone_supported": (
            request.deletion_or_tombstone_supported
        ),
        "rate_limit_compliance_confirmed": (
            request.rate_limit_compliance_confirmed
        ),
    }


def _source_use_constraint_reason_codes(
    constraints: Mapping[str, Any],
    request: SourceUseRequest,
) -> tuple[str, ...]:
    reasons: set[str] = set()
    if (
        constraints["plan_or_tier"] is not None
        and constraints["plan_or_tier"] != request.plan_or_tier
    ):
        reasons.add("PLAN_OR_TIER_MISMATCH")
    if (
        constraints["jurisdiction"] is not None
        and constraints["jurisdiction"] != request.jurisdiction
    ):
        reasons.add("JURISDICTION_MISMATCH")
    as_of = request.as_of_date.isoformat()
    if constraints["valid_from"] is not None and as_of < constraints["valid_from"]:
        reasons.add("ASSERTION_NOT_YET_VALID")
    if constraints["valid_until"] is not None and as_of > constraints["valid_until"]:
        reasons.add("ASSERTION_EXPIRED")

    for request_field, constraint_field, missing_code, exceeded_code in (
        (
            "requested_records",
            "max_records",
            "REQUESTED_RECORDS_REQUIRED",
            "MAX_RECORDS_EXCEEDED",
        ),
        (
            "requested_bytes",
            "max_bytes",
            "REQUESTED_BYTES_REQUIRED",
            "MAX_BYTES_EXCEEDED",
        ),
        (
            "retention_days",
            "retention_days",
            "RETENTION_DAYS_REQUIRED",
            "RETENTION_LIMIT_EXCEEDED",
        ),
    ):
        limit = constraints[constraint_field]
        if limit is None:
            continue
        actual = getattr(request, request_field)
        if actual is None:
            reasons.add(missing_code)
        elif actual > limit:
            reasons.add(exceeded_code)

    for required_field, request_field, missing_code in (
        ("freshness_required", "fresh_fetch", "FRESH_FETCH_REQUIRED"),
        (
            "attribution_required",
            "attribution_planned",
            "ATTRIBUTION_PLAN_REQUIRED",
        ),
        (
            "share_alike_required",
            "share_alike_planned",
            "SHARE_ALIKE_PLAN_REQUIRED",
        ),
        (
            "deletion_or_tombstone_required",
            "deletion_or_tombstone_supported",
            "DELETION_OR_TOMBSTONE_SUPPORT_REQUIRED",
        ),
    ):
        if constraints[required_field] and getattr(request, request_field) is not True:
            reasons.add(missing_code)

    for required_field, request_field, context_code, violation_code in (
        (
            "noncommercial_only",
            "commercial_use",
            "COMMERCIAL_CONTEXT_REQUIRED",
            "NONCOMMERCIAL_ONLY",
        ),
        (
            "no_sublicense",
            "sublicense",
            "SUBLICENSE_CONTEXT_REQUIRED",
            "SUBLICENSE_PROHIBITED",
        ),
        (
            "no_competing_service",
            "competing_service",
            "COMPETING_SERVICE_CONTEXT_REQUIRED",
            "COMPETING_SERVICE_PROHIBITED",
        ),
    ):
        if not constraints[required_field]:
            continue
        actual = getattr(request, request_field)
        if actual is None:
            reasons.add(context_code)
        elif actual:
            reasons.add(violation_code)

    if constraints["rate_limit_max_requests"] is not None and (
        request.rate_limit_compliance_confirmed is not True
    ):
        reasons.add("RATE_LIMIT_COMPLIANCE_REQUIRED")
    if constraints["unmodeled_constraints"]:
        reasons.add("UNMODELED_SOURCE_USE_CONSTRAINT")
    return tuple(sorted(reasons))


def _source_use_assessment(
    *,
    request: SourceUseRequest,
    assessment_state: str,
    reason_codes: set[str] | tuple[str, ...],
    constraints: tuple[LabSourceUseConstraintVersion, ...],
) -> SourceUseAssessment:
    ordered = tuple(sorted(constraints, key=lambda row: (row.record_sha256, row.id)))
    request_sha256 = stable_json_hash(_source_use_request_payload(request))
    reasons = tuple(sorted(set(reason_codes)))
    version_ids = tuple(row.id for row in ordered)
    record_hashes = tuple(row.record_sha256 for row in ordered)
    payload = {
        "schema": "lab-source-use-assessment-v1",
        "assessment_state": assessment_state,
        "authority_state": "SOURCE_DECLARATION_ONLY_NOT_LEGAL_CONCLUSION",
        "subject_source_version_id": request.subject_source_version_id,
        "reason_codes": reasons,
        "constraint_version_ids": version_ids,
        "constraint_record_sha256s": record_hashes,
        "request_sha256": request_sha256,
    }
    return SourceUseAssessment(
        schema_version="lab-source-use-assessment-v1",
        assessment_state=assessment_state,
        authority_state="SOURCE_DECLARATION_ONLY_NOT_LEGAL_CONCLUSION",
        subject_source_version_id=request.subject_source_version_id,
        reason_codes=reasons,
        constraint_version_ids=version_ids,
        constraint_record_sha256s=record_hashes,
        request_sha256=request_sha256,
        assessment_sha256=stable_json_hash(payload),
    )


def _candidate_date(value: Any, field: str) -> date | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise SourceAuthorityError(f"{field} must be an ISO date") from exc


def source_document_registration_from_candidate(
    candidate: Mapping[str, Any],
) -> tuple[str, SourceDocumentInput]:
    """Verify and map one immutable B1 staging candidate for registration."""

    if candidate.get("candidate_schema_version") != (
        "b1_source_document_candidate_v1"
    ):
        raise SourceAuthorityError("unsupported B1 source candidate schema")
    supplied_hash = _digest(
        str(candidate.get("candidate_sha256") or ""),
        "candidate_sha256",
    )
    payload = dict(candidate)
    payload.pop("candidate_sha256", None)
    if stable_json_hash(payload) != supplied_hash:
        raise SourceAuthorityError("B1 source candidate hash mismatch")
    external_source_id = _text(
        str(candidate.get("source_id") or ""),
        "source_id",
    )
    identifiers = dict(candidate.get("identifiers") or {})
    identifiers["staged_source_id"] = external_source_id
    identifiers["candidate_sha256"] = supplied_hash
    command = SourceDocumentInput(
        schema_version=_text(
            str(candidate.get("schema_version") or ""),
            "schema_version",
        ),
        source_type=_text(
            str(candidate.get("source_type") or ""),
            "source_type",
        ),
        title=_text(str(candidate.get("title") or ""), "title"),
        artifact_sha256=_text(
            str(candidate.get("artifact_sha256") or ""),
            "artifact_sha256",
        ),
        language=_text(str(candidate.get("language") or ""), "language"),
        review_state=_text(
            str(candidate.get("review_state") or ""),
            "review_state",
        ),
        independence_group=_text(
            str(candidate.get("independence_group") or ""),
            "independence_group",
        ),
        authors=tuple(str(value) for value in candidate.get("authors") or ()),
        issuing_organization=candidate.get("issuing_organization"),
        container_title=candidate.get("container_title"),
        publisher_or_authority=candidate.get("publisher_or_authority"),
        identifiers=identifiers,
        publication_date=_candidate_date(
            candidate.get("publication_date"),
            "publication_date",
        ),
        revision_date=_candidate_date(
            candidate.get("revision_date"),
            "revision_date",
        ),
        effective_date=_candidate_date(
            candidate.get("effective_date"),
            "effective_date",
        ),
        retrieval_date=_candidate_date(
            candidate.get("retrieval_date"),
            "retrieval_date",
        ),
        edition_or_amendment=candidate.get("edition_or_amendment"),
        default_locator=dict(candidate.get("default_locator") or {}),
        license_or_reuse_restriction=candidate.get(
            "license_or_reuse_restriction"
        ),
        rights=dict(candidate.get("rights") or {}),
        preserved_artifact_path=candidate.get("preserved_artifact_path"),
    )
    stable_source_id = str(
        uuid5(NAMESPACE_URL, f"perfume-chem:b1:{external_source_id}")
    )
    return stable_source_id, command


def source_derivation_scopes_from_candidate(
    candidate: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Verify and extract the claim scope from a B1 derivation candidate."""

    if candidate.get("candidate_schema_version") != (
        "b1_source_derivation_candidate_v1"
    ):
        raise SourceAuthorityError("unsupported B1 derivation candidate schema")
    supplied_hash = _digest(
        str(candidate.get("record_sha256") or ""),
        "record_sha256",
    )
    payload = dict(candidate)
    payload.pop("record_sha256", None)
    if stable_json_hash(payload) != supplied_hash:
        raise SourceAuthorityError("B1 derivation candidate hash mismatch")
    return _normalize_relation_scopes(
        (
            {
                "support_scope": str(candidate.get("support_scope") or ""),
                "supported_claim_path": str(
                    candidate.get("supported_claim_path") or ""
                ),
                "rationale": str(candidate.get("rationale") or ""),
            },
        )
    )


NORMAL_WORKFLOW = (
    "STAGED",
    "PARSED",
    "IDENTITY_RESOLVED",
    "UNIT_NORMALIZED",
    "CONDITION_NORMALIZED",
    "CONFLICT_CHECKED",
    "HUMAN_REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE",
)


class LabSourceServiceMixin:
    """Source commands that use the canonical service transaction owner."""

    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def register_source_document(
        self,
        command: SourceDocumentInput,
        *,
        parent_version_id: str | None = None,
        source_id: str | None = None,
    ) -> LabSourceDocumentVersion:
        explicit_source_id = (
            _text(source_id, "source_id") if source_id is not None else None
        )
        async with self._transaction():
            if parent_version_id is None:
                stable_source_id = explicit_source_id or str(uuid4())
                existing = await self.repository.latest_source_document_version(
                    stable_source_id
                )
                if existing is not None:
                    raise SourceAuthorityConflictError(
                        "SOURCE_ID_ALREADY_EXISTS",
                        "Source ID already has an immutable version.",
                    )
                parent = None
                version_number = 1
            else:
                parent = await self.repository.get_source_document_version(
                    _text(parent_version_id, "parent_version_id")
                )
                if parent is None:
                    raise SourceAuthorityConflictError(
                        "SOURCE_PARENT_NOT_FOUND",
                        f"Source parent not found: {parent_version_id}.",
                    )
                latest = await self.repository.latest_source_document_version(
                    parent.source_id
                )
                if latest is None or latest.id != parent.id:
                    raise SourceAuthorityConflictError(
                        "SOURCE_PARENT_NOT_LATEST",
                        "Source revisions must use the latest immutable version.",
                    )
                if (
                    explicit_source_id is not None
                    and explicit_source_id != parent.source_id
                ):
                    raise SourceAuthorityConflictError(
                        "SOURCE_ID_PARENT_MISMATCH",
                        "Source revision ID must match its parent.",
                    )
                stable_source_id = parent.source_id
                version_number = parent.version_number + 1

            parent_hash = parent.record_sha256 if parent is not None else None
            payload = _source_payload(
                source_id=stable_source_id,
                version_number=version_number,
                parent_record_sha256=parent_hash,
                command=command,
            )
            record_hash = stable_json_hash(payload)
            duplicate = await self.repository.source_record_by_hash(record_hash)
            if duplicate is not None:
                raise SourceAuthorityConflictError(
                    "SOURCE_RECORD_ALREADY_EXISTS",
                    "An identical immutable source record already exists.",
                )
            source = await self.repository.add(
                LabSourceDocumentVersion(
                    source_id=stable_source_id,
                    version_number=version_number,
                    schema_version=command.schema_version,
                    source_type=command.source_type,
                    title=command.title,
                    authors_json=list(command.authors),
                    issuing_organization=command.issuing_organization,
                    container_title=command.container_title,
                    publisher_or_authority=command.publisher_or_authority,
                    identifiers_json=dict(command.identifiers or {}),
                    publication_date=command.publication_date,
                    revision_date=command.revision_date,
                    effective_date=command.effective_date,
                    retrieval_date=command.retrieval_date,
                    edition_or_amendment=command.edition_or_amendment,
                    default_locator_json=dict(command.default_locator or {}),
                    artifact_sha256=command.artifact_sha256,
                    license_or_reuse_restriction=(
                        command.license_or_reuse_restriction
                    ),
                    rights_json=dict(command.rights or {}),
                    language=command.language,
                    original_unit=command.original_unit,
                    original_terminology=command.original_terminology,
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    review_state=command.review_state,
                    supersedes_version_id=parent.id if parent is not None else None,
                    independence_group=command.independence_group,
                    preserved_artifact_path=command.preserved_artifact_path,
                    parent_record_sha256=parent_hash,
                    record_sha256=record_hash,
                )
            )
            await self._append_initial_workflow_event(
                subject_type="SOURCE_VERSION",
                subject_id=source.id,
            )
            return source

    async def register_source_use_constraint(
        self,
        command: SourceUseConstraintInput,
        *,
        parent_version_id: str | None = None,
        constraint_id: str | None = None,
    ) -> LabSourceUseConstraintVersion:
        """Append one exact source-use assertion without granting authority."""

        explicit_constraint_id = (
            _text(constraint_id, "constraint_id")
            if constraint_id is not None
            else None
        )
        async with self._transaction():
            subject = await self.repository.get_source_document_version(
                command.subject_source_version_id
            )
            terms = await self.repository.get_source_document_version(
                command.terms_source_version_id
            )
            if subject is None:
                raise SourceAuthorityConflictError(
                    "SOURCE_USE_SUBJECT_NOT_FOUND",
                    "The exact subject source version does not exist.",
                )
            if terms is None:
                raise SourceAuthorityConflictError(
                    "SOURCE_USE_TERMS_NOT_FOUND",
                    "The exact terms source version does not exist.",
                )

            if parent_version_id is None:
                stable_constraint_id = explicit_constraint_id or str(uuid4())
                existing = (
                    await self.repository.latest_source_use_constraint_version(
                        stable_constraint_id
                    )
                )
                if existing is not None:
                    raise SourceAuthorityConflictError(
                        "SOURCE_USE_CONSTRAINT_ID_ALREADY_EXISTS",
                        "Constraint ID already has an immutable version.",
                    )
                parent = None
                version_number = 1
            else:
                parent = (
                    await self.repository.get_source_use_constraint_version(
                        _text(parent_version_id, "parent_version_id")
                    )
                )
                if parent is None:
                    raise SourceAuthorityConflictError(
                        "SOURCE_USE_PARENT_NOT_FOUND",
                        "The source-use constraint parent does not exist.",
                    )
                latest = (
                    await self.repository.latest_source_use_constraint_version(
                        parent.constraint_id
                    )
                )
                if latest is None or latest.id != parent.id:
                    raise SourceAuthorityConflictError(
                        "SOURCE_USE_PARENT_NOT_LATEST",
                        "Constraint revisions must use the latest version.",
                    )
                if (
                    explicit_constraint_id is not None
                    and explicit_constraint_id != parent.constraint_id
                ):
                    raise SourceAuthorityConflictError(
                        "SOURCE_USE_CONSTRAINT_ID_PARENT_MISMATCH",
                        "Constraint revision ID must match its parent.",
                    )
                immutable_scope = (
                    command.subject_source_version_id,
                    command.artifact_scope,
                    command.artifact_locator,
                    command.channel,
                    command.intended_action,
                    command.purpose_context,
                )
                parent_scope = (
                    parent.subject_source_version_id,
                    parent.artifact_scope,
                    parent.artifact_locator_json,
                    parent.channel,
                    parent.intended_action,
                    parent.purpose_context,
                )
                if immutable_scope != parent_scope:
                    raise SourceAuthorityConflictError(
                        "SOURCE_USE_SCOPE_REVISION_FORBIDDEN",
                        "A revision may change terms or decision, not the exact "
                        "subject/artifact/channel/action/purpose scope.",
                    )
                stable_constraint_id = parent.constraint_id
                version_number = parent.version_number + 1

            parent_hash = parent.record_sha256 if parent is not None else None
            payload = _source_use_constraint_payload(
                constraint_id=stable_constraint_id,
                version_number=version_number,
                subject_record_sha256=subject.record_sha256,
                terms_record_sha256=terms.record_sha256,
                parent_record_sha256=parent_hash,
                command=command,
            )
            record_hash = stable_json_hash(payload)
            duplicate = (
                await self.repository.source_use_constraint_record_by_hash(
                    record_hash
                )
            )
            if duplicate is not None:
                raise SourceAuthorityConflictError(
                    "SOURCE_USE_CONSTRAINT_RECORD_ALREADY_EXISTS",
                    "An identical immutable source-use assertion already exists.",
                )
            return await self.repository.add(
                LabSourceUseConstraintVersion(
                    constraint_id=stable_constraint_id,
                    version_number=version_number,
                    subject_source_version_id=(
                        command.subject_source_version_id
                    ),
                    terms_source_version_id=command.terms_source_version_id,
                    artifact_scope=command.artifact_scope,
                    artifact_locator_json=dict(command.artifact_locator),
                    channel=command.channel,
                    intended_action=command.intended_action,
                    purpose_context=command.purpose_context,
                    decision=command.decision,
                    constraints_json=dict(command.constraints),
                    terms_effective_date=command.terms_effective_date,
                    terms_retrieval_date=command.terms_retrieval_date,
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    review_state=command.review_state,
                    legal_review_required=command.legal_review_required,
                    supersedes_version_id=(
                        parent.id if parent is not None else None
                    ),
                    parent_record_sha256=parent_hash,
                    record_sha256=record_hash,
                )
            )

    async def assess_source_use(
        self,
        request: SourceUseRequest,
    ) -> SourceUseAssessment:
        """Fail closed unless an exact reviewed declaration satisfies the request."""

        subject = await self.repository.get_source_document_version(
            request.subject_source_version_id
        )
        if subject is None:
            return _source_use_assessment(
                request=request,
                assessment_state="HOLD",
                reason_codes={"SUBJECT_SOURCE_NOT_FOUND"},
                constraints=(),
            )

        rows = await self.repository.source_use_constraints(subject.id)
        latest_by_constraint: dict[str, LabSourceUseConstraintVersion] = {}
        for row in rows:
            current = latest_by_constraint.get(row.constraint_id)
            if current is None or row.version_number > current.version_number:
                latest_by_constraint[row.constraint_id] = row
        matching = tuple(
            row
            for row in latest_by_constraint.values()
            if row.artifact_scope == request.artifact_scope
            and row.artifact_locator_json == request.artifact_locator
            and row.channel == request.channel
            and row.intended_action == request.intended_action
            and row.purpose_context == request.purpose_context
        )
        if not matching:
            return _source_use_assessment(
                request=request,
                assessment_state="HOLD",
                reason_codes={"NO_EXACT_SOURCE_USE_ASSERTION"},
                constraints=(),
            )

        reasons: set[str] = set()
        if subject.review_state != "REVIEWED":
            reasons.add("SUBJECT_SOURCE_NOT_REVIEWED")

        normalized_constraints: dict[str, dict[str, Any]] = {}
        for row in matching:
            if row.review_state != "REVIEWED":
                reasons.add("SOURCE_USE_ASSERTION_NOT_REVIEWED")
            if row.legal_review_required:
                reasons.add("LEGAL_REVIEW_REQUIRED")
            if row.terms_effective_date is not None and (
                request.as_of_date < row.terms_effective_date
            ):
                reasons.add("TERMS_NOT_YET_EFFECTIVE")
            if request.as_of_date < row.terms_retrieval_date:
                reasons.add("TERMS_NOT_RETRIEVED_AS_OF_REQUEST")
            terms = await self.repository.get_source_document_version(
                row.terms_source_version_id
            )
            if terms is None:
                reasons.add("TERMS_SOURCE_NOT_FOUND")
            elif terms.review_state != "REVIEWED":
                reasons.add("TERMS_SOURCE_NOT_REVIEWED")
            try:
                normalized_constraints[row.id] = (
                    _normalize_source_use_constraints(row.constraints_json)
                )
            except SourceAuthorityError:
                reasons.add("SOURCE_USE_CONSTRAINT_PAYLOAD_INVALID")

        decisions = {row.decision for row in matching}
        constraint_hashes = {
            stable_json_hash(value)
            for value in normalized_constraints.values()
        }
        if len(decisions) != 1 or len(constraint_hashes) != 1:
            reasons.add("MATCHING_SOURCE_USE_ASSERTIONS_CONFLICT")
        decision = next(iter(decisions)) if len(decisions) == 1 else "CONFLICT"
        if decision == "CONFLICT":
            reasons.add("SOURCE_DECLARED_CONFLICT")
        elif decision == "UNRESOLVED":
            reasons.add("SOURCE_USE_UNRESOLVED")

        if reasons:
            return _source_use_assessment(
                request=request,
                assessment_state="HOLD",
                reason_codes=reasons,
                constraints=matching,
            )
        if decision == "DECLARED_PROHIBITED":
            return _source_use_assessment(
                request=request,
                assessment_state="DECLARED_PROHIBITED",
                reason_codes={"SOURCE_DECLARED_PROHIBITED"},
                constraints=matching,
            )

        assert decision == "DECLARED_ALLOWED"
        constraints = next(iter(normalized_constraints.values()))
        constraint_reasons = _source_use_constraint_reason_codes(
            constraints,
            request,
        )
        if constraint_reasons:
            return _source_use_assessment(
                request=request,
                assessment_state="HOLD",
                reason_codes=constraint_reasons,
                constraints=matching,
            )
        return _source_use_assessment(
            request=request,
            assessment_state="DECLARED_ALLOWED",
            reason_codes={"EXACT_REVIEWED_SOURCE_DECLARATION_MATCH"},
            constraints=matching,
        )

    async def record_source_extraction(
        self,
        command: ExtractionRecordInput,
    ) -> LabSourceExtractionRecord:
        async with self._transaction():
            source = await self.repository.get_source_document_version(
                command.source_version_id
            )
            if source is None:
                raise SourceAuthorityConflictError(
                    "EXTRACTION_SOURCE_NOT_FOUND",
                    f"Source version not found: {command.source_version_id}.",
                )
            payload = {
                "schema": "lab-source-extraction-v1",
                "source_version_id": command.source_version_id,
                "source_record_sha256": source.record_sha256,
                "locator": command.locator,
                "structure_context": command.structure_context,
                "original_wording": command.original_wording,
                "original_value": command.original_value,
                "parsed_value": command.parsed_value,
                "normalization": command.normalization,
                "parser_or_model_version": command.parser_or_model_version,
                "reviewer_pseudonym": command.reviewer_pseudonym,
                "uncertainty": command.uncertainty,
                "ambiguity": command.ambiguity,
                "output_observation_id": command.output_observation_id,
                "input_sha256": command.input_sha256,
                "output_sha256": command.output_sha256,
            }
            record_hash = stable_json_hash(payload)
            duplicate = await self.repository.extraction_record_by_hash(
                record_hash
            )
            if duplicate is not None:
                raise SourceAuthorityConflictError(
                    "EXTRACTION_RECORD_ALREADY_EXISTS",
                    "An identical immutable extraction record already exists.",
                )
            extraction = await self.repository.add(
                LabSourceExtractionRecord(
                    source_version_id=command.source_version_id,
                    locator_json=dict(command.locator),
                    structure_context_json=dict(command.structure_context),
                    original_wording=command.original_wording,
                    original_value_json=(
                        dict(command.original_value)
                        if command.original_value is not None
                        else None
                    ),
                    parsed_value_json=(
                        dict(command.parsed_value)
                        if command.parsed_value is not None
                        else None
                    ),
                    normalization_json=dict(command.normalization),
                    parser_or_model_version=command.parser_or_model_version,
                    reviewer_pseudonym=command.reviewer_pseudonym,
                    uncertainty_json=dict(command.uncertainty),
                    ambiguity_json=list(command.ambiguity),
                    output_observation_id=command.output_observation_id,
                    input_sha256=command.input_sha256,
                    output_sha256=command.output_sha256,
                    record_sha256=record_hash,
                )
            )
            await self._append_initial_workflow_event(
                subject_type="EXTRACTION_RECORD",
                subject_id=extraction.id,
            )
            return extraction

    async def add_source_derivation(
        self,
        *,
        child_source_version_id: str,
        parent_source_version_id: str,
        relation: str,
        relation_scopes: tuple[Mapping[str, str], ...],
    ) -> LabSourceDerivationLink:
        child_id = _text(
            child_source_version_id,
            "child_source_version_id",
        )
        parent_id = _text(
            parent_source_version_id,
            "parent_source_version_id",
        )
        normalized_relation = _choice(
            relation,
            "relation",
            SOURCE_DERIVATION_RELATIONS,
        )
        normalized_scopes = _normalize_relation_scopes(relation_scopes)
        if child_id == parent_id:
            raise SourceAuthorityConflictError(
                "SOURCE_DERIVATION_SELF_LINK",
                "A source version cannot derive from itself.",
            )
        async with self._transaction():
            child = await self.repository.get_source_document_version(child_id)
            parent = await self.repository.get_source_document_version(parent_id)
            if child is None or parent is None:
                raise SourceAuthorityConflictError(
                    "SOURCE_DERIVATION_SOURCE_NOT_FOUND",
                    "Both derivation source versions must exist.",
                )
            duplicate = await self.repository.get_source_derivation(
                child_id,
                parent_id,
                normalized_relation,
            )
            if duplicate is not None:
                raise SourceAuthorityConflictError(
                    "SOURCE_DERIVATION_DUPLICATE",
                    "The immutable source derivation link already exists.",
                )
            if await self._source_derivation_would_cycle(child_id, parent_id):
                raise SourceAuthorityConflictError(
                    "SOURCE_DERIVATION_CYCLE",
                    "The source derivation link would create a cycle.",
                )
            payload = {
                "schema": "lab-source-derivation-v1",
                "child_source_version_id": child_id,
                "child_record_sha256": child.record_sha256,
                "parent_source_version_id": parent_id,
                "parent_record_sha256": parent.record_sha256,
                "relation": normalized_relation,
                "relation_scopes": normalized_scopes,
            }
            record_hash = stable_json_hash(payload)
            hash_duplicate = await self.repository.derivation_record_by_hash(
                record_hash
            )
            if hash_duplicate is not None:
                raise SourceAuthorityConflictError(
                    "SOURCE_DERIVATION_DUPLICATE",
                    "The immutable source derivation record already exists.",
                )
            return await self.repository.add(
                LabSourceDerivationLink(
                    child_source_version_id=child_id,
                    parent_source_version_id=parent_id,
                    relation=normalized_relation,
                    relation_scopes_json=list(normalized_scopes),
                    record_sha256=record_hash,
                )
            )

    async def _source_derivation_would_cycle(
        self,
        child_source_version_id: str,
        parent_source_version_id: str,
    ) -> bool:
        frontier = [parent_source_version_id]
        visited: set[str] = set()
        while frontier:
            current = frontier.pop()
            if current == child_source_version_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            links = await self.repository.parent_derivation_links(current)
            frontier.extend(link.parent_source_version_id for link in links)
        return False

    async def _append_initial_workflow_event(
        self,
        *,
        subject_type: str,
        subject_id: str,
    ) -> LabEvidenceWorkflowEvent:
        payload = {
            "schema": "lab-evidence-workflow-event-v1",
            "subject_type": subject_type,
            "subject_id": subject_id,
            "sequence_number": 1,
            "from_state": None,
            "to_state": "STAGED",
            "reviewer_pseudonym": None,
            "scope": (),
            "reason": None,
        }
        return await self.repository.add(
            LabEvidenceWorkflowEvent(
                subject_type=subject_type,
                subject_id=subject_id,
                sequence_number=1,
                from_state=None,
                to_state="STAGED",
                reviewer_pseudonym=None,
                scope_json=[],
                reason=None,
                record_sha256=stable_json_hash(payload),
            )
        )

    async def effective_workflow_state(
        self,
        subject_type: str,
        subject_id: str,
    ) -> str | None:
        kind = _choice(
            subject_type,
            "subject_type",
            WORKFLOW_SUBJECT_TYPES,
        )
        identifier = _text(subject_id, "subject_id")
        events = await self.repository.workflow_events(kind, identifier)
        return events[-1].to_state if events else None

    async def transition_evidence_workflow(
        self,
        *,
        subject_type: str,
        subject_id: str,
        to_state: str,
        reviewer_pseudonym: str | None,
        scopes: tuple[str, ...],
        reason: str | None,
    ) -> LabEvidenceWorkflowEvent:
        kind = _choice(
            subject_type,
            "subject_type",
            WORKFLOW_SUBJECT_TYPES,
        )
        identifier = _text(subject_id, "subject_id")
        target = _choice(
            to_state,
            "to_state",
            EVIDENCE_WORKFLOW_STATES,
        )
        reviewer = _optional_text(reviewer_pseudonym)
        normalized_scopes = _tuple_text(scopes, "scopes")
        normalized_reason = _optional_text(reason)
        if target in {
            "HUMAN_REVIEWED",
            "ACCEPTED_FOR_SCOPED_USE",
            "REJECTED",
            "SUPERSEDED",
        } and reviewer is None:
            raise SourceAuthorityError(
                f"reviewer_pseudonym is required for {target}"
            )
        if target == "ACCEPTED_FOR_SCOPED_USE":
            if not normalized_scopes:
                raise SourceAuthorityError(
                    "scopes must not be empty for ACCEPTED_FOR_SCOPED_USE"
                )
        elif normalized_scopes:
            raise SourceAuthorityError(
                "scopes are permitted only for ACCEPTED_FOR_SCOPED_USE"
            )

        async with self._transaction():
            subject = await self._source_workflow_subject(kind, identifier)
            events = await self.repository.workflow_events(kind, identifier)
            if subject is None or not events:
                raise SourceAuthorityConflictError(
                    "WORKFLOW_SUBJECT_NOT_FOUND",
                    f"Workflow subject not found: {kind}/{identifier}.",
                )
            current = events[-1].to_state
            self._validate_workflow_transition(current, target)
            if target == "ACCEPTED_FOR_SCOPED_USE":
                await self._validate_acceptance(kind, subject)
            sequence_number = events[-1].sequence_number + 1
            payload = {
                "schema": "lab-evidence-workflow-event-v1",
                "subject_type": kind,
                "subject_id": identifier,
                "sequence_number": sequence_number,
                "from_state": current,
                "to_state": target,
                "reviewer_pseudonym": reviewer,
                "scope": normalized_scopes,
                "reason": normalized_reason,
            }
            return await self.repository.add(
                LabEvidenceWorkflowEvent(
                    subject_type=kind,
                    subject_id=identifier,
                    sequence_number=sequence_number,
                    from_state=current,
                    to_state=target,
                    reviewer_pseudonym=reviewer,
                    scope_json=list(normalized_scopes),
                    reason=normalized_reason,
                    record_sha256=stable_json_hash(payload),
                )
            )

    async def _source_workflow_subject(
        self,
        subject_type: str,
        subject_id: str,
    ) -> LabSourceDocumentVersion | LabSourceExtractionRecord | None:
        if subject_type == "SOURCE_VERSION":
            return await self.repository.get_source_document_version(subject_id)
        return await self.repository.get_source_extraction(subject_id)

    @staticmethod
    def _validate_workflow_transition(current: str, target: str) -> None:
        if current in {"REJECTED", "SUPERSEDED"}:
            raise SourceAuthorityConflictError(
                "WORKFLOW_TERMINAL",
                f"Workflow state {current} is terminal.",
            )
        if current == "ACCEPTED_FOR_SCOPED_USE":
            if target == "SUPERSEDED":
                return
            raise SourceAuthorityConflictError(
                "WORKFLOW_TERMINAL",
                "Accepted workflow records may only be superseded.",
            )
        if target == "REJECTED":
            return
        current_index = NORMAL_WORKFLOW.index(current)
        expected = NORMAL_WORKFLOW[current_index + 1]
        if target != expected:
            raise SourceAuthorityConflictError(
                "WORKFLOW_TRANSITION_INVALID",
                f"Workflow transition {current} -> {target} is invalid.",
            )

    async def _validate_acceptance(
        self,
        subject_type: str,
        subject: LabSourceDocumentVersion | LabSourceExtractionRecord,
    ) -> None:
        if subject_type == "SOURCE_VERSION":
            source = subject
            assert isinstance(source, LabSourceDocumentVersion)
            complete = bool(
                source.default_locator_json
                and source.artifact_sha256
                and source.independence_group
            )
        else:
            extraction = subject
            assert isinstance(extraction, LabSourceExtractionRecord)
            source_record = await self.repository.get_source_document_version(
                extraction.source_version_id
            )
            complete = bool(
                source_record is not None
                and source_record.artifact_sha256
                and extraction.locator_json
                and (
                    extraction.original_wording is not None
                    or extraction.original_value_json is not None
                )
                and extraction.output_observation_id
                and extraction.input_sha256
                and extraction.output_sha256
            )
        if not complete:
            raise SourceAuthorityConflictError(
                "WORKFLOW_ACCEPTANCE_INCOMPLETE",
                "Workflow acceptance requires complete source, locator, "
                "digest, and observation context.",
            )

    async def is_accepted_for_scoped_use(
        self,
        subject_type: str,
        subject_id: str,
        *,
        required_scope: str,
    ) -> bool:
        kind = _choice(
            subject_type,
            "subject_type",
            WORKFLOW_SUBJECT_TYPES,
        )
        identifier = _text(subject_id, "subject_id")
        scope = _text(required_scope, "required_scope")
        events = await self.repository.workflow_events(kind, identifier)
        if not events:
            return False
        effective = events[-1]
        return (
            effective.to_state == "ACCEPTED_FOR_SCOPED_USE"
            and scope in effective.scope_json
        )

    async def reconstruct_observation_derivation(
        self,
        observation_id: str,
        *,
        required_scope: str,
    ) -> dict[str, Any]:
        observation = _text(observation_id, "observation_id")
        scope = _text(required_scope, "required_scope")
        extractions = await self.repository.observation_extractions(observation)
        if not extractions:
            return {
                "schema": "lab-observation-derivation-v1",
                "observation_id": observation,
                "required_scope": scope,
                "complete": False,
                "sources": [],
                "derivation_links": [],
                "extractions": [],
                "independence_groups": [],
            }

        sources: dict[str, LabSourceDocumentVersion] = {}
        links: dict[str, LabSourceDerivationLink] = {}
        source_graph_complete = True

        async def collect_source(version_id: str) -> None:
            nonlocal source_graph_complete
            if version_id in sources:
                return
            source = await self.repository.get_source_document_version(version_id)
            if source is None:
                source_graph_complete = False
                return
            sources[source.id] = source
            parent_links = await self.repository.parent_derivation_links(source.id)
            for link in parent_links:
                links[link.id] = link
                if not link.relation_scopes_json:
                    source_graph_complete = False
                await collect_source(link.parent_source_version_id)

        extraction_rows: list[dict[str, Any]] = []
        accepted_complete_path = False
        for extraction in extractions:
            await collect_source(extraction.source_version_id)
            events = await self.repository.workflow_events(
                "EXTRACTION_RECORD",
                extraction.id,
            )
            effective = events[-1] if events else None
            accepted_for_scope = bool(
                effective is not None
                and effective.to_state == "ACCEPTED_FOR_SCOPED_USE"
                and scope in effective.scope_json
            )
            source = sources.get(extraction.source_version_id)
            extraction_context_complete = bool(
                source is not None
                and source.artifact_sha256
                and extraction.locator_json
                and (
                    extraction.original_wording is not None
                    or extraction.original_value_json is not None
                )
                and extraction.output_observation_id == observation
                and extraction.input_sha256
                and extraction.output_sha256
            )
            accepted_complete_path = (
                accepted_complete_path
                or accepted_for_scope and extraction_context_complete
            )
            extraction_rows.append(
                {
                    "id": extraction.id,
                    "source_version_id": extraction.source_version_id,
                    "locator": extraction.locator_json,
                    "structure_context": extraction.structure_context_json,
                    "original_wording": extraction.original_wording,
                    "original_value": extraction.original_value_json,
                    "parsed_value": extraction.parsed_value_json,
                    "normalization": extraction.normalization_json,
                    "parser_or_model_version": (
                        extraction.parser_or_model_version
                    ),
                    "reviewer_pseudonym": extraction.reviewer_pseudonym,
                    "uncertainty": extraction.uncertainty_json,
                    "ambiguity": extraction.ambiguity_json,
                    "output_observation_id": (
                        extraction.output_observation_id
                    ),
                    "input_sha256": extraction.input_sha256,
                    "output_sha256": extraction.output_sha256,
                    "record_sha256": extraction.record_sha256,
                    "effective_state": (
                        effective.to_state if effective is not None else None
                    ),
                    "accepted_scopes": (
                        effective.scope_json if effective is not None else []
                    ),
                    "workflow_events": [
                        {
                            "sequence_number": event.sequence_number,
                            "from_state": event.from_state,
                            "to_state": event.to_state,
                            "reviewer_pseudonym": event.reviewer_pseudonym,
                            "scopes": event.scope_json,
                            "reason": event.reason,
                            "record_sha256": event.record_sha256,
                        }
                        for event in events
                    ],
                }
            )

        source_rows = [
            {
                "id": source.id,
                "source_id": source.source_id,
                "version_number": source.version_number,
                "schema_version": source.schema_version,
                "source_type": source.source_type,
                "title": source.title,
                "authors": source.authors_json,
                "issuing_organization": source.issuing_organization,
                "publisher_or_authority": source.publisher_or_authority,
                "identifiers": source.identifiers_json,
                "publication_date": _dated(source.publication_date),
                "revision_date": _dated(source.revision_date),
                "effective_date": _dated(source.effective_date),
                "retrieval_date": _dated(source.retrieval_date),
                "default_locator": source.default_locator_json,
                "artifact_sha256": source.artifact_sha256,
                "rights": source.rights_json,
                "review_state": source.review_state,
                "independence_group": source.independence_group,
                "preserved_artifact_path": source.preserved_artifact_path,
                "parent_record_sha256": source.parent_record_sha256,
                "record_sha256": source.record_sha256,
            }
            for source in sorted(
                sources.values(),
                key=lambda item: (
                    item.source_id,
                    item.version_number,
                    item.id,
                ),
            )
        ]
        link_rows = [
            {
                "id": link.id,
                "child_source_version_id": link.child_source_version_id,
                "parent_source_version_id": link.parent_source_version_id,
                "relation": link.relation,
                "relation_scopes": link.relation_scopes_json,
                "record_sha256": link.record_sha256,
            }
            for link in sorted(
                links.values(),
                key=lambda item: (
                    item.relation,
                    item.parent_source_version_id,
                    item.child_source_version_id,
                    item.id,
                ),
            )
        ]
        extraction_rows.sort(
            key=lambda item: (
                str(item["source_version_id"]),
                str(item["id"]),
            )
        )
        return {
            "schema": "lab-observation-derivation-v1",
            "observation_id": observation,
            "required_scope": scope,
            "complete": bool(
                source_graph_complete and accepted_complete_path
            ),
            "sources": source_rows,
            "derivation_links": link_rows,
            "extractions": extraction_rows,
            "independence_groups": sorted(
                {source.independence_group for source in sources.values()}
            ),
        }


__all__ = [
    "ExtractionRecordInput",
    "LabSourceServiceMixin",
    "SourceAuthorityConflictError",
    "SourceAuthorityError",
    "SourceDocumentInput",
    "SourceUseAssessment",
    "SourceUseConstraintInput",
    "SourceUseRequest",
    "source_derivation_scopes_from_candidate",
    "source_document_registration_from_candidate",
]
