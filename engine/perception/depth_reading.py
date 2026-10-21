"""Depth reading: a structural screening diagnostic for the release gate.

The luxury index (``engine/optimizer/scoring.py`` ``score_luxury``) counts as
"shadows" the rows whose concentrate OAV sits in 0.1-1.0 and peaks at ten of
them. It never looks at time, objects or textures, so one object with a fresh
crowd and ten trace rows can top it (AGENTS.md Rule 3 and F12). This
module reads the gate's own five simulation windows and reports structure
instead: how many odour families and textures sit at OAV >= 1 in each window,
what each row does over time, whether the index's shadows stay shadows, and
whether the drydown changes.

It is informational only. It changes no gate verdict, score, ranking or overall
status, and it does not re-run physics: every number comes from the frames and
rows the gate already built. OAV here is ``MaterialState.screening_oav`` in each
``SimulationFrame`` (the value ``SimulationFrame.dominant_oav`` ranks and the gate
prints as ``time_windows[*].dominant_leaders``). OAV is a detection-related
screening diagnostic only (AGENTS.md Rule 1): never perceived contribution,
intensity, character, pleasantness or liking. A structural reading is not a
sensory verdict; it is what a luxury or depth claim must face.

Row classes (the same definitions as the studio role map, so counts agree):

* ``lead``: in the top 5 by OAV in at least one window.
* ``support``: OAV >= 1 in some window but never in a top 5.
* ``shadow``: 0.1 <= max OAV < 1.
* ``silent``: max OAV < 0.1 in every window that has an OAV.
* ``unknown``: no OAV in any window; the engine's own reason is kept.
* ``bridge`` (flag, not a class): OAV >= 1 in an early window (0 s, 5 min or
  30 min) and in a late one (2 h or 4 h).

Per window the family weights are the engine's perceptible-intensity weights
(``construction_complexity._perceptible_weights``: modelled Stevens screening
intensity of rows with OAV >= 1) summed by ``MaterialState.family`` and shaped
with ``construction_complexity._distribution_shape``. They are modelled
screening values, not measured intensity. Rows with no family are grouped as
``unassigned`` and never count as an assigned family.

Flags are screening heuristics, each carrying its numbers:

* ``INDEX_SHADOWS_NOT_SHADOWS``: one or more rows the luxury index counts as
  shadows (concentrate OAV 0.1-1.0) are not shadows over the gate's windows.
* ``SILENT_ROWS``: one or more rows never reach OAV 0.1 in any window.
* ``SAME_TOP_FAMILY``: the same assigned family tops the family weights in
  every window from 5 min on.
* ``NO_DRYDOWN_CHANGE``: the top 5 rows at heart (30 min) and drydown (4 h)
  share 4 or 5 rows and the assigned top family is unchanged.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from engine.perception.construction_complexity import (
    _distribution_shape,
    _dominant_name,
    _perceptible_weights,
)

SCHEMA = "depth_reading_v1"
CLASSES = ("lead", "support", "shadow", "silent", "unknown")
TOP_N = 5
EARLY_T = (0.0, 300.0, 1800.0)
LATE_T = (7200.0, 14400.0)
SAME_TOP_FAMILY_FROM_T = 300.0
HEART_T = 1800.0
DRYDOWN_T = 14400.0
NO_DRYDOWN_CHANGE_MIN_SHARED = 4
# score_luxury's trace band on the concentrate state (scoring.py): rows with
# OAV < 0.1 are skipped as silent, 0.1 <= OAV <= 1.0 are counted as traces.
INDEX_TRACE_LOW = 0.1
INDEX_TRACE_HIGH = 1.0
UNASSIGNED = "unassigned"

_SEMANTICS = (
    "Screening diagnostic only. OAV is a detection-related diagnostic (AGENTS.md "
    "Rule 1), never perceived contribution, intensity, character or liking. This "
    "reading changes no gate verdict, score, ranking or overall status."
)


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(float(value), digits)


def _oav(material: Any) -> float | None:
    value = getattr(material, "screening_oav", None)
    return None if value is None else float(value)


def _label(value: Any) -> str:
    text = str(value or "").strip()
    return text or UNASSIGNED


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _unknown_reason(material: Any) -> dict[str, Any]:
    return {
        "physics_status": getattr(material, "physics_status", None),
        "physics_blockers": list(getattr(material, "physics_blockers", ()) or ()),
        "missing_fields": list(getattr(material, "missing_fields", ()) or ()),
    }


def _window_reading(frame: Any) -> dict[str, Any]:
    materials = list(frame.state.materials)
    perceptible = [m for m in materials if (_oav(m) or 0.0) >= 1.0]
    families = _counts(_label(m.family) for m in perceptible)
    textures = _counts(_label(m.texture) for m in perceptible)
    family_of = {str(m.name): _label(m.family) for m in materials}
    family_weights: dict[str, float] = {}
    row_weights = _perceptible_weights(materials)
    for name, weight in row_weights.items():
        family = family_of[name]
        family_weights[family] = family_weights.get(family, 0.0) + weight
    shape = _distribution_shape(family_weights)
    total = sum(family_weights.values())
    top_family = _dominant_name(family_weights)
    return {
        "label": frame.label,
        "t_seconds": float(frame.t_seconds),
        "rows_oav_ge_1": len(perceptible),
        "families": families,
        "assigned_family_count": sum(1 for key in families if key != UNASSIGNED),
        "textures": textures,
        "assigned_texture_count": sum(1 for key in textures if key != UNASSIGNED),
        "family_weights": {
            "basis": (
                "modelled screening intensity of rows with OAV >= 1, summed by "
                "family; not measured intensity"
            ),
            "weighted_rows": len(row_weights),
            "effective_family_count": _round(shape["effective_component_count"]),
            "top_family": top_family,
            "top_family_share": (
                None if top_family is None or total <= 0
                else _round(family_weights[top_family] / total)
            ),
            "shares": {
                family: _round(weight / total)
                for family, weight in sorted(
                    family_weights.items(), key=lambda item: (-item[1], item[0])
                )
            } if total > 0 else {},
        },
        "top5": [
            {"material": row["material"], "oav": row["oav"], "family": row["family"]}
            for row in frame.dominant_oav(limit=TOP_N)
        ],
    }


def _row_readings(frames: Sequence[Any], windows: Sequence[Mapping[str, Any]]) -> list[dict]:
    labels = [frame.label for frame in frames]
    t_of = {frame.label: float(frame.t_seconds) for frame in frames}
    top5_names = {w["label"]: {row["material"] for row in w["top5"]} for w in windows}
    by_window = [{str(m.name): m for m in frame.state.materials} for frame in frames]
    rows = []
    for material in frames[0].state.materials:
        name = str(material.name)
        oav = {label: _oav(by_window[i][name]) for i, label in enumerate(labels)}
        known = [(label, value) for label, value in oav.items() if value is not None]
        max_oav = max((value for _, value in known), default=None)
        peak_window = next((label for label, value in known if value == max_oav), None)
        top5_windows = [label for label in labels if name in top5_names[label]]
        if max_oav is None:
            row_class = "unknown"
        elif top5_windows:
            row_class = "lead"
        elif max_oav >= 1.0:
            row_class = "support"
        elif max_oav >= 0.1:
            row_class = "shadow"
        else:
            row_class = "silent"
        early = any((oav[label] or 0.0) >= 1.0 for label in labels if t_of[label] in EARLY_T)
        late = any((oav[label] or 0.0) >= 1.0 for label in labels if t_of[label] in LATE_T)
        row = {
            "name": name,
            "class": row_class,
            "bridge": bool(early and late),
            "max_oav": _round(max_oav),
            "peak_window": peak_window,
            "family": material.family,
            "texture": material.texture or None,
            "top5_windows": top5_windows,
            "oav_by_window": {label: _round(value) for label, value in oav.items()},
        }
        if row_class == "unknown":
            row["unknown_reason"] = _unknown_reason(material)
        rows.append(row)
    return rows


def _index_shadows(
    index_rows: Iterable[Mapping[str, Any]] | None,
    class_of: Mapping[str, str],
    max_oav_of: Mapping[str, float | None],
) -> dict[str, Any]:
    band = (
        f"{INDEX_TRACE_LOW} <= concentrate OAV <= {INDEX_TRACE_HIGH} "
        "(score_luxury trace band)"
    )
    if index_rows is None:
        return {"status": "NOT_SUPPLIED", "band": band}
    traces = []
    for row in index_rows:
        value = row.get("oav")
        if value is None or not INDEX_TRACE_LOW <= float(value) <= INDEX_TRACE_HIGH:
            continue
        name = str(row["name"])
        if name not in class_of:
            raise ValueError(f"index row {name!r} is not in the simulation frames")
        traces.append(
            {
                "name": name,
                "concentrate_oav": _round(value),
                "class": class_of[name],
                "max_oav_over_windows": _round(max_oav_of[name]),
            }
        )
    by_class = {key: 0 for key in CLASSES}
    for trace in traces:
        by_class[trace["class"]] += 1
    return {
        "status": "AVAILABLE",
        "band": band,
        "count": len(traces),
        "by_class": by_class,
        "not_shadow_over_time": len(traces) - by_class["shadow"],
        "rows": traces,
    }


def _assigned(family: str | None) -> bool:
    return family is not None and family != UNASSIGNED


def _drydown_change(windows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    heart = next((w for w in windows if w["t_seconds"] == HEART_T), None)
    drydown = next((w for w in windows if w["t_seconds"] == DRYDOWN_T), None)
    if heart is None or drydown is None:
        return {"status": "UNAVAILABLE", "reason": "no 30 min or 4 h window"}
    heart_top5 = [row["material"] for row in heart["top5"]]
    drydown_top5 = [row["material"] for row in drydown["top5"]]
    heart_family = heart["family_weights"]["top_family"]
    drydown_family = drydown["family_weights"]["top_family"]
    unchanged = _assigned(heart_family) and heart_family == drydown_family
    return {
        "status": "AVAILABLE",
        "heart_window": heart["label"],
        "drydown_window": drydown["label"],
        "top5_shared": len(set(heart_top5) & set(drydown_top5)),
        "shared_rows": [name for name in heart_top5 if name in drydown_top5],
        "heart_top_family": heart_family,
        "drydown_top_family": drydown_family,
        "top_family_unchanged": unchanged,
    }


def _flags(
    rows: Sequence[Mapping[str, Any]],
    windows: Sequence[Mapping[str, Any]],
    index_shadows: Mapping[str, Any],
    drydown: Mapping[str, Any],
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if index_shadows.get("status") == "AVAILABLE" and index_shadows["not_shadow_over_time"]:
        flags.append(
            {
                "code": "INDEX_SHADOWS_NOT_SHADOWS",
                "message": (
                    f"{index_shadows['not_shadow_over_time']} of the "
                    f"{index_shadows['count']} rows the luxury index counts as shadows "
                    "are not shadows over the gate's windows"
                ),
                "index_shadow_rows": index_shadows["count"],
                "not_shadow_over_time": index_shadows["not_shadow_over_time"],
                "by_class": dict(index_shadows["by_class"]),
            }
        )
    silent = [row["name"] for row in rows if row["class"] == "silent"]
    if silent:
        flags.append(
            {
                "code": "SILENT_ROWS",
                "message": f"{len(silent)} rows never reach OAV 0.1 in any window",
                "count": len(silent),
                "rows": silent,
            }
        )
    later = [w for w in windows if w["t_seconds"] >= SAME_TOP_FAMILY_FROM_T]
    tops = [w["family_weights"]["top_family"] for w in later]
    if later and all(_assigned(top) for top in tops) and len(set(tops)) == 1:
        flags.append(
            {
                "code": "SAME_TOP_FAMILY",
                "message": (
                    f"{tops[0]} tops the family weights in all {len(later)} windows "
                    "from 5 min on"
                ),
                "family": tops[0],
                "windows": len(later),
                "top_family_shares": {
                    w["label"]: w["family_weights"]["top_family_share"] for w in later
                },
            }
        )
    if (
        drydown.get("status") == "AVAILABLE"
        and drydown["top5_shared"] >= NO_DRYDOWN_CHANGE_MIN_SHARED
        and drydown["top_family_unchanged"]
    ):
        flags.append(
            {
                "code": "NO_DRYDOWN_CHANGE",
                "message": (
                    f"top 5 at heart and drydown share {drydown['top5_shared']} rows and "
                    f"{drydown['heart_top_family']} stays the top family"
                ),
                "top5_shared": drydown["top5_shared"],
                "top_family": drydown["heart_top_family"],
            }
        )
    return flags


def build_depth_reading(
    frames: Sequence[Any],
    index_rows: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the JSON-serialisable depth reading for one formula.

    ``frames`` are the gate's ``SimulationFrame`` objects (``GateReport.simulation``).
    ``index_rows`` are the concentrate-state rows ``score_luxury`` reads, as
    mappings with ``name`` and unrounded ``oav``; omitted, the index-shadow check
    is reported as ``NOT_SUPPLIED``.
    """
    frames = list(frames)
    if not frames:
        return {"schema": SCHEMA, "status": "UNAVAILABLE", "reason": "no simulation frames"}
    windows = [_window_reading(frame) for frame in frames]
    rows = _row_readings(frames, windows)
    class_of = {row["name"]: row["class"] for row in rows}
    max_oav_of = {row["name"]: row["max_oav"] for row in rows}
    index_shadows = _index_shadows(index_rows, class_of, max_oav_of)
    drydown = _drydown_change(windows)
    class_counts = {key: 0 for key in CLASSES}
    for row in rows:
        class_counts[row["class"]] += 1
    return {
        "schema": SCHEMA,
        "status": "AVAILABLE",
        "authority": "SCREENING_DIAGNOSTIC_ONLY",
        "verdict_effect": "NONE",
        "semantics": _SEMANTICS,
        "oav_source": (
            "SimulationFrame.state.materials[*].screening_oav of the gate's frames; "
            "top 5 from SimulationFrame.dominant_oav (the gate's dominant_leaders)"
        ),
        "windows": windows,
        "class_counts": class_counts,
        "bridge_count": sum(1 for row in rows if row["bridge"]),
        "rows": rows,
        "index_shadows": index_shadows,
        "drydown_change": drydown,
        "flags": _flags(rows, windows, index_shadows, drydown),
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def _one_decimal(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}"


def depth_reading_text_lines(reading: Mapping[str, Any]) -> list[str]:
    """Return the short text section the gate prints for one formula."""
    if reading.get("status") != "AVAILABLE":
        return [f"  Depth reading: {reading.get('status')} ({reading.get('reason', '')})"]
    lines = [
        "  Depth reading (screening diagnostic; OAV is detection-related, not intensity; "
        "changes no verdict):"
    ]
    for w in reading["windows"]:
        weights = w["family_weights"]
        lines.append(
            f"    {w['label']}: {w['rows_oav_ge_1']} rows OAV>=1, "
            f"{w['assigned_family_count']} families, {w['assigned_texture_count']} textures; "
            f"top family {weights['top_family'] or 'n/a'} "
            f"{_pct(weights['top_family_share'])} of modelled weight, "
            f"effective families {_one_decimal(weights['effective_family_count'])}"
        )
    counts = reading["class_counts"]
    lines.append(
        "    Row classes: "
        + ", ".join(f"{key} {counts[key]}" for key in CLASSES)
        + f"; bridge {reading['bridge_count']}"
    )
    index = reading["index_shadows"]
    if index["status"] == "AVAILABLE":
        lines.append(
            f"    Index shadows (luxury index traces, concentrate OAV 0.1-1.0): {index['count']} -> "
            + ", ".join(f"{key} {index['by_class'][key]}" for key in CLASSES)
        )
    else:
        lines.append(f"    Index shadows: {index['status']}")
    drydown = reading["drydown_change"]
    if drydown["status"] == "AVAILABLE":
        lines.append(
            f"    Drydown change: top 5 at {drydown['heart_window']} and "
            f"{drydown['drydown_window']} share {drydown['top5_shared']}; top family "
            f"{drydown['heart_top_family'] or 'n/a'} -> {drydown['drydown_top_family'] or 'n/a'}"
        )
    else:
        lines.append(f"    Drydown change: {drydown['status']}")
    flags = reading["flags"]
    lines.append(
        "    Flags: "
        + ("; ".join(f"{flag['code']} ({flag['message']})" for flag in flags) if flags else "none")
    )
    return lines
