# Dual Rating System Comparison — Stars vs Scores

**Implemented:** March 28, 2026  
**Purpose:** Comprehensive formula evaluation using complementary methodologies

---

## System Overview

The perfume evaluation framework uses **two parallel rating systems**, each measuring different aspects:

### 1. ★ 10-Star Ratings — Wearability & Consumer Appeal
**Scale:** 0.0–10.0 stars (★★★★★★★★★★)  
**Focus:** Subjective wearability, versatility, originality  
**Target audience:** Consumers, fragrance enthusiasts  
**Question answered:** *"How will this perfume perform in real-world use?"*

**Characteristics evaluated:**
- **Wearability** — Comfort, not challenging, daily wearability
- **Versatility** — Season/occasion flexibility, day-to-night capability
- **Originality** — Uniqueness, creativity, non-generic character
- **Sophistication** — Refinement, artistry, perfumer skill level
- **Signature Potential** — Memorability, identity-building capability
- **Mass Appeal** — Compliment factor, crowd-pleasing (vs niche)
- **Gender Versatility** — Unisex rating, not polarizing
- **Age Range** — Broad age appropriateness (18-80 vs narrow)
- **Formula Elegance** — Structural elegance, fixative anchoring, proportion rationality
- **Value for Money** — Quality-to-cost ratio

### 2. ▣ 0-100 Scores — Technical Composition Metrics
**Scale:** 0–100 points  
**Focus:** Objective structural quality, compositional excellence  
**Target audience:** Perfumers, chemists, technicians  
**Question answered:** *"How well is this formula constructed technically?"*

**Axes evaluated:**
- **Longevity** — Duration on skin (VP, fixatives, tenacity)
- **Sillage** — Diffusion, projection, radius
- **Balance** — Top-to-heart-to-base ratio, structural harmony
- **Theory** — Alignment with perfumery principles (pairing, synergy rules)
- **Radiance** — Luminosity, halo effect (Hedione, Iso E, aldehydes)
- **Texture** — Tactile diversity, layering, volume
- **Complexity** — Structural diversity (dimensions, roles, characters)
- **Character Balance** — Olfactive profile evenness (dimension CV)
- **Synergy** — Ingredient pairing effectiveness
- **Cost** — Material expense (inversely scored)

---

## Key Differences

| Aspect | ★ Star Ratings | ▣ Scores |
|--------|---------------|----------|
| **Objectivity** | Subjective (consumer experience) | Objective (measurable properties) |
| **Calculation** | Heuristic, character-driven | Algorithmic, formula-vector-driven |
| **Target User** | Buyers, wearers, enthusiasts | Formulators, perfumers, chemists |
| **Question** | "Will I like wearing this?" | "Is this well-constructed?" |
| **Examples** | Wearability, mass appeal, originality | Longevity, sillage, balance |
| **Scoring Model** | Linear (0-10, higher = better) | Weighted mean (0-100, geometric) |
| **Emphasis** | Real-world utility | Technical excellence |

---

## Why Both Systems?

**Example scenario:** A formula could score 9★ wearability (easy, comfortable, crowd-pleasing) but only 60/100 balance (top-heavy structure). This tells us:

- ✅ **For consumers:** Great daily wear, pleasant, versatile
- ⚠️ **For perfumers:** Structural weakness, needs rebalancing

Conversely, a formula might score 85/100 complexity (many dimensions, roles) but only 5★ wearability (challenging, polarizing). This means:

- ⚠️ **For consumers:** Difficult, acquired taste, niche
- ✅ **For perfumers:** Sophisticated construction, artistic achievement

**Use cases:**
- **Optimization:** Use **scores** to identify technical flaws (balance, longevity), use **stars** to predict market reception
- **Consumer guidance:** Present **stars** for purchase decisions ("9★ versatility = wear year-round")
- **Perfumer training:** Present **scores** for compositional learning ("balance 26/100 = fix top-to-base ratio")
- **Product positioning:** High stars + high scores = luxury niche; high stars + low scores = mass market; low stars + high scores = artistic/challenging

---

## Implementation Notes

- **Star ratings** computed from character radar + material analysis
- **Scores** computed from FormulaVector properties + ingredient intelligence DB
- **Both run in parallel** — no conflict, complementary perspectives
- **Geometric mean** used for score composite (penalizes weaknesses)
- **Arithmetic mean** used for star composite (balanced overview)
