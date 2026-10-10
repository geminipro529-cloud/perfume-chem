"""AI-powered endpoints"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_ai_service, get_db, get_model_selector_dep
from app.core.exceptions import AIServiceError
from app.schemas.perfume import AIAnalysisRequest, AIModificationRequest, AIPairingRequest
from app.services.ai.answer_check import check_answer
from app.services.ai.base import BaseAIService
from app.services.engine_job_compatibility import (
    enqueue_formula_analysis_compatibility,
)
from app.services.validation_pipeline import (
    attach_validation,
    validate_formula,
    validate_search_query,
)

router = APIRouter()


@router.get("/models")
async def get_available_models(
    model_selector: Dict[str, Any] = Depends(get_model_selector_dep)
) -> Dict[str, Any]:
    """Get available AI models for selection"""
    return model_selector


@router.post("/analyze-perfume")
async def analyze_perfume(
    request: AIAnalysisRequest,
    model: Optional[str] = None,
    force_provider: Optional[str] = None,
    ai_service: BaseAIService = Depends(get_ai_service),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Analyze a perfume composition using AI"""
    ingredients_dict = {ing.name: ing.percentage for ing in request.ingredients}
    report = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(ingredients_dict),
        ingredients_dict,
        scope="ai.analyze-perfume",
        formula_name=request.name,
    )
    try:
        result = await ai_service.analyze_perfume(
            name=request.name,
            ingredients=[ing.dict() for ing in request.ingredients],
            concentration=request.concentration
        )
        result["inventory_check"] = check_answer(result)
        return attach_validation(result, report)
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-modifications")
async def suggest_modifications(
    request: AIModificationRequest,
    model: Optional[str] = None,
    force_provider: Optional[str] = None,
    ai_service: BaseAIService = Depends(get_ai_service),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get AI suggestions for formula modifications"""
    # Validate formula if it contains numeric ingredient percentages
    formula_nums = {k: v for k, v in request.formula.items() if isinstance(v, (int, float))}
    report = (
        await enqueue_formula_analysis_compatibility(
            session,
            validate_formula(formula_nums),
            formula_nums,
            scope="ai.suggest-modifications",
        )
        if formula_nums
        else None
    )
    validate_search_query(request.goal)
    try:
        result = await ai_service.suggest_modifications(
            formula=request.formula,
            goal=request.goal
        )
        result["inventory_check"] = check_answer(result)
        return attach_validation(result, report) if report else result
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-pairings")
async def suggest_pairings(
    request: AIPairingRequest,
    model: Optional[str] = None,
    force_provider: Optional[str] = None,
    ai_service: BaseAIService = Depends(get_ai_service)
) -> Dict[str, Any]:
    """Get AI suggestions for ingredient pairings"""
    validate_search_query(request.ingredient)
    try:
        result = await ai_service.suggest_pairings(
            ingredient=request.ingredient,
            cas_number=request.cas_number
        )
        result["inventory_check"] = check_answer(result)
        return result
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
