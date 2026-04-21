"""Outcome API endpoints: record, query, and analyze formulation outcomes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
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
