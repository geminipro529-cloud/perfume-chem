"""/v2/workbench/stock-on-hand and /v2/workbench/make-now: how much is left, and the saved formulas."""

import pytest
from engine.personal_inventory import materialize_personal_inventory

ON_HAND = "/api/v1/lab/v2/workbench/stock-on-hand"
MAKE_NOW = "/api/v1/lab/v2/workbench/make-now"
VERSIONS = "/api/v1/lab/v2/workbench/formula-versions"


def _owned_stock_id():
    return next(stock.stock_id for stock in materialize_personal_inventory().stocks if str(stock.status).casefold() == "owned")


@pytest.mark.asyncio
async def test_how_much_is_left_is_saved_per_stock_and_the_last_entry_wins(client):
    stock_id = _owned_stock_id()
    first = await client.post(ON_HAND, json={"stock_id": stock_id, "amount_decimal": "12.50", "unit": "mL", "supplier": "Bontoux"})
    second = await client.post(ON_HAND, json={"stock_id": stock_id, "amount_decimal": "8", "unit": "mL", "supplier": "Bontoux"})
    read = await client.get(ON_HAND)

    assert first.status_code == 200, first.text
    assert second.json()["receipt"]["previous_hash"] == first.json()["receipt"]["event_sha256"]
    entry = read.json()["on_hand"][stock_id]
    assert (entry["amount_decimal"], entry["unit"], entry["supplier"]) == ("8", "mL", "Bontoux")
    assert (read.json()["inventory_modified"], read.json()["compounding_authority"]) == (False, False)

    cleared = await client.post(ON_HAND, json={"stock_id": stock_id, "clear": True})
    assert stock_id not in cleared.json()["on_hand"]


@pytest.mark.asyncio
async def test_a_stock_not_owned_or_a_bad_amount_is_refused(client):
    stock_id = _owned_stock_id()
    unknown = await client.post(ON_HAND, json={"stock_id": "inventory:not-a-stock", "amount_decimal": "1", "unit": "mL"})
    negative = await client.post(ON_HAND, json={"stock_id": stock_id, "amount_decimal": "-1", "unit": "mL"})
    words = await client.post(ON_HAND, json={"stock_id": stock_id, "amount_decimal": "lots", "unit": "g"})
    unit = await client.post(ON_HAND, json={"stock_id": stock_id, "amount_decimal": "1", "unit": "kg"})
    extra = await client.post(ON_HAND, json={"stock_id": stock_id, "amount_decimal": "1", "unit": "g", "lot": "x"})

    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "STOCK_ON_HAND_STOCK_NOT_IN_INVENTORY"
    assert (negative.status_code, words.status_code) == (422, 422)
    assert negative.json()["error"]["code"] == "INVALID_STOCK_ON_HAND"
    assert (unit.status_code, extra.status_code) == (422, 422)


@pytest.mark.asyncio
async def test_make_now_serves_each_saved_formulas_latest_version_with_its_rows(client):
    rows = [{"material": "Hedione", "stock_id": None, "fraction": "1", "basis": "neat", "amount": "1200"}]
    saved = await client.post(VERSIONS, json={"name": "Make Now Test", "bottle_ml": "30", "rows": rows, "card_text": "| Hedione | 1200 |"})
    assert saved.status_code == 201, saved.text
    formula_id = saved.json()["formula_id"]
    again = await client.post(VERSIONS, json={
        "name": "Make Now Test", "formula_id": formula_id, "parent_version": 1, "bottle_ml": "50",
        "rows": [{**rows[0], "amount": "2000"}], "card_text": "| Hedione | 2000 |",
    })
    assert again.status_code == 201, again.text

    body = (await client.get(MAKE_NOW)).json()
    (formula,) = [entry for entry in body["formulas"] if entry["formula_id"] == formula_id]
    assert (formula["version"], formula["bottle_ml"]) == (2, "50")
    assert [row["amount"] for row in formula["rows"]] == ["2000"]
    assert (body["formula_modified"], body["inventory_modified"]) == (False, False)
    assert isinstance(body["on_hand"], dict)
