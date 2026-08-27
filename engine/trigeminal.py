"""Trigeminal chemesthetic effect modelling.

Fragrance materials don't just SMELL — they FEEL. The trigeminal nerve
(CN V) mediates touch-like sensations through TRP ion channels:

  **TRPM8** — Cooling (menthol, linalool, Dihydromyrcenol)
  **TRPV1** — Warming/irritation (eugenol, cinnamaldehyde, guaiacol)
  **TRPA1** — Tingling/pungency (cinnamaldehyde, allyl isothiocyanate)

Additionally:
  **Numbing** — Eugenol (dental anaesthetic), clove effects
  **Freshness** — Hedione respiratory lift, cis-3-hexenol green bite
  **Effervescence** — Aldehydes create a sparkling tingling (C10-C12)
  **Metallic** — Cyclamen Aldehyde, Scentenal metallic sharpness

Scoring:
  Measures the chemesthetic profile and its coherence.
  A formula with mixed signals (cooling + warming in equal doses) is
  confused. A formula with a clear chemesthetic identity scores higher.

Sources:
  Viana (2011) Molecular Pain — TRPA1 channels and chemesthesis
  Green (1996) Chemical Senses — chemesthetic sensory interaction
  McKemy et al. (2002) Nature — TRPM8 identification
  Caterina et al. (1997) Nature — TRPV1 (capsaicin receptor)
  Jordt et al. (2004) Nature — TRPA1 activation
  Laska et al. (2007) Flavour Fragrance J — trigeminal potency
"""

from __future__ import annotations

from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════════════════
# TRP Channel Activation Profiles
# Values are 0.0–1.0 activation strength at typical perfumery doses
# Sources: Viana (2011), McKemy (2002), Caterina (1997), Jordt (2004),
#          supplemented with sensory evaluation reports
# ═══════════════════════════════════════════════════════════════════════════════

TRIGEMINAL_PROFILES: dict[str, dict[str, float]] = {
    # ── Cooling (TRPM8 activation) ──
    "Linalool": {"TRPM8": 0.25, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
    "Linalyl Acetate": {
        "TRPM8": 0.15,
        "TRPV1": 0.0,
        "TRPA1": 0.0,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Dihydromyrcenol": {
        "TRPM8": 0.40,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Terpinyl Acetate": {
        "TRPM8": 0.20,
        "TRPV1": 0.0,
        "TRPA1": 0.0,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Hedione": {"TRPM8": 0.10, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.10},
    # ── Warming (TRPV1 activation) ──
    "Eugenol": {"TRPM8": 0.0, "TRPV1": 0.50, "TRPA1": 0.20, "numbing": 0.45, "effervescence": 0.0},
    "Guaiacol": {"TRPM8": 0.0, "TRPV1": 0.35, "TRPA1": 0.15, "numbing": 0.10, "effervescence": 0.0},
    "Cinnamaldehyde": {
        "TRPM8": 0.0,
        "TRPV1": 0.30,
        "TRPA1": 0.65,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Birch Tar Rectified": {
        "TRPM8": 0.0,
        "TRPV1": 0.20,
        "TRPA1": 0.10,
        "numbing": 0.05,
        "effervescence": 0.0,
    },
    "Ethyl Safranate": {
        "TRPM8": 0.0,
        "TRPV1": 0.15,
        "TRPA1": 0.10,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    # ── Aldehydic effervescence / tingling ──
    "Aldehyde C10": {
        "TRPM8": 0.05,
        "TRPV1": 0.05,
        "TRPA1": 0.15,
        "numbing": 0.0,
        "effervescence": 0.60,
    },
    "Aldehyde C11": {
        "TRPM8": 0.05,
        "TRPV1": 0.05,
        "TRPA1": 0.15,
        "numbing": 0.0,
        "effervescence": 0.55,
    },
    "Aldehyde C11 Undecylenic": {
        "TRPM8": 0.05,
        "TRPV1": 0.05,
        "TRPA1": 0.12,
        "numbing": 0.0,
        "effervescence": 0.50,
    },
    "Aldehyde C12 MNA": {
        "TRPM8": 0.05,
        "TRPV1": 0.03,
        "TRPA1": 0.10,
        "numbing": 0.0,
        "effervescence": 0.45,
    },
    # ── Metallic / mineral ──
    "Cyclamen Aldehyde": {
        "TRPM8": 0.10,
        "TRPV1": 0.05,
        "TRPA1": 0.20,
        "numbing": 0.0,
        "effervescence": 0.35,
    },
    "Scentenal": {
        "TRPM8": 0.15,
        "TRPV1": 0.0,
        "TRPA1": 0.15,
        "numbing": 0.0,
        "effervescence": 0.25,
    },
    # ── Green bite ──
    "cis-3-Hexenol": {
        "TRPM8": 0.05,
        "TRPV1": 0.10,
        "TRPA1": 0.30,
        "numbing": 0.0,
        "effervescence": 0.05,
    },
    "Dynascone": {"TRPM8": 0.0, "TRPV1": 0.10, "TRPA1": 0.25, "numbing": 0.0, "effervescence": 0.0},
    "Allyl Amyl Glycolate": {
        "TRPM8": 0.15,
        "TRPV1": 0.0,
        "TRPA1": 0.10,
        "numbing": 0.0,
        "effervescence": 0.05,
    },
    "Leafovert": {
        "TRPM8": 0.05,
        "TRPV1": 0.05,
        "TRPA1": 0.15,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Parmavert": {
        "TRPM8": 0.05,
        "TRPV1": 0.05,
        "TRPA1": 0.10,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    # ── Ozonic / aquatic ──
    "Calone": {"TRPM8": 0.10, "TRPV1": 0.0, "TRPA1": 0.05, "numbing": 0.0, "effervescence": 0.15},
    "Floralozone": {
        "TRPM8": 0.10,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.10,
    },
    # ── Citrus terpenes ──
    "D-Limonene": {
        "TRPM8": 0.10,
        "TRPV1": 0.05,
        "TRPA1": 0.10,
        "numbing": 0.0,
        "effervescence": 0.15,
    },
    "Cedrat FCF Sicilian": {
        "TRPM8": 0.10,
        "TRPV1": 0.0,
        "TRPA1": 0.10,
        "numbing": 0.0,
        "effervescence": 0.10,
    },
    "Grapefruit FCF": {
        "TRPM8": 0.10,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.10,
    },
    "Blood Orange Sicilian": {
        "TRPM8": 0.05,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.10,
    },
    "Bergamot FCF": {
        "TRPM8": 0.10,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.10,
    },
    "Bergamot FCF Sicilian": {
        "TRPM8": 0.10,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.10,
    },
    "Red Mandarin EO": {
        "TRPM8": 0.05,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.08,
    },
    "Methyl Pamplemousse": {
        "TRPM8": 0.08,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.10,
    },
    # ── Spice ──
    "Cardamom EO": {
        "TRPM8": 0.20,
        "TRPV1": 0.05,
        "TRPA1": 0.08,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    # ── Ambrox / mineral ──
    "Ambrox Super": {
        "TRPM8": 0.0,
        "TRPV1": 0.05,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    # ── Indole ──
    "Indole": {"TRPM8": 0.0, "TRPV1": 0.10, "TRPA1": 0.15, "numbing": 0.0, "effervescence": 0.0},
    # ── Lavender ──
    "Lavender EO": {
        "TRPM8": 0.20,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Lavender EO (BONTAUX SAS)": {
        "TRPM8": 0.15,
        "TRPV1": 0.0,
        "TRPA1": 0.03,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Clary Sage EO": {
        "TRPM8": 0.15,
        "TRPV1": 0.0,
        "TRPA1": 0.05,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    # ── Heliotropin / vanillic ──
    "Heliotropal": {"TRPM8": 0.0, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
    "Vanillin": {"TRPM8": 0.0, "TRPV1": 0.05, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
    # ── Neutral (no trigeminal activity) ──
    "Iso E Super": {"TRPM8": 0.0, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
    "Cashmeran": {"TRPM8": 0.0, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
    "Galaxolide": {"TRPM8": 0.0, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
    "Benzyl Salicylate": {
        "TRPM8": 0.0,
        "TRPV1": 0.0,
        "TRPA1": 0.0,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "Coumarin": {"TRPM8": 0.0, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
    "Ethylene Brassylate": {
        "TRPM8": 0.0,
        "TRPV1": 0.0,
        "TRPA1": 0.0,
        "numbing": 0.0,
        "effervescence": 0.0,
    },
    "DBCA": {"TRPM8": 0.0, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TrigeminalReport:
    """Chemesthetic profile and coherence analysis."""

    score: float  # 0-100 composite
    cooling_intensity: float  # 0-1 weighted TRPM8
    warming_intensity: float  # 0-1 weighted TRPV1+TRPA1 warming subset
    tingling_intensity: float  # 0-1 TRPA1 pungency
    effervescence_intensity: float  # 0-1 aldehydic sparkle
    numbing_intensity: float  # 0-1 anaesthetic effect
    dominant_effect: str  # "cooling", "warming", "tingling", etc.
    coherence: float  # 0-1 how unified the chemesthetic profile is
    active_materials: list[dict]  # materials contributing trigeminal effects
    diagnostics: list[str]


def score_trigeminal(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> TrigeminalReport:
    """Score the chemesthetic (touch-feel) profile of a formula.

    A high score means:
    - Formula has a clear, intentional chemesthetic identity
    - Cooling, warming, tingling, or effervescence is coherent (not random)
    - Active materials contribute meaningful sensory texture

    A low score means:
    - Mixed signals (cooling + warming cancel out = confusion)
    - No chemesthetic character at all (not necessarily bad for some styles)
    """
    dilutions = dilutions or {}
    total_active = 0.0
    channels = {"TRPM8": 0.0, "TRPV1": 0.0, "TRPA1": 0.0, "numbing": 0.0, "effervescence": 0.0}
    active_mats: list[dict] = []
    diagnostics: list[str] = []

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        profile = TRIGEMINAL_PROFILES.get(name)
        if not profile:
            continue

        has_activity = any(v > 0 for v in profile.values())
        if not has_activity:
            continue

        for ch, val in profile.items():
            channels[ch] += val * active

        dominant = max(profile, key=profile.get)
        active_mats.append(
            {
                "material": name,
                "dominant_channel": dominant,
                "intensity": round(profile[dominant], 2),
                "amount_uL": round(active, 1),
            }
        )

    if total_active == 0:
        return TrigeminalReport(
            score=50,
            cooling_intensity=0,
            warming_intensity=0,
            tingling_intensity=0,
            effervescence_intensity=0,
            numbing_intensity=0,
            dominant_effect="none",
            coherence=0,
            active_materials=[],
            diagnostics=["No trigeminal data"],
        )

    # Normalize channel outputs
    cooling = min(1.0, channels["TRPM8"] / (total_active * 0.15 + 1))
    warming = min(1.0, channels["TRPV1"] / (total_active * 0.15 + 1))
    tingling = min(1.0, channels["TRPA1"] / (total_active * 0.15 + 1))
    efferv = min(1.0, channels["effervescence"] / (total_active * 0.15 + 1))
    numb = min(1.0, channels["numbing"] / (total_active * 0.15 + 1))

    # Determine dominant effect
    effects = {
        "cooling": cooling,
        "warming": warming,
        "tingling": tingling,
        "effervescence": efferv,
        "numbing": numb,
    }
    dominant = max(effects, key=effects.get)
    dom_val = effects[dominant]

    # Coherence: how much does the dominant effect dominate?
    vals = list(effects.values())
    total_effect = sum(vals)
    if total_effect > 0:
        coherence = dom_val / total_effect
    else:
        coherence = 0.0

    # Score: reward clear chemesthetic identity
    # Base score from having any activity + coherence bonus
    activity_score = min(1.0, total_effect / 0.5) * 50  # up to 50 for having effects
    coherence_bonus = coherence * 50  # up to 50 for coherent profile

    # Penalty for conflicting signals (cooling + warming together)
    conflict_penalty = 0
    if cooling > 0.2 and warming > 0.2:
        conflict_penalty = min(20, (cooling + warming) * 15)
        diagnostics.append("⚠ Cooling-warming conflict — mixed chemesthetic signal")

    score = activity_score + coherence_bonus - conflict_penalty
    score = max(0, min(100, score))

    # Diagnostics
    if dom_val > 0.3:
        diagnostics.insert(0, f"✓ Clear {dominant} chemesthetic identity")
    elif dom_val > 0.1:
        diagnostics.insert(0, f"ℹ Subtle {dominant} chemesthetic undertone")
    else:
        diagnostics.insert(0, "ℹ Minimal chemesthetic activity (neutral texture)")

    if efferv > 0.2:
        diagnostics.append("Aldehydic effervescence detected — sparkling texture")
    if numb > 0.2:
        diagnostics.append("Eugenol-type numbing — dental/spice anaesthetic effect")

    return TrigeminalReport(
        score=round(score, 1),
        cooling_intensity=round(cooling, 3),
        warming_intensity=round(warming, 3),
        tingling_intensity=round(tingling, 3),
        effervescence_intensity=round(efferv, 3),
        numbing_intensity=round(numb, 3),
        dominant_effect=dominant,
        coherence=round(coherence, 3),
        active_materials=sorted(active_mats, key=lambda x: x["intensity"], reverse=True),
        diagnostics=diagnostics,
    )
