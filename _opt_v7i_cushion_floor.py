"""v7i — Soft-iris cushion recovery from v7h.

User-directed refinements (April 2026):
  1) Drop Allyl Ionone (0).  Replace with Dihydro Beta Ionone — creamier,
     smoother, no β-receptor competition — paired with the existing 60 µL
     Beta Ionone (anosmia-capped).
  2) Add Myristic Acid Powder (10 % in DPG) — replicates the C12-C16
     fatty-acid matrix of orris butter; silent cushion/fixative for the
     creamy iris register.
  3) Lower Carrot Seed EO (rooty signal — too much for a "soft" iris).
  4) Boost Ultralia paired with Alpha-Isomethyl Ionone — if AIMI doesn't
     read soft amid the creamies, the Ultralia halo softens it.
  5) Hard cushion floor:
       Hexyl Sal + Benzyl Sal + Mayol + Delta Decalactone + Myristic Acid
       ≥ 600 µL active.  This is the L'Heure Bleue / Infusion d'Iris
       cosmetic-creamy-veil — non-negotiable.

Carries forward:
  - β-Ionone hard cap 75 µL (anosmia OR5A1).
  - All v7h IFRA caps (Bourgeonal 5, Damascol 6, Helional 83, etc.).
  - Stock caps: Habanolide 350, Ambrettolide 350.
  - Off-brief block list.
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

# ── Load v7h baseline ──────────────────────────────────────
with open("_opt_v7h_ifra_iris.json", "r", encoding="utf-8") as f:
    SNAP = json.load(f)
V7H = SNAP["v7h"]
V7H_ING = dict(V7H["ing"])
DIL = dict(V7H["dil"])

ING = copy.deepcopy(V7H_ING)


def score(ing, dil):
    geo, detail = score_formula(ing, dil, scorer)
    return {"geo": geo, **detail}


# ── User-directed seed changes ─────────────────────────────
SEED = {
    # 1) Iris-violet chord — swap Allyl Ionone for Dihydro Beta Ionone
    "Allyl Ionone":            0.0,     # remove
    "Dihydro Beta Ionone":     100.0,   # creamier-smoother β replacement
    "Beta Ionone":             60.0,    # unchanged (anosmia-capped)
    "Alpha Ionone":            110.0,   # unchanged
    "Alpha Isomethyl Ionone":  80.0,    # unchanged
    "Ultralia":                80.0,    # 40 → 80 (soften AIMI)

    # 2) Myristic Acid Powder — orris butter fatty matrix
    "Myristic Acid Powder":    200.0,   # 10 % in DPG → 20 µL active

    # 3) Lower Carrot Seed EO (was 210)
    "Carrot Seed EO":          150.0,

    # 4) Restore cushion register (climber stripped it in v7h)
    "Hexyl Salicylate":        350.0,   # 200 → 350
    "Benzyl Salicylate":       100.0,   # 0 → 100
    "Mayol":                   50.0,    # 25 → 50
    "Delta Decalactone":       200.0,   # 50 → 200 (peach-skin lactone)
}

# Dilutions for new materials
DIL["Dihydro Beta Ionone"]   = 1.0   # neat per inventory
DIL["Myristic Acid Powder"]  = 0.10  # 10 % in DPG (waxy solid → must dilute)
DIL["Allyl Ionone"]          = 1.0

for k, v in SEED.items():
    ING[k] = v
    if k not in DIL:
        DIL[k] = 1.0


# ── IFRA caps (carry from v7h) ─────────────────────────────
IFRA_CAPS_ACTIVE = {
    "Bourgeonal":          5.0,
    "Hydroxycitronellal":  1190.0,
    "Isoeugenol":          24.0,
    "Coumarin":            714.0,
    "Anisaldehyde":        595.0,
    "Damascol":            6.0,
    "Indole":              12.0,
    "Helional":            83.0,
    "Bergamot FCF oil Sicilian": 595.0,
}


def ifra_check(ing, dil):
    violations = []
    for mat, max_active in IFRA_CAPS_ACTIVE.items():
        active = ing.get(mat, 0.0) * dil.get(mat, 1.0)
        if active > max_active:
            violations.append(f"{mat}: {active:.1f} µL active > {max_active:.1f} µL IFRA")
    return (len(violations) == 0), violations


# ── Brief / pillar guardrails ──────────────────────────────
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
    "Alpha Ionone", "Alpha Isomethyl Ionone",
    "Dihydro Beta Ionone",   # NEW pillar (v7i)
}
PILLAR_FLOOR_FRAC = 0.50

STOCK_CAP = {
    "Habanolide": 350.0,
    "Ambrettolide": 350.0,
}

# Cushion floor (active µL) — NON-NEGOTIABLE
CUSHION_MATERIALS = ("Hexyl Salicylate", "Benzyl Salicylate", "Mayol",
                     "Delta Decalactone", "Myristic Acid Powder")
CUSHION_FLOOR_ACTIVE = 600.0

INIT_FLOOR = dict(ING)


def cushion_active(ing, dil):
    return sum(ing.get(m, 0.0) * dil.get(m, 1.0) for m in CUSHION_MATERIALS)


def brief_ok(ing, dil):
    for blocked in OFF_BRIEF_BLOCK:
        if ing.get(blocked, 0.0) > 0.0:
            return False, f"off-brief: {blocked}"
    if ing.get("Carrot Seed EO", 0.0) > 200.0:
        return False, "Carrot Seed > 200 µL (soft-iris brief)"
    if ing.get("Bergamot FCF oil Sicilian", 0.0) > 500.0:
        return False, "Bergamot > 500 µL"
    if ing.get("Allyl Ionone", 0.0) > 0.0:
        return False, "Allyl Ionone locked OFF (per v7i brief)"
    if ing.get("Beta Ionone", 0.0) > 75.0:
        return False, "Beta Ionone > 75 µL (anosmia/adapt risk)"
    cush = cushion_active(ing, dil)
    if cush < CUSHION_FLOOR_ACTIVE:
        return False, f"cushion {cush:.0f} µL active < {CUSHION_FLOOR_ACTIVE:.0f} floor"
    sal = ing.get("Benzyl Salicylate", 0.0) + ing.get("Hexyl Salicylate", 0.0)
    if sal < 300.0:
        return False, f"salicylate {sal:.0f} < 300 µL"
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
print("  v7i — Soft-iris cushion recovery + Dihydro β-Ionone + Myristic Acid")
print("=" * 76)

g_seed = score(ING, DIL)
ok_seed, why = brief_ok(ING, DIL)
print(f"\n  v7h baseline : geo={V7H['geo']:.3f}  texture={V7H['axis']['texture']:.2f}")
print(f"  v7i seed     : geo={g_seed['geo']:.3f}  luxury={g_seed['luxury']:.2f}  "
      f"texture={g_seed['texture']:.2f}  hedonic={g_seed['hedonic']:.2f}")
print(f"  brief check  : {'OK' if ok_seed else 'FAIL — ' + why}")
print(f"  cushion seed : {cushion_active(ING, DIL):.1f} µL active "
      f"(floor {CUSHION_FLOOR_ACTIVE:.0f})")

ok_ifra, viols = ifra_check(ING, DIL)
print(f"\n  IFRA gate    : {'PASS' if ok_ifra else 'FAIL'}")
for v in viols:
    print(f"    ✗ {v}")

# Show iris-violet chord
iris_chord = [
    ("Alpha Irone",            "core — irones, slow"),
    ("Beta Ionone",            "headspace — CAPPED (OR5A1 hyposmia)"),
    ("Dihydro Beta Ionone",    "creamier-smoother β — no anosmia"),
    ("Alpha Ionone",           "headspace — no anosmia"),
    ("Alpha Isomethyl Ionone", "powder — softened by Ultralia halo"),
    ("Ultralia",               "ghost iris halo (boosted to soften AIMI)"),
    ("Orivone",                "buttery iris support"),
    ("Myristic Acid Powder",   "orris butter fatty matrix (10% DPG)"),
    ("Carrot Seed EO",         "rooty — lowered for soft brief"),
]
print("\n  IRIS-VIOLET CHORD (soft, with fatty matrix):")
for m, role in iris_chord:
    amt = ING.get(m, 0.0); d = DIL.get(m, 1.0); active = amt * d
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active  {role}")

print("\n  CUSHION REGISTER (floor ≥ 600 µL active):")
for m in CUSHION_MATERIALS:
    amt = ING.get(m, 0.0); d = DIL.get(m, 1.0); active = amt * d
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active")
print(f"    {'TOTAL':<26s}                    = {cushion_active(ING, DIL):>5.1f} µL")


# ── Bounds ─────────────────────────────────────────────────
SUB_ODT_TRACES = {"Geosmin", "Scentenal", "Indole"}
IFRA_CAPPED = {
    "Bourgeonal": 5.0,
    "Damascol": 75.0,
    "Indole": 120.0,
    "Helional": 83.0,
    "Isoeugenol": 24.0,
}


def bounds(name, cur, dil):
    if name == "Allyl Ionone":
        return 0.0, 0.0           # locked OFF
    if name in SUB_ODT_TRACES:
        ceil = max(cur * 3, cur + 50)
    elif name in IFRA_CAPPED:
        ceil = IFRA_CAPPED[name]
    elif name == "Geosmin":
        ceil = 3.0
    elif name == "Beta Ionone":
        ceil = 75.0
    elif name == "Dihydro Beta Ionone":
        ceil = 200.0              # creamier-smoother, no anosmia limit
    elif name == "Carrot Seed EO":
        ceil = 200.0              # soft-iris cap
    elif name == "Myristic Acid Powder":
        ceil = 400.0              # 10% × 400 = 40 µL active max
    elif name == "Ultralia":
        ceil = 150.0              # halo material — keep restrained
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
                print(f"    ★ pass {p} {name}: {cur_amt:.0f} → {ing[name]:.0f}  "
                      f"geo {cur_geo:.3f} → {best_geo:.3f}")
                cur_geo = best_geo
        if not improved:
            break
    print(f"  climb done: {moves} moves, {time.time()-t0:.0f}s, final geo {cur_geo:.3f}")
    return ing, dil


print("\n" + "─" * 76)
print("  CLIMB — cushion-floored, anosmia-capped, Allyl Ionone locked off")
print("─" * 76)
ING_FINAL, DIL_FINAL = climb(ING, DIL, max_passes=6)
g_final = score(ING_FINAL, DIL_FINAL)


# ── Report ─────────────────────────────────────────────────
print("\n" + "─" * 76)
print("  v7i vs v7h (default scorer)")
print("─" * 76)
print(f"\n  axis                    v7h        v7i        Δ")
for ax in ["longevity", "sillage", "luxury", "texture", "stacking_depth",
           "photorealism", "perceptual_clarity", "skin_performance",
           "synergy", "hedonic"]:
    v0 = V7H["axis"][ax]; v1 = g_final[ax]
    flag = "  ⚠" if v1 < v0 - 1.0 else ("  ✓" if v1 > v0 + 1.0 else "")
    print(f"  {ax:<22s} {v0:>7.2f}   {v1:>7.2f}    {v1-v0:+7.2f}{flag}")
print(f"\n  geo: v7h {V7H['geo']:.3f} → v7i {g_final['geo']:.3f}  "
      f"({g_final['geo']-V7H['geo']:+.3f})")

ok_final, why = brief_ok(ING_FINAL, DIL_FINAL)
ok_ifra, viols = ifra_check(ING_FINAL, DIL_FINAL)
print(f"\n  Brief guardrails: {'✓ PASS' if ok_final else '✗ FAIL — ' + why}")
print(f"  IFRA gate       : {'✓ PASS' if ok_ifra else '✗ FAIL'}")
print(f"  Cushion final   : {cushion_active(ING_FINAL, DIL_FINAL):.1f} µL active "
      f"(floor {CUSHION_FLOOR_ACTIVE:.0f})")
for v in viols:
    print(f"    ✗ {v}")

print("\n  Final IRIS-VIOLET CHORD:")
total_iris = 0.0
for m, role in iris_chord:
    amt = ING_FINAL.get(m, 0.0); d = DIL_FINAL.get(m, 1.0); active = amt * d
    total_iris += active
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active  {role}")
print(f"    {'TOTAL IRIS ACTIVE':<26s}                    = {total_iris:>5.1f} µL")

print("\n  Final CUSHION REGISTER:")
for m in CUSHION_MATERIALS:
    amt = ING_FINAL.get(m, 0.0); d = DIL_FINAL.get(m, 1.0); active = amt * d
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active")
print(f"    {'TOTAL CUSHION':<26s}                    = "
      f"{cushion_active(ING_FINAL, DIL_FINAL):>5.1f} µL")

print("\n  Δ ingredients (v7i vs v7h):")
all_keys = sorted(set(V7H_ING.keys()) | set(ING_FINAL.keys()))
for k in all_keys:
    a = V7H_ING.get(k, 0.0); b = ING_FINAL.get(k, 0.0)
    if abs(a - b) > 1e-3:
        flag = "  [IFRA]" if k in IFRA_CAPS_ACTIVE else ""
        flag += "  [NEW]" if a == 0.0 and b > 0.0 else ""
        flag += "  [REMOVED]" if a > 0.0 and b == 0.0 else ""
        print(f"    {k:<32s} {a:>7.1f} → {b:>7.1f}  ({b-a:+7.1f}){flag}")

snap = {
    "v7i": {
        "geo": g_final["geo"],
        "ing": ING_FINAL,
        "dil": DIL_FINAL,
        "axis": {ax: g_final[ax] for ax in [
            "longevity", "sillage", "luxury", "texture", "stacking_depth",
            "photorealism", "perceptual_clarity", "skin_performance",
            "synergy", "hedonic"]},
        "cushion_active": cushion_active(ING_FINAL, DIL_FINAL),
    },
    "v7h_baseline": {"geo": V7H["geo"], "axis": V7H["axis"]},
}
with open("_opt_v7i_cushion_floor.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2)
print(f"\n  snapshot → _opt_v7i_cushion_floor.json")
print("  ─── DONE ───")
