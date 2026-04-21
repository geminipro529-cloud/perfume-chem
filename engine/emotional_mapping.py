"""Emotional / mood mapping via olfactory-limbic pathways.

The olfactory bulb projects directly to the amygdala (emotion) and
hippocampus (memory) — unique among senses. This means odours trigger
emotional responses BEFORE conscious identification.

Dimensions modelled:
  **Calming**     — parasympathetic activation (lavender/linalool: EEG
                    theta increase, Sayorwan 2012)
  **Energizing**  — sympathetic activation (citrus/peppermint: EEG
                    beta increase, Moss et al. 2008)
  **Sensual**     — dopaminergic reward (musks, vanilla, indole trace:
                    fMRI nucleus accumbens, Rolls 2004)
  **Comforting**  — safety/familiarity signal (vanillin, coumarin,
                    lactones: Proustian association, Herz 2009)
  **Grounding**   — earth/stability (vetiver, patchouli, cedarwood:
                    cortisol reduction, Matsubara 2003)
  **Uplifting**   — euphoric/joyful (neroli, bergamot, hedione:
                    serotonin pathway, Watanabe 2015)

Scoring:
  Measures emotional coherence — does the formula tell a consistent
  emotional story? Mixed signals (calming + energizing in equal
  measure) create emotional ambiguity (lower score).

Sources:
  Herz (2009) Chemical Senses — emotion and cognition in perfumery
  Herz & Cupchik (1995) Memory & Cognition — Proustian memory
  Arshamian et al. (2020) PNAS — universal odor-emotion associations
  Sayorwan et al. (2012) Molecules — linalool calming EEG effects
  Moss et al. (2008) Int J Neuroscience — aromatic plant effects
  Rolls (2004) Brain Research Reviews — olfactory reward
  Bensafi et al. (2002) Chemical Senses — autonomic responses to odours
  Watanabe et al. (2015) Flavour Fragrance J — hedione VNO effect
"""

from __future__ import annotations

from dataclasses import dataclass
import math


# ═══════════════════════════════════════════════════════════════════════════════
# Emotional Profile Data
# 6 dimensions, each 0.0–1.0 intensity
# Based on EEG/fMRI/autonomic studies + Herz(2009) hedonic associations
# ═══════════════════════════════════════════════════════════════════════════════

EMOTIONAL_PROFILES: dict[str, dict[str, float]] = {
    # ── Calming (parasympathetic) ──
    "Linalool":             {"calming": 0.80, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.30, "grounding": 0.10, "uplifting": 0.20},
    "Lavender EO":          {"calming": 0.85, "energizing": 0.0,  "sensual": 0.05,
                             "comforting": 0.40, "grounding": 0.20, "uplifting": 0.10},
    "Clary Sage EO":        {"calming": 0.60, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.20, "grounding": 0.30, "uplifting": 0.10},
    "Benzoin Resinoid":     {"calming": 0.50, "energizing": 0.0,  "sensual": 0.30,
                             "comforting": 0.70, "grounding": 0.30, "uplifting": 0.0},
    "Coumarin":             {"calming": 0.40, "energizing": 0.0,  "sensual": 0.20,
                             "comforting": 0.60, "grounding": 0.15, "uplifting": 0.0},
    "Linalyl Acetate":      {"calming": 0.55, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.25, "grounding": 0.05, "uplifting": 0.15},
    # ── Energizing (sympathetic) ──
    "D-Limonene":           {"calming": 0.0,  "energizing": 0.70, "sensual": 0.0,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.60},
    "Bergamot FCF":         {"calming": 0.20, "energizing": 0.55, "sensual": 0.10,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.65},
    "Bergamot FCF Sicilian":{"calming": 0.20, "energizing": 0.55, "sensual": 0.10,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.65},
    "Cedrat FCF Sicilian":  {"calming": 0.05, "energizing": 0.60, "sensual": 0.05,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.55},
    "Blood Orange Sicilian":{"calming": 0.05, "energizing": 0.65, "sensual": 0.0,
                             "comforting": 0.20, "grounding": 0.0,  "uplifting": 0.70},
    "Grapefruit FCF":       {"calming": 0.0,  "energizing": 0.65, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.60},
    "Red Mandarin EO":      {"calming": 0.10, "energizing": 0.50, "sensual": 0.10,
                             "comforting": 0.30, "grounding": 0.0,  "uplifting": 0.55},
    "Dihydromyrcenol":      {"calming": 0.10, "energizing": 0.55, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.40},
    "Methyl Pamplemousse":  {"calming": 0.0,  "energizing": 0.55, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.45},
    "Terpinyl Acetate":     {"calming": 0.15, "energizing": 0.45, "sensual": 0.0,
                             "comforting": 0.05, "grounding": 0.15, "uplifting": 0.30},
    "Allyl Amyl Glycolate": {"calming": 0.0,  "energizing": 0.40, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.30},
    # ── Sensual (dopaminergic reward) ──
    "Galaxolide":           {"calming": 0.15, "energizing": 0.0,  "sensual": 0.65,
                             "comforting": 0.30, "grounding": 0.0,  "uplifting": 0.0},
    "Habanolide":           {"calming": 0.10, "energizing": 0.0,  "sensual": 0.70,
                             "comforting": 0.25, "grounding": 0.0,  "uplifting": 0.0},
    "Ethylene Brassylate":  {"calming": 0.10, "energizing": 0.0,  "sensual": 0.60,
                             "comforting": 0.30, "grounding": 0.0,  "uplifting": 0.0},
    "Exaltolide":           {"calming": 0.10, "energizing": 0.0,  "sensual": 0.75,
                             "comforting": 0.20, "grounding": 0.0,  "uplifting": 0.0},
    "Ambretone":            {"calming": 0.05, "energizing": 0.0,  "sensual": 0.65,
                             "comforting": 0.15, "grounding": 0.0,  "uplifting": 0.0},
    "Musk Ketone":          {"calming": 0.15, "energizing": 0.0,  "sensual": 0.55,
                             "comforting": 0.40, "grounding": 0.0,  "uplifting": 0.0},
    "Javanol":              {"calming": 0.20, "energizing": 0.0,  "sensual": 0.75,
                             "comforting": 0.15, "grounding": 0.10, "uplifting": 0.0},
    "Ebanol":               {"calming": 0.15, "energizing": 0.0,  "sensual": 0.65,
                             "comforting": 0.20, "grounding": 0.10, "uplifting": 0.0},
    "Indole":               {"calming": 0.0,  "energizing": 0.0,  "sensual": 0.70,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.0},
    "Ambrox Super":         {"calming": 0.10, "energizing": 0.10, "sensual": 0.55,
                             "comforting": 0.20, "grounding": 0.20, "uplifting": 0.15},
    "Isobutyl Quinoline":   {"calming": 0.0,  "energizing": 0.0,  "sensual": 0.40,
                             "comforting": 0.0,  "grounding": 0.05, "uplifting": 0.0},
    # ── Comforting (safety/familiarity) ──
    "Vanillin":             {"calming": 0.30, "energizing": 0.0,  "sensual": 0.30,
                             "comforting": 0.90, "grounding": 0.10, "uplifting": 0.05},
    "Ethyl Vanillin":       {"calming": 0.25, "energizing": 0.0,  "sensual": 0.30,
                             "comforting": 0.85, "grounding": 0.10, "uplifting": 0.05},
    "Heliotropin Fleuressence": {"calming": 0.30, "energizing": 0.0, "sensual": 0.20,
                             "comforting": 0.75, "grounding": 0.10, "uplifting": 0.0},
    "Maple Lactone":        {"calming": 0.15, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.80, "grounding": 0.0,  "uplifting": 0.10},
    "Gamma Decalactone":    {"calming": 0.10, "energizing": 0.0,  "sensual": 0.30,
                             "comforting": 0.60, "grounding": 0.0,  "uplifting": 0.10},
    "Raspberry Ketone":     {"calming": 0.10, "energizing": 0.05, "sensual": 0.15,
                             "comforting": 0.55, "grounding": 0.0,  "uplifting": 0.20},
    "Tonka Bean FO":        {"calming": 0.30, "energizing": 0.0,  "sensual": 0.20,
                             "comforting": 0.80, "grounding": 0.15, "uplifting": 0.0},
    # ── Grounding (earth/stability) ──
    "Vetiver EO":           {"calming": 0.30, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.10, "grounding": 0.85, "uplifting": 0.0},
    "Patchouli EO":         {"calming": 0.20, "energizing": 0.0,  "sensual": 0.25,
                             "comforting": 0.10, "grounding": 0.80, "uplifting": 0.0},
    "Cedarwood EO":         {"calming": 0.25, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.15, "grounding": 0.75, "uplifting": 0.0},
    "Labdanum Absolute":    {"calming": 0.15, "energizing": 0.0,  "sensual": 0.35,
                             "comforting": 0.25, "grounding": 0.65, "uplifting": 0.0},
    "Iso E Super":          {"calming": 0.10, "energizing": 0.0,  "sensual": 0.40,
                             "comforting": 0.15, "grounding": 0.50, "uplifting": 0.0},
    "Cashmeran":            {"calming": 0.20, "energizing": 0.0,  "sensual": 0.35,
                             "comforting": 0.30, "grounding": 0.50, "uplifting": 0.0},
    "Vertofix Coeur":       {"calming": 0.10, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.10, "grounding": 0.65, "uplifting": 0.0},
    "Timberol":             {"calming": 0.10, "energizing": 0.0,  "sensual": 0.05,
                             "comforting": 0.05, "grounding": 0.60, "uplifting": 0.0},
    "Kephalis":             {"calming": 0.05, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.05, "grounding": 0.55, "uplifting": 0.0},
    "Evernyl":              {"calming": 0.05, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.10, "grounding": 0.70, "uplifting": 0.0},
    "Myrrh EO":             {"calming": 0.25, "energizing": 0.0,  "sensual": 0.20,
                             "comforting": 0.20, "grounding": 0.60, "uplifting": 0.0},
    "Olibanum Resinoid":    {"calming": 0.30, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.15, "grounding": 0.60, "uplifting": 0.15},
    "Vetival":              {"calming": 0.15, "energizing": 0.0,  "sensual": 0.20,
                             "comforting": 0.05, "grounding": 0.65, "uplifting": 0.0},
    "Suederal":             {"calming": 0.05, "energizing": 0.0,  "sensual": 0.30,
                             "comforting": 0.05, "grounding": 0.55, "uplifting": 0.0},
    "Birch Tar Rectified":  {"calming": 0.0,  "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.05, "grounding": 0.50, "uplifting": 0.0},
    "Carrot Seed EO":       {"calming": 0.15, "energizing": 0.0,  "sensual": 0.05,
                             "comforting": 0.10, "grounding": 0.55, "uplifting": 0.0},
    # ── Uplifting (euphoric/joyful) ──
    "Neroli EO":            {"calming": 0.20, "energizing": 0.30, "sensual": 0.15,
                             "comforting": 0.15, "grounding": 0.0,  "uplifting": 0.75},
    "Hedione":              {"calming": 0.10, "energizing": 0.15, "sensual": 0.20,
                             "comforting": 0.05, "grounding": 0.0,  "uplifting": 0.70},
    "DBCA":                 {"calming": 0.10, "energizing": 0.10, "sensual": 0.15,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.50},
    "Champaca Flower EO":   {"calming": 0.15, "energizing": 0.15, "sensual": 0.30,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.55},
    "Ylang Comoros Complete EO": {"calming": 0.20, "energizing": 0.10, "sensual": 0.50,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.45},
    "Petitgrain EO":        {"calming": 0.20, "energizing": 0.35, "sensual": 0.05,
                             "comforting": 0.10, "grounding": 0.05, "uplifting": 0.50},
    "Phenethyl Alcohol":    {"calming": 0.15, "energizing": 0.05, "sensual": 0.20,
                             "comforting": 0.15, "grounding": 0.0,  "uplifting": 0.45},
    # ── Florals — mixed emotional profiles ──
    "Freesia HDI":          {"calming": 0.10, "energizing": 0.15, "sensual": 0.10,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.40},
    "Lilyreal ND":          {"calming": 0.15, "energizing": 0.10, "sensual": 0.10,
                             "comforting": 0.20, "grounding": 0.0,  "uplifting": 0.30},
    "Nympheal":             {"calming": 0.10, "energizing": 0.10, "sensual": 0.10,
                             "comforting": 0.15, "grounding": 0.0,  "uplifting": 0.30},
    "Florol":               {"calming": 0.15, "energizing": 0.10, "sensual": 0.10,
                             "comforting": 0.20, "grounding": 0.0,  "uplifting": 0.35},
    "Bourgeonal":           {"calming": 0.05, "energizing": 0.10, "sensual": 0.10,
                             "comforting": 0.15, "grounding": 0.0,  "uplifting": 0.30},
    "Hydroxycitronellal":   {"calming": 0.15, "energizing": 0.05, "sensual": 0.05,
                             "comforting": 0.30, "grounding": 0.0,  "uplifting": 0.25},
    "Orivone":              {"calming": 0.20, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.20, "grounding": 0.10, "uplifting": 0.10},
    # ── Green / ozonic ──
    "cis-3-Hexenol":        {"calming": 0.05, "energizing": 0.30, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.10, "uplifting": 0.35},
    "Dynascone":            {"calming": 0.0,  "energizing": 0.35, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.10, "uplifting": 0.25},
    "Scentenal":            {"calming": 0.0,  "energizing": 0.25, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.05, "uplifting": 0.15},
    "Calone":               {"calming": 0.15, "energizing": 0.20, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.30},
    # ── Ionones ──
    "Alpha Ionone":         {"calming": 0.15, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.20, "grounding": 0.05, "uplifting": 0.10},
    "Beta Ionone":          {"calming": 0.20, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.25, "grounding": 0.10, "uplifting": 0.08},
    "Methyl Ionone Pure":   {"calming": 0.15, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.15, "grounding": 0.10, "uplifting": 0.10},
    "Ultralia":             {"calming": 0.15, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.15, "grounding": 0.05, "uplifting": 0.10},
    # ── Spice ──
    "Eugenol":              {"calming": 0.20, "energizing": 0.15, "sensual": 0.20,
                             "comforting": 0.30, "grounding": 0.20, "uplifting": 0.0},
    "Ethyl Safranate":      {"calming": 0.10, "energizing": 0.10, "sensual": 0.25,
                             "comforting": 0.20, "grounding": 0.15, "uplifting": 0.05},
    "Cardamom FTEC":        {"calming": 0.10, "energizing": 0.30, "sensual": 0.15,
                             "comforting": 0.15, "grounding": 0.10, "uplifting": 0.20},
    # ── Salicylates ──
    "Hexyl Salicylate":     {"calming": 0.15, "energizing": 0.0,  "sensual": 0.20,
                             "comforting": 0.15, "grounding": 0.05, "uplifting": 0.10},
    "Benzyl Salicylate":    {"calming": 0.15, "energizing": 0.0,  "sensual": 0.20,
                             "comforting": 0.15, "grounding": 0.10, "uplifting": 0.05},
    # ── Aldehydic effervescence ──
    "Aldehyde C10":         {"calming": 0.0,  "energizing": 0.20, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.30},
    "Aldehyde C11":         {"calming": 0.0,  "energizing": 0.15, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.25},
    "Aldehyde C12 MNA":     {"calming": 0.05, "energizing": 0.15, "sensual": 0.05,
                             "comforting": 0.05, "grounding": 0.0,  "uplifting": 0.20},
    "Cyclamen Aldehyde":    {"calming": 0.0,  "energizing": 0.15, "sensual": 0.0,
                             "comforting": 0.0,  "grounding": 0.0,  "uplifting": 0.20},
    # ── Fruity ──
    "Paradisamide":         {"calming": 0.0,  "energizing": 0.25, "sensual": 0.15,
                             "comforting": 0.10, "grounding": 0.0,  "uplifting": 0.45},
    # ── Guaiacol / smoke ──
    "Guaiacol":             {"calming": 0.05, "energizing": 0.0,  "sensual": 0.10,
                             "comforting": 0.10, "grounding": 0.30, "uplifting": 0.0},
    # ── Styrax ──
    "Styrax FTEC":          {"calming": 0.05, "energizing": 0.0,  "sensual": 0.20,
                             "comforting": 0.15, "grounding": 0.40, "uplifting": 0.0},
    # ── Woody ──
    "Amberwood F":          {"calming": 0.10, "energizing": 0.0,  "sensual": 0.15,
                             "comforting": 0.15, "grounding": 0.50, "uplifting": 0.0},
    "Koavone":              {"calming": 0.10, "energizing": 0.0,  "sensual": 0.05,
                             "comforting": 0.10, "grounding": 0.45, "uplifting": 0.0},
    "Cedroxyde":            {"calming": 0.10, "energizing": 0.0,  "sensual": 0.05,
                             "comforting": 0.10, "grounding": 0.50, "uplifting": 0.0},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════

MOOD_DIMS = ["calming", "energizing", "sensual", "comforting", "grounding", "uplifting"]


@dataclass
class EmotionalReport:
    """Emotional / mood profile analysis."""
    score: float                      # 0-100 emotional coherence
    mood_vector: dict[str, float]     # 6-dim weighted emotional profile
    dominant_mood: str                 # strongest dimension
    secondary_mood: str               # second strongest
    emotional_narrative: str          # human-readable mood story
    coherence: float                  # 0-1 how unified the emotional message is
    ambiguity: float                  # 0-1 conflicting emotional signals
    diagnostics: list[str]


def score_emotional(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> EmotionalReport:
    """Score the emotional coherence of a formula.

    A high score means the formula projects a clear, unified mood.
    A low score means conflicting emotional signals (e.g., calming +
    energizing in equal measure creates emotional ambiguity).
    """
    dilutions = dilutions or {}
    total_active = 0.0
    mood_accum = {d: 0.0 for d in MOOD_DIMS}
    diagnostics: list[str] = []
    profiled_mass = 0.0

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        profile = EMOTIONAL_PROFILES.get(name)
        if not profile:
            continue

        profiled_mass += active
        for dim in MOOD_DIMS:
            mood_accum[dim] += profile.get(dim, 0.0) * active

    if total_active == 0 or profiled_mass == 0:
        return EmotionalReport(
            score=50, mood_vector={d: 0 for d in MOOD_DIMS},
            dominant_mood="none", secondary_mood="none",
            emotional_narrative="Insufficient data for emotional mapping",
            coherence=0, ambiguity=0, diagnostics=["No emotional data"],
        )

    # Normalize mood vector
    mood_vec = {d: mood_accum[d] / profiled_mass for d in MOOD_DIMS}

    # Sorted moods
    sorted_moods = sorted(mood_vec.items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_moods[0][0]
    secondary = sorted_moods[1][0]
    dom_val = sorted_moods[0][1]
    sec_val = sorted_moods[1][1]

    # Coherence: dominant mood's share of total mood signal
    total_signal = sum(mood_vec.values())
    coherence = dom_val / total_signal if total_signal > 0 else 0.0

    # Ambiguity: opposing moods in tension
    # calming ↔ energizing, comforting ↔ energizing
    opposing_pairs = [("calming", "energizing"), ("comforting", "energizing")]
    ambiguity = 0.0
    for a, b in opposing_pairs:
        if mood_vec[a] > 0.15 and mood_vec[b] > 0.15:
            ambiguity += min(mood_vec[a], mood_vec[b]) * 2

    ambiguity = min(1.0, ambiguity)

    # Narrative
    narrative_map = {
        "calming": "serene and meditative",
        "energizing": "vibrant and invigorating",
        "sensual": "intimate and seductive",
        "comforting": "warm and nurturing",
        "grounding": "stable and contemplative",
        "uplifting": "joyful and euphoric",
    }
    if sec_val > dom_val * 0.6:
        narrative = f"{narrative_map[dominant]} with {narrative_map[secondary]} undertones"
    else:
        narrative = narrative_map[dominant]

    # Score: reward clear emotional story
    base = coherence * 60 + 30  # 30-90 base
    ambiguity_penalty = ambiguity * 20
    score = base - ambiguity_penalty
    # Bonus for strong dominant mood
    if dom_val > 0.5:
        score += 10
    score = max(0, min(100, score))

    # Diagnostics
    diagnostics.append(f"Emotional narrative: {narrative}")
    diagnostics.append(
        f"Mood vector: {', '.join(f'{d}={v:.2f}' for d, v in sorted_moods)}"
    )
    if ambiguity > 0.3:
        diagnostics.append(
            "⚠ Emotional ambiguity — conflicting mood signals "
            "(may be intentional artistic choice)"
        )
    if coherence > 0.4:
        diagnostics.append("✓ Clear emotional identity")

    return EmotionalReport(
        score=round(score, 1),
        mood_vector={d: round(v, 3) for d, v in mood_vec.items()},
        dominant_mood=dominant,
        secondary_mood=secondary,
        emotional_narrative=narrative,
        coherence=round(coherence, 3),
        ambiguity=round(ambiguity, 3),
        diagnostics=diagnostics,
    )
