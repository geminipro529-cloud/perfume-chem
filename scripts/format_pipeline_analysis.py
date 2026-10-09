#!/usr/bin/env python3
"""Format a pipeline JSON output into a complete, thorough perfumer analysis.
Run: python scripts/format_pipeline_analysis.py --input <pipeline_output.json>
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import unicodedata


# Force stdout to UTF-8 regardless of the console codepage.
# Without this, characters like \xd7 (×) crash the script when the
# console codepage is CP874 (Thai) or anything other than UTF-8.
def _configure_cli_stdio() -> None:
    """Use UTF-8 for CLI output without replacing process-global streams."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


_ASCII_TRANSPORT_REPLACEMENTS = str.maketrans(
    {
        "—": "--",
        "–": "-",
        "−": "-",
        "µ": "u",
        "γ": "gamma",
        "×": "x",
        "→": "->",
        "←": "<-",
        "≤": "<=",
        "≥": ">=",
        "±": "+/-",
        "°": " deg",
        "α": "alpha",
        "β": "beta",
        "δ": "delta",
        "Δ": "Delta",
        "σ": "sigma",
        "Σ": "Sigma",
        "•": "*",
        "✓": "PASS",
        "✗": "FAIL",
    }
)


def cli_transport_text(text: str, *, ascii_only: bool | None = None) -> str:
    """Return stable CLI text across Windows native-process pipes.

    Persisted Markdown and JSON retain their original Unicode. Only live output
    is transliterated when a Windows process is writing to a pipe, where legacy
    PowerShell may decode UTF-8 bytes with the active locale code page.
    """
    if ascii_only is None:
        is_tty = bool(getattr(sys.stdout, "isatty", lambda: False)())
        ascii_only = os.name == "nt" and not is_tty
    if not ascii_only:
        return text

    translated = text.translate(_ASCII_TRANSPORT_REPLACEMENTS)
    normalized = unicodedata.normalize("NFKD", translated)
    return normalized.encode("ascii", errors="backslashreplace").decode("ascii")


# Numeric OAV ranges only. OAV is concentration over a detection threshold; it is not
# perceived intensity (AGENTS.md Rule 1), so the labels carry no loudness words.
_SUB_THRESHOLD_LABEL = "OAV < 1"
OAV_BRACKETS = [
    (10000, "OAV >= 10,000"),
    (1000, "OAV 1,000-10,000"),
    (100, "OAV 100-1,000"),
    (50, "OAV 50-100"),
    (10, "OAV 10-50"),
    (5, "OAV 5-10"),
    (1, "OAV 1-5"),
    (0, _SUB_THRESHOLD_LABEL),
]


def oav_label(oav: float | None) -> str:
    if oav is None:
        return "unknown"
    for threshold, label in OAV_BRACKETS:
        if oav >= threshold:
            return label
    return _SUB_THRESHOLD_LABEL


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
    return sorted(
        materials,
        key=lambda m: (m.get("oav") is not None, float(m.get("oav") or 0.0)),
        reverse=True,
    )


def _oav_number(material: dict) -> float:
    value = material.get("oav")
    return float(value) if value is not None else 0.0


def _oav_text(value: float | None, precision: int = 1) -> str:
    if value is None:
        return "UNKNOWN"
    return f"{float(value):.{precision}f}"


def _number_text(value, precision: int = 3) -> str:
    if value is None:
        return "UNKNOWN"
    return f"{float(value):.{precision}f}"


def _complete_numeric_sum(rows: list[dict], key: str) -> float | None:
    values = [row.get(key) for row in rows]
    if not values or any(value is None for value in values):
        return None
    return sum(float(value) for value in values)


def _ppm_text(value, precision: int = 1) -> str:
    return "UNKNOWN" if value is None else f"{float(value):.{precision}f} ppm"


def _functional_role(material: dict) -> str:
    return str(material.get("role") or "unspecified")


def _requires_perceptibility(material: dict) -> bool:
    role = _functional_role(material).casefold()
    texture = str(material.get("texture") or "").casefold()
    family = str(material.get("family") or "").casefold()
    return (
        role in {"character", "radiance"}
        or any(
            token in texture for token in ("lift", "diffusion", "projection", "radiance", "halo")
        )
        or (family == "musk" and role != "fixative")
    )


def build_gate_summary(formula):
    gates = formula.get("gates", [])
    passed = [g for g in gates if g["status"] == "PASS"]
    warned = [g for g in gates if g["status"] == "WARN"]
    held = [g for g in gates if g["status"] == "HOLD"]
    failed = [g for g in gates if g["status"] == "FAIL"]
    lines = ["## Gate Summary", ""]
    lines.append(
        f"**{len(passed)} PASS** / **{len(warned)} WARN** / "
        f"**{len(held)} HOLD** / **{len(failed)} FAIL**"
    )
    lines.append("")
    for g in failed:
        lines.append(f"  FAIL {g['gate']}: {str(g.get('detail', ''))}")
    for g in held:
        lines.append(f"  HOLD {g['gate']}: {str(g.get('detail', ''))}")
    for g in warned:
        lines.append(f"  WARN {g['gate']}: {str(g.get('detail', ''))}")
    lines.append("")
    return lines


def build_reference_deviation(formula):
    """Produce a per-contract deviation report from reference_claim_contract data.

    Shows which marker groups pass/fail per detected reference perfume,
    and flags over-add materials that belong to a different reference's DNA.
    """
    gate_map = {gate.get("gate"): gate for gate in formula.get("gates", [])}
    claim_gate = gate_map.get("reference_claim_contract")
    if not claim_gate:
        return []

    claim_data = claim_gate.get("data", {})
    evaluations = claim_data.get("evaluations", [])
    over_add_analysis = claim_data.get("over_add_analysis", [])
    metadata_warning = claim_data.get("metadata_warning", "")

    if not evaluations and not over_add_analysis:
        return []

    lines = ["## Reference Deviation Report", ""]

    if metadata_warning:
        lines.append(f"> ⚠️ {metadata_warning}")
        lines.append(
            "> Architecture evaluation below is best-effort — "
            "quantitative similarity cannot be assessed without "
            "explicit Claim mode and Reference scope metadata."
        )
        lines.append("")

    # --- Per-contract evaluation ---
    for ev in evaluations:
        display = ev.get("display_name", ev.get("contract_id", "Unknown"))
        lines.append(f"### {display}")
        lines.append("")

        scope_error = ev.get("scope_error")
        if scope_error:
            lines.append(f"> ❌ Scope error: {scope_error}")
            lines.append("")
            continue

        matched = ev.get("matched_groups", {})
        missing = ev.get("missing_groups", [])
        all_groups = ev.get("all_group_names", list(matched.keys()) + missing)

        for group_name in all_groups:
            if group_name in matched:
                mats = ", ".join(matched[group_name])
                lines.append(f"| ✅ | **{group_name}** | {mats} |")
            elif group_name in missing:
                lines.append(f"| ❌ | **{group_name}** | *MISSING* |")

        lines.append("")

        if ev["status"] == "FAIL":
            lines.append(f"**Result:** {len(missing)}/{len(all_groups)} marker group(s) missing")
        else:
            lines.append(f"**Result:** All {len(all_groups)} marker groups matched")
        lines.append("")

    # --- Over-add analysis ---
    if over_add_analysis:
        lines.append("### Over-Add Materials")
        lines.append("")
        lines.append(
            "Materials present in the formula that match a different "
            "reference perfume's DNA but NOT the primary target. "
            "If optimizing for the primary reference, these are "
            "candidates for removal."
        )
        lines.append("")
        for primary_block in over_add_analysis:
            primary_name = primary_block.get("primary_display_name", "Unknown")
            lines.append(f"**Extraneous to {primary_name}:**")
            lines.append("")
            for oa in primary_block.get("over_adds", []):
                source_name = oa.get("source_display_name", "Unknown")
                for group_name, materials in oa.get("extraneous_groups", {}).items():
                    mats_str = ", ".join(materials)
                    lines.append(
                        f"| ❌ | {mats_str} | "
                        f"Belongs to **{source_name}** `{group_name}` group "
                        f"— not in {primary_name} |"
                    )
            lines.append("")
        lines.append(
            "> ⚠️ These materials waste both formula space and budget if the "
            "target is the primary reference. They pull the character toward "
            "a different perfume's DNA."
        )
        lines.append("")

    return lines


def build_authority_dimensions(formula, manifest=None):
    gate_map = {gate.get("gate"): gate for gate in formula.get("gates", [])}
    state = formula.get("formula_state", {})
    quantitative = state.get("quantitative_authority", {})
    confidence = formula.get("confidence", {})
    stock_gate = gate_map.get("inventory_stock_contract", {})
    claim_gate = gate_map.get("reference_claim_contract", {})
    claim_data = claim_gate.get("data", {})
    combined = confidence.get("combined_confidence")
    if combined is None:
        combined = confidence.get("overall_confidence")
    combined_text = "UNKNOWN" if combined is None else f"{float(combined):.1f}/100"

    return [
        "## Authority Dimensions",
        "",
        "| Dimension | Status | Authority |",
        "|---|---|---|",
        f"| Inventory stock | {stock_gate.get('status', 'UNKNOWN')} | "
        f"{stock_gate.get('detail', 'No stock gate result.')} |",
        "| Quantitative ppm w/w | "
        f"{quantitative.get('active_concentrate_ppm_w_w', 'UNAVAILABLE')} | "
        "Exact only when the full declared mass and density chain is available. |",
        "| Headspace/OAV | "
        f"{quantitative.get('headspace_oav', state.get('headspace_basis', 'UNKNOWN'))} | "
        f"{quantitative.get('headspace_model_class', 'HEURISTIC_NOT_MEASURED')}; "
        "diagnostic model, not measured odor intensity. |",
        f"| Named reference | {claim_gate.get('status', 'UNKNOWN')} "
        f"({claim_data.get('scope', 'none')}) | "
        f"{claim_gate.get('detail', 'No named-reference contract.')} |",
        "| Sensory similarity | NOT_AUTHORIZED_NOT_MEASURED | "
        "Requires blinded bench comparison; no model score supplies this authority. |",
        f"| Combined confidence | {combined_text} | "
        "Aggregate diagnostic only; it cannot override any authority dimension above. |",
        "",
    ]


def _legacy_build_oav_headspace_table(materials):
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
        oav = m.get("oav")
        oav_text = _oav_text(oav)
        label = oav_label(oav)
        role = (m.get("profile_name", "") or "")[:30]
        vp = float(m.get("vp_pure_pa") or 0.0)
        vapor_ppm = float(m.get("vapor_ppm") or 0.0)
        odt_ppm = float(m.get("odt_air_ppm") or 0.0)
        active_g = float(m.get("active_g") or 0.0)
        mole_fraction = float(m.get("mole_fraction") or 0.0)
        lines.append(
            f"| {i:3d} | {m['name']:28s} | {oav_text:>10s} | {m.get('note', '?'):5s} | {label:>12s}"
            f" | {vp:>7.3f} | {vapor_ppm:>9.4f}"
            f" | {odt_ppm:>9.6f} | {active_g:>7.4f}"
            f" | {mole_fraction * 100:>5.2f} | {role:30s}"
        )

    total_ppm = sum(m.get("vapor_ppm", 0) or 0 for m in mats)
    ntop = sum(1 for m in mats if m.get("note") == "top")
    nheart = sum(1 for m in mats if m.get("note") == "heart")
    nbase = sum(1 for m in mats if m.get("note") == "base")
    lines.append("")
    lines.append(f"**Materials:** {len(mats)} total ({ntop} top, {nheart} heart, {nbase} base)")
    lines.append(f"**Total vapor:** {total_ppm:.2f} ppm")
    return lines


def build_oav_headspace_table(materials):
    lines = ["## Headspace OAV — Opening (0s)", ""]
    lines.append(
        "| Material | Dil | Raw µL | Act µL | MW | MF% | VP Pa | γ | "
        "Vapor ppm | ODT ppm | OAV | Note |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")

    mats = sort_by_oav(materials)
    for material in mats:
        dilution = material.get("dilution")
        dil_text = "UNKNOWN" if dilution is None else f"{float(dilution) * 100:.1f}%"
        mole_fraction = material.get("mole_fraction")
        mf_text = "UNKNOWN" if mole_fraction is None else f"{float(mole_fraction) * 100:.3f}"
        lines.append(
            f"| {material.get('name', 'UNKNOWN')} | {dil_text} | "
            f"{_number_text(material.get('raw_ul'), 2)} | "
            f"{_number_text(material.get('active_ul'), 2)} | "
            f"{_number_text(material.get('mw_g_mol'), 3)} | {mf_text} | "
            f"{_number_text(material.get('vp_pure_pa'), 6)} | "
            f"{_number_text(material.get('gamma'), 3)} | "
            f"{_number_text(material.get('vapor_ppm'), 6)} | "
            f"{_number_text(material.get('odt_air_ppm'), 9)} | "
            f"{_oav_text(material.get('oav'))} | "
            f"{material.get('note', 'UNKNOWN')} |"
        )

    total_ppm = _complete_numeric_sum(mats, "vapor_ppm")
    ntop = sum(1 for material in mats if material.get("note") == "top")
    nheart = sum(1 for material in mats if material.get("note") == "heart")
    nbase = sum(1 for material in mats if material.get("note") == "base")
    lines.extend(
        [
            "",
            f"**Materials:** {len(mats)} total ({ntop} top, {nheart} heart, {nbase} base)",
            f"**Total vapor:** {_ppm_text(total_ppm, 2)}",
        ]
    )
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
            o = m.get("oav")
            vp = float(m.get("vp_pure_pa") or 0.0)
            lines.append(
                f"  - {m['name']:28s} OAV={_oav_text(o):>8s} ({oav_label(o)}) VP={vp:.3f}Pa"
            )
        if len(tier) > 6:
            lines.append(f"  ... and {len(tier) - 6} more")
    return lines


def build_subthreshold(materials):
    sub = [m for m in materials if m.get("oav") is not None and m["oav"] < 1]
    high = [m for m in materials if m.get("oav") is not None and m["oav"] > 5000]
    unknown = [m for m in materials if m.get("oav") is None]
    lines = []
    if sub:
        lines.append("### Sub-threshold Materials (OAV < 1)")
        lines.append(f"{len(sub)}/{len(materials)} materials below perceptible threshold")
        for m in sub:
            oav = m.get("oav", 0) or 0
            role = _functional_role(m)
            vp = float(m.get("vp_pure_pa") or 0.0)
            act = m.get("active_ul", 0) or 0
            flag = (
                "**FUNCTIONAL_UNDERPERFORMANCE: review dose or assigned role**"
                if _requires_perceptibility(m)
                else "STRUCTURAL_OR_FIXATIVE"
            )
            lines.append(
                f"  - {m['name']}: OAV={oav:.2f} VP={vp:.3f}Pa act={act:.0f}uL role={role} [{flag}]"
            )
    if unknown:
        lines.append("### Unknown OAV (not sub-threshold)")
        for m in unknown:
            model = (m.get("sources") or {}).get("oav_model", "unknown")
            lines.append(f"  - {m['name']}: OAV=UNKNOWN model={model}")
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
        oav = _oav_number(m)
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
    h = " | ".join(["Window", "Time", "T/H/B", "Vapor", "Remain idx", "Leaders"])
    lines.append(f"| {h} |")
    lines.append("|" + "|".join(["-" * 12] * 6) + "|")
    first_ul = ts[0]["state"].get("total_raw_ul", 1) if ts else 1
    for w in ts:
        s = w["state"]
        nd = s.get("note_distribution", {})
        doms = w.get("dominant_oav", [])
        ldrs = ", ".join(f"{d['material'][:12]}({d['oav']:.0f})" for d in doms[:3])
        remaining_index = 100 * s.get("total_raw_ul", 0) / first_ul
        vapor_text = _ppm_text(s.get("total_vapor_ppm"), 2)
        lines.append(
            f"| {w['label'][:12]:12s} | {w['t_seconds']:>6.0f}s | {nd.get('top', 0):>4.1f}/{nd.get('heart', 0):>3.1f}/{nd.get('base', 0):>4.1f}"
            f" | {vapor_text:>12s} | {remaining_index:>6.1f}% | {ldrs:>40s}"
        )
    lines.append("")
    if ts:
        lines.append(
            "Temporal authority: "
            f"{ts[0].get('temporal_authority', 'HEURISTIC_UNCALIBRATED')}; "
            f"model={ts[0].get('temporal_model', 'unspecified')}; "
            "remaining index is not measured evaporation."
        )
        lines.append("")

    # Detail per window
    lines.append("### Per-Window Detail")
    for w in ts:
        s = w["state"]
        nd = s.get("note_distribution", {})
        doms = w.get("dominant_oav", [])
        loss_index = 100 * (1 - s.get("total_raw_ul", 0) / first_ul)
        lines.append("")
        lines.append(
            f"**{w['label'].upper()}** ({w['t_seconds']}s) "
            f"— Uncalibrated loss index:{loss_index:.0f}%"
        )
        lines.append(
            f"  T:{nd.get('top', 0):.1f}% H:{nd.get('heart', 0):.1f}% "
            f"B:{nd.get('base', 0):.1f}%  "
            f"Vapor:{_ppm_text(s.get('total_vapor_ppm'), 2)}"
        )
        if doms:
            lines.append(
                "  Leaders: " + " | ".join(f"{d['material']} OAV {d['oav']:.0f}" for d in doms[:5])
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
    tdesc = " + ".join(f"{m['name']}({oav_label(m.get('oav'))})" for m in top_m[:3])
    hdesc = " + ".join(f"{m['name']}({oav_label(m.get('oav'))})" for m in heart_m[:2]) or "(thin)"
    bdesc = " + ".join(f"{m['name']}({oav_label(m.get('oav'))})" for m in base_m[:5])
    lines.append(f"  Top: {tdesc}")
    lines.append(f"  Heart: {hdesc}")
    lines.append(f"  Base: {bdesc}")
    lines.append("")

    # Opening
    lines.append("### 2. Opening (0-5min)")
    total_vapor = _complete_numeric_sum(mats, "vapor_ppm")
    if top_m:
        lead = top_m[0]
        lines.append(
            f"  {lead['name']} leads the reported top at OAV {_oav_text(lead.get('oav'), 0)} ({oav_label(lead.get('oav'))})."
        )
        for m in top_m[:4]:
            o = m.get("oav")
            vp = float(m.get("vp_pure_pa") or 0.0)
            lines.append(
                f"  - {m['name']} OAV={_oav_text(o, 0)} VP={vp:.1f}Pa ({m.get('family', '?')})"
            )
    lines.append(f"  Total vapor: {_ppm_text(total_vapor, 1)}")
    lines.append("")

    # Heart
    lines.append("### 3. Heart (30min-2hr)")
    if ts and len(ts) >= 3:
        hw = ts[2]
        hm = sort_by_oav(hw["state"].get("materials", []))
        hnd = hw["state"].get("note_distribution", {})
        for m in hm[:4]:
            o = m.get("oav")
            if o is not None and o >= 1:
                lines.append(f"  {m['name']} OAV={o:.0f} ({oav_label(o)})")
        lines.append(
            f"  T:{hnd.get('top', 0):.1f}% H:{hnd.get('heart', 0):.1f}% B:{hnd.get('base', 0):.1f}%"
        )
        lines.append(
            f"  Vapor: {_ppm_text(hw['state'].get('total_vapor_ppm'), 1)}"
        )
    lines.append("")

    # Drydown
    lines.append("### 4. Drydown (2hr-4hr+)")
    if ts and len(ts) >= 5:
        dw = ts[-1]
        dm = sort_by_oav(dw["state"].get("materials", []))
        dnd = dw["state"].get("note_distribution", {})
        lines.append(f"  Base share of active note distribution: {dnd.get('base', 0):.0f}%")
        for m in dm[:6]:
            o = m.get("oav")
            if o is not None and o >= 1:
                lines.append(f"  - {m['name']} OAV={o:.0f}")
        lines.append(
            f"  Vapor: {_ppm_text(dw['state'].get('total_vapor_ppm'), 1)}"
        )
    lines.append("")

    # Sillage
    lines.append("### 5. Sillage & Diffusion")
    carriers = [m for m in mats if m.get("oav") is not None and m["oav"] > 500]
    if carriers:
        cstr = " + ".join(f"{m['name']}({m['oav']:.0f})" for m in carriers[:4])
        lines.append(f"  Primary carriers: {cstr}")
    fams = {}
    for m in mats:
        f = m.get("family", "?")
        oav = _oav_number(m)
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
        last_state = ts[-1]["state"]
        loss_index = 100 * (
            1 - last_state.get("total_raw_ul", 0) / f.get("total_raw_ul", 1)
        )
        persist = last_state.get("note_distribution", {}).get("base", 0)
        lines.append(f"  Uncalibrated loss index: {loss_index:.0f}% over modeled window")
        lines.append(
            "  Vapor: "
            f"{_ppm_text(f.get('total_vapor_ppm'), 1)} > "
            f"{_ppm_text(last_state.get('total_vapor_ppm'), 1)}"
        )
        lines.append(f"  Base @ drydown: {persist:.0f}%")
        lines.append(
            "  Absolute skin life: unavailable; calibrated finite-film, "
            "vehicle, skin-absorption, and sensory data are required"
        )
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
        leader = max(
            (m for m in mats if _oav_number(m) > 0),
            key=_oav_number,
            default=None,
        )
        leader_text = leader["name"] if leader else "Highest-OAV material"
        lines.append(
            f"  Wide OAV contrast: {leader_text} leads at OAV {mx:.0f}; "
            "lower-OAV materials may be masked."
        )
    if (nd.get("heart", 0) or 0) < 10:
        lines.append(
            f"  Thin active-mass heart ({nd.get('heart', 0):.1f}%); top-to-base architecture."
        )
    for label in [
        "OAV >= 10,000",
        "OAV 1,000-10,000",
        "OAV 100-1,000",
        "OAV 10-50",
        "OAV 5-10",
        "OAV 1-5",
        _SUB_THRESHOLD_LABEL,
    ]:
        if label == _SUB_THRESHOLD_LABEL:
            cnt = sum(1 for o in oavs if o < 1)
        else:
            th = next((t for t, lb in OAV_BRACKETS if lb == label), 0)
            next(
                (t for t, lb in OAV_BRACKETS if lb == label and lb != _SUB_THRESHOLD_LABEL and False),
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
                        for t, lb in OAV_BRACKETS
                        if lb == label and OAV_BRACKETS.index((t, lb)) > 0
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
        oav = m.get("oav")
        if oav is not None and oav < 1:
            role = _functional_role(m)
            functional = (
                "FUNCTIONAL_UNDERPERFORMANCE"
                if _requires_perceptibility(m)
                else "STRUCTURAL_OR_FIXATIVE"
            )
            lines.append(f"  SUB: {m['name']} OAV={oav:.2f} role={role} class={functional}")
        elif oav is None:
            model = (m.get("sources") or {}).get("oav_model", "unknown")
            lines.append(f"  UNKNOWN: {m['name']} OAV unavailable ({model})")
    for m in mats:
        if "hedione" in m["name"].lower():
            odt = m.get("odt_air_ppm", 0)
            if odt >= 0.01:
                lines.append(
                    f"  NOTE: Hedione HC ODT={odt * 1000:.1f}ppb (alias collision: pure hedione ODT=0.05ppb, OAV would be 400x higher)"
                )
    # General IFRA check for all restricted materials
    for m in mats:
        limit_pct = m.get("ifra_limit_pct")
        if limit_pct is not None and limit_pct > 0:
            batch_ul = formula.get("formula_state", {}).get("batch_volume_ml", 30) * 1000
            pct = m.get("active_ul", 0) / max(batch_ul, 1) * 100
            if pct > limit_pct * 0.9:
                lines.append(
                    f"  IFRA: {m['name']} at {pct:.2f}% of finished product — near/above Cat4 limit ({limit_pct}%)"
                )
    lines.append("")
    return lines


def build_oav_structural(materials: list[dict], formula: dict) -> list[str]:
    """Structural OAV analysis: tiers, block breakdown, balance critique."""
    lines = ["## Structural OAV Analysis", ""]
    if not materials:
        return lines

    tiers = {
        "OAV >= 1000": [],
        "OAV 100-1000": [],
        "OAV 50-100": [],
        "OAV 10-50": [],
        "OAV 5-10": [],
        "OAV 1-5": [],
        "sub": [],
        "unknown": [],
    }
    total_vapor = _complete_numeric_sum(materials, "vapor_ppm")
    active = sum(float(m.get("active_ul", 0) or 0) for m in materials)
    batch = float(formula.get("formula_state", {}).get("batch_volume_ml", 30))
    bottle_pct = active / max(batch * 1000, 1) * 100

    for m in materials:
        name = m.get("name", "")
        if m.get("oav") is None:
            tiers["unknown"].append((name, None))
            continue
        o = float(m["oav"])
        if o >= 1000:
            tiers["OAV >= 1000"].append((name, o))
        elif o >= 100:
            tiers["OAV 100-1000"].append((name, o))
        elif o >= 50:
            tiers["OAV 50-100"].append((name, o))
        elif o >= 10:
            tiers["OAV 10-50"].append((name, o))
        elif o >= 5:
            tiers["OAV 5-10"].append((name, o))
        elif o >= 1:
            tiers["OAV 1-5"].append((name, o))
        else:
            tiers["sub"].append((name, o))

    total_mats = len(materials)
    perceptible = sum(len(tiers[name]) for name in tiers if name not in {"sub", "unknown"})
    lines.append(
        f"**Vapor:** {_ppm_text(total_vapor, 0)}  |  **Active:** {bottle_pct:.1f}%  |  **Perceptible:** {perceptible}/{total_mats}  |  **Unknown:** {len(tiers['unknown'])}"
    )

    lines.append("")
    lines.append("### OAV Tiers")
    for tier_name in [
        "OAV >= 1000",
        "OAV 100-1000",
        "OAV 50-100",
        "OAV 10-50",
        "OAV 5-10",
        "OAV 1-5",
        "sub",
        "unknown",
    ]:
        items = tiers[tier_name]
        if not items:
            continue
        names = ", ".join(n if o is None else f"{n}({o:.0f})" for n, o in items)
        lines.append(f"  **{tier_name}** ({len(items)}): {names}")

    lines.append("")
    lines.append("### Note-Tier OAV Balance")
    top_oav = sum(float(m.get("oav", 0) or 0) for m in materials if m.get("note") == "top")
    base_oav = sum(float(m.get("oav", 0) or 0) for m in materials if m.get("note") == "base")
    heart_oav = sum(float(m.get("oav", 0) or 0) for m in materials if m.get("note") == "heart")
    total_block = top_oav + base_oav + heart_oav or 1
    lines.append(f"  **Top**    {top_oav:>8.0f} ({top_oav / total_block * 100:.0f}%)")
    lines.append(f"  **Heart**  {heart_oav:>8.0f} ({heart_oav / total_block * 100:.0f}%)")
    lines.append(f"  **Base**   {base_oav:>8.0f} ({base_oav / total_block * 100:.0f}%)")
    maxb = max(top_oav, base_oav, heart_oav)
    positive_blocks = [v for v in [top_oav, base_oav, heart_oav] if v > 0]
    minb = min(positive_blocks) if positive_blocks else 1
    ratio = maxb / minb if maxb > 0 else 0
    lines.append(f"  **Ratio:** {ratio:.0f}:1 between strongest/weakest note tier")

    lines.append("")
    lines.append("### Issues")
    issues = []
    if tiers["sub"]:
        issues.append(
            f"{len(tiers['sub'])} sub-threshold material(s): {', '.join(n for n, _ in tiers['sub'])}"
        )
    if tiers["unknown"]:
        issues.append(
            f"{len(tiers['unknown'])} material(s) have unknown OAV: {', '.join(n for n, _ in tiers['unknown'])}"
        )
    if not tiers["OAV 100-1000"]:
        issues.append("No materials in the OAV 100-1000 range")
    if not tiers["OAV 50-100"]:
        issues.append("No materials in the OAV 50-100 range")
    if top_oav > (heart_oav + base_oav) * 2:
        issues.append(f"Top tier dominates at {top_oav / total_block * 100:.0f}% of total OAV")
    if len(tiers["OAV >= 1000"]) >= 8:
        issues.append(f"{len(tiers['OAV >= 1000'])} materials with OAV >= 1000")
    if issues:
        for issue in issues:
            lines.append(f"  ! {issue}")
    else:
        lines.append("  None detected")
    lines.append("")
    return lines


def main():
    _configure_cli_stdio()
    p = argparse.ArgumentParser()
    p.add_argument("--input", "-i", required=True)
    args = p.parse_args()

    data = load_pipeline(args.input)
    formula = data.get("formulas", [{}])[0]
    mats = formula.get("formula_state", {}).get("materials", [])

    lines: list[str] = []
    lines.extend(build_gate_summary(formula))
    lines.extend(build_reference_deviation(formula))
    lines.extend(build_authority_dimensions(formula, data.get("run_evidence_contract")))
    lines.extend(build_oav_headspace_table(mats))
    lines.extend(build_note_distribution(mats))
    lines.extend(build_class_distribution(mats))
    lines.extend(build_subthreshold(mats))
    lines.extend(build_temporal(formula))
    lines.extend(build_oav_structural(mats, formula))
    lines.extend(build_perfumer(formula))
    print(cli_transport_text("\n".join(lines)))


if __name__ == "__main__":
    main()
