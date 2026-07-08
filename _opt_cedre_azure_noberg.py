"""Optimize Cedre Azure Mass Market — no-bergamot variant + local search + gate check.

No-bergamot replacement:
  -100 uL Bergamot FCF
  + 60 uL Blood Orange Sicilian (luxurious alternative)
  + 30 uL Linalyl Acetate (bergamot's molecular backbone, was 50, now 80)
  + 10 uL Aldehyde C10 1% (orange-peel elegance, "classy French" sparkle)
  
Net: 0 uL drift. 35 materials (+1 from Aldehyde C10).
"""
from __future__ import annotations

import math
import re
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer

# ── No-Bergamot Mass-Market Formula ─────────────────────────────────

# Start from mass-market base, swap bergamot
from _opt_cedre_azure_mass_market import MASS_MARKET_UL as _MM_UL

NOBERG_UL = dict(_MM_UL)

# Remove Bergamot
if "Bergamot FCF Sicilian" in NOBERG_UL:
    del NOBERG_UL["Bergamot FCF Sicilian"]

# Add replacements
NOBERG_UL["Blood Orange Sicilian"] = 60     # luxurious citrus signature
NOBERG_UL["Linalyl Acetate"] = 80           # was 50 (+30, bergamot backbone)
NOBERG_UL["Aldehyde C10"] = 10              # orange-peel radiance (at 1%)

TOTAL_UL = sum(NOBERG_UL.values())
print(f"No-bergamot variant: {len(NOBERG_UL)} materials, {TOTAL_UL:.0f} uL")
print(f"  Removed:  Bergamot FCF -100 uL")
print(f"  Added:    Blood Orange Sicilian +60, Linalyl Acetate +30, Aldehyde C10 1% +10")

# ── Optimizer config ────────────────────────────────────────────────

STEP_OPTIONS = (0.025, 0.050)   # mL  (= 25 uL, 50 uL)
MAX_DRIFT_ML = 0.25
MIN_AMOUNT_ML = 0.0
MIN_NONZERO_ML = 0.015
MAX_ITERATIONS = 8              # reduced to avoid timeout

LOCKED_MATERIALS: set[str] = set()

CUSTOM_WEIGHTS = ObjectiveWeights(
    longevity=1.0,
    sillage=1.0,
    hedonic=1.0,
    skin_performance=1.0,
    perceptual_clarity=0.5,
    luxury=0.2,
    texture=0.2,
    stacking_depth=0.2,
    synergy=0.1,
    photorealism=0.1,
)

SCORER = FormulaScorer(weights=CUSTOM_WEIGHTS, batch_volume_ml=30.0)

AXES = (
    "longevity", "sillage", "hedonic", "skin_performance",
    "perceptual_clarity", "luxury", "texture", "stacking_depth",
    "synergy", "photorealism",
)


def infer_dilution(name: str) -> float:
    explicit = re.search(r"(\d+(?:\.\d+)?)\s*%", name)
    if explicit:
        return float(explicit.group(1)) / 100.0
    overrides = {
        "Aldehyde C11 undecylenic": 0.01,
        "Benzoin Resinoid": 0.50,
        "Ambrofix": 0.30,
        "Methyl Pamplemousse": 0.10,
        "Coumarin": 0.20,
        "Floralozone": 0.10,
        "Scentenal": 0.01,
        "Olibanum Resinoid": 0.10,
        "Ethyl Maltol": 0.10,
        "Aldehyde C10": 0.01,
    }
    return overrides.get(name, 1.0)


def build_fv(ul: dict[str, float]) -> FormulaVector:
    total = sum(ul.values())
    ingredients: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    for mat, v in ul.items():
        if v <= 1e-9:
            continue
        pct = (v / total) * 100.0
        ingredients[mat] = round(pct, 4)
        dil = infer_dilution(mat)
        if dil != 1.0:
            dilutions[mat] = dil
    return FormulaVector(ingredients=ingredients, dilutions=dilutions)


def drift_from_original(current: dict[str, float], original: dict[str, float]) -> float:
    keys = set(current) | set(original)
    return round(sum(abs(current.get(k, 0.0) - original.get(k, 0.0)) for k in keys), 3)


def signature(amounts: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted((n, round(v, 4)) for n, v in amounts.items() if v > 1e-9))


@lru_cache(maxsize=16384)
def _cached_score(sig: tuple[tuple[str, float], ...]) -> dict[str, float]:
    amounts = {n: v for n, v in sig}
    fv = build_fv(amounts)
    scores: dict[str, float] = {}
    for axis in AXES:
        t0 = time.perf_counter()
        scores[axis] = SCORER.score_axis(fv, axis)
        elapsed = time.perf_counter() - t0
        if elapsed > 2.0:
            print(f"  [slow axis] {axis}: {elapsed:.1f}s")
    weights = SCORER.weights.as_dict()
    total_w = sum(weights.get(a, 0.0) for a in AXES) or 1.0
    log_sum = 0.0
    for a in AXES:
        w = weights.get(a, 0.0)
        if w <= 0:
            continue
        log_sum += (w / total_w) * math.log(max(scores[a], 1.0))
    scores["geometric_total"] = round(math.exp(log_sum), 1)
    scores["arithmetic_total"] = round(
        sum(scores[a] * weights.get(a, 0.0) for a in AXES) / total_w, 1
    )
    scores["total"] = scores["geometric_total"]
    return scores


def score_ul(ul: dict[str, float]) -> dict[str, float]:
    return _cached_score(signature(ul))


def candidate_key(scores: dict[str, float], *, drift: float) -> tuple:
    return (
        round(scores["total"], 3),
        round(scores["longevity"], 2),
        round(scores["sillage"], 2),
        round(scores["hedonic"], 2),
        round(scores["skin_performance"], 2),
        round(scores["perceptual_clarity"], 2),
        -round(drift, 3),
    )


@dataclass
class OptimizationResult:
    name: str
    original_scores: dict[str, float]
    optimized_scores: dict[str, float]
    original_ul: dict[str, float]
    optimized_ul: dict[str, float]
    history: list[str]


def optimize(ul: dict[str, float]) -> OptimizationResult:
    original = dict(ul)
    all_mats = sorted(original, key=lambda m: -original[m])

    # Only top 15 materials as givers (reduces search space)
    givers = [m for m in all_mats if original[m] > 60 and m not in LOCKED_MATERIALS][:15]
    receivers = [m for m in all_mats if m not in LOCKED_MATERIALS]

    print(f"  Givers ({len(givers)}): {', '.join(givers[:8])}...")
    print(f"  Receivers ({len(receivers)})")
    est_per_iter = len(givers) * len(receivers) * len(STEP_OPTIONS)
    print(f"  ~{est_per_iter} combos/iter × {MAX_ITERATIONS} iters")

    history: list[str] = []
    current = dict(original)
    current_scores = score_ul(current)

    for it in range(MAX_ITERATIONS):
        t_iter0 = time.perf_counter()
        best_candidate: dict[str, float] | None = None
        best_scores: dict[str, float] | None = None
        best_giver = ""
        best_receiver = ""
        best_delta = 0.0

        drift = drift_from_original(current, original)
        curr_key = candidate_key(current_scores, drift=drift)
        checked = 0

        for giver in givers:
            giver_amt = current.get(giver, 0.0)
            if giver_amt <= MIN_AMOUNT_ML + 1e-9:
                continue
            for receiver in receivers:
                if giver == receiver:
                    continue
                for delta in STEP_OPTIONS:
                    if giver_amt - delta < MIN_AMOUNT_ML - 1e-9:
                        continue
                    cand = dict(current)
                    cand[giver] = round(cand.get(giver, 0.0) - delta, 4)
                    cand[receiver] = round(cand.get(receiver, 0.0) + delta, 4)
                    if 0.0 < cand[giver] < MIN_NONZERO_ML:
                        continue
                    cand = {k: round(v, 4) for k, v in cand.items() if v > 1e-9}
                    cand_drift = drift_from_original(cand, original)
                    if cand_drift > MAX_DRIFT_ML:
                        continue
                    sc = score_ul(cand)
                    checked += 1
                    key = candidate_key(sc, drift=cand_drift)
                    if key <= curr_key:
                        continue
                    if best_scores is None or key > candidate_key(
                        best_scores, drift=drift_from_original(best_candidate or {}, original)
                    ):
                        best_candidate = cand
                        best_scores = sc
                        best_giver = giver
                        best_receiver = receiver
                        best_delta = delta

        t_iter = time.perf_counter() - t_iter0
        print(f"  Iter {it+1}: checked {checked} combos in {t_iter:.1f}s", end="")

        if best_candidate is None or best_scores is None:
            print(" — no improvement found, stopping")
            break

        print(
            f" — {best_giver} -> {best_receiver} {best_delta:.3f}mL, "
            f"total {current_scores['total']:.1f} -> {best_scores['total']:.1f}"
        )
        history.append(
            f"Iter {it+1}: {best_giver} -> {best_receiver} {best_delta:.3f}mL "
            f"(total {current_scores['total']:.1f} -> {best_scores['total']:.1f})"
        )
        current = best_candidate
        current_scores = best_scores

    return OptimizationResult(
        name="Cedre Azure — No-Bergamot Mass Market",
        original_scores=score_ul(original),
        optimized_scores=current_scores,
        original_ul=original,
        optimized_ul=current,
        history=history,
    )


def main() -> None:
    print(f"\n{'='*70}")
    print(f"  CEDRE AZURE — NO-BERGAMOT MASS-MARKET OPTIMIZATION")
    print(f"{'='*70}")

    # Score baseline
    print("\nScoring no-bergamot variant...")
    base_scores = score_ul(NOBERG_UL)
    for a in ("hedonic", "sillage", "longevity", "total"):
        print(f"  {a}: {base_scores[a]:.1f}")

    # Run optimizer
    print("\n--- Running local-search optimizer ---")
    t_start = time.perf_counter()
    result = optimize(NOBERG_UL)
    t_total = time.perf_counter() - t_start
    print(f"\nOptimization completed in {t_total:.1f}s")

    # Score comparison
    print(f"\n{'='*70}")
    print(f"  SCORE COMPARISON")
    print(f"{'='*70}")
    print(f"{'Axis':<24} {'Pre-Opt':>8} {'Optimized':>8} {'Delta':>8}")
    print(f"{'-'*24} {'-'*8} {'-'*8} {'-'*8}")
    for axis in AXES + ("total",):
        pre = base_scores.get(axis, 0)
        post = result.optimized_scores.get(axis, 0)
        d = post - pre
        print(f"{axis:<24} {pre:>8.1f} {post:>8.1f} {d:>+8.1f}")

    # Material deltas
    print(f"\n{'='*70}")
    print(f"  OPTIMIZER MATERIAL SHIFTS (>= 25 uL)")
    print(f"{'='*70}")
    shown = 0
    for mat in sorted(set(result.original_ul) | set(result.optimized_ul),
                       key=lambda m: -max(result.original_ul.get(m, 0), result.optimized_ul.get(m, 0))):
        o_ul = result.original_ul.get(mat, 0)
        n_ul = result.optimized_ul.get(mat, 0)
        d = n_ul - o_ul
        if abs(d) < 25:
            continue
        shown += 1
        print(f"  {mat:<30} {o_ul:>6.0f} -> {n_ul:>6.0f}  ({d:>+5.0f} uL)")
    if shown == 0:
        print("  No significant shifts (all < 25 uL)")

    # Optimizer moves
    if result.history:
        print(f"\n  Moves: {len(result.history)}")
        for move in result.history:
            print(f"    {move}")
    else:
        print("\n  No constrained rebalance improved the score (formula already optimal).")

    # Gate check
    print(f"\n{'='*70}")
    print(f"  GATE CHECK")
    print(f"{'='*70}")

    from engine.pipeline.gates import gate_formula, ReleaseGateConfig

    opt_ul = result.optimized_ul
    gate_dilutions = {
        "Benzoin Resinoid": 0.50,
        "Ambrofix": 0.30,
        "Coumarin": 0.20,
        "Olibanum Resinoid": 0.10,
        "Methyl Pamplemousse": 0.10,
        "Floralozone": 0.10,
        "Aldehyde C11 undecylenic": 0.01,
        "Scentenal": 0.01,
        "Ethyl Maltol": 0.10,
        "Aldehyde C10": 0.01,
    }
    gate_dilutions = {k: v for k, v in gate_dilutions.items() if k in opt_ul}

    formula = {
        "name": "Cedre Azure — No-Bergamot Mass-Market",
        "number": 1,
        "body": (
            "Mass-market blue aromatic woody fougere. "
            "No bergamot — Blood Orange + Linalyl Acetate + Aldehyde C10 "
            "reconstruct bergamot's role with more class/individuality. "
            "Black Pepper EO for Sauvage sparkle. Ambroxan projection engine."
        ),
        "family_archetype": "aromatic_fougere.modern_mineral",
        "ingredients_ul": opt_ul,
        "dilutions": gate_dilutions,
    }

    config = ReleaseGateConfig(
        expected_concentrate_ul=sum(opt_ul.values()),
        batch_volume_ml=30.0,
        brief="auto",
        family_archetype="aromatic_fougere.modern_mineral",
        allow_preblends=True,
        commercial_mode=False,
        audit_enabled=False,
    )

    report = gate_formula(formula, config)
    print(f"\n  Overall: {report.status}")
    fail_count = 0
    for gate in report.gates:
        label = f"[{gate.status}]"
        print(f"  {label:<8} {gate.gate:<42} {gate.detail[:130]}")
        if gate.status == "FAIL":
            fail_count += 1

    print(f"\n  FAILs: {fail_count}")
    if fail_count > 0:
        for gate in report.gates:
            if gate.status == "FAIL":
                print(f"\n  FAIL: {gate.gate}")
                print(f"  {gate.detail}")


if __name__ == "__main__":
    main()
