"""Iris Rêverie Lactée — 50 mL v5 palette expansion pass.

v5 = v3 final + 3 new seeded materials + 3 hand trims, staying within the
original concept: transparent lactonic orris, iris-cream-sandalwood.

New materials seeded (from inventory, inv-verified):
  - ACA (Amyl Cinnamic Aldehyde) 50 µL neat — jasmine-muguet waxy body,
    reinforces Hedione radiance with actual jasmine substance. IFRA ceiling
    at 50 mL concentrate band ≈ 50 µL — dose at ceiling.
  - Cashmeran 20% 250 µL neat-equivalent (50 µL active) — textile-warmth
    that pairs directly with Alpha Irone's iris-powder register. Recovers
    skin axis lost to Exaltolide cut via different mechanism (warm textile
    not fatty-lactonic).
  - Azarbre 100 µL neat — cedar-amber smooth bridge between Cedarwood
    Virginia EO and the amber base. Warms Ambrox Super's cold crystalline
    mineral register without reading "cozy oriental".

Hand trims:
  - Ambrox Super 30% 550 → 450 (−100 trim, keeps crystalline but less cold)
  - Benzoin Resinoid 50% 1475 → 1200 (clarity headroom, still dominant mass)
  - Hedione HC 600 → 400, Hedione 1250 → 1400 (rebalance toward base Hedione)

Concept constraints preserved:
  - No Heliotropin (cut in v3)
  - No Exaltolide (inventory out)
  - No FTECs
  - Transparent, not oriental
  - Iris pillar stays at Alpha Irone 900
"""
from __future__ import annotations

import os, random, sys, time

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

# v3 final (baseline for v5) ---------------------------------------------------
IRL_V3 = {
    "Benzoin Resinoid":          1475.0,
    "Hedione":                   1250.0,
    "Ethyl Linalool":            1050.0,
    "Alpha Irone":                900.0,
    "Ebanol":                     900.0,
    "Ethylene Brassylate":        800.0,
    "Ambrettolide":               700.0,
    "Hedione HC":                 600.0,
    "Carrot Seed EO":             600.0,
    "Habanolide":                 600.0,
    "Bergamot FCF oil Sicilian":  550.0,
    "Ambrox Super":               550.0,
    "Musk Ketone":                400.0,
    "Vanillin":                   400.0,
    "Orivone":                    350.0,
    "Cedarwood Virginia EO":      350.0,
    "Hydroxycitronellal":         300.0,
    "Delta Decalactone":          300.0,
    "Hexyl Salicylate":           300.0,
    "Coumarin":                   275.0,
    "Benzyl Salicylate":          250.0,
    "Mayol":                      175.0,
    "Javanol":                    100.0,
    "Ethyl Maltol":               100.0,
    "Lilyreal ND":                 75.0,
    "DBCA":                        75.0,
    "Freesia HDI":                 75.0,
    "Ethyl Vanillin":              75.0,
    "Damascol":                    75.0,
    "Gamma Undecalactone":         75.0,
    "Iso E Super":                 50.0,
    "Heliotropal":                 50.0,
    "Bourgeonal":                  50.0,
    "Beta Ionone":                 40.0,
    "Anisaldehyde":                40.0,
    "Scentenal":                   25.0,
    "Alpha Ionone":                25.0,
    "Irotyl":                      25.0,
    "Ultralia":                    25.0,
    "Alpha Isomethyl Ionone":      25.0,
    "PEDMC":                       25.0,
    "Aurantiol":                   25.0,
    "Geosmin":                     15.0,
    "Indole":                      15.0,
    "Isoeugenol":                  15.0,
    "Farnesol":                    10.0,
}

# v5 = v3 + seeded ACA/Cashmeran/Azarbre + trims -------------------------------
IRL_V5 = dict(IRL_V3)
IRL_V5["Benzoin Resinoid"] = 1200.0   # 1475 → 1200, clarity headroom
IRL_V5["Hedione"]          = 1400.0   # 1250 → 1400
IRL_V5["Hedione HC"]       =  400.0   # 600 → 400
IRL_V5["Ambrox Super"]     =  450.0   # 550 → 450
IRL_V5["ACA"]              =   50.0   # NEW: jasmine-muguet body, IFRA ceiling
IRL_V5["Cashmeran"]        =  250.0   # NEW: 20% dilution — textile skin warmth
IRL_V5["Azarbre"]          =  100.0   # NEW: cedar-amber smooth bridge

IRL_DIL = {
    "Scentenal":        0.01,
    "Alpha Irone":      0.30,
    "Musk Ketone":      0.10,
    "Coumarin":         0.20,
    "Vanillin":         0.10,
    "Ethyl Maltol":     0.10,
    "Benzoin Resinoid": 0.50,
    "Ambrettolide":     0.10,
    "Ambrox Super":     0.30,
    "Damascol":         0.10,
    "Geosmin":          0.01,
    "Indole":           0.10,
    "Cashmeran":        0.20,    # NEW — 20% dilution
    # ACA, Azarbre = neat
}

SUB_ODT_TRACES = {"Geosmin", "Indole", "Scentenal", "Isoeugenol",
                  "Farnesol", "Damascol", "Aurantiol", "Bourgeonal",
                  "Ethyl Vanillin"}
AIMI_CAPPED = {"Alpha Isomethyl Ionone"}
# IFRA-restricted: ACA ≤ 0.1% of finished product ≈ 50 µL at 50 mL batch
IFRA_CAPPED = {"ACA": 50.0, "Farnesol": 10.0}

AXES = ("longevity", "sillage", "luxury", "texture", "stacking_depth",
        "photorealism", "perceptual_clarity", "skin_performance",
        "synergy", "hedonic")

CONVERGENCE_THRESHOLD = 0.05
MAX_WAVES = 12


def hill_climb_wave(ing, dil, scorer, floor, ceiling, rng,
                    passes_broad=20, passes_fine=12):
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)
    base_rev = check_proportional_scaling(ing, dil, BATCH_ML, 15.0)
    baseline_err_count = sum(1 for c in base_rev if c.severity == "error")

    STEPS_BROAD = [+25, +50, +100, +200, +400, -25, -50, -100, -200, -400]
    STEPS_FINE = [+15, +25, +50, -15, -25, -50]

    total_passes = passes_broad + passes_fine
    accepted = 0
    for p in range(total_passes):
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
                if trial_err > baseline_err_count:
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


def main():
    print("═" * 78)
    print("  IRIS RÊVERIE LACTÉE — 50 mL v5 (ACA + Cashmeran + Azarbre seed)")
    print("═" * 78)

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    # Score v3 baseline
    v3_conc = sum(IRL_V3.values())
    v3_geo, v3_detail = score_formula(IRL_V3, IRL_DIL, scorer)
    print(f"\n  v3 baseline (prior final):")
    print(f"    materials:   {len(IRL_V3)}")
    print(f"    concentrate: {v3_conc:.0f} µL = {v3_conc/(BATCH_ML*10):.2f}%")
    print(f"    geo:         {v3_geo:.3f}")

    # Score v5 starting point
    v5_conc = sum(IRL_V5.values())
    v5_start_geo, v5_start_detail = score_formula(IRL_V5, IRL_DIL, scorer)
    print(f"\n  v5 starting (+ACA +Cashmeran +Azarbre, −Benzoin −AmbroxSuper, Hedione rebal):")
    print(f"    materials:   {len(IRL_V5)}")
    print(f"    concentrate: {v5_conc:.0f} µL = {v5_conc/(BATCH_ML*10):.2f}%")
    print(f"    geo:         {v5_start_geo:.3f}  Δ vs v3: {v5_start_geo - v3_geo:+.3f}")

    print(f"\n  v3 vs v5-start axis comparison:")
    print(f"    {'axis':22s} {'v3':>8s} {'v5-start':>10s} {'Δ':>8s}")
    for a in AXES:
        b = v3_detail.get(a, 0.0)
        f = v5_start_detail.get(a, 0.0)
        print(f"    {a:22s} {b:8.2f} {f:10.2f} {f-b:+8.2f}")

    # Floors / ceilings
    floor = {n: 1.0 for n in IRL_V5}
    ceiling = {n: float("inf") for n in IRL_V5}
    for n in SUB_ODT_TRACES:
        if n in IRL_V5:
            ceiling[n] = IRL_V5[n] * 3.0
    for n in AIMI_CAPPED:
        if n in IRL_V5:
            ceiling[n] = IRL_V5[n]
    for n, cap in IFRA_CAPPED.items():
        if n in IRL_V5:
            ceiling[n] = cap

    current_ing = dict(IRL_V5)
    current_geo = v5_start_geo
    current_detail = v5_start_detail
    SEED_POOL = [1, 42, 2026, 7, 13, 99, 314, 2718, 1618, 31415,
                 271, 577]

    print("\n" + "═" * 78)
    print("  v5 CONVERGENCE WAVES")
    print("═" * 78)
    history = []
    for wave_i, seed in enumerate(SEED_POOL[:MAX_WAVES], 1):
        t0 = time.time()
        rng = random.Random(seed)
        new_ing, new_detail, new_geo, accepted = hill_climb_wave(
            current_ing, IRL_DIL, scorer, floor, ceiling, rng)
        dt = time.time() - t0
        delta = new_geo - current_geo
        history.append((wave_i, seed, current_geo, new_geo, delta, accepted, dt))
        marker = "★" if delta > CONVERGENCE_THRESHOLD else "·"
        print(f"  {marker} Wave {wave_i:2d} · seed={seed:>5d} · "
              f"{current_geo:.3f} → {new_geo:.3f}  Δ{delta:+.3f}  · "
              f"{accepted:2d} moves · {dt:.1f}s")
        if delta > 0:
            current_ing = new_ing
            current_geo = new_geo
            current_detail = new_detail
        if len(history) >= 2 and all(h[4] <= CONVERGENCE_THRESHOLD for h in history[-2:]):
            print(f"\n  ✓ CONVERGED: last 2 waves both Δ ≤ {CONVERGENCE_THRESHOLD}")
            break

    # Final report
    print("\n" + "═" * 78)
    print("  FINAL — v3 vs v5-start vs v5-final")
    print("═" * 78)
    final_conc = sum(current_ing.values())
    print(f"\n  v3 geo:       {v3_geo:.3f}")
    print(f"  v5 start geo: {v5_start_geo:.3f}  (Δ vs v3: {v5_start_geo - v3_geo:+.3f})")
    print(f"  v5 final geo: {current_geo:.3f}  (Δ vs v3: {current_geo - v3_geo:+.3f})")
    print(f"  v5 final concentrate: {final_conc:.0f} µL = "
          f"{final_conc/(BATCH_ML*10):.2f}%")

    print(f"\n  Axis comparison v3 → v5-final:")
    print(f"    {'axis':22s} {'v3':>8s} {'v5fin':>8s} {'Δ':>8s}")
    for a in AXES:
        b = v3_detail.get(a, 0.0)
        f = current_detail.get(a, 0.0)
        d = f - b
        mark = "↑" if d > 0.5 else ("↓" if d < -0.5 else "·")
        print(f"    {mark} {a:22s} {b:8.2f} {f:8.2f} {d:+8.2f}")

    # Ingredient deltas v3 → v5
    all_names = sorted(set(IRL_V3) | set(current_ing))
    print(f"\n  Ingredient deltas v3 → v5-final:")
    for n in all_names:
        v3v = IRL_V3.get(n, 0.0)
        v5v = current_ing.get(n, 0.0)
        d = v5v - v3v
        if abs(d) < 0.5:
            continue
        tag = " NEW" if v3v == 0.0 else ("  CUT" if v5v == 0.0 else "     ")
        print(f"    {tag} {n:32s} {v3v:7.1f} → {v5v:7.1f}  Δ{d:+.1f}")

    # Final formula sorted
    print(f"\n  v5 FINAL FORMULA (sorted by µL desc):")
    for n, v in sorted(current_ing.items(), key=lambda x: -x[1]):
        dil_str = f"{int(IRL_DIL.get(n, 1.0)*100)}%" if n in IRL_DIL else "neat"
        print(f"    {n:32s} {dil_str:>6s} {v:7.1f} µL")
    ethanol = 50000.0 - final_conc
    print(f"    {'Ethanol 96%':32s} {'carrier':>6s} {ethanol:7.1f} µL")
    print(f"    {'TOTAL':32s} {'':>6s} {50000.0:7.1f} µL")


if __name__ == "__main__":
    main()
