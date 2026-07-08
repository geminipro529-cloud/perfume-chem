# Iris Dreamweaver v3 — ppm + coord-descent

**v3 vs v2 summary:** SPEC redesigned for luxury (EV cut, Vanillin raised, AIMI trace added, Alpha Irone raised) and sillage (Romandolide projection musk + Habanolide halo + Hexyl Salicylate sheer film). Optimizer passes 3/4/5 replaced with coordinate-descent gradient search against target axis, with a brief-marker floor rule preventing regressions.

## Final verification (10 mL reference batch)

- **Geo composite:** 79.632
- **Dose-response:** 100.0/100 (9 optimal · 1 marginal · 0 overdosed)
- **OAV guard:** 0 err · 0 warn
- **Concentrate:** 31.64%

### Brief markers (weight 1.5 each)

| Marker | Brief phrase | Score |
|---|---|--:|
| luxury         | "EXTREMELY EXPENSIVE, LUXURY" | 64.2 |
| longevity      | "LONG LASTING"              | 84.5 |
| sillage        | "PROJECTIVE"                | 72.5 |
| texture        | "TEXTURED"                  | 81.0 |
| stacking_depth | "DEEP"                      | 80.0 |
| synergy        | "SINGLE DIRECTION SYNERGY"  | 95.0 |

### Supporting markers (weight 1.0 each)

| Marker | Brief phrase | Score |
|---|---|--:|
| hedonic          | "beautiful and dreamy" | 85.5 |
| skin_performance | (required for projective longevity on skin) | 82.4 |

### Informational (de-weighted / excluded)

- perceptual_clarity (weight 0.2): 69.4
- photorealism (weight 0.0): 77.4 — EXCLUDED

## Optimization history

| Pass | Geo | Luxury | Sillage | Texture | OD |
|---|--:|--:|--:|--:|--:|
| baseline_v3 | 79.208 | 63.0 | 71.7 | 80.9 | 0 |
| pass1_fix_overdose | 79.208 | 63.0 | 71.7 | 80.9 | 0 |
| pass2_fix_marginal | 79.208 | 63.0 | 71.7 | 80.9 | 0 |
| pass3_coord_luxury | 79.620 | 64.3 | 71.5 | 80.9 | 0 |
| pass4_coord_sillage | 79.632 | 64.2 | 72.5 | 81.0 | 0 |
| pass5_coord_texture | 79.632 | 64.2 | 72.5 | 81.0 | 0 |

## Formula specification (ppm + OAV)

| Material | Role | ppm juice | Dilution | ODT eth (ppm) | OAV |
|---|---|--:|---|--:|--:|
| Bergamot FCF Sicilian | top | 4,000 | neat | 1.500 | 2667 |
| Red Mandarin EO | top | 2,000 | neat | 2.000 | 1000 |
| Alpha Irone | iris | 15,868 | 30% | 0.010 | 1586800 |
| Orivone | iris | 4,000 | neat | 0.500 | 8000 |
| Dihydro Beta Ionone | iris | 2,000 | neat | 0.050 | 40000 |
| Alpha Ionone | iris | 1,500 | neat | 0.100 | 15000 |
| Alpha Isomethyl Ionone | iris | 1,200 | neat | 3.000 | 400 |
| Carrot Seed EO | iris | 1,500 | neat | 1.000 | 1500 |
| Ultralia | iris | 2,500 | neat | 0.050 | 50000 |
| Irotyl | iris | 500 | neat | 1.000 | 500 |
| Hedione | floral | 22,000 | neat | 5.000 | 4400 |
| Hedione HC | floral | 8,049 | neat | 5.000 | 1610 |
| Mayol | floral | 2,500 | neat | 3.000 | 833 |
| Hydroxycitronellal | floral | 2,000 | neat | 3.000 | 667 |
| Amyl Cinnamic Aldehyde | floral | 2,000 | neat | 2.000 | 1000 |
| DBCA | floral | 1,500 | neat | 0.500 | 3000 |
| Bourgeonal | floral | 1,000 | neat | 0.030 | 33333 |
| Farnesol | floral | 500 | neat | 10.000 | 50 |
| Cis Jasmone | floral | 500 | neat | — | — |
| Myristic Acid | bridge | 4,250 | 20% | 500.000 | 8 |
| Benzoin Resinoid | bridge | 5,000 | 50% | 30.000 | 167 |
| Heliotropal | bridge | 3,400 | neat | 5.000 | 680 |
| Ethyl Vanillin | bridge | 400 | 10% | 10.000 | 40 |
| Vanillin | bridge | 1,500 | 10% | 10.000 | 150 |
| Ethyl Maltol | bridge | 500 | 10% | 0.300 | 1667 |
| Delta Decalactone | bridge | 3,500 | neat | 10.000 | 350 |
| Maple Lactone | bridge | 700 | 20% | 0.200 | 3500 |
| Gamma Undecalactone | bridge | 3,000 | neat | 1.000 | 3000 |
| Coumarin | bridge | 2,400 | 20% | 5.000 | 480 |
| Anisaldehyde | bridge | 1,500 | neat | 5.000 | 300 |
| Ethylene Brassylate | base | 30,416 | neat | 2.000 | 15208 |
| Romandolide | base | 6,800 | neat | 1.000 | 6800 |
| Habanolide | base | 2,550 | neat | 0.200 | 12750 |
| Musk Ketone | base | 1,000 | 10% | 2.000 | 500 |
| Exaltolide | base | 800 | 10% | 1.000 | 800 |
| Ambrettolide | base | 600 | 10% | 0.500 | 1200 |
| Iso E Super | base | 12,750 | neat | 2.000 | 6375 |
| Benzyl Salicylate | base | 9,211 | neat | 50.000 | 184 |
| Hexyl Salicylate | base | 10,350 | neat | 30.000 | 345 |
| Ambermax | base | 3,400 | 50% | 0.500 | 6800 |
| Azarbre | base | 5,750 | neat | 2.000 | 2875 |
| Koavone | base | 4,000 | neat | 2.000 | 2000 |
| Cedarwood Virginia | base | 3,000 | neat | 3.000 | 1000 |
| Ebanol | base | 4,000 | neat | 1.500 | 2667 |
| Bacdanol | base | 2,500 | neat | 2.500 | 1000 |

## Batch derivations (µL of stock dilution)

| Material | Dilution | 5 mL | 10 mL | 30 mL | 100 mL |
|---|---|--:|--:|--:|--:|
| Bergamot FCF Sicilian | neat | 20.00 | 40.00 | 120.00 | 400.00 |
| Red Mandarin EO | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| Alpha Irone | 30% | 264.47 | 528.93 | 1586.80 | 5289.33 |
| Orivone | neat | 20.00 | 40.00 | 120.00 | 400.00 |
| Dihydro Beta Ionone | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| Alpha Ionone | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Alpha Isomethyl Ionone | neat | 6.00 | 12.00 | 36.00 | 120.00 |
| Carrot Seed EO | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Ultralia | neat | 12.50 | 25.00 | 75.00 | 250.00 |
| Irotyl | neat | 2.50 | 5.00 | 15.00 | 50.00 |
| Hedione | neat | 110.00 | 220.00 | 660.00 | 2200.00 |
| Hedione HC | neat | 40.24 | 80.49 | 241.47 | 804.90 |
| Mayol | neat | 12.50 | 25.00 | 75.00 | 250.00 |
| Hydroxycitronellal | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| Amyl Cinnamic Aldehyde | neat | 10.00 | 20.00 | 60.00 | 200.00 |
| DBCA | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Bourgeonal | neat | 5.00 | 10.00 | 30.00 | 100.00 |
| Farnesol | neat | 2.50 | 5.00 | 15.00 | 50.00 |
| Cis Jasmone | neat | 2.50 | 5.00 | 15.00 | 50.00 |
| Myristic Acid | 20% | 106.25 | 212.50 | 637.50 | 2125.00 |
| Benzoin Resinoid | 50% | 50.00 | 100.00 | 300.00 | 1000.00 |
| Heliotropal | neat | 17.00 | 34.00 | 102.00 | 340.00 |
| Ethyl Vanillin | 10% | 20.00 | 40.00 | 120.00 | 400.00 |
| Vanillin | 10% | 75.00 | 150.00 | 450.00 | 1500.00 |
| Ethyl Maltol | 10% | 25.00 | 50.00 | 150.00 | 500.00 |
| Delta Decalactone | neat | 17.50 | 35.00 | 105.00 | 350.00 |
| Maple Lactone | 20% | 17.50 | 35.00 | 105.00 | 350.00 |
| Gamma Undecalactone | neat | 15.00 | 30.00 | 90.00 | 300.00 |
| Coumarin | 20% | 60.00 | 120.00 | 360.00 | 1200.00 |
| Anisaldehyde | neat | 7.50 | 15.00 | 45.00 | 150.00 |
| Ethylene Brassylate | neat | 152.08 | 304.16 | 912.48 | 3041.60 |
| Romandolide | neat | 34.00 | 68.00 | 204.00 | 680.00 |
| Habanolide | neat | 12.75 | 25.50 | 76.50 | 255.00 |
| Musk Ketone | 10% | 50.00 | 100.00 | 300.00 | 1000.00 |
| Exaltolide | 10% | 40.00 | 80.00 | 240.00 | 800.00 |
| Ambrettolide | 10% | 30.00 | 60.00 | 180.00 | 600.00 |
| Iso E Super | neat | 63.75 | 127.50 | 382.50 | 1275.00 |
| Benzyl Salicylate | neat | 46.05 | 92.11 | 276.33 | 921.10 |
| Hexyl Salicylate | neat | 51.75 | 103.50 | 310.50 | 1035.00 |
| Ambermax | 50% | 34.00 | 68.00 | 204.00 | 680.00 |
| Azarbre | neat | 28.75 | 57.50 | 172.50 | 575.00 |
| Koavone | neat | 20.00 | 40.00 | 120.00 | 400.00 |
| Cedarwood Virginia | neat | 15.00 | 30.00 | 90.00 | 300.00 |
| Ebanol | neat | 20.00 | 40.00 | 120.00 | 400.00 |
| Bacdanol | neat | 12.50 | 25.00 | 75.00 | 250.00 |
| **Concentrate total** | | **1582.1** | **3164.2** | **9492.6** | **31641.9** |
| **Ethanol 96% (µL)** | | **3418** | **6836** | **20507** | **68358** |
| **Batch (µL)** | | **5000** | **10000** | **30000** | **100000** |

## Notes on Myristic Acid (orris-butter matrix)

Myristic acid is a solid waxy powder — weigh as mg, not pipette. At 5,000 ppm in 10 mL juice that is **50 mg** of powder. The 20% stock listing is a workflow convenience: dissolve the required mg of powder in enough DPG to make a 20% solution, then pipette stock µL from that. This material anchors the iris with a lactonic-buttery coating that mimics the fatty matrix of natural Orris Butter.
