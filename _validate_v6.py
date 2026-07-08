"""Validate proposed v6 changes vs v3 — multi-run to defeat scorer noise.

v6 = v3 + these 5 changes (from 15-probe convergence analysis):
  Javanol                 100 → 200  (+100)
  Cedarwood Virginia EO   350 → 550  (+200)
  Iso E Super              50 → 150  (+100)
  Benzyl Salicylate       250 → 100  (-150)
  Coumarin                275 → 150  (-125)

Run N=8 scorings of both v3 and v6, report mean/stdev/min/max + axis means.
"""
from __future__ import annotations
import os, sys, statistics, time

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

from engine.optimizer.scoring import FormulaScorer
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula
from _opt_iris_reverie_15probes import IRL_V3, IRL_DIL_BASE, AXES

BATCH_ML = 50.0
N_RUNS = 8

V6_DELTAS = {
    "Javanol":                  +100.0,
    "Cedarwood Virginia EO":    +200.0,
    "Iso E Super":              +100.0,
    "Benzyl Salicylate":        -150.0,
    "Coumarin":                 -125.0,
}


def make_v6():
    v6 = dict(IRL_V3)
    for k, d in V6_DELTAS.items():
        v6[k] = v6.get(k, 0.0) + d
    return v6


def multi_score(label, ing, dil, n):
    geos = []
    axis_runs = {a: [] for a in AXES}
    t0 = time.time()
    for i in range(n):
        # Each run gets a fresh scorer to randomize RNG state
        scorer = FormulaScorer(synergy_graph=SynergyGraph(),
                               batch_volume_ml=BATCH_ML)
        geo, detail = score_formula(ing, dil, scorer)
        geos.append(geo)
        for a in AXES:
            axis_runs[a].append(detail.get(a, 0.0))
        print(f"  {label} run {i+1}/{n}: geo={geo:.3f}", flush=True)
    dt = time.time() - t0
    print(f"  {label} total {dt:.0f}s")
    return geos, axis_runs


def summarize(label, geos):
    return {
        "label": label,
        "mean": statistics.mean(geos),
        "stdev": statistics.stdev(geos) if len(geos) > 1 else 0.0,
        "min": min(geos),
        "max": max(geos),
        "n": len(geos),
    }


def main():
    print("═" * 78)
    print("  VALIDATE v6 vs v3 — multi-run")
    print("═" * 78)
    v6 = make_v6()
    print(f"\n  v3 concentrate: {sum(IRL_V3.values()):.0f} µL")
    print(f"  v6 concentrate: {sum(v6.values()):.0f} µL")
    print(f"  Δ concentrate : {sum(v6.values()) - sum(IRL_V3.values()):+.0f} µL")
    print(f"\n  Changes (v3 → v6):")
    for k, d in V6_DELTAS.items():
        v0 = IRL_V3.get(k, 0.0)
        print(f"    {k:28s} {v0:7.1f} → {v0+d:7.1f}  Δ{d:+7.1f}")

    print(f"\n  Scoring v3 ×{N_RUNS} ...")
    v3_geos, v3_axes = multi_score("v3", IRL_V3, IRL_DIL_BASE, N_RUNS)
    print(f"\n  Scoring v6 ×{N_RUNS} ...")
    v6_geos, v6_axes = multi_score("v6", v6,    IRL_DIL_BASE, N_RUNS)

    s3 = summarize("v3", v3_geos)
    s6 = summarize("v6", v6_geos)

    print("\n" + "═" * 78)
    print("  GEO SUMMARY")
    print("═" * 78)
    print(f"\n  {'label':>6s} {'n':>3s} {'mean':>8s} {'stdev':>7s} "
          f"{'min':>8s} {'max':>8s}")
    for s in (s3, s6):
        print(f"  {s['label']:>6s} {s['n']:3d} {s['mean']:8.3f} "
              f"{s['stdev']:7.3f} {s['min']:8.3f} {s['max']:8.3f}")
    d_mean = s6["mean"] - s3["mean"]
    pooled_stdev = (s3["stdev"]**2 + s6["stdev"]**2) ** 0.5
    print(f"\n  Δ mean (v6 − v3): {d_mean:+.3f}")
    print(f"  Pooled stdev    : {pooled_stdev:.3f}")
    if pooled_stdev > 0.001:
        print(f"  Signal-to-noise : {d_mean/pooled_stdev:+.2f}σ")

    print("\n" + "═" * 78)
    print("  AXIS MEANS (v3 → v6)")
    print("═" * 78)
    print(f"\n  {'axis':24s} {'v3 mean':>9s} {'v6 mean':>9s} {'Δ':>8s}")
    for a in AXES:
        m3 = statistics.mean(v3_axes[a])
        m6 = statistics.mean(v6_axes[a])
        d = m6 - m3
        mark = "↑" if d > 0.05 else ("↓" if d < -0.05 else " ")
        print(f"  {mark} {a:22s} {m3:9.3f} {m6:9.3f} {d:+8.3f}")

    print("\n" + "═" * 78)
    verdict = ("REAL WIN" if d_mean > pooled_stdev
               else ("MARGINAL" if d_mean > 0.5 * pooled_stdev
                     else ("NOISE" if abs(d_mean) < pooled_stdev
                           else "REAL LOSS")))
    print(f"  VERDICT: {verdict}  (Δ={d_mean:+.3f}, σ_pool={pooled_stdev:.3f})")
    print("═" * 78)


if __name__ == "__main__":
    main()
