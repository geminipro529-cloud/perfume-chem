# Powdery Floral — Après l'Ondée Study — 30 mL EdP

**Historical reference:** Guerlain Après l'Ondée  
**Family archetype:** `floral_powdery.apres_londee_reference`  
**Concentration:** 20.0% EdP · 6,000 µL concentrate in 30 mL  
**Historical gap:** There is no heliotropin stock, no real orris butter, and no pre-diluted musk ketone solution. The powder lesson is taught with `Heliotropal`, ionones, `Alpha Irone`, salicylates, vanilla-tonka materials, and a restrained modern musk bed.  
**Why this structure matters:** Powdery floral is about evaporation after rain: violet-iris facets, heliotrope-almond softness, and a blur rather than a crisp bouquet.

## Formula

| # | Material | Dilution | µL | Role |
|--:|---|---|---:|---|
| 1 | Bergamot FCF oil Sicilian | neat | 180 | opening relief (light) |
| 2 | Aldehyde C10 | 1% in DPG | 40 | lift |
| 3 | Aldehyde C11 | 1% in DPG | 40 | soft waxy air |
| 4 | Vanillin | 20% in DPG | 430 | main heliotrope-powder effect |
| 5 | Anisaldehyde | neat | 150 | almond-anise powder richness |
| 6 | Coumarin | 20% in DPG | 360 | tonka-hay warmth |
| 7 | Vanillin | 10% in DPG | 370 | soft vanilla powder |
| 8 | Ethyl Vanillin | 10% in DPG | 80 | stronger vanilla contour |
| 9 | Alpha Ionone | neat | 440 | iris-violet core |
| 10 | Alpha Ionone | neat | 220 | floral-violet powder (increased) |
| 11 | Beta Ionone | 10% in DPG | 20 | cooler violet transparency (OAV balanced) |
| 12 | Alpha Irone | 30% in DEP | 280 | orris-like depth (increased) |
| 13 | Irotyl | neat | 200 | iris texture |
| 14 | Phenethyl Alcohol | neat | 460 | floral body under the powder |
| 15 | Ylang Ylang EO | neat | 30 | trace cosmetic richness |
| 16 | Benzyl Salicylate | neat | 500 | waxy petal cushion |
| 17 | Benzyl Benzoate | neat | 330 | fixative density |
| 18 | Musk Ketone | 10% in DPG | 2250 | powder-clean base |
| 19 | Ethylene Brassylate | neat | 775 | soft musky persistence (fill) |
| 20 | Ambrettolide | 10% in DPG | 30 | airy diffusion |
| 21 | Cedarwood EO | neat | 100 | slight woody frame (reduced) |
| 22 | Linalool | neat | 5 | stabilizer |

**Total concentrate:** 6000 uL  
Top with ethanol 96% to 30 mL.

## Pipeline Analysis

```text
# Powdery Floral — Après l'Ondée Study — 30 mL EdP

## Gate Summary

**77 PASS** / **21 WARN** / **5 FAIL**

  FAIL exact_subtotal: 7290.0 uL parsed; expected 6000.0 uL
  FAIL chemistry_stability: predicted maturation shelf life 7 days
  FAIL safety_ifra_allergen: IFRA violations: Alpha Ionone 2.2% > 1.85%; IFRA headroom 100% violations: Alpha Ionone 2.2% > 1.85%; ℹ 6 EU fragrance allergen(s) require l
  FAIL family_drift_detector: floral_powdery.apres_londee_reference; not_white_floral: 7.270% active above 3.000
  FAIL roudnitska_transparence: Transparency ratio 18% — too opaque, no lift (Roudnitska aesthetic)
  WARN pipeline_preflight: 9 checks; 4 warnings
  WARN odt_coverage: 7 material(s) rely on derived/unverified ODTs (34% OAV share)
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 17.0% active mass across 4 materials
  WARN eu_allergen_declaration: EU allergens requiring label: coumarin, benzyl salicylate, linalool
  WARN perfumer_logic: generic; perfumer_logic_brief: No brief-specific logic selected.
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid off-target: Expected T:20% H:50% B:30%, Actual T:0.2% H:43.5% B:56.3%; top OAV off-target for family floral; heart OAV off-target fo
  WARN carles_accord_ratio: Extreme ratios (>8:1, Carles limit): bergamot fcf sicilian:aldehyde c10 = 139:1; bergamot fcf sicilian:aldehyde c11 = 532:1; bergamot fcf si
  WARN stevens_n_efficiency: Inefficient materials: musk ketone: 31% raw -> 0% perceived
  WARN jnd_redundancy: Potentially redundant pairs: vanillin vs anisaldehyde in gourmand (OAV 5/5)
  WARN jellinek_psychology: Jellinek categories weak: erogenic, narcotic, stimulating, anti_erogenic
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 98%) — collapse risk
  WARN oav_intelligence: linalool OAV 254.7 is above floral_jasmine target 10.0-25.0; ambrettolide OAV 0.1 is below floral_jasmine target 5.0-10.0; benzyl benzoate O
  WARN olfactory_fatigue: Olfactory fatigue risk: alpha ionone=6362 (limit 2000); hedione=0.0% of concentrate (<10% minimum for radiance)
  WARN evaporation_rate_balance: Pyramid imbalance: top = 0%
  WARN tenacity_projection: VP<0.001Pa = 0% (<3%, may lack depth)
  WARN master_perfumer_gate: opening likely underbuilt
  WARN mass_market_tier_check: Expensive captives found: Alpha Irone. At 1500 THB, these eat margin. Consider if their perceptible impact justifies the cost.; Estimated ma
  WARN robustness_perturbation: 39 fragile perturbation(s) across 39 checks; Bergamot FCF oil Sicilian up: safety failure under perturbation; IFRA headroom failure: Alpha I
  WARN confidence_minimum: combined confidence 48.5; preflight science penalty 27.4


## Headspace OAV — Opening (0s)

| # | Material | OAV | Note | Percept | VP Pa | Vapor ppm | ODT ppm | Act g | MF% | Role |
|---|--------|---|----|-------|-----|---------|-------|-----|---|----|
|   1 | Alpha Ionone                 |     6361.7 | heart |  very strong |   1.500 |    2.5447 |  0.000400 |  0.6600 | 17.07 | Alpha Ionone                  
|   2 | Bergamot FCF oil Sicilian    |     4007.7 | heart |  very strong |  40.000 |   24.0463 |  0.006000 |  0.1800 |  6.05 | Bergamot FCF oil Sicilian     
|   3 | Beta Ionone                  |      881.3 | heart |       strong |   1.200 |    0.0062 |  0.000007 |  0.0020 |  0.05 | Beta Ionone                   
|   4 | Linalool                     |      254.7 | top   |       strong |  21.300 |    0.3820 |  0.001500 |  0.0050 |  0.16 | Linalool                      
|   5 | Coumarin                     |      239.1 | base  |       strong |   0.500 |    0.1673 |  0.000700 |  0.0720 |  2.45 | Coumarin                      
|   6 | Phenethyl Alcohol            |      109.7 | heart |       strong |  11.570 |   21.9421 |  0.200000 |  0.4687 | 19.08 | Phenethyl Alcohol             
|   7 | Alpha Irone                  |       67.1 | base  | moderate-strong |   0.300 |    0.0604 |  0.000900 |  0.0840 |  2.03 | Alpha Irone                   
|   8 | Aldehyde C10                 |       28.7 | top   |     moderate |  10.000 |    0.0126 |  0.000440 |  0.0004 |  0.01 | Aldehyde C10                  
|   9 | Ethylene Brassylate          |       11.7 | base  |     moderate |   0.008 |    0.0113 |  0.000970 |  0.7750 | 14.26 | Ethylene Brassylate           
|  10 | Aldehyde C11                 |        7.5 | top   |  perceptible |   5.000 |    0.0058 |  0.000770 |  0.0004 |  0.01 | Aldehyde C11                  
|  11 | Anisaldehyde                 |        5.4 | heart |  perceptible |   0.050 |    0.0272 |  0.005000 |  0.1500 |  5.48 | Anisaldehyde                  
|  12 | Vanillin                     |        5.2 | base  |  perceptible |   0.200 |    0.1040 |  0.020000 |  0.0800 |  2.61 | Vanillin                      
|  13 | Cedarwood EO                 |        4.0 | base  | at threshold |   0.250 |    0.0605 |  0.015000 |  0.1000 |  2.43 | Cedarwood EO                  
|  14 | Ylang Ylang EO               |        3.7 | heart | at threshold |   0.050 |    0.0037 |  0.001000 |  0.0300 |  0.75 | Ylang Ylang EO                
|  15 | Benzyl Salicylate            |        3.6 | base  | at threshold |   0.030 |    0.0360 |  0.010000 |  0.5000 | 10.89 | Benzyl Salicylate             
|  16 | Irotyl                       |        2.4 | heart | at threshold |   0.005 |    0.0024 |  0.001000 |  0.2000 |  4.82 | Irotyl                        
|  17 | Ethyl Vanillin               |        0.6 | base  | sub-threshold |   0.150 |    0.0036 |  0.006000 |  0.0080 |  0.24 | Ethyl Vanillin                
|  18 | Musk Ketone                  |        0.6 | base  | sub-threshold |   0.003 |    0.0011 |  0.002000 |  0.2250 |  3.80 | Musk Ketone                   
|  19 | Ambrettolide                 |        0.1 | base  | sub-threshold |   0.003 |    0.0000 |  0.000136 |  0.0030 |  0.06 | Ambrettolide                  
|  20 | Benzyl Benzoate              |        0.0 | base  | sub-threshold |   0.001 |    0.0008 |  0.810000 |  0.3300 |  7.74 | Benzyl Benzoate               

**Materials:** 20 total (3 top, 7 heart, 10 base)
**Total vapor:** 49.42 ppm

### Note Distribution

**TOP:** 3 mats, 0.2% active, 2.4% OAV
  - Linalool                     OAV=   254.7 (strong) VP=21.300Pa
  - Aldehyde C10                 OAV=    28.7 (moderate) VP=10.000Pa
  - Aldehyde C11                 OAV=     7.5 (perceptible) VP=5.000Pa
**HEART:** 7 mats, 43.5% active, 94.8% OAV
  - Alpha Ionone                 OAV=  6361.7 (very strong) VP=1.500Pa
  - Bergamot FCF oil Sicilian    OAV=  4007.7 (very strong) VP=40.000Pa
  - Beta Ionone                  OAV=   881.3 (strong) VP=1.200Pa
  - Phenethyl Alcohol            OAV=   109.7 (strong) VP=11.570Pa
  - Anisaldehyde                 OAV=     5.4 (perceptible) VP=0.050Pa
  - Ylang Ylang EO               OAV=     3.7 (at threshold) VP=0.050Pa
  ... and 1 more
**BASE:** 10 mats, 56.3% active, 2.8% OAV
  - Coumarin                     OAV=   239.1 (strong) VP=0.500Pa
  - Alpha Irone                  OAV=    67.1 (moderate-strong) VP=0.300Pa
  - Ethylene Brassylate          OAV=    11.7 (moderate) VP=0.008Pa
  - Vanillin                     OAV=     5.2 (perceptible) VP=0.200Pa
  - Cedarwood EO                 OAV=     4.0 (at threshold) VP=0.250Pa
  - Benzyl Salicylate            OAV=     3.6 (at threshold) VP=0.030Pa
  ... and 4 more

### Sub-threshold Materials (OAV < 1)
4/20 materials below perceptible threshold
  - Ethyl Vanillin: OAV=0.59 VP=0.150Pa act=8uL role=Ethyl Vanillin [Structural (acceptable)]
  - Benzyl Benzoate: OAV=0.00 VP=0.001Pa act=330uL role=Benzyl Benzoate [Structural (acceptable)]
  - Musk Ketone: OAV=0.57 VP=0.003Pa act=225uL role=Musk Ketone [**Needs higher dose**]
  - Ambrettolide: OAV=0.13 VP=0.003Pa act=3uL role=Ambrettolide [Structural (acceptable)]
### High-OAV Flags (>5000)
  - Alpha Ionone OAV=6362 dominates headspace — may mask subtler notes

### OAV by Odor Family

           floral  53.1% ==========================  (2 mats)
           citrus  33.4% ================  (1 mats)
            woody   7.4% ===  (2 mats)
         aromatic   2.1% =  (1 mats)
         gourmand   2.1% =  (4 mats)
             rose   0.9% =  (1 mats)
             iris   0.6% =  (2 mats)
        aldehydic   0.3% =  (2 mats)
             musk   0.1% =  (3 mats)
       salicylate   0.0% =  (1 mats)
         fixative   0.0% =  (1 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Raw uL | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  0.2/43.5/56.3 |  49.42ppm |   7290 | Alpha Ionone(6362), Bergamot FCF(4008), Beta Ionone(881)
| top          |    300s |  0.1/43.4/56.4 |  48.93ppm |   7282 | Alpha Ionone(6374), Bergamot FCF(3939), Beta Ionone(883)
| heart        |   1800s |  0.1/42.9/56.9 |  46.55ppm |   7246 | Alpha Ionone(6432), Bergamot FCF(3611), Beta Ionone(892)
| late_heart   |   7200s |  0.1/41.4/58.5 |  39.17ppm |   7130 | Alpha Ionone(6616), Bergamot FCF(2628), Beta Ionone(919)
| drydown      |  14400s |  0.1/39.6/60.3 |  31.63ppm |   7007 | Alpha Ionone(6807), Bergamot FCF(1705), Beta Ionone(949)

### Per-Window Detail

**OPENING** (0.0s) — Evap:0%
  T:0.2% H:43.5% B:56.3%  Vapor:49.42ppm
  Leaders: Alpha Ionone OAV 6362 | Bergamot FCF oil Sicilian OAV 4008 | Beta Ionone OAV 881 | Linalool OAV 255 | Coumarin OAV 239

**TOP** (300.0s) — Evap:0%
  T:0.1% H:43.4% B:56.4%  Vapor:48.93ppm
  Leaders: Alpha Ionone OAV 6374 | Bergamot FCF oil Sicilian OAV 3939 | Beta Ionone OAV 883 | Linalool OAV 252 | Coumarin OAV 240

**HEART** (1800.0s) — Evap:1%
  T:0.1% H:42.9% B:56.9%  Vapor:46.55ppm
  Leaders: Alpha Ionone OAV 6432 | Bergamot FCF oil Sicilian OAV 3611 | Beta Ionone OAV 892 | Coumarin OAV 242 | Linalool OAV 241

**LATE_HEART** (7200.0s) — Evap:2%
  T:0.1% H:41.4% B:58.5%  Vapor:39.17ppm
  Leaders: Alpha Ionone OAV 6616 | Bergamot FCF oil Sicilian OAV 2628 | Beta Ionone OAV 919 | Coumarin OAV 250 | Linalool OAV 204

**DRYDOWN** (14400.0s) — Evap:4%
  T:0.1% H:39.6% B:60.3%  Vapor:31.63ppm
  Leaders: Alpha Ionone OAV 6807 | Bergamot FCF oil Sicilian OAV 1705 | Beta Ionone OAV 949 | Coumarin OAV 260 | Linalool OAV 161

## Perfumer's Assessment

### 1. Character
  Top: Linalool(strong) + Aldehyde C10(moderate) + Aldehyde C11(perceptible)
  Heart: Alpha Ionone(very strong) + Bergamot FCF oil Sicilian(very strong)
  Base: Coumarin(strong) + Alpha Irone(moderate-strong) + Ethylene Brassylate(moderate) + Vanillin(perceptible) + Cedarwood EO(at threshold)

### 2. Opening (0-5min)
  Linalool dominates at OAV 255 (strong).
  - Linalool OAV=255 VP=21.3Pa (aromatic)
  - Aldehyde C10 OAV=29 VP=10.0Pa (aldehydic)
  - Aldehyde C11 OAV=8 VP=5.0Pa (aldehydic)
  Total vapor: 49.4 ppm

### 3. Heart (30min-2hr)
  Alpha Ionone OAV=6432 (very strong)
  Bergamot FCF oil Sicilian OAV=3611 (very strong)
  Beta Ionone OAV=892 (strong)
  Coumarin OAV=242 (strong)
  T:0.1% H:42.9% B:56.9%
  Vapor: 46.6 ppm

### 4. Drydown (2hr-4hr+)
  Base dominates at 60% of headspace
  - Alpha Ionone OAV=6807
  - Bergamot FCF oil Sicilian OAV=1705
  - Beta Ionone OAV=949
  - Coumarin OAV=260
  - Linalool OAV=161
  - Phenethyl Alcohol OAV=89
  Vapor: 31.6 ppm

### 5. Sillage & Diffusion
  Primary carriers: Alpha Ionone(6362) + Bergamot FCF oil Sicilian(4008) + Beta Ionone(881)
  OAV by family: floral53% citrus33% woody7% aromatic2%

### 6. Longevity
  Evaporation: 4% over 4h
  Vapor: 49.4 > 31.6 ppm
  Base @ drydown: 60%
  Est. skin life: 6-8h moderate + 2-4h skin scent

### 7. Balance
  Pyramid: T:0.2% H:43.5% B:56.3%
  OAV range: 0.00 to 6362 (sigma-log=1.59)
  Wide contrast: citrus (OAV 6362) dominates opening before burning off to reveal base.
    sub-threshold: 4

### 8. Flags
  SUB: Ethyl Vanillin OAV=0.59 role=Ethyl Vanillin
  SUB: Musk Ketone OAV=0.57 role=Musk Ketone
  SUB: Ambrettolide OAV=0.13 role=Ambrettolide
  SUB: Benzyl Benzoate OAV=0.00 role=Benzyl Benzoate


## Structural OAV Analysis

**Vapor:** 49 ppm  |  **Active:** 12.9%  |  **Perceptible:** 16/20

### OAV Tiers
  **massive** (2): Bergamot FCF oil Sicilian(4008), Alpha Ionone(6362)
  **v.strong** (4): Coumarin(239), Beta Ionone(881), Phenethyl Alcohol(110), Linalool(255)
  **strong** (1): Alpha Irone(67)
  **moderate** (2): Aldehyde C10(29), Ethylene Brassylate(12)
  **perceptible** (3): Aldehyde C11(8), Vanillin(5), Anisaldehyde(5)
  **threshold** (4): Irotyl(2), Ylang Ylang EO(4), Benzyl Salicylate(4), Cedarwood EO(4)
  **sub** (4): Ethyl Vanillin(1), Benzyl Benzoate(0), Musk Ketone(1), Ambrettolide(0)

### Block Balance
  **Citrus**     4008 (33%)
  **Floral**     7975 (66%)
  **Base**         12 (0%)
  **Ratio:** 675:1 between strongest/weakest block

### Issues
  ! 4 sub-threshold material(s): Ethyl Vanillin, Benzyl Benzoate, Musk Ketone, Ambrettolide
```
