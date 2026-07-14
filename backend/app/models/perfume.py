"""Perfume/Formula database model"""

from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Integer, String, Text

from app.models.base import BaseModel


class Perfume(BaseModel):
    """Perfume/Fragrance composition model"""

    __tablename__ = "perfumes"

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    concentration_type = Column(String(50), nullable=True)  # edp, edt, etc
    concentration_percent = Column(Float, nullable=True)  # Total fragrance %

    # Classification
    primary_family = Column(String(100), nullable=True)
    secondary_family = Column(String(100), nullable=True)
    accords = Column(JSON, nullable=True)  # List of accords

    # Formulation data
    ingredients = Column(JSON, nullable=True)  # List of {ingredient_id, percentage, role}
    solvent = Column(String(100), default="ethanol")

    # Predictions/Analysis
    longevity_hours = Column(Float, nullable=True)
    sillage = Column(String(50), nullable=True)  # intimate, moderate, strong

    # Cost analysis
    cost_per_100ml = Column(Float, nullable=True)

    # Metadata
    created_by = Column(String(255), nullable=True)
    tags = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)


class Formula(BaseModel):
    """Detailed formula with ingredient breakdown"""

    __tablename__ = "formulas"

    perfume_id = Column(Integer, ForeignKey("perfumes.id"), nullable=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), default="1.0")

    # Formula details
    total_volume_ml = Column(Float, nullable=True)
    concentration_percent = Column(Float, nullable=True)

    # Ingredients breakdown (JSON structure)
    # [{"ingredient_id": 1, "name": "Linalool", "percentage": 5.0, "grams": 0.5, "role": "heart"}]
    ingredients = Column(JSON, nullable=False)

    # Calculated properties
    top_notes_percent = Column(Float, nullable=True)
    heart_notes_percent = Column(Float, nullable=True)
    base_notes_percent = Column(Float, nullable=True)

    # IFRA compliance
    ifra_compliant = Column(Boolean, nullable=True)
    ifra_violations = Column(JSON, nullable=True)

    # Cost
    total_cost = Column(Float, nullable=True)
    cost_per_ml = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=True)
