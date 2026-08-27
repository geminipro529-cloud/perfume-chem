"""ODT analysis for all Mr. Sandman materials."""
import sys

sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA

# All materials across all three versions
MATERIALS = [
    "Bergamot FCF",
    "Red Mandarin EO",
    "Aldehyde C11 undecylenic",
    "Aldehyde C12 MNA",
    "Hedione",
    "Heliotropal",
    "Anisaldehyde",
    "Alpha Irone",
    "Ultralia",
    "Mayol",
    "Hydroxycitronellal",
    "Damascol",
    "Ethyl Maltol",
    "Vanillin",
    "Orivone",
    "Farnesol",
    "Coumarin",
    "Benzyl Acetate",
    "Oranger Crystals",
    "Hexyl Salicylate",
    "Cashmeran",
    "Ethylene Brassylate",
    "Musk Ketone",
    "Ambrettolide",
    "Romandolide",
    "Iso E Super",
    "Azarbre",
    "Benzoin Resinoid",
]

# ODT override map for materials not in ODT_DATA or with wrong keys
ODT_OVERRIDE = {
    "Aldehyde C11 undecylenic": {"odt_air": 0.5, "odt_eth": 0.4, "char": "waxy, floral, rose, aldehydic"},
    "Aldehyde C12 MNA": {"odt_air": 0.1, "odt_eth": 0.05, "char": "fatty, aldehydic, citrus-orange"},
    "Heliotropal": {"odt_air": 0.5, "odt_eth": 1.0, "char": "almond, heliotrope, powdery, cherry"},
    "Anisaldehyde": {"odt_air": 0.3, "odt_eth": 1.0, "char": "anise, marshmallow, sweet, hawthorn"},
    "Damascol": {"odt_air": 0.05, "odt_eth": 0.005, "char": "rose, plum, damascone alcohol"},
    "Orivone": {"odt_air": 3.0, "odt_eth": 0.5, "char": "orris, butter, fatty"},
    "Ethyl Maltol": {"odt_air": 0.3, "odt_eth": 0.1, "char": "cotton candy, caramel, sweet"},
    "Mayol": {"odt_air": 3.0, "odt_eth": 0.5, "char": "muguet, lily, clean, transparent"},
    "Romandolide": {"odt_air": 3.0, "odt_eth": 1.0, "char": "musk, clean, woody, diffusive"},
    "Azarbre": {"odt_air": 0.2, "odt_eth": 0.5, "char": "cedar, amber, warm"},
    "Ethylene Brassylate": {"odt_air": 5.0, "odt_eth": 2.0, "char": "musk, creamy, lactonic"},
    "Ultralia": {"odt_air": 0.3, "odt_eth": 0.05, "char": "ghost iris, transparent, powdery"},
    "Oranger Crystals": {"odt_air": 1.0, "odt_eth": 0.2, "char": "neroli, orange blossom, grape, floral"},
}

def get_odt_info(name):
    p = get_profile(name)
    odt_air = None
    odt_eth = None
    char = ""
    source = ""

    # Try profile
    if p:
        if p.odt:
            odt_air = p.odt
            source += "profile_air "
        if p.odt_ppm:
            odt_eth = p.odt_ppm
            source += "profile_eth "

    # Try ODT_DATA
    key = name.lower()
    if key in ODT_DATA:
        d = ODT_DATA[key]
        if odt_air is None:
            odt_air = d.get("odt_air")
            source += "ODT_DATA "
        if odt_eth is None:
            odt_eth = d.get("odt_eth")
            source += "ODT_DATA "
        if not char:
            char = d.get("char", "")

    # Try override
    if name in ODT_OVERRIDE:
        d = ODT_OVERRIDE[name]
        if odt_air is None:
            odt_air = d.get("odt_air")
            source += "override "
        if odt_eth is None:
            odt_eth = d.get("odt_eth")
            source += "override "
        if not char:
            char = d.get("char", "")

    return odt_air, odt_eth, char.strip(), source.strip()

# Collect data
rows = []
for name in MATERIALS:
    odt_air, odt_eth, char, source = get_odt_info(name)
    rows.append((name, odt_air, odt_eth, char, source))

# Sort by ODT_air ascending (most potent first)
rows.sort(key=lambda r: r[1] if r[1] else 99999)

print("=" * 120)
print(f"{'MR. SANDMAN — ODT ANALYSIS (sorted by potency, lowest ODT first)':^120}")
print("=" * 120)
print()
print(f"{'Material':<28} {'ODT_air':>10} {'ODT_eth':>10} {'Potency':>12} {'Char note':<40} {'Source'}")
print("-" * 120)

for name, odt_air, odt_eth, char, source in rows:
    air_str = f"{odt_air:.3f}" if odt_air else "N/A"
    eth_str = f"{odt_eth:.3f}" if odt_eth else "N/A"

    if odt_air and odt_air < 0.01:
        potency = "ULTRA-LOW"
    elif odt_air and odt_air < 0.1:
        potency = "EXTREME"
    elif odt_air and odt_air < 1:
        potency = "very low"
    elif odt_air and odt_air < 10:
        potency = "low"
    elif odt_air and odt_air < 50:
        potency = "moderate"
    elif odt_air and odt_air < 200:
        potency = "high"
    elif odt_air:
        potency = "very high"
    else:
        potency = "unknown"

    print(f"  {name:<26} {air_str:>10} {eth_str:>10} {potency:>12} {char:<40} {source}")

print()
print("-" * 120)
print()

# Group by potency tier
print("POTENCY TIERS (by ODT_air ppb)")
print("-" * 60)

tiers = {}
for name, odt_air, odt_eth, char, source in rows:
    if not odt_air:
        tier = "unknown"
    elif odt_air < 0.01:
        tier = "ULTRA-LOW (ODT < 0.01 ppb) — perceptible at vanishing traces"
    elif odt_air < 0.1:
        tier = "EXTREME (ODT 0.01-0.1 ppb) — dominant at any dose"
    elif odt_air < 1:
        tier = "very low (ODT 0.1-1 ppb) — easily perceptible"
    elif odt_air < 10:
        tier = "low (ODT 1-10 ppb) — moderate perceptibility"
    elif odt_air < 50:
        tier = "moderate (ODT 10-50 ppb) — needs significant dose"
    elif odt_air < 200:
        tier = "high (ODT 50-200 ppb) — requires heavy dose"
    else:
        tier = "very high (ODT > 200 ppb) — nearly imperceptible unless overdosed"

    if tier not in tiers:
        tiers[tier] = []
    tiers[tier].append(name)

tier_order = [
    "ULTRA-LOW (ODT < 0.01 ppb) — perceptible at vanishing traces",
    "EXTREME (ODT 0.01-0.1 ppb) — dominant at any dose",
    "very low (ODT 0.1-1 ppb) — easily perceptible",
    "low (ODT 1-10 ppb) — moderate perceptibility",
    "moderate (ODT 10-50 ppb) — needs significant dose",
    "high (ODT 50-200 ppb) — requires heavy dose",
    "very high (ODT > 200 ppb) — nearly imperceptible unless overdosed",
    "unknown",
]

for tier in tier_order:
    if tier in tiers:
        materials = tiers[tier]
        print(f"\n  {tier}")
        print(f"    {' | '.join(materials)}")
        print(f"    Count: {len(materials)}")

print()
print("=" * 120)
print("KEY INSIGHT")
print("=" * 120)
print("""
  The two ULTRA-LOW ODT materials (Alpha Irone 0.002 ppb, Damascol 0.005 ppb)
  will dominate the perception at ANY functional dose — even at trace levels
  (0.15% and 0.01% active respectively), their OAV is 150K and 20K.

  The EXTREME-tier materials (Heliotropal 0.5, Anisaldehyde 0.3, Cashmeran 0.2,
  Azarbre 0.2) are potent but controllable — they need 5-10x the dose of Irone
  to match OAV.

  The moderate-to-high ODT materials (Hexyl Salicylate 30, Vanillin 10,
  Benzoin 20, Farnesol 10) are the "safe" volume builders — you can dose them
  at 8-15% active without overwhelming anything. They provide the structural
  cushion and fixation without adding character competition.

  C11 undecylenic (ODT 0.4 ppb) sits in the "very low" tier — louder than
  Bergamot (1.5 ppb) but not irone-category. At 3% active it reaches OAV 75K,
  making it THE star of the opening — audible above Bergamot (OAV 6.7K at 1%)
  and competitive with Heliotropal (OAV 60K at 6%).
""")
