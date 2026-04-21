"""IFRA Concentration Window Analysis — Legal bounds for allergen-declared materials.

EU Regulation 1223/2009 requires allergen declaration above 10 ppm (0.001%)
in leave-on products. IFRA 51st Amendment sets maximum use levels per category.

For each declared allergen, this creates a concentration window:
    [notification_threshold, IFRA_ceiling]

For each ABSENT allergen, this creates an upper bound:
    [0, notification_threshold)

Category 4 = Fine Fragrance (EDP/EDT), which is the relevant category.

The window constrains the Bayesian posterior by providing hard bounds on
concentration estimates that override softer evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── IFRA Category 4 (Fine Fragrance) Maximum Use Levels ──────────────
# Source: IFRA 51st Amendment (2024), expressed as % of finished product.
# For a 25% EDP, multiply by 4 to get % of concentrate.
#
# Format: material → (max_in_product_pct, max_in_concentrate_pct_at_25pct)

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
    "butylphenyl methylpropional": (0.0, 0.0),    # Banned (Lilial)
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


def compute_ifra_windows(
    declared_allergens: list[str],
    all_26_allergens: Optional[list[str]] = None,
    concentration_pct: float = 25.0,
    target_name: str = "",
) -> IFRAAnalysisResult:
    """Compute concentration windows for all declared and absent allergens.

    Args:
        declared_allergens: Allergens listed on the box (in order of concentration).
        all_26_allergens: Full list of EU 26 allergens for absence analysis.
        concentration_pct: Product concentration (25% for EDP).
        target_name: Name of the fragrance.

    Returns:
        IFRAAnalysisResult with per-material concentration windows and a score.
    """
    if all_26_allergens is None:
        all_26_allergens = list(IFRA_CAT4_LIMITS.keys())

    multiplier = 100.0 / concentration_pct  # Convert product% → concentrate%
    notif_conc = NOTIFICATION_THRESHOLD_LEAVE_ON * multiplier

    windows: list[ConcentrationWindow] = []
    absent: list[str] = []
    restricted: list[str] = []

    declared_lower = {a.lower().strip() for a in declared_allergens}

    for allergen, (max_prod, _) in IFRA_CAT4_LIMITS.items():
        max_conc = max_prod * multiplier
        is_declared = allergen in declared_lower

        if is_declared:
            # Declared → must be above notification, below IFRA ceiling
            ifra_restricted = max_conc < 50.0  # Meaningful restriction
            window = ConcentrationWindow(
                material=allergen,
                allergen_name=allergen,
                declared_on_box=True,
                min_pct=notif_conc,
                max_pct=min(max_conc, 100.0),
                ifra_restricted=ifra_restricted,
                window_width=min(max_conc, 100.0) - notif_conc,
                confidence=0.0,  # Set below
            )
            # Narrow windows are more constraining
            if ifra_restricted:
                window.confidence = max(0.3, 1.0 - (window.window_width / 20.0))
                restricted.append(allergen)
            else:
                window.confidence = 0.15  # Wide window = low constraint
            windows.append(window)
        else:
            # NOT declared → must be below notification threshold
            absent.append(allergen)

    # Score: how much total constraint the IFRA analysis provides
    if not windows:
        score = 0.0
    else:
        constrained_count = len([w for w in windows if w.ifra_restricted])
        avg_confidence = sum(w.confidence for w in windows) / len(windows)
        # Bonus for absent allergens (they eliminate materials)
        absence_bonus = min(20.0, len(absent) * 2.0)
        score = min(100.0, (avg_confidence * 60.0) + absence_bonus + (constrained_count * 5.0))

    return IFRAAnalysisResult(
        target_name=target_name,
        concentration_pct=concentration_pct,
        windows=windows,
        absent_allergens=absent,
        restricted_materials=restricted,
        total_constrained=len(windows),
        score=score,
    )


def format_ifra_report(result: IFRAAnalysisResult) -> str:
    """Format IFRA analysis as readable report."""
    lines = [
        f"═══ IFRA CONSTRAINT ANALYSIS: {result.target_name} ═══",
        f"Product concentration: {result.concentration_pct}% (Category 4 — Fine Fragrance)",
        f"Declared allergens: {result.total_constrained}",
        f"Absent allergens (eliminated): {len(result.absent_allergens)}",
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
            "── Absent Allergens (below 10 ppm → material eliminated or trace) ──",
        ])
        for a in sorted(result.absent_allergens):
            lines.append(f"  ✗ {a} — NOT in formula above 10 ppm")

    return "\n".join(lines)
