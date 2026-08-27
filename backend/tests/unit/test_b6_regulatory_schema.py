from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_regulatory import (
    REGULATORY_AUTHORITY_TABLE_NAMES,
    REGULATORY_RESULT_STATES,
    REGULATORY_SOURCE_STATUSES,
    LabRegulatoryAuthorityFinding,
    LabRegulatoryCompositionEntry,
    LabRegulatoryCompositionProfile,
    LabRegulatoryRuleVersion,
    LabRegulatorySnapshotVersion,
    LabRegulatorySourceVersion,
    LabSupplierDocumentBinding,
)

EXPECTED_TABLES = {
    "lab_regulatory_source_versions",
    "lab_regulatory_rule_versions",
    "lab_supplier_document_bindings",
    "lab_regulatory_composition_profiles",
    "lab_regulatory_composition_entries",
    "lab_regulatory_snapshot_versions",
    "lab_regulatory_authority_findings",
}


def _constraint_names(model, constraint_type):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type)
    }


def _index_names(model):
    return {index.name for index in model.__table__.indexes}


def test_b6_vocabularies_are_exact():
    assert REGULATORY_SOURCE_STATUSES == (
        "CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED",
        "FUTURE_EFFECTIVE",
        "DRAFT",
        "CONSULTATION",
        "WATCHLIST",
        "SUPERSEDED",
    )
    assert REGULATORY_RESULT_STATES == (
        "PASS_FOR_DECLARED_SCOPE",
        "FAIL",
        "UNKNOWN",
        "NOT_EVALUATED",
    )


def test_b6_tables_are_registered_and_append_only():
    assert REGULATORY_AUTHORITY_TABLE_NAMES == EXPECTED_TABLES
    assert EXPECTED_TABLES <= LAB_TABLE_NAMES
    assert EXPECTED_TABLES <= APPEND_ONLY_TABLES
    for table_name in EXPECTED_TABLES:
        assert "updated_at" not in LabRegulatorySourceVersion.metadata.tables[
            table_name
        ].columns


def test_b6_tables_expose_complete_authority_fields():
    expected_columns = {
        LabRegulatorySourceVersion: {
            "authority_id",
            "revision_number",
            "parent_version_id",
            "schema_version",
            "authority_family",
            "identifier",
            "published_version",
            "jurisdiction",
            "status",
            "notified_on",
            "effective_from",
            "effective_through",
            "checked_at",
            "supersedes_source_version_id",
            "official_source_document_version_id",
            "source_locator_json",
            "official_source_sha256",
            "notes_json",
            "content_sha256",
        },
        LabRegulatoryRuleVersion: {
            "rule_id",
            "revision_number",
            "parent_version_id",
            "schema_version",
            "regulatory_source_version_id",
            "rule_family",
            "rule_identifier",
            "material_id",
            "substance_name",
            "cas_number",
            "jurisdiction",
            "product_category",
            "use_classification",
            "concentration_basis",
            "rule_kind",
            "threshold_fraction",
            "maximum_fraction",
            "declaration_wording",
            "effective_from",
            "effective_through",
            "placement_transition_end",
            "availability_transition_end",
            "transition_conditions_json",
            "assumptions_json",
            "content_sha256",
        },
        LabSupplierDocumentBinding: {
            "stock_solution_id",
            "scope",
            "supplier",
            "supplier_product",
            "supplier_product_code",
            "grade",
            "document_type",
            "document_version",
            "lot_number",
            "effective_on",
            "expires_on",
            "source_document_version_id",
            "source_locator_json",
            "source_artifact_sha256",
            "supplier_identity_sha256",
            "content_sha256",
        },
        LabRegulatoryCompositionProfile: {
            "profile_id",
            "version_number",
            "parent_version_id",
            "stock_solution_id",
            "schema_version",
            "origin",
            "composition_basis",
            "completeness",
            "supplier_document_binding_id",
            "assumptions_json",
            "limitations_json",
            "reviewer_pseudonym",
            "reviewed_at",
            "content_sha256",
        },
        LabRegulatoryCompositionEntry: {
            "composition_profile_id",
            "position",
            "projection_family",
            "material_id",
            "constituent_name",
            "cas_number",
            "fraction",
            "fraction_basis",
            "standard_uncertainty",
            "source_locator_json",
            "content_sha256",
        },
        LabRegulatorySnapshotVersion: {
            "snapshot_id",
            "version_number",
            "parent_version_id",
            "schema_version",
            "subject_type",
            "subject_id",
            "legacy_assessment_version_id",
            "primary_source_version_id",
            "standard_identifier",
            "standard_version",
            "official_source_sha256",
            "jurisdiction",
            "product_category",
            "use_classification",
            "finished_product_concentration",
            "constituent_basis",
            "natural_material_assumptions_json",
            "effective_on",
            "evaluated_at",
            "evaluator_software_version",
            "market_action",
            "market_action_on",
            "current_state_source_ids_json",
            "watch_source_ids_json",
            "rule_version_ids_json",
            "supplier_binding_ids_json",
            "composition_profile_ids_json",
            "upstream_hashes_json",
            "unresolved_items_json",
            "result_reasons_json",
            "result_state",
            "permitted_wording",
            "reviewer_pseudonym",
            "reviewed_at",
            "content_sha256",
            "parent_sha256",
        },
        LabRegulatoryAuthorityFinding: {
            "snapshot_version_id",
            "rule_version_id",
            "substance_name",
            "cas_number",
            "observed_fraction",
            "limit_fraction",
            "concentration_basis",
            "source_status",
            "enforced",
            "contribution_lineage_json",
            "reason_codes_json",
            "detail_json",
            "result_state",
            "content_sha256",
        },
    }

    for model, required in expected_columns.items():
        assert required <= set(model.__table__.columns.keys())


def test_source_rule_and_supplier_shapes_are_constrained():
    assert {
        "uq_lab_regulatory_source_version",
        "uq_lab_regulatory_source_content_sha256",
    } <= _constraint_names(LabRegulatorySourceVersion, UniqueConstraint)
    assert {
        "ck_lab_regulatory_source_version_positive",
        "ck_lab_regulatory_source_family",
        "ck_lab_regulatory_source_status",
        "ck_lab_regulatory_source_date_range",
        "ck_lab_regulatory_source_official_sha256",
        "ck_lab_regulatory_source_content_sha256",
        "ck_lab_regulatory_source_version_chain",
    } <= _constraint_names(LabRegulatorySourceVersion, CheckConstraint)
    assert {
        "uq_lab_regulatory_rule_version",
        "uq_lab_regulatory_rule_content_sha256",
    } <= _constraint_names(LabRegulatoryRuleVersion, UniqueConstraint)
    assert {
        "ck_lab_regulatory_rule_family",
        "ck_lab_regulatory_rule_kind",
        "ck_lab_regulatory_rule_shape",
        "ck_lab_regulatory_rule_fraction",
        "ck_lab_regulatory_rule_date_range",
        "ck_lab_regulatory_rule_transition_order",
        "ck_lab_regulatory_rule_content_sha256",
    } <= _constraint_names(LabRegulatoryRuleVersion, CheckConstraint)
    assert {
        "uq_lab_supplier_document_binding_content_sha256",
    } <= _constraint_names(LabSupplierDocumentBinding, UniqueConstraint)
    assert {
        "ck_lab_supplier_document_scope",
        "ck_lab_supplier_document_scope_shape",
        "ck_lab_supplier_document_type",
        "ck_lab_supplier_document_date_range",
        "ck_lab_supplier_document_source_sha256",
        "ck_lab_supplier_document_identity_sha256",
        "ck_lab_supplier_document_content_sha256",
    } <= _constraint_names(LabSupplierDocumentBinding, CheckConstraint)
    assert {
        "ix_lab_regulatory_source_authority_status",
    } <= _index_names(LabRegulatorySourceVersion)
    assert {
        "ix_lab_regulatory_rule_source_family",
    } <= _index_names(LabRegulatoryRuleVersion)
    assert {
        "ix_lab_supplier_document_stock_type",
    } <= _index_names(LabSupplierDocumentBinding)


def test_composition_snapshot_and_finding_shapes_are_fail_closed():
    assert {
        "uq_lab_regulatory_composition_profile_version",
        "uq_lab_regulatory_composition_profile_content_sha256",
    } <= _constraint_names(LabRegulatoryCompositionProfile, UniqueConstraint)
    assert {
        "ck_lab_regulatory_composition_origin",
        "ck_lab_regulatory_composition_basis",
        "ck_lab_regulatory_composition_completeness",
        "ck_lab_regulatory_composition_shape",
        "ck_lab_regulatory_composition_review",
        "ck_lab_regulatory_composition_content_sha256",
    } <= _constraint_names(LabRegulatoryCompositionProfile, CheckConstraint)
    assert {
        "uq_lab_regulatory_composition_entry_position",
        "uq_lab_regulatory_composition_entry_content_sha256",
    } <= _constraint_names(LabRegulatoryCompositionEntry, UniqueConstraint)
    assert {
        "ck_lab_regulatory_composition_entry_position",
        "ck_lab_regulatory_composition_entry_projection",
        "ck_lab_regulatory_composition_entry_fraction",
        "ck_lab_regulatory_composition_entry_uncertainty",
        "ck_lab_regulatory_composition_entry_content_sha256",
    } <= _constraint_names(LabRegulatoryCompositionEntry, CheckConstraint)
    assert {
        "uq_lab_regulatory_snapshot_version",
        "uq_lab_regulatory_snapshot_content_sha256",
    } <= _constraint_names(LabRegulatorySnapshotVersion, UniqueConstraint)
    assert {
        "ck_lab_regulatory_snapshot_subject_type",
        "ck_lab_regulatory_snapshot_result_state",
        "ck_lab_regulatory_snapshot_market_action",
        "ck_lab_regulatory_snapshot_concentration",
        "ck_lab_regulatory_snapshot_wording",
        "ck_lab_regulatory_snapshot_review",
        "ck_lab_regulatory_snapshot_content_sha256",
        "ck_lab_regulatory_snapshot_parent_sha256",
    } <= _constraint_names(LabRegulatorySnapshotVersion, CheckConstraint)
    assert {
        "uq_lab_regulatory_finding_rule",
        "uq_lab_regulatory_finding_content_sha256",
    } <= _constraint_names(LabRegulatoryAuthorityFinding, UniqueConstraint)
    assert {
        "ck_lab_regulatory_finding_result_state",
        "ck_lab_regulatory_finding_source_status",
        "ck_lab_regulatory_finding_fraction",
        "ck_lab_regulatory_finding_enforcement_shape",
        "ck_lab_regulatory_finding_content_sha256",
    } <= _constraint_names(LabRegulatoryAuthorityFinding, CheckConstraint)
    assert {
        "fk_lab_regulatory_snapshot_legacy_assessment",
    } <= _constraint_names(LabRegulatorySnapshotVersion, ForeignKeyConstraint)
    assert {
        "ix_lab_regulatory_composition_stock",
    } <= _index_names(LabRegulatoryCompositionProfile)
    assert {
        "ix_lab_regulatory_snapshot_subject",
        "ix_lab_regulatory_snapshot_result",
    } <= _index_names(LabRegulatorySnapshotVersion)
    assert {
        "ix_lab_regulatory_finding_snapshot_result",
    } <= _index_names(LabRegulatoryAuthorityFinding)
