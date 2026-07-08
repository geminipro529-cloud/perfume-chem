"""v7f — two-pass push: luxury, then hedonic.

Pass A: re-weight scorer to luxury=4.0 (vs default 0.8), all other axes
        held at default. Hill-climb v7e with brief-direction guardrails.
Pass B: re-weight scorer to hedonic=3.5 (vs default 0.5), climb from
        v7f-A.

Brief-direction guardrails (Iris Rêverie Lactée — Prada Infusion d'Iris /
L'Heure Bleue axis: powdery iris, cosmetic-creamy white floral, NOT rooty
naturalist):
  - REJECT material additions in {Galbanum, Dynascone, Leafovert, IBQ,
    Birch Tar, Guaiacol, Styrax FTEC, Evernyl, Patchouli EO, Vetiver EO}
    → off-brief character (green bomb, leather/smoke, mossy, earthy).
  - CAP Carrot Seed EO ≤ 250 µL (v6 went 800 µL → off-brief rooty).
  - CAP Bergamot ≤ 500 µL (avoid cologne-citrus dominance).
  - FLOOR salicylate cushion: Benzyl Sal + Hexyl Sal ≥ 200 µL combined
    (this is the cosmetic-cushion spine of the brief).
  - PROTECT pillars: Alpha Irone, Hedione, Hedione HC, Ebanol, Vanillin,
    Coumarin, Heliotropal/Anisaldehyde region cannot be dropped or
    cut > 50 % from baseline.

After both passes, RE-SCORE with default weights and verify both:
  (a) all axes ≥ v7e − 1.0 (no axis collapse), AND
  (b) brief guardrails still satisfied.
"""

from __future__ import annotations
import copy
import json
import time

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph
from engine.ingredient_intelligence import get_profile
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from _scale_30mL_verify_nonlinear import score_formula
from _opt_iris_reverie_15probes import SUB_ODT_TRACES, AIMI_CAPPED, IFRA_CAPPED


# ── Load v7e winner as baseline ──────────────────────────────────────
with open("_opt_v7e_luxury.json", "r", encoding="utf-8") as f:
    SNAP = json.load(f)
V7E = SNAP["v7e"]
ING0 = {k: v for k, v in V7E["ing"].items() if v > 0.0}  # drop zeroed materials
DIL0 = dict(V7E["dil"])

# ── Default scorer for verification ──────────────────────────────────
default_scorer = FormulaScorer(synergy_graph=SynergyGraph(),
                               weights=ObjectiveWeights())


def make_scorer(**axis_overrides):
    w = ObjectiveWeights()
    for k, v in axis_overrides.items():
        setattr(w, k, v)
    return FormulaScorer(synergy_graph=SynergyGraph(), weights=w)


def score(ing, dil, scorer=None):
    s = scorer or default_scorer
    geo, detail = score_formula(ing, dil, s)
    out = dict(detail); out["geo"] = geo
    return out


# ── Brief-direction guardrails ──────────────────────────────────────
OFF_BRIEF_BLOCK = {
    "Galbanum CO2", "Galbanum EO",
    "Dynascone", "Leafovert",
    "IBQ", "Isobutyl Quinoline",
    "Birch Tar", "Guaiacol",
    "Styrax FTEC", "Evernyl",
    "Patchouli EO", "Vetiver EO",
    "Clary Sage EO",
}
PILLARS = {
    "Alpha Irone", "Hedione", "Hedione HC", "Ebanol", "Vanillin",
    "Coumarin", "Anisaldehyde", "Benzoin Resinoid", "Ethylene Brassylate",
    "Habanolide", "Ambrettolide", "Ambrox Super",
    "Bergamot FCF oil Sicilian", "Iso E Super",
}
PILLAR_FLOOR_FRAC = 0.50  # cannot drop below 50 % of baseline


def brief_ok(ing):
    # No off-brief blockers
    for blocked in OFF_BRIEF_BLOCK:
        if ing.get(blocked, 0.0) > 0.0:
            return False, f"off-brief: {blocked}"
    # Carrot Seed cap
    if ing.get("Carrot Seed EO", 0.0) > 250.0:
        return False, "Carrot Seed > 250 µL (rooty bomb)"
    # Bergamot cap
    if ing.get("Bergamot FCF oil Sicilian", 0.0) > 500.0:
        return False, "Bergamot > 500 µL (cologne-citrus dominance)"
    # Salicylate cushion floor
    sal = ing.get("Benzyl Salicylate", 0.0) + ing.get("Hexyl Salicylate", 0.0)
    if sal < 200.0:
        return False, f"salicylate cushion {sal:.0f} < 200 µL floor"
    # Pillars cannot collapse
    for p in PILLARS:
        b = ING0.get(p, 0.0)
        if b > 0.0 and ing.get(p, 0.0) < b * PILLAR_FLOOR_FRAC:
            return False, f"pillar {p} below 50 % of baseline ({ing.get(p,0):.0f} < {b*PILLAR_FLOOR_FRAC:.0f})"
    return True, ""


# Pre-bump salicylate to satisfy floor before climbing (we trimmed too far in v7e)
ING0_FIX = dict(ING0)
sal0 = ING0_FIX.get("Benzyl Salicylate", 0.0) + ING0_FIX.get("Hexyl Salicylate", 0.0)
if sal0 < 200.0:
    deficit = 200.0 - sal0
    ING0_FIX["Hexyl Salicylate"] = ING0_FIX.get("Hexyl Salicylate", 0.0) + deficit
    print(f"  pre-fix: bumped Hexyl Sal +{deficit:.0f} to satisfy 200 µL salicylate floor")


# ── Bounds (reused from v7e) ────────────────────────────────────────
def bounds(name, cur):
    if name in SUB_ODT_TRACES:
        ceil = max(cur * 3, cur + 50)
    elif name in IFRA_CAPPED:
        ceil = IFRA_CAPPED[name]
    elif name in AIMI_CAPPED:
        ceil = AIMI_CAPPED[name] if isinstance(AIMI_CAPPED, dict) else 100.0
    elif name == "Geosmin":
        ceil = 3.0
    else:
        ceil = 2000.0
    floor = 1.0 if name == "Geosmin" else (
        max(5.0, cur * 0.1) if name in SUB_ODT_TRACES else 0.0)
    return floor, ceil


# ── Greedy hill-climb under a given scorer ──────────────────────────
STEPS_BIG = [+200, +100, +50, -200, -100, -50]
STEPS_FINE = [+25, +15, +10, -25, -15, -10]


def climb(ing, dil, scorer, label, max_passes=8, step_seq=None):
    step_seq = step_seq or (STEPS_BIG + STEPS_FINE)
    cur = score(ing, dil, scorer)
    cur_geo = cur["geo"]
    moves = 0
    t0 = time.time()
    for p in range(1, max_passes + 1):
        improved = False
        for name in list(ing.keys()):
            cur_amt = ing[name]
            floor, ceil = bounds(name, cur_amt)
            best_step = None
            best_geo = cur_geo
            for s in step_seq:
                new_amt = cur_amt + s
                if new_amt < floor or new_amt > ceil:
                    continue
                test_ing = dict(ing); test_ing[name] = new_amt
                ok, why = brief_ok(test_ing)
                if not ok:
                    continue
                g_new = score(test_ing, dil, scorer)["geo"]
                if g_new > best_geo + 0.005:
                    best_geo = g_new; best_step = s
            if best_step is not None:
                ing[name] = cur_amt + best_step
                improved = True
                moves += 1
                print(f"    ★ {label} pass {p} {name}: {cur_amt:.0f} → {ing[name]:.0f}  geo {cur_geo:.3f} → {best_geo:.3f}")
                cur_geo = best_geo
        if not improved:
            break
    print(f"  {label} done: {moves} moves, {time.time()-t0:.0f}s, final scorer-geo {cur_geo:.3f}")
    return ing, dil


# ───────────── Run ─────────────
print("=" * 76)
print("  v7f — two-pass: luxury, then hedonic (with brief guardrails)")
print("=" * 76)

# Verify guardrails on baseline (after sal-fix)
ok, why = brief_ok(ING0_FIX)
g_base = score(ING0_FIX, DIL0)
print(f"\n  v7e baseline (after sal-fix): geo={g_base['geo']:.3f}  luxury={g_base['luxury']:.2f}  hedonic={g_base['hedonic']:.2f}")
print(f"  brief guardrails: {'OK' if ok else 'FAIL — ' + why}")

# ── Pass A — luxury-weighted ──────────────
print("\n" + "─" * 76)
print("  PASS A — luxury-weighted climb (luxury 0.8 → 4.0)")
print("─" * 76)
lux_scorer = make_scorer(luxury=4.0)
ing_a = dict(ING0_FIX); dil_a = dict(DIL0)
ing_a, dil_a = climb(ing_a, dil_a, lux_scorer, "lux", max_passes=6)

g_a_default = score(ing_a, dil_a)
print(f"\n  PASS A result (default scorer):")
print(f"    geo={g_a_default['geo']:.3f}  luxury={g_a_default['luxury']:.2f}  hedonic={g_a_default['hedonic']:.2f}")

# ── Pass B — hedonic-weighted ──────────────
print("\n" + "─" * 76)
print("  PASS B — hedonic-weighted climb (hedonic 0.5 → 3.5) on PASS A result")
print("─" * 76)
hed_scorer = make_scorer(hedonic=3.5)
ing_b = dict(ing_a); dil_b = dict(dil_a)
ing_b, dil_b = climb(ing_b, dil_b, hed_scorer, "hed", max_passes=6)

g_b_default = score(ing_b, dil_b)
print(f"\n  PASS B result (default scorer):")
print(f"    geo={g_b_default['geo']:.3f}  luxury={g_b_default['luxury']:.2f}  hedonic={g_b_default['hedonic']:.2f}")

# ── Final verification under default weights ───────────
print("\n" + "─" * 76)
print("  FINAL — v7f vs v7e (default scorer)")
print("─" * 76)
print(f"\n  axis                    v7e        v7f        Δ")
for ax in ["longevity", "sillage", "luxury", "texture", "stacking_depth",
           "photorealism", "perceptual_clarity", "skin_performance",
           "synergy", "hedonic"]:
    v0 = V7E["axis"][ax]
    v1 = g_b_default[ax]
    flag = "  ⚠" if v1 < v0 - 1.0 else ""
    print(f"  {ax:<22s} {v0:>7.2f}   {v1:>7.2f}    {v1-v0:+7.2f}{flag}")

print(f"\n  geo: v7e {V7E['geo']:.3f} → v7f {g_b_default['geo']:.3f}  ({g_b_default['geo']-V7E['geo']:+.3f})")

ok_final, why = brief_ok(ing_b)
print(f"\n  Brief guardrails: {'✓ PASS' if ok_final else '✗ FAIL — ' + why}")

# ── Δ ingredients ──────────
print("\n  Δ ingredients (v7f vs v7e):")
all_keys = sorted(set(ING0.keys()) | set(ing_b.keys()))
for k in all_keys:
    a = ING0.get(k, 0.0)
    b = ing_b.get(k, 0.0)
    if abs(a - b) > 1e-3:
        print(f"    {k:<36s} {a:>7.1f} → {b:>7.1f}  ({b-a:+.1f})")

# ── Save ──────
snap = {
    "v7f": {
        "geo": g_b_default["geo"],
        "ing": ing_b,
        "dil": dil_b,
        "axis": {ax: g_b_default[ax] for ax in [
            "longevity", "sillage", "luxury", "texture", "stacking_depth",
            "photorealism", "perceptual_clarity", "skin_performance",
            "synergy", "hedonic"]},
    },
    "v7f_pass_A": {
        "geo": g_a_default["geo"],
        "ing": ing_a,
        "dil": dil_a,
        "axis": {ax: g_a_default[ax] for ax in [
            "longevity", "sillage", "luxury", "texture", "stacking_depth",
            "photorealism", "perceptual_clarity", "skin_performance",
            "synergy", "hedonic"]},
    },
    "v7e_baseline": {"geo": V7E["geo"], "axis": V7E["axis"]},
}
with open("_opt_v7f_lux_hedonic.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2)
print(f"\n  snapshot → _opt_v7f_lux_hedonic.json")
print(f"  ─── DONE ───")
