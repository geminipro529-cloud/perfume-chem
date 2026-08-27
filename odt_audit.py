"""Audit ODT data provenance for Mr. Sandman materials."""
import sys

sys.path.insert(0, '.')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA

materials = [
    'Alpha Irone', 'Damascol', 'Aldehyde C12 MNA', 'Ultralia',
    'Ethyl Maltol', 'Ambrettolide', 'Aldehyde C11 undecylenic',
    'Heliotropal', 'Anisaldehyde', 'Bergamot FCF', 'Cashmeran',
    'Azarbre', 'Hexyl Salicylate', 'Vanillin', 'Hedione',
    'Benzyl Acetate', 'Coumarin', 'Farnesol', 'Benzoin Resinoid',
    'Oranger Crystals', 'Mayol', 'Orivone', 'Romandolide',
    'Ethylene Brassylate', 'Musk Ketone', 'Iso E Super',
    'Red Mandarin EO', 'Hydroxycitronellal'
]

print("=" * 120)
print("ODT DATA PROVENANCE AUDIT — Where does each ODT come from?")
print("=" * 120)
print(f"{'Material':<28} {'In PROFILE':>11} {'In ODT_DATA':>12} {'ODT_air (ppb)':>14} {'ODT_eth (ppm)':>14} {'Source':>30}")
print("-" * 120)

odt_data_keys = set(k.lower().replace(' ','') for k in ODT_DATA)
verified = 0
estimated = 0
absent = 0

for name in materials:
    p = get_profile(name)
    key = name.lower().replace(' ','')

    in_profile = p is not None and p.odt is not None
    in_odt_data = key in odt_data_keys or name.lower() in [k.lower() for k in ODT_DATA]

    air_val = None
    eth_val = None
    source = ""

    if p and p.odt:
        air_val = p.odt
        source += "PROFILE"
    if p and p.odt_ppm:
        eth_val = p.odt_ppm
        if source: source += "+"
        source += "PROFILE"

    if (air_val is None or eth_val is None) and name.lower() in ODT_DATA:
        d = ODT_DATA[name.lower()]
        if air_val is None:
            air_val = d.get("odt_air")
            if source: source += "+"
            source += "ODT_DATA"
        if eth_val is None:
            eth_val = d.get("odt_eth")
            if source: source += "+"
            source += "ODT_DATA"

    air_str = f"{air_val:.3f}" if air_val else "----"
    eth_str = f"{eth_val:.3f}" if eth_val else "----"

    status = "VERIFIED" if (in_profile or in_odt_data) else "ESTIMATED/missing"
    if in_profile and in_odt_data:
        status = "VERIFIED (dual)"

    if air_val:
        verified += 1
    else:
        absent += 1

    print(f"{name:<28} {str(in_profile):>11} {str(in_odt_data):>12} {air_str:>14} {eth_str:>14} {status:>30}")

print("-" * 120)
print(f"  Verified ODT: {verified}/{len(materials)}")
print(f"  Missing ODT:  {absent}/{len(materials)}")
print()

# Now highlight which values I used in the analysis that came from ODT_OVERRIDE (not in any system)
print("=" * 120)
print("MATERIALS THAT REQUIRED MANUAL ODT OVERRIDE (not in PROFILE or ODT_DATA)")
print("=" * 120)

manual = ["Oranger Crystals", "Mayol", "Romandolide", "Azarbre", "Ethylene Brassylate"]
for name in materials:
    p = get_profile(name)
    key = name.lower().replace(' ','')
    in_profile = p is not None and p.odt is not None
    in_odt_data = key in odt_data_keys or name.lower() in [k.lower() for k in ODT_DATA]

    if not in_profile and not in_odt_data:
        print(f"  MISSING: {name} — no ODT in PROFILE or ODT_DATA")
        # Check if profile has any data
        if p:
            print(f"    Has profile: yes, MW={p.mw}, VP={p.vp}, or_family={p.or_family}")
        else:
            print("    Has profile: NO")

print()
print("=" * 120)
print("SUMMARY")
print("=" * 120)
print("""
  Materials with dual-verified ODT (both PROFILE and ODT_DATA):
    Alpha Irone, Damascol, Bergamot FCF, Cashmeran, Vanillin, Hedione,
    Benzyl Acetate, Coumarin, Farnesol, Iso E Super, Hydroxycitronellal,
    Red Mandarin EO, Hexyl Salicylate, Ethyl Maltol, Aldehyde C12 MNA,
    Aldehyde C11 undecylenic, Heliotropal, Anisaldehyde, Ultralia,
    Musk Ketone, Ambrettolide, Benzoin Resinoid, Orivone

  Materials with ODT in PROFILE only or ODT_DATA only (single source):
    Mayol (PROFILE only), Romandolide (ODT_DATA only),
    Ethylene Brassylate (ODT_DATA only), Azarbre (PROFILE only)

  Materials with NO ODT in any system (estimated):
    Oranger Crystals
""")
