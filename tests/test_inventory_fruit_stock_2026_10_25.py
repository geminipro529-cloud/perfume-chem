"""Stock record, 25 Oct 2026: the 15 PerfumersWorld fruit bottles leave their intake hold
(Kenny's "All neat"), five PerfumersWorld stocks he confirmed owned are added neat, and
Vetiveryl Acetate is used up ("i am out of vetiveryl acetate")."""

from __future__ import annotations

import pytest

from engine import inventory_parser as inventory
from engine.inventory_parser import parse_current_inventory

NEAT_NOW = [
    "Ethyl 2-Methylbutyrate (neat)",
    "Butyl Butyrate",
    "Cis-3 Hexenyl Acetate",
    "Cis-3 Hexenyl Hexanoate",
    "Berry Hexanoate (BerryFlor)",
    "Manzanate",
    "Fructone B",
    "Diethyl Malonate",
    "Allyl Amyl Glycolate",
    "Gamma Octalactone",
    "Gamma Decalactone",
    "Aldehyde C-18",
    "Veloutone",
    "Maple Lactone",
    "Rhubofix",
]
ADDED = {
    "Ethyl Butyrate": "3FD00174",
    "Ethyl Acetoacetate": "3FG00172",
    "Palm Dates Base": "6FQ21068",
    "Anisyl Acetate": "3LN00043",
    "Phenyl Ethyl Dimethyl Carbinyl Acetate": "3LR00160",
}


@pytest.fixture(scope="module")
def stocks():
    return {item.name: item for item in parse_current_inventory()}


@pytest.fixture(scope="module")
def overlay():
    return inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)


@pytest.mark.parametrize("name", NEAT_NOW)
def test_fruit_bottles_are_neat_and_ready(stocks, name):
    stock = stocks[name]
    assert stock.status == "owned"
    assert stock.dilution == 1.0
    assert stock.fraction_basis == "neat"
    assert stock.execution_ready is True
    assert "STOCK_INTAKE_IDENTITY_ONLY" not in stock.execution_hold_reason


def test_fruit_bottle_records_quote_his_card_answer(overlay):
    cleared = [r for r in overlay["delta_records"] if r.get("source_quote") == "All neat"]
    assert len(cleared) == 15
    for record in cleared:
        assert record["receipt_line"] and record["supplier_product"]["supplier"] == "PerfumersWorld"
        assert record["stock"]["execution_basis"].endswith("_INTAKE_HOLD_CLEARED_BY_USER_ALL_NEAT_CARD_20261025")


@pytest.mark.parametrize(("name", "sku"), sorted(ADDED.items()))
def test_confirmed_pw_stocks_are_owned_neat(stocks, overlay, name, sku):
    stock = stocks[name]
    assert stock.status == "owned" and stock.dilution == 1.0 and stock.execution_ready
    (record,) = [r for r in overlay["delta_records"] if r["canonical_name"] == name]
    assert record["supplier_product"]["sku"] == sku
    assert record["source_quote"] == "THEE ARE IN MY INVENTORY"
    assert record["authority_limits"]["fraction_from_user_message"] is False


def test_pedmc_acetate_is_separate_from_the_carbinol(stocks):
    assert stocks["Phenyl Ethyl Dimethyl Carbinol"].status == "owned"
    assert stocks["Phenyl Ethyl Dimethyl Carbinyl Acetate"].stock_id != stocks["Phenyl Ethyl Dimethyl Carbinol"].stock_id


def test_vetiveryl_acetate_is_used_up(stocks, overlay):
    assert not [n for n, s in stocks.items() if "vetiveryl" in n.casefold() and s.status == "owned"]
    live = {r["record_id"] for r in overlay["records"]}
    assert "INV-USER-20260924-R5-002" not in live
    (record,) = [r for r in overlay["delta_records"] if r["canonical_name"] == "Vetiveryl Acetate"]
    assert record["state"] == "NOT_OWNED" and record["stock"] is None
    assert record["source_quote"] == "i am out of vetiveryl acetate"


def test_his_dilutions_of_the_fruit_bottles_are_unchanged(stocks):
    assert stocks["Ethyl 2-Methylbutyrate 1%"].dilution == pytest.approx(0.01)
    assert stocks["Ethyl 2-Methylbutyrate 0.01%"].dilution == pytest.approx(0.0001)
    assert stocks["Allyl Amyl Glycolate 10%"].dilution == pytest.approx(0.1)
