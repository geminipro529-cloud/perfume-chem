"""Professional blending protocol — mixing sequence, temperature control, solvent matrix.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the professional blending intelligence from the Advanced Perfumery
Supplement (Gap 12). The order of material addition matters: solubility, VP,
and reaction potential all depend on the concentration matrix at the moment
of addition. This module provides:

  - 8-step professional mixing sequence for 10g concentrate
  - Schiff base prevention strategy
  - Temperature control during mixing
  - Solubility matrix principles
  - Material category sequencing rationale
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# ---------------------------------------------------------------------------
# Professional mixing sequence
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MixingStep:
    """One step in the professional mixing sequence."""
    order: int
    category: str
    materials: str
    rationale: str


MIXING_SEQUENCE: tuple[MixingStep, ...] = (
    MixingStep(
        1, "Solvent / co-solvent matrix",
        "DPG, Benzyl Benzoate, IPM (if used as co-solvents)",
        "Creates the solubility and viscosity foundation. Largest-volume component first establishes the matrix in which everything else dissolves. Benzyl Benzoate functions as a hydrogen-bonding cohesive agent.",
    ),
    MixingStep(
        2, "Musks and fixatives",
        "Galaxolide, Habanolide, macrolides, Ambrettolide, Ethylene Brassylate",
        "Low VP, high logP materials form the molecular cage (fixative) before volatile materials are added. Musks in the matrix minimize headspace loss during subsequent additions.",
    ),
    MixingStep(
        3, "Principal heart materials",
        "Hedione, Iso E Super, Ambroxan, Benzyl Salicylate",
        "Mid-VP materials that form the diffusion platform. Added early so they are homogeneously distributed in the fixative matrix before character materials.",
    ),
    MixingStep(
        4, "Floral anchors",
        "PEA, Geraniol, Citronellol, Rose/Jasmine Absolute (if applicable)",
        "Character-defining florals benefit from the existing musk-fixative-heart matrix. Floral molecules are stable in the intermediate-VP environment.",
    ),
    MixingStep(
        5, "Woody/resin materials",
        "Patchouli, Labdanum, Benzoin, Vetiver, Cedarwood, Sandalwood",
        "High-MW resinous/woody materials integrate into the base matrix. Labdanum and benzoin (viscous) should be pre-warmed to 40°C. Measure by weight, not volume.",
    ),
    MixingStep(
        6, "Citrus and fresh top notes",
        "Bergamot FCF, Linalool, Linalyl Acetate, Lemon EO, Orange EO, Dihydromyrcenol",
        "High-VP materials added after the base matrix is complete — the heavy base partially suppresses immediate volatilization. Top notes in a completed base matrix lose less to headspace during mixing.",
    ),
    MixingStep(
        7, "Reactive/potent materials",
        "Aldehydes (C10/C11/C12), Indole dilution, IBQ dilution, Calone dilution, Geosmin dilution, Damascenone dilution",
        "Added LAST to the fully dilute matrix to prevent high-concentration reactions. If aldehydes are added early at high concentration, acetal formation begins immediately and maximally.",
    ),
    MixingStep(
        8, "Primary amines (if any)",
        "Methyl Anthranilate (ALWAYS last, if used at all)",
        "Maximum separation from aldehydes to minimize Schiff base formation time. If aldehydes and methyl anthranilate contact at high concentration early in mixing, the carbonyl-amine condensation rate is maximized. Adding MA last to a dilute aldehyde matrix minimizes this.",
    ),
)


# ---------------------------------------------------------------------------
# Temperature control
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TemperatureRule:
    """Temperature control rule for fragrance blending."""
    rule: str
    max_temp_c: float
    rationale: str


TEMPERATURE_RULES: tuple[TemperatureRule, ...] = (
    TemperatureRule(
        "General mixing temperature", 30.0,
        "Heat accelerates ALL reactions (Schiff base, acetal formation, terpene oxidation, ester hydrolysis). Keep below 30°C throughout mixing for formula stability.",
    ),
    TemperatureRule(
        "Solid dissolution (coumarin, vanillin, ethyl maltol)", 40.0,
        "If heat is required to dissolve solid materials, warm the specific material + co-solvent SEPARATELY, then cool to room temperature before adding to the main formula. Never heat the entire batch.",
    ),
    TemperatureRule(
        "Reactive material addition", 25.0,
        "The formula should be at or below 25°C when aldehydes and primary amines are added. Lower temperature = slower reaction rate = longer formula stability window.",
    ),
    TemperatureRule(
        "Viscous material warming", 40.0,
        "Labdanum Absolute, Benzoin Resinoid, Styrax, Tolu Balsam: pre-warm individual containers to 40°C before measuring. Measure by weight (not volume) at the warmed temperature.",
    ),
)


# ---------------------------------------------------------------------------
# Schiff base prevention
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SchiffBasePrevention:
    """Strategy for preventing Schiff base formation in aldehyde + amine formulas."""
    description: str = (
        "Schiff base (aldimine) formation occurs when aldehydes (carbonyl) react with "
        "primary amines (Methyl Anthranilate, Indole in trace). The reaction produces "
        "imines with higher MW and lower VP, shifting the odor character to brown-floral-orange "
        "and creating yellow-brown discoloration."
    )
    prevention_rules: tuple[str, ...] = (
        "Add aldehydes LAST (Step 7), Methyl Anthranilate ABSOLUTE LAST (Step 8)",
        "Aldehydes at dilute concentration in the full matrix react slower than concentrated aldehydes added early",
        "If using both aldehydes and MA: consider formulating without MA and adding it as a separate component",
        "Alternatively: pre-dissolve aldehydes in ethanol separately; pre-dissolve MA in DPG separately; combine only in final dilute matrix",
        "Once Schiff base has formed (yellow-brown color change), the reaction is irreversible — the formula is permanently altered",
    )
    incompatible_pairs: tuple[tuple[str, str], ...] = (
        ("Aldehyde C10", "Methyl Anthranilate"),
        ("Aldehyde C11", "Methyl Anthranilate"),
        ("Aldehyde C12 MNA", "Methyl Anthranilate"),
        ("Aldehyde C12 Lauric", "Methyl Anthranilate"),
        ("Hydroxycitronellal", "Methyl Anthranilate"),
        ("Citral", "Methyl Anthranilate"),
    )


SCHIFF_BASE_PREVENTION = SchiffBasePrevention()


# ---------------------------------------------------------------------------
# Solvent matrix principles
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SolventMatrixGuide:
    """Guide for selecting the optimal co-solvent matrix."""
    principle: str = (
        "The co-solvent matrix (DPG, Benzyl Benzoate, IPM, TEC) serves three functions: "
        "1. Solubility — prevents precipitation of solid materials at low temperatures "
        "2. Cohesion — Benzyl Benzoate specifically forms a hydrogen-bonding matrix that retains volatiles "
        "3. Viscosity control — DPG and IPM provide workable viscosity for uniform mixing"
    )
    solvent_recommendations: tuple[tuple[str, str, str], ...] = (
        ("Benzyl Benzoate", "5–15% of concentrate", "Best all-purpose co-solvent + cohesive agent; IFRA max 4.8% in finished product"),
        ("DPG (Dipropylene Glycol)", "5–20% of concentrate", "Good general-purpose solvent; slightly heavier than BB; good for vanillin/coumarin"),
        ("IPM (Isopropyl Myristate)", "3–10% of concentrate", "Light solvent; good for citrus and fresh formulas where BB would be too heavy"),
        ("TEC (Triethyl Citrate)", "3–10% of concentrate", "Citrate ester solvent; 'greener' alternative; good musk solvent"),
    )
    matrix_rules: tuple[str, ...] = (
        "Minimum 5% total co-solvent for any formula containing > 5% solid materials",
        "Benzyl Benzoate at 5–10% for formulas targeting > 6 hour longevity",
        "Avoid > 20% total co-solvent — the formula will feel diluted and under-performing",
        "For all-citrus formulas: use IPM or TEC instead of BB (BB weight clashes with citrus freshness)",
    )


SOLVENT_MATRIX = SolventMatrixGuide()


# ---------------------------------------------------------------------------
# Post-mixing protocol
# ---------------------------------------------------------------------------

POST_MIXING_PROTOCOL: tuple[tuple[str, str], ...] = (
    ("Rest period", "Let the mixed concentrate rest for 24 hours at room temperature before adding ethanol. This allows the molecular network to stabilize."),
    ("Ethanol addition", "Add ethanol slowly with gentle swirling. Never shake vigorously — this introduces oxygen and accelerates oxidation."),
    ("Nitrogen headspace", "If available, displace the bottle headspace with nitrogen gas (N2) before capping. This prevents terpene autoxidation during maceration."),
    ("Dark storage", "Store in amber glass in a dark cabinet. UV light accelerates photo-oxidation of citrus oils and terpenes."),
    ("Temperature during maceration", "Store at 15–22°C for optimal maceration. Below 5°C: solids may precipitate. Above 30°C: all reactions accelerate."),
    ("BHT / antioxidant", "For formulas containing > 5% citrus EOs or terpenes: add BHT 0.01–0.05% or tocopherol 0.02–0.1% as antioxidant at the mixing stage."),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_mixing_sequence() -> tuple[MixingStep, ...]:
    """Return the 8-step professional mixing sequence."""
    return MIXING_SEQUENCE


def get_mixing_step(order: int) -> MixingStep | None:
    """Return a specific mixing step by order number."""
    for step in MIXING_SEQUENCE:
        if step.order == order:
            return step
    return None


def get_temperature_rules() -> tuple[TemperatureRule, ...]:
    """Return all temperature control rules."""
    return TEMPERATURE_RULES


def get_schiff_base_prevention() -> SchiffBasePrevention:
    """Return the Schiff base prevention strategy."""
    return SCHIFF_BASE_PREVENTION


def check_aldehyde_amine_conflict(material_names: Sequence[str]) -> bool:
    """Return True if the formula contains both aldehydes and primary amines."""
    aldehydes = {"aldehyde c10", "aldehyde c11", "aldehyde c12 mna", "aldehyde c12 lauric",
                 "hydroxycitronellal", "citral", "citronellal", "cyclamen aldehyde",
                 "amyl cinnamal", "cinnamal", "c10 aldehyde", "c11 aldehyde", "c12 aldehyde"}
    amines = {"methyl anthranilate", "anthranilate"}
    names = {n.lower() for n in material_names}
    has_aldehyde = bool(names & aldehydes)
    has_amine = bool(names & amines)
    return has_aldehyde and has_amine


def get_solvent_matrix_guide() -> SolventMatrixGuide:
    """Return the solvent matrix selection guide."""
    return SOLVENT_MATRIX


def get_post_mixing_protocol() -> tuple[tuple[str, str], ...]:
    """Return the post-mixing handling protocol."""
    return POST_MIXING_PROTOCOL


def recommend_solvent_mix(
    has_solids: bool = False,
    has_citrus_dominant: bool = False,
    target_longevity_hours: float = 8.0,
) -> tuple[str, float]:
    """Recommend the best co-solvent and loading for a formula.

    Returns:
        (solvent_name, recommended_pct_of_concentrate)
    """
    if has_citrus_dominant:
        return ("IPM", 5.0)
    if target_longevity_hours > 8:
        return ("Benzyl Benzoate", 10.0)
    if has_solids:
        return ("DPG", 10.0)
    return ("Benzyl Benzoate", 7.0)
