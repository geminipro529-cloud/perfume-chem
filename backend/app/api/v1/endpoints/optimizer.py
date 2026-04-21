"""Optimizer API endpoints: score, suggest, optimize, and Carles grid search."""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Add project root to path so engine module is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from engine.optimizer.models import FormulaVector, ObjectiveWeights, OptimizationConstraints
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer
from app.services.validation_pipeline import validate_formula, attach_validation

router = APIRouter()


# ── Request/Response schemas ──

class FormulaInput(BaseModel):
    ingredients: dict[str, float] = Field(
        ..., description="Mapping of ingredient name → percentage",
        examples=[{"ISO E SUPER": 15, "HEDIONE": 10, "BERGAMOT": 5}]
    )

class WeightsInput(BaseModel):
    longevity: float = 1.0
    sillage: float = 1.0
    balance: float = 1.0
    synergy: float = 1.0
    theory: float = 0.5
    cost: float = 0.3

class ScoreResponse(BaseModel):
    scores: dict[str, float]
    note_distribution: dict[str, float]
    confidence: dict | None = None

class SuggestResponse(BaseModel):
    suggestions: list[str]
    scores: dict[str, float]
    note_distribution: dict[str, float]

class OptimizeRequest(BaseModel):
    formula: FormulaInput
    weights: WeightsInput = WeightsInput()
    max_ingredients: int = 15

class OptimizeResponse(BaseModel):
    original_scores: dict[str, float]
    optimized_formula: dict[str, float]
    optimized_scores: dict[str, float]
    improvement: float
    reasoning: list[str]
    suggestions: list[str]

class GridSearchRequest(BaseModel):
    star_material: str = Field(..., description="The characterizing material to build around")
    weights: WeightsInput = WeightsInput()
    n_results: int = Field(5, ge=1, le=20)

class GridSearchResult(BaseModel):
    formula: dict[str, float]
    scores: dict[str, float]
    total_score: float
    reasoning: list[str]

class GridSearchResponse(BaseModel):
    results: list[GridSearchResult]


# ── Endpoints ──

@router.post("/score")
async def score_formula(body: FormulaInput, weights: WeightsInput = WeightsInput()):
    """Score a formula on 6 axes: longevity, sillage, balance, synergy, theory, cost."""
    report = validate_formula(body.ingredients)
    fv = FormulaVector(ingredients=body.ingredients)
    w = ObjectiveWeights(**weights.model_dump())
    scorer = FormulaScorer(w)
    scores = scorer.score(fv)
    confidence = ConfidenceScorer().score(body.ingredients)
    return attach_validation({
        "scores": scores,
        "note_distribution": fv.note_distribution(),
        "confidence": confidence,
    }, report)


@router.post("/suggest")
async def suggest_improvements(body: FormulaInput, weights: WeightsInput = WeightsInput()):
    """Get improvement suggestions for a formula based on knowledge graph analysis."""
    report = validate_formula(body.ingredients)
    fv = FormulaVector(ingredients=body.ingredients)
    w = ObjectiveWeights(**weights.model_dump())
    opt = FormulaOptimizer(weights=w)
    suggestions = opt.suggest(fv)
    scores = opt.score(fv)
    return attach_validation({
        "suggestions": suggestions,
        "scores": scores,
        "note_distribution": fv.note_distribution(),
    }, report)


@router.post("/optimize")
async def optimize_formula(body: OptimizeRequest):
    """Optimize an existing formula by iteratively testing improvements."""
    report = validate_formula(body.formula.ingredients)
    fv = FormulaVector(ingredients=body.formula.ingredients)
    w = ObjectiveWeights(**body.weights.model_dump())
    constraints = OptimizationConstraints(max_ingredients=body.max_ingredients)
    opt = FormulaOptimizer(weights=w, constraints=constraints)

    original_scores = opt.score(fv)
    result = opt.optimize(fv)

    return attach_validation({
        "original_scores": original_scores,
        "optimized_formula": result.formula.ingredients,
        "optimized_scores": result.scores,
        "improvement": round(result.total_score - original_scores["total"], 1),
        "reasoning": result.reasoning,
        "suggestions": result.suggestions,
    }, report)


@router.post("/grid-search")
async def carles_grid_search(body: GridSearchRequest):
    """Carles method: try a star material against different base accords."""
    # Grid search generates formulas internally — validate star material name
    if not body.star_material or not body.star_material.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="star_material must be a non-empty string.")
    w = ObjectiveWeights(**body.weights.model_dump())
    opt = FormulaOptimizer(weights=w)
    results = opt.carles_grid_search(body.star_material, n_results=body.n_results)

    return {
        "results": [
            {
                "formula": r.formula.ingredients,
                "scores": r.scores,
                "total_score": r.total_score,
                "reasoning": r.reasoning,
            }
            for r in results
        ]
    }
