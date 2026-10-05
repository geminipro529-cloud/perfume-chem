"""Immutable commercial-reference sample bindings for personal comparison."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.commercial_references import (
    CommercialReferenceSampleCreate,
    CommercialReferenceSampleResponse,
)
from app.services.commercial_references import (
    CommercialReferenceConflictError,
    CommercialReferenceError,
    CommercialReferenceNotFoundError,
    commercial_reference_sample_response,
)
from app.services.lab_service import LabService

router = APIRouter()


def _error_response(error: CommercialReferenceError) -> JSONResponse:
    if isinstance(error, CommercialReferenceNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, CommercialReferenceConflictError):
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": error.code, "message": str(error)}},
    )


@router.post(
    "/commercial-reference-samples",
    status_code=status.HTTP_201_CREATED,
    response_model=CommercialReferenceSampleResponse,
)
async def link_commercial_reference_sample(
    request: CommercialReferenceSampleCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        record, reused = await service.link_commercial_reference_sample(
            **request.model_dump()
        )
        return commercial_reference_sample_response(record, reused=reused)
    except CommercialReferenceError as error:
        return _error_response(error)


@router.get(
    "/commercial-reference-samples/{record_id}",
    response_model=CommercialReferenceSampleResponse,
)
async def get_commercial_reference_sample(
    record_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        record = await service.require_commercial_reference_sample(record_id)
        return commercial_reference_sample_response(record, reused=None)
    except CommercialReferenceError as error:
        return _error_response(error)


__all__ = ["router"]
