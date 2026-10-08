"""The app start copies personal stock records from output/ into data/user/."""

from pathlib import Path

import engine.inventory_completions as completions
import engine.personal_inventory as personal
import engine.user_records as user_records
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app import db_bootstrap


def _point_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    new, old = tmp_path / "data" / "user", tmp_path / "output"
    old.mkdir(parents=True)
    monkeypatch.delenv(personal.ADDITION_PATH_ENV, raising=False)
    monkeypatch.delenv(completions.COMPLETION_PATH_ENV, raising=False)
    monkeypatch.setattr(personal, "DEFAULT_ADDITION_PATH", new / user_records.ADDITION_LOG_NAME)
    monkeypatch.setattr(personal, "LEGACY_ADDITION_PATH", old / user_records.ADDITION_LOG_NAME)
    monkeypatch.setattr(
        completions, "DEFAULT_COMPLETION_PATH", new / user_records.COMPLETION_LOG_NAME
    )
    monkeypatch.setattr(
        completions, "LEGACY_COMPLETION_PATH", old / user_records.COMPLETION_LOG_NAME
    )
    database_url = "sqlite+aiosqlite:///" + (tmp_path / "lab.db").as_posix()
    monkeypatch.setattr(main_module.settings, "DATABASE_URL", database_url)
    monkeypatch.setattr(db_bootstrap, "upgrade_database", lambda _config: None)
    return new, old


def test_app_start_copies_legacy_records_into_data_user(tmp_path, monkeypatch):
    new, old = _point_at(tmp_path, monkeypatch)
    records = {
        user_records.ADDITION_LOG_NAME: b'{"event_id":"addition"}\n',
        user_records.COMPLETION_LOG_NAME: b'{"event_id":"details"}\n',
        user_records.BASKET_LOG_NAME: b'{"event_id":"basket"}\n',
    }
    for name, data in records.items():
        (old / name).write_bytes(data)

    with TestClient(main_module.app) as client:
        assert client.get("/health").status_code == 200
        for name, data in records.items():
            assert (new / name).read_bytes() == data

    for name, data in records.items():
        assert (old / name).read_bytes() == data


def test_app_start_stops_when_a_record_cannot_be_copied(tmp_path, monkeypatch):
    new, old = _point_at(tmp_path, monkeypatch)
    (old / user_records.ADDITION_LOG_NAME).mkdir()  # unreadable as a file

    with pytest.raises(RuntimeError) as raised:
        with TestClient(main_module.app):
            pass

    message = str(raised.value)
    assert str(old / user_records.ADDITION_LOG_NAME) in message
    assert str((new / user_records.ADDITION_LOG_NAME).resolve()) in message
