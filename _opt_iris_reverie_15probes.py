"""Iris Rêverie Lactée — 15 single-variable probes on v3 baseline.

Each probe: take v3, change ONE material (or add one new), run a short
hill-climb, and see if the result beats v3's 78.802.

Probes chosen by olfactive logic — each addresses a specific axis or
accord gap identified in v5 analysis, or tests the v5 finding that
Gamma Undecalactone wanted to go from 75 → 450.
"""
from __future__ import annotations

import os, random, sys, time, copy

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula

BATCH_ML = 50.0

IRL_V3 = {
    "Benzoin Resinoid":          1475.0, "Hedione":                   1250.0,
    "Ethyl Linalool":            1050.0, "Alpha Irone":                900.0,
    "Ebanol":                     900.0, "Ethylene Brassylate":        800.0,
    "Ambrettolide":               700.0, "Hedione HC":                 600.0,
    "Carrot Seed EO":             600.0, "Habanolide":                 600.0,
    "Bergamot FCF oil Sicilian":  550.0, "Ambrox Super":               550.0,
    "Musk Ketone":                400.0, "Vanillin":                   400.0,
    "Orivone":                    350.0, "Cedarwood Virginia EO":      350.0,
    "Hydroxycitronellal":         300.0, "Delta Decalactone":          300.0,
    "Hexyl Salicylate":           300.0, "Coumarin":                   275.0,
    "Benzyl Salicylate":          250.0, "Mayol":                      175.0,
    "Javanol":                    100.0, "Ethyl Maltol":               100.0,
    "Lilyreal ND":                 75.0, "DBCA":                        75.0,
    "Freesia HDI":                 75.0, "Ethyl Vanillin":              75.0,
    "Damascol":                    75.0, "Gamma Undecalactone":         75.0,
    "Iso E Super":                 50.0, "Heliotropal":                 50.0,
    "Bourgeonal":                  50.0, "Beta Ionone":                 40.0,
    "Anisaldehyde":                40.0, "Scentenal":                   25.0,
    "Alpha Ionone":                25.0, "Irotyl":                      25.0,
    "Ultralia":                    25.0, "Alpha Isomethyl Ionone":      25.0,
    "PEDMC":                       25.0, "Aurantiol":                   25.0,
    "Geosmin":                     15.0, "Indole":                      15.0,
    "Isoeugenol":                  15.0, "Farnesol":                    10.0,
}

IRL_DIL_BASE = {
    "Scentenal": 0.01, "Alpha Irone": 0.30, "Musk Ketone": 0.10,
    "Coumarin": 0.20, "Vanillin": 0.10, "Ethyl Maltol": 0.10,
    "Benzoin Resinoid": 0.50, "Ambrettolide": 0.10, "Ambrox Super": 0.30,
    "Damascol": 0.10, "Geosmin": 0.01, "Indole": 0.10,
}

SUB_ODT_TRACES = {"Geosmin", "Indole", "Scentenal", "Isoeugenol",
                  "Farnesol", "Damascol", "Aurantiol", "Bourgeonal",
                  "Ethyl Vanillin"}
AIMI_CAPPED = {"Alpha Isomethyl Ionone"}
IFRA_CAPPED = {"ACA": 50.0, "Farnesol": 10.0}

AXES = ("longevity", "sillage", "luxury", "texture", "stacking_depth",
        "photorealism", "perceptual_clarity", "skin_performance",
        "synergy", "hedonic")


# --- 15 probes. Each: name, description, mutator(ing, dil) ------------------
def probe(ing, dil, mods_add=None, dil_add=None):
    """Return (new_ing, new_dil) after applying modifications."""
    new_ing = dict(ing)
    new_dil = dict(dil)
    for k, v in (mods_add or {}).items():
        new_ing[k] = v
    for k, v in (dil_add or {}).items():
        new_dil[k] = v
    return new_ing, new_dil


PROBES = [
    ("GammaUnde 75→450",           "γ-Undecalactone push (v5 finding)",
        {"Gamma Undecalactone": 450.0}, {}),
    ("GammaUnde 75→300",           "γ-Undecalactone moderate push",
        {"Gamma Undecalactone": 300.0}, {}),
    ("DeltaDeca 300→500",          "δ-Decalactone creamy-peach lift",
        {"Delta Decalactone": 500.0}, {}),
    ("EthylLinalool 1050→1300",    "Linalool transparency lift",
        {"Ethyl Linalool": 1300.0}, {}),
    ("AlphaIrone 900→1100",        "Iris pillar reinforced",
        {"Alpha Irone": 1100.0}, {}),
    ("Ebanol 900→1100",            "Sandalwood creamy lift",
        {"Ebanol": 1100.0}, {}),
    ("Javanol 100→200",            "Sandalwood intimate reinforced",
        {"Javanol": 200.0}, {}),
    ("Orivone 350→500",            "Iris-butter warmth",
        {"Orivone": 500.0}, {}),
    ("CarrotSeed 600→800",         "Carrot seed iris-naturalism lift",
        {"Carrot Seed EO": 800.0}, {}),
    ("Hedione 1250→1500",          "Radiance amplifier max",
        {"Hedione": 1500.0}, {}),
    ("Ambrox 550→350",             "Crystalline amber trim",
        {"Ambrox Super": 350.0}, {}),
    ("BenzoinResinoid 1475→1100",  "Benzoin trim for clarity",
        {"Benzoin Resinoid": 1100.0}, {}),
    ("AddCashmeran 250",           "Cashmeran 20% textile skin warmth",
        {"Cashmeran": 250.0}, {"Cashmeran": 0.20}),
    ("AddACA 50",                  "ACA jasmine body (IFRA ceiling)",
        {"ACA": 50.0}, {}),
    ("AddAzarbre 100",             "Azarbre cedar-amber warm bridge",
        {"Azarbre": 100.0}, {}),
]


def mini_hill_climb(ing, dil, scorer, floor, ceiling, rng,
                    passes_broad=12, passes_fine=8):
    """Same structure as v5 script but shorter for 15-probe sweep."""
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)
    base_rev = check_proportional_scaling(ing, dil, BATCH_ML, 15.0)
    baseline_err = sum(1 for c in base_rev if c.severity == "error")

    STEPS_BROAD = [+25, +50, +100, +200, -25, -50, -100, -200]
    STEPS_FINE = [+15, +25, +50, -15, -25, -50]

    accepted = 0
    for p in range(passes_broad + passes_fine):
        steps = list(STEPS_BROAD if p < passes_broad else STEPS_FINE)
        keys = list(ing.keys())
        rng.shuffle(keys)
        found = False
        for name in keys:
            cur = ing[name]
            fl = floor.get(name, 1.0)
            cl = ceiling.get(name, float("inf"))
            if fl >= cl - 0.5:
                continue
            probe_steps = list(steps)
            rng.shuffle(probe_steps)
            for step in probe_steps:
                new_val = cur + step
                if new_val < fl - 0.5 or new_val > cl + 0.5:
                    continue
                if new_val < 1 or new_val > 4000:
                    continue
                trial = dict(ing)
                trial[name] = new_val
                rev = check_proportional_scaling(trial, dil, BATCH_ML, 15.0)
                trial_err = sum(1 for c in rev if c.severity == "error")
                if trial_err > baseline_err:
                    continue
                geo, detail = score_formula(trial, dil, scorer)
                if geo > best_geo + 0.02:
                    ing = trial
                    best_geo, best_detail = geo, detail
                    found = True
                    accepted += 1
                    cur = new_val
                    break
        if not found:
            break
    return ing, best_detail, best_geo, accepted


def build_bounds(ing):
    floor = {n: 1.0 for n in ing}
    ceiling = {n: float("inf") for n in ing}
    for n in SUB_ODT_TRACES:
        if n in ing:
            ceiling[n] = ing[n] * 3.0
    for n in AIMI_CAPPED:
        if n in ing:
            ceiling[n] = ing[n]
    for n, cap in IFRA_CAPPED.items():
        if n in ing:
            ceiling[n] = cap
    return floor, ceiling


def main():
    print("═" * 78)
    print("  IRIS RÊVERIE LACTÉE — 15 single-variable probes on v3")
    print("═" * 78)

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    # v3 baseline
    v3_geo, v3_detail = score_formula(IRL_V3, IRL_DIL_BASE, scorer)
    v3_conc = sum(IRL_V3.values())
    print(f"\n  v3 baseline: geo={v3_geo:.3f}, concentrate={v3_conc:.0f} µL "
          f"({v3_conc/(BATCH_ML*10):.2f}%)\n")

    results = []
    for i, (tag, desc, mods_add, dil_add) in enumerate(PROBES, 1):
        t0 = time.time()
        seed_ing, seed_dil = probe(IRL_V3, IRL_DIL_BASE, mods_add, dil_add)
        seed_geo, seed_detail = score_formula(seed_ing, seed_dil, scorer)
        floor, ceiling = build_bounds(seed_ing)
        rng = random.Random(42 + i)
        final_ing, final_detail, final_geo, moves = mini_hill_climb(
            seed_ing, seed_dil, scorer, floor, ceiling, rng)
        dt = time.time() - t0
        dseed = seed_geo - v3_geo
        dfinal = final_geo - v3_geo
        mark = "★" if dfinal > 0.05 else ("·" if dfinal > -0.05 else "✗")
        print(f"  {mark} Probe {i:2d}: {tag:28s}  seed={seed_geo:.3f} "
              f"(Δ{dseed:+.2f})  final={final_geo:.3f} (Δ{dfinal:+.2f})  "
              f"{moves:2d}m {dt:.0f}s")
        results.append((tag, desc, seed_geo, final_geo, dseed, dfinal,
                        final_detail, final_ing, seed_dil))

    # Ranked report
    print("\n" + "═" * 78)
    print("  RANKED BY FINAL Δ vs v3")
    print("═" * 78)
    results.sort(key=lambda r: -r[5])
    print(f"\n  {'tag':30s} {'seed':>8s} {'final':>8s} {'Δseed':>8s} {'Δfinal':>8s}")
    for tag, desc, sg_, fg, ds, df, _, _, _ in results:
        print(f"  {tag:30s} {sg_:8.3f} {fg:8.3f} {ds:+8.2f} {df:+8.2f}")

    # Top 3 detailed axis comparison
    print("\n" + "═" * 78)
    print("  TOP 3 — axis comparison vs v3")
    print("═" * 78)
    for tag, desc, sg_, fg, ds, df, fdet, fing, _ in results[:3]:
        print(f"\n  {tag}  ({desc})")
        print(f"    geo {v3_geo:.3f} → {fg:.3f}  Δ{df:+.3f}")
        for a in AXES:
            b = v3_detail.get(a, 0.0)
            f = fdet.get(a, 0.0)
            d = f - b
            if abs(d) >= 0.1:
                m = "↑" if d > 0 else "↓"
                print(f"      {m} {a:22s} {b:8.2f} → {f:8.2f}  Δ{d:+.2f}")
        # Top 5 ingredient changes
        diffs = []
        for n in set(IRL_V3) | set(fing):
            d = fing.get(n, 0.0) - IRL_V3.get(n, 0.0)
            if abs(d) >= 1.0:
                diffs.append((n, IRL_V3.get(n, 0.0), fing.get(n, 0.0), d))
        diffs.sort(key=lambda x: -abs(x[3]))
        print(f"    top ingredient moves:")
        for n, v0, v1, d in diffs[:8]:
            tag2 = " NEW" if v0 == 0 else "    "
            print(f"      {tag2} {n:28s} {v0:7.1f} → {v1:7.1f}  Δ{d:+7.1f}")


if __name__ == "__main__":
    main()
