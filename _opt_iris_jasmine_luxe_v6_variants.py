"""v6 Iris-Jasmine Luxe Lactée — three variants run against v5 state.

V6a: lower Helional floor to 0 (let it zero out) — test if texture recovers.
V6b: Cashmeran ceiling 300 (instead of 400) — blend rather than overdrive.
V6c: both combined.

All three share the same v5 BASE_ING so optimizer starts from the same baseline.
Winner picked by geo; texture & luxury called out explicitly.
"""

from __future__ import annotations
import copy, json, sys, os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

sys.path.insert(0, ".")

import _opt_iris_jasmine_luxe_lactee as O
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph


def run_variant(label: str, helional_floor: float, cashmeran_ceil: float):
    # Patch HARD_FLOOR / HARD_CEIL in-place
    orig_hf = O.HARD_FLOOR.get("Helional")
    orig_hc = O.HARD_CEIL.get("Cashmeran")
    O.HARD_FLOOR["Helional"] = helional_floor
    O.HARD_CEIL["Cashmeran"] = cashmeran_ceil

    scorer = FormulaScorer(synergy_graph=SynergyGraph(), weights=ObjectiveWeights())
    ing = copy.deepcopy(O.BASE_ING)
    dil = copy.deepcopy(O.BASE_DIL)

    # Also: if helional floor lowered and user wants it to zero, drop starting dose
    # so optimizer can explore the low region more easily.
    if helional_floor == 0.0:
        # Keep starting at 80 so the 'stay' move is available; climber can still
        # drive it to 0 via -80 step.
        pass

    ok, why = O.brief_ok(ing, dil)
    print(f"\n{'='*78}\n  {label}\n{'='*78}")
    print(f"  patches:  Helional floor={helional_floor}  Cashmeran ceil={cashmeran_ceil}")
    print(f"  brief gate: {'OK' if ok else 'FAIL — ' + why}")
    if not ok:
        sys.exit(1)

    geo0, det0 = O.score_formula(ing, dil, scorer)
    print(f"  baseline geo: {geo0:.3f}")

    ing2, dil2, geo, detail, moves = O.climb(ing, dil, scorer, max_passes=5)

    print(f"\n  optimized geo: {geo:.3f}   Δ = {geo - geo0:+.3f}   moves={moves}")
    print(f"  axes baseline → optimized:")
    for a in sorted(O.AXIS_WEIGHTS.keys(), key=lambda x: -O.AXIS_WEIGHTS[x]):
        print(f"    {a:<20s}  {det0[a]:>6.2f} → {detail[a]:>6.2f}  ({detail[a]-det0[a]:+.2f})")

    # Restore
    if orig_hf is None:
        O.HARD_FLOOR.pop("Helional", None)
    else:
        O.HARD_FLOOR["Helional"] = orig_hf
    if orig_hc is None:
        O.HARD_CEIL.pop("Cashmeran", None)
    else:
        O.HARD_CEIL["Cashmeran"] = orig_hc

    return {
        "label": label,
        "helional_floor": helional_floor,
        "cashmeran_ceil": cashmeran_ceil,
        "baseline_geo": geo0,
        "optimized_geo": geo,
        "delta": geo - geo0,
        "moves": moves,
        "axes_baseline": det0,
        "axes_optimized": detail,
        "ing": ing2,
        "dil": dil2,
    }


def main():
    results = []
    results.append(run_variant("V6a: Helional floor → 0 (free it to zero out)",
                               helional_floor=0.0, cashmeran_ceil=400.0))
    results.append(run_variant("V6b: Cashmeran ceil → 300 (blend, don't overdrive)",
                               helional_floor=40.0, cashmeran_ceil=300.0))
    results.append(run_variant("V6c: both (Helional free + Cashmeran ceil 300)",
                               helional_floor=0.0, cashmeran_ceil=300.0))

    print("\n" + "═" * 78)
    print("  SUMMARY  (v4=71.893 · v5=72.496)")
    print("═" * 78)
    print(f"  {'variant':<55s} {'geo':>7s} {'Δ vs v5':>9s} {'texture':>8s} {'luxury':>7s}")
    for r in results:
        d_v5 = r["optimized_geo"] - 72.496
        tex = r["axes_optimized"]["texture"]
        lux = r["axes_optimized"]["luxury"]
        print(f"  {r['label']:<55s} {r['optimized_geo']:>7.3f} {d_v5:>+9.3f} "
              f"{tex:>8.2f} {lux:>7.2f}")

    # Dump final ingredients of the best variant
    best = max(results, key=lambda r: r["optimized_geo"])
    print(f"\n  BEST: {best['label']}  (geo {best['optimized_geo']:.3f})")
    print(f"  final ingredients (µL of as-bottled):")
    for name in best["ing"]:
        base = O.BASE_ING.get(name, 0.0)
        delta = best["ing"][name] - base
        marker = "★" if abs(delta) > 5 else " "
        print(f"    {marker} {name:<32s} {best['ing'][name]:>7.1f}  (base {base:>7.1f}  Δ{delta:+7.1f})")
    total = sum(best["ing"].values())
    print(f"\n  Σ concentrate = {total:.1f} µL")

    with open("_opt_iris_jasmine_luxe_v6_out.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\n  → _opt_iris_jasmine_luxe_v6_out.json")


if __name__ == "__main__":
    main()
