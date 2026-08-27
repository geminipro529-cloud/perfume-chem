import re
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.models.lab_rules import (
    LabKnowledgeRule,
    LabRuleCompilationRun,
    LabRuleContradiction,
    LabRuleGroup,
    LabRuleGroupMember,
    LabRuleSupportEvidence,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B3_HEAD = "20260730_0007"
B4_HEAD = "20260731_0008"
B4_MODELS = (
    LabRuleGroup,
    LabRuleGroupMember,
    LabKnowledgeRule,
    LabRuleContradiction,
    LabRuleSupportEvidence,
    LabRuleCompilationRun,
)
B4_TABLES = {model.__tablename__ for model in B4_MODELS}


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
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def _insert_b3_sentinel(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_legacy_threshold_records
        (id, created_at, schema_version, material_key, medium,
         numeric_value, original_unit, verification_status,
         authority_state, source_payload_json, content_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "b3-sentinel",
            "2026-07-31T00:00:00+00:00",
            "lab-legacy-threshold-v1",
            "linalool",
            "AIR",
            0.51,
            "ppb",
            "DERIVED",
            "LEGACY_CONTEXT_INCOMPLETE",
            "{}",
            "a" * 64,
        ),
    )


def _rule_values(
    *,
    rule_id: str,
    subject_kind: str = "EXACT_IDENTITY",
    subject_identity: str | None = "1" * 64,
    status: str = "ADVISORY",
    runtime_role: str = "ADVISORY",
) -> tuple:
    return (
        rule_id,
        "2026-07-31T00:00:00+00:00",
        rule_id,
        1,
        subject_kind,
        "subject",
        subject_identity,
        None,
        "REINFORCES",
        "EXACT_IDENTITY",
        "object",
        "2" * 64,
        None,
        "DIRECTED",
        "{}",
        "{}",
        "{}",
        "{}",
        "floral_radiance",
        "Legacy explanatory record.",
        None,
        None,
        "",
        "LEGACY_UNVERIFIED",
        '{"state": "UNKNOWN"}',
        "UNREVIEWED",
        status,
        runtime_role,
        None,
        None,
        "legacy.json",
        "/0",
        "3" * 64,
        "[]",
        ("4" if rule_id.endswith("1") else "5") * 64,
    )


RULE_INSERT = """
    INSERT INTO lab_knowledge_rules (
        id, created_at, rule_key, version,
        subject_kind, subject_raw_label, subject_identity_scope_sha256,
        subject_group_id, relation, object_kind, object_raw_label,
        object_identity_scope_sha256, object_group_id, directionality,
        matrix_context_json, dose_domain_json, temporal_domain_json,
        expected_effect_json, attribute, rationale,
        source_document_version_id, source_extraction_id, source_locator,
        evidence_class, uncertainty_json, review_state, status, runtime_role,
        numerical_model_ref, supersedes_rule_id, raw_source_path,
        raw_json_pointer, raw_payload_sha256, compiler_diagnostics_json,
        content_sha256
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
"""


def test_b4_migration_creates_six_empty_append_only_authority_tables(tmp_path):
    database = tmp_path / "b4-empty.db"
    config = _config(database)
    command.upgrade(config, B4_HEAD)

    with sqlite3.connect(database) as connection:
        assert B4_TABLES <= _tables(connection)
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B4_HEAD,)
        assert {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in B4_TABLES
        } == {table: 0 for table in B4_TABLES}
        triggers = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        for table in B4_TABLES:
            assert f"trg_{table}_no_update" in triggers
            assert f"trg_{table}_no_delete" in triggers
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_b4_migration_downgrades_to_b3_without_touching_b3_rows(tmp_path):
    database = tmp_path / "b4-roundtrip.db"
    config = _config(database)
    command.upgrade(config, B3_HEAD)
    with sqlite3.connect(database) as connection:
        _insert_b3_sentinel(connection)
        connection.commit()

    command.upgrade(config, B4_HEAD)
    command.downgrade(config, B3_HEAD)

    with sqlite3.connect(database) as connection:
        assert not (B4_TABLES & _tables(connection))
        assert connection.execute(
            "SELECT id, numeric_value FROM lab_legacy_threshold_records"
        ).fetchall() == [("b3-sentinel", 0.51)]
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B3_HEAD,)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_b4_database_guards_rule_authority_and_append_only_history(tmp_path):
    database = tmp_path / "b4-constraints.db"
    config = _config(database)
    command.upgrade(config, B4_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(RULE_INSERT, _rule_values(rule_id="valid-rule-1"))
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_knowledge_rules SET rationale=rationale "
                "WHERE id='valid-rule-1'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM lab_knowledge_rules WHERE id='valid-rule-1'"
            )
        connection.rollback()

        invalid_rows = (
            _rule_values(
                rule_id="bad-shape",
                subject_kind="EXACT_IDENTITY",
                subject_identity=None,
            ),
            _rule_values(
                rule_id="generic-authority",
                subject_kind="GENERIC_PROSE",
                subject_identity=None,
                status="AUTHORITATIVE",
                runtime_role="EXPLANATORY",
            ),
            _rule_values(
                rule_id="generic-blocking",
                subject_kind="GENERIC_PROSE",
                subject_identity=None,
                status="ADVISORY",
                runtime_role="BLOCKING",
            ),
            _rule_values(
                rule_id="exact-authority-without-provenance",
                status="AUTHORITATIVE",
                runtime_role="EXPLANATORY",
            ),
        )
        for values in invalid_rows:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(RULE_INSERT, values)
            connection.rollback()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_rule_groups (
                    id, created_at, group_key, version, label, definition,
                    source_document_version_id, source_extraction_id,
                    source_locator, review_state, status, supersedes_group_id,
                    content_sha256
                ) VALUES (
                    'authority-group-without-provenance', CURRENT_TIMESTAMP,
                    'white-musks', 1, 'White musks', 'Reviewed group.',
                    NULL, NULL, '', 'APPROVED', 'AUTHORITATIVE', NULL, ?
                )
                """,
                ("9" * 64,),
            )
        connection.rollback()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_rule_compilation_runs (
                    id, created_at, compiler_version, source_manifest_json,
                    source_corpus_sha256, source_record_count,
                    compiled_rule_count, invalid_exact_count, duplicate_count,
                    contradiction_count, cycle_count, orphan_count,
                    generic_count, baseline_invalid_exact_count, passed,
                    report_sha256, content_sha256
                ) VALUES (
                    'bad-compilation', CURRENT_TIMESTAMP, 'v1', '{}', ?, 3381,
                    3381, 138, 68, 0, 1, 138, 5, 137, 1, ?, ?
                )
                """,
                ("6" * 64, "7" * 64, "8" * 64),
            )


def test_b4_migration_matches_model_columns_checks_and_explicit_indexes(tmp_path):
    database = tmp_path / "b4-parity.db"
    config = _config(database)
    command.upgrade(config, B4_HEAD)

    with sqlite3.connect(database) as connection:
        for model in B4_MODELS:
            table_name = model.__tablename__
            actual_columns = {
                str(row[1])
                for row in connection.execute(
                    f'PRAGMA table_info("{table_name}")'
                )
            }
            assert actual_columns == {
                column.name for column in model.__table__.columns
            }

            actual_indexes = {
                str(row[1])
                for row in connection.execute(
                    f'PRAGMA index_list("{table_name}")'
                )
                if str(row[1]).startswith("ix_")
            }
            assert actual_indexes == {
                index.name for index in model.__table__.indexes
            }

            create_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()[0]
            actual_check_names = set(
                re.findall(
                    r"CONSTRAINT\s+([A-Za-z0-9_]+)\s+CHECK",
                    create_sql,
                    flags=re.IGNORECASE,
                )
            )
            expected_check_names = {
                constraint.name
                for constraint in model.__table__.constraints
                if constraint.__class__.__name__ == "CheckConstraint"
            }
            assert actual_check_names == expected_check_names


def test_b4_migration_is_explicit_and_imports_zero_legacy_rows():
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260731_0008_b4_knowledge_rules.py"
    )
    source = migration_path.read_text(encoding="utf-8")
    lowered = source.casefold()

    assert "app.models" not in lowered
    assert "base.metadata" not in lowered
    assert "checkfirst" not in lowered
    assert "bulk_insert" not in lowered
    for table_name in B4_TABLES:
        assert table_name in source
        assert f"insert into {table_name}" not in lowered
