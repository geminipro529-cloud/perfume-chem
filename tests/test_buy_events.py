"""Kenny's buy log: hash chain, strict kinds, the state fold and LABPICKS blocks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engine import buy_events
from engine.buy_events import (
    BuyEventError,
    BuyEventLogCorruptError,
    buy_events_path,
    buy_state,
    buy_state_to_json,
    load_buy_events,
    parse_labpicks,
    record_buy_events,
    state_key,
)

PICK = {
    "kind": "pick",
    "material_key": "Iso E Super",
    "tier": 1,
    "offer_key": "pw:4JD02734",
    "dose": "1%",
    "reason": "woody lift for the cathedral base",
    "decided_by": "Kenny",
    "decided_at": "2026-10-14",
    "source": "Lab review 2026-10-14",
    "price": {"amount": "450.50", "currency": "THB", "pack": "25 g", "observed_on": "2026-10-13"},
}
SKIP = {
    "kind": "skip",
    "material_key": "Iso E Super",
    "reason": "already have enough",
    "decided_by": "Kenny",
    "decided_at": "2026-10-15",
    "source": "Lab review 2026-10-15",
}
ORDERED = {
    "kind": "order",
    "order_id": "PW-1001",
    "shop": "PW",
    "material_key": "Iso E Super",
    "offer_key": "pw:4JD02734",
    "pack": "25 g",
    "shown_price": {"amount": "12.5", "currency": "USD", "observed_on": "2026-10-14"},
    "state": "ORDERED",
}
ENTRIES = {
    "fx_rate": {"kind": "fx_rate", "rate": "33.25"},
    "budget": {"kind": "budget", "amount_thb": 5000},
    "budget_clear": {"kind": "budget", "clear": True},
    "match": {
        "kind": "match",
        "material_key": "Iso E Super",
        "offer_key": "pw:4JD02734",
        "answer": "SAME",
        "title_at_confirm": "Iso E Super (IFF) 25g",
    },
    "pick": PICK,
    "skip": SKIP,
    "order": ORDERED,
}


@pytest.fixture
def log(tmp_path: Path) -> Path:
    return tmp_path / "data" / "user" / "user_buy_events.jsonl"


def _record(log: Path, *entries: dict, now: datetime | None = None) -> tuple[dict, ...]:
    return record_buy_events(list(entries), path=log, now=now)


def _content(event: dict) -> dict:
    envelope = {"schema_version", "event_id", "recorded_at", "prev_event_sha256", "event_sha256"}
    return {key: value for key, value in event.items() if key not in envelope}


# --- round trips --------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_each_kind_round_trips(log: Path, name: str) -> None:
    (stored,) = _record(log, ENTRIES[name])
    loaded = load_buy_events(log)
    assert loaded == (stored,)
    assert stored["schema_version"] == "buy-event-v1"
    assert len(stored["event_id"]) == 32
    assert stored["prev_event_sha256"] == ""
    assert stored["kind"] == ENTRIES[name]["kind"]


def test_stored_values_are_normalized(log: Path) -> None:
    fx, budget, pick = _record(log, ENTRIES["fx_rate"], ENTRIES["budget"], PICK)
    assert fx["rate"] == "33.25" and fx["pair"] == "USD/THB"
    assert budget["amount_thb"] == "5000"
    assert pick["price"]["amount"] == "450.5"
    assert _content(pick) == {**PICK, "price": {**PICK["price"], "amount": "450.5"}}


def test_events_chain_to_the_previous_one(log: Path) -> None:
    first, second = _record(log, ENTRIES["fx_rate"], ENTRIES["match"])
    (third,) = _record(log, SKIP)
    assert second["prev_event_sha256"] == first["event_sha256"]
    assert third["prev_event_sha256"] == second["event_sha256"]
    assert load_buy_events(log) == (first, second, third)


def test_missing_file_is_an_empty_log(log: Path) -> None:
    assert load_buy_events(log) == ()


def test_injected_now_lands_in_recorded_at(log: Path) -> None:
    moment = datetime(2026, 10, 15, 8, 30, tzinfo=UTC)
    (stored,) = _record(log, ENTRIES["fx_rate"], now=moment)
    assert stored["recorded_at"] == "2026-10-15T08:30:00Z"
    assert load_buy_events(log)[0]["recorded_at"] == "2026-10-15T08:30:00Z"


def test_default_path_is_data_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PERFUME_BUY_EVENTS_PATH", raising=False)
    root = Path(buy_events.__file__).resolve().parents[1]
    assert buy_events_path() == root / "data" / "user" / "user_buy_events.jsonl"


def test_env_var_overrides_the_path(monkeypatch: pytest.MonkeyPatch, log: Path) -> None:
    monkeypatch.setenv("PERFUME_BUY_EVENTS_PATH", str(log))
    record_buy_events([ENTRIES["fx_rate"]])
    assert log.exists()
    assert len(load_buy_events()) == 1


# --- validation ---------------------------------------------------------------


@pytest.mark.parametrize("rate", ["25", "45", 25, "45.00"])
def test_fx_rate_bounds_are_inclusive(log: Path, rate: object) -> None:
    (stored,) = _record(log, {"kind": "fx_rate", "rate": rate})
    assert stored["rate"] in ("25", "45")


@pytest.mark.parametrize("rate", ["24.99", "45.01", "0", "-30", "NaN", "abc"])
def test_fx_rate_outside_25_to_45_is_refused(log: Path, rate: str) -> None:
    with pytest.raises(BuyEventError) as caught:
        _record(log, {"kind": "fx_rate", "rate": rate})
    if rate in ("24.99", "45.01", "0", "-30"):
        assert caught.value.code == "BUY_FX_RATE_OUT_OF_RANGE"
    assert not log.exists()


def test_fx_rate_pair_is_fixed(log: Path) -> None:
    with pytest.raises(BuyEventError):
        _record(log, {"kind": "fx_rate", "rate": "33", "pair": "EUR/THB"})


def test_unknown_kind_is_refused(log: Path) -> None:
    with pytest.raises(BuyEventError) as caught:
        _record(log, {"kind": "wish", "material_key": "x"})
    assert caught.value.code == "BUY_EVENT_UNKNOWN_KIND"


def test_unknown_field_is_refused(log: Path) -> None:
    with pytest.raises(BuyEventError) as caught:
        _record(log, {**SKIP, "note": "extra"})
    assert caught.value.code == "BUY_EVENT_UNKNOWN_FIELD"
    with pytest.raises(BuyEventError):
        _record(log, {**PICK, "price": {**PICK["price"], "discount": "5"}})


def test_envelope_fields_cannot_be_supplied(log: Path) -> None:
    with pytest.raises(BuyEventError):
        _record(log, {**SKIP, "recorded_at": "2020-01-01T00:00:00Z"})


@pytest.mark.parametrize("reason", ["two\nlines", "carriage\rreturn", "trailing\n"])
def test_newline_in_text_is_refused(log: Path, reason: str) -> None:
    with pytest.raises(BuyEventError):
        _record(log, {**SKIP, "reason": reason})


def test_text_is_stripped_and_capped(log: Path) -> None:
    (stored,) = _record(log, {**SKIP, "reason": "  padded  "})
    assert stored["reason"] == "padded"
    with pytest.raises(BuyEventError):
        _record(log, {**SKIP, "reason": "x" * 201})
    with pytest.raises(BuyEventError):
        _record(log, {**SKIP, "reason": "   "})


@pytest.mark.parametrize(
    "entry",
    [
        {"kind": "budget", "amount_thb": 0},
        {"kind": "budget", "amount_thb": "1000000.01"},
        {"kind": "budget"},
        {"kind": "budget", "clear": False},
        {"kind": "budget", "clear": True, "amount_thb": 10},
        {**ENTRIES["match"], "answer": "MAYBE"},
        {**PICK, "tier": 3},
        {**PICK, "tier": True},
        {**PICK, "decided_at": "2026-02-30"},
        {**PICK, "decided_at": "14/10/2026"},
        {**PICK, "price": {**PICK["price"], "currency": "EUR"}},
        {**PICK, "price": {**PICK["price"], "amount": "0"}},
        {key: value for key, value in PICK.items() if key != "dose"},
        {**ORDERED, "shop": "EBAY"},
        {**ORDERED, "state": "LOST"},
        {key: value for key, value in ORDERED.items() if key != "shown_price"},
    ],
)
def test_invalid_entries_are_refused(log: Path, entry: dict) -> None:
    with pytest.raises(BuyEventError):
        _record(log, entry)


def test_budget_upper_bound_is_inclusive(log: Path) -> None:
    (stored,) = _record(log, {"kind": "budget", "amount_thb": "1000000"})
    assert stored["amount_thb"] == "1000000"


def test_order_after_ordered_may_omit_shown_price(log: Path) -> None:
    arrived = {key: value for key, value in ORDERED.items() if key != "shown_price"}
    (stored,) = _record(log, {**arrived, "state": "ARRIVED"})
    assert "shown_price" not in stored


def test_batch_is_all_or_none(log: Path) -> None:
    _record(log, ENTRIES["fx_rate"])
    before = log.read_bytes()
    with pytest.raises(BuyEventError):
        _record(log, SKIP, {**SKIP, "reason": "bad\nreason"})
    assert log.read_bytes() == before


# --- tamper detection ---------------------------------------------------------


def _three_line_log(log: Path) -> list[str]:
    _record(log, ENTRIES["fx_rate"], ENTRIES["match"], SKIP)
    return log.read_text(encoding="utf-8").splitlines()


def test_edited_line_is_detected(log: Path) -> None:
    lines = _three_line_log(log)
    event = json.loads(lines[1])
    event["answer"] = "DIFFERENT"  # still a valid entry; only the hash can tell
    lines[1] = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(BuyEventLogCorruptError, match="line 2"):
        load_buy_events(log)


def test_deleted_middle_line_is_detected(log: Path) -> None:
    lines = _three_line_log(log)
    log.write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")
    with pytest.raises(BuyEventLogCorruptError):
        load_buy_events(log)


def test_swapped_pair_is_detected(log: Path) -> None:
    lines = _three_line_log(log)
    log.write_text("\n".join([lines[0], lines[2], lines[1]]) + "\n", encoding="utf-8")
    with pytest.raises(BuyEventLogCorruptError):
        load_buy_events(log)


def test_tampered_log_refuses_further_writes(log: Path) -> None:
    lines = _three_line_log(log)
    log.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
    before = log.read_bytes()
    with pytest.raises(BuyEventLogCorruptError):
        _record(log, ENTRIES["fx_rate"])
    assert log.read_bytes() == before


def test_log_over_5_mb_is_refused(log: Path) -> None:
    log.parent.mkdir(parents=True)
    log.write_text(" " * 5_000_001, encoding="utf-8")
    with pytest.raises(BuyEventLogCorruptError, match="5 MB"):
        load_buy_events(log)


# --- state fold ---------------------------------------------------------------


def test_buy_state_of_empty_log() -> None:
    assert buy_state(()) == {
        "fx_rate": None,
        "budget": None,
        "matches": {},
        "decisions": {},
        "orders": {},
    }


def test_latest_fx_rate_wins(log: Path) -> None:
    _record(log, {"kind": "fx_rate", "rate": "33"}, now=datetime(2026, 10, 1, tzinfo=UTC))
    _record(log, {"kind": "fx_rate", "rate": "34.5"}, now=datetime(2026, 10, 2, tzinfo=UTC))
    state = buy_state(load_buy_events(log))
    assert state["fx_rate"] == {
        "rate": "34.5",
        "pair": "USD/THB",
        "recorded_at": "2026-10-02T00:00:00Z",
    }


def test_budget_clear_removes_the_budget(log: Path) -> None:
    _record(log, ENTRIES["budget"])
    assert buy_state(load_buy_events(log))["budget"]["amount_thb"] == "5000"
    _record(log, ENTRIES["budget_clear"])
    assert buy_state(load_buy_events(log))["budget"] is None
    _record(log, {"kind": "budget", "amount_thb": "800"})
    assert buy_state(load_buy_events(log))["budget"]["amount_thb"] == "800"


def test_skip_after_pick_replaces_it(log: Path) -> None:
    _record(log, PICK, SKIP)
    decision = buy_state(load_buy_events(log))["decisions"]["Iso E Super"]
    assert decision["kind"] == "skip"
    assert decision["reason"] == "already have enough"
    assert "tier" not in decision


def test_pick_after_skip_replaces_it(log: Path) -> None:
    _record(log, SKIP, PICK)
    decision = buy_state(load_buy_events(log))["decisions"]["Iso E Super"]
    assert decision["kind"] == "pick"
    assert decision["tier"] == 1
    assert decision["price"]["pack"] == "25 g"


def test_latest_match_answer_wins(log: Path) -> None:
    _record(log, ENTRIES["match"], {**ENTRIES["match"], "answer": "DIFFERENT"})
    state = buy_state(load_buy_events(log))
    assert state["matches"][("Iso E Super", "pw:4JD02734")]["answer"] == "DIFFERENT"


def test_arrived_order_keeps_ordered_at_and_shown_price(log: Path) -> None:
    _record(log, ORDERED, now=datetime(2026, 10, 14, 9, tzinfo=UTC))
    arrived = {key: value for key, value in ORDERED.items() if key != "shown_price"}
    _record(log, {**arrived, "state": "ARRIVED"}, now=datetime(2026, 10, 20, 9, tzinfo=UTC))
    order = buy_state(load_buy_events(log))["orders"][("PW-1001", "Iso E Super")]
    assert order["state"] == "ARRIVED"
    assert order["ordered_at"] == "2026-10-14T09:00:00Z"
    assert order["recorded_at"] == "2026-10-20T09:00:00Z"
    assert order["shown_price"] == {
        "amount": "12.5",
        "currency": "USD",
        "observed_on": "2026-10-14",
    }
    assert (order["shop"], order["offer_key"], order["pack"]) == ("PW", "pw:4JD02734", "25 g")


def test_buy_state_to_json_uses_stable_string_keys(log: Path) -> None:
    _record(log, ENTRIES["match"], ORDERED, ENTRIES["fx_rate"])
    as_json = buy_state_to_json(buy_state(load_buy_events(log)))
    assert list(as_json["matches"]) == ['["Iso E Super","pw:4JD02734"]']
    assert list(as_json["orders"]) == [state_key("PW-1001", "Iso E Super")]
    assert json.loads(json.dumps(as_json)) == as_json


# --- LABPICKS -----------------------------------------------------------------


def _block(**overrides: object) -> dict:
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
                "price": {
                    "amount": 450.5,
                    "currency": "THB",
                    "pack": "25 g",
                    "observed_on": "2026-10-13",
                },
            },
            {"material_key": "Ambrox", "tier": 2, "dose": "10%", "reason": "later"},
        ],
        "skips": [{"material_key": "Galaxolide", "reason": "musk already covered"}],
    }
    block.update(overrides)
    return block


def _paste(block: dict) -> str:
    return "\n  \nLABPICKS/1\n" + json.dumps(block, indent=2) + "\n"


def test_parse_labpicks_accepts_a_good_block(log: Path) -> None:
    entries = parse_labpicks(_paste(_block()))
    assert [entry["kind"] for entry in entries] == ["pick", "pick", "skip"]
    first = entries[0]
    assert first["decided_at"] == "2026-10-15"
    assert first["decided_by"] == "Kenny"
    assert first["source"] == "Claude review of the Iris Cathedral gaps"
    assert first["price"]["amount"] == "450.5"
    assert "offer_key" not in entries[1]
    assert not log.exists()
    stored = record_buy_events(entries, path=log)
    assert [_content(event) for event in stored] == entries


@pytest.mark.parametrize(
    "text",
    [
        json.dumps(_block()),
        "LABPICKS/2\n" + json.dumps(_block()),
        "labpicks/1\n" + json.dumps(_block()),
        "",
    ],
)
def test_parse_labpicks_needs_the_marker(text: str) -> None:
    with pytest.raises(BuyEventError) as caught:
        parse_labpicks(text)
    assert caught.value.code == "BUY_LABPICKS_INVALID"


@pytest.mark.parametrize(
    "text",
    ["LABPICKS/1\n{not json", "LABPICKS/1\n[]", 'LABPICKS/1\n{"source": NaN}'],
)
def test_parse_labpicks_refuses_bad_json(text: str) -> None:
    with pytest.raises(BuyEventError) as caught:
        parse_labpicks(text)
    assert caught.value.code == "BUY_LABPICKS_INVALID"


def test_parse_labpicks_refuses_tier_3_naming_the_item() -> None:
    block = _block()
    block["picks"][1]["tier"] = 3
    with pytest.raises(BuyEventError, match=r"picks\[1\] \(Ambrox\)") as caught:
        parse_labpicks(_paste(block))
    assert caught.value.code == "BUY_LABPICKS_INVALID"


def test_parse_labpicks_refuses_more_than_100_entries() -> None:
    skips = [{"material_key": f"Material {index}", "reason": "no"} for index in range(99)]
    with pytest.raises(BuyEventError, match="101") as caught:
        parse_labpicks(_paste(_block(skips=skips)))
    assert caught.value.code == "BUY_LABPICKS_INVALID"
    assert len(parse_labpicks(_paste(_block(skips=skips[:98])))) == 100


@pytest.mark.parametrize(
    "block",
    [
        _block(reviewed_on="15 Oct 2026"),
        _block(extra="field"),
        _block(
            picks=[
                {
                    "material_key": "Ambrox",
                    "tier": 1,
                    "dose": "1%",
                    "reason": "x",
                    "decided_by": "someone else",
                }
            ]
        ),
        _block(skips=[{"material_key": "Iso E Super", "reason": "dupe"}]),
        _block(picks=[], skips=[]),
    ],
)
def test_parse_labpicks_refuses_other_problems(block: dict) -> None:
    with pytest.raises(BuyEventError) as caught:
        parse_labpicks(_paste(block))
    assert caught.value.code == "BUY_LABPICKS_INVALID"


def test_parse_labpicks_refuses_over_200_kb() -> None:
    with pytest.raises(BuyEventError, match="200 KB"):
        parse_labpicks("LABPICKS/1\n" + " " * 200_001)
