"""Start and stop the engine worker subprocess that belongs to an API process."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

logger = logging.getLogger(__name__)

AUTOSTART_ENV = "PERFUME_ENGINE_WORKER_AUTOSTART"
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
    did when it owned the worker).
    """

    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(BACKEND_DIR),
            str(REPOSITORY_ROOT),
            environment.get("PYTHONPATH", ""),
        ]
    ).rstrip(os.pathsep)
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        [sys.executable, "-m", "app.services.engine_job_worker"],
        cwd=BACKEND_DIR,
        env=environment,
        creationflags=creation_flags,
    )
    logger.info("Started engine worker process pid=%s", process.pid)
    return process


def stop_engine_worker_process(process: subprocess.Popen[bytes]) -> None:
    """Terminate, wait up to 10 s, then kill."""

    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    logger.info("Stopped engine worker process pid=%s", process.pid)


__all__ = [
    "AUTOSTART_ENV",
    "engine_worker_autostart_enabled",
    "start_engine_worker_process",
    "stop_engine_worker_process",
]
