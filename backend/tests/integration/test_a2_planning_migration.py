import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from tests.unit.test_a2_planning_schema import PLANNING_TABLES

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RELEASED_HEAD = "20260717_0001"
A2_HEAD = "20260730_0001"


def _config(database: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    return config


def _revision(database: Path) -> str:
    with sqlite3.connect(database) as connection:
        return str(
            connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        )


def _tables(database: Path) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def _integrity(database: Path) -> str:
    with sqlite3.connect(database) as connection:
        return str(connection.execute("PRAGMA integrity_check").fetchone()[0])


def _insert_representative_lab_rows(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO lab_materials (id, canonical_name, created_at) VALUES (?, ?, ?)",
            ("released-material", "Released iris", "2026-07-30T00:00:00+00:00"),
        )
        connection.execute(
            """
            INSERT INTO lab_stock_solutions (
                id, material_id, active_fraction, fraction_basis,
                initial_mass_g, remaining_mass_g, source_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "released-stock",
                "released-material",
                0.1,
                "mass_fraction",
                10.0,
                10.0,
                "{}",
                "2026-07-30T00:00:00+00:00",
            ),
        )
        connection.commit()


def _representative_rows(database: Path) -> list[tuple]:
    with sqlite3.connect(database) as connection:
        return list(
            connection.execute(
                """
                SELECT m.id, m.canonical_name, s.id, s.initial_mass_g
                FROM lab_materials AS m
                JOIN lab_stock_solutions AS s ON s.material_id = m.id
                ORDER BY m.id
                """
            )
        )


def _create_legacy_material(database: Path, name: str) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE materials (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO materials (name) VALUES (?)", (name,))
        connection.commit()


def _legacy_material(database: Path) -> str:
    with sqlite3.connect(database) as connection:
        return str(connection.execute("SELECT name FROM materials").fetchone()[0])


def _minimum_rows(connection: sqlite3.Connection) -> None:
    timestamp = "2026-07-30T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO lab_evidence_records (
            id, claim_key, classification, source_locator,
            assumptions_json, limitations_json, created_at
        ) VALUES ('evidence-1', 'a2:test', 'EXACT', 'test://a2', '[]', '[]', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        "INSERT INTO lab_materials (id, canonical_name, created_at) VALUES "
        "('material-1', 'Jasmine Absolute', ?)",
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_stock_solutions (
            id, material_id, active_fraction, fraction_basis,
            initial_mass_g, remaining_mass_g, source_json, created_at
        ) VALUES (
            'stock-1', 'material-1', 0.1, 'mass_fraction',
            10.0, 10.0, '{}', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        "INSERT INTO lab_formulas (id, name, created_at) VALUES "
        "('formula-1', 'A2 formula', ?)",
        (timestamp,),
    )
    connection.executemany(
        """
        INSERT INTO lab_formula_versions (
            id, formula_id, version_number, brief_json,
            constraints_json, source_json, created_at
        ) VALUES (?, 'formula-1', ?, '{}', '{}', '{}', ?)
        """,
        [
            ("formula-version-1", 1, timestamp),
            ("formula-version-2", 2, timestamp),
        ],
    )
    connection.execute(
        """
        INSERT INTO lab_target_hypothesis_versions (
            id, target_id, version_number, schema_version, product_key,
            author, provenance_activity_json, uncertainty_summary_json,
            rationale, content_sha256, created_at
        ) VALUES (
            'target-version-1', 'target-1', 1, 'a2-target-v1',
            'reference:jasmine', 'Sol', '{}', '{}',
            'Initial target', ?, ?
        )
        """,
        ("1" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_target_lines (
            id, line_id, target_hypothesis_version_id, position,
            target_identity, source_name, grade, presence_probability,
            target_raw_quantity, target_active_quantity, unit,
            concentration_fraction, concentration_basis,
            functional_roles_json, uncertainty_json, created_at
        ) VALUES (
            'target-line-row-1', 'target-line-1', 'target-version-1', 1,
            'Jasmine Absolute', 'Reference', 'absolute', 0.95,
            1.0, 0.1, 'g', 0.1, 'mass_fraction', '[]', '{}', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_target_evidence_links (
            id, target_hypothesis_version_id, target_line_id,
            evidence_record_id, created_at
        ) VALUES (
            'target-evidence-1', 'target-version-1', 'target-line-row-1',
            'evidence-1', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_accepted_target_versions (
            id, accepted_target_id, version_number,
            target_hypothesis_version_id, reviewer, rationale,
            content_sha256, created_at
        ) VALUES (
            'acceptance-version-1', 'acceptance-1', 1,
            'target-version-1', 'Sol', 'Accepted', ?, ?
        )
        """,
        ("2" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_formula_version_edges (
            id, child_version_id, parent_version_id, relationship_kind,
            change_json, rationale, content_sha256, created_at
        ) VALUES (
            'formula-edge-1', 'formula-version-2', 'formula-version-1',
            'DERIVED_FROM', '{}', 'Revision', ?, ?
        )
        """,
        ("3" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_inventory_mapping_versions (
            id, mapping_id, version_number, target_line_id,
            stock_solution_id, target_identity, build_identity,
            identity_status, inventory_status, substitution_class,
            preserved_functions_json, lost_functions_json, confidence,
            rationale, content_sha256, created_at
        ) VALUES (
            'mapping-version-1', 'mapping-1', 1, 'target-line-row-1',
            'stock-1', 'Jasmine Absolute', 'Jasmine Absolute',
            'EXACT', 'EXACT_LOT_AVAILABLE', 'EXACT',
            '[]', '[]', 1.0, 'Exact lot', ?, ?
        )
        """,
        ("4" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_inventory_mapping_evidence_links (
            id, inventory_mapping_version_id, evidence_record_id, created_at
        ) VALUES ('mapping-evidence-1', 'mapping-version-1', 'evidence-1', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_build_plan_versions (
            id, plan_id, version_number, schema_version,
            target_hypothesis_version_id, accepted_target_version_id,
            status, author, provenance_activity_json,
            inventory_snapshot_ref, content_sha256,
            uncertainty_summary_json, rationale, created_at
        ) VALUES (
            'build-plan-version-1', 'plan-1', 1, 'a2-build-plan-v1',
            'target-version-1', 'acceptance-version-1',
            'APPROVED', 'Sol', '{}', 'inventory-sha256:test',
            ?, '{}', 'Approved plan', ?
        )
        """,
        ("5" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_build_plan_lines (
            id, line_id, build_plan_version_id, position,
            target_line_id, target_identity, inventory_mapping_version_id,
            stock_solution_id, planned_raw_quantity, planned_active_quantity,
            unit, concentration_fraction, concentration_basis,
            density_g_ml, density_source, standard_uncertainty,
            measurement_method, resolution, expected_transfer_loss,
            substitution_class, preserved_functions_json, lost_functions_json,
            rationale, reservation_state, execution_state, created_at
        ) VALUES (
            'build-line-row-1', 'build-line-1', 'build-plan-version-1', 1,
            'target-line-row-1', 'Jasmine Absolute', 'mapping-version-1',
            'stock-1', 1.0, 0.1, 'g', 0.1, 'mass_fraction',
            1.0, 'lot record', 0.01, 'gravimetric', 0.001, 0.01,
            'EXACT', '[]', '[]', 'Exact lot', 'UNRESERVED', 'PLANNED', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_build_plan_evidence_links (
            id, build_plan_version_id, build_plan_line_id,
            evidence_record_id, created_at
        ) VALUES (
            'build-evidence-1', 'build-plan-version-1', 'build-line-row-1',
            'evidence-1', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_inventory_reservation_events (
            id, reservation_id, sequence, build_plan_version_id,
            build_plan_line_id, stock_solution_id, state, reserved_mass_g,
            idempotency_key, command_sha256, actor, rationale, created_at
        ) VALUES (
            'reservation-event-1', 'reservation-1', 1,
            'build-plan-version-1', 'build-line-row-1', 'stock-1',
            'RESERVED', 1.0, 'idempotency-1', ?, 'Sol', 'Reserve', ?
        )
        """,
        ("6" * 64, timestamp),
    )


def test_a2_planning_migration_upgrades_empty_database(tmp_path):
    database = tmp_path / "empty.db"
    command.upgrade(_config(database), A2_HEAD)
    assert _revision(database) == A2_HEAD
    assert PLANNING_TABLES <= _tables(database)
    assert _integrity(database) == "ok"


def test_a2_planning_migration_upgrades_released_schema_copy(tmp_path):
    database = tmp_path / "released.db"
    config = _config(database)
    command.upgrade(config, RELEASED_HEAD)
    _insert_representative_lab_rows(database)
    before = _representative_rows(database)
    command.upgrade(config, A2_HEAD)
    assert _representative_rows(database) == before
    assert _revision(database) == A2_HEAD


def test_a2_planning_migration_downgrades_to_released_head(tmp_path):
    database = tmp_path / "rollback.db"
    config = _config(database)
    command.upgrade(config, A2_HEAD)
    command.downgrade(config, RELEASED_HEAD)
    assert not (PLANNING_TABLES & _tables(database))
    assert _revision(database) == RELEASED_HEAD
    assert _integrity(database) == "ok"


def test_a2_planning_migration_preserves_legacy_tables(tmp_path):
    database = tmp_path / "legacy.db"
    _create_legacy_material(database, "legacy orris")
    command.upgrade(_config(database), A2_HEAD)
    assert _legacy_material(database) == "legacy orris"


def test_a2_planning_migration_installs_append_only_guards(tmp_path):
    database = tmp_path / "append-only.db"
    command.upgrade(_config(database), A2_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        connection.commit()
        for table_name in sorted(PLANNING_TABLES):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f"UPDATE {table_name} SET created_at=created_at WHERE id="
                    f"(SELECT id FROM {table_name} LIMIT 1)"
                )
            connection.rollback()
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f"DELETE FROM {table_name} WHERE id="
                    f"(SELECT id FROM {table_name} LIMIT 1)"
                )
            connection.rollback()


def test_a2_planning_database_constraints_reject_invalid_rows(tmp_path):
    database = tmp_path / "constraints.db"
    command.upgrade(_config(database), A2_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        connection.commit()

        invalid_statements = (
            """
            INSERT INTO lab_target_lines (
                id, line_id, target_hypothesis_version_id, position,
                target_identity, source_name, grade, presence_probability,
                target_raw_quantity, target_active_quantity, unit,
                concentration_fraction, concentration_basis,
                functional_roles_json, uncertainty_json, created_at
            ) SELECT
                'bad-target-line', 'bad-target-line', id, 2,
                'Bad', 'Bad', 'bad', 1.1, -1.0, 0.0, 'g',
                0.5, 'mass_fraction', '[]', '{}', created_at
              FROM lab_target_hypothesis_versions LIMIT 1
            """,
            """
            INSERT INTO lab_build_plan_lines (
                id, line_id, build_plan_version_id, position,
                target_line_id, target_identity, inventory_mapping_version_id,
                stock_solution_id, planned_raw_quantity, planned_active_quantity,
                unit, concentration_fraction, concentration_basis,
                measurement_method, resolution, expected_transfer_loss,
                substitution_class, preserved_functions_json, lost_functions_json,
                rationale, reservation_state, execution_state, created_at
            ) SELECT
                'bad-build-line', 'bad-build-line', id, 2,
                'target-line-row-1', 'Bad', 'mapping-version-1', 'stock-1',
                1.0, 0.1, 'g', 0.1, 'mass_fraction',
                'gravimetric', 0.0, -1.0, 'EXACT', '[]', '[]',
                'Bad', 'UNRESERVED', 'PLANNED', created_at
              FROM lab_build_plan_versions LIMIT 1
            """,
            """
            INSERT INTO lab_inventory_reservation_events (
                id, reservation_id, sequence, build_plan_version_id,
                build_plan_line_id, stock_solution_id, state, reserved_mass_g,
                idempotency_key, command_sha256, actor, rationale, created_at
            ) SELECT
                'bad-reservation', 'bad-reservation', 0, id,
                'build-line-row-1', 'stock-1', 'RESERVED', 0,
                'bad-idempotency', 'bad-sha', 'Sol', 'Bad', created_at
              FROM lab_build_plan_versions LIMIT 1
            """,
            """
            INSERT INTO lab_formula_version_edges (
                id, child_version_id, parent_version_id, relationship_kind,
                change_json, rationale, content_sha256, created_at
            ) VALUES (
                'bad-edge', 'formula-version-1', 'formula-version-1',
                'DERIVED_FROM', '{}', 'Bad', 'bad-sha',
                '2026-07-30T00:00:00+00:00'
            )
            """,
            """
            INSERT INTO lab_target_evidence_links (
                id, target_hypothesis_version_id, target_line_id,
                evidence_record_id, created_at
            ) VALUES (
                'bad-membership', 'target-version-1', 'missing-line',
                'evidence-1', '2026-07-30T00:00:00+00:00'
            )
            """,
        )
        for statement in invalid_statements:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)
            connection.rollback()


def test_a2_planning_migration_is_frozen_and_explicit():
    revision_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260730_0001_a2_planning_core.py"
    )
    source = revision_path.read_text(encoding="utf-8")
    assert "app.models" not in source
    assert "Base.metadata" not in source
    assert "checkfirst" not in source
    assert "20260717_0001" in source
    for table_name in PLANNING_TABLES:
        assert table_name in source
