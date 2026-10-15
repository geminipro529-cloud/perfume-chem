"""Production batches: scale a card, rerun the release gate, record the batch.

Handlers are plain functions on purpose: they read and parse formula files,
and FastAPI runs a plain handler in a worker thread. The gate itself runs in a
background thread; the page polls its status.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services import batch_production as batches

router = APIRouter()


class BatchPlanRequest(BaseModel):
    source_path: str | None = Field(default=None, max_length=500)
    text: str | None = Field(default=None, max_length=2_000_000)
    name: str | None = Field(default=None, max_length=255)
    bottles: str = Field(max_length=20)
    bottle_ml: str = Field(default="30", max_length=20)
    card_total_ml: str | None = Field(default=None, max_length=20)
    loss_percent: str = Field(default="3", max_length=20)


class BatchGateRunRequest(BatchPlanRequest):
    lot: str = Field(max_length=64)


class BatchRecordRequest(BatchGateRunRequest):
    made_on: str = Field(max_length=10)
    made_by: str = Field(default="", max_length=120)
    gate_run_id: str | None = Field(default=None, max_length=64)
    notes: str = Field(default="", max_length=4000)


class BatchActual(BaseModel):
    line: int
    actual_amount: str | None = Field(default=None, max_length=20)
    # Bench mode on the phone: grams on the balance, and for a µL line the stock
    # density used to turn them into µL (the server works the µL out).
    weighed_g: str | None = Field(default=None, max_length=20)
    density_g_ml: str | None = Field(default=None, max_length=20)


class BatchActualsRequest(BaseModel):
    actuals: list[BatchActual] = Field(max_length=500)
    notes: str = Field(default="", max_length=4000)


def _error(error: Exception) -> JSONResponse:
    not_found = isinstance(error, LookupError)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND if not_found else status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "BATCH_NOT_FOUND" if not_found else "INVALID_BATCH",
                "message": str(error.args[0]) if error.args else str(error),
            }
        },
    )


def _plan(request: BatchPlanRequest) -> dict[str, Any]:
    return batches.plan_batch(
        source_path=request.source_path,
        text=request.text,
        name=request.name,
        bottles=request.bottles,
        bottle_ml=request.bottle_ml,
        card_total_ml=request.card_total_ml,
        loss_percent=request.loss_percent,
    )


@router.post("/batches/plan", response_model=None)
def plan_batch(request: BatchPlanRequest) -> dict[str, Any] | JSONResponse:
    """Scale a card to a batch; read-only."""

    try:
        plan = _plan(request)
    except ValueError as error:
        return _error(error)
    return {"schema_version": "batch-plan-v1", **plan, "inventory_modified": False}


@router.get("/batches/suggest-lot", response_model=None)
def suggest_lot(initials: str = "", day: str | None = None) -> dict[str, Any] | JSONResponse:
    try:
        when = date.fromisoformat(day) if day else date.today()
        return {"lot": batches.suggest_lot(initials, when, batches.taken_lots())}
    except ValueError as error:
        return _error(error)


@router.post("/batches/gate-runs", status_code=status.HTTP_202_ACCEPTED, response_model=None)
def start_gate_run(request: BatchGateRunRequest) -> dict[str, Any] | JSONResponse:
    """Rerun the release gate on the scaled card; poll the returned run."""

    try:
        return batches.start_gate_run(request.lot, _plan(request))
    except ValueError as error:
        return _error(error)


@router.get("/batches/gate-runs/{run_id}", response_model=None)
def gate_run(run_id: str) -> dict[str, Any] | JSONResponse:
    try:
        return batches.gate_run_status(run_id)
    except LookupError as error:
        return _error(error)


@router.post("/batches", status_code=status.HTTP_201_CREATED, response_model=None)
def record_batch(request: BatchRecordRequest) -> dict[str, Any] | JSONResponse:
    try:
        return batches.record_batch(
            lot=request.lot,
            made_on=request.made_on,
            made_by=request.made_by,
            plan=_plan(request),
            gate_run_id=request.gate_run_id,
            notes=request.notes,
        )
    except (ValueError, LookupError) as error:
        return _error(error)


@router.get("/batches", response_model=None)
def list_batches() -> dict[str, Any] | JSONResponse:
    try:
        return {"schema_version": "batch-records-v1", "records": batches.list_records()}
    except ValueError as error:
        return _error(error)


@router.get("/batches/{lot}", response_model=None)
def get_batch(lot: str) -> dict[str, Any] | JSONResponse:
    try:
        return batches.get_record(lot)
    except (ValueError, LookupError) as error:
        return _error(error)


@router.post("/batches/{lot}/actuals", response_model=None)
def record_actuals(lot: str, request: BatchActualsRequest) -> dict[str, Any] | JSONResponse:
    try:
        return batches.record_actuals(
            lot, [item.model_dump() for item in request.actuals], request.notes
        )
    except (ValueError, LookupError) as error:
        return _error(error)
