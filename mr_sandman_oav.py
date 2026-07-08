"""Compute OAV profile for Mr. Sandman formula."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.perception.oav import oav

# Mr. Sandman formula: material -> active_frac (% w/w in concentrate)
FORMULA = {
    # TOP
    "Bergamot FCF":               {"active": 5.000, "note": "top"},
    "Red Mandarin EO":            {"active": 3.000, "note": "top"},
    "Aldehyde C11 undecylenic":   {"active": 0.300, "note": "top"},
    "Aldehyde C12 MNA":           {"active": 0.025, "note": "top"},
    # HEART
    "Hedione":                    {"active": 15.000, "note": "heart"},
    "Heliotropal":                {"active": 6.000, "note": "heart"},
    "Anisaldehyde":               {"active": 3.000, "note": "heart"},
    "Alpha Irone":                {"active": 2.400, "note": "heart"},
    "Ultralia":                   {"active": 0.200, "note": "heart"},
    "Mayol":                      {"active": 1.500, "note": "heart"},
    "Hydroxycitronellal":         {"active": 1.000, "note": "heart"},
    "Damascol":                   {"active": 0.200, "note": "heart"},
    "Ethyl Maltol":               {"active": 0.250, "note": "heart"},
    "Vanillin":                   {"active": 0.400, "note": "heart"},
    "Orivone":                    {"active": 0.600, "note": "heart"},
    "Farnesol":                   {"active": 0.250, "note": "heart"},
    "Coumarin":                   {"active": 1.500, "note": "heart"},
    # BASE
    "Hexyl Salicylate":           {"active": 8.000, "note": "base"},
    "Cashmeran":                  {"active": 2.000, "note": "base"},
    "Ethylene Brassylate":        {"active": 9.000, "note": "base"},
    "Musk Ketone":                {"active": 0.400, "note": "base"},
    "Ambrettolide":               {"active": 0.350, "note": "base"},
    "Romandolide":                {"active": 3.000, "note": "base"},
    "Iso E Super":                {"active": 4.000, "note": "base"},
    "Azarbre":                    {"active": 2.000, "note": "base"},
    "Benzoin Resinoid":           {"active": 0.500, "note": "base"},
}

# ODT lookup mapping (formula name -> ODT_DATA key)
ODT_MAP = {
    "Bergamot FCF": "bergamot",
    "Red Mandarin EO": "limonene",
    "Aldehyde C11 undecylenic": "aldehyde c11 undecylenic",
    "Aldehyde C12 MNA": "aldehyde c12 mna",
    "Hedione": "hedione",
    "Heliotropal": "heliotropin",
    "Anisaldehyde": "anisaldehyde",
    "Alpha Irone": "alpha irone",
    "Ultralia": "ultralia",
    "Mayol": "mayol",
    "Hydroxycitronellal": "hydroxycitronellal",
    "Damascol": "damascol",
    "Ethyl Maltol": "ethyl maltol",
    "Vanillin": "vanillin",
    "Orivone": "orivone",
    "Farnesol": "farnesol",
    "Coumarin": "coumarin",
    "Hexyl Salicylate": "hexyl salicylate",
    "Cashmeran": "cashmeran",
    "Ethylene Brassylate": "ethylene brassylate",
    "Musk Ketone": "musk ketone",
    "Ambrettolide": "ambrettolide",
    "Romandolide": "romandolide",
    "Iso E Super": "iso e super",
    "Azarbre": "azarbre",
    "Benzoin Resinoid": "benzoin resinoid",
}

print("=" * 110)
print(f"{'MR. SANDMAN — OAV PROFILE (concentrate, % w/w)':^110}")
print("=" * 110)
print()
print(f"{'#':>2} {'Material':<28} {'Note':>5} {'Active%':>8} {'ODT_ppm':>9} {'ODT_ppb':>9} "
      f"{'Conc_ppm':>9} {'OAV':>10} {'Percept':>10} {'Character'}")
print("-" * 110)

total_oav = 0
section = ""
idx = 0
results = []

for name, data in FORMULA.items():
    idx += 1
    note = data["note"]
    active_pct = data["active"]
    conc_ppm = active_pct * 10000  # % to ppm w/w
    
    # Get ODT
    profile = get_profile(name)
    odt_eth = profile.odt_ppm if profile and profile.odt_ppm else None
    odt_air = profile.odt if profile and profile.odt else None
    
    # Try ODT_DATA
    odt_key = ODT_MAP.get(name, name.lower())
    if odt_eth is None and odt_key in ODT_DATA:
        odt_eth = ODT_DATA[odt_key].get("odt_eth")
    if odt_air is None:
        for k, v in ODT_DATA.items():
            if k == odt_key or name.lower().replace(" ", "") == k.replace(" ", ""):
                odt_air = v.get("odt_air")
                break
    
    # Compute OAV
    if odt_eth and odt_eth > 0:
        oav_val = conc_ppm / odt_eth
        if oav_val < 1:
            percept = "SUBLIMINAL"
        elif oav_val < 5:
            percept = "weak"
        elif oav_val < 50:
            percept = "clear"
        elif oav_val < 500:
            percept = "DOMINANT"
        else:
            percept = "EXTREME"
    elif odt_air and odt_air > 0:
        oav_val = conc_ppm / (odt_air / 1000)  # ppb to ppm
        if oav_val < 1:
            percept = "~subliminal"
        elif oav_val < 5:
            percept = "~weak"
        elif oav_val < 50:
            percept = "~clear"
        elif oav_val < 500:
            percept = "~DOMINANT"
        else:
            percept = "~EXTREME"
    else:
        oav_val = 0
        percept = "NO ODT"
    
    total_oav += oav_val
    
    char = ""
    if profile:
        tags = profile.character_tags(threshold=4.0)
        char = ", ".join(tags[:3]) if tags else profile.dominant_character()
    
    odt_eth_str = f"{odt_eth:.3f}" if odt_eth else "N/A"
    odt_air_str = f"{odt_air:.1f}" if odt_air else "N/A"
    
    results.append((idx, name, note, active_pct, odt_eth, odt_air, conc_ppm, oav_val, percept, char))

# Print with section headers
prev_note = ""
for r in results:
    idx, name, note, active_pct, odt_eth, odt_air, conc_ppm, oav_val, percept, char = r
    if note != prev_note:
        print()
        print(f"  --- {note.upper()} ---")
        prev_note = note
    
    odt_eth_str = f"{odt_eth:.3f}" if odt_eth else "N/A"
    odt_air_str = f"{odt_air:.1f}" if odt_air else "N/A"
    print(f"{idx:2d} {name:<28} {note:>5} {active_pct:>8.3f} {odt_eth_str:>9} {odt_air_str:>9} "
          f"{conc_ppm:>9.0f} {oav_val:>10.1f} {percept:>10} {char}")

print()
print("-" * 110)
print(f"{'TOTAL':>28} {'':>5} {'':>8} {'':>9} {'':>9} {'':>9} {total_oav:>10.1f}")
print()

# Section summaries
for section_name in ["top", "heart", "base"]:
    section_oav = sum(r[7] for r in results if r[2] == section_name)
    section_pct = sum(r[3] for r in results if r[2] == section_name)
    print(f"  {section_name.upper():>5}: {section_pct:>7.2f}% active  |  OAV sum = {section_oav:>12,.1f}")

print()
print("=" * 110)
print("OAV INTERPRETATION:")
print("  OAV < 1     = Below detection threshold (subliminal or imperceptible)")
print("  OAV 1-5     = Weakly perceptible (trace contribution)")
print("  OAV 5-50    = Clearly perceptible (functional role)")
print("  OAV 50-500  = Dominant (leads the composition)")
print("  OAV > 500   = Extreme (overpowering, consider reduction)")
print()
print("  '~' prefix = OAV estimated from air ODT (ppb) converted to ppm")
print("  Concentrate ppm = active_frac% x 10,000 (for 23.3% w/v EDP)")
print("  Actual EDP ppm = concentrate ppm x 0.233")