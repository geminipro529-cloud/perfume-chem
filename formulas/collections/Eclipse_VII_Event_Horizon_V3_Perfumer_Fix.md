# Eclipse VII — Event Horizon — V3 Perfumer Logic Fix

## Summary

| | Original (FP) | V2 Optimizer | **V3 Perfumer Fix** |
|---|---|---|---|
| Materials | 35 | 43 | **36** |
| Concentrate | 3,745 µL | 4,953 µL | **2,113 µL** |
| Concentration | 37.5% | 49.5% | **21.1% (EDP)** |
| Geometric Score | 81.4 | 84.1 | **81.9** |
| Stacking Depth | 75.0 | 80.0 | **80.0** |
| Sillage | 92.5 | 92.8 | **96.2** |
| Smoky | 0.30 | 0.23 ↓ | **0.38 ↑** |
| Creamy | 1.28 | 1.78 | **1.36** |
| Woody | 2.90 | 3.00 | **3.04** |
| Dominant Style | oriental | oriental | **oriental** |

**Verdict:** V3 scores 81.9 geometric (vs 81.4 original, +0.5) while reducing concentrate by 44% to hit EDP concentration. MORE importantly: V2 destroyed the leather-smoke identity (smoky dropped 0.30→0.23, spicy 0.49→0.37, animalic 0.37→0.29) while pumping creamy through 6 gourmand additives. V3 **restores and strengthens** the leather-smoke identity (smoky +0.08, spicy +0.10, animalic +0.10) with proportional creamy gain.

---

## Step 1 — Diagnosis: What the V2 Optimizer Got Wrong

The 5-pass direction-locked optimizer (V2) scored well on paper (geometric 84.1) but made several perfumer-logic errors:

### 1A. Concentration Absurdity
V2 produced 4,953 µL concentrate in a 10 mL reference = **49.5% concentration**. That's extrait territory. The user wants EDT-EDP (15–20%). At 30 mL, multiplying ×3 gives 14,859 µL = 49.5%. The formula needs to sit at ~2,000 µL (10 mL reference) for a practical EDP.

### 1B. Radiance Drowning Leather-Smoke
Hedione inflated from 450 → **700 µL** (14% of all concentrate). In a dark leather-smoke composition, Hedione's transparent radiance works AGAINST the concept. At 700 µL, the fragrance becomes a sheer floral wash with leather undertones — the reverse of what Eclipse VII should be.

### 1C. Molecular Cocoon Anosmia Risk
Iso E Super at **500 µL** (10% of concentrate) risks anosmia. At this dose, ~30% of people won't smell the cedar cocoon at all — they'd get a weaker version of the fragrance with a structural hole.

### 1D. Musk Drowning
Ethylene Brassylate at **500 µL** + Galaxolide at **435 µL** = 935 µL (19% of concentrate) is an enormous lactonic-synthetic musk bed. This competes with the leather-smoke core for olfactive space, pushing the frag toward "clean laundry with leather" rather than "dark leather with molecular depth."

### 1E. Sandalwood Takeover
Javanol inflated from 70 → **200 µL** + Ebanol from 60 → **136 µL** = 336 µL sandalwood. At this dose, the fragrance reads as a sandalwood composition with leather nuances, not a leather composition with creamy texture.

### 1F. Gourmand Battery (6 Additions)
The optimizer added Delta Decalactone (30), Gamma Decalactone (58), Gamma Undecalactone (40), Maple Lactone (52), Ethyl Vanillin (34), and Vanillin (30) — **six** sweet/lactonic materials totaling 244 µL. This is how a gourmand fragrance is built, not how you add "creamy, smooth, tender" to a leather-smoke composition.

For creamy in leather: you want **Ebanol** (creamy sandalwood), **Cashmeran** (textile warmth), **EB** (lactonic depth), and maybe **one** lactone. Not six.

### 1G. Structural Materials Crushed
The optimizer reduced several essential structural materials to near-nothing:
- **Timberol**: 70 → 23 µL (architectural wood gutted)
- **Vertofix Coeur**: 50 → 24 µL (woody-musky bridge gutted)
- **Benzyl Salicylate**: 105 → 35 µL (diffusion cushion gutted)
- **Benzyl Benzoate**: 80 → 27 µL (fixative anchor gutted)

These materials don't score well individually (near-odorless in the case of BB, subtle cushion effect for BSal) but they provide the invisible architecture that holds a fragrance together.

### 1H. Identity Erosion Hidden by Numbers
The V2 radar tells the story: **smoky dropped** (0.30→0.23), **spicy dropped** (0.49→0.37), **animalic dropped** (0.37→0.29). The optimizer gained creamy (+0.50) by DILUTING the leather-smoke character in a sea of musks, lactones, and sandalwood. The geometric score went up because texture, luxury, and stacking_depth improved — but the perfume's IDENTITY was weakened. A perfumer would catch this instantly.

---

## Step 2 — Remove Unavailable Materials

Three materials are no longer available:

| Material | V2 Dose | Role | Redistribution |
|---|---|---|---|
| **Kephalis** | 13 µL | Powerful woody-amber | Already near-negligible at 13 µL. Role absorbed by existing Ambrox + Norlimbanol. No redistribution needed. |
| **Orivone** | 21 µL | Buttery orris | Score-chasing addition — iris-buttery character has no place in leather-smoke. No redistribution needed. |
| **Habanolide** | 147 µL | Warm skin musk (depth axis) | Meaningful role. Redistribute to: **Exaltolide** +40 µL (skin-fatty intimate quality), **Romandolide** +40 µL (projection musk). Remaining 67 µL absorbed by formula compression. |

---

## Step 3 — Strip Gourmand Overload

Remove 4 of 6 V2-added sweet materials. Keep only Gamma Decalactone (peach-skin, the most "leather-compatible" lactone) and Vanillin (trace sweetness):

| Material | V2 Dose | Active | Action | Reason |
|---|---|---|---|---|
| **Delta Decalactone** | 30 µL (10%) | 3 µL | REMOVE | Buttery lactone — 3 µL active is subliminal AND gourmand-coded |
| **Gamma Undecalactone** | 40 µL (10%) | 4 µL | REMOVE | Peach-depth — 4 µL active is subliminal, redundant with Gamma Deca |
| **Maple Lactone** | 52 µL (20%) | 10.4 µL | REMOVE | Sweet maple — wrong register for dark leather, reads gourmand |
| **Ethyl Vanillin** | 34 µL (30%) | 10.2 µL | REMOVE | Redundant with Vanillin, Ethyl Vanillin has harsher synthetic edge |
| **Gamma Decalactone** | 58 µL (neat) | 58 µL | **KEEP at 20 µL** | Peach-skin creaminess — controlled trace for skin-leather texture |
| **Vanillin** | 30 µL (10%) | 3 µL | **KEEP at 20 µL** | Trace sweetness — rounds balsamic-leather juncture |

---

## Step 4 — Reduce Inflated Materials for EDP Concentration

Target: ~2,000–2,200 µL concentrate at 10 mL reference → ~21% EDP at 30 mL.

| Material | V2 Dose | V3 Dose | Change | Perfumer Rationale |
|---|---|---|---|---|
| **Hedione** | 700 | **200** | −500 | Radiance amplifier must SUPPORT leather darkness, not drown it. 200 µL still provides diffusion lift without floral wash. |
| **Iso E Super** | 500 | **150** | −350 | Molecular cocoon at 150 is enough for skin-adhesion halo without anosmia risk (~10% probability vs ~30% at 500). |
| **Ethylene Brassylate** | 500 | **100** | −400 | Lactonic depth musk at 100 provides creamy undertone without competing with leather for olfactive foreground. |
| **Javanol** | 200 | **40** | −160 | Dry mineral sandalwood for skin-scent intimacy, not a sandalwood feature note. 40 µL = support register. |
| **Cedarwood EO** | 300 | **60** | −240 | Natural cedar warmth at 60 provides wood identity without pencil-shaving heaviness. |
| **Ebanol** | 136 | **60** | −76 | Creamy sandalwood at 60 — still the main creamy contributor but not overwhelming leather character. |
| **Galaxolide** | 435 | **160** | −275 | 80% → 128 µL active. Sterile void concept preserved at proportional level. |
| **Suederal** | 200 | **120** | −80 | 10% → 12 µL active suede. Proportional to leaner formula. |
| **Evernyl** | 150 | **100** | −50 | Oakmoss darkness — still substantial at 100, proportional to concentrate. |
| **Vetiver EO** | 150 | **100** | −50 | Earthy-smoky backbone — proportional reduction, still the second-heaviest heart note. |

---

## Step 5 — Restore Crushed Structural Materials

The optimizer starved these materials. Restoring them:

| Material | V2 Dose | V3 Dose | Change | Perfumer Rationale |
|---|---|---|---|---|
| **Timberol** | 23 | **50** | +27 | Architectural angular cedarwood needs presence to provide geometric structure. At 23 it was inaudible — at 50 it contributes dry angular framework. |
| **Vertofix Coeur** | 24 | **40** | +16 | Woody-musky bridge glues the wood section to the musk section. At 24 the bridge was broken — at 40 it seals the transition. |
| **Benzyl Salicylate** | 35 | **80** | +45 | Diffusion cushion — the cosmetic warmth that makes the leather WEARABLE. At 35 the leather was raw; at 80 it's cradled in salicylate volume. |
| **Benzyl Benzoate** | 27 | **50** | +23 | Invisible fixative anchor — adds molecular weight without character. At 27 the base had no anchor; at 50 it holds everything together longer. |

---

## Step 6 — Redistribute Habanolide's Depth-Axis Role

Habanolide provided 147 µL of warm-skin musk on the depth axis. Without it, the musk chord needs rebalancing:

| Musk Material | Original | V3 | Axis | Notes |
|---|---|---|---|---|
| **Ethylene Brassylate** | 300 | 100 | Depth | Lactonic-creamy — reduced from V2's 500 but still the depth anchor |
| **Galaxolide** | 420 | 160 | Depth/Character | 80% → 128 µL active. Synthetic void character-echo |
| **Romandolide** | *(new in V2: 60)* | **80** | Projection | Clean slightly woody musk. Takes over Habanolide's outward sillage component |
| **Exaltolide** | 80 | **100** | Depth/Skin | 10% → 10 µL active. Skin-fatty intimate quality fills Habanolide's warm-intimate gap |
| **Zenolide** | 42 | 20 | Character | Cold fresh void — proportional |

**Musk chord architecture:**
- Depth axis: EB (100) + Galaxolide (160) = 260 µL → warm-synthetic depth
- Projection axis: Romandolide (80) → extends sillage outward
- Intimate axis: Exaltolide (100 @ 10% = 10 active) → skin adhesion
- Cold accent: Zenolide (20) → crystalline void touch
++
---

## Step 7 — Final Formula: Eclipse VII — Event Horizon V3

**36 materials · 2,113 µL concentrate (10 mL reference) · 21.1% EDP**

### 30 mL EDT/EDP Mixing Guide

| # | Ingredient | Dil | µL (10 mL) | µL (30 mL) | mL (30 mL) | Notes |
|---|---|---|---|---|---|---|
| | **— TOP: Escape Velocity —** | | | | | |
| 1 | Black Pepper FTEC | neat | 50 | 150 | 0.150 | spicy kinetic heat |
| 2 | Cedrat FCF oil Sicilian | neat | 50 | 150 | 0.150 | bitter mineral citron |
| 3 | Ethyl Safranate | neat | 20 | 60 | 0.060 | saffron metallic warmth |
| 4 | Pink Pepper Base | neat | 40 | 120 | 0.120 | aromatic pink peppercorn |
| | **— HEART: Gravitational Pull —** | | | | | |
| 5 | Hedione | neat | 200 | 600 | 0.600 | controlled radiance amplifier |
| 6 | Suederal | 10% | 120 | 360 | 0.360 | suede leather pull (12 µL active) |
| 7 | Evernyl | neat | 100 | 300 | 0.300 | oakmoss-chypre darkness |
| 8 | Vetiver EO | neat | 100 | 300 | 0.300 | dry earthy-smoky backbone |
| 9 | Guaiacol | neat | 8 | 24 | 0.024 | phenolic campfire smoke |
| 10 | Eugenol | neat | 25 | 75 | 0.075 | clove dark heat |
| 11 | Isobutyl Quinoline | 10% | 10 | 30 | 0.030 | subliminal animalic danger (1 µL active) |
| | **— BASE: Singularity —** | | | | | |
| | *Woody Structure* | | | | | |
| 12 | Iso E Super | neat | 150 | 450 | 0.450 | molecular cocoon — abstract cedar skin-halo |
| 13 | Cedarwood EO | neat | 60 | 180 | 0.180 | natural cedar warmth |
| 14 | Timberol | neat | 50 | 150 | 0.150 | architectural angular cedarwood |
| 15 | Clearwood | neat | 30 | 90 | 0.090 | dark modern woody (clean patchouli replacement) |
| 16 | Vertofix Coeur | neat | 40 | 120 | 0.120 | woody-musky bridge |
| 17 | Patchouli EO | neat | 25 | 75 | 0.075 | dark earthy texture |
| 18 | Norlimbanol Dextro | neat | 5 | 15 | 0.015 | rigid structural pillar (ODT 0.05 ppm) |
| | *Amber* | | | | | |
| 19 | Ambrox Super | 30% | 60 | 180 | 0.180 | crystalline mineral depth (18 µL active) |
| 20 | Ambrofix | 30% | 40 | 120 | 0.120 | smoother amber complement (12 µL active) |
| 21 | Amberwood F | neat | 25 | 75 | 0.075 | transparent warmth |
| | *Musk (No Habanolide)* | | | | | |
| 22 | Ethylene Brassylate | neat | 100 | 300 | 0.300 | lactonic depth musk — creamy undertone |
| 23 | Galaxolide | 80% | 160 | 480 | 0.480 | sterile synthetic void (128 µL active) |
| 24 | Romandolide | neat | 80 | 240 | 0.240 | projection musk — extends sillage outward |
| 25 | Exaltolide | 10% | 100 | 300 | 0.300 | skin-fatty intimate musk (10 µL active) |
| 26 | Zenolide | neat | 20 | 60 | 0.060 | cold fresh void accent |
| | *Creamy-Tender* | | | | | |
| 27 | Cashmeran | 20% | 80 | 240 | 0.240 | textile warmth — cashmere softness (16 µL active) |
| 28 | Ebanol | neat | 60 | 180 | 0.180 | creamy sandalwood — THE cream note |
| 29 | Javanol | neat | 40 | 120 | 0.120 | dry mineral sandalwood — skin intimacy |
| | *Balsamic / Sweet* | | | | | |
| 30 | Benzoin Resinoid | 50% | 25 | 75 | 0.075 | balsamic smoothness (12.5 µL active) |
| 31 | Coumarin | 20% | 30 | 90 | 0.090 | hay-tonka warmth (6 µL active) |
| 32 | Gamma Decalactone | neat | 20 | 60 | 0.060 | peach-skin lactonic trace — ONE lactone only |
| 33 | Vanillin | 10% | 20 | 60 | 0.060 | trace sweetness (2 µL active) |
| | *Fixative Gradient* | | | | | |
| 34 | Benzyl Salicylate | neat | 80 | 240 | 0.240 | diffusion cushion — cosmetic wearability |
| 35 | Hexyl Salicylate | neat | 40 | 120 | 0.120 | transparent fixative — invisible adhesion |
| 36 | Benzyl Benzoate | neat | 50 | 150 | 0.150 | invisible anchor mass |
| | **— SOLVENT —** | | | | | |
| | Ethanol (190 proof) | — | — | 23,661 | 23.66 | |
| | **TOTAL** | | **2,113** | **30,000** | **30.00** | |

**Concentration: 21.1% (EDP)**

---

## Step 8 — Scoring Results

### Individual Axis Scores (Custom Weights for Creamy/Smooth/Tender/Woody Depth)

| Axis | Weight | Original | V2 Optimizer | V3 Perfumer Fix | Δ (V3−Orig) |
|---|---|---|---|---|---|
| sillage | 0.4 | 92.5 | 92.8 | **96.2** | **+3.7** ★★ |
| skin_performance | 0.3 | 80.5 | 83.4 | 81.5 | +1.0 |
| longevity | 0.4 | 89.9 | 88.7 | 86.2 | −3.7 ★★ |
| hedonic | 1.2 | 81.7 | 83.0 | 81.0 | −0.7 |
| texture | 1.5 | 76.0 | 76.0 | 76.0 | 0.0 |
| luxury | 1.2 | 67.6 | 79.8 | 68.9 | +1.3 |
| synergy | 0.8 | 95.0 | 95.0 | 95.0 | 0.0 |
| **stacking_depth** | **1.5** | 75.0 | 80.0 | **80.0** | **+5.0** ★★ |
| perceptual_clarity | 0.5 | 83.4 | 83.2 | 79.3 | −4.1 ★★ |
| **geometric_total** | — | **81.4** | **84.1** | **81.9** | **+0.5** |

### Character Radar Comparison

| Dimension | Original | V2 Optimizer | V3 Perfumer Fix | Δ (V3−Orig) | Assessment |
|---|---|---|---|---|---|
| transparency | 5.15 | 5.08 | **4.48** | −0.67 | Less transparent = DARKER = correct for leather-smoke |
| **woody** | 2.90 | 3.00 | **3.04** | **+0.14** | ✓ TARGET MET |
| radiance | 2.93 | 3.14 | 2.56 | −0.37 | Controlled radiance — Hedione pulled back appropriately |
| warmth | 2.23 | 2.21 | 2.21 | −0.02 | Stable |
| **creamy** | 1.28 | 1.78 | **1.36** | **+0.08** | ✓ TARGET MET (proportional, not gourmand) |
| sweetness | 1.10 | 1.15 | 1.27 | +0.17 | Slight sweet lift from Gamma Deca + Vanillin |
| freshness | 1.36 | 1.39 | 1.33 | −0.03 | Stable |
| floral | 1.43 | 1.51 | 1.24 | −0.19 | Less floral = correct (Hedione reduction) |
| powdery | 1.12 | 1.07 | 0.94 | −0.18 | Less powdery — Orivone iris removed |
| green | 0.66 | 0.49 | 0.78 | +0.12 | Slight green boost from Clearwood/Patchouli proportion |
| **spicy** | 0.49 | 0.37 ↓ | **0.59** | **+0.10** | ✓ IDENTITY RESTORED (V2 suppressed this!) |
| **animalic** | 0.37 | 0.29 ↓ | **0.47** | **+0.10** | ✓ IDENTITY RESTORED (V2 suppressed this!) |
| **smoky** | 0.30 | 0.23 ↓ | **0.38** | **+0.08** | ✓ IDENTITY RESTORED (V2 suppressed this!) |

### Style Fingerprint

| | Original | V2 Optimizer | V3 Perfumer Fix |
|---|---|---|---|
| Dominant | oriental | oriental | **oriental** ✓ |
| Categories | amber, woody | amber, woody | **woody, amber** |
| Styles | oriental, skin_scent, classical | oriental, iris_powdery, skin_scent | **oriental, skin_scent, classical** ✓ |

V3 restores the original style profile exactly: classical oriental. V2 had drifted into iris_powdery due to Orivone and material inflation.

---

## Key Perfumer Observations

### Why V3 Scores Lower Geometric Than V2 But Is the Better Fragrance

V2's geometric 84.1 was inflated by:
- **Luxury 79.8** (driven by stacking 6 gourmand materials — luxury-as-quantity, not quality)
- **Skin Performance 83.4** (driven by 336 µL sandalwood + 1,082 µL musk — skin saturation, not finesse)
- **Hedonic 83.0** (more sweet materials = more "pleasant" to the algorithm)

But V2 **lost the fragrance's identity**: smoky ↓, spicy ↓, animalic ↓ — the three dimensions that DEFINE leather-smoke. The algorithm doesn't penalize identity loss because it has no concept of "this was supposed to be a leather fragrance."

V3 scores 81.9 — effectively the same quality — while:
- Using 57% less concentrate (2,113 vs 4,953 µL)
- Hitting EDP concentration (21.1% vs 49.5% extrait)
- **Strengthening** the leather-smoke identity
- Removing 3 unavailable materials
- Eliminating gourmand drift

### Creamy Without Gourmand

The V3 creamy architecture achieves "creamy, smooth, tender" through materials that work WITH leather-smoke:

| Material | Role in Creamy Architecture |
|---|---|
| **Ebanol** (60 neat) | THE creamy note — silk sandalwood that reads as worn leather softness, not sweetness |
| **Cashmeran** (80 @ 20%) | Textile warmth — "wrapped in cashmere" quality that echoes leather's tactile register |
| **Ethylene Brassylate** (100 neat) | Lactonic depth — buttery-creamy musk that smooths the leather's edges |
| **Gamma Decalactone** (20 neat) | Peach-skin trace — subliminal fruit-skin that reads as "skin" in a leather context |
| **Benzoin Resinoid** (25 @ 50%) | Balsamic smoothness — rounds the Evernyl/Vetiver transition |
| **Coumarin** (30 @ 20%) | Hay-tonka warmth — bridges sweet and smoky registers |

This is 6 specific materials contributing different FACETS of creaminess, not 6 interchangeable lactones building a gourmand wall.

### Concentration Advantage

At 21.1%, this is a proper EDP that can be sprayed liberally (4–6 sprays) for a leather-smoke aura that develops over 8+ hours. The V2 at 49.5% would have been overwhelming — 2 sprays maximum, and the sticky-sweet lactone/musk base would have been cloying by hour 3.

---

## Mixing Order (30 mL Batch)

1. **Measure ethanol** (23.66 mL) into a clean glass bottle
2. **Add base materials** (materials 12–36) in the order listed above
3. **Add heart materials** (materials 5–11)
4. **Add top materials** (materials 1–4) last
5. **Cap tightly** and roll gently to mix — do NOT shake
6. **Macerate minimum 2 weeks**, ideally 4 weeks (the leather-smoke accord needs time for Evernyl + Guaiacol + IBQ to integrate with the musk-salicylate bed)
7. **Strain through filter paper** if any cloudiness from Benzoin Resinoid

### Special Handling Notes

- **Guaiacol** (24 µL @ 30 mL batch): This is NEAT guaiacol — measure carefully with a microsyringe or pipette in 1 µL increments. Overdose by 10 µL and the phenolic character becomes medicinal.
- **Norlimbanol Dextro** (15 µL): Extremely potent (ODT 0.05 ppm). Measure precisely.
- **IBQ** (30 µL @ 10%): The animalic "danger" note. Barely perceptible at 3 µL active, but it adds subliminal rawness that prevents the leather from being merely "cosmetic."
- **Benzoin Resinoid** (75 µL @ 50% in DPG): Thick material — warm the bottle slightly if it won't flow, and ensure it fully dissolves into the ethanol before adding lighter materials.
