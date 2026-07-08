"""Re-run the 30 mL optimizer against the FIRST-EDITION Photorealistic Iris
(v4_Final / v6-labelled 38-material master) — 10 independent stochastic runs.

Stochasticity source:
  - random.shuffle(keys) per pass (different ingredient-scan order each run)
  - random.shuffle(steps) per ingredient (different step-probe order)

All runs share:
  - Floor = starting µL (cannot subtract — matches "already in bottle" semantics)
  - Ceiling = +∞ except DHM (pinned at starting value — waxy-terpenic filler)
  - OAV guard: 30→15 mL proportional scaling must not throw errors
  - Passes: 20 broad + 12 fine per run

Prints per-run axis detail + final summary table.
"""
from __future__ import annotations

import io, os, random, sys, time
from pathlib import Path
from statistics import mean, median, stdev

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula, BATCH_ML

# ═══════════════════════════════════════════════════════════════════════════════
# FIRST EDITION — Photorealistic_Iris_v4_Final.md (38 materials, 30 mL target)
# ═══════════════════════════════════════════════════════════════════════════════
FIRST_EDITION_ING = {
    # TOP
    "Bergamot FCF oil Sicilian": 200.0,
    "Grapefruit FCF":             60.0,
    "Leafovert":                   8.0,
    "Ethyl Linalool":            140.0,
    "Dihydromyrcenol":           100.0,
    "Allyl Amyl Glycolate":       20.0,
    "Scentenal":                  24.0,
    # HEART
    "Alpha Irone":               500.0,
    "Myristic Acid":            1500.0,
    "Alpha Ionone":               80.0,
    "Beta Ionone":                50.0,
    "Allyl Ionone":               30.0,
    "Alpha Isomethyl Ionone":    180.0,
    "Dihydro Beta Ionone":        40.0,
    "Irotyl":                     60.0,
    "Orivone":                   120.0,
    "Hedione":                   650.0,
    "Hedione HC":                 80.0,
    "Cis Jasmone":                20.0,
    "Carrot Seed EO":             60.0,
    "Ultralia":                   80.0,
    "Cyclamen Aldehyde":          30.0,
    "Farnesol":                   10.0,
    "Violet Fleuressence":        30.0,
    # BASE
    "Heliotropal":                80.0,
    "Musk Ketone":               200.0,
    "Koavone":                   200.0,
    "Azarbre":                   100.0,
    "Ebanol":                    230.0,
    "Iso E Super":               280.0,
    "Habanolide":                550.0,
    "Ethylene Brassylate":       380.0,
    "Exaltolide":                300.0,
    "Ambrettolide":              250.0,
    "Romandolide":               120.0,
    "Ambrox Super":              100.0,
    "IPM":                       500.0,
    "Geosmin":                     1.0,
}

FIRST_EDITION_DIL = {
    "Scentenal":     0.01,
    "Alpha Irone":   0.30,
    "Myristic Acid": 0.20,
    "Musk Ketone":   0.10,
    "Exaltolide":    0.10,
    "Ambrettolide":  0.10,
    "Ambrox Super":  0.30,
    "Geosmin":       0.01,
}

PINNED = {"Dihydromyrcenol"}

AXES = ("longevity", "sillage", "luxury", "texture", "stacking_depth",
        "photorealism", "perceptual_clarity", "skin_performance",
        "synergy", "hedonic")


# ═══════════════════════════════════════════════════════════════════════════════
# STOCHASTIC HILL-CLIMB
# ═══════════════════════════════════════════════════════════════════════════════
def hill_climb_stochastic(ing, dil, scorer, floor, ceiling, rng,
                          passes_broad=20, passes_fine=12):
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)
    start_geo = best_geo

    # Baseline OAV error count — the starting formula may already trip
    # proportional-scaling guards (existing warnings in v4_Final). Moves are
    # rejected only if they INCREASE the error count beyond baseline.
    base_rev = check_proportional_scaling(ing, dil, BATCH_ML, 15.0)
    baseline_err_count = sum(1 for c in base_rev if c.severity == "error")

    STEPS_BROAD = [+15, +30, +60, +120, +240, -15, -30, -60, -120, -240]
    STEPS_FINE = [+10, +15, +30, -10, -15, -30]

    total_passes = passes_broad + passes_fine
    for p in range(total_passes):
        steps = list(STEPS_BROAD if p < passes_broad else STEPS_FINE)
        keys = list(ing.keys())
        rng.shuffle(keys)
        found = False
        for name in keys:
            cur = ing[name]
            fl = floor.get(name, 0.0)
            cl = ceiling.get(name, float("inf"))
            if fl >= cl - 0.5:
                continue
            probe_steps = list(steps)
            rng.shuffle(probe_steps)
            for step in probe_steps:
                new_val = cur + step
                if new_val < fl - 0.5 or new_val > cl + 0.5:
                    continue
                if new_val < 1 or new_val > 2500:
                    continue
                trial = dict(ing)
                trial[name] = new_val
                rev = check_proportional_scaling(trial, dil, BATCH_ML, 15.0)
                trial_err = sum(1 for c in rev if c.severity == "error")
                if trial_err > baseline_err_count:
                    continue
                geo, detail = score_formula(trial, dil, scorer)
                if geo > best_geo + 0.02:
                    ing = trial
                    best_geo, best_detail = geo, detail
                    found = True
                    cur = new_val
                    break
        if not found:
            break
    return ing, best_detail, best_geo, start_geo


# ═══════════════════════════════════════════════════════════════════════════════
# DRIVER
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print("═" * 78)
    print("  PHOTOREALISTIC IRIS — FIRST EDITION (v4_Final / v6 master)")
    print("  10 stochastic hill-climb runs @ 30 mL")
    print("═" * 78)
    print(f"  Materials: {len(FIRST_EDITION_ING)}")
    print(f"  Starting concentrate: {sum(FIRST_EDITION_ING.values()):.0f} µL "
          f"= {sum(FIRST_EDITION_ING.values()) / 300.0:.2f}% of 30 mL")
    print(f"  Pinned: {sorted(PINNED)}")
    print(f"  Floor = 1 µL (free range); OAV guard: only reject NEW errors")
    print()

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    # Paper first edition — give the optimizer real freedom:
    # floor = 1 µL minimum for all materials (keep present, allow reduction),
    # ceiling = +∞ except DHM which is pinned at starting µL.
    floor = {n: 1.0 for n in FIRST_EDITION_ING}
    ceiling = {n: float("inf") for n in FIRST_EDITION_ING}
    for n in PINNED:
        floor[n] = FIRST_EDITION_ING[n]
        ceiling[n] = FIRST_EDITION_ING[n]

    baseline_geo, baseline_detail = score_formula(
        FIRST_EDITION_ING, FIRST_EDITION_DIL, scorer)
    print(f"  Baseline geo: {baseline_geo:.3f}")
    print(f"  Baseline axes:")
    for a in AXES:
        print(f"    {a:22s} {baseline_detail.get(a, 0.0):6.2f}")
    print()

    results = []
    SEEDS = [1, 42, 2026, 7, 13, 99, 314, 2718, 1618, 31415]
    for i, seed in enumerate(SEEDS, 1):
        t0 = time.time()
        rng = random.Random(seed)
        ing_best, detail_best, geo_best, start_geo = hill_climb_stochastic(
            FIRST_EDITION_ING, FIRST_EDITION_DIL, scorer,
            floor, ceiling, rng)
        dt = time.time() - t0
        gain = geo_best - baseline_geo
        conc = sum(ing_best.values())
        print(f"  Run {i:2d}/10 · seed={seed:>5d} · geo {geo_best:7.3f} "
              f"(Δ{gain:+.3f}) · conc {conc:5.0f} µL · {dt:5.1f}s")
        results.append({
            "run": i, "seed": seed, "geo": geo_best, "gain": gain,
            "detail": detail_best, "ing": ing_best, "conc_ul": conc,
            "elapsed_s": dt,
        })
    print()

    # ── Summary table
    print("─" * 78)
    print("  PER-RUN AXIS SCORES")
    print("─" * 78)
    hdr = f"  {'run':>3s} {'seed':>5s} {'geo':>7s} {'gain':>6s}"
    for a in AXES:
        hdr += f" {a[:4]:>5s}"
    print(hdr)
    for r in results:
        line = f"  {r['run']:>3d} {r['seed']:>5d} {r['geo']:>7.2f} {r['gain']:>+6.2f}"
        for a in AXES:
            line += f" {r['detail'].get(a, 0.0):>5.1f}"
        print(line)
    print()

    geos = [r["geo"] for r in results]
    gains = [r["gain"] for r in results]
    print("─" * 78)
    print("  AGGREGATE STATS (geo)")
    print("─" * 78)
    print(f"    baseline : {baseline_geo:7.3f}")
    print(f"    mean     : {mean(geos):7.3f}  (Δ{mean(gains):+.3f})")
    print(f"    median   : {median(geos):7.3f}")
    print(f"    stdev    : {stdev(geos):7.3f}")
    print(f"    min      : {min(geos):7.3f}")
    print(f"    max      : {max(geos):7.3f}")
    print(f"    range    : {max(geos) - min(geos):7.3f}")
    print()

    # ── Best run
    best = max(results, key=lambda r: r["geo"])
    print("─" * 78)
    print(f"  BEST RUN: seed={best['seed']} · geo={best['geo']:.3f} "
          f"(Δ{best['gain']:+.3f} vs baseline)")
    print("─" * 78)
    print(f"  {'Material':30s} {'Dil':>5s} {'Start µL':>10s} {'Best µL':>10s} {'Δ':>7s}")
    sorted_items = sorted(
        best["ing"].items(),
        key=lambda kv: -abs(kv[1] - FIRST_EDITION_ING.get(kv[0], 0.0)),
    )
    for name, v_best in sorted_items:
        v_start = FIRST_EDITION_ING.get(name, 0.0)
        d = FIRST_EDITION_DIL.get(name, 1.0)
        delta = v_best - v_start
        dilstr = f"{int(d * 100)}%" if d < 1.0 else "neat"
        print(f"  {name:30s} {dilstr:>5s} {v_start:>10.0f} {v_best:>10.0f} {delta:>+7.0f}")
    print(f"  {'(Concentrate total)':30s} {'':>5s} "
          f"{sum(FIRST_EDITION_ING.values()):>10.0f} "
          f"{sum(best['ing'].values()):>10.0f} "
          f"{sum(best['ing'].values()) - sum(FIRST_EDITION_ING.values()):>+7.0f}")
    print()
    print("  Best run axes:")
    for a in AXES:
        b = baseline_detail.get(a, 0.0)
        x = best["detail"].get(a, 0.0)
        print(f"    {a:22s} {b:6.2f} → {x:6.2f} (Δ{x - b:+.2f})")
    print()
    print("  Done.")


if __name__ == "__main__":
    main()
