"""Build B8 append-only prioritized scientific-data backfill campaigns.

Revision ID: 20260731_0012
Revises: 20260731_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0012"
down_revision: str | None = "20260731_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
B8_TABLES = (
    "lab_backfill_campaign_versions",
    "lab_backfill_material_priorities",
    "lab_backfill_priority_signal_links",
    "lab_backfill_gap_items",
    "lab_backfill_dashboard_cells",
)

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


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _record_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _json_object(name: str, *, default: bool = False) -> sa.Column:
    return sa.Column(
        name,
        sa.JSON(),
        server_default=sa.text("'{}'") if default else None,
        nullable=False,
    )


def _json_array(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.JSON(),
        server_default=sa.text("'[]'"),
        nullable=False,
    )


def _create_append_only_triggers(table_name: str) -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}_no_update
        BEFORE UPDATE ON {table_name}
        BEGIN
            SELECT RAISE(ABORT, 'append-only table');
        END
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}_no_delete
        BEFORE DELETE ON {table_name}
        BEGIN
            SELECT RAISE(ABORT, 'append-only table');
        END
        """
    )


def _drop_append_only_triggers(table_name: str) -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete")
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_update")


def upgrade() -> None:
    op.create_table(
        "lab_backfill_campaign_versions",
        *_record_columns(),
        sa.Column("campaign_key", sa.String(length=255), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column(
            "as_of_utc",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "priority_policy_version",
            sa.String(length=100),
            nullable=False,
        ),
        _json_object("priority_policy_json"),
        sa.Column(
            "priority_policy_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "input_snapshot_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("material_count", sa.Integer(), nullable=False),
        sa.Column("signal_count", sa.Integer(), nullable=False),
        sa.Column("gap_count", sa.Integer(), nullable=False),
        sa.Column("dashboard_cell_count", sa.Integer(), nullable=False),
        sa.Column("accepted_exact_count", sa.Integer(), nullable=False),
        sa.Column("accepted_scoped_count", sa.Integer(), nullable=False),
        sa.Column("weak_count", sa.Integer(), nullable=False),
        sa.Column("conflicted_count", sa.Integer(), nullable=False),
        sa.Column("unknown_count", sa.Integer(), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("not_applicable_count", sa.Integer(), nullable=False),
        sa.Column(
            "release_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_pseudonym",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_backfill_campaign_version_positive",
        ),
        sa.CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL "
            "AND parent_sha256 IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL "
            "AND parent_sha256 IS NOT NULL)",
            name="ck_lab_backfill_campaign_chain",
        ),
        sa.CheckConstraint(
            "material_count >= 1 AND signal_count >= 0 "
            "AND gap_count >= 0 AND dashboard_cell_count >= 1",
            name="ck_lab_backfill_campaign_counts",
        ),
        sa.CheckConstraint(
            "accepted_exact_count >= 0 AND accepted_scoped_count >= 0 "
            "AND weak_count >= 0 AND conflicted_count >= 0 "
            "AND unknown_count >= 0 AND missing_count >= 0 "
            "AND not_applicable_count >= 0 "
            "AND gap_count = accepted_exact_count + accepted_scoped_count "
            "+ weak_count + conflicted_count + unknown_count + missing_count "
            "+ not_applicable_count",
            name="ck_lab_backfill_campaign_gap_counts",
        ),
        sa.CheckConstraint(
            "release_authority = 0",
            name="ck_lab_backfill_campaign_no_release",
        ),
        sa.CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 AND reviewed_at IS NOT NULL",
            name="ck_lab_backfill_campaign_review",
        ),
        sa.CheckConstraint(
            "length(priority_policy_sha256) = 64",
            name="ck_lab_backfill_campaign_policy_sha256",
        ),
        sa.CheckConstraint(
            "length(input_snapshot_sha256) = 64",
            name="ck_lab_backfill_campaign_input_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_campaign_content_sha256",
        ),
        sa.CheckConstraint(
            "parent_sha256 IS NULL OR length(parent_sha256) = 64",
            name="ck_lab_backfill_campaign_parent_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_backfill_campaign_versions.id"],
            name="fk_lab_backfill_campaign_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_key",
            "version_number",
            name="uq_lab_backfill_campaign_version",
        ),
        sa.UniqueConstraint(
            "parent_version_id",
            name="uq_lab_backfill_campaign_parent",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_campaign_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_backfill_campaign_key_version",
        "lab_backfill_campaign_versions",
        ["campaign_key", "version_number"],
        unique=False,
    )

    op.create_table(
        "lab_backfill_material_priorities",
        *_record_columns(),
        sa.Column(
            "campaign_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("material_id", sa.String(length=36), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column(
            "primary_priority_class",
            sa.String(length=60),
            nullable=False,
        ),
        _json_object("signal_vector_json"),
        sa.Column("rank_key_json", sa.JSON(), nullable=False),
        sa.Column("rank_key_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "critical_unresolved_gap_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "total_unresolved_gap_count",
            sa.Integer(),
            nullable=False,
        ),
        _json_array("source_references_json"),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "rank >= 1",
            name="ck_lab_backfill_priority_rank",
        ),
        sa.CheckConstraint(
            f"primary_priority_class IN "
            f"({_quoted(BACKFILL_PRIORITY_CLASSES)})",
            name="ck_lab_backfill_priority_class",
        ),
        sa.CheckConstraint(
            "critical_unresolved_gap_count >= 0 "
            "AND total_unresolved_gap_count >= 0 "
            "AND critical_unresolved_gap_count <= total_unresolved_gap_count",
            name="ck_lab_backfill_priority_gap_counts",
        ),
        sa.CheckConstraint(
            "length(rank_key_sha256) = 64",
            name="ck_lab_backfill_priority_rank_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_priority_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"],
            ["lab_backfill_campaign_versions.id"],
            name="fk_lab_backfill_priority_campaign",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["lab_materials.id"],
            name="fk_lab_backfill_priority_material",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_version_id",
            "material_id",
            name="uq_lab_backfill_priority_material",
        ),
        sa.UniqueConstraint(
            "campaign_version_id",
            "rank",
            name="uq_lab_backfill_priority_rank",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_priority_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_backfill_priority_campaign_rank",
        "lab_backfill_material_priorities",
        ["campaign_version_id", "rank"],
        unique=False,
    )
    op.create_index(
        "ix_lab_backfill_priority_material",
        "lab_backfill_material_priorities",
        ["material_id"],
        unique=False,
    )

    op.create_table(
        "lab_backfill_priority_signal_links",
        *_record_columns(),
        sa.Column(
            "material_priority_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("signal_type", sa.String(length=60), nullable=False),
        sa.Column("evidence_class", sa.String(length=40), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=True),
        sa.Column("formula_component_id", sa.String(length=36), nullable=True),
        sa.Column("oav_assessment_id", sa.String(length=36), nullable=True),
        sa.Column("knowledge_rule_id", sa.String(length=36), nullable=True),
        sa.Column(
            "regulatory_snapshot_version_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "analytical_sequence_entry_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column("composition_entry_id", sa.String(length=36), nullable=True),
        sa.Column("prediction_id", sa.String(length=36), nullable=True),
        _json_object("signal_value_json"),
        _json_object("applicability_json", default=True),
        _json_array("limitations_json"),
        sa.Column(
            "upstream_content_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_lab_backfill_signal_position",
        ),
        sa.CheckConstraint(
            f"signal_type IN ({_quoted(BACKFILL_SIGNAL_TYPES)})",
            name="ck_lab_backfill_signal_type",
        ),
        sa.CheckConstraint(
            f"evidence_class IN ({_quoted(BACKFILL_EVIDENCE_CLASSES)})",
            name="ck_lab_backfill_signal_evidence_class",
        ),
        sa.CheckConstraint(
            f"({_SIGNAL_SHAPE})",
            name="ck_lab_backfill_signal_shape",
        ),
        sa.CheckConstraint(
            "length(upstream_content_sha256) = 64",
            name="ck_lab_backfill_signal_upstream_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_signal_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["material_priority_id"],
            ["lab_backfill_material_priorities.id"],
            name="fk_lab_backfill_signal_priority",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            name="fk_lab_backfill_signal_stock",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["formula_component_id"],
            ["lab_formula_components.id"],
            name="fk_lab_backfill_signal_formula_component",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["oav_assessment_id"],
            ["lab_oav_assessments.id"],
            name="fk_lab_backfill_signal_oav",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_rule_id"],
            ["lab_knowledge_rules.id"],
            name="fk_lab_backfill_signal_rule",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["regulatory_snapshot_version_id"],
            ["lab_regulatory_snapshot_versions.id"],
            name="fk_lab_backfill_signal_regulatory",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_sequence_entry_id"],
            ["lab_analytical_sequence_entries.id"],
            name="fk_lab_backfill_signal_analytical",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["composition_entry_id"],
            ["lab_regulatory_composition_entries.id"],
            name="fk_lab_backfill_signal_composition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["lab_predictions.id"],
            name="fk_lab_backfill_signal_prediction",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_priority_id",
            "position",
            name="uq_lab_backfill_signal_position",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_signal_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_backfill_signal_priority",
        "lab_backfill_priority_signal_links",
        ["material_priority_id", "position"],
        unique=False,
    )
    op.create_index(
        "ix_lab_backfill_signal_type",
        "lab_backfill_priority_signal_links",
        ["signal_type"],
        unique=False,
    )

    op.create_table(
        "lab_backfill_gap_items",
        *_record_columns(),
        sa.Column(
            "material_priority_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("requirement_type", sa.String(length=60), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("evidence_class", sa.String(length=40), nullable=False),
        sa.Column(
            "claim_authority_version_id",
            sa.String(length=36),
            nullable=True,
        ),
        _json_object("applicability_scope_json"),
        sa.Column(
            "applicability_scope_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        _json_array("conflicts_json"),
        sa.Column("conflict_count", sa.Integer(), nullable=False),
        _json_array("missing_requirements_json"),
        sa.Column("missing_requirement_count", sa.Integer(), nullable=False),
        _json_array("source_references_json"),
        sa.Column(
            "upstream_content_sha256",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_lab_backfill_gap_position",
        ),
        sa.CheckConstraint(
            f"requirement_type IN ({_quoted(BACKFILL_REQUIREMENT_TYPES)})",
            name="ck_lab_backfill_gap_requirement",
        ),
        sa.CheckConstraint(
            f"state IN ({_quoted(BACKFILL_GAP_STATES)})",
            name="ck_lab_backfill_gap_state",
        ),
        sa.CheckConstraint(
            f"evidence_class IN ({_quoted(BACKFILL_EVIDENCE_CLASSES)})",
            name="ck_lab_backfill_gap_evidence_class",
        ),
        sa.CheckConstraint(
            "(state IN ('ACCEPTED_SCOPED', 'ACCEPTED_EXACT') "
            "AND claim_authority_version_id IS NOT NULL "
            "AND upstream_content_sha256 IS NOT NULL) OR "
            "(state NOT IN ('ACCEPTED_SCOPED', 'ACCEPTED_EXACT') "
            "AND claim_authority_version_id IS NULL "
            "AND upstream_content_sha256 IS NULL)",
            name="ck_lab_backfill_gap_authority_shape",
        ),
        sa.CheckConstraint(
            "conflict_count >= 0 AND missing_requirement_count >= 0",
            name="ck_lab_backfill_gap_counts",
        ),
        sa.CheckConstraint(
            "length(applicability_scope_sha256) = 64",
            name="ck_lab_backfill_gap_scope_sha256",
        ),
        sa.CheckConstraint(
            "upstream_content_sha256 IS NULL "
            "OR length(upstream_content_sha256) = 64",
            name="ck_lab_backfill_gap_upstream_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_gap_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["material_priority_id"],
            ["lab_backfill_material_priorities.id"],
            name="fk_lab_backfill_gap_priority",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["claim_authority_version_id"],
            ["lab_claim_authority_versions.id"],
            name="fk_lab_backfill_gap_claim_authority",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "material_priority_id",
            "requirement_type",
            name="uq_lab_backfill_gap_requirement",
        ),
        sa.UniqueConstraint(
            "material_priority_id",
            "position",
            name="uq_lab_backfill_gap_position",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_gap_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_backfill_gap_priority",
        "lab_backfill_gap_items",
        ["material_priority_id", "position"],
        unique=False,
    )
    op.create_index(
        "ix_lab_backfill_gap_requirement_state",
        "lab_backfill_gap_items",
        ["requirement_type", "state"],
        unique=False,
    )

    op.create_table(
        "lab_backfill_dashboard_cells",
        *_record_columns(),
        sa.Column(
            "campaign_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("dimension_key", sa.Text(), nullable=False),
        sa.Column("material_count", sa.Integer(), nullable=False),
        sa.Column("requirements_total", sa.Integer(), nullable=False),
        sa.Column("accepted_exact_count", sa.Integer(), nullable=False),
        sa.Column("accepted_scoped_count", sa.Integer(), nullable=False),
        sa.Column("weak_count", sa.Integer(), nullable=False),
        sa.Column("conflicted_count", sa.Integer(), nullable=False),
        sa.Column("unknown_count", sa.Integer(), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("not_applicable_count", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"dimension IN ({_quoted(BACKFILL_DASHBOARD_DIMENSIONS)})",
            name="ck_lab_backfill_dashboard_dimension",
        ),
        sa.CheckConstraint(
            "length(trim(dimension_key)) > 0 "
            "AND upper(dimension_key) NOT IN "
            "('OVERALL', 'TOTAL_CONFIDENCE', 'COVERAGE_SCORE', "
            "'CONFIDENCE_PERCENT')",
            name="ck_lab_backfill_dashboard_key",
        ),
        sa.CheckConstraint(
            "material_count >= 0 AND requirements_total >= 0 "
            "AND accepted_exact_count >= 0 AND accepted_scoped_count >= 0 "
            "AND weak_count >= 0 AND conflicted_count >= 0 "
            "AND unknown_count >= 0 AND missing_count >= 0 "
            "AND not_applicable_count >= 0",
            name="ck_lab_backfill_dashboard_counts",
        ),
        sa.CheckConstraint(
            "requirements_total = accepted_exact_count "
            "+ accepted_scoped_count + weak_count + conflicted_count "
            "+ unknown_count + missing_count + not_applicable_count",
            name="ck_lab_backfill_dashboard_reconciliation",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_backfill_dashboard_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"],
            ["lab_backfill_campaign_versions.id"],
            name="fk_lab_backfill_dashboard_campaign",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_version_id",
            "dimension",
            "dimension_key",
            name="uq_lab_backfill_dashboard_cell",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_backfill_dashboard_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_backfill_dashboard_dimension",
        "lab_backfill_dashboard_cells",
        ["campaign_version_id", "dimension", "dimension_key"],
        unique=False,
    )

    for table_name in B8_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(B8_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_index(
        "ix_lab_backfill_dashboard_dimension",
        table_name="lab_backfill_dashboard_cells",
    )
    op.drop_table("lab_backfill_dashboard_cells")

    op.drop_index(
        "ix_lab_backfill_gap_requirement_state",
        table_name="lab_backfill_gap_items",
    )
    op.drop_index(
        "ix_lab_backfill_gap_priority",
        table_name="lab_backfill_gap_items",
    )
    op.drop_table("lab_backfill_gap_items")

    op.drop_index(
        "ix_lab_backfill_signal_type",
        table_name="lab_backfill_priority_signal_links",
    )
    op.drop_index(
        "ix_lab_backfill_signal_priority",
        table_name="lab_backfill_priority_signal_links",
    )
    op.drop_table("lab_backfill_priority_signal_links")

    op.drop_index(
        "ix_lab_backfill_priority_material",
        table_name="lab_backfill_material_priorities",
    )
    op.drop_index(
        "ix_lab_backfill_priority_campaign_rank",
        table_name="lab_backfill_material_priorities",
    )
    op.drop_table("lab_backfill_material_priorities")

    op.drop_index(
        "ix_lab_backfill_campaign_key_version",
        table_name="lab_backfill_campaign_versions",
    )
    op.drop_table("lab_backfill_campaign_versions")
