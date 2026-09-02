"""Stock-basis repair and computational formula admission.

This module repairs known parser mistakes where a diluted current stock was
incorrectly represented as fraction=1.0. It admits exact generated formula values
for computational provenance only, computes planned active-equivalent shares, and
keeps physical FormulaDoseReceipt authority fail-closed until ExactStockRefs exist.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence


EXACT_V5_SHA256 = "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"


@dataclass(frozen=True, slots=True)
class RepairRule:
    material: str
    fraction: float
    basis: str
    carrier: str | None


@dataclass(frozen=True, slots=True)
class RowStock:
    material: str
    registration_share: float
    fraction: float
    basis: str
    carrier: str | None
    exact_stock_ref_state: str
    product_basis: bool = False
    active_equivalent_fraction: float | None = None


def apply_repair(row: RowStock, rule: RepairRule | None) -> RowStock:
    if rule is None:
        return row
    return RowStock(
        material=row.material,
        registration_share=row.registration_share,
        fraction=rule.fraction,
        basis=rule.basis,
        carrier=rule.carrier,
        exact_stock_ref_state=row.exact_stock_ref_state,
        product_basis=row.product_basis,
        active_equivalent_fraction=row.active_equivalent_fraction,
    )


def planned_active_equivalent(row: RowStock) -> float:
    if row.product_basis:
        if row.active_equivalent_fraction is not None:
            raise ValueError("PRODUCT_BASIS_ACTIVE_EQUIVALENT_INFERRED")
        raise ValueError("PRODUCT_BASIS_ACTIVE_EQUIVALENCE_WITHHELD")
    if row.fraction <= 0 or row.fraction > 1:
        raise ValueError("INVALID_STOCK_FRACTION")
    if not row.basis:
        raise ValueError("STOCK_FRACTION_BASIS_REQUIRED")
    return row.registration_share * row.fraction


def stock_basis_state(row: RowStock) -> str:
    if row.fraction <= 0 or row.fraction > 1 or not row.basis:
        return "FAIL_STOCK_BASIS"
    if row.fraction < 1 and not row.carrier:
        return "PASS_ACTIVE_EQUIVALENCE__HOLD_CARRIER_LINEAGE"
    return "PASS_COMPLETE"


def physical_formula_dose_receipt_state(rows: Sequence[RowStock]) -> str:
    if any(row.exact_stock_ref_state != "PASS" for row in rows):
        return "HOLD_EXACTSTOCKREF"
    if any(stock_basis_state(row) == "FAIL_STOCK_BASIS" for row in rows):
        return "HOLD_STOCK_BASIS"
    return "ELIGIBLE_FOR_PHYSICAL_FDR_CONSTRUCTION__NOT_RELEASE"


def definition_receipt(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def choose_first_pilot(formulas: Sequence[Mapping[str, object]]) -> str:
    ranked = sorted(
        formulas,
        key=lambda f: (
            int(f["carrier_open_rows"]),
            int(f["corrected_row_uses"]),
            int(f.get("product_basis_rows", 0)),
            str(f["formula_id"]),
        ),
    )
    return str(ranked[0]["formula_id"])


def validate_v5_sha256(observed: str) -> None:
    if observed != EXACT_V5_SHA256:
        raise ValueError("CURRENT_V5_SHA256_MISMATCH")
