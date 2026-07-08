"""DHC 100mL Correction -- CEDRAT FCF PRIMARY LEMON SOURCE.

Strategy: Replace most Lemon FCF additions with Cedrat FCF oil Sicilian.
Cedrat = citron (Citrus medica) -- high citral, low limonene = real lemon pith, no candy.
Existing 4,200 uL Lemon FCF stays -- Cedrat adds the missing sharp/pithy character.
"""
import sys
sys.path.insert(0, '.')
from engine.odor_thresholds import ODT_DATA
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name

PPM = 20.0

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0, "Hedione": 900.0, "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0, "Linalyl Acetate": 120.0, "Petitgrain EO": 150.0,
    "Ambrofix": 10.8,
    "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

# DHC A additions -- Cedrat FCF replaces Lemon FCF as primary lemon
ADDITIONS = {
    # CEDRAT PRIMARY LEMON -- high citral, low limonene, pithy-sharp
    "Cedrat FCF oil Sicilian": 1700.0,
    # Lemon FCF remains second citrus (user already has 4200 uL)
    "Lemon FCF oil Sicilian": 400.0,
    # Anti-candy support
    "Lime Distilled EO": 300.0,
    "Aldehyde C10 (1%)": 8.0,
    "Citral": 3.0,
    # DHC core (unchanged)
    "Hedione": 500.0,
    "Dihydromyrcenol": 500.0,
    "Galaxolide": 400.0,
    "Habanolide": 200.0,
    "Ambrofix": 200.0,
    "Alpha Irone": 145.0,
    "Ethyl Linalool": 120.0,
    "Linalyl Acetate": 100.0,
}

STOCK = {"Aldehyde C10 (1%)": 0.01, "Alpha Irone": 0.30, "Galaxolide": 0.50, "Ambrofix": 0.30}

existing_total = sum(EXISTING.values())
target_active = 12000.0
add_total = sum(ADDITIONS.values())
scale = (target_active - existing_total) / add_total if add_total else 0

# Stock helper
def stock_frac(name):
    for k, v in STOCK.items():
        if k in name: return v
    return 1.0

print("=" * 90)
print("  DHC 100mL CORRECTION -- CEDRAT FCF PRIMARY LEMON")
print("=" * 90)
print(f"\n  Existing active:   {existing_total:.0f} uL")
print(f"  Target active:     {target_active:.0f} uL  (12% of 100mL)")
print(f"  Additions budget:  {target_active - existing_total:.0f} uL active")
print(f"  Scale factor:      {scale:.3f}")

print(f"\n  {'MATERIAL':<30} {'ACTIVE':>8} {'RAW':>8} {'STOCK':>10}")
print("  " + "-" * 60)
total_raw = 0.0
for mat, active in sorted(ADDITIONS.items(), key=lambda x: x[1], reverse=True):
    a = active * scale
    sf = stock_frac(mat)
    r = a / sf
    label = f"{sf*100:.0f}%" if sf < 1.0 else "neat"
    total_raw += r
    print(f"  {mat:<30} {a:>8.1f} {r:>8.1f} {label:>10}")

ethanol = 100.0 - 31.4 - total_raw/1000
print("  " + "-" * 60)
print(f"  {'TOTAL STOCK':<30} {sum(ADDITIONS.values())*scale:>8.1f} {total_raw:>8.1f}")
print(f"\n  ETHANOL 96% TO ADD:  {ethanol:.1f} mL")
print(f"  FINAL: 31.4 + {total_raw/1000:.1f} + {ethanol:.1f} = 100.0 mL")

# OAV analysis
CORRECTED = dict(EXISTING)
for mat, active in ADDITIONS.items():
    CORRECTED[mat] = CORRECTED.get(mat, 0.0) + active * scale

def get_vp_odt(name):
    p = get_profile(name)
    return (p.vp if p and p.vp else 0), (ODT_DATA.get(normalize_name(name), {}).get("odt_air") or 0)

rows = []
for n, a in CORRECTED.items():
    vp, odt = get_vp_odt(n)
    if vp and odt:
        rows.append((n, a, vp, odt, a * vp * PPM / odt))
total = sum(r[4] for r in rows)
rows.sort(key=lambda x: x[4], reverse=True)

print(f"\n  {'='*90}")
print(f"  TOP 10 OAV -- CEDRAT CORRECTION")
print(f"  {'='*90}")
print(f"  {'#':<4} {'MATERIAL':<30} {'OAV':>10} {'%':>8}")
GOOD = set(ADDITIONS.keys()) | {"Lemon FCF oil Sicilian", "Hedione HC", "Petitgrain EO", "Hedione"}
good, bad = 0, 0
for i, (n, a, vp, odt, o) in enumerate(rows[:10], 1):
    p = o / total * 100
    ok = "" if n in GOOD else " XX"
    if n in GOOD: good += o
    else: bad += o
    print(f"  {i:<4} {n:<30} {o:>10,.0f} {p:>7.1f}%{ok}")
print(f"\n  GOOD OAV: {good/total*100:.1f}%   BAD OAV: {bad/total*100:.1f}%")
print(f"  HEDONIC INDEX: {good/total*100:.1f}%")
