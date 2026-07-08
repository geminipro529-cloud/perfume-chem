"""Commercial brief-to-material translation system.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the brief reading intelligence from the Advanced Perfumery Supplement
(Gap 9). At Dior/Chanel/Amouage, the commercial brief is a non-technical
document. The perfumer must translate abstract marketing language into specific
material selections, OAV targets, and compositional constraints.

This module provides:
  - Brief-element → material translation table
  - Concept strip construction (5-material rough sketch)
  - OAV target assignment by brief element type
  - Compositional constraint generation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


# ---------------------------------------------------------------------------
# Brief element → material translation
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BriefTranslation:
    """Translation of one abstract brief element into concrete formulation choices."""
    brief_keyword: str             # the abstract brief word
    material_translation: str      # specific materials to use
    oav_target: tuple[float, float]  # OAV range
    material_category: str         # texture-dominant, character-dominant, compositional constraint
    examples: str                  # known fragrances using this translation
    alternatives: tuple[str, ...] = ()  # alternative materials


BRIEF_TRANSLATIONS: tuple[BriefTranslation, ...] = (
    BriefTranslation(
        "raw, masculine strength", "Ambroxan + Iso E Super + Vetiver",
        (50, 200), "character-dominant",
        "Dior Sauvage backbone",
        ("Norlimbanol", "Cypriol EO"),
    ),
    BriefTranslation(
        "mediterranean herbs", "Lavender + Rosemary + Thyme + Linalool + Bergamot",
        (30, 100), "character-dominant",
        "Aromatic fougère, Acqua di Parma Colonia",
    ),
    BriefTranslation(
        "volcanic rock, mineral", "Cashmeran + Ambroxan + Geosmin trace + Vetiver",
        (3, 20), "texture-dominant",
        "Mineral/stone accord, Terre d'Hermès",
    ),
    BriefTranslation(
        "wild freshness", "Dihydromyrcenol + Hedione + Aldehydes trace + Calone trace",
        (20, 80), "character + texture",
        "Ozonic platform, Sauvage/Cool Water",
    ),
    BriefTranslation(
        "masculine, not feminine", "Avoid florals > OAV 20; emphasize woody, aromatic, resinous",
        (0, 20), "compositional constraint",
        "Constraint — limits floral loading, not a material recommendation",
    ),
    BriefTranslation(
        "luxury, price-no-object", "Include 2-3 naturals as anchors (Jasmine Absolute, Vetiver Haiti, Bergamot Calabrian)",
        (5, 25), "credibility + complexity",
        "Credibility anchors — authenticates the formula narrative",
    ),
    BriefTranslation(
        "long-lasting trail", "Base loading doubled: Norlimbanol 0.5% + Ambroxan 5% + Iso E Super 5%",
        (20, 100), "performance platform",
        "VP < 0.01 Pa platform, PDM/Amouage base structures",
    ),
    BriefTranslation(
        "elegant, refined", "Violet/Iris accord (γ-MIG + α-Ionone) + Sandalwood + Musk",
        (15, 40), "character-dominant",
        "Dior Homme, Chanel No.5 backbone",
    ),
    BriefTranslation(
        "sensual, intimate", "Jasmine Absolute + Hedione + Indole trace + Musk + Ambroxan",
        (10, 60), "character + texture",
        "Chanel No.5, Tom Ford Black Orchid intimacy layer",
    ),
    BriefTranslation(
        "fresh, clean, modern", "Hedione + Dihydromyrcenol + Habanolide + Floralozone",
        (30, 100), "texture-dominant",
        "Escentric Molecules, contemporary clean signatures",
    ),
    BriefTranslation(
        "dark, mysterious", "Patchouli + Cocoa Absolute + Guaiacwood + IBQ trace + Cypriol",
        (10, 40), "character-dominant",
        "Tom Ford Black Orchid, Amouage Interlude",
    ),
    BriefTranslation(
        "fruity, playful", "Allyl Amyl Glycolate + Helvetolide + Alpha-Damascone + Bergamot",
        (20, 80), "character-dominant",
        "Creed Aventus pineapple accord",
    ),
)


# ---------------------------------------------------------------------------
# Concept strip construction (the "smell the brief" exercise)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConceptStrip:
    """A 5-material rough sketch capturing a brief's emotional core."""
    brief_summary: str
    materials: tuple[tuple[str, str], ...]  # (material, role_in_strip)
    philosophy: str = (
        "At professional houses, the perfumer creates a concept strip — a 5-material "
        "rough sketch that captures the brief's emotional core — before building the "
        "full formula. This concept strip acts as the north star throughout development."
    )


# ---------------------------------------------------------------------------
# Material ↔ emotion mapping (the perfumer's vocabulary)
# ---------------------------------------------------------------------------

MATERIAL_EMOTION_MAP: dict[str, tuple[str, ...]] = {
    "Ambroxan": ("warm", "skin-like", "clean sensuality", "amber", "modern"),
    "Iso E Super": ("woody", "transparent", "sillage", "modern", "skin-amplifier"),
    "Hedione": ("radiant", "jasmine", "fresh-floral", "transparent", "lifting"),
    "Norlimbanol": ("dry-woody", "powerful", "masculine", "deep", "long-lasting"),
    "Cashmeran": ("spicy", "apple", "musky", "velvety", "woody"),
    "Helvetolide": ("fruity", "transparent", "pear-apple", "modern", "atmospheric"),
    "Galaxolide": ("powdery", "sweet", "comforting", "classic", "clean"),
    "Habanolide": ("clean", "transparent", "laundry-fresh", "modern", "skin-like"),
    "Jasmine Absolute": ("sensual", "narcotic", "floral", "luxury", "feminine"),
    "Rose Absolute": ("romantic", "velvety", "floral", "luxury", "classic"),
    "Vanillin": ("sweet", "comforting", "gourmand", "warm", "familiar"),
    "Coumarin": ("hay", "almond", "warm", "classic", "fresh"),
    "Patchouli EO": ("earthy", "dark", "hippie-chic", "grounding", "sensual"),
    "Vetiver EO": ("smoky", "green", "earthy", "masculine", "complex"),
    "Bergamot FCF": ("bright", "citrus", "fresh", "classic", "uplifting"),
    "Dihydromyrcenol": ("fresh", "clean", "transparent", "modern", "citrus"),
    "Calone": ("marine", "watermelon", "ozonic", "fresh", "aquatic"),
    "Cypriol EO": ("smoky", "woody-spicy", "oud-adjacent", "mysterious", "dark"),
    "Sichuan Pepper": ("electric", "tingling", "spicy-vibrating", "modern", "fresh"),
    "Labdanum": ("resinous", "amber", "balsamic", "warm", "classic"),
    "Birch Tar": ("smoky", "leathery", "camphoraceous", "dark", "masculine"),
    "Vertofix Coeur": ("cedar-musky", "warm-wood", "amber-undertone", "expensive", "masculine"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def translate_brief_element(keyword: str) -> list[BriefTranslation]:
    """Return all brief translations matching a keyword."""
    results = []
    for bt in BRIEF_TRANSLATIONS:
        if keyword.lower() in bt.brief_keyword.lower():
            results.append(bt)
    return results


def get_all_brief_translations() -> tuple[BriefTranslation, ...]:
    """Return all brief element translations."""
    return BRIEF_TRANSLATIONS


def translate_brief(brief_elements: Sequence[str]) -> dict[str, str]:
    """Translate a list of brief elements into material recommendations.

    Returns:
        dict mapping brief element → material recommendation
    """
    result: dict[str, str] = {}
    for element in brief_elements:
        translations = translate_brief_element(element)
        if translations:
            result[element] = translations[0].material_translation
        else:
            result[element] = "No translation found — consider abstract texture approach"
    return result


def get_emotions_for_material(material_name: str) -> tuple[str, ...] | None:
    """Return the emotional vocabulary associated with a material."""
    return MATERIAL_EMOTION_MAP.get(material_name.lower())


def find_materials_by_emotion(emotion: str) -> tuple[str, ...]:
    """Find materials associated with a specific emotion/descriptor."""
    results = []
    for mat, emotions in MATERIAL_EMOTION_MAP.items():
        if emotion.lower() in (e.lower() for e in emotions):
            results.append(mat)
    return tuple(results)


def build_concept_strip(
    brief_elements: Sequence[str],
    max_materials: int = 5,
) -> tuple[str, ...]:
    """Build a 5-material concept strip from brief elements.

    This mimics the 'smell the brief' exercise used at professional houses.
    Returns up to max_materials materials that best capture the brief's emotional core.
    """
    materials: list[str] = []
    seen: set[str] = set()

    for element in brief_elements:
        translations = translate_brief_element(element)
        for bt in translations:
            if bt.material_category == "compositional constraint":
                continue  # constraints don't suggest materials
            # Take the first material from each translation
            first_mat = bt.material_translation.split(" + ")[0].strip()
            if first_mat.lower() not in seen and len(materials) < max_materials:
                materials.append(first_mat)
                seen.add(first_mat.lower())

    return tuple(materials)


def generate_constraints(brief_elements: Sequence[str]) -> dict[str, str]:
    """Extract compositional constraints from brief elements.

    Returns:
        dict of constraint_type → constraint_description
    """
    constraints: dict[str, str] = {}
    for element in brief_elements:
        translations = translate_brief_element(element)
        for bt in translations:
            if bt.material_category == "compositional constraint":
                constraints[bt.brief_keyword] = bt.material_translation
    return constraints
