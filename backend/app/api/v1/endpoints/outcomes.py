"""Outcome API endpoints: record, query, and analyze formulation outcomes."""

import math
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.liking import LikingPick, LikingRating
from app.services import personal_liking
from app.services.outcome_store import OutcomeStore

router = APIRouter()


# ── Request/Response schemas ──

class OutcomeCreate(BaseModel):
    formula_name: str
    formula_version: str = "1.0"
    ingredients: dict[str, float] = Field(
        ..., description="Mapping of ingredient name → percentage"
    )
    total_volume_ml: Optional[float] = None
    concentration_pct: Optional[float] = None
    predicted_scores: Optional[dict[str, float]] = None
    rating_longevity: Optional[float] = Field(None, ge=1, le=10)
    rating_sillage: Optional[float] = Field(None, ge=1, le=10)
    rating_balance: Optional[float] = Field(None, ge=1, le=10)
    rating_overall: Optional[float] = Field(None, ge=1, le=10)
    rating_complexity: Optional[float] = Field(None, ge=1, le=10)
    notes_text: Optional[str] = None
    top_notes_observed: Optional[str] = None
    heart_notes_observed: Optional[str] = None
    base_notes_observed: Optional[str] = None
    longevity_hours: Optional[float] = None
    sillage_description: Optional[str] = None
    batch_size_ml: Optional[float] = None
    maceration_days: Optional[int] = None
    tags: Optional[list[str]] = None


class OutcomeResponse(BaseModel):
    id: int
    formula_name: str
    ingredients: dict[str, float]
    predicted_scores: Optional[dict[str, float]]
    rating_longevity: Optional[float]
    rating_sillage: Optional[float]
    rating_balance: Optional[float]
    rating_overall: Optional[float]
    rating_complexity: Optional[float]
    notes_text: Optional[str]
    tags: Optional[list[str]]

    model_config = {"from_attributes": True}


class PreferenceCreate(BaseModel):
    material_a: str
    material_b: str
    rating: int = Field(..., ge=1, le=5)
    worked_well: Optional[bool] = None
    ratio_used: Optional[str] = None
    context: Optional[str] = None
    formula_name: Optional[str] = None


class PreferenceResponse(BaseModel):
    id: int
    material_a: str
    material_b: str
    rating: int
    worked_well: Optional[bool]
    context: Optional[str]

    model_config = {"from_attributes": True}


class AccuracyResponse(BaseModel):
    axes: dict


# ── Endpoints ──

@router.post("/outcomes", response_model=OutcomeResponse, status_code=201)
async def record_outcome(body: OutcomeCreate, db: AsyncSession = Depends(get_db)):
    """Record a formulation outcome (user rates what they created)."""
    store = OutcomeStore(db)
    outcome = await store.record_outcome(body.model_dump())
    return outcome


@router.get("/outcomes", response_model=list[OutcomeResponse])
async def list_outcomes(
    skip: int = 0,
    limit: int = 50,
    formula_name: Optional[str] = None,
    min_rating: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
):
    """List recorded outcomes with optional filters."""
    store = OutcomeStore(db)
    return await store.list_outcomes(skip=skip, limit=limit,
                                     formula_name=formula_name,
                                     min_rating=min_rating)


@router.get("/outcomes/{outcome_id}", response_model=OutcomeResponse)
async def get_outcome(outcome_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single outcome by ID."""
    store = OutcomeStore(db)
    outcome = await store.get_outcome(outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return outcome


@router.patch("/outcomes/{outcome_id}", response_model=OutcomeResponse)
async def update_outcome(
    outcome_id: int, body: OutcomeCreate, db: AsyncSession = Depends(get_db),
):
    """Update an existing outcome (e.g., add ratings after maceration)."""
    store = OutcomeStore(db)
    outcome = await store.update_outcome(outcome_id, body.model_dump(exclude_unset=True))
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return outcome


@router.post("/preferences", response_model=PreferenceResponse, status_code=201)
async def record_preference(body: PreferenceCreate, db: AsyncSession = Depends(get_db)):
    """Record a pairwise ingredient preference."""
    store = OutcomeStore(db)
    pref = await store.record_preference(body.model_dump())
    return pref


@router.get("/preferences", response_model=list[PreferenceResponse])
async def list_preferences(
    material: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List pairwise preferences, optionally filtered by material."""
    store = OutcomeStore(db)
    return await store.list_preferences(material=material, skip=skip, limit=limit)


@router.get("/accuracy", response_model=AccuracyResponse)
async def prediction_accuracy(db: AsyncSession = Depends(get_db)):
    """Compare predicted scores vs actual ratings across all outcomes."""
    store = OutcomeStore(db)
    stats = await store.prediction_accuracy()
    return {"axes": stats}


@router.get("/top-ingredients")
async def top_ingredients(
    min_outcomes: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """Find ingredients that appear most often in highly-rated formulations."""
    store = OutcomeStore(db)
    return await store.top_ingredients(min_outcomes=min_outcomes)


# ── Kenny's liking ratings and two-bottle picks ──

LikingWindow = Literal["opening", "1h", "4h"]


def _checked_shares(shares: dict[str, float]) -> dict[str, float]:
    if not shares:
        raise ValueError("list at least one material share")
    for name, share in shares.items():
        if not name.strip():
            raise ValueError("material names must not be blank")
        if not math.isfinite(share) or share < 0:
            raise ValueError(f"the share for {name} must be a number of 0 or more")
    if not any(share > 0 for share in shares.values()):
        raise ValueError("at least one material share must be above 0")
    if sum(shares.values()) > 1.0001:
        raise ValueError("material shares must add up to 1 or less")
    return shares


class LikingRatingCreate(BaseModel):
    formula_name: str = Field(..., min_length=1, max_length=255)
    formula_key: str = Field(..., min_length=1, max_length=255)
    window: LikingWindow
    liking: int = Field(..., ge=1, le=10)
    complexity: Optional[int] = Field(None, ge=1, le=10)
    too_loud: Optional[str] = None
    note: Optional[str] = None
    material_shares: dict[str, float]
    crowd_guess: Optional[float] = Field(None, ge=-1, le=1)
    source: str = Field("lab_card", min_length=1, max_length=64)

    check_shares = field_validator("material_shares")(_checked_shares)


class LikingRatingResponse(LikingRatingCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LikingPickCreate(BaseModel):
    window: LikingWindow
    formula_a_name: str = Field(..., min_length=1, max_length=255)
    formula_a_key: str = Field(..., min_length=1, max_length=255)
    shares_a: dict[str, float]
    crowd_a: Optional[float] = Field(None, ge=-1, le=1)
    formula_b_name: str = Field(..., min_length=1, max_length=255)
    formula_b_key: str = Field(..., min_length=1, max_length=255)
    shares_b: dict[str, float]
    crowd_b: Optional[float] = Field(None, ge=-1, le=1)
    preferred: Literal["a", "b", "same"]
    note: Optional[str] = None

    check_shares = field_validator("shares_a", "shares_b")(_checked_shares)


class LikingPickResponse(LikingPickCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


async def _save_and_refit(db: AsyncSession) -> None:
    """Refit and rewrite data/user/personal_liking.json, then commit.

    The file is written before the commit, so a failed write leaves the change
    unsaved rather than saved beside a stale personal fit.
    """

    await db.flush()
    await personal_liking.refit_and_write(db)
    await db.commit()


@router.post("/liking/ratings", response_model=LikingRatingResponse, status_code=201)
async def record_liking_rating(body: LikingRatingCreate, db: AsyncSession = Depends(get_db)):
    """Record Kenny's liking for a bottle at one time point."""
    rating = LikingRating(**body.model_dump())
    db.add(rating)
    await _save_and_refit(db)
    await db.refresh(rating)
    return rating


@router.get("/liking/ratings", response_model=list[LikingRatingResponse])
async def list_liking_ratings(
    limit: int = Query(100, ge=1, le=1000), db: AsyncSession = Depends(get_db)
):
    """List liking ratings, newest first."""
    rows = await db.execute(
        select(LikingRating)
        .order_by(LikingRating.created_at.desc(), LikingRating.id.desc())
        .limit(limit)
    )
    return rows.scalars().all()


@router.delete("/liking/ratings/{rating_id}", status_code=204)
async def delete_liking_rating(rating_id: int, db: AsyncSession = Depends(get_db)):
    """Delete one liking rating and refit."""
    rating = await db.get(LikingRating, rating_id)
    if rating is None:
        raise HTTPException(status_code=404, detail="Liking rating not found")
    await db.delete(rating)
    await _save_and_refit(db)
    return Response(status_code=204)


@router.post("/liking/picks", response_model=LikingPickResponse, status_code=201)
async def record_liking_pick(body: LikingPickCreate, db: AsyncSession = Depends(get_db)):
    """Record which of two bottles Kenny preferred at one time point."""
    pick = LikingPick(**body.model_dump())
    db.add(pick)
    await _save_and_refit(db)
    await db.refresh(pick)
    return pick


@router.get("/liking/picks", response_model=list[LikingPickResponse])
async def list_liking_picks(
    limit: int = Query(100, ge=1, le=1000), db: AsyncSession = Depends(get_db)
):
    """List two-bottle picks, newest first."""
    rows = await db.execute(
        select(LikingPick)
        .order_by(LikingPick.created_at.desc(), LikingPick.id.desc())
        .limit(limit)
    )
    return rows.scalars().all()


@router.delete("/liking/picks/{pick_id}", status_code=204)
async def delete_liking_pick(pick_id: int, db: AsyncSession = Depends(get_db)):
    """Delete one two-bottle pick and refit."""
    pick = await db.get(LikingPick, pick_id)
    if pick is None:
        raise HTTPException(status_code=404, detail="Liking pick not found")
    await db.delete(pick)
    await _save_and_refit(db)
    return Response(status_code=204)


@router.get("/liking/personal")
async def personal_liking_fit(db: AsyncSession = Depends(get_db)):
    """Kenny's personal liking per material and per odour family, fitted from his records."""
    return await personal_liking.current_fit(db)
