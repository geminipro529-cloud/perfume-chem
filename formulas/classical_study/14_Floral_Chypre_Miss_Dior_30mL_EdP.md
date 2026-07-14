# Floral Chypre — Miss Dior Study — 30 mL EdP

**Historical reference:** Miss Dior original  
**Family archetype:** `chypre_floral.miss_dior_reference`  
**Concentration:** 20.0% EdP · 6,000 µL concentrate in 30 mL  
**Historical gap:** True oakmoss, labdanum, and some vintage animalic supports are absent. This version preserves the lesson with a rose-jasmine-muguet heart laid over `Evernyl`, patchouli, vetiver, and a benzoin-incense shadow instead of true labdanum.  
**Why this structure matters:** Floral chypre teaches how a mossy framework can remain strict and elegant while carrying a full feminine floral heart.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 40 | bright opening (balanced) |
| 2 | Aldehyde C10 | 1% in DPG | 20 | classical sparkle |
| 3 | Galbanum Resinoid | 10% in DPG | 120 | green chypre edge |
| 4 | Phenethyl Alcohol | neat | 500 | floral body |
| 5 | Geraniol | neat | 15 | rose whisper |
| 6 | Citronellol | neat | 200 | rosy softness |
| 7 | Rose Oxide | 10% in DPG | 40 | airy rose lift |
| 8 | Hedione | neat | 500 | radiance |
| 9 | Benzyl Acetate | neat | 200 | floral freshness (increased) |
| 10 | Methyl Benzoate | neat | 50 | jasmine brightness |
| 11 | Hydroxycitronellal | neat | 180 | muguet support |
| 12 | Linalool | neat | 80 | transparent florality |
| 13 | Hedione HC | neat | 40 | jasmine bloom |
| 14 | Indole | 10% in DPG | 20 | hidden floral depth |
| 15 | Ylang Ylang EO | neat | 70 | richer heart shading |
| 16 | Benzyl Salicylate | neat | 300 | waxy heart-to-base bridge |
| 17 | Patchouli EO | neat | 580 | dark chypre body |
| 18 | Vetiver EO | neat | 335 | dry root support |
| 19 | Evernyl | neat | 25 | moss memory |
| 20 | Cedarwood EO | neat | 200 | structure |
| 21 | Siam Benzoin | 50% in DPG | 190 | balsamic warmth |
| 22 | Olibanum Resinoid Absolute | 10% | 90 | incense shadow |
| 23 | Labdanum | 10% in DPG | 200 | warm amber-resin anchor |
| 24 | Cedarwood EO | neat | 250 | dry diffusion |
| 25 | Musk Ketone | 10% in DPG | 1050 | clean soft trail |
| 26 | Geranium EO | neat | 80 | natural geranium-rose (replaces synthetic geraniol) |
| 27 | Ethylene Brassylate | neat | 490 | persistence (fill) |
| 28 | Ambrettolide | 10% in DPG | 30 | lift |
| 29 | Coumarin | 20% in DPG | 100 | classical softness |
| 30 | Linalool | neat | 5 | stabilizer |

**Total concentrate:** 6000 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Floral Chypre — Miss Dior Study — 30 mL EdP

## Gate Summary

**82 PASS** / **19 WARN** / **2 FAIL**

  FAIL chemistry_stability: predicted maturation shelf life 7 days
  FAIL family_drift_detector: chypre_floral.miss_dior_reference; bergamot_flash: 0.667% active below 2.500
  WARN pipeline_preflight: 9 checks; 4 warnings
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 34.5% active mass across 6 materials
  WARN chypre_skeleton: Chypre skeleton missing: labdanum
  WARN safety_ifra_allergen: 8 materials lack explicit IFRA Cat4 limits; 1 materials near IFRA/headroom edge; 6 EU allergen declarations
  WARN eu_allergen_declaration: EU allergens requiring label: geraniol, citronellol, hydroxycitronellal, linalool, benzyl salicylate +1 more
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid off-target: Expected T:20% H:50% B:30%, Actual T:2.2% H:42.7% B:55.1%; top OAV needs improvement for family floral; heart OAV off-ta
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:aldehyde c10 = 62:1; bergamot fcf sicilian:galbanum resinoid = 90:1; bergamot fcf
  WARN jnd_redundancy: Potentially redundant pairs: phenethyl alcohol vs rose oxide in rose (OAV 103/118); hedione vs hedione in floral (OAV 1833/1833)
  WARN jellinek_psychology: Jellinek categories weak: erogenic, anti_erogenic
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: linalool OAV 3738.8 is above floral_jasmine target 10.0-25.0; hedione OAV 1833.0 is above floral_jasmine target 40.0-80.0; methyl benzoate O
  WARN olfactory_fatigue: Olfactory fatigue risk: hedione=9.0% of concentrate (<10% minimum for radiance)
  WARN evaporation_rate_balance: Pyramid imbalance: top = 2%
  WARN tenacity_projection: VP<0.001Pa = 3% (<3%, may lack depth)
  WARN master_perfumer_gate: opening likely underbuilt
  WARN confidence_minimum: combined confidence 47.2; preflight science penalty 29.4


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Geraniol                     |     4158.1 | heart |  very strong |   4.000 |    0.1663 |  0.000040 |  0.0150 |  0.42 | Geraniol                      
|   2 | Linalool                     |     3738.8 | top   |  very strong |  21.300 |    5.6082 |  0.001500 |  0.0850 |  2.39 | Linalool                      
|   3 | Hedione                      |     1833.0 | heart |  very strong |   0.089 |    0.0916 |  0.000050 |  0.5000 | 10.33 | Hedione                       
|   4 | Hedione HC                   |     1833.0 | heart |  very strong |   0.089 |    0.0916 |  0.000050 |  0.0400 | 10.33 | Hedione                       
|   5 | Bergamot FCF oil Sicilian    |      770.7 | heart |       strong |  40.000 |    4.6241 |  0.006000 |  0.0400 |  1.17 | Bergamot FCF oil Sicilian     
|   6 | Geranium EO                  |      363.2 | heart |       strong |   2.500 |    0.5449 |  0.001500 |  0.0800 |  2.21 | Geranium EO                   
|   7 | Methyl Benzoate              |      125.7 | heart |       strong |  40.000 |    6.2832 |  0.050000 |  0.0500 |  1.59 | Methyl Benzoate               
|   8 | Rose Oxide                   |      117.5 | heart |       strong |   5.300 |    0.0588 |  0.000500 |  0.0040 |  0.11 | Rose Oxide                    
|   9 | Phenethyl Alcohol            |      103.2 | heart |       strong |  11.570 |   20.6385 |  0.200000 |  0.5095 | 18.06 | Phenethyl Alcohol             
|  10 | Indole                       |       78.2 | heart | moderate-strong |   1.500 |    0.0109 |  0.000140 |  0.0020 |  0.07 | Indole                        
|  11 | Coumarin                     |       62.0 | base  | moderate-strong |   0.500 |    0.0434 |  0.000700 |  0.0200 |  0.59 | Coumarin                      
|  12 | Citronellol                  |       61.6 | heart | moderate-strong |   4.500 |    2.4629 |  0.040000 |  0.2000 |  5.54 | Citronellol                   
|  13 | Hydroxycitronellal           |       59.6 | heart | moderate-strong |   2.000 |    0.8937 |  0.015000 |  0.1800 |  4.52 | Hydroxycitronellal            
|  14 | Patchouli EO                 |       22.5 | base  |     moderate |   0.060 |    0.0675 |  0.003000 |  0.5800 | 11.29 | Patchouli EO                  
|  15 | Evernyl                      |       18.2 | base  |     moderate |   0.100 |    0.0055 |  0.000300 |  0.0250 |  0.55 | Evernyl                       
|  16 | Cedarwood EO                 |       15.7 | base  |     moderate |   0.250 |    0.2354 |  0.015000 |  0.4500 |  9.53 | Cedarwood EO                  
|  17 | Aldehyde C10                 |       12.4 | top   |     moderate |  10.000 |    0.0055 |  0.000440 |  0.0002 |  0.01 | Aldehyde C10                  
|  18 | Galbanum Resinoid            |        8.6 | top   |  perceptible |   0.100 |    0.0026 |  0.000300 |  0.0120 |  0.26 | Galbanum Resinoid             
|  19 | Ylang Ylang EO               |        7.5 | heart |  perceptible |   0.050 |    0.0075 |  0.001000 |  0.0700 |  1.52 | Ylang Ylang EO                
|  20 | Vetiver EO                   |        6.4 | base  |  perceptible |   0.050 |    0.0322 |  0.005000 |  0.3350 |  6.52 | Vetiver EO                    
|  21 | Ethylene Brassylate          |        6.4 | base  |  perceptible |   0.008 |    0.0062 |  0.000970 |  0.4900 |  7.85 | Ethylene Brassylate           
|  22 | Benzyl Acetate               |        6.3 | heart |  perceptible |   0.220 |    0.1253 |  0.020000 |  0.2000 |  5.77 | Benzyl Acetate                
|  23 | Benzyl Salicylate            |        2.0 | base  | at threshold |   0.030 |    0.0196 |  0.010000 |  0.3000 |  5.69 | Benzyl Salicylate             
|  24 | Musk Ketone                  |        0.2 | base  | sub-threshold |   0.003 |    0.0005 |  0.002000 |  0.1050 |  1.55 | Musk Ketone                   
|  25 | Olibanum Resinoid Absolute   |        0.1 | base  | sub-threshold |   0.080 |    0.0014 |  0.010000 |  0.0090 |  0.18 | Olibanum Resinoid             
|  26 | Ambrettolide                 |        0.1 | base  | sub-threshold |   0.003 |    0.0000 |  0.000136 |  0.0030 |  0.05 | Ambrettolide                  
|  27 | Siam Benzoin                 |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.040000 |  0.0950 |  1.94 | Siam Benzoin                  
|  28 | Labdanum                     |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.005000 |  0.0200 |  0.29 | Labdanum                      

**Materials:** 28 total (3 top, 13 heart, 12 base)
**Total vapor:** 42.03 ppm

### Note Distribution

**TOP:** 3 mats, 2.2% active, 28.0% OAV
  - Linalool                     OAV=  3738.8 (very strong) VP=21.300Pa
  - Aldehyde C10                 OAV=    12.4 (moderate) VP=10.000Pa
  - Galbanum Resinoid            OAV=     8.6 (perceptible) VP=0.100Pa
**HEART:** 13 mats, 42.7% active, 71.0% OAV
  - Geraniol                     OAV=  4158.1 (very strong) VP=4.000Pa
  - Hedione                      OAV=  1833.0 (very strong) VP=0.089Pa
  - Hedione HC                   OAV=  1833.0 (very strong) VP=0.089Pa
  - Bergamot FCF oil Sicilian    OAV=   770.7 (strong) VP=40.000Pa
  - Geranium EO                  OAV=   363.2 (strong) VP=2.500Pa
  - Methyl Benzoate              OAV=   125.7 (strong) VP=40.000Pa
  ... and 7 more
**BASE:** 12 mats, 55.1% active, 1.0% OAV
  - Coumarin                     OAV=    62.0 (moderate-strong) VP=0.500Pa
  - Patchouli EO                 OAV=    22.5 (moderate) VP=0.060Pa
  - Evernyl                      OAV=    18.2 (moderate) VP=0.100Pa
  - Cedarwood EO                 OAV=    15.7 (moderate) VP=0.250Pa
  - Vetiver EO                   OAV=     6.4 (perceptible) VP=0.050Pa
  - Ethylene Brassylate          OAV=     6.4 (perceptible) VP=0.008Pa
  ... and 6 more

### Sub-threshold Materials (OAV < 1)
5/28 materials below perceptible threshold
  - Siam Benzoin: OAV=0.00 VP=0.000Pa act=95uL role=Siam Benzoin [Structural (acceptable)]
  - Olibanum Resinoid Absolute: OAV=0.14 VP=0.080Pa act=9uL role=Olibanum Resinoid [Structural (acceptable)]
  - Labdanum: OAV=0.00 VP=0.000Pa act=20uL role=Labdanum [Structural (acceptable)]
  - Musk Ketone: OAV=0.23 VP=0.003Pa act=105uL role=Musk Ketone [**Needs higher dose**]
  - Ambrettolide: OAV=0.11 VP=0.003Pa act=3uL role=Ambrettolide [Structural (acceptable)]

### OAV by Odor Family

             rose  33.1% ================  (4 mats)
           floral  31.1% ===============  (6 mats)
         aromatic  27.9% =============  (1 mats)
           citrus   5.7% ==  (1 mats)
          indolic   0.6% =  (1 mats)
         gourmand   0.5% =  (2 mats)
           muguet   0.4% =  (1 mats)
            woody   0.3% =  (3 mats)
             moss   0.1% =  (1 mats)
        aldehydic   0.1% =  (1 mats)
            green   0.1% =  (1 mats)
             musk   0.1% =  (3 mats)
       salicylate   0.0% =  (1 mats)
            smoky   0.0% =  (1 mats)
            amber   0.0% =  (1 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  2.2/42.7/55.1 |  42.03ppm |   6000 | Geraniol(4158), Linalool(3739), Hedione(1833)
| top          |    300s |  2.2/42.6/55.2 |  41.70ppm |   5993 | Geraniol(4159), Linalool(3704), Hedione(1837)
| heart        |   1800s |  2.1/42.3/55.6 |  40.11ppm |   5959 | Geraniol(4163), Linalool(3535), Hedione(1856)
| late_heart   |   7200s |  1.8/41.2/57.0 |  35.07ppm |   5849 | Geraniol(4165), Linalool(2977), Hedione(1922)
| drydown      |  14400s |  1.5/40.0/58.5 |  29.68ppm |   5727 | Geraniol(4141), Linalool(2352), Hedione(1999)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:2.2% H:42.7% B:55.1%  Vapor:42.03ppm
  Leaders: Geraniol OAV 4158 | Linalool OAV 3739 | Hedione OAV 1833 | Hedione HC OAV 1833 | Bergamot FCF oil Sicilian OAV 771

**TOP** (300.0s) — Evap:0%
  T:2.2% H:42.6% B:55.2%  Vapor:41.70ppm
  Leaders: Geraniol OAV 4159 | Linalool OAV 3704 | Hedione OAV 1837 | Hedione HC OAV 1837 | Bergamot FCF oil Sicilian OAV 757

**HEART** (1800.0s) — Evap:1%
  T:2.1% H:42.3% B:55.6%  Vapor:40.11ppm
  Leaders: Geraniol OAV 4163 | Linalool OAV 3535 | Hedione OAV 1856 | Hedione HC OAV 1856 | Bergamot FCF oil Sicilian OAV 693

**LATE_HEART** (7200.0s) — Evap:3%
  T:1.8% H:41.2% B:57.0%  Vapor:35.07ppm
  Leaders: Geraniol OAV 4165 | Linalool OAV 2977 | Hedione OAV 1922 | Hedione HC OAV 1922 | Bergamot FCF oil Sicilian OAV 504

**DRYDOWN** (14400.0s) — Evap:5%
  T:1.5% H:40.0% B:58.5%  Vapor:29.68ppm
  Leaders: Geraniol OAV 4141 | Linalool OAV 2352 | Hedione OAV 1999 | Hedione HC OAV 1999 | Geranium EO OAV 375

## Perfumer's Assessment

### 1. Character
  Top: Linalool(very strong) + Aldehyde C10(moderate) + Galbanum Resinoid(perceptible)
  Heart: Geraniol(very strong) + Hedione(very strong)
  Base: Coumarin(moderate-strong) + Patchouli EO(moderate) + Evernyl(moderate) + Cedarwood EO(moderate) + Vetiver EO(perceptible)

### 2. Opening (0-5min)
  Linalool dominates at OAV 3739 (very strong).
  - Linalool OAV=3739 VP=21.3Pa (aromatic)
  - Aldehyde C10 OAV=12 VP=10.0Pa (aldehydic)
  - Galbanum Resinoid OAV=9 VP=0.1Pa (green)
  Total vapor: 42.0 ppm

### 3. Heart (30min-2hr)
  Geraniol OAV=4163 (very strong)
  Linalool OAV=3535 (very strong)
  Hedione OAV=1856 (very strong)
  Hedione HC OAV=1856 (very strong)
  T:2.1% H:42.3% B:55.6%
  Vapor: 40.1 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 58% of headspace
  - Geraniol OAV=4141
  - Linalool OAV=2352
  - Hedione OAV=1999
  - Hedione HC OAV=1999
  - Geranium EO OAV=375
  - Bergamot FCF oil Sicilian OAV=326
  Vapor: 29.7 ppm

### 5. Sillage & Diffusion
  Primary carriers: Geraniol(4158) + Linalool(3739) + Hedione(1833) + Hedione HC(1833)
  OAV by family: rose33% floral31% aromatic28% citrus6%

### 6. Longevity
  Evaporation: 5% over 4h
  Vapor: 42.0 > 29.7 ppm
  Base @ drydown: 58%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:2.2% H:42.7% B:55.1%
  OAV range: 0.00 to 4158 (sigma-log=1.85)
  Wide contrast: citrus (OAV 4158) dominates opening before burning off to reveal base.
    sub-threshold: 5

### 8. Flags
  SUB: Musk Ketone OAV=0.23 role=Musk Ketone
  SUB: Olibanum Resinoid Absolute OAV=0.14 role=Olibanum Resinoid
  SUB: Ambrettolide OAV=0.11 role=Ambrettolide
  SUB: Siam Benzoin OAV=0.00 role=Siam Benzoin
  SUB: Labdanum OAV=0.00 role=Labdanum
  IFRA: Evernyl at 0.57% active — check Cat4 limit (0.1% in product = 0.5% at 20% EdP)


## Structural OAV Analysis

**Vapor:** 42 ppm  |  **Active:** 14.7%  |  **Perceptible:** 23/28

### OAV Tiers
  **massive** (4): Geraniol(4158), Hedione(1833), Linalool(3739), Hedione HC(1833)
  **v.strong** (5): Bergamot FCF oil Sicilian(771), Phenethyl Alcohol(103), Rose Oxide(118), Methyl Benzoate(126), Geranium EO(363)
  **strong** (4): Citronellol(62), Hydroxycitronellal(60), Indole(78), Coumarin(62)
  **moderate** (4): Aldehyde C10(12), Patchouli EO(23), Evernyl(18), Cedarwood EO(16)
  **perceptible** (5): Galbanum Resinoid(9), Benzyl Acetate(6), Ylang Ylang EO(7), Vetiver EO(6), Ethylene Brassylate(6)
  **threshold** (1): Benzyl Salicylate(2)
  **sub** (5): Siam Benzoin(0), Olibanum Resinoid Absolute(0), Labdanum(0), Musk Ketone(0), Ambrettolide(0)

### Block Balance
  **Citrus**      771 (6%)
  **Floral**    12634 (94%)
  **Base**          7 (0%)
  **Ratio:** 1942:1 between strongest/weakest block

### Issues
  ! 5 sub-threshold material(s): Siam Benzoin, Olibanum Resinoid Absolute, Labdanum, Musk Ketone, Ambrettolide
```
