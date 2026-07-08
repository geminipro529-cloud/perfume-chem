"""Genre-aware citrus scoring + hedonism for 4 DHC formulas.

Uses engine FormulaScorer internally but applies citrus-aware corrections
to the star ratings and adds a hedonism/pleasure index.
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
from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer
from engine.formula_rating import compute_star_ratings, StarRatings, format_star_rating

PPM = 20.0

def get_vp_odt(name):
    p = get_profile(name)
    return (p.vp if p and p.vp else 0), (ODT_DATA.get(normalize_name(name), {}).get("odt_air") or 0)

def calc_oav(active, vp, odt):
    return active * vp * PPM / odt if vp and odt else 0.0

def analyze_oav(materials):
    rows = []
    for n, a in materials.items():
        vp, odt = get_vp_odt(n)
        if vp and odt:
            o = calc_oav(a, vp, odt)
            rows.append((n, a, vp, odt, o))
    total = sum(r[4] for r in rows)
    rows.sort(key=lambda x: x[4], reverse=True)
    return {"rows": rows, "total": total}

# ── FORMULA DEFINITIONS ──

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0, "Hedione": 900.0, "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0, "Linalyl Acetate": 120.0, "Petitgrain EO": 150.0,
    "Ambrofix": 10.8,
    "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

DHC_A_PCT = {
    "Lemon FCF oil Sicilian": 61.09, "Lime Distilled EO": 3.00,
    "Aldehyde C10 (1%)": 0.08, "Citral": 0.03, "Petitgrain EO": 0.80,
    "Hedione": 10.00, "Hedione HC": 2.00, "Ethyl Linalool": 4.00,
    "Linalyl Acetate": 2.00, "Dihydromyrcenol": 3.00, "Alpha Irone": 1.50,
    "Galaxolide": 8.00, "Habanolide": 2.00, "Ambrofix": 2.50,
}
STOCK = {"Aldehyde C10 (1%)": 0.01, "Alpha Irone": 0.30, "Galaxolide": 0.50, "Ambrofix": 0.30}
GOOD = set(DHC_A_PCT.keys())
BAD_EXISTING = {n: v for n, v in EXISTING.items() if n not in GOOD}

def build_corrected(target_mL):
    """Build corrected batch at target mL, scaled to exactly 12%."""
    existing_total = sum(EXISTING.values())
    target_active = 0.12 * target_mL * 1000
    add_needed = target_active - existing_total
    raw_additions = {m: max(0, DHC_A_PCT[m] / 100 * target_active - EXISTING.get(m, 0)) for m in DHC_A_PCT}
    raw_total = sum(raw_additions.values())
    scale = add_needed / raw_total if raw_total > 0 else 0
    added = {m: v * scale for m, v in raw_additions.items()}
    result = dict(EXISTING)
    for m, a in added.items():
        result[m] = result.get(m, 0.0) + a
    return result, added

def build_fresh(target_mL):
    """Build fresh DHC A at target mL."""
    target_active = 0.12 * target_mL * 1000
    return {m: target_active * pct / 100 for m, pct in DHC_A_PCT.items()}

# Define all 4 formulas
formulas = {
    "Original 30mL (your batch)": dict(EXISTING),
}
for v_mL in [83, 100]:
    corr, adds = build_corrected(v_mL)
    formulas[f"Corrected {v_mL}mL"] = corr
formulas["DHC A Lemon 100mL (fresh)"] = build_fresh(100)

# ── CUSTOM CITRUS SCORER ──

def rate_citrus(oav_analysis, formula_name, n_materials, total_active, volume_mL):
    """Rate a citrus perfume on 0-100 with genre awareness + hedonism."""
    rows = oav_analysis["rows"]
    total_oav = oav_analysis["total"]
    if total_oav == 0: return {}

    # Build material-level data
    mat_data = {r[0]: {"active": r[1], "vp": r[2], "odt": r[3], "oav": r[4]} for r in rows}
    oav_pct = {r[0]: r[4] / total_oav * 100 for r in rows}
    good_oav = sum(r[4] for r in rows if r[0] in GOOD)
    bad_oav = total_oav - good_oav
    bad_pct = bad_oav / total_oav * 100

    # ── FRESHNESS POTENCY ── how much of the OAV comes from fresh/citrus materials
    citrus_mats = {"Lemon FCF oil Sicilian", "Lime Distilled EO", "Aldehyde C10 (1%)",
                   "Citral", "Petitgrain EO", "Dihydromyrcenol", "Linalyl Acetate"}
    citrus_oav = sum(r[4] for r in rows if r[0] in citrus_mats)
    citrus_pct = citrus_oav / total_oav * 100 if total_oav else 0

    # ── CLEANLINESS ── how much of the OAV comes from clean/modern materials
    clean_mats = {"Galaxolide", "Habanolide", "Hedione", "Hedione HC", "Ethyl Linalool",
                  "Ambrofix", "Dihydromyrcenol"}
    clean_oav = sum(r[4] for r in rows if r[0] in clean_mats)
    clean_pct = clean_oav / total_oav * 100 if total_oav else 0

    # ── HEDONISM (pleasure index) ──
    # Freshness, radiance, clean musk, transparent materials = high hedonic
    # Heavy woody, animalic, smoky = low hedonic
    pleasant_mats = citrus_mats | clean_mats
    unpleasant_mats = {"Iso E Super", "Javanol", "Vetival", "Norlimbanol Dextro",
                       "Ethylene Brassylate", "Cardamom EO", "Dihydrojasmone"}
    pleasant_oav = sum(r[4] for r in rows if r[0] in pleasant_mats)
    unpleasant_oav = sum(r[4] for r in rows if r[0] in unpleasant_mats)
    hedonism = min(100, (pleasant_oav / total_oav) * 100 * 1.1 - (unpleasant_oav / total_oav) * 100 * 1.5)
    hedonism = max(0, hedonism)

    # ── CITRUS PURITY ── how close to a perfect citrus cologne
    # Penalize: too many base notes, too much bad OAV, oversweet, overweight
    purity = citrus_pct * 1.2  # baseline from citrus OAV share
    purity -= bad_pct * 0.8     # penalty for locked bad materials
    purity = max(0, min(100, purity))

    # ── LONGEVITY (citrus-adjusted) ──
    # For citrus: anything >4hr is good, >6hr is excellent
    # Check for fixatives (Galaxolide, Ambrofix, Hedione, Habanolide)
    fixative_active = sum(mat_data.get(m, {}).get("active", 0) for m in ["Galaxolide", "Ambrofix", "Habanolide"])
    hedione_active = mat_data.get("Hedione", {}).get("active", 0) if "Hedione" in mat_data else 0
    longevity_raw = min(100, 30 + fixative_active / 100 * 5 + hedione_active / 100 * 2)
    longevity = min(100, longevity_raw)

    # ── COMPLEXITY (citrus-adjusted) ──
    # For citrus: 8-15 materials is sweet spot, >15 is cluttered
    if 8 <= n_materials <= 15:
        complexity = 80
    elif 5 <= n_materials <= 20:
        complexity = 70 - abs(n_materials - 12) * 2
    else:
        complexity = max(20, 50 - abs(n_materials - 12) * 3)

    # ── BALANCE (citrus pyramid) ──
    # Citrus cologne ideal: 40% top, 35% heart, 25% base
    # Use OAV distribution as proxy
    top_oav = sum(r[4] for r in rows if r[0] in citrus_mats)
    base_oav = sum(r[4] for r in rows if r[0] in {"Iso E Super", "Ambrofix", "Romandolide",
                   "Ethylene Brassylate", "Norlimbanol Dextro", "Vetival", "Javanol", "Galaxolide", "Habanolide"})
    heart_oav = total_oav - top_oav - base_oav
    top_pct = top_oav / total_oav * 100 if total_oav else 0
    heart_pct = heart_oav / total_oav * 100 if total_oav else 0
    base_pct = base_oav / total_oav * 100 if total_oav else 0
    # Ideal for cologne: top 40%, heart 35%, base 25%
    # But actually citrus-heavy formulas naturally have more top, so adjust:
    # For a 12% concentrate, 61% lemon means ~7.3% of the bottle is lemon.
    # The headspace OAV of lemon dominates. So "balance" for citrus means
    # the other layers are present and perceptible.
    if heart_pct > 5 and base_pct > 2:
        balance = 80 + min(15, heart_pct * 0.5 + base_pct * 0.8)
    elif heart_pct > 2:
        balance = 60 + heart_pct * 3
    else:
        balance = 40 + heart_pct * 3 + base_pct * 5
    balance = min(100, max(10, balance))

    # ── SILLAGE (projection) ──
    # High DHM, Hedione, Linalyl Acetate = good projection
    proj_mats = {"Dihydromyrcenol", "Hedione", "Linalyl Acetate", "Citral"}
    proj_oav = sum(r[4] for r in rows if r[0] in proj_mats)
    proj_pct = proj_oav / total_oav * 100 if total_oav else 0
    sillage = min(100, proj_pct * 1.2 + citrus_pct * 0.3)

    # ── TRANSPARENCY ──
    # Modern citrus cologne should be transparent, not syrupy
    transparent_mats = {"Dihydromyrcenol", "Habanolide", "Hedione", "Ethyl Linalool",
                        "Aldehyde C10 (1%)", "Galaxolide"}
    transp_oav = sum(r[4] for r in rows if r[0] in transparent_mats)
    transp_pct = transp_oav / total_oav * 100 if total_oav else 0
    transparency = min(100, transp_pct * 1.0 + 20)

    # ── RADIANCE (halo effect) ──
    radiance_mats = {"Hedione", "Hedione HC", "Ethyl Linalool", "Galaxolide", "Dihydromyrcenol"}
    rad_oav = sum(r[4] for r in rows if r[0] in radiance_mats)
    rad_pct = rad_oav / total_oav * 100 if total_oav else 0
    radiance = min(100, rad_pct * 1.1 + 10)

    # ── SYNERGY ──
    # Citrus + Hedione + DHM + Galaxolide + Ambrofix = classic cologne stack
    stack_present = all(m in mat_data for m in ["Lemon FCF oil Sicilian", "Hedione", "Dihydromyrcenol", "Galaxolide"] if m in mat_data)
    synergy = 85 if stack_present else 55

    # ── COST (higher score = cheaper) ──
    # Lemon FCF is cheap, most synthetics are moderate
    cost_score = 50  # baseline
    if "Alpha Irone" in mat_data and mat_data["Alpha Irone"]["active"] > 100:
        cost_score -= 5
    if "Ambrofix" in mat_data and mat_data["Ambrofix"]["active"] > 200:
        cost_score -= 5

    # ── GEOMETRIC MEAN ──
    axes = {
        "freshness": citrus_pct * 0.8 + 10,
        "longevity": longevity,
        "sillage": sillage,
        "balance": balance,
        "complexity": complexity,
        "transparency": transparency,
        "radiance": radiance,
        "synergy": synergy,
        "purity": purity,
    }
    for k in axes:
        axes[k] = max(5, min(100, axes[k]))

    weights = {
        "freshness": 1.5, "longevity": 0.6, "sillage": 0.8,
        "balance": 1.0, "complexity": 0.5, "transparency": 1.2,
        "radiance": 1.0, "synergy": 0.8, "purity": 1.2,
    }
    total_w = sum(weights.values())
    log_sum = sum(w * math.log(v) for k, v in axes.items() if v > 0 for kw, w in [(k, weights[k])] if k in weights)
    geometric = round(math.exp(log_sum / total_w), 1)

    # ── 10-STAR RATINGS (citrus-adjusted) ──
    f = citrus_pct * 0.8 + 10  # freshness axis value
    stars = {
        "Wearability": min(10, 6.5 + f / 100 * 3),
        "Versatility": min(10, 3 + hedonism / 100 * 4 + f / 100 * 3),
        "Originality": min(10, 5 + (1 - bad_pct / 100) * 3 - abs(n_materials - 12) * 0.15),
        "Sophistication": min(10, 3 + balance / 100 * 4 + synergy / 100 * 3),
        "Signature Potential": min(10, 5 + hedonism / 100 * 3 + radiance / 100 * 2),
        "Mass Appeal": min(10, 5 + f / 100 * 3 + hedonism / 100 * 2),
        "Gender Versatility": min(10, 7 + f / 100 * 2 - bad_pct / 100 * 2),
        "Age Range": min(10, 7 + f / 100 * 2),
        "Formula Elegance": min(10, 4 + balance / 100 * 3 + synergy / 100 * 3),
        "Value For Money": min(10, 5 + longevity / 100 * 2 + sillage / 100 * 2),
    }

    return {
        "axes": axes,
        "weights": weights,
        "geometric": geometric,
        "stars": stars,
        "hedonism": round(hedonism, 1),
        "citrus_purity": round(purity, 1),
        "citrus_oav_pct": round(citrus_pct, 1),
        "clean_oav_pct": round(clean_pct, 1),
        "bad_oav_pct": round(bad_pct, 1),
        "top_pct": round(top_pct, 1),
        "heart_pct": round(heart_pct, 1),
        "base_pct": round(base_pct, 1),
        "n_materials": n_materials,
        "total_active": round(total_active, 1),
        "volume_mL": volume_mL,
        "concentration_pct": round(total_active / (volume_mL * 1000) * 100, 1),
    }

# ── RUN ──

results = {}
for name, mats in formulas.items():
    vol = 100 if "fresh" in name.lower() else (float(name.split(" ")[1].replace("mL","")) if "mL" in name and name.split(" ")[1].replace("mL","").isdigit() else 31.4)
    if "Original" in name: vol = 31.4
    if "fresh" in name.lower(): vol = 100

    oav = analyze_oav(mats)
    r = rate_citrus(oav, name, len(mats), sum(mats.values()), vol)
    results[name] = r

# ── PRINT ──

print("=" * 90)
print("  CITRUS-AWARE SCORING + HEDONISM")
print("  Genre-adjusted for citrus colognes (transparency, freshness, radiance)")
print("=" * 90)

for name, r in sorted(results.items(), key=lambda x: x[1].get("geometric", 0), reverse=True):
    print()
    print("-" * 90)
    print(f"  {name}")
    print(f"  {r['n_materials']} materials | {r['total_active']:.0f} uL active | {r['concentration_pct']:.1f}% v/v | {r['volume_mL']:.0f} mL")
    print("-" * 90)

    print(f"  HEDONISM:        {r['hedonism']:>5.1f}/100  (pleasure/pleasantness index)")
    print(f"  CITRUS PURITY:   {r['citrus_purity']:>5.1f}/100  (how close to ideal citrus cologne)")
    print(f"  BAD OAV:         {r['bad_oav_pct']:>5.1f}%       (locked materials altering profile)")
    print(f"  CITRUS OAV:      {r['citrus_oav_pct']:>5.1f}%     (of total headspace)")
    print(f"  CLEAN OAV:       {r['clean_oav_pct']:>5.1f}%     (modern/clean materials)")
    print(f"  PYRAMID:         {r['top_pct']:.0f}%T / {r['heart_pct']:.0f}%H / {r['base_pct']:.0f}%B")

    print(f"\n  AXIS             SCORE")
    print(f"  {'-'*20}  {'-'*6}")
    for ax in ["freshness", "transparency", "radiance", "balance", "longevity",
               "sillage", "purity", "synergy", "complexity"]:
        s = r["axes"][ax]
        bar = "#" * int(s / 5) + "-" * (20 - int(s / 5))
        print(f"  {ax:<20} {s:>5.1f}  {bar}")

    print(f"\n  GEOMETRIC TOTAL: {r['geometric']:>5.1f}/100  (citrus-weighted)")

    print(f"\n  10-STAR RATINGS (citrus-adjusted)")
    star_avg = sum(r["stars"].values()) / len(r["stars"])
    for k, v in sorted(r["stars"].items(), key=lambda x: x[1], reverse=True):
        bar = "#" * int(v) + "-" * (10 - int(v))
        print(f"    {k:<22} {v:>4.1f}/10  {bar}")
    print(f"    {'OVERALL':<22} {star_avg:>4.1f}/10")

print()
print("=" * 90)
print("  RANKING BY GEOMETRIC TOTAL")
print("-" * 90)
for rank, (name, r) in enumerate(sorted(results.items(), key=lambda x: x[1].get("geometric", 0), reverse=True), 1):
    s = r["stars"]
    s_avg = sum(s.values()) / len(s)
    print(f"  #{rank}  {name:<30}  Geometric: {r['geometric']:>5.1f}  Hedonism: {r['hedonism']:>5.1f}  Stars: {s_avg:.1f}/10")
    print(f"      Citrus: {r['citrus_oav_pct']:.0f}%  Clean: {r['clean_oav_pct']:.0f}%  Bad: {r['bad_oav_pct']:.0f}%  Pyramid: {r['top_pct']:.0f}T/{r['heart_pct']:.0f}H/{r['base_pct']:.0f}B")
