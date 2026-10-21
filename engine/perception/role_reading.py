"""Row roles over time: a detection diagnostic for the release gate.

What it is. Screening OAV per time window is a detection diagnostic (AGENTS.md
Rule 1). This reading takes the gate's own five simulation windows (0 s, 5 min,
30 min, 2 h, 4 h) and shows which rows reach detection (OAV >= 1) when, the role
each row takes over those windows, and which rows the luxury index
(``engine/optimizer/scoring.py`` ``score_luxury``) miscounts as sub-threshold
shadows.

What it is not. It does not measure depth, objects, textures, strength or
beauty. A count of detectable rows, families or textures is the size of the
crowd, not a number of objects, and supports no depth or luxury claim. Kenny's
nose decides: blotter, then skin, blind against his reference bottle (F12 in
``docs/agents/failure-registry.md``).

It is informational only. It changes no gate verdict, score, ranking or overall
status, and it re-runs no physics: every number comes from the frames and rows
the gate already built. OAV is ``MaterialState.screening_oav`` in each
``SimulationFrame``; the top 5 of a window is ``SimulationFrame.dominant_oav``
(what the gate prints as ``time_windows[*].dominant_leaders``).

Row classes (the studio role map's definitions, so counts agree):

* ``lead``: in the top 5 by OAV in at least one window.
* ``support``: OAV >= 1 in some window but never in a top 5.
* ``shadow``: 0.1 <= max OAV < 1.
* ``silent``: max OAV < 0.1 in every window that has an OAV.
* ``unknown``: no OAV in any window; the engine's reason is kept.
* ``bridge`` (flag, not a class): OAV >= 1 in an early window (0 s, 5 min or
  30 min) and in a late one (2 h or 4 h).

Flags (only these two):

* ``INDEX_SHADOWS_NOT_SHADOWS``: one or more rows the luxury index counts as
  traces (concentrate OAV 0.1-1.0, the band and inputs ``score_luxury`` reads)
  are not shadows over the windows, judged by the shadow definition on their
  max OAV (0.1 <= max OAV < 1). Rows that become notes, never reach 0.1 or have
  no OAV are named.
* ``SILENT_ROWS``: one or more rows have max OAV < 0.1 in every window that has
  an OAV, tested on max OAV directly, so a top-5 row in a tiny formula is caught.

Unknown rows are listed with their reason, never flagged. Data gaps never
raise: a row missing from a frame counts as no OAV in that window, and an index
row that matches no frame row is listed in ``index_shadows.unmatched``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "role_reading_v1"
CLASSES = ("lead", "support", "shadow", "silent", "unknown")
TOP_N = 5
DETECTION_OAV = 1.0
SHADOW_FLOOR_OAV = 0.1
EARLY_MAX_T = 1800.0  # early windows: 0 s, 5 min, 30 min
LATE_MIN_T = 7200.0  # late windows: 2 h, 4 h
HEART_T = 1800.0
DRYDOWN_T = 14400.0
# score_luxury's trace band on the concentrate state (scoring.py): rows with
# OAV < 0.1 are skipped as silent, 0.1 <= OAV <= 1.0 are counted as traces.
INDEX_TRACE_LOW = 0.1
INDEX_TRACE_HIGH = 1.0

WHAT_IT_IS = (
    "Screening OAV per time window is a detection diagnostic (AGENTS.md Rule 1). "
    "This reading shows which rows reach detection (OAV >= 1) when, and which rows "
    "the luxury index counts as sub-threshold shadows but are not."
)
WHAT_IT_IS_NOT = (
    "It does not measure depth, objects, textures, strength or beauty; counts of "
    "detectable rows, families or textures are the size of the crowd, not objects. "
    "Kenny's nose decides. It changes no gate verdict, score, ranking or overall status."
)


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(float(value), digits)


def _oav(material: Any) -> float | None:
    value = getattr(material, "screening_oav", None)
    return None if value is None else float(value)


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def time_label(t_seconds: float) -> str:
    """Write a window time the way a perfumer reads it: 0 s, 5 min, 30 min, 2 h, 4 h."""
    t = float(t_seconds)
    if t < 60.0:
        return f"{t:g} s"
    if t < 3600.0:
        return f"{t / 60.0:g} min"
    return f"{t / 3600.0:g} h"


def _named_counts(values: Iterable[str]) -> dict[str, int]:
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


def _window(frame: Any) -> dict[str, Any]:
    materials = list(frame.state.materials)
    detectable = [m for m in materials if (_oav(m) or 0.0) >= DETECTION_OAV]
    families = [_text(getattr(m, "family", None)) for m in detectable]
    textures = [_text(getattr(m, "texture", None)) for m in detectable]
    return {
        "label": frame.label,
        "t_seconds": float(frame.t_seconds),
        "time": time_label(frame.t_seconds),
        "rows_oav_ge_1": len(detectable),
        "top5": [
            {"material": row["material"], "oav": row["oav"]}
            for row in frame.dominant_oav(limit=TOP_N)
        ],
        "detectable_families": _named_counts(f for f in families if f),
        "detectable_rows_without_family": sum(1 for f in families if not f),
        "detectable_textures": _named_counts(t for t in textures if t),
        "detectable_rows_without_texture": sum(1 for t in textures if not t),
    }


def _row_class(max_oav: float | None, in_top5: bool) -> str:
    if max_oav is None:
        return "unknown"
    if in_top5:
        return "lead"
    if max_oav >= DETECTION_OAV:
        return "support"
    if max_oav >= SHADOW_FLOOR_OAV:
        return "shadow"
    return "silent"


def _rows(
    frames: Sequence[Any], windows: Sequence[Mapping[str, Any]]
) -> tuple[list[dict], dict[str, float | None]]:
    """Return the row readings and each row's unrounded max OAV (for the band tests)."""
    labels = [w["label"] for w in windows]
    times = [w["t_seconds"] for w in windows]
    top5_names = [{row["material"] for row in w["top5"]} for w in windows]
    by_window = [{str(m.name): m for m in frame.state.materials} for frame in frames]
    # Every row seen in any frame, in first-seen order; a row absent from a
    # frame has no OAV in that window.
    first_seen: dict[str, Any] = {}
    for materials in by_window:
        for name, material in materials.items():
            first_seen.setdefault(name, material)
    rows = []
    raw_max: dict[str, float | None] = {}
    for name, material in first_seen.items():
        oav = [_oav(materials.get(name)) for materials in by_window]
        known = [value for value in oav if value is not None]
        max_oav = max(known) if known else None
        peak = next((i for i, value in enumerate(oav) if value == max_oav), None)
        top5_windows = [labels[i] for i, names in enumerate(top5_names) if name in names]
        row_class = _row_class(max_oav, bool(top5_windows))
        early = any(
            value is not None and value >= DETECTION_OAV and times[i] <= EARLY_MAX_T
            for i, value in enumerate(oav)
        )
        late = any(
            value is not None and value >= DETECTION_OAV and times[i] >= LATE_MIN_T
            for i, value in enumerate(oav)
        )
        row = {
            "name": name,
            "class": row_class,
            "bridge": bool(early and late),
            "max_oav": _round(max_oav),
            "peak_window": None if max_oav is None else labels[peak],
            "peak_time": None if max_oav is None else time_label(times[peak]),
            "family": _text(getattr(material, "family", None)),
            "texture": _text(getattr(material, "texture", None)),
            "top5_windows": top5_windows,
            "oav_by_window": {label: _round(value) for label, value in zip(labels, oav)},
            "absent_from_windows": [
                labels[i] for i, materials in enumerate(by_window) if name not in materials
            ],
        }
        if row_class == "unknown":
            row["unknown_reason"] = _unknown_reason(material)
        rows.append(row)
        raw_max[name] = max_oav
    return rows, raw_max


def _over_time(max_oav: float | None) -> str:
    """Where a row's max OAV over the windows puts it against the shadow band."""
    if max_oav is None:
        return "no_oav"
    if max_oav >= DETECTION_OAV:
        return "becomes_note"
    if max_oav >= SHADOW_FLOOR_OAV:
        return "stays_shadow"
    return "never_reaches_0_1"


def _index_shadows(
    index_rows: Iterable[Mapping[str, Any]] | None,
    row_of: Mapping[str, Mapping[str, Any]],
    raw_max: Mapping[str, float | None],
) -> dict[str, Any]:
    band = f"{INDEX_TRACE_LOW} <= concentrate OAV <= {INDEX_TRACE_HIGH} (score_luxury trace band)"
    if index_rows is None:
        return {"status": "NOT_SUPPLIED", "band": band}
    traces = []
    unmatched = []
    for index_row in index_rows:
        value = index_row.get("oav")
        if value is None or not INDEX_TRACE_LOW <= float(value) <= INDEX_TRACE_HIGH:
            continue
        name = str(index_row.get("name"))
        row = row_of.get(name)
        if row is None:
            unmatched.append({"name": name, "concentrate_oav": _round(value)})
            continue
        traces.append(
            {
                "name": name,
                "concentrate_oav": _round(value),
                "class": row["class"],
                "max_oav_over_windows": row["max_oav"],
                "over_time": _over_time(raw_max[name]),
            }
        )
    by_class = {key: 0 for key in CLASSES}
    for trace in traces:
        by_class[trace["class"]] += 1

    def names(over_time: str) -> list[str]:
        return [trace["name"] for trace in traces if trace["over_time"] == over_time]

    stay = names("stays_shadow")
    return {
        "status": "AVAILABLE",
        "band": band,
        "count": len(traces) + len(unmatched),
        "matched": len(traces),
        "by_class": by_class,
        "stay_shadows": stay,
        "become_notes": names("becomes_note"),
        "never_reach_0_1": names("never_reaches_0_1"),
        "no_oav": names("no_oav"),
        "not_shadow_over_time": len(traces) - len(stay),
        "unmatched": unmatched,
        "rows": traces,
    }


def _heart_drydown(windows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    heart = next((w for w in windows if w["t_seconds"] == HEART_T), None)
    drydown = next((w for w in windows if w["t_seconds"] == DRYDOWN_T), None)
    if heart is None or drydown is None:
        return {"status": "UNAVAILABLE", "reason": "no 30 min or 4 h window"}
    heart_top5 = [row["material"] for row in heart["top5"]]
    drydown_top5 = [row["material"] for row in drydown["top5"]]
    shared = [name for name in heart_top5 if name in drydown_top5]
    return {
        "status": "AVAILABLE",
        "heart_time": heart["time"],
        "drydown_time": drydown["time"],
        "heart_top5": heart_top5,
        "drydown_top5": drydown_top5,
        "shared": len(shared),
        "shared_rows": shared,
    }


def _join(names: Sequence[str]) -> str:
    return ", ".join(names) if names else "none"


def _index_flag(index: Mapping[str, Any]) -> dict[str, Any] | None:
    if index.get("status") != "AVAILABLE" or not index["not_shadow_over_time"]:
        return None
    count = index["count"]
    stay = len(index["stay_shadows"])
    parts = [
        f"The luxury index counts {count} {'row' if count == 1 else 'rows'} as "
        f"sub-threshold shadows; over the gate's time windows {stay} "
        f"{'stays a shadow' if stay == 1 else 'stay shadows'} (peak OAV from 0.1 to below 1)."
    ]
    for label, key in (
        ("Become notes (OAV >= 1)", "become_notes"),
        ("Never reach 0.1", "never_reach_0_1"),
        ("No OAV", "no_oav"),
    ):
        if index[key]:
            parts.append(f"{label}: {_join(index[key])}.")
    if index["unmatched"]:
        parts.append(
            "Not in the frames: " + _join([row["name"] for row in index["unmatched"]]) + "."
        )
    return {
        "code": "INDEX_SHADOWS_NOT_SHADOWS",
        "message": " ".join(parts),
        "index_shadow_rows": index["count"],
        "stay_shadows": list(index["stay_shadows"]),
        "become_notes": list(index["become_notes"]),
        "never_reach_0_1": list(index["never_reach_0_1"]),
        "no_oav": list(index["no_oav"]),
        "unmatched": [row["name"] for row in index["unmatched"]],
    }


def _silent_flag(raw_max: Mapping[str, float | None]) -> dict[str, Any] | None:
    silent = [
        name
        for name, max_oav in raw_max.items()
        if max_oav is not None and max_oav < SHADOW_FLOOR_OAV
    ]
    if not silent:
        return None
    return {
        "code": "SILENT_ROWS",
        "message": (
            f"{len(silent)} {'row never reaches' if len(silent) == 1 else 'rows never reach'} "
            "OAV 0.1 in any window that has an OAV: "
            f"{_join(silent)}."
        ),
        "count": len(silent),
        "rows": silent,
    }


def build_role_reading(
    frames: Sequence[Any],
    index_rows: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the JSON-serialisable row-role reading for one formula.

    ``frames`` are the gate's ``SimulationFrame`` objects (``GateReport.simulation``).
    ``index_rows`` are the concentrate-state rows ``score_luxury`` reads, as
    mappings with ``name`` and unrounded ``oav``; omitted, the index-shadow check
    is reported as ``NOT_SUPPLIED``.
    """
    frames = list(frames)
    if not frames:
        return {
            "schema": SCHEMA,
            "status": "UNAVAILABLE",
            "reason": "no simulation frames",
            "verdict_effect": "NONE",
        }
    windows = [_window(frame) for frame in frames]
    rows, raw_max = _rows(frames, windows)
    index_shadows = _index_shadows(index_rows, {row["name"]: row for row in rows}, raw_max)
    flags = [
        flag for flag in (_index_flag(index_shadows), _silent_flag(raw_max)) if flag is not None
    ]
    class_rows = {key: [row["name"] for row in rows if row["class"] == key] for key in CLASSES}
    return {
        "schema": SCHEMA,
        "status": "OK",
        "authority": "SCREENING_DIAGNOSTIC_ONLY",
        "verdict_effect": "NONE",
        "what_it_is": WHAT_IT_IS,
        "what_it_is_not": WHAT_IT_IS_NOT,
        "oav_source": (
            "SimulationFrame.state.materials[*].screening_oav of the gate's frames; "
            "top 5 from SimulationFrame.dominant_oav (the gate's dominant_leaders)"
        ),
        "windows": windows,
        "class_counts": {key: len(names) for key, names in class_rows.items()},
        "class_rows": class_rows,
        "bridge_count": sum(1 for row in rows if row["bridge"]),
        "unknown_rows": [
            {"name": row["name"], "reason": row["unknown_reason"]}
            for row in rows
            if row["class"] == "unknown"
        ],
        "rows": rows,
        "index_shadows": index_shadows,
        "heart_drydown_top5": _heart_drydown(windows),
        "flags": flags,
    }


def _fmt_oav(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 10.0:
        return f"{value:.0f}"
    if value >= 1.0:
        return f"{value:.1f}"
    return f"{value:.2f}"


def _reason_text(reason: Mapping[str, Any]) -> str:
    missing = reason.get("missing_fields") or []
    if missing:
        return "missing " + ", ".join(str(field) for field in missing)
    blockers = reason.get("physics_blockers") or []
    if blockers:
        return ", ".join(str(blocker) for blocker in blockers)
    return str(reason.get("physics_status") or "no reason given")


def role_reading_text_lines(reading: Mapping[str, Any]) -> list[str]:
    """Return the short text section the gate prints for one formula."""
    title = "  Row roles over time"
    if reading.get("status") != "OK":
        detail = reading.get("error") or reading.get("reason") or ""
        return [f"{title}: {reading.get('status')} ({detail})"]
    lines = [
        f"{title} (detection diagnostic, AGENTS.md Rule 1; changes no verdict):",
        "    Screening OAV per window shows which rows reach detection when and which rows "
        "the luxury index miscounts. It does not measure depth, objects, textures, "
        "strength or beauty; Kenny's nose decides.",
    ]
    for w in reading["windows"]:
        top5 = ", ".join(f"{row['material']} {_fmt_oav(row['oav'])}" for row in w["top5"])
        lines.append(
            f"    {w['time']}: {w['rows_oav_ge_1']} rows at OAV >= 1; top 5: {top5 or 'none'}"
        )
    counts = reading["class_counts"]
    named = reading["class_rows"]
    unknown = [f"{row['name']}: {_reason_text(row['reason'])}" for row in reading["unknown_rows"]]
    lines.append(
        f"    Roles: lead {counts['lead']}, support {counts['support']}, "
        f"shadow {counts['shadow']} ({_join(named['shadow'])}), "
        f"silent {counts['silent']} ({_join(named['silent'])}), "
        f"unknown {counts['unknown']} ({'; '.join(unknown) or 'none'})"
    )
    lines.append(
        "    Lead = top 5 in some window; support = OAV >= 1, never top 5; shadow = peak "
        "OAV 0.1 to below 1; silent = never OAV 0.1; "
        f"{reading['bridge_count']} bridge rows = detectable both early (by 30 min) "
        "and late (2 h or later)"
    )
    pair = reading["heart_drydown_top5"]
    if pair["status"] == "AVAILABLE":
        lines.append(
            f"    Top 5 at {pair['heart_time']} and {pair['drydown_time']} share "
            f"{pair['shared']}: {_join(pair['shared_rows'])}"
        )
    flags = reading["flags"]
    if flags:
        lines.extend(f"    {flag['code']}: {flag['message']}" for flag in flags)
    else:
        lines.append("    Flags: none")
    return lines
