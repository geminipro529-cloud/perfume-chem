"""Add exact Checkpoint-2 physical binding and compounding lineage.

Revision ID: 20260923_0017
Revises: 20260810_0016
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_0017"
down_revision: str | None = "20260810_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "lab_build_plan_physical_bindings",
    "lab_stock_preparation_receipts",
    "lab_build_plan_line_physical_bindings",
    "lab_compounding_runs",
    "lab_compounding_command_receipts",
)
UNITS = ("g", "mg", "mL", "uL")
OPERATIONS = ("PRECHARGE", "DIRECT_ADD", "POSTCHARGE", "MASS_ADD")
COMMAND_TYPES = ("TRANSFER", "CANCEL", "RUN_COMPLETE")
COMMAND_STATUSES = ("COMPLETED", "CANCELLED", "HOLD", "REJECTED")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _base_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _authority_columns() -> tuple[sa.Column, sa.Column, sa.Column]:
    return (
        sa.Column(
            "release_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "safety_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "compounding_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
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
        op.execute(
            f"DROP TRIGGER IF EXISTS "
            f"trg_{table_name}_{operation.lower()}_append_only"
        )


def upgrade() -> None:
    op.create_table(
        "lab_build_plan_physical_bindings",
        *_base_columns(),
        sa.Column("build_plan_version_id", sa.String(length=36), nullable=False),
        sa.Column("formula_version_id", sa.String(length=36), nullable=False),
        sa.Column("formula_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "immediate_parent_formula_version_id",
            sa.String(length=36),
        ),
        sa.Column("immediate_parent_sha256", sa.String(length=64)),
        sa.Column("inventory_snapshot_ref", sa.Text(), nullable=False),
        sa.Column(
            "inventory_snapshot_sha256", sa.String(length=64), nullable=False
        ),
        sa.Column(
            "stock_lineage_receipts_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "release_authority_receipt_ids_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("order_policy", sa.String(length=120), nullable=False),
        sa.Column("order_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        *_authority_columns(),
        sa.CheckConstraint(
            "length(formula_sha256) = 64 AND "
            "length(inventory_snapshot_sha256) = 64 AND "
            "length(order_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_build_plan_physical_binding_hashes",
        ),
        sa.CheckConstraint(
            "(immediate_parent_formula_version_id IS NULL AND "
            "immediate_parent_sha256 IS NULL) OR "
            "(immediate_parent_formula_version_id IS NOT NULL AND "
            "length(immediate_parent_sha256) = 64)",
            name="ck_lab_build_plan_physical_parent_shape",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 AND "
            "compounding_authority = 0",
            name="ck_lab_build_plan_physical_no_authority",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_version_id"],
            ["lab_build_plan_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["formula_version_id"],
            ["lab_formula_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["immediate_parent_formula_version_id"],
            ["lab_formula_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "build_plan_version_id",
            name="uq_lab_build_plan_physical_binding_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_build_plan_physical_binding_hash",
        ),
    )
    op.create_index(
        "ix_lab_build_plan_physical_binding_plan",
        "lab_build_plan_physical_bindings",
        ["build_plan_version_id"],
    )

    op.create_table(
        "lab_stock_preparation_receipts",
        *_base_columns(),
        sa.Column("build_plan_version_id", sa.String(length=36), nullable=False),
        sa.Column(
            "parent_stock_solution_id", sa.String(length=36), nullable=False
        ),
        sa.Column(
            "carrier_stock_solution_id", sa.String(length=36), nullable=False
        ),
        sa.Column("prepared_stock_solution_id", sa.String(length=36)),
        sa.Column("basis", sa.String(length=20), nullable=False),
        sa.Column("parent_quantity_decimal", sa.String(length=128), nullable=False),
        sa.Column("parent_quantity_unit", sa.String(length=20), nullable=False),
        sa.Column("carrier_quantity_decimal", sa.String(length=128), nullable=False),
        sa.Column("carrier_quantity_unit", sa.String(length=20), nullable=False),
        sa.Column("result_quantity_decimal", sa.String(length=128), nullable=False),
        sa.Column("result_quantity_unit", sa.String(length=20), nullable=False),
        sa.Column(
            "resulting_active_fraction_decimal",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("density_g_ml_decimal", sa.String(length=128)),
        sa.Column("density_provenance", sa.Text()),
        sa.Column("homogeneity_state", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("operator", sa.String(length=255), nullable=False),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        *_authority_columns(),
        sa.CheckConstraint(
            "basis IN ('W_W', 'V_V')",
            name="ck_lab_stock_preparation_basis",
        ),
        sa.CheckConstraint(
            f"parent_quantity_unit IN ({_quoted(UNITS)}) AND "
            f"carrier_quantity_unit IN ({_quoted(UNITS)}) AND "
            f"result_quantity_unit IN ({_quoted(UNITS)})",
            name="ck_lab_stock_preparation_units",
        ),
        sa.CheckConstraint(
            "homogeneity_state IN ('CONFIRMED', 'UNKNOWN', 'FAILED')",
            name="ck_lab_stock_preparation_homogeneity",
        ),
        sa.CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_stock_preparation_hashes",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 AND "
            "compounding_authority = 0",
            name="ck_lab_stock_preparation_no_authority",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_version_id"],
            ["lab_build_plan_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["carrier_stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prepared_stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key_sha256",
            name="uq_lab_stock_preparation_idempotency",
        ),
        sa.UniqueConstraint(
            "content_sha256", name="uq_lab_stock_preparation_content"
        ),
    )
    op.create_index(
        "ix_lab_stock_preparation_plan",
        "lab_stock_preparation_receipts",
        ["build_plan_version_id", "created_at"],
    )

    op.create_table(
        "lab_build_plan_line_physical_bindings",
        *_base_columns(),
        sa.Column(
            "build_plan_physical_binding_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("build_plan_line_id", sa.String(length=36), nullable=False),
        sa.Column("formula_component_id", sa.String(length=36), nullable=False),
        sa.Column("basket", sa.String(length=40), nullable=False),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column(
            "concentration_fraction_decimal",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("concentration_basis", sa.String(length=80), nullable=False),
        sa.Column("carrier", sa.String(length=255)),
        sa.Column("stock_preparation_receipt_id", sa.String(length=36)),
        sa.Column("amount_decimal", sa.String(length=128), nullable=False),
        sa.Column("amount_unit", sa.String(length=20), nullable=False),
        sa.Column("density_g_ml_decimal", sa.String(length=128)),
        sa.Column("density_provenance", sa.Text()),
        sa.Column("command_sequence", sa.Integer(), nullable=False),
        sa.Column("command_identity_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        *_authority_columns(),
        sa.CheckConstraint(
            "length(basket) >= 2 AND command_sequence >= 1",
            name="ck_lab_build_plan_line_physical_order",
        ),
        sa.CheckConstraint(
            f"operation IN ({_quoted(OPERATIONS)})",
            name="ck_lab_build_plan_line_physical_operation",
        ),
        sa.CheckConstraint(
            f"amount_unit IN ({_quoted(UNITS)})",
            name="ck_lab_build_plan_line_physical_unit",
        ),
        sa.CheckConstraint(
            "length(command_identity_sha256) = 64 AND "
            "length(content_sha256) = 64",
            name="ck_lab_build_plan_line_physical_hashes",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 AND "
            "compounding_authority = 0",
            name="ck_lab_build_plan_line_physical_no_authority",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_physical_binding_id"],
            ["lab_build_plan_physical_bindings.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_line_id"],
            ["lab_build_plan_lines.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["formula_component_id"],
            ["lab_formula_components.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_preparation_receipt_id"],
            ["lab_stock_preparation_receipts.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "build_plan_physical_binding_id",
            "command_sequence",
            name="uq_lab_build_plan_line_physical_sequence",
        ),
        sa.UniqueConstraint(
            "build_plan_physical_binding_id",
            "build_plan_line_id",
            name="uq_lab_build_plan_line_physical_line",
        ),
        sa.UniqueConstraint(
            "command_identity_sha256",
            name="uq_lab_build_plan_line_physical_command",
        ),
    )
    op.create_index(
        "ix_lab_build_plan_line_physical_order",
        "lab_build_plan_line_physical_bindings",
        ["build_plan_physical_binding_id", "command_sequence"],
    )

    op.create_table(
        "lab_compounding_runs",
        *_base_columns(),
        sa.Column("logical_plan_id", sa.String(length=36), nullable=False),
        sa.Column("build_plan_version_id", sa.String(length=36), nullable=False),
        sa.Column("physical_binding_id", sa.String(length=36), nullable=False),
        sa.Column("order_sha256", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        *_authority_columns(),
        sa.CheckConstraint(
            "length(order_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_compounding_run_hashes",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 AND "
            "compounding_authority = 0",
            name="ck_lab_compounding_run_no_authority",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_version_id"],
            ["lab_build_plan_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["physical_binding_id"],
            ["lab_build_plan_physical_bindings.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "logical_plan_id", name="uq_lab_compounding_run_logical_plan"
        ),
        sa.UniqueConstraint(
            "content_sha256", name="uq_lab_compounding_run_content"
        ),
    )
    op.create_index(
        "ix_lab_compounding_run_plan",
        "lab_compounding_runs",
        ["build_plan_version_id", "created_at"],
    )

    op.create_table(
        "lab_compounding_command_receipts",
        *_base_columns(),
        sa.Column("compounding_run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("command_id", sa.String(length=80), nullable=False),
        sa.Column("command_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("line_physical_binding_id", sa.String(length=36)),
        sa.Column("bottle_action_commit_id", sa.String(length=36)),
        sa.Column("reservation_event_id", sa.String(length=36)),
        sa.Column("stock_solution_id", sa.String(length=36)),
        sa.Column("amount_decimal", sa.String(length=128)),
        sa.Column("amount_unit", sa.String(length=20)),
        sa.Column("operator", sa.String(length=255), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "detail_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_receipt_sha256", sa.String(length=64)),
        sa.Column("receipt_sha256", sa.String(length=64), nullable=False),
        *_authority_columns(),
        sa.CheckConstraint(
            "sequence >= 1", name="ck_lab_compounding_receipt_sequence"
        ),
        sa.CheckConstraint(
            f"command_type IN ({_quoted(COMMAND_TYPES)})",
            name="ck_lab_compounding_receipt_type",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(COMMAND_STATUSES)})",
            name="ck_lab_compounding_receipt_status",
        ),
        sa.CheckConstraint(
            f"amount_unit IS NULL OR amount_unit IN ({_quoted(UNITS)})",
            name="ck_lab_compounding_receipt_unit",
        ),
        sa.CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(receipt_sha256) = 64 "
            "AND (parent_receipt_sha256 IS NULL OR "
            "length(parent_receipt_sha256) = 64)",
            name="ck_lab_compounding_receipt_hashes",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 AND "
            "compounding_authority = 0",
            name="ck_lab_compounding_receipt_no_authority",
        ),
        sa.ForeignKeyConstraint(
            ["compounding_run_id"],
            ["lab_compounding_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["line_physical_binding_id"],
            ["lab_build_plan_line_physical_bindings.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["bottle_action_commit_id"],
            ["lab_bottle_action_commits.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_event_id"],
            ["lab_inventory_reservation_events.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "compounding_run_id",
            "sequence",
            name="uq_lab_compounding_receipt_sequence",
        ),
        sa.UniqueConstraint(
            "compounding_run_id",
            "command_id",
            name="uq_lab_compounding_receipt_command",
        ),
        sa.UniqueConstraint(
            "idempotency_key_sha256",
            name="uq_lab_compounding_receipt_idempotency",
        ),
        sa.UniqueConstraint(
            "receipt_sha256", name="uq_lab_compounding_receipt_hash"
        ),
    )
    op.create_index(
        "ix_lab_compounding_receipt_run",
        "lab_compounding_command_receipts",
        ["compounding_run_id", "sequence"],
    )

    for table_name in TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(TABLES):
        _drop_append_only_triggers(table_name)
    op.drop_index(
        "ix_lab_compounding_receipt_run",
        table_name="lab_compounding_command_receipts",
    )
    op.drop_table("lab_compounding_command_receipts")
    op.drop_index(
        "ix_lab_compounding_run_plan", table_name="lab_compounding_runs"
    )
    op.drop_table("lab_compounding_runs")
    op.drop_index(
        "ix_lab_build_plan_line_physical_order",
        table_name="lab_build_plan_line_physical_bindings",
    )
    op.drop_table("lab_build_plan_line_physical_bindings")
    op.drop_index(
        "ix_lab_stock_preparation_plan",
        table_name="lab_stock_preparation_receipts",
    )
    op.drop_table("lab_stock_preparation_receipts")
    op.drop_index(
        "ix_lab_build_plan_physical_binding_plan",
        table_name="lab_build_plan_physical_bindings",
    )
    op.drop_table("lab_build_plan_physical_bindings")
