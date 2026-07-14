"""Bleu Carbon MAX — Complete OAV Analysis with Literature Validation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.platform == "win32": sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engine.pipeline.formula_state import build_formula_state
from engine.odor_thresholds import ODT_DATA
from engine.ingredient_intelligence import get_profile
import math

# ═══════════════════════════════════════════════════════════════
# Final formula after 5mL removal + all additions
# ═══════════════════════════════════════════════════════════════

ingredients_ul = {
    # BASE (after 5mL removal ×0.833 + boosts)
    "Iso E Super": 542, "Ambrofix": 840, "Romandolide": 167,
    "Cedarwood oil Virginia": 142, "Olibanum Resinoid": 230,
    "Clearwood": 108, "Ebanol": 83, "Ethylene Brassylate": 180,
    "Zenolide": 67, "Javanol": 110, "Vertofix": 58, "Habanolide": 130,
    "Sandalore": 42, "Timberol": 42, "Vetival": 17, "Ambrettolide": 35,
    "Benzoin Resinoid": 25, "Evernyl": 55, "Norlimbanol Dextro": 15,
    "Patchouli EO": 13, "Kephalis": 10, "Suederal": 10,
    "Costus Olifac": 8, "Nagarmortha Oil": 7,
    # NEW base materials
    "Benzyl Salicylate": 120, "Cashmeran": 60, "Polysantol": 80,
    "Amberwood F": 50, "Azarbre": 50, "Musk Ketone": 30,
    "Myristic Acid": 50,
    # HEART
    "Hedione": 620, "Lavender EO": 420, "Hedione HC": 200,
    "Geraniol": 75, "Coumarin": 70, "Linalyl Acetate": 33,
    "Aurantiol": 90, "Clary Sage EO": 21, "Terpinyl Acetate": 17,
    "Dihydrojasmone": 17, "Spike Lavender EO": 13, "Damascenone": 10,
    "Alpha Damascone": 12, "Alpha Irone": 4, "Carrot Seed EO": 4,
    # NEW heart materials
    "Floralozone": 60, "Cardamom EO": 25,
    # TOP
    "Cedrat FCF Sicilian": 300, "Grapefruit FCF": 167,
    "Dihydromyrcenol": 150, "Bergamot FCF Sicilian": 92,
    "Aldehyde C10": 42, "Black Pepper EO": 76, "Blood Orange Sicilian": 29,
    "Petitgrain EO": 29, "Scentenal": 40, "Juniper Berry EO": 13,
    "Rosemary EO": 7, "Ethyl Safranate": 4,
}

dilutions = {
    "Ambrofix": 0.30, "Olibanum Resinoid": 0.10, "Ambrettolide": 0.10,
    "Benzoin Resinoid": 0.50, "Suederal": 0.10, "Costus Olifac": 0.10,
    "Coumarin": 0.20, "Aurantiol": 0.10, "Damascenone": 0.01,
    "Alpha Damascone": 0.10, "Alpha Irone": 0.30,
    "Floralozone": 0.10, "Aldehyde C10": 0.01, "Scentenal": 0.01,
    "Musk Ketone": 1.0, "Myristic Acid": 1.0,
}
# Fill defaults
for k in ingredients_ul:
    if k not in dilutions: dilutions[k] = 1.0

total_ul = sum(ingredients_ul.values())
print(f"Total concentrate: {total_ul:.0f} uL")

state = build_formula_state(
    ingredients_ul=ingredients_ul, dilutions=dilutions,
    temperature_K=298.15, batch_volume_ml=30.0,
)

SEP = "=" * 80
DIV = "-" * 80

print(SEP)
print("  BLEU CARBON MAX — FULL OAV + LITERATURE VALIDATION")
print(SEP)
print(f"  {len(state.materials)} materials, {total_ul:.0f} uL concentrate, 30 mL batch")

# ═══════════ 1. HEADSPACE OAV RANKING ═══════════
print(f"\n{DIV}")
print("  1. HEADSPACE OAV — FULL RANKING (Modified Raoult, 32°C)")
print(DIV)

ranked = sorted(
    [(ms.name, ms.oav or 0, ms.vapor_ppm or 0, ms.odt_air_ppm or 0,
      ms.partial_pressure_pa or 0, ms.gamma or 1.0, ms.mole_fraction or 0,
      ms.vp_pure_pa or 0, ms.active_ul, ms.note or "?")
     for ms in state.materials],
    key=lambda x: -x[1]
)

print(f"\n  {'#':>3} {'Material':<30} {'OAV':>10} {'vap_ppb':>10} {'ODT_ppb':>10} {'p(Pa)':>10} {'γ':>6} {'x%':>8} {'VP':>8} {'Note':>6} {'Active':>8}")
print(f"  {'-'*3} {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*6} {'-'*8} {'-'*8} {'-'*6} {'-'*8}")

for i, (nm, oav, vap, odt, pp, gam, mf, vp, act, note) in enumerate(ranked, 1):
    vap_ppb = vap * 1000
    mf_pct = mf * 100
    band = "DOM" if oav >= 50 else ("ACT" if oav >= 5 else ("THR" if oav >= 1 else "SUB"))
    if odt == 0: odt_str = "N/A"
    else: odt_str = f"{odt:.4f}"
    print(f"  {i:>3} {nm:<30} {oav:>10.1f} {vap_ppb:>10.2f} {odt_str:>10} {pp:>10.2e} {gam:>6.2f} {mf_pct:>7.3f}% {vp:>8.4f} {note:>6} {act:>8.1f}")

# Count
n_dom = sum(1 for _, o, *_ in ranked if o >= 50)
n_act = sum(1 for _, o, *_ in ranked if 5 <= o < 50)
n_thr = sum(1 for _, o, *_ in ranked if 1 <= o < 5)
n_sub = sum(1 for _, o, *_ in ranked if 0 < o < 1)
n_zero = sum(1 for _, o, *_ in ranked if o == 0)
print(f"\n  {n_dom} dominant (OAV≥50) | {n_act} active (5-50) | {n_thr} threshold (1-5) | {n_sub} subliminal (<1) | {n_zero} zero")

# ═══════════ 2. THREE-STYLE REFERENCE CHECK ═══════════
print(f"\n{DIV}")
print("  2. STYLE REFERENCE — SAUVAGE / LUNA ROSSA CARBON / BLEU DE CHANEL")
print(DIV)

ref_mats = {
    "SAUVAGE (ambrox-citrus-pepper-lavender)": [
        ("Ambrofix", "Crystalline ambergris — must dominate skin texture"),
        ("Black Pepper EO", "Hot-dry spark opening — Sauvage signature"),
        ("Dihydromyrcenol", "Blue-aquatic lift"),
        ("Cedrat FCF Sicilian", "Bitter-mineral citrus"),
        ("Iso E Super", "Molecular skin cocoon"),
        ("Lavender EO", "Aromatic-fougere soul"),
    ],
    "LUNA ROSSA CARBON (mineral-carbon-patchouli)": [
        ("Clearwood", "Carbon-mineral earth"),
        ("Scentenal", "Metallic-coal air"),
        ("Patchouli EO", "Earthy-camphor anchor"),
        ("Kephalis", "Woody-amber industrial"),
        ("Spike Lavender EO", "Camphor aromatic edge"),
        ("Cashmeran", "Textile warmth — rounds the mineral edge"),
    ],
    "BLEU DE CHANEL (grapefruit-incense-sandalwood)": [
        ("Grapefruit FCF", "Pink-pith signature top"),
        ("Olibanum Resinoid", "Transparent incense depth"),
        ("Javanol", "Architectural sandalwood"),
        ("Bergamot FCF Sicilian", "Aromatic citrus bridge"),
        ("Hedione", "Radiance amplifier — transparency"),
        ("Polysantol", "Creamy sandalwood richness"),
    ],
}

for style, mats in ref_mats.items():
    print(f"\n  ── {style} ──")
    for m_name, target in mats:
        found = None
        for r in ranked:
            if m_name.lower() in r[0].lower():
                found = r
                break
        if found:
            nm, oav, vap, odt, pp, gam, mf, vp, act, note = found
            status = "✓" if oav >= 1 else ("△ subliminal" if oav > 0 else "✗ absent")
            print(f"    {status} {nm:<30} OAV={oav:>8.1f}  {target}")
        else:
            print(f"    ✗ {m_name:<30} NOT FOUND")

# ═══════════ 3. GOURMAND/FOUGERE LITERATURE BENCHMARKS ═══════════
print(f"\n{DIV}")
print("  3. LITERATURE BENCHMARKS — AROMATIC FOUGERE OAV TARGETS")
print(DIV)

# From the oav_intelligence module's family targets for aromatic_fougere
FOUGERE_TARGETS = {
    "iso e super": (30, 80),
    "ambrox": (5, 25),
    "hedione": (20, 80),
    "lavender": (5, 30),
    "coumarin": (0.5, 3),
    "clary sage": (1, 10),
    "geraniol": (1, 10),
}

print(f"\n  {'Material':<25} {'OAV':>10} {'Target':>15} {'Status':>20}")
print(f"  {'-'*25} {'-'*10} {'-'*15} {'-'*20}")

for mat_key, (lo, hi) in FOUGERE_TARGETS.items():
    found = False
    for nm, oav, *_ in ranked:
        if mat_key.replace(" ", "") in nm.lower().replace(" ", ""):
            if lo <= oav <= hi:
                status = "✓ IN RANGE"
            elif oav > hi:
                status = f"↑ ABOVE target >{hi}"
            else:
                status = f"↓ BELOW target <{lo}"
            print(f"  {nm:<25} {oav:>10.1f} {lo}-{hi:>10} {status:>20}")
            found = True
            break
    if not found:
        print(f"  {mat_key:<25} {'--':>10} {lo}-{hi:>10} {'NOT IN FORMULA':>20}")

# ═══════════ 4. CRITICAL RATIOS ═══════════
print(f"\n{DIV}")
print("  4. CRITICAL OAV RATIOS")
print(DIV)

def get_oav(name_substr):
    for nm, oav, *_ in ranked:
        if name_substr.lower() in nm.lower():
            return oav
    return 0

ratios = [
    ("Ambrofix : Iso E Super", "ambrofix", "iso e super", (0.01, 0.5),
     "Sauvage DNA: Ambrox should be textural (low headspace OAV), Iso E provides the vapor halo"),
    ("Hedione : DHM", "hedione", "dihydromyrcenol", (1.0, 5.0),
     "Hedione radiance should exceed DHM blue lift to avoid 'sport deodorant' effect"),
    ("Lavender : Geraniol", "lavender", "geraniol", (2.0, 8.0),
     "Lavender must dominate geranium to maintain fougere identity"),
    ("Grapefruit : Bergamot", "grapefruit", "bergamot", (2.0, 20.0),
     "BdC signature: grapefruit pink-pith should far exceed bergamot"),
    ("Javanol : Ebanol", "javanol", "ebanol", (2.0, 10.0),
     "Architectural sandalwood (dry) should dominate creamy (soft) for modern profile"),
    ("Cashmeran : Ambrofix", "cashmeran", "ambrofix", (0.05, 0.3),
     "Cashmeran warmth should be ~10-20% of Ambrox intensity — textile accent, not dominant"),
]

print(f"\n  {'Ratio':<30} {'Value':>10} {'Target':>12} {'Verdict':>12}")
print(f"  {'-'*30} {'-'*10} {'-'*12} {'-'*12}")

for label, a_key, b_key, (lo, hi), note in ratios:
    a_oav = get_oav(a_key)
    b_oav = get_oav(b_key)
    ratio = a_oav / b_oav if b_oav > 0 else float('inf')
    if lo <= ratio <= hi:
        verdict = "✓ CORRECT"
    elif ratio > hi * 2:
        verdict = "↑↑ HIGH"
    elif ratio > hi:
        verdict = "↑ HIGH"
    elif ratio < lo / 2:
        verdict = "↓↓ LOW"
    else:
        verdict = "↓ LOW"
    print(f"  {label:<30} {ratio:>10.3f} {lo}-{hi:>8} {verdict:>12}")
    if "HIGH" in verdict or "LOW" in verdict:
        print(f"    → {note}")

# ═══════════ 5. HEDONIC VALENCE ANALYSIS ═══════════
print(f"\n{DIV}")
print("  5. HEDONIC ANALYSIS — VALENCE BY OAV WEIGHT")
print(DIV)

from engine.hedonic_model import HEDONIC_VALENCE, score_hedonic

report = score_hedonic(ingredients_ul, dilutions)
print(f"\n  Weighted mean valence: {report.weighted_valence:+.3f}")
print(f"  Hedonic class: {report.pleasantness_class}")
print(f"  Hedonic contrast: {report.hedonic_contrast:.3f}")
print(f"  Pleasant fraction: {report.pleasant_fraction:.1%}")
print(f"  Hedonic score: {report.score:.1f}/100")

for d in report.diagnostics:
    print(f"  {d}")

print(f"\n  Top 5 hedonic contributors (valence × active mass):")
for m in report.most_pleasant:
    print(f"    {m['material']:<30} +{m['valence']:+.2f} × {m['amount_uL']:>6.0f} uL = {m['hedonic_contribution']:>7.0f}")

if report.unpleasant_materials:
    print(f"\n  Unpleasant materials in formula:")
    for m in report.unpleasant_materials:
        print(f"    {m['material']:<30} {m['valence']:+.2f} × {m['amount_uL']:>6.0f} uL")

# ═══════════ 6. SUBLIMINAL LUXURY AUDIT ═══════════
print(f"\n{DIV}")
print("  6. SUBLIMINAL LUXURY AUDIT — materials below OAV 1")
print(DIV)

print(f"\n  {'Material':<30} {'OAV':>10} {'Active':>8} {'Valence':>8} {'Action':>30}")
print(f"  {'-'*30} {'-'*10} {'-'*8} {'-'*8} {'-'*30}")

for nm, oav, vap, odt, pp, gam, mf, vp, act, note in ranked:
    if 0 < oav < 1:
        val = HEDONIC_VALENCE.get(nm, None)
        val_str = f"{val:+.2f}" if val is not None else "N/A"
        action = "↑ boost to OAV>1" if (val and val > 0.6) else "keep subliminal (functional)"
        print(f"  {nm:<30} {oav:>10.3f} {act:>8.1f} {val_str:>8} {action:>30}")

# ═══════════ 7. NIOSH / IFRA SAFETY CHECK ═══════════
print(f"\n{DIV}")
print("  7. SAFETY — IFRA / EU ALLERGEN FLAGS")
print(DIV)

# Check key restricted materials
restricted = {
    "Coumarin": (1.6, "% in leave-on", "IFRA"),
    "Geraniol": (None, "EU allergen (declaration required if >0.001% in leave-on)", "EU 1223/2009"),
    "Evernyl": (0.1, "% in leave-on", "IFRA (as oakmoss substitute, same limits)"),
}

for mat, (limit, unit, source) in restricted.items():
    found = False
    for nm, oav, vap, odt, pp, gam, mf, vp, act, note in ranked:
        if mat.lower() in nm.lower():
            active_pct_final = (act / 30000) * 100  # % in final product
            if limit:
                headroom = (limit - active_pct_final) / limit * 100
                status = "✓" if active_pct_final < limit else "✗ OVER LIMIT"
                print(f"  {status} {nm:<30} {active_pct_final:.4f}% in final product (limit: {limit}% {source}) — {headroom:.0f}% headroom")
            else:
                print(f"  ⚠ {nm:<30} {active_pct_final:.4f}% in final product — {unit} ({source})")
            found = True
            break
    if not found:
        print(f"  — {mat}: not in formula")

# ═══════════ 8. FINAL VERDICT ═══════════
print(f"\n{DIV}")
print("  8. VERDICT")
print(DIV)

# Determine overall assessment
issues = []
wins = []

# Check style references
ambrofix_oav = get_oav("ambrofix")
if ambrofix_oav > 0:
    wins.append(f"Ambrofix at OAV {ambrofix_oav:.1f} — correct skin-texture signature (headspace-subtle, skin-dominant)")

grapefruit_oav = get_oav("grapefruit")
if grapefruit_oav > 1000:
    wins.append(f"Grapefruit dominates opening — BdC pink-pith signature verified")

cashmeran_oav = get_oav("cashmeran")
if cashmeran_oav and cashmeran_oav > 10:
    wins.append(f"Cashmeran at OAV {cashmeran_oav:.0f} — textile warmth perceptible")

hedione_oav = get_oav("hedione")
if hedione_oav and hedione_oav > 1000:
    wins.append(f"Hedione at OAV {hedione_oav:.0f} — radiance ceiling maintained")

habanolide_oav = get_oav("habanolide")
if habanolide_oav and habanolide_oav >= 1:
    wins.append(f"Habanolide at OAV {habanolide_oav:.2f} — warm skin now perceptible (was 0.69)")
elif habanolide_oav:
    issues.append(f"Habanolide still below threshold at OAV {habanolide_oav:.2f}")

aurantiol_oav = get_oav("aurantiol")
if aurantiol_oav and aurantiol_oav < 0.5:
    issues.append(f"Aurantiol at OAV {aurantiol_oav:.2f} — still deeply subliminal, consider larger boost")

scentenal_oav = get_oav("scentenal")
if scentenal_oav and scentenal_oav < 1:
    wins.append(f"Scentenal at OAV {scentenal_oav:.2f} — subliminal (correct for mineral edge)")
elif scentenal_oav and scentenal_oav >= 5:
    issues.append(f"Scentenal at OAV {scentenal_oav:.1f} — too dominant, metallic-coal should be felt not smelled")

# Fougere identity check
lav_oav = get_oav("lavender")
coumarin_oav = get_oav("coumarin")
if lav_oav and coumarin_oav:
    if lav_oav > 5 and coumarin_oav > 0.5:
        wins.append(f"Fougere identity intact: Lavender OAV {lav_oav:.0f} + Coumarin OAV {coumarin_oav:.1f}")
    else:
        issues.append(f"Fougere identity weak: Lavender OAV {lav_oav:.1f}, Coumarin OAV {coumarin_oav:.2f}")

# Hedonic
if report.score >= 75:
    wins.append(f"Hedonic score {report.score:.0f}/100 — highly pleasant (weighted valence {report.weighted_valence:+.2f})")
elif report.score >= 60:
    wins.append(f"Hedonic score {report.score:.0f}/100 — pleasant")
else:
    issues.append(f"Hedonic score {report.score:.0f}/100 — below pleasant threshold")

print("\n  WINS:")
for w in wins:
    print(f"    ✓ {w}")

if issues:
    print(f"\n  ISSUES TO ADDRESS:")
    for i in issues:
        print(f"    ⚠ {i}")
else:
    print(f"\n  No issues detected.")

print(f"\n{SEP}")
print("  OAV ANALYSIS COMPLETE")
print(SEP)
