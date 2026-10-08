"""Engine worker autostart, table wait, lease renewal and liveness (no real workers)."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import time
from datetime import timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import db_bootstrap
from app import main as main_module
from app.core.config import get_settings
from app.models.base import Base
from app.services import engine_job_worker as worker_module
from app.services import engine_jobs as engine_jobs_module
from app.services import engine_worker_liveness as liveness_module
from app.services import engine_worker_process
from app.services import lab_service as lab_service_module
from app.services.engine_worker_liveness import (
    get_live_engine_workers,
    record_engine_worker_seen,
)
from app.services.lab_service import LabService
from tests.unit.test_cp2_engine_jobs import _formula_payload


@pytest.fixture(autouse=True)
def fresh_write_lock(monkeypatch):
    """The module-level write lock binds to the first loop that contends for it."""
    monkeypatch.setattr(lab_service_module, "_LAB_WRITE_LOCK", asyncio.Lock())


# ---------------------------------------------------------------- autostart


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, True),
        ("", True),
        ("1", True),
        ("yes", True),
        ("0", False),
        ("false", False),
        (" FALSE ", False),
        ("no", False),
        ("No", False),
    ],
)
def test_autostart_env_parsing(value, expected) -> None:
    environ = {} if value is None else {"PERFUME_ENGINE_WORKER_AUTOSTART": value}
    assert engine_worker_process.engine_worker_autostart_enabled(environ) is expected


class _FakeStdin:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls

    def close(self) -> None:
        self.calls.append(("close_stdin",))


class _FakeWorker:
    instances: list[_FakeWorker] = []
    launch_errors: list[int] = []  # 1-based launch attempts that raise

    def __init__(self, args, **kwargs) -> None:
        _FakeWorker.attempts += 1
        if _FakeWorker.attempts in _FakeWorker.launch_errors:
            raise OSError("fixture: could not start the worker")
        self.args = args
        self.kwargs = kwargs
        self.pid = 4242
        self.calls: list[tuple] = []
        self.stdin = _FakeStdin(self.calls)
        self.ignores_stop = False
        self.returncode = None
        _FakeWorker.instances.append(self)

    attempts = 0

    def poll(self):
        return self.returncode

    def terminate(self) -> None:
        self.calls.append(("terminate",))

    def wait(self, timeout):
        self.calls.append(("wait", timeout))
        if self.ignores_stop and ("kill",) not in self.calls:
            raise subprocess.TimeoutExpired(self.args, timeout)
        return 0

    def kill(self) -> None:
        self.calls.append(("kill",))


@pytest.fixture
def fake_popen(monkeypatch):
    _FakeWorker.instances = []
    _FakeWorker.launch_errors = []
    _FakeWorker.attempts = 0
    monkeypatch.setattr(engine_worker_process.subprocess, "Popen", _FakeWorker)
    monkeypatch.setattr(db_bootstrap, "upgrade_database", lambda _config: None)
    return _FakeWorker


@pytest.mark.asyncio
async def test_lifespan_starts_one_worker_and_stops_it(monkeypatch, fake_popen) -> None:
    monkeypatch.setenv("PERFUME_ENGINE_WORKER_AUTOSTART", "1")
    monkeypatch.setenv("PYTHONPATH", "/inherited")
    async with main_module.lifespan(FastAPI()):
        assert len(fake_popen.instances) == 1
        worker = fake_popen.instances[0]
        assert worker.args == [sys.executable, "-m", "app.services.engine_job_worker"]
        assert worker.kwargs["cwd"] == engine_worker_process.BACKEND_DIR
        assert worker.kwargs["env"]["PYTHONPATH"].split(":") == [
            str(engine_worker_process.BACKEND_DIR),
            str(engine_worker_process.REPOSITORY_ROOT),
            "/inherited",
        ]
        assert worker.kwargs["env"]["PERFUME_ENGINE_WORKER_PARENT_PIPE"] == "1"
        assert worker.kwargs["stdin"] == subprocess.PIPE
        assert worker.calls == []
    # Closing the pipe asks the worker to stop; no signal is needed.
    assert worker.calls == [("close_stdin",), ("wait", 10)]


@pytest.mark.asyncio
async def test_lifespan_kills_a_worker_that_ignores_terminate(
    monkeypatch, fake_popen
) -> None:
    monkeypatch.setenv("PERFUME_ENGINE_WORKER_AUTOSTART", "true")
    async with main_module.lifespan(FastAPI()):
        fake_popen.instances[0].ignores_stop = True
    assert fake_popen.instances[0].calls == [
        ("close_stdin",),
        ("wait", 10),
        ("terminate",),
        ("wait", 5),
        ("kill",),
        ("wait", 5),
    ]


@pytest.mark.asyncio
async def test_lifespan_autostart_off_starts_nothing(monkeypatch, fake_popen) -> None:
    monkeypatch.setenv("PERFUME_ENGINE_WORKER_AUTOSTART", "no")
    async with main_module.lifespan(FastAPI()):
        pass
    assert fake_popen.instances == []


@pytest.fixture
def fast_supervision(monkeypatch):
    monkeypatch.setattr(engine_worker_process, "_SUPERVISE_INTERVAL_SECONDS", 0.01, raising=False)
    monkeypatch.setattr(engine_worker_process, "_RESTART_INITIAL_DELAY_SECONDS", 0.01, raising=False)


@pytest.mark.asyncio
async def test_lifespan_replaces_a_worker_that_died(
    monkeypatch, fake_popen, fast_supervision
) -> None:
    monkeypatch.setenv("PERFUME_ENGINE_WORKER_AUTOSTART", "1")
    async with main_module.lifespan(FastAPI()):
        first = fake_popen.instances[0]
        first.returncode = -9  # SIGKILL: its leased job would otherwise hang.

        async def replaced() -> bool:
            return len(fake_popen.instances) == 2

        await _wait_until(replaced)
        second = fake_popen.instances[1]
        await asyncio.sleep(0.05)
        assert len(fake_popen.instances) == 2
    assert first.calls == []
    assert second.calls == [("close_stdin",), ("wait", 10)]


@pytest.mark.asyncio
async def test_supervisor_retries_a_launch_that_raised(
    monkeypatch, fake_popen, fast_supervision
) -> None:
    monkeypatch.setenv("PERFUME_ENGINE_WORKER_AUTOSTART", "1")
    fake_popen.launch_errors = [1, 3]  # at API start, then on a restart
    async with main_module.lifespan(FastAPI()):

        async def launched(count: int):
            async def check() -> bool:
                return len(fake_popen.instances) == count

            return check

        await _wait_until(await launched(1))
        fake_popen.instances[0].returncode = -9
        await _wait_until(await launched(2))
        assert fake_popen.attempts == 4
    assert fake_popen.instances[1].calls == [("close_stdin",), ("wait", 10)]


@pytest.mark.asyncio
async def test_lifespan_does_not_restart_a_worker_that_was_stopped(
    monkeypatch, fake_popen, fast_supervision
) -> None:
    monkeypatch.setenv("PERFUME_ENGINE_WORKER_AUTOSTART", "1")
    async with main_module.lifespan(FastAPI()):
        fake_popen.instances[0].returncode = 0  # Clean exit after SIGINT/SIGTERM.
        await asyncio.sleep(0.1)
        assert len(fake_popen.instances) == 1
    assert fake_popen.instances[0].calls == []


# ------------------------------------------------- shared database plumbing


def _engine_for(path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")

    @event.listens_for(engine.sync_engine, "connect")
    def _fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _point_worker_at(monkeypatch, engine) -> async_sessionmaker[AsyncSession]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(worker_module, "database_engine", engine)
    monkeypatch.setattr(worker_module, "get_session", maker)
    return maker


async def _wait_until(predicate, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while not await predicate():
        assert time.monotonic() < deadline, "condition not reached in time"
        await asyncio.sleep(0.02)


# ------------------------------------------------- table wait and liveness


@pytest.mark.asyncio
async def test_worker_waits_for_tables_then_runs_and_reports_liveness(
    monkeypatch, tmp_path, caplog
) -> None:
    engine = _engine_for(tmp_path / "fresh.db")
    maker = _point_worker_at(monkeypatch, engine)
    monkeypatch.setattr(worker_module, "_TABLE_WAIT_INITIAL_SECONDS", 0.02)
    monkeypatch.setattr(worker_module, "_TABLE_WAIT_MAX_SECONDS", 0.08)
    settings = get_settings()
    monkeypatch.setattr(settings, "ENGINE_JOB_WORKER_POLL_SECONDS", 0.05)
    monkeypatch.setattr(settings, "ENGINE_WORKER_HEARTBEAT_SECONDS", 0.1)
    caplog.set_level(logging.INFO, logger=worker_module.__name__)

    def waits() -> list[str]:
        return [
            record.getMessage()
            for record in caplog.records
            if record.getMessage().startswith("Engine job tables not ready")
        ]

    async def waited_four_times() -> bool:
        return len(waits()) >= 4

    stop = asyncio.Event()
    task = asyncio.create_task(worker_module.run_worker(stop))
    try:
        await _wait_until(waited_four_times)
        assert not task.done()  # a fresh database no longer crashes the worker
        assert [line.rsplit(" in ", 1)[1] for line in waits()[:4]] == [
            "0.02 s",
            "0.04 s",
            "0.08 s",
            "0.08 s",
        ]
        async with engine.begin() as connection:  # migrations "finish"
            await connection.run_sync(Base.metadata.create_all)

        async def one_live_worker() -> bool:
            async with maker() as session:
                return len(await get_live_engine_workers(session)) == 1

        await _wait_until(one_live_worker)
        async with maker() as session:
            first = (await get_live_engine_workers(session))[0]
        await asyncio.sleep(0.3)  # several heartbeats while idle
        async with maker() as session:
            again = (await get_live_engine_workers(session))[0]
        assert again.id == first.id
        assert again.last_seen_at > first.last_seen_at
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=10)
    assert task.exception() is None
    async with maker() as session:  # clean exit removes the row
        assert await get_live_engine_workers(session) == []
    await engine.dispose()


@pytest.mark.asyncio
async def test_live_worker_helper_honours_max_age(db_session, monkeypatch) -> None:
    started = liveness_module._utcnow()
    await record_engine_worker_seen(
        db_session, worker_id="host:1:abcd", pid=1, host="host", started_at=started
    )
    rows = await get_live_engine_workers(db_session, max_age_seconds=45)
    assert [(row.id, row.pid, row.host) for row in rows] == [("host:1:abcd", 1, "host")]

    later = started + timedelta(seconds=46)
    monkeypatch.setattr(liveness_module, "_utcnow", lambda: later)
    assert await get_live_engine_workers(db_session, max_age_seconds=45) == []


# --------------------------------------------------------------- leases

_SCALE = 10.0  # fake seconds per real second, so a 5 s lease lasts 0.5 s


@pytest.fixture
def fast_clock(monkeypatch):
    real_start = engine_jobs_module._utcnow()
    monotonic_start = time.monotonic()

    def now():
        return real_start + timedelta(
            seconds=(time.monotonic() - monotonic_start) * _SCALE
        )

    monkeypatch.setattr(engine_jobs_module, "_utcnow", now)
    return now


async def _submit(maker, key: str, amount: str) -> str:
    async with maker() as session:
        job, reused = await LabService(session).submit_engine_job(
            job_type="FORMULA_ANALYSIS",
            payload=_formula_payload(amount=amount),
            requester="fixture-requester",
            idempotency_key=key,
        )
        assert reused is False
        return job.id


@pytest.mark.asyncio
async def test_running_job_keeps_renewed_lease_and_unrenewed_lease_is_reclaimed(
    monkeypatch, tmp_path, fast_clock
) -> None:
    engine = _engine_for(tmp_path / "leases.db")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = _point_worker_at(monkeypatch, engine)
    settings = get_settings()
    monkeypatch.setattr(settings, "ENGINE_JOB_LEASE_SECONDS", 5)  # 0.5 s real
    monkeypatch.setattr(settings, "ENGINE_JOB_LEASE_RENEW_SECONDS", 0.1)  # real

    def slow_job(job_type, payload, timeout_seconds, contract_version):
        time.sleep(1.2)  # 12 fake seconds: well past the 5 s lease
        return ("SUCCEEDED", {"status": "SUCCEEDED"}, "FIXTURE_OK", {})

    monkeypatch.setattr(worker_module, "_execute_isolated", slow_job)

    renewed_job = await _submit(maker, "renewed", "100")
    claimed_at = fast_clock()
    reaped = 0
    run = asyncio.create_task(worker_module._run_lease("worker-a:1"))
    while not run.done():  # another worker's loop failing expired leases
        async with maker() as session:
            reaped += await LabService(session).fail_expired_engine_jobs()
        await asyncio.sleep(0.05)
    assert run.result() is True
    assert reaped == 0
    assert fast_clock() - claimed_at > timedelta(seconds=10)
    async with maker() as session:
        service = LabService(session)
        snapshot = await service.engine_job_snapshot(renewed_job)
        reasons = [
            event.sanitized_reason
            for event in await service._engine_job_events(renewed_job)
        ]
    assert snapshot["state"] == "SUCCEEDED"
    assert reasons.count("WORKER_LEASE_RENEWED") >= 5
    assert reasons[-1] == "WORKER_RESULT_ACCEPTED"

    # The same lease without renewal (a dead worker) is failed closed.
    lost_job = await _submit(maker, "unrenewed", "150")
    async with maker() as session:
        service = LabService(session)
        lease = await service.claim_next_engine_job(owner="dead-worker:1", lease_seconds=5)
        assert lease is not None and lease.job.id == lost_job
        await service.mark_engine_job_running(
            job_id=lease.job.id, owner=lease.owner, token=lease.token
        )
    await asyncio.sleep(0.7)  # 7 fake seconds
    async with maker() as session:
        service = LabService(session)
        assert await service.fail_expired_engine_jobs() == 1
        snapshot = await service.engine_job_snapshot(lost_job)
    assert snapshot["state"] == "FAILED"
    assert snapshot["result"]["validation_state"] == "FAILED_CLOSED_WORKER_LOST"
    await engine.dispose()


@pytest.mark.asyncio
async def test_renewal_cannot_revive_a_failed_or_finished_job(db_session) -> None:
    service = LabService(db_session)
    job, _ = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="no-revive",
    )
    job_id = job.id  # a rolled-back conflict expires loaded objects
    lease = await service.claim_next_engine_job(owner="w:1", lease_seconds=30)
    assert lease is not None
    await service.mark_engine_job_running(job_id=job_id, owner="w:1", token=lease.token)
    with pytest.raises(engine_jobs_module.EngineJobConflictError):
        await service.renew_engine_job_lease(
            job_id=job_id, owner="w:1", token="wrong-token", lease_seconds=30
        )
    await service.cancel_engine_job(job_id=job_id, requester="fixture-requester", reason="x")
    with pytest.raises(engine_jobs_module.EngineJobConflictError) as caught:
        await service.renew_engine_job_lease(
            job_id=job_id, owner="w:1", token=lease.token, lease_seconds=30
        )
    assert caught.value.code == "ENGINE_JOB_NOT_RUNNING"


@pytest.mark.asyncio
async def test_lost_lease_discards_late_result_without_crashing(
    monkeypatch, tmp_path, fast_clock
) -> None:
    engine = _engine_for(tmp_path / "late.db")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = _point_worker_at(monkeypatch, engine)
    settings = get_settings()
    monkeypatch.setattr(settings, "ENGINE_JOB_LEASE_SECONDS", 5)  # 0.5 s real
    monkeypatch.setattr(settings, "ENGINE_JOB_LEASE_RENEW_SECONDS", 60)  # never

    def slow_job(job_type, payload, timeout_seconds, contract_version):
        time.sleep(1.0)
        return ("SUCCEEDED", {"status": "SUCCEEDED"}, "FIXTURE_OK", {})

    monkeypatch.setattr(worker_module, "_execute_isolated", slow_job)
    job_id = await _submit(maker, "late", "175")
    run = asyncio.create_task(worker_module._run_lease("worker-b:1"))
    while not run.done():
        async with maker() as session:
            await LabService(session).fail_expired_engine_jobs()
        await asyncio.sleep(0.05)
    assert run.result() is True  # the late result is discarded, not raised
    async with maker() as session:
        snapshot = await LabService(session).engine_job_snapshot(job_id)
    assert snapshot["result"]["validation_state"] == "FAILED_CLOSED_WORKER_LOST"
    await engine.dispose()
