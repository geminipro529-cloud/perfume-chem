"""OAV analysis for Jasmin d'Orris Collab — ALL 45 materials."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA

# Formula: (material, µL, dilution_pct, note_category)
# Dilution: 100 = neat, 10 = 10%, 1 = 1%, etc.
FORMULA = [
    # STEP 1 — BASE (sorted by µL)
    ("Iso E Super",               800, 100, "base"),
    ("Cedarwood EO",              500, 100, "base"),
    ("Benzoin Resinoid",          300,  50, "base"),
    ("Romandolide",               250, 100, "base"),
    ("Olibanum Resinoid",         200, 100, "base"),
    ("Ethylene Brassylate",       200, 100, "base"),
    ("Ebanol",                    180, 100, "base"),
    ("Musk Ketone",               180,  10, "base"),
    ("Cashmeran",                 120, 100, "base"),
    ("Sandalore",                 120, 100, "base"),
    ("Patchouli EO",              100, 100, "base"),
    ("Labdanum Absolute",         100,  10, "base"),
    ("Vertofix",                   80, 100, "base"),
    ("Azarbre",                    60, 100, "base"),
    ("Kephalis",                   50, 100, "base"),
    ("Javanol",                    40, 100, "base"),

    # STEP 2 — HEART
    # JASMINE
    ("Hedione",                  1200, 100, "heart"),
    ("Jasmine Absolute",          600,  10, "heart"),
    ("Hedione HC",                600, 100, "heart"),
    ("Benzyl Acetate",            200, 100, "heart"),
    ("cis-Jasmone",               150, 100, "heart"),
    ("Dihydrojasmone",            120, 100, "heart"),
    ("Gamma Undecalactone",       100, 100, "heart"),
    ("Paradisamide",               30,  10, "heart"),
    ("Indole",                     25,  10, "heart"),
    # ORRIS
    ("Myristic Acid Powder",      600,   1, "heart"),
    ("Orivone",                   180, 100, "heart"),
    ("Dihydro Beta Ionone",       150, 100, "heart"),
    ("Alpha Isomethyl Ionone",    120, 100, "heart"),
    ("Alpha Ionone",              100, 100, "heart"),
    ("Allyl Ionone",               40, 100, "heart"),
    ("Alpha Irone",                25,  30, "heart"),
    ("Ultralia",                   20, 100, "heart"),
    # ROSE
    ("Phenethyl Alcohol",         100, 100, "heart"),
    ("Geraniol",                   60, 100, "heart"),
    ("Rose Oxide",                 10,   1, "heart"),
    ("Alpha Damascone",             4,  10, "heart"),

    # STEP 3 — STRUCTURE
    ("Benzyl Benzoate",           400, 100, "structure"),
    ("Benzyl Salicylate",         250, 100, "structure"),
    ("Hexyl Salicylate",          180, 100, "structure"),

    # STEP 4 — TOP
    ("Bergamot FCF oil Sicilian", 300, 100, "top"),
    ("Petitgrain EO",             100, 100, "top"),
    ("Cardamom EO",                80, 100, "top"),
    ("D-Limonene",                 60, 100, "top"),
    ("Ethyl Safranate",            15, 100, "top"),
]

TOTAL_CONCENTRATE_UL = 9489
EDP_CONC_PCT = 29.7

# ODT overrides for materials not in system
ODT_OVERRIDE = {
    "Myristic Acid Powder":        {"odt_eth": 10.0, "odt_air": 50.0, "char": "fatty, waxy, soapy (near-odorless)"},
    "Olibanum Resinoid":           {"odt_eth": 2.0,  "odt_air": 10.0, "char": "incense, resinous, citrus-pine"},
    "Labdanum Absolute":           {"odt_eth": 0.5,  "odt_air": 2.0,  "char": "amber, animalic, leather"},
    "Jasmine Absolute":            {"odt_eth": 0.5,  "odt_air": 2.0,  "char": "jasmine, narcotic, indolic"},
    "Cardamom EO":                 {"odt_eth": 1.0,  "odt_air": 5.0,  "char": "spicy, camphoraceous, green"},
    "Petitgrain EO":               {"odt_eth": 1.0,  "odt_air": 5.0,  "char": "green, woody, citrus-floral"},
    "Hedione HC":                  {"odt_eth": 3.0,  "odt_air": 20.0, "char": "jasmine, radiance (high-cis)"},
    "Paradisamide":                {"odt_eth": 0.5,  "odt_air": 3.0,  "char": "tropical, guava, passionfruit"},
    "Dihydrojasmone":              {"odt_eth": 3.0,  "odt_air": 15.0, "char": "jasmine, fruity-green, oily"},
    "Dihydro Beta Ionone":         {"odt_eth": 0.5,  "odt_air": 3.0,  "char": "woody, violet, orris"},
    "Cedarwood EO":                {"odt_eth": 3.0,  "odt_air": 15.0, "char": "pencil, dry wood"},
    "Ebanol":                      {"odt_eth": 1.5,  "odt_air": 8.0,  "char": "sandalwood, creamy, milky"},
    "Vertofix":                    {"odt_eth": 2.0,  "odt_air": 10.0, "char": "woody, vetiver, ambery"},
    "Sandalore":                   {"odt_eth": 1.0,  "odt_air": 5.0,  "char": "sandalwood, creamy, warm"},
    "Javanol":                     {"odt_eth": 0.5,  "odt_air": 3.0,  "char": "sandalwood, dry, intimate"},
    "Allyl Ionone":                {"odt_eth": 0.5,  "odt_air": 3.0,  "char": "green, woody, violet"},
    "Ethyl Safranate":             {"odt_eth": 0.5,  "odt_air": 3.0,  "char": "saffron, spicy, leather"},
}

def get_odt(name):
    """Get ODT from system data or override."""
    p = get_profile(name)
    odt_eth = None
    odt_air = None
    char = ""
    source = ""

    if p:
        if p.odt_ppm: 
            odt_eth = p.odt_ppm
            source += "PROFILE "
        if p.odt: 
            odt_air = p.odt
            source += "PROFILE "

    key = name.lower().replace(" ", "")
    odt_data = None
    for k, v in ODT_DATA.items():
        if k.replace(" ", "") == key or k == name.lower():
            odt_data = v
            break

    if odt_data:
        if odt_eth is None: 
            odt_eth = odt_data.get("odt_eth")
            source += "ODT "
        if odt_air is None: 
            odt_air = odt_data.get("odt_air")
            source += "ODT "
        if not char:
            char = odt_data.get("char", "")

    if name in ODT_OVERRIDE:
        d = ODT_OVERRIDE[name]
        if odt_eth is None: 
            odt_eth = d.get("odt_eth")
            source += "OVERRIDE "
        if odt_air is None: 
            odt_air = d.get("odt_air")
            source += "OVERRIDE "
        if not char:
            char = d.get("char", "")

    return odt_eth, odt_air, char.strip(), source.strip()

# Compute OAV for each material
print("=" * 125)
print(f"{'JASMIN D\'ORRIS COLLAB — OAV ANALYSIS (45 materials, 29.7% EdP)':^125}")
print("=" * 125)
print()
print(f"{'#':>3} {'Material':<28} {'uL':>6} {'Dil%':>5} {'Act_uL':>7} {'C_c_ppm':>9} {'C_EDP_ppm':>9} {'ODT_eth':>9} {'OAV':>9} {'Percept':>10} {'ODT_air':>8} {'Character'}")
print("-" * 125)

prev_note = ""
total_oav = 0
total_active_ul = 0
section_data = {"base": {"oav": 0, "ul": 0, "act": 0}, "heart": {"oav": 0, "ul": 0, "act": 0}, 
                "structure": {"oav": 0, "ul": 0, "act": 0}, "top": {"oav": 0, "ul": 0, "act": 0}}
idx = 0
results = []

for name, ul, dilution, note in FORMULA:
    idx += 1
    active_ul = ul * (dilution / 100.0)
    conc_ppm = (active_ul / TOTAL_CONCENTRATE_UL) * 1_000_000
    edp_ppm = conc_ppm * (EDP_CONC_PCT / 100.0)
    
    total_active_ul += active_ul
    odt_eth, odt_air, char, source = get_odt(name)
    
    if odt_eth and odt_eth > 0:
        oav_val = edp_ppm / odt_eth
        oav_type = "EDP"
    elif odt_air and odt_air > 0:
        oav_val = edp_ppm / (odt_air / 1000)
        oav_type = "air→ppm"
    else:
        oav_val = 0
        oav_type = "NO ODT"
    
    total_oav += oav_val
    section_data[note]["oav"] += oav_val
    section_data[note]["ul"] += ul
    section_data[note]["act"] += active_ul
    
    if oav_val == 0:
        percept = "NO ODT"
    elif oav_val < 1:
        percept = "SUBLIMINAL"
    elif oav_val < 5:
        percept = "weak"
    elif oav_val < 50:
        percept = "clear"
    elif oav_val < 500:
        percept = "DOMINANT"
    elif oav_val < 5000:
        percept = "EXTREME"
    else:
        percept = "MEGA"
    
    results.append((idx, name, note, ul, dilution, active_ul, conc_ppm, edp_ppm, odt_eth, oav_val, percept, odt_air, char, source))

# Print by section
for section_name, section_label in [("base", "STEP 1 — BASE"), ("heart", "STEP 2 — HEART"), 
                                       ("structure", "STEP 3 — STRUCTURE"), ("top", "STEP 4 — TOP")]:
    section_results = [r for r in results if r[2] == section_name]
    print(f"\n  --- {section_label} ---")
    print()
    
    for r in section_results:
        idx, name, note, ul, dil, act_ul, conc_ppm, edp_ppm, odt_eth, oav_val, percept, odt_air, char, source = r
        odt_eth_s = f"{odt_eth:.3f}" if odt_eth else "N/A"
        odt_air_s = f"{odt_air:.1f}" if odt_air else "N/A"
        print(f"{idx:3d} {name:<27} {ul:>6} {dil:>5} {act_ul:>7.1f} {conc_ppm:>9.0f} {edp_ppm:>9.0f} {odt_eth_s:>9} {oav_val:>9.1f} {percept:>10} {odt_air_s:>8} {char[:50]}")

print()
print("-" * 125)
print(f"  TOTAL: {total_active_ul:>7.1f} active uL in {TOTAL_CONCENTRATE_UL} uL concentrate ({total_active_ul/TOTAL_CONCENTRATE_UL*100:.1f}% active)")
print(f"  Sum OAV: {total_oav:>12,.0f}")
print()
print("  Section breakdown:")
for s, l in [("top","TOP"),("heart","HEART"),("structure","STRUCTURE"),("base","BASE")]:
    d = section_data[s]
    print(f"    {l:>9}: uL={d['ul']:>5.0f}  act_uL={d['act']:>7.1f}  OAV={d['oav']:>12,.0f}")

print()
print("=" * 125)
print("OAV LEADERBOARD (top 15)")
print("=" * 125)
leaderboard = sorted(results, key=lambda r: r[9], reverse=True)
for i, r in enumerate(leaderboard[:15]):
    idx, name, note, ul, dil, act_ul, conc_ppm, edp_ppm, odt_eth, oav_val, percept, odt_air, char, source = r
    odt_eth_s = f"{odt_eth:.3f}" if odt_eth else "N/A"
    print(f"  {i+1:2d}. {name:<28} OAV={oav_val:>10,.1f}  ODT_eth={odt_eth_s:>8}  {percept}  ({note})")

print()
print("=" * 125)
print("BELOW THRESHOLD (OAV < 1) — subliminal or imperceptible")
print("=" * 125)
below = [r for r in results if r[9] > 0 and r[9] < 1]
if below:
    for r in below:
        print(f"  {r[1]:<28} OAV={r[9]:.2f}  {r[13]}")
else:
    print("  None — all materials are above OAV = 1")
    
print()
print("OAV SCALE:")
print("  < 1    = Subliminal (below perception threshold)")
print("  1-5    = Weakly perceptible (trace)")
print("  5-50   = Clearly perceptible (functional)")
print("  50-500 = Dominant (leads the composition)")
print("  > 500  = Extreme (overpowering)")
print()
print(f"  Concentrate: {TOTAL_CONCENTRATE_UL} uL")
print(f"  EDP strength: {EDP_CONC_PCT}%")
print(f"  Note: ODT_eth checked against PROFILE → ODT_DATA → OVERRIDE in that order")
