"""Convert F1 Le Barbier de Grasse v2-optimized wt% to a 30 mL concentrate
recipe in µL, accounting for inventory dilutions (Galaxolide 80%, Coumarin 20%,
Ambrox Super 30%, Vanillin 10%). Validate inventory presence + sum.
"""
from __future__ import annotations

import json
from pathlib import Path

# Active wt% from _fougere_5_named_v2_out.json -> F1 -> optimized
ACTIVE_WT = {
    "Hedione":           16.924,
    "Iso E Super":       13.619,
    "Ethylene Brassylate": 9.054,  # swapped from Habanolide (low stock); neat-for-neat, depth axis preserved
    "Lavender EO":        8.096,
    "Galaxolide":         7.036,
    "Cedarwood EO":       6.886,
    "Bergamot FCF":       6.248,
    "Linalyl Acetate":    5.729,
    "Coumarin":           5.322,
    "Patchouli EO":       5.181,
    "Vetiver EO":         3.445,
    "Geraniol":           3.340,
    "Evernyl":            2.313,
    "Ambrox Super":       2.282,
    "Hexyl Salicylate":   2.103,
    "Eugenol":            1.477,
    "Vanillin":           0.943,
}

# Inventory form to use, dilution fraction, inventory listing as confirmed
DILUTION = {
    "Hedione":           ("neat",        1.00),
    "Iso E Super":       ("neat",        1.00),
    "Ethylene Brassylate": ("neat",      1.00),
    "Lavender EO":       ("neat",        1.00),
    "Galaxolide":        ("80%",         0.80),
    "Cedarwood EO":      ("neat",        1.00),
    "Bergamot FCF":      ("neat",        1.00),
    "Linalyl Acetate":   ("neat",        1.00),
    "Coumarin":          ("20% in DPG",  0.20),
    "Patchouli EO":      ("neat",        1.00),
    "Vetiver EO":        ("neat",        1.00),
    "Geraniol":          ("neat",        1.00),
    "Evernyl":           ("neat",        1.00),
    "Ambrox Super":      ("30% w/v",     0.30),
    "Hexyl Salicylate":  ("neat",        1.00),
    "Eugenol":           ("neat",        1.00),
    "Vanillin":          ("10%",         0.10),
}

BATCH_VOL_ML = 30.0
BATCH_MASS_MG = BATCH_VOL_ML * 1000.0  # density ≈ 1.0 g/mL


# Validate inventory presence (string match)
INV_PATH = Path(__file__).parent / "inventory.txt"
inv = INV_PATH.read_text(encoding="utf-8")
missing = []
for mat in ACTIVE_WT:
    if mat.lower() not in inv.lower():
        missing.append(mat)
if missing:
    print(f"WARNING: not found in inventory: {missing}")
else:
    print("All 17 materials present in inventory.txt ✓")

# Verify wt% sums to ~100
total_wt = sum(ACTIVE_WT.values())
print(f"Active wt% sum = {total_wt:.3f} (expect ~100.0)")

# Stage 1: per-material µL of inventory item (un-scaled, target = 30 g actives)
rows = []
total_inv_uL = 0.0
total_active_mg = 0.0
for mat, wt in ACTIVE_WT.items():
    form, dil = DILUTION[mat]
    active_mg = wt * BATCH_MASS_MG / 100.0
    inv_uL = active_mg / dil  # density 1.0, so mg = µL of inventory liquid
    rows.append({"mat": mat, "wt%_active": wt, "form": form, "dil": dil,
                 "active_mg": active_mg, "inv_uL_unscaled": inv_uL})
    total_inv_uL += inv_uL
    total_active_mg += active_mg

# Stage 2: scale so total inventory volume = 30 mL exactly
scale = BATCH_MASS_MG / total_inv_uL
print(f"\nUnscaled inventory volume sum = {total_inv_uL:.0f} µL  ({total_inv_uL/1000:.2f} mL)")
print(f"Scale factor (to fit 30 mL) = {scale:.4f}")
print(f"Active mass after scaling   = {total_active_mg * scale:.0f} mg ({(total_active_mg*scale)/BATCH_MASS_MG*100:.1f}% of concentrate)")
print(f"Inert carrier (DPG/DEP)     = {(BATCH_MASS_MG - total_active_mg*scale):.0f} mg ({(1-(total_active_mg*scale)/BATCH_MASS_MG)*100:.1f}% of concentrate)")

for r in rows:
    r["inv_uL_30mL"] = round(r["inv_uL_unscaled"] * scale)
    r["active_mg_final"] = r["active_mg"] * scale

# Validate scaled sum
scaled_sum = sum(r["inv_uL_30mL"] for r in rows)
print(f"\nScaled µL sum = {scaled_sum} µL  (target = 30000; rounding diff = {scaled_sum-30000})")

# Sort by descending µL
rows.sort(key=lambda r: -r["inv_uL_30mL"])

# Print recipe table
print("\n" + "="*88)
print(f"{'#':>2}  {'Material':25s}  {'Form':14s}  {'µL':>6s}  {'mL':>6s}  {'wt%(act)':>8s}")
print("="*88)
for i, r in enumerate(rows, 1):
    mL = r["inv_uL_30mL"] / 1000.0
    print(f"{i:>2}  {r['mat']:25s}  {r['form']:14s}  {r['inv_uL_30mL']:>6d}  {mL:>6.2f}  {r['wt%_active']:>7.2f}%")
print("="*88)
print(f"{'TOTAL':>43s}                  {scaled_sum:>6d}  {scaled_sum/1000:>6.2f}")

# Persist
out = {"batch_mL": BATCH_VOL_ML, "scale_factor": scale,
       "active_mass_mg": total_active_mg * scale,
       "inert_carrier_mg": BATCH_MASS_MG - total_active_mg * scale,
       "rows": rows, "scaled_sum_uL": scaled_sum}
Path("_F1_30mL_recipe.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("\nWrote _F1_30mL_recipe.json")
