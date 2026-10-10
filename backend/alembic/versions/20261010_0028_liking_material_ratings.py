"""Store Kenny's liking ratings of single materials smelled on a blotter.

Revision ID: 20261010_0028
Revises: 20261009_0027
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0028"
down_revision: str | None = "20261009_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "liking_material_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("material", sa.String(length=255), nullable=False),
        sa.Column("stock_label", sa.String(length=255), nullable=True),
        sa.Column("strength", sa.String(length=8), nullable=True),
        sa.Column("liking", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.CheckConstraint("liking BETWEEN 1 AND 10", name="ck_liking_material_ratings_liking"),
        sa.CheckConstraint(
            "strength IS NULL OR strength IN ('weak', 'medium', 'strong')",
            name="ck_liking_material_ratings_strength",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_liking_material_ratings_created_at", "liking_material_ratings", ["created_at"]
    )
    op.create_index(
        "ix_liking_material_ratings_material", "liking_material_ratings", ["material"]
    )


def downgrade() -> None:
    op.drop_index("ix_liking_material_ratings_material", table_name="liking_material_ratings")
    op.drop_index("ix_liking_material_ratings_created_at", table_name="liking_material_ratings")
    op.drop_table("liking_material_ratings")
