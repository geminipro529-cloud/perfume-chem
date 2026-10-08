# DHI-11 — Velours d'Iris V3.1 Current Stock — 05443/A Architecture Study — 30 mL / 20%

**Status:** DRAFT — current-stock rebuild of V3 Smooth. Every stock is in the inventory records (2026-10-08); the gate has no FAILs; its two remaining HOLDs are density data gaps (see Stocks and remaining holds). Mixing is Kenny's call.
**Case:** `DHI-11-VELOURS-D-IRIS-05443A-V3-1-CURRENT-STOCK`  
**Claim mode:** named_reference  
**Reference contract:** dior_homme_intense_2011_05443a_architecture_v1  
**Reference scope:** architecture  
**Family archetype:** `iris_coumarin_amber.dhi2011`  
**Claim ceiling:** `COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY`  
**Physical state:** `NOT COMPOUNDED`  
**Sensory / liking / depth / similarity / smoothness / performance / stability:** `NOT TESTED`  
**Safety / IFRA / skin-use / release:** `HOLD`  
**Immediate parent formula:** `formulas/DHI-11_Velours_d_Iris_05443A_30mL_20pct_V3_Smooth.md`  
**Parent semantics:** same 30 functions and nominal active doses as V3 Smooth, rebuilt on the stocks Kenny owns on 2026-10-08; the target, modules and handoffs are V3's and are not repeated here.

Compound exactly **4,560 µL raw stock**, then add exactly **24,000 µL
Ethanol 96%**. This is a positive-addition instruction, not q.s. to volume.
The finished volume is about 28.6 mL, not 30 mL (see the Ambrettolide row below).

## What changed from V3 Smooth, and why

| V3 Smooth row | This card | Reason |
|---|---|---|
| Ambrettolide, 10% w/w in DPG, 1,600 µL | Ambrettolide, neat, 160 µL | Kenny's Ambrettolide is neat (2026-10-08). 160 µL neat keeps V3's 160 µL nominal active dose (the 1:10 rebase Kenny accepted for R6). The 1,440 µL of DPG that came with the 10% stock is left out, as in the R6 rebase, and the ethanol stays 24,000 µL: the concentrate is 4,560 µL, the bottle about 28.6 mL, and the nominal active concentration about 5% higher than V3 with its DPG. Adding the DPG back as a row would keep 30 mL but lowers every modelled OAV by about 2.6%, putting Verdox and Ethylene Brassylate at 0.98. |
| Lavender EO High Altitude (angustifolia, France), 110 µL | Lavender EO (BONTAUX SAS), 110 µL | The High Altitude lavender is no longer owned (removed 2026-09-08). BONTAUX is the owned French angustifolia lavender. This is a substitution, not the same oil. |
| Vetiver EO (India), 140 µL, basket 2 | Vetiver EO (Haiti), 140 µL, basket 1 | Kenny corrected this bottle's origin to Haiti on 2026-09-10. Basket 1 is where docs/basket_order_preference.md puts Haitian vetiver. |
| Vetival, basket 5 | Vetival, basket 1 | Same dose; docs/basket_order_preference.md lists Vetival in Always used. |
| Mimosa Absolute, "10% in DPG" | Mimosa Absolute, 10% w/w in DPG | The inventory records this stock as 10% w/w in DPG; Kenny is keeping it (2026-10-08). |
| Osmanthus Absolute, "10% in DPG" | Osmanthus Absolute, 10% w/w in DPG | Kenny confirmed it was made by weight (2026-10-08). |
| Ethyl 2-Methylbutyrate, 0.1% in DPG, 50 µL | Ethyl 2-Methylbutyrate, 0.01% w/w in DPG, 50 µL | Kenny's choice (2026-10-08) after E2MB's vapour pressure was corrected from an unsourced 5 Pa to 1,070 Pa (RIFM safety assessment, EPI Suite estimate). At 0.1% it modelled at about 187 times its odour threshold, fourth in the opening; at 0.01% it models at about 19, below Linalyl Acetate, which keeps it the short pear flash V3 designed. This is an intended tenfold cut in E2MB's active dose, not a stock rebase. |

Every other dose is V3 Smooth's, including the 2026-10-08 Verdox 340 µL / Benzyl Acetate 160 µL revision.

**E2MB dose authority:** the tenfold E2MB cut is Kenny's decision (card, 2026-10-08 16:28 UTC). Gate this card against V3 Smooth with `--authorize-active-dose-change "Ethyl 2-Methylbutyrate=Kenny decision card 2026-10-08 16:28 UTC: use 0.01% after the E2MB vapour-pressure fix (5 -> 1,070 Pa)"`; the pre-mix guard then reports it as an authorized dose change (WARN) instead of a stock-rebase FAIL.

## Stocks and remaining holds

All 30 stocks now resolve in the inventory records (successor overlay v22, 2026-10-08), and preflight passes.

- **Ethyl 2-Methylbutyrate (0.01% w/w in DPG):** a new solution made from Kenny's neat PerfumersWorld E2MB (received 2026-10-07). Kenny asked for it to be recorded at its nominal percentage, so no weights are on file. Make it by weight in three steps, capping each vial straight away because E2MB is very volatile:
  1. **1% w/w:** 9.900 g DPG, then 0.100 g E2MB.
  2. **0.1% w/w:** 9.000 g DPG, then 1.000 g of the 1%.
  3. **0.01% w/w:** 9.000 g DPG, then 1.000 g of the 0.1%.
- **Mimosa Absolute (10% w/w in DPG):** Kenny keeps it. Its execution hold is lifted on that decision; its bottle-lot and preparation receipts are still missing.
- **Osmanthus Absolute (10% w/w in DPG):** basis confirmed by Kenny.
- **Densities:** the gate's chemistry-stability and phase checks need an authoritative active mass, so they report HOLD until densities exist for 15 stocks: Alpha Irone, Ambrettolide, Carrot Seed EO, Ethyl 2-Methylbutyrate, Ethylene Brassylate, Irotyl, Iso E Super, Isobutavan, Mimosa Absolute, Osmanthus Absolute, Romandolide, Tonkarome, Ultralia, Vetival and Vetiver EO (Haiti). This is a data gap, not a formula problem.

## CURRENT-INVENTORY RAW-VOLUME BUILD — parser-visible formula

Every occupied basket is in descending raw Amount (µL); the sequence resets
only at a new basket. No separate carrier is added.

**BASKET 1 — ALWAYS USED**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Hedione | neat | 140 | 140.000 | 30701.7544 | 30701.7544 | floral air across lavender decay, fruit ingress, and iris edge |
| 2 | Iso E Super | neat | 140 | 140.000 | 30701.7544 | 30701.7544 | transparent rear wood receiving the iris tail |
| 3 | Vetiver EO (Haiti) | neat | 140 | 140.000 | 30701.7544 | 30701.7544 | natural dry-earth counterline (was the Indian-labelled row) |
| 4 | Vetival | neat | 80 | 80.000 | 17543.8596 | 17543.8596 | polished suede-vetiver grading material |
| 5 | Benzyl Salicylate | neat | 60 | 60.000 | 13157.8947 | 13157.8947 | waxy cosmetic film between powder and musk |
| 6 | Benzyl Benzoate | neat | 40 | 40.000 | 8771.9298 | 8771.9298 | sub-threshold slow mass and constant-total reservoir |

**BASKET 2 — VETIVERS**

*(no materials in this formula)*

**BASKET 3 — WOODS**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 7 | Cedarwood oil Virginia | neat | 250 | 250.000 | 54824.5614 | 54824.5614 | named Virginia-cedar grain |
| 8 | Cashmeran | neat | 60 | 60.000 | 13157.8947 | 13157.8947 | textile flex between warm powder, wood, and skin |
| 9 | Sandalore | neat | 60 | 60.000 | 13157.8947 | 13157.8947 | sub-threshold creamy seam hypothesis rounding cedar into musk |

**BASKET 4 — WOOD MODIFIERS AND AMBERS**

*(no materials in this formula)*

**BASKET 5 — WOOD-VETIVERS**

*(no materials in this formula)*

**BASKET 6 — MUSKS**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 10 | Ethylene Brassylate | neat | 870 | 870.000 | 190789.4737 | 190789.4737 | creamy powder-textile velvet |
| 11 | Romandolide | neat | 210 | 210.000 | 46052.6316 | 46052.6316 | restrained outward woody-musk shell |
| 12 | Ambrettolide | neat | 160 | 160.000 | 35087.7193 | 35087.7193 | fruity-wine ambrette proxy and skin mediator |

**BASKET 7 — MUGUET AND LAVENDER**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 13 | Lavender EO (BONTAUX SAS) | neat | 110 | 110.000 | 24122.8070 | 24122.8070 | short fine-French aromatic veil (replaces the High Altitude lavender) |
| 14 | Linalyl Acetate | neat | 70 | 70.000 | 15350.8772 | 15350.8772 | soft ester fold from lavender into pear skin |
| 15 | Linalool | neat | 20 | 20.000 | 4385.9649 | 4385.9649 | small floral-air continuation into the heart |

**BASKET 8 — JASMINE, INDOLE, AND MAGNOLIA**

*(no materials in this formula)*

**BASKET 9 — YLANG, ORANGE FLOWER, AND NARCOTICS**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 16 | Mimosa Absolute | 10% w/w in DPG | 80 | 8.000 nominal | 17543.8596 | 1754.3860 nominal | natural honeyed-green powder irregularity |
| 17 | Osmanthus Absolute | 10% w/w in DPG | 20 | 2.000 nominal | 4385.9649 | 438.5965 nominal | trace suede-apricot fruit skin |

**BASKET 10 — ROSE**

*(no materials in this formula)*

**BASKET 11 — IRIS AND ORRIS**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 18 | Alpha Isomethyl Ionone (Methyl Ionone Pure) | neat | 420 | 420.000 | 92105.2632 | 92105.2632 | opaque powder and lipstick body |
| 19 | Alpha Ionone | neat | 180 | 180.000 | 39473.6842 | 39473.6842 | violet motion receiving fruit and turning toward wood |
| 20 | Alpha Irone | 10% w/w in DEP | 180 | 18.000 nominal | 39473.6842 | 3947.3684 nominal | cool buttery rhizome specificity |
| 21 | Dihydro Beta Ionone | neat | 100 | 100.000 | 21929.8246 | 21929.8246 | sub-threshold structural darkening hypothesis at the iris-to-wood seam |
| 22 | Irotyl | neat | 80 | 80.000 | 17543.8596 | 17543.8596 | sub-threshold dry-grain hypothesis in the late iris |
| 23 | Ultralia | neat | 60 | 60.000 | 13157.8947 | 13157.8947 | sub-threshold iris-recurrence hypothesis in the textile drydown |
| 24 | Orivone | neat | 20 | 20.000 | 4385.9649 | 4385.9649 | fatty-warm orris-to-tonka seam |
| 25 | Carrot Seed EO | neat | 10 | 10.000 | 2192.9825 | 2192.9825 | sub-threshold botanical-asymmetry hypothesis linking irone to vetiver |

**BASKET 12 — EDIBLE SMELLS**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 26 | Tonkarome | 20% w/w in TEC | 310 | 62.000 nominal | 67982.4561 | 13596.4912 nominal | coumarinic hay-tonka underlay |
| 27 | Isobutavan | neat | 140 | 140.000 | 30701.7544 | 30701.7544 | narrow buttery-vanillic seam into musk |

**BASKET 13 — EDIBLE SPICES**

*(no materials in this formula)*

**BASKET 14 — MY FAVORITE SMELLS**

*(no materials in this formula)*

**BASKET 15 — FRUITS**

| # | Material | Dilution | Amount (µL) | Active µL | Raw ppm | Active ppm | Current-build function |
|---:|---|---|---:|---:|---:|---:|---|
| 28 | Verdox | neat | 340 | 340.000 | 74561.4035 | 74561.4035 | green pear flesh and woody continuity |
| 29 | Benzyl Acetate | neat | 160 | 160.000 | 35087.7193 | 35087.7193 | floral-fruit skin at the pear-to-orris boundary |
| 30 | Ethyl 2-Methylbutyrate | 0.01% w/w in DPG | 50 | 0.005 nominal | 10964.9123 | 1.0965 nominal | volatile juicy pear-liqueur flash |

**BASKET 16 — ALDEHYDES**

*(no materials in this formula)*

**BASKET 17 — GREEN SMELLING THINGS**

*(no materials in this formula)*

**Concentrate total:** **4,560 µL raw stock**.  
**Nominal mixed-basis screening-active total:** **4,010.005 µL proxy**, or
**879,387.0614 active-ppm screening proxy** in concentrate. W/w stocks and
stocks without solution density do not supply literal active volume or exact
mass ppm.

<!-- FORMULA_MIXING_PROTOCOL_START -->
### Pour sequence — raw-volume card

Use a fresh tip whenever moving to a new material. Complete each basket and
dose high to low raw µL inside it:

1. **Always used:** Hedione 140; Iso E Super 140; Haitian Vetiver EO 140; Vetival 80; Benzyl Salicylate 60; Benzyl Benzoate 40.
2. **Vetivers:** none.
3. **Woods:** Cedarwood oil Virginia 250; Cashmeran (neat) 60; Sandalore 60.
4. **Wood modifiers and ambers:** none.
5. **Wood-vetivers:** none.
6. **Musks:** Ethylene Brassylate 870; Romandolide 210; Ambrettolide (neat) 160.
7. **Muguet and lavender:** Lavender EO (BONTAUX SAS) 110; Linalyl Acetate 70; Linalool 20.
8. **Jasmine, indole, and magnolia:** none.
9. **Ylang, orange flower, and narcotics:** Mimosa Absolute (10% w/w in DPG) 80; Osmanthus Absolute (10% w/w in DPG) 20.
10. **Rose:** none.
11. **Iris and orris:** Alpha Isomethyl Ionone (Methyl Ionone Pure) 420; Alpha Ionone 180; Alpha Irone (10% w/w in DEP) 180; Dihydro Beta Ionone 100; Irotyl 80; Ultralia 60; Orivone 20; Carrot Seed EO 10.
12. **Edible smells:** Tonkarome (20% w/w in TEC) 310; Isobutavan 140.
13. **Edible spices:** none.
14. **My favorite smells:** none.
15. **Fruits:** Verdox 340; Benzyl Acetate 160; Ethyl 2-Methylbutyrate (0.01% w/w in DPG) 50.
16. **Aldehydes:** none.
17. **Green smelling things:** none.

#### Exact transfer card

| Step | Basket | Physical bottle label | Stock form | Transfer | Running concentrate |
|---:|---|---|---|---:|---:|
| 1 | 1 | Hedione | neat | 140 µL | 140 µL |
| 2 | 1 | Iso E Super | neat | 140 µL | 280 µL |
| 3 | 1 | Haitian Vetiver EO | neat | 140 µL | 420 µL |
| 4 | 1 | Vetival | neat | 80 µL | 500 µL |
| 5 | 1 | Benzyl Salicylate | neat | 60 µL | 560 µL |
| 6 | 1 | Benzyl Benzoate | neat | 40 µL | 600 µL |
| 7 | 3 | Cedarwood oil Virginia | neat | 250 µL | 850 µL |
| 8 | 3 | Cashmeran (neat) | neat | 60 µL | 910 µL |
| 9 | 3 | Sandalore | neat | 60 µL | 970 µL |
| 10 | 6 | Ethylene Brassylate | neat | 870 µL | 1,840 µL |
| 11 | 6 | Romandolide | neat | 210 µL | 2,050 µL |
| 12 | 6 | Ambrettolide (neat) | neat | 160 µL | 2,210 µL |
| 13 | 7 | Lavender EO (BONTAUX SAS) | neat | 110 µL | 2,320 µL |
| 14 | 7 | Linalyl Acetate | neat | 70 µL | 2,390 µL |
| 15 | 7 | Linalool | neat | 20 µL | 2,410 µL |
| 16 | 9 | Mimosa Absolute (10% w/w in DPG) | 10% w/w in DPG | 80 µL | 2,490 µL |
| 17 | 9 | Osmanthus Absolute (10% w/w in DPG) | 10% w/w in DPG | 20 µL | 2,510 µL |
| 18 | 11 | Alpha Isomethyl Ionone (Methyl Ionone Pure) | neat | 420 µL | 2,930 µL |
| 19 | 11 | Alpha Ionone | neat | 180 µL | 3,110 µL |
| 20 | 11 | Alpha Irone (10% w/w in DEP) | 10% w/w in DEP | 180 µL | 3,290 µL |
| 21 | 11 | Dihydro Beta Ionone | neat | 100 µL | 3,390 µL |
| 22 | 11 | Irotyl | neat | 80 µL | 3,470 µL |
| 23 | 11 | Ultralia | neat | 60 µL | 3,530 µL |
| 24 | 11 | Orivone | neat | 20 µL | 3,550 µL |
| 25 | 11 | Carrot Seed EO | neat | 10 µL | 3,560 µL |
| 26 | 12 | Tonkarome (20% w/w in TEC) | 20% w/w in TEC | 310 µL | 3,870 µL |
| 27 | 12 | Isobutavan | neat | 140 µL | 4,010 µL |
| 28 | 15 | Verdox | neat | 340 µL | 4,350 µL |
| 29 | 15 | Benzyl Acetate | neat | 160 µL | 4,510 µL |
| 30 | 15 | Ethyl 2-Methylbutyrate (0.01% w/w in DPG) | 0.01% w/w in DPG | 50 µL | 4,560 µL |

#### Seventeen-basket checkpoints

| Basket | Action | Row steps | Basket subtotal | Running total |
|---:|---|---:|---:|---:|
| 1 | COMPOUND | 1–6 | 600 µL | 600 µL |
| 2 | SKIP | — | 0 µL | 600 µL |
| 3 | COMPOUND | 7–9 | 370 µL | 970 µL |
| 4 | SKIP | — | 0 µL | 970 µL |
| 5 | SKIP | — | 0 µL | 970 µL |
| 6 | COMPOUND | 10–12 | 1,240 µL | 2,210 µL |
| 7 | COMPOUND | 13–15 | 200 µL | 2,410 µL |
| 8 | SKIP | — | 0 µL | 2,410 µL |
| 9 | COMPOUND | 16–17 | 100 µL | 2,510 µL |
| 10 | SKIP | — | 0 µL | 2,510 µL |
| 11 | COMPOUND | 18–25 | 1,050 µL | 3,560 µL |
| 12 | COMPOUND | 26–27 | 450 µL | 4,010 µL |
| 13 | SKIP | — | 0 µL | 4,010 µL |
| 14 | SKIP | — | 0 µL | 4,010 µL |
| 15 | COMPOUND | 28–30 | 550 µL | 4,560 µL |
| 16 | SKIP | — | 0 µL | 4,560 µL |
| 17 | SKIP | — | 0 µL | 4,560 µL |

After the Basket 17 checkpoint, add exactly **24,000 µL Ethanol 96%**.
Do not q.s. to 30 mL. Record actual delivered volume and any deviation for
every transfer.
<!-- FORMULA_MIXING_PROTOCOL_END -->

## Finished Matrix Inputs

**Matrix authority:** `declared_volume_proxy`

| Component | Volume µL | Density g/mL | MW g/mol | Source |
|---|---:|---:|---:|---|
| Ethanol | 23040 | 0.785 | 46.0684 | nominal 96% v/v ethanol-stock representation; no contraction correction |
| Water | 960 | 0.9970 | 18.01528 | nominal 4% v/v co-component of declared ethanol stock |

This is the same finished-matrix declaration as the immediate parent, so the
parent/child OAV-per-time screen compares like with like. It does not resolve
stock-solution density or literal active volume for w/w stocks.
