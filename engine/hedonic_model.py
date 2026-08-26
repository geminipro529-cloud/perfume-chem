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

# ═══════════════════════════════════════════════════════════════════════════════
# Hedonic Valence Data
# Scale: -1.0 (maximally unpleasant) to +1.0 (maximally pleasant)
# Based on Khan (2007) PNAS model outputs, Dravnieks (1985) atlas values,
# and Arctander (1969) subjective descriptors cross-referenced
# ═══════════════════════════════════════════════════════════════════════════════

HEDONIC_VALENCE: dict[str, float] = {
    # ── Universally pleasant (vanillic, floral, fruity) ──
    "Vanillin":               0.90,
    "Ethyl Vanillin":         0.88,
    "Heliotropal": 0.85,  # neat piperonal
    "Linalool":               0.82,
    "Linalyl Acetate":        0.80,
    "Hedione":                0.78,
    "Phenethyl Alcohol":      0.82,
    "Benzyl Acetate":         0.75,
    "Jessemal":              0.45,
    "Coumarin":               0.80,
    "Maple Lactone":          0.85,
    "Gamma Decalactone":      0.83,
    "Gamma Undecalactone":    0.80,
    "Delta Decalactone":      0.78,
    "Raspberry Ketone":       0.80,
    # ── Pleasant florals ──
    "DBCA":                   0.75,
    "Lilyreal ND":            0.70,
    "Bourgeonal":             0.68,
    "Hydroxycitronellal":     0.72,
    "Nympheal":               0.70,
    "Florol":                 0.72,
    "Freesia HDI":            0.70,
    "Orivone":                0.65,
    "Ultralia":               0.60,
    "Methyl Ionone Pure":     0.72,
    "Alpha Ionone":           0.68,
    "Beta Ionone":            0.70,
    "Alpha Irone":            0.65,
    "Cis Jasmone":            0.65,
    # ── Pleasant woody/amber ──
    "Iso E Super":            0.55,
    "Javanol":                0.72,
    "Ebanol":                 0.68,
    "Ambrox Super":           0.60,
    "Cashmeran":              0.65,
    "Vertofix Coeur":         0.55,
    "Amberwood F":            0.60,
    "Timberol":               0.50,
    "Kephalis":               0.45,  # powerful, but less intrinsically pleasant
    "Koavone":                0.55,
    "Cedroxyde":              0.50,
    # ── Pleasant musks ──
    "Galaxolide":             0.70,
    "Habanolide":             0.72,
    "Ethylene Brassylate":    0.70,
    "Exaltolide":             0.75,
    "Musk Ketone":            0.65,
    "Ambretone":              0.68,
    # ── Pleasant citrus ──
    "D-Limonene":             0.75,
    "Bergamot FCF":           0.78,
    "Bergamot FCF Sicilian":  0.80,
    "Cedrat FCF Sicilian":    0.72,
    "Blood Orange Sicilian":  0.80,
    "Grapefruit FCF":         0.73,
    "Red Mandarin EO":        0.82,
    "Methyl Pamplemousse":    0.68,
    "Neroli EO":              0.80,
    "Petitgrain EO":          0.72,
    "Aldehyde C10":           0.40,  # pleasant in context, raw = waxy
    "Aldehyde C11":           0.38,
    "Aldehyde C11 Undecylenic": 0.35,
    "Aldehyde C12 MNA":       0.42,
    "Cyclamen Aldehyde":      0.45,
    "Scentenal":              0.30,  # metallic — polarizing
    "Calone":                 0.35,  # marine — polarizing
    "Floralozone":            0.40,
    "Dihydromyrcenol":        0.55,
    # ── Green (fresh but sharp) ──
    "cis-3-Hexenol":          0.50,
    "Parmavert":              0.55,
    "Leafovert":              0.45,
    "Dynascone":              0.30,  # powerful green bomb, unpleasant neat
    "Allyl Amyl Glycolate":   0.50,
    # ── Spice (context-dependent) ──
    "Eugenol":                0.45,
    "Ethyl Safranate":        0.55,
        "Cardamom EO":            0.65,  # natural EO, more aromatic complexity than FTEC
    "Terpinyl Acetate":       0.55,
    # ── Leather / smoke (acquired taste) ──
    "Suederal":               0.30,
    "Evernyl":                0.35,
    "Birch Tar Rectified":    0.10,  # smoky — divisive
    "Guaiacol":               0.15,  # medicinal neat, beautiful in traces
    "Isobutyl Quinoline":     0.05,  # dirty leather — negative neat
    "Styrax FTEC":            0.25,
    # ── Animalic (negative neat, positive in traces) ──
    "Indole":                -0.20,  # fecal neat, jasmine in traces
    # ── Balsamic ──
    "Benzoin Resinoid":       0.70,
    "Labdanum Absolute":      0.50,
    "Olibanum Resinoid":      0.55,
    "Myrrh EO":               0.45,
    # ── EOs ──
    "Lavender EO":            0.75,
    "Lavender EO (BONTAUX SAS)": 0.78,  # premium French angustifolia, less camphoraceous
    "Clary Sage EO":          0.50,
    "Rosemary EO (French Rosmarinus Officinalis leaf oil)": 0.55,
    "Vetiver EO":             0.45,
    "Vetiver EO (India)":     0.50,  # deeper, richer ruh khus character
    "Patchouli EO":           0.42,
    "Cedarwood EO":           0.55,
    "Champaca Flower EO":     0.60,
    "Ylang Comoros Complete EO": 0.65,
    "Ylang Comoros III EO":   0.68,
    "Carrot Seed EO":         0.30,
    # ── Fruity ──
    "Paradisamide":           0.65,
    # ── Misc ──
    "Hexyl Salicylate":       0.60,
    "Benzyl Salicylate":      0.55,
    "Vetival":                0.40,
    "Salicylate FTEC":        0.55,
    # ── Coverage additions (Perfume A materials) ──
    "Romandolide":            0.68,  # clean woody-musk, pleasant
    "Benzyl Benzoate":        0.35,  # near-odorless fixative, faint balsamic
    "Hedione HC":             0.78,  # same hedonic as Hedione, high-cis variant
    "Dihydro Beta Ionone":    0.62,  # soft woody-violet, pleasant
    "Sandalore":              0.70,  # fresh-creamy sandalwood
    "Clearwood":              0.50,  # clean patchouli replacement, earthy
    "Zenolide":               0.65,  # clean citrusy-fresh musk
    "Vertofix":               0.55,  # woody-musky, amber-cedarwood fixative
    "Bacdanol":               0.70,  # milky round sandalwood
    "Dihydrojasmone":         0.60,  # creamy jasmine-fruity
    "Methyl Nonyl Ketone":    0.30,  # waxy, green-fatty
    "Helional":               0.62,  # green-floral aquatic, heliotrope facet
    "Norlimbanol Dextro":     0.50,  # powerful transparent woody
    "Ambrofix":               0.60,  # smooth ambergris-amber
    "Ambermax":               0.65,  # warm rounded amber
    "Aurantiol":              0.72,  # orange-blossom hydroxycitronellal type
    "Anisaldehyde":           0.60,  # sweet aniseed-hawthorn
    "Macrolide":              0.65,  # soft clean musk
    "Ylang III":              0.65,  # heavy floral, balsamic ylang
    "Ethyl Maltol":           0.85,  # sweet cotton-candy caramel
    "Rose Oxide":             0.72,  # rose-lychee, pleasant floral
    "Damascenone":            0.75,  # rose-ketone, powerful pleasant
}


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
