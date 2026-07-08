"""Two follow-ups on the 5 named fougeres:

  (1) Re-score F2 (Côte Sauvage) with a log1p-compressed OAV objective so
      the marine axis (Calone-saturated, OAVs in tens of thousands) does not
      dominate the L2 distance over balance with citrus/wood/amber. Re-runs
      DE and reports whether the optimizer finds a meaningfully different wt%.

  (2) Visualize all 5 optimized envelopes (top/heart/base, family-stacked) as
      one figure so the directional shapes can be compared at a glance.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping

import matplotlib.pyplot as plt
import numpy as np

from _fougere_5_named_v2 import (
    CONCEPTS, FAMILY, IFRA_CAP_PCT_CONC,
    REGISTRY, _odt_air_ppm, build_tables, make_headspace_fn,
    family_summed,
)
from engine.optimizer.oav_objective import OAVObjective, differential_evolution_oav


# ─── (1) log-OAV objective for F2 ────────────────────────────────────────────

def _log_envelope_match(profile, families, target):
    obs = {}
    for mat, m in profile.items():
        fam = families.get(mat, "default")
        obs[fam] = obs.get(fam, 0.0) + m.get("oav", 0.0)
    err = 0.0
    for fam, tgt in target.items():
        err += (math.log1p(obs.get(fam, 0.0)) - math.log1p(tgt)) ** 2
    return -err


def score_log(wt_pct, obj):
    snap = obj.headspace_fn(wt_pct)
    total = 0.0
    novelty = 0.0
    prev = None
    for window in ("top", "heart", "base"):
        prof = snap.get(window, {})
        tgt = obj.target_envelope.get(window, {})
        total += obj.weights["match"] * _log_envelope_match(prof, obj.families, tgt)
        cur = {m: p.get("oav", 0.0) for m, p in prof.items()}
        if prev is not None:
            keys = set(prev) | set(cur)
            a = [prev.get(k, 0.0) for k in keys]
            b = [cur.get(k, 0.0) for k in keys]
            na = math.sqrt(sum(x * x for x in a)) or 1e-9
            nb = math.sqrt(sum(x * x for x in b)) or 1e-9
            total += obj.weights["novelty"] * (1.0 - sum(x * y for x, y in zip(a, b)) / (na * nb))
        prev = cur
    return total


def de_log(obj, *, maxiter=60, popsize=18, seed=42):
    """DE with log-objective. scipy DE if available; otherwise fall back."""
    try:
        from scipy.optimize import differential_evolution
    except ImportError:
        return None, None

    def neg(x):
        wt = {m: float(v) for m, v in zip(obj.materials, x)}
        return -score_log(wt, obj)

    res = differential_evolution(neg, bounds=obj.bounds, maxiter=maxiter,
                                 popsize=popsize, seed=seed, tol=1e-7,
                                 polish=True, init="sobol")
    best_wt = {m: float(v) for m, v in zip(obj.materials, res.x)}
    return best_wt, -res.fun


def rerun_F2_log():
    f2 = next(c for c in CONCEPTS if c["key"] == "F2")
    recipe = {k: v for k, v in f2["recipe"].items() if v > 0}
    materials = list(recipe.keys())
    tables = build_tables(materials)

    bounds = []
    for m in materials:
        v = recipe[m]
        lo, hi = max(0.0, v * 0.65), v * 1.45
        cap = IFRA_CAP_PCT_CONC.get(m)
        if cap is not None:
            hi = min(hi, cap)
        if v < 0.5:
            hi = max(hi, v * 2.0)
        bounds.append((lo, hi))

    headspace_fn = make_headspace_fn(tables)
    obj = OAVObjective(
        materials=materials, bounds=bounds,
        target_envelope=f2["envelope"],
        headspace_fn=headspace_fn, families=tables["fam"],
    )

    init_score = score_log(recipe, obj)
    init_snap = headspace_fn(recipe)
    print(f"\n=== F2 Côte Sauvage  —  log-OAV objective ===")
    print(f"  INITIAL  log-score = {init_score:+.4f}")

    best_wt, best_score = de_log(obj, maxiter=60, popsize=18, seed=42)
    total = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_snap = headspace_fn(best_wt_norm)
    final_score = score_log(best_wt_norm, obj)
    print(f"  OPTIMIZED log-score = {final_score:+.4f}   (delta = {final_score - init_score:+.4f})")

    # Compare to v2 (L2) optimum for the same recipe
    print("\n  Top-12 wt% (sorted by optimized):")
    print(f"  {'material':30s}  {'init':>8s}  {'log-opt':>8s}   delta")
    sorted_mats = sorted(materials, key=lambda m: -best_wt_norm[m])[:12]
    for m in sorted_mats:
        i, o = recipe[m], best_wt_norm[m]
        print(f"  {m:30s}  {i:8.3f}  {o:8.3f}   {o - i:+.3f}")

    print("\n  Optimized envelope (log-fit):")
    for win in ("top", "heart", "base"):
        fams = family_summed(best_snap[win], tables["fam"])
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
        print(f"    {win:5s}: " + "  ".join(f"{k}={v:.1f}" for k, v in items))

    return {
        "init_recipe": recipe, "log_opt_recipe": best_wt_norm,
        "init_log_score": init_score, "final_log_score": final_score,
        "envelope_target": f2["envelope"],
        "envelope_optimized": {w: family_summed(best_snap[w], tables["fam"])
                               for w in ("top", "heart", "base")},
    }


# ─── (2) Envelope visualization ──────────────────────────────────────────────

FAMILY_ORDER = ["citrus", "aromatic", "marine", "geranium", "coumarin",
                "spice", "gourmand", "radiance", "cushion",
                "wood", "amber", "moss", "musk"]
FAMILY_COLORS = {
    "citrus":   "#ffd166",
    "aromatic": "#9cd08f",
    "marine":   "#7fb3d5",
    "geranium": "#f7a6c0",
    "coumarin": "#d4a373",
    "spice":    "#e07a5f",
    "gourmand": "#c08552",
    "radiance": "#fcd5ce",
    "cushion":  "#e2c2c6",
    "wood":     "#8d6a4f",
    "amber":    "#b08968",
    "moss":     "#606c38",
    "musk":     "#a89f91",
    "default":  "#bfbfbf",
}


def render_envelope_grid(out_path: Path):
    """5 concepts × 3 windows stacked-bar grid, log-scale y."""
    # Reload v2 results
    v2 = json.loads((Path(__file__).parent / "_fougere_5_named_v2_out.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(5, 3, figsize=(13, 16), sharey=True)
    for row, (key, data) in enumerate(v2.items()):
        for col, win in enumerate(("top", "heart", "base")):
            ax = axes[row, col]
            env = data["optimized"]["envelope"][win]
            tgt = data["envelope_target"].get(win, {})

            # Stacked bar of optimized envelope
            bottom = 0.0
            xpos = 0.0
            bar_w = 0.6
            for fam in FAMILY_ORDER:
                v = env.get(fam, 0.0)
                if v <= 0:
                    continue
                ax.bar(xpos, v, bottom=bottom, width=bar_w,
                       color=FAMILY_COLORS.get(fam, "#bfbfbf"),
                       edgecolor="white", linewidth=0.4,
                       label=fam if (row == 0 and col == 0) else None)
                bottom += v

            # Target overlay (hollow bar at right)
            tgt_total = sum(tgt.values())
            if tgt_total > 0:
                bottom2 = 0.0
                for fam in FAMILY_ORDER:
                    v = tgt.get(fam, 0.0)
                    if v <= 0:
                        continue
                    ax.bar(xpos + 0.75, v, bottom=bottom2, width=bar_w * 0.6,
                           color=FAMILY_COLORS.get(fam, "#bfbfbf"),
                           edgecolor="black", linewidth=0.5, alpha=0.45)
                    bottom2 += v

            ax.set_yscale("symlog", linthresh=10)
            ax.set_xticks([xpos, xpos + 0.75])
            ax.set_xticklabels(["opt", "tgt"], fontsize=8)
            ax.tick_params(axis='y', labelsize=7)
            ax.grid(axis='y', linestyle=':', alpha=0.4)
            if col == 0:
                ax.set_ylabel(f"{key}  {data['name']}", fontsize=9, rotation=0,
                              labelpad=80, ha='right', va='center')
            if row == 0:
                ax.set_title(win, fontsize=11, fontweight='bold')

    handles = [plt.Rectangle((0, 0), 1, 1, color=FAMILY_COLORS[f]) for f in FAMILY_ORDER]
    fig.legend(handles, FAMILY_ORDER, loc='lower center', ncol=7,
               fontsize=9, bbox_to_anchor=(0.5, -0.01), frameon=False)
    fig.suptitle("Five Named Fougères — Optimized vs Target OAV Envelopes\n"
                 "(stacked family OAV per evaporation window; symlog y; right bar = target shape)",
                 fontsize=12, y=0.995)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))

    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\nWrote {out_path}")


def main():
    f2_result = rerun_F2_log()

    out_json = Path(__file__).parent / "_fougere_5_logF2_out.json"
    out_json.write_text(json.dumps(f2_result, indent=2), encoding="utf-8")
    print(f"\nWrote {out_json}")

    render_envelope_grid(Path(__file__).parent / "_fougere_5_envelopes.png")


if __name__ == "__main__":
    main()
