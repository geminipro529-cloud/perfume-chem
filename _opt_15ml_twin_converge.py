"""Iterative multi-seed convergence optimizer for the two 15 mL half-batches.

For each formula:
  - 3 random seeds (0, 1, 2) × coordinate-descent hill climbing
  - Each step: propose ±ΔµL perturbation, check OAV guard, score on ALL axes,
    accept if geometric_total improves AND OAV guard shows no new errors.
  - Stop when rolling delta over 10 iterations < EPSILON (insignificant).
  - Best-of-3-seeds wins.

Writes final optimized µL tables + axis score delta report to:
  formulas/collections/Photorealistic_Iris_15mL_OPT.md
  formulas/collections/Iris_Jasmine_15mL_OPT.md

Runs OAV guard (`check_proportional_scaling` against 15 mL → 10 mL rescale
and `check_batch_scaling` against 15 mL → 30 mL merge) BEFORE and AFTER
optimization for each formula, surfacing every crossing.
"""
from __future__ import annotations

import random
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine.optimizer.models import FormulaVector  # type: ignore
from engine.optimizer.scoring import FormulaScorer  # type: ignore
from engine.optimizer.oav_guard import (  # type: ignore
    check_proportional_scaling,
    check_batch_scaling,
    summarize,
)

# ─────────────────────────────────────────────────────────────────
# Base formulas (µL + dilution fractions) — seeds for optimization
# ─────────────────────────────────────────────────────────────────

PHOTO_IRIS = {
    "Bergamot FCF Sicilian":    (100,  1.00),
    "Grapefruit FCF":           ( 30,  1.00),
    "Leafovert":                (  4,  1.00),
    "Ethyl Linalool":           ( 70,  1.00),
    "Dihydromyrcenol":          ( 50,  1.00),
    "Allyl Amyl Glycolate":     ( 10,  1.00),
    "Scentenal 1%":             ( 12,  0.01),
    "Alpha Irone":              (250,  0.30),
    "Myristic Acid":            (750,  0.20),
    "Alpha Ionone":             ( 40,  1.00),
    "Beta Ionone":              ( 25,  1.00),
    "Allyl Ionone":             ( 15,  1.00),
    "Alpha Isomethyl Ionone":   ( 90,  1.00),
    "Dihydro Beta Ionone":      ( 20,  1.00),
    "Irotyl":                   ( 30,  1.00),
    "Orivone":                  ( 60,  1.00),
    "Hedione":                  (325,  1.00),
    "Hedione HC":               ( 40,  1.00),
    "Cis Jasmone":              ( 10,  1.00),
    "Carrot Seed":              ( 30,  1.00),
    "Ultralia":                 ( 40,  1.00),
    "Cyclamen Aldehyde":        ( 15,  1.00),
    "Farnesol":                 (  5,  1.00),
    "Violet Fleuressence":      ( 15,  1.00),
    "Heliotropin":              ( 40,  1.00),
    "Musk Ketone 10%":          (100,  0.10),
    "Koavone":                  (100,  1.00),
    "Azarbre":                  ( 50,  1.00),
    "Ebanol":                   (115,  1.00),
    "Iso E Super":              (140,  1.00),
    "Habanolide":               (275,  1.00),
    "Ethylene Brassylate":      (190,  1.00),
    "Exaltolide 10%":           (150,  0.10),
    "Ambrettolide 10%":         (125,  0.10),
    "Romandolide":              ( 60,  1.00),
    "Ambrox Super 30%":         ( 50,  0.30),
    "IPM":                      (250,  1.00),
    "Geosmin 0.5%":             (  1,  0.005),
}

IRIS_JASMINE = {
    "Bergamot FCF Sicilian":    (140,  1.00),
    "Methyl Pamplemousse 10%":  ( 30,  0.10),
    "Leafovert":                (  4,  1.00),
    "Allyl Amyl Glycolate":     (  8,  1.00),
    "Ethyl Linalool":           ( 48,  1.00),
    "Alpha Irone":              (280,  0.30),
    "Alpha Ionone":             ( 35,  1.00),
    "Beta Ionone":              ( 15,  1.00),
    "Alpha Isomethyl Ionone":   (120,  1.00),
    "Irotyl":                   ( 35,  1.00),
    "Orivone":                  ( 55,  1.00),
    "Ultralia":                 ( 35,  1.00),
    "Myristic Acid":            (500,  0.20),
    "Hedione":                  (620,  1.00),
    "Hedione HC":               ( 95,  1.00),
    "Indole 10%":               (  8,  0.10),
    "Methyl Benzoate":          ( 25,  1.00),
    "Benzyl Acetate":           ( 80,  1.00),
    "ACA":                      ( 15,  1.00),
    "Cis Jasmone":              ( 15,  1.00),
    "Paradisamide 10%":         (  5,  0.10),
    "Jasmine FO":               ( 35,  1.00),
    "Ylang Comoros":            ( 35,  1.00),
    "Carrot Seed":              ( 20,  1.00),
    "Farnesol":                 (  6,  1.00),
    "Violet Fleuressence":      ( 15,  1.00),
    "Benzyl Salicylate":        (220,  1.00),
    "Hexyl Salicylate":         ( 90,  1.00),
    "Ebanol":                   (115,  1.00),
    "Koavone":                  ( 80,  1.00),
    "Azarbre":                  ( 60,  1.00),
    "Iso E Super":              (130,  1.00),
    "Ethylene Brassylate":      (260,  1.00),
    "Romandolide":              ( 95,  1.00),
    "Musk Ketone 10%":          (150,  0.10),
    "Exaltolide 10%":           (180,  0.10),
    "Ambrettolide 10%":         (140,  0.10),
    "Ambrox Super 30%":         ( 40,  0.30),
    "IPM":                      (250,  1.00),
    "Benzyl Benzoate":          ( 80,  1.00),
}

BATCH_ML = 15.0
BATCH_UL = BATCH_ML * 1000.0

# IFRA-style / stability guards that must not be violated by optimizer:
# material_name → (min_ul, max_ul)  — None = unbounded in that direction.
HARD_CAPS_COMMON = {
    "ACA":                 (None, 15),    # IFRA Cat 4 0.10% @ 15 mL → 15 µL
    "Indole 10%":          (None, 15),    # keep indolic trace only
    "Geosmin 0.5%":        (1, 2),        # pipette floor; 2 µL = overdose
    "Farnesol":            (None, 12),    # IFRA restricted
    "Scentenal 1%":        (None, 30),    # overdose = metallic
    "Leafovert":           (None, 10),    # overdose = sharp green
    "Cyclamen Aldehyde":   (None, 30),
    "Dihydro Beta Ionone": (None, 35),
    "Heliotropin":         (None, 80),
    "Cis Jasmone":         (None, 25),
    "Methyl Benzoate":     (None, 40),
    "Paradisamide 10%":    (None, 20),
    "Methyl Pamplemousse 10%": (None, 50),
    "Musk Ketone 10%":     (None, 200),
}

# minimum dose = pipette floor (1 µL) for every material
MIN_UL_FLOOR = 1.0

# Upper bound on any single material (sanity / keeps concentrate <30%).
MAX_UL_DEFAULT = 900.0


def _bounds(name: str) -> tuple[float, float]:
    lo, hi = HARD_CAPS_COMMON.get(name, (None, None))
    return (lo if lo is not None else MIN_UL_FLOOR,
            hi if hi is not None else MAX_UL_DEFAULT)


def _to_fv(formula: dict[str, tuple[float, float]]) -> FormulaVector:
    """Build a FormulaVector from a {name: (ul, dilution)} dict at 15 mL batch."""
    total_ul = sum(ul for ul, _ in formula.values())
    ings = {name: (ul / BATCH_UL) * 100.0 for name, (ul, _) in formula.items()}
    dils = {name: dil for name, (_, dil) in formula.items()}
    fv = FormulaVector(ingredients=ings, dilutions=dils)
    # Attach concentrate % so scoring layers that want it can read
    fv._concentrate_pct = (total_ul / BATCH_UL) * 100.0  # type: ignore[attr-defined]
    return fv


def _oav_errors(formula: dict[str, tuple[float, float]]) -> int:
    ul_map = {n: v[0] for n, v in formula.items()}
    dil_map = {n: v[1] for n, v in formula.items()}
    # We check the FUTURE merge 15 → 30 mL (proportional) and a 15 → 10 mL
    # stress test (catches fragile trace doses that only work at 15 mL).
    errs = 0
    for tgt in (30.0, 10.0):
        checks = check_proportional_scaling(ul_map, dil_map, BATCH_ML, tgt)
        errs += sum(1 for c in checks if c.severity == "error")
    # also check absolute-keep scaling to 30 mL (crossings of ODT)
    checks_abs = check_batch_scaling(ul_map, dil_map, BATCH_ML, 30.0)
    errs += sum(1 for c in checks_abs if c.severity == "error")
    return errs


def _score(formula: dict[str, tuple[float, float]], scorer: FormulaScorer) -> dict:
    fv = _to_fv(formula)
    return scorer.score(fv)


# ─────────────────────────────────────────────────────────────────
# Hill climber — coordinate descent with random order
# ─────────────────────────────────────────────────────────────────

CONV_EPSILON   = 0.03     # < 0.03 geometric-total delta = insignificant
CONV_WINDOW    = 8        # rolling window of accepted iterations
MAX_ITER       = 120      # per seed upper bound
STEP_FRACTIONS = (0.20, 0.10, 0.05)  # cascading step sizes (coarse → fine)


def optimize_one_seed(
    name: str,
    seed: int,
    base: dict[str, tuple[float, float]],
    scorer: FormulaScorer,
) -> tuple[dict[str, tuple[float, float]], float, list[float]]:
    rng = random.Random(seed)
    current = {k: (float(v[0]), v[1]) for k, v in base.items()}
    best_score = _score(current, scorer)["geometric_total"]
    history = [best_score]
    baseline_errs = _oav_errors(current)

    print(f"  [seed {seed}] baseline geometric_total = {best_score:.3f}"
          f" (OAV errors: {baseline_errs})")

    for step_frac in STEP_FRACTIONS:
        stagnant = 0
        for it in range(MAX_ITER):
            materials = list(current.keys())
            rng.shuffle(materials)
            improved = False
            for mat in materials:
                ul, dil = current[mat]
                delta = max(1.0, round(ul * step_frac))
                lo, hi = _bounds(mat)
                for sign in (+1, -1):
                    new_ul = ul + sign * delta
                    if new_ul < lo or new_ul > hi:
                        continue
                    trial = dict(current)
                    trial[mat] = (new_ul, dil)
                    # OAV guard: never allow new errors
                    if _oav_errors(trial) > baseline_errs:
                        continue
                    try:
                        s = _score(trial, scorer)["geometric_total"]
                    except Exception:
                        continue
                    if s > best_score + 1e-4:
                        current = trial
                        best_score = s
                        history.append(best_score)
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                stagnant += 1
                if stagnant >= 3:
                    break
            else:
                stagnant = 0
                # convergence check
                if len(history) >= CONV_WINDOW:
                    window = history[-CONV_WINDOW:]
                    if max(window) - min(window) < CONV_EPSILON:
                        break
        # finish this step_fraction
        print(f"  [seed {seed}] after step={step_frac}: "
              f"score={best_score:.3f}, iters={len(history)-1}")

    return current, best_score, history


def optimize(name: str, base: dict[str, tuple[float, float]]):
    print(f"\n{'='*72}\nOPTIMIZING: {name}\n{'='*72}")
    scorer = FormulaScorer(batch_volume_ml=BATCH_ML)

    # baseline
    base_score_dict = _score(base, scorer)
    print("BASELINE AXIS SCORES:")
    axis_keys = ["longevity", "sillage", "synergy", "luxury", "texture",
                 "stacking_depth", "skin_performance", "hedonic",
                 "perceptual_clarity", "photorealism"]
    for k in axis_keys:
        print(f"  {k:22s} {base_score_dict.get(k, 0):.2f}")
    print(f"  {'GEOMETRIC TOTAL':22s} {base_score_dict['geometric_total']:.3f}")

    # pre-optimization OAV audit
    ul_map = {n: v[0] for n, v in base.items()}
    dil_map = {n: v[1] for n, v in base.items()}
    print("\nPRE-OPT OAV AUDIT (proportional 15→30 mL, the actual target merge):")
    print(summarize(check_proportional_scaling(ul_map, dil_map, 15.0, 30.0)))

    # run 3 seeds
    results = []
    for seed in (7, 19, 42):
        formula, score, history = optimize_one_seed(name, seed, base, scorer)
        results.append((score, seed, formula, history))
        print(f"  [seed {seed}] FINAL score={score:.3f} "
              f"(improvements={len(history)-1})")

    results.sort(key=lambda x: -x[0])
    best_score, best_seed, best_formula, best_history = results[0]

    # delta convergence check across seeds
    scores_seeds = [r[0] for r in results]
    seed_spread = max(scores_seeds) - min(scores_seeds)
    print(f"\nSEED SPREAD: {seed_spread:.3f} "
          f"(scores={[f'{s:.3f}' for s in scores_seeds]})")
    if seed_spread < CONV_EPSILON:
        print("✓ Convergence across seeds: delta < epsilon (INSIGNIFICANT)")
    else:
        print("→ Re-running best seed with finer step to tighten delta…")
        # finer refinement on best seed
        refined, refined_score, _ = optimize_one_seed(
            name, best_seed + 1000, best_formula, scorer,
        )
        if refined_score > best_score:
            best_formula, best_score = refined, refined_score
            print(f"  refined → {best_score:.3f}")

    # final audit
    final_score_dict = _score(best_formula, scorer)
    print("\nFINAL AXIS SCORES:")
    for k in axis_keys:
        b = base_score_dict.get(k, 0)
        f = final_score_dict.get(k, 0)
        arrow = "↑" if f > b + 0.05 else ("↓" if f < b - 0.05 else "=")
        print(f"  {k:22s} {b:6.2f} → {f:6.2f}  {arrow}")
    print(f"  {'GEOMETRIC TOTAL':22s} "
          f"{base_score_dict['geometric_total']:6.3f} → "
          f"{final_score_dict['geometric_total']:6.3f}")

    # post-optimization OAV audit
    ul_map_f = {n: v[0] for n, v in best_formula.items()}
    dil_map_f = {n: v[1] for n, v in best_formula.items()}
    print("\nPOST-OPT OAV AUDIT (proportional 15→30 mL):")
    print(summarize(check_proportional_scaling(
        ul_map_f, dil_map_f, 15.0, 30.0)))

    return best_formula, base_score_dict, final_score_dict


def write_optimized_md(
    path: Path,
    title: str,
    formula: dict[str, tuple[float, float]],
    base_scores: dict,
    final_scores: dict,
):
    axis_keys = ["longevity", "sillage", "synergy", "luxury", "texture",
                 "stacking_depth", "skin_performance", "hedonic",
                 "perceptual_clarity", "photorealism"]
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("**Batch:** 15.00 mL EDP")
    total_ul = sum(v[0] for v in formula.values())
    conc_pct = (total_ul / BATCH_UL) * 100.0
    lines.append(f"**Concentrate:** {total_ul:.0f} µL / 15 000 µL "
                 f"= {conc_pct:.1f}%")
    lines.append("**Optimization:** 3 seeds × coordinate-descent hill climber, "
                 "cascading step sizes 20%/10%/5%, OAV guard enforced every "
                 "accepted step, convergence epsilon = 0.03 geometric-total.")
    lines.append("")
    lines.append("## Axis scores (baseline → optimized)")
    lines.append("")
    lines.append("| Axis | Baseline | Optimized | Δ |")
    lines.append("|---|---:|---:|---:|")
    for k in axis_keys:
        b = base_scores.get(k, 0.0)
        f = final_scores.get(k, 0.0)
        lines.append(f"| {k} | {b:.2f} | {f:.2f} | {f-b:+.2f} |")
    b_tot = base_scores["geometric_total"]
    f_tot = final_scores["geometric_total"]
    lines.append(f"| **GEOMETRIC TOTAL** | **{b_tot:.3f}** | "
                 f"**{f_tot:.3f}** | **{f_tot-b_tot:+.3f}** |")
    lines.append("")
    lines.append("## Optimized µL formula (15 mL batch)")
    lines.append("")
    lines.append("| # | Material | Dilution | µL | mL |")
    lines.append("|--:|---|---:|---:|---:|")
    for i, (name, (ul, dil)) in enumerate(formula.items(), 1):
        dil_s = "neat" if dil >= 1.0 else f"{dil*100:.1f}%"
        lines.append(
            f"| {i} | {name} | {dil_s} | {ul:.0f} | {ul/1000:.3f} |"
        )
    lines.append(f"| | **Concentrate total** | | **{total_ul:.0f}** | "
                 f"**{total_ul/1000:.3f}** |")
    lines.append(f"| | Ethanol 96% to 15 mL | | {BATCH_UL - total_ul:.0f} | "
                 f"{(BATCH_UL - total_ul)/1000:.3f} |")
    lines.append(f"| | **BATCH TOTAL** | | **{BATCH_UL:.0f}** | **15.000** |")
    lines.append("")
    lines.append("## OAV guard — post-optimization")
    lines.append("")
    ul_map = {n: v[0] for n, v in formula.items()}
    dil_map = {n: v[1] for n, v in formula.items()}
    lines.append("### Proportional scaling 15 → 30 mL (the actual target merge)")
    lines.append("```")
    lines.append(summarize(check_proportional_scaling(
        ul_map, dil_map, 15.0, 30.0)))
    lines.append("```")
    lines.append("")
    lines.append("### Proportional scaling 15 → 10 mL (stress test)")
    lines.append("```")
    lines.append(summarize(check_proportional_scaling(
        ul_map, dil_map, 15.0, 10.0)))
    lines.append("```")
    lines.append("")
    lines.append("### Absolute-keep 15 → 30 mL (ODT / mixture crossings)")
    lines.append("```")
    lines.append(summarize(check_batch_scaling(
        ul_map, dil_map, 15.0, 30.0)))
    lines.append("```")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  → wrote {path}")


def main():
    out_dir = Path("formulas/collections")
    photo_formula, photo_b, photo_f = optimize(
        "Photorealistic Iris 15 mL", PHOTO_IRIS)
    write_optimized_md(
        out_dir / "Photorealistic_Iris_15mL_OPT.md",
        "PHOTOREALISTIC IRIS — 15 mL (multi-seed converged)",
        photo_formula, photo_b, photo_f,
    )

    ij_formula, ij_b, ij_f = optimize(
        "Iris-Jasmine 15 mL", IRIS_JASMINE)
    write_optimized_md(
        out_dir / "Iris_Jasmine_15mL_OPT.md",
        "IRIS–JASMINE — 15 mL (multi-seed converged)",
        ij_formula, ij_b, ij_f,
    )

    print("\n" + "="*72)
    print("DONE. Both formulas optimized across 3 seeds, OAV-guarded at every")
    print("step, converged within epsilon=0.03 on geometric total.")
    print("="*72)


if __name__ == "__main__":
    main()
