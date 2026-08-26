from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_claims import (
    CLAIM_AUTHORITY_DECISIONS,
    CLAIM_AUTHORITY_SUPPORT_KINDS,
    CLAIM_AUTHORITY_SUPPORT_ROLES,
    CLAIM_AUTHORITY_TABLE_NAMES,
    CLAIM_AUTHORITY_TYPES,
    CLAIM_DIMENSION_STATES,
    LabClaimAuthoritySupportLink,
    LabClaimAuthorityVersion,
)

EXPECTED_TABLES = {
    "lab_claim_authority_versions",
    "lab_claim_authority_support_links",
}


def _constraint_names(model, constraint_type):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type)
    }


def _index_names(model):
    return {index.name for index in model.__table__.indexes}


def test_b7_vocabularies_are_exact():
    assert CLAIM_AUTHORITY_TYPES == (
        "EXACT_CHEMICAL_IDENTITY",
        "GRADE_IDENTITY",
        "PROPERTY_VALUE",
        "THRESHOLD",
        "ABOVE_THRESHOLD_SCREENING",
        "ANALYTICAL_IDENTIFICATION",
        "ANALYTICAL_QUANTITATION",
        "NATURAL_CONSTITUENT_PROFILE",
        "KNOWLEDGE_RULE_RECOMMENDATION",
        "REGULATORY_SCREENING",
        "FORMULA_OR_MODEL_COMPARISON",
    )
    assert CLAIM_AUTHORITY_DECISIONS == (
        "ALLOW_EXACT",
        "ALLOW_SCOPED",
        "ADVISORY_ONLY",
        "WITHHOLD_UNKNOWN",
        "BLOCK",
    )
    assert CLAIM_AUTHORITY_SUPPORT_ROLES == (
        "SUPPORTING",
        "CONTRADICTING",
        "LIMITATION",
    )
    assert CLAIM_AUTHORITY_SUPPORT_KINDS == (
        "PROPERTY_ASSERTION",
        "OAV_ASSESSMENT",
        "KNOWLEDGE_RULE",
        "ANALYTICAL_ASSESSMENT",
        "COMPOSITION_PROFILE",
        "REGULATORY_SNAPSHOT",
    )
    assert CLAIM_DIMENSION_STATES == (
        "PASS",
        "FAIL",
        "UNKNOWN",
        "NOT_APPLICABLE",
    )


def test_b7_tables_are_registered_and_append_only():
    assert CLAIM_AUTHORITY_TABLE_NAMES == EXPECTED_TABLES
    assert EXPECTED_TABLES <= LAB_TABLE_NAMES
    assert EXPECTED_TABLES <= APPEND_ONLY_TABLES
    for table_name in EXPECTED_TABLES:
        table = LabClaimAuthorityVersion.metadata.tables[table_name]
        assert "updated_at" not in table.columns


def test_b7_authority_version_exposes_complete_output_contract():
    assert {
        "authority_id",
        "version_number",
        "parent_version_id",
        "legacy_claim_assessment_version_id",
        "schema_version",
        "policy_version",
        "policy_sha256",
        "policy_json",
        "claim_type",
        "subject_type",
        "subject_id",
        "claim_payload_json",
        "identity_scope_json",
        "identity_scope_sha256",
        "condition_scope_json",
        "condition_scope_sha256",
        "claim_scope_sha256",
        "decision",
        "dimension_results_json",
        "supporting_observations_json",
        "conflicts_json",
        "missing_requirements_json",
        "source_references_json",
        "uncertainty_json",
        "permitted_wording",
        "forbidden_wording",
        "blocker_count",
        "conflict_count",
        "missing_requirement_count",
        "critical_unknown_count",
        "support_count",
        "source_reference_count",
        "release_authority",
        "upstream_hashes_json",
        "reviewer_pseudonym",
        "reviewed_at",
        "content_sha256",
        "parent_sha256",
    } <= set(LabClaimAuthorityVersion.__table__.columns.keys())


def test_b7_support_link_exposes_typed_canonical_references():
    assert {
        "claim_authority_version_id",
        "support_kind",
        "role",
        "property_assertion_id",
        "oav_assessment_id",
        "knowledge_rule_id",
        "analytical_assessment_id",
        "composition_profile_id",
        "regulatory_snapshot_version_id",
        "upstream_content_sha256",
        "derived_facts_json",
        "source_references_json",
        "content_sha256",
    } <= set(LabClaimAuthoritySupportLink.__table__.columns.keys())


def test_b7_authority_version_shape_is_fail_closed():
    assert {
        "uq_lab_claim_authority_version",
        "uq_lab_claim_authority_parent",
        "uq_lab_claim_authority_content_sha256",
    } <= _constraint_names(LabClaimAuthorityVersion, UniqueConstraint)
    assert {
        "ck_lab_claim_authority_version_positive",
        "ck_lab_claim_authority_version_chain",
        "ck_lab_claim_authority_type",
        "ck_lab_claim_authority_decision",
        "ck_lab_claim_authority_counts",
        "ck_lab_claim_authority_exact_shape",
        "ck_lab_claim_authority_scoped_shape",
        "ck_lab_claim_authority_withheld_shape",
        "ck_lab_claim_authority_block_shape",
        "ck_lab_claim_authority_no_release",
        "ck_lab_claim_authority_review",
        "ck_lab_claim_authority_policy_sha256",
        "ck_lab_claim_authority_identity_sha256",
        "ck_lab_claim_authority_condition_sha256",
        "ck_lab_claim_authority_scope_sha256",
        "ck_lab_claim_authority_content_sha256",
        "ck_lab_claim_authority_parent_sha256",
    } <= _constraint_names(LabClaimAuthorityVersion, CheckConstraint)
    assert {
        "fk_lab_claim_authority_legacy_assessment",
    } <= _constraint_names(LabClaimAuthorityVersion, ForeignKeyConstraint)
    assert {
        "ix_lab_claim_authority_claim_scope",
        "ix_lab_claim_authority_subject",
    } <= _index_names(LabClaimAuthorityVersion)


def test_b7_support_shape_has_typed_foreign_keys_and_hash_guards():
    assert {
        "uq_lab_claim_authority_support_content_sha256",
    } <= _constraint_names(LabClaimAuthoritySupportLink, UniqueConstraint)
    assert {
        "ck_lab_claim_authority_support_kind",
        "ck_lab_claim_authority_support_role",
        "ck_lab_claim_authority_support_shape",
        "ck_lab_claim_authority_support_upstream_sha256",
        "ck_lab_claim_authority_support_content_sha256",
    } <= _constraint_names(LabClaimAuthoritySupportLink, CheckConstraint)
    targets = {
        element.target_fullname
        for constraint in LabClaimAuthoritySupportLink.__table__.foreign_key_constraints
        for element in constraint.elements
    }
    assert {
        "lab_claim_authority_versions.id",
        "lab_selected_assertions.id",
        "lab_oav_assessments.id",
        "lab_knowledge_rules.id",
        "lab_analytical_claim_assessments.id",
        "lab_regulatory_composition_profiles.id",
        "lab_regulatory_snapshot_versions.id",
    } <= targets
    assert {
        "ix_lab_claim_authority_support_authority",
        "ix_lab_claim_authority_support_kind",
    } <= _index_names(LabClaimAuthoritySupportLink)
