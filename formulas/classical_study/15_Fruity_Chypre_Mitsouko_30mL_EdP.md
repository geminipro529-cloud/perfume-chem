# Fruity Chypre — Mitsouko Study — 30 mL EdP

**Historical reference:** Guerlain Mitsouko  
**Family archetype:** `chypre_fruity.mitsouko_reference`  
**Concentration:** 20.0% EdP · 6,000 µL concentrate in 30 mL  
**Historical gap:** True oakmoss, labdanum, costus, and vintage animalics are not in stock. The peach-lactone accent is rebuilt with restrained `Gamma Decalactone` and rose-ketone support over an `Evernyl`-patchouli-vetiver base.  
**Why this structure matters:** Fruity chypre teaches restraint: fruit must read as a veil over the chypre spine, not as a modern juicy accord.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 30 | bright opening (capped) |
| 2 | Lemon FCF oil Sicilian | neat | 100 | sharpened top |
| 3 | Orange Peel EO | neat | 60 | rounded hesperidic body |
| 4 | Gamma Decalactone | neat | 280 | peach skin accent (increased — THE note) |
| 5 | Damascone Beta | 10% in DPG | 60 | fruity-rosy depth |
| 6 | Phenethyl Alcohol | neat | 400 | floral body |
| 7 | Geraniol | neat | 0 | rosy whisper |
| 8 | Methyl Benzoate | neat | 50 | soft floral veil |
| 9 | Benzyl Acetate | neat | 50 | floral freshness |
| 10 | Hedione HC | neat | 40 | jasmine-like bloom |
| 11 | Indole | 10% in DPG | 20 | hidden floral depth |
| 12 | Ylang Ylang EO | neat | 10 | waxy warmth |
| 13 | Alpha Ionone | neat | 240 | dry violet-iris shadow |
| 14 | Rose Oxide | 10% in DPG | 30 | metallic lift |
| 15 | Hedione | neat | 260 | expansion |
| 16 | Patchouli EO | neat | 800 | dark earthy backbone |
| 17 | Vetiver EO | neat | 450 | bitter dry root |
| 18 | Evernyl | neat | 25 | moss memory |
| 19 | Cedarwood EO | neat | 240 | dry wood frame |
| 20 | Siam Benzoin | 50% in DPG | 260 | warm ambered support |
| 21 | Benzoin Sumatra Resinoid | 10% | 190 | balsamic sweetness |
| 22 | Olibanum Resinoid Absolute | 10% | 80 | incense dryness |
| 23 | Labdanum | 10% in DPG | 200 | amber-resin base |
| 24 | Cedarwood EO | neat | 250 | structure |
| 25 | Musk Ketone | 10% in DPG | 840 | softened trail |
| 26 | Ethylene Brassylate | neat | 930 | persistence (fill) |
| 27 | Ambrettolide | 10% in DPG | 30 | airy lift |
| 28 | Benzyl Salicylate | neat | 70 | waxy floral bridge |
| 29 | Linalool | neat | 5 | stabilizer |

**Total concentrate:** 6000 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Fruity Chypre — Mitsouko Study — 30 mL EdP

## Gate Summary

**81 PASS** / **21 WARN** / **1 FAIL**

  FAIL pipette_floor_neat_traces: Geraniol=0.0uL below 5.0 uL neat floor
  WARN pipeline_preflight: 9 checks; 5 warnings
  WARN odt_coverage: 16 material(s) rely on derived/unverified ODTs (36% OAV share)
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 25.7% active mass across 5 materials
  WARN chypre_skeleton: Chypre skeleton missing: labdanum
  WARN safety_ifra_allergen: 9 materials lack explicit IFRA Cat4 limits; 2 materials near IFRA/headroom edge; 2 EU allergen declarations
  WARN eu_allergen_declaration: EU allergens requiring label: linalool
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid needs improvement: Expected T:20% H:30% B:50%, Actual T:3.6% H:30.0% B:66.4%; top OAV needs improvement for family chypre; heart OAV
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:orange peel eo = 16:1; bergamot fcf sicilian:benzyl acetate = 369:1; bergamot fcf
  WARN jnd_redundancy: Potentially redundant pairs: phenethyl alcohol vs rose oxide in rose (OAV 84/90); hedione vs hedione in floral (OAV 1038/1038)
  WARN guerlain_rose_jasmine_balance: Rose:jasmine OAV ratio = 13.1:1 — Guerlain recommends <3:1
  WARN jellinek_psychology: Jellinek categories weak: erogenic, stimulating, anti_erogenic
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: vetiver eo OAV 8.8 is below chypre target 10.0-25.0; material_class_distribution: Class distribution: animalic:0%, fixatives:2%, florals:16%
  WARN olfactory_fatigue: Olfactory fatigue risk: alpha ionone=2042 (limit 2000); hedione=5.0% of concentrate (<10% minimum for radiance)
  WARN evaporation_rate_balance: Pyramid imbalance: top = 4%, base = 66%
  WARN master_perfumer_gate: opening likely underbuilt
  WARN robustness_perturbation: 1 fragile perturbation(s) across 53 checks; Damascone Beta up: safety failure under perturbation; IFRA headroom failure: Damascone Beta 0.02
  WARN confidence_minimum: combined confidence 46.1; preflight science penalty 32.5


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Alpha Ionone                 |     2041.7 | heart |  very strong |   1.500 |    0.8167 |  0.000400 |  0.2400 |  5.52 | Alpha Ionone                  
|   2 | Hedione HC                   |     1037.6 | heart |  very strong |   0.089 |    0.0519 |  0.000050 |  0.0400 |  5.86 | Hedione                       
|   3 | Hedione                      |     1037.6 | heart |  very strong |   0.089 |    0.0519 |  0.000050 |  0.2600 |  5.86 | Hedione                       
|   4 | Bergamot FCF oil Sicilian    |      589.5 | heart |       strong |  40.000 |    3.5371 |  0.006000 |  0.0300 |  0.90 | Bergamot FCF oil Sicilian     
|   5 | Damascone Beta               |      510.4 | heart |       strong |   1.500 |    0.0204 |  0.000040 |  0.0060 |  0.14 | Damascone Beta                
|   6 | Gamma Decalactone            |      382.5 | heart |       strong |   0.800 |    0.5738 |  0.001500 |  0.2800 |  7.27 | Gamma Decalactone             
|   7 | Linalool                     |      225.4 | top   |       strong |  21.300 |    0.3381 |  0.001500 |  0.0050 |  0.14 | Linalool                      
|   8 | Methyl Benzoate              |      128.2 | heart |       strong |  40.000 |    6.4082 |  0.050000 |  0.0500 |  1.62 | Methyl Benzoate               
|   9 | Rose Oxide                   |       89.9 | heart | moderate-strong |   5.300 |    0.0450 |  0.000500 |  0.0030 |  0.09 | Rose Oxide                    
|  10 | Phenethyl Alcohol            |       84.2 | heart | moderate-strong |  11.570 |   16.8393 |  0.200000 |  0.4076 | 14.74 | Phenethyl Alcohol             
|  11 | Lemon FCF oil Sicilian       |       80.2 | top   | moderate-strong |   2.500 |    0.6415 |  0.008000 |  0.1000 |  2.60 | Lemon FCF oil Sicilian        
|  12 | Indole                       |       79.8 | heart | moderate-strong |   1.500 |    0.0112 |  0.000140 |  0.0020 |  0.08 | Indole                        
|  13 | Orange Peel EO               |       36.5 | top   |     moderate |   1.900 |    0.3651 |  0.010000 |  0.0600 |  1.95 | Orange Peel EO                
|  14 | Patchouli EO                 |       31.7 | base  |     moderate |   0.060 |    0.0950 |  0.003000 |  0.8000 | 15.90 | Patchouli EO                  
|  15 | Evernyl                      |       18.5 | base  |     moderate |   0.100 |    0.0056 |  0.000300 |  0.0250 |  0.56 | Evernyl                       
|  16 | Cedarwood EO                 |       17.4 | base  |     moderate |   0.250 |    0.2614 |  0.015000 |  0.4900 | 10.59 | Cedarwood EO                  
|  17 | Ethylene Brassylate          |       12.4 | base  |     moderate |   0.008 |    0.0120 |  0.000970 |  0.9300 | 15.20 | Ethylene Brassylate           
|  18 | Vetiver EO                   |        8.8 | base  |  perceptible |   0.050 |    0.0441 |  0.005000 |  0.4500 |  8.94 | Vetiver EO                    
|  19 | Benzyl Acetate               |        1.6 | heart | at threshold |   0.220 |    0.0319 |  0.020000 |  0.0500 |  1.47 | Benzyl Acetate                
|  20 | Ylang Ylang EO               |        1.1 | heart | at threshold |   0.050 |    0.0011 |  0.001000 |  0.0100 |  0.22 | Ylang Ylang EO                
|  21 | Benzyl Salicylate            |        0.5 | base  | sub-threshold |   0.030 |    0.0047 |  0.010000 |  0.0700 |  1.35 | Benzyl Salicylate             
|  22 | Musk Ketone                  |        0.2 | base  | sub-threshold |   0.003 |    0.0004 |  0.002000 |  0.0840 |  1.26 | Musk Ketone                   
|  23 | Olibanum Resinoid Absolute   |        0.1 | base  | sub-threshold |   0.080 |    0.0013 |  0.010000 |  0.0080 |  0.16 | Olibanum Resinoid             
|  24 | Ambrettolide                 |        0.1 | base  | sub-threshold |   0.003 |    0.0000 |  0.000136 |  0.0030 |  0.05 | Ambrettolide                  
|  25 | Benzoin Sumatra Resinoid     |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.003000 |  0.0190 |  0.40 | Benzoin Sumatra Resinoid      
|  26 | Siam Benzoin                 |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.040000 |  0.1300 |  2.71 | Siam Benzoin                  
|  27 | Labdanum                     |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.005000 |  0.0200 |  0.29 | Labdanum                      
|  28 | Geraniol                     |        0.0 | heart | sub-threshold |   4.000 |    0.0000 |  0.000040 |  0.0000 |  0.00 | Geraniol                      

**Materials:** 28 total (3 top, 13 heart, 12 base)
**Total vapor:** 30.16 ppm

### Note Distribution

**TOP:** 3 mats, 3.6% active, 5.3% OAV
  - Linalool                     OAV=   225.4 (strong) VP=21.300Pa
  - Lemon FCF oil Sicilian       OAV=    80.2 (moderate-strong) VP=2.500Pa
  - Orange Peel EO               OAV=    36.5 (moderate) VP=1.900Pa
**HEART:** 13 mats, 30.0% active, 93.3% OAV
  - Alpha Ionone                 OAV=  2041.7 (very strong) VP=1.500Pa
  - Hedione HC                   OAV=  1037.6 (very strong) VP=0.089Pa
  - Hedione                      OAV=  1037.6 (very strong) VP=0.089Pa
  - Bergamot FCF oil Sicilian    OAV=   589.5 (strong) VP=40.000Pa
  - Damascone Beta               OAV=   510.4 (strong) VP=1.500Pa
  - Gamma Decalactone            OAV=   382.5 (strong) VP=0.800Pa
  ... and 7 more
**BASE:** 12 mats, 66.4% active, 1.4% OAV
  - Patchouli EO                 OAV=    31.7 (moderate) VP=0.060Pa
  - Evernyl                      OAV=    18.5 (moderate) VP=0.100Pa
  - Cedarwood EO                 OAV=    17.4 (moderate) VP=0.250Pa
  - Ethylene Brassylate          OAV=    12.4 (moderate) VP=0.008Pa
  - Vetiver EO                   OAV=     8.8 (perceptible) VP=0.050Pa
  - Benzyl Salicylate            OAV=     0.5 (sub-threshold) VP=0.030Pa
  ... and 6 more

### Sub-threshold Materials (OAV < 1)
8/28 materials below perceptible threshold
  - Geraniol: OAV=0.00 VP=4.000Pa act=0uL role=Geraniol [Structural (acceptable)]
  - Siam Benzoin: OAV=0.00 VP=0.000Pa act=130uL role=Siam Benzoin [Structural (acceptable)]
  - Benzoin Sumatra Resinoid: OAV=0.00 VP=0.000Pa act=19uL role=Benzoin Sumatra Resi [Structural (acceptable)]
  - Olibanum Resinoid Absolute: OAV=0.13 VP=0.080Pa act=8uL role=Olibanum Resinoid [Structural (acceptable)]
  - Labdanum: OAV=0.00 VP=0.000Pa act=20uL role=Labdanum [Structural (acceptable)]
  - Musk Ketone: OAV=0.19 VP=0.003Pa act=84uL role=Musk Ketone [**Needs higher dose**]
  - Ambrettolide: OAV=0.11 VP=0.003Pa act=3uL role=Ambrettolide [Structural (acceptable)]
  - Benzyl Salicylate: OAV=0.47 VP=0.030Pa act=70uL role=Benzyl Salicylate [Structural (acceptable)]

### OAV by Odor Family

           floral  66.2% =================================  (6 mats)
           citrus  11.0% =====  (3 mats)
             rose  10.7% =====  (4 mats)
         gourmand   6.0% ==  (3 mats)
         aromatic   3.5% =  (1 mats)
          indolic   1.2% =  (1 mats)
            woody   0.9% =  (3 mats)
             moss   0.3% =  (1 mats)
             musk   0.2% =  (3 mats)
       salicylate   0.0% =  (1 mats)
            smoky   0.0% =  (1 mats)
            amber   0.0% =  (1 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  3.6/30.0/66.4 |  30.16ppm |   6000 | Alpha Ionone(2042), Hedione HC(1038), Hedione(1038)
| top          |    300s |  3.6/30.0/66.4 |  29.89ppm |   5995 | Alpha Ionone(2044), Hedione HC(1039), Hedione(1039)
| heart        |   1800s |  3.6/29.6/66.7 |  28.63ppm |   5972 | Alpha Ionone(2053), Hedione HC(1047), Hedione(1047)
| late_heart   |   7200s |  3.6/28.6/67.8 |  24.68ppm |   5896 | Alpha Ionone(2081), Hedione HC(1073), Hedione(1073)
| drydown      |  14400s |  3.5/27.5/69.0 |  20.61ppm |   5813 | Alpha Ionone(2108), Hedione HC(1103), Hedione(1103)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:3.6% H:30.0% B:66.4%  Vapor:30.16ppm
  Leaders: Alpha Ionone OAV 2042 | Hedione HC OAV 1038 | Hedione OAV 1038 | Bergamot FCF oil Sicilian OAV 590 | Damascone Beta OAV 510

**TOP** (300.0s) — Evap:0%
  T:3.6% H:30.0% B:66.4%  Vapor:29.89ppm
  Leaders: Alpha Ionone OAV 2044 | Hedione HC OAV 1039 | Hedione OAV 1039 | Bergamot FCF oil Sicilian OAV 579 | Damascone Beta OAV 511

**HEART** (1800.0s) — Evap:0%
  T:3.6% H:29.6% B:66.7%  Vapor:28.63ppm
  Leaders: Alpha Ionone OAV 2053 | Hedione HC OAV 1047 | Hedione OAV 1047 | Bergamot FCF oil Sicilian OAV 529 | Damascone Beta OAV 513

**LATE_HEART** (7200.0s) — Evap:2%
  T:3.6% H:28.6% B:67.8%  Vapor:24.68ppm
  Leaders: Alpha Ionone OAV 2081 | Hedione HC OAV 1073 | Hedione OAV 1073 | Damascone Beta OAV 520 | Gamma Decalactone OAV 392

**DRYDOWN** (14400.0s) — Evap:3%
  T:3.5% H:27.5% B:69.0%  Vapor:20.61ppm
  Leaders: Alpha Ionone OAV 2108 | Hedione HC OAV 1103 | Hedione OAV 1103 | Damascone Beta OAV 527 | Gamma Decalactone OAV 400

## Perfumer's Assessment

### 1. Character
  Top: Linalool(strong) + Lemon FCF oil Sicilian(moderate-strong) + Orange Peel EO(moderate)
  Heart: Alpha Ionone(very strong) + Hedione HC(very strong)
  Base: Patchouli EO(moderate) + Evernyl(moderate) + Cedarwood EO(moderate) + Ethylene Brassylate(moderate) + Vetiver EO(perceptible)

### 2. Opening (0-5min)
  Linalool dominates at OAV 225 (strong).
  - Linalool OAV=225 VP=21.3Pa (aromatic)
  - Lemon FCF oil Sicilian OAV=80 VP=2.5Pa (citrus)
  - Orange Peel EO OAV=37 VP=1.9Pa (citrus)
  Total vapor: 30.2 ppm

### 3. Heart (30min-2hr)
  Alpha Ionone OAV=2053 (very strong)
  Hedione HC OAV=1047 (very strong)
  Hedione OAV=1047 (very strong)
  Bergamot FCF oil Sicilian OAV=529 (strong)
  T:3.6% H:29.6% B:66.7%
  Vapor: 28.6 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 69% of headspace
  - Alpha Ionone OAV=2108
  - Hedione HC OAV=1103
  - Hedione OAV=1103
  - Damascone Beta OAV=527
  - Gamma Decalactone OAV=400
  - Bergamot FCF oil Sicilian OAV=244
  Vapor: 20.6 ppm

### 5. Sillage & Diffusion
  Primary carriers: Alpha Ionone(2042) + Hedione HC(1038) + Hedione(1038) + Bergamot FCF oil Sicilian(590)
  OAV by family: floral66% citrus11% rose11% gourmand6%

### 6. Longevity
  Evaporation: 3% over 4h
  Vapor: 30.2 > 20.6 ppm
  Base @ drydown: 69%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:3.6% H:30.0% B:66.4%
  OAV range: 0.00 to 2042 (sigma-log=1.99)
  Wide contrast: citrus (OAV 2042) dominates opening before burning off to reveal base.
    sub-threshold: 7

### 8. Flags
  SUB: Benzyl Salicylate OAV=0.47 role=Benzyl Salicylate
  SUB: Musk Ketone OAV=0.19 role=Musk Ketone
  SUB: Olibanum Resinoid Absolute OAV=0.13 role=Olibanum Resinoid
  SUB: Ambrettolide OAV=0.11 role=Ambrettolide
  SUB: Benzoin Sumatra Resinoid OAV=0.00 role=Benzoin Sumatra Resinoid
  SUB: Siam Benzoin OAV=0.00 role=Siam Benzoin
  SUB: Labdanum OAV=0.00 role=Labdanum
  SUB: Geraniol OAV=0.00 role=Geraniol
  IFRA: Evernyl at 0.55% active — check Cat4 limit (0.1% in product = 0.5% at 20% EdP)


## Structural OAV Analysis

**Vapor:** 30 ppm  |  **Active:** 15.2%  |  **Perceptible:** 20/28

### OAV Tiers
  **massive** (3): Hedione HC(1038), Alpha Ionone(2042), Hedione(1038)
  **v.strong** (5): Bergamot FCF oil Sicilian(590), Gamma Decalactone(383), Damascone Beta(510), Methyl Benzoate(128), Linalool(225)
  **strong** (4): Lemon FCF oil Sicilian(80), Phenethyl Alcohol(84), Indole(80), Rose Oxide(90)
  **moderate** (5): Orange Peel EO(37), Patchouli EO(32), Evernyl(19), Cedarwood EO(17), Ethylene Brassylate(12)
  **perceptible** (1): Vetiver EO(9)
  **threshold** (2): Benzyl Acetate(2), Ylang Ylang EO(1)
  **sub** (8): Geraniol(0), Siam Benzoin(0), Benzoin Sumatra Resinoid(0), Olibanum Resinoid Absolute(0), Labdanum(0), Musk Ketone(0), Ambrettolide(0), Benzyl Salicylate(0)

### Block Balance
  **Citrus**      706 (11%)
  **Floral**     5697 (89%)
  **Base**         12 (0%)
  **Ratio:** 456:1 between strongest/weakest block

### Issues
  ! 8 sub-threshold material(s): Geraniol, Siam Benzoin, Benzoin Sumatra Resinoid, Olibanum Resinoid Absolute, Labdanum, Musk Ketone, Ambrettolide, Benzyl Salicylate
```
