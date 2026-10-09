"""The notes a brief names lead the composed formula (audit COMP-02, AGENTS.md Rule 3)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.research.formula_design import design_inventory_formula

_NAMED_PROVENANCE = {"PROMPT_DERIVED_FACET", "ACCORD_SUPPORT", "EXPLICIT_REQUEST_MATERIAL"}


def _active_by_slot(report: dict) -> dict[str, Decimal]:
    formula = report["optimized_formula"] or report["initial_formula"]
    return {
        row["slot"]: Decimal(row["amount_decimal"]) * Decimal(row["stock_fraction_decimal"])
        for row in formula["rows"]
        if row["amount_unit"] == "uL"
    }


@pytest.fixture(scope="module")
def iris_leather() -> dict:
    return design_inventory_formula(idea="iris leather")


@pytest.fixture(scope="module")
def lavender_fougere() -> dict:
    return design_inventory_formula(idea="a lavender fougere")


def test_named_facets_hold_the_floor_share_of_active_volume(iris_leather: dict) -> None:
    provenance = {role["role_id"]: role["provenance"] for role in iris_leather["semantic_brief"]["roles"]}
    active = _active_by_slot(iris_leather)
    named = sum(amount for slot, amount in active.items() if provenance[slot] in _NAMED_PROVENANCE)
    holds = iris_leather["constraint_audit"]["holds"]
    assert named / sum(active.values()) >= Decimal("0.40") or any(
        hold.startswith("NAMED_NOTE_FLOOR_SHORT:") for hold in holds
    )
    # Reached here, so no shortfall is reported.
    assert not any(hold.startswith("NAMED_NOTE_FLOOR_SHORT:") for hold in holds)


def test_no_generic_slot_outranks_the_named_lead(lavender_fougere: dict) -> None:
    # The curated fougere capsule: the open architectural wood is a generic
    # volume slot, the requested lavender is the named note.
    active = _active_by_slot(lavender_fougere)
    assert active["architectural_wood"] <= active["explicit_anchor_1"]
    holds = lavender_fougere["constraint_audit"]["holds"]
    assert not any(hold.startswith("GENERIC_SLOT_ABOVE_NAMED_LEAD:") for hold in holds)


def test_liquid_total_is_conserved_after_the_named_notes_lead(
    iris_leather: dict, lavender_fougere: dict
) -> None:
    for report in (iris_leather, lavender_fougere):
        formula = report["optimized_formula"] or report["initial_formula"]
        liquid = sum(int(row["amount_decimal"]) for row in formula["rows"] if row["amount_unit"] == "uL")
        assert liquid == 6000


def test_a_capsule_slot_that_requires_its_material_is_not_generic() -> None:
    # The fig capsule's creamy sandalwood body is a required volume slot; the
    # named lead may trim an open volume slot but never a required one.
    from engine.research.composition_planner import _r

    assert _r("open_volume", "Open volume", "heart", "volume", .2, "hedione").generic_slot
    assert not _r(
        "creamy_sandalwood", "Creamy sandalwood body", "base", "volume", .25, "ebanol", required=True
    ).generic_slot


# Synthetic rows for the pass itself: equal allocation weights, neat stocks
# unless stated, and firm caps given per stock id.
def _choice(stock_id: str, *, named=False, generic=False, required=False, dilution=1.0):
    from types import SimpleNamespace

    role = SimpleNamespace(
        serves_requested_facet=named, generic_slot=generic, exact_preference_required=required
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


def test_a_generic_slot_above_the_named_lead_gives_its_excess_to_the_named_rows(monkeypatch) -> None:
    choices = [
        _choice("lavender", named=True), _choice("rosemary", named=True),
        _choice("cedar", generic=True), _choice("vetiver"),
    ]
    result, holds = _lead(monkeypatch, choices, {0: 1300, 1: 1300, 2: 1700, 3: 1700})

    # Named share is already 43%, so only the lead rule acts: the open wood slot
    # drops to the lead and the character row above it is left alone.
    assert result == {0: 1500, 1: 1500, 2: 1300, 3: 1700}
    assert holds == []


def test_the_floor_cuts_open_rows_evenly_and_leaves_required_rows(monkeypatch) -> None:
    choices = [
        _choice("lavender", named=True), _choice("cedar", generic=True),
        _choice("vetiver"), _choice("coumarin", required=True),
    ]
    result, holds = _lead(monkeypatch, choices, {0: 600, 1: 2400, 2: 2400, 3: 600})

    assert Decimal("0.40") <= Decimal(result[0]) / 6000 < Decimal("0.41")
    assert result[1] == result[2] and result[3] == 600
    assert holds == []


def test_a_firm_cap_that_stops_the_floor_is_named_in_a_hold(monkeypatch) -> None:
    choices = [_choice("lavender", named=True), _choice("cedar"), _choice("vetiver")]
    result, holds = _lead(
        monkeypatch, choices, {0: 600, 1: 2700, 2: 2700}, firm={"lavender": 1000}
    )

    assert 900 < result[0] <= 1000
    assert [hold.split(":")[0] for hold in holds] == ["NAMED_NOTE_FLOOR_SHORT"]


def test_a_generic_slot_the_named_rows_cannot_outgrow_keeps_its_volume_under_a_hold(
    monkeypatch,
) -> None:
    choices = [_choice("lavender", named=True), _choice("cedar", generic=True)]
    result, holds = _lead(monkeypatch, choices, {0: 2600, 1: 3400}, firm={"lavender": 2600})

    assert result == {0: 2600, 1: 3400}
    assert holds == ["GENERIC_SLOT_ABOVE_NAMED_LEAD:cedar"]
