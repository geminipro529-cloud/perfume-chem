"""What can I make now: saved formulas against how much of each stock is left.

The page (static/make-now.js) does the arithmetic with the bench sheet's own density
and price code, so a shopping list costs a row exactly as the bench sheet would. This
file serves what it needs in one call (each saved formula's latest version with its
rows, and how much is left of each stock), and records how much is left of a stock
(engine/stock_on_hand.py). Nothing here changes a formula, the stock list the checks
use, a price or a gate verdict.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from engine.personal_inventory import materialize_personal_inventory
from engine.stock_on_hand import (
    StockOnHandError,
    StockOnHandLogCorruptError,
    latest_on_hand,
    record_on_hand,
)
from fastapi import APIRouter, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.services import formula_versions as versions

router = APIRouter()

ON_HAND_SCHEMA = "workbench-stock-on-hand-v1"
MAKE_NOW_SCHEMA = "workbench-make-now-v1"


class StockOnHandCreate(BaseModel):
    """How much is left of one stock, read off the bottle; clear removes it."""

    model_config = ConfigDict(extra="forbid")

    stock_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    amount_decimal: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    unit: Literal["mL", "g"] | None = None
    supplier: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""
    clear: bool = False


def _error(error: StockOnHandError) -> JSONResponse:
    corrupt = isinstance(error, StockOnHandLogCorruptError)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT if corrupt else 422,
        content={"error": {"code": error.code, "message": str(error)}},
    )


def _on_hand_payload(on_hand: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": ON_HAND_SCHEMA,
        "on_hand": on_hand,
        "source": "read off the bottle by you",
        "inventory_modified": False,
        "compounding_authority": False,
    }


@router.get("/workbench/stock-on-hand", response_model=None)
def read_stock_on_hand() -> dict[str, Any] | JSONResponse:
    """How much is left of each stock, as Kenny last typed it."""
    try:
        return _on_hand_payload(latest_on_hand())
    except StockOnHandError as error:
        return _error(error)


@router.post("/workbench/stock-on-hand", response_model=None)
async def write_stock_on_hand(request: StockOnHandCreate) -> dict[str, Any] | JSONResponse:
    """Append one entry; the last entry per stock wins."""

    def record() -> dict[str, Any] | JSONResponse:
        if not any(stock.stock_id == request.stock_id for stock in materialize_personal_inventory().stocks):
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "STOCK_ON_HAND_STOCK_NOT_IN_INVENTORY",
                                   "message": "That stock is not in the current inventory."}},
            )
        try:
            event = record_on_hand(
                stock_id=request.stock_id,
                amount_decimal=request.amount_decimal,
                unit=request.unit,
                supplier=request.supplier,
                note=request.note,
                clear=request.clear,
            )
            return {**_on_hand_payload(latest_on_hand()), "receipt": event}
        except StockOnHandError as error:
            return _error(error)

    return await run_in_threadpool(record)


@router.get("/workbench/make-now", response_model=None)
def read_make_now() -> dict[str, Any] | JSONResponse:
    """Each saved formula's latest version with its rows, and how much is left of each stock."""
    try:
        on_hand = latest_on_hand()
        listed = versions.list_formulas()["formulas"]
        formulas = []
        for formula in listed:
            latest = versions.get_version(formula["formula_id"], formula["latest"])
            formulas.append({
                key: latest[key]
                for key in ("formula_id", "version", "name", "bottle_ml", "saved_at", "rows")
            })
    except StockOnHandError as error:
        return _error(error)
    except versions.FormulaVersionError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": "FORMULA_VERSIONS_UNREADABLE", "message": str(error)}},
        )
    return {
        "schema_version": MAKE_NOW_SCHEMA,
        "formulas": formulas,
        "on_hand": on_hand,
        "inventory_modified": False,
        "formula_modified": False,
        "compounding_authority": False,
    }


__all__ = ["StockOnHandCreate", "router"]

