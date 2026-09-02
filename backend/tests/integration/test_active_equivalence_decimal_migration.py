import sqlite3

import pytest

from alembic import command
from tests.integration.test_a2_planning_migration import (
    _config,
    _integrity,
    _revision,
)

PRIOR_HEAD = "20260810_0013"
DECIMAL_HEAD = "20260810_0014"


def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table_name}")')
    }


def _insert_legacy_formula_rows(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO lab_materials (id, canonical_name, created_at) "
        "VALUES ('material-decimal-legacy', 'Legacy Decimal Material', CURRENT_TIMESTAMP)"
    )
    connection.execute(
        """
        INSERT INTO lab_stock_solutions (
            id, material_id, active_fraction, fraction_basis,
            initial_mass_g, remaining_mass_g, source_json, created_at
        ) VALUES (
            'stock-decimal-legacy', 'material-decimal-legacy', 0.1,
            'mass_fraction', 10.0, 10.0, '{}', CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        "INSERT INTO lab_formulas (id, name, created_at) "
        "VALUES ('formula-decimal-legacy', 'Legacy Decimal Formula', CURRENT_TIMESTAMP)"
    )
    connection.execute(
        """
        INSERT INTO lab_formula_versions (
            id, formula_id, version_number, brief_json, constraints_json,
            source_json, created_at
        ) VALUES (
            'version-decimal-legacy', 'formula-decimal-legacy', 1,
            '{}', '{}', '{}', CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO lab_formula_components (
            id, formula_version_id, stock_solution_id, position,
            requested_mass_g, role, unit, created_at
        ) VALUES (
            'component-decimal-legacy', 'version-decimal-legacy',
            'stock-decimal-legacy', 1, 1.25, 'heart', 'g', CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def test_decimal_migration_preserves_legacy_unknown_and_append_only_guard(tmp_path):
    database = tmp_path / "active-equivalence-decimal.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_legacy_formula_rows(connection)

    command.upgrade(config, DECIMAL_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert "active_fraction_decimal_text" in _columns(
            connection,
            "lab_stock_solutions",
        )
        assert "requested_mass_g_decimal_text" in _columns(
            connection,
            "lab_formula_components",
        )
        assert connection.execute(
            "SELECT active_fraction_decimal_text FROM lab_stock_solutions "
            "WHERE id='stock-decimal-legacy'"
        ).fetchone()[0] is None
        assert connection.execute(
            "SELECT requested_mass_g_decimal_text FROM lab_formula_components "
            "WHERE id='component-decimal-legacy'"
        ).fetchone()[0] is None
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_formula_components "
                "SET requested_mass_g_decimal_text='1.25' "
                "WHERE id='component-decimal-legacy'"
            )
        connection.rollback()
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    assert _revision(database) == DECIMAL_HEAD
    assert _integrity(database) == "ok"


def test_decimal_migration_downgrades_and_reupgrades_without_inference(tmp_path):
    database = tmp_path / "active-equivalence-decimal-roundtrip.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        _insert_legacy_formula_rows(connection)
    command.upgrade(config, DECIMAL_HEAD)

    command.downgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        assert "active_fraction_decimal_text" not in _columns(
            connection,
            "lab_stock_solutions",
        )
        assert "requested_mass_g_decimal_text" not in _columns(
            connection,
            "lab_formula_components",
        )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_formula_components SET requested_mass_g=2.0 "
                "WHERE id='component-decimal-legacy'"
            )
        connection.rollback()

    command.upgrade(config, DECIMAL_HEAD)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT active_fraction_decimal_text FROM lab_stock_solutions "
            "WHERE id='stock-decimal-legacy'"
        ).fetchone()[0] is None
        assert connection.execute(
            "SELECT requested_mass_g_decimal_text FROM lab_formula_components "
            "WHERE id='component-decimal-legacy'"
        ).fetchone()[0] is None
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    assert _revision(database) == DECIMAL_HEAD
    assert _integrity(database) == "ok"
