"""Exact-stock and dose contracts that fail closed.

The module separates raw amount, active amount, concentration basis, stock
lifecycle, and physical receipt. It never treats an unknown strength as neat.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .canonical import canonical_decimal, parse_decimal, sha256_payload


class QuantityHold(ValueError):
    """A structured fail-closed quantity condition."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class ConcentrationBasis(str, Enum):
    MASS_FRACTION = "MASS_FRACTION"
    VOLUME_FRACTION = "VOLUME_FRACTION"
    MOLE_FRACTION = "MOLE_FRACTION"
    UNKNOWN = "UNKNOWN"


class AmountKind(str, Enum):
    MASS = "MASS"
    VOLUME = "VOLUME"
    AMOUNT_OF_SUBSTANCE = "AMOUNT_OF_SUBSTANCE"


class StockLifecycle(str, Enum):
    OWNED = "OWNED"
    PHYSICALLY_RECEIVED = "PHYSICALLY_RECEIVED"
    PREPARABLE = "PREPARABLE"
    PLANNED_ACQUISITION = "PLANNED_ACQUISITION"
    PROCUREMENT_PENDING = "PROCUREMENT_PENDING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DensityEvidence:
    value_g_per_ml: Decimal
    temperature_c: Decimal
    pressure_kpa: Decimal | None
    source_ref: str
    measured_or_authoritative: bool

    @classmethod
    def create(
        cls,
        *,
        value_g_per_ml: Decimal | str | int,
        temperature_c: Decimal | str | int,
        pressure_kpa: Decimal | str | int | None,
        source_ref: str,
        measured_or_authoritative: bool,
    ) -> "DensityEvidence":
        value = parse_decimal(value_g_per_ml)
        if value <= 0:
            raise QuantityHold("INVALID_DENSITY", "density must be positive")
        if not source_ref.strip():
            raise QuantityHold("MISSING_DENSITY_SOURCE", "density source is required")
        return cls(
            value_g_per_ml=value,
            temperature_c=parse_decimal(temperature_c),
            pressure_kpa=(parse_decimal(pressure_kpa) if pressure_kpa is not None else None),
            source_ref=source_ref,
            measured_or_authoritative=measured_or_authoritative,
        )


@dataclass(frozen=True)
class StockSpec:
    stock_id: str
    material_id: str
    active_fraction: Decimal | None
    concentration_basis: ConcentrationBasis
    carrier: str | None
    product_basis: bool
    lifecycle: StockLifecycle
    exact_stock_ref: str | None

    @classmethod
    def create(
        cls,
        *,
        stock_id: str,
        material_id: str,
        active_fraction: Decimal | str | int | None,
        concentration_basis: ConcentrationBasis,
        carrier: str | None,
        product_basis: bool,
        lifecycle: StockLifecycle,
        exact_stock_ref: str | None,
    ) -> "StockSpec":
        fraction = parse_decimal(active_fraction) if active_fraction is not None else None
        if not stock_id.strip() or not material_id.strip():
            raise QuantityHold("MISSING_STOCK_IDENTITY", "stock and material IDs are required")
        if fraction is not None and not Decimal("0") < fraction <= Decimal("1"):
            raise QuantityHold("INVALID_ACTIVE_FRACTION", "active fraction must be in (0, 1]")
        if fraction is None and concentration_basis is not ConcentrationBasis.UNKNOWN:
            raise QuantityHold(
                "MISSING_ACTIVE_FRACTION",
                "a known concentration basis cannot carry a null active fraction",
            )
        if fraction is not None and concentration_basis is ConcentrationBasis.UNKNOWN:
            raise QuantityHold(
                "UNSPECIFIED_CONCENTRATION_BASIS",
                "numeric active fraction requires an explicit basis",
            )
        if product_basis and fraction is not None:
            raise QuantityHold(
                "OPAQUE_PRODUCT_BASIS",
                "opaque product-basis composition must not receive an invented active fraction",
            )
        if lifecycle in {
            StockLifecycle.PLANNED_ACQUISITION,
            StockLifecycle.PROCUREMENT_PENDING,
        } and exact_stock_ref is not None:
            raise QuantityHold(
                "PLANNED_NOT_PHYSICAL",
                "planned or procurement-pending stock cannot have a physical ExactStockRef",
            )
        return cls(
            stock_id=stock_id,
            material_id=material_id,
            active_fraction=fraction,
            concentration_basis=concentration_basis,
            carrier=carrier,
            product_basis=product_basis,
            lifecycle=lifecycle,
            exact_stock_ref=exact_stock_ref,
        )

    @property
    def physically_executable(self) -> bool:
        return (
            self.lifecycle in {StockLifecycle.OWNED, StockLifecycle.PHYSICALLY_RECEIVED}
            and self.exact_stock_ref is not None
            and not self.product_basis
            and self.active_fraction is not None
        )


@dataclass(frozen=True)
class ActiveAmount:
    value: Decimal
    kind: AmountKind
    source_stock_id: str
    arithmetic_basis: ConcentrationBasis


@dataclass(frozen=True)
class DoseLine:
    line_id: str
    raw_amount: Decimal
    raw_kind: AmountKind
    stock: StockSpec
    density: DensityEvidence | None = None

    @classmethod
    def create(
        cls,
        *,
        line_id: str,
        raw_amount: Decimal | str | int,
        raw_kind: AmountKind,
        stock: StockSpec,
        density: DensityEvidence | None = None,
    ) -> "DoseLine":
        amount = parse_decimal(raw_amount)
        if amount < 0:
            raise QuantityHold("NEGATIVE_AMOUNT", "dose amount cannot be negative")
        if not line_id.strip():
            raise QuantityHold("MISSING_LINE_ID", "line ID is required")
        return cls(line_id=line_id, raw_amount=amount, raw_kind=raw_kind, stock=stock, density=density)


@dataclass(frozen=True)
class LineResolution:
    line_id: str
    state: str
    active_amount: ActiveAmount | None
    hold_code: str | None
    hold_reason: str | None


@dataclass(frozen=True)
class FormulaDoseReceipt:
    formula_id: str
    inventory_source_sha256: str
    lines: tuple[LineResolution, ...]
    state: str
    physical_execution_authorized: bool
    sensory_authority: bool
    release_authority: bool
    receipt_hash: str


def resolve_active_amount(line: DoseLine) -> ActiveAmount:
    stock = line.stock
    if stock.product_basis:
        raise QuantityHold(
            "OPAQUE_PRODUCT_BASIS",
            "named product basis remains executable only as named supplied product, not decomposed active",
        )
    if stock.active_fraction is None:
        raise QuantityHold(
            "MISSING_ACTIVE_FRACTION",
            "unknown stock strength cannot become 1.0 or neat",
        )
    if stock.concentration_basis is ConcentrationBasis.UNKNOWN:
        raise QuantityHold(
            "UNSPECIFIED_CONCENTRATION_BASIS",
            "active arithmetic requires an explicit basis",
        )
    if stock.carrier is None and stock.active_fraction < 1:
        raise QuantityHold("UNKNOWN_DILUENT", "diluted stock carrier remains unknown")

    fraction = stock.active_fraction
    if stock.concentration_basis is ConcentrationBasis.MASS_FRACTION:
        if line.raw_kind is AmountKind.MASS:
            return ActiveAmount(
                value=line.raw_amount * fraction,
                kind=AmountKind.MASS,
                source_stock_id=stock.stock_id,
                arithmetic_basis=stock.concentration_basis,
            )
        if line.raw_kind is AmountKind.VOLUME:
            if line.density is None:
                raise QuantityHold(
                    "MISSING_DENSITY",
                    "volume-to-mass conversion requires conditioned density evidence",
                )
            if not line.density.measured_or_authoritative:
                raise QuantityHold(
                    "DENSITY_NOT_AUTHORITATIVE",
                    "advisory density cannot authorize cross-basis conversion",
                )
            stock_mass = line.raw_amount * line.density.value_g_per_ml
            return ActiveAmount(
                value=stock_mass * fraction,
                kind=AmountKind.MASS,
                source_stock_id=stock.stock_id,
                arithmetic_basis=stock.concentration_basis,
            )
        raise QuantityHold("UNIT_NOT_CONVERTIBLE", "mass fraction requires mass or density-bound volume")

    if stock.concentration_basis is ConcentrationBasis.VOLUME_FRACTION:
        if line.raw_kind is AmountKind.VOLUME:
            return ActiveAmount(
                value=line.raw_amount * fraction,
                kind=AmountKind.VOLUME,
                source_stock_id=stock.stock_id,
                arithmetic_basis=stock.concentration_basis,
            )
        raise QuantityHold(
            "BASIS_MISMATCH",
            "mass and volume fractions are not interchangeable",
        )

    if stock.concentration_basis is ConcentrationBasis.MOLE_FRACTION:
        if line.raw_kind is AmountKind.AMOUNT_OF_SUBSTANCE:
            return ActiveAmount(
                value=line.raw_amount * fraction,
                kind=AmountKind.AMOUNT_OF_SUBSTANCE,
                source_stock_id=stock.stock_id,
                arithmetic_basis=stock.concentration_basis,
            )
        raise QuantityHold("BASIS_MISMATCH", "mole fraction requires amount-of-substance")

    raise QuantityHold("UNSUPPORTED_BASIS", "unsupported concentration basis")


def physical_stock_gate(stock: StockSpec) -> None:
    if stock.lifecycle in {
        StockLifecycle.PLANNED_ACQUISITION,
        StockLifecycle.PROCUREMENT_PENDING,
    }:
        raise QuantityHold(
            "PLANNED_NOT_PHYSICAL",
            "design-available or planned material is not physically received",
        )
    if stock.lifecycle is StockLifecycle.PREPARABLE:
        raise QuantityHold(
            "PREPARATION_RECEIPT_REQUIRED",
            "preparable stock is not prepared until a dated stock receipt exists",
        )
    if stock.exact_stock_ref is None:
        raise QuantityHold("MISSING_EXACT_STOCK_REF", "physical execution requires ExactStockRef")


def build_formula_dose_receipt(
    *,
    formula_id: str,
    inventory_source_sha256: str,
    lines: Iterable[DoseLine],
) -> FormulaDoseReceipt:
    if not formula_id.strip():
        raise QuantityHold("MISSING_FORMULA_ID", "formula ID is required")
    if len(inventory_source_sha256) != 64:
        raise QuantityHold("INVALID_INVENTORY_HASH", "inventory SHA-256 must be 64 hex characters")

    resolutions: list[LineResolution] = []
    physical_ok = True
    for line in lines:
        try:
            active = resolve_active_amount(line)
            physical_stock_gate(line.stock)
        except QuantityHold as exc:
            physical_ok = False
            resolutions.append(
                LineResolution(
                    line_id=line.line_id,
                    state="HOLD",
                    active_amount=None,
                    hold_code=exc.code,
                    hold_reason=exc.message,
                )
            )
        else:
            resolutions.append(
                LineResolution(
                    line_id=line.line_id,
                    state="RESOLVED",
                    active_amount=active,
                    hold_code=None,
                    hold_reason=None,
                )
            )

    state = "RESOLVED_FOR_DOSE_ACCOUNTING" if physical_ok else "HOLD"
    payload = {
        "formula_id": formula_id,
        "inventory_source_sha256": inventory_source_sha256,
        "lines": [
            {
                "line_id": result.line_id,
                "state": result.state,
                "active_amount": (
                    {
                        "value": canonical_decimal(result.active_amount.value),
                        "kind": result.active_amount.kind.value,
                        "source_stock_id": result.active_amount.source_stock_id,
                        "arithmetic_basis": result.active_amount.arithmetic_basis.value,
                    }
                    if result.active_amount is not None
                    else None
                ),
                "hold_code": result.hold_code,
                "hold_reason": result.hold_reason,
            }
            for result in resolutions
        ],
        "state": state,
        "physical_execution_authorized": False,
        "sensory_authority": False,
        "release_authority": False,
    }
    return FormulaDoseReceipt(
        formula_id=formula_id,
        inventory_source_sha256=inventory_source_sha256,
        lines=tuple(resolutions),
        state=state,
        physical_execution_authorized=False,
        sensory_authority=False,
        release_authority=False,
        receipt_hash=sha256_payload(payload, domain="PERFUME_CHEM_FORMULA_DOSE_RECEIPT_V20"),
    )


def screening_claim_boundary() -> dict[str, bool | str]:
    """Return the fixed claim cap for screening outputs."""

    return {
        "screening_state": "DESIGNED_OR_COMPUTED_ONLY",
        "formula_release_authority": False,
        "sensory_authority": False,
        "physical_authority": False,
        "strict_empirical_oav_authority": False,
    }
