"""The Buy page: what the saved cards call for that Kenny doesn't own, and his buying decisions.

GET joins the saved cards' needs (engine/buy_needs.py), PerfumersWorld list prices and
Kenny's buy log into the page (engine/buy_list.py). POST records buying decisions
(engine/buy_events.py): entries as given, or a pasted ``LABPICKS/1`` block. Nothing here
changes stock, a formula, a price or a gate verdict.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from engine.buy_events import (
    BuyEventError,
    BuyEventLogCorruptError,
    load_buy_events,
    normalize_buy_entry,
    parse_labpicks,
    record_buy_events,
)
from engine.buy_list import build_buy_list
from engine.buy_needs import card_needs, material_key
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services import formula_versions as versions

router = APIRouter()

ResponsePayload = dict[str, Any] | JSONResponse


class BuyEventsCreate(BaseModel):
    """Buy entries as objects, or a pasted LABPICKS/1 block; exactly one of the two."""

    model_config = ConfigDict(extra="forbid")

    events: Annotated[list[dict[str, Any]], Field(max_length=100)] | None = None
    labpicks: Annotated[str, Field(max_length=200_000)] | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _one_of(self) -> BuyEventsCreate:
        if (self.events is None) == (self.labpicks is None):
            raise ValueError("give exactly one of events or labpicks")
        return self


def _today() -> date:
    # Local date: the app runs on Kenny's PC.
    return date.today()


def _error(error: BuyEventError) -> JSONResponse:
    corrupt = isinstance(error, BuyEventLogCorruptError)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT if corrupt else 422,
        content={"error": {"code": error.code, "message": str(error)}},
    )


@router.get("/workbench/buy-list", response_model=None)
def read_buy_list() -> ResponsePayload:
    """What the saved cards call for that Kenny doesn't own, priced, with his decisions."""

    try:
        cards = []
        for formula in versions.list_formulas()["formulas"]:
            latest = versions.get_version(formula["formula_id"], formula["latest"])
            cards.append({key: latest[key] for key in ("formula_id", "version", "name", "bottle_ml", "rows")})
        events = load_buy_events()
    except BuyEventError as error:
        return _error(error)
    except versions.FormulaVersionError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": "FORMULA_VERSIONS_UNREADABLE", "message": str(error)}},
        )
    payload: dict[str, Any] = build_buy_list(card_needs(cards), events=events, today=_today())
    return payload


@router.post("/workbench/buy-events", response_model=None)
def record_buy_decisions(request: BuyEventsCreate) -> ResponsePayload:
    """Validate the entries, then record them all or none (or, with dry_run, record nothing)."""

    try:
        pasted = request.labpicks is not None
        entries = parse_labpicks(request.labpicks) if request.labpicks is not None else list(request.events or [])
        # The cards' needs are keyed by material_key(); a pasted "Nootkatone" is "nootkatone".
        seen: set[str] = set()
        for entry in entries:
            if isinstance(entry.get("material_key"), str):
                entry["material_key"] = material_key(entry["material_key"])
                if pasted:
                    if entry["material_key"] in seen:
                        raise BuyEventError(
                            f"LABPICKS: {entry['material_key']} is listed more than once",
                            code="BUY_LABPICKS_INVALID",
                        )
                    seen.add(entry["material_key"])
        if request.dry_run:
            normalized = [normalize_buy_entry(entry) for entry in entries]
            return {"dry_run": True, "entries": normalized, "count": len(normalized)}
        stored = record_buy_events(entries)
    except BuyEventError as error:
        return _error(error)
    return {"dry_run": False, "recorded": list(stored), "count": len(stored)}


__all__ = ["BuyEventsCreate", "router"]
