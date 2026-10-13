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
            "devices on the network reach the app; they must sign in with "
            "the lab password unless --no-login is given."
        ),
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help=(
            f"Bind {ALL_INTERFACES_HOST} so other devices on the network can "
            "open the app. Other devices sign in once with the lab password "
            "(LAB_PASSWORD, else data/user/lab_password.txt, created on the "
            "first network start); this PC itself never needs it."
        ),
    )
    parser.add_argument(
        "--no-login",
        action="store_true",
        help=(
            "With --lan/--host: turn the password off, so anyone on the "
            "network can read, change and delete the lab data."
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
    if args.host is not None:
        host = args.host
    elif args.lan:
        host = ALL_INTERFACES_HOST
    else:
        host = LOOPBACK_HOST
    if not _is_loopback(host) and args.no_login:
        print(
            f"WARNING: the API will listen on {host}:8000, reachable from other "
            "devices on the network, and --no-login turned the password off: "
            "anyone who can reach this PC can open, change and delete the lab "
            "data (formulas, stock and bottle records). Drop --no-login to "
            f"require the lab password, or run without --lan/--host to keep it "
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
    # The app answers only Host names that point at this PC; tell it the bind
    # address so --lan / --host also answer the address other devices use.
    os.environ["API_BIND_HOST"] = host
    if args.no_login:
        os.environ["LAB_LOGIN"] = "false"
    elif not _is_loopback(host):
        os.environ["LAB_LOGIN"] = "true"
        _announce_password(host)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=8000,
        reload=args.reload,
        log_level="info",
        app_dir=str(backend_dir),
    )


def _announce_password(host: str) -> None:
    from app.core.config import Settings
    from app.core.login import resolve_password

    settings = Settings()
    password, path, created = resolve_password(
        settings.LAB_PASSWORD, settings.LAB_PASSWORD_FILE
    )
    where = "set in LAB_PASSWORD" if path is None else f"kept in {path}"
    note = "New lab password" if created else "Lab password"
    print(
        f"{note} for other devices: {password} ({where}). Open "
        f"http://<this PC's address>:8000/app on the phone and sign in once; "
        "on this PC the app never asks for it.",
        file=sys.stderr,
        flush=True,
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
