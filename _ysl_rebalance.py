"""Rebalance YSL — let aldehydic top lead without touching signature materials."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

# === ODT TABLE (verified internet estimates) ===
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

# === TARGET OAV RATIOS (relative to Bergamot = 1.0x) ===
# Top signature: KEEP current doses → OAVs stay fixed
# Heart jingle: reduce to 0.3-0.6x bergamot
# Base musks: reduce to 0.5-0.9x bergamot
# Everything else: reduce to 0.05-0.3x bergamot

# Target OAV multipliers relative to bergamot OAV
TARGETS = {
    # TOP — KEEP (signature, don't touch)
    "Bergamot FCF oil Sicilian":  "keep",
    "Aldehyde C11 undecylenic":   "keep",
    "Aldehyde C12 MNA":           "keep",
    "Red Mandarin EO":            "keep",
    "Cardamom EO":                "keep",

    # HEDIONE — projection engine, moderate reduction
    "Hedione":                    0.65,   # was 0.93x
    "Hedione HC":                 0.40,   # was 0.39x

    # IRIS — whisper
    "Alpha Irone":                0.03,   # was 0.09x

    # JINGLE — support, not compete
    "Heliotropal":                0.50,   # was 2.0x
    "Anisaldehyde":               0.35,   # was 1.0x
    "Coumarin":                   0.10,   # was 0.09x
    "Vanillin":                   0.02,   # was 0.02x
    "Eugenol":                    0.05,   # was 0.07x

    # FLORAL BODY — subtle
    "DBCA":                       0.20,   # was 0.28x
    "Phenethyl Alcohol":          0.01,   # was 0.01x
    "Damascol":                   0.30,   # was 0.58x
    "Geraniol":                   0.03,   # was 0.03x
    "Farnesol":                   0.01,   # was 0.01x

    # BASE MUSKS — foundation, not wall
    "Habanolide":                 0.75,   # was 4.2x
    "Romandolide":                0.65,   # was 1.2x
    "Ethylene Brassylate":        0.90,   # was 1.4x
    "Musk Ketone":                0.10,   # was 0.09x
    "Ambrettolide":               0.15,   # was 0.22x
    "Exaltolide":                 0.03,   # was 0.03x
    "Cashmeran":                  0.50,   # was 1.1x
    "Iso E Super":                0.60,   # was 0.62x
    "Azarbre":                    0.50,   # was 1.1x
    "Polysantol":                 0.20,   # was 0.27x
    "Vertofix":                   0.65,   # was 1.7x
    "Hexyl Salicylate":           0.08,   # was 0.08x
    "Siam Benzoin 50%":           0.02,   # was 0.02x
    "Labdanum Absolute 10%":      0.001,  # warmth trace
}

# Current formula (name, uL, dil%)
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

TC = 11079
EC = 0.234

# Step 1: Compute current bergamot OAV (reference)
berg_ul, berg_dil = 487, 100
berg_act = berg_ul * berg_dil / 100
berg_oav = (berg_act / TC * 1e6 * EC) / ODT["Bergamot FCF oil Sicilian"]
print(f"Bergamot reference OAV: {berg_oav:,.0f}")

# Step 2: Compute new µL for each material
new_formula = []
for name, ul, dil in CURRENT:
    odt = ODT[name]
    target = TARGETS[name]

    if target == "keep":
        new_ul = ul
    else:
        target_oav = berg_oav * target
        # OAV = (ul * dil/100) / TC * 1e6 * EC / odt
        # ul = target_oav * odt * TC / (1e6 * EC * dil/100)
        new_ul = target_oav * odt * TC / (1e6 * EC * dil / 100)
        new_ul = max(1, round(new_ul))

    new_formula.append((name, new_ul, dil))

# Step 3: Compute new total and scale to ~23.4% EDP
new_tc = sum(ul * dil / 100 for name, ul, dil in new_formula)
# Wait, that's active µL. Total concentrate µL is sum of ul (stock volumes).
new_tc_ul = sum(ul for name, ul, dil in new_formula)
print(f"\nNew concentrate total: {new_tc_ul:,} µL ({new_tc_ul/50000*100:.1f}%)")

# If concentration is too low, scale up non-top materials proportionally
TARGET_CONC = 11079  # keep ~23.4%
if new_tc_ul < TARGET_CONC * 0.85:
    # Scale factor for non-top materials
    top_ul = sum(ul for name, ul, dil in new_formula if TARGETS[name] == "keep")
    non_top_ul = new_tc_ul - top_ul
    target_non_top = TARGET_CONC - top_ul
    scale = target_non_top / non_top_ul
    print(f"Scaling non-top materials by {scale:.2f}x to maintain concentration")

    scaled_formula = []
    for name, ul, dil in new_formula:
        if TARGETS[name] == "keep":
            scaled_formula.append((name, ul, dil))
        else:
            scaled_formula.append((name, max(1, round(ul * scale)), dil))

    new_formula = scaled_formula
    new_tc_ul = sum(ul for name, ul, dil in new_formula)
    print(f"Scaled concentrate total: {new_tc_ul:,} µL ({new_tc_ul/50000*100:.1f}%)")

# Step 4: Final OAV analysis
print(f"\n{'='*95}")
print(f"{'MR. SANDMAN — YSL EDITION — REBALANCED OAV ANALYSIS':^95}")
print(f"{'Top signature preserved · Base + heart reduced to support, not compete':^95}")
print(f"{'='*95}\n")

results = []
for name, ul, dil in new_formula:
    act = ul * dil / 100
    conc_ppm = act / new_tc_ul * 1e6
    edp_ppm = conc_ppm * (new_tc_ul / 50000)
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

print(f"  {'#':>2} {'Material':<28} {'Old uL':>6} {'New uL':>6} {'Act':>6} {'ODT':>7} {'OAV':>8} {'Tier':>10} {'Ratio':>7}")
print(f"  {'-'*90}")

# Build old lookup
old_lookup = {name: ul for name, ul, dil in CURRENT}

prev_tier = ""
for i, (name, ul, dil, act, odt, oav, tier) in enumerate(results):
    if tier != prev_tier:
        print()
        prev_tier = tier

    old_ul = old_lookup.get(name, ul)
    ratio = oav / berg_oav if berg_oav > 0 else 0
    change = ">>" if old_ul != ul else "  "
    print(f"  {i+1:2d} {name:<28} {old_ul:>6} {change} {ul:>6} {act:>6.1f} {odt:>7.3f} {oav:>8.0f} {tier:>10} {ratio:>6.2f}x")

# Section totals
sec_top = [r for r in results if r[0] in ["Bergamot FCF oil Sicilian","Aldehyde C11 undecylenic","Aldehyde C12 MNA","Red Mandarin EO","Cardamom EO"]]
sec_heart = [r for r in results if r[0] in ["Hedione","Hedione HC","Heliotropal","Anisaldehyde","Coumarin","Vanillin","Alpha Irone","Eugenol","DBCA","Phenethyl Alcohol","Geraniol","Damascol","Farnesol"]]
sec_base = [r for r in results if r[0] not in [x[0] for x in sec_top] and r[0] not in [x[0] for x in sec_heart]]

top_oav = sum(r[5] for r in sec_top)
heart_oav = sum(r[5] for r in sec_heart)
base_oav = sum(r[5] for r in sec_base)
total = top_oav + heart_oav + base_oav

print()
print(f"  {'='*90}")
print(f"  TOTAL OAV: {total:,.0f}")
print(f"  TOP: {top_oav:,.0f} ({top_oav/total*100:.0f}%)  |  HEART: {heart_oav:,.0f} ({heart_oav/total*100:.0f}%)  |  BASE: {base_oav:,.0f} ({base_oav/total*100:.0f}%)")
print(f"  Concentration: {new_tc_ul/50000*100:.1f}% EDP")
print()
print(f"  TIER DISTRIBUTION:")
for tier_name in ["MEGA", "EXTREME", "DOMINANT", "clear", "weak", "subliminal"]:
    count = len([r for r in results if r[6] == tier_name])
    if count > 0:
        print(f"    {tier_name:>10}: {count} material{'s' if count>1 else ' '}")
