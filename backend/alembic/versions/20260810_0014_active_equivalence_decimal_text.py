"""Add exact decimal text for decision-bearing stock lineage quantities.

Revision ID: 20260810_0014
Revises: 20260810_0013

Existing float values are deliberately not converted or backfilled.  Legacy
rows remain NULL and must be rebound through new immutable source records before
they can issue active-equivalence authority.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260810_0014"
down_revision: str | None = "20260810_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lab_stock_solutions",
        sa.Column(
            "active_fraction_decimal_text",
            sa.String(length=128),
            nullable=True,
        ),
    )
    op.add_column(
        "lab_formula_components",
        sa.Column(
            "requested_mass_g_decimal_text",
            sa.String(length=128),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "lab_formula_components",
        "requested_mass_g_decimal_text",
    )
    op.drop_column(
        "lab_stock_solutions",
        "active_fraction_decimal_text",
    )
