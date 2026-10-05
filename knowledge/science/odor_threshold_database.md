# Odor Detection Threshold Database

## Overview
This document provides comprehensive odor detection threshold (ODT) data for fragrance materials, psychophysical laws governing smell perception, and practical applications for perfume formulation.

---

## 1. Fundamental Concepts

### 1.1 Odor Detection Threshold (ODT)
The **minimum concentration** at which 50% of a trained panel can detect the presence of an odor (not identify it).

**Units:**
- **ppm** (parts per million): μg/L in air
- **ppb** (parts per billion): ng/L in air
- **ppt** (parts per trillion): pg/L in air
- **% w/w**: percentage in solution

### 1.2 Recognition Threshold
The minimum concentration required to **identify** the odor (typically 2-5× higher than ODT).

### 1.3 Difference Threshold (Just Noticeable Difference - JND)
The minimum concentration change that can be perceived as different.

---

## 2. Psychophysical Laws

### 2.1 Weber-Fechner Law

**Perceived intensity** is proportional to the **logarithm of concentration**:

```
S = k × log(I/I₀)
```

Where:
- S = perceived intensity
- I = actual concentration
- I₀ = threshold concentration
- k = constant

**Implications:**
- Doubling concentration does NOT double perceived intensity
- Small changes near threshold are very noticeable
- Large changes at high concentrations are less noticeable

**Example:**
Going from 0.1% to 0.2% feels like a bigger jump than 10% to 20%.

### 2.2 Stevens' Power Law

More accurate for extreme intensities:

```
S = k × I^n
```

Where:
- n = exponent (varies by material)
- For most fragrances: n ≈ 0.5-0.7

**Example:**
- n = 0.5: 4× concentration = 2× perceived intensity
- n = 1.0: linear relationship (rare)

### 2.3 Just Noticeable Difference (JND)

```
JND = ΔI/I ≈ constant
```

Typically: **20-30%** concentration change needed for perception.

**Example:**
- At 1% concentration: need change to 1.2-1.3% to notice
- At 10% concentration: need change to 12-13% to notice

---

## 3. Odor Detection Thresholds by Chemical Class

### 3.1 Ultra-Potent Materials (ODT < 0.001 ppm)

| Chemical | ODT (ppm) | ODT (ppb) | Notes |
|----------|-----------|-----------|-------|
| **β-Damascenone** | 0.000009 | 0.009 | Apple, rose, plum - strongest known natural |
| **2-Methyl-3-furanthiol** | 0.00002 | 0.02 | Roasted, meaty - found in coffee |
| **1-p-Menthene-8-thiol** | 0.00003 | 0.03 | Grapefruit, sulfurous |
| **Grapefruit mercaptan** | 0.00004 | 0.04 | Fresh grapefruit |
| **β-Damascone** | 0.00008 | 0.08 | Fruity, rose, tobacco |

**Formulation Rule:** Never exceed 0.001-0.01% in final formula.

### 3.2 Extremely Potent Materials (ODT 0.001-0.1 ppm)

| Chemical | ODT (ppm) | ODT (ppb) | Safe Max % | Notes |
|----------|-----------|-----------|------------|-------|
| **Indole** | 0.00014 | 0.14 | 0.01-0.1% | Fecal in high conc, floral trace |
| **Skatole** | 0.0002 | 0.2 | 0.005-0.05% | Animalic, fecal |
| **Methyl anthranilate** | 0.0004 | 0.4 | 0.1-0.5% | Grape, neroli |
| **γ-Decalactone** | 0.001 | 1.0 | 0.5-2% | Peach, coconut |
| **Ionones (α & β)** | 0.007 | 7.0 | 0.5-3% | Violet, woody |
| **Geraniol** | 0.04 | 40 | 1-10% | Rose, citrus |

**Formulation Rule:** Consider headspace impact - these dominate vapor phase.

### 3.3 High Impact Materials (ODT 0.1-1 ppm)

| Chemical | ODT (ppm) | Safe Max % | Character |
|----------|-----------|------------|-----------|
| **Linalool** | 0.15 | 5-30% | Lavender, floral |
| **Eugenol** | 0.3 | 1-10% | Clove, spicy |
| **Citronellol** | 0.5 | 2-15% | Rose, citrus |
| **Benzyl acetate** | 0.8 | 5-20% | Jasmine, fruity |
| **Phenylethyl alcohol** | 1.0 | 5-25% | Rose, honey |

### 3.4 Moderate Impact Materials (ODT 1-10 ppm)

| Chemical | ODT (ppm) | Typical % | Character |
|----------|-----------|-----------|-----------|
| **Limonene** | 2.0 | 10-50% | Citrus, fresh |
| **Linalyl acetate** | 2.5 | 5-30% | Lavender, bergamot |
| **Coumarin** | 3.0 | 1-5% | Tonka, hay |
| **Hedione** | 5.0 | 10-40% | Jasmine, fresh |
| **Benzyl salicylate** | 7.0 | 5-20% | Floral, balsamic |

### 3.5 Low Impact Materials (ODT > 10 ppm)

| Chemical | ODT (ppm) | Typical % | Character |
|----------|-----------|-----------|-----------|
| **Ethyl vanillin** | 12 | 1-5% | Vanilla, sweet |
| **Vanillin** | 20 | 2-10% | Vanilla, balsamic |
| **Iso E Super** | 50 | 10-50% | Woody, amber |
| **Galaxolide** | 80 | 10-40% | Musk, clean |
| **Dihydromyrcenol** | 100 | 5-30% | Citrus, lime |

---

## 4. Odor Value Calculations

### 4.1 Odor Value (OV)

```
OV = Concentration_in_formula / ODT
```

**Interpretation:**
- **OV < 1:** Below perception threshold (subliminal)
- **OV = 1:** Just perceivable (threshold)
- **OV = 10:** Clearly present
- **OV = 100:** Dominant
- **OV > 1000:** Overwhelming

### 4.2 Practical Examples

**Example 1: β-Damascenone**
- Used at 0.0001% in formula
- ODT = 0.000009 ppm ≈ 0.000001% in solution
- OV = 0.0001 / 0.000001 = **100** (very strong presence)

**Example 2: Iso E Super**
- Used at 20% in formula
- ODT ≈ 0.05% in solution
- OV = 20 / 0.05 = **400** (dominant character)

**Example 3: Linalool**
- Used at 5% in formula
- ODT ≈ 0.0015% in solution
- OV = 5 / 0.0015 ≈ **3333** (extremely strong)

### 4.3 Formula Balancing Using OV

**Target:** Balanced floral formula

| Material | Conc % | ODT % | OV | Target Role |
|----------|--------|-------|-------|-------------|
| Rose absolute | 2.0 | 0.005 | 400 | Main character |
| Geraniol | 3.0 | 0.004 | 750 | Supporting floral |
| Linalool | 5.0 | 0.0015 | 3333 | Dominant fresh |
| Indole | 0.05 | 0.000014 | 3571 | Animalic depth |

**Analysis:** Indole and linalool have similar OV despite 100× difference in concentration - both will be prominent.

---

## 5. Temperature Effects on Thresholds

### 5.1 General Trends

**Higher temperature:**
- Increases vapor pressure → more molecules in air
- Lowers effective ODT
- Materials smell stronger

**Rule of thumb:**
```
ODT_temp2 = ODT_temp1 × 0.9^((T2-T1)/10)
```

**Example:** Material with ODT = 1 ppm at 20°C:
- At 30°C: ODT ≈ 1 × 0.9 = 0.9 ppm (smells stronger)
- At 10°C: ODT ≈ 1 × 1.11 = 1.11 ppm (smells weaker)

### 5.2 Practical Implications

- Perfumes smell stronger in summer heat
- Cold storage reduces perceived intensity during evaluation
- Test formulas at intended wearing temperature (skin temp ≈ 32-34°C)

---

## 6. Synergistic & Antagonistic Effects

### 6.1 Odor Masking

Some materials raise the threshold of others:

**Example combinations:**
- **Vanillin + Coumarin:** Coumarin threshold increases 2-3× in presence of high vanillin
- **Musk + Aldehydes:** Musks can suppress aldehyde sharpness, raising perceived threshold

### 6.2 Odor Enhancement

Some materials lower the threshold of others:

**Example combinations:**
- **Linalool + Linalyl acetate:** Together smell stronger than expected from individual OVs
- **Iso E Super + Hedione:** Mutual enhancement, effective ODT drops ~30%

### 6.3 Compensation Effect

```
Perceived_threshold_mix ≠ Σ(Individual_thresholds)
```

Must test blends empirically - calculations are approximations.

---

## 7. Context-Dependent Thresholds

### 7.1 Matrix Effects

ODT varies by medium:

| Medium | Typical ODT Multiplier | Example |
|--------|------------------------|---------|
| Air (pure) | 1.0× | Reference |
| Ethanol solution | 1.2-1.5× | Slightly higher threshold |
| Oil/DPG | 0.8-1.0× | Lower threshold (better solubility) |
| Water | 2-5× | Much higher threshold (poor solubility) |
| Dry-down on skin | 0.5-0.8× | Lower (body heat enhances) |

**Implication:** Don't formulate only based on pure ODT - consider delivery medium.

### 7.2 Adaptation Effects

**Olfactory fatigue:**
- Continuous exposure raises effective threshold
- After 5-10 minutes, threshold can increase 10-100×
- Recovery takes 15-30 minutes

**Example:**
- Linalool ODT = 0.15 ppm initially
- After 5 min exposure: effective ODT ≈ 5-10 ppm
- "Nose-blind" to own perfume after wearing 1 hour

### 7.3 Individual Variation

**Genetic differences:**
- 10-1000× variation between individuals for some molecules
- Example: Androstenone (musk)
  - ~30% of people are anosmic (cannot smell)
  - ~30% find it pleasant (musky)
  - ~40% find it unpleasant (urine-like)

**Age effects:**
- Threshold increases ~1% per year after age 50
- Children have lower thresholds (more sensitive)

**Training:**
- Professional perfumers have 2-5× lower thresholds
- With practice, ODT can decrease significantly

---

## 8. Practical Formulation Guidelines

### 8.1 The 1% Rule for Extreme Potency

**For materials with ODT < 0.01 ppm:**
```
Max_safe_% = ODT_ppm × 100
```

**Example:** β-Damascenone (ODT = 0.000009 ppm):
```
Max ≈ 0.000009 × 100 = 0.0009% (approximately 0.001% or 10 ppm)
```

### 8.2 Odor Impact Budgeting

**Total Odor Value Budget:** Aim for cumulative OV ≈ 5000-10000 for balanced formula.

**Distribution:**
- Main accord: 40-50% of total OV
- Supporting notes: 30-40% of total OV
- Trace effects: 10-20% of total OV

**Example:** Target total OV = 8000
- Main rose accord: OV = 3500
- Citrus top: OV = 2500
- Woody base: OV = 1500
- Animalic trace: OV = 500

### 8.3 Dilution Strategy for Testing

When testing potent materials:

**Step 1:** Create 0.1% or 1% dilution in DPG or ethanol
**Step 2:** Use dilution in formula
**Step 3:** Calculate neat equivalent for records

**Example:** Testing Indole (ODT = 0.00014 ppm)
- Create 1% dilution in DPG
- Add 0.5% of this dilution to formula
- Neat equivalent = 0.5% × 1% = 0.005% Indole

---

## 9. Analytical Methods for Threshold Determination

### 9.1 Triangle Test
- Present 3 samples: 2 blanks, 1 with odorant
- Panel identifies the odd one
- Repeat at decreasing concentrations
- ODT = 50% correct identification level

### 9.2 Ascending Concentration Method
- Start below threshold
- Increase concentration in steps
- Record first detection
- Average across panel

### 9.3 Descending Concentration Method
- Start above threshold
- Decrease concentration
- Record last detection
- More conservative (higher ODT values)

**Best practice:** Use both ascending and descending, average results.

---

## 10. Threshold Data by Olfactive Family

### 10.1 Citrus Notes

| Material | ODT (ppm) | Typical % | Impact |
|----------|-----------|-----------|--------|
| Limonene | 2.0 | 15-40% | Moderate |
| β-Pinene | 5.0 | 5-15% | Low-moderate |
| Linalool | 0.15 | 5-20% | High |
| Citral | 0.02 | 0.5-2% | Very high |
| Nootkatone | 0.001 | 0.01-0.1% | Extreme |

### 10.2 Floral Notes

| Material | ODT (ppm) | Typical % | Impact |
|----------|-----------|-----------|--------|
| Phenylethyl alcohol | 1.0 | 10-25% | Moderate |
| Geraniol | 0.04 | 2-10% | High |
| Linalool | 0.15 | 5-20% | High |
| Indole | 0.00014 | 0.01-0.1% | Extreme |
| Hedione | 5.0 | 10-30% | Moderate |
| Methyl anthranilate | 0.0004 | 0.1-0.5% | Extreme |

### 10.3 Woody Notes

| Material | ODT (ppm) | Typical % | Impact |
|----------|-----------|-----------|--------|
| Cedrol | 10 | 1-5% | Low-moderate |
| Iso E Super | 50 | 10-50% | Low |
| Sandalwood oil | 8 | 5-20% | Moderate |
| Patchouli oil | 3 | 2-10% | Moderate-high |
| Cashmeran | 15 | 5-15% | Low-moderate |

### 10.4 Amber/Balsamic Notes

| Material | ODT (ppm) | Typical % | Impact |
|----------|-----------|-----------|--------|
| Vanillin | 20 | 2-8% | Low-moderate |
| Ethyl vanillin | 12 | 1-5% | Moderate |
| Coumarin | 3.0 | 1-5% | Moderate-high |
| Benzoin resinoid | 5 | 2-10% | Moderate |
| Labdanum | 4 | 3-12% | Moderate |

### 10.5 Musk Notes

| Material | ODT (ppm) | Typical % | Impact |
|----------|-----------|-----------|--------|
| Galaxolide | 80 | 15-35% | Low |
| Cashmeran | 15 | 5-15% | Low-moderate |
| Muscone | 0.5 | 1-5% | High |
| Exaltolide | 20 | 5-15% | Low-moderate |
| Ambrettolide | 0.8 | 1-8% | High |

### 10.6 Animalic Notes

| Material | ODT (ppm) | Typical % | Impact |
|----------|-----------|-----------|--------|
| Indole | 0.00014 | 0.01-0.1% | Extreme |
| Skatole | 0.0002 | 0.005-0.05% | Extreme |
| Civetone | 0.3 | 0.5-3% | Very high |
| Castoreum | 2 | 1-5% | Moderate-high |

---

## 11. Advanced Concepts

### 11.1 Threshold Curves

**Log-log relationship:**
```
log(Perceived_intensity) = m × log(Concentration) + b
```

**Slope (m)** indicates sensitivity:
- Steep slope (m > 0.7): small concentration changes have big perceptual impact
- Shallow slope (m < 0.5): large changes needed for perceptual difference

### 11.2 Cross-Modal Interactions

**Trigeminal stimulation** (cooling, warming, tingling) lowers odor threshold:
- Menthol enhances mint odor perception
- Capsaicin enhances spice odor perception

**Taste-smell interaction:**
- Sweetness lowers threshold for vanilla-like odors
- Bitterness raises threshold for pleasant florals

### 11.3 Temporal Dynamics

**First sniff vs. sustained:**
- Initial threshold (first exposure): Reference ODT
- After 30 seconds: Effective ODT increases 2-5×
- After 5 minutes: Effective ODT increases 10-50×

**Recovery:**
- 50% recovery: 5-10 minutes
- 90% recovery: 30-60 minutes
- Full recovery: 2-4 hours (for very potent materials)

---

## 12. Quality Control Applications

### 12.1 Batch Consistency Testing

**Method:**
1. Calculate OV for each component in reference batch
2. Measure OV for each component in test batch
3. Acceptable variance: ±20% OV

**Example:**
- Reference: Linalool at 5% (OV = 3333)
- Test batch: Linalool at 4.5% (OV = 3000)
- Variance: (3000-3333)/3333 = -10% ✓ (acceptable)

### 12.2 Reformulation Guidance

When replacing a material, match OV:

**Example:** Replace natural rose otto (expensive) with synthetic blend:

**Rose otto:**
- 2% in formula
- ODT ≈ 0.002%
- OV = 2/0.002 = 1000

**Synthetic blend to match:**
- Geraniol (ODT 0.004%): Use at 0.8% → OV = 200
- Phenylethyl alcohol (ODT 0.1%): Use at 10% → OV = 100
- Citronellol (ODT 0.05%): Use at 4% → OV = 80
- Rose oxide (ODT 0.0005%): Use at 0.2% → OV = 400
- **Total OV ≈ 780** (close to 1000, adjust ratios to fine-tune)

---

## 13. Safety Thresholds vs. Odor Thresholds

**Important distinction:**

- **Odor Threshold (ODT):** When you can smell it
- **Irritation Threshold:** When it causes physical irritation (usually 1000-10000× ODT)
- **Sensitization Threshold:** When it can cause allergic reaction (varies, but often 100-1000× ODT)

**IFRA limits are based on safety, NOT odor!**

**Example: Coumarin**
- ODT: ~3 ppm in air (0.0003% in solution)
- IFRA limit: 0.8% in leave-on product (safety limit)
- You'd smell it at 0.001%, but it's safe up to 0.8%

Always follow **IFRA limits** even if odor threshold suggests you could use less.

---

## 14. Reference Values Summary

### Quick Reference: Potency Categories

| Category | ODT Range | Max Safe % | Examples |
|----------|-----------|------------|----------|
| **Nuclear** | < 0.001 ppm | 0.001-0.01% | β-Damascenone, mercaptans |
| **Extreme** | 0.001-0.1 ppm | 0.01-0.5% | Indole, skatole, ionones |
| **Very High** | 0.1-1 ppm | 0.5-5% | Geraniol, eugenol, muscone |
| **High** | 1-10 ppm | 2-15% | Linalool, citronellol, coumarin |
| **Moderate** | 10-100 ppm | 5-40% | Hedione, vanillin, Iso E Super |
| **Low** | > 100 ppm | 10-60% | Dihydromyrcenol, Galaxolide |

---

## References & Notes

- ODT values are approximate and vary by testing method
- Always test in actual formula context
- Individual perception varies significantly
- Temperature, medium, and time affect practical thresholds
- Use OV calculations as guidelines, not absolute rules
- When in doubt, start low and build up in small increments

**Critical Reminder:** Odor thresholds are for perception, not safety. Always check IFRA limits separately.
