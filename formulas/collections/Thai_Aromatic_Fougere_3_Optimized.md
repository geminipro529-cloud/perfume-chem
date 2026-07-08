# Thai Aromatic Fougere - 3 Optimized 30 mL EDPs

**Status:** Commercial-trial candidates when generated with `--commercial-trial`; not sellable until calibrated with real wear-test records.

These are final 30 mL EDP builds at 20% concentrate: 6.00 mL concentrate plus 24.00 mL ethanol.
Optimization used final-solution evaporation snapshots rather than static concentrate percentages.

Layton classification note: Layton is treated here as an amber-floral / oriental-floral masculine, not a true aromatic fougere. The fougeres below borrow only the mass-appeal lesson: freshness plus comfort, with sweetness controlled for Thai heat.
Exploration order: build Andaman Mineral Fougere first for the new modern direction, Bangkok Tonka Fougere second for mass appeal, and keep Siam Barber Citrus as the reference/control.

## Optimization Model

- Final EDP liquid model: 80% ethanol plus 20% raw concentrate.
- Diluted stocks are handled as active material plus low-volatility carrier.
- Vapor ppm comes from modified Raoult headspace inside the evaporation trajectory.
- OAV = vapor ppm / ODT ppm, using `engine/odor_thresholds.py`.
- Target windows: top ~1 min, heart ~30 min, base ~4 hr.

## 1. Siam Barber Citrus

*Bright office-safe aromatic fougere: bergamot rind, lavender-clary foam, dry vetiver moss.*

**Market logic:** Reference/control build for a classical barbershop fougere: fast freshness, low sticky sweetness, clean musks, and a recognizable lavender-coumarin-moss fougere frame.

**Family archetype:** `aromatic_fougere.classic_reference`

**Optimizer score:** `-50.397 -> -35.275` (`+15.122`)

### Release Gate Audit

**Gate status:** `WARN`
**Commercial readiness:** `COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE`
**Family archetype:** `aromatic_fougere.classic_reference`
**Commercial mode:** `True`
**Commercial confidence policy:** `warn`
**IFRA headroom:** `80%` (configured `80%`)
**Audit event:** `not logged`
**Confidence:** `LOW` (48.1 combined)

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
| phase_compatibility | WARN | phase tension: Coumarin RED 1.29 at 1.2% |
| opaque_preblends | PASS | - |
| blocked_materials | PASS | - |
| pipette_floor_neat_traces | PASS | - |
| small_diluted_traces | PASS | - |
| oav_scaling_guard | PASS | not requested |
| safety_ifra_allergen | WARN | 5 materials lack explicit IFRA Cat4 limits; 3 EU allergen declarations |
| perfumer_logic | PASS | aromatic_fougere.classic_reference |
| family_drift_detector | PASS | aromatic_fougere.classic_reference; no family drift |
| novelty_vs_reference | WARN | reference/control archetype; familiar by design, not the new exploration target |
| oav_legibility | PASS | 21 perceptible materials |
| sensory_overcrowding | PASS | 11 perceptible channels |
| master_perfumer_gate | PASS | coherent, buildable, and readable |
| robustness_perturbation | PASS | 46 subtotal-preserving perturbations stable |
| confidence_minimum | WARN | combined confidence 48.1; commercial-trial warning, not sellable until calibrated |

### Repair History

| Pass | Gate | Action | Material | Change | Effect |
|---:|---|---|---|---:|---|
| 1 | robustness_perturbation | cap_robustness_safety_margin | Evernyl | 21.271754 -> 16.271754 uL | SAFER: Material-up perturbation of 5.000 uL caused safety failure; cap uses min(current-delta=16.272, headroom-cap=24.000). |
| 1 | robustness_perturbation | rebalance_displaced_volume | Iso E Super | 828.315113 -> 829.630903 uL | SAFER: Received 1.316 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Vetiver EO | 193.273526 -> 194.260369 uL | SAFER: Received 0.987 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Patchouli EO | 124.247267 -> 125.036741 uL | SAFER: Received 0.789 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Cedarwood oil Virginia | 310.618167 -> 311.276062 uL | SAFER: Received 0.658 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Habanolide | 414.157557 -> 414.683872 uL | SAFER: Received 0.526 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Hexyl Salicylate | 276.105038 -> 276.499775 uL | SAFER: Received 0.395 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Ambrox Super | 161.037732 -> 161.366679 uL | SAFER: Received 0.329 uL displaced from a hard gate repair. |

### Gate Time-Series OAV Leaders

- `opening` (0s): Grapefruit FCF OAV=10304.7 ppm=51.523458, Dihydromyrcenol OAV=6734.6 ppm=6.734640, Bergamot FCF OAV=2045.4 ppm=30.680622, Cedrat FCF oil Sicilian OAV=891.1 ppm=10.693261, Linalool OAV=867.6 ppm=5.205484
- `top` (300s): Grapefruit FCF OAV=9506.1 ppm=47.530741, Dihydromyrcenol OAV=6725.7 ppm=6.725691, Bergamot FCF OAV=2019.1 ppm=30.287023, Cedrat FCF oil Sicilian OAV=882.0 ppm=10.584594, Linalool OAV=863.5 ppm=5.180755
- `heart` (1800s): Dihydromyrcenol OAV=6655.7 ppm=6.655668, Grapefruit FCF OAV=6327.0 ppm=31.634755, Bergamot FCF OAV=1885.7 ppm=28.285299, Linalool OAV=839.9 ppm=5.039344, Cedrat FCF oil Sicilian OAV=834.9 ppm=10.019275
- `late_heart` (7200s): Dihydromyrcenol OAV=6200.0 ppm=6.199968, Bergamot FCF OAV=1426.0 ppm=21.390284, Grapefruit FCF OAV=1413.3 ppm=7.066573, Linalool OAV=735.0 ppm=4.410166, Cedrat FCF oil Sicilian OAV=662.8 ppm=7.953909
- `drydown` (14400s): Dihydromyrcenol OAV=5438.1 ppm=5.438096, Bergamot FCF OAV=947.2 ppm=14.208602, Linalool OAV=592.8 ppm=3.556796, Cedrat FCF oil Sicilian OAV=469.7 ppm=5.636811, Lavender EO OAV=402.0 ppm=8.039298

### Optimized Formula - 30 mL EDP

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Hedione | neat | 968 | 0.968 |
| 2 | Iso E Super | neat | 830 | 0.830 |
| 3 | Habanolide | neat | 415 | 0.415 |
| 4 | Linalyl Acetate | neat | 345 | 0.345 |
| 5 | Coumarin | 20% | 345 | 0.345 |
| 6 | Bergamot FCF | neat | 321 | 0.321 |
| 7 | Cedarwood oil Virginia | neat | 311 | 0.311 |
| 8 | Hexyl Salicylate | neat | 276 | 0.276 |
| 9 | Romandolide | neat | 242 | 0.242 |
| 10 | Lavender EO | neat | 233 | 0.233 |
| 11 | Clary Sage EO | neat | 207 | 0.207 |
| 12 | Ethyl Linalool | neat | 207 | 0.207 |
| 13 | Vetiver EO | neat | 194 | 0.194 |
| 14 | Dihydromyrcenol | neat | 175 | 0.175 |
| 15 | Ambrox Super | 30% | 161 | 0.161 |
| 16 | Galaxolide | 80% | 159 | 0.159 |
| 17 | Cedrat FCF oil Sicilian | neat | 131 | 0.131 |
| 18 | Patchouli EO | neat | 125 | 0.125 |
| 19 | Grapefruit FCF | neat | 117 | 0.117 |
| 20 | Geraniol | neat | 98 | 0.098 |
| 21 | Linalool | neat | 93 | 0.093 |
| 22 | cis-3-Hexenol | neat | 31 | 0.031 |
| 23 | Evernyl | neat | 16 | 0.016 |
| - | **Fragrance concentrate subtotal** | - | **6000** | **6.000** |
| - | Ethanol 96% bottle fill | neat | **24000** | **24.000** |
| - | **Final bottle total** | - | **30000** | **30.000** |

### Family OAV Envelope

| Window | Optimized family OAV |
|---|---|
| top | `citrus`=1839.3, `fresh`=935.5, `aromatic`=206.3, `green`=26.1, `radiance`=5.2, `wood`=4.0, `geranium`=3.1, `musk`=1.8 |
| heart | `fresh`=4490.3, `aromatic`=942.5, `citrus`=812.7, `radiance`=41.4, `wood`=31.5, `geranium`=22.5, `musk`=14.2, `amber`=13.4 |
| base | `radiance`=46.4, `aromatic`=42.5, `wood`=40.3, `musk`=19.0, `amber`=17.7, `cushion`=10.7, `coumarin`=6.8, `geranium`=6.7 |

### Vapor ppm / ODT / OAV Leaders

**top window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Grapefruit FCF | 7.156856 | 0.005000 | 1431.4 |
| Dihydromyrcenol | 0.935474 | 0.001000 | 935.5 |
| Bergamot FCF | 4.261686 | 0.015000 | 284.1 |
| Cedrat FCF oil Sicilian | 1.485345 | 0.012000 | 123.8 |
| Linalool | 0.633219 | 0.006000 | 105.5 |
| Lavender EO | 1.486430 | 0.020000 | 74.3 |
| cis-3-Hexenol | 1.828326 | 0.070000 | 26.1 |
| Clary Sage EO | 0.259238 | 0.015000 | 17.3 |

**heart window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Dihydromyrcenol | 4.490347 | 0.001000 | 4490.3 |
| Bergamot FCF | 7.821261 | 0.015000 | 521.4 |
| Linalool | 2.615187 | 0.006000 | 435.9 |
| Lavender EO | 6.431461 | 0.020000 | 321.6 |
| Cedrat FCF oil Sicilian | 3.494890 | 0.012000 | 291.2 |
| Clary Sage EO | 1.806113 | 0.015000 | 120.4 |
| Linalyl Acetate | 3.010189 | 0.050000 | 60.2 |
| Hedione | 0.828581 | 0.020000 | 41.4 |

**base window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Hedione | 0.928332 | 0.020000 | 46.4 |
| Iso E Super | 0.264655 | 0.010000 | 26.5 |
| Clary Sage EO | 0.366074 | 0.015000 | 24.4 |
| Habanolide | 0.018242 | 0.001000 | 18.2 |
| Ambrox Super | 0.005307 | 0.000300 | 17.7 |
| Linalyl Acetate | 0.610124 | 0.050000 | 12.2 |
| Hexyl Salicylate | 0.032232 | 0.003000 | 10.7 |
| Cedarwood oil Virginia | 0.113872 | 0.015000 | 7.6 |

### Mixing Order

| Step | Phase | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---|---|---:|---:|
| 1 | Foundation | Iso E Super | neat | 830 | 0.830 |
| 2 | Foundation | Habanolide | neat | 415 | 0.415 |
| 3 | Foundation | Coumarin | 20% | 345 | 0.345 |
| 4 | Foundation | Cedarwood oil Virginia | neat | 311 | 0.311 |
| 5 | Foundation | Hexyl Salicylate | neat | 276 | 0.276 |
| 6 | Foundation | Romandolide | neat | 242 | 0.242 |
| 7 | Foundation | Vetiver EO | neat | 194 | 0.194 |
| 8 | Foundation | Ambrox Super | 30% | 161 | 0.161 |
| 9 | Foundation | Galaxolide | 80% | 159 | 0.159 |
| 10 | Foundation | Patchouli EO | neat | 125 | 0.125 |
| 11 | Foundation | Evernyl | neat | 16 | 0.016 |
| 12 | Heart Bridge | Hedione | neat | 968 | 0.968 |
| 13 | Heart Bridge | Geraniol | neat | 98 | 0.098 |
| 14 | Aromatic Support | Linalyl Acetate | neat | 345 | 0.345 |
| 15 | Aromatic Support | Lavender EO | neat | 233 | 0.233 |
| 16 | Aromatic Support | Clary Sage EO | neat | 207 | 0.207 |
| 17 | Aromatic Support | Ethyl Linalool | neat | 207 | 0.207 |
| 18 | Aromatic Support | Linalool | neat | 93 | 0.093 |
| 19 | Top Impact | Bergamot FCF | neat | 321 | 0.321 |
| 20 | Top Impact | Dihydromyrcenol | neat | 175 | 0.175 |
| 21 | Top Impact | Cedrat FCF oil Sicilian | neat | 131 | 0.131 |
| 22 | Top Impact | Grapefruit FCF | neat | 117 | 0.117 |
| 23 | Top Impact | cis-3-Hexenol | neat | 31 | 0.031 |
| 24 | Final Dilution | Ethanol 96% bottle fill | neat | 24000 | 24.000 |

1. Add foundation materials first so the moss-wood-musk body and coumarin cushion are fully integrated.
2. Add the heart bridge next to lock the fougere body into the base before the fresh top goes on.
3. Add aromatic support once the concentrate is uniform.
4. Add the top-impact materials last to preserve lift, freshness, and volatility.
5. Rest 48 hours before first read; judge seriously after 14 days.

## 2. Andaman Mineral Fougere

*Marine-green aromatic fougere: grapefruit spray, lavender metal, clear cedar musk.*

**Market logic:** A humid-climate fresh masculine direction: SEA-friendly aquatic lift, but with lavender, coumarin, moss, and vetiver to keep it fougere rather than shower gel.

**Family archetype:** `aromatic_fougere.modern_mineral`

**Optimizer score:** `-82.489 -> -56.255` (`+26.233`)

### Release Gate Audit

**Gate status:** `WARN`
**Commercial readiness:** `COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE`
**Family archetype:** `aromatic_fougere.modern_mineral`
**Commercial mode:** `True`
**Commercial confidence policy:** `warn`
**IFRA headroom:** `80%` (configured `80%`)
**Audit event:** `not logged`
**Confidence:** `LOW` (47.4 combined)

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
| safety_ifra_allergen | WARN | 7 materials lack explicit IFRA Cat4 limits; 3 EU allergen declarations |
| perfumer_logic | PASS | aromatic_fougere.modern_mineral |
| family_drift_detector | PASS | aromatic_fougere.modern_mineral; no family drift |
| novelty_vs_reference | PASS | mineral/fresh signature 11.02% raw; target >= 3.00 for meaningful modernity |
| oav_legibility | PASS | 23 perceptible materials |
| sensory_overcrowding | PASS | 13 perceptible channels |
| master_perfumer_gate | PASS | coherent, buildable, and readable |
| robustness_perturbation | PASS | 52 subtotal-preserving perturbations stable |
| confidence_minimum | WARN | combined confidence 47.4; commercial-trial warning, not sellable until calibrated |

### Repair History

| Pass | Gate | Action | Material | Change | Effect |
|---:|---|---|---|---:|---|
| 1 | robustness_perturbation | cap_robustness_safety_margin | Evernyl | 20.686719 -> 15.686719 uL | SAFER: Material-up perturbation of 5.000 uL caused safety failure; cap uses min(current-delta=15.687, headroom-cap=24.000). |
| 1 | robustness_perturbation | rebalance_displaced_volume | Iso E Super | 965.380226 -> 966.942726 uL | SAFER: Received 1.562 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Vetiver EO | 165.493753 -> 166.665628 uL | SAFER: Received 1.172 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Cedarwood EO | 330.987506 -> 331.768756 uL | SAFER: Received 0.781 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Habanolide | 275.822922 -> 276.447922 uL | SAFER: Received 0.625 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Hexyl Salicylate | 234.449483 -> 234.918233 uL | SAFER: Received 0.469 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Ambrox Super | 251.605863 -> 251.996488 uL | SAFER: Received 0.391 uL displaced from a hard gate repair. |

### Gate Time-Series OAV Leaders

- `opening` (0s): Grapefruit FCF OAV=19080.1 ppm=95.400505, Dihydromyrcenol OAV=14251.2 ppm=14.251219, Bergamot FCF OAV=1672.3 ppm=25.084071, Linalool OAV=1007.5 ppm=6.044820, Cedrat FCF oil Sicilian OAV=838.1 ppm=10.056926
- `top` (300s): Grapefruit FCF OAV=17625.7 ppm=88.128496, Dihydromyrcenol OAV=14253.0 ppm=14.253025, Bergamot FCF OAV=1653.2 ppm=24.798056, Linalool OAV=1004.2 ppm=6.024966, Cedrat FCF oil Sicilian OAV=830.8 ppm=9.969140
- `heart` (1800s): Dihydromyrcenol OAV=14186.7 ppm=14.186698, Grapefruit FCF OAV=11794.3 ppm=58.971734, Bergamot FCF OAV=1552.8 ppm=23.292430, Linalool OAV=982.5 ppm=5.894883, Cedrat FCF oil Sicilian OAV=790.9 ppm=9.491153
- `late_heart` (7200s): Dihydromyrcenol OAV=13342.4 ppm=13.342435, Grapefruit FCF OAV=2655.9 ppm=13.279736, Bergamot FCF OAV=1185.3 ppm=17.779969, Linalool OAV=868.0 ppm=5.207864, Cedrat FCF oil Sicilian OAV=633.8 ppm=7.605819
- `drydown` (14400s): Dihydromyrcenol OAV=11758.0 ppm=11.758010, Bergamot FCF OAV=790.8 ppm=11.862592, Linalool OAV=703.0 ppm=4.218016, Calone OAV=532.6 ppm=0.005326, Cedrat FCF oil Sicilian OAV=451.2 ppm=5.414300

### Optimized Formula - 30 mL EDP

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Hedione | neat | 1033 | 1.033 |
| 2 | Iso E Super | neat | 967 | 0.967 |
| 3 | Dihydromyrcenol | neat | 350 | 0.350 |
| 4 | Romandolide | neat | 345 | 0.345 |
| 5 | Cedarwood EO | neat | 332 | 0.332 |
| 6 | Habanolide | neat | 276 | 0.276 |
| 7 | Ambrox Super | 30% | 252 | 0.252 |
| 8 | Bergamot FCF | neat | 248 | 0.248 |
| 9 | Hexyl Salicylate | neat | 235 | 0.235 |
| 10 | Grapefruit FCF | neat | 204 | 0.204 |
| 11 | Coumarin | 20% | 193 | 0.193 |
| 12 | Clary Sage EO | neat | 172 | 0.172 |
| 13 | Vetiver EO | neat | 167 | 0.167 |
| 14 | Lavender EO | neat | 160 | 0.160 |
| 15 | Galaxolide | 80% | 152 | 0.152 |
| 16 | Floralozone | 10% | 125 | 0.125 |
| 17 | Cedrat FCF oil Sicilian | neat | 117 | 0.117 |
| 18 | Calone | 1% | 117 | 0.117 |
| 19 | Linalool | neat | 102 | 0.102 |
| 20 | Phenethyl Alcohol | neat | 94 | 0.094 |
| 21 | Methyl Pamplemousse | 10% | 87 | 0.087 |
| 22 | Geraniol | neat | 83 | 0.083 |
| 23 | Scentenal | 1% | 70 | 0.070 |
| 24 | Cashmeran | neat | 55 | 0.055 |
| 25 | Nympheal | neat | 48 | 0.048 |
| 26 | Evernyl | neat | 16 | 0.016 |
| - | **Fragrance concentrate subtotal** | - | **6000** | **6.000** |
| - | Ethanol 96% bottle fill | neat | **24000** | **24.000** |
| - | **Final bottle total** | - | **30000** | **30.000** |

### Family OAV Envelope

| Window | Optimized family OAV |
|---|---|
| top | `citrus`=2847.7, `fresh`=1879.7, `aromatic`=181.8, `marine`=62.6, `fruity`=10.3, `wood`=7.4, `floral`=5.8, `radiance`=5.6 |
| heart | `fresh`=9069.2, `aromatic`=805.1, `citrus`=657.8, `marine`=477.5, `wood`=59.6, `fruity`=58.5, `radiance`=45.1, `floral`=41.0 |
| base | `marine`=292.5, `wood`=72.5, `radiance`=50.0, `floral`=30.0, `amber`=27.9, `aromatic`=19.7, `musk`=13.1, `cushion`=9.2 |

### Vapor ppm / ODT / OAV Leaders

**top window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Grapefruit FCF | 12.582967 | 0.005000 | 2516.6 |
| Dihydromyrcenol | 1.879682 | 0.001000 | 1879.7 |
| Bergamot FCF | 3.308494 | 0.015000 | 220.6 |
| Linalool | 0.695817 | 0.006000 | 116.0 |
| Cedrat FCF oil Sicilian | 1.326471 | 0.012000 | 110.5 |
| Calone | 0.000599 | 0.000010 | 59.9 |
| Lavender EO | 1.026692 | 0.020000 | 51.3 |
| Clary Sage EO | 0.217040 | 0.015000 | 14.5 |

**heart window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Dihydromyrcenol | 9.069160 | 0.001000 | 9069.2 |
| Linalool | 2.882025 | 0.006000 | 480.3 |
| Calone | 0.004594 | 0.000010 | 459.4 |
| Bergamot FCF | 5.994057 | 0.015000 | 399.6 |
| Cedrat FCF oil Sicilian | 3.098307 | 0.012000 | 258.2 |
| Lavender EO | 4.458315 | 0.020000 | 222.9 |
| Clary Sage EO | 1.527391 | 0.015000 | 101.8 |
| Methyl Pamplemousse | 0.175422 | 0.003000 | 58.5 |

**base window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Calone | 0.002889 | 0.000010 | 288.9 |
| Hedione | 0.999820 | 0.020000 | 50.0 |
| Iso E Super | 0.311250 | 0.010000 | 31.1 |
| Nympheal | 0.059826 | 0.002000 | 29.9 |
| Ambrox Super | 0.008369 | 0.000300 | 27.9 |
| Cashmeran | 0.048702 | 0.002000 | 24.4 |
| Clary Sage EO | 0.294847 | 0.015000 | 19.7 |
| Cedarwood EO | 0.196152 | 0.015000 | 13.1 |

### Mixing Order

| Step | Phase | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---|---|---:|---:|
| 1 | Foundation | Iso E Super | neat | 967 | 0.967 |
| 2 | Foundation | Romandolide | neat | 345 | 0.345 |
| 3 | Foundation | Cedarwood EO | neat | 332 | 0.332 |
| 4 | Foundation | Habanolide | neat | 276 | 0.276 |
| 5 | Foundation | Ambrox Super | 30% | 252 | 0.252 |
| 6 | Foundation | Hexyl Salicylate | neat | 235 | 0.235 |
| 7 | Foundation | Coumarin | 20% | 193 | 0.193 |
| 8 | Foundation | Vetiver EO | neat | 167 | 0.167 |
| 9 | Foundation | Galaxolide | 80% | 152 | 0.152 |
| 10 | Foundation | Cashmeran | neat | 55 | 0.055 |
| 11 | Foundation | Evernyl | neat | 16 | 0.016 |
| 12 | Heart Bridge | Hedione | neat | 1033 | 1.033 |
| 13 | Heart Bridge | Phenethyl Alcohol | neat | 94 | 0.094 |
| 14 | Heart Bridge | Geraniol | neat | 83 | 0.083 |
| 15 | Heart Bridge | Nympheal | neat | 48 | 0.048 |
| 16 | Aromatic Support | Clary Sage EO | neat | 172 | 0.172 |
| 17 | Aromatic Support | Lavender EO | neat | 160 | 0.160 |
| 18 | Aromatic Support | Linalool | neat | 102 | 0.102 |
| 19 | Top Impact | Dihydromyrcenol | neat | 350 | 0.350 |
| 20 | Top Impact | Bergamot FCF | neat | 248 | 0.248 |
| 21 | Top Impact | Grapefruit FCF | neat | 204 | 0.204 |
| 22 | Top Impact | Floralozone | 10% | 125 | 0.125 |
| 23 | Top Impact | Calone | 1% | 117 | 0.117 |
| 24 | Top Impact | Cedrat FCF oil Sicilian | neat | 117 | 0.117 |
| 25 | Top Impact | Methyl Pamplemousse | 10% | 87 | 0.087 |
| 26 | Top Impact | Scentenal | 1% | 70 | 0.070 |
| 27 | Final Dilution | Ethanol 96% bottle fill | neat | 24000 | 24.000 |

1. Add foundation materials first so the moss-wood-musk body and coumarin cushion are fully integrated.
2. Add the heart bridge next to lock the fougere body into the base before the fresh top goes on.
3. Add aromatic support once the concentrate is uniform.
4. Add the top-impact materials last to preserve lift, freshness, and volatility.
5. Rest 48 hours before first read; judge seriously after 14 days.

## 3. Bangkok Tonka Fougere

*Mass-appeal sweet aromatic fougere: mandarin-lavender, apple-tonka, polished woods.*

**Market logic:** Uses the Layton lesson, not the Layton family: a small fruity-spiced hook over a real lavender-coumarin-moss fougere body, with sweetness capped for heat.

**Family archetype:** `aromatic_fougere.modern_tonka_mass`

**Optimizer score:** `-75.708 -> -51.943` (`+23.765`)

### Release Gate Audit

**Gate status:** `WARN`
**Commercial readiness:** `COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE`
**Family archetype:** `aromatic_fougere.modern_tonka_mass`
**Commercial mode:** `True`
**Commercial confidence policy:** `warn`
**IFRA headroom:** `80%` (configured `80%`)
**Audit event:** `not logged`
**Confidence:** `LOW` (46.6 combined)

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
| phase_compatibility | WARN | HSP coverage too thin for trusted phase audit: 37.1% active mass across 7 materials |
| opaque_preblends | PASS | - |
| blocked_materials | PASS | - |
| pipette_floor_neat_traces | PASS | - |
| small_diluted_traces | PASS | - |
| oav_scaling_guard | PASS | not requested |
| safety_ifra_allergen | WARN | 7 materials lack explicit IFRA Cat4 limits; 4 EU allergen declarations |
| perfumer_logic | PASS | aromatic_fougere.modern_tonka_mass |
| family_drift_detector | PASS | aromatic_fougere.modern_tonka_mass; no family drift |
| novelty_vs_reference | PASS | fruit/tonka mass hook 1.21% active; target >= 0.25 for meaningful modernity |
| oav_legibility | PASS | 25 perceptible materials |
| sensory_overcrowding | PASS | 10 perceptible channels |
| master_perfumer_gate | PASS | coherent, buildable, and readable |
| robustness_perturbation | PASS | 58 subtotal-preserving perturbations stable |
| confidence_minimum | WARN | combined confidence 46.6; commercial-trial warning, not sellable until calibrated |

### Repair History

| Pass | Gate | Action | Material | Change | Effect |
|---:|---|---|---|---:|---|
| 1 | robustness_perturbation | cap_robustness_safety_margin | Evernyl | 19.993143 -> 14.993143 uL | SAFER: Material-up perturbation of 5.000 uL caused safety failure; cap uses min(current-delta=14.993, headroom-cap=24.000). |
| 1 | robustness_perturbation | rebalance_displaced_volume | Iso E Super | 655.664281 -> 656.997615 uL | SAFER: Received 1.333 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Vetiver EO | 131.132856 -> 132.132856 uL | SAFER: Received 1.000 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Patchouli EO | 144.246142 -> 145.046142 uL | SAFER: Received 0.800 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Cedarwood oil Virginia | 209.81257 -> 210.479237 uL | SAFER: Received 0.667 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Habanolide | 327.832141 -> 328.365474 uL | SAFER: Received 0.533 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Ambrox Super | 196.699284 -> 197.032618 uL | SAFER: Received 0.333 uL displaced from a hard gate repair. |
| 1 | robustness_perturbation | rebalance_displaced_volume | Sandalore | 196.699284 -> 197.032618 uL | SAFER: Received 0.333 uL displaced from a hard gate repair. |

### Gate Time-Series OAV Leaders

- `opening` (0s): Grapefruit FCF OAV=8073.1 ppm=40.365382, Red Mandarin EO OAV=6727.6 ppm=67.275637, Dihydromyrcenol OAV=5276.2 ppm=5.276166, Ethyl 2-Methylbutyrate OAV=2415.2 ppm=0.144914, Bergamot FCF OAV=1553.9 ppm=23.307960
- `top` (300s): Grapefruit FCF OAV=7463.0 ppm=37.315014, Red Mandarin EO OAV=6219.2 ppm=62.191690, Dihydromyrcenol OAV=5279.8 ppm=5.279849, Ethyl 2-Methylbutyrate OAV=2430.3 ppm=0.145819, Bergamot FCF OAV=1537.1 ppm=23.055830
- `heart` (1800s): Dihydromyrcenol OAV=5264.9 ppm=5.264946, Grapefruit FCF OAV=5006.6 ppm=25.033037, Red Mandarin EO OAV=4172.2 ppm=41.721729, Ethyl 2-Methylbutyrate OAV=2491.4 ppm=0.149486, Bergamot FCF OAV=1446.5 ppm=21.698039
- `late_heart` (7200s): Dihydromyrcenol OAV=4943.7 ppm=4.943651, Ethyl 2-Methylbutyrate OAV=2584.3 ppm=0.155059, Grapefruit FCF OAV=1128.5 ppm=5.642279, Bergamot FCF OAV=1102.8 ppm=16.542331, Red Mandarin EO OAV=940.4 ppm=9.403799
- `drydown` (14400s): Dihydromyrcenol OAV=4323.0 ppm=4.322990, Ethyl 2-Methylbutyrate OAV=2580.7 ppm=0.154842, Bergamot FCF OAV=730.5 ppm=10.957117, Lavender EO OAV=654.3 ppm=13.085045, Linalool OAV=489.5 ppm=2.936927

### Optimized Formula - 30 mL EDP

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Hedione | neat | 818 | 0.818 |
| 2 | Iso E Super | neat | 657 | 0.657 |
| 3 | Coumarin | 20% | 400 | 0.400 |
| 4 | Lavender EO | neat | 340 | 0.340 |
| 5 | Habanolide | neat | 328 | 0.328 |
| 6 | Linalyl Acetate | neat | 328 | 0.328 |
| 7 | Bergamot FCF | neat | 222 | 0.222 |
| 8 | Cedarwood oil Virginia | neat | 210 | 0.210 |
| 9 | Sandalore | neat | 197 | 0.197 |
| 10 | Ambrox Super | 30% | 197 | 0.197 |
| 11 | Ethyl Linalool | neat | 197 | 0.197 |
| 12 | Romandolide | neat | 197 | 0.197 |
| 13 | Ethylene Brassylate | neat | 197 | 0.197 |
| 14 | Ethyl Vanillin | 10% | 197 | 0.197 |
| 15 | Vanillin | 10% | 164 | 0.164 |
| 16 | Apritone | 10% | 151 | 0.151 |
| 17 | Patchouli EO | neat | 145 | 0.145 |
| 18 | Clary Sage EO | neat | 144 | 0.144 |
| 19 | Red Mandarin EO | neat | 139 | 0.139 |
| 20 | Vetiver EO | neat | 132 | 0.132 |
| 21 | Geraniol | neat | 131 | 0.131 |
| 22 | Dihydromyrcenol | neat | 125 | 0.125 |
| 23 | Hexyl Acetate | 10% | 118 | 0.118 |
| 24 | Grapefruit FCF | neat | 83 | 0.083 |
| 25 | Linalool | neat | 69 | 0.069 |
| 26 | Citronellol | neat | 66 | 0.066 |
| 27 | cis-3-Hexenol | neat | 23 | 0.023 |
| 28 | Evernyl | neat | 15 | 0.015 |
| 29 | Ethyl 2-Methylbutyrate | neat | 10 | 0.010 |
| - | **Fragrance concentrate subtotal** | - | **6000** | **6.000** |
| - | Ethanol 96% bottle fill | neat | **24000** | **24.000** |
| - | **Final bottle total** | - | **30000** | **30.000** |

### Family OAV Envelope

| Window | Optimized family OAV |
|---|---|
| top | `citrus`=2084.0, `fresh`=672.3, `fruity`=310.6, `aromatic`=209.3, `green`=19.5, `geranium`=6.6, `radiance`=4.5, `wood`=3.1 |
| heart | `fresh`=3196.8, `fruity`=2157.4, `aromatic`=936.3, `citrus`=352.9, `geranium`=46.6, `radiance`=35.4, `wood`=24.6, `amber`=16.5 |
| base | `fruity`=446.7, `radiance`=40.2, `aromatic`=34.2, `wood`=31.9, `amber`=22.1, `musk`=16.5, `geranium`=13.0, `coumarin`=8.1 |

### Vapor ppm / ODT / OAV Leaders

**top window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Grapefruit FCF | 5.143602 | 0.005000 | 1028.7 |
| Red Mandarin EO | 8.572670 | 0.010000 | 857.3 |
| Dihydromyrcenol | 0.672321 | 0.001000 | 672.3 |
| Ethyl 2-Methylbutyrate | 0.018466 | 0.000060 | 307.8 |
| Bergamot FCF | 2.970042 | 0.015000 | 198.0 |
| Lavender EO | 2.187192 | 0.020000 | 109.4 |
| Linalool | 0.474054 | 0.006000 | 79.0 |
| cis-3-Hexenol | 1.362677 | 0.070000 | 19.5 |

**heart window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Dihydromyrcenol | 3.196771 | 0.001000 | 3196.8 |
| Ethyl 2-Methylbutyrate | 0.128131 | 0.000060 | 2135.5 |
| Lavender EO | 9.358429 | 0.020000 | 467.9 |
| Bergamot FCF | 5.294009 | 0.015000 | 352.9 |
| Linalool | 1.934573 | 0.006000 | 322.4 |
| Clary Sage EO | 1.264062 | 0.015000 | 84.3 |
| Linalyl Acetate | 2.872868 | 0.050000 | 57.5 |
| Hedione | 0.707194 | 0.020000 | 35.4 |

**base window**

| Material | Vapor ppm | ODT ppm | OAV |
|---|---:|---:|---:|
| Ethyl 2-Methylbutyrate | 0.025731 | 0.000060 | 428.8 |
| Hedione | 0.803173 | 0.020000 | 40.2 |
| Ambrox Super | 0.006625 | 0.000300 | 22.1 |
| Iso E Super | 0.214176 | 0.010000 | 21.4 |
| Hexyl Acetate | 0.035455 | 0.002000 | 17.7 |
| Clary Sage EO | 0.253846 | 0.015000 | 16.9 |
| Habanolide | 0.014771 | 0.001000 | 14.8 |
| Linalyl Acetate | 0.576922 | 0.050000 | 11.5 |

### Mixing Order

| Step | Phase | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---|---|---:|---:|
| 1 | Foundation | Iso E Super | neat | 657 | 0.657 |
| 2 | Foundation | Coumarin | 20% | 400 | 0.400 |
| 3 | Foundation | Habanolide | neat | 328 | 0.328 |
| 4 | Foundation | Cedarwood oil Virginia | neat | 210 | 0.210 |
| 5 | Foundation | Ambrox Super | 30% | 197 | 0.197 |
| 6 | Foundation | Ethyl Vanillin | 10% | 197 | 0.197 |
| 7 | Foundation | Ethylene Brassylate | neat | 197 | 0.197 |
| 8 | Foundation | Romandolide | neat | 197 | 0.197 |
| 9 | Foundation | Sandalore | neat | 197 | 0.197 |
| 10 | Foundation | Vanillin | 10% | 164 | 0.164 |
| 11 | Foundation | Patchouli EO | neat | 145 | 0.145 |
| 12 | Foundation | Vetiver EO | neat | 132 | 0.132 |
| 13 | Foundation | Evernyl | neat | 15 | 0.015 |
| 14 | Heart Bridge | Hedione | neat | 818 | 0.818 |
| 15 | Heart Bridge | Geraniol | neat | 131 | 0.131 |
| 16 | Heart Bridge | Citronellol | neat | 66 | 0.066 |
| 17 | Aromatic Support | Lavender EO | neat | 340 | 0.340 |
| 18 | Aromatic Support | Linalyl Acetate | neat | 328 | 0.328 |
| 19 | Aromatic Support | Ethyl Linalool | neat | 197 | 0.197 |
| 20 | Aromatic Support | Clary Sage EO | neat | 144 | 0.144 |
| 21 | Aromatic Support | Linalool | neat | 69 | 0.069 |
| 22 | Top Impact | Bergamot FCF | neat | 222 | 0.222 |
| 23 | Top Impact | Apritone | 10% | 151 | 0.151 |
| 24 | Top Impact | Red Mandarin EO | neat | 139 | 0.139 |
| 25 | Top Impact | Dihydromyrcenol | neat | 125 | 0.125 |
| 26 | Top Impact | Hexyl Acetate | 10% | 118 | 0.118 |
| 27 | Top Impact | Grapefruit FCF | neat | 83 | 0.083 |
| 28 | Top Impact | cis-3-Hexenol | neat | 23 | 0.023 |
| 29 | Top Impact | Ethyl 2-Methylbutyrate | neat | 10 | 0.010 |
| 30 | Final Dilution | Ethanol 96% bottle fill | neat | 24000 | 24.000 |

1. Add foundation materials first so the moss-wood-musk body and coumarin cushion are fully integrated.
2. Add the heart bridge next to lock the fougere body into the base before the fresh top goes on.
3. Add aromatic support once the concentrate is uniform.
4. Add the top-impact materials last to preserve lift, freshness, and volatility.
5. Rest 48 hours before first read; judge seriously after 14 days.

