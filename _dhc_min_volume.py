"""Find minimum final volume V for correction at 12% concentration.

Given: existing 31.4 mL batch at 22.3% with 7,001 uL active (930.7 uL "bad locked").
Goal: dilute to 12% v/v AND add DHC A materials so good materials are in DHC A proportions.
Find: the smallest V where all good materials meet their DHC A target.
"""
from __future__ import annotations

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0,
    "Hedione": 900.0,
    "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0,
    "Linalyl Acetate": 120.0,
    "Petitgrain EO": 150.0,
    "Ambrofix": 10.8,
    # Locked bad:
    "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

DHC_A_PCT = {
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

STOCK = {"Aldehyde C10 (1%)": 0.01, "Alpha Irone": 0.30, "Galaxolide": 0.50, "Ambrofix": 0.30}
GOOD_MATS = set(DHC_A_PCT.keys())

existing_bad = sum(v for n, v in EXISTING.items() if n not in GOOD_MATS)
existing_good = sum(v for n, v in EXISTING.items() if n in GOOD_MATS)
existing_total = sum(EXISTING.values())

print(f"Existing bad locked: {existing_bad:.1f} uL")
print(f"Existing good: {existing_good:.1f} uL")
print(f"Existing total: {existing_total:.1f} uL\n")

# Find minimum V where all existing good materials <= their DHC A target
# At volume V: good_material_target = (0.12*V - existing_bad) * (pct_i / 100)
# Need: good_material_target >= existing_good_i
# => 0.12*V - existing_bad >= existing_good_i * 100 / pct_i
# => V >= (existing_good_i * 100 / pct_i + existing_bad) / 0.12

v_candidates = []
for mat, pct in DHC_A_PCT.items():
    eg = EXISTING.get(mat, 0.0)
    if eg > 0:
        V = (eg * 100.0 / pct + existing_bad) / 0.12
        v_candidates.append((mat, eg, pct, V))

v_candidates.sort(key=lambda x: x[3], reverse=True)
print(f"{'Material':<28} {'Existing':>10} {'DHC A %':>8} {'Min V (mL)':>12}")
print("-" * 60)
for mat, eg, pct, V in v_candidates:
    print(f"{mat:<28} {eg:>10.1f} {pct:>7.2f}% {V/1000:>11.1f}")

# The first one in sorted list = maximum = the constraint
# But we also skip materials where existing > target at low V (they're over-dosed, which is fine)
# We only care about materials where existing < target (need to add)
# So the limiting factor is the material with existing > 0 that needs the MOST volume
# to make target >= existing

# Actually, we want ALL existing good materials to be AT OR BELOW their target.
# If existing > target at small V, that's fine - the material is just over-dosed.
# The constraint is: existing_good materials CAN'T be reduced, so we need V large enough
# that their proportional target is AT LEAST their existing amount.
# This means V must be >= (existing_good_i * 100 / pct_i + existing_bad) / 0.12 for ALL i.

# Petitgrain is the limit: existing 150, pct 0.80%
# 0.12V - 930.7 >= 150 * 100 / 0.80 = 18750
# V >= (18750 + 930.7) / 0.12 = 164 mL

# BUT - Petitgrain being over-dosed is not a problem. It's a good material.
# The REAL constraints are the locked bad materials' OAV share.
# At a given V, the bad OAV share = bad_activity / total_activity

# Let me just compute for several V values:
print("\n\n")
print(f"{'V (mL)':>8} {'Total act':>10} {'Bad act':>10} {'Bad OAV%':>10} {'Add active':>12} {'Add raw':>10} {'Ethanol':>10}")
print("-" * 70)
for V_mL in [50, 60, 70, 80, 82.8, 90, 100, 125, 150, 164, 200]:
    total_active = 0.12 * V_mL * 1000
    bad_share = existing_bad / total_active * 100
    add_active = total_active - existing_total  # might be negative for small V
    
    # Calculate additions for each good material
    good_target_total = total_active - existing_bad  # total good materials target
    add_raw_ul = 0
    for mat, pct in DHC_A_PCT.items():
        target = good_target_total * pct / 100.0
        have = EXISTING.get(mat, 0.0)
        if target > have:
            raw = (target - have) / STOCK.get(mat, 1.0)
            add_raw_ul += raw
    
    ethanol_mL = V_mL - 31.4 - (add_raw_ul / 1000)
    marker = " <--" if bad_share < 5 or V_mL == 164 else ""
    print(f"{V_mL:>8.1f} {total_active:>10.0f} {existing_bad:>10.1f} {bad_share:>9.1f}% {add_active:>10.0f} {add_raw_ul:>10.0f} {ethanol_mL:>9.1f}{marker}")
