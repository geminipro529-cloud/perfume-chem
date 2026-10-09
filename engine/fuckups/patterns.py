"""Registry of known failure patterns — the growing rulebook.

Each pattern is a named rule with detection logic. Patterns are learned from
historical FuckupEntry records and applied by the detector to new formulas.

Pattern naming convention: <cause>_in_<context> → <effect>
Example: juniper_in_non_fougere → aromatic_green_drift
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MaterialRule:
    """A rule about a specific material: name pattern, dose threshold, context check."""

    material_names: tuple[str, ...]
    """Normalized names to match (OR logic — any match triggers)."""

    active_threshold_ul: float = 0
    """Minimum active µL (raw µL x stock dilution) to trigger. 0 means any dose."""

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

    stock_basis: str = ""
    """Which stock the active threshold was converted from."""

    campaign_id: str = ""
    """When set, the rule fires only for a scan given this exact campaign id."""


@dataclass(frozen=True, slots=True)
class CombinationRule:
    """A rule about a combination of materials that together create a problem."""

    name: str
    """Human-readable pattern name."""

    materials: tuple[str, ...]
    """Normalized material names — ALL must be present to trigger."""

    min_count: int = 0
    """Minimum number from the tuple that must be present. 0 = all."""

    count_once: tuple[tuple[str, ...], ...] = ()
    """Groups of variant names (e.g. two cedarwood oils) that count once toward min_count."""

    context: str = ""
    """When this combination is problematic (e.g. 'in non-chypre formula')."""

    effect: str = ""
    """What happens when this combination is present."""

    severity: str = "high"
    """'catastrophic', 'high', 'warn', 'moderate', 'low'."""

    recommendation: str = ""
    """What to do about it."""

    fuckup_reference: str = ""
    """ID of the fuckup entry that taught us this rule."""

    campaign_id: str = ""
    """When set, the rule fires only for a scan given this exact campaign id."""


@dataclass(frozen=True, slots=True)
class DoseRule:
    """A rule about a material being dosed beyond its safe ceiling for a context."""

    material_name: str

    max_active_ul: float = 0
    """Maximum dose in active µL (raw µL x stock dilution). 0 = no limit."""

    max_oav: float = 0
    """Maximum safe OAV. 0 = no limit."""

    context: str = ""
    """When this limit applies."""

    effect: str = ""
    """What happens when overdosed."""

    severity: str = "moderate"

    recommendation: str = ""

    fuckup_reference: str = ""

    stock_basis: str = ""
    """Which stock the active ceiling was converted from."""

    campaign_id: str = ""
    """When set, the rule fires only for a scan given this exact campaign id."""


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN REGISTRY — learned from historical fuckups
# ═══════════════════════════════════════════════════════════════════════════════

CASSIS_IRIS_SMOKE_CAMPAIGN_ID = "cassis_iris_smoke_2026-07-05"
"""Every rule below was learned from this one formula (formulas/Cassis_Iris_Smoke_30mL_EdP.md).

The rules fire only when a scan names this exact campaign. Outside it they stay
silent: one bottle does not establish a genre ban for other briefs.
"""

_ONE_BOTTLE = "This lesson comes from one bottle (Cassis Iris Smoke) and is not a general ban."


def compare_without(*names: str) -> str:
    joined = " + ".join(names)
    return (
        f"Compare the formula with and without {joined} (an omission comparison "
        f"against the unchanged control) before changing the dose. {_ONE_BOTTLE}"
    )


def _compare_at_ceiling(name: str, ceiling_active_ul: float) -> str:
    return (
        f"Compare the formula with and without {name}, and with {name} held at "
        f"≤{ceiling_active_ul:g} µL active, before changing it. {_ONE_BOTTLE}"
    )


# -- Material rules: single-material out-of-context detectors --
# Thresholds are active µL. The Cassis Iris Smoke formula dosed Juniper, Orivone,
# Petitgrain and Nagarmotha neat and Geosmin as 0.1% in TEC.

MATERIAL_RULES: tuple[MaterialRule, ...] = (
    MaterialRule(
        material_names=("juniper berry eo",),
        active_threshold_ul=30,
        stock_basis="30 µL of the neat oil (Cassis Iris Smoke used 50 µL neat).",
        reason=(
            "Juniper Berry EO is a powerful aromatic-coniferous material (VP=65 Pa). "
            "In Cassis Iris Smoke, 50 µL neat gave a gin-juniper opening that dominated the top "
            "(OAV 1,936, the third-strongest material in the formula) and competed with the "
            "bergamot-blackcurrant opening that brief wanted."
        ),
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    MaterialRule(
        material_names=("orivone",),
        active_threshold_ul=20,
        oav_threshold=300,
        stock_basis="20 µL of neat Orivone (Cassis Iris Smoke used 30 µL neat).",
        reason=(
            "Orivone at VP=8.6 Pa reaches the top and heart. In Cassis Iris Smoke, 30 µL neat "
            "(OAV 833) read as warm, buttery, slightly fungal orris and pulled that formula "
            "toward a classical register its brief did not want."
        ),
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    MaterialRule(
        material_names=("petitgrain eo paraguay", "petitgrain eo"),
        active_threshold_ul=60,
        stock_basis="60 µL of the neat oil (Cassis Iris Smoke used 80 µL neat).",
        reason=(
            "In Cassis Iris Smoke, 80 µL neat Petitgrain added a bitter-green-neroli bite that, "
            "with Juniper, gave an aromatic opening instead of the bergamot-blackcurrant "
            "opening that brief wanted."
        ),
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    MaterialRule(
        material_names=("nagarmotha oil", "nagarmortha oil", "cypriol eo"),
        active_threshold_ul=100,
        forbidden_when_present=("birch tar rectified", "cade oil rectified"),
        stock_basis="100 µL of the neat oil (Cassis Iris Smoke used 200 µL neat).",
        reason=(
            "In Cassis Iris Smoke, 200 µL neat Nagarmotha used as a smoke substitute read "
            "earthy-musty (cypriol/oud-adjacent) rather than sharp smoky, alongside the "
            "birch tar or cade smoke."
        ),
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    MaterialRule(
        material_names=("alpha irone",),
        active_threshold_ul=30,
        stock_basis="30 µL active (Cassis Iris Smoke used 200 µL of 30% = 60 µL active).",
        reason=(
            "In Cassis Iris Smoke, 60 µL active Alpha Irone, with Orivone, Ultralia and Beta "
            "Ionone, gave a soliflore-level iris heart that pulled that formula away from the "
            "fruity Aventus-adjacent direction its brief named."
        ),
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    MaterialRule(
        material_names=("geosmin",),
        active_threshold_ul=0.005,
        stock_basis=(
            "0.005 µL active geosmin = 5 µL of the 0.1% in TEC stock the rule was written for "
            "(= 0.5 µL of the 1% in TEC stock)."
        ),
        reason=(
            "In Cassis Iris Smoke, Geosmin (15 µL of 0.1% in TEC) gave a damp petrichor / "
            "rain-on-earth quality that read as 'old cellar' against that formula's fruity brief."
        ),
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
)


# -- Combination rules: material clusters that pulled the Cassis Iris Smoke formula off its brief --

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
        count_once=(("cedarwood eo", "cedarwood oil virginia"),),
        effect=(
            "Oakmoss + labdanum + vetiver + cedar is the classical chypre base skeleton "
            "(Coty's Chypre, 1917). Cedarwood variants count once, so at least three of "
            "moss, labdanum, vetiver and cedar must be present. In Cassis Iris Smoke this "
            "skeleton gave a classical mossy-leathery-woody drydown that pulled the formula "
            "away from the newer Aventus-adjacent direction its brief named."
        ),
        severity="warn",
        recommendation=compare_without("the moss-labdanum-vetiver-cedar base block"),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
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
        count_once=(("petitgrain eo paraguay", "petitgrain eo"),),
        effect=(
            "In Cassis Iris Smoke, two or more aromatic-green materials (juniper, petitgrain, "
            "cardamom, galbanum) in the top gave an aromatic-fougère opening that obscured "
            "the bergamot-blackcurrant opening that brief wanted."
        ),
        severity="warn",
        recommendation=compare_without("the aromatic-green top materials"),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
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
        effect=(
            "In Cassis Iris Smoke, three or more iris materials gave a soliflore-level iris "
            "heart (cold, buttery, powdery) that outlasted the fruit top and pulled that "
            "formula away from the fruity direction its brief named."
        ),
        severity="warn",
        recommendation=compare_without("the iris block"),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
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
        effect=(
            "Cassis Iris Smoke named Aventus as its direction but lacked a coherent architecture: "
            "a primary bergamot-blackcurrant head, controlled pepper-jasmine and secondary "
            "pineapple bridge, cross-layer dry-wood/musk continuity, and smoky-birch/patchouli/"
            "musk base."
        ),
        severity="warn",
        recommendation=(
            "Preserve the role hierarchy rather than forcing fixed materials or doses. In the "
            "current inventory, Birch Tar is excluded because its live row is marked prohibited; "
            "any Cade/Suederal smoke-leather mapping is explicitly non-equivalent. "
            + compare_without("each candidate role material")
        ),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    CombinationRule(
        name="earth_smoke_mismatch",
        materials=("nagarmotha oil", "guaiacol"),
        min_count=2,
        effect=(
            "In Cassis Iris Smoke, Nagarmotha (earthy-musty) + Guaiacol (clean phenolic) gave "
            "a damp-earth smoke rather than the sharp, oily, leather-smoke of birch tar."
        ),
        severity="warn",
        recommendation=(
            "Do not use Birch Tar because the live inventory marks it prohibited. "
            + compare_without("Nagarmotha", "Guaiacol")
        ),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
)


# -- Dose rules: active-µL ceilings learned from the Cassis Iris Smoke formula --
# Each ceiling is active µL (raw µL x the row's stock dilution). The stock basis
# says which stock the original raw number was written for.

DOSE_RULES: tuple[DoseRule, ...] = (
    DoseRule(
        material_name="juniper berry eo",
        max_active_ul=30,
        stock_basis="Written as 30 µL of the neat oil; Cassis Iris Smoke used 50 µL neat.",
        effect="Gin-coniferous opening dominated the top note (OAV >1,000 at 50 µL neat).",
        severity="warn",
        recommendation=_compare_at_ceiling("Juniper Berry EO", 30),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    DoseRule(
        material_name="orivone",
        max_active_ul=15,
        stock_basis="Written as 15 µL of neat Orivone; Cassis Iris Smoke used 30 µL neat.",
        effect="Buttery orris read as an older, classical register in that formula.",
        severity="warn",
        recommendation=_compare_at_ceiling("Orivone", 15),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    DoseRule(
        material_name="petitgrain eo paraguay",
        max_active_ul=40,
        stock_basis="Written as 40 µL of the neat oil; Cassis Iris Smoke used 80 µL neat.",
        effect="Bitter-green-neroli top competed with the fruity opening that brief wanted.",
        severity="warn",
        recommendation=_compare_at_ceiling("Petitgrain EO Paraguay", 40),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    DoseRule(
        material_name="alpha irone",
        max_active_ul=20,
        stock_basis="Written in active µL; Cassis Iris Smoke used 200 µL of 30% = 60 µL active.",
        effect="Soliflore-level iris pulled that formula away from its fruity brief.",
        severity="warn",
        recommendation=_compare_at_ceiling("Alpha Irone", 20),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    DoseRule(
        material_name="nagarmotha oil",
        max_active_ul=80,
        stock_basis="Written as 80 µL of the neat oil; Cassis Iris Smoke used 200 µL neat.",
        effect="Earthy-musty character in place of the intended smoke.",
        severity="warn",
        recommendation=_compare_at_ceiling("Nagarmotha Oil", 80),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    DoseRule(
        material_name="geosmin",
        max_active_ul=0.005,
        stock_basis=(
            "Written as 5 µL of the 0.1% in TEC stock = 0.005 µL active "
            "(= 0.5 µL of the 1% in TEC stock); Cassis Iris Smoke used 15 µL of 0.1%."
        ),
        effect="Petrichor added a 'damp cellar' quality. At ODT 6 ppt, even trace doses are perceptible.",
        severity="warn",
        recommendation=_compare_at_ceiling("Geosmin", 0.005),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
    ),
    DoseRule(
        material_name="cassis base 345b",
        max_active_ul=30,
        stock_basis="Written as 30 µL of the neat base; Cassis Iris Smoke used 50 µL neat.",
        effect="Sulfury blackcurrant dominated at OAV >2,000 and persisted through the drydown.",
        severity="warn",
        recommendation=_compare_at_ceiling("Cassis Base 345B", 30),
        fuckup_reference=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
        campaign_id=CASSIS_IRIS_SMOKE_CAMPAIGN_ID,
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
