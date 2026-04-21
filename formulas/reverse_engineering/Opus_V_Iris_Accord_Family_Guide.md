# Opus V Iris Accord Family Guide

**Date:** 2026-04-04  
**Purpose:** crystallize the `Opus V` iris idea into a reusable module system without destroying the darker signature version  
**Signature Rich Master:** [Amouage_Opus_V_Iris_Accord_Current_Inventory.md](d:\chatbots\perfume-chem\Amouage_Opus_V_Iris_Accord_Current_Inventory.md)

---

## Design Brief

The official `Opus V / Woods Symphony` structure is not just iris:
- top `Orris Absolute, Rhum`
- heart `Orris Concrete, Rose, Jasmine`
- base `Oud, Civet, Dry Woods`

So the reusable part is not the full perfume. It is the **iris center**:
- buttery irone body
- metallic-cold orris concrete edge
- dry, polished, slightly rooty finish

To make that travel across many perfume families, the accord has to be split into:
- a **crystallized cross-family core**
- a **lighter airier version**
- a **dark shadow module**
- the existing **rich signature master**

---

## What Stays Fixed

Across all versions, the real `Opus V` iris DNA lives in:
- `Alpha Irone (10%)`
- `Orivone`
- `Orris F-TEC`
- `Methyl Ionone Pure`
- `I-IRIS F-TEC`
- `Alpha Ionone`
- `Beta Ionone`
- `Dihydro Beta Ionone`
- `Rose Oxide (1%)` at trace

These are the materials that keep the accord:
- buttery
- waxy
- metallic-cool
- iris-concrete rather than cosmetic-lipstick

What moves in and out by family:
- `Carrot Seed EO`
- `Bacdanol`
- `Ambrox Super`
- `Vetival`
- `Heliotropin Fleuressence`
- `Coumarin (20%)`
- outer wood support

---

## Module Set

### 1. Crystal Core

Use [Opus_V_Iris_Crystal_1000uL.md](d:\chatbots\perfume-chem\Opus_V_Iris_Crystal_1000uL.md) as the default reusable iris module.

This is the best starting point for:
- woody
- musk
- ambroxan
- floral-woody
- transparent modern styles

### 2. Signature Rich

Keep [Amouage_Opus_V_Iris_Accord_Current_Inventory.md](d:\chatbots\perfume-chem\Amouage_Opus_V_Iris_Accord_Current_Inventory.md) as the locked rich version.

Use it for:
- incense
- amber
- suede
- leather
- dark woods
- dressed-up niche floral-woods

### 3. Light / Air

Use [Opus_V_Iris_Light_1000uL.md](d:\chatbots\perfume-chem\Opus_V_Iris_Light_1000uL.md) when the perfume has to stay cleaner, cooler, and less root-heavy.

This is the better branch for:
- clean musk
- transparent wood
- bright floral
- office-safe modern iris
- sport-adjacent builds

### 4. Shadow Booster

Use [Opus_V_Iris_Shadow_Booster_1000uL.md](d:\chatbots\perfume-chem\Opus_V_Iris_Shadow_Booster_1000uL.md) as a low-dose darkening module instead of baking all the darkness into every iris accord.

This is for:
- incense
- dry woods
- amber
- suede
- library / parchment / root effects

---

## Family Usage Guide

- `Floral / musky / modern clean`: start with `Crystal` at `8-15%` of concentrate.
- `Transparent woody / ambroxan / mineral`: start with `Crystal` at `6-12%`, or `Light` at `5-10%`.
- `Sport-adjacent / bright daily wear`: use `Light` at `4-9%`, then build lift outside the accord with citrus, linalool, hedione, and clean musks.
- `Woody / incense / amber / suede`: use `Crystal` at `8-14%` plus `Shadow Booster` at `2-6%`, or use `Signature Rich` directly at `10-25%`.
- `Full Opus V-inspired niche structure`: use `Signature Rich` at `15-30%`, then add the missing outer architecture: `rhum`, restrained `rose/jasmine`, and a dry `wood/oud/civet` frame.

Still poor fits even after crystallization:
- pure aquatics
- very bright citrus colognes
- ultra-sheer ozonics
- hard gym-sport profiles

Those families can borrow from the `Light` branch, but this DNA will still read as iris.

---

## Validation Snapshot

These checks were rerun locally on the new modules after normalizing the formulas to percentage input for the validator:

- `Crystal`: `validate_formula()` returned no hard errors; `analyze_formula_rule_coverage()` returned `24` positive pairs and `0` conflict pairs.
- `Light`: `validate_formula()` returned no hard errors; `analyze_formula_rule_coverage()` returned `22` positive pairs and `0` conflict pairs.
- `Shadow Booster`: `validate_formula()` returned no hard errors; `analyze_formula_rule_coverage()` returned `44` positive pairs and `0` conflict pairs.

Warnings about high total concentration, low top notes, or weak base are expected because these are accord modules, not finished perfumes.

---

## Workflow Integration

The verification workflow now carries the new analysis layers together instead of treating them separately:
- material fingerprinting for formula shape and inventory neighbors
- synergy graph analysis for stacks, clashes, and musk fit
- chemical life graph for balance, gaps, temporal evolution, and health score

Use that bundle output as the default downstream review surface for any new `Opus V` branch.

---

## Bottom Line

The clean workflow is:
- keep the current file as the dark `Signature Rich` master
- use `Crystal` as the reusable brand-core iris
- use `Light` when the perfume must stay cleaner
- use `Shadow Booster` when the formula needs depth without re-darkening the whole accord

That preserves the `Opus V` iris identity while letting it move through many perfume families without forcing every formula to smell like the same dense root-powder base.
