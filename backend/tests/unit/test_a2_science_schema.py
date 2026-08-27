from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

import app.models.lab  # noqa: F401
from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES

SCIENCE_AUTHORITY_TABLES = {
    "lab_analytical_method_versions",
    "lab_analytical_runs",
    "lab_analytical_peaks",
    "lab_analytical_qc_records",
    "lab_analytical_attachments",
    "lab_gco_events",
    "lab_regulatory_assessment_versions",
    "lab_regulatory_findings",
    "lab_claim_assessment_versions",
    "lab_claim_assessment_evidence_links",
}


def _named_constraints(table_name: str, constraint_type: type) -> set[str]:
    return {
        str(constraint.name)
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, constraint_type)
    }


def test_a2_science_authority_tables_are_canonical_and_append_only():
    assert SCIENCE_AUTHORITY_TABLES <= set(Base.metadata.tables)
    assert SCIENCE_AUTHORITY_TABLES <= APPEND_ONLY_TABLES
    for name in SCIENCE_AUTHORITY_TABLES:
        assert "updated_at" not in Base.metadata.tables[name].columns


def test_a2_science_authority_tables_declare_named_checks_and_uniqueness():
    expected = {
        "lab_analytical_method_versions": {
            "uq_lab_analytical_method_version",
            "uq_lab_analytical_method_content_sha256",
            "ck_lab_analytical_method_version_positive",
            "ck_lab_analytical_method_technique",
            "ck_lab_analytical_method_status",
        },
        "lab_analytical_runs": {
            "uq_lab_analytical_run_identity",
            "uq_lab_analytical_run_content_sha256",
            "ck_lab_analytical_run_kind",
            "ck_lab_analytical_run_status",
            "ck_lab_analytical_run_subject",
        },
        "lab_analytical_peaks": {
            "uq_lab_analytical_peak_identity",
            "uq_lab_analytical_peak_content_sha256",
            "uq_lab_analytical_peak_id_run",
            "ck_lab_analytical_peak_nonnegative",
            "ck_lab_analytical_peak_match_score",
            "ck_lab_analytical_peak_identity_state",
            "ck_lab_analytical_peak_confirmed_material",
            "ck_lab_analytical_peak_quantity_basis",
        },
        "lab_analytical_qc_records": {
            "uq_lab_analytical_qc_identity",
            "uq_lab_analytical_qc_content_sha256",
            "ck_lab_analytical_qc_status",
        },
        "lab_analytical_attachments": {
            "uq_lab_analytical_attachment",
            "ck_lab_analytical_attachment_length",
        },
        "lab_gco_events": {
            "uq_lab_gco_event_identity",
            "uq_lab_gco_event_content_sha256",
            "ck_lab_gco_event_position",
            "ck_lab_gco_event_intensity",
        },
        "lab_regulatory_assessment_versions": {
            "uq_lab_regulatory_assessment_version",
            "uq_lab_regulatory_assessment_content_sha256",
            "ck_lab_regulatory_assessment_version_positive",
            "ck_lab_regulatory_assessment_subject_type",
            "ck_lab_regulatory_assessment_standard_state",
            "ck_lab_regulatory_assessment_result_state",
            "ck_lab_regulatory_assessment_concentration",
        },
        "lab_regulatory_findings": {
            "uq_lab_regulatory_finding_identity",
            "uq_lab_regulatory_finding_content_sha256",
            "ck_lab_regulatory_finding_fractions",
            "ck_lab_regulatory_finding_result_state",
            "ck_lab_regulatory_finding_pass_basis",
        },
        "lab_claim_assessment_versions": {
            "uq_lab_claim_assessment_version",
            "uq_lab_claim_assessment_content_sha256",
            "ck_lab_claim_assessment_version_positive",
            "ck_lab_claim_assessment_subject_type",
            "ck_lab_claim_assessment_decision",
            "ck_lab_claim_assessment_review_state",
        },
        "lab_claim_assessment_evidence_links": {
            "uq_lab_claim_assessment_evidence_link",
            "ck_lab_claim_evidence_role",
        },
    }
    for table_name, required in expected.items():
        named = _named_constraints(table_name, (CheckConstraint, UniqueConstraint))
        assert required <= named


def test_a2_science_ownership_uses_composite_foreign_keys():
    expected = {
        "lab_gco_events": "fk_lab_gco_peak_run",
    }
    for table_name, name in expected.items():
        assert name in _named_constraints(table_name, ForeignKeyConstraint)
