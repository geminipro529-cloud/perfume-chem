"""Enhancement API endpoints: confidence, volatility, odor ontology, gap detection, calibration.

These endpoints expose the 5 Perplexity-recommended enhancement modules
that were added to the engine layer.
"""

import sys
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path so engine module is importable
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from engine.calibration import ScoreCalibrationPipeline
from engine.confidence import ConfidenceScorer
from engine.gap_detector import GapDetector
from engine.odor_ontology import OdorOntology
from engine.volatility import VolatilityCurveSimulator

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


# ── Request / Response schemas ──

class FormulaInput(BaseModel):
    ingredients: dict[str, float] = Field(
        ..., description="Mapping of ingredient name → percentage",
        examples=[{"ISO E SUPER": 15, "HEDIONE": 10, "BERGAMOT": 5}],
    )

class ConfidenceResponse(BaseModel):
    data_confidence: float
    pairing_confidence: float
    prediction_confidence: float
    overall_confidence: float
    confidence_grade: str
    per_material: dict[str, float]

class VolatilityResponse(BaseModel):
    time_points: list[float]
    curves: dict[str, list[float]]
    dominant_notes: list[str]
    note_evolution: list[dict[str, float]]
    summary: dict

class ClassifyResponse(BaseModel):
    classifications: dict[str, dict]

class SimilarRequest(BaseModel):
    material: str
    max_results: int = Field(10, ge=1, le=50)

class SimilarResponse(BaseModel):
    query_material: str
    similar: list[dict]

class GapResponse(BaseModel):
    gaps: list[dict]
    data_quality_score: float
    stats: dict

class CalibrationTrainResponse(BaseModel):
    total_outcomes_used: int
    axes_calibrated: int
    summary: list[str]
    results: list[dict]

class CalibrateRequest(BaseModel):
    raw_scores: dict[str, float] = Field(
        ..., description="Raw scores from the scoring engine",
        examples=[{"longevity": 72, "sillage": 65, "balance": 80}],
    )

class CalibrateResponse(BaseModel):
    raw_scores: dict[str, float]
    calibrated_scores: dict[str, float]


# ── Confidence ──

@router.post("/confidence")
async def formula_confidence(
    body: FormulaInput,
    session: AsyncSession = Depends(get_db),
):
    """Compute confidence bands for a formula's predicted scores."""
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(body.ingredients),
        body.ingredients,
        scope="enhancements.confidence",
    )
    scorer = ConfidenceScorer()
    result = scorer.score(body.ingredients)
    return attach_validation(result, report)


# ── Volatility ──

@router.post("/volatility")
async def volatility_simulation(
    body: FormulaInput,
    session: AsyncSession = Depends(get_db),
):
    """Simulate fragrance evolution over time (headspace concentration curves)."""
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(body.ingredients),
        body.ingredients,
        scope="enhancements.volatility",
    )
    sim = VolatilityCurveSimulator()
    profile = sim.simulate(body.ingredients)
    return attach_validation({
        "time_points": profile.time_points,
        "curves": profile.curves,
        "dominant_notes": profile.dominant_notes,
        "note_evolution": profile.note_evolution,
        "summary": sim.summary(profile),
    }, report)


# ── Odor Ontology ──

@router.post("/classify")
async def classify_materials(
    body: FormulaInput,
    session: AsyncSession = Depends(get_db),
):
    """Classify formula ingredients into the odor ontology."""
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(body.ingredients),
        body.ingredients,
        scope="enhancements.classify",
    )
    ontology = OdorOntology()
    classifications = {}
    for name in body.ingredients:
        result = ontology.classify_material(name)
        classifications[name] = result
    return attach_validation({"classifications": classifications}, report)


@router.post("/similar")
async def find_similar_materials(body: SimilarRequest):
    """Find materials with similar odor profiles."""
    report = validate_search_query(body.material)
    ontology = OdorOntology()
    similar = ontology.find_similar(body.material, max_results=body.max_results)
    return attach_validation(
        {"query_material": body.material, "similar": similar}, report
    )


@router.get("/taxonomy")
async def odor_taxonomy():
    """Return the full odor family taxonomy tree."""
    ontology = OdorOntology()
    return ontology.get_taxonomy()


# ── Gap Detection ──

@router.get("/gaps", response_model=GapResponse)
async def detect_gaps():
    """Analyze knowledge graph for data gaps and prioritize them."""
    detector = GapDetector()
    report = detector.analyze()
    return GapResponse(
        gaps=[
            {
                "category": g.category,
                "severity": g.severity,
                "description": g.description,
                "impact_score": g.impact_score,
                "resolution_hint": g.resolution_hint,
            }
            for g in report.gaps
        ],
        data_quality_score=report.data_quality_score,
        stats=report.stats,
    )


# ── Score Calibration ──

@router.post("/calibrate/train", response_model=CalibrationTrainResponse)
async def train_calibration():
    """Train score calibration from FormulationOutcome data."""
    pipeline = ScoreCalibrationPipeline()
    report = pipeline.train()

    # Persist to database if outcomes were used
    if report.axes_calibrated > 0:
        import sqlite3
        from datetime import datetime, timezone

        from engine.optimizer.models import DB_PATH

        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            for r in report.results:
                conn.execute(
                    "INSERT OR REPLACE INTO score_calibrations "
                    "(scoring_axis, slope, intercept, r_squared, n_samples, last_trained) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (r.axis, r.slope, r.intercept, r.r_squared, r.n_samples,
                     datetime.now(timezone.utc).isoformat()),
                )
            conn.commit()
            conn.close()

    return CalibrationTrainResponse(
        total_outcomes_used=report.total_outcomes_used,
        axes_calibrated=report.axes_calibrated,
        summary=report.summary(),
        results=[
            {
                "axis": r.axis,
                "slope": r.slope,
                "intercept": r.intercept,
                "r_squared": r.r_squared,
                "n_samples": r.n_samples,
                "mean_error": r.mean_error,
            }
            for r in report.results
        ],
    )


@router.post("/calibrate/apply", response_model=CalibrateResponse)
async def apply_calibration(body: CalibrateRequest):
    """Apply learned calibration corrections to raw scores."""
    pipeline = ScoreCalibrationPipeline()
    calibrated = pipeline.calibrate(body.raw_scores)
    return CalibrateResponse(
        raw_scores=body.raw_scores,
        calibrated_scores=calibrated,
    )
