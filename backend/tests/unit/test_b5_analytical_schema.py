from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_analytical import (
    ANALYTICAL_AUTHORITY_TABLE_NAMES,
    LabAnalyticalClaimAssessment,
    LabAnalyticalMethodAuthority,
    LabAnalyticalPeakAuthority,
    LabAnalyticalRunAuthority,
    LabAnalyticalSequence,
    LabAnalyticalSequenceEntry,
    LabGCOEventAuthority,
    LabMethodValidationRecord,
)

EXPECTED_TABLES = {
    "lab_analytical_method_authorities",
    "lab_method_validation_records",
    "lab_analytical_sequences",
    "lab_analytical_sequence_entries",
    "lab_analytical_run_authorities",
    "lab_analytical_peak_authorities",
    "lab_gco_event_authorities",
    "lab_analytical_claim_assessments",
}


def _constraint_names(model, constraint_type):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type)
    }


def _index_names(model):
    return {index.name for index in model.__table__.indexes}


def test_b5_tables_are_registered_and_append_only():
    assert ANALYTICAL_AUTHORITY_TABLE_NAMES == EXPECTED_TABLES
    assert EXPECTED_TABLES <= LAB_TABLE_NAMES
    assert EXPECTED_TABLES <= APPEND_ONLY_TABLES
    for table_name in EXPECTED_TABLES:
        assert "updated_at" not in LabAnalyticalMethodAuthority.metadata.tables[
            table_name
        ].columns


def test_b5_tables_expose_the_complete_authority_fields():
    expected_columns = {
        LabAnalyticalMethodAuthority: {
            "method_version_id",
            "schema_version",
            "status",
            "analyte_scope_json",
            "instrument_json",
            "detector_json",
            "software_json",
            "separation_json",
            "acquisition_json",
            "sample_preparation_json",
            "hs_spme_json",
            "standards_json",
            "calibration_json",
            "response_factors_json",
            "identity_criteria_json",
            "integration_policy_json",
            "qc_plan_json",
            "raw_data_policy_json",
            "source_document_version_id",
            "source_locator_json",
            "source_artifact_sha256",
            "content_sha256",
        },
        LabMethodValidationRecord: {
            "method_authority_id",
            "intended_claim",
            "matrix_scope_json",
            "scope_sha256",
            "characteristics_json",
            "acceptance_criteria_json",
            "result",
            "limitations_json",
            "measurement_uncertainty_json",
            "reviewer_pseudonym",
            "reviewed_at",
            "source_document_version_id",
            "source_locator_json",
            "source_artifact_sha256",
            "content_sha256",
        },
        LabAnalyticalSequence: {
            "sequence_key",
            "method_authority_id",
            "instrument_identifier",
            "status",
            "entry_count",
            "entries_sha256",
            "acquired_at",
            "content_sha256",
        },
        LabAnalyticalSequenceEntry: {
            "sequence_id",
            "injection_order",
            "role",
            "reference",
            "level_json",
            "content_sha256",
        },
        LabAnalyticalRunAuthority: {
            "analytical_run_id",
            "method_authority_id",
            "sequence_id",
            "sequence_entry_id",
            "subject_type",
            "subject_id",
            "subject_stream_sequence",
            "matrix_scope_json",
            "applicability_json",
            "instrument_state_json",
            "processing_details_json",
            "deviation_assessment_json",
            "reviewer_pseudonym",
            "reviewed_at",
            "disposition",
            "raw_vendor_attachment_id",
            "open_export_attachment_id",
            "content_sha256",
        },
        LabAnalyticalPeakAuthority: {
            "analytical_peak_id",
            "analytical_run_authority_id",
            "identity_state",
            "identity_label",
            "stationary_phase",
            "spectrum_json",
            "deconvolution_json",
            "library_candidates_json",
            "exact_mass_json",
            "authentic_standard_state",
            "co_injection_state",
            "quantifier_ions_json",
            "coelution_json",
            "manual_review_json",
            "identity_decision_json",
            "quantitation_state",
            "quantitation_json",
            "applicability_json",
            "reviewer_pseudonym",
            "reviewed_at",
            "content_sha256",
        },
        LabGCOEventAuthority: {
            "gco_event_id",
            "analytical_run_authority_id",
            "assessor_training_state",
            "window_basis",
            "window_start",
            "window_end",
            "detection_method",
            "replicate_index",
            "replicate_count",
            "detection_frequency",
            "repeatability_json",
            "aligned_peak_ids_json",
            "unknown_event",
            "exact_identity_claim",
            "content_sha256",
        },
        LabAnalyticalClaimAssessment: {
            "analytical_run_id",
            "run_authority_id",
            "peak_authority_id",
            "claim_type",
            "policy_version",
            "decision",
            "scope_json",
            "missing_requirements_json",
            "qualifications_json",
            "details_json",
            "upstream_hashes_json",
            "result_json",
            "reviewer_pseudonym",
            "reviewed_at",
            "evidence_record_id",
            "content_sha256",
        },
    }

    for model, required in expected_columns.items():
        assert required <= set(model.__table__.columns.keys())


def test_method_and_validation_authority_shapes_are_constrained():
    assert {
        "uq_lab_analytical_method_authority_version",
        "uq_lab_analytical_method_authority_content_sha256",
    } <= _constraint_names(LabAnalyticalMethodAuthority, UniqueConstraint)
    assert {
        "ck_lab_analytical_method_authority_status",
        "ck_lab_analytical_method_authority_source_sha256",
        "ck_lab_analytical_method_authority_content_sha256",
    } <= _constraint_names(LabAnalyticalMethodAuthority, CheckConstraint)
    assert {
        "uq_lab_method_validation_scope",
        "uq_lab_method_validation_content_sha256",
    } <= _constraint_names(LabMethodValidationRecord, UniqueConstraint)
    assert {
        "ck_lab_method_validation_result",
        "ck_lab_method_validation_scope_sha256",
        "ck_lab_method_validation_source_sha256",
        "ck_lab_method_validation_content_sha256",
        "ck_lab_method_validation_review",
    } <= _constraint_names(LabMethodValidationRecord, CheckConstraint)
    assert {
        "ix_lab_analytical_method_authorities_status",
    } <= _index_names(LabAnalyticalMethodAuthority)
    assert {
        "ix_lab_method_validation_records_method_authority_id",
    } <= _index_names(LabMethodValidationRecord)


def test_sequence_and_run_authority_shapes_are_constrained():
    assert {
        "uq_lab_analytical_sequence_key",
        "uq_lab_analytical_sequence_content_sha256",
    } <= _constraint_names(LabAnalyticalSequence, UniqueConstraint)
    assert {
        "ck_lab_analytical_sequence_status",
        "ck_lab_analytical_sequence_entry_count",
        "ck_lab_analytical_sequence_content_sha256",
    } <= _constraint_names(LabAnalyticalSequence, CheckConstraint)
    assert {
        "uq_lab_analytical_sequence_entry_order",
        "uq_lab_analytical_sequence_entry_content_sha256",
        "uq_lab_analytical_sequence_entry_id_sequence",
    } <= _constraint_names(LabAnalyticalSequenceEntry, UniqueConstraint)
    assert {
        "ck_lab_analytical_sequence_entry_role",
        "ck_lab_analytical_sequence_entry_order",
        "ck_lab_analytical_sequence_entry_content_sha256",
    } <= _constraint_names(LabAnalyticalSequenceEntry, CheckConstraint)
    assert {
        "uq_lab_analytical_run_authority_run",
        "uq_lab_analytical_run_authority_content_sha256",
    } <= _constraint_names(LabAnalyticalRunAuthority, UniqueConstraint)
    assert {
        "ck_lab_analytical_run_authority_subject_type",
        "ck_lab_analytical_run_authority_subject_shape",
        "ck_lab_analytical_run_authority_disposition",
        "ck_lab_analytical_run_authority_raw_distinct",
        "ck_lab_analytical_run_authority_content_sha256",
    } <= _constraint_names(LabAnalyticalRunAuthority, CheckConstraint)
    assert {
        "fk_lab_analytical_run_authority_sequence_entry",
    } <= _constraint_names(LabAnalyticalRunAuthority, ForeignKeyConstraint)
    assert {
        "ix_lab_analytical_sequences_method_authority_id",
    } <= _index_names(LabAnalyticalSequence)
    assert {
        "ix_lab_analytical_sequence_entries_sequence_id",
    } <= _index_names(LabAnalyticalSequenceEntry)
    assert {
        "ix_lab_analytical_run_authorities_sequence_id",
        "ix_lab_analytical_run_authorities_subject",
    } <= _index_names(LabAnalyticalRunAuthority)


def test_peak_gco_and_claim_authority_shapes_are_fail_closed():
    assert {
        "uq_lab_analytical_peak_authority_peak",
        "uq_lab_analytical_peak_authority_content_sha256",
    } <= _constraint_names(LabAnalyticalPeakAuthority, UniqueConstraint)
    assert {
        "ck_lab_analytical_peak_authority_identity_state",
        "ck_lab_analytical_peak_authority_standard_states",
        "ck_lab_analytical_peak_authority_quantitation_state",
        "ck_lab_analytical_peak_authority_confirmed_standard",
        "ck_lab_analytical_peak_authority_content_sha256",
    } <= _constraint_names(LabAnalyticalPeakAuthority, CheckConstraint)
    assert {
        "uq_lab_gco_event_authority_event",
        "uq_lab_gco_event_authority_content_sha256",
    } <= _constraint_names(LabGCOEventAuthority, UniqueConstraint)
    assert {
        "ck_lab_gco_event_authority_training_state",
        "ck_lab_gco_event_authority_window_basis",
        "ck_lab_gco_event_authority_window",
        "ck_lab_gco_event_authority_replicates",
        "ck_lab_gco_event_authority_frequency",
        "ck_lab_gco_event_authority_no_exact_identity",
        "ck_lab_gco_event_authority_content_sha256",
    } <= _constraint_names(LabGCOEventAuthority, CheckConstraint)
    assert {
        "uq_lab_analytical_claim_assessment_content_sha256",
    } <= _constraint_names(LabAnalyticalClaimAssessment, UniqueConstraint)
    assert {
        "ck_lab_analytical_claim_assessment_type",
        "ck_lab_analytical_claim_assessment_decision",
        "ck_lab_analytical_claim_assessment_withheld_result",
        "ck_lab_analytical_claim_assessment_review",
        "ck_lab_analytical_claim_assessment_content_sha256",
    } <= _constraint_names(LabAnalyticalClaimAssessment, CheckConstraint)
    assert {
        "ix_lab_analytical_peak_authorities_identity_state",
    } <= _index_names(LabAnalyticalPeakAuthority)
    assert {
        "ix_lab_gco_event_authorities_training_state",
    } <= _index_names(LabGCOEventAuthority)
    assert {
        "ix_lab_analytical_claim_assessments_run_decision",
    } <= _index_names(LabAnalyticalClaimAssessment)
