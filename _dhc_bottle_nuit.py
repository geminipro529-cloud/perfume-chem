"""Bottle B -- DHC Lemon Nuit."""
import sys; sys.path.insert(0,'.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0, "Hedione": 900.0, "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0, "Linalyl Acetate": 120.0, "Petitgrain EO": 150.0,
    "Ambrofix": 10.8, "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

F = 0.75
TARGET = 7000
EXISTING_ML = 33.0
EXISTING_A = {n: v * F for n, v in EXISTING.items()}

ADD = {
    # IRIS SPINE (shared)
    "Alpha Irone": 220,
    # CITRUS REALISM (trimmed for forest budget)
    "Lime Distilled EO": 200,
    "Bergamot FCF oil Sicilian": 250,
    "Cedrat FCF oil Sicilian": 140,
    "Terpinyl Acetate": 80,
    "D-Limonene": 7,
    "Beta-Pinene": 3,
    "Aldehyde C10": 10,
    "Aldehyde C11": 8,
    # CORE
    "Galaxolide": 175,
    "Ambrox Super": 14,
    "Hedione": 80,
    # WARM BASE
    "Coumarin (20%)": 180,
    "Vanillin (10%)": 15,
    "Cashmeran": 70,
    "Damascenone (1%)": 9,
    # DARK FOREST (NUIT)
    "Olibanum Resinoid Absolute (10%)": 100,
    "Lavender EO High Altitude": 150,
    # LAVENDER (aromatic bridge)
    # removed Suederal, IBQ
    # EARTH
    "Vetiver EO India": 18,
    "Evernyl": 10,
}

STOCK = {"Galaxolide": 0.50, "Ambrox Super": 0.333, "Coumarin (20%)": 0.20,
         "Vanillin (10%)": 0.10, "Damascenone (1%)": 0.01,
         "Olibanum Resinoid Absolute (10%)": 0.10,
         "Alpha Irone": 0.30}

existing_total = sum(EXISTING_A.values())
add_total = sum(ADD.values())
remaining = TARGET - existing_total
scale = remaining / add_total if add_total else 0

print("=" * 70)
print("  BOTTLE B -- DHC LEMON NUIT")
print(f"  Pour {EXISTING_ML * F:.1f} mL | Add budget: {remaining:.0f} uL active")
print("=" * 70)

final = dict(EXISTING_A)
total_raw = 0
print(f"\n  {'#':<4} {'MATERIAL':<32} {'ACT uL':>8} {'RAW uL':>8}")
print("  " + "-" * 56)
for i, (m, a) in enumerate(sorted(ADD.items(), key=lambda x: x[1], reverse=True), 1):
    sa = a * scale
    sf = STOCK.get(m, 1.0)
    sr = sa / sf
    total_raw += sr
    final[m] = final.get(m, 0) + sa
    sl = f"{sf*100:.0f}%" if sf < 1.0 else ""
    print(f"  {i:<4} {m:<32} {sa:>8.1f} {sr:>8.1f}  {sl}")

raw_ml = EXISTING_ML * F
eth = 50.0 - raw_ml - total_raw / 1000
total_final = sum(final.values())
print(f"\n  ETHANOL 96%: {eth:.1f} mL")
print(f"  CONCENTRATION: {total_final/50000*100:.1f}%  |  Active: {total_final:.0f} uL")

# OAV
rows = []
for n, a in final.items():
    p = get_profile(n)
    vp = p.vp if p and p.vp else 0
    odt = (ODT_DATA.get(normalize_name(n), {}).get("odt_air"))
    if vp and (odt or 0):
        rows.append((n, a, a * vp * PPM / odt))
rows.sort(key=lambda x: x[2], reverse=True)
total_oav = sum(r[2] for r in rows)

GOOD = set(ADD.keys()) | {"Lemon FCF oil Sicilian","Hedione HC","Petitgrain EO","Linalyl Acetate",
    "Ethyl Linalool","Iso E Super","Romandolide","Ethylene Brassylate","Dihydrojasmone",
    "Javanol","Vetival","Norlimbanol Dextro","Cardamom EO","Mayol","Nympheal",
    "Ambrofix","Hedione"}

good_ = sum(r[2] for r in rows if r[0] in GOOD)
print(f"\n  TOP OAV:")
for i, (n, a, o) in enumerate(rows[:10], 1):
    p = o / total_oav * 100
    ok = "XX" if n not in GOOD else ""
    print(f"  {i:>2}. {n:<30} {o:>8,.0f} ({p:>5.1f}%) {ok}")
print(f"\n  GOOD OAV: {good_/total_oav*100:.1f}%  |  BAD: {(total_oav-good_)/total_oav*100:.1f}%")
