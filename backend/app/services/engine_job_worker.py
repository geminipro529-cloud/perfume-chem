"""Standalone database-leased worker for Checkpoint-2 engine jobs."""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import secrets
import signal
import socket
import time
from contextlib import suppress
from datetime import datetime, timezone
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from typing import Any, cast

from sqlalchemy import inspect
from sqlalchemy.engine import Connection as SyncConnection
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db_session import engine as database_engine
from app.db_session import get_session
from app.models.lab_engine_jobs import CP2_ENGINE_JOB_TABLE_NAMES
from app.services.engine_job_executor import execute_registered_engine_job
from app.services.engine_jobs import EngineJobConflictError, EngineJobLease
from app.services.engine_worker_liveness import (
    record_engine_worker_seen,
    remove_engine_worker,
)
from app.services.lab_service import LabService

logger = logging.getLogger(__name__)


class EngineJobChildTimeoutError(TimeoutError):
    """The isolated job process exceeded its server-owned hard deadline."""


class EngineJobChildFailureError(RuntimeError):
    """The isolated job process failed without exposing sensitive details."""


def _child_execute(
    connection: Connection,
    job_type: str,
    payload: dict[str, Any],
    contract_version: str,
) -> None:
    """Execute one closed-registry command in a disposable child process."""

    try:
        result = execute_registered_engine_job(
            job_type,
            payload,
            contract_version=contract_version,
        )
        connection.send(("COMPLETED", result))
    except BaseException as error:
        connection.send(("FAILED", {"exception_class": type(error).__name__}))
    finally:
        connection.close()


def _terminate_child(process: BaseProcess) -> None:
    if not process.is_alive():
        process.join(timeout=1)
        return
    process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()
        process.join(timeout=5)


def _execute_isolated(
    job_type: str,
    payload: dict[str, Any],
    timeout_seconds: int,
    contract_version: str = "perfume-chem-engine-job-contract-v1",
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    """Run one job with a killable, wall-clock hard timeout."""

    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(
        target=_child_execute,
        args=(sending, job_type, payload, contract_version),
        name=f"perfume-engine-job-{job_type.lower()}",
        daemon=False,
    )
    try:
        process.start()
        sending.close()
        if not receiving.poll(float(timeout_seconds)):
            _terminate_child(process)
            raise EngineJobChildTimeoutError("ENGINE_JOB_TIMEOUT")
        try:
            outcome, value = receiving.recv()
        except EOFError as error:
            raise EngineJobChildFailureError("ENGINE_JOB_CHILD_NO_RECEIPT") from error
        process.join(timeout=5)
        if process.is_alive():
            _terminate_child(process)
        if outcome != "COMPLETED":
            exception_class = str(dict(value).get("exception_class", "Unknown"))
            raise EngineJobChildFailureError(exception_class)
        return cast(tuple[str, dict[str, Any], str, dict[str, Any]], value)
    finally:
        receiving.close()
        sending.close()
        _terminate_child(process)


_REQUIRED_TABLE_NAMES = frozenset({*CP2_ENGINE_JOB_TABLE_NAMES, "lab_engine_workers"})
_TABLE_WAIT_INITIAL_SECONDS = 1.0
_TABLE_WAIT_MAX_SECONDS = 30.0


def _missing_table_names(connection: SyncConnection) -> set[str]:
    return set(_REQUIRED_TABLE_NAMES) - set(inspect(connection).get_table_names())


async def _missing_engine_job_tables() -> set[str]:
    async with database_engine.connect() as connection:
        missing: set[str] = await connection.run_sync(_missing_table_names)
        return missing


async def wait_for_engine_job_tables(
    stop: asyncio.Event,
    *,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
) -> bool:
    """Wait (never create) until the API's migrations have made the job tables.

    Retries with a delay doubling from ``initial_delay`` to ``max_delay`` and
    logs one line per wait.  Returns False if asked to stop first.
    """

    delay = initial_delay
    while not stop.is_set():
        try:
            missing = await _missing_engine_job_tables()
        except OperationalError as error:
            missing = {f"database unavailable ({type(error).__name__})"}
        if not missing:
            return True
        logger.info(
            "Engine job tables not ready (missing: %s); retrying in %g s",
            ", ".join(sorted(missing)),
            delay,
        )
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=delay)
        delay = min(delay * 2, max_delay)
    return False


async def _renew_lease_until(
    done: asyncio.Event,
    lease: EngineJobLease,
    *,
    lease_seconds: int,
    renew_seconds: float,
) -> None:
    """Renew the job's lease every ``renew_seconds`` until ``done`` is set.

    Runs on the event loop while the engine work runs in a thread, with its own
    session.  The caller sets ``done`` and awaits this task before completing
    the job, so a renewal never races this worker's own completion.
    """

    while True:
        with suppress(TimeoutError):
            await asyncio.wait_for(done.wait(), timeout=renew_seconds)
        if done.is_set():
            return
        try:
            async with get_session() as session:
                await LabService(session).renew_engine_job_lease(
                    job_id=lease.job.id,
                    owner=lease.owner,
                    token=lease.token,
                    lease_seconds=lease_seconds,
                )
        except EngineJobConflictError as error:
            # Cancelled, completed or failed closed meanwhile: nothing to keep.
            logger.warning(
                "Stopped renewing lease for engine job %s: %s",
                lease.job.id,
                error.code,
            )
            return
        except Exception:
            logger.exception(
                "Lease renewal for engine job %s failed; retrying", lease.job.id
            )


async def _execute_lease(
    lease: EngineJobLease,
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    try:
        return await asyncio.to_thread(
            _execute_isolated,
            lease.job.job_type,
            dict(lease.job.normalized_payload_json),
            lease.job.timeout_seconds,
            lease.job.contract_version,
        )
    except EngineJobChildTimeoutError:
        return (
            "FAILED",
            {
                "status": "FAILED",
                "code": "ENGINE_JOB_TIMEOUT",
                "formula_action": "NO_CHANGE",
            },
            "ENGINE_JOB_TIMEOUT",
            {"timeout_seconds": lease.job.timeout_seconds},
        )
    except Exception as error:  # sanitized at the persistence boundary
        return (
            "FAILED",
            {
                "status": "FAILED",
                "code": "ENGINE_JOB_EXECUTION_FAILED",
                "formula_action": "NO_CHANGE",
            },
            "ENGINE_JOB_EXECUTION_FAILED",
            {"exception_class": type(error).__name__},
        )


async def _run_lease(owner: str) -> bool:
    settings = get_settings()
    lease_seconds = settings.ENGINE_JOB_LEASE_SECONDS
    async with get_session() as session:
        service = LabService(session)
        lease = await service.claim_next_engine_job(
            owner=owner, lease_seconds=lease_seconds
        )
        if lease is None:
            return False
        # Read once: a rejected completion rolls the session back and expires
        # ``lease.job``, and a lazy reload outside a greenlet would raise.
        job_id = lease.job.id
        await service.mark_engine_job_running(
            job_id=job_id, owner=lease.owner, token=lease.token
        )
        execution_done = asyncio.Event()
        renewal = asyncio.create_task(
            _renew_lease_until(
                execution_done,
                lease,
                lease_seconds=lease_seconds,
                renew_seconds=settings.ENGINE_JOB_LEASE_RENEW_SECONDS,
            )
        )
        try:
            terminal_state, result, validation_state, diagnostics = (
                await _execute_lease(lease)
            )
        finally:
            execution_done.set()
            await renewal
        try:
            await service.complete_engine_job(
                job_id=job_id,
                owner=lease.owner,
                token=lease.token,
                terminal_state=terminal_state,
                result=result,
                validation_state=validation_state,
                diagnostics=diagnostics,
            )
        except EngineJobConflictError:
            # Cancellation or lease expiry wins.  A late result is intentionally
            # discarded and never attached to the immutable job.
            logger.info("Discarded late result for engine job %s", job_id)
        return True


async def _record_liveness(worker_id: str, started_at: datetime) -> None:
    try:
        async with get_session() as session:
            await record_engine_worker_seen(
                session,
                worker_id=worker_id,
                pid=os.getpid(),
                host=socket.gethostname(),
                started_at=started_at,
            )
    except Exception:
        logger.exception("Could not record engine worker liveness; will retry")


async def run_worker(stop: asyncio.Event | None = None) -> None:
    """Poll for jobs until SIGINT/SIGTERM (or ``stop``, for callers that own it)."""

    settings = get_settings()
    concurrency = settings.ENGINE_JOB_WORKER_CONCURRENCY
    poll_seconds = settings.ENGINE_JOB_WORKER_POLL_SECONDS
    heartbeat_seconds = settings.ENGINE_WORKER_HEARTBEAT_SECONDS
    owner_prefix = f"{socket.gethostname()}:{os.getpid()}"
    worker_id = f"{owner_prefix}:{secrets.token_hex(4)}"
    if stop is None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGINT, signal.SIGTERM):
            with suppress(NotImplementedError):
                loop.add_signal_handler(signum, stop.set)

    if not await wait_for_engine_job_tables(
        stop,
        initial_delay=_TABLE_WAIT_INITIAL_SECONDS,
        max_delay=_TABLE_WAIT_MAX_SECONDS,
    ):
        return
    started_at = datetime.now(timezone.utc)
    await _record_liveness(worker_id, started_at)
    last_seen = time.monotonic()

    active: set[asyncio.Task[bool]] = set()
    logger.info("Engine worker %s started with concurrency=%s", worker_id, concurrency)
    try:
        while not stop.is_set():
            if time.monotonic() - last_seen >= heartbeat_seconds:
                await _record_liveness(worker_id, started_at)
                last_seen = time.monotonic()
            async with get_session() as session:
                await LabService(session).fail_expired_engine_jobs()
            while len(active) < concurrency and not stop.is_set():
                slot = len(active) + 1
                task = asyncio.create_task(_run_lease(f"{owner_prefix}:{slot}"))
                active.add(task)
                await asyncio.sleep(0)
                if task.done() and not task.result():
                    active.remove(task)
                    break
            if active:
                done, pending = await asyncio.wait(
                    active,
                    timeout=poll_seconds,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                active = set(pending)
                for task in done:
                    with suppress(Exception):
                        task.result()
            else:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=poll_seconds)
                except TimeoutError:
                    pass

        if active:
            await asyncio.gather(*active, return_exceptions=True)
    finally:
        with suppress(Exception):
            async with get_session() as session:
                await remove_engine_worker(session, worker_id=worker_id)
        logger.info("Engine worker %s stopped", worker_id)



def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()


__all__ = ["main", "run_worker"]
