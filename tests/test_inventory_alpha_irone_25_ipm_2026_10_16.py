"""Alpha Irone 25% in IPM (v26 record STK-117).

Kenny, 16 Oct 2026 07:59 UTC: "Add Alpha Irone 5% in IPM to inventory", then "25", "not 5".
"""

from __future__ import annotations

import engine.inventory_parser as inventory


def _irone_stocks():
    return {
        s.name: s
        for s in inventory.materialize_current_inventory().stocks
        if s.status.casefold() == "owned" and s.identity_name == "Alpha Irone"
    }


def test_alpha_irone_25_percent_in_ipm_is_a_ready_stock():
    stock = _irone_stocks()["Alpha Irone 25% in IPM"]
    assert stock.dilution == 0.25
    assert stock.fraction_basis == "mass_fraction"
    assert stock.carrier == "ipm"
    assert stock.execution_ready is True


def test_the_10_percent_dep_stock_stays_owned_beside_it():
    stocks = _irone_stocks()
    assert sorted(stocks) == ["Alpha Irone", "Alpha Irone 25% in IPM"]
    assert stocks["Alpha Irone"].dilution == 0.1
    assert stocks["Alpha Irone"].carrier == "dep"


def test_record_quotes_kenny():
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    (record,) = [r for r in overlay["records"] if r["canonical_name"] == "Alpha Irone 25% in IPM"]
    assert record["source_quote"] == "Add Alpha Irone 5% in IPM to inventory / 25 / not 5"
    assert record["authority_limits"]["supplier_asserted"] is False
