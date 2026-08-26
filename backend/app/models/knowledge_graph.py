"""Knowledge Graph database models with provenance tracking.

Phase 1 of the Next-Gen CAFD pipeline: migrate from flat JSON files to
SQLite with schema enforcement, provenance tracking, and confidence scoring.
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ConfidenceLevel(str, enum.Enum):
    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class RuleType(str, enum.Enum):
    SYNERGY = "synergy"
    ANTAGONISM = "antagonism"
    NEUTRAL = "neutral"


# ── Material (replaces material_properties.json entries) ────────────────────


class Material(BaseModel):
    """A fragrance material with full property profile and provenance."""

    __tablename__ = "materials"

    # Identity
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    alt_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    cas: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    formula_str: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Physical / chemical properties
    mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    vp: Mapped[float | None] = mapped_column(Float, nullable=True)
    clp: Mapped[float | None] = mapped_column(Float, nullable=True)
    odt: Mapped[float | None] = mapped_column(Float, nullable=True)
    odor_family: Mapped[str | None] = mapped_column(String(255), nullable=True)
    odor_profile: Mapped[str | None] = mapped_column(Text, nullable=True)

    # SAR / olfactophore
    sar_class: Mapped[str | None] = mapped_column(String(255), nullable=True)
    olfactophore: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Arctander
    arctander_character: Mapped[str | None] = mapped_column(Text, nullable=True)
    arctander_tenacity: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Carles method
    carles_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    carles_pairing_rule: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Roudnitska
    roudnitska_function: Mapped[str | None] = mapped_column(Text, nullable=True)
    roudnitska_craft_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Jellinek
    jellinek_axis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jellinek_quadrant: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jellinek_effect: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Practical usage
    typical_pct_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    max_safe_pct: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stock_form: Mapped[str | None] = mapped_column(String(255), nullable=True)
    best_with: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    avoid: Mapped[str | None] = mapped_column(Text, nullable=True)
    handle_as: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance (every entry tracks where it came from)
    source: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default="knowledge_graph_v1"
    )
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        SAEnum(ConfidenceLevel), nullable=False,
        default=ConfidenceLevel.MEDIUM,
    )
    last_verified: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    edit_history: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True, default=list
    )

    # Data completeness score (auto-calculated)
    completeness_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    pairing_rules_as_a: Mapped[list["PairingRule"]] = relationship(
        "PairingRule", foreign_keys="PairingRule.material_a_id",
        back_populates="material_a_ref", lazy="selectin",
    )
    pairing_rules_as_b: Mapped[list["PairingRule"]] = relationship(
        "PairingRule", foreign_keys="PairingRule.material_b_id",
        back_populates="material_b_ref", lazy="selectin",
    )

    def compute_completeness(self) -> float:
        """Calculate what % of property fields are populated."""
        props = [
            self.mw, self.bp, self.vp, self.clp, self.odt,
            self.odor_family, self.odor_profile,
            self.sar_class, self.olfactophore,
            self.arctander_character, self.arctander_tenacity,
            self.carles_position, self.jellinek_quadrant,
            self.typical_pct_range, self.best_with,
        ]
        filled = sum(1 for p in props if p is not None)
        return round(filled / len(props) * 100, 1)


# ── Pairing Rule (replaces pairing_rules.json) ─────────────────────────────


class PairingRule(BaseModel):
    """A directional pairing rule between two materials."""

    __tablename__ = "pairing_rules"
    __table_args__ = (
        Index("ix_pairing_pair", "material_a_id", "material_b_id"),
    )

    material_a_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("materials.id"), nullable=True
    )
    material_b_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("materials.id"), nullable=True
    )

    # Denormalized names for rules that reference materials not yet in the DB
    material_a_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    material_b_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )

    effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_type: Mapped[RuleType] = mapped_column(
        SAEnum(RuleType), nullable=False, default=RuleType.SYNERGY
    )
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Provenance
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        SAEnum(ConfidenceLevel), nullable=False,
        default=ConfidenceLevel.MEDIUM,
    )
    last_verified: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    material_a_ref: Mapped[Material | None] = relationship(
        "Material", foreign_keys=[material_a_id],
        back_populates="pairing_rules_as_a",
    )
    material_b_ref: Mapped[Material | None] = relationship(
        "Material", foreign_keys=[material_b_id],
        back_populates="pairing_rules_as_b",
    )


# ── Synergy Rule (replaces synergy_matrix.json) ────────────────────────────


class SynergyRule(BaseModel):
    """A synergy/antagonism rule with quantified effects and ratios."""

    __tablename__ = "synergy_rules"

    material_a_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    material_b_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    ratio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_type: Mapped[RuleType] = mapped_column(
        SAEnum(RuleType), nullable=False, default=RuleType.SYNERGY
    )
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Provenance
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        SAEnum(ConfidenceLevel), nullable=False,
        default=ConfidenceLevel.MEDIUM,
    )
    last_verified: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Validation flags
    is_corrupted: Mapped[bool | None] = mapped_column(Boolean, default=False)
    corruption_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Theory Rule ─────────────────────────────────────────────────────────────


class TheoryFramework(BaseModel):
    """A perfumery theory framework (Carles, Roudnitska, Jellinek, etc.)."""

    __tablename__ = "theory_frameworks"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    principle: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[ConfidenceLevel] = mapped_column(
        SAEnum(ConfidenceLevel), nullable=False,
        default=ConfidenceLevel.HIGH,
    )


# ── Formulation Outcome (NEW — feedback loop) ──────────────────────────────


class FormulationOutcome(BaseModel):
    """User-reported outcome of a formulation attempt.

    Closes the loop: system suggests → user creates → user rates → system learns.
    """

    __tablename__ = "formulation_outcomes"

    # Formula identity
    formula_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    formula_version: Mapped[str | None] = mapped_column(String(50), default="1.0")
    ingredients: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    total_volume_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    concentration_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Predicted scores (from optimizer at creation time)
    predicted_scores: Mapped[dict[str, float] | None] = mapped_column(
        JSON, nullable=True
    )

    # Actual user ratings (1-10 scale)
    rating_longevity: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_sillage: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_complexity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Qualitative feedback
    notes_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_notes_observed: Mapped[str | None] = mapped_column(Text, nullable=True)
    heart_notes_observed: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_notes_observed: Mapped[str | None] = mapped_column(Text, nullable=True)
    longevity_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    sillage_description: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    # Batch info
    batch_size_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    maceration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    evaluation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Tags for filtering
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


# ── Pairwise Preference (NEW — pairing feedback) ───────────────────────────


class PairwisePreference(BaseModel):
    """User rating of a specific ingredient pairing they tried."""

    __tablename__ = "pairwise_preferences"

    material_a: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    material_b: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    worked_well: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ratio_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula_name: Mapped[str | None] = mapped_column(String(255), nullable=True)


# ── Score Calibration (NEW — learning correction factors) ───────────────────


class ScoreCalibration(BaseModel):
    """Learned correction factors between predicted and actual scores.

    After enough FormulationOutcome data, regression learns how to
    adjust each scoring axis.
    """

    __tablename__ = "score_calibrations"

    scoring_axis: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    slope: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    intercept: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    r_squared: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_trained: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
