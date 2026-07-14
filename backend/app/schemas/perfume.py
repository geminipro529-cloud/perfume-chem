"""Perfume and formula schemas"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.schemas.chemical import FormulaIngredient


class PerfumeBase(BaseModel):
    """Base perfume schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    concentration_type: Optional[str] = None  # edp, edt, etc
    concentration_percent: Optional[float] = Field(None, ge=0, le=100)


class PerfumeCreate(PerfumeBase):
    """Schema for creating a perfume"""
    primary_family: Optional[str] = None
    secondary_family: Optional[str] = None
    accords: Optional[List[str]] = None
    ingredients: List[FormulaIngredient] = []
    solvent: str = "ethanol"
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    @validator('ingredients')
    def validate_ingredients_sum(self, v):
        """Ensure ingredients sum to ~100%"""
        if v:
            total = sum(ing.percentage for ing in v)
            if not (99.0 <= total <= 101.0):
                raise ValueError(f'Ingredients must sum to 100%, got {total}%')
        return v


class PerfumeResponse(PerfumeBase):
    """Schema for perfume response"""
    id: int
    primary_family: Optional[str] = None
    secondary_family: Optional[str] = None
    accords: Optional[List[str]] = None
    ingredients: Optional[List[Dict[str, Any]]] = None
    solvent: str
    longevity_hours: Optional[float] = None
    sillage: Optional[str] = None
    cost_per_100ml: Optional[float] = None
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class FormulaBase(BaseModel):
    """Base formula schema"""
    name: str = Field(..., min_length=1, max_length=255)
    version: str = "1.0"
    total_volume_ml: Optional[float] = Field(None, gt=0)
    concentration_percent: Optional[float] = Field(None, ge=0, le=100)


class FormulaCreate(FormulaBase):
    """Schema for creating a formula"""
    perfume_id: Optional[int] = None
    ingredients: List[FormulaIngredient]
    notes: Optional[str] = None

    @validator('ingredients')
    def validate_formula_balance(self, v):
        """Ensure formula is balanced"""
        total = sum(ing.percentage for ing in v)
        if not (99.0 <= total <= 101.0):
            raise ValueError(f'Formula must sum to 100%, got {total}%')
        return v


class FormulaResponse(FormulaBase):
    """Schema for formula response"""
    id: int
    perfume_id: Optional[int] = None
    ingredients: List[Dict[str, Any]]
    top_notes_percent: Optional[float] = None
    heart_notes_percent: Optional[float] = None
    base_notes_percent: Optional[float] = None
    ifra_compliant: Optional[bool] = None
    ifra_violations: Optional[List[str]] = None
    total_cost: Optional[float] = None
    cost_per_ml: Optional[float] = None
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class AIAnalysisRequest(BaseModel):
    """Request for AI perfume analysis"""
    name: str
    ingredients: List[FormulaIngredient]
    concentration: float = 15.0


class AIModificationRequest(BaseModel):
    """Request for AI formula modification suggestions"""
    formula: Dict[str, Any]
    goal: str


class AIPairingRequest(BaseModel):
    """Request for AI ingredient pairing suggestions"""
    ingredient: str
    cas_number: Optional[str] = None
