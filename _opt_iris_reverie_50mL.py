"""Iris Rêverie Lactée — 50 mL iterative optimizer.

Scales the 10 mL formula × 5 to 50 mL, then runs stochastic hill-climb waves
until successive waves produce < CONVERGENCE_THRESHOLD geo improvement.

A "wave" = one full stochastic hill-climb (20 broad + 12 fine passes) with a
different RNG seed. If a wave's ending geo improves on the current best by less
than the threshold, we call the run converged.
"""
from __future__ import annotations

import io, os, random, sys, time
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
from _scale_30mL_verify_nonlinear import score_formula

BATCH_ML = 50.0

# ═══════════════════════════════════════════════════════════════════════════════
# Iris Rêverie Lactée — 10 mL formula × 5 → 50 mL (µL × 5)
# ═══════════════════════════════════════════════════════════════════════════════
IRL_10mL = {
    # TOP
    "Bergamot FCF oil Sicilian":   50.0,
    "Ethyl Linalool":              30.0,
    "Scentenal":                    5.0,
    # IRIS POWDER CORE
    "Alpha Irone":                180.0,
    "Alpha Ionone":                25.0,
    "Beta Ionone":                  8.0,
    "Irotyl":                      25.0,
    "Orivone":                     45.0,
    "Ultralia":                    25.0,
    "Carrot Seed EO":              20.0,
    "Alpha Isomethyl Ionone":      40.0,
    "Musk Ketone":                 80.0,
    # WHITE FLORAL HEART
    "Hydroxycitronellal":          70.0,
    "Mayol":                       35.0,
    "Lilyreal ND":                 25.0,
    "Bourgeonal":                  10.0,
    "DBCA":                        30.0,
    "Freesia HDI":                 20.0,
    "PEDMC":                       20.0,
    "Hedione":                    280.0,
    "Hedione HC":                  40.0,
    "Farnesol":                     2.0,
    # CREAM DRYDOWN
    "Heliotropal":                 50.0,
    "Coumarin":                   200.0,
    "Vanillin":                   120.0,
    "Ethyl Vanillin":               5.0,
    "Ethyl Maltol":                40.0,
    "Anisaldehyde":                 8.0,
    "Gamma Undecalactone":         12.0,
    "Delta Decalactone":           10.0,
    "Benzoin Resinoid":            60.0,
    # MUSK / COCOON
    "Benzyl Salicylate":          140.0,
    "Hexyl Salicylate":            60.0,
    "Ethylene Brassylate":        150.0,
    "Exaltolide":                  80.0,
    "Ambrettolide":                60.0,
    "Habanolide":                  70.0,
    "Ebanol":                      55.0,
    "Iso E Super":                 90.0,
    "Ambrox Super":                30.0,
    # SUB-ODT TRACES
    "Aurantiol":                    5.0,
    "Damascol":                    15.0,
    "Geosmin":                      3.0,
    "Indole":                       3.0,
    "Isoeugenol":                   3.0,
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
}

# Scale ×5 to 50 mL
IRL_50mL = {k: v * 5.0 for k, v in IRL_10mL.items()}

# Character-preservation: keep sub-ODT traces within reasonable trace range
# (floor = starting µL, ceiling = 3× starting) to ensure they stay sub-threshold.
SUB_ODT_TRACES = {"Geosmin", "Indole", "Scentenal", "Isoeugenol",
                  "Farnesol", "Damascol", "Aurantiol", "Bourgeonal",
                  "Ethyl Vanillin"}

# Low-AIMI per user spec — cap AIMI at starting value so it never gets heavy
AIMI_CAPPED = {"Alpha Isomethyl Ionone"}

AXES = ("longevity", "sillage", "luxury", "texture", "stacking_depth",
        "photorealism", "perceptual_clarity", "skin_performance",
        "synergy", "hedonic")

CONVERGENCE_THRESHOLD = 0.05   # geo-point Δ below which we declare insignificant
MAX_WAVES = 25


# ═══════════════════════════════════════════════════════════════════════════════
# STOCHASTIC HILL-CLIMB (single wave)
# ═══════════════════════════════════════════════════════════════════════════════
def hill_climb_wave(ing, dil, scorer, floor, ceiling, rng,
                    passes_broad=20, passes_fine=12):
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)

    base_rev = check_proportional_scaling(ing, dil, BATCH_ML, 15.0)
    baseline_err_count = sum(1 for c in base_rev if c.severity == "error")

    # 50 mL is ~1.67× the 30 mL optimizer, so step sizes scale proportionally
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


# ═══════════════════════════════════════════════════════════════════════════════
# DRIVER — iterate waves until delta < threshold
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print("═" * 78)
    print("  IRIS RÊVERIE LACTÉE — 50 mL ITERATIVE CONVERGENCE OPTIMIZER")
    print("═" * 78)
    start_conc = sum(IRL_50mL.values())
    print(f"  Materials: {len(IRL_50mL)}")
    print(f"  Starting concentrate: {start_conc:.0f} µL "
          f"= {start_conc / (BATCH_ML * 10):.2f}% of {BATCH_ML:.0f} mL")
    print(f"  Convergence threshold: Δgeo < {CONVERGENCE_THRESHOLD}")
    print(f"  Max waves: {MAX_WAVES}")
    print(f"  Sub-ODT traces held ≤ 3× start: {sorted(SUB_ODT_TRACES)}")
    print(f"  AIMI capped at start: {sorted(AIMI_CAPPED)}")
    print()

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    # Floors / ceilings
    floor = {n: 1.0 for n in IRL_50mL}
    ceiling = {n: float("inf") for n in IRL_50mL}

    # Sub-ODT traces: ceiling = 3× start (keep sub-threshold character)
    for n in SUB_ODT_TRACES:
        if n in IRL_50mL:
            ceiling[n] = IRL_50mL[n] * 3.0

    # AIMI: ceiling locked at start (user: "only little AIMI")
    for n in AIMI_CAPPED:
        if n in IRL_50mL:
            ceiling[n] = IRL_50mL[n]

    baseline_geo, baseline_detail = score_formula(IRL_50mL, IRL_DIL, scorer)
    print(f"  Baseline geo @ 50 mL: {baseline_geo:.3f}")
    print(f"  Baseline axes:")
    for a in AXES:
        print(f"    {a:22s} {baseline_detail.get(a, 0.0):6.2f}")
    print()

    # Iterative waves
    current_ing = dict(IRL_50mL)
    current_geo = baseline_geo
    current_detail = baseline_detail
    SEED_POOL = [1, 42, 2026, 7, 13, 99, 314, 2718, 1618, 31415,
                 271, 577, 1001, 2357, 4099, 8191, 131, 239, 617, 877,
                 1223, 1697, 2011, 2389, 2999]
    print("═" * 78)
    print("  CONVERGENCE WAVES")
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
        print(f"  {marker} Wave {wave_i:2d}/{MAX_WAVES} · seed={seed:>5d} · "
              f"{current_geo:.3f} → {new_geo:.3f}  "
              f"Δ{delta:+.3f}  · {accepted:2d} moves · {dt:.1f}s")

        if delta > CONVERGENCE_THRESHOLD:
            current_ing = new_ing
            current_geo = new_geo
            current_detail = new_detail
        else:
            # No significant improvement → still accept the local improvement
            # but track insignificance. Converged when 2 consecutive waves < threshold.
            if delta > 0:
                current_ing = new_ing
                current_geo = new_geo
                current_detail = new_detail
            # Check last 2 waves
            if len(history) >= 2:
                last2 = [h[4] for h in history[-2:]]
                if all(d <= CONVERGENCE_THRESHOLD for d in last2):
                    print(f"\n  ✓ CONVERGED: last 2 waves both Δ ≤ {CONVERGENCE_THRESHOLD}")
                    break
    else:
        print(f"\n  ⚠ Hit MAX_WAVES={MAX_WAVES} without convergence")

    # ═══════════════════════════════════════════════════════════════════════
    # FINAL REPORT
    # ═══════════════════════════════════════════════════════════════════════
    print()
    print("═" * 78)
    print("  FINAL RESULTS — 50 mL IRIS RÊVERIE LACTÉE")
    print("═" * 78)
    final_conc = sum(current_ing.values())
    print(f"  Waves executed: {len(history)}")
    print(f"  Baseline geo: {baseline_geo:.3f}")
    print(f"  Final geo:    {current_geo:.3f}")
    print(f"  Total Δ:      {current_geo - baseline_geo:+.3f}")
    print(f"  Final concentrate: {final_conc:.0f} µL = "
          f"{final_conc / (BATCH_ML * 10):.2f}%")
    print()
    print("  Axis deltas (baseline → final):")
    for a in AXES:
        b = baseline_detail.get(a, 0.0)
        f = current_detail.get(a, 0.0)
        d = f - b
        mark = "↑" if d > 0.5 else ("↓" if d < -0.5 else "·")
        print(f"    {mark} {a:22s} {b:6.2f} → {f:6.2f}  Δ{d:+.2f}")
    print()

    # Ingredient deltas (sorted by absolute change)
    print("  Ingredient deltas (sorted by |Δ|):")
    print(f"    {'Material':30s} {'Start':>8s} → {'Final':>8s}  {'ΔµL':>8s}  {'Δ%':>7s}")
    print(f"    {'-'*30} {'-'*8}   {'-'*8}  {'-'*8}  {'-'*7}")
    deltas = []
    for n in current_ing:
        start = IRL_50mL.get(n, 0.0)
        end = current_ing[n]
        deltas.append((n, start, end, end - start))
    deltas.sort(key=lambda x: abs(x[3]), reverse=True)
    for n, s, e, d in deltas:
        pct = (d / s * 100.0) if s > 0 else 0.0
        if abs(d) < 0.5:
            continue
        print(f"    {n:30s} {s:8.1f} → {e:8.1f}  {d:+8.1f}  {pct:+6.1f}%")
    print()

    # Wave history table
    print("  Wave history:")
    print(f"    {'#':>3s} {'seed':>6s} {'geo_in':>8s}  {'geo_out':>8s}  "
          f"{'Δ':>7s}  {'moves':>6s}  {'time':>6s}")
    for h in history:
        print(f"    {h[0]:>3d} {h[1]:>6d} {h[2]:>8.3f}  {h[3]:>8.3f}  "
              f"{h[4]:>+7.3f}  {h[5]:>6d}  {h[6]:>5.1f}s")
    print()

    # Write final formula MD
    out = Path("formulas/collections/Iris_Reverie_Lactee_50mL_optimized.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Iris Rêverie Lactée — 50 mL Optimized\n\n")
    lines.append(f"**Batch:** 50.00 mL · ")
    lines.append(f"**Concentrate:** {final_conc / 1000.0:.3f} mL "
                 f"({final_conc / (BATCH_ML * 10):.2f} %)\n\n")
    lines.append(f"**Baseline geo @ 50 mL:** {baseline_geo:.3f}  \n")
    lines.append(f"**Optimized geo:** {current_geo:.3f}  \n")
    lines.append(f"**Gain:** {current_geo - baseline_geo:+.3f}  \n")
    lines.append(f"**Waves:** {len(history)} "
                 f"(converged when Δgeo < {CONVERGENCE_THRESHOLD})\n\n")
    lines.append("## Formula\n\n")
    lines.append("| Ingredient | Dilution | µL | mL |\n")
    lines.append("|---|---|---:|---:|\n")
    for n, amt in sorted(current_ing.items(), key=lambda kv: -kv[1]):
        d = IRL_DIL.get(n)
        dil_s = f"{int(d*100)} %" if d else "neat"
        lines.append(f"| {n} | {dil_s} | {amt:.0f} | {amt/1000:.3f} |\n")
    eth_ul = BATCH_ML * 1000.0 - final_conc
    lines.append(f"| Ethanol 96 % | carrier | {eth_ul:.0f} | {eth_ul/1000:.3f} |\n")
    lines.append(f"| **TOTAL** | | **{BATCH_ML*1000:.0f}** | **{BATCH_ML:.3f}** |\n\n")
    lines.append("## Axis scores\n\n")
    lines.append("| Axis | Baseline | Final | Δ |\n|---|---:|---:|---:|\n")
    for a in AXES:
        b = baseline_detail.get(a, 0.0)
        f = current_detail.get(a, 0.0)
        lines.append(f"| {a} | {b:.2f} | {f:.2f} | {f-b:+.2f} |\n")
    out.write_text("".join(lines), encoding="utf-8")
    print(f"  Written: {out}")


if __name__ == "__main__":
    main()
