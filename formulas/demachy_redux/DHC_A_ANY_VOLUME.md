# DHC A Lemon — Any Volume Recipe

> **Target volume can be anything.** 10 mL. 30 mL. 47 mL. 100 mL. The math scales perfectly.

## The Rule

**Concentration = 12% v/v**  
For any target volume **V** (in mL):

```
Total concentrate = 0.12 × V × 1000 µL
Each material = %_of_concentrate × Total_concentrate
Ethanol = V − (Total_raw_µL / 1000)
```

---

## Complete Formula (% of Concentrate)

| # | Material | % | Stock | Smell |
|---|----------|---|-------|-------|
| 1 | Lemon FCF oil Sicilian | **61.09%** | neat | Star citrus |
| 2 | Lime Distilled EO | **3.00%** | neat | Anti-candy: green |
| 3 | Galaxolide | **8.00%** | 50% in DEP | Clean white musk |
| 4 | Hedione | **10.00%** | neat | Radiance |
| 5 | Dihydromyrcenol | **3.00%** | neat | Transparency |
| 6 | Ethyl Linalool | **4.00%** | neat | Clean lift |
| 7 | Habanolide | **2.00%** | neat | Skin musk |
| 8 | Ambrofix | **2.50%** | 30% w/v | Amber halo |
| 9 | Hedione HC | **2.00%** | neat | Radiance nuance |
| 10 | Alpha Irone | **1.50%** | 30% in DEP | Iris heart |
| 11 | Linalyl Acetate | **2.00%** | neat | Bright top |
| 12 | Petitgrain EO | **0.80%** | neat | Green edge |
| 13 | Aldehyde C10 | **0.08%** | 1% stock | Pith bite |
| 14 | Citral | **0.03%** | neat | Sharp spike |
| | **TOTAL** | **100.00%** | | |

---

## Worked Examples

### Example 1: 25 mL (pocket atomizer)
```
Total concentrate = 0.12 × 25 × 1000 = 3,000 µL

Lemon FCF      = 61.09% × 3000 = 1,833 µL
Galaxolide     = 8.00% × 3000 = 240 µL active = 480 µL of 50% stock
Alpha Irone    = 1.50% × 3000 = 45 µL active = 150 µL of 30% stock
...etc for all 14 materials

Ethanol ≈ 21.3 mL
```

### Example 2: 47 mL (random bottle size)
```
Total concentrate = 0.12 × 47 × 1000 = 5,640 µL

Lemon FCF      = 61.09% × 5640 = 3,445 µL
Galaxolide     = 8.00% × 5640 = 451 µL active = 902 µL of 50% stock
Alpha Irone    = 1.50% × 5640 = 85 µL active = 282 µL of 30% stock
...etc

Ethanol ≈ 40.2 mL
```

### Example 3: 100 mL (large decant)
```
Total concentrate = 0.12 × 100 × 1000 = 12,000 µL

Lemon FCF      = 61.09% × 12000 = 7,331 µL
Galaxolide     = 8.00% × 12000 = 960 µL active = 1,920 µL of 50% stock
Alpha Irone    = 1.50% × 12000 = 180 µL active = 600 µL of 30% stock
...etc

Ethanol ≈ 85 mL
```

---

## For Your Existing 30 mL Batch

You already have ~6,406 µL active concentrate in 30 mL (~21%).  
To shift to **12% at any volume V** (where V ≥ 30):

### Step 1: Calculate what the final batch needs
```
Final concentrate = 0.12 × V × 1000 µL
Final Lemon FCF   = 61.09% × Final_concentrate
Final Galaxolide  = 8.00% × Final_concentrate
...etc
```

### Step 2: Subtract what you already have
```
Lemon FCF to add  = Final_Lemon_FCF − 3900
Galaxolide to add = Final_Galaxolide − 0
Alpha Irone to add= Final_Alpha_Irone − 0
...etc
```

### Step 3: Add ethanol
```
Ethanol = V − 30 − (Total_raw_to_add / 1000)
```

---

## Quick Calculator

```python
# Paste this into any Python interpreter
V = 50  # <-- change this to any volume in mL

conc = V * 0.12 * 1000  # total concentrate in µL

materials = {
    "Lemon FCF": 61.09,
    "Galaxolide": 8.00,
    "Hedione": 10.00,
    "DHM": 3.00,
    "Ethyl Linalool": 4.00,
    "Habanolide": 2.00,
    "Ambrofix": 2.50,
    "Hedione HC": 2.00,
    "Alpha Irone": 1.50,
    "Linalyl Acetate": 2.00,
    "Lime EO": 3.00,
    "Petitgrain": 0.80,
    "Aldehyde C10": 0.08,
    "Citral": 0.03,
}

for name, pct in materials.items():
    print(f"{name:20s}: {conc * pct/100:6.1f} µL active")
```

---

## Or Use the Script

```bash
# Fresh batch at ANY volume
python _dhc_a_lemon_universal.py 25 0    # 25 mL fresh
python _dhc_a_lemon_universal.py 47 0    # 47 mL fresh
python _dhc_a_lemon_universal.py 100 0   # 100 mL fresh

# Correction from your existing 30 mL to ANY volume
python _dhc_a_lemon_universal.py 40 30   # -> 40 mL
python _dhc_a_lemon_universal.py 50 30   # -> 50 mL
python _dhc_a_lemon_universal.py 75 30   # -> 75 mL
python _dhc_a_lemon_universal.py 100 30  # -> 100 mL
```

The script calculates exact µL for every material automatically.

---

## Summary

| Your Question | Answer |
|--------------|--------|
| Any volume? | **Yes.** Just multiply % by `0.12 × V × 1000` |
| Same concentration? | **Yes.** Always 12% v/v |
| Same smell? | **Yes.** Identical ratios |
| With existing batch? | **Yes.** Subtract what you have, add the rest |

**The formula is a percentage law. It doesn't care about milliliters.**
