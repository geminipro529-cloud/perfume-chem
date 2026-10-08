#!/usr/bin/env python3
"""Run the backend API from the repository root."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="API bind address; use 127.0.0.1 for a loopback-only desktop session.",
    )
    parser.add_argument(
        "--no-engine-worker",
        action="store_true",
        help="Run only the API process (the durable worker is enabled by default).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help=(
            "Enable Uvicorn source auto-reload for interactive development. "
            "The normal desktop launcher stays single-process so stopping it "
            "cannot leave an orphaned listener behind."
        ),
    )
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parent
    backend_dir = repository_root / "backend"
    # Pin this checkout ahead of any inherited PYTHONPATH entries.  Uvicorn's
    # reload child must import the same backend that serves the static assets;
    # otherwise another checkout's ``app`` package can remain in memory.
    runtime_paths = (str(backend_dir), str(repository_root))
    for runtime_path in reversed(runtime_paths):
        if runtime_path in sys.path:
            sys.path.remove(runtime_path)
        sys.path.insert(0, runtime_path)
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [*runtime_paths, os.environ.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    # Import Uvicorn only after pinning this checkout.  This also keeps any
    # import-time discovery performed by Uvicorn on the same application path.
    import uvicorn

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
            host=args.host,
            port=8000,
            reload=args.reload,
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
