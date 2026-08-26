import hashlib
import re
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import CheckConstraint

from alembic import command
from app.models.lab_claims import (
    LabClaimAuthoritySupportLink,
    LabClaimAuthorityVersion,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B6_HEAD = "20260731_0010"
B7_HEAD = "20260731_0011"
B7_MODELS = (
    LabClaimAuthorityVersion,
    LabClaimAuthoritySupportLink,
)
B7_TABLES = {model.__tablename__ for model in B7_MODELS}


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


def _insert_a2_claim(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_claim_assessment_versions (
            id, created_at, claim_id, version_number, schema_version,
            claim_type, subject_type, subject_id, parent_version_id,
            policy_version, decision, authority_json,
            missing_evidence_json, conflicts_json, permitted_wording,
            forbidden_wording, human_review_state, reviewer_pseudonym,
            reviewed_at, content_sha256, parent_sha256
        ) VALUES (
            'b7-a2-claim', CURRENT_TIMESTAMP, 'b7-a2-chain', 1,
            'a4-claim-v1', 'PROPERTY_VALUE', 'FORMULA_VERSION',
            'historical-subject', NULL, 'a4-policy-v1', 'ALLOW_EXACT',
            '{"source_coverage_complete": true}', '[]', '[]',
            'legacy wording', 'legacy forbidden', 'APPROVED', 'reviewer',
            CURRENT_TIMESTAMP, ?, NULL
        )
        """,
        ("a" * 64,),
    )


def _insert_b7_authority(
    connection: sqlite3.Connection,
    *,
    row_id: str = "b7-authority",
    decision: str = "ALLOW_EXACT",
    content_sha256: str = "f" * 64,
) -> None:
    connection.execute(
        """
        INSERT INTO lab_claim_authority_versions (
            id, created_at, authority_id, version_number, parent_version_id,
            legacy_claim_assessment_version_id, schema_version,
            policy_version, policy_sha256, policy_json, claim_type,
            subject_type, subject_id, claim_payload_json,
            identity_scope_json, identity_scope_sha256,
            condition_scope_json, condition_scope_sha256,
            claim_scope_sha256, decision, dimension_results_json,
            supporting_observations_json, conflicts_json,
            missing_requirements_json, source_references_json,
            uncertainty_json, permitted_wording, forbidden_wording,
            blocker_count, conflict_count, missing_requirement_count,
            critical_unknown_count, support_count, source_reference_count,
            release_authority, upstream_hashes_json, reviewer_pseudonym,
            reviewed_at, content_sha256, parent_sha256
        ) VALUES (
            ?, CURRENT_TIMESTAMP, 'b7-authority-chain', 1, NULL,
            'b7-a2-claim', 'b7-claim-authority-v1', 'b7-policy-v1',
            ?, '{}', 'PROPERTY_VALUE', 'FORMULA_VERSION',
            'historical-subject', '{"property_type": "density"}',
            '{"material": "test"}', ?, '{"temperature_k": 298.15}', ?,
            ?, ?, '{}', '[{"kind": "PROPERTY_ASSERTION"}]', '[]', '[]',
            '[{"source_version_id": "source"}]', '{}',
            'Exact only for the declared scope.',
            'Not release-grade.', 0, 0, 0, 0, 1, 1, 0, '{}',
            'reviewer', CURRENT_TIMESTAMP, ?, NULL
        )
        """,
        (
            row_id,
            "b" * 64,
            "c" * 64,
            "d" * 64,
            "e" * 64,
            decision,
            content_sha256,
        ),
    )


def test_b7_migration_adds_two_empty_tables_without_changing_prior_rows(
    tmp_path,
):
    database = tmp_path / "b7-empty.db"
    config = _config(database)
    command.upgrade(config, B6_HEAD)
    with sqlite3.connect(database) as connection:
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B7_HEAD)

    with sqlite3.connect(database) as connection:
        assert B7_TABLES <= _tables(connection)
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B7_HEAD,)
        assert {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in B7_TABLES
        } == {table: 0 for table in B7_TABLES}
        assert _table_state(connection, prior_tables) == prior_state
        triggers = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        for table in B7_TABLES:
            assert f"trg_{table}_no_update" in triggers
            assert f"trg_{table}_no_delete" in triggers
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_b7_migration_downgrades_only_b7_and_reupgrades_empty(tmp_path):
    database = tmp_path / "b7-roundtrip.db"
    config = _config(database)
    command.upgrade(config, B6_HEAD)
    with sqlite3.connect(database) as connection:
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B7_HEAD)
    command.downgrade(config, B6_HEAD)

    with sqlite3.connect(database) as connection:
        assert not (B7_TABLES & _tables(connection))
        assert _table_state(connection, prior_tables) == prior_state
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B6_HEAD,)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    command.upgrade(config, B7_HEAD)
    with sqlite3.connect(database) as connection:
        assert B7_TABLES <= _tables(connection)
        assert all(
            connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            == 0
            for table in B7_TABLES
        )


def test_b7_database_guards_decisions_typed_links_and_append_only(tmp_path):
    database = tmp_path / "b7-constraints.db"
    config = _config(database)
    command.upgrade(config, B7_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_a2_claim(connection)
        _insert_b7_authority(connection)
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_claim_authority_versions "
                "SET decision=decision WHERE id='b7-authority'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM lab_claim_authority_versions "
                "WHERE id='b7-authority'"
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_claim_authority_decision",
        ):
            _insert_b7_authority(
                connection,
                row_id="b7-bad-decision",
                decision="RELEASE",
                content_sha256="1" * 64,
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_claim_authority_support_shape",
        ):
            connection.execute(
                """
                INSERT INTO lab_claim_authority_support_links (
                    id, created_at, claim_authority_version_id,
                    support_kind, role, property_assertion_id,
                    oav_assessment_id, upstream_content_sha256,
                    derived_facts_json, source_references_json,
                    content_sha256
                ) VALUES (
                    'b7-bad-support', CURRENT_TIMESTAMP, 'b7-authority',
                    'PROPERTY_ASSERTION', 'SUPPORTING', 'missing-property',
                    'missing-oav', ?, '{}', '[]', ?
                )
                """,
                ("2" * 64, "3" * 64),
            )


def test_b7_migration_matches_models_columns_checks_indexes_and_fks(tmp_path):
    database = tmp_path / "b7-parity.db"
    config = _config(database)
    command.upgrade(config, B7_HEAD)

    with sqlite3.connect(database) as connection:
        for model in B7_MODELS:
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


def test_b7_migration_is_explicit_and_imports_zero_prior_rows():
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260731_0011_b7_claim_authority.py"
    )
    source = migration_path.read_text(encoding="utf-8")
    lowered = source.casefold()

    assert "app.models" not in lowered
    assert "base.metadata" not in lowered
    assert "checkfirst" not in lowered
    assert "bulk_insert" not in lowered
    for table_name in B7_TABLES:
        assert table_name in source
        assert f"insert into {table_name}" not in lowered
