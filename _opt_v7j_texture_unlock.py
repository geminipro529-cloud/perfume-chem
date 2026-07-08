"""v7j — Texture unlock from v7i.

Diagnostic finding (April 2026):
  v7i texture stayed flat at 73.7 vs v7h 73.8 because
  (a) richness sub-score is GATED at "active tactile facets > 2.0".
      Roundness reached 1.87 — JUST below the 2.0 threshold.
      Crossing 2.0 = instant +7 richness pts.
  (b) climber pulled Hedione 1700 → 1500 to chase geo elsewhere,
      cutting silkiness (Hedione is #1 contributor to floral &
      transparency dims, both feeding silkiness × 2.5 fit).

v7j fix levers:
  1) LOCK Hedione (standard) ≥ 1700 µL — climber forbidden to reduce.
  2) Cap Hedione HC at 800 (current) — DO NOT let climber push higher
     (HC is expensive; user does not want to lean on it).
  3) ADD Heliotropal (Piperonal, neat) 300 µL — pushes
     creamy + sweetness + powdery (3 dims feeding roundness threshold
     AND silkiness). Brief-perfect for L'Heure Bleue / Infusion d'Iris
     (the canonical iris–heliotrope–coumarin Guerlain triad).
  4) ADD Coumarin (20% dilution) 150 µL of dilution = 30 µL active —
     warmth + sweetness + powdery, classic coumarinic-iris pairing.
     Well under IFRA cap (714 µL active).

Carries forward from v7i:
  - Allyl Ionone locked OFF (Dihydro β replaces it).
  - β-Ionone hard cap 75 µL (anosmia OR5A1).
  - Cushion floor 600 µL active.
  - Salicylate floor 300 µL.
  - All IFRA caps + stock caps (Habanolide 350, Ambrettolide 350).
  - Off-brief block list.
  - Carrot Seed EO ≤ 200 µL.
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

# ── Load v7i baseline ──────────────────────────────────────
with open("_opt_v7i_cushion_floor.json", "r", encoding="utf-8") as f:
    SNAP_I = json.load(f)
V7I = SNAP_I["v7i"]
V7I_ING = dict(V7I["ing"])
DIL = dict(V7I["dil"])

# Also load v7h for full comparison
with open("_opt_v7h_ifra_iris.json", "r", encoding="utf-8") as f:
    SNAP_H = json.load(f)
V7H = SNAP_H["v7h"]

ING = copy.deepcopy(V7I_ING)


def score(ing, dil):
    geo, detail = score_formula(ing, dil, scorer)
    return {"geo": geo, **detail}


# ── v7j SEED CHANGES ───────────────────────────────────────
HEDIONE_LOCK = 1700.0     # standard Hedione minimum, climber forbidden below
HEDIONE_HC_CAP = 800.0    # HC ceiling — expensive, don't push higher

# Roundness-feeders — LOCK floors so climber cannot unwind
# (v7j first run: climber halved Heliotropal & Delta Decalactone for geo)
HELIOTROPAL_FLOOR    = 300.0
DELTA_DEC_FLOOR      = 200.0
DIHYDRO_BETA_FLOOR   = 100.0

SEED = {
    # 1) RESTORE Hedione (climber cut it 1700 → 1500 in v7i)
    "Hedione": HEDIONE_LOCK,

    # 2) Add Heliotropal — sweet-almond-heliotrope-powdery, base, neat
    "Heliotropal": 300.0,

    # 3) Add Coumarin (20% dil) — warmth + sweetness + powdery
    "Coumarin": 150.0,        # 150 µL of 20% = 30 µL active
}

# Dilutions
if "Heliotropal" not in DIL:
    DIL["Heliotropal"] = 1.0      # neat per inventory (added 2026-04-17)
if "Coumarin" not in DIL:
    DIL["Coumarin"] = 0.20        # 20 % in DPG (standard handling)

for k, v in SEED.items():
    ING[k] = v


# ── IFRA caps (carry from v7i) ─────────────────────────────
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
    "Dihydro Beta Ionone",
}
PILLAR_FLOOR_FRAC = 0.50

STOCK_CAP = {
    "Habanolide": 350.0,
    "Ambrettolide": 350.0,
    "Hedione HC": HEDIONE_HC_CAP,   # expensive — no climbing up
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
        return False, "Allyl Ionone locked OFF (per v7i+ brief)"
    if ing.get("Beta Ionone", 0.0) > 75.0:
        return False, "Beta Ionone > 75 µL (anosmia/adapt risk)"
    # v7j hard locks
    if ing.get("Hedione", 0.0) < HEDIONE_LOCK:
        return False, f"Hedione < {HEDIONE_LOCK:.0f} µL lock (texture fit)"
    if ing.get("Hedione HC", 0.0) > HEDIONE_HC_CAP:
        return False, f"Hedione HC > {HEDIONE_HC_CAP:.0f} µL cap (cost)"
    if ing.get("Heliotropal", 0.0) < HELIOTROPAL_FLOOR:
        return False, f"Heliotropal < {HELIOTROPAL_FLOOR:.0f} (roundness lock)"
    if ing.get("Delta Decalactone", 0.0) < DELTA_DEC_FLOOR:
        return False, f"Delta Decalactone < {DELTA_DEC_FLOOR:.0f} (roundness lock)"
    if ing.get("Dihydro Beta Ionone", 0.0) < DIHYDRO_BETA_FLOOR:
        return False, f"Dihydro β Ionone < {DIHYDRO_BETA_FLOOR:.0f} (creamy lock)"
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
            return False, f"{mat} exceeds cap {cap:.0f}"
    ok_ifra, viols = ifra_check(ing, dil)
    if not ok_ifra:
        return False, f"IFRA: {viols[0]}"
    return True, ""


print("=" * 76)
print("  v7j — Texture unlock: Hedione lock + Heliotropal + Coumarin")
print("=" * 76)

g_seed = score(ING, DIL)
ok_seed, why = brief_ok(ING, DIL)
print(f"\n  v7h baseline : geo={V7H['geo']:.3f}  texture={V7H['axis']['texture']:.2f}")
print(f"  v7i baseline : geo={V7I['geo']:.3f}  texture={V7I['axis']['texture']:.2f}")
print(f"  v7j seed     : geo={g_seed['geo']:.3f}  luxury={g_seed['luxury']:.2f}  "
      f"texture={g_seed['texture']:.2f}  hedonic={g_seed['hedonic']:.2f}")
print(f"  brief check  : {'OK' if ok_seed else 'FAIL — ' + why}")
print(f"  cushion seed : {cushion_active(ING, DIL):.1f} µL active "
      f"(floor {CUSHION_FLOOR_ACTIVE:.0f})")

ok_ifra, viols = ifra_check(ING, DIL)
print(f"\n  IFRA gate    : {'PASS' if ok_ifra else 'FAIL'}")
for v in viols:
    print(f"    ✗ {v}")

# Show new texture-unlock chord
unlock_chord = [
    ("Hedione",                 f"LOCKED ≥ {HEDIONE_LOCK:.0f} (silkiness fit)"),
    ("Hedione HC",              f"capped ≤ {HEDIONE_HC_CAP:.0f} (cost)"),
    ("Heliotropal",             "NEW — sweet-almond-powdery (creamy+sweet+powder)"),
    ("Coumarin",                "NEW — coumarinic-iris pairing (warm+sweet+powder)"),
]
print("\n  TEXTURE UNLOCK CHORD:")
for m, role in unlock_chord:
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
    if name == "Hedione":
        # LOCK floor at 1700 — climber cannot reduce
        return HEDIONE_LOCK, 2400.0
    if name == "Hedione HC":
        # CAP — climber cannot increase past current 800 (cost)
        return cur * 0.5, HEDIONE_HC_CAP
    if name == "Heliotropal":
        return HELIOTROPAL_FLOOR, 500.0
    if name == "Delta Decalactone":
        return DELTA_DEC_FLOOR, 400.0
    if name == "Dihydro Beta Ionone":
        return DIHYDRO_BETA_FLOOR, 200.0
    if name in SUB_ODT_TRACES:
        ceil = max(cur * 3, cur + 50)
    elif name in IFRA_CAPPED:
        ceil = IFRA_CAPPED[name]
    elif name == "Geosmin":
        ceil = 3.0
    elif name == "Beta Ionone":
        ceil = 75.0
    elif name == "Carrot Seed EO":
        ceil = 200.0
    elif name == "Myristic Acid Powder":
        ceil = 400.0              # 10% × 400 = 40 µL active max
    elif name == "Ultralia":
        ceil = 150.0
    elif name == "Coumarin":
        # IFRA cap 714 active; at 20% dil → ceil 3570 µL of dilution
        # but practical taste cap ~600 µL of dilution = 120 µL active
        ceil = 600.0
    else:
        ceil = 2000.0
    if name in STOCK_CAP and name not in ("Hedione HC",):
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
print("  CLIMB — Hedione locked ≥ 1700, HC capped ≤ 800, cushion-floored")
print("─" * 76)
ING_FINAL, DIL_FINAL = climb(ING, DIL, max_passes=6)
g_final = score(ING_FINAL, DIL_FINAL)


# ── Report ─────────────────────────────────────────────────
print("\n" + "─" * 76)
print("  v7j vs v7i vs v7h (default scorer)")
print("─" * 76)
print(f"\n  axis                    v7h        v7i        v7j        Δ(v7j−v7i)")
for ax in ["longevity", "sillage", "luxury", "texture", "stacking_depth",
           "photorealism", "perceptual_clarity", "skin_performance",
           "synergy", "hedonic"]:
    v0 = V7H["axis"][ax]; v1 = V7I["axis"][ax]; v2 = g_final[ax]
    flag = "  ⚠" if v2 < v1 - 1.0 else ("  ✓" if v2 > v1 + 1.0 else "")
    print(f"  {ax:<22s} {v0:>7.2f}   {v1:>7.2f}   {v2:>7.2f}   {v2-v1:+7.2f}{flag}")
print(f"\n  geo: v7h {V7H['geo']:.3f} → v7i {V7I['geo']:.3f} → v7j {g_final['geo']:.3f}")

ok_final, why = brief_ok(ING_FINAL, DIL_FINAL)
ok_ifra, viols = ifra_check(ING_FINAL, DIL_FINAL)
print(f"\n  Brief guardrails: {'✓ PASS' if ok_final else '✗ FAIL — ' + why}")
print(f"  IFRA gate       : {'✓ PASS' if ok_ifra else '✗ FAIL'}")
print(f"  Cushion final   : {cushion_active(ING_FINAL, DIL_FINAL):.1f} µL active "
      f"(floor {CUSHION_FLOOR_ACTIVE:.0f})")
print(f"  Hedione final   : {ING_FINAL.get('Hedione', 0):.0f} µL  "
      f"(lock ≥ {HEDIONE_LOCK:.0f})")
print(f"  Hedione HC final: {ING_FINAL.get('Hedione HC', 0):.0f} µL  "
      f"(cap ≤ {HEDIONE_HC_CAP:.0f})")
for v in viols:
    print(f"    ✗ {v}")

print("\n  Final TEXTURE UNLOCK CHORD:")
for m, role in unlock_chord:
    amt = ING_FINAL.get(m, 0.0); d = DIL_FINAL.get(m, 1.0); active = amt * d
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active  {role}")

print("\n  Final CUSHION REGISTER:")
for m in CUSHION_MATERIALS:
    amt = ING_FINAL.get(m, 0.0); d = DIL_FINAL.get(m, 1.0); active = amt * d
    if amt > 0:
        print(f"    {m:<26s} {amt:>5.0f} µL × {d:.2f} = {active:>5.1f} µL active")
print(f"    {'TOTAL CUSHION':<26s}                    = "
      f"{cushion_active(ING_FINAL, DIL_FINAL):>5.1f} µL")

print("\n  Δ ingredients (v7j vs v7i):")
all_keys = sorted(set(V7I_ING.keys()) | set(ING_FINAL.keys()))
for k in all_keys:
    a = V7I_ING.get(k, 0.0); b = ING_FINAL.get(k, 0.0)
    if abs(a - b) > 1e-3:
        flag = "  [IFRA]" if k in IFRA_CAPS_ACTIVE else ""
        flag += "  [NEW]" if a == 0.0 and b > 0.0 else ""
        flag += "  [REMOVED]" if a > 0.0 and b == 0.0 else ""
        print(f"    {k:<32s} {a:>7.1f} → {b:>7.1f}  ({b-a:+7.1f}){flag}")

snap = {
    "v7j": {
        "geo": g_final["geo"],
        "ing": ING_FINAL,
        "dil": DIL_FINAL,
        "axis": {ax: g_final[ax] for ax in [
            "longevity", "sillage", "luxury", "texture", "stacking_depth",
            "photorealism", "perceptual_clarity", "skin_performance",
            "synergy", "hedonic"]},
        "cushion_active": cushion_active(ING_FINAL, DIL_FINAL),
        "hedione_lock": HEDIONE_LOCK,
        "hedione_hc_cap": HEDIONE_HC_CAP,
    },
    "v7i_baseline": {"geo": V7I["geo"], "axis": V7I["axis"]},
    "v7h_baseline": {"geo": V7H["geo"], "axis": V7H["axis"]},
}
with open("_opt_v7j_texture_unlock.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2)

# ── Re-run texture diagnostic on v7j final ────────────────
print("\n" + "─" * 76)
print("  TEXTURE DIAGNOSTIC — v7j final (does roundness cross 2.0?)")
print("─" * 76)
try:
    from _diag_texture_v7i import replay_texture
    rj = replay_texture(ING_FINAL, DIL_FINAL, "v7j")
except Exception as e:
    print(f"  diag failed: {e}")
print(f"\n  snapshot → _opt_v7j_texture_unlock.json")
print("  ─── DONE ───")
