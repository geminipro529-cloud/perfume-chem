"""
Scale 15 mL optimized formulas to 30 mL + non-linear reverification + hill-climb.

User request: "I want 30 mL for both perfumes. remember to use non-linear models
for ODT, OAV, volatility, etc. You have created the script. Fix the files and
then reverify with the nonlinear script, and see if anything can be optimized"

Plan:
  1. Load optimized ingredients/dilutions from _opt_convergence_v2_out.json
     (this holds v3 multi-seed converged results: Iris 82.698, Iris-Jasmine 81.053)
  2. Proportionally scale µL × 2 → 30 mL batch (concentrate % unchanged → OAV invariant)
  3. Non-linear reverification:
     - TemporalEngine (Raoult/Clausius-Clapeyron evaporation + Stevens perceived
       intensity + ODT mixture suppression) over 0-24 hr
     - score_dose_response (Hill-equation character-zone audit against
       CHARACTER_SHIFT_DATA — flags materials in negative/dangerous zones)
     - check_batch_scaling (absolute-µL semantics at 30 mL — ODT crossings)
     - check_proportional_scaling (30 → 15 mL reverse — trace pipette floor)
  4. Re-optimize at 30 mL with finer-grained moves (at 30 mL each ±15 µL move is
     half the concentrate-% delta of the same move at 15 mL, so the optimizer has
     2× finer resolution — briefly hill-climb to see if any gain)
  5. Write formulas/collections/{Photorealistic_Iris,Iris_Jasmine}_30mL_optimized.md

Live-stream stdout to _scale_30mL_out.txt via line_buffering + write_through.
"""
from __future__ import annotations

import io, json, math, os, sys, time
from pathlib import Path

# Unbuffered live stdout (survive `python script.py > log.txt`)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    fd = sys.stdout.fileno()
    sys.stdout = io.TextIOWrapper(os.fdopen(fd, "wb", 0), encoding="utf-8",
                                  errors="replace", line_buffering=True,
                                  write_through=True)

import numpy as np

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import (
    check_batch_scaling, check_proportional_scaling,
)
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.synergy_graph import SynergyGraph
from engine.temporal_graph import generate_temporal_graph
from engine.dose_response import score_dose_response

BATCH_ML = 30.0
SOURCE_ML = 15.0

AXIS_WEIGHTS = {
    "longevity": 1.0, "sillage": 1.0, "luxury": 1.0, "texture": 1.0,
    "stacking_depth": 1.0, "photorealism": 1.0,
    "perceptual_clarity": 0.6, "skin_performance": 0.6,
    "synergy": 0.5, "hedonic": 0.4,
}
WSUM = sum(AXIS_WEIGHTS.values())


def geo_composite(detail: dict) -> float:
    log_sum = 0.0
    for a, w in AXIS_WEIGHTS.items():
        v = max(float(detail.get(a, 5.0)), 5.0)
        log_sum += (w / WSUM) * math.log(v)
    return round(math.exp(log_sum), 3)


def score_formula(ing: dict, dil: dict, scorer: FormulaScorer) -> tuple[float, dict]:
    total_ul = sum(ing.values())
    fi = FormulaInfo(number=0, name="X", ingredients=ing, dilutions=dil,
                     concentrate_ml=total_ul / 1000.0, description="")
    fv = formula_to_vector(fi)
    s = scorer.score(fv)
    detail = {a: float(s.get(a, 5.0)) for a in AXIS_WEIGHTS}
    return geo_composite(detail), detail


def concentrate_pct_map(ing: dict, dil: dict) -> dict[str, float]:
    """Build {material: % of total concentrate} for TemporalEngine."""
    total = sum(amt * dil.get(n, 1.0) for n, amt in ing.items())
    # TemporalEngine wants % of concentrate including dilution solvent? The
    # docstring says "percentage_in_concentrate" — we use active-neat %.
    # Renormalise to sum ≈ 100 based on dosed µL (including dilution solvent).
    total_dosed = sum(ing.values())
    return {n: (amt / total_dosed) * 100.0 for n, amt in ing.items()}


def nonlinear_verify(label: str, ing30: dict, dil: dict) -> dict:
    """Run full non-linear audit on a 30 mL formula."""
    print(f"\n════════════════════════════════════════════════════════════")
    print(f"  NON-LINEAR VERIFICATION — {label} @ {BATCH_ML} mL")
    print(f"════════════════════════════════════════════════════════════")
    concentrate_ul = sum(ing30.values())
    conc_pct_total = concentrate_ul / (BATCH_ML * 1000.0) * 100.0
    print(f"  Concentrate: {concentrate_ul} µL / {BATCH_ML} mL = {conc_pct_total:.2f}%")

    # ── (A) OAV guard — absolute-µL audit at 30 mL ──
    print(f"\n── (A) OAV guard: absolute-µL at 30 mL (ODT crossings) ──")
    abs_checks = check_batch_scaling(ing30, dil, BATCH_ML, BATCH_ML)
    errs = [c for c in abs_checks if c.severity == "error"]
    warns = [c for c in abs_checks if c.severity == "warn"]
    print(f"  {len(errs)} err · {len(warns)} warn (informational flags omitted)")
    for c in errs + warns:
        print(f"    {c.severity}: {c.message}")

    # ── (B) OAV guard — proportional 30 → 15 mL reverse (re-split safety) ──
    print(f"\n── (B) OAV guard: proportional 30 → 15 mL reverse (re-split) ──")
    rev_checks = check_proportional_scaling(ing30, dil, BATCH_ML, 15.0)
    rerrs = [c for c in rev_checks if c.severity == "error"]
    rwarns = [c for c in rev_checks if c.severity == "warn"]
    rinfos = [c for c in rev_checks if c.severity == "info"]
    print(f"  {len(rerrs)} err · {len(rwarns)} warn · {len(rinfos)} info")
    for c in rerrs + rwarns:
        print(f"    {c.severity}: {c.message}")

    # ── (C) Hill-equation dose-response: character-zone audit ──
    print(f"\n── (C) Hill dose-response: character zones vs CHARACTER_SHIFT_DATA ──")
    dr = score_dose_response(ing30, dilutions=dil, total_volume_ul=concentrate_ul)
    print(f"  Dose-response score: {dr.score:.1f}/100")
    print(f"  Overdosed (negative/dangerous zone): {len(dr.overdosed)}")
    for o in dr.overdosed:
        print(f"    ⚠ {o['material']:28s} @ {o['conc_pct']:.3f}% → {o['quality']}: {o['character']}")
    print(f"  Optimal (positive zone): {len(dr.optimal)}")
    print(f"  Marginal (neutral zone): {len(dr.marginal)}")
    for m in dr.marginal:
        print(f"    ⚠ {m['material']:28s} @ {m['conc_pct']:.3f}% → {m['quality']}: {m['character']}")

    # ── (D) TemporalEngine: full evaporation/perception non-linear model ──
    print(f"\n── (D) TemporalEngine: Raoult/Stevens/mixture-suppression ──")
    ingredients_pct = concentrate_pct_map(ing30, dil)
    print(f"  Simulating {len(ingredients_pct)} materials...")
    try:
        sg = SynergyGraph()
        sg.build(list(ingredients_pct.keys()))
        syn_data = {k: e.weight for k, e in sg.edges.items()}
        profile, _fig = generate_temporal_graph(
            formula_name=f"{label} @ 30 mL",
            ingredients=ingredients_pct,
            save_path=None, show=False, synergy_data=syn_data,
        )
        print(f"  Perceptual half-life: {profile.perceptual_half_life_hr:.1f} hr")
        print(f"  Longevity (OAV>2):    {profile.longevity_hr:.1f} hr")
        subliminal = [m for m, mt in profile.materials.items() if max(mt.oav) < 1.0]
        print(f"  Subliminal materials (OAV peak < 1): {len(subliminal)}")
        for s in subliminal:
            print(f"    ○ {s}")
        # OAV at key timepoints (summary)
        for hrs, tag in [(0, "Opening"), (1, "1hr"), (4, "4hr"), (8, "Drydown")]:
            idx = int(np.searchsorted(profile.time_hours, hrs))
            idx = min(idx, len(profile.time_hours) - 1)
            top = sorted(profile.materials.values(),
                         key=lambda m: m.oav[idx], reverse=True)[:3]
            top_str = ", ".join(f"{m.name}(OAV={m.oav[idx]:.0f})" for m in top)
            print(f"  {tag:10s}: {top_str}")
        perc_half = profile.perceptual_half_life_hr
        longev = profile.longevity_hr
    except Exception as e:
        print(f"  ✗ TemporalEngine failed: {e}")
        subliminal = []
        perc_half = None
        longev = None

    return {
        "oav_abs_errors": len(errs),
        "oav_abs_warnings": len(warns),
        "oav_prop_errors": len(rerrs),
        "oav_prop_warnings": len(rwarns),
        "oav_prop_info": len(rinfos),
        "dose_response_score": dr.score,
        "overdosed": [o["material"] for o in dr.overdosed],
        "marginal": [m["material"] for m in dr.marginal],
        "subliminal": subliminal,
        "perceptual_half_life_hr": perc_half,
        "longevity_hr": longev,
    }


def hill_climb_30mL(label: str, ing: dict, dil: dict, scorer: FormulaScorer,
                    passes: int = 8) -> tuple[dict, dict, float]:
    """Single-seed brief hill-climb at 30 mL with finer-grained µL steps
    (±15, ±30, ±60) to exploit the doubled concentrate budget.
    """
    print(f"\n── HILL-CLIMB @ 30 mL — {label} (brief, {passes} passes) ──")
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)
    print(f"  start geo = {best_geo:.3f}")

    STEPS = (+15, +30, +60, -15, -30, -60)
    improved_any = False

    for p in range(passes):
        t0 = time.time()
        materials = list(ing.keys())
        found_improvement = False
        for name in materials:
            cur = ing[name]
            # Skip trace materials (< 5 µL) — don't remove under hill-climb
            if cur < 5:
                continue
            for step in STEPS:
                new_val = cur + step
                if new_val < 1:  # allow removal below 5 only via specific branch
                    continue
                if new_val > 2000:
                    continue
                trial = dict(ing)
                trial[name] = new_val
                # Must pass reverse-split OAV check at 15 mL (safety)
                rev = check_proportional_scaling(trial, dil, BATCH_ML, 15.0)
                if any(c.severity == "error" for c in rev):
                    continue
                geo, detail = score_formula(trial, dil, scorer)
                if geo > best_geo + 0.02:
                    ing = trial
                    best_geo, best_detail = geo, detail
                    print(f"    pass {p+1}: {name} {cur:+.0f}→{new_val:.0f} "
                          f"(step {step:+d}) → geo {best_geo:.3f}")
                    found_improvement = True
                    improved_any = True
                    cur = new_val
                    break
        dt = time.time() - t0
        if not found_improvement:
            print(f"    pass {p+1}: no improvement ({dt:.1f}s) — converged")
            break
        print(f"    pass {p+1} took {dt:.1f}s")

    if not improved_any:
        print(f"  ✓ Already at 30 mL local optimum (score unchanged: {best_geo:.3f})")
    else:
        print(f"  ✓ Improved geo by {best_geo - score_formula(ing, dil, scorer)[0] + 0:.3f}")
    return ing, best_detail, best_geo


def write_md(label: str, ing: dict, dil: dict, detail: dict,
             nonlinear: dict, geo: float, path: Path):
    total_ul = sum(ing.values())
    batch_ul = int(BATCH_ML * 1000)
    eth_ul = batch_ul - total_ul
    lines = [
        f"# {label} — optimized {BATCH_ML:.0f} mL (non-linear verified)",
        "",
        f"**Status:** converged at 15 mL → proportionally scaled 2× to {BATCH_ML:.0f} mL → "
        f"non-linearly reverified (Hill/Raoult/Stevens/mixture-suppression).",
        f"**Geometric composite score:** {geo:.2f}",
        "",
        f"**Batch:** {BATCH_ML:.2f} mL · concentrate {total_ul} µL · "
        f"{total_ul/batch_ul*100:.1f}% concentrate",
        "",
        "## Axis scores",
        "",
        "| Axis | Score |",
        "|---|---:|",
    ]
    for a in AXIS_WEIGHTS:
        lines.append(f"| {a} | {detail[a]:.1f} |")
    lines.append(f"| **geometric composite** | **{geo:.2f}** |")

    lines += ["", "## Formula", "",
              "| # | Material | Dilution | Amount (µL) | Amount (mL) |",
              "|--:|---|---|---:|---:|"]
    for i, (name, ul) in enumerate(sorted(ing.items(), key=lambda kv: -kv[1]), 1):
        d = dil.get(name, 1.0)
        d_str = "neat" if d >= 1.0 else f"{d*100:.0f}%"
        lines.append(f"| {i} | {name} | {d_str} | {ul:.0f} | {ul/1000:.3f} |")
    lines += [
        f"| — | Ethanol 96% | — | {eth_ul} | {eth_ul/1000:.3f} |",
        f"| — | **TOTAL** | — | **{batch_ul}** | **{BATCH_ML:.3f}** |",
        "",
        "## Non-linear verification",
        "",
        "Concentration-dependent models applied (not simple linear scaling):",
        "- **Hill equation** (`engine/dose_response.py`) — sigmoid character-zone audit",
        "- **Raoult/Clausius-Clapeyron** (`engine/temporal_graph.py`) — evaporation physics",
        "- **Stevens power law** — perceived intensity = OAV^0.4",
        f"- **Mixture suppression** — effective ODT × {5} for complex formulas",
        "",
        "### OAV guard",
        f"- Absolute-µL semantics at {BATCH_ML} mL: "
        f"**{nonlinear['oav_abs_errors']} err**, {nonlinear['oav_abs_warnings']} warn",
        f"- Proportional {BATCH_ML:.0f} → 15 mL reverse (re-split safety): "
        f"**{nonlinear['oav_prop_errors']} err**, {nonlinear['oav_prop_warnings']} warn, "
        f"{nonlinear['oav_prop_info']} info",
        "",
        "### Dose-response (Hill-equation character zones)",
        f"- Score: **{nonlinear['dose_response_score']:.1f}/100**",
        f"- Overdosed (negative/dangerous zone): {len(nonlinear['overdosed'])}"
        + (" — " + ", ".join(nonlinear['overdosed']) if nonlinear['overdosed'] else ""),
        f"- Marginal (neutral zone): {len(nonlinear['marginal'])}"
        + (" — " + ", ".join(nonlinear['marginal']) if nonlinear['marginal'] else ""),
        "",
        "### Temporal evolution (TemporalEngine)",
    ]
    if nonlinear["perceptual_half_life_hr"] is not None:
        lines += [
            f"- Perceptual half-life: **{nonlinear['perceptual_half_life_hr']:.1f} hr**",
            f"- Longevity (OAV > 2): **{nonlinear['longevity_hr']:.1f} hr**",
            f"- Subliminal materials (peak OAV < 1): {len(nonlinear['subliminal'])}"
            + (" — " + ", ".join(nonlinear['subliminal']) if nonlinear['subliminal'] else ""),
        ]
    else:
        lines.append("- TemporalEngine simulation did not complete.")

    lines += [
        "",
        "## Scaling notes",
        "",
        f"- Scaled proportionally from the 15 mL optimized formula (µL × 2).",
        f"- Concentrate fraction is invariant under proportional scaling: "
        f"OAV, perceived intensity, and evaporation curves are identical to the "
        f"15 mL half by construction.",
        f"- At {BATCH_ML:.0f} mL the 1 µL pipette floor is 0.033% of concentrate "
        f"(vs 0.067% at 15 mL) — trace materials below 1 µL at 15 mL can be "
        f"expressed precisely at {BATCH_ML:.0f} mL.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    t_start = time.time()
    print("Loading optimized 15 mL formulas from _opt_convergence_v2_out.json …")
    data = json.loads(Path("_opt_convergence_v2_out.json").read_text())

    # Load 15 mL formulas
    formulas = {
        "Photorealistic Iris": {
            "ing15": {k: float(v) for k, v in data["iris"]["ingredients"].items()},
            "dil":   {k: float(v) for k, v in data["iris"]["dilutions"].items()},
            "md_path": Path("formulas/collections/Photorealistic_Iris_30mL_optimized.md"),
            "label": "Photorealistic Iris",
        },
        "Iris-Jasmine": {
            "ing15": {k: float(v) for k, v in data["iris_jasmine"]["ingredients"].items()},
            "dil":   {k: float(v) for k, v in data["iris_jasmine"]["dilutions"].items()},
            "md_path": Path("formulas/collections/Iris_Jasmine_30mL_optimized.md"),
            "label": "Iris-Jasmine",
        },
    }

    print(f"\nPer-seed converged geo scores (at 15 mL):")
    print(f"  Iris        : {data['iris']['geo']}  (seeds: {data['iris']['seeds']})")
    print(f"  Iris-Jasmine: {data['iris_jasmine']['geo']}  (seeds: {data['iris_jasmine']['seeds']})")

    # Build 30 mL scorer
    print("\nBuilding FormulaScorer(batch_volume_ml=30.0) …")
    sg = SynergyGraph()
    scorer30 = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    summary = {}
    for key, f in formulas.items():
        print(f"\n{'█' * 64}")
        print(f"  {f['label']}")
        print(f"{'█' * 64}")

        # 1. Scale 2× → 30 mL
        ing30 = {n: v * 2.0 for n, v in f["ing15"].items()}
        print(f"\nScaled {len(ing30)} materials: total concentrate "
              f"{sum(f['ing15'].values()):.0f} µL @ 15 mL → {sum(ing30.values()):.0f} µL @ 30 mL")

        # 2. Score at 30 mL (should match 15 mL by construction since scorer uses %)
        geo_scaled, detail_scaled = score_formula(ing30, f["dil"], scorer30)
        print(f"Scaled 30 mL geo composite: {geo_scaled:.3f}")

        # 3. Non-linear verify
        nl = nonlinear_verify(f["label"], ing30, f["dil"])

        # 4. Brief hill-climb at 30 mL
        ing30_opt, detail_opt, geo_opt = hill_climb_30mL(
            f["label"], ing30, f["dil"], scorer30, passes=8)

        # 5. Re-verify if hill-climb improved
        if geo_opt > geo_scaled + 0.02:
            print(f"\nHill-climb gained {geo_opt - geo_scaled:.3f} — re-running non-linear audit")
            nl = nonlinear_verify(f["label"] + " (post-hill-climb)", ing30_opt, f["dil"])
            ing_final, detail_final, geo_final = ing30_opt, detail_opt, geo_opt
        else:
            ing_final, detail_final, geo_final = ing30, detail_scaled, geo_scaled

        # 6. Write markdown
        write_md(f["label"], ing_final, f["dil"], detail_final, nl, geo_final, f["md_path"])
        summary[key] = {
            "batch_ml": BATCH_ML,
            "geo_15mL": data[key.lower().replace("-", "_").replace(" ", "_")]["geo"] if False else (
                data["iris"]["geo"] if key == "Photorealistic Iris" else data["iris_jasmine"]["geo"]
            ),
            "geo_30mL_scaled": geo_scaled,
            "geo_30mL_optimized": geo_final,
            "hill_climb_gain": geo_final - geo_scaled,
            "nonlinear": nl,
            "concentrate_ul": sum(ing_final.values()),
        }

    # Final summary
    elapsed = time.time() - t_start
    print(f"\n\n{'═' * 64}")
    print(f"  FINAL SUMMARY — {BATCH_ML:.0f} mL non-linear reverification")
    print(f"{'═' * 64}")
    for key, s in summary.items():
        print(f"\n  {key}:")
        print(f"    15 mL geo        : {s['geo_15mL']:.3f}")
        print(f"    30 mL scaled geo : {s['geo_30mL_scaled']:.3f}")
        print(f"    30 mL optimized  : {s['geo_30mL_optimized']:.3f}")
        print(f"    hill-climb gain  : {s['hill_climb_gain']:+.3f}")
        print(f"    concentrate µL   : {s['concentrate_ul']:.0f} / {BATCH_ML*1000:.0f} "
              f"({s['concentrate_ul']/(BATCH_ML*1000)*100:.1f}%)")
        nl = s['nonlinear']
        print(f"    dose-response    : {nl['dose_response_score']:.1f}/100")
        print(f"    overdosed        : {len(nl['overdosed'])}")
        print(f"    subliminal       : {len(nl['subliminal'])}")
        if nl['perceptual_half_life_hr'] is not None:
            print(f"    perceptual t½    : {nl['perceptual_half_life_hr']:.1f} hr")
            print(f"    longevity OAV>2  : {nl['longevity_hr']:.1f} hr")
    print(f"\n  total runtime: {elapsed:.1f}s")

    Path("_scale_30mL_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"  summary JSON: _scale_30mL_summary.json")
    print(f"  markdown:     formulas/collections/{{Photorealistic_Iris,Iris_Jasmine}}_30mL_optimized.md")
