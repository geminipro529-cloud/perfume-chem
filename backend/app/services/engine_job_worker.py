"""Standalone database-leased worker for Checkpoint-2 engine jobs."""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import signal
import socket
from contextlib import suppress
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from typing import Any, cast

from app.core.config import get_settings
from app.db_session import get_session
from app.services.engine_job_executor import execute_registered_engine_job
from app.services.engine_jobs import EngineJobConflictError
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


async def _run_lease(owner: str) -> bool:
    async with get_session() as session:
        service = LabService(session)
        lease = await service.claim_next_engine_job(owner=owner, lease_seconds=3600)
        if lease is None:
            return False
        await service.mark_engine_job_running(
            job_id=lease.job.id, owner=lease.owner, token=lease.token
        )
        try:
            terminal_state, result, validation_state, diagnostics = (
                await asyncio.to_thread(
                    _execute_isolated,
                    lease.job.job_type,
                    dict(lease.job.normalized_payload_json),
                    lease.job.timeout_seconds,
                    lease.job.contract_version,
                )
            )
        except EngineJobChildTimeoutError:
            terminal_state = "FAILED"
            validation_state = "ENGINE_JOB_TIMEOUT"
            result = {
                "status": "FAILED",
                "code": "ENGINE_JOB_TIMEOUT",
                "formula_action": "NO_CHANGE",
            }
            diagnostics = {"timeout_seconds": lease.job.timeout_seconds}
        except Exception as error:  # sanitized at the persistence boundary
            terminal_state = "FAILED"
            validation_state = "ENGINE_JOB_EXECUTION_FAILED"
            result = {
                "status": "FAILED",
                "code": "ENGINE_JOB_EXECUTION_FAILED",
                "formula_action": "NO_CHANGE",
            }
            diagnostics = {"exception_class": type(error).__name__}
        try:
            await service.complete_engine_job(
                job_id=lease.job.id,
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
            logger.info("Discarded late result for engine job %s", lease.job.id)
        return True


async def run_worker() -> None:
    settings = get_settings()
    concurrency = settings.ENGINE_JOB_WORKER_CONCURRENCY
    poll_seconds = settings.ENGINE_JOB_WORKER_POLL_SECONDS
    owner_prefix = f"{socket.gethostname()}:{os.getpid()}"
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(signum, stop.set)

    active: set[asyncio.Task[bool]] = set()
    logger.info("Engine worker started with concurrency=%s", concurrency)
    while not stop.is_set():
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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()


__all__ = ["main", "run_worker"]
