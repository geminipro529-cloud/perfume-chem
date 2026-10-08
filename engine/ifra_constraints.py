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

from dataclasses import dataclass, field
from typing import Optional

from engine.ifra_standards import load_ifra_table

# ═══════════════════════════════════════════════════════════════════════════════
# IFRA Category 4 ceilings for the EU-labelled allergens
#
# The numbers come from the sourced IFRA 51st Amendment Category 4 table
# (data/regulatory/ifra_cat4_51.json, read through engine.ifra_standards); no
# limit is typed into this module. Each entry maps an allergen to
# (max % finished product, max % concentrate at 25% concentration):
#   restricted                 -> (limit, limit x 4)
#   no_standard, specification -> (100.0, 100.0): no quantitative IFRA ceiling
#   prohibited                 -> (0.0, 0.0)
# An allergen whose table record is missing or has any other status gets no
# entry, and compute_ifra_windows reports it as unchecked instead of inventing
# a ceiling. EU notification thresholds are a separate datum (below).
#
# This module is used by reconstruction_pipeline.py, not by the main pipeline
# gates.
# ═══════════════════════════════════════════════════════════════════════════════

# EU-labelled allergen names (INCI-style) whose IFRA Category 4 ceiling is
# looked up in the sourced table. Also the default allergen universe of
# compute_ifra_windows.
EU_ALLERGEN_KEYS: tuple[str, ...] = (
    "benzyl salicylate",
    "linalool",
    "citronellol",
    "eugenol",
    "benzyl benzoate",
    "farnesol",
    "hydroxycitronellal",
    "geraniol",
    "limonene",
    "benzyl alcohol",
    "alpha-isomethyl ionone",
    "coumarin",
    "isoeugenol",
    "cinnamal",
    "cinnamyl alcohol",
    "hexyl cinnamal",
    "amyl cinnamal",
    "citral",
    "methyl 2-octynoate",
    "oak moss",
    "tree moss",
    "butylphenyl methylpropional",
    "hydroxyisohexyl 3-cyclohexene carboxaldehyde",
    "anise alcohol",
    "benzyl cinnamate",
    "evernia furfuracea",
    "evernia prunastri",
)

_CONCENTRATE_FACTOR = 4.0  # 100% / 25% concentration
_NO_QUANTITATIVE_CEILING = frozenset({"no_standard", "specification"})


def _limits_from_table(keys: tuple[str, ...]) -> dict[str, tuple[float, float]]:
    table = load_ifra_table()
    limits: dict[str, tuple[float, float]] = {}
    for key in keys:
        material = table.lookup(key)
        if material is None:
            continue
        if material.status == "restricted" and material.cat4_limit_pct is not None:
            limit = material.cat4_limit_pct
            limits[key] = (limit, limit * _CONCENTRATE_FACTOR)
        elif material.status in _NO_QUANTITATIVE_CEILING:
            limits[key] = (100.0, 100.0)
        elif material.status == "prohibited":
            limits[key] = (0.0, 0.0)
    return limits


IFRA_CAT4_LIMITS: dict[str, tuple[float, float]] = _limits_from_table(EU_ALLERGEN_KEYS)

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
    # Declared allergens with no usable record in the sourced IFRA table: no
    # ceiling was checked for them.
    unchecked_allergens: list[str] = field(default_factory=list)


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
        list(EU_ALLERGEN_KEYS)
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
    unchecked: list[str] = []

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
            # ceiling is diagnostic here only when the sourced table gives one.
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
                # The sourced IFRA table has no usable record for this
                # allergen: report it unchecked, with no ceiling claimed.
                window.confidence = 0.0
                unchecked.append(allergen)
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
        unchecked_allergens=unchecked,
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
        f"Unchecked (no IFRA table record): {len(result.unchecked_allergens)}",
        f"Constraint Score: {result.score:.1f}/100",
        "",
        "── Concentration Windows (declared allergens) ──",
        f"{'Allergen':<30} {'Min%':>6} {'Max%':>6} {'Width':>6} {'Restricted':>10} {'Conf':>5}",
        "─" * 70,
    ]

    unchecked = set(result.unchecked_allergens)
    for w in sorted(result.windows, key=lambda x: x.max_pct):
        if w.allergen_name in unchecked:
            lines.append(f"{w.allergen_name:<30} {w.min_pct:>6.3f}  UNCHECKED: no IFRA table record")
            continue
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
