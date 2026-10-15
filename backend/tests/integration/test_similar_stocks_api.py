"""/v2/workbench/similar-stocks and /v2/workbench/shelf-map: owned stocks by written character."""

import pytest
from engine.formulation_intelligence.similar_stocks import _owned_capabilities

SIMILAR = "/api/v1/lab/v2/workbench/similar-stocks"
SHELF = "/api/v1/lab/v2/workbench/shelf-map"


@pytest.mark.asyncio
async def test_similar_stocks_are_owned_labelled_and_found_by_id_or_name(client):
    profiled = next(capability for capability in _owned_capabilities() if capability.character)
    by_id = await client.post(SIMILAR, json={"stock_id": profiled.stock_id, "limit": 3})
    by_name = await client.post(SIMILAR, json={"material": profiled.identity_name})

    assert by_id.status_code == 200, by_id.text
    body = by_id.json()
    assert body["label"] == "similar, not the same"
    assert body["stock"]["stock_id"] == profiled.stock_id
    assert len(body["similar"]) <= 3
    assert (body["inventory_modified"], body["formula_modified"]) == (False, False)
    assert by_name.status_code == 200 and by_name.json()["stock"]["identity_name"]


@pytest.mark.asyncio
async def test_an_unknown_stock_or_an_empty_ask_is_refused(client):
    unknown = await client.post(SIMILAR, json={"stock_id": "inventory:not-a-stock"})
    empty = await client.post(SIMILAR, json={})
    extra = await client.post(SIMILAR, json={"material": "Hedione", "lot": "x"})
    too_many = await client.post(SIMILAR, json={"material": "Hedione", "limit": 50})

    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "SIMILAR_STOCK_NOT_FOUND"
    assert (empty.status_code, extra.status_code, too_many.status_code) == (422, 422, 422)


@pytest.mark.asyncio
async def test_the_shelf_map_places_owned_materials(client):
    answer = await client.get(SHELF)

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["schema_version"] == "shelf-map-v1"
    assert body["stocks"] and all(0 <= dot["x"] <= 1 for dot in body["stocks"])
    assert {facet["facet"] for facet in body["facets"]} >= {"woody", "powdery", "floral"}
