"""Which physical basket each stock material sits in, for the Lab page only.

Kenny keeps his stock bottles in 17 baskets and compounds basket by basket.
An unconfirmed seed drafted from past bench cards proposes baskets; his own
choices are appended to a hash-chained JSONL log and the last choice per
normalized identity wins.  This is display/ordering data: nothing here feeds
the mixer sequence, bench instructions or any release gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:  # POSIX
    import fcntl
except ImportError:  # Windows, where Kenny runs the app
    fcntl = None  # type: ignore[assignment]
try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None  # type: ignore[assignment]

from engine import inventory_completions
from engine.mixer.sequencer import BASKET_LABELS
from engine.name_utils import normalize_name
from engine.user_records import BASKET_LOG_NAME

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASKET_EVENT_PATH_ENV = "PERFUME_BASKET_EVENT_PATH"
BASKET_SEED_PATH = PROJECT_ROOT / "data" / "baskets" / "past_cards_draft_20261008.json"

EVENT_SCHEMA = "basket-event-v1"
SEED_SCHEMA = "basket-seed-v1"
CRYSTALS_SUFFIX = " crystals"

STATUS_CONFIRMED = "confirmed"
STATUS_FROM_PAST_CARDS = "from_past_cards"
STATUS_CONFLICTING = "conflicting"
STATUS_NONE = "none"

_WRITE_LOCK = threading.Lock()


class BasketError(ValueError):
    """Invalid basket choice, seed or event log."""

    code = "INVALID_BASKET"


class BasketLogCorruptError(BasketError):
    """The basket log can't be read; the message is plain enough to show Kenny."""

    code = "BASKET_LOG_CORRUPT"


def _damaged_line(line_number: int) -> BasketLogCorruptError:
    return BasketLogCorruptError(
        f"The basket log has a damaged line (line {line_number}); "
        "your basket choices can't be read until it is repaired."
    )


def basket_key(normalized_identity: str) -> str:
    """Canonical key: a material's solution and crystals forms share one basket."""

    return normalized_identity.removesuffix(CRYSTALS_SUFFIX)


def basket_event_log_path(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    override = os.environ.get(BASKET_EVENT_PATH_ENV)
    return Path(override).resolve() if override else default_basket_event_path().resolve()


def default_basket_event_path() -> Path:
    """Beside the stock completion log in data/user/, as backups and the export expect.

    Resolving the completion log also carries an older basket log over from output/.
    """
    return inventory_completions.completion_log_path().with_name(BASKET_LOG_NAME)


def basket_list() -> list[dict[str, Any]]:
    return [{"number": number, "name": name} for number, name in sorted(BASKET_LABELS.items())]


def _valid_basket(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value in BASKET_LABELS


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _event_hash(core: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(core).encode("utf-8")).hexdigest()


def load_basket_events(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    """Read and verify the hash chain of Kenny's basket choices."""

    source = basket_event_log_path(path)
    if not source.exists():
        return ()
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as error:
        raise BasketLogCorruptError(
            "The basket log can't be read; your basket choices can't be read "
            "until it is repaired."
        ) from error
    events: list[dict[str, Any]] = []
    previous_hash = ""
    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise _damaged_line(line_number) from error
        if not isinstance(raw, dict) or raw.get("schema") != EVENT_SCHEMA:
            raise _damaged_line(line_number)
        core = {key: value for key, value in raw.items() if key != "event_sha256"}
        if raw.get("previous_hash") != previous_hash or raw.get("event_sha256") != _event_hash(
            core
        ):
            raise _damaged_line(line_number)
        if not isinstance(raw.get("normalized_identity"), str) or not (
            raw.get("basket") is None or _valid_basket(raw.get("basket"))
        ):
            raise _damaged_line(line_number)
        previous_hash = str(raw["event_sha256"])
        events.append(raw)
    return tuple(events)


def confirmed_baskets(path: Path | None = None) -> dict[str, int | None]:
    """Return the last confirmed basket (or explicit None) per canonical basket key.

    Events stored under an older "... crystals" key map to the canonical key.
    """

    return {
        basket_key(str(event["normalized_identity"])): event["basket"]
        for event in load_basket_events(path)
    }


def load_basket_seed(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return the past-card seed keyed by normalized identity name.

    Seed spellings that normalize to one identity (e.g. "Aldehyde C10" and
    "Aldehyde C10 neat") are merged: one shared basket stays agreed, several
    become competing suggestions.
    """

    source = path or BASKET_SEED_PATH
    seed = json.loads(source.read_text(encoding="utf-8"))
    if seed.get("schema") != SEED_SCHEMA:
        raise BasketError("basket seed has the wrong schema")
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for entry in seed["materials"]:
        grouped.setdefault(normalize_name(entry["identity_name"]), []).append(entry)
    merged: dict[str, dict[str, Any]] = {}
    for key, group in grouped.items():
        baskets = sorted(
            {entry["basket"] for entry in group if entry["basket"] is not None}
            | {basket for entry in group for basket in entry["competing_baskets"]}
        )
        if not all(_valid_basket(basket) for basket in baskets):
            raise BasketError(f"basket seed has an invalid basket for {key!r}")
        merged[key] = {
            "identity_names": [entry["identity_name"] for entry in group],
            "basket": baskets[0] if len(baskets) == 1 else None,
            "competing_baskets": baskets if len(baskets) > 1 else [],
            "sources": [source_row for entry in group for source_row in entry["sources"]],
        }
    return merged


def stock_basket_fields(
    normalized_identity: str,
    *,
    confirmed: Mapping[str, int | None],
    seed: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Basket fields for one stock; every strength and form of one material shares them."""

    key = basket_key(normalized_identity)
    if key in confirmed:
        return {
            "basket_key": key,
            "basket": confirmed[key],
            "basket_status": STATUS_CONFIRMED,
            "basket_suggestions": [],
        }
    # Crystals and solutions of one material share the seed's past-card basket.
    entry = seed.get(normalized_identity) or seed.get(key)
    if entry is not None and entry.get("basket") is not None:
        return {
            "basket_key": key,
            "basket": entry["basket"],
            "basket_status": STATUS_FROM_PAST_CARDS,
            "basket_suggestions": [],
        }
    if entry is not None and entry.get("competing_baskets"):
        return {
            "basket_key": key,
            "basket": None,
            "basket_status": STATUS_CONFLICTING,
            "basket_suggestions": list(entry["competing_baskets"]),
        }
    return {
        "basket_key": key,
        "basket": None,
        "basket_status": STATUS_NONE,
        "basket_suggestions": [],
    }


@contextmanager
def _file_lock(log_path: Path) -> Iterator[None]:
    """Cross-process lock so two servers can't append with one previous_hash."""

    lock_path = log_path.with_name(log_path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:
            while True:  # LK_LOCK gives up after ~10 s; keep waiting instead
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        # With neither module available only the in-process lock protects us.
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def record_basket_choice(
    *,
    normalized_identity: str,
    identity_name: str,
    basket: int | None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Append one confirmed basket choice (None means "no basket")."""

    if basket is not None and not _valid_basket(basket):
        raise BasketError("basket must be a number from 1 to 17, or null for no basket")
    source = basket_event_log_path(path)
    with _WRITE_LOCK, _file_lock(source):
        events = load_basket_events(source)
        core: dict[str, Any] = {
            "schema": EVENT_SCHEMA,
            "normalized_identity": basket_key(normalized_identity),
            "posted_identity": normalized_identity,
            "identity_name": identity_name,
            "basket": basket,
            "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "previous_hash": str(events[-1]["event_sha256"]) if events else "",
        }
        event = {**core, "event_sha256": _event_hash(core)}
        source.parent.mkdir(parents=True, exist_ok=True)
        with source.open("a", encoding="utf-8") as handle:
            handle.write(_canonical_json(event) + "\n")
    return event


__all__ = [
    "BASKET_EVENT_PATH_ENV",
    "BASKET_SEED_PATH",
    "BasketError",
    "BasketLogCorruptError",
    "basket_key",
    "basket_event_log_path",
    "default_basket_event_path",
    "basket_list",
    "confirmed_baskets",
    "load_basket_events",
    "load_basket_seed",
    "record_basket_choice",
    "stock_basket_fields",
]
