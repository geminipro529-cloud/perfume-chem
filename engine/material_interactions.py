"""Material Interactions — Bayesian co-occurrence and chemical interactions.

Materials don't exist in isolation. When two materials co-occur, they
change each other's probability through:

1. **Synergy co-occurrence**: Hedione + Iso E Super → Ambrox more likely
   (perfumers who reach for H+ISE usually add ambrox to complete the triad)

2. **Chemical necessity**: If rose absolute is present, citronellol and
   geraniol MUST be present (they're components). If oud is present,
   guaiacol character is inherent.

3. **Architectural requirements**: An iris formula NEEDS a fixative base
   (benzyl salicylate, or musks, or both). A chypre NEEDS oakmoss/evernyl.

4. **Mutual exclusion**: Some materials are redundant in context —
   you won't find BOTH Javanol AND Bacdanol in most formulas.

This module provides conditional probability adjustments that modify
material posteriors based on other confirmed materials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Co-occurrence rules ────────────────────────────────────────────
# (material_a, material_b) → conditional probability modifier
# If A is CONFIRMED, multiply B's posterior by this factor
# >1.0 = A's presence increases B's probability
# <1.0 = A's presence decreases B's probability

CO_OCCURRENCE_RULES: list[tuple[str, str, float, str]] = [
    # (material_a, material_b, multiplier, reason)

    # ── Synergy triads ──
    ("hedione", "iso e super", 1.5, "radiance + molecular wood triad common in luxury"),
    ("hedione", "ambrox", 1.4, "Hedione amplifies ambrox crystalline effect"),
    ("iso e super", "ambrox", 1.5, "abstract-wood + amber triad in niche"),
    ("hedione", "benzyl salicylate", 1.3, "Hedione + salicylate = radiance + diffusion cushion"),

    # ── Chemical containment (naturals contain allergens) ──
    ("rose absolute", "citronellol", 3.0, "rose absolute is 34% citronellol"),
    ("rose absolute", "geraniol", 3.0, "rose absolute is 15% geraniol"),
    ("rose absolute", "phenethyl alcohol", 2.5, "rose absolute is 60% PEA"),
    ("rose absolute", "eugenol", 2.0, "rose absolute contains 1.5% eugenol"),
    ("jasmine absolute", "benzyl acetate", 3.0, "jasmine is 25% benzyl acetate"),
    ("jasmine absolute", "indole", 2.5, "jasmine contains 2.5% indole"),
    ("jasmine absolute", "linalool", 1.8, "jasmine is 7% linalool"),
    ("bergamot", "linalool", 2.5, "bergamot is 25% linalool"),
    ("bergamot", "d-limonene", 2.0, "bergamot is 30% d-limonene"),
    ("ylang ylang", "linalool", 1.8, "ylang is 12% linalool"),
    ("neroli", "linalool", 2.5, "neroli is 35% linalool"),
    ("patchouli oil", "patchouli alcohol", 3.0, "patchouli oil is patchoulol"),

    # ── Architectural requirements ──
    ("alpha irone", "benzyl salicylate", 1.4, "iris base needs salicylate cushion"),
    ("alpha irone", "ambrox", 1.3, "iris + ambrox common in orris modern"),
    ("alpha irone", "coumarin", 1.3, "iris + coumarin = powdery depth"),
    ("alpha irone", "hedione", 1.4, "iris + hedione = lifted iris radiance"),
    ("evernyl", "benzyl salicylate", 1.3, "chypre needs salicylate body"),
    ("evernyl", "patchouli oil", 1.5, "chypre = oakmoss + patchouli"),
    ("oud oil", "rose absolute", 1.5, "oud-rose pairing is major genre"),
    ("oud oil", "ambrox", 1.3, "oud + ambrox = modern oud finish"),

    # ── Musk base dynamics ──
    ("galaxolide", "habanolide", 0.7, "typically one polycyclic OR macrocyclic musk, not both at high dose"),
    ("galaxolide", "cashmeran", 1.2, "polycyclic + cashmeran for warm musk"),
    ("habanolide", "hedione", 1.3, "macrocyclic + hedione = skin-scent intimacy"),

    # ── Woody base ──
    ("iso e super", "cedarwood", 1.2, "ISE + cedarwood = layered wood"),
    ("iso e super", "cashmeran", 1.3, "ISE + cashmeran = warm abstract wood"),
    ("vetiver", "patchouli oil", 1.2, "earthy base pairing"),

    # ── Sandalwood exclusions ──
    ("javanol", "bacdanol", 0.6, "typically one sandalwood captive in formula"),
    ("javanol", "ebanol", 0.6, "typically one sandalwood captive"),

    # ── Perfumer house style ──
    ("ambrox", "rose absolute", 1.3, "Amouage signature pairing"),
    ("habanolide", "hedione", 1.4, "Cavallier signature pair"),

    # ── Iris palette ──
    ("alpha irone", "alpha-isomethyl ionone", 1.5, "real + synthetic iris layering"),
    ("alpha irone", "orivone", 1.3, "alpha irone + orivone = buttery iris"),
    ("alpha-isomethyl ionone", "coumarin", 1.4, "powdery iris base"),

    # ── Floral architecture ──
    ("hydroxycitronellal", "linalool", 1.3, "muguet + floral heart"),
    ("indole", "hedione", 1.4, "narcotic + radiance = complex jasmine"),

    # ── Leather-smoke ──
    ("ibq", "guaiacol", 1.5, "dirty leather + smoke = animalic base"),
    ("suederal", "ibq", 0.7, "clean suede vs dirty leather — pick one primary"),

    # ── Oriental base ──
    ("labdanum", "benzyl benzoate", 1.3, "amber base fixation"),
    ("vanillin", "coumarin", 1.4, "gourmand-oriental base"),
    ("vanillin", "benzyl benzoate", 1.3, "vanilla fixation"),
]

# ── Architectural templates ────────────────────────────────────────
# If the fragrance matches a template, boost template-required materials

ARCHITECTURAL_TEMPLATES: dict[str, dict] = {
    "iris_soliflore": {
        "required": ["alpha irone", "benzyl salicylate"],
        "expected": ["hedione", "ambrox", "coumarin", "alpha-isomethyl ionone"],
        "boost_if_template": 1.3,
    },
    "oud_rose": {
        "required": ["oud oil", "rose absolute"],
        "expected": ["ambrox", "benzyl salicylate", "patchouli oil"],
        "boost_if_template": 1.3,
    },
    "modern_chypre": {
        "required": ["evernyl", "patchouli oil"],
        "expected": ["bergamot", "benzyl salicylate", "hedione"],
        "boost_if_template": 1.3,
    },
    "woody_amber": {
        "required": ["iso e super", "ambrox"],
        "expected": ["hedione", "cedarwood", "cashmeran"],
        "boost_if_template": 1.2,
    },
    "white_floral": {
        "required": ["hedione"],
        "expected": ["benzyl salicylate", "indole", "hydroxycitronellal",
                     "jasmine absolute", "linalool"],
        "boost_if_template": 1.2,
    },
    "lavender_fougère": {
        "required": ["lavender oil", "coumarin"],
        "expected": ["hedione", "evernyl", "cedarwood"],
        "boost_if_template": 1.2,
    },
}


@dataclass
class InteractionEffect:
    """One material-material interaction effect."""
    source_material: str
    target_material: str
    multiplier: float
    reason: str
    source_confirmed: bool


@dataclass
class TemplateMatch:
    """An architectural template match."""
    template_name: str
    match_score: float       # 0–1
    matched_required: list[str]
    missing_required: list[str]
    matched_expected: list[str]
    boost_factor: float


@dataclass
class InteractionAnalysisResult:
    """Complete interaction analysis."""
    target_name: str
    effects: list[InteractionEffect]
    template_matches: list[TemplateMatch]
    adjusted_posteriors: dict[str, float]   # material → adjusted posterior
    strongest_interactions: list[tuple[str, str, float]]  # top boosted pairs
    score: float             # 0–100


def analyze_material_interactions(
    target_name: str,
    material_posteriors: dict[str, float],
    confirmed_materials: Optional[list[str]] = None,
    probable_materials: Optional[list[str]] = None,
) -> InteractionAnalysisResult:
    """Apply co-occurrence and architectural rules to adjust posteriors.

    Args:
        target_name: Fragrance name.
        material_posteriors: material → current posterior probability.
        confirmed_materials: Materials with CONFIRMED status.
        probable_materials: Materials with PROBABLE status.

    Returns:
        InteractionAnalysisResult with adjusted posteriors.
    """
    if confirmed_materials is None:
        confirmed_materials = []
    if probable_materials is None:
        probable_materials = []

    confirmed_set = {m.lower().strip() for m in confirmed_materials}
    probable_set = {m.lower().strip() for m in probable_materials}
    all_known = confirmed_set | probable_set

    # Normalize posteriors keys
    posteriors = {k.lower().strip(): v for k, v in material_posteriors.items()}
    adjusted = dict(posteriors)
    effects: list[InteractionEffect] = []
    strongest: list[tuple[str, str, float]] = []

    # Apply co-occurrence rules
    for mat_a, mat_b, multiplier, reason in CO_OCCURRENCE_RULES:
        a_key = mat_a.lower().strip()
        b_key = mat_b.lower().strip()

        # If A is confirmed/probable, adjust B's posterior
        if a_key in all_known and b_key in adjusted:
            old_val = adjusted[b_key]
            is_confirmed = a_key in confirmed_set
            # Dampen multiplier for merely probable sources
            effective_mult = multiplier if is_confirmed else 1.0 + (multiplier - 1.0) * 0.5
            new_val = min(0.99, old_val * effective_mult)
            adjusted[b_key] = new_val

            effects.append(InteractionEffect(
                source_material=a_key,
                target_material=b_key,
                multiplier=effective_mult,
                reason=reason,
                source_confirmed=is_confirmed,
            ))

            if effective_mult > 1.1:
                strongest.append((a_key, b_key, effective_mult))

        # Symmetric: if B is confirmed, adjust A
        if b_key in all_known and a_key in adjusted:
            old_val = adjusted[a_key]
            is_confirmed = b_key in confirmed_set
            effective_mult = multiplier if is_confirmed else 1.0 + (multiplier - 1.0) * 0.5
            new_val = min(0.99, old_val * effective_mult)
            adjusted[a_key] = new_val

            effects.append(InteractionEffect(
                source_material=b_key,
                target_material=a_key,
                multiplier=effective_mult,
                reason=reason + " (symmetric)",
                source_confirmed=is_confirmed,
            ))

    # Architectural template matching
    template_matches: list[TemplateMatch] = []
    for tmpl_name, tmpl_data in ARCHITECTURAL_TEMPLATES.items():
        required = [r.lower() for r in tmpl_data["required"]]
        expected = [e.lower() for e in tmpl_data["expected"]]

        matched_req = [r for r in required if r in all_known]
        missing_req = [r for r in required if r not in all_known]
        matched_exp = [e for e in expected if e in all_known or e in adjusted]

        if len(matched_req) >= len(required):
            # All required present → boost expected materials
            match_score = 1.0
            boost = tmpl_data["boost_if_template"]
            for exp_mat in expected:
                if exp_mat in adjusted:
                    adjusted[exp_mat] = min(0.99, adjusted[exp_mat] * boost)
        elif len(matched_req) >= len(required) - 1:
            match_score = len(matched_req) / len(required)
            boost = 1.0 + (tmpl_data["boost_if_template"] - 1.0) * 0.5
            for exp_mat in expected:
                if exp_mat in adjusted:
                    adjusted[exp_mat] = min(0.99, adjusted[exp_mat] * boost)
        else:
            match_score = len(matched_req) / max(len(required), 1)
            boost = 1.0

        if match_score > 0.3:
            template_matches.append(TemplateMatch(
                template_name=tmpl_name,
                match_score=match_score,
                matched_required=matched_req,
                missing_required=missing_req,
                matched_expected=matched_exp,
                boost_factor=boost,
            ))

    # Sort strongest interactions
    strongest.sort(key=lambda x: x[2], reverse=True)

    # Score: how much the interactions constrain the formula
    if not effects:
        score = 0.0
    else:
        n_effects = min(len(effects), 20)
        avg_mult = sum(abs(e.multiplier - 1.0) for e in effects) / len(effects)
        template_bonus = sum(tm.match_score * 10 for tm in template_matches)
        score = min(100.0, n_effects * 2 + avg_mult * 50 + template_bonus)

    return InteractionAnalysisResult(
        target_name=target_name,
        effects=effects,
        template_matches=template_matches,
        adjusted_posteriors=adjusted,
        strongest_interactions=strongest[:10],
        score=score,
    )
