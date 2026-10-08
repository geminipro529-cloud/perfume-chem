"""The full workspace export carries Kenny's personal stock records byte for byte."""

import base64
import hashlib
import json

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.lab import LabMaterial
from app.services.lab_export import ImportConflictError, LabExportService
from app.services.lab_service import LabService

ADDITIONS = "user_inventory_addition_events.jsonl"
COMPLETIONS = "user_inventory_completion_events.jsonl"
BASKET = "user_basket_events.jsonl"
NAMES = (ADDITIONS, COMPLETIONS, BASKET)

# CRLF, non-ASCII and a byte that is not valid UTF-8: the copy must be exact.
ADDITION_BYTES = b'{"event":"added","name":"Iris \xc3\xa9"}\r\n{"event":"added"}\n\xff'
COMPLETION_BYTES = b'{"event":"completed","dilution":"10% w/w"}\n'


def _paths(directory):
    return {name: directory / name for name in NAMES}


def _source_records(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / ADDITIONS).write_bytes(ADDITION_BYTES)
    (source / COMPLETIONS).write_bytes(COMPLETION_BYTES)
    return _paths(source)


async def _exported_packet(db_session, record_paths):
    await LabService(db_session).create_material("Portable iris")
    exporter = LabExportService(db_session, record_paths=lambda: record_paths)
    return await exporter.export_workspace()


class _EmptyWorkspace:
    def __init__(self, record_paths):
        self.record_paths = record_paths

    async def __aenter__(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        @event.listens_for(self.engine.sync_engine, "connect")
        def _foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.session = factory()
        self.importer = LabExportService(
            self.session, record_paths=lambda: self.record_paths
        )
        return self

    async def material_count(self):
        return await self.session.scalar(select(func.count()).select_from(LabMaterial))

    async def __aexit__(self, *_exc):
        await self.session.close()
        await self.engine.dispose()


@pytest.mark.asyncio
async def test_export_holds_records_and_round_trips_byte_exact(db_session, tmp_path):
    packet = await _exported_packet(db_session, _source_records(tmp_path))
    records = packet["records"]
    assert set(records) == set(NAMES)
    assert records[BASKET] is None
    for name, content in ((ADDITIONS, ADDITION_BYTES), (COMPLETIONS, COMPLETION_BYTES)):
        assert records[name]["sha256"] == hashlib.sha256(content).hexdigest()
        assert records[name]["size_bytes"] == len(content)
        assert base64.b64decode(records[name]["content_base64"]) == content

    packet = json.loads(json.dumps(packet))  # through JSON, as the Export button sends it
    target = tmp_path / "new-pc" / "data" / "user"
    async with _EmptyWorkspace(_paths(target)) as workspace:
        result = await workspace.importer.import_workspace(packet)
        assert result.records_written == 2
        assert result.records_identical == 0
        assert result.as_dict()["records_written"] == 2
        assert await workspace.material_count() == 1
    assert (target / ADDITIONS).read_bytes() == ADDITION_BYTES
    assert (target / COMPLETIONS).read_bytes() == COMPLETION_BYTES
    assert not (target / BASKET).exists()
    assert sorted(path.name for path in target.iterdir()) == sorted([ADDITIONS, COMPLETIONS])


@pytest.mark.asyncio
async def test_identical_live_record_is_left_alone(db_session, tmp_path):
    packet = await _exported_packet(db_session, _source_records(tmp_path))
    target = tmp_path / "target"
    target.mkdir()
    live = target / ADDITIONS
    live.write_bytes(ADDITION_BYTES)
    before = live.stat()
    async with _EmptyWorkspace(_paths(target)) as workspace:
        result = await workspace.importer.import_workspace(packet)
        assert (result.records_written, result.records_identical) == (1, 1)
    after = live.stat()
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert live.read_bytes() == ADDITION_BYTES


@pytest.mark.asyncio
async def test_different_live_record_refuses_the_whole_import(db_session, tmp_path):
    packet = await _exported_packet(db_session, _source_records(tmp_path))
    target = tmp_path / "target"
    target.mkdir()
    (target / COMPLETIONS).write_bytes(b'{"event":"completed","other":true}\n')
    async with _EmptyWorkspace(_paths(target)) as workspace:
        with pytest.raises(ImportConflictError, match=COMPLETIONS):
            await workspace.importer.import_workspace(packet)
        assert await workspace.material_count() == 0
    assert (target / COMPLETIONS).read_bytes() == b'{"event":"completed","other":true}\n'
    assert not (target / ADDITIONS).exists()


@pytest.mark.asyncio
async def test_tampered_record_is_refused_before_anything_is_written(db_session, tmp_path):
    packet = await _exported_packet(db_session, _source_records(tmp_path))
    tampered = base64.b64encode(COMPLETION_BYTES.replace(b"10%", b"20%")).decode("ascii")
    packet["records"][COMPLETIONS]["content_base64"] = tampered
    target = tmp_path / "target"
    async with _EmptyWorkspace(_paths(target)) as workspace:
        with pytest.raises(ValueError, match="hash"):
            await workspace.importer.import_workspace(packet)
        assert await workspace.material_count() == 0
    assert not target.exists()


@pytest.mark.asyncio
async def test_packet_without_records_leaves_live_records_alone(db_session, tmp_path):
    packet = await _exported_packet(db_session, _source_records(tmp_path))
    del packet["records"]
    target = tmp_path / "target"
    target.mkdir()
    (target / ADDITIONS).write_bytes(b"live history\n")
    async with _EmptyWorkspace(_paths(target)) as workspace:
        result = await workspace.importer.import_workspace(packet)
        assert (result.records_written, result.records_identical) == (0, 0)
        assert await workspace.material_count() == 1
    assert (target / ADDITIONS).read_bytes() == b"live history\n"
    assert sorted(path.name for path in target.iterdir()) == [ADDITIONS]


@pytest.mark.asyncio
async def test_partial_exports_leave_the_records_out(db_session, tmp_path):
    exporter = LabExportService(db_session, record_paths=lambda: _source_records(tmp_path))
    for packet in (
        await exporter.export_planning_workspace(),
        await exporter.export_science_workspace(),
        await exporter.export_execution_workspace(),
        await exporter.export_external_validation_workspace(),
    ):
        assert "records" not in packet
