"""Direction 4: a real backup of the real schema restores into a database, intact.

Round trip through the same code Kenny uses: rows written by the lab service on a
database migrated to the current head, a backup from the backup service, then
changes and deletions, then the stopped-server restore command
(``run_api_server.py --restore``).  Every original row must come back and every
later change must be gone.
"""

import socket
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from alembic import command
from app.db_bootstrap import build_alembic_config
from app.models.lab import LabMaterial
from app.services.backup_service import backup_service_for_database_url
from app.services.lab_service import LabService
from app.services.restore_command import restore_from_backup

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
ORIGINAL = ["Ambroxan", "Hedione", "Iso E Super", "Orris Butter"]


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


async def _names(database_url: str) -> list[str]:
    engine = create_async_engine(database_url)
    try:
        async with AsyncSession(engine) as session:
            rows = await session.scalars(select(LabMaterial.canonical_name))
            return sorted(rows)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_backup_restores_every_row_and_drops_later_changes(tmp_path, capsys):
    database = tmp_path / "lab.db"
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    command.upgrade(build_alembic_config(ALEMBIC_INI, database_url), "head")

    engine = create_async_engine(database_url)
    async with AsyncSession(engine) as session:
        lab = LabService(session)
        for name in ORIGINAL:
            await lab.create_material(name)
    await engine.dispose()
    assert await _names(database_url) == ORIGINAL

    backup = backup_service_for_database_url(database_url).create_backup(label="manual")

    # After the backup: one row deleted, one renamed, one added.
    engine = create_async_engine(database_url)
    async with AsyncSession(engine) as session:
        rows = {row.canonical_name: row for row in await session.scalars(select(LabMaterial))}
        await session.delete(rows["Hedione"])
        rows["Iso E Super"].canonical_name = "Renamed by mistake"
        session.add(LabMaterial(canonical_name="Added after the backup"))
        await session.commit()
    await engine.dispose()
    assert "Hedione" not in await _names(database_url)

    exit_code = restore_from_backup(
        backup.snapshot_path.name, database_url=database_url, port=_free_port()
    )

    assert exit_code == 0, capsys.readouterr()
    assert await _names(database_url) == ORIGINAL
    # The state just before the restore is kept as a safety copy.
    safety = sorted((backup.snapshot_path.parent).glob("lab-pre-restore-*.sqlite"))
    assert len(safety) == 1
    assert "Added after the backup" in await _names(
        f"sqlite+aiosqlite:///{safety[0].as_posix()}"
    )
