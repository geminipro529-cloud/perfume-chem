"""Knowledge Graph database models with provenance tracking.

Phase 1 of the Next-Gen CAFD pipeline: migrate from flat JSON files to
SQLite with schema enforcement, provenance tracking, and confidence scoring.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, JSON,
    DateTime, ForeignKey, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


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
    name = Column(String(255), nullable=False, unique=True, index=True)
    alt_name = Column(String(255), nullable=True, index=True)
    cas = Column(String(50), nullable=True, index=True)
    formula_str = Column(String(100), nullable=True)

    # Physical / chemical properties
    mw = Column(Float, nullable=True)            # molecular weight
    bp = Column(Float, nullable=True)            # boiling point °C
    vp = Column(Float, nullable=True)            # vapor pressure mmHg @25°C
    clp = Column(Float, nullable=True)           # calculated log P
    odt = Column(Float, nullable=True)           # odor detection threshold mg/L
    odor_family = Column(String(255), nullable=True)
    odor_profile = Column(Text, nullable=True)

    # SAR / olfactophore
    sar_class = Column(String(255), nullable=True)
    olfactophore = Column(Text, nullable=True)

    # Arctander
    arctander_character = Column(Text, nullable=True)
    arctander_tenacity = Column(Text, nullable=True)

    # Carles method
    carles_position = Column(String(255), nullable=True)
    carles_pairing_rule = Column(Text, nullable=True)

    # Roudnitska
    roudnitska_function = Column(Text, nullable=True)
    roudnitska_craft_note = Column(Text, nullable=True)

    # Jellinek
    jellinek_axis = Column(String(255), nullable=True)
    jellinek_quadrant = Column(String(255), nullable=True)
    jellinek_effect = Column(Text, nullable=True)

    # Practical usage
    typical_pct_range = Column(String(100), nullable=True)
    max_safe_pct = Column(String(100), nullable=True)
    stock_form = Column(String(255), nullable=True)
    best_with = Column(JSON, nullable=True)      # list of material names
    avoid = Column(Text, nullable=True)
    handle_as = Column(Text, nullable=True)

    # Provenance (every entry tracks where it came from)
    source = Column(String(255), nullable=True, default="knowledge_graph_v1")
    confidence = Column(
        SAEnum(ConfidenceLevel), nullable=False,
        default=ConfidenceLevel.MEDIUM,
    )
    last_verified = Column(DateTime, nullable=True)
    edit_history = Column(JSON, nullable=True, default=list)

    # Data completeness score (auto-calculated)
    completeness_pct = Column(Float, nullable=True)

    # Relationships
    pairing_rules_as_a = relationship(
        "PairingRule", foreign_keys="PairingRule.material_a_id",
        back_populates="material_a_ref", lazy="selectin",
    )
    pairing_rules_as_b = relationship(
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

    material_a_id = Column(Integer, ForeignKey("materials.id"), nullable=True)
    material_b_id = Column(Integer, ForeignKey("materials.id"), nullable=True)

    # Denormalized names for rules that reference materials not yet in the DB
    material_a_name = Column(String(255), nullable=False, index=True)
    material_b_name = Column(String(255), nullable=False, index=True)

    effect = Column(Text, nullable=True)
    rule_type = Column(SAEnum(RuleType), nullable=False, default=RuleType.SYNERGY)
    source = Column(String(255), nullable=True)

    # Provenance
    confidence = Column(
        SAEnum(ConfidenceLevel), nullable=False,
        default=ConfidenceLevel.MEDIUM,
    )
    last_verified = Column(DateTime, nullable=True)

    # Relationships
    material_a_ref = relationship(
        "Material", foreign_keys=[material_a_id],
        back_populates="pairing_rules_as_a",
    )
    material_b_ref = relationship(
        "Material", foreign_keys=[material_b_id],
        back_populates="pairing_rules_as_b",
    )


# ── Synergy Rule (replaces synergy_matrix.json) ────────────────────────────


class SynergyRule(BaseModel):
    """A synergy/antagonism rule with quantified effects and ratios."""

    __tablename__ = "synergy_rules"

    material_a_name = Column(String(255), nullable=False, index=True)
    material_b_name = Column(String(255), nullable=False, index=True)
    effect = Column(Text, nullable=True)
    ratio = Column(String(100), nullable=True)
    rule_type = Column(SAEnum(RuleType), nullable=False, default=RuleType.SYNERGY)
    source = Column(String(255), nullable=True)

    # Provenance
    confidence = Column(
        SAEnum(ConfidenceLevel), nullable=False,
        default=ConfidenceLevel.MEDIUM,
    )
    last_verified = Column(DateTime, nullable=True)

    # Validation flags
    is_corrupted = Column(Boolean, default=False)
    corruption_notes = Column(Text, nullable=True)


# ── Theory Rule ─────────────────────────────────────────────────────────────


class TheoryFramework(BaseModel):
    """A perfumery theory framework (Carles, Roudnitska, Jellinek, etc.)."""

    __tablename__ = "theory_frameworks"

    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    principle = Column(Text, nullable=True)
    rules_json = Column(JSON, nullable=True)  # the full theory data
    source = Column(String(255), nullable=True)
    confidence = Column(
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
    formula_name = Column(String(255), nullable=False, index=True)
    formula_version = Column(String(50), default="1.0")
    ingredients = Column(JSON, nullable=False)  # {name: pct, ...}
    total_volume_ml = Column(Float, nullable=True)
    concentration_pct = Column(Float, nullable=True)

    # Predicted scores (from optimizer at creation time)
    predicted_scores = Column(JSON, nullable=True)  # {longevity: 72, sillage: 65, ...}

    # Actual user ratings (1-10 scale)
    rating_longevity = Column(Float, nullable=True)
    rating_sillage = Column(Float, nullable=True)
    rating_balance = Column(Float, nullable=True)
    rating_overall = Column(Float, nullable=True)
    rating_complexity = Column(Float, nullable=True)

    # Qualitative feedback
    notes_text = Column(Text, nullable=True)
    top_notes_observed = Column(Text, nullable=True)
    heart_notes_observed = Column(Text, nullable=True)
    base_notes_observed = Column(Text, nullable=True)
    longevity_hours = Column(Float, nullable=True)
    sillage_description = Column(String(50), nullable=True)

    # Batch info
    batch_size_ml = Column(Float, nullable=True)
    maceration_days = Column(Integer, nullable=True)
    creation_date = Column(DateTime, nullable=True)
    evaluation_date = Column(DateTime, nullable=True)

    # Tags for filtering
    tags = Column(JSON, nullable=True)


# ── Pairwise Preference (NEW — pairing feedback) ───────────────────────────


class PairwisePreference(BaseModel):
    """User rating of a specific ingredient pairing they tried."""

    __tablename__ = "pairwise_preferences"

    material_a = Column(String(255), nullable=False, index=True)
    material_b = Column(String(255), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    worked_well = Column(Boolean, nullable=True)
    ratio_used = Column(String(50), nullable=True)
    context = Column(Text, nullable=True)  # "in a woody accord", etc
    formula_name = Column(String(255), nullable=True)  # which formula this was in


# ── Score Calibration (NEW — learning correction factors) ───────────────────


class ScoreCalibration(BaseModel):
    """Learned correction factors between predicted and actual scores.

    After enough FormulationOutcome data, regression learns how to
    adjust each scoring axis.
    """

    __tablename__ = "score_calibrations"

    scoring_axis = Column(String(50), nullable=False, unique=True, index=True)
    slope = Column(Float, nullable=False, default=1.0)
    intercept = Column(Float, nullable=False, default=0.0)
    r_squared = Column(Float, nullable=True)
    n_samples = Column(Integer, nullable=False, default=0)
    last_trained = Column(DateTime, nullable=True)
