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
