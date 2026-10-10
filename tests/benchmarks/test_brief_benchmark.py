"""Brief-to-formula benchmark: compose 20 plain-language briefs, compare to a frozen baseline.

Metrics are detection diagnostics only (OAV is not intensity or liking; Rule 1), so the
named-note metric is called "detectability share": the share of audible OAV (materials
with OAV >= 1) in a note's window held by materials matching that note.

Unknown-physics metric: the simulator state exposes ``odt_air_ppm`` and ``missing_fields``,
so ``unknown_physics_rows`` counts rows whose material has no air ODT (``odt_air_ppm`` is None
or listed in ``missing_fields``) in the opening frame. ``inaudible_or_unknown_rows`` is not used.

Env vars: BRIEF_BENCH_BASELINE (baseline path override), BRIEF_BENCH_WRITE_BASELINE=1
(write baseline instead of comparing), BRIEF_BENCH_REPORT (path for the full JSON report).
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BRIEFS = ROOT / "data" / "benchmarks" / "briefs_v1.json"
DEFAULT_BASELINE = ROOT / "data" / "benchmarks" / "baseline_8e9cedd.json"
INVENTORY = ROOT / "inventory.txt"
ONE_NOTE_SHARE = 0.60
MAX_DETECTABILITY_DROP = 0.1
MAX_MATERIALS = 60


def _briefs() -> list[dict]:
    return json.loads(BRIEFS.read_text(encoding="utf-8"))["briefs"]


def _effective_voices(oavs: dict[str, float]) -> tuple[float, float]:
    audible = [v for v in oavs.values() if v >= 1]
    tot = sum(audible)
    if not audible:
        return 0.0, 0.0
    ps = [v / tot for v in audible]
    return math.exp(-sum(p * math.log(p) for p in ps)), max(ps)


def _measure(brief: dict) -> dict:
    from engine.formulation_intelligence.formula_design_runtime import design_formula
    from engine.pipeline import simulator

    t0 = time.time()
    result = design_formula(idea=brief["idea"])
    seconds = time.time() - t0
    formula = result.get("optimized_formula") or result.get("initial_formula") or {}
    rows = formula.get("rows", [])
    ing: dict[str, float] = {}
    dil: dict[str, float] = {}
    role: dict[str, str] = {}
    for row in rows:
        if row.get("amount_unit") != "uL":
            continue
        name = row["identity_name"]
        ing[name] = ing.get(name, 0.0) + float(row["amount_decimal"])
        dil[name] = float(row.get("stock_fraction_decimal") or 1)
        role[name] = row.get("role")
    total = sum(ing.values())
    checks = (result.get("composition_checks") or {}).get("checks") or []
    ifra_pass = not any(c.get("check") == "ifra" and c.get("status") == "FAIL" for c in checks)

    frames = simulator.simulate_formula(ing, dil)
    windows: dict[str, dict] = {}
    oav_by_label: dict[str, dict[str, float]] = {}
    max_oav = {n: 0.0 for n in ing}
    unknown = 0
    for i, fr in enumerate(frames):
        mats = fr.state.materials
        oavs = {m.name: float(m.screening_oav or 0.0) for m in mats}
        oav_by_label[fr.label] = oavs
        eff, top = _effective_voices(oavs)
        windows[fr.label] = {"effective_voices": round(eff, 3), "top_oav_share": round(top, 4)}
        for n, v in oavs.items():
            if n in max_oav:
                max_oav[n] = max(max_oav[n], v)
        if i == 0:
            unknown = sum(
                1 for m in mats
                if m.name in ing and (m.odt_air_ppm is None or "odt_air_ppm" in m.missing_fields)
            )

    notes = []
    for note in brief["named_notes"]:
        oavs = oav_by_label.get(note["window"], {})
        audible = {k: v for k, v in oavs.items() if v >= 1}
        tot = sum(audible.values())
        subs = [s.lower() for s in note["materials"]]
        hit = sum(v for k, v in audible.items() if any(s in k.lower() for s in subs))
        notes.append({"name": note["name"], "window": note["window"],
                      "detectability": round(hit / tot, 4) if tot else 0.0})
    return {
        "ifra_pass": ifra_pass,
        "max_volume_share": round(max(ing.values()) / total, 4) if total else 0.0,
        "windows": windows,
        "one_note": sum(1 for w in windows.values() if w["top_oav_share"] >= ONE_NOTE_SHARE) >= 2,
        "named_notes": notes,
        "named_note_detectability": min((n["detectability"] for n in notes), default=1.0),
        "unknown_physics_rows": unknown,
        "silent_character_rows": sum(
            1 for n in ing if role[n] in ("character", "anchor") and max_oav[n] < 1),
        "material_count": len(ing),
        "total_uL": round(total, 3),
        "seconds": round(seconds, 1),
    }


@pytest.fixture(scope="module")
def report() -> dict:
    out = {}
    for b in _briefs():
        out[b["id"]] = _measure(b)
        m = out[b["id"]]
        print(f"{b['id']:32s} ifra={m['ifra_pass']!s:5} maxvol={m['max_volume_share']:.2f} "
              f"onenote={m['one_note']!s:5} detect={m['named_note_detectability']:.2f} "
              f"unk={m['unknown_physics_rows']} silent={m['silent_character_rows']} "
              f"n={m['material_count']} {m['seconds']}s")
    path = os.environ.get("BRIEF_BENCH_REPORT")
    if path:
        Path(path).write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    return out


def test_briefs_file_matches_inventory():
    names = INVENTORY.read_text(encoding="utf-8").lower()
    briefs = _briefs()
    assert len(briefs) == 20 and len({b["id"] for b in briefs}) == 20
    windows = {"opening", "top", "heart", "late_heart", "drydown"}
    for b in briefs:
        for note in b["named_notes"]:
            assert note["window"] in windows, (b["id"], note)
            for s in note["materials"]:
                assert s.lower() in names, (b["id"], s)


def test_against_baseline(report):
    baseline_path = Path(os.environ.get("BRIEF_BENCH_BASELINE") or DEFAULT_BASELINE)
    if os.environ.get("BRIEF_BENCH_WRITE_BASELINE") == "1":
        # seconds is wall-clock and non-deterministic; keep the frozen baseline metrics-only
        data = {k: {m: v for m, v in r.items() if m != "seconds"} for k, r in report.items()}
        baseline_path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    problems = []
    for bid, cur in report.items():
        if cur["material_count"] > MAX_MATERIALS:
            problems.append(f"{bid}: material_count {cur['material_count']} > {MAX_MATERIALS}")
        base = baseline.get(bid)
        if base is None:
            problems.append(f"{bid}: missing from baseline")
            continue
        if base["ifra_pass"] and not cur["ifra_pass"]:
            problems.append(f"{bid}: ifra_pass True -> False")
        drop = base["named_note_detectability"] - cur["named_note_detectability"]
        if drop > MAX_DETECTABILITY_DROP:
            problems.append(f"{bid}: named_note_detectability fell by {drop:.3f}")
    assert not problems, "\n".join(problems)
