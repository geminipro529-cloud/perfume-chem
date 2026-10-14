"""Opus duel: the Lab composer against 14 reference formulas, brief by brief.

Fast tests (always on) validate ``data/benchmarks/opus_duel_v1.json``. The duel itself is
opt-in (it composes 34 formulas):

- ``OPUS_DUEL=1`` runs it; ``OPUS_DUEL_MODE`` = FAST_SKETCH (default) or DEEP_COMPOSE;
  ``OPUS_DUEL_ONLY`` = comma-separated duel or benchmark ids to run a subset.
- ``OPUS_DUEL_REFERENCES`` is the references root (default ``data/user/opus_duel_references``,
  gitignored). Reference formulas are private and never committed; a ``formulas/`` path
  resolves from the repo root. A missing reference file scores the brief engine-only
  (verdict NO_REFERENCE). An empty references folder counts as absent.
- ``OPUS_DUEL_REPORT=<path>`` writes the JSON (cards, verdicts, closeness, timings) to a
  path outside the repo (the repo is public); the reference card's rows, per-material
  amounts and unreadable-row text are left out.
- ``OPUS_DUEL_WRITE_BASELINE=1`` writes ``data/benchmarks/opus_duel_baseline_<mode>.json``
  (verdicts and scores only: no material names, amounts or closeness); otherwise the run is
  compared to that file when it exists. Writing refuses ``OPUS_DUEL_ONLY`` (a partial
  baseline) and an absent references root (a baseline with no reference scored). A reference the baseline scored must still score when the references root is
  present; with the root absent, reference comparisons are skipped and a line says so.

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
VERDICT_RANK = {"REFERENCE_WINS": 0, "REFERENCE_AHEAD_HELD": 1, "TIE": 2, "BOTH_DISQUALIFIED": 2,
                "NAME_HELD": 2, "ENGINE_AHEAD_HELD": 3, "ENGINE_WINS": 4}
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


def _references_present(root: Path) -> bool:
    """An empty references folder is as good as none (a fresh checkout makes one)."""
    return root.is_dir() and any(root.iterdir())


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
    if not _references_present(root):
        pytest.skip(f"references root {root} is absent or empty")
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
    name = -1.0 if card["name_score"] is None else card["name_score"]  # held: no name number
    return (not card["disqualified"], name, card["craft_score"],
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
        # A set parent whose file is missing makes F3 HOLD (formula_from_markdown).
        ref = formula_from_markdown(ref_path, parent_path=parent)
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
        "engine_floor_holds": _held_floors(eng),
    }
    if ref is not None:
        rec["reference_name_score"] = ref["name_score"]
        rec["reference_craft_score"] = ref["craft_score"]
        rec["reference_floor_holds"] = _held_floors(ref)
    return rec


def _held_floors(card: dict) -> list[str]:
    return sorted(fid for fid, f in card["floors"].items() if f["status"] == "HOLD")


def _compare(baseline: dict, current: dict, references_present: bool = True) -> list[str]:
    """Regressions against the baseline. With the references root absent, reference
    comparisons are skipped; with it present, a reference the baseline scored must score."""
    problems = []
    for bid, base in baseline.items():
        cur = current.get(bid)
        if cur is None:
            problems.append(f"{bid}: in the baseline but missing from the run")
            continue
        if cur["engine_disqualified"] and not base["engine_disqualified"]:
            problems.append(f"{bid}: engine now disqualified ({cur['engine_failing_floors']})")
        was, now = base["engine_name_score"], cur["engine_name_score"]
        if was is not None and (now is None or was - now >= NAME_DROP_LIMIT):
            problems.append(f"{bid}: engine name score {was} -> {'HOLD' if now is None else now}")
        if not references_present:
            continue
        if base["reference_scored"] and not cur["reference_scored"]:
            problems.append(f"{bid}: the baseline scored a reference that is now missing")
            continue
        if base["reference_scored"]:
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


def _report_run(run: dict) -> dict:
    """A run as written to the report. Reference formulas are private: their scores,
    floors and holds stay; their rows, per-material amounts (diagnostics, closeness) and
    unreadable-row text go."""
    ref, near = run["reference"], run["closeness"]
    if ref is not None:
        floors = {}
        for fid, floor in ref["floors"].items():
            floor = dict(floor)
            blocked = floor.pop("blocked_rows", None)
            if blocked:
                floor["detail"] = (f"{len(blocked)} row(s) could not be read "
                                   "(text withheld: private formula)")
            floors[fid] = floor
        holds = [  # a floor's hold repeats its detail
            {**h, "detail": floors[h["source"]]["detail"]} if h.get("source") in floors else h
            for h in ref.get("holds", [])
        ]
        ref = {**{k: v for k, v in ref.items() if k not in {"rows", "diagnostics"}},
               "floors": floors, "holds": holds}
    if near is not None:
        near = {**{k: v for k, v in near.items()
                   if k not in {"basis", "reference_top5_by_active_amount"}},
                "reference_top5_materials": [
                    {k: v for k, v in item.items() if k != "active_amount"}
                    for item in near["reference_top5_by_active_amount"]]}
    return {**run, "reference": ref, "closeness": near}


def _score_text(score: float | None) -> str:
    return "  HOLD" if score is None else f"{score:6.2f}"


def _summary_line(bid: str, run: dict) -> str:
    v, eng, ref = run["verdict"], run["engine"], run["reference"]
    ref_part = (f"ref name={_score_text(ref['name_score'])} craft={ref['craft_score']:6.2f}"
                f"{' DQ' if ref['disqualified'] else ''}" if ref else "ref -")
    return (f"{bid:28s} {v['verdict']:17s} {v['deciding_step']:11s} "
            f"eng name={_score_text(eng['name_score'])} craft={eng['craft_score']:6.2f}"
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
    write_baseline = os.environ.get("OPUS_DUEL_WRITE_BASELINE") == "1"
    if write_baseline and only:
        pytest.fail("OPUS_DUEL_WRITE_BASELINE=1 with OPUS_DUEL_ONLY would write a partial "
                    "baseline: unset one of them")
    report_path = os.environ.get("OPUS_DUEL_REPORT")
    if report_path and Path(report_path).resolve().is_relative_to(ROOT.resolve()):
        pytest.fail(f"OPUS_DUEL_REPORT {report_path} is inside the repo (public): "
                    "write it outside the repo")
    references_present = _references_present(root)
    if write_baseline and not references_present:
        pytest.fail(f"OPUS_DUEL_WRITE_BASELINE=1 with the references root {root} absent would "
                    "write a baseline with no reference scored: set OPUS_DUEL_REFERENCES")
    if not references_present:
        print(f"references root {root} is absent or empty: reference comparisons skipped")
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
    if report_path:
        briefs = {bid: _report_run(run) for bid, run in runs.items()}
        Path(report_path).write_text(json.dumps(
            {"mode": mode, "commit": commit, "references_root": str(root),
             "total_seconds": total_s, "briefs": briefs}, indent=1, sort_keys=True),
            encoding="utf-8")

    current = {bid: _baseline_record(run) for bid, run in runs.items()}
    baseline_path = _baseline_path(mode)
    if write_baseline:
        baseline_path.write_text(json.dumps(
            {"commit": commit, "mode": mode, "briefs": current}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        return
    if not baseline_path.exists():
        return
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["briefs"]
    if only:
        baseline = {k: v for k, v in baseline.items() if k in only}
    problems = _compare(baseline, current, references_present)
    assert not problems, "\n".join(problems)


def test_report_drops_reference_amounts_and_row_text():
    from engine.formulation_intelligence.yardstick import closeness, score_formula

    secret = "line 9: '| Orris Givco 204 | 37 uL |' unread"
    ref = {"name": "private", "batch_volume_ml": 30.0, "row_parse_blockers": [secret], "rows": [
        {"material": m, "amount": a, "unit": "uL", "active_fraction": "1"}
        for m, a in (("Linalool", "123"), ("Hedione", "456"), ("Iso E Super", "789"))]}
    brief = {"id": "t", "family": "floral", "named_notes": [], "excluded_notes": [],
             "family_core_groups": []}
    card = score_formula(ref, brief)
    run = {"engine": card, "reference": card, "closeness": closeness(ref, ref),
           "verdict": {}, "timing": {}}

    report = _report_run(run)
    raw, text = json.dumps([run["reference"], run["closeness"]]), json.dumps(
        [report["reference"], report["closeness"]])

    for leaked in (secret, "Orris Givco", "456", "active_amount", "active_ul"):
        assert leaked in raw and leaked not in text, leaked
    assert report["reference"]["floors"]["F1_owned_stock"]["status"] == "HOLD"
    assert report["engine"] is card  # the engine's own formula is not private


def test_an_empty_references_folder_counts_as_absent(tmp_path: Path) -> None:
    assert _references_present(tmp_path / "missing") is False
    assert _references_present(tmp_path) is False
    (tmp_path / "studio").mkdir()
    assert _references_present(tmp_path) is True


def test_compare_treats_a_newly_held_name_as_a_regression() -> None:
    base = {"verdict": "NO_REFERENCE", "deciding_step": "1_reference",
            "reference_scored": False, "engine_disqualified": False,
            "engine_failing_floors": [], "engine_name_score": 80.0, "engine_craft_score": 70.0}
    held = {**base, "engine_name_score": None}

    assert _compare({"a": base}, {"a": held}) == ["a: engine name score 80.0 -> HOLD"]
    assert _compare({"a": held}, {"a": held}) == []
    assert _compare({"a": held}, {"a": base}) == []


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
    assert _compare({"a": base}, {"a": no_ref}, references_present=False) == []
    assert _compare({"a": base}, {"a": no_ref}) == [
        "a: the baseline scored a reference that is now missing"]
    held = {**base, "verdict": "ENGINE_AHEAD_HELD"}
    assert len(_compare({"a": base}, {"a": held})) == 1
    assert _compare({"a": held}, {"a": {**base, "verdict": "BOTH_DISQUALIFIED"}}) != []
    level = {**base, "verdict": "TIE"}
    assert _compare({"a": level}, {"a": {**base, "verdict": "BOTH_DISQUALIFIED"}}) == []
    assert len(_compare({"a": level}, {"a": {**base, "verdict": "REFERENCE_AHEAD_HELD"}})) == 1
    tie = {**base, "verdict": "TIE"}
    assert len(_compare({"a": tie}, {"a": {**base, "verdict": "REFERENCE_WINS"}})) == 1
