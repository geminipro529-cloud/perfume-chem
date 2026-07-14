#!/usr/bin/env python3
"""Format a pipeline JSON output into a complete, thorough perfumer analysis.
Run: python scripts/format_pipeline_analysis.py --input <pipeline_output.json>
"""

from __future__ import annotations

import argparse
import io
import json
import math
import statistics
import sys
from pathlib import Path

# Force stdout to UTF-8 regardless of the console codepage.
# Without this, characters like \xd7 (×) crash the script when the
# console codepage is CP874 (Thai) or anything other than UTF-8.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


OAV_BRACKETS = [
    (10000, "massive"),
    (1000, "very strong"),
    (100, "strong"),
    (50, "moderate-strong"),
    (10, "moderate"),
    (5, "perceptible"),
    (1, "at threshold"),
    (0, "sub-threshold"),
]


def oav_label(oav: float) -> str:
    for threshold, label in OAV_BRACKETS:
        if oav >= threshold:
            return label
    return "sub-threshold"


def load_pipeline(path):
    with open(path, "rb") as f:
        raw = f.read()
    # Strip BOM (UTF-8 / UTF-16LE / UTF-16BE) and decode
    if raw[:3] == b"\xef\xbb\xbf":
        raw = raw[3:]
        text = raw.decode("utf-8")
    elif raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8", errors="replace")
    return json.loads(text)


def sort_by_oav(materials):
    return sorted(materials, key=lambda m: m.get("oav", 0) or 0, reverse=True)


def _compute_longevity(ts):
    """Compute longevity estimate (hours) from temporal time-series data.

    Uses the ratio of base-note OAV at drydown (4h) vs opening (0s) scaled by 8.0.
    If base OAV grows as top notes evaporate (ratio > 1), longevity exceeds 8h.
    Returns None when temporal data is missing or base OAV at opening is zero.
    """
    if not ts or len(ts) < 2:
        return None
    opening_mats = ts[0]["state"].get("materials", [])
    drydown_mats = ts[-1]["state"].get("materials", [])
    base_oav_open = sum(
        m.get("oav", 0) or 0 for m in opening_mats if m.get("note") == "base"
    )
    base_oav_dry = sum(
        m.get("oav", 0) or 0 for m in drydown_mats if m.get("note") == "base"
    )
    if base_oav_open <= 0:
        return None
    return (base_oav_dry / base_oav_open) * 8.0


def build_gate_summary(formula):
    gates = formula.get("gates", [])
    passed = [g for g in gates if g["status"] == "PASS"]
    warned = [g for g in gates if g["status"] == "WARN"]
    failed = [g for g in gates if g["status"] == "FAIL"]
    lines = ["## Gate Summary", ""]
    lines.append(
        f"**{len(passed)} PASS** / **{len(warned)} WARN** / **{len(failed)} FAIL**"
    )
    lines.append("")
    for g in failed:
        lines.append(f"  FAIL {g['gate']}: {str(g.get('detail', ''))[:140]}")
    for g in warned:
        lines.append(f"  WARN {g['gate']}: {str(g.get('detail', ''))[:140]}")
    lines.append("")
    return lines


def build_oav_headspace_table(materials):
    lines = ["## Headspace OAV — Opening (0s)", ""]
    h = " | ".join(
        [
            "#",
            "Material",
            "OAV",
            "Note",
            "Percept",
            "VP Pa",
            "Vapor ppm",
            "ODT ppm",
            "Act g",
            "MF%",
            "Role",
        ]
    )
    sep = "|" + "|".join(["-" * max(3, len(c)) for c in h.split(" | ")]) + "|"
    lines.append(f"| {h} |")
    lines.append(sep)

    mats = sort_by_oav(materials)
    for i, m in enumerate(mats, 1):
        oav = m.get("oav", 0) or 0
        label = oav_label(oav)
        role = (m.get("profile_name", "") or "")[:30]
        vp = float(m.get("vp_pure_pa") or 0.0)
        vapor_ppm = float(m.get("vapor_ppm") or 0.0)
        odt_ppm = float(m.get("odt_air_ppm") or 0.0)
        active_g = float(m.get("active_g") or 0.0)
        mole_fraction = float(m.get("mole_fraction") or 0.0)
        lines.append(
            f"| {i:3d} | {m['name']:28s} | {oav:>10.1f} | {m.get('note', '?'):5s} | {label:>12s}"
            f" | {vp:>7.3f} | {vapor_ppm:>9.4f}"
            f" | {odt_ppm:>9.6f} | {active_g:>7.4f}"
            f" | {mole_fraction * 100:>5.2f} | {role:30s}"
        )

    total_ppm = sum(m.get("vapor_ppm", 0) or 0 for m in mats)
    ntop = sum(1 for m in mats if m.get("note") == "top")
    nheart = sum(1 for m in mats if m.get("note") == "heart")
    nbase = sum(1 for m in mats if m.get("note") == "base")
    lines.append("")
    lines.append(
        f"**Materials:** {len(mats)} total ({ntop} top, {nheart} heart, {nbase} base)"
    )
    lines.append(f"**Total vapor:** {total_ppm:.2f} ppm")
    return lines


def build_note_distribution(materials):
    lines = ["### Note Distribution", ""]
    mats = sort_by_oav(materials)
    total_act = sum(m.get("active_ul", 0) or 0 for m in mats) or 1
    total_oav = sum(m.get("oav", 0) or 0 for m in mats) or 1

    for tier_name in ("TOP", "HEART", "BASE"):
        tier = [m for m in mats if m.get("note") == tier_name.lower()]
        act_pct = sum(m.get("active_ul", 0) or 0 for m in tier) / total_act * 100
        oav_pct = sum(m.get("oav", 0) or 0 for m in tier) / total_oav * 100
        lines.append(
            f"**{tier_name}:** {len(tier)} mats, {act_pct:.1f}% active, {oav_pct:.1f}% OAV"
        )
        for m in tier[:6]:
            o = m.get("oav", 0) or 0
            vp = float(m.get("vp_pure_pa") or 0.0)
            lines.append(
                f"  - {m['name']:28s} OAV={o:>8.1f} ({oav_label(o)}) VP={vp:.3f}Pa"
            )
        if len(tier) > 6:
            lines.append(f"  ... and {len(tier) - 6} more")
    return lines


def build_subthreshold(materials):
    sub = [m for m in materials if (m.get("oav", 0) or 0) < 1]
    high = [m for m in materials if (m.get("oav", 0) or 0) > 5000]
    lines = []
    if sub:
        lines.append("### Sub-threshold Materials (OAV < 1)")
        lines.append(
            f"{len(sub)}/{len(materials)} materials below perceptible threshold"
        )
        for m in sub:
            oav = m.get("oav", 0) or 0
            role = (m.get("profile_name", "") or "")[:20]
            vp = float(m.get("vp_pure_pa") or 0.0)
            act = m.get("active_ul", 0) or 0
            flag = (
                "**Needs higher dose**"
                if "musk" in role.lower()
                else "Structural (acceptable)"
            )
            lines.append(
                f"  - {m['name']}: OAV={oav:.2f} VP={vp:.3f}Pa act={act:.0f}uL role={role} [{flag}]"
            )
    if high:
        lines.append("### High-OAV Flags (>5000)")
        for m in high:
            oav = m.get("oav", 0) or 0
            lines.append(
                f"  - {m['name']} OAV={oav:.0f} dominates headspace — may mask subtler notes"
            )
    return lines


def build_class_distribution(materials):
    lines = ["### OAV by Odor Family", ""]
    fams = {}
    for m in materials:
        f = m.get("family") or "?"
        oav = m.get("oav", 0) or 0
        if f not in fams:
            fams[f] = {"oav": 0, "names": []}
        fams[f]["oav"] += oav
        fams[f]["names"].append(m["name"])
    total = sum(v["oav"] for v in fams.values()) or 1
    for f, d in sorted(fams.items(), key=lambda x: x[1]["oav"], reverse=True):
        pct = d["oav"] / total * 100
        bar = "=" * max(1, int(pct / 2))
        lines.append(f"  {f:>15s} {pct:5.1f}% {bar}  ({len(d['names'])} mats)")
    return lines


def build_temporal(formula):
    ts = formula.get("time_series", [])
    lines = ["## Temporal Evolution (5 Windows)", ""]

    # Summary table
    h = " | ".join(["Window", "Time", "T/H/B", "Vapor", "Raw uL", "Leaders"])
    lines.append(f"| {h} |")
    lines.append("|" + "|".join(["-" * 12] * 6) + "|")
    first_ul = ts[0]["state"].get("total_raw_ul", 1) if ts else 1
    for w in ts:
        s = w["state"]
        nd = s.get("note_distribution", {})
        doms = w.get("dominant_oav", [])
        ldrs = ", ".join(f"{d['material'][:12]}({d['oav']:.0f})" for d in doms[:3])
        evap = 100 * (1 - s.get("total_raw_ul", 0) / first_ul)
        lines.append(
            f"| {w['label'][:12]:12s} | {w['t_seconds']:>6.0f}s | {nd.get('top', 0):>4.1f}/{nd.get('heart', 0):>3.1f}/{nd.get('base', 0):>4.1f}"
            f" | {s.get('total_vapor_ppm', 0):>6.2f}ppm | {s.get('total_raw_ul', 0):>6.0f} | {ldrs:>40s}"
        )
    lines.append("")

    # Detail per window
    lines.append("### Per-Window Detail")
    for w in ts:
        s = w["state"]
        nd = s.get("note_distribution", {})
        doms = w.get("dominant_oav", [])
        evap = 100 * (1 - s.get("total_raw_ul", 0) / first_ul)
        lines.append("")
        lines.append(f"**{w['label'].upper()}** ({w['t_seconds']}s) — Evap:{evap:.0f}%")
        lines.append(
            f"  T:{nd.get('top', 0):.1f}% H:{nd.get('heart', 0):.1f}% B:{nd.get('base', 0):.1f}%  Vapor:{s.get('total_vapor_ppm', 0):.2f}ppm"
        )
        if doms:
            lines.append(
                "  Leaders: "
                + " | ".join(f"{d['material']} OAV {d['oav']:.0f}" for d in doms[:5])
            )
    return lines


def build_perfumer(formula):
    mats = sort_by_oav(formula.get("formula_state", {}).get("materials", []))
    ts = formula.get("time_series", [])
    lines = []

    # Character
    lines.append("## Perfumer's Assessment")
    lines.append("")
    top_m = [m for m in mats if m.get("note") == "top"]
    heart_m = [m for m in mats if m.get("note") == "heart"]
    base_m = [m for m in mats if m.get("note") == "base"]

    lines.append("### 1. Character")
    tdesc = " + ".join(f"{m['name']}({oav_label(m.get('oav', 0))})" for m in top_m[:3])
    hdesc = (
        " + ".join(f"{m['name']}({oav_label(m.get('oav', 0))})" for m in heart_m[:2])
        or "(thin)"
    )
    bdesc = " + ".join(f"{m['name']}({oav_label(m.get('oav', 0))})" for m in base_m[:5])
    lines.append(f"  Top: {tdesc}")
    lines.append(f"  Heart: {hdesc}")
    lines.append(f"  Base: {bdesc}")
    lines.append("")

    # Opening
    lines.append("### 2. Opening (0-5min)")
    total_vapor = sum(m.get("vapor_ppm", 0) or 0 for m in mats)
    if top_m:
        lead = top_m[0]
        lines.append(
            f"  {lead['name']} dominates at OAV {lead.get('oav', 0):.0f} ({oav_label(lead.get('oav', 0))})."
        )
        for m in top_m[:4]:
            o = m.get("oav", 0) or 0
            vp = float(m.get("vp_pure_pa") or 0.0)
            lines.append(
                f"  - {m['name']} OAV={o:.0f} VP={vp:.1f}Pa ({m.get('family', '?')})"
            )
    lines.append(f"  Total vapor: {total_vapor:.1f} ppm")
    lines.append("")

    # Heart
    lines.append("### 3. Heart (30min-2hr)")
    if ts and len(ts) >= 3:
        hw = ts[2]
        hm = sort_by_oav(hw["state"].get("materials", []))
        hnd = hw["state"].get("note_distribution", {})
        for m in hm[:4]:
            o = m.get("oav", 0) or 0
            if o >= 1:
                lines.append(f"  {m['name']} OAV={o:.0f} ({oav_label(o)})")
        lines.append(
            f"  T:{hnd.get('top', 0):.1f}% H:{hnd.get('heart', 0):.1f}% B:{hnd.get('base', 0):.1f}%"
        )
        lines.append(f"  Vapor: {hw['state'].get('total_vapor_ppm', 0):.1f} ppm")
    lines.append("")

    # Drydown
    lines.append("### 4. Drydown (2hr-4hr+)")
    if ts and len(ts) >= 5:
        dw = ts[-1]
        dm = sort_by_oav(dw["state"].get("materials", []))
        dnd = dw["state"].get("note_distribution", {})
        lines.append(f"  Base dominates at {dnd.get('base', 0):.0f}% of headspace")
        for m in dm[:6]:
            o = m.get("oav", 0) or 0
            if o >= 1:
                lines.append(f"  - {m['name']} OAV={o:.0f}")
        lines.append(f"  Vapor: {dw['state'].get('total_vapor_ppm', 0):.1f} ppm")
    lines.append("")

    # Sillage
    lines.append("### 5. Sillage & Diffusion")
    carriers = [m for m in mats if (m.get("oav", 0) or 0) > 500]
    if carriers:
        cstr = " + ".join(f"{m['name']}({m['oav']:.0f})" for m in carriers[:4])
        lines.append(f"  Primary carriers: {cstr}")
    fams = {}
    for m in mats:
        f = m.get("family", "?")
        oav = m.get("oav", 0) or 0
        fams[f] = fams.get(f, 0) + oav
    tot = sum(fams.values()) or 1
    lines.append(
        "  OAV by family: "
        + " ".join(
            f"{f}{v / tot * 100:.0f}%"
            for f, v in sorted(fams.items(), key=lambda x: x[1], reverse=True)[:4]
        )
    )
    lines.append("")

    # Longevity
    lines.append("### 6. Longevity")
    if ts:
        f = ts[0]["state"]
        l = ts[-1]["state"]
        evap = 100 * (1 - l.get("total_raw_ul", 0) / f.get("total_raw_ul", 1))
        persist = l.get("note_distribution", {}).get("base", 0)
        lines.append(f"  Evaporation: {evap:.0f}% over 4h")
        lines.append(
            f"  Vapor: {f.get('total_vapor_ppm', 0):.1f} > {l.get('total_vapor_ppm', 0):.1f} ppm"
        )
        lines.append(f"  Base @ drydown: {persist:.0f}%")
        longevity_hr = _compute_longevity(ts)
        if longevity_hr is not None:
            lines.append(
                f"  Est. skin life: {longevity_hr:.0f}h moderate + {longevity_hr * 0.5:.0f}h skin scent"
            )
        else:
            lines.append(f"  Est. skin life: data insufficient")
    lines.append("")

    # Balance
    lines.append("### 7. Balance")
    nd = formula.get("formula_state", {}).get("note_distribution", {})
    oavs = [(m.get("oav", 0) or 0.001) for m in mats if (m.get("oav", 0) or 0) > 0]
    mx = max(oavs) if oavs else 0
    mn = min(oavs) if oavs else 0
    ct = statistics.stdev([math.log10(v) for v in oavs]) if len(oavs) > 1 else 0
    lines.append(
        f"  Pyramid: T:{nd.get('top', 0):.1f}% H:{nd.get('heart', 0):.1f}% B:{nd.get('base', 0):.1f}%"
    )
    lines.append(f"  OAV range: {mn:.2f} to {mx:.0f} (sigma-log={ct:.2f})")
    if ct > 1.2:
        lines.append(
            f"  Wide contrast: citrus (OAV {mx:.0f}) dominates opening before burning off to reveal base."
        )
    if (nd.get("heart", 0) or 0) < 10:
        lines.append(
            f"  Thin heart ({nd.get('heart', 0):.1f}%) — top-to-base architecture, authentic for vetiver."
        )
    for label in [
        "massive",
        "very strong",
        "strong",
        "moderate",
        "perceptible",
        "at threshold",
        "sub-threshold",
    ]:
        if label == "sub-threshold":
            cnt = sum(1 for o in oavs if o < 1)
        else:
            th = next((t for t, l in OAV_BRACKETS if l == label), 0)
            nth = next(
                (
                    t
                    for t, l in OAV_BRACKETS
                    if l == label and l != "sub-threshold" and False
                ),
                0,
            )
            cnt = sum(
                1
                for o in oavs
                if o >= th
                and o
                < next(
                    (
                        t
                        for t, l in OAV_BRACKETS
                        if l == label and OAV_BRACKETS.index((t, l)) > 0
                    ),
                    999999,
                )
            )
        if cnt:
            lines.append(f"    {label}: {cnt}")
    lines.append("")

    # Flags
    lines.append("### 8. Flags")
    for m in mats:
        oav = m.get("oav", 0) or 0
        if oav < 1:
            role = m.get("profile_name", "") or ""
            lines.append(f"  SUB: {m['name']} OAV={oav:.2f} role={role}")
    for m in mats:
        if "hedione" in m["name"].lower():
            odt = m.get("odt_air_ppm", 0)
            if odt >= 0.01:
                lines.append(
                    f"  NOTE: Hedione HC ODT={odt * 1000:.1f}ppb (alias collision: pure hedione ODT=0.05ppb, OAV would be 400x higher)"
                )
    for m in mats:
        if "evernyl" in m["name"].lower():
            pct = (
                m.get("active_ul", 0)
                / formula.get("formula_state", {}).get("total_active_ul", 1)
                * 100
            )
            if pct > 0.5:
                lines.append(
                    f"  IFRA: Evernyl at {pct:.2f}% active — check Cat4 limit (0.1% in product = 0.5% at 20% EdP)"
                )
    # General IFRA check for all restricted materials
    for m in mats:
        limit_pct = m.get("ifra_limit_pct")
        if limit_pct is not None and limit_pct > 0:
            pct = (
                m.get("active_ul", 0)
                / formula.get("formula_state", {}).get("total_active_ul", 1)
                * 100
            )
            if pct > limit_pct * 0.9:
                lines.append(
                    f"  IFRA: {m['name']} at {pct:.2f}% active — near/above Cat4 limit ({limit_pct}%)"
                )
    lines.append("")
    return lines


def build_oav_structural(materials: list[dict], formula: dict) -> list[str]:
    """Structural OAV analysis: tiers, block breakdown, balance critique."""
    lines = ["## Structural OAV Analysis", ""]
    if not materials:
        return lines

    tiers = {
        "massive": [],
        "v.strong": [],
        "strong": [],
        "moderate": [],
        "perceptible": [],
        "threshold": [],
        "sub": [],
    }
    total_vapor = sum(float(m.get("vapor_ppm", 0) or 0) for m in materials)
    active = sum(float(m.get("active_ul", 0) or 0) for m in materials)
    batch = float(formula.get("formula_state", {}).get("batch_volume_ml", 30))
    bottle_pct = active / max(batch * 1000, 1) * 100

    for m in materials:
        o = float(m.get("oav", 0) or 0)
        name = m.get("name", "")
        if o >= 1000:
            tiers["massive"].append((name, o))
        elif o >= 100:
            tiers["v.strong"].append((name, o))
        elif o >= 50:
            tiers["strong"].append((name, o))
        elif o >= 10:
            tiers["moderate"].append((name, o))
        elif o >= 5:
            tiers["perceptible"].append((name, o))
        elif o >= 1:
            tiers["threshold"].append((name, o))
        else:
            tiers["sub"].append((name, o))

    total_mats = len(materials)
    perceptible = total_mats - len(tiers["sub"])
    lines.append(
        f"**Vapor:** {total_vapor:.0f} ppm  |  **Active:** {bottle_pct:.1f}%  |  **Perceptible:** {perceptible}/{total_mats}"
    )

    lines.append("")
    lines.append("### OAV Tiers")
    for tier_name in [
        "massive",
        "v.strong",
        "strong",
        "moderate",
        "perceptible",
        "threshold",
        "sub",
    ]:
        items = tiers[tier_name]
        if not items:
            continue
        names = ", ".join(f"{n}({o:.0f})" for n, o in items)
        flags = []
        if any(o > 10000 for _, o in items):
            flags.append("fatigue risk")
        if tier_name == "massive" and len(items) >= 6:
            flags.append("overload risk")
        flag_str = f"  ! {', '.join(flags)}" if flags else ""
        lines.append(f"  **{tier_name}** ({len(items)}): {names}{flag_str}")

    lines.append("")
    lines.append("### Block Balance")
    citrus_oav = sum(
        float(m.get("oav", 0) or 0)
        for m in materials
        if m.get("note") == "top" and "citrus" in (m.get("family", "") or "").lower()
    )
    base_oav = sum(
        float(m.get("oav", 0) or 0) for m in materials if m.get("note") == "base"
    )
    floral_oav = sum(
        float(m.get("oav", 0) or 0) for m in materials if m.get("note") == "heart"
    )
    total_block = citrus_oav + base_oav + floral_oav or 1
    lines.append(
        f"  **Citrus** {citrus_oav:>8.0f} ({citrus_oav / total_block * 100:.0f}%)"
    )
    lines.append(
        f"  **Floral** {floral_oav:>8.0f} ({floral_oav / total_block * 100:.0f}%)"
    )
    lines.append(f"  **Base**   {base_oav:>8.0f} ({base_oav / total_block * 100:.0f}%)")
    maxb = max(citrus_oav, base_oav, floral_oav)
    minb = min(v for v in [citrus_oav, base_oav, floral_oav] if v > 0) or 1
    ratio = maxb / minb
    lines.append(
        f"  **Ratio:** {ratio:.0f}:1 between strongest/weakest block{' — CITRUS DOMINANT' if citrus_oav > floral_oav + base_oav else ''}"
    )

    lines.append("")
    lines.append("### Issues")
    issues = []
    if tiers["sub"]:
        issues.append(
            f"{len(tiers['sub'])} sub-threshold material(s): {', '.join(n for n, _ in tiers['sub'])}"
        )
    if not tiers["v.strong"]:
        issues.append("Missing 'very strong' tier (OAV 100-1000)")
    if not tiers["strong"]:
        issues.append("Missing 'strong' tier (OAV 50-100)")
    if citrus_oav > (floral_oav + base_oav) * 2:
        issues.append(
            f"Citrus dominates at {citrus_oav / total_block * 100:.0f}% of total OAV"
        )
    if len(tiers["massive"]) >= 8:
        issues.append(
            f"{len(tiers['massive'])} massive-OAV materials — sensory overload likely"
        )
    if issues:
        for issue in issues:
            lines.append(f"  ! {issue}")
    else:
        lines.append("  None detected")
    lines.append("")
    return lines


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", required=True)
    args = p.parse_args()

    data = load_pipeline(args.input)
    formula = data.get("formulas", [{}])[0]
    mats = formula.get("formula_state", {}).get("materials", [])

    for line in build_gate_summary(formula):
        print(line)
    for line in build_oav_headspace_table(mats):
        print(line)
    for line in build_note_distribution(mats):
        print(line)
    for line in build_class_distribution(mats):
        print(line)
    for line in build_subthreshold(mats):
        print(line)
    for line in build_temporal(formula):
        print(line)
    for line in build_oav_structural(mats, formula):
        print(line)
    for line in build_perfumer(formula):
        print(line)


if __name__ == "__main__":
    main()
