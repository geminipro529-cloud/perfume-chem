from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PRIOR_HEAD = "20260927_0020"
CP18_HEAD = "20260927_0021"


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


def _objects(database: Path, object_type: str) -> set[str]:
    with closing(sqlite3.connect(database)) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = ?", (object_type,)
            )
        }


def test_stock_lot_receipt_migration_is_linear_append_only_and_reversible(
    tmp_path: Path,
) -> None:
    database = tmp_path / "cp18-stock-lot.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    command.upgrade(config, CP18_HEAD)
    assert _revision(database) == CP18_HEAD
    assert "lab_stock_lot_physical_receipts" in _objects(database, "table")
    triggers = _objects(database, "trigger")
    assert "trg_lab_stock_lot_physical_receipts_update_append_only" in triggers
    assert "trg_lab_stock_lot_physical_receipts_delete_append_only" in triggers

    command.downgrade(config, PRIOR_HEAD)
    assert _revision(database) == PRIOR_HEAD
    assert "lab_stock_lot_physical_receipts" not in _objects(database, "table")


def test_cp18_revision_chain_is_exact_and_model_independent() -> None:
    migration = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260927_0021_cp18_stock_lot_receipts.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "20260927_0021"' in migration
    assert 'down_revision: str | None = "20260927_0020"' in migration
    assert "Base.metadata" not in migration
    assert "app.models" not in migration
