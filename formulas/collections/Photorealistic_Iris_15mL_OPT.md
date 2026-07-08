# PHOTOREALISTIC IRIS — 15 mL (multi-seed converged)

**Batch:** 15.00 mL EDP
**Concentrate:** 4236 µL / 15 000 µL = 28.2%
**Optimization:** 3 seeds × coordinate-descent hill climber, cascading step sizes 20%/10%/5%, OAV guard enforced every accepted step, convergence epsilon = 0.03 geometric-total.

## Axis scores (baseline → optimized)

| Axis | Baseline | Optimized | Δ |
|---|---:|---:|---:|
| longevity | 89.20 | 85.90 | -3.30 |
| sillage | 80.80 | 95.60 | +14.80 |
| synergy | 95.00 | 95.00 | +0.00 |
| luxury | 61.40 | 62.90 | +1.50 |
| texture | 73.10 | 73.80 | +0.70 |
| stacking_depth | 70.00 | 70.00 | +0.00 |
| skin_performance | 69.60 | 71.80 | +2.20 |
| hedonic | 85.80 | 85.90 | +0.10 |
| perceptual_clarity | 59.50 | 65.00 | +5.50 |
| photorealism | 83.70 | 91.00 | +7.30 |
| **GEOMETRIC TOTAL** | **75.400** | **78.300** | **+2.900** |

## Optimized µL formula (15 mL batch)

| # | Material | Dilution | µL | mL |
|--:|---|---:|---:|---:|
| 1 | Bergamot FCF Sicilian | neat | 100 | 0.100 |
| 2 | Grapefruit FCF | neat | 30 | 0.030 |
| 3 | Leafovert | neat | 4 | 0.004 |
| 4 | Ethyl Linalool | neat | 56 | 0.056 |
| 5 | Dihydromyrcenol | neat | 237 | 0.237 |
| 6 | Allyl Amyl Glycolate | neat | 10 | 0.010 |
| 7 | Scentenal 1% | 1.0% | 12 | 0.012 |
| 8 | Alpha Irone | 30.0% | 250 | 0.250 |
| 9 | Myristic Acid | 20.0% | 600 | 0.600 |
| 10 | Alpha Ionone | neat | 32 | 0.032 |
| 11 | Beta Ionone | neat | 25 | 0.025 |
| 12 | Allyl Ionone | neat | 15 | 0.015 |
| 13 | Alpha Isomethyl Ionone | neat | 72 | 0.072 |
| 14 | Dihydro Beta Ionone | neat | 20 | 0.020 |
| 15 | Irotyl | neat | 30 | 0.030 |
| 16 | Orivone | neat | 60 | 0.060 |
| 17 | Hedione | neat | 674 | 0.674 |
| 18 | Hedione HC | neat | 48 | 0.048 |
| 19 | Cis Jasmone | neat | 10 | 0.010 |
| 20 | Carrot Seed | neat | 30 | 0.030 |
| 21 | Ultralia | neat | 32 | 0.032 |
| 22 | Cyclamen Aldehyde | neat | 15 | 0.015 |
| 23 | Farnesol | neat | 5 | 0.005 |
| 24 | Violet Fleuressence | neat | 15 | 0.015 |
| 25 | Heliotropin | neat | 32 | 0.032 |
| 26 | Musk Ketone 10% | 10.0% | 100 | 0.100 |
| 27 | Koavone | neat | 100 | 0.100 |
| 28 | Azarbre | neat | 50 | 0.050 |
| 29 | Ebanol | neat | 115 | 0.115 |
| 30 | Iso E Super | neat | 168 | 0.168 |
| 31 | Habanolide | neat | 475 | 0.475 |
| 32 | Ethylene Brassylate | neat | 190 | 0.190 |
| 33 | Exaltolide 10% | 10.0% | 150 | 0.150 |
| 34 | Ambrettolide 10% | 10.0% | 125 | 0.125 |
| 35 | Romandolide | neat | 48 | 0.048 |
| 36 | Ambrox Super 30% | 30.0% | 50 | 0.050 |
| 37 | IPM | neat | 250 | 0.250 |
| 38 | Geosmin 0.5% | 0.5% | 1 | 0.001 |
| | **Concentrate total** | | **4236** | **4.236** |
| | Ethanol 96% to 15 mL | | 10764 | 10.764 |
| | **BATCH TOTAL** | | **15000** | **15.000** |

## OAV guard — post-optimization

### Proportional scaling 15 → 30 mL (the actual target merge)
```
OAV batch-scaling audit: 0 error(s), 0 warning(s), 2 info
  ℹ Scentenal 1%: scaled dose 24.00 µL of 1.0% (neat-equiv 0.240 µL) — trace band, verify dilution stock accuracy
  ℹ Geosmin 0.5%: scaled dose 2.00 µL of 0.5% (neat-equiv 0.010 µL) — trace band, verify dilution stock accuracy
```

### Proportional scaling 15 → 10 mL (stress test)
```
OAV batch-scaling audit: 1 error(s), 0 warning(s), 1 info
  ✗ Geosmin 0.5%: proportional scaling from 15.0 mL → 10.0 mL yields 0.667 µL (below 1.0 µL pipette floor). Use a weaker pre-dilution or keep minimum 1 µL and accept concentration shift.
  ℹ Scentenal 1%: scaled dose 8.00 µL of 1.0% (neat-equiv 0.080 µL) — trace band, verify dilution stock accuracy
```

### Absolute-keep 15 → 30 mL (ODT / mixture crossings)
```
OAV batch-scaling audit: 0 error(s), 2 warning(s), 0 info
  ⚠ Scentenal 1%: 12.00 µL (neat-equiv 0.12 µL) — near pipette floor; cannot be halved safely, re-dilute stock or keep dose fixed across splits
  ⚠ Geosmin 0.5%: 1.00 µL (neat-equiv 0.01 µL) — near pipette floor; cannot be halved safely, re-dilute stock or keep dose fixed across splits
```