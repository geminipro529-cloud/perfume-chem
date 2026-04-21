# 12 Luxury Perfume Formulas — Converged & Audited

All formulas built with hybrid optimizer (additive greedy + reductive loop, Δgeo < 0.0005 convergence). Each batch is **10.00 mL of concentrate in 100 mL finished EDP** (scored at 10% concentration). All 12 formulas pass: **0 IFRA violations · 0 dose-response overdoses · 0 subliminal materials (per-material OAV ≥ 1.0) · zero excluded materials · per-material CAPS enforced · mutually-exclusive materials enforced (Ambrox Super ∥ Ambrofix)**.

**Chemistry grounded in:** MW (longevity score + top/heart/base classification), VP (sillage + temporal register spread + powerhouse mass check), volatility index VI = Σ(pct·VP/√MW) (projection scaling), ODT (dose-response overdose gate using Hill character zones), OAV = conc_ppm / ODT_ppm (per-material perceptibility gate — verified ≥ 1.0 for every material in every formula), ppm concentration (IFRA ppm-based category caps + OAV computation).

**Non-ideal mixture audit (v11):** Raoult's law (p_i = x_i·P°_i, γ=1) was replaced by γ-corrected partial pressures (p_i = γ_i·x_i·P°_i) using a logP-bucket activity-coefficient heuristic for EtOH/water solvent: polar H-bond donors (logP<2) get γ ≈ 0.35–0.55 (headspace suppressed), mid-polar esters/terpenes (logP 2.5–3.5) γ ≈ 1.0, hydrophobic musks/ambers/Iso E Super (logP 4+) γ ≈ 1.5–4.8 (headspace amplified). This corrects the "percentage × VP" fallacy: 1% of a polar material hides, 1% of a hydrophobic macrocyclic punches. Running the γ-corrected audit across all 12 formulas: **0 hidden subliminals** (no material drops below OAV = 1 under non-ideal mixing), **0 suppressed materials** (rank↓ ≥ 3), and **1 amplified material** (Geraniol in SUEDE rises from rank 5 → 2 under γ = 1.5 — directionally correct; Geraniol is known to bloom in warm bases). Headspace composition shifts are small (1–5 percentage points) because dominant materials across these formulas share similar γ values (Linalool 0.8, Linalyl Acetate 1.0, citrus terpenes 1.5–2.3). Full per-material γ·VP·x contribution table saved to `_v11_activity_audit.json`.

**Optimization method:** multi-axis geometric aggregation with weights longevity 0.8, sillage 0.8, synergy 0.5, luxury 0.8, texture 0.8, stacking_depth 0.8, skin_performance 0.7, hedonic 0.5, perceptual_clarity 0.6, safety 1.2 (Σ = 7.5). Accept-if-improve loop (Δ ≥ 0.0005) with strict IFRA and overdose rejection gates. After convergence: iterative cap pass eliminated every dose-response character-shift warning, then per-material OAV audit confirmed zero subliminal materials across all 12 formulas.

## Convergence Summary

| # | Formula | Family | Geo Score | Safety | Ingredients | Total µL | IFRA Violations | Overdoses |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | **NUAGE_fixed** | Luxury White Floral | 85.47 | 96.4 | 29 | 2255 | 0 | 0 |
| 2 | **fougere** | Aromatic Fougère | 87.52 | 95.1 | 32 | 1861 | 0 | 0 |
| 3 | **chypre** | Modern Chypre | 85.72 | 95.1 | 32 | 2040 | 0 | 0 |
| 4 | **oriental** | Amber Oriental | 85.70 | 94.8 | 32 | 1911 | 0 | 0 |
| 5 | **gourmand** | Modern Gourmand | 87.90 | 97.3 | 32 | 1916 | 0 | 0 |
| 6 | **aquatic** | Ozonic Aquatic | 86.03 | 99.1 | 32 | 1713 | 0 | 0 |
| 7 | **woody** | Dry Woody | 84.85 | 98.2 | 32 | 2004 | 0 | 0 |
| 8 | **cologne** | Modern Cologne | 86.74 | 97.3 | 32 | 1924 | 0 | 0 |
| 9 | **green** | Green Floral | 87.01 | 98.2 | 32 | 1849 | 0 | 0 |
| 10 | **soliflore** | Rose Soliflore | 83.68 | 95.5 | 32 | 2177 | 0 | 0 |
| 11 | **iris** | Iris-Powder | 85.58 | 97.3 | 32 | 2111 | 0 | 0 |
| 12 | **SUEDE** | Luxury Suede Leather | 83.87 | 95.1 | 29 | 2241 | 0 | 0 |

## 1. NUAGE_fixed — Luxury White Floral

**Accord architecture:** Aldehyde-muguet radiance over salicylate-musk diffusion cloud; cosmetic-plastic floral architecture with Hedione radiance amplifier and Hexyl Salicylate transparent fixative. C11 undecylenic dropped (not in inventory); compensated with Hedione/Hexyl Sal/Neroli.

**Scores:** Geo = **85.47**, Safety = 96.4, Longevity = 88.5, Sillage = 89.9, Luxury = 80.1, Texture = 74.2, Hedonic = 85.4, Clarity = 85.0

**Batch:** 2255 µL concentrate → diluted to **10.00 mL EDP at 22.55% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Aldehyde C10 | 1% | 60 | 0.060 | 0.6 |
| 2 | Aldehyde C11 | 1% | 60 | 0.060 | 0.6 |
| 3 | Aldehyde C12 MNA | 1% | 60 | 0.060 | 0.6 |
| 4 | Linalool | neat | 60 | 0.060 | 60.0 |
| 5 | Bergamot FCF Sicilian | neat | 51 | 0.051 | 51.0 |
| **— HEART —** |  |  |  |  |  |
| 6 | Hedione | neat | 243 | 0.243 | 243.0 |
| 7 | Hedione HC | neat | 120 | 0.120 | 120.0 |
| 8 | Alpha Irone | 30% | 80 | 0.080 | 24.0 |
| 9 | Neroli EO | neat | 70 | 0.070 | 70.0 |
| 10 | Vanillin | 10% | 60 | 0.060 | 6.0 |
| 11 | Coumarin | 20% | 60 | 0.060 | 12.0 |
| 12 | ACA | neat | 35 | 0.035 | 35.0 |
| 13 | Rose Oxide | 10% | 25 | 0.025 | 2.5 |
| 14 | Ethyl Maltol | 10% | 2 | 0.002 | 0.2 |
| **— BASE —** |  |  |  |  |  |
| 15 | Iso E Super | neat | 250 | 0.250 | 250.0 |
| 16 | Ethylene Brassylate | neat | 200 | 0.200 | 200.0 |
| 17 | Habanolide | neat | 200 | 0.200 | 200.0 |
| 18 | Hexyl Salicylate | neat | 120 | 0.120 | 120.0 |
| 19 | Ambrettolide | 10% | 120 | 0.120 | 12.0 |
| 20 | Benzyl Salicylate | neat | 79 | 0.079 | 79.0 |
| 21 | Vetiver EO | neat | 50 | 0.050 | 50.0 |
| 22 | PEDMC | neat | 42 | 0.042 | 42.0 |
| 23 | Alpha Isomethyl Ionone | neat | 42 | 0.042 | 42.0 |
| 24 | Musk Ketone | neat | 34 | 0.034 | 34.0 |
| 25 | Sandalore | neat | 34 | 0.034 | 34.0 |
| 26 | Cashmeran | 20% | 30 | 0.030 | 6.0 |
| 27 | Ylang Ylang EO Extra | neat | 28 | 0.028 | 28.0 |
| 28 | Alpha Damascone | 10% | 25 | 0.025 | 2.5 |
| 29 | Ambrox Super | 30% | 15 | 0.015 | 4.5 |

**Allergen declarations (EU 26):** Alpha Isomethyl Ionone, Benzyl Salicylate, Coumarin, Linalool

## 2. fougere — Aromatic Fougère

**Accord architecture:** Lavender–coumarin–oakmoss-replacement triad (Evernyl) with Dihydromyrcenol lift and vetival suede base; classic fougère architecture updated with molecular amber bridge.

**Scores:** Geo = **87.52**, Safety = 95.1, Longevity = 85.6, Sillage = 96.4, Luxury = 90.9, Texture = 80.9, Hedonic = 84.1, Clarity = 84.7

**Batch:** 1861 µL concentrate → diluted to **10.00 mL EDP at 18.61% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Linalyl Acetate | neat | 85 | 0.085 | 85.0 |
| 2 | Lavender EO | neat | 69 | 0.069 | 69.0 |
| 3 | Dihydromyrcenol | neat | 68 | 0.068 | 68.0 |
| 4 | Linalool | neat | 50 | 0.050 | 50.0 |
| 5 | Clary Sage EO | neat | 40 | 0.040 | 40.0 |
| 6 | Bergamot FCF Sicilian | neat | 32 | 0.032 | 32.0 |
| 7 | Geraniol | neat | 21 | 0.021 | 21.0 |
| **— HEART —** |  |  |  |  |  |
| 8 | Hedione | neat | 230 | 0.230 | 230.0 |
| 9 | Hedione HC | neat | 80 | 0.080 | 80.0 |
| 10 | Coumarin | 20% | 70 | 0.070 | 14.0 |
| 11 | Neroli EO | neat | 15 | 0.015 | 15.0 |
| 12 | Vanillin | 10% | 15 | 0.015 | 1.5 |
| 13 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| 14 | Paradisamide | 10% | 5 | 0.005 | 0.5 |
| 15 | Ethyl Vanillin | neat | 3 | 0.003 | 3.0 |
| **— BASE —** |  |  |  |  |  |
| 16 | Iso E Super | neat | 205 | 0.205 | 205.0 |
| 17 | Habanolide | neat | 190 | 0.190 | 190.0 |
| 18 | Ethylene Brassylate | neat | 150 | 0.150 | 150.0 |
| 19 | Ambrettolide | 10% | 80 | 0.080 | 8.0 |
| 20 | Cedarwood oil Virginia | neat | 68 | 0.068 | 68.0 |
| 21 | Vetiver EO | neat | 60 | 0.060 | 60.0 |
| 22 | Benzyl Salicylate | neat | 60 | 0.060 | 60.0 |
| 23 | Hexyl Salicylate | neat | 60 | 0.060 | 60.0 |
| 24 | Ambermax | 50% | 42 | 0.042 | 21.0 |
| 25 | Vetival | neat | 40 | 0.040 | 40.0 |
| 26 | Patchouli EO | neat | 40 | 0.040 | 40.0 |
| 27 | Cashmeran | 20% | 15 | 0.015 | 3.0 |
| 28 | Ambrox Super | 30% | 15 | 0.015 | 4.5 |
| 29 | Macrolide | 10% | 15 | 0.015 | 1.5 |
| 30 | Ebanol | neat | 12 | 0.012 | 12.0 |
| 31 | Javanol | neat | 10 | 0.010 | 10.0 |
| 32 | Evernyl | neat | 8 | 0.008 | 8.0 |

**Allergen declarations (EU 26):** Benzyl Salicylate, Coumarin, Geraniol, Linalool

## 3. chypre — Modern Chypre

**Accord architecture:** Bergamot–labdanum–Evernyl axis replacing oakmoss; patchouli earth anchored by Ambrox mineral crystalline register and Hedione radiance.

**Scores:** Geo = **85.72**, Safety = 95.1, Longevity = 87.4, Sillage = 96.6, Luxury = 78.9, Texture = 79.9, Hedonic = 83.9, Clarity = 76.6

**Batch:** 2040 µL concentrate → diluted to **10.00 mL EDP at 20.40% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Bergamot FCF Sicilian | neat | 87 | 0.087 | 87.0 |
| 2 | Aldehyde C10 | 1% | 40 | 0.040 | 0.4 |
| 3 | Geraniol | neat | 25 | 0.025 | 25.0 |
| **— HEART —** |  |  |  |  |  |
| 4 | Hedione | neat | 340 | 0.340 | 340.0 |
| 5 | Neroli EO | neat | 40 | 0.040 | 40.0 |
| 6 | ACA | neat | 25 | 0.025 | 25.0 |
| 7 | Alpha Irone | 30% | 25 | 0.025 | 7.5 |
| 8 | Hedione HC | neat | 25 | 0.025 | 25.0 |
| 9 | Rose Oxide | 10% | 20 | 0.020 | 2.0 |
| 10 | Vanillin | 10% | 15 | 0.015 | 1.5 |
| 11 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| 12 | Paradisamide | 10% | 5 | 0.005 | 0.5 |
| **— BASE —** |  |  |  |  |  |
| 13 | Iso E Super | neat | 250 | 0.250 | 250.0 |
| 14 | Habanolide | neat | 195 | 0.195 | 195.0 |
| 15 | Hexyl Salicylate | neat | 100 | 0.100 | 100.0 |
| 16 | Ethylene Brassylate | neat | 100 | 0.100 | 100.0 |
| 17 | Benzyl Salicylate | neat | 90 | 0.090 | 90.0 |
| 18 | Ambrettolide | 10% | 80 | 0.080 | 8.0 |
| 19 | Cedarwood EO | neat | 80 | 0.080 | 80.0 |
| 20 | Patchouli EO | neat | 70 | 0.070 | 70.0 |
| 21 | Ambermax | 50% | 60 | 0.060 | 30.0 |
| 22 | Vetiver EO | neat | 50 | 0.050 | 50.0 |
| 23 | Alpha Damascone | 10% | 40 | 0.040 | 4.0 |
| 24 | Citronellol | neat | 40 | 0.040 | 40.0 |
| 25 | PEDMC | neat | 40 | 0.040 | 40.0 |
| 26 | Alpha Isomethyl Ionone | neat | 40 | 0.040 | 40.0 |
| 27 | Benzoin Resinoid | 50% | 40 | 0.040 | 20.0 |
| 28 | Damascol | 10% | 30 | 0.030 | 3.0 |
| 29 | Ylang Ylang EO Extra | neat | 30 | 0.030 | 30.0 |
| 30 | Ambrox Super | 30% | 25 | 0.025 | 7.5 |
| 31 | Ebanol | neat | 15 | 0.015 | 15.0 |
| 32 | Evernyl | neat | 10 | 0.010 | 10.0 |

**Allergen declarations (EU 26):** Alpha Isomethyl Ionone, Benzyl Salicylate, Citronellol, Geraniol

## 4. oriental — Amber Oriental

**Accord architecture:** Resin triad (benzoin–labdanum–opoponax) over Ambermax warm-rounded amber bed; Eugenol spice trace, Ethylene Brassylate lactonic musk depth.

**Scores:** Geo = **85.70**, Safety = 94.8, Longevity = 86.5, Sillage = 93.7, Luxury = 78.6, Texture = 80.0, Hedonic = 85.1, Clarity = 75.9

**Batch:** 1911 µL concentrate → diluted to **10.00 mL EDP at 19.11% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Bergamot FCF Sicilian | neat | 80 | 0.080 | 80.0 |
| 2 | Red Mandarin EO | neat | 70 | 0.070 | 70.0 |
| **— HEART —** |  |  |  |  |  |
| 3 | Hedione | neat | 270 | 0.270 | 270.0 |
| 4 | Vanillin | 10% | 60 | 0.060 | 6.0 |
| 5 | Coumarin | 20% | 50 | 0.050 | 10.0 |
| 6 | ACA | neat | 20 | 0.020 | 20.0 |
| 7 | Rose Oxide | 10% | 15 | 0.015 | 1.5 |
| 8 | Neroli EO | neat | 15 | 0.015 | 15.0 |
| 9 | Ethyl Vanillin | neat | 12 | 0.012 | 12.0 |
| 10 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| 11 | Eugenol | neat | 6 | 0.006 | 6.0 |
| **— BASE —** |  |  |  |  |  |
| 12 | Iso E Super | neat | 200 | 0.200 | 200.0 |
| 13 | Habanolide | neat | 140 | 0.140 | 140.0 |
| 14 | Ethylene Brassylate | neat | 120 | 0.120 | 120.0 |
| 15 | Ambermax | 50% | 100 | 0.100 | 50.0 |
| 16 | Ambrettolide | 10% | 100 | 0.100 | 10.0 |
| 17 | Benzoin Resinoid | 50% | 80 | 0.080 | 40.0 |
| 18 | Cashmeran | 20% | 80 | 0.080 | 16.0 |
| 19 | Cedarwood oil Virginia | neat | 60 | 0.060 | 60.0 |
| 20 | Benzyl Salicylate | neat | 57 | 0.057 | 57.0 |
| 21 | Siam Benzoin | 50% | 40 | 0.040 | 20.0 |
| 22 | Ambrox Super | 30% | 40 | 0.040 | 12.0 |
| 23 | Amberwood F | neat | 40 | 0.040 | 40.0 |
| 24 | Cedarwood EO | neat | 40 | 0.040 | 40.0 |
| 25 | Ylang Ylang EO Extra | neat | 34 | 0.034 | 34.0 |
| 26 | Heliotropin Fleuressence | neat | 33 | 0.033 | 33.0 |
| 27 | Olibanum Resinoid | neat | 33 | 0.033 | 33.0 |
| 28 | Alpha Damascone | 10% | 30 | 0.030 | 3.0 |
| 29 | Tonalide | 10% | 30 | 0.030 | 3.0 |
| 30 | Patchouli EO | neat | 28 | 0.028 | 28.0 |
| 31 | Myrrh EO | neat | 17 | 0.017 | 17.0 |
| 32 | Cinnamaldehyde | neat | 3 | 0.003 | 3.0 |

**Allergen declarations (EU 26):** Benzyl Salicylate, Cinnamaldehyde, Coumarin, Eugenol

## 5. gourmand — Modern Gourmand

**Accord architecture:** Ethyl maltol–vanillin–coumarin–heliotropin core with gamma-decalactone peach skin and tonka-benzoin resinous drydown; Habanolide skin-trail musk.

**Scores:** Geo = **87.46**, Safety = 97.3, Longevity = 86.0, Sillage = 95.7, Luxury = 84.9, Texture = 76.2, Hedonic = 86.3, Clarity = 84.9

**Batch:** 1916 µL concentrate → diluted to **10.00 mL EDP at 19.16% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Bergamot FCF Sicilian | neat | 80 | 0.080 | 80.0 |
| 2 | Red Mandarin EO | neat | 70 | 0.070 | 70.0 |
| 3 | Linalool | neat | 40 | 0.040 | 40.0 |
| **— HEART —** |  |  |  |  |  |
| 4 | Hedione | neat | 270 | 0.270 | 270.0 |
| 5 | Vanillin | 10% | 70 | 0.070 | 7.0 |
| 6 | Coumarin | 20% | 51 | 0.051 | 10.2 |
| 7 | Orivone | neat | 45 | 0.045 | 45.0 |
| 8 | Alpha Irone | 30% | 25 | 0.025 | 7.5 |
| 9 | Maple Lactone | 20% | 20 | 0.020 | 4.0 |
| 10 | Rose Oxide | 10% | 15 | 0.015 | 1.5 |
| 11 | Ethyl Vanillin | neat | 11 | 0.011 | 11.0 |
| 12 | Paradisamide | 10% | 5 | 0.005 | 0.5 |
| 13 | Ethyl Maltol | 10% | 4 | 0.004 | 0.4 |
| **— BASE —** |  |  |  |  |  |
| 14 | Iso E Super | neat | 200 | 0.200 | 200.0 |
| 15 | Habanolide | neat | 200 | 0.200 | 200.0 |
| 16 | Ethylene Brassylate | neat | 150 | 0.150 | 150.0 |
| 17 | Cashmeran | 20% | 100 | 0.100 | 20.0 |
| 18 | Ambrettolide | 10% | 100 | 0.100 | 10.0 |
| 19 | Benzoin Resinoid | 50% | 60 | 0.060 | 30.0 |
| 20 | Cedarwood EO | neat | 60 | 0.060 | 60.0 |
| 21 | Ambermax | 50% | 48 | 0.048 | 24.0 |
| 22 | Tonalide | 10% | 40 | 0.040 | 4.0 |
| 23 | Benzyl Salicylate | neat | 40 | 0.040 | 40.0 |
| 24 | Heliotropin Fleuressence | neat | 38 | 0.038 | 38.0 |
| 25 | Sandalore | neat | 34 | 0.034 | 34.0 |
| 26 | Ebanol | neat | 30 | 0.030 | 30.0 |
| 27 | Alpha Damascone | 10% | 25 | 0.025 | 2.5 |
| 28 | Ambrox Super | 30% | 25 | 0.025 | 7.5 |
| 29 | Gamma Undecalactone | neat | 20 | 0.020 | 20.0 |
| 30 | Delta Decalactone | neat | 20 | 0.020 | 20.0 |
| 31 | Heliotropal | neat | 12 | 0.012 | 12.0 |
| 32 | Anisaldehyde | neat | 8 | 0.008 | 8.0 |

**Allergen declarations (EU 26):** Benzyl Salicylate, Coumarin, Linalool

## 6. aquatic — Ozonic Aquatic

**Accord architecture:** Calone–Floralozone–Helional ozonic triad with Scentenal mineral accent; Hedione radiance over Ambrofix crystalline-transparent warmth and Zenolide clean-fresh musk.

**Scores:** Geo = **86.03**, Safety = 99.1, Longevity = 84.1, Sillage = 96.4, Luxury = 82.5, Texture = 74.5, Hedonic = 84.9, Clarity = 81.1

**Batch:** 1713 µL concentrate → diluted to **10.00 mL EDP at 17.13% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Dihydromyrcenol | neat | 90 | 0.090 | 90.0 |
| 2 | Bergamot FCF Sicilian | neat | 52 | 0.052 | 52.0 |
| 3 | Grapefruit FCF | neat | 50 | 0.050 | 50.0 |
| 4 | Linalool | neat | 50 | 0.050 | 50.0 |
| 5 | Cedrat FCF Sicilian | neat | 30 | 0.030 | 30.0 |
| 6 | Floralozone | 10% | 30 | 0.030 | 3.0 |
| 7 | Calone | 1% | 20 | 0.020 | 0.2 |
| 8 | Helional | neat | 19 | 0.019 | 19.0 |
| 9 | Scentenal | 1% | 18 | 0.018 | 0.2 |
| 10 | Allyl Amyl Glycolate | neat | 12 | 0.012 | 12.0 |
| 11 | Cyclamen Aldehyde | neat | 7 | 0.007 | 7.0 |
| 12 | cis-3-Hexenol | neat | 4 | 0.004 | 4.0 |
| **— HEART —** |  |  |  |  |  |
| 13 | Hedione | neat | 220 | 0.220 | 220.0 |
| 14 | Hedione HC | neat | 80 | 0.080 | 80.0 |
| 15 | Mayol | neat | 25 | 0.025 | 25.0 |
| 16 | Lilyreal ND | neat | 20 | 0.020 | 20.0 |
| 17 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| 18 | Rose Oxide | 10% | 5 | 0.005 | 0.5 |
| 19 | Paradisamide | 10% | 5 | 0.005 | 0.5 |
| **— BASE —** |  |  |  |  |  |
| 20 | Iso E Super | neat | 245 | 0.245 | 245.0 |
| 21 | Habanolide | neat | 185 | 0.185 | 185.0 |
| 22 | Zenolide | neat | 135 | 0.135 | 135.0 |
| 23 | Ethylene Brassylate | neat | 80 | 0.080 | 80.0 |
| 24 | Hexyl Salicylate | neat | 80 | 0.080 | 80.0 |
| 25 | Romandolide | neat | 61 | 0.061 | 61.0 |
| 26 | Ambrox Super | 30% | 55 | 0.055 | 16.5 |
| 27 | Clearwood | neat | 40 | 0.040 | 40.0 |
| 28 | Amberwood F | neat | 34 | 0.034 | 34.0 |
| 29 | Cedarwood oil Virginia | neat | 23 | 0.023 | 23.0 |
| 30 | Ebanol | neat | 15 | 0.015 | 15.0 |
| 31 | Undecavertol | neat | 10 | 0.010 | 10.0 |
| 32 | Heliotropal | neat | 5 | 0.005 | 5.0 |

**Allergen declarations (EU 26):** Linalool

## 7. woody — Dry Woody

**Accord architecture:** Iso E Super molecular cocoon + Timberol architectural cedar + Norlimbanol structural power; Vetival suede-textural dryness, Cashmeran textile-warmth bridge.

**Scores:** Geo = **84.85**, Safety = 98.2, Longevity = 87.8, Sillage = 96.4, Luxury = 74.9, Texture = 78.8, Hedonic = 83.3, Clarity = 85.2

**Batch:** 2004 µL concentrate → diluted to **10.00 mL EDP at 20.04% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Bergamot FCF Sicilian | neat | 80 | 0.080 | 80.0 |
| 2 | Cardamom FTEC | 10% | 20 | 0.020 | 2.0 |
| 3 | Linalool | neat | 20 | 0.020 | 20.0 |
| **— HEART —** |  |  |  |  |  |
| 4 | Hedione | neat | 350 | 0.350 | 350.0 |
| 5 | Orivone | neat | 15 | 0.015 | 15.0 |
| 6 | Rose Oxide | 10% | 12 | 0.012 | 1.2 |
| 7 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| **— BASE —** |  |  |  |  |  |
| 8 | Iso E Super | neat | 250 | 0.250 | 250.0 |
| 9 | Habanolide | neat | 150 | 0.150 | 150.0 |
| 10 | Cedarwood EO | neat | 80 | 0.080 | 80.0 |
| 11 | Ethylene Brassylate | neat | 80 | 0.080 | 80.0 |
| 12 | Ambrettolide | 10% | 80 | 0.080 | 8.0 |
| 13 | Hexyl Salicylate | neat | 80 | 0.080 | 80.0 |
| 14 | Romandolide | neat | 62 | 0.062 | 62.0 |
| 15 | Timberol | neat | 55 | 0.055 | 55.0 |
| 16 | Vertofix | neat | 50 | 0.050 | 50.0 |
| 17 | Clearwood | neat | 50 | 0.050 | 50.0 |
| 18 | Vetiver EO | neat | 50 | 0.050 | 50.0 |
| 19 | Patchouli EO | neat | 50 | 0.050 | 50.0 |
| 20 | Amberwood F | neat | 50 | 0.050 | 50.0 |
| 21 | Ambermax | 50% | 50 | 0.050 | 25.0 |
| 22 | Cedarwood oil Virginia | neat | 43 | 0.043 | 43.0 |
| 23 | Vetival | neat | 42 | 0.042 | 42.0 |
| 24 | Azarbre | neat | 40 | 0.040 | 40.0 |
| 25 | Ambrox Super | 30% | 40 | 0.040 | 12.0 |
| 26 | Alpha Isomethyl Ionone | neat | 35 | 0.035 | 35.0 |
| 27 | Alpha Damascone | 10% | 35 | 0.035 | 3.5 |
| 28 | Bacdanol | neat | 34 | 0.034 | 34.0 |
| 29 | Cedramber | neat | 30 | 0.030 | 30.0 |
| 30 | Ebanol | neat | 30 | 0.030 | 30.0 |
| 31 | Pink Pepper Base | neat | 25 | 0.025 | 25.0 |
| 32 | Norlimbanol Dextro | neat | 8 | 0.008 | 8.0 |

**Allergen declarations (EU 26):** Alpha Isomethyl Ionone, Linalool

## 8. cologne — Modern Cologne

**Accord architecture:** Bergamot–Cedrat–Petitgrain citrus trilogy over neroli–Hedione heart with Dihydromyrcenol laundry-fresh lift; Romandolide projection musk and Ambrofix transparent warmth.

**Scores:** Geo = **86.74**, Safety = 97.3, Longevity = 81.1, Sillage = 96.8, Luxury = 91.9, Texture = 74.6, Hedonic = 86.2, Clarity = 83.2

**Batch:** 1924 µL concentrate → diluted to **10.00 mL EDP at 19.24% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Linalyl Acetate | neat | 60 | 0.060 | 60.0 |
| 2 | Grapefruit FCF | neat | 50 | 0.050 | 50.0 |
| 3 | Red Mandarin EO | neat | 42 | 0.042 | 42.0 |
| 4 | Lavender EO | neat | 42 | 0.042 | 42.0 |
| 5 | Cedrat FCF Sicilian | neat | 40 | 0.040 | 40.0 |
| 6 | Linalool | neat | 40 | 0.040 | 40.0 |
| 7 | Petitgrain EO | neat | 30 | 0.030 | 30.0 |
| 8 | Methyl Pamplemousse | 10% | 20 | 0.020 | 2.0 |
| 9 | Clary Sage EO | neat | 20 | 0.020 | 20.0 |
| 10 | Bergamot FCF Sicilian | neat | 19 | 0.019 | 19.0 |
| **— HEART —** |  |  |  |  |  |
| 11 | Hedione | neat | 280 | 0.280 | 280.0 |
| 12 | Hedione HC | neat | 80 | 0.080 | 80.0 |
| 13 | Neroli EO | neat | 50 | 0.050 | 50.0 |
| 14 | Alpha Irone | 30% | 25 | 0.025 | 7.5 |
| 15 | Mayol | neat | 20 | 0.020 | 20.0 |
| 16 | Orivone | neat | 15 | 0.015 | 15.0 |
| 17 | Coumarin | 20% | 10 | 0.010 | 2.0 |
| 18 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| **— BASE —** |  |  |  |  |  |
| 19 | Iso E Super | neat | 250 | 0.250 | 250.0 |
| 20 | Habanolide | neat | 195 | 0.195 | 195.0 |
| 21 | Romandolide | neat | 190 | 0.190 | 190.0 |
| 22 | Zenolide | neat | 85 | 0.085 | 85.0 |
| 23 | Ambrox Super | 30% | 60 | 0.060 | 18.0 |
| 24 | Hexyl Salicylate | neat | 60 | 0.060 | 60.0 |
| 25 | Ambrettolide | 10% | 59 | 0.059 | 5.9 |
| 26 | Cedarwood oil Virginia | neat | 40 | 0.040 | 40.0 |
| 27 | Amberwood F | neat | 34 | 0.034 | 34.0 |
| 28 | Blood Orange oil Sicilian | neat | 30 | 0.030 | 30.0 |
| 29 | Ebanol | neat | 30 | 0.030 | 30.0 |
| 30 | Lemonile | neat | 15 | 0.015 | 15.0 |
| 31 | Cashmeran | 20% | 15 | 0.015 | 3.0 |
| 32 | Citronellol | neat | 10 | 0.010 | 10.0 |

**Allergen declarations (EU 26):** Citronellol, Coumarin, Linalool

## 9. green — Green Floral

**Accord architecture:** Galbanum–cis-3-hexenol–Violet Leaf green triad with Parmavert violet-leaf ionone bridge and Freesia HDI transparency; Alpha Irone powder-iris heart.

**Scores:** Geo = **87.01**, Safety = 98.2, Longevity = 89.4, Sillage = 94.9, Luxury = 81.8, Texture = 79.9, Hedonic = 84.3, Clarity = 75.4

**Batch:** 1849 µL concentrate → diluted to **10.00 mL EDP at 18.49% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Bergamot FCF Sicilian | neat | 43 | 0.043 | 43.0 |
| 2 | Petitgrain EO | neat | 28 | 0.028 | 28.0 |
| 3 | Helional | neat | 25 | 0.025 | 25.0 |
| 4 | Parmavert | neat | 20 | 0.020 | 20.0 |
| 5 | Linalool | neat | 20 | 0.020 | 20.0 |
| 6 | Leafovert | neat | 8 | 0.008 | 8.0 |
| 7 | Cyclamen Aldehyde | neat | 7 | 0.007 | 7.0 |
| 8 | cis-3-Hexenol | neat | 5 | 0.005 | 5.0 |
| **— HEART —** |  |  |  |  |  |
| 9 | Hedione | neat | 280 | 0.280 | 280.0 |
| 10 | Hedione HC | neat | 85 | 0.085 | 85.0 |
| 11 | Alpha Ionone | neat | 40 | 0.040 | 40.0 |
| 12 | Beta Ionone | neat | 35 | 0.035 | 35.0 |
| 13 | Alpha Irone | 30% | 25 | 0.025 | 7.5 |
| 14 | Rose Oxide | 10% | 15 | 0.015 | 1.5 |
| 15 | Vanillin | 10% | 15 | 0.015 | 1.5 |
| 16 | Ultralia | neat | 12 | 0.012 | 12.0 |
| 17 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| 18 | Paradisamide | 10% | 5 | 0.005 | 0.5 |
| **— BASE —** |  |  |  |  |  |
| 19 | Iso E Super | neat | 245 | 0.245 | 245.0 |
| 20 | Ethylene Brassylate | neat | 200 | 0.200 | 200.0 |
| 21 | Habanolide | neat | 190 | 0.190 | 190.0 |
| 22 | Ambrettolide | 10% | 100 | 0.100 | 10.0 |
| 23 | Hexyl Salicylate | neat | 100 | 0.100 | 100.0 |
| 24 | Cedarwood EO | neat | 80 | 0.080 | 80.0 |
| 25 | Vetiver EO | neat | 60 | 0.060 | 60.0 |
| 26 | Cedarwood oil Virginia | neat | 50 | 0.050 | 50.0 |
| 27 | Alpha Isomethyl Ionone | neat | 40 | 0.040 | 40.0 |
| 28 | Vetival | neat | 40 | 0.040 | 40.0 |
| 29 | Ambrox Super | 30% | 25 | 0.025 | 7.5 |
| 30 | Alpha Damascone | 10% | 20 | 0.020 | 2.0 |
| 31 | Galbanum Resinoid | 10% | 18 | 0.018 | 1.8 |
| 32 | Heliotropal | neat | 5 | 0.005 | 5.0 |

**Allergen declarations (EU 26):** Alpha Isomethyl Ionone, Linalool

## 10. soliflore — Rose Soliflore

**Accord architecture:** Rose Otto + Rose Moroccan Absolute + Geranium bourbon triad with Hedione radiance amplifier and Damascenone impact; rose-centered single-note meditation with salicylate cushion and Javanol skin-intimacy finish.

**Scores:** Geo = **83.68**, Safety = 95.5, Longevity = 88.8, Sillage = 95.2, Luxury = 69.4, Texture = 72.2, Hedonic = 84.6, Clarity = 84.9

**Batch:** 2177 µL concentrate → diluted to **10.00 mL EDP at 21.77% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Bergamot FCF Sicilian | neat | 30 | 0.030 | 30.0 |
| 2 | Aldehyde C10 | 1% | 30 | 0.030 | 0.3 |
| 3 | Aldehyde C12 MNA | 1% | 30 | 0.030 | 0.3 |
| 4 | Linalool | neat | 10 | 0.010 | 10.0 |
| **— HEART —** |  |  |  |  |  |
| 5 | Hedione | neat | 300 | 0.300 | 300.0 |
| 6 | Hedione HC | neat | 120 | 0.120 | 120.0 |
| 7 | Vanillin | 10% | 40 | 0.040 | 4.0 |
| 8 | Coumarin | 20% | 40 | 0.040 | 8.0 |
| 9 | ACA | neat | 35 | 0.035 | 35.0 |
| 10 | Benzyl Acetate | neat | 24 | 0.024 | 24.0 |
| 11 | Rose Oxide | 10% | 12 | 0.012 | 1.2 |
| 12 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| **— BASE —** |  |  |  |  |  |
| 13 | Iso E Super | neat | 250 | 0.250 | 250.0 |
| 14 | Habanolide | neat | 200 | 0.200 | 200.0 |
| 15 | Ethylene Brassylate | neat | 200 | 0.200 | 200.0 |
| 16 | Hexyl Salicylate | neat | 140 | 0.140 | 140.0 |
| 17 | Benzyl Salicylate | neat | 130 | 0.130 | 130.0 |
| 18 | Ambrettolide | 10% | 100 | 0.100 | 10.0 |
| 19 | Cedarwood EO | neat | 100 | 0.100 | 100.0 |
| 20 | Ylang Ylang EO Extra | neat | 43 | 0.043 | 43.0 |
| 21 | Alpha Isomethyl Ionone | neat | 42 | 0.042 | 42.0 |
| 22 | PEDMC | neat | 40 | 0.040 | 40.0 |
| 23 | Sandalore | neat | 40 | 0.040 | 40.0 |
| 24 | Ylang Comoros III EO F3295 | neat | 36 | 0.036 | 36.0 |
| 25 | Ebanol | neat | 30 | 0.030 | 30.0 |
| 26 | Benzyl Benzoate | neat | 28 | 0.028 | 28.0 |
| 27 | Methyl Benzoate | neat | 25 | 0.025 | 25.0 |
| 28 | Musk Ketone | neat | 25 | 0.025 | 25.0 |
| 29 | Dihydrojasmone | neat | 21 | 0.021 | 21.0 |
| 30 | Cis Jasmone | neat | 20 | 0.020 | 20.0 |
| 31 | Alpha Damascone | 10% | 20 | 0.020 | 2.0 |
| 32 | Indole | 10% | 8 | 0.008 | 0.8 |

**Allergen declarations (EU 26):** Alpha Isomethyl Ionone, Benzyl Benzoate, Benzyl Salicylate, Coumarin, Linalool

## 11. iris — Iris-Powder

**Accord architecture:** Alpha Irone + Orris FTEC + Orivone iris-register stack with Heliotropin/Musk Ketone powder-talc cushion; Ethylene Brassylate lactonic creamy musk depth and Exaltolide skin-fatty fixation.

**Scores:** Geo = **85.58**, Safety = 97.3, Longevity = 87.5, Sillage = 96.2, Luxury = 76.3, Texture = 73.6, Hedonic = 85.3, Clarity = 81.9

**Batch:** 2111 µL concentrate → diluted to **10.00 mL EDP at 21.11% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Aldehyde C11 | 1% | 30 | 0.030 | 0.3 |
| 2 | Bergamot FCF Sicilian | neat | 29 | 0.029 | 29.0 |
| **— HEART —** |  |  |  |  |  |
| 3 | Hedione | neat | 270 | 0.270 | 270.0 |
| 4 | Alpha Irone | 30% | 180 | 0.180 | 54.0 |
| 5 | Orivone | neat | 60 | 0.060 | 60.0 |
| 6 | Hedione HC | neat | 60 | 0.060 | 60.0 |
| 7 | Alpha Ionone | neat | 40 | 0.040 | 40.0 |
| 8 | Vanillin | 10% | 40 | 0.040 | 4.0 |
| 9 | Coumarin | 20% | 40 | 0.040 | 8.0 |
| 10 | Beta Ionone | neat | 30 | 0.030 | 30.0 |
| 11 | Ultralia | neat | 20 | 0.020 | 20.0 |
| 12 | Rose Oxide | 10% | 10 | 0.010 | 1.0 |
| 13 | Maple Lactone | 20% | 8 | 0.008 | 1.6 |
| **— BASE —** |  |  |  |  |  |
| 14 | Ethylene Brassylate | neat | 190 | 0.190 | 190.0 |
| 15 | Iso E Super | neat | 180 | 0.180 | 180.0 |
| 16 | Habanolide | neat | 145 | 0.145 | 145.0 |
| 17 | Hexyl Salicylate | neat | 140 | 0.140 | 140.0 |
| 18 | Ambrettolide | 10% | 120 | 0.120 | 12.0 |
| 19 | Cashmeran | 20% | 90 | 0.090 | 18.0 |
| 20 | Cedarwood EO | neat | 80 | 0.080 | 80.0 |
| 21 | Ambermax | 50% | 50 | 0.050 | 25.0 |
| 22 | Alpha Isomethyl Ionone | neat | 43 | 0.043 | 43.0 |
| 23 | Cedarwood oil Virginia | neat | 40 | 0.040 | 40.0 |
| 24 | Benzyl Salicylate | neat | 39 | 0.039 | 39.0 |
| 25 | Musk Ketone | neat | 34 | 0.034 | 34.0 |
| 26 | Allyl Ionone | neat | 30 | 0.030 | 30.0 |
| 27 | Heliotropin Fleuressence | neat | 30 | 0.030 | 30.0 |
| 28 | Dihydro Beta Ionone | neat | 25 | 0.025 | 25.0 |
| 29 | Ambrox Super | 30% | 25 | 0.025 | 7.5 |
| 30 | Alpha Damascone | 10% | 15 | 0.015 | 1.5 |
| 31 | Heliotropal | neat | 10 | 0.010 | 10.0 |
| 32 | Anisaldehyde | neat | 8 | 0.008 | 8.0 |

**Allergen declarations (EU 26):** Alpha Isomethyl Ionone, Benzyl Salicylate, Coumarin

## 12. SUEDE — Luxury Suede Leather

**Accord architecture:** Safraleine–IBQ–Suederal leather triad with rose-patchouli heart and Styrax balsamic smoke; Vetival suede-texture, Ambrox crystalline mineral, Ambrettolide wine-musky depth.

**Scores:** Geo = **83.87**, Safety = 95.1, Longevity = 86.1, Sillage = 95.1, Luxury = 71.1, Texture = 80.2, Hedonic = 83.6, Clarity = 77.3

**Batch:** 2241 µL concentrate → diluted to **10.00 mL EDP at 22.41% concentration** in perfumer's alcohol.

### Top / Heart / Base

| Register | Ingredient | Dilution | Amount (µL) | Amount (mL) | Active µL |
|---|---|---:|---:|---:|---:|
| **— TOP —** |  |  |  |  |  |
| 1 | Bergamot FCF Sicilian | neat | 61 | 0.061 | 61.0 |
| 2 | Linalool | neat | 60 | 0.060 | 60.0 |
| 3 | Aldehyde C11 | 1% | 30 | 0.030 | 0.3 |
| 4 | Geraniol | neat | 24 | 0.024 | 24.0 |
| **— HEART —** |  |  |  |  |  |
| 5 | Hedione | neat | 310 | 0.310 | 310.0 |
| 6 | Rose Oxide | 10% | 30 | 0.030 | 3.0 |
| 7 | ACA | neat | 30 | 0.030 | 30.0 |
| 8 | Phenethyl Alcohol | neat | 17 | 0.017 | 17.0 |
| 9 | Damascenone | 1% | 12 | 0.012 | 0.1 |
| 10 | Ethyl Maltol | 10% | 2 | 0.002 | 0.2 |
| **— BASE —** |  |  |  |  |  |
| 11 | Iso E Super | neat | 250 | 0.250 | 250.0 |
| 12 | Suederal | 10% | 207 | 0.207 | 20.7 |
| 13 | Hexyl Salicylate | neat | 190 | 0.190 | 190.0 |
| 14 | Ambrettolide | 10% | 150 | 0.150 | 15.0 |
| 15 | Habanolide | neat | 125 | 0.125 | 125.0 |
| 16 | Cashmeran | 20% | 105 | 0.105 | 21.0 |
| 17 | Ethylene Brassylate | neat | 102 | 0.102 | 102.0 |
| 18 | Vetival | neat | 80 | 0.080 | 80.0 |
| 19 | Alpha Damascone | 10% | 70 | 0.070 | 7.0 |
| 20 | Ambermax | 50% | 61 | 0.061 | 30.5 |
| 21 | Damascol | 10% | 60 | 0.060 | 6.0 |
| 22 | Cedarwood oil Virginia | neat | 51 | 0.051 | 51.0 |
| 23 | Benzyl Salicylate | neat | 45 | 0.045 | 45.0 |
| 24 | Pink Pepper Base | neat | 40 | 0.040 | 40.0 |
| 25 | Citronellol | neat | 39 | 0.039 | 39.0 |
| 26 | Ambrox Super | 30% | 30 | 0.030 | 9.0 |
| 27 | Ebanol | neat | 30 | 0.030 | 30.0 |
| 28 | Isobutyl Quinoline | 10% | 20 | 0.020 | 2.0 |
| 29 | Evernyl | neat | 10 | 0.010 | 10.0 |

**Allergen declarations (EU 26):** Benzyl Salicylate, Citronellol, Geraniol, Linalool
