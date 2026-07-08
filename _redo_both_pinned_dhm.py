"""Redo BOTH Iris and Iris-Jasmine 30 mL with DHM pinned at 15 mL level.

Dihydromyrcenol is waxy-terpenic lavender-adjacent filler, not appropriate for
a photorealistic iris. It's in the 15 mL physical batch and cannot be removed,
but we can refuse to add any more in the 30 mL top-up. Result: DHM concentration
halves (~1.13% → ~0.57%), pushing it below the character-shift threshold.

Strategy:
  - ing30 starting point: DHM kept at 15 mL value (not ×2), everything else ×2
  - Floor: DHM pinned = 15 mL value (cannot go up OR down from here); others ×2
  - Ceiling for DHM: 15 mL value (exact pin)
  - Hill-climb: redirect DHM's forfeited budget into iris/floral materials
"""
from __future__ import annotations
import json, os, sys, time
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

from _scale_30mL_verify_nonlinear import (
    score_formula, nonlinear_verify, write_md, BATCH_ML,
)

JSON_PATH = Path("_opt_convergence_v2_out.json")
PINNED = {"Dihydromyrcenol"}   # kept at 15 mL µL value, not doubled


def hill_climb_pinned(label, ing, dil, scorer, floor, ceiling, passes=12):
    """Hill-climb with per-material floor AND ceiling.

    `floor` = minimum µL allowed for each material.
    `ceiling` = maximum µL allowed (used to PIN pinned materials: floor == ceiling).
    """
    print(f"\n── HILL-CLIMB (pinned-DHM, top-up safe) — {label} ──")
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)
    print(f"  start geo = {best_geo:.3f}")

    STEPS = (+15, +30, +60, +120, +240, -15, -30, -60)
    improved_any = False

    for p in range(passes):
        t0 = time.time()
        found = False
        for name in list(ing.keys()):
            cur = ing[name]
            fl = floor.get(name, 0.0)
            cl = ceiling.get(name, float("inf"))
            # Skip pinned materials entirely (floor == ceiling)
            if fl >= cl - 0.5:
                continue
            for step in STEPS:
                new_val = cur + step
                if new_val < fl - 0.5 or new_val > cl + 0.5:
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
                          f"(Δ{step:+d}, floor={fl:.0f}, ceil={cl:.0f}) → geo {best_geo:.3f}")
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


def process(key, label, out_md, out_json):
    print(f"\n{'█' * 64}\n  {label}\n{'█' * 64}")
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    ing15 = {k: float(v) for k, v in data[key]["ingredients"].items()}
    dil = {k: float(v) for k, v in data[key]["dilutions"].items()}
    print(f"  15 mL geo = {data[key]['geo']}, {len(ing15)} materials, "
          f"{sum(ing15.values()):.0f} µL concentrate")

    # Build 30 mL baseline with DHM pinned at 15 mL value, rest ×2
    ing30 = {}
    floor = {}
    ceiling = {}
    for n, v in ing15.items():
        if n in PINNED:
            ing30[n] = v              # same µL → half concentration in 30 mL
            floor[n] = v
            ceiling[n] = v
            print(f"  PINNED: {n} = {v:.0f} µL (15 mL value, halves concentration)")
        else:
            ing30[n] = v * 2.0
            floor[n] = v * 2.0
            ceiling[n] = float("inf")

    sg = SynergyGraph()
    scorer30 = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
    geo_scaled, _ = score_formula(ing30, dil, scorer30)
    print(f"  geo @ 30 mL (DHM-pinned baseline) = {geo_scaled:.3f}")

    ing_final, detail_final, geo_final = hill_climb_pinned(
        label, ing30, dil, scorer30, floor, ceiling, passes=12)

    # Non-linear verify of final
    nl = nonlinear_verify(f"{label} (DHM-pinned 30 mL)", ing_final, dil)

    # Sanity checks
    violations = [(n, ing_final[n], floor[n], ceiling[n])
                  for n in ing_final
                  if ing_final[n] < floor[n] - 0.5 or ing_final[n] > ceiling[n] + 0.5]
    if violations:
        print("!! VIOLATIONS:", violations)
        sys.exit(1)
    for n in PINNED:
        if n in ing_final and abs(ing_final[n] - ing15[n]) > 0.5:
            print(f"!! {n} NOT PINNED: {ing_final[n]} vs {ing15[n]}"); sys.exit(1)
    print(f"✓ All materials within [floor, ceiling]; DHM pinned at {ing15.get('Dihydromyrcenol', 0):.0f} µL")

    write_md(label, ing_final, dil, detail_final, nl, geo_final, out_md)
    out_json.write_text(json.dumps({
        "ingredients": ing_final, "dilutions": dil, "geo": geo_final,
        "geo_baseline": geo_scaled, "pinned": sorted(PINNED),
    }, indent=2), encoding="utf-8")
    print(f"✓ Wrote {out_md}")
    print(f"  15 mL geo          : {data[key]['geo']:.3f}")
    print(f"  30 mL pinned base  : {geo_scaled:.3f}")
    print(f"  30 mL pinned final : {geo_final:.3f}  (Δ {geo_final - geo_scaled:+.3f})")


if __name__ == "__main__":
    process("iris", "Photorealistic Iris",
            Path("formulas/collections/Photorealistic_Iris_30mL_optimized.md"),
            Path("_redo_iris_30mL_pinned.json"))
    process("iris_jasmine", "Iris-Jasmine",
            Path("formulas/collections/Iris_Jasmine_30mL_optimized.md"),
            Path("_redo_iris_jasmine_30mL_pinned.json"))
