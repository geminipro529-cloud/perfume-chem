import json
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.base import Base
from app.services.lab_export import LabExportService
from app.services.lab_science import (
    AnalyticalAttachmentInput,
    AnalyticalPeakInput,
    AnalyticalQCInput,
    ClaimAssessmentInput,
    ClaimEvidenceInput,
    GCOEventInput,
    RegulatoryAssessmentInput,
    RegulatoryFindingInput,
)
from app.services.lab_service import LabService
from tests.unit.test_a2_planning_schema import PLANNING_TABLES
from tests.unit.test_a2_science_schema import SCIENCE_AUTHORITY_TABLES
from tests.unit.test_a2_science_service import (
    _evidence,
    _formula_version,
    _method_input,
    _run_input,
)


async def _science_graph(session):
    service = LabService(session)
    evidence = await _evidence(service, "science-export:test")
    material = await service.create_material("Science export jasmine")
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
            tentative_identity="Science export jasmine",
            material_id=material.id,
            identity_state="CONFIRMED",
            match_score=0.95,
            quantitation_basis="external_standard",
            quantity=0.01,
            quantity_unit="mass_fraction",
            standard_uncertainty=0.001,
            notes="Bounded export fixture",
        )
    )
    await service.record_analytical_qc(
        AnalyticalQCInput(
            analytical_run_id=run.id,
            qc_key="blank",
            qc_type="BLANK",
            status="PASS",
            criteria={},
            observed={},
            evidence_record_id=evidence.id,
        )
    )
    await service.bind_analytical_attachment(
        AnalyticalAttachmentInput(
            analytical_run_id=run.id,
            attachment_kind="RAW_DATA",
            media_type="application/octet-stream",
            byte_length=100,
            content_sha256="a" * 64,
            storage_locator="artifact://science-export/run-1",
            evidence_record_id=evidence.id,
        )
    )
    await service.record_gco_event(
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
    regulatory = await service.create_regulatory_assessment_version(
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
    await service.record_regulatory_finding(
        RegulatoryFindingInput(
            regulatory_assessment_version_id=regulatory.id,
            finding_key="finding-1",
            restriction_id=None,
            material_id=material.id,
            substance_identity="Science export jasmine",
            observed_fraction=0.01,
            maximum_fraction=0.02,
            concentration_basis="mass_fraction",
            result_state="PASS",
            detail="Within named test limit",
            evidence_record_id=evidence.id,
        )
    )
    claim = await service.create_claim_assessment_version(
        ClaimAssessmentInput(
            schema_version="a2-claim-v1",
            claim_type="REGULATORY_STATUS",
            subject_type="REGULATORY_ASSESSMENT",
            subject_id=regulatory.id,
            policy_version="policy-v1",
            decision="ALLOW_EXACT",
            authority={"scope": "named test standard state"},
            missing_evidence=(),
            conflicts=(),
            permitted_wording="Passes the named test standard state",
            forbidden_wording="Unqualified global compliance",
            human_review_state="APPROVED",
            reviewer_pseudonym="reviewer-1",
            reviewed_at=datetime(2026, 7, 30, 1, 0, tzinfo=timezone.utc),
            evidence_links=(
                ClaimEvidenceInput(
                    evidence_record_id=evidence.id,
                    role="DIRECT",
                ),
            ),
        )
    )
    return service, method, run, regulatory, claim


async def _row_count(session, table_names: set[str]) -> int:
    total = 0
    for table_name in sorted(table_names):
        table = Base.metadata.tables[table_name]
        total += int(
            await session.scalar(select(func.count()).select_from(table)) or 0
        )
    return total


@pytest.mark.asyncio
async def test_v3_export_orders_complete_science_authority_graph(db_session):
    await _science_graph(db_session)
    packet = await LabExportService(db_session).export_science_workspace()
    assert packet["format_revision"] == "lab-export-v3"
    assert SCIENCE_AUTHORITY_TABLES <= set(packet["tables"])
    assert packet["ordering_contract"]["analytical_method_versions"] == [
        "method_id",
        "version_number",
        "id",
    ]
    assert packet["ordering_contract"]["analytical_runs"] == ["run_id", "id"]
    assert packet["ordering_contract"]["regulatory_assessment_versions"] == [
        "assessment_id",
        "version_number",
        "id",
    ]
    assert packet["ordering_contract"]["claim_assessment_versions"] == [
        "claim_id",
        "version_number",
        "id",
    ]
    attachment = packet["tables"]["lab_analytical_attachments"][0]
    assert attachment["content_sha256"] == "a" * 64
    assert "content_bytes" not in attachment


@pytest.mark.asyncio
async def test_v3_export_import_is_byte_deterministic_and_idempotent(db_session):
    await _science_graph(db_session)
    exporter = LabExportService(db_session)
    packet = await exporter.export_science_workspace()
    before = await exporter.canonical_bytes()
    result = await exporter.import_workspace(packet)
    after = await exporter.canonical_bytes()
    assert result.inserted == 0
    assert result.skipped == sum(
        len(rows) for rows in packet["tables"].values()
    )
    assert after == before
    assert json.loads(after) == packet


@pytest.mark.asyncio
async def test_legacy_exports_do_not_invent_science_authority(db_session):
    exporter = LabExportService(db_session)
    v1 = await exporter.export_workspace()
    v2 = await exporter.export_planning_workspace()
    assert v1["format_revision"] == "lab-export-v1"
    assert v2["format_revision"] == "lab-export-v2"
    assert not (SCIENCE_AUTHORITY_TABLES & set(v1["tables"]))
    assert not (SCIENCE_AUTHORITY_TABLES & set(v2["tables"]))

    for packet in (v1, v2):
        result = await exporter.import_workspace(packet)
        assert result.inserted == 0
        assert await _row_count(db_session, SCIENCE_AUTHORITY_TABLES) == 0
    assert await _row_count(db_session, PLANNING_TABLES) == 0
