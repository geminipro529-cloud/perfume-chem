"""Deep Architecture validation harness (Phase 5 gate).

Uses the labeled ``formulas/classical_study`` corpus with leave-one-out
discrimination (profiles fitted on n-1, tested on 1) plus anti-trivial,
determinism, ablation, and evidence checks.

Exit code 0 only if ALL pass (promotion gate for Phase 6 / default weights).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for candidate in (str(ROOT), str(ROOT / "scripts")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from calibrate_deep_architecture import (  # noqa: E402
    auc_holdout,
    auc_loo,
    fit,
    fit_score,
    load_corpus,
    score_rows,
)

from engine.knowledge.deep_architecture import (  # noqa: E402
    DIMENSIONS,
    DeepArchitectureConfig,
    validate_deep_architecture,
)
from engine.optimizer.models import FormulaVector  # noqa: E402
from engine.optimizer.scoring import FormulaScorer  # noqa: E402

MIN_AUC = 0.70
MAX_COUNT_CORRELATION = 0.90
MIN_SANITY_ACCURACY = 0.70
# Promotion of the dimensions into the default objective needs both holdout
# directions to generalize, not just leave-one-out.
MIN_HOLDOUT_C2N = 0.65
MIN_HOLDOUT_N2C = 0.60
MIN_HOLDOUT_EXTERNAL = 0.60


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if vx == 0 or vy == 0:
        return 0.0
    return cov / (vx * vy)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    evidence = validate_deep_architecture()
    rows = load_corpus()
    score_rows(rows)
    internal = [r for r in rows if r.get("source") != "external"]
    external = [r for r in rows if r.get("source") == "external"]

    # 1. Leave-one-out discrimination AUC (trusted internal corpus)
    auc, pairs, skipped = auc_loo(internal)

    # 1b. Held-out generalization: classical <-> non-classical references
    classical = [r for r in internal if r.get("source") == "classical"]
    nonclassical = [r for r in internal if r.get("source") == "other"]
    holdout_c2n, c2n_pairs, _ = auc_holdout(classical, nonclassical)
    holdout_n2c, n2c_pairs, _ = auc_holdout(nonclassical, classical)
    external_auc, external_pairs, _ = auc_holdout(internal, external)

    # 2. Anti-trivial: per-dimension variance + correlation with material count
    counts = [float(len(r["ingredients"])) for r in internal]
    anti_trivial: dict[str, dict[str, float]] = {}
    collinear, zero_variance = [], []
    for dim in DIMENSIONS:
        values = [r["dims"][dim] for r in internal]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        corr = _pearson(values, counts)
        anti_trivial[dim] = {"variance": round(variance, 3), "count_correlation": round(corr, 3)}
        if variance <= 0.0:
            zero_variance.append(dim)
        if abs(corr) >= MAX_COUNT_CORRELATION:
            collinear.append(dim)

    # 3. Determinism
    first = rows[0]
    fv = FormulaVector(ingredients=dict(first["ingredients"]), dilutions=dict(first["dilutions"]))
    config = DeepArchitectureConfig(enabled=True, profile=first["archetype"])
    run_a = FormulaScorer().score(fv, deep_architecture=config)["deep_architecture"]
    run_b = FormulaScorer().score(fv, deep_architecture=config)["deep_architecture"]
    deterministic = run_a == run_b

    # 4. Ablation: `within` must equal min <= score <= max
    ablation_ok = True
    for entry in run_a["dimensions"].values():
        if bool(entry["within"]) != bool(entry["min"] <= entry["score"] <= entry["max"]):
            ablation_ok = False

    # 5. Reference sanity: share of internal rows that fit their own family best
    profiles = fit(internal)
    own_best = 0
    for row in internal:
        own = fit_score(row["dims"], profiles[row["family"]])
        others = [fit_score(row["dims"], profiles[o]) for o in profiles if o != row["family"]]
        if not others or own >= max(others):
            own_best += 1
    sanity_accuracy = own_best / max(1, len(internal))
    sanity_ok = sanity_accuracy >= MIN_SANITY_ACCURACY

    criteria = {
        "corpus_files": len(internal),
        "external_holdout_files": len(external),
        "discrimination_auc": round(auc, 3),
        "comparison_pairs": pairs,
        "skipped_singleton_folds": skipped,
        "discrimination_pass": auc >= MIN_AUC,
        "anti_trivial_pass": not collinear and not zero_variance,
        "collinear_dimensions": collinear,
        "zero_variance_dimensions": zero_variance,
        "determinism_pass": deterministic,
        "ablation_pass": ablation_ok,
        "reference_sanity_accuracy": round(sanity_accuracy, 3),
        "reference_sanity_pass": sanity_ok,
        "holdout_classical_to_other_auc": round(holdout_c2n, 3),
        "holdout_other_to_classical_auc": round(holdout_n2c, 3),
        "external_holdout_auc": round(external_auc, 3),
        "holdout_pairs": {
            "classical_to_other": c2n_pairs,
            "other_to_classical": n2c_pairs,
            "external": external_pairs,
        },
        "evidence_dimensions": evidence["dimension_refs"],
        "doi_failures": evidence.get("doi_verification", {}).get("failed_dois", []),
    }
    criteria["all_pass"] = all(
        criteria[k] for k in (
            "discrimination_pass", "anti_trivial_pass", "determinism_pass",
            "ablation_pass", "reference_sanity_pass",
        )
    ) and not criteria["doi_failures"]
    criteria["promotion_ready"] = (
        criteria["all_pass"]
        and holdout_c2n >= MIN_HOLDOUT_C2N
        and holdout_n2c >= MIN_HOLDOUT_N2C
        and external_auc >= MIN_HOLDOUT_EXTERNAL
    )

    report = {"criteria": criteria, "anti_trivial": anti_trivial}
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        print(f"corpus: internal {criteria['corpus_files']}, external {criteria['external_holdout_files']}, pairs={pairs}")
        print(f"AUC={criteria['discrimination_auc']} (>= {MIN_AUC}: {criteria['discrimination_pass']})")
        print(f"anti-trivial: {criteria['anti_trivial_pass']} (collinear={collinear}, zero_var={zero_variance})")
        print(f"determinism: {deterministic}; ablation: {ablation_ok}; sanity: {sanity_ok}")
        print(
            "holdout: classical->other "
            f"{criteria['holdout_classical_to_other_auc']} (>= {MIN_HOLDOUT_C2N}), "
            "other->classical "
            f"{criteria['holdout_other_to_classical_auc']} (>= {MIN_HOLDOUT_N2C}), "
            f"external {criteria['external_holdout_auc']} (>= {MIN_HOLDOUT_EXTERNAL})"
        )
        print(f"evidence dims: {evidence['dimension_refs']}")
        print(f"ALL PASS: {criteria['all_pass']}; PROMOTION READY: {criteria['promotion_ready']}")
    return 0 if criteria["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
