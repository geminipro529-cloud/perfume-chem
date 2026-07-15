"""Chemical and ingredient schemas"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VolatilityClass(str, Enum):
    """Fragrance volatility classifications"""
    TOP = "top"
    TOP_HEART = "top-heart"
    HEART = "heart"
    HEART_BASE = "heart-base"
    BASE = "base"


class OdorFamily(str, Enum):
    """Main odor families"""
    CITRUS = "citrus"
    FLORAL = "floral"
    ORIENTAL = "oriental"
    WOODY = "woody"
    FRESH = "fresh"
    FOUGERE = "fougere"
    CHYPRE = "chypre"
    GOURMAND = "gourmand"


class IngredientBase(BaseModel):
    """Base ingredient schema"""
    name: str = Field(..., min_length=1, max_length=255)
    cas_number: Optional[str] = Field(None, pattern=r"^\d{2,7}-\d{2}-\d$")
    odor_description: Optional[str] = None
    volatility: Optional[VolatilityClass] = None

    class Config:
        use_enum_values = True


class IngredientCreate(IngredientBase):
    """Schema for creating an ingredient"""
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = Field(None, gt=0)
    odor_strength: Optional[int] = Field(None, ge=1, le=10)
    odor_families: Optional[List[OdorFamily]] = None
    ifra_restricted: bool = False
    ifra_max_level: Optional[float] = Field(None, ge=0, le=100)
    allergen: bool = False
    photosensitizer: bool = False
    typical_use_min: float = Field(0.1, ge=0, le=100)
    typical_use_max: float = Field(10.0, ge=0, le=100)
    cost_per_gram: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = None
    notes: Optional[str] = None


class IngredientResponse(IngredientBase):
    """Schema for ingredient response"""
    id: int
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    odor_strength: Optional[int] = None
    odor_families: Optional[List[str]] = None
    ifra_restricted: bool
    ifra_max_level: Optional[float] = None
    allergen: bool
    photosensitizer: bool
    typical_use_min: float
    typical_use_max: float
    cost_per_gram: Optional[float] = None

    class Config:
        from_attributes = True


class FormulaIngredient(BaseModel):
    """Ingredient within a formula"""
    ingredient_id: Optional[int] = None
    name: str
    percentage: float = Field(..., gt=0, le=100)
    role: Optional[str] = None  # "top", "modifier", "fixative", etc.
    cas_number: Optional[str] = None
    cost_per_gram: Optional[float] = None
    ifra_restricted: bool = False
    ifra_max_level: Optional[float] = None
    volatility: Optional[str] = None
    stock_active_fraction: float = Field(1.0, gt=0, le=1)
    stock_density_g_ml: Optional[float] = Field(None, gt=0)


class BottleSnapshotInput(BaseModel):
    """Measured bottle state before an additive correction."""

    total_mass_g: float = Field(..., gt=0)
    active_material_mass_g: float = Field(..., ge=0)
    total_mass_standard_uncertainty_g: float = Field(0.0, ge=0)
    active_mass_standard_uncertainty_g: float = Field(0.0, ge=0)


class StockSolutionInput(BaseModel):
    """Stock composition and optional measured density."""

    active_mass_fraction: float = Field(..., gt=0, le=1)
    density_g_ml: Optional[float] = Field(None, gt=0)
    active_fraction_standard_uncertainty: float = Field(0.0, ge=0)
    density_standard_uncertainty_g_ml: float = Field(0.0, ge=0)


class PipetteProfileInput(BaseModel):
    """Declared pipette range, resolution, and standard uncertainty."""

    minimum_ul: float = Field(..., gt=0)
    increment_ul: float = Field(..., gt=0)
    maximum_single_step_ul: Optional[float] = Field(None, gt=0)
    standard_uncertainty_ul: float = Field(0.0, ge=0)


class BottleAdditionCalculation(BaseModel):
    """Exact active-material target for a one-stock bottle addition."""

    bottle: BottleSnapshotInput
    stock: StockSolutionInput
    target_active_mass_fraction: float = Field(..., ge=0, le=1)
    pipette: Optional[PipetteProfileInput] = None


class DilutionCalculation(BaseModel):
    """Dilution calculation request"""
    concentrate_volume: float = Field(..., gt=0)
    concentrate_percent: float = Field(..., gt=0, le=100)
    target_percent: float = Field(..., gt=0, le=100)
    solvent: str = "ethanol"


class DilutionResult(BaseModel):
    """Dilution calculation result"""
    concentrate_volume: float
    total_volume: float
    solvent_to_add: float
    final_concentration: float
    solvent: str
