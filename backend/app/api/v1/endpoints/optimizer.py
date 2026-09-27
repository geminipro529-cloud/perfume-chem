"""Optimizer API endpoints: score, suggest, optimize, and Carles grid search."""

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path so engine module is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from engine.confidence import ConfidenceScorer
from engine.optimizer.models import FormulaVector, ObjectiveWeights, OptimizationConstraints
from engine.optimizer.optimizer import FormulaOptimizer
from engine.optimizer.scoring import FormulaScorer

from app.api.deps import get_db
from app.services.engine_job_compatibility import (
    enqueue_formula_analysis_compatibility,
)
from app.services.validation_pipeline import (
    attach_validation,
    validate_formula,
    validate_search_query,
)

router = APIRouter()

_DIAGNOSTIC_SCORE_AUTHORITY = {
    "classification": "HEURISTIC_DIAGNOSTIC_INDICES",
    "release_authority": False,
    "formula_optimization_authority": False,
    "pleasantness_or_liking_authority": False,
    "ranking_status": "WITHHELD",
}


# ── Request/Response schemas ──

class FormulaInput(BaseModel):
    ingredients: dict[str, float] = Field(
        ..., description="Mapping of ingredient name → percentage",
        examples=[{"ISO E SUPER": 15, "HEDIONE": 10, "BERGAMOT": 5}]
    )

class WeightsInput(BaseModel):
    """Version-matched legacy diagnostic weights; unknown axes fail closed."""

    model_config = ConfigDict(extra="forbid")

    longevity: float = 0.8
    sillage: float = 0.8
    synergy: float = 0.5
    luxury: float = 0.8
    texture: float = 0.8
    stacking_depth: float = 0.8
    skin_performance: float = 0.7
    hedonic: float = 0.5
    perceptual_clarity: float = 0.6
    photorealism: float = 0.7

class ScoreResponse(BaseModel):
    scores: dict[str, Any]
    note_distribution: dict[str, float]
    confidence: dict | None = None
    score_authority: dict[str, Any]

class SuggestResponse(BaseModel):
    suggestions: list[str]
    scores: dict[str, Any]
    note_distribution: dict[str, float]
    suggestion_authority: dict[str, Any]

class OptimizeRequest(BaseModel):
    formula: FormulaInput
    weights: WeightsInput = WeightsInput()
    max_ingredients: int = 15

class OptimizeResponse(BaseModel):
    original_scores: dict[str, Any]
    optimized_formula: dict[str, float]
    optimized_scores: dict[str, Any]
    improvement: float
    reasoning: list[str]
    suggestions: list[str]
    ranking_status: str
    formula_optimization_authority: bool
    selection_basis: str

class GridSearchRequest(BaseModel):
    star_material: str = Field(..., description="The characterizing material to build around")
    weights: WeightsInput = WeightsInput()
    n_results: int = Field(5, ge=1, le=20)

class GridSearchResult(BaseModel):
    formula: dict[str, float]
    scores: dict[str, Any]
    total_score: float
    reasoning: list[str]
    ranking_status: str
    formula_optimization_authority: bool
    selection_basis: str

class GridSearchResponse(BaseModel):
    results: list[GridSearchResult]
    ranking_status: str
    formula_optimization_authority: bool


# ── Endpoints ──

@router.post("/score")
async def score_formula(
    body: FormulaInput,
    weights: WeightsInput = WeightsInput(),
    session: AsyncSession = Depends(get_db),
):
    """Return explicitly non-authoritative legacy diagnostic score axes."""
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(body.ingredients),
        body.ingredients,
        scope="optimizer.score",
    )
    fv = FormulaVector(ingredients=body.ingredients)
    w = ObjectiveWeights(**weights.model_dump())
    scorer = FormulaScorer(w)
    scores = scorer.score(fv)
    confidence = ConfidenceScorer().score(body.ingredients)
    return attach_validation(
        {
            "scores": scores,
            "note_distribution": fv.note_distribution(),
            "confidence": confidence,
            "score_authority": dict(_DIAGNOSTIC_SCORE_AUTHORITY),
        },
        report,
    )


@router.post("/suggest")
async def suggest_improvements(
    body: FormulaInput,
    weights: WeightsInput = WeightsInput(),
    session: AsyncSession = Depends(get_db),
):
    """Fail closed to NO_CHANGE without an admitted optimization endpoint."""
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(body.ingredients),
        body.ingredients,
        scope="optimizer.suggest",
    )
    fv = FormulaVector(ingredients=body.ingredients)
    w = ObjectiveWeights(**weights.model_dump())
    opt = FormulaOptimizer(weights=w)
    suggestions = opt.suggest(fv)
    scores = opt.score(fv)
    return attach_validation(
        {
            "suggestions": suggestions,
            "scores": scores,
            "note_distribution": fv.note_distribution(),
            "suggestion_authority": dict(_DIAGNOSTIC_SCORE_AUTHORITY),
        },
        report,
    )


@router.post("/optimize")
async def optimize_formula(
    body: OptimizeRequest,
    session: AsyncSession = Depends(get_db),
):
    """Preserve the input formula while ranking authority is withheld."""
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(body.formula.ingredients),
        body.formula.ingredients,
        scope="optimizer.optimize",
    )
    fv = FormulaVector(ingredients=body.formula.ingredients)
    w = ObjectiveWeights(**body.weights.model_dump())
    constraints = OptimizationConstraints(max_ingredients=body.max_ingredients)
    opt = FormulaOptimizer(weights=w, constraints=constraints)

    result = opt.optimize(fv)
    original_scores = result.scores

    return attach_validation(
        {
            "original_scores": original_scores,
            "optimized_formula": result.formula.ingredients,
            "optimized_scores": result.scores,
            "improvement": 0.0,
            "reasoning": result.reasoning,
            "suggestions": result.suggestions,
            "ranking_status": result.ranking_status,
            "formula_optimization_authority": result.formula_optimization_authority,
            "selection_basis": result.selection_basis,
        },
        report,
    )


@router.post("/grid-search")
async def carles_grid_search(
    body: GridSearchRequest,
    session: AsyncSession = Depends(get_db),
):
    """Generate deterministic unranked Carles design candidates."""
    # Grid search generates formulas internally — validate star material name
    if not body.star_material or not body.star_material.strip():
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="star_material must be a non-empty string.",
        )
    w = ObjectiveWeights(**body.weights.model_dump())
    opt = FormulaOptimizer(weights=w)
    results = opt.carles_grid_search(body.star_material, n_results=body.n_results)

    validated_results = []
    for result in results:
        candidate = {
            "formula": result.formula.ingredients,
            "scores": result.scores,
            "total_score": result.total_score,
            "reasoning": result.reasoning,
            "ranking_status": result.ranking_status,
            "formula_optimization_authority": result.formula_optimization_authority,
            "selection_basis": result.selection_basis,
        }
        candidate_report = await enqueue_formula_analysis_compatibility(
            session,
            validate_formula(result.formula.ingredients),
            result.formula.ingredients,
            scope="optimizer.grid-search.candidate",
            formula_name=f"Carles candidate for {body.star_material}",
        )
        validated_results.append(attach_validation(candidate, candidate_report))
    return attach_validation(
        {
            "results": validated_results,
            "ranking_status": "WITHHELD",
            "formula_optimization_authority": False,
        },
        validate_search_query(body.star_material),
    )
