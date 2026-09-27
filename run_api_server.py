#!/usr/bin/env python3
"""Run the backend API from the repository root."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-engine-worker",
        action="store_true",
        help="Run only the API process (the durable worker is enabled by default).",
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parent
    backend_dir = repository_root / "backend"
    worker: subprocess.Popen | None = None
    if not args.no_engine_worker:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            [
                str(backend_dir),
                str(repository_root),
                environment.get("PYTHONPATH", ""),
            ]
        ).rstrip(os.pathsep)
        creation_flags = (
            subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        worker = subprocess.Popen(
            [sys.executable, "-m", "app.services.engine_job_worker"],
            cwd=backend_dir,
            env=environment,
            creationflags=creation_flags,
        )
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            app_dir=str(backend_dir),
        )
    finally:
        if worker is not None and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)


if __name__ == "__main__":
    main()
