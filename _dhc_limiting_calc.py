"""DHC A Lemon — Limiting Ingredient Calculator.

Input your available stock for each material (in µL). 
The script finds the limiting ingredient and calculates max batch size.
"""

import sys

# DHC A Lemon formula: % of concentrate
FORMULA = {
    "Lemon FCF oil Sicilian": 61.09,
    "Lime Distilled EO": 3.00,
    "Aldehyde C10 (1%)": 0.08,  # this is % of concentrate, but stock is 1%
    "Citral": 0.03,
    "Petitgrain EO": 0.80,
    "Hedione": 10.00,
    "Hedione HC": 2.00,
    "Ethyl Linalool": 4.00,
    "Linalyl Acetate": 2.00,
    "Dihydromyrcenol": 3.00,
    "Alpha Irone": 1.50,  # stock is 30% in DEP
    "Galaxolide": 8.00,  # stock is 50% in DEP
    "Habanolide": 2.00,
    "Ambrofix": 2.50,  # stock is 30% w/v
}

# Stock concentration: material -> stock fraction
STOCK_CONC = {
    "Aldehyde C10 (1%)": 0.01,
    "Alpha Irone": 0.30,
    "Galaxolide": 0.50,
    "Ambrofix": 0.30,
}

# Default assumption: most perfumers have plenty of synthetics,
# but natural oils are limiting. Here are TYPICAL working stock sizes.
# Change these to match YOUR actual inventory.
DEFAULT_STOCK = {
    "Lemon FCF oil Sicilian": 5000,   # 5 mL — natural oil, often limiting
    "Lime Distilled EO": 2000,        # 2 mL
    "Aldehyde C10 (1%)": 1000,        # 1 mL of 1% stock
    "Citral": 500,
    "Petitgrain EO": 2000,
    "Hedione": 10000,                 # 10 mL — synthetic, usually plenty
    "Hedione HC": 5000,
    "Ethyl Linalool": 5000,
    "Linalyl Acetate": 5000,
    "Dihydromyrcenol": 5000,
    "Alpha Irone": 1000,              # 1 mL of 30% stock = 300 µL active
    "Galaxolide": 5000,               # 5 mL of 50% stock = 2500 µL active
    "Habanolide": 2000,
    "Ambrofix": 2000,                 # 2 mL of 30% stock = 600 µL active
}

def calculate_max_batch(stock_dict):
    """Find limiting ingredient and max batch size."""
    
    limiting = None
    max_batch_active = float('inf')
    
    print("\nStock Analysis:")
    print(f"{'Material':<30} {'StockµL':>10} {'Stock%':>8} {'Need%':>8} {'Ratio':>10} {'Status':>12}")
    print("-" * 85)
    
    for material, need_pct in FORMULA.items():
        stock_raw = stock_dict.get(material, 0)
        stock_frac = STOCK_CONC.get(material, 1.0)
        stock_active = stock_raw * stock_frac
        
        # How much total concentrate can we make with this stock?
        # need_pct% of total_concentrate = stock_active
        # total_concentrate = stock_active / (need_pct / 100)
        possible_conc = stock_active / (need_pct / 100)
        
        ratio = stock_active / (need_pct / 100)  # same as possible_conc
        
        is_limiting = possible_conc < max_batch_active
        if is_limiting:
            max_batch_active = possible_conc
            limiting = material
        
        status = "LIMITING" if is_limiting else "OK"
        print(f"{material:<30} {stock_raw:>10.1f} {stock_frac*100:>7.1f}% {need_pct:>7.2f}% {possible_conc:>9.1f} {status:>12}")
    
    print("-" * 85)
    
    # Max batch volume at 12% concentration
    max_batch_volume_ml = max_batch_active / 1000 / 0.12
    
    print(f"\nLIMITING INGREDIENT: {limiting}")
    print(f"Max concentrate (active): {max_batch_active:.1f} µL")
    print(f"Max batch volume (at 12%): {max_batch_volume_ml:.1f} mL")
    
    return limiting, max_batch_active, max_batch_volume_ml

def print_batch_recipe(total_concentrate_active):
    """Print exact recipe for the max batch size."""
    
    volume_ml = total_concentrate_active / 1000 / 0.12
    
    print(f"\n{'='*60}")
    print(f"DHC A LEMON RECIPE — {volume_ml:.1f} mL batch")
    print(f"{'='*60}")
    print(f"Concentration: 12% v/v")
    print(f"Total concentrate (active): {total_concentrate_active:.1f} µL")
    print(f"\n{'Material':<30} {'Active%':>8} {'ActiveµL':>10} {'StockµL':>10} {'Notes':>15}")
    print("-" * 80)
    
    total_raw = 0
    for material, need_pct in FORMULA.items():
        active = total_concentrate_active * (need_pct / 100)
        stock_frac = STOCK_CONC.get(material, 1.0)
        raw = active / stock_frac
        note = f"{stock_frac*100:.0f}% stock" if stock_frac < 1.0 else "neat"
        print(f"{material:<30} {need_pct:>7.2f}% {active:>9.1f} {raw:>9.1f} {note:>15}")
        total_raw += raw
    
    print("-" * 80)
    ethanol = volume_ml - (total_raw / 1000)
    print(f"{'Ethanol 96%':<30} {'':>8} {'':>10} {ethanol*1000:>9.1f} {'neat':>15}")
    print(f"\n{'TOTAL':<30} {'100.00%':>8} {total_concentrate_active:>9.1f} {total_raw:>9.1f}")
    print(f"Final volume: {volume_ml:.1f} mL")
    print(f"\nInstructions:")
    print(f"1. Add all concentrate materials to bottle")
    print(f"2. Add ethanol to {volume_ml:.1f} mL line")
    print(f"3. Cap and invert 50x")
    print(f"4. Macerate 4 weeks")

if __name__ == "__main__":
    print("DHC A Lemon — Limiting Ingredient Calculator")
    print("=" * 60)
    
    # Check if user provided stock amounts
    if len(sys.argv) > 1 and sys.argv[1] == "--custom":
        print("\nEnter your available stock in µL (or 0 if none):")
        custom_stock = {}
        for material in FORMULA:
            val = input(f"  {material}: ").strip()
            custom_stock[material] = float(val) if val else 0
        limiting, conc, vol = calculate_max_batch(custom_stock)
        print_batch_recipe(conc)
    else:
        print("\nUsing DEFAULT stock assumptions (edit script to change):")
        limiting, conc, vol = calculate_max_batch(DEFAULT_STOCK)
        print_batch_recipe(conc)
        
        print(f"\n{'='*60}")
        print("To use YOUR actual stock amounts, run:")
        print("  python _dhc_limiting_calc.py --custom")
        print(f"{'='*60}")
