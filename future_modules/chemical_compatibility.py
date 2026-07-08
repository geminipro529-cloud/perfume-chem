"""Chemical compatibility matrix — reactive pair detection and stability checking.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the chemical reaction database from the Formulation Intelligence Database
(Part VIII). Detects known reactive pairs in a formula and provides mitigation
strategies for each reaction type:

  - Schiff base (aldimine) formation: aldehydes + primary amines
  - Acetal formation: aldehydes + ethanol
  - Ester hydrolysis: esters + water (pH-dependent)
  - Terpene autoxidation: limonene, pinenes + O2
  - Phenol oxidation: vanillin, eugenol, guaiacol + O2
  - Photo-oxidation: expressed citrus EOs + UV
  - Transesterification: multiple esters + ethanol
  - Polymerization: farnesol, geraniol (conjugated dienes)

Used to validate formula composition before maceration and to compute
over-dosing strategies for known degradation pathways.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ._shared_types import ChemicalReaction, CompatibilityReport, SolubilityRisk


# ---------------------------------------------------------------------------
# Reaction database
# ---------------------------------------------------------------------------

CHEMICAL_REACTIONS: tuple[ChemicalReaction, ...] = (
    ChemicalReaction(
        reaction_type="Schiff base (aldimine)",
        materials_involved_1="aldehydes",
        materials_involved_2="methyl anthranilate",
        rate_at_25c="Days–weeks",
        products="Imine (higher MW, lower VP)",
        smell_change="Shifts to brown-floral-orange",
        color_change="Yellow-brown",
        mitigation="Never combine; use methyl anthranilate in separate phase or omit",
    ),
    ChemicalReaction(
        reaction_type="Acetal formation",
        materials_involved_1="aldehydes C10/C11/C12",
        materials_involved_2="ethanol",
        rate_at_25c="Weeks–months",
        products="Acetal (less volatile, softer)",
        smell_change="Softer, longer-lasting, less sharp",
        color_change="None",
        mitigation="Pre-formulate in solvent; dose 40–60% excess at T=0 to account for loss",
    ),
    ChemicalReaction(
        reaction_type="Ester hydrolysis",
        materials_involved_1="benzyl acetate, linalyl acetate",
        materials_involved_2="water (pH < 5 or > 8)",
        rate_at_25c="Months",
        products="Free acid + alcohol",
        smell_change="Loss of fruity-floral esters",
        color_change="None",
        mitigation="Buffer to pH 5.5–7; minimize water; anhydrous ethanol",
    ),
    ChemicalReaction(
        reaction_type="Terpene autoxidation",
        materials_involved_1="limonene, alpha-pinene",
        materials_involved_2="O2",
        rate_at_25c="Weeks (accelerated by light)",
        products="Hydroperoxides, epoxides",
        smell_change="Off-notes, rancid, phototoxic products",
        color_change="None",
        mitigation="BHT/tocopherol 0.01–0.05%; UV-protected packaging; N2 headspace",
    ),
    ChemicalReaction(
        reaction_type="Phenol oxidation",
        materials_involved_1="vanillin, eugenol, guaiacol",
        materials_involved_2="O2",
        rate_at_25c="Weeks–months",
        products="Quinones (brown colored)",
        smell_change="Off-character, darkening",
        color_change="Dark brown",
        mitigation="Antioxidant; pH < 7; nitrogen headspace",
    ),
    ChemicalReaction(
        reaction_type="Photo-oxidation",
        materials_involved_1="expressed citrus EOs (bergamot, lime)",
        materials_involved_2="UV light",
        rate_at_25c="Days (sunlight)",
        products="Hydroperoxides; phototoxic bergaptens released",
        smell_change="Rancid, off-notes",
        color_change="Yellow",
        mitigation="Amber glass; UV absorber (octocrylene 0.1%); FCF-stripped bergamot; max 1 year shelf life",
    ),
    ChemicalReaction(
        reaction_type="Transesterification",
        materials_involved_1="multiple esters",
        materials_involved_2="ethanol",
        rate_at_25c="Months",
        products="Mixed esters",
        smell_change="Subtle character shift",
        color_change="None",
        mitigation="Minimize ester diversity; accept gracefully in multi-ester formulas",
    ),
    ChemicalReaction(
        reaction_type="Polymerization",
        materials_involved_1="farnesol, geraniol",
        materials_involved_2="conjugated dienes",
        rate_at_25c="Months",
        products="Dimers, oligomers",
        smell_change="Heavier, less volatile",
        color_change="Possible",
        mitigation="Antioxidant; cool storage; 5°C if possible",
    ),
)


# ---------------------------------------------------------------------------
# Material classification for reactivity checking
# ---------------------------------------------------------------------------

# Materials that are known aldehydes
_ALDEHYDE_MATERIALS: frozenset[str] = frozenset({
    "aldehyde c10", "aldehyde c11", "aldehyde c12 mna",
    "aldehyde c10 (decanal)", "aldehyde c11 (undecanal)",
    "aldehyde c12 lauric", "cinnamal", "citral",
    "citronellal", "hydroxycitronellal", "lilial",
    "amyl cinnamal", "cyclamen aldehyde",
    "c10 aldehyde", "c11 aldehyde", "c12 aldehyde",
})

# Materials containing primary amine groups (methyl anthranilate is the main risk)
_AMINE_MATERIALS: frozenset[str] = frozenset({
    "methyl anthranilate", "anthranilate",
})

# Materials susceptible to phenol oxidation
_PHENOLIC_MATERIALS: frozenset[str] = frozenset({
    "vanillin", "eugenol", "guaiacol", "isoeugenol",
    "ethyl vanillin", "maltol", "ethyl maltol",
})

# Materials susceptible to terpene autoxidation
_TERPENE_MATERIALS: frozenset[str] = frozenset({
    "limonene", "d-limonene", "alpha-pinene", "beta-pinene",
    "bergamot", "lemon eo", "orange eo", "grapefruit eo",
    "lime eo", "mandarin eo",
})

# Ester materials
_ESTER_MATERIALS: frozenset[str] = frozenset({
    "benzyl acetate", "linalyl acetate", "benzyl benzoate",
    "benzyl salicylate", "isoamyl salicylate", "geranyl acetate",
    "citronellyl acetate", "phenylethyl acetate", "vetiver acetate",
    "vetivenyl acetate", "ethyl phenylacetate",
})

# Conjugated diene materials
_DIENE_MATERIALS: frozenset[str] = frozenset({
    "farnesol", "geraniol", "nerol",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_formula_compatibility(
    material_names: Sequence[str],
    uses_ethanol: bool = True,
    contains_water: bool = False,
    ph_value: float = 6.0,
) -> CompatibilityReport:
    """Check a formula composition for known chemical incompatibilities.

    Args:
        material_names: list of material names in the formula
        uses_ethanol: formula is in ethanol solution (default True)
        contains_water: formula contains water
        ph_value: estimated pH of the formula

    Returns:
        CompatibilityReport with detected risks and overall grade
    """
    name_set = {n.lower() for n in material_names}

    # Check for Schiff base risk
    has_aldehyde = any(a in name_set for a in _ALDEHYDE_MATERIALS)
    has_amine = any(a in name_set for a in _AMINE_MATERIALS)
    schiff_base_risk = has_aldehyde and has_amine

    # Check for oxidation risks
    has_terpenes = any(t in name_set for t in _TERPENE_MATERIALS)
    has_phenolics = any(p in name_set for p in _PHENOLIC_MATERIALS)
    oxidation_risk = has_terpenes or has_phenolics

    # Check for hydrolysis risk
    has_esters = any(e in name_set for e in _ESTER_MATERIALS)
    hydrolysis_risk = has_esters and (contains_water or (ph_value < 5.0 or ph_value > 8.0))

    # Check for color stability
    has_dienes = any(d in name_set for d in _DIENE_MATERIALS)
    color_stability_risk = has_phenolics  # phenol → quinone darkening

    # Collect specific reactive pairs
    reactive_pairs: list[ChemicalReaction] = []
    if schiff_base_risk:
        reactive_pairs.append(CHEMICAL_REACTIONS[0])  # Schiff base
    if has_aldehyde and uses_ethanol:
        reactive_pairs.append(CHEMICAL_REACTIONS[1])  # Acetal formation
    if has_terpenes:
        reactive_pairs.append(CHEMICAL_REACTIONS[3])  # Terpene autoxidation
    if has_phenolics:
        reactive_pairs.append(CHEMICAL_REACTIONS[4])  # Phenol oxidation
    if has_dienes:
        reactive_pairs.append(CHEMICAL_REACTIONS[7])  # Polymerization
    if hydrolysis_risk:
        reactive_pairs.append(CHEMICAL_REACTIONS[2])  # Ester hydrolysis

    # Overall risk grade
    risk_count = len(reactive_pairs)
    if schiff_base_risk:
        overall = SolubilityRisk.HIGH  # reuse for chemical risk
    elif risk_count >= 3:
        overall = SolubilityRisk.MEDIUM
    elif risk_count >= 1:
        overall = SolubilityRisk.LOW
    else:
        overall = SolubilityRisk.NONE

    return CompatibilityReport(
        reactive_pairs=tuple(reactive_pairs),
        schiff_base_risk=schiff_base_risk,
        oxidation_risk=oxidation_risk,
        hydrolysis_risk=hydrolysis_risk,
        color_stability_risk=color_stability_risk,
        overall_risk=overall,
    )


def detect_schiff_base_risk(material_names: Sequence[str]) -> bool:
    """Return True if the formula combines aldehydes with primary amines."""
    name_set = {n.lower() for n in material_names}
    has_aldehyde = any(a in name_set for a in _ALDEHYDE_MATERIALS)
    has_amine = any(a in name_set for a in _AMINE_MATERIALS)
    return has_aldehyde and has_amine


def detect_oxidation_risk(material_names: Sequence[str]) -> tuple[str, ...]:
    """Return list of oxidation-prone material categories found in the formula."""
    name_set = {n.lower() for n in material_names}
    risks = []
    if any(t in name_set for t in _TERPENE_MATERIALS):
        risks.append("terpene_autoxidation")
    if any(p in name_set for p in _PHENOLIC_MATERIALS):
        risks.append("phenol_oxidation")
    if any(d in name_set for d in _DIENE_MATERIALS):
        risks.append("polymerization")
    return tuple(risks)


def get_reaction(reaction_type: str) -> ChemicalReaction | None:
    """Return a specific chemical reaction by its type name."""
    for rxn in CHEMICAL_REACTIONS:
        if rxn.reaction_type.lower() == reaction_type.lower():
            return rxn
    return None


def get_mitigation(reaction_type: str) -> str | None:
    """Return the mitigation strategy for a reaction type."""
    rxn = get_reaction(reaction_type)
    return rxn.mitigation if rxn else None


def get_all_reactions() -> tuple[ChemicalReaction, ...]:
    """Return all known chemical reactions."""
    return CHEMICAL_REACTIONS


def classify_material_reactivity(
    material_name: str,
) -> dict[str, bool]:
    """Classify a single material's chemical reactivity risks."""
    key = material_name.lower()
    return {
        "is_aldehyde": key in _ALDEHYDE_MATERIALS,
        "is_amine": key in _AMINE_MATERIALS,
        "is_phenolic": key in _PHENOLIC_MATERIALS,
        "is_terpene": key in _TERPENE_MATERIALS,
        "is_ester": key in _ESTER_MATERIALS,
        "is_diene": key in _DIENE_MATERIALS,
    }
