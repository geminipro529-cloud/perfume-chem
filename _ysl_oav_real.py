"""OAV analysis — YSL Edition — with realistic ODT estimates."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

# --- CONSERVATIVE ODT ESTIMATES (ppm in ethanol) ---
# Sourced from Leffingwell, van Gemert, Arctander, and class-normalized estimates
# Overrides only for values where engine data is physically impossible

ODT = {
    # Top
    "Bergamot FCF oil Sicilian":  1.5,   # citrus EO - Leffingwell
    "Aldehyde C11 undecylenic":    0.4,   # aldehyde C11 class - Arctander
    "Aldehyde C12 MNA":            0.3,   # aldehyde C12 class - Arctander (up from 0.05)
    "Red Mandarin EO":             2.0,   # citrus EO class
    "Cardamom EO":                 1.0,   # spice EO class
    
    # Heart — Jasmine / Diffusion
    "Hedione":                     5.0,   # jasmonate - Leffingwell (correct)
    "Hedione HC":                  3.0,   # jasmonate - high-cis, slightly more potent
    "DBCA":                        1.5,   # gardenia ester - mid-range floral (up from 0.1)
    "Heliotropal":                 1.0,   # heliotropin class - van Gemert
    "Anisaldehyde":                1.0,   # anisic aldehyde - van Gemert
    "Coumarin":                    5.0,   # coumarin - Leffingwell (correct)
    "Vanillin":                   10.0,   # vanilla - Leffingwell (correct)
    
    # Heart — Iris
    "Alpha Irone":                 0.10,  # irone class - conservative (engine says 0.16)
    
    # Heart — Floral
    "Phenethyl Alcohol":          40.0,   # PEA - Leffingwell (correct)
    "Geraniol":                    5.0,   # geraniol - Leffingwell
    "Damascol":                    0.05,  # damascone ALCOHOL - NOT damascone ketone (engine had 0.005)
    "Eugenol":                     1.0,   # eugenol - Leffingwell (correct)
    "Farnesol":                   10.0,   # farnesol - Leffingwell (correct)
    
    # Base — Musks
    "Habanolide":                  0.2,   # macrocyclic musk - correct
    "Romandolide":                 1.0,   # diffusive musk - mid-range
    "Ethylene Brassylate":         2.0,   # creamy musk - Leffingwell
    "Musk Ketone":                 2.0,   # nitro-musk - Leffingwell
    "Ambrettolide":                0.5,   # macrocyclic musk - van Gemert (correct)
    "Exaltolide":                  1.0,   # macrocyclic musk - correct
    
    # Base — Warmth / Structure
    "Cashmeran":                   0.5,   # synthetic cashmere - correct
    "Iso E Super":                 2.0,   # Iso E Super - Leffingwell (correct)
    "Azarbre":                     0.5,   # cedar-amber - moderate
    "Polysantol":                  0.5,   # sandalwood - moderate potency
    "Vertofix":                    0.3,   # woody bridge - potent (engine says 0.3, seems low but keep)
    
    # Base — Fixatives
    "Hexyl Salicylate":           30.0,   # salicylate - Leffingwell (correct)
    "Siam Benzoin 50%":           10.0,   # balsamic - van Gemert
    "Labdanum Absolute 10%":      50.0,   # amber-resinoid dilution - estimated
}

# Final YSL formula — (name, uL, dilution_pct) — matches Mr_Sandman_YSL.md exactly
F = [
    # Stage 1 — Base (5,263 uL, 14 materials)
    ('Ethylene Brassylate',900,100),('Labdanum Absolute 10%',100,10),('Cashmeran',875,20),
    ('Hexyl Salicylate',787,100),('Musk Ketone',600,10),('Iso E Super',400,100),
    ('Romandolide',375,100),('Ambrettolide',350,10),('Habanolide',275,100),
    ('Azarbre',175,100),('Vertofix',165,100),('Siam Benzoin 50%',110,50),
    ('Exaltolide',107,10),('Polysantol',44,100),
    # Stage 2 — Hedione (1,875 uL, 2 materials)
    ('Hedione',1500,100),('Hedione HC',375,100),
    # Stage 3 — Iris (10 uL, 1 material)
    ('Alpha Irone',10,30),
    # Stage 4 — Jingle + Spice (2,249 uL, 5 materials)
    ('Coumarin',750,20),('Heliotropal',650,100),('Vanillin',500,10),
    ('Anisaldehyde',325,100),('Eugenol',24,100),
    # Stage 5 — Floral Body (402 uL, 5 materials)
    ('DBCA',138,100),('Phenethyl Alcohol',95,100),('Damascol',94,10),
    ('Geraniol',51,100),('Farnesol',24,100),
    # Stage 6 — Top (1,280 uL, 5 materials)
    ('Bergamot FCF oil Sicilian',487,100),('Aldehyde C12 MNA',412,1),
    ('Red Mandarin EO',250,100),('Aldehyde C11 undecylenic',75,100),
    ('Cardamom EO',56,100)]

TC = 11079  # concentrate uL — matches formula total
EC = 0.234  # EDP fraction

results = []
for name, ul, dil in F:
    act = ul * dil / 100
    conc_ppm = act / TC * 1e6
    edp_ppm = conc_ppm * EC
    odt = ODT.get(name, 5.0)  # default 5 ppm if unknown
    oav = edp_ppm / odt
    
    if oav > 5000:     tier = "MEGA"
    elif oav > 500:    tier = "EXTREME"
    elif oav > 50:     tier = "DOMINANT"
    elif oav > 5:      tier = "clear"
    elif oav > 1:      tier = "weak"
    else:              tier = "subliminal"
    
    results.append((name, ul, act, odt, oav, tier))

results.sort(key=lambda x: -x[4])

print("=" * 95)
print(f"{'MR. SANDMAN — YSL EDITION — OAV ANALYSIS (realistic ODTs)':^95}")
print(f"{'32 materials · 50 mL @ 23.4% EDP · 11,079 uL concentrate':^95}")
print("=" * 95)
print()
print(f"  {'#':>2} {'Material':<28} {'uL':>5} {'Act':>6} {'ODT_eth':>8} {'OAV':>9} {'Tier':>10} {'Bar'}")
print(f"  {'-'*80}")

prev_tier = ""
for i, (name, ul, act, odt, oav, tier) in enumerate(results):
    if tier != prev_tier:
        print()
        prev_tier = tier
    
    bar_len = min(40, int(oav / 25))
    bar = "#" * bar_len + "-" * (40 - bar_len)
    print(f"  {i+1:2d} {name:<28} {ul:>5} {act:>6.1f} {odt:>8.3f} {oav:>9.0f} {tier:>10} {bar}")

# Section totals — match 6-stage formula
sec_top = [r for r in results if r[0] in ["Bergamot FCF oil Sicilian","Aldehyde C11 undecylenic","Aldehyde C12 MNA","Red Mandarin EO","Cardamom EO"]]
sec_heart = [r for r in results if r[0] in ["Hedione","Hedione HC","Heliotropal","Anisaldehyde","Coumarin","Vanillin","Alpha Irone","Eugenol","DBCA","Phenethyl Alcohol","Geraniol","Damascol","Farnesol"]]
sec_base = [r for r in results if r[0] not in [x[0] for x in sec_top] and r[0] not in [x[0] for x in sec_heart]]

top_oav = sum(r[4] for r in sec_top)
heart_oav = sum(r[4] for r in sec_heart)
base_oav = sum(r[4] for r in sec_base)
total = top_oav + heart_oav + base_oav

print()
print(f"  {'='*80}")
print(f"  TOTAL OAV: {total:,.0f}")
print(f"  TOP: {top_oav:,.0f} ({top_oav/total*100:.0f}%)  |  HEART: {heart_oav:,.0f} ({heart_oav/total*100:.0f}%)  |  BASE: {base_oav:,.0f} ({base_oav/total*100:.0f}%)")
print()
print(f"  TIER DISTRIBUTION:")
for tier_name in ["MEGA", "EXTREME", "DOMINANT", "clear", "weak", "subliminal"]:
    count = len([r for r in results if r[5] == tier_name])
    if count > 0:
        print(f"    {tier_name:>10}: {count} material{'s' if count>1 else ' '}")
print()
print("  KEY CHANGES FROM PREVIOUS VERSION:")
print("    Alpha Irone: 733 uL -> 10 uL (30% stock) — ODT-level whisper, no longer MEGA")
print("    Labdanum Absolute 10%: +100 uL — YSL amber warmth, Rive Gauche DNA")
print("    Eugenol: +24 uL — Opium trace, clove warmth under jingle")
print("    Farnesol: +24 uL — Lily-muguet fixative")
print("    Total concentrate: 11,702 uL -> 11,079 uL")
print()
print("  ODT CORRECTIONS APPLIED:")
print("    Damascol:    0.005 -> 0.05 (damascone alcohol, not damascone ketone)")
print("    DBCA:        0.100 -> 1.50 (gardenia ester, not trace-potent captive)")
print("    C12 MNA:     0.050 -> 0.30 (aldehyde class, not trace-potent)")
