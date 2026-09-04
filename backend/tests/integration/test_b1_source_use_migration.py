from __future__ import annotations

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

PRIOR_HEAD = "20260810_0014"
SOURCE_USE_HEAD = "20260810_0015"
TABLE_NAME = "lab_source_use_constraint_versions"


def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table_name}")')
    }


def _insert_source_use_constraint(connection: sqlite3.Connection) -> None:
    constraints = {
        "plan_or_tier": None,
        "jurisdiction": None,
        "valid_from": None,
        "valid_until": None,
        "max_records": 100,
        "max_bytes": None,
        "retention_days": None,
        "freshness_required": False,
        "attribution_required": True,
        "share_alike_required": False,
        "noncommercial_only": False,
        "no_sublicense": False,
        "no_competing_service": False,
        "deletion_or_tombstone_required": False,
        "rate_limit_max_requests": None,
        "rate_limit_period_seconds": None,
        "unmodeled_constraints": [],
    }
    connection.execute(
        f"""
        INSERT INTO {TABLE_NAME} (
            id, constraint_id, version_number,
            subject_source_version_id, terms_source_version_id,
            artifact_scope, artifact_locator_json, channel,
            intended_action, purpose_context, decision, constraints_json,
            terms_effective_date, terms_retrieval_date,
            reviewer_pseudonym, review_state, legal_review_required,
            record_sha256, created_at
        ) VALUES (
            'source-use-version-1', 'source-use-constraint-1', 1,
            'source-version-2', 'source-version-1',
            'DATASET', '{{"artifact_id":"dataset-v1"}}',
            'official-data-repository', 'INTERNAL_ANALYSIS',
            'external-study-method-development', 'DECLARED_ALLOWED', ?,
            '2021-05-05', '2026-08-10', 'rights-reviewer', 'REVIEWED', 0,
            ?, CURRENT_TIMESTAMP
        )
        """,
        (json.dumps(constraints), "8" * 64),
    )
    connection.commit()


def test_source_use_migration_installs_exact_fields_fks_and_append_only_guard(
    tmp_path,
):
    database = tmp_path / "b1-source-use.db"
    config = _config(database)
    command.upgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_b1_rows(connection)

    command.upgrade(config, SOURCE_USE_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert {
            "constraint_id",
            "version_number",
            "subject_source_version_id",
            "terms_source_version_id",
            "artifact_scope",
            "artifact_locator_json",
            "channel",
            "intended_action",
            "purpose_context",
            "decision",
            "constraints_json",
            "terms_effective_date",
            "terms_retrieval_date",
            "review_state",
            "legal_review_required",
            "supersedes_version_id",
            "parent_record_sha256",
            "record_sha256",
        } <= _columns(connection, TABLE_NAME)
        _insert_source_use_constraint(connection)
        row = connection.execute(
            f"SELECT artifact_scope, intended_action, decision, "
            f"constraints_json FROM {TABLE_NAME}"
        ).fetchone()
        assert row[:3] == (
            "DATASET",
            "INTERNAL_ANALYSIS",
            "DECLARED_ALLOWED",
        )
        assert json.loads(row[3])["attribution_required"] is True

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                f"UPDATE {TABLE_NAME} SET decision='DECLARED_PROHIBITED'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(f"DELETE FROM {TABLE_NAME}")
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                f"""
                INSERT INTO {TABLE_NAME} (
                    id, constraint_id, version_number,
                    subject_source_version_id, terms_source_version_id,
                    artifact_scope, artifact_locator_json, channel,
                    intended_action, purpose_context, decision,
                    constraints_json, terms_retrieval_date,
                    review_state, legal_review_required,
                    record_sha256, created_at
                ) VALUES (
                    'bad-source-use', 'bad-source-use', 1,
                    'source-version-2', 'source-version-1', 'DATASET', '{{}}',
                    'channel', 'SCRAPE_ANYTHING', 'purpose', 'UNRESOLVED',
                    '{{}}', '2026-08-10', 'UNREVIEWED', 1, ?, CURRENT_TIMESTAMP
                )
                """,
                ("9" * 64,),
            )
        connection.rollback()
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    assert _revision(database) == SOURCE_USE_HEAD
    assert _integrity(database) == "ok"


def test_source_use_migration_downgrades_and_reupgrades_cleanly(tmp_path):
    database = tmp_path / "b1-source-use-roundtrip.db"
    config = _config(database)
    command.upgrade(config, SOURCE_USE_HEAD)

    command.downgrade(config, PRIOR_HEAD)
    with sqlite3.connect(database) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert TABLE_NAME not in tables
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert _revision(database) == PRIOR_HEAD

    command.upgrade(config, SOURCE_USE_HEAD)
    with sqlite3.connect(database) as connection:
        assert TABLE_NAME in {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert _revision(database) == SOURCE_USE_HEAD
    assert _integrity(database) == "ok"
