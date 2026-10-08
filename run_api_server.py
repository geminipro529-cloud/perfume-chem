#!/usr/bin/env python3
"""Run the backend API from the repository root."""

from __future__ import annotations

import argparse
import ipaddress
import os
import sys
from pathlib import Path

LOOPBACK_HOST = "127.0.0.1"
ALL_INTERFACES_HOST = "0.0.0.0"


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        default=None,
        help=(
            f"API bind address (default {LOOPBACK_HOST}: only this PC can open "
            "the app). Overrides --lan. Any non-loopback address lets other "
            "devices on the network reach the lab data with no login."
        ),
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help=(
            f"Bind {ALL_INTERFACES_HOST} so other devices on the network can "
            "open the app. There is no login: anyone on the network can read, "
            "change and delete the lab data."
        ),
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
    args = parser.parse_args()
    if args.host is not None:
        host = args.host
    elif args.lan:
        host = ALL_INTERFACES_HOST
    else:
        host = LOOPBACK_HOST
    if not _is_loopback(host):
        print(
            f"WARNING: the API will listen on {host}:8000, reachable from other "
            "devices on the network. There is no login: anyone who can reach "
            "this PC can open, change and delete the lab data (formulas, "
            "stock and bottle records). Run without --lan/--host to keep it "
            f"on this PC only ({LOOPBACK_HOST}).",
            file=sys.stderr,
            flush=True,
        )
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

    # The app's lifespan starts and stops the engine worker (see
    # backend/app/services/engine_worker_process.py), so this launcher no longer
    # spawns its own: that would give two workers.  --no-engine-worker keeps its
    # meaning by switching the app's autostart off.
    if args.no_engine_worker:
        os.environ["PERFUME_ENGINE_WORKER_AUTOSTART"] = "0"
    uvicorn.run(
        "app.main:app",
        host=host,
        port=8000,
        reload=args.reload,
        log_level="info",
        app_dir=str(backend_dir),
    )


if __name__ == "__main__":
    main()
