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
    # Violet leaf already sits past 40% of the active oil once the support
    # has given up its excess, so the orris lead takes all of it.
    assert result == {0: 2580, 1: 120, 2: 1500, 3: 1800}
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


def _leather_accord(*, cedar_exact=False):
    choices = [
        _choice("leather_base_5pct", "facet_leather", named=True, dilution=0.05),
        _choice("agarwood", "facet_leather__accord_1", named=True),
        _choice("cedar", "base_wood"),
    ]
    choices[2].role.exact_preference_required = cedar_exact
    return choices


def _named_share(choices, result, fixed=None) -> Decimal:
    amounts = {**(fixed or {}), **result}
    total = sum(_active(choices[index], amount) for index, amount in amounts.items())
    named = sum(_active(choices[index], amount) for index, amount in amounts.items()
                if choices[index].role.serves_requested_facet)
    return named / total


def test_a_move_that_leaves_the_floor_short_takes_from_the_unnamed_rows(monkeypatch) -> None:
    # Named share is 40.6%; moving 1950 uL of neat support into a 5% lead
    # (the weakest lead still checked) would leave the named rows about 6%
    # of the active volume, so the lead also takes from the unnamed cedar,
    # as the floor rule does, until the floor holds again.
    choices = _leather_accord()
    result, holds = _lead(monkeypatch, choices, {0: 1000, 1: 2000, 2: 3000})

    assert _active(choices[1], result[1]) <= _active(choices[0], result[0])
    assert _named_share(choices, result) >= Decimal("0.40")
    assert result[2] < 3000
    assert holds == []


def test_a_move_whose_floor_cannot_be_restored_holds_instead(monkeypatch) -> None:
    # The cedar is a requested stock, so no unnamed row can give volume.
    choices = _leather_accord(cedar_exact=True)
    result, holds = _lead(monkeypatch, choices, {0: 1000, 1: 2000, 2: 3000})

    assert result == {0: 1000, 1: 2000, 2: 3000}
    assert holds == ["ACCORD_HELPER_ABOVE_LEAD:agarwood"]


def test_a_move_may_not_lower_a_floor_already_short(monkeypatch) -> None:
    # A fixed 3000 uL cedar keeps the named share at 16% whatever the floor
    # rule does; moving the support's excess into the 10% lead would lower
    # it further and leave the recorded short share overstated.
    import engine.research.composition_planner as planner

    choices = _iris_accord()
    choices[2] = _choice("violet_leaf_10pct", "facet_violet", named=True, dilution=0.1)
    monkeypatch.setattr(planner, "_allocation_weight", lambda _choice: 1.0)
    monkeypatch.setattr(planner, "_firm_cap_ul", lambda _choice, _total: None)
    allocated = {0: 1000, 1: 300, 2: 1700}
    holds: list[str] = []
    result = planner._lead_with_named_notes(
        allocated, [(index, 1.0, None) for index in allocated], {3: 3000}, choices, 6000, holds,
    )

    assert result == allocated
    assert holds == ["NAMED_NOTE_FLOOR_SHORT:16.0", "ACCORD_HELPER_ABOVE_LEAD:ionone"]


def test_a_support_beside_a_lead_under_one_transfer_of_active_is_not_checked(monkeypatch) -> None:
    # Rose Oxide 10% under its hard cap: 60 uL is 6 uL active, so holding the
    # neat support to it would leave a 6 uL row nobody can pipette.
    choices = [
        _choice("rose_oxide_10pct", "explicit_anchor_1", named=True, dilution=0.1),
        _choice("phenethyl_alcohol", "explicit_anchor_1__accord_1", named=True),
        _choice("violet_leaf", "facet_violet", named=True),
        _choice("cedar", "base_wood"),
    ]
    allocated = {0: 60, 1: 1500, 2: 1500, 3: 2940}
    assert _lead(monkeypatch, choices, allocated) == (allocated, [])
    # At 100 uL (10 uL active) it is checked and brought down to 10 uL.
    result, holds = _lead(monkeypatch, choices, {0: 100, 1: 1500, 2: 1500, 3: 2900})
    assert result[1] == 10 and holds == []


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
