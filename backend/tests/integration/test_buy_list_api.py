"""/v2/workbench/buy-list and /v2/workbench/buy-events: the Buy page and Kenny's buying decisions."""

import json
from datetime import date

import pytest

from app.api.v1.endpoints import lab_buy

BUY_LIST = "/api/v1/lab/v2/workbench/buy-list"
BUY_EVENTS = "/api/v1/lab/v2/workbench/buy-events"
VERSIONS = "/api/v1/lab/v2/workbench/formula-versions"

# card_needs: Kenny doesn't own Sandalwood Oil S.album (PW 7WX21054, priced in the YAML);
# he owns Hedione.
UNOWNED, UNOWNED_KEY, OWNED_KEY = "Sandalwood Oil S.album", "sandalwood oil s.album", "hedione"


@pytest.fixture
def buy_log(tmp_path, monkeypatch):
    """A fresh buy log and formula-version log for each test."""
    monkeypatch.setenv("PERFUME_BUY_EVENTS_PATH", str(tmp_path / "buy_events.jsonl"))
    monkeypatch.setenv("PERFUME_FORMULA_VERSION_PATH", str(tmp_path / "formula_versions.jsonl"))
    monkeypatch.setattr(lab_buy, "_today", lambda: date(2026, 10, 15))
    return tmp_path / "buy_events.jsonl"


def _labpicks(**overrides: object) -> str:
    # The block of tests/test_buy_events.py::_block, keys as Kenny would type them.
    block = {
        "source": "Claude review of the Iris Cathedral gaps",
        "reviewed_on": "2026-10-15",
        "decided_by": "Kenny",
        "picks": [
            {
                "material_key": "Iso E Super",
                "tier": 1,
                "offer_key": "pw:4JD02734",
                "dose": "1%",
                "reason": "woody lift",
                "price": {"amount": 450.5, "currency": "THB", "pack": "25 g", "observed_on": "2026-10-13"},
            },
            {"material_key": "Ambrox", "tier": 2, "dose": "10%", "reason": "later"},
        ],
        "skips": [{"material_key": "Galaxolide", "reason": "musk already covered"}],
    }
    block.update(overrides)
    return "\n  \nLABPICKS/1\n" + json.dumps(block, indent=2) + "\n"


async def _save_card(client, name="Buy Test"):
    rows = [
        {"material": UNOWNED, "stock_id": None, "fraction": "1", "basis": "neat", "amount": "300"},
        {"material": "Hedione", "stock_id": None, "fraction": "1", "basis": "neat", "amount": "1200"},
    ]
    saved = await client.post(VERSIONS, json={"name": name, "bottle_ml": "30", "rows": rows, "card_text": "| x |"})
    assert saved.status_code == 201, saved.text
    return saved.json()["formula_id"]


@pytest.mark.asyncio
async def test_buy_list_puts_an_unowned_material_first_and_leaves_owned_ones_out(client, buy_log):
    formula_id = await _save_card(client)

    response = await client.get(BUY_LIST)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_version"] == "workbench-buy-list-v1"
    assert body["generated_on"] == "2026-10-15"
    keys = [row["material_key"] for row in body["buy_first"]]
    assert OWNED_KEY not in keys
    (row,) = [row for row in body["buy_first"] if row["material_key"] == UNOWNED_KEY]
    assert row["need_count"] == 1
    assert [(card["formula_id"], card["name"]) for card in row["cards"]] == [(formula_id, "Buy Test")]
    assert any(offer["offer_key"] == "pw:7WX21054" for offer in row["offers"])
    assert body["price_header"] == "PW list prices from 11 Apr. Check on PW before ordering."
    assert body["fx"] is None and body["rate_banner"] == {"reason": "missing"}
    assert (body["inventory_modified"], body["formula_modified"], body["compounding_authority"]) == (False, False, False)
    assert not buy_log.exists()


@pytest.mark.asyncio
async def test_a_rate_is_recorded_and_shown_and_an_out_of_range_rate_is_refused(client, buy_log):
    await _save_card(client)
    posted = await client.post(BUY_EVENTS, json={"events": [{"kind": "fx_rate", "rate": "33.55", "pair": "USD/THB"}]})
    assert posted.status_code == 200, posted.text
    assert (posted.json()["dry_run"], posted.json()["count"]) == (False, 1)
    assert posted.json()["recorded"][0]["rate"] == "33.55"

    body = (await client.get(BUY_LIST)).json()
    assert body["fx"]["rate"] == "33.55" and body["fx"]["stale"] is False
    assert body["rate_banner"] is None

    before = buy_log.read_bytes()
    refused = await client.post(BUY_EVENTS, json={"events": [{"kind": "fx_rate", "rate": "50", "pair": "USD/THB"}]})
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "BUY_FX_RATE_OUT_OF_RANGE"
    assert buy_log.read_bytes() == before


@pytest.mark.asyncio
async def test_a_labpicks_dry_run_writes_nothing_and_the_real_paste_lists_the_picks(client, buy_log):
    dry = await client.post(BUY_EVENTS, json={"labpicks": _labpicks(), "dry_run": True})

    assert dry.status_code == 200, dry.text
    assert (dry.json()["dry_run"], dry.json()["count"]) == (True, 3)
    entries = dry.json()["entries"]
    assert [(entry["kind"], entry["material_key"]) for entry in entries] == [
        ("pick", "iso e super"), ("pick", "ambrox"), ("skip", "galaxolide"),
    ]
    assert entries[0]["price"]["amount"] == "450.5"
    assert not buy_log.exists()

    real = await client.post(BUY_EVENTS, json={"labpicks": _labpicks()})
    assert real.status_code == 200, real.text
    assert (real.json()["dry_run"], real.json()["count"]) == (False, 3)
    assert len(buy_log.read_text(encoding="utf-8").splitlines()) == 3

    body = (await client.get(BUY_LIST)).json()
    assert [(pick["material_key"], pick["dose"]) for pick in body["tiers"]["1"]] == [("iso e super", "1%")]
    assert [pick["material_key"] for pick in body["tiers"]["2"]] == ["ambrox"]
    assert [skip["material_key"] for skip in body["skip"]] == ["galaxolide"]


@pytest.mark.asyncio
async def test_a_paste_listing_one_material_twice_after_normalizing_is_refused(client, buy_log):
    paste = _labpicks(skips=[{"material_key": "iso e super", "reason": "changed my mind"}])

    refused = await client.post(BUY_EVENTS, json={"labpicks": paste, "dry_run": True})

    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "BUY_LABPICKS_INVALID"
    assert "iso e super" in refused.json()["error"]["message"]
    assert not buy_log.exists()


@pytest.mark.asyncio
async def test_a_posted_material_key_is_stored_under_the_cards_key(client, buy_log):
    skip = {
        "kind": "skip", "material_key": "Nootkatone", "reason": "too grapefruit",
        "decided_by": "Kenny", "decided_at": "2026-10-15", "source": "Buy page",
    }

    posted = await client.post(BUY_EVENTS, json={"events": [skip]})

    assert posted.status_code == 200, posted.text
    assert posted.json()["recorded"][0]["material_key"] == "nootkatone"
    stored = json.loads(buy_log.read_text(encoding="utf-8").splitlines()[0])
    assert stored["material_key"] == "nootkatone"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{}, {"dry_run": True}, {"events": [{"kind": "fx_rate", "rate": "33"}], "labpicks": "LABPICKS/1\n{}"}],
)
async def test_events_and_labpicks_are_one_or_the_other(client, buy_log, payload):
    response = await client.post(BUY_EVENTS, json=payload)

    assert response.status_code == 422
    assert not buy_log.exists()


@pytest.mark.asyncio
async def test_a_damaged_buy_log_is_refused_on_read_and_write(client, buy_log):
    buy_log.write_text("not a buy event\n", encoding="utf-8")

    read = await client.get(BUY_LIST)
    write = await client.post(BUY_EVENTS, json={"events": [{"kind": "fx_rate", "rate": "33.55"}]})

    for response in (read, write):
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "BUY_EVENT_LOG_CORRUPT"
    assert buy_log.read_text(encoding="utf-8") == "not a buy event\n"
