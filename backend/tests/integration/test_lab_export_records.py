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
DILUTIONS = "user_inventory_dilution_events.jsonl"
NAMES = (ADDITIONS, COMPLETIONS, BASKET, DILUTIONS)

# CRLF, non-ASCII and a byte that is not valid UTF-8: the copy must be exact.
ADDITION_BYTES = b'{"event":"added","name":"Iris \xc3\xa9"}\r\n{"event":"added"}\n\xff'
COMPLETION_BYTES = b'{"event":"completed","dilution":"10% w/w"}\n'
DILUTION_BYTES = b'{"event":"prepared","strength":"1% w/w in DPG"}\n'


def _paths(directory):
    return {name: directory / name for name in NAMES}


def _source_records(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / ADDITIONS).write_bytes(ADDITION_BYTES)
    (source / COMPLETIONS).write_bytes(COMPLETION_BYTES)
    (source / DILUTIONS).write_bytes(DILUTION_BYTES)
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
    for name, content in (
        (ADDITIONS, ADDITION_BYTES),
        (COMPLETIONS, COMPLETION_BYTES),
        (DILUTIONS, DILUTION_BYTES),
    ):
        assert records[name]["sha256"] == hashlib.sha256(content).hexdigest()
        assert records[name]["size_bytes"] == len(content)
        assert base64.b64decode(records[name]["content_base64"]) == content

    packet = json.loads(json.dumps(packet))  # through JSON, as the Export button sends it
    target = tmp_path / "new-pc" / "data" / "user"
    async with _EmptyWorkspace(_paths(target)) as workspace:
        result = await workspace.importer.import_workspace(packet)
        assert result.records_written == 3
        assert result.records_already_present == 0
        assert result.as_dict()["records_written"] == 3
        assert await workspace.material_count() == 1
    assert (target / ADDITIONS).read_bytes() == ADDITION_BYTES
    assert (target / COMPLETIONS).read_bytes() == COMPLETION_BYTES
    assert (target / DILUTIONS).read_bytes() == DILUTION_BYTES
    assert not (target / BASKET).exists()
    assert sorted(path.name for path in target.iterdir()) == sorted(
        [ADDITIONS, COMPLETIONS, DILUTIONS]
    )


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
        assert (result.records_written, result.records_already_present) == (2, 1)
    after = live.stat()
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert live.read_bytes() == ADDITION_BYTES


@pytest.mark.asyncio
async def test_live_record_that_grew_since_the_export_is_left_alone(db_session, tmp_path):
    packet = await _exported_packet(db_session, _source_records(tmp_path))
    target = tmp_path / "target"
    target.mkdir()
    grown = COMPLETION_BYTES + b'{"event":"completed","later":true}\n'
    (target / COMPLETIONS).write_bytes(grown)
    async with _EmptyWorkspace(_paths(target)) as workspace:
        result = await workspace.importer.import_workspace(packet)
        assert (result.records_written, result.records_already_present) == (2, 1)
        assert await workspace.material_count() == 1
    assert (target / COMPLETIONS).read_bytes() == grown
    assert (target / ADDITIONS).read_bytes() == ADDITION_BYTES


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
        assert (result.records_written, result.records_already_present) == (0, 0)
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


@pytest.mark.asyncio
async def test_export_carries_liking_rows_and_restores_them(client, db_session, tmp_path, monkeypatch):
    from app.models.liking import LikingMaterialRating, LikingPick, LikingRating
    from app.services import personal_liking

    monkeypatch.setenv(personal_liking.PERSONAL_LIKING_PATH_ENV, str(tmp_path / "fit.json"))
    monkeypatch.setenv(personal_liking.CROWD_TABLE_PATH_ENV, str(tmp_path / "crowd.json"))
    base = "/api/v1/feedback/liking"
    shares = {"Iso E Super": 0.5}
    assert (
        await client.post(
            f"{base}/ratings",
            json={
                "formula_name": "Iris Cathedral",
                "formula_key": "k1",
                "window": "opening",
                "liking": 8,
                "note": "calm",
                "material_shares": shares,
            },
        )
    ).status_code == 201
    assert (
        await client.post(
            f"{base}/picks",
            json={
                "window": "1h",
                "formula_a_name": "A",
                "formula_a_key": "ka",
                "shares_a": shares,
                "formula_b_name": "B",
                "formula_b_key": "kb",
                "shares_b": shares,
                "preferred": "same",
            },
        )
    ).status_code == 201
    assert (
        await client.post(f"{base}/materials", json={"material": "Hedione", "liking": 6})
    ).status_code == 201

    packet = (await client.get("/api/v1/lab/export")).json()
    assert packet["format_revision"] == "lab-export-v6"
    tables = packet["tables"]
    assert [row["liking"] for row in tables["liking_ratings"]] == [8]
    assert tables["liking_ratings"][0]["note"] == "calm"
    assert [row["preferred"] for row in tables["liking_picks"]] == ["same"]
    assert [row["material"] for row in tables["liking_material_ratings"]] == ["Hedione"]

    async with _EmptyWorkspace(_paths(tmp_path / "restored")) as workspace:
        await workspace.importer.import_workspace(json.loads(json.dumps(packet)))
        for model, count in ((LikingRating, 1), (LikingPick, 1), (LikingMaterialRating, 1)):
            assert await workspace.session.scalar(select(func.count()).select_from(model)) == count


@pytest.mark.asyncio
async def test_export_before_the_liking_tables_still_restores(db_session, tmp_path):
    from app.services.lab_export import migrate_export_packet

    exporter = LabExportService(db_session, record_paths=lambda: _source_records(tmp_path))
    await LabService(db_session).create_material("Older iris")
    packet = json.loads(json.dumps(await exporter.export_workspace(format_revision="lab-export-v5")))
    assert "liking_ratings" not in packet["tables"]
    assert "liking_ratings" in migrate_export_packet(packet)["tables"]
    async with _EmptyWorkspace(_paths(tmp_path / "older")) as workspace:
        await workspace.importer.import_workspace(packet)
        assert await workspace.material_count() == 1
