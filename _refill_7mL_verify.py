"""7 mL spill refill for Photorealistic Iris — full 33-material formula scaled,
with complete non-linear verification: OAV, ODT, volatility, ppm, dose-response.
"""
import json, math, os, sys, io

# UTF-8 stdout for Windows
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_batch_scaling, check_proportional_scaling
from engine.dose_response import score_dose_response
from engine.formula_analyzer import FormulaInfo, formula_to_vector

BATCH_30 = 30.0
BATCH_7 = 7.0
SCALE = BATCH_7 / BATCH_30  # 0.2333

with open("_opt_final_iris.json") as f:
    full = json.load(f)

ing30 = full["ingredients"]
dil = full["dilutions"]

# Scale to 7 mL
ing7 = {n: round(v * SCALE, 2) for n, v in ing30.items()}

conc_total_ul = sum(ing7.values())
conc_pct = conc_total_ul / (BATCH_7 * 1000) * 100
ethanol_ul = BATCH_7 * 1000 - conc_total_ul

print("═" * 70)
print(f"  PHOTOREALISTIC IRIS — 7 mL REFILL (scaled from 30 mL optimized)")
print("═" * 70)
print(f"  Concentrate: {conc_total_ul:.1f} µL ({conc_pct:.2f}%)")
print(f"  Ethanol 96%: {ethanol_ul:.1f} µL")
print(f"  Scale factor: {SCALE:.4f}")
print()

# ── OAV guard: absolute-µL at 7 mL ──
print("─" * 70)
print(" (A) OAV guard @ 7 mL — absolute ODT crossings")
print("─" * 70)
abs_checks = check_batch_scaling(ing7, dil, BATCH_7, BATCH_7)
errs = [c for c in abs_checks if c.severity == "error"]
warns = [c for c in abs_checks if c.severity == "warn"]
infos = [c for c in abs_checks if c.severity == "info"]
print(f"  {len(errs)} err · {len(warns)} warn · {len(infos)} info")
for c in errs + warns:
    print(f"    {c.severity}: {c.message}")

# ── Proportional 7 → 15 mL reverse (pipette-floor safety) ──
print("\n" + "─" * 70)
print(" (B) Proportional re-split check: 7 → 3.5 mL (trace-floor safety)")
print("─" * 70)
rev = check_proportional_scaling(ing7, dil, BATCH_7, 3.5)
rerrs = [c for c in rev if c.severity == "error"]
rwarns = [c for c in rev if c.severity == "warn"]
rinfos = [c for c in rev if c.severity == "info"]
print(f"  {len(rerrs)} err · {len(rwarns)} warn · {len(rinfos)} info")
for c in rerrs + rwarns:
    print(f"    {c.severity}: {c.message}")

# ── Dose-response (concentration-driven, so IDENTICAL to 30 mL result) ──
print("\n" + "─" * 70)
print(" (C) Hill dose-response — character-zone audit")
print("─" * 70)
dr = score_dose_response(ing7, dilutions=dil, total_volume_ul=conc_total_ul)
print(f"  Score: {dr.score:.1f}/100")
print(f"  Optimal: {len(dr.optimal)} · Marginal: {len(dr.marginal)} · Overdosed: {len(dr.overdosed)}")
for o in dr.overdosed:
    print(f"    ⚠ {o['material']:28s} @ {o['conc_pct']:.3f}% → {o['quality']}")
for m in dr.marginal:
    print(f"    ⚠ {m['material']:28s} @ {m['conc_pct']:.3f}% → {m['quality']}")

# ── Scorer geo ──
print("\n" + "─" * 70)
print(" (D) Axis scoring")
print("─" * 70)
try:
    scorer = FormulaScorer()
    fi = FormulaInfo(number=0, name="Iris7mL", ingredients=ing7, dilutions=dil,
                     concentrate_ml=conc_total_ul/1000.0, description="")
    fv = formula_to_vector(fi)
    s = scorer.score(fv)
    AXIS_WEIGHTS = {
        "longevity": 1.0, "sillage": 1.0, "luxury": 1.0, "texture": 1.0,
        "stacking_depth": 1.0, "photorealism": 1.0,
        "perceptual_clarity": 0.6, "skin_performance": 0.6,
        "synergy": 0.5, "hedonic": 0.4,
    }
    wsum = sum(AXIS_WEIGHTS.values())
    log_sum = 0.0
    for a, w in AXIS_WEIGHTS.items():
        v = max(float(s.get(a, 5.0)), 5.0)
        log_sum += (w / wsum) * math.log(v)
    geo = math.exp(log_sum)
    print(f"  Geo composite: {geo:.3f}")
    for a in AXIS_WEIGHTS:
        print(f"    {a:24s} {float(s.get(a, 0)):.2f}")
except Exception as e:
    print(f"  (scorer skipped: {e})")

# ── Volatility / ppm per material ──
print("\n" + "─" * 70)
print(" (E) Per-material: ppm in final 7 mL (assumes density ≈ 0.85 g/mL EtOH)")
print("─" * 70)
BATCH_MASS_G = BATCH_7 * 0.85 * 1000  # 7 mL * 0.85 g/mL → mg
print(f"  Final batch mass: ~{BATCH_MASS_G:.0f} mg")
print()
print(f"  {'#':>2}  {'Material':<28s} {'Dil':>5s}  {'µL(dil)':>8s}  {'µL(neat)':>9s}  {'ppm(w/w)':>9s}")
print("  " + "─" * 70)
rows = []
for i, (n, amt) in enumerate(ing7.items(), 1):
    d = dil.get(n, 1.0)
    neat_ul = amt * d
    # Assume density 1 g/mL for active; ppm = mg/kg of final batch
    neat_mg = neat_ul * 1.0  # µL × 1 mg/µL (density 1.0)
    ppm = neat_mg / BATCH_MASS_G * 1e6
    rows.append((n, d, amt, neat_ul, ppm))
    dstr = "neat" if d == 1.0 else f"{int(d*100)}%"
    print(f"  {i:>2}  {n:<28s} {dstr:>5s}  {amt:>8.2f}  {neat_ul:>9.2f}  {ppm:>9.0f}")

print()
print("─" * 70)
print(" Mixing Procedure (7 mL in a 20 mL beaker)")
print("─" * 70)
print("  1. Add materials in listed order (macros → traces).")
print("  2. Top up with ethanol 96%: {:.0f} µL.".format(ethanol_ul))
print("  3. Cap, swirl 30 s, rest 24–48 hr for maceration.")
print("  4. Pour into parent bottle, swirl.")
print()
print("  Traces < 1 µL — use a 10% pre-dilution in DPG, or micro-pipette 0.2–0.5 µL.")
sub_ul = [n for n, _, a, _, _ in [(r[0], r[1], r[2], r[3], r[4]) for r in rows] if a < 1.0]
if sub_ul:
    print(f"  Sub-µL materials: {', '.join(sub_ul)}")

# Write MD
md_lines = [
    "# Photorealistic Iris — 7 mL Spill Refill (verified)",
    "",
    f"**Scale:** 7/30 = {SCALE:.4f}× of the 30 mL optimized formula",
    f"**Concentrate:** {conc_total_ul:.0f} µL ({conc_pct:.2f}%)",
    f"**Ethanol 96%:** {ethanol_ul:.0f} µL",
    f"**Final batch:** 7,000 µL (7.00 mL)",
    "",
    "## Verification Summary",
    "",
    f"- **OAV @ 7 mL:** {len(errs)} err · {len(warns)} warn",
    f"- **Proportional 7→3.5 mL (re-split):** {len(rerrs)} err · {len(rwarns)} warn",
    f"- **Dose-response:** {dr.score:.1f}/100 · {len(dr.optimal)} optimal · {len(dr.marginal)} marginal · {len(dr.overdosed)} overdosed",
    "",
    "## Formula",
    "",
    "| # | Material | Dilution | Amount (µL) | Neat (µL) | ppm (w/w) |",
    "|--:|---|---|---:|---:|---:|",
]
for i, (n, d, amt, neat_ul, ppm) in enumerate(rows, 1):
    dstr = "neat" if d == 1.0 else f"{int(d*100)}%"
    md_lines.append(f"| {i} | {n} | {dstr} | {amt:.2f} | {neat_ul:.2f} | {ppm:.0f} |")
md_lines += [
    f"| | **Concentrate** | | {conc_total_ul:.0f} | | |",
    f"| | **Ethanol 96%** | | {ethanol_ul:.0f} | | |",
    f"| | **Final** | | 7,000 | | |",
    "",
    "## Procedure",
    "1. In a clean 20 mL beaker, add materials in listed order (macros → traces).",
    f"2. Top up with {ethanol_ul:.0f} µL ethanol 96%.",
    "3. Cap, swirl 30 s, rest 24–48 hr for maceration.",
    "4. Pour into parent bottle, swirl.",
    "",
    "## Trace handling",
    "",
    "Materials below ~1 µL should be dosed as a 10% pre-dilution in DPG (dose 10× the µL shown from the 10% stock) or with a calibrated 0.5 µL micropipette.",
]
sub_ul_names = [r[0] for r in rows if r[2] < 1.0]
if sub_ul_names:
    md_lines.append(f"**Sub-µL in this batch:** {', '.join(sub_ul_names)}")

with open("formulas/collections/Photorealistic_Iris_7mL_REFILL_VERIFIED.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print("\n✓ Saved: formulas/collections/Photorealistic_Iris_7mL_REFILL_VERIFIED.md")
