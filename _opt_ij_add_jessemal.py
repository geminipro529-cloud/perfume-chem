"""Iris-Jasmine re-optimization with Jessemal + Dihydrojasmone added.

Jessemal (Jasmonyl / methyl 2-methylpentyl salicylate):
  - Warm-fatty jasmine body — fills the register between Hedione's radiance
    and the salicylate cushion. Acts as a jasmine-salicylate hybrid, adding
    BODY (not brightness). Expect a meaningful dose: 80–180 µL at 30 mL.

Dihydrojasmone:
  - Softer, creamier, rounder than Cis Jasmone — celery-jasmine-floral.
    Pairs with Cis Jasmone as a two-ketone chord (sharp + round). Typical
    dose: 20–60 µL neat at 30 mL.

Only IJ is re-run. Iris is already finalized and unchanged.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
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
from _opt_final_v2 import hill_climb


def main():
    print("█" * 72)
    print("  IRIS-JASMINE  —  30 mL  —  with Jessemal + Dihydrojasmone")
    print("█" * 72)

    # Start from the previous optimized IJ and add the two new materials at
    # reasonable opening doses. Hill-climb will tune.
    prev = json.loads(Path("_opt_final_iris_jasmine.json").read_text(encoding="utf-8"))
    seed = {k: float(v) for k, v in prev["ingredients"].items()}
    dil = {k: float(v) for k, v in prev["dilutions"].items()}

    # New materials — both neat
    seed["Jessemal"] = 120.0        # warm-fatty jasmine body
    seed["Dihydrojasmone"] = 30.0   # creamy/round jasmine ketone (pairs with Cis Jasmone)

    print(f"  Seed now has {len(seed)} materials "
          f"({sum(seed.values()):.0f} µL concentrate)")
    print(f"  New: Jessemal 120 µL (warm-fatty jasmine body)")
    print(f"  New: Dihydrojasmone 30 µL (creamy jasmine ketone, pairs w/ Cis Jasmone)")

    ANCHORS = {"Hedione", "Alpha Irone", "Myristic Acid", "Ethylene Brassylate",
               "Benzyl Salicylate", "IPM"}
    floor = {n: (max(1.0, v * 0.5) if n in ANCHORS else 1.0) for n, v in seed.items()}
    ceiling = {n: float("inf") for n in seed}

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
    seed_geo, _ = score_formula(seed, dil, scorer)
    print(f"  Seed geo = {seed_geo:.3f}  (prior converged IJ was {prev['geo']:.3f})")

    ing, det, geo = hill_climb("IJ + Jessemal/DHJ (pass A)", seed, dil, scorer,
                               floor, ceiling, passes=18)
    print(f"\n── RE-SEED pass B ──")
    ing, det, geo = hill_climb("IJ + Jessemal/DHJ (pass B)", ing, dil, scorer,
                               floor, ceiling, passes=12)
    print(f"\n── PASS C fine polish ──")
    ing, det, geo = hill_climb("IJ + Jessemal/DHJ (pass C)", ing, dil, scorer,
                               floor, ceiling, passes=8)

    # Report what happened to the two new materials
    print(f"\n  Jessemal final:      {ing.get('Jessemal', 0):.0f} µL "
          f"(seeded 120)")
    print(f"  Dihydrojasmone final: {ing.get('Dihydrojasmone', 0):.0f} µL "
          f"(seeded 30)")
    print(f"  Cis Jasmone final:   {ing.get('Cis Jasmone', 0):.0f} µL")

    # IFRA-sensitive check
    TOTAL_ML = 30.0
    ACA_pct = ing.get("Amyl Cinnamic Aldehyde", 0) / (TOTAL_ML * 1000) * 100
    print(f"  ACA:     {ACA_pct:.3f}% of final")

    nl = nonlinear_verify("Iris-Jasmine — 30 mL (with Jessemal+DHJ)", ing, dil)

    md = Path("formulas/collections/Iris_Jasmine_30mL_optimized.md")
    write_md("Iris-Jasmine", ing, dil, det, nl, geo, md)
    out = Path("_opt_final_iris_jasmine.json")
    out.write_text(json.dumps({
        "ingredients": ing, "dilutions": dil, "geo": geo, "geo_seed": seed_geo,
        "geo_prior_no_jessemal": prev["geo"],
        "nonlinear": nl,
        "notes": "Jasmine heart built from chemistry; Jessemal + Dihydrojasmone added.",
    }, indent=2), encoding="utf-8")

    print(f"\n  Summary")
    print(f"    Prior IJ (no Jess/DHJ) : {prev['geo']:.3f}")
    print(f"    Seed + Jess/DHJ        : {seed_geo:.3f}")
    print(f"    Optimized              : {geo:.3f}  (Δ vs prior {geo - prev['geo']:+.3f})")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"\n✓ {time.time() - t0:.1f}s")
