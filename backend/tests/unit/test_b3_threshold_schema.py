from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_thresholds import (
    LabLegacyThresholdRecord,
    LabOAVAssessment,
    LabThresholdObservationContext,
)


def _constraint_names(model, constraint_type):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type)
    }


def _index_names(model):
    return {index.name for index in model.__table__.indexes}


def test_b3_tables_are_registered_and_append_only():
    expected = {
        "lab_threshold_observation_contexts",
        "lab_oav_assessments",
        "lab_legacy_threshold_records",
    }

    assert expected <= LAB_TABLE_NAMES
    assert expected <= APPEND_ONLY_TABLES


def test_threshold_context_has_one_to_one_observation_and_content_identity():
    uniques = _constraint_names(
        LabThresholdObservationContext,
        UniqueConstraint,
    )
    checks = _constraint_names(
        LabThresholdObservationContext,
        CheckConstraint,
    )

    assert "uq_lab_threshold_context_observation" in uniques
    assert "uq_lab_threshold_context_content_sha256" in uniques
    assert {
        "ck_lab_threshold_context_endpoint",
        "ck_lab_threshold_context_route",
        "ck_lab_threshold_context_matrix_state",
        "ck_lab_threshold_context_sample_size",
        "ck_lab_threshold_context_content_sha256",
    } <= checks
    assert {
        "ix_lab_threshold_observation_contexts_observation_id"
    } <= _index_names(LabThresholdObservationContext)


def test_oav_assessment_shape_is_fail_closed():
    checks = _constraint_names(LabOAVAssessment, CheckConstraint)

    assert {
        "ck_lab_oav_assessment_status",
        "ck_lab_oav_assessment_shape",
        "ck_lab_oav_assessment_strict",
        "ck_lab_oav_assessment_content_sha256",
    } <= checks
    assert {
        "ix_lab_oav_assessments_concentration_observation_id",
        "ix_lab_oav_assessments_threshold_assertion_id",
    } <= _index_names(LabOAVAssessment)


def test_legacy_record_is_quarantined_by_schema():
    checks = _constraint_names(LabLegacyThresholdRecord, CheckConstraint)

    assert {
        "ck_lab_legacy_threshold_status",
        "ck_lab_legacy_threshold_authority",
        "ck_lab_legacy_threshold_value",
        "ck_lab_legacy_threshold_content_sha256",
    } <= checks
    assert {
        "ix_lab_legacy_threshold_records_material_key"
    } <= _index_names(LabLegacyThresholdRecord)
