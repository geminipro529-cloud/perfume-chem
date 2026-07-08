# Layton DNA-Inspired Mass-Market Trio - 3 Optimized 30 mL EDPs

Classification: amber-vanilla fruity-spiced masculine / modern oriental amber, not aromatic fougere.

**Status:** Commercial-trial candidates when generated with `--commercial-trial`; not sellable until calibrated with real wear-test records.

Each build is a 30 mL EDP at 20% concentrate: 6.00 mL concentrate plus 24.00 mL ethanol.
The optimizer models the final mixed solution: ethanol, active raw materials, diluted-stock carrier, vapor ppm, ODT, and OAV over top/heart/base windows.

Layton DNA-inspired target: apple-citrus-cardamom-like opening, lavender as support only, Hedione-led radiance, then amber-vanilla-sandalwood/musk drydown.
True proprietary cardamom-base fidelity is intentionally sacrificed for transparent commercial-trial buildability: the impression is rebuilt from Terpinyl Acetate, Linalyl Acetate, Ethyl Linalool, and trace Eugenol.
These are explicitly not aromatic fougeres; the family gate blocks moss/coumarin drift into fougere territory.

## Release Gate Summary

| Formula | Gate status | Commercial readiness | Confidence | Repair actions |
|---|---:|---|---:|---:|
| Bangkok Fresh Layton | WARN | COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE | 46.7 | 0 |
| Air-Conditioned Amber Layton | WARN | COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE | 46.0 | 0 |
| Tropical Night Layton Intense | WARN | COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE | 46.2 | 0 |

## Perfumist Verdict

Would a real perfumer who does not care about the chemistry read these as good formulas? Yes, as transparent commercial-trial sketches. The caveat is deliberate: these are Layton DNA-inspired, not proprietary-cardamom-base faithful, and they still need empirical wear-test calibration before sale.

## 1. Bangkok Fresh Layton

*Daytime Layton DNA-inspired: bergamot-citron apple, transparent cardamom air, clean amber musk.*

**Market logic:** Built for Thai daytime and malls: keep the apple-cardamom-like hook, reduce winter vanilla density, and let citrus/fresh musks carry projection.

**Perfumer-readable verdict:** A non-technical perfumer should read this as a commercial fresh amber: apple and a transparent cardamom impression are obvious in the top, lavender is support, and the drydown is soft vanilla amber rather than barbershop fougere.

**Family archetype:** `layton_dna.fresh_thai`

**Optimizer score:** `-71.997 -> -55.979` (`+16.019`)

### Release Gate Audit

**Gate status:** `WARN`
**Commercial readiness:** `COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE`
**Family archetype:** `layton_dna.fresh_thai`
**Commercial mode:** `True`
**Commercial confidence policy:** `warn`
**IFRA headroom:** `80%` (configured `80%`)
**Audit event:** `not logged`
**Confidence:** `LOW` (46.7 combined)

### Calibration Summary

Records `0`, wear observations `0`, panel results `0`, ready `False`

| Gate | Status | Detail |
|---|---:|---|
| exact_subtotal | PASS | 6000.0 uL |
| duplicate_canonical_materials | PASS | - |
| material_spine_coverage | PASS | - |
| physics_data_coverage | PASS | - |
| odt_coverage | PASS | - |
| chemistry_stability | PASS | predicted shelf life 896 days |
| phase_compatibility | PASS | no HSP phase-out risk detected |
| opaque_preblends | PASS | - |
| blocked_materials | PASS | - |
| pipette_floor_neat_traces | PASS | - |
| small_diluted_traces | PASS | - |
| oav_scaling_guard | PASS | not requested |
| safety_ifra_allergen | WARN | 9 materials lack explicit IFRA Cat4 limits; 4 EU allergen declarations |
| perfumer_logic | PASS | layton_dna.fresh_thai |
| family_drift_detector | PASS | layton_dna.fresh_thai; no family drift |
| novelty_vs_reference | PASS | Fresh Thai Layton DNA-inspired amber; novelty judged against Layton DNA transparency rather than fougere reference |
| oav_legibility | PASS | 21 perceptible materials |
| sensory_overcrowding | PASS | 9 perceptible channels |
| master_perfumer_gate | PASS | coherent, buildable, and readable |
| robustness_perturbation | PASS | 56 subtotal-preserving perturbations stable |
| confidence_minimum | WARN | combined confidence 46.7; commercial-trial warning, not sellable until calibrated |

### Repair History

No repair actions were needed after the optimizer pass.

### Gate Time-Series OAV Leaders

- `opening` (0s): Grapefruit FCF OAV=13449.9 ppm=67.249431, Red Mandarin EO OAV=5674.2 ppm=56.741707, Dihydromyrcenol OAV=2930.1 ppm=2.930062, Bergamot FCF OAV=2184.3 ppm=32.764051, Ethyl 2-Methylbutyrate OAV=970.0 ppm=0.058202
- `top` (300s): Grapefruit FCF OAV=12436.3 ppm=62.181462, Red Mandarin EO OAV=5246.6 ppm=52.465609, Dihydromyrcenol OAV=2933.2 ppm=2.933203, Bergamot FCF OAV=2161.4 ppm=32.421041, Ethyl 2-Methylbutyrate OAV=976.5 ppm=0.058588
- `heart` (1800s): Grapefruit FCF OAV=8348.6 ppm=41.742873, Red Mandarin EO OAV=3522.1 ppm=35.220549, Dihydromyrcenol OAV=2929.1 ppm=2.929062, Bergamot FCF OAV=2036.8 ppm=30.551576, Ethyl 2-Methylbutyrate OAV=1002.5 ppm=0.060149
- `late_heart` (7200s): Dihydromyrcenol OAV=2753.3 ppm=2.753262, Grapefruit FCF OAV=1878.7 ppm=9.393495, Bergamot FCF OAV=1553.9 ppm=23.308022, Ethyl 2-Methylbutyrate OAV=1041.2 ppm=0.062470, Red Mandarin EO OAV=792.6 ppm=7.925762
- `drydown` (14400s): Dihydromyrcenol OAV=2399.9 ppm=2.399904, Ethyl 2-Methylbutyrate OAV=1036.6 ppm=0.062199, Bergamot FCF OAV=1025.4 ppm=15.381151, Cedrat FCF oil Sicilian OAV=518.0 ppm=6.215917, Linalool OAV=307.6 ppm=1.845305

### Optimized Formula - 30 mL EDP

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Hedione | neat | 913 | 0.913 |
| 2 | Iso E Super | neat | 854 | 0.854 |
| 3 | Ambrox Super | 30% | 831 | 0.831 |
| 4 | Vanillin | 10% | 399 | 0.399 |
| 5 | Habanolide | neat | 394 | 0.394 |
| 6 | Bergamot FCF | neat | 273 | 0.273 |
| 7 | Terpinyl Acetate | neat | 265 | 0.265 |
| 8 | Ethyl Vanillin | 10% | 216 | 0.216 |
| 9 | Linalyl Acetate | neat | 208 | 0.208 |
| 10 | Apritone | 10% | 155 | 0.155 |
| 11 | Alpha Isomethyl Ionone | neat | 150 | 0.150 |
| 12 | Sandalore | neat | 133 | 0.133 |
| 13 | Grapefruit FCF | neat | 121 | 0.121 |
| 14 | Coumarin | 20% | 116 | 0.116 |
| 15 | Cedrat FCF oil Sicilian | neat | 114 | 0.114 |
| 16 | Romandolide | neat | 114 | 0.114 |
| 17 | Red Mandarin EO | neat | 102 | 0.102 |
| 18 | Lavender EO | neat | 96 | 0.096 |
| 19 | Galaxolide | 80% | 83 | 0.083 |
| 20 | Hexyl Acetate | 10% | 80 | 0.080 |
| 21 | Ethylene Brassylate | neat | 76 | 0.076 |
| 22 | Dihydromyrcenol | neat | 61 | 0.061 |
| 23 | Ethyl Linalool | neat | 61 | 0.061 |
| 24 | Azarbre | neat | 57 | 0.057 |
| 25 | Linalool | neat | 38 | 0.038 |
| 26 | Benzyl Acetate | neat | 38 | 0.038 |
| 27 | Ethyl 2-Methylbutyrate | 10% prep | 34 | 0.034 |
| 28 | Eugenol | neat | 18 | 0.018 |
| - | **Fragrance concentrate subtotal** | - | **6000** | **6.000** |
| - | Ethanol 96% bottle fill | neat | **24000** | **24.000** |
| - | **Final bottle total** | - | **30000** | **30.000** |

### Active Neat-Equivalent View

| Material | Raw concentrate % | Active neat-equivalent % of concentrate |
|---|---:|---:|
| Hedione | 15.237 | 15.237 |
| Iso E Super | 14.236 | 14.236 |
| Ambrox Super | 13.852 | 4.156 |
| Vanillin | 6.649 | 0.665 |
| Habanolide | 6.560 | 6.560 |
| Bergamot FCF | 4.547 | 4.547 |
| Terpinyl Acetate | 4.419 | 4.419 |
| Ethyl Vanillin | 3.606 | 0.361 |
| Linalyl Acetate | 3.463 | 3.463 |
| Apritone | 2.589 | 0.259 |
| Alpha Isomethyl Ionone | 2.493 | 2.493 |
| Sandalore | 2.210 | 2.210 |
| Grapefruit FCF | 2.021 | 2.021 |
| Coumarin | 1.939 | 0.388 |
| Cedrat FCF oil Sicilian | 1.895 | 1.895 |
| Romandolide | 1.895 | 1.895 |
| Red Mandarin EO | 1.705 | 1.705 |
| Lavender EO | 1.593 | 1.593 |
| Galaxolide | 1.389 | 1.111 |
| Hexyl Acetate | 1.336 | 0.134 |
| Ethylene Brassylate | 1.263 | 1.263 |
| Dihydromyrcenol | 1.010 | 1.010 |
| Ethyl Linalool | 1.010 | 1.010 |
| Azarbre | 0.947 | 0.947 |
| Linalool | 0.631 | 0.631 |
| Benzyl Acetate | 0.631 | 0.631 |
| Ethyl 2-Methylbutyrate | 0.568 | 0.057 |
| Eugenol | 0.305 | 0.305 |

### Family OAV Envelope

| Window | Optimized family OAV |
|---|---|
| top | `citrus`=2518.6, `fresh`=331.3, `fruity`=111.6, `aromatic`=82.9, `amber`=8.8, `radiance`=5.1, `wood`=2.7, `spice`=2.3 |
| heart | `fresh`=1610.3, `fruity`=822.6, `citrus`=626.3, `aromatic`=374.7, `amber`=75.5, `radiance`=42.8, `wood`=23.4, `spice`=18.5 |
| base | `fruity`=154.3, `amber`=92.7, `radiance`=44.3, `wood`=27.7, `musk`=18.6, `aromatic`=16.5, `spice`=8.9, `gourmand`=2.9 |

### Vapor ppm / ODT / OAV Leaders

**top window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Grapefruit FCF | 7.602888 | 0.005000 | 1520.6 |
| Red Mandarin EO | 6.414936 | 0.010000 | 641.5 |
| Dihydromyrcenol | 0.331258 | 0.001000 | 331.3 |
| Bergamot FCF | 3.704141 | 0.015000 | 246.9 |
| Ethyl 2-Methylbutyrate | 0.006580 | 0.000060 | 109.7 |
| Cedrat FCF oil Sicilian | 1.314930 | 0.012000 | 109.6 |
| Linalool | 0.262767 | 0.006000 | 43.8 |
| Lavender EO | 0.622291 | 0.020000 | 31.1 |

**heart window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Dihydromyrcenol | 1.610296 | 0.001000 | 1610.3 |
| Ethyl 2-Methylbutyrate | 0.048385 | 0.000060 | 806.4 |
| Bergamot FCF | 5.879201 | 0.015000 | 391.9 |
| Cedrat FCF oil Sicilian | 2.812403 | 0.012000 | 234.4 |
| Linalool | 1.078078 | 0.006000 | 179.7 |
| Lavender EO | 2.691249 | 0.020000 | 134.6 |
| Ambrox Super | 0.022647 | 0.000300 | 75.5 |
| Hedione | 0.856002 | 0.020000 | 42.8 |

**base window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Ethyl 2-Methylbutyrate | 0.008540 | 0.000060 | 142.3 |
| Ambrox Super | 0.027781 | 0.000300 | 92.6 |
| Hedione | 0.886774 | 0.020000 | 44.3 |
| Iso E Super | 0.276541 | 0.010000 | 27.7 |
| Habanolide | 0.017606 | 0.001000 | 17.6 |
| Hexyl Acetate | 0.023628 | 0.002000 | 11.8 |
| Eugenol | 0.053393 | 0.006000 | 8.9 |
| Terpinyl Acetate | 0.628877 | 0.080000 | 7.9 |

### Mixing Order

| Step | Phase | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---|---|---:|---:|
| 1 | Foundation | Iso E Super | neat | 854 | 0.854 |
| 2 | Foundation | Ambrox Super | 30% | 831 | 0.831 |
| 3 | Foundation | Vanillin | 10% | 399 | 0.399 |
| 4 | Foundation | Habanolide | neat | 394 | 0.394 |
| 5 | Foundation | Ethyl Vanillin | 10% | 216 | 0.216 |
| 6 | Foundation | Sandalore | neat | 133 | 0.133 |
| 7 | Foundation | Coumarin | 20% | 116 | 0.116 |
| 8 | Foundation | Romandolide | neat | 114 | 0.114 |
| 9 | Foundation | Galaxolide | 80% | 83 | 0.083 |
| 10 | Foundation | Ethylene Brassylate | neat | 76 | 0.076 |
| 11 | Foundation | Azarbre | neat | 57 | 0.057 |
| 12 | Heart Bridge | Hedione | neat | 913 | 0.913 |
| 13 | Heart Bridge | Alpha Isomethyl Ionone | neat | 150 | 0.150 |
| 14 | Heart Bridge | Benzyl Acetate | neat | 38 | 0.038 |
| 15 | Aromatic Support | Terpinyl Acetate | neat | 265 | 0.265 |
| 16 | Aromatic Support | Linalyl Acetate | neat | 208 | 0.208 |
| 17 | Aromatic Support | Lavender EO | neat | 96 | 0.096 |
| 18 | Aromatic Support | Ethyl Linalool | neat | 61 | 0.061 |
| 19 | Aromatic Support | Linalool | neat | 38 | 0.038 |
| 20 | Top Impact | Bergamot FCF | neat | 273 | 0.273 |
| 21 | Top Impact | Apritone | 10% | 155 | 0.155 |
| 22 | Top Impact | Grapefruit FCF | neat | 121 | 0.121 |
| 23 | Top Impact | Cedrat FCF oil Sicilian | neat | 114 | 0.114 |
| 24 | Top Impact | Red Mandarin EO | neat | 102 | 0.102 |
| 25 | Top Impact | Hexyl Acetate | 10% | 80 | 0.080 |
| 26 | Top Impact | Dihydromyrcenol | neat | 61 | 0.061 |
| 27 | Top Impact | Ethyl 2-Methylbutyrate | 10% prep | 34 | 0.034 |
| 28 | Top Impact | Eugenol | neat | 18 | 0.018 |
| 29 | Final Dilution | Ethanol 96% bottle fill | neat | 24000 | 24.000 |

1. Add foundation materials first so the amber-wood-musk-vanilla body is fully homogeneous.
2. Add the heart bridge next to connect diffusion, floral lift, and powdery volume into the base.
3. Add aromatic support after the body is clear and uniform.
4. Add the top-impact materials last to preserve freshness and the apple-citrus-cardamom-like effect.
5. Rest 48 hours before first read; judge seriously after 14-21 days.

## 2. Air-Conditioned Amber Layton

*Polished indoor amber: luminous jasmine air, apple-cardamom-like trace, vanilla woods.*

**Market logic:** SEA office/evening version: recognizable amber-vanilla Layton architecture, but transparent enough for air-conditioned interiors and not syrupy outdoors.

**Perfumer-readable verdict:** A perfumer should see one clear amber anchor, one sandalwood layer, one dry wood trace, and one musk cushion. The formula avoids the v4 problem of every warm base material shouting at once.

**Family archetype:** `layton_dna.indoor_amber`

**Optimizer score:** `-68.739 -> -58.230` (`+10.509`)

### Release Gate Audit

**Gate status:** `WARN`
**Commercial readiness:** `COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE`
**Family archetype:** `layton_dna.indoor_amber`
**Commercial mode:** `True`
**Commercial confidence policy:** `warn`
**IFRA headroom:** `80%` (configured `80%`)
**Audit event:** `not logged`
**Confidence:** `LOW` (46.0 combined)

### Calibration Summary

Records `0`, wear observations `0`, panel results `0`, ready `False`

| Gate | Status | Detail |
|---|---:|---|
| exact_subtotal | PASS | 6000.0 uL |
| duplicate_canonical_materials | PASS | - |
| material_spine_coverage | PASS | - |
| physics_data_coverage | PASS | - |
| odt_coverage | PASS | - |
| chemistry_stability | PASS | predicted shelf life 896 days |
| phase_compatibility | PASS | no HSP phase-out risk detected |
| opaque_preblends | PASS | - |
| blocked_materials | PASS | - |
| pipette_floor_neat_traces | PASS | - |
| small_diluted_traces | PASS | - |
| oav_scaling_guard | PASS | not requested |
| safety_ifra_allergen | WARN | 11 materials lack explicit IFRA Cat4 limits; 5 EU allergen declarations |
| perfumer_logic | PASS | layton_dna.indoor_amber |
| family_drift_detector | PASS | layton_dna.indoor_amber; no family drift |
| novelty_vs_reference | PASS | Air-conditioned amber Layton DNA-inspired trial; novelty judged against Layton DNA transparency rather than fougere reference |
| oav_legibility | PASS | 23 perceptible materials |
| sensory_overcrowding | PASS | 11 perceptible channels |
| master_perfumer_gate | PASS | coherent, buildable, and readable |
| robustness_perturbation | PASS | 62 subtotal-preserving perturbations stable |
| confidence_minimum | WARN | combined confidence 46.0; commercial-trial warning, not sellable until calibrated |

### Repair History

No repair actions were needed after the optimizer pass.

### Gate Time-Series OAV Leaders

- `opening` (0s): Red Mandarin EO OAV=6126.5 ppm=61.265128, Bergamot FCF OAV=1754.9 ppm=26.323321, Ethyl 2-Methylbutyrate OAV=748.2 ppm=0.044890, Cedrat FCF oil Sicilian OAV=747.6 ppm=8.970711, Linalool OAV=510.1 ppm=3.060460
- `top` (300s): Red Mandarin EO OAV=5644.6 ppm=56.445809, Bergamot FCF OAV=1730.2 ppm=25.952935, Ethyl 2-Methylbutyrate OAV=750.4 ppm=0.045023, Cedrat FCF oil Sicilian OAV=739.0 ppm=8.868383, Linalool OAV=507.0 ppm=3.042027
- `heart` (1800s): Red Mandarin EO OAV=3733.7 ppm=37.336525, Bergamot FCF OAV=1606.0 ppm=24.089394, Ethyl 2-Methylbutyrate OAV=758.7 ppm=0.045525, Cedrat FCF oil Sicilian OAV=695.3 ppm=8.343392, Linalool OAV=490.1 ppm=2.940610
- `late_heart` (7200s): Bergamot FCF OAV=1191.0 ppm=17.865125, Red Mandarin EO OAV=817.7 ppm=8.177493, Ethyl 2-Methylbutyrate OAV=765.8 ppm=0.045948, Cedrat FCF oil Sicilian OAV=541.3 ppm=6.495531, Linalool OAV=420.5 ppm=2.523140
- `drydown` (14400s): Bergamot FCF OAV=774.9 ppm=11.623817, Ethyl 2-Methylbutyrate OAV=751.5 ppm=0.045087, Cedrat FCF oil Sicilian OAV=375.8 ppm=4.508995, Linalool OAV=332.2 ppm=1.993000, Lavender EO OAV=199.0 ppm=3.979272

### Optimized Formula - 30 mL EDP

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Hedione | neat | 1413 | 1.413 |
| 2 | Ambrox Super | 30% | 1018 | 1.018 |
| 3 | Iso E Super | neat | 542 | 0.542 |
| 4 | Vanillin | 10% | 370 | 0.370 |
| 5 | Habanolide | neat | 256 | 0.256 |
| 6 | Bergamot FCF | neat | 211 | 0.211 |
| 7 | Alpha Isomethyl Ionone | neat | 204 | 0.204 |
| 8 | Ethyl Vanillin | 10% | 201 | 0.201 |
| 9 | Sandalore | neat | 169 | 0.169 |
| 10 | Terpinyl Acetate | neat | 156 | 0.156 |
| 11 | Apritone | 10% | 135 | 0.135 |
| 12 | Ethylene Brassylate | neat | 127 | 0.127 |
| 13 | Coumarin | 20% | 111 | 0.111 |
| 14 | Red Mandarin EO | neat | 106 | 0.106 |
| 15 | Linalyl Acetate | neat | 101 | 0.101 |
| 16 | Lavender EO | neat | 93 | 0.093 |
| 17 | Timberol | neat | 93 | 0.093 |
| 18 | Cedrat FCF oil Sicilian | neat | 84 | 0.084 |
| 19 | Azarbre | neat | 84 | 0.084 |
| 20 | Ambrettolide | 10% | 84 | 0.084 |
| 21 | Ethyl Linalool | neat | 76 | 0.076 |
| 22 | Benzyl Acetate | neat | 63 | 0.063 |
| 23 | Hexyl Acetate | 10% | 56 | 0.056 |
| 24 | Benzoin Resinoid | 50% | 51 | 0.051 |
| 25 | Linalool | neat | 42 | 0.042 |
| 26 | Phenethyl Alcohol | neat | 42 | 0.042 |
| 27 | Geraniol | neat | 34 | 0.034 |
| 28 | Ethyl 2-Methylbutyrate | 10% prep | 25 | 0.025 |
| 29 | Dihydrojasmone | neat | 25 | 0.025 |
| 30 | Eugenol | neat | 15 | 0.015 |
| 31 | Norlimbanol Dextro | neat | 13 | 0.013 |
| - | **Fragrance concentrate subtotal** | - | **6000** | **6.000** |
| - | Ethanol 96% bottle fill | neat | **24000** | **24.000** |
| - | **Final bottle total** | - | **30000** | **30.000** |

### Active Neat-Equivalent View

| Material | Raw concentrate % | Active neat-equivalent % of concentrate |
|---|---:|---:|
| Hedione | 23.531 | 23.531 |
| Ambrox Super | 16.971 | 5.091 |
| Iso E Super | 9.038 | 9.038 |
| Vanillin | 6.171 | 0.617 |
| Habanolide | 4.272 | 4.272 |
| Bergamot FCF | 3.517 | 3.517 |
| Alpha Isomethyl Ionone | 3.394 | 3.394 |
| Ethyl Vanillin | 3.346 | 0.335 |
| Sandalore | 2.813 | 2.813 |
| Terpinyl Acetate | 2.605 | 2.605 |
| Apritone | 2.248 | 0.225 |
| Ethylene Brassylate | 2.110 | 2.110 |
| Coumarin | 1.851 | 0.370 |
| Red Mandarin EO | 1.772 | 1.772 |
| Linalyl Acetate | 1.688 | 1.688 |
| Lavender EO | 1.547 | 1.547 |
| Timberol | 1.543 | 1.543 |
| Cedrat FCF oil Sicilian | 1.407 | 1.407 |
| Azarbre | 1.407 | 1.407 |
| Ambrettolide | 1.407 | 0.141 |
| Ethyl Linalool | 1.266 | 1.266 |
| Benzyl Acetate | 1.055 | 1.055 |
| Hexyl Acetate | 0.930 | 0.093 |
| Benzoin Resinoid | 0.844 | 0.422 |
| Linalool | 0.703 | 0.703 |
| Phenethyl Alcohol | 0.703 | 0.703 |
| Geraniol | 0.563 | 0.563 |
| Ethyl 2-Methylbutyrate | 0.422 | 0.042 |
| Dihydrojasmone | 0.422 | 0.422 |
| Eugenol | 0.243 | 0.243 |
| Norlimbanol Dextro | 0.211 | 0.211 |

### Family OAV Envelope

| Window | Optimized family OAV |
|---|---|
| top | `citrus`=942.6, `aromatic`=83.6, `fruity`=83.1, `amber`=10.9, `radiance`=7.9, `floral`=3.6, `wood`=2.6, `spice`=1.9 |
| heart | `fruity`=587.5, `citrus`=467.8, `aromatic`=351.6, `amber`=89.0, `radiance`=63.6, `floral`=23.4, `wood`=21.3, `spice`=14.2 |
| base | `fruity`=119.4, `amber`=106.0, `radiance`=64.6, `wood`=24.6, `musk`=12.0, `aromatic`=10.3, `spice`=7.0, `floral`=5.0 |

### Vapor ppm / ODT / OAV Leaders

**top window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Red Mandarin EO | 6.692234 | 0.010000 | 669.2 |
| Bergamot FCF | 2.875401 | 0.015000 | 191.7 |
| Ethyl 2-Methylbutyrate | 0.004904 | 0.000060 | 81.7 |
| Cedrat FCF oil Sicilian | 0.979906 | 0.012000 | 81.7 |
| Linalool | 0.293727 | 0.006000 | 49.0 |
| Lavender EO | 0.606760 | 0.020000 | 30.3 |
| Ambrox Super | 0.003258 | 0.000300 | 10.9 |
| Hedione | 0.157289 | 0.020000 | 7.9 |

**heart window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Ethyl 2-Methylbutyrate | 0.034597 | 0.000060 | 576.6 |
| Bergamot FCF | 4.466739 | 0.015000 | 297.8 |
| Linalool | 1.162377 | 0.006000 | 193.7 |
| Cedrat FCF oil Sicilian | 2.039669 | 0.012000 | 170.0 |
| Lavender EO | 2.529626 | 0.020000 | 126.5 |
| Ambrox Super | 0.026691 | 0.000300 | 89.0 |
| Hedione | 1.271799 | 0.020000 | 63.6 |
| Linalyl Acetate | 0.917749 | 0.050000 | 18.4 |

**base window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Ethyl 2-Methylbutyrate | 0.006681 | 0.000060 | 111.3 |
| Ambrox Super | 0.031764 | 0.000300 | 105.9 |
| Hedione | 1.291117 | 0.020000 | 64.6 |
| Iso E Super | 0.164222 | 0.010000 | 16.4 |
| Habanolide | 0.010695 | 0.001000 | 10.7 |
| Timberol | 0.024126 | 0.003000 | 8.0 |
| Hexyl Acetate | 0.015832 | 0.002000 | 7.9 |
| Eugenol | 0.042119 | 0.006000 | 7.0 |

### Mixing Order

| Step | Phase | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---|---|---:|---:|
| 1 | Foundation | Ambrox Super | 30% | 1018 | 1.018 |
| 2 | Foundation | Iso E Super | neat | 542 | 0.542 |
| 3 | Foundation | Vanillin | 10% | 370 | 0.370 |
| 4 | Foundation | Habanolide | neat | 256 | 0.256 |
| 5 | Foundation | Ethyl Vanillin | 10% | 201 | 0.201 |
| 6 | Foundation | Sandalore | neat | 169 | 0.169 |
| 7 | Foundation | Ethylene Brassylate | neat | 127 | 0.127 |
| 8 | Foundation | Coumarin | 20% | 111 | 0.111 |
| 9 | Foundation | Timberol | neat | 93 | 0.093 |
| 10 | Foundation | Ambrettolide | 10% | 84 | 0.084 |
| 11 | Foundation | Azarbre | neat | 84 | 0.084 |
| 12 | Foundation | Benzoin Resinoid | 50% | 51 | 0.051 |
| 13 | Foundation | Norlimbanol Dextro | neat | 13 | 0.013 |
| 14 | Heart Bridge | Hedione | neat | 1413 | 1.413 |
| 15 | Heart Bridge | Alpha Isomethyl Ionone | neat | 204 | 0.204 |
| 16 | Heart Bridge | Benzyl Acetate | neat | 63 | 0.063 |
| 17 | Heart Bridge | Phenethyl Alcohol | neat | 42 | 0.042 |
| 18 | Heart Bridge | Geraniol | neat | 34 | 0.034 |
| 19 | Heart Bridge | Dihydrojasmone | neat | 25 | 0.025 |
| 20 | Aromatic Support | Terpinyl Acetate | neat | 156 | 0.156 |
| 21 | Aromatic Support | Linalyl Acetate | neat | 101 | 0.101 |
| 22 | Aromatic Support | Lavender EO | neat | 93 | 0.093 |
| 23 | Aromatic Support | Ethyl Linalool | neat | 76 | 0.076 |
| 24 | Aromatic Support | Linalool | neat | 42 | 0.042 |
| 25 | Top Impact | Bergamot FCF | neat | 211 | 0.211 |
| 26 | Top Impact | Apritone | 10% | 135 | 0.135 |
| 27 | Top Impact | Red Mandarin EO | neat | 106 | 0.106 |
| 28 | Top Impact | Cedrat FCF oil Sicilian | neat | 84 | 0.084 |
| 29 | Top Impact | Hexyl Acetate | 10% | 56 | 0.056 |
| 30 | Top Impact | Ethyl 2-Methylbutyrate | 10% prep | 25 | 0.025 |
| 31 | Top Impact | Eugenol | neat | 15 | 0.015 |
| 32 | Final Dilution | Ethanol 96% bottle fill | neat | 24000 | 24.000 |

1. Add foundation materials first so the amber-wood-musk-vanilla body is fully homogeneous.
2. Add the heart bridge next to connect diffusion, floral lift, and powdery volume into the base.
3. Add aromatic support after the body is clear and uniform.
4. Add the top-impact materials last to preserve freshness and the apple-citrus-cardamom-like effect.
5. Rest 48 hours before first read; judge seriously after 14-21 days.

## 3. Tropical Night Layton Intense

*Warm night-market amber: transparent cardamom apple, polished vanilla, dry sandalwood musk.*

**Market logic:** Evening/date variant for humid weather: richer than the fresh version, but drier than v4 by using woods, musks, and transparent cardamom-like aromatics instead of simply adding resin.

**Perfumer-readable verdict:** This is the most Layton-like of the three: the opening should say apple spice, the heart should turn radiant amber, and the base should be vanilla sandalwood with restraint rather than sticky benzoin syrup.

**Family archetype:** `layton_dna.night_intense`

**Optimizer score:** `-67.803 -> -54.201` (`+13.602`)

### Release Gate Audit

**Gate status:** `WARN`
**Commercial readiness:** `COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE`
**Family archetype:** `layton_dna.night_intense`
**Commercial mode:** `True`
**Commercial confidence policy:** `warn`
**IFRA headroom:** `80%` (configured `80%`)
**Audit event:** `not logged`
**Confidence:** `LOW` (46.2 combined)

### Calibration Summary

Records `0`, wear observations `0`, panel results `0`, ready `False`

| Gate | Status | Detail |
|---|---:|---|
| exact_subtotal | PASS | 6000.0 uL |
| duplicate_canonical_materials | PASS | - |
| material_spine_coverage | PASS | - |
| physics_data_coverage | PASS | - |
| odt_coverage | PASS | - |
| chemistry_stability | PASS | predicted shelf life 896 days |
| phase_compatibility | WARN | phase tension: Vanillin RED 1.73 at 1.5% |
| opaque_preblends | PASS | - |
| blocked_materials | PASS | - |
| pipette_floor_neat_traces | PASS | - |
| small_diluted_traces | PASS | - |
| oav_scaling_guard | PASS | not requested |
| safety_ifra_allergen | WARN | 11 materials lack explicit IFRA Cat4 limits; 4 EU allergen declarations |
| perfumer_logic | PASS | layton_dna.night_intense |
| family_drift_detector | PASS | layton_dna.night_intense; no family drift |
| novelty_vs_reference | PASS | Night intense Layton DNA-inspired trial; novelty judged against Layton DNA transparency rather than fougere reference |
| oav_legibility | PASS | 22 perceptible materials |
| sensory_overcrowding | PASS | 10 perceptible channels |
| master_perfumer_gate | PASS | coherent, buildable, and readable |
| robustness_perturbation | PASS | 60 subtotal-preserving perturbations stable |
| confidence_minimum | WARN | combined confidence 46.2; commercial-trial warning, not sellable until calibrated |

### Repair History

No repair actions were needed after the optimizer pass.

### Gate Time-Series OAV Leaders

- `opening` (0s): Red Mandarin EO OAV=7617.9 ppm=76.178812, Bergamot FCF OAV=1889.8 ppm=28.347492, Linalool OAV=1197.4 ppm=7.184509, Ethyl 2-Methylbutyrate OAV=1007.1 ppm=0.060427, Cedrat FCF oil Sicilian OAV=805.0 ppm=9.660527
- `top` (300s): Red Mandarin EO OAV=7026.8 ppm=70.267965, Bergamot FCF OAV=1865.3 ppm=27.979146, Linalool OAV=1191.6 ppm=7.149630, Ethyl 2-Methylbutyrate OAV=1011.2 ppm=0.060671, Cedrat FCF oil Sicilian OAV=796.7 ppm=9.560732
- `heart` (1800s): Red Mandarin EO OAV=4671.5 ppm=46.714847, Bergamot FCF OAV=1739.5 ppm=26.092468, Linalool OAV=1157.8 ppm=6.946858, Ethyl 2-Methylbutyrate OAV=1027.2 ppm=0.061631, Cedrat FCF oil Sicilian OAV=753.1 ppm=9.037006
- `late_heart` (7200s): Bergamot FCF OAV=1303.6 ppm=19.554404, Ethyl 2-Methylbutyrate OAV=1047.3 ppm=0.062838, Red Mandarin EO OAV=1035.2 ppm=10.352494, Linalool OAV=1005.6 ppm=6.033552, Cedrat FCF oil Sicilian OAV=592.4 ppm=7.109249
- `drydown` (14400s): Ethyl 2-Methylbutyrate OAV=1035.1 ppm=0.062106, Bergamot FCF OAV=854.7 ppm=12.820171, Linalool OAV=802.2 ppm=4.813107, Cedrat FCF oil Sicilian OAV=414.4 ppm=4.972399, Lavender EO OAV=239.3 ppm=4.785389

### Optimized Formula - 30 mL EDP

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Ambrox Super | 30% | 1095 | 1.095 |
| 2 | Hedione | neat | 783 | 0.783 |
| 3 | Vanillin | 10% | 584 | 0.584 |
| 4 | Iso E Super | neat | 416 | 0.416 |
| 5 | Habanolide | neat | 293 | 0.293 |
| 6 | Ethyl Vanillin | 10% | 277 | 0.277 |
| 7 | Bergamot FCF | neat | 208 | 0.208 |
| 8 | Sandalore | neat | 208 | 0.208 |
| 9 | Terpinyl Acetate | neat | 198 | 0.198 |
| 10 | Alpha Isomethyl Ionone | neat | 182 | 0.182 |
| 11 | Benzoin Resinoid | 50% | 180 | 0.180 |
| 12 | Coumarin | 20% | 164 | 0.164 |
| 13 | Apritone | 10% | 143 | 0.143 |
| 14 | Romandolide | neat | 125 | 0.125 |
| 15 | Red Mandarin EO | neat | 121 | 0.121 |
| 16 | Cashmeran | neat | 106 | 0.106 |
| 17 | Linalyl Acetate | neat | 104 | 0.104 |
| 18 | Azarbre | neat | 104 | 0.104 |
| 19 | Lavender EO | neat | 100 | 0.100 |
| 20 | Ambrettolide | 10% | 92 | 0.092 |
| 21 | Linalool | neat | 91 | 0.091 |
| 22 | Cedrat FCF oil Sicilian | neat | 83 | 0.083 |
| 23 | Ethyl Linalool | neat | 75 | 0.075 |
| 24 | Timberol | neat | 75 | 0.075 |
| 25 | Hexyl Acetate | 10% | 61 | 0.061 |
| 26 | Benzyl Acetate | neat | 37 | 0.037 |
| 27 | Phenethyl Alcohol | neat | 33 | 0.033 |
| 28 | Ethyl 2-Methylbutyrate | 10% prep | 31 | 0.031 |
| 29 | Norlimbanol Dextro | neat | 19 | 0.019 |
| 30 | Eugenol | neat | 12 | 0.012 |
| - | **Fragrance concentrate subtotal** | - | **6000** | **6.000** |
| - | Ethanol 96% bottle fill | neat | **24000** | **24.000** |
| - | **Final bottle total** | - | **30000** | **30.000** |

### Active Neat-Equivalent View

| Material | Raw concentrate % | Active neat-equivalent % of concentrate |
|---|---:|---:|
| Ambrox Super | 18.249 | 5.475 |
| Hedione | 13.051 | 13.051 |
| Vanillin | 9.733 | 0.973 |
| Iso E Super | 6.933 | 6.933 |
| Habanolide | 4.888 | 4.888 |
| Ethyl Vanillin | 4.618 | 0.462 |
| Bergamot FCF | 3.466 | 3.466 |
| Sandalore | 3.466 | 3.466 |
| Terpinyl Acetate | 3.301 | 3.301 |
| Alpha Isomethyl Ionone | 3.041 | 3.041 |
| Benzoin Resinoid | 3.000 | 1.500 |
| Coumarin | 2.737 | 0.547 |
| Apritone | 2.384 | 0.238 |
| Romandolide | 2.080 | 2.080 |
| Red Mandarin EO | 2.017 | 2.017 |
| Cashmeran | 1.764 | 1.764 |
| Linalyl Acetate | 1.733 | 1.733 |
| Azarbre | 1.733 | 1.733 |
| Lavender EO | 1.664 | 1.664 |
| Ambrettolide | 1.525 | 0.153 |
| Linalool | 1.521 | 1.521 |
| Cedrat FCF oil Sicilian | 1.387 | 1.387 |
| Ethyl Linalool | 1.248 | 1.248 |
| Timberol | 1.248 | 1.248 |
| Hexyl Acetate | 1.009 | 0.101 |
| Benzyl Acetate | 0.624 | 0.624 |
| Phenethyl Alcohol | 0.555 | 0.555 |
| Ethyl 2-Methylbutyrate | 0.520 | 0.052 |
| Norlimbanol Dextro | 0.312 | 0.312 |
| Eugenol | 0.194 | 0.194 |

### Family OAV Envelope

| Window | Optimized family OAV |
|---|---|
| top | `citrus`=1037.6, `aromatic`=144.2, `fruity`=102.8, `amber`=11.8, `wood`=7.3, `radiance`=4.4, `spice`=1.5, `musk`=1.3 |
| heart | `fruity`=775.3, `aromatic`=606.9, `citrus`=427.9, `amber`=103.8, `wood`=63.5, `radiance`=38.2, `spice`=12.2, `musk`=11.5 |
| base | `fruity`=133.1, `amber`=123.1, `wood`=67.8, `radiance`=38.1, `musk`=13.8, `aromatic`=11.2, `spice`=5.6, `gourmand`=4.0 |

### Vapor ppm / ODT / OAV Leaders

**top window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Red Mandarin EO | 7.664455 | 0.010000 | 766.4 |
| Bergamot FCF | 2.852080 | 0.015000 | 190.1 |
| Linalool | 0.639079 | 0.006000 | 106.5 |
| Ethyl 2-Methylbutyrate | 0.006080 | 0.000060 | 101.3 |
| Cedrat FCF oil Sicilian | 0.971959 | 0.012000 | 81.0 |
| Lavender EO | 0.656551 | 0.020000 | 32.8 |
| Ambrox Super | 0.003525 | 0.000300 | 11.8 |
| Cashmeran | 0.010416 | 0.002000 | 5.2 |

**heart window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Ethyl 2-Methylbutyrate | 0.045756 | 0.000060 | 762.6 |
| Linalool | 2.575896 | 0.006000 | 429.3 |
| Bergamot FCF | 4.022128 | 0.015000 | 268.1 |
| Cedrat FCF oil Sicilian | 1.917175 | 0.012000 | 159.8 |
| Lavender EO | 2.801291 | 0.020000 | 140.1 |
| Ambrox Super | 0.031110 | 0.000300 | 103.7 |
| Cashmeran | 0.090925 | 0.002000 | 45.5 |
| Hedione | 0.763925 | 0.020000 | 38.2 |

**base window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Ethyl 2-Methylbutyrate | 0.007451 | 0.000060 | 124.2 |
| Ambrox Super | 0.036887 | 0.000300 | 123.0 |
| Cashmeran | 0.094254 | 0.002000 | 47.1 |
| Hedione | 0.761956 | 0.020000 | 38.1 |
| Iso E Super | 0.135596 | 0.010000 | 13.6 |
| Habanolide | 0.013227 | 0.001000 | 13.2 |
| Hexyl Acetate | 0.017722 | 0.002000 | 8.9 |
| Timberol | 0.021026 | 0.003000 | 7.0 |

### Mixing Order

| Step | Phase | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---|---|---:|---:|
| 1 | Foundation | Ambrox Super | 30% | 1095 | 1.095 |
| 2 | Foundation | Vanillin | 10% | 584 | 0.584 |
| 3 | Foundation | Iso E Super | neat | 416 | 0.416 |
| 4 | Foundation | Habanolide | neat | 293 | 0.293 |
| 5 | Foundation | Ethyl Vanillin | 10% | 277 | 0.277 |
| 6 | Foundation | Sandalore | neat | 208 | 0.208 |
| 7 | Foundation | Benzoin Resinoid | 50% | 180 | 0.180 |
| 8 | Foundation | Coumarin | 20% | 164 | 0.164 |
| 9 | Foundation | Romandolide | neat | 125 | 0.125 |
| 10 | Foundation | Cashmeran | neat | 106 | 0.106 |
| 11 | Foundation | Azarbre | neat | 104 | 0.104 |
| 12 | Foundation | Ambrettolide | 10% | 92 | 0.092 |
| 13 | Foundation | Timberol | neat | 75 | 0.075 |
| 14 | Foundation | Norlimbanol Dextro | neat | 19 | 0.019 |
| 15 | Heart Bridge | Hedione | neat | 783 | 0.783 |
| 16 | Heart Bridge | Alpha Isomethyl Ionone | neat | 182 | 0.182 |
| 17 | Heart Bridge | Benzyl Acetate | neat | 37 | 0.037 |
| 18 | Heart Bridge | Phenethyl Alcohol | neat | 33 | 0.033 |
| 19 | Aromatic Support | Terpinyl Acetate | neat | 198 | 0.198 |
| 20 | Aromatic Support | Linalyl Acetate | neat | 104 | 0.104 |
| 21 | Aromatic Support | Lavender EO | neat | 100 | 0.100 |
| 22 | Aromatic Support | Linalool | neat | 91 | 0.091 |
| 23 | Aromatic Support | Ethyl Linalool | neat | 75 | 0.075 |
| 24 | Top Impact | Bergamot FCF | neat | 208 | 0.208 |
| 25 | Top Impact | Apritone | 10% | 143 | 0.143 |
| 26 | Top Impact | Red Mandarin EO | neat | 121 | 0.121 |
| 27 | Top Impact | Cedrat FCF oil Sicilian | neat | 83 | 0.083 |
| 28 | Top Impact | Hexyl Acetate | 10% | 61 | 0.061 |
| 29 | Top Impact | Ethyl 2-Methylbutyrate | 10% prep | 31 | 0.031 |
| 30 | Top Impact | Eugenol | neat | 12 | 0.012 |
| 31 | Final Dilution | Ethanol 96% bottle fill | neat | 24000 | 24.000 |

1. Add foundation materials first so the amber-wood-musk-vanilla body is fully homogeneous.
2. Add the heart bridge next to connect diffusion, floral lift, and powdery volume into the base.
3. Add aromatic support after the body is clear and uniform.
4. Add the top-impact materials last to preserve freshness and the apple-citrus-cardamom-like effect.
5. Rest 48 hours before first read; judge seriously after 14-21 days.

