"""Plan item A4: every HOLD on a formula says what is missing and where to supply it.

Expectations are read from the inventory itself (not hard-coded stock names), so the
tests keep holding as Kenny confirms stocks and the stock list grows.
"""

from __future__ import annotations

import pytest

from engine.formulation_intelligence.hold_reasons import TEXT_ONLY_ACTION, explain_holds
from engine.inventory_completions import (
    completion_clears_execution_hold,
    inventory_completion_requirements,
)
from engine.personal_inventory import materialize_personal_inventory


@pytest.fixture(scope="module")
def projection():
    return materialize_personal_inventory()


def _owned(projection):
    return [s for s in projection.stocks if str(s.status).casefold() == "owned"]


def _row(stock, amount="300"):
    return {
        "material": stock.identity_name or stock.name,
        "stock_id": stock.stock_id,
        "amount_ul": amount,
        "fraction": format(stock.dilution, "g") if stock.dilution else "1",
        "basis": stock.fraction_basis or "",
        "carrier": stock.carrier or "",
    }


def _items_for(result, material):
    return [item for item in result["items"] if item["material"] == material]


def test_a_stock_with_missing_details_names_them_and_opens_its_stock_page_entry(projection):
    stock = next(
        s for s in _owned(projection)
        if s.stock_id in projection.canonical_stock_ids
        and not s.execution_ready
        and [f for f in inventory_completion_requirements(s) if f != "USER_COMPOUNDING_HOLD"]
        and "USER_COMPOUNDING_HOLD" not in inventory_completion_requirements(s)
    )
    result = explain_holds([_row(stock)])

    (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
    assert item["reason"].startswith("Its details are not complete: ")
    assert item["open"] == {"kind": "stock_page", "stock_id": stock.stock_id}
    assert item["action"] == "Open it on the Stock page and fill those in."
    assert result["inventory_modified"] is False and result["formula_modified"] is False


def test_a_hold_a_stock_page_entry_clears_says_no_receipt_is_needed(projection):
    candidates = [
        s for s in _owned(projection)
        if s.stock_id in projection.canonical_stock_ids
        and not s.execution_ready
        and not inventory_completion_requirements(s)
        and completion_clears_execution_hold(s)
        and "RECEIPT" in str(s.execution_hold_reason)
    ]
    if not candidates:
        pytest.skip("no receipt-held stock in the current inventory")
    stock = candidates[0]
    result = explain_holds([_row(stock)])

    (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
    assert "No lot or receipt is needed (Rule 6)" in item["reason"]
    assert item["open"] == {"kind": "stock_page", "stock_id": stock.stock_id}


def test_a_stock_only_inventory_txt_lists_goes_to_the_stock_data_thread(projection):
    stock = next(
        s for s in _owned(projection)
        if s.stock_id not in projection.canonical_stock_ids and s.dilution
    )
    result = explain_holds([_row(stock)])

    (item,) = [i for i in _items_for(result, stock.identity_name or stock.name) if i["check"] == "stock"]
    assert item["action"] == TEXT_ONLY_ACTION
    assert item["open"] is None


def test_a_material_not_owned_says_buy_or_swap_and_ifra_says_why_it_cannot_check():
    result = explain_holds([{"material": "Zzyzx Moonflower Absolute", "amount_ul": "200", "fraction": "1"}])

    stock = [i for i in result["items"] if i["check"] == "stock"]
    ifra = [i for i in result["items"] if i["check"] == "ifra"]
    assert [i["reason"] for i in stock] == ["It is not in your stock."]
    assert stock[0]["action"] == "Buy it, or swap the row for a similar stock you own."
    assert ifra and ifra[0]["reason"].startswith("IFRA's Category 4 table does not know it by this name")
    assert all(i["reason"] and i["action"] for i in result["items"])


def test_every_item_has_a_reason_an_action_and_a_unique_id(projection):
    rows = [_row(s, "150") for s in _owned(projection)[:25]]
    result = explain_holds(rows)

    ids = [item["id"] for item in result["items"]]
    assert len(ids) == len(set(ids))
    for item in result["items"]:
        assert item["check"] in {"stock", "ifra"}
        assert item["reason"][:1].isupper() and item["reason"].endswith(".")
        assert item["action"]
        assert item["open"] is None or item["open"]["kind"] == "stock_page"


def test_no_rows_and_a_clean_summary():
    assert explain_holds([])["summary"] == "Add rows with amounts to check them."
    assert explain_holds([{"material": "Hedione", "amount_ul": "0"}])["items"] == []
