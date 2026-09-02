from __future__ import annotations

import sqlite3

import pytest

from alembic import command
from tests.integration.test_a2_planning_migration import (
    _config,
    _integrity,
    _revision,
)
from tests.integration.test_b1_source_migration import _insert_b1_rows

PRIOR_HEAD = "20260810_0015"
EXTERNAL_STUDY_HEAD = "20260810_0016"
TABLES = {
    "lab_external_study_versions",
    "lab_external_stimulus_versions",
    "lab_external_stimulus_components",
    "lab_external_conditions",
    "lab_external_experimental_units",
    "lab_external_observations",
    "lab_external_identity_crosswalks",
    "lab_external_study_conflicts",
}


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def _insert_study(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_external_study_versions (
            id, study_id, version_number, source_version_id,
            source_extraction_id, source_family, study_key, title,
            study_domain, design_json, protocol_json,
            source_use_request_sha256, source_use_assessment_sha256,
            source_use_constraint_version_ids_json,
            source_use_constraint_record_sha256s_json,
            adapter_name, adapter_version, adapter_config_json,
            authority_state, record_sha256, created_at
        ) VALUES (
            'external-study-v1', 'external-study', 1, 'source-version-2',
            'extraction-1', 'source-family', 'study-key', 'Study title',
            'HUMAN_SENSORY', '{"design":"source"}',
            '{"matrix":"source"}', ?, ?, '[]', '[]',
            'adapter', '1', '{"strict":true}',
            'SOURCE_REPORTED_ONLY', ?, CURRENT_TIMESTAMP
        )
        """,
        ("8" * 64, "9" * 64, "a" * 64),
    )
    connection.execute(
        """
        INSERT INTO lab_external_stimulus_versions (
            id, study_version_id, stimulus_key, source_extraction_id,
            stimulus_kind, label, matrix_json, preparation_json,
            context_json, record_sha256, created_at
        ) VALUES (
            'external-stimulus-v1', 'external-study-v1', 'stimulus-1',
            'extraction-1', 'MIXTURE', 'Mixture', '{"name":"air"}',
            '{"state":"reported"}', '{}', ?, CURRENT_TIMESTAMP
        )
        """,
        ("b" * 64,),
    )
    connection.commit()


def test_external_study_migration_installs_tables_constraints_and_guards(tmp_path):
    database = tmp_path / "external-study.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_b1_rows(connection)

    command.upgrade(config, EXTERNAL_STUDY_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert TABLES <= _table_names(connection)
        _insert_study(connection)

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_external_study_versions SET title='changed'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM lab_external_stimulus_versions")
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_external_experimental_units (
                    id, study_version_id, unit_key, source_extraction_id,
                    unit_grain, reported_n, context_json, record_sha256,
                    created_at
                ) VALUES (
                    'bad-unit', 'external-study-v1', 'bad', 'extraction-1',
                    'ROW_COUNT_AS_PERSON', 1, '{}', ?, CURRENT_TIMESTAMP
                )
                """,
                ("c" * 64,),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_external_conditions (
                    id, study_version_id, condition_key,
                    source_extraction_id, condition_role, label,
                    factors_json, context_json, record_sha256, created_at
                ) VALUES (
                    'foreign-condition', 'missing-study', 'condition',
                    'extraction-1', 'TEST', 'Test', '{}', '{}', ?,
                    CURRENT_TIMESTAMP
                )
                """,
                ("d" * 64,),
            )
        connection.rollback()
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    assert _revision(database) == EXTERNAL_STUDY_HEAD
    assert _integrity(database) == "ok"


def test_external_study_migration_downgrades_and_reupgrades_cleanly(tmp_path):
    database = tmp_path / "external-study-roundtrip.db"
    config = _config(database)
    command.upgrade(config, EXTERNAL_STUDY_HEAD)

    command.downgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        assert not (TABLES & _table_names(connection))
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert _revision(database) == PRIOR_HEAD

    command.upgrade(config, EXTERNAL_STUDY_HEAD)
    with sqlite3.connect(database) as connection:
        assert TABLES <= _table_names(connection)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert _revision(database) == EXTERNAL_STUDY_HEAD
    assert _integrity(database) == "ok"
