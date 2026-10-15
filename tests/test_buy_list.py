"""The Buy page's data: offers, match states, rate, orders, decisions and tiers."""

from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from engine.buy_events import load_buy_events, record_buy_events
from engine.buy_list import BUY_LIST_SCHEMA, build_buy_list, day_month_label
from engine.supplier_offers.pw_prices import PwPrice

TODAY = date(2026, 10, 15)
APR_11 = date(2026, 4, 11)
HEADER = "PW list prices from 11 Apr. Check on PW before ordering."


def _price(sku, title, usd, form="neat", strength=Decimal(1), solvent=None, parent=None):
    usd = Decimal(usd)
    return PwPrice(
        sku=sku,
        material_name=title,
        usd_per_g=usd,
        form=form,
        strength=strength,
        solvent=solvent,
        usd_per_active_g=None if strength is None else usd / strength,
        observed_on=APR_11,
        source="materials_yaml",
        in_stock="UNKNOWN",
        parent_sku=parent,
    )


PRICES = {
    p.sku: p
    for p in (
        _price("1IR00001", "Orris Concrete", "10"),
        _price("2IR00002", "Orris Concrete", "1.5", "10% in DPG", Decimal("0.1"), "DPG", "1IR00001"),
        _price("5VD10871", "Methyl Laitone", "2"),
        _price("4JD02734", "Jasmine Lactone", "3"),
        _price("3SW00003", "Sandalwood Oil", "10"),
        _price("6VT00006", "Vetiver Oil", "4"),
    )
}
# A prefix-5 SKU marked neat cannot be trusted: no strength.
PRICES["5VD10871"] = _price("5VD10871", "Methyl Laitone", "2", strength=None)


def _material(name, sku, alternates=()):
    return SimpleNamespace(
        canonical_name=name,
        supplier=SimpleNamespace(
            perfumersworld_sku=sku,
            other={"pw_alternate_forms": [{"form": "x", "sku": a} for a in alternates]},
        ),
    )


class FakeRegistry:
    def __init__(self, *materials):
        self._by_name = {m.canonical_name.casefold(): m for m in materials}

    def get(self, name):
        return self._by_name.get(name.casefold())


REGISTRY = FakeRegistry(
    _material("Orris Concrete", "1IR00001", ["2IR00002", "9NO00000"]),
    _material("Methyl Laitone", "5VD10871"),
    _material("Jasmine Lactone", "4JD02734"),
    _material("Lactojasmone", "4JD02734"),
    _material("Sandalwood Oil", "3SW00003"),
    _material("Vetiver Oil", "6VT00006"),
    _material("Unpriced Thing", None),
)


def _card(formula_id, fraction="0.01"):
    return {
        "formula_id": formula_id,
        "version": 1,
        "name": formula_id.title(),
        "neat_fraction": None if fraction is None else Decimal(fraction),
    }


def _need(material, *cards):
    return {"material_key": material.casefold(), "material": material, "cards": list(cards)}


def _needs(*rows, disagreements=()):
    return {"needs": list(rows), "disagreements": list(disagreements), "unreadable": []}


def _events(tmp_path, *batches):
    """Record (iso_day, [entries]) batches in order and read them back."""

    path = tmp_path / "buy.jsonl"
    for day, entries in batches:
        moment = datetime.fromisoformat(day).replace(hour=9, tzinfo=UTC)
        record_buy_events(entries, path=path, now=moment)
    return load_buy_events(path)


def _build(needs, events=(), **kwargs):
    kwargs.setdefault("today", TODAY)
    kwargs.setdefault("prices", PRICES)
    kwargs.setdefault("registry", REGISTRY)
    return build_buy_list(needs, events=events, **kwargs)


def _row(result, key):
    return next(row for row in result["buy_first"] if row["material_key"] == key)


def _offers(result, key):
    return {offer["offer_key"]: offer for offer in _row(result, key)["offers"]}


RATE = {"kind": "fx_rate", "rate": "33.55"}


def _match(key, offer_key, answer, title):
    return {
        "kind": "match",
        "material_key": key,
        "offer_key": offer_key,
        "answer": answer,
        "title_at_confirm": title,
    }


def _order(state, order_id="PW-1", key="sandalwood oil", offer_key="pw:3SW00003"):
    entry = {
        "kind": "order",
        "order_id": order_id,
        "shop": "PW",
        "material_key": key,
        "offer_key": offer_key,
        "pack": "5 g",
        "state": state,
    }
    if state == "ORDERED":
        entry["shown_price"] = {"amount": "50.9", "currency": "USD", "observed_on": "2026-04-11"}
    return entry


# --- header, labels, contract -------------------------------------------------


def test_header_and_row_date_labels():
    result = _build(_needs(_need("Sandalwood Oil", _card("santal"))))
    assert result["schema_version"] == BUY_LIST_SCHEMA
    assert result["generated_on"] == "2026-10-15"
    assert result["price_header"] == HEADER
    offer = _row(result, "sandalwood oil")["offers"][0]
    assert offer["observed_on"] == "2026-04-11"
    assert offer["observed_label"] == "11 Apr"
    assert offer["product_url"].endswith("3SW00003")
    assert offer["default_pack_g"] == "5"
    assert day_month_label(date(2026, 1, 3)) == "3 Jan"
    assert result["inventory_modified"] is False
    assert result["formula_modified"] is False
    assert result["compounding_authority"] is False
    json.dumps(result)  # every value is plain JSON


def test_header_is_dated_by_prices_on_the_page():
    newer = dict(PRICES)
    newer["7NW00007"] = PwPrice(
        **{**PRICES["6VT00006"].__dict__, "sku": "7NW00007", "observed_on": date(2026, 9, 30)}
    )
    result = _build(_needs(_need("Sandalwood Oil", _card("santal"))), prices=newer)
    assert result["price_header"] == HEADER


# --- offers and match states --------------------------------------------------


def test_offer_order_and_confirmed_beats_cheaper(tmp_path):
    events = _events(
        tmp_path, ("2026-10-14", [_match("orris concrete", "pw:2IR00002", "SAME", "Orris Concrete")])
    )
    result = _build(_needs(_need("Orris Concrete", _card("iris"))), events)
    offers = _row(result, "orris concrete")["offers"]
    # The alternate is dearer per active gram (15 vs 10) but confirmed; the
    # unpriced alternate SKU is left out.
    assert [o["offer_key"] for o in offers] == ["pw:2IR00002", "pw:1IR00001"]
    assert [o["match"] for o in offers] == ["confirmed", "probable"]
    assert offers[0]["match_question"] is None
    assert offers[0]["parent_sku"] == "1IR00001"
    assert offers[0]["strength"] == "0.1"
    assert offers[1]["match_question"] == "Is PW 1IR00001 'Orris Concrete' your Orris Concrete?"
    assert all(o["tickable"] for o in offers)


def test_probable_offers_sort_by_cost_per_active_gram():
    result = _build(_needs(_need("Orris Concrete", _card("iris"))))
    offers = _row(result, "orris concrete")["offers"]
    assert [o["offer_key"] for o in offers] == ["pw:1IR00001", "pw:2IR00002"]
    assert [o["usd_per_active_g"] for o in offers] == ["10", "15"]


def test_prefix_5_neat_sku_is_price_only(tmp_path):
    events = _events(tmp_path, ("2026-10-14", [RATE]))
    result = _build(_needs(_need("Methyl Laitone", _card("milk"))), events)
    offer = _row(result, "methyl laitone")["offers"][0]
    assert offer["match"] == "price_only"
    assert offer["tickable"] is True
    assert offer["match_question"] == "Is PW 5VD10871 'Methyl Laitone' your Methyl Laitone?"
    assert offer["usd_per_g"] == "2"
    assert offer["upfront_usd"] == "10.90"
    assert offer["upfront_thb"] == "365.695"
    assert offer["usd_per_active_g"] is None
    assert offer["neat_thb_per_g"] is None
    assert offer["cost_per_bottle_thb"] is None
    assert _row(result, "methyl laitone")["cost_per_bottle_thb"] is None


def test_mislabelled_offer_is_unknown_without_price_or_tick(tmp_path):
    events = _events(tmp_path, ("2026-10-14", [RATE]))
    result = _build(
        _needs(_need("Jasmine Lactone", _card("jas")), _need("Lactojasmone", _card("lacto"))),
        events,
    )
    unknown = _row(result, "jasmine lactone")["offers"][0]
    assert unknown["match"] == "unknown"
    assert unknown["tickable"] is False
    assert unknown["match_question"] is None
    for field in ("usd_per_g", "usd_per_active_g", "upfront_usd", "upfront_thb",
                  "neat_thb_per_g", "cost_per_bottle_thb"):
        assert unknown[field] is None, field
    assert _row(result, "jasmine lactone")["cost_per_bottle_thb"] is None
    # For the material PW really sells under that title, the offer is ordinary.
    assert _row(result, "lactojasmone")["offers"][0]["match"] == "probable"


def test_different_answer_drops_the_offer(tmp_path):
    events = _events(
        tmp_path, ("2026-10-14", [_match("orris concrete", "pw:1IR00001", "DIFFERENT", "Orris Concrete")])
    )
    result = _build(_needs(_need("Orris Concrete", _card("iris"))), events)
    assert list(_offers(result, "orris concrete")) == ["pw:2IR00002"]


def test_changed_shop_title_asks_again_with_the_old_title(tmp_path):
    events = _events(
        tmp_path, ("2026-10-14", [_match("sandalwood oil", "pw:3SW00003", "SAME", "Sandalwood Oil E.I.")])
    )
    offer = _row(_build(_needs(_need("Sandalwood Oil", _card("s"))), events), "sandalwood oil")[
        "offers"
    ][0]
    assert offer["match"] == "probable"
    assert offer["previous_title"] == "Sandalwood Oil E.I."
    assert offer["title"] == "Sandalwood Oil"
    assert offer["match_question"] == "Is PW 3SW00003 'Sandalwood Oil' your Sandalwood Oil?"


def test_material_without_any_price_has_no_offers():
    result = _build(_needs(_need("Unpriced Thing", _card("x")), _need("Not In Registry", _card("y"))))
    assert _row(result, "unpriced thing")["offers"] == []
    assert _row(result, "not in registry")["offers"] == []


# --- rate -----------------------------------------------------------------------


def test_no_rate_leaves_thb_empty_and_asks_for_it():
    result = _build(_needs(_need("Sandalwood Oil", _card("santal"))))
    assert result["fx"] is None
    assert result["rate_banner"] == {"reason": "missing"}
    row = _row(result, "sandalwood oil")
    offer = row["offers"][0]
    assert offer["usd_per_g"] == "10"
    assert offer["upfront_usd"] == "50.90"
    assert offer["upfront_thb"] is None
    assert offer["neat_thb_per_g"] is None
    assert offer["cost_per_bottle_thb"] is None
    assert row["cost_per_bottle_thb"] is None
    assert row["cards"][0]["cost_per_bottle_thb"] is None


def test_rate_older_than_30_days_still_prices_and_brings_the_banner_back(tmp_path):
    events = _events(tmp_path, ("2026-09-14", [RATE]))
    result = _build(_needs(_need("Sandalwood Oil", _card("santal"))), events)
    assert result["fx"] == {
        "rate": "33.55",
        "set_at": "2026-09-14T09:00:00Z",
        "set_on": "2026-09-14",
        "stale": True,
    }
    assert result["rate_banner"] == {"reason": "stale", "last_set_on": "2026-09-14"}
    assert _row(result, "sandalwood oil")["offers"][0]["upfront_thb"] == "1707.695"


def test_rate_30_days_old_is_not_stale(tmp_path):
    events = _events(tmp_path, ("2026-09-15", [RATE]))
    result = _build(_needs(_need("Sandalwood Oil", _card("santal"))), events)
    assert result["fx"]["stale"] is False
    assert result["rate_banner"] is None


def test_cost_per_bottle_range_across_two_cards(tmp_path):
    events = _events(tmp_path, ("2026-10-14", [RATE]))
    needs = _needs(
        _need("Sandalwood Oil", _card("santal", "0.01"), _card("cedar", "0.03"), _card("open", None))
    )
    row = _row(_build(needs, events), "sandalwood oil")
    # 10 US$/g x 33.55 x fraction x 6 g
    assert [card["cost_per_bottle_thb"] for card in row["cards"]] == ["20.13", "60.39", None]
    assert row["cards"][0]["neat_fraction"] == "0.01"
    assert row["cost_per_bottle_thb"] == {"min": "20.13", "max": "60.39"}
    offer = row["offers"][0]
    assert offer["cost_per_bottle_thb"] == {"min": "20.13", "max": "60.39"}
    assert offer["neat_thb_per_g"] == "335.5"


def test_each_card_keeps_its_own_row_text_for_the_material():
    # Two cards spell one material differently; What can I make matches each card by its own text.
    santal = {**_card("santal"), "material": "Sandalwood Oil"}
    cedar = {**_card("cedar", "0.03"), "material": "  sandalwood OIL"}
    disagreement = {**_need("Vetiver Oil", {**_card("v"), "material": "vetiver oil"}), "code": "X", "reason": "r"}
    result = _build(_needs(_need("Sandalwood Oil", santal, cedar), disagreements=[disagreement]))

    row = _row(result, "sandalwood oil")
    assert row["material"] == "Sandalwood Oil"
    assert [(card["name"], card["material"]) for card in row["cards"]] == [
        ("Santal", "Sandalwood Oil"), ("Cedar", "  sandalwood OIL"),
    ]
    assert result["check_stock"][0]["cards"][0]["material"] == "vetiver oil"
    json.dumps(result)


def test_old_prices_never_drop_rows():
    needs = _needs(*(_need(name, _card("f")) for name in ("Sandalwood Oil", "Vetiver Oil")))
    result = _build(needs)
    assert {row["material_key"] for row in result["buy_first"]} == {"sandalwood oil", "vetiver oil"}
    for row in result["buy_first"]:
        assert row["offers"][0]["price_age_days"] == 187


def test_buy_first_sorts_by_need_count_then_material():
    needs = _needs(
        _need("Vetiver Oil", _card("a")),
        _need("Sandalwood Oil", _card("a")),
        _need("Orris Concrete", _card("a"), _card("b")),
    )
    keys = [row["material_key"] for row in _build(needs)["buy_first"]]
    assert keys == ["orris concrete", "sandalwood oil", "vetiver oil"]


# --- orders ---------------------------------------------------------------------


def _santal_needs():
    return _needs(_need("Sandalwood Oil", _card("santal")), _need("Vetiver Oil", _card("v")))


def test_ordered_material_leaves_buy_first_for_on_the_way(tmp_path):
    events = _events(tmp_path, ("2026-10-10", [_order("ORDERED")]))
    result = _build(_santal_needs(), events)
    assert [row["material_key"] for row in result["buy_first"]] == ["vetiver oil"]
    (group,) = result["on_the_way"]
    assert group["shop"] == "PW"
    assert group["order_id"] == "PW-1"
    assert group["ordered_on"] == "2026-10-10"
    assert group["days"] == 5
    assert group["nudge"] is False
    assert group["nudge_text"] == "PW parcel still on the way?"
    (line,) = group["lines"]
    assert line["material"] == "Sandalwood Oil"
    assert line["offer_key"] == "pw:3SW00003"
    assert line["pack"] == "5 g"
    assert line["state"] == "ORDERED"
    assert line["shown_price"]["amount"] == "50.9"


def test_on_the_way_lines_carry_the_offer_label_from_the_price_index(tmp_path):
    events = _events(
        tmp_path,
        (
            "2026-10-10",
            [
                _order("ORDERED", key="orris concrete", offer_key="pw:2IR00002"),
                _order("ORDERED", key="sandalwood oil", offer_key="pw:3SW00003"),
                _order("ORDERED", key="vetiver oil", offer_key="pw:9XX99999"),
            ],
        ),
    )
    (group,) = _build(_santal_needs(), events)["on_the_way"]
    lines = {line["offer_key"]: line for line in group["lines"]}
    label = ("title", "form", "strength", "solvent")
    assert [lines["pw:2IR00002"][key] for key in label] == [
        "Orris Concrete", "10% in DPG", "0.1", "DPG"
    ]
    assert [lines["pw:3SW00003"][key] for key in label] == ["Sandalwood Oil", "neat", "1", None]
    assert [lines["pw:9XX99999"][key] for key in label] == [None, None, None, None]


def test_nudge_from_day_10(tmp_path):
    day_9 = _build(_santal_needs(), _events(tmp_path / "a", ("2026-10-06", [_order("ORDERED")])))
    day_10 = _build(_santal_needs(), _events(tmp_path / "b", ("2026-10-05", [_order("ORDERED")])))
    assert day_9["on_the_way"][0]["nudge"] is False
    assert day_10["on_the_way"][0]["days"] == 10
    assert day_10["on_the_way"][0]["nudge"] is True


def test_unanswered_on_day_21_returns_to_buy_first(tmp_path):
    day_20 = _build(_santal_needs(), _events(tmp_path / "a", ("2026-09-25", [_order("ORDERED")])))
    assert day_20["on_the_way"][0]["days"] == 20
    day_21 = _build(_santal_needs(), _events(tmp_path / "b", ("2026-09-24", [_order("ORDERED")])))
    assert day_21["on_the_way"] == []
    assert _row(day_21, "sandalwood oil")["returned_from_order"] == {
        "order_id": "PW-1",
        "shop": "PW",
        "ordered_on": "2026-09-24",
        "state": "not_arrived",
    }


def test_still_coming_restarts_the_clock(tmp_path):
    events = _events(
        tmp_path, ("2026-09-20", [_order("ORDERED")]), ("2026-10-01", [_order("STILL_COMING")])
    )
    result = _build(_santal_needs(), events)
    (group,) = result["on_the_way"]
    assert group["days"] == 14
    assert group["ordered_on"] == "2026-09-20"
    assert group["lines"][0]["state"] == "STILL_COMING"
    assert "sandalwood oil" not in {row["material_key"] for row in result["buy_first"]}


def test_didnt_come_returns_the_row(tmp_path):
    events = _events(
        tmp_path, ("2026-10-01", [_order("ORDERED")]), ("2026-10-12", [_order("DIDNT_COME")])
    )
    result = _build(_santal_needs(), events)
    assert result["on_the_way"] == []
    row = _row(result, "sandalwood oil")
    assert row["returned_from_order"] == {
        "order_id": "PW-1", "shop": "PW", "ordered_on": "2026-10-01", "state": "DIDNT_COME",
    }
    assert row["offers"][0]["last_not_this_on"] is None


def test_not_this_returns_the_row_and_dates_the_offer(tmp_path):
    events = _events(
        tmp_path, ("2026-10-01", [_order("ORDERED")]), ("2026-10-12", [_order("NOT_THIS")])
    )
    row = _row(_build(_santal_needs(), events), "sandalwood oil")
    assert row["returned_from_order"]["state"] == "NOT_THIS"
    offer = row["offers"][0]
    assert offer["last_not_this_on"] == "2026-10-12"
    assert offer["match"] == "probable"


def test_a_parcel_asks_when_its_oldest_line_reaches_day_10(tmp_path):
    # Only the sandalwood line was answered "still coming"; the vetiver line's clock
    # still runs from the order and returns it on its own day 21.
    vetiver = _order("ORDERED", key="vetiver oil", offer_key="pw:6VT00006")
    events = _events(
        tmp_path,
        ("2026-10-01", [_order("ORDERED"), vetiver]),
        ("2026-10-12", [_order("STILL_COMING")]),
    )
    (group,) = _build(_santal_needs(), events)["on_the_way"]
    assert len(group["lines"]) == 2
    assert group["days"] == 14
    assert group["nudge"] is True


@pytest.fixture
def thai_clock(monkeypatch):
    """The PC's clock on Thai time (UTC+7), as on Kenny's PC."""

    tzset = getattr(time, "tzset", None)
    if tzset is None:
        pytest.skip("needs time.tzset, which Windows lacks")
    monkeypatch.setenv("TZ", "ICT-7")
    tzset()
    yield
    monkeypatch.undo()
    tzset()


def test_days_count_on_the_pcs_own_calendar(tmp_path, thai_clock):
    # 23:30 UTC on 1 Oct is 06:30 on 2 Oct in Thailand: day 9 on 11 Oct, no nudge yet.
    path = tmp_path / "buy.jsonl"
    record_buy_events(
        [_order("ORDERED"), RATE], path=path, now=datetime(2026, 10, 1, 23, 30, tzinfo=UTC)
    )
    result = _build(_santal_needs(), load_buy_events(path), today=date(2026, 10, 11))
    (group,) = result["on_the_way"]
    assert group["ordered_on"] == "2026-10-02"
    assert group["days"] == 9
    assert group["nudge"] is False
    assert result["fx"]["set_on"] == "2026-10-02"


def test_arrived_closes_the_order(tmp_path):
    events = _events(
        tmp_path, ("2026-10-01", [_order("ORDERED")]), ("2026-10-08", [_order("ARRIVED")])
    )
    result = _build(_santal_needs(), events)
    assert result["on_the_way"] == []
    assert _row(result, "sandalwood oil")["returned_from_order"] is None


# --- decisions --------------------------------------------------------------------


def _decision(kind, key, **extra):
    entry = {
        "kind": kind,
        "material_key": key,
        "reason": f"{kind} reason",
        "decided_by": "Kenny",
        "decided_at": "2026-10-15",
        "source": "Lab review 2026-10-15",
    }
    entry.update(extra)
    return entry


def test_skip_overrides_a_card_need(tmp_path):
    events = _events(
        tmp_path,
        ("2026-10-14", [_decision("pick", "sandalwood oil", tier=1, dose="2%")]),
        ("2026-10-15", [_decision("skip", "sandalwood oil")]),
    )
    needs = _needs(_need("Sandalwood Oil", _card("a"), _card("b")))
    result = _build(needs, events)
    assert result["buy_first"] == []
    assert result["tiers"]["1"] == []
    assert result["skip"] == [
        {
            "material_key": "sandalwood oil",
            "material": "Sandalwood Oil",
            "reason": "skip reason",
            "decided_by": "Kenny",
            "decided_at": "2026-10-15",
            "source": "Lab review 2026-10-15",
            "need_count": 2,
        }
    ]


def test_tiers_list_picks_with_review_prices(tmp_path):
    review_price = {"amount": "450", "currency": "THB", "pack": "10 g", "observed_on": "2026-10-14"}
    events = _events(
        tmp_path,
        (
            "2026-10-15",
            [
                _decision("pick", "sandalwood oil", tier=1, dose="2%",
                          offer_key="pw:3SW00003", price=review_price),
                _decision("pick", "vetiver oil", tier=2, dose="0.5%"),
            ],
        ),
    )
    result = _build(_santal_needs(), events)
    (tier_1,) = result["tiers"]["1"]
    assert tier_1 == {
        "material_key": "sandalwood oil",
        "material": "Sandalwood Oil",
        "tier": 1,
        "offer_key": "pw:3SW00003",
        "dose": "2%",
        "reason": "pick reason",
        "decided_by": "Kenny",
        "reviewed_on": "2026-10-15",
        "source": "Lab review 2026-10-15",
        "price": review_price,
        "offer_note": None,
        "need_count": 1,
    }
    (tier_2,) = result["tiers"]["2"]
    assert tier_2["material_key"] == "vetiver oil"
    assert tier_2["offer_key"] is None
    assert tier_2["price"] is None
    assert result["tiers"]["3"] == {"note": "needs fresh shop prices"}
    assert _row(result, "sandalwood oil")["pick_tier"] == 1
    assert _row(result, "vetiver oil")["pick_tier"] == 2


def test_a_pick_leaves_its_tier_once_ordered_and_comes_back_if_it_didnt_come(tmp_path):
    pick = _decision("pick", "sandalwood oil", tier=1, dose="2%")
    ordered = ("2026-10-10", [pick, _order("ORDERED")])

    def tier_1(*later):
        key = "-".join(state for _day_text, entries in later for state in [entries[0]["state"]])
        events = _events(tmp_path / (key or "ordered"), ordered, *later)
        return [row["material_key"] for row in _build(_santal_needs(), events)["tiers"]["1"]]

    assert tier_1() == []
    assert tier_1(("2026-10-12", [_order("ARRIVED")])) == []
    assert tier_1(("2026-10-12", [_order("ALREADY_HAVE")])) == []
    assert tier_1(("2026-10-12", [_order("DIDNT_COME")])) == ["sandalwood oil"]


def test_a_pick_whose_offer_is_not_the_material_shows_no_price(tmp_path):
    review_price = {"amount": "450", "currency": "THB", "pack": "10 g", "observed_on": "2026-10-14"}
    events = _events(
        tmp_path,
        (
            "2026-10-15",
            [
                _decision("pick", "sandalwood oil", tier=1, dose="2%",
                          offer_key="pw:3SW00003", price=review_price),
                _decision("pick", "vetiver oil", tier=2, dose="0.5%",
                          offer_key="pw:4JD02734", price=review_price),
                _match("sandalwood oil", "pw:3SW00003", "DIFFERENT", "Sandalwood Oil"),
            ],
        ),
    )
    result = _build(_santal_needs(), events)
    (tier_1,) = result["tiers"]["1"]
    assert tier_1["offer_key"] == "pw:3SW00003"
    assert tier_1["price"] is None
    assert tier_1["offer_note"] == (
        "You said PW 3SW00003 is a different material, so this pick has no price."
    )
    (tier_2,) = result["tiers"]["2"]
    assert tier_2["price"] is None
    assert tier_2["offer_note"] == "PW 4JD02734 may not be your Vetiver Oil, so this pick has no price."


def test_disagreements_go_to_check_stock_only():
    disagreement = {
        "material_key": "vetiver oil",
        "material": "Vetiver Oil",
        "cards": [_card("v", "0.02")],
        "code": "STOCK_SOURCES_DISAGREE",
        "reason": "inventory.txt lists it; the snapshot does not",
    }
    result = _build(_needs(_need("Sandalwood Oil", _card("s")), disagreements=[disagreement]))
    assert [row["material_key"] for row in result["buy_first"]] == ["sandalwood oil"]
    (check,) = result["check_stock"]
    assert check["material_key"] == "vetiver oil"
    assert check["code"] == "STOCK_SOURCES_DISAGREE"
    assert check["cards"][0]["neat_fraction"] == "0.02"
    assert "offers" not in check
    json.dumps(result)


def test_budget_passes_through(tmp_path):
    assert _build(_santal_needs())["budget"] is None
    events = _events(tmp_path, ("2026-10-14", [{"kind": "budget", "amount_thb": "1600"}]))
    assert _build(_santal_needs(), events)["budget"] == {"amount_thb": "1600"}


def test_similar_keeps_the_top_two_and_tolerates_unprofiled():
    def similar(material):
        if material == "Vetiver Oil":
            raise LookupError("no profile")
        return {
            "similar": [
                {"identity_name": f"Like {n}", "stocks": [{"stock_id": f"s{n}"}]} for n in range(3)
            ]
        }

    result = _build(_santal_needs(), similar=similar)
    assert _row(result, "sandalwood oil")["similar"] == [
        {"stock_id": "s0", "name": "Like 0"},
        {"stock_id": "s1", "name": "Like 1"},
    ]
    assert _row(result, "vetiver oil")["similar"] == []
