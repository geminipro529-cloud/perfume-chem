"""Local-only SolForge Workbench transport endpoints."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.solforge_workbench import (
    SolForgeWorkbenchDesignRequestV1,
    SolForgeWorkbenchDesignResponseV1,
    SolForgeWorkbenchStatusV1,
)
from app.services.solforge_workbench import (
    SolForgeWorkbenchService,
    WorkbenchFailure,
    resolve_runtime_config,
)

router = APIRouter()


class _WorkbenchService(Protocol):
    async def status(self) -> SolForgeWorkbenchStatusV1: ...

    async def run_design(
        self, request: SolForgeWorkbenchDesignRequestV1
    ) -> SolForgeWorkbenchDesignResponseV1: ...


class _LazyWorkbenchService:
    def __init__(self) -> None:
        self._service: SolForgeWorkbenchService | None = None

    def _resolve(self) -> SolForgeWorkbenchService:
        if self._service is None:
            self._service = SolForgeWorkbenchService(
                resolve_runtime_config(get_settings())
            )
        return self._service

    async def status(self) -> SolForgeWorkbenchStatusV1:
        return await self._resolve().status()

    async def run_design(
        self, request: SolForgeWorkbenchDesignRequestV1
    ) -> SolForgeWorkbenchDesignResponseV1:
        return await self._resolve().run_design(request)


@lru_cache
def get_solforge_workbench_service() -> _WorkbenchService:
    return _LazyWorkbenchService()


def _failure_response(exc: WorkbenchFailure) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    )


async def _read_bounded_json(request: Request, limit: int) -> object:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type != "application/json":
        raise HTTPException(
            status_code=415,
            detail={"code": "JSON_REQUIRED", "message": "application/json is required"},
        )
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_CONTENT_LENGTH", "message": "invalid length"},
            ) from exc
        if declared_length > limit:
            raise HTTPException(
                status_code=413,
                detail={"code": "REQUEST_TOO_LARGE", "message": "request exceeds limit"},
            )

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise HTTPException(
                status_code=413,
                detail={"code": "REQUEST_TOO_LARGE", "message": "request exceeds limit"},
            )
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "MALFORMED_JSON", "message": "body is not valid UTF-8 JSON"},
        ) from exc


@router.get("/status", response_model=SolForgeWorkbenchStatusV1)
async def workbench_status(
    service: _WorkbenchService = Depends(get_solforge_workbench_service),
) -> SolForgeWorkbenchStatusV1:
    try:
        return await service.status()
    except WorkbenchFailure as exc:
        raise _failure_response(exc) from exc


@router.post("/design", response_model=SolForgeWorkbenchDesignResponseV1)
async def design_experiment(
    request: Request,
    service: _WorkbenchService = Depends(get_solforge_workbench_service),
) -> SolForgeWorkbenchDesignResponseV1:
    settings = get_settings()
    payload = await _read_bounded_json(request, settings.SOLFORGE_MAX_BODY_BYTES)
    try:
        design_request = SolForgeWorkbenchDesignRequestV1.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "PACKET_INVALID", "message": "closed packet validation failed"},
        ) from exc
    try:
        return await service.run_design(design_request)
    except WorkbenchFailure as exc:
        raise _failure_response(exc) from exc


__all__ = ["get_solforge_workbench_service", "router"]
