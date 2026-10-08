import json
import socket
import sqlite3
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.api.v1.endpoints.lab import _backup_service
from app.api.v1.endpoints.lab import stage_restore as stage_restore_route
from app.db_bootstrap import build_alembic_config
from app.models.base import Base
from app.models.lab import LabBottleEvent, LabMaterial
from app.models.lab_planning import LabInventoryReservationEvent
from app.schemas.lab import RestoreSnapshotCreate
from app.services.backup_service import (
    BackupService,
    RestoreSafetyError,
    backup_service_for_database_url,
)
from app.services.lab_export import ImportConflictError, LabExportService
from app.services.lab_service import LabService
from app.services.restore_command import restore_from_backup
from tests.a2_planning_fixtures import _approved_plan

CURRENT_HEAD = "20261008_0026"


def _database(path, value: str, revision: str = "20260716_0001") -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE alembic_version (version_num TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
    connection.execute("CREATE TABLE lab_probe (value TEXT NOT NULL)")
    connection.execute("INSERT INTO lab_probe VALUES (?)", (value,))
    connection.commit()
    connection.close()


def _value(path) -> str:
    connection = sqlite3.connect(path)
    try:
        return connection.execute("SELECT value FROM lab_probe").fetchone()[0]
    finally:
        connection.close()


@pytest.mark.asyncio
async def test_http_backup_service_tracks_the_current_alembic_head(tmp_path):
    database = tmp_path / "lab.db"
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    engine = create_async_engine(database_url)
    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    config = build_alembic_config(config_path, database_url)
    expected_head = ScriptDirectory.from_config(config).get_current_head()

    async with AsyncSession(engine) as session:
        service = _backup_service(session)

    await engine.dispose()
    assert service.expected_schema_revision == expected_head


def test_live_backup_writes_consistent_snapshot_manifest_and_digest(tmp_path):
    database = tmp_path / "lab.db"
    _database(database, "original")
    service = BackupService(
        database_path=database,
        backup_directory=tmp_path / "backups",
        expected_schema_revision="20260716_0001",
    )

    artifact = service.create_backup(label="manual")
    validation = service.validate_restore(artifact.snapshot_path)

    assert artifact.snapshot_path.exists()
    assert artifact.manifest_path.exists()
    assert len(artifact.snapshot_sha256) == 64
    assert len(artifact.schema_fingerprint_sha256) == 64
    assert artifact.schema_revision == "20260716_0001"
    assert validation.valid is True
    assert validation.errors == ()
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    assert manifest["snapshot_sha256"] == artifact.snapshot_sha256
    assert _value(artifact.snapshot_path) == "original"


def test_a2_migrated_backup_manifest_tracks_new_head(tmp_path):
    database = tmp_path / "a2-lab.db"
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    config = build_alembic_config(config_path, database_url)
    command.upgrade(config, "head")
    service = BackupService(
        database_path=database,
        backup_directory=tmp_path / "a2-backups",
        expected_schema_revision=CURRENT_HEAD,
    )

    artifact = service.create_backup(label="a2-planning")
    validation = service.validate_restore(artifact.snapshot_path)

    assert artifact.schema_revision == CURRENT_HEAD
    assert validation.valid is True


def test_restore_validation_rejects_corrupt_digest_and_revision(tmp_path):
    database = tmp_path / "lab.db"
    _database(database, "original")
    service = BackupService(
        database_path=database,
        backup_directory=tmp_path / "backups",
        expected_schema_revision="20260716_0001",
    )
    artifact = service.create_backup()
    artifact.snapshot_path.write_bytes(artifact.snapshot_path.read_bytes() + b"tamper")

    corrupt = service.validate_restore(artifact.snapshot_path)

    assert corrupt.valid is False
    assert "snapshot digest mismatch" in corrupt.errors

    other_database = tmp_path / "newer.db"
    _database(other_database, "newer", revision="future_revision")
    other_service = BackupService(
        database_path=other_database,
        backup_directory=tmp_path / "other-backups",
        expected_schema_revision="future_revision",
    )
    newer = other_service.create_backup()
    newer.snapshot_path.replace(service.backup_directory / newer.snapshot_path.name)
    newer.manifest_path.replace(
        service.backup_directory / newer.manifest_path.name
    )
    mismatch = service.validate_restore(
        service.backup_directory / newer.snapshot_path.name
    )
    assert mismatch.valid is False
    assert any("schema revision" in error for error in mismatch.errors)


def test_restore_stages_while_running_and_applies_only_in_maintenance_mode(tmp_path):
    database = tmp_path / "lab.db"
    _database(database, "old")
    service = BackupService(
        database_path=database,
        backup_directory=tmp_path / "backups",
        expected_schema_revision="20260716_0001",
    )
    old_backup = service.create_backup(label="old")

    connection = sqlite3.connect(database)
    connection.execute("UPDATE lab_probe SET value = 'current'")
    connection.commit()
    connection.close()

    staged = service.stage_restore(old_backup.snapshot_path)
    assert staged.staged_path.exists()
    assert _value(database) == "current"
    with pytest.raises(RestoreSafetyError, match="maintenance mode"):
        service.apply_staged_restore(staged, maintenance_mode=False)

    result = service.apply_staged_restore(staged, maintenance_mode=True)

    assert _value(database) == "old"
    assert result.pre_restore_backup.snapshot_path.exists()
    assert _value(result.pre_restore_backup.snapshot_path) == "current"


@pytest.mark.asyncio
async def test_a5_backup_restores_active_stream_and_open_reservation_replay(
    tmp_path,
):
    database = tmp_path / "a5-active.db"
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    config = build_alembic_config(config_path, database_url)
    command.upgrade(config, "head")
    engine = create_async_engine(database_url)

    @event.listens_for(engine.sync_engine, "connect")
    def _source_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        service, approved, line, stock = await _approved_plan(session)
        reservation = await service.reserve_inventory(
            build_plan_version_id=approved.id,
            build_plan_line_id=line.id,
            stock_solution_id=stock.id,
            reserved_mass_g=1.0,
            idempotency_key="a5-backup-reservation",
            actor="planner",
            rationale="Open during backup",
        )
        bottle = await service.create_bottle("A5 active stream")
        await service.add_stock_to_bottle(
            bottle_id=bottle.id,
            stock_solution_id=stock.id,
            mass_g=0.25,
            expected_sequence=1,
            command_id="a5-backup-addition",
        )
        expected_replay = await service.reconstruct_bottle(bottle.id)
        bottle_id = bottle.id
        stock_id = stock.id
        reservation_id = reservation.reservation_id
        await session.commit()
    await engine.dispose()

    backup_service = BackupService(
        database_path=database,
        backup_directory=tmp_path / "a5-backups",
        expected_schema_revision=CURRENT_HEAD,
    )
    artifact = backup_service.create_backup(label="active-stream")

    mutate_engine = create_async_engine(database_url)
    async with AsyncSession(mutate_engine) as session:
        service = LabService(session)
        await service.add_stock_to_bottle(
            bottle_id=bottle_id,
            stock_solution_id=stock_id,
            mass_g=0.1,
            expected_sequence=2,
            command_id="post-backup-addition",
        )
    await mutate_engine.dispose()

    staged = backup_service.stage_restore(artifact.snapshot_path)
    backup_service.apply_staged_restore(staged, maintenance_mode=True)

    restored_engine = create_async_engine(database_url)
    async with AsyncSession(restored_engine) as session:
        service = LabService(session)
        restored_replay = await service.reconstruct_bottle(bottle_id)
        latest_reservation = (
            await session.execute(
                select(LabInventoryReservationEvent)
                .where(
                    LabInventoryReservationEvent.reservation_id
                    == reservation_id
                )
                .order_by(
                    LabInventoryReservationEvent.sequence.desc()
                )
                .limit(1)
            )
        ).scalar_one()
    await restored_engine.dispose()

    assert restored_replay == expected_replay
    assert latest_reservation.state == "RESERVED"


@pytest.mark.asyncio
async def test_json_export_preserves_ids_event_order_and_imports_idempotently(db_session):
    service = LabService(db_session)
    material = await service.create_material("Portable iris")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.3,
        fraction_basis="mass_fraction",
        initial_mass_g=2.0,
    )
    bottle = await service.create_bottle("Portable bottle", initial_mass_g=1.0)
    await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=stock.id,
        mass_g=0.2,
        expected_sequence=1,
        command_id="portable-addition",
    )
    packet = await LabExportService(db_session).export_workspace()

    assert packet["format_revision"] == "lab-export-v1"
    assert packet["unit_contract"]["mass_g"] == "g"
    events = packet["tables"]["lab_bottle_events"]
    assert [row["stream_sequence"] for row in events] == [1, 2]
    assert packet["tables"]["lab_materials"][0]["id"] == material.id

    target_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(target_engine.sync_engine, "connect")
    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    async with target_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as target_session:
        importer = LabExportService(target_session)
        first = await importer.import_workspace(packet)
        second = await importer.import_workspace(packet)
        assert first.inserted > 0
        assert second.inserted == 0
        assert second.skipped == first.inserted
        assert await target_session.scalar(select(func.count()).select_from(LabBottleEvent)) == 2
        imported = await target_session.get(LabMaterial, material.id)
        assert imported is not None and imported.canonical_name == "Portable iris"

        conflicting = json.loads(json.dumps(packet))
        conflicting["tables"]["lab_materials"][0]["canonical_name"] = "Changed history"
        with pytest.raises(ImportConflictError):
            await importer.import_workspace(conflicting)

    await target_engine.dispose()


def _app_database(tmp_path, value: str) -> tuple[Path, str]:
    """A file database at the app's schema head, with its database URL."""

    database = tmp_path / "lab.db"
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    head = ScriptDirectory.from_config(
        build_alembic_config(config_path, database_url)
    ).get_current_head()
    _database(database, value, revision=head)
    return database, database_url


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _leftovers(tmp_path) -> tuple[list[str], list[str]]:
    stages = sorted(path.name for path in tmp_path.glob(".lab-restore-stage-*"))
    backups = sorted(
        path.name for path in (tmp_path / "lab-backups").glob("*.sqlite")
    )
    return stages, backups


def test_restore_command_refuses_while_the_app_answers_on_its_port(
    tmp_path, capsys
):
    database, database_url = _app_database(tmp_path, "old")
    service = backup_service_for_database_url(database_url)
    backup = service.create_backup()
    connection = sqlite3.connect(database)
    connection.execute("UPDATE lab_probe SET value = 'current'")
    connection.commit()
    connection.close()

    with socket.socket() as app:  # an idle running app: listening, no SQLite lock
        app.bind(("127.0.0.1", 0))
        app.listen()
        code = restore_from_backup(
            backup.snapshot_path.name,
            database_url=database_url,
            port=app.getsockname()[1],
        )

    assert code != 0
    assert "The app is still running" in capsys.readouterr().err
    assert _value(database) == "current"
    assert _leftovers(tmp_path) == ([], [backup.snapshot_path.name])


def test_restore_command_refuses_while_another_program_locks_the_database(
    tmp_path, capsys
):
    database, database_url = _app_database(tmp_path, "old")
    backup = backup_service_for_database_url(database_url).create_backup()

    holder = sqlite3.connect(database)
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("UPDATE lab_probe SET value = 'uncommitted'")
    try:
        code = restore_from_backup(
            str(backup.snapshot_path), database_url=database_url, port=_free_port()
        )
    finally:
        holder.rollback()
        holder.close()

    assert code != 0
    assert "in use by another program" in capsys.readouterr().err
    assert _value(database) == "old"
    assert _leftovers(tmp_path) == ([], [backup.snapshot_path.name])


def test_restore_command_refuses_missing_and_corrupted_backups(tmp_path, capsys):
    database, database_url = _app_database(tmp_path, "current")
    backup = backup_service_for_database_url(database_url).create_backup()
    backup.snapshot_path.write_bytes(backup.snapshot_path.read_bytes() + b"tamper")

    missing = restore_from_backup(
        "lab-manual-missing.sqlite", database_url=database_url, port=_free_port()
    )
    missing_error = capsys.readouterr().err
    corrupted = restore_from_backup(
        backup.snapshot_path.name, database_url=database_url, port=_free_port()
    )
    corrupted_error = capsys.readouterr().err

    assert missing != 0 and "snapshot file is missing" in missing_error
    assert corrupted != 0 and "snapshot digest mismatch" in corrupted_error
    assert _value(database) == "current"
    assert _leftovers(tmp_path) == ([], [backup.snapshot_path.name])


def test_staging_again_removes_the_earlier_stage_copy(tmp_path):
    database = tmp_path / "lab.db"
    _database(database, "old")
    unrelated = tmp_path / ".lab-restore-stage-notes.txt"
    unrelated.write_text("not a stage copy", encoding="utf-8")
    service = BackupService(
        database_path=database,
        backup_directory=tmp_path / "backups",
        expected_schema_revision="20260716_0001",
    )
    backup = service.create_backup()

    first = service.stage_restore(backup.snapshot_path)
    second = service.stage_restore(backup.snapshot_path)

    assert not first.staged_path.exists()
    assert list(tmp_path.glob(".lab-restore-stage-*.sqlite")) == [second.staged_path]
    assert unrelated.exists()


@pytest.mark.asyncio
async def test_stage_route_message_names_the_exact_restore_command(tmp_path):
    database, database_url = _app_database(tmp_path, "old")
    backup = backup_service_for_database_url(database_url).create_backup()
    engine = create_async_engine(database_url)
    async with AsyncSession(engine) as session:
        response = await stage_restore_route(
            RestoreSnapshotCreate(snapshot_path=str(backup.snapshot_path)), session
        )
    await engine.dispose()

    assert response["message"] == (
        "Validated. Stop the app, then run: python run_api_server.py "
        f"--restore {backup.snapshot_path.name}"
    )
    assert response["source_snapshot_path"] == str(backup.snapshot_path)
    assert Path(response["staged_path"]).exists()
