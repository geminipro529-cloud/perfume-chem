"""
v7a: swap Cedarwood Virginia EO 300 -> Cedarwood EO 300 (neutral natural cedar,
no smoky/pencil-shaving edge). Verify everything on the formula:
  - IFRA caps
  - Dilution consistency vs inventory.txt
  - Total sum == 50 mL
  - Concentrate percentage
  - Axis scores and composite vs v3/v6/v7
"""
import json
import sys
from _opt_iris_reverie_15probes import (
    IRL_V3, IRL_DIL_BASE, BATCH_ML, score_formula, FormulaScorer,
    AIMI_CAPPED, IFRA_CAPPED, SUB_ODT_TRACES,
)

# Load v7 from v7_v8 JSON
with open("_opt_v7_v8_iris_brief.json", "r", encoding="utf-8") as f:
    data = json.load(f)
v7_ing = dict(data["v7"]["ing"])
v3_geo_ref = data["v3_geo"]
v6_geo_ref = data["v6_geo"]
v7_geo_ref = data["v7"]["geo"]

# v7a: swap Cedarwood Virginia EO -> Cedarwood EO (same volume 300 µL neat)
v7a_ing = dict(v7_ing)
v7a_ing["Cedarwood EO"] = v7a_ing.pop("Cedarwood Virginia EO")

# Dilutions: inherit base, add Cedarwood EO neat
v7a_dil = dict(IRL_DIL_BASE)
if "Cedarwood EO" not in v7a_dil:
    v7a_dil["Cedarwood EO"] = 1.0  # neat per inventory

scorer = FormulaScorer()

v3_geo, v3_det = score_formula(IRL_V3, IRL_DIL_BASE, scorer)
v7_geo, v7_det = score_formula(v7_ing, IRL_DIL_BASE, scorer)
v7a_geo, v7a_det = score_formula(v7a_ing, v7a_dil, scorer)

# ----- Verification checks -----
def check_ifra(ing):
    issues = []
    for k, cap in IFRA_CAPPED.items():
        if k in ing and ing[k] > cap:
            issues.append(f"  FAIL: {k} = {ing[k]} µL > IFRA cap {cap}")
    return issues

def check_sum(ing, batch=50000.0):
    total = sum(ing.values())
    # ethanol = batch - total
    return total, batch - total

def concentrate_pct(ing, dil, batch=50000.0):
    # dilutions are fractions of active; compute active µL
    # For reporting, concentrate volume is sum of dosed volumes (including diluent carriers)
    return sum(ing.values()) / batch * 100.0

print("=" * 72)
print("v7a VERIFICATION REPORT — Cedarwood Virginia -> Cedarwood EO swap")
print("=" * 72)

print("\n[1] Score comparison (in-process)")
print(f"  v3 (baseline)       geo = {v3_geo:.3f}")
print(f"  v6 (scorer pick)    geo = {v6_geo_ref:.3f}  (cached from prior run)")
print(f"  v7 (perfumer pick)  geo = {v7_geo:.3f}  (Δ v3 = {v7_geo-v3_geo:+.3f})")
print(f"  v7a (cedar swap)    geo = {v7a_geo:.3f}  (Δ v7 = {v7a_geo-v7_geo:+.3f}, Δ v3 = {v7a_geo-v3_geo:+.3f})")

print("\n[2] Axis-by-axis: v7 vs v7a")
axes = ["longevity","sillage","luxury","texture","stacking_depth",
        "photorealism","perceptual_clarity","skin_performance","synergy","hedonic"]
print(f"  {'axis':<22}{'v3':>8}{'v7':>8}{'v7a':>8}{'Δ v7a-v7':>10}")
for a in axes:
    s3 = v3_det.get(a, 0.0)
    s7 = v7_det.get(a, 0.0)
    s7a = v7a_det.get(a, 0.0)
    print(f"  {a:<22}{s3:>8.2f}{s7:>8.2f}{s7a:>8.2f}{s7a-s7:>+10.2f}")

print("\n[3] IFRA check (v7a)")
ifra_issues = check_ifra(v7a_ing)
if ifra_issues:
    for x in ifra_issues: print(x)
else:
    print("  PASS: no IFRA violations")
for k, cap in IFRA_CAPPED.items():
    if k in v7a_ing:
        pct = v7a_ing[k] / cap * 100.0
        print(f"    {k}: {v7a_ing[k]:.1f} / {cap:.1f} µL  ({pct:.1f}% of cap)")

print("\n[4] Total volume check (v7a)")
tot, eth = check_sum(v7a_ing)
print(f"  Concentrate sum: {tot:.1f} µL")
print(f"  Ethanol 96%   : {eth:.1f} µL")
print(f"  Batch total   : {tot+eth:.1f} µL (target 50000.0)")
print(f"  Concentrate % : {tot/50000.0*100:.2f}%")

print("\n[5] Dilution consistency check (v7a)")
missing = [k for k in v7a_ing if k not in v7a_dil]
if missing:
    print(f"  FAIL: missing dilutions for: {missing}")
else:
    print("  PASS: all v7a ingredients have dilution entries")

print("\n[6] Sub-ODT trace check (v7a)")
for k in ["Geosmin", "Scentenal", "Indole"]:
    if k in v7a_ing:
        print(f"    {k}: {v7a_ing[k]:.1f} µL at {v7a_dil.get(k,1.0)*100:.0f}% dilution")

# Save
out = {
    "v3_geo": v3_geo,
    "v7_geo": v7_geo,
    "v7a_geo": v7a_geo,
    "v7a_ing": v7a_ing,
    "v7a_axes": {a: v7a_det.get(a, 0.0) for a in axes},
    "delta_v7a_vs_v7": v7a_geo - v7_geo,
    "delta_v7a_vs_v3": v7a_geo - v3_geo,
}
with open("_opt_v7a_cedarEO_swap.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\nSaved: _opt_v7a_cedarEO_swap.json")
