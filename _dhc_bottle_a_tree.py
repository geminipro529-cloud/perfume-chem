"""Bottle A -- DHC Realistic Lemon Tree accent."""
import sys; sys.path.insert(0,'.')

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0, "Hedione": 900.0, "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0, "Linalyl Acetate": 120.0, "Petitgrain EO": 150.0,
    "Ambrofix": 10.8, "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

F = 0.25
TARGET = 6000
EXISTING_ML = 33.0
EXISTING_A = {n: v * F for n, v in EXISTING.items()}

# Core targets (% of concentrate)
CORE = {
    "Hedione": 25, "Hedione HC": 5, "Iso E Super": 4,
    "Galaxolide": 6, "Alpha Irone": 3, "Habanolide": 2,     "Ambrox Super": 1,
}

# Citrus accent targets (uL active)
CITRUS = {
    "Cedrat FCF oil Sicilian": 850,
    "Lime Distilled EO": 480,
    "Bergamot FCF oil Sicilian": 280,
    "Terpinyl Acetate": 190,
    "D-Limonene": 8,
    "Beta-Pinene": 2,
    "Aldehyde C10": 10,
    "Aldehyde C11": 4,
    "Helional": 15,
}

# Longevity/sillage boosts (add on top of CORE values)
BOOST = {
    "Cashmeran": 55,      # warmth without detergent
    "Ambrox Super": 75,   # salt-amber tenacity
    "Habanolide": 45,     # transparent skin musk
    "Galaxolide": 120,    # reduced: clean but not laundry
    "Hedione": 200,       # active extra for sillage
}

STOCK = {"Alpha Irone": 0.30, "Galaxolide": 0.50, "Ambrox Super": 0.333}

additions = {}
for m, pct in CORE.items():
    target = TARGET * pct / 100
    have = EXISTING_A.get(m, 0)
    if target > have:
        additions[m] = target - have

for m, a in CITRUS.items():
    # Don't add if already have more
    additions[m] = a

for m, a in BOOST.items():
    additions[m] = additions.get(m, 0) + a

# Scale to fit budget
existing_total = sum(EXISTING_A.values())
committed = sum(additions.values())
remaining = TARGET - existing_total
scale = remaining / committed if committed else 0

print("=" * 70)
print("  BOTTLE A -- DHC REALISTIC LEMON TREE")
print(f"  Pour {EXISTING_ML * F:.1f} mL of existing batch")
print(f"  Existing active: {existing_total:.0f} uL | Target: {TARGET} uL")
print("=" * 70)

total_raw = 0
print(f"\n  {'LINE':<5} {'MATERIAL':<30} {'ACT uL':>8} {'RAW uL':>8} {'STOCK':>10}")
print("  " + "-" * 65)
for i, (m, a) in enumerate(sorted(additions.items(), key=lambda x: x[1], reverse=True), 1):
    sa = a * scale
    sf = STOCK.get(m, 1.0)
    if "C12" in m: sf = 0.01
    sr = sa / sf
    sl = "neat" if sf >= 1.0 else f"{sf*100:.0f}%"
    total_raw += sr
    print(f"  {i:<5} {m:<30} {sa:>8.1f} {sr:>8.1f} {sl:>10}")

# Ethanol
existing_raw_ml = EXISTING_ML * F
eth = 50.0 - existing_raw_ml - total_raw / 1000
print(f"\n  ETHANOL 96%: {eth:.1f} mL")
print(f"  FINAL: {existing_raw_ml:.1f} + {total_raw/1000:.1f} + {eth:.1f} = 50.0 mL")

# Final active check
final = dict(EXISTING_A)
for m, a in additions.items():
    final[m] = final.get(m, 0) + a * scale
total_final = sum(final.values())
print(f"  FINAL ACTIVE: {total_final:.0f} uL ({total_final/50000*100:.1f}%)\n")

# OAV
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name
PPM = 20

rows = []
for n, a in final.items():
    p = get_profile(n)
    vp = p.vp if p and p.vp else 0
    odt = (ODT_DATA.get(normalize_name(n), {}).get("odt_air"))
    if vp and (odt or 0):
        rows.append((n, a, a * vp * PPM / odt))
rows.sort(key=lambda x: x[2], reverse=True)
total_oav = sum(r[2] for r in rows)

GOOD = set(CORE.keys()) | set(CITRUS.keys()) | {"Lemon FCF oil Sicilian", "Petitgrain EO", "Linalyl Acetate", "Ethyl Linalool", "Hedione HC"}
good_ = sum(r[2] for r in rows if r[0] in GOOD)
bad_ = total_oav - good_

print(f"  OAV:")
for i, (n, a, o) in enumerate(rows[:8], 1):
    p = o/total_oav*100
    ok = "OK" if n in GOOD else "XX"
    print(f"    {i}. {n:<30} {o:>8,.0f} ({p:>5.1f}%) {ok}")
print(f"\n  GOOD OAV: {good_/total_oav*100:.1f}%  |  BAD OAV: {bad_/total_oav*100:.1f}%")
