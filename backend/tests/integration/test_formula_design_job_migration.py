"""Durable Formula Studio job-type migration lifecycle."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRIOR_HEAD = "20260928_0023"
CURRENT_HEAD = "20260929_0024"


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


def _job_table_sql(database: Path) -> str:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='lab_engine_jobs'"
        ).fetchone()
        assert row is not None
        return str(row[0])


def _triggers(database: Path) -> set[str]:
    with closing(sqlite3.connect(database)) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }


def _insert_populated_job_graph(database: Path) -> None:
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        hash_a = "a" * 64
        connection.execute(
            """
            INSERT INTO lab_engine_jobs (
                id, created_at, schema_version, contract_version, job_type,
                execution_class, requester_scope, source_request_json,
                normalized_payload_json, source_request_sha256,
                normalized_payload_sha256, implementation_fingerprint_sha256,
                implementation_manifest_json, reference_bundle_sha256,
                inventory_fingerprint_sha256, capability_fingerprint_sha256,
                authority_context_sha256, idempotency_key_sha256, command_sha256,
                job_fingerprint_sha256, timeout_seconds, max_attempts
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "job-populated",
                "2026-09-29 00:00:00",
                "lab-engine-job-request-v2",
                "lab-engine-job-contract-v2",
                "FORMULA_ANALYSIS",
                "READ_ONLY_DIAGNOSTIC",
                "migration-test",
                "{}",
                "{}",
                hash_a,
                hash_a,
                hash_a,
                "{}",
                hash_a,
                hash_a,
                hash_a,
                hash_a,
                hash_a,
                hash_a,
                hash_a,
                90,
                1,
            ),
        )
        connection.execute(
            """
            INSERT INTO lab_engine_job_events (
                id, created_at, job_id, sequence, state, lease_epoch,
                attempt, detail_json, event_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "event-populated",
                "2026-09-29 00:00:00",
                "job-populated",
                1,
                "QUEUED",
                0,
                0,
                "{}",
                "b" * 64,
            ),
        )
        connection.execute(
            """
            INSERT INTO lab_engine_job_results (
                id, created_at, job_id, terminal_state, result_json,
                result_sha256, validation_state, diagnostics_json,
                release_authority, safety_authority, compounding_authority,
                evidence_admission_authorized
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "result-populated",
                "2026-09-29 00:00:00",
                "job-populated",
                "SUCCEEDED",
                "{}",
                "c" * 64,
                "ADVISORY_COMPLETE",
                "{}",
                0,
                0,
                0,
                0,
            ),
        )
        connection.commit()


def test_formula_design_job_migration_is_linear_and_reversible(tmp_path: Path) -> None:
    database = tmp_path / "formula-design-job.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    assert "FORMULA_DESIGN" not in _job_table_sql(database)

    command.upgrade(config, CURRENT_HEAD)
    assert _revision(database) == CURRENT_HEAD
    assert "FORMULA_DESIGN" in _job_table_sql(database)
    assert "trg_lab_engine_jobs_update_append_only" in _triggers(database)
    assert "trg_lab_engine_jobs_delete_append_only" in _triggers(database)

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD
    assert "FORMULA_DESIGN" not in _job_table_sql(database)


def test_formula_design_job_migration_preserves_populated_child_graph(
    tmp_path: Path,
) -> None:
    database = tmp_path / "formula-design-job-populated.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    _insert_populated_job_graph(database)

    command.upgrade(config, CURRENT_HEAD)

    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT count(*) FROM lab_engine_jobs WHERE id = 'job-populated'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM lab_engine_job_events WHERE job_id = 'job-populated'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM lab_engine_job_results WHERE job_id = 'job-populated'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE name LIKE '_alembic_tmp%'"
        ).fetchone() == (0,)

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD


def test_formula_design_job_revision_is_model_independent() -> None:
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260929_0024_formula_design_job.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "20260929_0024"' in migration
    assert 'down_revision: str | None = "20260928_0023"' in migration
    assert "Base.metadata" not in migration
    assert "app.models" not in migration
