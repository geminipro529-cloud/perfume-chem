"""OAV analysis for Mr. Sandman — YSL Edition."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.ifra_safety import IFRA_CAT4_LIMITS

ODT_OVERRIDE = {
    "Olibanum Resinoid 10%": {"odt_eth": 0.2},
    "Siam Benzoin 50%":      {"odt_eth": 10.0},
    "Jasmine Absolute":      {"odt_eth": 0.5},
    "Cardamom EO":           {"odt_eth": 1.0},
    "Hedione HC":            {"odt_eth": 3.0},
    "Dihydrojasmone":        {"odt_eth": 3.0},
    "Dihydro Beta Ionone":   {"odt_eth": 0.5},
    "Cedarwood EO":          {"odt_eth": 3.0},
    "Ebanol":                {"odt_eth": 1.5},
    "Vertofix":              {"odt_eth": 2.0},
    "Javanol":               {"odt_eth": 0.5},
    "Ethyl Safranate":       {"odt_eth": 0.5},
    "Labdanum Absolute":     {"odt_eth": 0.5},
    "Sandalore":             {"odt_eth": 1.0},
}

def get_odt(name):
    """Get ODT — ODT_DATA first (authoritative), profile as fallback."""
    odt_eth = None
    
    # Check ODT_DATA first
    key = name.lower().replace(" ", "")
    for k, v in ODT_DATA.items():
        if k.replace(" ", "") == key:
            odt_eth = v.get("odt_eth")
            break
    
    # Fallback to profile
    if not odt_eth:
        p = get_profile(name)
        if p and p.odt_ppm: odt_eth = p.odt_ppm
    
    # Check overrides
    if name in ODT_OVERRIDE and not odt_eth:
        odt_eth = ODT_OVERRIDE[name].get("odt_eth")
    
    return odt_eth

# YSL Formula: (name, mass_frac_pct, dilution_pct, note)
FORMULA = [
    # TOP
    ("Bergamot FCF oil Sicilian", 5.00, 100, "top"),
    ("Red Mandarin EO",          3.00, 100, "top"),
    ("Aldehyde C11 undecylenic", 0.70, 100, "top"),
    ("Aldehyde C12 MNA",         4.00,   1, "top"),
    ("Cardamom EO",              0.60, 100, "top"),
    # HEART
    ("Hedione",                 18.00, 100, "heart"),
    ("Heliotropal",              6.00, 100, "heart"),
    ("Anisaldehyde",             3.00, 100, "heart"),
    ("Coumarin",                 7.50,  20, "heart"),
    ("Vanillin",                 4.00,  10, "heart"),
    ("Alpha Irone",              8.00,  30, "heart"),
    ("Orivone",                  0.60, 100, "heart"),
    ("Ultralia",                 0.20, 100, "heart"),
    ("Eugenol",                  0.25, 100, "heart"),
    ("DBCA",                     1.50, 100, "heart"),
    ("Phenethyl Alcohol",        1.00, 100, "heart"),
    ("Geraniol",                 0.50, 100, "heart"),
    ("Damascol",                 1.00,  10, "heart"),
    ("Farnesol",                 0.25, 100, "heart"),
    # BASE
    ("Habanolide",               3.00, 100, "base"),
    ("Romandolide",              4.00, 100, "base"),
    ("Ethylene Brassylate",      9.00, 100, "base"),
    ("Musk Ketone",              6.00,  10, "base"),
    ("Ambrettolide",             3.50,  10, "base"),
    ("Exaltolide",               1.00,  10, "base"),
    ("Cashmeran",               10.00,  20, "base"),
    ("Iso E Super",              4.00, 100, "base"),
    ("Azarbre",                  2.00, 100, "base"),
    ("Polysantol",               0.50, 100, "base"),
    ("Vertofix",                 2.00, 100, "base"),
    ("Hexyl Salicylate",         8.00, 100, "base"),
    ("Siam Benzoin 50%",         1.00,  50, "base"),
]

TOTAL_CONC = 13.35  # g concentrate for 50 mL
EDP_CONC = 0.22

print("=" * 120)
print(f"{'MR. SANDMAN — YSL EDITION — OAV ANALYSIS':^120}")
print(f"{'32 materials · 50 mL EDP @ ~22% · Concentrate ~13.35 g':^120}")
print("=" * 120)
print()

# Compute OAV
results = []
total_oav = 0
section_totals = {"top": 0, "heart": 0, "base": 0}
section_counts = {"top": 0, "heart": 0, "base": 0}

for name, mass_frac, dilution, note in FORMULA:
    active_pct = mass_frac * (dilution / 100.0)
    conc_ppm = active_pct * 10000  # % to ppm in concentrate
    edp_ppm = conc_ppm * EDP_CONC
    
    odt_eth = get_odt(name)
    
    if odt_eth and odt_eth > 0:
        oav_val = edp_ppm / odt_eth
    else:
        oav_val = 0
    
    total_oav += oav_val
    section_totals[note] += oav_val
    section_counts[note] += 1
    
    if oav_val == 0:
        percept = "NO ODT"
    elif oav_val < 1:
        percept = "subliminal"
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
    
    results.append((name, note, mass_frac, active_pct, conc_ppm, edp_ppm, odt_eth, oav_val, percept))

# Print by section
for section_name, section_label in [("top", "TOP — YSL Aldehydic Opening"), 
                                       ("heart", "HEART — Aldehydes First, Jingle Second"),
                                       ("base", "BASE — Clean White Musk")]:
    print(f"\n{'—'*60}")
    print(f"  {section_label} ({section_counts[section_name]} materials, OAV sum = {section_totals[section_name]:,.0f})")
    print("-" * 120)
    print(f"  {'Material':<28} {'MFr%':>7} {'Act%':>7} {'C_ppm':>9} {'EDP_ppm':>9} {'ODT_eth':>9} {'OAV':>10} {'Percept':>12}")
    print("-" * 120)
    
    for r in results:
        if r[1] == section_name:
            name, note, mfr, act_pct, conc_ppm, edp_ppm, odt_eth, oav_val, percept = r
            odt_s = f"{odt_eth:.3f}" if odt_eth else "N/A"
            print(f"  {name:<26} {mfr:>7.2f} {act_pct:>7.3f} {conc_ppm:>9.0f} {edp_ppm:>9.0f} {odt_s:>9} {oav_val:>10.0f} {percept:>12}")

print(f"\n{'-'*120}")
print(f"  TOTAL OAV: {total_oav:>12,.0f}")
print(f"  Section split: TOP={section_totals['top']:,.0f} ({section_totals['top']/total_oav*100:.0f}%)  "
      f"HEART={section_totals['heart']:,.0f} ({section_totals['heart']/total_oav*100:.0f}%)  "
      f"BASE={section_totals['base']:,.0f} ({section_totals['base']/total_oav*100:.0f}%)")

print()
print("=" * 120)
print("OAV LEADERBOARD - Top 12")
print("=" * 120)
leaderboard = sorted(results, key=lambda r: -r[7])
for i, r in enumerate(leaderboard[:12]):
    name, note, mfr, act_pct, conc_ppm, edp_ppm, odt_eth, oav_val, percept = r
    odt_s = f"{odt_eth:.3f}" if odt_eth else "N/A"
    bar = "#" * min(30, int(oav_val / 1000))
    print(f"  {i+1:2d}. {name:<26} OAV={oav_val:>12,.0f}  {odt_s:>8}  {bar}  ({note})")

print()
print("=" * 120)
print("BELOW THRESHOLD (OAV < 5)")
print("=" * 120)
below = [r for r in results if r[7] > 0 and r[7] < 5]
if below:
    for r in below:
        print(f"  {r[0]:<28} OAV={r[7]:.1f}  {r[8]}")
else:
    print("  None — all materials above OAV = 5")

print()
print("=" * 120)
print("IFRA CHECK")
print("=" * 120)
ifra_issues = 0
for name, mass_frac, dilution, note in FORMULA:
    limit = IFRA_CAT4_LIMITS.get(name)
    if limit:
        edp_pct = (mass_frac * dilution / 100) / 100 * EDP_CONC * 100
        if edp_pct > limit:
            print(f"  VIOLATION: {name:<28} EDP={edp_pct:.3f}% > IFRA={limit}%")
            ifra_issues += 1
        elif edp_pct > limit * 0.8:
            print(f"  APPROACHING: {name:<26} EDP={edp_pct:.3f}% (80% of limit {limit}%)")

if ifra_issues == 0:
    print("  All 32 materials within IFRA Cat4 limits.")
print()
print("OAV SCALE: <1=subliminal  1-5=weak  5-50=clear  50-500=DOMINANT  500-5000=EXTREME  >5000=MEGA")
