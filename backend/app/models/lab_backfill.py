"""Append-only B8 prioritized scientific-data backfill campaigns."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord, UTCDateTime

BACKFILL_SIGNAL_TYPES = (
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
BACKFILL_REQUIREMENT_TYPES = (
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
BACKFILL_GAP_STATES = (
    "MISSING",
    "UNKNOWN",
    "WEAK",
    "CONFLICTED",
    "ACCEPTED_SCOPED",
    "ACCEPTED_EXACT",
    "NOT_APPLICABLE",
)
BACKFILL_DASHBOARD_DIMENSIONS = (
    "EVIDENCE_CLASS",
    "PROPERTY",
    "CURRENT_INVENTORY",
    "ACTIVE_FORMULA",
    "CHEMICAL_FAMILY",
    "REGULATORY_IMPACT",
    "MODEL_SENSITIVITY",
)
BACKFILL_EVIDENCE_CLASSES = (
    "MEASURED",
    "LITERATURE_DERIVED",
    "SUPPLIER_PROVIDED",
    "EMPIRICALLY_CALIBRATED",
    "MODEL_ESTIMATED",
    "HEURISTIC",
    "SPECULATIVE",
    "UNKNOWN",
)
BACKFILL_PRIORITY_CLASSES = (
    "CURRENT_INVENTORY",
    "ACTIVE_OR_SHIPPED_FORMULA",
    "HIGH_DOSE_STRUCTURE",
    "POTENT_TRACE",
    "REGULATORY_OR_FAMILY_DRIVER",
    "ANALYTICAL_STANDARD",
    "NATURAL_CONSTITUENT",
    "MODEL_SENSITIVITY",
    "UNPRIORITIZED",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabBackfillCampaignVersion(LabRecord):
    __tablename__ = "lab_backfill_campaign_versions"
    __table_args__ = (
        UniqueConstraint(
            "campaign_key",
            "version_number",
            name="uq_lab_backfill_campaign_version",
        ),
        UniqueConstraint(
            "parent_version_id",
            name="uq_lab_backfill_campaign_parent",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_campaign_content_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_backfill_campaign_version_positive",
        ),
        CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL "
            "AND parent_sha256 IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL "
            "AND parent_sha256 IS NOT NULL)",
            name="ck_lab_backfill_campaign_chain",
        ),
        CheckConstraint(
            "material_count >= 1 AND signal_count >= 0 "
            "AND gap_count >= 0 AND dashboard_cell_count >= 1",
            name="ck_lab_backfill_campaign_counts",
        ),
        CheckConstraint(
            "accepted_exact_count >= 0 AND accepted_scoped_count >= 0 "
            "AND weak_count >= 0 AND conflicted_count >= 0 "
            "AND unknown_count >= 0 AND missing_count >= 0 "
            "AND not_applicable_count >= 0 "
            "AND gap_count = accepted_exact_count + accepted_scoped_count "
            "+ weak_count + conflicted_count + unknown_count + missing_count "
            "+ not_applicable_count",
            name="ck_lab_backfill_campaign_gap_counts",
        ),
        CheckConstraint(
            "release_authority = false",
            name="ck_lab_backfill_campaign_no_release",
        ),
        CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 AND reviewed_at IS NOT NULL",
            name="ck_lab_backfill_campaign_review",
        ),
        CheckConstraint(
            "length(priority_policy_sha256) = 64",
            name="ck_lab_backfill_campaign_policy_sha256",
        ),
        CheckConstraint(
            "length(input_snapshot_sha256) = 64",
            name="ck_lab_backfill_campaign_input_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_campaign_content_sha256",
        ),
        CheckConstraint(
            "parent_sha256 IS NULL OR length(parent_sha256) = 64",
            name="ck_lab_backfill_campaign_parent_sha256",
        ),
        Index(
            "ix_lab_backfill_campaign_key_version",
            "campaign_key",
            "version_number",
        ),
    )

    campaign_key: Mapped[str] = mapped_column(String(255), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_backfill_campaign_versions.id",
            ondelete="RESTRICT",
        )
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    as_of_utc: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True),
        nullable=False,
    )
    priority_policy_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    priority_policy_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    priority_policy_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    input_snapshot_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    material_count: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False)
    dashboard_cell_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_exact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_scoped_count: Mapped[int] = mapped_column(Integer, nullable=False)
    weak_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conflicted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unknown_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False)
    not_applicable_count: Mapped[int] = mapped_column(Integer, nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
    )
    reviewer_pseudonym: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabBackfillMaterialPriority(LabRecord):
    __tablename__ = "lab_backfill_material_priorities"
    __table_args__ = (
        UniqueConstraint(
            "campaign_version_id",
            "material_id",
            name="uq_lab_backfill_priority_material",
        ),
        UniqueConstraint(
            "campaign_version_id",
            "rank",
            name="uq_lab_backfill_priority_rank",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_priority_content_sha256",
        ),
        CheckConstraint(
            "rank >= 1",
            name="ck_lab_backfill_priority_rank",
        ),
        CheckConstraint(
            f"primary_priority_class IN ({_quoted(BACKFILL_PRIORITY_CLASSES)})",
            name="ck_lab_backfill_priority_class",
        ),
        CheckConstraint(
            "critical_unresolved_gap_count >= 0 "
            "AND total_unresolved_gap_count >= 0 "
            "AND critical_unresolved_gap_count <= total_unresolved_gap_count",
            name="ck_lab_backfill_priority_gap_counts",
        ),
        CheckConstraint(
            "length(rank_key_sha256) = 64",
            name="ck_lab_backfill_priority_rank_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_priority_content_sha256",
        ),
        Index(
            "ix_lab_backfill_priority_campaign_rank",
            "campaign_version_id",
            "rank",
        ),
        Index(
            "ix_lab_backfill_priority_material",
            "material_id",
        ),
    )

    campaign_version_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_backfill_campaign_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    material_id: Mapped[str] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_priority_class: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
    )
    signal_vector_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    rank_key_json: Mapped[list] = mapped_column(JSON, nullable=False)
    rank_key_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    critical_unresolved_gap_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_unresolved_gap_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    source_references_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


_SIGNAL_SHAPE = (
    "(signal_type = 'CURRENT_INVENTORY' AND stock_solution_id IS NOT NULL "
    "AND formula_component_id IS NULL AND oav_assessment_id IS NULL "
    "AND knowledge_rule_id IS NULL "
    "AND regulatory_snapshot_version_id IS NULL "
    "AND analytical_sequence_entry_id IS NULL "
    "AND composition_entry_id IS NULL AND prediction_id IS NULL) OR "
    "(signal_type IN ('ACTIVE_FORMULA', 'SHIPPED_FORMULA', "
    "'REFERENCE_FORMULA', 'HIGH_DOSE_STRUCTURE') "
    "AND stock_solution_id IS NULL AND formula_component_id IS NOT NULL "
    "AND oav_assessment_id IS NULL AND knowledge_rule_id IS NULL "
    "AND regulatory_snapshot_version_id IS NULL "
    "AND analytical_sequence_entry_id IS NULL "
    "AND composition_entry_id IS NULL AND prediction_id IS NULL) OR "
    "(signal_type = 'POTENT_TRACE' AND stock_solution_id IS NULL "
    "AND formula_component_id IS NULL AND oav_assessment_id IS NOT NULL "
    "AND knowledge_rule_id IS NULL "
    "AND regulatory_snapshot_version_id IS NULL "
    "AND analytical_sequence_entry_id IS NULL "
    "AND composition_entry_id IS NULL AND prediction_id IS NULL) OR "
    "(signal_type = 'FAMILY_DRIVER' AND stock_solution_id IS NULL "
    "AND formula_component_id IS NULL AND oav_assessment_id IS NULL "
    "AND knowledge_rule_id IS NOT NULL "
    "AND regulatory_snapshot_version_id IS NULL "
    "AND analytical_sequence_entry_id IS NULL "
    "AND composition_entry_id IS NULL AND prediction_id IS NULL) OR "
    "(signal_type = 'REGULATORY_DRIVER' AND stock_solution_id IS NULL "
    "AND formula_component_id IS NULL AND oav_assessment_id IS NULL "
    "AND knowledge_rule_id IS NULL "
    "AND regulatory_snapshot_version_id IS NOT NULL "
    "AND analytical_sequence_entry_id IS NULL "
    "AND composition_entry_id IS NULL AND prediction_id IS NULL) OR "
    "(signal_type = 'ANALYTICAL_STANDARD' AND stock_solution_id IS NULL "
    "AND formula_component_id IS NULL AND oav_assessment_id IS NULL "
    "AND knowledge_rule_id IS NULL "
    "AND regulatory_snapshot_version_id IS NULL "
    "AND analytical_sequence_entry_id IS NOT NULL "
    "AND composition_entry_id IS NULL AND prediction_id IS NULL) OR "
    "(signal_type = 'NATURAL_CONSTITUENT' AND stock_solution_id IS NULL "
    "AND formula_component_id IS NULL AND oav_assessment_id IS NULL "
    "AND knowledge_rule_id IS NULL "
    "AND regulatory_snapshot_version_id IS NULL "
    "AND analytical_sequence_entry_id IS NULL "
    "AND composition_entry_id IS NOT NULL AND prediction_id IS NULL) OR "
    "(signal_type = 'MODEL_SENSITIVITY' AND stock_solution_id IS NULL "
    "AND formula_component_id IS NULL AND oav_assessment_id IS NULL "
    "AND knowledge_rule_id IS NULL "
    "AND regulatory_snapshot_version_id IS NULL "
    "AND analytical_sequence_entry_id IS NULL "
    "AND composition_entry_id IS NULL AND prediction_id IS NOT NULL)"
)


class LabBackfillPrioritySignalLink(LabRecord):
    __tablename__ = "lab_backfill_priority_signal_links"
    __table_args__ = (
        UniqueConstraint(
            "material_priority_id",
            "position",
            name="uq_lab_backfill_signal_position",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_signal_content_sha256",
        ),
        CheckConstraint(
            "position >= 1",
            name="ck_lab_backfill_signal_position",
        ),
        CheckConstraint(
            f"signal_type IN ({_quoted(BACKFILL_SIGNAL_TYPES)})",
            name="ck_lab_backfill_signal_type",
        ),
        CheckConstraint(
            f"evidence_class IN ({_quoted(BACKFILL_EVIDENCE_CLASSES)})",
            name="ck_lab_backfill_signal_evidence_class",
        ),
        CheckConstraint(
            f"({_SIGNAL_SHAPE})",
            name="ck_lab_backfill_signal_shape",
        ),
        CheckConstraint(
            "length(upstream_content_sha256) = 64",
            name="ck_lab_backfill_signal_upstream_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_signal_content_sha256",
        ),
        Index(
            "ix_lab_backfill_signal_priority",
            "material_priority_id",
            "position",
        ),
        Index(
            "ix_lab_backfill_signal_type",
            "signal_type",
        ),
    )

    material_priority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_backfill_material_priorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_type: Mapped[str] = mapped_column(String(60), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(40), nullable=False)
    stock_solution_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT")
    )
    formula_component_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_formula_components.id", ondelete="RESTRICT")
    )
    oav_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_oav_assessments.id", ondelete="RESTRICT")
    )
    knowledge_rule_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_knowledge_rules.id", ondelete="RESTRICT")
    )
    regulatory_snapshot_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_regulatory_snapshot_versions.id",
            ondelete="RESTRICT",
        )
    )
    analytical_sequence_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_analytical_sequence_entries.id",
            ondelete="RESTRICT",
        )
    )
    composition_entry_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_regulatory_composition_entries.id",
            ondelete="RESTRICT",
        )
    )
    prediction_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_predictions.id", ondelete="RESTRICT")
    )
    signal_value_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    applicability_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'"),
        nullable=False,
    )
    limitations_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    upstream_content_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabBackfillGapItem(LabRecord):
    __tablename__ = "lab_backfill_gap_items"
    __table_args__ = (
        UniqueConstraint(
            "material_priority_id",
            "requirement_type",
            name="uq_lab_backfill_gap_requirement",
        ),
        UniqueConstraint(
            "material_priority_id",
            "position",
            name="uq_lab_backfill_gap_position",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_gap_content_sha256",
        ),
        CheckConstraint(
            "position >= 1",
            name="ck_lab_backfill_gap_position",
        ),
        CheckConstraint(
            f"requirement_type IN ({_quoted(BACKFILL_REQUIREMENT_TYPES)})",
            name="ck_lab_backfill_gap_requirement",
        ),
        CheckConstraint(
            f"state IN ({_quoted(BACKFILL_GAP_STATES)})",
            name="ck_lab_backfill_gap_state",
        ),
        CheckConstraint(
            f"evidence_class IN ({_quoted(BACKFILL_EVIDENCE_CLASSES)})",
            name="ck_lab_backfill_gap_evidence_class",
        ),
        CheckConstraint(
            "(state IN ('ACCEPTED_SCOPED', 'ACCEPTED_EXACT') "
            "AND claim_authority_version_id IS NOT NULL "
            "AND upstream_content_sha256 IS NOT NULL) OR "
            "(state NOT IN ('ACCEPTED_SCOPED', 'ACCEPTED_EXACT') "
            "AND claim_authority_version_id IS NULL "
            "AND upstream_content_sha256 IS NULL)",
            name="ck_lab_backfill_gap_authority_shape",
        ),
        CheckConstraint(
            "conflict_count >= 0 AND missing_requirement_count >= 0",
            name="ck_lab_backfill_gap_counts",
        ),
        CheckConstraint(
            "length(applicability_scope_sha256) = 64",
            name="ck_lab_backfill_gap_scope_sha256",
        ),
        CheckConstraint(
            "upstream_content_sha256 IS NULL "
            "OR length(upstream_content_sha256) = 64",
            name="ck_lab_backfill_gap_upstream_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_gap_content_sha256",
        ),
        Index(
            "ix_lab_backfill_gap_priority",
            "material_priority_id",
            "position",
        ),
        Index(
            "ix_lab_backfill_gap_requirement_state",
            "requirement_type",
            "state",
        ),
    )

    material_priority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_backfill_material_priorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(40), nullable=False)
    claim_authority_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_claim_authority_versions.id",
            ondelete="RESTRICT",
        )
    )
    applicability_scope_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    applicability_scope_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    conflicts_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_requirements_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    missing_requirement_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    source_references_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    upstream_content_sha256: Mapped[str | None] = mapped_column(String(64))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabBackfillDashboardCell(LabRecord):
    __tablename__ = "lab_backfill_dashboard_cells"
    __table_args__ = (
        UniqueConstraint(
            "campaign_version_id",
            "dimension",
            "dimension_key",
            name="uq_lab_backfill_dashboard_cell",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_dashboard_content_sha256",
        ),
        CheckConstraint(
            f"dimension IN ({_quoted(BACKFILL_DASHBOARD_DIMENSIONS)})",
            name="ck_lab_backfill_dashboard_dimension",
        ),
        CheckConstraint(
            "length(trim(dimension_key)) > 0 "
            "AND upper(dimension_key) NOT IN "
            "('OVERALL', 'TOTAL_CONFIDENCE', 'COVERAGE_SCORE', "
            "'CONFIDENCE_PERCENT')",
            name="ck_lab_backfill_dashboard_key",
        ),
        CheckConstraint(
            "material_count >= 0 AND requirements_total >= 0 "
            "AND accepted_exact_count >= 0 AND accepted_scoped_count >= 0 "
            "AND weak_count >= 0 AND conflicted_count >= 0 "
            "AND unknown_count >= 0 AND missing_count >= 0 "
            "AND not_applicable_count >= 0",
            name="ck_lab_backfill_dashboard_counts",
        ),
        CheckConstraint(
            "requirements_total = accepted_exact_count "
            "+ accepted_scoped_count + weak_count + conflicted_count "
            "+ unknown_count + missing_count + not_applicable_count",
            name="ck_lab_backfill_dashboard_reconciliation",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_dashboard_content_sha256",
        ),
        Index(
            "ix_lab_backfill_dashboard_dimension",
            "campaign_version_id",
            "dimension",
            "dimension_key",
        ),
    )

    campaign_version_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_backfill_campaign_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    dimension: Mapped[str] = mapped_column(String(40), nullable=False)
    dimension_key: Mapped[str] = mapped_column(Text, nullable=False)
    material_count: Mapped[int] = mapped_column(Integer, nullable=False)
    requirements_total: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_exact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_scoped_count: Mapped[int] = mapped_column(Integer, nullable=False)
    weak_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conflicted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unknown_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False)
    not_applicable_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


BACKFILL_TABLE_NAMES = {
    LabBackfillCampaignVersion.__tablename__,
    LabBackfillMaterialPriority.__tablename__,
    LabBackfillPrioritySignalLink.__tablename__,
    LabBackfillGapItem.__tablename__,
    LabBackfillDashboardCell.__tablename__,
}


__all__ = [
    "BACKFILL_DASHBOARD_DIMENSIONS",
    "BACKFILL_EVIDENCE_CLASSES",
    "BACKFILL_GAP_STATES",
    "BACKFILL_PRIORITY_CLASSES",
    "BACKFILL_REQUIREMENT_TYPES",
    "BACKFILL_SIGNAL_TYPES",
    "BACKFILL_TABLE_NAMES",
    "LabBackfillCampaignVersion",
    "LabBackfillDashboardCell",
    "LabBackfillGapItem",
    "LabBackfillMaterialPriority",
    "LabBackfillPrioritySignalLink",
]
