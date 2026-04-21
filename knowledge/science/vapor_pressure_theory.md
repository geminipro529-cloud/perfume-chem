# Vapor Pressure Theory & Evaporation Kinetics

## Overview
This document covers the physical chemistry of fragrance volatility, including vapor pressure, evaporation rates, headspace composition, and temperature effects critical for perfume development.

---

## 1. Fundamental Vapor Pressure Concepts

### 1.1 Definition
**Vapor pressure** is the pressure exerted by a vapor in equilibrium with its liquid phase at a given temperature.

**Key principle:** Higher vapor pressure = more volatile = evaporates faster

**Units:**
- mmHg (millimeters of mercury)
- Pa (Pascals): 1 mmHg = 133.32 Pa
- kPa (kiloPascals): 1 kPa = 1000 Pa = 7.5 mmHg

### 1.2 Clausius-Clapeyron Equation

Vapor pressure vs. temperature relationship:

```
ln(P₂/P₁) = -(ΔHvap/R) × (1/T₂ - 1/T₁)
```

Where:
- P = vapor pressure
- ΔHvap = enthalpy of vaporization (J/mol)
- R = gas constant (8.314 J/mol·K)
- T = temperature (Kelvin)

**Implication:** Vapor pressure increases exponentially with temperature.

### 1.3 Antoine Equation (Practical Form)

More accurate for specific temperature ranges:

```
log₁₀(P) = A - B/(C + T)
```

Where:
- P = vapor pressure (mmHg)
- T = temperature (°C)
- A, B, C = substance-specific constants

**Example: Linalool**
- A = 7.115
- B = 1821
- C = 215

At 25°C:
```
log₁₀(P) = 7.115 - 1821/(215 + 25) = 7.115 - 7.588 = -0.473
P = 10^(-0.473) = 0.336 mmHg
```

---

## 2. Vapor Pressure Database for Fragrance Materials

### 2.1 Very High Volatility (VP > 10 mmHg at 25°C)

| Material | VP (mmHg) | Boiling Point (°C) | Character | Evaporation Class |
|----------|-----------|-------------------|-----------|-------------------|
| **Ethanol** | 59 | 78 | Solvent | Immediate |
| **Acetone** | 231 | 56 | Solvent | Immediate |
| **Diethyl ether** | 442 | 35 | Solvent | Immediate |
| **Eucalyptol** | 18 | 176 | Camphoraceous | Very fast |
| **α-Pinene** | 14.5 | 156 | Pine, fresh | Very fast |
| **β-Pinene** | 12.8 | 166 | Pine, woody | Very fast |

**Role:** Top notes, immediate impact (0-15 minutes)

### 2.2 High Volatility (VP 1-10 mmHg at 25°C)

| Material | VP (mmHg) | Boiling Point (°C) | Character | Evaporation Class |
|----------|-----------|-------------------|-----------|-------------------|
| **Limonene** | 1.98 | 176 | Citrus, orange | Fast |
| **γ-Terpinene** | 2.1 | 183 | Citrus, herbal | Fast |
| **p-Cymene** | 1.8 | 177 | Cumin, citrus | Fast |
| **Linalool** | 0.22 | 198 | Lavender, floral | Fast |
| **Citronellal** | 1.5 | 207 | Lemon, rose | Fast |

**Role:** Top to early heart (15-60 minutes)

### 2.3 Medium Volatility (VP 0.1-1 mmHg at 25°C)

| Material | VP (mmHg) | Boiling Point (°C) | Character | Evaporation Class |
|----------|-----------|-------------------|-----------|-------------------|
| **Linalyl acetate** | 0.18 | 220 | Bergamot, lavender | Medium |
| **Geraniol** | 0.12 | 230 | Rose, citrus | Medium |
| **Citronellol** | 0.08 | 224 | Rose, citrus | Medium |
| **Eugenol** | 0.15 | 254 | Clove, spicy | Medium |
| **Benzyl acetate** | 0.18 | 213 | Jasmine, fruity | Medium |

**Role:** Heart notes (1-4 hours)

### 2.4 Low Volatility (VP 0.01-0.1 mmHg at 25°C)

| Material | VP (mmHg) | Boiling Point (°C) | Character | Evaporation Class |
|----------|-----------|-------------------|-----------|-------------------|
| **Phenylethyl alcohol** | 0.08 | 219 | Rose, honey | Medium-slow |
| **Hedione** | 0.02 | 298 | Jasmine, fresh | Slow |
| **β-Ionone** | 0.03 | 273 | Violet, woody | Slow |
| **Coumarin** | 0.001 | 298 | Tonka, hay | Very slow |
| **Iso E Super** | 0.005 | 305 | Woody, amber | Very slow |

**Role:** Late heart to base (3-8 hours)

### 2.5 Very Low Volatility (VP < 0.01 mmHg at 25°C)

| Material | VP (mmHg) | Boiling Point (°C) | Character | Evaporation Class |
|----------|-----------|-------------------|-----------|-------------------|
| **Cedrol** | 0.003 | 291 | Cedarwood | Very slow |
| **Vanillin** | 0.0008 | 285 | Vanilla, sweet | Very slow |
| **Galaxolide** | 0.002 | 298 | Musk, clean | Very slow |
| **Cashmeran** | 0.004 | 310 | Woody, musky | Very slow |
| **Ambrettolide** | 0.0005 | 338 | Musk, amber | Extremely slow |

**Role:** Base notes, fixatives (6-24+ hours)

---

## 3. Evaporation Rate Theory

### 3.1 Relative Evaporation Rate (RER)

Standardized against **n-butyl acetate = 100**

```
RER = (Evaporation_rate_sample / Evaporation_rate_n-butyl_acetate) × 100
```

**Categories:**
- **Very fast:** RER > 150 (ether, acetone)
- **Fast:** RER 50-150 (ethanol, limonene)
- **Medium:** RER 10-50 (linalool, geraniol)
- **Slow:** RER 1-10 (eugenol, vanillin)
- **Very slow:** RER < 1 (heavy musks, resins)

### 3.2 RER vs. Vapor Pressure Relationship

**Approximate correlation:**
```
RER ≈ k × VP^0.7
```

Where k is a constant depending on molecular weight and temperature.

**Practical RER values:**

| Material | VP (mmHg) | RER | Class |
|----------|-----------|-----|-------|
| Ethanol | 59 | 180 | Very fast |
| Limonene | 1.98 | 60 | Fast |
| Linalool | 0.22 | 15 | Medium |
| Eugenol | 0.15 | 1.2 | Slow |
| Vanillin | 0.0008 | 0.01 | Very slow |

### 3.3 Evaporation Time Estimation

**Simple model:**
```
t₅₀ = k / VP
```

Where:
- t₅₀ = time for 50% to evaporate
- k = constant (≈ 10 for typical conditions)
- VP = vapor pressure (mmHg)

**Example: Linalool (VP = 0.22 mmHg)**
```
t₅₀ ≈ 10 / 0.22 ≈ 45 minutes
```

**Example: Vanillin (VP = 0.0008 mmHg)**
```
t₅₀ ≈ 10 / 0.0008 ≈ 12,500 minutes (8.7 days)
```

---

## 4. Headspace Composition

### 4.1 Raoult's Law (Ideal Mixtures)

For a component in a mixture:

```
P_component = X_component × P°_component
```

Where:
- P_component = partial vapor pressure of component
- X_component = mole fraction in liquid
- P°_component = pure vapor pressure

**Headspace mole fraction:**
```
Y_component = P_component / P_total
```

### 4.2 Practical Headspace Example

**Formula composition (by mole fraction):**
- Limonene: X = 0.50, P° = 1.98 mmHg
- Linalool: X = 0.30, P° = 0.22 mmHg
- Vanillin: X = 0.20, P° = 0.0008 mmHg

**Partial pressures:**
- P_limonene = 0.50 × 1.98 = 0.99 mmHg
- P_linalool = 0.30 × 0.22 = 0.066 mmHg
- P_vanillin = 0.20 × 0.0008 = 0.00016 mmHg

**Total pressure:**
```
P_total = 0.99 + 0.066 + 0.00016 = 1.056 mmHg
```

**Headspace composition:**
- Y_limonene = 0.99 / 1.056 = **93.8%**
- Y_linalool = 0.066 / 1.056 = **6.2%**
- Y_vanillin = 0.00016 / 1.056 = **0.015%**

**Interpretation:** Even though vanillin is 20% of liquid, it's only 0.015% of vapor → initial smell is dominated by limonene.

### 4.3 Non-Ideal Behavior (Activity Coefficients)

Real mixtures deviate from Raoult's Law:

```
P_component = γ × X_component × P°_component
```

Where γ = activity coefficient:
- **γ > 1:** Positive deviation (component "wants to escape" → higher evaporation)
- **γ < 1:** Negative deviation (component "likes" the mixture → lower evaporation)
- **γ = 1:** Ideal behavior

**Example: Ethanol in perfume oil**
- Ethanol in pure ethanol: γ = 1
- Ethanol in heavy oils: γ ≈ 1.5-2.0 (escapes more readily)

This is why alcohol evaporates faster from perfume than from pure alcohol.

---

## 5. Temperature Effects

### 5.1 Vapor Pressure Temperature Dependence

**Rule of thumb:** Vapor pressure roughly **doubles** for every 10°C increase.

**Example: Linalool**
- At 15°C: VP ≈ 0.15 mmHg
- At 25°C: VP ≈ 0.22 mmHg (1.5× increase)
- At 35°C: VP ≈ 0.35 mmHg (2.3× vs. 15°C)

### 5.2 Skin Temperature Effects

**Normal skin temperature: 32-34°C**

Perfume on skin vs. in bottle (20°C):
- VP increase ≈ 1.8-2.2×
- Evaporation rate ≈ 2-3× faster

**This is why:**
- Perfumes smell stronger on skin than on paper strips
- Warm body areas (neck, wrists) project more
- Summer fragrances need different balance than winter

### 5.3 Heat-Accelerated Aging Test

**Shelf life prediction:**
```
Aging_rate_55°C ≈ 8-10× faster than 20°C
```

**Application:**
- 2 weeks at 55°C ≈ 4 months at room temperature
- Use for accelerated stability testing

---

## 6. Evaporation Profiles (Olfactory Timeline)

### 6.1 Top Notes (0-30 minutes)

**Characteristics:**
- VP > 1 mmHg
- RER > 50
- BP < 200°C

**Typical materials:**
- Citrus oils (limonene, linalool, citral)
- Light aldehydes (C6-C10)
- Green notes (cis-3-hexenol)
- Ozonic notes

**Evaporation:** 80-95% gone in 30 minutes

### 6.2 Heart Notes (30 min - 4 hours)

**Characteristics:**
- VP 0.05-1 mmHg
- RER 5-50
- BP 200-260°C

**Typical materials:**
- Florals (geraniol, phenylethyl alcohol, linalyl acetate)
- Spices (eugenol, cinnamaldehyde)
- Fruits (esters, lactones)

**Evaporation:** 50-80% gone in 4 hours

### 6.3 Base Notes (4-24+ hours)

**Characteristics:**
- VP < 0.05 mmHg
- RER < 5
- BP > 260°C

**Typical materials:**
- Woods (cedrol, sandalwood)
- Balsams (vanillin, benzoin)
- Musks (galaxolide, cashmeran)
- Animalics (civetone, castoreum)

**Evaporation:** 20-50% gone in 24 hours

### 6.4 Fixatives (24+ hours)

**Characteristics:**
- VP < 0.01 mmHg
- RER < 1
- BP > 280°C

**Typical materials:**
- Heavy musks (ambrettolide, muscone)
- Resins (labdanum, benzoin resinoid)
- Vetiver oil
- Patchouli oil

**Evaporation:** <20% gone in 24 hours

---

## 7. Predicting Evaporation Behavior

### 7.1 Molecular Weight Correlation

**General trend:**
```
Volatility ∝ 1/MW^n
```

Where n ≈ 0.5-0.7

**Example:**
- Limonene (MW 136): High volatility
- Linalool (MW 154): Medium-high
- Iso E Super (MW 234): Low volatility

**BUT:** Structure matters more than MW alone!

### 7.2 Structural Factors Affecting Volatility

**Factors that INCREASE volatility:**
- Branched structures (vs. linear)
- Fewer hydrogen bonds
- Lower polarity
- Smaller molecular size

**Factors that DECREASE volatility:**
- Hydrogen bonding (OH groups)
- High polarity
- Aromatic rings (π-π stacking)
- Large molecular size

**Example comparison (similar MW ~150):**
- **Limonene** (C₁₀H₁₆, no OH): VP = 1.98 mmHg (high)
- **Linalool** (C₁₀H₁₈O, has OH): VP = 0.22 mmHg (medium)
- **Eugenol** (C₁₀H₁₂O₂, OH + aromatic): VP = 0.15 mmHg (lower)

### 7.3 Hydrogen Bonding Effects

**Free OH groups reduce volatility significantly:**

| Material | MW | OH groups | VP (mmHg) |
|----------|-----|-----------|-----------|
| Limonene | 136 | 0 | 1.98 |
| Linalool | 154 | 1 | 0.22 |
| Geraniol | 154 | 1 | 0.12 |
| Phenylethyl alcohol | 122 | 1 | 0.08 |

**Acetylation increases volatility:**
- Linalool (VP 0.22) → Linalyl acetate (VP 0.18) - slightly higher
- Benzyl alcohol → Benzyl acetate (VP increases ~2×)

---

## 8. Practical Applications

### 8.1 Balancing Evaporation Rates

**Target:** Smooth transition from top → heart → base

**Method 1: Vapor Pressure Blending**
```
Average_VP = Σ(X_i × VP_i)
```

**Example target VP ranges:**
- Top accord: Average VP > 0.5 mmHg
- Heart accord: Average VP 0.05-0.5 mmHg
- Base accord: Average VP < 0.05 mmHg

**Method 2: Half-life Matching**

Calculate t₅₀ for each note:
- Top: t₅₀ = 10-30 min
- Heart: t₅₀ = 1-4 hours
- Base: t₅₀ > 6 hours

### 8.2 Extending Longevity

**Techniques:**

1. **Increase base note %:**
   - Typical: 20% base
   - Longer-lasting: 30-40% base

2. **Add fixatives:**
   - Musks (Galaxolide, Iso E Super): 10-20%
   - Woody notes (Cedrol, Sandalwood): 5-15%
   - Resins (Labdanum, Benzoin): 2-10%

3. **Reduce volatile top %:**
   - Standard: 30% top
   - Longer-lasting: 15-20% top

4. **Use lower-volatility alternatives:**
   - Instead of linalool → use linalyl acetate
   - Instead of citrus oils → use terpinyl acetate

### 8.3 Boosting Projection (Sillage)

**Opposite strategy - increase volatility:**

1. **Increase top note %:**
   - Standard: 30%
   - High projection: 40-50%

2. **Use high VP materials:**
   - Add dihydromyrcenol (fresh, projects strongly)
   - Add aldehyde C12 MNA (powerful projection)

3. **Reduce base fixation:**
   - Lower musk % to 5-10%
   - Use medium-volatility heart as "base"

---

## 9. Measuring Evaporation Experimentally

### 9.1 Gravimetric Method

**Setup:**
1. Weigh precise amount of sample
2. Expose to controlled conditions (temp, airflow)
3. Weigh at intervals
4. Plot mass vs. time

**Data analysis:**
```
% Evaporated = (Initial_mass - Current_mass) / Initial_mass × 100
```

### 9.2 Gas Chromatography Headspace Analysis

**Method:**
1. Seal sample in vial
2. Equilibrate at controlled temperature
3. Sample headspace with GC
4. Quantify each component

**Advantage:** Measures actual composition, not just total mass.

### 9.3 Smelling Strip Test

**Quick practical method:**

1. Apply same amount to multiple strips
2. Smell at intervals (15 min, 30 min, 1h, 2h, 4h, 8h, 24h)
3. Note intensity and character changes
4. Map evaporation profile qualitatively

**Documentation template:**
- **15 min:** Bright citrus, intense (8/10)
- **1 hour:** Floral emerges, citrus fading (6/10)
- **4 hours:** Soft floral, woody base appearing (4/10)
- **8 hours:** Woody-musky, smooth (2/10)
- **24 hours:** Faint musk (1/10)

---

## 10. Solvent Effects on Evaporation

### 10.1 Ethanol vs. Oil Base

**Ethanol (VP = 59 mmHg):**
- Carrier evaporates quickly (minutes)
- Leaves fragrance oils on skin
- "Exposes" materials quickly → strong initial impact
- Better for top-note heavy compositions

**Oil/DPG (VP ≈ 0.001 mmHg):**
- Carrier stays on skin
- Fragrance oils evaporate more slowly from oil matrix
- Smoother, more gradual development
- Better for base-heavy, long-lasting compositions

### 10.2 Alcohol Concentration Effects

**High alcohol (90%+):**
- Faster burst of top notes
- Sharper transitions
- Less longevity

**Lower alcohol (70-80%):**
- Gentler evaporation
- Smoother transitions
- Slightly better longevity

**Optimal for most EdP:** 75-80% alcohol

---

## 11. Advanced Modeling

### 11.1 Multi-Component Evaporation Model

For complex mixtures, use **activity-corrected Raoult's Law:**

```
P_i(t) = γ_i × X_i(t) × P°_i(T)
```

Where X_i(t) changes over time as more volatile components evaporate.

**Iterative calculation:**
1. Start with initial composition
2. Calculate vapor composition
3. Remove evaporated amount (Δt)
4. Recalculate liquid composition
5. Repeat for next time step

### 11.2 Diffusion-Limited Evaporation

For thick films or skin application:

```
Evaporation_rate = (D × ΔC) / thickness
```

Where:
- D = diffusion coefficient
- ΔC = concentration gradient
- thickness = film thickness

**Thicker application → slower evaporation → better longevity**

---

## 12. Quick Reference Tables

### 12.1 Volatility Classification

| VP (mmHg) | RER | t₅₀ | Class | Perfume Role |
|-----------|-----|-----|-------|--------------|
| > 10 | > 150 | < 10 min | Very high | Initial burst |
| 1-10 | 50-150 | 10-60 min | High | Top notes |
| 0.1-1 | 10-50 | 1-4 hours | Medium | Heart notes |
| 0.01-0.1 | 1-10 | 4-12 hours | Low | Late heart/base |
| < 0.01 | < 1 | > 12 hours | Very low | Fixatives |

### 12.2 Temperature Correction Factors

| Temp (°C) | VP Multiplier | Notes |
|-----------|---------------|-------|
| 5 | 0.4× | Refrigerator |
| 15 | 0.7× | Cool room |
| 20 | 1.0× | Reference |
| 25 | 1.5× | Room temp |
| 32-34 | 2.0× | Skin temp |
| 40 | 3.0× | Hot day |
| 55 | 8-10× | Accelerated testing |

---

## References & Practical Notes

- Vapor pressures are approximate, vary by source
- Real mixtures deviate from ideal behavior
- Skin chemistry affects evaporation (oils, pH, temperature)
- Humidity affects perceived volatility (not actual VP)
- Always test on skin, not just paper strips
- Evaporation profiles change during dry-down (as composition shifts)

**Key Takeaway:** Use VP and RER as guides for initial formulation, then refine through testing.
