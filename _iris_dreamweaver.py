"""Iris Dreamweaver — verify + save. Single-direction iris-cream-coumarin-vanillic luxury."""
import json, math, os, sys, io
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_batch_scaling
from engine.dose_response import score_dose_response
from engine.formula_analyzer import FormulaInfo, formula_to_vector

BATCH_ML = 10.0

# ingredients: (name, dilution_factor, amount_uL_of_dilution)
# dilution_factor is the "active fraction": neat=1.0, 30%=0.30, 10%=0.10, 20%=0.20, 50%=0.50, 1%=0.01
ing = {
    # TOP
    "Bergamot FCF oil Sicilian": 40.0,
    "Red Mandarin EO": 20.0,
    # IRIS CORE
    "Alpha Irone": 340.0,
    "Orris F-TEC": 70.0,
    "Orivone": 40.0,
    "Dihydro Beta Ionone": 20.0,
    "Alpha Ionone": 15.0,
    "Carrot Seed EO": 15.0,
    "Ultralia": 25.0,
    "Irotyl": 5.0,
    # WHITE FLORAL
    "Hedione": 280.0,
    "Hedione HC": 100.0,
    "Mayol": 25.0,
    "Hydroxycitronellal": 20.0,
    "Amyl Cinnamic Aldehyde (ACA)": 20.0,
    "DBCA": 15.0,
    "Bourgeonal": 10.0,
    "Farnesol": 5.0,
    "Cis Jasmone": 5.0,
    # GOURMAND BRIDGE & BASE
    "Myristic Acid": 150.0,
    "Benzoin Resinoid": 140.0,
    "Heliotropal": 40.0,
    "Tonka Bean FO": 50.0,
    "Ethyl Vanillin": 20.0,
    "Vanillin": 70.0,
    "Ethyl Maltol": 50.0,
    "Delta Decalactone": 35.0,
    "Maple Lactone": 35.0,
    "Heliotropin Fleuressence": 30.0,
    "Gamma Undecalactone": 30.0,
    "Coumarin": 120.0,
    "Anisaldehyde": 15.0,
    # FIXATIVE / DIFFUSION / WOODS
    "Ethylene Brassylate": 200.0,
    "Iso E Super": 150.0,
    "Benzyl Salicylate": 150.0,
    "Musk Ketone": 100.0,
    "Exaltolide": 80.0,
    "Ambermax": 110.0,
    "Ebanol": 40.0,
    "Ambrettolide": 60.0,
    "Hexyl Salicylate": 50.0,
    "Azarbre": 50.0,
    "Koavone": 40.0,
    "Cedarwood oil Virginia": 30.0,
}

dil = {
    "Alpha Irone": 0.30,
    "Myristic Acid": 0.20,
    "Benzoin Resinoid": 0.50,
    "Vanillin": 0.10,
    "Ethyl Maltol": 0.10,
    "Maple Lactone": 0.20,
    "Coumarin": 0.20,
    "Musk Ketone": 0.10,
    "Exaltolide": 0.10,
    "Ambermax": 0.50,
    "Ambrettolide": 0.10,
}

conc_total = sum(ing.values())
pct = conc_total / (BATCH_ML * 1000) * 100
ethanol = BATCH_ML * 1000 - conc_total

print(f"Iris Dreamweaver — 10 mL @ {pct:.2f}% concentrate")
print(f"Concentrate: {conc_total:.0f} µL · Ethanol 96%: {ethanol:.0f} µL · {len(ing)} materials\n")

# (A) OAV guard
print("─" * 70)
print(" (A) OAV guard @ 10 mL")
print("─" * 70)
checks = check_batch_scaling(ing, dil, BATCH_ML, BATCH_ML)
errs = [c for c in checks if c.severity == "error"]
warns = [c for c in checks if c.severity == "warn"]
print(f"  {len(errs)} err · {len(warns)} warn")
for c in errs + warns:
    print(f"    {c.severity}: {c.message}")

# (B) Dose-response
print("\n" + "─" * 70)
print(" (B) Hill dose-response")
print("─" * 70)
dr = score_dose_response(ing, dilutions=dil, total_volume_ul=conc_total)
print(f"  Score: {dr.score:.1f}/100 · {len(dr.optimal)} optimal · {len(dr.marginal)} marginal · {len(dr.overdosed)} overdosed")
for o in dr.overdosed:
    print(f"    ⚠ OD: {o['material']:30s} @ {o['conc_pct']:.3f}% → {o['quality']}")
for m in dr.marginal:
    print(f"    · mg: {m['material']:30s} @ {m['conc_pct']:.3f}% → {m['quality']}")

# (C) Axis scoring
print("\n" + "─" * 70)
print(" (C) Axis scoring")
print("─" * 70)
scorer = FormulaScorer()
fi = FormulaInfo(number=0, name="IrisDreamweaver", ingredients=ing, dilutions=dil,
                 concentrate_ml=conc_total/1000.0, description="")
fv = formula_to_vector(fi)
s = scorer.score(fv)
AXIS_W = {"longevity":1.0,"sillage":1.0,"luxury":1.0,"texture":1.0,"stacking_depth":1.0,
          "photorealism":1.0,"perceptual_clarity":0.6,"skin_performance":0.6,"synergy":0.5,"hedonic":0.4}
wsum = sum(AXIS_W.values())
log_sum = sum((w/wsum)*math.log(max(float(s.get(a,5.0)),5.0)) for a,w in AXIS_W.items())
geo = math.exp(log_sum)
print(f"  Geo composite: {geo:.3f}")
for a in AXIS_W:
    print(f"    {a:24s} {float(s.get(a,0)):.2f}")

# Save MD
md = []
md += ["# Iris Dreamweaver — 10 mL (verified)", ""]
md += [f"**Concept:** Soft iris powder + low-AIMI white florals → heliotropin-coumarin-vanillin-lactone creamy luxury base. Single-direction synergy, deep, projective, long-lasting, textured (intentionally not transparent).", ""]
md += [f"**Batch:** 10.00 mL · **Concentrate:** {conc_total:.0f} µL ({pct:.2f}%) · **Ethanol 96%:** {ethanol:.0f} µL", ""]
md += ["## Verification", "",
       f"- **OAV @ 10 mL:** {len(errs)} err · {len(warns)} warn",
       f"- **Dose-response:** {dr.score:.1f}/100 · {len(dr.optimal)} optimal · {len(dr.marginal)} marginal · {len(dr.overdosed)} overdosed",
       f"- **Geo composite:** {geo:.3f}",
       f"- **Longevity/Sillage/Photorealism/Luxury:** "
       f"{float(s.get('longevity',0)):.1f} / {float(s.get('sillage',0)):.1f} / "
       f"{float(s.get('photorealism',0)):.1f} / {float(s.get('luxury',0)):.1f}",
       ""]
if errs: md += ["**Errors:**", ""] + [f"- {c.message}" for c in errs] + [""]
if warns: md += ["**Warnings:**", ""] + [f"- {c.message}" for c in warns] + [""]
if dr.overdosed: md += ["**Overdosed:**", ""] + [f"- {o['material']} @ {o['conc_pct']:.3f}%" for o in dr.overdosed] + [""]

# Formula table (grouped)
md += ["## Formula", "",
       "| # | Material | Dilution | µL (dilution) | µL (neat) |",
       "|--:|---|---|--:|--:|"]
order = list(ing.keys())
for i, n in enumerate(order, 1):
    d = dil.get(n, 1.0)
    dstr = "neat" if d == 1.0 else f"{int(d*100)}%"
    md.append(f"| {i} | {n} | {dstr} | {ing[n]:.1f} | {ing[n]*d:.2f} |")
md += [f"| | **Concentrate** | | **{conc_total:.0f}** | |",
       f"| | **Ethanol 96%** | | **{ethanol:.0f}** | |",
       f"| | **Final** | | **10,000** | |",
       ""]

md += ["## Procedure", "",
       "1. In a clean 20 mL beaker, dose in order: macros (Hedione → Alpha Irone 30% → EB → BzSal → Iso E → Benzoin 50% → Myristic 20% → Coumarin 20% → MuskK 10%) first; then mids; then traces (Farnesol, Irotyl, Cis Jasmone last).",
       f"2. Top up with **{ethanol:.0f} µL ethanol 96%**.",
       "3. Cap tightly, swirl 60 s.",
       "4. **Macerate 14 days minimum**, shake daily for the first 3 days. Iris waxes, benzoin resin, and heliotropin need extended maturation.",
       "5. Optional: filter through 0.45 µm PTFE before decant.",
       "",
       "## Why this works",
       "",
       "- **Iris↔Cream triple bridge:** Heliotropal + Myristic Acid + Ethylene Brassylate all carry character on both sides of the iris/cream boundary — the transition is seamless, not stacked.",
       "- **Powder double-echo:** Musk Ketone (powdery nitromusk) + Alpha Irone (buttery-powdery orris) — powder reappears in drydown, not just opening.",
       "- **Vanillic spectrum layered:** Ethyl Vanillin (sharp-deep) + Vanillin (round) + Coumarin (hay-coumarinic) + Tonka Bean FO (body) + Benzoin (resin cushion) + Ethyl Maltol (sugar) — each plays a different vanillic facet.",
       "- **Low-AIMI white floral:** Hedione + Hedione HC for volume; Mayol + Bourgeonal + HDC + ACA + Farnesol for clean-white muguet character. Zero Alpha Isomethyl Ionone, zero Beta Ionone. Alpha Ionone kept at 15 µL (whisper only).",
       "- **Amber choice — warm not crystalline:** Ambermax 50% (rounded-cozy) selected over Ambrox Super (mineral-cold) per the deep-luxury brief. Azarbre reinforces warm cedar-amber.",
       "- **Musk chord:** Ethylene Brassylate (creamy-depth, central) + Musk Ketone (powdery character-echo) + Exaltolide (skin-lactonic) + Ambrettolide (natural-warm). Habanolide and Romandolide rejected — the dense creamy direction doesn't need generic skin-warm or projective-clean musks.",
       ]

out_path = "formulas/collections/Iris_Dreamweaver_10mL.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print(f"\n✓ Saved: {out_path}")
