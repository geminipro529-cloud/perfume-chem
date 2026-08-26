"""Quantified material synergy and antagonist pair database.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the synergy quantification matrix and antagonist pair database from the
Formulation Intelligence Database (Part VI). Each synergy pair specifies:
  - The mechanism of interaction (receptor co-activation, contrast enhancement, etc.)
  - The optimal ratio range
  - The synergy factor (multiplicative boost to perceived intensity)
  - The active OAV range where synergy holds

Antagonist pairs specify materials that suppress or destroy each other's character.
These can be used to validate formula material combinations before dosing.
"""

from __future__ import annotations

from typing import Sequence

from ._shared_types import AntagonistPair, SynergyPair

# ---------------------------------------------------------------------------
# Synergy pairs (Part VI)
# ---------------------------------------------------------------------------

SYNERGY_PAIRS: tuple[SynergyPair, ...] = (
    SynergyPair(
        material_a="Hedione",
        material_b="Bergamot FCF",
        mechanism="VN1R1 activation + linalool bridge to jasmine character; OR2G2 co-activation",
        optimal_ratio=(65, 35),
        synergy_factor=2.5,
        oav_range=(1, 200),
        hedonic_impact=1.5,
        source="Wallrabenstein et al. 2015, NeuroImage",
    ),
    SynergyPair(
        material_a="Hedione",
        material_b="Rose Absolute",
        mechanism="Hedione amplifies rose radiance; rose anchor frames jasmine register",
        optimal_ratio=(70, 30),
        synergy_factor=2.0,
        oav_range=(5, 100),
        hedonic_impact=1.8,
        source="Practitioner consensus",
    ),
    SynergyPair(
        material_a="Beta-Damascenone",
        material_b="Citrus EO",
        mechanism="Damascenone enhances fruity-rosy facet of citrus; subliminal rose perception in hesperidic",
        optimal_ratio=(5, 95),
        synergy_factor=3.0,
        oav_range=(1, 10),
        hedonic_impact=2.0,
        source="ODT data; Leffingwell",
    ),
    SynergyPair(
        material_a="Indole",
        material_b="Jasmine Absolute",
        mechanism="Animalic warmth amplifies jasmine authenticity; contrast makes jasmine more beautiful",
        optimal_ratio=(3, 97),
        synergy_factor=2.5,
        oav_range=(2, 8),
        hedonic_impact=2.5,
        source="Arctander; practitioner consensus",
    ),
    SynergyPair(
        material_a="Vanillin",
        material_b="Coumarin",
        mechanism="Three-way triangle with Ethyl Maltol — each modifies the other's excess facet; coumarin prevents vanillin plasticity",
        optimal_ratio=(40, 40),
        synergy_factor=1.8,
        oav_range=(10, 80),
        hedonic_impact=1.5,
        source="Structure-activity; practitioner",
    ),
    SynergyPair(
        material_a="Ambroxan",
        material_b="Javanol",
        mechanism="Ambroxan deepens and grounds woody character; woody materials extend ambroxan's amber into spatial territory",
        optimal_ratio=(25, 75),
        synergy_factor=1.5,
        oav_range=(20, 80),
        hedonic_impact=1.2,
        source="Practitioner; TGSC",
    ),
    SynergyPair(
        material_a="Ambroxan",
        material_b="Iso E Super",
        mechanism="Ambroxan grounds Iso E Super's synthetic edge; Iso E Super extends ambroxan's spatial projection",
        optimal_ratio=(30, 70),
        synergy_factor=1.5,
        oav_range=(20, 80),
        hedonic_impact=1.2,
        source="Practitioner; chypre tradition",
    ),
    SynergyPair(
        material_a="Calone",
        material_b="Dihydromyrcenol",
        mechanism="Calone provides marine character; DHMN extends and softens marine into fresh-clean without metallic flip",
        optimal_ratio=(5, 95),
        synergy_factor=3.0,
        oav_range=(5, 50),
        hedonic_impact=1.0,
        source="Practitioner",
    ),
    SynergyPair(
        material_a="Geraniol",
        material_b="Citronellol",
        mechanism="Classic rose-pair; complementary character fills complete rosy spectrum; citronellol prevents geraniol's leaf off-note",
        optimal_ratio=(50, 50),
        synergy_factor=1.6,
        oav_range=(15, 50),
        hedonic_impact=1.5,
        source="Classical rose chemistry",
    ),
    SynergyPair(
        material_a="Coumarin",
        material_b="Lavender EO",
        mechanism="Coumarin masks medicinal facet of lavender; lavender freshens coumarin's sweetness",
        optimal_ratio=(20, 80),
        synergy_factor=1.7,
        oav_range=(10, 40),
        hedonic_impact=1.8,
        source="Fougère tradition; practitioner",
    ),
    SynergyPair(
        material_a="Iso E Super",
        material_b="Patchouli EO",
        mechanism="Iso E Super amplifies patchouli's earthy-cedar facet; patchouli grounds Iso E Super's synthetic edge",
        optimal_ratio=(55, 45),
        synergy_factor=1.8,
        oav_range=(20, 100),
        hedonic_impact=1.3,
        source="Practitioner; chypre tradition",
    ),
)


# ---------------------------------------------------------------------------
# Antagonist pairs (Part VI)
# ---------------------------------------------------------------------------

ANTAGONIST_PAIRS: tuple[AntagonistPair, ...] = (
    AntagonistPair(
        material_a="Aldehydes C10/C11",
        material_b="Methyl Anthranilate",
        problem="Schiff base formation → brown-orange floral shift; carbonyl-amine condensation",
        max_safe_ratio="Never combine — separate use only",
        mechanism="Carbonyl-amine condensation (Schiff base)",
    ),
    AntagonistPair(
        material_a="Calone",
        material_b="Labdanum",
        problem="Aquatic metallic character destroys resinous warmth; olfactory contrast collapse",
        max_safe_ratio="< 3% calone vs 100% labdanum",
        mechanism="Olfactory contrast collapse",
    ),
    AntagonistPair(
        material_a="Oakmoss Absolute",
        material_b="Rose Absolute",
        problem="Oakmoss dominates and obscures rose at > 30:70 ratio",
        max_safe_ratio="< 15% oakmoss vs 100% rose content",
        mechanism="VP dominance — oakmoss character overwhelms rose at high ratio",
    ),
    AntagonistPair(
        material_a="Isobutyl Quinoline (IBQ)",
        material_b="Floral materials",
        problem="IBQ at > OAV 5 reads as medicinal-tar, destroys floral context",
        max_safe_ratio="< 0.01% IBQ in floral formulas",
        mechanism="Character incompatibility — leather vs floral",
    ),
    AntagonistPair(
        material_a="Vanillin",
        material_b="Citrus top notes",
        problem="Vanillin sweetness clashes with citrus fresh-sour character",
        max_safe_ratio="Keep vanillin OAV < 20 if citrus OAV > 50",
        mechanism="Hedonic-context incompatibility",
    ),
    AntagonistPair(
        material_a="Calone",
        material_b="Gourmand materials",
        problem="Aquatic sharpness destroys gourmand warmth; fundamental opposition",
        max_safe_ratio="< 5% marine character in gourmand formula",
        mechanism="Fundamental family incompatibility",
    ),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_synergy_pairs_material(material_name: str) -> tuple[SynergyPair, ...]:
    """Return all synergy pairs involving a given material."""
    key = material_name.lower()
    results = []
    for pair in SYNERGY_PAIRS:
        if pair.material_a.lower() == key or pair.material_b.lower() == key:
            results.append(pair)
    return tuple(results)


def get_synergy_factor(
    material_a: str,
    material_b: str,
    oav_a: float,
    oav_b: float,
) -> float:
    """Return the synergy factor for a pair of materials given their OAVs.

    The synergy only applies if BOTH materials are within their active OAV range.

    Returns:
        synergy_factor if synergy applies, 1.0 if no synergy or OAVs out of range
    """
    key_a = material_a.lower()
    key_b = material_b.lower()
    for pair in SYNERGY_PAIRS:
        match_a = pair.material_a.lower() == key_a and pair.material_b.lower() == key_b
        match_b = pair.material_b.lower() == key_a and pair.material_a.lower() == key_b
        if not (match_a or match_b):
            continue

        # Check OAV range (simplified: check the range is applicable)
        lo, hi = pair.oav_range
        if lo <= oav_a <= hi and lo <= oav_b <= hi:
            return pair.synergy_factor
        # Partial: at least one is in range → proportional synergy
        if lo <= oav_a <= hi or lo <= oav_b <= hi:
            return 1.0 + (pair.synergy_factor - 1.0) * 0.5
        return 1.0

    return 1.0


def get_antagonist_pairs_material(material_name: str) -> tuple[AntagonistPair, ...]:
    """Return all antagonist pairs involving a given material."""
    key = material_name.lower()
    results = []
    for pair in ANTAGONIST_PAIRS:
        if pair.material_a.lower() == key or pair.material_b.lower() == key:
            results.append(pair)
    return tuple(results)


def check_formula_conflicts(
    material_names: Sequence[str],
) -> tuple[AntagonistPair, ...]:
    """Check a set of material names for known antagonist conflicts.

    Returns:
        tuple of conflicting pairs found in the formula
    """
    name_set = {n.lower() for n in material_names}
    conflicts = []
    for pair in ANTAGONIST_PAIRS:
        a = pair.material_a.lower()
        b = pair.material_b.lower()
        if a in name_set and b in name_set:
            conflicts.append(pair)
    return tuple(conflicts)


def check_formula_synergies(
    material_names: Sequence[str],
) -> tuple[SynergyPair, ...]:
    """Check a set of material names for known synergy pairs.

    Returns:
        tuple of synergy pairs found in the formula
    """
    name_set = {n.lower() for n in material_names}
    synergies = []
    for pair in SYNERGY_PAIRS:
        a = pair.material_a.lower()
        b = pair.material_b.lower()
        if a in name_set and b in name_set:
            synergies.append(pair)
    return tuple(synergies)


def get_all_synergy_pairs() -> tuple[SynergyPair, ...]:
    """Return all known synergy pairs."""
    return SYNERGY_PAIRS


def get_all_antagonist_pairs() -> tuple[AntagonistPair, ...]:
    """Return all known antagonist pairs."""
    return ANTAGONIST_PAIRS
