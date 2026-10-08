"""Record engine worker liveness so the API can tell whether jobs will run.

Revision ID: 20261008_0026
Revises: 20261007_0025
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261008_0026"
down_revision: str | None = "20261007_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lab_engine_workers",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lab_engine_workers_last_seen_at",
        "lab_engine_workers",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lab_engine_workers_last_seen_at", table_name="lab_engine_workers"
    )
    op.drop_table("lab_engine_workers")
