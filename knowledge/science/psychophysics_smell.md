# Psychophysics of Smell: Perception, Measurement & Hedonic Theory

## Overview
This document covers the psychophysical principles of olfactory perception, including magnitude estimation, hedonic evaluation, individual differences, cultural factors, and practical applications for perfume development.

---

## 1. Fundamental Psychophysical Concepts

### 1.1 Psychophysics Defined

**The bridge between physical stimuli and psychological perception:**
```
Physical Stimulus (chemical concentration) → Sensory Response → Perceptual Experience
```

**Key questions:**
- How does odor intensity relate to concentration?
- What is the minimum detectable difference?
- How do we measure subjective "pleasantness"?
- How do cultural/personal factors shape perception?

### 1.2 Classical Psychophysical Laws

**Weber's Law (JND - Just Noticeable Difference):**
```
ΔI / I = k (constant)
```

Where:
- ΔI = smallest detectable change in intensity
- I = initial intensity
- k = Weber fraction (~0.2-0.3 for olfaction)

**Example:**
- If you smell linalool at 5% concentration
- JND = 5% × 0.25 = 1.25%
- Need to change to 6.25% or 3.75% to notice difference

**Fechner's Law:**
```
S = k × log(I / I₀)
```

Where:
- S = perceived intensity
- I = stimulus intensity
- I₀ = threshold intensity
- k = constant

**Implication:** Doubling concentration does NOT double perceived strength.

**Stevens' Power Law (more accurate):**
```
S = k × I^n
```

Where:
- n = exponent (for odor: typically 0.4-0.7)

**Example with n = 0.5:**
- 4× concentration → 2× perceived intensity
- 100× concentration → 10× perceived intensity

---

## 2. Odor Intensity Measurement

### 2.1 Magnitude Estimation

**Method:**
1. Present reference stimulus at standard concentration (e.g., "This is 10")
2. Present test stimuli at various concentrations
3. Subject assigns numbers relative to reference
4. Repeat across panel (20-50 subjects)
5. Average results

**Example data (linalool):**

| Concentration (%) | Average Magnitude | Std Dev |
|-------------------|-------------------|---------|
| 0.1 | 2.5 | 0.8 |
| 0.5 | 5.1 | 1.2 |
| 1.0 | 7.8 | 1.5 |
| 2.0 | 11.2 | 2.0 |
| 5.0 | 18.4 | 3.1 |

**Power function fit:**
```
S = 8.5 × C^0.52
```

### 2.2 Category Scaling

**Method:**
1. Define categories (e.g., 0 = none, 1 = very weak, 2 = weak, 3 = moderate, 4 = strong, 5 = very strong)
2. Present stimuli
3. Subject assigns to category
4. Analyze distribution

**Advantage:** Simpler than magnitude estimation, easier for untrained subjects.

**Disadvantage:** Less resolution (only 5-7 categories vs. continuous scale).

### 2.3 Labeled Magnitude Scale (LMS)

**Anchored scale:**
```
0 - No sensation
1.4 - Barely detectable
6.1 - Weak
17.2 - Moderate
35.4 - Strong
53.3 - Very strong
100 - Strongest imaginable sensation (of any kind)
```

**Advantage:** Universal anchor ("strongest imaginable") allows cross-modal comparison (compare odor intensity to pain, taste, etc.).

**Use:** Academic research, standardized sensory studies.

### 2.4 Temporal Dominance of Sensations (TDS)

**Tracks perception over time:**

1. Subject smells perfume continuously (or on smelling strip)
2. At each time point (every 5-10 sec), indicates which attribute is dominant
3. Example attributes: "citrus," "floral," "woody," "musky"
4. Plot dominance curves over time

**Example result:**
- 0-5 min: Citrus dominant
- 5-30 min: Floral emerges, becomes dominant
- 30 min-2 hours: Woody becomes dominant
- 2-8 hours: Musky dominant

**Application:** Understanding perfume evolution, optimizing dry-down.

---

## 3. Odor Quality & Descriptive Analysis

### 3.1 Odor Profiling (Descriptive)

**Method:**
1. Train panel (10-15 people) on reference materials
2. Generate vocabulary (e.g., "floral," "green," "woody," "sweet," "powdery")
3. Rate each attribute on intensity scale (0-10)
4. Statistically analyze (PCA, cluster analysis)

**Example profile (Rose absolute):**

| Attribute | Intensity (0-10) | Std Dev |
|-----------|------------------|---------|
| Floral | 9.2 | 0.8 |
| Rosy | 8.8 | 0.9 |
| Honey-like | 4.5 | 1.2 |
| Green | 3.1 | 1.5 |
| Spicy | 2.8 | 1.1 |
| Woody | 1.2 | 0.9 |

### 3.2 Principal Component Analysis (PCA)

**Goal:** Reduce dimensionality of odor space

**Process:**
1. Collect odor profiles (50 materials × 30 attributes)
2. PCA extracts main dimensions (e.g., PC1 = "floral-woody," PC2 = "fresh-heavy")
3. Plot materials in 2D space

**Interpretation:**
- Materials close together = similar smell
- Materials far apart = different smell

**Example:**
- PC1 (50% variance): Fresh (negative) ↔ Heavy (positive)
- PC2 (25% variance): Floral (negative) ↔ Woody (positive)

**Position of materials:**
- Bergamot: (-0.8, -0.2) [fresh, slightly floral]
- Rose: (-0.3, -0.7) [moderately fresh, very floral]
- Sandalwood: (+0.6, +0.8) [heavy, very woody]

### 3.3 Semantic Odor Profiling

**Use natural language:**
- Subject describes odor in own words
- Text mining extracts common descriptors
- Build word clouds, frequency tables

**Example (analyzing 100 descriptions of "vanilla"):**
- Top words: sweet (95%), creamy (78%), warm (65%), comforting (52%), dessert (48%)
- Rare words: floral (8%), fresh (5%), sharp (2%)

**Application:** Marketing (use consumer language), formulation (understand associations).

---

## 4. Hedonic Evaluation (Pleasantness)

### 4.1 Hedonic Scales

**Bipolar scale (most common):**
```
-4 = Extremely dislike
-3 = Strongly dislike
-2 = Moderately dislike
-1 = Slightly dislike
 0 = Neither like nor dislike
+1 = Slightly like
+2 = Moderately like
+3 = Strongly like
+4 = Extremely like
```

**Unipolar scale:**
```
0 = Not at all pleasant
1 = Slightly pleasant
2 = Moderately pleasant
3 = Very pleasant
4 = Extremely pleasant
```

**Visual Analog Scale (VAS):**
- 100 mm line: "Dislike" ←→ "Like"
- Subject marks position
- Measure distance from left (0-100)

### 4.2 Inverted-U Relationship (Concentration vs. Hedonic)

**Pattern:** Many odorants are pleasant at low concentrations, unpleasant at high.

**Example: Indole**

| Concentration (ppm) | Hedonic Rating | Character |
|---------------------|----------------|-----------|
| 0.0001 | +2.5 | Floral, jasmine-like |
| 0.001 | +3.2 | Pleasant floral |
| 0.01 | +1.8 | Floral with slight animalic |
| 0.1 | -0.5 | Animalic, slightly unpleasant |
| 1.0 | -2.8 | Fecal, unpleasant |
| 10.0 | -3.9 | Strongly fecal, very unpleasant |

**Optimal concentration:** ~0.001-0.01 ppm (peak hedonic).

**Mechanism:**
- Different receptors activated at different concentrations
- Low conc: Pleasant-receptor dominant
- High conc: Unpleasant-receptor dominant (trigeminal irritation also)

### 4.3 Familiarity Effect

**General finding:** Familiarity increases pleasantness (up to a point).

**Example study:**
- Unfamiliar odorants: Hedonic rating = 0.5 ± 1.2
- Familiar odorants: Hedonic rating = 1.8 ± 1.0
- **p < 0.001 (significant difference)**

**Explanation:**
- Mere exposure effect (repeated exposure → preference)
- Cultural learning (familiar = safe)
- Semantic associations (name influences liking)

**Exception:** Very unpleasant odors (fecal, rotten) remain unpleasant even with familiarity (innate aversion).

### 4.4 Context Effects

**Odor + Label:**

**Example study (same odor, different labels):**

| Label | Hedonic Rating | Perceived Intensity |
|-------|----------------|---------------------|
| "Cheddar cheese" | +2.1 | 6.5 |
| "Body odor" | -2.3 | 7.8 |

**Same chemical (isovaleric acid), different perception!**

**Odor + Color:**

**Example:**
- Red color + fruity odor → rated more "strawberry-like"
- Green color + same odor → rated more "apple-like"

**Odor + Music:**
- Pleasant music + neutral odor → odor rated more pleasant
- Dissonant music + same odor → odor rated less pleasant

**Implication:** Perfume perception is multi-sensory. Packaging, brand story, environment all matter.

---

## 5. Individual Differences in Perception

### 5.1 Genetic Variation (Specific Anosmias)

**Reviewed in olfactory_neuroscience.md**, but key points:

- ~30% population anosmic to androstenone
- ~10-15% anosmic to β-ionone (violet)
- Specific anosmias common (affects ~10-30% for specific materials)

**Practical:**
- Don't rely on single material for key effect (redundancy)
- Panel testing essential (not just perfumer's nose)

### 5.2 Age Effects

**Sensitivity decline:**
- Peak sensitivity: ages 20-40
- Gradual decline: 1-2% per year after 50
- By age 70: ~50% have measurable impairment

**Hedonic shifts:**
- Children: Prefer sweet, fruity
- Adults: More tolerance for complex, woody, animalic
- Elderly: Prefer stronger, simpler fragrances

### 5.3 Sex Differences

**Sensitivity:**
- Women typically 20-50% more sensitive (lower thresholds)
- Greater discrimination ability
- Hormonal variation (peaks at ovulation)

**Hedonic preferences:**
- Women (average): Prefer floral, sweet, fresh
- Men (average): Prefer woody, spicy, leathery
- **But:** Large overlap, individual variation greater than sex difference

**Cultural overlay:**
- "Masculine" vs. "feminine" fragrances are socially constructed
- No inherent biological basis for labeling (e.g., lavender as "feminine" in West, "masculine" in Middle East)

### 5.4 Personality & Hedonic Preferences

**Studies show correlations (small to moderate):**

**Extraversion:**
- Prefer intense, stimulating fragrances
- Like citrus, spicy, fresh

**Neuroticism:**
- Prefer calming, comforting fragrances
- Like lavender, vanilla, soft florals

**Openness to experience:**
- Willing to try unusual, complex fragrances
- Like niche, avant-garde perfumes

**Conscientiousness:**
- Prefer classic, traditional fragrances
- Like Chanel No. 5, conventional florals

**Caveat:** These are statistical trends, not absolutes. Individual variation is huge.

---

## 6. Cultural Differences in Odor Perception

### 6.1 Odor Preferences Across Cultures

**Universal preferences (innate):**
- Pleasant: Vanilla, fruity esters (strawberry, banana)
- Unpleasant: Fecal (skatole, indole at high conc), rotten (sulfides, amines)

**Culturally variable:**

| Odor | Western Preference | Asian Preference | Middle Eastern Preference |
|------|-------------------|------------------|---------------------------|
| Oud (agarwood) | Neutral to dislike | Mixed | Strongly like |
| Patchouli | Mixed | Like | Like |
| White florals (jasmine, tuberose) | Like | Strongly like | Like |
| Aldehydic (Chanel No. 5 type) | Like (traditional) | Mixed | Less common |
| Incense (frankincense, myrrh) | Mixed | Less common | Strongly like |

**Example study (Ayabe-Kanamura et al., 1998):**
- Japanese vs. German subjects rating 30 odorants
- Correlation: r = 0.75 (moderate agreement)
- But significant differences for specific odors:
  - Soy sauce: Japanese like (+2.5), Germans dislike (-1.2)
  - Cheese: Germans like (+1.8), Japanese mixed (0.3)

### 6.2 Semantic Associations

**Same odor, different associations:**

**Lavender:**
- **Western:** Calming, clean, grandmother's sachets
- **Traditional Chinese Medicine:** Medicinal, therapeutic

**Patchouli:**
- **1960s West:** Hippie, counterculture
- **Contemporary Asia:** Luxury, sophistication

**Rose:**
- **Universal:** Romance, femininity
- **Middle East:** Religious, spiritual (rose water in mosques)

### 6.3 Odor-Color Associations (Cultural)

**Example: Lemon odor**

| Culture | Associated Color | Reason |
|---------|------------------|--------|
| Western | Yellow | Lemon fruit color |
| Tropical (e.g., Philippines) | Green | Calamansi (green citrus) |

**Perfume marketing:** Tailor packaging color to target market's associations.

---

## 7. Emotional Response to Odor

### 7.1 Emotion Theories

**Basic emotions (Ekman):**
- Happiness, Sadness, Anger, Fear, Disgust, Surprise

**Circumplex model (Russell):**
- 2D space: Valence (pleasant ↔ unpleasant) × Arousal (calming ↔ stimulating)

**Example mapping of fragrances:**

| Fragrance Type | Valence | Arousal | Emotion |
|----------------|---------|---------|---------|
| **Vanilla** | Positive | Low | Comfort, relaxation |
| **Citrus** | Positive | High | Energy, happiness |
| **Lavender** | Positive | Low | Calm, peace |
| **Patchouli** | Positive | Moderate | Sensuality, depth |
| **Aldehydes** | Neutral-Positive | High | Excitement, alertness |
| **Oud** | Neutral-Negative (Western) | High | Intensity, intrigue |

### 7.2 Odor-Evoked Autobiographical Memory (Proust Effect)

**Characteristics:**
- Odors trigger vivid, emotional memories
- Memories are older (childhood) than those triggered by visual/auditory cues
- More emotional, less detailed than visual memories

**Neural basis:**
- Olfactory pathway directly to amygdala (emotion) and hippocampus (memory)
- No thalamic relay (unlike vision, hearing)

**Example:**
- "Smell of crayons → elementary school classroom" (vivid, emotional)
- More powerful than seeing photo of classroom

**Perfume implication:**
- Signature scents create lifelong associations
- Nostalgia marketing effective (e.g., "smells like my grandmother's perfume")

### 7.3 Mood Induction

**Can odors change mood?**

**Evidence:**
- **Lavender:** Reduces anxiety (multiple RCTs), lowers cortisol
- **Citrus (lemon, orange):** Increases alertness, positive mood
- **Vanilla:** Reduces startle response (calming)
- **Peppermint:** Increases cognitive performance (attention, memory)

**Mechanisms:**
- **Physiological:** Some odorants affect autonomic nervous system (heart rate, cortisol)
- **Psychological:** Learned associations, expectancy effects

**Example study (Lehrner et al., 2005):**
- Lavender in dental waiting room → reduced anxiety (vs. control)
- Effect size: moderate (d = 0.5)

**Caveat:** Effects are modest, individual variation large. Not a replacement for clinical treatment.

---

## 8. Odor Adaptation & Habituation

### 8.1 Peripheral Adaptation

**Mechanism:**
- Odorant receptor desensitization (phosphorylation)
- Ca²⁺-mediated feedback (closes ion channels)
- Time course: Seconds to minutes

**Example:**
- Enter room with strong perfume → very noticeable
- After 5 minutes → barely notice
- Leave room, return 30 min later → noticeable again

### 8.2 Central Habituation

**Mechanism:**
- Decreased response in olfactory cortex
- "Gating" of familiar, non-salient stimuli

**Cross-adaptation:**
- Adaptation to one odorant affects perception of similar odorants
- Example: Adapt to linalool → sensitivity to linalyl acetate also reduced

**Practical:**
- Perfumers "rest" nose between evaluations (coffee beans, fresh air breaks)
- Don't evaluate >10-12 samples in one session

### 8.3 Individual Differences in Adaptation

**Fast adapters:**
- Become "nose-blind" to own perfume within 30 min
- May over-apply

**Slow adapters:**
- Maintain sensitivity longer
- Less likely to over-apply

**Implication:** Formulate for average (moderate adaptation rate).

---

## 9. Measuring Perfume Performance

### 9.1 Consumer Testing Metrics

**Typical questionnaire:**

**Initial impression (0-5 min):**
- Overall liking (hedonic scale)
- Intensity (too weak / just right / too strong)
- Character (check attributes: floral, fruity, woody, etc.)

**Dry-down (4-8 hours):**
- Still present? (yes/no)
- Still like? (hedonic scale)
- Character change? (better / same / worse)

**Purchase intent:**
- Would you buy this? (1 = definitely not, 5 = definitely yes)

**Example results (100 subjects):**

| Metric | Fragrance A | Fragrance B |
|--------|-------------|-------------|
| Initial liking (1-5) | 3.8 ± 0.9 | 4.2 ± 0.7 |
| Dry-down liking (1-5) | 3.2 ± 1.1 | 3.9 ± 0.9 |
| Intensity (% "just right") | 65% | 78% |
| Purchase intent (% 4-5) | 48% | 62% |

**Winner: Fragrance B** (higher liking, better intensity perception, higher purchase intent).

### 9.2 Wear Testing (Real-World Use)

**Protocol:**
1. Give samples to 20-50 participants
2. Wear for 1-2 weeks (daily use)
3. Diary: Rate each day (liking, intensity, longevity, compliments received)
4. Final questionnaire

**Advantages:**
- Real-world context (vs. lab)
- Accounts for adaptation, fatigue, context effects

**Example finding:**
- Lab test: Fragrance rated 3.8/5
- Wear test: Rated 3.2/5 (novelty wears off, adaptation)

### 9.3 A/B Testing (Preference)

**Paired comparison:**
- Present A and B side-by-side (blind)
- Which do you prefer?
- Repeat across 50-100 subjects

**Statistical analysis:**
```
Binomial test: Is preference significantly different from 50/50?
```

**Example:**
- 60% prefer A, 40% prefer B
- n = 100, p = 0.04 (significant at α = 0.05)
- **Conclusion:** A is significantly preferred

---

## 10. Psychophysical Methods for Formulation Optimization

### 10.1 Threshold Determination (Detection & Recognition)

**Ascending Method of Limits:**
1. Start below threshold
2. Increase concentration in steps
3. Record when subject first detects
4. Repeat 5-10 times, average

**Example (Linalool detection threshold):**
- Trials: 0.0012%, 0.0015%, 0.0018%, 0.0011%, 0.0014%
- Average: **0.0014%**

### 10.2 Difference Threshold (JND) for Formulation Tweaks

**Method:**
1. Present reference formula
2. Present test formula (slightly different)
3. "Are these the same or different?"
4. Repeat at various concentrations
5. Find concentration where 75% detect difference

**Example:**
- Reference: 5% Bergamot
- Test: 4.5%, 5%, 5.5%, 6%, 6.5%
- 75% detection at 6% → **JND = 1%** (20% relative change)

**Application:** Know minimum change needed to create perceptible difference.

### 10.3 Optimal Concentration (Hedonic Peak)

**Method:**
1. Prepare samples at 5-7 concentrations
2. Rate hedonic (1-5 scale)
3. Plot hedonic vs. concentration
4. Find peak

**Example: Iso E Super in woody base**

| Concentration (%) | Hedonic Rating |
|-------------------|----------------|
| 5 | 2.8 |
| 10 | 3.5 |
| 15 | 4.1 |
| 20 | 4.3 ← **Peak** |
| 25 | 4.0 |
| 30 | 3.6 |

**Optimal:** 20% Iso E Super (hedonic maximum).

---

## 11. Advanced Topics

### 11.1 Signal Detection Theory (SDT)

**Separates sensitivity from response bias:**

**2×2 outcome matrix:**

|               | Signal Present | Signal Absent |
|---------------|----------------|---------------|
| "Detect"      | Hit            | False Alarm   |
| "No detect"   | Miss           | Correct Rejection |

**Sensitivity (d'):**
```
d' = Z(Hit Rate) - Z(False Alarm Rate)
```

Higher d' = better discrimination.

**Criterion (c):**
```
c = -0.5 × [Z(Hit Rate) + Z(False Alarm Rate)]
```

Positive c = conservative (reluctant to say "yes"), negative c = liberal.

**Application:** Separate true olfactory ability from guessing strategy.

### 11.2 Multidimensional Scaling (MDS)

**Create perceptual map of odor space:**

**Process:**
1. Subject rates dissimilarity between all pairs of odorants (e.g., 20 materials = 190 pairs)
2. MDS algorithm finds 2D or 3D configuration that preserves dissimilarities
3. Plot materials in space

**Example result:**
- Dimension 1: Fresh ↔ Heavy
- Dimension 2: Floral ↔ Woody
- Bergamot and Lemon close together (similar)
- Bergamot and Sandalwood far apart (dissimilar)

### 11.3 Preference Mapping (External Preference)

**Combine descriptive data + hedonic data:**

**Process:**
1. Descriptive panel rates 20 perfumes on 30 attributes
2. Consumer panel (200 people) rates hedonic (like/dislike)
3. Regression: Hedonic = f(Attributes)
4. Identify which attributes drive liking

**Example finding:**
- Liking increases with "fresh" (β = +0.45, p < 0.001)
- Liking decreases with "powdery" (β = -0.32, p < 0.01)
- **Implication:** Increase freshness, reduce powdery for this market segment

---

## 12. Practical Applications for Perfumers

### 12.1 Panel Selection & Training

**Screening:**
- Test olfactory sensitivity (detection thresholds for 10-20 reference odorants)
- Exclude anosmics (e.g., androstenone-anosmic may miss key musks)
- Exclude heavy smokers (reduced sensitivity)

**Training (3-6 months):**
- Learn vocabulary (60-100 descriptors)
- Calibrate intensity scales (practice with reference standards)
- Develop reproducibility (rate same sample multiple times, check consistency)

**Maintenance:**
- Monthly calibration sessions
- Avoid strong fragrances day-of testing
- No perfume, scented products on test day

### 12.2 Designing Consumer Tests

**Sample size:**
- Minimum 50 (for basic hedonic)
- 100-200 (for segmentation, preference mapping)
- 500+ (for launch decisions)

**Demographic matching:**
- Age, sex, income to match target market
- Exclude fragrance industry professionals (too critical)

**Blind vs. branded:**
- **Blind:** Reveals product performance alone
- **Branded:** Reveals brand power, packaging influence
- Do both!

### 12.3 Interpreting Hedonic Data

**Mean hedonic score:**
- < 2.5 (on 1-5 scale): Poor, reject
- 2.5-3.5: Acceptable, niche appeal
- 3.5-4.0: Good, mainstream potential
- > 4.0: Excellent, strong market potential

**Standard deviation:**
- Low SD (< 0.8): Consensus (everyone agrees)
- High SD (> 1.2): Polarizing (some love, some hate)

**Bimodal distribution:**
- Two peaks (e.g., many 1s and many 5s, few 3s)
- **Indicates:** Two distinct segments (different tastes)
- **Action:** Market to one segment specifically, or reformulate for broader appeal

---

## 13. Hedonic Optimization Strategies

### 13.1 Universal Appeal vs. Niche

**Universal (target mean > 3.5, SD < 1.0):**
- Familiar notes (vanilla, citrus, soft florals)
- Moderate intensity
- No polarizing materials (avoid oud, heavy animalics for Western mass market)

**Niche (target passionate fans, accept high SD):**
- Unusual, complex, challenging notes
- May have lower mean (3.0) but intense loyalty from fans
- Example: Oud-heavy, leather, animalic

### 13.2 Intensity Tuning

**"Just right" scale:**
- 1 = Much too weak
- 2 = Slightly too weak
- 3 = Just right
- 4 = Slightly too strong
- 5 = Much too strong

**Target:** >60% say "just right" (3)

**Example analysis:**

| Intensity | % Respondents | Action |
|-----------|---------------|--------|
| Too weak (1-2) | 35% | **Increase concentration** |
| Just right (3) | 55% | - |
| Too strong (4-5) | 10% | - |

**Adjust:** Increase by 10-20% to bring "too weak" into "just right."

### 13.3 Balancing Top/Heart/Base Hedonics

**Measure hedonic at multiple timepoints:**
- 0-5 min (top note)
- 1-2 hours (heart)
- 4-8 hours (base)

**Example:**

| Timepoint | Hedonic | Issue |
|-----------|---------|-------|
| Top | 4.2 | ✓ Excellent |
| Heart | 3.1 | ⚠ Drops significantly |
| Base | 3.8 | ✓ Recovers |

**Diagnosis:** Heart note is weak link.

**Action:** Boost heart materials (florals, spices) by 20-30%.

---

## 14. Quick Reference Tables

### 14.1 Psychophysical Scales Comparison

| Method | Type | Pros | Cons | Best Use |
|--------|------|------|------|----------|
| Magnitude Estimation | Ratio | High resolution | Requires training | Research, expert panels |
| Category Scale | Interval | Easy, quick | Lower resolution | Consumer testing |
| Hedonic (9-point) | Interval | Standard, comparable | Ceiling effects | Consumer preference |
| LMS | Ratio | Universal anchor | Complex | Cross-modal research |
| VAS | Interval/Ratio | Continuous | Harder to analyze | Lab studies |

### 14.2 Typical JND Values (Perfumery)

| Parameter | JND (Typical) | Example |
|-----------|---------------|---------|
| Concentration | 20-30% | 5% → 6.25% to notice |
| Intensity (perceived) | 1 point on 5-point scale | 3 → 4 |
| Hedonic | 0.5 points on 5-point scale | 3.0 → 3.5 noticeable, 3.0 → 3.3 borderline |

### 14.3 Cultural Hedonic Trends (Generalizations)

| Region | Preferred Notes | Intensity | Longevity |
|--------|----------------|-----------|-----------|
| **North America** | Fresh, clean, citrus, soft florals | Moderate | Moderate (4-6h) |
| **Europe (West)** | Classic florals, aldehydic, chypre | Moderate-Strong | Moderate-Long (6-8h) |
| **Middle East** | Oud, amber, musk, incense, very sweet | Very Strong | Very Long (8-12h+) |
| **East Asia** | Light florals, fruity, green, aquatic | Light-Moderate | Light-Moderate (3-6h) |
| **Latin America** | Fruity, sweet, tropical florals | Strong | Moderate-Long (6-8h) |

**Caveat:** These are broad generalizations. Individual and within-region variation is enormous.

---

## References & Further Reading

**Classic Texts:**
- Stevens, S.S. (1975) - *Psychophysics* (foundational work on power law)
- Engen, T. (1982) - *The Perception of Odors* (comprehensive olfactory psychophysics)
- Lawless, H.T. & Heymann, H. (2010) - *Sensory Evaluation of Food* (methods applicable to perfume)

**Recent Research:**
- Yeshurun & Sobel (2010) - "An odor is not worth a thousand words" (odor description challenges)
- Herz (2016) - *The Scent of Desire* (odor, emotion, memory)
- Zarzo & Stanton (2009) - "Understanding the underlying dimensions in perfumers' odor perception space"

**Industry:**
- ASTM E679 (Standard Practice for Determination of Odor and Taste Thresholds)
- ISO 13301:2018 (Sensory analysis - Methodology - General guidance for measuring odour, flavour and taste detection thresholds)

**Critical Reminder:** Psychophysics provides tools, not absolute answers. Perception is subjective, variable, context-dependent. Use data to inform decisions, but always validate with real-world consumer testing.
