"""Personal-design inventory projection and append-only ownership additions.

The governed current-inventory materialization is the authority for exact
physical stock binding.  Personal formulation needs a wider, deliberately
lower-authority view: every currently owned row in ``inventory.txt`` plus
materials the user directly confirms through the workbench.  This module
builds that view without rewriting historical governance records or granting
physical-compounding, safety, release, or evidence-admission authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from engine.inventory_dilutions import PREPARED_DILUTION_AUTHORITY
from engine.inventory_parser import (
    INVENTORY_PATH,
    CurrentInventoryMaterialization,
    InventoryMaterial,
    InventoryRequirement,
    apply_user_compounding_holds,
    assign_stock_display_names,
    materialize_current_inventory,
    parse_inventory,
)
from engine.name_utils import normalize_name
from engine.user_records import (
    ADDITION_LOG_NAME,
    LEGACY_RECORDS_DIR,
    USER_RECORDS_DIR,
    copy_legacy_record,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDITION_PATH_ENV = "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH"
DEFAULT_ADDITION_PATH = USER_RECORDS_DIR / ADDITION_LOG_NAME
# Older versions kept the log in output/; it is copied once, never moved.
LEGACY_ADDITION_PATH = LEGACY_RECORDS_DIR / ADDITION_LOG_NAME

SCHEMA_VERSION = "perfume-chem-personal-inventory-addition-event-v1"
DESIGN_ONLY_AUTHORITY = "PERSONAL_INVENTORY_ADDITION_DESIGN_ONLY"
LIVE_TEXT_AUTHORITY = "LEGACY_INVENTORY_TEXT_DESIGN_ONLY"
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

_SOLID_MARKERS = ("crystal", "powder", "solid", "flakes")
_WRITE_LOCK = threading.Lock()


class PersonalInventoryError(ValueError):
    """Invalid or unverifiable personal inventory addition."""

    code = "INVALID_PERSONAL_INVENTORY_ADDITION"


class PersonalInventoryConflictError(PersonalInventoryError):
    """Stale inventory projection or mismatched idempotent command."""

    code = "PERSONAL_INVENTORY_ADDITION_CONFLICT"


@dataclass(frozen=True)
class PersonalInventoryProjection:
    """Union used for creative formulation, never exact physical execution."""

    stocks: tuple[InventoryMaterial, ...]
    requirements: tuple[InventoryRequirement, ...]
    source_workbook_sha256: str
    snapshot_sha256: str
    overlay_sha256: str
    completion_sha256: str
    canonical_effective_inventory_sha256: str
    inventory_text_sha256: str
    addition_log_sha256: str
    effective_inventory_sha256: str
    canonical_stock_ids: frozenset[str]


def addition_log_path(path: Path | None = None) -> Path:
    if path is not None:
        return path.resolve()
    override = os.environ.get(ADDITION_PATH_ENV)
    if override:
        return Path(override).resolve()
    default = DEFAULT_ADDITION_PATH.resolve()
    copy_legacy_record(LEGACY_ADDITION_PATH, default)
    return default


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _event_hash(event: Mapping[str, Any]) -> str:
    return _sha256_text(
        _canonical_json(
            {key: value for key, value in event.items() if key != "event_sha256"}
        )
    )


def _clean_text(value: object, *, field: str, maximum: int = 255) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        raise PersonalInventoryError(f"{field} is required")
    if len(text) > maximum:
        raise PersonalInventoryError(f"{field} exceeds {maximum} characters")
    return text


def _optional_text(value: object, *, field: str, maximum: int = 255) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) > maximum:
        raise PersonalInventoryError(f"{field} exceeds {maximum} characters")
    return text


def _decimal_text(value: object, field: str) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise PersonalInventoryError(f"{field} must be a finite decimal") from error
    if not parsed.is_finite() or parsed <= 0 or parsed > 1:
        raise PersonalInventoryError(
            f"{field} must be greater than 0 and no greater than 1"
        )
    rendered = format(parsed, "f").rstrip("0").rstrip(".")
    return rendered or "0"


def _normalized_identity(stock: InventoryMaterial) -> str:
    identity = normalize_name(stock.identity_name or stock.name)
    probe = " ".join(
        (stock.physical_form, stock.raw_name, stock.name, stock.identity_name)
    ).casefold()
    if any(marker in probe for marker in _SOLID_MARKERS) and "crystal" not in identity:
        return f"{identity} crystals"
    return identity


def personal_inventory_identity_key(stock: InventoryMaterial) -> str:
    """Return the alias- and physical-form-aware identity used by the UI/search."""

    return _normalized_identity(stock)


def _same_stock_form(left: InventoryMaterial, right: InventoryMaterial) -> bool:
    # Compare the normalized product/physical-form identity, not just the base
    # chemical alias.  This keeps Ambrox Super crystals separate from an
    # Ambrox Super solution while still deduplicating 3X/X3 spellings.
    if _normalized_identity(left) != _normalized_identity(right):
        return False
    if abs(float(left.dilution) - float(right.dilution)) > 1e-9:
        return False
    if right.carrier and normalize_name(left.carrier) != normalize_name(right.carrier):
        return False
    if (
        right.fraction_basis not in {"", "unspecified"}
        and left.fraction_basis != right.fraction_basis
    ):
        return False
    return True


def _stock_label_fraction_consistent(
    stock: InventoryMaterial, live_forms: Sequence[InventoryMaterial] = ()
) -> bool:
    """True when the stock's labels as written agree with its stored strength.

    The labels are ``raw_name`` and the source's own name: the display
    ``name`` may be derived from the stored strength, so it always agrees and
    proves nothing.  A label whose stated strengths all differ from the stored
    one is still consistent when inventory.txt lists this material at the
    stored strength.
    """

    if any(
        abs(float(live.dilution) - float(stock.dilution)) <= 1e-9 for live in live_forms
    ):
        return True
    for label in (stock.raw_name, stock.source_name or stock.name):
        label = re.sub(r"\s*#.*$", "", label)  # free-text comment
        label = re.sub(r"\[[^\]]*\]", " ", label)  # the parser's "[0.1]" fraction tag
        stated = [
            float(value.replace(",", ".")) / 100.0
            for value in re.findall(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*%", label)
        ]
        # A label naming several strengths, one of them the stored one, is
        # ambiguous rather than contradictory; the composer handles that case.
        if stated and not any(abs(value - float(stock.dilution)) <= 1e-9 for value in stated):
            return False
    return True


def _live_design_stock(stock: InventoryMaterial) -> InventoryMaterial:
    digest = hashlib.sha256(
        f"{stock.category}|{stock.raw_name}|{stock.name}".encode("utf-8")
    ).hexdigest()[:20]
    usable = stock.status.casefold() == "owned" and stock.dilution > 0
    return replace(
        stock,
        stock_id=f"inventory:text-design-only:{digest}",
        authority=LIVE_TEXT_AUTHORITY,
        execution_ready=False,
        execution_hold_reason="NOT_BOUND_TO_CURRENT_INVENTORY_SNAPSHOT",
        design_ready=usable,
        design_hold_reason=(
            "EXECUTION_STOCK_BINDING_REQUIRED" if usable else "STOCK_FORM_INCOMPLETE"
        ),
    )


def _validate_event(raw: object, *, previous_hash: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PersonalInventoryError("personal inventory addition event must be an object")
    event = dict(raw)
    required = {
        "schema_version",
        "event_id",
        "recorded_at",
        "idempotency_key_sha256",
        "command_sha256",
        "expected_design_inventory_sha256",
        "confirmed_stock",
        "source_kind",
        "user_note",
        "previous_event_sha256",
        "event_sha256",
        *FALSE_ACTION_AUTHORITY,
    }
    if set(event) != required:
        raise PersonalInventoryError("personal inventory addition event shape is invalid")
    if event["schema_version"] != SCHEMA_VERSION:
        raise PersonalInventoryError("personal inventory addition schema is unsupported")
    for field in (
        "idempotency_key_sha256",
        "command_sha256",
        "expected_design_inventory_sha256",
        "event_sha256",
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", str(event[field])):
            raise PersonalInventoryError(f"personal inventory {field} is invalid")
    if str(event["previous_event_sha256"]) != previous_hash:
        raise PersonalInventoryError("personal inventory addition event chain is broken")
    if str(event["event_sha256"]) != _event_hash(event):
        raise PersonalInventoryError("personal inventory addition event hash is invalid")
    if event["source_kind"] not in ALLOWED_SOURCE_KINDS:
        raise PersonalInventoryError("personal inventory source kind is invalid")
    if any(event[field] is not False for field in FALSE_ACTION_AUTHORITY):
        raise PersonalInventoryError("personal inventory addition cannot grant authority")
    stock = event["confirmed_stock"]
    if not isinstance(stock, Mapping):
        raise PersonalInventoryError("personal inventory confirmed stock is invalid")
    expected_stock_fields = {
        "identity_name",
        "category",
        "fraction_decimal",
        "fraction_basis",
        "carrier",
        "physical_form",
        "possession_confirmed",
        "homogeneity",
        "supplier_name",
        "supplier_sku",
    }
    if set(stock) != expected_stock_fields:
        raise PersonalInventoryError("personal inventory confirmed stock shape is invalid")
    _clean_text(stock["identity_name"], field="identity_name")
    _clean_text(stock["category"], field="category")
    fraction = Decimal(_decimal_text(stock["fraction_decimal"], "fraction_decimal"))
    if stock["fraction_basis"] not in ALLOWED_BASES:
        raise PersonalInventoryError("personal inventory fraction basis is invalid")
    if stock["homogeneity"] not in ALLOWED_HOMOGENEITY:
        raise PersonalInventoryError("personal inventory homogeneity is invalid")
    if stock["possession_confirmed"] is not True:
        raise PersonalInventoryError("personal inventory ownership must be confirmed")
    carrier = _optional_text(stock["carrier"], field="carrier")
    _clean_text(stock["physical_form"], field="physical_form", maximum=120)
    _optional_text(stock["supplier_name"], field="supplier_name")
    _optional_text(stock["supplier_sku"], field="supplier_sku", maximum=120)
    if fraction == 1 and (stock["fraction_basis"] != "neat" or carrier):
        raise PersonalInventoryError("a 100% personal stock must be neat with no carrier")
    if fraction < 1 and (
        stock["fraction_basis"] not in {"mass_fraction", "volume_fraction", "mass_per_volume"}
        or not carrier
    ):
        raise PersonalInventoryError("a diluted personal stock needs basis and carrier")
    return event


def load_personal_inventory_addition_events(
    path: Path | None = None,
) -> tuple[dict[str, Any], ...]:
    source = addition_log_path(path)
    if not source.exists():
        return ()
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as error:
        raise PersonalInventoryError(
            f"personal inventory addition log is unreadable: {error}"
        ) from error
    if len(content.encode("utf-8")) > 5_000_000:
        raise PersonalInventoryError("personal inventory addition log exceeds 5 MB")
    events: list[dict[str, Any]] = []
    previous_hash = ""
    idempotency_keys: set[str] = set()
    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise PersonalInventoryError(
                f"personal inventory addition line {line_number} is not valid JSON"
            ) from error
        event = _validate_event(raw, previous_hash=previous_hash)
        key_hash = str(event["idempotency_key_sha256"])
        if key_hash in idempotency_keys:
            raise PersonalInventoryError(
                "personal inventory addition idempotency key is duplicated"
            )
        idempotency_keys.add(key_hash)
        previous_hash = str(event["event_sha256"])
        events.append(event)
    return tuple(events)


def personal_inventory_addition_log_sha256(path: Path | None = None) -> str:
    source = addition_log_path(path)
    if not source.exists():
        return ""
    try:
        return hashlib.sha256(source.read_bytes()).hexdigest()
    except OSError as error:
        raise PersonalInventoryError(
            f"personal inventory addition log is unreadable: {error}"
        ) from error


def _event_stock(event: Mapping[str, Any], *, path: Path | None = None) -> InventoryMaterial:
    values = event["confirmed_stock"]
    fraction = float(Decimal(str(values["fraction_decimal"])))
    identity = str(values["identity_name"])
    carrier = str(values["carrier"])
    form = str(values["physical_form"])
    label = (
        f"{identity} ({fraction * 100:g}% {values['fraction_basis']} in {carrier})"
        if fraction < 1
        else f"{identity} (neat / as supplied)"
    )
    return InventoryMaterial(
        name=identity,
        dilution=fraction,
        category=str(values["category"]),
        raw_name=label,
        status="owned",
        fraction_basis=str(values["fraction_basis"]),
        carrier=carrier,
        physical_form=form,
        approximate=False,
        identity_name=identity,
        stock_id=f"inventory:personal-addition:{str(event['command_sha256'])[:20]}",
        authority=DESIGN_ONLY_AUTHORITY,
        source_ref=f"{addition_log_path(path)}#{event['event_id']}",
        execution_ready=False,
        execution_hold_reason="EXACT_PHYSICAL_STOCK_BINDING_REQUIRED",
        design_ready=True,
        design_hold_reason="EXECUTION_STOCK_BINDING_REQUIRED",
        completion_event_sha256=str(event["event_sha256"]),
        completion_source_ref=f"{addition_log_path(path)}#{event['event_id']}",
        homogeneity=str(values["homogeneity"]),
    )


def materialize_personal_inventory(
    *,
    canonical: CurrentInventoryMaterialization | None = None,
    addition_path: Path | None = None,
) -> PersonalInventoryProjection:
    """Return the complete personal-design view with explicit authority tiers."""

    governed = canonical or materialize_current_inventory()
    live_owned = tuple(
        stock
        for stock in parse_inventory(unique=False, include_unavailable=False)
        if stock.status.casefold() == "owned"
    )
    live_by_identity: dict[str, list[InventoryMaterial]] = {}
    for stock in live_owned:
        live_by_identity.setdefault(_normalized_identity(stock), []).append(stock)

    bound: list[InventoryMaterial] = []
    for stock in governed.stocks:
        live_forms = live_by_identity.get(_normalized_identity(stock), [])
        # A dilution prepared on the Stock page is not in inventory.txt by design,
        # and a Stock page entry that changed the strength, basis or carrier wins
        # over the old inventory.txt form, so its row and disagreement stay shown.
        prepared = stock.authority == PREPARED_DILUTION_AUTHORITY
        overridden = bool(stock.authority_facts_differ)
        # Stock page facts are the user's own record and the gate counts them,
        # so a name still stating the workbook strength must not hide the row.
        user_recorded = prepared or bool(stock.completion_event_sha256)
        if not user_recorded and not _stock_label_fraction_consistent(stock, live_forms):
            continue
        if not prepared and not overridden and live_forms and not any(
            _same_stock_form(stock, live) for live in live_forms
        ):
            continue
        bound.append(stock)

    projected: list[InventoryMaterial] = list(bound)
    for stock in live_owned:
        if any(_same_stock_form(existing, stock) for existing in projected):
            continue
        projected.append(_live_design_stock(stock))

    events = load_personal_inventory_addition_events(addition_path)
    for event in events:
        addition = _event_stock(event, path=addition_path)
        matching = [
            index
            for index, existing in enumerate(projected)
            if _same_stock_form(existing, addition)
        ]
        if matching:
            # A governed stock remains stronger.  A direct personal receipt may
            # replace only the lower-authority live-text projection.
            if all(projected[index].authority == LIVE_TEXT_AUTHORITY for index in matching):
                first = matching[0]
                projected[first] = addition
                for index in reversed(matching[1:]):
                    projected.pop(index)
            continue
        projected.append(addition)

    held_stocks, hold_sha = apply_user_compounding_holds(tuple(projected))
    # inventory.txt lines and personal additions join the governed stocks here,
    # so names are settled again: one owned name still means one bottle.
    projected = list(assign_stock_display_names(held_stocks))
    projected.sort(
        key=lambda stock: (
            stock.category.casefold(),
            normalize_name(stock.identity_name or stock.name),
            -float(stock.dilution),
            stock.stock_id,
        )
    )
    inventory_text_sha = _file_sha256(INVENTORY_PATH)
    addition_sha = personal_inventory_addition_log_sha256(addition_path)
    projection_payload = {
        "canonical_effective_inventory_sha256": governed.effective_inventory_sha256,
        "inventory_text_sha256": inventory_text_sha,
        "addition_log_sha256": addition_sha,
        "compounding_holds_sha256": hold_sha,
        "stock_rows": [
            {
                "stock_id": stock.stock_id,
                "identity": normalize_name(stock.identity_name or stock.name),
                "fraction": format(float(stock.dilution), ".12g"),
                "basis": stock.fraction_basis,
                "carrier": normalize_name(stock.carrier),
                "authority": stock.authority,
            }
            for stock in projected
        ],
    }
    return PersonalInventoryProjection(
        stocks=tuple(projected),
        requirements=governed.requirements,
        source_workbook_sha256=governed.source_workbook_sha256,
        snapshot_sha256=governed.snapshot_sha256,
        overlay_sha256=governed.overlay_sha256,
        completion_sha256=governed.completion_sha256,
        canonical_effective_inventory_sha256=governed.effective_inventory_sha256,
        inventory_text_sha256=inventory_text_sha,
        addition_log_sha256=addition_sha,
        effective_inventory_sha256=_sha256_text(_canonical_json(projection_payload)),
        canonical_stock_ids=frozenset(stock.stock_id for stock in governed.stocks),
    )


def _normalize_command(
    *,
    identity_name: object,
    category: object,
    fraction_decimal: object,
    fraction_basis: object,
    carrier: object,
    physical_form: object,
    possession_confirmed: bool,
    homogeneity: object,
    source_kind: object,
    supplier_name: object,
    supplier_sku: object,
    user_note: object,
) -> dict[str, Any]:
    identity = _clean_text(identity_name, field="identity_name")
    clean_category = _clean_text(category, field="category")
    fraction = _decimal_text(fraction_decimal, "fraction_decimal")
    basis = _clean_text(fraction_basis, field="fraction_basis").casefold()
    clean_carrier = _optional_text(carrier, field="carrier").casefold()
    clean_form = _clean_text(
        physical_form, field="physical_form", maximum=120
    ).casefold()
    clean_homogeneity = _clean_text(homogeneity, field="homogeneity", maximum=80).upper()
    clean_source = _clean_text(source_kind, field="source_kind", maximum=80).upper()
    if basis not in ALLOWED_BASES:
        raise PersonalInventoryError("fraction_basis is unsupported")
    if clean_homogeneity not in ALLOWED_HOMOGENEITY:
        raise PersonalInventoryError("homogeneity is unsupported")
    if clean_source not in ALLOWED_SOURCE_KINDS:
        raise PersonalInventoryError("source_kind is unsupported")
    if possession_confirmed is not True:
        raise PersonalInventoryError("confirm physical ownership before adding a material")
    parsed_fraction = Decimal(fraction)
    if parsed_fraction == 1 and (basis != "neat" or clean_carrier):
        raise PersonalInventoryError("a 100% stock must use neat basis with no carrier")
    if parsed_fraction < 1 and (
        basis not in {"mass_fraction", "volume_fraction", "mass_per_volume"}
        or not clean_carrier
    ):
        raise PersonalInventoryError("a diluted stock needs its basis and carrier")
    return {
        "confirmed_stock": {
            "identity_name": identity,
            "category": clean_category,
            "fraction_decimal": fraction,
            "fraction_basis": basis,
            "carrier": clean_carrier,
            "physical_form": clean_form,
            "possession_confirmed": True,
            "homogeneity": clean_homogeneity,
            "supplier_name": _optional_text(supplier_name, field="supplier_name"),
            "supplier_sku": _optional_text(
                supplier_sku, field="supplier_sku", maximum=120
            ),
        },
        "source_kind": clean_source,
        "user_note": _optional_text(user_note, field="user_note", maximum=1000),
    }


def record_personal_inventory_addition(
    *,
    expected_design_inventory_sha256: str,
    idempotency_key: str,
    identity_name: object,
    category: object,
    fraction_decimal: object,
    fraction_basis: object,
    carrier: object,
    physical_form: object,
    possession_confirmed: bool,
    homogeneity: object,
    source_kind: object,
    supplier_name: object = "",
    supplier_sku: object = "",
    user_note: object = "",
    path: Path | None = None,
) -> tuple[dict[str, Any], PersonalInventoryProjection]:
    """Append one user-confirmed owned stock for personal formulation."""

    if not re.fullmatch(r"[0-9a-f]{64}", expected_design_inventory_sha256):
        raise PersonalInventoryError("expected_design_inventory_sha256 is invalid")
    clean_key = _clean_text(idempotency_key, field="idempotency_key")
    key_hash = _sha256_text(clean_key)
    command = _normalize_command(
        identity_name=identity_name,
        category=category,
        fraction_decimal=fraction_decimal,
        fraction_basis=fraction_basis,
        carrier=carrier,
        physical_form=physical_form,
        possession_confirmed=possession_confirmed,
        homogeneity=homogeneity,
        source_kind=source_kind,
        supplier_name=supplier_name,
        supplier_sku=supplier_sku,
        user_note=user_note,
    )
    command_sha = _sha256_text(_canonical_json(command))
    source = addition_log_path(path)

    with _WRITE_LOCK:
        events = load_personal_inventory_addition_events(source)
        current = materialize_personal_inventory(addition_path=source)
        for existing in events:
            if existing["idempotency_key_sha256"] != key_hash:
                continue
            if existing["command_sha256"] != command_sha:
                raise PersonalInventoryConflictError(
                    "idempotency key was already used for a different inventory addition"
                )
            return dict(existing), current
        if current.effective_inventory_sha256 != expected_design_inventory_sha256:
            raise PersonalInventoryConflictError(
                "inventory changed after this editor was opened; refresh and review"
            )
        probe = InventoryMaterial(
            name=str(command["confirmed_stock"]["identity_name"]),
            dilution=float(Decimal(str(command["confirmed_stock"]["fraction_decimal"]))),
            category=str(command["confirmed_stock"]["category"]),
            raw_name=str(command["confirmed_stock"]["identity_name"]),
            status="owned",
            fraction_basis=str(command["confirmed_stock"]["fraction_basis"]),
            carrier=str(command["confirmed_stock"]["carrier"]),
            physical_form=str(command["confirmed_stock"]["physical_form"]),
            identity_name=str(command["confirmed_stock"]["identity_name"]),
        )
        if any(_same_stock_form(stock, probe) for stock in current.stocks):
            raise PersonalInventoryConflictError(
                "that owned material and stock form is already in the personal inventory"
            )
        previous_hash = str(events[-1]["event_sha256"]) if events else ""
        recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        event_core: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_id": "personal-inventory-addition-" + command_sha[:20],
            "recorded_at": recorded_at,
            "idempotency_key_sha256": key_hash,
            "command_sha256": command_sha,
            "expected_design_inventory_sha256": expected_design_inventory_sha256,
            "confirmed_stock": command["confirmed_stock"],
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
            raise PersonalInventoryError(
                f"personal inventory addition could not be persisted: {error}"
            ) from error
        return event, materialize_personal_inventory(addition_path=source)


__all__ = [
    "ADDITION_PATH_ENV",
    "DESIGN_ONLY_AUTHORITY",
    "LIVE_TEXT_AUTHORITY",
    "PersonalInventoryConflictError",
    "PersonalInventoryError",
    "PersonalInventoryProjection",
    "addition_log_path",
    "load_personal_inventory_addition_events",
    "materialize_personal_inventory",
    "personal_inventory_identity_key",
    "personal_inventory_addition_log_sha256",
    "record_personal_inventory_addition",
]
