# Floral Aldehydic — No. 5 Study — 30 mL EdP

**Historical reference:** Chanel No. 5  
**Family archetype:** `floral_aldehydic.no5_reference`  
**Concentration:** 20.0% EdP · 6,000 µL concentrate in 30 mL  
**Historical gap:** There is no real neroli, orris butter, civet, or vintage sandalwood/oakmoss depth in stock. This study keeps the core No. 5 lesson: aldehydic halo over rose-jasmine-ylang and a powder-musk base.  
**Why this structure matters:** Floral aldehydic is the classical abstraction lesson. The fragrance does not smell like one flower; it smells like a constructed, glowing idea of floral luxury.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 30 | citrus trace |
| 2 | Aldehyde C10 | 1% in DPG | 500 | sparkle — 5 µL active, dominates opening then clears |
| 3 | Aldehyde C11 | 1% in DPG | 300 | waxy-clean luminosity — 3 µL active, amplifies the halo |
| 4 | Aldehyde C12 MNA | 1% in DPG | 100 | signature aldehydic flash — 1 µL active, micro-dose |
| 5 | Linalool | neat | 200 | floral-citrus air (increased — bridges aldehydes to heart) |
| 6 | Phenethyl Alcohol | neat | 500 | rose body |
| 7 | Geraniol | neat | 10 | rose whisper |
| 8 | Citronellol | neat | 300 | rosy softness (increased — bridges) |
| 9 | Hedione | neat | 700 | jasmine radiance (increased — competes with ylang in heart) |
| 10 | Benzyl Acetate | neat | 600 | jasmine freshness (increased — more jasmine body) |
| 11 | Methyl Benzoate | neat | 70 | abstract white-floral lift |
| 12 | Cis Jasmone | neat | 20 | warm jasmine nuance |
| 13 | Hydroxycitronellal | neat | 250 | muguet cushion (1909 — era-perfect) |
| 14 | Ylang Ylang EO | neat | 150 | exotic richness (essential to No.5) |
| 15 | Ylang Comoros Complete EO F3255 | neat | 70 | fatty floral depth |
| 16 | Benzyl Salicylate | neat | 250 | powder-waxy heart-to-base link |
| 17 | Vanillin | 10% in DPG | 80 | trace powder accent |
| 18 | Alpha Ionone | neat | 80 | iris-powder tone (1893 — era-perfect) |
| 19 | Musk Ketone | 10% in DPG | 360 | classical nitro-musk (1888 — era-perfect) |
| 20 | Ethylene Brassylate | neat | 1295 | invisible macrocyclic fixative (fill) |
| 21 | Ambrettolide | 10% in DPG | 30 | lift in the drydown |
| 22 | Cedarwood EO | neat | 100 | discreet wood structure |
| 23 | BHT (antioxidant) | neat | 5 | stabilizer |

**Total concentrate:** 6000 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Floral Aldehydic — No. 5 Study — 30 mL EdP

## Gate Summary

**81 PASS** / **20 WARN** / **2 FAIL**

  FAIL chemistry_stability: predicted maturation shelf life 7 days
  FAIL family_drift_detector: floral_aldehydic.no5_reference; aldehydic_halo: 0.150% active below 0.180
  WARN pipeline_preflight: 9 checks; 3 warnings
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 24.7% active mass across 4 materials
  WARN dilution_accuracy: Check pipetting: aldehyde c10: 500.0uL at 1%; aldehyde c11: 300.0uL at 1%; aldehyde c12 mna: 100.0uL at 1%
  WARN safety_ifra_allergen: 5 materials lack explicit IFRA Cat4 limits; 1 materials near IFRA/headroom edge; 6 EU allergen declarations
  WARN eu_allergen_declaration: EU allergens requiring label: linalool, geraniol, citronellol, hydroxycitronellal, benzyl salicylate
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid needs improvement: Expected T:20% H:50% B:30%, Actual T:4.5% H:59.3% B:36.2%; top OAV needs improvement for family floral; heart OAV
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:aldehyde c11 = 12:1; bergamot fcf sicilian:aldehyde c12 mna = 913:1; bergamot fcf
  WARN jnd_redundancy: Potentially redundant pairs: phenethyl alcohol vs citronellol in rose (OAV 95/85); benzyl acetate vs ylang in floral (OAV 17/15)
  WARN guerlain_vanillin_coumarin: Vanillin present without coumarin — no structural counterweight
  WARN jellinek_psychology: Jellinek categories weak: erogenic, anti_erogenic
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: linalool OAV 8075.2 is above floral_jasmine target 10.0-25.0; hedione OAV 2190.0 is above floral_jasmine target 40.0-80.0; methyl benzoate O
  WARN olfactory_fatigue: Olfactory fatigue risk: aldehyde c10=287 (limit 200)
  WARN evaporation_rate_balance: Pyramid imbalance: top = 4%
  WARN tenacity_projection: VP<0.001Pa = 0% (<3%, may lack depth)
  WARN master_perfumer_gate: opening likely underbuilt
  WARN confidence_minimum: combined confidence 46.9; preflight science penalty 29.4


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Linalool                     |     8075.2 | top   |  very strong |  21.300 |   12.1128 |  0.001500 |  0.2000 |  5.19 | Linalool                      
|   2 | Geraniol                     |     2562.5 | heart |  very strong |   4.000 |    0.1025 |  0.000040 |  0.0100 |  0.26 | Geraniol                      
|   3 | Hedione                      |     2190.0 | heart |  very strong |   0.089 |    0.1095 |  0.000050 |  0.7000 | 12.39 | Hedione                       
|   4 | Alpha Ionone                 |      616.8 | heart |       strong |   1.500 |    0.2467 |  0.000400 |  0.0800 |  1.67 | Alpha Ionone                  
|   5 | Bergamot FCF oil Sicilian    |      534.3 | heart |       strong |  40.000 |    3.2059 |  0.006000 |  0.0300 |  0.81 | Bergamot FCF oil Sicilian     
|   6 | Aldehyde C10                 |      287.5 | top   |       strong |  10.000 |    0.1265 |  0.000440 |  0.0050 |  0.13 | Aldehyde C10                  
|   7 | Methyl Benzoate              |      162.6 | heart |       strong |  40.000 |    8.1316 |  0.050000 |  0.0700 |  2.06 | Methyl Benzoate               
|   8 | Cis Jasmone                  |      121.3 | heart |       strong |   1.333 |    0.0607 |  0.000500 |  0.0189 |  0.46 | Cis Jasmone                   
|   9 | Phenethyl Alcohol            |       95.4 | heart | moderate-strong |  11.570 |   19.0786 |  0.200000 |  0.5095 | 16.70 | Phenethyl Alcohol             
|  10 | Citronellol                  |       85.4 | heart | moderate-strong |   4.500 |    3.4151 |  0.040000 |  0.3000 |  7.69 | Citronellol                   
|  11 | Hydroxycitronellal           |       76.5 | heart | moderate-strong |   2.000 |    1.1474 |  0.015000 |  0.2500 |  5.81 | Hydroxycitronellal            
|  12 | Aldehyde C11                 |       45.2 | top   |     moderate |   5.000 |    0.0348 |  0.000770 |  0.0030 |  0.07 | Aldehyde C11                  
|  13 | Benzyl Acetate               |       17.4 | heart |     moderate |   0.220 |    0.3475 |  0.020000 |  0.6000 | 15.99 | Benzyl Acetate                
|  14 | Ethylene Brassylate          |       15.6 | base  |     moderate |   0.008 |    0.0151 |  0.000970 |  1.2950 | 19.18 | Ethylene Brassylate           
|  15 | Ylang Ylang EO               |       14.8 | heart |     moderate |   0.050 |    0.0148 |  0.001000 |  0.1500 |  3.00 | Ylang Ylang EO                
|  16 | Cedarwood EO                 |        3.2 | base  | at threshold |   0.250 |    0.0484 |  0.015000 |  0.1000 |  1.96 | Cedarwood EO                  
|  17 | Benzyl Salicylate            |        1.5 | base  | at threshold |   0.030 |    0.0153 |  0.010000 |  0.2500 |  4.38 | Benzyl Salicylate             
|  18 | Aldehyde C12 MNA             |        0.6 | top   | sub-threshold |   3.000 |    0.0064 |  0.011000 |  0.0010 |  0.02 | Aldehyde C12 MNA              
|  19 | Vanillin                     |        0.5 | base  | sub-threshold |   0.200 |    0.0092 |  0.020000 |  0.0080 |  0.21 | Vanillin                      
|  20 | Ylang Comoros Complete EO F3255 |        0.2 | heart | sub-threshold |   0.050 |    0.0069 |  0.030000 |  0.0700 |  1.40 | Ylang Comoros Complete EO F325
|  21 | Ambrettolide                 |        0.1 | base  | sub-threshold |   0.003 |    0.0000 |  0.000136 |  0.0030 |  0.05 | Ambrettolide                  
|  22 | Musk Ketone                  |        0.1 | base  | sub-threshold |   0.003 |    0.0001 |  0.002000 |  0.0360 |  0.49 | Musk Ketone                   
|  23 | BHT (antioxidant)            |        0.0 | base  | sub-threshold |   0.001 |    0.0000 | 100.000000 |  0.0050 |  0.09 | BHT                           

**Materials:** 23 total (4 top, 12 heart, 7 base)
**Total vapor:** 48.24 ppm

### Note Distribution

**TOP:** 4 mats, 4.5% active, 56.4% OAV
  - Linalool                     OAV=  8075.2 (very strong) VP=21.300Pa
  - Aldehyde C10                 OAV=   287.5 (strong) VP=10.000Pa
  - Aldehyde C11                 OAV=    45.2 (moderate) VP=5.000Pa
  - Aldehyde C12 MNA             OAV=     0.6 (sub-threshold) VP=3.000Pa
**HEART:** 12 mats, 59.3% active, 43.5% OAV
  - Geraniol                     OAV=  2562.5 (very strong) VP=4.000Pa
  - Hedione                      OAV=  2190.0 (very strong) VP=0.089Pa
  - Alpha Ionone                 OAV=   616.8 (strong) VP=1.500Pa
  - Bergamot FCF oil Sicilian    OAV=   534.3 (strong) VP=40.000Pa
  - Methyl Benzoate              OAV=   162.6 (strong) VP=40.000Pa
  - Cis Jasmone                  OAV=   121.3 (strong) VP=1.333Pa
  ... and 6 more
**BASE:** 7 mats, 36.2% active, 0.1% OAV
  - Ethylene Brassylate          OAV=    15.6 (moderate) VP=0.008Pa
  - Cedarwood EO                 OAV=     3.2 (at threshold) VP=0.250Pa
  - Benzyl Salicylate            OAV=     1.5 (at threshold) VP=0.030Pa
  - Vanillin                     OAV=     0.5 (sub-threshold) VP=0.200Pa
  - Ambrettolide                 OAV=     0.1 (sub-threshold) VP=0.003Pa
  - Musk Ketone                  OAV=     0.1 (sub-threshold) VP=0.003Pa
  ... and 1 more

### Sub-threshold Materials (OAV < 1)
6/23 materials below perceptible threshold
  - Aldehyde C12 MNA: OAV=0.59 VP=3.000Pa act=1uL role=Aldehyde C12 MNA [Structural (acceptable)]
  - Ylang Comoros Complete EO F3255: OAV=0.23 VP=0.050Pa act=70uL role=Ylang Comoros Comple [Structural (acceptable)]
  - Vanillin: OAV=0.46 VP=0.200Pa act=8uL role=Vanillin [Structural (acceptable)]
  - Musk Ketone: OAV=0.07 VP=0.003Pa act=36uL role=Musk Ketone [**Needs higher dose**]
  - Ambrettolide: OAV=0.10 VP=0.003Pa act=3uL role=Ambrettolide [Structural (acceptable)]
  - BHT (antioxidant): OAV=0.00 VP=0.001Pa act=5uL role=BHT [Structural (acceptable)]
### High-OAV Flags (>5000)
  - Linalool OAV=8075 dominates headspace — may mask subtler notes

### OAV by Odor Family

         aromatic  54.2% ===========================  (1 mats)
           floral  21.0% ==========  (7 mats)
             rose  18.4% =========  (3 mats)
           citrus   3.6% =  (1 mats)
        aldehydic   2.2% =  (3 mats)
           muguet   0.5% =  (1 mats)
             musk   0.1% =  (3 mats)
            woody   0.0% =  (1 mats)
       salicylate   0.0% =  (1 mats)
         gourmand   0.0% =  (1 mats)
                ?   0.0% =  (1 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  4.5/59.3/36.2 |  48.24ppm |   6000 | Linalool(8075), Geraniol(2563), Hedione(2190)
| top          |    300s |  4.4/59.3/36.3 |  47.86ppm |   5988 | Linalool(8003), Geraniol(2564), Hedione(2195)
| heart        |   1800s |  4.2/59.2/36.6 |  46.04ppm |   5931 | Linalool(7652), Geraniol(2570), Hedione(2222)
| late_heart   |   7200s |  3.6/58.8/37.7 |  40.20ppm |   5744 | Linalool(6485), Geraniol(2584), Hedione(2311)
| drydown      |  14400s |  2.8/58.3/38.9 |  33.90ppm |   5532 | Linalool(5162), Geraniol(2583), Hedione(2418)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:4.5% H:59.3% B:36.2%  Vapor:48.24ppm
  Leaders: Linalool OAV 8075 | Geraniol OAV 2563 | Hedione OAV 2190 | Alpha Ionone OAV 617 | Bergamot FCF oil Sicilian OAV 534

**TOP** (300.0s) — Evap:0%
  T:4.4% H:59.3% B:36.3%  Vapor:47.86ppm
  Leaders: Linalool OAV 8003 | Geraniol OAV 2564 | Hedione OAV 2195 | Alpha Ionone OAV 618 | Bergamot FCF oil Sicilian OAV 525

**HEART** (1800.0s) — Evap:1%
  T:4.2% H:59.2% B:36.6%  Vapor:46.04ppm
  Leaders: Linalool OAV 7652 | Geraniol OAV 2570 | Hedione OAV 2222 | Alpha Ionone OAV 624 | Bergamot FCF oil Sicilian OAV 482

**LATE_HEART** (7200.0s) — Evap:4%
  T:3.6% H:58.8% B:37.7%  Vapor:40.20ppm
  Leaders: Linalool OAV 6485 | Geraniol OAV 2584 | Hedione OAV 2311 | Alpha Ionone OAV 642 | Bergamot FCF oil Sicilian OAV 351

**DRYDOWN** (14400.0s) — Evap:8%
  T:2.8% H:58.3% B:38.9%  Vapor:33.90ppm
  Leaders: Linalool OAV 5162 | Geraniol OAV 2583 | Hedione OAV 2418 | Alpha Ionone OAV 661 | Aldehyde C10 OAV 252

## Perfumer's Assessment

### 1. Character
  Top: Linalool(very strong) + Aldehyde C10(strong) + Aldehyde C11(moderate)
  Heart: Geraniol(very strong) + Hedione(very strong)
  Base: Ethylene Brassylate(moderate) + Cedarwood EO(at threshold) + Benzyl Salicylate(at threshold) + Vanillin(sub-threshold) + Ambrettolide(sub-threshold)

### 2. Opening (0-5min)
  Linalool dominates at OAV 8075 (very strong).
  - Linalool OAV=8075 VP=21.3Pa (aromatic)
  - Aldehyde C10 OAV=287 VP=10.0Pa (aldehydic)
  - Aldehyde C11 OAV=45 VP=5.0Pa (aldehydic)
  - Aldehyde C12 MNA OAV=1 VP=3.0Pa (aldehydic)
  Total vapor: 48.2 ppm

### 3. Heart (30min-2hr)
  Linalool OAV=7652 (very strong)
  Geraniol OAV=2570 (very strong)
  Hedione OAV=2222 (very strong)
  Alpha Ionone OAV=624 (strong)
  T:4.2% H:59.2% B:36.6%
  Vapor: 46.0 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 39% of headspace
  - Linalool OAV=5162
  - Geraniol OAV=2583
  - Hedione OAV=2418
  - Alpha Ionone OAV=661
  - Aldehyde C10 OAV=252
  - Bergamot FCF oil Sicilian OAV=229
  Vapor: 33.9 ppm

### 5. Sillage & Diffusion
  Primary carriers: Linalool(8075) + Geraniol(2563) + Hedione(2190) + Alpha Ionone(617)
  OAV by family: aromatic54% floral21% rose18% citrus4%

### 6. Longevity
  Evaporation: 8% over 4h
  Vapor: 48.2 > 33.9 ppm
  Base @ drydown: 39%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:4.5% H:59.3% B:36.2%
  OAV range: 0.00 to 8075 (sigma-log=2.28)
  Wide contrast: citrus (OAV 8075) dominates opening before burning off to reveal base.
    sub-threshold: 6

### 8. Flags
  SUB: Aldehyde C12 MNA OAV=0.59 role=Aldehyde C12 MNA
  SUB: Vanillin OAV=0.46 role=Vanillin
  SUB: Ylang Comoros Complete EO F3255 OAV=0.23 role=Ylang Comoros Complete EO F3255
  SUB: Ambrettolide OAV=0.10 role=Ambrettolide
  SUB: Musk Ketone OAV=0.07 role=Musk Ketone
  SUB: BHT (antioxidant) OAV=0.00 role=BHT


## Structural OAV Analysis

**Vapor:** 48 ppm  |  **Active:** 15.6%  |  **Perceptible:** 17/23

### OAV Tiers
  **massive** (3): Linalool(8075), Geraniol(2563), Hedione(2190)
  **v.strong** (5): Bergamot FCF oil Sicilian(534), Aldehyde C10(287), Methyl Benzoate(163), Cis Jasmone(121), Alpha Ionone(617)
  **strong** (3): Phenethyl Alcohol(95), Citronellol(85), Hydroxycitronellal(76)
  **moderate** (4): Aldehyde C11(45), Benzyl Acetate(17), Ylang Ylang EO(15), Ethylene Brassylate(16)
  **threshold** (2): Benzyl Salicylate(2), Cedarwood EO(3)
  **sub** (6): Aldehyde C12 MNA(1), Ylang Comoros Complete EO F3255(0), Vanillin(0), Musk Ketone(0), Ambrettolide(0), BHT (antioxidant)(0)

### Block Balance
  **Citrus**      534 (4%)
  **Floral**    14357 (96%)
  **Base**         16 (0%)
  **Ratio:** 913:1 between strongest/weakest block

### Issues
  ! 6 sub-threshold material(s): Aldehyde C12 MNA, Ylang Comoros Complete EO F3255, Vanillin, Musk Ketone, Ambrettolide, BHT (antioxidant)
```
