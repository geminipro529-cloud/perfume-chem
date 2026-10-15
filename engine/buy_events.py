"""Kenny's buying decisions, made on the Lab app's Buy page.

Each decision is one line of an append-only, hash-chained JSONL log in
``data/user/``, built like the stock price log on the Stock page: an edited,
removed or reordered line breaks the chain and the log refuses to load.  The
log holds six kinds of event: the USD/THB rate Kenny uses (``fx_rate``), his
spending budget (``budget``), whether a shop offer is the material he means
(``match``), what he chose to buy or not buy (``pick``/``skip``) and how an
order went (``order``).

``buy_state`` folds the events into the current state; ``parse_labpicks`` turns
a pasted ``LABPICKS/1`` block into ``pick``/``skip`` entries without writing
anything.  Nothing here touches stock, prices or formulas.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from engine.user_records import USER_RECORDS_DIR

BUY_EVENTS_LOG_NAME = "user_buy_events.jsonl"
BUY_EVENTS_PATH_ENV = "PERFUME_BUY_EVENTS_PATH"
EVENT_SCHEMA = "buy-event-v1"
LABPICKS_MARKER = "LABPICKS/1"

FX_MIN = Decimal("25")
FX_MAX = Decimal("45")
FX_PAIR = "USD/THB"
BUDGET_MAX_THB = Decimal("1000000")

MATCH_ANSWERS = ("SAME", "DIFFERENT")
PICK_TIERS = (1, 2)
PRICE_CURRENCIES = ("THB", "USD")
ORDER_SHOPS = ("PW", "AM", "MSR", "OTHER")
ORDER_STATES = (
    "ORDERED",
    "STILL_COMING",
    "ARRIVED",
    "DIDNT_COME",
    "NOT_THIS",
    "ALREADY_HAVE",
)

_MAX_LOG_BYTES = 5_000_000
_MAX_LABPICKS_BYTES = 200_000
_MAX_LABPICKS_ENTRIES = 100
_MAX_AMOUNT = Decimal("1e12")
_ENVELOPE_FIELDS = (
    "schema_version",
    "event_id",
    "recorded_at",
    "prev_event_sha256",
    "event_sha256",
)
_EVENT_ID = re.compile(r"[0-9a-f]{32}")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

_WRITE_LOCK = threading.Lock()


class BuyEventError(ValueError):
    """An invalid buy entry; ``code`` says which rule it broke."""

    code = "BUY_EVENT_INVALID"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class BuyEventLogCorruptError(BuyEventError):
    """The buy log can't be read; the message is plain enough to show Kenny."""

    code = "BUY_EVENT_LOG_CORRUPT"


def buy_events_path(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    override = os.environ.get(BUY_EVENTS_PATH_ENV)
    if override:
        return Path(override).resolve()
    # Beside the other personal stock records in data/user/ (gitignored).
    return (USER_RECORDS_DIR / BUY_EVENTS_LOG_NAME).resolve()


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _event_hash(core: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(core).encode("utf-8")).hexdigest()


# --- validation -------------------------------------------------------------


def _check_keys(
    fields: Mapping[Any, Any],
    what: str,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> None:
    required = tuple(required)
    allowed = set(required) | set(optional)
    unknown = sorted(str(key) for key in fields if key not in allowed)
    if unknown:
        raise BuyEventError(
            f"{what}: unknown field {', '.join(unknown)}", code="BUY_EVENT_UNKNOWN_FIELD"
        )
    missing = [key for key in required if fields.get(key) is None]
    if missing:
        raise BuyEventError(f"{what}: missing {', '.join(missing)}")


def _text(value: object, what: str, cap: int) -> str:
    if not isinstance(value, str):
        raise BuyEventError(f"{what} must be text")
    if "\n" in value or "\r" in value:
        raise BuyEventError(f"{what} must be a single line")
    text = value.strip()
    if not text:
        raise BuyEventError(f"{what} is required")
    if len(text) > cap:
        raise BuyEventError(f"{what} exceeds {cap} characters")
    return text


def _choice(value: object, what: str, allowed: Sequence[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise BuyEventError(f"{what} must be one of: {', '.join(allowed)}")
    return value


def _decimal(value: object, what: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise BuyEventError(f"{what} must be a number")
    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation as error:
        raise BuyEventError(f"{what} must be a number") from error
    if not parsed.is_finite():
        raise BuyEventError(f"{what} must be a number")
    return parsed


def _positive_amount(value: object, what: str, ceiling: Decimal | None = None) -> Decimal:
    parsed = _decimal(value, what)
    if parsed <= 0:
        raise BuyEventError(f"{what} must be more than 0")
    if parsed >= _MAX_AMOUNT or (ceiling is not None and parsed > ceiling):
        raise BuyEventError(f"{what} is too large")
    return parsed


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _iso_date(value: object, what: str) -> str:
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise BuyEventError(f"{what} must be a date written YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise BuyEventError(f"{what} is not a real date") from error
    return value


def _price(value: object, what: str, *, with_pack: bool) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BuyEventError(f"{what} must be an object")
    required = ("amount", "currency", "pack", "observed_on")
    if not with_pack:
        required = ("amount", "currency", "observed_on")
    _check_keys(value, what, required)
    price: dict[str, Any] = {
        "amount": _decimal_text(_positive_amount(value["amount"], f"{what}.amount")),
        "currency": _choice(value["currency"], f"{what}.currency", PRICE_CURRENCIES),
    }
    if with_pack:
        price["pack"] = _text(value["pack"], f"{what}.pack", 40)
    price["observed_on"] = _iso_date(value["observed_on"], f"{what}.observed_on")
    return price


def _fx_rate(fields: Mapping[str, Any]) -> dict[str, Any]:
    _check_keys(fields, "fx_rate", ("rate",), ("pair",))
    if fields.get("pair") is not None and fields["pair"] != FX_PAIR:
        raise BuyEventError(f"fx_rate pair must be {FX_PAIR}")
    rate = _decimal(fields["rate"], "rate")
    if not FX_MIN <= rate <= FX_MAX:
        raise BuyEventError(
            f"the USD/THB rate must be between {FX_MIN} and {FX_MAX}",
            code="BUY_FX_RATE_OUT_OF_RANGE",
        )
    return {"rate": _decimal_text(rate), "pair": FX_PAIR}


def _budget(fields: Mapping[str, Any]) -> dict[str, Any]:
    _check_keys(fields, "budget", (), ("amount_thb", "clear"))
    clear = fields.get("clear")
    amount = fields.get("amount_thb")
    if clear is not None:
        if clear is not True or amount is not None:
            raise BuyEventError("budget: give amount_thb, or clear: true on its own")
        return {"clear": True}
    if amount is None:
        raise BuyEventError("budget: give amount_thb, or clear: true on its own")
    return {"amount_thb": _decimal_text(_positive_amount(amount, "amount_thb", BUDGET_MAX_THB))}


def _match(fields: Mapping[str, Any]) -> dict[str, Any]:
    _check_keys(fields, "match", ("material_key", "offer_key", "answer", "title_at_confirm"))
    return {
        "material_key": _text(fields["material_key"], "material_key", 200),
        "offer_key": _text(fields["offer_key"], "offer_key", 80),
        "answer": _choice(fields["answer"], "answer", MATCH_ANSWERS),
        "title_at_confirm": _text(fields["title_at_confirm"], "title_at_confirm", 200),
    }


def _decision_common(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "material_key": _text(fields["material_key"], "material_key", 200),
        "reason": _text(fields["reason"], "reason", 200),
        "decided_by": _text(fields["decided_by"], "decided_by", 60),
        "decided_at": _iso_date(fields["decided_at"], "decided_at"),
        "source": _text(fields["source"], "source", 300),
    }


def _pick(fields: Mapping[str, Any]) -> dict[str, Any]:
    _check_keys(
        fields,
        "pick",
        ("material_key", "tier", "dose", "reason", "decided_by", "decided_at", "source"),
        ("offer_key", "price"),
    )
    tier = fields["tier"]
    if type(tier) is not int or tier not in PICK_TIERS:
        raise BuyEventError("tier must be 1 or 2")
    entry = _decision_common(fields)
    entry["tier"] = tier
    entry["dose"] = _text(fields["dose"], "dose", 40)
    if fields.get("offer_key") is not None:
        entry["offer_key"] = _text(fields["offer_key"], "offer_key", 80)
    if fields.get("price") is not None:
        entry["price"] = _price(fields["price"], "price", with_pack=True)
    return entry


def _skip(fields: Mapping[str, Any]) -> dict[str, Any]:
    _check_keys(fields, "skip", ("material_key", "reason", "decided_by", "decided_at", "source"))
    return _decision_common(fields)


def _order(fields: Mapping[str, Any]) -> dict[str, Any]:
    _check_keys(
        fields,
        "order",
        ("order_id", "shop", "material_key", "offer_key", "pack", "state"),
        ("shown_price",),
    )
    entry: dict[str, Any] = {
        "order_id": _text(fields["order_id"], "order_id", 64),
        "shop": _choice(fields["shop"], "shop", ORDER_SHOPS),
        "material_key": _text(fields["material_key"], "material_key", 200),
        "offer_key": _text(fields["offer_key"], "offer_key", 80),
        "pack": _text(fields["pack"], "pack", 40),
        "state": _choice(fields["state"], "state", ORDER_STATES),
    }
    if fields.get("shown_price") is not None:
        entry["shown_price"] = _price(fields["shown_price"], "shown_price", with_pack=False)
    elif entry["state"] == "ORDERED":
        raise BuyEventError("an ORDERED order needs its shown_price")
    return entry


_KINDS: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
    "fx_rate": _fx_rate,
    "budget": _budget,
    "match": _match,
    "pick": _pick,
    "skip": _skip,
    "order": _order,
}


def normalize_buy_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one entry; return its stored fields (decimals as strings)."""

    if not isinstance(entry, Mapping):
        raise BuyEventError("a buy entry must be an object")
    kind = entry.get("kind")
    if not isinstance(kind, str) or kind not in _KINDS:
        raise BuyEventError(
            f"kind must be one of: {', '.join(_KINDS)}", code="BUY_EVENT_UNKNOWN_KIND"
        )
    fields = {key: value for key, value in entry.items() if key != "kind"}
    return {"kind": kind, **_KINDS[kind](fields)}


# --- the log ----------------------------------------------------------------


def _damaged(line_number: int) -> BuyEventLogCorruptError:
    return BuyEventLogCorruptError(
        f"The buy log has a damaged line (line {line_number}); "
        "your buying decisions can't be read until it is repaired."
    )


def load_buy_events(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    """Read and verify the hash chain of Kenny's buy events."""

    source = buy_events_path(path)
    if not source.exists():
        return ()
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as error:
        raise BuyEventLogCorruptError(
            "The buy log can't be read; your buying decisions can't be read until it is repaired."
        ) from error
    if len(content.encode("utf-8")) > _MAX_LOG_BYTES:
        raise BuyEventLogCorruptError("The buy log is larger than the 5 MB limit.")
    events: list[dict[str, Any]] = []
    previous_hash = ""
    # Only "\n" ends a record: JSON escapes it inside strings, but writes U+2028,
    # U+2029 and U+0085 raw, and str.splitlines() would break a record on those.
    for line_number, line in enumerate(content.split("\n"), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise _damaged(line_number) from error
        if not isinstance(raw, dict) or raw.get("schema_version") != EVENT_SCHEMA:
            raise _damaged(line_number)
        core = {key: value for key, value in raw.items() if key != "event_sha256"}
        if raw.get("prev_event_sha256") != previous_hash or raw.get("event_sha256") != _event_hash(
            core
        ):
            raise _damaged(line_number)
        if not isinstance(raw.get("event_id"), str) or not _EVENT_ID.fullmatch(raw["event_id"]):
            raise _damaged(line_number)
        if not isinstance(raw.get("recorded_at"), str):
            raise _damaged(line_number)
        content_fields = {key: value for key, value in raw.items() if key not in _ENVELOPE_FIELDS}
        try:
            stored = normalize_buy_entry(content_fields)
        except BuyEventError as error:
            raise _damaged(line_number) from error
        if stored != content_fields:
            raise _damaged(line_number)
        previous_hash = str(raw["event_sha256"])
        events.append(raw)
    return tuple(events)


def _recorded_at(now: datetime | None) -> str:
    moment = datetime.now(UTC) if now is None else now
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def record_buy_events(
    entries: Sequence[Mapping[str, Any]],
    *,
    path: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], ...]:
    """Validate every entry, then append them all (or none) and return them as stored."""

    if isinstance(entries, Mapping) or not isinstance(entries, Sequence):
        raise BuyEventError("give a list of buy entries")
    if not entries:
        raise BuyEventError("there is nothing to record")
    normalized = [normalize_buy_entry(entry) for entry in entries]
    recorded_at = _recorded_at(now)
    source = buy_events_path(path)
    with _WRITE_LOCK:
        existing = load_buy_events(source)
        previous_hash = str(existing[-1]["event_sha256"]) if existing else ""
        stored: list[dict[str, Any]] = []
        for entry in normalized:
            core: dict[str, Any] = {
                "schema_version": EVENT_SCHEMA,
                "event_id": uuid.uuid4().hex,
                **entry,
                "recorded_at": recorded_at,
                "prev_event_sha256": previous_hash,
            }
            event = {**core, "event_sha256": _event_hash(core)}
            stored.append(event)
            previous_hash = event["event_sha256"]
        text = "".join(_canonical_json(event) + "\n" for event in stored)
        current_size = source.stat().st_size if source.exists() else 0
        if current_size + len(text.encode("utf-8")) > _MAX_LOG_BYTES:
            raise BuyEventError(
                "The buy log would grow past its 5 MB limit; nothing was saved.",
                code="BUY_EVENT_LOG_FULL",
            )
        source.parent.mkdir(parents=True, exist_ok=True)
        with source.open("a", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    return tuple(stored)


# --- current state ----------------------------------------------------------


def _without_envelope(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in event.items() if key not in _ENVELOPE_FIELDS and key != "kind"
    }


def buy_state(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Fold buy events, oldest first, into the current state; the latest wins.

    ``matches`` is keyed by ``(material_key, offer_key)``, ``decisions`` by
    ``material_key`` and ``orders`` by ``(order_id, material_key)``; use
    ``buy_state_to_json`` for a form with string keys.
    """

    fx_rate: dict[str, Any] | None = None
    budget: dict[str, Any] | None = None
    matches: dict[tuple[str, str], dict[str, Any]] = {}
    decisions: dict[str, dict[str, Any]] = {}
    orders: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        kind = event.get("kind")
        recorded_at = event.get("recorded_at")
        if kind == "fx_rate":
            fx_rate = {"rate": event["rate"], "pair": event["pair"], "recorded_at": recorded_at}
        elif kind == "budget":
            budget = (
                None
                if event.get("clear") is True
                else {"amount_thb": event["amount_thb"], "recorded_at": recorded_at}
            )
        elif kind == "match":
            matches[(event["material_key"], event["offer_key"])] = {
                "material_key": event["material_key"],
                "offer_key": event["offer_key"],
                "answer": event["answer"],
                "title_at_confirm": event["title_at_confirm"],
                "recorded_at": recorded_at,
            }
        elif kind in ("pick", "skip"):
            decisions[event["material_key"]] = {
                "kind": kind,
                **_without_envelope(event),
                "recorded_at": recorded_at,
            }
        elif kind == "order":
            key = (event["order_id"], event["material_key"])
            before = orders.get(key, {})
            orders[key] = {
                "order_id": event["order_id"],
                "material_key": event["material_key"],
                "state": event["state"],
                "shop": event["shop"],
                "offer_key": event["offer_key"],
                "pack": event["pack"],
                # A later state change need not repeat the price shown at ordering.
                "shown_price": event.get("shown_price", before.get("shown_price")),
                "ordered_at": (
                    recorded_at if event["state"] == "ORDERED" else before.get("ordered_at")
                ),
                "recorded_at": recorded_at,
            }
    return {
        "fx_rate": fx_rate,
        "budget": budget,
        "matches": matches,
        "decisions": decisions,
        "orders": orders,
    }


def state_key(*parts: str) -> str:
    """The stable string form of a tuple key: its compact JSON array."""

    return json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"))


def buy_state_to_json(state: Mapping[str, Any]) -> dict[str, Any]:
    """``buy_state`` with tuple keys written as ``state_key`` strings."""

    return {
        **state,
        "matches": {state_key(*key): value for key, value in state["matches"].items()},
        "orders": {state_key(*key): value for key, value in state["orders"].items()},
    }


# --- pasted pick blocks ------------------------------------------------------


def _labpicks_error(message: str) -> BuyEventError:
    return BuyEventError(f"LABPICKS: {message}", code="BUY_LABPICKS_INVALID")


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not a number")


def parse_labpicks(text: str) -> list[dict[str, Any]]:
    """Turn a pasted ``LABPICKS/1`` block into ``pick``/``skip`` entries; writes nothing."""

    if not isinstance(text, str):
        raise _labpicks_error("the pasted block must be text")
    if len(text.encode("utf-8")) > _MAX_LABPICKS_BYTES:
        raise _labpicks_error("the pasted block is larger than 200 KB")
    lines = text.splitlines()
    first = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first is None or lines[first].strip() != LABPICKS_MARKER:
        raise _labpicks_error(f"the first line must be {LABPICKS_MARKER}")
    body = "\n".join(lines[first + 1 :])
    try:
        block = json.loads(body, parse_float=Decimal, parse_constant=_reject_constant)
    except ValueError as error:
        raise _labpicks_error(
            f"the block after the first line is not valid JSON ({error})"
        ) from error
    if not isinstance(block, dict):
        raise _labpicks_error("the block after the first line must be one JSON object")
    try:
        _check_keys(block, "block", ("source", "reviewed_on", "decided_by"), ("picks", "skips"))
        source = _text(block["source"], "source", 300)
        decided_by = _text(block["decided_by"], "decided_by", 60)
        reviewed_on = _iso_date(block["reviewed_on"], "reviewed_on")
    except BuyEventError as error:
        raise _labpicks_error(str(error)) from error
    sections: dict[str, list[Any]] = {}
    for name in ("picks", "skips"):
        items = block.get(name, [])
        if not isinstance(items, list):
            raise _labpicks_error(f"{name} must be a list")
        sections[name] = items
    count = len(sections["picks"]) + len(sections["skips"])
    if count == 0:
        raise _labpicks_error("the block has no picks or skips")
    if count > _MAX_LABPICKS_ENTRIES:
        raise _labpicks_error(
            f"the block has {count} picks and skips; at most {_MAX_LABPICKS_ENTRIES} are allowed"
        )
    allowed = {
        "picks": ("material_key", "tier", "offer_key", "dose", "reason", "price"),
        "skips": ("material_key", "reason"),
    }
    entries: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for name, kind in (("picks", "pick"), ("skips", "skip")):
        for index, item in enumerate(sections[name]):
            label = f"{name}[{index}]"
            if isinstance(item, dict) and isinstance(item.get("material_key"), str):
                label += f" ({item['material_key'].strip()})"
            try:
                if not isinstance(item, dict):
                    raise BuyEventError("must be an object")
                _check_keys(item, "item", (), allowed[name])
                entry = normalize_buy_entry(
                    {
                        "kind": kind,
                        **item,
                        "decided_by": decided_by,
                        "decided_at": reviewed_on,
                        "source": source,
                    }
                )
            except BuyEventError as error:
                raise _labpicks_error(f"{label}: {error}") from error
            material = entry["material_key"]
            if material in seen:
                raise _labpicks_error(f"{label}: {material} is already listed at {seen[material]}")
            seen[material] = label
            entries.append(entry)
    return entries


__all__ = [
    "BUDGET_MAX_THB",
    "BUY_EVENTS_LOG_NAME",
    "BUY_EVENTS_PATH_ENV",
    "EVENT_SCHEMA",
    "FX_MAX",
    "FX_MIN",
    "FX_PAIR",
    "LABPICKS_MARKER",
    "MATCH_ANSWERS",
    "ORDER_SHOPS",
    "ORDER_STATES",
    "PICK_TIERS",
    "PRICE_CURRENCIES",
    "BuyEventError",
    "BuyEventLogCorruptError",
    "buy_events_path",
    "buy_state",
    "buy_state_to_json",
    "load_buy_events",
    "normalize_buy_entry",
    "parse_labpicks",
    "record_buy_events",
    "state_key",
]
