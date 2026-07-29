import sqlite3
from pathlib import Path

import pytest

from alembic import command
from tests.integration.test_a2_planning_migration import (
    _config,
    _integrity,
    _minimum_rows,
    _revision,
    _tables,
)
from tests.unit.test_a2_science_schema import SCIENCE_AUTHORITY_TABLES

BACKEND_ROOT = Path(__file__).resolve().parents[2]
A2_PLANNING_HEAD = "20260730_0001"
A2_SCIENCE_HEAD = "20260730_0002"


def _planning_counts(database) -> tuple[int, int, int]:
    with sqlite3.connect(database) as connection:
        return (
            int(
                connection.execute(
                    "SELECT COUNT(*) FROM lab_target_hypothesis_versions"
                ).fetchone()[0]
            ),
            int(
                connection.execute(
                    "SELECT COUNT(*) FROM lab_build_plan_versions"
                ).fetchone()[0]
            ),
            int(
                connection.execute(
                    "SELECT COUNT(*) FROM lab_inventory_reservation_events"
                ).fetchone()[0]
            ),
        )


def _minimum_science_rows(connection: sqlite3.Connection) -> None:
    timestamp = "2026-07-30T01:00:00+00:00"
    connection.execute(
        """
        INSERT INTO lab_analytical_method_versions (
            id, method_id, version_number, schema_version, technique,
            intended_use, status, method_json, evidence_record_id,
            content_sha256, created_at
        ) VALUES (
            'method-version-1', 'method-1', 1, 'a2-analytical-v1', 'GCMS',
            'Identity support', 'VALIDATED', '{}', 'evidence-1', ?, ?
        )
        """,
        ("a" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_analytical_runs (
            id, run_id, method_version_id, run_kind, status,
            instrument_identifier, acquired_at, parameters_json,
            deviations_json, processing_version, formula_version_id,
            content_sha256, created_at
        ) VALUES (
            'analytical-run-1', 'run-1', 'method-version-1', 'GCMS',
            'QC_ACCEPTED', 'instrument:pseudonymous', ?, '{}', '[]',
            'processor-v1', 'formula-version-1', ?, ?
        )
        """,
        (timestamp, "b" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_analytical_peaks (
            id, analytical_run_id, peak_key, retention_time_minutes,
            retention_index, area, response_factor, qualifier_ions_json,
            tentative_identity, material_id, identity_state, match_score,
            quantitation_basis, quantity, quantity_unit,
            standard_uncertainty, notes, content_sha256, created_at
        ) VALUES (
            'analytical-peak-1', 'analytical-run-1', 'peak-1', 2.5,
            1050.0, 1200.0, 1.0, '[43, 71]', 'Jasmine Absolute',
            'material-1', 'CONFIRMED', 0.95, 'external_standard',
            0.2, 'mass_fraction', 0.01, 'Test peak', ?, ?
        )
        """,
        ("c" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_analytical_qc_records (
            id, analytical_run_id, qc_key, qc_type, status,
            criteria_json, observed_json, evidence_record_id,
            content_sha256, created_at
        ) VALUES (
            'analytical-qc-1', 'analytical-run-1', 'blank', 'BLANK',
            'PASS', '{}', '{}', 'evidence-1', ?, ?
        )
        """,
        ("d" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_analytical_attachments (
            id, analytical_run_id, attachment_kind, media_type,
            byte_length, content_sha256, storage_locator,
            evidence_record_id, created_at
        ) VALUES (
            'analytical-attachment-1', 'analytical-run-1', 'RAW_DATA',
            'application/octet-stream', 100, ?, 'artifact://raw/run-1',
            'evidence-1', ?
        )
        """,
        ("e" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_gco_events (
            id, analytical_run_id, analytical_peak_id, event_key,
            retention_time_minutes, retention_index, descriptor, intensity,
            assessor_pseudonym, repeatability_json, evidence_record_id,
            content_sha256, created_at
        ) VALUES (
            'gco-event-1', 'analytical-run-1', 'analytical-peak-1', 'event-1',
            2.5, 1050.0, 'floral', 0.6, 'assessor-1', '{}',
            'evidence-1', ?, ?
        )
        """,
        ("f" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_regulatory_assessment_versions (
            id, assessment_id, version_number, schema_version,
            subject_type, subject_id, standard_identifier,
            standard_amendment, standard_state, source_evidence_record_id,
            jurisdiction, product_category, concentration_basis,
            finished_product_concentration, effective_date, evaluated_at,
            result_state, assumptions_json, unresolved_json,
            permitted_wording, content_sha256, created_at
        ) VALUES (
            'regulatory-assessment-1', 'regulatory-1', 1,
            'a2-regulatory-v1', 'FORMULA_VERSION', 'formula-version-1',
            'test-standard', '2026-01', 'CURRENT', 'evidence-1',
            'TEST', 'fine-fragrance', 'mass_fraction', 0.2,
            '2026-01-01', ?, 'PASS', '[]', '[]',
            'Passes the named test standard state', ?, ?
        )
        """,
        (timestamp, "1" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_regulatory_findings (
            id, regulatory_assessment_version_id, finding_key,
            material_id, substance_identity, observed_fraction,
            maximum_fraction, concentration_basis, result_state,
            detail, evidence_record_id, content_sha256, created_at
        ) VALUES (
            'regulatory-finding-1', 'regulatory-assessment-1', 'finding-1',
            'material-1', 'Jasmine Absolute', 0.01, 0.02,
            'mass_fraction', 'PASS', 'Within named test limit',
            'evidence-1', ?, ?
        )
        """,
        ("2" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_claim_assessment_versions (
            id, claim_id, version_number, schema_version, claim_type,
            subject_type, subject_id, policy_version, decision,
            authority_json, missing_evidence_json, conflicts_json,
            permitted_wording, forbidden_wording, human_review_state,
            reviewer_pseudonym, reviewed_at, content_sha256, created_at
        ) VALUES (
            'claim-assessment-1', 'claim-1', 1, 'a2-claim-v1',
            'REGULATORY_STATUS', 'REGULATORY_ASSESSMENT',
            'regulatory-assessment-1', 'policy-v1', 'ALLOW_EXACT',
            '{}', '[]', '[]', 'Passes the named test standard state',
            'Unqualified global compliance', 'APPROVED', 'reviewer-1',
            ?, ?, ?
        )
        """,
        (timestamp, "3" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_claim_assessment_evidence_links (
            id, claim_assessment_version_id, evidence_record_id,
            role, created_at
        ) VALUES (
            'claim-evidence-1', 'claim-assessment-1', 'evidence-1',
            'DIRECT', ?
        )
        """,
        (timestamp,),
    )


def test_a2_science_migration_upgrades_empty_database(tmp_path):
    database = tmp_path / "empty.db"
    command.upgrade(_config(database), "head")
    assert _revision(database) == A2_SCIENCE_HEAD
    assert SCIENCE_AUTHORITY_TABLES <= _tables(database)
    assert _integrity(database) == "ok"


def test_a2_science_migration_upgrades_planning_schema_copy(tmp_path):
    database = tmp_path / "planning.db"
    config = _config(database)
    command.upgrade(config, A2_PLANNING_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        connection.commit()
    before = _planning_counts(database)
    command.upgrade(config, "head")
    assert _planning_counts(database) == before
    assert _revision(database) == A2_SCIENCE_HEAD


def test_a2_science_migration_downgrades_to_planning_head(tmp_path):
    database = tmp_path / "rollback.db"
    config = _config(database)
    command.upgrade(config, "head")
    command.downgrade(config, A2_PLANNING_HEAD)
    assert not (SCIENCE_AUTHORITY_TABLES & _tables(database))
    assert _revision(database) == A2_PLANNING_HEAD
    assert _integrity(database) == "ok"


def test_a2_science_migration_installs_append_only_guards(tmp_path):
    database = tmp_path / "append-only.db"
    command.upgrade(_config(database), "head")
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        _minimum_science_rows(connection)
        connection.commit()
        for table_name in sorted(SCIENCE_AUTHORITY_TABLES):
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


def test_a2_science_database_constraints_reject_invalid_rows(tmp_path):
    database = tmp_path / "constraints.db"
    command.upgrade(_config(database), "head")
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        _minimum_science_rows(connection)
        connection.commit()

        invalid_statements = (
            """
            INSERT INTO lab_analytical_method_versions (
                id, method_id, version_number, schema_version, technique,
                intended_use, status, method_json, evidence_record_id,
                content_sha256, created_at
            ) VALUES (
                'bad-method', 'bad-method', 0, 'v1', 'INVALID',
                'Bad', 'INVALID', '{}', 'evidence-1', 'bad', CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_analytical_runs (
                id, run_id, method_version_id, run_kind, status,
                instrument_identifier, acquired_at, parameters_json,
                deviations_json, processing_version, content_sha256, created_at
            ) VALUES (
                'bad-run', 'bad-run', 'method-version-1', 'GCMS', 'ACQUIRED',
                'instrument', CURRENT_TIMESTAMP, '{}', '[]', 'v1',
                'bad-run-sha', CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_analytical_peaks (
                id, analytical_run_id, peak_key, area, qualifier_ions_json,
                identity_state, match_score, quantity, content_sha256, created_at
            ) VALUES (
                'bad-peak', 'analytical-run-1', 'bad-peak', -1, '[]',
                'CONFIRMED', 1.1, 1.0, 'bad-peak-sha', CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_gco_events (
                id, analytical_run_id, event_key, descriptor, intensity,
                assessor_pseudonym, repeatability_json, content_sha256, created_at
            ) VALUES (
                'bad-gco', 'analytical-run-1', 'bad-gco', 'bad', 1.1,
                'assessor', '{}', 'bad-gco-sha', CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_regulatory_assessment_versions (
                id, assessment_id, version_number, schema_version,
                subject_type, subject_id, standard_identifier, standard_state,
                jurisdiction, product_category, concentration_basis,
                finished_product_concentration, evaluated_at, result_state,
                assumptions_json, unresolved_json, content_sha256, created_at
            ) VALUES (
                'bad-regulatory', 'bad-regulatory', 1, 'v1',
                'FORMULA_VERSION', 'formula-version-1', 'standard', 'CURRENT',
                'TEST', 'fine-fragrance', 'mass_fraction', -1,
                CURRENT_TIMESTAMP, 'PASS', '[]', '[]', 'bad-regulatory-sha',
                CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_regulatory_findings (
                id, regulatory_assessment_version_id, finding_key,
                substance_identity, result_state, detail, content_sha256,
                created_at
            ) VALUES (
                'bad-finding', 'regulatory-assessment-1', 'bad-finding',
                'Bad', 'PASS', 'Bad', 'bad-finding-sha', CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_claim_assessment_evidence_links (
                id, claim_assessment_version_id, evidence_record_id,
                role, created_at
            ) VALUES (
                'bad-role', 'claim-assessment-1', 'evidence-1',
                'INFERRED', CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_gco_events (
                id, analytical_run_id, analytical_peak_id, event_key,
                descriptor, assessor_pseudonym, repeatability_json,
                content_sha256, created_at
            ) VALUES (
                'bad-membership', 'analytical-run-1', 'missing-peak',
                'bad-membership', 'Bad', 'assessor', '{}',
                'bad-membership-sha', CURRENT_TIMESTAMP
            )
            """,
        )
        for statement in invalid_statements:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)
            connection.rollback()


def test_a2_science_migration_is_frozen_and_explicit():
    revision_path = (
        BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20260730_0002_a2_science_authority.py"
    )
    source = revision_path.read_text(encoding="utf-8")
    assert "app.models" not in source
    assert "Base.metadata" not in source
    assert "checkfirst" not in source
    assert A2_PLANNING_HEAD in source
    for table_name in SCIENCE_AUTHORITY_TABLES:
        assert table_name in source
