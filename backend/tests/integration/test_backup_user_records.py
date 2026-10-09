"""Backups carry the personal stock records, and the restore puts them back."""

import json
import os
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from engine.user_records import (
    ADDITION_LOG_NAME,
    BASKET_LOG_NAME,
    COMPLETION_LOG_NAME,
    DILUTION_LOG_NAME,
)

from app.services import backup_service as backup_service_module
from app.services.backup_service import BackupService, RestoreSafetyError
from app.services.restore_command import restore_from_backup
from tests.integration.test_backup_restore import (
    _app_database,
    _database,
    _free_port,
    _value,
)

REVISION = "20260716_0001"


def _records(folder: Path) -> dict[str, Path]:
    return {
        ADDITION_LOG_NAME: folder / "additions.jsonl",
        COMPLETION_LOG_NAME: folder / "completions.jsonl",
        BASKET_LOG_NAME: folder / BASKET_LOG_NAME,
        DILUTION_LOG_NAME: folder / DILUTION_LOG_NAME,
    }


def _service(tmp_path: Path, database: Path | None = None) -> tuple[BackupService, dict]:
    records = _records(tmp_path / "user")
    (tmp_path / "user").mkdir(exist_ok=True)
    database = database or tmp_path / "lab.db"
    if not database.exists():
        _database(database, "old")
    service = BackupService(
        database_path=database,
        backup_directory=tmp_path / "lab-backups",
        expected_schema_revision=REVISION,
        user_records=lambda: records,
    )
    return service, records


def _set(database: Path, value: str) -> None:
    connection = sqlite3.connect(database)
    connection.execute("UPDATE lab_probe SET value = ?", (value,))
    connection.commit()
    connection.close()


def _restore(service: BackupService, snapshot: Path):
    staged = service.stage_restore(snapshot)
    return service.apply_staged_restore(staged, maintenance_mode=True)


def _records_dir(snapshot: Path) -> Path:
    return snapshot.with_suffix(".records")


def test_backup_copies_records_byte_for_byte_and_lists_absent_ones_as_null(tmp_path):
    service, records = _service(tmp_path)
    addition = b'{"event_id":"a1"}\n{"event_id":"a2","note":"\xc3\xa9"}\n'
    records[ADDITION_LOG_NAME].write_bytes(addition)
    records[COMPLETION_LOG_NAME].write_bytes(b"")
    dilution = b'{"event_id":"prepared-dilution-1"}\n'
    records[DILUTION_LOG_NAME].write_bytes(dilution)

    artifact = service.create_backup("manual")

    copies = _records_dir(artifact.snapshot_path)
    assert (copies / ADDITION_LOG_NAME).read_bytes() == addition
    assert (copies / COMPLETION_LOG_NAME).read_bytes() == b""
    assert not (copies / BASKET_LOG_NAME).exists()
    assert (copies / DILUTION_LOG_NAME).read_bytes() == dilution
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    assert manifest["user_records"] == {
        ADDITION_LOG_NAME: {"sha256": sha256(addition).hexdigest(), "bytes": len(addition)},
        COMPLETION_LOG_NAME: {"sha256": sha256(b"").hexdigest(), "bytes": 0},
        BASKET_LOG_NAME: None,
        DILUTION_LOG_NAME: {"sha256": sha256(dilution).hexdigest(), "bytes": len(dilution)},
    }
    validation = service.validate_restore(artifact.snapshot_path)
    assert validation.valid is True
    assert validation.includes_user_records is True
    assert validation.user_records == {
        ADDITION_LOG_NAME: "verified",
        COMPLETION_LOG_NAME: "verified",
        BASKET_LOG_NAME: "not in backup",
        DILUTION_LOG_NAME: "verified",
    }


def test_partial_last_line_is_taken_again(tmp_path, monkeypatch):
    service, records = _service(tmp_path)
    live = records[ADDITION_LOG_NAME]
    live.write_bytes(b'{"event_id":"a1"}\n{"event_id":')
    real_copy = backup_service_module._copy_file
    calls = []

    def copy_then_finish_the_write(source, target, *, exclusive):
        real_copy(source, target, exclusive=exclusive)
        calls.append(source)
        live.write_bytes(b'{"event_id":"a1"}\n{"event_id":"a2"}\n')

    monkeypatch.setattr(backup_service_module, "_copy_file", copy_then_finish_the_write)
    monkeypatch.setattr(backup_service_module, "_RECORD_RETAKE_PAUSE_SECONDS", 0)

    artifact = service.create_backup()

    assert len(calls) == 2
    copy = _records_dir(artifact.snapshot_path) / ADDITION_LOG_NAME
    assert copy.read_bytes() == b'{"event_id":"a1"}\n{"event_id":"a2"}\n'


def test_record_that_stays_partial_is_backed_up_as_it_is(tmp_path, monkeypatch):
    # A torn last line that outlasts every retake is the file's real content;
    # refusing it would block every backup, and with it every restore.
    service, records = _service(tmp_path)
    torn = b'{"event_id":"c1"}\n{"event_'
    records[COMPLETION_LOG_NAME].write_bytes(torn)
    monkeypatch.setattr(backup_service_module, "_RECORD_RETAKE_PAUSE_SECONDS", 0)

    artifact = service.create_backup()

    copy = _records_dir(artifact.snapshot_path) / COMPLETION_LOG_NAME
    assert copy.read_bytes() == torn
    assert artifact.user_records[COMPLETION_LOG_NAME] == {
        "sha256": sha256(torn).hexdigest(),
        "bytes": len(torn),
    }


def test_restore_puts_records_back_and_pre_restore_backup_holds_the_previous_ones(tmp_path):
    service, records = _service(tmp_path)
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"old-addition"}\n')
    records[BASKET_LOG_NAME].write_bytes(b'{"event_id":"old-basket"}\n')
    backup = service.create_backup()
    _set(service.database_path, "current")
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"old-addition"}\n{"event_id":"new"}\n')
    records[BASKET_LOG_NAME].write_bytes(b'{"event_id":"new-basket"}\n')

    applied = _restore(service, backup.snapshot_path)

    assert _value(service.database_path) == "old"
    assert records[ADDITION_LOG_NAME].read_bytes() == b'{"event_id":"old-addition"}\n'
    assert records[BASKET_LOG_NAME].read_bytes() == b'{"event_id":"old-basket"}\n'
    assert not records[COMPLETION_LOG_NAME].exists()
    assert applied.backup_has_user_records is True
    assert applied.records_restored == (ADDITION_LOG_NAME, BASKET_LOG_NAME)
    assert applied.records_left == ()
    assert applied.pre_restore_backup is not None
    previous = _records_dir(applied.pre_restore_backup.snapshot_path)
    assert (previous / ADDITION_LOG_NAME).read_bytes() == (
        b'{"event_id":"old-addition"}\n{"event_id":"new"}\n'
    )
    assert (previous / BASKET_LOG_NAME).read_bytes() == b'{"event_id":"new-basket"}\n'
    assert sorted(path.name for path in records[ADDITION_LOG_NAME].parent.iterdir()) == sorted(
        [records[ADDITION_LOG_NAME].name, records[BASKET_LOG_NAME].name]
    )  # no staged record copies left behind


def test_record_absent_from_backup_is_left_in_place(tmp_path):
    service, records = _service(tmp_path)
    backup = service.create_backup()
    records[COMPLETION_LOG_NAME].write_bytes(b'{"event_id":"made-later"}\n')

    applied = _restore(service, backup.snapshot_path)

    assert records[COMPLETION_LOG_NAME].read_bytes() == b'{"event_id":"made-later"}\n'
    assert applied.records_restored == ()
    assert applied.records_left == (
        (COMPLETION_LOG_NAME, backup_service_module.RECORD_NOT_IN_BACKUP),
    )


def test_backup_from_before_records_leaves_live_records_and_says_so(tmp_path):
    service, records = _service(tmp_path)
    backup = service.create_backup()
    manifest = json.loads(backup.manifest_path.read_text(encoding="utf-8"))
    del manifest["user_records"]
    backup.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"kept"}\n')

    assert service.validate_restore(backup.snapshot_path).includes_user_records is False
    applied = _restore(service, backup.snapshot_path)

    assert records[ADDITION_LOG_NAME].read_bytes() == b'{"event_id":"kept"}\n'
    assert applied.backup_has_user_records is False
    assert applied.records_restored == ()
    assert applied.records_left == (
        (ADDITION_LOG_NAME, backup_service_module.RECORDS_PREDATE_BACKUP),
    )


def test_backup_from_before_the_dilution_log_restores_and_leaves_the_log(tmp_path):
    # Backups made before the prepared-dilution log joined the stock records
    # list only the three older records in their manifest.
    service, records = _service(tmp_path)
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"old-addition"}\n')
    backup = service.create_backup()
    manifest = json.loads(backup.manifest_path.read_text(encoding="utf-8"))
    del manifest["user_records"][DILUTION_LOG_NAME]
    assert set(manifest["user_records"]) == {
        ADDITION_LOG_NAME,
        COMPLETION_LOG_NAME,
        BASKET_LOG_NAME,
    }
    backup.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"new-addition"}\n')
    records[DILUTION_LOG_NAME].write_bytes(b'{"event_id":"dilution-made-later"}\n')

    applied = _restore(service, backup.snapshot_path)

    assert records[ADDITION_LOG_NAME].read_bytes() == b'{"event_id":"old-addition"}\n'
    assert records[DILUTION_LOG_NAME].read_bytes() == b'{"event_id":"dilution-made-later"}\n'
    assert applied.records_restored == (ADDITION_LOG_NAME,)
    assert applied.records_left == (
        (DILUTION_LOG_NAME, backup_service_module.RECORD_NOT_IN_BACKUP),
    )
    validation = service.validate_restore(backup.snapshot_path)
    assert validation.valid, validation.errors
    assert validation.user_records[DILUTION_LOG_NAME] == "not in backup"


def test_manifest_naming_an_unknown_record_is_refused(tmp_path):
    service, _records_by_name = _service(tmp_path)
    backup = service.create_backup()
    manifest = json.loads(backup.manifest_path.read_text(encoding="utf-8"))
    manifest["user_records"]["unknown.jsonl"] = None
    backup.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert "stock records manifest entry is invalid" in (
        service.validate_restore(backup.snapshot_path).errors
    )
    with pytest.raises(RestoreSafetyError, match="manifest entry is invalid"):
        _restore(service, backup.snapshot_path)


def test_damaged_record_copy_is_refused_before_anything_changes(tmp_path):
    service, records = _service(tmp_path)
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"backed-up"}\n')
    backup = service.create_backup()
    _set(service.database_path, "current")
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"live"}\n')
    staged = service.stage_restore(backup.snapshot_path)
    (_records_dir(backup.snapshot_path) / ADDITION_LOG_NAME).write_bytes(b'{"event_id":"xx"}\n')

    assert service.validate_restore(backup.snapshot_path).valid is False
    with pytest.raises(RestoreSafetyError, match="damaged"):
        service.apply_staged_restore(staged, maintenance_mode=True)

    assert _value(service.database_path) == "current"
    assert records[ADDITION_LOG_NAME].read_bytes() == b'{"event_id":"live"}\n'
    assert sorted(path.name for path in service.backup_directory.glob("*.sqlite")) == [
        backup.snapshot_path.name
    ]  # no pre-restore backup either
    assert [path.name for path in records[ADDITION_LOG_NAME].parent.iterdir()] == [
        records[ADDITION_LOG_NAME].name
    ]


def test_missing_live_database_still_gets_safety_copies_of_live_records(tmp_path):
    service, records = _service(tmp_path)
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"backed-up"}\n')
    backup = service.create_backup()
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"live"}\n')
    records[BASKET_LOG_NAME].write_bytes(b'{"event_id":"live-basket"}\n')
    service.database_path.unlink()

    applied = _restore(service, backup.snapshot_path)

    assert applied.pre_restore_backup is None
    assert applied.records_copy is not None
    assert applied.records_copy.parent == service.backup_directory
    assert (applied.records_copy / ADDITION_LOG_NAME).read_bytes() == b'{"event_id":"live"}\n'
    assert (applied.records_copy / BASKET_LOG_NAME).read_bytes() == (
        b'{"event_id":"live-basket"}\n'
    )
    assert records[ADDITION_LOG_NAME].read_bytes() == b'{"event_id":"backed-up"}\n'
    assert records[BASKET_LOG_NAME].read_bytes() == b'{"event_id":"live-basket"}\n'


def _command_records(tmp_path: Path, monkeypatch) -> dict[str, Path]:
    """Point the app's default record locations at ``tmp_path``."""

    folder = tmp_path / "user"
    folder.mkdir()
    monkeypatch.setenv("PERFUME_PERSONAL_INVENTORY_ADDITION_PATH", str(folder / "add.jsonl"))
    monkeypatch.setenv(
        "PERFUME_INVENTORY_COMPLETION_PATH", str(folder / COMPLETION_LOG_NAME)
    )
    return {
        ADDITION_LOG_NAME: folder / "add.jsonl",
        COMPLETION_LOG_NAME: folder / COMPLETION_LOG_NAME,
        BASKET_LOG_NAME: folder / BASKET_LOG_NAME,
        DILUTION_LOG_NAME: folder / DILUTION_LOG_NAME,
    }


def test_restore_command_says_which_stock_records_were_restored(
    tmp_path, monkeypatch, capsys
):
    records = _command_records(tmp_path, monkeypatch)
    database, database_url = _app_database(tmp_path, "old")
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"backed-up"}\n')
    records[COMPLETION_LOG_NAME].write_bytes(b'{"event_id":"details"}\n')
    service = backup_service_module.backup_service_for_database_url(database_url)
    backup = service.create_backup()
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"live"}\n')
    records[BASKET_LOG_NAME].write_bytes(b'{"event_id":"basket"}\n')
    capsys.readouterr()

    code = restore_from_backup(
        backup.snapshot_path.name, database_url=database_url, port=_free_port()
    )

    output = capsys.readouterr().out
    assert code == 0
    assert records[ADDITION_LOG_NAME].read_bytes() == b'{"event_id":"backed-up"}\n'
    assert (
        "Stock records restored: stock you added, stock details you completed." in output
    )
    assert "Left as they are, because this backup has no copy of them: basket choices." in output
    assert "That backup also holds your stock records as they were." in output


def test_restore_command_says_an_older_backup_left_stock_records_alone(
    tmp_path, monkeypatch, capsys
):
    records = _command_records(tmp_path, monkeypatch)
    database, database_url = _app_database(tmp_path, "old")
    artifact = backup_service_module.backup_service_for_database_url(database_url).create_backup()
    manifest = json.loads(artifact.manifest_path.read_text(encoding="utf-8"))
    del manifest["user_records"]
    artifact.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"live"}\n')
    capsys.readouterr()

    code = restore_from_backup(
        artifact.snapshot_path.name, database_url=database_url, port=_free_port()
    )

    assert code == 0
    assert records[ADDITION_LOG_NAME].read_bytes() == b'{"event_id":"live"}\n'
    assert (
        "This backup was made before stock records were included in backups; "
        "your current stock records were left as they are."
    ) in capsys.readouterr().out


def test_restore_command_names_record_safety_copy_when_database_is_missing(
    tmp_path, monkeypatch, capsys
):
    records = _command_records(tmp_path, monkeypatch)
    database, database_url = _app_database(tmp_path, "old")
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"backed-up"}\n')
    backup = backup_service_module.backup_service_for_database_url(database_url).create_backup()
    records[ADDITION_LOG_NAME].write_bytes(b'{"event_id":"live"}\n')
    os.remove(database)
    capsys.readouterr()

    code = restore_from_backup(
        backup.snapshot_path.name, database_url=database_url, port=_free_port()
    )

    output = capsys.readouterr().out
    assert code == 0
    copies = sorted((tmp_path / "lab-backups").glob("stock-records-pre-restore-*"))
    assert len(copies) == 1
    assert (copies[0] / ADDITION_LOG_NAME).read_bytes() == b'{"event_id":"live"}\n'
    assert (
        f"Your stock records as they were before this restore are kept at: {copies[0]}"
        in output
    )
