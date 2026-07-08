"""Quantified accord recipe library.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the quantified accord recipes from the Formulation Intelligence Database
(Part V). Each accord is a materializable dataclass with:
  - Named materials at specific parts ratios
  - Character dimension scores (0-10)
  - Aggregate hedonic score
  - Integration guidance (typical use % in EdP)

Accords can be materialized into ingredient dicts for direct use in pipeline
construction, or used as reference targets for formula evaluation.

Key accords:
  1. Grojsman Accord (Trésor backbone)
  2. Classic Jasmine Accord
  3. Post-IFRA Chypre Backbone
  4. Fougère Backbone
  5. Lactonic Cream Accord
  6. Tobacco Accord
  7. Mineral / Stone / Petrichor
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from ._shared_types import AccordRecipe, FragranceFamily


# ---------------------------------------------------------------------------
# Accord definitions
# ---------------------------------------------------------------------------

GROJSMAN_ACCORD = AccordRecipe(
    name="Grojsman Accord",
    family=None,  # universal backbone, used across families
    description="Trésor backbone by Sofia Grojsman (IFF). The universal modern floral-musk backbone.",
    materials=(
        ("Galaxolide 50% DEP", 25),
        ("Hedione", 20),
        ("Iso E Super", 15),
        ("Methyl Ionone (gamma)", 12),
        ("PEA (Phenylethyl Alcohol)", 10),
        ("Geraniol", 8),
        ("Citronellol", 10),
    ),
    character={
        "warmth": 5, "sweetness": 4, "freshness": 5,
        "powdery": 6, "radiance": 8, "woody": 4,
        "floral": 6, "transparency": 8,
    },
    hedonic=4.0,
    total_parts=100,
    typical_use_pct=15.0,
)

CLASSIC_JASMINE_ACCORD = AccordRecipe(
    name="Classic Jasmine Accord",
    family=FragranceFamily.FLORAL_JASMINE,
    description="Photorealistic jasmine reconstruction based on GC analysis of Jasmine grandiflorum absolute (India).",
    materials=(
        ("Benzyl Acetate", 45),
        ("Hedione", 25),
        ("Benzyl Benzoate", 12),
        ("Linalool", 8),
        ("Indole (10% DPG)", 3),   # = 0.3% pure indole
        ("Methyl Benzoate", 3),
        ("Cis-Jasmone", 2),
        ("Methyl Anthranilate", 1),
        ("Jasmine Absolute", 1),
    ),
    character={
        "warmth": 4, "sweetness": 5, "freshness": 4,
        "radiance": 7, "floral": 9, "green": 3,
        "animalic": 2,
    },
    hedonic=4.5,
    total_parts=100,
    typical_use_pct=20.0,
)

POST_IFRA_CHYPRE_BACKBONE = AccordRecipe(
    name="Post-IFRA Chypre Backbone",
    family=FragranceFamily.CHYPRE,
    description="Modern chypre backbone compliant with IFRA 51st Amendment — replaces oakmoss with Evernyl, Clearwood, Ambroxan.",
    materials=(
        ("Bergamot FCF", 200),
        ("Patchouli EO (Clearwood)", 40),
        ("Labdanum Absolute", 30),
        ("Oakmoss Absolute", 4),       # keep below 0.1% in finished product
        ("Evernyl (Veramoss)", 15),
        ("Rose Absolute", 10),
        ("Ambroxan", 15),
        ("Habanolide", 20),
        ("Galaxolide 50%", 20),
        ("Iso E Super", 25),
    ),
    character={
        "warmth": 6, "freshness": 3, "powdery": 5,
        "woody": 7, "floral": 4, "smoky": 5,
        "animalic": 2, "radiance": 5,
    },
    hedonic=4.0,
    total_parts=379,
    typical_use_pct=30.0,
)

FOUGERE_BACKBONE = AccordRecipe(
    name="Fougère Backbone",
    family=FragranceFamily.AROMATIC_FOUGERE,
    description="Classic fougère backbone based on the Fougère Royale (Houbigant 1882) template. First synthetic molecule in perfumery = coumarin.",
    materials=(
        ("Lavender EO (40/42 standardized)", 280),
        ("Bergamot FCF", 160),
        ("Geranium EO", 100),
        ("Coumarin", 50),
        ("Oakmoss Absolute", 10),      # IFRA max 0.1% finished
        ("Tonka Bean Absolute", 10),
        ("Iso E Super", 10),
        ("Ambroxan", 10),
        ("Galaxolide 50%", 20),
        ("Musk mix", 20),              # Habanolide + Ethylene Brassylate
    ),
    character={
        "warmth": 5, "freshness": 7, "green": 6,
        "floral": 4, "powdery": 4, "aromatic": 8,
        "radiance": 5,
    },
    hedonic=4.0,
    total_parts=670,
    typical_use_pct=25.0,
)

LACTONIC_CREAM_ACCORD = AccordRecipe(
    name="Lactonic Cream Accord",
    family=FragranceFamily.GOURMAND,
    description="Creamy, milky, peachy-coconut accord for gourmand and floral-gourmand contexts.",
    materials=(
        ("Gamma-Octalactone", 20),
        ("Gamma-Decalactone", 25),
        ("Delta-Decalactone", 15),
        ("Coumarin", 10),
        ("Vanillin", 8),
        ("Ambrettolide", 12),
        ("Methyl Laitone", 10),
    ),
    character={
        "warmth": 6, "sweetness": 7, "freshness": 2,
        "creamy": 8, "radiance": 3, "transparency": 3,
    },
    hedonic=3.5,
    total_parts=100,
    typical_use_pct=10.0,
)

TOBACCO_ACCORD = AccordRecipe(
    name="Tobacco Accord",
    family=FragranceFamily.AMBER_ORIENTAL,
    description="Dried tobacco leaf accord with coumarin, labdanum, benzoin, and smoky guaiacol.",
    materials=(
        ("Coumarin", 25),
        ("Labdanum Absolute", 20),
        ("Benzoin Resinoid", 15),
        ("Tonka Bean Absolute", 10),
        ("Hay Absolute", 5),
        ("Guaiacol (10% DPG)", 5),     # = 0.5% pure guaiacol
        ("Isoamyl Salicylate", 5),
        ("Ethyl Maltol", 3),
    ),
    character={
        "warmth": 8, "sweetness": 5, "smoky": 6,
        "powdery": 4, "radiance": 3, "transparency": 2,
    },
    hedonic=3.5,
    total_parts=88,
    typical_use_pct=12.0,
)

MINERAL_PETRICHOR_ACCORD = AccordRecipe(
    name="Mineral / Stone / Petrichor",
    family=FragranceFamily.WOODY_AMBER,
    description="Rain-on-stone, geological freshness. Geosmin-driven accord with woody-mineral texture.",
    materials=(
        ("Geosmin (0.1% in DPG)", 1),  # extreme potency — dose carefully
        ("Iso E Super", 20),
        ("Ambroxan", 8),
        ("Ultralia", 5),
        ("Vetiver EO (Haitian)", 10),
        ("Cashmeran", 5),
    ),
    character={
        "warmth": 3, "freshness": 4, "green": 5,
        "woody": 5, "radiance": 4, "transparency": 6,
        "earthy": 8,
    },
    hedonic=3.0,
    total_parts=49,
    typical_use_pct=8.0,
)


# ---------------------------------------------------------------------------
# Gap 6 Additional Accords — from Advanced Perfumery Supplement
# ---------------------------------------------------------------------------

ALDEHYDIC_FLORAL_ACCORD = AccordRecipe(
    name="Aldehydic Floral Accord (Chanel No.5 style)",
    family=FragranceFamily.FLORAL_ROSE,
    description="Chanel No.5-style aldehydic floral: abstract metallic overlay on jasmine-rose-ylang with orris-sandalwood skin dimension. Three aldehyde quartet at 0.2% pure each.",
    materials=(
        ("Linalool", 50),
        ("Benzyl Acetate", 120),
        ("Aldehyde C10 (10% dilution)", 20),
        ("Aldehyde C11 (10% dilution)", 10),
        ("Aldehyde C12 MNA (10% dilution)", 10),
        ("Ylang Ylang EO", 35),
        ("PEA (Phenylethyl Alcohol)", 50),
        ("Hydroxycitronellal", 20),
        ("Methyl Ionone Gamma", 50),
        ("Jasmine Absolute", 30),
        ("Rose Absolute", 10),
        ("Coumarin", 50),
        ("Benzyl Salicylate", 100),
        ("Galaxolide 50%", 40),
        ("Habanolide", 20),
        ("Sandalwood / Javanol", 50),
        ("DPG (diluent)", 285),
    ),
    character={
        "warmth": 6, "sweetness": 5, "freshness": 4,
        "powdery": 7, "radiance": 7, "floral": 8,
        "transparency": 5, "soapy": 6,
    },
    hedonic=4.5,
    total_parts=1000,
    typical_use_pct=25.0,
)

PHOTOREALISTIC_ROSE_ACCORD = AccordRecipe(
    name="Photorealistic Rose Accord",
    family=FragranceFamily.FLORAL_ROSE,
    description="8-material photorealistic rose based on rose oil composition (PEA:citronellol:geraniol = 1:35:20 in EO, 13-23:2:1 in absolute). Hybrid of EO and absolute character.",
    materials=(
        ("PEA (Phenylethyl Alcohol)", 300),
        ("Citronellol", 200),
        ("Geraniol", 100),
        ("Nerol", 50),
        ("Beta-Damascenone (0.1% dilution)", 30),
        ("Rose Oxide (1% dilution)", 10),
        ("Eugenol", 10),
        ("Rhodinol", 50),
        ("Rose Absolute", 50),
        ("Benzyl Salicylate", 100),
        ("Coumarin", 30),
        ("Habanolide", 70),
    ),
    character={
        "warmth": 5, "sweetness": 6, "freshness": 4,
        "floral": 9, "radiance": 5, "green": 2,
        "spicy": 1, "creamy": 4,
    },
    hedonic=4.5,
    total_parts=1000,
    typical_use_pct=20.0,
)

GREEN_ACCORD = AccordRecipe(
    name="Green Accord (Galbanum + Violet Leaf)",
    family=FragranceFamily.FLORAL_ROSE,
    description="Precision green accord: galbanum is 3-5× more powerful than juniper and lime. Ratio is critical — OAV miscalculation by 2× makes galbanum bitter-medicinal instead of beautiful green.",
    materials=(
        ("Galbanum EO", 11),
        ("Violet Leaf Absolute", 5),
        ("cis-3-Hexenol", 15),
        ("cis-3-Hexenyl Acetate", 20),
        ("Parmavert", 10),
        ("Undecavertol", 8),
        ("Lime EO", 52),
        ("Juniper Berry EO", 35),
    ),
    character={
        "warmth": 2, "freshness": 8, "green": 9,
        "floral": 3, "woody": 3, "radiance": 5,
        "transparency": 7,
    },
    hedonic=3.5,
    total_parts=156,
    typical_use_pct=8.0,
)

SYNTHETIC_OUD_ACCORD = AccordRecipe(
    name="Synthetic Oud Accord",
    family=FragranceFamily.WOODY_AMBER,
    description="Professional synthetic oud accord: Cypriol + IBQ + Cashmeran + Guaiacwood as smoky-woody core. Para-cresol at trace (<0.05%) provides authentic barnyard character. Supplement with real Agarwood EO if available.",
    materials=(
        ("Cypriol EO (Nagarmotha)", 25),
        ("IBQ (Isobutyl Quinoline) 10%", 5),
        ("Cashmeran", 10),
        ("Guaiacwood EO", 15),
        ("Virginian Cedar EO", 15),
        ("Ambrocenide", 8),
        ("Kephalis", 10),
        ("Ebanol (Sandalore)", 8),
        ("Patchouli EO", 5),
        ("Para-Cresol 1%", 3),         # = 0.03% pure
        ("Benzyl Acetone", 5),
        ("Olibanum Resinoid", 10),
        ("Ambroxan", 10),
        ("Vetivert EO", 8),
        ("Coumarin", 3),
        ("Birch Tar 10%", 2),          # = 0.02% pure
    ),
    character={
        "warmth": 7, "smoky": 8, "woody": 7,
        "animalic": 4, "radiance": 3, "freshness": 1,
        "spicy": 4,
    },
    hedonic=3.0,
    total_parts=142,
    typical_use_pct=12.0,
)

MUGUET_ACCORD = AccordRecipe(
    name="Muguet (Lily of the Valley) Accord",
    family=FragranceFamily.FLORAL_ROSE,
    description="Professional muguet accord: Hydroxycitronellal + Bourgeonal + Cyclamen Aldehyde as core. Bourgeonal IFRA Cat4 max 0.05% in finished product — potent sensitizer and OR1D2 agonist.",
    materials=(
        ("Hydroxycitronellal", 300),
        ("Linalool", 100),
        ("Bourgeonal (Lily Aldehyde)", 50),
        ("Cyclamen Aldehyde", 80),
        ("Koavone / Liffarome (if available)", 30),
        ("Calone", 3),
        ("Hedione", 100),
        ("Adoxal", 20),
        ("Methyl Ionone Gamma", 30),
        ("Galaxolide 50%", 100),
        ("Habanolide", 60),
        ("Benzyl Salicylate", 100),
        ("Ambroxan", 27),
    ),
    character={
        "warmth": 4, "freshness": 7, "green": 5,
        "floral": 8, "radiance": 7, "transparency": 6,
        "powdery": 5, "sweetness": 3,
    },
    hedonic=4.0,
    total_parts=1000,
    typical_use_pct=20.0,
)

VIOLET_IRIS_ACCORD = AccordRecipe(
    name="Violet/Iris Accord (Ionone Triangle)",
    family=FragranceFamily.FLORAL_ROSE,
    description="Professional ionone-based violet/iris: the ionone triangle (γ-MIG + α-Ionone + β-Ionone) creates 3D violet at 3 different distances. γ-MIG dominates at personal distance, α-Ionone at sillage, β-Ionone skin-intimate.",
    materials=(
        ("Methyl Ionone Gamma Coeur", 400),
        ("Alpha Ionone", 150),
        ("Bergamot EO", 120),
        ("Galaxolide 50%", 85),
        ("Helvetolide", 85),
        ("Hydroxycitronellal", 68),
        ("Helional", 34),
        ("Sweet Cassie Absolute", 30),
        ("Anisic Aldehyde", 25),
        ("Undecavertol", 17),
        ("Heliotrope X / Heliotropex", 17),
        ("Beta Ionone", 15),
        ("Koavone / Liffarome (if available)", 10),
        ("Violiff (if available)", 8),
        ("PEA (Phenylethyl Alcohol)", 8),
        ("Benzaldehyde", 1.7),
        ("Vanillin", 1.7),
        ("Aldehyde C12", 1.7),
    ),
    character={
        "warmth": 6, "powdery": 8, "floral": 7,
        "freshness": 4, "radiance": 6, "woody": 4,
        "sweetness": 5, "green": 3,
    },
    hedonic=4.5,
    total_parts=1077,
    typical_use_pct=20.0,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_ACCORDS: tuple[AccordRecipe, ...] = (
    GROJSMAN_ACCORD,
    CLASSIC_JASMINE_ACCORD,
    POST_IFRA_CHYPRE_BACKBONE,
    FOUGERE_BACKBONE,
    LACTONIC_CREAM_ACCORD,
    TOBACCO_ACCORD,
    MINERAL_PETRICHOR_ACCORD,
    ALDEHYDIC_FLORAL_ACCORD,
    PHOTOREALISTIC_ROSE_ACCORD,
    GREEN_ACCORD,
    SYNTHETIC_OUD_ACCORD,
    MUGUET_ACCORD,
    VIOLET_IRIS_ACCORD,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_accord(name: str) -> AccordRecipe | None:
    """Return an accord recipe by name (case-insensitive)."""
    for accord in ALL_ACCORDS:
        if accord.name.lower() == name.lower():
            return accord
    return None


def list_accords() -> tuple[str, ...]:
    """Return the names of all available accord recipes."""
    return tuple(a.name for a in ALL_ACCORDS)


def list_accords_by_family(family: FragranceFamily) -> tuple[AccordRecipe, ...]:
    """Return accords associated with a specific fragrance family."""
    return tuple(a for a in ALL_ACCORDS if a.family == family)


def materialize_accord(
    accord_name: str,
    formula_weight_g: float = 100.0,
    accord_loading_pct: float | None = None,
) -> dict[str, float] | None:
    """Convert an accord recipe into a raw ingredient dict (name → grams).

    Args:
        accord_name: name of the accord from the library
        formula_weight_g: total concentrate mass in grams
        accord_loading_pct: % of formula weight for this accord
            (if None, uses the accord's typical_use_pct)

    Returns:
        dict mapping material name to grams, or None if accord not found
    """
    accord = get_accord(accord_name)
    if accord is None:
        return None

    if accord_loading_pct is None:
        accord_loading_pct = accord.typical_use_pct or 20.0

    accord_mass = formula_weight_g * (accord_loading_pct / 100.0)
    ingredients: dict[str, float] = {}

    for mat_name, parts in accord.materials:
        mat_mass = accord_mass * (parts / accord.total_parts)
        ingredients[mat_name] = ingredients.get(mat_name, 0.0) + mat_mass

    return ingredients


def materialize_multi_accord_formula(
    accords: Sequence[tuple[str, float]],  # (accord_name, loading_pct)
    formula_weight_g: float = 100.0,
) -> dict[str, float] | None:
    """Build a formula from multiple accords.

    Args:
        accords: list of (accord_name, loading_percentage) pairs
        formula_weight_g: total concentrate mass in grams

    Returns:
        dict mapping material name to grams, or None if any accord not found
    """
    ingredients: dict[str, float] = {}
    for name, loading_pct in accords:
        result = materialize_accord(name, formula_weight_g, loading_pct)
        if result is None:
            return None
        for mat, mass in result.items():
            ingredients[mat] = ingredients.get(mat, 0.0) + mass

    return ingredients


def get_accord_character(accord_name: str) -> dict[str, float] | None:
    """Return the character dimension scores for an accord."""
    accord = get_accord(accord_name)
    return dict(accord.character) if accord else None


def get_accord_hedonic(accord_name: str) -> float | None:
    """Return the aggregate hedonic score for an accord."""
    accord = get_accord(accord_name)
    return accord.hedonic if accord else None
