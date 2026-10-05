"""Commercial-reference persistence and job registry migration lifecycle."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRIOR_HEAD = "20260927_0022"
CURRENT_HEAD = "20260928_0023"
TABLE = "lab_commercial_reference_samples"


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


def _job_table_sql(database: Path) -> str:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='lab_engine_jobs'"
        ).fetchone()
        assert row is not None
        return str(row[0])


def test_global_reference_migration_is_linear_append_only_and_reversible(tmp_path: Path) -> None:
    database = tmp_path / "global-reference.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    command.upgrade(config, CURRENT_HEAD)
    assert _revision(database) == CURRENT_HEAD
    assert TABLE in _objects(database, "table")
    assert "REFERENCE_PANEL_EVALUATION" in _job_table_sql(database)
    triggers = _objects(database, "trigger")
    assert f"trg_{TABLE}_update_append_only" in triggers
    assert f"trg_{TABLE}_delete_append_only" in triggers
    assert "trg_lab_engine_jobs_update_append_only" in triggers
    assert "trg_lab_engine_jobs_delete_append_only" in triggers

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD
    assert TABLE not in _objects(database, "table")
    assert "REFERENCE_PANEL_EVALUATION" not in _job_table_sql(database)


def test_global_reference_revision_is_model_independent() -> None:
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260928_0023_global_reference_samples.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "20260928_0023"' in migration
    assert 'down_revision: str | None = "20260927_0022"' in migration
    assert "Base.metadata" not in migration
    assert "app.models" not in migration
