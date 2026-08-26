"""Complete append-only bottle and inventory operation records."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260730_0004"
down_revision = "20260730_0003"
branch_labels = None
depends_on = None

MOVEMENT_TYPES = (
    "RESERVATION",
    "RESERVATION_RELEASE",
    "CONSUMPTION",
    "RETURN",
    "ADJUSTMENT",
    "TRANSFER",
    "CORRECTION",
    "REVERSAL",
)
ACTION_TYPES = ("ADD_STOCK", "ADD_MATERIAL", "ADD_SOLVENT")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _drop_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"DROP TRIGGER IF EXISTS "
            f"trg_{table_name}_{operation.lower()}_append_only"
        )


def _create_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger_name = (
            f"trg_{table_name}_{operation.lower()}_append_only"
        )
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE {operation} ON {table_name}
            BEGIN
                SELECT RAISE(ABORT, 'append-only: {table_name}');
            END
            """
        )


def _movement_type(reason: str, delta: float) -> str:
    normalized = reason.strip().lower()
    if normalized == "bottle_addition" and delta < 0:
        return "CONSUMPTION"
    if normalized == "compensating_event" and delta > 0:
        return "RETURN"
    return "ADJUSTMENT"


def _backfill_movements() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT
                movement.id,
                movement.stock_solution_id,
                movement.mass_delta_g,
                movement.reason,
                movement.created_at,
                stock.initial_mass_g,
                stock.active_fraction,
                effect.event_id,
                bottle_event.transaction_id
            FROM lab_inventory_movements AS movement
            JOIN lab_stock_solutions AS stock
              ON stock.id = movement.stock_solution_id
            LEFT JOIN lab_bottle_event_effects AS effect
              ON effect.id = movement.event_effect_id
            LEFT JOIN lab_bottle_events AS bottle_event
              ON bottle_event.id = effect.event_id
            ORDER BY
                movement.stock_solution_id,
                movement.created_at,
                movement.id
            """
        )
    ).fetchall()
    balances: dict[str, float] = {}
    for row in rows:
        (
            movement_id,
            stock_id,
            mass_delta,
            reason,
            _created_at,
            initial_mass,
            active_fraction,
            bottle_event_id,
            event_transaction_id,
        ) = row
        before = balances.setdefault(str(stock_id), float(initial_mass))
        delta = float(mass_delta)
        after = before + delta
        raw_quantity = abs(delta)
        active_quantity = raw_quantity * float(active_fraction)
        transaction_id = str(
            event_transaction_id or f"legacy:{movement_id}"
        )
        connection.execute(
            sa.text(
                """
                UPDATE lab_inventory_movements
                SET
                    bottle_event_id = :bottle_event_id,
                    movement_type = :movement_type,
                    raw_quantity = :raw_quantity,
                    active_quantity = :active_quantity,
                    unit = 'g',
                    basis = 'mass',
                    balance_before = :balance_before,
                    balance_after = :balance_after,
                    actor = 'legacy-migration',
                    transaction_id = :transaction_id,
                    idempotency_key = :idempotency_key,
                    admin_cause = :admin_cause
                WHERE id = :movement_id
                """
            ),
            {
                "movement_id": movement_id,
                "bottle_event_id": bottle_event_id,
                "movement_type": _movement_type(str(reason), delta),
                "raw_quantity": raw_quantity,
                "active_quantity": active_quantity,
                "balance_before": before,
                "balance_after": after,
                "transaction_id": transaction_id,
                "idempotency_key": f"legacy:{movement_id}",
                "admin_cause": None if bottle_event_id else str(reason),
            },
        )
        balances[str(stock_id)] = after


def upgrade() -> None:
    table_name = "lab_inventory_movements"
    _drop_append_only_triggers(table_name)
    for column in (
        sa.Column("build_plan_line_id", sa.String(length=36)),
        sa.Column("reservation_event_id", sa.String(length=36)),
        sa.Column("bottle_event_id", sa.String(length=36)),
        sa.Column("movement_type", sa.String(length=40)),
        sa.Column("raw_quantity", sa.Float()),
        sa.Column("active_quantity", sa.Float()),
        sa.Column("unit", sa.String(length=40)),
        sa.Column("basis", sa.String(length=80)),
        sa.Column("balance_before", sa.Float()),
        sa.Column("balance_after", sa.Float()),
        sa.Column("standard_uncertainty", sa.Float()),
        sa.Column("actor", sa.String(length=255)),
        sa.Column("transaction_id", sa.String(length=64)),
        sa.Column("idempotency_key", sa.String(length=255)),
        sa.Column("admin_cause", sa.Text()),
        sa.Column("correction_of_movement_id", sa.String(length=36)),
        sa.Column("reversal_of_movement_id", sa.String(length=36)),
    ):
        op.add_column(table_name, column)

    _backfill_movements()

    with op.batch_alter_table(table_name, recreate="always") as batch_op:
        for name, column_type in (
            ("movement_type", sa.String(length=40)),
            ("raw_quantity", sa.Float()),
            ("active_quantity", sa.Float()),
            ("unit", sa.String(length=40)),
            ("basis", sa.String(length=80)),
            ("balance_before", sa.Float()),
            ("balance_after", sa.Float()),
            ("actor", sa.String(length=255)),
            ("transaction_id", sa.String(length=64)),
            ("idempotency_key", sa.String(length=255)),
        ):
            batch_op.alter_column(
                name,
                existing_type=column_type,
                nullable=False,
            )
        batch_op.create_foreign_key(
            "fk_lab_inventory_movement_build_line",
            "lab_build_plan_lines",
            ["build_plan_line_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_lab_inventory_movement_reservation",
            "lab_inventory_reservation_events",
            ["reservation_event_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_lab_inventory_movement_bottle_event",
            "lab_bottle_events",
            ["bottle_event_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_lab_inventory_movement_correction",
            table_name,
            ["correction_of_movement_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_lab_inventory_movement_reversal",
            table_name,
            ["reversal_of_movement_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_lab_inventory_movement_idempotency",
            ["idempotency_key"],
        )
        batch_op.create_unique_constraint(
            "uq_lab_inventory_movement_correction",
            ["correction_of_movement_id"],
        )
        batch_op.create_unique_constraint(
            "uq_lab_inventory_movement_reversal",
            ["reversal_of_movement_id"],
        )
        batch_op.create_check_constraint(
            "ck_lab_inventory_movement_type",
            f"movement_type IN ({_quoted(MOVEMENT_TYPES)})",
        )
        batch_op.create_check_constraint(
            "ck_lab_inventory_movement_quantities",
            "raw_quantity >= 0 AND active_quantity >= 0 "
            "AND active_quantity <= raw_quantity "
            "AND (standard_uncertainty IS NULL "
            "OR standard_uncertainty >= 0)",
        )
        batch_op.create_check_constraint(
            "ck_lab_inventory_movement_balances",
            "balance_before >= 0 AND balance_after >= 0",
        )
        batch_op.create_check_constraint(
            "ck_lab_inventory_movement_reference",
            "NOT (correction_of_movement_id IS NOT NULL "
            "AND reversal_of_movement_id IS NOT NULL) "
            "AND ((movement_type = 'CORRECTION' "
            "AND correction_of_movement_id IS NOT NULL) "
            "OR (movement_type != 'CORRECTION' "
            "AND correction_of_movement_id IS NULL)) "
            "AND ((movement_type = 'REVERSAL' "
            "AND reversal_of_movement_id IS NOT NULL) "
            "OR (movement_type != 'REVERSAL' "
            "AND reversal_of_movement_id IS NULL))",
        )
        batch_op.create_check_constraint(
            "ck_lab_inventory_movement_cause",
            "build_plan_line_id IS NOT NULL "
            "OR reservation_event_id IS NOT NULL "
            "OR bottle_event_id IS NOT NULL "
            "OR event_effect_id IS NOT NULL "
            "OR admin_cause IS NOT NULL",
        )
    op.create_index(
        "ix_lab_inventory_movements_transaction_id",
        table_name,
        ["transaction_id"],
        unique=False,
    )
    _create_append_only_triggers(table_name)

    proposal_table = "lab_bottle_action_proposals"
    _drop_append_only_triggers(proposal_table)
    with op.batch_alter_table(
        proposal_table,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_lab_bottle_action_proposal_type",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_lab_bottle_action_proposal_type",
            f"action_type IN ({_quoted(ACTION_TYPES)})",
        )
    _create_append_only_triggers(proposal_table)


def downgrade() -> None:
    proposal_table = "lab_bottle_action_proposals"
    _drop_append_only_triggers(proposal_table)
    op.execute(
        """
        UPDATE lab_bottle_action_proposals
        SET action_type='ADD_STOCK'
        WHERE action_type IN ('ADD_MATERIAL', 'ADD_SOLVENT')
        """
    )
    with op.batch_alter_table(
        proposal_table,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_lab_bottle_action_proposal_type",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_lab_bottle_action_proposal_type",
            "action_type IN ('ADD_STOCK')",
        )
    _create_append_only_triggers(proposal_table)

    table_name = "lab_inventory_movements"
    _drop_append_only_triggers(table_name)
    op.drop_index(
        "ix_lab_inventory_movements_transaction_id",
        table_name=table_name,
    )
    with op.batch_alter_table(table_name, recreate="always") as batch_op:
        for constraint_name, constraint_type in (
            ("ck_lab_inventory_movement_cause", "check"),
            ("ck_lab_inventory_movement_reference", "check"),
            ("ck_lab_inventory_movement_balances", "check"),
            ("ck_lab_inventory_movement_quantities", "check"),
            ("ck_lab_inventory_movement_type", "check"),
            ("uq_lab_inventory_movement_reversal", "unique"),
            ("uq_lab_inventory_movement_correction", "unique"),
            ("uq_lab_inventory_movement_idempotency", "unique"),
            ("fk_lab_inventory_movement_reversal", "foreignkey"),
            ("fk_lab_inventory_movement_correction", "foreignkey"),
            ("fk_lab_inventory_movement_bottle_event", "foreignkey"),
            ("fk_lab_inventory_movement_reservation", "foreignkey"),
            ("fk_lab_inventory_movement_build_line", "foreignkey"),
        ):
            batch_op.drop_constraint(
                constraint_name,
                type_=constraint_type,
            )
        for column_name in (
            "reversal_of_movement_id",
            "correction_of_movement_id",
            "admin_cause",
            "idempotency_key",
            "transaction_id",
            "actor",
            "standard_uncertainty",
            "balance_after",
            "balance_before",
            "basis",
            "unit",
            "active_quantity",
            "raw_quantity",
            "movement_type",
            "bottle_event_id",
            "reservation_event_id",
            "build_plan_line_id",
        ):
            batch_op.drop_column(column_name)
    _create_append_only_triggers(table_name)
