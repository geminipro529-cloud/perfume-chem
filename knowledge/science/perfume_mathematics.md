# Perfumery Mathematics: Fundamental Calculations

## Overview
This document provides the mathematical framework for perfume formulation, including concentration calculations, blending ratios, scaling, yield calculations, and cost analysis.

---

## 1. Concentration Calculations

### 1.1 Percentage by Weight (% w/w)
Most perfume formulas use weight percentage:

```
% Component = (Weight of Component / Total Weight) × 100
```

**Example:**
- 5g Bergamot in 100g formula = (5/100) × 100 = 5% w/w

### 1.2 Converting Between Dilutions

**From Neat to Diluted:**
```
Amount_diluted = Amount_neat × (Concentration_target / Concentration_stock)
```

**Example:** Need 2g of 10% Civetone, have 100% stock:
```
Amount_100% = 2g × (10/100) = 0.2g neat + 1.8g solvent
```

**From Diluted to Neat Equivalent:**
```
Neat_equivalent = Amount_diluted × (Concentration_stock / 100)
```

**Example:** 5g of Hedione 10% contains:
```
Neat_equivalent = 5g × (10/100) = 0.5g pure Hedione
```

### 1.3 Alcohol Concentration in Final Product

For Eau de Parfum (EDP) targeting 15% fragrance concentration:

```
Alcohol_% = 100 - Fragrance_% - Water_% - Other_%
```

**Typical EDP:**
- 15% fragrance concentrate
- 75-80% ethanol
- 5-10% water
- 0-1% fixatives/stabilizers

---

## 2. Blending Ratios

### 2.1 Simple Ratio Notation
Perfume ratios written as **Top:Heart:Base**

**Example:** 3:5:2 ratio means:
```
Top = 3/(3+5+2) = 3/10 = 30%
Heart = 5/(3+5+2) = 5/10 = 50%
Base = 2/(3+5+2) = 2/10 = 20%
```

### 2.2 Calculating Component Amounts from Ratios

For a 100g formula with 3:5:2 ratio:
```
Total parts = 3 + 5 + 2 = 10
Top = (3/10) × 100g = 30g
Heart = (5/10) × 100g = 50g
Base = (2/10) × 100g = 20g
```

### 2.3 Adjusting Ratios While Maintaining Total

To increase base from 20% to 25% in a 3:5:2 formula:

1. New base = 25%
2. Remaining = 75% for top + heart
3. Maintain top:heart ratio (3:5)
   - Top = 75% × (3/8) = 28.125%
   - Heart = 75% × (5/8) = 46.875%

**New ratio: 2.8:4.7:2.5**

---

## 3. Scaling Formulas

### 3.1 Linear Scaling
To scale formula from any size to target size:

```
Scaling_factor = Target_weight / Current_weight
New_amount = Original_amount × Scaling_factor
```

**Example:** Scale 50g formula to 500g:
```
Scaling_factor = 500/50 = 10
Bergamot: 2.5g × 10 = 25g
Rose: 1.0g × 10 = 10g
Sandalwood: 3.0g × 10 = 30g
```

### 3.2 Drop-Based to Weight Conversion

**Standard Drop Weights:**
- Thin liquids (citrus oils): 0.03-0.04g per drop
- Medium liquids (most aromatics): 0.04-0.05g per drop
- Thick liquids (absolutes): 0.05-0.06g per drop

**Formula:**
```
Weight = Number_of_drops × Drop_weight
```

**Example:** Recipe calls for 20 drops bergamot (0.035g/drop):
```
Weight = 20 × 0.035g = 0.7g
```

### 3.3 Volume to Weight Conversion

```
Weight = Volume × Density
```

**Common Densities (g/mL):**
- Ethanol: 0.789
- Water: 1.000
- Limonene: 0.841
- Linalool: 0.862
- Vanillin: 1.056
- Coumarin: 1.176

**Example:** 10mL of linalool:
```
Weight = 10mL × 0.862 g/mL = 8.62g
```

---

## 4. Yield Calculations

### 4.1 Theoretical Yield
Sum of all input weights:

```
Theoretical_yield = Σ(Weight of each component)
```

### 4.2 Actual Yield Losses

**Typical losses:**
- Transfer losses: 1-3%
- Evaporation (volatile top notes): 2-5%
- Absorption to containers: 0.5-1%

```
Actual_yield = Theoretical_yield × (1 - Loss_%)
```

**Example:** 100g formula with 4% loss:
```
Actual_yield = 100g × (1 - 0.04) = 96g
```

### 4.3 Calculating Overage for Target Yield

To compensate for losses and achieve target:

```
Required_input = Target_yield / (1 - Expected_loss_%)
```

**Example:** Need 100g final, expect 4% loss:
```
Required_input = 100g / (1 - 0.04) = 104.17g
```

---

## 5. Dilution Mathematics

### 5.1 Creating Custom Dilutions

**C₁V₁ = C₂V₂ Formula:**

```
Volume_stock = (Target_concentration × Target_volume) / Stock_concentration
```

**Example:** Make 10mL of 1% Iso E Super from 100% stock:
```
Volume_100% = (1 × 10mL) / 100 = 0.1mL
Volume_solvent = 10mL - 0.1mL = 9.9mL
```

### 5.2 Mixing Two Dilutions

To achieve intermediate concentration:

```
V₁ × C₁ + V₂ × C₂ = V_total × C_target
```

**Example:** Mix 50% and 10% to get 30% concentration:

Using 10mL total:
```
Let x = volume of 50% solution
(10-x) = volume of 10% solution

x(50) + (10-x)(10) = 10(30)
50x + 100 - 10x = 300
40x = 200
x = 5mL of 50% solution
10-x = 5mL of 10% solution
```

---

## 6. Cost Calculations

### 6.1 Cost Per Gram

```
Cost_per_gram = Total_price / Weight_in_grams
```

**Example:** 100mL Bergamot at $15, density 0.88 g/mL:
```
Weight = 100mL × 0.88 = 88g
Cost_per_gram = $15 / 88g = $0.17/g
```

### 6.2 Formula Cost Calculation

```
Total_cost = Σ(Weight_component × Cost_per_gram_component)
```

**Example:**
| Component | Weight | Cost/g | Total |
|-----------|--------|--------|-------|
| Bergamot | 10g | $0.17 | $1.70 |
| Rose Abs | 2g | $8.50 | $17.00 |
| Sandalwood | 5g | $1.20 | $6.00 |
| Ethanol | 83g | $0.02 | $1.66 |
| **TOTAL** | **100g** | - | **$26.36** |

### 6.3 Cost Percentage Breakdown

```
Component_cost_% = (Component_cost / Total_cost) × 100
```

From example above:
- Rose absolute = ($17.00 / $26.36) × 100 = **64.5% of cost**
- Bergamot = ($1.70 / $26.36) × 100 = **6.4% of cost**

### 6.4 Target Price Formulation

To meet target cost per mL:

```
Max_material_cost = (Target_price × Volume) - (Packaging + Labor + Overhead)
```

**Example:** 50mL EDP selling at $80, costs breakdown:
- Packaging: $8
- Labor: $5
- Overhead: $12
- Margin: 40% ($32)

```
Max_material_cost = $80 - $8 - $5 - $12 - $32 = $23 for 50mL
Cost_per_mL = $23 / 50mL = $0.46/mL
```

---

## 7. Concentration Standards

### 7.1 Fragrance Categories

| Type | Concentrate % | Longevity | Typical Use |
|------|---------------|-----------|-------------|
| Parfum/Extrait | 20-40% | 8-12h | Luxury, special occasion |
| Eau de Parfum | 15-20% | 6-8h | Daily wear, premium |
| Eau de Toilette | 5-15% | 3-5h | Fresh, casual |
| Eau de Cologne | 2-5% | 2-3h | Refreshing, splash |
| After Shave | 2-4% | 1-2h | Post-shave care |

### 7.2 Converting Between Concentrations

**From EDP (15%) to Parfum (25%):**

For same olfactive profile:
```
Scaling_factor = 25/15 = 1.67
New_amounts = Original_amounts × 1.67
```

**Example:** EDP has 3% Bergamot (of total):
```
In Parfum: 3% × 1.67 = 5% Bergamot (of total)
```

---

## 8. Evaporation Rate Calculations

### 8.1 Relative Evaporation Rate (RER)

Relative to n-butyl acetate = 100:

```
Evaporation_time_ratio = Component_RER / Reference_RER
```

**Example RER values:**
- Ethanol: 180
- Limonene: 60
- Linalool: 15
- Eugenol: 1
- Vanillin: 0.01

### 8.2 Predicting Top Note Duration

Rough estimation:
```
Duration_hours ≈ (RER / 20) for components with RER < 50
```

**Example:** Linalool (RER = 15):
```
Duration ≈ 15/20 = 0.75 hours (45 minutes)
```

This is why top notes need refreshing and heart notes provide the main body.

---

## 9. Headspace Ratios

### 9.1 Vapor Phase Concentration

Not all components evaporate equally. Headspace ratio:

```
Headspace_ratio = Vapor_pressure × Concentration
```

Higher vapor pressure = stronger initial impact.

**Example Vapor Pressures (mmHg at 20°C):**
- d-Limonene: 1.98
- Linalool: 0.22
- Coumarin: 0.001

Even at equal concentration, limonene will dominate headspace initially.

---

## 10. Advanced Calculations

### 10.1 Weighted Average Molecular Weight

For predicting overall volatility:

```
MW_avg = Σ(MW_component × Weight_%)
```

**Example:**
- Limonene (MW 136): 30%
- Linalool (MW 154): 50%
- Eugenol (MW 164): 20%

```
MW_avg = (136 × 0.30) + (154 × 0.50) + (164 × 0.20)
MW_avg = 40.8 + 77 + 32.8 = 150.6 g/mol
```

Lower MW_avg = more volatile formula overall.

### 10.2 Odor Value (OV)

```
Odor_Value = Concentration / Odor_Detection_Threshold
```

OV > 1 means component is perceivable.

**Example:** 0.1% Iso E Super with ODT of 0.05%:
```
OV = 0.1 / 0.05 = 2 (clearly perceivable)
```

### 10.3 Substantivity Index

Predicting longevity:

```
Substantivity = log(Octanol_Water_Partition × Molecular_Weight)
```

Higher substantivity = longer lasting.

---

## 11. Quality Control Calculations

### 11.1 Batch Reproducibility

Acceptable variance: ±2% for main components, ±5% for trace materials.

```
Variance_% = |Actual - Target| / Target × 100
```

**Example:** Target 5.00g bergamot, actual 5.15g:
```
Variance = |5.15 - 5.00| / 5.00 × 100 = 3% (outside tolerance)
```

### 11.2 Specific Gravity Check

```
Specific_Gravity = Weight / Volume
```

For quality verification:
- Measure 10mL of finished formula
- Weigh precisely
- Calculate SG
- Compare to reference batch (should be ±0.005)

---

## 12. Practical Examples

### Example 1: Complete Formula Calculation

**Target:** 100g Eau de Parfum, 15% concentrate

**Step 1: Concentrate composition (15g total)**
- Bergamot 10% = 1.5g
- Rose 5% = 0.75g
- Sandalwood 5% = 0.75g
- Sum = 3.0g (20% of concentrate)
- Fill to 15g with base aromatics

**Step 2: Solvent (85g total)**
- Ethanol 80% = 80g
- Water 5% = 5g

**Step 3: Verify total = 100g** ✓

### Example 2: Scaling with Dilutions

**Original:** 50g formula with 2g of Civetone 10%
**Target:** 500g formula

**Calculation:**
```
Scaling = 500/50 = 10×
Civetone_10% needed = 2g × 10 = 20g

If you only have Civetone 100%:
Neat_needed = 20g × (10/100) = 2g
Solvent_needed = 18g
```

---

## References & Notes

- All percentages are w/w unless specified
- Densities vary with temperature (use 20°C as standard)
- Always verify with analytical balance for precision
- Round final amounts to practical measurement precision (0.01g for analytical work)
- Account for temperature expansion when measuring volumes

**Critical Safety Note:** When calculating potent materials (musks, animalics, indoles), always double-check dilution math. A 10× error can ruin a formula or create skin sensitization risk.
