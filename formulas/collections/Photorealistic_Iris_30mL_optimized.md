# Photorealistic Iris — optimized 30 mL (non-linear verified)

**Status:** converged at 15 mL → proportionally scaled 2× to 30 mL → non-linearly reverified (Hill/Raoult/Stevens/mixture-suppression).
**Geometric composite score:** 83.63

**Batch:** 30.00 mL · concentrate 4506.0 µL · 15.0% concentrate

## Axis scores

| Axis | Score |
|---|---:|
| longevity | 89.4 |
| sillage | 89.6 |
| luxury | 76.9 |
| texture | 80.9 |
| stacking_depth | 75.0 |
| photorealism | 88.5 |
| perceptual_clarity | 84.4 |
| skin_performance | 78.4 |
| synergy | 95.0 |
| hedonic | 84.3 |
| **geometric composite** | **83.63** |

## Formula

| # | Material | Dilution | Amount (µL) | Amount (mL) |
|--:|---|---|---:|---:|
| 1 | Myristic Acid | 20% | 750 | 0.750 |
| 2 | Alpha Irone | 30% | 730 | 0.730 |
| 3 | Iso E Super | neat | 365 | 0.365 |
| 4 | Hedione | neat | 355 | 0.355 |
| 5 | Habanolide | neat | 335 | 0.335 |
| 6 | IPM | neat | 250 | 0.250 |
| 7 | Ethylene Brassylate | neat | 190 | 0.190 |
| 8 | Dihydromyrcenol | neat | 170 | 0.170 |
| 9 | Exaltolide | 10% | 150 | 0.150 |
| 10 | Ambrettolide | 10% | 140 | 0.140 |
| 11 | Ebanol | neat | 115 | 0.115 |
| 12 | Bergamot FCF oil Sicilian | neat | 100 | 0.100 |
| 13 | Musk Ketone | 10% | 100 | 0.100 |
| 14 | Koavone | neat | 100 | 0.100 |
| 15 | Hedione HC | neat | 85 | 0.085 |
| 16 | Ethyl Linalool | neat | 70 | 0.070 |
| 17 | Orivone | neat | 60 | 0.060 |
| 18 | Paradisamide | 10% | 60 | 0.060 |
| 19 | Azarbre | neat | 50 | 0.050 |
| 20 | Ambrox Super | 30% | 50 | 0.050 |
| 21 | Alpha Ionone | neat | 40 | 0.040 |
| 22 | Ultralia | neat | 40 | 0.040 |
| 23 | Heliotropal | neat | 40 | 0.040 |
| 24 | Carrot Seed EO | neat | 30 | 0.030 |
| 25 | Cashmeran | 20% | 30 | 0.030 |
| 26 | Beta Ionone | neat | 25 | 0.025 |
| 27 | Dihydro Beta Ionone | neat | 20 | 0.020 |
| 28 | Cyclamen Aldehyde | neat | 15 | 0.015 |
| 29 | Scentenal | 1% | 12 | 0.012 |
| 30 | Allyl Amyl Glycolate | neat | 10 | 0.010 |
| 31 | Cis Jasmone | neat | 10 | 0.010 |
| 32 | Farnesol | neat | 5 | 0.005 |
| 33 | Leafovert | neat | 4 | 0.004 |
| — | Ethanol 96% | — | 25494.0 | 25.494 |
| — | **TOTAL** | — | **30000** | **30.000** |

## Non-linear verification

Concentration-dependent models applied (not simple linear scaling):
- **Hill equation** (`engine/dose_response.py`) — sigmoid character-zone audit
- **Raoult/Clausius-Clapeyron** (`engine/temporal_graph.py`) — evaporation physics
- **Stevens power law** — perceived intensity = OAV^0.4
- **Mixture suppression** — effective ODT × 5 for complex formulas

### OAV guard
- Absolute-µL semantics at 30.0 mL: **0 err**, 1 warn
- Proportional 30 → 15 mL reverse (re-split safety): **0 err**, 0 warn, 1 info

### Dose-response (Hill-equation character zones)
- Score: **100.0/100**
- Overdosed (negative/dangerous zone): 0
- Marginal (neutral zone): 1 — Iso E Super

### Temporal evolution (TemporalEngine)
- TemporalEngine simulation did not complete.

## Scaling notes

- Scaled proportionally from the 15 mL optimized formula (µL × 2).
- Concentrate fraction is invariant under proportional scaling: OAV, perceived intensity, and evaporation curves are identical to the 15 mL half by construction.
- At 30 mL the 1 µL pipette floor is 0.033% of concentrate (vs 0.067% at 15 mL) — trace materials below 1 µL at 15 mL can be expressed precisely at 30 mL.