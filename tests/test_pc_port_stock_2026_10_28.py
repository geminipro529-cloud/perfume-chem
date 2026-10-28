"""Stock that existed only on Kenny's PC (20-21 Oct 2026), brought into master on his card tap
"After this PR" (28 Oct 2026). Three fragrance items: the MySkinRecipes Iso E Super Anthamber
bottle, the product code and SDS of his Magnolia Flower Extract, and the source butter of his
Orris Butter 50% in EtOH. These pin the data and its sources; they make no sensory claim."""

from __future__ import annotations

import pytest

from engine import inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.inventory_parser import parse_current_inventory
from engine.pipeline.natural_absolute_decomposition import get_composite_metadata

QUOTE = "After this PR"


@pytest.fixture(scope="module")
def records():
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    return {r["record_id"]: r for r in overlay["delta_records"]}


@pytest.fixture(scope="module")
def stocks():
    return parse_current_inventory(unique=False)


def test_iso_e_super_anthamber_replaces_the_v5_row_as_the_one_neat_stock(records, stocks):
    record = records["INV-USER-20261014-STK-188"]
    assert record["source_quote"] == QUOTE
    assert record["supersedes_parent_stocks"] == [{"source_row": 140}]
    product = record["supplier_product"]
    assert (product["sku"], product["order"], product["lot"], product["cas_on_coa"]) == (
        "2845", "2199458", "42V557", "54464-57-2")
    iso = [s for s in stocks if s.name == "Iso E Super"]
    assert len(iso) == 1
    assert iso[0].dilution == 1.0
    assert iso[0].source_ref.endswith("#INV-USER-20261014-STK-188")


def test_iso_e_super_density_stays_the_25c_value_the_owned_lot_agrees_with():
    spine = load_registry().get("Iso E Super")
    assert spine.density_25c_g_ml == pytest.approx(0.9612)
    assert spine.provenance["density_25c_g_ml"].startswith("TGSC")
    assert "COA lot 42V557 prints SG(20 C) 0.9660" in spine.provenance["density_25c_g_ml"]


def test_magnolia_flower_extract_keeps_his_dilution_and_gains_its_product_code(records, stocks):
    record = records["INV-USER-20261014-STK-126"]
    product = record["supplier_product"]
    assert (product["sku"], product["lot"]) == ("7871", "D5924C")
    assert product["inci_on_sds"] == "Magnolia Officinalis Flower Extract, Propylene Glycol"
    (stock,) = [s for s in stocks if s.name == "Magnolia Flower Extract"]
    assert (stock.dilution, stock.carrier) == (0.05, "dpg")
    # A PG scent extract: never linked to the Magnolia Absolute profile.
    assert get_composite_metadata("Magnolia Flower Extract") is None


def test_orris_butter_50pct_names_its_msr_source_butter(records, stocks):
    record = records["INV-USER-20261014-STK-119"]
    product = record["supplier_product"]
    assert (product["sku"], product["order"], product["lot"]) == ("3261", "2199458", "VFD29V")
    assert record["authority_limits"]["supplier_sku_asserted"] is True
    (stock,) = [s for s in stocks if s.name == "Orris Butter 50% in EtOH"]
    assert (stock.dilution, stock.carrier) == (0.5, "ethanol")
