"""v7h — Apply ppm/ODT/IFRA-driven refinements to v7g.

Refinements (from _v7g_ppm_odt_analysis.py findings):
  A) Bourgeonal 50 → 4 µL  — IFRA Cat 4 hard cap (12× over)
  B) Heliotropal 35 → 80 µL — get into headspace (HS_idx must be > 0.05)
  C) Iris-violet headspace WITHOUT β-ionone over-dose (anosmia + adaptation)
     • β-Ionone 75 → 60 µL  (slight reduction; OR5A1 hyposmia ~30 % pop, Jaeger 2013)
     • α-Ionone 60 → 110 µL (no anosmia, ODT_air 0.4 ppb, less receptor-binding)
     • α-Isomethyl Ionone 25 → 80 µL (powdery-violet, slow adapt)
     • Allyl Ionone 0 → 30 µL (Ketone V — fruity-violet bridge, no β-receptor competition)
  D) Benzoin 1675 → 1200 µL — un-blanket cream register
  E) Add Benzyl Sal 0 → 100 µL — restore L'Heure Bleue cosmetic gravitas
  F) Musk chord rebalance: EB 1275 → 950, Romandolide 600 → 850
  G) Hydroxycitronellal 500 → 600 µL — compensate Bourgeonal cut, maintain muguet ppm

IFRA Cat 4 caps (50 mL EDP @ ~24 % concentration in EtOH, applied to skin diluted 5x):
  Bourgeonal (p-BMHCA): 4 µL × 1.0 = 4 µL active in 11.9k µL = 336 ppm conc
                         → 67 ppm on skin → 0.0067 % — at IFRA 50 limit
  Hydroxycitronellal: ~1.0 % skin limit — 600 µL safe
  ACA (not in formula)
  Cinnamal (not in formula)
"""

from __future__ import annotations
import copy
import json
import sys
import time

sys.path.insert(0, ".")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula

scorer = FormulaScorer(synergy_graph=SynergyGraph(), weights=ObjectiveWeights())

# ── Load v7g baseline ──────────────────────────────────────
with open("_opt_v7g_helio_musk.json", "r", encoding="utf-8") as f:
    SNAP = json.load(f)
V7G = SNAP["v7g"]
V7G_ING = dict(V7G["ing"])
DIL = dict(V7G["dil"])

ING = copy.deepcopy(V7G_ING)


def score(ing, dil):
    geo, detail = score_formula(ing, dil, scorer)
    return {"geo": geo, **detail}


# ── Apply refinement seeds ─────────────────────────────────
SEED = {
    # A — IFRA Bourgeonal hard cap
    "Bourgeonal":              4.0,
    # B — Heliotropal into headspace
    "Heliotropal":             80.0,
    # C — anosmia-aware iris-violet chord
    "Beta Ionone":             60.0,
    "Alpha Ionone":            110.0,
    "Alpha Isomethyl Ionone":  80.0,
    "Allyl Ionone":            30.0,    # Ketone V — new addition
    # D — un-blanket the cream
    "Benzoin Resinoid":        1200.0,
    # E — cosmetic salicylate cushion
    "Benzyl Salicylate":       100.0,
    # F — musk chord rebalance
    "Ethylene Brassylate":     950.0,
    "Romandolide":             850.0,
    # G — muguet ppm preservation after Bourgeonal cut
    "Hydroxycitronellal":      600.0,
}
for k, v in SEED.items():
    ING[k] = v
    if k not in DIL:
        DIL[k] = 1.0  # neat unless inventory says otherwise

# Allyl Ionone is neat in inventory
DIL["Allyl Ionone"] = 1.0

# ── IFRA caps (volume in µL of dilution; converted to ppm at active calc) ──
# Conservative IFRA 50/51 Cat 4 estimates expressed as MAX ACTIVE µL in 11.9k µL active concentrate.
# Limit-on-skin × dilution-to-skin (~5×) × 11.9k:
#   skin-limit %   →  conc-limit %   →  active µL ceiling
IFRA_CAPS_ACTIVE = {
    "Bourgeonal":          5.0,    # 0.0007 % skin → 4.2 µL active
    "Hydroxycitronellal":  1190.0, # 1.0 % skin → ~1190 µL conc — well above
    "Isoeugenol":          24.0,   # 0.02 % skin
    "Coumarin":            714.0,  # 0.6 % skin
    "Anisaldehyde":        595.0,  # 0.5 % skin
    "Damascol":            6.0,    # 0.005 % skin (damascones strict)
    "Indole":              12.0,   # 0.01 % skin
    "Helional":            83.0,   # 0.07 % skin
    "Bergamot FCF oil Sicilian": 595.0,  # already FCF, ~0.5 % skin headroom
}


def ifra_check(ing, dil):
    """Return (ok, list_of_violations) checking active dose against IFRA caps."""
    violations = []
    for mat, max_active in IFRA_CAPS_ACTIVE.items():
        active = ing.get(mat, 0.0) * dil.get(mat, 1.0)
        if active > max_active:
            violations.append(f"{mat}: {active:.1f} µL active > {max_active:.1f} µL IFRA")
    return (len(violations) == 0), violations


# ── Brief / pillar guardrails (carried from v7g) ──────────
OFF_BRIEF_BLOCK = {
    "Galbanum CO2", "Galbanum EO", "Galbanum Resinoid",
    "Dynascone", "Leafovert",
    "IBQ", "Isobutyl Quinoline",
    "Birch Tar", "Guaiacol",
    "Styrax FTEC", "Evernyl",
    "Patchouli EO", "Vetiver EO",
    "Clary Sage EO",
}
PILLARS = {
    "Alpha Irone", "Hedione", "Hedione HC", "Ebanol", "Vanillin",
    "Coumarin", "Anisaldehyde", "Benzoin Resinoid",
    "Heliotropal",
    "Ethylene Brassylate", "Romandolide",
    "Habanolide", "Ambrettolide", "Ambrox Super",
    "Bergamot FCF oil Sicilian", "Iso E Super",
    # New iris-violet pillars (anosmia-balanced)
    "Alpha Ionone", "Alpha Isomethyl Ionone",
}
PILLAR_FLOOR_FRAC = 0.50

STOCK_CAP = {
    "Habanolide": 350.0,
    "Ambrettolide": 350.0,
}

INIT_FLOOR = dict(ING)


def brief_ok(ing, dil):
    for blocked in OFF_BRIEF_BLOCK:
        if ing.get(blocked, 0.0) > 0.0:
            return False, f"off-brief: {blocked}"
    if ing.get("Carrot Seed EO", 0.0) > 250.0:
        return False, "Carrot Seed > 250 µL"
    if ing.get("Bergamot FCF oil Sicilian", 0.0) > 500.0:
        return False, "Bergamot > 500 µL"
    sal = ing.get("Benzyl Salicylate", 0.0) + ing.get("Hexyl Salicylate", 0.0)
    if sal < 200.0:
        return False, f"salicylate cushion {sal:.0f} < 200 µL"
    # β-Ionone hard ceiling — anosmia / adaptation guard
    if ing.get("Beta Ionone", 0.0) > 75.0:
        return False, f"Beta Ionone > 75 µL (anosmia/adapt risk)"
    for p in PILLARS:
        b = INIT_FLOOR.get(p, 0.0)
        if b > 0.0 and ing.get(p, 0.0) < b * PILLAR_FLOOR_FRAC:
            return False, f"pillar {p} below 50% floor"
    for mat, cap in STOCK_CAP.items():
        if ing.get(mat, 0.0) > cap:
            return False, f"{mat} exceeds stock cap {cap:.0f}"
    ok_ifra, viols = ifra_check(ing, dil)
    if not ok_ifra:
        return False, f"IFRA: {viols[0]}"
    return True, ""


print("=" * 76)
print("  v7h — IFRA + anosmia-aware iris-violet refinement of v7g")
print("=" * 76)

g_seed = score(ING, DIL)
ok_seed, why = brief_ok(ING, DIL)
print(f"\n  v7g baseline : geo={V7G['geo']:.3f}")
print(f"  v7h seed     : geo={g_seed['geo']:.3f}  luxury={g_seed['luxury']:.2f}  hedonic={g_seed['hedonic']:.2f}")
print(f"  brief check  : {'OK' if ok_seed else 'FAIL — ' + why}")

ok_ifra, viols = ifra_check(ING, DIL)
print(f"\n  IFRA gate    : {'PASS' if ok_ifra else 'FAIL'}")
for v in viols:
    print(f"    ✗ {v}")

# Show iris-violet chord
print("\n  IRIS-VIOLET CHORD (anosmia-balanced):")
iris_chord = [
    ("Alpha Irone",            "core — irones, slow"),
    ("Beta Ionone",            "headspace — CAPPED 60µL (OR5A1 hyposmia)"),
    ("Alpha Ionone",           "headspace — no anosmia, ODT 0.4 ppb"),
    ("Alpha Isomethyl Ionone", "powder — slow-adapt violet"),
    ("Allyl Ionone",           "fruity-violet bridge, no β-receptor compete"),
    ("Orivone",                "buttery iris support"),
    ("Ultralia",               "ghost iris trace"),
    ("Carrot Seed EO",         "rooty — capped per brief"),
]
for m, role in iris_chord:
    amt = ING.get(m, 0.0); d = DIL.get(m, 1.0); active = amt * d
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active  {role}")


# ── Bounds (carry v7g logic) ─────────────────────
SUB_ODT_TRACES = {"Geosmin", "Scentenal", "Indole"}
IFRA_CAPPED = {
    "Bourgeonal": 5.0,
    "Damascol": 75.0,    # 0.005% × 5 / 0.10 dil = 6 µL active = 60 µL @ 10 %
    "Indole": 120.0,     # 0.01 % skin × 5 / 0.10 dil = 100 µL @ 10 %
    "Helional": 83.0,
    "Isoeugenol": 24.0,
}
AIMI_CAPPED = set()


def bounds(name, cur, dil):
    if name in SUB_ODT_TRACES:
        ceil = max(cur * 3, cur + 50)
    elif name in IFRA_CAPPED:
        ceil = IFRA_CAPPED[name]
    elif name == "Geosmin":
        ceil = 3.0
    elif name == "Beta Ionone":
        ceil = 75.0          # anosmia hard cap
    else:
        ceil = 2000.0
    if name in STOCK_CAP:
        ceil = min(ceil, STOCK_CAP[name])
    floor = 1.0 if name == "Geosmin" else (
        max(5.0, cur * 0.1) if name in SUB_ODT_TRACES else 0.0)
    return floor, ceil


STEPS = [+200, +100, +50, +25, +15, +10, +5, -200, -100, -50, -25, -15, -10, -5]


def climb(ing, dil, max_passes=8):
    cur = score(ing, dil)
    cur_geo = cur["geo"]
    moves = 0
    t0 = time.time()
    for p in range(1, max_passes + 1):
        improved = False
        for name in list(ing.keys()):
            cur_amt = ing[name]
            floor, ceil = bounds(name, cur_amt, dil)
            best_step, best_geo = None, cur_geo
            for s in STEPS:
                new_amt = cur_amt + s
                if new_amt < floor or new_amt > ceil:
                    continue
                test_ing = dict(ing); test_ing[name] = new_amt
                ok, _ = brief_ok(test_ing, dil)
                if not ok:
                    continue
                g_new = score(test_ing, dil)["geo"]
                if g_new > best_geo + 0.005:
                    best_geo = g_new; best_step = s
            if best_step is not None:
                ing[name] = cur_amt + best_step
                improved = True
                moves += 1
                print(f"    ★ pass {p} {name}: {cur_amt:.0f} → {ing[name]:.0f}  geo {cur_geo:.3f} → {best_geo:.3f}")
                cur_geo = best_geo
        if not improved:
            break
    print(f"  climb done: {moves} moves, {time.time()-t0:.0f}s, final geo {cur_geo:.3f}")
    return ing, dil


print("\n" + "─" * 76)
print("  CLIMB — IFRA-locked, β-Ionone-capped, anosmia-aware")
print("─" * 76)
ING_FINAL, DIL_FINAL = climb(ING, DIL, max_passes=6)
g_final = score(ING_FINAL, DIL_FINAL)


# ── Report ─────────────
print("\n" + "─" * 76)
print("  v7h vs v7g (default scorer)")
print("─" * 76)
print(f"\n  axis                    v7g        v7h        Δ")
for ax in ["longevity", "sillage", "luxury", "texture", "stacking_depth",
           "photorealism", "perceptual_clarity", "skin_performance",
           "synergy", "hedonic"]:
    v0 = V7G["axis"][ax]; v1 = g_final[ax]
    flag = "  ⚠" if v1 < v0 - 1.0 else ""
    print(f"  {ax:<22s} {v0:>7.2f}   {v1:>7.2f}    {v1-v0:+7.2f}{flag}")
print(f"\n  geo: v7g {V7G['geo']:.3f} → v7h {g_final['geo']:.3f}  ({g_final['geo']-V7G['geo']:+.3f})")

ok_final, why = brief_ok(ING_FINAL, DIL_FINAL)
ok_ifra, viols = ifra_check(ING_FINAL, DIL_FINAL)
print(f"\n  Brief guardrails: {'✓ PASS' if ok_final else '✗ FAIL — ' + why}")
print(f"  IFRA gate       : {'✓ PASS' if ok_ifra else '✗ FAIL'}")
for v in viols:
    print(f"    ✗ {v}")

# Final iris-violet chord
print("\n  Final IRIS-VIOLET CHORD:")
total_iris_active = 0.0
for m, role in iris_chord:
    amt = ING_FINAL.get(m, 0.0); d = DIL_FINAL.get(m, 1.0); active = amt * d
    total_iris_active += active
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active  {role}")
print(f"    {'TOTAL IRIS ACTIVE':<26s}                    = {total_iris_active:>5.1f} µL")

# Δ from v7g
print("\n  Δ ingredients (v7h vs v7g):")
all_keys = sorted(set(V7G_ING.keys()) | set(ING_FINAL.keys()))
for k in all_keys:
    a = V7G_ING.get(k, 0.0); b = ING_FINAL.get(k, 0.0)
    if abs(a - b) > 1e-3:
        flag = "  [IFRA]" if k in IFRA_CAPS_ACTIVE else ""
        print(f"    {k:<32s} {a:>7.1f} → {b:>7.1f}  ({b-a:+7.1f}){flag}")

snap = {
    "v7h": {
        "geo": g_final["geo"],
        "ing": ING_FINAL,
        "dil": DIL_FINAL,
        "axis": {ax: g_final[ax] for ax in [
            "longevity", "sillage", "luxury", "texture", "stacking_depth",
            "photorealism", "perceptual_clarity", "skin_performance",
            "synergy", "hedonic"]},
    },
    "v7g_baseline": {"geo": V7G["geo"], "axis": V7G["axis"]},
}
with open("_opt_v7h_ifra_iris.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2)
print(f"\n  snapshot → _opt_v7h_ifra_iris.json")
print("  ─── DONE ───")
