"""DHC Compare — Full OAV + Scoring analysis of Correction vs Fresh 100mL batches.

Runs:
  1. Headspace OAV for both formulas (simplified: active * VP * 20 / ODT_air)
  2. Engine FormulaScorer multi-axis scoring
  3. 10-star consumer ratings
  4. Side-by-side comparison report
"""
from __future__ import annotations
import sys, math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.odor_thresholds import ODT_DATA
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.formula_rating import compute_star_ratings, format_star_rating

PPM = 20.0

def get_vp_odt(name: str):
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0.0
    n = normalize_name(name)
    odt = ODT_DATA.get(n, {}).get("odt_air")
    return vp, odt

def calc_oav(active: float, vp: float, odt: float) -> float:
    return active * vp * PPM / odt if vp and odt else 0.0

def analyze_oav(materials: dict[str, float]) -> dict:
    """Return {name: oav, total, sorted list}."""
    rows = []
    total = 0.0
    for name, active in materials.items():
        vp, odt = get_vp_odt(name)
        if vp and odt:
            val = calc_oav(active, vp, odt)
        else:
            val = 0.0
        rows.append((name, active, vp, odt, val))
        total += val
    rows.sort(key=lambda x: x[4], reverse=True)
    return {"rows": rows, "total": total}

def build_formula_vector(active_materials: dict[str, float]) -> FormulaVector:
    """Build FormulaVector from active µL amounts (converted to % of concentrate)."""
    total_active = sum(active_materials.values())
    pct = {name: (active / total_active) * 100.0 for name, active in active_materials.items()}
    return FormulaVector(ingredients=pct, dilutions={})

def score_formula(fv: FormulaVector, name: str):
    scorer = FormulaScorer()
    scores = scorer.score(fv)
    # Bridge legacy keys if missing
    if "theory" not in scores and "synergy" in scores:
        scores["theory"] = scores["synergy"]
    if "complexity" not in scores and "stacking_depth" in scores:
        scores["complexity"] = scores["stacking_depth"]
    if "cost" not in scores:
        scores["cost"] = scores.get("luxury", 50.0)
    if "balance" not in scores:
        radar = scores.get("_radar", {})
        vals = [v for v in radar.values() if isinstance(v, (int, float))]
        if vals:
            mean_r = sum(vals) / len(vals)
            deviation = sum(abs(v - mean_r) for v in vals) / len(vals)
            scores["balance"] = max(0, min(100, 100 - deviation * 12))
        else:
            scores["balance"] = 50.0
    if "radiance" not in scores:
        radar = scores.get("_radar", {})
        scores["radiance"] = radar.get("radiance", 5.0) * 10.0
    if "character_balance" not in scores:
        scores["character_balance"] = scores.get("balance", 50.0)

    stars = compute_star_ratings(fv, scores, scores.get("_radar", {}))
    return scores, stars

# ═══════════════════════════════════════════════════════════════════════════════
# FORMULA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Existing 30mL DHC VII Lemon Lemonade (scaled x0.6 from 50mL) ──
EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0,
    "Hedione": 900.0,
    "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0,
    "Linalyl Acetate": 120.0,
    "Petitgrain EO": 150.0,
    "Ethyl Maltol": 1.8,
    "Dihydrojasmone": 30.0,
    "Aurantiol": 9.0,
    "Mayol": 8.4,
    "Nympheal": 3.6,
    "Scentenal": 0.012,
    "Floralozone": 0.06,
    "Ambrofix": 10.8,
    # Locked bad materials
    "Iso E Super": 300.0,
    "Romandolide": 288.0,
    "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2,
    "Vetival": 24.0,
    "Javanol": 9.6,
    "Cardamom EO": 3.0,
}

# ── Correction additions to reach DHC A target at 100mL ──
ADDITIONS = {
    "Lemon FCF oil Sicilian": 3130.8,
    "Lime Distilled EO": 360.0,
    "Aldehyde C10 (1%)": 9.6,
    "Citral": 3.6,
    "Hedione": 300.0,
    "Ethyl Linalool": 150.0,
    "Linalyl Acetate": 120.0,
    "Dihydromyrcenol": 360.0,
    "Alpha Irone": 180.0,
    "Galaxolide": 960.0,
    "Habanolide": 240.0,
    "Ambrofix": 289.2,
}

# Scale additions so final concentration = 12% (12,000 uL active in 100mL)
# Existing active = 7,001.5 uL, locked bad = 930.7 uL, good existing = 6,070.8 uL
# Need total additions such that: 7,001.5 + additions = 12,000
TARGET_TOTAL_ACTIVE = 12000.0
existing_total = sum(EXISTING.values())
additions_total = sum(ADDITIONS.values())
scale = (TARGET_TOTAL_ACTIVE - existing_total) / additions_total
scale = max(0.0, scale)

SCALED_ADDITIONS = {mat: add * scale for mat, add in ADDITIONS.items()}

# Build corrected batch (100mL total volume at 12%)
CORRECTED = dict(EXISTING)
for mat, add in SCALED_ADDITIONS.items():
    CORRECTED[mat] = CORRECTED.get(mat, 0.0) + add

# ── Fresh DHC A Lemon 100mL (12% v/v = 12,000 µL active) ──
FRESH = {
    "Lemon FCF oil Sicilian": 12000 * 61.09 / 100,   # 7330.8
    "Lime Distilled EO": 12000 * 3.00 / 100,         # 360.0
    "Aldehyde C10 (1%)": 12000 * 0.08 / 100,         # 9.6
    "Citral": 12000 * 0.03 / 100,                    # 3.6
    "Petitgrain EO": 12000 * 0.80 / 100,             # 96.0
    "Hedione": 12000 * 10.00 / 100,                 # 1200.0
    "Hedione HC": 12000 * 2.00 / 100,               # 240.0
    "Ethyl Linalool": 12000 * 4.00 / 100,           # 480.0
    "Linalyl Acetate": 12000 * 2.00 / 100,          # 240.0
    "Dihydromyrcenol": 12000 * 3.00 / 100,          # 360.0
    "Alpha Irone": 12000 * 1.50 / 100,              # 180.0
    "Galaxolide": 12000 * 8.00 / 100,               # 960.0
    "Habanolide": 12000 * 2.00 / 100,               # 240.0
    "Ambrofix": 12000 * 2.50 / 100,                 # 300.0
}

# Actual batch volume (user added 24 mL ethanol to ~7.1 mL raw concentrate)
EXISTING_RAW_ML = sum([
    250.0 * 0.6, 600.0 * 0.6, 1500.0 * 0.6, 600.0 * 0.6, 550.0 * 0.6,
    30.0 * 0.6, 50.0 * 0.6, 150.0 * 0.6, 14.0 * 0.6, 6.0 * 0.6,
    2.0 * 0.6, 1.5 * 0.6, 500.0 * 0.6, 480.0 * 0.6, 380.0 * 0.6,
    60.0 * 0.6, 42.0 * 0.6, 40.0 * 0.6, 16.0 * 0.6, 5.0 * 0.6, 7000.0 * 0.6,
]) / 1000.0  # ≈ 7.126 mL
EXISTING_ETHANOL_ML = 24.0
EXISTING_VOLUME_ML = EXISTING_RAW_ML + EXISTING_ETHANOL_ML  # ≈ 31.1 mL

STOCK_DILUTION = {
    "Aldehyde C10 (1%)": 0.01,
    "Alpha Irone": 0.30,
    "Galaxolide": 0.50,
    "Ambrofix": 0.30,
}

def total_raw_volume(materials: dict[str, float]) -> float:
    raw = 0.0
    for name, active in materials.items():
        stock_frac = STOCK_DILUTION.get(name, 1.0)
        raw += active / stock_frac
    return raw / 1000.0  # mL

ADDITIONS_RAW_ML = total_raw_volume(SCALED_ADDITIONS)
FRESH_RAW_ML = total_raw_volume(FRESH)

GOOD_MATS = set(FRESH.keys())

# ═══════════════════════════════════════════════════════════════════════════════
# RUN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    oav_corrected = analyze_oav(CORRECTED)
    oav_fresh = analyze_oav(FRESH)

    fv_corrected = build_formula_vector(CORRECTED)
    fv_fresh = build_formula_vector(FRESH)

    scores_corrected, stars_corrected = score_formula(fv_corrected, "CORRECTED")
    scores_fresh, stars_fresh = score_formula(fv_fresh, "FRESH")

    # ── Print Report ──
    print("=" * 90)
    print("  DHC LEMON 100mL — CORRECTION vs FRESH")
    print("  Full OAV + Engine Scoring + 10-Star Ratings")
    print("=" * 90)

    # Formula stats
    total_corr = sum(CORRECTED.values())
    total_fresh = sum(FRESH.values())
    print(f"\n  {'Metric':<30} {'CORRECTED':>25} {'FRESH':>25}")
    print("  " + "-" * 82)
    print(f"  {'Total active µL':<30} {total_corr:>24.1f} {total_fresh:>24.1f}")
    print(f"  {'Total volume mL':<30} {'100.0':>25} {'100.0':>25}")
    print(f"  {'Concentration % v/v':<30} {total_corr/1000:>24.1f}% {total_fresh/1000:>24.1f}%")
    print(f"  {'Unique materials':<30} {len(CORRECTED):>25} {len(FRESH):>25}")
    print(f"  {'Existing batch volume':<30} {EXISTING_VOLUME_ML:>24.1f} {'N/A':>25}")
    print(f"  {'Stock additions mL':<30} {ADDITIONS_RAW_ML:>24.1f} {FRESH_RAW_ML:>24.1f}")
    ethanol_corr = 100.0 - EXISTING_VOLUME_ML - ADDITIONS_RAW_ML
    ethanol_fresh = 100.0 - FRESH_RAW_ML
    print(f"  {'Ethanol 96% to add mL':<30} {ethanol_corr:>24.1f} {ethanol_fresh:>24.1f}")

    # OAV Summary
    print(f"\n  {'HEADSPACE OAV SUMMARY':<30}")
    print("  " + "-" * 82)
    print(f"  {'Total OAV':<30} {oav_corrected['total']:>24,.0f} {oav_fresh['total']:>24,.0f}")

    good_corr = sum(v for n, a, vp, odt, v in oav_corrected["rows"] if n in GOOD_MATS)
    bad_corr = oav_corrected["total"] - good_corr
    good_fresh = sum(v for n, a, vp, odt, v in oav_fresh["rows"] if n in GOOD_MATS)
    bad_fresh = oav_fresh["total"] - good_fresh

    print(f"  {'Good OAV % (DHC A mats)':<30} {good_corr/oav_corrected['total']*100:>24.1f}% {good_fresh/oav_fresh['total']*100:>24.1f}%")
    print(f"  {'Bad OAV % (locked extras)':<30} {bad_corr/oav_corrected['total']*100:>24.1f}% {bad_fresh/oav_fresh['total']*100:>24.1f}%")

    # Top 8 OAV materials
    print(f"\n  {'TOP 8 HEADSPACE OAV MATERIALS':<30}")
    print("  " + "-" * 82)
    print(f"  {'#':<3} {'Material':<26} {'CORRECTED OAV':>20} {'%':>6} {'FRESH OAV':>20} {'%':>6}")
    print("  " + "-" * 82)
    corr_rows = oav_corrected["rows"]
    fresh_rows = oav_fresh["rows"]
    fresh_dict = {n: v for n, a, vp, odt, v in fresh_rows}
    fresh_total = oav_fresh["total"]
    corr_total = oav_corrected["total"]

    for i in range(8):
        nc, ac, vpc, odtc, vc = corr_rows[i] if i < len(corr_rows) else ("", 0, 0, 0, 0)
        pc = vc / corr_total * 100 if corr_total else 0
        vf = fresh_dict.get(nc, 0)
        pf = vf / fresh_total * 100 if fresh_total else 0
        marker = " OK" if nc in GOOD_MATS else " XX"
        print(f"  {i+1:<3} {nc:<24} {vc:>20,.0f} {pc:>6.1f}% {vf:>20,.0f} {pf:>6.1f}%{marker}")

    # Show locked bad materials in corrected
    print(f"\n  {'LOCKED BAD MATERIALS (CORRECTED ONLY)':<30}")
    print("  " + "-" * 82)
    for name, active, vp, odt, val in corr_rows:
        if name not in GOOD_MATS:
            pc = val / corr_total * 100
            print(f"  {'':3} {name:<24} {val:>20,.0f} {pc:>6.1f}% XX")

    # Scores
    axes = ["longevity", "sillage", "balance", "theory", "radiance",
            "texture", "complexity", "character_balance", "synergy", "cost"]
    print(f"\n  {'MULTI-AXIS SCORES (0-100)':<30}")
    print("  " + "-" * 82)
    print(f"  {'Axis':<20} {'CORRECTED':>25} {'FRESH':>25}")
    print("  " + "-" * 82)
    for ax in axes:
        sc = scores_corrected.get(ax, 0)
        sf = scores_fresh.get(ax, 0)
        bar_c = "#" * int(sc / 5) + "-" * (20 - int(sc / 5))
        bar_f = "#" * int(sf / 5) + "-" * (20 - int(sf / 5))
        print(f"  {ax:<20} {bar_c} {sc:>5.1f}  {bar_f} {sf:>5.1f}")

    geom_c = scores_corrected.get("geometric_total", 0)
    geom_f = scores_fresh.get("geometric_total", 0)
    arith_c = scores_corrected.get("arithmetic_total", 0)
    arith_f = scores_fresh.get("arithmetic_total", 0)
    print(f"\n  {'GEOMETRIC TOTAL':<20} {'':25} {geom_c:>25.1f} {geom_f:>25.1f}")
    print(f"  {'ARITHMETIC TOTAL':<20} {'':25} {arith_c:>25.1f} {arith_f:>25.1f}")

    # Star ratings
    print(f"\n  {'10-STAR CONSUMER RATINGS':<30}")
    print("  " + "-" * 82)
    print(f"  {'Characteristic':<25} {'CORRECTED':>28} {'FRESH':>28}")
    print("  " + "-" * 82)
    for key in stars_corrected.as_dict():
        sc = stars_corrected.as_dict()[key]
        sf = stars_fresh.as_dict()[key]
        print(f"  {key.replace('_', ' ').title():<25} {sc:>6.1f}/10{'':>22} {sf:>6.1f}/10")
    print(f"\n  {'OVERALL':<25} {stars_corrected.average():>6.1f}/10{'':>22} {stars_fresh.average():>6.1f}/10")

    # Radar
    radar_c = scores_corrected.get("_radar", {})
    radar_f = scores_fresh.get("_radar", {})
    if radar_c or radar_f:
        print(f"\n  {'CHARACTER RADAR (0-10)':<30}")
        print("  " + "-" * 82)
        print(f"  {'Dimension':<18} {'CORRECTED':>30} {'FRESH':>30}")
        print("  " + "-" * 82)
        all_dims = sorted(set(list(radar_c.keys()) + list(radar_f.keys())))
        for dim in all_dims:
            vc = radar_c.get(dim, 0)
            vf = radar_f.get(dim, 0)
            bar_c = "#" * int(vc) + "-" * (10 - int(vc))
            bar_f = "#" * int(vf) + "-" * (10 - int(vf))
            print(f"  {dim:<18} {bar_c} {vc:>5.1f}  {bar_f} {vf:>5.1f}")

    # Verdict
    print(f"\n{'='*90}")
    print("  VERDICT")
    print("="*90)
    print(f"\n  CORRECTED (existing {EXISTING_VOLUME_ML:.1f}mL + additions -> 100mL)")
    print(f"    • Concentration: {total_corr/1000:.1f}% v/v (scaled additions to hit 12%)")
    print(f"    • Good OAV: {good_corr/oav_corrected['total']*100:.1f}% | Bad OAV: {bad_corr/oav_corrected['total']*100:.1f}%")
    print(f"    • Geometric score: {geom_c:.1f} | Stars: {stars_corrected.average():.1f}/10")
    print(f"    • Identity: Sweet woody lemon with iris heart (unique, not pure DHC)")

    print(f"\n  FRESH (mixed from scratch -> 100mL)")
    print(f"    • Concentration: {total_fresh/1000:.1f}% v/v (exact target)")
    print(f"    • Good OAV: {good_fresh/oav_fresh['total']*100:.1f}% | Bad OAV: {bad_fresh/oav_fresh['total']*100:.1f}%")
    print(f"    • Geometric score: {geom_f:.1f} | Stars: {stars_fresh.average():.1f}/10")
    print(f"    • Identity: True DHC flanker -- citrus -> iris -> clean musk")

    print(f"\n  RECOMMENDATION:")
    if geom_f > geom_c + 5 and stars_fresh.average() > stars_corrected.average() + 0.3:
        print(f"    Mix the FRESH batch. It scores significantly higher on both")
        print(f"    technical composition (+{geom_f-geom_c:.1f} geometric) and consumer appeal")
        print(f"    (+{stars_fresh.average()-stars_corrected.average():.1f} stars).")
        print(f"    The corrected batch carries too much locked baggage.")
    elif geom_f > geom_c:
        print(f"    The FRESH batch is technically superior (+{geom_f-geom_c:.1f} geometric),")
        print(f"    but both are viable. If you value the unique 'lemonade' character")
        print(f"    of your existing batch, keep it as a distinct creation and mix fresh.")
    else:
        print(f"    Both batches are comparable. Choose based on material availability")
        print(f"    and whether you want to preserve the existing batch's character.")
    print()

if __name__ == "__main__":
    main()
