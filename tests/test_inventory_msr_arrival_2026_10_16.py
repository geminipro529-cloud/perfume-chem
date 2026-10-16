"""MySkinRecipes order #2199302 arrived (v26 records STK-107 to STK-116).

Kenny, 16 Oct 2026 03:55 UTC: "Tell all chats that myskinrecipes chemicals arrived".
The order's fifteen lines are all neat as supplied. Ten are new stocks; five are more
bottles of stocks he already had, so they add nothing to the stock list.
"""

from __future__ import annotations

import pytest

import engine.inventory_parser as inventory

NEW = [
    "Isoraldeine 95",
    "Isoraldeine 70",
    "Rum Ether",
    "Geranium Bourbon Essential Oil",
    "Para-Acetanisole",
    "Sweet Orange Essential Oil",
    "Cedarwood Texas EO",
    "Delta Damascone",
    "Rhodinol",
    "Methyl Ionone",
]
ALREADY_OWNED = ["Hedione", "Black Pepper EO", "Clary Sage EO", "Cardamom EO", "Dimethyl Benzyl Carbinyl Acetate"]


def _owned():
    return [s for s in inventory.materialize_current_inventory().stocks if s.status.casefold() == "owned"]


def _records():
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    return {r["canonical_name"]: r for r in overlay["records"] if r["record_id"] >= "INV-USER-20261014-STK-107"}


@pytest.mark.parametrize("name", NEW)
def test_each_new_myskinrecipes_material_is_one_neat_ready_stock(name):
    matches = [s for s in _owned() if s.name == name]
    assert len(matches) == 1, matches
    stock = matches[0]
    assert stock.dilution == 1.0
    assert stock.fraction_basis == "neat"
    assert stock.execution_ready is True


def test_records_name_the_order_and_quote_kenny():
    records = _records()
    assert sorted(records) == sorted(NEW)
    for name, record in records.items():
        assert record["supplier_product"]["supplier"] == "MySkinRecipes"
        assert record["supplier_product"]["order"] == "2199302"
        assert record["authority_limits"]["purity_assay_asserted"] is False
        quote = record["source_quote"]
        if name == "Sweet Orange Essential Oil":
            assert quote == "Sweet orange peel oil China sour"
        else:
            assert quote == "Tell all chats that myskinrecipes chemicals arrived"


def test_the_two_isoraldeine_grades_stay_two_stocks_apart_from_aimi():
    names = [s.name for s in _owned()]
    assert names.count("Isoraldeine 95") == 1
    assert names.count("Isoraldeine 70") == 1
    assert names.count("Alpha Isomethyl Ionone") == 1


def test_alpha_methyl_ionone_74_80_is_not_recorded_as_aimi():
    record = _records()["Methyl Ionone"]
    assert record["supplier_product"]["product_name"] == "Alpha-methyl Ionone (74-80%)"
    assert record["aliases"] == []
    aimi = [s for s in _owned() if s.identity_name == "Alpha Isomethyl Ionone"]
    assert [s.name for s in aimi] == ["Alpha Isomethyl Ionone"]


@pytest.mark.parametrize("name", ALREADY_OWNED)
def test_restocked_materials_stay_one_stock(name):
    assert [s.name for s in _owned()].count(name) == 1
