"""
Redo Iris-Jasmine 15→30 mL correctly for top-up use.

Fix from prior run: the unconstrained hill-climb reduced some materials below
their scaled 15 mL × 2 baseline, creating overshoots when topping-up an already
mixed 15 mL batch (worst was Methyl Benzoate +400%).

Correction: constrain hill-climb so every material stays ≥ its 15 mL × 2 floor.
Only additions (and reproportioning via additions of other materials) allowed.
Guarantees a top-up-feasible 30 mL recipe.

Also regenerates the TOPUP markdown afterwards.
"""
from __future__ import annotations

import io, json, os, sys, time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.synergy_graph import SynergyGraph

# Reuse helpers from the main scale script
from _scale_30mL_verify_nonlinear import (
    score_formula, nonlinear_verify, write_md, BATCH_ML,
)

JSON_PATH = Path("_opt_convergence_v2_out.json")
OUT_MD = Path("formulas/collections/Iris_Jasmine_30mL_optimized.md")


def hill_climb_floored(label, ing, dil, scorer, floor, passes=12):
    """Hill-climb at 30 mL with a per-material floor (top-up safety).

    Any trial value < floor[name] is rejected, so the optimized 30 mL recipe
    always dominates the scaled 15 mL × 2 baseline → top-up feasible.
    """
    print(f"\n── HILL-CLIMB (floored, top-up safe) — {label} ──")
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)
    print(f"  start geo = {best_geo:.3f}")

    # Steps: only additions (since reductions would violate the floor anyway for
    # materials currently at floor). Include small negatives too, for materials
    # the hill-climb has already pushed above floor.
    STEPS = (+15, +30, +60, +120, -15, -30, -60)
    improved_any = False

    for p in range(passes):
        t0 = time.time()
        found = False
        for name in list(ing.keys()):
            cur = ing[name]
            fl = floor.get(name, 0.0)
            for step in STEPS:
                new_val = cur + step
                if new_val < fl - 0.5:        # floor constraint (0.5 µL tolerance)
                    continue
                if new_val < 1 or new_val > 2000:
                    continue
                trial = dict(ing)
                trial[name] = new_val
                rev = check_proportional_scaling(trial, dil, BATCH_ML, 15.0)
                if any(c.severity == "error" for c in rev):
                    continue
                geo, detail = score_formula(trial, dil, scorer)
                if geo > best_geo + 0.02:
                    ing = trial
                    best_geo, best_detail = geo, detail
                    print(f"    pass {p+1}: {name} {cur:+.0f}→{new_val:.0f} "
                          f"(Δ{step:+d}, floor={fl:.0f}) → geo {best_geo:.3f}")
                    found = True
                    improved_any = True
                    cur = new_val
                    break
        dt = time.time() - t0
        if not found:
            print(f"    pass {p+1}: no improvement ({dt:.1f}s) — converged")
            break
        print(f"    pass {p+1} took {dt:.1f}s")

    print(f"  final geo = {best_geo:.3f}  (improved={improved_any})")
    return ing, best_detail, best_geo


def main():
    print("Loading _opt_convergence_v2_out.json …")
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    ing15 = {k: float(v) for k, v in data["iris_jasmine"]["ingredients"].items()}
    dil = {k: float(v) for k, v in data["iris_jasmine"]["dilutions"].items()}
    print(f"  15 mL geo = {data['iris_jasmine']['geo']}")
    print(f"  {len(ing15)} materials, {sum(ing15.values()):.0f} µL concentrate @ 15 mL")

    # Scale ×2 → 30 mL (this is also the floor)
    ing30_scaled = {n: v * 2.0 for n, v in ing15.items()}
    floor = dict(ing30_scaled)
    print(f"  scaled to 30 mL: {sum(ing30_scaled.values()):.0f} µL concentrate")

    # Scorer at 30 mL
    sg = SynergyGraph()
    scorer30 = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
    geo_scaled, detail_scaled = score_formula(ing30_scaled, dil, scorer30)
    print(f"  geo @ 30 mL scaled = {geo_scaled:.3f}")

    # Non-linear audit on scaled baseline
    nl = nonlinear_verify("Iris-Jasmine (scaled 30 mL)", ing30_scaled, dil)

    # Floored hill-climb
    ing_final, detail_final, geo_final = hill_climb_floored(
        "Iris-Jasmine", ing30_scaled, dil, scorer30, floor, passes=12)

    # Re-audit if improved
    if geo_final > geo_scaled + 0.02:
        nl = nonlinear_verify("Iris-Jasmine (floored-optimized 30 mL)", ing_final, dil)

    # Verify floor invariant
    violations = [(n, ing_final[n], floor[n])
                  for n in ing_final if ing_final[n] < floor[n] - 0.5]
    if violations:
        print("\n!! FLOOR VIOLATIONS (bug):")
        for n, v, f in violations:
            print(f"    {n}: {v:.1f} < floor {f:.1f}")
        sys.exit(1)
    else:
        print(f"\n✓ All {len(ing_final)} materials ≥ 15 mL × 2 floor — top-up safe")

    # Write
    write_md("Iris-Jasmine", ing_final, dil, detail_final, nl, geo_final, OUT_MD)
    print(f"\n✓ Wrote {OUT_MD}")
    print(f"  15 mL geo        : {data['iris_jasmine']['geo']:.3f}")
    print(f"  30 mL scaled geo : {geo_scaled:.3f}")
    print(f"  30 mL floored geo: {geo_final:.3f}  (Δ {geo_final - geo_scaled:+.3f})")

    # Persist
    out_json = Path("_redo_iris_jasmine_30mL_out.json")
    out_json.write_text(json.dumps({
        "ingredients": ing_final,
        "dilutions": dil,
        "geo": geo_final,
        "geo_scaled": geo_scaled,
        "floor": floor,
    }, indent=2), encoding="utf-8")
    print(f"  wrote {out_json}")


if __name__ == "__main__":
    main()
