"""Ten quantified construction methodologies for fragrance formulation.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Each methodology is encoded as a composable strategy that produces ingredient
targets, OAV ranges, and structural constraints. Designed to integrate with
the gate-first pipeline via FormulaState and optimize for hedonic output.

Methodologies (from Formulation Intelligence Database, Part II):
  A. Pyramid Construction (Carles / Roudnitska)
  B. Accord-Based Construction (Carles / Jellinek)
  C. Hedonic Optimization (Computational)
  D. Single-Material Expansion (Roudnitska "One Truth")
  E. Constraint-Based Construction (Regulatory / Cost / Safety)
  F. OAV-Targeted Construction
  G. Texture-First Construction (Ellena / Modern Minimalism)
  H. Performance-First Construction
  I. Cost-Optimized Construction (Commercial)
  J. Minimum-Material Construction (Minimalist / Niche)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ._shared_types import (
    bangkok_vp_ratio_default,
    FIXATIVE_LOADING,
    HEDONIC_TARGETS,
    HEDONIC_WEIGHTS,
    PYRAMID_OAV_RATIOS,
    TEXTURE_RATIOS,
    ConcentrationBracket,
    FragranceFamily,
    HedonicCategory,
    MarketSegment,
    MethodologySpec,
    MethodologyType,
    TextureLayer,
    estimate_mixture_suppression,
)

# ---------------------------------------------------------------------------
# Methodology A: Pyramid Construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PyramidBlueprint:
    """OAV targets per note tier for a pyramid-constructed formula."""

    bracket: ConcentrationBracket
    top_target: tuple[float, float]     # (min, max) % of total formula OAV
    heart_target: tuple[float, float]
    base_target: tuple[float, float]
    min_overlap_minutes: int = 15       # top-heart overlap to prevent olfactory cliff


def get_pyramid_blueprint(bracket: ConcentrationBracket) -> PyramidBlueprint:
    """Return the optimal pyramid ratio blueprint for a concentration bracket."""
    ratios = PYRAMID_OAV_RATIOS[bracket]
    # Allow ±5% tolerance
    return PyramidBlueprint(
        bracket=bracket,
        top_target=(ratios[0] - 5, ratios[0] + 5),
        heart_target=(ratios[1] - 5, ratios[1] + 5),
        base_target=(ratios[2] - 5, ratios[2] + 5),
        min_overlap_minutes=15,
    )


def evaluate_pyramid_balance(
    top_oav_total: float,
    heart_oav_total: float,
    base_oav_total: float,
    blueprint: PyramidBlueprint,
) -> tuple[float, str]:
    """Score how well a formula's OAV distribution matches the pyramid blueprint.

    Returns:
        (score 0-1, status message)
    """
    total = top_oav_total + heart_oav_total + base_oav_total
    if total == 0:
        return 0.0, "No OAV detected"

    t_frac = top_oav_total / total * 100
    h_frac = heart_oav_total / total * 100
    b_frac = base_oav_total / total * 100

    t_ok = blueprint.top_target[0] <= t_frac <= blueprint.top_target[1]
    h_ok = blueprint.heart_target[0] <= h_frac <= blueprint.heart_target[1]
    b_ok = blueprint.base_target[0] <= b_frac <= blueprint.base_target[1]

    score = (t_ok + h_ok + b_ok) / 3.0

    if score >= 0.9:
        return score, "Optimal pyramid balance"
    if score >= 0.6:
        return score, "Acceptable pyramid balance — consider adjustment"
    return score, "Pyramid imbalance — restructure T:H:B ratios"


# ---------------------------------------------------------------------------
# Method B: Accord-Based Construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AccordSpec:
    """Specification for a single accord within an accord-based formula."""

    name: str
    weight_pct: float               # % of total formula weight for this accord
    materials: tuple[tuple[str, float], ...]  # (material_name, parts_in_accord)
    internal_oav_targets: dict[str, float]    # material → target OAV in accord
    is_character: bool = True                # False = this accord is invisible atmosphere
    total_parts: float = 100.0


def materialize_accord_spec(
    specs: Sequence[AccordSpec],
    concentrate_g: float = 10.0,
) -> dict[str, float]:
    """Convert accord specifications into a raw ingredient dict (name → grams).

    Args:
        specs: ordered list of accord specifications with weight percentages
        concentrate_g: total concentrate mass in grams

    Returns:
        dict mapping material name to grams for the full formula
    """
    ingredients: dict[str, float] = {}
    for spec in specs:
        accord_mass = concentrate_g * (spec.weight_pct / 100.0)
        for mat_name, parts in spec.materials:
            mat_mass = accord_mass * (parts / spec.total_parts)
            ingredients[mat_name] = ingredients.get(mat_name, 0.0) + mat_mass
    return ingredients


def recommend_accord_count(n_materials: int) -> int:
    """Recommend optimal number of accords based on total materials.

    Livermore & Laing: humans discriminate 3-4 components maximum.
    """
    if n_materials <= 12:
        return 2
    if n_materials <= 30:
        return 3
    return 3  # never exceed 3 — 4th accord fragments into noise


# ---------------------------------------------------------------------------
# Method C: Hedonic Optimization
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HedonicMaterialTarget:
    """Hedonic dose-response target for a single material."""

    material: str
    intrinsic_hedonic: float         # -5 to +5 neat hedonic
    sweet_spot_oav: tuple[float, float]  # (min, max) optimal OAV
    flip_oav: float | None = None    # OAV at which character flips
    flip_description: str | None = None
    context_shift: dict[str, float] = field(default_factory=dict)  # family → hedonic delta
    category: HedonicCategory = HedonicCategory.INTERESTING


def compute_hedonic_objective(
    hedonic_score: float,
    longevity_score: float,
    sillage_score: float,
    cost_score: float,
    segment: MarketSegment,
) -> float:
    """Compute the simplified hedonic objective function.

    maximize: alpha*H + beta*L + gamma*S - delta*C

    Returns a score where higher is better.
    """
    w = HEDONIC_WEIGHTS[segment]
    return (
        w["alpha"] * hedonic_score
        + w["beta"] * longevity_score
        + w["gamma"] * sillage_score
        - w["delta"] * cost_score
    )


def check_hedonic_distribution(
    materials_hedonic: Mapping[str, tuple[float, float]],  # name → (OAV, hedonic)
    segment: MarketSegment,
) -> tuple[float, str]:
    """Check if a formula meets hedonic category distribution targets.

    Returns:
        (compliance_score 0-1, status message)
    """
    targets = HEDONIC_TARGETS[segment]
    total_oav = sum(o for o, _ in materials_hedonic.values())
    if total_oav == 0:
        return 0.0, "No hedonic-bearing OAV"

    beautiful_oav = sum(o for (o, h) in materials_hedonic.values() if h >= 3.0)
    interesting_oav = sum(o for (o, h) in materials_hedonic.values() if 1.0 <= h < 3.0)
    challenging_oav = sum(o for (o, h) in materials_hedonic.values() if -2.0 <= h < 1.0)

    b_frac = beautiful_oav / total_oav
    i_frac = interesting_oav / total_oav
    c_frac = challenging_oav / total_oav

    b_ok = b_frac >= targets[HedonicCategory.BEAUTIFUL] * 0.8
    i_ok = i_frac >= targets[HedonicCategory.INTERESTING] * 0.5
    c_ok = c_frac <= targets[HedonicCategory.CHALLENGING] * 1.2

    issues = []
    if not b_ok:
        issues.append(f"beautiful OAV below target ({b_frac:.0%} < {targets[HedonicCategory.BEAUTIFUL]:.0%})")
    if not i_ok:
        issues.append(f"interesting OAV below target ({i_frac:.0%} < {targets[HedonicCategory.INTERESTING]:.0%})")
    if not c_ok:
        issues.append(f"challenging OAV above target ({c_frac:.0%} > {targets[HedonicCategory.CHALLENGING]:.0%})")

    score = (b_ok + i_ok + c_ok) / 3.0
    status = "; ".join(issues) if issues else "Hedonic distribution optimal"
    return score, status


# ---------------------------------------------------------------------------
# Method D: Single-Material Expansion
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AnchorMaterial:
    """An anchor material suitable for single-material expansion methodology."""

    material: str
    best_oav_range: tuple[float, float]
    character_when_centered: str
    max_formula_size: int
    family: FragranceFamily


ANCHOR_MATERIALS: tuple[AnchorMaterial, ...] = (
    AnchorMaterial("Methyl Ionone Gamma", (15, 60), "Violet-orris, powdery", 22, FragranceFamily.FLORAL_ROSE),
    AnchorMaterial("Beta-Damascenone", (1, 8), "Rose-plum, deep fruit", 18, FragranceFamily.FLORAL_ROSE),
    AnchorMaterial("Hedione HC", (30, 120), "Radiant jasmine, luminous", 28, FragranceFamily.FLORAL_JASMINE),
    AnchorMaterial("Ambroxan", (20, 80), "Skin-amber, clean sensuality", 22, FragranceFamily.WOODY_AMBER),
    AnchorMaterial("Iso E Super", (40, 150), "Woody-cedar, skin-amplifier", 30, FragranceFamily.WOODY_AMBER),
    AnchorMaterial("Javanol", (10, 40), "Creamy sandalwood, soft rose", 22, FragranceFamily.WOODY_AMBER),
    AnchorMaterial("Vetiver EO (Haitian)", (5, 25), "Smoky-earthy, complex", 20, FragranceFamily.WOODY_AMBER),
)


def select_anchor(family: FragranceFamily) -> list[AnchorMaterial]:
    """Return anchor materials suitable for a given fragrance family."""
    return [a for a in ANCHOR_MATERIALS if a.family == family]


# ---------------------------------------------------------------------------
# Method E: Constraint-Based Construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class IFRAConstraint:
    """IFRA 51st Amendment Category 4 constraint for a material."""

    material: str
    cat4_max_pct: float          # max % in finished product
    primary_concern: str
    applies_to_naturals: bool = True  # also applies to EOs containing this material


# Key IFRA Cat4 limits (from Part II, Method E)
IFRA_CAT4_LIMITS: tuple[IFRAConstraint, ...] = (
    IFRAConstraint("Oakmoss Absolute", 0.10, "Dermal sensitization (atranol/chloroatranol)"),
    IFRAConstraint("Treemoss Extract", 0.10, "Dermal sensitization"),
    IFRAConstraint("Coumarin", 1.50, "Dermal sensitization + systemic toxicity"),
    IFRAConstraint("Benzyl Benzoate", 4.80, "Dermal sensitization + systemic toxicity"),
    IFRAConstraint("Benzyl Salicylate", 7.30, "Dermal sensitization + systemic toxicity"),
    IFRAConstraint("Eugenol", 2.50, "Dermal sensitization"),
    IFRAConstraint("Geraniol", 4.70, "Dermal sensitization"),
    IFRAConstraint("Citronellol", 12.00, "Dermal sensitization"),
    IFRAConstraint("Isoeugenol", 0.11, "Dermal sensitization"),
    IFRAConstraint("Farnesol", 1.20, "Dermal sensitization + systemic toxicity"),
    IFRAConstraint("Lilial", 1.40, "Dermal sensitization + systemic toxicity"),
    IFRAConstraint("Lyral (HICC)", 0.20, "Dermal sensitization (potent)"),
    IFRAConstraint("Citral", 0.60, "Dermal sensitization"),
    IFRAConstraint("Amyl Cinnamal", 7.00, "Dermal sensitization"),
    IFRAConstraint("Cinnamal", 0.25, "Dermal sensitization"),
    IFRAConstraint("Alpha-Isomethylionone", 30.00, "Dermal sensitization"),
    IFRAConstraint("Hydroxycitronellal", 2.10, "Dermal sensitization"),
    IFRAConstraint("Methyl 2-Octynoate", 0.047, "Dermal sensitization (potent)"),
)


@dataclass(frozen=True, slots=True)
class CostEfficiencyData:
    """Cost optimization data for a material."""

    material: str
    approx_cost_per_kg: tuple[float, float]  # (low, high) USD/kg
    oav_per_1pct_in_conc: float             # approximate OAV at 1% in concentrate
    efficiency: str                           # "Very high", "High", "Low", etc.


COST_EFFICIENCY: tuple[CostEfficiencyData, ...] = (
    CostEfficiencyData("Linalool", (5, 15), 200, "Very high"),
    CostEfficiencyData("Hedione", (15, 30), 50, "High"),
    CostEfficiencyData("Iso E Super", (15, 25), 80, "High"),
    CostEfficiencyData("Galaxolide 50%", (20, 40), 45, "High"),
    CostEfficiencyData("Coumarin", (5, 15), 120, "Very high"),
    CostEfficiencyData("Ambroxan", (100, 200), 500, "High"),
    CostEfficiencyData("Rose Absolute", (3000, 8000), 20, "Very low"),
    CostEfficiencyData("Jasmine Absolute", (1500, 4000), 8, "Very low"),
    CostEfficiencyData("Orris Butter", (40000, 80000), 30, "Extremely low"),
)


def check_ifra_compliance(
    material_pcts: Mapping[str, float],  # material name → % in finished product
) -> tuple[bool, list[str]]:
    """Check a formula against IFRA Cat4 limits.

    Returns:
        (is_compliant, list_of_violations)
    """
    violations: list[str] = []
    limits_lookup = {c.material.lower(): c for c in IFRA_CAT4_LIMITS}

    for mat_name, pct in material_pcts.items():
        constraint = limits_lookup.get(mat_name.lower())
        if constraint and pct > constraint.cat4_max_pct:
            violations.append(
                f"{mat_name}: {pct:.3f}% > IFRA Cat4 limit {constraint.cat4_max_pct:.3f}% "
                f"({constraint.primary_concern})"
            )

    return len(violations) == 0, violations


def get_oav_cost_efficiency(
    material_name: str,
) -> CostEfficiencyData | None:
    """Return cost efficiency data for a material."""
    for ce in COST_EFFICIENCY:
        if ce.material.lower() == material_name.lower():
            return ce
    return None


# ---------------------------------------------------------------------------
# Method F: OAV-Targeted Construction
# ---------------------------------------------------------------------------

def get_oav_sweet_spot(oav: float) -> str:
    """Classify an OAV value into its perceptual sweet-spot category."""
    if oav < 0.1:
        return "wasted (below detection)"
    if oav < 1.0:
        return "trace (receptor priming)"
    if oav < 10.0:
        return "supporting (ensemble texture)"
    if oav < 100.0:
        return "dominant (primary identifiable)"
    if oav < 1000.0:
        return "overwhelming (background amplifier)"
    return "structural waste (unusable at this concentration)"


def apply_mixture_suppression(oav: float, n_materials: int) -> float:
    """Apply Laing & Francis mixture suppression to a calculated OAV.

    In complex formulas (15+ materials), effective OAV is 3-5x lower
    than single-material OAV calculations predict.
    """
    factor = estimate_mixture_suppression(n_materials)
    return oav * factor


# ---------------------------------------------------------------------------
# Method G: Texture-First Construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TextureMaterial:
    """A material classified by its texture contribution."""

    material: str
    texture_layer: TextureLayer
    vp_range_pa: tuple[float, float]
    sillage_distance: str


TEXTURE_MATERIALS: tuple[TextureMaterial, ...] = (
    TextureMaterial("Bergamot FCF", TextureLayer.LIFT, (20, 200), "Ambient (>200 cm)"),
    TextureMaterial("Dihydromyrcenol", TextureLayer.LIFT, (20, 200), "Ambient (>200 cm)"),
    TextureMaterial("C10 Aldehyde", TextureLayer.LIFT, (20, 200), "Ambient (>200 cm)"),
    TextureMaterial("Hedione", TextureLayer.DIFFUSION, (0.1, 2), "50-200 cm"),
    TextureMaterial("Iso E Super", TextureLayer.DIFFUSION, (0.1, 2), "50-200 cm"),
    TextureMaterial("Calone", TextureLayer.DIFFUSION, (0.1, 2), "50-200 cm"),
    TextureMaterial("Benzyl Salicylate", TextureLayer.CUSHION, (0.0001, 0.01), "15-50 cm"),
    TextureMaterial("Coumarin", TextureLayer.CUSHION, (0.0001, 0.01), "15-50 cm"),
    TextureMaterial("Vanillin", TextureLayer.CUSHION, (0.0001, 0.01), "15-50 cm"),
    TextureMaterial("Galaxolide", TextureLayer.COCOON, (0.0, 0.001), "<15 cm"),
    TextureMaterial("Cashmeran", TextureLayer.COCOON, (0.0, 0.001), "<15 cm"),
    TextureMaterial("Ambroxan", TextureLayer.SKIN_EFFECT, (0.0001, 0.001), "<5 cm"),
    TextureMaterial("Javanol", TextureLayer.SKIN_EFFECT, (0.0001, 0.001), "<5 cm"),
    TextureMaterial("Habanolide", TextureLayer.VEIL, (0.001, 0.01), "Transparent overlay"),
    TextureMaterial("Floralozone", TextureLayer.VEIL, (0.001, 0.01), "Transparent overlay"),
    TextureMaterial("Hedione HC", TextureLayer.HALO, (0.001, 0.1), "Arm's length radiant"),
    TextureMaterial("Ambroxan Super", TextureLayer.HALO, (0.001, 0.1), "Arm's length radiant"),
)


def get_texture_classification(material_name: str) -> TextureLayer | None:
    """Return the texture layer classification for a material."""
    for tm in TEXTURE_MATERIALS:
        if tm.material.lower() == material_name.lower():
            return tm.texture_layer
    return None


def get_texture_blueprint(aesthetic: str) -> dict[TextureLayer, float]:
    """Return optimal texture ratios for a given aesthetic target.

    Valid aesthetics: "transparent_skin", "statement", "intimate_skin", "everyday_edt"
    """
    return dict(TEXTURE_RATIOS.get(aesthetic, TEXTURE_RATIOS["transparent_skin"]))


# ---------------------------------------------------------------------------
# Method H: Performance-First Construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FixativeStrategy:
    """Fixative loading strategy for a formula type."""

    formula_type: str
    min_fixative_pct: float
    max_fixative_pct: float
    max_vp_pa: float = 0.01


def get_fixative_strategy(formula_type: str) -> FixativeStrategy:
    """Return fixative loading targets for a formula type."""
    ranges = FIXATIVE_LOADING.get(
        formula_type, FIXATIVE_LOADING["standard_edp"]
    )
    return FixativeStrategy(
        formula_type=formula_type,
        min_fixative_pct=ranges[0],
        max_fixative_pct=ranges[1],
        max_vp_pa=0.01 if formula_type != "high_performance_extrait" else 0.005,
    )


def evaporative_half_life_estimator(vp_pa: float, logp: float | None = None) -> float:
    """Estimate evaporative half-life on skin at 32°C from VP and logP.

    This is a heuristic model — values are approximate.
    High logP (>4) retards evaporation via skin lipid binding.
    """
    # Base half-life in minutes from VP
    if vp_pa > 50:
        base_half_life = 10.0 + (100.0 - vp_pa) * 0.5
    elif vp_pa > 0.5:
        base_half_life = 45.0 + (50.0 - vp_pa) * 5.0
    elif vp_pa > 0.001:
        base_half_life = 240.0 + (0.5 - vp_pa) * 1000.0
    else:
        base_half_life = 1000.0  # ultra-base

    # logP skin binding bonus
    logp_bonus = 1.0
    if logp is not None:
        if logp > 4.0:
            logp_bonus = 1.5 + (logp - 4.0) * 0.5
        elif logp > 2.0:
            logp_bonus = 1.0 + (logp - 2.0) * 0.25

    return base_half_life * logp_bonus


def bangkok_temperature_adjustment(vp_pa: float) -> float:
    """Adjust VP from 22°C to Bangkok-like 35°C using a default Clausius-Clapeyron estimate.

    Returns VP at 35°C.
    """
    return vp_pa * bangkok_vp_ratio_default()


# ---------------------------------------------------------------------------
# Method I: Cost-Optimized Construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NaturalExtension:
    """Strategy for extending a costly natural with synthetics while preserving character."""

    natural: str
    natural_pct: float             # % of natural in concentrate
    extension_ratio: float         # how much the total blend expands
    synthetics: dict[str, float]   # synthetic → parts to add
    character_fidelity: float       # 0-1 fidelity estimate
    cost_saving_pct: float         # % cost saved vs pure natural


NATURAL_EXTENSIONS: tuple[NaturalExtension, ...] = (
    NaturalExtension(
        "Rose Absolute", 2.0, 5.0,
        {"PEA": 3.0, "Geraniol": 3.0, "Citronellol": 4.0, "Rhodinol": 1.0},
        0.88, 85.0,
    ),
    NaturalExtension(
        "Jasmine Absolute", 1.0, 18.0,
        {"Benzyl Acetate": 12.0, "Hedione": 8.0, "Linalool": 3.0, "Indole": 0.2, "Benzyl Benzoate": 4.0},
        0.85, 90.0,
    ),
    NaturalExtension(
        "Sandalwood EO", 5.0, 8.0,
        {"Javanol": 1.5, "Bacdanol": 2.0, "Polysantol": 1.0},
        0.80, 70.0,
    ),
    NaturalExtension(
        "Vetiver EO", 2.0, 8.0,
        {"Iso E Super": 3.0, "Vetivenyl Acetate": 1.0, "Cedar Atlas": 2.0},
        0.75, 60.0,
    ),
)


def get_extension(natural_name: str) -> NaturalExtension | None:
    """Return the cost-saving natural extension strategy for a given natural."""
    for ne in NATURAL_EXTENSIONS:
        if ne.natural.lower() == natural_name.lower():
            return ne
    return None


# ---------------------------------------------------------------------------
# Method J: Minimum-Material Construction
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MinimumViableFormula:
    """Minimum viable formula size per fragrance family."""

    family: FragranceFamily
    min_materials: int
    max_materials: int
    key_strategy: str
    core_materials: tuple[str, ...]


MINIMUM_VIABLE_FORMULAS: tuple[MinimumViableFormula, ...] = (
    MinimumViableFormula(
        FragranceFamily.FLORAL_ROSE, 4, 6,
        "PEA + Geraniol + Damascenone + Rose Oxide + Muguet modifier",
        ("PEA", "Geraniol", "Beta-Damascenone", "Rose Oxide"),
    ),
    MinimumViableFormula(
        FragranceFamily.FLORAL_JASMINE, 5, 8,
        "Benzyl Acetate + Hedione + Indole + Linalool + Benzyl Benzoate",
        ("Benzyl Acetate", "Hedione", "Indole", "Linalool", "Benzyl Benzoate"),
    ),
    MinimumViableFormula(
        FragranceFamily.WOODY_AMBER, 3, 5,
        "Iso E Super + Ambroxan + Javanol / Sandalwood EO",
        ("Iso E Super", "Ambroxan", "Javanol"),
    ),
    MinimumViableFormula(
        FragranceFamily.AMBER_ORIENTAL, 4, 6,
        "Labdanum + Vanillin + Benzyl Benzoate + Iso E Super",
        ("Labdanum", "Vanillin", "Benzyl Benzoate", "Iso E Super"),
    ),
    MinimumViableFormula(
        FragranceFamily.MUSK, 3, 4,
        "Galaxolide + Habanolide + Ambrettolide (3 classes)",
        ("Galaxolide", "Habanolide", "Ambrettolide"),
    ),
    MinimumViableFormula(
        FragranceFamily.CITRUS, 3, 5,
        "Bergamot FCF + Dihydromyrcenol + Hedione + Fixative",
        ("Bergamot FCF", "Dihydromyrcenol", "Hedione"),
    ),
    MinimumViableFormula(
        FragranceFamily.AROMATIC_FOUGERE, 4, 6,
        "Lavender + Coumarin + Oakmoss/Veramoss + Bergamot + Musk",
        ("Lavender EO", "Coumarin", "Veramoss", "Bergamot FCF"),
    ),
)


def get_min_viable(family: FragranceFamily) -> MinimumViableFormula | None:
    """Return minimum viable formula spec for a fragrance family."""
    for mvf in MINIMUM_VIABLE_FORMULAS:
        if mvf.family == family:
            return mvf
    return None


# ---------------------------------------------------------------------------
# Multi-functional materials (character + texture + performance simultaneously)
# ---------------------------------------------------------------------------

MULTIFUNCTIONAL_MATERIALS: tuple[tuple[str, str], ...] = (
    ("Ambroxan", "skin-amber character + halo texture + very long performance (logP ~5.0)"),
    ("Iso E Super", "woody-cedar character + diffusion texture + long performance"),
    ("Hedione HC", "jasmine-radiance character + diffusion + moderate skin depot"),
    ("Beta-Damascenone", "rose-plum character + minimal fixation (logP ~3.9 depot)"),
    ("Coumarin", "hay-tonka character + cushion texture + excellent fixation (IFRA-limited)"),
)


# ---------------------------------------------------------------------------
# Methodology registry
# ---------------------------------------------------------------------------

METHODOLOGY_SPECS: tuple[MethodologySpec, ...] = (
    MethodologySpec(
        MethodologyType.PYRAMID, "Pyramid Construction",
        "Organize by volatility class. The pyramid is an evaporation schedule.",
        [FragranceFamily.CITRUS, FragranceFamily.CHYPRE, FragranceFamily.FLORAL_ROSE,
         FragranceFamily.FLORAL_JASMINE, FragranceFamily.AMBER_ORIENTAL, FragranceFamily.AROMATIC_FOUGERE],
        (),
    ),
    MethodologySpec(
        MethodologyType.ACCORD_BASED, "Accord-Based Construction",
        "Build 3-4 discrete accords each smelling like a coherent entity.",
        [FragranceFamily.CHYPRE, FragranceFamily.AROMATIC_FOUGERE, FragranceFamily.LEATHER, FragranceFamily.FLORAL_JASMINE],
        (),
    ),
    MethodologySpec(
        MethodologyType.HEDONIC_OPTIMIZATION, "Hedonic Optimization",
        "Define the formula as an optimization problem maximizing hedonic output.",
        [FragranceFamily.GOURMAND, FragranceFamily.AMBER_ORIENTAL],
        (),
    ),
    MethodologySpec(
        MethodologyType.SINGLE_MATERIAL, "Single-Material Expansion",
        "Begin with the single most beautiful characteristic of one material.",
        [FragranceFamily.WOODY_AMBER, FragranceFamily.MUSK],
        (),
    ),
    MethodologySpec(
        MethodologyType.CONSTRAINT_BASED, "Constraint-Based Construction",
        "Build within regulatory, cost, and safety constraints.",
        [FragranceFamily.CITRUS, FragranceFamily.LEATHER, FragranceFamily.CHYPRE, FragranceFamily.AROMATIC_FOUGERE],
        (),
    ),
    MethodologySpec(
        MethodologyType.OAV_TARGETED, "OAV-Targeted Construction",
        "Define OAV ranges for every material before dosing.",
        [FragranceFamily.FLORAL_JASMINE, FragranceFamily.MUSK, FragranceFamily.MARINE_AQUATIC],
        (),
    ),
    MethodologySpec(
        MethodologyType.TEXTURE_FIRST, "Texture-First Construction",
        "Design the spatial-temporal texture before selecting character materials.",
        [FragranceFamily.MARINE_AQUATIC, FragranceFamily.WOODY_AMBER],
        (),
    ),
    MethodologySpec(
        MethodologyType.PERFORMANCE_FIRST, "Performance-First Construction",
        "Build fixative architecture first; layer character materials onto it.",
        [FragranceFamily.CITRUS, FragranceFamily.MUSK, FragranceFamily.WOODY_AMBER],
        (),
    ),
    MethodologySpec(
        MethodologyType.COST_OPTIMIZED, "Cost-Optimized Construction",
        "Maximize hedonic output per cost while maintaining character fidelity.",
        [FragranceFamily.CITRUS, FragranceFamily.AROMATIC_FOUGERE],
        (),
    ),
    MethodologySpec(
        MethodologyType.MINIMAL_MATERIAL, "Minimum-Material Construction",
        "Achieve the target character with the fewest possible materials.",
        [FragranceFamily.MUSK, FragranceFamily.WOODY_AMBER],
        (),
    ),
)
