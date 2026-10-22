"""No accord support carries more active volume than its own lead row."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace


# Synthetic rows for the planner's named-note pass: equal allocation weights,
# firm caps given per stock id.  A support's role id is its lead's role id,
# "__accord_" and a number, as the semantic brief adapter builds it.
def _choice(stock_id: str, role_id: str, *, named=False, dilution=1.0):
    role = SimpleNamespace(
        role_id=role_id,
        serves_requested_facet=named,
        generic_slot=False,
        exact_preference_required=False,
    )
    stock = SimpleNamespace(stock_id=stock_id, identity_name=stock_id, name=stock_id, dilution=dilution)
    return SimpleNamespace(role=role, candidate=SimpleNamespace(stock=stock))


def _lead(monkeypatch, choices, allocated, firm=None):
    import engine.research.composition_planner as planner

    firm = firm or {}
    monkeypatch.setattr(planner, "_allocation_weight", lambda _choice: 1.0)
    monkeypatch.setattr(
        planner, "_firm_cap_ul", lambda choice, _total: firm.get(choice.candidate.stock.stock_id)
    )
    holds: list[str] = []
    free_rows = [(index, 1.0, None) for index in allocated]
    result = planner._lead_with_named_notes(allocated, free_rows, {}, choices, 6000, holds)
    assert sum(result.values()) == sum(allocated.values())
    return result, holds


def _active(choice, amount: int) -> Decimal:
    return Decimal(amount) * Decimal(str(choice.candidate.stock.dilution))


def _iris_accord():
    return [
        _choice("orris_10pct", "facet_iris", named=True, dilution=0.1),
        _choice("ionone", "facet_iris__accord_1", named=True),
        _choice("violet_leaf", "facet_violet", named=True),
        _choice("cedar", "base_wood"),
    ]


def test_a_support_above_its_lead_comes_down_to_the_lead(monkeypatch) -> None:
    choices = _iris_accord()
    # Lead 1200 uL at 10% = 120 uL active; the neat support carries 1500.
    result, holds = _lead(monkeypatch, choices, {0: 1200, 1: 1500, 2: 1500, 3: 1800})

    assert _active(choices[1], result[1]) <= _active(choices[0], result[0])
    # The support keeps the lead's active volume; its excess goes to the
    # named rows that are no support, and the unnamed row is left alone.
    assert result == {0: 1890, 1: 120, 2: 2190, 3: 1800}
    assert holds == []


def test_a_support_that_cannot_come_down_keeps_its_volume_under_a_hold(monkeypatch) -> None:
    choices = _iris_accord()
    result, holds = _lead(
        monkeypatch,
        choices,
        {0: 1200, 1: 1500, 2: 1500, 3: 1800},
        firm={"orris_10pct": 1200, "violet_leaf": 1500},
    )

    assert result == {0: 1200, 1: 1500, 2: 1500, 3: 1800}
    assert holds == ["ACCORD_HELPER_ABOVE_LEAD:ionone"]


def test_a_move_that_would_break_the_named_floor_holds_instead(monkeypatch) -> None:
    choices = [
        _choice("leather_base_5pct", "facet_leather", named=True, dilution=0.05),
        _choice("agarwood", "facet_leather__accord_1", named=True),
        _choice("cedar", "base_wood"),
    ]
    # Named share is 40.6%; moving 1950 uL of neat support into a 5% lead
    # (the weakest lead still checked) would leave the named rows about 6%
    # of the active volume.
    result, holds = _lead(monkeypatch, choices, {0: 1000, 1: 2000, 2: 3000})

    assert result == {0: 1000, 1: 2000, 2: 3000}
    assert holds == ["ACCORD_HELPER_ABOVE_LEAD:agarwood"]


def test_a_support_of_a_trace_grade_lead_is_not_checked(monkeypatch) -> None:
    # A 1% lead is a potent material diluted for handling: its active volume
    # and a weak helper's are not comparable, so the support is not moved
    # down to the lead's 12 uL active and no hold is raised.
    choices = [
        _choice("calone_1pct", "facet_marine", named=True, dilution=0.01),
        _choice("helper", "facet_marine__accord_1", named=True),
        _choice("violet_leaf", "facet_violet", named=True),
        _choice("cedar", "base_wood"),
    ]
    allocated = {0: 1200, 1: 1500, 2: 1500, 3: 1800}
    assert _lead(monkeypatch, choices, allocated) == (allocated, [])


def test_a_support_whose_lead_row_is_absent_or_empty_is_left_alone(monkeypatch) -> None:
    choices = _iris_accord()
    allocated = {0: 0, 1: 1500, 2: 1500, 3: 3000}
    assert _lead(monkeypatch, choices, allocated) == (allocated, [])

    absent = {1: 1500, 2: 1500, 3: 3000}
    assert _lead(monkeypatch, choices, absent) == (absent, [])
