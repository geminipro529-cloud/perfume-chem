"""YSL Edition rebalance — as YSL's perfumer would critique."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

ODT = {
    "Bergamot FCF oil Sicilian":  1.5,
    "Aldehyde C11 undecylenic":    0.4,
    "Aldehyde C12 MNA":            0.3,
    "Red Mandarin EO":             2.0,
    "Cardamom EO":                 1.0,
    "Hedione":                     5.0,
    "Hedione HC":                  3.0,
    "DBCA":                        1.5,
    "Heliotropal":                 1.0,
    "Anisaldehyde":                1.0,
    "Coumarin":                    5.0,
    "Vanillin":                   10.0,
    "Alpha Irone":                 0.10,
    "Phenethyl Alcohol":          40.0,
    "Geraniol":                    5.0,
    "Damascol":                    0.05,
    "Eugenol":                     1.0,
    "Farnesol":                   10.0,
    "Habanolide":                  0.2,
    "Romandolide":                 1.0,
    "Ethylene Brassylate":         2.0,
    "Musk Ketone":                 2.0,
    "Ambrettolide":                0.5,
    "Exaltolide":                  1.0,
    "Cashmeran":                   0.5,
    "Iso E Super":                 2.0,
    "Azarbre":                     0.5,
    "Polysantol":                  0.5,
    "Vertofix":                    0.3,
    "Hexyl Salicylate":           30.0,
    "Siam Benzoin 50%":           10.0,
    "Labdanum Absolute 10%":      50.0,
}

# ===== YSL CRITIQUE TARGETS =====
# Bergamot must be #1. Period. YSL signature leads.
# Habanolide clean musk = character-echo, slightly below bergamot.
# C11 undecylenic = THE sparkle. C12 MNA = the echo.
# Powder jingle = ghost jingle, perceptible but not shouting.
# Iso E Super = slash mercilessly. YSL is not Hermes/Bulgari.
# EB = supporting player, not leader. Habanolide is the clean musk.
# Labdanum = Rive Gauche amber body heat. Increase.

TARGETS = {
    # TOP — KEEP (YSL signatures, don't touch)
    "Bergamot FCF oil Sicilian":  "keep",
    "Aldehyde C11 undecylenic":   "keep",
    "Aldehyde C12 MNA":           "keep",
    "Red Mandarin EO":            "keep",
    "Cardamom EO":                "keep",

    # HEDIONE — projection engine
    "Hedione":                    0.65,
    "Hedione HC":                 0.30,

    # IRIS — ghost whisper (rumor of iris)
    "Alpha Irone":                0.03,

    # JINGLE — ghost jingle (perceptible, never shouting)
    "Heliotropal":                0.30,
    "Anisaldehyde":               0.20,
    "Coumarin":                   0.06,
    "Vanillin":                   0.01,
    "Eugenol":                    0.03,

    # FLORAL BODY — rose-plum ghost
    "DBCA":                       0.15,
    "Phenethyl Alcohol":          0.01,
    "Damascol":                   0.20,
    "Geraniol":                   0.02,
    "Farnesol":                   0.005,

    # MUSK CHORD — Habanolide > Romandolide > EB (clean white musk leads)
    "Habanolide":                 0.85,
    "Romandolide":                0.65,
    "Ethylene Brassylate":        0.55,
    "Musk Ketone":                0.05,
    "Ambrettolide":               0.10,
    "Exaltolide":                 0.02,

    # WARMTH + STRUCTURE — slash Iso E, boost Labdanum
    "Iso E Super":                0.20,
    "Cashmeran":                  0.30,
    "Azarbre":                    0.25,
    "Vertofix":                   0.45,
    "Polysantol":                 0.10,
    "Hexyl Salicylate":           0.05,
    "Siam Benzoin 50%":           0.01,
    "Labdanum Absolute 10%":      0.004,
}

# Current formula
CURRENT = [
    ('Ethylene Brassylate',900,100),('Labdanum Absolute 10%',100,10),('Cashmeran',875,20),
    ('Hexyl Salicylate',787,100),('Musk Ketone',600,10),('Iso E Super',400,100),
    ('Romandolide',375,100),('Ambrettolide',350,10),('Habanolide',275,100),
    ('Azarbre',175,100),('Vertofix',165,100),('Siam Benzoin 50%',110,50),
    ('Exaltolide',107,10),('Polysantol',44,100),
    ('Hedione',1500,100),('Hedione HC',375,100),
    ('Alpha Irone',10,30),
    ('Coumarin',750,20),('Heliotropal',650,100),('Vanillin',500,10),
    ('Anisaldehyde',325,100),('Eugenol',24,100),
    ('DBCA',138,100),('Phenethyl Alcohol',95,100),('Damascol',94,10),
    ('Geraniol',51,100),('Farnesol',24,100),
    ('Bergamot FCF oil Sicilian',487,100),('Aldehyde C12 MNA',412,1),
    ('Red Mandarin EO',250,100),('Aldehyde C11 undecylenic',75,100),
    ('Cardamom EO',56,100)]

# Reference bergamot OAV
TC_REF = 11079
EC_REF = 0.234
berg_oav = (487 * 1.0 / TC_REF * 1e6 * EC_REF) / 1.5

# Compute new doses — exact targets, NO scaling
new_f = {}
for name, ul, dil in CURRENT:
    odt = ODT[name]
    tgt = TARGETS[name]

    if tgt == "keep":
        new_f[name] = (ul, dil)
    else:
        # ul = target_oav * odt * TC_REF / (1e6 * EC_REF * dil/100)
        target_oav = berg_oav * tgt
        new_ul = round(target_oav * odt * TC_REF / (1e6 * EC_REF * dil / 100))
        new_f[name] = (max(1, new_ul), dil)

# Assemble and scale to ~20% EDP
new_formula_raw = [(name, new_f[name][0], new_f[name][1]) for name, _, _ in CURRENT]

# Scale non-top materials to hit 20% EDP (~10,000 uL total)
top_ul = sum(ul for name, ul, _ in new_formula_raw if TARGETS[name] == "keep")
non_top_ul = sum(ul for name, ul, _ in new_formula_raw if TARGETS[name] != "keep")
target_total = 10000  # 50mL * 20%
target_non_top = target_total - top_ul
scale = target_non_top / non_top_ul

new_formula = []
for name, ul, dil in new_formula_raw:
    if TARGETS[name] == "keep":
        new_formula.append((name, ul, dil))
    else:
        new_formula.append((name, max(1, round(ul * scale)), dil))

non_top_scaled = sum(ul for name, ul, _ in new_formula if TARGETS[name] != "keep")

# Compute totals
tc_full = sum(ul for _, ul, _ in new_formula)
tc_act = sum(ul * dil / 100 for _, ul, dil in new_formula)
conc_pct = tc_full / 50000 * 100
frac = tinyml = tc_full / 50000

# OAV analysis using actual fraction
results = []
for name, ul, dil in new_formula:
    act = ul * dil / 100
    conc_ppm = act / tc_full * 1e6
    edp_ppm = conc_ppm * frac
    odt = ODT[name]
    oav = edp_ppm / odt

    if oav > 5000:     tier = "MEGA"
    elif oav > 500:    tier = "EXTREME"
    elif oav > 50:     tier = "DOMINANT"
    elif oav > 5:      tier = "clear"
    elif oav > 1:      tier = "weak"
    else:              tier = "subliminal"

    results.append((name, ul, dil, act, odt, oav, tier))

results.sort(key=lambda x: -x[5])

old_lookup = {name: ul for name, ul, _ in CURRENT}

print("=" * 110)
print(f"{'YSL PERFUMER CRITIQUE — Mr. Sandman Rebalance':^110}")
print(f"{'Bergamot leads. Clean musk echoes. Ghost jingle whispers. Iso E slashed. Labdanum warms.':^110}")
print("=" * 110)
print()

print(f"  {'#':>2} {'Material':<28} {'Old':>6}  {'New':>6} {'Dil%':>5} {'ODT':>7} {'OAV':>8} {'Tier':>10} {'Ratio':>7} {'YSL Note'}")
print(f"  {'-'*105}")

prev_tier = ""
for i, (name, ul, dil, act, odt, oav, tier) in enumerate(results):
    if tier != prev_tier:
        print()
        prev_tier = tier

    old_ul = old_lookup.get(name, ul)
    ch = ">>" if old_ul != ul else "  "
    ratio = oav / berg_oav

    # Generate YSL note
    if name == "Bergamot FCF oil Sicilian":
        note = "THE signature. Leads. No compromise."
    elif name == "Aldehyde C11 undecylenic":
        note = "THE sparkle. Rive Gauche DNA."
    elif name == "Aldehyde C12 MNA":
        note = "C11 echo. Ethereal shimmer."
    elif name == "Habanolide":
        note = "Clean musk leader. YSL character."
    elif name == "Romandolide":
        note = "Projection. Behind bergamot."
    elif name == "Ethylene Brassylate":
        note = "Support player. Not front row."
    elif name == "Iso E Super":
        note = "Slashed. YSL is not Bulgari."
    elif name == "Heliotropal":
        note = "Ghost jingle. Perceptible, not shouting."
    elif name == "Anisaldehyde":
        note = "Marshmallow whisper under jingle."
    elif name == "Coumarin":
        note = "Almond-hay whisper. Drydown only."
    elif name == "Vanillin":
        note = "Fixative, not dessert patisserie."
    elif name == "Cashmeran":
        note = "Yellow blanket, not yellow wall."
    elif name == "Labdanum Absolute 10%":
        note = "Rive Gauche amber body heat. Warmed up."
    elif name == "Hedione HC":
        note = "Jasmin boost. Proportional."
    elif name == "Alpha Irone":
        note = "Rumor of iris. Ghost veil."
    elif name == "Damascol":
        note = "Rose-plum ghost under aldehydes."
    elif name == "Eugenol":
        note = "Clove whisper. Opium trace."
    elif name == "Vertofix":
        note = "Woody bridge. Structure, not volume."
    elif name == "Musk Ketone":
        note = "Classic powdery trace. Reduced."
    elif name == "Hexyl Salicylate":
        note = "Transparent fixative. Restrained."
    elif name == "Siam Benzoin 50%":
        note = "Warm vanilla anchor. Hour-8."
    elif name == "Farnesol":
        note = "Lily whisper. Fixative depth."
    else:
        note = ""

    print(f"  {i+1:2d} {name:<28} {old_ul:>6} {ch} {ul:>6} {dil:>4}% {odt:>7.3f} {oav:>8.0f} {tier:>10} {ratio:>6.2f}x   {note}")

# Section totals
sec_top = [r for r in results if r[0] in ["Bergamot FCF oil Sicilian","Aldehyde C11 undecylenic","Aldehyde C12 MNA","Red Mandarin EO","Cardamom EO"]]
sec_heart = [r for r in results if r[0] in ["Hedione","Hedione HC","Heliotropal","Anisaldehyde","Coumarin","Vanillin","Alpha Irone","Eugenol","DBCA","Phenethyl Alcohol","Geraniol","Damascol","Farnesol"]]
sec_base = [r for r in results if r[0] not in [x[0] for x in sec_top] and r[0] not in [x[0] for x in sec_heart]]

top_oav = sum(r[5] for r in sec_top)
heart_oav = sum(r[5] for r in sec_heart)
base_oav = sum(r[5] for r in sec_base)
total = top_oav + heart_oav + base_oav

print()
print(f"  {'='*105}")
print(f"  TOTAL OAV: {total:,.0f}    concentration: {conc_pct:.1f}% ({tc_full:,} uL / 50,000 uL)")
print(f"  TOP: {top_oav:,.0f} ({top_oav/total*100:.0f}%)  |  HEART: {heart_oav:,.0f} ({heart_oav/total*100:.0f}%)  |  BASE: {base_oav:,.0f} ({base_oav/total*100:.0f}%)")
print(f"  Musk chord: Habanolide {new_f['Habanolide'][0]} uL > Romandolide {new_f['Romandolide'][0]} uL > EB {new_f['Ethylene Brassylate'][0]} uL")
print(f"  Iso E Super: {old_lookup['Iso E Super']} -> {new_f['Iso E Super'][0]} uL (YSL is not Hermes)")
print(f"  Labdanum: {old_lookup['Labdanum Absolute 10%']} -> {new_f['Labdanum Absolute 10%'][0]} uL (Rive Gauche body heat)")
print()
print(f"  TIER DISTRIBUTION:")
for tier_name in ["MEGA", "EXTREME", "DOMINANT", "clear", "weak", "subliminal"]:
    count = len([r for r in results if r[6] == tier_name])
    if count > 0:
        print(f"    {tier_name:>10}: {count} material{'s' if count>1 else ' '}")
