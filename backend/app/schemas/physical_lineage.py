"""Strict API contracts for exact Checkpoint-2 compounding lineage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _PhysicalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def reject_boolean_quantities(cls, value: Any, info):
        if "quantity" in info.field_name and isinstance(value, bool):
            raise ValueError("boolean is not a physical quantity")
        return value


class FinalizeStockPreparationRequest(_PhysicalRequest):
    schema_version: Literal["lab-stock-preparation-finalize-v1"]
    parent_stock_solution_id: str = Field(min_length=1, max_length=255)
    carrier_stock_solution_id: str = Field(min_length=1, max_length=255)
    prepared_stock_solution_id: str = Field(min_length=1, max_length=255)
    basis: Literal["W_W", "V_V"]
    parent_quantity_decimal: str = Field(min_length=1, max_length=128)
    parent_quantity_unit: Literal["g", "mg", "mL", "uL"]
    carrier_quantity_decimal: str = Field(min_length=1, max_length=128)
    carrier_quantity_unit: Literal["g", "mg", "mL", "uL"]
    result_quantity_decimal: str = Field(min_length=1, max_length=128)
    result_quantity_unit: Literal["g", "mg", "mL", "uL"]
    density_g_ml_decimal: str | None = Field(default=None, max_length=128)
    density_provenance: str | None = Field(default=None, max_length=1000)
    homogeneity: Literal["CONFIRMED", "FAILED"]
    label: str = Field(min_length=1, max_length=255)
    operator: str = Field(min_length=1, max_length=255)
    prepared_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=255)


class FinalizeStockLotPhysicalReceiptRequest(_PhysicalRequest):
    schema_version: Literal["lab-stock-lot-physical-receipt-v1"]
    supplier: str = Field(min_length=1, max_length=255)
    lot_number: str = Field(min_length=1, max_length=100)
    bottle_identifier: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=255)
    active_fraction_decimal: str = Field(min_length=1, max_length=128)
    fraction_basis: Literal["mass_fraction", "volume_fraction", "amount_fraction"]
    carrier: str | None = Field(default=None, max_length=255)
    density_g_ml_decimal: str | None = Field(default=None, max_length=128)
    density_provenance: str | None = Field(default=None, max_length=1000)
    preparation_state: Literal["SUPPLIER_AS_SUPPLIED", "LOCALLY_PREPARED"]
    stock_preparation_receipt_id: str | None = Field(default=None, max_length=255)
    homogeneity_state: Literal["CONFIRMED", "NOT_APPLICABLE"]
    source_reference: str = Field(min_length=1, max_length=2000)
    reviewer: str = Field(min_length=1, max_length=255)
    observed_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=255)


class NextCompoundingCommandRequest(_PhysicalRequest):
    schema_version: Literal["lab-compounding-next-command-v1"]
    operator: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)


class CompleteCompoundingCommandRequest(_PhysicalRequest):
    schema_version: Literal["lab-compounding-command-complete-v1"]
    bottle_action_commit_id: str = Field(min_length=1, max_length=255)
    operator: str = Field(min_length=1, max_length=255)
    completed_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=255)


class CancelCompoundingPlanRequest(_PhysicalRequest):
    schema_version: Literal["lab-compounding-plan-cancel-v1"]
    operator: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=1000)
    cancelled_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=255)


class PhysicalLineageResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    outcome: str
    release_authority: Literal[False] = False
    safety_authority: Literal[False] = False
    compounding_authority: Literal[False] = False


__all__ = [
    "CancelCompoundingPlanRequest",
    "CompleteCompoundingCommandRequest",
    "FinalizeStockLotPhysicalReceiptRequest",
    "FinalizeStockPreparationRequest",
    "NextCompoundingCommandRequest",
    "PhysicalLineageResponse",
]
