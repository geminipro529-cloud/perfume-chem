"""Iris Rêverie Lactée — 50 mL v2 verification + optimizer.

v2 = hand-expanded palette (Javanol, Cedarwood Virginia EO, Heliotropin added;
Alpha Irone / Ambrettolide / Ebanol / EB / Heliotropal / γ-Undecalactone lifted;
Iso E Super trimmed) targeting luxury + hedonic weakness in v1.

Steps:
  1. Score v1 (optimizer-converged) baseline.
  2. Score v2 (hand-expanded palette) as starting point.
  3. Run iterative hill-climb waves on v2 until convergence.
  4. Report v1 vs v2-start vs v2-final.
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

# ═══════════════════════════════════════════════════════════════════════════════
# v1 — optimizer-converged 50 mL formula (from Iris_Reverie_Lactee_50mL_optimized.md)
# geo = 79.056 (reported)
# ═══════════════════════════════════════════════════════════════════════════════
IRL_V1 = {
    "Benzoin Resinoid":          1475.0,
    "Hedione":                   1250.0,
    "Ethylene Brassylate":        900.0,
    "Ethyl Linalool":             650.0,
    "Ebanol":                     650.0,
    "Hedione HC":                 600.0,
    "Exaltolide":                 600.0,
    "Bergamot FCF oil Sicilian":  550.0,
    "Ambrox Super":               550.0,
    "Alpha Irone":                500.0,
    "Carrot Seed EO":             450.0,
    "Habanolide":                 450.0,
    "Iso E Super":                450.0,
    "Musk Ketone":                400.0,
    "Vanillin":                   400.0,
    "Benzyl Salicylate":          350.0,
    "Hydroxycitronellal":         300.0,
    "Coumarin":                   300.0,
    "Delta Decalactone":          300.0,
    "Hexyl Salicylate":           300.0,
    "Orivone":                    225.0,
    "Ambrettolide":               200.0,
    "Mayol":                      175.0,
    "Ethyl Maltol":               100.0,
    "Lilyreal ND":                 75.0,
    "DBCA":                        75.0,
    "Freesia HDI":                 75.0,
    "Ethyl Vanillin":              75.0,
    "Damascol":                    75.0,
    "Bourgeonal":                  50.0,
    "Beta Ionone":                 40.0,
    "Anisaldehyde":                40.0,
    "Scentenal":                   25.0,
    "Alpha Ionone":                25.0,
    "Irotyl":                      25.0,
    "Ultralia":                    25.0,
    "Alpha Isomethyl Ionone":      25.0,
    "PEDMC":                       25.0,
    "Heliotropal":                 25.0,
    "Aurantiol":                   25.0,
    "Geosmin":                     15.0,
    "Indole":                      15.0,
    "Isoeugenol":                  15.0,
    "Farnesol":                    10.0,
    "Gamma Undecalactone":         10.0,
}

# ═══════════════════════════════════════════════════════════════════════════════
# v2 — hand-expanded palette
# ═══════════════════════════════════════════════════════════════════════════════
IRL_V2 = {
    "Benzoin Resinoid":          1475.0,
    "Hedione":                   1250.0,
    "Ethylene Brassylate":       1100.0,   # +200
    "Alpha Irone":                900.0,   # +400
    "Ebanol":                     900.0,   # +250
    "Ethyl Linalool":             650.0,
    "Hedione HC":                 600.0,
    "Carrot Seed EO":             600.0,   # +150
    "Bergamot FCF oil Sicilian":  550.0,
    "Ambrox Super":               550.0,
    "Ambrettolide":               700.0,   # +500 (compensates cut Exaltolide)
    "Habanolide":                 600.0,   # +150 (compensates cut Exaltolide)
    "Musk Ketone":                400.0,
    "Vanillin":                   400.0,
    "Benzyl Salicylate":          350.0,
    "Orivone":                    350.0,   # +125
    "Hydroxycitronellal":         300.0,
    "Coumarin":                   300.0,
    "Delta Decalactone":          300.0,
    "Hexyl Salicylate":           300.0,
    "Iso E Super":                250.0,   # -200
    "Mayol":                      175.0,
    "Cedarwood Virginia EO":      150.0,   # NEW
    "Javanol":                    100.0,   # NEW
    "Ethyl Maltol":               100.0,
    "Heliotropal":                100.0,   # +75
    "Lilyreal ND":                 75.0,
    "DBCA":                        75.0,
    "Freesia HDI":                 75.0,
    "Ethyl Vanillin":              75.0,
    "Damascol":                    75.0,
    "Gamma Undecalactone":         75.0,   # +65
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

IRL_DIL = {
    "Scentenal":        0.01,
    "Alpha Irone":      0.30,
    "Musk Ketone":      0.10,
    "Coumarin":         0.20,
    "Vanillin":         0.10,
    "Ethyl Maltol":     0.10,
    "Benzoin Resinoid": 0.50,
    "Exaltolide":       0.10,
    "Ambrettolide":     0.10,
    "Ambrox Super":     0.30,
    "Damascol":         0.10,
    "Geosmin":          0.01,
    "Indole":           0.10,
    # new v2 materials — all neat
}

SUB_ODT_TRACES = {"Geosmin", "Indole", "Scentenal", "Isoeugenol",
                  "Farnesol", "Damascol", "Aurantiol", "Bourgeonal",
                  "Ethyl Vanillin"}
AIMI_CAPPED = {"Alpha Isomethyl Ionone"}

AXES = ("longevity", "sillage", "luxury", "texture", "stacking_depth",
        "photorealism", "perceptual_clarity", "skin_performance",
        "synergy", "hedonic")

CONVERGENCE_THRESHOLD = 0.05
MAX_WAVES = 15


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
    print("  IRIS RÊVERIE LACTÉE — 50 mL v2 VERIFICATION + OPTIMIZER")
    print("═" * 78)

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    # Score v1 (optimizer-converged baseline)
    v1_conc = sum(IRL_V1.values())
    v1_geo, v1_detail = score_formula(IRL_V1, IRL_DIL, scorer)
    print(f"\n  v1 (optimizer-converged):")
    print(f"    materials:   {len(IRL_V1)}")
    print(f"    concentrate: {v1_conc:.0f} µL = {v1_conc/(BATCH_ML*10):.2f}%")
    print(f"    geo:         {v1_geo:.3f}")

    # Score v2 starting point (hand-expanded palette)
    v2_conc = sum(IRL_V2.values())
    v2_start_geo, v2_start_detail = score_formula(IRL_V2, IRL_DIL, scorer)
    print(f"\n  v2 starting (hand-expanded palette):")
    print(f"    materials:   {len(IRL_V2)}")
    print(f"    concentrate: {v2_conc:.0f} µL = {v2_conc/(BATCH_ML*10):.2f}%")
    print(f"    geo:         {v2_start_geo:.3f}  Δ vs v1: {v2_start_geo - v1_geo:+.3f}")

    print(f"\n  v1 vs v2-start axis comparison:")
    print(f"    {'axis':22s} {'v1':>8s} {'v2-start':>10s} {'Δ':>8s}")
    for a in AXES:
        b = v1_detail.get(a, 0.0)
        f = v2_start_detail.get(a, 0.0)
        print(f"    {a:22s} {b:8.2f} {f:10.2f} {f-b:+8.2f}")

    # Floors / ceilings for v2 optimization
    floor = {n: 1.0 for n in IRL_V2}
    ceiling = {n: float("inf") for n in IRL_V2}
    for n in SUB_ODT_TRACES:
        if n in IRL_V2:
            ceiling[n] = IRL_V2[n] * 3.0
    for n in AIMI_CAPPED:
        if n in IRL_V2:
            ceiling[n] = IRL_V2[n]

    # Run convergence waves on v2
    current_ing = dict(IRL_V2)
    current_geo = v2_start_geo
    current_detail = v2_start_detail
    SEED_POOL = [1, 42, 2026, 7, 13, 99, 314, 2718, 1618, 31415,
                 271, 577, 1001, 2357, 4099]

    print("\n" + "═" * 78)
    print("  v2 CONVERGENCE WAVES")
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
    print("  FINAL — v1 vs v2-start vs v2-final")
    print("═" * 78)
    final_conc = sum(current_ing.values())
    print(f"\n  v1 geo:       {v1_geo:.3f}")
    print(f"  v2 start geo: {v2_start_geo:.3f}  (Δ vs v1: {v2_start_geo - v1_geo:+.3f})")
    print(f"  v2 final geo: {current_geo:.3f}  (Δ vs v1: {current_geo - v1_geo:+.3f})")
    print(f"  v2 final concentrate: {final_conc:.0f} µL = "
          f"{final_conc/(BATCH_ML*10):.2f}%")

    print(f"\n  Axis comparison v1 → v2-final:")
    print(f"    {'axis':22s} {'v1':>8s} {'v2fin':>8s} {'Δ':>8s}")
    for a in AXES:
        b = v1_detail.get(a, 0.0)
        f = current_detail.get(a, 0.0)
        d = f - b
        mark = "↑" if d > 0.5 else ("↓" if d < -0.5 else "·")
        print(f"    {mark} {a:22s} {b:8.2f} {f:8.2f} {d:+8.2f}")

    # Ingredient deltas
    all_names = sorted(set(IRL_V1) | set(current_ing))
    diffs = []
    for n in all_names:
        b = IRL_V1.get(n, 0.0)
        f = current_ing.get(n, 0.0)
        if abs(f - b) >= 0.5:
            diffs.append((n, b, f, f - b))
    diffs.sort(key=lambda x: -abs(x[3]))
    print(f"\n  Ingredient deltas v1 → v2-final (|Δ| ≥ 1 µL):")
    print(f"    {'Material':30s} {'v1':>8s} {'v2fin':>8s} {'ΔµL':>8s}")
    for n, b, f, d in diffs[:30]:
        print(f"    {n:30s} {b:8.0f} {f:8.0f} {d:+8.0f}")

    # Full final formula
    print(f"\n  FINAL v2 FORMULA (sorted by µL):")
    for n, v in sorted(current_ing.items(), key=lambda x: -x[1]):
        dil = IRL_DIL.get(n, 1.0)
        dil_str = f"{int(dil*100)}%" if dil < 1.0 else "neat"
        print(f"    {n:30s} {dil_str:>6s}  {v:7.1f} µL")


if __name__ == "__main__":
    main()
