"""Stock record, 27 Oct 2026: the MySkinRecipes orders #2200410 and #2200413 in Kenny's mail
("Stock data from msr emails and find all of the properties."). Twelve fragrance lines are
recorded neat as supplied with the lot from each COA; L-Arginine HCl, a cosmetic, is left out.
Five lines are second bottles and replace the older record as the one stock of that name."""

from __future__ import annotations

import pytest

from engine import inventory_parser as inventory
from engine.inventory_parser import parse_current_inventory

QUOTE = "Stock data from msr emails and find all of the properties."

# Stock name -> (order, lot from the COA).
MSR_STOCKS = {
    "Magnolia Absolute": ("2200410", "ZDHY6L"),
    "Labdanum Absolute": ("2200410", "3J7L0O"),
    "White Sandalwood Oil (China)": ("2200410", "W9F536"),
    "Olibanum Oil": ("2200410", "3S74J8"),
    "Cinnamyl Acetate": ("2200410", "B62L38"),
    "Fir Needle Oil (Canada)": ("2200410", "ECPT07"),
    "Galbanum Resinoid": ("2200410", "QM0D25"),
    "Methyl Anthranilate": ("2200410", "222GWQ"),
    "Hedione HC": ("2200410", "X6K6NQ"),
    "Dihydro Beta Ionone": ("2200413", "N58L3K"),
    "Phenyl Ethyl Dimethyl Carbinol": ("2200413", "70E1FQ"),
    "Farnesol": ("2200413", "CF557U"),
}
SECOND_BOTTLES = [
    "Methyl Anthranilate",
    "Hedione HC",
    "Dihydro Beta Ionone",
    "Phenyl Ethyl Dimethyl Carbinol",
    "Farnesol",
]


@pytest.fixture(scope="module")
def stocks():
    return parse_current_inventory(unique=False)


@pytest.fixture(scope="module")
def overlay():
    return inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)


def _records(overlay):
    return {r["canonical_name"]: r for r in overlay["delta_records"] if r.get("source_quote") == QUOTE}


def test_twelve_lines_quote_his_message(overlay):
    records = _records(overlay)
    assert set(records) == set(MSR_STOCKS)
    assert sorted(r["record_id"] for r in records.values()) == [
        f"INV-USER-20261014-STK-{n:03d}" for n in range(170, 182)
    ]
    assert not [r for r in overlay["delta_records"] if "arginine" in r["canonical_name"].casefold()]


@pytest.mark.parametrize(("name", "order_lot"), sorted(MSR_STOCKS.items()))
def test_msr_lines_are_neat_ready_and_carry_the_coa_lot(stocks, overlay, name, order_lot):
    # A name with a second bottle gets the "(neat)" form: Labdanum Absolute since PW's 10% in DPG
    # was recorded on 28 Oct 2026 (v26 STK-209).
    (stock,) = [s for s in stocks if s.name in (name, f"{name} (neat)")]
    assert stock.status == "owned"
    assert stock.dilution == 1.0 and stock.fraction_basis == "neat"
    assert stock.execution_ready is True
    record = _records(overlay)[name]
    product = record["supplier_product"]
    assert product["supplier"] == "MySkinRecipes"
    assert (product["order"], product["lot"]) == order_lot
    assert record["authority_limits"]["lot_from_supplier_coa"] is True
    assert record["authority_limits"]["delivery_email_seen"] is (product["order"] == "2200413")


@pytest.mark.parametrize("name", SECOND_BOTTLES)
def test_second_bottles_leave_one_stock_of_that_name(stocks, name):
    same = [s for s in stocks if s.name.removesuffix(" (neat)") == name or s.name.startswith(f"{name} (neat)")]
    assert [s.name for s in same] == [name]


def test_older_hedione_hc_and_pedmc_records_are_superseded(overlay):
    live = {r["record_id"] for r in overlay["records"]}
    assert "INV-USER-20260924-R5-016" not in live
    assert "INV-USER-20260908-AHSEE-001" not in live
    records = _records(overlay)
    assert records["Hedione HC"]["authority_limits"]["cis_content_asserted"] is False
    assert "Carbinol Muguet" in records["Phenyl Ethyl Dimethyl Carbinol"]["aliases"]


def test_his_dilutions_stay_separate_requirements(stocks):
    by_name = {s.name: s for s in stocks}
    for name in ("Methyl Anthranilate 10%", "Dihydro Beta Ionone 10%", "Galbanum Resinoid 10%"):
        assert by_name[name].execution_ready is False
