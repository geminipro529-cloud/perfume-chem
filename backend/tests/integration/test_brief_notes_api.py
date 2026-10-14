"""/v2/workbench/brief-notes and /v2/workbench/formula-roles: what the composer reads in a brief."""

import pytest

BRIEF = "/api/v1/lab/v2/workbench/brief-notes"
ROLES = "/api/v1/lab/v2/workbench/formula-roles"


@pytest.mark.asyncio
async def test_the_brief_notes_are_the_materials_and_notes_the_composer_designs_for(client):
    response = await client.post(BRIEF, json={
        "formula_name": "Baie Rose Homme",
        "message": "A pink pepper and cedar fougere with vetiver",
        "must_avoid": ["lavender", ""],
    })

    assert response.status_code == 200, response.text
    body = response.json()
    chips = {chip["label"]: chip for chip in body["notes"]}
    assert chips["Pink Pepper EO"]["kind"] == "material"
    assert chips["fougere coumarin"]["remove_word"] == "fougere"
    assert body["avoided"] == ["lavender"]
    assert (body["inventory_modified"], body["formula_modified"]) == (False, False)
    assert "not how strong" in body["basis"]


@pytest.mark.asyncio
async def test_a_refinement_turn_is_read_with_its_earlier_turns(client):
    response = await client.post(BRIEF, json={
        "message": "Make it drier", "conversation_context": ["A raspberry rose with a little oud"],
    })

    assert {"rose", "raspberry", "oud agarwood"} <= {chip["label"] for chip in response.json()["notes"]}


@pytest.mark.asyncio
async def test_an_empty_brief_and_bad_requests_are_refused(client):
    empty = await client.post(BRIEF, json={"formula_name": " ", "message": ""})
    extra = await client.post(BRIEF, json={"message": "rose", "mode": "x"})
    too_many = await client.post(ROLES, json={"formula_name": "Rose", "rows": [{"material": "Hedione"}] * 121})
    no_name = await client.post(ROLES, json={"formula_name": "", "rows": []})

    assert empty.status_code == 400
    assert empty.json()["error"] == {"code": "INVALID_BRIEF", "message": "Type a name or an idea first."}
    assert (extra.status_code, too_many.status_code, no_name.status_code) == (422, 422, 422)


@pytest.mark.asyncio
async def test_each_row_says_which_of_the_names_notes_its_stock_carries(client):
    response = await client.post(ROLES, json={
        "formula_name": "Baie Rose Homme",
        "rows": [{"material": "Pink Pepper EO", "stock_id": None}, {"material": "Hedione"}, {"material": "Nothing Owned"}],
    })

    assert response.status_code == 200, response.text
    pepper, hedione, unknown = response.json()["rows"]
    assert [(item["label"], item["by"]) for item in pepper["carries"]] == [("spice", "name")]
    assert hedione["carries"] == [] and hedione["profile"]
    assert unknown["found"] is False
