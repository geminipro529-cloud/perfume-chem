"""Diagnostic windows for threshold-declared fragrance allergens.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm, ODT in ppm/ppb, OAV = C/ODT (dimensionless).
- Every perceptibility claim must be backed by OAV.

EU Regulation 1223/2009 requires allergen declaration above 10 ppm (0.001%)
in leave-on products. A declaration establishes constituent presence above the
applicable threshold; it does not identify the source material or reveal the
constituent's formula concentration.

For each declared allergen, this creates a concentration window:
    [notification_threshold, IFRA_ceiling]

For each ABSENT allergen in an explicitly verified complete label regime, this
creates an upper bound:
    [0, notification_threshold)

Category 4 = Fine Fragrance (EDP/EDT), which is the relevant category.

These windows are diagnostic regulatory evidence only. They must not create
standalone raw-material hypotheses or back-calculate natural-material doses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# EU Allergen Notification Thresholds & Regulatory Windows
#
# WARNING: This dict is named IFRA_CAT4_LIMITS but for most materials it contains
# EU Cosmetics Regulation 1223/2009 Annex III notification thresholds,
# NOT IFRA 51st Amendment quantitative use limits.
#
# For authoritative IFRA Cat4 quantitative limits, see engine/ifra_safety.py.
#
# Values with 100.0% (e.g., geraniol, citronellol) = require label declaration
# above 0.001% but have NO quantitative use restriction under QRA2.
#
# This module is used by reconstruction_pipeline.py, NOT by the main pipeline gates
# (gates.py imports IFRA_CAT4_LIMITS from engine/ifra_safety instead).
# ═══════════════════════════════════════════════════════════════════════════════

IFRA_CAT4_LIMITS: dict[str, tuple[float, float]] = {
    # Allergen name → (max % finished product, max % concentrate at 25% conc)
    "benzyl salicylate":        (5.60, 22.40),
    "linalool":                 (100.0, 100.0),   # No restriction (QRA2)
    "citronellol":              (100.0, 100.0),   # No restriction (QRA2)
    "eugenol":                  (0.50, 2.00),
    "benzyl benzoate":          (100.0, 100.0),   # No restriction
    "farnesol":                 (1.25, 5.00),
    "hydroxycitronellal":       (1.00, 4.00),
    "geraniol":                 (100.0, 100.0),   # No restriction (QRA2)
    "limonene":                 (100.0, 100.0),   # No restriction (QRA2)
    "benzyl alcohol":           (100.0, 100.0),   # No restriction
    "alpha-isomethyl ionone":   (100.0, 100.0),   # No restriction
    "coumarin":                 (0.80, 3.20),
    "isoeugenol":               (0.02, 0.08),
    "cinnamal":                 (0.05, 0.20),
    "cinnamyl alcohol":         (0.80, 3.20),
    "hexyl cinnamal":           (100.0, 100.0),   # No restriction
    "amyl cinnamal":            (100.0, 100.0),   # No restriction
    "citral":                   (0.60, 2.40),
    "methyl 2-octynoate":       (0.006, 0.024),
    "oak moss":                 (0.10, 0.40),
    "tree moss":                (0.10, 0.40),
    "butylphenyl methylpropional": (100.0, 100.0),  # Experimental local use: do not hard-ban in bench-only analysis
    "hydroxyisohexyl 3-cyclohexene carboxaldehyde": (0.0, 0.0),  # Banned (Lyral)
    "anise alcohol":            (100.0, 100.0),
    "benzyl cinnamate":         (100.0, 100.0),
    "evernia furfuracea":       (0.10, 0.40),     # Tree moss extract
    "evernia prunastri":        (0.10, 0.40),     # Oakmoss extract
}

# EU notification threshold for leave-on products (% of finished product)
NOTIFICATION_THRESHOLD_LEAVE_ON = 0.001  # 10 ppm


# ── Allergen → Source Material Mappings ──────────────────────────────
# Which raw materials contribute each allergen, with typical % content

ALLERGEN_SOURCES: dict[str, list[tuple[str, float]]] = {
    "linalool": [
        ("bergamot eo", 25.0), ("bergamot fcf", 22.0),
        ("lavender eo", 30.0), ("neroli eo", 35.0),
        ("rose absolute", 2.0), ("jasmine absolute", 5.0),
        ("linalool (synthetic)", 100.0),
    ],
    "citronellol": [
        ("rose absolute", 35.0), ("geranium eo", 30.0),
        ("citronellol (synthetic)", 100.0),
    ],
    "geraniol": [
        ("rose absolute", 18.0), ("palmarosa eo", 80.0),
        ("geranium eo", 20.0), ("geraniol (synthetic)", 100.0),
    ],
    "eugenol": [
        ("rose absolute", 1.5), ("clove bud eo", 85.0),
        ("oud oil", 8.0), ("eugenol (synthetic)", 100.0),
    ],
    "benzyl benzoate": [
        ("jasmine absolute", 15.0), ("benzoin resinoid", 20.0),
        ("peru balsam", 25.0), ("benzyl benzoate (synthetic)", 100.0),
    ],
    "benzyl alcohol": [
        ("jasmine absolute", 5.0), ("benzoin resinoid", 3.0),
        ("benzyl alcohol (synthetic)", 100.0),
    ],
    "farnesol": [
        ("rose absolute", 1.0), ("jasmine absolute", 2.0),
        ("oud oil", 3.0), ("ylang ylang eo", 5.0),
        ("farnesol (synthetic)", 100.0),
    ],
    "limonene": [
        ("bergamot eo", 35.0), ("bergamot fcf", 30.0),
        ("blood orange eo", 95.0), ("d-limonene", 100.0),
        ("grapefruit eo", 90.0), ("red mandarin eo", 70.0),
    ],
    "hydroxycitronellal": [
        ("hydroxycitronellal (synthetic)", 100.0),
    ],
    "benzyl salicylate": [
        ("benzyl salicylate (synthetic)", 100.0),
    ],
    "alpha-isomethyl ionone": [
        ("alpha-isomethyl ionone (synthetic)", 100.0),
    ],
    "coumarin": [
        ("coumarin (synthetic)", 100.0),
        ("tonka bean absolute", 40.0),
    ],
}


@dataclass
class ConcentrationWindow:
    """Legal concentration bounds for a material in a formula."""
    material: str
    allergen_name: str
    declared_on_box: bool
    min_pct: float          # Minimum % of concentrate (notification threshold)
    max_pct: float          # Maximum % of concentrate (IFRA ceiling)
    ifra_restricted: bool   # True if IFRA ceiling < 100% (meaningful restriction)
    window_width: float     # max - min
    confidence: float       # How constraining this window is (narrow = high)

    @property
    def midpoint(self) -> float:
        return (self.min_pct + self.max_pct) / 2.0


@dataclass
class IFRAAnalysisResult:
    """Complete IFRA constraint analysis for a fragrance."""
    target_name: str
    concentration_pct: float          # EDP concentration (e.g. 25%)
    windows: list[ConcentrationWindow]
    absent_allergens: list[str]       # Allergens NOT declared (upper-bounded)
    restricted_materials: list[str]   # Materials with IFRA ceilings that matter
    total_constrained: int
    score: float                      # 0-100: how much IFRA evidence constrains the formula
    absence_authority: bool
    limitations: tuple[str, ...]


def compute_ifra_windows(
    declared_allergens: list[str],
    all_26_allergens: Optional[list[str]] = None,
    concentration_pct: float = 25.0,
    target_name: str = "",
    label_regime_complete: bool = False,
) -> IFRAAnalysisResult:
    """Compute concentration windows for all declared and absent allergens.

    Args:
        declared_allergens: Allergens listed on the package. Their order is not
            treated as quantitative evidence.
        all_26_allergens: Applicable complete allergen universe for the verified
            market/date label regime. The historical parameter name is retained
            for API compatibility.
        concentration_pct: Product concentration (25% for EDP).
        target_name: Name of the fragrance.
        label_regime_complete: True only when the applicable market/date label
            regime and complete required-allergen universe have been verified.

    Returns:
        IFRAAnalysisResult with per-material concentration windows and a score.
    """
    if concentration_pct <= 0.0:
        raise ValueError("concentration_pct must be greater than zero")

    declared_ordered = tuple(
        dict.fromkeys(
            name
            for allergen in declared_allergens
            if (name := allergen.lower().strip())
        )
    )
    universe_source = (
        list(IFRA_CAT4_LIMITS.keys())
        if all_26_allergens is None
        else all_26_allergens
    )
    allergen_universe = list(
        dict.fromkeys(
            name
            for allergen in universe_source
            if (name := allergen.lower().strip())
        )
    )
    # Retain declared evidence even if a caller supplied an incomplete universe.
    # Only universe members can become absence findings.
    analysis_allergens = allergen_universe + [
        allergen for allergen in declared_ordered if allergen not in allergen_universe
    ]

    multiplier = 100.0 / concentration_pct  # Convert product% → concentrate%
    notif_conc = NOTIFICATION_THRESHOLD_LEAVE_ON * multiplier

    windows: list[ConcentrationWindow] = []
    absent: list[str] = []
    restricted: list[str] = []

    declared_lower = set(declared_ordered)

    for allergen in analysis_allergens:
        limit_record = IFRA_CAT4_LIMITS.get(allergen)
        max_conc = (
            min(limit_record[0] * multiplier, 100.0)
            if limit_record is not None
            else 100.0
        )
        is_declared = allergen in declared_lower

        if is_declared:
            # Declared constituent: threshold lower bound only. A quantitative
            # ceiling is diagnostic here only when this legacy table records one.
            ifra_restricted = limit_record is not None and max_conc < 100.0
            window = ConcentrationWindow(
                material=allergen,
                allergen_name=allergen,
                declared_on_box=True,
                min_pct=notif_conc,
                max_pct=max_conc,
                ifra_restricted=ifra_restricted,
                window_width=max(0.0, max_conc - notif_conc),
                confidence=0.0,  # Set below
            )
            # Narrow windows are more constraining
            if ifra_restricted:
                window.confidence = max(0.3, 1.0 - (window.window_width / 20.0))
                restricted.append(allergen)
            elif limit_record is not None:
                window.confidence = 0.15  # Wide window = low constraint
            else:
                # No quantitative limit authority exists in this diagnostic
                # table for this explicitly requested allergen.
                window.confidence = 0.0
            windows.append(window)
        elif label_regime_complete and allergen in allergen_universe:
            # NOT declared → must be below notification threshold
            absent.append(allergen)

    # Score: how much total constraint the IFRA analysis provides
    if not windows:
        score = 0.0
    else:
        constrained_count = len([w for w in windows if w.ifra_restricted])
        avg_confidence = sum(w.confidence for w in windows) / len(windows)
        # Absence narrows constituent presence only; it never identifies or
        # eliminates a source material by itself.
        absence_bonus = min(20.0, len(absent) * 2.0) if label_regime_complete else 0.0
        score = min(100.0, (avg_confidence * 60.0) + absence_bonus + (constrained_count * 5.0))

    return IFRAAnalysisResult(
        target_name=target_name,
        concentration_pct=concentration_pct,
        windows=windows,
        absent_allergens=absent,
        restricted_materials=restricted,
        total_constrained=len(windows),
        score=score,
        absence_authority=label_regime_complete,
        limitations=(
            "Declared allergens support thresholded constituent presence, not "
            "standalone raw-material identity.",
            "Absent-label upper bounds are withheld unless the applicable label "
            "regime and complete allergen universe are explicitly verified.",
        ),
    )


def format_ifra_report(result: IFRAAnalysisResult) -> str:
    """Format IFRA analysis as readable report."""
    lines = [
        f"═══ IFRA CONSTRAINT ANALYSIS: {result.target_name} ═══",
        f"Product concentration: {result.concentration_pct}% (Category 4 — Fine Fragrance)",
        f"Declared allergens: {result.total_constrained}",
        f"Absent-allergen authority: {'VERIFIED' if result.absence_authority else 'WITHHELD'}",
        f"Absent allergens below threshold: {len(result.absent_allergens)}",
        f"IFRA-restricted materials: {len(result.restricted_materials)}",
        f"Constraint Score: {result.score:.1f}/100",
        "",
        "── Concentration Windows (declared allergens) ──",
        f"{'Allergen':<30} {'Min%':>6} {'Max%':>6} {'Width':>6} {'Restricted':>10} {'Conf':>5}",
        "─" * 70,
    ]

    for w in sorted(result.windows, key=lambda x: x.max_pct):
        lines.append(
            f"{w.allergen_name:<30} {w.min_pct:>6.3f} {w.max_pct:>6.1f} "
            f"{w.window_width:>6.1f} {'YES' if w.ifra_restricted else 'no':>10} {w.confidence:>5.2f}"
        )

    if result.absent_allergens:
        lines.extend([
            "",
            "── Absent Allergens (constituent below threshold; source not identified) ──",
        ])
        for a in sorted(result.absent_allergens):
            lines.append(f"  ✗ {a} — constituent not declared above the applicable threshold")

    return "\n".join(lines)
