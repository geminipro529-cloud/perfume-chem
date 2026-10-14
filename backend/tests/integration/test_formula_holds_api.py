"""/v2/workbench/formula-holds: per material, what a HOLD is missing and where to supply it."""

import pytest
from engine.inventory_completions import inventory_completion_requirements
from engine.personal_inventory import materialize_personal_inventory

HOLDS = "/api/v1/lab/v2/workbench/formula-holds"


def _stock_with_missing_details():
    projection = materialize_personal_inventory()
    return next(
        stock for stock in projection.stocks
        if str(stock.status).casefold() == "owned"
        and stock.stock_id in projection.canonical_stock_ids
        and not stock.execution_ready
        and inventory_completion_requirements(stock)
        and "USER_COMPOUNDING_HOLD" not in inventory_completion_requirements(stock)
    )


@pytest.mark.asyncio
async def test_each_hold_says_what_is_missing_and_opens_the_stock_page_entry(client):
    stock = _stock_with_missing_details()
    name = stock.identity_name or stock.name
    response = await client.post(HOLDS, json={"rows": [
        {"material": name, "stock_id": stock.stock_id, "amount": "300",
         "fraction": format(stock.dilution, "g") if stock.dilution else "1",
         "basis": stock.fraction_basis or "", "carrier": stock.carrier or ""},
        {"material": "Zzyzx Moonflower Absolute", "amount": "120", "unit": "mg"},
    ]})

    assert response.status_code == 200, response.text
    body = response.json()
    by_material = {(item["material"], item["check"]): item for item in body["items"]}
    ours = by_material[(name, "stock")]
    assert ours["reason"].startswith("Its details are not complete: ")
    assert ours["open"] == {"kind": "stock_page", "stock_id": stock.stock_id}
    unknown = by_material[("Zzyzx Moonflower Absolute", "stock")]
    assert (unknown["reason"], unknown["open"]) == ("It is not in your stock.", None)
    assert body["summary"].endswith("Each says what to do.")
    assert (body["inventory_modified"], body["formula_modified"]) == (False, False)
    assert "not how the formula smells" in body["basis"]


@pytest.mark.asyncio
async def test_no_rows_and_bad_requests(client):
    empty = await client.post(HOLDS, json={"rows": []})
    extra = await client.post(HOLDS, json={"rows": [], "mode": "x"})
    bad_amount = await client.post(HOLDS, json={"rows": [{"material": "Hedione", "amount": "1000/3"}]})
    negative = await client.post(HOLDS, json={"rows": [{"material": "Hedione", "amount": "-5"}]})
    bad_unit = await client.post(HOLDS, json={"rows": [{"material": "Hedione", "amount": "5", "unit": "g"}]})
    too_many = await client.post(HOLDS, json={"rows": [{"material": "Hedione", "amount": "1"}] * 121})

    assert empty.status_code == 200
    assert empty.json()["summary"] == "Add rows with amounts to check them."
    assert [r.status_code for r in (extra, bad_amount, negative, bad_unit, too_many)] == [422] * 5
