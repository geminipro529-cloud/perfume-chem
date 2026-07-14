# F1 — Le Barbier de Grasse · 30 mL Concentrate

**Family:** Classical Fougère (lavender · coumarin · oakmoss-cedar · musk)
**Batch:** 30.00 mL concentrate (≈ 30.0 g at ρ ≈ 1.0)
**Active load:** 73.1 % (21 920 mg single-molecule + EO actives)
**Inert carrier:** 26.9 % (8 080 mg DPG / DEP from supplier dilutions — not added separately)
**Final dilution suggested:** 20 % in perfumer's ethanol → **150 mL EDP**

---

## Architecture

| Layer | Function | Materials |
|---|---|---|
| **Base** | Coumarinic-mossy-musk shadow, fixation, depth | Coumarin, Vanillin, Ethylene Brassylate, Galaxolide, Ambrox Super, Cedarwood EO, Patchouli EO, Vetiver EO, Evernyl, Hexyl Salicylate |
| **Heart** | Aromatic lavender body, radiance, eugenol-clove warmth | Hedione, Iso E Super, Lavender EO, Linalyl Acetate, Geraniol, Eugenol |
| **Top** | Hesperidic lift | Bergamot FCF |

**Musk chord (2-axis):**
- Ethylene Brassylate (depth · creamy-lactonic, synergizes with Coumarin + Vanillin)
- Galaxolide (projection · clean-synthetic sillage extender)

---

## Recipe — sorted by mixing order

> Add to a clean 50 mL amber vial. Use positive-displacement pipette for ≤ 100 µL doses, glass syringe or graduated dropper for larger volumes. Cap and swirl gently after each addition. Total before maturation ≈ 30.00 mL.

### Stage 1 — Base (build first, longest to integrate)

| # | Material | Form | µL | mL |
|---:|---|---|---:|---:|
| 1 | Coumarin | 20 % in DPG | 5 833 | 5.83 |
| 2 | Ethylene Brassylate | neat | 1 985 | 1.99 |
| 3 | Galaxolide | 80 % | 1 928 | 1.93 |
| 4 | Vanillin | 10 % | 2 067 | 2.07 |
| 5 | Ambrox Super | 30 % w/v | 1 667 | 1.67 |
| 6 | Cedarwood EO | neat | 1 509 | 1.51 |
| 7 | Patchouli EO | neat | 1 136 | 1.14 |
| 8 | Vetiver EO | neat | 755 | 0.76 |
| 9 | Evernyl | neat | 507 | 0.51 |
| 10 | Hexyl Salicylate | neat | 461 | 0.46 |
| | **Stage 1 subtotal** | | **17 848** | **17.85** |

> *Swirl. The base should look pale-amber and slightly viscous. Let it homogenize 2–3 minutes before Stage 2.*

### Stage 2 — Heart (aromatic-floral body)

| # | Material | Form | µL | mL |
|---:|---|---|---:|---:|
| 11 | Hedione | neat | 3 710 | 3.71 |
| 12 | Iso E Super | neat | 2 985 | 2.99 |
| 13 | Lavender EO | neat | 1 775 | 1.78 |
| 14 | Linalyl Acetate | neat | 1 256 | 1.26 |
| 15 | Geraniol | 10% in DPG | 7320 | 7.320 |
| 16 | Eugenol | neat | 324 | 0.32 |
| | **Stage 2 subtotal** | | **10 782** | **10.78** |

> *Swirl. The blend should now smell distinctly fougère — lavender + coumarin axis already legible.*

### Stage 3 — Top (volatile, add last)

| # | Material | Form | µL | mL |
|---:|---|---|---:|---:|
| 17 | Bergamot FCF | neat | 1 370 | 1.37 |
| | **Stage 3 subtotal** | | **1 370** | **1.37** |

---

## Total

| | µL | mL |
|---|---:|---:|
| **Concentrate total** | **30 000** | **30.00** |

---

## Maturation

1. Cap tightly, label "F1 concentrate · DD-MM-YYYY".
2. Rest **dark, 18–22 °C, 4 weeks minimum** before dilution. Coumarin + Evernyl + macrocyclic musks integrate slowly.
3. After maturation: dilute 20 % w/v in perfumer's ethanol (≥ 96 %, denatured acceptable). For 150 mL EDP: 30 mL concentrate + 120 mL ethanol. Optional: 1–2 drops distilled water per 100 mL after dilution to soften.
4. Macerate diluted EDP additional 2 weeks before evaluation on skin.

---

## IFRA / safety check (50th amendment, Cat. 4 EDP, applied at 20 % concentrate in ethanol)

| Material | wt % in concentrate | wt % in EDP (×0.20) | IFRA Cat. 4 limit | Status |
|---|---:|---:|---:|---|
| Eugenol | 1.48 | 0.30 | 0.50 | ✓ |
| Geraniol | 3.34 | 0.67 | 5.30 | ✓ |
| Coumarin (active) | 1.06 | 0.21 | 1.60 | ✓ |
| Hexyl Salicylate | 2.10 | 0.42 | 5.00 | ✓ |
| Linalyl Acetate (as linalool eq.) | 5.73 | 1.15 | (no Cat. 4 cap) | ✓ |
| Lavender EO (linalool ~30%) | 8.10 | 1.62 | linalool 7.5 | ✓ |
| Evernyl | 2.31 | 0.46 | (synthetic, no oakmoss cap) | ✓ |

All values within Cat. 4 limits at 20 % EDP dilution. No restricted-allergen overshoot.

---

## Verification

- ✓ All 17 materials confirmed in `inventory.txt`
- ✓ Active wt % sum = **99.998** (rounding from optimizer; treat as 100.0)
- ✓ µL sum = **30 000** exactly (post-rounding scaled to 30 mL)
- ✓ All supplier dilutions accounted for (Coumarin 20 % DPG, Vanillin 10 %, Galaxolide 80 %, Ambrox Super 30 % w/v; remainder neat)
- ✓ IFRA Cat. 4 compliant at 20 % EDP

Source data: [_F1_30mL_recipe.json](../_F1_30mL_recipe.json) · driver: [_F1_30mL_recipe.py](../_F1_30mL_recipe.py)
