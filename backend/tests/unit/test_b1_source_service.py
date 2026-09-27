from dataclasses import replace
from datetime import date

import pytest
from engine.calibration.hashing import stable_json_hash
from sqlalchemy import func, select

from app.models.lab import LabEvidenceRecord
from app.schemas.lab_reporting import ScienceView
from app.services.lab_reporting import REPORT_COLLECTION_KEYS, build_science_report
from app.services.lab_service import LabService
from app.services.lab_sources import (
    ExtractionRecordInput,
    SourceAuthorityConflictError,
    SourceAuthorityError,
    SourceDocumentInput,
    SourceUseConstraintInput,
    SourceUseRequest,
    _source_payload,
    source_derivation_scopes_from_candidate,
    source_document_registration_from_candidate,
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
        "rights": {
            "reuse_status": "RESTRICTED",
            "license_or_reuse_restriction": "metadata-only",
            "license_url": "https://example.org/rights",
            "redistribution_allowed": False,
            "spdx_identifier": None,
            "notes": "Metadata may be retained; source bytes are restricted.",
        },
        "original_unit": "microgram/m3",
        "original_terminology": "odor threshold",
        "reviewer_pseudonym": None,
        "preserved_artifact_path": "evidence/papers/example-metadata.json",
    }
    values.update(overrides)
    return SourceDocumentInput(**values)


def _relation_scopes(
    claim_path: str = "observations.threshold",
) -> tuple[dict[str, str], ...]:
    return (
        {
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": claim_path,
            "rationale": "The parent documents the declared method context.",
        },
    )


def _source_use_constraint(
    subject_source_version_id: str,
    terms_source_version_id: str,
    **overrides,
) -> SourceUseConstraintInput:
    values = {
        "subject_source_version_id": subject_source_version_id,
        "terms_source_version_id": terms_source_version_id,
        "artifact_scope": "DATASET",
        "artifact_locator": {
            "artifact_id": "example-dataset-v2",
            "sha256": "d" * 64,
        },
        "channel": "official-data-repository",
        "intended_action": "INTERNAL_ANALYSIS",
        "purpose_context": "external-study-method-development",
        "decision": "DECLARED_ALLOWED",
        "constraints": {
            "attribution_required": True,
            "max_records": 6660,
        },
        "terms_effective_date": date(2021, 5, 5),
        "terms_retrieval_date": date(2026, 8, 10),
        "reviewer_pseudonym": "rights-reviewer",
        "review_state": "REVIEWED",
        "legal_review_required": False,
    }
    values.update(overrides)
    return SourceUseConstraintInput(**values)


def _source_use_request(
    subject_source_version_id: str,
    **overrides,
) -> SourceUseRequest:
    values = {
        "subject_source_version_id": subject_source_version_id,
        "artifact_scope": "DATASET",
        "artifact_locator": {
            "artifact_id": "example-dataset-v2",
            "sha256": "d" * 64,
        },
        "channel": "official-data-repository",
        "intended_action": "INTERNAL_ANALYSIS",
        "purpose_context": "external-study-method-development",
        "as_of_date": date(2026, 8, 10),
        "requested_records": 6660,
        "attribution_planned": True,
    }
    values.update(overrides)
    return SourceUseRequest(**values)


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
    assert first.rights_json == _source_input().rights
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
async def test_b1_candidate_rights_round_trip_and_tamper_detection(db_session):
    payload = {
        "candidate_schema_version": "b1_source_document_candidate_v1",
        "schema_version": "scientific-source-manifest-v1",
        "source_id": "keller-study-data:study-data-xlsx",
        "source_type": "PRIMARY_RESEARCH_DATASET",
        "title": "Keller and Vosshall study data",
        "artifact_sha256": "9" * 64,
        "language": "en",
        "review_state": "UNREVIEWED",
        "independence_group": "keller-vosshall-2016",
        "authors": ["Andreas Keller", "Leslie B. Vosshall"],
        "issuing_organization": None,
        "container_title": None,
        "publisher_or_authority": "BMC Neuroscience",
        "identifiers": {"doi": "10.1186/s12868-016-0287-2"},
        "publication_date": "2016-08-05",
        "revision_date": None,
        "effective_date": None,
        "retrieval_date": "2026-08-10",
        "edition_or_amendment": None,
        "default_locator": {"artifact_id": "study-data-xlsx"},
        "license_or_reuse_restriction": "CC0 1.0",
        "rights": {
            "reuse_status": "PERMITTED",
            "license_or_reuse_restriction": "CC0 1.0",
            "license_url": (
                "https://creativecommons.org/publicdomain/zero/1.0/"
            ),
            "redistribution_allowed": True,
            "spdx_identifier": "CC0-1.0",
            "notes": "Data scope only; article scope remains separate.",
        },
        "preserved_artifact_path": "data/external/keller/study.xlsx",
        "workflow_state": "STAGED",
        "authority_state": "CANDIDATE_ONLY",
    }
    candidate = {**payload, "candidate_sha256": stable_json_hash(payload)}
    source_id, command = source_document_registration_from_candidate(candidate)
    service = LabService(db_session)
    source = await service.register_source_document(
        command,
        source_id=source_id,
    )

    assert len(source_id) == 36
    assert source.identifiers_json["staged_source_id"] == payload["source_id"]
    assert source.rights_json == payload["rights"]
    assert source.license_or_reuse_restriction == "CC0 1.0"

    tampered = {
        **candidate,
        "rights": {**candidate["rights"], "redistribution_allowed": False},
    }
    with pytest.raises(SourceAuthorityError, match="candidate hash mismatch"):
        source_document_registration_from_candidate(tampered)

    expected_record_payload = _source_payload(
        source_id=source_id,
        version_number=1,
        parent_record_sha256=None,
        command=command,
    )
    assert source.record_sha256 == stable_json_hash(expected_record_payload)
    rights_changed_command = replace(
        command,
        rights={**command.rights, "redistribution_allowed": False},
    )
    assert stable_json_hash(
        _source_payload(
            source_id=source_id,
            version_number=1,
            parent_record_sha256=None,
            command=rights_changed_command,
        )
    ) != source.record_sha256

    article_rights = {
        "reuse_status": "PERMITTED",
        "license_or_reuse_restriction": "CC BY 4.0 article text only",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "redistribution_allowed": True,
        "spdx_identifier": "CC-BY-4.0",
        "notes": "Article scope only; this does not license the study data.",
    }
    article_payload = {
        **payload,
        "source_id": "keller-study-article:fulltext-xml",
        "source_type": "PRIMARY_PEER_REVIEWED_PAPER",
        "title": "Keller and Vosshall article text",
        "artifact_sha256": "8" * 64,
        "license_or_reuse_restriction": article_rights[
            "license_or_reuse_restriction"
        ],
        "rights": article_rights,
        "default_locator": {"artifact_id": "fulltext-xml"},
        "preserved_artifact_path": "data/external/keller/article.xml",
    }
    article_candidate = {
        **article_payload,
        "candidate_sha256": stable_json_hash(article_payload),
    }
    article_id, article_command = source_document_registration_from_candidate(
        article_candidate
    )
    article = await service.register_source_document(
        article_command,
        source_id=article_id,
    )

    pubchem_rights = {
        "reuse_status": "RESTRICTED",
        "license_or_reuse_restriction": (
            "Field-scoped rights caution; no blanket permissive claim."
        ),
        "license_url": "https://pubchem.ncbi.nlm.nih.gov/docs/downloads",
        "redistribution_allowed": False,
        "spdx_identifier": None,
        "notes": "Identity review only; contributor provenance must be rechecked.",
    }
    pubchem_payload = {
        **payload,
        "source_id": "pubchem-geraniol:properties-json",
        "source_type": "AUTHORITATIVE_DATABASE_RECORD",
        "title": "PubChem Geraniol properties response",
        "artifact_sha256": "7" * 64,
        "authors": [],
        "issuing_organization": "National Center for Biotechnology Information",
        "container_title": "PubChem PUG REST",
        "publisher_or_authority": "PubChem",
        "identifiers": {"pubchem_cid": "637566"},
        "license_or_reuse_restriction": pubchem_rights[
            "license_or_reuse_restriction"
        ],
        "rights": pubchem_rights,
        "default_locator": {"artifact_id": "geraniol-properties-json"},
        "preserved_artifact_path": "data/external/pubchem/geraniol.json",
    }
    pubchem_candidate = {
        **pubchem_payload,
        "candidate_sha256": stable_json_hash(pubchem_payload),
    }
    pubchem_id, pubchem_command = source_document_registration_from_candidate(
        pubchem_candidate
    )
    pubchem = await service.register_source_document(
        pubchem_command,
        source_id=pubchem_id,
    )

    snapshot = {key: () for key in REPORT_COLLECTION_KEYS}
    snapshot["source_documents"] = (source, article, pubchem)
    report = build_science_report(snapshot, ScienceView.EXPLORATORY)
    source_section = next(
        section for section in report.sections if section.key == "source_documents"
    )
    rights_by_title = {
        str(record.facts["title"]): record.provenance["rights"]
        for record in source_section.included
    }
    evidence_by_title = {
        str(record.facts["title"]): record.evidence_class
        for record in source_section.included
    }
    assert rights_by_title == {
        payload["title"]: payload["rights"],
        article_payload["title"]: article_rights,
        pubchem_payload["title"]: pubchem_rights,
    }
    assert rights_by_title[article_payload["title"]]["spdx_identifier"] == (
        "CC-BY-4.0"
    )
    assert rights_by_title[payload["title"]]["spdx_identifier"] == "CC0-1.0"
    assert rights_by_title[pubchem_payload["title"]][
        "redistribution_allowed"
    ] is False
    assert evidence_by_title[payload["title"]] == "LITERATURE_DERIVED"


def test_derivation_candidate_scope_is_hash_bound() -> None:
    payload = {
        "candidate_schema_version": "b1_source_derivation_candidate_v1",
        "child_source_id": "child",
        "child_source_candidate_sha256": "1" * 64,
        "child_artifact_sha256": "2" * 64,
        "child_manifest_sha256": "3" * 64,
        "parent_source_id": "parent",
        "parent_source_candidate_sha256": "4" * 64,
        "parent_artifact_sha256": "5" * 64,
        "parent_manifest_sha256": "6" * 64,
        "parent_bundle_sha256": "7" * 64,
        "relation": "CITES",
        "support_scope": "EXPERIMENTAL_METHOD",
        "supported_claim_path": "observation_tranche.method_context",
        "rationale": "Documents the psychophysics method.",
        "review_state": "UNREVIEWED",
        "workflow_state": "STAGED",
        "authority_state": "CANDIDATE_ONLY",
    }
    candidate = {**payload, "record_sha256": stable_json_hash(payload)}
    assert source_derivation_scopes_from_candidate(candidate) == (
        {
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "Documents the psychophysics method.",
        },
    )
    with pytest.raises(SourceAuthorityError, match="candidate hash mismatch"):
        source_derivation_scopes_from_candidate(
            {**candidate, "rationale": "Different claim."}
        )


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


@pytest.mark.asyncio
async def test_source_use_is_exact_scoped_hash_chained_and_nonleaking(
    db_session,
):
    service = LabService(db_session)
    dataset = await service.register_source_document(
        _source_input(
            source_type="PRIMARY_RESEARCH_DATASET",
            title="Example study dataset",
            artifact_sha256="1" * 64,
            review_state="REVIEWED",
            independence_group="example-study-data",
        )
    )
    article = await service.register_source_document(
        _source_input(
            title="Example study article",
            artifact_sha256="2" * 64,
            review_state="REVIEWED",
            independence_group="example-study-article",
        )
    )
    terms = await service.register_source_document(
        _source_input(
            source_type="REGULATION_OR_OFFICIAL_GUIDANCE",
            title="Example dataset terms version",
            artifact_sha256="3" * 64,
            review_state="REVIEWED",
            independence_group="example-data-terms",
        )
    )

    first = await service.register_source_use_constraint(
        _source_use_constraint(dataset.id, terms.id)
    )
    allowed = await service.assess_source_use(_source_use_request(dataset.id))

    assert first.version_number == 1
    assert first.parent_record_sha256 is None
    assert first.constraints_json["attribution_required"] is True
    assert allowed.assessment_state == "DECLARED_ALLOWED"
    assert allowed.authority_state == (
        "SOURCE_DECLARATION_ONLY_NOT_LEGAL_CONCLUSION"
    )
    assert allowed.reason_codes == (
        "EXACT_REVIEWED_SOURCE_DECLARATION_MATCH",
    )
    assert allowed.constraint_version_ids == (first.id,)
    assert len(allowed.request_sha256) == 64
    assert len(allowed.assessment_sha256) == 64

    wrong_channel = await service.assess_source_use(
        _source_use_request(dataset.id, channel="repository-mirror")
    )
    article_nonleak = await service.assess_source_use(
        _source_use_request(article.id)
    )
    external_transmission = await service.assess_source_use(
        _source_use_request(
            dataset.id,
            intended_action="EXTERNAL_TRANSMISSION",
        )
    )
    assert wrong_channel.reason_codes == ("NO_EXACT_SOURCE_USE_ASSERTION",)
    assert article_nonleak.reason_codes == ("NO_EXACT_SOURCE_USE_ASSERTION",)
    assert external_transmission.reason_codes == (
        "NO_EXACT_SOURCE_USE_ASSERTION",
    )

    second = await service.register_source_use_constraint(
        replace(
            _source_use_constraint(dataset.id, terms.id),
            decision="DECLARED_PROHIBITED",
        ),
        parent_version_id=first.id,
    )
    prohibited = await service.assess_source_use(_source_use_request(dataset.id))
    assert second.constraint_id == first.constraint_id
    assert second.version_number == 2
    assert second.supersedes_version_id == first.id
    assert second.parent_record_sha256 == first.record_sha256
    assert second.record_sha256 != first.record_sha256
    assert prohibited.assessment_state == "DECLARED_PROHIBITED"
    assert prohibited.constraint_version_ids == (second.id,)
    assert prohibited.reason_codes == ("SOURCE_DECLARED_PROHIBITED",)

    with pytest.raises(SourceAuthorityConflictError) as changed_scope:
        await service.register_source_use_constraint(
            replace(
                _source_use_constraint(dataset.id, terms.id),
                purpose_context="model-training",
            ),
            parent_version_id=second.id,
        )
    assert changed_scope.value.code == "SOURCE_USE_SCOPE_REVISION_FORBIDDEN"


@pytest.mark.asyncio
async def test_source_use_constraints_fail_closed_on_missing_context_and_conflict(
    db_session,
):
    service = LabService(db_session)
    source = await service.register_source_document(
        _source_input(
            source_type="AUTHORITATIVE_DATABASE_RECORD",
            title="Example API response",
            artifact_sha256="4" * 64,
            review_state="REVIEWED",
            independence_group="example-api-response",
        )
    )
    terms = await service.register_source_document(
        _source_input(
            source_type="REGULATION_OR_OFFICIAL_GUIDANCE",
            title="Example API terms",
            artifact_sha256="5" * 64,
            review_state="REVIEWED",
            independence_group="example-api-terms",
        )
    )
    constraints = {
        "plan_or_tier": "research-plan",
        "jurisdiction": "TH",
        "max_records": 100,
        "max_bytes": 1000,
        "retention_days": 7,
        "freshness_required": True,
        "attribution_required": True,
        "share_alike_required": True,
        "noncommercial_only": True,
        "no_sublicense": True,
        "no_competing_service": True,
        "deletion_or_tombstone_required": True,
        "rate_limit_max_requests": 10,
        "rate_limit_period_seconds": 60,
    }
    row = await service.register_source_use_constraint(
        _source_use_constraint(
            source.id,
            terms.id,
            artifact_scope="API_RESPONSE",
            artifact_locator={"endpoint": "/v1/example", "response": "r1"},
            channel="approved-oauth-api",
            intended_action="LOCAL_CACHE",
            purpose_context="bounded-api-evaluation",
            constraints=constraints,
        )
    )
    incomplete = await service.assess_source_use(
        _source_use_request(
            source.id,
            artifact_scope="API_RESPONSE",
            artifact_locator={"endpoint": "/v1/example", "response": "r1"},
            channel="approved-oauth-api",
            intended_action="LOCAL_CACHE",
            purpose_context="bounded-api-evaluation",
            requested_records=None,
            attribution_planned=None,
        )
    )
    assert incomplete.assessment_state == "HOLD"
    assert {
        "PLAN_OR_TIER_MISMATCH",
        "JURISDICTION_MISMATCH",
        "REQUESTED_RECORDS_REQUIRED",
        "REQUESTED_BYTES_REQUIRED",
        "RETENTION_DAYS_REQUIRED",
        "FRESH_FETCH_REQUIRED",
        "ATTRIBUTION_PLAN_REQUIRED",
        "SHARE_ALIKE_PLAN_REQUIRED",
        "COMMERCIAL_CONTEXT_REQUIRED",
        "SUBLICENSE_CONTEXT_REQUIRED",
        "COMPETING_SERVICE_CONTEXT_REQUIRED",
        "DELETION_OR_TOMBSTONE_SUPPORT_REQUIRED",
        "RATE_LIMIT_COMPLIANCE_REQUIRED",
    } <= set(incomplete.reason_codes)

    exact = await service.assess_source_use(
        _source_use_request(
            source.id,
            artifact_scope="API_RESPONSE",
            artifact_locator={"endpoint": "/v1/example", "response": "r1"},
            channel="approved-oauth-api",
            intended_action="LOCAL_CACHE",
            purpose_context="bounded-api-evaluation",
            plan_or_tier="research-plan",
            jurisdiction="TH",
            requested_records=100,
            requested_bytes=1000,
            retention_days=7,
            fresh_fetch=True,
            attribution_planned=True,
            share_alike_planned=True,
            commercial_use=False,
            sublicense=False,
            competing_service=False,
            deletion_or_tombstone_supported=True,
            rate_limit_compliance_confirmed=True,
        )
    )
    assert exact.assessment_state == "DECLARED_ALLOWED"
    assert exact.constraint_version_ids == (row.id,)

    await service.register_source_use_constraint(
        _source_use_constraint(
            source.id,
            terms.id,
            artifact_scope="API_RESPONSE",
            artifact_locator={"endpoint": "/v1/example", "response": "r1"},
            channel="approved-oauth-api",
            intended_action="LOCAL_CACHE",
            purpose_context="bounded-api-evaluation",
            decision="DECLARED_PROHIBITED",
            constraints=constraints,
        )
    )
    conflict = await service.assess_source_use(
        _source_use_request(
            source.id,
            artifact_scope="API_RESPONSE",
            artifact_locator={"endpoint": "/v1/example", "response": "r1"},
            channel="approved-oauth-api",
            intended_action="LOCAL_CACHE",
            purpose_context="bounded-api-evaluation",
        )
    )
    assert conflict.assessment_state == "HOLD"
    assert "MATCHING_SOURCE_USE_ASSERTIONS_CONFLICT" in conflict.reason_codes


@pytest.mark.asyncio
async def test_source_use_holds_legal_unmodeled_and_unresolved_assertions(
    db_session,
):
    service = LabService(db_session)
    source = await service.register_source_document(
        _source_input(
            source_type="AUTHORITATIVE_DATABASE_RECORD",
            title="Example software release",
            artifact_sha256="6" * 64,
            review_state="REVIEWED",
            independence_group="example-software",
        )
    )
    terms = await service.register_source_document(
        _source_input(
            source_type="REGULATION_OR_OFFICIAL_GUIDANCE",
            title="Example software terms",
            artifact_sha256="7" * 64,
            review_state="REVIEWED",
            independence_group="example-software-terms",
        )
    )
    await service.register_source_use_constraint(
        _source_use_constraint(
            source.id,
            terms.id,
            artifact_scope="SOFTWARE",
            artifact_locator={"release": "v1"},
            intended_action="ARCHIVE_SOURCE_BYTES",
            purpose_context="reproducibility-archive",
            legal_review_required=True,
            constraints={},
        )
    )
    legal_hold = await service.assess_source_use(
        _source_use_request(
            source.id,
            artifact_scope="SOFTWARE",
            artifact_locator={"release": "v1"},
            intended_action="ARCHIVE_SOURCE_BYTES",
            purpose_context="reproducibility-archive",
        )
    )
    assert legal_hold.assessment_state == "HOLD"
    assert "LEGAL_REVIEW_REQUIRED" in legal_hold.reason_codes

    await service.register_source_use_constraint(
        _source_use_constraint(
            source.id,
            terms.id,
            artifact_scope="SOFTWARE",
            artifact_locator={"release": "v1"},
            intended_action="ML_TRAIN_OR_EVALUATE",
            purpose_context="benchmark-only",
            constraints={"unmodeled_constraints": ["author approval required"]},
        )
    )
    unmodeled = await service.assess_source_use(
        _source_use_request(
            source.id,
            artifact_scope="SOFTWARE",
            artifact_locator={"release": "v1"},
            intended_action="ML_TRAIN_OR_EVALUATE",
            purpose_context="benchmark-only",
        )
    )
    assert unmodeled.assessment_state == "HOLD"
    assert unmodeled.reason_codes == ("UNMODELED_SOURCE_USE_CONSTRAINT",)

    await service.register_source_use_constraint(
        _source_use_constraint(
            source.id,
            terms.id,
            artifact_scope="SOFTWARE",
            artifact_locator={"release": "v1"},
            intended_action="COMMERCIAL_RUNTIME",
            purpose_context="runtime-evaluation",
            decision="UNRESOLVED",
            constraints={},
        )
    )
    unresolved = await service.assess_source_use(
        _source_use_request(
            source.id,
            artifact_scope="SOFTWARE",
            artifact_locator={"release": "v1"},
            intended_action="COMMERCIAL_RUNTIME",
            purpose_context="runtime-evaluation",
        )
    )
    assert unresolved.assessment_state == "HOLD"
    assert unresolved.reason_codes == ("SOURCE_USE_UNRESOLVED",)


def test_source_use_input_rejects_unbounded_or_unreviewed_claims() -> None:
    with pytest.raises(SourceAuthorityError, match="artifact_locator"):
        _source_use_constraint("source", "terms", artifact_locator={})
    with pytest.raises(SourceAuthorityError, match="reviewer_pseudonym"):
        _source_use_constraint(
            "source",
            "terms",
            reviewer_pseudonym=None,
        )
    with pytest.raises(SourceAuthorityError, match="unsupported fields"):
        _source_use_constraint(
            "source",
            "terms",
            constraints={"blanket_integration_allowed": True},
        )
    with pytest.raises(SourceAuthorityError, match="supplied together"):
        _source_use_constraint(
            "source",
            "terms",
            constraints={"rate_limit_max_requests": 5},
        )
    with pytest.raises(SourceAuthorityError, match="credentials"):
        _source_use_constraint(
            "source",
            "terms",
            artifact_locator={"api_key": "do-not-store"},
        )
    with pytest.raises(SourceAuthorityError, match="list of strings"):
        _source_use_constraint(
            "source",
            "terms",
            constraints={"unmodeled_constraints": "author approval"},
        )
    with pytest.raises(SourceAuthorityError, match="must be a boolean"):
        _source_use_constraint(
            "source",
            "terms",
            constraints={"attribution_required": None},
        )


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


async def _accept_extraction(
    service: LabService,
    extraction_id: str,
    *,
    scope: str = "threshold_screening",
) -> None:
    await _advance_to_human_review(service, extraction_id)
    await service.transition_evidence_workflow(
        subject_type="EXTRACTION_RECORD",
        subject_id=extraction_id,
        to_state="ACCEPTED_FOR_SCOPED_USE",
        reviewer_pseudonym="reviewer-1",
        scopes=(scope,),
        reason=f"accepted for {scope}",
    )


@pytest.mark.asyncio
async def test_reconstruction_collapses_repeated_sources_to_one_independence_group(
    db_session,
):
    service = LabService(db_session)
    primary = await service.register_source_document(
        _source_input(
            title="Primary measurement",
            artifact_sha256="1" * 64,
            independence_group="primary-lineage",
        )
    )
    review = await service.register_source_document(
        _source_input(
            source_type="REVIEW_PAPER",
            title="Review repeating the primary measurement",
            artifact_sha256="2" * 64,
            identifiers={"doi": "10.1000/review"},
            independence_group="primary-lineage",
        )
    )
    database = await service.register_source_document(
        _source_input(
            source_type="AUTHORITATIVE_DATABASE_RECORD",
            title="Database record derived from the primary measurement",
            artifact_sha256="3" * 64,
            identifiers={"accession": "DB-1"},
            independence_group="primary-lineage",
        )
    )
    await service.add_source_derivation(
        child_source_version_id=review.id,
        parent_source_version_id=primary.id,
        relation="DERIVED_FROM",
        relation_scopes=_relation_scopes(),
    )
    await service.add_source_derivation(
        child_source_version_id=database.id,
        parent_source_version_id=primary.id,
        relation="DERIVED_FROM",
        relation_scopes=_relation_scopes("observations.database_threshold"),
    )
    review_extraction = await service.record_source_extraction(
        _extraction_input(
            review.id,
            output_observation_id="observation-shared",
            input_sha256="4" * 64,
            output_sha256="5" * 64,
        )
    )
    database_extraction = await service.record_source_extraction(
        _extraction_input(
            database.id,
            output_observation_id="observation-shared",
            parser_or_model_version="database-parser/1",
            original_wording="Database value 7.0 microgram/m3",
            input_sha256="6" * 64,
            output_sha256="7" * 64,
        )
    )
    await _accept_extraction(service, review_extraction.id)
    await _accept_extraction(service, database_extraction.id)

    graph = await service.reconstruct_observation_derivation(
        "observation-shared",
        required_scope="threshold_screening",
    )

    assert graph["schema"] == "lab-observation-derivation-v1"
    assert graph["observation_id"] == "observation-shared"
    assert graph["required_scope"] == "threshold_screening"
    assert graph["complete"] is True
    assert graph["independence_groups"] == ["primary-lineage"]
    assert {edge["relation"] for edge in graph["derivation_links"]} == {
        "DERIVED_FROM"
    }
    assert len(graph["derivation_links"]) == 2
    assert all(link["relation_scopes"] for link in graph["derivation_links"])
    assert {source["source_type"] for source in graph["sources"]} == {
        "PRIMARY_PEER_REVIEWED_PAPER",
        "REVIEW_PAPER",
        "AUTHORITATIVE_DATABASE_RECORD",
    }
    assert {
        item["effective_state"] for item in graph["extractions"]
    } == {"ACCEPTED_FOR_SCOPED_USE"}
    assert "reliability_score" not in graph


@pytest.mark.asyncio
async def test_derivation_links_reject_self_duplicate_and_cycles(db_session):
    service = LabService(db_session)
    primary = await service.register_source_document(
        _source_input(
            title="Primary",
            artifact_sha256="1" * 64,
            independence_group="lineage-1",
        )
    )
    review = await service.register_source_document(
        _source_input(
            source_type="REVIEW_PAPER",
            title="Review",
            artifact_sha256="2" * 64,
            identifiers={"doi": "10.1000/review-2"},
            independence_group="lineage-1",
        )
    )
    primary_id = primary.id
    review_id = review.id

    with pytest.raises(SourceAuthorityConflictError) as self_link:
        await service.add_source_derivation(
            child_source_version_id=primary_id,
            parent_source_version_id=primary_id,
            relation="DERIVED_FROM",
            relation_scopes=_relation_scopes(),
        )
    assert self_link.value.code == "SOURCE_DERIVATION_SELF_LINK"

    await service.add_source_derivation(
        child_source_version_id=review_id,
        parent_source_version_id=primary_id,
        relation="DERIVED_FROM",
        relation_scopes=_relation_scopes(),
    )
    with pytest.raises(SourceAuthorityConflictError) as duplicate:
        await service.add_source_derivation(
            child_source_version_id=review_id,
            parent_source_version_id=primary_id,
            relation="DERIVED_FROM",
            relation_scopes=_relation_scopes(),
        )
    assert duplicate.value.code == "SOURCE_DERIVATION_DUPLICATE"

    with pytest.raises(SourceAuthorityConflictError) as cycle:
        await service.add_source_derivation(
            child_source_version_id=primary_id,
            parent_source_version_id=review_id,
            relation="DERIVED_FROM",
            relation_scopes=_relation_scopes(),
        )
    assert cycle.value.code == "SOURCE_DERIVATION_CYCLE"


@pytest.mark.asyncio
async def test_reconstruction_is_incomplete_for_missing_staged_or_wrong_scope(
    db_session,
):
    service = LabService(db_session)
    missing = await service.reconstruct_observation_derivation(
        "missing-observation",
        required_scope="threshold_screening",
    )
    assert missing == {
        "schema": "lab-observation-derivation-v1",
        "observation_id": "missing-observation",
        "required_scope": "threshold_screening",
        "complete": False,
        "sources": [],
        "derivation_links": [],
        "extractions": [],
        "independence_groups": [],
    }

    source = await service.register_source_document(
        _source_input(
            title="Scoped source",
            artifact_sha256="8" * 64,
            independence_group="scoped-lineage",
        )
    )
    extraction = await service.record_source_extraction(
        _extraction_input(
            source.id,
            output_observation_id="observation-scoped",
            input_sha256="9" * 64,
            output_sha256="a" * 64,
        )
    )
    staged = await service.reconstruct_observation_derivation(
        "observation-scoped",
        required_scope="threshold_screening",
    )
    assert staged["complete"] is False
    assert staged["extractions"][0]["effective_state"] == "STAGED"

    await _accept_extraction(service, extraction.id)
    wrong_scope = await service.reconstruct_observation_derivation(
        "observation-scoped",
        required_scope="release",
    )
    assert wrong_scope["complete"] is False
