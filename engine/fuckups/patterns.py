"""Registry of known failure patterns — the growing rulebook.

Each pattern is a named rule with detection logic. Patterns are learned from
historical FuckupEntry records and applied by the detector to new formulas.

Pattern naming convention: <cause>_in_<context> → <effect>
Example: juniper_in_non_fougere → aromatic_green_drift
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from engine.name_utils import normalize_name


@dataclass(frozen=True, slots=True)
class MaterialRule:
    """A rule about a specific material: name pattern, dose threshold, context check."""

    material_names: tuple[str, ...]
    """Normalized names to match (OR logic — any match triggers)."""

    dose_threshold_ul: float = 0
    """Minimum dose (raw µL) to trigger. 0 means any dose."""

    active_threshold_ul: float = 0
    """Minimum active µL to trigger. 0 means any dose."""

    oav_threshold: float = 0
    """Minimum OAV to trigger. 0 means any OAV."""

    forbidden_in_families: tuple[str, ...] = ()
    """If the target family is one of these, the material is flagged."""

    forbidden_in_contexts: tuple[str, ...] = ()
    """If these keyword(s) appear in the formula's intended character, flag."""

    forbidden_when_present: tuple[str, ...] = ()
    """If these material(s) are also in the formula, flag (co-occurrence rule)."""

    reason: str = ""
    """Why this material is problematic in this context."""


@dataclass(frozen=True, slots=True)
class CombinationRule:
    """A rule about a combination of materials that together create a problem."""

    name: str
    """Human-readable pattern name."""

    materials: tuple[str, ...]
    """Normalized material names — ALL must be present to trigger."""

    min_count: int = 0
    """Minimum number from the tuple that must be present. 0 = all."""

    context: str = ""
    """When this combination is problematic (e.g. 'in non-chypre formula')."""

    effect: str = ""
    """What happens when this combination is present."""

    severity: str = "high"
    """'catastrophic', 'high', 'moderate', 'low'."""

    recommendation: str = ""
    """What to do about it."""

    fuckup_reference: str = ""
    """ID of the fuckup entry that taught us this rule."""


@dataclass(frozen=True, slots=True)
class DoseRule:
    """A rule about a material being dosed beyond its safe ceiling for a context."""

    material_name: str

    max_dose_ul: float = 0
    """Maximum safe dose in raw µL. 0 = no limit."""

    max_active_ul: float = 0
    """Maximum safe dose in active µL. 0 = no limit."""

    max_oav: float = 0
    """Maximum safe OAV. 0 = no limit."""

    context: str = ""
    """When this limit applies."""

    effect: str = ""
    """What happens when overdosed."""

    severity: str = "moderate"

    recommendation: str = ""

    fuckup_reference: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN REGISTRY — learned from historical fuckups
# ═══════════════════════════════════════════════════════════════════════════════

# -- Material rules: single-material out-of-context detectors --

MATERIAL_RULES: tuple[MaterialRule, ...] = (
    MaterialRule(
        material_names=("juniper berry eo",),
        dose_threshold_ul=30,
        forbidden_in_contexts=("aventus", "fruity chypre", "modern chypre"),
        reason=(
            "Juniper Berry EO is a powerful aromatic-coniferous material (VP=65 Pa). "
            "At >30 µL it creates a gin-juniper opening that dominates the top note. "
            "This is appropriate for aromatic fougères but collides with fruity chypre / "
            "Aventus-style compositions where the top should be bright-fruity, not coniferous-green. "
            "At 50 µL neat, it produced OAV 1,936 — the third-strongest material in the formula."
        ),
    ),
    MaterialRule(
        material_names=("orivone",),
        dose_threshold_ul=20,
        oav_threshold=300,
        forbidden_in_contexts=("aventus", "fruity", "modern chypre", "non-iris"),
        reason=(
            "Orivone at VP=8.6 Pa functions as a top-to-heart orris note. Above 20 µL, "
            "it creates a warm, buttery, slightly fungal 'old perfume' character that reads "
            "as classical pre-modern perfumery (1880-1920 era). This directly contradicts "
            "modern fruity chypre character where orris should be absent or at trace only."
        ),
    ),
    MaterialRule(
        material_names=("petitgrain eo paraguay", "petitgrain eo"),
        dose_threshold_ul=60,
        forbidden_in_contexts=("aventus", "fruity chypre"),
        reason=(
            "Petitgrain at >60 µL adds bitter-green-neroli character. Combined with juniper "
            "or other aromatic materials, it creates an aromatic-chypre opening (fougère-era style) "
            "instead of the bright-fruity opening expected in Aventus-style compositions."
        ),
    ),
    MaterialRule(
        material_names=("nagarmotha oil", "nagarmortha oil", "cypriol eo"),
        dose_threshold_ul=100,
        forbidden_when_present=("birch tar rectified", "cade oil rectified"),
        reason=(
            "Nagarmotha at >100 µL as a 'smoke' substitute creates earthy-musty character "
            "(cypriol/oud-adjacent) rather than sharp smoky. It lacks the oily-leather bite "
            "of birch tar or the dry-ashy character of cade. The earthy quality collides with "
            "modern chypre expectations."
        ),
    ),
    MaterialRule(
        material_names=("alpha irone",),
        active_threshold_ul=30,
        forbidden_in_contexts=("aventus", "non-iris"),
        reason=(
            "Alpha Irone at >30 µL active creates a soliflore-level iris statement. "
            "Iris fundamentally re-routes any fragrance away from fruity chypre territory. "
            "Aventus has zero iris — any detectable iris contradicts the reference."
        ),
    ),
    MaterialRule(
        material_names=("geosmin",),
        dose_threshold_ul=5,
        forbidden_in_contexts=("aventus", "fruity", "modern"),
        reason=(
            "Geosmin at >5 µL (of 0.1%) creates petrichor/rain-on-earth character. "
            "This damp-earth quality belongs in naturalistic earth accords, not modern "
            "fruity chypre. It adds an 'old cellar' quality contradicted by Aventus DNA."
        ),
    ),
)


# -- Combination rules: material clusters that together create genre drift --

COMBINATION_RULES: tuple[CombinationRule, ...] = (
    CombinationRule(
        name="classical_chypre_skeleton",
        materials=(
            "oakmoss absolute",
            "labdanum resinoid",
            "vetiver eo",
            "cedarwood eo",
            "cedarwood oil virginia",
        ),
        min_count=3,
        context="in non-chypre formula claiming Aventus/modern DNA",
        effect=(
            "Oakmoss + labdanum + vetiver + cedar = the classical chypre base skeleton. "
            "This four-material foundation dates to Coty's Chypre (1917) and creates "
            "an unmistakably classical mossy-leathery-woody drydown. When present in a "
            "formula claiming Aventus DNA (which has a modern ambrox-musk base), the "
            "chypre skeleton pulls the fragrance toward 1880-1920 territory."
        ),
        severity="catastrophic",
        recommendation=(
            "Replace the chypre skeleton with a modern base: "
            "Ambrofix + Cashmeran + Clearwood + Romandolide. "
            "If moss character is needed, use Evernyl at trace (5-10 µL neat) instead of Oakmoss Absolute. "
            "If leather is needed, use Suederal (10%) at 20-30 µL instead of IBQ + Labdanum."
        ),
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    CombinationRule(
        name="aromatic_green_opening",
        materials=(
            "juniper berry eo",
            "petitgrain eo paraguay",
            "petitgrain eo",
            "cardamom eo",
            "galbanum eo",
            "galbanum resinoid",
        ),
        min_count=2,
        context="in fruity chypre / Aventus-adjacent formula",
        effect=(
            "Two or more aromatic-green materials (juniper, petitgrain, cardamom, galbanum) "
            "in the top create an aromatic-fougère opening, not a fruity one. This combination "
            "is excellent for aromatic fougères (Fougère Royale, 1882) but contradicts the "
            "bright-fruity opening expected in Aventus-style compositions."
        ),
        severity="catastrophic",
        recommendation=(
            "For Aventus-style top: Bergamot + Pineapple accord (Allyl Amyl Glycolate 10% at 40-60 µL, "
            "or Dynascone 10% at 30 µL) + Blackcurrant (Cassis Base 345B at 30 µL max, or Paradisamide). "
            "Remove juniper and reduce petitgrain to ≤20 µL."
        ),
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    CombinationRule(
        name="iris_soliflore_collision",
        materials=(
            "alpha irone",
            "orivone",
            "ultralia",
            "beta ionone",
            "alpha ionone",
            "methyl ionone pure",
            "irotyl",
        ),
        min_count=3,
        context="in non-iris formula",
        effect=(
            "Three or more iris materials create a soliflore-level iris heart. "
            "Iris (cold, buttery, powdery, orris) is one of the most distinctive and "
            "genre-defining registers in perfumery. It cannot coexist with fruity chypre "
            "(Aventus DNA) — the registers collide and iris wins because ionones/irones "
            "are more tenacious than fruit esters."
        ),
        severity="high",
        recommendation=(
            "If iris is wanted as a subtle accent, use only ONE iris material at ≤20 µL "
            "(e.g. Beta Ionone 1% at 20 µL for violet-leaf rounding, or Ultralia at 10 µL "
            "for ghost powder). Remove Alpha Irone, Orivone, and other iris materials entirely "
            "unless the formula is explicitly an iris fragrance."
        ),
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    CombinationRule(
        name="missing_aventus_dna",
        materials=(
            "allyl amyl glycolate",
            "dynascone",
            "birch tar rectified",
            "patchouli eo",
            "clearwood",
        ),
        min_count=0,
        context="when formula design brief mentions Aventus",
        effect=(
            "The formula claims Aventus DNA but lacks the core materials that define it: "
            "pineapple accord, birch tar smoke, patchouli earth, and ambrox-musk base. "
            "Without these, any substitute materials will create a different fragrance entirely."
        ),
        severity="high",
        recommendation=(
            "Must-have Aventus markers: pineapple accord (Allyl Amyl Glycolate 10% 40-60 µL "
            "OR Dynascone 10% 30 µL), birch tar rectified (10% at 20-30 µL for smoky-leather), "
            "patchouli or Clearwood (for earthy bridge), Ambrofix 30% (300-400 µL), "
            "and a transparent musk scaffold (Romandolide + Habanolide)."
        ),
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    CombinationRule(
        name="earth_smoke_mismatch",
        materials=("nagarmotha oil", "guaiacol"),
        min_count=2,
        context="when formula intends smoky character without birch tar",
        effect=(
            "Nagarmotha (earthy-musty) + Guaiacol (clean phenolic) creates a damp-earth "
            "smoke character rather than the sharp, oily, leather-smoke of birch tar. "
            "This combination pulls toward classical chypre or oud territory."
        ),
        severity="moderate",
        recommendation=(
            "For Aventus-style smoke: Birch Tar Rectified 10% at 20-30 µL. "
            "For a cleaner smoke: Cade Oil Rectified 1% at 30-50 µL + trace Guaiacol 10% at 20 µL. "
            "Avoid Nagarmotha entirely in non-oud/non-classical contexts."
        ),
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
)


# -- Dose rules: material-specific ceilings by context --

DOSE_RULES: tuple[DoseRule, ...] = (
    DoseRule(
        material_name="juniper berry eo",
        max_dose_ul=30,
        context="in non-fougère, non-aromatic formula",
        effect="Gin-coniferous opening dominates top note (OAV >1,000 at 50 µL).",
        severity="high",
        recommendation="Reduce to ≤20 µL or remove entirely in fruity/modern contexts.",
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    DoseRule(
        material_name="orivone",
        max_dose_ul=15,
        context="in non-iris formula",
        effect="Buttery orris character reads as 'old perfume' (1880-1920 era).",
        severity="high",
        recommendation="Reduce to ≤10 µL or replace with Ultralia at 5-10 µL for ghost iris.",
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    DoseRule(
        material_name="petitgrain eo paraguay",
        max_dose_ul=40,
        context="in fruity chypre / Aventus-adjacent formula",
        effect="Bitter-green-neroli top contradicts fruity character.",
        severity="moderate",
        recommendation="Reduce to ≤20 µL. Use Bergamot FCF for citrus body instead.",
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    DoseRule(
        material_name="alpha irone",
        max_active_ul=20,
        context="in non-iris formula",
        effect="Soliflore-level iris creates genre collision with non-iris brief.",
        severity="high",
        recommendation="Reduce active dose to ≤10 µL or remove. Use Beta Ionone 1% at trace for rounding.",
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    DoseRule(
        material_name="nagarmotha oil",
        max_dose_ul=80,
        context="in non-oud, non-classical formula",
        effect="Earthy-musty character contradicts modern/transparent contexts.",
        severity="moderate",
        recommendation="Reduce to ≤50 µL or replace with Cade Oil Rectified 1% for smoke.",
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    DoseRule(
        material_name="geosmin",
        max_dose_ul=5,
        context="universal",
        effect="Petrichor adds 'damp cellar' quality to any composition.",
        severity="low",
        recommendation="Keep at 2-5 µL of 0.1%. At ODT 6 ppt, even trace doses are perceptible.",
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
    DoseRule(
        material_name="cassis base 345b",
        max_dose_ul=30,
        context="in non-cassis-forward formula",
        effect="Sulfury blackcurrant dominates at OAV >2,000, persisting through drydown.",
        severity="moderate",
        recommendation="If cassis is not the star, reduce to ≤20 µL. Supplement with Paradisamide 10% for softer fruit.",
        fuckup_reference="cassis_iris_smoke_2026-07-05",
    ),
)


def get_all_material_rules() -> tuple[MaterialRule, ...]:
    """Return all known single-material out-of-context rules."""
    return MATERIAL_RULES


def get_all_combination_rules() -> tuple[CombinationRule, ...]:
    """Return all known material combination rules."""
    return COMBINATION_RULES


def get_all_dose_rules() -> tuple[DoseRule, ...]:
    """Return all known dose ceiling rules."""
    return DOSE_RULES
