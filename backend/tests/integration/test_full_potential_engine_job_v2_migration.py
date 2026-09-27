from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRIOR_HEAD = "20260927_0019"
V2_HEAD = "20260927_0020"


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


def test_v2_registry_migration_is_linear_reversible_and_preserves_append_only(
    tmp_path: Path,
) -> None:
    database = tmp_path / "engine-job-v2.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    command.upgrade(config, V2_HEAD)
    assert _revision(database) == V2_HEAD
    sql = _job_table_sql(database)
    for job_type in (
        "RELEASE_SIMULATION",
        "CANDIDATE_EVALUATION",
        "MODEL_BENCHMARK",
        "PREFERENCE_ANALYSIS",
    ):
        assert job_type in sql
    assert "trg_lab_engine_jobs_update_append_only" in _triggers(database)
    assert "trg_lab_engine_jobs_delete_append_only" in _triggers(database)

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD
    sql = _job_table_sql(database)
    assert "RELEASE_SIMULATION" not in sql
    assert "FORMULA_ANALYSIS" in sql


def test_v2_revision_chain_is_exact_and_model_independent() -> None:
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260927_0020_full_potential_engine_job_v2.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "20260927_0020"' in migration
    assert 'down_revision: str | None = "20260927_0019"' in migration
    assert "Base.metadata" not in migration
    assert "app.models" not in migration
