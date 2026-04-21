"""Psychophysical perception modelling.

Four empirically validated phenomena that constrain how humans
actually PERCEIVE complex mixtures:

1. **Mixture suppression** (Laing & Francis 1989):
   In a mixture of N odorants, humans can typically identify only 3-4
   individual components. Beyond this, mutual suppression dominates
   and the percept becomes "blended/unresolvable."

2. **Cross-adaptation** (Cain & Polak 1992, Dalton 2000):
   Exposure to one odorant reduces sensitivity to chemically similar
   odorants. Materials sharing functional groups cross-adapt: adapting
   to linalool → reduced perception of linalyl acetate and geraniol.

3. **Genetic anosmia** (Keller et al. 2007, Jaeger et al. 2013):
   Specific OR (olfactory receptor) gene variants cause selective
   anosmia in fraction of population:
     OR7D4 → androstenone/androstenol: ~50% of population less sensitive
     OR5A1 → β-ionone: ~8% of population less sensitive
     OR11H7P → Iso E Super: ~20% less perception
     Galaxolide: ~10% complete anosmia

4. **Olfactory white** (Weiss et al. 2012 PNAS):
   When ≥30 components of similar intensity span olfactory space,
   all mixtures converge to the same nondescript "olfactory white."
   Implications: over-complex formulas lose distinctiveness.

Sources:
  Laing & Francis (1989) Perception — mixture component identification
  Livermore & Laing (1996) Chemical Senses — 3-4 component ceiling
  Cain & Polak (1992) Chemical Senses — cross-adaptation
  Dalton (2000) Psychophysiology — neural adaptation
  Keller et al. (2007) Nature — OR7D4 and androstenone
  Jaeger et al. (2013) Current Biology — OR5A1 and beta-ionone
  Weiss et al. (2012) PNAS — olfactory white
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-Adaptation Groups — chemicals that share receptor space
# Materials within the same group cross-adapt (adapting to one reduces
# perception of others in the group). Grouping by functional chemistry.
# ═══════════════════════════════════════════════════════════════════════════════

CROSS_ADAPTATION_GROUPS: dict[str, list[str]] = {
    "terpene_alcohol": [
        "Linalool", "Geraniol", "Citronellol", "Nerol",
        "cis-3-Hexenol", "Dihydromyrcenol", "Terpinyl Acetate",
        "Ethyl Linalool",        # linalool ether, same terpene alcohol receptor space
        "Neroli EO",             # 25-40% linalool, terpene-rich EO
        "Rose Oxide",            # monoterpene pyranoid, geraniol-derived
        "Cardamom FTEC",         # terpinyl acetate + 1,8-cineole dominant, terpene receptor space
    ],
    "terpene_ester": [
        "Linalyl Acetate", "Hexyl Acetate",
        # Benzyl Acetate reclassified → jasmine (aromatic ester, not terpene-derived)
    ],
    "aldehyde_fatty": [
        "Aldehyde C10", "Aldehyde C11", "Aldehyde C11 Undecylenic",
        "Aldehyde C12 MNA",
        "Methyl Nonyl Ketone",   # C11 aliphatic carbonyl, same waxy receptor space
    ],
    "aldehyde_aromatic": [
        "Cyclamen Aldehyde", "Bourgeonal", "Hydroxycitronellal",
        "Anisaldehyde",
        "Aurantiol",             # Schiff base of hydroxycitronellal + methyl anthranilate
        "Scentenal",             # metallic-ozone aldehyde, shares aromatic aldehyde receptor space
    ],
    "ionone_family": [
        "Alpha Ionone", "Beta Ionone", "Alpha Irone",
        "Methyl Ionone Pure", "Ultralia",
        "Alpha Isomethyl Ionone",
        "Dihydro Beta Ionone",   # reduced ionone, same OR5A1 space
        "Orivone",              # orris ketone, OR5A1 iris-ionone receptor space
        "Allyl Ionone",         # ionone derivative, same OR5A1 family
    ],
    "salicylate_family": [
        "Benzyl Salicylate", "Hexyl Salicylate",
        "Methyl Salicylate",
        "Benzyl Benzoate",       # benzyl ester analog, shared receptor space with BzSal
    ],
    "vanillic_coumarinic": [
        "Vanillin", "Ethyl Vanillin", "Benzoin Resinoid",
        "Ethyl Maltol",          # sweet enhancer, vanillic receptor overlap
        "Coumarin",              # sweet-lactonic cross-adaptation with vanillin family
        "Maple Lactone",         # coumarin analog, same sweet receptor space
        # Lactones merged: sweet-creamy receptor family overlap (Dravnieks 1985)
        "Gamma Decalactone", "Gamma Undecalactone",
        "Delta Decalactone",
    ],
    # Benzodioxole aldehydes — piperonal/heliotropin family.
    # Distinct from vanillic: methylenedioxy ring creates unique receptor binding
    # (CYP2D6 affinity, OR5A1/OR5A2 cross-talk). Sweet-powdery but NOT vanillic.
    "heliotropic_benzodioxole": [
        "Heliotropin Fleuressence",  # piperonal FTEC, heliotrope-almond
        "Heliotropal",               # piperonal aldehyde, deeper fixative
        "Helional",                  # methylenedioxy muguet, benzodioxole backbone
    ],
    "musk": [
        # Macrocyclic musks
        "Habanolide", "Exaltolide", "Ethylene Brassylate",
        "Ambretone", "Romandolide", "Zenolide", "Macrolide",
        # Polycyclic musks (cross-adapt with macrocyclics: Kraft & Fr\u00e1ter 2001)
        "Galaxolide", "Cashmeran", "Tonalide",
        # Nitro musks (all musk classes converge to single percept in complex mixtures)
        "Musk Ketone", "Musk Xylene",
    ],
    "woody_amber": [
        # Woody abstract (sesquiterpenoids)
        "Iso E Super", "Vertofix Coeur", "Vertofix", "Kephalis",
        "Timberol", "Koavone", "Amberwood F", "Cedroxyde",
        "Norlimbanol Dextro", "Clearwood",
        "Cedarwood EO", "Cedarwood oil Virginia",  # cedrene/cedrol = sesquiterpene, same backbone
        "Carrot Seed EO",       # carotol (sesquiterpene alcohol), woody-earthy receptor overlap
        # Sandalwood merged: santalols are sesquiterpenols, same terpene backbone
        # Cross-adaptation documented (Mori & Yoshii 1999)
        "Javanol", "Ebanol", "Bacdanol", "Sandalore",
        "Polysantol",
        # Amber merged: labdane-derived terpenoids share woody-amber receptor space
        # Ambrox = tricyclic terpenoid, cross-adapts with cedrene/cedrol (Sell 2006)
        "Ambrox Super", "Ambrofix", "Ambermax",
        "Amber Core",
    ],
    # phenolic members merged → balsamic_smoke
    "citrus_terpene": [
        "D-Limonene", "Bergamot FCF", "Bergamot FCF Sicilian",
        "Cedrat FCF Sicilian", "Blood Orange Sicilian",
        "Grapefruit FCF", "Red Mandarin EO",
        "Methyl Pamplemousse",
    ],
    "green_leaf": [
        "Dynascone", "Parmavert", "Leafovert",
    ],
    "muguet": [
        "Lilyreal ND", "Bourgeonal", "Nympheal", "Florol",
        "Hydroxycitronellal", "Freesia HDI",
        "Undecavertol",          # green-muguet, lily-of-valley receptor space
        "Mayol",                 # transparent muguet-lily, post-Lyral
        "Helional",              # methylenedioxy muguet-heliotrope
        "DBCA",                  # gardenia-muguet, cosmetic-floral receptor space
        "Floralozone",           # ozonic muguet, lily-of-the-valley family
    ],
    "jasmine": [
        "Hedione", "Hedione HC", "Cis Jasmone", "Benzyl Acetate",
        "Indole", "Dihydrojasmone",
        "Ylang III",             # benzyl acetate + linalool rich, jasmine-accord EO
    ],
    # amber members merged → woody_amber
    "balsamic_smoke": [
        "Benzoin Resinoid", "Olibanum Resinoid", "Styrax Resinoid",
        "Birch Tar Rectified", "Evernyl",
        "Isobutyl Quinoline",    # quinoline leather, cross-adapts with smoke-leather materials
        # Phenolic merged: phenylpropanoids cross-adapt with smoky-balsamic
        "Eugenol", "Guaiacol", "Isoeugenol",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Genetic Anosmia / Hyposmia Risk
# {material: {receptor: OR_gene, prevalence: fraction_affected,
#              severity: "anosmia" or "hyposmia"}}
# ═══════════════════════════════════════════════════════════════════════════════

GENETIC_ANOSMIA: dict[str, dict[str, Any]] = {
    "Galaxolide": {
        "receptor": "OR2J3",
        "prevalence": 0.10,         # 10% complete anosmia
        "severity": "anosmia",
        "note": "Common specific anosmia, well-documented",
    },
    "Iso E Super": {
        "receptor": "OR11H7P",
        "prevalence": 0.20,         # ~20% hyposmic
        "severity": "hyposmia",
        "note": "Variable perception — 'can you smell Molecule 01?'",
    },
    "Habanolide": {
        "receptor": "OR2J3",
        "prevalence": 0.08,
        "severity": "hyposmia",
        "note": "Related to macrocyclic musk receptor",
    },
    "Beta Ionone": {
        "receptor": "OR5A1",
        "prevalence": 0.08,         # ~8% less sensitive
        "severity": "hyposmia",
        "note": "OR5A1 rs6591536 variant",
    },
    "Alpha Ionone": {
        "receptor": "OR5A1",
        "prevalence": 0.08,
        "severity": "hyposmia",
    },
    "Alpha Irone": {
        "receptor": "OR5A1",
        "prevalence": 0.06,
        "severity": "hyposmia",
    },
    "Ambrox Super": {
        "receptor": "OR4D6",
        "prevalence": 0.05,
        "severity": "hyposmia",
        "note": "Variable amber perception",
    },
    "Ethylene Brassylate": {
        "receptor": "OR2J3",
        "prevalence": 0.06,
        "severity": "hyposmia",
    },
    "Exaltolide": {
        "receptor": "OR2J3",
        "prevalence": 0.07,
        "severity": "hyposmia",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PsychophysicsReport:
    """Psychophysical perception analysis."""
    score: float                          # 0-100 perceptual clarity score
    perceptible_count: int                # estimated distinct notes perceived
    mixture_suppression_level: str        # "minimal", "moderate", "high", "white"
    cross_adaptation_groups: list[dict]   # groups with >1 member present
    anosmia_risk_materials: list[dict]    # materials affected by genetic anosmia
    anosmia_exposure: float               # 0-1: fraction of formula at risk
    olfactory_white_risk: bool            # True if approaching olfactory white
    distinctiveness: float                # 0-1 how unique/identifiable
    diagnostics: list[str]


def score_psychophysics(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> PsychophysicsReport:
    """Score a formula's psychophysical perceptibility.

    Evaluates:
    - How many distinct notes a human can actually perceive (Laing ceiling)
    - Cross-adaptation conflicts (redundant materials)
    - Genetic anosmia exposure (what % can't smell key materials)
    - Olfactory white risk (>30 moderately-contributing components)
    """
    dilutions = dilutions or {}
    total_active = 0.0
    material_weights: dict[str, float] = {}
    diagnostics: list[str] = []

    # Build case-insensitive lookup index for cross-module compatibility
    from engine.name_utils import normalize_name
    _anosmia_lower = {normalize_name(k): v for k, v in GENETIC_ANOSMIA.items()}
    _adapt_lower: dict[str, list[str]] = {
        gn: [normalize_name(m) for m in members]
        for gn, members in CROSS_ADAPTATION_GROUPS.items()
    }

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active
        material_weights[name] = active

    if total_active == 0:
        return PsychophysicsReport(
            score=10, perceptible_count=0,
            mixture_suppression_level="none",
            cross_adaptation_groups=[], anosmia_risk_materials=[],
            anosmia_exposure=0, olfactory_white_risk=False,
            distinctiveness=0, diagnostics=["No ingredients — formula incomplete"],
        )

    # Reverse lookup: normalized name → original name (needed by all sections)
    # NOTE: aliases can cause collisions (e.g. "Hedione"/"Hedione HC" both
    # normalize to "hedione").  Use mw_lower for group-member lookup but
    # track grouped status via NORMALIZED keys to avoid missing aliases.
    mw_lower = {normalize_name(n): n for n in material_weights}

    # ── 1. Mixture suppression (Laing ceiling) ──
    # The Laing & Francis ceiling (3-4 identifiable) applies to DISCRETE
    # perceptual channels, not raw ingredient count.  Materials within the
    # same cross-adaptation group share receptor space and merge into a
    # single percept — 6 musks = 1-2 musk channels, not 6 competing notes.
    #
    # Perceptual channel = occupied cross-adaptation group OR a solo
    # material that doesn't belong to any group.

    # Determine which cross-adaptation groups are active in this formula
    grouped_normalized: set[str] = set()   # track by normalized key (alias-safe)
    grouped_materials: set[str] = set()
    active_channel_names: list[str] = []
    for group_name, members_lower in _adapt_lower.items():
        present = [mw_lower[m] for m in members_lower if m in mw_lower]
        present_keys = [m for m in members_lower if m in mw_lower]
        if present:
            active_channel_names.append(group_name)
            grouped_materials.update(present)
            grouped_normalized.update(present_keys)

    # Solo materials (not in any cross-adaptation group) = 1 channel each
    # Use normalized keys for comparison to handle alias collisions
    solo_materials = [n for n in material_weights
                      if normalize_name(n) not in grouped_normalized]
    n_channels = len(active_channel_names) + len(solo_materials)
    n_perc = n_channels

    # Laing model applied to CHANNELS, not raw materials.
    # Perfumery sweet-spot: 6-16 channels (professional niche range).
    # Complex formulas (73+ materials) with proper grouping routinely
    # produce 14-16 channels — this is architectural richness, not noise.
    # >20 risks congestion even with grouping.
    if n_perc <= 3:
        suppression = "minimal"
        laing_penalty = 0
    elif n_perc <= 6:
        suppression = "low"
        laing_penalty = 0
    elif n_perc <= 16:
        suppression = "optimal"
        laing_penalty = 0
    elif n_perc <= 22:
        suppression = "high"
        laing_penalty = 3 + (n_perc - 16) * 0.4   # gradual: 3–5.4
    else:
        suppression = "very_high"
        laing_penalty = 7 + (n_perc - 22) * 0.6   # moderate above 22

    # ── 2. Cross-adaptation analysis ──
    # With channel-based counting, redundancy WITHIN a group only matters
    # when there are so many members the group becomes unfocused.
    # 2 members = normal pair (no penalty), 3+ = mild redundancy.
    active_groups: list[dict] = []
    adaptation_penalty = 0

    for group_name, members_lower in _adapt_lower.items():
        present = [mw_lower[m] for m in members_lower if m in mw_lower]
        if len(present) >= 2:
            total_group_mass = sum(material_weights[m] for m in present)
            active_groups.append({
                "group": group_name,
                "materials": present,
                "count": len(present),
                "total_mass_uL": round(total_group_mass, 1),
            })
            # Mild penalty for 3+ members in a group (pairs are normal).
            # Only count members at *significant* dose (>10% of group mass);
            # low-dose entries are intentional subthreshold modifiers, not
            # redundancy (Perplexity-verified: subthreshold summation adds
            # complexity without competing for the same perceptual channel).
            if len(present) >= 3:
                doses = [material_weights[m] for m in present]
                total_group = sum(doses) or 1.0
                significant = sum(1 for d in doses
                                  if d / total_group > 0.10)
                if significant >= 3:
                    adaptation_penalty += (significant - 2) * 1.0

    # Cap total adaptation penalty — even densely-stacked formulas should
    # not be crushed by this single axis.
    adaptation_penalty = min(adaptation_penalty, 10)

    # ── 3. Genetic anosmia exposure ──
    anosmia_mats: list[dict] = []
    anosmia_mass = 0.0

    for name, weight in material_weights.items():
        data = _anosmia_lower.get(normalize_name(name))
        if data:
            anosmia_mats.append({
                "material": name,
                "receptor": data["receptor"],
                "prevalence": data["prevalence"],
                "severity": data["severity"],
                "mass_uL": round(weight, 1),
            })
            anosmia_mass += weight * data["prevalence"]

    anosmia_exposure = anosmia_mass / total_active if total_active > 0 else 0

    # ── 4. Olfactory white risk ──
    # Olfactory white requires many DISTINCT perceptual channels at similar
    # intensity spanning olfactory space (Weiss et al. 2012 PNAS: ≥30
    # components).  Grouped materials collapse into channels.
    white_risk = n_channels >= 30

    # ── 5. Distinctiveness ──
    # Formula is more distinctive when it has clear dominant notes
    # vs. everything at similar levels
    if material_weights:
        weights = sorted(material_weights.values(), reverse=True)
        top_3_mass = sum(weights[:3])
        distinctiveness = top_3_mass / total_active  # higher = more distinct
    else:
        distinctiveness = 0.0

    # ── Score computation ──
    # Base score rewards well-structured channel counts
    if 6 <= n_perc <= 16:
        base = 80          # sweet-spot: structured niche complexity
    elif 4 <= n_perc <= 22:
        base = 75          # good: either lean or rich
    elif n_perc < 4:
        base = 65          # too simple — not enough olfactive interest
    else:
        base = 68          # very complex — still valid but riskier

    score = base - laing_penalty - adaptation_penalty
    # Anosmia penalty: if >15% of formula mass is at genetic anosmia risk
    if anosmia_exposure > 0.15:
        score -= 10
    # Olfactory white penalty
    if white_risk:
        score -= 15
    # Distinctiveness bonus
    score += distinctiveness * 15

    score = max(0, min(100, score))

    # ── Diagnostics ──
    n_grouped = len(grouped_materials)
    n_solo = len(solo_materials)
    diagnostics.append(
        f"Perceptual channels: {n_channels} "
        f"({len(active_channel_names)} cross-adaptation groups + "
        f"{n_solo} solo materials) from {len(material_weights)} ingredients"
    )
    diagnostics.append(
        f"Channel model: {n_grouped} materials collapsed into "
        f"{len(active_channel_names)} group channels "
        f"(Laing ceiling applies to channels, not ingredients)"
    )
    if active_groups:
        diagnostics.append(
            f"Active receptor groups ({len(active_groups)} with 2+ members):"
        )
        for g in active_groups:
            diagnostics.append(
                f"  • {g['group']}: {', '.join(g['materials'])} "
                f"({g['count']} → 1 channel)"
            )
    if anosmia_mats:
        diagnostics.append(
            f"Genetic anosmia risk: {anosmia_exposure:.1%} of formula mass "
            f"affected by OR variants"
        )
        for am in anosmia_mats:
            diagnostics.append(
                f"  • {am['material']}: {am['prevalence']:.0%} population "
                f"({am['severity']}, {am['receptor']})"
            )
    if white_risk:
        diagnostics.append(
            "⚠ Olfactory white risk: ≥30 distinct channels spanning "
            "olfactory space (Weiss et al. 2012)"
        )
    diagnostics.append(f"Distinctiveness index: {distinctiveness:.2f}")

    return PsychophysicsReport(
        score=round(score, 1),
        perceptible_count=n_perc,
        mixture_suppression_level=suppression,
        cross_adaptation_groups=active_groups,
        anosmia_risk_materials=anosmia_mats,
        anosmia_exposure=round(anosmia_exposure, 4),
        olfactory_white_risk=white_risk,
        distinctiveness=round(distinctiveness, 3),
        diagnostics=diagnostics,
    )
