import hashlib
import re
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.models.lab_analytical import (
    LabAnalyticalClaimAssessment,
    LabAnalyticalMethodAuthority,
    LabAnalyticalPeakAuthority,
    LabAnalyticalRunAuthority,
    LabAnalyticalSequence,
    LabAnalyticalSequenceEntry,
    LabGCOEventAuthority,
    LabMethodValidationRecord,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B4_HEAD = "20260731_0008"
B5_HEAD = "20260731_0009"
B5_MODELS = (
    LabAnalyticalMethodAuthority,
    LabMethodValidationRecord,
    LabAnalyticalSequence,
    LabAnalyticalSequenceEntry,
    LabAnalyticalRunAuthority,
    LabAnalyticalPeakAuthority,
    LabGCOEventAuthority,
    LabAnalyticalClaimAssessment,
)
B5_TABLES = {model.__tablename__ for model in B5_MODELS}


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
        digest = hashlib.sha256(
            repr((columns, rows)).encode("utf-8")
        ).hexdigest()
        state[table_name] = (len(rows), digest)
    return state


def _insert_b4_sentinel(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_legacy_threshold_records
        (id, created_at, schema_version, material_key, medium,
         numeric_value, original_unit, verification_status,
         authority_state, source_payload_json, content_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "b5-prior-sentinel",
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


def _insert_method_prerequisites(connection: sqlite3.Connection) -> None:
    timestamp = "2026-07-31T00:00:00+00:00"
    connection.execute(
        """
        INSERT INTO lab_evidence_records (
            id, claim_key, classification, source_locator,
            assumptions_json, limitations_json, created_at
        ) VALUES (
            'b5-evidence', 'b5-method', 'DIRECT', 'test:b5',
            '[]', '[]', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_source_document_versions (
            id, source_id, version_number, schema_version, source_type,
            title, authors_json, identifiers_json, default_locator_json,
            artifact_sha256, language, review_state, independence_group,
            record_sha256, created_at
        ) VALUES (
            'b5-source-version', 'b5-source', 1, 'lab-source-document-v1',
            'PRIMARY_PEER_REVIEWED_PAPER', 'B5 source', '["Author"]',
            '{}', '{"page": 1}', ?, 'en', 'REVIEWED',
            'b5-independent-source', ?, ?
        )
        """,
        ("b" * 64, "c" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_analytical_method_versions (
            id, method_id, version_number, schema_version, technique,
            intended_use, status, method_json, evidence_record_id,
            content_sha256, created_at
        ) VALUES (
            'b5-method-version', 'b5-method', 1, 'a2-analytical-v1',
            'GCMS', 'Scoped identity support', 'VALIDATED', '{}',
            'b5-evidence', ?, ?
        )
        """,
        ("d" * 64, timestamp),
    )


def _insert_method_authority(
    connection: sqlite3.Connection,
    *,
    row_id: str = "b5-method-authority",
    status: str = "VALIDATED_FOR_SCOPE",
    content_sha256: str = "f" * 64,
) -> None:
    connection.execute(
        """
        INSERT INTO lab_analytical_method_authorities (
            id, created_at, method_version_id, schema_version, status,
            analyte_scope_json, instrument_json, detector_json,
            software_json, separation_json, acquisition_json,
            sample_preparation_json, hs_spme_json, standards_json,
            calibration_json, response_factors_json,
            identity_criteria_json, integration_policy_json, qc_plan_json,
            raw_data_policy_json, source_document_version_id,
            source_locator_json, source_artifact_sha256, content_sha256
        ) VALUES (
            ?, CURRENT_TIMESTAMP, 'b5-method-version',
            'lab-analytical-method-authority-v1', ?, '[]', '{}', '{}',
            '{}', '{}', '{}', '{}', NULL, '{}', '{}', '{}', '{}', '{}',
            '{}', '{}', 'b5-source-version', '{"page": 1}', ?, ?
        )
        """,
        (row_id, status, "e" * 64, content_sha256),
    )


def _unique_column_sets(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[tuple[str, ...]]:
    result = set()
    for row in connection.execute(f'PRAGMA index_list("{table_name}")'):
        if int(row[2]) and str(row[3]) == "u":
            result.add(
                tuple(
                    str(index_row[2])
                    for index_row in connection.execute(
                        f'PRAGMA index_info("{row[1]}")'
                    )
                )
            )
    return result


def _foreign_keys(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[tuple[str, tuple[tuple[str, str], ...], str]]:
    grouped: dict[int, dict] = {}
    for row in connection.execute(f'PRAGMA foreign_key_list("{table_name}")'):
        item = grouped.setdefault(
            int(row[0]),
            {"target": str(row[2]), "pairs": [], "ondelete": str(row[6])},
        )
        item["pairs"].append((int(row[1]), str(row[3]), str(row[4])))
    return {
        (
            item["target"],
            tuple(
                (source, remote)
                for _, source, remote in sorted(item["pairs"])
            ),
            item["ondelete"],
        )
        for item in grouped.values()
    }


def _model_foreign_keys(model) -> set[
    tuple[str, tuple[tuple[str, str], ...], str]
]:
    result = set()
    for constraint in model.__table__.foreign_key_constraints:
        elements = tuple(constraint.elements)
        targets = tuple(
            element.target_fullname.rsplit(".", maxsplit=1)
            for element in elements
        )
        assert len({target[0] for target in targets}) == 1
        result.add(
            (
                targets[0][0],
                tuple(
                    (element.parent.name, target[1])
                    for element, target in zip(elements, targets, strict=True)
                ),
                (constraint.ondelete or "NO ACTION").upper(),
            )
        )
    return result


def test_b5_migration_adds_eight_empty_tables_without_changing_prior_rows(
    tmp_path,
):
    database = tmp_path / "b5-empty.db"
    config = _config(database)
    command.upgrade(config, B4_HEAD)

    with sqlite3.connect(database) as connection:
        _insert_b4_sentinel(connection)
        connection.commit()
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B5_HEAD)

    with sqlite3.connect(database) as connection:
        assert B5_TABLES <= _tables(connection)
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B5_HEAD,)
        assert {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in B5_TABLES
        } == {table: 0 for table in B5_TABLES}
        assert _table_state(connection, prior_tables) == prior_state
        triggers = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        for table in B5_TABLES:
            assert f"trg_{table}_no_update" in triggers
            assert f"trg_{table}_no_delete" in triggers
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_b5_migration_downgrades_only_b5_and_reupgrades_empty(tmp_path):
    database = tmp_path / "b5-roundtrip.db"
    config = _config(database)
    command.upgrade(config, B4_HEAD)
    with sqlite3.connect(database) as connection:
        _insert_b4_sentinel(connection)
        connection.commit()
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B5_HEAD)
    command.downgrade(config, B4_HEAD)

    with sqlite3.connect(database) as connection:
        assert not (B5_TABLES & _tables(connection))
        assert _table_state(connection, prior_tables) == prior_state
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B4_HEAD,)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    command.upgrade(config, B5_HEAD)
    with sqlite3.connect(database) as connection:
        assert B5_TABLES <= _tables(connection)
        assert all(
            connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            == 0
            for table in B5_TABLES
        )
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B5_HEAD,)


def test_b5_database_guards_authority_shapes_and_append_only_history(tmp_path):
    database = tmp_path / "b5-constraints.db"
    config = _config(database)
    command.upgrade(config, B5_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_method_prerequisites(connection)
        _insert_method_authority(connection)
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_analytical_method_authorities "
                "SET status=status WHERE id='b5-method-authority'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM lab_analytical_method_authorities "
                "WHERE id='b5-method-authority'"
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_analytical_method_authority_status",
        ):
            _insert_method_authority(
                connection,
                row_id="b5-bad-method-status",
                status="CLAIMED",
                content_sha256="1" * 64,
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_method_validation_source_sha256",
        ):
            connection.execute(
                """
                INSERT INTO lab_method_validation_records (
                    id, created_at, method_authority_id, intended_claim,
                    matrix_scope_json, scope_sha256, characteristics_json,
                    acceptance_criteria_json, result, limitations_json,
                    measurement_uncertainty_json, reviewer_pseudonym,
                    reviewed_at, source_document_version_id,
                    source_locator_json, source_artifact_sha256,
                    content_sha256
                ) VALUES (
                    'b5-bad-validation-source', CURRENT_TIMESTAMP,
                    'b5-method-authority', 'identity', '{}', ?, '{}', '{}',
                    'PASS', '[]', '{}', 'reviewer', CURRENT_TIMESTAMP,
                    'b5-source-version', '{}', 'bad-digest', ?
                )
                """,
                ("4" * 64, "5" * 64),
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_gco_event_authority_no_exact_identity",
        ):
            connection.execute(
                """
                INSERT INTO lab_gco_event_authorities (
                    id, created_at, gco_event_id,
                    analytical_run_authority_id, assessor_training_state,
                    window_basis, window_start, window_end,
                    detection_method, replicate_index, replicate_count,
                    detection_frequency, repeatability_json,
                    aligned_peak_ids_json, unknown_event,
                    exact_identity_claim, content_sha256
                ) VALUES (
                    'b5-bad-gco', CURRENT_TIMESTAMP, 'missing-gco',
                    'missing-run-authority', 'QUALIFIED', 'RETENTION_TIME',
                    1.0, 1.5, 'sniffing', 1, 1, 1.0, '{}', '[]', 0, 1, ?
                )
                """,
                ("2" * 64,),
            )
        connection.rollback()

        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_analytical_claim_assessment_withheld_result",
        ):
            connection.execute(
                """
                INSERT INTO lab_analytical_claim_assessments (
                    id, created_at, analytical_run_id, run_authority_id,
                    peak_authority_id, claim_type, policy_version, decision,
                    scope_json, missing_requirements_json,
                    qualifications_json, details_json, upstream_hashes_json,
                    result_json, reviewer_pseudonym, reviewed_at,
                    evidence_record_id, content_sha256
                ) VALUES (
                    'b5-bad-claim', CURRENT_TIMESTAMP, 'missing-run',
                    'missing-run-authority', 'missing-peak-authority',
                    'IDENTITY', 'b5-policy-v1', 'WITHHELD', '{}', '[]',
                    '[]', '{}', '{}', '{}', 'reviewer',
                    CURRENT_TIMESTAMP, 'b5-evidence', ?
                )
                """,
                ("3" * 64,),
            )


def test_b5_migration_matches_models_columns_checks_indexes_uniques_and_fks(
    tmp_path,
):
    database = tmp_path / "b5-parity.db"
    config = _config(database)
    command.upgrade(config, B5_HEAD)

    with sqlite3.connect(database) as connection:
        for model in B5_MODELS:
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
                if constraint.__class__.__name__ == "CheckConstraint"
            }

            assert _unique_column_sets(connection, table_name) == {
                tuple(column.name for column in constraint.columns)
                for constraint in model.__table__.constraints
                if constraint.__class__.__name__ == "UniqueConstraint"
            }
            assert _foreign_keys(connection, table_name) == _model_foreign_keys(
                model
            )


def test_b5_migration_is_explicit_and_imports_zero_prior_rows():
    migration_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260731_0009_b5_analytical_authority.py"
    )
    source = migration_path.read_text(encoding="utf-8")
    lowered = source.casefold()

    assert "app.models" not in lowered
    assert "base.metadata" not in lowered
    assert "checkfirst" not in lowered
    assert "bulk_insert" not in lowered
    for table_name in B5_TABLES:
        assert table_name in source
        assert f"insert into {table_name}" not in lowered
