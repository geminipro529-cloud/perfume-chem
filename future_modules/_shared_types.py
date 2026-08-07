"""Shared enums, constants, and lightweight dataclasses used across future_modules.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

This module defines the vocabulary that the other formulation intelligence modules
use: concentration brackets, fragrance families, texture layers, note tiers,
diffusion layers, hedonic categories, market segments, and OAV perceptual ranges.

All values are derived from the Formulation Intelligence Database (May 2026).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConcentrationBracket(StrEnum):
    """Fine fragrance concentration brackets (% w/w in ethanol)."""
    EDC = "EdC"          # 3–5%
    EDT = "EdT"          # 8–12%
    EDP = "EdP"          # 15–20%
    EXTRAIT = "Extrait"  # 20%+
    BODY_SPRAY = "Body Spray"  # ~3%


class FragranceFamily(StrEnum):
    """Eleven fragrance families as codified in formulation science."""
    CITRUS = "citrus"
    AROMATIC_FOUGERE = "aromatic_fougere"
    FLORAL_ROSE = "floral_rose"
    FLORAL_JASMINE = "floral_jasmine"
    CHYPRE = "chypre"
    AMBER_ORIENTAL = "amber_oriental"
    WOODY_AMBER = "woody_amber"
    GOURMAND = "gourmand"
    MARINE_AQUATIC = "marine_aquatic"
    LEATHER = "leather"
    MUSK = "musk"


class NoteTier(StrEnum):
    """Volatility-based note tier (VP ranges at 25°C)."""
    TOP = "top"      # VP > 50 Pa
    HEART = "heart"  # VP 0.5–50 Pa
    BASE = "base"    # VP < 0.5 Pa


class TextureLayer(StrEnum):
    """Texture layers in modern perfumery (Ellena system)."""
    LIFT = "lift"          # Ambient projection (>200 cm), very brief
    DIFFUSION = "diffusion"  # Sillage (50–200 cm)
    CUSHION = "cushion"      # Personal space (15–50 cm)
    COCOON = "cocoon"        # Intimate (<15 cm)
    SKIN_EFFECT = "skin_effect"  # On-skin (<5 cm)
    VEIL = "veil"            # Transparent overlay
    HALO = "halo"            # Radiant presence at arm's length


class DiffusionLayer(StrEnum):
    """Diffusion distance layers."""
    INTIMATE = "intimate"    # 0–15 cm
    PERSONAL = "personal"    # 15–50 cm
    SILLAGE = "sillage"      # 50–200 cm
    AMBIENT = "ambient"      # >200 cm


class HedonicCategory(StrEnum):
    """Hedonic valence classification for materials."""
    BEAUTIFUL = "beautiful"        # +3 to +5
    INTERESTING = "interesting"    # +1 to +2
    CHALLENGING = "challenging"    # -2 to 0


class MarketSegment(StrEnum):
    """Target market segment for formula optimization."""
    MAINSTREAM = "mainstream"
    NICHE = "niche"
    LUXURY = "luxury"


class MethodologyType(StrEnum):
    """Ten construction methodologies."""
    PYRAMID = "pyramid"                  # Carles / Roudnitska
    ACCORD_BASED = "accord_based"       # Carles / Jellinek
    HEDONIC_OPTIMIZATION = "hedonic_optimization"  # Computational
    SINGLE_MATERIAL = "single_material"  # Roudnitska "One Truth"
    CONSTRAINT_BASED = "constraint_based"  # Regulatory / Cost / Safety
    OAV_TARGETED = "oav_targeted"
    TEXTURE_FIRST = "texture_first"      # Ellena / Modern Minimalism
    PERFORMANCE_FIRST = "performance_first"
    COST_OPTIMIZED = "cost_optimized"
    MINIMAL_MATERIAL = "minimal_material"


class ReferenceTier(StrEnum):
    """Literature reference quality tiers."""
    A_PEER_REVIEWED = "A_peer_reviewed"
    B_CLASSICAL_TEXT = "B_classical_text"
    C_PRACTITIONER = "C_practitioner"
    D_REGULATORY = "D_regulatory"
    E_AUTHOR_ESTIMATE = "E_author_estimate"


class SolubilityRisk(StrEnum):
    """Solubility risk levels at 5°C storage/shipping."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Optimal top:heart:base OAV ratios by concentration bracket
PYRAMID_OAV_RATIOS: dict[ConcentrationBracket, tuple[float, float, float]] = {
    ConcentrationBracket.EDC: (50, 30, 20),
    ConcentrationBracket.EDT: (40, 35, 25),
    ConcentrationBracket.EDP: (30, 35, 35),
    ConcentrationBracket.EXTRAIT: (20, 35, 45),
}

# Hedonic category targets by market segment (% of total formula OAV)
HEDONIC_TARGETS: dict[MarketSegment, dict[HedonicCategory, float]] = {
    MarketSegment.MAINSTREAM: {
        HedonicCategory.BEAUTIFUL: 0.70,
        HedonicCategory.INTERESTING: 0.20,
        HedonicCategory.CHALLENGING: 0.10,
    },
    MarketSegment.NICHE: {
        HedonicCategory.BEAUTIFUL: 0.50,
        HedonicCategory.INTERESTING: 0.30,
        HedonicCategory.CHALLENGING: 0.20,
    },
    MarketSegment.LUXURY: {
        HedonicCategory.BEAUTIFUL: 0.60,
        HedonicCategory.INTERESTING: 0.25,
        HedonicCategory.CHALLENGING: 0.15,
    },
}

# OAV perceptual ranges (after mixture suppression factor ~3-5x)
OAV_PERCEPTUAL_STATUS: dict[str, tuple[float, float]] = {
    "wasted": (0.0, 0.1),
    "trace": (0.1, 1.0),
    "supporting": (1.0, 10.0),
    "dominant": (10.0, 100.0),
    "overwhelming": (100.0, 1000.0),
    "structural_waste": (1000.0, float("inf")),
}

# Optimized log(OAV) standard deviation for perceived complexity
OPTIMAL_LOG_OAV_SD: tuple[float, float] = (0.8, 1.2)

# Mixture suppression factor (Laing & Francis 1989)
MIXTURE_SUPPRESSION_FACTOR: float = 4.0  # midpoint of 3-5 range

# Clausius-Clapeyron constants
DELTA_H_VAP_DEFAULT: float = 60000.0  # J/mol - typical fragrance terpene
R_GAS: float = 8.314  # J/(mol·K)

# Bangkok vs Paris temperature constants
T_BANGKOK: float = 308.15   # 35°C
T_PARIS: float = 295.15     # 22°C
T_SKIN: float = 305.15      # 32°C skin temperature
BANGKOK_VP_RATIO: float = 2.8  # legacy fallback for VP_35C / VP_22C; use bangkok_vp_ratio_default() for explicit context


def bangkok_vp_ratio_default(
    delta_h_vap: float = DELTA_H_VAP_DEFAULT,
) -> float:
    """Return a default Clausius-Clapeyron VP ratio for 22°C → 35°C.

    This is an approximate material-independent fallback used for guidance modules
    when material-level enthalpy estimates are unavailable.
    """
    return clausius_clapeyron_vp_ratio(
        (T_PARIS - 273.15, T_BANGKOK - 273.15),
        delta_h_vap,
    )

# Maceration milestones (days)
MACERATION_STAGES: dict[str, int] = {
    "raw": 0,
    "aldehyde_equilibration": 2,
    "early_maceration": 7,
    "intermediate": 14,
    "first_reliable_evaluation": 28,
    "secondary_maceration": 56,
    "final_maceration": 84,
}

# Accelerated aging Q10 factor
Q10_DEFAULT: float = 2.0

# Hedonic trade-off weights for the simplified objective function
# maximize: alpha*H + beta*L + gamma*S - delta*C
# H = hedonic, L = longevity, S = sillage, C = cost
HEDONIC_WEIGHTS: dict[MarketSegment, dict[str, float]] = {
    MarketSegment.MAINSTREAM: {"alpha": 0.50, "beta": 0.25, "gamma": 0.15, "delta": 0.10},
    MarketSegment.NICHE: {"alpha": 0.65, "beta": 0.15, "gamma": 0.10, "delta": 0.10},
    MarketSegment.LUXURY: {"alpha": 0.55, "beta": 0.20, "gamma": 0.15, "delta": 0.10},
}

# Optical texture ratios for different aesthetics
TEXTURE_RATIOS: dict[str, dict[TextureLayer, float]] = {
    "transparent_skin": {
        TextureLayer.LIFT: 0.10,
        TextureLayer.DIFFUSION: 0.20,
        TextureLayer.CUSHION: 0.15,
        TextureLayer.COCOON: 0.25,
        TextureLayer.SKIN_EFFECT: 0.30,
    },
    "statement": {
        TextureLayer.LIFT: 0.25,
        TextureLayer.DIFFUSION: 0.30,
        TextureLayer.CUSHION: 0.20,
        TextureLayer.COCOON: 0.15,
        TextureLayer.SKIN_EFFECT: 0.10,
    },
    "intimate_skin": {
        TextureLayer.LIFT: 0.05,
        TextureLayer.DIFFUSION: 0.10,
        TextureLayer.CUSHION: 0.20,
        TextureLayer.COCOON: 0.35,
        TextureLayer.SKIN_EFFECT: 0.30,
    },
    "everyday_edt": {
        TextureLayer.LIFT: 0.30,
        TextureLayer.DIFFUSION: 0.25,
        TextureLayer.CUSHION: 0.20,
        TextureLayer.COCOON: 0.15,
        TextureLayer.SKIN_EFFECT: 0.10,
    },
}

# Material class distribution by fragrance family (% by portion)
MATERIAL_CLASS_DISTRIBUTION: dict[FragranceFamily, dict[str, tuple[float, float]]] = {
    FragranceFamily.CITRUS: {
        "florals": (5, 10), "woods": (5, 10), "musks": (10, 15),
        "citrus": (50, 65), "fixatives": (10, 15), "animalic": (0, 0), "resins": (0, 0),
    },
    FragranceFamily.AROMATIC_FOUGERE: {
        "florals": (10, 15), "woods": (15, 20), "musks": (15, 20),
        "citrus": (10, 15), "fixatives": (15, 20), "animalic": (0, 0), "resins": (5, 10),
    },
    FragranceFamily.FLORAL_ROSE: {
        "florals": (45, 55), "woods": (5, 10), "musks": (15, 20),
        "citrus": (5, 10), "fixatives": (10, 15), "animalic": (0, 0), "resins": (0, 5),
    },
    FragranceFamily.FLORAL_JASMINE: {
        "florals": (45, 55), "woods": (5, 10), "musks": (10, 15),
        "citrus": (5, 10), "fixatives": (5, 10), "animalic": (3, 5), "resins": (5, 5),
    },
    FragranceFamily.CHYPRE: {
        "florals": (20, 30), "woods": (20, 30), "musks": (10, 15),
        "citrus": (10, 15), "fixatives": (5, 10), "animalic": (0, 5), "resins": (10, 15),
    },
    FragranceFamily.AMBER_ORIENTAL: {
        "florals": (10, 15), "woods": (15, 20), "musks": (10, 15),
        "citrus": (5, 10), "fixatives": (5, 10), "animalic": (3, 8), "resins": (20, 30),
    },
    FragranceFamily.WOODY_AMBER: {
        "florals": (5, 5), "woods": (40, 55), "musks": (20, 25),
        "citrus": (5, 10), "fixatives": (10, 15), "animalic": (0, 3), "resins": (5, 10),
    },
    FragranceFamily.GOURMAND: {
        "florals": (10, 10), "woods": (5, 5), "musks": (15, 20),
        "citrus": (5, 5), "fixatives": (5, 10), "animalic": (0, 0), "resins": (20, 30),
    },
    FragranceFamily.MARINE_AQUATIC: {
        "florals": (5, 10), "woods": (10, 15), "musks": (20, 25),
        "citrus": (20, 30), "fixatives": (5, 10), "animalic": (0, 0), "resins": (0, 5),
    },
    FragranceFamily.LEATHER: {
        "florals": (5, 10), "woods": (10, 15), "musks": (10, 15),
        "citrus": (5, 10), "fixatives": (10, 15), "animalic": (10, 20), "resins": (15, 20),
    },
}

# Activity coefficient ranges by material class (ethanol matrix, ~20°C)
ACTIVITY_COEFFICIENT_RANGES: dict[str, tuple[float, float]] = {
    "nonpolar_hydrocarbon": (3.0, 3.2),
    "polar_ester": (1.5, 2.0),
    "mid_polarity": (1.2, 1.8),
    "h_bond_donor_acceptor": (0.5, 0.7),
    "macrocyclic_musk": (0.4, 0.6),
}

# VP-to-note-tier mapping
VP_NOTE_TIERS: dict[NoteTier, tuple[float, float]] = {
    NoteTier.TOP: (50.0, float("inf")),
    NoteTier.HEART: (0.5, 50.0),
    NoteTier.BASE: (0.0, 0.5),
}

# Top-heart overlap minimum window (minutes) to prevent olfactory gaps
MIN_OVERLAP_WINDOW_MINUTES: int = 15

# Maximum identifiable components (Livermore & Laing 1996)
MAX_IDENTIFIABLE_COMPONENTS: int = 4

# Optimal number of accords
OPTIMAL_ACCORD_COUNT: int = 3

# Fixative loading by formula type
FIXATIVE_LOADING: dict[str, tuple[float, float]] = {
    "light_edc": (0.10, 0.20),
    "standard_edp": (0.20, 0.35),
    "high_performance_extrait": (0.30, 0.50),
}

# Evaporation half-life categories (skin at 32°C)
HALF_LIFE_CATEGORIES: dict[str, tuple[float, float]] = {
    "fleeting": (0, 10),        # minutes
    "short_top": (15, 45),
    "mid_top": (30, 90),
    "heart": (60, 240),
    "bridge": (180, 480),
    "base": (480, 1080),
    "ultra_base": (1080, float("inf")),
}

# Cross-family blending compatibility
CROSS_FAMILY_COMPATIBILITY: dict[tuple[FragranceFamily, FragranceFamily], str] = {
    (FragranceFamily.FLORAL_ROSE, FragranceFamily.CITRUS): "high",
    (FragranceFamily.FLORAL_JASMINE, FragranceFamily.CITRUS): "high",
    (FragranceFamily.WOODY_AMBER, FragranceFamily.AMBER_ORIENTAL): "high",
    (FragranceFamily.LEATHER, FragranceFamily.CHYPRE): "high",
    (FragranceFamily.AROMATIC_FOUGERE, FragranceFamily.CHYPRE): "high",
    (FragranceFamily.GOURMAND, FragranceFamily.AMBER_ORIENTAL): "high",
    (FragranceFamily.MARINE_AQUATIC, FragranceFamily.FLORAL_ROSE): "medium",
    (FragranceFamily.CITRUS, FragranceFamily.AMBER_ORIENTAL): "medium",
    (FragranceFamily.MARINE_AQUATIC, FragranceFamily.GOURMAND): "low",
    (FragranceFamily.CITRUS, FragranceFamily.LEATHER): "low",
    (FragranceFamily.AMBER_ORIENTAL, FragranceFamily.MARINE_AQUATIC): "very_low",
    (FragranceFamily.FLORAL_JASMINE, FragranceFamily.LEATHER): "low",
}

# Transition families that bridge between two families
TRANSITION_FAMILIES: dict[FragranceFamily, tuple[FragranceFamily, FragranceFamily]] = {
    FragranceFamily.AROMATIC_FOUGERE: (FragranceFamily.AROMATIC_FOUGERE, FragranceFamily.CHYPRE),
    FragranceFamily.AMBER_ORIENTAL: (FragranceFamily.AMBER_ORIENTAL, FragranceFamily.WOODY_AMBER),
    FragranceFamily.CHYPRE: (FragranceFamily.FLORAL_ROSE, FragranceFamily.CHYPRE),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OAVRange:
    """An OAV-based perceptual status range with its formulation role."""
    status: str
    min_oav: float
    max_oav: float
    role: str


@dataclass(frozen=True, slots=True)
class PyramidRatio:
    """Top:Heart:Base OAV ratio for a specific concentration bracket."""
    top: float
    heart: float
    base: float
    bracket: ConcentrationBracket


@dataclass(frozen=True, slots=True)
class PerformanceData:
    """Material performance profile data (Part IX)."""
    material: str
    vp_pa: float            # Vapor pressure at 25°C (Pa)
    half_life_min: float    # Half-life on skin at 32°C (minutes)
    substantivity: str      # Short / Moderate / Long / Very long
    sillage_radius: str     # Intimate / Personal / Sillage / Ambient
    note_tier: NoteTier
    logp: float | None = None
    bangkok_vp_factor: float = 2.8  # Clausius-Clapeyron VP ratio 35°C/22°C


@dataclass(frozen=True, slots=True)
class HedgeShiftZone:
    """A character shift zone for a material's hedonic dose-response."""
    label: str            # e.g., "trace", "working", "dominant", "overdose"
    conc_min_pct: float   # min % in concentrate
    conc_max_pct: float   # max % in concentrate (inf for "and above")
    oav_min: float
    oav_max: float
    character: str         # odor character description
    hedonic: float         # -5 to +5


@dataclass(frozen=True, slots=True)
class MaterialShiftProfile:
    """Complete hedonic dose-response profile for a single material."""
    material: str
    cas: str
    zones: tuple[HedgeShiftZone, ...]
    hill_ec50: float | None = None      # EC50 for Hill equation (% in concentrate)
    hill_n: float | None = None         # Hill coefficient (steepness)
    hill_rmax: float = 1.0             # Maximum response


@dataclass(frozen=True, slots=True)
class SynergyPair:
    """A quantified synergy between two materials."""
    material_a: str
    material_b: str
    mechanism: str
    optimal_ratio: tuple[float, float]  # (A:B) ratio
    synergy_factor: float               # multiplier (e.g., 2.5x)
    oav_range: tuple[float, float]      # active OAV range where synergy holds
    hedonic_impact: float               # hedonic change from synergy
    source: str


@dataclass(frozen=True, slots=True)
class AntagonistPair:
    """Materials that suppress each other when combined."""
    material_a: str
    material_b: str
    problem: str
    max_safe_ratio: str
    mechanism: str


@dataclass(frozen=True, slots=True)
class AccordRecipe:
    """A quantified accord recipe that can be materialized into weight/volume."""
    name: str
    family: FragranceFamily | None
    description: str
    materials: tuple[tuple[str, float], ...]  # (name, parts) pairs
    character: dict[str, float]               # 0–10 dimension scores
    hedonic: float                            # -5 to +5 aggregate
    total_parts: float
    typical_use_pct: float | None = None      # typical % of EdP formula


@dataclass(frozen=True, slots=True)
class ChemicalReaction:
    """A known chemical reaction between fragrance materials."""
    reaction_type: str
    materials_involved_1: str
    materials_involved_2: str
    rate_at_25c: str
    products: str
    smell_change: str
    color_change: str
    mitigation: str


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Result of chemical compatibility check on a formula."""
    reactive_pairs: tuple[ChemicalReaction, ...]
    schiff_base_risk: bool
    oxidation_risk: bool
    hydrolysis_risk: bool
    color_stability_risk: bool
    overall_risk: SolubilityRisk  # reused for chemical risk grading


@dataclass(frozen=True, slots=True)
class SolubilityData:
    """Solubility and handling data for a specific material."""
    material: str
    solubility_in_etoh_96: str           # description
    precipitation_temp_c: float | None   # temperature at which precipitation occurs
    recommended_stock: str               # e.g., "10% in benzyl benzoate"
    co_solvent: str | None = None
    risk: SolubilityRisk = SolubilityRisk.NONE


@dataclass(frozen=True, slots=True)
class Reference:
    """A single literature reference with source quality grading."""
    key: str
    title: str
    tier: ReferenceTier
    data_provided: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class IterationStage:
    """One stage in the formula iteration protocol (Part XI)."""
    stage: str
    timepoint_days: int
    evaluation_focus: str
    allowed_action: str


@dataclass(frozen=True, slots=True)
class BalanceReport:
    """Multi-axis balance evaluation result for a formula."""
    axis_name: str
    score: float           # 0.0–1.0 normalized
    target_range: tuple[float, float] | None
    status: str             # "optimal", "acceptable", "needs_improvement", "critical"
    details: str


@dataclass(frozen=True, slots=True)
class DosingEntry:
    """µL dosing entry for a specific material in a concentrate batch."""
    material: str
    stock_pct: float        # stock concentration (%)
    target_pct: float       # target % in concentrate
    ul_per_10g: float       # µL needed per 10g concentrate
    ppm_in_conc: float      # ppm in concentrate
    est_oav_at_25pct_edp: float  # estimated OAV at 25% EdP


@dataclass(frozen=True, slots=True)
class AnosmiaData:
    """Population-level anosmia data for a specific material."""
    material: str
    receptor: str | None
    anosmia_prevalence_pct: float  # percentage of general population
    population_note: str | None = None
    trainable: bool = False


@dataclass(frozen=True, slots=True)
class NaturalEOData:
    """Character-defining constituent data for a natural essential oil."""
    eo_name: str
    mass_dominant_constituent: str      # highest mass fraction
    mass_dominant_pct: float
    character_defining_constituent: str  # the odor-character-defining molecule
    character_constituent_odt_ppb: float  # ODT in air (ppb)
    note: str


@dataclass(frozen=True, slots=True)
class GhostNoteMaterial:
    """Sub-threshold texture material (perceptible below conscious OAV-1)."""
    material: str
    mechanism: str
    texture_type: str
    receptor: str | None = None


@dataclass(frozen=True, slots=True)
class ConcentrationConversion:
    """Rules for converting formulas between concentration brackets."""
    from_bracket: ConcentrationBracket
    to_bracket: ConcentrationBracket
    rule: str
    base_adjustment_pct: float  # % change to base loading
    heart_adjustment_pct: float
    top_adjustment_pct: float


@dataclass(frozen=True, slots=True)
class MethodologySpec:
    """Specification for one of the 10 construction methodologies."""
    method_type: MethodologyType
    name: str
    philosophy: str
    optimal_for: list[FragranceFamily]
    key_parameters: tuple[tuple[str, float | str], ...]


# ---------------------------------------------------------------------------
# The "indispensable flaw" table — one flaw material per family
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FamilyFlaw:
    """The Roudnitska 'indispensable flaw' — material providing contrast per family."""
    family: FragranceFamily
    flaw_material: str
    target_oav_min: float
    target_oav_max: float
    mechanism: str


FAMILY_FLAWS: tuple[FamilyFlaw, ...] = (
    FamilyFlaw(FragranceFamily.FLORAL_JASMINE, "Indole", 1, 5, "Animalic warmth, narcotic depth"),
    FamilyFlaw(FragranceFamily.LEATHER, "Isobutyl Quinoline (IBQ)", 0.5, 3, "Harsh tarry leather edge"),
    FamilyFlaw(FragranceFamily.CHYPRE, "Birch Tar", 0.1, 1, "Smoky-medicinal contrast"),
    FamilyFlaw(FragranceFamily.AMBER_ORIENTAL, "Skatole", 0.01, 0.1, "Fecal-floral tension"),
    FamilyFlaw(FragranceFamily.FLORAL_ROSE, "Violet Leaf Absolute", 2, 8, "Bitter metallic green edge"),
    FamilyFlaw(FragranceFamily.MARINE_AQUATIC, "Calone", 3, 15, "Metallic-ozonic sharpness"),
)


# ---------------------------------------------------------------------------
# Pre-computed OAV perceptual status lookups
# ---------------------------------------------------------------------------

def get_oav_perceptual_status(oav: float) -> str:
    """Return the perceptual status label for a given OAV value."""
    for status, (lo, hi) in OAV_PERCEPTUAL_STATUS.items():
        if lo <= oav < hi:
            return status
    return "structural_waste"


def get_note_tier_from_vp(vp_pa: float) -> NoteTier:
    """Determine note tier from vapor pressure (Pa at 25°C)."""
    for tier, (lo, hi) in VP_NOTE_TIERS.items():
        if lo <= vp_pa < hi:
            return tier
    return NoteTier.BASE


def clausius_clapeyron_vp_ratio(
    t_c: tuple[float, float] = (22.0, 35.0),
    delta_h_vap: float = DELTA_H_VAP_DEFAULT,
) -> float:
    """Calculate VP ratio at two Celsius temperatures using Clausius-Clapeyron.

    Returns P2/P1 where T2 > T1 typically.
    """
    t1_k = t_c[0] + 273.15
    t2_k = t_c[1] + 273.15
    import math
    exponent = (delta_h_vap / R_GAS) * (1.0 / t1_k - 1.0 / t2_k)
    return math.exp(exponent)


def accelerated_aging_time(
    real_time_days: float,
    real_temp_c: float = 21.0,
    aging_temp_c: float = 50.0,
    q10: float = Q10_DEFAULT,
) -> float:
    """Calculate accelerated aging time equivalent.

    Args:
        real_time_days: real-time duration to simulate
        real_temp_c: real storage temperature (°C)
        aging_temp_c: accelerated aging temperature (°C)
        q10: temperature coefficient (default 2.0)

    Returns:
        Accelerated aging time in days needed to simulate real_time_days
    """
    delta_t = aging_temp_c - real_temp_c
    return real_time_days / (q10 ** (delta_t / 10.0))


def estimate_mixture_suppression(
    n_materials: int,
    suppression_factor: float = MIXTURE_SUPPRESSION_FACTOR,
) -> float:
    """Estimate effective OAV multiplier accounting for mixture suppression.

    For n_materials < 5: no suppression (1.0)
    For n_materials 5-15: linear ramp to suppression_factor
    For n_materials > 15: full suppression_factor
    """
    if n_materials < 5:
        return 1.0
    if n_materials <= 15:
        frac = (n_materials - 5) / 10.0
        return 1.0 - frac * (1.0 - 1.0 / suppression_factor)
    return 1.0 / suppression_factor
