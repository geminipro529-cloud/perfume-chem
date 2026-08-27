from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.models.lab_analytical import (
    LabAnalyticalClaimAssessment,
    LabAnalyticalMethodAuthority,
    LabAnalyticalPeakAuthority,
    LabAnalyticalRunAuthority,
    LabAnalyticalSequence,
    LabMethodValidationRecord,
)
from app.services.lab_analytical import canonical_json_sha256
from app.services.lab_science import (
    AnalyticalQCInput,
    ScienceAuthorityConflictError,
)
from app.services.lab_service import LabService
from tests.unit.test_b5_analytical_service import (
    _a2_exact_analytical_claim,
    _claim_request,
    _complete_peak_authority_graph,
    _method_configuration,
    _record_required_qc,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B5_HEAD = "20260731_0009"


def _config(database_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path.as_posix()}",
    )
    return config


@asynccontextmanager
async def _migrated_service(database_path: Path):
    command.upgrade(_config(database_path), B5_HEAD)
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    engine = create_async_engine(database_url)

    @event.listens_for(engine.sync_engine, "connect")
    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        async with factory() as session:
            yield session, LabService(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_b5_supported_chain_persists_exact_authority_and_a2_claim(
    tmp_path,
):
    async with _migrated_service(tmp_path / "b5-supported.db") as (
        session,
        service,
    ):
        graph = await _complete_peak_authority_graph(service)
        await _record_required_qc(
            service,
            graph["run"].id,
            graph["method"].evidence_record_id,
        )

        assessment = await service.assess_analytical_claim(
            _claim_request(graph)
        )
        exact_claim = await service.create_claim_assessment_version(
            _a2_exact_analytical_claim(
                graph["run"].id,
                graph["method"].evidence_record_id,
                assessment_id=assessment.id,
            )
        )
        await session.commit()

        vendor = await service.repository.get_analytical_attachment(
            graph["run_authority"].raw_vendor_attachment_id
        )
        open_export = await service.repository.get_analytical_attachment(
            graph["run_authority"].open_export_attachment_id
        )
        evidence = await service.repository.get_evidence_record(
            graph["method"].evidence_record_id
        )
        assert vendor is not None
        assert open_export is not None
        assert evidence is not None

        assert assessment.decision == "SUPPORTED_FOR_SCOPE"
        assert assessment.analytical_run_id == graph["run"].id
        assert assessment.run_authority_id == graph["run_authority"].id
        assert assessment.peak_authority_id == graph["peak_authority"].id
        assert assessment.evidence_record_id == evidence.id
        assert assessment.upstream_hashes_json == {
            "analytical_run_authority": (
                graph["run_authority"].content_sha256
            ),
            "analytical_peak_authority": (
                graph["peak_authority"].content_sha256
            ),
            "method_authority": graph["method_authority"].content_sha256,
            "method_validation": graph["validation"].content_sha256,
            "sequence": graph["sequence"].content_sha256,
            "raw_vendor_attachment": vendor.content_sha256,
            "open_export_attachment": open_export.content_sha256,
            "evidence": canonical_json_sha256(
                {
                    "evidence_record_id": evidence.id,
                    "payload_sha256": evidence.payload_sha256,
                }
            ),
        }
        assert exact_claim.decision == "ALLOW_EXACT"
        assert (
            exact_claim.authority_json[
                "analytical_authority_assessment_id"
            ]
            == assessment.id
        )

        assert (
            await session.get(
                LabAnalyticalMethodAuthority,
                graph["method_authority"].id,
            )
        ).method_version_id == graph["method"].id
        assert (
            await session.get(
                LabMethodValidationRecord,
                graph["validation"].id,
            )
        ).method_authority_id == graph["method_authority"].id
        assert (
            await session.get(
                LabAnalyticalSequence,
                graph["sequence"].id,
            )
        ).method_authority_id == graph["method_authority"].id
        assert (
            await session.get(
                LabAnalyticalRunAuthority,
                graph["run_authority"].id,
            )
        ).analytical_run_id == graph["run"].id
        assert (
            await session.get(
                LabAnalyticalPeakAuthority,
                graph["peak_authority"].id,
            )
        ).analytical_run_authority_id == graph["run_authority"].id
        assert (
            await session.get(
                LabAnalyticalClaimAssessment,
                assessment.id,
            )
        ).peak_authority_id == graph["peak_authority"].id


@pytest.mark.asyncio
async def test_b5_blocking_qc_twin_withholds_and_cannot_authorize_a2_exact(
    tmp_path,
):
    async with _migrated_service(tmp_path / "b5-blocked.db") as (
        session,
        service,
    ):
        graph = await _complete_peak_authority_graph(service)
        await _record_required_qc(
            service,
            graph["run"].id,
            graph["method"].evidence_record_id,
            status_by_type={"BLANK": "FAIL"},
        )
        assessment = await service.assess_analytical_claim(
            _claim_request(graph)
        )
        await session.commit()

        assert assessment.decision == "WITHHELD"
        assert assessment.missing_requirements_json == [
            "QC_FAILED_BLOCKING"
        ]
        assert assessment.qualifications_json == []
        assert assessment.result_json is None

        with pytest.raises(ScienceAuthorityConflictError) as rejected:
            await service.create_claim_assessment_version(
                _a2_exact_analytical_claim(
                    graph["run"].id,
                    graph["method"].evidence_record_id,
                    assessment_id=assessment.id,
                )
            )
        assert rejected.value.code == "ANALYTICAL_QC_NOT_ACCEPTED"


@pytest.mark.asyncio
async def test_b5_qualifying_qc_twin_is_advisory_and_cannot_authorize_exact(
    tmp_path,
):
    async with _migrated_service(tmp_path / "b5-qualified.db") as (
        session,
        service,
    ):
        configuration = _method_configuration()
        qc_plan = {
            "required_checks": [
                *configuration["qc_plan"]["required_checks"],
                "DUPLICATE",
            ],
            "failure_policy": {
                **configuration["qc_plan"]["failure_policy"],
                "DUPLICATE": "QUALIFY",
            },
        }
        graph = await _complete_peak_authority_graph(
            service,
            qc_plan=qc_plan,
            include_duplicate=True,
        )
        evidence_id = graph["method"].evidence_record_id
        await _record_required_qc(
            service,
            graph["run"].id,
            evidence_id,
        )
        await service.record_analytical_qc(
            AnalyticalQCInput(
                analytical_run_id=graph["run"].id,
                qc_key="qc:duplicate",
                qc_type="DUPLICATE",
                status="FAIL",
                criteria={"acceptance": "bounded duplicate precision"},
                observed={"result": "outside criterion"},
                evidence_record_id=evidence_id,
            )
        )

        assessment = await service.assess_analytical_claim(
            _claim_request(graph)
        )
        await session.commit()

        assert assessment.decision == "ADVISORY_ONLY"
        assert assessment.missing_requirements_json == []
        assert assessment.qualifications_json == ["QC_FAILED_QUALIFYING"]
        assert assessment.result_json is not None

        with pytest.raises(ScienceAuthorityConflictError) as rejected:
            await service.create_claim_assessment_version(
                _a2_exact_analytical_claim(
                    graph["run"].id,
                    evidence_id,
                    assessment_id=assessment.id,
                )
            )
        assert rejected.value.code == "ANALYTICAL_QC_NOT_ACCEPTED"
