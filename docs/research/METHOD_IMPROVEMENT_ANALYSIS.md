# Perfume Chemistry Scoring System — Critical Method Improvement Analysis

**Date:** 2026-03-27  
**Scope:** Full audit of FormulaScorer (10 axes, 0-100) + StarRatings (10 characteristics, 0-10)  
**Sources:** Internal code audit, academic computational fragrance literature (Zhang et al. 2018, Santana et al. 2021, Liu et al. 2021, Oliveira et al. 2023), Calkin & Jellinek "Perfumery: Practice & Principles", Roudnitska "L'Esthétique en Question", Carles "A Method of Creation in Perfumery"

---

## Executive Summary

The current system is **structurally sound** — it covers the right axes and uses a geometric mean composite that properly penalizes weakness. But it suffers from **three systemic flaws** that a Perplexity-sourced industry comparison would immediately flag:

1. **No dilution/concentration awareness** — The system treats materials by weight percentage, ignoring that a 1% dilution at 5% of formula contributes 0.05% active. This breaks longevity, sillage, radiance, and synergy scores.
2. **Rigid canonical targets** — The Carles 20/40/40 pyramid is presented as universal truth, but chypres, skin scents, eaux de cologne, and soliflores all have intentionally different distributions.
3. **Non-validated character dimensions** — All 148 material profiles are expert-estimated, not validated against GC-MS retention indices, QSPR models, or panel testing. This is the deepest weakness.

---

## Part 1: What We Get Right (Keep These)

### 1.1 Geometric Mean Composite
**Our approach:** `exp(Σ(w_i/Σw × ln(max(1, s_i))))`  
**Industry validation:** This is the correct choice. Arithmetic means hide catastrophic weakness (a formula scoring 100/longevity + 0/balance = 50 arithmetic, but 0 geometric). The geometric mean mirrors how perfumers think — a single failing dimension tanks the composition.

**What Perplexity/literature would say:** Confirmed. The Santana et al. (2021) deep learning fragrance formulation paper uses multiplicative loss functions for exactly this reason.

### 1.2 Ten-Axis Coverage
Balance, theory, longevity, sillage, radiance, texture, complexity, character balance, synergy, cost — this covers the structural evaluation comprehensively. No academic paper I found uses more than 6-8 axes for formula quality. We're ahead of most.

### 1.3 Dual Rating System
Consumer-facing stars + technical scores in parallel is exactly how Fragrantica/Basenotes community scoring works alongside expert panel evaluations. No system I found combines both in code.

### 1.4 Theory Axis (Roudnitska + Jellinek + Arctander + OPK)
Encoding classical perfumery literature into algorithmic rules is novel. No academic paper attempts this — they focus on QSPR molecular descriptors. Having a "theory compliance" score is a genuine differentiator.

---

## Part 2: Critical Weaknesses & Fixes

### 2.1 🔴 CRITICAL: No Dilution-Aware Dosing

**The Problem:**  
`FormulaVector.ingredients` stores percentage by weight of the concentrate. When Aldehyde C12 MNA is listed at 1% dilution and occupies 0.8% of the formula, the active dose is **0.008%** — essentially homeopathic. But every scorer treats it as 0.8% of active material.

This breaks:
- **Longevity** (MW/ClogP averaged over stated percentage, not active)
- **Sillage** (VP averaged incorrectly — a 1%-diluted high-VP material contributes almost nothing)
- **Radiance** (amplifier bonus fires for materials present at negligible active)
- **Synergy** (pairing rules count presence/absence, ignoring that 0.008% active can't synergize)

**The Fix:**
```python
# In FormulaVector or a preprocessing step:
def effective_concentration(self, name: str) -> float:
    """Return active % accounting for dilution."""
    raw_pct = self.ingredients.get(name, 0)
    dilution = self.dilutions.get(name, 1.0)  # 1.0 = neat
    return raw_pct * dilution
```

**Impact:** HIGH — affects 4 of 10 scoring axes.  
**Effort:** MEDIUM — requires adding `dilutions` dict to FormulaVector and updating parsers.

---

### 2.2 🔴 CRITICAL: Rigid Carles Pyramid (20/40/40)

**The Problem:**  
`score_balance()` hardcodes target = `[20, 40, 40]`. This penalizes:
- **Chypres** (need ~15/30/55 — heavy base with oakmoss/labdanum)
- **Eaux de cologne** (need ~40/35/25 — volatile top-heavy)
- **Skin scents** (need ~10/55/35 — heart-dominant intimate projection)
- **Linear fragrances** (intentionally flat distribution)

F2 "Nuit d'Ambre" scores 25.9/100 on balance — worst in the set — but it's an oriental-amber designed to be base-heavy. That's not a defect, it's the architecture.

**The Fix:**
```python
# Style-aware balance targets
BALANCE_TARGETS = {
    "classical":    (20, 40, 40),
    "chypre":       (15, 30, 55),
    "cologne":      (40, 35, 25),
    "skin_scent":   (10, 55, 35),
    "oriental":     (15, 35, 50),
    "soliflore":    (10, 60, 30),
    "linear":       (33, 34, 33),
}

def score_balance(self, fv, style="classical"):
    target = BALANCE_TARGETS.get(style, (20, 40, 40))
    ...
```

**What Perplexity would say:** This is entry-level perfumery knowledge. No trained perfumer evaluates a chypre against a Carles pyramid. The system should either auto-detect style from ingredient profile or accept it as input.

**Impact:** HIGH — balance has weight 1.5 (highest tier alongside theory).  
**Effort:** LOW — parameterize the function + add auto-detection via ingredient dominant families.

---

### 2.3 🔴 CRITICAL: Cost Score is Fantasy

**The Problem:**  
Only 8 materials have cost data, all manually assigned "multipliers" (not real prices):
```python
expensive = {
    "alpha irone": 5, "rose absolute": 5, "jasmine absolute": 5,
    "oud": 10, "sandalwood": 4, "iris butter": 8,
    "ambergris": 10, "orris concrete": 8,
}
```

Of these, **zero** are in the current inventory (we use Alpha Irone 10% dilution, not neat Alpha Irone). The cost score for ALL 9 formulas is essentially `100 - 0 = 100` (no matches found).

**The Fix:**  
Either:
1. **Populate real cost data** for all 148 inventory materials (PerfumersWorld prices, Creating Perfume prices, even approximate $/mL buckets)
2. **Remove cost axis entirely** and redistribute its 0.2 weight to other axes
3. **Replace with "ingredient accessibility" score** — common synthetics score high, rare naturals score low

**What Perplexity would say:** A cost metric with 8 materials out of 148 is worse than no cost metric. It creates false confidence. Either invest in real data or remove it.

**Impact:** LOW (0.2 weight), but the principle matters — a useless metric corrupts the composite.  
**Effort:** MEDIUM for option 1 (data entry), LOW for option 2 (delete + reweight).

---

### 2.4 🟡 MAJOR: Non-Reciprocal Synergy

**The Problem:**  
Pairing rules are indexed by `material_a`. If material A has a synergy rule with material B, but **not** vice versa, the synergy counts once. But chemically, A+B and B+A are the same pairing.

```python
# Current: only checks from A→B
for name in ingredients_lower:
    rules = pairing_idx.get(name, [])  # only finds A→B, misses B→A
```

**The Fix:**
```python
def _build_pairing_index(self):
    for rule in get_pairing_rules():
        # Index both directions
        key_a = rule["material_a"].lower().strip()
        key_b = rule["material_b"].lower().strip()
        self._pairing_index.setdefault(key_a, []).append(rule)
        # Mirror rule for reverse lookup
        reverse = {**rule, "material_a": rule["material_b"], "material_b": rule["material_a"]}
        self._pairing_index.setdefault(key_b, []).append(reverse)
```

Then deduplicate by unordered pair `(min(A,B), max(A,B))` to avoid double-counting.

**Impact:** MEDIUM — synergy has low weight (0.3) but this is a correctness bug.  
**Effort:** LOW — 10-line fix.

---

### 2.5 🟡 MAJOR: Sillage VP Threshold

**The Problem:**  
`min(avg_vp / 5.0, 1.0) * 30` — VP threshold 5.0 Pa. But:
- Most heavy synthetics (Cashmeran ~0.01 Pa, Galaxolide ~0.003 Pa) are WAY below this
- Heavy musks are known projectors but via skin-warming diffusion, not vapor pressure
- A formula of all heavy musks would score near-zero on VP, which is wrong

**The Fix:**
```python
# Tiered VP scoring instead of linear
if avg_vp > 1.0:
    vp_score = 25 + min((avg_vp - 1.0) / 4.0, 1.0) * 5  # light projectors
elif avg_vp > 0.01:
    vp_score = 10 + min((avg_vp - 0.01) / 1.0, 1.0) * 15  # moderate
else:
    vp_score = min(avg_vp / 0.01, 1.0) * 10  # heavy (bloom diffusion)
```

Also: the 4 hardcoded boosters (Hedione, Iso E Super, Ambrox, DHM) should be expanded to include Cashmeran, Paradisone, Galaxolide, Habanolide — all known projection boosters via bloom diffusion.

**Impact:** MEDIUM — sillage weight 0.8.  
**Effort:** LOW — rework one function.

---

### 2.6 🟡 MAJOR: Theory Score Missing Data

**The Problem:**  
Roudnitska roles require `roudnitska_function` field on materials. Jellinek mapping requires `jellinek_quadrant`. Arctander tenacity requires `arctander_tenacity`. These fields exist on **<30% of materials** in the DB.

When data is missing, the function silently scores 0 for that sub-axis. A formula using all well-profiled materials gets theory credit; a formula using newer synthetics (Paradisamide, DBCA, Kephalis) gets penalized because these materials lack the metadata.

**The Fix:**
1. **Infer Roudnitska roles from character dimensions:**
   - High radiance + low MW → éclat
   - High warmth + high creamy → chaleur
   - High freshness + low animalic → transparence
   - High powdery/soft → peau (skin effect)
   - High woody/smoky + high MW → profondeur
   - Rare/expensive → noblesse

2. **Infer Jellinek quadrants from dominant dimensions:**
   - Floral + powdery → narcotic
   - Fresh + green → stimulating
   - Warm + sweet → erogenous
   - Clean + light → exalting

3. **Use MW as Arctander tenacity proxy when actual data is missing** (already partly done, but make it more robust)

**Impact:** HIGH — theory has weight 1.5.  
**Effort:** MEDIUM — write inference functions, validate against known materials.

---

### 2.7 🟡 MAJOR: Star Ratings Magic Numbers

**The Problem:**  
Star ratings use many hardcoded offsets and multipliers with no empirical basis:
- `rate_wearability`: `baseline 5.0`, animalic penalty `1.5×`, smoky `1.2×`
- `rate_originality`: 17 materials with manually assigned rarity weights
- `rate_mass_appeal`: `baseline 2.0`, "too complex" penalty for `>6 dimensions`
- `rate_value_for_money`: 3×3 hardcoded matrix (cheap/mid/expensive × bad/ok/good)

None of these were calibrated against real consumer data (Fragrantica ratings, panel studies, etc.).

**The Fix:**  
Short-term: Document the magic numbers and their rationale in code comments.  
Long-term: 
1. Collect ground-truth data — scrape Fragrantica ratings for ~50 well-known fragrances and their known composition approximations
2. Use linear regression to calibrate the weights against real consumer ratings
3. Replace the 3×3 value matrix with a continuous function

**What Perplexity would say:** The Kengpol & Wangananon (2006) paper "Expert system for assessing customer satisfaction on fragrance notes" used ANNs trained on actual consumer panel scores. Our hardcoded numbers are educated guesses, not empirical.

**Impact:** MEDIUM — affects ALL star ratings (the entire consumer-facing system).  
**Effort:** HIGH — requires ground truth data collection.

---

### 2.8 🟢 MINOR: Character Dimension Validation

**The Problem:**  
All 148 MaterialProfile entries have manually scored character dimensions (warmth, sweetness, freshness, etc. on 0-10). These were assigned by a single expert (the AI assistant), not validated against GC-MS data, trained perfumer panels, or published descriptor databases.

**What the academic literature uses instead:**
- **QSPR models** (Liu et al. 2021): Compute molecular descriptors from SMILES → predict retention grade/odor threshold
- **Odor descriptor databases** (TGSC, GoodScents, Leffingwell): Community-validated odor descriptions
- **Headspace GC-O** data: Human-evaluated gas chromatography-olfactometry

**The Fix (realistic for hobbyist scale):**
1. Cross-reference character dimensions against GoodScents Company odor descriptors for validation
2. Use IFRAnet or PerfumersWorld published material descriptions as secondary validation
3. Flag materials where our character scores diverge significantly from published descriptors

**Impact:** FOUNDATIONAL — character dimensions flow into 6 of 10 scores.  
**Effort:** HIGH — requires systematic validation pass.

---

### 2.9 🟢 MINOR: classify_note() Brittle Fallback

**The Problem:**  
Note classification uses 3-tier fallback:
1. Pre-assigned `carles_position` field → rarely populated
2. MW threshold (>250 = base, <180 = top, else heart)
3. Hardcoded name lists

MW as note predictor is crude. Linalool (MW 154) is a heart note, not a top note. Coumarin (MW 146) is a base note fixative. The MW→note mapping has systematic errors.

**The Fix:**
Use VP (vapor pressure) as primary biochemical predictor instead of MW:
- VP > 10 Pa → top note (high volatility)
- VP 0.1-10 Pa → heart note
- VP < 0.1 Pa → base note

Supplement with a "functional note" override: Some materials are classified by their perfumistic function, not their volatility (e.g., vanillin has moderate VP but functions as a base note fixative due to its tenacity on blotter).

**Impact:** MEDIUM — note distribution feeds into balance (1.5w), longevity (0.8w), sillage (0.8w).  
**Effort:** LOW-MEDIUM — VP data already exists in MaterialProfile.

---

### 2.10 🟢 MINOR: Bottle Presentation Fixed at 7.0

**The Problem:**  
`bottle_presentation = 7.0` for all DIY formulas. This wastes 1/10th of the star rating system on a meaningless constant.

**The Fix:**  
Replace with **"Formula Elegance"** — a measure of formulation craft:
- Proper use of dilutions (not overdosing trace materials)
- Avoid ingredients that serve no purpose (< 0.1% active with no amplifier effect)
- Proportion consistency (no ingredient is 10× the next largest)
- Proper fixative anchoring (has at least one fixative > 5%)

Or simply remove it from the average and compute stars as mean of 9 characteristics.

**Impact:** LOW — but improves the star system's signal-to-noise ratio.  
**Effort:** LOW.

---

## Part 3: What Perplexity / Academic Literature Would Recommend

### 3.1 Temporal Evolution Modeling (Not in our system)

**What it is:** How does the fragrance change over time? Top→heart→base transitions. Linearity vs dramatic evolution. Drydown quality.

**What the literature says:**
- Liu et al. (2021) QSPR models predict "retention grade" using MW, LogP, and molecular descriptors
- Oliveira et al. (2023) used transfer learning to predict odor detection thresholds
- Real perfumers evaluate on blotter at 15min, 1hr, 4hr, 12hr

**Our gap:** We have longevity (duration) but not evolution (quality of transitions). A formula could have great longevity but terrible transitions (jarring shift from citrus top to heavy base with no bridge).

**Proposed new axis: `score_evolution()`**
```python
def score_evolution(self, fv):
    """Score quality of temporal transitions.
    Evaluates bridge materials, transition smoothness, drydown quality."""
    # 1. Count bridge materials (ingredients classified as heart that share
    #    character overlap with both top and base ingredients)
    # 2. Score transition gradient (MW/VP distribution should be continuous,
    #    not bimodal)
    # 3. Drydown quality: base materials should have positive character
    #    dimensions (no harsh fixatives without softeners)
```

### 3.2 Odor Detection Threshold (ODT) Awareness

**What it is:** Each material has an ODT (concentration at which humans can detect it). Materials below ODT in the final dilution are functionally invisible.

**Our gap:** We don't check if materials are above their ODT in the final EdP/EdT concentration. An ingredient at 0.1% of concentrate in a 15% EdP = 0.015% final. If its ODT is 0.1 ppm, it's fine. If its ODT is 100 ppm, it's completely wasted.

**Impact on scoring:** Materials below ODT shouldn't count toward complexity, character balance, or synergy — they're olfactively absent.

### 3.3 QSPR-Based Property Prediction

**What it is:** Quantitative Structure-Property Relationships — predicting physical properties and odor characteristics from molecular structure (SMILES/InChI).

**What the literature does:**
- Zhang et al. (2018): ML-based CAMD for fragrance molecules using group contribution methods
- Heng et al. (2022): ML incorporating GC features for fragrance design

**Our opportunity:** For materials where we have SMILES strings, we could:
1. Validate our manual ClogP/MW/VP entries against computed values
2. Predict missing VP/ODT data for materials where it's absent
3. Cross-validate character dimensions against computed molecular descriptors

**Effort:** HIGH — requires RDKit or similar cheminformatics library + SMILES database.

### 3.4 Ingredient Interaction Modeling (Beyond Pairwise Synergy)

**What it is:** Our synergy model is pairwise (A+B). Real fragrance interactions are multi-body — the ternary combination A+B+C may produce effects that no pairwise rule captures.

**What the literature does:**
- Santana et al. (2021) used deep learning to model non-linear ingredient interactions
- The Kengpol (2006) ANN approach implicitly captures multi-body effects through hidden layers

**Our realistic path:**  
Add "accord-level" synergy rules alongside material-level ones:
```python
accord_synergies = {
    ("bergamot", "oakmoss", "labdanum"): "chypre_accord",  # 1+1+1 > 3
    ("lavender", "coumarin", "oakmoss"): "fougere_accord",
    ("hedione", "iso_e_super", "musk"): "molecular_cloud",
}
```

---

## Part 4: Prioritized Improvement Roadmap

| Priority | Issue | Impact | Effort | ROI |
|----------|-------|--------|--------|-----|
| **P0** | Dilution-aware dosing | HIGH (4 axes) | MEDIUM | ★★★★★ |
| **P0** | Style-aware balance targets | HIGH (1.5w) | LOW | ★★★★★ |
| **P1** | Fix cost axis or remove it | LOW-MED | LOW | ★★★★ |
| **P1** | Reciprocal synergy | MED (correctness) | LOW | ★★★★ |
| **P1** | Theory inference from dimensions | HIGH (1.5w) | MEDIUM | ★★★★ |
| **P2** | VP-corrected sillage thresholds | MED (0.8w) | LOW | ★★★ |
| **P2** | classify_note() VP-based rework | MED (feeds 3 axes) | LOW-MED | ★★★ |
| **P2** | Replace Bottle Presentation | LOW | LOW | ★★★ |
| **P3** | Temporal evolution axis | MED (new axis) | MED | ★★ |
| **P3** | Star rating calibration | MED | HIGH | ★★ |
| **P4** | Character dimension validation | FOUNDATIONAL | HIGH | ★★ |
| **P4** | ODT-awareness | MED | HIGH | ★ |
| **P5** | QSPR property validation | LOW-MED | VERY HIGH | ★ |
| **P5** | Multi-body synergy | LOW | HIGH | ★ |

---

## Part 5: Comparison — Our System vs. What Perplexity Would Recommend

| Aspect | Our System | Perplexity / Industry Standard | Gap |
|--------|-----------|-------------------------------|-----|
| **Scoring composite** | Geometric mean (weighted) | Geometric or multiplicative loss | ✅ Aligned |
| **Axis coverage** | 10 axes | Typically 4-8, rarely 10 | ✅ Ahead |
| **Theory grounding** | Roudnitska + Jellinek + Carles + Arctander | Academic papers use QSPR, not literature rules | ✅ Unique (our strength) |
| **Dual rating** | Stars + scores | Fragrantica has community ratings; academic papers have panel scores | ✅ Ahead |
| **Concentration handling** | Percentage by weight (no dilution) | Active concentration with ODT filtering | 🔴 Critical gap |
| **Style adaptability** | Fixed 20/40/40 target | Style-aware targets per fragrance family | 🔴 Critical gap |
| **Material data quality** | 148 manually scored profiles | TGSC/GoodScents validated; QSPR-predicted | 🟡 Moderate gap |
| **Temporal modeling** | Longevity (duration only) | Evolution curves, drydown quality | 🟡 Missing axis |
| **Consumer calibration** | Hardcoded magic numbers | ANN/regression trained on panel data | 🟡 No empirical basis |
| **Synergy model** | Pairwise, non-reciprocal | Multi-body (DL-based), reciprocal | 🟡 Correctness issue |
| **Cost data** | 8 materials, arbitrary multipliers | Real supplier pricing or material tier system | 🔴 Non-functional |
| **Note classification** | MW fallback (crude) | VP-based + functional override | 🟢 Improvable |

---

## Part 6: Quick Wins (Can Implement Now)

### 6.1 Make score_balance() style-aware
Add a `style` parameter that auto-detects from dominant ingredient families or accepts user input. **5-10 lines of code change.**

### 6.2 Fix synergy reciprocity
Index pairing rules in both directions, deduplicate by unordered pair. **10 lines.**

### 6.3 Remove or fix cost axis
Option A: Remove cost from ObjectiveWeights (set to 0), redistribute 0.2 across other axes.  
Option B: Add a simple 3-tier cost classification (budget/mid/premium) per material.

### 6.4 Replace bottle_presentation with formula_elegance
Score based on:
- Proportion rationality (no ingredient is < 0.2% with no amplifier function)
- Fixative anchoring (at least one fixative > 5% of concentrate)
- Dilution discipline (trace materials use proper dilutions)

### 6.5 Expand sillage boosters
Add Cashmeran, Galaxolide, Habanolide, Paradisone to the booster list. Adjust VP threshold curve.

---

## Conclusion

The system's **architecture is solid** — geometric mean, 10-axis coverage, theory grounding, dual ratings. These are genuine differentiators that no academic paper or Perplexity response would replicate.

The **critical fixes are concentration-awareness and style-adaptive balance** — these affect the most heavily weighted axes and are conceptually straightforward. Without them, formulas are evaluated against a single canonical standard that doesn't exist in real perfumery.

The **deepest long-term weakness is data quality** — 148 manually scored profiles without external validation. This is the foundation everything else builds on. But it's also the hardest to fix without access to proprietary databases.

**Recommended immediate actions:** P0 items (dilution-aware dosing + style-aware balance), then P1 items (cost fix + synergy reciprocity + theory inference). These 5 changes would improve the system's accuracy more than any other combination of modifications.
