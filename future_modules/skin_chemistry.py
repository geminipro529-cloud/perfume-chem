"""Skin chemistry as active formulation variable.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the skin chemistry intelligence from the Advanced Perfumery Supplement
(Gap 3). Skin is not an inert substrate — pH, sebum, sweat, and hormonal state
all affect fragrance performance. This module provides:

  - Skin pH effects on fragrance character (acid mantle 4.5–6.5)
  - Sebum/skin lipid depot effect (logP-dependent retention)
  - Dry vs oily skin formulation rules
  - Thai (Southeast Asian) skin formulation strategy
  - Hormonal variation effects (estrogen, progesterone, cortisol)
  - Material selection by logP for skin-type optimization
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Skin type profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SkinTypeProfile:
    """Fragrance behavior on a specific skin type."""
    skin_type: str
    ph_range: tuple[float, float]
    sebum_level: str             # low, moderate, high
    top_note_behavior: str
    heart_note_behavior: str
    base_note_behavior: str
    formulation_recommendations: tuple[str, ...]
    best_concentration: str      # recommended bracket


SKIN_TYPE_PROFILES: tuple[SkinTypeProfile, ...] = (
    SkinTypeProfile(
        "normal", (4.8, 5.5), "moderate",
        "Balanced evaporation — top notes project 20–30 minutes",
        "Heart notes develop fully at 15–45 minutes",
        "Base notes last 6–10 hours depending on fixative loading",
        ("Standard pyramid ratios work well", "No special adjustment needed"),
        "EdT or EdP",
    ),
    SkinTypeProfile(
        "oily", (4.5, 5.0), "high",
        "Slightly faster opening (acid pH sharpens aldehydes and citrus)",
        "Extended heart duration — sebum lipid matrix retards evaporation",
        "Enhanced longevity 30–60% for logP 3–5 materials; the fragrance 'depot' in skin lipids acts as sustained-release reservoir",
        (
            "Use heavily on logP 3–5 base materials (Iso E Super, Galaxolide, Ambroxan)",
            "Reduce top note loading — they will appear sharper from acid pH",
            "EdP concentration works best — the lipid matrix extends low-VP materials",
            "Avoid over-loading light esters — acid pH increases hydrolysis risk",
        ),
        "EdP or Extrait",
    ),
    SkinTypeProfile(
        "dry", (5.0, 6.5), "low",
        "Rapid absorption — top notes collapse faster; evaporation accelerated",
        "Heart notes may register weakly — no lipid matrix to retard release",
        "Base notes may register weakly — rapid skin absorption pulls materials deep",
        (
            "Heavier base loading required — 2× standard fixative percentage",
            "Use EdP or Extrait concentration — EdT will disappear too fast",
            "Pre-application: unscented moisturizer 30 minutes before fragrance (creates artificial lipid layer)",
            "Focus on high-MW, low-VP materials with good substantivity",
            "Benzyl Benzoate at 5–10% of concentrate as cohesive matrix",
        ),
        "Extrait or high-concentration EdP",
    ),
    SkinTypeProfile(
        "sensitive", (5.0, 5.8), "low-to-moderate",
        "Variable — depends on specific sensitivity triggers",
        "Heart notes may read more prominently (fewer competing lipid interactions)",
        "IFRA sensitizer limits must be strictly observed",
        (
            "Avoid known dermal sensitizers at any concentration",
            "Reduce aldehyde loading — sensitive skin reacts more",
            "Test on inner elbow for 24 hours before full application",
            "Use hypoallergenic musk classes (macrocyclic, alicyclic preferred)",
        ),
        "EdP (lower concentration = lower sensitizer load)",
    ),
)


# ---------------------------------------------------------------------------
# Thai / Southeast Asian skin profile
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ThaiSkinProfile:
    """Formulation strategy for Thai/Southeast Asian skin (moderate sebum, slight acidity, heat)."""
    typical_ph: float = 5.1                # pH 4.8–5.4
    sebum_production: str = "moderate (increases in heat)"
    sweat_production: str = "increased (35°C ambient)"
    skin_temp_c: float = 35.0

    net_effects: str = (
        "1. Higher sebum production in heat → enhanced logP 3–5 material depot "
        "(Iso E Super, Galaxolide, Ambroxan bind most strongly). "
        "2. Sweat production increases → aqueous microenvironment forms → "
        "some ester hydrolysis risk for light acetates. "
        "3. Higher skin temperature → VP ×2.8 for top notes, but depot effect "
        "partially compensates for logP > 4 bases."
    )

    rule: str = (
        "Focus base loading on logP 4–5 materials (Iso E Super logP 5.3, "
        "Galaxolide logP 5.9, Ambroxan logP ~5.0) — these bind most strongly "
        "to tropical-warm sebum-rich skin. Avoid reliance on logP < 2 base "
        "materials (Vanillin logP 1.21, Coumarin logP 1.39) in high-sweat "
        "conditions — they will partition into aqueous sweat rather than skin lipids."
    )

    preferred_base_materials: tuple[str, ...] = (
        "Iso E Super (logP 5.3)", "Galaxolide (logP 5.9)", "Ambroxan (logP ~5.0)",
        "Ambrettolide (logP ~4.5)", "Habanolide (logP ~5.5)", "Norlimbanol (logP ~5.0)",
        "Benzyl Benzoate (logP 3.97)", "Cashmeran (logP ~4.5)", "Vertofix Coeur (logP ~4.5)",
    )

    avoid_base_materials: tuple[str, ...] = (
        "Vanillin (logP 1.21 — partitions into sweat)", "Coumarin (logP 1.39 — partitions into sweat)",
        "Ethyl Maltol (logP ~1.5 — sweat-soluble)", "Maltol (low logP)",
    )


THAI_SKIN = ThaiSkinProfile()


# ---------------------------------------------------------------------------
# pH effect on materials (rules)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PhEffectRule:
    """How skin pH affects a specific class of fragrance materials."""
    material_class: str
    acid_ph_effect: str       # pH 4.5–5.0
    neutral_ph_effect: str    # pH 5.5–6.5
    formulation_implication: str


PH_EFFECTS: tuple[PhEffectRule, ...] = (
    PhEffectRule(
        "Aldehydes (C10, C11, C12)",
        "Acetal equilibrium shifts toward free aldehyde → brighter, sharper opening; aldehydes appear more prominent",
        "Acetal formation favored → softer, rounder aldehydic character",
        "For acid skin: reduce aldehyde loading 20% below standard; for neutral: standard dosage",
    ),
    PhEffectRule(
        "Citrus EOs (terpenes)",
        "Bright, sharp citrus character accentuated; limonene oxidation slightly accelerated",
        "Rounded, softer citrus; terpenes less reactive",
        "Acid skin: add BHT 0.05% to compensate for faster oxidation",
    ),
    PhEffectRule(
        "Esters (benzyl acetate, linalyl acetate)",
        "Relatively stable at acid pH; hydrolysis rate minimal below pH 5.0",
        "Slightly elevated hydrolysis risk at pH > 6.0; ester character may soften over time",
        "Buffer formula to pH 5.5–6.0 for optimal ester stability",
    ),
    PhEffectRule(
        "Florals (PEA, geraniol, citronellol)",
        "Standard floral character; no significant pH interaction",
        "Florals appear softer and rounder; base notes read more distinctly",
        "No pH adjustment needed for florals alone",
    ),
    PhEffectRule(
        "Musks (polycyclic, macrocyclic)",
        "Musk base reads clean and defined; no pH interaction",
        "Musks read softer but longer-lasting due to reduced competition from top notes",
        "No pH adjustment needed for musks",
    ),
    PhEffectRule(
        "Coumarin, Vanillin",
        "Standard sweetness; no significant pH interaction",
        "Coumarin and vanillin more prominent on neutral-to-alkaline skin (less acid competition)",
        "For neutral skin: consider reducing vanillin 10% relative to acid-skin target",
    ),
    PhEffectRule(
        "Animalics (indole, skatole, castoreum)",
        "Acid pH slightly suppresses animalic notes — reads cleaner",
        "Animalic notes more prominent at neutral pH",
        "For acid skin: dose animalics at standard; for neutral: reduce 10–20% if animalic character unwanted",
    ),
)


# ---------------------------------------------------------------------------
# Sebum / lipid depot model
# ---------------------------------------------------------------------------

def estimate_sebum_depot_factor(
    logp: float,
    sebum_level: str,  # "low", "moderate", "high"
) -> float:
    """Estimate longevity multiplier from skin lipid binding.

    Materials with logP 3–5 bind strongly to skin lipids (sebum),
    creating a sustained-release depot effect.

    Args:
        logp: material logP
        sebum_level: "low", "moderate", or "high"

    Returns:
        Multiplier for effective half-life on skin (1.0 = no effect)
    """
    # Base logP depot effect
    if logp < 2.0:
        base_multiplier = 1.0  # no binding
    elif logp < 3.0:
        base_multiplier = 1.2
    elif logp < 4.0:
        base_multiplier = 1.5
    elif logp < 5.0:
        base_multiplier = 2.0
    else:
        base_multiplier = 2.5

    # Sebum level modulation
    sebum_mods = {"low": 0.6, "moderate": 1.0, "high": 1.4}
    sebum_factor = sebum_mods.get(sebum_level, 1.0)

    return 1.0 + (base_multiplier - 1.0) * sebum_factor


def recommend_logp_strategy(
    skin_type: str,  # "normal", "oily", "dry", "sensitive", "thai"
    note_tier: str,  # "top", "heart", "base"
) -> tuple[float, float]:
    """Return recommended logP range for a skin type and note tier.

    Returns:
        (min_logp, max_logp) recommended range
    """
    strategies: dict[str, dict[str, tuple[float, float]]] = {
        "normal": {
            "top": (1.0, 4.5), "heart": (1.0, 5.0), "base": (1.0, 6.0),
        },
        "oily": {
            "top": (1.0, 4.5), "heart": (2.0, 5.5), "base": (3.5, 6.0),
        },
        "dry": {
            "top": (1.0, 4.5), "heart": (1.0, 4.5), "base": (3.0, 5.5),
        },
        "thai": {
            "top": (1.0, 4.5), "heart": (2.0, 5.5), "base": (4.0, 6.0),
        },
    }
    return strategies.get(skin_type, strategies["normal"]).get(note_tier, (1.0, 6.0))


# ---------------------------------------------------------------------------
# Hormonal context effects
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HormonalContext:
    """Fragrance perception shifts due to hormonal state."""
    phase: str
    hormone_profile: str
    odt_shift: str                # how ODT changes
    perceptual_effect: str
    formulation_implication: str


HORMONAL_CONTEXTS: tuple[HormonalContext, ...] = (
    HormonalContext(
        "Estrogen peak (follicular phase)",
        "High estrogen, low progesterone",
        "ODT decreases 20–40% — heightened olfactory sensitivity",
        "Florals perceived more intensely; subtle nuances more detectable; fragrance seems 'stronger'",
        "Mass-market formulas: design for this context so fragrance is not overwhelming at peak sensitivity",
    ),
    HormonalContext(
        "Progesterone dominance (luteal phase)",
        "High progesterone, falling estrogen",
        "ODT increases 10–25% — reduced sensitivity",
        "Base notes relatively more prominent; top notes may seem 'absent'; fragrance seems 'weaker'",
        "Niche formulas: heavier base character designs work better in this phase",
    ),
    HormonalContext(
        "Stress (high cortisol)",
        "Elevated cortisol, increased perspiration",
        "ODT variable — anxiety increases, attention to scent decreases",
        "Sweat pH drops (more acidic) → esters hydrolyze faster; animalic materials amplified; 'sweaty' character enhanced",
        "Avoid high ester loading for stress-context formulas; animalics read stronger than intended",
    ),
    HormonalContext(
        "Rest/relaxation (low cortisol)",
        "Parasympathetic dominant",
        "ODT at baseline",
        "All note tiers perceived at intended levels; ideal evaluation context",
        "Professional evaluation should occur in this state",
    ),
)


# ---------------------------------------------------------------------------
# Skin preparation (pre-application)
# ---------------------------------------------------------------------------

SKIN_PREPARATION_GUIDE: tuple[tuple[str, str], ...] = (
    ("Unscented moisturizer (30 min before)", "Creates artificial lipid layer for dry skin; enhances logP 3–5 material depot by 30-50%"),
    ("Clean, dry skin", "Optimal baseline — no competing lipids, no interfering pH products"),
    ("Avoid scented lotion", "Scented lotions add competing OAV — 3-5× mixture suppression on fragrance perception"),
    ("Avoid antiperspirant on application site", "Aluminum salts alter skin pH and can react with fragrance aldehydes"),
    ("Warm skin (after shower)", "Dilated pores + increased blood flow enhance diffusion and projection"),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_skin_profile(skin_type: str) -> SkinTypeProfile | None:
    """Return skin type profile by name."""
    for sp in SKIN_TYPE_PROFILES:
        if sp.skin_type == skin_type:
            return sp
    return None


def get_thai_skin_profile() -> ThaiSkinProfile:
    """Return the Thai/Southeast Asian skin formulation profile."""
    return THAI_SKIN


def get_ph_effect(material_class: str) -> PhEffectRule | None:
    """Return pH effect rule for a material class."""
    for pe in PH_EFFECTS:
        if pe.material_class.lower() == material_class.lower():
            return pe
    return None


def get_hormonal_context(phase: str) -> HormonalContext | None:
    """Return hormonal context profile by phase name."""
    for hc in HORMONAL_CONTEXTS:
        if phase.lower() in hc.phase.lower():
            return hc
    return None


def formulate_for_skin_type(
    skin_type: str,
    formula_base_pct: float = 25.0,
) -> dict[str, str]:
    """Return formulation adjustments for a specific skin type.

    Returns a dict of category → adjustment instruction.
    """
    profile = get_skin_profile(skin_type)
    if profile is None:
        return {"general": "No special adjustment needed"}

    return {
        "concentration": profile.best_concentration,
        "top_note_strategy": profile.top_note_behavior,
        "base_loading": "Standard" if skin_type == "normal" else "Increased 1.5-2×" if skin_type == "dry" else "Focus on logP 3-5",
        "recommendations": "; ".join(profile.formulation_recommendations),
    }


def thai_base_material_score(
    material_name: str,
    logp: float | None = None,
) -> tuple[str, float]:
    """Score a base material's suitability for Thai tropical skin.

    Returns:
        (rating, score 0-1)
    """
    if logp is None:
        # Use known values
        known = {
            "iso e super": 5.3, "galaxolide": 5.9, "ambroxan": 5.0,
            "ambrettolide": 4.5, "habanolide": 5.5, "norlimbanol": 5.0,
            "benzyl benzoate": 3.97, "cashmeran": 4.5, "vertofix coeur": 4.5,
            "vanillin": 1.21, "coumarin": 1.39, "ethyl maltol": 1.5,
            "hedione": 2.8, "linalool": 2.97, "geraniol": 3.56,
        }
        logp = known.get(material_name.lower())

    if logp is None:
        return ("unknown", 0.5)

    if logp >= 4.5:
        return ("excellent — strong sebum binding, climate-stable", 1.0)
    if logp >= 3.5:
        return ("good — moderate sebum binding", 0.75)
    if logp >= 2.5:
        return ("acceptable — limited sebum binding, moderate sweat risk", 0.5)
    if logp >= 2.0:
        return ("poor — partitions into sweat, not recommended for Thai skin base", 0.25)
    return ("avoid — will be lost through sweat at tropical temperatures", 0.0)
