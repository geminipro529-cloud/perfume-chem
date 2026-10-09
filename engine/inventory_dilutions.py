"""Append-only records of dilutions the user prepared from a bottle they own.

Kenny (2026-10-09): bottles and dilutions saved on the Lab app's Stock page
count at the release gate too, so a new stock no longer needs a code change.
Each event names an owned parent stock (neat or stronger) and the new strength,
basis and carrier.  ``apply_prepared_dilution_events`` adds one stock per
distinct dilution with the parent's identity, so name matching, physics, IFRA
and allergen lookups work unchanged; the parent stock is not modified.

The log follows ``engine.inventory_completions``: one JSON object per line,
hash-chained, an idempotency key per command, and every action-authority flag
False.  The dated governance overlays are not changed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from engine.user_records import DILUTION_LOG_NAME

DILUTION_PATH_ENV = "PERFUME_INVENTORY_DILUTION_PATH"
SCHEMA_VERSION = "perfume-chem-prepared-dilution-event-v1"
PREPARED_DILUTION_AUTHORITY = "LAB_STOCK_PAGE_PREPARED_DILUTION"
STOCK_ID_PREFIX = "inventory:prepared-dilution:"
ALLOWED_BASES = {"mass_fraction", "volume_fraction"}
DEFAULT_BASIS = "mass_fraction"
DEFAULT_CARRIER = "dpg"
FALSE_ACTION_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}
_STOCK_FIELDS = ("parent_stock_id", "fraction_decimal", "fraction_basis", "carrier")
_RECORD_FIELDS = ("amount_made_g", "prepared_on", "user_note")
_WRITE_LOCK = threading.Lock()


class PreparedDilutionError(ValueError):
    """Invalid or unverifiable prepared dilution."""

    code = "INVALID_PREPARED_DILUTION"


class PreparedDilutionConflictError(PreparedDilutionError):
    """A stale inventory view or a reused idempotency key."""

    code = "PREPARED_DILUTION_CONFLICT"


def dilution_log_path(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    override = os.environ.get(DILUTION_PATH_ENV)
    if override:
        return Path(override).resolve()
    # Beside the completion log, as the basket log is, so it follows the same
    # data/user default and test overrides.
    from engine.inventory_completions import completion_log_path

    return completion_log_path().with_name(DILUTION_LOG_NAME)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _event_hash(event: Mapping[str, Any]) -> str:
    return _sha256_text(_canonical_json({k: v for k, v in event.items() if k != "event_sha256"}))


def _clean_text(value: object, *, maximum: int = 255) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) > maximum:
        raise PreparedDilutionError(f"text exceeds {maximum} characters")
    return text


def _fraction_text(value: object) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise PreparedDilutionError("strength must be a number") from error
    if not parsed.is_finite() or parsed <= 0 or parsed >= 1:
        raise PreparedDilutionError("strength must be above 0% and below 100%")
    return format(parsed.normalize(), "f")


def _amount_text(value: object) -> str:
    if value is None or str(value).strip() == "":
        return ""
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise PreparedDilutionError("amount made must be a number of grams") from error
    if not parsed.is_finite() or parsed <= 0:
        raise PreparedDilutionError("amount made must be more than 0 g")
    return format(parsed.normalize(), "f")


def _date_text(value: object) -> str:
    text = _clean_text(value, maximum=10)
    if not text:
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as error:
        raise PreparedDilutionError("date must be YYYY-MM-DD") from error


def _normalize_values(
    *,
    parent_stock_id: object,
    fraction_decimal: object,
    fraction_basis: object,
    carrier: object,
    amount_made_g: object,
    prepared_on: object,
    user_note: object,
) -> dict[str, str]:
    basis = _clean_text(fraction_basis).casefold()
    if basis not in ALLOWED_BASES:
        raise PreparedDilutionError("basis must be w/w (mass_fraction) or v/v (volume_fraction)")
    clean_carrier = _clean_text(carrier, maximum=120).casefold()
    if not clean_carrier:
        raise PreparedDilutionError("carrier is required")
    parent = _clean_text(parent_stock_id)
    if not parent:
        raise PreparedDilutionError("parent stock is required")
    return {
        "parent_stock_id": parent,
        "fraction_decimal": _fraction_text(fraction_decimal),
        "fraction_basis": basis,
        "carrier": clean_carrier,
        "amount_made_g": _amount_text(amount_made_g),
        "prepared_on": _date_text(prepared_on),
        "user_note": _clean_text(user_note, maximum=1000),
    }


def _validate_event(raw: object, *, previous_hash: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PreparedDilutionError("prepared dilution event must be an object")
    event = dict(raw)
    required = {
        "schema_version",
        "event_id",
        "recorded_at",
        "idempotency_key_sha256",
        "dilution_key_sha256",
        "expected_effective_inventory_sha256",
        "prepared",
        "previous_event_sha256",
        "event_sha256",
        *FALSE_ACTION_AUTHORITY,
    }
    if set(event) != required or event["schema_version"] != SCHEMA_VERSION:
        raise PreparedDilutionError("prepared dilution event shape is invalid")
    for field in (
        "idempotency_key_sha256",
        "dilution_key_sha256",
        "expected_effective_inventory_sha256",
        "event_sha256",
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", str(event[field])):
            raise PreparedDilutionError(f"prepared dilution {field} is invalid")
    if str(event["previous_event_sha256"]) != previous_hash:
        raise PreparedDilutionError("prepared dilution event chain is broken")
    if str(event["event_sha256"]) != _event_hash(event):
        raise PreparedDilutionError("prepared dilution event hash is invalid")
    if any(event[field] is not False for field in FALSE_ACTION_AUTHORITY):
        raise PreparedDilutionError("prepared dilution cannot grant action authority")
    prepared = event["prepared"]
    if not isinstance(prepared, Mapping) or set(prepared) != {
        *_STOCK_FIELDS,
        *_RECORD_FIELDS,
        "parent_identity",
    }:
        raise PreparedDilutionError("prepared dilution values are invalid")
    normalized = _normalize_values(**{k: prepared[k] for k in (*_STOCK_FIELDS, *_RECORD_FIELDS)})
    if any(normalized[k] != prepared[k] for k in normalized):
        raise PreparedDilutionError("prepared dilution values are not normalized")
    return event


def load_prepared_dilution_events(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    source = dilution_log_path(path)
    if not source.exists():
        return ()
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as error:
        raise PreparedDilutionError(f"prepared dilution log is unreadable: {error}") from error
    if len(content.encode("utf-8")) > 5_000_000:
        raise PreparedDilutionError("prepared dilution log exceeds the 5 MB local limit")
    events: list[dict[str, Any]] = []
    previous_hash = ""
    keys: set[str] = set()
    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise PreparedDilutionError(
                f"prepared dilution log line {line_number} is not valid JSON"
            ) from error
        event = _validate_event(raw, previous_hash=previous_hash)
        if event["idempotency_key_sha256"] in keys:
            raise PreparedDilutionError("prepared dilution idempotency key is duplicated")
        keys.add(str(event["idempotency_key_sha256"]))
        previous_hash = str(event["event_sha256"])
        events.append(event)
    return tuple(events)


def dilution_log_sha256(path: Path | None = None) -> str:
    source = dilution_log_path(path)
    if not source.exists():
        return ""
    return hashlib.sha256(source.read_bytes()).hexdigest()


def _identity_key(stock: Any) -> str:
    from engine.name_utils import normalize_name

    return normalize_name(str(getattr(stock, "identity_name", "") or stock.name))


def _dilution_key(parent: Any, values: Mapping[str, str]) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "identity": _identity_key(parent),
                "fraction_decimal": values["fraction_decimal"],
                "fraction_basis": values["fraction_basis"],
                "carrier": values["carrier"],
            }
        )
    )


def _parent_refusal(parent: Any, fraction: Decimal) -> str:
    if parent is None:
        return "the parent stock is not in the current inventory"
    if str(getattr(parent, "status", "")).casefold() != "owned":
        return "the parent stock is not an owned stock"
    design_ready = getattr(parent, "design_ready", None)
    if not (parent.execution_ready if design_ready is None else design_ready):
        return "the parent stock's strength, basis or carrier is not confirmed; complete it first"
    if Decimal(str(parent.dilution)) <= fraction:
        return "the new strength must be weaker than the parent stock"
    return ""


def _label(identity: str, values: Mapping[str, str]) -> str:
    basis = "w/w" if values["fraction_basis"] == "mass_fraction" else "v/v"
    percent = format((Decimal(values["fraction_decimal"]) * 100).normalize(), "f")
    return f"{identity} {percent}% {basis} in {values['carrier'].upper()} (prepared)"


def apply_prepared_dilution_events(materialization: Any, path: Path | None = None) -> Any:
    """Add one stock per distinct prepared dilution whose parent is still present."""

    events = load_prepared_dilution_events(path)
    stocks = list(materialization.stocks)
    by_id = {stock.stock_id: stock for stock in stocks}
    seen: set[str] = set()
    for event in events:
        key = str(event["dilution_key_sha256"])
        prepared = event["prepared"]
        parent = by_id.get(str(prepared["parent_stock_id"]))
        if key in seen or _parent_refusal(parent, Decimal(prepared["fraction_decimal"])):
            continue
        seen.add(key)
        identity = str(parent.identity_name or parent.name)
        source_ref = f"{dilution_log_path(path)}#{event['event_id']}"
        stocks.append(
            replace(
                parent,
                dilution=float(Decimal(prepared["fraction_decimal"])),
                raw_name=_label(identity, prepared),
                fraction_basis=str(prepared["fraction_basis"]),
                carrier=str(prepared["carrier"]),
                physical_form="liquid",
                approximate=False,
                stock_id=STOCK_ID_PREFIX + key[:20],
                authority=PREPARED_DILUTION_AUTHORITY,
                source_rows=(),
                source_ref=source_ref,
                execution_ready=True,
                execution_hold_reason="",
                requirement_state="",
                design_ready=True,
                design_hold_reason="",
                completion_event_sha256=str(event["event_sha256"]),
                completion_source_ref=source_ref,
                homogeneity="HOMOGENEOUS",
            )
        )
    log_hash = dilution_log_sha256(path)
    if not log_hash:
        return materialization
    return replace(
        materialization,
        stocks=tuple(stocks),
        effective_inventory_sha256=_sha256_text(
            f"{materialization.effective_inventory_sha256}|dilutions:{log_hash}"
        ),
    )


def record_prepared_dilution(
    *,
    parent_stock_id: str,
    expected_effective_inventory_sha256: str,
    idempotency_key: str,
    fraction_decimal: object,
    fraction_basis: object = DEFAULT_BASIS,
    carrier: object = DEFAULT_CARRIER,
    amount_made_g: object = "",
    prepared_on: object = "",
    user_note: object = "",
    path: Path | None = None,
) -> tuple[dict[str, Any], Any]:
    """Append one prepared dilution and return it with a fresh materialization.

    Preparing the same dilution (same identity, strength, basis and carrier)
    again returns the earlier event instead of adding a second stock.
    """

    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_effective_inventory_sha256)):
        raise PreparedDilutionError("expected_effective_inventory_sha256 is invalid")
    clean_key = _clean_text(idempotency_key)
    if not clean_key:
        raise PreparedDilutionError("idempotency_key is required")
    key_hash = _sha256_text(clean_key)
    values = _normalize_values(
        parent_stock_id=parent_stock_id,
        fraction_decimal=fraction_decimal,
        fraction_basis=fraction_basis,
        carrier=carrier,
        amount_made_g=amount_made_g,
        prepared_on=prepared_on,
        user_note=user_note,
    )
    source = dilution_log_path(path)
    from engine.inventory_parser import materialize_current_inventory

    with _WRITE_LOCK:
        events = load_prepared_dilution_events(source)
        materialized = materialize_current_inventory()
        parent = next(
            (s for s in materialized.stocks if s.stock_id == values["parent_stock_id"]), None
        )
        if parent is not None and parent.authority == PREPARED_DILUTION_AUTHORITY:
            parent = None  # dilute from a bottle in the inventory, not a prepared record
        refusal = _parent_refusal(parent, Decimal(values["fraction_decimal"]))
        if refusal:
            raise PreparedDilutionError(refusal)
        dilution_key = _dilution_key(parent, values)
        for existing in events:
            if existing["idempotency_key_sha256"] == key_hash:
                if existing["dilution_key_sha256"] != dilution_key:
                    raise PreparedDilutionConflictError(
                        "idempotency key was already used for a different dilution"
                    )
                return dict(existing), materialized
        for existing in events:
            if existing["dilution_key_sha256"] == dilution_key:
                return dict(existing), materialized
        if materialized.effective_inventory_sha256 != expected_effective_inventory_sha256:
            raise PreparedDilutionConflictError(
                "inventory changed after this editor was opened; refresh and review before saving"
            )
        previous_hash = str(events[-1]["event_sha256"]) if events else ""
        event_core: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_id": "prepared-dilution-" + dilution_key[:20],
            "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "idempotency_key_sha256": key_hash,
            "dilution_key_sha256": dilution_key,
            "expected_effective_inventory_sha256": expected_effective_inventory_sha256,
            "prepared": {**values, "parent_identity": _identity_key(parent)},
            "previous_event_sha256": previous_hash,
            **FALSE_ACTION_AUTHORITY,
        }
        event = {**event_core, "event_sha256": _event_hash(event_core)}
        source.parent.mkdir(parents=True, exist_ok=True)
        encoded = (_canonical_json(event) + "\n").encode("utf-8")
        try:
            descriptor = os.open(source, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            try:
                os.write(descriptor, encoded)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise PreparedDilutionError(f"prepared dilution could not be saved: {error}") from error
        return event, materialize_current_inventory()


__all__ = [
    "DILUTION_PATH_ENV",
    "FALSE_ACTION_AUTHORITY",
    "PREPARED_DILUTION_AUTHORITY",
    "PreparedDilutionConflictError",
    "PreparedDilutionError",
    "apply_prepared_dilution_events",
    "dilution_log_path",
    "dilution_log_sha256",
    "load_prepared_dilution_events",
    "record_prepared_dilution",
]
