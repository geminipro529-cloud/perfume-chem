"""Checkpoint 16 instrumental observation migration lifecycle."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRIOR_HEAD = "20260927_0021"
CP16_HEAD = "20260927_0022"
TABLE = "lab_instrumental_observations"


def _config(database: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    return config


def _revision(database: Path) -> str:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        assert row is not None
        return str(row[0])


def _objects(database: Path, kind: str) -> set[str]:
    with closing(sqlite3.connect(database)) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = ?", (kind,)
            )
        }


def test_instrumental_observation_migration_is_linear_append_only_and_reversible(
    tmp_path: Path,
) -> None:
    database = tmp_path / "cp16-instrumental.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    command.upgrade(config, CP16_HEAD)
    assert _revision(database) == CP16_HEAD
    assert TABLE in _objects(database, "table")
    triggers = _objects(database, "trigger")
    assert f"trg_{TABLE}_update_append_only" in triggers
    assert f"trg_{TABLE}_delete_append_only" in triggers

    def digest(character: str) -> str:
        return character * 64

    row = {
        "id": "observation-record-1",
        "created_at": "2026-09-27 00:00:00",
        "schema_version": "lab-instrumental-observation-record-v1",
        "observation_id": "observation-1",
        "requester_scope": "migration-test",
        "formula_sha256": digest("1"),
        "inventory_sha256": digest("2"),
        "stock_lot_bundle_sha256": digest("3"),
        "preparation_receipt_sha256": digest("4"),
        "release_scenario_sha256": digest("5"),
        "deposit_decimal_text": "0.1",
        "deposit_unit": "g",
        "matrix_id": "matrix",
        "substrate": "GLASS",
        "temperature_k_decimal_text": "298.15",
        "relative_humidity_decimal_text": "0.5",
        "airflow_m_s_decimal_text": "0.1",
        "surface_area_m2_decimal_text": "0.001",
        "delivery_geometry_id": "geometry",
        "sampling_method_id": "method",
        "instrument_id": "instrument",
        "calibration_receipt_sha256": digest("6"),
        "blank_receipt_sha256": digest("7"),
        "time_seconds_decimal_text": "300",
        "replicate_id": "replicate",
        "session_id": "session",
        "raw_data_sha256": digest("8"),
        "processed_result_sha256": digest("9"),
        "protocol_deviations_json": json.dumps([]),
        "review_state": "UNREVIEWED",
        "payload_json": json.dumps({}),
        "idempotency_key_sha256": digest("a"),
        "command_sha256": digest("b"),
        "record_sha256": digest("c"),
        "review_note": None,
        "processing_allowed": 0,
        "scientific_authority": 0,
        "model_calibration_authority": 0,
        "release_authority": 0,
        "safety_authority": 0,
        "compounding_authority": 0,
        "evidence_admission_authorized": 0,
    }
    with closing(sqlite3.connect(database)) as connection:
        columns = ", ".join(row)
        placeholders = ", ".join("?" for _ in row)
        connection.execute(
            f"INSERT INTO {TABLE} ({columns}) VALUES ({placeholders})",
            tuple(row.values()),
        )
        connection.commit()
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            connection.execute(
                f"UPDATE {TABLE} SET instrument_id = 'changed' WHERE id = ?",
                (row["id"],),
            )
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            connection.execute(f"DELETE FROM {TABLE} WHERE id = ?", (row["id"],))

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD
    assert TABLE not in _objects(database, "table")


def test_instrumental_observation_revision_chain_is_exact_and_model_independent() -> None:
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260927_0022_instrumental_observations.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "20260927_0022"' in migration
    assert 'down_revision: str | None = "20260927_0021"' in migration
    assert "Base.metadata" not in migration
    assert "app.models" not in migration
