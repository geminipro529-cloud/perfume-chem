"""Stopped-server restore behind ``python run_api_server.py --restore <backup>``.

The running app only validates and stages a restore; replacing the live
database happens here, in a process of its own, after checking that nothing
else is using the database.
"""

from __future__ import annotations

import socket
import sqlite3
import sys
from pathlib import Path

from sqlalchemy.engine import URL

from app.services.backup_service import (
    RestoreSafetyError,
    backup_service_for_database_url,
)

RESTORE_COMMAND = "python run_api_server.py --restore"


def restore_from_backup(backup: str, *, database_url: str | URL, port: int) -> int:
    """Restore the app database from ``backup``; return the process exit code.

    ``backup`` is a backup file name as the app shows it (looked up in the
    managed backup folder) or a path to the backup file.  ``port`` is the
    app's port: anything answering on it at 127.0.0.1 means the app is running.
    """

    try:
        service = backup_service_for_database_url(database_url)
    except RestoreSafetyError as exc:
        return _refuse(str(exc))
    database = service.database_path
    if not database.is_file():
        return _refuse(f"There is no database to restore into at {database}.")

    snapshot = _backup_path(backup, service.backup_directory)
    try:
        validation = service.validate_restore(snapshot)
    except RestoreSafetyError as exc:
        return _refuse(f"{exc} ({service.backup_directory}).")
    if not validation.valid:
        return _refuse(
            f"Backup {snapshot} cannot be restored: " + "; ".join(validation.errors) + "."
        )

    in_use = _database_in_use(database, port)
    if in_use:
        return _refuse(in_use + " Nothing was changed.")

    staged = service.stage_restore(snapshot)
    try:
        applied = service.apply_staged_restore(staged, maintenance_mode=True)
    except (OSError, sqlite3.Error, RestoreSafetyError) as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        return 1
    finally:
        staged.staged_path.unlink(missing_ok=True)

    pre_restore = applied.pre_restore_backup.snapshot_path
    print(f"Restored {database} from {validation.snapshot_path.name}.")
    print(f"The database as it was before this restore is saved at: {pre_restore}")
    print(f"To undo, run: {RESTORE_COMMAND} {pre_restore.name}")
    return 0


def _backup_path(backup: str, backup_directory: Path) -> Path:
    path = Path(backup).expanduser()
    if path.name != backup:  # a path, not a bare backup name
        return path
    return backup_directory / (backup if path.suffix else f"{backup}.sqlite")


def _database_in_use(database: Path, port: int) -> str | None:
    # An idle running app holds no SQLite lock, so a lock probe alone cannot
    # see it; its listening port can.  The lock probe then catches any other
    # program in the middle of reading or writing the database.
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return (
                f"The app is still running (it answers on 127.0.0.1:{port}). "
                "Stop it, then run this command again."
            )
    except OSError:
        pass
    connection = sqlite3.connect(database, timeout=0)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        connection.rollback()
    except sqlite3.OperationalError:
        return (
            f"The database {database} is in use by another program. "
            "Close it, then run this command again."
        )
    finally:
        connection.close()
    return None


def _refuse(message: str) -> int:
    print(f"Restore refused: {message}", file=sys.stderr)
    return 1
