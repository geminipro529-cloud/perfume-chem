"""Validated commands for canonical B1 source and provenance records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from engine.calibration.hashing import stable_json_hash

from app.models.lab_sources import (
    EVIDENCE_WORKFLOW_STATES,
    SOURCE_DERIVATION_RELATIONS,
    SOURCE_REVIEW_STATES,
    SOURCE_TYPES,
    WORKFLOW_SUBJECT_TYPES,
    LabEvidenceWorkflowEvent,
    LabSourceDerivationLink,
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
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
]
