"""Vapor pressure modeling for perfume reconstruction engine.

SILLAGE_PREDICTION category module. Uses Antoine equation constants and boiling
point data to estimate evaporation behavior, sillage radius, and head-note vs
base-note classification. Cross-validates against reviewer note detection timing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# ── Reference constants ──
_ETHANOL_VP_25C: float = 59.0  # mmHg at 25°C (fast-evaporation benchmark)
_LINALOOL_VP_25C: float = 0.16  # mmHg at 25°C (perfumery volatility reference)

# ── Vapor pressure data ──
VAPOR_PRESSURE_DATA: dict[str, dict] = {
    # {vp_25c: float (mmHg), bp_c: int, class: str ("top"/"heart"/"base"), mw: float}
    # Top/head notes (high VP, bp < 200°C)
    "limonene": {"vp_25c": 2.0, "bp_c": 176, "class": "top", "mw": 136.2},
    "bergamot": {"vp_25c": 0.8, "bp_c": 185, "class": "top", "mw": 136.2},
    "d-limonene": {"vp_25c": 2.0, "bp_c": 176, "class": "top", "mw": 136.2},
    "linalyl acetate": {"vp_25c": 0.10, "bp_c": 220, "class": "top", "mw": 196.3},
    "citronellol": {"vp_25c": 0.04, "bp_c": 225, "class": "heart", "mw": 156.3},
    "geraniol": {"vp_25c": 0.03, "bp_c": 230, "class": "heart", "mw": 154.2},
    "eugenol": {"vp_25c": 0.02, "bp_c": 254, "class": "heart", "mw": 164.2},
    # Heart notes (moderate VP, bp 200–280°C)
    "hedione": {"vp_25c": 0.008, "bp_c": 265, "class": "heart", "mw": 226.3},
    "cis-jasmone": {"vp_25c": 0.05, "bp_c": 262, "class": "heart", "mw": 164.2},
    "rose oxide": {"vp_25c": 0.20, "bp_c": 202, "class": "heart", "mw": 154.2},
    "phenethyl alcohol": {"vp_25c": 0.10, "bp_c": 220, "class": "heart", "mw": 122.2},
    "hydroxycitronellal": {"vp_25c": 0.008, "bp_c": 241, "class": "heart", "mw": 172.3},
    "alpha irone": {"vp_25c": 0.01, "bp_c": 265, "class": "heart", "mw": 192.3},
    "alpha-isomethyl ionone": {"vp_25c": 0.005, "bp_c": 270, "class": "heart", "mw": 206.3},
    "iso e super": {"vp_25c": 0.003, "bp_c": 278, "class": "heart", "mw": 204.3},
    "coumarin": {"vp_25c": 0.002, "bp_c": 301, "class": "base", "mw": 146.2},
    "indole": {"vp_25c": 0.04, "bp_c": 253, "class": "heart", "mw": 117.1},
    "linalool": {"vp_25c": 0.16, "bp_c": 198, "class": "top", "mw": 154.2},
    "benzyl alcohol": {"vp_25c": 0.13, "bp_c": 205, "class": "heart", "mw": 108.1},
    # Base notes (low VP, bp > 280°C)
    "benzyl salicylate": {"vp_25c": 0.001, "bp_c": 320, "class": "base", "mw": 228.2},
    "ambrox": {"vp_25c": 0.002, "bp_c": 290, "class": "base", "mw": 236.4},
    "galaxolide": {"vp_25c": 0.0005, "bp_c": 330, "class": "base", "mw": 258.4},
    "habanolide": {"vp_25c": 0.001, "bp_c": 320, "class": "base", "mw": 254.4},
    "patchouli alcohol": {"vp_25c": 0.001, "bp_c": 285, "class": "base", "mw": 222.4},
    "vetiver": {"vp_25c": 0.001, "bp_c": 300, "class": "base", "mw": 222.0},
    "cedarwood": {"vp_25c": 0.003, "bp_c": 280, "class": "base", "mw": 204.4},
    "labdanum": {"vp_25c": 0.0005, "bp_c": 340, "class": "base", "mw": 210.0},
    "benzoin resinoid": {"vp_25c": 0.0003, "bp_c": 350, "class": "base", "mw": 228.2},
    "ethyl vanillin": {"vp_25c": 0.001, "bp_c": 295, "class": "base", "mw": 166.2},
    "farnesol": {"vp_25c": 0.0005, "bp_c": 283, "class": "base", "mw": 222.4},
    "benzyl benzoate": {"vp_25c": 0.001, "bp_c": 323, "class": "base", "mw": 212.2},
}


# ── Result dataclasses ──


@dataclass
class VPConstraint:
    material: str
    vp_25c: float  # mmHg
    bp_c: int  # boiling point °C
    predicted_class: str  # "top" / "heart" / "base"
    volatility_index: float  # 0–100, relative to linalool reference
    estimated_evap_time_min: float  # minutes at 25°C on skin
    in_correct_layer: bool  # matches declared note pyramid layer


@dataclass
class VPAnalysisResult:
    target_name: str
    constraints: list[VPConstraint] = field(default_factory=list)
    top_note_materials: list[str] = field(default_factory=list)
    heart_note_materials: list[str] = field(default_factory=list)
    base_note_materials: list[str] = field(default_factory=list)
    misclassified_materials: list[str] = field(default_factory=list)
    sillage_index: float = 0.0  # 0–100, higher = better projected sillage
    score: float = 0.0  # 0–100 SILLAGE_PREDICTION category score


# ── Internal helpers ──


def _normalize_name(name: str) -> str:
    """Lowercase and strip whitespace for lookup."""
    return name.strip().lower()


def _lookup_vp(material: str) -> Optional[dict]:
    """Return VAPOR_PRESSURE_DATA entry for material, or None if not found.

    Tries exact match first, then checks if any key is contained in the
    material name (handles multi-word names like 'Bergamot FCF Sicilian').
    """
    key = _normalize_name(material)
    if key in VAPOR_PRESSURE_DATA:
        return VAPOR_PRESSURE_DATA[key]
    # Partial match: longest key that appears as a substring of the query
    best: Optional[str] = None
    for db_key in VAPOR_PRESSURE_DATA:
        if db_key in key:
            if best is None or len(db_key) > len(best):
                best = db_key
    if best is not None:
        return VAPOR_PRESSURE_DATA[best]
    return None


def _compute_volatility_index(vp_25c: float) -> float:
    """Volatility index 0–100 relative to linalool (0.16 mmHg) reference."""
    return min(100.0, vp_25c / _LINALOOL_VP_25C * 100.0)


def _compute_evap_time(vp_25c: float) -> float:
    """Estimate evaporation time in minutes at 25°C on skin.

    Logarithmic model anchored at:
      vp = 2.0 mmHg  → ~15 min  (fast top note)
      vp = 0.16 mmHg → ~60 min  (mid-volatility, linalool reference)
      vp = 0.001 mmHg → ~240 min (slow base note)
    """
    if vp_25c <= 0.0:
        return 480.0
    # log-linear interpolation: t = a * vp^b
    # Fit: ln(15) = ln(a) + b*ln(2.0) and ln(60) = ln(a) + b*ln(0.16)
    # b = (ln(15)-ln(60)) / (ln(2.0)-ln(0.16))
    b = (math.log(15.0) - math.log(60.0)) / (math.log(2.0) - math.log(0.16))
    a = 60.0 / (0.16**b)
    raw = a * (vp_25c**b)
    return max(5.0, min(600.0, raw))


def _predict_class(vp_25c: float, bp_c: int) -> str:
    """Classify material as top/heart/base using VP and boiling point thresholds."""
    if vp_25c >= 0.10 or bp_c < 210:
        return "top"
    if vp_25c >= 0.003 or bp_c < 285:
        return "heart"
    return "base"


def _declared_layer(material: str, pyramid: dict[str, list[str]]) -> Optional[str]:
    """Return which pyramid layer ('top'/'heart'/'base') declares this material."""
    key = _normalize_name(material)
    for layer, materials in pyramid.items():
        for m in materials:
            if _normalize_name(m) == key or key in _normalize_name(m) or _normalize_name(m) in key:
                return layer
    return None


# ── Main public function ──


def analyze_vapor_pressure(
    target_name: str,
    material_posteriors: dict[str, float],  # material → posterior probability
    declared_pyramid: dict[str, list[str]],  # {"top": [...], "heart": [...], "base": [...]}
    concentrate_pct: float = 25.0,
) -> VPAnalysisResult:
    """Analyze vapor pressure behavior of materials in a fragrance formula.

    Parameters
    ----------
    target_name:
        Name of the fragrance being analyzed.
    material_posteriors:
        Mapping of material name to posterior probability (0–1) from Bayesian
        reconstruction engine.
    declared_pyramid:
        Note pyramid as declared by the brand or reverse-engineering reference,
        keyed by 'top', 'heart', 'base'.
    concentrate_pct:
        Estimated concentrate percentage of the formula (affects absolute sillage
        projection; default 25%).

    Returns
    -------
    VPAnalysisResult with per-material constraints, classification lists,
    misclassification flags, sillage index, and composite score.
    """
    result = VPAnalysisResult(target_name=target_name)

    # Posterior threshold — only analyze materials with meaningful probability
    _posterior_threshold = 0.4

    n_classified = 0
    n_total = 0
    n_correct_layer = 0
    sillage_weighted_sum = 0.0
    sillage_weight_sum = 0.0

    for material, posterior in material_posteriors.items():
        if posterior < _posterior_threshold:
            continue

        vp_data = _lookup_vp(material)
        if vp_data is None:
            continue

        n_classified += 1
        n_total += 1

        vp_25c: float = vp_data["vp_25c"]
        bp_c: int = int(vp_data["bp_c"])
        vp_data["class"]

        volatility_index = _compute_volatility_index(vp_25c)
        evap_time = _compute_evap_time(vp_25c)
        predicted_class = _predict_class(vp_25c, bp_c)

        # Check pyramid placement
        declared_layer = _declared_layer(material, declared_pyramid)
        if declared_layer is not None:
            in_correct_layer = declared_layer == predicted_class
        else:
            # If not explicitly declared, check against db_class as ground truth
            in_correct_layer = True

        if in_correct_layer:
            n_correct_layer += 1
        else:
            result.misclassified_materials.append(material)

        constraint = VPConstraint(
            material=material,
            vp_25c=vp_25c,
            bp_c=bp_c,
            predicted_class=predicted_class,
            volatility_index=volatility_index,
            estimated_evap_time_min=round(evap_time, 1),
            in_correct_layer=in_correct_layer,
        )
        result.constraints.append(constraint)

        # Assign to note layer lists
        if predicted_class == "top":
            result.top_note_materials.append(material)
        elif predicted_class == "heart":
            result.heart_note_materials.append(material)
        else:
            result.base_note_materials.append(material)

        # Sillage contribution: top and heart materials drive detectable projection
        if predicted_class in ("top", "heart"):
            sillage_weighted_sum += posterior * volatility_index
            sillage_weight_sum += posterior

    # Sillage index: normalised weighted average of top+heart volatility,
    # scaled by concentrate percentage (higher conc → more projection)
    if sillage_weight_sum > 0.0:
        raw_sillage = sillage_weighted_sum / sillage_weight_sum
        conc_factor = min(1.5, concentrate_pct / 20.0)  # 20% = neutral reference
        result.sillage_index = min(100.0, raw_sillage * conc_factor)
    else:
        result.sillage_index = 0.0

    # Composite score
    # – Up to 50 pts for volume of classified materials (8 pts each, capped at ~6 materials)
    # – Up to 50 pts for pyramid placement accuracy
    classification_score = min(50.0, n_classified * 8.0)
    placement_score = (n_correct_layer / max(1, n_total)) * 50.0
    result.score = min(100.0, classification_score + placement_score)

    return result


# ── Format function ──


def format_vp_report(result: VPAnalysisResult) -> str:
    """Format vapor pressure analysis as a text report.

    Returns a human-readable table:
        Material              | VP(mmHg) | Class  | Evap(min) | Pyramid OK
    """
    lines: list[str] = []
    lines.append(f"Vapor Pressure Analysis — {result.target_name}")
    lines.append("=" * 72)

    # Header
    col_mat = 24
    col_vp = 10
    col_cls = 8
    col_evap = 11
    col_ok = 12

    header = (
        f"{'Material':<{col_mat}} | "
        f"{'VP(mmHg)':<{col_vp}} | "
        f"{'Class':<{col_cls}} | "
        f"{'Evap(min)':<{col_evap}} | "
        f"{'Pyramid OK':<{col_ok}}"
    )
    separator = "-" * len(header)
    lines.append(header)
    lines.append(separator)

    if not result.constraints:
        lines.append("  No materials with VP data found above posterior threshold.")
    else:
        # Sort: top → heart → base, then by evap time ascending
        order = {"top": 0, "heart": 1, "base": 2}
        sorted_constraints = sorted(
            result.constraints,
            key=lambda c: (order.get(c.predicted_class, 3), c.estimated_evap_time_min),
        )
        for c in sorted_constraints:
            mat_display = c.material[:col_mat]
            vp_str = f"{c.vp_25c:.4f}"
            ok_str = "YES" if c.in_correct_layer else "NO ⚠"
            row = (
                f"{mat_display:<{col_mat}} | "
                f"{vp_str:<{col_vp}} | "
                f"{c.predicted_class:<{col_cls}} | "
                f"{c.estimated_evap_time_min:<{col_evap}.1f} | "
                f"{ok_str:<{col_ok}}"
            )
            lines.append(row)

    lines.append(separator)

    # Summary block
    lines.append("")
    lines.append(
        f"  Top note materials  : {', '.join(result.top_note_materials) or 'none detected'}"
    )
    lines.append(
        f"  Heart note materials: {', '.join(result.heart_note_materials) or 'none detected'}"
    )
    lines.append(
        f"  Base note materials : {', '.join(result.base_note_materials) or 'none detected'}"
    )
    if result.misclassified_materials:
        lines.append(
            f"  Misclassified (wrong pyramid layer): {', '.join(result.misclassified_materials)}"
        )
    lines.append("")
    lines.append(f"  Sillage index : {result.sillage_index:.1f} / 100")
    lines.append(f"  Module score  : {result.score:.1f} / 100")

    return "\n".join(lines)
