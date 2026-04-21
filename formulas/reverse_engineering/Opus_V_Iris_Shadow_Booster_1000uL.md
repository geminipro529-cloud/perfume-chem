# Opus V Iris Shadow Booster — 1000uL

**Date:** 2026-04-04  
**Purpose:** darkening and anchoring module for the `Opus V` iris family  
**Role In The Module Set:** low-dose structural booster, not a universal standalone accord  
**Related Guide:** [Opus_V_Iris_Accord_Family_Guide.md](d:\chatbots\perfume-chem\Opus_V_Iris_Accord_Family_Guide.md)

---

## Intent

This is the part you add when a perfume needs more:
- dry shadow
- root depth
- wood grain
- incense weight
- suede / parchment / library atmosphere

It is **not** the default iris core.

It exists so that the `Crystal` and `Light` versions do not have to carry this darkness all the time.

---

## Formula

Build this as a **1000 uL booster module**.

| # | Material | Dilution | uL | % of Module | Function |
|---|---|---|---:|---:|---|
| 1 | Alpha Irone | 10% | 200 | 20.0 | Keeps the booster tied to the iris family |
| 2 | Orivone | neat | 40 | 4.0 | Darker buttery-metallic body |
| 3 | Orris F-TEC | neat | 60 | 6.0 | Waxy root mass |
| 4 | Methyl Ionone Pure | neat | 80 | 8.0 | Iris volume |
| 5 | I-IRIS F-TEC | neat | 25 | 2.5 | Iris lift so the booster does not go muddy |
| 6 | Alpha Ionone | neat | 20 | 2.0 | Violet flash |
| 7 | Beta Ionone | neat | 20 | 2.0 | Dark violet depth |
| 8 | Allyl Ionone (Ketone V) | neat | 10 | 1.0 | Warm powder bridge |
| 9 | Dihydro Beta Ionone | neat | 30 | 3.0 | Dry woody-violet persistence |
| 10 | Irotyl | neat | 10 | 1.0 | Iris reinforcement |
| 11 | Ultralia | neat | 5 | 0.5 | Small cold halo |
| 12 | Carrot Seed EO | neat | 10 | 1.0 | Root realism |
| 13 | Rose Oxide | 1% | 5 | 0.5 | Concrete chill |
| 14 | Hedione | neat | 20 | 2.0 | Minimal breathing room |
| 15 | Bacdanol | neat | 40 | 4.0 | Creamy wood cushion |
| 16 | Ambrox Super | 30% w/v | 80 | 8.0 | Dry crystalline wood shadow |
| 17 | Vetival | neat | 50 | 5.0 | Earthy dry wood bridge |
| 18 | Heliotropin Fleuressence | neat | 15 | 1.5 | Powder-soft underlayer |
| 19 | Coumarin | 20% | 50 | 5.0 | Warm powder bridge |
| 20 | Clearwood | neat | 100 | 10.0 | Transparent dark wood body |
| 21 | Iso E Super | neat | 130 | 13.0 | Dry woody diffusion |
| | **TOTAL** | | **1000** | **100.0** | |

---

## Why This Works

### 1. It darkens without replacing the iris core

The booster still contains enough iris materials to stay in-family.

So when you add it to `Crystal` or `Light`, the perfume gets darker without feeling like a separate woody accord was dropped on top.

### 2. The shadow is modular now

The main darkening materials are:
- `Ambrox Super`
- `Vetival`
- `Clearwood`
- `Iso E Super`
- `Bacdanol`
- `Coumarin`
- `Heliotropin`

That lets you add drydown character only when the perfume asks for it.

### 3. The booster stays dry, not syrupy

This is a **dry shadow** module, not a resin bomb.

It is built for:
- incense
- woods
- suede
- amber-wood
- mineral parchment effects

If you need resin, oud, or animalic facets, add those outside this module.

---

## Mixing Order

1. Add the dark structural base:
   `Bacdanol`, `Coumarin (20%)`, `Ambrox Super (30% w/v)`, `Vetival`, `Heliotropin Fleuressence`, `Clearwood`, `Iso E Super`.
2. Add the iris body:
   `Orivone`, `Methyl Ionone Pure`, `Orris F-TEC`, `I-IRIS F-TEC`, `Allyl Ionone (Ketone V)`, `Dihydro Beta Ionone`, `Irotyl`, `Ultralia`.
3. Add the irone-violet section:
   `Alpha Ionone`, `Beta Ionone`, `Alpha Irone (10%)`.
4. Add `Hedione`.
5. Add `Carrot Seed EO`.
6. Add `Rose Oxide (1%)` last.
7. Rest `7-10 days` minimum.
8. Best read: `14-21 days`.

---

## How To Use It

- with `Crystal`: `2-6%` of total concentrate
- with `Light`: `1-4%`
- in dark woods / incense / amber builds: up to `8%`

Do not use this as the only iris accord unless you explicitly want a dark, structural, wood-loaded iris effect.

---

## Adjustment Knobs

If it is too dry:
- reduce `Ambrox Super (30% w/v)` by `10-20 uL`
- reduce `Vetival` by `10 uL`

If it is too powdery:
- reduce `Coumarin (20%)` by `10 uL`
- reduce `Heliotropin Fleuressence` by `5 uL`

If it lacks structure:
- raise `Clearwood` by `10-20 uL`
- raise `Iso E Super` by `10-20 uL`

If it needs more iris legibility:
- raise `Alpha Irone (10%)` by `20 uL`
- raise `Orris F-TEC` by `10 uL`

---

## Module Check

This version was checked locally after normalizing the `1000 uL` formula into percentage input for the validator:

- `validate_formula()` returned no hard errors
- `analyze_formula_rule_coverage()` returned `44` positive pairs and `0` conflict pairs

The remaining warnings are expected because this is a concentrated booster module rather than a finished perfume.

---

## Bottom Line

Use this when the formula needs the `Opus V` iris family to read:
- darker
- drier
- woodier
- more root-shadowed

Keep it modular, and the rest of the iris system stays much more usable.

---

## Verification Snapshot

Module-aware verification was run on `2026-04-05`.

- `validate_formula()` still returned no hard errors
- chemical-life `structure mode` = `module`
- health score = `30.9 / 100` as a booster module, not as a finished perfume
- no formula correction applied after the run

What the run says in plain language:
- this is working exactly like a booster, not like a standalone accord
- it starts base-heavy on purpose
- the current `2-6%` usage band remains the right safe band

The main caution remains dosage, not correctness:
- if you overdose it, `Ambrox Super`, `Iso E Super`, `Clearwood`, `Vetival`, and `Coumarin` will take over fast

---

## Temporal Graph

![Temporal Graph](Opus_V_Iris_Shadow_Booster_1000uL_Temporal_Graph.png)

Plain-English read:
- opens `base-led`
- stays base-heavy for hours
- handoff is `base -> heart` only around `8 hr`
- the late carriers are `Alpha Irone`, `Methyl Ionone Pure`, `Orivone`, and `Dihydro Beta Ionone`

That is correct for a shadow booster. It is supposed to darken and anchor another iris module, not wear like a balanced standalone perfume.
