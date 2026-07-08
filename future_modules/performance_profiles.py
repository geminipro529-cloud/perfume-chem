"""Material performance profiles — VP, half-life, substantivity, sillage database.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the performance data from the Formulation Intelligence Database (Part IX).
Each material profile includes:
  - Vapor pressure at 25°C (Pa)
  - Evaporation half-life on skin at 32°C (minutes)
  - Substantivity class
  - Sillage radius
  - Note tier
  - logP (skin binding)
  - Bangkok (35°C) VP correction factor

Also includes fixative physics modeling:
  - Raoult's Law VP suppression
  - logP skin binding depot effect
  - Molecular network caging
  - Hydrogen bonding matrix (benzyl benzoate)

Integrates with FormulaState by providing the physical constants
needed for the headspace OAV calculation chain.

**Note on VP vs. half-life independence:**
Vapor pressure (VP) and evaporation half-life (HL) are independently
determined. VP is a pure-component thermodynamic property at 25°C.
HL is an expert-estimated kinetic value for skin at 32°C that accounts
for skin binding, sebum interaction, and molecular network effects.
They do not obey a simple inverse proportionality — fixing one does
not automatically fix the other. See `calculate_logp_retardation()` and
`estimate_tropical_performance_shift()` for the correction pipeline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from ._shared_types import (
    BANGKOK_VP_RATIO,
    DELTA_H_VAP_DEFAULT,
    NoteTier,
    PerformanceData,
    R_GAS,
    T_BANGKOK,
    T_PARIS,
    T_SKIN,
    clausius_clapeyron_vp_ratio,
    get_note_tier_from_vp,
)


# ---------------------------------------------------------------------------
# Performance database (Part IX)
# ---------------------------------------------------------------------------

PERFORMANCE_DB: tuple[PerformanceData, ...] = (
    PerformanceData("Limonene", 190, 12.5, "Fleeting", "Ambient", NoteTier.TOP, 4.5),
    PerformanceData("Linalool", 15.8, 20, "Short", "Personal", NoteTier.TOP, 2.97),
    PerformanceData("Linalyl Acetate", 17.5, 18, "Short", "Personal", NoteTier.TOP, 3.5),
    PerformanceData("Phenethyl Alcohol", 0.03, 90, "Moderate", "Personal", NoteTier.HEART, 1.36),
    PerformanceData("Hedione", 0.1, 180, "Moderate", "Sillage", NoteTier.HEART, 2.8),
    PerformanceData("Geraniol", 2.12, 55, "Short-moderate", "Personal", NoteTier.HEART, 3.56),
    PerformanceData("Damascenone", 0.693, 120, "Long", "Personal-sillage", NoteTier.HEART, 3.9),
    PerformanceData("Iso E Super", 0.231, 360, "Long", "Sillage-ambient", NoteTier.BASE, 5.3),
    PerformanceData("Javanol", 0.03, 360, "Long", "Personal-sillage", NoteTier.HEART, 3.5),
    PerformanceData("Ambrox Super", 0.05, 600, "Very long", "Intimate-personal", NoteTier.BASE, 5.0),
    PerformanceData("Galaxolide", 0.0001, 900, "Very long", "Personal", NoteTier.BASE, 5.9),
    PerformanceData("Benzyl Benzoate", 0.001, 1080, "Very long", "Intimate", NoteTier.BASE, 3.97),
    PerformanceData("Coumarin", 0.19, 180, "Very long", "Personal", NoteTier.BASE, 1.39),
    PerformanceData("Vanillin", 0.0001, 960, "Very long", "Personal", NoteTier.BASE, 1.21),
    PerformanceData("Dihydromyrcenol", 14.8, 20, "Short-moderate", "Personal-sillage", NoteTier.TOP, 3.0),
    PerformanceData("Benzyl Salicylate", 0.01, 960, "Very long", "Personal", NoteTier.BASE, 4.5),
    PerformanceData("Ambrettolide", 0.0005, 900, "Very long", "Intimate-personal", NoteTier.BASE, 6.8),
    PerformanceData("Habanolide", 0.0003, 840, "Very long", "Personal", NoteTier.BASE, 5.5),
    PerformanceData("Cashmeran", 1.2, 480, "Long", "Intimate-personal", NoteTier.BASE, 4.2),
    PerformanceData("Ethylene Brassylate", 0.008, 900, "Very long", "Personal", NoteTier.BASE, 4.0),
    # --- Pass E: 21 additional materials ---
    PerformanceData("Citronellol", 0.67, 45, "Short-moderate", "Personal", NoteTier.HEART, 3.91),
    PerformanceData("Benzyl Acetate", 0.22, 60, "Moderate", "Personal", NoteTier.HEART, 1.96),
    PerformanceData("Aldehyde C12 MNA", 0.01, 180, "Long", "Personal-sillage", NoteTier.TOP, 4.83),
    PerformanceData("Calone", 0.293, 90, "Short-moderate", "Personal-sillage", NoteTier.HEART, 1.4),
    PerformanceData("Patchouli EO", 0.001, 1080, "Very long", "Intimate", NoteTier.BASE, 4.5),
    PerformanceData("Vetiver EO", 0.003, 960, "Very long", "Intimate", NoteTier.BASE, 4.5),
    PerformanceData("Cedarwood EO", 9.37, 90, "Short-moderate", "Personal", NoteTier.BASE, 4.9),
    PerformanceData("Sandalore", 0.08, 720, "Long", "Personal", NoteTier.BASE, 4.2),
    PerformanceData("Alpha Ionone", 0.02, 240, "Long", "Personal-sillage", NoteTier.HEART, 3.86),
    PerformanceData("Beta Ionone", 7.20, 18, "Short", "Ambient", NoteTier.HEART, 4.42),
    PerformanceData("Methyl Ionone", 0.01, 270, "Long", "Personal-sillage", NoteTier.HEART, 3.8),
    PerformanceData("Eugenol", 0.01, 180, "Long", "Personal-sillage", NoteTier.HEART, 2.49),
    PerformanceData("Ethyl Maltol", 0.001, 240, "Very long", "Personal", NoteTier.HEART, 0.03),
    PerformanceData("Ethyl Vanillin", 0.0002, 900, "Very long", "Personal", NoteTier.BASE, 1.58),
    PerformanceData("Musk Ketone", 0.00001, 1200, "Very long", "Intimate", NoteTier.BASE, 3.0),
    PerformanceData("Exaltolide", 0.0001, 960, "Very long", "Intimate-personal", NoteTier.BASE, 5.3),
    PerformanceData("Rose Oxide", 5.3, 15, "Short", "Personal-sillage", NoteTier.HEART, 3.2),
    PerformanceData("Indole", 0.01, 180, "Long", "Personal-sillage", NoteTier.HEART, 2.14),
    PerformanceData("Cinnamaldehyde", 0.05, 120, "Moderate", "Personal-sillage", NoteTier.HEART, 1.9),
    PerformanceData("Lavender EO", 3.5, 25, "Short", "Personal-sillage", NoteTier.HEART, 2.5),
    PerformanceData("Heliotropin", 0.6, 60, "Short-moderate", "Personal", NoteTier.HEART, 1.05),
)


def get_performance(material_name: str) -> PerformanceData | None:
    """Return performance data for a material by name (case-insensitive)."""
    key = material_name.lower()
    for pd in PERFORMANCE_DB:
        if pd.material.lower() == key:
            return pd
    # Try partial match
    for pd in PERFORMANCE_DB:
        if key in pd.material.lower() or pd.material.lower() in key:
            return pd
    return None


def get_vp(material_name: str) -> float | None:
    """Return vapor pressure at 25°C (Pa) for a material."""
    pd = get_performance(material_name)
    return pd.vp_pa if pd else None


def get_logp(material_name: str) -> float | None:
    """Return logP for a material."""
    pd = get_performance(material_name)
    return pd.logp if pd else None


def get_half_life(material_name: str) -> float | None:
    """Return evaporation half-life on skin at 32°C (minutes)."""
    pd = get_performance(material_name)
    return pd.half_life_min if pd else None


def get_note_tier(material_name: str) -> NoteTier | None:
    """Return note tier for a material."""
    pd = get_performance(material_name)
    return pd.note_tier if pd else None


def list_all_performance() -> tuple[str, ...]:
    """Return all materials with performance data."""
    return tuple(p.material for p in PERFORMANCE_DB)


# ---------------------------------------------------------------------------
# Fixative physics calculations
# ---------------------------------------------------------------------------

def calculate_vp_suppression(
    initial_vp_pa: float,
    fixative_mass_fraction: float,
    fixative_vp_pa: float = 0.0001,
) -> float:
    """Estimate VP reduction due to fixative loading (Raoult's Law approximation).

    Adding low-VP materials reduces the mole fraction of high-VP materials.
    Each 10% of high-MW fixative reduces effective VP of top notes by 5–10%.

    Args:
        initial_vp_pa: VP of the material without fixatives (Pa)
        fixative_mass_fraction: mass fraction of fixatives in the formula (0–1)
        fixative_vp_pa: typical VP of the fixative material (Pa)

    Returns:
        Effective VP after fixative suppression (Pa)
    """
    # Simplified Raoult: effective mole fraction ≈ mass fraction correction
    # Heuristic: each 10% fixative → 7.5% VP reduction
    suppression_factor = 1.0 - fixative_mass_fraction * 0.75
    return initial_vp_pa * max(suppression_factor, 0.1)


def calculate_logp_retardation(
    half_life_min: float,
    logp: float | None,
) -> float:
    """Adjust half-life for skin lipid binding based on logP.

    Materials with logP 3–5 bind strongly to skin lipids, releasing slowly
    over 6–12 hours (depot effect).

    Args:
        half_life_min: base half-life without depot effect
        logp: the material's logP value

    Returns:
        Adjusted half-life accounting for skin binding
    """
    if logp is None:
        return half_life_min

    if logp < 2.0:
        return half_life_min  # no binding
    if logp < 4.0:
        return half_life_min * 1.3
    if logp < 5.0:
        return half_life_min * 1.8
    return half_life_min * 2.5  # logP > 5.0: strong depot


def calculate_hydrogen_bonding_matrix(
    benzyl_benzoate_pct: float,
) -> float:
    """Estimate retention factor from benzyl benzoate hydrogen-bonding matrix.

    Benzyl benzoate at 5–10% of concentrate forms a cohesive matrix
    that retains more volatile materials via hydrogen bonding.

    Returns:
        Multiplier for effective half-life (1.0 = no effect, up to ~1.5)
    """
    if benzyl_benzoate_pct < 3.0:
        return 1.0
    if benzyl_benzoate_pct < 8.0:
        return 1.0 + (benzyl_benzoate_pct - 3.0) / 5.0 * 0.3
    return 1.3  # ceiling


def calculate_molecular_caging(
    galaxolide_pct: float,
    iso_e_super_pct: float,
    ambroxan_pct: float,
) -> float:
    """Estimate molecular network caging from polycyclic fixatives.

    Galaxolide, Iso E Super, and Ambroxan with rigid ring systems create
    molecular networks that trap smaller volatile molecules, slowing release.
    Effect most pronounced for molecules with geometric complementarity.

    Returns:
        Multiplier for effective half-life of top/heart notes (1.0 = no effect)
    """
    caging_mass = galaxolide_pct + iso_e_super_pct * 0.5 + ambroxan_pct * 0.3
    if caging_mass < 5.0:
        return 1.0
    return 1.0 + min(caging_mass / 50.0, 0.5)  # cap at 1.5x


def calculate_effective_half_life(
    material_name: str,
    fixative_mass_fraction: float = 0.0,
    benzyl_benzoate_pct: float = 0.0,
    galaxolide_pct: float = 0.0,
    iso_e_super_pct: float = 0.0,
    ambroxan_pct: float = 0.0,
) -> float | None:
    """Calculate effective half-life factoring in all fixative mechanisms.

    Returns:
        Estimated half-life on skin (minutes) or None if material unknown
    """
    pd = get_performance(material_name)
    if pd is None:
        return None

    base_hl = pd.half_life_min

    # logP skin depot bonus
    depot_hl = calculate_logp_retardation(base_hl, pd.logp)

    # Hydrogen bonding matrix
    hbond_factor = calculate_hydrogen_bonding_matrix(benzyl_benzoate_pct)

    # Molecular caging
    cage_factor = calculate_molecular_caging(galaxolide_pct, iso_e_super_pct, ambroxan_pct)

    # Fixative VP suppression reduces effective half-life of fixatives themselves
    # but extends the half-life of volatile top notes
    if pd.note_tier in (NoteTier.TOP, NoteTier.HEART):
        # Volatiles get extended by caging
        effective = depot_hl * cage_factor * hbond_factor
    else:
        effective = depot_hl

    return effective


def estimate_vp_from_halflife(half_life_min: float) -> float:
    """Rough VP estimate from half-life (inverse relationship heuristic)."""
    if half_life_min <= 0:
        return 200.0
    return 200.0 / (half_life_min ** 0.7)


def get_bangkok_vp(vp_pa: float) -> float:
    """Convert VP from 22°C to Bangkok 35°C using Clausius-Clapeyron."""
    return vp_pa * BANGKOK_VP_RATIO


def get_temperature_adjusted_vp(
    vp_pa: float,
    temp_c: float,
    ref_temp_c: float = 22.0,
    delta_h_vap: float = DELTA_H_VAP_DEFAULT,
) -> float:
    """Adjust vapor pressure to any temperature using Clausius-Clapeyron.

    Args:
        vp_pa: known VP at ref_temp_c
        temp_c: target temperature (°C)
        ref_temp_c: reference temperature (°C) where vp_pa is known
        delta_h_vap: enthalpy of vaporization (J/mol)

    Returns:
        VP at target temperature (Pa)
    """
    if temp_c == ref_temp_c:
        return vp_pa
    ratio = clausius_clapeyron_vp_ratio((ref_temp_c, temp_c), delta_h_vap)
    return vp_pa * ratio


def estimate_tropical_performance_shift(
    material_name: str,
    paris_half_life_min: float | None = None,
) -> dict[str, float] | None:
    """Estimate how a material's performance shifts from Paris (22°C) to Bangkok (35°C).

    Returns:
        dict with bangkok_vp, bangkok_half_life_estimate, vp_ratio, or None
    """
    pd = get_performance(material_name)
    if pd is None:
        return None

    bangkok_vp = get_bangkok_vp(pd.vp_pa)
    # Half-life inversely proportional to VP
    vp_ratio = bangkok_vp / pd.vp_pa
    bangkok_hl = pd.half_life_min / vp_ratio

    return {
        "paris_vp": pd.vp_pa,
        "bangkok_vp": bangkok_vp,
        "vp_ratio": vp_ratio,
        "paris_half_life_min": pd.half_life_min,
        "bangkok_half_life_min_est": bangkok_hl,
    }


# ---------------------------------------------------------------------------
# Fixative loading recommendations
# ---------------------------------------------------------------------------

def recommend_fixative_loading(
    formula_type: str,  # "light_edc", "standard_edp", "high_performance_extrait"
    target_longevity_hours: float = 8.0,
) -> tuple[float, str]:
    """Recommend fixative loading percentage and strategy for a formula type.

    Returns:
        (recommended_fixative_pct, strategy_description)
    """
    from ._shared_types import FIXATIVE_LOADING

    ranges = FIXATIVE_LOADING.get(formula_type, FIXATIVE_LOADING["standard_edp"])
    mid = (ranges[0] + ranges[1]) / 2

    if target_longevity_hours > 12:
        return ranges[1], "Maximum fixative loading — use high-potency bases (Ambroxan, Galaxolide, Benzyl Benzoate)"
    if target_longevity_hours > 8:
        return mid + (ranges[1] - mid) * 0.5, "Above-average fixative loading"
    return mid, "Standard fixative loading"


# ---------------------------------------------------------------------------
# Evaporation timeline estimation
# ---------------------------------------------------------------------------

def estimate_evaporation_timeline(
    materials: Sequence[tuple[str, float]],  # (name, half_life_min)
    top_fade_threshold_min: float = 30.0,
) -> dict[str, float]:
    """Estimate when top, heart, and base phases transition.

    Uses half-life data to predict the evaporation timeline.
    Top phase ends when top note materials fall below 50% of initial.
    Heart phase transitions to base similarly.

    Returns:
        dict with 'top_fade_min', 'heart_fade_min', 'base_persist_min'
    """
    top_hls = []
    heart_hls = []
    base_hls = []

    for name, hl in materials:
        tier = get_note_tier(name)
        if tier == NoteTier.TOP:
            top_hls.append(hl)
        elif tier == NoteTier.HEART:
            heart_hls.append(hl)
        elif tier == NoteTier.BASE:
            base_hls.append(hl)

    # Top fade: when the longest top note drops to threshold
    top_fade = top_fade_threshold_min + (max(top_hls) * 2 if top_hls else 30)

    # Heart fade: longest heart note half-life * 4 (two doublings)
    heart_fade = max(heart_hls) * 4 if heart_hls else 240

    # Base persists: longest base note half-life * 3
    base_persist = max(base_hls) * 3 if base_hls else 720

    return {
        "top_fade_min": top_fade,
        "heart_fade_min": heart_fade,
        "base_persist_min": base_persist,
    }
