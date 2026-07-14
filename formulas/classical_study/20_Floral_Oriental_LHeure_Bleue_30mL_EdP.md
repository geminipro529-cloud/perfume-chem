# Floral Oriental / Floral Amber — L'Heure Bleue Study — 30 mL EdP

**Historical reference:** Guerlain L'Heure Bleue  
**Family archetype:** `oriental_floral.lheure_bleue_reference`  
**Concentration:** 20.0% EdP · 6,000 µL concentrate in 30 mL  
**Historical gap:** True heliotropin, orris butter, vintage carnation facets, and animalic traces are incomplete in live stock. The powder-floral amber lesson is rebuilt with `Heliotropal`, ionones, `Alpha Irone`, jasmine, ylang, salicylates, benzoin, and vanilla materials.  
**Why this structure matters:** Floral oriental is the classical powder-luxury lesson: flower and amber fused into one violet-heliotrope dusk rather than stacked in separate layers.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 80 | faint opening relief (capped) |
| 2 | Aldehyde C10 | 1% in DPG | 20 | cold classical sparkle |
| 3 | Vanillin | 20% in DPG | 440 | signature powder-heliotrope core |
| 4 | Anisaldehyde | neat | 200 | almond-anise powder richness (increased) |
| 5 | Coumarin | 20% in DPG | 280 | tonka powder warmth |
| 6 | Vanillin | 10% in DPG | 340 | vanilla softness |
| 7 | Alpha Ionone | neat | 520 | iris-violet body |
| 8 | Alpha Ionone | neat | 220 | floral violet blur (increased) |
| 9 | Beta Ionone | 10% in DPG | 15 | cooler violet shadow |
| 10 | Alpha Irone | 30% in DEP | 350 | orris-like depth (increased) |
| 11 | Irotyl | neat | 200 | dry iris texture (increased) |
| 12 | Benzyl Acetate | neat | 100 | floral heart |
| 13 | Methyl Benzoate | neat | 80 | jasmine-violet lift |
| 14 | Hedione HC | neat | 60 | luminous floral bloom |
| 15 | Indole | 10% in DPG | 20 | classical floral depth |
| 16 | Cis Jasmone | neat | 20 | warm jasmine nuance |
| 17 | Jessemal | neat | 30 | creamy floral body |
| 18 | Hedione | neat | 300 | luminous expansion |
| 19 | Ylang Ylang EO | neat | 150 | rich floral warmth |
| 20 | Phenethyl Alcohol | neat | 260 | rosy cushion |
| 21 | Benzyl Salicylate | neat | 500 | waxy powder bridge |
| 22 | Siam Benzoin | 50% in DPG | 240 | amber warmth |
| 23 | Benzoin Sumatra Resinoid | 10% | 140 | balsamic sweetness |
| 24 | Olibanum Resinoid Absolute | 10% | 90 | faint incense shadow |
| 25 | Labdanum | 10% in DPG | 200 | warm resin shadow (increased) |
| 26 | Musk Ketone | 10% in DPG | 600 | soft cosmetic musk |
| 27 | Ethylene Brassylate | neat | 410 | lasting powder body (fill) |
| 28 | Ambrettolide | 10% in DPG | 30 | air in the drydown |
| 29 | Cedarwood EO | neat | 100 | discreet frame |
| 30 | Linalool | neat | 5 | stabilizer |

**Total concentrate:** 6000 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Floral Oriental / Floral Amber — L'Heure Bleue Study — 30 mL EdP

## Gate Summary

**78 PASS** / **22 WARN** / **3 FAIL**

  FAIL chemistry_stability: predicted maturation shelf life 7 days
  FAIL safety_ifra_allergen: IFRA violations: Alpha Ionone 2.4667% > 1.85%; IFRA headroom 100% violations: Alpha Ionone 2.466667% > 1.85%; ℹ 4 EU fragrance allergen(s) r
  FAIL family_drift_detector: oriental_floral.lheure_bleue_reference; not_green: 4.333% active above 1.200
  WARN pipeline_preflight: 9 checks; 4 warnings
  WARN odt_coverage: 13 material(s) rely on derived/unverified ODTs (26% OAV share)
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 26.9% active mass across 6 materials
  WARN small_diluted_traces: Beta Ionone=15.0uL at 10.0%
  WARN eu_allergen_declaration: EU allergens requiring label: coumarin, benzyl salicylate, linalool
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid off-target: Expected T:20% H:50% B:30%, Actual T:0.1% H:60.0% B:39.8%; top OAV off-target for family floral; heart OAV off-target fo
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:aldehyde c10 = 124:1; bergamot fcf sicilian:vanillin = 349:1; bergamot fcf sicili
  WARN jnd_redundancy: Potentially redundant pairs: hedione vs hedione in floral (OAV 1463/1463); musk ketone vs ambrettolide in musk (OAV 0/0)
  WARN guerlain_rose_jasmine_balance: Rose:jasmine OAV ratio = 53.4:1 — Guerlain recommends <3:1
  WARN jellinek_psychology: Jellinek categories weak: erogenic, stimulating, anti_erogenic
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: coumarin OAV 193.3 is above amber_oriental target 10.0-25.0; indole OAV 93.3 is above amber_oriental target 0.5-3.0; ethylene brassylate OAV
  WARN olfactory_fatigue: Olfactory fatigue risk: alpha ionone=7364 (limit 2000); hedione=6.0% of concentrate (<10% minimum for radiance)
  WARN evaporation_rate_balance: Pyramid imbalance: top = 0%
  WARN oriental_skeleton: Oriental skeleton missing: labdanum, benzoin
  WARN master_perfumer_gate: opening likely underbuilt
  WARN mass_market_tier_check: Expensive captives found: Alpha Irone. At 1500 THB, these eat margin. Consider if their perceptible impact justifies the cost.; Estimated ma
  WARN robustness_perturbation: 55 fragile perturbation(s) across 55 checks; Bergamot FCF oil Sicilian up: safety failure under perturbation; IFRA headroom failure: Alpha I
  WARN confidence_minimum: combined confidence 47.5; preflight science penalty 29.4


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Alpha Ionone                 |     7363.6 | heart |  very strong |   1.500 |    2.9454 |  0.000400 |  0.7400 | 19.78 | Alpha Ionone                  
|   2 | Bergamot FCF oil Sicilian    |     1838.8 | heart |  very strong |  40.000 |   11.0330 |  0.006000 |  0.0800 |  2.78 | Bergamot FCF oil Sicilian     
|   3 | Hedione HC                   |     1463.4 | heart |  very strong |   0.089 |    0.0732 |  0.000050 |  0.0600 |  8.18 | Hedione                       
|   4 | Hedione                      |     1463.4 | heart |  very strong |   0.089 |    0.0732 |  0.000050 |  0.3000 |  8.18 | Hedione                       
|   5 | Beta Ionone                  |      682.3 | heart |       strong |   1.200 |    0.0048 |  0.000007 |  0.0015 |  0.04 | Beta Ionone                   
|   6 | Linalool                     |      262.6 | top   |       strong |  21.300 |    0.3939 |  0.001500 |  0.0050 |  0.17 | Linalool                      
|   7 | Methyl Benzoate              |      239.9 | heart |       strong |  40.000 |   11.9933 |  0.050000 |  0.0800 |  3.02 | Methyl Benzoate               
|   8 | Coumarin                     |      193.3 | base  |       strong |   0.500 |    0.1353 |  0.000700 |  0.0560 |  1.97 | Coumarin                      
|   9 | Cis Jasmone                  |      156.5 | heart |       strong |   1.333 |    0.0783 |  0.000500 |  0.0189 |  0.59 | Cis Jasmone                   
|  10 | Indole                       |       93.3 | heart | moderate-strong |   1.500 |    0.0131 |  0.000140 |  0.0020 |  0.09 | Indole                        
|  11 | Alpha Irone                  |       86.6 | base  | moderate-strong |   0.300 |    0.0779 |  0.000900 |  0.1050 |  2.62 | Alpha Irone                   
|  12 | Phenethyl Alcohol            |       64.0 | heart | moderate-strong |  11.570 |   12.8033 |  0.200000 |  0.2649 | 11.15 | Phenethyl Alcohol             
|  13 | Ylang Ylang EO               |       19.1 | heart |     moderate |   0.050 |    0.0191 |  0.001000 |  0.1500 |  3.85 | Ylang Ylang EO                
|  14 | Aldehyde C10                 |       14.8 | top   |     moderate |  10.000 |    0.0065 |  0.000440 |  0.0002 |  0.01 | Aldehyde C10                  
|  15 | Anisaldehyde                 |        7.5 | heart |  perceptible |   0.050 |    0.0375 |  0.005000 |  0.2000 |  7.55 | Anisaldehyde                  
|  16 | Jessemal                     |        7.1 | heart |  perceptible |   0.500 |    0.0357 |  0.005000 |  0.0300 |  0.72 | Jessemal                      
|  17 | Ethylene Brassylate          |        6.4 | base  |  perceptible |   0.008 |    0.0062 |  0.000970 |  0.4100 |  7.79 | Ethylene Brassylate           
|  18 | Vanillin                     |        5.3 | base  |  perceptible |   0.200 |    0.1054 |  0.020000 |  0.0780 |  2.63 | Vanillin                      
|  19 | Cedarwood EO                 |        4.2 | base  | at threshold |   0.250 |    0.0624 |  0.015000 |  0.1000 |  2.51 | Cedarwood EO                  
|  20 | Benzyl Salicylate            |        3.7 | base  | at threshold |   0.030 |    0.0374 |  0.010000 |  0.5000 | 11.26 | Benzyl Salicylate             
|  21 | Benzyl Acetate               |        3.7 | heart | at threshold |   0.220 |    0.0747 |  0.020000 |  0.1000 |  3.42 | Benzyl Acetate                
|  22 | Irotyl                       |        2.5 | heart | at threshold |   0.005 |    0.0025 |  0.001000 |  0.2000 |  4.98 | Irotyl                        
|  23 | Olibanum Resinoid Absolute   |        0.2 | base  | sub-threshold |   0.080 |    0.0017 |  0.010000 |  0.0090 |  0.21 | Olibanum Resinoid             
|  24 | Musk Ketone                  |        0.2 | base  | sub-threshold |   0.003 |    0.0003 |  0.002000 |  0.0600 |  1.05 | Musk Ketone                   
|  25 | Ambrettolide                 |        0.1 | base  | sub-threshold |   0.003 |    0.0000 |  0.000136 |  0.0030 |  0.06 | Ambrettolide                  
|  26 | Benzoin Sumatra Resinoid     |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.003000 |  0.0140 |  0.34 | Benzoin Sumatra Resinoid      
|  27 | Siam Benzoin                 |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.040000 |  0.1200 |  2.91 | Siam Benzoin                  
|  28 | Labdanum                     |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.005000 |  0.0200 |  0.34 | Labdanum                      

**Materials:** 28 total (2 top, 14 heart, 12 base)
**Total vapor:** 40.01 ppm

### Note Distribution

**TOP:** 2 mats, 0.1% active, 2.0% OAV
  - Linalool                     OAV=   262.6 (strong) VP=21.300Pa
  - Aldehyde C10                 OAV=    14.8 (moderate) VP=10.000Pa
**HEART:** 14 mats, 60.0% active, 95.9% OAV
  - Alpha Ionone                 OAV=  7363.6 (very strong) VP=1.500Pa
  - Bergamot FCF oil Sicilian    OAV=  1838.8 (very strong) VP=40.000Pa
  - Hedione HC                   OAV=  1463.4 (very strong) VP=0.089Pa
  - Hedione                      OAV=  1463.4 (very strong) VP=0.089Pa
  - Beta Ionone                  OAV=   682.3 (strong) VP=1.200Pa
  - Methyl Benzoate              OAV=   239.9 (strong) VP=40.000Pa
  ... and 8 more
**BASE:** 12 mats, 39.8% active, 2.1% OAV
  - Coumarin                     OAV=   193.3 (strong) VP=0.500Pa
  - Alpha Irone                  OAV=    86.6 (moderate-strong) VP=0.300Pa
  - Ethylene Brassylate          OAV=     6.4 (perceptible) VP=0.008Pa
  - Vanillin                     OAV=     5.3 (perceptible) VP=0.200Pa
  - Cedarwood EO                 OAV=     4.2 (at threshold) VP=0.250Pa
  - Benzyl Salicylate            OAV=     3.7 (at threshold) VP=0.030Pa
  ... and 6 more

### Sub-threshold Materials (OAV < 1)
6/28 materials below perceptible threshold
  - Siam Benzoin: OAV=0.00 VP=0.000Pa act=120uL role=Siam Benzoin [Structural (acceptable)]
  - Benzoin Sumatra Resinoid: OAV=0.00 VP=0.000Pa act=14uL role=Benzoin Sumatra Resi [Structural (acceptable)]
  - Olibanum Resinoid Absolute: OAV=0.17 VP=0.080Pa act=9uL role=Olibanum Resinoid [Structural (acceptable)]
  - Labdanum: OAV=0.00 VP=0.000Pa act=20uL role=Labdanum [Structural (acceptable)]
  - Musk Ketone: OAV=0.16 VP=0.003Pa act=60uL role=Musk Ketone [**Needs higher dose**]
  - Ambrettolide: OAV=0.13 VP=0.003Pa act=3uL role=Ambrettolide [Structural (acceptable)]
### High-OAV Flags (>5000)
  - Alpha Ionone OAV=7364 dominates headspace — may mask subtler notes

### OAV by Odor Family

           floral  76.6% ======================================  (8 mats)
           citrus  13.2% ======  (1 mats)
            woody   4.9% ==  (2 mats)
         aromatic   1.9% =  (1 mats)
         gourmand   1.5% =  (5 mats)
          indolic   0.7% =  (1 mats)
             iris   0.6% =  (2 mats)
             rose   0.5% =  (1 mats)
        aldehydic   0.1% =  (1 mats)
             musk   0.0% =  (3 mats)
       salicylate   0.0% =  (1 mats)
            smoky   0.0% =  (1 mats)
            amber   0.0% =  (1 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  0.1/60.0/39.8 |  40.01ppm |   6000 | Alpha Ionone(7364), Bergamot FCF(1839), Hedione HC(1463)
| top          |    300s |  0.1/60.0/39.9 |  39.55ppm |   5994 | Alpha Ionone(7374), Bergamot FCF(1806), Hedione HC(1466)
| heart        |   1800s |  0.1/59.7/40.2 |  37.30ppm |   5966 | Alpha Ionone(7423), Bergamot FCF(1652), Hedione HC(1481)
| late_heart   |   7200s |  0.1/58.8/41.0 |  30.48ppm |   5877 | Alpha Ionone(7570), Hedione HC(1527), Hedione(1527)
| drydown      |  14400s |  0.1/57.9/42.0 |  23.82ppm |   5785 | Alpha Ionone(7705), Hedione HC(1577), Hedione(1577)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:0.1% H:60.0% B:39.8%  Vapor:40.01ppm
  Leaders: Alpha Ionone OAV 7364 | Bergamot FCF oil Sicilian OAV 1839 | Hedione HC OAV 1463 | Hedione OAV 1463 | Beta Ionone OAV 682

**TOP** (300.0s) — Evap:0%
  T:0.1% H:60.0% B:39.9%  Vapor:39.55ppm
  Leaders: Alpha Ionone OAV 7374 | Bergamot FCF oil Sicilian OAV 1806 | Hedione HC OAV 1466 | Hedione OAV 1466 | Beta Ionone OAV 683

**HEART** (1800.0s) — Evap:1%
  T:0.1% H:59.7% B:40.2%  Vapor:37.30ppm
  Leaders: Alpha Ionone OAV 7423 | Bergamot FCF oil Sicilian OAV 1652 | Hedione HC OAV 1481 | Hedione OAV 1481 | Beta Ionone OAV 688

**LATE_HEART** (7200.0s) — Evap:2%
  T:0.1% H:58.8% B:41.0%  Vapor:30.48ppm
  Leaders: Alpha Ionone OAV 7570 | Hedione HC OAV 1527 | Hedione OAV 1527 | Bergamot FCF oil Sicilian OAV 1193 | Beta Ionone OAV 704

**DRYDOWN** (14400.0s) — Evap:4%
  T:0.1% H:57.9% B:42.0%  Vapor:23.82ppm
  Leaders: Alpha Ionone OAV 7705 | Hedione HC OAV 1577 | Hedione OAV 1577 | Bergamot FCF oil Sicilian OAV 766 | Beta Ionone OAV 718

## Perfumer's Assessment

### 1. Character
  Top: Linalool(strong) + Aldehyde C10(moderate)
  Heart: Alpha Ionone(very strong) + Bergamot FCF oil Sicilian(very strong)
  Base: Coumarin(strong) + Alpha Irone(moderate-strong) + Ethylene Brassylate(perceptible) + Vanillin(perceptible) + Cedarwood EO(at threshold)

### 2. Opening (0-5min)
  Linalool dominates at OAV 263 (strong).
  - Linalool OAV=263 VP=21.3Pa (aromatic)
  - Aldehyde C10 OAV=15 VP=10.0Pa (aldehydic)
  Total vapor: 40.0 ppm

### 3. Heart (30min-2hr)
  Alpha Ionone OAV=7423 (very strong)
  Bergamot FCF oil Sicilian OAV=1652 (very strong)
  Hedione HC OAV=1481 (very strong)
  Hedione OAV=1481 (very strong)
  T:0.1% H:59.7% B:40.2%
  Vapor: 37.3 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 42% of headspace
  - Alpha Ionone OAV=7705
  - Hedione HC OAV=1577
  - Hedione OAV=1577
  - Bergamot FCF oil Sicilian OAV=766
  - Beta Ionone OAV=718
  - Coumarin OAV=205
  Vapor: 23.8 ppm

### 5. Sillage & Diffusion
  Primary carriers: Alpha Ionone(7364) + Bergamot FCF oil Sicilian(1839) + Hedione HC(1463) + Hedione(1463)
  OAV by family: floral77% citrus13% woody5% aromatic2%

### 6. Longevity
  Evaporation: 4% over 4h
  Vapor: 40.0 > 23.8 ppm
  Base @ drydown: 42%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:0.1% H:60.0% B:39.8%
  OAV range: 0.00 to 7364 (sigma-log=1.98)
  Wide contrast: citrus (OAV 7364) dominates opening before burning off to reveal base.
    sub-threshold: 6

### 8. Flags
  SUB: Olibanum Resinoid Absolute OAV=0.17 role=Olibanum Resinoid
  SUB: Musk Ketone OAV=0.16 role=Musk Ketone
  SUB: Ambrettolide OAV=0.13 role=Ambrettolide
  SUB: Benzoin Sumatra Resinoid OAV=0.00 role=Benzoin Sumatra Resinoid
  SUB: Siam Benzoin OAV=0.00 role=Siam Benzoin
  SUB: Labdanum OAV=0.00 role=Labdanum


## Structural OAV Analysis

**Vapor:** 40 ppm  |  **Active:** 12.3%  |  **Perceptible:** 22/28

### OAV Tiers
  **massive** (4): Bergamot FCF oil Sicilian(1839), Alpha Ionone(7364), Hedione HC(1463), Hedione(1463)
  **v.strong** (5): Coumarin(193), Beta Ionone(682), Methyl Benzoate(240), Cis Jasmone(157), Linalool(263)
  **strong** (3): Alpha Irone(87), Indole(93), Phenethyl Alcohol(64)
  **moderate** (2): Aldehyde C10(15), Ylang Ylang EO(19)
  **perceptible** (4): Vanillin(5), Anisaldehyde(7), Jessemal(7), Ethylene Brassylate(6)
  **threshold** (4): Irotyl(2), Benzyl Acetate(4), Benzyl Salicylate(4), Cedarwood EO(4)
  **sub** (6): Siam Benzoin(0), Benzoin Sumatra Resinoid(0), Olibanum Resinoid Absolute(0), Labdanum(0), Musk Ketone(0), Ambrettolide(0)

### Block Balance
  **Citrus**     1839 (13%)
  **Floral**    12137 (87%)
  **Base**          7 (0%)
  **Ratio:** 1863:1 between strongest/weakest block

### Issues
  ! 6 sub-threshold material(s): Siam Benzoin, Benzoin Sumatra Resinoid, Olibanum Resinoid Absolute, Labdanum, Musk Ketone, Ambrettolide
```
