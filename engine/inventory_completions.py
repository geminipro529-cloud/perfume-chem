"""Append-only personal inventory-detail completion receipts.

The dated governance overlays remain immutable scientific/physical authority.
This module adds a deliberately lighter personal layer so a user can confirm
the stock facts needed to formulate from material they already own (the Lab
app's Stock page writes these events).  A completion that gives the strength,
basis and carrier (or neat) makes the stock design-ready and, for the hold
reasons ``COMPLETION_HOLD_DISPOSITIONS`` marks cleared, ready at the release
gate too.  The gate still runs every check, and a completion never grants
physical-compounding, safety, release, or regulatory authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from engine.user_records import (
    BASKET_LOG_NAME,
    COMPLETION_LOG_NAME,
    LEGACY_RECORDS_DIR,
    USER_RECORDS_DIR,
    copy_legacy_record,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPLETION_PATH_ENV = "PERFUME_INVENTORY_COMPLETION_PATH"
DEFAULT_COMPLETION_PATH = USER_RECORDS_DIR / COMPLETION_LOG_NAME
# Older versions kept the log (and the basket log beside it) in output/; they
# are copied once, never moved.
LEGACY_COMPLETION_PATH = LEGACY_RECORDS_DIR / COMPLETION_LOG_NAME

SCHEMA_VERSION = "perfume-chem-personal-inventory-completion-event-v1"
ALLOWED_BASES = {
    "neat",
    "mass_fraction",
    "volume_fraction",
    "mass_per_volume",
    "unspecified",
}
ALLOWED_HOMOGENEITY = {
    "NOT_APPLICABLE",
    "HOMOGENEOUS",
    "FULLY_DISSOLVED",
    "UNKNOWN",
    "NOT_HOMOGENEOUS",
}
ALLOWED_SOURCE_KINDS = {
    "USER_LABEL_OR_RECIPE",
    "USER_MEASUREMENT",
    "SUPPLIER_LABEL",
    "PERSONAL_CONFIRMATION",
}
FALSE_ACTION_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}

# Set when the latest Stock page entry for a stock leaves it not design-ready:
# its strength is then Kenny's unfinished word, so the gate must not use it.
# A later complete entry replaces that entry and so clears this hold.
STOCK_PAGE_ENTRY_INCOMPLETE = "STOCK_PAGE_ENTRY_INCOMPLETE"

# Every execution hold reason the current inventory carries (plus the earlier
# ones the overlays have used), and whether a completion that makes the stock
# design-ready also clears it at the release gate.  True: the hold only records
# a strength/basis/carrier fact the Stock page form supplies.  False: the form
# does not answer it.  A reason not listed here is kept.
COMPLETION_HOLD_DISPOSITIONS: dict[str, tuple[bool, str]] = {
    "": (True, "unnamed hold: cleared only if the stock lacked basis or carrier"),
    STOCK_PAGE_ENTRY_INCOMPLETE: (True, "the latest Stock page entry left the stock incomplete"),
    "STOCK_INTAKE_IDENTITY_ONLY": (True, "intake named the product, not its strength/basis/carrier"),
    "FRACTION_BASIS_UNSPECIFIED": (True, "basis is a form field"),
    "CARRIER_UNSPECIFIED": (True, "carrier is a form field"),
    "FRACTION_BASIS_AND_CARRIER_UNSPECIFIED": (True, "basis and carrier are form fields"),
    "FRACTION_BASIS_OR_CARRIER_UNSPECIFIED": (True, "basis and carrier are form fields"),
    "STOCK_FRACTION_UNSPECIFIED": (True, "strength is a form field"),
    "RESTOCKED_BOTTLE_STRENGTH_AND_CARRIER_NOT_STATED": (True, "strength and carrier are form fields"),
    "APPROXIMATE_STOCK_FRACTION": (True, "the form records an exact strength"),
    "FRACTION_BASIS_AND_HOMOGENEITY_NOT_CONFIRMED": (
        True,
        "design readiness requires a basis and a homogeneity confirmation",
    ),
    "HOMOGENEITY_NOT_RECONFIRMED": (True, "design readiness requires a homogeneity confirmation"),
    "FINAL_DISSOLVED_FRACTION_UNMEASURED": (
        True,
        "design readiness requires a known final fraction from a measurement or label",
    ),
    "FILTERED_TINCTURE_FINAL_DISSOLVED_FRACTION_UNKNOWN": (
        False,
        "the final-fraction safeguard covers only starting-charge stocks",
    ),
    "TINCTURE_PERCENTAGE_BASIS_AND_EXTRACTED_SOLIDS_UNSPECIFIED": (
        False,
        "extracted solids are not a form field",
    ),
    "VISIBLE_CRYSTALS_LIQUID_PHASE_STRENGTH_UNKNOWN": (False, "a phase problem, not a label fact"),
    # AGENTS.md RULE 6: lots and receipts are not needed to compute a formula;
    # Kenny confirming the bottle and its strength on the Stock page is.
    "BOTTLE_LOT_AND_LABEL_RECEIPT_MISSING": (True, "RULE 6: a lot or label receipt is not needed"),
    "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING": (
        True,
        "RULE 6: the confirmed strength, basis and carrier replace the receipts",
    ),
    "PREPARATION_QUANTITIES_DATE_AND_LOTS_MISSING": (
        True,
        "RULE 6: the confirmed strength, basis and carrier replace the preparation record",
    ),
    "LOT_PURCHASE_SOURCE_AND_LABEL_RECEIPT_MISSING": (
        True,
        "RULE 6: a lot, purchase source or label receipt is not needed",
    ),
    "LEGACY_TEXT_CURRENT_STOCK_HOLD": (False, "a legacy-text conflict, not a missing fact"),
    "USER_COMPOUNDING_HOLD": (False, "the user's exclusion; only an explicit clearance lifts it"),
}
COMPLETION_CLEARABLE_HOLDS = frozenset(
    reason for reason, (cleared, _why) in COMPLETION_HOLD_DISPOSITIONS.items() if cleared and reason
)

_WRITE_LOCK = threading.Lock()


class InventoryCompletionError(ValueError):
    """Invalid or unverifiable personal inventory completion."""

    code = "INVALID_INVENTORY_COMPLETION"


class InventoryCompletionConflictError(InventoryCompletionError):
    """A stale or mismatched idempotent completion command."""

    code = "INVENTORY_COMPLETION_CONFLICT"


def completion_log_path(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    override = os.environ.get(COMPLETION_PATH_ENV)
    if override:
        return Path(override).resolve()
    default = DEFAULT_COMPLETION_PATH.resolve()
    copy_legacy_record(LEGACY_COMPLETION_PATH, default)
    copy_legacy_record(
        LEGACY_COMPLETION_PATH.with_name(BASKET_LOG_NAME),
        default.with_name(BASKET_LOG_NAME),
    )
    return default


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _event_hash(event: Mapping[str, Any]) -> str:
    return _sha256_text(_canonical_json({key: value for key, value in event.items() if key != "event_sha256"}))


def _clean_text(value: object, *, maximum: int = 255) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) > maximum:
        raise InventoryCompletionError(f"text exceeds {maximum} characters")
    return text


def _decimal_text(value: object, field: str) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise InventoryCompletionError(f"{field} must be a finite decimal") from error
    if not parsed.is_finite() or parsed <= 0 or parsed > 1:
        raise InventoryCompletionError(f"{field} must be greater than 0 and no greater than 1")
    rendered = format(parsed, "f").rstrip("0").rstrip(".")
    return rendered or "0"


def _validate_event(raw: object, *, previous_hash: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise InventoryCompletionError("inventory completion event must be an object")
    event = dict(raw)
    required = {
        "schema_version",
        "event_id",
        "recorded_at",
        "idempotency_key_sha256",
        "command_sha256",
        "target_stock_id",
        "expected_effective_inventory_sha256",
        "confirmed_values",
        "source_kind",
        "user_note",
        "previous_event_sha256",
        "event_sha256",
        *FALSE_ACTION_AUTHORITY,
    }
    if set(event) != required:
        raise InventoryCompletionError("inventory completion event shape is invalid")
    if event["schema_version"] != SCHEMA_VERSION:
        raise InventoryCompletionError("inventory completion event schema is unsupported")
    for field in (
        "idempotency_key_sha256",
        "command_sha256",
        "expected_effective_inventory_sha256",
        "event_sha256",
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", str(event[field])):
            raise InventoryCompletionError(f"inventory completion {field} is invalid")
    if str(event["previous_event_sha256"]) != previous_hash:
        raise InventoryCompletionError("inventory completion event chain is broken")
    if str(event["event_sha256"]) != _event_hash(event):
        raise InventoryCompletionError("inventory completion event hash is invalid")
    if event["source_kind"] not in ALLOWED_SOURCE_KINDS:
        raise InventoryCompletionError("inventory completion source kind is invalid")
    if any(event[field] is not False for field in FALSE_ACTION_AUTHORITY):
        raise InventoryCompletionError("inventory completion cannot grant action authority")
    values = event["confirmed_values"]
    if not isinstance(values, Mapping):
        raise InventoryCompletionError("inventory completion values are invalid")
    expected_value_fields = {
        "fraction_decimal",
        "fraction_basis",
        "carrier",
        "physical_form",
        "possession_confirmed",
        "homogeneity",
        "final_fraction_known",
    }
    if set(values) != expected_value_fields:
        raise InventoryCompletionError("inventory completion value shape is invalid")
    _decimal_text(values["fraction_decimal"], "fraction_decimal")
    if values["fraction_basis"] not in ALLOWED_BASES:
        raise InventoryCompletionError("inventory completion fraction basis is invalid")
    if values["homogeneity"] not in ALLOWED_HOMOGENEITY:
        raise InventoryCompletionError("inventory completion homogeneity is invalid")
    if not isinstance(values["possession_confirmed"], bool) or not isinstance(
        values["final_fraction_known"], bool
    ):
        raise InventoryCompletionError("inventory completion confirmations must be booleans")
    _clean_text(values["carrier"])
    _clean_text(values["physical_form"])
    return event


def load_inventory_completion_events(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    source = completion_log_path(path)
    if not source.exists():
        return ()
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as error:
        raise InventoryCompletionError(f"inventory completion log is unreadable: {error}") from error
    if len(content.encode("utf-8")) > 5_000_000:
        raise InventoryCompletionError("inventory completion log exceeds the 5 MB local limit")
    events: list[dict[str, Any]] = []
    previous_hash = ""
    idempotency_keys: set[str] = set()
    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise InventoryCompletionError(
                f"inventory completion log line {line_number} is not valid JSON"
            ) from error
        event = _validate_event(raw, previous_hash=previous_hash)
        key_hash = str(event["idempotency_key_sha256"])
        if key_hash in idempotency_keys:
            raise InventoryCompletionError("inventory completion idempotency key is duplicated")
        idempotency_keys.add(key_hash)
        previous_hash = str(event["event_sha256"])
        events.append(event)
    return tuple(events)


def completion_log_sha256(path: Path | None = None) -> str:
    source = completion_log_path(path)
    if not source.exists():
        return ""
    try:
        return hashlib.sha256(source.read_bytes()).hexdigest()
    except OSError as error:
        raise InventoryCompletionError(f"inventory completion log is unreadable: {error}") from error


def _hold_reasons(stock: Any) -> list[str]:
    return [item for item in str(getattr(stock, "execution_hold_reason", "")).split("|") if item]


def _effective_design_readiness(stock: Any, values: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
    missing: list[str] = []
    fraction = Decimal(str(values["fraction_decimal"]))
    basis = str(values["fraction_basis"])
    carrier = _clean_text(values["carrier"])
    physical_form = _clean_text(values["physical_form"])
    homogeneity = str(values["homogeneity"])
    if not values["possession_confirmed"]:
        missing.append("possession_confirmation")
    if fraction == 1:
        if basis != "neat":
            missing.append("fraction_basis_neat")
        if carrier:
            missing.append("carrier_must_be_empty_for_neat_stock")
    else:
        if basis not in {"mass_fraction", "volume_fraction", "mass_per_volume"}:
            missing.append("fraction_basis")
        if not carrier:
            missing.append("carrier")
        if homogeneity not in {"HOMOGENEOUS", "FULLY_DISSOLVED"}:
            missing.append("homogeneity_confirmation")
    if not physical_form:
        missing.append("physical_form")
    starting_charge = (
        str(getattr(stock, "fraction_basis", "")) == "mass_fraction_starting_charge"
        or "FINAL_DISSOLVED_FRACTION_UNMEASURED" in _hold_reasons(stock)
    )
    if starting_charge and not values["final_fraction_known"]:
        missing.append("final_usable_fraction_confirmation")
    if starting_charge and str(values.get("source_kind", "")) == "USER_LABEL_OR_RECIPE":
        missing.append("final_fraction_measurement_or_label_source")
    if str(getattr(stock, "status", "")).casefold() != "owned":
        missing.append("owned_stock")
    return not missing, tuple(dict.fromkeys(missing))


def inventory_completion_requirements(stock: Any) -> tuple[str, ...]:
    if bool(getattr(stock, "execution_ready", False)):
        return ()
    if getattr(stock, "design_ready", None) is True:
        return ()
    current = getattr(stock, "design_hold_reason", "")
    if current:
        return tuple(item for item in str(current).split("|") if item)
    missing: list[str] = ["possession_confirmation"]
    fraction = Decimal(str(getattr(stock, "dilution", 0) or 0))
    basis = str(getattr(stock, "fraction_basis", "") or "")
    if fraction <= 0:
        missing.append("fraction_percent")
    elif fraction < 1:
        if basis in {"", "unspecified", "mass_fraction_starting_charge"}:
            missing.append("fraction_basis")
        if not str(getattr(stock, "carrier", "") or "").strip():
            missing.append("carrier")
        missing.append("homogeneity_confirmation")
    if not str(getattr(stock, "physical_form", "") or "").strip():
        missing.append("physical_form")
    if (
        basis == "mass_fraction_starting_charge"
        or "FINAL_DISSOLVED_FRACTION_UNMEASURED" in _hold_reasons(stock)
    ):
        missing.append("final_usable_fraction_confirmation")
    return tuple(dict.fromkeys(missing))


def completion_clears_execution_hold(stock: Any) -> bool:
    """Whether a complete Stock page entry would make this held stock ready."""

    if str(getattr(stock, "row_unresolved_tokens", "") or ""):
        # The V5 row itself is unresolved (identity kept separate, species
        # unresolved, ...); the form's strength/basis/carrier do not answer it.
        return False
    reasons = _hold_reasons(stock)
    if reasons:
        return all(reason in COMPLETION_CLEARABLE_HOLDS for reason in reasons)
    # An unnamed hold on a stock whose strength, basis and carrier were already
    # complete came from elsewhere in its row (an unresolved species or a
    # product basis, say), which a completion does not answer.
    basis = str(getattr(stock, "fraction_basis", "") or "")
    if float(getattr(stock, "dilution", 0) or 0) == 1:
        return basis != "neat"
    return basis in {"", "unspecified"} or not str(getattr(stock, "carrier", "") or "").strip()


def _authority_facts_differ(
    stock: Any, fraction: float, basis: str, carrier: str
) -> tuple[tuple[str, Any], ...]:
    """The authority's stock facts when the completion changes any of them.

    An authority value that states nothing (no strength, an unspecified basis,
    no carrier) is filled in by the completion rather than contradicted.
    """

    authority_fraction = float(getattr(stock, "dilution", 0) or 0)
    authority_basis = str(getattr(stock, "fraction_basis", "") or "")
    authority_carrier = str(getattr(stock, "carrier", "") or "").strip()
    differs = (
        (authority_fraction > 0 and abs(authority_fraction - fraction) > 1e-9)
        or (authority_basis not in {"", "unspecified"} and authority_basis != basis)
        or (bool(authority_carrier) and authority_carrier.casefold() != carrier.casefold())
    )
    if not differs:
        return ()
    return (
        ("dilution", authority_fraction),
        ("fraction_basis", authority_basis),
        ("carrier", authority_carrier),
    )


def apply_inventory_completion_events(materialization: Any, path: Path | None = None) -> Any:
    events = load_inventory_completion_events(path)
    latest_by_stock: dict[str, dict[str, Any]] = {}
    for event in events:
        latest_by_stock[str(event["target_stock_id"])] = event

    completed_stocks: list[Any] = []
    for stock in materialization.stocks:
        latest_event = latest_by_stock.get(str(stock.stock_id))
        if latest_event is None:
            completed_stocks.append(stock)
            continue
        values = dict(latest_event["confirmed_values"])
        values["source_kind"] = latest_event["source_kind"]
        design_ready, missing = _effective_design_readiness(stock, values)
        fraction = float(Decimal(str(values["fraction_decimal"])))
        carrier = _clean_text(values["carrier"])
        physical_form = _clean_text(values["physical_form"])
        descriptor = (
            f"{physical_form or 'as supplied'} / neat"
            if fraction == 1
            else f"{fraction * 100:g}% {values['fraction_basis']} in {carrier or 'carrier unstated'}"
        )
        execution_ready = bool(stock.execution_ready)
        execution_hold_reason = str(stock.execution_hold_reason)
        if not design_ready:
            # The entry replaces the stock's strength, so an unfinished one
            # must not leave a ready stock ready at a strength nobody confirmed.
            execution_ready = False
            execution_hold_reason = "|".join(
                dict.fromkeys([STOCK_PAGE_ENTRY_INCOMPLETE, *_hold_reasons(stock)])
            )
        elif not execution_ready and completion_clears_execution_hold(stock):
            execution_ready = True
            execution_hold_reason = ""
        completed_stocks.append(
            replace(
                stock,
                execution_ready=execution_ready,
                execution_hold_reason=execution_hold_reason,
                dilution=fraction,
                fraction_basis=str(values["fraction_basis"]),
                carrier=carrier,
                physical_form=physical_form,
                raw_name=descriptor,
                approximate=False,
                design_ready=design_ready,
                design_hold_reason="|".join(missing),
                completion_event_sha256=str(latest_event["event_sha256"]),
                authority_facts_differ=_authority_facts_differ(
                    stock, fraction, str(values["fraction_basis"]), carrier
                ),
                completion_source_ref=(
                    f"{completion_log_path(path)}#{latest_event['event_id']}"
                ),
                homogeneity=str(values["homogeneity"]),
            )
        )

    log_hash = completion_log_sha256(path)
    effective_payload = {
        "snapshot_sha256": materialization.snapshot_sha256,
        "overlay_sha256": materialization.overlay_sha256,
        "completion_sha256": log_hash,
        "event_hashes": [event["event_sha256"] for event in events],
    }
    return replace(
        materialization,
        stocks=tuple(completed_stocks),
        completion_sha256=log_hash,
        effective_inventory_sha256=_sha256_text(_canonical_json(effective_payload)),
    )


def _normalize_command(
    *,
    stock: Any,
    fraction_decimal: object | None,
    fraction_basis: object | None,
    carrier: object | None,
    physical_form: object | None,
    possession_confirmed: bool,
    homogeneity: str,
    final_fraction_known: bool,
    source_kind: str,
    user_note: str,
) -> dict[str, Any]:
    fraction = _decimal_text(
        fraction_decimal if fraction_decimal is not None else getattr(stock, "dilution", 0),
        "fraction_decimal",
    )
    basis = _clean_text(
        fraction_basis if fraction_basis is not None else getattr(stock, "fraction_basis", "")
    ).casefold()
    if basis not in ALLOWED_BASES:
        raise InventoryCompletionError("fraction_basis is unsupported")
    clean_carrier = _clean_text(
        carrier if carrier is not None else getattr(stock, "carrier", "")
    ).casefold()
    clean_form = _clean_text(
        physical_form if physical_form is not None else getattr(stock, "physical_form", "")
    ).casefold()
    if homogeneity not in ALLOWED_HOMOGENEITY:
        raise InventoryCompletionError("homogeneity is unsupported")
    if source_kind not in ALLOWED_SOURCE_KINDS:
        raise InventoryCompletionError("source_kind is unsupported")
    if Decimal(fraction) == 1 and (basis != "neat" or clean_carrier):
        raise InventoryCompletionError("a 100% stock must use neat basis with no carrier")
    return {
        "target_stock_id": str(stock.stock_id),
        "confirmed_values": {
            "fraction_decimal": fraction,
            "fraction_basis": basis,
            "carrier": clean_carrier,
            "physical_form": clean_form,
            "possession_confirmed": bool(possession_confirmed),
            "homogeneity": homogeneity,
            "final_fraction_known": bool(final_fraction_known),
        },
        "source_kind": source_kind,
        "user_note": _clean_text(user_note, maximum=1000),
    }


def record_inventory_completion(
    *,
    stock_id: str,
    expected_effective_inventory_sha256: str,
    idempotency_key: str,
    fraction_decimal: object | None,
    fraction_basis: object | None,
    carrier: object | None,
    physical_form: object | None,
    possession_confirmed: bool,
    homogeneity: str,
    final_fraction_known: bool,
    source_kind: str,
    user_note: str = "",
    path: Path | None = None,
) -> tuple[dict[str, Any], Any]:
    """Append one idempotent completion and return it with fresh materialization."""

    clean_stock_id = _clean_text(stock_id)
    clean_key = _clean_text(idempotency_key)
    if not re.fullmatch(r"[0-9a-f]{64}", expected_effective_inventory_sha256):
        raise InventoryCompletionError("expected_effective_inventory_sha256 is invalid")
    key_hash = _sha256_text(clean_key)
    source = completion_log_path(path)

    with _WRITE_LOCK:
        events = load_inventory_completion_events(source)
        from engine.inventory_parser import materialize_current_inventory

        materialized = materialize_current_inventory()
        stock = next((item for item in materialized.stocks if item.stock_id == clean_stock_id), None)
        if stock is None:
            raise InventoryCompletionError("target inventory stock does not exist")
        command = _normalize_command(
            stock=stock,
            fraction_decimal=fraction_decimal,
            fraction_basis=fraction_basis,
            carrier=carrier,
            physical_form=physical_form,
            possession_confirmed=possession_confirmed,
            homogeneity=homogeneity,
            final_fraction_known=final_fraction_known,
            source_kind=source_kind,
            user_note=user_note,
        )
        command_sha = _sha256_text(_canonical_json(command))
        for existing in events:
            if existing["idempotency_key_sha256"] != key_hash:
                continue
            if existing["command_sha256"] != command_sha:
                raise InventoryCompletionConflictError(
                    "idempotency key was already used for different inventory details"
                )
            return dict(existing), materialized
        if materialized.effective_inventory_sha256 != expected_effective_inventory_sha256:
            raise InventoryCompletionConflictError(
                "inventory changed after this editor was opened; refresh and review before saving"
            )
        previous_hash = str(events[-1]["event_sha256"]) if events else ""
        recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        event_core: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_id": "inventory-completion-" + command_sha[:20],
            "recorded_at": recorded_at,
            "idempotency_key_sha256": key_hash,
            "command_sha256": command_sha,
            "target_stock_id": clean_stock_id,
            "expected_effective_inventory_sha256": expected_effective_inventory_sha256,
            "confirmed_values": command["confirmed_values"],
            "source_kind": command["source_kind"],
            "user_note": command["user_note"],
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
            raise InventoryCompletionError(
                f"inventory completion could not be persisted: {error}"
            ) from error

        fresh = materialize_current_inventory()
        return event, fresh


def effective_design_ready(stock: Any) -> bool:
    value = getattr(stock, "design_ready", None)
    return bool(stock.execution_ready if value is None else value)


__all__ = [
    "COMPLETION_CLEARABLE_HOLDS",
    "COMPLETION_HOLD_DISPOSITIONS",
    "COMPLETION_PATH_ENV",
    "STOCK_PAGE_ENTRY_INCOMPLETE",
    "InventoryCompletionConflictError",
    "InventoryCompletionError",
    "completion_clears_execution_hold",
    "apply_inventory_completion_events",
    "completion_log_path",
    "completion_log_sha256",
    "effective_design_ready",
    "inventory_completion_requirements",
    "load_inventory_completion_events",
    "record_inventory_completion",
]
