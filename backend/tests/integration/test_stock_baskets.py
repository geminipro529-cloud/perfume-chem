"""Basket fields on current inventory and the store for Kenny's basket choices."""

import json
from collections import Counter
from pathlib import Path

import pytest

INVENTORY = "/api/v1/lab/v2/workbench/current-inventory"
BASKET = INVENTORY + "/basket"
REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_LOG = REPO_ROOT / "output" / "user_basket_events.jsonl"


@pytest.fixture
def basket_log(tmp_path, monkeypatch):
    path = tmp_path / "basket_events.jsonl"
    monkeypatch.setenv("PERFUME_BASKET_EVENT_PATH", str(path))
    return path


async def _stocks(client, normalized_identity):
    response = await client.get(INVENTORY)
    assert response.status_code == 200
    return [
        stock
        for stock in response.json()["stocks"]
        if stock["normalized_identity"] == normalized_identity
    ]


@pytest.mark.asyncio
async def test_every_stock_has_basket_fields_and_the_17_baskets_are_listed(
    client, basket_log
):
    payload = (await client.get(INVENTORY)).json()

    assert [entry["number"] for entry in payload["baskets"]] == list(range(1, 18))
    assert payload["baskets"][0] == {"number": 1, "name": "Always used"}
    assert payload["baskets"][16] == {"number": 17, "name": "Green things"}
    statuses = Counter()
    for stock in payload["stocks"]:
        assert stock["basket"] is None or 1 <= stock["basket"] <= 17
        assert stock["basket_status"] in {
            "confirmed",
            "from_past_cards",
            "conflicting",
            "none",
        }
        assert isinstance(stock["basket_suggestions"], list)
        statuses[stock["basket_status"]] += 1
    assert statuses["confirmed"] == 0
    assert statuses["from_past_cards"] > 0
    assert statuses["conflicting"] > 0


@pytest.mark.asyncio
async def test_seeded_agreed_basket_covers_crystals_and_solution(client, basket_log):
    for identity in ("ambrox super", "ambrox super crystals"):
        stocks = await _stocks(client, identity)
        assert stocks, identity
        for stock in stocks:
            assert stock["basket"] == 1
            assert stock["basket_status"] == "from_past_cards"
            assert stock["basket_suggestions"] == []


@pytest.mark.asyncio
async def test_seeded_conflict_shows_its_suggestions(client, basket_log):
    stocks = await _stocks(client, "alpha ionone")
    assert stocks
    for stock in stocks:
        assert stock["basket"] is None
        assert stock["basket_status"] == "conflicting"
        assert stock["basket_suggestions"] == [5, 11]


@pytest.mark.asyncio
async def test_posting_a_basket_confirms_it_for_every_stock_of_the_material(
    client, basket_log
):
    payload = (await client.get(INVENTORY)).json()
    counts = Counter(stock["normalized_identity"] for stock in payload["stocks"])
    identity = next(key for key, count in sorted(counts.items()) if count >= 2)

    response = await client.post(
        BASKET, json={"normalized_identity": identity, "basket": 14}
    )

    assert response.status_code == 200
    assert response.json() == {
        "normalized_identity": identity,
        "basket": 14,
        "basket_status": "confirmed",
    }
    stocks = await _stocks(client, identity)
    assert len(stocks) >= 2
    for stock in stocks:
        assert stock["basket"] == 14
        assert stock["basket_status"] == "confirmed"
        assert stock["basket_suggestions"] == []


@pytest.mark.asyncio
async def test_posting_null_confirms_no_basket_and_last_choice_wins(client, basket_log):
    await client.post(BASKET, json={"normalized_identity": "alpha ionone", "basket": 11})
    response = await client.post(
        BASKET, json={"normalized_identity": "alpha ionone", "basket": None}
    )

    assert response.status_code == 200
    assert response.json()["basket"] is None
    for stock in await _stocks(client, "alpha ionone"):
        assert stock["basket"] is None
        assert stock["basket_status"] == "confirmed"
        assert stock["basket_suggestions"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("basket", [0, 18, -1, "5", True])
async def test_basket_outside_1_to_17_is_rejected(client, basket_log, basket):
    response = await client.post(
        BASKET, json={"normalized_identity": "alpha ionone", "basket": basket}
    )

    assert response.status_code == 422
    assert not basket_log.exists()


@pytest.mark.asyncio
async def test_identity_not_in_current_inventory_is_rejected(client, basket_log):
    response = await client.post(
        BASKET, json={"normalized_identity": "not a stocked material", "basket": 3}
    )

    assert response.status_code == 422
    assert not basket_log.exists()


@pytest.mark.asyncio
async def test_choices_go_to_the_isolated_hash_chained_log_not_output(
    client, basket_log
):
    real_before = REAL_LOG.read_bytes() if REAL_LOG.exists() else None

    await client.post(BASKET, json={"normalized_identity": "alpha ionone", "basket": 5})
    await client.post(BASKET, json={"normalized_identity": "ambrox super", "basket": 1})

    events = [json.loads(line) for line in basket_log.read_text().splitlines()]
    assert [event["schema"] for event in events] == ["basket-event-v1"] * 2
    assert events[0]["previous_hash"] == ""
    assert events[1]["previous_hash"] == events[0]["event_sha256"]
    assert events[1]["identity_name"] == "Ambrox Super"
    assert (REAL_LOG.read_bytes() if REAL_LOG.exists() else None) == real_before
