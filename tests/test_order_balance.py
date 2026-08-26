from __future__ import annotations

from engine.sensory.order_balance import (
    OrderBalanceState,
    PresentationSchedule,
    assess_order_balance,
    generate_williams_schedule,
)


def test_even_and_odd_williams_schedules_pass_design_audit() -> None:
    even = generate_williams_schedule(("A", "B", "C", "D"))
    odd = generate_williams_schedule(("A", "B", "C"))
    assert len(even.sequences) == 4
    assert len(odd.sequences) == 6
    assert assess_order_balance(even).state is OrderBalanceState.PASS_FOR_DESIGN
    assert assess_order_balance(odd).state is OrderBalanceState.PASS_FOR_DESIGN
    assert even.random_assignment_authorized is False


def test_unbalanced_schedule_is_rebuild_without_execution_authority() -> None:
    schedule = PresentationSchedule(
        labels=("A", "B", "C"),
        sequences=(("A", "B", "C"), ("A", "C", "B")),
        method="USER_SUPPLIED",
    )
    result = assess_order_balance(schedule)
    assert result.state is OrderBalanceState.REBUILD
    assert result.failures
    assert result.physical_execution_authorized is False
    assert result.release_authority is False
