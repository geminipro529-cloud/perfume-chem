"""Exact physical binding and resumable compounding bookkeeping.

These records bind and replay existing approved physical actions.  They do not
authorize an operator to compound, do not create a bottle transfer, and never
promote workbook prose into inventory truth.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from engine.calibration.hashing import stable_file_hash, stable_json_hash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabFormulaComponent, LabFormulaVersion, LabStockSolution
from app.models.lab_cp2_physical import (
    LabBuildPlanLinePhysicalBinding,
    LabBuildPlanPhysicalBinding,
    LabCompoundingCommandReceipt,
    LabCompoundingRun,
    LabStockLotPhysicalReceipt,
    LabStockPreparationReceipt,
)
from app.models.lab_execution import LabBottleActionCommit, LabBottleActionProposal
from app.models.lab_planning import (
    LabBuildPlanLine,
    LabBuildPlanVersion,
    LabFormulaVersionEdge,
    LabInventoryReservationEvent,
)

if TYPE_CHECKING:
    from app.models.lab import LabInventoryMovement
    from app.repositories.lab import LabRepository

_ROOT = Path(__file__).resolve().parents[3]
_FALSE_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
}


class PhysicalLineageError(RuntimeError):
    code = "PHYSICAL_LINEAGE_ERROR"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PhysicalLineageConflictError(PhysicalLineageError):
    pass


@dataclass(frozen=True, slots=True)
class PhysicalLineBindingInput:
    build_plan_line_id: str
    formula_component_id: str
    basket: str
    operation: str
    stock_solution_id: str
    concentration_fraction_decimal: str
    concentration_basis: str
    carrier: str | None
    stock_preparation_receipt_id: str | None
    amount_decimal: str
    amount_unit: str
    density_g_ml_decimal: str | None
    density_provenance: str | None


def _decimal(value: object, field: str, *, positive: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise PhysicalLineageError(
            "INVALID_DECIMAL", f"{field} must be a finite decimal string."
        ) from error
    if not result.is_finite() or result < 0 or (positive and result <= 0):
        qualifier = "positive" if positive else "non-negative"
        raise PhysicalLineageError(
            "INVALID_DECIMAL", f"{field} must be finite and {qualifier}."
        )
    return result


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _quantity_base(value: Decimal, unit: str) -> tuple[str, Decimal]:
    if unit == "g":
        return "mass", value
    if unit == "mg":
        return "mass", value / Decimal(1000)
    if unit == "mL":
        return "volume", value
    if unit == "uL":
        return "volume", value / Decimal(1000)
    raise PhysicalLineageError("INVALID_PHYSICAL_UNIT", f"Unsupported unit: {unit}.")


def _hash_key(value: str) -> str:
    return sha256(str(value).strip().encode("utf-8")).hexdigest()


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PhysicalLineageError(
            "NAIVE_PHYSICAL_TIMESTAMP", f"{field} must include a UTC offset."
        )
    return value.astimezone(timezone.utc)


def _basket_rank(value: str) -> int:
    if value == "W0":
        return 0
    if value.startswith("B") and value[1:].isdigit() and int(value[1:]) >= 1:
        return int(value[1:])
    raise PhysicalLineageError(
        "INVALID_PHYSICAL_BASKET",
        "Basket must be W0 or a positive B-number.",
    )


class LabPhysicalLineageServiceMixin:
    if TYPE_CHECKING:
        session: AsyncSession
        repository: "LabRepository"

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

        async def _append_inventory_movement(
            self,
            *,
            stock: LabStockSolution,
            movement_type: str,
            raw_quantity: float,
            balance_before: float,
            balance_after: float,
            actor: str,
            transaction_id: str,
            idempotency_key: str,
            reason: str,
            mass_delta_g: float,
            event_effect_id: str | None = None,
            build_plan_line_id: str | None = None,
            reservation_event_id: str | None = None,
            bottle_event_id: str | None = None,
            admin_cause: str | None = None,
            correction_of_movement_id: str | None = None,
            reversal_of_movement_id: str | None = None,
            measured_volume_ul: float | None = None,
            standard_uncertainty: float | None = None,
        ) -> LabInventoryMovement: ...

    async def finalize_stock_lot_physical_receipt(
        self,
        *,
        stock_solution_id: str,
        supplier: str,
        lot_number: str,
        bottle_identifier: str,
        label: str,
        active_fraction_decimal: str,
        fraction_basis: str,
        carrier: str | None,
        density_g_ml_decimal: str | None,
        density_provenance: str | None,
        preparation_state: str,
        stock_preparation_receipt_id: str | None,
        homogeneity_state: str,
        source_reference: str,
        reviewer: str,
        observed_at: datetime,
        idempotency_key: str,
    ) -> LabStockLotPhysicalReceipt:
        """Bind exact stock facts without changing inventory or granting authority."""

        text_fields = {
            "supplier": supplier,
            "lot_number": lot_number,
            "bottle_identifier": bottle_identifier,
            "label": label,
            "source_reference": source_reference,
            "reviewer": reviewer,
        }
        normalized_text: dict[str, str] = {}
        for field, value in text_fields.items():
            normalized = str(value).strip()
            if not normalized:
                raise PhysicalLineageError(
                    "STOCK_LOT_RECEIPT_FIELD_REQUIRED",
                    f"{field} must be non-empty.",
                )
            normalized_text[field] = normalized
        fraction = _decimal(
            active_fraction_decimal, "active_fraction_decimal", positive=True
        )
        if fraction > 1:
            raise PhysicalLineageError(
                "STOCK_LOT_FRACTION_INVALID",
                "active_fraction_decimal cannot exceed one.",
            )
        density_text = None
        if density_g_ml_decimal is not None:
            density_text = _decimal_text(
                _decimal(density_g_ml_decimal, "density_g_ml_decimal", positive=True)
            )
            if not str(density_provenance or "").strip():
                raise PhysicalLineageError(
                    "DENSITY_PROVENANCE_REQUIRED",
                    "A density value requires explicit provenance.",
                )
        if preparation_state not in {"SUPPLIER_AS_SUPPLIED", "LOCALLY_PREPARED"}:
            raise PhysicalLineageError(
                "INVALID_STOCK_PREPARATION_STATE",
                "Unsupported stock preparation state.",
            )
        if homogeneity_state not in {"CONFIRMED", "NOT_APPLICABLE"}:
            raise PhysicalLineageError(
                "INVALID_STOCK_HOMOGENEITY_STATE",
                "Stock homogeneity must be confirmed or explicitly not applicable.",
            )
        if fraction < 1 and homogeneity_state != "CONFIRMED":
            raise PhysicalLineageError(
                "STOCK_HOMOGENEITY_NOT_CONFIRMED",
                "A diluted stock requires confirmed homogeneity.",
            )
        if preparation_state == "LOCALLY_PREPARED" and not str(
            stock_preparation_receipt_id or ""
        ).strip():
            raise PhysicalLineageError(
                "STOCK_PREPARATION_RECEIPT_REQUIRED",
                "A locally prepared stock requires its preparation receipt.",
            )
        if preparation_state == "SUPPLIER_AS_SUPPLIED" and (
            stock_preparation_receipt_id is not None
        ):
            raise PhysicalLineageError(
                "STOCK_PREPARATION_RECEIPT_NOT_APPLICABLE",
                "Supplier-as-supplied stock cannot claim a local preparation receipt.",
            )
        command = {
            "schema": "lab-stock-lot-physical-receipt-v1",
            "stock_solution_id": stock_solution_id,
            **normalized_text,
            "active_fraction_decimal": _decimal_text(fraction),
            "fraction_basis": fraction_basis,
            "carrier": str(carrier).strip() if carrier is not None else None,
            "density_g_ml_decimal": density_text,
            "density_provenance": (
                str(density_provenance).strip()
                if density_provenance is not None
                else None
            ),
            "preparation_state": preparation_state,
            "stock_preparation_receipt_id": stock_preparation_receipt_id,
            "homogeneity_state": homogeneity_state,
            "observed_at": _aware(observed_at, "observed_at").isoformat(),
        }
        key_sha256 = _hash_key(idempotency_key)
        command_sha256 = stable_json_hash(command)
        async with self._transaction():
            replay = await self.session.scalar(
                select(LabStockLotPhysicalReceipt).where(
                    LabStockLotPhysicalReceipt.idempotency_key_sha256 == key_sha256
                )
            )
            if replay is not None:
                if replay.command_sha256 == command_sha256:
                    return replay
                raise PhysicalLineageConflictError(
                    "STOCK_LOT_RECEIPT_IDEMPOTENCY_MISMATCH",
                    "The idempotency key was reused for different stock facts.",
                )
            stock = await self.session.get(LabStockSolution, stock_solution_id)
            if stock is None:
                raise PhysicalLineageError(
                    "STOCK_SOLUTION_NOT_FOUND", "The stock solution does not exist."
                )
            existing = await self.session.scalar(
                select(LabStockLotPhysicalReceipt).where(
                    LabStockLotPhysicalReceipt.stock_solution_id == stock.id
                )
            )
            if existing is not None:
                if existing.command_sha256 == command_sha256:
                    return existing
                raise PhysicalLineageConflictError(
                    "STOCK_LOT_RECEIPT_ALREADY_EXISTS",
                    "A different immutable receipt already binds this stock identity.",
                )
            if stock.active_fraction_decimal_text is None or fraction != _decimal(
                stock.active_fraction_decimal_text, "stock_active_fraction", positive=True
            ):
                raise PhysicalLineageError(
                    "STOCK_LOT_FRACTION_MISMATCH",
                    "Receipt fraction must exactly match the stock record.",
                )
            if fraction_basis != stock.fraction_basis:
                raise PhysicalLineageError(
                    "STOCK_LOT_BASIS_MISMATCH",
                    "Receipt basis must exactly match the stock record.",
                )
            if not stock.supplier or (
                " ".join(stock.supplier.split()).casefold()
                != " ".join(normalized_text["supplier"].split()).casefold()
            ):
                raise PhysicalLineageError(
                    "STOCK_LOT_SUPPLIER_MISMATCH",
                    "Receipt supplier must match the immutable stock record.",
                )
            if not stock.lot_number or stock.lot_number.strip() != normalized_text[
                "lot_number"
            ]:
                raise PhysicalLineageError(
                    "STOCK_LOT_NUMBER_MISMATCH",
                    "Receipt lot must exactly match the immutable stock record.",
                )
            recorded_carrier = str(stock.solvent_name or "").strip()
            supplied_carrier = str(carrier or "").strip()
            if recorded_carrier.casefold() != supplied_carrier.casefold():
                raise PhysicalLineageError(
                    "STOCK_LOT_CARRIER_MISMATCH",
                    "Receipt carrier must exactly match the stock record.",
                )
            if stock.density_g_ml is None:
                if density_text is not None:
                    raise PhysicalLineageError(
                        "STOCK_LOT_DENSITY_UNBOUND",
                        "A receipt cannot add density to an existing stock record.",
                    )
            elif density_text is None or float(Decimal(density_text)) != float(
                stock.density_g_ml
            ):
                raise PhysicalLineageError(
                    "STOCK_LOT_DENSITY_MISMATCH",
                    "Receipt density must match the stock record's numeric projection.",
                )
            preparation = None
            if stock_preparation_receipt_id is not None:
                preparation = await self.session.get(
                    LabStockPreparationReceipt, stock_preparation_receipt_id
                )
                if (
                    preparation is None
                    or preparation.prepared_stock_solution_id != stock.id
                    or preparation.homogeneity_state != "CONFIRMED"
                ):
                    raise PhysicalLineageError(
                        "STOCK_PREPARATION_RECEIPT_MISMATCH",
                        "Preparation receipt must bind this stock with confirmed homogeneity.",
                    )
            content = {**command, "idempotency_key_sha256": key_sha256, **_FALSE_AUTHORITY}
            receipt = LabStockLotPhysicalReceipt(
                stock_solution_id=stock.id,
                supplier=normalized_text["supplier"],
                lot_number=normalized_text["lot_number"],
                bottle_identifier=normalized_text["bottle_identifier"],
                label=normalized_text["label"],
                active_fraction_decimal=_decimal_text(fraction),
                fraction_basis=fraction_basis,
                carrier=supplied_carrier or None,
                density_g_ml_decimal=density_text,
                density_provenance=(
                    str(density_provenance).strip()
                    if density_provenance is not None
                    else None
                ),
                preparation_state=preparation_state,
                stock_preparation_receipt_id=(preparation.id if preparation else None),
                homogeneity_state=homogeneity_state,
                source_reference=normalized_text["source_reference"],
                reviewer=normalized_text["reviewer"],
                observed_at=_aware(observed_at, "observed_at"),
                idempotency_key_sha256=key_sha256,
                command_sha256=command_sha256,
                content_sha256=stable_json_hash(content),
                **_FALSE_AUTHORITY,
            )
            self.session.add(receipt)
            await self.session.flush()
            return receipt

    async def finalize_build_plan_stock_preparation(
        self,
        *,
        build_plan_version_id: str,
        parent_stock_solution_id: str,
        carrier_stock_solution_id: str,
        prepared_stock_solution_id: str,
        basis: str,
        parent_quantity_decimal: str,
        parent_quantity_unit: str,
        carrier_quantity_decimal: str,
        carrier_quantity_unit: str,
        result_quantity_decimal: str,
        result_quantity_unit: str,
        density_g_ml_decimal: str | None,
        density_provenance: str | None,
        homogeneity: str,
        label: str,
        operator: str,
        prepared_at: datetime,
        idempotency_key: str,
    ) -> LabStockPreparationReceipt:
        if basis not in {"W_W", "V_V"}:
            raise PhysicalLineageError(
                "INVALID_PREPARATION_BASIS", "basis must be W_W or V_V."
            )
        if homogeneity != "CONFIRMED":
            raise PhysicalLineageError(
                "PREPARATION_HOMOGENEITY_NOT_CONFIRMED",
                "A failed or unknown homogeneity state cannot be finalized.",
            )
        parent_quantity = _decimal(
            parent_quantity_decimal, "parent_quantity_decimal", positive=True
        )
        carrier_quantity = _decimal(
            carrier_quantity_decimal, "carrier_quantity_decimal", positive=True
        )
        result_quantity = _decimal(
            result_quantity_decimal, "result_quantity_decimal", positive=True
        )
        parent_dimension, parent_base = _quantity_base(
            parent_quantity, parent_quantity_unit
        )
        carrier_dimension, carrier_base = _quantity_base(
            carrier_quantity, carrier_quantity_unit
        )
        result_dimension, result_base = _quantity_base(
            result_quantity, result_quantity_unit
        )
        required_dimension = "mass" if basis == "W_W" else "volume"
        if {
            parent_dimension,
            carrier_dimension,
            result_dimension,
        } != {required_dimension}:
            raise PhysicalLineageError(
                "PREPARATION_DIMENSION_MISMATCH",
                "W_W requires mass quantities and V_V requires volume quantities; "
                "no density conversion is inferred.",
            )
        if parent_base + carrier_base != result_base:
            raise PhysicalLineageError(
                "STOCK_PREPARATION_CONSERVATION_FAILURE",
                "Parent plus carrier quantity must equal the measured result.",
            )
        density_text = None
        if density_g_ml_decimal is not None:
            density_text = _decimal_text(
                _decimal(density_g_ml_decimal, "density_g_ml_decimal", positive=True)
            )
            if not str(density_provenance or "").strip():
                raise PhysicalLineageError(
                    "DENSITY_PROVENANCE_REQUIRED",
                    "A density value requires explicit provenance.",
                )
        command = {
            "schema": "lab-stock-preparation-finalize-v1",
            "build_plan_version_id": build_plan_version_id,
            "parent_stock_solution_id": parent_stock_solution_id,
            "carrier_stock_solution_id": carrier_stock_solution_id,
            "prepared_stock_solution_id": prepared_stock_solution_id,
            "basis": basis,
            "parent_quantity_decimal": _decimal_text(parent_quantity),
            "parent_quantity_unit": parent_quantity_unit,
            "carrier_quantity_decimal": _decimal_text(carrier_quantity),
            "carrier_quantity_unit": carrier_quantity_unit,
            "result_quantity_decimal": _decimal_text(result_quantity),
            "result_quantity_unit": result_quantity_unit,
            "density_g_ml_decimal": density_text,
            "density_provenance": density_provenance,
            "homogeneity": homogeneity,
            "label": str(label).strip(),
            "operator": str(operator).strip(),
            "prepared_at": _aware(prepared_at, "prepared_at").isoformat(),
        }
        command_sha256 = stable_json_hash(command)
        key_sha256 = _hash_key(idempotency_key)
        async with self._transaction():
            replay = await self.session.scalar(
                select(LabStockPreparationReceipt).where(
                    LabStockPreparationReceipt.idempotency_key_sha256
                    == key_sha256
                )
            )
            if replay is not None:
                if replay.command_sha256 == command_sha256:
                    return replay
                raise PhysicalLineageConflictError(
                    "STOCK_PREPARATION_IDEMPOTENCY_MISMATCH",
                    "The idempotency key was reused for a different preparation.",
                )
            plan = await self.session.get(LabBuildPlanVersion, build_plan_version_id)
            parent = await self.session.get(
                LabStockSolution, parent_stock_solution_id
            )
            carrier = await self.session.get(
                LabStockSolution, carrier_stock_solution_id
            )
            prepared = await self.session.get(
                LabStockSolution, prepared_stock_solution_id
            )
            if plan is None:
                raise PhysicalLineageError(
                    "BUILD_PLAN_NOT_FOUND", "The build-plan version does not exist."
                )
            if parent is None or carrier is None or prepared is None:
                raise PhysicalLineageError(
                    "STOCK_BINDING_NOT_FOUND",
                    "Parent, carrier, and prepared stock must already exist.",
                )
            if parent.id == carrier.id or prepared.id in {parent.id, carrier.id}:
                raise PhysicalLineageError(
                    "STOCK_PREPARATION_IDENTITY_COLLISION",
                    "Parent, carrier, and prepared stock identities must be distinct.",
                )
            if parent.active_fraction_decimal_text is None:
                raise PhysicalLineageError(
                    "PARENT_ACTIVE_FRACTION_NOT_EXACT",
                    "The parent stock lacks an exact active-fraction receipt.",
                )
            parent_fraction = _decimal(
                parent.active_fraction_decimal_text,
                "parent_active_fraction",
            )
            expected_fraction = parent_base * parent_fraction / result_base
            if prepared.active_fraction_decimal_text is None:
                raise PhysicalLineageError(
                    "PREPARED_ACTIVE_FRACTION_NOT_EXACT",
                    "The prepared stock lacks an exact active-fraction receipt.",
                )
            recorded_fraction = _decimal(
                prepared.active_fraction_decimal_text,
                "prepared_active_fraction",
            )
            if recorded_fraction != expected_fraction:
                raise PhysicalLineageError(
                    "PREPARED_ACTIVE_FRACTION_MISMATCH",
                    "Prepared stock fraction does not conserve parent active material.",
                )
            if basis == "W_W" and prepared.fraction_basis not in {
                "mass_fraction",
                "W_W",
            }:
                raise PhysicalLineageError(
                    "PREPARED_BASIS_MISMATCH",
                    "The prepared stock does not declare a mass-fraction basis.",
                )
            if basis == "V_V" and prepared.fraction_basis not in {
                "volume_fraction",
                "V_V",
            }:
                raise PhysicalLineageError(
                    "PREPARED_BASIS_MISMATCH",
                    "The prepared stock does not declare a volume-fraction basis.",
                )
            content = {
                **command,
                "resulting_active_fraction_decimal": _decimal_text(
                    expected_fraction
                ),
                "idempotency_key_sha256": key_sha256,
                **_FALSE_AUTHORITY,
            }
            receipt = LabStockPreparationReceipt(
                build_plan_version_id=plan.id,
                parent_stock_solution_id=parent.id,
                carrier_stock_solution_id=carrier.id,
                prepared_stock_solution_id=prepared.id,
                basis=basis,
                parent_quantity_decimal=_decimal_text(parent_quantity),
                parent_quantity_unit=parent_quantity_unit,
                carrier_quantity_decimal=_decimal_text(carrier_quantity),
                carrier_quantity_unit=carrier_quantity_unit,
                result_quantity_decimal=_decimal_text(result_quantity),
                result_quantity_unit=result_quantity_unit,
                resulting_active_fraction_decimal=_decimal_text(expected_fraction),
                density_g_ml_decimal=density_text,
                density_provenance=density_provenance,
                homogeneity_state=homogeneity,
                label=str(label).strip(),
                operator=str(operator).strip(),
                prepared_at=_aware(prepared_at, "prepared_at"),
                idempotency_key_sha256=key_sha256,
                command_sha256=command_sha256,
                content_sha256=stable_json_hash(content),
                **_FALSE_AUTHORITY,
            )
            self.session.add(receipt)
            await self.session.flush()
            return receipt

    async def bind_build_plan_physical_lineage(
        self,
        *,
        build_plan_version_id: str,
        formula_version_id: str,
        immediate_parent_formula_version_id: str | None,
        stock_lineage_receipts: list[str],
        release_authority_receipt_ids: list[str],
        order_policy: str,
        lines: tuple[PhysicalLineBindingInput, ...],
    ) -> LabBuildPlanPhysicalBinding:
        """Create an exact all-lines binding; no physical actions are created."""

        if not lines:
            raise PhysicalLineageError(
                "EMPTY_PHYSICAL_BINDING", "At least one exact line is required."
            )
        async with self._transaction():
            plan = await self.session.get(LabBuildPlanVersion, build_plan_version_id)
            formula = await self.session.get(LabFormulaVersion, formula_version_id)
            parent = (
                await self.session.get(
                    LabFormulaVersion, immediate_parent_formula_version_id
                )
                if immediate_parent_formula_version_id
                else None
            )
            if plan is None or formula is None:
                raise PhysicalLineageError(
                    "PHYSICAL_BINDING_PARENT_NOT_FOUND",
                    "Build-plan and formula versions must exist.",
                )
            if immediate_parent_formula_version_id and parent is None:
                raise PhysicalLineageError(
                    "IMMEDIATE_PARENT_FORMULA_NOT_FOUND",
                    "The declared immediate parent formula does not exist.",
                )
            if parent is not None:
                edge = await self.session.scalar(
                    select(LabFormulaVersionEdge).where(
                        LabFormulaVersionEdge.child_version_id == formula.id,
                        LabFormulaVersionEdge.parent_version_id == parent.id,
                    )
                )
                if edge is None:
                    raise PhysicalLineageError(
                        "IMMEDIATE_PARENT_EDGE_NOT_FOUND",
                        "The declared parent is not an immutable direct parent edge.",
                    )
            existing = await self.session.scalar(
                select(LabBuildPlanPhysicalBinding).where(
                    LabBuildPlanPhysicalBinding.build_plan_version_id == plan.id
                )
            )
            components = list(
                await self.session.scalars(
                    select(LabFormulaComponent)
                    .where(LabFormulaComponent.formula_version_id == formula.id)
                    .order_by(LabFormulaComponent.position)
                )
            )
            formula_payload = [
                {
                    "component_id": item.id,
                    "position": item.position,
                    "stock_solution_id": item.stock_solution_id,
                    "requested_mass_g_decimal_text": (
                        item.requested_mass_g_decimal_text
                    ),
                    "requested_volume_ul": item.requested_volume_ul,
                    "unit": item.unit,
                }
                for item in components
            ]
            formula_sha256 = stable_json_hash(formula_payload)
            parent_sha256 = None
            if parent is not None:
                parent_components = list(
                    await self.session.scalars(
                        select(LabFormulaComponent)
                        .where(
                            LabFormulaComponent.formula_version_id == parent.id
                        )
                        .order_by(LabFormulaComponent.position)
                    )
                )
                parent_sha256 = stable_json_hash(
                    [
                        {
                            "component_id": item.id,
                            "position": item.position,
                            "stock_solution_id": item.stock_solution_id,
                            "requested_mass_g_decimal_text": (
                                item.requested_mass_g_decimal_text
                            ),
                            "requested_volume_ul": item.requested_volume_ul,
                            "unit": item.unit,
                        }
                        for item in parent_components
                    ]
                )
            plan_lines = {
                row.id: row
                for row in await self.session.scalars(
                    select(LabBuildPlanLine).where(
                        LabBuildPlanLine.build_plan_version_id == plan.id
                    )
                )
            }
            components_by_id = {item.id: item for item in components}
            normalized_lines: list[dict[str, Any]] = []
            seen_plan_lines: set[str] = set()
            seen_components: set[str] = set()
            previous_basket: str | None = None
            previous_basket_rank: int | None = None
            closed_baskets: set[str] = set()
            previous_liquid_amount: Decimal | None = None
            mass_seen_in_basket = False
            for sequence, requested in enumerate(lines, start=1):
                line = plan_lines.get(requested.build_plan_line_id)
                component = components_by_id.get(requested.formula_component_id)
                if line is None or component is None:
                    raise PhysicalLineageError(
                        "PHYSICAL_LINE_PARENT_MISMATCH",
                        "Every line must belong to the bound plan and formula.",
                    )
                if line.id in seen_plan_lines or component.id in seen_components:
                    raise PhysicalLineageError(
                        "DUPLICATE_PHYSICAL_LINE_BINDING",
                        "Plan lines and formula components may be bound only once.",
                    )
                if (
                    line.stock_solution_id != requested.stock_solution_id
                    or component.stock_solution_id != requested.stock_solution_id
                ):
                    raise PhysicalLineageError(
                        "PHYSICAL_LINE_STOCK_MISMATCH",
                        "The selected stock must match both immutable parent rows.",
                    )
                stock = await self.session.get(
                    LabStockSolution, requested.stock_solution_id
                )
                if stock is None or stock.active_fraction_decimal_text is None:
                    raise PhysicalLineageError(
                        "PHYSICAL_LINE_STOCK_NOT_EXACT",
                        "Each stock requires an exact active-fraction binding.",
                    )
                fraction = _decimal(
                    requested.concentration_fraction_decimal,
                    "concentration_fraction_decimal",
                )
                if fraction > 1 or fraction != _decimal(
                    stock.active_fraction_decimal_text,
                    "stock_active_fraction",
                ):
                    raise PhysicalLineageError(
                        "PHYSICAL_LINE_FRACTION_MISMATCH",
                        "Line fraction must exactly match the selected stock.",
                    )
                if (
                    requested.concentration_basis != line.concentration_basis
                    or requested.concentration_basis != stock.fraction_basis
                ):
                    raise PhysicalLineageError(
                        "PHYSICAL_LINE_BASIS_MISMATCH",
                        "Line, plan, and stock concentration bases must match exactly.",
                    )
                amount = _decimal(
                    requested.amount_decimal, "amount_decimal", positive=True
                )
                if requested.amount_unit != line.unit or amount != _decimal(
                    line.planned_raw_quantity, "planned_raw_quantity", positive=True
                ):
                    raise PhysicalLineageError(
                        "PHYSICAL_LINE_AMOUNT_MISMATCH",
                        "The exact physical amount must match the immutable plan line.",
                    )
                if requested.amount_unit in {"mL", "uL"}:
                    if requested.density_g_ml_decimal is None or not str(
                        requested.density_provenance or ""
                    ).strip():
                        raise PhysicalLineageError(
                            "PHYSICAL_LINE_DENSITY_REQUIRED",
                            "Volume lines require exact density and provenance.",
                        )
                    _decimal(
                        requested.density_g_ml_decimal,
                        "density_g_ml_decimal",
                        positive=True,
                    )
                    if (
                        line.density_g_ml is None
                        or not str(line.density_source or "").strip()
                        or _decimal(
                            requested.density_g_ml_decimal,
                            "density_g_ml_decimal",
                            positive=True,
                        )
                        != _decimal(line.density_g_ml, "plan_density", positive=True)
                        or requested.density_provenance != line.density_source
                    ):
                        raise PhysicalLineageError(
                            "PHYSICAL_LINE_DENSITY_MISMATCH",
                            "Volume density and provenance must match the immutable plan.",
                        )
                if component.requested_mass_g_decimal_text is None:
                    raise PhysicalLineageError(
                        "FORMULA_COMPONENT_EXACT_AMOUNT_MISSING",
                        "The formula component lacks an exact decimal mass binding.",
                    )
                expected_component_mass = _decimal(
                    component.requested_mass_g_decimal_text,
                    "formula_component_mass",
                    positive=True,
                )
                if requested.amount_unit in {"g", "mg"}:
                    _, requested_mass = _quantity_base(amount, requested.amount_unit)
                else:
                    _, volume_ml = _quantity_base(amount, requested.amount_unit)
                    requested_mass = volume_ml * _decimal(
                        requested.density_g_ml_decimal,
                        "density_g_ml_decimal",
                        positive=True,
                    )
                if requested_mass != expected_component_mass:
                    raise PhysicalLineageError(
                        "FORMULA_COMPONENT_AMOUNT_MISMATCH",
                        "The exact line conversion must match the formula component mass.",
                    )
                if requested.stock_preparation_receipt_id is not None:
                    preparation = await self.session.get(
                        LabStockPreparationReceipt,
                        requested.stock_preparation_receipt_id,
                    )
                    if (
                        preparation is None
                        or preparation.build_plan_version_id != plan.id
                        or preparation.prepared_stock_solution_id != stock.id
                    ):
                        raise PhysicalLineageError(
                            "STOCK_PREPARATION_BINDING_MISMATCH",
                            "The preparation receipt must bind this plan and stock.",
                        )
                if requested.basket != previous_basket:
                    if requested.basket in closed_baskets:
                        raise PhysicalLineageError(
                            "PHYSICAL_BASKET_ORDER_DRIFT",
                            "A closed basket cannot be reopened.",
                        )
                    if previous_basket is not None:
                        closed_baskets.add(previous_basket)
                    rank = _basket_rank(requested.basket)
                    if previous_basket_rank is not None and rank <= previous_basket_rank:
                        raise PhysicalLineageError(
                            "PHYSICAL_BASKET_ORDER_DRIFT",
                            "Baskets must advance from W0 through ascending B numbers.",
                        )
                    previous_basket = requested.basket
                    previous_basket_rank = rank
                    previous_liquid_amount = None
                    mass_seen_in_basket = False
                is_liquid = requested.amount_unit in {"mL", "uL"}
                if is_liquid:
                    if mass_seen_in_basket:
                        raise PhysicalLineageError(
                            "PHYSICAL_LINE_ORDER_DRIFT",
                            "Liquid transfers cannot follow a mass row in one basket.",
                        )
                    if (
                        previous_liquid_amount is not None
                        and amount > previous_liquid_amount
                    ):
                        raise PhysicalLineageError(
                            "PHYSICAL_LINE_ORDER_DRIFT",
                            "Liquid amounts must descend within each basket.",
                        )
                    previous_liquid_amount = amount
                elif requested.operation != "MASS_ADD":
                    raise PhysicalLineageError(
                        "MASS_OPERATION_REQUIRED",
                        "Mass rows must remain separate as MASS_ADD operations.",
                    )
                else:
                    mass_seen_in_basket = True
                line_payload = {
                    "sequence": sequence,
                    "build_plan_line_id": line.id,
                    "formula_component_id": component.id,
                    "basket": requested.basket,
                    "operation": requested.operation,
                    "stock_solution_id": stock.id,
                    "concentration_fraction_decimal": _decimal_text(fraction),
                    "concentration_basis": requested.concentration_basis,
                    "carrier": requested.carrier,
                    "stock_preparation_receipt_id": (
                        requested.stock_preparation_receipt_id
                    ),
                    "amount_decimal": _decimal_text(amount),
                    "amount_unit": requested.amount_unit,
                    "density_g_ml_decimal": requested.density_g_ml_decimal,
                    "density_provenance": requested.density_provenance,
                }
                line_payload["command_identity_sha256"] = stable_json_hash(
                    {"schema": "physical-command-identity-v1", **line_payload}
                )
                line_payload["content_sha256"] = stable_json_hash(
                    {**line_payload, **_FALSE_AUTHORITY}
                )
                normalized_lines.append(line_payload)
                seen_plan_lines.add(line.id)
                seen_components.add(component.id)
            if seen_plan_lines != set(plan_lines) or seen_components != set(
                components_by_id
            ):
                raise PhysicalLineageError(
                    "INCOMPLETE_PHYSICAL_BINDING",
                    "The physical binding must cover every plan line and component.",
                )
            stock_receipt_ids = [
                str(value).strip() for value in stock_lineage_receipts
            ]
            if (
                any(not value for value in stock_receipt_ids)
                or len(stock_receipt_ids) != len(set(stock_receipt_ids))
            ):
                raise PhysicalLineageError(
                    "STOCK_LOT_RECEIPT_IDENTITIES_INVALID",
                    "Stock-lot physical receipt identities must be non-empty and unique.",
                )
            stock_receipts = list(
                await self.session.scalars(
                    select(LabStockLotPhysicalReceipt).where(
                        LabStockLotPhysicalReceipt.id.in_(stock_receipt_ids)
                    )
                )
            )
            required_stock_ids = {
                item["stock_solution_id"] for item in normalized_lines
            }
            if (
                len(stock_receipts) != len(stock_receipt_ids)
                or {receipt.stock_solution_id for receipt in stock_receipts}
                != required_stock_ids
            ):
                raise PhysicalLineageError(
                    "STOCK_LOT_RECEIPT_COVERAGE_INCOMPLETE",
                    "Exactly one immutable lot/bottle/homogeneity receipt is required "
                    "for every bound stock.",
                )
            authority_receipt_ids = [
                str(value).strip() for value in release_authority_receipt_ids
            ]
            if (
                not authority_receipt_ids
                or any(not value for value in authority_receipt_ids)
                or len(authority_receipt_ids) != len(set(authority_receipt_ids))
            ):
                raise PhysicalLineageError(
                    "AUTHORITY_RECEIPT_IDENTITIES_REQUIRED",
                    "At least one non-empty, unique authority-review receipt identity "
                    "is required. It does not grant compounding authority.",
                )
            order_sha256 = stable_json_hash(
                [item["command_identity_sha256"] for item in normalized_lines]
            )
            inventory_path = _ROOT / "inventory.txt"
            inventory_sha256 = stable_file_hash(inventory_path)
            binding_payload = {
                "schema": "lab-build-plan-physical-binding-v1",
                "build_plan_version_id": plan.id,
                "formula_version_id": formula.id,
                "formula_sha256": formula_sha256,
                "immediate_parent_formula_version_id": (
                    parent.id if parent else None
                ),
                "immediate_parent_sha256": parent_sha256,
                "inventory_snapshot_ref": "inventory.txt",
                "inventory_snapshot_sha256": inventory_sha256,
                "stock_lineage_receipts": stock_receipt_ids,
                "release_authority_receipt_ids": authority_receipt_ids,
                "order_policy": str(order_policy),
                "order_sha256": order_sha256,
                "lines": normalized_lines,
                **_FALSE_AUTHORITY,
            }
            content_sha256 = stable_json_hash(binding_payload)
            if existing is not None:
                if existing.content_sha256 == content_sha256:
                    return existing
                raise PhysicalLineageConflictError(
                    "PHYSICAL_BINDING_ALREADY_EXISTS",
                    "The build-plan version already has a different binding.",
                )
            binding = LabBuildPlanPhysicalBinding(
                build_plan_version_id=plan.id,
                formula_version_id=formula.id,
                formula_sha256=formula_sha256,
                immediate_parent_formula_version_id=parent.id if parent else None,
                immediate_parent_sha256=parent_sha256,
                inventory_snapshot_ref="inventory.txt",
                inventory_snapshot_sha256=inventory_sha256,
                stock_lineage_receipts_json=stock_receipt_ids,
                release_authority_receipt_ids_json=authority_receipt_ids,
                order_policy=str(order_policy),
                order_sha256=order_sha256,
                content_sha256=content_sha256,
                **_FALSE_AUTHORITY,
            )
            self.session.add(binding)
            await self.session.flush()
            for item in normalized_lines:
                self.session.add(
                    LabBuildPlanLinePhysicalBinding(
                        build_plan_physical_binding_id=binding.id,
                        build_plan_line_id=item["build_plan_line_id"],
                        formula_component_id=item["formula_component_id"],
                        basket=item["basket"],
                        operation=item["operation"],
                        stock_solution_id=item["stock_solution_id"],
                        concentration_fraction_decimal=item[
                            "concentration_fraction_decimal"
                        ],
                        concentration_basis=item["concentration_basis"],
                        carrier=item["carrier"],
                        stock_preparation_receipt_id=item[
                            "stock_preparation_receipt_id"
                        ],
                        amount_decimal=item["amount_decimal"],
                        amount_unit=item["amount_unit"],
                        density_g_ml_decimal=item["density_g_ml_decimal"],
                        density_provenance=item["density_provenance"],
                        command_sequence=item["sequence"],
                        command_identity_sha256=item[
                            "command_identity_sha256"
                        ],
                        content_sha256=item["content_sha256"],
                        **_FALSE_AUTHORITY,
                    )
                )
            await self.session.flush()
            return binding

    async def _physical_binding(
        self, build_plan_version_id: str
    ) -> LabBuildPlanPhysicalBinding | None:
        return cast(
            LabBuildPlanPhysicalBinding | None,
            await self.session.scalar(
                select(LabBuildPlanPhysicalBinding).where(
                    LabBuildPlanPhysicalBinding.build_plan_version_id
                    == build_plan_version_id
                )
            ),
        )

    async def _physical_lines(
        self, binding_id: str
    ) -> list[LabBuildPlanLinePhysicalBinding]:
        return list(
            await self.session.scalars(
                select(LabBuildPlanLinePhysicalBinding)
                .where(
                    LabBuildPlanLinePhysicalBinding.build_plan_physical_binding_id
                    == binding_id
                )
                .order_by(LabBuildPlanLinePhysicalBinding.command_sequence)
            )
        )

    async def _compounding_run_for_plan(
        self, logical_plan_id: str
    ) -> LabCompoundingRun | None:
        return cast(
            LabCompoundingRun | None,
            await self.session.scalar(
                select(LabCompoundingRun).where(
                    LabCompoundingRun.logical_plan_id == logical_plan_id
                )
            ),
        )

    async def _compounding_receipts(
        self, run_id: str
    ) -> list[LabCompoundingCommandReceipt]:
        return list(
            await self.session.scalars(
                select(LabCompoundingCommandReceipt)
                .where(LabCompoundingCommandReceipt.compounding_run_id == run_id)
                .order_by(LabCompoundingCommandReceipt.sequence)
            )
        )

    async def _active_reservation_for_line(
        self, line_id: str
    ) -> LabInventoryReservationEvent | None:
        events = list(
            await self.session.scalars(
                select(LabInventoryReservationEvent)
                .where(LabInventoryReservationEvent.build_plan_line_id == line_id)
                .order_by(
                    LabInventoryReservationEvent.reservation_id,
                    LabInventoryReservationEvent.sequence,
                )
            )
        )
        latest: dict[str, LabInventoryReservationEvent] = {}
        for event in events:
            latest[event.reservation_id] = event
        active = [event for event in latest.values() if event.state == "RESERVED"]
        if len(active) != 1:
            return None
        return active[0]

    async def _physical_readiness_packet(
        self,
        *,
        plan: LabBuildPlanVersion,
        binding: LabBuildPlanPhysicalBinding,
    ) -> dict[str, Any]:
        """Derive a deterministic, non-authorizing preflight packet."""

        missing: list[dict[str, Any]] = []
        inventory_path = _ROOT / binding.inventory_snapshot_ref
        inventory_current_hash = (
            stable_file_hash(inventory_path) if inventory_path.is_file() else None
        )
        if inventory_current_hash != binding.inventory_snapshot_sha256:
            missing.append(
                {
                    "code": "INVENTORY_SNAPSHOT_DRIFT",
                    "expected_sha256": binding.inventory_snapshot_sha256,
                    "observed_sha256": inventory_current_hash,
                }
            )
        if plan.status not in {"APPROVED", "RESERVED", "EXECUTING"}:
            missing.append(
                {
                    "code": "BUILD_PLAN_STATUS_NOT_EXECUTION_ELIGIBLE",
                    "observed_status": plan.status,
                }
            )
        lines = await self._physical_lines(binding.id)
        if not lines or stable_json_hash(
            [line.command_identity_sha256 for line in lines]
        ) != binding.order_sha256:
            missing.append({"code": "PHYSICAL_ORDER_HASH_MISMATCH"})
        run = await self._compounding_run_for_plan(plan.plan_id)
        run_receipts = (
            await self._compounding_receipts(run.id) if run is not None else []
        )
        completed_line_ids = {
            receipt.line_physical_binding_id
            for receipt in run_receipts
            if receipt.command_type == "TRANSFER"
            and receipt.status == "COMPLETED"
        }
        if any(receipt.command_type == "CANCEL" for receipt in run_receipts):
            missing.append({"code": "LOGICAL_PLAN_CANCELLED"})

        formula = await self.session.get(LabFormulaVersion, binding.formula_version_id)
        if formula is None:
            missing.append({"code": "BOUND_FORMULA_VERSION_MISSING"})
        elif formula.version_number > 1 and (
            binding.immediate_parent_formula_version_id is None
            or binding.immediate_parent_sha256 is None
        ):
            missing.append({"code": "IMMEDIATE_PARENT_BINDING_MISSING"})

        required_stock_ids = {line.stock_solution_id for line in lines}
        receipt_ids = [
            str(value).strip() for value in binding.stock_lineage_receipts_json
        ]
        lot_receipts = list(
            await self.session.scalars(
                select(LabStockLotPhysicalReceipt).where(
                    LabStockLotPhysicalReceipt.id.in_(receipt_ids)
                )
            )
        ) if receipt_ids else []
        receipt_stock_ids = {receipt.stock_solution_id for receipt in lot_receipts}
        for stock_id in sorted(required_stock_ids - receipt_stock_ids):
            missing.append(
                {
                    "code": "STOCK_LOT_BOTTLE_HOMOGENEITY_RECEIPT_MISSING",
                    "stock_solution_id": stock_id,
                }
            )
        if len(lot_receipts) != len(receipt_ids):
            missing.append({"code": "STOCK_LOT_RECEIPT_REFERENCE_INVALID"})
        if not binding.release_authority_receipt_ids_json:
            missing.append({"code": "AUTHORITY_REVIEW_RECEIPT_MISSING"})

        equipment = {"labeled_destination_vessel", "plan_and_stock_labels"}
        prepared_dilutions: list[dict[str, Any]] = []
        command_rows: list[dict[str, Any]] = []
        cumulative_liquid_ul = Decimal(0)
        cumulative_solid_mg = Decimal(0)
        reservation_ids: dict[str, str] = {}
        for line in lines:
            amount = _decimal(line.amount_decimal, "amount_decimal", positive=True)
            if line.amount_unit in {"uL", "mL"}:
                equipment.add("calibrated_volume_transfer_device")
                liquid_ul = (
                    amount if line.amount_unit == "uL" else amount * Decimal(1000)
                )
                cumulative_liquid_ul += liquid_ul
                if liquid_ul < Decimal(10):
                    equipment.add("prepared_dilution_vessel_and_label")
                    requirement = {
                        "line_physical_binding_id": line.id,
                        "stock_solution_id": line.stock_solution_id,
                        "target_amount_decimal": line.amount_decimal,
                        "target_amount_unit": line.amount_unit,
                        "stock_preparation_receipt_id": (
                            line.stock_preparation_receipt_id
                        ),
                    }
                    prepared_dilutions.append(requirement)
                    if line.stock_preparation_receipt_id is None:
                        missing.append(
                            {
                                "code": "SUB_10_UL_PREPARED_DILUTION_REQUIRED",
                                **requirement,
                            }
                        )
            else:
                equipment.add("calibrated_mass_balance")
                solid_mg = (
                    amount if line.amount_unit == "mg" else amount * Decimal(1000)
                )
                cumulative_solid_mg += solid_mg
            is_completed = line.id in completed_line_ids
            if not is_completed:
                reservation = await self._active_reservation_for_line(
                    line.build_plan_line_id
                )
                if (
                    reservation is None
                    or reservation.stock_solution_id != line.stock_solution_id
                ):
                    missing.append(
                        {
                            "code": "ACTIVE_EXACT_RESERVATION_MISSING",
                            "build_plan_line_id": line.build_plan_line_id,
                            "stock_solution_id": line.stock_solution_id,
                        }
                    )
                else:
                    reservation_ids[line.id] = reservation.reservation_id
            command_rows.append(
                {
                    "sequence": line.command_sequence,
                    "basket": line.basket,
                    "operation": line.operation,
                    "stock_solution_id": line.stock_solution_id,
                    "target_amount_decimal": line.amount_decimal,
                    "target_amount_unit": line.amount_unit,
                    "reservation_id": reservation_ids.get(line.id),
                    "cumulative_liquid_uL": _decimal_text(cumulative_liquid_ul),
                    "cumulative_solid_mg": _decimal_text(cumulative_solid_mg),
                    "completion_state": (
                        "COMPLETED" if is_completed else "PENDING"
                    ),
                    "server_command_required": not is_completed,
                    "physical_instruction_authorized": False,
                }
            )
        if lines and len(completed_line_ids) == len(lines) and not missing:
            readiness_state = "ALREADY_COMPOUNDED"
        elif not missing:
            readiness_state = "READY_FOR_SERVER_SELECTED_COMMAND"
        else:
            readiness_state = "HOLD_MISSING_REQUIREMENTS"
        payload: dict[str, Any] = {
            "schema_version": "lab-compounding-readiness-packet-v1",
            "outcome": readiness_state,
            "build_plan_version_id": plan.id,
            "logical_plan_id": plan.plan_id,
            "physical_binding_id": binding.id,
            "formula_sha256": binding.formula_sha256,
            "inventory_snapshot_sha256": binding.inventory_snapshot_sha256,
            "order_sha256": binding.order_sha256,
            "missing_requirements": missing,
            "prepared_dilutions": prepared_dilutions,
            "required_equipment": sorted(equipment),
            "basket_commands": command_rows,
            "expected_totals": {
                "liquid_uL": _decimal_text(cumulative_liquid_ul),
                "solid_mg": _decimal_text(cumulative_solid_mg),
                "combined_total": None,
                "reason": "Mass and volume remain dimensionally separate.",
            },
            "operation_count": len(command_rows),
            "stop_points": [
                "Stop before any line whose server-selected command is unavailable.",
                "Stop on stock, order, parent, inventory, amount, or unit drift.",
                "Stop if a measurement cannot be linked to the selected command.",
            ],
            "recovery": {
                "partial_run": "Resume only from the first unreceipted server-selected line.",
                "completed_run": "Return ALREADY_COMPOUNDED; never restart the logical plan.",
                "cancelled_run": "Reservations remain released; create a separately reviewed plan.",
            },
            "physical_instruction_authorized": False,
            **_FALSE_AUTHORITY,
        }
        payload["readiness_sha256"] = stable_json_hash(payload)
        return payload

    async def physical_readiness_packet(
        self, *, build_plan_version_id: str
    ) -> dict[str, Any]:
        async with self._transaction():
            plan = await self.session.get(LabBuildPlanVersion, build_plan_version_id)
            if plan is None:
                raise PhysicalLineageError(
                    "BUILD_PLAN_NOT_FOUND", "The build-plan version does not exist."
                )
            binding = await self._physical_binding(build_plan_version_id)
            if binding is None:
                payload: dict[str, Any] = {
                    "schema_version": "lab-compounding-readiness-packet-v1",
                    "outcome": "HOLD_MISSING_REQUIREMENTS",
                    "build_plan_version_id": plan.id,
                    "logical_plan_id": plan.plan_id,
                    "physical_binding_id": None,
                    "missing_requirements": [
                        {"code": "EXACT_PHYSICAL_BINDING_MISSING"}
                    ],
                    "prepared_dilutions": [],
                    "required_equipment": [],
                    "basket_commands": [],
                    "expected_totals": {
                        "liquid_uL": "0",
                        "solid_mg": "0",
                        "combined_total": None,
                        "reason": "Mass and volume remain dimensionally separate.",
                    },
                    "operation_count": 0,
                    "stop_points": ["Do not begin physical work."],
                    "recovery": {
                        "missing_binding": "Create and review exact immutable bindings first."
                    },
                    "physical_instruction_authorized": False,
                    **_FALSE_AUTHORITY,
                }
                payload["readiness_sha256"] = stable_json_hash(payload)
                return payload
            return await self._physical_readiness_packet(plan=plan, binding=binding)

    async def next_compounding_command(
        self,
        *,
        build_plan_version_id: str,
        operator: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        async with self._transaction():
            plan = await self.session.get(LabBuildPlanVersion, build_plan_version_id)
            binding = await self._physical_binding(build_plan_version_id)
            if plan is None or binding is None:
                return self._command_hold(
                    "ORDER_DRIFT_HOLD", "EXACT_PHYSICAL_BINDING_MISSING"
                )
            inventory_path = _ROOT / binding.inventory_snapshot_ref
            if (
                not inventory_path.is_file()
                or stable_file_hash(inventory_path)
                != binding.inventory_snapshot_sha256
            ):
                return self._command_hold(
                    "ORDER_DRIFT_HOLD", "INVENTORY_SNAPSHOT_DRIFT"
                )
            lines = await self._physical_lines(binding.id)
            if not lines or stable_json_hash(
                [line.command_identity_sha256 for line in lines]
            ) != binding.order_sha256:
                return self._command_hold(
                    "ORDER_DRIFT_HOLD", "PHYSICAL_ORDER_HASH_MISMATCH"
                )
            run = await self._compounding_run_for_plan(plan.plan_id)
            if run is not None and (
                run.physical_binding_id != binding.id
                or run.order_sha256 != binding.order_sha256
            ):
                return self._command_hold(
                    "ORDER_DRIFT_HOLD", "RUN_BINDING_OR_ORDER_DRIFT"
                )
            receipts = (
                await self._compounding_receipts(run.id) if run is not None else []
            )
            if any(receipt.command_type == "CANCEL" for receipt in receipts):
                return self._command_hold(
                    "ORDER_DRIFT_HOLD", "LOGICAL_PLAN_CANCELLED"
                )
            completed = {
                receipt.line_physical_binding_id
                for receipt in receipts
                if receipt.command_type == "TRANSFER"
                and receipt.status == "COMPLETED"
            }
            remaining = [line for line in lines if line.id not in completed]
            if not remaining:
                assert run is not None
                return {
                    "schema_version": "lab-compounding-next-command-response-v1",
                    "outcome": "ALREADY_COMPOUNDED",
                    "run_id": run.id,
                    "command": None,
                    **_FALSE_AUTHORITY,
                }
            readiness = await self._physical_readiness_packet(
                plan=plan, binding=binding
            )
            if readiness["outcome"] != "READY_FOR_SERVER_SELECTED_COMMAND":
                held = self._command_hold(
                    "ORDER_DRIFT_HOLD", "PHYSICAL_READINESS_INCOMPLETE"
                )
                held["readiness"] = readiness
                return held
            if run is None:
                content = {
                    "schema": "lab-compounding-run-v1",
                    "logical_plan_id": plan.plan_id,
                    "build_plan_version_id": plan.id,
                    "physical_binding_id": binding.id,
                    "order_sha256": binding.order_sha256,
                    "operator": str(operator).strip(),
                    "idempotency_key_sha256": _hash_key(idempotency_key),
                    **_FALSE_AUTHORITY,
                }
                run = LabCompoundingRun(
                    logical_plan_id=plan.plan_id,
                    build_plan_version_id=plan.id,
                    physical_binding_id=binding.id,
                    order_sha256=binding.order_sha256,
                    operator=str(operator).strip(),
                    started_at=datetime.now(timezone.utc),
                    content_sha256=stable_json_hash(content),
                    **_FALSE_AUTHORITY,
                )
                self.session.add(run)
                await self.session.flush()
            line = remaining[0]
            reservation = await self._active_reservation_for_line(
                line.build_plan_line_id
            )
            if (
                reservation is None
                or reservation.stock_solution_id != line.stock_solution_id
            ):
                return self._command_hold(
                    "ORDER_DRIFT_HOLD", "ACTIVE_EXACT_RESERVATION_MISSING"
                )
            outcome = "RESUME_EXISTING" if completed else "NEXT_LINE_READY"
            return {
                "schema_version": "lab-compounding-next-command-response-v1",
                "outcome": outcome,
                "run_id": run.id,
                "command": {
                    "command_id": self._line_command_id(line),
                    "sequence": line.command_sequence,
                    "basket": line.basket,
                    "operation": line.operation,
                    "stock_solution_id": line.stock_solution_id,
                    "reservation_id": reservation.reservation_id,
                    "target_amount_decimal": line.amount_decimal,
                    "target_amount_unit": line.amount_unit,
                    "density_g_ml_decimal": line.density_g_ml_decimal,
                    "density_provenance": line.density_provenance,
                    "physical_instruction_authorized": False,
                },
                **_FALSE_AUTHORITY,
            }

    @staticmethod
    def _line_command_id(line: LabBuildPlanLinePhysicalBinding) -> str:
        return f"line-{line.command_sequence}-{line.command_identity_sha256[:48]}"

    @staticmethod
    def _command_hold(outcome: str, reason: str) -> dict[str, Any]:
        return {
            "schema_version": "lab-compounding-next-command-response-v1",
            "outcome": outcome,
            "reason": reason,
            "command": None,
            **_FALSE_AUTHORITY,
        }

    @staticmethod
    def _line_expected_mass_g(
        line: LabBuildPlanLinePhysicalBinding,
    ) -> Decimal:
        amount = _decimal(line.amount_decimal, "amount_decimal", positive=True)
        if line.amount_unit == "g":
            return amount
        if line.amount_unit == "mg":
            return amount / Decimal(1000)
        density = _decimal(
            line.density_g_ml_decimal,
            "density_g_ml_decimal",
            positive=True,
        )
        volume_ml = amount if line.amount_unit == "mL" else amount / Decimal(1000)
        return volume_ml * density

    async def complete_compounding_command(
        self,
        *,
        build_plan_version_id: str,
        command_id: str,
        bottle_action_commit_id: str,
        operator: str,
        completed_at: datetime,
        idempotency_key: str,
    ) -> dict[str, Any]:
        key_sha256 = _hash_key(idempotency_key)
        async with self._transaction():
            replay = await self.session.scalar(
                select(LabCompoundingCommandReceipt).where(
                    LabCompoundingCommandReceipt.idempotency_key_sha256
                    == key_sha256
                )
            )
            plan = await self.session.get(LabBuildPlanVersion, build_plan_version_id)
            binding = await self._physical_binding(build_plan_version_id)
            if plan is None or binding is None:
                raise PhysicalLineageConflictError(
                    "PHYSICAL_BINDING_MISSING",
                    "The exact plan binding is unavailable.",
                )
            run = await self._compounding_run_for_plan(plan.plan_id)
            if run is None:
                raise PhysicalLineageConflictError(
                    "COMPOUNDING_RUN_NOT_STARTED",
                    "Request the server-selected next command first.",
                )
            lines = await self._physical_lines(binding.id)
            line = next(
                (item for item in lines if self._line_command_id(item) == command_id),
                None,
            )
            if line is None:
                raise PhysicalLineageConflictError(
                    "COMPOUNDING_COMMAND_NOT_FOUND",
                    "The command is not part of the bound order.",
                )
            command_payload = {
                "schema": "lab-compounding-command-complete-v1",
                "run_id": run.id,
                "command_id": command_id,
                "line_physical_binding_id": line.id,
                "bottle_action_commit_id": bottle_action_commit_id,
                "operator": str(operator).strip(),
                "completed_at": _aware(completed_at, "completed_at").isoformat(),
            }
            command_sha256 = stable_json_hash(command_payload)
            if replay is not None:
                if replay.command_sha256 == command_sha256:
                    return self._receipt_response(replay)
                raise PhysicalLineageConflictError(
                    "COMPOUNDING_IDEMPOTENCY_MISMATCH",
                    "The idempotency key was reused for a different completion.",
                )
            receipts = await self._compounding_receipts(run.id)
            if any(receipt.command_type == "CANCEL" for receipt in receipts):
                raise PhysicalLineageConflictError(
                    "COMPOUNDING_RUN_CANCELLED",
                    "A cancelled logical plan cannot accept a completion.",
                )
            completed_line_ids = {
                receipt.line_physical_binding_id
                for receipt in receipts
                if receipt.command_type == "TRANSFER"
            }
            next_line = next(
                (item for item in lines if item.id not in completed_line_ids), None
            )
            if next_line is None or next_line.id != line.id:
                existing = next(
                    (
                        receipt
                        for receipt in receipts
                        if receipt.line_physical_binding_id == line.id
                    ),
                    None,
                )
                if existing is not None and existing.command_sha256 == command_sha256:
                    return self._receipt_response(existing)
                raise PhysicalLineageConflictError(
                    "COMPOUNDING_ORDER_DRIFT",
                    "Only the first unreceipted line may be completed.",
                )
            commit = await self.session.get(
                LabBottleActionCommit, bottle_action_commit_id
            )
            if commit is None:
                raise PhysicalLineageConflictError(
                    "BOTTLE_ACTION_COMMIT_NOT_FOUND",
                    "Completion requires an existing immutable bottle-action commit.",
                )
            proposal = await self.session.get(
                LabBottleActionProposal, commit.proposal_id
            )
            reservation = await self.session.get(
                LabInventoryReservationEvent,
                commit.fulfilled_reservation_event_id,
            )
            if proposal is None or reservation is None:
                raise PhysicalLineageConflictError(
                    "PHYSICAL_ACTION_LINEAGE_INCOMPLETE",
                    "The bottle action lacks proposal or reservation lineage.",
                )
            if (
                proposal.stock_solution_id != line.stock_solution_id
                or reservation.stock_solution_id != line.stock_solution_id
                or reservation.build_plan_line_id != line.build_plan_line_id
                or reservation.state != "FULFILLED"
            ):
                raise PhysicalLineageConflictError(
                    "PHYSICAL_ACTION_BINDING_MISMATCH",
                    "The committed action does not match the bound line and reservation.",
                )
            expected_mass = self._line_expected_mass_g(line)
            if abs(Decimal(str(proposal.planned_mass_g)) - expected_mass) > Decimal(
                "0.000000000001"
            ):
                raise PhysicalLineageConflictError(
                    "PHYSICAL_ACTION_AMOUNT_MISMATCH",
                    "The committed action mass does not match the exact line conversion.",
                )
            previous = receipts[-1] if receipts else None
            receipt_payload = {
                **command_payload,
                "sequence": len(receipts) + 1,
                "stock_solution_id": line.stock_solution_id,
                "reservation_event_id": reservation.id,
                "amount_decimal": line.amount_decimal,
                "amount_unit": line.amount_unit,
                "parent_receipt_sha256": (
                    previous.receipt_sha256 if previous else None
                ),
                "bottle_id": proposal.bottle_id,
                **_FALSE_AUTHORITY,
            }
            if receipts:
                first_bottle_id = receipts[0].detail_json.get("bottle_id")
                if first_bottle_id and first_bottle_id != proposal.bottle_id:
                    raise PhysicalLineageConflictError(
                        "COMPOUNDING_BOTTLE_MISMATCH",
                        "All receipts for a logical plan must use one bottle.",
                    )
            receipt = LabCompoundingCommandReceipt(
                compounding_run_id=run.id,
                sequence=len(receipts) + 1,
                command_id=command_id,
                command_type="TRANSFER",
                status="COMPLETED",
                line_physical_binding_id=line.id,
                bottle_action_commit_id=commit.id,
                reservation_event_id=reservation.id,
                stock_solution_id=line.stock_solution_id,
                amount_decimal=line.amount_decimal,
                amount_unit=line.amount_unit,
                operator=str(operator).strip(),
                completed_at=_aware(completed_at, "completed_at"),
                detail_json={
                    "bottle_id": proposal.bottle_id,
                    "bottle_event_id": commit.bottle_event_id,
                    "physical_action_preexisted": True,
                },
                idempotency_key_sha256=key_sha256,
                command_sha256=command_sha256,
                parent_receipt_sha256=(
                    previous.receipt_sha256 if previous else None
                ),
                receipt_sha256=stable_json_hash(receipt_payload),
                **_FALSE_AUTHORITY,
            )
            self.session.add(receipt)
            await self.session.flush()
            return self._receipt_response(receipt)

    @staticmethod
    def _receipt_response(
        receipt: LabCompoundingCommandReceipt,
    ) -> dict[str, Any]:
        return {
            "schema_version": "lab-compounding-command-receipt-v1",
            "outcome": "COMPLETED",
            "receipt_id": receipt.id,
            "command_id": receipt.command_id,
            "sequence": receipt.sequence,
            "receipt_sha256": receipt.receipt_sha256,
            "replay_safe": True,
            **_FALSE_AUTHORITY,
        }

    async def cancel_compounding_plan(
        self,
        *,
        build_plan_version_id: str,
        operator: str,
        reason: str,
        cancelled_at: datetime,
        idempotency_key: str,
    ) -> dict[str, Any]:
        key_sha256 = _hash_key(idempotency_key)
        async with self._transaction():
            replay = await self.session.scalar(
                select(LabCompoundingCommandReceipt).where(
                    LabCompoundingCommandReceipt.idempotency_key_sha256
                    == key_sha256
                )
            )
            if replay is not None:
                return {
                    "schema_version": "lab-compounding-cancel-response-v1",
                    "outcome": "CANCELLED",
                    "released_reservations": replay.detail_json.get(
                        "released_reservations", []
                    ),
                    "receipt_id": replay.id,
                    **_FALSE_AUTHORITY,
                }
            plan = await self.session.get(LabBuildPlanVersion, build_plan_version_id)
            if plan is None:
                raise PhysicalLineageError(
                    "BUILD_PLAN_NOT_FOUND", "The build-plan version does not exist."
                )
            version_ids = list(
                await self.session.scalars(
                    select(LabBuildPlanVersion.id).where(
                        LabBuildPlanVersion.plan_id == plan.plan_id
                    )
                )
            )
            events = list(
                await self.session.scalars(
                    select(LabInventoryReservationEvent)
                    .where(
                        LabInventoryReservationEvent.build_plan_version_id.in_(
                            version_ids
                        )
                    )
                    .order_by(
                        LabInventoryReservationEvent.reservation_id,
                        LabInventoryReservationEvent.sequence,
                    )
                )
            )
            latest: dict[str, LabInventoryReservationEvent] = {}
            for event in events:
                latest[event.reservation_id] = event
            cancel_prefix = f"cp2-cancel:{key_sha256}:"
            previously_released = sorted(
                event.reservation_id
                for event in latest.values()
                if event.state == "RELEASED"
                and str(event.idempotency_key).startswith(cancel_prefix)
            )
            if previously_released:
                return {
                    "schema_version": "lab-compounding-cancel-response-v1",
                    "outcome": "CANCELLED",
                    "released_reservations": previously_released,
                    "receipt_id": None,
                    **_FALSE_AUTHORITY,
                }
            released: list[str] = []
            for current in latest.values():
                if current.state != "RESERVED":
                    continue
                command_sha256 = stable_json_hash(
                    {
                        "schema": "cp2-cancel-reservation-v1",
                        "reservation_id": current.reservation_id,
                        "parent_event_id": current.id,
                        "cancel_idempotency_key_sha256": key_sha256,
                    }
                )
                release_event = LabInventoryReservationEvent(
                    reservation_id=current.reservation_id,
                    sequence=current.sequence + 1,
                    parent_event_id=current.id,
                    build_plan_version_id=current.build_plan_version_id,
                    build_plan_line_id=current.build_plan_line_id,
                    stock_solution_id=current.stock_solution_id,
                    state="RELEASED",
                    reserved_mass_g=current.reserved_mass_g,
                    idempotency_key=(
                        f"cp2-cancel:{key_sha256}:{current.reservation_id}"
                    ),
                    command_sha256=command_sha256,
                    actor=str(operator).strip(),
                    rationale=str(reason).strip(),
                )
                self.session.add(release_event)
                await self.session.flush()
                stock = await self.repository.get_stock(current.stock_solution_id)
                if stock is None:
                    raise PhysicalLineageConflictError(
                        "RESERVATION_STOCK_NOT_FOUND",
                        "A reservation stock disappeared during cancellation.",
                    )
                balance = await self.repository.stock_balance_g(stock.id)
                await self._append_inventory_movement(
                    stock=stock,
                    movement_type="RESERVATION_RELEASE",
                    raw_quantity=current.reserved_mass_g,
                    balance_before=balance,
                    balance_after=balance,
                    actor=str(operator).strip(),
                    transaction_id=current.reservation_id,
                    idempotency_key=f"movement:cp2-cancel:{release_event.id}",
                    reason="cp2_logical_plan_cancel",
                    mass_delta_g=0.0,
                    build_plan_line_id=current.build_plan_line_id,
                    reservation_event_id=release_event.id,
                )
                released.append(current.reservation_id)
            run = await self._compounding_run_for_plan(plan.plan_id)
            receipt_id = None
            if run is not None:
                receipts = await self._compounding_receipts(run.id)
                previous = receipts[-1] if receipts else None
                payload = {
                    "schema": "lab-compounding-cancel-v1",
                    "run_id": run.id,
                    "operator": str(operator).strip(),
                    "reason": str(reason).strip(),
                    "cancelled_at": _aware(
                        cancelled_at, "cancelled_at"
                    ).isoformat(),
                    "released_reservations": sorted(released),
                    "parent_receipt_sha256": (
                        previous.receipt_sha256 if previous else None
                    ),
                    **_FALSE_AUTHORITY,
                }
                receipt = LabCompoundingCommandReceipt(
                    compounding_run_id=run.id,
                    sequence=len(receipts) + 1,
                    command_id=f"cancel-{key_sha256[:48]}",
                    command_type="CANCEL",
                    status="CANCELLED",
                    line_physical_binding_id=None,
                    bottle_action_commit_id=None,
                    reservation_event_id=None,
                    stock_solution_id=None,
                    amount_decimal=None,
                    amount_unit=None,
                    operator=str(operator).strip(),
                    completed_at=_aware(cancelled_at, "cancelled_at"),
                    detail_json={
                        "reason": str(reason).strip(),
                        "released_reservations": sorted(released),
                    },
                    idempotency_key_sha256=key_sha256,
                    command_sha256=stable_json_hash(payload),
                    parent_receipt_sha256=(
                        previous.receipt_sha256 if previous else None
                    ),
                    receipt_sha256=stable_json_hash(payload),
                    **_FALSE_AUTHORITY,
                )
                self.session.add(receipt)
                await self.session.flush()
                receipt_id = receipt.id
            return {
                "schema_version": "lab-compounding-cancel-response-v1",
                "outcome": "CANCELLED",
                "released_reservations": sorted(released),
                "receipt_id": receipt_id,
                **_FALSE_AUTHORITY,
            }


__all__ = [
    "LabPhysicalLineageServiceMixin",
    "PhysicalLineBindingInput",
    "PhysicalLineageConflictError",
    "PhysicalLineageError",
]
