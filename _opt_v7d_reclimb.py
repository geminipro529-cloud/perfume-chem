"""v7d — Re-climb from v7a (current leader under new Hill/Raoult/hedonic/OR scorer).

Context (2026-04-23 post-scorer-upgrade):
  - The scorer now uses Hill-saturation OAV response, Raoult γᵢ correction,
    mass-weighted hedonic nudge, and OR-family overload penalty.
  - Under the new default weights v7a moved to 81.020 (was 80.810) and v7b
    to 80.871 (was 80.542); v7a regained the lead. The D3 climb from v7b
    accepted 0 moves.
  - This script re-climbs from v7a with a wider step ladder under both
    default and brief weights and reports the winner.
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

# ---- v7a seed ----
with open("_opt_v7a_cedarEO_swap.json","r",encoding="utf-8") as f:
    v7a_snap = json.load(f)
v7a_ing = dict(v7a_snap["v7a_ing"])

v7a_dil = dict(IRL_DIL_BASE)
v7a_dil["Cedarwood EO"] = 1.0

# ---- brief weights (from v7b script) ----
brief_w = ObjectiveWeights(
    longevity=0.8, sillage=0.6, synergy=0.5, luxury=1.0, texture=1.0,
    stacking_depth=0.8, skin_performance=0.9, hedonic=0.9,
    perceptual_clarity=0.5, photorealism=0.4,
)

sg = SynergyGraph()
scorer_def   = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
scorer_brief = FormulaScorer(weights=brief_w, synergy_graph=sg,
                             batch_volume_ml=BATCH_ML)

def s(scorer, ing, dil):
    return score_formula(ing, dil, scorer)

def build_bounds(ing):
    floor = {n: 1.0 for n in ing}
    ceil  = {n: float("inf") for n in ing}
    for n in SUB_ODT_TRACES:
        if n in ing:
            ceil[n] = max(ing[n] * 3.0, ing[n] + 50.0)
    for n in AIMI_CAPPED:
        if n in ing:
            ceil[n] = ing[n]
    for n, cap in IFRA_CAPPED.items():
        if n in ing:
            ceil[n] = cap
    if "Geosmin" in ing:
        ceil["Geosmin"]  = 3.0
        floor["Geosmin"] = 1.0
    return floor, ceil

# Wider step ladder than D3 (which used ±15/25/50/100)
STEPS = [+200, +100, +50, +25, +15, +10,
         -200, -100, -50, -25, -15, -10]

# Optional new-material trials (carefully chosen, not in v7a)
ADD_CANDIDATES = [
    # (name, dil, start_uL) — try inserting at small dose, then climb
    ("Cashmeran",        0.20,  50.0),  # textile warmth, iris-powder synergist
    ("Gamma Decalactone", 1.0,  50.0),  # buttery peach (in v7b, not v7a)
    ("Helional",          1.0,  25.0),  # ozonic-watery-melon support
]

def climb(ing, dil, scorer, label, passes=12, seed=42):
    ing = dict(ing); dil = dict(dil)
    floor, ceil = build_bounds(ing)
    best_geo, best_det = s(scorer, ing, dil)
    rng = random.Random(seed)
    accepted = 0
    print(f"\n  [{label}] start geo={best_geo:.3f}")
    for p in range(passes):
        keys = list(ing.keys())
        rng.shuffle(keys)
        moved_this_pass = False
        for name in keys:
            cur = ing[name]
            fl = floor.get(name, 1.0); cl = ceil.get(name, float("inf"))
            if fl >= cl - 0.5:
                continue
            for step in STEPS:
                nv = cur + step
                if nv < fl - 0.5 or nv > cl + 0.5:
                    continue
                if nv < 1 or nv > 4500:
                    continue
                trial = dict(ing); trial[name] = nv
                try:
                    rev = check_proportional_scaling(trial, dil, BATCH_ML, 15.0)
                    if any(c.severity == "error" for c in rev):
                        continue
                except Exception:
                    pass
                g, d = s(scorer, trial, dil)
                if g > best_geo + 0.02:
                    ing = trial
                    best_geo, best_det = g, d
                    accepted += 1
                    moved_this_pass = True
                    print(f"    ★ pass {p+1} {name}: {cur:.0f} → {nv:.0f}  "
                          f"geo {best_geo:.3f}")
                    break
        if not moved_this_pass:
            break
    print(f"  [{label}] final geo={best_geo:.3f}  ({accepted} moves)")
    return ing, dil, best_geo, best_det

def try_add_then_climb(ing, dil, scorer, label):
    ing = dict(ing); dil = dict(dil)
    base_geo, _ = s(scorer, ing, dil)
    print(f"\n  [{label}] base geo={base_geo:.3f}, trying ADD candidates")
    best_ing, best_dil, best_geo = ing, dil, base_geo
    for name, dl, start in ADD_CANDIDATES:
        if name in ing:
            continue
        trial_ing = dict(ing); trial_ing[name] = start
        trial_dil = dict(dil); trial_dil[name] = dl
        try:
            rev = check_proportional_scaling(trial_ing, trial_dil, BATCH_ML, 15.0)
            if any(c.severity == "error" for c in rev):
                print(f"    skip {name}: scaling error")
                continue
        except Exception:
            pass
        g, _ = s(scorer, trial_ing, trial_dil)
        delta = g - base_geo
        mark = "+" if delta > 0 else "-"
        print(f"    {mark} +{name} @ {start:.0f} µL ({dl*100:.0f}%): "
              f"geo {g:.3f} (Δ{delta:+.3f})")
        if g > best_geo + 0.02:
            best_ing, best_dil, best_geo = trial_ing, trial_dil, g
    if best_geo > base_geo + 0.02:
        print(f"  [{label}] best ADD: {best_geo:.3f} — now climbing")
        return climb(best_ing, best_dil, scorer, f"{label}+add")
    print(f"  [{label}] no ADD beat base — skipping climb")
    return ing, dil, base_geo, None

# ── Re-climb v7a under default and brief weights ──
print("═" * 76)
print("  v7d — re-climb from v7a under new scorer (Hill/γ/hedonic/OR)")
print("═" * 76)

v3_def,_ = s(scorer_def, IRL_V3, IRL_DIL_BASE)
v7a_def,_ = s(scorer_def, v7a_ing, v7a_dil)
print(f"  baselines (default): v3={v3_def:.3f}  v7a={v7a_def:.3f}")

t0 = time.time()
v7d_def_ing, v7d_def_dil, v7d_def_geo, v7d_def_det = climb(
    v7a_ing, v7a_dil, scorer_def, "v7d-default", passes=12, seed=42)
print(f"  Δ vs v7a: {v7d_def_geo - v7a_def:+.3f}  ({time.time()-t0:.0f}s)")

t0 = time.time()
v7a_br,_ = s(scorer_brief, v7a_ing, v7a_dil)
print(f"\n  baselines (brief): v7a={v7a_br:.3f}")
v7d_br_ing, v7d_br_dil, v7d_br_geo, v7d_br_det = climb(
    v7a_ing, v7a_dil, scorer_brief, "v7d-brief", passes=12, seed=42)
print(f"  Δ vs v7a: {v7d_br_geo - v7a_br:+.3f}  ({time.time()-t0:.0f}s)")

# ── Try ADDing 1 new material (non-v7a) then climb ──
t0 = time.time()
v7d_add_ing, v7d_add_dil, v7d_add_geo, v7d_add_det = try_add_then_climb(
    v7a_ing, v7a_dil, scorer_def, "v7d-default+addtrial")
print(f"  add-trial total time: {time.time()-t0:.0f}s")

# ── Print per-axis breakdown for the winning default-weights variant ──
candidates = [
    ("v7a base",  v7a_ing, v7a_dil, v7a_def, None),
    ("v7d-def",   v7d_def_ing, v7d_def_dil, v7d_def_geo, v7d_def_det),
    ("v7d-add",   v7d_add_ing, v7d_add_dil, v7d_add_geo, v7d_add_det),
]
winner = max(candidates, key=lambda c: c[3])
print(f"\n[winner default] {winner[0]}: geo={winner[3]:.3f}")

if winner[4] is not None:
    print(f"\n  axis breakdown ({winner[0]} vs v7a):")
    _, v7a_det = s(scorer_def, v7a_ing, v7a_dil)
    print(f"  {'axis':<22}{'v7a':>8}{winner[0][:8]:>10}{'Δ':>8}")
    for a in AXES:
        sa = v7a_det.get(a, 0.0); sw = winner[4].get(a, 0.0)
        print(f"  {a:<22}{sa:>8.2f}{sw:>10.2f}{sw-sa:>+8.2f}")

# ── Diff vs v7a ──
def diff(base, new):
    out = {}
    for k in set(base) | set(new):
        b = base.get(k, 0.0); n = new.get(k, 0.0)
        if abs(b - n) > 0.5:
            out[k] = (b, n, n - b)
    return out

if winner[0] != "v7a base":
    print(f"\n  Δ ingredients ({winner[0]} vs v7a):")
    d = diff(v7a_ing, winner[1])
    for k in sorted(d, key=lambda kk: -abs(d[kk][2])):
        b, n, dd = d[k]
        print(f"    {k:<32} {b:>8.1f} → {n:>8.1f}  ({dd:+.1f})")

# ── Save snapshot ──
snap = {
    "v7d_default": {
        "geo": v7d_def_geo,
        "ing": v7d_def_ing,
        "dil": v7d_def_dil,
    },
    "v7d_brief": {
        "geo": v7d_br_geo,
        "ing": v7d_br_ing,
        "dil": v7d_br_dil,
    },
    "v7d_add": {
        "geo": v7d_add_geo,
        "ing": v7d_add_ing,
        "dil": v7d_add_dil,
    },
    "v7a_baseline_default": v7a_def,
    "v7a_baseline_brief":   v7a_br,
}
with open("_opt_v7d_reclimb.json","w",encoding="utf-8") as f:
    json.dump(snap, f, indent=2, default=lambda o: o if isinstance(o,(int,float,str,list,dict)) else str(o))
print("\n  snapshot → _opt_v7d_reclimb.json")
