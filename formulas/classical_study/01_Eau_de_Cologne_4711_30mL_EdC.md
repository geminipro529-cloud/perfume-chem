# Eau de Cologne — 4711 Study — 30 mL EdC

**Historical reference:** 4711 Original Eau de Cologne  
**Family archetype:** `citrus_classical.4711_reference`  
**Concentration:** 5.7% EdC · 1,700 µL concentrate in 30 mL  
**Historical gap:** True `Neroli EO` is absent and `Petitgrain EO` is depleted, so `Aurantiol`, `Nerol`, `Oranger Crystals`, and `Nerolin Bromelia` rebuild the orange-flower/petitgrain register.  
**Why this structure matters:** This is the canonical cologne skeleton: citrus flood, aromatic-herbal bridge, light orange-flower heart, and almost no substantive base.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 420 | primary sparkling cologne citrus |
| 2 | Lemon FCF oil Sicilian | neat | 260 | lemon brightness |
| 3 | Orange Peel EO | neat | 240 | sweet orange body |
| 4 | Cedrat FCF oil Sicilian | neat | 120 | bitter citron edge |
| 5 | Lavender EO | neat | 110 | classical aromatic bridge |
| 6 | Rosemary EO | neat | 40 | herbal backbone |
| 7 | Linalool | neat | 70 | citrus-floral air |
| 8 | Nerol | neat | 80 | orange-flower/rose bridge |
| 9 | Aurantiol | neat | 110 | orange blossom heart |
| 10 | Oranger Crystals | 10% in DPG | 120 | neroli sparkle substitute |
| 11 | Nerolin Bromelia | 10% in DPG | 80 | naphthyl orange-flower depth |
| 12 | Ethylene Brassylate | neat | 1650 | minimal persistence cushion |
| 13 | Musk Ketone | 10% in DPG | 300 | soft drydown padding |

**Total concentrate:** 3600 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Eau de Cologne — 4711 Study — 30 mL EdC

## Gate Summary

**79 PASS** / **20 WARN** / **4 FAIL**

  FAIL exact_subtotal: 3600.0 uL parsed; expected 1800.0 uL
  FAIL family_drift_detector: citrus_classical.4711_reference; hesperidic_mass: 15.000% active below 20.000
  FAIL coty_single_material_limit: ethylene brassylate = 46% of concentrate (>40% Coty limit)
  FAIL roudnitska_transparence: Transparency ratio 16% — too opaque, no lift (Roudnitska aesthetic)
  WARN pipeline_preflight: 9 checks; 3 warnings
  WARN odt_coverage: 10 material(s) rely on derived/unverified ODTs (77% OAV share)
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 2.2% active mass across 1 materials
  WARN safety_ifra_allergen: 8 materials lack explicit IFRA Cat4 limits; 1 EU allergen declarations
  WARN eu_allergen_declaration: EU allergens requiring label: linalool
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid needs improvement: Expected T:30% H:35% B:35%, Actual T:24.4% H:22.2% B:53.3%; top OAV off-target for family citrus; heart OAV off-t
  WARN carles_pyramid: Carles pyramid: empty windows = 6h_heart, 12h_heart_base (need >2% active in each of 5 windows)
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:lemon fcf oil sicilian = 40:1; bergamot fcf sicilian:orange peel eo = 57:1; berga
  WARN stevens_n_efficiency: Inefficient materials: ethylene brassylate: 46% raw -> 1% perceived
  WARN jnd_redundancy: Potentially redundant pairs: lavender eo vs linalool in aromatic (OAV 4532/4575)
  WARN jellinek_psychology: Jellinek categories weak: erogenic, narcotic, anti_erogenic
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: linalool OAV 4575.1 is above citrus target 50.0-120.0; diffusion_layers: Missing intimate layer — fragrance will feel hollow up close; mater
  WARN olfactory_fatigue: Olfactory fatigue risk: hedione=0.0% of concentrate (<10% minimum for radiance)
  WARN tenacity_projection: VP<0.001Pa = 0% (<3%, may lack depth)
  WARN master_perfumer_gate: Ethylene Brassylate dominates active formula at 52.4%
  WARN confidence_minimum: combined confidence 48.1; preflight science penalty 31.4


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Bergamot FCF oil Sicilian    |    12026.7 | heart |      massive |  40.000 |   72.1605 |  0.006000 |  0.4200 | 18.28 | Bergamot FCF oil Sicilian     
|   2 | Linalool                     |     4575.1 | top   |  very strong |  21.300 |    6.8626 |  0.001500 |  0.0700 |  2.92 | Linalool                      
|   3 | Lavender EO                  |     4531.9 | heart |  very strong |  20.000 |    9.0638 |  0.002000 |  0.1100 |  4.59 | Lavender EO                   
|   4 | Cedrat FCF oil Sicilian      |     2195.7 | top   |  very strong |  35.000 |   17.5654 |  0.008000 |  0.1200 |  5.08 | Cedrat FCF Sicilian           
|   5 | Nerol                        |     1318.8 | top   |  very strong |   2.000 |    0.6594 |  0.000500 |  0.0800 |  3.34 | Nerol                         
|   6 | Rosemary EO                  |      381.4 | heart |       strong |  18.000 |    2.6697 |  0.007000 |  0.0360 |  1.50 |                               
|   7 | Lemon FCF oil Sicilian       |      303.8 | top   |       strong |   2.500 |    2.4306 |  0.008000 |  0.2600 |  9.85 | Lemon FCF oil Sicilian        
|   8 | Orange Peel EO               |      212.8 | top   |       strong |   1.900 |    2.1279 |  0.010000 |  0.2400 | 11.35 | Orange Peel EO                
|   9 | Ethylene Brassylate          |       32.0 | base  |     moderate |   0.008 |    0.0310 |  0.000970 |  1.6500 | 39.30 | Ethylene Brassylate           
|  10 | Nerolin Bromelia             |        4.9 | heart | at threshold |   0.500 |    0.0148 |  0.003000 |  0.0080 |  0.30 | Nerolin Bromelia              
|  11 | Aurantiol                    |        4.1 | heart | at threshold |   0.533 |    0.1220 |  0.030000 |  0.1100 |  2.32 | Aurantiol                     
|  12 | Musk Ketone                  |        0.1 | base  | sub-threshold |   0.003 |    0.0002 |  0.002000 |  0.0300 |  0.66 | Musk Ketone                   
|  13 | Oranger Crystals             |        0.1 | heart | sub-threshold |   0.120 |    0.0060 |  0.100000 |  0.0134 |  0.51 | Oranger Crystals              

**Materials:** 13 total (5 top, 6 heart, 2 base)
**Total vapor:** 113.71 ppm

### Note Distribution

**TOP:** 5 mats, 24.4% active, 33.6% OAV
  - Linalool                     OAV=  4575.1 (very strong) VP=21.300Pa
  - Cedrat FCF oil Sicilian      OAV=  2195.7 (very strong) VP=35.000Pa
  - Nerol                        OAV=  1318.8 (very strong) VP=2.000Pa
  - Lemon FCF oil Sicilian       OAV=   303.8 (strong) VP=2.500Pa
  - Orange Peel EO               OAV=   212.8 (strong) VP=1.900Pa
**HEART:** 6 mats, 22.2% active, 66.2% OAV
  - Bergamot FCF oil Sicilian    OAV= 12026.7 (massive) VP=40.000Pa
  - Lavender EO                  OAV=  4531.9 (very strong) VP=20.000Pa
  - Rosemary EO                  OAV=   381.4 (strong) VP=18.000Pa
  - Nerolin Bromelia             OAV=     4.9 (at threshold) VP=0.500Pa
  - Aurantiol                    OAV=     4.1 (at threshold) VP=0.533Pa
  - Oranger Crystals             OAV=     0.1 (sub-threshold) VP=0.120Pa
**BASE:** 2 mats, 53.3% active, 0.1% OAV
  - Ethylene Brassylate          OAV=    32.0 (moderate) VP=0.008Pa
  - Musk Ketone                  OAV=     0.1 (sub-threshold) VP=0.003Pa

### Sub-threshold Materials (OAV < 1)
2/13 materials below perceptible threshold
  - Oranger Crystals: OAV=0.06 VP=0.120Pa act=12uL role=Oranger Crystals [Structural (acceptable)]
  - Musk Ketone: OAV=0.10 VP=0.003Pa act=30uL role=Musk Ketone [**Needs higher dose**]
### High-OAV Flags (>5000)
  - Bergamot FCF oil Sicilian OAV=12027 dominates headspace — may mask subtler notes

### OAV by Odor Family

           citrus  57.6% ============================  (4 mats)
         aromatic  35.6% =================  (2 mats)
           floral   5.2% ==  (4 mats)
                ?   1.5% =  (1 mats)
             musk   0.1% =  (2 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s | 24.4/22.2/53.3 | 113.71ppm |   3600 | Bergamot FCF(12027), Linalool(4575), Lavender EO(4532)
| top          |    300s | 24.4/22.0/53.6 | 112.44ppm |   3587 | Bergamot FCF(11858), Linalool(4548), Lavender EO(4514)
| heart        |   1800s | 24.4/21.0/54.6 | 106.24ppm |   3525 | Bergamot FCF(11040), Lavender EO(4419), Linalool(4412)
| late_heart   |   7200s | 24.2/17.7/58.1 |  86.04ppm |   3338 | Bergamot FCF(8431), Lavender EO(4046), Linalool(3908)
| drydown      |  14400s | 23.8/14.3/61.9 |  64.33ppm |   3161 | Bergamot FCF(5739), Lavender EO(3506), Linalool(3242)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:24.4% H:22.2% B:53.3%  Vapor:113.71ppm
  Leaders: Bergamot FCF oil Sicilian OAV 12027 | Linalool OAV 4575 | Lavender EO OAV 4532 | Cedrat FCF oil Sicilian OAV 2196 | Nerol OAV 1319

**TOP** (300.0s) — Evap:0%
  T:24.4% H:22.0% B:53.6%  Vapor:112.44ppm
  Leaders: Bergamot FCF oil Sicilian OAV 11858 | Linalool OAV 4548 | Lavender EO OAV 4514 | Cedrat FCF oil Sicilian OAV 2171 | Nerol OAV 1325

**HEART** (1800.0s) — Evap:2%
  T:24.4% H:21.0% B:54.6%  Vapor:106.24ppm
  Leaders: Bergamot FCF oil Sicilian OAV 11040 | Lavender EO OAV 4419 | Linalool OAV 4412 | Cedrat FCF oil Sicilian OAV 2048 | Nerol OAV 1355

**LATE_HEART** (7200.0s) — Evap:7%
  T:24.2% H:17.7% B:58.1%  Vapor:86.04ppm
  Leaders: Bergamot FCF oil Sicilian OAV 8431 | Lavender EO OAV 4046 | Linalool OAV 3908 | Cedrat FCF oil Sicilian OAV 1642 | Nerol OAV 1450

**DRYDOWN** (14400.0s) — Evap:12%
  T:23.8% H:14.3% B:61.9%  Vapor:64.33ppm
  Leaders: Bergamot FCF oil Sicilian OAV 5739 | Lavender EO OAV 3506 | Linalool OAV 3242 | Nerol OAV 1549 | Cedrat FCF oil Sicilian OAV 1192

## Perfumer's Assessment

### 1. Character
  Top: Linalool(very strong) + Cedrat FCF oil Sicilian(very strong) + Nerol(very strong)
  Heart: Bergamot FCF oil Sicilian(massive) + Lavender EO(very strong)
  Base: Ethylene Brassylate(moderate) + Musk Ketone(sub-threshold)

### 2. Opening (0-5min)
  Linalool dominates at OAV 4575 (very strong).
  - Linalool OAV=4575 VP=21.3Pa (aromatic)
  - Cedrat FCF oil Sicilian OAV=2196 VP=35.0Pa (citrus)
  - Nerol OAV=1319 VP=2.0Pa (floral)
  - Lemon FCF oil Sicilian OAV=304 VP=2.5Pa (citrus)
  Total vapor: 113.7 ppm

### 3. Heart (30min-2hr)
  Bergamot FCF oil Sicilian OAV=11040 (massive)
  Lavender EO OAV=4419 (very strong)
  Linalool OAV=4412 (very strong)
  Cedrat FCF oil Sicilian OAV=2048 (very strong)
  T:24.4% H:21.0% B:54.6%
  Vapor: 106.2 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 62% of headspace
  - Bergamot FCF oil Sicilian OAV=5739
  - Lavender EO OAV=3506
  - Linalool OAV=3242
  - Nerol OAV=1549
  - Cedrat FCF oil Sicilian OAV=1192
  - Lemon FCF oil Sicilian OAV=354
  Vapor: 64.3 ppm

### 5. Sillage & Diffusion
  Primary carriers: Bergamot FCF oil Sicilian(12027) + Linalool(4575) + Lavender EO(4532) + Cedrat FCF oil Sicilian(2196)
  OAV by family: citrus58% aromatic36% floral5% None1%

### 6. Longevity
  Evaporation: 12% over 4h
  Vapor: 113.7 > 64.3 ppm
  Base @ drydown: 62%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:24.4% H:22.2% B:53.3%
  OAV range: 0.06 to 12027 (sigma-log=1.75)
  Wide contrast: citrus (OAV 12027) dominates opening before burning off to reveal base.
    massive: 1
    sub-threshold: 2

### 8. Flags
  SUB: Musk Ketone OAV=0.10 role=Musk Ketone
  SUB: Oranger Crystals OAV=0.06 role=Oranger Crystals


## Structural OAV Analysis

**Vapor:** 114 ppm  |  **Active:** 10.5%  |  **Perceptible:** 11/13

### OAV Tiers
  **massive** (5): Bergamot FCF oil Sicilian(12027), Cedrat FCF oil Sicilian(2196), Lavender EO(4532), Linalool(4575), Nerol(1319)  ! fatigue risk
  **v.strong** (3): Lemon FCF oil Sicilian(304), Orange Peel EO(213), Rosemary EO(381)
  **moderate** (1): Ethylene Brassylate(32)
  **threshold** (2): Aurantiol(4), Nerolin Bromelia(5)
  **sub** (2): Oranger Crystals(0), Musk Ketone(0)

### Block Balance
  **Citrus**    12543 (49%)
  **Floral**    13012 (51%)
  **Base**         32 (0%)
  **Ratio:** 407:1 between strongest/weakest block

### Issues
  ! 2 sub-threshold material(s): Oranger Crystals, Musk Ketone
  ! Missing 'strong' tier (OAV 50-100)
```
