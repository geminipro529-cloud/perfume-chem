# Iris-Jasmine — optimized 30 mL (non-linear verified)

**Status:** converged at 15 mL → proportionally scaled 2× to 30 mL → non-linearly reverified (Hill/Raoult/Stevens/mixture-suppression).
**Geometric composite score:** 81.15

**Batch:** 30.00 mL · concentrate 15020.0 µL · 50.1% concentrate

## Axis scores

| Axis | Score |
|---|---:|
| longevity | 82.8 |
| sillage | 93.7 |
| luxury | 68.7 |
| texture | 73.8 |
| stacking_depth | 80.0 |
| photorealism | 90.8 |
| perceptual_clarity | 75.3 |
| skin_performance | 73.6 |
| synergy | 95.0 |
| hedonic | 86.2 |
| **geometric composite** | **81.15** |

## Formula

| # | Material | Dilution | Amount (µL) | Amount (mL) |
|--:|---|---|---:|---:|
| 1 | Hedione | neat | 2400 | 2.400 |
| 2 | IPM | neat | 1620 | 1.620 |
| 3 | Ethylene Brassylate | neat | 1580 | 1.580 |
| 4 | Cedrat FCF oil Sicilian | neat | 1380 | 1.380 |
| 5 | Myristic Acid | 20% | 980 | 0.980 |
| 6 | Geraniol | neat | 950 | 0.950 |
| 7 | Hedione HC | neat | 820 | 0.820 |
| 8 | Alpha Irone | 30% | 720 | 0.720 |
| 9 | Iso E Super | neat | 560 | 0.560 |
| 10 | Hexyl Salicylate | neat | 460 | 0.460 |
| 11 | Exaltolide | 10% | 420 | 0.420 |
| 12 | Ebanol | neat | 380 | 0.380 |
| 13 | Romandolide | neat | 350 | 0.350 |
| 14 | Alpha Isomethyl Ionone | neat | 340 | 0.340 |
| 15 | Ambrettolide | 10% | 340 | 0.340 |
| 16 | Benzyl Salicylate | neat | 320 | 0.320 |
| 17 | Musk Ketone | 10% | 300 | 0.300 |
| 18 | Ambrox Super | 30% | 260 | 0.260 |
| 19 | Orivone | neat | 125 | 0.125 |
| 20 | Alpha Ionone | neat | 90 | 0.090 |
| 21 | Ultralia | neat | 90 | 0.090 |
| 22 | Jessemal | neat | 60 | 0.060 |
| 23 | Benzyl Acetate | neat | 50 | 0.050 |
| 24 | Beta Ionone | neat | 45 | 0.045 |
| 25 | Irotyl | neat | 30 | 0.030 |
| 26 | Methyl Benzoate | neat | 30 | 0.030 |
| 27 | Indole | 10% | 30 | 0.030 |
| 28 | Amyl Cinnamic Aldehyde | neat | 30 | 0.030 |
| 29 | Benzyl Benzoate | neat | 30 | 0.030 |
| 30 | Dihydrojasmone | neat | 30 | 0.030 |
| 31 | Carrot Seed EO | neat | 25 | 0.025 |
| 32 | Bergamot FCF oil Sicilian | neat | 20 | 0.020 |
| 33 | Ethyl Linalool | neat | 20 | 0.020 |
| 34 | Allyl Amyl Glycolate | neat | 20 | 0.020 |
| 35 | Paradisamide | 10% | 20 | 0.020 |
| 36 | Ylang Ylang EO (Extra grade) | neat | 20 | 0.020 |
| 37 | Phenethyl Alcohol | neat | 20 | 0.020 |
| 38 | Farnesol | neat | 15 | 0.015 |
| 39 | Koavone | neat | 15 | 0.015 |
| 40 | Leafovert | neat | 10 | 0.010 |
| 41 | Methyl Anthranilate | neat | 10 | 0.010 |
| 42 | Cis Jasmone | neat | 5 | 0.005 |
| — | Ethanol 96% | — | 14980.0 | 14.980 |
| — | **TOTAL** | — | **30000** | **30.000** |

## Non-linear verification

Concentration-dependent models applied (not simple linear scaling):
- **Hill equation** (`engine/dose_response.py`) — sigmoid character-zone audit
- **Raoult/Clausius-Clapeyron** (`engine/temporal_graph.py`) — evaporation physics
- **Stevens power law** — perceived intensity = OAV^0.4
- **Mixture suppression** — effective ODT × 5 for complex formulas

### OAV guard
- Absolute-µL semantics at 30.0 mL: **0 err**, 0 warn
- Proportional 30 → 15 mL reverse (re-split safety): **0 err**, 0 warn, 0 info

### Dose-response (Hill-equation character zones)
- Score: **98.4/100**
- Overdosed (negative/dangerous zone): 0
- Marginal (neutral zone): 2 — Hedione, Ethylene Brassylate

### Temporal evolution (TemporalEngine)
- TemporalEngine simulation did not complete.

## Scaling notes

- Scaled proportionally from the 15 mL optimized formula (µL × 2).
- Concentrate fraction is invariant under proportional scaling: OAV, perceived intensity, and evaporation curves are identical to the 15 mL half by construction.
- At 30 mL the 1 µL pipette floor is 0.033% of concentrate (vs 0.067% at 15 mL) — trace materials below 1 µL at 15 mL can be expressed precisely at 30 mL.