"""The stocks Kenny marked ready on 24 Sep 2026 are design-ready (14 Oct 2026).

Labdanum, Olibanum and Opoponax Resinoid have a
confirmed strength, basis and carrier and wait only on bottle lot and
preparation receipts. Kenny chose to let the composer design with them. Mixing
still waits on those receipts: the release gate keeps flagging each one.
"""

from __future__ import annotations

from engine.inventory_completions import effective_design_ready
from engine.personal_inventory import materialize_personal_inventory
from engine.pipeline.preflight import resolve_inventory_stock_contract

RECEIPTS_HOLD = "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING"
USER_READY = {
    "Labdanum Resinoid": 0.1,
    "Olibanum Resinoid": 0.5,
    "Opoponax Resinoid": 0.5,
    # Tonka Bean Absolute left on 2026-10-15: it is PerfumersWorld's own 10% in DPG,
    # so it has no preparation to receipt and is ready to mix.
}


def test_the_user_ready_stocks_are_design_ready():
    stocks = materialize_personal_inventory().stocks
    held = {
        (stock.identity_name, stock.dilution): stock
        for stock in stocks
        if stock.execution_hold_reason == RECEIPTS_HOLD
    }
    assert set(held) == set(USER_READY.items())
    not_ready = sorted(name for (name, _), stock in held.items() if not effective_design_ready(stock))
    assert not not_ready, f"user-ready stocks the composer still avoids: {not_ready}"
    mixable = sorted(name for (name, _), stock in held.items() if stock.execution_ready)
    assert not mixable, f"receipts-held stocks marked mixable: {mixable}"


def test_mixing_them_still_asks_for_the_receipts():
    for material, fraction in USER_READY.items():
        check = resolve_inventory_stock_contract(
            {"ingredients_ul": {material: 100.0}, "dilutions": {material: fraction}}
        )
        reasons = [issue["reason"] for issue in check.data["issues"]]
        assert reasons == ["inventory_stock_non_executable"], (material, reasons)
