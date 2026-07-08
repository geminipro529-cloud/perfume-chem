"""Re-run top 3 probes (Javanol, Orivone, CarrotSeed) with full ing-dict JSON dump.

The 15-probe sweep only kept the top-8 ingredient moves printed to stdout.
We need the complete final dict to build an actual v6 candidate and re-verify.

The scorer is deterministic (validated N=8, stdev=0.000) so a single run suffices.
"""

import json
import random
import time

from _opt_iris_reverie_15probes import (
    IRL_V3, IRL_DIL_BASE, BATCH_ML,
    probe, mini_hill_climb, build_bounds,
    score_formula, FormulaScorer, SynergyGraph,
    AXES,
)

TOP3 = [
    ("Javanol_100to200",  "Sandalwood intimate reinforced",
        {"Javanol": 200.0}, {}),
    ("Orivone_350to500",  "Iris-butter warmth",
        {"Orivone": 500.0}, {}),
    ("CarrotSeed_600to800","Carrot seed iris-naturalism lift",
        {"Carrot Seed EO": 800.0}, {}),
]


def main():
    print("═" * 78)
    print("  TOP-3 HARVEST — full ing-dict JSON dump")
    print("═" * 78)

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    v3_geo, v3_detail = score_formula(IRL_V3, IRL_DIL_BASE, scorer)
    print(f"\n  v3 baseline: geo={v3_geo:.3f}")

    out = {
        "v3_baseline": {"geo": v3_geo,
                        "axes": {a: (v3_detail.get(a, 0.0) if isinstance(v3_detail, dict) else v3_detail.scores.get(a, 0.0)) for a in AXES},
                        "ing": dict(IRL_V3)},
        "probes": {},
    }

    # Match seeds from original run (42 + i where i=7,8,9)
    seed_map = {"Javanol_100to200": 42 + 7,
                "Orivone_350to500": 42 + 8,
                "CarrotSeed_600to800": 42 + 9}

    for tag, desc, mods_add, dil_add in TOP3:
        t0 = time.time()
        seed_ing, seed_dil = probe(IRL_V3, IRL_DIL_BASE, mods_add, dil_add)
        seed_geo, _ = score_formula(seed_ing, seed_dil, scorer)
        floor, ceiling = build_bounds(seed_ing)
        rng = random.Random(seed_map[tag])
        final_ing, final_detail, final_geo, moves = mini_hill_climb(
            seed_ing, seed_dil, scorer, floor, ceiling, rng)
        dt = time.time() - t0
        dfinal = final_geo - v3_geo
        print(f"\n  {tag}: seed={seed_geo:.3f} final={final_geo:.3f} "
              f"(Δ{dfinal:+.3f})  {moves}m {dt:.0f}s")

        # Show what moved
        changes = []
        all_keys = set(final_ing) | set(IRL_V3)
        for name in sorted(all_keys):
            v3_amt = IRL_V3.get(name, 0.0)
            new_amt = final_ing.get(name, 0.0)
            if abs(new_amt - v3_amt) >= 0.5:
                changes.append((name, v3_amt, new_amt, new_amt - v3_amt))
        print(f"    {len(changes)} ingredient changes vs v3:")
        for name, a, b, d in sorted(changes, key=lambda x: -abs(x[3])):
            print(f"      {name:30s} {a:8.1f} → {b:8.1f}  Δ{d:+8.1f}")

        out["probes"][tag] = {
            "desc": desc,
            "seed_geo": seed_geo,
            "final_geo": final_geo,
            "delta": dfinal,
            "moves": moves,
            "axes": {a: (final_detail.get(a, 0.0) if isinstance(final_detail, dict) else final_detail.scores.get(a, 0.0)) for a in AXES},
            "ing": dict(final_ing),
            "dil": dict(seed_dil),
            "changes_vs_v3": [{"name": n, "v3": a, "new": b, "delta": d}
                              for n, a, b, d in changes],
        }

    # Save
    with open("_opt_iris_top3_harvest.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Saved → _opt_iris_top3_harvest.json")

    # Rank
    print("\n" + "═" * 78)
    print("  RANKED")
    print("═" * 78)
    ranked = sorted(out["probes"].items(),
                    key=lambda kv: -kv[1]["final_geo"])
    for tag, d in ranked:
        print(f"  {tag:25s} geo={d['final_geo']:.3f} (Δ{d['delta']:+.3f}) "
              f"[{d['moves']} moves, {len(d['changes_vs_v3'])} Δing]")


if __name__ == "__main__":
    main()
