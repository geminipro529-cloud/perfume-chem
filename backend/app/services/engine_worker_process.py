"""Start and stop the engine worker subprocess that belongs to an API process."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path

logger = logging.getLogger(__name__)

AUTOSTART_ENV = "PERFUME_ENGINE_WORKER_AUTOSTART"
# Must match app.services.engine_job_worker.PARENT_PIPE_ENV (not imported: that
# module pulls in the database engine and the job executor).
PARENT_PIPE_ENV = "PERFUME_ENGINE_WORKER_PARENT_PIPE"
_DISABLED_VALUES = {"0", "false", "no"}

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_DIR.parent


def engine_worker_autostart_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Autostart is on unless the env var is "0", "false" or "no"."""

    values = os.environ if environ is None else environ
    return values.get(AUTOSTART_ENV, "").strip().lower() not in _DISABLED_VALUES


def start_engine_worker_process() -> subprocess.Popen[bytes]:
    """Launch ``python -m app.services.engine_job_worker`` from ``backend/``.

    Uses the API's own interpreter and environment, with this checkout's
    backend and repository root first on ``PYTHONPATH`` (as run_api_server.py
    did when it owned the worker).  Its stdin is a pipe the worker watches:
    when the API closes it, or exits however it dies (a Windows hard kill
    included), the worker stops and fails its running jobs.
    """

    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(BACKEND_DIR),
            str(REPOSITORY_ROOT),
            environment.get("PYTHONPATH", ""),
        ]
    ).rstrip(os.pathsep)
    environment[PARENT_PIPE_ENV] = "1"
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW
    process = subprocess.Popen(
        [sys.executable, "-m", "app.services.engine_job_worker"],
        cwd=BACKEND_DIR,
        env=environment,
        stdin=subprocess.PIPE,
        creationflags=creation_flags,
    )
    logger.info("Started engine worker process pid=%s", process.pid)
    return process


def stop_engine_worker_process(process: subprocess.Popen[bytes]) -> None:
    """Close the worker's stdin pipe, wait up to 10 s, then terminate and kill.

    Closing the pipe is the stop request; it needs no signal, which Windows
    cannot deliver to a CREATE_NO_WINDOW child.
    """

    if process.stdin is not None:
        with suppress(OSError):
            process.stdin.close()
    if process.poll() is not None:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    logger.info("Stopped engine worker process pid=%s", process.pid)


_SUPERVISE_INTERVAL_SECONDS = 2.0
_RESTART_INITIAL_DELAY_SECONDS = 1.0
_RESTART_MAX_DELAY_SECONDS = 60.0
_HEALTHY_RUN_SECONDS = 60.0


class EngineWorkerSupervisor:
    """Own one worker process for the API's lifetime and replace it if it dies.

    Only a running worker fails expired leases, so a worker that crashed or was
    killed would otherwise leave its job RUNNING forever.  A worker that exits
    with status 0 was asked to stop (SIGINT/SIGTERM) and is not restarted.
    Restarts, and retries of a launch that raised, back off (1 s doubling to
    60 s) until a worker stays up 60 s.
    ``uvicorn --workers N`` starts N API processes and so N engine workers;
    job leases keep that safe.
    """

    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None
        self._started_at = 0.0
        self._restart_delay = _RESTART_INITIAL_DELAY_SECONDS
        self._task: asyncio.Task[None] | None = None
        self._launch_failed = False

    def start(self) -> None:
        self._try_launch()
        self._task = asyncio.create_task(self._supervise())

    def _launch(self) -> None:
        self.process = start_engine_worker_process()
        self._started_at = time.monotonic()

    def _try_launch(self) -> None:
        try:
            self._launch()
        except Exception:
            logger.exception(
                "Could not start the engine worker; retrying in %g s",
                self._restart_delay,
            )
            self.process = None
            self._launch_failed = True
        else:
            self._launch_failed = False

    async def _supervise(self) -> None:
        while True:
            await asyncio.sleep(_SUPERVISE_INTERVAL_SECONDS)
            process = self.process
            if process is None:
                if not self._launch_failed:
                    continue
            else:
                returncode = process.poll()
                if returncode is None:
                    if time.monotonic() - self._started_at >= _HEALTHY_RUN_SECONDS:
                        self._restart_delay = _RESTART_INITIAL_DELAY_SECONDS
                    continue
                if returncode == 0:
                    logger.info(
                        "Engine worker pid=%s stopped; not restarting", process.pid
                    )
                    self.process = None
                    continue
                logger.warning(
                    "Engine worker pid=%s exited with status %s; restarting in %g s",
                    process.pid,
                    returncode,
                    self._restart_delay,
                )
            await asyncio.sleep(self._restart_delay)
            self._restart_delay = min(
                self._restart_delay * 2, _RESTART_MAX_DELAY_SECONDS
            )
            self._try_launch()

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self.process is not None:
            await asyncio.to_thread(stop_engine_worker_process, self.process)


__all__ = [
    "AUTOSTART_ENV",
    "PARENT_PIPE_ENV",
    "EngineWorkerSupervisor",
    "engine_worker_autostart_enabled",
    "start_engine_worker_process",
    "stop_engine_worker_process",
]
