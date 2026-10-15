"""Owned stocks like another one, and a map of the shelf by character (plan item F6).

engine/formulation_intelligence/similar_stocks.py compares the profiles written for
each stock, not smell, so every answer carries "similar, not the same". Edit a
formula previews a swap with it; What can I make lists it beside a stock that runs
short. Read-only: nothing changes a formula or stock.
"""

from __future__ import annotations

from typing import Annotated, Any

from engine.formulation_intelligence.similar_stocks import shelf_map, similar_stocks
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

router = APIRouter()


class SimilarStocksRequest(BaseModel):
    """The stock to compare: its Lab stock id, or else its material name."""

    model_config = ConfigDict(extra="forbid")

    stock_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    material: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    limit: int = Field(default=6, ge=1, le=12)

    @model_validator(mode="after")
    def _one_of(self) -> SimilarStocksRequest:
        if not (self.stock_id or self.material):
            raise ValueError("give a stock_id or a material name")
        return self


@router.post("/workbench/similar-stocks", response_model=None)
async def read_similar_stocks(request: SimilarStocksRequest) -> dict[str, Any] | JSONResponse:
    """Owned materials whose written character is closest, the stock's other bottles first."""

    def compare() -> dict[str, Any] | JSONResponse:
        try:
            return similar_stocks(request.stock_id or None, material=request.material or None, limit=request.limit)
        except LookupError as error:
            return JSONResponse(status_code=404, content={"error": {"code": "SIMILAR_STOCK_NOT_FOUND", "message": str(error)}})

    return await run_in_threadpool(compare)


@router.get("/workbench/shelf-map", response_model=None)
async def read_shelf_map() -> dict[str, Any]:
    """Every owned material placed by written character, pairs written alike, thin facets."""
    answer: dict[str, Any] = await run_in_threadpool(shelf_map)
    return answer
