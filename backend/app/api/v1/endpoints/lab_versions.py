"""Saved versions of formulas from the Edit a formula page.

The versions live in Kenny's own data/user folder (app/services/formula_versions.py),
not in the Lab database: a Lab formula version needs every row weighed as a Lab stock
solution, and the editor saves cards that are not weighed yet. Bottles come from the
Lab database and are tied to a version by id.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_db
from app.models.lab import LabBottle
from app.services import formula_versions as versions

router = APIRouter()


def _error(error: Exception) -> JSONResponse:
    not_found = isinstance(error, LookupError)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND if not_found else status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "FORMULA_VERSION_NOT_FOUND" if not_found else "INVALID_FORMULA_VERSION",
                "message": str(error.args[0]) if error.args else str(error),
            }
        },
    )


@router.get("/workbench/formula-versions", response_model=None)
def list_formula_versions() -> dict[str, Any] | JSONResponse:
    """Every saved formula with its versions, newest formula first; rows left out."""
    try:
        return versions.list_formulas()
    except versions.FormulaVersionError as error:
        return _error(error)


@router.get("/workbench/formula-versions/{formula_id}/{version}", response_model=None)
def get_formula_version(formula_id: str, version: int) -> dict[str, Any] | JSONResponse:
    """One version with its rows and card text."""
    try:
        return versions.get_version(formula_id, version)
    except (LookupError, versions.FormulaVersionError) as error:
        return _error(error)


@router.post("/workbench/formula-versions", response_model=None)
def save_formula_version(request: versions.FormulaVersionSave) -> JSONResponse:
    """Save the next version (201), or answer with the saved version of the same content (200)."""
    try:
        record, created = versions.save_version(request)
    except (LookupError, versions.FormulaVersionError) as error:
        return _error(error)
    # "created" says the same as the status code, for a page that reads only the body.
    return JSONResponse(
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        content={**record, "created": created},
    )


@router.post("/workbench/formula-versions/{formula_id}/{version}/bottles", response_model=None)
async def tie_formula_version_bottle(
    formula_id: str,
    version: int,
    request: versions.BottleTie,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    """Tie a Lab bottle to the version it was made from, or untie it (tied: false)."""
    bottle = await session.get(LabBottle, request.bottle_id)
    if bottle is None and request.tied:
        return _error(LookupError("No Lab bottle with that id."))
    label = bottle.label if bottle is not None else ""
    try:
        return await run_in_threadpool(versions.tie_bottle, formula_id, version, request.bottle_id, label, request.tied)
    except (LookupError, versions.FormulaVersionError) as error:
        return _error(error)
