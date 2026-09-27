"""Add immutable stock lot, bottle, and homogeneity receipts.

Revision ID: 20260927_0021
Revises: 20260927_0020
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0021"
down_revision: str | None = "20260927_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "lab_stock_lot_physical_receipts"


def _create_append_only_triggers() -> None:
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{TABLE}_{operation.lower()}_append_only
            BEFORE {operation} ON {TABLE}
            BEGIN
                SELECT RAISE(ABORT, 'append-only: {TABLE}');
            END
            """
        )


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("supplier", sa.String(length=255), nullable=False),
        sa.Column("lot_number", sa.String(length=100), nullable=False),
        sa.Column("bottle_identifier", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "active_fraction_decimal", sa.String(length=128), nullable=False
        ),
        sa.Column("fraction_basis", sa.String(length=80), nullable=False),
        sa.Column("carrier", sa.String(length=255)),
        sa.Column("density_g_ml_decimal", sa.String(length=128)),
        sa.Column("density_provenance", sa.Text()),
        sa.Column("preparation_state", sa.String(length=40), nullable=False),
        sa.Column("stock_preparation_receipt_id", sa.String(length=36)),
        sa.Column("homogeneity_state", sa.String(length=30), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("reviewer", sa.String(length=255), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
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
        sa.CheckConstraint(
            "preparation_state IN ('SUPPLIER_AS_SUPPLIED', 'LOCALLY_PREPARED')",
            name="ck_lab_stock_lot_physical_preparation_state",
        ),
        sa.CheckConstraint(
            "homogeneity_state IN ('CONFIRMED', 'NOT_APPLICABLE')",
            name="ck_lab_stock_lot_physical_homogeneity",
        ),
        sa.CheckConstraint(
            "(preparation_state = 'LOCALLY_PREPARED' AND "
            "stock_preparation_receipt_id IS NOT NULL) OR "
            "(preparation_state = 'SUPPLIER_AS_SUPPLIED' AND "
            "stock_preparation_receipt_id IS NULL)",
            name="ck_lab_stock_lot_physical_preparation_receipt_shape",
        ),
        sa.CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_stock_lot_physical_hashes",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 AND "
            "compounding_authority = 0",
            name="ck_lab_stock_lot_physical_no_authority",
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
            "stock_solution_id",
            name="uq_lab_stock_lot_physical_receipt_stock",
        ),
        sa.UniqueConstraint(
            "idempotency_key_sha256",
            name="uq_lab_stock_lot_physical_receipt_idempotency",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_stock_lot_physical_receipt_content",
        ),
    )
    op.create_index(
        "ix_lab_stock_lot_physical_receipt_stock",
        TABLE,
        ["stock_solution_id", "created_at"],
    )
    _create_append_only_triggers()


def downgrade() -> None:
    for operation in ("update", "delete"):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{TABLE}_{operation}_append_only"
        )
    op.drop_index("ix_lab_stock_lot_physical_receipt_stock", table_name=TABLE)
    op.drop_table(TABLE)
