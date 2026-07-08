"""Edge cases and exception handling — anosmia, climate, solubility, ghost notes, EO math.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the edge case database from the Formulation Intelligence Database
(Part XII). Handles five categories:

  1. Anosmia Coverage Strategy — population-level anosmia data, 3-class musk rule
  2. Temperature Sensitivity — Clausius-Clapeyron for Bangkok vs Paris
  3. Solubility Risk Materials — cold shipping / winter storage precipitation
  4. Natural EO OAV Math — multi-component logic (character vs mass constituents)
  5. "Ghost Note" Phenomenon — sub-threshold texture materials
  6. Concentration Bracket Calibration — non-linear conversion rules
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from ._shared_types import (
    AnosmiaData,
    BANGKOK_VP_RATIO,
    ConcentrationBracket,
    ConcentrationConversion,
    DELTA_H_VAP_DEFAULT,
    GhostNoteMaterial,
    NaturalEOData,
    R_GAS,
    SolubilityData,
    SolubilityRisk,
    T_BANGKOK,
    T_PARIS,
    T_SKIN,
    clausius_clapeyron_vp_ratio,
)


# ---------------------------------------------------------------------------
# 1. Anosmia Coverage Strategy (Part XII.1)
# ---------------------------------------------------------------------------

ANOSMIA_DATABASE: tuple[AnosmiaData, ...] = (
    AnosmiaData("Androstenone", "OR7D4", 5.0, "True non-detection ~2-6%; apparent ~16-50% (training-dependent); heritable", trainable=True),
    AnosmiaData("Iso E Super", "Multiple ORs", 22.5, "Pending EU allergen labeling; most common synthetic anosmia", trainable=False),
    AnosmiaData("Galaxolide", "OR4D6", 30.0, "M263T and S151T alleles reduce perception; estimated prevalence", trainable=False),
    AnosmiaData("Ambroxan", "OR7A17", 20.0, "Non-functional alleles prevalent in East Asia — critical for Thai market", trainable=False),
    AnosmiaData("Beta-Ionone", "OR51A4", 20.0, "Affects violet/orris perception", trainable=False),
    AnosmiaData("Muscone", "Unknown musk OR", 8.0, "Natural musk-specific anosmia", trainable=False),
    AnosmiaData("Linalool", "Multiple", 5.0, "Low concern — most people perceive linalool normally", trainable=False),
    AnosmiaData("Cashmeran", "Unknown", 12.5, "Estimated prevalence based on musk-class receptor overlap", trainable=False),
    AnosmiaData("Skatole", "Unknown", 30.0, "High variability — some perceive floral, others only fecal", trainable=False),
)


# Musk class coverage requirements
MUSK_CLASS_COVERAGE = {
    "polycyclic": frozenset({"Galaxolide"}),
    "macrocyclic": frozenset({"Habanolide", "Ambrettolide", "Romandolide", "Nirvanolide"}),
    "alicyclic": frozenset({"Ethylene Brassylate", "Muscone"}),
    "terpenic_amber": frozenset({"Ambroxan", "Ambroxide"}),
}


def get_anosmia(material_name: str) -> AnosmiaData | None:
    """Return anosmia data for a material."""
    key = material_name.lower()
    for a in ANOSMIA_DATABASE:
        if a.material.lower() == key:
            return a
    return None


def check_musk_class_coverage(musk_materials: Sequence[str]) -> tuple[bool, list[str]]:
    """Check that a musk blend covers the minimum 3 structural classes.

    Rule: Never rely on a single musk class. Minimum 3 classes
    (polycyclic + macrocyclic + alicyclic/terpenic) to cover > 90% of population.

    Returns:
        (is_adequate, list_of_missing_classes)
    """
    name_set = {m.lower() for m in musk_materials}
    covered = set()

    for class_name, mats in MUSK_CLASS_COVERAGE.items():
        if any(m.lower() in name_set for m in mats):
            covered.add(class_name)

    required = {"polycyclic", "macrocyclic", "alicyclic" if "alicyclic" in covered else "terpenic_amber"}
    missing = [c for c in required if c not in covered and c != "terpenic_amber"]

    # If alicyclic not covered, check terpenic_amber
    if "alicyclic" not in covered and "terpenic_amber" not in covered:
        missing.append("alicyclic_or_terpenic_amber")

    n_classes = len(covered)
    if n_classes >= 3:
        return True, []
    if n_classes >= 2:
        return False, missing
    return False, missing


def estimate_anosmia_coverage(musk_materials: Sequence[str]) -> float:
    """Estimate percentage of population covered by a musk blend.

    Uses independent probability model: P(all undetectable) = product of anosmia rates.

    Returns:
        Estimated population coverage (0-1)
    """
    undetectable_prob = 1.0
    for mat in musk_materials:
        anosmia = get_anosmia(mat)
        if anosmia:
            undetectable_prob *= (anosmia.anosmia_prevalence_pct / 100.0)
        else:
            undetectable_prob *= 0.10  # assume 10% unknown material anosmia

    return 1.0 - undetectable_prob


def thai_market_check(musk_materials: Sequence[str], ambroxan_present: bool) -> dict[str, str]:
    """Check formula suitability for the Thai (East Asian ancestry) market.

    Key concern: Ambroxan anosmia ~20% in East Asian populations (OR7A17).
    """
    warnings: dict[str, str] = {}
    if ambroxan_present:
        warnings["ambroxan_east_asian"] = (
            "Ambroxan non-functional alleles (~20% in East Asian populations) may cause "
            "5-20% of Thai consumers to miss the amber-skin note. Supplement with "
            "Habanolide, Ethylene Brassylate, and Iso E Super."
        )
    coverage_result, missing = check_musk_class_coverage(musk_materials)
    if not coverage_result:
        warnings["musk_coverage"] = f"Musk classes missing: {', '.join(missing)}. Target > 90% population coverage."
    return warnings


# ---------------------------------------------------------------------------
# 2. Temperature Sensitivity (Part XII.2)
# ---------------------------------------------------------------------------

def clausius_clapeyron_factor(
    temp_c: float,
    ref_temp_c: float = 22.0,
    delta_h_vap: float = DELTA_H_VAP_DEFAULT,
) -> float:
    """VP ratio at temperature vs reference using Clausius-Clapeyron.

    For Bangkok (35°C) vs Paris (22°C): factor ≈ 2.8x.
    """
    return clausius_clapeyron_vp_ratio((ref_temp_c, temp_c), delta_h_vap)


def estimate_evaporation_acceleration(
    temp_c: float,
    ref_temp_c: float = 22.0,
) -> dict[str, float]:
    """Estimate how evaporation rates accelerate at a given temperature.

    Returns:
        dict with 'vp_ratio' and 'effective_time_ratio'
    """
    ratio = clausius_clapeyron_factor(temp_c, ref_temp_c)
    return {
        "vp_ratio": ratio,
        "effective_time_ratio": 1.0 / ratio,  # time is inversely proportional
        "temp_c": temp_c,
        "ref_temp_c": ref_temp_c,
    }


def tropical_base_loading_correction(
    paris_base_pct: float,
    temp_c: float = 35.0,
) -> float:
    """Calculate required base loading increase for tropical climates.

    Rule: For Bangkok (35°C, 80% RH), increase base loading by 2-3x
    relative to temperate EdP design.
    """
    factor = clausius_clapeyron_factor(temp_c)
    if factor <= 1.0:
        return paris_base_pct
    # Scale: 2.8x VP → ~2.5x base correction
    return paris_base_pct * min(factor * 0.9, 3.0)


def humidity_effects(rel_humidity_pct: float) -> dict[str, str]:
    """Assess high-humidity effects on fragrance materials.

    Returns:
        dict of material types → effect description
    """
    effects = {}
    if rel_humidity_pct > 70:
        effects["light_acetates"] = "Water-reactive esters hydrolyze faster at high RH"
        effects["hygroscopic"] = "Vanillin, coumarin, ethyl maltol may absorb moisture — affects perceived concentration"
        effects["sweat_ph"] = "Sweat pH ~4.5-6 accelerates some reactions; formulate for pH stability"
    return effects


# ---------------------------------------------------------------------------
# 3. Solubility Risk Materials (Part XII.3)
# ---------------------------------------------------------------------------

COLD_SHIPPING_RISKS: tuple[SolubilityData, ...] = (
    SolubilityData(
        "Coumarin", "Precipitates below 2% in EtOH", 5.0,
        "Use 5-10% benzyl benzoate or IPM as co-solvent",
        "Benzyl benzoate 5-10%",
        risk=SolubilityRisk.MEDIUM,
    ),
    SolubilityData(
        "Vanillin", "Precipitates below 5% in EtOH", 5.0,
        "Pre-dissolve in DPG; use 10-15% DPG as co-solvent",
        "DPG 10-15%",
        risk=SolubilityRisk.MEDIUM,
    ),
    SolubilityData(
        "Oranger Crystals", "Precipitates below 1% without co-solvent", 20.0,
        "5% benzyl benzoate co-solvent required",
        "5% benzyl benzoate",
        risk=SolubilityRisk.HIGH,
    ),
    SolubilityData(
        "Ethyl Maltol", "Precipitates below 0.5% over time", 20.0,
        "10-15% DPG as co-solvent",
        "DPG 10-15%",
        risk=SolubilityRisk.HIGH,
    ),
    SolubilityData(
        "Musk Ketone", "Precipitates below 1% in EtOH", 5.0,
        "5-15% DPG as co-solvent",
        "DPG 5-15%",
        risk=SolubilityRisk.MEDIUM,
    ),
)


def check_solubility_risk(
    material_name: str,
    concentration_pct: float,
    storage_temp_c: float = 5.0,
) -> tuple[SolubilityRisk, str]:
    """Check if a material is at risk of precipitation at given storage temperature.

    Returns:
        (risk_level, guidance)
    """
    key = material_name.lower()
    for risk in COLD_SHIPPING_RISKS:
        if risk.material.lower() == key and risk.precipitation_temp_c is not None:
            if storage_temp_c <= risk.precipitation_temp_c:
                return risk.risk, f"Precipitation risk at {storage_temp_c}°C: {risk.solubility_in_etoh_96}. {risk.recommended_stock}."
    return SolubilityRisk.NONE, ""


# ---------------------------------------------------------------------------
# 4. Natural EO OAV Math (Part XII.4)
# ---------------------------------------------------------------------------

NATURAL_EO_DATA: tuple[NaturalEOData, ...] = (
    NaturalEOData(
        "Bergamot EO", "Limonene", 40.0,
        "Linalool", 0.51,
        "When calculating Bergamot OAV, use linalool ODT (0.51 ppb), not limonene ODT (~10 ppm)",
    ),
    NaturalEOData(
        "Grapefruit EO", "Limonene", 90.0,
        "1-p-Menthene-8-thiol", 3.4e-5,
        "Grapefruit mercaptan is the sole character-defining compound despite < 0.0001 ppb in fruit",
    ),
    NaturalEOData(
        "Lemon EO", "Limonene", 60.0,
        "Citral", 0.5,
        "Citral is the character-defining molecule — ODT ~0.5 ppb in air",
    ),
    NaturalEOData(
        "Lavender EO (40/42)", "Linalool", 40.0,
        "Linalool", 0.51,
        "Character is linalool-driven; linalyl acetate at 42% adds freshness but linalool defines",
    ),
)


def get_eo_character_constituent(eo_name: str) -> NaturalEOData | None:
    """Return the character-defining constituent for a natural EO."""
    key = eo_name.lower()
    for eo in NATURAL_EO_DATA:
        if eo.eo_name.lower() == key:
            return eo
    return None


def calculate_eo_oav(
    eo_name: str,
    eo_concentration_ppm: float,
) -> tuple[float, str] | None:
    """Calculate the character-based OAV for a natural EO.

    Uses the character-defining constituent's ODT, NOT the mass-dominant
    constituent's ODT.

    Returns:
        (oav, explanation) or None if EO unknown
    """
    eo = get_eo_character_constituent(eo_name)
    if eo is None:
        return None

    # Approximate: the character constituent's concentration in the EO
    # For bergamot: linalool is ~11-14% → use 12%
    constituent_pct = {
        "bergamot eo": 12.0,
        "grapefruit eo": 0.000001,  # trace mercaptan
        "lemon eo": 3.0,
        "lavender eo (40/42)": 40.0,
    }.get(eo_name.lower(), 10.0)

    constituent_ppm = eo_concentration_ppm * (constituent_pct / 100.0)
    # Convert ppb air ODT to ppm
    odt_ppm = eo.character_constituent_odt_ppb / 1000.0
    if odt_ppm <= 0:
        return float("inf"), f"Zero ODT for {eo.character_defining_constituent}"

    oav = constituent_ppm / odt_ppm
    return oav, (
        f"{eo_name}: character calculated using {eo.character_defining_constituent} "
        f"(ODT {eo.character_constituent_odt_ppb} ppb), not {eo.mass_dominant_constituent} "
        f"({eo.mass_dominant_pct:.0f}% mass)"
    )


# ---------------------------------------------------------------------------
# 5. "Ghost Note" Phenomenon (Part XII.5)
# ---------------------------------------------------------------------------

GHOST_NOTE_MATERIALS: tuple[GhostNoteMaterial, ...] = (
    GhostNoteMaterial(
        "Hedione", "OR2G2 activation at sub-OAV-1 concentrations",
        "background radiance texture", "OR2G2",
    ),
    GhostNoteMaterial(
        "Iso E Super", "Multiple OR activation — woody skin-warmth texture even when unidentifiable",
        "woody skin-warmth texture", None,
    ),
    GhostNoteMaterial(
        "Ambroxan", "OR7A17 activation — amber-skin texture below identification threshold",
        "amber-skin texture", "OR7A17",
    ),
    GhostNoteMaterial(
        "Ultralia", "Atmospheric veil — spatial texture rather than character",
        "atmospheric veil texture", None,
    ),
    GhostNoteMaterial(
        "Floralozone", "Transparent overlay — functions as spatial texture",
        "transparent overlay texture", None,
    ),
)


def get_ghost_note(material_name: str) -> GhostNoteMaterial | None:
    """Return ghost-note data for a material."""
    key = material_name.lower()
    for gn in GHOST_NOTE_MATERIALS:
        if gn.material.lower() == key:
            return gn
    return None


def is_ghost_note_material(material_name: str) -> bool:
    """Check if a material is a known ghost-note (sub-threshold texture) material."""
    return get_ghost_note(material_name) is not None


# ---------------------------------------------------------------------------
# 6. Concentration Bracket Calibration (Part XII.6)
# ---------------------------------------------------------------------------

CONCENTRATION_CONVERSIONS: tuple[ConcentrationConversion, ...] = (
    ConcentrationConversion(
        ConcentrationBracket.EXTRAIT, ConcentrationBracket.EDP,
        "Reduce base loading ~20%; increase heart ~10%; keep top similar",
        base_adjustment_pct=-20, heart_adjustment_pct=10, top_adjustment_pct=0,
    ),
    ConcentrationConversion(
        ConcentrationBracket.EDP, ConcentrationBracket.EDT,
        "Increase heart loading 20%; base notes approach sub-threshold — reinforce with higher-potency bases",
        base_adjustment_pct=30, heart_adjustment_pct=20, top_adjustment_pct=0,
    ),
    ConcentrationConversion(
        ConcentrationBracket.EDT, ConcentrationBracket.EDC,
        "Base notes sub-threshold. Add 2-3× base loading or use ultra-potent bases (Ambroxan, Ambrette). Top notes dominate",
        base_adjustment_pct=200, heart_adjustment_pct=0, top_adjustment_pct=0,
    ),
)


def get_concentration_conversion(
    from_bracket: ConcentrationBracket,
    to_bracket: ConcentrationBracket,
) -> ConcentrationConversion | None:
    """Return conversion rules between two concentration brackets."""
    for conv in CONCENTRATION_CONVERSIONS:
        if conv.from_bracket == from_bracket and conv.to_bracket == to_bracket:
            return conv
    return None


def adjust_for_concentration(
    ingredient_pct: float,  # % of ingredient in concentrate
    from_bracket: ConcentrationBracket,
    to_bracket: ConcentrationBracket,
    note_tier: str,  # "top", "heart", "base"
) -> float:
    """Adjust an ingredient's percentage when converting concentration brackets.

    Non-linearity note: Activity coefficients shift with concentration.
    OAV ratios at 40% are not the same as at 10% even after proportional
    dilution — this function provides a first-order correction.
    """
    conv = get_concentration_conversion(from_bracket, to_bracket)
    if conv is None:
        # Fallback: simple dilution ratio
        if from_bracket in (ConcentrationBracket.EXTRAIT,) and to_bracket == ConcentrationBracket.EDP:
            return ingredient_pct * 0.5
        if from_bracket == ConcentrationBracket.EDP and to_bracket == ConcentrationBracket.EDT:
            return ingredient_pct * 0.4
        return ingredient_pct

    adjustment = 0.0
    if note_tier == "top":
        adjustment = conv.top_adjustment_pct
    elif note_tier == "heart":
        adjustment = conv.heart_adjustment_pct
    elif note_tier == "base":
        adjustment = conv.base_adjustment_pct

    return ingredient_pct * (1.0 + adjustment / 100.0)


def candle_compatibility(material_vp_pa: float) -> bool:
    """Check if a material is suitable for candle use.

    Only materials with VP 0.01-100 Pa reach candle headspace.
    Materials VP < 0.005 Pa never reach the headspace.
    """
    return 0.005 <= material_vp_pa <= 150.0
