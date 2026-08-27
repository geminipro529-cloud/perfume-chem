"""Non-quantitative allergen-source diagnostic for fragrance labels.

A package declaration supports thresholded constituent presence under the
applicable label regime. It does not disclose a constituent concentration,
the source raw material, or a natural-material dose. Ingredients below 1% may
be listed in any order, and natural-complex composition varies by batch.
Accordingly this module exposes possible sources but withholds natural
concentration estimates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

# ── GC-MS composition of natural extracts (% by weight) ────────────
# Each natural contains a mix of allergens in known proportions.
# Sources: ISO standards, supplier COA data, Arctander, Bauer/Garbe

NATURAL_COMPOSITIONS: dict[str, dict[str, float]] = {
    "rose absolute": {
        "citronellol": 34.0,
        "geraniol": 15.0,
        "nerol": 5.0,
        "linalool": 2.0,
        "phenethyl alcohol": 60.0,
        "eugenol": 1.5,
        "farnesol": 2.5,
        "benzyl alcohol": 1.0,
    },
    "rose otto": {
        "citronellol": 38.0,
        "geraniol": 18.0,
        "nerol": 8.0,
        "linalool": 2.5,
        "eugenol": 1.0,
        "farnesol": 3.0,
    },
    "jasmine absolute": {
        "benzyl acetate": 25.0,
        "linalool": 7.0,
        "benzyl alcohol": 10.0,
        "indole": 2.5,
        "cis-jasmone": 3.0,
        "eugenol": 2.0,
        "farnesol": 1.5,
        "benzyl benzoate": 15.0,
    },
    "bergamot oil": {
        "linalool": 25.0,
        "linalyl acetate": 35.0,
        "d-limonene": 30.0,
        "geraniol": 1.5,
    },
    "lavender oil": {
        "linalool": 30.0,
        "linalyl acetate": 35.0,
    },
    "ylang ylang": {
        "linalool": 12.0,
        "geraniol": 5.0,
        "benzyl acetate": 8.0,
        "benzyl benzoate": 10.0,
        "eugenol": 3.0,
        "farnesol": 5.0,
        "benzyl alcohol": 2.0,
    },
    "neroli oil": {
        "linalool": 35.0,
        "linalyl acetate": 10.0,
        "geraniol": 3.0,
        "farnesol": 4.0,
        "nerol": 5.0,
        "indole": 0.3,
    },
    "clove bud oil": {
        "eugenol": 80.0,
    },
    "patchouli oil": {
        "patchouli alcohol": 35.0,
    },
    "vetiver oil": {
        "vetiver": 100.0,   # placeholder — vetiver is vetiverol complex
    },
    "geranium oil": {
        "citronellol": 25.0,
        "geraniol": 15.0,
        "linalool": 5.0,
    },
    "frankincense oil": {
        "linalool": 3.0,
        "d-limonene": 15.0,
    },
    "sandalwood oil": {
        # santalol not an EU allergen — so doesn't constrain via allergens
    },
    "oud oil": {
        # agarospirol not an EU allergen — limited allergen utility
    },
    "labdanum absolute": {
        "eugenol": 1.0,
        "benzyl alcohol": 0.5,
    },
}

# ── Allergen → sources breakdown ───────────────────────────────────

ALLERGEN_SOURCES: dict[str, list[tuple[str, float]]] = {}
for nat_name, composition in NATURAL_COMPOSITIONS.items():
    for allergen, pct in composition.items():
        if allergen not in ALLERGEN_SOURCES:
            ALLERGEN_SOURCES[allergen] = []
        ALLERGEN_SOURCES[allergen].append((nat_name, pct))


@dataclass
class AllergenEquation:
    """One equation in the system: allergen constrains source naturals."""
    allergen: str
    declared_position: int     # Position on the box list (earlier = more)
    estimated_pct_range: tuple[float, float]   # min, max in concentrate
    contributing_sources: list[tuple[str, float]]  # (natural, % in natural)


@dataclass
class SolvedNatural:
    """A natural extract with back-calculated concentration range."""
    material: str
    min_pct: float
    max_pct: float
    best_estimate_pct: float
    constraining_allergens: list[str]
    confidence: float          # 0–1: how tight the constraint is
    method: str                # "ratio", "single_source", "least_squares"


@dataclass
class AllergenSolverResult:
    """Fail-closed allergen-source diagnostic."""
    target_name: str
    equations: list[AllergenEquation]
    solved_naturals: list[SolvedNatural]
    residual_allergens: list[str]     # Allergens not explained by naturals
    deficit_analysis: dict[str, float]  # Allergen deficits suggesting synthetics
    score: float               # 0–100
    authority: str
    quantitative_authority: bool
    limitations: tuple[str, ...]


# ── Allergen position → concentration estimation ───────────────────
# EU requires listing allergens by descending concentration.
# We estimate ranges based on position and typical formulation levels.

def _declaration_to_pct_range(
    concentrate_pct: float = 25.0,
) -> tuple[float, float]:
    """Return only the label-threshold lower bound and a non-informative cap."""
    if not math.isfinite(concentrate_pct) or not 0 < concentrate_pct <= 100:
        raise ValueError("concentrate_pct must be finite and in (0, 100]")
    # For leave-on products, declaration threshold is 0.001% (10 ppm) in product
    # In a 25% concentrate, that's 0.004% in concentrate
    min_declaration_pct = 0.001 / (concentrate_pct / 100.0) * 100.0
    return (min_declaration_pct, 100.0)


def _solve_two_source_ratio(
    allergen_a: str,
    allergen_b: str,
    source_a: str,
    source_b: str,
    compositions: dict[str, dict[str, float]],
    ratio_a_to_b: float,
) -> tuple[float, float]:
    """Solve for two sources using the ratio of two allergens.

    If citronellol/geraniol ratio = R, and both come from rose (c%, g%)
    and source_b (c2%, g2%), solve the system.

    Returns (source_a_pct, source_b_pct) in concentrate.
    """
    comp_a = compositions.get(source_a, {})
    comp_b = compositions.get(source_b, {})

    # Get allergen content in each source
    a_in_src_a = comp_a.get(allergen_a, 0)
    b_in_src_a = comp_a.get(allergen_b, 0)
    a_in_src_b = comp_b.get(allergen_a, 0)
    b_in_src_b = comp_b.get(allergen_b, 0)

    if b_in_src_a == 0 and b_in_src_b == 0:
        return (0.0, 0.0)

    # This is a simplified solver for the dominant case
    # Ratio R = (S1*a1 + S2*a2) / (S1*b1 + S2*b2)
    # In the common rose+jasmine case, jasmine has negligible citronellol/geraniol
    # so it simplifies to R ≈ a1/b1 of the dominant source
    if a_in_src_b < 0.5 and b_in_src_b < 0.5:
        # Source B doesn't contribute these allergens meaningfully
        # Just check that the ratio matches source A
        if b_in_src_a > 0:
            implied_ratio = a_in_src_a / b_in_src_a
            if abs(implied_ratio - ratio_a_to_b) / max(implied_ratio, 0.01) < 0.3:
                return (1.0, 0.0)  # Consistent with source A alone

    return (0.0, 0.0)  # Fallback — insufficient data


def solve_allergen_ratios(
    target_name: str,
    declared_allergens: list[str],
    concentrate_pct: float = 25.0,
    known_ratios: Optional[dict[str, float]] = None,
    additional_constraints: Optional[dict[str, tuple[float, float]]] = None,
) -> AllergenSolverResult:
    """Expose possible constituent sources without estimating natural doses.

    Args:
        target_name: Fragrance name.
        declared_allergens: Allergens transcribed from the package.
        concentrate_pct: Product concentration %.
        known_ratios: Retained for API compatibility; insufficient for source
            attribution without measured constituent concentrations and a
            source-complete mixture model.
        additional_constraints: Retained for API compatibility; not promoted
            through this label-only diagnostic.

    Returns:
        A non-quantitative result. ``solved_naturals`` is always empty.
    """
    equations: list[AllergenEquation] = []
    residuals: list[str] = []
    _ = known_ratios, additional_constraints

    for pos, allergen in enumerate(declared_allergens, 1):
        allergen_key = allergen.lower().strip()
        if not allergen_key:
            continue
        pct_range = _declaration_to_pct_range(concentrate_pct)
        sources = ALLERGEN_SOURCES.get(allergen_key, [])
        equations.append(AllergenEquation(
            allergen=allergen_key,
            declared_position=pos,
            estimated_pct_range=pct_range,
            contributing_sources=sources,
        ))
        residuals.append(allergen_key)

    return AllergenSolverResult(
        target_name=target_name,
        equations=equations,
        solved_naturals=[],
        residual_allergens=residuals,
        deficit_analysis={},
        score=0.0,
        authority="UNSUPPORTED_FROM_LABEL_ORDER",
        quantitative_authority=False,
        limitations=(
            "Package position does not quantify constituents below one percent.",
            "A declared constituent may come from a standalone chemical, one or more "
            "natural complex substances, or both.",
            "Natural-complex composition varies by source and batch.",
            "Measured constituent concentrations and a source-complete model are "
            "required before raw-material attribution.",
        ),
    )
