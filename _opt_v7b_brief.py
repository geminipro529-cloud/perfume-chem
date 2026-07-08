"""v7b — A1+A2+A4 + all of B + D2 brief-specific scoring + D3 re-seeded hill-climb.

User directive (2026-04-23):
  - A1 Geosmin overdose fix (15 → 2 µL).
  - A2 Amber split: Ambrox Super 450 → 300 + add Ambermax (50%) 250 µL.
  - A4 Add Azarbre 100 µL neat (cedar-amber warm bridge).
  - B1 Buttery push: Orivone 500→650, Delta Decalactone 375→500, +Gamma Decalactone 100.
  - B2 Powder push: Musk Ketone 600→900, Heliotropal 100→150, Anisaldehyde 60→100, +Helional 50.
  - B3 Cosmetic-diffusion: Benzyl Sal 350→500, Hexyl Sal 350→500.
    (Amyl Salicylate NOT in inventory — scrapped.)
  - Skip A3 Exaltolide (user excluded).
  - Skip all C (user excluded).
  - Brief shift: "powdery iris white floral powder creamy" —
    small white-floral lift: DBCA 75→125, Lilyreal ND 75→125, +ACA 40 µL.
  - D2: build iris_cosmetic_powder ObjectiveWeights (down-weight photorealism,
    up-weight hedonic/texture/luxury). Score v3/v7a/v7b under BOTH default
    and brief weights — show how brief weights change the ranking.
  - D3: re-seed the hill-climb from v7b using brief weights, IFRA caps and
    sub-ODT ceilings enforced. Report any extra gains found.
"""
from __future__ import annotations
import json, os, sys, random, time

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula
from _opt_iris_reverie_15probes import (
    IRL_V3, IRL_DIL_BASE, BATCH_ML, AIMI_CAPPED, IFRA_CAPPED, SUB_ODT_TRACES,
)

AXES = ("longevity","sillage","luxury","texture","stacking_depth",
        "photorealism","perceptual_clarity","skin_performance",
        "synergy","hedonic")

# ---------- v7a ingredients (from v7a JSON) ----------
with open("_opt_v7a_cedarEO_swap.json","r",encoding="utf-8") as f:
    v7a_snap = json.load(f)
v7a_ing = dict(v7a_snap["v7a_ing"])

# ---------- v7b construction ----------
v7b_ing = dict(v7a_ing)

# A1 Geosmin overdose fix
v7b_ing["Geosmin"] = 2.0

# A2 Amber split
v7b_ing["Ambrox Super"] = 300.0
v7b_ing["Ambermax"]     = 250.0  # 50% dilution

# A4 Azarbre
v7b_ing["Azarbre"] = 100.0       # neat

# B1 Buttery push
v7b_ing["Orivone"]            = 650.0
v7b_ing["Delta Decalactone"]  = 500.0
v7b_ing["Gamma Decalactone"]  = 100.0  # new, neat

# B2 Powder push
v7b_ing["Musk Ketone"]   = 900.0
v7b_ing["Heliotropal"]   = 150.0
v7b_ing["Anisaldehyde"]  = 100.0
v7b_ing["Helional"]      = 50.0        # new, neat

# B3 Cosmetic-diffusion push
v7b_ing["Benzyl Salicylate"] = 500.0
v7b_ing["Hexyl Salicylate"]  = 500.0

# Brief emphasis — white floral + powder lift
v7b_ing["DBCA"]        = 125.0
v7b_ing["Lilyreal ND"] = 125.0
v7b_ing["ACA"]         = 40.0          # new, neat (under IFRA cap 50)

# ---------- v7b dilutions ----------
v7b_dil = dict(IRL_DIL_BASE)
v7b_dil["Cedarwood EO"] = 1.0   # from v7a
v7b_dil["Ambermax"]     = 0.50  # inventory note
v7b_dil["Azarbre"]      = 1.0
v7b_dil["Gamma Decalactone"] = 1.0
v7b_dil["Helional"]     = 1.0
v7b_dil["ACA"]          = 1.0

# ---------- Brief-specific weights (D2) ----------
BRIEF_NAME = "iris_cosmetic_powder"
brief_weights = ObjectiveWeights(
    longevity=0.8,        # default
    sillage=0.6,          # slightly down — skin-intimate, not sport
    synergy=0.5,          # default
    luxury=1.0,           # up — brief is luxury niche
    texture=1.0,          # up — powdery/creamy IS texture
    stacking_depth=0.8,   # default
    skin_performance=0.9, # up — must sit well on skin
    hedonic=0.9,          # up — brief-alignment axis
    perceptual_clarity=0.5,  # slightly down — powder is inherently blurred
    photorealism=0.4,     # down — brief is cosmetic, not photoreal
)

# ---------- Scorers ----------
sg = SynergyGraph()
scorer_default = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
scorer_brief   = FormulaScorer(weights=brief_weights,
                               synergy_graph=sg, batch_volume_ml=BATCH_ML)

def score_with(scorer, ing, dil):
    return score_formula(ing, dil, scorer)

# ---------- Verification helpers ----------
def check_ifra(ing):
    out = []
    for k,cap in IFRA_CAPPED.items():
        if k in ing and ing[k] > cap:
            out.append(f"  FAIL {k}: {ing[k]} > {cap}")
    return out

def tot(ing): return sum(ing.values())

# ---------- v7b: score under both weight profiles ----------
print("═" * 76)
print("  v7b — A1+A2+A4 + all B + D2 (brief weights) + D3 (re-seed)")
print("═" * 76)

v3_geo_def, v3_det_def = score_with(scorer_default, IRL_V3, IRL_DIL_BASE)
v7a_geo_def, v7a_det_def = score_with(scorer_default, v7a_ing, v7b_dil)
v7b_geo_def, v7b_det_def = score_with(scorer_default, v7b_ing, v7b_dil)

v3_geo_br, v3_det_br = score_with(scorer_brief, IRL_V3, IRL_DIL_BASE)
v7a_geo_br, v7a_det_br = score_with(scorer_brief, v7a_ing, v7b_dil)
v7b_geo_br, v7b_det_br = score_with(scorer_brief, v7b_ing, v7b_dil)

print(f"\n[1] Composite scores — default vs brief weights")
print(f"  {'version':<10} {'default':>10} {'brief':>10}  Δ(brief-default)")
print(f"  {'v3':<10} {v3_geo_def:>10.3f} {v3_geo_br:>10.3f}  {v3_geo_br-v3_geo_def:+.3f}")
print(f"  {'v7a':<10} {v7a_geo_def:>10.3f} {v7a_geo_br:>10.3f}  {v7a_geo_br-v7a_geo_def:+.3f}")
print(f"  {'v7b':<10} {v7b_geo_def:>10.3f} {v7b_geo_br:>10.3f}  {v7b_geo_br-v7b_geo_def:+.3f}")
print(f"\n  Δ v7b vs v7a (default): {v7b_geo_def-v7a_geo_def:+.3f}")
print(f"  Δ v7b vs v7a (brief)  : {v7b_geo_br -v7a_geo_br :+.3f}")
print(f"  Δ v7b vs v3  (default): {v7b_geo_def-v3_geo_def:+.3f}")
print(f"  Δ v7b vs v3  (brief)  : {v7b_geo_br -v3_geo_br :+.3f}")

print(f"\n[2] Axis table — v7a vs v7b (default weights)")
print(f"  {'axis':<22}{'v3':>8}{'v7a':>8}{'v7b':>8}{'Δ v7b-v7a':>11}")
for a in AXES:
    s3 = v3_det_def.get(a,0.0); sa=v7a_det_def.get(a,0.0); sb=v7b_det_def.get(a,0.0)
    print(f"  {a:<22}{s3:>8.2f}{sa:>8.2f}{sb:>8.2f}{sb-sa:>+11.2f}")

print(f"\n[3] IFRA & cap compliance (v7b)")
issues = check_ifra(v7b_ing)
if issues:
    for i in issues: print(i)
else:
    print("  PASS: no IFRA violations")
for k,cap in IFRA_CAPPED.items():
    if k in v7b_ing:
        print(f"    {k}: {v7b_ing[k]:.1f} / {cap:.1f} µL ({v7b_ing[k]/cap*100:.0f}% of cap)")

print(f"\n[4] Volume check (v7b)")
conc = tot(v7b_ing)
eth = 50000.0 - conc
print(f"  Concentrate: {conc:.1f} µL ({conc/500:.2f}%)")
print(f"  Ethanol 96%: {eth:.1f} µL")
print(f"  Total      : {conc+eth:.1f} µL (target 50000.0)")

# ---------- D3: re-seed hill-climb from v7b under brief weights ----------
print(f"\n[5] D3 — Re-seeded hill-climb from v7b (brief weights)")

def build_bounds(ing):
    floor = {n: 1.0 for n in ing}
    ceiling = {n: float("inf") for n in ing}
    for n in SUB_ODT_TRACES:
        if n in ing:
            ceiling[n] = ing[n] * 3.0
    for n in AIMI_CAPPED:
        if n in ing:
            ceiling[n] = ing[n]
    for n, cap in IFRA_CAPPED.items():
        if n in ing:
            ceiling[n] = cap
    # Geosmin hard ceiling 3 µL (perfumer-guidance max per 100mL = 2–5 µL)
    if "Geosmin" in ing:
        ceiling["Geosmin"] = 3.0
        floor["Geosmin"] = 1.0
    return floor, ceiling

def climb(ing, dil, scorer, passes=10, seed=42):
    ing = dict(ing)
    floor, ceiling = build_bounds(ing)
    best_geo, best_det = score_with(scorer, ing, dil)
    rng = random.Random(seed)
    STEPS = [+25,+50,+100,-25,-50,-100,+15,-15]
    accepted = 0
    for p in range(passes):
        keys = list(ing.keys())
        rng.shuffle(keys)
        found = False
        for name in keys:
            cur = ing[name]
            fl = floor.get(name,1.0); cl = ceiling.get(name,float("inf"))
            if fl >= cl-0.5: continue
            for step in STEPS:
                nv = cur+step
                if nv < fl-0.5 or nv > cl+0.5: continue
                if nv < 1 or nv > 4000: continue
                trial = dict(ing); trial[name] = nv
                try:
                    rev = check_proportional_scaling(trial, dil, BATCH_ML, 15.0)
                    if any(c.severity=="error" for c in rev):
                        continue
                except Exception:
                    pass
                g, d = score_with(scorer, trial, dil)
                if g > best_geo + 0.02:
                    ing = trial; best_geo, best_det = g, d
                    accepted += 1; found = True
                    break
        if not found: break
    return ing, best_det, best_geo, accepted

t0 = time.time()
v7c_ing, v7c_det, v7c_geo, moves = climb(v7b_ing, v7b_dil, scorer_brief, passes=12)
dt = time.time()-t0
v7c_geo_default, v7c_det_default = score_with(scorer_default, v7c_ing, v7b_dil)
print(f"  v7b (brief weights): {v7b_geo_br:.3f}")
print(f"  v7c (hill-climb): {v7c_geo:.3f} ({moves} accepted moves, {dt:.1f}s)")
print(f"  v7c (default weights for reference): {v7c_geo_default:.3f}")
print(f"  Δ v7c-v7b (brief): {v7c_geo - v7b_geo_br:+.3f}")

# Show moves
print(f"\n[6] v7c changes vs v7b")
changes = []
for k in sorted(set(list(v7b_ing.keys()) + list(v7c_ing.keys()))):
    a = v7b_ing.get(k, 0.0); b = v7c_ing.get(k, 0.0)
    if abs(a-b) > 0.5:
        changes.append((k, a, b, b-a))
if changes:
    for n,a,b,d in sorted(changes, key=lambda x:-abs(x[3])):
        print(f"    {n:<30} {a:>7.1f} → {b:>7.1f}  (Δ {d:+.1f})")
else:
    print("    (no moves accepted — v7b already at local optimum under brief weights)")

# ---------- Save ----------
out = {
    "v3_geo_default": v3_geo_def,
    "v3_geo_brief":   v3_geo_br,
    "v7a_geo_default": v7a_geo_def,
    "v7a_geo_brief":   v7a_geo_br,
    "v7b_ing":         v7b_ing,
    "v7b_dil":         v7b_dil,
    "v7b_geo_default": v7b_geo_def,
    "v7b_geo_brief":   v7b_geo_br,
    "v7b_axes_default": v7b_det_def,
    "v7b_axes_brief":   v7b_det_br,
    "brief_weights":   brief_weights.as_dict(),
    "v7c_ing":         v7c_ing,
    "v7c_geo_brief":   v7c_geo,
    "v7c_geo_default": v7c_geo_default,
    "v7c_axes_brief":  v7c_det,
    "v7c_moves":       moves,
    "v7c_changes":     [(n,a,b,d) for n,a,b,d in changes],
}
with open("_opt_v7b_brief.json","w",encoding="utf-8") as f:
    json.dump(out, f, indent=2, default=float)
print(f"\nSaved: _opt_v7b_brief.json")
