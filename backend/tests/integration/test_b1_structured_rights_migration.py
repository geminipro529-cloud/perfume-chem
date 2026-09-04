import json
import sqlite3

import pytest

from alembic import command
from tests.integration.test_a2_planning_migration import (
    _config,
    _integrity,
    _revision,
)
from tests.integration.test_b1_source_migration import _insert_b1_rows

PRIOR_HEAD = "20260731_0012"
RIGHTS_HEAD = "20260810_0013"
LEGACY_RIGHTS = {
    "reuse_status": "UNKNOWN",
    "license_or_reuse_restriction": "UNVERIFIED_LEGACY_ROW",
    "license_url": None,
    "redistribution_allowed": False,
    "spdx_identifier": None,
    "notes": "Legacy row requires explicit manifest rebind.",
}


def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table_name}")')
    }


def test_structured_rights_migration_backfills_unknown_and_preserves_guards(
    tmp_path,
):
    database = tmp_path / "b1-structured-rights.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_b1_rows(connection)

    command.upgrade(config, RIGHTS_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert "rights_json" in _columns(
            connection,
            "lab_source_document_versions",
        )
        assert "relation_scopes_json" in _columns(
            connection,
            "lab_source_derivation_links",
        )
        legacy_rights = json.loads(
            connection.execute(
                "SELECT rights_json FROM lab_source_document_versions "
                "WHERE id='source-version-1'"
            ).fetchone()[0]
        )
        assert legacy_rights == LEGACY_RIGHTS
        assert json.loads(
            connection.execute(
                "SELECT relation_scopes_json FROM lab_source_derivation_links "
                "WHERE id='derivation-1'"
            ).fetchone()[0]
        ) == []

        dataset_rights = {
            "reuse_status": "PERMITTED",
            "license_or_reuse_restriction": "CC0 1.0",
            "license_url": (
                "https://creativecommons.org/publicdomain/zero/1.0/"
            ),
            "redistribution_allowed": True,
            "spdx_identifier": "CC0-1.0",
            "notes": "Dataset scope only.",
        }
        connection.execute(
            """
            INSERT INTO lab_source_document_versions (
                id, source_id, version_number, schema_version, source_type,
                title, authors_json, identifiers_json, default_locator_json,
                artifact_sha256, license_or_reuse_restriction, rights_json,
                language, review_state, independence_group, record_sha256,
                created_at
            ) VALUES (
                'dataset-version-1', 'dataset-source-1', 1,
                'lab-source-document-v2', 'PRIMARY_RESEARCH_DATASET',
                'Primary study dataset', '["Researcher"]', '{}',
                '{"table":"observations"}', ?, 'CC0 1.0', ?, 'en',
                'UNREVIEWED', 'dataset-lineage', ?, CURRENT_TIMESTAMP
            )
            """,
            ("9" * 64, json.dumps(dataset_rights), "8" * 64),
        )
        connection.commit()
        assert json.loads(
            connection.execute(
                "SELECT rights_json FROM lab_source_document_versions "
                "WHERE id='dataset-version-1'"
            ).fetchone()[0]
        ) == dataset_rights

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_source_document_versions SET rights_json='{}' "
                "WHERE id='source-version-1'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_source_derivation_links "
                "SET relation_scopes_json='[]' WHERE id='derivation-1'"
            )
        connection.rollback()
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    assert _revision(database) == RIGHTS_HEAD
    assert _integrity(database) == "ok"


def test_structured_rights_migration_downgrades_and_reupgrades_empty_database(
    tmp_path,
):
    database = tmp_path / "b1-structured-rights-roundtrip.db"
    config = _config(database)
    command.upgrade(config, RIGHTS_HEAD)

    command.downgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        assert "rights_json" not in _columns(
            connection,
            "lab_source_document_versions",
        )
        assert "relation_scopes_json" not in _columns(
            connection,
            "lab_source_derivation_links",
        )
        _insert_b1_rows(connection)
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_source_document_versions SET title='Changed' "
                "WHERE id='source-version-1'"
            )
        connection.rollback()
    assert _revision(database) == PRIOR_HEAD
    assert _integrity(database) == "ok"

    command.upgrade(config, RIGHTS_HEAD)
    with sqlite3.connect(database) as connection:
        assert json.loads(
            connection.execute(
                "SELECT rights_json FROM lab_source_document_versions "
                "WHERE id='source-version-1'"
            ).fetchone()[0]
        ) == LEGACY_RIGHTS
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert _revision(database) == RIGHTS_HEAD
    assert _integrity(database) == "ok"
