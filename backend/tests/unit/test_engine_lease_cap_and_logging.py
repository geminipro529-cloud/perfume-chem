"""No-op lease renewals at the cap, and in-process migrations keeping app logging."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import update

from app.db_bootstrap import upgrade_database
from app.models.lab_engine_jobs import LabEngineJob
from app.services.lab_service import LabService
from tests.unit.test_cp2_engine_jobs import _formula_payload

BACKEND_ROOT = Path(__file__).resolve().parents[2]


async def _running_job(db_session, key: str, timeout_seconds: int):
    service = LabService(db_session)
    job, _ = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key=key,
    )
    job_id = job.id
    await db_session.execute(
        update(LabEngineJob)
        .where(LabEngineJob.id == job_id)
        .values(timeout_seconds=timeout_seconds)
    )
    await db_session.commit()
    lease = await service.claim_next_engine_job(owner="w:1", lease_seconds=30)
    assert lease is not None and lease.job.id == job_id
    await service.mark_engine_job_running(job_id=job_id, owner="w:1", token=lease.token)
    return service, job_id, lease.token


async def _event_count(service, job_id: str) -> int:
    return len(await service._engine_job_events(job_id))


@pytest.mark.asyncio
async def test_renewal_at_the_cap_appends_no_event(db_session) -> None:
    # Cap = leased_at + 5 + 60 s, so a 3600 s renewal is clipped to it.
    service, job_id, token = await _running_job(db_session, "cap", 5)
    before = await _event_count(service, job_id)
    first = await service.renew_engine_job_lease(
        job_id=job_id, owner="w:1", token=token, lease_seconds=3600
    )
    assert await _event_count(service, job_id) == before + 1
    second = await service.renew_engine_job_lease(
        job_id=job_id, owner="w:1", token=token, lease_seconds=3600
    )
    assert await _event_count(service, job_id) == before + 1
    assert second == first


@pytest.mark.asyncio
async def test_renewal_below_the_cap_still_appends_an_event(db_session) -> None:
    service, job_id, token = await _running_job(db_session, "below-cap", 3000)
    before = await _event_count(service, job_id)
    await service.renew_engine_job_lease(
        job_id=job_id, owner="w:1", token=token, lease_seconds=300
    )
    assert await _event_count(service, job_id) == before + 1


def test_in_process_migration_keeps_application_logging(tmp_path) -> None:
    app_logger = logging.getLogger("app.services.engine_worker_process")
    root = logging.getLogger()
    saved_root_level, saved_logger_level = root.level, app_logger.level
    root.setLevel(logging.INFO)
    app_logger.setLevel(logging.NOTSET)
    handlers = list(root.handlers)
    try:
        assert app_logger.isEnabledFor(logging.INFO)
        config = Config(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        config.set_main_option(
            "sqlalchemy.url", f"sqlite:///{(tmp_path / 'log.db').as_posix()}"
        )
        upgrade_database(config, "head")
        assert root.level == logging.INFO
        assert list(root.handlers) == handlers
        assert app_logger.isEnabledFor(logging.INFO)
    finally:
        root.setLevel(saved_root_level)
        app_logger.setLevel(saved_logger_level)
