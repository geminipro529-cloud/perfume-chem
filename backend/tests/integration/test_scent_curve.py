import pytest

URL = "/api/v1/lab/v2/workbench/scent-curve"
ROWS = [
    {"identity_name": "Linalool", "amount_ul": 800, "stock_fraction": 1},
    {"identity_name": "Hedione", "amount_ul": 900, "stock_fraction": 0.5},
    {"identity_name": "Lavender EO", "amount_ul": 500, "stock_fraction": 1},
]


@pytest.mark.asyncio
async def test_scent_curve_shares_sum_to_one_over_audible_materials(client):
    response = await client.post(URL, json={"rows": ROWS})

    assert response.status_code == 200
    windows = response.json()["windows"]
    assert [w["label"] for w in windows] == ["opening", "top", "heart", "late_heart", "drydown"]
    for window in windows:
        assert {m["name"] for m in window["materials"]} == {r["identity_name"] for r in ROWS}
        assert all(m["known"] and m["note"] in {"top", "heart", "base"} for m in window["materials"])
        audible = [m["share"] for m in window["materials"] if m["oav"] >= 1]
        assert audible and sum(audible) == pytest.approx(1.0)
        assert sum(m["share"] for m in window["materials"]) == pytest.approx(1.0)
        assert 1 <= window["effective_voices"] <= len(ROWS)
        assert 1 <= len(window["top"]) <= 3


@pytest.mark.asyncio
async def test_scent_curve_returns_unknown_physics_as_not_known(client):
    rows = [*ROWS, {"identity_name": "Zzz Unknown Material", "amount_ul": 50, "stock_fraction": 1}]
    response = await client.post(URL, json={"rows": rows})

    assert response.status_code == 200
    for window in response.json()["windows"]:
        unknown = next(m for m in window["materials"] if m["name"] == "Zzz Unknown Material")
        assert unknown["known"] is False
        assert unknown["share"] is None
        assert unknown["oav"] is None


@pytest.mark.asyncio
async def test_scent_curve_rejects_too_many_rows_and_non_finite_numbers(client):
    too_many = [{"identity_name": f"M{i}", "amount_ul": 1} for i in range(61)]
    assert (await client.post(URL, json={"rows": too_many})).status_code == 422
    assert (await client.post(URL, json={"rows": []})).status_code == 422
    for bad in ("NaN", "Infinity"):
        body = '{"rows": [{"identity_name": "Linalool", "amount_ul": ' + bad + "}]}"
        response = await client.post(URL, content=body, headers={"Content-Type": "application/json"})
        assert response.status_code == 422
