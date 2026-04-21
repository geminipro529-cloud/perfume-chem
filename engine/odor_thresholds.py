"""Odor Detection Threshold Analysis — Reviewer perception constrains doses.

Every aroma chemical has a published odor detection threshold (ODT) — the
minimum concentration at which 50% of panelists can detect the material.

If reviewers consistently detect a note (e.g., 85% detect "iris"), the
responsible material must be ABOVE its effective perception threshold
(which is typically 3–10× the ODT due to mixture suppression).

If reviewers DON'T detect a note (e.g., only 15% detect "sandalwood"),
the material is either below threshold, absent, or masked.

This module converts reviewer vote data into concentration constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Odor Detection Thresholds in Air (ppb) ──────────────────────────
# Sources: Leffingwell, Arctander, van Gemert (2011), Devos et al.
# ODT_air values in parts per billion (ppb v/v)
# Also includes approximate ODT in ethanol solution (ppm w/w)

ODT_DATA: dict[str, dict] = {
    # Material → {odt_air_ppb, odt_ethanol_ppm, character}
    "alpha irone":              {"odt_air": 0.1, "odt_eth": 0.01, "char": "iris, orris, butter"},
    "alpha-isomethyl ionone":   {"odt_air": 5.0, "odt_eth": 0.5, "char": "violet, powder, iris"},
    "alpha ionone":             {"odt_air": 0.4, "odt_eth": 0.1, "char": "violet, berry, fruity"},
    "beta ionone":              {"odt_air": 0.007, "odt_eth": 0.05, "char": "violet, woody, warm"},
    "methyl ionone gamma":      {"odt_air": 2.0, "odt_eth": 0.3, "char": "woody iris, warm"},
    "orivone":                  {"odt_air": 3.0, "odt_eth": 0.5, "char": "orris, butter, fatty"},
    "hedione":                  {"odt_air": 25.0, "odt_eth": 5.0, "char": "jasmine, radiance"},
    "iso e super":              {"odt_air": 10.0, "odt_eth": 2.0, "char": "cedar, abstract wood"},
    "benzyl salicylate":        {"odt_air": 200.0, "odt_eth": 50.0, "char": "balsamic, faint floral"},
    "ambrox super":             {"odt_air": 0.3, "odt_eth": 0.05, "char": "amber, crystal, mineral"},
    "galaxolide":               {"odt_air": 5.0, "odt_eth": 1.0, "char": "musk, sweet, clean"},
    "habanolide":               {"odt_air": 1.0, "odt_eth": 0.2, "char": "musk, white, skin"},
    "coumarin":                 {"odt_air": 15.0, "odt_eth": 5.0, "char": "hay, tonka, warm"},
    "vanillin":                 {"odt_air": 20.0, "odt_eth": 10.0, "char": "vanilla, sweet"},
    "ethyl vanillin":           {"odt_air": 6.0, "odt_eth": 3.0, "char": "vanilla, caramel, dark"},
    "linalool":                 {"odt_air": 6.0, "odt_eth": 1.0, "char": "floral, fresh, lavender"},
    "citronellol":              {"odt_air": 40.0, "odt_eth": 5.0, "char": "rose, fresh, green"},
    "geraniol":                 {"odt_air": 40.0, "odt_eth": 5.0, "char": "rose, geranium, sweet"},
    "eugenol":                  {"odt_air": 6.0, "odt_eth": 1.0, "char": "clove, spicy, warm"},
    "hydroxycitronellal":       {"odt_air": 15.0, "odt_eth": 3.0, "char": "muguet, dewy, fresh"},
    "indole":                   {"odt_air": 0.3, "odt_eth": 0.05, "char": "animalic, floral, narcotic"},
    "guaiacol":                 {"odt_air": 3.0, "odt_eth": 0.5, "char": "smoke, phenolic, campfire"},
    "patchouli alcohol":        {"odt_air": 10.0, "odt_eth": 2.0, "char": "earthy, dark, woody"},
    "vetiver":                  {"odt_air": 5.0, "odt_eth": 1.0, "char": "earthy, smoky, root"},
    "cedarwood":                {"odt_air": 15.0, "odt_eth": 3.0, "char": "pencil, dry wood"},
    "cis-jasmone":              {"odt_air": 0.5, "odt_eth": 0.1, "char": "jasmine, green, oily"},
    "benzyl acetate":           {"odt_air": 20.0, "odt_eth": 5.0, "char": "jasmine, fruity, sweet"},
    "phenethyl alcohol":        {"odt_air": 200.0, "odt_eth": 40.0, "char": "rose, honey, mild"},
    "rose oxide":               {"odt_air": 0.005, "odt_eth": 0.001, "char": "metallic, green, lychee"},
    "limonene":                 {"odt_air": 10.0, "odt_eth": 2.0, "char": "orange peel, citrus"},
    "bergamot":                 {"odt_air": 8.0, "odt_eth": 1.5, "char": "fresh, citrus, tea"},
    "cashmeran":                {"odt_air": 2.0, "odt_eth": 0.5, "char": "musky, woody, warm"},
    "labdanum":                 {"odt_air": 10.0, "odt_eth": 2.0, "char": "amber, resinous, dark"},
    "ibq":                      {"odt_air": 0.1, "odt_eth": 0.02, "char": "leather, dirty, animalic"},
    "farnesol":                 {"odt_air": 50.0, "odt_eth": 10.0, "char": "floral, muguet, subtle"},
    "benzyl benzoate":          {"odt_air": 500.0, "odt_eth": 100.0, "char": "faint balsamic (mostly fixative)"},
    "benzyl alcohol":           {"odt_air": 300.0, "odt_eth": 60.0, "char": "faint, solvent-like"},
    "oud oil":                  {"odt_air": 0.5, "odt_eth": 0.1, "char": "barnyard, smoky, complex"},
    "carrot seed":              {"odt_air": 5.0, "odt_eth": 1.0, "char": "earthy, rooty, iris-like"},
    "ultralia":                 {"odt_air": 0.3, "odt_eth": 0.05, "char": "ghost iris, transparent"},
    "suederal":                 {"odt_air": 2.0, "odt_eth": 0.5, "char": "suede, leather, warm"},
    "maple lactone":            {"odt_air": 1.0, "odt_eth": 0.2, "char": "caramel, toffee, sweet"},
    # ── Materials referenced by NOTE_TO_MATERIALS ──
    "rose absolute":            {"odt_air": 15.0, "odt_eth": 3.0, "char": "rose, complex, honeyed"},
    "jasmine absolute":         {"odt_air": 8.0, "odt_eth": 1.5, "char": "jasmine, narcotic, indolic"},
    "ebanol":                   {"odt_air": 8.0, "odt_eth": 1.5, "char": "sandalwood, creamy, milky"},
    "javanol":                  {"odt_air": 3.0, "odt_eth": 0.5, "char": "sandalwood, dry, intimate"},
    "bacdanol":                 {"odt_air": 12.0, "odt_eth": 2.5, "char": "sandalwood, milky, heavy"},
    "sandalwood eo":            {"odt_air": 5.0, "odt_eth": 1.0, "char": "sandalwood, warm, balsamic"},
}

# Mixture suppression factor: in a complex formula, effective threshold
# is typically 3–10× the pure ODT (Laing & Francis, 1989)
MIXTURE_SUPPRESSION_FACTOR = 5.0

# Vote fraction → presence probability mapping
# 85% of reviewers detect → almost certainly present above threshold
# 50% detect → likely present but could be subliminal
# 20% detect → trace or projected/imagined
VOTE_TO_PRESENCE = [
    (0.80, 0.95),   # ≥80% → 95% likely above threshold
    (0.60, 0.80),   # 60-80% → 80% likely
    (0.40, 0.60),   # 40-60% → 60% likely
    (0.25, 0.40),   # 25-40% → marginal
    (0.10, 0.20),   # 10-25% → trace or phantom
    (0.00, 0.05),   # <10% → noise
]

# ── Note → Material mappings for ODT analysis ──────────────────────
# Which materials produce each note that reviewers vote on

NOTE_TO_MATERIALS: dict[str, list[tuple[str, float]]] = {
    "iris":     [("alpha irone", 0.50), ("alpha-isomethyl ionone", 0.30),
                 ("orivone", 0.15), ("ultralia", 0.05)],
    "orris":    [("alpha irone", 0.45), ("orivone", 0.30),
                 ("carrot seed", 0.15), ("alpha-isomethyl ionone", 0.10)],
    "rose":     [("citronellol", 0.35), ("geraniol", 0.25),
                 ("phenethyl alcohol", 0.25), ("rose oxide", 0.10),
                 ("rose absolute", 0.05)],
    "jasmine":  [("hedione", 0.30), ("cis-jasmone", 0.25),
                 ("benzyl acetate", 0.20), ("indole", 0.15),
                 ("jasmine absolute", 0.10)],
    "wood":     [("iso e super", 0.40), ("cedarwood", 0.30),
                 ("patchouli alcohol", 0.15), ("vetiver", 0.15)],
    "powder":   [("alpha-isomethyl ionone", 0.40), ("coumarin", 0.30),
                 ("alpha irone", 0.20), ("vanillin", 0.10)],
    "oud":      [("oud oil", 0.40), ("guaiacol", 0.30),
                 ("patchouli alcohol", 0.15), ("vetiver", 0.15)],
    "musk":     [("galaxolide", 0.30), ("habanolide", 0.30),
                 ("ambrox super", 0.20), ("cashmeran", 0.20)],
    "amber":    [("ambrox super", 0.35), ("labdanum", 0.35),
                 ("benzyl benzoate", 0.15), ("vanillin", 0.15)],
    "leather":  [("ibq", 0.35), ("suederal", 0.30),
                 ("guaiacol", 0.20), ("indole", 0.15)],
    "vanilla":  [("vanillin", 0.40), ("ethyl vanillin", 0.35),
                 ("benzyl benzoate", 0.15), ("coumarin", 0.10)],
    "cedar":    [("cedarwood", 0.50), ("iso e super", 0.40),
                 ("cashmeran", 0.10)],
    "sandalwood": [("ebanol", 0.30), ("javanol", 0.30),
                   ("bacdanol", 0.20), ("sandalwood eo", 0.20)],
    "vetiver":  [("vetiver", 0.70), ("patchouli alcohol", 0.20),
                 ("guaiacol", 0.10)],
    "patchouli": [("patchouli alcohol", 0.80), ("vetiver", 0.10),
                  ("cedarwood", 0.10)],
}


@dataclass
class ODTConstraint:
    """Concentration constraint derived from reviewer perception data."""
    material: str
    note: str                        # The note reviewers voted on
    vote_fraction: float             # Fraction of reviewers detecting this note
    presence_probability: float      # Probability material is above threshold
    min_effective_pct: float         # Minimum % of concentrate to be perceptible
    odt_air_ppb: float
    material_weight: float           # How much this material contributes to the note
    status: str                      # "above_threshold", "near_threshold", "below_threshold"


@dataclass
class ODTAnalysisResult:
    """Complete ODT-based analysis for a fragrance."""
    target_name: str
    constraints: list[ODTConstraint]
    materials_above_threshold: list[str]
    materials_below_threshold: list[str]
    score: float                     # 0–100: how much ODT constrains


def _vote_to_presence_prob(vote_frac: float) -> float:
    """Convert vote fraction to presence probability."""
    for threshold, prob in VOTE_TO_PRESENCE:
        if vote_frac >= threshold:
            return prob
    return 0.05


def _estimate_min_concentrate_pct(
    odt_eth_ppm: float,
    concentrate_pct: float = 25.0,
) -> float:
    """Estimate minimum % of concentrate for a material to be perceptible.

    Uses ODT in ethanol solution, adjusted for mixture suppression and
    dilution to final product concentration.
    """
    # Effective threshold = ODT × suppression factor
    effective_ppm = odt_eth_ppm * MIXTURE_SUPPRESSION_FACTOR

    # Convert ppm in finished product to % of concentrate
    # effective_ppm in finished product = conc_ppm × (concentrate_pct / 100)
    # So conc_ppm = effective_ppm / (concentrate_pct / 100)
    conc_ppm = effective_ppm / (concentrate_pct / 100.0)
    conc_pct = conc_ppm / 10000.0  # ppm → %

    return conc_pct


def analyze_odor_thresholds(
    target_name: str,
    note_votes: dict[str, float],
    total_reviewers: int = 200,
    concentrate_pct: float = 25.0,
) -> ODTAnalysisResult:
    """Derive concentration constraints from reviewer vote data + ODT science.

    Args:
        target_name: Fragrance name.
        note_votes: note → fraction of reviewers detecting it (0–1).
        total_reviewers: Total reviewer count (for statistical significance).
        concentrate_pct: Product concentration %.

    Returns:
        ODTAnalysisResult with per-material constraints.
    """
    constraints: list[ODTConstraint] = []
    above: set[str] = set()
    below: set[str] = set()

    for note, vote_frac in note_votes.items():
        note_key = note.lower().strip()
        if note_key not in NOTE_TO_MATERIALS:
            continue

        presence_prob = _vote_to_presence_prob(vote_frac)

        for material, weight in NOTE_TO_MATERIALS[note_key]:
            odt_data = ODT_DATA.get(material)
            if not odt_data:
                continue

            min_pct = _estimate_min_concentrate_pct(
                odt_data["odt_eth"], concentrate_pct
            )

            if presence_prob >= 0.60:
                status = "above_threshold"
                above.add(material)
            elif presence_prob >= 0.30:
                status = "near_threshold"
            else:
                status = "below_threshold"
                below.add(material)

            constraints.append(ODTConstraint(
                material=material,
                note=note,
                vote_fraction=vote_frac,
                presence_probability=presence_prob,
                min_effective_pct=min_pct,
                odt_air_ppb=odt_data["odt_air"],
                material_weight=weight,
                status=status,
            ))

    # Remove from below if also above (different notes may conflict)
    below -= above

    # Score: how constraining the ODT analysis is
    if not constraints:
        score = 0.0
    else:
        n_constrained = len(above) + len(below)
        avg_presence = sum(c.presence_probability for c in constraints) / len(constraints)
        score = min(100.0, n_constrained * 3.0 + avg_presence * 40.0)

    return ODTAnalysisResult(
        target_name=target_name,
        constraints=constraints,
        materials_above_threshold=sorted(above),
        materials_below_threshold=sorted(below),
        score=score,
    )
