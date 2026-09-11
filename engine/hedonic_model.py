"""Hedonic valence modelling — intrinsic pleasantness prediction.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm, ODT in ppm/ppb, OAV = C/ODT (dimensionless).
- Every perceptibility claim must be backed by OAV.

Odorant molecules have measurable hedonic valence (pleasantness)
that is partially universal across cultures. Khan et al. (2007)
demonstrated that molecular features (compact, high MW, fewer
functional groups = pleasant; small, polar, with S/N = unpleasant)
predict hedonic ratings with R² ≈ 0.55.

This module scores each material's hedonic contribution and the
formula's overall hedonic harmony — whether materials work together
to create a pleasant impression or clash hedonically.

Hedonic contrast (juxtaposing pleasant/unpleasant elements) is a
legitimate creative tool — Muscs Koublaï Khän (Lutens), Secretions
Magnifiques (ELDO) — but must be intentional, not accidental.

Sources:
  Khan et al. (2007) J Neurosci, 27(37), 10015-10023 — predicting odor pleasantness from structure
  Zarzo (2011) Sensors, 11(5), 5296-5322 — molecular descriptors and pleasantness
  Dravnieks (1985) Atlas of Odor Character Profiles — 146 odorant profiles
  Keller et al. (2007) Nature, 449(7161), 468-472 — OR7D4 individual variation
  Yeshurun & Sobel (2010) Annual Review Psych — perception of smell
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from engine.material_data_loader import load_engine_data as _load_engine_data

# ═══════════════════════════════════════════════════════════════════════════════
# Hedonic Valence Data
# Scale: -1.0 (maximally unpleasant) to +1.0 (maximally pleasant)
# Based on Khan (2007) PNAS model outputs, Dravnieks (1985) atlas values,
# and Arctander (1969) subjective descriptors cross-referenced
# ═══════════════════════════════════════════════════════════════════════════════

HEDONIC_VALENCE = _load_engine_data("hedonic_model", "HEDONIC_VALENCE")


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HedonicReport:
    """Hedonic valence analysis of a formula."""
    score: float                      # 0-100 hedonic score
    weighted_valence: float           # -1.0 to 1.0 weighted mean
    pleasantness_class: str           # "highly_pleasant", "pleasant", etc.
    hedonic_contrast: float           # 0-1 how much contrast between materials
    pleasant_fraction: float          # 0-1 fraction of mass that is pleasant
    unpleasant_materials: list[dict]  # materials with negative valence
    most_pleasant: list[dict]         # top 5 by hedonic contribution
    diagnostics: list[str]


def score_hedonic(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> HedonicReport:
    """Score the hedonic (pleasantness) profile of a formula.

    High score = formula materials converge on pleasant valence.
    Low score  = dominant unpleasant materials OR high hedonic conflict.

    Moderate hedonic contrast is artistically valid (chypre, leather,
    animalic accords) but reduces the hedonic score.
    """
    dilutions = dilutions or {}
    total_active = 0.0
    rated_active = 0.0
    weighted_sum = 0.0
    valence_list: list[float] = []
    weight_list: list[float] = []
    pleasant_mass = 0.0
    unpleasant_mats: list[dict] = []
    material_scores: list[dict] = []
    diagnostics: list[str] = []

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        valence = HEDONIC_VALENCE.get(name)
        if valence is None:
            continue

        rated_active += active
        weighted_sum += valence * active
        valence_list.append(valence)
        weight_list.append(active)

        material_scores.append({
            "material": name,
            "valence": valence,
            "amount_uL": round(active, 1),
            "hedonic_contribution": round(valence * active, 1),
        })

        if valence >= 0.3:
            pleasant_mass += active
        elif valence < 0.0:
            unpleasant_mats.append({
                "material": name,
                "valence": valence,
                "amount_uL": round(active, 1),
            })

    if total_active == 0 or not valence_list:
        return HedonicReport(
            score=50, weighted_valence=0, pleasantness_class="unknown",
            hedonic_contrast=0, pleasant_fraction=0,
            unpleasant_materials=[], most_pleasant=[],
            diagnostics=["No hedonic data"],
        )

    # Weighted mean valence (over rated materials only — unrated are excluded,
    # not penalised as valence=0)
    mean_valence = weighted_sum / rated_active

    # Hedonic contrast: weighted standard deviation
    var_sum = sum(w * (v - mean_valence) ** 2
                  for v, w in zip(valence_list, weight_list))
    contrast = math.sqrt(var_sum / rated_active)

    # Pleasant fraction (of rated mass)
    pleas_frac = pleasant_mass / rated_active

    # Classification
    if mean_valence > 0.7:
        pclass = "highly_pleasant"
    elif mean_valence > 0.5:
        pclass = "pleasant"
    elif mean_valence > 0.3:
        pclass = "moderately_pleasant"
    elif mean_valence > 0.0:
        pclass = "neutral"
    elif mean_valence > -0.2:
        pclass = "challenging"
    else:
        pclass = "discordant"

    # Score: map mean_valence from [-1, 1] to [0, 100]
    # With bonus for coherence and penalty for contrast
    base = (mean_valence + 1.0) / 2.0 * 80  # 0-80 from valence
    coherence_bonus = max(0, (1.0 - contrast) * 20)  # 0-20 from low contrast
    score = base + coherence_bonus
    score = max(0, min(100, score))

    # Sort for top 5
    material_scores.sort(key=lambda x: x["hedonic_contribution"], reverse=True)

    # Diagnostics
    diagnostics.append(f"Hedonic class: {pclass} (mean valence {mean_valence:+.2f})")
    if contrast > 0.3:
        diagnostics.append(
            f"⚠ High hedonic contrast ({contrast:.2f}) — "
            "pleasant/unpleasant elements in tension"
        )
    if unpleasant_mats:
        names = [f"{m['material']} ({m['valence']:+.2f})" for m in unpleasant_mats]
        diagnostics.append(f"Hedonically negative: {', '.join(names)}")
    if pleas_frac > 0.8:
        diagnostics.append("✓ >80% of formula mass is hedonically pleasant")

    return HedonicReport(
        score=round(score, 1),
        weighted_valence=round(mean_valence, 3),
        pleasantness_class=pclass,
        hedonic_contrast=round(contrast, 3),
        pleasant_fraction=round(pleas_frac, 3),
        unpleasant_materials=unpleasant_mats,
        most_pleasant=material_scores[:5],
        diagnostics=diagnostics,
    )
