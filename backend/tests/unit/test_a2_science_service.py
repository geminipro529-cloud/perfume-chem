from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.lab_science import LabClaimAssessmentEvidenceLink
from app.services.lab_science import (
    AnalyticalAttachmentInput,
    AnalyticalMethodInput,
    AnalyticalPeakInput,
    AnalyticalQCInput,
    AnalyticalRunInput,
    ClaimAssessmentInput,
    ClaimEvidenceInput,
    GCOEventInput,
    RegulatoryAssessmentInput,
    RegulatoryFindingInput,
    ScienceAuthorityConflictError,
    ScienceAuthorityError,
)
from app.services.lab_service import LabService


async def _evidence(service: LabService, key: str = "science:test"):
    return await service.record_evidence(
        claim_key=key,
        classification="EXACT",
        source_locator=f"test://{key}",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )


async def _formula_version(service: LabService):
    formula = await service.create_formula("A2 science fixture")
    return await service.add_formula_version(
        formula.id,
        brief={"purpose": "science authority test"},
        constraints={},
        source={"kind": "test"},
    )


def _method_input(evidence_id: str, *, intended_use: str = "Identity support"):
    return AnalyticalMethodInput(
        schema_version="a2-analytical-v1",
        technique="GCMS",
        intended_use=intended_use,
        status="VALIDATED",
        method={"column": "test-column", "temperature_program": "test"},
        evidence_record_id=evidence_id,
    )


def _run_input(method_id: str, formula_version_id: str):
    return AnalyticalRunInput(
        method_version_id=method_id,
        run_kind="GCMS",
        status="QC_ACCEPTED",
        instrument_identifier="instrument:pseudonymous",
        acquired_at=datetime(2026, 7, 30, 1, 0, tzinfo=timezone.utc),
        parameters={"injection": "split"},
        deviations=(),
        processing_version="processor-v1",
        formula_version_id=formula_version_id,
    )


@pytest.mark.asyncio
async def test_analytical_method_versions_are_hash_chained_and_evidence_backed(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service)
    first = await service.create_analytical_method_version(
        _method_input(evidence.id)
    )
    second = await service.create_analytical_method_version(
        _method_input(evidence.id, intended_use="Identity and quantitation support"),
        parent_version_id=first.id,
    )
    assert second.method_id == first.method_id
    assert second.version_number == 2
    assert second.parent_version_id == first.id
    assert second.parent_sha256 == first.content_sha256
    assert second.content_sha256 != first.content_sha256

    with pytest.raises(ScienceAuthorityConflictError) as stale:
        await service.create_analytical_method_version(
            _method_input(evidence.id),
            parent_version_id=first.id,
        )
    assert stale.value.code == "ANALYTICAL_METHOD_PARENT_NOT_LATEST"


@pytest.mark.asyncio
async def test_complete_analytical_graph_preserves_units_qc_digest_and_gco(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service)
    formula_version = await _formula_version(service)
    method = await service.create_analytical_method_version(
        _method_input(evidence.id)
    )
    run = await service.record_analytical_run(
        _run_input(method.id, formula_version.id)
    )
    peak = await service.record_analytical_peak(
        AnalyticalPeakInput(
            analytical_run_id=run.id,
            peak_key="peak-1",
            retention_time_minutes=2.5,
            retention_index=1050.0,
            area=1200.0,
            response_factor=1.0,
            qualifier_ions=(43, 71),
            tentative_identity="Jasmine Absolute",
            material_id=None,
            identity_state="TENTATIVE",
            match_score=0.95,
            quantitation_basis="external_standard",
            quantity=0.2,
            quantity_unit="mass_fraction",
            standard_uncertainty=0.01,
            notes="Bounded fixture",
        )
    )
    qc = await service.record_analytical_qc(
        AnalyticalQCInput(
            analytical_run_id=run.id,
            qc_key="blank",
            qc_type="BLANK",
            status="PASS",
            criteria={"maximum_area": 1.0},
            observed={"area": 0.0},
            evidence_record_id=evidence.id,
        )
    )
    attachment = await service.bind_analytical_attachment(
        AnalyticalAttachmentInput(
            analytical_run_id=run.id,
            attachment_kind="RAW_DATA",
            media_type="application/octet-stream",
            byte_length=100,
            content_sha256="a" * 64,
            storage_locator="artifact://analytical/run-1",
            evidence_record_id=evidence.id,
        )
    )
    event = await service.record_gco_event(
        GCOEventInput(
            analytical_run_id=run.id,
            analytical_peak_id=peak.id,
            event_key="event-1",
            retention_time_minutes=2.5,
            retention_index=1050.0,
            descriptor="floral",
            intensity=0.6,
            assessor_pseudonym="assessor-1",
            repeatability={"replicates": 2},
            evidence_record_id=evidence.id,
        )
    )
    assert peak.quantity_unit == "mass_fraction"
    assert qc.status == "PASS"
    assert attachment.content_sha256 == "a" * 64
    assert not hasattr(attachment, "content_bytes")
    assert event.analytical_peak_id == peak.id


@pytest.mark.asyncio
async def test_analytical_commands_fail_closed_on_missing_subject_and_bad_digest(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service)
    method = await service.create_analytical_method_version(
        _method_input(evidence.id)
    )
    with pytest.raises(ScienceAuthorityError):
        await service.record_analytical_run(
            replace(
                _run_input(method.id, "missing-formula-version"),
                formula_version_id=None,
            )
        )
    with pytest.raises(ScienceAuthorityError):
        AnalyticalAttachmentInput(
            analytical_run_id="missing-run",
            attachment_kind="RAW_DATA",
            media_type="application/octet-stream",
            byte_length=1,
            content_sha256="not-a-digest",
            storage_locator="artifact://bad",
            evidence_record_id=evidence.id,
        )


@pytest.mark.asyncio
async def test_gco_event_rejects_peak_from_another_run(db_session):
    service = LabService(db_session)
    evidence = await _evidence(service)
    formula_version = await _formula_version(service)
    method = await service.create_analytical_method_version(
        _method_input(evidence.id)
    )
    left = await service.record_analytical_run(
        _run_input(method.id, formula_version.id)
    )
    right = await service.record_analytical_run(
        replace(
            _run_input(method.id, formula_version.id),
            instrument_identifier="instrument:second",
        )
    )
    peak = await service.record_analytical_peak(
        AnalyticalPeakInput(
            analytical_run_id=left.id,
            peak_key="left-peak",
            identity_state="UNASSIGNED",
        )
    )
    with pytest.raises(ScienceAuthorityConflictError) as mismatch:
        await service.record_gco_event(
            GCOEventInput(
                analytical_run_id=right.id,
                analytical_peak_id=peak.id,
                event_key="wrong-run",
                descriptor="floral",
                assessor_pseudonym="assessor-1",
            )
        )
    assert mismatch.value.code == "GCO_PEAK_RUN_MISMATCH"


@pytest.mark.asyncio
async def test_regulatory_pass_requires_current_sourced_resolved_authority(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service, "regulatory:test")
    formula_version = await _formula_version(service)
    valid = RegulatoryAssessmentInput(
        schema_version="a2-regulatory-v1",
        subject_type="FORMULA_VERSION",
        subject_id=formula_version.id,
        standard_identifier="test-standard",
        standard_amendment="2026-01",
        standard_state="CURRENT",
        source_evidence_record_id=evidence.id,
        jurisdiction="TEST",
        product_category="fine-fragrance",
        concentration_basis="mass_fraction",
        finished_product_concentration=0.2,
        effective_date=date(2026, 1, 1),
        evaluated_at=datetime(2026, 7, 30, 1, 0, tzinfo=timezone.utc),
        result_state="PASS",
        assumptions=(),
        unresolved=(),
        permitted_wording="Passes the named test standard state",
    )
    assessment = await service.create_regulatory_assessment_version(valid)
    finding = await service.record_regulatory_finding(
        RegulatoryFindingInput(
            regulatory_assessment_version_id=assessment.id,
            finding_key="finding-1",
            restriction_id=None,
            material_id=None,
            substance_identity="Test substance",
            observed_fraction=0.01,
            maximum_fraction=0.02,
            concentration_basis="mass_fraction",
            result_state="PASS",
            detail="Within named test limit",
            evidence_record_id=evidence.id,
        )
    )
    assert finding.result_state == "PASS"

    with pytest.raises(ScienceAuthorityConflictError) as unknown:
        await service.create_regulatory_assessment_version(
            replace(
                valid,
                standard_state="UNKNOWN",
                source_evidence_record_id=None,
            )
        )
    assert unknown.value.code == "REGULATORY_PASS_NOT_SUPPORTED"


@pytest.mark.asyncio
async def test_new_a2_claim_writes_are_capped_below_exact_authority(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service, "claim:test")
    formula_version = await _formula_version(service)
    command = ClaimAssessmentInput(
        schema_version="a2-claim-v1",
        claim_type="FORMULA_IDENTITY",
        subject_type="FORMULA_VERSION",
        subject_id=formula_version.id,
        policy_version="policy-v1",
        decision="ALLOW_EXACT",
        authority={"scope": "named formula version"},
        missing_evidence=(),
        conflicts=(),
        permitted_wording="This exact formula version was recorded",
        forbidden_wording="Universal equivalence",
        human_review_state="APPROVED",
        reviewer_pseudonym="reviewer-1",
        reviewed_at=datetime(2026, 7, 30, 1, 0, tzinfo=timezone.utc),
        evidence_links=(
            ClaimEvidenceInput(evidence_record_id=evidence.id, role="DIRECT"),
        ),
    )
    with pytest.raises(ScienceAuthorityConflictError) as error:
        await service.create_claim_assessment_version(command)
    assert error.value.code == "CLAIM_LEGACY_DECISION_EXCEEDS_CEILING"
    assert (
        await db_session.scalar(
            select(func.count()).select_from(LabClaimAssessmentEvidenceLink)
        )
        == 0
    )


@pytest.mark.asyncio
async def test_a4_claim_rejects_decision_above_dimension_authority(db_session):
    service = LabService(db_session)
    evidence = await _evidence(service, "a4-overclaim:test")
    formula_version = await _formula_version(service)
    authority = {
        "target_row_coverage_complete": True,
        "source_coverage_complete": True,
        "source_independence": False,
        "identity_resolved": True,
        "quantity_basis_complete": True,
        "uncertainty_bounded": True,
        "contradiction_present": False,
        "method_validated": True,
        "analytical_support": True,
        "sensory_support": True,
        "model_applicable": True,
        "safety_complete": True,
        "family_defined": True,
        "family_evidence_complete": True,
        "human_reviewed": True,
        "scope_defined": True,
        "exact_evidence": True,
        "documentary_support": True,
    }
    command = ClaimAssessmentInput(
        schema_version="a4-claim-v1",
        claim_type="RELEASE",
        subject_type="FORMULA_VERSION",
        subject_id=formula_version.id,
        policy_version="a4-policy-v1",
        decision="ALLOW_EXACT",
        authority=authority,
        missing_evidence=(),
        conflicts=(),
        permitted_wording="Scientifically released",
        forbidden_wording=None,
        human_review_state="APPROVED",
        reviewer_pseudonym="reviewer-1",
        reviewed_at=datetime(2026, 7, 30, 2, 0, tzinfo=timezone.utc),
        evidence_links=(
            ClaimEvidenceInput(evidence_record_id=evidence.id, role="DIRECT"),
        ),
    )

    with pytest.raises(ScienceAuthorityConflictError) as error:
        await service.create_claim_assessment_version(command)

    assert error.value.code == "CLAIM_DECISION_EXCEEDS_AUTHORITY"


@pytest.mark.asyncio
async def test_a4_claim_persists_scoped_identity_with_complete_dimensions(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service, "a4-scoped:test")
    formula_version = await _formula_version(service)
    authority = {
        "source_coverage_complete": True,
        "source_independence": True,
        "identity_resolved": True,
        "scope_defined": True,
        "exact_evidence": False,
        "documentary_support": True,
    }

    assessment = await service.create_claim_assessment_version(
        ClaimAssessmentInput(
            schema_version="a4-claim-v1",
            claim_type="IDENTITY",
            subject_type="FORMULA_VERSION",
            subject_id=formula_version.id,
            policy_version="a4-policy-v1",
            decision="ALLOW_SCOPED",
            authority=authority,
            missing_evidence=(),
            conflicts=(),
            permitted_wording="Identity supported for this formula version",
            forbidden_wording="Universal identity",
            human_review_state="APPROVED",
            reviewer_pseudonym="reviewer-1",
            reviewed_at=datetime(2026, 7, 30, 2, 5, tzinfo=timezone.utc),
            evidence_links=(
                ClaimEvidenceInput(
                    evidence_record_id=evidence.id,
                    role="DIRECT",
                ),
            ),
        )
    )

    assert assessment.decision == "ALLOW_SCOPED"


@pytest.mark.asyncio
async def test_legacy_a2_claim_cannot_request_exact_even_before_qc(db_session):
    service = LabService(db_session)
    evidence = await _evidence(service, "analytical-claim:test")
    formula_version = await _formula_version(service)
    method = await service.create_analytical_method_version(
        _method_input(evidence.id)
    )
    run = await service.record_analytical_run(
        _run_input(method.id, formula_version.id)
    )
    await service.record_analytical_qc(
        AnalyticalQCInput(
            analytical_run_id=run.id,
            qc_key="identity-qc",
            qc_type="IDENTITY",
            status="UNKNOWN",
            criteria={},
            observed={},
            evidence_record_id=evidence.id,
        )
    )
    command = ClaimAssessmentInput(
        schema_version="a2-claim-v1",
        claim_type="ANALYTICAL_IDENTITY",
        subject_type="ANALYTICAL_RUN",
        subject_id=run.id,
        policy_version="policy-v1",
        decision="ALLOW_EXACT",
        authority={},
        missing_evidence=(),
        conflicts=(),
        permitted_wording="Exact analytical identity",
        forbidden_wording=None,
        human_review_state="NOT_REQUIRED",
        reviewer_pseudonym=None,
        reviewed_at=None,
        evidence_links=(
            ClaimEvidenceInput(evidence_record_id=evidence.id, role="DIRECT"),
        ),
    )
    with pytest.raises(ScienceAuthorityConflictError) as error:
        await service.create_claim_assessment_version(command)
    assert error.value.code == "CLAIM_LEGACY_DECISION_EXCEEDS_CEILING"


@pytest.mark.asyncio
async def test_claim_assessment_never_persists_legacy_authority_vector_fields(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service, "vector:test")
    formula_version = await _formula_version(service)
    assessment = await service.create_claim_assessment_version(
        ClaimAssessmentInput(
            schema_version="a2-claim-v1",
            claim_type="ADVISORY",
            subject_type="FORMULA_VERSION",
            subject_id=formula_version.id,
            policy_version="policy-v1",
            decision="ADVISORY_ONLY",
            authority={"evidence_classes": ["documentary"]},
            missing_evidence=("held-out sensory",),
            conflicts=(),
            permitted_wording="Documentary advisory only",
            forbidden_wording="Scientific validation",
            human_review_state="NOT_REQUIRED",
            reviewer_pseudonym=None,
            reviewed_at=None,
            evidence_links=(
                ClaimEvidenceInput(
                    evidence_record_id=evidence.id,
                    role="SUPPORTING",
                ),
            ),
        )
    )
    assert not hasattr(assessment, "documentary")
    assert not hasattr(assessment, "experimental")
    assert not hasattr(assessment, "sensory")
    assert assessment.authority_json == {
        "authority_scope": "LEGACY_ADVISORY_ONLY",
        "release_authority": False,
        "safety_authority": False,
        "compounding_authority": False,
        "caller_authority_discarded": True,
    }
    assert assessment.permitted_wording == (
        "Advisory evidence only; no release, safety, or compounding authority."
    )
