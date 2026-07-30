"""Validated commands for canonical B1 source and provenance records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from engine.calibration.hashing import stable_json_hash

from app.models.lab_sources import (
    SOURCE_REVIEW_STATES,
    SOURCE_TYPES,
    WORKFLOW_SUBJECT_TYPES,
    LabEvidenceWorkflowEvent,
    LabSourceDocumentVersion,
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
        object.__setattr__(
            self,
            "license_or_reuse_restriction",
            _optional_text(self.license_or_reuse_restriction),
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


def _source_payload(
    *,
    source_id: str,
    version_number: int,
    parent_record_sha256: str | None,
    command: SourceDocumentInput,
) -> dict[str, Any]:
    return {
        "schema": "lab-source-document-v1",
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
        "language": command.language,
        "original_unit": command.original_unit,
        "original_terminology": command.original_terminology,
        "reviewer_pseudonym": command.reviewer_pseudonym,
        "review_state": command.review_state,
        "independence_group": command.independence_group,
        "preserved_artifact_path": command.preserved_artifact_path,
        "parent_record_sha256": parent_record_sha256,
    }


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


__all__ = [
    "LabSourceServiceMixin",
    "SourceAuthorityConflictError",
    "SourceAuthorityError",
    "SourceDocumentInput",
]
