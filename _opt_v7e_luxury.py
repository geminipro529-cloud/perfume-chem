"""v7e — push luxury axis from v7d-add baseline.

Strategy:
  A. Diagnostic: break v7d-add luxury into its 6 sub-components.
  B. Shadow plateau seeding — add 4–8 sub-ODT trace materials
     (target dose_ratio 0.1–1.0). Score's trace_score is currently 0
     because v7d-add has zero materials in the shadow zone.
  C. Premium captive density push — try lifting under-dosed canonical
     premium synthetics already present (Javanol, Helional, Cashmeran)
     or adding more (Paradisone, Polysantol) within IFRA/inventory.
  D. Carles architecture — check note balance vs target 18/42/40
     and try shifts that close the gap.
  E. Re-climb the full default scorer after each gain.

Output: _opt_v7e_luxury_out.txt and _opt_v7e_luxury.json snapshot.
"""

from __future__ import annotations
import copy
import json
import math
import time

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from _scale_30mL_verify_nonlinear import score_formula
from _opt_iris_reverie_15probes import SUB_ODT_TRACES, AIMI_CAPPED, IFRA_CAPPED


# ── Load v7d-add winner as baseline ──────────────────────────────────
with open("_opt_v7d_reclimb.json", "r", encoding="utf-8") as f:
    SNAP = json.load(f)
V7D = SNAP["v7d_add"]
ING0 = dict(V7D["ing"])
DIL0 = dict(V7D["dil"])

scorer = FormulaScorer(synergy_graph=SynergyGraph(), weights=ObjectiveWeights())


def score(ing, dil):
    geo, detail = score_formula(ing, dil, scorer)
    out = dict(detail); out["geo"] = geo
    return out


def _to_fv(ing, dil):
    fi = FormulaInfo(number=0, name="X", ingredients=ing, dilutions=dil,
                     concentrate_ml=sum(ing.values()) / 1000.0, description="")
    return formula_to_vector(fi)


def luxury_breakdown(ing, dil):
    """Replicate score_luxury sub-component math for diagnostic."""
    fv = _to_fv(ing, dil)
    eff = fv.effective_ingredients()
    total_pct = sum(eff.values()) or 1.0

    PREMIUM = {
        "ambrettolide", "habanolide", "romandolide", "ethylene brassylate",
        "exaltolide", "muscenone", "nirvanolide", "velvione", "zenolide",
        "macrolide", "ambrox super", "ambrox", "ambrofix", "ambermax",
        "amberwood f", "cetalox", "ysamber k", "cedramber", "cedamber",
        "iso e super", "javanol", "ebanol", "bacdanol", "sandalore",
        "polysantol", "norlimbanol", "norlimbanol dextro", "clearwood",
        "timberol", "kephalis", "koavone", "vertofix coeur", "azarbre",
        "cashmeran", "georgywood", "okoumal", "sylvamber",
        "hedione", "hedione hc", "paradisone", "methyl dihydrojasmonate",
        "dbca", "lilyreal", "mayol", "bourgeonal", "florhydral",
        "cyclamen aldehyde", "alpha irone", "alpha ionone",
        "beta ionone", "methyl ionone", "orivone", "ultralia",
        "farnesol", "paradisamide", "peonile",
        "helional", "scentenal", "floralozone", "calone", "triplal",
        "lactoscone", "prismantol", "gamma decalactone", "delta decalactone",
        "hexyl salicylate", "benzyl salicylate",
    }
    NAT_SFX = ("eo", "absolute", "resinoid", "co2")
    PRE_MK = ("ftec", " fo", "fleuressence", "accord", "core")

    nat_mass = prem_mass = pre_mass = 0.0
    n_decl = shadow = silent = 0
    note_mass = {"top": 0.0, "heart": 0.0, "base": 0.0}
    or_counts: dict[str, int] = {}
    dom_counts: dict[str, int] = {}

    for name, pct in eff.items():
        norm = normalize_name(name)
        prof = get_profile(name)
        odt = getattr(prof, "odt_ppm", None) if prof else None
        gamma = getattr(prof, "activity_coef", 1.0) if prof else 1.0
        ratio = 0.0
        is_shadow = is_silent = False
        if odt and odt > 0:
            ratio = pct * 10000.0 * max(gamma, 0.1) / odt
            if ratio < 0.1:
                is_silent = True
            elif ratio <= 1.0:
                is_shadow = True
        if is_silent:
            silent += 1
            continue
        if is_shadow:
            shadow += 1
            continue
        if any(m in norm for m in PRE_MK):
            pre_mass += pct
        if any(norm.endswith(s) for s in NAT_SFX) and not any(m in norm for m in PRE_MK):
            nat_mass += pct
        if norm in PREMIUM:
            prem_mass += pct
        n_decl += 1
        if prof:
            dom = prof.dominant_character()
            if dom and dom != "neutral":
                dom_counts[dom] = dom_counts.get(dom, 0) + 1
            if prof.or_family:
                or_counts[prof.or_family] = or_counts.get(prof.or_family, 0) + 1
            note = prof.note if prof.note in note_mass else "heart"
            note_mass[note] += pct

    nat_frac = nat_mass / total_pct
    prem_frac = prem_mass / total_pct
    pre_frac = pre_mass / total_pct
    note_total = sum(note_mass.values()) or 1.0
    note_frac = {k: v / note_total for k, v in note_mass.items()}

    if nat_frac <= 0.05:
        nat_score = nat_frac / 0.05 * 8.0
    elif nat_frac <= 0.12:
        nat_score = 8.0 + (nat_frac - 0.05) / 0.07 * 6.0
    elif nat_frac <= 0.30:
        nat_score = 14.0 + (nat_frac - 0.12) / 0.18 * 6.0
    elif nat_frac <= 0.40:
        nat_score = 20.0
    else:
        nat_score = max(12.0, 20.0 - (nat_frac - 0.40) * 20.0)

    prem_score = max(0.0, min(prem_frac / 0.25 * 20.0, 20.0) - pre_frac * 30.0)

    target = {"top": 0.18, "heart": 0.42, "base": 0.40}
    dev = sum(abs(note_frac[k] - target[k]) for k in target)
    arch_score = max(0.0, 15.0 - dev * 15.0)

    if shadow < 2:
        trace_score = shadow / 2.0 * 6.0
    elif shadow <= 10:
        trace_score = 6.0 + (shadow - 2) / 8.0 * 9.0
    elif shadow <= 14:
        trace_score = 15.0 - (shadow - 10) * 0.5
    else:
        trace_score = max(8.0, 13.0 - (shadow - 14) * 0.5)

    redundancy = sum(max(0, c - 2) for c in dom_counts.values())
    or_overload = sum(max(0, c - 3) for c in or_counts.values())

    return {
        "n_declared": n_decl,
        "shadow": shadow,
        "silent": silent,
        "nat_frac": nat_frac,
        "prem_frac": prem_frac,
        "pre_frac": pre_frac,
        "note_frac": note_frac,
        "nat_score": nat_score,
        "prem_score": prem_score,
        "arch_score": arch_score,
        "trace_score": trace_score,
        "redundancy": redundancy,
        "or_overload": or_overload,
        "or_counts": or_counts,
        "dom_counts": dom_counts,
    }


# ───────────── Diagnostic ─────────────
print("=" * 76)
print("  v7e — luxury push from v7d-add")
print("=" * 76)
g0 = score(ING0, DIL0)
b0 = luxury_breakdown(ING0, DIL0)
print(f"\n  v7d-add geo (default): {g0['geo']:.3f}  luxury={g0['luxury']:.2f}")
print(f"\n  Luxury sub-components (v7d-add):")
print(f"    natural_score   : {b0['nat_score']:5.2f} / 20   (nat_frac={b0['nat_frac']*100:.2f}%, target 12-30%)")
print(f"    premium_score   : {b0['prem_score']:5.2f} / 20   (prem_frac={b0['prem_frac']*100:.2f}%, target ≥25%)")
print(f"    architecture    : {b0['arch_score']:5.2f} / 15   (note_frac t/h/b = "
      f"{b0['note_frac']['top']*100:.0f}/{b0['note_frac']['heart']*100:.0f}/{b0['note_frac']['base']*100:.0f}, "
      f"target 18/42/40)")
print(f"    trace_shadow    : {b0['trace_score']:5.2f} / 15   (shadow_count={b0['shadow']}, target 2-10)")
print(f"    declared notes  : {b0['n_declared']}   silent={b0['silent']}")
print(f"    OR families >3  : overload={b0['or_overload']}   "
      f"counts={ {k:v for k,v in b0['or_counts'].items() if v>2} }")
print(f"    dominant >2     : redundancy={b0['redundancy']}   "
      f"counts={ {k:v for k,v in b0['dom_counts'].items() if v>1} }")

# ───────────── Strategy B — Shadow plateau seeding ─────────────
# Add rare/premium materials at sub-ODT trace doses (target ratio 0.1-1.0).
# Pick materials NOT already in formula and with known ODT.
# Goal: shadow_count 0 → 4-6 (worth ~+9-12 luxury points raw,
# weighted ~+0.7-1.0 on composite at luxury weight 0.8/9 axes ≈ 0.09).

# Format: (name, dilution, dose_µL).
# Doses sized so dose_ratio falls in [0.15, 0.7] given known ODTs.
SHADOW_CANDIDATES = [
    # Premium captives at extreme trace
    ("Paradisone", 1.0, 30),       # premium hedione cousin
    ("Cashmeran", 0.20, 25),       # premium cashmere wood
    ("Norlimbanol Dextro", 0.10, 15),  # premium dry wood
    ("Velvione", 0.10, 30),        # premium musk
    ("Romandolide", 1.0, 25),      # premium projection musk
    ("Sylvamber", 0.10, 25),       # premium amber
    # Naturals (also lift natural_score)
    ("Vetiver EO", 1.0, 50),
    ("Patchouli EO", 1.0, 25),
    ("Jasmine Sambac Absolute", 1.0, 15),
    ("Rose Otto", 1.0, 10),
    ("Clary Sage EO", 1.0, 25),
    # Premium florals
    ("Cyclamen Aldehyde", 0.10, 20),
    ("Florhydral", 0.10, 20),
    ("Methyl Ionone", 1.0, 25),
]

print("\n" + "─" * 76)
print("  STEP B — Shadow-plateau probe")
print("─" * 76)

results = []
for name, d, ul in SHADOW_CANDIDATES:
    if name in ING0:
        continue
    prof = get_profile(name)
    if not prof:
        results.append((name, None, None, "no profile"))
        continue
    ing_t = dict(ING0); ing_t[name] = float(ul)
    dil_t = dict(DIL0)
    if d != 1.0:
        dil_t[name] = d
    g = score(ing_t, dil_t)
    b = luxury_breakdown(ing_t, dil_t)
    dlx = b["nat_score"] + b["prem_score"] + b["arch_score"] + b["trace_score"] - (
        b0["nat_score"] + b0["prem_score"] + b0["arch_score"] + b0["trace_score"])
    note = "shadow" if b["shadow"] > b0["shadow"] else (
        "declared" if b["n_declared"] > b0["n_declared"] else "silent")
    results.append((name, g["geo"], g["luxury"], f"{note} (Δgeo={g['geo']-g0['geo']:+.3f} Δlux={g['luxury']-g0['luxury']:+.2f} Δsubs={dlx:+.2f})"))
    print(f"    + {name:<28s} {ul:>4d}µL @ {d:>4.2g}: geo={g['geo']:.3f}  lux={g['luxury']:.2f}  {results[-1][3]}")

# ───────────── Strategy: greedily add the top-K shadow-positive picks ─────────────
print("\n" + "─" * 76)
print("  STEP C — Greedy multi-add (shadow plateau)")
print("─" * 76)

# Sort by Δgeo positive picks
positive = [(n, g, lx, msg) for n, g, lx, msg in results if g and g > g0["geo"]]
positive.sort(key=lambda t: -t[1])
print(f"  positive picks: {len(positive)}")
for n, g, lx, msg in positive:
    print(f"    {n:<28s} geo={g:.3f}  lux={lx:.2f}")

ing_g = dict(ING0); dil_g = dict(DIL0)
for n, g_indiv, lx_indiv, _ in positive[:6]:
    cand = next(c for c in SHADOW_CANDIDATES if c[0] == n)
    name, d, ul = cand
    test_ing = dict(ing_g); test_ing[name] = float(ul)
    test_dil = dict(dil_g)
    if d != 1.0:
        test_dil[name] = d
    g_new = score(test_ing, test_dil)
    cur_geo = score(ing_g, dil_g)["geo"]
    if g_new["geo"] > cur_geo + 0.01:
        ing_g, dil_g = test_ing, test_dil
        print(f"    ★ keep {name} (geo {cur_geo:.3f} → {g_new['geo']:.3f})")
    else:
        print(f"    - drop {name} (geo {cur_geo:.3f} → {g_new['geo']:.3f}, masking)")

g_after_seed = score(ing_g, dil_g)
b_after_seed = luxury_breakdown(ing_g, dil_g)
print(f"\n  after greedy seed: geo={g_after_seed['geo']:.3f}  luxury={g_after_seed['luxury']:.2f}  shadow={b_after_seed['shadow']}")
print(f"    Δ vs v7d-add: geo {g_after_seed['geo']-g0['geo']:+.3f}  luxury {g_after_seed['luxury']-g0['luxury']:+.2f}")

# ───────────── Strategy D — Climb from seeded baseline ─────────────
print("\n" + "─" * 76)
print("  STEP D — Hill-climb from seeded baseline (default weights)")
print("─" * 76)

STEPS = [+200, +100, +50, +25, +15, +10, -200, -100, -50, -25, -15, -10]
THR = 0.02
MAX_PASSES = 8


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


t0 = time.time()
moves = 0
cur_score = score(ing_g, dil_g)

# ── D1 — Prune pass: try removing each material; restraint score
#       (redundancy + or_overload) currently drains luxury heavily.
print("  D1 — prune pass (try drop each material):")
removable = sorted(ing_g.keys(), key=lambda k: ing_g[k])  # smallest first
for name in removable:
    if name in {"Hedione", "Hedione HC", "Iso E Super", "Benzoin Resinoid",
                "Habanolide", "Ethylene Brassylate", "Ambrettolide", "Ambrox Super",
                "Ebanol", "Bergamot FCF Sicilian", "Alpha Irone"}:
        continue  # keep structural pillars
    test_ing = {k: v for k, v in ing_g.items() if k != name}
    test_dil = {k: v for k, v in dil_g.items() if k != name}
    g_new = score(test_ing, test_dil)
    if g_new["geo"] > cur_score["geo"] + 0.005:
        old_geo = cur_score["geo"]; old_lux = cur_score["luxury"]
        ing_g, dil_g = test_ing, test_dil
        cur_score = g_new
        moves += 1
        print(f"    ✂ drop {name:<28s} geo {old_geo:.3f}→{g_new['geo']:.3f}  lux {old_lux:.2f}→{g_new['luxury']:.2f}")

# ── D2 — Carles architecture rebalance: lift top-mass, trim base-mass
#       Current 12/40/48 → target 18/42/40. Need ~6 pp from base→top.
print("\n  D2 — architecture rebalance (lift top, trim base):")
TOP_BOOSTS = ["Bergamot FCF Sicilian", "Ethyl Linalool", "Bourgeonal",
              "Lilyreal ND", "Mayol", "Hydroxycitronellal", "Freesia HDI"]
BASE_TRIMS = ["Benzoin Resinoid", "Ethylene Brassylate", "Habanolide",
              "Ebanol", "Hexyl Salicylate", "Benzyl Salicylate",
              "Cedarwood EO", "Orivone"]
for name in TOP_BOOSTS:
    if name not in ing_g: continue
    cur = ing_g[name]
    for step in [+200, +100, +50]:
        test_ing = dict(ing_g); test_ing[name] = cur + step
        g_new = score(test_ing, dil_g)
        if g_new["geo"] > cur_score["geo"] + 0.01:
            ing_g = test_ing; cur_score = g_new; moves += 1
            print(f"    ▲ {name:<26s} {cur:.0f}→{cur+step:.0f}  geo {g_new['geo']:.3f}  lux {g_new['luxury']:.2f}")
            break
for name in BASE_TRIMS:
    if name not in ing_g: continue
    cur = ing_g[name]
    for step in [-300, -200, -100, -50]:
        if cur + step < 50: continue
        test_ing = dict(ing_g); test_ing[name] = cur + step
        g_new = score(test_ing, dil_g)
        if g_new["geo"] > cur_score["geo"] + 0.01:
            ing_g = test_ing; cur_score = g_new; moves += 1
            print(f"    ▼ {name:<26s} {cur:.0f}→{cur+step:.0f}  geo {g_new['geo']:.3f}  lux {g_new['luxury']:.2f}")
            break

# ── D3 — Standard hill-climb to settle ──
print("\n  D3 — full hill-climb:")
for p in range(1, MAX_PASSES + 1):
    improved = False
    for name in list(ing_g.keys()):
        cur = ing_g[name]
        floor, ceil = bounds(name, cur)
        for step in STEPS:
            tgt = cur + step
            if tgt < floor or tgt > ceil:
                continue
            test_ing = dict(ing_g); test_ing[name] = tgt
            g_new = score(test_ing, dil_g)
            if g_new["geo"] > cur_score["geo"] + THR:
                ing_g = test_ing
                old = cur
                cur_score = g_new
                cur = tgt
                moves += 1
                improved = True
                print(f"    ★ pass {p} {name}: {old:.0f} → {tgt:.0f}  geo {cur_score['geo']:.3f}")
                break
    if not improved:
        break

g_final = cur_score
b_final = luxury_breakdown(ing_g, dil_g)
print(f"\n  v7e final geo={g_final['geo']:.3f}  ({moves} moves, {time.time()-t0:.0f}s)")
print(f"  Δ vs v7d-add: {g_final['geo']-g0['geo']:+.3f}")

# ───────────── Final breakdown ─────────────
print("\n" + "─" * 76)
print("  v7e axis breakdown vs v7d-add")
print("─" * 76)
axes = ["longevity", "sillage", "luxury", "texture", "stacking_depth",
        "photorealism", "perceptual_clarity", "skin_performance",
        "synergy", "hedonic"]
print(f"  {'axis':<22s} {'v7d-add':>8s} {'v7e':>8s} {'Δ':>8s}")
for a in axes:
    v0 = g0[a]; vf = g_final[a]
    print(f"  {a:<22s} {v0:8.2f} {vf:8.2f} {vf-v0:+8.2f}")

print(f"\n  Luxury sub-components (v7e):")
print(f"    natural_score   : {b_final['nat_score']:5.2f} / 20   (Δ {b_final['nat_score']-b0['nat_score']:+.2f}, nat_frac={b_final['nat_frac']*100:.2f}%)")
print(f"    premium_score   : {b_final['prem_score']:5.2f} / 20   (Δ {b_final['prem_score']-b0['prem_score']:+.2f}, prem_frac={b_final['prem_frac']*100:.2f}%)")
print(f"    architecture    : {b_final['arch_score']:5.2f} / 15   (Δ {b_final['arch_score']-b0['arch_score']:+.2f})")
print(f"    trace_shadow    : {b_final['trace_score']:5.2f} / 15   (Δ {b_final['trace_score']-b0['trace_score']:+.2f}, shadow={b_final['shadow']})")

# ───────────── Δ ingredients ─────────────
print("\n  Δ ingredients (v7e vs v7d-add):")
all_keys = set(ING0) | set(ing_g)
for k in sorted(all_keys, key=lambda x: -abs(ing_g.get(x, 0) - ING0.get(x, 0))):
    a, b = ING0.get(k, 0), ing_g.get(k, 0)
    if abs(a - b) > 0.5:
        print(f"    {k:<35s} {a:>7.1f} → {b:>7.1f}  ({b-a:+.1f})")

# Save snapshot
snap = {
    "v7e": {"geo": g_final["geo"], "ing": ing_g, "dil": dil_g,
            "axis": {a: g_final[a] for a in axes},
            "luxury_breakdown": {k: (v if not isinstance(v, dict) else dict(v))
                                 for k, v in b_final.items()}},
    "v7d_add_baseline": V7D,
}
with open("_opt_v7e_luxury.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, indent=2, default=str)
print("\n  snapshot → _opt_v7e_luxury.json")
print("  ─── DONE ───")
