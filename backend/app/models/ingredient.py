"""Ingredient database model"""

from sqlalchemy import JSON, Boolean, Column, Float, Integer, String, Text

from app.models.base import BaseModel


class Ingredient(BaseModel):
    """Ingredient/Chemical compound model"""

    __tablename__ = "ingredients"

    # Basic info
    name = Column(String(255), nullable=False, index=True, unique=True)
    cas_number = Column(String(50), nullable=True, index=True)
    common_names = Column(JSON, nullable=True)  # List of alternative names

    # Chemical properties
    molecular_formula = Column(String(100), nullable=True)
    molecular_weight = Column(Float, nullable=True)
    density = Column(Float, nullable=True)  # g/ml

    # Olfactory properties
    odor_description = Column(Text, nullable=True)
    odor_strength = Column(Integer, nullable=True)  # 1-10 scale
    volatility = Column(String(50), nullable=True)  # top, heart, base
    odor_families = Column(JSON, nullable=True)  # List of families

    # Safety & Compliance
    ifra_restricted = Column(Boolean, default=False)
    ifra_max_level = Column(Float, nullable=True)  # Max % in finished product
    allergen = Column(Boolean, default=False)
    photosensitizer = Column(Boolean, default=False)

    # Usage recommendations
    typical_use_min = Column(Float, default=0.1)  # Minimum % in formula
    typical_use_max = Column(Float, default=10.0)  # Maximum % in formula

    # Cost
    cost_per_gram = Column(Float, nullable=True)
    supplier = Column(String(255), nullable=True)

    # Additional metadata
    notes = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)
