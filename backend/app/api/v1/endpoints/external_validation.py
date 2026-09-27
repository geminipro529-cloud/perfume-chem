"""Authority-safe, append-only external-validation intake API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.external_validation import (
    ExternalValidationRecordResponse,
    PairwisePreferenceIntakeRequest,
    TemporalObservationIntakeRequest,
)
from app.schemas.instrumental_observations import (
    InstrumentalObservationIntakeRequest,
    InstrumentalObservationResponse,
)
from app.services.external_validation import (
    ExternalValidationConflictError,
    ExternalValidationError,
    ExternalValidationNotFoundError,
    external_validation_record_response,
)
from app.services.instrumental_observations import (
    InstrumentalObservationConflictError,
    InstrumentalObservationError,
    InstrumentalObservationNotFoundError,
    instrumental_observation_response,
)
from app.services.lab_service import LabService

router = APIRouter()


def _error_response(error: ExternalValidationError) -> JSONResponse:
    if isinstance(error, ExternalValidationNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ExternalValidationConflictError):
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=http_status,
        content={
            "error": {
                "code": error.code,
                "message": str(error),
            }
        },
    )


def _instrumental_error_response(error: InstrumentalObservationError) -> JSONResponse:
    if isinstance(error, InstrumentalObservationNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, InstrumentalObservationConflictError):
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": error.code, "message": str(error)}},
    )


@router.post(
    "/instrumental-observations",
    status_code=status.HTTP_201_CREATED,
    response_model=InstrumentalObservationResponse,
)
async def record_instrumental_observation(
    request: InstrumentalObservationIntakeRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        record, reused = await service.record_instrumental_observation(
            **request.model_dump()
        )
        return instrumental_observation_response(record, reused=reused)
    except InstrumentalObservationError as error:
        return _instrumental_error_response(error)


@router.get(
    "/instrumental-observations/{record_id}",
    response_model=InstrumentalObservationResponse,
)
async def get_instrumental_observation(
    record_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        record = await service.require_instrumental_observation(record_id)
        return instrumental_observation_response(record, reused=None)
    except InstrumentalObservationError as error:
        return _instrumental_error_response(error)


@router.post(
    "/external-validation/temporal-observations",
    status_code=status.HTTP_201_CREATED,
    response_model=ExternalValidationRecordResponse,
)
async def record_temporal_observation(
    request: TemporalObservationIntakeRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        record, reused = await service.record_external_temporal_observation(
            **request.model_dump()
        )
        return external_validation_record_response(record, reused=reused)
    except ExternalValidationError as error:
        return _error_response(error)


@router.post(
    "/external-validation/pairwise-preferences",
    status_code=status.HTTP_201_CREATED,
    response_model=ExternalValidationRecordResponse,
)
async def record_pairwise_preference(
    request: PairwisePreferenceIntakeRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        record, reused = await service.record_external_pairwise_preference(
            **request.model_dump()
        )
        return external_validation_record_response(record, reused=reused)
    except ExternalValidationError as error:
        return _error_response(error)


@router.get(
    "/external-validation/records/{record_id}",
    response_model=ExternalValidationRecordResponse,
)
async def get_external_validation_record(
    record_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        record = await service.get_external_validation_record(record_id)
        return external_validation_record_response(record, reused=None)
    except ExternalValidationError as error:
        return _error_response(error)


__all__ = ["router"]
