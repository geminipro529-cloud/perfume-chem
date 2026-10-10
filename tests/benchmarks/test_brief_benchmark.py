"""Brief-to-formula benchmark: compose 20 plain-language briefs, compare to a frozen baseline.

Metrics are detection diagnostics only (OAV is not intensity or liking; Rule 1).
- Named-note detectability is a per-note binary detection diagnostic: status "detectable" means
  a matching material has OAV >= 1 in that note's own window (absent / unknown_physics /
  below_threshold otherwise). The audible-OAV share is reported only, not gated. Windows are per
  note, not the spec's single 30-min window.
- Effective voices counts only materials with OAV >= 1 (deliberately narrower than the spec).
- There is no separate chypre brief: the rose chypre brief stands in.
- ``unknown_physics_rows`` counts opening-frame formula rows lacking MW, VP or air ODT.
- ``ifra_status`` is MISSING when no ifra check ran; MISSING is not a pass.

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
DEFAULT_BASELINE = ROOT / "data" / "benchmarks" / "baseline_17a2e9c.json"
INVENTORY = ROOT / "inventory.txt"
ONE_NOTE_SHARE = 0.60
RUNTIME_BUDGET_S = 180
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


def _note_eval(mats, formula_names: set[str], subs: list[str]) -> dict:
    """Detection status (OAV >= 1) and audible-OAV share for one note in one window."""
    subs = [x.lower() for x in subs]

    def match(name: str) -> bool:
        return any(x in name.lower() for x in subs)

    rows = [m for m in mats if m.name in formula_names and match(m.name)]
    if not rows:
        status = "absent"
    elif all(
        m.screening_oav is None or m.odt_air_ppm is None or "odt_air_ppm" in m.missing_fields
        for m in rows
    ):
        status = "unknown_physics"
    elif any(m.screening_oav is not None and m.screening_oav >= 1 for m in rows):
        status = "detectable"
    else:
        status = "below_threshold"
    audible = {m.name: float(m.screening_oav) for m in mats if (m.screening_oav or 0) >= 1}
    tot = sum(audible.values())
    hit = sum(v for k, v in audible.items() if match(k))
    return {"status": status, "share": round(hit / tot, 4) if tot else 0.0}


def _ifra_status(checks: list[dict]) -> str:
    sts = [c.get("status") for c in checks if c.get("check") == "ifra"]
    for level in ("FAIL", "WARN", "PASS"):
        if level in sts:
            return level
    return "MISSING"


def _compare(baseline: dict, report: dict) -> list[str]:
    problems = []
    for bid, cur in report.items():
        if cur["material_count"] > MAX_MATERIALS:
            problems.append(f"{bid}: material_count {cur['material_count']} > {MAX_MATERIALS}")
        base = baseline.get(bid)
        if base is None:
            problems.append(f"{bid}: missing from baseline")
            continue
        if base["ifra_pass"] and not cur["ifra_pass"]:
            problems.append(f"{bid}: ifra_pass True -> False (ifra_status {cur['ifra_status']})")
        now = {n["name"]: n["status"] for n in cur["named_notes"]}
        for n in base["named_notes"]:
            if n["status"] == "detectable" and now.get(n["name"]) != "detectable":
                problems.append(
                    f"{bid}: note {n['name']} status detectable -> {now.get(n['name'], 'missing')}")
    return problems


def _measure(brief: dict) -> dict:
    from engine.formulation_intelligence.formula_design_runtime import design_formula
    from engine.pipeline import simulator

    t0 = time.time()
    result = design_formula(idea=brief["idea"])
    seconds = time.time() - t0
    formula = result.get("optimized_formula") or result.get("initial_formula") or {}
    rows = formula.get("rows", [])
    ing: dict[str, float] = {}
    act: dict[str, float] = {}
    role: dict[str, str] = {}
    for row in rows:
        if row.get("amount_unit") != "uL":
            continue
        name = row["identity_name"]
        amt = float(row["amount_decimal"])
        ing[name] = ing.get(name, 0.0) + amt
        act[name] = act.get(name, 0.0) + amt * float(row.get("stock_fraction_decimal") or 1)
        role[name] = row.get("role")
    dil = {n: (act[n] / ing[n] if ing[n] else 1.0) for n in ing}
    total_active = sum(act.values())
    checks = (result.get("composition_checks") or {}).get("checks") or []
    ifra_status = _ifra_status(checks)
    ifra_pass = ifra_status in ("PASS", "WARN")

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
                if m.name in ing and (
                    m.mw_g_mol is None or m.vp_pure_pa is None or m.odt_air_ppm is None
                    or {"mw", "vp", "odt_air_ppm"} & set(m.missing_fields))
            )

    names = set(ing)
    mats_by_label = {fr.label: fr.state.materials for fr in frames}
    notes = []
    for note in brief["named_notes"]:
        ev = _note_eval(mats_by_label.get(note["window"], []), names, note["materials"])
        notes.append({"name": note["name"], "window": note["window"], **ev})
    return {
        "ifra_pass": ifra_pass,
        "ifra_status": ifra_status,
        "max_active_share": round(max(act.values()) / total_active, 4) if total_active else 0.0,
        "windows": windows,
        "one_note": sum(1 for w in windows.values() if w["top_oav_share"] >= ONE_NOTE_SHARE) >= 2,
        "named_notes": notes,
        "named_notes_detectable": sum(1 for n in notes if n["status"] == "detectable"),
        "unknown_physics_rows": unknown,
        "silent_character_rows": sum(
            1 for n in ing if role[n] in ("character", "anchor") and max_oav[n] < 1),
        "material_count": len(ing),
        "total_uL": round(sum(ing.values()), 3),
        "seconds": round(seconds, 1),
    }


@pytest.fixture(scope="module")
def report() -> dict:
    out = {}
    for b in _briefs():
        out[b["id"]] = _measure(b)
        m = out[b["id"]]
        print(f"{b['id']:32s} ifra={m['ifra_status']:7} maxact={m['max_active_share']:.2f} "
              f"onenote={m['one_note']!s:5} detect={m['named_notes_detectable']} "
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
    problems = _compare(baseline, report)
    assert not problems, "\n".join(problems)


def test_runtime_budget(report):
    total = sum(r["seconds"] for r in report.values())
    assert total <= RUNTIME_BUDGET_S, f"benchmark took {total:.0f}s > {RUNTIME_BUDGET_S}s"
