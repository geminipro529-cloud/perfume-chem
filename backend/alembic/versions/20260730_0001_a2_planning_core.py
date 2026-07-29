"""Add the immutable A2 canonical planning core."""

import sqlalchemy as sa

from alembic import op

revision = "20260730_0001"
down_revision = "20260717_0001"
branch_labels = None
depends_on = None


BUILD_PLAN_STATUSES = (
    "DRAFT",
    "UNDER_REVIEW",
    "APPROVED",
    "RESERVED",
    "EXECUTING",
    "CLOSED",
    "SUPERSEDED",
    "CANCELLED",
)
RESERVATION_STATES = ("RESERVED", "RELEASED", "FULFILLED", "CANCELLED")
UNAVAILABLE_INVENTORY_STATUSES = (
    "EXACT_IDENTITY_NOT_IN_STOCK",
    "NO_SUITABLE_STOCK",
)
PLANNING_TABLES = (
    "lab_target_hypothesis_versions",
    "lab_target_lines",
    "lab_target_evidence_links",
    "lab_accepted_target_versions",
    "lab_formula_version_edges",
    "lab_inventory_mapping_versions",
    "lab_inventory_mapping_evidence_links",
    "lab_build_plan_versions",
    "lab_build_plan_lines",
    "lab_build_plan_evidence_links",
    "lab_inventory_reservation_events",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _record_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _create_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger_name = f"trg_{table_name}_{operation.lower()}_append_only"
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE {operation} ON {table_name}
            BEGIN
                SELECT RAISE(ABORT, 'append-only: {table_name}');
            END
            """
        )


def _drop_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger_name = f"trg_{table_name}_{operation.lower()}_append_only"
        op.execute(f"DROP TRIGGER {trigger_name}")


def upgrade() -> None:
    op.create_table(
        "lab_target_hypothesis_versions",
        *_record_columns(),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("product_key", sa.String(length=255), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column(
            "provenance_activity_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "uncertainty_summary_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1", name="ck_lab_target_version_positive"
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_target_hypothesis_versions.id"],
            name="fk_lab_target_version_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_target_hypothesis_versions"),
        sa.UniqueConstraint(
            "target_id", "version_number", name="uq_lab_target_version"
        ),
        sa.UniqueConstraint(
            "content_sha256", name="uq_lab_target_version_content_sha256"
        ),
    )
    op.create_index(
        "ix_lab_target_hypothesis_versions_target_id",
        "lab_target_hypothesis_versions",
        ["target_id"],
        unique=False,
    )

    op.create_table(
        "lab_target_lines",
        *_record_columns(),
        sa.Column("line_id", sa.String(length=255), nullable=False),
        sa.Column(
            "target_hypothesis_version_id", sa.String(length=36), nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("target_identity", sa.String(length=255), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("grade", sa.String(length=100), nullable=False),
        sa.Column("presence_probability", sa.Float(), nullable=False),
        sa.Column("target_raw_quantity", sa.Float(), nullable=False),
        sa.Column("target_active_quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("concentration_fraction", sa.Float(), nullable=False),
        sa.Column("concentration_basis", sa.String(length=80), nullable=False),
        sa.Column(
            "functional_roles_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "uncertainty_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 1 AND target_raw_quantity >= 0 "
            "AND target_active_quantity >= 0 "
            "AND target_active_quantity <= target_raw_quantity",
            name="ck_lab_target_line_quantities",
        ),
        sa.CheckConstraint(
            "presence_probability >= 0 AND presence_probability <= 1 "
            "AND concentration_fraction >= 0 AND concentration_fraction <= 1",
            name="ck_lab_target_line_fractions",
        ),
        sa.ForeignKeyConstraint(
            ["target_hypothesis_version_id"],
            ["lab_target_hypothesis_versions.id"],
            name="fk_lab_target_line_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_target_lines"),
        sa.UniqueConstraint(
            "target_hypothesis_version_id",
            "position",
            name="uq_lab_target_line_position",
        ),
        sa.UniqueConstraint(
            "target_hypothesis_version_id",
            "line_id",
            name="uq_lab_target_line_identity",
        ),
        sa.UniqueConstraint(
            "id",
            "target_hypothesis_version_id",
            name="uq_lab_target_line_id_version",
        ),
    )

    op.create_table(
        "lab_target_evidence_links",
        *_record_columns(),
        sa.Column(
            "target_hypothesis_version_id", sa.String(length=36), nullable=False
        ),
        sa.Column("target_line_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_hypothesis_version_id"],
            ["lab_target_hypothesis_versions.id"],
            name="fk_lab_target_evidence_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_line_id", "target_hypothesis_version_id"],
            [
                "lab_target_lines.id",
                "lab_target_lines.target_hypothesis_version_id",
            ],
            name="fk_lab_target_evidence_line_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            name="fk_lab_target_evidence_record",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_target_evidence_links"),
        sa.UniqueConstraint(
            "target_hypothesis_version_id",
            "target_line_id",
            "evidence_record_id",
            name="uq_lab_target_evidence_link",
        ),
    )

    op.create_table(
        "lab_accepted_target_versions",
        *_record_columns(),
        sa.Column("accepted_target_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "target_hypothesis_version_id", sa.String(length=36), nullable=False
        ),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("reviewer", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_accepted_target_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["target_hypothesis_version_id"],
            ["lab_target_hypothesis_versions.id"],
            name="fk_lab_accepted_target_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_accepted_target_versions.id"],
            name="fk_lab_accepted_target_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_accepted_target_versions"),
        sa.UniqueConstraint(
            "target_hypothesis_version_id",
            name="uq_lab_accepted_target_version",
        ),
        sa.UniqueConstraint(
            "accepted_target_id",
            "version_number",
            name="uq_lab_accepted_target_identity",
        ),
        sa.UniqueConstraint(
            "id",
            "target_hypothesis_version_id",
            name="uq_lab_accepted_target_id_target",
        ),
    )
    op.create_index(
        "ix_lab_accepted_target_versions_accepted_target_id",
        "lab_accepted_target_versions",
        ["accepted_target_id"],
        unique=False,
    )

    op.create_table(
        "lab_formula_version_edges",
        *_record_columns(),
        sa.Column("child_version_id", sa.String(length=36), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=False),
        sa.Column("relationship_kind", sa.String(length=80), nullable=False),
        sa.Column(
            "change_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "child_version_id <> parent_version_id",
            name="ck_lab_formula_version_edge_not_self",
        ),
        sa.ForeignKeyConstraint(
            ["child_version_id"],
            ["lab_formula_versions.id"],
            name="fk_lab_formula_edge_child",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_formula_versions.id"],
            name="fk_lab_formula_edge_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_formula_version_edges"),
        sa.UniqueConstraint(
            "child_version_id",
            "parent_version_id",
            name="uq_lab_formula_version_edge",
        ),
    )

    op.create_table(
        "lab_inventory_mapping_versions",
        *_record_columns(),
        sa.Column("mapping_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("target_line_id", sa.String(length=36), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=True),
        sa.Column("target_identity", sa.String(length=255), nullable=False),
        sa.Column("build_identity", sa.String(length=255), nullable=False),
        sa.Column("identity_status", sa.String(length=80), nullable=False),
        sa.Column("inventory_status", sa.String(length=80), nullable=False),
        sa.Column("substitution_class", sa.String(length=80), nullable=False),
        sa.Column(
            "preserved_functions_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "lost_functions_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1", name="ck_lab_mapping_version_positive"
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_lab_mapping_confidence",
        ),
        sa.CheckConstraint(
            "("
            "stock_solution_id IS NOT NULL AND inventory_status NOT IN "
            f"({_quoted(UNAVAILABLE_INVENTORY_STATUSES)})"
            ") OR ("
            "stock_solution_id IS NULL AND inventory_status IN "
            f"({_quoted(UNAVAILABLE_INVENTORY_STATUSES)})"
            ")",
            name="ck_lab_mapping_stock_status",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_inventory_mapping_versions.id"],
            name="fk_lab_mapping_parent",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_line_id"],
            ["lab_target_lines.id"],
            name="fk_lab_mapping_target_line",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            name="fk_lab_mapping_stock",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_inventory_mapping_versions"),
        sa.UniqueConstraint(
            "mapping_id", "version_number", name="uq_lab_mapping_version"
        ),
    )
    op.create_index(
        "ix_lab_inventory_mapping_versions_mapping_id",
        "lab_inventory_mapping_versions",
        ["mapping_id"],
        unique=False,
    )

    op.create_table(
        "lab_inventory_mapping_evidence_links",
        *_record_columns(),
        sa.Column(
            "inventory_mapping_version_id", sa.String(length=36), nullable=False
        ),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["inventory_mapping_version_id"],
            ["lab_inventory_mapping_versions.id"],
            name="fk_lab_mapping_evidence_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            name="fk_lab_mapping_evidence_record",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_lab_inventory_mapping_evidence_links"
        ),
        sa.UniqueConstraint(
            "inventory_mapping_version_id",
            "evidence_record_id",
            name="uq_lab_mapping_evidence_link",
        ),
    )

    op.create_table(
        "lab_build_plan_versions",
        *_record_columns(),
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column(
            "target_hypothesis_version_id", sa.String(length=36), nullable=False
        ),
        sa.Column(
            "accepted_target_version_id", sa.String(length=36), nullable=False
        ),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("reviewer", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "provenance_activity_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("inventory_snapshot_ref", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "uncertainty_summary_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_build_plan_version_positive",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(BUILD_PLAN_STATUSES)})",
            name="ck_lab_build_plan_status",
        ),
        sa.ForeignKeyConstraint(
            ["target_hypothesis_version_id"],
            ["lab_target_hypothesis_versions.id"],
            name="fk_lab_build_plan_target",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_target_version_id", "target_hypothesis_version_id"],
            [
                "lab_accepted_target_versions.id",
                "lab_accepted_target_versions.target_hypothesis_version_id",
            ],
            name="fk_lab_build_plan_acceptance_target",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_build_plan_versions.id"],
            name="fk_lab_build_plan_parent",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_build_plan_versions"),
        sa.UniqueConstraint(
            "plan_id", "version_number", name="uq_lab_build_plan_version"
        ),
        sa.UniqueConstraint(
            "content_sha256", name="uq_lab_build_plan_content_sha256"
        ),
    )
    op.create_index(
        "ix_lab_build_plan_versions_plan_id",
        "lab_build_plan_versions",
        ["plan_id"],
        unique=False,
    )

    op.create_table(
        "lab_build_plan_lines",
        *_record_columns(),
        sa.Column("line_id", sa.String(length=255), nullable=False),
        sa.Column("build_plan_version_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("target_line_id", sa.String(length=36), nullable=False),
        sa.Column("target_identity", sa.String(length=255), nullable=False),
        sa.Column(
            "inventory_mapping_version_id", sa.String(length=36), nullable=False
        ),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("planned_raw_quantity", sa.Float(), nullable=False),
        sa.Column("planned_active_quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("concentration_fraction", sa.Float(), nullable=False),
        sa.Column("concentration_basis", sa.String(length=80), nullable=False),
        sa.Column("density_g_ml", sa.Float(), nullable=True),
        sa.Column("density_source", sa.Text(), nullable=True),
        sa.Column("standard_uncertainty", sa.Float(), nullable=True),
        sa.Column("measurement_method", sa.String(length=100), nullable=False),
        sa.Column("resolution", sa.Float(), nullable=False),
        sa.Column("expected_transfer_loss", sa.Float(), nullable=False),
        sa.Column("substitution_class", sa.String(length=80), nullable=False),
        sa.Column(
            "preserved_functions_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "lost_functions_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reservation_state", sa.String(length=40), nullable=False),
        sa.Column("execution_state", sa.String(length=40), nullable=False),
        sa.CheckConstraint(
            "position >= 1 AND planned_raw_quantity >= 0 "
            "AND planned_active_quantity >= 0 "
            "AND planned_active_quantity <= planned_raw_quantity "
            "AND resolution > 0 AND expected_transfer_loss >= 0",
            name="ck_lab_build_plan_line_quantities",
        ),
        sa.CheckConstraint(
            "concentration_fraction >= 0 AND concentration_fraction <= 1",
            name="ck_lab_build_plan_line_fraction",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_version_id"],
            ["lab_build_plan_versions.id"],
            name="fk_lab_build_line_plan",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_line_id"],
            ["lab_target_lines.id"],
            name="fk_lab_build_line_target",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_mapping_version_id"],
            ["lab_inventory_mapping_versions.id"],
            name="fk_lab_build_line_mapping",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            name="fk_lab_build_line_stock",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_build_plan_lines"),
        sa.UniqueConstraint(
            "build_plan_version_id",
            "position",
            name="uq_lab_build_plan_line_position",
        ),
        sa.UniqueConstraint(
            "build_plan_version_id",
            "line_id",
            name="uq_lab_build_plan_line_identity",
        ),
        sa.UniqueConstraint(
            "id",
            "build_plan_version_id",
            name="uq_lab_build_plan_line_id_version",
        ),
    )

    op.create_table(
        "lab_build_plan_evidence_links",
        *_record_columns(),
        sa.Column("build_plan_version_id", sa.String(length=36), nullable=False),
        sa.Column("build_plan_line_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["build_plan_version_id"],
            ["lab_build_plan_versions.id"],
            name="fk_lab_build_evidence_plan",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_line_id", "build_plan_version_id"],
            [
                "lab_build_plan_lines.id",
                "lab_build_plan_lines.build_plan_version_id",
            ],
            name="fk_lab_build_evidence_line_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            name="fk_lab_build_evidence_record",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lab_build_plan_evidence_links"),
        sa.UniqueConstraint(
            "build_plan_version_id",
            "build_plan_line_id",
            "evidence_record_id",
            name="uq_lab_build_plan_evidence_link",
        ),
    )

    op.create_table(
        "lab_inventory_reservation_events",
        *_record_columns(),
        sa.Column("reservation_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("parent_event_id", sa.String(length=36), nullable=True),
        sa.Column("build_plan_version_id", sa.String(length=36), nullable=False),
        sa.Column("build_plan_line_id", sa.String(length=36), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("reserved_mass_g", sa.Float(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "sequence >= 1", name="ck_lab_reservation_sequence"
        ),
        sa.CheckConstraint(
            "reserved_mass_g > 0", name="ck_lab_reservation_mass"
        ),
        sa.CheckConstraint(
            f"state IN ({_quoted(RESERVATION_STATES)})",
            name="ck_lab_reservation_state",
        ),
        sa.ForeignKeyConstraint(
            ["parent_event_id"],
            ["lab_inventory_reservation_events.id"],
            name="fk_lab_reservation_parent",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_line_id", "build_plan_version_id"],
            [
                "lab_build_plan_lines.id",
                "lab_build_plan_lines.build_plan_version_id",
            ],
            name="fk_lab_reservation_line_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            name="fk_lab_reservation_stock",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name="pk_lab_inventory_reservation_events"
        ),
        sa.UniqueConstraint(
            "reservation_id",
            "sequence",
            name="uq_lab_reservation_sequence",
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_lab_reservation_idempotency"
        ),
        sa.UniqueConstraint(
            "id",
            "reservation_id",
            name="uq_lab_reservation_event_identity",
        ),
    )
    op.create_index(
        "ix_lab_inventory_reservation_events_reservation_id",
        "lab_inventory_reservation_events",
        ["reservation_id"],
        unique=False,
    )

    for table_name in PLANNING_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(PLANNING_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_index(
        "ix_lab_inventory_reservation_events_reservation_id",
        table_name="lab_inventory_reservation_events",
    )
    op.drop_table("lab_inventory_reservation_events")
    op.drop_table("lab_build_plan_evidence_links")
    op.drop_table("lab_build_plan_lines")
    op.drop_index(
        "ix_lab_build_plan_versions_plan_id",
        table_name="lab_build_plan_versions",
    )
    op.drop_table("lab_build_plan_versions")
    op.drop_table("lab_inventory_mapping_evidence_links")
    op.drop_index(
        "ix_lab_inventory_mapping_versions_mapping_id",
        table_name="lab_inventory_mapping_versions",
    )
    op.drop_table("lab_inventory_mapping_versions")
    op.drop_table("lab_formula_version_edges")
    op.drop_index(
        "ix_lab_accepted_target_versions_accepted_target_id",
        table_name="lab_accepted_target_versions",
    )
    op.drop_table("lab_accepted_target_versions")
    op.drop_table("lab_target_evidence_links")
    op.drop_table("lab_target_lines")
    op.drop_index(
        "ix_lab_target_hypothesis_versions_target_id",
        table_name="lab_target_hypothesis_versions",
    )
    op.drop_table("lab_target_hypothesis_versions")
