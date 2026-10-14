"""POST /v2/workbench/formula-checks: IFRA Category 4 and EU allergens for the formula editor."""

import pytest

URL = "/api/v1/lab/v2/workbench/formula-checks"

ROSE = [
    {"material": "Hedione", "amount_ul": "600", "stock_fraction": "1", "fraction_basis": "neat"},
    {"material": "Rose Oxide", "amount_ul": "30", "stock_fraction": "0.1", "fraction_basis": "w/w", "carrier": "dpg"},
    {"material": "Iso E Super", "amount_ul": "370", "stock_fraction": "1", "fraction_basis": "neat"},
    {"material": "Ambrox", "amount_mg": "120", "stock_fraction": "1"},
    {"material": "Velvet Musk", "amount_ul": "60", "stock_fraction": "0.1", "fraction_basis": "w/w"},
]


def _row(answer, material):
    return next(row for row in answer["ifra"]["rows"] if row["material"] == material)


@pytest.mark.asyncio
async def test_each_row_is_read_as_a_share_of_the_finished_bottle(client):
    response = await client.post(URL, json={"rows": ROSE, "bottle_ml": "30"})

    assert response.status_code == 200
    answer = response.json()
    assert answer["schema_version"] == "workbench-formula-checks-v1"
    assert (answer["bottle_ml"], answer["bottle_source"]) == (30.0, "bottle_ml")
    assert answer["concentrate_ml"] == pytest.approx(1.06)
    assert answer["ethanol_ml"] == pytest.approx(28.94)
    assert answer["oil_pct"] == pytest.approx(3.5333, abs=1e-4)
    # 600 µL of Hedione at 0.999 g/mL in ~24.0 g of perfume; 120 mg of Ambrox crystals.
    assert answer["pct_w_w"]["Hedione"] == pytest.approx(2.4976, abs=1e-3)
    assert answer["pct_w_w"]["Ambrox"] == pytest.approx(0.5000, abs=1e-3)
    iso = _row(answer, "Iso E Super")
    assert (iso["ifra_status"], iso["limit_pct"], iso["usage_pct"], iso["verdict"]) == ("restricted", 20.0, 7.4, "pass")
    # A material the IFRA table does not know holds the check, as in the release gate.
    assert answer["ifra"]["verdict"] == "HOLD"
    assert answer["ifra"]["unrecognised"] == ["Velvet Musk"]
    assert (answer["ifra"]["amendment"], answer["ifra"]["category"]) == (51, "4")
    assert answer["assumptions"] == [
        "Velvet Musk: density unknown, 1.0 g/mL used",
        "Velvet Musk: carrier not recorded has no density here, 1.0 g/mL used",
    ]
    assert (answer["release_authority"], answer["inventory_modified"], answer["compounding_authority"]) == (False, False, False)


@pytest.mark.asyncio
async def test_a_row_over_its_limit_fails_with_the_limit_named(client):
    rows = [{"material": "Hedione", "amount_ul": "5000"}, {"material": "Cinnamic Aldehyde", "amount_ul": "100"}]
    response = await client.post(URL, json={"rows": rows, "bottle_ml": "30"})

    answer = response.json()
    cinnamic = _row(answer, "Cinnamic Aldehyde")
    assert cinnamic["verdict"] == "fail"
    assert cinnamic["limit_pct"] == 0.25
    assert cinnamic["actual_pct"] > 0.25
    assert answer["ifra"]["verdict"] == "FAIL"


@pytest.mark.asyncio
async def test_rows_that_list_their_ethanol_are_the_bottle(client):
    rows = [{"material": "Hedione", "amount_ul": "6000"}, {"material": "Ethanol", "amount_ul": "24000"}]
    response = await client.post(URL, json={"rows": rows, "bottle_ml": "50"})

    answer = response.json()
    assert (answer["bottle_ml"], answer["bottle_source"]) == (30.0, "rows")
    assert answer["oil_pct"] == pytest.approx(20.0)
    assert set(answer["pct_w_w"]) == {"Hedione"}
    assert answer["ifra"]["verdict"] == "PASS"


@pytest.mark.asyncio
async def test_allergens_over_the_label_line_are_named_and_one_allergen_under_two_names_is_summed(client):
    rows = [
        {"material": "Hedione", "amount_ul": "6000"},
        {"material": "Linalool", "amount_ul": "10"},
        # Each alone is under 0.001% of the bottle; together they are over it.
        {"material": "D-Limonene", "amount_ul": "0.2"},
        {"material": "Limonene", "amount_ul": "0.2"},
    ]
    response = await client.post(URL, json={"rows": rows, "bottle_ml": "30"})

    allergens = response.json()["allergens"]
    assert allergens["use"] == "leave_on"
    assert [row["allergen"] for row in allergens["declare"]] == ["Linalool", "Limonene"]
    linalool, limonene = allergens["declare"]
    assert linalool["line_pct"] == 0.001
    assert linalool["pct"] == pytest.approx(0.0347, abs=2e-3)
    assert 0.001 < limonene["pct"] < 0.002


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"rows": []},
        {"rows": [{"material": "Hedione"}]},
        {"rows": [{"material": "Hedione", "amount_ul": "10", "amount_mg": "10"}]},
        {"rows": [{"material": "Hedione", "amount_ul": "10", "stock_fraction": "0"}]},
        {"rows": [{"material": "Hedione", "amount_ul": "-1"}]},
        {"rows": [{"material": "Hedione", "amount_ul": "10"}], "bottle_ml": "0"},
        {"rows": [{"material": "Hedione", "amount_ul": "10"}], "extra": 1},
    ],
)
async def test_a_malformed_request_is_refused(client, body):
    response = await client.post(URL, json=body)

    assert response.status_code == 422
