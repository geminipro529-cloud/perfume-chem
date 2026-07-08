# Cobalt Cedar Air — Optimized (Longevity + Projection + Smell, Cedar-First, No DHM Boost)

**Date:** 2026-05-03  
**Method:** constrained local-search optimizer with smell-preservation guardrail  (max drift 250 µL, step sizes 25 µL / 50 µL).
**DHM directive:** locked at original dose — user saving DHM for sport cologne project.

## Guardrails

- Total concentrate locked at `5.920 mL`.
- No new materials introduced; original roster of 34 materials kept.
- Max drift from original: `250 µL` (~4.2 % of concentrate).
- Key character materials (Ambrox Super, Iso E Super, Sandalore, Ginger, Pink Pepper) protected by tight drift.

## Weighted Axes

| Axis | Weight | Maps to |
|---|---|---|
| longevity | 1.0 | MW + fixative load — core target |
| projection (sillage) | 1.0 | VP + boosters — core target |
| smell (hedonic) | 1.0 | intrinsic pleasantness — core target |
| skin performance | 1.0 | reservoir kinetics — longevity contributor |
| perceptual clarity | 0.5 | mixture suppression — smell clarity |
| luxury | 0.3 | ingredient quality |
| texture | 0.3 | haptic / creamy / silky |
| depth (stacking) | 0.3 | structural layering |
| synergy | 0.2 | pairing-rule hits |
| photorealism | 0.2 | glass-like definition |

## Score Summary

**Geometric total:** `72.8` → `74.1` (`+1.3`)

| Axis | Original | Optimized | Delta |
|---|---|---|---|
| longevity | 89.1 | 88.8 | -0.3 |
| sillage | 86.5 | 92.5 | +6.0 |
| luxury | 43.2 | 43.2 | +0.0 |
| texture | 82.8 | 83.0 | +0.2 |
| stacking_depth | 71.0 | 71.0 | +0.0 |
| hedonic | 83.5 | 83.9 | +0.4 |
| synergy | 95.0 | 95.0 | +0.0 |
| skin_performance | 45.9 | 47.4 | +1.5 |
| perceptual_clarity | 73.3 | 73.3 | +0.0 |
| photorealism | 79.6 | 79.9 | +0.3 |

**Main shifts:** Patchouli EO -0.100 mL; Beta-Pinene +0.075 mL; Norlimbanol Dextro -0.025 mL; Lime Distilled EO +0.025 mL; Geraniol +0.025 mL

## Optimized Formula

| Material | Original µL | Optimized µL | Delta µL |
|---|---:|---:|---:|
| Iso E Super | 850 | 850 | +0 |
| Ambrofix | 800 | 800 | +0 |
| Cedarwood Virginia | 400 | 400 | +0 |
| Cedrat FCF Sicilian | 380 | 380 | +0 |
| Galaxolide | 380 | 380 | +0 |
| Sandalore | 350 | 350 | +0 |
| Ethylene Brassylate | 230 | 230 | +0 |
| Habanolide | 220 | 220 | +0 |
| Ebanol | 210 | 210 | +0 |
| Hedione | 200 | 200 | +0 |
| Vetiver EO | 200 | 200 | +0 |
| Cashmeran | 200 | 200 | +0 |
| Benzoin Resinoid | 200 | 200 | +0 |
| Patchouli EO | 130 | 30 | -100 |
| Lime Distilled EO | 120 | 145 | +25 |
| Polysantol | 120 | 120 | +0 |
| Dihydromyrcenol | 100 | 100 | +0 |
| Lavender EO | 100 | 100 | +0 |
| Geraniol | 100 | 125 | +25 |
| Floralozone | 80 | 80 | +0 |
| Timberol | 80 | 80 | +0 |
| Azarbre | 80 | 80 | +0 |
| Coumarin | 60 | 60 | +0 |
| Linalyl Acetate | 50 | 50 | +0 |
| Norlimbanol Dextro | 50 | 25 | -25 |
| Olibanum Resinoid | 50 | 50 | +0 |
| Aldehyde C11 undecylenic | 40 | 40 | +0 |
| Methyl Pamplemousse | 30 | 30 | +0 |
| Hedione HC | 30 | 30 | +0 |
| Vertofix | 25 | 25 | +0 |
| Beta-Pinene | 15 | 90 | +75 |
| Evernyl | 15 | 15 | +0 |
| Nagarmotha Oil | 15 | 15 | +0 |
| Scentenal | 10 | 10 | +0 |
| **Ethanol 96 %** | **24080** | **24080** | **0** |

## Optimizer Moves

- Iter 1: shifted 0.050 mL from Cashmeran → Beta-Pinene  (total 72.8 → 73.6,  longevity 89.1 → 89.0,  sillage 86.5 → 91.2)
- Iter 2: shifted 0.050 mL from Patchouli EO → Geraniol  (total 73.6 → 73.9,  longevity 89.0 → 88.9,  sillage 91.2 → 92.2)
- Iter 3: shifted 0.025 mL from Ebanol → Beta-Pinene  (total 73.9 → 74.0,  longevity 88.9 → 88.9,  sillage 92.2 → 92.8)
- Iter 4: shifted 0.050 mL from Ethylene Brassylate → Cashmeran  (total 74.0 → 74.1,  longevity 88.9 → 88.7,  sillage 92.8 → 92.8)
- Iter 5: shifted 0.025 mL from Patchouli EO → Ebanol  (total 74.1 → 74.1,  longevity 88.7 → 88.7,  sillage 92.8 → 92.8)
- Iter 6: shifted 0.025 mL from Patchouli EO → Ethylene Brassylate  (total 74.1 → 74.1,  longevity 88.7 → 88.7,  sillage 92.8 → 92.8)
- Iter 7: shifted 0.025 mL from Geraniol → Lime Distilled EO  (total 74.1 → 74.1,  longevity 88.7 → 88.8,  sillage 92.8 → 92.5)
- Iter 8: shifted 0.025 mL from Norlimbanol Dextro → Ethylene Brassylate  (total 74.1 → 74.1,  longevity 88.8 → 88.8,  sillage 92.5 → 92.5)

## Build Rule

1. Blend the optimized concentrate first (base → heart → top).
2. Add `24.08 mL` ethanol 96 %.
3. Rest 4 weeks before serious judgement.
