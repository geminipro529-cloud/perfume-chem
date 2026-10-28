"""The stocks Kenny marked ready on 24 Sep 2026 are design-ready (14 Oct 2026).

Labdanum and Olibanum Resinoid (Opoponax until 28 Oct) had a confirmed strength, basis and
carrier and waited only on bottle lot and preparation receipts; Kenny let the composer design
with them while mixing waited. On 28 Oct 2026 his card "Clear on order evidence" cleared those
holds (v26 STK-209 and STK-211), and the "Labdanum Resinoid" bottle turned out to be
PerfumersWorld's Labdanum Absolute 10% in DPG. So no stock is held for receipts any more.
"""

from __future__ import annotations

from engine.inventory_completions import effective_design_ready
from engine.personal_inventory import materialize_personal_inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract

RECEIPTS_HOLD = "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING"
FORMERLY_HELD = {
    "Labdanum Absolute": 0.1,
    "Olibanum Resinoid": 0.5,
}


def test_no_stock_is_held_for_receipts_and_the_former_ones_are_ready():
    stocks = materialize_personal_inventory().stocks
    assert not [s.identity_name for s in stocks if s.execution_hold_reason == RECEIPTS_HOLD]
    ready = {
        (stock.identity_name, stock.dilution)
        for stock in stocks
        if stock.execution_ready and effective_design_ready(stock)
    }
    assert set(FORMERLY_HELD.items()) <= ready


def test_mixing_them_raises_no_stock_issue():
    for material, fraction in FORMERLY_HELD.items():
        check = resolve_inventory_stock_contract(
            {"ingredients_ul": {material: 100.0}, "dilutions": {material: fraction}}
        )
        assert [issue["reason"] for issue in check.data["issues"]] == [], material


def test_no_labdanum_resinoid_is_owned():
    # Kenny, 28 Oct 2026: "I have two right now, one is that one from PW another is from MSR".
    check = resolve_inventory_stock_contract(
        {"ingredients_ul": {"Labdanum Resinoid": 100.0}, "dilutions": {"Labdanum Resinoid": 0.1}}
    )
    assert [issue["reason"] for issue in check.data["issues"]] == ["not_in_inventory"]
