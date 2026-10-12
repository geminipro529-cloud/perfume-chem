"""Opus duel: the Lab composer against 14 reference formulas, brief by brief.

Fast tests (always on) validate ``data/benchmarks/opus_duel_v1.json``. The duel itself is
opt-in (it composes 34 formulas):

- ``OPUS_DUEL=1`` runs it; ``OPUS_DUEL_MODE`` = FAST_SKETCH (default) or DEEP_COMPOSE;
  ``OPUS_DUEL_ONLY`` = comma-separated duel or benchmark ids to run a subset.
- ``OPUS_DUEL_REFERENCES`` is the references root (default ``data/user/opus_duel_references``,
  gitignored). Reference formulas are private and never committed; a ``formulas/`` path
  resolves from the repo root. A missing reference file scores the brief engine-only
  (verdict NO_REFERENCE).
- ``OPUS_DUEL_REPORT=<path>`` writes the full JSON (cards, verdicts, closeness, timings).
- ``OPUS_DUEL_WRITE_BASELINE=1`` writes ``data/benchmarks/opus_duel_baseline_<mode>.json``
  (verdicts and scores only: no material names, amounts or closeness); otherwise the run is
  compared to that file when it exists.

DEEP_COMPOSE returns up to three variants in ``result["design_variants"][i]["formula"]``;
each is scored and the best kept: not disqualified, then name score, then craft, then liking.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "benchmarks" / "opus_duel_v1.json"
BRIEFS = ROOT / "data" / "benchmarks" / "briefs_v1.json"
DEFAULT_REFERENCES = ROOT / "data" / "user" / "opus_duel_references"
WINDOWS = {"opening", "top", "heart", "late_heart", "drydown"}
MODES = {"FAST_SKETCH", "DEEP_COMPOSE"}
BENCH_CONCENTRATE_UL = 6000
NAME_DROP_LIMIT = 5.0
# Verdict rank from the engine's side: a move to a lower rank is a regression.
VERDICT_RANK = {"REFERENCE_WINS": 0, "TIE": 1, "ENGINE_WINS": 2}
DUEL_KEYS = {"id", "name", "idea", "idea_source", "family", "family_source", "named_notes",
             "family_core_groups", "precious_caps", "reference", "concentrate_ul"}
DUEL_OPTIONAL = {"excluded_notes", "family_note"}
EXTRA_KEYS = {"family", "family_source", "family_core_groups"}
EXTRA_OPTIONAL = {"excluded_notes", "family_note"}


def _data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _bench_briefs() -> list[dict]:
    return json.loads(BRIEFS.read_text(encoding="utf-8"))["briefs"]


def _family_headings() -> set[str]:
    text = (ROOT / "docs" / "fragrance_families_reference.md").read_text(encoding="utf-8")
    out = set()
    for line in text.splitlines():
        if line.startswith("## ") and ". " in line:
            num, _, rest = line[3:].partition(". ")
            if num.isdigit():
                out.add(rest.strip())
    return out


def _references_root() -> Path:
    return Path(os.environ.get("OPUS_DUEL_REFERENCES") or DEFAULT_REFERENCES)


def _resolve(rel: str | None, root: Path) -> Path | None:
    if not rel:
        return None
    return ROOT / rel if rel.startswith("formulas/") else root / rel


# ── Fast tests ──────────────────────────────────────────────────────────────


def _check_notes(where: str, notes: list, windows: bool) -> None:
    for note in notes:
        expected = {"name", "window", "materials"} if windows else {"name", "materials"}
        assert set(note) == expected, (where, note)
        assert isinstance(note["name"], str) and note["name"], (where, note)
        if windows:
            assert note["window"] in WINDOWS, (where, note)
        assert note["materials"] and all(
            isinstance(s, str) and s and s == s.lower() for s in note["materials"]
        ), (where, note)


def _check_family(where: str, entry: dict, headings: set[str]) -> None:
    assert entry["family"] in headings, (where, entry["family"])
    path, _, lines = entry["family_source"].partition(":")
    assert path == "docs/fragrance_families_reference.md" and lines, (where, entry)
    groups = entry["family_core_groups"]
    assert isinstance(groups, list), where
    if not groups:
        assert entry.get("family_note"), (where, "empty family groups need a family_note")
    for group in groups:
        assert group and all(isinstance(s, str) and s and s == s.lower() for s in group), (
            where, group)


def test_data_file_shape():
    data = _data()
    assert set(data) == {"version", "duel", "benchmark_extras"} and data["version"] == 1
    duel = data["duel"]
    assert len(duel) == 14 and len({e["id"] for e in duel}) == 14
    headings = _family_headings()
    for e in duel:
        keys = set(e)
        assert DUEL_KEYS <= keys <= DUEL_KEYS | DUEL_OPTIONAL, (e["id"], keys ^ DUEL_KEYS)
        assert len(e["idea"].split()) <= 30, e["id"]
        assert e["idea_source"], e["id"]
        assert 2 <= len(e["named_notes"]) <= 4, e["id"]
        _check_notes(e["id"], e["named_notes"], windows=True)
        _check_notes(e["id"], e.get("excluded_notes", []), windows=False)
        _check_family(e["id"], e, headings)
        assert all(
            k == k.lower() and isinstance(v, (int, float)) and v > 0
            for k, v in e["precious_caps"].items()
        ), e["id"]
        ref = e["reference"]
        assert set(ref) == {"path", "parent", "parent_note"}, e["id"]
        assert ref["path"].endswith(".md") and ref["parent_note"], e["id"]
        assert ref["parent"] is None or ref["parent"].endswith(".md"), e["id"]
        assert isinstance(e["concentrate_ul"], int) and 1000 <= e["concentrate_ul"] <= 30000
    bench_ids = {b["id"] for b in _bench_briefs()}
    extras = data["benchmark_extras"]
    assert set(extras) == bench_ids
    for bid, x in extras.items():
        assert EXTRA_KEYS <= set(x) <= EXTRA_KEYS | EXTRA_OPTIONAL, (bid, set(x))
        _check_family(bid, x, headings)
        _check_notes(bid, x.get("excluded_notes", []), windows=False)
    for bid in ("dark-oud-rose-no-vanilla", "woody-floral-no-musk", "citrus-no-lavender"):
        assert extras[bid].get("excluded_notes"), bid


def test_every_substring_group_matches_owned_stock():
    from engine.inventory_parser import parse_current_inventory

    owned = [
        name.lower()
        for r in parse_current_inventory(unique=False, include_unavailable=True)
        if r.status == "owned"
        for name in (r.name, r.identity_name or "")
        if name
    ]

    def hits(subs: list[str]) -> bool:
        return any(s in name for s in subs for name in owned)

    data = _data()
    entries = [(e["id"], e) for e in data["duel"]] + list(data["benchmark_extras"].items())
    missing = []
    for eid, e in entries:
        for note in e.get("named_notes", []) + e.get("excluded_notes", []):
            if not hits(note["materials"]):
                missing.append(f"{eid}: note {note['name']} {note['materials']}")
        for group in e["family_core_groups"]:
            if not hits(group):
                missing.append(f"{eid}: family group {group}")
    assert not missing, "\n".join(missing)


def test_reference_paths_resolve():
    root = _references_root()
    paths = [p for e in _data()["duel"] for p in (e["reference"]["path"], e["reference"]["parent"])
             if p]
    repo_paths = [p for p in paths if p.startswith("formulas/")]
    for p in repo_paths:  # public references live in the repo and must always resolve
        assert (ROOT / p).is_file(), p
    if not root.is_dir():
        pytest.skip(f"references root {root} is not present")
    missing = [p for p in paths if not _resolve(p, root).is_file()]
    assert not missing, f"missing under {root}: {missing}"


# ── Duel run (opt-in) ───────────────────────────────────────────────────────


def _mode() -> str:
    mode = os.environ.get("OPUS_DUEL_MODE") or "FAST_SKETCH"
    assert mode in MODES, f"OPUS_DUEL_MODE must be one of {sorted(MODES)}"
    return mode


def _baseline_path(mode: str) -> Path:
    return ROOT / "data" / "benchmarks" / f"opus_duel_baseline_{mode.lower()}.json"


def _rank_key(card: dict) -> tuple:
    valence = card["liking"].get("valence")
    return (not card["disqualified"], card["name_score"], card["craft_score"],
            -2.0 if valence is None else float(valence))


def _compose_and_score(brief: dict, name: str, concentrate_ul: int, mode: str) -> dict:
    from engine.formulation_intelligence.formula_design_runtime import design_formula
    from engine.formulation_intelligence.yardstick import formula_from_composer, score_formula

    t0 = time.time()
    result = design_formula(idea=brief["idea"], formula_name=name,
                            liquid_concentrate_ul_decimal=str(concentrate_ul), design_mode=mode)
    compose_s = time.time() - t0
    candidates = [formula_from_composer(result)]
    if mode == "DEEP_COMPOSE":
        variants = [v for v in result.get("design_variants") or [] if v.get("formula")]
        if variants:
            candidates = [formula_from_composer({"optimized_formula": v["formula"]})
                          for v in variants]
    cards = [score_formula(f, brief) for f in candidates]
    best = max(range(len(cards)), key=lambda i: _rank_key(cards[i]))
    return {"formula": candidates[best], "card": cards[best], "variant_index": best,
            "variants_scored": len(cards), "compose_seconds": round(compose_s, 1),
            "seconds": round(time.time() - t0, 1)}


def _run_duel_entry(entry: dict, mode: str, root: Path) -> dict:
    from engine.formulation_intelligence.yardstick import (
        closeness,
        duel_verdict,
        formula_from_markdown,
        score_formula,
    )

    engine = _compose_and_score(entry, entry["name"], entry["concentrate_ul"], mode)
    ref_path = _resolve(entry["reference"]["path"], root)
    parent = _resolve(entry["reference"]["parent"], root)
    ref_card = near = None
    if ref_path is not None and ref_path.is_file():
        ref = formula_from_markdown(ref_path,
                                    parent_path=parent if parent and parent.is_file() else None)
        ref_card = score_formula(ref, entry)
        near = closeness(engine["formula"], ref)
    return {"kind": "duel", "engine": engine["card"], "reference": ref_card,
            "verdict": duel_verdict(engine["card"], ref_card), "closeness": near,
            "variant_index": engine["variant_index"],
            "variants_scored": engine["variants_scored"],
            "timing": {"compose_seconds": engine["compose_seconds"],
                       "engine_seconds": engine["seconds"]}}


def _run_bench_entry(brief: dict, mode: str) -> dict:
    from engine.formulation_intelligence.yardstick import duel_verdict

    engine = _compose_and_score(brief, None, BENCH_CONCENTRATE_UL, mode)
    return {"kind": "benchmark", "engine": engine["card"], "reference": None,
            "verdict": duel_verdict(engine["card"], None), "closeness": None,
            "variant_index": engine["variant_index"],
            "variants_scored": engine["variants_scored"],
            "timing": {"compose_seconds": engine["compose_seconds"],
                       "engine_seconds": engine["seconds"]}}


def _failing_floors(card: dict) -> list[str]:
    return sorted(fid for fid, f in card["floors"].items() if f["status"] == "FAIL")


def _baseline_record(run: dict) -> dict:
    """Verdicts and scores only: no material names, amounts or closeness (privacy rule)."""
    eng, ref = run["engine"], run["reference"]
    rec = {
        "verdict": run["verdict"]["verdict"],
        "deciding_step": run["verdict"]["deciding_step"],
        "reference_scored": ref is not None,
        "engine_disqualified": eng["disqualified"],
        "engine_failing_floors": _failing_floors(eng),
        "engine_name_score": eng["name_score"],
        "engine_craft_score": eng["craft_score"],
    }
    if ref is not None:
        rec["reference_name_score"] = ref["name_score"]
        rec["reference_craft_score"] = ref["craft_score"]
    return rec


def _compare(baseline: dict, current: dict) -> list[str]:
    problems = []
    for bid, base in baseline.items():
        cur = current.get(bid)
        if cur is None:
            problems.append(f"{bid}: in the baseline but missing from the run")
            continue
        if cur["engine_disqualified"] and not base["engine_disqualified"]:
            problems.append(f"{bid}: engine now disqualified ({cur['engine_failing_floors']})")
        drop = base["engine_name_score"] - cur["engine_name_score"]
        if drop >= NAME_DROP_LIMIT:
            problems.append(f"{bid}: engine name score {base['engine_name_score']} -> "
                            f"{cur['engine_name_score']}")
        if base["reference_scored"] and cur["reference_scored"]:
            b, c = VERDICT_RANK.get(base["verdict"]), VERDICT_RANK.get(cur["verdict"])
            if b is not None and c is not None and c < b:
                problems.append(f"{bid}: verdict {base['verdict']} -> {cur['verdict']}")
    return problems


def _git_commit() -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, env=env, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _summary_line(bid: str, run: dict) -> str:
    v, eng, ref = run["verdict"], run["engine"], run["reference"]
    ref_part = (f"ref name={ref['name_score']:6.2f} craft={ref['craft_score']:6.2f}"
                f"{' DQ' if ref['disqualified'] else ''}" if ref else "ref -")
    return (f"{bid:28s} {v['verdict']:17s} {v['deciding_step']:11s} "
            f"eng name={eng['name_score']:6.2f} craft={eng['craft_score']:6.2f}"
            f"{' DQ' + str(_failing_floors(eng)) if eng['disqualified'] else ''} | {ref_part} "
            f"{run['timing']['engine_seconds']}s")


@pytest.mark.skipif(os.environ.get("OPUS_DUEL") != "1", reason="opt-in: set OPUS_DUEL=1")
def test_opus_duel():
    mode = _mode()
    root = _references_root()
    only = {s.strip() for s in (os.environ.get("OPUS_DUEL_ONLY") or "").split(",") if s.strip()}
    data = _data()
    known = {e["id"] for e in data["duel"]} | set(data["benchmark_extras"])
    assert only <= known, f"unknown ids in OPUS_DUEL_ONLY: {sorted(only - known)}"
    runs: dict[str, dict] = {}
    t0 = time.time()
    for entry in data["duel"]:
        if not only or entry["id"] in only:
            runs[entry["id"]] = _run_duel_entry(entry, mode, root)
            print(_summary_line(entry["id"], runs[entry["id"]]))
    for brief in _bench_briefs():
        if not only or brief["id"] in only:
            merged = {**brief, **data["benchmark_extras"][brief["id"]]}
            runs[brief["id"]] = _run_bench_entry(merged, mode)
            print(_summary_line(brief["id"], runs[brief["id"]]))
    total_s = round(time.time() - t0, 1)
    print(f"opus duel {mode}: {len(runs)} briefs in {total_s}s")

    commit = _git_commit()
    report_path = os.environ.get("OPUS_DUEL_REPORT")
    if report_path:
        Path(report_path).write_text(json.dumps(
            {"mode": mode, "commit": commit, "references_root": str(root),
             "total_seconds": total_s, "briefs": runs}, indent=1, sort_keys=True),
            encoding="utf-8")

    current = {bid: _baseline_record(run) for bid, run in runs.items()}
    baseline_path = _baseline_path(mode)
    if os.environ.get("OPUS_DUEL_WRITE_BASELINE") == "1":
        baseline_path.write_text(json.dumps(
            {"commit": commit, "mode": mode, "briefs": current}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        return
    if not baseline_path.exists():
        return
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["briefs"]
    if only:
        baseline = {k: v for k, v in baseline.items() if k in only}
    problems = _compare(baseline, current)
    assert not problems, "\n".join(problems)


def test_compare_flags_regressions():
    base = {"verdict": "ENGINE_WINS", "deciding_step": "3_name", "reference_scored": True,
            "engine_disqualified": False, "engine_failing_floors": [],
            "engine_name_score": 80.0, "engine_craft_score": 70.0}
    assert _compare({"a": base}, {"a": dict(base)}) == []
    assert _compare({"a": base}, {}) == ["a: in the baseline but missing from the run"]
    assert len(_compare({"a": base}, {"a": {**base, "verdict": "TIE"}})) == 1
    assert len(_compare({"a": base}, {"a": {**base, "engine_name_score": 75.0}})) == 1
    assert _compare({"a": base}, {"a": {**base, "engine_name_score": 75.01}}) == []
    dq = {**base, "engine_disqualified": True, "engine_failing_floors": ["F5_pours"]}
    assert len(_compare({"a": base}, {"a": dq})) == 1
    no_ref = {**base, "reference_scored": False, "verdict": "NO_REFERENCE"}
    assert _compare({"a": base}, {"a": no_ref}) == []
    tie = {**base, "verdict": "TIE"}
    assert len(_compare({"a": tie}, {"a": {**base, "verdict": "REFERENCE_WINS"}})) == 1
