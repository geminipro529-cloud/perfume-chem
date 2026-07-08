"""DHC Lemon OAV Correction Calculator.

Calculates exact additions to shift existing batch toward DHC A OAV profile.
Shows OAV before/after for every material.
Honest about what can and cannot be fixed.
"""

import sys

PPM = 20.0

# Material properties: (VP_Pa, ODT_ppb)
PROPS = {
    "Lemon FCF oil Sicilian": (2.500, 10.0),
    "Lime Distilled EO": (1.800, 12.0),
    "Aldehyde C10 (1%)": (0.010, 0.5),  # active properties
    "Citral": (0.050, 5.0),
    "Petitgrain EO": (6.000, 4.0),
    "Hedione": (0.089, 0.05),
    "Hedione HC": (0.089, 0.05),
    "Ethyl Linalool": (0.080, 1.5),
    "Linalyl Acetate": (17.500, 50.0),
    "Dihydromyrcenol": (14.800, 1.0),
    "Alpha Irone": (0.559, 0.9),
    "Galaxolide": (0.0727, 0.05),
    "Habanolide": (0.0001, 0.5),
    "Ambrofix": (0.050, 0.3),
    # Bad materials (existing only)
    "Iso E Super": (0.231, 0.05),
    "Romandolide": (0.100, 4.9),
    "Ethylene Brassylate": (0.008, 0.97),
    "Norlimbanol Dextro": (0.067, 0.5),
    "Vetival": (6.530, 2.0),
    "Javanol": (0.030, 0.0016),
    "Cardamom EO": (15.000, 3.0),
    "Hydroxycitronellal": (0.010, 15.0),
    "Nympheal": (0.010, 2.0),
    "Scentenal": (0.010, 0.5),
    "Floralozone": (0.431, 0.5),
}

def oav(active, vp, odt):
    return active * vp * PPM / odt if odt > 0 else 0

# Your existing 30 mL batch (active µL)
EXISTING = {
    "Lemon FCF oil Sicilian": 3900.0,
    "Hedione": 630.0,
    "Hedione HC": 270.0,
    "Ethyl Linalool": 330.0,
    "Linalyl Acetate": 48.0,
    "Petitgrain EO": 330.0,
    "Ambrofix": 10.8,
    # Bad materials
    "Iso E Super": 300.0,
    "Romandolide": 288.0,
    "Ethylene Brassylate": 228.0,
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
DHC_A_FORMULA = {
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

GOOD_MATERIALS = set(DHC_A_FORMULA.keys())

def calculate_profile(active_dict):
    """Calculate OAV profile from active amounts."""
    profile = {}
    for mat, active in active_dict.items():
        if mat in PROPS:
            vp, odt = PROPS[mat]
            profile[mat] = oav(active, vp, odt)
    return profile

def analyze_correction(target_mL):
    total_conc = target_mL * 0.12 * 1000
    
    # Calculate target active amounts
    target_active = {}
    for mat, pct in DHC_A_FORMULA.items():
        target_active[mat] = total_conc * (pct / 100)
    
    # Calculate additions needed
    additions = {}
    for mat, target in target_active.items():
        have = EXISTING.get(mat, 0)
        if target > have:
            additions[mat] = target - have
    
    # Simulate final batch
    final_active = dict(EXISTING)
    for mat, add in additions.items():
        final_active[mat] = final_active.get(mat, 0) + add
    
    # Calculate OAV profiles
    existing_oav = calculate_profile(EXISTING)
    target_oav = calculate_profile(target_active)
    final_oav = calculate_profile(final_active)
    
    existing_total = sum(existing_oav.values())
    target_total = sum(target_oav.values())
    final_total = sum(final_oav.values())
    
    existing_good = sum(v for m, v in existing_oav.items() if m in GOOD_MATERIALS)
    existing_bad = existing_total - existing_good
    
    final_good = sum(v for m, v in final_oav.items() if m in GOOD_MATERIALS)
    final_bad = final_total - final_good
    
    return {
        "target_mL": target_mL,
        "total_conc": total_conc,
        "additions": additions,
        "target_active": target_active,
        "existing_oav": existing_oav,
        "target_oav": target_oav,
        "final_oav": final_oav,
        "existing_total": existing_total,
        "target_total": target_total,
        "final_total": final_total,
        "existing_good_pct": existing_good / existing_total * 100 if existing_total > 0 else 0,
        "final_good_pct": final_good / final_total * 100 if final_total > 0 else 0,
        "existing_bad_pct": existing_bad / existing_total * 100 if existing_total > 0 else 0,
        "final_bad_pct": final_bad / final_total * 100 if final_total > 0 else 0,
    }

def print_analysis(result):
    r = result
    print(f"\n{'='*75}")
    print(f"DHC LEMON CORRECTION: 30 mL existing -> {r['target_mL']} mL final")
    print(f"{'='*75}")
    
    print(f"\nCONCENTRATION")
    print(f"  Target: 12% v/v = {r['total_conc']:.0f} µL active concentrate")
    
    print(f"\nOAV COMPARISON")
    print(f"  {'Material':<28} {'ExistOAV':>10} {'TargetOAV':>10} {'FinalOAV':>10} {'Exist%':>8} {'Target%':>8} {'Final%':>8}")
    print(f"  {'-'*75}")
    
    # Sort by target OAV descending
    sorted_mats = sorted(r['target_oav'].keys(), key=lambda m: r['target_oav'][m], reverse=True)
    
    for mat in sorted_mats:
        e = r['existing_oav'].get(mat, 0)
        t = r['target_oav'].get(mat, 0)
        f = r['final_oav'].get(mat, 0)
        ep = e / r['existing_total'] * 100 if r['existing_total'] > 0 else 0
        tp = t / r['target_total'] * 100 if r['target_total'] > 0 else 0
        fp = f / r['final_total'] * 100 if r['final_total'] > 0 else 0
        print(f"  {mat:<28} {e:>10,.0f} {t:>10,.0f} {f:>10,.0f} {ep:>7.1f}% {tp:>7.1f}% {fp:>7.1f}%")
    
    # Bad materials
    print(f"  {'-'*75}")
    print(f"  {'BAD MATERIALS (cannot remove)':<28}")
    bad_mats = [m for m in r['existing_oav'] if m not in GOOD_MATERIALS]
    for mat in sorted(bad_mats, key=lambda m: r['existing_oav'][m], reverse=True):
        e = r['existing_oav'][mat]
        f = r['final_oav'][mat]
        ep = e / r['existing_total'] * 100
        fp = f / r['final_total'] * 100
        print(f"  {mat:<28} {e:>10,.0f} {'—':>10} {f:>10,.0f} {ep:>7.1f}% {'—':>8} {fp:>7.1f}%")
    
    print(f"  {'-'*75}")
    print(f"  {'TOTAL':<28} {r['existing_total']:>10,.0f} {r['target_total']:>10,.0f} {r['final_total']:>10,.0f}")
    
    print(f"\nGOOD vs BAD RATIOS")
    print(f"  Existing: {r['existing_good_pct']:.1f}% good / {r['existing_bad_pct']:.1f}% bad")
    print(f"  Target:   100.0% good / 0.0% bad")
    print(f"  Final:    {r['final_good_pct']:.1f}% good / {r['final_bad_pct']:.1f}% bad")
    
    print(f"\nMATERIALS TO ADD")
    if r['additions']:
        print(f"  {'Material':<28} {'ActiveµL':>10} {'StockµL':>10} {'Stock':>12}")
        print(f"  {'-'*62}")
        for mat, active in sorted(r['additions'].items(), key=lambda x: x[1], reverse=True):
            stock_frac = STOCK_DILUTION.get(mat, 1.0)
            raw = active / stock_frac
            label = f"{stock_frac*100:.0f}% stock" if stock_frac < 1.0 else "neat"
            print(f"  {mat:<28} {active:>10.1f} {raw:>10.1f} {label:>12}")
    else:
        print("  Nothing to add")
    
    print(f"\nBOTTOM LINE")
    if r['final_bad_pct'] < 10:
        print(f"  EXCELLENT: Bad materials only {r['final_bad_pct']:.1f}% of OAV")
    elif r['final_bad_pct'] < 20:
        print(f"  GOOD: Bad materials {r['final_bad_pct']:.1f}% of OAV — woody/green undertone present but subdued")
    elif r['final_bad_pct'] < 30:
        print(f"  FAIR: Bad materials {r['final_bad_pct']:.1f}% of OAV — will smell like 'green woody DHC'")
    else:
        print(f"  POOR: Bad materials {r['final_bad_pct']:.1f}% of OAV — still dominated by original character")
    
    print(f"\n  The biggest remaining divergence:")
    bad_mats = [(m, r['final_oav'][m]) for m in r['final_oav'] if m not in GOOD_MATERIALS]
    worst = max(bad_mats, key=lambda x: x[1])
    print(f"    -> {worst[0]}: {worst[1]:,.0f} OAV ({worst[1]/r['final_total']*100:.1f}% of total)")
    print(f"    -> Cannot be removed. Only dilution + massive additions can suppress it.")

if __name__ == "__main__":
    volumes = [40, 50, 60, 80, 100]
    if len(sys.argv) > 1:
        volumes = [float(sys.argv[1])]
    
    for v in volumes:
        result = analyze_correction(v)
        print_analysis(result)
