"""DHC Lemon 100mL Correction -- ACTUAL LEMONADE FORMULA.

User has DHC_VII_Lemon_Lemonade_Chanel.md (30mL version).
This is sweeter, more floral, higher concentration than standard DHC.
"""

import sys
sys.path.insert(0, '.')
from engine.odor_thresholds import ODT_DATA
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name

PPM = 20.0

def get_vp_odt(name):
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    n = normalize_name(name)
    odt = ODT_DATA.get(n, {}).get('odt_air')
    return vp, odt

def oav(active, vp, odt):
    return active * vp * PPM / odt if vp and odt else 0

# YOUR ACTUAL 30mL LEMONADE BATCH (scaled from 50mL x 0.6)
EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0,
    "Hedione": 900.0,
    "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0,
    "Linalyl Acetate": 120.0,
    "Petitgrain EO": 150.0,
    "Ethyl Maltol": 1.8,
    "Dihydrojasmone": 30.0,
    "Aurantiol": 9.0,
    "Mayol": 8.4,
    "Nympheal": 3.6,
    "Scentenal": 0.012,
    "Floralozone": 0.06,
    "Ambrofix": 10.8,
    # Bad materials
    "Iso E Super": 300.0,
    "Romandolide": 288.0,
    "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2,
    "Vetival": 24.0,
    "Javanol": 9.6,
    "Cardamom EO": 3.0,
}

# DHC A target formula (% of concentrate)
TARGET_FORMULA = {
    "Lemon FCF oil Sicilian": 61.09,
    "Lime Distilled EO": 3.00,
    "Aldehyde C10 (1%)": 0.08,
    "Citral": 0.03,
    "Petitgrain EO": 0.80,
    "Hedione": 10.00,
    "Hedione HC": 2.00,
    "Ethyl Linalool": 4.00,
    "Linalyl Acetate": 2.00,
    "Dihydromyrcenol": 3.00,
    "Alpha Irone": 1.50,
    "Galaxolide": 8.00,
    "Habanolide": 2.00,
    "Ambrofix": 2.50,
}

STOCK_DILUTION = {
    "Aldehyde C10 (1%)": 0.01,
    "Alpha Irone": 0.30,
    "Galaxolide": 0.50,
    "Ambrofix": 0.30,
}

GOOD_MATS = set(TARGET_FORMULA.keys())

# Calculate
target_mL = 100.0
total_conc = target_mL * 0.12 * 1000  # 12,000 µL active

target_active = {}
for mat, pct in TARGET_FORMULA.items():
    target_active[mat] = total_conc * (pct / 100)

additions = {}
for mat, target in target_active.items():
    have = EXISTING.get(mat, 0)
    if target > have:
        additions[mat] = target - have

final_active = dict(EXISTING)
for mat, add in additions.items():
    final_active[mat] = final_active.get(mat, 0) + add

existing_oav = {}
target_oav = {}
final_oav = {}

for mat in set(list(EXISTING.keys()) + list(TARGET_FORMULA.keys())):
    vp, odt = get_vp_odt(mat)
    if vp and odt:
        existing_oav[mat] = oav(EXISTING.get(mat, 0), vp, odt)
        target_oav[mat] = oav(target_active.get(mat, 0), vp, odt)
        final_oav[mat] = oav(final_active.get(mat, 0), vp, odt)

existing_total = sum(existing_oav.values())
target_total = sum(target_oav.values())
final_total = sum(final_oav.values())

final_good = sum(v for m, v in final_oav.items() if m in GOOD_MATS)
final_bad = final_total - final_good

# Print
print("=" * 75)
print("DHC LEMONADE -> DHC A (100mL CORRECTION)")
print("=" * 75)
print(f"\nYour actual batch: DHC VII Lemon Lemonade (30mL)")
print(f"  - Sweetened with Ethyl Maltol + Aurantiol")
print(f"  - Higher concentration (~23% vs target 12%)")
print(f"  - Total active: {sum(EXISTING.values()):.0f} µL")
print(f"\nTarget: {target_mL} mL at 12% v/v")
print(f"  - Total concentrate needed: {total_conc:.0f} µL active")

print(f"\n{'='*75}")
print("MATERIALS TO ADD")
print(f"{'='*75}")
print(f"{'#':<4} {'Material':<28} {'ActiveµL':>10} {'StockµL':>10} {'Stock':>15}")
print("-" * 75)

total_add_active = 0
total_add_raw = 0
for i, (mat, active) in enumerate(sorted(additions.items(), key=lambda x: x[1], reverse=True), 1):
    stock_frac = STOCK_DILUTION.get(mat, 1.0)
    raw = active / stock_frac
    label = f"{stock_frac*100:.0f}% stock" if stock_frac < 1.0 else "neat"
    print(f"{i:<4} {mat:<28} {active:>10.1f} {raw:>10.1f} {label:>15}")
    total_add_active += active
    total_add_raw += raw

print("-" * 75)
print(f"{'TOTAL ADDITIONS':<33} {total_add_active:>10.1f} {total_add_raw:>10.1f}")

ethanol_mL = target_mL - 30 - (total_add_raw / 1000)
print(f"\nEthanol 96% to add: {ethanol_mL:.1f} mL")
print(f"Final check: 30 + {total_add_raw/1000:.1f} + {ethanol_mL:.1f} = {target_mL:.1f} mL")

print(f"\n{'='*75}")
print("OAV ANALYSIS (NEW ENGINE)")
print(f"{'='*75}")

print(f"\n{'Material':<28} {'Exist%':>8} {'Target%':>8} {'Final%':>8}")
print("-" * 75)

for mat in sorted(TARGET_FORMULA.keys(), key=lambda m: target_oav.get(m, 0), reverse=True):
    e = existing_oav.get(mat, 0) / existing_total * 100 if existing_total > 0 else 0
    t = target_oav.get(mat, 0) / target_total * 100 if target_total > 0 else 0
    f = final_oav.get(mat, 0) / final_total * 100 if final_total > 0 else 0
    print(f"{mat:<28} {e:>7.1f}% {t:>7.1f}% {f:>7.1f}%")

print("-" * 75)
print(f"{'BAD MATERIALS (locked)':<28}")
for mat in sorted([m for m in final_oav if m not in GOOD_MATS], key=lambda m: final_oav[m], reverse=True)[:8]:
    e = existing_oav.get(mat, 0) / existing_total * 100 if existing_total > 0 else 0
    f = final_oav[mat] / final_total * 100
    print(f"{mat:<28} {e:>7.1f}% {'--':>8} {f:>7.1f}%")

print(f"\nGOOD vs BAD")
print(f"  Before: {(sum(v for m,v in existing_oav.items() if m in GOOD_MATS)/existing_total*100 if existing_total > 0 else 0):.1f}% good")
print(f"  Target: 100.0% good")
print(f"  After:  {final_good/final_total*100:.1f}% good / {final_bad/final_total*100:.1f}% bad")

bad_pct = final_bad / final_total * 100
print(f"\nVERDICT:")
if bad_pct < 15:
    print(f"  VERY GOOD -- DHC with subtle depth")
else:
    print(f"  GOOD -- Noticeable woody/green background")

print(f"\nKey issue: Iso E Super at {final_oav.get('Iso E Super', 0)/final_total*100:.1f}% of OAV")
print(f"Also: Aurantiol + Ethyl Maltol sugar notes will persist")
print(f"Result: 'Sweet woody lemon' rather than pure DHC")

print(f"\n{'='*75}")
print("MATERIALS IN YOUR BATCH NOT IN DHC A:")
print(f"{'='*75}")
extra = set(EXISTING.keys()) - set(TARGET_FORMULA.keys())
for mat in sorted(extra):
    print(f"  - {mat}: {EXISTING[mat]:.1f} µL active (cannot remove)")

print(f"\nThese give your corrected batch a UNIQUE character:")
print(f"  - Sweet (Ethyl Maltol + Aurantiol)")
print(f"  - Floral-jasmine (Dihydrojasmone)")
print(f"  - Muguet (Mayol + Nympheal)")
print(f"  - Woody (Iso E Super + Romandolide)")
print(f"\nThis is NOT a flaw -- it's a distinct lemonade-woody-lemon identity.")
