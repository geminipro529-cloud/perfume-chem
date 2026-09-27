"""Opt-in paired acceptance benchmark; never part of routine validation time.

PowerShell:
    $env:PERFUME_RUN_PERFORMANCE = '1'
    $env:PYTHONHASHSEED = '0'
    .venv/Scripts/python.exe -m pytest tests/test_formulation_performance.py -q -s

Uses synthetic regression compositions, not compounding recommendations.
"""

import hashlib
import json
import os
import platform
import re
import statistics
import sys
from pathlib import Path
from time import perf_counter

import pytest

from engine import name_utils


def _legacy_normalize(name):
    if not name:
        return ""
    n = re.sub(r"\s+", " ", name.strip()).lower()
    return _ALIASES.get(n, n)  # noqa: F821 - executed in name_utils globals


@pytest.mark.skipif(
    os.environ.get("PERFUME_RUN_PERFORMANCE") != "1",
    reason="Explicit opt-in required for timing acceptance",
)
def test_paired_formulation_performance(monkeypatch):
    from engine.optimizer.gate_aware import optimize_global_design
    from engine.optimizer.models import FormulaVector
    from engine.optimizer.scoring import FormulaScorer
    from engine.pipeline.formula_state import build_formula_state
    from engine.pipeline.gates import ReleaseGateConfig, gate_formula
    from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
    from engine.pipeline.release_scoring import compute_unified_release_scores

    root = Path(__file__).resolve().parents[1]
    bound_files = sorted({
        *root.glob("engine/**/*.py"),
        *root.glob("data/materials/*.yaml"),
        *root.glob("data/governance/*.json"),
        *root.glob("data/knowledge_graph/*.json"),
        root / "inventory.txt",
        Path(__file__),
    })

    def input_hashes():
        return {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in bound_files
        }

    snapshot = input_hashes()
    base = {
        "Iso E Super": 30., "Hedione": 25., "Patchouli EO": 10.,
        "Lavender EO": 15., "Bergamot": 10., "Coumarin": 10.,
    }
    # Keep vectors alive: the existing scorer contains identity-based caches.
    vectors = [FormulaVector(ingredients={
        **base, "Iso E Super": 30. + i / 10, "Hedione": 25. - i / 10,
    }) for i in range(40)]

    def scoring():
        scorer = FormulaScorer()
        return [scorer.score(vector) for vector in vectors]

    def evaluate(candidate):
        # A fresh scorer keeps evaluator state isolated across worker threads.
        scores = FormulaScorer().score(FormulaVector(ingredients=candidate))
        return {
            "basis": "experimental_design_proxy",
            "losses": {"fixture_distance": abs(60. - scores["longevity"])},
            "diagnostics": scores,
        }

    def optimization():
        return optimize_global_design(
            base, evaluate=evaluate,
            bounds={name: (max(0., value - 5.), value + 5.) for name, value in base.items()},
            budget=24, seed=17, max_workers=4,
        )

    formula = {
        "number": 1, "name": "Performance regression fixture",
        "ingredients_ul": {
            "Lavender EO": 700., "Hedione": 900., "Coumarin": 300., "Iso E Super": 1500.,
        },
        "dilutions": {"Lavender EO": 1., "Hedione": 1., "Coumarin": .2, "Iso E Super": 1.},
    }

    def validation():
        report = gate_formula(formula, ReleaseGateConfig(audit_enabled=False))
        authority = analyze_oav_authority(OAVAuthorityRequest(
            formula_name=formula["name"], ingredients_ul=formula["ingredients_ul"],
            dilutions=formula["dilutions"], batch_volume_ml=30.,
        ), gate_report=report)
        scores = compute_unified_release_scores(formula, authority, report.as_dict())
        return {"gates": report.as_dict(), "scoring": scores.as_dict()}

    accepted_code = name_utils.normalize_name.__code__
    # Change the function body, not its identity, so existing from-import
    # references in every consumer execute the selected arm. Restore in finally.
    monkeypatch.setattr(name_utils, "re", re, raising=False)
    workloads = {"scoring_40_candidates": scoring, "global_search_49_evaluations": optimization,
                 "all_gates_and_release_scoring": validation}
    results = {}
    try:
        for title, work in workloads.items():
            work()  # warm imports, registry, rule indexes; no startup-time claim
            samples = {"before": [], "after": []}
            expected = None
            for trial in range(12):
                for arm in (("before", "after") if trial % 2 == 0 else ("after", "before")):
                    name_utils.normalize_name.__code__ = (
                        _legacy_normalize.__code__ if arm == "before" else accepted_code
                    )
                    build_formula_state.cache_clear()
                    started = perf_counter()
                    value = work()
                    elapsed = perf_counter() - started
                    payload = json.dumps(value, sort_keys=True, allow_nan=False, default=str)
                    digest = hashlib.sha256(payload.encode()).hexdigest()
                    if expected is None:
                        expected = digest
                    assert digest == expected, (title, trial, arm, "output changed")
                    samples[arm].append(elapsed)
            medians = {arm: statistics.median(values) for arm, values in samples.items()}
            results[title] = {
                "seconds": samples, "median_seconds": medians,
                "reduction_percent": 100 * (1 - medians["after"] / medians["before"]),
                "faster_pairs": sum(a < b for a, b in zip(samples["after"], samples["before"])),
                "identical_output_sha256": expected,
            }
    finally:
        name_utils.normalize_name.__code__ = accepted_code

    assert input_hashes() == snapshot, "Benchmark inputs changed during measurement"
    passed = all(
        results[key]["reduction_percent"] >= 5 and results[key]["faster_pairs"] >= 9
        for key in ("scoring_40_candidates", "global_search_49_evaluations")
    ) and results["all_gates_and_release_scoring"]["reduction_percent"] >= -5
    receipt = {
        "schema": "formulation_performance_acceptance_v1",
        "python": sys.version, "platform": platform.platform(),
        "hash_seed": os.environ.get("PYTHONHASHSEED"), "trials_per_arm": 12,
        "method": "alternating paired order; warmed imports; formula-state cache cleared each arm",
        "scope": "synthetic fixtures; compute only; no physical compounding or sensory claim",
        "acceptance": "at least 5% faster scoring and search in at least 9/12 pairs; validation slowdown <=5%",
        "accepted": passed, "workloads": results, "input_sha256": snapshot,
    }
    target = root / "output/performance_20260915/acceptance.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"accepted": passed, "workloads": results}, indent=2))
    assert passed, "Speed trial failed: remove the candidate change"
