"""Stock record, 28 Oct 2026: the three PerfumersWorld orders of 25 Oct arrived ("PW orders have
arrived"). Six lines are recorded from the order mails with their SKU; PerfumersWorld gives no
bottle lot. Three lines are second bottles of stocks he already owns at the same strength, so
they add no record."""

from __future__ import annotations

import pytest

from engine import inventory_parser as inventory
from engine.inventory_parser import parse_current_inventory

QUOTE = "PW orders have arrived"

# Stock name -> (order, SKU, fraction, carrier).
PW_STOCKS = {
    "Vetiveryl Acetate": ("PW-261024-211206f41", "3WY00468", 1.0, ""),
    "Fixative 505": ("PW-261024-211206f41", "4UY07514", 1.0, ""),
    "Davana Essential Oil": ("PW-261024-211206f41", "5HH12466", 0.1, "dpg"),
    "Beta Caryophyllene": ("PW-261024-21230599a", "3WS00089", 1.0, ""),
    "Isolongifolanone": ("PW-261024-21230599a", "3WY14446", 1.0, ""),
    "Tuberose Absolute 10% in TEC": ("PW-261024-23332424a", "5ND19125", 0.1, "tec"),
}
# Second bottles: the stock each joins, which stays the only one of its name.
RESTOCKS = {
    "Ambrox Super (neat)": "INV-USER-20260924-R5-001",
    "IBQ 10%": "INV-USER-20261014-STK-059",
    "Orange Flower Absolute": "INV-USER-20261014-STK-148",
}


@pytest.fixture(scope="module")
def stocks():
    return parse_current_inventory(unique=False)


@pytest.fixture(scope="module")
def overlay():
    return inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)


def _records(overlay):
    return {r["canonical_name"]: r for r in overlay["delta_records"] if r.get("source_quote") == QUOTE}


def test_six_lines_quote_his_message(overlay):
    records = _records(overlay)
    assert set(records) == set(PW_STOCKS)
    assert sorted(r["record_id"] for r in records.values()) == [
        f"INV-USER-20261014-STK-{n:03d}" for n in range(182, 188)
    ]
    (statement,) = [s for s in overlay["source"]["verbatim_user_statements"] if s["text"] == QUOTE]
    assert "EQ291309744TH" in statement["context"]
    assert all(sku in statement["context"] for sku in ("1UW00035", "5UP07523", "5NC07544"))


@pytest.mark.parametrize(("name", "expected"), sorted(PW_STOCKS.items()))
def test_pw_lines_are_owned_ready_and_carry_the_order_sku(stocks, overlay, name, expected):
    order, sku, fraction, carrier = expected
    (stock,) = [s for s in stocks if s.name == name]
    assert stock.status == "owned" and stock.execution_ready is True
    assert (stock.dilution, stock.carrier) == (fraction, carrier)
    assert stock.fraction_basis == ("neat" if fraction == 1.0 else "mass_fraction")
    record = _records(overlay)[name]
    product = record["supplier_product"]
    assert (product["supplier"], product["order"], product["sku"]) == ("PerfumersWorld", order, sku)
    assert "lot" not in product
    limits = record["authority_limits"]
    assert limits["lot_from_supplier_coa"] is False and limits["user_lot_asserted"] is False


@pytest.mark.parametrize(("name", "record_id"), sorted(RESTOCKS.items()))
def test_second_bottles_add_no_stock(stocks, name, record_id):
    same = [s for s in stocks if s.name == name]
    assert len(same) == 1 and same[0].source_ref.endswith(f"#{record_id}")


def test_vetiveryl_acetate_is_owned_again_after_running_out(stocks, overlay):
    records = [r for r in overlay["delta_records"] if r["canonical_name"] == "Vetiveryl Acetate"]
    assert [r["state"] for r in records] == ["NOT_OWNED", "OWNED"]
    assert [s.name for s in stocks if "vetiveryl" in s.name.casefold()] == ["Vetiveryl Acetate"]


def test_davana_fills_the_v5_requirement_row(overlay):
    (override,) = _records(overlay)["Davana Essential Oil"]["requirement_overrides"]
    assert (override["source_row"], override["disposition"]) == (91, "OWNED")


def test_tuberose_tec_bottle_stays_separate_from_the_older_ten_percent(stocks):
    tuberose = {s.name: (s.dilution, s.carrier) for s in stocks if s.name.startswith("Tuberose Absolute")}
    assert tuberose == {"Tuberose Absolute 10%": (0.1, "dpg"), "Tuberose Absolute 10% in TEC": (0.1, "tec")}


def test_isolongifolanone_cas_is_not_asserted(overlay):
    record = _records(overlay)["Isolongifolanone"]
    assert record["supplier_product"]["cas_on_supplier_certificate"] == "14727-47-0"
    assert record["authority_limits"]["cas_asserted"] is False
