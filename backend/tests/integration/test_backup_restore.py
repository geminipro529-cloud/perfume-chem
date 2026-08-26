import json
import sqlite3
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.api.v1.endpoints.lab import _backup_service
from app.db_bootstrap import build_alembic_config
from app.models.base import Base
from app.models.lab import LabBottleEvent, LabMaterial
from app.models.lab_planning import LabInventoryReservationEvent
from app.services.backup_service import BackupService, RestoreSafetyError
from app.services.lab_export import ImportConflictError, LabExportService
from app.services.lab_service import LabService
from tests.a2_planning_fixtures import _approved_plan

CURRENT_HEAD = "20260731_0012"


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
