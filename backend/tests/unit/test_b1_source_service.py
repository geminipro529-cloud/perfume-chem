from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.lab import LabEvidenceRecord
from app.services.lab_service import LabService
from app.services.lab_sources import (
    SourceAuthorityConflictError,
    SourceAuthorityError,
    SourceDocumentInput,
)


def _source_input(**overrides) -> SourceDocumentInput:
    values = {
        "schema_version": "lab-source-document-v1",
        "source_type": "PRIMARY_PEER_REVIEWED_PAPER",
        "title": "Measured odor thresholds under controlled conditions",
        "artifact_sha256": "a" * 64,
        "language": "en",
        "review_state": "UNREVIEWED",
        "independence_group": "primary-doi-10.1000-example",
        "authors": ("A. Researcher", "B. Chemist"),
        "issuing_organization": None,
        "container_title": "Journal of Test Evidence",
        "publisher_or_authority": "Evidence Society",
        "identifiers": {"doi": "10.1000/example"},
        "publication_date": date(2024, 2, 3),
        "revision_date": None,
        "effective_date": None,
        "retrieval_date": date(2026, 7, 30),
        "edition_or_amendment": "Version of record",
        "default_locator": {"page": 12, "table": "2"},
        "license_or_reuse_restriction": "metadata-only",
        "original_unit": "microgram/m3",
        "original_terminology": "odor threshold",
        "reviewer_pseudonym": None,
        "preserved_artifact_path": "evidence/papers/example-metadata.json",
    }
    values.update(overrides)
    return SourceDocumentInput(**values)


@pytest.mark.asyncio
async def test_source_document_versions_are_immutable_hash_chained_and_staged(
    db_session,
):
    service = LabService(db_session)
    first = await service.register_source_document(_source_input())
    second = await service.register_source_document(
        replace(
            _source_input(),
            title="Measured odor thresholds — corrected metadata",
            revision_date=date(2025, 1, 2),
            artifact_sha256="b" * 64,
        ),
        parent_version_id=first.id,
    )

    assert first.source_id == second.source_id
    assert (first.version_number, second.version_number) == (1, 2)
    assert second.supersedes_version_id == first.id
    assert second.parent_record_sha256 == first.record_sha256
    assert second.record_sha256 != first.record_sha256
    assert (
        await service.effective_workflow_state("SOURCE_VERSION", first.id)
        == "STAGED"
    )
    assert (
        await service.effective_workflow_state("SOURCE_VERSION", second.id)
        == "STAGED"
    )
    legacy_count = await db_session.scalar(
        select(func.count()).select_from(LabEvidenceRecord)
    )
    assert legacy_count == 0


@pytest.mark.asyncio
async def test_source_revision_requires_the_latest_parent(db_session):
    service = LabService(db_session)
    first = await service.register_source_document(_source_input())
    await service.register_source_document(
        replace(_source_input(), title="Second version", artifact_sha256="b" * 64),
        parent_version_id=first.id,
    )

    with pytest.raises(SourceAuthorityConflictError) as error:
        await service.register_source_document(
            replace(_source_input(), title="Stale branch", artifact_sha256="c" * 64),
            parent_version_id=first.id,
        )

    assert error.value.code == "SOURCE_PARENT_NOT_LATEST"


@pytest.mark.asyncio
async def test_source_registration_rejects_missing_parent_and_duplicate_identity(
    db_session,
):
    service = LabService(db_session)
    with pytest.raises(SourceAuthorityConflictError) as missing:
        await service.register_source_document(
            _source_input(),
            parent_version_id="missing-source-version",
        )
    assert missing.value.code == "SOURCE_PARENT_NOT_FOUND"

    first = await service.register_source_document(_source_input())
    with pytest.raises(SourceAuthorityConflictError) as duplicate:
        await service.register_source_document(
            _source_input(),
            source_id=first.source_id,
        )
    assert duplicate.value.code == "SOURCE_ID_ALREADY_EXISTS"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"title": "   "}, "title must not be blank"),
        ({"source_type": "BLOG"}, "source_type must be one of"),
        ({"artifact_sha256": "not-a-digest"}, "64-character hexadecimal"),
        ({"independence_group": ""}, "independence_group must not be blank"),
        (
            {"authors": (), "issuing_organization": None},
            "authors or issuing_organization",
        ),
        (
            {"preserved_artifact_path": "C:\\secrets\\source.pdf"},
            "repository-relative",
        ),
        (
            {"preserved_artifact_path": "../outside/source.pdf"},
            "repository-relative",
        ),
        (
            {"preserved_artifact_path": "evidence/.env"},
            "sensitive path",
        ),
    ],
)
def test_source_document_input_rejects_invalid_or_sensitive_metadata(
    overrides,
    message,
):
    with pytest.raises(SourceAuthorityError, match=message):
        _source_input(**overrides)
