"""Compare existing 30 mL DHC Lemon against DHC A target.
Shows ratios and identifies limiting ingredients."""

# What you ALREADY have in your 30 mL mixed batch (active µL)
EXISTING = {
    "Lemon FCF oil Sicilian": 3900.0,
    "Hedione": 630.0,
    "Hedione HC": 270.0,
    "Ethyl Linalool": 330.0,
    "Linalyl Acetate": 48.0,
    "Petitgrain EO": 330.0,
    # Materials NOT in new formula:
    "Iso E Super": 300.0,
    "Romandolide": 288.0,
    "Ethylene Brassylate": 228.0,
    "Ambrofix": 10.8,
    "Norlimbanol Dextro": 25.2,
    "Vetival": 24.0,
    "Javanol": 9.6,
    "Cardamom EO": 3.0,
    "Hydroxycitronellal": 6.0,
    "Nympheal": 3.6,
    "Scentenal": 0.012,
    "Floralozone": 0.09,
}

# DHC A formula: % of concentrate
FORMULA = {
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

# Calculate targets at different volumes
for target_mL in [30, 40, 50]:
    total_conc = target_mL * 0.12 * 1000
    
    print(f"\n{'='*70}")
    print(f"DHC A TARGET: {target_mL} mL (Total concentrate: {total_conc:.0f} µL active)")
    print(f"{'='*70}")
    print(f"{'Material':<28} {'HaveµL':>8} {'NeedµL':>8} {'Ratio':>8} {'Status':>15}")
    print("-" * 70)
    
    # Materials in both
    for mat, pct in FORMULA.items():
        need = total_conc * (pct / 100)
        have = EXISTING.get(mat, 0)
        ratio = have / need if need > 0 else 999
        
        if have == 0:
            status = "MISSING — add"
        elif ratio >= 1.0:
            status = f"EXCESS ({ratio:.1f}x)"
        else:
            status = f"SHORT ({ratio:.2f}x)"
        
        print(f"{mat:<28} {have:>8.1f} {need:>8.1f} {ratio:>8.2f} {status:>15}")
    
    # Materials in existing but NOT in new formula
    print("-" * 70)
    print("Materials in YOUR batch NOT in DHC A (cannot remove):")
    extra = set(EXISTING.keys()) - set(FORMULA.keys())
    for mat in sorted(extra):
        have = EXISTING[mat]
        print(f"  {mat:<28} {have:>8.1f} µL — will be diluted to {have/(total_conc/1000)*100:.2f}% of concentrate")
    
    # Find limiting factor
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    # Missing materials
    missing = [m for m in FORMULA if EXISTING.get(m, 0) == 0]
    if missing:
        print(f"\nMissing materials (you need to ADD these):")
        for m in missing:
            need = total_conc * (FORMULA[m] / 100)
            print(f"  • {m}: add {need:.1f} µL active")
    
    # Excess materials that can't be removed
    excess = [(m, EXISTING[m], total_conc * (FORMULA[m] / 100)) 
              for m in FORMULA if m in EXISTING and EXISTING[m] > total_conc * (FORMULA[m] / 100)]
    if excess:
        print(f"\nExcess materials (already in batch, CANNOT REMOVE):")
        worst_ratio = 0
        worst_mat = None
        for m, have, need in excess:
            ratio = have / need
            if ratio > worst_ratio:
                worst_ratio = ratio
                worst_mat = m
            print(f"  • {m}: have {have:.1f}, need {need:.1f} — {ratio:.1f}x excess")
        
        print(f"\n  >> WORST EXCESS: {worst_mat} ({worst_ratio:.1f}x too much)")
        print(f"  >> This is your REAL limiting factor — it will always diverge from true DHC A")
    
    # Short materials
    short = [(m, EXISTING[m], total_conc * (FORMULA[m] / 100)) 
             for m in FORMULA if m in EXISTING and 0 < EXISTING[m] < total_conc * (FORMULA[m] / 100)]
    if short:
        print(f"\nShort materials (need to add more):")
        for m, have, need in short:
            print(f"  • {m}: have {have:.1f}, need {need:.1f} — add {need-have:.1f} µL")

print("\n" + "=" * 70)
print("BOTTOM LINE")
print("=" * 70)
print("""
Your 30 mL batch has TWO types of limiting problems:

1. MISSING materials (need to add):
   → Galaxolide, Alpha Irone, Habanolide, DHM, Lime EO, Aldehyde C10, Citral
   → EASY FIX: just add them

2. EXCESS materials (CANNOT REMOVE):
   → Petitgrain EO: 330 µL in batch, DHC A wants only 48–80 µL
     = 4–7x TOO MUCH. Will always add green-bitter note.
   
   → Iso E Super: 300 µL in batch, DHC A wants 0
     = INFINITY x too much. Will always add woody background.

THE REAL LIMITING INGREDIENT: Petitgrain EO
  - It's the most dramatically overshot material
  - It changes the character from "clean citrus-musk" to "green woody citrus"
  - Cannot be removed from mixed batch
  - At 50 mL dilution: 330 µL / 6000 µL = 5.5% of concentrate
    (DHC A wants only 0.8%)
""")
