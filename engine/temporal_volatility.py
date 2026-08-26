"""Temporal Volatility Analysis — reviewer timeline descriptions constrain material volatility.

Maps reviewer timing language ("opens with X", "dries down to", "base is") to expected
volatility windows, then checks whether the materials hypothesized for those notes have
matching volatility profiles.

TEMPORAL_CONSISTENCY category module for the perfume reconstruction engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from engine.name_utils import normalize_name
from engine.odor_thresholds import MIXTURE_SUPPRESSION_FACTOR, ODT_DATA

VOLATILITY_WINDOWS: dict[str, dict] = {
    "immediate_opening": {"vp_min": 0.5,   "vp_max": 100.0, "evap_max_min": 30},
    "early_heart":       {"vp_min": 0.05,  "vp_max": 2.0,   "evap_max_min": 90},
    "late_heart":        {"vp_min": 0.005, "vp_max": 0.5,   "evap_max_min": 240},
    "drydown":           {"vp_min": 0.0,   "vp_max": 0.05,  "evap_max_min": 480},
    "base_only":         {"vp_min": 0.0,   "vp_max": 0.01,  "evap_max_min": 9999},
}

MATERIAL_VOLATILITY: dict[str, dict] = {
    "limonene":               {"vp_25c": 2.00,   "onset_min": 0,   "fade_min": 15,   "position": "immediate_opening"},
    "linalool":               {"vp_25c": 0.16,   "onset_min": 0,   "fade_min": 45,   "position": "immediate_opening"},
    "bergamot":               {"vp_25c": 0.80,   "onset_min": 0,   "fade_min": 30,   "position": "immediate_opening"},
    "citronellol":            {"vp_25c": 0.04,   "onset_min": 5,   "fade_min": 90,   "position": "early_heart"},
    "geraniol":               {"vp_25c": 0.03,   "onset_min": 5,   "fade_min": 90,   "position": "early_heart"},
    "eugenol":                {"vp_25c": 0.02,   "onset_min": 10,  "fade_min": 120,  "position": "early_heart"},
    "hydroxycitronellal":     {"vp_25c": 0.008,  "onset_min": 10,  "fade_min": 180,  "position": "early_heart"},
    "rose oxide":             {"vp_25c": 0.20,   "onset_min": 0,   "fade_min": 60,   "position": "immediate_opening"},
    "hedione":                {"vp_25c": 0.008,  "onset_min": 15,  "fade_min": 240,  "position": "late_heart"},
    "cis-jasmone":            {"vp_25c": 0.05,   "onset_min": 5,   "fade_min": 120,  "position": "early_heart"},
    "phenethyl alcohol":      {"vp_25c": 0.10,   "onset_min": 0,   "fade_min": 60,   "position": "early_heart"},
    "alpha irone":            {"vp_25c": 0.01,   "onset_min": 15,  "fade_min": 300,  "position": "late_heart"},
    "alpha-isomethyl ionone": {"vp_25c": 0.005,  "onset_min": 20,  "fade_min": 360,  "position": "late_heart"},
    "iso e super":            {"vp_25c": 0.003,  "onset_min": 30,  "fade_min": 480,  "position": "drydown"},
    "indole":                 {"vp_25c": 0.04,   "onset_min": 5,   "fade_min": 90,   "position": "early_heart"},
    "coumarin":               {"vp_25c": 0.002,  "onset_min": 60,  "fade_min": 600,  "position": "drydown"},
    "benzyl salicylate":      {"vp_25c": 0.001,  "onset_min": 60,  "fade_min": 720,  "position": "base_only"},
    "ambrox super":             {"vp_25c": 0.002,  "onset_min": 45,  "fade_min": 600,  "position": "drydown"},
    "galaxolide":             {"vp_25c": 0.0005, "onset_min": 90,  "fade_min": 999,  "position": "base_only"},
    "habanolide":             {"vp_25c": 0.001,  "onset_min": 60,  "fade_min": 999,  "position": "base_only"},
    "patchouli alcohol":      {"vp_25c": 0.001,  "onset_min": 45,  "fade_min": 720,  "position": "drydown"},
    "vetiver":                {"vp_25c": 0.001,  "onset_min": 30,  "fade_min": 600,  "position": "drydown"},
    "cedarwood":              {"vp_25c": 0.003,  "onset_min": 20,  "fade_min": 480,  "position": "drydown"},
    "labdanum":               {"vp_25c": 0.0005, "onset_min": 90,  "fade_min": 999,  "position": "base_only"},
    "benzoin resinoid":       {"vp_25c": 0.0003, "onset_min": 120, "fade_min": 999,  "position": "base_only"},
    "ethyl vanillin":         {"vp_25c": 0.001,  "onset_min": 60,  "fade_min": 720,  "position": "drydown"},
    "farnesol":               {"vp_25c": 0.0005, "onset_min": 90,  "fade_min": 999,  "position": "base_only"},
    "benzyl benzoate":        {"vp_25c": 0.001,  "onset_min": 45,  "fade_min": 720,  "position": "drydown"},
    "benzyl alcohol":         {"vp_25c": 0.13,   "onset_min": 0,   "fade_min": 45,   "position": "immediate_opening"},
    "linalyl acetate":        {"vp_25c": 0.10,   "onset_min": 0,   "fade_min": 45,   "position": "immediate_opening"},
    "cashmeran":              {"vp_25c": 0.003,  "onset_min": 30,  "fade_min": 480,  "position": "drydown"},
    "vertofix coeur":         {"vp_25c": 0.002,  "onset_min": 45,  "fade_min": 600,  "position": "drydown"},
}

NOTE_TIMING_KEYWORDS: dict[str, list[str]] = {
    "immediate_opening": ["opens with", "opening", "initial", "first spray", "top note", "burst"],
    "early_heart":       ["develops into", "heart", "middle", "after 10 minutes", "transition"],
    "late_heart":        ["after 30 minutes", "heart settles", "core", "main accord"],
    "drydown":           ["dries down", "drydown", "after an hour", "after 2 hours", "dry", "warm"],
    "base_only":         ["base", "base note", "after 4 hours", "remains", "lasts", "fixative"],
}

_PYRAMID_POSITION_MAP: dict[str, str] = {
    "top":    "immediate_opening",
    "heart":  "early_heart",
    "base":   "drydown",
}

_TEMPORAL_ARC_WINDOWS: list[tuple[str, int, int]] = [
    ("0-15min",   0,   15),
    ("15-60min",  15,  60),
    ("60-240min", 60,  240),
    ("240min+",   240, 99999),
]


@dataclass
class TemporalConstraint:
    material: str
    onset_min: int
    fade_min: int
    position: str
    reviewer_implied_position: Optional[str]
    is_consistent: bool
    consistency_note: str = ""


@dataclass
class TemporalAnalysisResult:
    target_name: str
    constraints: list[TemporalConstraint] = field(default_factory=list)
    consistent_materials: list[str] = field(default_factory=list)
    inconsistent_materials: list[str] = field(default_factory=list)
    temporal_arc: dict[str, list[str]] = field(default_factory=dict)
    score: float = 0.0


def _normalize_material_name(name: str) -> str:
    return normalize_name(name)


# Pre-build a normalised lookup for MATERIAL_VOLATILITY
_VOLATILITY_INDEX: dict[str, dict] = {
    normalize_name(k): v for k, v in MATERIAL_VOLATILITY.items()
}


def _lookup_volatility(name: str) -> Optional[dict]:
    key = _normalize_material_name(name)
    return _VOLATILITY_INDEX.get(key)


def _reviewer_timing_position(
    material: str,
    reviewer_timing: Optional[dict[str, list[str]]],
) -> Optional[str]:
    if not reviewer_timing:
        return None
    mat_lower = _normalize_material_name(material)
    for position, terms in reviewer_timing.items():
        for term in terms:
            if _normalize_material_name(term) == mat_lower:
                return position
    return None


def _pyramid_position(
    material: str,
    declared_pyramid: dict[str, list[str]],
) -> Optional[str]:
    mat_lower = _normalize_material_name(material)
    for layer, members in declared_pyramid.items():
        layer_key = layer.lower().strip()
        for member in members:
            if _normalize_material_name(member) in mat_lower or mat_lower in _normalize_material_name(member):
                return _PYRAMID_POSITION_MAP.get(layer_key, None)
    return None


def _positions_consistent(natural: str, implied: str) -> tuple[bool, str]:
    position_order = ["immediate_opening", "early_heart", "late_heart", "drydown", "base_only"]

    if natural == implied:
        return True, f"{natural} matches reviewer-implied {implied}"

    if natural not in position_order or implied not in position_order:
        return True, f"positions not directly comparable ({natural} vs {implied})"

    nat_idx = position_order.index(natural)
    imp_idx = position_order.index(implied)
    gap = abs(nat_idx - imp_idx)

    if gap == 1:
        return True, f"adjacent positions acceptable ({natural} → {implied})"

    if imp_idx < nat_idx:
        return False, (
            f"INCONSISTENCY: reviewer places in {implied} but material "
            f"({natural}) is too low-volatility to be prominent that early"
        )
    else:
        return False, (
            f"INCONSISTENCY: reviewer places in {implied} but material "
            f"({natural}) is too volatile to persist that long"
        )


def _build_temporal_arc(
    materials_with_data: list[tuple[str, dict]],
) -> dict[str, list[str]]:
    arc: dict[str, list[str]] = {window: [] for window, _, _ in _TEMPORAL_ARC_WINDOWS}
    for mat_name, vol_data in materials_with_data:
        onset = vol_data["onset_min"]
        fade = vol_data["fade_min"]
        for window_label, win_start, win_end in _TEMPORAL_ARC_WINDOWS:
            if onset < win_end and fade > win_start:
                arc[window_label].append(mat_name)
    return arc


def analyze_temporal_consistency(
    target_name: str,
    material_posteriors: dict[str, float],
    declared_pyramid: dict[str, list[str]],
    reviewer_timing: Optional[dict[str, list[str]]] = None,
) -> TemporalAnalysisResult:
    result = TemporalAnalysisResult(target_name=target_name)

    active_materials: list[tuple[str, dict]] = []

    for material, posterior in material_posteriors.items():
        if posterior <= 0.4:
            continue

        vol_data = _lookup_volatility(material)
        if vol_data is None:
            continue

        active_materials.append((material, vol_data))

        natural_position = vol_data["position"]

        reviewer_implied = _reviewer_timing_position(material, reviewer_timing)
        if reviewer_implied is None:
            reviewer_implied = _pyramid_position(material, declared_pyramid)

        if reviewer_implied is None:
            constraint = TemporalConstraint(
                material=material,
                onset_min=vol_data["onset_min"],
                fade_min=vol_data["fade_min"],
                position=natural_position,
                reviewer_implied_position=None,
                is_consistent=True,
                consistency_note="no reviewer timing data; defaulting to consistent",
            )
        else:
            is_consistent, note = _positions_consistent(natural_position, reviewer_implied)
            constraint = TemporalConstraint(
                material=material,
                onset_min=vol_data["onset_min"],
                fade_min=vol_data["fade_min"],
                position=natural_position,
                reviewer_implied_position=reviewer_implied,
                is_consistent=is_consistent,
                consistency_note=note,
            )

        result.constraints.append(constraint)

        if constraint.is_consistent:
            result.consistent_materials.append(material)
        else:
            result.inconsistent_materials.append(material)

    result.temporal_arc = _build_temporal_arc(active_materials)

    n_total = len(result.constraints)
    n_consistent = len(result.consistent_materials)
    result.score = (n_consistent / max(1, n_total)) * 80.0 + min(20.0, n_total * 2.0)
    result.score = min(100.0, result.score)

    return result


def format_temporal_report(result: TemporalAnalysisResult) -> str:
    lines: list[str] = []
    lines.append(f"TEMPORAL CONSISTENCY — {result.target_name}")
    lines.append(f"Score: {result.score:.1f}/100")
    lines.append(
        f"Consistent: {len(result.consistent_materials)}  |  "
        f"Inconsistent: {len(result.inconsistent_materials)}  |  "
        f"Total evaluated: {len(result.constraints)}"
    )
    lines.append("")

    if result.inconsistent_materials:
        lines.append("INCONSISTENCIES:")
        for c in result.constraints:
            if not c.is_consistent:
                lines.append(
                    f"  [{c.material}]  natural={c.position}  "
                    f"implied={c.reviewer_implied_position}  — {c.consistency_note}"
                )
        lines.append("")

    lines.append("TEMPORAL ARC:")
    col_w = 20
    for window, materials in result.temporal_arc.items():
        mat_str = ", ".join(materials) if materials else "(none)"
        lines.append(f"  {window:<{col_w}} {mat_str}")

    lines.append("")
    lines.append("MATERIAL DETAIL:")
    header = f"  {'Material':<26} {'Natural Pos':<22} {'Implied Pos':<22} {'Onset':>6} {'Fade':>6}  Status"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for c in result.constraints:
        status = "OK" if c.is_consistent else "!!"
        implied = c.reviewer_implied_position or "—"
        lines.append(
            f"  {c.material:<26} {c.position:<22} {implied:<22} "
            f"{c.onset_min:>5}m {c.fade_min:>5}m  {status}"
        )

    return "\n".join(lines)


def validate_perception_windows(
    material_posteriors: dict[str, float],
    n_materials_total: int = 10,
) -> list[dict]:
    """Cross-reference temporal position with ODT to flag perceptual ghosts.

    A material may evaporate into a temporal window but sit below its odor
    detection threshold (adjusted for mixture suppression).  This function
    identifies those "phantom" materials that contribute mass but not scent.

    Returns a list of warning dicts:
      {material, window, vp_25c, odt_air, estimated_headspace_ppb, threshold_ppb, verdict}
    """
    warnings: list[dict] = []
    suppression = min(MIXTURE_SUPPRESSION_FACTOR, 1.0 + n_materials_total * 0.4)

    for material, posterior in material_posteriors.items():
        if posterior <= 0.4:
            continue
        vol = _lookup_volatility(material)
        if vol is None:
            continue
        odt_entry = ODT_DATA.get(normalize_name(material))
        if odt_entry is None:
            continue

        vp = vol["vp_25c"]
        odt_air = odt_entry["odt_air"]
        # Rough headspace estimate: VP (mmHg) → ppb via ideal gas
        # 1 mmHg ≈ 1316 ppm at 1 atm; convert to ppb (*1000)
        estimated_ppb = vp * 1_316_000
        effective_threshold = odt_air * suppression

        if estimated_ppb < effective_threshold:
            warnings.append({
                "material": material,
                "window": vol["position"],
                "vp_25c": vp,
                "odt_air": odt_air,
                "estimated_headspace_ppb": round(estimated_ppb, 1),
                "threshold_ppb": round(effective_threshold, 1),
                "verdict": "SUBLIMINAL — below perception threshold in mixture",
            })
        elif estimated_ppb < effective_threshold * 3:
            warnings.append({
                "material": material,
                "window": vol["position"],
                "vp_25c": vp,
                "odt_air": odt_air,
                "estimated_headspace_ppb": round(estimated_ppb, 1),
                "threshold_ppb": round(effective_threshold, 1),
                "verdict": "MARGINAL — near perception threshold, may be inconsistently detected",
            })

    return warnings
