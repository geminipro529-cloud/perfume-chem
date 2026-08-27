"""Add canonical proposal-confirm-measure-commit bottle execution."""

import sqlalchemy as sa

from alembic import op

revision = "20260730_0003"
down_revision = "20260730_0002"
branch_labels = None
depends_on = None

ACTION_TYPES = ("ADD_STOCK",)
CONFIRMATION_DECISIONS = ("CONFIRMED", "REJECTED")
EXECUTION_TABLES = (
    "lab_bottle_action_proposals",
    "lab_bottle_action_confirmations",
    "lab_bottle_action_commits",
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
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")


def upgrade() -> None:
    op.create_table(
        "lab_bottle_action_proposals",
        *_record_columns(),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("reservation_id", sa.String(length=36), nullable=False),
        sa.Column("reservation_event_id", sa.String(length=36), nullable=False),
        sa.Column("bottle_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("planned_mass_g", sa.Float(), nullable=False),
        sa.Column("expected_sequence", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"action_type IN ({_quoted(ACTION_TYPES)})",
            name="ck_lab_bottle_action_proposal_type",
        ),
        sa.CheckConstraint(
            "planned_mass_g > 0",
            name="ck_lab_bottle_action_proposal_mass",
        ),
        sa.CheckConstraint(
            "expected_sequence >= 0",
            name="ck_lab_bottle_action_proposal_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_event_id"],
            ["lab_inventory_reservation_events.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["bottle_id"],
            ["lab_bottles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_lab_bottle_action_proposal_idempotency",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_bottle_action_proposal_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_bottle_action_proposals_reservation_id",
        "lab_bottle_action_proposals",
        ["reservation_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_bottle_action_proposals_bottle_id",
        "lab_bottle_action_proposals",
        ["bottle_id"],
        unique=False,
    )

    op.create_table(
        "lab_bottle_action_confirmations",
        *_record_columns(),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column("confirmer_pseudonym", sa.String(length=255), nullable=False),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"decision IN ({_quoted(CONFIRMATION_DECISIONS)})",
            name="ck_lab_bottle_action_confirmation_decision",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["lab_bottle_action_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposal_id",
            name="uq_lab_bottle_action_confirmation_proposal",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_bottle_action_confirmation_content_sha256",
        ),
    )

    _drop_append_only_triggers("lab_bottle_measurements")
    with op.batch_alter_table(
        "lab_bottle_measurements",
        recreate="always",
    ) as batch_op:
        batch_op.alter_column(
            "bottle_event_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("proposal_id", sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column("method", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "measured_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("actor", sa.String(length=255), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_lab_bottle_measurement_proposal",
            "lab_bottle_action_proposals",
            ["proposal_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_lab_bottle_measurement_proposal_kind",
            ["proposal_id", "quantity_kind"],
        )
        batch_op.create_check_constraint(
            "ck_lab_bottle_measurement_authority",
            "(bottle_event_id IS NOT NULL AND proposal_id IS NULL) OR "
            "(bottle_event_id IS NULL AND proposal_id IS NOT NULL "
            "AND method IS NOT NULL AND measured_at IS NOT NULL "
            "AND actor IS NOT NULL)",
        )
    _create_append_only_triggers("lab_bottle_measurements")

    op.create_table(
        "lab_bottle_action_commits",
        *_record_columns(),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("bottle_event_id", sa.String(length=36), nullable=False),
        sa.Column(
            "fulfilled_reservation_event_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "before_state_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "after_state_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "state_diff_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["lab_bottle_action_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["bottle_event_id"],
            ["lab_bottle_events.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fulfilled_reservation_event_id"],
            ["lab_inventory_reservation_events.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "proposal_id",
            name="uq_lab_bottle_action_commit_proposal",
        ),
        sa.UniqueConstraint(
            "bottle_event_id",
            name="uq_lab_bottle_action_commit_event",
        ),
        sa.UniqueConstraint(
            "fulfilled_reservation_event_id",
            name="uq_lab_bottle_action_commit_reservation_event",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_bottle_action_commit_content_sha256",
        ),
    )

    for table_name in EXECUTION_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(EXECUTION_TABLES):
        _drop_append_only_triggers(table_name)
    _drop_append_only_triggers("lab_bottle_measurements")

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE lab_bottle_measurements
            SET bottle_event_id = (
                SELECT lab_bottle_action_commits.bottle_event_id
                FROM lab_bottle_action_commits
                WHERE lab_bottle_action_commits.proposal_id =
                    lab_bottle_measurements.proposal_id
            )
            WHERE proposal_id IS NOT NULL
            """
        )
    )
    unmapped = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM lab_bottle_measurements
            WHERE bottle_event_id IS NULL
            """
        )
    ).scalar_one()
    if int(unmapped):
        raise RuntimeError(
            "cannot downgrade with uncommitted proposal measurements"
        )

    op.drop_table("lab_bottle_action_commits")

    with op.batch_alter_table(
        "lab_bottle_measurements",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_lab_bottle_measurement_authority",
            type_="check",
        )
        batch_op.drop_constraint(
            "uq_lab_bottle_measurement_proposal_kind",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_lab_bottle_measurement_proposal",
            type_="foreignkey",
        )
        batch_op.drop_column("actor")
        batch_op.drop_column("measured_at")
        batch_op.drop_column("method")
        batch_op.drop_column("proposal_id")
        batch_op.alter_column(
            "bottle_event_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )

    op.drop_table("lab_bottle_action_confirmations")
    op.drop_index(
        "ix_lab_bottle_action_proposals_bottle_id",
        table_name="lab_bottle_action_proposals",
    )
    op.drop_index(
        "ix_lab_bottle_action_proposals_reservation_id",
        table_name="lab_bottle_action_proposals",
    )
    op.drop_table("lab_bottle_action_proposals")
    _create_append_only_triggers("lab_bottle_measurements")
