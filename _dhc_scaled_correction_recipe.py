"""Generate scaled correction recipe for 100mL at 12% concentration."""
from __future__ import annotations

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
    "Iso E Super": 300.0,
    "Romandolide": 288.0,
    "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2,
    "Vetival": 24.0,
    "Javanol": 9.6,
    "Cardamom EO": 3.0,
}

TARGET_PCT = {
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

existing_total = sum(EXISTING.values())
target_total = 12000.0
additions_needed = target_total - existing_total

# Calculate unscaled additions
unscaled = {}
for mat, pct in TARGET_PCT.items():
    target_active = target_total * (pct / 100.0)
    have = EXISTING.get(mat, 0.0)
    if target_active > have:
        unscaled[mat] = target_active - have

unscaled_total = sum(unscaled.values())
scale = additions_needed / unscaled_total

print("=" * 80)
print("DHC A LEMON -- SCALED CORRECTION RECIPE (100mL at 12% v/v)")
print("=" * 80)
print(f"\nExisting batch: 31.4 mL total (24 mL ethanol + ~7.1 mL concentrate)")
print(f"Existing active: {existing_total:.1f} uL")
print(f"Target active: {target_total:.1f} uL")
print(f"Additions needed: {additions_needed:.1f} uL active")
print(f"Scale factor: {scale:.4f} (to hit exactly 12%)")

print(f"\n{'MATERIAL TO ADD':<28} {'ACTIVE uL':>12} {'STOCK uL':>12} {'DILUTION':>12}")
print("-" * 80)
total_add_active = 0.0
total_add_raw = 0.0
for mat, active in sorted(unscaled.items(), key=lambda x: x[1], reverse=True):
    scaled_active = active * scale
    stock_frac = STOCK_DILUTION.get(mat, 1.0)
    raw = scaled_active / stock_frac
    label = f"{stock_frac*100:.0f}%" if stock_frac < 1.0 else "neat"
    print(f"{mat:<28} {scaled_active:>12.1f} {raw:>12.1f} {label:>12}")
    total_add_active += scaled_active
    total_add_raw += raw

print("-" * 80)
print(f"{'TOTAL':<28} {total_add_active:>12.1f} {total_add_raw:>12.1f}")

ethanol_mL = 100.0 - 31.4 - (total_add_raw / 1000.0)
print(f"\nEthanol 96% to add: {ethanol_mL:.1f} mL")
print(f"Final check: 31.4 + {total_add_raw/1000:.1f} + {ethanol_mL:.1f} = 100.0 mL")
print(f"Final concentration: {(existing_total + total_add_active)/1000:.1f}%")

print("\n" + "=" * 80)
print("FRESH DHC A LEMON 100mL (for comparison)")
print("=" * 80)
print(f"{'MATERIAL':<28} {'ACTIVE uL':>12} {'STOCK uL':>12} {'DILUTION':>12}")
print("-" * 80)
fresh_total_raw = 0.0
for mat, pct in sorted(TARGET_PCT.items(), key=lambda x: x[1], reverse=True):
    active = target_total * (pct / 100.0)
    stock_frac = STOCK_DILUTION.get(mat, 1.0)
    raw = active / stock_frac
    label = f"{stock_frac*100:.0f}%" if stock_frac < 1.0 else "neat"
    print(f"{mat:<28} {active:>12.1f} {raw:>12.1f} {label:>12}")
    fresh_total_raw += raw
print("-" * 80)
print(f"Ethanol 96%: {100.0 - fresh_total_raw/1000.0:.1f} mL")
