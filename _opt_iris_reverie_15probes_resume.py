"""Resume the 15-probe run starting at probe 5 (indices 4..14).

Probes 1-4 already completed in the prior run. This script skips to
probes 5-15 to avoid redoing them.
"""
from __future__ import annotations
import _opt_iris_reverie_15probes as base

# Replace PROBES with only probes 5..15 (indices 4..14), renumbered
ORIG = base.PROBES
base.PROBES = ORIG[4:]   # probes 5..15

# Patch main's enumerate start so labels read as "Probe 5..15"
import time, random

def main():
    print("═" * 78)
    print("  IRIS RÊVERIE LACTÉE — RESUME probes 5-15 on v3")
    print("═" * 78)

    sg = base.SynergyGraph()
    scorer = base.FormulaScorer(synergy_graph=sg, batch_volume_ml=base.BATCH_ML)

    v3_geo, v3_detail = base.score_formula(base.IRL_V3, base.IRL_DIL_BASE, scorer)
    v3_conc = sum(base.IRL_V3.values())
    print(f"\n  v3 baseline: geo={v3_geo:.3f}, concentrate={v3_conc:.0f} µL "
          f"({v3_conc/(base.BATCH_ML*10):.2f}%)\n")

    results = []
    for idx, (tag, desc, mods_add, dil_add) in enumerate(base.PROBES):
        i = idx + 5   # original probe number
        t0 = time.time()
        seed_ing, seed_dil = base.probe(base.IRL_V3, base.IRL_DIL_BASE,
                                        mods_add, dil_add)
        seed_geo, seed_detail = base.score_formula(seed_ing, seed_dil, scorer)
        floor, ceiling = base.build_bounds(seed_ing)
        rng = random.Random(42 + i)
        final_ing, final_detail, final_geo, moves = base.mini_hill_climb(
            seed_ing, seed_dil, scorer, floor, ceiling, rng)
        dt = time.time() - t0
        dseed = seed_geo - v3_geo
        dfinal = final_geo - v3_geo
        mark = "★" if dfinal > 0.05 else ("·" if dfinal > -0.05 else "✗")
        print(f"  {mark} Probe {i:2d}: {tag:28s}  seed={seed_geo:.3f} "
              f"(Δ{dseed:+.2f})  final={final_geo:.3f} (Δ{dfinal:+.2f})  "
              f"{moves:2d}m {dt:.0f}s", flush=True)
        results.append((i, tag, desc, seed_geo, final_geo, dseed, dfinal,
                        final_detail, final_ing, seed_dil))

    # Include probes 1-4 from prior run (hardcoded from output file)
    prior = [
        (1, "GammaUnde 75→450",    "γ-Undecalactone push (v5 finding)",
         78.597, 78.971, -0.54, -0.17, None, None, None),
        (2, "GammaUnde 75→300",    "γ-Undecalactone moderate push",
         78.772, 79.095, -0.36, -0.04, None, None, None),
        (3, "DeltaDeca 300→500",   "δ-Decalactone creamy-peach lift",
         78.938, 79.232, -0.20, +0.09, None, None, None),
        (4, "EthylLinalool 1050→1300", "Linalool transparency lift",
         78.312, 79.068, -0.83, -0.07, None, None, None),
    ]
    # Note: prior run used v3_geo=79.137; this run may differ.
    # Keep prior Δ as-is; recompute in report if needed.
    all_results = prior + results

    print("\n" + "═" * 78)
    print("  RANKED BY FINAL Δ vs v3 (all 15, prior run deltas for 1-4)")
    print("═" * 78)
    all_results.sort(key=lambda r: -r[6])
    print(f"\n  {'#':>3s} {'tag':30s} {'seed':>8s} {'final':>8s} "
          f"{'Δseed':>8s} {'Δfinal':>8s}")
    for i, tag, desc, sg_, fg, ds, df, _, _, _ in all_results:
        print(f"  {i:3d} {tag:30s} {sg_:8.3f} {fg:8.3f} {ds:+8.2f} {df:+8.2f}")

    # Top 3 axis comparison (only those with detail available)
    print("\n" + "═" * 78)
    print("  TOP 3 (this run) — axis comparison vs v3")
    print("═" * 78)
    detailed = [r for r in all_results if r[7] is not None]
    detailed.sort(key=lambda r: -r[6])
    for i, tag, desc, sg_, fg, ds, df, fdet, fing, _ in detailed[:3]:
        print(f"\n  Probe {i}: {tag}  ({desc})")
        print(f"    geo {v3_geo:.3f} → {fg:.3f}  Δ{df:+.3f}")
        for a in base.AXES:
            b = v3_detail.get(a, 0.0)
            f = fdet.get(a, 0.0)
            d = f - b
            if abs(d) >= 0.1:
                m = "↑" if d > 0 else "↓"
                print(f"      {m} {a:22s} {b:8.2f} → {f:8.2f}  Δ{d:+.2f}")
        diffs = []
        for n in set(base.IRL_V3) | set(fing):
            d = fing.get(n, 0.0) - base.IRL_V3.get(n, 0.0)
            if abs(d) >= 1.0:
                diffs.append((n, base.IRL_V3.get(n, 0.0),
                              fing.get(n, 0.0), d))
        diffs.sort(key=lambda x: -abs(x[3]))
        print("    top ingredient moves:")
        for n, v0, v1, d in diffs[:8]:
            tag2 = " NEW" if v0 == 0 else "    "
            print(f"      {tag2} {n:28s} {v0:7.1f} → {v1:7.1f}  Δ{d:+7.1f}")


if __name__ == "__main__":
    main()
