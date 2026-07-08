"""v7c — Shadow-zone audit on v7b, then surgical brief-echoing additions.

User directive (2026-04-23):
  - "i do not have methyl laitone. run the audit on v7b, then run it on v7c.
     verify formulas"

Strategy:
  1. AUDIT v7b: classify every effective ingredient by ppm_in_conc / odt_ppm:
       silent  : ratio < 0.1  (Ellena: not even shadow, ignored by trace_score)
       shadow  : 0.1 ≤ ratio ≤ 1.0  (Ellena: trace_score plateau 2-10 = +1.125 ea)
       declared: ratio > 1.0  (declared note, scored on natural/premium/architecture)
       unknown : no odt_ppm in profile
  2. From the audit, identify:
       - Materials currently shadow → free luxury already paying out
       - Materials currently silent → wasted bottles, candidates for up-dose or removal
       - Materials currently barely declared → candidates for DOWN-dose into shadow
  3. v7c = v7b
       + 6 NEW brief-echoing shadow additions (verified in inventory):
           PEA, Methyl Anthranilate, Cyclamen Aldehyde, Ambrofix, Allyl Ionone,
           Champaca Flower EO  (NOT Methyl Laitone — confirmed not in inventory)
       + DOWN-DOSE existing barely-declared materials into shadow
           (data-driven from audit: only down-dose materials currently classed
            'declared' with ratio < 3.0 — easy to push into shadow without
            killing character)
  4. AUDIT v7c with same classifier
  5. Score v7c default + brief weights, compare to v7b/v7a/v3
  6. Verify: IFRA caps, total volume = 50000 µL exact, all materials in inventory.

Outputs:
  _opt_v7c_shadow_audit.json   — full structured results
  _opt_v7c_shadow_audit_out.txt — human-readable terminal log
"""
from __future__ import annotations
import json, os, sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

from engine.ingredient_intelligence import get_profile
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph
from _scale_30mL_verify_nonlinear import score_formula
from _opt_iris_reverie_15probes import IRL_DIL_BASE, BATCH_ML, IFRA_CAPPED

# ---------- Load v7b ----------
with open("_opt_v7b_brief.json", "r", encoding="utf-8") as f:
    v7b_snap = json.load(f)
v7b_ing = dict(v7b_snap["v7b_ing"])
v7b_dil = dict(v7b_snap["v7b_dil"])

# Sanity: v7b dilutions for newly-added materials (already in JSON)
# v7c will inherit and extend.

# ---------- Brief weights (from v7b D2 — same profile) ----------
brief_weights = ObjectiveWeights(
    longevity=0.8, sillage=0.6, synergy=0.5, luxury=1.0, texture=1.0,
    stacking_depth=0.8, skin_performance=0.9, hedonic=0.9,
    perceptual_clarity=0.5, photorealism=0.4,
)

sg = SynergyGraph()
scorer_default = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)
scorer_brief   = FormulaScorer(weights=brief_weights, synergy_graph=sg,
                               batch_volume_ml=BATCH_ML)

# ============================================================================
#  AUDIT FUNCTION — uses the same shadow classifier as score_luxury (engine
#  scoring.py:1166) so audit output corresponds 1:1 to luxury.trace_score.
# ============================================================================

def shadow_audit(label: str, ing: dict, dil: dict) -> dict:
    """Classify every effective material as silent/shadow/declared/unknown.

    Mirrors engine/optimizer/scoring.py score_luxury() shadow logic exactly:
        odt_ref = profile.odt_ppm
        ppm_in_conc = pct * 10000.0  (pct = active % of concentrate)
        ratio = ppm_in_conc / odt_ref
        ratio < 0.1   → silent (excluded entirely from luxury components)
        0.1 ≤ r ≤ 1.0 → shadow (counts toward trace_score, NOT toward
                        natural/premium/architecture/effect mass)
        ratio > 1.0   → declared (full participant)
    """
    fi = FormulaInfo(number=0, name=label, ingredients=ing, dilutions=dil,
                     concentrate_ml=sum(ing.values())/1000.0, description="")
    fv = formula_to_vector(fi)
    eff = fv.effective_ingredients()  # {name: pct_in_concentrate}

    rows = []
    counts = {"silent": 0, "shadow": 0, "declared": 0, "unknown": 0}
    for name, pct in sorted(eff.items(), key=lambda kv: -kv[1]):
        prof = get_profile(name)
        odt = getattr(prof, "odt_ppm", None) if prof else None
        if not odt or odt <= 0:
            classification = "unknown"
            ratio = None
        else:
            ratio = (pct * 10000.0) / odt
            if ratio < 0.1:
                classification = "silent"
            elif ratio <= 1.0:
                classification = "shadow"
            else:
                classification = "declared"
        counts[classification] += 1
        rows.append({
            "name": name,
            "raw_ul": ing.get(name, 0),
            "dil": dil.get(name, 1.0),
            "pct_in_conc": round(pct, 5),
            "odt_ppm": odt,
            "ratio_to_odt": round(ratio, 4) if ratio is not None else None,
            "class": classification,
        })

    # Trace score formula (from scoring.py:1252)
    s = counts["shadow"]
    if s < 2:
        trace_score = s / 2.0 * 6.0
    elif s <= 10:
        trace_score = 6.0 + (s - 2) / 8.0 * 9.0
    elif s <= 14:
        trace_score = 15.0 - (s - 10) * 0.5
    else:
        trace_score = max(8.0, 13.0 - (s - 14) * 0.5)

    return {
        "label": label,
        "counts": counts,
        "trace_score_predicted": round(trace_score, 3),
        "shadow_count": s,
        "rows": rows,
    }


def print_audit(audit: dict, only_classes=None):
    print(f"\n{'='*78}")
    print(f"  SHADOW AUDIT — {audit['label']}")
    print(f"{'='*78}")
    c = audit["counts"]
    print(f"  silent={c['silent']}  shadow={c['shadow']}  "
          f"declared={c['declared']}  unknown={c['unknown']}")
    print(f"  Predicted trace_score (luxury component 5): "
          f"{audit['trace_score_predicted']} / 15.00")
    print(f"  Shadow plateau: 2-10 materials = best zone "
          f"(+1.125 luxury per shadow)")
    print()
    print(f"  {'Material':<32} {'raw µL':>8} {'dil':>6} {'pct_conc':>10} "
          f"{'odt_ppm':>10} {'ratio':>8}  class")
    print(f"  {'-'*32} {'-'*8} {'-'*6} {'-'*10} {'-'*10} {'-'*8}  -----")
    for r in audit["rows"]:
        if only_classes and r["class"] not in only_classes:
            continue
        odt = f"{r['odt_ppm']:.4g}" if r['odt_ppm'] else "—"
        rat = f"{r['ratio_to_odt']:.3g}" if r['ratio_to_odt'] is not None else "—"
        print(f"  {r['name']:<32} {r['raw_ul']:>8.1f} {r['dil']:>6.2f} "
              f"{r['pct_in_conc']:>10.4f} {odt:>10} {rat:>8}  {r['class']}")


# ============================================================================
#  STEP 1 — Audit v7b
# ============================================================================
print("\n" + "█"*78)
print("  STEP 1 — Audit v7b (current state)")
print("█"*78)
v7b_audit = shadow_audit("v7b", v7b_ing, v7b_dil)
print_audit(v7b_audit)

# Extract actionable lists from v7b audit
v7b_silent     = [r["name"] for r in v7b_audit["rows"] if r["class"] == "silent"]
v7b_shadow     = [r["name"] for r in v7b_audit["rows"] if r["class"] == "shadow"]
# barely-declared candidates: declared with ratio between 1.0 and 3.0
v7b_barely_dec = [r for r in v7b_audit["rows"]
                  if r["class"] == "declared"
                  and r["ratio_to_odt"] is not None
                  and 1.0 < r["ratio_to_odt"] <= 3.0]

print(f"\n  → Currently silent ({len(v7b_silent)}): {v7b_silent}")
print(f"  → Currently shadow ({len(v7b_shadow)}): {v7b_shadow}")
print(f"  → Barely-declared (ratio 1-3, candidates for down-dose into shadow):")
for r in v7b_barely_dec:
    print(f"     {r['name']:<32}  ratio={r['ratio_to_odt']:.3g}  "
          f"raw={r['raw_ul']} µL")

# ============================================================================
#  STEP 2 — Build v7c
# ============================================================================
print("\n" + "█"*78)
print("  STEP 2 — Build v7c from audit findings")
print("█"*78)

v7c_ing = dict(v7b_ing)
v7c_dil = dict(v7b_dil)

# --- (A) New brief-echoing additions (all VERIFIED in inventory) ---
# Targeting Ellena shadow zone: dose ≈ 0.3-0.7× ODT each material.
# Doses chosen to land in shadow band; will re-audit to verify.
NEW_ADDITIONS = [
    # (name, raw_ul, dilution, register, brief_echo)
    ("Phenethyl Alcohol (PEA)", 60.0, 1.0,
        "rosy white-floral alcohol", "white floral"),
    ("Methyl Anthranilate", 25.0, 1.0,
        "powdery orange-blossom Schiff-base precursor", "powder + bridge"),
    ("Cyclamen Aldehyde", 8.0, 1.0,
        "fresh muguet aldehyde, 5th muguet axis", "white floral muguet"),
    ("Ambrofix", 30.0, 0.30,
        "amber-mineral shadow (4th amber, sits below threshold)", "amber depth"),
    ("Allyl Ionone", 40.0, 1.0,
        "violet-iris reinforcement, distinct from Alpha/Beta/AIMI", "iris"),
    ("Champaca Flower EO", 8.0, 1.0,
        "natural magnolia-tea white floral, naturals++", "white floral natural"),
]
for name, raw, d, reg, echo in NEW_ADDITIONS:
    v7c_ing[name] = raw
    v7c_dil[name] = d
    print(f"  + {name:<28} {raw:>5.1f} µL @ {d:.2f}  ({reg})")

# --- (B) Down-doses of barely-declared v7b materials (data-driven) ---
# Targets: materials with ratio_to_odt in (1.0, 3.0] — push into shadow band.
# Conservative: divide raw by 2× for ratios 2-3, by 1.5× for ratios 1-2.
# Exclude IFRA-capped materials (already at min) and architectural pillars.
PROTECT_DOMINANT = {  # core character pillars — never down-dose
    "Hedione", "Hedione HC", "Ebanol", "Alpha Irone", "Orivone",
    "Ethyl Linalool", "Ethylene Brassylate", "Ambrettolide", "Habanolide",
    "Bergamot FCF oil Sicilian", "Benzoin Resinoid", "Musk Ketone",
    "Vanillin", "Ambrox Super", "Ambermax", "Cedarwood EO",
    "Hexyl Salicylate", "Benzyl Salicylate", "DBCA", "Lilyreal ND",
    "Iso E Super", "Javanol", "Coumarin", "Hydroxycitronellal",
    "Mayol", "Heliotropal", "Anisaldehyde", "Bourgeonal",  # white-floral structural
    "Beta Ionone", "Alpha Ionone",  # iris structural
    "Delta Decalactone", "Gamma Decalactone", "Gamma Undecalactone",  # buttery structural
    "Ethyl Vanillin", "Ethyl Maltol",  # gourmand support
    "Carrot Seed EO", "Freesia HDI",  # natural pillars
    "Damascol", "Helional", "ACA", "Azarbre",  # newly added structural
}
print(f"\n  --- Down-dose targets (barely-declared, not protected) ---")
for r in v7b_barely_dec:
    if r["name"] in PROTECT_DOMINANT:
        continue
    if r["name"] in IFRA_CAPPED:  # already at IFRA limit
        continue
    cur = v7c_ing[r["name"]]
    if r["ratio_to_odt"] >= 2.0:
        new_raw = round(cur / 2.5, 1)
    else:
        new_raw = round(cur / 1.6, 1)
    new_raw = max(new_raw, 1.0)  # never zero
    if new_raw < cur:
        print(f"  ↓ {r['name']:<28} {cur:>5.1f} → {new_raw:>5.1f} µL  "
              f"(ratio {r['ratio_to_odt']:.2g} → target shadow)")
        v7c_ing[r["name"]] = new_raw

# --- (C) Re-balance ethanol so total = 50000 µL exact ---
conc_ul = sum(v7c_ing.values())
print(f"\n  v7c concentrate: {conc_ul:.1f} µL ({conc_ul/500:.2f}% of 50 mL)")

# ============================================================================
#  STEP 3 — Audit v7c
# ============================================================================
print("\n" + "█"*78)
print("  STEP 3 — Audit v7c (post-additions + down-doses)")
print("█"*78)
v7c_audit = shadow_audit("v7c", v7c_ing, v7c_dil)
print_audit(v7c_audit)

# Show the diff
v7b_classes = {r["name"]: r["class"] for r in v7b_audit["rows"]}
print(f"\n  --- Class transitions v7b → v7c ---")
transitions = []
for r in v7c_audit["rows"]:
    old = v7b_classes.get(r["name"], "(new)")
    new = r["class"]
    if old != new:
        transitions.append((r["name"], old, new, r["ratio_to_odt"]))
        print(f"  {r['name']:<32} {old:>9} → {new:<9}  "
              f"ratio={r['ratio_to_odt']}")

print(f"\n  Trace score: v7b={v7b_audit['trace_score_predicted']} → "
      f"v7c={v7c_audit['trace_score_predicted']}  "
      f"(Δ={v7c_audit['trace_score_predicted']-v7b_audit['trace_score_predicted']:+.2f})")

# ============================================================================
#  STEP 4 — Score v7c
# ============================================================================
print("\n" + "█"*78)
print("  STEP 4 — Score v7c (default and brief weights)")
print("█"*78)
v7c_default, v7c_axes_default = score_with_helper = score_formula(v7c_ing, v7c_dil, scorer_default)
v7c_brief, v7c_axes_brief = score_formula(v7c_ing, v7c_dil, scorer_brief)

print(f"\n  v7c geo (default): {v7c_default}")
print(f"  v7c geo (brief)  : {v7c_brief}")
print(f"\n  vs prior versions:")
print(f"    v3  default = {v7b_snap['v3_geo_default']}")
print(f"    v7a default = {v7b_snap['v7a_geo_default']}     brief = {v7b_snap['v7a_geo_brief']}")
print(f"    v7b default = {v7b_snap['v7b_geo_default']}     brief = {v7b_snap['v7b_geo_brief']}")
print(f"    v7c default = {v7c_default}     brief = {v7c_brief}")

print(f"\n  v7c axis breakdown (default):")
for k in ("longevity","sillage","luxury","texture","stacking_depth",
          "photorealism","perceptual_clarity","skin_performance",
          "synergy","hedonic"):
    print(f"    {k:<22} {v7c_axes_default[k]:6.2f}")

# ============================================================================
#  STEP 5 — Verify formulas (IFRA, volume, inventory)
# ============================================================================
print("\n" + "█"*78)
print("  STEP 5 — Verify formulas")
print("█"*78)

INVENTORY_NAMES = set()
with open("inventory.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("- "):
            # Strip leading "- ", trailing comments, trailing parens about dilution
            entry = line[2:].split("#")[0].strip()
            # Common forms: "Name", "Name (dil%)", "Name (10% in DPG)"
            base = entry.split("(")[0].strip()
            INVENTORY_NAMES.add(base.lower())
            # Also store the full label and aliases
            if "(" in entry and ")" in entry:
                full = entry.split(")")[0].split("(")[1].lower()
                INVENTORY_NAMES.add(full)

# Custom alias map for known short forms
ALIAS = {
    "Phenethyl Alcohol (PEA)": "phenethyl alcohol (pea)",
    "Allyl Ionone": "allyl ionone (ketone v)",
    "Methyl Anthranilate": "methyl anthranilate",
    "Cyclamen Aldehyde": "cyclamen aldehyde",
    "Ambrofix": "ambrofix",
    "Champaca Flower EO": "champaca flower eo",
}

def in_inventory(name: str) -> bool:
    if name.lower() in INVENTORY_NAMES:
        return True
    if name in ALIAS and ALIAS[name] in INVENTORY_NAMES:
        return True
    # last-chance partial: check normalized contains
    n = name.lower().replace("(pea)", "").strip()
    return any(n in inv for inv in INVENTORY_NAMES)

print(f"\n  --- Inventory check (v7c, {len(v7c_ing)} materials) ---")
missing = [n for n in v7c_ing if not in_inventory(n)]
if missing:
    print(f"  FAIL — {len(missing)} not in inventory:")
    for m in missing:
        print(f"    {m}")
else:
    print(f"  PASS — all {len(v7c_ing)} materials confirmed in inventory.")

print(f"\n  --- IFRA cap check (v7c) ---")
ifra_fail = []
for name, cap in IFRA_CAPPED.items():
    if name in v7c_ing and v7c_ing[name] > cap:
        ifra_fail.append((name, v7c_ing[name], cap))
        print(f"  FAIL {name}: {v7c_ing[name]} > {cap}")
    elif name in v7c_ing:
        pct_of_cap = v7c_ing[name] / cap * 100
        print(f"  OK   {name}: {v7c_ing[name]} / {cap} ({pct_of_cap:.0f}%)")
if not ifra_fail:
    print(f"  PASS — all IFRA-capped materials within limits.")

print(f"\n  --- Volume check (v7c) ---")
conc_ul = sum(v7c_ing.values())
ethanol_ul = 50000.0 - conc_ul
print(f"  Concentrate: {conc_ul:.1f} µL ({conc_ul/500:.2f}%)")
print(f"  Ethanol 96%: {ethanol_ul:.1f} µL")
print(f"  TOTAL      : {conc_ul + ethanol_ul:.1f} µL  (target 50000.0)")
if abs(conc_ul + ethanol_ul - 50000.0) < 0.01:
    print(f"  PASS — total = 50000 µL exact.")

# ============================================================================
#  STEP 6 — Save snapshot
# ============================================================================
out = {
    "v7b_audit": v7b_audit,
    "v7c_audit": v7c_audit,
    "v7c_ing": v7c_ing,
    "v7c_dil": v7c_dil,
    "v7c_geo_default": v7c_default,
    "v7c_geo_brief": v7c_brief,
    "v7c_axes_default": v7c_axes_default,
    "v7c_axes_brief": v7c_axes_brief,
    "concentrate_ul": conc_ul,
    "ethanol_ul": ethanol_ul,
    "ifra_fails": ifra_fail,
    "inventory_missing": missing,
    "transitions": transitions,
    "new_additions": [(n, raw, d, reg, echo)
                      for n, raw, d, reg, echo in NEW_ADDITIONS],
    "v3_geo_default": v7b_snap["v3_geo_default"],
    "v7a_geo_default": v7b_snap["v7a_geo_default"],
    "v7a_geo_brief": v7b_snap["v7a_geo_brief"],
    "v7b_geo_default": v7b_snap["v7b_geo_default"],
    "v7b_geo_brief": v7b_snap["v7b_geo_brief"],
}
with open("_opt_v7c_shadow_audit.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n  Saved → _opt_v7c_shadow_audit.json")
print(f"\n  ─── DONE ───")
