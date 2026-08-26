from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.base import Base
from app.models.lab import INVENTORY_MOVEMENT_TYPES


def _constraint_names(table_name: str, constraint_type) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
        and constraint.name is not None
    }


def test_a5_inventory_movement_schema_is_complete_and_append_oriented():
    table = Base.metadata.tables["lab_inventory_movements"]
    assert set(table.columns.keys()) >= {
        "id",
        "stock_solution_id",
        "build_plan_line_id",
        "reservation_event_id",
        "bottle_event_id",
        "event_effect_id",
        "movement_type",
        "raw_quantity",
        "active_quantity",
        "unit",
        "basis",
        "balance_before",
        "balance_after",
        "standard_uncertainty",
        "actor",
        "transaction_id",
        "idempotency_key",
        "correction_of_movement_id",
        "reversal_of_movement_id",
        "mass_delta_g",
        "measured_volume_ul",
        "reason",
        "created_at",
    }
    assert set(INVENTORY_MOVEMENT_TYPES) == {
        "RESERVATION",
        "RESERVATION_RELEASE",
        "CONSUMPTION",
        "RETURN",
        "ADJUSTMENT",
        "TRANSFER",
        "CORRECTION",
        "REVERSAL",
    }

    unique_names = _constraint_names(
        "lab_inventory_movements",
        UniqueConstraint,
    )
    check_names = _constraint_names(
        "lab_inventory_movements",
        CheckConstraint,
    )
    assert "uq_lab_inventory_movement_idempotency" in unique_names
    assert "uq_lab_inventory_movement_correction" in unique_names
    assert "uq_lab_inventory_movement_reversal" in unique_names
    assert {
        "ck_lab_inventory_movement_type",
        "ck_lab_inventory_movement_quantities",
        "ck_lab_inventory_movement_balances",
        "ck_lab_inventory_movement_reference",
        "ck_lab_inventory_movement_cause",
    } <= check_names
