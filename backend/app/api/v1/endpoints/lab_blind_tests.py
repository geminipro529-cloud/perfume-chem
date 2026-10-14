"""Blind tests on the Your nose page (app/services/blind_tests.py).

Two saved formula versions become vials A and B; the key stays on the server
until Kenny reveals it. Kept in his own data/user folder, not the Lab database.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.services import blind_tests

router = APIRouter()


def _error(error: Exception) -> JSONResponse:
    not_found = isinstance(error, LookupError)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND if not_found else status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "BLIND_TEST_NOT_FOUND" if not_found else "INVALID_BLIND_TEST",
                "message": str(error.args[0]) if error.args else str(error),
            }
        },
    )


@router.get("/workbench/blind-tests", response_model=None)
def list_blind_tests() -> dict[str, Any] | JSONResponse:
    """Every blind test, newest first; a test's key only after its reveal."""
    try:
        return blind_tests.list_tests()
    except blind_tests.BlindTestError as error:
        return _error(error)


@router.post("/workbench/blind-tests", response_model=None)
def create_blind_test(request: blind_tests.BlindTestCreate) -> JSONResponse:
    """Make vials A and B from two saved versions, in an order the page doesn't show."""
    try:
        test = blind_tests.create_test(request)
    except (LookupError, ValueError) as error:
        return _error(error)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=test)


@router.post("/workbench/blind-tests/{test_id}/picks", response_model=None)
def record_blind_pick(test_id: str, request: blind_tests.BlindPick) -> dict[str, Any] | JSONResponse:
    """Record the pick for one strip time; a later pick for the same time replaces it."""
    try:
        return blind_tests.record_pick(test_id, request)
    except (LookupError, blind_tests.BlindTestError) as error:
        return _error(error)


@router.post("/workbench/blind-tests/{test_id}/reveal", response_model=None)
def reveal_blind_test(test_id: str) -> dict[str, Any] | JSONResponse:
    """Show which vial is which; the picks are fixed from then on."""
    try:
        return blind_tests.reveal(test_id)
    except (LookupError, blind_tests.BlindTestError) as error:
        return _error(error)
