import hashlib
import re
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import CheckConstraint

from alembic import command
from app.models.lab_backfill import (
    LabBackfillCampaignVersion,
    LabBackfillDashboardCell,
    LabBackfillGapItem,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B7_HEAD = "20260731_0011"
B8_HEAD = "20260731_0012"
B8_MODELS = (
    LabBackfillCampaignVersion,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
    LabBackfillGapItem,
    LabBackfillDashboardCell,
)
B8_TABLES = {model.__tablename__ for model in B8_MODELS}


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
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _table_state(
    connection: sqlite3.Connection,
    table_names: set[str],
) -> dict[str, tuple[int, str]]:
    state = {}
    for table_name in sorted(table_names):
        columns = tuple(
            str(row[1])
            for row in connection.execute(
                f'PRAGMA table_info("{table_name}")'
            )
        )
        rows = connection.execute(
            f'SELECT * FROM "{table_name}" ORDER BY rowid'
        ).fetchall()
        state[table_name] = (
            len(rows),
            hashlib.sha256(repr((columns, rows)).encode()).hexdigest(),
        )
    return state


def _insert_material(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_materials (
            id, created_at, canonical_name, cas_number, original_payload_json
        ) VALUES (
            'b8-material', CURRENT_TIMESTAMP, 'B8 material', NULL, '{}'
        )
        """
    )


def _insert_stock_solution(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_stock_solutions (
            id, created_at, material_id, supplier, lot_number,
            active_fraction, fraction_basis, density_g_ml, solvent_name,
            initial_mass_g, remaining_mass_g, source_json
        ) VALUES (
            'b8-stock', CURRENT_TIMESTAMP, 'b8-material', 'test', 'lot-b8',
            1.0, 'mass_fraction', NULL, NULL, 1.0, 1.0, '{}'
        )
        """
    )


def _insert_campaign(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_backfill_campaign_versions (
            id, created_at, campaign_key, version_number, parent_version_id,
            name, purpose, as_of_utc, priority_policy_version,
            priority_policy_json, priority_policy_sha256,
            input_snapshot_sha256, material_count, signal_count, gap_count,
            dashboard_cell_count, accepted_exact_count,
            accepted_scoped_count, weak_count, conflicted_count,
            unknown_count, missing_count, not_applicable_count,
            release_authority, reviewer_pseudonym, reviewed_at,
            content_sha256, parent_sha256
        ) VALUES (
            'b8-campaign', CURRENT_TIMESTAMP, 'b8-campaign-key', 1, NULL,
            'B8 campaign', 'test', CURRENT_TIMESTAMP, 'b8-priority-v1',
            '{}', ?, ?, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0,
            'reviewer', CURRENT_TIMESTAMP, ?, NULL
        )
        """,
        ("a" * 64, "b" * 64, "c" * 64),
    )


def _insert_priority(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_backfill_material_priorities (
            id, created_at, campaign_version_id, material_id, rank,
            primary_priority_class, signal_vector_json, rank_key_json,
            rank_key_sha256, critical_unresolved_gap_count,
            total_unresolved_gap_count, source_references_json,
            content_sha256
        ) VALUES (
            'b8-priority', CURRENT_TIMESTAMP, 'b8-campaign', 'b8-material', 1,
            'UNPRIORITIZED', '{}', '[]', ?, 1, 1, '[]', ?
        )
        """,
        ("d" * 64, "e" * 64),
    )


def _insert_signal(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_backfill_priority_signal_links (
            id, created_at, material_priority_id, position,
            signal_type, evidence_class, stock_solution_id,
            formula_component_id, oav_assessment_id, knowledge_rule_id,
            regulatory_snapshot_version_id, analytical_sequence_entry_id,
            composition_entry_id, prediction_id, signal_value_json,
            applicability_json, limitations_json, upstream_content_sha256,
            content_sha256
        ) VALUES (
            'b8-signal', CURRENT_TIMESTAMP, 'b8-priority', 1,
            'CURRENT_INVENTORY', 'UNKNOWN', 'b8-stock',
            NULL, NULL, NULL, NULL, NULL, NULL, NULL, '{}', '{}', '[]', ?, ?
        )
        """,
        ("8" * 64, "9" * 64),
    )


def _insert_gap(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_backfill_gap_items (
            id, created_at, material_priority_id, position,
            requirement_type, state, evidence_class,
            claim_authority_version_id, applicability_scope_json,
            applicability_scope_sha256, conflicts_json, conflict_count,
            missing_requirements_json, missing_requirement_count,
            source_references_json, upstream_content_sha256, content_sha256
        ) VALUES (
            'b8-gap', CURRENT_TIMESTAMP, 'b8-priority', 1,
            'EXACT_IDENTITY', 'MISSING', 'UNKNOWN', NULL, '{}', ?,
            '[]', 0, '["exact identity"]', 1, '[]', NULL, ?
        )
        """,
        ("f" * 64, "1" * 64),
    )


def _insert_dashboard(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_backfill_dashboard_cells (
            id, created_at, campaign_version_id, dimension, dimension_key,
            material_count, requirements_total, accepted_exact_count,
            accepted_scoped_count, weak_count, conflicted_count,
            unknown_count, missing_count, not_applicable_count,
            content_sha256
        ) VALUES (
            'b8-dashboard', CURRENT_TIMESTAMP, 'b8-campaign',
            'PROPERTY', 'EXACT_IDENTITY', 1, 1, 0, 0, 0, 0, 0, 1, 0, ?
        )
        """,
        ("2" * 64,),
    )


def test_b8_migration_adds_five_empty_tables_without_changing_prior_rows(
    tmp_path,
):
    database = tmp_path / "b8-empty.db"
    config = _config(database)
    command.upgrade(config, B7_HEAD)
    with sqlite3.connect(database) as connection:
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B8_HEAD)

    with sqlite3.connect(database) as connection:
        assert B8_TABLES <= _tables(connection)
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B8_HEAD,)
        assert {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in B8_TABLES
        } == {table: 0 for table in B8_TABLES}
        assert _table_state(connection, prior_tables) == prior_state
        triggers = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        for table in B8_TABLES:
            assert f"trg_{table}_no_update" in triggers
            assert f"trg_{table}_no_delete" in triggers
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_b8_migration_downgrades_only_b8_and_reupgrades_empty(tmp_path):
    database = tmp_path / "b8-roundtrip.db"
    config = _config(database)
    command.upgrade(config, B7_HEAD)
    with sqlite3.connect(database) as connection:
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B8_HEAD)
    command.downgrade(config, B7_HEAD)

    with sqlite3.connect(database) as connection:
        assert not (B8_TABLES & _tables(connection))
        assert _table_state(connection, prior_tables) == prior_state
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B7_HEAD,)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    command.upgrade(config, B8_HEAD)
    with sqlite3.connect(database) as connection:
        assert B8_TABLES <= _tables(connection)
        assert all(
            connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            == 0
            for table in B8_TABLES
        )


def test_b8_database_guards_shapes_reconciliation_and_append_only(tmp_path):
    database = tmp_path / "b8-constraints.db"
    config = _config(database)
    command.upgrade(config, B8_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_material(connection)
        _insert_stock_solution(connection)
        _insert_campaign(connection)
        _insert_priority(connection)
        _insert_signal(connection)
        _insert_gap(connection)
        _insert_dashboard(connection)
        connection.commit()

        for table_name in B8_TABLES:
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f'UPDATE "{table_name}" SET id=id WHERE id=('
                    f'SELECT id FROM "{table_name}" LIMIT 1)'
                )
            connection.rollback()
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f'DELETE FROM "{table_name}" WHERE id=('
                    f'SELECT id FROM "{table_name}" LIMIT 1)'
                )
            connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_backfill_signal_shape",
        ):
            connection.execute(
                """
                INSERT INTO lab_backfill_priority_signal_links (
                    id, created_at, material_priority_id, position,
                    signal_type, evidence_class, signal_value_json,
                    applicability_json, limitations_json,
                    upstream_content_sha256, content_sha256
                ) VALUES (
                    'b8-bad-signal', CURRENT_TIMESTAMP, 'b8-priority', 1,
                    'CURRENT_INVENTORY', 'UNKNOWN', '{}', '{}', '[]', ?, ?
                )
                """,
                ("3" * 64, "4" * 64),
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_backfill_gap_authority_shape",
        ):
            connection.execute(
                """
                INSERT INTO lab_backfill_gap_items (
                    id, created_at, material_priority_id, position,
                    requirement_type, state, evidence_class,
                    claim_authority_version_id, applicability_scope_json,
                    applicability_scope_sha256, conflicts_json,
                    conflict_count, missing_requirements_json,
                    missing_requirement_count, source_references_json,
                    upstream_content_sha256, content_sha256
                ) VALUES (
                    'b8-bad-gap', CURRENT_TIMESTAMP, 'b8-priority', 2,
                    'DENSITY', 'ACCEPTED_EXACT', 'MEASURED', NULL, '{}', ?,
                    '[]', 0, '[]', 0, '[]', NULL, ?
                )
                """,
                ("5" * 64, "6" * 64),
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_backfill_dashboard_reconciliation",
        ):
            connection.execute(
                """
                INSERT INTO lab_backfill_dashboard_cells (
                    id, created_at, campaign_version_id, dimension,
                    dimension_key, material_count, requirements_total,
                    accepted_exact_count, accepted_scoped_count, weak_count,
                    conflicted_count, unknown_count, missing_count,
                    not_applicable_count, content_sha256
                ) VALUES (
                    'b8-bad-dashboard', CURRENT_TIMESTAMP, 'b8-campaign',
                    'PROPERTY', 'DENSITY', 1, 2, 0, 0, 0, 0, 0, 1, 0, ?
                )
                """,
                ("7" * 64,),
            )


def test_b8_migration_matches_models_columns_checks_indexes_and_fks(tmp_path):
    database = tmp_path / "b8-parity.db"
    config = _config(database)
    command.upgrade(config, B8_HEAD)

    with sqlite3.connect(database) as connection:
        for model in B8_MODELS:
            table_name = model.__tablename__
            assert {
                str(row[1])
                for row in connection.execute(
                    f'PRAGMA table_info("{table_name}")'
                )
            } == {column.name for column in model.__table__.columns}

            assert {
                str(row[1])
                for row in connection.execute(
                    f'PRAGMA index_list("{table_name}")'
                )
                if str(row[1]).startswith("ix_")
            } == {index.name for index in model.__table__.indexes}

            create_sql = connection.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()[0]
            assert set(
                re.findall(
                    r"CONSTRAINT\s+([A-Za-z0-9_]+)\s+CHECK",
                    create_sql,
                    flags=re.IGNORECASE,
                )
            ) == {
                constraint.name
                for constraint in model.__table__.constraints
                if isinstance(constraint, CheckConstraint)
            }


def test_b8_migration_is_explicit_and_imports_zero_prior_rows():
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260731_0012_b8_prioritized_backfill.py"
    )
    source = migration_path.read_text(encoding="utf-8")
    lowered = source.casefold()

    assert "app.models" not in lowered
    assert "base.metadata" not in lowered
    assert "checkfirst" not in lowered
    assert "bulk_insert" not in lowered
    for table_name in B8_TABLES:
        assert table_name in source
        assert f"insert into {table_name}" not in lowered
