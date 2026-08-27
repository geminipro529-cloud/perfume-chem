from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_backfill import (
    BACKFILL_DASHBOARD_DIMENSIONS,
    BACKFILL_EVIDENCE_CLASSES,
    BACKFILL_GAP_STATES,
    BACKFILL_REQUIREMENT_TYPES,
    BACKFILL_SIGNAL_TYPES,
    BACKFILL_TABLE_NAMES,
    LabBackfillCampaignVersion,
    LabBackfillDashboardCell,
    LabBackfillGapItem,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
)

EXPECTED_TABLES = {
    "lab_backfill_campaign_versions",
    "lab_backfill_material_priorities",
    "lab_backfill_priority_signal_links",
    "lab_backfill_gap_items",
    "lab_backfill_dashboard_cells",
}


def _constraint_names(model, constraint_type):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type)
    }


def _index_names(model):
    return {index.name for index in model.__table__.indexes}


def test_b8_vocabularies_are_exact():
    assert BACKFILL_SIGNAL_TYPES == (
        "CURRENT_INVENTORY",
        "ACTIVE_FORMULA",
        "SHIPPED_FORMULA",
        "REFERENCE_FORMULA",
        "HIGH_DOSE_STRUCTURE",
        "POTENT_TRACE",
        "REGULATORY_DRIVER",
        "FAMILY_DRIVER",
        "ANALYTICAL_STANDARD",
        "NATURAL_CONSTITUENT",
        "MODEL_SENSITIVITY",
    )
    assert BACKFILL_REQUIREMENT_TYPES == (
        "EXACT_IDENTITY",
        "GRADE_IDENTITY",
        "MOLECULAR_WEIGHT",
        "DENSITY",
        "VAPOR_PRESSURE",
        "CONTEXTUAL_THRESHOLD",
        "SAFETY_DOCUMENTATION",
        "RETENTION_INDEX",
        "ANALYTICAL_REFERENCE",
        "NATURAL_LOT_COMPOSITION",
    )
    assert BACKFILL_GAP_STATES == (
        "MISSING",
        "UNKNOWN",
        "WEAK",
        "CONFLICTED",
        "ACCEPTED_SCOPED",
        "ACCEPTED_EXACT",
        "NOT_APPLICABLE",
    )
    assert BACKFILL_DASHBOARD_DIMENSIONS == (
        "EVIDENCE_CLASS",
        "PROPERTY",
        "CURRENT_INVENTORY",
        "ACTIVE_FORMULA",
        "CHEMICAL_FAMILY",
        "REGULATORY_IMPACT",
        "MODEL_SENSITIVITY",
    )
    assert BACKFILL_EVIDENCE_CLASSES == (
        "MEASURED",
        "LITERATURE_DERIVED",
        "SUPPLIER_PROVIDED",
        "EMPIRICALLY_CALIBRATED",
        "MODEL_ESTIMATED",
        "HEURISTIC",
        "SPECULATIVE",
        "UNKNOWN",
    )


def test_b8_tables_are_registered_and_append_only():
    assert BACKFILL_TABLE_NAMES == EXPECTED_TABLES
    assert EXPECTED_TABLES <= LAB_TABLE_NAMES
    assert EXPECTED_TABLES <= APPEND_ONLY_TABLES
    for table_name in EXPECTED_TABLES:
        table = LabBackfillCampaignVersion.metadata.tables[table_name]
        assert "updated_at" not in table.columns


def test_b8_campaign_exposes_versioned_reconstructable_contract():
    assert {
        "campaign_key",
        "version_number",
        "parent_version_id",
        "name",
        "purpose",
        "as_of_utc",
        "priority_policy_version",
        "priority_policy_json",
        "priority_policy_sha256",
        "input_snapshot_sha256",
        "material_count",
        "signal_count",
        "gap_count",
        "dashboard_cell_count",
        "accepted_exact_count",
        "accepted_scoped_count",
        "weak_count",
        "conflicted_count",
        "unknown_count",
        "missing_count",
        "not_applicable_count",
        "release_authority",
        "reviewer_pseudonym",
        "reviewed_at",
        "content_sha256",
        "parent_sha256",
    } <= set(LabBackfillCampaignVersion.__table__.columns.keys())
    assert {
        "uq_lab_backfill_campaign_version",
        "uq_lab_backfill_campaign_parent",
        "uq_lab_backfill_campaign_content_sha256",
    } <= _constraint_names(LabBackfillCampaignVersion, UniqueConstraint)
    assert {
        "ck_lab_backfill_campaign_version_positive",
        "ck_lab_backfill_campaign_chain",
        "ck_lab_backfill_campaign_counts",
        "ck_lab_backfill_campaign_gap_counts",
        "ck_lab_backfill_campaign_no_release",
        "ck_lab_backfill_campaign_review",
        "ck_lab_backfill_campaign_policy_sha256",
        "ck_lab_backfill_campaign_input_sha256",
        "ck_lab_backfill_campaign_content_sha256",
        "ck_lab_backfill_campaign_parent_sha256",
    } <= _constraint_names(LabBackfillCampaignVersion, CheckConstraint)


def test_b8_material_priority_exposes_rank_and_gap_contract():
    assert {
        "campaign_version_id",
        "material_id",
        "rank",
        "primary_priority_class",
        "signal_vector_json",
        "rank_key_json",
        "rank_key_sha256",
        "critical_unresolved_gap_count",
        "total_unresolved_gap_count",
        "source_references_json",
        "content_sha256",
    } <= set(LabBackfillMaterialPriority.__table__.columns.keys())
    assert {
        "uq_lab_backfill_priority_material",
        "uq_lab_backfill_priority_rank",
        "uq_lab_backfill_priority_content_sha256",
    } <= _constraint_names(LabBackfillMaterialPriority, UniqueConstraint)
    assert {
        "ck_lab_backfill_priority_rank",
        "ck_lab_backfill_priority_class",
        "ck_lab_backfill_priority_gap_counts",
        "ck_lab_backfill_priority_rank_sha256",
        "ck_lab_backfill_priority_content_sha256",
    } <= _constraint_names(LabBackfillMaterialPriority, CheckConstraint)
    assert {
        "ix_lab_backfill_priority_campaign_rank",
        "ix_lab_backfill_priority_material",
    } <= _index_names(LabBackfillMaterialPriority)


def test_b8_signal_link_has_exactly_one_typed_upstream_shape():
    assert {
        "material_priority_id",
        "position",
        "signal_type",
        "evidence_class",
        "stock_solution_id",
        "formula_component_id",
        "oav_assessment_id",
        "knowledge_rule_id",
        "regulatory_snapshot_version_id",
        "analytical_sequence_entry_id",
        "composition_entry_id",
        "prediction_id",
        "signal_value_json",
        "applicability_json",
        "limitations_json",
        "upstream_content_sha256",
        "content_sha256",
    } <= set(LabBackfillPrioritySignalLink.__table__.columns.keys())
    assert {
        "ck_lab_backfill_signal_type",
        "ck_lab_backfill_signal_evidence_class",
        "ck_lab_backfill_signal_shape",
        "ck_lab_backfill_signal_upstream_sha256",
        "ck_lab_backfill_signal_content_sha256",
    } <= _constraint_names(LabBackfillPrioritySignalLink, CheckConstraint)
    targets = {
        element.target_fullname
        for constraint in (
            LabBackfillPrioritySignalLink.__table__.foreign_key_constraints
        )
        for element in constraint.elements
    }
    assert {
        "lab_backfill_material_priorities.id",
        "lab_stock_solutions.id",
        "lab_formula_components.id",
        "lab_oav_assessments.id",
        "lab_knowledge_rules.id",
        "lab_regulatory_snapshot_versions.id",
        "lab_analytical_sequence_entries.id",
        "lab_regulatory_composition_entries.id",
        "lab_predictions.id",
    } <= targets


def test_b8_gap_item_requires_b7_link_only_for_accepted_states():
    assert {
        "material_priority_id",
        "position",
        "requirement_type",
        "state",
        "evidence_class",
        "claim_authority_version_id",
        "applicability_scope_json",
        "applicability_scope_sha256",
        "conflicts_json",
        "conflict_count",
        "missing_requirements_json",
        "missing_requirement_count",
        "source_references_json",
        "upstream_content_sha256",
        "content_sha256",
    } <= set(LabBackfillGapItem.__table__.columns.keys())
    assert {
        "ck_lab_backfill_gap_requirement",
        "ck_lab_backfill_gap_state",
        "ck_lab_backfill_gap_evidence_class",
        "ck_lab_backfill_gap_authority_shape",
        "ck_lab_backfill_gap_counts",
        "ck_lab_backfill_gap_scope_sha256",
        "ck_lab_backfill_gap_upstream_sha256",
        "ck_lab_backfill_gap_content_sha256",
    } <= _constraint_names(LabBackfillGapItem, CheckConstraint)
    targets = {
        element.target_fullname
        for constraint in LabBackfillGapItem.__table__.foreign_key_constraints
        for element in constraint.elements
    }
    assert "lab_claim_authority_versions.id" in targets


def test_b8_dashboard_cells_are_stratified_and_reconciled():
    assert {
        "campaign_version_id",
        "dimension",
        "dimension_key",
        "material_count",
        "requirements_total",
        "accepted_exact_count",
        "accepted_scoped_count",
        "weak_count",
        "conflicted_count",
        "unknown_count",
        "missing_count",
        "not_applicable_count",
        "content_sha256",
    } <= set(LabBackfillDashboardCell.__table__.columns.keys())
    assert {
        "ck_lab_backfill_dashboard_dimension",
        "ck_lab_backfill_dashboard_key",
        "ck_lab_backfill_dashboard_counts",
        "ck_lab_backfill_dashboard_reconciliation",
        "ck_lab_backfill_dashboard_content_sha256",
    } <= _constraint_names(LabBackfillDashboardCell, CheckConstraint)
    assert {
        "uq_lab_backfill_dashboard_cell",
        "uq_lab_backfill_dashboard_content_sha256",
    } <= _constraint_names(LabBackfillDashboardCell, UniqueConstraint)
