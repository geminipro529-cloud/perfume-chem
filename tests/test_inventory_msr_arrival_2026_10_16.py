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
    return {
        r["canonical_name"]: r
        for r in overlay["records"]
        if r.get("supplier_product", {}).get("order") == "2199302"
    }


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


# The COAs MySkinRecipes emailed for the order (Kenny chose "Add them", 16 Oct 2026 07:54 UTC).
COA_LOTS = {
    "Isoraldeine 95": ("I0DN81", "1335-46-2", "2025-09-12"),
    "Isoraldeine 70": ("3F2IT8", "1335-46-2", "2026-05-01"),
    "Rum Ether": ("QI71T6", "8030-89-5", "2026-02-05"),
    "Geranium Bourbon Essential Oil": ("RS8T01", "0-91-6", "2026-06-03"),
    "Para-Acetanisole": ("K0DQ69", "100-06-1", "2025-11-26"),
    "Sweet Orange Essential Oil": ("1RBCN3", None, "2026-02-26"),
    "Cedarwood Texas EO": ("4ZPU51", "91722-61-1", "2026-05-17"),
    "Delta Damascone": ("4VSQ2Q", "57378-68-4", "2026-01-29"),
    "Rhodinol": ("4XG0CM", "6812-78-8", "2026-01-22"),
    "Methyl Ionone": ("39KMUR", "127-42-4", "2025-11-29"),
}


@pytest.mark.parametrize("name", NEW)
def test_each_new_stock_carries_its_coa_lot_cas_and_dates(name):
    product = _records()[name]["supplier_product"]
    lot, cas, tested = COA_LOTS[name]
    assert product["lot"] == lot
    assert product["cas_on_coa"] == cas
    coa = product["coa"]
    assert coa["test_date"] == tested
    assert coa["expiry_date"] == str(int(tested[:4]) + 2) + tested[4:]
    assert coa["flash_point_given"] is False


def test_coa_data_does_not_assert_purity_or_change_the_stock():
    for name, record in _records().items():
        assert record["authority_limits"]["purity_assay_asserted"] is False, name
        assert record["authority_limits"]["lot_from_supplier_coa"] is True, name
        assert record["stock"]["fraction"] == 1.0, name


def test_coa_problems_are_flagged_on_the_record():
    records = _records()
    damascone = records["Delta Damascone"]["supplier_product"]["coa"]
    assert damascone["results_as_printed"]["assay"] == "96.91"
    assert any("below the COA's own 98-100 spec" in flag for flag in damascone["flags"])
    geranium = records["Geranium Bourbon Essential Oil"]["supplier_product"]["coa"]
    assert any("not a valid CAS" in flag for flag in geranium["flags"])
    ionone = records["Methyl Ionone"]
    assert ionone["aliases"] == []
    assert any("no AIMI alias" in flag for flag in ionone["supplier_product"]["coa"]["flags"])


def test_para_acetanisole_is_a_solid_not_a_neat_liquid():
    # Kenny, 16 Oct 2026 08:28:26 UTC (Studio 1): "para-acetaniole i olid" (= is solid).
    record = _records()["Para-Acetanisole"]
    assert record["stock"]["physical_form"] == "solid_as_supplied"
    assert record["stock"]["execution_scope"] == "WEIGHED_SOLID_OR_PREPARED_SOLUTION_ONLY"
    assert record["authority_limits"]["physical_form_from_user_message"] is True
    rows = [s for s in inventory.materialize_current_inventory().stocks if s.name == "Para-Acetanisole"]
    assert len(rows) == 1
    assert rows[0].physical_form == "solid_as_supplied"
    assert rows[0].dilution == 1.0


def test_rose_otto_10pct_is_mass_fraction_in_dpg_as_kenny_confirmed():
    # Kenny, 16 Oct 2026 08:27:54 UTC (Studio 1), asked w/w or v/v: "eight/eight" (= weight/weight).
    rows = [s for s in inventory.materialize_current_inventory().stocks if s.name == "Rose Otto Bulgarian"]
    assert len(rows) == 1
    assert rows[0].dilution == pytest.approx(0.1)
    assert rows[0].fraction_basis == "mass_fraction"
    assert rows[0].carrier == "dpg"


def test_dmbca_is_a_powder_dosed_by_weight():
    # Kenny, 20 Oct 2026 23:14:07 UTC (CHIMIE Femme thread): "my dmbca i poder".
    payload = inventory.load_current_user_inventory_overlay()
    record = next(r for r in payload["delta_records"] if r["canonical_name"] == "Dimethyl Benzyl Carbinyl Acetate")
    assert record["record_id"] == "INV-USER-20261014-STK-138"
    assert record["stock"]["physical_form"] == "solid_as_supplied"
    assert record["stock"]["execution_scope"] == "WEIGHED_SOLID_OR_PREPARED_SOLUTION_ONLY"
    assert record["supplier_product"]["sku"] == "3LF00157"
    assert "INV-USER-20261008-TOBDBCA-002" in payload["superseded_record_ids"]
    stocks = [s for s in inventory.materialize_current_inventory().stocks if s.identity_name == "Dimethyl Benzyl Carbinyl Acetate"]
    assert len(stocks) == 1 and stocks[0].physical_form == "solid_as_supplied"


def test_nagarmortha_oil_is_back_in_stock_neat():
    # Kenny, 21 Oct 2026 00:04:04 UTC ('Check new ingredients in code'): "i have nagarmortha oil no" (= now).
    payload = inventory.load_current_user_inventory_overlay()
    record = next(r for r in payload["delta_records"] if r["canonical_name"] == "Nagarmortha Oil")
    assert record["record_id"] == "INV-USER-20261014-STK-139"
    assert record["source_quote"] == "i have nagarmortha oil no"
    assert record["authority_limits"]["fraction_from_user_message"] is False
    assert record["authority_limits"]["species_asserted"] is False
    stocks = [s for s in inventory.materialize_current_inventory().stocks if s.identity_name == "Nagarmortha Oil"]
    assert len(stocks) == 1
    assert (stocks[0].dilution, stocks[0].fraction_basis, stocks[0].physical_form) == (1.0, "neat", "as_supplied")


def test_cyclogalbanate_10pct_is_a_separate_dpg_dilution():
    # Kenny, 21 Oct 2026 00:42:08 UTC (CHIMIE Femme thread): "It went in as a 10%".
    stocks = {s.name: s for s in inventory.materialize_current_inventory().stocks if s.identity_name.startswith("Cyclogalbanate")}
    assert set(stocks) == {"Cyclogalbanate", "Cyclogalbanate 10% in DPG"}
    diluted = stocks["Cyclogalbanate 10% in DPG"]
    assert (diluted.dilution, diluted.fraction_basis, diluted.carrier) == (0.1, "mass_fraction", "dpg")
    assert stocks["Cyclogalbanate"].dilution == 1.0


def test_p_cresyl_phenyl_acetate_is_a_powder_dosed_by_weight():
    # Kenny, 21 Oct 2026 01:20:42 UTC ('Stock data into the engine'): "P cresyl phenyl acetate is powder".
    payload = inventory.load_current_user_inventory_overlay()
    record = next(r for r in payload["delta_records"] if r["canonical_name"] == "Para-Cresyl Phenyl Acetate")
    assert record["record_id"] == "INV-USER-20261014-STK-129"
    assert record["stock"]["physical_form"] == "solid_as_supplied"
    assert record["stock"]["execution_scope"] == "WEIGHED_SOLID_OR_PREPARED_SOLUTION_ONLY"
    assert record["supplier_product"]["sku"] == "1PF01952"
    stocks = [s for s in inventory.materialize_current_inventory().stocks if s.identity_name == "Para-Cresyl Phenyl Acetate"]
    assert len(stocks) == 1 and stocks[0].physical_form == "solid_as_supplied"
