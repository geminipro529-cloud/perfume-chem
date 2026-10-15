"""How much is left of a stock, and where Kenny buys it, typed in the Lab app.

The project has no record of how much of each bottle is left: inventory.txt and the
stock workbook list what is owned, not how much. "What can I make" asks for an amount
only where a saved formula needs that stock, and keeps it here: one line per entry
in an append-only, hash-chained JSONL log beside the other personal stock records in
``data/user/``; the last entry per stock wins.

An amount is what Kenny read off the bottle, in mL for a liquid or g for a solid,
with an optional supplier name for the shopping list. It is bookkeeping only: it
never feeds a formula, the mixer, the stock list the checks use or any release gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ON_HAND_LOG_NAME = "user_stock_on_hand_events.jsonl"
ON_HAND_PATH_ENV = "PERFUME_STOCK_ON_HAND_PATH"
EVENT_SCHEMA = "stock-on-hand-event-v1"
ON_HAND_UNITS = ("mL", "g")
_MAX_LOG_BYTES = 5_000_000

_WRITE_LOCK = threading.Lock()


class StockOnHandError(ValueError):
    """An invalid entry."""

    code = "INVALID_STOCK_ON_HAND"


class StockOnHandLogCorruptError(StockOnHandError):
    """The log can't be read; the message is plain enough to show Kenny."""

    code = "STOCK_ON_HAND_LOG_CORRUPT"


def on_hand_log_path(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    override = os.environ.get(ON_HAND_PATH_ENV)
    if override:
        return Path(override).resolve()
    # Beside the completion log in data/user/, as the price and basket logs are.
    from engine.inventory_completions import completion_log_path

    return completion_log_path().with_name(ON_HAND_LOG_NAME)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _event_hash(core: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(core).encode("utf-8")).hexdigest()


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _text(value: object, what: str, maximum: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) > maximum:
        raise StockOnHandError(f"{what} exceeds {maximum} characters")
    return text


def normalize_on_hand_entry(
    *,
    stock_id: object,
    amount_decimal: object = None,
    unit: object = None,
    supplier: object = "",
    note: object = "",
    clear: bool = False,
) -> dict[str, Any]:
    """Validate one entry; return its stored fields (the amount as decimal text)."""

    key = re.sub(r"\s+", " ", str(stock_id or "").strip())
    if not key or len(key) > 255:
        raise StockOnHandError("stock_id is required (at most 255 characters)")
    entry: dict[str, Any] = {
        "stock_id": key,
        "amount_decimal": None,
        "unit": None,
        "supplier": _text(supplier, "supplier", 120),
        "note": _text(note, "note", 500),
        "cleared": bool(clear),
    }
    if clear:
        if not (_blank(amount_decimal) and _blank(unit)):
            raise StockOnHandError("a cleared entry carries no amount")
        return entry
    unit_text = str(unit or "").strip()
    if unit_text not in ON_HAND_UNITS:
        raise StockOnHandError(f"unit must be one of: {', '.join(ON_HAND_UNITS)}")
    try:
        amount = Decimal(str(amount_decimal).strip())
    except (InvalidOperation, TypeError, ValueError) as error:
        raise StockOnHandError("how much is left must be a number") from error
    # 0 is a real answer: the bottle is empty.
    if not amount.is_finite() or amount < 0:
        raise StockOnHandError("how much is left must be 0 or more")
    if amount >= Decimal("1e9"):
        raise StockOnHandError("how much is left is too large")
    entry["amount_decimal"] = format(amount.normalize(), "f") if amount else "0"
    entry["unit"] = unit_text
    return entry


def _damaged(line_number: int) -> StockOnHandLogCorruptError:
    return StockOnHandLogCorruptError(
        f"The how-much-is-left log has a damaged line (line {line_number}); "
        "your amounts can't be read until it is repaired."
    )


def load_on_hand_events(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    """Read and verify the hash chain of Kenny's entries."""

    source = on_hand_log_path(path)
    if not source.exists():
        return ()
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as error:
        raise StockOnHandLogCorruptError(
            "The how-much-is-left log can't be read; your amounts can't be read until it is repaired."
        ) from error
    if len(content.encode("utf-8")) > _MAX_LOG_BYTES:
        raise StockOnHandLogCorruptError("The how-much-is-left log is larger than the 5 MB limit.")
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
        if raw.get("previous_hash") != previous_hash or raw.get("event_sha256") != _event_hash(core):
            raise _damaged(line_number)
        try:
            stored = normalize_on_hand_entry(
                stock_id=raw.get("stock_id"),
                amount_decimal=raw.get("amount_decimal"),
                unit=raw.get("unit"),
                supplier=raw.get("supplier"),
                note=raw.get("note"),
                clear=raw.get("cleared") is True,
            )
        except StockOnHandError as error:
            raise _damaged(line_number) from error
        if any(raw.get(field) != value for field, value in stored.items()):
            raise _damaged(line_number)
        previous_hash = str(raw["event_sha256"])
        events.append(raw)
    return tuple(events)


def _public(event: Mapping[str, Any]) -> dict[str, Any]:
    return {key: event[key] for key in ("stock_id", "amount_decimal", "unit", "supplier", "note", "recorded_at")}


def latest_on_hand(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """The current entry per stock; a cleared stock is absent."""

    latest: dict[str, dict[str, Any]] = {}
    for event in load_on_hand_events(path):
        if event["cleared"]:
            latest.pop(str(event["stock_id"]), None)
        else:
            latest[str(event["stock_id"])] = _public(event)
    return latest


def record_on_hand(*, path: Path | None = None, **fields: Any) -> dict[str, Any]:
    """Append one validated entry and return it as stored."""

    entry = normalize_on_hand_entry(**fields)
    source = on_hand_log_path(path)
    with _WRITE_LOCK:
        events = load_on_hand_events(source)
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
    "ON_HAND_LOG_NAME",
    "ON_HAND_PATH_ENV",
    "ON_HAND_UNITS",
    "StockOnHandError",
    "StockOnHandLogCorruptError",
    "latest_on_hand",
    "load_on_hand_events",
    "normalize_on_hand_entry",
    "on_hand_log_path",
    "record_on_hand",
]
