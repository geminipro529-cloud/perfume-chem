"""Comprehensive perfume formula rating system — 10-star characteristics + 0-100 scores.

Implements dual rating methodology:
1. 10-STAR RATINGS: Consumer/wearability-focused characteristics (★★★★★★★★★★)
2. 0-100 SCORES: Technical/compositional metrics (already in optimizer/scoring.py)

Star ratings evaluate subjective wearability, versatility, originality, sophistication.
Scores evaluate objective structure: longevity, sillage, balance, complexity, etc.

Both systems run in parallel for comprehensive formula assessment.
"""

from dataclasses import dataclass
from typing import Dict
from pathlib import Path

from engine.optimizer.scoring import FormulaScorer, FormulaVector
from engine.ingredient_intelligence import get_profile, DIMENSIONS
from engine.chemical_data_validator import is_blocked_chemical


# ═══════════════════════════════════════════════════════════════════════════════
# 10-STAR RATING SYSTEM — Wearability & Consumer Appeal
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StarRatings:
    """10-star ratings (0.0-10.0) for wearability/consumer characteristics."""
    wearability: float  # Comfort, not challenging, easy to wear daily
    versatility: float  # Season/occasion flexibility, day-to-night
    originality: float  # Uniqueness, creativity, non-generic
    sophistication: float  # Refinement, artistry, perfumer skill
    signature_potential: float  # Memorability, distinctiveness, personal identity
    mass_appeal: float  # Compliment factor, crowd-pleasing
    gender_versatility: float  # Unisex rating, not polarizing
    age_range: float  # Broad age appropriateness (higher = more universal)
    formula_elegance: float  # Structural elegance: proportion rationality, fixative anchoring
    value_for_money: float  # Quality-to-cost ratio

    def as_dict(self) -> Dict[str, float]:
        return {
            "wearability": self.wearability,
            "versatility": self.versatility,
            "originality": self.originality,
            "sophistication": self.sophistication,
            "signature_potential": self.signature_potential,
            "mass_appeal": self.mass_appeal,
            "gender_versatility": self.gender_versatility,
            "age_range": self.age_range,
            "formula_elegance": self.formula_elegance,
            "value_for_money": self.value_for_money,
        }

    def average(self) -> float:
        """Overall star rating (mean of all characteristics)."""
        vals = list(self.as_dict().values())
        return sum(vals) / len(vals) if vals else 0.0


def rate_wearability(fv: FormulaVector, character_radar: Dict[str, float]) -> float:
    """Comfort and ease of wear — penalize challenging notes (animalic, smoky, heavy).
    
    10 stars = clean, fresh, easy, comfortable
    5 stars = challenging, polarizing
    0 stars = unwearable, harsh
    """
    # Comfort from wearable dimensions (max ~6 pts)
    comfort = character_radar.get("freshness", 0) * 0.5
    comfort += character_radar.get("powdery", 0) * 0.3
    comfort += character_radar.get("creamy", 0) * 0.3
    comfort += character_radar.get("floral", 0) * 0.2
    comfort += character_radar.get("sweetness", 0) * 0.15

    # Penalties for challenging notes (max ~20 pts at extreme)
    penalties = 0
    penalties += character_radar.get("animalic", 0) * 1.5
    penalties += character_radar.get("smoky", 0) * 1.2
    penalties += character_radar.get("green", 0) * 0.3
    penalties += character_radar.get("spicy", 0) * 0.4

    # Baseline 3.0: clean formulas reach 8-10, challenging ones drop to 0-3
    score = comfort - penalties + 3.0
    return max(0.0, min(10.0, score))


def rate_versatility(fv: FormulaVector, character_radar: Dict[str, float]) -> float:
    """Season/occasion flexibility — balanced formulas score high, extreme profiles score low.
    
    10 stars = works year-round, day/night, casual/formal
    5 stars = seasonal/occasional
    0 stars = extremely niche timing
    """
    # Check character balance (coefficient of variation)
    dims = [character_radar.get(d, 0) for d in DIMENSIONS if character_radar.get(d, 0) > 0]
    if len(dims) < 3:
        # Too few dimensions = not versatile
        return 3.0
    
    mean_dim = sum(dims) / len(dims)
    if mean_dim < 0.1:
        return 5.0
    cv = (sum((d - mean_dim)**2 for d in dims) / len(dims))**0.5 / mean_dim

    # Low CV = balanced = versatile
    versatility_score = 10.0 - (cv * 4.0)  # penalize high variation
    
    # Bonus for having moderate everything (not extreme in any direction)
    extremes = sum(1 for d in dims if d > 7.0 or d < 0.5)
    versatility_score -= extremes * 0.8
    
    # Bonus for freshness (day wearability) + warmth (night wearability)
    freshness = character_radar.get("freshness", 0)
    warmth = character_radar.get("warmth", 0)
    if freshness > 2.0 and warmth > 2.0:
        versatility_score += 1.5  # day + night capable
    
    return max(0.0, min(10.0, versatility_score))


def rate_originality(fv: FormulaVector, character_radar: Dict[str, float]) -> float:
    """Uniqueness and creativity — rare materials, unusual combinations.
    
    10 stars = groundbreaking, never-smelled-before
    5 stars = competent but familiar
    0 stars = clone/generic
    """
    # Materials indicating originality
    originality_materials = {
        "DBCA": 2.0,  # Unique gardenia-rose character
        "Paradisamide": 1.5,  # Transparent muguet
        "Scentenal": 2.5,  # Metallic-green ozone (unusual)
        "Dynascone": 2.0,  # Powerful green-galbanum (uncommon)
        "Cyclamen Aldehyde": 1.8,  # Metallic-green floral
        "IBQ": 2.5,  # Dirty leather (niche)
        "Ethyl Safranate": 1.5,  # Saffron note (uncommon)
        "Suederal": 1.5,  # Suede leather without smoke
        "Parmavert": 1.0,  # Green violet-leaf
        "Leafovert": 1.0,  # Cut-grass
        "Styrax FTEC": 1.0,  # Balsamic-leather smoke
        "Cedrat FCF Sicilian": 1.0,  # Bitter citron vs generic bergamot
        "Blood Orange Sicilian": 0.8,
        "Methyl Pamplemousse": 1.2,  # Grapefruit-rhubarb
        "Ultralia": 1.5,  # Ghost iris
        "Kephalis": 1.0,  # Woody-amber structure
    }
    
    originality_score = 0.0
    eff = fv.effective_ingredients()
    for mat, pct in eff.items():
        if is_blocked_chemical(mat):
            continue
        if mat in originality_materials:
            # Weight by active percentage (more impactful if high dosing)
            contribution = originality_materials[mat] * (pct / 100.0) * 20
            originality_score += contribution
    
    # Bonus for unusual character combinations (e.g., smoky + fresh, animalic + powdery)
    smoky = character_radar.get("smoky", 0)
    fresh = character_radar.get("freshness", 0)
    if smoky > 2.0 and fresh > 2.0:
        originality_score += 1.5  # smoke + freshness is unusual
    
    animalic = character_radar.get("animalic", 0)
    powdery = character_radar.get("powdery", 0)
    if animalic > 1.5 and powdery > 2.5:
        originality_score += 1.2  # animalic + powdery = vintage chypre feel
    
    # Penalty for generic materials dominating
    generic_materials = ["Bergamot FCF", "D-Limonene", "Iso E Super", "Hedione"]
    generic_pct = sum(eff.get(m, 0) for m in generic_materials)
    if generic_pct > 50:
        originality_score -= 3.0  # heavily generic
    elif generic_pct > 30:
        originality_score -= 1.5

    # Ingredient count diversity bonus: more unique materials = more original
    n_ingredients = len(eff)
    if n_ingredients >= 12:
        originality_score += 1.0
    elif n_ingredients <= 5:
        originality_score -= 1.0

    # Baseline 3.0 so full 0-10 range is used (generic scores ~1-3, creative scores 7-10)
    return max(0.0, min(10.0, 3.0 + originality_score))


def rate_sophistication(fv: FormulaVector, character_radar: Dict[str, float],
                         theory_score: float, complexity_score: float) -> float:
    """Refinement and artistry — uses complexity + theory scores as inputs.
    
    10 stars = masterpiece-level perfumer work
    5 stars = competent commercial
    0 stars = amateur hour
    """
    # Sophistication: theory compliance + complexity + character depth
    # Use steeper curve: only high scores yield high sophistication
    theory_factor = max(0, (theory_score - 50) / 50.0) * 3.0  # 0-3 (only >50 contributes)
    complexity_factor = max(0, (complexity_score - 50) / 50.0) * 2.5  # 0-2.5

    # Character depth: sophistication = multi-faceted but harmonious
    dims = [character_radar.get(d, 0) for d in DIMENSIONS if character_radar.get(d, 0) > 0.5]
    n_dims = len(dims)
    if n_dims >= 6:
        depth_score = 2.0  # rich palette
    elif n_dims >= 4:
        depth_score = 1.2  # good depth
    elif n_dims >= 2:
        depth_score = 0.5
    else:
        depth_score = -1.0  # flat = unsophisticated

    # Harmony: low variance across active dimensions = refined
    if dims:
        avg_dim = sum(dims) / len(dims)
        variance = sum((d - avg_dim) ** 2 for d in dims) / len(dims)
        harmony_bonus = max(0, 1.0 - variance * 0.3)  # 0-1
    else:
        harmony_bonus = 0

    # Materials indicating sophistication (expensive, rare, precise dosing)
    soph_materials = {
        "Javanol": 0.8, "Evernyl": 0.7,
        "Orris FTEC": 1.0, "I-IRIS FTEC": 1.0,
        "Ambrox Super": 0.5, "Ambrox": 0.5,
        "Habanolide": 0.6, "Timberol": 0.5,
        "Orris Butter Absolute": 1.0, "Rose Absolute": 0.7,
        "Jasmine Absolute": 0.7, "Oud Oil": 0.8,
    }
    eff = fv.effective_ingredients()
    soph_mat_bonus = sum(
        0.3 for m in eff
        if m in soph_materials and eff[m] > 2.0 and not is_blocked_chemical(m)
    )

    score = theory_factor + complexity_factor + depth_score + harmony_bonus + soph_mat_bonus
    return max(0.0, min(10.0, score))


def rate_signature_potential(fv: FormulaVector, character_radar: Dict[str, float],
                               originality: float) -> float:
    """Memorability and distinctiveness — ability to become someone's signature scent.
    
    10 stars = "that's YOUR scent" identity-building
    5 stars = pleasant but forgettable
    0 stars = generic mall spray
    """
    # Signature potential = originality + character strength (not generic)
    sig_score = originality * 0.5  # originality is base component

    # Check for dominant character (people remember specific traits)
    # Radar scale is 0-10 but typical values 0-5; threshold 2.5 = noticeable
    dominant_dims = [d for d in DIMENSIONS if character_radar.get(d, 0) > 2.5]
    if len(dominant_dims) >= 2:
        sig_score += 2.5  # multi-faceted identity
    elif len(dominant_dims) == 1:
        sig_score += 1.5  # single strong anchor
    else:
        sig_score -= 1.0  # too flat = forgettable

    # Character intensity: max dimension value contributes to memorability
    max_dim = max(character_radar.values()) if character_radar else 0
    sig_score += min(max_dim * 0.3, 1.5)  # up to 1.5 for strong character

    # Materials with high signature potential (distinctive, not ubiquitous)
    signature_materials = {
        "Ambrox Super": 1.5, "Ambrox": 1.5,
        "Iso E Super": 1.2,
        "Javanol": 1.0, "Cashmeran": 1.0,
        "IBQ": 2.0, "DBCA": 1.5,
        "Evernyl": 1.2, "Styrax FTEC": 1.5,
        "Oud Oil": 1.5, "Orris Butter Absolute": 1.5,
        "Skatole": 1.0, "Civet Reconstitution": 1.0,
    }
    eff = fv.effective_ingredients()
    for mat, weight in signature_materials.items():
        if is_blocked_chemical(mat):
            continue
        if eff.get(mat, 0) > 3.0:  # >3% active = meaningful presence
            sig_score += weight * 0.5

    return max(0.0, min(10.0, sig_score))


def rate_mass_appeal(fv: FormulaVector, character_radar: Dict[str, float],
                      wearability: float) -> float:
    """Compliment factor and crowd-pleasing — vs niche/acquired taste.
    
    10 stars = everyone loves it
    5 stars = divisive
    0 stars = only perfume nerds appreciate
    """
    # Mass appeal = high wearability + sweet/fresh/floral (safe notes)
    appeal_score = wearability * 0.5  # wearability is 50% of appeal
    
    # Safe, crowd-pleasing characteristics
    sweetness = character_radar.get("sweetness", 0)
    freshness = character_radar.get("freshness", 0)
    floral = character_radar.get("floral", 0)
    creamy = character_radar.get("creamy", 0)
    
    safe_score = (sweetness * 0.4 + freshness * 0.3 + floral * 0.2 + creamy * 0.1)
    appeal_score += safe_score
    
    # Penalties for polarizing notes
    animalic = character_radar.get("animalic", 0)
    smoky = character_radar.get("smoky", 0)
    green = character_radar.get("green", 0)
    
    polarizing_penalty = animalic * 1.5 + smoky * 1.2 + green * 0.5
    appeal_score -= polarizing_penalty
    
    # Penalty for too complex (mass market prefers simple)
    dims_count = len([d for d in DIMENSIONS if character_radar.get(d, 0) > 1.0])
    if dims_count > 6:
        appeal_score -= 1.0  # too complex for mass market
    
    return max(0.0, min(10.0, appeal_score))  # full 0-10 range


def rate_gender_versatility(character_radar: Dict[str, float]) -> float:
    """Unisex rating — how well it wears across gender spectrum.
    
    10 stars = perfectly unisex
    5 stars = leans masc/fem but wearable
    0 stars = strongly gendered
    """
    # Strongly masculine indicators
    woody = character_radar.get("woody", 0)
    spicy = character_radar.get("spicy", 0)
    smoky = character_radar.get("smoky", 0)
    masc_score = woody * 0.5 + spicy * 0.3 + smoky * 0.2
    
    # Strongly feminine indicators
    floral = character_radar.get("floral", 0)
    powdery = character_radar.get("powdery", 0)
    sweetness = character_radar.get("sweetness", 0)
    fem_score = floral * 0.5 + powdery * 0.3 + sweetness * 0.2
    
    # Neutral/unisex indicators
    freshness = character_radar.get("freshness", 0)
    creamy = character_radar.get("creamy", 0)
    radiance = character_radar.get("radiance", 0)
    neutral_score = freshness * 0.4 + creamy * 0.3 + radiance * 0.3
    
    # Perfect unisex = balanced masc + fem, or high neutral
    # With radar 0-5, weighted scores typically 0-2.5
    gender_diff = abs(masc_score - fem_score)
    total_gendering = masc_score + fem_score

    if gender_diff < 0.5 and total_gendering < 1.5:
        # Low gendering overall = truly neutral
        versatility = 8.0 + neutral_score * 0.3
    elif gender_diff < 0.5:
        # Balanced but present = unisex with character
        versatility = 7.0 + neutral_score * 0.3
    elif gender_diff < 1.0:
        # Slight lean
        versatility = 5.5 + neutral_score * 0.3
    elif gender_diff < 1.5:
        # Moderate lean
        versatility = 4.0 + neutral_score * 0.3
    else:
        # Strong gendering
        versatility = 2.0 + neutral_score * 0.4
    
    return max(0.0, min(10.0, versatility))


def rate_age_range(character_radar: Dict[str, float]) -> float:
    """Broad age appropriateness — universal vs age-specific.
    
    10 stars = 18-80 years, anyone can wear
    5 stars = specific age bracket (e.g., 25-40)
    0 stars = very age-specific (teen/elderly only)
    """
    # Universal notes (any age)
    freshness = character_radar.get("freshness", 0)
    creamy = character_radar.get("creamy", 0)
    universal_score = freshness * 0.5 + creamy * 0.3
    
    # Mature/sophisticated notes (skew older)
    woody = character_radar.get("woody", 0)
    powdery = character_radar.get("powdery", 0)
    smoky = character_radar.get("smoky", 0)
    mature_score = woody * 0.4 + powdery * 0.3 + smoky * 0.3
    
    # Youthful notes (skew younger)
    sweetness = character_radar.get("sweetness", 0)
    floral = character_radar.get("floral", 0)
    youthful_score = sweetness * 0.5 + floral * 0.3
    
    # Balanced age profile = high universal + moderate mature/youthful
    # Radar values typically 0-5, so use proportional thresholds
    age_imbalance = abs(mature_score - youthful_score)
    if mature_score > 2.5 and youthful_score < 0.8:
        # Strongly mature-skewed (old-fashioned)
        age_score = 3.0 + universal_score * 0.3
    elif youthful_score > 2.5 and mature_score < 0.8:
        # Strongly young-skewed (teen/candy)
        age_score = 3.5 + universal_score * 0.3
    elif age_imbalance > 1.5:
        # Moderate skew
        age_score = 5.0 + universal_score * 0.4
    else:
        # Balanced or universal
        age_score = 6.0 + universal_score * 0.5

    return max(0.0, min(10.0, age_score))


def rate_value_for_money(cost_score: float, quality_scores: Dict[str, float]) -> float:
    """Quality-to-cost ratio — bang for buck.
    
    10 stars = exceptional value
    5 stars = fair price
    0 stars = overpriced
    
    Args:
        cost_score: 0-100 cost score (lower = more expensive)
        quality_scores: dict of all other scores (longevity, sillage, etc.)
    """
    # Average quality score (excluding cost)
    quality_axes = ["longevity", "sillage", "balance", "theory", "radiance",
                    "texture", "complexity", "character_balance", "synergy"]
    quality_vals = [quality_scores.get(ax, 0) for ax in quality_axes if ax in quality_scores]
    avg_quality = sum(quality_vals) / len(quality_vals) if quality_vals else 50.0

    # Continuous value: weighted sum of quality and affordability
    # cost_score 0-100 (100=cheap), avg_quality 0-100 (100=excellent)
    cost_norm = cost_score / 100.0
    quality_norm = avg_quality / 100.0

    # Value = quality weighted more, with cost as multiplier
    # A $5 mediocre fragrance isn't great value; a $50 masterpiece is.
    # quality drives the score, cost adjusts it up/down
    base_value = quality_norm * 6.0  # 0-6 from quality alone
    cost_modifier = (cost_norm - 0.5) * 4.0  # -2 to +2 from cost
    value = base_value + cost_modifier

    return max(0.0, min(10.0, value))


def rate_formula_elegance(fv: FormulaVector) -> float:
    """Structural elegance of the formula — proportion rationality, fixative anchoring.

    Replaces the old bottle_presentation = 7.0 constant with an actually computed metric.

    10 stars = every ingredient earns its place, solid fixative base, no waste
    5 stars = some filler, weak base, or poor proportions
    0 stars = random ingredient dump
    """
    from engine.optimizer.models import classify_note

    eff = fv.effective_ingredients()
    n_ingredients = len(eff)
    total_pct = sum(eff.values()) or 1.0

    score = 5.0  # neutral baseline

    # 1. Ingredient count efficiency (sweet spot 8-15)
    if 8 <= n_ingredients <= 15:
        score += 1.5  # well-sized formula
    elif 6 <= n_ingredients <= 18:
        score += 0.5  # acceptable
    elif n_ingredients < 4:
        score -= 2.0  # too sparse
    elif n_ingredients > 20:
        score -= 1.0  # bloated

    # 2. No decorative trace ingredients (<0.5% active, doesn't contribute)
    trace_count = sum(1 for pct in eff.values() if pct / total_pct * 100 < 0.3)
    if trace_count == 0:
        score += 1.0  # every ingredient pulls weight
    else:
        score -= trace_count * 0.3  # penalty per decorative trace

    # 3. Fixative anchoring — base notes should be ≥25% of formula
    note_dist = fv.note_distribution()
    base_pct = note_dist.get("base", 0)
    if base_pct >= 30:
        score += 1.5  # solid fixative foundation
    elif base_pct >= 20:
        score += 0.5  # adequate
    elif base_pct < 10:
        score -= 1.5  # will evaporate fast

    # 4. No single ingredient dominates >45% (over-reliance)
    max_pct = max(eff.values()) / total_pct * 100 if eff else 0
    if max_pct > 45:
        score -= 1.5  # single-ingredient dominance
    elif max_pct > 35:
        score -= 0.5

    # 5. Proportion spread — Gini-like check (not all at same level)
    if n_ingredients >= 4:
        sorted_pcts = sorted(eff.values(), reverse=True)
        top_half = sum(sorted_pcts[:n_ingredients // 2])
        total = sum(sorted_pcts) or 1.0
        concentration_ratio = top_half / total
        # Good range: 0.5-0.8 (some hierarchy but not all in one ingredient)
        if 0.5 <= concentration_ratio <= 0.8:
            score += 1.0
        elif concentration_ratio > 0.9:
            score -= 0.5  # too top-heavy

    return max(0.0, min(10.0, score))


def compute_star_ratings(fv: FormulaVector, scores: Dict[str, float],
                          character_radar: Dict[str, float]) -> StarRatings:
    """Compute all 10 star ratings for a formula."""
    wearability = rate_wearability(fv, character_radar)
    versatility = rate_versatility(fv, character_radar)
    originality = rate_originality(fv, character_radar)
    sophistication = rate_sophistication(fv, character_radar, scores["theory"], scores["complexity"])
    signature_potential = rate_signature_potential(fv, character_radar, originality)
    mass_appeal = rate_mass_appeal(fv, character_radar, wearability)
    gender_versatility = rate_gender_versatility(character_radar)
    age_range = rate_age_range(character_radar)
    formula_elegance = rate_formula_elegance(fv)
    value_for_money = rate_value_for_money(scores["cost"], scores)
    
    return StarRatings(
        wearability=wearability,
        versatility=versatility,
        originality=originality,
        sophistication=sophistication,
        signature_potential=signature_potential,
        mass_appeal=mass_appeal,
        gender_versatility=gender_versatility,
        age_range=age_range,
        formula_elegance=formula_elegance,
        value_for_money=value_for_money,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE RATING REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def format_star_rating(stars: float) -> str:
    """Format a 0-10 star rating with visual stars (★☆)."""
    full = int(stars)
    half = 1 if (stars - full) >= 0.5 else 0
    empty = 10 - full - half
    
    visual = "★" * full + ("⯨" * half) + ("☆" * empty)
    return f"{visual} {stars:.1f}/10"


def format_comprehensive_report(formula_name: str, fv: FormulaVector,
                                  scores: Dict[str, float], stars: StarRatings,
                                  character_radar: Dict[str, float]) -> str:
    """Generate comprehensive rating report with both star ratings and scores."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"  {formula_name}  ")
    lines.append("=" * 80)
    
    # SECTION 1: 10-Star Ratings (Consumer/Wearability Focus)
    lines.append("\n  ★ 10-STAR RATINGS — Wearability & Consumer Appeal")
    lines.append("  " + "-" * 76)
    star_dict = stars.as_dict()
    for key, value in star_dict.items():
        key_display = key.replace("_", " ").title()
        lines.append(f"    {key_display:<25s} {format_star_rating(value)}")
    lines.append(f"\n    {'OVERALL STAR RATING':<25s} {format_star_rating(stars.average())}")
    
    # SECTION 2: 0-100 Scores (Technical/Compositional Focus)
    lines.append("\n  ▣ 0-100 SCORES — Technical Composition Metrics")
    lines.append("  " + "-" * 76)
    score_axes = ["longevity", "sillage", "balance", "theory", "radiance",
                  "texture", "complexity", "character_balance", "synergy", "cost"]
    for ax in score_axes:
        if ax in scores:
            score = scores[ax]
            bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
            lines.append(f"    {ax:<20s} {bar} {score:5.1f}/100")
    
    geom = scores.get("geometric_total", 0)
    arith = scores.get("arithmetic_total", 0)
    lines.append(f"\n    {'Geometric Mean':<20s} {'▓' * int(geom/5)}{'░' * (20-int(geom/5))} {geom:5.1f}/100 (primary)")
    lines.append(f"    {'Arithmetic Mean':<20s} {'▓' * int(arith/5)}{'░' * (20-int(arith/5))} {arith:5.1f}/100 (legacy)")
    
    # SECTION 3: Character Radar (12 Dimensions)
    lines.append("\n  ◉ CHARACTER RADAR — 12 Olfactive Dimensions (0-10)")
    lines.append("  " + "-" * 76)
    for dim in DIMENSIONS:
        val = character_radar.get(dim, 0)
        bar = "▓" * int(val) + "░" * (10 - int(val))
        lines.append(f"    {dim:<15s} {bar} {val:4.1f}/10")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# RATING IMPLEMENTATION COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

def compare_rating_systems() -> str:
    """Generate comparison document explaining both rating systems."""
    doc = []
    doc.append("# Dual Rating System Comparison — Stars vs Scores\n")
    doc.append("**Implemented:** March 28, 2026  ")
    doc.append("**Purpose:** Comprehensive formula evaluation using complementary methodologies\n")
    doc.append("---\n")
    
    doc.append("## System Overview\n")
    doc.append("The perfume evaluation framework uses **two parallel rating systems**, each measuring different aspects:\n")
    
    doc.append("### 1. ★ 10-Star Ratings — Wearability & Consumer Appeal")
    doc.append("**Scale:** 0.0–10.0 stars (★★★★★★★★★★)  ")
    doc.append("**Focus:** Subjective wearability, versatility, originality  ")
    doc.append("**Target audience:** Consumers, fragrance enthusiasts  ")
    doc.append("**Question answered:** *\"How will this perfume perform in real-world use?\"*\n")
    
    doc.append("**Characteristics evaluated:**")
    doc.append("- **Wearability** — Comfort, not challenging, daily wearability")
    doc.append("- **Versatility** — Season/occasion flexibility, day-to-night capability")
    doc.append("- **Originality** — Uniqueness, creativity, non-generic character")
    doc.append("- **Sophistication** — Refinement, artistry, perfumer skill level")
    doc.append("- **Signature Potential** — Memorability, identity-building capability")
    doc.append("- **Mass Appeal** — Compliment factor, crowd-pleasing (vs niche)")
    doc.append("- **Gender Versatility** — Unisex rating, not polarizing")
    doc.append("- **Age Range** — Broad age appropriateness (18-80 vs narrow)")
    doc.append("- **Formula Elegance** — Structural elegance, fixative anchoring, proportion rationality")
    doc.append("- **Value for Money** — Quality-to-cost ratio\n")
    
    doc.append("### 2. ▣ 0-100 Scores — Technical Composition Metrics")
    doc.append("**Scale:** 0–100 points  ")
    doc.append("**Focus:** Objective structural quality, compositional excellence  ")
    doc.append("**Target audience:** Perfumers, chemists, technicians  ")
    doc.append("**Question answered:** *\"How well is this formula constructed technically?\"*\n")
    
    doc.append("**Axes evaluated:**")
    doc.append("- **Longevity** — Duration on skin (VP, fixatives, tenacity)")
    doc.append("- **Sillage** — Diffusion, projection, radius")
    doc.append("- **Balance** — Top-to-heart-to-base ratio, structural harmony")
    doc.append("- **Theory** — Alignment with perfumery principles (pairing, synergy rules)")
    doc.append("- **Radiance** — Luminosity, halo effect (Hedione, Iso E, aldehydes)")
    doc.append("- **Texture** — Tactile diversity, layering, volume")
    doc.append("- **Complexity** — Structural diversity (dimensions, roles, characters)")
    doc.append("- **Character Balance** — Olfactive profile evenness (dimension CV)")
    doc.append("- **Synergy** — Ingredient pairing effectiveness")
    doc.append("- **Cost** — Material expense (inversely scored)\n")
    
    doc.append("---\n")
    doc.append("## Key Differences\n")
    doc.append("| Aspect | ★ Star Ratings | ▣ Scores |")
    doc.append("|--------|---------------|----------|")
    doc.append("| **Objectivity** | Subjective (consumer experience) | Objective (measurable properties) |")
    doc.append("| **Calculation** | Heuristic, character-driven | Algorithmic, formula-vector-driven |")
    doc.append("| **Target User** | Buyers, wearers, enthusiasts | Formulators, perfumers, chemists |")
    doc.append("| **Question** | \"Will I like wearing this?\" | \"Is this well-constructed?\" |")
    doc.append("| **Examples** | Wearability, mass appeal, originality | Longevity, sillage, balance |")
    doc.append("| **Scoring Model** | Linear (0-10, higher = better) | Weighted mean (0-100, geometric) |")
    doc.append("| **Emphasis** | Real-world utility | Technical excellence |\n")
    
    doc.append("---\n")
    doc.append("## Why Both Systems?\n")
    doc.append("**Example scenario:** A formula could score 9★ wearability (easy, comfortable, crowd-pleasing) but only 60/100 balance (top-heavy structure). This tells us:\n")
    doc.append("- ✅ **For consumers:** Great daily wear, pleasant, versatile")
    doc.append("- ⚠️ **For perfumers:** Structural weakness, needs rebalancing\n")
    
    doc.append("Conversely, a formula might score 85/100 complexity (many dimensions, roles) but only 5★ wearability (challenging, polarizing). This means:\n")
    doc.append("- ⚠️ **For consumers:** Difficult, acquired taste, niche")
    doc.append("- ✅ **For perfumers:** Sophisticated construction, artistic achievement\n")
    
    doc.append("**Use cases:**")
    doc.append("- **Optimization:** Use **scores** to identify technical flaws (balance, longevity), use **stars** to predict market reception")
    doc.append("- **Consumer guidance:** Present **stars** for purchase decisions (\"9★ versatility = wear year-round\")")
    doc.append("- **Perfumer training:** Present **scores** for compositional learning (\"balance 26/100 = fix top-to-base ratio\")")
    doc.append("- **Product positioning:** High stars + high scores = luxury niche; high stars + low scores = mass market; low stars + high scores = artistic/challenging\n")
    
    doc.append("---\n")
    doc.append("## Implementation Notes\n")
    doc.append("- **Star ratings** computed from character radar + material analysis")
    doc.append("- **Scores** computed from FormulaVector properties + ingredient intelligence DB")
    doc.append("- **Both run in parallel** — no conflict, complementary perspectives")
    doc.append("- **Geometric mean** used for score composite (penalizes weaknesses)")
    doc.append("- **Arithmetic mean** used for star composite (balanced overview)\n")
    
    return "\n".join(doc)
