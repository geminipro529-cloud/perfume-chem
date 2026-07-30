import sqlite3
from pathlib import Path

import pytest

from alembic import command
from tests.integration.test_a2_planning_migration import (
    _config,
    _integrity,
    _minimum_rows,
    _revision,
)
from tests.integration.test_b1_source_migration import _insert_b1_rows
from tests.unit.test_b2_property_schema import B2_TABLES

B1_HEAD = "20260730_0005"
B2_HEAD = "20260730_0006"
LEGACY_AUTHORITY_REASON = (
    "Pre-B2 scalar property without canonical observation lineage."
)


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
        )
    }


def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table_name}")')
    }


def _insert_legacy_property(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_material_properties (
            id, material_id, property_key, value, unit, conditions_json,
            standard_uncertainty, evidence_id, created_at
        ) VALUES (
            'legacy-property-1', 'material-1', 'vapor_pressure', 7.0, 'Pa',
            '{}', 0.5, 'evidence-1', '2026-07-30T00:00:00+00:00'
        )
        """
    )


def _insert_b2_rows(connection: sqlite3.Connection) -> None:
    timestamp = "2026-07-30T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO lab_property_observations (
            id, schema_version, identity_scope, subject_identity_json,
            subject_identity_sha256, property_type, value_kind,
            numeric_value, original_unit, canonical_unit, method,
            source_version_id, extraction_record_id, source_locator_json,
            replicate_count, statistic, uncertainty_interval_json,
            evidence_class, review_state, quality_flags_json,
            applicability_domain_json, provenance_activity_json,
            content_sha256, created_at
        ) VALUES (
            'observation-1', 'lab-property-observation-v1',
            'CHEMICAL_ENTITY', '{"cas": "78-70-6"}', ?, 'vapor_pressure',
            'NUMERIC', 7.0, 'Pa', 'Pa', 'published measurement',
            'source-version-2', 'extraction-1', '{"page": 1}', 1, 'reported',
            '{}', 'MEASURED', 'REVIEWED', '[]', '{}', '{}', ?, ?
        )
        """,
        ("8" * 64, "9" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_property_conflict_sets (
            id, schema_version, requested_identity_json,
            requested_identity_sha256, property_type,
            requested_conditions_json, state, materiality,
            difference_dimensions_json, explanation, content_sha256,
            created_at
        ) VALUES (
            'conflict-1', 'lab-property-conflict-v1',
            '{"cas": "78-70-6"}', ?, 'vapor_pressure', '{}', 'UNRESOLVED',
            'NON_BLOCKING', '[]', 'Single-candidate audit set', ?, ?
        )
        """,
        ("8" * 64, "a" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_property_conflict_members (
            id, conflict_set_id, observation_id, differences_json, created_at
        ) VALUES ('conflict-member-1', 'conflict-1', 'observation-1', '{}', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_selected_assertions (
            id, schema_version, requested_identity_json,
            requested_identity_sha256, requested_property_type,
            requested_conditions_json, conflict_set_id,
            selection_policy_version, selection_kind,
            selected_observation_id, interpolation_state,
            propagated_uncertainty_json, applicability_json, authority_state,
            permitted_claim_wording, content_sha256, created_at
        ) VALUES (
            'assertion-1', 'lab-selected-assertion-v1',
            '{"cas": "78-70-6"}', ?, 'vapor_pressure', '{}', 'conflict-1',
            'b2-selection-v1', 'OBSERVATION', 'observation-1', 'EXACT',
            '{}', '{}', 'AUTHORIZED_FOR_SCOPED_PROPERTY',
            'Measured vapor pressure under the recorded conditions.', ?, ?
        )
        """,
        ("8" * 64, "b" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_selected_assertion_candidates (
            id, selected_assertion_id, observation_id, decision, rationale,
            created_at
        ) VALUES (
            'candidate-1', 'assertion-1', 'observation-1', 'INCLUDE',
            'Only reviewed candidate in the requested scope.', ?
        )
        """,
        (timestamp,),
    )


def test_b2_migration_upgrades_empty_database_without_promoting_rows(tmp_path):
    database = tmp_path / "b2-empty.db"
    config = _config(database)

    command.upgrade(config, B2_HEAD)

    with sqlite3.connect(database) as connection:
        assert B2_TABLES <= _table_names(connection)
        assert {
            table: int(
                connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            )
            for table in B2_TABLES
        } == {table: 0 for table in B2_TABLES}
        assert {"authority_state", "authority_reason"} <= _columns(
            connection,
            "lab_material_properties",
        )
    assert _revision(database) == B2_HEAD
    assert _integrity(database) == "ok"


def test_b2_migration_labels_b1_legacy_rows_without_promoting_them(tmp_path):
    database = tmp_path / "b2-representative.db"
    config = _config(database)
    command.upgrade(config, B1_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        _insert_legacy_property(connection)
        connection.commit()

    command.upgrade(config, B2_HEAD)

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            """
            SELECT id, value, evidence_id, authority_state, authority_reason
            FROM lab_material_properties
            """
        ).fetchall() == [
            (
                "legacy-property-1",
                7.0,
                "evidence-1",
                "LEGACY_HEURISTIC",
                LEGACY_AUTHORITY_REASON,
            )
        ]
        assert {
            table: int(
                connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            )
            for table in B2_TABLES
        } == {table: 0 for table in B2_TABLES}
    assert _revision(database) == B2_HEAD
    assert _integrity(database) == "ok"


def test_b2_migration_enforces_shapes_foreign_keys_and_append_only_history(tmp_path):
    database = tmp_path / "b2-constraints.db"
    config = _config(database)
    command.upgrade(config, B2_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_b1_rows(connection)
        _insert_b2_rows(connection)
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_property_observations (
                    id, schema_version, identity_scope, subject_identity_json,
                    subject_identity_sha256, property_type, value_kind,
                    original_unit, canonical_unit, method, source_version_id,
                    extraction_record_id, source_locator_json, replicate_count,
                    statistic, uncertainty_interval_json, evidence_class,
                    review_state, quality_flags_json, applicability_domain_json,
                    provenance_activity_json, content_sha256, created_at
                ) VALUES (
                    'bad-shape', 'v1', 'CHEMICAL_ENTITY', '{}', ?,
                    'vapor_pressure', 'NUMERIC', 'Pa', 'Pa', 'unknown',
                    'source-version-2', 'extraction-1', '{}', 1, 'reported',
                    '{}', 'MEASURED', 'STAGED', '[]', '{}', '{}', ?,
                    CURRENT_TIMESTAMP
                )
                """,
                ("c" * 64, "d" * 64),
            )
        connection.rollback()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_property_observations (
                    id, schema_version, identity_scope, subject_identity_json,
                    subject_identity_sha256, property_type, value_kind,
                    numeric_value, original_unit, canonical_unit, method,
                    source_version_id, extraction_record_id,
                    source_locator_json, replicate_count, statistic,
                    uncertainty_interval_json, evidence_class, review_state,
                    quality_flags_json, applicability_domain_json,
                    provenance_activity_json, content_sha256, created_at
                ) VALUES (
                    'bad-source', 'v1', 'CHEMICAL_ENTITY', '{}', ?,
                    'vapor_pressure', 'NUMERIC', 1.0, 'Pa', 'Pa', 'unknown',
                    'missing-source', 'extraction-1', '{}', 1, 'reported',
                    '{}', 'MEASURED', 'STAGED', '[]', '{}', '{}', ?,
                    CURRENT_TIMESTAMP
                )
                """,
                ("e" * 64, "f" * 64),
            )
        connection.rollback()

        for table_name in sorted(B2_TABLES | {"lab_material_properties"}):
            if table_name == "lab_material_properties":
                _minimum_rows(connection)
                _insert_legacy_property(connection)
                connection.commit()
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f'UPDATE "{table_name}" SET created_at=created_at'
                )
            connection.rollback()
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(f'DELETE FROM "{table_name}"')
            connection.rollback()


def test_b2_migration_downgrades_to_b1_and_reupgrades_legacy_labels(tmp_path):
    database = tmp_path / "b2-roundtrip.db"
    config = _config(database)
    command.upgrade(config, B1_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        _insert_legacy_property(connection)
        connection.commit()
    command.upgrade(config, B2_HEAD)

    command.downgrade(config, B1_HEAD)
    with sqlite3.connect(database) as connection:
        assert not (B2_TABLES & _table_names(connection))
        assert not (
            {"authority_state", "authority_reason"}
            & _columns(connection, "lab_material_properties")
        )
        assert connection.execute(
            "SELECT id, value, evidence_id FROM lab_material_properties"
        ).fetchall() == [("legacy-property-1", 7.0, "evidence-1")]
    assert _revision(database) == B1_HEAD
    assert _integrity(database) == "ok"

    command.upgrade(config, B2_HEAD)
    with sqlite3.connect(database) as connection:
        assert B2_TABLES <= _table_names(connection)
        assert connection.execute(
            """
            SELECT authority_state, authority_reason
            FROM lab_material_properties
            WHERE id='legacy-property-1'
            """
        ).fetchone() == ("LEGACY_HEURISTIC", LEGACY_AUTHORITY_REASON)
    assert _revision(database) == B2_HEAD
    assert _integrity(database) == "ok"


def test_b2_migration_is_explicit_and_contains_no_canonical_backfill():
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "20260730_0006_b2_property_authority.py"
    )
    source = migration_path.read_text(encoding="utf-8")
    lowered = source.casefold()

    assert "app.models" not in lowered
    assert "base.metadata" not in lowered
    assert "checkfirst" not in lowered
    assert "bulk_insert" not in lowered
    for table_name in B2_TABLES:
        assert table_name in source
        assert f"insert into {table_name}" not in lowered
    assert "LEGACY_HEURISTIC" in source
    assert LEGACY_AUTHORITY_REASON in source
