# Iris–Jasmine Toile — 10 mL (v2 — luxury/hedonic expansion)

**Status:** toile v2 (pre-optimizer hand-expansion)
**Batch:** 10.00 mL (≈ 10.00 g at ρ ≈ 1.0)
**Concentrate:** 2 268 µL = **22.68 %**
**Ethanol 96 %:** 7 732 µL

## Changelog v1 → v2 (luxury + hedonic lift)

**Luxury (naturals & macrocyclics):**
- Alpha Irone 30 % 180 → **260** µL (+80) — real orris dose
- Ambrettolide 10 % 70 → **140** µL (+70) — macrocyclic naturalistic musk
- Carrot Seed EO 40 → **70** µL (+30) — natural earthy-iris
- Orivone 50 → **80** µL (+30) — buttery orris base
- Ebanol 55 → **90** µL (+35) — creamy sandalwood
- Iso E Super 90 → **50** µL (−40) — trim luxury-neutral filler
- **Added Javanol 20 µL neat** — premium skin-sandalwood for textural precision
- **Added Cedarwood Virginia EO 30 µL** — natural cedar warmth

**Hedonic (powder-cream sweetness):**
- Heliotropal 10 → **25** µL (+15)
- **Added Heliotropin neat 20 µL** — direct almond-heliotrope hedonic driver
- **Added Coumarin 20 % 40 µL** — hay-almond cushion
- **Added γ-Undecalactone 10 % 20 µL** — peach-cream lactone
- EB 150 → **200** µL (+50) — lactonic-creamy depth

## Why the optimizer didn't already do this

The toile was never run through the optimizer — it was hand-drafted. But even if it had been, hill-climbers have structural blindspots:

1. **Material pinning.** Optimizers only move materials already in the starting palette. Heliotropin, Coumarin, γ-Undecalactone, Javanol, Cedarwood Virginia weren't in v1 — the optimizer could never try them. Palette expansion is a human move.
2. **Acceptance threshold.** The hill-climb rejects moves that don't clear +0.02 geo. Small intermediate steps (e.g. trim Iso E Super −40) get rejected even when they'd unblock larger gains.
3. **Weighted composite dilutes hedonic.** AXIS_WEIGHTS: longevity/sillage/luxury/texture/stacking/photoreal = 1.0, hedonic = 0.4. Powder-sweet moves barely register in the geo.
4. **Sub-ODT ceilings.** Many trace materials are locked at start × 3, so they can't climb to their real optimum.
5. **Concentrate caps.** v1 was 18.68%; v2 is 22.68%. An optimizer with a 20% ceiling would refuse these additions.

Workflow fix: hand-expand palette → run optimizer on v2 → iterate.

## Concept

A **powdery iris** (Alpha Irone orris spine, earthy carrot seed, restrained ionone chord) laid under a **radiant indolic jasmine** (Hedione HC amplification, Cis Jasmone ketone, Jasmine FO body, Indole trace). The two accords are bridged by a **salicylate cushion gradient** — Benzyl Salicylate (cosmetic-heavy) layered under Hexyl Salicylate (transparent-green) — which is simultaneously the classical jasmine-diffusion framework and a cosmetic-powder register that echoes the orris.

Drydown: creamy-skin musk chord (Ethylene Brassylate lactonic depth + Habanolide skin warmth + Ambrettolide fruity-musky naturalism), Ebanol creamy sandalwood for silk texture, Iso E Super molecular cocoon, Ambrox Super trace mineral for transparency without crystalline cold.

**Signal shape:** short bergamot-petitgrain burst → iris-jasmine co-radiance at 20 min → salicylate powder bed at 2 h → lactonic skin musk + creamy sandalwood at 6 h+.

## Formula

| # | Ingredient | Dilution | µL | mL |
|---:|---|---|---:|---:|
| | **TOP — 150 µL** | | | |
| 1 | Bergamot FCF oil Sicilian | neat | 80 | 0.080 |
| 2 | Petitgrain EO | neat | 20 | 0.020 |
| 3 | Ethyl Linalool | neat | 40 | 0.040 |
| 4 | Aldehyde C11 undecylenic | 1 % | 10 | 0.010 |
| | **IRIS CORE — 580 µL** | | | |
| 5 | Alpha Irone | 30 % | 260 | 0.260 |
| 6 | Alpha Ionone | neat | 30 | 0.030 |
| 7 | Beta Ionone | neat | 15 | 0.015 |
| 8 | Irotyl | neat | 25 | 0.025 |
| 9 | Orivone | neat | 80 | 0.080 |
| 10 | Ultralia | neat | 30 | 0.030 |
| 11 | Carrot Seed EO | neat | 70 | 0.070 |
| 12 | Alpha Isomethyl Ionone | neat | 35 | 0.035 |
| 13 | Dihydro Beta Ionone | neat | 5 | 0.005 |
| 14 | Violet Fleuressence | neat | 30 | 0.030 |
| | **JASMINE CORE — 575 µL** | | | |
| 15 | Hedione | neat | 300 | 0.300 |
| 16 | Hedione HC | neat | 70 | 0.070 |
| 17 | Cis Jasmone | neat | 10 | 0.010 |
| 18 | Amyl Cinnamic Aldehyde (ACA) | neat | 40 | 0.040 |
| 19 | Benzyl Acetate | neat | 30 | 0.030 |
| 20 | Methyl Benzoate | neat | 12 | 0.012 |
| 21 | Jasmine FO | neat | 70 | 0.070 |
| 22 | Indole | 10 % | 6 | 0.006 |
| 23 | DBCA | neat | 20 | 0.020 |
| 24 | PEDMC | neat | 15 | 0.015 |
| 25 | Farnesol | neat | 2 | 0.002 |
| | **HEDONIC POWDER–CREAM — 80 µL (new)** | | | |
| 26 | Heliotropin | neat | 20 | 0.020 |
| 27 | Coumarin | 20 % | 40 | 0.040 |
| 28 | γ-Undecalactone | 10 % | 20 | 0.020 |
| | **BASE / MUSK / FIXATIVE / WOODS — 845 µL** | | | |
| 29 | Benzyl Salicylate | neat | 130 | 0.130 |
| 30 | Hexyl Salicylate | neat | 50 | 0.050 |
| 31 | Ethylene Brassylate | neat | 200 | 0.200 |
| 32 | Habanolide | neat | 80 | 0.080 |
| 33 | Ambrettolide | 10 % | 140 | 0.140 |
| 34 | Ebanol | neat | 90 | 0.090 |
| 35 | Javanol | neat | 20 | 0.020 |
| 36 | Cedarwood Virginia EO | neat | 30 | 0.030 |
| 37 | Iso E Super | neat | 50 | 0.050 |
| 38 | Ambrox Super | 30 % | 25 | 0.025 |
| 39 | Musk Ketone | 10 % | 30 | 0.030 |
| | **SUB-ODT TRACES — 38 µL** | | | |
| 40 | Geosmin | 1 % | 3 | 0.003 |
| 41 | Isoeugenol | neat | 3 | 0.003 |
| 42 | Damascone Beta | 10 % | 7 | 0.007 |
| 43 | Heliotropal | neat | 25 | 0.025 |
| | **Ethanol 96 %** | carrier | 7 732 | 7.732 |
| | **TOTAL** | | **10 000** | **10.000** |

## Material rationale — why THIS material, not alternatives

### Citrus — Bergamot FCF Sicilian (not Grapefruit, not Cedrat)
Jasmine soliflores are the classical home of bergamot; its linalyl acetate–linalool signature echoes and extends the Hedione radiance. Grapefruit FCF (bitter-pith dryness) would harden the iris cushion; Cedrat (bitter mineral citron) would fight the powder register. Sicilian origin chosen over regular FCF for richer top-note complexity.

### Petitgrain EO — green-bitter bridge
Adds the bitter-leafy facet that lives *between* bergamot and jasmine in a classical soliflore. Reads as "green stem" rather than "green leaf" — shortens the gap from citrus to indolic heart.

### Iris spine — Alpha Irone 30 % (primary) + Carrot Seed EO (depth) + Orivone (base)
Alpha Irone 30 % → 54 µL active = a real orris spine, not decoration. Carrot Seed EO is the earthy-iris backbone (proven critical in the IRL 50 mL optimization — carrot seed did heavy lifting). Orivone provides the buttery-vegetal iris base. Ultralia is a ghost-iris trace at 30 µL. AIMI held low at 35 µL (per the user's iris preference and IRL spec).

### Jasmine spine — Hedione + Hedione HC (not Hedione alone)
Hedione HC (high-cis) is ~4× the olfactive potency of regular Hedione for the jasmonate radiance register. 300 neat Hedione + 70 HC gives the soliflore volume without the HC over-sharpening the top. Cis Jasmone supplies the actual *ketone* character — without it, Hedione alone is "jasmine radiance" rather than "jasmine". Benzyl Acetate + Methyl Benzoate = the jasmine ester chord. Jasmine FO as body (70 µL — enough to read, not enough to dominate).

### Indole at trace (6 µL of 10 %)
Indole = 0.6 µL active. Below ODT for most wearers but present enough to shift the jasmine from "clean" into "real". Skatole rejected — too fecal for a toile; Indole is the controlled version.

### ACA (Amyl Cinnamic Aldehyde) for jasmine body
Waxy-floral diffusant that amplifies the jasmine without adding cinnamic spice. IFRA-restricted but 40 µL in 10 mL = 0.4 % which is below the 0.5 % EDP guidance.

### Farnesol at 2 µL (trace)
Synergizes with Hedione for neroli-lily depth under the jasmine. Above 5 µL risks the waxy-rancid overdose register.

### Salicylate gradient — Benzyl Sal (heavy) + Hexyl Sal (transparent)
Not a choice, a structure. Benzyl Salicylate 130 µL = the cosmetic-floral diffusion cushion every classical jasmine sits on. Hexyl Salicylate 50 µL layered above = green-floral transparency that keeps the cushion from reading as "old-school". Benzyl Benzoate rejected — it is a character-free fixative and the salicylate *character* is wanted here.

### Musk chord — 3 axes
- **Depth (lactonic):** Ethylene Brassylate 150 — creamy skin-body, echoes the iris butter
- **Projection / warmth:** Habanolide 80 — warm skin-trail (chosen over Romandolide because this toile wants intimacy, not outward projection)
- **Naturalistic:** Ambrettolide 10 % 70 µL = 7 µL active — macrocyclic fruity-musky, the most naturalistic musk in inventory; adds a real-skin quality Habanolide alone cannot
- Musk Ketone 10 % 30 µL = 3 µL active → powdery-talc character-echo for the iris register (the only nitro musk that reinforces the powder axis)

### Sandalwood — Ebanol (not Javanol)
Iris-jasmine = warm-creamy-silk register. Ebanol's milky-soft sandalwood matches; Javanol's dry-mineral would be too cold under this heart.

### Iso E Super (molecular cocoon, not cedar)
90 µL — enough for the skin-halo radiance amplification; not loaded as wood structure. Timberol or Koavone would push toward a woody-floral chypre; Iso E is the correct "invisible amplifier" here.

### Ambrox Super 30 % at 25 µL
Active = 7.5 µL. Mineral transparency trace to lift the drydown without introducing crystalline cold into an otherwise warm-powdery composition.

### Sub-ODT traces — Geosmin, Damascone β, Isoeugenol, Heliotropal
- **Geosmin 1 % 3 µL** — subliminal petrichor depth under the iris (ODT ≈ 6 ppt air; this is near the floor)
- **Damascone β 10 % 7 µL** = 0.7 µL — rose-ketone glint into the jasmine heart, adds a fruit facet without pulling toward rose
- **Isoeugenol 3 µL** — clove-carnation trace that vibrates with Cis Jasmone
- **Heliotropal 10 µL** — heliotrope-almond-powder whisper that ties iris to the lactonic drydown

## Axis targets (expected)

| Axis | Target | Reasoning |
|---|---:|---|
| Longevity | 78–82 | EB + Habanolide + Ambrettolide + BS = strong fixation, modest concentrate |
| Sillage | 78–85 | Hedione 300 + HC 70 + BS 130 = classical diffusion platform |
| Luxury | 60–68 | Real Irone 30 % dose + Jasmine FO + Ambrettolide drives it up |
| Texture | 80+ | Orivone + Ebanol + EB + Heliotropal = creamy-powdery-silk |
| Photorealism | 82–88 | Jasmine FO + Cis Jasmone + Indole + Carrot Seed = real iris and real jasmine |
| Synergy | 95 | Single direction (no green/leather/smoke intrusions) |
| Hedonic | 85+ | Powder-cream-floral = classical pleasure-accord |

## Next steps

1. Mix the toile and evaluate 24 h dry-down.
2. If radiance reads thin → boost Hedione HC first, then ACA.
3. If iris is swallowed by jasmine → increase Alpha Irone 30 % toward 240 µL.
4. If drydown reads synthetic → increase Ambrettolide (the naturalistic musk).
5. Run an `_opt_iris_jasmine_toile_10mL.py` convergence pass once the toile is approved.

## Rejected alternatives (recorded)

- **Ylang Comoros Complete** — would add a banana-solar facet that competes with the jasmine ester chord. Save for a separate "solar floral" concept.
- **PEA (Phenethyl Alcohol)** — rose-honey; would pull the heart toward rose rather than jasmine-iris.
- **Neroli EO** — orange-blossom is adjacent but its terpenic facet clashes with the carrot-seed earthiness.
- **Benzyl Benzoate** — character-free; the salicylate CHARACTER is wanted, not invisible fixation.
- **Javanol** — too cold-dry for a warm-creamy iris-jasmine.
- **Coumarin / Vanillin / Benzoin** — would push toward Iris Rêverie Lactée cream-drydown territory. This toile is the *non-gourmand* iris-jasmine.
- **Methyl Pamplemousse / Grapefruit FCF / Cedrat** — citrus alternatives that would harden the composition.
- **Evernyl** — would turn the toile into a jasmine-chypre; out of scope.
- **Mayol / Lilyreal / Bourgeonal** — muguet materials; they belong in IRL's cosmetic-muguet heart, not a jasmine toile.
