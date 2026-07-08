# Iris Dreamweaver v2 — VP/ODT/ppm-based (scale-invariant)

**Design unit:** target active concentration (ppm w/w) in finished juice. Scales linearly to any batch size. OAV = ppm_juice / ODT_eth.

**Single-molecule + known-composition EOs only.** No FTECs, Fleuressence, FOs, or Accords whose individual ingredients are unknown.

## Final verification (10 mL reference batch)

- **Geo composite:** 79.139
- **Dose-response:** 100.0/100 (10 optimal · 0 marginal · 0 overdosed)
- **OAV guard:** 0 err · 0 warn
- **Concentrate:** 30.71%

### Brief markers (weight 1.5 each)

| Marker | Brief phrase | Score |
|---|---|--:|
| luxury         | "EXTREMELY EXPENSIVE, LUXURY" | 64.1 |
| longevity      | "LONG LASTING"              | 84.4 |
| sillage        | "PROJECTIVE"                | 71.6 |
| texture        | "TEXTURED"                  | 81.1 |
| stacking_depth | "DEEP"                      | 80.0 |
| synergy        | "SINGLE DIRECTION SYNERGY"  | 95.0 |

### Supporting markers (weight 1.0 each)

| Marker | Brief phrase | Score |
|---|---|--:|
| hedonic          | "beautiful and dreamy" | 85.1 |
| skin_performance | (required for projective longevity on skin) | 79.2 |

### Informational (de-weighted / excluded)

- perceptual_clarity (weight 0.2): 67.9 — brief said transparency is optional if character is lost
- photorealism (weight 0.0): 75.0 — EXCLUDED; not a literal-flower reproduction

## Optimization history

| Pass | Geo | DR | Overdosed |
|---|--:|--:|--:|
| baseline | 79.076 | 100.0 | 0 |
| pass1_fix_overdose | 79.076 | 100.0 | 0 |
| pass2_fix_marginal | 79.129 | 100.0 | 0 |
| pass3_boost_luxury | 79.163 | 100.0 | 0 |
| pass4_boost_sillage | 79.184 | 100.0 | 0 |
| pass5_boost_texture_stacking | 79.139 | 100.0 | 0 |

## Formula specification (ppm + OAV — the scale-invariant definition)

| Material | Role | ppm juice | Dilution | ODT eth (ppm) | OAV |
|---|---|--:|---|--:|--:|
| Bergamot FCF Sicilian | top | 4,000 | neat | 1.500 | 2667 |
| Red Mandarin EO | top | 2,000 | neat | 2.000 | 1000 |
| Alpha Irone | iris | 10,080 | 30% | 0.010 | 1008000 |
| Orivone | iris | 4,000 | neat | 0.500 | 8000 |
| Dihydro Beta Ionone | iris | 2,000 | neat | 0.050 | 40000 |
| Alpha Ionone | iris | 1,500 | neat | 0.100 | 15000 |
| Carrot Seed EO | iris | 1,500 | neat | 1.000 | 1500 |
| Ultralia | iris | 2,875 | neat | 0.050 | 57500 |
| Irotyl | iris | 650 | neat | 1.000 | 650 |
| Hedione | floral | 21,840 | neat | 5.000 | 4368 |
| Hedione HC | floral | 13,000 | neat | 5.000 | 2600 |
| Mayol | floral | 2,500 | neat | 3.000 | 833 |
| Hydroxycitronellal | floral | 2,000 | neat | 3.000 | 667 |
| Amyl Cinnamic Aldehyde | floral | 2,000 | neat | 2.000 | 1000 |
| DBCA | floral | 1,500 | neat | 0.500 | 3000 |
| Bourgeonal | floral | 1,000 | neat | 0.030 | 33333 |
| Farnesol | floral | 500 | neat | 10.000 | 50 |
| Cis Jasmone | floral | 500 | neat | — | — |
| Myristic Acid | bridge | 4,140 | 20% | 500.000 | 8 |
| Benzoin Resinoid | bridge | 7,800 | 50% | 30.000 | 260 |
| Heliotropal | bridge | 5,000 | neat | 5.000 | 1000 |
| Ethyl Vanillin | bridge | 2,000 | neat | 10.000 | 200 |
| Vanillin | bridge | 500 | 10% | 10.000 | 50 |
| Ethyl Maltol | bridge | 500 | 10% | 0.300 | 1667 |
| Delta Decalactone | bridge | 4,550 | neat | 10.000 | 455 |
| Maple Lactone | bridge | 840 | 20% | 0.200 | 4200 |
| Gamma Undecalactone | bridge | 3,750 | neat | 1.000 | 3750 |
| Coumarin | bridge | 2,400 | 20% | 5.000 | 480 |
| Anisaldehyde | bridge | 1,500 | neat | 5.000 | 300 |
| Ethylene Brassylate | base | 23,000 | neat | 2.000 | 11500 |
| Iso E Super | base | 18,000 | neat | 2.000 | 9000 |
| Benzyl Salicylate | base | 18,750 | neat | 50.000 | 375 |
| Musk Ketone | base | 1,400 | 10% | 2.000 | 700 |
| Exaltolide | base | 1,000 | 10% | 1.000 | 1000 |
| Ambermax | base | 5,400 | 50% | 0.500 | 10800 |
| Ambrettolide | base | 780 | 10% | 0.500 | 1560 |
| Hexyl Salicylate | base | 7,000 | neat | 30.000 | 233 |
| Azarbre | base | 6,000 | neat | 2.000 | 3000 |
| Koavone | base | 5,000 | neat | 2.000 | 2500 |
| Cedarwood Virginia | base | 3,000 | neat | 3.000 | 1000 |
| Ebanol | base | 5,000 | neat | 1.500 | 3333 |
| Bacdanol | base | 2,500 | neat | 2.500 | 1000 |

## Batch derivations (µL of stock dilution)

| Material | Dilution | 5 mL | 10 mL | 30 mL | 100 mL |
|---|---|--:|--:|--:|--:|
| Bergamot FCF Sicilian | neat | 20.00 | 40.00 | 120.00 | 400.00 |
| Red Mandarin EO | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| Alpha Irone | 30% | 168.00 | 336.00 | 1008.00 | 3360.00 |
| Orivone | neat | 20.00 | 40.00 | 120.00 | 400.00 |
| Dihydro Beta Ionone | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| Alpha Ionone | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Carrot Seed EO | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Ultralia | neat | 14.38 | 28.75 | 86.25 | 287.50 |
| Irotyl | neat | 3.25 | 6.50 | 19.50 | 65.00 |
| Hedione | neat | 109.20 | 218.40 | 655.20 | 2184.00 |
| Hedione HC | neat | 65.00 | 130.00 | 390.00 | 1300.00 |
| Mayol | neat | 12.50 | 25.00 | 75.00 | 250.00 |
| Hydroxycitronellal | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| Amyl Cinnamic Aldehyde | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| DBCA | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Bourgeonal | neat | 5.00 | 10.00 | 30.00 | 100.00 |
| Farnesol | neat | 2.50 | 5.00 | 15.00 | 50.00 |
| Cis Jasmone | neat | 2.50 | 5.00 | 15.00 | 50.00 |
| Myristic Acid | 20% | 103.50 | 207.00 | 621.00 | 2070.00 |
| Benzoin Resinoid | 50% | 78.00 | 156.00 | 468.00 | 1560.00 |
| Heliotropal | neat | 25.00 | 50.00 | 150.00 | 500.00 |
| Ethyl Vanillin | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| Vanillin | 10% | 25.00 | 50.00 | 150.00 | 500.00 |
| Ethyl Maltol | 10% | 25.00 | 50.00 | 150.00 | 500.00 |
| Delta Decalactone | neat | 22.75 | 45.50 | 136.50 | 455.00 |
| Maple Lactone | 20% | 21.00 | 42.00 | 126.00 | 420.00 |
| Gamma Undecalactone | neat | 18.75 | 37.50 | 112.50 | 375.00 |
| Coumarin | 20% | 60.00 | 120.00 | 360.00 | 1200.00 |
| Anisaldehyde | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Ethylene Brassylate | neat | 115.00 | 230.00 | 690.00 | 2300.00 |
| Iso E Super | neat | 90.00 | 180.00 | 540.00 | 1800.00 |
| Benzyl Salicylate | neat | 93.75 | 187.50 | 562.50 | 1875.00 |
| Musk Ketone | 10% | 70.00 | 140.00 | 420.00 | 1400.00 |
| Exaltolide | 10% | 50.00 | 100.00 | 300.00 | 1000.00 |
| Ambermax | 50% | 54.00 | 108.00 | 324.00 | 1080.00 |
| Ambrettolide | 10% | 39.00 | 78.00 | 234.00 | 780.00 |
| Hexyl Salicylate | neat | 35.00 | 70.00 | 210.00 | 700.00 |
| Azarbre | neat | 30.00 | 60.00 | 180.00 | 600.00 |
| Koavone | neat | 25.00 | 50.00 | 150.00 | 500.00 |
| Cedarwood Virginia | neat | 15.00 | 30.00 | 90.00 | 300.00 |
| Ebanol | neat | 25.00 | 50.00 | 150.00 | 500.00 |
| Bacdanol | neat | 12.50 | 25.00 | 75.00 | 250.00 |
| **Concentrate total** | | **1535.6** | **3071.2** | **9213.5** | **30711.5** |
| **Ethanol 96% (µL)** | | **3464** | **6929** | **20787** | **69288** |
| **Batch (µL)** | | **5000** | **10000** | **30000** | **100000** |

## Removed pre-blends (banned by rule 2)

- ~~Orris F-TEC~~ → replaced with more Alpha Irone + Orivone + Dihydro Beta Ionone (all single molecules)
- ~~Heliotropin Fleuressence~~ → Heliotropal (Piperonal) alone; it IS the heliotropin
- ~~Tonka Bean FO~~ → decomposed into Coumarin + Vanillin + Ethyl Vanillin + Benzoin Resinoid (known GC composition)

## Why this formula scales logically

The formula is defined in **ppm of active per unit juice**, not µL per batch. When you scale from 10 mL to 100 mL the ppm stays fixed, the OAV stays fixed, and the perceptual profile stays fixed. µL values simply multiply by 10. This is exactly how industrial fragrance specifications are written.

Pipette-floor flags below are the only non-linear concern — at small batches some trace materials fall below the 1 µL floor and must be pre-diluted further. These are called out by the OAV guard.
