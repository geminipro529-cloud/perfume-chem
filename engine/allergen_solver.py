"""Allergen Ratio Solver — Back-calculates natural extract %% from declared allergens.

When a fragrance box declares allergens (EU cosmetics regulation), each
allergen has a specific GC-MS composition in natural extracts. By treating
the allergen declarations as simultaneous equations, we can solve for the
concentration of each natural raw material.

Example:
  - Citronellol declared at position X → comes from rose absolute (34%)
    and geraniol from rose (15%), jasmine (trace)
  - Linalool declared at position Y → comes from bergamot (25%),
    lavender (30%), rose (2%)
  - Solving the system constrains rose absolute to ~2.8%, jasmine to ~2.3%

This is the generalized version of the back-calculation done for Opus V.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import math


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
    """Complete allergen ratio solution."""
    target_name: str
    equations: list[AllergenEquation]
    solved_naturals: list[SolvedNatural]
    residual_allergens: list[str]     # Allergens not explained by naturals
    deficit_analysis: dict[str, float]  # Allergen deficits suggesting synthetics
    score: float               # 0–100


# ── Allergen position → concentration estimation ───────────────────
# EU requires listing allergens by descending concentration.
# We estimate ranges based on position and typical formulation levels.

def _position_to_pct_range(
    position: int,
    total_allergens: int,
    concentrate_pct: float = 25.0,
) -> tuple[float, float]:
    """Estimate allergen % in CONCENTRATE from its box position.

    Position 1 = highest concentration; descending order required by EU regulation.
    Returns (min_pct, max_pct) of the allergen in the concentrate.
    """
    # For leave-on products, declaration threshold is 0.001% (10 ppm) in product
    # In a 25% concentrate, that's 0.004% in concentrate
    min_declaration_pct = 0.001 / (concentrate_pct / 100.0) * 100.0

    # Estimate: first allergen typically 0.5–3% of concentrate
    # Last allergen typically 0.004–0.1%
    if total_allergens <= 1:
        return (0.01, 3.0)

    # Log-spaced decay between first and last
    max_first = 3.0
    min_last = min_declaration_pct

    log_max = math.log(max_first)
    log_min = math.log(max(min_last, 0.001))
    fraction = (position - 1) / max(total_allergens - 1, 1)

    center = math.exp(log_max - fraction * (log_max - log_min))

    return (center * 0.5, center * 2.0)


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
    """Solve for natural extract concentrations from allergen declarations.

    Args:
        target_name: Fragrance name.
        declared_allergens: Ordered list of allergens from box (1st = highest).
        concentrate_pct: Product concentration %.
        known_ratios: Known allergen ratios, e.g. {"citronellol:geraniol": 1.94}.
        additional_constraints: Extra constraints, e.g. {"rose absolute": (2.0, 4.0)}.

    Returns:
        AllergenSolverResult with solved naturals and per-category score.
    """
    n = len(declared_allergens)
    equations: list[AllergenEquation] = []
    solved: dict[str, SolvedNatural] = {}
    residuals: list[str] = []
    deficits: dict[str, float] = {}

    if known_ratios is None:
        known_ratios = {}
    if additional_constraints is None:
        additional_constraints = {}

    # Build equations from each declared allergen
    for pos, allergen in enumerate(declared_allergens, 1):
        allergen_key = allergen.lower().strip()
        pct_range = _position_to_pct_range(pos, n, concentrate_pct)
        sources = ALLERGEN_SOURCES.get(allergen_key, [])

        equations.append(AllergenEquation(
            allergen=allergen_key,
            declared_position=pos,
            estimated_pct_range=pct_range,
            contributing_sources=sources,
        ))

        if not sources:
            residuals.append(allergen_key)
            continue

        # For single-source allergens, directly estimate the natural
        single_sources = [(name, pct) for name, pct in sources if pct > 5.0]
        if len(single_sources) == 1:
            src_name, src_allergen_pct = single_sources[0]
            # natural_pct = allergen_pct_in_concentrate / (allergen_% in natural / 100)
            min_nat = pct_range[0] / (src_allergen_pct / 100.0)
            max_nat = pct_range[1] / (src_allergen_pct / 100.0)

            if src_name in solved:
                # Tighten existing bounds
                existing = solved[src_name]
                existing.min_pct = max(existing.min_pct, min_nat)
                existing.max_pct = min(existing.max_pct, max_nat)
                existing.best_estimate_pct = (existing.min_pct + existing.max_pct) / 2
                existing.constraining_allergens.append(allergen_key)
                existing.confidence = min(1.0, existing.confidence + 0.2)
            else:
                solved[src_name] = SolvedNatural(
                    material=src_name,
                    min_pct=min_nat,
                    max_pct=max_nat,
                    best_estimate_pct=(min_nat + max_nat) / 2,
                    constraining_allergens=[allergen_key],
                    confidence=0.5,
                    method="single_source",
                )
        elif len(single_sources) > 1:
            # Multiple sources — mark as unsolved for now
            for src_name, src_pct in single_sources:
                if src_name not in solved:
                    min_nat = pct_range[0] / (src_pct / 100.0)
                    max_nat = pct_range[1] / (src_pct / 100.0)
                    solved[src_name] = SolvedNatural(
                        material=src_name,
                        min_pct=0.0,
                        max_pct=max_nat,
                        best_estimate_pct=max_nat / 3,
                        constraining_allergens=[allergen_key],
                        confidence=0.3,
                        method="multi_source_bound",
                    )

    # Apply known ratios for tighter constraints
    for ratio_key, ratio_val in known_ratios.items():
        parts = ratio_key.split(":")
        if len(parts) == 2:
            a_name, b_name = parts[0].strip().lower(), parts[1].strip().lower()
            # Find equations for both allergens
            eq_a = next((e for e in equations if e.allergen == a_name), None)
            eq_b = next((e for e in equations if e.allergen == b_name), None)
            if eq_a and eq_b:
                # Try rose ratio analysis
                for source_name in ["rose absolute", "rose otto"]:
                    comp = NATURAL_COMPOSITIONS.get(source_name, {})
                    if a_name in comp and b_name in comp:
                        expected_ratio = comp[a_name] / max(comp[b_name], 0.01)
                        if abs(expected_ratio - ratio_val) / max(expected_ratio, 0.01) < 0.25:
                            # Ratio matches this source — refine
                            mid_a = sum(eq_a.estimated_pct_range) / 2
                            nat_pct = mid_a / (comp[a_name] / 100.0)
                            if source_name in solved:
                                solved[source_name].best_estimate_pct = nat_pct
                                solved[source_name].confidence = min(1.0, solved[source_name].confidence + 0.3)
                                solved[source_name].method = "ratio"
                            else:
                                solved[source_name] = SolvedNatural(
                                    material=source_name,
                                    min_pct=nat_pct * 0.7,
                                    max_pct=nat_pct * 1.3,
                                    best_estimate_pct=nat_pct,
                                    constraining_allergens=[a_name, b_name],
                                    confidence=0.75,
                                    method="ratio",
                                )

    # Apply additional external constraints
    for mat_name, (cmin, cmax) in additional_constraints.items():
        if mat_name in solved:
            solved[mat_name].min_pct = max(solved[mat_name].min_pct, cmin)
            solved[mat_name].max_pct = min(solved[mat_name].max_pct, cmax)
            solved[mat_name].best_estimate_pct = (solved[mat_name].min_pct + solved[mat_name].max_pct) / 2
            solved[mat_name].confidence = min(1.0, solved[mat_name].confidence + 0.2)

    # Deficit analysis: allergens not fully explained by solved naturals
    for eq in equations:
        total_explained = 0.0
        for src_name, src_pct in eq.contributing_sources:
            if src_name in solved:
                total_explained += solved[src_name].best_estimate_pct * (src_pct / 100.0)
        mid_declared = sum(eq.estimated_pct_range) / 2
        deficit = mid_declared - total_explained
        if deficit > 0.01:
            deficits[eq.allergen] = deficit

    # Score: more solved naturals with tighter bounds = higher score
    if not solved:
        score = 0.0
    else:
        avg_conf = sum(s.confidence for s in solved.values()) / len(solved)
        spread = sum(
            1.0 - min(1.0, (s.max_pct - s.min_pct) / max(s.best_estimate_pct, 0.1))
            for s in solved.values()
        ) / len(solved)
        n_solved = min(len(solved), 8)
        score = min(100.0, (avg_conf * 40 + spread * 30 + n_solved * 5))

    return AllergenSolverResult(
        target_name=target_name,
        equations=equations,
        solved_naturals=list(solved.values()),
        residual_allergens=residuals,
        deficit_analysis=deficits,
        score=score,
    )
