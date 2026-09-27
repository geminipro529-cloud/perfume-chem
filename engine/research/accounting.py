"""Exact stock-row accounting without cross-unit invention.

The functions in this module are deliberately narrower than a formula parser.
They operate on already-adjudicated product and stock identities and return
partial/withheld results when a required density or basis is unavailable.
Volume and mass totals are always retained separately, even when a complete
active-mass conversion is possible.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .contracts import (
    FALSE_ACTION_AUTHORITY,
    FormulaSnapshotV1,
    ProductIdentityV1,
    StockLotV1,
    decimal_text,
)


@dataclass(frozen=True, slots=True)
class AccountedFormulaRowV1:
    row_id: str
    product_id: str
    material_id: str
    stock_id: str | None
    source_amount_decimal: str
    source_unit: str
    stock_mass_g_decimal: str | None
    stock_volume_ml_decimal: str | None
    active_mass_g_decimal: str | None
    carrier_mass_g_decimal: str | None
    applicability_state: str
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _quantity_in_base_units(amount: str, unit: str) -> tuple[Decimal | None, Decimal | None]:
    value = Decimal(amount)
    if unit == "uL":
        return None, value / Decimal("1000")
    if unit == "mL":
        return None, value
    if unit == "mg":
        return value / Decimal("1000"), None
    if unit == "g":
        return value, None
    raise ValueError(f"unsupported physical unit: {unit}")


def _active_mass(
    *,
    mass_g: Decimal | None,
    volume_ml: Decimal | None,
    stock: StockLotV1,
    active_density_g_ml: Decimal | None,
) -> tuple[Decimal | None, Decimal | None, list[str]]:
    """Return active mass, carrier mass, and fail-closed reason codes."""

    fraction = Decimal(stock.fraction_decimal)
    stock_density = (
        Decimal(stock.density_g_ml_decimal)
        if stock.density_g_ml_decimal is not None
        else None
    )
    reasons: list[str] = []

    if stock.basis == "UNKNOWN":
        return None, None, ["STOCK_BASIS_UNKNOWN"]

    resolved_stock_mass = mass_g
    if resolved_stock_mass is None and volume_ml is not None and stock_density is not None:
        resolved_stock_mass = volume_ml * stock_density

    if stock.basis in {"W_W", "NEAT"}:
        if resolved_stock_mass is None:
            reasons.append("STOCK_DENSITY_REQUIRED_FOR_VOLUME_TO_MASS")
            return None, None, reasons
        active = resolved_stock_mass * fraction
        carrier = resolved_stock_mass - active
        return active, carrier, reasons

    resolved_stock_volume = volume_ml
    if resolved_stock_volume is None and mass_g is not None:
        if stock_density is None:
            return None, None, ["STOCK_DENSITY_REQUIRED_FOR_MASS_TO_VOLUME"]
        resolved_stock_volume = mass_g / stock_density

    if stock.basis == "W_V":
        if resolved_stock_volume is None:
            return None, None, ["STOCK_VOLUME_UNAVAILABLE"]
        active = resolved_stock_volume * fraction
        carrier = (
            resolved_stock_mass - active
            if resolved_stock_mass is not None
            else None
        )
        if carrier is not None and carrier < 0:
            return None, None, ["STOCK_COMPOSITION_MASS_INCONSISTENT"]
        return active, carrier, reasons

    if stock.basis == "V_V":
        if resolved_stock_volume is None:
            return None, None, ["STOCK_VOLUME_UNAVAILABLE"]
        if active_density_g_ml is None:
            return None, None, ["ACTIVE_PRODUCT_DENSITY_REQUIRED_FOR_V_V"]
        active = resolved_stock_volume * fraction * active_density_g_ml
        carrier = (
            resolved_stock_mass - active
            if resolved_stock_mass is not None
            else None
        )
        if carrier is not None and carrier < 0:
            return None, None, ["STOCK_COMPOSITION_MASS_INCONSISTENT"]
        return active, carrier, reasons

    return None, None, ["STOCK_BASIS_UNSUPPORTED"]


def account_formula_snapshot(
    snapshot: FormulaSnapshotV1,
    *,
    products: Sequence[ProductIdentityV1],
    stocks: Sequence[StockLotV1],
    active_product_density_g_ml: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve exact row accounting while preserving unknowns and source rows.

    ``active_product_density_g_ml`` is keyed by product ID and is used only for
    v/v-to-mass conversion.  It is never inferred from the stock density.
    """

    product_by_id = {item.product_id: item for item in products}
    stock_by_id = {item.stock_id: item for item in stocks}
    densities: dict[str, Decimal] = {}
    for product_id, value in (active_product_density_g_ml or {}).items():
        normalized = decimal_text(value, f"density for {product_id}", positive=True)
        densities[str(product_id)] = Decimal(normalized)

    rows: list[AccountedFormulaRowV1] = []
    physical_totals: dict[str, Decimal] = defaultdict(Decimal)
    active_by_material: dict[str, Decimal] = defaultdict(Decimal)
    missing: list[dict[str, Any]] = []
    positive_rows = 0
    covered_rows = 0

    for component in snapshot.components:
        positive_rows += 1
        physical_totals[component.amount_unit] += Decimal(component.amount_decimal)
        product = product_by_id.get(component.product_id)
        reasons: list[str] = []
        material_id = product.material_id if product is not None else component.product_id
        if product is None:
            reasons.append("PRODUCT_IDENTITY_NOT_BOUND")
        stock = stock_by_id.get(component.stock_id) if component.stock_id else None
        if component.stock_id is None:
            reasons.append("STOCK_ID_NOT_BOUND")
        elif stock is None:
            reasons.append("STOCK_ID_UNKNOWN")
        elif stock.product_id != component.product_id:
            reasons.append("STOCK_PRODUCT_ID_MISMATCH")

        mass_g, volume_ml = _quantity_in_base_units(
            component.amount_decimal, component.amount_unit
        )
        active: Decimal | None = None
        carrier: Decimal | None = None
        if not reasons and stock is not None:
            active, carrier, conversion_reasons = _active_mass(
                mass_g=mass_g,
                volume_ml=volume_ml,
                stock=stock,
                active_density_g_ml=densities.get(component.product_id),
            )
            reasons.extend(conversion_reasons)

        if active is not None and not reasons:
            covered_rows += 1
            active_by_material[material_id] += active
        else:
            missing.append({"row_id": component.row_id, "reason_codes": sorted(set(reasons))})

        rows.append(
            AccountedFormulaRowV1(
                row_id=component.row_id,
                product_id=component.product_id,
                material_id=material_id,
                stock_id=component.stock_id,
                source_amount_decimal=component.amount_decimal,
                source_unit=component.amount_unit,
                stock_mass_g_decimal=(
                    decimal_text(mass_g, "stock_mass_g", nonnegative=True)
                    if mass_g is not None
                    else (
                        decimal_text(
                            volume_ml * Decimal(stock.density_g_ml_decimal),
                            "stock_mass_g",
                            nonnegative=True,
                        )
                        if volume_ml is not None
                        and stock is not None
                        and stock.density_g_ml_decimal is not None
                        else None
                    )
                ),
                stock_volume_ml_decimal=(
                    decimal_text(volume_ml, "stock_volume_ml", nonnegative=True)
                    if volume_ml is not None
                    else (
                        decimal_text(
                            mass_g / Decimal(stock.density_g_ml_decimal),
                            "stock_volume_ml",
                            nonnegative=True,
                        )
                        if mass_g is not None
                        and stock is not None
                        and stock.density_g_ml_decimal is not None
                        else None
                    )
                ),
                active_mass_g_decimal=(
                    decimal_text(active, "active_mass_g", nonnegative=True)
                    if active is not None and not reasons
                    else None
                ),
                carrier_mass_g_decimal=(
                    decimal_text(carrier, "carrier_mass_g", nonnegative=True)
                    if carrier is not None and not reasons
                    else None
                ),
                applicability_state="APPLICABLE" if active is not None and not reasons else "UNAVAILABLE",
                reason_codes=tuple(sorted(set(reasons))),
            )
        )

    coverage = Decimal(covered_rows) / Decimal(positive_rows) if positive_rows else Decimal(0)
    common_basis_available = covered_rows == positive_rows
    return {
        "schema_version": "formula-accounting-v1",
        "formula_id": snapshot.formula_id,
        "formula_sha256": snapshot.sha256,
        "rows": [row.as_dict() for row in rows],
        "physical_totals": {
            unit: decimal_text(value, f"total_{unit}", nonnegative=True)
            for unit, value in sorted(physical_totals.items())
        },
        "active_mass_by_material_g": {
            material_id: decimal_text(value, "active_mass", nonnegative=True)
            for material_id, value in sorted(active_by_material.items())
        },
        "total_active_mass_g_decimal": (
            decimal_text(sum(active_by_material.values(), Decimal(0)), "total_active_mass", nonnegative=True)
            if common_basis_available
            else None
        ),
        "common_active_mass_basis_available": common_basis_available,
        "positive_row_coverage_decimal": decimal_text(coverage, "coverage", nonnegative=True),
        "missing_requirements": missing,
        "validation_state": "ADVISORY_COMPLETE" if common_basis_available else "WITHHOLD_UNKNOWN",
        "applicability_state": "APPLICABLE" if common_basis_available else "PARTIAL",
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


__all__ = ["AccountedFormulaRowV1", "account_formula_snapshot"]
