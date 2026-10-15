"""What stops a formula from being fully checked or mixed (engine/formulation_intelligence/hold_reasons.py).

Create a formula and Edit a formula show it when a check says HOLD: per material, what is
missing and where to supply it, with the Stock page entry that answers it. Read-only:
nothing changes a formula, a card, stock or a gate verdict.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from engine.formulation_intelligence.hold_reasons import explain_holds
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

router = APIRouter()

_Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class FormulaHoldRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    stock_id: _Short | None = None
    # One bottle's amount. A weighed solid (mg) is modelled 1 mg ~ 1 uL, as the release
    # gate's yardstick does; that only matters for the IFRA totals, never for stock.
    amount: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)]
    unit: Literal["uL", "mg"] = "uL"
    fraction: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] = "1"
    basis: _Short = ""
    carrier: _Short = ""

    @field_validator("amount", "fraction")
    @classmethod
    def _decimal(cls, value: str) -> str:
        try:
            number = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("must be a decimal number") from error
        if not number.is_finite() or number < 0:
            raise ValueError("must be zero or more")
        return value


class FormulaHoldsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[FormulaHoldRow] = Field(max_length=120)
    bottle_ml: float = Field(default=30.0, gt=0, le=1000)


@router.post("/workbench/formula-holds", response_model=None)
async def formula_holds(request: FormulaHoldsRequest) -> dict[str, Any]:
    """Per material: what holds the stock and IFRA checks, and what to do about it."""
    rows = [
        {
            "material": row.material,
            "stock_id": row.stock_id or "",
            "amount_ul": row.amount,
            "fraction": row.fraction,
            "basis": row.basis,
            "carrier": row.carrier,
        }
        for row in request.rows
    ]
    answer: dict[str, Any] = await run_in_threadpool(lambda: explain_holds(rows, bottle_ml=request.bottle_ml))
    return answer
