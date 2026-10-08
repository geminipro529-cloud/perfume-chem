"""Stopped-server restore: app lock, failure messages, disaster cases, staging."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app import db_bootstrap
from app.services import app_lock
from app.services import backup_service as backup_service_module
from app.services.backup_service import BackupService, backup_service_for_database_url
from app.services.restore_command import restore_from_backup
from tests.integration.test_backup_restore import (
    _app_database,
    _database,
    _free_port,
    _value,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
RESTORE = "python run_api_server.py --restore"


def _with_backup(tmp_path) -> tuple[Path, str, Path]:
    """Live DB holding 'current' and a backup of it holding 'old'."""

    database, database_url = _app_database(tmp_path, "old")
    backup = backup_service_for_database_url(database_url).create_backup()
    _set_value(database, "current")
    return database, database_url, backup.snapshot_path


def _set_value(database: Path, value: str) -> None:
    import sqlite3

    connection = sqlite3.connect(database)
    connection.execute("UPDATE lab_probe SET value = ?", (value,))
    connection.commit()
    connection.close()


def _stages(folder: Path) -> list[Path]:
    return sorted(folder.glob(".lab.db-restore-stage-*"))


def _restore(snapshot: Path, database_url: str) -> int:
    return restore_from_backup(snapshot.name, database_url=database_url, port=_free_port())


def _lock_holder(lock_path: Path) -> subprocess.Popen:
    """Another process that holds the app lock until its stdin closes."""

    code = (
        "import sys; from pathlib import Path; from app.services import app_lock\n"
        "held = app_lock.try_acquire(Path(sys.argv[1]))\n"
        "print('held' if held else 'busy', flush=True)\n"
        "sys.stdin.read()\n"
    )
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment["PYTHONPATH"] = str(BACKEND_DIR)
    holder = subprocess.Popen(
        [sys.executable, "-c", code, str(lock_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=environment,
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == "held"
    return holder


def test_restore_refuses_while_another_process_holds_the_app_lock(tmp_path, capsys):
    database, database_url, snapshot = _with_backup(tmp_path)
    lock_path = tmp_path / "lab.db.app.lock"

    holder = _lock_holder(lock_path)
    try:
        refused = _restore(snapshot, database_url)
        refusal = capsys.readouterr().err
    finally:
        assert holder.stdin is not None
        holder.stdin.close()
        holder.wait(timeout=30)

    assert refused != 0
    assert "The app is still running" in refusal and str(lock_path) in refusal
    assert "Nothing was changed" in refusal
    assert _value(database) == "current"
    assert _stages(tmp_path) == []
    assert list((tmp_path / "lab-backups").glob("lab-pre-restore-*")) == []

    # Once that process has exited, the OS has released its lock.
    assert _restore(snapshot, database_url) == 0
    assert _value(database) == "old"
    assert lock_path.exists()  # the lock file is never deleted


def test_app_lifespan_holds_the_lock_while_it_runs(tmp_path, monkeypatch, capsys):
    database, database_url, snapshot = _with_backup(tmp_path)
    lock_path = tmp_path / "lab.db.app.lock"
    monkeypatch.setattr(main_module.settings, "DATABASE_URL", database_url)
    monkeypatch.setattr(db_bootstrap, "upgrade_database", lambda _config: None)

    with TestClient(main_module.app) as client:
        assert client.get("/health").status_code == 200
        assert app_lock.try_acquire(lock_path) is None
        refused = _restore(snapshot, database_url)
        assert refused != 0
        assert "The app is still running" in capsys.readouterr().err
        assert _value(database) == "current"

    released = app_lock.try_acquire(lock_path)
    assert released is not None
    released.release()


def test_failure_after_the_pre_restore_backup_says_where_it_is(
    tmp_path, monkeypatch, capsys
):
    database, database_url, snapshot = _with_backup(tmp_path)
    require_integrity = backup_service_module._require_integrity

    def failing_after_replace(connection, label):
        if label == "restored database":
            raise backup_service_module.RestoreSafetyError(f"{label} failed (fixture)")
        require_integrity(connection, label)

    monkeypatch.setattr(backup_service_module, "_require_integrity", failing_after_replace)

    code = _restore(snapshot, database_url)

    error = capsys.readouterr().err
    pre_restore = sorted((tmp_path / "lab-backups").glob("lab-pre-restore-*.sqlite"))
    assert code != 0
    assert len(pre_restore) == 1
    assert _value(pre_restore[0]) == "current"
    assert "Restore failed" in error
    assert str(pre_restore[0]) in error
    assert f"{RESTORE} {pre_restore[0].name}" in error
    assert _stages(tmp_path) == []


def test_failure_while_staging_leaves_no_stage_file(tmp_path, monkeypatch, capsys):
    database, database_url, snapshot = _with_backup(tmp_path)

    def disk_full(source, target, *args):
        target.write(source.read(100))
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(backup_service_module.shutil, "copyfileobj", disk_full)

    code = _restore(snapshot, database_url)

    error = capsys.readouterr().err
    assert code != 0
    assert "No space left on device" in error and "was not changed" in error
    assert _stages(tmp_path) == []
    assert _value(database) == "current"


def test_restore_into_a_missing_live_database(tmp_path, capsys):
    database, database_url, snapshot = _with_backup(tmp_path)
    database.unlink()

    code = _restore(snapshot, database_url)

    output = capsys.readouterr().out
    assert code == 0
    assert _value(database) == "old"
    assert "no pre-restore backup was taken" in output
    assert list((tmp_path / "lab-backups").glob("lab-pre-restore-*")) == []
    assert _stages(tmp_path) == []


def test_restore_over_a_corrupt_live_database_keeps_a_raw_copy(tmp_path, capsys):
    database, database_url, snapshot = _with_backup(tmp_path)
    damaged = b"not a database " * 4096
    database.write_bytes(damaged)

    code = _restore(snapshot, database_url)

    output = capsys.readouterr().out
    copies = sorted(tmp_path.glob("lab.db.corrupt-*"))
    assert code == 0
    assert _value(database) == "old"
    assert len(copies) == 1
    assert copies[0].read_bytes() == damaged
    assert str(copies[0]) in output
    assert _stages(tmp_path) == []


def test_stage_files_of_databases_sharing_a_stem_are_kept_apart(tmp_path):
    services = {}
    for name in ("lab.db", "lab.sqlite"):
        _database(tmp_path / name, name)
        services[name] = BackupService(
            database_path=tmp_path / name,
            backup_directory=tmp_path / f"backups-{name}",
            expected_schema_revision="20260716_0001",
        )
    backups = {name: service.create_backup() for name, service in services.items()}
    not_a_stage = tmp_path / ".lab.db-restore-stage-notes.sqlite"
    not_a_stage.write_text("kept", encoding="utf-8")

    db_stage = services["lab.db"].stage_restore(backups["lab.db"].snapshot_path)
    sqlite_stage = services["lab.sqlite"].stage_restore(backups["lab.sqlite"].snapshot_path)
    db_again = services["lab.db"].stage_restore(backups["lab.db"].snapshot_path)
    sqlite_again = services["lab.sqlite"].stage_restore(backups["lab.sqlite"].snapshot_path)

    assert db_stage.staged_path.name.startswith(".lab.db-restore-stage-")
    assert sqlite_stage.staged_path.name.startswith(".lab.sqlite-restore-stage-")
    assert not db_stage.staged_path.exists() and not sqlite_stage.staged_path.exists()
    assert db_again.staged_path.exists() and sqlite_again.staged_path.exists()
    assert not_a_stage.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="reads /proc/self/fd")
def test_stage_copy_and_undo_manifest_are_synced_before_replace(
    tmp_path, monkeypatch, capsys
):
    database, database_url, snapshot = _with_backup(tmp_path)
    events: list[tuple[str, str]] = []
    real_fsync, real_replace = os.fsync, os.replace

    def fsync(descriptor):
        events.append(("fsync", os.readlink(f"/proc/self/fd/{descriptor}")))
        real_fsync(descriptor)

    def replace(source, target):
        events.append(("replace", str(source)))
        real_replace(source, target)

    monkeypatch.setattr(backup_service_module.os, "fsync", fsync)
    monkeypatch.setattr(backup_service_module.os, "replace", replace)

    assert _restore(snapshot, database_url) == 0

    replaced = [index for index, (kind, _) in enumerate(events) if kind == "replace"]
    assert replaced, events
    for index in replaced:
        source = events[index][1]
        assert ("fsync", source) in events[:index], (source, events)
    replaced_sources = [Path(events[index][1]).name for index in replaced]
    assert any(name.startswith(".lab.db-restore-stage-") for name in replaced_sources)
    assert any(".manifest.json-" in name for name in replaced_sources)
