"""Eight-axis balance evaluation for fragrance formulas.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Evaluates a formula on eight orthogonal axes derived from the Formulation
Intelligence Database (Part III). Each axis produces a normalized 0-1 score
with a diagnostic status.

Axes:
  1. Volatility (Evaporation Schedule)
  2. Hedonic Contrast (Beautiful + Interesting + Challenging)
  3. OAV Contrast (Depth Through Dynamic Range)
  4. Transparency vs Opacity
  5. Diffusion Layers
  6. Material Class Distribution
  7. Cross-Family Blending Compatibility
  8. Maceration as Active Construction
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from ._shared_types import (
    CROSS_FAMILY_COMPATIBILITY,
    HEDONIC_TARGETS,
    MATERIAL_CLASS_DISTRIBUTION,
    OPTIMAL_LOG_OAV_SD,
    PYRAMID_OAV_RATIOS,
    BalanceReport,
    ConcentrationBracket,
    DiffusionLayer,
    FragranceFamily,
    HedonicCategory,
    MarketSegment,
)

# ---------------------------------------------------------------------------
# Axis 1: Volatility Balance (Evaporation Schedule)
# ---------------------------------------------------------------------------

def evaluate_volatility_balance(
    top_oav_total: float,
    heart_oav_total: float,
    base_oav_total: float,
    bracket: ConcentrationBracket,
) -> BalanceReport:
    """Check top:heart:base OAV ratio against optimal pyramid targets."""
    ratios = PYRAMID_OAV_RATIOS[bracket]
    total = top_oav_total + heart_oav_total + base_oav_total
    if total == 0:
        return BalanceReport("volatility_balance", 0.0, (0, 100), "critical", "No OAV detected")

    t_pct = top_oav_total / total * 100
    h_pct = heart_oav_total / total * 100
    b_pct = base_oav_total / total * 100

    t_deviation = abs(t_pct - ratios[0]) / max(ratios[0], 1)
    h_deviation = abs(h_pct - ratios[1]) / max(ratios[1], 1)
    b_deviation = abs(b_pct - ratios[2]) / max(ratios[2], 1)

    # Score: 1.0 = perfect match, decays with deviation
    score = max(0.0, 1.0 - (t_deviation + h_deviation + b_deviation) * 0.5)

    if score >= 0.85:
        status = "optimal"
    elif score >= 0.60:
        status = "acceptable"
    elif score >= 0.30:
        status = "needs_improvement"
    else:
        status = "critical"

    details = (
        f"T:{t_pct:.0f}% H:{h_pct:.0f}% B:{b_pct:.0f}% "
        f"(target {ratios[0]:.0f}:{ratios[1]:.0f}:{ratios[2]:.0f} for {bracket.value})"
    )
    return BalanceReport("volatility_balance", score, (0, 100), status, details)


# ---------------------------------------------------------------------------
# Axis 2: Hedonic Contrast
# ---------------------------------------------------------------------------

def evaluate_hedonic_contrast(
    hedonic_by_material: Mapping[str, tuple[float, float]],  # name → (oav_contribution, hedonic_score)
    segment: MarketSegment,
) -> BalanceReport:
    """Evaluate hedonic category distribution against market segment targets."""
    targets = HEDONIC_TARGETS[segment]
    total_oav = sum(o for o, _ in hedonic_by_material.values())
    if total_oav == 0:
        return BalanceReport("hedonic_contrast", 0.0, None, "critical", "No hedonic-bearing materials")

    beautiful = sum(o for (o, h) in hedonic_by_material.values() if h >= 3.0)
    interesting = sum(o for (o, h) in hedonic_by_material.values() if 1.0 <= h < 3.0)
    challenging = sum(o for (o, h) in hedonic_by_material.values() if -2.0 <= h < 1.0)

    b_frac = beautiful / total_oav
    i_frac = interesting / total_oav
    c_frac = challenging / total_oav

    b_score = min(b_frac / targets[HedonicCategory.BEAUTIFUL], 1.0) if targets[HedonicCategory.BEAUTIFUL] > 0 else 1.0
    i_score = min(i_frac / max(targets[HedonicCategory.INTERESTING], 0.01), 1.0) if targets[HedonicCategory.INTERESTING] > 0 else 1.0
    # Challenging should be below target
    c_score = 1.0 - min(c_frac / max(targets[HedonicCategory.CHALLENGING], 0.01), 1.0)

    score = (b_score * 0.5 + i_score * 0.3 + c_score * 0.2)

    if score >= 0.80:
        status = "optimal"
    elif score >= 0.55:
        status = "acceptable"
    elif score >= 0.30:
        status = "needs_improvement"
    else:
        status = "critical"

    details = (
        f"Beautiful:{b_frac:.0%} (target>{targets[HedonicCategory.BEAUTIFUL]:.0%}), "
        f"Interesting:{i_frac:.0%} (target>{targets[HedonicCategory.INTERESTING]:.0%}), "
        f"Challenging:{c_frac:.0%} (target<{targets[HedonicCategory.CHALLENGING]:.0%})"
    )
    return BalanceReport("hedonic_contrast", score, None, status, details)


# ---------------------------------------------------------------------------
# Axis 3: OAV Contrast (Depth Through Dynamic Range)
# ---------------------------------------------------------------------------

def evaluate_oav_contrast(
    oav_values: Sequence[float],
) -> BalanceReport:
    """Evaluate the log(OAV) standard deviation for optimal dynamic range.

    Optimal σ_log(OAV) ≈ 0.8–1.2. Values outside this range indicate
    either flat (too uniform) or overly spiky OAV distribution.
    """
    if len(oav_values) < 3:
        return BalanceReport("oav_contrast", 0.5, OPTIMAL_LOG_OAV_SD, "acceptable", "Too few materials to assess OAV contrast")

    # Filter to materials with OAV > 0.01 (below detection adds noise)
    positive_oavs = [o for o in oav_values if o > 0.01]
    if len(positive_oavs) < 3:
        return BalanceReport("oav_contrast", 0.3, OPTIMAL_LOG_OAV_SD, "needs_improvement", "Too few materials with perceptible OAV")

    log_oavs = [math.log10(o) for o in positive_oavs]
    mean_log = sum(log_oavs) / len(log_oavs)
    variance = sum((lo - mean_log) ** 2 for lo in log_oavs) / len(log_oavs)
    sigma = math.sqrt(variance)

    lo, hi = OPTIMAL_LOG_OAV_SD
    if lo <= sigma <= hi:
        status = "optimal"
        score = 1.0
    elif sigma < lo:
        # Too flat
        score = max(0.0, sigma / lo)
        status = "needs_improvement" if score < 0.5 else "acceptable"
    else:
        # Too spiky
        excess = (sigma - hi) / hi
        score = max(0.0, 1.0 - excess)
        status = "needs_improvement" if score < 0.5 else "acceptable"

    if score < 0.3:
        status = "critical"

    details = f"σ_log(OAV) = {sigma:.2f} (optimal {lo:.1f}–{hi:.1f})"
    return BalanceReport("oav_contrast", score, OPTIMAL_LOG_OAV_SD, status, details)


# ---------------------------------------------------------------------------
# Axis 4: Transparency vs Opacity
# ---------------------------------------------------------------------------

# Materials classified as transparent vs opaque
_TRANSPARENT_MATERIALS: frozenset[str] = frozenset({
    "hedione", "hedione hc", "dihydromyrcenol", "calone", "habanolide",
    "floralozone", "ultralia", "ambrettolide", "ethylene brassylate",
    "romandolide", "linalool", "linalyl acetate", "benzyl acetate",
})

_OPAQUE_MATERIALS: frozenset[str] = frozenset({
    "patchouli eo", "labdanum", "vanillin", "benzoin", "oakmoss absolute",
    "benzyl benzoate", "castoreum", "vetiver eo", "coumarin",
    "cashmeran", "galaxolide", "iso e super",
})


def evaluate_transparency_opacity(
    materials: Mapping[str, float],  # name → mass fraction
    bracket: ConcentrationBracket,
) -> BalanceReport:
    """Evaluate transparency/opacity ratio based on material classification.

    Lower concentration brackets (EdC/EdT) need MORE opaque materials
    to achieve equivalent perceived presence.
    """
    transparent_mass = 0.0
    opaque_mass = 0.0
    sum(materials.values())

    for name, mass in materials.items():
        key = name.lower()
        if key in _TRANSPARENT_MATERIALS:
            transparent_mass += mass
        elif key in _OPAQUE_MATERIALS:
            opaque_mass += mass

    total_known = transparent_mass + opaque_mass
    if total_known == 0:
        return BalanceReport("transparency_opacity", 0.5, None, "acceptable", "No classified materials found")

    t_frac = transparent_mass / total_known
    o_frac = opaque_mass / total_known

    # Target transparency fractions by bracket (EdT/EdP 60-70%, Classic 20-30%)
    targets: dict[ConcentrationBracket, tuple[float, float]] = {
        ConcentrationBracket.EDC: (0.55, 0.75),
        ConcentrationBracket.EDT: (0.60, 0.70),
        ConcentrationBracket.EDP: (0.55, 0.70),
        ConcentrationBracket.EXTRAIT: (0.40, 0.60),
        ConcentrationBracket.BODY_SPRAY: (0.50, 0.70),
    }
    lo, hi = targets.get(bracket, (0.50, 0.70))

    if lo <= t_frac <= hi:
        score = 1.0
        status = "optimal"
    else:
        score = max(0.0, 1.0 - abs(t_frac - (lo + hi) / 2) / ((hi - lo) / 2))
        status = "acceptable" if score >= 0.5 else "needs_improvement"

    details = f"Transparent:{t_frac:.0%} Opaque:{o_frac:.0%} (target {lo:.0%}-{hi:.0%} for {bracket.value})"
    return BalanceReport("transparency_opacity", score, (lo, hi), status, details)


# ---------------------------------------------------------------------------
# Axis 5: Diffusion Layers
# ---------------------------------------------------------------------------

_DIFFUSION_LAYER_MATERIALS: dict[DiffusionLayer, frozenset[str]] = {
    DiffusionLayer.INTIMATE: frozenset({
        "vetiver eo", "sandalwood eo", "javanol", "cashmeran", "castoreum", "indole",
    }),
    DiffusionLayer.PERSONAL: frozenset({
        "pea", "phenylethyl alcohol", "geraniol", "benzyl acetate", "coumarin",
        "linalool", "benzyl salicylate",
    }),
    DiffusionLayer.SILLAGE: frozenset({
        "hedione", "iso e super", "calone", "c10 aldehyde", "c11 aldehyde",
    }),
    DiffusionLayer.AMBIENT: frozenset({
        "hedione hc", "ambroxan", "dihydromyrcenol", "c12 mna",
    }),
}


def evaluate_diffusion_layers(
    materials: Mapping[str, float],  # name → OAV contribution
) -> BalanceReport:
    """Check that all diffusion layers are represented.

    Critical rule: the intimate layer MUST be present or the fragrance
    feels "hollow" up close.
    """
    layer_presence: dict[DiffusionLayer, float] = {layer: 0.0 for layer in DiffusionLayer}

    for name, oav in materials.items():
        key = name.lower()
        for layer, mats in _DIFFUSION_LAYER_MATERIALS.items():
            if key in mats:
                layer_presence[layer] += oav

    # Check each layer
    checks = {
        DiffusionLayer.INTIMATE: (layer_presence[DiffusionLayer.INTIMATE] > 0, "Critical — no intimate layer"),
        DiffusionLayer.PERSONAL: (True, ""),  # usually present
        DiffusionLayer.SILLAGE: (layer_presence[DiffusionLayer.SILLAGE] > 0, "Limited projection"),
        DiffusionLayer.AMBIENT: (True, ""),  # optional
    }

    n_ok = sum(1 for ok, _ in checks.values() if ok)
    sum(1 for ok, msg in checks.values() if not ok)

    score = n_ok / len(checks)

    if not checks[DiffusionLayer.INTIMATE][0]:
        status = "critical"
        details = "Missing intimate layer — fragrance will feel hollow up close"
    elif score >= 0.9:
        status = "optimal"
        details = "All diffusion layers present"
    elif score >= 0.6:
        status = "acceptable"
        missing = [l.value for l, (ok, _) in checks.items() if not ok]
        details = f"Missing diffusion layers: {', '.join(missing)}"
    else:
        status = "needs_improvement"
        details = "Multiple diffusion layers absent"

    return BalanceReport("diffusion_layers", score, None, status, details)


# ---------------------------------------------------------------------------
# Axis 6: Material Class Distribution
# ---------------------------------------------------------------------------

# Coarse material class mapping (used when detailed profiles unavailable)
_MATERIAL_CLASS_MAP: dict[str, str] = {
    # Florals
    "hedione": "florals", "hedione hc": "florals", "pea": "florals",
    "geraniol": "florals", "citronellol": "florals", "linalool": "florals",
    "benzyl acetate": "florals", "rose absolute": "florals",
    "jasmine absolute": "florals", "ylang ylang eo": "florals",
    "phenylethyl alcohol": "florals", "rhodinol": "florals",
    # Woods
    "iso e super": "woods", "javanol": "woods", "cedarwood eo": "woods",
    "patchouli eo": "woods", "clearwood": "woods", "ambroxan": "woods",
    "vetiver eo": "woods", "sandalwood eo": "woods", "bacdanol": "woods",
    "polysantol": "woods", "cashmeran": "woods",
    # Musks
    "galaxolide": "musks", "habanolide": "musks", "ambrettolide": "musks",
    "ethylene brassylate": "musks", "romandolide": "musks",
    "exaltolide": "musks", "muscone": "musks", "musk ketone": "musks",
    # Citrus
    "bergamot fcf": "citrus", "limonene": "citrus", "citral": "citrus",
    "lemon eo": "citrus", "orange eo": "citrus", "dihydromyrcenol": "citrus",
    "linalyl acetate": "citrus", "grapefruit eo": "citrus",
    # Fixatives
    "benzyl benzoate": "fixatives", "benzyl salicylate": "fixatives",
    "isopropyl myristate": "fixatives", "dpg": "fixatives",
    "triethyl citrate": "fixatives", "dep": "fixatives",
    # Animalic
    "indole": "animalic", "skatole": "animalic", "castoreum": "animalic",
    "civet": "animalic", "isobutyl quinoline": "animalic",
    # Resins
    "labdanum": "resins", "benzoin": "resins", "vanillin": "resins",
    "coumarin": "resins", "oakmoss absolute": "resins", "birch tar": "resins",
    "styrax": "resins", "tolu balsam": "resins", "ethyl maltol": "resins",
}


def evaluate_material_class_distribution(
    materials: Mapping[str, float],  # name → mass fraction
    family: FragranceFamily,
) -> BalanceReport:
    """Evaluate material class distribution against family archetype targets."""
    targets = MATERIAL_CLASS_DISTRIBUTION.get(family)
    if targets is None:
        return BalanceReport("material_class_distribution", 1.0, None, "optimal", f"No archetype defined for {family.value}")

    # Sum mass by class
    class_mass: dict[str, float] = {cls: 0.0 for cls in targets}
    unclassified: float = 0.0

    for name, mass in materials.items():
        key = name.lower()
        cls = _MATERIAL_CLASS_MAP.get(key)
        if cls:
            class_mass[cls] += mass
        else:
            unclassified += mass

    total = sum(materials.values())
    if total == 0:
        return BalanceReport("material_class_distribution", 0.0, None, "critical", "No materials present")

    # Check each class against target range
    class_checks = []
    for cls, (lo, hi) in targets.items():
        frac = class_mass[cls] / total
        ok = lo == 0 and frac == 0  # zero target, zero observed
        if not ok:
            ok = lo <= frac * 100 <= hi
        class_checks.append(ok)

    score = sum(class_checks) / len(class_checks)

    if score >= 0.85:
        status = "optimal"
    elif score >= 0.70:
        status = "acceptable"
    else:
        status = "needs_improvement"

    class_summary = ", ".join(
        f"{c}:{class_mass[c]/total*100:.0f}%"
        for c in sorted(targets) if class_mass[c] > 0
    )
    details = f"Class distribution: {class_summary}"
    return BalanceReport("material_class_distribution", score, None, status, details)


# ---------------------------------------------------------------------------
# Axis 7: Cross-Family Blending Compatibility
# ---------------------------------------------------------------------------

_CROSS_FAMILY_SCORES: dict[str, float] = {
    "high": 1.0,
    "medium": 0.65,
    "low": 0.30,
    "very_low": 0.10,
}


def evaluate_cross_family_compatibility(
    family_a: FragranceFamily,
    family_b: FragranceFamily,
) -> BalanceReport:
    """Evaluate compatibility between two fragrance families."""

    # Normalize key lookup (either direction)
    key = (family_a, family_b)
    compat = CROSS_FAMILY_COMPATIBILITY.get(key)
    if compat is None:
        compat = CROSS_FAMILY_COMPATIBILITY.get((family_b, family_a), "medium")

    score = _CROSS_FAMILY_SCORES.get(compat, 0.5)

    if score >= 0.80:
        status = "optimal"
    elif score >= 0.50:
        status = "acceptable"
    else:
        status = "needs_improvement"

    details = f"{family_a.value} + {family_b.value}: {compat} compatibility"
    return BalanceReport("cross_family_compatibility", score, None, status, details)


# ---------------------------------------------------------------------------
# Axis 8: Maceration
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MacerationRule:
    """Chemical change expected during maceration."""

    reaction: str
    reaction_type: str
    rate_at_25c: str
    t0_vs_t30_change: str
    mitigation: str


MACERATION_RULES: tuple[MacerationRule, ...] = (
    MacerationRule(
        "Acetal formation", "Aldehyde + ethanol", "Weeks–months",
        "Softening, less sharp, more rounded",
        "Dose aldehydes 30–50% higher at T=0",
    ),
    MacerationRule(
        "Schiff base", "Aldehyde + primary amine", "Days–weeks",
        "Brown-floral shift, color formation",
        "Never combine aldehyde + methyl anthranilate in same vessel",
    ),
    MacerationRule(
        "Ester hydrolysis", "Ester + water (pH < 5)", "Months",
        "Loss of fruity ester character",
        "Buffer to pH 5.5–7",
    ),
    MacerationRule(
        "Terpene autoxidation", "Limonene, pinenes + O2", "Weeks",
        "Rancid off-notes, phototoxic products",
        "BHT/tocopherol 0.01–0.05%, N2 headspace",
    ),
    MacerationRule(
        "Phenol oxidation", "Vanillin, eugenol, guaiacol + O2", "Weeks–months",
        "Darkening, color change",
        "pH < 7, antioxidant",
    ),
)


def evaluate_maceration_risks(
    contains_aldehydes: bool,
    contains_methyl_anthranilate: bool,
    contains_citrus_eos: bool,
    contains_esters: bool,
    contains_phenolics: bool,
) -> BalanceReport:
    """Evaluate maceration risks based on formula chemical composition.

    Detects incompatible pairings and recommends over-dosing strategies.
    """
    risks: list[str] = []
    severity: float = 0.0

    if contains_aldehydes and contains_methyl_anthranilate:
        risks.append("Schiff base risk: aldehyde + methyl anthranilate → brown-floral shift")
        severity += 0.5

    if contains_aldehydes:
        risks.append("Aldehydes present: dose 40–60% excess at T=0 for acetal softening")
        severity += 0.1

    if contains_citrus_eos:
        risks.append("Citrus EOs: add 20–30% excess; BHT 0.01–0.05% for limonene oxidation")
        severity += 0.15

    if contains_phenolics:
        risks.append("Phenolics present: antioxidant + pH < 7 to prevent darkening")
        severity += 0.1

    if not risks:
        score = 1.0
        status = "optimal"
        details = "No maceration risk factors detected"
    elif severity < 0.3:
        score = 0.7
        status = "acceptable"
        details = "; ".join(risks)
    elif severity < 0.6:
        score = 0.4
        status = "needs_improvement"
        details = "; ".join(risks)
    else:
        score = 0.2
        status = "critical"
        details = "; ".join(risks)

    return BalanceReport("maceration", score, None, status, details)


def get_balance_overdose_strategy(material_type: str) -> float:
    """Return recommended T=0 overdosing factor for maceration compensation.

    Args:
        material_type: "aldehyde", "citrus_eo", "ester", or "base"

    Returns:
        Multiplier for T=0 dose (e.g., 1.5 = dose 50% higher)
    """
    strategies = {
        "aldehyde": 1.5,    # 40–60% excess
        "citrus_eo": 1.25,  # 20–30% excess
        "ester": 1.0,       # no over-dose needed
        "base": 1.0,        # dose to target
    }
    return strategies.get(material_type, 1.0)


# ---------------------------------------------------------------------------
# Full balance evaluation
# ---------------------------------------------------------------------------

def evaluate_all_balances(
    top_oav: float,
    heart_oav: float,
    base_oav: float,
    bracket: ConcentrationBracket,
    hedonic_data: Mapping[str, tuple[float, float]],
    segment: MarketSegment,
    oav_values: Sequence[float],
    material_masses: Mapping[str, float],
    family: FragranceFamily,
    contains_aldehydes: bool = False,
    contains_ma: bool = False,  # methyl anthranilate
    contains_citrus: bool = False,
    contains_esters: bool = True,
    contains_phenolics: bool = False,
) -> tuple[BalanceReport, ...]:
    """Run all 8 balance axes on a formula and return reports."""
    return (
        evaluate_volatility_balance(top_oav, heart_oav, base_oav, bracket),
        evaluate_hedonic_contrast(hedonic_data, segment),
        evaluate_oav_contrast(oav_values),
        evaluate_transparency_opacity(material_masses, bracket),
        evaluate_diffusion_layers({name: hedonic_data[name][0] for name in material_masses if name in hedonic_data}),
        evaluate_material_class_distribution(material_masses, family),
        evaluate_cross_family_compatibility(family, family),  # self-check
        evaluate_maceration_risks(contains_aldehydes, contains_ma, contains_citrus, contains_esters, contains_phenolics),
    )
