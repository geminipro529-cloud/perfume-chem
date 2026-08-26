import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B2_HEAD = "20260730_0006"
B3_HEAD = "20260730_0007"
B3_TABLES = {
    "lab_threshold_observation_contexts",
    "lab_oav_assessments",
    "lab_legacy_threshold_records",
}


def _config(database_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path.as_posix()}",
    )
    return config


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_b3_migration_creates_empty_append_only_authority_tables(tmp_path):
    database = tmp_path / "b3.db"
    config = _config(database)
    command.upgrade(config, B3_HEAD)

    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        assert B3_TABLES <= _tables(connection)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            B3_HEAD,
        )
        assert all(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
            for table in B3_TABLES
        )
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        triggers = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
        for table in B3_TABLES:
            assert f"trg_{table}_no_update" in triggers
            assert f"trg_{table}_no_delete" in triggers
    finally:
        connection.close()


def test_b3_migration_downgrades_to_b2_without_touching_b2_tables(tmp_path):
    database = tmp_path / "b3-downgrade.db"
    config = _config(database)
    command.upgrade(config, B3_HEAD)
    command.downgrade(config, B2_HEAD)

    connection = sqlite3.connect(database)
    try:
        tables = _tables(connection)
        assert not (B3_TABLES & tables)
        assert "lab_property_observations" in tables
        assert "lab_selected_assertions" in tables
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            B2_HEAD,
        )
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        connection.close()


def test_b3_database_guards_legacy_quarantine_and_assessment_shape(tmp_path):
    database = tmp_path / "b3-constraints.db"
    config = _config(database)
    command.upgrade(config, B3_HEAD)

    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute(
            """
            INSERT INTO lab_legacy_threshold_records
            (id, created_at, schema_version, material_key, medium,
             numeric_value, original_unit, verification_status,
             authority_state, source_payload_json, content_sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-1",
                "2026-07-30T00:00:00+00:00",
                "lab-legacy-threshold-v1",
                "linalool",
                "AIR",
                0.51,
                "ppb",
                "DERIVED",
                "LEGACY_CONTEXT_INCOMPLETE",
                "{}",
                "a" * 64,
            ),
        )
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_legacy_threshold_records "
                "SET verification_status='PEER_CROSS' WHERE id='legacy-1'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_legacy_threshold_records
                (id, created_at, schema_version, material_key, medium,
                 numeric_value, original_unit, verification_status,
                 authority_state, source_payload_json, content_sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-upgraded",
                    "2026-07-30T00:00:00+00:00",
                    "lab-legacy-threshold-v1",
                    "linalool",
                    "AIR",
                    0.51,
                    "ppb",
                    "DERIVED",
                    "AUTHORIZED_FOR_SCOPED_PROPERTY",
                    "{}",
                    "b" * 64,
                ),
            )
        connection.rollback()
        assert (
            connection.execute("SELECT COUNT(*) FROM lab_property_observations").fetchone()[0] == 0
        )
        assert connection.execute("SELECT COUNT(*) FROM lab_selected_assertions").fetchone()[0] == 0
    finally:
        connection.close()
