"""v7g — Heliotropal restored + musk chord rebalance.

User feedback on v7e/v7f:
  1. Heliotropal was removed by the optimizer. Brief = creamy-powdery iris
     + white floral — Heliotropal is a HERO material for that register.
     Must restore and protect.
  2. v7e leaned 1000 µL Habanolide + 700 µL Ambrettolide (both running low).
     User has plenty of: Musk Ketone (powder), Zenolide, Romandolide,
     Tonalide, Galaxolide, Ethylene Brassylate. Spread the musk chord.

Changes vs v7e:
  • Heliotropal: 0 → 60 µL (low VP solid; trace dose appropriate, protected
    in PILLARS).
  • Habanolide: 1000 → 300 µL (stock conservation; keep enough for
    skin-warmth signature only).
  • Ambrettolide (10%): 700 → 300 µL of dilution = 30 µL active (stock
    conservation; keep token natural-fruity-musk character).
  • Ethylene Brassylate: 1000 → 1300 µL (push creamy-lactonic depth axis;
    abundant stock).
  • Romandolide: 0 → 600 µL (projection axis; modern clean-woody-musk
    halo; abundant stock).
  • Zenolide: 0 → 200 µL (clean-fresh musk character-echo for the
    transparent muguet upper-heart; abundant stock).
  • Galaxolide (80%): 0 → 250 µL (projection volume; pairs with cosmetic-
    powder register; abundant).
  • Musk Ketone (10% pre-dilution in DPG): 0 → 200 µL of 10% = 20 µL
    active, powdery-talc echo for the iris-powder pillar — IFRA Cat 4
    EDP limit ~1.4 %, we are at 0.13 % (well under).
  • Tonalide (10%): 0 → 150 µL of 10% = 15 µL active, light floral-musk
    bridge.

Musk chord verification (§10 of copilot-instructions):
  • Depth axis: Ethylene Brassylate 1300 (creamy lactonic) + Ambrettolide 30
    active (fruity-natural) + Habanolide 300 (warm-skin)
  • Projection axis: Romandolide 600 + Galaxolide 80% 200 active + Zenolide 200
  • Character-echo axis: Musk Ketone 20 active (powder echo for iris) +
    Tonalide 15 active (light floral bridge)

Then climb under default scorer with brief guardrails AND musk-stock cap
(Habanolide ≤ 350, Ambrettolide ≤ 350 of 10% dilution).
"""

from __future__ import annotations
import json
import time

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula
from _opt_iris_reverie_15probes import SUB_ODT_TRACES, AIMI_CAPPED, IFRA_CAPPED


# ── Load v7e baseline ──────────────────────────────────────
with open("_opt_v7e_luxury.json", "r", encoding="utf-8") as f:
    SNAP = json.load(f)
V7E = SNAP["v7e"]
V7E_ING = {k: v for k, v in V7E["ing"].items() if v > 0.0}
V7E_DIL = dict(V7E["dil"])

scorer = FormulaScorer(synergy_graph=SynergyGraph(), weights=ObjectiveWeights())

def score(ing, dil):
    geo, detail = score_formula(ing, dil, scorer)
    out = dict(detail); out["geo"] = geo
    return out


# ── Build v7g initial from v7e with corrections ─────────
ING = dict(V7E_ING)
DIL = dict(V7E_DIL)

# Restore Heliotropal — hero material for cream-powder-iris register
ING["Heliotropal"] = 60.0          # neat
DIL["Heliotropal"] = 1.0

# Stock conservation — cut overused macrocyclics
ING["Habanolide"] = 300.0          # neat, was 1000
ING["Ambrettolide"] = 300.0        # 10% in DPG, was 700 (= 30 µL active)
DIL["Ambrettolide"] = 0.10

# Push abundant musks
ING["Ethylene Brassylate"] = 1300.0     # neat, was 1000
DIL["Ethylene Brassylate"] = 1.0

ING["Romandolide"] = 600.0              # neat
DIL["Romandolide"] = 1.0

ING["Zenolide"] = 200.0                 # neat
DIL["Zenolide"] = 1.0

ING["Galaxolide"] = 250.0               # 80% in IPM (per inventory)
DIL["Galaxolide"] = 0.80

ING["Musk Ketone"] = 200.0              # use 10% pre-dilution (powder dissolved in DPG)
DIL["Musk Ketone"] = 0.10

ING["Tonalide"] = 150.0                 # 10% in DPG (per inventory)
DIL["Tonalide"] = 0.10

# Salicylate cushion — fix v7e's drift; brief implies fuller cosmetic veil
# Bump Hexyl Sal from 250 → 400 (light, transparent — pairs with iris)
ING["Hexyl Salicylate"] = 400.0


# ── Brief-direction guardrails ─────────────────────────────
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
    "Heliotropal",                          # ← protected hero material
    "Ethylene Brassylate", "Romandolide",   # ← new musk pillars
    "Habanolide", "Ambrettolide", "Ambrox Super",
    "Bergamot FCF oil Sicilian", "Iso E Super",
}
PILLAR_FLOOR_FRAC = 0.50

# Stock caps — these materials are running low
STOCK_CAP = {
    "Habanolide": 350.0,
    "Ambrettolide": 350.0,
}


def brief_ok(ing):
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
    for p in PILLARS:
        b = INIT_FLOOR.get(p, 0.0)
        if b > 0.0 and ing.get(p, 0.0) < b * PILLAR_FLOOR_FRAC:
            return False, f"pillar {p} below 50% floor"
    for mat, cap in STOCK_CAP.items():
        if ing.get(mat, 0.0) > cap:
            return False, f"{mat} exceeds stock cap {cap:.0f}"
    return True, ""


# Snapshot floor for pillar-protection BEFORE climbing
INIT_FLOOR = dict(ING)

ok, why = brief_ok(ING)
g0 = score(ING, DIL)
print("=" * 76)
print("  v7g — Heliotropal restored + musk chord rebalance")
print("=" * 76)
print(f"\n  v7e baseline: geo={V7E['geo']:.3f}")
print(f"  v7g initial : geo={g0['geo']:.3f}  luxury={g0['luxury']:.2f}  hedonic={g0['hedonic']:.2f}")
print(f"  brief check : {'OK' if ok else 'FAIL — ' + why}")

# Show musk chord
print("\n  MUSK CHORD (active µL):")
musks = [
    ("Ethylene Brassylate", "depth — creamy-lactonic"),
    ("Habanolide",          "depth — warm-skin"),
    ("Ambrettolide",        "depth — fruity-natural"),
    ("Romandolide",         "projection — clean modern halo"),
    ("Galaxolide",          "projection — fruity-floral cushion"),
    ("Zenolide",            "projection — clean-fresh"),
    ("Musk Ketone",         "echo — powder/talc (iris)"),
    ("Tonalide",            "echo — light floral bridge"),
]
for m, role in musks:
    amt = ING.get(m, 0.0)
    dilu = DIL.get(m, 1.0)
    active = amt * dilu
    if amt > 0:
        print(f"    {m:<22s} {amt:>6.0f} µL × {dilu:.2f} = {active:>6.1f} µL active   {role}")


# ── Bounds ─────────────────────────────────────────
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
    # apply stock caps as ceiling
    if name in STOCK_CAP:
        ceil = min(ceil, STOCK_CAP[name])
    floor = 1.0 if name == "Geosmin" else (
        max(5.0, cur * 0.1) if name in SUB_ODT_TRACES else 0.0)
    return floor, ceil


STEPS = [+200, +100, +50, +25, +15, +10, -200, -100, -50, -25, -15, -10]


def climb(ing, dil, max_passes=8):
    cur = score(ing, dil)
    cur_geo = cur["geo"]
    moves = 0
    t0 = time.time()
    for p in range(1, max_passes + 1):
        improved = False
        for name in list(ing.keys()):
            cur_amt = ing[name]
            floor, ceil = bounds(name, cur_amt)
            best_step, best_geo = None, cur_geo
            for s in STEPS:
                new_amt = cur_amt + s
                if new_amt < floor or new_amt > ceil:
                    continue
                test_ing = dict(ing); test_ing[name] = new_amt
                ok, _ = brief_ok(test_ing)
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


# ── Climb ─────────────
print("\n" + "─" * 76)
print("  CLIMB — default weights, brief guardrails, stock caps")
print("─" * 76)
ING_FINAL, DIL_FINAL = climb(ING, DIL, max_passes=6)
g_final = score(ING_FINAL, DIL_FINAL)


# ── Report ─────────────
print("\n" + "─" * 76)
print("  v7g vs v7e (default scorer)")
print("─" * 76)
print(f"\n  axis                    v7e        v7g        Δ")
for ax in ["longevity", "sillage", "luxury", "texture", "stacking_depth",
           "photorealism", "perceptual_clarity", "skin_performance",
           "synergy", "hedonic"]:
    v0 = V7E["axis"][ax]; v1 = g_final[ax]
    flag = "  ⚠" if v1 < v0 - 1.0 else ""
    print(f"  {ax:<22s} {v0:>7.2f}   {v1:>7.2f}    {v1-v0:+7.2f}{flag}")
print(f"\n  geo: v7e {V7E['geo']:.3f} → v7g {g_final['geo']:.3f}  ({g_final['geo']-V7E['geo']:+.3f})")

ok_final, why = brief_ok(ING_FINAL)
print(f"\n  Brief guardrails: {'✓ PASS' if ok_final else '✗ FAIL — ' + why}")

# Stock-conservative musk verification
print("\n  Final musk chord (active µL):")
total_active = 0.0
for m, role in musks:
    amt = ING_FINAL.get(m, 0.0)
    dilu = DIL_FINAL.get(m, 1.0)
    active = amt * dilu
    total_active += active
    if amt > 0:
        print(f"    {m:<22s} {amt:>6.0f} µL × {dilu:.2f} = {active:>6.1f} µL active   {role}")
print(f"    {'TOTAL ACTIVE MUSK':<22s}                       = {total_active:>6.1f} µL")
print(f"    (v7e was: Habanolide 1000 + Ambrettolide 70 active + EB 1000 = 2070 µL active)")

print("\n  Δ ingredients (v7g vs v7e):")
all_keys = sorted(set(V7E_ING.keys()) | set(ING_FINAL.keys()))
for k in all_keys:
    a = V7E_ING.get(k, 0.0); b = ING_FINAL.get(k, 0.0)
    if abs(a - b) > 1e-3:
        print(f"    {k:<36s} {a:>7.1f} → {b:>7.1f}  ({b-a:+.1f})")

snap = {
    "v7g": {
        "geo": g_final["geo"],
        "ing": ING_FINAL,
        "dil": DIL_FINAL,
        "axis": {ax: g_final[ax] for ax in [
            "longevity", "sillage", "luxury", "texture", "stacking_depth",
            "photorealism", "perceptual_clarity", "skin_performance",
            "synergy", "hedonic"]},
    },
    "v7e_baseline": {"geo": V7E["geo"], "axis": V7E["axis"]},
}
with open("_opt_v7g_helio_musk.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2)
print(f"\n  snapshot → _opt_v7g_helio_musk.json")
print("  ─── DONE ───")
