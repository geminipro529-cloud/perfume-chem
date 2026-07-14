# Classic Chypre - Coty Chypre Study - 30 mL EdP

**Historical reference:** Coty Chypre  
**Family archetype:** `chypre_classical.coty_reference`  
**Concentration:** 20.0% EdP · 6,000 µL concentrate in 30 mL  
**Historical gap:** True oakmoss and labdanum are absent, and vintage animalics are not available. `Evernyl` provides the moss memory while `Siam Benzoin`, `Benzoin Sumatra Resinoid`, and `Olibanum Resinoid Absolute` stand in for the balsamic labdanum shadow.  
**Why this structure matters:** Classical chypre is the architecture lesson of contrast: bright citrus flash over a dry mossy-woody-balsamic skeleton with only a restrained floral veil.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 80 | defining chypre opening (balanced) |
| 2 | Lemon FCF oil Sicilian | neat | 150 | sharpened hesperidic edge |
| 3 | Orange Peel EO | neat | 90 | soft citrus body |
| 4 | Phenethyl Alcohol | neat | 500 | floral veil |
| 5 | Linalool | neat | 5 | rosy accent (minimized) |
| 6 | Citronellol | neat | 200 | floral softness |
| 7 | Benzyl Acetate | neat | 100 | abstract jasmine brightness |
| 8 | Methyl Benzoate | neat | 50 | floral lift |
| 9 | Hedione HC | neat | 40 | jasmine air |
| 10 | Indole | 10% in DPG | 20 | hidden floral depth |
| 11 | Ylang Ylang EO | neat | 20 | waxy floral richness |
| 12 | Alpha Ionone | neat | 260 | dry iris shadow |
| 13 | Rose Oxide | 10% in DPG | 40 | metallic top shimmer |
| 14 | Patchouli EO | neat | 800 | dark chypre earth |
| 15 | Vetiver EO | neat | 500 | dry bitter root |
| 16 | Cedarwood EO | neat | 300 | structural wood |
| 17 | Evernyl | neat | 25 | moss memory |
| 18 | Siam Benzoin | 50% in DPG | 400 | warm balsamic cushion |
| 19 | Benzoin Sumatra Resinoid | 10% | 290 | balsamic sweetness |
| 20 | Olibanum Resinoid Absolute | 10% | 180 | incense projection |
| 21 | Labdanum | 10% in DPG | 250 | warm amber-resin shadow |
| 22 | Cedarwood EO | neat | 250 | structure (reduced) |
| 23 | Musk Ketone | 10% in DPG | 900 | clean soft trail |
| 24 | Geranium EO | neat | 80 | natural geranium-rose (replaces synthetic geraniol) |
| 25 | Ethylene Brassylate | neat | 290 | persistence (fill) |
| 26 | Ambrettolide | 10% in DPG | 30 | lift |
| 27 | Benzyl Salicylate | neat | 150 | waxy floral bridge |

**Total concentrate:** 6000 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Classic Chypre - Coty Chypre Study - 30 mL EdP

## Gate Summary

**83 PASS** / **19 WARN** / **1 FAIL**

  FAIL family_drift_detector: chypre_classical.coty_reference; citrus_flash: 1.333% active below 3.500
  WARN pipeline_preflight: 9 checks; 4 warnings
  WARN odt_coverage: 15 material(s) rely on derived/unverified ODTs (40% OAV share)
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 23.3% active mass across 4 materials
  WARN chypre_skeleton: Chypre skeleton missing: labdanum
  WARN safety_ifra_allergen: 10 materials lack explicit IFRA Cat4 limits; 1 materials near IFRA/headroom edge; 3 EU allergen declarations
  WARN eu_allergen_declaration: EU allergens requiring label: linalool, citronellol, benzyl salicylate
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid needs improvement: Expected T:20% H:30% B:50%, Actual T:5.7% H:31.4% B:62.9%; top OAV needs improvement for family chypre; heart OAV
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:lemon fcf oil sicilian = 13:1; bergamot fcf sicilian:orange peel eo = 29:1; berga
  WARN jnd_redundancy: Potentially redundant pairs: phenethyl alcohol vs rose oxide in rose (OAV 105/119); methyl benzoate vs hedione in floral (OAV 128/138)
  WARN jellinek_psychology: Jellinek categories weak: erogenic, stimulating, anti_erogenic
  WARN roudnitska_hedione_pct: Hedione = 0.7% of concentrate (<5%, minimal radiance effect)
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: vetiver eo OAV 9.8 is below chypre target 10.0-25.0; material_class_distribution: Class distribution: animalic:0%, fixatives:4%, florals:20%
  WARN olfactory_fatigue: Olfactory fatigue risk: alpha ionone=2202 (limit 2000); hedione=0.7% of concentrate (<10% minimum for radiance)
  WARN evaporation_rate_balance: Pyramid imbalance: base = 63%
  WARN confidence_minimum: combined confidence 46.0; preflight science penalty 32.5


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Alpha Ionone                 |     2202.2 | heart |  very strong |   1.500 |    0.8809 |  0.000400 |  0.2600 |  5.95 | Alpha Ionone                  
|   2 | Bergamot FCF oil Sicilian    |     1565.2 | heart |  very strong |  40.000 |    9.3910 |  0.006000 |  0.0800 |  2.38 | Bergamot FCF oil Sicilian     
|   3 | Geranium EO                  |      368.9 | heart |       strong |   2.500 |    0.5533 |  0.001500 |  0.0800 |  2.24 | Geranium EO                   
|   4 | Linalool                     |      224.6 | top   |       strong |  21.300 |    0.3368 |  0.001500 |  0.0050 |  0.14 | Linalool                      
|   5 | Hedione HC                   |      137.9 | heart |       strong |   0.089 |    0.0069 |  0.000050 |  0.0400 |  0.78 | Hedione                       
|   6 | Methyl Benzoate              |      127.6 | heart |       strong |  40.000 |    6.3802 |  0.050000 |  0.0500 |  1.62 | Methyl Benzoate               
|   7 | Lemon FCF oil Sicilian       |      119.8 | top   |       strong |   2.500 |    0.9581 |  0.008000 |  0.1500 |  3.88 | Lemon FCF oil Sicilian        
|   8 | Rose Oxide                   |      119.4 | heart |       strong |   5.300 |    0.0597 |  0.000500 |  0.0040 |  0.11 | Rose Oxide                    
|   9 | Phenethyl Alcohol            |      104.8 | heart |       strong |  11.570 |   20.9574 |  0.200000 |  0.5095 | 18.34 | Phenethyl Alcohol             
|  10 | Indole                       |       79.4 | heart | moderate-strong |   1.500 |    0.0111 |  0.000140 |  0.0020 |  0.08 | Indole                        
|  11 | Citronellol                  |       62.5 | heart | moderate-strong |   4.500 |    2.5010 |  0.040000 |  0.2000 |  5.63 | Citronellol                   
|  12 | Orange Peel EO               |       54.5 | top   | moderate-strong |   1.900 |    0.5452 |  0.010000 |  0.0900 |  2.91 | Orange Peel EO                
|  13 | Patchouli EO                 |       31.5 | base  |     moderate |   0.060 |    0.0944 |  0.003000 |  0.8000 | 15.82 | Patchouli EO                  
|  14 | Cedarwood EO                 |       19.5 | base  |     moderate |   0.250 |    0.2922 |  0.015000 |  0.5500 | 11.84 | Cedarwood EO                  
|  15 | Evernyl                      |       18.4 | base  |     moderate |   0.100 |    0.0055 |  0.000300 |  0.0250 |  0.56 | Evernyl                       
|  16 | Vetiver EO                   |        9.8 | base  |  perceptible |   0.050 |    0.0488 |  0.005000 |  0.5000 |  9.89 | Vetiver EO                    
|  17 | Ethylene Brassylate          |        3.8 | base  | at threshold |   0.008 |    0.0037 |  0.000970 |  0.2900 |  4.72 | Ethylene Brassylate           
|  18 | Benzyl Acetate               |        3.2 | heart | at threshold |   0.220 |    0.0636 |  0.020000 |  0.1000 |  2.93 | Benzyl Acetate                
|  19 | Ylang Ylang EO               |        2.2 | heart | at threshold |   0.050 |    0.0022 |  0.001000 |  0.0200 |  0.44 | Ylang Ylang EO                
|  20 | Benzyl Salicylate            |        1.0 | base  | at threshold |   0.030 |    0.0100 |  0.010000 |  0.1500 |  2.89 | Benzyl Salicylate             
|  21 | Olibanum Resinoid Absolute   |        0.3 | base  | sub-threshold |   0.080 |    0.0028 |  0.010000 |  0.0180 |  0.36 | Olibanum Resinoid             
|  22 | Musk Ketone                  |        0.2 | base  | sub-threshold |   0.003 |    0.0004 |  0.002000 |  0.0900 |  1.35 | Musk Ketone                   
|  23 | Ambrettolide                 |        0.1 | base  | sub-threshold |   0.003 |    0.0000 |  0.000136 |  0.0030 |  0.05 | Ambrettolide                  
|  24 | Benzoin Sumatra Resinoid     |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.003000 |  0.0290 |  0.60 | Benzoin Sumatra Resinoid      
|  25 | Siam Benzoin                 |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.040000 |  0.2000 |  4.14 | Siam Benzoin                  
|  26 | Labdanum                     |        0.0 | base  | sub-threshold |   0.000 |    0.0000 |  0.005000 |  0.0250 |  0.37 | Labdanum                      

**Materials:** 26 total (3 top, 11 heart, 12 base)
**Total vapor:** 43.11 ppm

### Note Distribution

**TOP:** 3 mats, 5.7% active, 7.6% OAV
  - Linalool                     OAV=   224.6 (strong) VP=21.300Pa
  - Lemon FCF oil Sicilian       OAV=   119.8 (strong) VP=2.500Pa
  - Orange Peel EO               OAV=    54.5 (moderate-strong) VP=1.900Pa
**HEART:** 11 mats, 31.4% active, 90.8% OAV
  - Alpha Ionone                 OAV=  2202.2 (very strong) VP=1.500Pa
  - Bergamot FCF oil Sicilian    OAV=  1565.2 (very strong) VP=40.000Pa
  - Geranium EO                  OAV=   368.9 (strong) VP=2.500Pa
  - Hedione HC                   OAV=   137.9 (strong) VP=0.089Pa
  - Methyl Benzoate              OAV=   127.6 (strong) VP=40.000Pa
  - Rose Oxide                   OAV=   119.4 (strong) VP=5.300Pa
  ... and 5 more
**BASE:** 12 mats, 62.9% active, 1.6% OAV
  - Patchouli EO                 OAV=    31.5 (moderate) VP=0.060Pa
  - Cedarwood EO                 OAV=    19.5 (moderate) VP=0.250Pa
  - Evernyl                      OAV=    18.4 (moderate) VP=0.100Pa
  - Vetiver EO                   OAV=     9.8 (perceptible) VP=0.050Pa
  - Ethylene Brassylate          OAV=     3.8 (at threshold) VP=0.008Pa
  - Benzyl Salicylate            OAV=     1.0 (at threshold) VP=0.030Pa
  ... and 6 more

### Sub-threshold Materials (OAV < 1)
6/26 materials below perceptible threshold
  - Siam Benzoin: OAV=0.00 VP=0.000Pa act=200uL role=Siam Benzoin [Structural (acceptable)]
  - Benzoin Sumatra Resinoid: OAV=0.00 VP=0.000Pa act=29uL role=Benzoin Sumatra Resi [Structural (acceptable)]
  - Olibanum Resinoid Absolute: OAV=0.28 VP=0.080Pa act=18uL role=Olibanum Resinoid [Structural (acceptable)]
  - Labdanum: OAV=0.00 VP=0.000Pa act=25uL role=Labdanum [Structural (acceptable)]
  - Musk Ketone: OAV=0.20 VP=0.003Pa act=90uL role=Musk Ketone [**Needs higher dose**]
  - Ambrettolide: OAV=0.11 VP=0.003Pa act=3uL role=Ambrettolide [Structural (acceptable)]

### OAV by Odor Family

           floral  54.1% ===========================  (6 mats)
           citrus  33.1% ================  (3 mats)
             rose   5.5% ==  (3 mats)
         aromatic   4.3% ==  (1 mats)
          indolic   1.5% =  (1 mats)
            woody   1.2% =  (3 mats)
             moss   0.4% =  (1 mats)
             musk   0.1% =  (3 mats)
       salicylate   0.0% =  (1 mats)
            smoky   0.0% =  (1 mats)
         gourmand   0.0% =  (2 mats)
            amber   0.0% =  (1 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  5.7/31.4/62.9 |  43.11ppm |   6000 | Alpha Ionone(2202), Bergamot FCF(1565), Geranium EO(369)
| top          |    300s |  5.8/31.3/63.0 |  42.74ppm |   5993 | Alpha Ionone(2206), Bergamot FCF(1538), Geranium EO(369)
| heart        |   1800s |  5.8/30.8/63.5 |  41.01ppm |   5959 | Alpha Ionone(2223), Bergamot FCF(1409), Geranium EO(371)
| late_heart   |   7200s |  5.8/29.1/65.1 |  35.57ppm |   5851 | Alpha Ionone(2278), Bergamot FCF(1024), Geranium EO(376)
| drydown      |  14400s |  5.8/27.3/66.9 |  29.95ppm |   5732 | Alpha Ionone(2336), Bergamot FCF(664), Geranium EO(381)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:5.7% H:31.4% B:62.9%  Vapor:43.11ppm
  Leaders: Alpha Ionone OAV 2202 | Bergamot FCF oil Sicilian OAV 1565 | Geranium EO OAV 369 | Linalool OAV 225 | Hedione HC OAV 138

**TOP** (300.0s) — Evap:0%
  T:5.8% H:31.3% B:63.0%  Vapor:42.74ppm
  Leaders: Alpha Ionone OAV 2206 | Bergamot FCF oil Sicilian OAV 1538 | Geranium EO OAV 369 | Linalool OAV 222 | Hedione HC OAV 138

**HEART** (1800.0s) — Evap:1%
  T:5.8% H:30.8% B:63.5%  Vapor:41.01ppm
  Leaders: Alpha Ionone OAV 2223 | Bergamot FCF oil Sicilian OAV 1409 | Geranium EO OAV 371 | Linalool OAV 212 | Hedione HC OAV 140

**LATE_HEART** (7200.0s) — Evap:2%
  T:5.8% H:29.1% B:65.1%  Vapor:35.57ppm
  Leaders: Alpha Ionone OAV 2278 | Bergamot FCF oil Sicilian OAV 1024 | Geranium EO OAV 376 | Linalool OAV 179 | Hedione HC OAV 145

**DRYDOWN** (14400.0s) — Evap:4%
  T:5.8% H:27.3% B:66.9%  Vapor:29.95ppm
  Leaders: Alpha Ionone OAV 2336 | Bergamot FCF oil Sicilian OAV 664 | Geranium EO OAV 381 | Hedione HC OAV 151 | Linalool OAV 141

## Perfumer's Assessment

### 1. Character
  Top: Linalool(strong) + Lemon FCF oil Sicilian(strong) + Orange Peel EO(moderate-strong)
  Heart: Alpha Ionone(very strong) + Bergamot FCF oil Sicilian(very strong)
  Base: Patchouli EO(moderate) + Cedarwood EO(moderate) + Evernyl(moderate) + Vetiver EO(perceptible) + Ethylene Brassylate(at threshold)

### 2. Opening (0-5min)
  Linalool dominates at OAV 225 (strong).
  - Linalool OAV=225 VP=21.3Pa (aromatic)
  - Lemon FCF oil Sicilian OAV=120 VP=2.5Pa (citrus)
  - Orange Peel EO OAV=55 VP=1.9Pa (citrus)
  Total vapor: 43.1 ppm

### 3. Heart (30min-2hr)
  Alpha Ionone OAV=2223 (very strong)
  Bergamot FCF oil Sicilian OAV=1409 (very strong)
  Geranium EO OAV=371 (strong)
  Linalool OAV=212 (strong)
  T:5.8% H:30.8% B:63.5%
  Vapor: 41.0 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 67% of headspace
  - Alpha Ionone OAV=2336
  - Bergamot FCF oil Sicilian OAV=664
  - Geranium EO OAV=381
  - Hedione HC OAV=151
  - Linalool OAV=141
  - Lemon FCF oil Sicilian OAV=124
  Vapor: 29.9 ppm

### 5. Sillage & Diffusion
  Primary carriers: Alpha Ionone(2202) + Bergamot FCF oil Sicilian(1565)
  OAV by family: floral54% citrus33% rose5% aromatic4%

### 6. Longevity
  Evaporation: 4% over 4h
  Vapor: 43.1 > 29.9 ppm
  Base @ drydown: 67%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:5.7% H:31.4% B:62.9%
  OAV range: 0.00 to 2202 (sigma-log=1.89)
  Wide contrast: citrus (OAV 2202) dominates opening before burning off to reveal base.
    sub-threshold: 6

### 8. Flags
  SUB: Olibanum Resinoid Absolute OAV=0.28 role=Olibanum Resinoid
  SUB: Musk Ketone OAV=0.20 role=Musk Ketone
  SUB: Ambrettolide OAV=0.11 role=Ambrettolide
  SUB: Benzoin Sumatra Resinoid OAV=0.00 role=Benzoin Sumatra Resinoid
  SUB: Siam Benzoin OAV=0.00 role=Siam Benzoin
  SUB: Labdanum OAV=0.00 role=Labdanum
  IFRA: Evernyl at 0.59% active — check Cat4 limit (0.1% in product = 0.5% at 20% EdP)


## Structural OAV Analysis

**Vapor:** 43 ppm  |  **Active:** 14.2%  |  **Perceptible:** 20/26

### OAV Tiers
  **massive** (2): Bergamot FCF oil Sicilian(1565), Alpha Ionone(2202)
  **v.strong** (7): Lemon FCF oil Sicilian(120), Phenethyl Alcohol(105), Linalool(225), Methyl Benzoate(128), Hedione HC(138), Rose Oxide(119), Geranium EO(369)
  **strong** (3): Orange Peel EO(55), Citronellol(63), Indole(79)
  **moderate** (3): Patchouli EO(31), Cedarwood EO(19), Evernyl(18)
  **perceptible** (1): Vetiver EO(10)
  **threshold** (4): Benzyl Acetate(3), Ylang Ylang EO(2), Ethylene Brassylate(4), Benzyl Salicylate(1)
  **sub** (6): Siam Benzoin(0), Benzoin Sumatra Resinoid(0), Olibanum Resinoid Absolute(0), Labdanum(0), Musk Ketone(0), Ambrettolide(0)

### Block Balance
  **Citrus**     1739 (33%)
  **Floral**     3513 (67%)
  **Base**          4 (0%)
  **Ratio:** 888:1 between strongest/weakest block

### Issues
  ! 6 sub-threshold material(s): Siam Benzoin, Benzoin Sumatra Resinoid, Olibanum Resinoid Absolute, Labdanum, Musk Ketone, Ambrettolide
```
