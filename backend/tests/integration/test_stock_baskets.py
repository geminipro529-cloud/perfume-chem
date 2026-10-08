"""Basket fields on current inventory and the store for Kenny's basket choices."""

import json
from collections import Counter

import pytest

from engine import inventory_baskets, inventory_completions

INVENTORY = "/api/v1/lab/v2/workbench/current-inventory"
BASKET = INVENTORY + "/basket"
REAL_LOG = inventory_baskets.default_basket_event_path()


def test_basket_log_follows_the_other_stock_records(tmp_path, monkeypatch):
    moved = tmp_path / "backed-up" / "user_inventory_completion_events.jsonl"
    monkeypatch.delenv(inventory_baskets.BASKET_EVENT_PATH_ENV, raising=False)
    monkeypatch.setattr(inventory_completions, "DEFAULT_COMPLETION_PATH", moved)
    assert inventory_baskets.basket_event_log_path() == (
        tmp_path / "backed-up" / "user_basket_events.jsonl"
    ).resolve()


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


DAMAGED_MESSAGE = (
    "The basket log has a damaged line (line 2); your basket choices can't be "
    "read until it is repaired."
)


async def _damaged_log(client, basket_log):
    await client.post(BASKET, json={"normalized_identity": "alpha ionone", "basket": 5})
    with basket_log.open("a", encoding="utf-8") as handle:
        handle.write("{torn write\n")
    return basket_log.read_bytes()


@pytest.mark.asyncio
async def test_damaged_basket_log_falls_back_to_seed_values(client, basket_log):
    await _damaged_log(client, basket_log)

    response = await client.get(INVENTORY)

    assert response.status_code == 200
    payload = response.json()
    assert payload["basket_log_error"] == DAMAGED_MESSAGE
    statuses = {stock["basket_status"] for stock in payload["stocks"]}
    assert "confirmed" not in statuses
    for stock in await _stocks(client, "alpha ionone"):
        assert stock["basket_status"] == "conflicting"
        assert stock["basket"] is None


@pytest.mark.asyncio
async def test_healthy_basket_log_has_no_error_field(client, basket_log):
    assert "basket_log_error" not in (await client.get(INVENTORY)).json()


@pytest.mark.asyncio
async def test_damaged_log_does_not_fail_completion_or_addition(
    client, basket_log, tmp_path, monkeypatch
):
    # Own completion/addition logs so these writes don't leak into other tests.
    monkeypatch.setenv(
        "PERFUME_INVENTORY_COMPLETION_PATH", str(tmp_path / "completions.jsonl")
    )
    monkeypatch.setenv(
        "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH", str(tmp_path / "additions.jsonl")
    )
    await _damaged_log(client, basket_log)
    inventory = (await client.get(INVENTORY)).json()
    stock = next(
        item
        for item in inventory["stocks"]
        if item["identity_name"] == "Cedrat FCF Sicilian"
    )

    completed = await client.post(
        INVENTORY + "/complete",
        json={
            "schema_version": "personal-inventory-completion-request-v1",
            "stock_id": stock["stock_id"],
            "expected_effective_inventory_sha256": inventory[
                "canonical_effective_inventory_sha256"
            ],
            "idempotency_key": "basket-damaged-complete",
            "fraction_percent_decimal": "100",
            "fraction_basis": "neat",
            "carrier": "",
            "physical_form": "as_supplied",
            "possession_confirmed": True,
            "homogeneity": "NOT_APPLICABLE",
            "final_fraction_known": True,
            "source_kind": "PERSONAL_CONFIRMATION",
            "user_note": "Current bottle confirmed for personal design.",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["inventory"]["basket_log_error"] == DAMAGED_MESSAGE

    inventory = (await client.get(INVENTORY)).json()
    added = await client.post(
        INVENTORY + "/add",
        json={
            "schema_version": "personal-inventory-addition-request-v1",
            "expected_design_inventory_sha256": inventory[
                "effective_inventory_sha256"
            ],
            "idempotency_key": "basket-damaged-add",
            "identity_name": "Hindinol",
            "category": "woods / amber / structure",
            "fraction_percent_decimal": "100",
            "fraction_basis": "neat",
            "carrier": "",
            "physical_form": "as_supplied",
            "possession_confirmed": True,
            "homogeneity": "NOT_APPLICABLE",
            "source_kind": "PERSONAL_CONFIRMATION",
            "supplier_name": "PerfumersWorld",
            "supplier_sku": "4WX24656",
            "user_note": "Direct user confirmation.",
        },
    )
    assert added.status_code == 200
    assert added.json()["inventory"]["basket_log_error"] == DAMAGED_MESSAGE


@pytest.mark.asyncio
async def test_posting_to_a_damaged_log_is_refused_and_writes_nothing(
    client, basket_log
):
    before = await _damaged_log(client, basket_log)

    response = await client.post(
        BASKET, json={"normalized_identity": "ambrox super", "basket": 1}
    )

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "BASKET_LOG_CORRUPT",
        "message": DAMAGED_MESSAGE,
    }
    assert basket_log.read_bytes() == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("confirm_via", "other"),
    [
        ("ambrox super", "ambrox super crystals"),
        ("ambrox super crystals", "ambrox super"),
    ],
)
async def test_solution_and_crystals_share_a_confirmed_basket(
    client, basket_log, confirm_via, other
):
    response = await client.post(
        BASKET, json={"normalized_identity": confirm_via, "basket": 4}
    )

    assert response.status_code == 200
    event = json.loads(basket_log.read_text().splitlines()[0])
    assert event["normalized_identity"] == "ambrox super"
    assert event["posted_identity"] == confirm_via
    for identity in (confirm_via, other):
        stocks = await _stocks(client, identity)
        assert stocks, identity
        for stock in stocks:
            assert stock["basket"] == 4
            assert stock["basket_status"] == "confirmed"
            assert stock["basket_key"] == "ambrox super"


@pytest.mark.asyncio
async def test_old_event_stored_under_a_crystals_key_still_counts(client, basket_log):
    from engine.inventory_baskets import EVENT_SCHEMA, _canonical_json, _event_hash

    core = {
        "schema": EVENT_SCHEMA,
        "normalized_identity": "ambrox super crystals",
        "identity_name": "Ambrox Super Crystals",
        "basket": 9,
        "recorded_at": "2026-10-08T00:00:00Z",
        "previous_hash": "",
    }
    basket_log.write_text(
        _canonical_json({**core, "event_sha256": _event_hash(core)}) + "\n"
    )

    for identity in ("ambrox super", "ambrox super crystals"):
        for stock in await _stocks(client, identity):
            assert stock["basket"] == 9
            assert stock["basket_status"] == "confirmed"
