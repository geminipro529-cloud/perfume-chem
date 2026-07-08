"""Mr. Sandman — YSL Art Design v3 — Galbanum + Evernyl restore the YSL signature.
C11 bold gesture. Galbanum green bite. Evernyl chypre backbone. Contrast = art."""

import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

ODT = {
    "Aldehyde C11 undecylenic":   0.4,  "Aldehyde C12 MNA": 0.3,
    "C11 Undecanal (10%)":        0.15, # undecanal is sharper than undecylenic, ODT ~0.15 ppm
    "C11 undecylenic (1%)":       0.4,  # same ODT as neat, just at 1% dilution
    "C10 (1%)":                   0.3,  # aldehyde C10 — orange-dewy, ODT ~0.3 ppm
    "Bergamot FCF oil Sicilian":  1.5,  "Red Mandarin EO": 2.0,  "Cardamom EO": 1.0,
    "Galbanum Resinoid (10%)":    1.0,  # galbanum pyrazines — potent green, ODT ~1 ppm pure
    "Evernyl (10% in DPG)":       0.5,  # veramoss — modern oakmoss, ODT ~0.5 ppm pure, 10% dilution
    "Hedione": 5.0, "Hedione HC": 3.0, "DBCA": 1.5, "Mayol": 2.0,
    "Heliotropal": 1.0, "Anisaldehyde": 1.0, "Coumarin": 5.0, "Vanillin": 10.0,
    "Alpha Irone": 0.10, "Eugenol": 1.0,
    "Habanolide": 0.2, "Romandolide": 1.0, "Ethylene Brassylate": 2.0,
    "Ambrettolide": 0.5, "Cashmeran": 0.5, "Vertofix": 0.3,
    "Polysantol": 0.5, "Hexyl Salicylate": 30.0, "Labdanum Absolute 10%": 50.0,
    "Kephalis": 5.0,  # woody-amber-ionone texture, moderate ODT
    "Ambrofix (30%)": 0.01,  # ambroxide — extremely potent, ODT ~0.01 ppm in ethanol
    "Javanol (1%)": 0.002,  # extremely potent sandalwood, ODT ~0.002 ppm
    "Clary Sage EO": 3.0,  # herbal-aromatic, moderate ODT
    "Gamma Decalactone": 0.5,  # peach-skin lactone, moderate potency
}

# ========== YSL SIGNATURE RESTORED ==========
# BOLD GESTURE:  C11 undecylenic aldehyde overdose — THE defining sparkle
# GREEN BITE:    Galbanum (10%) — the sappy, bitter-green CHIC that makes it YSL, not just aldehydic
# CHYPRE BONE:   Evernyl (10%) — modern oakmoss backbone. The skeleton Rive Gauche was built on.
# CITRUS HALO:   Bergamot — light around the sparkle
# THE SONG:      Heliotropal + Anisaldehyde — audible lullaby
# YELLOW BLANKET: Cashmeran — comfort object
# SAFE SLEEPING: Coumarin + Vanillin — warm bed
# SKIN INTIMACY: Habanolide + Ambrettolide + Labdanum — making love
# CONTRAST:      COLD aldehydic-galbanum sparkle vs. WARM amber skin heat

FORMULA = [
    # ---- I: ALDEHYDIC SPARKLE (0-5 min) ----
    ("Bergamot FCF oil Sicilian", 700, 100),    # BOOSTED. Signature leads harder.
    ("Aldehyde C12 MNA",         1000,   1),    # BOOSTED. LOUD aldehydic signature — sparkle fix.
    ("C10 (1%)",                  200,   1),    # NEW. Orange-peel dewy sparkle. Lifts the top.
    ("C11 Undecanal (10%)",       350,  10),    # THE sparkle — louder, assertive C11 aldehyde.
    ("Red Mandarin EO",           300, 100),    # Hesperidic bed.
    ("C11 undecylenic (1%)",      500,   1),    # Softer rosy-fatty aldehyde support.
    ("Cardamom EO",               100, 100),    # BOOSTED. Spice bite hits harder.

    # ---- II: JINGLE LULLABY (5-30 min) — the song emerges ----
    ("Hedione",                  1800, 100),    # Jasmin projection. Clean radiance.
    ("Hedione HC",                350, 100),    # High-cis moonlight.
    ("Mayol",                     150, 100),    # NEW. Fresh muguet transparency. Modern YSL lift.
    ("Heliotropal",               250, 100),    # THE SONG — audible, not screaming.
    ("Anisaldehyde",              180, 100),    # Marshmallow harmony — supports the song.
    ("Alpha Irone",                 6,  30),    # Ghost iris. "Tell him..."

    # ---- III: YELLOW BLANKET (30-120 min) — the comfort ----
    ("Cashmeran",                 600,  20),    # YELLOW BLANKET. The comfort object.
    ("Coumarin",                  250,  20),    # Almond-hay. Safe sleeping.
    ("Vanillin",                  400,  10),    # Custard bed.
    ("DBCA",                      120, 100),    # Gardenia petal. Soft body.
    ("Eugenol",                    20, 100),    # Clover whisper.

    # ---- IV: SKIN INTIMACY (2-8 hr) — the making love ----
    ("Habanolide",                 60, 100),    # CLEAN SKIN echo — below bergamot, not crowding it.
    ("Romandolide",               350, 100),    # Projection. "I'm so alone."
    ("Ethylene Brassylate",       400, 100),    # Creamy depth — support, not front row.
    ("Ambrettolide",              250,  10),    # Warm-skin depth. Making love.
    ("Labdanum Absolute 10%",     600,  10),    # AMBER BODY HEAT — wraps the drydown.
    ("Evernyl (10% in DPG)",      100,  10),    # CHYPRE BACKBONE — felt, not guessed at.
    ("Polysantol",                 25, 100),    # Sandalwood cream.
    ("Vertofix",                   50, 100),    # Woody bridge — structure, not main character.
    ("Hexyl Salicylate",          700, 100),    # Transparent sheets.
    ("Kephalis",                   80, 100),    # Dry woody-iris texture. Gravelly skin depth.
    ("Javanol (1%)",              10,   1),    # Transparent sandalwood polish. Micro-dose at 1%.
    ("Clary Sage EO",              25, 100),    # Herbal-aromatic lift. Bridges aldehydes to jingle.
    ("Gamma Decalactone",         20, 100),    # Creamy peach-skin velvet. "Making love" cushion.
    ("Ambrofix (30%)",              5,  30),    # Crystalline glow. "Bring me a dream" luminescence.
]

CUT = ["Geraniol","Damascol","Phenethyl Alcohol","Farnesol","Musk Ketone","Exaltolide","Iso E Super","Azarbre","Siam Benzoin 50%"]
OLD = {
    "Bergamot FCF oil Sicilian": 487, "Aldehyde C11 undecylenic": 75, "Aldehyde C12 MNA": 412,
    "Red Mandarin EO": 250, "Cardamom EO": 56, "Hedione": 1500, "Hedione HC": 375,
    "Heliotropal": 650, "Anisaldehyde": 325, "Coumarin": 750, "Vanillin": 500, "Eugenol": 24,
    "DBCA": 138, "Alpha Irone": 10, "Habanolide": 275, "Romandolide": 375,
    "Ethylene Brassylate": 900, "Ambrettolide": 350, "Cashmeran": 875,
    "Vertofix": 165, "Polysantol": 44, "Hexyl Salicylate": 787,
    "Labdanum Absolute 10%": 100,     "Kephalis": 0, "Ambrofix (30%)": 0, "Mayol": 0, "Javanol (1%)": 0, "Clary Sage EO": 0, "Gamma Decalactone": 0,
    "C11 Undecanal (10%)": 0, "C11 undecylenic (1%)": 0, "C10 (1%)": 0,
}

SECTIONS = {
    "I-SPARK":   ["Aldehyde C11 undecylenic","Bergamot FCF oil Sicilian","Aldehyde C12 MNA","Red Mandarin EO","Cardamom EO","C11 Undecanal (10%)","C11 undecylenic (1%)","C10 (1%)"],
    "II-JINGLE": ["Hedione","Hedione HC","Mayol","Heliotropal","Anisaldehyde","Alpha Irone"],
    "III-BLANKET": ["Cashmeran","Coumarin","Vanillin","DBCA","Eugenol"],
    "IV-SKIN":   ["Habanolide","Romandolide","Ethylene Brassylate","Ambrettolide","Labdanum Absolute 10%","Evernyl (10% in DPG)","Polysantol","Vertofix","Hexyl Salicylate","Kephalis","Ambrofix (30%)","Javanol (1%)","Clary Sage EO","Gamma Decalactone"],
}
section_map = {}; [section_map.update({n: sec}) for sec, ns in SECTIONS.items() for n in ns]

tc_full = sum(ul for _, ul, _ in FORMULA)
frac = tc_full / 50000
results = []

for name, ul, dil in FORMULA:
    act = ul * dil / 100
    conc_ppm = act / tc_full * 1e6
    edp_ppm = conc_ppm * frac
    odt = ODT.get(name, 5.0)
    oav = edp_ppm / odt
    if oav > 5000:       tier = "MEGA"
    elif oav > 500:      tier = "EXTREME"
    elif oav > 50:       tier = "DOMINANT"
    elif oav > 5:        tier = "clear"
    elif oav > 1:        tier = "weak"
    else:                tier = "subliminal"
    results.append((name, ul, dil, act, odt, oav, tier))

results.sort(key=lambda x: -x[5])

role = {
    "Aldehyde C11 undecylenic": "Aldehydic sparkle — assertive. Mr. Sandman signature.",
    "C11 Undecanal (10%)": "THE sparkle — sharper classic YSL C11 aldehyde.",
    "C11 undecylenic (1%)": "Softer rosy-fatty aldehyde support.",
    "Bergamot FCF oil Sicilian": "Citrus brightness — leads the opening.",
    "Aldehyde C12 MNA": "LOUD aldehydic signature — prominent in the spray.",
    "Red Mandarin EO": "Hesperidic bed — warm tangerine.",
    "Cardamom EO": "Spice bite — YSL DNA.",
    "Hedione": "Jasmin projection — carries the song.",
    "Hedione HC": "Moonlight jasmine.",
    "Heliotropal": "THE SONG — 'Bum bum bum bum...' Jingle lead.",
    "Anisaldehyde": "Marshmallow — 'Bring me a dream...'",
    "Alpha Irone": "Ghost iris — rumor of a veil.",
    "Cashmeran": "YELLOW BLANKET — comfort object. 'Lonesome nights are over.'",
    "Coumarin": "Almond-hay — safe sleeping softness.",
    "Vanillin": "Custard bed — warm, soft.",
    "DBCA": "Gardenia petal — soft body. No rose.",
    "Eugenol": "Clover whisper — 'Two lips like roses and clover.'",
    "Habanolide": "CLEAN SKIN echo — below bergamot, present not dominant.",
    "Heliotropal": "THE SONG — audible, not screaming.",
    "Anisaldehyde": "Marshmallow — supports the song.",
    "Ethylene Brassylate": "Creamy depth — the bed, supports.",
    "Vertofix": "Woody bridge — structure only.",
    "Evernyl (10% in DPG)": "Chypre backbone — modern oakmoss. FELT, not guessed.",
    "Labdanum Absolute 10%": "AMBER BODY HEAT — wraps the drydown.",
    "Polysantol": "Sandalwood cream.",
    "Vertofix": "Woody bridge.",
    "Hexyl Salicylate": "Transparent sheets.",
    "Kephalis": "Dry woody-iris texture. Gravelly, intimate skin.",
    "Ambrofix (30%)": "Crystalline glow. Luminous dream. 'Bring me a dream...'",
    "Mayol": "Fresh muguet transparency. Modern YSL lift.",
    "C10 (1%)": "Orange-peel dewy sparkle. Brightens the top.",
    "Javanol (1%)": "Transparent sandalwood polish. Invisible luxe finish.",
    "Clary Sage EO": "Herbal-aromatic lift. Bridges sparkle to jingle.",
    "Gamma Decalactone": "Creamy peach-skin velvet. Intimate drydown cushion.",
}

print("=" * 112)
print(f"{'MR. SANDMAN — YSL EDITION — Signature Opening Boosted':^112}")
print(f"{'Bergamot 600. C12 MNA 600. C11 100. The aldehydic opening HITS. Jingle sings. Blanket wraps.':^112}")
print("=" * 112)
print()

print(f"  {'Mvt':<10} {'#':>2} {'Material':<27} {'Old':>6} {'New':>6} {'Dil%':>5} {'OAV':>8} {'Tier':>10}  {'Role'}")
print(f"  {'-'*108}")

prev_sec = ""
for i, (name, ul, dil, act, odt, oav, tier) in enumerate(results):
    sec = section_map.get(name, "???")
    if sec != prev_sec:
        print()
        prev_sec = sec

    old_ul = OLD.get(name, 0)
    is_new = old_ul == 0
    ch = "NEW" if is_new else (">>" if abs(old_ul - ul) > 1 else "  ")
    r = role.get(name, "")

    print(f"  {sec:<10} {i+1:>2} {name:<27} {old_ul:>6} {ch:>4} {ul:>6} {dil:>4}% {oav:>8.0f} {tier:>10}  {r}")

# Movement totals
av = lambda sec: sum(r[5] for r in results if section_map[r[0]] == sec)
total = av("I-SPARK") + av("II-JINGLE") + av("III-BLANKET") + av("IV-SKIN")

lab_ul = next((r[1] for r in results if "Labdanum" in r[0]), 0)
gal_ul = next((r[1] for r in results if "Galbanum" in r[0]), 0)
evn_ul = next((r[1] for r in results if "Evernyl" in r[0]), 0)
hel_ul = next((r[1] for r in results if "Heliotropal" in r[0]), 0)
cas_ul = next((r[1] for r in results if "Cashmeran" in r[0]), 0)
cou_ul = next((r[1] for r in results if "Coumarin" in r[0]), 0)
hab_ul = next((r[1] for r in results if "Habanolide" in r[0]), 0)
amb_ul = next((r[1] for r in results if "Ambrettolide" in r[0]), 0)

print()
print(f"  {'='*108}")
print(f"  CONCENTRATION: {tc_full/50000*100:.1f}% EDP  ({tc_full:,} uL / 50,000 uL)   Ethanol: {50000-tc_full:,} uL")
print(f"  TOTAL OAV: {total:,.0f}")
print(f"  I-SPARK: {av('I-SPARK'):,.0f} ({av('I-SPARK')/total*100:.0f}%) | II-JINGLE: {av('II-JINGLE'):,.0f} ({av('II-JINGLE')/total*100:.0f}%) | III-BLANKET: {av('III-BLANKET'):,.0f} ({av('III-BLANKET')/total*100:.0f}%) | IV-SKIN: {av('IV-SKIN'):,.0f} ({av('IV-SKIN')/total*100:.0f}%)")
print()
print(f"  YSL SIGNATURE RESTORED (original Mr. Sandman top + YSL structure):")
print(f"    SIGNATURE TOP: Bergamot(600uL) + C12 MNA(600uL of 1%) + C11(100uL) + Mandarin(300uL) + Cardamom(100uL)")
print(f"    CHYPRE BACKBONE: Evernyl({evn_ul}uL of 10%) -- modern oakmoss. The skeleton.")
print(f"    CONTRAST:     COLD aldehydic sparkle -> WARM amber body heat (Labdanum {lab_ul}uL).")
print(f"    THE SONG:     Heliotropal({hel_ul}uL) + Anisaldehyde. Audible lullaby.")
print(f"    YELLOW BLANKET: Cashmeran({cas_ul}uL of 20%). Comfort object.")
print(f"    SAFE SLEEPING: Coumarin({cou_ul}uL of 20%) almond-hay + Vanillin custard.")
print(f"    MAKING LOVE:  Habanolide({hab_ul}uL) clean skin + Ambrettolide({amb_ul}uL) warm depth + Labdanum amber heat.")
print()
print(f"  MUSK (4): Habanolide > Romandolide > EB > Ambrettolide")
print(f"  CUT (9): {', '.join(CUT)}")
print(f"  NEW (3): C11 Undecanal (10%), C11 undecylenic (1%), Evernyl (10% in DPG), Kephalis, Ambrofix (30%)")
tiers = {}
for r in results: tiers[r[6]] = tiers.get(r[6], 0) + 1
print(f"  TIERS: {' * '.join(f'{k}={v}' for k, v in tiers.items())}   MATERIALS: {len(FORMULA)}")
