"""Redo Photorealistic Iris 15→30 mL with top-up-safe floored hill-climb.

Same fix as _redo_iris_jasmine_30mL.py — constrain hill-climb so every material
stays ≥ 15 mL × 2 floor, eliminating the Heliotropal +14.3% overshoot.
"""
from __future__ import annotations
import io, json, os, sys
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

from engine.optimizer.scoring import FormulaScorer
from engine.synergy_graph import SynergyGraph

from _scale_30mL_verify_nonlinear import (
    score_formula, nonlinear_verify, write_md, BATCH_ML,
)
from _redo_iris_jasmine_30mL import hill_climb_floored

JSON_PATH = Path("_opt_convergence_v2_out.json")
OUT_MD = Path("formulas/collections/Photorealistic_Iris_30mL_optimized.md")


def main():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    ing15 = {k: float(v) for k, v in data["iris"]["ingredients"].items()}
    dil = {k: float(v) for k, v in data["iris"]["dilutions"].items()}
    print(f"Loaded Photorealistic Iris: 15 mL geo = {data['iris']['geo']}")
    print(f"  {len(ing15)} materials, {sum(ing15.values()):.0f} µL concentrate @ 15 mL")

    ing30_scaled = {n: v * 2.0 for n, v in ing15.items()}
    floor = dict(ing30_scaled)
    print(f"  scaled to 30 mL: {sum(ing30_scaled.values()):.0f} µL concentrate")

    sg = SynergyGraph()
    scorer30 = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
    geo_scaled, detail_scaled = score_formula(ing30_scaled, dil, scorer30)
    print(f"  geo @ 30 mL scaled = {geo_scaled:.3f}")

    nl = nonlinear_verify("Photorealistic Iris (scaled 30 mL)", ing30_scaled, dil)

    ing_final, detail_final, geo_final = hill_climb_floored(
        "Photorealistic Iris", ing30_scaled, dil, scorer30, floor, passes=12)

    if geo_final > geo_scaled + 0.02:
        nl = nonlinear_verify("Photorealistic Iris (floored-optimized 30 mL)", ing_final, dil)

    violations = [(n, ing_final[n], floor[n])
                  for n in ing_final if ing_final[n] < floor[n] - 0.5]
    if violations:
        print("\n!! FLOOR VIOLATIONS:")
        for n, v, f in violations:
            print(f"    {n}: {v:.1f} < {f:.1f}")
        sys.exit(1)
    print(f"\n✓ All {len(ing_final)} materials ≥ 15 mL × 2 floor — top-up safe")

    write_md("Photorealistic Iris", ing_final, dil, detail_final, nl, geo_final, OUT_MD)
    print(f"\n✓ Wrote {OUT_MD}")
    print(f"  15 mL geo        : {data['iris']['geo']:.3f}")
    print(f"  30 mL scaled geo : {geo_scaled:.3f}")
    print(f"  30 mL floored geo: {geo_final:.3f}  (Δ {geo_final - geo_scaled:+.3f})")

    Path("_redo_iris_30mL_out.json").write_text(json.dumps({
        "ingredients": ing_final, "dilutions": dil,
        "geo": geo_final, "geo_scaled": geo_scaled, "floor": floor,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
