"""The Lab app's Buy page: what the cards need, priced from PerfumersWorld.

``build_buy_list`` joins three inputs into the page's data:

* the needs from ``engine.buy_needs.card_needs()`` (taken as data, not imported),
* the PerfumersWorld list prices of ``engine.supplier_offers.pw_prices``,
* Kenny's buy log, folded by ``engine.buy_events.buy_state``.

Pure and offline: it reads nothing but the default price index and material
registry, writes nothing, and never changes stock or formulas.  Decimals go out
as strings, unrounded (values computed with the USD/THB rate drop trailing
zeros); dates go out as ISO text.

An old price only informs (``price_age_days``); it never adds, removes or skips
a row.  Offer identity is judged per (material, offer): Kenny's ``match``
answers win, then a static mislabel table, then whether the strength parsed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from engine.buy_events import buy_state
from engine.supplier_offers.pw_prices import (
    DEFAULT_PACK_G,
    PwPrice,
    cost_per_bottle_thb,
    neat_thb_per_g,
    pw_price_index,
    pw_product_url,
    upfront_usd,
)

BUY_LIST_SCHEMA = "workbench-buy-list-v1"

# PerfumersWorld sells Lactojasmone under the title "Jasmine Lactone"; for any
# other material that offer's identity is unknown.
MISLABELS: Mapping[str, str] = {"pw:4JD02734": "lactojasmone"}

FX_STALE_AFTER_DAYS = 30
NUDGE_AFTER_DAYS = 10
RETURN_AFTER_DAYS = 21
TIER_3_NOTE = "needs fresh shop prices"

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_MATCH_RANK = {"confirmed": 0, "probable": 1, "price_only": 2, "unknown": 3}
_ON_THE_WAY_STATES = ("ORDERED", "STILL_COMING")
_RETURNED_STATES = ("DIDNT_COME", "NOT_THIS")


def day_month_label(day: date) -> str:
    """``11 Apr``: day and short English month, independent of the OS locale."""

    return f"{day.day} {_MONTHS[day.month - 1]}"


def _dec(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _thb(value: Decimal | None) -> str | None:
    # Rate products pile up trailing zeros (29.38980); drop them, never round.
    return None if value is None else format(value.normalize(), "f")


def _day(timestamp: str) -> date:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()


def _price_header(shown: Iterable[date], prices: Mapping[str, PwPrice]) -> str:
    """Dated by the newest price on the page; with none shown, the newest in the index."""

    newest = max(shown, default=None) or max(
        (price.observed_on for price in prices.values()), default=None
    )
    if newest is None:
        return "PW list prices. Check on PW before ordering."
    return f"PW list prices from {day_month_label(newest)}. Check on PW before ordering."


def _skus_for(material: Any) -> list[str]:
    supplier = material.supplier
    skus = [supplier.perfumersworld_sku]
    for entry in (supplier.other or {}).get("pw_alternate_forms") or []:
        if isinstance(entry, Mapping):
            skus.append(entry.get("sku"))
    seen: list[str] = []
    for sku in skus:
        text = sku.strip() if isinstance(sku, str) else ""
        if text and text not in seen:
            seen.append(text)
    return seen


def _match_state(
    price: PwPrice, material_key: str, answer: Mapping[str, Any] | None
) -> tuple[str | None, str | None]:
    """(match state, previous title); a ``None`` state drops the offer."""

    offer_key = f"pw:{price.sku}"
    if answer is not None and answer["answer"] == "DIFFERENT":
        return None, None
    mislabel = MISLABELS.get(offer_key)
    if mislabel is not None and mislabel != material_key.casefold():
        return "unknown", None
    previous = None
    if answer is not None:
        if answer["title_at_confirm"] == price.material_name:
            return "confirmed", None
        previous = answer["title_at_confirm"]
    return ("probable" if price.strength is not None else "price_only"), previous


def _range(values: Iterable[Decimal | None]) -> dict[str, str] | None:
    known = [value for value in values if value is not None]
    if not known:
        return None
    return {"min": _thb(min(known)), "max": _thb(max(known))}


def _offer(
    price: PwPrice,
    *,
    material_key: str,
    material: str,
    answer: Mapping[str, Any] | None,
    rate: Decimal | None,
    cards: list[Mapping[str, Any]],
    today: date,
    last_not_this_on: str | None,
) -> tuple[dict[str, Any], list[Decimal | None]] | None:
    match, previous_title = _match_state(price, material_key, answer)
    if match is None:
        return None
    priced = match != "unknown"
    upfront = upfront_usd(price) if priced else None
    card_costs: list[Decimal | None] = [None] * len(cards)
    per_g = None
    if priced and rate is not None:
        per_g = neat_thb_per_g(price, rate)
        card_costs = [
            None
            if card.get("neat_fraction") is None
            else cost_per_bottle_thb(price, rate, Decimal(card["neat_fraction"]))
            for card in cards
        ]
    question = None
    if match in ("probable", "price_only"):
        question = f"Is PW {price.sku} '{price.material_name}' your {material}?"
    offer = {
        "offer_key": f"pw:{price.sku}",
        "shop": "PW",
        "sku": price.sku,
        "title": price.material_name,
        "form": price.form,
        "strength": _dec(price.strength),
        "solvent": price.solvent,
        "parent_sku": price.parent_sku,
        "usd_per_g": _dec(price.usd_per_g) if priced else None,
        "usd_per_active_g": _dec(price.usd_per_active_g) if priced else None,
        "observed_on": price.observed_on.isoformat(),
        "observed_label": day_month_label(price.observed_on),
        "source": price.source,
        "in_stock": price.in_stock,
        "product_url": pw_product_url(price.sku),
        "match": match,
        "match_question": question,
        "previous_title": previous_title,
        "tickable": priced,
        "default_pack_g": str(DEFAULT_PACK_G),
        "upfront_usd": _dec(upfront),
        "upfront_thb": _thb(upfront * rate) if upfront is not None and rate is not None else None,
        "neat_thb_per_g": _thb(per_g),
        "cost_per_bottle_thb": _range(card_costs),
        "price_age_days": (today - price.observed_on).days,
        "last_not_this_on": last_not_this_on,
    }
    return offer, card_costs


def _offer_sort_key(item: tuple[dict[str, Any], list[Decimal | None], PwPrice]) -> tuple:
    offer, _costs, price = item
    per_active = price.usd_per_active_g
    return (
        _MATCH_RANK[offer["match"]],
        per_active is None,
        per_active if per_active is not None else Decimal(0),
        offer["sku"],
    )


def _card_json(card: Mapping[str, Any], cost: Decimal | None = None) -> dict[str, Any]:
    fraction = card.get("neat_fraction")
    return {
        "formula_id": card.get("formula_id"),
        "version": card.get("version"),
        "name": card.get("name"),
        "material": card.get("material"),
        "neat_fraction": None if fraction is None else str(fraction),
        "cost_per_bottle_thb": _thb(cost),
    }


def _similar_lines(
    similar: Callable[[str], Mapping[str, Any]] | None, material: str
) -> list[dict[str, Any]]:
    if similar is None:
        return []
    try:
        result = similar(material)
    except LookupError:
        # The material has no character profile among owned stocks.
        return []
    lines = []
    for entry in list(result.get("similar") or [])[:2]:
        stocks = entry.get("stocks") or []
        lines.append(
            {
                "stock_id": stocks[0].get("stock_id") if stocks else None,
                "name": entry.get("identity_name"),
            }
        )
    return lines


def build_buy_list(
    needs: Mapping[str, Any],
    *,
    events: Iterable[Mapping[str, Any]] = (),
    today: date | None = None,
    prices: Mapping[str, PwPrice] | None = None,
    registry: Any = None,
    similar: Callable[[str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble the Buy page from card needs, PW list prices and Kenny's buy log."""

    if today is None:
        today = datetime.now(UTC).date()
    if prices is None:
        prices = pw_price_index()
    if registry is None:
        from engine.data_spine.loader import load_registry

        registry = load_registry()
    state = buy_state(events)

    need_rows = list(needs.get("needs") or [])
    names = {row["material_key"]: row["material"] for row in need_rows}
    need_counts = {row["material_key"]: len(row.get("cards") or []) for row in need_rows}

    def name_of(material_key: str) -> str:
        if material_key in names:
            return names[material_key]
        found = registry.get(material_key)
        return found.canonical_name if found is not None else material_key

    # --- rate, budget -------------------------------------------------------
    fx = None
    rate_banner: dict[str, Any] | None = {"reason": "missing"}
    rate: Decimal | None = None
    if state["fx_rate"] is not None:
        rate = Decimal(state["fx_rate"]["rate"])
        set_at = state["fx_rate"]["recorded_at"]
        set_on = _day(set_at)
        stale = (today - set_on).days > FX_STALE_AFTER_DAYS
        fx = {"rate": state["fx_rate"]["rate"], "set_at": set_at, "stale": stale}
        rate_banner = {"reason": "stale", "last_set_on": set_on.isoformat()} if stale else None
    budget = None
    if state["budget"] is not None:
        budget = {"amount_thb": state["budget"]["amount_thb"]}

    # --- orders ---------------------------------------------------------------
    on_the_way_keys: set[str] = set()
    returned: dict[str, tuple[str, dict[str, Any]]] = {}
    not_this_on: dict[tuple[str, str], str] = {}
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for order in state["orders"].values():
        material_key = order["material_key"]
        last_on = _day(order["recorded_at"])
        ordered_on = _day(order["ordered_at"]).isoformat() if order.get("ordered_at") else None
        order_state = order["state"]
        returned_state = None
        if order_state in _ON_THE_WAY_STATES:
            # The clock runs from the latest ORDERED or STILL_COMING event.
            days = (today - last_on).days
            if days < RETURN_AFTER_DAYS:
                on_the_way_keys.add(material_key)
                group = groups.setdefault(
                    (order["shop"], order["order_id"]),
                    {"shop": order["shop"], "order_id": order["order_id"], "starts": [],
                     "ordered": [], "lines": []},
                )
                group["starts"].append(days)
                group["ordered"].append(ordered_on or last_on.isoformat())
                # The offer as the price index has it, for the label check on arrival.
                offer_key = order["offer_key"]
                price = prices.get(offer_key[3:]) if offer_key.startswith("pw:") else None
                group["lines"].append(
                    {
                        "material_key": material_key,
                        "material": name_of(material_key),
                        "offer_key": offer_key,
                        "pack": order["pack"],
                        "shown_price": order.get("shown_price"),
                        "state": order_state,
                        "title": None if price is None else price.material_name,
                        "form": None if price is None else price.form,
                        "strength": None if price is None else _dec(price.strength),
                        "solvent": None if price is None else price.solvent,
                    }
                )
            else:
                returned_state = "not_arrived"
        elif order_state in _RETURNED_STATES:
            returned_state = order_state
            if order_state == "NOT_THIS":
                key = (material_key, order["offer_key"])
                day_text = last_on.isoformat()
                not_this_on[key] = max(not_this_on.get(key, day_text), day_text)
        if returned_state is not None:
            previous = returned.get(material_key)
            if previous is None or order["recorded_at"] >= previous[0]:
                returned[material_key] = (
                    order["recorded_at"],
                    {
                        "order_id": order["order_id"],
                        "shop": order["shop"],
                        "ordered_on": ordered_on,
                        "state": returned_state,
                    },
                )

    on_the_way = []
    for group in groups.values():
        days = min(group["starts"])
        on_the_way.append(
            {
                "shop": group["shop"],
                "order_id": group["order_id"],
                "ordered_on": min(group["ordered"]),
                "days": days,
                "nudge": days >= NUDGE_AFTER_DAYS,
                "nudge_text": f"{group['shop']} parcel still on the way?",
                "lines": sorted(group["lines"], key=lambda line: line["material"].casefold()),
            }
        )
    on_the_way.sort(key=lambda group: (group["ordered_on"], group["shop"], group["order_id"]))

    # --- decisions --------------------------------------------------------------
    skipped: set[str] = set()
    skip = []
    tiers: dict[str, Any] = {"1": [], "2": [], "3": {"note": TIER_3_NOTE}}
    pick_tiers: dict[str, int] = {}
    for material_key, decision in state["decisions"].items():
        common = {
            "material_key": material_key,
            "material": name_of(material_key),
        }
        if decision["kind"] == "skip":
            skipped.add(material_key)
            skip.append(
                {
                    **common,
                    "reason": decision["reason"],
                    "decided_by": decision["decided_by"],
                    "decided_at": decision["decided_at"],
                    "source": decision["source"],
                    "need_count": need_counts.get(material_key, 0),
                }
            )
            continue
        pick_tiers[material_key] = decision["tier"]
        tiers[str(decision["tier"])].append(
            {
                **common,
                "tier": decision["tier"],
                "offer_key": decision.get("offer_key"),
                "dose": decision["dose"],
                "reason": decision["reason"],
                "decided_by": decision["decided_by"],
                "reviewed_on": decision["decided_at"],
                "source": decision["source"],
                "price": decision.get("price"),
                "need_count": need_counts.get(material_key, 0),
            }
        )
    skip.sort(key=lambda row: (row["material"].casefold(), row["material_key"]))
    for tier in ("1", "2"):
        tiers[tier].sort(key=lambda row: (row["material"].casefold(), row["material_key"]))

    # --- Buy first ----------------------------------------------------------------
    buy_first = []
    for need in need_rows:
        material_key = need["material_key"]
        if material_key in skipped or material_key in on_the_way_keys:
            continue
        material = need["material"]
        cards = list(need.get("cards") or [])
        record = registry.get(material) or registry.get(material_key)
        built = []
        for sku in _skus_for(record) if record is not None else []:
            price = prices.get(sku)
            if price is None:
                continue
            item = _offer(
                price,
                material_key=material_key,
                material=material,
                answer=state["matches"].get((material_key, f"pw:{sku}")),
                rate=rate,
                cards=cards,
                today=today,
                last_not_this_on=not_this_on.get((material_key, f"pw:{sku}")),
            )
            if item is not None:
                built.append((*item, price))
        built.sort(key=_offer_sort_key)
        chosen_costs: list[Decimal | None] = [None] * len(cards)
        row_range = None
        for offer, costs, _price in built:
            if offer["tickable"] and offer["cost_per_bottle_thb"] is not None:
                chosen_costs, row_range = costs, offer["cost_per_bottle_thb"]
                break
        back = returned.get(material_key)
        buy_first.append(
            {
                "material_key": material_key,
                "material": material,
                "need_count": len(cards),
                "cards": [_card_json(card, cost) for card, cost in zip(cards, chosen_costs)],
                "similar": _similar_lines(similar, material),
                "pick_tier": pick_tiers.get(material_key),
                "returned_from_order": back[1] if back is not None else None,
                "offers": [offer for offer, _costs, _price in built],
                "cost_per_bottle_thb": row_range,
            }
        )
    buy_first.sort(key=lambda row: (-row["need_count"], row["material"].casefold(), row["material"]))

    check_stock = [
        {
            "material_key": row["material_key"],
            "material": row["material"],
            "cards": [
                {key: str(value) if isinstance(value, Decimal) else value for key, value in card.items()}
                for card in row.get("cards") or []
            ],
            "code": row.get("code"),
            "reason": row.get("reason"),
        }
        for row in needs.get("disagreements") or []
    ]

    return {
        "schema_version": BUY_LIST_SCHEMA,
        "generated_on": today.isoformat(),
        "price_header": _price_header(
            (
                date.fromisoformat(offer["observed_on"])
                for row in buy_first
                for offer in row["offers"]
            ),
            prices,
        ),
        "fx": fx,
        "rate_banner": rate_banner,
        "budget": budget,
        "buy_first": buy_first,
        "check_stock": check_stock,
        "tiers": tiers,
        "skip": skip,
        "on_the_way": on_the_way,
        "unreadable": list(needs.get("unreadable") or []),
        "inventory_modified": False,
        "formula_modified": False,
        "compounding_authority": False,
    }


__all__ = [
    "BUY_LIST_SCHEMA",
    "MISLABELS",
    "build_buy_list",
    "day_month_label",
]
