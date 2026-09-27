from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.models.lab_external_validation import EXTERNAL_VALIDATION_TABLE_NAMES

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRIOR_HEAD = "20260923_0018"
CP9_HEAD = "20260927_0019"


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


def _tables(database: Path) -> set[str]:
    with closing(sqlite3.connect(database)) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def _triggers(database: Path) -> set[str]:
    with closing(sqlite3.connect(database)) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }


def test_cp9_migration_is_linear_additive_append_only_and_reversible(
    tmp_path: Path,
) -> None:
    database = tmp_path / "cp9.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    tables_before = _tables(database)

    command.upgrade(config, CP9_HEAD)
    assert _revision(database) == CP9_HEAD
    assert tables_before <= _tables(database)
    assert EXTERNAL_VALIDATION_TABLE_NAMES <= _tables(database)
    assert (
        "trg_lab_external_validation_records_update_append_only" in _triggers(database)
    )
    assert (
        "trg_lab_external_validation_records_delete_append_only" in _triggers(database)
    )

    empty_json = json.dumps({}, sort_keys=True)
    digest = "a" * 64
    row = {
        "id": "record-1",
        "created_at": "2026-09-27 00:00:00",
        "schema_version": "lab-external-validation-record-v1",
        "record_kind": "TEMPORAL_OBSERVATION",
        "experiment_id": "experiment-1",
        "primary_application_id": "application-1",
        "secondary_application_id": None,
        "requester_scope": "migration-test",
        "protocol_id": "protocol-v1",
        "endpoint_id": "pleasantness",
        "repeat_id": "repeat-1",
        "time_seconds_decimal_text": "300",
        "presentation_sequence_id": "sequence-1",
        "presentation_position": 1,
        "missingness_state": "OBSERVED",
        "value_decimal_text": "5",
        "preference_outcome": None,
        "missing_reason": None,
        "protocol_snapshot_json": empty_json,
        "sample_snapshot_json": empty_json,
        "condition_snapshot_json": empty_json,
        "order_snapshot_json": empty_json,
        "assessor_snapshot_json": empty_json,
        "provenance_snapshot_json": empty_json,
        "payload_json": empty_json,
        "idempotency_key_sha256": "1" * 64,
        "command_sha256": "2" * 64,
        "canonical_cell_sha256": "3" * 64,
        "protocol_scope_sha256": "4" * 64,
        "sample_scope_sha256": "5" * 64,
        "condition_scope_sha256": "6" * 64,
        "order_scope_sha256": "7" * 64,
        "assessor_scope_sha256": "8" * 64,
        "provenance_scope_sha256": "9" * 64,
        "record_sha256": digest,
        "processing_allowed": 0,
        "scientific_authority": 0,
        "sensory_authority": 0,
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
            f"INSERT INTO lab_external_validation_records ({columns}) "
            f"VALUES ({placeholders})",
            tuple(row.values()),
        )
        connection.commit()
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            connection.execute(
                "UPDATE lab_external_validation_records "
                "SET endpoint_id = 'changed' WHERE id = 'record-1'"
            )
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            connection.execute(
                "DELETE FROM lab_external_validation_records WHERE id = 'record-1'"
            )

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD
    assert _tables(database) == tables_before


def test_cp9_revision_chain_is_exact_and_model_independent() -> None:
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260927_0019_cp9_external_validation_intake.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "20260927_0019"' in migration
    assert 'down_revision: str | None = "20260923_0018"' in migration
    assert "Base.metadata" not in migration
    assert "app.models" not in migration
