"""Build-plan extensions for exact, resumable physical bookkeeping."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.physical_lineage import (
    CancelCompoundingPlanRequest,
    CompleteCompoundingCommandRequest,
    FinalizeStockLotPhysicalReceiptRequest,
    FinalizeStockPreparationRequest,
    NextCompoundingCommandRequest,
    PhysicalLineageResponse,
)
from app.services.lab_service import LabService
from app.services.physical_lineage import (
    PhysicalLineageConflictError,
    PhysicalLineageError,
)

router = APIRouter()


def _error(error: PhysicalLineageError) -> JSONResponse:
    http_status = (
        status.HTTP_409_CONFLICT
        if isinstance(error, PhysicalLineageConflictError)
        else status.HTTP_400_BAD_REQUEST
    )
    if error.code.endswith("_NOT_FOUND"):
        http_status = status.HTTP_404_NOT_FOUND
    return JSONResponse(
        status_code=http_status,
        content={
            "error": {
                "code": error.code,
                "message": str(error),
                "release_authority": False,
                "safety_authority": False,
                "compounding_authority": False,
            }
        },
    )


@router.post(
    "/stock-solutions/{stock_solution_id}/physical-receipts/finalize",
    status_code=status.HTTP_201_CREATED,
    response_model=PhysicalLineageResponse,
)
async def finalize_stock_lot_physical_receipt(
    stock_solution_id: str,
    request: FinalizeStockLotPhysicalReceiptRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        receipt = await service.finalize_stock_lot_physical_receipt(
            stock_solution_id=stock_solution_id,
            **request.model_dump(exclude={"schema_version"}),
        )
        return {
            "schema_version": "lab-stock-lot-physical-receipt-response-v1",
            "outcome": "STOCK_LOT_RECEIPT_FINALIZED",
            "receipt_id": receipt.id,
            "content_sha256": receipt.content_sha256,
            "stock_solution_id": receipt.stock_solution_id,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
        }
    except PhysicalLineageError as error:
        return _error(error)


@router.post(
    "/build-plans/{version_id}/stock-preparations/finalize",
    status_code=status.HTTP_201_CREATED,
    response_model=PhysicalLineageResponse,
)
async def finalize_stock_preparation(
    version_id: str,
    request: FinalizeStockPreparationRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        receipt = await service.finalize_build_plan_stock_preparation(
            build_plan_version_id=version_id,
            **request.model_dump(exclude={"schema_version"}),
        )
        return {
            "schema_version": "lab-stock-preparation-receipt-response-v1",
            "outcome": "PREPARATION_FINALIZED",
            "receipt_id": receipt.id,
            "content_sha256": receipt.content_sha256,
            "resulting_active_fraction_decimal": (
                receipt.resulting_active_fraction_decimal
            ),
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
        }
    except PhysicalLineageError as error:
        return _error(error)


@router.get(
    "/build-plans/{version_id}/readiness",
    response_model=PhysicalLineageResponse,
)
async def get_compounding_readiness(
    version_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        return await service.physical_readiness_packet(
            build_plan_version_id=version_id
        )
    except PhysicalLineageError as error:
        return _error(error)


@router.post(
    "/build-plans/{version_id}/commands/next",
    response_model=PhysicalLineageResponse,
)
async def next_compounding_command(
    version_id: str,
    request: NextCompoundingCommandRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        return await service.next_compounding_command(
            build_plan_version_id=version_id,
            operator=request.operator,
            idempotency_key=request.idempotency_key,
        )
    except PhysicalLineageError as error:
        return _error(error)


@router.post(
    "/build-plans/{version_id}/commands/{command_id}/complete",
    status_code=status.HTTP_201_CREATED,
    response_model=PhysicalLineageResponse,
)
async def complete_compounding_command(
    version_id: str,
    command_id: str,
    request: CompleteCompoundingCommandRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        return await service.complete_compounding_command(
            build_plan_version_id=version_id,
            command_id=command_id,
            **request.model_dump(exclude={"schema_version"}),
        )
    except PhysicalLineageError as error:
        return _error(error)


@router.post(
    "/build-plans/{version_id}/cancel",
    response_model=PhysicalLineageResponse,
)
async def cancel_compounding_plan(
    version_id: str,
    request: CancelCompoundingPlanRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        return await service.cancel_compounding_plan(
            build_plan_version_id=version_id,
            **request.model_dump(exclude={"schema_version"}),
        )
    except PhysicalLineageError as error:
        return _error(error)


__all__ = ["router"]
