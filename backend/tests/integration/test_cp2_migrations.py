from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.models.lab_cp2_physical import CP2_PHYSICAL_TABLE_NAMES
from app.models.lab_engine_jobs import CP2_ENGINE_JOB_TABLE_NAMES

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRIOR_HEAD = "20260810_0016"
PHYSICAL_HEAD = "20260923_0017"
CP2_HEAD = "20260923_0018"


def _config(database: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    return config


def _revision(database: Path) -> str:
    with closing(sqlite3.connect(database)) as connection:
        return str(connection.execute("SELECT version_num FROM alembic_version").fetchone()[0])


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


def test_cp2_migrations_are_linear_additive_and_reversible(tmp_path: Path) -> None:
    database = tmp_path / "cp2.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    tables_before = _tables(database)

    command.upgrade(config, CP2_HEAD)
    assert _revision(database) == CP2_HEAD
    assert tables_before <= _tables(database)
    assert CP2_PHYSICAL_TABLE_NAMES <= _tables(database)
    assert CP2_ENGINE_JOB_TABLE_NAMES <= _tables(database)
    for table in CP2_PHYSICAL_TABLE_NAMES | CP2_ENGINE_JOB_TABLE_NAMES:
        assert f"trg_{table}_update_append_only" in _triggers(database)
        assert f"trg_{table}_delete_append_only" in _triggers(database)

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD
    assert _tables(database) == tables_before


def test_cp2_revision_chain_is_exact() -> None:
    physical = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260923_0017_cp2_physical_lineage.py"
    ).read_text(encoding="utf-8")
    jobs = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260923_0018_cp2_engine_jobs.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "20260923_0017"' in physical
    assert 'down_revision: str | None = "20260810_0016"' in physical
    assert 'revision: str = "20260923_0018"' in jobs
    assert 'down_revision: str | None = "20260923_0017"' in jobs
    assert "Base.metadata" not in physical + jobs
    assert "app.models" not in physical + jobs
