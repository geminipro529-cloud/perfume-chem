# Vetiver Classique V5 — 50 mL EdP
## Classical Vetiver-Woody · Pipeline Verified
### Citrus-Spice Top · Geranium Heart · Vetiver-Cedar-Moss-Tonka Base

> **Inventory:** [`inventory.txt`](/inventory.txt) · **Art direction:** Dry classical vetiver-woody. Bergamot as controlled opening. Vetiver as unmistakable star (32%). Cedar woody spine, not Iso E Super. Geranium EO as natural floral-herbaceous heart. Evernyl + Coumarin + Kephalis classical drydown. Ambrox Super at functional trace for lift without modern character.

---

### Full Formula (50 mL EdP · 10000 µL concentrate)

| # | Material | Dilution | Amount (uL) | Amount (mL) | Role |
|---:|---|:---:|---:|---:|------|
| 1 | Bergamot FCF oil Sicilian | neat | 500 | 0.500 | Bright citrus opening |
| 2 | Cedrat FCF oil Sicilian | neat | 300 | 0.300 | Citrus lift |
| 3 | Petitgrain EO | neat | 200 | 0.200 | Green-woody bridge |
| 4 | Black Pepper EO | neat | 100 | 0.100 | Dry terpenic spice |
| 5 | Linalool | neat | 50 | 0.050 | Fresh floral lift |
| 6 | Lavender EO | neat | 50 | 0.050 | Herbal-floral trace |
| 7 | Geranium EO | neat | 1500 | 1.500 | Natural floral heart |
| 8 | Vetiver EO (India) | neat | 3200 | 3.200 | **STAR** — earthy root |
| 9 | Cedarwood oil Virginia | neat | 1700 | 1.700 | Classical woody spine |
| 10 | Ambrox Super | neat | 100 | 0.100 | Functional lift/weight |
| 11 | Evernyl | neat | 50 | 0.050 | Mossy anchor |
| 12 | Coumarin | 20% | 750 | 0.750 | Tonka warmth |
| 13 | Kephalis | neat | 100 | 0.100 | Warm resinous depth |
| 14 | Habanolide | neat | 200 | 0.200 | Skin musk |
| 15 | Patchouli EO | neat | 100 | 0.100 | Earthy bed |
| | **Total** | | **8900** | **8.900** | |

---

### Key Design Decisions

| Change from V1 | V1 | V5 | Why |
|----------------|----:|----:|-----|
| Geraniol | 400 | — | Replaced by Geranium EO (natural, complex) |
| Geranium EO | — | 1500 | Natural geranium-rose-herbaceous heart |
| Vetiver EO (India) | 1700 | 3200 | Doubled — star must dominate |
| Cedarwood EO | 650 | 1700 | Tripled — classical woody spine |
| Iso E Super | 150 | — | Removed — molecular cocoon not classical |
| Sandalore | 400 | — | Removed — no sandalwood in classical vetiver |
| Vertofix | 500 | — | Removed — modern fixative |
| Hedione HC | 100 | — | Removed — jasmonate not classical |
| Tobacco Absolute (10%) | 400 | — | Replaced by Kephalis |
| Kephalis | — | 100 | Warm resinous depth in inventory |
| Ambrox Super | — | 100 | Functional propellant at trace (OAV 17) |
| Habanolide | 450 | 200 | Reduced — trace skin musk only |
| Coumarin (20%) | 200 | 150 neat | 3.75× more active dose |
| **Materials** | **18** | **15** | Cleaner, more focused |

### Pipeline Verification

**Result: PASS** (13 PASS / 2 WARN / 0 FAIL)

| Gate | Status |
|------|--------|
| Registry integrity | ✅ PASS |
| Name normalization | ✅ PASS |
| Family resolution | ✅ PASS → woody.vetiver_classical |
| Build formula state | ✅ PASS |
| ODT coverage | ✅ PASS |
| OAV computation | ✅ PASS — 14/15 perceptible |
| Family fit | ✅ PASS — all 10 anchors + drift limits |
| Pyramid balance | ✅ PASS |
| Temporal simulation | ✅ PASS — evap 8% over 4h |
| IFRA safety | ✅ PASS — all within limits |
| Robustness | ✅ PASS — 30 perturbations stable |
| OAV intelligence | ✅ PASS |
| Repair suggestions | ✅ PASS — no repairs needed |
| Confidence | ⚠ WARN (47.9 — calibration data gap) |

### Headspace OAV Profile

| Material | OAV | Perceptibility | Note | Vapor ppm |
|----------|----:|:--------------|:----:|----------:|
| Bergamot FCF oil Sicilian | 5168 | very strong | heart | 31.01 |
| Geranium EO | 3654 | very strong | heart | 5.48 |
| Cedrat FCF oil Sicilian | 1981 | very strong | top | 15.85 |
| Linalool | 1188 | very strong | top | 1.78 |
| Lavender EO | 744 | strong | heart | 1.49 |
| Petitgrain EO | 468 | strong | top | 1.40 |
| Coumarin | 252 | strong | base | 0.18 |
| Vetiver EO | 33 | moderate | base | 0.17 |
| Evernyl | 20 | moderate | base | 0.01 |
| Cedarwood Virginia | 19 | moderate | heart | 0.28 |
| Black Pepper EO | 17 | moderate | top | 0.03 |
| Ambrox Super | 17 | moderate | base | 0.01 |
| Patchouli EO | 2 | threshold | base | — |
| Habanolide | 1 | threshold | base | — |
| Kephalis | 0.1 | sub-threshold | heart | — |
| **Total** | **57.69 ppm** | | | |

### Temporal Evolution (5 Windows)

| Window | Leader | T/H/B | Vapor |
|---------|--------|:-----:|:-----:|
| Opening (0s) | Bergamot 5168 | 8/46/46 | 57.7 ppm |
| 5 min | Bergamot 5081 | 8/46/46 | 56.9 ppm |
| 30 min | Bergamot 4667 | 8/46/46 | 53.3 ppm |
| 2 hr | **Geranium 3764** | 7/46/48 | 42.1 ppm |
| 4 hr | **Geranium 3817** | 6/45/50 | 31.1 ppm |

> Geranium EO overtakes citrus at 2h and leads to drydown — classical heart persistence.
> Vetiver OAV 33 throughout — perceptible star.
> Ambrox Super at OAV 17 provides functional lift without character dominance.

## Pipeline Analysis

The latest canonical analysis for this formula is stored in [`_vetiver_classique_v5_analysis.txt`](../_vetiver_classique_v5_analysis.txt).
It was generated from `_vetiver_classique_v5_pipeline.json` using `scripts/format_pipeline_analysis.py`.
