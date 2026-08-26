import asyncio
from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.lab_science import (
    LabAnalyticalMethodVersion,
    LabClaimAssessmentVersion,
    LabRegulatoryFinding,
)
from app.services.lab_science import (
    ClaimAssessmentInput,
    ClaimEvidenceInput,
    RegulatoryAssessmentInput,
    RegulatoryFindingInput,
    ScienceAuthorityConflictError,
)
from app.services.lab_service import LabService
from tests.unit.test_a2_science_service import (
    _evidence,
    _formula_version,
    _method_input,
)


@pytest.mark.asyncio
async def test_claim_graph_rolls_back_before_insert_when_any_evidence_is_missing(
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service, "claim-atomic:test")
    formula_version = await _formula_version(service)
    command = ClaimAssessmentInput(
        schema_version="a2-claim-v1",
        claim_type="ADVISORY",
        subject_type="FORMULA_VERSION",
        subject_id=formula_version.id,
        policy_version="policy-v1",
        decision="ADVISORY_ONLY",
        authority={},
        missing_evidence=("held-out validation",),
        conflicts=(),
        permitted_wording="Advisory only",
        forbidden_wording="Scientific validation",
        human_review_state="NOT_REQUIRED",
        reviewer_pseudonym=None,
        reviewed_at=None,
        evidence_links=(
            ClaimEvidenceInput(
                evidence_record_id=evidence.id,
                role="SUPPORTING",
            ),
            ClaimEvidenceInput(
                evidence_record_id="missing-evidence",
                role="LIMITATION",
            ),
        ),
    )
    with pytest.raises(ScienceAuthorityConflictError) as error:
        await service.create_claim_assessment_version(command)
    assert error.value.code == "EVIDENCE_NOT_FOUND"
    assert (
        await db_session.scalar(
            select(func.count()).select_from(LabClaimAssessmentVersion)
        )
        == 0
    )


@pytest.mark.asyncio
async def test_concurrent_method_revisions_accept_only_one_latest_parent(
    test_engine,
):
    factory = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as setup_session:
        setup = LabService(setup_session)
        evidence = await _evidence(setup, "method-concurrency:test")
        parent = await setup.create_analytical_method_version(
            _method_input(evidence.id)
        )

    async def revise(intended_use: str):
        async with factory() as session:
            service = LabService(session)
            return await service.create_analytical_method_version(
                _method_input(evidence.id, intended_use=intended_use),
                parent_version_id=parent.id,
            )

    results = await asyncio.gather(
        revise("Identity support revision A"),
        revise("Identity support revision B"),
        return_exceptions=True,
    )
    assert sum(
        isinstance(result, LabAnalyticalMethodVersion) for result in results
    ) == 1
    conflicts = [
        result
        for result in results
        if isinstance(result, ScienceAuthorityConflictError)
    ]
    assert len(conflicts) == 1
    assert conflicts[0].code == "ANALYTICAL_METHOD_PARENT_NOT_LATEST"
    async with factory() as check_session:
        assert (
            await check_session.scalar(
                select(func.count()).select_from(
                    LabAnalyticalMethodVersion
                )
            )
            == 2
        )


@pytest.mark.asyncio
async def test_rejected_regulatory_finding_leaves_no_partial_row(db_session):
    service = LabService(db_session)
    evidence = await _evidence(service, "regulatory-finding-atomic:test")
    formula_version = await _formula_version(service)

    assessment = await service.create_regulatory_assessment_version(
        RegulatoryAssessmentInput(
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
    )
    valid = RegulatoryFindingInput(
        regulatory_assessment_version_id=assessment.id,
        finding_key="finding-1",
        restriction_id=None,
        material_id=None,
        substance_identity="Test substance",
        observed_fraction=0.01,
        maximum_fraction=0.02,
        concentration_basis="mass_fraction",
        result_state="PASS",
        detail="Within named limit",
        evidence_record_id=evidence.id,
    )
    with pytest.raises(ScienceAuthorityConflictError) as error:
        await service.record_regulatory_finding(
            replace(valid, observed_fraction=0.03)
        )
    assert error.value.code == "REGULATORY_FINDING_PASS_NOT_SUPPORTED"
    assert (
        await db_session.scalar(
            select(func.count()).select_from(LabRegulatoryFinding)
        )
        == 0
    )
