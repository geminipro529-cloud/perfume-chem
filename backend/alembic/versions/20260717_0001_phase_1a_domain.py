"""Add role/unit columns to lab_formula_components, remaining_mass_g to lab_stock_solutions for Phase 1A domain foundation."""

import sqlalchemy as sa

from alembic import op

revision = "20260717_0001"
down_revision = "20260716_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("lab_formula_components") as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("unit", sa.String(length=20), nullable=True))
    with op.batch_alter_table("lab_stock_solutions") as batch_op:
        batch_op.add_column(sa.Column("remaining_mass_g", sa.Float(), nullable=True))


def downgrade() -> None:
    # SQLite 3.35.0+ supports native DROP COLUMN (current version: 3.50.4).
    # For older SQLite, use batch_alter_table with table recreation.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("ALTER TABLE lab_stock_solutions DROP COLUMN remaining_mass_g")
        op.execute("ALTER TABLE lab_formula_components DROP COLUMN unit")
        op.execute("ALTER TABLE lab_formula_components DROP COLUMN role")
    else:
        with op.batch_alter_table("lab_stock_solutions") as batch_op:
            batch_op.drop_column("remaining_mass_g")
        with op.batch_alter_table("lab_formula_components") as batch_op:
            batch_op.drop_column("unit")
            batch_op.drop_column("role")
