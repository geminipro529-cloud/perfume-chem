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

A5_HEAD = "20260730_0004"
B1_HEAD = "20260730_0005"
B1_TABLES = {
    "lab_source_document_versions",
    "lab_source_derivation_links",
    "lab_source_extraction_records",
    "lab_evidence_workflow_events",
}


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


def _legacy_schema(connection: sqlite3.Connection) -> dict[tuple[str, str], str]:
    return {
        (str(row[0]), str(row[1])): str(row[2])
        for row in connection.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%'
              AND tbl_name NOT IN (
                  'lab_source_document_versions',
                  'lab_source_derivation_links',
                  'lab_source_extraction_records',
                  'lab_evidence_workflow_events'
              )
            ORDER BY type, name
            """
        )
    }


def _legacy_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
        for table in sorted(_table_names(connection) - B1_TABLES)
    }


def _insert_b1_rows(connection: sqlite3.Connection) -> None:
    source_sql = """
        INSERT INTO lab_source_document_versions (
            id, source_id, version_number, schema_version, source_type,
            title, authors_json, identifiers_json, default_locator_json,
            artifact_sha256, language, review_state, independence_group,
            record_sha256, created_at
        ) VALUES (?, ?, 1, 'lab-source-document-v1',
                  'PRIMARY_PEER_REVIEWED_PAPER', ?, '["Author"]', '{}',
                  '{"page": 1}', ?, 'en', 'UNREVIEWED', ?, ?,
                  CURRENT_TIMESTAMP)
    """
    connection.execute(
        source_sql,
        (
            "source-version-1",
            "source-1",
            "Primary source",
            "a" * 64,
            "primary-lineage",
            "1" * 64,
        ),
    )
    connection.execute(
        source_sql,
        (
            "source-version-2",
            "source-2",
            "Derived source",
            "b" * 64,
            "primary-lineage",
            "2" * 64,
        ),
    )
    connection.execute(
        """
        INSERT INTO lab_source_derivation_links (
            id, child_source_version_id, parent_source_version_id,
            relation, record_sha256, created_at
        ) VALUES (
            'derivation-1', 'source-version-2', 'source-version-1',
            'DERIVED_FROM', ?, CURRENT_TIMESTAMP
        )
        """,
        ("3" * 64,),
    )
    connection.execute(
        """
        INSERT INTO lab_source_extraction_records (
            id, source_version_id, locator_json, structure_context_json,
            original_wording, normalization_json, parser_or_model_version,
            uncertainty_json, ambiguity_json, output_observation_id,
            input_sha256, output_sha256, record_sha256, created_at
        ) VALUES (
            'extraction-1', 'source-version-2', '{"page": 1}',
            '{"column_heading": "value"}', '7.0', '{}', 'manual/1',
            '{}', '[]', 'observation-1', ?, ?, ?, CURRENT_TIMESTAMP
        )
        """,
        ("4" * 64, "5" * 64, "6" * 64),
    )
    connection.execute(
        """
        INSERT INTO lab_evidence_workflow_events (
            id, subject_type, subject_id, sequence_number, from_state,
            to_state, scope_json, record_sha256, created_at
        ) VALUES (
            'workflow-1', 'EXTRACTION_RECORD', 'extraction-1', 1, NULL,
            'STAGED', '[]', ?, CURRENT_TIMESTAMP
        )
        """,
        ("7" * 64,),
    )
    connection.commit()


def test_b1_migration_upgrades_empty_database_without_backfill(tmp_path):
    database = tmp_path / "b1-empty.db"
    config = _config(database)

    command.upgrade(config, B1_HEAD)

    with sqlite3.connect(database) as connection:
        assert B1_TABLES <= _table_names(connection)
        assert {
            table: connection.execute(
                f'SELECT count(*) FROM "{table}"'
            ).fetchone()[0]
            for table in B1_TABLES
        } == {table: 0 for table in B1_TABLES}
    assert _revision(database) == B1_HEAD
    assert _integrity(database) == "ok"


def test_b1_migration_preserves_representative_a5_schema_and_rows(tmp_path):
    database = tmp_path / "b1-representative.db"
    config = _config(database)
    command.upgrade(config, A5_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        connection.commit()
        before_schema = _legacy_schema(connection)
        before_counts = _legacy_counts(connection)

    command.upgrade(config, B1_HEAD)

    with sqlite3.connect(database) as connection:
        assert _legacy_schema(connection) == before_schema
        assert _legacy_counts(connection) == before_counts
        assert B1_TABLES <= _table_names(connection)
    assert _revision(database) == B1_HEAD
    assert _integrity(database) == "ok"


def test_b1_migration_installs_constraints_and_append_only_guards(tmp_path):
    database = tmp_path / "b1-constraints.db"
    config = _config(database)
    command.upgrade(config, B1_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_source_document_versions (
                    id, source_id, version_number, schema_version,
                    source_type, title, authors_json, identifiers_json,
                    default_locator_json, artifact_sha256, language,
                    review_state, independence_group, record_sha256,
                    created_at
                ) VALUES (
                    'bad', 'bad', 1, 'v1', 'BLOG', 'Bad', '[]', '{}', '{}',
                    ?, 'en', 'UNREVIEWED', 'bad', ?, CURRENT_TIMESTAMP
                )
                """,
                ("a" * 64, "b" * 64),
            )
        connection.rollback()
        _insert_b1_rows(connection)

        update_columns = {
            "lab_source_document_versions": ("title", "Changed"),
            "lab_source_derivation_links": ("relation", "CITES"),
            "lab_source_extraction_records": ("original_wording", "Changed"),
            "lab_evidence_workflow_events": ("reason", "Changed"),
        }
        for table, (column, value) in update_columns.items():
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f'UPDATE "{table}" SET "{column}"=?',
                    (value,),
                )
            connection.rollback()
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(f'DELETE FROM "{table}"')
            connection.rollback()


def test_b1_migration_downgrades_only_b1_and_reupgrades(tmp_path):
    database = tmp_path / "b1-roundtrip.db"
    config = _config(database)
    command.upgrade(config, B1_HEAD)

    command.downgrade(config, A5_HEAD)
    with sqlite3.connect(database) as connection:
        assert not (B1_TABLES & _table_names(connection))
    assert _revision(database) == A5_HEAD
    assert _integrity(database) == "ok"

    command.upgrade(config, B1_HEAD)
    with sqlite3.connect(database) as connection:
        assert B1_TABLES <= _table_names(connection)
    assert _revision(database) == B1_HEAD
    assert _integrity(database) == "ok"


def test_b1_migration_is_explicit_and_contains_no_backfill():
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "20260730_0005_b1_source_provenance.py"
    ).read_text(encoding="utf-8")
    lowered = migration.casefold()

    assert "has_table" not in lowered
    assert "bulk_insert" not in lowered
    assert "insert into" not in lowered
    assert "update lab_" not in lowered
