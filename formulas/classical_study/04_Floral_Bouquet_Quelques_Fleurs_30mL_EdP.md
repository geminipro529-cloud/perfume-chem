# Floral Bouquet - Quelques Fleurs Study - 30 mL EdP

**Historical reference:** Houbigant Quelques Fleurs  
**Family archetype:** `floral_bouquet.quelques_fleurs_reference`  
**Concentration:** 20.0% EdP · 6,000 µL concentrate in 30 mL  
**Historical gap:** True jasmine absolute, neroli, and antique carnation/orris materials are missing. The bouquet is taught through a current-stock rose-jasmine-muguet architecture built from rose alcohols, muguet materials, `Benzyl Acetate`, `Methyl Benzoate`, `Cis Jasmone`, and restrained aldehydic lift.  
**Why this structure matters:** Floral bouquet is the classical lesson in proportion: no flower should read alone, but the bouquet must still feel full, radiant, and expensive.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 200 | bright opening |
| 2 | Aldehyde C10 | 1% in DPG | 500 | sparkle |
| 3 | Aldehyde C11 | 1% in DPG | 450 | waxy-clean luminosity |
| 4 | Aldehyde C12 MNA | 1% in DPG | 400 | the aldehydic halo |
| 5 | Phenethyl Alcohol | neat | 800 | rose body |
| 6 | Geraniol | neat | 10 | rose whisper |
| 7 | Citronellol | neat | 600 | rosy softness |
| 8 | Nerol | neat | 100 | citrus-rose freshness |
| 9 | Phenyl Ethyl Dimethyl Carbinol | neat | 140 | polished rose bloom |
| 10 | Rose Oxide | 10% in DPG | 50 | rosy lift |
| 11 | Hedione | neat | 600 | bouquet radiance |
| 12 | Hedione HC | neat | 150 | jasmine luminosity |
| 13 | Benzyl Acetate | neat | 400 | jasmine brightness |
| 14 | Methyl Benzoate | neat | 60 | floral lift |
| 15 | Cis Jasmone | neat | 25 | jasmine nuance |
| 16 | Hydroxycitronellal | neat | 280 | muguet cradle |
| 17 | Hydroxycitronellal | neat | 60 | LOTV bloom (balanced) |
| 18 | Hydroxycitronellal | neat | 250 | petal brightness |
| 19 | Linalool | neat | 90 | transparent muguet air |
| 20 | Indole | 10% in DPG | 15 | floral depth |
| 21 | Ylang Ylang EO | neat | 50 | exotic richness |
| 22 | Benzyl Salicylate | neat | 280 | waxy floral cushion |
| 23 | Musk Ketone | 10% in DPG | 750 | clean soft base |
| 24 | Geranium EO | neat | 100 | natural geranium-rose bouquet complexity |
| 25 | Ethylene Brassylate | neat | -155 | musk-fixative volume (fill) |
| 26 | Ambrettolide | 10% in DPG | 30 | lift in the drydown |
| 27 | Cedarwood EO | neat | 250 | discreet wood frame |
| 28 | Vanillin | 10% in DPG | 50 | trace warmth |
| 29 | Linalool | neat | 5 | stabilizer |

**Total concentrate:** 6000 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Floral Bouquet - Quelques Fleurs Study - 30 mL EdP

## Gate Summary

**75 PASS** / **22 WARN** / **6 FAIL**

  FAIL pipeline_preflight: 9 checks; 3 warnings
  FAIL exact_subtotal: 6540.0 uL parsed; expected 6000.0 uL
  FAIL chemistry_stability: predicted maturation shelf life 7 days
  FAIL pipette_floor_neat_traces: Ethylene Brassylate=0.0uL below 5.0 uL neat floor
  FAIL safety_ifra_allergen: IFRA violations: Hydroxycitronellal 1.9667% > 1.0%; IFRA headroom 100% violations: Hydroxycitronellal 1.966667% > 1.0%; ℹ 6 EU fragrance all
  FAIL family_drift_detector: floral_bouquet.quelques_fleurs_reference; not_tuberose_white_floral: 18.372% active above 18.000
  WARN odt_coverage: 8 material(s) rely on derived/unverified ODTs (35% OAV share)
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 24.7% active mass across 5 materials
  WARN small_diluted_traces: Indole=15.0uL at 10.0%
  WARN dilution_accuracy: Check pipetting: aldehyde c10: 500.0uL at 1%; aldehyde c11: 450.0uL at 1%; aldehyde c12 mna: 400.0uL at 1%
  WARN eu_allergen_declaration: EU allergens requiring label: geraniol, citronellol, hydroxycitronellal, linalool, benzyl salicylate
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid off-target: Expected T:20% H:50% B:30%, Actual T:4.6% H:82.0% B:13.5%; top OAV off-target for family floral; heart OAV needs improve
  WARN carles_pyramid: Carles pyramid: empty windows = 24h+_base (need >2% active in each of 5 windows)
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:aldehyde c10 = 12:1; bergamot fcf sicilian:aldehyde c11 = 53:1; bergamot fcf sici
  WARN jnd_redundancy: Potentially redundant pairs: phenethyl alcohol vs citronellol in rose (OAV 137/153); phenethyl alcohol vs rose oxide in rose (OAV 137/122); 
  WARN guerlain_vanillin_coumarin: Vanillin present without coumarin — no structural counterweight
  WARN jellinek_psychology: Jellinek categories weak: erogenic, anti_erogenic
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: linalool OAV 3471.1 is above floral_jasmine target 10.0-25.0; hedione OAV 2108.7 is above floral_jasmine target 40.0-80.0; cis jasmone OAV 1
  WARN olfactory_fatigue: Olfactory fatigue risk: aldehyde c10=258 (limit 200)
  WARN evaporation_rate_balance: Pyramid imbalance: top = 5%, heart = 82%
  WARN tenacity_projection: VP<0.01Pa = 2% (<10%, weak longevity); VP<0.001Pa = 0% (<3%, may lack depth)
  WARN master_perfumer_gate: opening likely underbuilt; drydown likely underbuilt
  WARN robustness_perturbation: 50 fragile perturbation(s) across 50 checks; Bergamot FCF oil Sicilian up: safety failure under perturbation; IFRA headroom failure: Hydroxy
  WARN confidence_minimum: combined confidence 47.5; preflight science penalty 29.4


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Linalool                     |     3471.1 | top   |  very strong |  21.300 |    5.2067 |  0.001500 |  0.0950 |  2.22 | Linalool                      
|   2 | Bergamot FCF oil Sicilian    |     3200.2 | heart |  very strong |  40.000 |   19.2011 |  0.006000 |  0.2000 |  4.86 | Bergamot FCF oil Sicilian     
|   3 | Geraniol                     |     2302.1 | heart |  very strong |   4.000 |    0.0921 |  0.000040 |  0.0100 |  0.23 | Geraniol                      
|   4 | Hedione                      |     2108.7 | heart |  very strong |   0.089 |    0.1054 |  0.000050 |  0.6000 | 11.93 | Hedione                       
|   5 | Hedione HC                   |     2108.7 | heart |  very strong |   0.089 |    0.1054 |  0.000050 |  0.1500 | 11.93 | Hedione                       
|   6 | Nerol                        |      921.2 | top   |       strong |   2.000 |    0.4606 |  0.000500 |  0.1000 |  2.33 | Nerol                         
|   7 | Geranium EO                  |      377.1 | heart |       strong |   2.500 |    0.5656 |  0.001500 |  0.1000 |  2.29 | Geranium EO                   
|   8 | Aldehyde C10                 |      258.3 | top   |       strong |  10.000 |    0.1136 |  0.000440 |  0.0050 |  0.12 | Aldehyde C10                  
|   9 | Hydroxycitronellal           |      162.2 | heart |       strong |   2.000 |    2.4327 |  0.015000 |  0.5900 | 12.32 | Hydroxycitronellal            
|  10 | Citronellol                  |      153.4 | heart |       strong |   4.500 |    6.1362 |  0.040000 |  0.6000 | 13.81 | Citronellol                   
|  11 | Phenethyl Alcohol            |      137.1 | heart |       strong |  11.570 |   27.4239 |  0.200000 |  0.8152 | 24.01 | Phenethyl Alcohol             
|  12 | Cis Jasmone                  |      136.2 | heart |       strong |   1.333 |    0.0681 |  0.000500 |  0.0236 |  0.52 | Cis Jasmone                   
|  13 | Methyl Benzoate              |      125.2 | heart |       strong |  40.000 |    6.2617 |  0.050000 |  0.0600 |  1.59 | Methyl Benzoate               
|  14 | Rose Oxide                   |      122.0 | heart |       strong |   5.300 |    0.0610 |  0.000500 |  0.0050 |  0.12 | Rose Oxide                    
|  15 | Aldehyde C11                 |       61.0 | top   | moderate-strong |   5.000 |    0.0469 |  0.000770 |  0.0045 |  0.10 | Aldehyde C11                  
|  16 | Indole                       |       48.7 | heart |     moderate |   1.500 |    0.0068 |  0.000140 |  0.0015 |  0.05 | Indole                        
|  17 | Phenyl Ethyl Dimethyl Carbinol |       30.3 | heart |     moderate |   0.300 |    0.0908 |  0.003000 |  0.1400 |  3.07 | PEDMC                         
|  18 | Benzyl Acetate               |       10.4 | heart |     moderate |   0.220 |    0.2081 |  0.020000 |  0.4000 |  9.58 | Benzyl Acetate                
|  19 | Cedarwood EO                 |        7.2 | base  |  perceptible |   0.250 |    0.1086 |  0.015000 |  0.2500 |  4.40 | Cedarwood EO                  
|  20 | Ylang Ylang EO               |        4.4 | heart | at threshold |   0.050 |    0.0044 |  0.001000 |  0.0500 |  0.90 | Ylang Ylang EO                
|  21 | Aldehyde C12 MNA             |        2.1 | top   | at threshold |   3.000 |    0.0231 |  0.011000 |  0.0040 |  0.08 | Aldehyde C12 MNA              
|  22 | Benzyl Salicylate            |        1.5 | base  | at threshold |   0.030 |    0.0154 |  0.010000 |  0.2800 |  4.41 | Benzyl Salicylate             
|  23 | Vanillin                     |        0.3 | base  | sub-threshold |   0.200 |    0.0052 |  0.020000 |  0.0050 |  0.12 | Vanillin                      
|  24 | Musk Ketone                  |        0.1 | base  | sub-threshold |   0.003 |    0.0003 |  0.002000 |  0.0750 |  0.92 | Musk Ketone                   
|  25 | Ambrettolide                 |        0.1 | base  | sub-threshold |   0.003 |    0.0000 |  0.000136 |  0.0030 |  0.04 | Ambrettolide                  
|  26 | Ethylene Brassylate          |        0.0 | base  | sub-threshold |   0.008 |    0.0000 |  0.000970 |  0.0000 |  0.00 | Ethylene Brassylate           

**Materials:** 26 total (5 top, 15 heart, 6 base)
**Total vapor:** 68.74 ppm

### Note Distribution

**TOP:** 5 mats, 4.6% active, 29.9% OAV
  - Linalool                     OAV=  3471.1 (very strong) VP=21.300Pa
  - Nerol                        OAV=   921.2 (strong) VP=2.000Pa
  - Aldehyde C10                 OAV=   258.3 (strong) VP=10.000Pa
  - Aldehyde C11                 OAV=    61.0 (moderate-strong) VP=5.000Pa
  - Aldehyde C12 MNA             OAV=     2.1 (at threshold) VP=3.000Pa
**HEART:** 15 mats, 82.0% active, 70.0% OAV
  - Bergamot FCF oil Sicilian    OAV=  3200.2 (very strong) VP=40.000Pa
  - Geraniol                     OAV=  2302.1 (very strong) VP=4.000Pa
  - Hedione                      OAV=  2108.7 (very strong) VP=0.089Pa
  - Hedione HC                   OAV=  2108.7 (very strong) VP=0.089Pa
  - Geranium EO                  OAV=   377.1 (strong) VP=2.500Pa
  - Hydroxycitronellal           OAV=   162.2 (strong) VP=2.000Pa
  ... and 9 more
**BASE:** 6 mats, 13.5% active, 0.1% OAV
  - Cedarwood EO                 OAV=     7.2 (perceptible) VP=0.250Pa
  - Benzyl Salicylate            OAV=     1.5 (at threshold) VP=0.030Pa
  - Vanillin                     OAV=     0.3 (sub-threshold) VP=0.200Pa
  - Musk Ketone                  OAV=     0.1 (sub-threshold) VP=0.003Pa
  - Ambrettolide                 OAV=     0.1 (sub-threshold) VP=0.003Pa
  - Ethylene Brassylate          OAV=     0.0 (sub-threshold) VP=0.008Pa

### Sub-threshold Materials (OAV < 1)
4/26 materials below perceptible threshold
  - Musk Ketone: OAV=0.14 VP=0.003Pa act=75uL role=Musk Ketone [**Needs higher dose**]
  - Ethylene Brassylate: OAV=0.00 VP=0.008Pa act=0uL role=Ethylene Brassylate [Structural (acceptable)]
  - Ambrettolide: OAV=0.09 VP=0.003Pa act=3uL role=Ambrettolide [Structural (acceptable)]
  - Vanillin: OAV=0.26 VP=0.200Pa act=5uL role=Vanillin [Structural (acceptable)]

### OAV by Odor Family

           floral  37.0% ==================  (9 mats)
         aromatic  22.0% ===========  (1 mats)
           citrus  20.3% ==========  (1 mats)
             rose  17.2% ========  (4 mats)
        aldehydic   2.0% =  (3 mats)
           muguet   1.0% =  (1 mats)
          indolic   0.3% =  (1 mats)
            woody   0.0% =  (1 mats)
       salicylate   0.0% =  (1 mats)
         gourmand   0.0% =  (1 mats)
             musk   0.0% =  (3 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  4.6/82.0/13.5 |  68.74ppm |   6540 | Linalool(3471), Bergamot FCF(3200), Geraniol(2302)
| top          |    300s |  4.6/81.9/13.5 |  68.23ppm |   6677 | Linalool(3444), Bergamot FCF(3149), Geraniol(2306)
| heart        |   1800s |  4.5/81.8/13.7 |  65.76ppm |   6592 | Linalool(3308), Bergamot FCF(2903), Geraniol(2324)
| late_heart   |   7200s |  4.3/81.4/14.4 |  57.92ppm |   6315 | Linalool(2848), Geraniol(2377), Hedione(2279)
| drydown      |  14400s |  4.0/80.9/15.1 |  49.59ppm |   6003 | Hedione(2433), Hedione HC(2433), Geraniol(2425)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:4.6% H:82.0% B:13.5%  Vapor:68.74ppm
  Leaders: Linalool OAV 3471 | Bergamot FCF oil Sicilian OAV 3200 | Geraniol OAV 2302 | Hedione OAV 2109 | Hedione HC OAV 2109

**TOP** (300.0s) — Evap:-2%
  T:4.6% H:81.9% B:13.5%  Vapor:68.23ppm
  Leaders: Linalool OAV 3444 | Bergamot FCF oil Sicilian OAV 3149 | Geraniol OAV 2306 | Hedione OAV 2116 | Hedione HC OAV 2116

**HEART** (1800.0s) — Evap:-1%
  T:4.5% H:81.8% B:13.7%  Vapor:65.76ppm
  Leaders: Linalool OAV 3308 | Bergamot FCF oil Sicilian OAV 2903 | Geraniol OAV 2324 | Hedione OAV 2153 | Hedione HC OAV 2153

**LATE_HEART** (7200.0s) — Evap:3%
  T:4.3% H:81.4% B:14.4%  Vapor:57.92ppm
  Leaders: Linalool OAV 2848 | Geraniol OAV 2377 | Hedione OAV 2279 | Hedione HC OAV 2279 | Bergamot FCF oil Sicilian OAV 2155

**DRYDOWN** (14400.0s) — Evap:8%
  T:4.0% H:80.9% B:15.1%  Vapor:49.59ppm
  Leaders: Hedione OAV 2433 | Hedione HC OAV 2433 | Geraniol OAV 2425 | Linalool OAV 2310 | Bergamot FCF oil Sicilian OAV 1435

## Perfumer's Assessment

### 1. Character
  Top: Linalool(very strong) + Nerol(strong) + Aldehyde C10(strong)
  Heart: Bergamot FCF oil Sicilian(very strong) + Geraniol(very strong)
  Base: Cedarwood EO(perceptible) + Benzyl Salicylate(at threshold) + Vanillin(sub-threshold) + Musk Ketone(sub-threshold) + Ambrettolide(sub-threshold)

### 2. Opening (0-5min)
  Linalool dominates at OAV 3471 (very strong).
  - Linalool OAV=3471 VP=21.3Pa (aromatic)
  - Nerol OAV=921 VP=2.0Pa (floral)
  - Aldehyde C10 OAV=258 VP=10.0Pa (aldehydic)
  - Aldehyde C11 OAV=61 VP=5.0Pa (aldehydic)
  Total vapor: 68.7 ppm

### 3. Heart (30min-2hr)
  Linalool OAV=3308 (very strong)
  Bergamot FCF oil Sicilian OAV=2903 (very strong)
  Geraniol OAV=2324 (very strong)
  Hedione OAV=2153 (very strong)
  T:4.5% H:81.8% B:13.7%
  Vapor: 65.8 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 15% of headspace
  - Hedione OAV=2433
  - Hedione HC OAV=2433
  - Geraniol OAV=2425
  - Linalool OAV=2310
  - Bergamot FCF oil Sicilian OAV=1435
  - Nerol OAV=1017
  Vapor: 49.6 ppm

### 5. Sillage & Diffusion
  Primary carriers: Linalool(3471) + Bergamot FCF oil Sicilian(3200) + Geraniol(2302) + Hedione(2109)
  OAV by family: floral37% aromatic22% citrus20% rose17%

### 6. Longevity
  Evaporation: 8% over 4h
  Vapor: 68.7 > 49.6 ppm
  Base @ drydown: 15%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:4.6% H:82.0% B:13.5%
  OAV range: 0.09 to 3471 (sigma-log=1.36)
  Wide contrast: citrus (OAV 3471) dominates opening before burning off to reveal base.
    sub-threshold: 3

### 8. Flags
  SUB: Vanillin OAV=0.26 role=Vanillin
  SUB: Musk Ketone OAV=0.14 role=Musk Ketone
  SUB: Ambrettolide OAV=0.09 role=Ambrettolide
  SUB: Ethylene Brassylate OAV=0.00 role=Ethylene Brassylate


## Structural OAV Analysis

**Vapor:** 69 ppm  |  **Active:** 15.2%  |  **Perceptible:** 22/26

### OAV Tiers
  **massive** (5): Bergamot FCF oil Sicilian(3200), Geraniol(2302), Hedione(2109), Hedione HC(2109), Linalool(3471)
  **v.strong** (9): Aldehyde C10(258), Phenethyl Alcohol(137), Citronellol(153), Nerol(921), Rose Oxide(122), Methyl Benzoate(125), Cis Jasmone(136), Hydroxycitronellal(162), Geranium EO(377)
  **strong** (1): Aldehyde C11(61)
  **moderate** (3): Phenyl Ethyl Dimethyl Carbinol(30), Benzyl Acetate(10), Indole(49)
  **perceptible** (1): Cedarwood EO(7)
  **threshold** (3): Aldehyde C12 MNA(2), Ylang Ylang EO(4), Benzyl Salicylate(2)
  **sub** (4): Musk Ketone(0), Ethylene Brassylate(0), Ambrettolide(0), Vanillin(0)

### Block Balance
  **Citrus**     3200 (20%)
  **Floral**    12549 (80%)
  **Base**          0 (0%)
  **Ratio:** 134745:1 between strongest/weakest block

### Issues
  ! 4 sub-threshold material(s): Musk Ketone, Ethylene Brassylate, Ambrettolide, Vanillin
```
