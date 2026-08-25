"""Typed V5 stock-authority spine for formula dose and physical-run binding.

This module implements the authority chain:

V5InventorySnapshot -> exact inventory-row binding -> FormulaDoseLineReceipt
-> FormulaDoseReceipt -> PreparedRun

The TARGET / IDEAL formula remains outside this chain. This spine governs only
current-inventory quantitative computation and downstream physical execution.

Project semantics preserved here:
- HOLD is not an inventory absence state. Ownership is supplied explicitly by
  the V5 authority adapter.
- an unresolved ExactStockRef never erases ownership;
- no missing fraction becomes an implicit neat stock;
- product-basis material is never converted into a fictional active fraction;
- mass-basis stocks are not mislabeled as active volume;
- PreparedRun grants no sensory, liking, safety, stability, or release authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from engine.pipeline.preflight import FormulaDoseLineReceipt, FormulaDoseReceipt


V5_AUTHORITY_FILENAME = "Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx"
V5_AUTHORITY_SHA256 = "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
V5_AUTHORITY_VERSION = "V5"

CURRENT_INVENTORY_BUILD = "CURRENT_INVENTORY_BUILD"
PHYSICAL_EXECUTION = "PHYSICAL_EXECUTION"


class StockAuthorityError(ValueError):
    """Raised when the stock-authority chain cannot be established safely."""


def _text(value: object) -> str:
    return str(value or "").strip()


def _norm(value: object) -> str:
    return " ".join(_text(value).casefold().split())


def _stable_hash(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _valid_sha256(value: object) -> bool:
    text = _text(value).lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _finite_nonnegative(value: object, *, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise StockAuthorityError(f"{label} must be numeric") from exc
    if not math.isfinite(number) or number < 0:
        raise StockAuthorityError(f"{label} must be finite and nonnegative")
    return number


def _fraction(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = _text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        return None
    return number


def _basis(value: object) -> str:
    raw = _norm(value).replace(" ", "_")
    aliases = {
        "vv": "volume_fraction",
        "v/v": "volume_fraction",
        "volume": "volume_fraction",
        "volume_fraction": "volume_fraction",
        "neat": "neat",
        "pure": "neat",
        "undiluted": "neat",
        "ww": "mass_fraction",
        "w/w": "mass_fraction",
        "mass_fraction": "mass_fraction",
        "wv": "mass_per_volume",
        "w/v": "mass_per_volume",
        "mass_per_volume": "mass_per_volume",
        "product_basis": "product_basis",
        "product-basis": "product_basis",
    }
    return aliases.get(raw, raw or "unspecified")


@dataclass(frozen=True, slots=True)
class V5StockRecord:
    """One normalized stock identity derived from V5 authority evidence."""

    material: str
    stock_description: str
    active_fraction: float | None
    fraction_basis: str
    carrier: str
    inventory_owned: bool
    product_basis: bool
    exact_stock_ref: str | None
    source_row: int

    def __post_init__(self) -> None:
        if not _text(self.material):
            raise StockAuthorityError("stock material must not be blank")
        if int(self.source_row) <= 0:
            raise StockAuthorityError(f"{self.material}: source_row must be positive")
        object.__setattr__(self, "source_row", int(self.source_row))
        parsed_fraction = _fraction(self.active_fraction)
        if self.active_fraction is not None and parsed_fraction is None:
            raise StockAuthorityError(
                f"{self.material}: active_fraction must be within [0, 1]"
            )
        object.__setattr__(self, "active_fraction", parsed_fraction)
        object.__setattr__(self, "fraction_basis", _basis(self.fraction_basis))
        object.__setattr__(self, "carrier", _text(self.carrier))
        ref = _text(self.exact_stock_ref)
        object.__setattr__(self, "exact_stock_ref", ref or None)
        if self.product_basis:
            object.__setattr__(self, "fraction_basis", "product_basis")

    def normalized_payload(self) -> dict[str, Any]:
        return {
            "material": self.material,
            "stock_description": self.stock_description,
            "active_fraction": self.active_fraction,
            "fraction_basis": self.fraction_basis,
            "carrier": self.carrier,
            "inventory_owned": bool(self.inventory_owned),
            "product_basis": bool(self.product_basis),
            "exact_stock_ref": self.exact_stock_ref,
            "source_row": self.source_row,
        }


@dataclass(frozen=True, slots=True)
class V5InventorySnapshot:
    """Immutable V5-derived inventory snapshot with exact source provenance."""

    authority_filename: str
    authority_sha256: str
    authority_sheet: str
    records: tuple[V5StockRecord, ...]
    snapshot_sha256: str

    @classmethod
    def build(
        cls,
        *,
        authority_filename: str,
        authority_sha256: str,
        authority_sheet: str,
        records: Sequence[V5StockRecord],
    ) -> "V5InventorySnapshot":
        if _text(authority_filename) != V5_AUTHORITY_FILENAME:
            raise StockAuthorityError(
                "inventory snapshot must bind the canonical V5 authority filename"
            )
        if _text(authority_sha256).lower() != V5_AUTHORITY_SHA256:
            raise StockAuthorityError(
                "inventory snapshot V5 workbook SHA-256 does not match authority"
            )
        if not _valid_sha256(authority_sha256):
            raise StockAuthorityError("inventory authority SHA-256 is invalid")
        if not _text(authority_sheet):
            raise StockAuthorityError("inventory authority sheet must not be blank")
        normalized = tuple(records)
        if not normalized:
            raise StockAuthorityError("inventory snapshot requires at least one record")
        seen: dict[str, V5StockRecord] = {}
        for record in normalized:
            key = _norm(record.material)
            if key in seen:
                raise StockAuthorityError(
                    f"duplicate canonical stock row: {record.material}"
                )
            seen[key] = record
        payload = {
            "schema": "v5-inventory-snapshot-v1",
            "authority_filename": V5_AUTHORITY_FILENAME,
            "authority_sha256": V5_AUTHORITY_SHA256,
            "authority_version": V5_AUTHORITY_VERSION,
            "authority_sheet": _text(authority_sheet),
            "records": [
                record.normalized_payload()
                for record in sorted(normalized, key=lambda row: _norm(row.material))
            ],
        }
        return cls(
            authority_filename=V5_AUTHORITY_FILENAME,
            authority_sha256=V5_AUTHORITY_SHA256,
            authority_sheet=_text(authority_sheet),
            records=normalized,
            snapshot_sha256=_stable_hash(payload),
        )

    def resolve(self, material: str) -> V5StockRecord | None:
        key = _norm(material)
        matches = [row for row in self.records if _norm(row.material) == key]
        if len(matches) > 1:
            raise StockAuthorityError(f"ambiguous V5 stock identity: {material}")
        return matches[0] if matches else None

    def stock_id(self, record: V5StockRecord) -> str:
        return "v5row:" + _stable_hash(
            {
                "snapshot_sha256": self.snapshot_sha256,
                "material": record.material,
                "source_row": record.source_row,
            }
        )[:24]


@dataclass(frozen=True, slots=True)
class ExactStockRef:
    """Explicit physical bottle or prepared-stock reference.

    This object cannot be synthesized merely from an ownership/HOLD state.
    """

    ref_id: str
    material: str
    inventory_snapshot_sha256: str
    source_row: int
    stock_description: str
    active_fraction: float | None
    fraction_basis: str
    carrier: str

    @classmethod
    def from_record(
        cls,
        snapshot: V5InventorySnapshot,
        record: V5StockRecord,
    ) -> "ExactStockRef":
        if not record.inventory_owned:
            raise StockAuthorityError(
                f"{record.material}: cannot bind physical stock for unowned inventory"
            )
        if not _text(record.exact_stock_ref):
            raise StockAuthorityError(
                f"{record.material}: ExactStockRef is unresolved"
            )
        return cls(
            ref_id=_text(record.exact_stock_ref),
            material=record.material,
            inventory_snapshot_sha256=snapshot.snapshot_sha256,
            source_row=record.source_row,
            stock_description=record.stock_description,
            active_fraction=record.active_fraction,
            fraction_basis=record.fraction_basis,
            carrier=record.carrier,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "material": self.material,
            "inventory_snapshot_sha256": self.inventory_snapshot_sha256,
            "source_row": self.source_row,
            "stock_description": self.stock_description,
            "active_fraction": self.active_fraction,
            "fraction_basis": self.fraction_basis,
            "carrier": self.carrier,
        }


@dataclass(frozen=True, slots=True)
class PreparedRun:
    """Physical-run binding built only after exact refs exist for every dose line."""

    run_id: str
    formula_receipt_sha256: str
    inventory_snapshot_sha256: str
    exact_stock_refs: tuple[ExactStockRef, ...]
    status: str = "BOUND"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "prepared-run-v1",
            "run_id": self.run_id,
            "formula_receipt_sha256": self.formula_receipt_sha256,
            "inventory_snapshot_sha256": self.inventory_snapshot_sha256,
            "exact_stock_refs": [ref.as_dict() for ref in self.exact_stock_refs],
            "status": self.status,
            "physical_metrology_authority": False,
            "sensory_authority": False,
            "liking_authority": False,
            "safety_authority": False,
            "stability_authority": False,
            "release_authority": False,
        }


def _line_from_record(
    *,
    formula_material: str,
    raw_ul: float,
    record: V5StockRecord | None,
    snapshot: V5InventorySnapshot,
) -> FormulaDoseLineReceipt:
    blockers: list[str] = []
    if record is None:
        return FormulaDoseLineReceipt(
            material_name=formula_material,
            raw_ul=raw_ul,
            active_ul=None,
            stock_fraction=None,
            fraction_basis="unspecified",
            carrier="",
            stock_id=None,
            stock_authority=None,
            inventory_authority=(
                f"{snapshot.authority_filename}@{snapshot.authority_sha256}"
            ),
            source_rows=(),
            status="ABSTAINED",
            blockers=("not_in_v5_inventory_snapshot",),
        )

    fraction = record.active_fraction
    basis = record.fraction_basis
    active_ul: float | None = None

    if not record.inventory_owned:
        blockers.append("inventory_not_owned")
    if record.product_basis or basis == "product_basis":
        blockers.append("product_basis_active_equivalent_not_defined")
    elif fraction is None:
        blockers.append("stock_fraction_unknown")
    elif basis in {"neat", "volume_fraction"}:
        active_ul = raw_ul * fraction
    elif basis in {"mass_fraction", "mass_per_volume"}:
        blockers.append("mass_basis_requires_mass_quantity_model")
    else:
        blockers.append("stock_fraction_basis_unknown")

    status = "BOUND" if not blockers else "ABSTAINED"
    return FormulaDoseLineReceipt(
        material_name=formula_material,
        raw_ul=raw_ul,
        active_ul=active_ul if status == "BOUND" else None,
        stock_fraction=fraction,
        fraction_basis=basis,
        carrier=record.carrier,
        stock_id=snapshot.stock_id(record),
        stock_authority="V5_INVENTORY_ROW",
        inventory_authority=(
            f"{snapshot.authority_filename}@{snapshot.authority_sha256}"
        ),
        source_rows=(record.source_row,),
        status=status,
        blockers=tuple(blockers),
    )


def build_formula_dose_receipt_from_snapshot(
    formula: Mapping[str, Any],
    snapshot: V5InventorySnapshot,
) -> FormulaDoseReceipt:
    """Build the existing FormulaDoseReceipt from one immutable V5 snapshot.

    No fuzzy matching is performed. An optional ``stock_bindings`` mapping may
    explicitly map a formula row name to a V5 stock row name.
    """

    ingredients = dict(formula.get("ingredients_ul", {}) or {})
    if not ingredients:
        raise StockAuthorityError("formula has no ingredients_ul")
    bindings = {
        str(name): str(value)
        for name, value in dict(formula.get("stock_bindings", {}) or {}).items()
    }
    lines: list[FormulaDoseLineReceipt] = []
    reasons: list[str] = []
    for raw_name, raw_amount in sorted(
        ingredients.items(), key=lambda item: _norm(item[0])
    ):
        name = _text(raw_name)
        if not name:
            raise StockAuthorityError("formula material name must not be blank")
        raw_ul = _finite_nonnegative(raw_amount, label=f"{name} raw_ul")
        if raw_ul == 0.0:
            continue
        requested_stock = bindings.get(name, name)
        record = snapshot.resolve(requested_stock)
        line = _line_from_record(
            formula_material=name,
            raw_ul=raw_ul,
            record=record,
            snapshot=snapshot,
        )
        lines.append(line)
        reasons.extend(f"{name}:{blocker}" for blocker in line.blockers)

    if not lines:
        raise StockAuthorityError("formula has no positive ingredient doses")

    input_payload = {
        "name": _text(formula.get("name")) or "Formula",
        "ingredients_ul": {
            str(name): float(value or 0.0)
            for name, value in ingredients.items()
        },
        "stock_bindings": bindings,
        "inventory_snapshot_sha256": snapshot.snapshot_sha256,
    }
    input_hash = _stable_hash(input_payload)
    return FormulaDoseReceipt(
        formula_name=_text(formula.get("name")) or "Formula",
        formula_input_sha256=input_hash,
        legacy_formula_hash=input_hash,
        inventory_snapshot_sha256=snapshot.snapshot_sha256,
        inventory_source_workbook_sha256=snapshot.authority_sha256,
        inventory_authority_sheet=snapshot.authority_sheet,
        lines=tuple(lines),
        status="BOUND" if lines and not reasons else "ABSTAINED",
        reasons=tuple(reasons),
    )


def prepare_run(
    run_id: str,
    receipt: FormulaDoseReceipt,
    snapshot: V5InventorySnapshot,
) -> PreparedRun:
    """Bind a quantitative receipt to explicit physical stock references."""

    if not _text(run_id):
        raise StockAuthorityError("prepared run_id must not be blank")
    if receipt.status != "BOUND":
        raise StockAuthorityError(
            "PreparedRun requires a BOUND FormulaDoseReceipt"
        )
    if receipt.inventory_snapshot_sha256 != snapshot.snapshot_sha256:
        raise StockAuthorityError(
            "FormulaDoseReceipt inventory snapshot does not match PreparedRun snapshot"
        )

    refs: list[ExactStockRef] = []
    for line in receipt.lines:
        if line.status != "BOUND":
            raise StockAuthorityError(
                f"{line.material_name}: dose line is not bound"
            )
        record = snapshot.resolve(line.material_name)
        if record is None:
            raise StockAuthorityError(
                f"{line.material_name}: stock row missing from PreparedRun snapshot"
            )
        refs.append(ExactStockRef.from_record(snapshot, record))

    return PreparedRun(
        run_id=_text(run_id),
        formula_receipt_sha256=receipt.receipt_sha256,
        inventory_snapshot_sha256=snapshot.snapshot_sha256,
        exact_stock_refs=tuple(refs),
    )


def require_formula_state_authority(
    receipt: FormulaDoseReceipt,
    *,
    scope: str,
    prepared_run: PreparedRun | None = None,
) -> bool:
    """Fail closed before FormulaState construction.

    CURRENT_INVENTORY_BUILD requires a quantitative V5-bound formula receipt.
    PHYSICAL_EXECUTION additionally requires a PreparedRun bound to the same
    receipt. TARGET/IDEAL is intentionally not handled here because inventory
    must never gate or rewrite the target.
    """

    scope_name = _text(scope).upper()
    if scope_name == CURRENT_INVENTORY_BUILD:
        if receipt.status != "BOUND":
            raise StockAuthorityError(
                "FormulaState blocked: FormulaDoseReceipt is not quantitatively bound"
            )
        return True
    if scope_name == PHYSICAL_EXECUTION:
        if receipt.status != "BOUND":
            raise StockAuthorityError(
                "Physical FormulaState blocked: FormulaDoseReceipt is not bound"
            )
        if prepared_run is None or prepared_run.status != "BOUND":
            raise StockAuthorityError(
                "Physical FormulaState blocked: PreparedRun is missing or unbound"
            )
        if prepared_run.formula_receipt_sha256 != receipt.receipt_sha256:
            raise StockAuthorityError(
                "Physical FormulaState blocked: PreparedRun receipt hash mismatch"
            )
        return True
    raise StockAuthorityError(
        f"unsupported FormulaState authority scope: {scope_name}; "
        "TARGET_IDEAL must remain inventory-independent"
    )
