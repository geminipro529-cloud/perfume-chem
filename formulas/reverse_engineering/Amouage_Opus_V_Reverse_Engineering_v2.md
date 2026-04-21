# Amouage Opus V — "Woods Symphony" — Complete Reverse Engineering v2

**Date:** 2026-03-29  
**Batch Size:** 10.00 mL (scalable to 30 mL)  
**Target Concentration:** 25% EdP  
**Source Intelligence:** Amouage.com official notes, perfume chemistry first principles, ionone-family pharmacology, accord theory  
**Materials:** 34 ingredients from working inventory (all verified against `inventory.txt`)

---

## 1. Intelligence Dossier — What We Know

### Official Declared Notes (Amouage.com)

| Layer | Declared Notes |
|-------|---------------|
| **Top** | Orris, Rhum |
| **Heart** | Orris concrete, Jasmine, Rose |
| **Base** | Oud, Civet, Dry Woods |

**Classification:** EDP · FLORAL · AMBER · WOODY  
**Subtitle:** "Woods Symphony"  
**Release:** 2012, Library Collection  
**Creative Director:** Christopher Chong  

### Olfactive Character from Review Consensus

Opus V is **NOT** a clean, powdery, Dior Homme-style iris. It is a **dark, opulent, animalic iris** where the orris root is presented in its full earthy-buttery-violet splendor, wrapped in a smoky oud base and lifted by a boozy rhum accord in the opening. The key observations:

1. **Double-iris architecture** — Orris appears in BOTH top AND heart (rare). The top uses the violet-ketonic facets of irones; the heart uses the buttery-fatty character of orris concrete.
2. **Rhum is the surprise modifier** — Not a typical iris opening. The rum note gives warm, caramel-vanilla-spiced lift that bridges into the orris heart.
3. **Jasmine and Rose are SUPPORT materials** — They don't compete with the iris; they provide floral dimensionality and prevent the composition from becoming too linear.
4. **The base is DARK** — Oud + civet = animalic-smoky depth that grounds the powdery iris. "Woods Symphony" subtitle tells us the woody base is multi-layered and structural.
5. **The drydown reads WOODY-AMBER** — Not floral. The iris fades into an animalic-woody cocoon.

---

## 2. Reverse Engineering Strategy — Note-to-Material Translation

### 2.1 The Orris Problem

Real orris butter/orris concrete costs $40,000–80,000/kg. Amouage likely uses genuine orris concrete (they have the budget), but we must reconstruct the same olfactive effect using synthetic irones and ionone-family materials.

**What makes orris concrete smell like orris concrete?**

Orris concrete (from *Iris pallida* or *Iris germanica* rhizomes, aged 3+ years) contains:

| Component | % in Orris Concrete | Olfactive Contribution |
|-----------|---------------------|----------------------|
| **Alpha-Irone** | 12–18% | THE defining molecule. Violet-powdery-woody ketone. The "irisness." |
| **Myristic acid** | 60–80% | Fatty-waxy, gives the "buttery" orris body. Odorless but affects texture. |
| **Oleic/linoleic acids** | 5–10% | More fatty acids, contribute to smooth mouthfeel. |
| **Gamma-Irone** | 1–3% | Warmer, woodier than alpha-irone. |
| **Irone isomers (cis/trans)** | trace | Dimensional complexity. |
| **Methyl myristate** | 1–3% | Waxy character. |
| **Carotol** | trace | Earthy-root character (also found in carrot seed). |

**Reconstruction Strategy:**

- **Alpha Irone (10%)** at high dose → the defining irone character
- **Orivone** → buttery-warm orris that mimics the fatty acid context
- **Carrot Seed EO** → carotol content simulates the earthy root dimension
- **I-IRIS FTEC + Orris FTEC** → pre-balanced iris/orris accords as harmonic foundation
- **Ionone family stack** (Alpha, Beta, Allyl, Dihydro Beta, Irotyl) → builds a multi-dimensional ionone field that simulates the complexity of real orris

### 2.2 The Rhum Accord

Rum absolute is available in perfumery, but we don't have it. Rum's olfactive DNA decomposes as:

| Rum Character | Material Translation | Chemical Reasoning |
|--------------|---------------------|-------------------|
| Sweet vanilla warmth | **Ethyl Vanillin** (12× stronger than vanillin) | Rum's barrel-aging produces vanillin from lignin |
| Caramel/toffee body | **Maple Lactone (20%)** | Furaneol-like caramellic that reads as dark sugar |
| Resinous amber depth | **Labdanum** | Amber-balsamic warmth, bridges into orris |
| Balsamic sweetness | **Benzoin Resinoid (50% DPG)** | Cinnamic acid benzyl ester = warm churchy sweetness |
| Clove spice (rum spiciness) | **Eugenol** (trace) | The allylbenzene that defines spiced rum |

### 2.3 Oud Reconstruction

No real oud in inventory. Oud's olfactive DNA:

| Oud Facet | Material Translation | Chemical Reasoning |
|-----------|---------------------|-------------------|
| Smoky-phenolic | **Guaiacol** (trace, 15 µL) | 2-methoxyphenol, THE smoke molecule in oud |
| Dark-earthy | **Patchouli EO** | Patchoulol provides dark earth |
| Resinous-incense | **Myrrh EO** | Furanosesquiterpenes = resinous darkness |
| Dry woody | **Cedarwood EO Virginia** | Cedrol = dry architectural wood |
| Earthy-vetiver | **Vetiver EO** | Vetiverol = mineral-earth depth |

### 2.4 Civet Reconstruction

Real civet absolute (from civet cat secretions) is ethically problematic and unavailable. Civet's character in perfumery = dirty-animalic-fecal-musky depth:

| Civet Facet | Material Translation | Chemical Reasoning |
|------------|---------------------|-------------------|
| Dirty leather | **IBQ (10%)** at trace | Isobutyl quinoline = dirty-animalic, THE civet substitute |
| Fecal-indolic | **Indole (10%)** at trace | Indole at low dose = jasmine; at trace = animalic-fecal |

### 2.5 Dry Woods — "The Symphony"

The subtitle "Woods Symphony" tells us the woody base is polyphonic — multiple wood voices:

| Wood Voice | Material | Chemical Effect |
|-----------|----------|----------------|
| Abstract cedar cocoon | **Iso E Super** (heavy dose) | Tetramethyl acetyl octahydronaphthalene. THE molecular wood. |
| Amber-cedar bridge | **Vertofix Coeur** | Acetyl cedrene. Fixative + woody-amber hybrid. |
| Dry oakmoss | **Evernyl** | Methyl β-orsellinate. THE chypre dry-down. |
| Crystalline amber | **Ambrox Super (30%)** | Ambroxide. Mineral-crystalline-ambergris effect. |

---

## 3. The Opus V Iris Accord — Standalone Module

This is the heart of the fragrance and can be used as a standalone iris accord base for other compositions.

### 3.1 Ionone Family Architecture

The iris illusion is built from 8 ionone-family molecules, each contributing a distinct facet. This is NOT "adding iris smell" — it's building a **multidimensional ionone field** where the brain integrates overlapping signals into "orris."

```
                    VIOLET ←→ WOODY
                         ↑
                    Alpha Irone (THE irone)
                   /     |      \
          Alpha Ionone  Irotyl  Orivone
          (violet)    (iris)   (butter)
              |          |        |
         Beta Ionone   Ultralia  Orris FTEC
         (deep violet) (ghost)   (earthy)
              |
      Dihydro Beta Ionone ←→ Allyl Ionone
      (woody transition)     (powdery projection)
```

### 3.2 Material Roles in the Iris Accord

| # | Material | Dilution | Amount (µL) | Active µL | Chemical Role |
|---|----------|----------|-------------|-----------|---------------|
| 1 | Alpha Irone | 10% | 400 | 40 | **Primary irone.** *cis*-α-Irone = the defining molecule of orris root. Violet-powdery-woody ketone at C13. Threshold ~0.5 ppb — extremely tenacious. THIS is what makes iris smell like iris. |
| 2 | Orivone | neat | 120 | 120 | **Buttery orris concrete simulator.** Warm, fatty-buttery iris with slight carrot root quality. Mimics the myristic acid context of natural orris concrete. |
| 3 | I-IRIS FTEC | neat | 100 | 100 | **Pre-built iris foundation.** Balanced iris accord — provides harmonic blending of multiple ionone facets that would be hard to balance individually. |
| 4 | Orris FTEC | neat | 100 | 100 | **Pre-built orris accord.** Emphasizes the earthy-powdery-root dimension of orris rather than the violet-floral. Bridges iris into woody base. |
| 5 | Alpha Ionone | neat | 80 | 80 | **Violet-floral facet.** The lighter, more obviously "violet" ionone. Provides the floral top-lift to the iris accord. |
| 6 | Beta Ionone | neat | 60 | 60 | **Deep violet-woody.** Darker than Alpha Ionone, more tenacious. Adds depth and bridges into woody drydown. |
| 7 | Allyl Ionone (Ketone V) | neat | 40 | 40 | **Powdery projection.** Woody-violet with strong sillage. Named "Ketone V" for violet. Projects the iris outward. |
| 8 | Ultralia | neat | 40 | 40 | **Ghost iris transparency.** Ultra-diffusive, almost subliminal iris. At trace levels, creates an "iris halo" around the wearer without being identifiable as iris. |
| 9 | Irotyl | neat | 50 | 50 | **Iris character extension.** Extends and reinforces the iris tonality. Provides body to the ionone field. |
| 10 | Dihydro Beta Ionone | neat | 40 | 40 | **Woody-violet transition.** Bridges the violet ionone heart into the woody base. Less overtly floral than Beta Ionone. |
| 11 | Carrot Seed EO | neat | 20 | 20 | **Carotol earthy-root dimension.** Contains carotol, also found in orris root (*Iris pallida* rhizome). Adds the distinctive earthy-root character of orris concrete that pure ionones lack. NOT just "carrot" — it's the SAME terpenoid as in real orris. |
| | **IRIS ACCORD TOTAL** | | **1050** | **690** | 42% of concentrate |

### 3.3 Iris Accord Chemistry — Why This Stack Works

**The Ionone Integration Principle:**  
A single ionone (even Alpha Irone) reads as "a chemical." Multiple ionones at different ratios create a **constructive interference pattern** where the brain integrates overlapping olfactory receptor activations into the percept of "orris root" — the same way RGB pixels create "white."

**Key Ratios:**
- **Alpha Irone : Orivone** = 40:120 (active) = 1:3 → Orivone provides the body that contextualizes the irone sparkle
- **Alpha Ionone : Beta Ionone** = 80:60 = 4:3 → Standard violet ratio, slight bias toward lighter violet for projection
- **FTEC foundation : Individual molecules** = 200:520 = ~1:2.6 → FTECs provide the base harmony, individuals provide character
- **Ultralia dose** = 40 µL (~1.6% of concentrate) → Ghost-level, subliminal iris aura. Below perceptual threshold individually but contributes to the integrated percept.

**Active Irone Concentration:**  
40 µL Alpha Irone in 2500 µL concentrate = **1.6% active irone**  
In real orris concrete, irone content is 12–18%. Amouage would use ~0.5–1.0% orris concrete in concentrate, contributing 0.06–0.18% irone. Our 1.6% active irone is generous — deliberately so, because we lack the fatty acid matrix that makes real orris concrete's irone radiate slowly. The higher irone dose compensates for the missing lipid context.

---

## 4. Complete Formula — Opus V "Woods Symphony" Reconstruction

### 4.1 Full Ingredient Table

| # | Ingredient | Dilution | Amount (µL) | Amount (mL) | Accord Layer |
|---|-----------|----------|------------|------------|-------------|
| | **━━━ IRIS CORE ━━━** | | | | |
| 1 | Alpha Irone | 10% | 400 | 0.40 | Iris — primary irone character |
| 2 | Orivone | neat | 120 | 0.12 | Iris — buttery orris body |
| 3 | I-IRIS FTEC | neat | 100 | 0.10 | Iris — pre-built iris foundation |
| 4 | Orris FTEC | neat | 100 | 0.10 | Iris — pre-built orris earth |
| 5 | Alpha Ionone | neat | 80 | 0.08 | Iris — violet-floral facet |
| 6 | Beta Ionone | neat | 60 | 0.06 | Iris — deep violet-woody |
| 7 | Allyl Ionone (Ketone V) | neat | 40 | 0.04 | Iris — powdery projection |
| 8 | Ultralia | neat | 40 | 0.04 | Iris — ghost iris halo |
| 9 | Irotyl | neat | 50 | 0.05 | Iris — iris reinforcement |
| 10 | Dihydro Beta Ionone | neat | 40 | 0.04 | Iris — woody-violet bridge |
| 11 | Carrot Seed EO | neat | 20 | 0.02 | Iris — carotol root earth |
| | **━━━ RHUM ACCORD ━━━** | | | | |
| 12 | Ethyl Vanillin | neat | 30 | 0.03 | Rhum — barrel-aged vanilla |
| 13 | Maple Lactone | 20% | 60 | 0.06 | Rhum — caramel/toffee body |
| 14 | Labdanum | neat | 50 | 0.05 | Rhum — resinous amber warmth |
| 15 | Benzoin Resinoid | 50% DPG | 50 | 0.05 | Rhum — balsamic sweetness |
| 16 | Eugenol | neat | 15 | 0.015 | Rhum — clove spice (trace) |
| | **━━━ JASMINE·ROSE ━━━** | | | | |
| 17 | Hedione | neat | 200 | 0.20 | Floral — jasmine radiance amplifier |
| 18 | Jasmine FO | neat | 50 | 0.05 | Floral — jasmine character |
| 19 | Phenethyl Alcohol | neat | 40 | 0.04 | Floral — rose body (PEA) |
| 20 | Citronellol | neat | 30 | 0.03 | Floral — rose petal freshness |
| 21 | Indole | 10% | 20 | 0.02 | Floral — jasmine depth, animalic bridge |
| | **━━━ OUD·CIVET·DRY WOODS ━━━** | | | | |
| 22 | Iso E Super | neat | 230 | 0.23 | Woods — abstract cedar molecular cocoon |
| 23 | Patchouli EO | neat | 60 | 0.06 | Woods — dark earthy oud foundation |
| 24 | Cedarwood EO Virginia | neat | 50 | 0.05 | Woods — dry architectural cedar |
| 25 | Vetiver EO | neat | 30 | 0.03 | Woods — mineral earth depth |
| 26 | Guaiacol | neat | 15 | 0.015 | Oud — smoky-phenolic (trace!) |
| 27 | Myrrh EO | neat | 30 | 0.03 | Oud — dark resinous incense |
| 28 | IBQ | 10% | 30 | 0.03 | Civet — dirty leather animalic |
| 29 | Ambrox Super | 30% | 140 | 0.14 | Base — crystalline amber fixation |
| 30 | Vertofix Coeur | neat | 70 | 0.07 | Base — woody-amber bridge fixative |
| 31 | Evernyl | neat | 30 | 0.03 | Base — dry oakmoss character |
| | **━━━ STRUCTURAL ━━━** | | | | |
| 32 | Benzyl Salicylate | neat | 90 | 0.09 | Structure — diffusion cushion |
| 33 | Coumarin | 20% | 80 | 0.08 | Structure — powdery warmth bridge |
| 34 | Cashmeran | 20% | 50 | 0.05 | Structure — cashmere warmth |
| | **━━━━━━━━━━━━━━━━** | | | | |
| 35 | **Ethanol 96%** | — | — | **7.50** | Solvent |
| | **TOTAL** | | | **10.00** | |

### 4.2 Concentrate Breakdown

| Accord Layer | Volume (µL) | % of Concentrate | % of Total |
|-------------|------------|-----------------|-----------|
| Iris Core | 1050 | 42.0% | 10.5% |
| Rhum Accord | 205 | 8.2% | 2.05% |
| Jasmine·Rose | 340 | 13.6% | 3.4% |
| Oud·Civet·Dry Woods | 685 | 27.4% | 6.85% |
| Structural | 220 | 8.8% | 2.2% |
| **TOTAL CONCENTRATE** | **2500** | **100%** | **25.0%** |
| Ethanol | 7500 | — | 75.0% |

**Concentrate:** 2.50 mL (25.0% EdP)

---

## 5. Accord-by-Accord Chemical Analysis

### 5.1 IRIS CORE — 42% of Concentrate

**Why 42%?** Opus V declares orris in BOTH top and heart. This is an iris-dominant composition where the orris is not an accent — it IS the fragrance. Typical luxury iris fragrances allocate 25–40% to the iris accord (Dior Homme Intense ~30%, Prada Infusion d'Iris ~35%). Opus V's double-orris declaration and "dark iris" character justifies 42%.

**The Active Irone Budget:**

| Material | Volume | Active Factor | Active Dose |
|----------|--------|--------------|-------------|
| Alpha Irone (10%) | 400 µL | ×0.10 | 40 µL |
| Orivone (neat) | 120 µL | ×1.0 | 120 µL |
| I-IRIS FTEC | 100 µL | ~0.3 effective | ~30 µL |
| Orris FTEC | 100 µL | ~0.3 effective | ~30 µL |
| Alpha Ionone (neat) | 80 µL | ×1.0 | 80 µL |
| Beta Ionone (neat) | 60 µL | ×1.0 | 60 µL |
| Allyl Ionone (neat) | 40 µL | ×1.0 | 40 µL |
| Ultralia (neat) | 40 µL | ×1.0 | 40 µL |
| Irotyl (neat) | 50 µL | ×1.0 | 50 µL |
| Dihydro Beta Ionone | 40 µL | ×1.0 | 40 µL |
| Carrot Seed EO | 20 µL | ×1.0 | 20 µL |
| **TOTAL ACTIVE IRIS** | | | **~550 µL** |

The iris accord delivers ~550 µL of olfactively active iris material in 2500 µL concentrate = **22% iris activity** in the composition. This is high — deliberately so for olfactive fidelity to Opus V's iris-dominant character.

### 5.2 RHUM ACCORD — 8.2% of Concentrate

**Target Effect:** Warm, boozy, barrel-aged sweetness that opens the fragrance before yielding to the iris heart. NOT a full rum — a **rhum impression** that reads as "dark sugar warming into powder."

**Chemical Synergies:**
- Ethyl Vanillin (30 µL) + Benzoin (50 µL × 0.5 = 25 µL active) → vanillin-benzyl benzoate interaction creates "aged barrel" effect
- Maple Lactone (60 µL × 0.2 = 12 µL active) → furaneol-like caramellic gives the dark molasses body that distinguishes rum from plain vanilla
- Eugenol (15 µL trace) → 4-allyl-2-methoxyphenol = clove oil's main component. At trace dose, provides the spicy bite of spiced rum without reading as "clove"
- Labdanum (50 µL) → Amber-resinous warmth connects the rhum accord into the orris concrete's own resinous qualities

**Transition Chemistry:**  
The rhum accord is designed to **front-load and fade**. Ethyl Vanillin (bp ~285°C) and Eugenol (bp ~253°C) are semi-volatile — they project in the first 30 minutes, then yield to the iris heart. Labdanum and Benzoin persist and merge into the base.

### 5.3 JASMINE·ROSE — 13.6% of Concentrate

**Target Effect:** Floral dimensionality that supports the iris without competing. Opus V's heart declares "Orris concrete, Jasmine, Rose" — iris is FIRST. The jasmine and rose provide the floral lushness that prevents the iris from becoming austere.

**Material Rationale:**
- **Hedione at 200 µL (8% of concentrate)** — Methyl dihydrojasmonate. Radiance amplifier and volume expander. Makes the iris feel 3D rather than flat. Hedione's famous "aura effect" is critical for iris compositions — it lifts the heavy ionones into air.
- **Jasmine FO at 50 µL** — Pre-built jasmine character. Provides the narcotic, honeyed jasmine dimension.
- **PEA at 40 µL** — Rose body. Phenethyl Alcohol is the simplest rose approximation — clean, petally, slightly honey.
- **Citronellol at 30 µL** — Rose petal freshness. The terpenoid that makes rose smell "fresh" rather than "jammy."
- **Indole at 20 µL (10%)** = 2 µL active — At this trace dose, indole is below its fecal threshold and reads as jasmine/narcotic depth. It also simultaneously serves as the first plank of the **civet reconstruction** in the base.

### 5.4 OUD·CIVET·DRY WOODS — 27.4% of Concentrate

**Target Effect:** The "Symphony" — a polyphonic woody base with oud darkness, civet animalic depth, and multiple wood voices. This is where Opus V diverges from typical iris fragrances.

**Oud Reconstruction — 3-Material Simulation:**

| Material | Dose | Oud Facet Simulated |
|----------|------|-------------------|
| Guaiacol | 15 µL (0.6%) | THE smoky-phenolic that defines oud's medicinal top. At 0.6% of concentrate, it whispers "smoke" without becoming dominant. Guaiacol is literally found in distilled agarwood. |
| Patchouli EO | 60 µL (2.4%) | Patchoulol provides the dark, earthy, damp-wood character. This is the BODY of the oud simulation. |
| Myrrh EO | 30 µL (1.2%) | Furanosesquiterpenes add dark, resinous, temple-incense quality that real oud has from its bacterial origin. |

**Civet Reconstruction — 2-Material Simulation:**

| Material | Dose | Active | Civet Facet |
|----------|------|--------|------------|
| IBQ (10%) | 30 µL | 3 µL | Isobutyl quinoline at 0.12% of concentrate. Dirty-leather-animalic. THE IFRA-approved civet substitute. At this dose, it reads as "something animalic underneath" — not dirty, not clean, just... alive. |
| Indole (10%) | 20 µL | 2 µL | Already counted in the jasmine accord. Does double duty — jasmine AND civet depth at trace. Classic perfumery trick. |

**"Dry Woods" Multi-Voice Stack:**

| Material | Dose | Wood Character |
|----------|------|---------------|
| Iso E Super | 230 µL (9.2%) | Abstract cedar molecular cocoon. The most-used woody molecule in modern perfumery. At 9.2%, it creates a volumetric woody halo around the entire composition. This is the "symphony conductor." |
| Cedarwood EO Virginia | 50 µL (2.0%) | Cedrol-rich dry architectural wood. Reads as "cabinet" or "pencil shavings." The most literal interpretation of "dry woods." |
| Vetiver EO | 30 µL (1.2%) | Vetiverol and khusimol provide mineral-earth-dark wood. Not smoky vetiver — earthy vetiver. |
| Vertofix Coeur | 70 µL (2.8%) | Acetyl cedrene — a woody-amber bridge that acts as fixative AND character material. Connects the cedar-patchouli woods to the amber base. |
| Evernyl | 30 µL (1.2%) | Methyl β-orsellinate. The synthetic oakmoss. Provides dry, mossy, forest-floor character. In the "dry woods" context, it adds the moss-and-leaf dimension that natural woodland has. |

**Amber Foundation:**
- **Ambrox Super (30%)** at 140 µL = 42 µL active ambroxide. Crystalline-mineral amber that provides the "amber" in "FLORAL · AMBER · WOODY." At 1.7% active in concentrate, it creates the mineral-warm base that all the woody materials sit on.

### 5.5 STRUCTURAL MATERIALS — 8.8% of Concentrate

| Material | Dose | Structural Function |
|----------|------|-------------------|
| Benzyl Salicylate | 90 µL | **Diffusion cushion.** Salicylate ester that makes the composition radiate from skin rather than sitting close. Also a fixative — extends longevity of the lighter iris materials. Creates the "cosmetic transparency" effect. |
| Coumarin (20%) | 80 µL (16 µL active) | **Powdery warmth bridge.** Coumarin (from tonka bean) is the classic "powdery" molecule. Bridges the iris's inherent powderiness into the warm base. At 0.64% active, it's below its hay/almond threshold — simply reads as "powder." |
| Cashmeran (20%) | 50 µL (10 µL active) | **Cashmere warmth.** 6,7-Dihydro-1,1,2,3,3-pentamethyl-4(5H)-indanone. Musky-spicy-woody with a cashmere sensation. Not declared in notes but provides the "luxury textile" feel that Amouage fragrances are known for. |

---

## 6. Temporal Architecture — How It Unfolds

### Phase 1: The Rhum Opening (0–15 minutes)

**What fires:** Eugenol (bp 253°C), Citronellol (bp 225°C), Ethyl Vanillin (bp 285°C), Alpha Ionone (bp 229°C), top facets of the FTEC blends, Linalool from Carrot Seed EO.

**Perceived Effect:** Warm, boozy-sweet opening with a violet-powder flash. The rhum accord creates an unexpected first impression — this is NOT the austere iris opening of Prada Infusion d'Iris. It's dark, warm, inviting. The Alpha Ionone provides the first "iris signal" before the full orris accord develops.

### Phase 2: The Orris Concrete Heart (15 min – 2 hours)

**What dominates:** Alpha Irone (bp ~305°C, extremely tenacious), Orivone, both FTECs, Beta Ionone, Irotyl, Hedione radiance amplification.

**Perceived Effect:** The rhum warmth yields to a buttery, earthy, powdery orris concrete. This is the CORE of Opus V — a rich, opulent iris that reads as "natural root" rather than "synthetic violet." The Orivone provides butter, the Carrot Seed provides earth, and the irone provides the defining character. Hedione at 8% amplifies the iris into radiating sillage.

The jasmine (Hedione + Jasmine FO + Indole) and rose (PEA + Citronellol) become perceptible as SUPPORTING voices — they give the iris floral context, preventing it from becoming monolithic.

### Phase 3: The Dark Transition (2–4 hours)

**What emerges:** Iso E Super (extremely tenacious, bp ~300°C), Patchouli sesquiterpenes, Guaiacol smokiness, IBQ animalic-leather, Ambrox crystalline amber.

**Perceived Effect:** The iris heart begins to darken. Oud-like smokiness (Guaiacol + Patchouli + Myrrh) seeps through. Civet-like animalic warmth (IBQ + Indole) adds a primal dimension. The composition transitions from "opulent floral" to "dark floral-wood."

### Phase 4: Woods Symphony Drydown (4–12+ hours)

**What persists:** Iso E Super, Vertofix Coeur, Evernyl, Ambrox Super, Benzyl Salicylate, residual Alpha Irone (irone is extremely tenacious), Cashmeran.

**Perceived Effect:** A woody-amber-musky cocoon with ghost-irone iris still detectable underneath. This is the "Woods Symphony" — Iso E providing abstract cedar, Vertofix adding amber-cedar, Evernyl giving dry moss, and Ambrox providing the crystalline mineral finish. The iris never fully disappears — Alpha Irone's sub-ppb threshold means trace amounts continue to register for hours.

---

## 7. Scaling to 30 mL

Multiply all amounts by 3×:

| Ingredient | 10 mL (µL) | 30 mL (µL) | 30 mL (mL) |
|-----------|-----------|-----------|-----------|
| Alpha Irone (10%) | 400 | 1200 | 1.20 |
| Orivone | 120 | 360 | 0.36 |
| I-IRIS FTEC | 100 | 300 | 0.30 |
| Orris FTEC | 100 | 300 | 0.30 |
| Alpha Ionone | 80 | 240 | 0.24 |
| Beta Ionone | 60 | 180 | 0.18 |
| Allyl Ionone | 40 | 120 | 0.12 |
| Ultralia | 40 | 120 | 0.12 |
| Irotyl | 50 | 150 | 0.15 |
| Dihydro Beta Ionone | 40 | 120 | 0.12 |
| Carrot Seed EO | 20 | 60 | 0.06 |
| Ethyl Vanillin | 30 | 90 | 0.09 |
| Maple Lactone (20%) | 60 | 180 | 0.18 |
| Labdanum | 50 | 150 | 0.15 |
| Benzoin Resinoid (50% DPG) | 50 | 150 | 0.15 |
| Eugenol | 15 | 45 | 0.045 |
| Hedione | 200 | 600 | 0.60 |
| Jasmine FO | 50 | 150 | 0.15 |
| Phenethyl Alcohol | 40 | 120 | 0.12 |
| Citronellol | 30 | 90 | 0.09 |
| Indole (10%) | 20 | 60 | 0.06 |
| Iso E Super | 230 | 690 | 0.69 |
| Patchouli EO | 60 | 180 | 0.18 |
| Cedarwood EO Virginia | 50 | 150 | 0.15 |
| Vetiver EO | 30 | 90 | 0.09 |
| Guaiacol | 15 | 45 | 0.045 |
| Myrrh EO | 30 | 90 | 0.09 |
| IBQ (10%) | 30 | 90 | 0.09 |
| Ambrox Super (30%) | 140 | 420 | 0.42 |
| Vertofix Coeur | 70 | 210 | 0.21 |
| Evernyl | 30 | 90 | 0.09 |
| Benzyl Salicylate | 90 | 270 | 0.27 |
| Coumarin (20%) | 80 | 240 | 0.24 |
| Cashmeran (20%) | 50 | 150 | 0.15 |
| **Ethanol 96%** | — | — | **22.50** |
| **TOTAL** | | | **30.00** |

**30 mL Concentrate:** 7.50 mL (25.0%)

---

## 8. Critical Tuning Notes

### What to Watch For

1. **If the iris reads too "violet" and not enough "orris"** → Increase Orivone by 20–30% and add 10 µL more Carrot Seed EO. The buttery-earthy dimension is what separates orris from violet.

2. **If the rhum accord is too sweet** → Reduce Ethyl Vanillin to 15 µL and increase Eugenol to 20 µL. Shift the balance from sweet to spicy.

3. **If the oud simulation is too smoky** → Reduce Guaiacol to 8–10 µL. Guaiacol is extremely potent; even 5 µL can be perceptible.

4. **If the civet/animalic is too dirty** → Reduce IBQ to 15 µL (10%) = 1.5 µL active. IBQ has a steep dose-response curve — the line between "intriguing" and "unwashed" is 1–2 µL.

5. **If the drydown is too abstract/woody and not enough iris** → Increase Alpha Irone to 500 µL. Irone is so tenacious that this extra dose will push iris presence deep into the drydown.

6. **If the composition lacks projection** → Increase Hedione to 250–300 µL. Hedione is the radiance engine; more Hedione = more "aura."

### Maturation

- **Day 0–3:** Ethanol bite, materials smell separate and angular.
- **Day 3–7:** Rhum accord integrates first. Iris materials begin to coalesce.
- **Week 1–2:** Iris-wood transition smooths out. The "orris concrete" character develops as Orivone integrates with the irone.
- **Week 2–4:** Full integration. Civet/oud base melts into the iris heart. The composition becomes seamless.
- **1 month+:** Peak. The ionone field has fully matured. Ambrox and Iso E Super have mellowed into the molecular cocoon.

**Minimum maturation: 2 weeks. Optimal: 4–6 weeks.**

---

## 9. Comparison: This Reconstruction vs. Iris Impériale (F1)

| Parameter | Iris Impériale (F1) | Opus V Reconstruction |
|-----------|-------------------|---------------------|
| Iris approach | Clean powdery iris (Dior Homme DNA) | Dark earthy orris concrete |
| Ionone materials used | 3 (Alpha Irone, Orivone, Methyl Ionone) | 11 (full ionone stack + FTECs) |
| Base character | Suede-sandalwood-cashmere | Oud-civet-dry woods |
| Animalic content | None | IBQ + Indole (civet simulation) |
| Opening | Bergamot-cardamom | Rhum (boozy-vanilla-spice) |
| Jasmine presence | No | Yes (Hedione + Jasmine FO) |
| Rose presence | No | Yes (PEA + Citronellol) |
| Woody base depth | Moderate (Iso E + Cashmeran) | Heavy (6 wood materials + oud sim) |
| Character | Transparent-luminous | Opaque-dark-opulent |
| Concentration | 25% | 25% |

**Key Difference:** Iris Impériale is Dior Homme territory — clean, sculptural, suede-wrapped iris. Opus V is the **opposite** — dirty, dark, resinous iris drowning in oud and civet. Same plant genus, completely different olfactive philosophy.

---

## 10. Theoretical Grounding

### The Roudnitska Principle Applied

Edmond Roudnitska's "Complements" theory states that a fragrance ingredient's full character only reveals itself when placed against its complement. For iris:

- **Iris + Woods** = reveals iris's powdery dimension (standard approach, see Dior Homme)
- **Iris + Animalic** = reveals iris's earthy-root dimension (Opus V's choice)
- **Iris + Aldehydes** = reveals iris's waxy-metallic dimension (Chanel No. 19)

Opus V deliberately places iris against its **animalic complement** (civet + oud), which foregrounds the earthy, buttery, root-like qualities of orris concrete rather than its violet-powdery facets. This is why the reconstruction MUST include IBQ and Indole — without the animalic complement, the iris reads as violet powder, not orris earth.

### Jellinek Map Position

Opus V occupies the **WARM–NARCOTIC** quadrant of the Jellinek scent diagram:
- X-axis: Warm (rhum, benzoin, oud, civet) rather than Cool
- Y-axis: Narcotic/Erogenous (iris root, animalic, heavy floral) rather than Anti-erogenous

This contrasts with most iris fragrances which sit in the **COOL–ANTI-EROGENOUS** quadrant (clean, intellectual, powdery).

### Material Cost Analysis

| Material | Quantity (10mL) | Est. Cost |
|----------|----------------|-----------|
| Alpha Irone (10%) | 400 µL | ~$2.40 |
| Orivone | 120 µL | ~$0.60 |
| FTECs (2×) | 200 µL | ~$0.80 |
| Ionones (5 materials) | 270 µL | ~$1.10 |
| Hedione | 200 µL | ~$0.30 |
| Iso E Super | 230 µL | ~$0.15 |
| Essential Oils (6) | 240 µL | ~$1.80 |
| Ambrox Super (30%) | 140 µL | ~$0.80 |
| All others | 600 µL | ~$2.00 |
| Ethanol | 7500 µL | ~$1.00 |
| **TOTAL** | | **~$10.95** |

For a 10 mL bottle of an Opus V reconstruction = **~$11/10mL** (vs. $395/100mL retail = $39.50/10mL). The hobbyist version costs ~28% of retail even with generous material dosing.

---

*Formula verified against inventory.txt (2026-03-26, 103 materials). All 34 ingredients confirmed available.*
