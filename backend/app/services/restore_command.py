"""Stopped-server restore behind ``python run_api_server.py --restore <backup>``.

The running app only validates and stages a restore; replacing the live
database happens here, in a process of its own, after checking that nothing
else is using the database: the app's lock file (see ``app_lock``) first,
then its port and a SQLite lock probe.
"""

from __future__ import annotations

import socket
import sqlite3
import sys
from pathlib import Path
from typing import TextIO

from engine.user_records import ADDITION_LOG_NAME, BASKET_LOG_NAME, COMPLETION_LOG_NAME
from sqlalchemy.engine import URL

from app.services import app_lock
from app.services.backup_service import (
    RECORDS_PREDATE_BACKUP,
    AppliedRestore,
    BackupArtifact,
    BackupService,
    RestoreAfterSafetyCopyError,
    RestoreSafetyError,
    StagedRestore,
    backup_service_for_database_url,
)

RESTORE_COMMAND = "python run_api_server.py --restore"
# The stock records in plain words, by standard file name.
RECORD_LABELS = {
    ADDITION_LOG_NAME: "stock you added",
    COMPLETION_LOG_NAME: "stock details you completed",
    BASKET_LOG_NAME: "basket choices",
}


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

    snapshot = _backup_path(backup, service.backup_directory)
    try:
        validation = service.validate_restore(snapshot)
    except RestoreSafetyError as exc:
        return _refuse(f"{exc} ({service.backup_directory}).")
    if not validation.valid:
        return _refuse(
            f"Backup {snapshot} cannot be restored: " + "; ".join(validation.errors) + "."
        )

    # The running app holds this lock whatever host or port it serves on.
    lock_path = app_lock.lock_path_for(database)
    try:
        held = app_lock.try_acquire(lock_path)
    except OSError as exc:
        return _refuse(f"Cannot open the lock file {lock_path}: {exc}. Nothing was changed.")
    if held is None:
        return _refuse(
            f"The app is still running: another process holds {lock_path}. "
            "Stop the app, then run this command again. Nothing was changed."
        )
    try:
        in_use = _database_in_use(database, port)
        if in_use:
            return _refuse(in_use + " Nothing was changed.")
        return _replace(service, validation.snapshot_path)
    finally:
        held.release()


def _replace(service: BackupService, snapshot: Path) -> int:
    database = service.database_path
    staged: StagedRestore | None = None
    try:
        staged = service.stage_restore(snapshot)
        applied = service.apply_staged_restore(staged, maintenance_mode=True)
    except RestoreAfterSafetyCopyError as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        print(f"The database at {database} may already have been replaced.", file=sys.stderr)
        print("Your stock records may also have been replaced.", file=sys.stderr)
        _print_safety_copies(
            exc.pre_restore_backup, exc.damaged_copy, exc.records_copy, file=sys.stderr
        )
        return 1
    except (OSError, sqlite3.Error, RestoreSafetyError) as exc:
        print(f"Restore failed: {exc}", file=sys.stderr)
        print(f"The database at {database} was not changed.", file=sys.stderr)
        return 1
    finally:
        if staged is not None:
            staged.staged_path.unlink(missing_ok=True)

    print(f"Restored {database} from {snapshot.name}.")
    _print_records_outcome(applied)
    if applied.pre_restore_backup is None and applied.damaged_copy is None:
        print(f"There was no database at {database}, so no pre-restore backup was taken.")
    _print_safety_copies(
        applied.pre_restore_backup, applied.damaged_copy, applied.records_copy, file=sys.stdout
    )
    return 0


def _print_records_outcome(applied: AppliedRestore) -> None:
    if not applied.backup_has_user_records:
        print(
            "This backup was made before stock records were included in backups; "
            "your current stock records were left as they are."
        )
        return
    if applied.records_restored:
        print("Stock records restored: " + _record_list(applied.records_restored) + ".")
    left = [name for name, reason in applied.records_left if reason != RECORDS_PREDATE_BACKUP]
    if left:
        print(
            "Left as they are, because this backup has no copy of them: "
            + _record_list(left)
            + "."
        )


def _record_list(names: tuple[str, ...] | list[str]) -> str:
    return ", ".join(RECORD_LABELS.get(name, name) for name in names)


def _print_safety_copies(
    pre_restore: BackupArtifact | None,
    damaged_copy: Path | None,
    records_copy: Path | None,
    *,
    file: TextIO,
) -> None:
    if pre_restore is not None:
        path = pre_restore.snapshot_path
        print(f"The database as it was before this restore is saved at: {path}", file=file)
        if any(entry is not None for entry in (pre_restore.user_records or {}).values()):
            print("That backup also holds your stock records as they were.", file=file)
        print(f"To put it back, run: {RESTORE_COMMAND} {path.name}", file=file)
    if records_copy is not None:
        print(
            "Your stock records as they were before this restore are kept at: "
            f"{records_copy}",
            file=file,
        )
    if damaged_copy is not None:
        print(
            "The database failed its integrity check, so no backup could be made of it. "
            f"A raw copy of the damaged file is kept at: {damaged_copy}",
            file=file,
        )


def _backup_path(backup: str, backup_directory: Path) -> Path:
    path = Path(backup).expanduser()
    if path.name != backup:  # a path, not a bare backup name
        return path
    return backup_directory / (backup if path.suffix else f"{backup}.sqlite")


def _database_in_use(database: Path, port: int) -> str | None:
    # Second checks behind the app lock: an app from a build without that
    # lock still answers on its port, and the SQLite lock probe catches any
    # other program in the middle of reading or writing the database.
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return (
                f"The app is still running (it answers on 127.0.0.1:{port}). "
                "Stop it, then run this command again."
            )
    except OSError:
        pass
    if not database.exists():  # connecting would create an empty database
        return None
    connection = sqlite3.connect(database, timeout=0)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        connection.rollback()
    except sqlite3.OperationalError:
        return (
            f"The database {database} is in use by another program. "
            "Close it, then run this command again."
        )
    except sqlite3.DatabaseError:
        return None  # damaged, not in use: the restore keeps a raw copy of it
    finally:
        connection.close()
    return None


def _refuse(message: str) -> int:
    print(f"Restore refused: {message}", file=sys.stderr)
    return 1
