"""The lab database in write-ahead-log mode: saving from two places, backups, restore.

The phone at the bench and the PC save to one SQLite file.  In write-ahead-log
mode a reader never holds up a save, but the log is a second file beside the
database, which backups and the stopped-server restore have to account for.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from alembic import command
from app.db_bootstrap import build_alembic_config, prepare_database_upgrade
from app.db_session import _use_sqlite_write_ahead_log
from app.db_session import engine as app_engine
from app.models.lab import LabMaterial
from app.services.backup_service import backup_service_for_database_url
from app.services.lab_service import LabService
from app.services.restore_command import restore_from_backup
from tests.integration.test_backup_restore import _app_database, _free_port, _value

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _wal(database: Path) -> Path:
    return database.with_name(database.name + "-wal")


def _sidecars(folder: Path) -> list[str]:
    return sorted(path.name for path in folder.rglob("*") if path.name.endswith(("-wal", "-shm")))


def _journal_mode_byte(database: Path) -> int:
    # Header bytes 18 and 19: 1 for rollback-journal mode, 2 for write-ahead-log mode.
    return database.read_bytes()[18]


def _to_write_ahead_log(database: Path) -> None:
    connection = sqlite3.connect(database)
    try:
        _use_sqlite_write_ahead_log(connection, None)
    finally:
        connection.close()


@pytest.mark.asyncio
async def test_the_app_connects_in_write_ahead_log_mode():
    # The mode is kept in the file, so start from rollback mode: only the app's
    # own connection setup can turn it back on.
    await app_engine.dispose()
    with closing(sqlite3.connect(app_engine.url.database)) as other:
        assert other.execute("PRAGMA journal_mode=DELETE").fetchone() == ("delete",)
    async with app_engine.connect() as connection:
        mode = (await connection.exec_driver_sql("PRAGMA journal_mode")).scalar()

    assert mode == "wal"


def test_a_save_goes_through_while_another_device_is_reading(tmp_path):
    database, _url = _app_database(tmp_path, "before")
    _to_write_ahead_log(database)
    reader = sqlite3.connect(database)
    reader.execute("BEGIN")
    assert reader.execute("SELECT value FROM lab_probe").fetchone() == ("before",)
    writer = sqlite3.connect(database, timeout=1)
    try:
        # In rollback mode this save waits for the reader and gives up locked.
        writer.execute("UPDATE lab_probe SET value = 'saved'")
        writer.commit()
        # The reader keeps the view it started with until its read ends.
        assert reader.execute("SELECT value FROM lab_probe").fetchone() == ("before",)
        reader.rollback()
        assert reader.execute("SELECT value FROM lab_probe").fetchone() == ("saved",)
    finally:
        writer.close()
        reader.close()


def test_a_backup_holds_the_log_s_saves_and_is_one_file(tmp_path):
    database, database_url = _app_database(tmp_path, "in the database")
    _to_write_ahead_log(database)
    app = sqlite3.connect(database)
    app.execute("PRAGMA wal_autocheckpoint=0")
    app.execute("UPDATE lab_probe SET value = 'only in the log'")
    app.commit()
    try:
        assert _wal(database).stat().st_size > 0
        service = backup_service_for_database_url(database_url)
        backup = service.create_backup()
        validation = service.validate_restore(backup.snapshot_path)
    finally:
        app.close()

    assert validation.valid, validation.errors
    assert _value(backup.snapshot_path) == "only in the log"
    assert _journal_mode_byte(backup.snapshot_path) == 1
    assert _sidecars(backup.snapshot_path.parent) == []


def test_the_pre_upgrade_snapshot_is_one_file(tmp_path):
    database, _url = _app_database(tmp_path, "before the upgrade")
    _to_write_ahead_log(database)

    snapshot = prepare_database_upgrade(database, tmp_path / "snapshots").snapshot_path

    assert snapshot is not None
    assert _journal_mode_byte(snapshot) == 1
    assert _value(snapshot) == "before the upgrade"
    assert _sidecars(snapshot.parent) == []


def test_restore_refuses_while_another_program_holds_the_database_open(tmp_path, capsys):
    database, database_url = _app_database(tmp_path, "old")
    backup = backup_service_for_database_url(database_url).create_backup()
    _to_write_ahead_log(database)
    other = sqlite3.connect(database)
    other.execute("UPDATE lab_probe SET value = 'current'")
    other.commit()
    try:
        code = restore_from_backup(
            backup.snapshot_path.name, database_url=database_url, port=_free_port()
        )
        error = capsys.readouterr().err
        assert code != 0
        assert "in use by another program" in error and "Nothing was changed" in error
    finally:
        other.close()
    assert _value(database) == "current"


def test_replacing_the_database_leaves_no_old_log_to_replay(tmp_path):
    # The restore command's in-use probe opens the database, which folds a
    # crash log in; the replace itself must not rely on that.
    database, database_url = _app_database(tmp_path, "old")
    service = backup_service_for_database_url(database_url)
    backup = service.create_backup()
    _to_write_ahead_log(database)
    app = sqlite3.connect(database)
    app.execute("PRAGMA wal_autocheckpoint=0")
    app.execute("UPDATE lab_probe SET value = 'crashed'")
    app.commit()
    crash_log = _wal(database).read_bytes()
    app.close()
    # The app died with its log not yet folded in, and the database file is damaged.
    damaged = b"not a database " * 4096
    database.write_bytes(damaged)
    _wal(database).write_bytes(crash_log)

    applied = service.apply_staged_restore(
        service.stage_restore(backup.snapshot_path), maintenance_mode=True
    )

    assert not _wal(database).exists()
    assert _value(database) == "old"
    assert applied.damaged_copy is not None
    assert applied.damaged_copy.read_bytes() == damaged
    # Opening the raw copy replays its log, as it would have for the live file.
    assert _wal(applied.damaged_copy).read_bytes() == crash_log


async def _names(engine) -> list[str]:
    async with AsyncSession(engine) as session:
        return sorted(await session.scalars(select(LabMaterial.canonical_name)))


@pytest.mark.asyncio
async def test_round_trip_in_write_ahead_log_mode(tmp_path, capsys):
    database = tmp_path / "lab.db"
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    command.upgrade(build_alembic_config(ALEMBIC_INI, database_url), "head")

    def _engine():
        engine = create_async_engine(database_url)
        event.listen(engine.sync_engine, "connect", _use_sqlite_write_ahead_log)
        return engine

    engine = _engine()
    async with AsyncSession(engine) as session:
        for name in ("Ambroxan", "Hedione"):
            await LabService(session).create_material(name)
    # The backup runs while the app is still connected, its saves in the log.
    assert _wal(database).exists()
    backup = backup_service_for_database_url(database_url).create_backup()
    async with AsyncSession(engine) as session:
        await LabService(session).create_material("Added after the backup")
    await engine.dispose()
    assert not _wal(database).exists()

    code = restore_from_backup(
        backup.snapshot_path.name, database_url=database_url, port=_free_port()
    )

    assert code == 0, capsys.readouterr()
    engine = _engine()
    try:
        assert await _names(engine) == ["Ambroxan", "Hedione"]
        async with engine.connect() as connection:
            mode = (await connection.exec_driver_sql("PRAGMA journal_mode")).scalar()
        assert mode == "wal"
    finally:
        await engine.dispose()
    safety = sorted(backup.snapshot_path.parent.glob("lab-pre-restore-*.sqlite"))
    assert len(safety) == 1
    with closing(sqlite3.connect(safety[0])) as kept:
        names = [row[0] for row in kept.execute("SELECT canonical_name FROM lab_materials")]
    assert "Added after the backup" in names
