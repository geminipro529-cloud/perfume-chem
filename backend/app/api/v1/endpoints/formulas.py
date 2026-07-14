"""Formula calculation endpoints"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.core.exceptions import DilutionCalculationError
from app.domain.ingredients.chemistry import (
    calculate_dilution,
    calculate_drops_to_ml,
    calculate_ml_to_drops,
    calculate_note_distribution,
    estimate_longevity,
    estimate_sillage,
    validate_formula_balance,
)
from app.schemas.chemical import DilutionCalculation, DilutionResult
from app.schemas.perfume import FormulaCreate
from app.services.validation_pipeline import attach_validation, validate_formula

router = APIRouter()


@router.post("/calculate-dilution", response_model=DilutionResult)
async def calculate_dilution_endpoint(
    dilution: DilutionCalculation
) -> DilutionResult:
    """Calculate dilution for a concentrate"""
    try:
        result = calculate_dilution(
            concentrate_volume=dilution.concentrate_volume,
            concentrate_percent=dilution.concentrate_percent,
            target_percent=dilution.target_percent
        )
        return DilutionResult(**result, solvent=dilution.solvent)
    except DilutionCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/drops-to-ml/{drops}")
async def drops_to_ml(drops: int, drop_size: float = 0.05) -> Dict[str, float]:
    """Convert drops to milliliters"""
    ml = calculate_drops_to_ml(drops, drop_size)
    return {"drops": drops, "milliliters": ml, "drop_size": drop_size}


@router.get("/ml-to-drops/{volume}")
async def ml_to_drops(volume: float, drop_size: float = 0.05) -> Dict[str, int]:
    """Convert milliliters to drops"""
    drops = calculate_ml_to_drops(volume, drop_size)
    return {"milliliters": volume, "drops": drops, "drop_size": drop_size}


@router.post("/analyze-formula")
async def analyze_formula(formula: FormulaCreate) -> Dict[str, Any]:
    """Analyze a formula for note distribution and properties"""
    ingredients_dict = {ing.name: ing.percentage for ing in formula.ingredients}
    report = validate_formula(ingredients_dict)
    try:
        # Validate balance
        validate_formula_balance([ing.dict() for ing in formula.ingredients])

        # Calculate note distribution
        note_dist = calculate_note_distribution([ing.dict() for ing in formula.ingredients])

        # Estimate properties
        longevity = estimate_longevity(note_dist)
        sillage = estimate_sillage(
            note_dist.get('top', 0),
            formula.concentration_percent or 15.0
        )

        return attach_validation({
            "formula_name": formula.name,
            "note_distribution": note_dist,
            "estimated_longevity_hours": longevity,
            "estimated_sillage": sillage,
            "total_volume_ml": formula.total_volume_ml,
            "concentration_percent": formula.concentration_percent
        }, report)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
