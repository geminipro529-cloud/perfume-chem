# YSL L'Homme EDT Super Luxury Design

**Date:** 2026-07-09  
**Status:** Approved design, pre-implementation  
**Target file:** `formulas/L_Homme_Luxe_30mL_EdP.md`  
**Family archetype:** `ysl_lhomme`  
**Batch format:** 30 mL EdP, 6,000 uL concentrate + 24 mL ethanol

## Goal

Create an ultra-polished luxury reinterpretation of YSL `L'Homme EDT` that still reads as `L'Homme` immediately on first smell. The formula should smell more expensive, smoother, and more tailored than the current Luxe draft without drifting into Prada iris, La Nuit cardamom-amber darkness, or natural-luxury muddiness.

## Core Constraints

- Preserve the repo skeleton markers for `ysl_lhomme`: perceptible `ginger`, `basil`, `tonka`, and `cedarwood`.
- Preserve the recognizable fresh-spicy-woody `L'Homme` silhouette:
  - bergamot
  - ginger
  - cool spice
  - violet-green softness
  - cedar
  - tonka
- Avoid the Reserve v1 failure mode from `AGENTS.md`: no chemically unrelated luxury naturals added for prestige.
- Avoid turning the fragrance into:
  - `Prada L'Homme` style iris-powder
  - `La Nuit de L'Homme` style dark cardamom oriental
  - generic fresh-musky designer brightness driven mainly by `Dihydromyrcenol`

## Olfactive Direction

The approved direction is **spiced silk luxury**.

This means the fragrance should open with smoother, richer citrus-spice contrast than stock `L'Homme`, then move into a polished violet-green woody heart, and finish with a tailored cedar-tonka-musk drydown that feels more expensive and texturally refined than a mass-market designer base.

The luxury should come from:

- better material choices
- smoother transitions
- cleaner architecture
- more elegant woody-musky texture

The luxury should **not** come from adding more note types or unrelated naturals.

## Architecture

### 1. Opening

**Function:** Announce `L'Homme` immediately, but with a richer and more polished surface.

**Primary materials**

- `Bergamot FCF oil Sicilian`
- `Ginger EO`
- `Cardamom EO`
- trace `Basil EO`

**Design intent**

- `Bergamot FCF oil Sicilian` is the citrus lead because it gives classical bergamot identity with a more luxurious profile than plain Bergamot FCF.
- `Ginger EO` is the required signature spark and should remain clearly audible.
- `Cardamom EO` is the cool luxury bridge from bergamot to woods.
- `Basil EO` stays at trace level only, enough to satisfy the skeleton and create aromatic definition without becoming anisic or herbal-forward.

**Opening control rules**

- Reduce `Dihydromyrcenol` versus the current Luxe draft.
- Do not let citrus freshness become generic sport-freshness.
- Do not let cardamom dominate enough to suggest `La Nuit`.

### 2. Heart

**Function:** Supply the soft violet-green designer elegance that makes the scent read as `L'Homme` rather than a generic fresh woody.

**Primary materials**

- `Alpha Isomethyl Ionone`
- `Parmavert`
- `Hedione HC`
- `Hedione`
- optional small `Mayol`

**Design intent**

- `Alpha Isomethyl Ionone` is the main violet-woody heart and should be the center of the luxury profile.
- `Parmavert` provides green leaf polish, not a loud leaf note.
- `Hedione HC` and `Hedione` provide air, expansion, and smoothness without turning the composition into a floral fragrance.
- `Mayol` is optional and should only be used if the center needs extra clean designer continuity.

**Heart control rules**

- Keep the heart smooth, translucent, and expensive.
- Avoid strong iris-butter, lipstick, or powder signatures.
- Avoid adding species-specific floral naturals that compete with the designer abstraction.

### 3. Base

**Function:** Turn the EDT structure into a more luxurious drydown while preserving `cedar + tonka + musk` identity.

**Primary materials**

- `Cedarwood oil Virginia`
- `Iso E Super`
- `Ambrofix`
- `Ebanol` or `Azarbre`
- `Tonkarome`
- `Habanolide`
- `Romandolide`

**Design intent**

- `Cedarwood oil Virginia` provides literal cedar identity.
- `Iso E Super` provides the modern woody halo, but should no longer flatten the whole fragrance.
- `Ambrofix` adds mineral-polished depth.
- `Ebanol` or `Azarbre` provides tactile luxury:
  - `Ebanol` if the base needs more creamy softness
  - `Azarbre` if the base needs warmer cedar-amber tailoring
- `Tonkarome` provides controlled tonka warmth without gourmand drift.
- `Habanolide + Romandolide` form the luxury musk chord:
  - `Habanolide` for intimate skin warmth
  - `Romandolide` for outward clean diffusion

**Base control rules**

- Do not let `Iso E Super` become the entire fragrance.
- Keep cedar perceptible enough to anchor the YSL skeleton.
- Keep tonka elegant and dry-soft, not sweet dessert-like.

## Material Inclusion Logic

### Keep

- `Bergamot FCF oil Sicilian`
- `Ginger EO`
- `Cardamom EO`
- `Basil EO` at trace
- `Alpha Isomethyl Ionone`
- `Parmavert`
- `Hedione HC`
- `Hedione`
- `Cedarwood oil Virginia`
- `Iso E Super`
- `Ambrofix`
- `Tonkarome`
- `Habanolide`
- `Romandolide`

### Candidate support materials

- `Mayol`
- `Ebanol`
- `Azarbre`
- small `Vetiver EO (India)` only if needed for base dryness and definition

### Explicitly rejected

- `Rose EO`, `Rose de Mai Absolute`, `Geranium EO`, `Geraniol`, `Citronellol`
- `Blue Chamomile EO`
- `Osmanthus Absolute`
- `Ylang` materials
- `Tuberose` materials
- `Clove EO`, `Eugenol`, `Isoeugenol`
- `Benzyl Salicylate` as a major fixative cushion
- `Galaxolide`
- heavy `Alpha Irone`
- `Tonka Bean FO`
- overt leather, smoke, incense, or gourmand materials

## Risk Controls

### Risk 1: Generic bright designer opening

**Cause:** too much `Dihydromyrcenol`

**Response:** lower it substantially or remove it entirely if bergamot, ginger, and cardamom already provide enough lift.

### Risk 2: Prada / Dior drift

**Cause:** too much iris, AIMI, or powder-musky softness

**Response:** use `Alpha Isomethyl Ionone` as a violet-woody accent, not a full iris statement; keep `Parmavert` polished and restrained.

### Risk 3: La Nuit drift

**Cause:** cardamom too loud, base too amber-dark

**Response:** keep cardamom elegant and controlled; do not sweeten or darken the base with oriental materials.

### Risk 4: Reserve v1 muddiness

**Cause:** unrelated naturals and too many luxury voices

**Response:** maintain a narrow material family palette focused on citrus-spice-violet-wood.

### Risk 5: Flat woody abstraction

**Cause:** `Iso E Super` dominating cedar and tonka

**Response:** ensure `Cedarwood oil Virginia` remains functionally audible; use support materials to improve texture instead of only increasing `Iso E Super`.

## Verification Plan

The implementation must be checked against both smell intent and pipeline behavior.

### Formula goals

- 30 mL total
- 20% EdP
- 6,000 uL exact concentrate
- material count should stay lean and legible

### Structural goals

- perceptible `ginger`
- perceptible but controlled `basil`
- perceptible `cedar`
- perceptible `tonka`
- violet-green heart should be present without iris takeover

### Pipeline goals

- pass `ysl_lhomme` skeleton markers in practical terms
- avoid extreme top-material OAV dominance where possible
- reduce current imbalance where `Dihydromyrcenol`, `Hedione`, and `Iso E Super` swamp the formula
- keep sub-threshold materials limited to genuinely structural roles

### Smell goals

- first impression: unmistakably `L'Homme`
- second impression: smoother, richer, more tailored
- drydown: cedar-tonka-musk luxury, not generic fresh wood

## Implementation Notes

The formula rewrite should begin from the current Luxe version, not the Reserve natural-luxury draft. The Reserve file is useful mainly as a warning case for luxury drift and for excluded materials.

Implementation should prioritize:

1. reducing crude freshness dominance
2. strengthening the violet-green and cedar-tonka signature
3. refining the musk and woody texture

## Acceptance Criteria

The design is successful if:

- the user smells `L'Homme` immediately
- the fragrance reads clearly more expensive than the original EDT
- the formula does not drift into Prada, La Nuit, or natural-luxury floral territory
- the architecture remains clean enough to survive pipeline and wear analysis without a muddy or chaotic opening
