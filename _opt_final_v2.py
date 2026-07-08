"""Final optimization pass for both 30 mL formulas.

PHOTOREALISTIC IRIS (already in bottle, no ethanol yet):
  - Floor = 15 mL µL values (can't subtract — already added to bottle)
  - Ceiling DHM = 15 mL value (pinned — waxy-terpenic filler, dilute to half by
    adding more of other materials + ethanol)
  - Ceiling others = unbounded
  - Multi-pass hill-climb with broad step set; re-seed every 6 passes

IRIS-JASMINE (not yet made — full design freedom at 30 mL):
  - No Jasmine FO (pre-built FO is not character-correct; user built from
    jasmine-specific chemicals instead: Hedione, Hedione HC, Cis Jasmone,
    Benzyl Acetate, Methyl Benzoate, Methyl Anthranilate, Indole, Paradisamide,
    ACA, Ylang, Farnesol)
  - No Dihydromyrcenol (waxy-terpenic filler; not appropriate here)
  - Fresh seed configuration + multi-pass hill-climb
  - Floor = 0 for non-anchor materials, 1 µL for anchors

VALIDATION (both):
  - OAV guard (absolute-µL at 30 mL + proportional 30→15 mL reverse)
  - Hill dose-response (character-zone audit via CHARACTER_SHIFT_DATA)
  - TemporalEngine (Raoult/Clausius-Clapeyron + Stevens + mixture suppression)
  - IFRA-sensitive material flags (ACA, Indole, Farnesol)
"""
from __future__ import annotations
import io, json, os, sys, time
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

from _scale_30mL_verify_nonlinear import (
    score_formula, nonlinear_verify, write_md, BATCH_ML,
)

JSON_PATH = Path("_opt_convergence_v2_out.json")


# ═══════════════════════════════════════════════════════════════════════════════
# HILL-CLIMB with floor + ceiling + multi-pass
# ═══════════════════════════════════════════════════════════════════════════════
def hill_climb(label, ing, dil, scorer, floor, ceiling, passes=20):
    """Multi-pass hill-climb with ±15/30/60/120/240 steps."""
    print(f"\n── HILL-CLIMB — {label} ──")
    ing = dict(ing)
    best_geo, best_detail = score_formula(ing, dil, scorer)
    print(f"  start geo = {best_geo:.3f}  ({len(ing)} materials, "
          f"{sum(ing.values()):.0f} µL concentrate)")

    STEPS_BROAD = (+15, +30, +60, +120, +240, -15, -30, -60, -120)
    STEPS_FINE = (+15, +30, -15, -30)

    total_improved = False
    for p in range(passes):
        t0 = time.time()
        # Early passes: broad; late passes: fine
        steps = STEPS_BROAD if p < 8 else STEPS_FINE
        found = False
        for name in list(ing.keys()):
            cur = ing[name]
            fl = floor.get(name, 0.0)
            cl = ceiling.get(name, float("inf"))
            if fl >= cl - 0.5:  # pinned
                continue
            for step in steps:
                new_val = cur + step
                if new_val < fl - 0.5 or new_val > cl + 0.5:
                    continue
                if new_val < 1 or new_val > 2500:
                    continue
                trial = dict(ing)
                trial[name] = new_val
                rev = check_proportional_scaling(trial, dil, BATCH_ML, 15.0)
                if any(c.severity == "error" for c in rev):
                    continue
                geo, detail = score_formula(trial, dil, scorer)
                if geo > best_geo + 0.02:
                    ing = trial
                    best_geo, best_detail = geo, detail
                    print(f"    pass {p+1:2d}: {name:30s} {cur:>5.0f}→{new_val:<5.0f} "
                          f"(Δ{step:+d}) → geo {best_geo:.3f}")
                    found = True
                    total_improved = True
                    cur = new_val
                    break
        dt = time.time() - t0
        if not found:
            print(f"    pass {p+1:2d}: converged ({dt:.1f}s)")
            break
    print(f"  final geo = {best_geo:.3f}")
    return ing, best_detail, best_geo


# ═══════════════════════════════════════════════════════════════════════════════
# PHOTOREALISTIC IRIS — floor locked to 15 mL values
# ═══════════════════════════════════════════════════════════════════════════════
def process_iris():
    print(f"\n{'█' * 72}")
    print(f"  PHOTOREALISTIC IRIS  —  30 mL  —  all 15 mL concentrate already in bottle")
    print(f"{'█' * 72}")

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    ing15 = {k: float(v) for k, v in data["iris"]["ingredients"].items()}
    dil = {k: float(v) for k, v in data["iris"]["dilutions"].items()}
    print(f"  15 mL state: {len(ing15)} materials, "
          f"{sum(ing15.values()):.0f} µL concentrate, geo {data['iris']['geo']}")

    # Floor = exactly what's already in the bottle (can't go lower)
    # Start at the same µL (the bottle has 15 mL-worth of concentrate; ethanol
    # will bring to 30 mL). We are free to add MORE concentrate of any material
    # except DHM (pinned).
    PINNED = {"Dihydromyrcenol"}
    ing30 = dict(ing15)  # starting point = current bottle contents
    floor = {n: v for n, v in ing15.items()}
    ceiling = {n: (v if n in PINNED else float("inf")) for n, v in ing15.items()}

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
    baseline_geo, _ = score_formula(ing30, dil, scorer)
    print(f"  30 mL baseline (current bottle + ethanol fill): geo {baseline_geo:.3f}")
    print(f"  PINNED at 15 mL µL: {sorted(PINNED)}")
    print(f"  FLOOR = current bottle µL (cannot subtract)")

    # Multi-pass hill-climb with re-seed
    ing_best, detail_best, geo_best = hill_climb(
        "Photorealistic Iris (pass A)", ing30, dil, scorer, floor, ceiling, passes=20)

    # Re-optimize from the optimized point (second pass may find new local optima)
    print(f"\n── RE-SEED pass B ──")
    ing_best, detail_best, geo_best = hill_climb(
        "Photorealistic Iris (pass B)", ing_best, dil, scorer, floor, ceiling, passes=12)

    # Sanity: no floor/ceiling violation
    for n, v in ing_best.items():
        if v < floor[n] - 0.5:
            print(f"!! FLOOR VIOLATION: {n}={v} < {floor[n]}"); sys.exit(1)
        if v > ceiling[n] + 0.5:
            print(f"!! CEILING VIOLATION: {n}={v} > {ceiling[n]}"); sys.exit(1)
    for n in PINNED:
        if n in ing_best and abs(ing_best[n] - ing15[n]) > 0.5:
            print(f"!! {n} not pinned"); sys.exit(1)
    print(f"✓ No violations; DHM pinned at {ing15.get('Dihydromyrcenol', 0):.0f} µL")

    # Full non-linear verify
    nl = nonlinear_verify("Photorealistic Iris — 30 mL (final)", ing_best, dil)

    # Write outputs
    md = Path("formulas/collections/Photorealistic_Iris_30mL_optimized.md")
    write_md("Photorealistic Iris", ing_best, dil, detail_best, nl, geo_best, md)

    out = Path("_opt_final_iris.json")
    out.write_text(json.dumps({
        "ingredients": ing_best, "dilutions": dil,
        "geo": geo_best, "geo_baseline_30mL": baseline_geo,
        "geo_15mL": data["iris"]["geo"],
        "pinned": sorted(PINNED),
        "nonlinear": nl,
    }, indent=2), encoding="utf-8")
    print(f"\n  Summary (Photorealistic Iris 30 mL)")
    print(f"    15 mL geo                : {data['iris']['geo']:.3f}")
    print(f"    30 mL baseline (scaled)  : {baseline_geo:.3f}")
    print(f"    30 mL optimized          : {geo_best:.3f}")
    print(f"    Hill-climb gain          : {geo_best - baseline_geo:+.3f}")
    return ing_best, dil, geo_best


# ═══════════════════════════════════════════════════════════════════════════════
# IRIS-JASMINE — fresh design, no Jasmine FO, no DHM
# ═══════════════════════════════════════════════════════════════════════════════
def process_iris_jasmine():
    print(f"\n{'█' * 72}")
    print(f"  IRIS-JASMINE  —  30 mL  —  FRESH BUILD (no Jasmine FO, no DHM)")
    print(f"{'█' * 72}")

    # Chemical-built jasmine heart — NOT Jasmine FO
    # All amounts are µL at 30 mL batch; dilutions tracked in `dil`
    seed = {
        # ── Citrus/top ──
        "Bergamot FCF oil Sicilian":   320,
        "Cedrat FCF oil Sicilian":     120,
        "Ethyl Linalool":              140,
        # ── Green sparkle (minimal) ──
        "Allyl Amyl Glycolate":         20,
        "Leafovert":                    10,
        # ── IRIS CORE ──
        "Alpha Irone":                 720,   # 30% in DEP
        "Alpha Isomethyl Ionone":      340,
        "Alpha Ionone":                 90,
        "Beta Ionone":                  45,
        "Irotyl":                       90,
        "Orivone":                     140,
        "Ultralia":                     90,
        "Carrot Seed EO":               55,
        # ── JASMINE HEART (chemistry-built, not FO) ──
        "Hedione":                    1800,   # primary jasmine radiance + volume
        "Hedione HC":                  700,   # high-cis jasmine intensity
        "Cis Jasmone":                  35,   # jasmine ketone core (neat)
        "Methyl Benzoate":              90,   # jasmine ester lift
        "Benzyl Acetate":              140,   # classic jasmine ester body
        "Methyl Anthranilate":          40,   # grape-orange-blossom-jasmine
        "Indole":                       30,   # 10% dilution → 3 µL neat — animalic depth
        "Paradisamide":                 20,   # 10% dilution — fruity modifier
        "Amyl Cinnamic Aldehyde":      120,   # jasmine-muguet-waxy diffusant
        "Farnesol":                     15,   # neat — lily-muguet-jasmine fixative
        # ── Ylang support ──
        "Ylang Ylang EO (Extra grade)": 110,
        # ── Rose accent (subtle) ──
        "Phenethyl Alcohol":            80,
        "Geraniol":                     50,
        # ── Salicylate cushion (gradient: heavy + light) ──
        "Benzyl Salicylate":           560,
        "Hexyl Salicylate":            220,
        # ── Fixative acid ──
        "Myristic Acid":              1100,   # 20% — fixative/bloom anchor
        # ── Musk 3-axis chord ──
        "Ethylene Brassylate":         950,   # depth — creamy lactonic
        "Romandolide":                 230,   # projection
        "Ambrettolide":                340,   # 10% in DPG — natural-musk depth
        "Exaltolide":                  420,   # 10% — skin-fatty intimate
        "Musk Ketone":                 300,   # 10% solution — powder character echo
        # ── Wood/amber structure ──
        "Iso E Super":                 320,   # skin cocoon
        "Ebanol":                      380,   # creamy sandalwood
        "Koavone":                      60,
        "Ambrox Super":                260,   # 30% — crystalline mineral
        # ── Solvent / auxiliary ──
        "IPM":                         780,   # carrier (IPM-only solvent for some materials)
        "Benzyl Benzoate":              60,   # invisible fixative
    }
    dil = {
        "Alpha Irone":        0.30,
        "Myristic Acid":      0.20,
        "Indole":             0.10,
        "Paradisamide":       0.10,
        "Musk Ketone":        0.10,
        "Exaltolide":         0.10,
        "Ambrettolide":       0.10,
        "Ambrox Super":       0.30,
    }

    print(f"  Seed: {len(seed)} materials, {sum(seed.values()):.0f} µL concentrate "
          f"= {sum(seed.values())/300:.1f}% of 30 mL")
    print(f"  NO Jasmine FO  ·  NO Dihydromyrcenol")
    print(f"  Jasmine chemistry: Hedione/Hedione HC/Cis Jasmone/Benzyl Acetate/"
          f"Methyl Benzoate/Methyl Anthranilate/Indole/ACA/Paradisamide/Farnesol/Ylang")

    # Floor: 1 µL for all (meaningful minimum); free to grow
    ANCHORS = {"Hedione", "Alpha Irone", "Myristic Acid", "Ethylene Brassylate",
               "Benzyl Salicylate", "IPM"}
    floor = {n: (max(1.0, v * 0.5) if n in ANCHORS else 1.0) for n, v in seed.items()}
    ceiling = {n: float("inf") for n in seed}

    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
    base_geo, _ = score_formula(seed, dil, scorer)
    print(f"  Seed geo = {base_geo:.3f}")

    ing_best, detail_best, geo_best = hill_climb(
        "Iris-Jasmine (pass A)", seed, dil, scorer, floor, ceiling, passes=22)

    print(f"\n── RE-SEED pass B ──")
    ing_best, detail_best, geo_best = hill_climb(
        "Iris-Jasmine (pass B)", ing_best, dil, scorer, floor, ceiling, passes=14)

    print(f"\n── PASS C — fine-grained final polish ──")
    ing_best, detail_best, geo_best = hill_climb(
        "Iris-Jasmine (pass C)", ing_best, dil, scorer, floor, ceiling, passes=8)

    # Guardrails on IFRA-sensitive materials in final formula
    TOTAL_ML = 30.0
    ACA_ul = ing_best.get("Amyl Cinnamic Aldehyde", 0)
    ACA_pct = ACA_ul / (TOTAL_ML * 1000) * 100
    if ACA_pct > 1.0:
        print(f"  ⚠ ACA at {ACA_pct:.2f}% of final — IFRA cat 4 EDP limit is ~1-2% depending on skin-sens class")
    else:
        print(f"  ✓ ACA at {ACA_pct:.3f}% of final — within IFRA headroom")

    nl = nonlinear_verify("Iris-Jasmine — 30 mL (final)", ing_best, dil)

    md = Path("formulas/collections/Iris_Jasmine_30mL_optimized.md")
    write_md("Iris-Jasmine", ing_best, dil, detail_best, nl, geo_best, md)

    out = Path("_opt_final_iris_jasmine.json")
    out.write_text(json.dumps({
        "ingredients": ing_best, "dilutions": dil,
        "geo": geo_best, "geo_seed": base_geo,
        "nonlinear": nl,
        "notes": "Built from jasmine-specific chemicals — no Jasmine FO, no Dihydromyrcenol.",
    }, indent=2), encoding="utf-8")
    print(f"\n  Summary (Iris-Jasmine 30 mL)")
    print(f"    Seed geo       : {base_geo:.3f}")
    print(f"    Optimized geo  : {geo_best:.3f}  (Δ {geo_best - base_geo:+.3f})")


if __name__ == "__main__":
    t0 = time.time()
    process_iris()
    process_iris_jasmine()
    print(f"\n✓ Total wall time: {time.time() - t0:.1f}s")
