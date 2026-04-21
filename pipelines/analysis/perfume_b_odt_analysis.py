"""Perfume B (Iris-Muguet 30mL) — ODT Audit & Direction A Optimization

Full analysis:
  1. Retroactive audit of ALL materials (base + first layer + MIG correction)
  2. ODT-validated Direction A (Hedione) optimization
  3. Gap analysis — what's missing from the composition
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

from engine.temporal_graph import get_odt, _ODT_LITERATURE
from engine.ingredient_intelligence import get_profile

# ═══════════════════════════════════════════════════════════════════════════
# COMPOSITION — Perfume B: Iris-Muguet 30mL
# ═══════════════════════════════════════════════════════════════════════════

BATCH_SIZE_ML = 30.0
BATCH_SIZE_UL = 30_000.0

# Mixture suppression: in a complex formula, effective threshold
# is 3-10× the pure ODT (Laing & Francis, 1989).  Using 5× standard.
MIXTURE_SUPPRESSION = 5.0

# ── Base composition (estimated high doses — user said "quite high") ──
# Format: (name, amount_µL, dilution_factor, note_about_dilution)
BASE_MATERIALS = [
    ("Alpha Ionone",             400,  1.0,   "neat"),
    ("Beta Ionone",              200,  1.0,   "neat"),
    ("Alpha-Isomethyl Ionone",   500,  1.0,   "neat — AIMI"),
    ("Dihydro Beta Ionone",      150,  1.0,   "neat — DHBI"),
    ("Ultralia",                  80,  1.0,   "neat"),
    ("Methyl Ionone",            500,  1.0,   "neat — Methyl Ionone Gamma"),
    ("Hydroxycitronellal",       500,  1.0,   "neat"),
    ("Cyclamen Aldehyde",         80,  1.0,   "neat"),
]

# ── First layer additions (exact doses from our session) ──
FIRST_LAYER = [
    ("Bourgeonal",                10,  1.0,   "neat"),
    ("Lilyreal ND",               15,  1.0,   "neat"),
    ("Helional",                  10,  1.0,   "neat"),
    ("Nympheal",                   8,  1.0,   "neat"),
    ("Allyl Ionone",               5,  1.0,   "neat — Ketone V"),
    ("Irotyl",                    20,  1.0,   "neat"),
    ("Violet Fleuressence",       10,  1.0,   "neat"),
    ("Carrot Seed EO",            60,  0.10,  "10% dilution"),
    ("Freesia HDI",               12,  1.0,   "neat"),
]

# ── MIG correction ──
MIG_CORRECTION = [
    ("Methyl Ionone",             30,  1.0,   "neat — cold balance restoration"),
]

# Combine all
ALL_MATERIALS = BASE_MATERIALS + FIRST_LAYER + MIG_CORRECTION

# ── Direction A (proposed) ──
DIRECTION_A = [
    ("Hedione",                  300,  1.0,   "neat — radiance amplifier"),
]

# ── Direction B (proposed) ──
DIRECTION_B = [
    ("Orivone",                   40,  1.0,   "neat — warm orris butter"),
    ("Javanol",                   40,  1.0,   "neat — premium sandalwood"),
    ("Iso E Super",               80,  1.0,   "neat — molecular cocoon cedar"),
    ("Coumarin",                  50,  0.20,  "20% dilution"),
    ("Indole",                    12,  0.10,  "10% dilution"),
]

# ── Direction C (proposed) ──
DIRECTION_C = [
    ("Habanolide",                80,  1.0,   "neat — macrocyclic white musk"),
    ("Cyclamen Aldehyde",         15,  1.0,   "neat — metallic green edge"),
]


def calc_concentration(amount_ul: float, dilution: float,
                       batch_ul: float = BATCH_SIZE_UL) -> dict:
    """Calculate concentration metrics for a material.
    
    Returns: active_ul, ppm_in_solution, percent_of_total
    """
    active_ul = amount_ul * dilution
    ppm = (active_ul / batch_ul) * 1_000_000
    pct = (active_ul / batch_ul) * 100
    return {
        "active_ul": active_ul,
        "ppm": ppm,
        "pct": pct,
    }


def get_odt_ppb(name: str) -> float:
    """Get ODT in ppb from the literature database."""
    # Try exact match first
    odt = _ODT_LITERATURE.get(name)
    if odt is not None:
        return odt
    # Try case-insensitive partial match
    name_lower = name.lower()
    for key, val in _ODT_LITERATURE.items():
        if key.lower() == name_lower:
            return val
        if name_lower in key.lower() or key.lower() in name_lower:
            return val
    # Fallback: use get_odt which tries profile estimation
    profile = get_profile(name)
    return get_odt(name, profile)


def analyze_material(name: str, amount_ul: float, dilution: float,
                     note: str = "") -> dict:
    """Full ODT analysis for a single material."""
    conc = calc_concentration(amount_ul, dilution)
    odt_ppb = get_odt_ppb(name)
    
    # ODT in ethanol solution (approximate conversion from air ODT)
    # The odor_thresholds.py has dual data — use ethanol values where available
    from engine.odor_thresholds import ODT_DATA
    odt_eth_lookup = None
    for key, data in ODT_DATA.items():
        if key.lower() in name.lower() or name.lower() in key.lower():
            odt_eth_lookup = data.get("odt_eth")
            break
    
    # If we have ethanol ODT, use it directly for in-solution analysis
    # Otherwise estimate: ODT_ethanol ≈ ODT_air × 100 (rough conversion)
    if odt_eth_lookup:
        odt_eth_ppm = odt_eth_lookup
    else:
        odt_eth_ppm = odt_ppb * 0.1  # rough: 1 ppb air ≈ 0.1 ppm ethanol
    
    # Effective threshold with mixture suppression
    effective_threshold_ppm = odt_eth_ppm * MIXTURE_SUPPRESSION
    
    # Odor Activity Value in solution
    if effective_threshold_ppm > 0:
        oav = conc["ppm"] / effective_threshold_ppm
    else:
        oav = float("inf")
    
    # Status classification
    if oav >= 3.0:
        status = "STRONG"
    elif oav >= 1.0:
        status = "FUNCTIONAL"
    elif oav >= 0.3:
        status = "MARGINAL"
    elif oav >= 0.1:
        status = "SUB-THRESHOLD"
    else:
        status = "WASTED"
    
    return {
        "name": name,
        "amount_ul": amount_ul,
        "dilution": dilution,
        "active_ul": conc["active_ul"],
        "ppm": conc["ppm"],
        "pct": conc["pct"],
        "odt_air_ppb": odt_ppb,
        "odt_eth_ppm": odt_eth_ppm,
        "effective_threshold_ppm": effective_threshold_ppm,
        "oav": oav,
        "status": status,
        "note": note,
    }


def print_section(title: str, materials: list[tuple], all_results: list[dict] = None):
    """Analyze and print a section of materials."""
    if all_results is None:
        all_results = []
    
    print(f"\n{'═' * 80}")
    print(f"  {title}")
    print(f"{'═' * 80}")
    print(f"{'Material':<28} {'µL':>5} {'Dil':>5} {'Active':>7} "
          f"{'ppm':>8} {'ODT_eth':>8} {'Eff.Thr':>8} {'OAV':>7} {'Status':<14}")
    print(f"{'─' * 28} {'─' * 5} {'─' * 5} {'─' * 7} "
          f"{'─' * 8} {'─' * 8} {'─' * 8} {'─' * 7} {'─' * 14}")
    
    section_results = []
    for name, amount, dilution, note in materials:
        result = analyze_material(name, amount, dilution, note)
        section_results.append(result)
        all_results.append(result)
        
        status_marker = {
            "STRONG": "★★★",
            "FUNCTIONAL": "★★ ",
            "MARGINAL": "★  ",
            "SUB-THRESHOLD": "⚠  ",
            "WASTED": "✗  ",
        }.get(result["status"], "?  ")
        
        print(f"{result['name']:<28} {result['amount_ul']:>5.0f} "
              f"{result['dilution']:>5.2f} {result['active_ul']:>7.1f} "
              f"{result['ppm']:>8.1f} {result['odt_eth_ppm']:>8.2f} "
              f"{result['effective_threshold_ppm']:>8.1f} "
              f"{result['oav']:>7.2f} {status_marker} {result['status']}")
    
    return section_results


def gap_analysis(all_results: list[dict]):
    """Identify what's missing from the composition."""
    print(f"\n{'═' * 80}")
    print(f"  GAP ANALYSIS — What's Missing?")
    print(f"{'═' * 80}")
    
    # Define essential perfumery registers
    registers = {
        "RADIANCE / DIFFUSION": {
            "present": [],
            "candidates": ["Hedione"],
            "status": "MISSING",
        },
        "MUSK / TRAIL": {
            "present": [],
            "candidates": ["Habanolide", "Galaxolide", "Ethylene Brassylate"],
            "status": "MISSING",
        },
        "WOODY STRUCTURE": {
            "present": [],
            "candidates": ["Iso E Super", "Cashmeran", "Cedarwood EO"],
            "status": "MISSING",
        },
        "AMBER / WARMTH": {
            "present": [],
            "candidates": ["Ambrox Super", "Coumarin", "Benzoin"],
            "status": "MISSING",
        },
        "SANDALWOOD / SKIN": {
            "present": [],
            "candidates": ["Javanol", "Ebanol", "Bacdanol"],
            "status": "MISSING",
        },
        "FIXATIVE / BODY": {
            "present": [],
            "candidates": ["Benzyl Benzoate", "Hexyl Salicylate"],
            "status": "MISSING",
        },
        "ANIMALIC / DEPTH": {
            "present": [],
            "candidates": ["Indole", "Civet reconstitution"],
            "status": "MISSING",
        },
    }
    
    material_names = {r["name"].lower() for r in all_results}
    
    # Check iris/violet register
    iris_mats = [r for r in all_results 
                 if any(k in r["name"].lower() for k in 
                        ["ionone", "irone", "ultralia", "irotyl", "orivone",
                         "methyl ionone", "violet", "carrot"])]
    
    # Check muguet register
    muguet_mats = [r for r in all_results
                   if any(k in r["name"].lower() for k in
                          ["hydroxycitronellal", "bourgeonal", "lilyreal",
                           "helional", "nympheal", "freesia"])]
    
    # Check each register
    for reg_name, reg_info in registers.items():
        for r in all_results:
            for candidate in reg_info["candidates"]:
                if candidate.lower() in r["name"].lower():
                    reg_info["present"].append(r["name"])
                    if r["oav"] >= 1.0:
                        reg_info["status"] = "COVERED"
                    elif r["oav"] >= 0.3:
                        reg_info["status"] = "MARGINAL"
                    else:
                        reg_info["status"] = "BELOW THRESHOLD"
    
    print(f"\n  Iris/Violet register: {len(iris_mats)} materials, "
          f"{sum(1 for m in iris_mats if m['status'] in ('STRONG', 'FUNCTIONAL'))} functional")
    print(f"  Muguet register: {len(muguet_mats)} materials, "
          f"{sum(1 for m in muguet_mats if m['status'] in ('STRONG', 'FUNCTIONAL'))} functional")
    
    print(f"\n  {'Register':<30} {'Status':<20} {'Materials Present'}")
    print(f"  {'─' * 30} {'─' * 20} {'─' * 30}")
    for reg_name, reg_info in registers.items():
        present_str = ", ".join(reg_info["present"]) if reg_info["present"] else "—"
        print(f"  {reg_name:<30} {reg_info['status']:<20} {present_str}")


def direction_optimization(direction_materials: list[tuple], 
                           existing_results: list[dict],
                           direction_name: str):
    """Optimize a direction's doses based on ODT analysis."""
    print(f"\n{'═' * 80}")
    print(f"  DIRECTION {direction_name} — ODT-VALIDATED OPTIMIZATION")
    print(f"{'═' * 80}")
    
    optimized = []
    for name, amount, dilution, note in direction_materials:
        result = analyze_material(name, amount, dilution, note)
        
        # Check if this material already exists in the composition
        existing = [r for r in existing_results if r["name"].lower() == name.lower()]
        
        if existing:
            existing_ppm = sum(r["ppm"] for r in existing)
            total_ppm = existing_ppm + result["ppm"]
            effective_threshold = result["effective_threshold_ppm"]
            combined_oav = total_ppm / effective_threshold if effective_threshold > 0 else float("inf")
            
            print(f"\n  {name}: ALREADY IN BOTTLE at {existing_ppm:.1f} ppm")
            print(f"    Adding {amount} µL → +{result['ppm']:.1f} ppm → total {total_ppm:.1f} ppm")
            print(f"    Combined OAV: {combined_oav:.2f} (threshold: {effective_threshold:.1f} ppm)")
        else:
            print(f"\n  {name}: NEW ADDITION")
            print(f"    {amount} µL {'(' + note + ')' if note else ''}")
            print(f"    Conc: {result['ppm']:.1f} ppm | ODT_eth: {result['odt_eth_ppm']:.2f} ppm")
            print(f"    Eff. threshold (×{MIXTURE_SUPPRESSION:.0f}): {result['effective_threshold_ppm']:.1f} ppm")
            print(f"    OAV: {result['oav']:.2f} → {result['status']}")
        
        # Optimization recommendation
        if result["oav"] < 0.3:
            # Sub-threshold — increase dose
            min_ul = (result["effective_threshold_ppm"] / 1_000_000) * BATCH_SIZE_UL / max(dilution, 0.01)
            recommended = max(min_ul * 1.5, amount * 3)  # 1.5× threshold for safety
            print(f"    ⚠ SUB-THRESHOLD: Increase to {recommended:.0f} µL minimum")
            optimized.append((name, recommended, dilution, note))
        elif result["oav"] > 10.0:
            # Over-saturated — could reduce
            reduced = amount * (3.0 / result["oav"])
            print(f"    ↓ OVER-DOSED: Could reduce to {reduced:.0f} µL and still be 3× threshold")
            optimized.append((name, amount, dilution, note))  # keep original unless user wants to reduce
        else:
            print(f"    ✓ DOSE IS GOOD")
            optimized.append((name, amount, dilution, note))
    
    return optimized


def main():
    print("=" * 80)
    print("  PERFUME B: IRIS-MUGUET 30mL — ODT AUDIT & OPTIMIZATION")
    print("  Batch: 30 mL | Mixture suppression: 5×")
    print("  Base amounts estimated (user: 'quite high')")
    print("=" * 80)
    
    all_results = []
    
    # ── 1. Retroactive audit ──
    base_results = print_section(
        "RETROACTIVE AUDIT — BASE COMPOSITION (estimated amounts)",
        BASE_MATERIALS, all_results)
    
    layer1_results = print_section(
        "RETROACTIVE AUDIT — FIRST LAYER ADDITIONS (exact doses)",
        FIRST_LAYER, all_results)
    
    mig_results = print_section(
        "MIG CORRECTION",
        MIG_CORRECTION, all_results)
    
    # ── Summary statistics ──
    print(f"\n{'═' * 80}")
    print(f"  SUMMARY — Current Composition")
    print(f"{'═' * 80}")
    
    total_active_ul = sum(r["active_ul"] for r in all_results)
    functional_count = sum(1 for r in all_results if r["status"] in ("STRONG", "FUNCTIONAL"))
    marginal_count = sum(1 for r in all_results if r["status"] == "MARGINAL")
    sub_count = sum(1 for r in all_results if r["status"] == "SUB-THRESHOLD")
    wasted_count = sum(1 for r in all_results if r["status"] == "WASTED")
    
    # Aggregate duplicate materials (MIG correction adds to existing Methyl Ionone)
    aggregated = {}
    for r in all_results:
        key = r["name"]
        if key in aggregated:
            aggregated[key]["active_ul"] += r["active_ul"]
            aggregated[key]["ppm"] += r["ppm"]
            aggregated[key]["amount_ul"] += r["amount_ul"]
            # Recalculate OAV
            if aggregated[key]["effective_threshold_ppm"] > 0:
                aggregated[key]["oav"] = aggregated[key]["ppm"] / aggregated[key]["effective_threshold_ppm"]
        else:
            aggregated[key] = dict(r)
    
    print(f"\n  Total active concentrate: {total_active_ul:.0f} µL ({total_active_ul/BATCH_SIZE_UL*100:.2f}%)")
    print(f"  Unique materials: {len(aggregated)}")
    print(f"  STRONG (OAV ≥ 3): {functional_count} materials")
    print(f"  FUNCTIONAL (OAV 1-3): {marginal_count} materials (these I may be double counting)")
    
    # Recount from aggregated
    agg_list = list(aggregated.values())
    for r in agg_list:
        if r["oav"] >= 3.0:
            r["status"] = "STRONG"
        elif r["oav"] >= 1.0:
            r["status"] = "FUNCTIONAL"
        elif r["oav"] >= 0.3:
            r["status"] = "MARGINAL"
        elif r["oav"] >= 0.1:
            r["status"] = "SUB-THRESHOLD"
        else:
            r["status"] = "WASTED"
    
    print(f"\n  AGGREGATED STATUS (after combining duplicates):")
    print(f"  {'Material':<28} {'Total ppm':>9} {'Eff.Thr':>8} {'OAV':>7} {'Status':<14}")
    print(f"  {'─' * 28} {'─' * 9} {'─' * 8} {'─' * 7} {'─' * 14}")
    for r in sorted(agg_list, key=lambda x: x["oav"], reverse=True):
        status_marker = {
            "STRONG": "★★★",
            "FUNCTIONAL": "★★ ",
            "MARGINAL": "★  ",
            "SUB-THRESHOLD": "⚠  ",
            "WASTED": "✗  ",
        }.get(r["status"], "?  ")
        print(f"  {r['name']:<28} {r['ppm']:>9.1f} {r['effective_threshold_ppm']:>8.1f} "
              f"{r['oav']:>7.2f} {status_marker} {r['status']}")
    
    # ── 2. Problem materials ──
    problems = [r for r in agg_list if r["status"] in ("SUB-THRESHOLD", "WASTED")]
    marginals = [r for r in agg_list if r["status"] == "MARGINAL"]
    
    if problems:
        print(f"\n  ⚠ PROBLEM MATERIALS — below effective threshold:")
        for r in problems:
            min_ppm = r["effective_threshold_ppm"]
            min_ul = (min_ppm / 1_000_000) * BATCH_SIZE_UL / max(r["dilution"], 0.01)
            print(f"    {r['name']}: at {r['ppm']:.1f} ppm, need {min_ppm:.1f} ppm "
                  f"(increase to ~{min_ul:.0f} µL)")
    
    if marginals:
        print(f"\n  ★ MARGINAL MATERIALS — perceptible but weak:")
        for r in marginals:
            target_ppm = r["effective_threshold_ppm"] * 2  # 2× threshold
            target_ul = (target_ppm / 1_000_000) * BATCH_SIZE_UL / max(r["dilution"], 0.01)
            print(f"    {r['name']}: OAV {r['oav']:.2f} — boost to ~{target_ul:.0f} µL for solid function")
    
    # ── 3. Direction A optimization ──
    direction_optimization(DIRECTION_A, all_results, "A — RADIANCE (Hedione)")
    
    # ── 4. Direction B optimization ──
    direction_optimization(DIRECTION_B, all_results, "B — DEPTH & SKIN")
    
    # ── 5. Direction C optimization ──
    direction_optimization(DIRECTION_C, all_results, "C — TRAIL & EDGE")
    
    # ── 6. Gap analysis ──
    gap_analysis(all_results)
    
    # ── 7. Final recommendation ──
    print(f"\n{'═' * 80}")
    print(f"  FINAL OPTIMIZED DIRECTION A+B+C RECIPE")
    print(f"{'═' * 80}")
    
    # Combine all directions and show optimized amounts
    all_directions = DIRECTION_A + DIRECTION_B + DIRECTION_C
    total_addition = 0
    print(f"\n  {'Material':<28} {'Proposed':>8} {'Dil':>5} {'Active µL':>9} {'ppm':>8} {'OAV':>7}")
    print(f"  {'─' * 28} {'─' * 8} {'─' * 5} {'─' * 9} {'─' * 8} {'─' * 7}")
    for name, amount, dilution, note in all_directions:
        result = analyze_material(name, amount, dilution, note)
        # Check for existing material
        existing_ppm = sum(r["ppm"] for r in all_results if r["name"].lower() == name.lower())
        total_ppm = existing_ppm + result["ppm"]
        eff_thr = result["effective_threshold_ppm"]
        combined_oav = total_ppm / eff_thr if eff_thr > 0 else float("inf")
        
        total_addition += amount
        existing_note = f" (+{existing_ppm:.0f} existing)" if existing_ppm > 0 else ""
        print(f"  {name:<28} {amount:>7.0f} {dilution:>5.2f} {result['active_ul']:>9.1f} "
              f"{result['ppm']:>8.1f} {combined_oav:>7.2f}{existing_note}")
    
    print(f"\n  Total Direction A+B+C addition: {total_addition} µL")
    print(f"  New concentrate total: {total_active_ul + sum(calc_concentration(a, d)['active_ul'] for _, a, d, _ in all_directions):.0f} µL")


if __name__ == "__main__":
    main()
