"""Prices Kenny paid for his stocks, typed on the Lab app's Stock page.

No supplier price data exists in the project, so every price here is one Kenny
entered himself.  Each entry is one line of an append-only, hash-chained JSONL
log beside the other personal stock records in ``data/user/``; the last entry
per id wins.  Besides stocks (keyed by ``stock_id``) the log holds two fixed
cost items: ``ethanol`` (per mL) and ``packaging_per_bottle`` (bottle, cap, box
and label, per bottle).

Prices are cost bookkeeping only.  They never feed a formula, the mixer or any
release gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

PRICE_LOG_NAME = "user_stock_price_events.jsonl"
PRICE_PATH_ENV = "PERFUME_STOCK_PRICE_PATH"
EVENT_SCHEMA = "stock-price-event-v1"

ETHANOL_ID = "ethanol"
PACKAGING_ID = "packaging_per_bottle"
# The unit each fixed cost item is priced in.
COST_ITEM_UNITS = {ETHANOL_ID: "mL", PACKAGING_ID: "bottle"}
STOCK_UNITS = ("g", "mL")
DEFAULT_CURRENCY = "THB"
# Shown price per unit when it comes from "paid X for Y": exact enough for
# display; the bench sheet recomputes from the pack itself.
_PACK_PRICE_PLACES = Decimal("0.000001")
_MAX_LOG_BYTES = 5_000_000

_WRITE_LOCK = threading.Lock()


class StockPriceError(ValueError):
    """An invalid price entry."""

    code = "INVALID_STOCK_PRICE"


class StockPriceLogCorruptError(StockPriceError):
    """The price log can't be read; the message is plain enough to show Kenny."""

    code = "STOCK_PRICE_LOG_CORRUPT"


def price_log_path(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    override = os.environ.get(PRICE_PATH_ENV)
    if override:
        return Path(override).resolve()
    # Beside the completion log in data/user/, as the basket log is.
    from engine.inventory_completions import completion_log_path

    return completion_log_path().with_name(PRICE_LOG_NAME)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _event_hash(core: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(core).encode("utf-8")).hexdigest()


def _positive_decimal(value: object, what: str) -> Decimal:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError) as error:
        raise StockPriceError(f"{what} must be a number") from error
    if not parsed.is_finite() or parsed <= 0:
        raise StockPriceError(f"{what} must be more than 0")
    if parsed >= Decimal("1e12"):
        raise StockPriceError(f"{what} is too large")
    return parsed


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def normalize_price_entry(
    *,
    stock_id: object,
    per_unit: object,
    price_decimal: object = None,
    pack_price: object = None,
    pack_size: object = None,
    currency: object = DEFAULT_CURRENCY,
    note: object = "",
    clear: bool = False,
) -> dict[str, Any]:
    """Validate one entry; return its stored fields (all decimals as strings)."""

    key = re.sub(r"\s+", " ", str(stock_id or "").strip())
    if not key or len(key) > 255:
        raise StockPriceError("stock_id is required (at most 255 characters)")
    unit = str(per_unit or "").strip()
    allowed = (COST_ITEM_UNITS[key],) if key in COST_ITEM_UNITS else STOCK_UNITS
    if unit not in allowed:
        raise StockPriceError(f"per_unit for {key} must be one of: {', '.join(allowed)}")
    money = str(currency or DEFAULT_CURRENCY).strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", money):
        raise StockPriceError("currency must be a three-letter code such as THB")
    note_text = re.sub(r"\s+", " ", str(note or "").strip())
    if len(note_text) > 500:
        raise StockPriceError("note exceeds 500 characters")
    entry: dict[str, Any] = {
        "stock_id": key,
        "per_unit": unit,
        "currency": money,
        "price_decimal": None,
        "pack_price": None,
        "pack_size": None,
        "note": note_text,
        "cleared": bool(clear),
    }
    if clear:
        if not (_blank(price_decimal) and _blank(pack_price) and _blank(pack_size)):
            raise StockPriceError("a cleared price carries no amounts")
        return entry
    has_pack = not (_blank(pack_price) and _blank(pack_size))
    if has_pack:
        if _blank(pack_price) or _blank(pack_size):
            raise StockPriceError("give both what you paid and how much you got")
        if not _blank(price_decimal):
            raise StockPriceError("give a price per unit or a pack price, not both")
        paid = _positive_decimal(pack_price, "price paid")
        size = _positive_decimal(pack_size, "amount bought")
        entry["pack_price"] = _decimal_text(paid)
        entry["pack_size"] = _decimal_text(size)
        entry["price_decimal"] = _decimal_text(
            (paid / size).quantize(_PACK_PRICE_PLACES, rounding=ROUND_HALF_UP)
        )
        if Decimal(entry["price_decimal"]) == 0:
            raise StockPriceError("that price per unit rounds to 0")
    else:
        if _blank(price_decimal):
            raise StockPriceError("give a price per unit or what you paid for how much")
        entry["price_decimal"] = _decimal_text(_positive_decimal(price_decimal, "price"))
    return entry


def _damaged(line_number: int) -> StockPriceLogCorruptError:
    return StockPriceLogCorruptError(
        f"The price log has a damaged line (line {line_number}); "
        "your prices can't be read until it is repaired."
    )


def load_price_events(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    """Read and verify the hash chain of Kenny's price entries."""

    source = price_log_path(path)
    if not source.exists():
        return ()
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as error:
        raise StockPriceLogCorruptError(
            "The price log can't be read; your prices can't be read until it is repaired."
        ) from error
    if len(content.encode("utf-8")) > _MAX_LOG_BYTES:
        raise StockPriceLogCorruptError("The price log is larger than the 5 MB limit.")
    events: list[dict[str, Any]] = []
    previous_hash = ""
    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise _damaged(line_number) from error
        if not isinstance(raw, dict) or raw.get("schema") != EVENT_SCHEMA:
            raise _damaged(line_number)
        core = {key: value for key, value in raw.items() if key != "event_sha256"}
        if raw.get("previous_hash") != previous_hash or raw.get("event_sha256") != _event_hash(
            core
        ):
            raise _damaged(line_number)
        try:
            stored = normalize_price_entry(
                stock_id=raw.get("stock_id"),
                per_unit=raw.get("per_unit"),
                price_decimal=None if raw.get("pack_price") else raw.get("price_decimal"),
                pack_price=raw.get("pack_price"),
                pack_size=raw.get("pack_size"),
                currency=raw.get("currency"),
                note=raw.get("note"),
                clear=raw.get("cleared") is True,
            )
        except StockPriceError as error:
            raise _damaged(line_number) from error
        if any(raw.get(field) != value for field, value in stored.items()):
            raise _damaged(line_number)
        previous_hash = str(raw["event_sha256"])
        events.append(raw)
    return tuple(events)


def _public(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: event[key]
        for key in (
            "stock_id",
            "price_decimal",
            "per_unit",
            "currency",
            "pack_price",
            "pack_size",
            "note",
            "recorded_at",
        )
    }


def latest_prices(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """The current price per id; a cleared id is absent."""

    latest: dict[str, dict[str, Any]] = {}
    for event in load_price_events(path):
        if event["cleared"]:
            latest.pop(str(event["stock_id"]), None)
        else:
            latest[str(event["stock_id"])] = _public(event)
    return latest


def record_stock_price(*, path: Path | None = None, **fields: Any) -> dict[str, Any]:
    """Append one validated price entry and return it as stored."""

    entry = normalize_price_entry(**fields)
    source = price_log_path(path)
    with _WRITE_LOCK:
        events = load_price_events(source)
        core: dict[str, Any] = {
            "schema": EVENT_SCHEMA,
            **entry,
            "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "previous_hash": str(events[-1]["event_sha256"]) if events else "",
        }
        event = {**core, "event_sha256": _event_hash(core)}
        source.parent.mkdir(parents=True, exist_ok=True)
        with source.open("a", encoding="utf-8") as handle:
            handle.write(_canonical_json(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    return event


__all__ = [
    "COST_ITEM_UNITS",
    "DEFAULT_CURRENCY",
    "ETHANOL_ID",
    "PACKAGING_ID",
    "PRICE_LOG_NAME",
    "PRICE_PATH_ENV",
    "STOCK_UNITS",
    "StockPriceError",
    "StockPriceLogCorruptError",
    "latest_prices",
    "load_price_events",
    "normalize_price_entry",
    "price_log_path",
    "record_stock_price",
]
