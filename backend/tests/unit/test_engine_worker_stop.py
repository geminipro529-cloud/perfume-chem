"""Engine worker loop: parent pipe, graceful stop, loop-error exit, idle polling."""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import signal
import subprocess
import sys
import threading
import time

import pytest

from app.core.config import get_settings
from app.models.base import Base
from app.services import engine_job_worker as worker_module
from app.services import lab_service as lab_service_module
from app.services.engine_worker_liveness import get_live_engine_workers
from app.services.engine_worker_process import BACKEND_DIR, REPOSITORY_ROOT
from app.services.lab_service import LabService
from tests.unit import _engine_worker_sleeper
from tests.unit.test_engine_worker_lifecycle import (
    _engine_for,
    _point_worker_at,
    _submit,
    _wait_until,
)


@pytest.fixture(autouse=True)
def fresh_write_lock(monkeypatch):
    monkeypatch.setattr(lab_service_module, "_LAB_WRITE_LOCK", asyncio.Lock())


@pytest.fixture
def fast_loop(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ENGINE_JOB_WORKER_POLL_SECONDS", 0.05)
    monkeypatch.setattr(settings, "ENGINE_WORKER_HEARTBEAT_SECONDS", 60.0)


async def _ready_database(monkeypatch, path):
    engine = _engine_for(path)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, _point_worker_at(monkeypatch, engine)


# ------------------------------------------------------------ parent pipe


def _start_worker_process(tmp_path, *, parent_pipe: bool):
    environment = {
        key: value
        for key, value in os.environ.items()
        if key != "PERFUME_ENGINE_WORKER_PARENT_PIPE"
    }
    environment["PYTHONPATH"] = os.pathsep.join([str(BACKEND_DIR), str(REPOSITORY_ROOT)])
    # No tables: the worker sits in its wait-for-migrations loop.
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{(tmp_path / 'empty.db').as_posix()}"
    if parent_pipe:
        environment["PERFUME_ENGINE_WORKER_PARENT_PIPE"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-m", "app.services.engine_job_worker"],
        cwd=BACKEND_DIR,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    waiting = threading.Event()

    def read_log() -> None:
        assert process.stderr is not None
        for line in process.stderr:
            if b"Engine job tables not ready" in line:
                waiting.set()

    threading.Thread(target=read_log, daemon=True).start()
    return process, waiting


@pytest.mark.parametrize("parent_pipe", [True, False])
def test_parent_pipe_eof_stops_only_a_worker_started_with_the_flag(
    tmp_path, parent_pipe
) -> None:
    process, waiting = _start_worker_process(tmp_path, parent_pipe=parent_pipe)
    try:
        assert waiting.wait(timeout=60), "worker did not start"
        assert process.stdin is not None
        process.stdin.close()  # what the API's exit (or its stop()) does
        if parent_pipe:
            assert process.wait(timeout=10) == 0
        else:
            with pytest.raises(subprocess.TimeoutExpired):
                process.wait(timeout=3)
            process.send_signal(signal.SIGTERM)
            assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


_SPAWN_WHILE_WATCHING = """
import multiprocessing, sys, threading
from app.services import engine_job_worker as worker_module

def answer(connection):
    connection.send("ok")

if __name__ == "__main__":
    worker_module._watch_parent_pipe(sys.stdin.fileno(), lambda: None)
    threading.Event().wait(0.5)  # let the watcher reach its pipe wait
    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    child = context.Process(target=answer, args=(sending,), daemon=True)
    child.start()
    sending.close()
    print("ANSWERED" if receiving.poll(20) and receiving.recv() == "ok" else "SILENT", flush=True)
"""


def test_a_job_child_starts_while_the_parent_pipe_is_watched(tmp_path) -> None:
    # The API keeps the worker's stdin pipe open; the job child inherits it.
    script = tmp_path / "spawn_while_watching.py"
    script.write_text(_SPAWN_WHILE_WATCHING, encoding="utf-8")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join([str(BACKEND_DIR), str(REPOSITORY_ROOT)])
    process = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=BACKEND_DIR,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    output: list[bytes] = []
    reader = threading.Thread(
        target=lambda: output.append(process.stdout.readline()), daemon=True
    )
    reader.start()
    try:
        reader.join(timeout=60)
        assert [line.strip() for line in output] == [b"ANSWERED"]
    finally:
        process.kill()
        process.wait(timeout=10)


# ---------------------------------------------------------- graceful stop


@pytest.mark.asyncio
async def test_stop_terminates_the_job_child_and_fails_the_job_as_stopped(
    monkeypatch, tmp_path, fast_loop
) -> None:
    engine, maker = await _ready_database(monkeypatch, tmp_path / "stop.db")
    monkeypatch.setattr(worker_module, "_child_execute", _engine_worker_sleeper.sleep_child)
    job_id = await _submit(maker, "stopped", "125")

    stop = asyncio.Event()
    run = asyncio.create_task(worker_module.run_worker(stop))
    children: list[multiprocessing.process.BaseProcess] = []
    try:

        async def running_with_child() -> bool:
            children[:] = multiprocessing.active_children()
            async with maker() as session:
                state = (await LabService(session).engine_job_snapshot(job_id))["state"]
            return state == "RUNNING" and len(children) == 1

        await _wait_until(running_with_child, timeout=30)
        child = children[0]
        stop.set()
        await asyncio.wait_for(run, timeout=15)
        assert run.exception() is None
        assert not child.is_alive()
        assert child.exitcode == -signal.SIGTERM
        assert multiprocessing.active_children() == []
        async with maker() as session:
            snapshot = await LabService(session).engine_job_snapshot(job_id)
            assert await get_live_engine_workers(session) == []
        assert snapshot["state"] == "FAILED"
        assert snapshot["result"]["validation_state"] == "FAILED_CLOSED_WORKER_STOPPED"
        assert snapshot["result"]["result"]["code"] == "FAILED_CLOSED_WORKER_STOPPED"
        assert "restarted or shut down" in snapshot["result"]["result"]["message"]
    finally:
        for leftover in multiprocessing.active_children():
            leftover.kill()
            leftover.join(timeout=5)
        if not run.done():
            run.cancel()
        await engine.dispose()


# -------------------------------------------------------- loop errors


class _ExitedError(Exception):
    pass


def _fail_expiry_for(monkeypatch, failing_calls: set[int]) -> list[int]:
    calls: list[int] = []
    original = LabService.fail_expired_engine_jobs

    async def flaky(self):
        calls.append(len(calls) + 1)
        if len(calls) in failing_calls:
            raise RuntimeError("fixture: database briefly unavailable")
        return await original(self)

    monkeypatch.setattr(LabService, "fail_expired_engine_jobs", flaky)
    return calls


def _record_exit(monkeypatch) -> list[int]:
    codes: list[int] = []

    def fake_exit(code: int):
        codes.append(code)
        raise _ExitedError(code)

    monkeypatch.setattr(worker_module, "_exit_process", fake_exit, raising=False)
    return codes


@pytest.mark.asyncio
async def test_one_maintenance_error_does_not_end_the_loop(
    monkeypatch, tmp_path, fast_loop
) -> None:
    engine, _maker = await _ready_database(monkeypatch, tmp_path / "flaky.db")
    calls = _fail_expiry_for(monkeypatch, {2, 4, 5, 6, 7})  # never 5 in a row
    codes = _record_exit(monkeypatch)
    stop = asyncio.Event()
    run = asyncio.create_task(worker_module.run_worker(stop))
    try:

        async def ran_ten_iterations() -> bool:
            assert not run.done(), run
            return len(calls) >= 10

        await _wait_until(ran_ten_iterations)
    finally:
        stop.set()
        await asyncio.wait_for(run, timeout=10)
        await engine.dispose()
    assert run.exception() is None
    assert codes == []


@pytest.mark.asyncio
async def test_five_failing_iterations_in_a_row_exit_non_zero(
    monkeypatch, tmp_path, fast_loop
) -> None:
    engine, _maker = await _ready_database(monkeypatch, tmp_path / "down.db")
    calls = _fail_expiry_for(monkeypatch, set(range(1, 100)))
    codes = _record_exit(monkeypatch)
    started = time.monotonic()
    try:
        with pytest.raises(_ExitedError):
            await asyncio.wait_for(worker_module.run_worker(asyncio.Event()), timeout=10)
    finally:
        await engine.dispose()
    assert codes == [1]
    assert calls == [1, 2, 3, 4, 5]
    assert time.monotonic() - started < 5


# ---------------------------------------------------------- idle polling


@pytest.mark.asyncio
async def test_an_idle_worker_claims_once_per_poll_interval(monkeypatch, tmp_path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ENGINE_JOB_WORKER_POLL_SECONDS", 0.2)
    monkeypatch.setattr(settings, "ENGINE_WORKER_HEARTBEAT_SECONDS", 60.0)
    monkeypatch.setattr(settings, "ENGINE_JOB_WORKER_CONCURRENCY", 2)
    engine, _maker = await _ready_database(monkeypatch, tmp_path / "idle.db")
    claims: list[float] = []

    async def empty_queue(owner: str) -> bool:
        claims.append(time.monotonic())
        await asyncio.sleep(0.001)  # a real claim takes several event-loop turns
        return False

    monkeypatch.setattr(worker_module, "_run_lease", empty_queue)
    stop = asyncio.Event()
    run = asyncio.create_task(worker_module.run_worker(stop))
    try:
        await asyncio.sleep(1.0)
    finally:
        stop.set()
        await asyncio.wait_for(run, timeout=10)
        await engine.dispose()
    assert run.exception() is None
    # At most 6 claim rounds of 2 claims in 1 s at a 0.2 s poll; a worker that
    # claims again as soon as the queue comes back empty makes hundreds.
    assert 0 < len(claims) <= 12, len(claims)
