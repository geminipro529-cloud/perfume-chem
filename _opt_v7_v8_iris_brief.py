"""v7 (perfumer-hand brief-override) + v8 (brief-constrained hill-climb).

Brief: creamy-buttery iris + white floral + powder (Prada Infusion d'Iris /
L'Heure Bleue axis, NOT Iris Silver Mist rooty-earth axis).

v7 = hand-redistribution of v3, same material set, reverses the off-brief
     v6 moves (Carrot Seed dominance, Benzyl Sal dump, powder trims).
v8 = hill-climb from v3 with brief caps/floors: Carrot Seed <=250, Cedarwood
     Virginia <=400, Ambrox <=600, Benzyl Sal >=250, Heliotropal >=50,
     Anisaldehyde >=40, Musk Ketone >=400, Orivone >=350, Delta Deca >=275.
"""
import json
import random
import time

from _opt_iris_reverie_15probes import (
    IRL_V3, IRL_DIL_BASE, BATCH_ML, AXES,
    score_formula, FormulaScorer, SynergyGraph,
    mini_hill_climb, build_bounds,
    SUB_ODT_TRACES, AIMI_CAPPED, IFRA_CAPPED,
)


# --- v7: perfumer-hand brief-override (same material set as v3) -------------
V7_OVERRIDES = {
    # Reverse the off-brief v6 moves
    "Carrot Seed EO":        200.0,   # 600 -> 200 (trace-naturalism, not driver)
    "Cedarwood Virginia EO": 300.0,   # 350 -> 300 (de-emphasize cedar pillar)
    "Ambrox Super":          450.0,   # 550 -> 450 (less crystalline-cold)
    # Restore / amplify powder + cream + cushion
    "Benzyl Salicylate":     350.0,   # 250 -> 350 (cosmetic cushion spine)
    "Hexyl Salicylate":      350.0,   # 300 -> 350 (keep v6 move)
    "Ebanol":               1100.0,   # 900 -> 1100 (keep v6 move)
    "Iso E Super":           200.0,   # 50 -> 200 (keep v6 move, neutral halo)
    "Heliotropal":           100.0,   # 50 -> 100 (cherry-almond powder)
    "Anisaldehyde":           60.0,   # 40 -> 60 (hawthorne-anise powder)
    "Musk Ketone":           600.0,   # 400 -> 600 (talcum echo)
    "Orivone":               500.0,   # 350 -> 500 (buttery iris)
    "Delta Decalactone":     375.0,   # 300 -> 375 (lactonic peach cream)
    "Alpha Ionone":           60.0,   # 25 -> 60 (violet-powder)
    "Beta Ionone":            75.0,   # 40 -> 75 (woody-violet)
    "Ultralia":               40.0,   # 25 -> 40 (ghost iris trace)
}


def build_v7():
    v7 = dict(IRL_V3)
    for n, v in V7_OVERRIDES.items():
        v7[n] = v
    return v7


# --- v8: brief-constrained hill-climb bounds --------------------------------
BRIEF_CEILINGS = {
    "Carrot Seed EO":        250.0,   # was effectively uncapped
    "Cedarwood Virginia EO": 400.0,
    "Ambrox Super":          600.0,
}
BRIEF_FLOORS = {
    "Benzyl Salicylate":     250.0,
    "Hexyl Salicylate":      300.0,
    "Heliotropal":            50.0,
    "Anisaldehyde":           40.0,
    "Musk Ketone":           400.0,
    "Orivone":               350.0,
    "Delta Decalactone":     275.0,
    "Alpha Ionone":           25.0,
    "Beta Ionone":            40.0,
    "Ebanol":                900.0,
    "Ethylene Brassylate":   800.0,
    "Ambrettolide":          700.0,
    "Alpha Irone":           900.0,
}


def build_brief_bounds(ing):
    floor, ceiling = build_bounds(ing)
    for n, fl in BRIEF_FLOORS.items():
        if n in ing:
            floor[n] = max(floor.get(n, 1.0), fl)
    for n, cl in BRIEF_CEILINGS.items():
        if n in ing:
            ceiling[n] = min(ceiling.get(n, float("inf")), cl)
    return floor, ceiling


def axis_line(axis, rows):
    s = f"  {axis:22s}"
    for _, _, det in rows:
        v = det.get(axis, 0.0) if isinstance(det, dict) else det.scores.get(axis, 0.0)
        s += f" {v:10.2f}"
    return s


def print_axis_table(rows):
    print(f"\n  {'axis':22s}" + "".join(f" {lbl[:10]:>10s}" for lbl, _, _ in rows))
    for a in AXES:
        print(axis_line(a, rows))


def main():
    print("=" * 78)
    print("  IRIS REVERIE LACTEE — v7 (perfumer-hand) + v8 (brief-constrained)")
    print("=" * 78)

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    # v3 baseline
    v3_geo, v3_det = score_formula(IRL_V3, IRL_DIL_BASE, scorer)
    print(f"\n  v3 baseline:   geo = {v3_geo:.3f}")

    # v6 (from harvest JSON for comparison)
    try:
        with open("_opt_iris_top3_harvest.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        v6_ing = {k: float(v) for k, v in
                  data["probes"]["CarrotSeed_600to800"]["ing"].items()}
        v6_geo, v6_det = score_formula(v6_ing, IRL_DIL_BASE, scorer)
        print(f"  v6 CarrotSeed: geo = {v6_geo:.3f}  (Δ vs v3 {v6_geo-v3_geo:+.3f})")
    except Exception as e:
        print(f"  (could not load v6: {e})")
        v6_ing, v6_geo, v6_det = None, None, None

    # v7 — perfumer-hand brief-override, same material set as v3
    v7_ing = build_v7()
    v7_geo, v7_det = score_formula(v7_ing, IRL_DIL_BASE, scorer)
    print(f"\n  v7 perfumer:   geo = {v7_geo:.3f}  (Δ vs v3 {v7_geo-v3_geo:+.3f})"
          f"  concentrate = {sum(v7_ing.values()):.0f} uL")

    # v8 — brief-constrained hill-climb from v3
    print(f"\n  running v8 brief-constrained hill-climb from v3 ...")
    t0 = time.time()
    rng = random.Random(2026)
    floor, ceiling = build_brief_bounds(IRL_V3)
    v8_ing, v8_det, v8_geo, moves = mini_hill_climb(
        dict(IRL_V3), IRL_DIL_BASE, scorer, floor, ceiling, rng,
    )
    dt = time.time() - t0
    print(f"  v8 constrained: geo = {v8_geo:.3f}  (Δ vs v3 {v8_geo-v3_geo:+.3f})"
          f"  {moves} moves  {dt:.0f}s"
          f"  concentrate = {sum(v8_ing.values()):.0f} uL")

    # Axis table
    rows = [("v3", v3_geo, v3_det)]
    if v6_det is not None:
        rows.append(("v6 Carrot", v6_geo, v6_det))
    rows.append(("v7 hand", v7_geo, v7_det))
    rows.append(("v8 brief", v8_geo, v8_det))

    print("\n  AXIS COMPARISON")
    print_axis_table(rows)

    # v8 ingredient changes vs v3
    print("\n  v8 changes vs v3 (|Δ| >= 15 uL):")
    diffs = []
    for n in set(IRL_V3) | set(v8_ing):
        d = v8_ing.get(n, 0.0) - IRL_V3.get(n, 0.0)
        if abs(d) >= 15.0:
            diffs.append((n, IRL_V3.get(n, 0.0), v8_ing.get(n, 0.0), d))
    diffs.sort(key=lambda x: -abs(x[3]))
    for n, v0, v1, d in diffs:
        print(f"    {n:28s} {v0:7.1f} -> {v1:7.1f}  D{d:+7.1f}")

    # Save results
    out = {
        "v3_geo": v3_geo,
        "v6_geo": v6_geo,
        "v7": {"geo": v7_geo, "ing": v7_ing,
               "axes": {a: (v7_det.get(a, 0.0) if isinstance(v7_det, dict)
                            else v7_det.scores.get(a, 0.0)) for a in AXES}},
        "v8": {"geo": v8_geo, "ing": v8_ing, "moves": moves,
               "axes": {a: (v8_det.get(a, 0.0) if isinstance(v8_det, dict)
                            else v8_det.scores.get(a, 0.0)) for a in AXES}},
    }
    with open("_opt_v7_v8_iris_brief.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\n  saved: _opt_v7_v8_iris_brief.json")


if __name__ == "__main__":
    main()
