"""Public durable Checkpoint-2 engine-job API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.engine_jobs import (
    EngineJobCancelRequest,
    EngineJobRequest,
    EngineJobResponse,
)
from app.services.engine_jobs import (
    EngineJobConflictError,
    EngineJobError,
    EngineJobNotFoundError,
)
from app.services.lab_service import LabService

router = APIRouter()


def _error_response(error: EngineJobError) -> JSONResponse:
    code = getattr(error, "code", "ENGINE_JOB_ERROR")
    if isinstance(error, EngineJobNotFoundError):
        http_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, EngineJobConflictError):
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": str(error)}},
    )


@router.post(
    "/engine-jobs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EngineJobResponse,
)
async def submit_engine_job(
    request: EngineJobRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        job, _reused = await service.submit_engine_job(
            job_type=request.job_type,
            payload=request.payload,
            requester=request.requester,
            idempotency_key=request.idempotency_key,
            request_schema_version=request.schema_version,
        )
        return await service.engine_job_snapshot(job.id)
    except EngineJobError as error:
        return _error_response(error)


@router.get(
    "/engine-jobs/{job_id}",
    response_model=EngineJobResponse,
)
async def get_engine_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        return await service.engine_job_snapshot(job_id)
    except EngineJobError as error:
        return _error_response(error)


@router.post(
    "/engine-jobs/{job_id}/cancel",
    response_model=EngineJobResponse,
)
async def cancel_engine_job(
    job_id: str,
    request: EngineJobCancelRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    service = LabService(session)
    try:
        await service.cancel_engine_job(
            job_id=job_id,
            requester=request.requester,
            reason=request.reason,
        )
        return await service.engine_job_snapshot(job_id)
    except EngineJobError as error:
        return _error_response(error)


__all__ = ["router"]
