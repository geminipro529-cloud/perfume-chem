"""
Regulatory timeline consistency module for perfume reconstruction engine.

Checks IFRA amendment dates against fragrance launch year to assess whether
hypothesized formula materials comply with the standards in force at launch
and at any known reformulation date.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

IFRA_AMENDMENTS: dict[str, dict] = {
    "amendment_46": {
        "effective_year": 2011,
        "key_restrictions": {
            "oakmoss": {"action": "restricted", "max_pct_cat4": 0.1},
            "treemoss": {"action": "restricted", "max_pct_cat4": 0.1},
            "lyral": {"action": "restricted", "max_pct_cat4": 1.0},
            "musk ambrette": {"action": "prohibited", "max_pct_cat4": 0.0},
            "6-methylcoumarin": {"action": "restricted", "max_pct_cat4": 0.01},
        },
    },
    "amendment_47": {
        "effective_year": 2013,
        "key_restrictions": {
            "lyral": {"action": "restricted", "max_pct_cat4": 0.5},
            "eugenol": {"action": "restricted", "max_pct_cat4": 0.5},
            "isoeugenol": {"action": "restricted", "max_pct_cat4": 0.02},
            "citral": {"action": "restricted", "max_pct_cat4": 1.0},
        },
    },
    "amendment_48": {
        "effective_year": 2015,
        "key_restrictions": {
            "lyral": {"action": "prohibited", "max_pct_cat4": 0.0},
            "lilial": {"action": "restricted", "max_pct_cat4": 0.01},
            "atraanol": {"action": "prohibited", "max_pct_cat4": 0.0},
            "chloroatranol": {"action": "prohibited", "max_pct_cat4": 0.0},
            "HICC": {"action": "prohibited", "max_pct_cat4": 0.0},
            "hydroxycitronellal": {"action": "restricted", "max_pct_cat4": 1.0},
        },
    },
    "amendment_49": {
        "effective_year": 2019,
        "key_restrictions": {
            "lilial": {"action": "prohibited", "max_pct_cat4": 0.0},
            "eugenol": {"action": "restricted", "max_pct_cat4": 0.5},
            "isoeugenol": {"action": "restricted", "max_pct_cat4": 0.02},
            "methyl eugenol": {"action": "prohibited", "max_pct_cat4": 0.0},
            "estragole": {"action": "restricted", "max_pct_cat4": 0.01},
            "safrole": {"action": "prohibited", "max_pct_cat4": 0.0},
        },
    },
    "amendment_50": {
        "effective_year": 2022,
        "key_restrictions": {
            "eugenol": {"action": "restricted", "max_pct_cat4": 0.5},
            "benzyl benzoate": {"action": "restricted", "max_pct_cat4": 2.0},
            "benzyl salicylate": {"action": "restricted", "max_pct_cat4": 3.0},
            "farnesol": {"action": "restricted", "max_pct_cat4": 0.2},
            "geraniol": {"action": "restricted", "max_pct_cat4": 1.6},
            "coumarin": {"action": "restricted", "max_pct_cat4": 1.0},
            "hydroxycitronellal": {"action": "restricted", "max_pct_cat4": 1.0},
            "alpha-isomethyl ionone": {"action": "restricted", "max_pct_cat4": 4.0},
            "cinnamaldehyde": {"action": "restricted", "max_pct_cat4": 0.05},
            "hexyl cinnamal": {"action": "restricted", "max_pct_cat4": 0.5},
            "linalool": {"action": "restricted", "max_pct_cat4": 16.0},
            "citronellol": {"action": "restricted", "max_pct_cat4": 10.0},
            "limonene": {"action": "restricted", "max_pct_cat4": 15.0},
        },
    },
}

REFORMULATION_DATES: dict[str, int] = {
    "chanel no 5": 2012,
    "miss dior": 2013,
    "shalimar": 2012,
    "mitsouko": 2013,
    "arpege": 2011,
    "vol de nuit": 2012,
    "opium": 2012,
    "tresor": 2012,
}

# Posterior thresholds for penalty severity
_CONFIRMED_THRESHOLD = 0.7
_PROBABLE_THRESHOLD = 0.5
_SPECULATIVE_THRESHOLD = 0.3


@dataclass
class RegulatoryConstraint:
    material: str
    amendment: str
    amendment_year: int
    fragrance_year: int
    action: str
    pre_restriction_allowed: bool
    max_pct_at_launch: Optional[float]
    current_max_pct: Optional[float]
    needs_reformulation_check: bool
    plausibility_note: str = ""


@dataclass
class RegulatoryAnalysisResult:
    target_name: str
    fragrance_year: int
    applicable_amendments: list[str]
    constraints: list[RegulatoryConstraint] = field(default_factory=list)
    prohibited_at_launch: list[str] = field(default_factory=list)
    restricted_since_launch: list[str] = field(default_factory=list)
    always_compliant: list[str] = field(default_factory=list)
    score: float = 0.0


def _amendments_in_force_at(year: int) -> list[str]:
    """Return amendment keys whose effective_year <= year, sorted chronologically."""
    return [
        k for k, v in IFRA_AMENDMENTS.items()
        if v["effective_year"] <= year
    ]


def _earliest_restriction(
    material_lower: str, by_year: int
) -> Optional[dict]:
    """Return the earliest amendment entry that restricts/bans the material on or before by_year."""
    candidates = []
    for amend_key, amend_data in IFRA_AMENDMENTS.items():
        if amend_data["effective_year"] > by_year:
            continue
        if material_lower in amend_data["key_restrictions"]:
            candidates.append(
                (amend_data["effective_year"], amend_key, amend_data["key_restrictions"][material_lower])
            )
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    year, key, restriction = candidates[0]
    return {"amendment": key, "year": year, "restriction": restriction}


def _strictest_restriction_at(
    material_lower: str, by_year: int
) -> Optional[dict]:
    """
    Return the most restrictive entry for a material across all amendments
    in force by `by_year`.  Most restrictive = lowest max_pct_cat4 (or prohibited).
    """
    candidates = []
    for amend_key, amend_data in IFRA_AMENDMENTS.items():
        if amend_data["effective_year"] > by_year:
            continue
        if material_lower in amend_data["key_restrictions"]:
            r = amend_data["key_restrictions"][material_lower]
            candidates.append(
                (r["max_pct_cat4"], amend_data["effective_year"], amend_key, r)
            )
    if not candidates:
        return None
    # Sort by max_pct ascending (most restrictive first), then by year descending (latest)
    candidates.sort(key=lambda x: (x[0], -x[1]))
    max_pct, year, key, restriction = candidates[0]
    return {"amendment": key, "year": year, "restriction": restriction}


def _any_restriction_after(
    material_lower: str, after_year: int
) -> Optional[dict]:
    """Return the earliest amendment entry restricting the material AFTER after_year."""
    candidates = []
    for amend_key, amend_data in IFRA_AMENDMENTS.items():
        if amend_data["effective_year"] <= after_year:
            continue
        if material_lower in amend_data["key_restrictions"]:
            candidates.append(
                (amend_data["effective_year"], amend_key, amend_data["key_restrictions"][material_lower])
            )
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    year, key, restriction = candidates[0]
    return {"amendment": key, "year": year, "restriction": restriction}


def _current_restriction(material_lower: str) -> Optional[dict]:
    """Return strictest restriction across all known amendments."""
    max_year = max(v["effective_year"] for v in IFRA_AMENDMENTS.values())
    return _strictest_restriction_at(material_lower, max_year)


def analyze_regulatory_timeline(
    target_name: str,
    fragrance_year: int,
    material_posteriors: dict[str, float],
    concentrate_pct: float = 25.0,
    known_reformulation_year: Optional[int] = None,
) -> RegulatoryAnalysisResult:
    """
    Assess IFRA regulatory consistency for a hypothesized formula.

    Parameters
    ----------
    target_name:
        Name of the fragrance being reconstructed.
    fragrance_year:
        Year the fragrance was originally launched.
    material_posteriors:
        Mapping of material name → posterior probability (0–1).
    concentrate_pct:
        Estimated concentrate percentage in the finished EdP/EdT (default 25%).
        Used to contextualise whether a restricted limit is relevant.
    known_reformulation_year:
        If the fragrance is known to have been reformulated, re-evaluate with
        that year's standards and flag materials whose status changed.

    Returns
    -------
    RegulatoryAnalysisResult
    """
    # Resolve known reformulation year from lookup if not supplied
    if known_reformulation_year is None:
        known_reformulation_year = REFORMULATION_DATES.get(target_name.lower())

    applicable_amendments = _amendments_in_force_at(fragrance_year)

    # Effective evaluation year: if reformulated, use that year for current compliance
    eval_year = known_reformulation_year if known_reformulation_year else fragrance_year

    constraints: list[RegulatoryConstraint] = []
    prohibited_at_launch: list[str] = []
    restricted_since_launch: list[str] = []
    always_compliant: list[str] = []

    for material, posterior in material_posteriors.items():
        if posterior < _SPECULATIVE_THRESHOLD:
            continue

        mat_lower = material.lower()

        # Check status at launch year
        launch_restriction = _strictest_restriction_at(mat_lower, fragrance_year)
        # Check for any new restrictions imposed after launch
        post_launch = _any_restriction_after(mat_lower, fragrance_year)
        # Current status (or at reformulation year)
        current = _strictest_restriction_at(mat_lower, eval_year)

        if launch_restriction is not None:
            action_at_launch = launch_restriction["restriction"]["action"]
            max_at_launch: Optional[float] = launch_restriction["restriction"]["max_pct_cat4"]
            current_max: Optional[float] = current["restriction"]["max_pct_cat4"] if current else max_at_launch

            pre_restriction_allowed = action_at_launch != "prohibited"
            needs_refo_check = (
                known_reformulation_year is not None
                and post_launch is not None
                and post_launch["year"] <= known_reformulation_year
            )

            if action_at_launch == "prohibited":
                note = (
                    f"{material} was prohibited at launch ({fragrance_year}) under "
                    f"{launch_restriction['amendment']} (effective {launch_restriction['year']}). "
                    f"Presence in formula is a regulatory inconsistency."
                )
                prohibited_at_launch.append(material)
            else:
                note = (
                    f"{material} was restricted to {max_at_launch}% (cat4) at launch "
                    f"under {launch_restriction['amendment']} (effective {launch_restriction['year']})."
                )
                if needs_refo_check:
                    note += (
                        f" Post-reformulation ({known_reformulation_year}) stricter limits apply; "
                        f"current limit: {current_max}% (cat4)."
                    )

            constraint = RegulatoryConstraint(
                material=material,
                amendment=launch_restriction["amendment"],
                amendment_year=launch_restriction["year"],
                fragrance_year=fragrance_year,
                action=action_at_launch,
                pre_restriction_allowed=pre_restriction_allowed,
                max_pct_at_launch=max_at_launch,
                current_max_pct=current_max,
                needs_reformulation_check=needs_refo_check,
                plausibility_note=note,
            )
            constraints.append(constraint)

        elif post_launch is not None:
            # Material was unrestricted at launch, restricted later
            action_post = post_launch["restriction"]["action"]
            max_post: Optional[float] = post_launch["restriction"]["max_pct_cat4"]
            current_max = current["restriction"]["max_pct_cat4"] if current else max_post

            needs_refo_check = (
                known_reformulation_year is not None
                and post_launch["year"] <= known_reformulation_year
            )

            note = (
                f"{material} was unrestricted at launch ({fragrance_year}). "
                f"Restricted/prohibited under {post_launch['amendment']} "
                f"(effective {post_launch['year']}, action: {action_post}, "
                f"limit: {max_post}% cat4). "
            )
            if needs_refo_check:
                note += (
                    f"Reformulation ({known_reformulation_year}) would require compliance "
                    f"with current limit: {current_max}% (cat4)."
                )

            constraint = RegulatoryConstraint(
                material=material,
                amendment=post_launch["amendment"],
                amendment_year=post_launch["year"],
                fragrance_year=fragrance_year,
                action=action_post,
                pre_restriction_allowed=True,
                max_pct_at_launch=None,
                current_max_pct=current_max,
                needs_reformulation_check=needs_refo_check,
                plausibility_note=note,
            )
            constraints.append(constraint)
            restricted_since_launch.append(material)

        else:
            # Never restricted under any tracked amendment
            always_compliant.append(material)

    # -------------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------------
    base_score = 100.0
    confirmed_prohibited: list[str] = []
    probable_prohibited: list[str] = []
    speculative_prohibited: list[str] = []

    for mat in prohibited_at_launch:
        posterior = material_posteriors.get(mat, 0.0)
        if posterior >= _CONFIRMED_THRESHOLD:
            base_score -= 25
            confirmed_prohibited.append(mat)
        elif posterior >= _PROBABLE_THRESHOLD:
            base_score -= 15
            probable_prohibited.append(mat)
        else:
            base_score -= 5
            speculative_prohibited.append(mat)

    # Bonus: all confirmed-tier materials are compliant at launch
    [
        mat for mat, p in material_posteriors.items()
        if p >= _CONFIRMED_THRESHOLD and mat in always_compliant
    ]
    all_confirmed = [
        mat for mat, p in material_posteriors.items() if p >= _CONFIRMED_THRESHOLD
    ]
    if all_confirmed and not confirmed_prohibited:
        base_score += 10

    score = max(0.0, min(100.0, base_score))

    return RegulatoryAnalysisResult(
        target_name=target_name,
        fragrance_year=fragrance_year,
        applicable_amendments=applicable_amendments,
        constraints=constraints,
        prohibited_at_launch=prohibited_at_launch,
        restricted_since_launch=restricted_since_launch,
        always_compliant=always_compliant,
        score=score,
    )


def format_regulatory_report(result: RegulatoryAnalysisResult) -> str:
    """
    Return a human-readable regulatory consistency report for a
    RegulatoryAnalysisResult instance.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("REGULATORY CONSISTENCY REPORT")
    lines.append("=" * 60)
    lines.append(f"Target       : {result.target_name}")
    lines.append(f"Launch year  : {result.fragrance_year}")
    lines.append(f"Score        : {result.score:.1f} / 100")
    lines.append("")

    if result.applicable_amendments:
        lines.append("Amendments in force at launch:")
        for amend in result.applicable_amendments:
            year = IFRA_AMENDMENTS[amend]["effective_year"]
            lines.append(f"  • {amend} (effective {year})")
    else:
        lines.append("No tracked IFRA amendments were in force at launch year.")
    lines.append("")

    if result.prohibited_at_launch:
        lines.append("PROHIBITED AT LAUNCH (regulatory inconsistency):")
        for mat in result.prohibited_at_launch:
            lines.append(f"  ✗ {mat}")
    else:
        lines.append("No hypothesized materials were prohibited at launch.")
    lines.append("")

    if result.restricted_since_launch:
        lines.append("RESTRICTED SINCE LAUNCH (post-launch restriction, no launch-year penalty):")
        for mat in result.restricted_since_launch:
            lines.append(f"  ~ {mat}")
    else:
        lines.append("No materials acquired new restrictions after launch.")
    lines.append("")

    if result.always_compliant:
        lines.append("ALWAYS COMPLIANT (no tracked restriction):")
        for mat in result.always_compliant:
            lines.append(f"  ✓ {mat}")
    lines.append("")

    reformulation_items = [c for c in result.constraints if c.needs_reformulation_check]
    if reformulation_items:
        lines.append("REFORMULATION FLAGS:")
        for c in reformulation_items:
            lines.append(f"  [{c.material}] {c.plausibility_note}")
        lines.append("")

    lines.append("-" * 60)
    lines.append("Constraint detail:")
    if result.constraints:
        for c in result.constraints:
            lines.append(f"  {c.material}:")
            lines.append(f"    Amendment      : {c.amendment} ({c.amendment_year})")
            lines.append(f"    Action         : {c.action}")
            lines.append(f"    Allowed launch : {c.pre_restriction_allowed}")
            if c.max_pct_at_launch is not None:
                lines.append(f"    Limit at launch: {c.max_pct_at_launch}% (cat4)")
            if c.current_max_pct is not None:
                lines.append(f"    Current limit  : {c.current_max_pct}% (cat4)")
            lines.append(f"    Note           : {c.plausibility_note}")
    else:
        lines.append("  (none)")

    lines.append("=" * 60)
    return "\n".join(lines)
