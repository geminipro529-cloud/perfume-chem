"""Tests for Phase 1A domain foundation migration."""

import sqlite3
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(db_path: Path) -> Config:
    """Create an Alembic config pointing to a test database."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    url = f"sqlite:///{db_path}"
    config.set_main_option("sqlalchemy.url", url)
    return config


def _columns(db_path: Path, table: str) -> set[str]:
    """Get column names for a table in the test database."""
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


class TestPhase1aMigration:
    """Verify the 20260717_0001 migration adds correct columns."""

    @pytest.fixture
    def db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = Path(f.name)
        yield path
        if path.exists():
            path.unlink()

    def test_migration_from_empty(self, db_path):
        """Migration from empty database adds the expected columns."""
        config = _alembic_config(db_path)
        command.upgrade(config, "head")
        cols = _columns(db_path, "lab_formula_components")
        assert "role" in cols, "lab_formula_components should have role column"
        assert "unit" in cols, "lab_formula_components should have unit column"
        stock_cols = _columns(db_path, "lab_stock_solutions")
        assert "remaining_mass_g" in stock_cols, (
            "lab_stock_solutions should have remaining_mass_g column"
        )

    def test_migration_rollback(self, db_path):
        """Migration downgrade removes the expected columns."""
        config = _alembic_config(db_path)
        command.upgrade(config, "head")
        command.downgrade(config, "-1")
        cols = _columns(db_path, "lab_formula_components")
        assert "role" not in cols, "role should be removed after downgrade"
        assert "unit" not in cols, "unit should be removed after downgrade"
        stock_cols = _columns(db_path, "lab_stock_solutions")
        assert "remaining_mass_g" not in stock_cols, (
            "remaining_mass_g should be removed after downgrade"
        )

    def test_migration_idempotent(self, db_path):
        """Running upgrade twice should be safe (no-op second time)."""
        config = _alembic_config(db_path)
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        cols = _columns(db_path, "lab_formula_components")
        assert "role" in cols

    def test_migration_from_current_schema(self, db_path):
        """Migration from existing lab schema adds new columns without removing old ones."""
        config = _alembic_config(db_path)
        # First apply base migration
        command.upgrade(config, "20260716_0001")
        # Verify old columns exist and new ones don't
        cols_before = _columns(db_path, "lab_formula_components")
        assert "role" not in cols_before
        # Apply Phase 1A migration
        command.upgrade(config, "head")
        cols_after = _columns(db_path, "lab_formula_components")
        assert "role" in cols_after
        assert "unit" in cols_after
        # Verify old columns preserved
        assert "id" in cols_after
        assert "formula_version_id" in cols_after
