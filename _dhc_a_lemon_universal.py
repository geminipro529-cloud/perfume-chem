"""DHC A Lemon — Universal Formula (Any Volume).

Expressed as % of concentrate (v/v). This guarantees the same concentration
regardless of batch size: 50 mL, 30 mL, 10 mL, 100 mL.

Usage:
    python _dhc_a_lemon_universal.py <target_mL>
    
Or import and call generate_correction(target_mL).
"""

import sys

# ══════════════════════════════════════════════════════════
# DHC A LEMON — UNIVERSAL FORMULA
# All values are % of concentrate (v/v)
# Concentration: ~12% (120 µL concentrate per 1 mL final)
# ══════════════════════════════════════════════════════════

FINAL_FORMULA = {
    # Citrus — 65% of concentrate
    "Lemon FCF oil Sicilian":  61.09,  # dominant
    "Lime Distilled EO":        3.00,  # anti-candy: green sharpness
    "Aldehyde C10 (1%)":        0.08,  # anti-candy: pith bite
    "Citral":                   0.03,  # anti-candy: citral spike
    "Petitgrain EO":            0.80,  # anti-candy: green-bitter (reduced from original)
    
    # Backbone — 18% of concentrate
    "Hedione":                 10.00,
    "Hedione HC":               2.00,
    "Ethyl Linalool":           4.00,
    "Linalyl Acetate":          2.00,
    
    # Transparency — 3% of concentrate
    "Dihydromyrcenol":          3.00,  # opens up, prevents density
    
    # Iris — 1.5% of concentrate
    "Alpha Irone":              1.50,  # 30% stock = 0.45% active
    
    # Musk/Amber — 11.5% of concentrate
    "Galaxolide":               8.00,  # 50% stock = 4.0% active
    "Habanolide":               2.00,
    "Ambrofix":                 2.50,  # 30% stock = 0.75% active
}

# Verify total
TOTAL_PCT = sum(FINAL_FORMULA.values())
assert abs(TOTAL_PCT - 100.0) < 0.1, f"Formula totals {TOTAL_PCT}%, must be 100%"

# Stock dilution mapping: material -> (stock_concentration, unit)
# For calculating raw µL from active µL
STOCK_DILUTION = {
    "Aldehyde C10 (1%)": (0.01, "1% stock"),
    "Alpha Irone": (0.30, "30% in DEP"),
    "Galaxolide": (0.50, "50% in DEP"),
    "Ambrofix": (0.30, "30% w/v"),
}

def generate_batch(target_mL: float) -> dict:
    """Generate a complete DHC A Lemon batch at any volume.
    
    Returns dict with:
        - target_mL: final volume
        - concentration: % v/v
        - total_concentrate_µL: total concentrate volume
        - materials: list of (name, active_µL, raw_µL, dilution_info)
        - ethanol_mL: ethanol to add
    """
    concentrate_mL = target_mL * 0.12  # 12% concentration
    concentrate_µL = concentrate_mL * 1000
    
    materials = []
    for name, pct in FINAL_FORMULA.items():
        active_µL = concentrate_µL * (pct / 100.0)
        if name in STOCK_DILUTION:
            stock_pct, stock_label = STOCK_DILUTION[name]
            raw_µL = active_µL / stock_pct
            dilution = stock_label
        else:
            raw_µL = active_µL
            dilution = "neat"
        materials.append((name, active_µL, raw_µL, dilution, pct))
    
    total_raw_µL = sum(m[2] for m in materials)
    total_active_µL = sum(m[1] for m in materials)
    ethanol_mL = target_mL - (total_raw_µL / 1000)
    
    return {
        "target_mL": target_mL,
        "concentration": 12.0,
        "total_concentrate_µL": total_active_µL,
        "total_raw_µL": total_raw_µL,
        "materials": materials,
        "ethanol_mL": ethanol_mL,
    }

def generate_correction(existing_batch_mL: float, target_mL: float,
                        existing_materials: dict[str, float]) -> dict:
    """Generate correction for an existing mixed batch.
    
    Args:
        existing_batch_mL: volume of already-mixed batch
        target_mL: desired final volume (must be >= existing_batch_mL)
        existing_materials: dict of {material_name: active_µL} already in batch
        
    Returns dict with materials to ADD and ethanol to add.
    """
    if target_mL < existing_batch_mL:
        raise ValueError("target_mL must be >= existing_batch_mL")
    
    # Calculate what the final batch should have
    final = generate_batch(target_mL)
    
    # Calculate what we need to add
    to_add = []
    for name, active_µL, raw_µL, dilution, pct in final["materials"]:
        existing = existing_materials.get(name, 0)
        needed_active = active_µL - existing
        if needed_active <= 0:
            continue  # already have enough or more
        
        if name in STOCK_DILUTION:
            stock_pct, stock_label = STOCK_DILUTION[name]
            needed_raw = needed_active / stock_pct
        else:
            needed_raw = needed_active
            stock_label = "neat"
        
        to_add.append((name, needed_active, needed_raw, stock_label, pct))
    
    # Calculate ethanol
    total_raw_to_add = sum(m[2] for m in to_add)
    ethanol_mL = target_mL - existing_batch_mL - (total_raw_to_add / 1000)
    
    return {
        "existing_batch_mL": existing_batch_mL,
        "target_mL": target_mL,
        "to_add": to_add,
        "ethanol_mL": ethanol_mL,
        "final_concentration": 12.0,
    }

# ══════════════════════════════════════════════════════════
# YOUR EXISTING LEMON DHC (30 mL Veritas batch)
# These are the ACTIVE µL amounts already in your bottle
# ══════════════════════════════════════════════════════════

YOUR_EXISTING_BATCH = {
    "Lemon FCF oil Sicilian": 3900.0,
    "Hedione": 630.0,
    "Hedione HC": 270.0,
    "Ethyl Linalool": 330.0,
    "Linalyl Acetate": 48.0,
    "Hydroxycitronellal": 6.0,
    "Nympheal": 3.6,
    "Scentenal": 0.012,
    "Floralozone": 0.09,
    "Petitgrain EO": 330.0,
    "Iso E Super": 300.0,
    "Romandolide": 288.0,
    "Ethylene Brassylate": 228.0,
    "Ambrofix": 10.8,
    "Norlimbanol Dextro": 25.2,
    "Vetival": 24.0,
    "Javanol": 9.6,
    "Cardamom EO": 3.0,
}

# ══════════════════════════════════════════════════════════
# CLI / Script execution
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Default: generate correction for your existing 30 mL -> 50 mL
    existing_mL = 30.0
    target_mL = 50.0
    
    if len(sys.argv) > 1:
        target_mL = float(sys.argv[1])
    if len(sys.argv) > 2:
        existing_mL = float(sys.argv[2])
    
    print(f"=" * 60)
    print(f"DHC A Lemon Universal Formula Generator")
    print(f"=" * 60)
    print(f"\nTarget volume: {target_mL} mL")
    print(f"Target concentration: 12% v/v")
    print(f"\n{'MATERIAL':<28} {'ACTIVE%':>8} {'ACTIVEµL':>10} {'RAWµL':>10} {'STOCK':>15}")
    print("-" * 70)
    
    # Show the universal formula
    batch = generate_batch(target_mL)
    for name, active, raw, dilution, pct in batch["materials"]:
        print(f"{name:<28} {pct:>7.2f}% {active:>9.1f} {raw:>9.1f} {dilution:>15}")
    
    print("-" * 70)
    print(f"{'TOTAL CONCENTRATE':<28} {batch['concentration']:>7.1f}% {batch['total_concentrate_µL']:>9.1f} {batch['total_raw_µL']:>9.1f}")
    print(f"{'ETHANOL 96%':<28} {'':>8} {'':>10} {batch['ethanol_mL']*1000:>9.1f} {'neat':>15}")
    print(f"\nFinal volume: {target_mL} mL")
    
    # Show correction for existing batch
    if existing_mL > 0:
        print(f"\n{'=' * 60}")
        print(f"CORRECTION: Existing {existing_mL} mL -> {target_mL} mL")
        print(f"{'=' * 60}")
        
        corr = generate_correction(existing_mL, target_mL, YOUR_EXISTING_BATCH)
        
        if corr["to_add"]:
            print(f"\nMaterials to ADD:")
            print(f"{'MATERIAL':<28} {'ADDµL(active)':>14} {'ADDµL(raw)':>12} {'STOCK':>15}")
            print("-" * 70)
            for name, active, raw, dilution, pct in corr["to_add"]:
                print(f"{name:<28} {active:>13.2f} {raw:>11.2f} {dilution:>15}")
            print("-" * 70)
        else:
            print("\nNo materials need to be added.")
        
        # Show what already exists
        print(f"\nMaterials already in your {existing_mL} mL batch (not added):")
        existing_names = set(YOUR_EXISTING_BATCH.keys())
        final_names = set(FINAL_FORMULA.keys())
        for name in sorted(final_names & existing_names):
            existing = YOUR_EXISTING_BATCH[name]
            target = next(m[1] for m in batch["materials"] if m[0] == name)
            status = "OK" if existing >= target else f"have {existing:.1f}, need {target:.1f}"
            print(f"  {name:<28} {existing:>8.1f} µL active  ({status})")
        
        # Show what's in existing batch but NOT in final formula
        extra = existing_names - final_names
        if extra:
            print(f"\nMaterials in your batch NOT in DHC A formula (will be diluted):")
            for name in sorted(extra):
                print(f"  {name:<28} {YOUR_EXISTING_BATCH[name]:>8.1f} µL active")
        
        print(f"\n{'=' * 60}")
        print(f"INSTRUCTIONS")
        print(f"{'=' * 60}")
        print(f"1. Pour your existing {existing_mL} mL batch into a {target_mL} mL bottle")
        if corr["ethanol_mL"] > 0:
            print(f"2. Add {corr['ethanol_mL']:.1f} mL ethanol 96%")
        if corr["to_add"]:
            print(f"3. Add the correction materials above (in order shown)")
        print(f"4. Cap and invert 50×")
        print(f"5. Macerate 4 weeks minimum")
        print(f"\nFinal concentration: ~{corr['final_concentration']:.0f}%")
        print(f"Expected longevity: 5–7 hours")
        print(f"DHC likeness: ~85%")
