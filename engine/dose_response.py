"""Dose-response modelling and character shift detection.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every perceptibility claim must be backed by OAV.

Most aroma chemicals change their olfactive character at different
concentrations. This is NOT just intensity — it's qualitative shift:

  **Indole**: 0.01% floral-jasmine → 0.1% animalic → 1% fecal
  **Guaiacol**: 0.001% smoky depth → 0.01% phenolic → 0.1% medicinal
  **Civet/Castoreum**: trace = warmth → 0.1% = animalic
  **Ethyl Maltol**: 0.1% sweet lift → 2% cotton candy → 5% chemical burn
  **Iso E Super**: low = transparent woody → 5%+ = molecular cocoon effect
  **Hydroxycitronellal**: low = dewy-fresh → high = soapy/detergent
  **Aldehydes**: trace = sparkle → 1% = waxy-candle → 2%+ = soapy

The sigmoid Hill equation models this:
  Response = Rmax × [C]^n / (EC50^n + [C]^n)
where:
  Rmax = maximal response
  EC50 = half-maximal concentration
  n    = Hill coefficient (steepness of dose-response curve)

Sources:
  Chastrette (1998) Chemical Senses — structure-odor relationships
  Arctander (1969) Perfume and Flavor Chemicals
  Sell (2006) Chemistry and the Sense of Smell
  Stevens (1957) Psychophysical Review — power law for perceived intensity
  Cain (1969) Perception & Psychophysics — adaptation and dose-response
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# Character Shift Data
# Each material defines concentration zones and their character descriptors
# Zones are cumulative (highest matching zone applies)
# conc_pct thresholds are % of CONCENTRATE (not finished product)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CharacterZone:
    """A concentration-dependent character region."""
    max_conc_pct: float     # upper limit of this zone (% in concentrate)
    character: str          # olfactive character in this zone
    quality: str            # "positive", "neutral", "negative", "dangerous"


CHARACTER_SHIFT_DATA: dict[str, list[CharacterZone]] = {
    # ── Animalics / trace materials ──
    "Indole": [
        CharacterZone(0.05,  "transparent jasmine-floral lift",     "positive"),
        CharacterZone(0.2,   "narcotic floral, slightly animalic",  "positive"),
        CharacterZone(0.5,   "animalic, mothball, ink",             "neutral"),
        CharacterZone(2.0,   "fecal, skatolic, overwhelming",       "dangerous"),
    ],
    "Isobutyl Quinoline": [
        CharacterZone(0.05,  "dirty leather undertone",             "positive"),
        CharacterZone(0.2,   "dark leather, animalistic",           "positive"),
        CharacterZone(0.5,   "harsh quinoline, chemical",           "negative"),
    ],
    "Guaiacol": [
        CharacterZone(0.03,  "smoky depth, leather warmth",         "positive"),
        CharacterZone(0.1,   "creosote, phenolic",                  "neutral"),
        CharacterZone(0.5,   "medicinal, sharp, overwhelming",      "dangerous"),
    ],
    # ── Aldehydes ──
    "Aldehyde C10": [
        CharacterZone(0.05,  "waxy sparkle, citrus peel",           "positive"),
        CharacterZone(0.3,   "orange-peel, slightly soapy",         "positive"),
        CharacterZone(1.0,   "waxy-candle, metallic",               "neutral"),
        CharacterZone(3.0,   "soapy, tallow, rancid",               "negative"),
    ],
    "Aldehyde C11": [
        CharacterZone(0.05,  "clean, fresh, soapy lift",            "positive"),
        CharacterZone(0.3,   "waxy, aldehydic body",                "positive"),
        CharacterZone(1.0,   "heavy waxy, detergent",               "neutral"),
        CharacterZone(3.0,   "overwhelming, chemical soapy",        "negative"),
    ],
    "Aldehyde C12 MNA": [
        CharacterZone(0.05,  "metallic sparkle, amber warmth",      "positive"),
        CharacterZone(0.3,   "amber-metallic, powdery",             "positive"),
        CharacterZone(1.0,   "soapy, laundry",                      "neutral"),
    ],
    "Cyclamen Aldehyde": [
        CharacterZone(0.1,   "green-metallic floral",               "positive"),
        CharacterZone(0.5,   "cucumber, hyacinth",                  "positive"),
        CharacterZone(1.5,   "sharp, chemical, metallic overload",  "negative"),
    ],
    "Hydroxycitronellal": [
        CharacterZone(0.2,   "dewy, fresh linen, transparent",      "positive"),
        CharacterZone(0.8,   "sweet muguet, slightly waxy",         "positive"),
        CharacterZone(2.0,   "soapy, detergent-like",               "neutral"),
        CharacterZone(5.0,   "cloying, chemical laundry",           "negative"),
    ],
    # ── Musks ──
    "Galaxolide": [
        CharacterZone(2.0,   "clean musk, subtle skin",             "positive"),
        CharacterZone(5.0,   "sweet musk, laundry clean",           "positive"),
        CharacterZone(15.0,  "powdery-sweet, slightly synthetic",   "neutral"),
        CharacterZone(30.0,  "overwhelming, headache-inducing",     "negative"),
    ],
    "Ethylene Brassylate": [
        CharacterZone(3.0,   "subtle musk veil, skin-scent",         "positive"),
        CharacterZone(8.0,   "powdery musk, gentle fixative",        "positive"),
        CharacterZone(20.0,  "flat, monotone musk blanket",          "neutral"),
    ],
    "Musk Ketone": [
        CharacterZone(0.5,   "powdery, sweet musk, cosmetic",       "positive"),
        CharacterZone(2.0,   "classic musk, slightly powdery",      "positive"),
        CharacterZone(5.0,   "heavy, nitro-musk character",         "neutral"),
    ],
    # ── Florals ──
    "Hedione": [
        CharacterZone(3.0,   "radiance amplifier, transparent lift", "positive"),
        CharacterZone(10.0,  "jasmine-green, full body",            "positive"),
        CharacterZone(30.0,  "dominant jasmine-hedione character",  "neutral"),
        CharacterZone(50.0,  "overwhelming, loses nuance",          "negative"),
    ],
    "Phenethyl Alcohol": [
        CharacterZone(1.0,   "rose-petal transparency",             "positive"),
        CharacterZone(3.0,   "full rose, honey undertone",          "positive"),
        CharacterZone(8.0,   "yeasty, bread-dough, fermented",      "negative"),
    ],
    # ── Woods ──
    "Iso E Super": [
        CharacterZone(3.0,   "transparent woody veil, skin-scent",  "positive"),
        CharacterZone(8.0,   "molecular cocoon, cedar-amber",       "positive"),
        CharacterZone(20.0,  "dominant abstract-wood, monotone",    "neutral"),
        CharacterZone(40.0,  "flat, loses all other materials",     "negative"),
    ],
    "Cashmeran": [
        CharacterZone(0.5,   "woody-musky warmth, cashmere",        "positive"),
        CharacterZone(2.0,   "dense wood-amber, musky",             "positive"),
        CharacterZone(5.0,   "overwhelming, sweet-chemical",        "negative"),
    ],
    # ── Balsamic / gourmand ──
    "Vanillin": [
        CharacterZone(0.5,   "warm vanilla sweetness",              "positive"),
        CharacterZone(2.0,   "rich vanilla, balsamic",              "positive"),
        CharacterZone(5.0,   "cloying sweet, confectionery",        "neutral"),
        CharacterZone(10.0,  "synthetic, harsh vanilla",            "negative"),
    ],
    "Ethyl Vanillin": [
        CharacterZone(0.3,   "intense vanilla, sweeter than vanillin", "positive"),
        CharacterZone(1.0,   "rich vanilla-cream",                  "positive"),
        CharacterZone(3.0,   "overpowering sweet, chemical",        "negative"),
    ],
    "Coumarin": [
        CharacterZone(0.5,   "tonka-hay transparency",              "positive"),
        CharacterZone(2.0,   "rich coumarinic, tobacco warmth",     "positive"),
        CharacterZone(4.0,   "heavy, slightly bitter",              "neutral"),
    ],
    "Heliotropal": [
                            ],
    # Heliotropal (piperonal): benzodioxole aldehyde, heliotrope-almond-vanilla.
    # At subliminal doses activates OR5A1/OR5A2 → sweet-powdery subliminal warmth.
    # At moderate doses → full heliotrope character. Overdose → cloying powdery-chemical.
    # Lower VP than Heliotropin (less volatile), deeper fixative quality.
    "Heliotropal": [
        CharacterZone(0.5,   "subliminal sweet-almond warmth, powdery depth", "positive"),
        CharacterZone(2.0,   "full heliotrope, cherry-almond, violet-powder", "positive"),
        CharacterZone(5.0,   "dense heliotrope powder, starts to dominate",   "neutral"),
        CharacterZone(10.0,  "cloying sweet-powder, chemical-aldehyde",       "negative"),
    ],
    # ── Terpene alcohols ──
    # Ethyl Linalool (3,7-dimethyl-1,6-octadien-3-ol ethyl ether):
    # Cleaner, sharper than linalool — more transparent, less sweet.
    # At moderate dose: crisp floral-citrus lift. Overdose: chemical-etherish.
    "Ethyl Linalool": [
        CharacterZone(1.0,   "clean citrus-floral, sharper linalool",   "positive"),
        CharacterZone(3.0,   "transparent terpene-ether, floral body",  "positive"),
        CharacterZone(8.0,   "chemical-etherish, loses floral quality", "neutral"),
        CharacterZone(15.0,  "harsh solvent-ether, flat terpenic",      "negative"),
    ],
    # ── Green ──
    "Dynascone": [
        CharacterZone(0.01,  "green galbanum freshness",            "positive"),
        CharacterZone(0.05,  "intense green, stem-like",            "positive"),
        CharacterZone(0.2,   "overwhelming green bomb, harsh",      "dangerous"),
    ],
    "cis-3-Hexenol": [
        CharacterZone(0.1,   "fresh cut grass, natural green",      "positive"),
        CharacterZone(0.5,   "crushed leaves, vegetal",             "positive"),
        CharacterZone(1.5,   "harsh, acetaldehyde-like",            "negative"),
    ],
    # ── Fresh/aquatic terpene alcohols ──
    # Dihydromyrcenol is a hydrated myrcene — at low dose the hydroxyl
    # group drives the percept (clean-citrus-muguet, the Cool Water effect).
    # At overdose or after nose adapts to the fresh topnote, the terpenic
    # hydrocarbon backbone dominates → petroleum/gasoline/paraffin character.
    # Classic "Cool Water gone bad" inversion.
    "Dihydromyrcenol": [
        CharacterZone(1.0,   "clean citrus-muguet lift, lime peel", "positive"),
        CharacterZone(4.0,   "fresh cologne-soapy, lily-of-valley", "positive"),
        CharacterZone(10.0,  "waxy-terpenic, adaptation residual",  "neutral"),
        CharacterZone(20.0,  "petroleum/gasoline hydrocarbon backbone exposed", "negative"),
        CharacterZone(40.0,  "kerosene-paraffin, raw terpenic solvent", "dangerous"),
    ],
    # ── Smoke / leather ──
    "Birch Tar Rectified": [
        CharacterZone(0.02,  "subtle campfire smoke",               "positive"),
        CharacterZone(0.1,   "leather-smoke, Russian leather",      "positive"),
        CharacterZone(0.3,   "overwhelming creosote, tarry",        "dangerous"),
    ],
    # ── Ozonic ──
    "Calone": [
        CharacterZone(0.01,  "watermelon-marine transparency",      "positive"),
        CharacterZone(0.05,  "marine-ozonic, sea breeze",           "positive"),
        CharacterZone(0.2,   "synthetic, harsh melon",              "negative"),
    ],
    "Scentenal": [
        CharacterZone(0.02,  "metallic green ozone, mineral",       "positive"),
        CharacterZone(0.1,   "intense metal-green, unusual",        "positive"),
        CharacterZone(0.3,   "aggressive, headache-inducing",       "negative"),
    ],
    # ── Spice ──
    "Eugenol": [
        CharacterZone(0.1,   "warm spice, clove nuance",           "positive"),
        CharacterZone(0.5,   "clove-spice, dental",                "positive"),
        CharacterZone(1.5,   "dental office, numbing, harsh",      "negative"),
    ],
    # ── Fruity ──
    "Paradisamide": [
        CharacterZone(0.1,   "tropical-fruity modifier, guava",    "positive"),
        CharacterZone(0.5,   "passion fruit, cassis, rhubarb",     "positive"),
        CharacterZone(2.0,   "sulfurous-catty undertone",          "neutral"),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Hill Equation Parameters
# For each material: EC50 (% producing half-max response), n (steepness)
# ═══════════════════════════════════════════════════════════════════════════════

HILL_PARAMS: dict[str, dict[str, float]] = {
    "Indole":              {"EC50": 0.08, "n": 2.5, "Rmax": 1.0},
    "Guaiacol":            {"EC50": 0.05, "n": 3.0, "Rmax": 1.0},
    "Isobutyl Quinoline":  {"EC50": 0.1,  "n": 2.0, "Rmax": 1.0},
    "Aldehyde C10":        {"EC50": 0.2,  "n": 1.5, "Rmax": 1.0},
    "Aldehyde C11":        {"EC50": 0.2,  "n": 1.5, "Rmax": 1.0},
    "Cyclamen Aldehyde":   {"EC50": 0.3,  "n": 1.8, "Rmax": 1.0},
    "Galaxolide":          {"EC50": 5.0,  "n": 1.2, "Rmax": 1.0},
    "Iso E Super":         {"EC50": 5.0,  "n": 1.0, "Rmax": 1.0},
    "Hedione":             {"EC50": 8.0,  "n": 1.0, "Rmax": 1.0},
    "Vanillin":            {"EC50": 2.0,  "n": 1.5, "Rmax": 1.0},
    "Coumarin":            {"EC50": 1.5,  "n": 1.3, "Rmax": 1.0},
    "Dynascone":           {"EC50": 0.03, "n": 3.0, "Rmax": 1.0},
    "Calone":              {"EC50": 0.03, "n": 3.5, "Rmax": 1.0},
    "Scentenal":           {"EC50": 0.05, "n": 2.8, "Rmax": 1.0},
    "Birch Tar Rectified": {"EC50": 0.05, "n": 3.0, "Rmax": 1.0},
    "cis-3-Hexenol":       {"EC50": 0.3,  "n": 1.5, "Rmax": 1.0},
    "Eugenol":             {"EC50": 0.3,  "n": 1.8, "Rmax": 1.0},
    "Phenethyl Alcohol":   {"EC50": 2.0,  "n": 1.2, "Rmax": 1.0},
    "Cashmeran":           {"EC50": 1.5,  "n": 1.5, "Rmax": 1.0},
    "Ethyl Vanillin":      {"EC50": 0.8,  "n": 1.8, "Rmax": 1.0},
    "Paradisamide":        {"EC50": 0.3,  "n": 1.8, "Rmax": 1.0},
    "Hydroxycitronellal":  {"EC50": 0.5,  "n": 1.5, "Rmax": 1.0},
    # Dihydromyrcenol: gradual dose response, relatively high ODT in
    # concentrate terms. EC50 ~3% conc, gentle slope (n=1.2) — why it's
    # used at 5-15% as a workhorse before the hydrocarbon inversion hits.
    "Dihydromyrcenol":     {"EC50": 3.0,  "n": 1.2, "Rmax": 1.0},
    # Heliotropal: moderate sensitivity, gentle slope — sweet materials
    # need higher concentrations to trigger character shift
    "Heliotropal":          {"EC50": 1.5,  "n": 1.5, "Rmax": 1.0},
    # Ethyl Linalool: similar profile to linalool but slightly higher threshold
    "Ethyl Linalool":       {"EC50": 2.0,  "n": 1.3, "Rmax": 1.0},
}


# Validate Hill parameters at module load
for _hp_name, _hp_vals in HILL_PARAMS.items():
    assert 0.5 <= _hp_vals["n"] <= 5.0, (
        f"Hill coefficient n={_hp_vals['n']} for {_hp_name} outside valid range [0.5, 5.0]"
    )
    assert _hp_vals["EC50"] > 0, f"EC50 must be positive for {_hp_name}"
del _hp_name, _hp_vals

# Pre-build normalized indexes for cross-module lookups
from engine.name_utils import normalize_name as _nn
_HILL_INDEX: dict[str, dict[str, float]] = {_nn(k): v for k, v in HILL_PARAMS.items()}
_CHAR_SHIFT_INDEX: dict[str, list[CharacterZone]] = {
    _nn(k): v for k, v in CHARACTER_SHIFT_DATA.items()
}
del _nn


def _hill_response(conc_pct: float, EC50: float, n: float, Rmax: float = 1.0) -> float:
    """Hill equation sigmoid response."""
    if conc_pct <= 0:
        return 0.0
    return Rmax * (conc_pct ** n) / (EC50 ** n + conc_pct ** n)


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DoseResponseReport:
    """Dose-response analysis with character shift detection."""
    score: float                      # 0-100 dosing quality
    overdosed: list[dict[str, Any]]   # materials in negative zone
    optimal: list[dict[str, Any]]     # materials in positive zone
    marginal: list[dict[str, Any]]    # materials in neutral zone
    character_map: dict[str, str]     # material → current character description
    hill_responses: dict[str, float]  # material → sigmoid response level (0-1)
    diagnostics: list[str]


def score_dose_response(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
    total_volume_ul: float = 10000.0,
) -> DoseResponseReport:
    """Score formula dosing quality based on character shift analysis.

    Args:
        ingredients: {name: amount_uL}
        dilutions: {name: dilution_factor} (1.0=neat, 0.1=10%, etc.)
        total_volume_ul: total batch volume in µL (default 10mL)

    Returns:
        DoseResponseReport with dosing quality score and character maps.
    """
    dilutions = dilutions or {}
    overdosed: list[dict] = []
    optimal: list[dict] = []
    marginal: list[dict] = []
    char_map: dict[str, str] = {}
    hill_map: dict[str, float] = {}
    diagnostics: list[str] = []
    penalties = 0.0
    bonuses = 0.0
    material_count = 0

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active_ul = amount * dil
        conc_pct = (active_ul / total_volume_ul) * 100.0

        # Character shift analysis — use normalized index
        from engine.name_utils import normalize_name
        norm = normalize_name(name)
        zones = _CHAR_SHIFT_INDEX.get(norm)
        if zones:
            material_count += 1
            current_char = zones[0].character
            current_quality = zones[0].quality

            for zone in zones:
                if conc_pct <= zone.max_conc_pct:
                    current_char = zone.character
                    current_quality = zone.quality
                    break
            else:
                # Above all defined zones — use the last one
                current_char = zones[-1].character
                current_quality = zones[-1].quality

            char_map[name] = current_char
            info = {
                "material": name,
                "conc_pct": round(conc_pct, 4),
                "character": current_char,
                "quality": current_quality,
            }

            if current_quality == "negative":
                overdosed.append(info)
                penalties += 25      # strong penalty — negative zone = character inversion
            elif current_quality == "dangerous":
                overdosed.append(info)
                penalties += 40      # catastrophic — fecal, kerosene, chemical burn
            elif current_quality == "positive":
                optimal.append(info)
                bonuses += 5
            else:  # neutral
                marginal.append(info)
                penalties += 3       # mild penalty — neutral zones waste material

        # Hill equation response level — use normalized index
        hill = _HILL_INDEX.get(norm)
        if hill:
            response = _hill_response(conc_pct, hill["EC50"], hill["n"], hill["Rmax"])
            hill_map[name] = round(response, 3)

    # Scoring
    if material_count == 0:
        return DoseResponseReport(
            score=75.0, overdosed=[], optimal=[], marginal=[],
            character_map={}, hill_responses={},
            diagnostics=["No dose-response data for formula materials"],
        )

    # Base score from optimal dosing
    opt_ratio = len(optimal) / material_count if material_count > 0 else 0
    base_score = opt_ratio * 70 + 30  # 30-100 range

    # Penalty for overdosing
    score = base_score - penalties + min(bonuses, 20)
    score = max(0, min(100, score))

    # Diagnostics
    if overdosed:
        names = [f"{o['material']} ({o['conc_pct']:.3f}%: {o['character']})"
                 for o in overdosed]
        diagnostics.append(f"⚠ OVERDOSED: {'; '.join(names)}")
    if optimal:
        diagnostics.append(f"✓ {len(optimal)} material(s) in optimal character zone")
    if not overdosed and material_count > 0:
        diagnostics.append("✓ All profiled materials within positive character range")

    # Check for narrow Hill responses (materials near EC50 — character transition)
    transitional = [n for n, r in hill_map.items() if 0.35 < r < 0.65]
    if transitional:
        diagnostics.append(
            f"ℹ Near character-shift boundary: {', '.join(transitional)} — "
            "small dose changes could shift perceived character"
        )

    return DoseResponseReport(
        score=round(score, 1),
        overdosed=overdosed,
        optimal=optimal,
        marginal=marginal,
        character_map=char_map,
        hill_responses=hill_map,
        diagnostics=diagnostics,
    )
