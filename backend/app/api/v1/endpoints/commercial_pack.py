"""Printable Thai label and IFRA Category 4 self-declaration for one bottled batch.

A gate result can be posted inline or named by a path; a path is read only when it
resolves (symlinks followed) inside data/user/batches/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import PROJECT_ROOT
from app.services.commercial_label import (
    CommercialPackError,
    build_ifra_statement,
    build_label,
)

router = APIRouter()

BATCHES_RELATIVE = Path("data") / "user" / "batches"
MAX_GATE_BYTES = 32 * 1024 * 1024


class LabelRequest(BaseModel):
    fields: dict[str, Any]
    rows: list[dict[str, Any]] = Field(default_factory=list)


class IfraStatementRequest(BaseModel):
    gate_json: dict[str, Any] | None = None
    gate_path: str | None = Field(default=None, max_length=500)
    meta: dict[str, Any] = Field(default_factory=dict)


def _error(code: str, message: str, http_status: int = status.HTTP_400_BAD_REQUEST) -> JSONResponse:
    return JSONResponse(status_code=http_status, content={"error": {"code": code, "message": message}})


def _read_gate(path_text: str) -> Any:
    """Load a gate JSON that must live under data/user/batches/ (no escape)."""
    root = (PROJECT_ROOT / BATCHES_RELATIVE).resolve()
    candidate = Path(path_text)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or resolved == root or resolved.suffix != ".json":
        raise CommercialPackError(
            "gate_path_refused", "gate_path must name a .json file under data/user/batches/."
        )
    if not resolved.is_file():
        raise CommercialPackError("gate_path_missing", f"No gate result at {path_text}.")
    if resolved.stat().st_size > MAX_GATE_BYTES:
        raise CommercialPackError("gate_path_too_large", "The gate result file is too large.")
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CommercialPackError(
            "gate_path_unreadable", f"The gate result at {path_text} is not readable JSON."
        ) from error


@router.post("/label")
def make_label(request: LabelRequest) -> Any:
    try:
        return build_label(request.fields, request.rows)
    except CommercialPackError as error:
        return _error(error.code, str(error))


@router.post("/ifra-statement")
def make_ifra_statement(request: IfraStatementRequest) -> Any:
    if (request.gate_json is None) == (request.gate_path is None):
        return _error("invalid_request", "Send exactly one of gate_json or gate_path.")
    try:
        gate = request.gate_json
        if request.gate_path is not None:
            gate = _read_gate(request.gate_path)
        return build_ifra_statement(gate, request.meta)
    except CommercialPackError as error:
        http_status = (
            status.HTTP_404_NOT_FOUND if error.code == "gate_path_missing"
            else status.HTTP_400_BAD_REQUEST
        )
        return _error(error.code, str(error), http_status)
