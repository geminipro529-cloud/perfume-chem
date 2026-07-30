from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.lab import LabEvidenceRecord
from app.services.lab_service import LabService
from app.services.lab_sources import (
    ExtractionRecordInput,
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


def _extraction_input(source_version_id: str, **overrides) -> ExtractionRecordInput:
    values = {
        "source_version_id": source_version_id,
        "locator": {"page": 12, "table": "2", "row": "Linalool"},
        "structure_context": {
            "column_heading": "Odor threshold",
            "unit_heading": "microgram/m3",
            "footnotes": ["measured at 25 C in air"],
        },
        "original_wording": "Linalool 7.0 microgram/m3",
        "original_value": {"value": "7.0", "unit": "microgram/m3"},
        "parsed_value": {"value": 7.0},
        "normalization": {"target_unit": "microgram/m3", "factor": 1.0},
        "parser_or_model_version": "manual-parser/1",
        "reviewer_pseudonym": None,
        "uncertainty": {"kind": "not_reported"},
        "ambiguity": (),
        "output_observation_id": "observation-1",
        "input_sha256": "b" * 64,
        "output_sha256": "c" * 64,
    }
    values.update(overrides)
    return ExtractionRecordInput(**values)


@pytest.mark.asyncio
async def test_extraction_preserves_table_context_and_starts_non_authoritative(
    db_session,
):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())

    extraction = await service.record_source_extraction(
        _extraction_input(source.id)
    )

    assert extraction.source_version_id == source.id
    assert extraction.locator_json == {
        "page": 12,
        "table": "2",
        "row": "Linalool",
    }
    assert extraction.structure_context_json == {
        "column_heading": "Odor threshold",
        "unit_heading": "microgram/m3",
        "footnotes": ["measured at 25 C in air"],
    }
    assert extraction.original_value_json == {
        "value": "7.0",
        "unit": "microgram/m3",
    }
    assert extraction.parsed_value_json == {"value": 7.0}
    assert extraction.normalization_json == {
        "target_unit": "microgram/m3",
        "factor": 1.0,
    }
    assert (
        await service.effective_workflow_state(
            "EXTRACTION_RECORD",
            extraction.id,
        )
        == "STAGED"
    )
    assert not await service.is_accepted_for_scoped_use(
        "EXTRACTION_RECORD",
        extraction.id,
        required_scope="threshold_screening",
    )


@pytest.mark.asyncio
async def test_extraction_requires_a_known_source_and_unique_record(db_session):
    service = LabService(db_session)
    with pytest.raises(SourceAuthorityConflictError) as missing:
        await service.record_source_extraction(
            _extraction_input("missing-source")
        )
    assert missing.value.code == "EXTRACTION_SOURCE_NOT_FOUND"

    source = await service.register_source_document(_source_input())
    first = await service.record_source_extraction(
        _extraction_input(source.id)
    )
    assert first.record_sha256
    with pytest.raises(SourceAuthorityConflictError) as duplicate:
        await service.record_source_extraction(
            _extraction_input(source.id)
        )
    assert duplicate.value.code == "EXTRACTION_RECORD_ALREADY_EXISTS"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"source_version_id": ""}, "source_version_id must not be blank"),
        (
            {"original_wording": None, "original_value": None},
            "original wording or original value",
        ),
        (
            {"parser_or_model_version": ""},
            "parser_or_model_version must not be blank",
        ),
        ({"input_sha256": "bad"}, "64-character hexadecimal"),
        ({"output_sha256": "bad"}, "64-character hexadecimal"),
    ],
)
def test_extraction_input_rejects_detached_or_invalid_data(overrides, message):
    values = dict(overrides)
    source_version_id = values.pop("source_version_id", "source-version")
    with pytest.raises(SourceAuthorityError, match=message):
        _extraction_input(source_version_id, **values)


async def _advance_to_human_review(
    service: LabService,
    extraction_id: str,
) -> None:
    transitions = (
        ("PARSED", None),
        ("IDENTITY_RESOLVED", None),
        ("UNIT_NORMALIZED", None),
        ("CONDITION_NORMALIZED", None),
        ("CONFLICT_CHECKED", None),
        ("HUMAN_REVIEWED", "reviewer-1"),
    )
    for state, reviewer in transitions:
        await service.transition_evidence_workflow(
            subject_type="EXTRACTION_RECORD",
            subject_id=extraction_id,
            to_state=state,
            reviewer_pseudonym=reviewer,
            scopes=(),
            reason=f"advance to {state}",
        )


@pytest.mark.asyncio
async def test_workflow_requires_ordered_human_review_and_exact_scope(db_session):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())
    extraction = await service.record_source_extraction(
        _extraction_input(source.id)
    )

    for state in (
        "STAGED",
        "PARSED",
        "IDENTITY_RESOLVED",
        "UNIT_NORMALIZED",
        "CONDITION_NORMALIZED",
        "CONFLICT_CHECKED",
        "HUMAN_REVIEWED",
    ):
        if state != "STAGED":
            reviewer = "reviewer-1" if state == "HUMAN_REVIEWED" else None
            await service.transition_evidence_workflow(
                subject_type="EXTRACTION_RECORD",
                subject_id=extraction.id,
                to_state=state,
                reviewer_pseudonym=reviewer,
                scopes=(),
                reason=f"advance to {state}",
            )
        assert not await service.is_accepted_for_scoped_use(
            "EXTRACTION_RECORD",
            extraction.id,
            required_scope="threshold_screening",
        )

    accepted = await service.transition_evidence_workflow(
        subject_type="EXTRACTION_RECORD",
        subject_id=extraction.id,
        to_state="ACCEPTED_FOR_SCOPED_USE",
        reviewer_pseudonym="reviewer-1",
        scopes=("threshold_screening",),
        reason="accepted for threshold screening only",
    )

    assert accepted.sequence_number == 8
    assert await service.is_accepted_for_scoped_use(
        "EXTRACTION_RECORD",
        extraction.id,
        required_scope="threshold_screening",
    )
    assert not await service.is_accepted_for_scoped_use(
        "EXTRACTION_RECORD",
        extraction.id,
        required_scope="release",
    )


@pytest.mark.asyncio
async def test_workflow_rejects_skips_and_terminal_transitions(db_session):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())
    extraction = await service.record_source_extraction(
        _extraction_input(source.id)
    )
    extraction_id = extraction.id

    with pytest.raises(SourceAuthorityConflictError) as skipped:
        await service.transition_evidence_workflow(
            subject_type="EXTRACTION_RECORD",
            subject_id=extraction_id,
            to_state="IDENTITY_RESOLVED",
            reviewer_pseudonym=None,
            scopes=(),
            reason="invalid skip",
        )
    assert skipped.value.code == "WORKFLOW_TRANSITION_INVALID"

    await service.transition_evidence_workflow(
        subject_type="EXTRACTION_RECORD",
        subject_id=extraction_id,
        to_state="REJECTED",
        reviewer_pseudonym="reviewer-1",
        scopes=(),
        reason="source conditions do not apply",
    )
    with pytest.raises(SourceAuthorityConflictError) as terminal:
        await service.transition_evidence_workflow(
            subject_type="EXTRACTION_RECORD",
            subject_id=extraction_id,
            to_state="PARSED",
            reviewer_pseudonym=None,
            scopes=(),
            reason="cannot revive",
        )
    assert terminal.value.code == "WORKFLOW_TERMINAL"


@pytest.mark.asyncio
async def test_workflow_acceptance_fails_closed_without_required_context(db_session):
    service = LabService(db_session)
    source = await service.register_source_document(_source_input())
    extraction = await service.record_source_extraction(
        _extraction_input(
            source.id,
            locator={},
            output_observation_id=None,
        )
    )
    await _advance_to_human_review(service, extraction.id)

    with pytest.raises(SourceAuthorityConflictError) as incomplete:
        await service.transition_evidence_workflow(
            subject_type="EXTRACTION_RECORD",
            subject_id=extraction.id,
            to_state="ACCEPTED_FOR_SCOPED_USE",
            reviewer_pseudonym="reviewer-1",
            scopes=("threshold_screening",),
            reason="must fail",
        )
    assert incomplete.value.code == "WORKFLOW_ACCEPTANCE_INCOMPLETE"


@pytest.mark.asyncio
async def test_ai_generated_source_and_extraction_are_not_auto_authoritative(
    db_session,
):
    service = LabService(db_session)
    source = await service.register_source_document(
        _source_input(
            source_type="AI_GENERATED_HYPOTHESIS",
            title="Bounded machine-generated hypothesis",
            authors=(),
            issuing_organization="local-model",
            artifact_sha256="d" * 64,
            independence_group="ai-hypothesis-1",
        )
    )
    extraction = await service.record_source_extraction(
        _extraction_input(source.id, parser_or_model_version="model/1")
    )

    assert not await service.is_accepted_for_scoped_use(
        "SOURCE_VERSION",
        source.id,
        required_scope="threshold_screening",
    )
    assert not await service.is_accepted_for_scoped_use(
        "EXTRACTION_RECORD",
        extraction.id,
        required_scope="threshold_screening",
    )
