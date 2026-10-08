#!/usr/bin/env python3
"""Run the backend API from the repository root."""

from __future__ import annotations

import argparse
import os
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
        help=(
            "Run only the API process: sets PERFUME_ENGINE_WORKER_AUTOSTART=0 so "
            "the app does not start its engine worker (enabled by default)."
        ),
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
    parser.add_argument(
        "--restore",
        metavar="BACKUP",
        help=(
            "Restore the lab database from a backup (its file name as the app "
            "shows it, or a path to the backup file) and exit without starting "
            "the server. Stop the app first."
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

    if args.restore is not None:
        _restore(args.restore)
        return

    # Import Uvicorn only after pinning this checkout.  This also keeps any
    # import-time discovery performed by Uvicorn on the same application path.
    import uvicorn

    # The app's lifespan starts and stops the engine worker (see
    # backend/app/services/engine_worker_process.py), so this launcher no longer
    # spawns its own: that would give two workers.  --no-engine-worker keeps its
    # meaning by switching the app's autostart off.
    if args.no_engine_worker:
        os.environ["PERFUME_ENGINE_WORKER_AUTOSTART"] = "0"
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=8000,
        reload=args.reload,
        log_level="info",
        app_dir=str(backend_dir),
    )


def _restore(backup: str) -> None:
    from app.core.config import Settings
    from app.services.restore_command import restore_from_backup

    # Port 8000 is the port uvicorn.run serves the app on in main().
    exit_code = restore_from_backup(
        backup, database_url=Settings().DATABASE_URL, port=8000
    )
    if exit_code:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
