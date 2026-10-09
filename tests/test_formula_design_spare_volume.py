"""Spare volume a hard cap frees stays on the named notes, not on bridges."""

from functools import lru_cache

import pytest

from engine.research.formula_design import design_inventory_formula

# Roles the composer adds on its own to link the requested notes.
_BRIDGE_SLOTS = {
    "opening_articulation",
    "heart_continuity",
    "top_to_heart_link",
    "heart_to_base_link",
    "diffusion_texture",
}


@lru_cache(maxsize=None)
def _formula(idea: str, formula_name: str | None) -> dict:
    return design_inventory_formula(idea=idea, formula_name=formula_name)["optimized_formula"]


def _liquid(rows: list[dict]) -> dict[str, int]:
    return {row["slot"]: int(row["amount_decimal"]) for row in rows if row["amount_unit"] == "uL"}


_SPRING_ROSE = ("A rose perfume for spring", "Spring Rose")
_COLOGNE = ("A fresh citrus cologne with a soft musky drydown", None)


def test_capped_rose_lead_hands_its_volume_to_its_own_accord() -> None:
    formula = _formula(*_SPRING_ROSE)
    amounts = _liquid(formula["rows"])
    total = int(formula["separate_totals"]["liquid_total_ul"])

    rose_accord = sum(
        amount
        for slot, amount in amounts.items()
        if slot == "facet_rose" or slot.startswith("facet_rose__accord_")
    )
    bridges = {slot: amount for slot, amount in amounts.items() if slot in _BRIDGE_SLOTS}
    assert bridges, "expected generic bridge rows in the spring rose formula"
    assert rose_accord > max(bridges.values())
    assert all(amount <= total * 0.12 for amount in bridges.values()), bridges


def test_cologne_bridge_never_carries_the_formula() -> None:
    formula = _formula(*_COLOGNE)
    amounts = _liquid(formula["rows"])
    total = int(formula["separate_totals"]["liquid_total_ul"])

    bridges = {slot: amount for slot, amount in amounts.items() if slot in _BRIDGE_SLOTS}
    assert bridges, "expected generic bridge rows in the cologne formula"
    assert all(amount <= total * 0.12 for amount in bridges.values()), bridges


@pytest.mark.parametrize("brief", [_SPRING_ROSE, _COLOGNE], ids=["spring_rose", "cologne"])
def test_liquid_total_is_conserved(brief: tuple[str, str | None]) -> None:
    formula = _formula(*brief)

    assert int(formula["separate_totals"]["liquid_total_ul"]) == 6000
    assert sum(_liquid(formula["rows"]).values()) == 6000
