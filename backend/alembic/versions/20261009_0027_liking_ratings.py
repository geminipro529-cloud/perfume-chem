"""Store Kenny's liking ratings and two-bottle picks.

Revision ID: 20261009_0027
Revises: 20261008_0026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261009_0027"
down_revision: str | None = "20261008_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_WINDOWS = "'opening', '1h', '4h'"


def upgrade() -> None:
    op.create_table(
        "liking_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("formula_name", sa.String(length=255), nullable=False),
        sa.Column("formula_key", sa.String(length=255), nullable=False),
        sa.Column("window", sa.String(length=16), nullable=False),
        sa.Column("liking", sa.Integer(), nullable=False),
        sa.Column("complexity", sa.Integer(), nullable=True),
        sa.Column("too_loud", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("material_shares", sa.JSON(), nullable=False),
        sa.Column("crowd_guess", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.CheckConstraint(f"window IN ({_WINDOWS})", name="ck_liking_ratings_window"),
        sa.CheckConstraint("liking BETWEEN 1 AND 10", name="ck_liking_ratings_liking"),
        sa.CheckConstraint(
            "complexity IS NULL OR complexity BETWEEN 1 AND 10",
            name="ck_liking_ratings_complexity",
        ),
        sa.CheckConstraint(
            "crowd_guess IS NULL OR crowd_guess BETWEEN -1 AND 1",
            name="ck_liking_ratings_crowd_guess",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_liking_ratings_created_at", "liking_ratings", ["created_at"])
    op.create_index("ix_liking_ratings_formula_key", "liking_ratings", ["formula_key"])

    op.create_table(
        "liking_picks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window", sa.String(length=16), nullable=False),
        sa.Column("formula_a_name", sa.String(length=255), nullable=False),
        sa.Column("formula_a_key", sa.String(length=255), nullable=False),
        sa.Column("shares_a", sa.JSON(), nullable=False),
        sa.Column("crowd_a", sa.Float(), nullable=True),
        sa.Column("formula_b_name", sa.String(length=255), nullable=False),
        sa.Column("formula_b_key", sa.String(length=255), nullable=False),
        sa.Column("shares_b", sa.JSON(), nullable=False),
        sa.Column("crowd_b", sa.Float(), nullable=True),
        sa.Column("preferred", sa.String(length=8), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(f"window IN ({_WINDOWS})", name="ck_liking_picks_window"),
        sa.CheckConstraint("preferred IN ('a', 'b', 'same')", name="ck_liking_picks_preferred"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_liking_picks_created_at", "liking_picks", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_liking_picks_created_at", table_name="liking_picks")
    op.drop_table("liking_picks")
    op.drop_index("ix_liking_ratings_formula_key", table_name="liking_ratings")
    op.drop_index("ix_liking_ratings_created_at", table_name="liking_ratings")
    op.drop_table("liking_ratings")
