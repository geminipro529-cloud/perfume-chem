"""DHC Corrections: LEMON-FIRST + Realness Microadditions.

Strategy:
- MAIN additions: materials that SMELL like lemon (real lemon character, not candy)
- CORE additions: DHC architecture materials (Hedione, DHM, Galaxolide, Ambrofix, Alpha Irone)
- MICRO additions: non-lemon realness at trace levels (green, earthy, mineral, herbal)
"""
import sys, math
sys.path.insert(0, '.')
from engine.odor_thresholds import ODT_DATA
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name

PPM = 20.0
STOCK = {"Aldehyde C10 (1%)": 0.01, "Aldehyde C12 MNA (1%)": 0.01, "Alpha Irone": 0.30,
         "Galaxolide": 0.50, "Ambrofix": 0.30, "Geosmin (0.1%)": 0.001,
         "Scentenal (1%)": 0.01}

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0, "Hedione": 900.0, "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0, "Linalyl Acetate": 120.0, "Petitgrain EO": 150.0,
    "Ambrofix": 10.8,
    "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

# LEMON additions (smell like lemon)
LEMON_ADDITIONS = {
    "Lemon FCF oil Sicilian": 1700.0,   # still the base, but reduced (existing 4200 covers most)
    "Citral": 50.0,                       # sharp lemon zest -- UP from 3
    "Lemonile": 5.0,                     # intensely fresh lemon peel (NEW)
    "Lime Distilled EO": 500.0,          # green lemon-lime clarity -- UP from 295
    "Aldehyde C10 (1%)": 25.0,           # citrus peel sparkle -- UP from 8
    "Aldehyde C12 MNA (1%)": 3.0,        # citrus wax aldehydic lift (NEW)
}

# CORE DHC architecture (essential structure materials)
CORE_ADDITIONS = {
    "Hedione": 600.0,                    # radiance -- UP from 246
    "Dihydromyrcenol": 800.0,            # transparency: opens locked woods -- UP from 295
    "Galaxolide (50%)": 350.0,           # active: clean white musk
    "Habanolide": 200.0,                 # transparent musk
    "Ambrofix (30%)": 150.0,             # active: skin-amber halo
    "Alpha Irone (30%)": 150.0,          # active: iris heart (DHC signature)
    "Ethyl Linalool": 100.0,             # clean lift (existing 330 nearly enough)
    "Linalyl Acetate": 100.0,            # bright top
}

# MICRO realness (non-lemon, trace levels)
MICRO_ADDITIONS = {
    "cis-3-Hexenol": 2.0,                # fresh-cut grass: makes citrus feel "alive"
    "Vetiver EO India": 2.0,             # earthy root: grounds citrus (tree effect)
    "Geosmin (0.1%)": 2.0,               # active: petrichor wet stone
    "Clary Sage EO": 8.0,                # herbal tea: natural complexity
    "Scentenal (1%)": 0.3,               # active: metallic effervescence
}

ADDITIONS = {}
for d in [LEMON_ADDITIONS, CORE_ADDITIONS, MICRO_ADDITIONS]:
    ADDITIONS.update(d)

STOCK_MAP = {
    "Aldehyde C10 (1%)": 0.01,
    "Aldehyde C12 MNA (1%)": 0.01,
    "Alpha Irone (30%)": 0.30,
    "Galaxolide (50%)": 0.50,
    "Ambrofix (30%)": 0.30,
    "Geosmin (0.1%)": 0.001,
    "Scentenal (1%)": 0.01,
}

def stock_frac(name):
    for k, v in STOCK_MAP.items():
        if k in name:
            return v
    return 1.0

def stock_label(name):
    sf = stock_frac(name)
    if sf < 0.01: return f"<1%"
    if sf < 1.0: return f"{sf*100:.0f}%"
    return "neat"

existing_total = sum(EXISTING.values())
target_active = 12000.0
add_total = sum(ADDITIONS.values())
scale = (target_active - existing_total) / add_total if add_total else 0

print("=" * 90)
print("  HEDONIC CORRECTION -- LEMON-FIRST + REALNESS MICROADDITIONS")
print(f"  Scale factor: {scale:.3f}  |  Total additions needed: {target_active-existing_total:.0f} uL active")
print("=" * 90)

print(f"\n  {'='*90}")
print(f"  {'CATEGORY':<20} {'MATERIAL':<28} {'ACTIVE':>8} {'RAW':>8} {'STOCK':>10}")
print(f"  {'='*90}")

categories = [("LEMON (smells like lemon)", LEMON_ADDITIONS),
              ("CORE (architecture)", CORE_ADDITIONS),
              ("MICRO (realness)", MICRO_ADDITIONS)]

total_raw = 0.0
total_active = 0.0
for cat_name, adds in categories:
    print(f"\n  {cat_name}")
    print(f"  {'-'*78}")
    for mat, active in sorted(adds.items(), key=lambda x: x[1], reverse=True):
        if scale < 1.0:
            active = active * scale
        sf = stock_frac(mat)
        raw = active / sf
        label = stock_label(mat)
        print(f"  {'':<20} {mat:<28} {active:>8.1f} {raw:>8.1f} {label:>10}")
        total_raw += raw
        total_active += active

ethanol = 100.0 - 31.4 - total_raw/1000
print(f"\n  {'TOTAL STOCK ADDITIONS':<48} {total_raw:>8.1f} uL")
print(f"  {'ETHANOL 96% TO ADD':<48} {ethanol:>8.1f} mL")
print(f"  {'FINAL VOLUME':<48}  100.0 mL")
print(f"  {'FINAL CONCENTRATION':<48}  {(existing_total + total_active)/1000:.1f}%")

# OAV analysis
def get_vp_odt(name):
    p = get_profile(name)
    return (p.vp if p and p.vp else 0), (ODT_DATA.get(normalize_name(name), {}).get("odt_air") or 0)

def calc_oav(active, vp, odt):
    return active * vp * PPM / odt if vp and odt else 0.0

CORRECTED = dict(EXISTING)
for mat, active in ADDITIONS.items():
    CORRECTED[mat] = CORRECTED.get(mat, 0.0) + active * scale

rows = []
for n, a in CORRECTED.items():
    vp, odt = get_vp_odt(n)
    if vp and odt:
        rows.append((n, a, vp, odt, calc_oav(a, vp, odt)))
total_oav = sum(r[4] for r in rows)
rows.sort(key=lambda x: x[4], reverse=True)

print(f"\n  {'='*90}")
print(f"  TOP 10 OAV")
print(f"  {'='*78}")
fresh_mats = {"Lemon FCF oil Sicilian", "Citral", "Lemonile", "Lime Distilled EO",
              "Aldehyde C10 (1%)", "Aldehyde C12 MNA (1%)", "Dihydromyrcenol",
              "Hedione", "Galaxolide (50%)", "Habanolide", "Ambrofix (30%)",
              "Alpha Irone (30%)", "Ethyl Linalool", "Linalyl Acetate", "Petitgrain EO",
              "Hedione HC", "cis-3-Hexenol", "Vetiver EO India", "Clary Sage EO",
              "Geosmin (0.1%)", "Scentenal (1%)"}
good_oav = 0
bad_oav = 0
print(f"  {'#':<4} {'MATERIAL':<30} {'OAV':>10} {'%':>8}")
for i, (n, a, vp, odt, o) in enumerate(rows[:10], 1):
    pct = o / total_oav * 100
    if n in fresh_mats:
        good_oav += o
        ok = ""
    else:
        bad_oav += o
        ok = " !!"
    print(f"  {i:<4} {n:<30} {o:>10,.0f} {pct:>7.1f}%{ok}")
print(f"\n  GOOD OAV: {good_oav/total_oav*100:.1f}%   BAD OAV: {bad_oav/total_oav*100:.1f}%")
print(f"  HEDONIC INDEX: {good_oav/total_oav*100:.1f}")
