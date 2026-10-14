"""What the composer reads in a name and brief (engine/formulation_intelligence/brief_notes.py).

Create a formula shows it as chips before composing; Edit a formula shows, for each
row, which of the name's notes its stock carries. Read-only: nothing changes a
formula, a card or stock, and nothing here says how strong anything smells.
"""

from __future__ import annotations

from typing import Annotated, Any

from engine.formulation_intelligence.brief_notes import row_notes, understood_notes
from fastapi import APIRouter, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

router = APIRouter()

_Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
_Word = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class BriefNotesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""
    message: _Text = ""
    must_avoid: list[_Word] = Field(default_factory=list, max_length=40)
    conversation_context: list[_Text] = Field(default_factory=list, max_length=8)


class FormulaRoleRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] = ""
    stock_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None


class FormulaRolesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    brief: _Text = ""
    rows: list[FormulaRoleRow] = Field(max_length=120)


def _error(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": {"code": "INVALID_BRIEF", "message": message}},
    )


@router.post("/workbench/brief-notes", response_model=None)
async def brief_notes(request: BriefNotesRequest) -> dict[str, Any] | JSONResponse:
    """The materials and notes the composer would design for, before composing."""
    if not (request.message or request.formula_name or any(request.conversation_context)):
        return _error("Type a name or an idea first.")
    try:
        return await run_in_threadpool(
            lambda: understood_notes(
                formula_name=request.formula_name,
                message=request.message,
                must_avoid=[word for word in request.must_avoid if word],
                conversation_context=request.conversation_context,
            )
        )
    except ValueError as error:
        return _error(str(error))


@router.post("/workbench/formula-roles", response_model=None)
async def formula_roles(request: FormulaRolesRequest) -> dict[str, Any] | JSONResponse:
    """For each row, the notes of the formula's name its stock carries."""
    try:
        return await run_in_threadpool(
            lambda: row_notes(
                formula_name=request.formula_name,
                brief=request.brief,
                rows=[row.model_dump() for row in request.rows],
            )
        )
    except ValueError as error:
        return _error(str(error))
