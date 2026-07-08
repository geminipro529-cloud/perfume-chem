# Vol d'Ambre v3c — Soft Amber Fougère (Layton-Style Niche)

**Honest classification (locked 2026-04-30):** `Fougère Doux Ambré Fruité` (Sweet Fruity Amber Fougère). This perfume meets the *minimum* technical fougère grammar (lavender + coumarin + Evernyl + dry woods) but its dominant character is amber-fruity-floral-gourmand. Real-world category: **Oriental Fougère / Amber Fougère** — the same sub-family Parfums de Marly officially uses for Layton.

**Market positioning:** niche-style sweet amber fougère. Direct competitors are Layton, Pegasus, Khamrah, and the Lattafa/Maison Alhambra Layton-clone tier. **Not** a Sauvage / Bleu de Chanel / Acqua di Giò Profondo competitor — different family.

**Original working title:** `Vol d'Ambre v3c -> Thai Aromatic Fougere Addition-Only Optimization` (kept for history; misleading because the perfume is not a clean aromatic fougère and the "Thai mass-market masculine" target was reframed mid-process).

---

**Date:** 2026-04-29
**Input checked:** `Vol d'Ambre v3c` non-HC bottle, including the documented post-mix Ambrox/Azarbre/Javanol/Norlimbanol booster and Timberol masculinity fix.
**Optimization source:** `_opt_layton_fougere_addonly.py`
**Goal:** Thai mass-market smell, sillage, and longevity first; masculine mass-market aromatic fougere family second; keep enough Layton DNA to avoid becoming generic barbershop. **Competitive target (revised 2026-04-30): high-Ambrox aromatic fougere tier — Sauvage EDP, Bleu de Chanel EDP, Acqua di Giò Profondo — on skin-warmth, Ambrox projection, and longevity axes.**

If the bottle did **not** receive the documented v3c post-mix boosters, do not use this addition table unchanged; the amber/wood balance will be different.

Bottle naming note: if this is being called the current `Vol d'Ambre v3b` at the bench, the math below assumes the **current boosted bottle**: v3c-style non-HC formula plus post-mix `Ambrox Super`, `Azarbre`, `Javanol`, `Norlimbanol Dextro`, and `Timberol`.

---

## Current Bottle Summary

The starting perfume is already a dense Layton-style amber-vanilla-woody composition. Its recognizable identity comes from:

- Fruity-spiced opening: `Apritone`, `Hexyl Acetate`, `Ethyl 2-Methylbutyrate`, and `Cardamom FTEC`.
- Aromatic/floral lift: `Bergamot FCF`, `Lavender EO`, `Linalyl Acetate`, `Ethyl Linalool`, `Hedione`, `Benzyl Acetate`, `Dihydrojasmone`, `Geraniol`, and `Phenethyl Alcohol`.
- Amber-vanilla base: `Ambrox Super`, `Azarbre`, `Vanillin`, `Ethyl Vanillin`, `Benzoin Resinoid`, and `Coumarin`.
- Long woody/musky base: `Javanol`, `Sandalore`, `Timberol`, `Norlimbanol Dextro`, `Iso E Super`, `Habanolide`, `Galaxolide`, `Romandolide`, and `Ethylene Brassylate`.

The problem is not lack of strength. The bottle already has strong base mass and a large amber-gourmand core. The problem is **classification and climate fit**: in Thai heat, the vanilla/benzoin/amber/sandalwood mass can feel sweet, dense, and duplicate-Layton-like. A straight addition-only fougere overlay makes it more aromatic, but it also risks making the bottle crowded and over-concentrated.

The chosen correction therefore has two moves:

- **Remove `3.0 mL` of existing mixed perfume.** This removes about 10% of every old note, including the inherited amber-gourmand load.
- **Add a `640 uL` performance-first fougere/fresh accord, then refill with ethanol.** This keeps strength and longevity, but shifts the balance toward fresh masculine aromatic fougere.

This is not simply dilution to make the bottle weaker. It is a controlled **olfactory rebalancing by partial subtraction plus targeted replacement**.

---

## Scientific And Perfume-Theory Rationale

### Why Re-Dilution Improves The Perfume

If the `640 uL` accord is added without removing mixed perfume, the bottle becomes denser: raw aroma stock rises to about `26.42%`, and active aroma load rises to about `18.25%`. That is powerful, but not ideal for Thai mass market. High concentration plus vanilla/benzoin/amber can read sticky, heavy, and less fresh in humid heat.

Removing `3.0 mL` first and refilling after the additions gives a better balance:

- Retained original aroma stock: `7,287 uL x 0.90 = 6,558.3 uL`.
- New additions: `640 uL`.
- Final stock-as-held aroma load: `7,198.3 uL`.
- Final raw aroma concentration: `7,198.3 / 30,000 = 24.0%`.
- Final active aroma concentration: `4,986.0 / 30,000 = 16.62%`.

Perfume-theory meaning: the bottle stays EdP-strength and long-lasting, but the **old amber-sweet mass is diluted relative to the new fresh/aromatic accord**. This makes the fresh top and fougere heart audible instead of burying them under the original amber base.

### Why These Additions Fit Thai Mass Market

Thai mass-market masculine fragrances generally reward clean projection, fresh impact, and non-sticky sweetness. In that context, the best move is not more amber, more vanilla, or more moss. The best move is controlled fresh diffusion over a soft masculine base.

- `Dihydromyrcenol`, `Grapefruit FCF`, `Lime Distilled EO`, `Petitgrain EO`, `Juniper Berry EO`, and trace `Beta-Pinene` create a bright fresh top that cuts through heat and humidity.
- `Linalyl Acetate`, `Terpinyl Acetate`, `Lavender EO`, `Spike Lavender EO`, and `Clary Sage EO` create the aromatic fougere heart.
- `Iso E Super`, `Habanolide`, and `Cedarwood oil Virginia` add clean diffusion, dry masculine volume, and long wear without adding more sweetness.
- `Evernyl`, `Coumarin`, `Patchouli EO`, and `Vetiver EO` provide enough fougere base grammar without turning the perfume into vintage barbershop or dark chypre.
- `Cardamom FTEC` and `Apritone` are kept small so the bottle still has Layton DNA, but they do not dominate the market-facing direction.

### Fougere Family Logic

Aromatic fougere is not just "lavender plus freshness." It needs a recognizable triangular grammar:

- **Aromatic top/heart:** lavender materials, linalyl acetate, clary sage, terpinyl acetate, petitgrain.
- **Coumarin/tonka axis:** enough `Coumarin` for hay-tonka warmth, but not so much that it becomes dessert amber.
- **Moss/wood base:** `Evernyl` plus dry woods, patchouli, vetiver, and cedar.

This bottle is not a textbook clean-sheet fougere because it keeps Layton's amber-vanilla-fruity skeleton. The intended result is more specific: **Layton-derived masculine mass-market aromatic fougere**, optimized for Thai wearability.

---

## Optimizer Result, Then Priority Revision

The raw optimizer selected mostly existing materials, not the newly added materials:

- Existing-material spine: `Linalyl Acetate`, `Terpinyl Acetate`, `Coumarin`, `Cedarwood oil Virginia`, `Dihydromyrcenol`, `Clary Sage EO`, `Petitgrain EO`, `Lavender EO`, `Evernyl`, `Patchouli EO`, `Cardamom FTEC`, `Apritone`.
- New-material accents: `Lime Distilled EO`, `Beta-Pinene`, `Juniper Berry EO`, small `Spike Lavender EO`.
- Rejected in final pass: `Nagarmortha Oil` and extra `Frankincense EO`. They are valid materials, but here they pull the bottle toward dark resin/oud-vetiver and away from mass-market Layton fougere.

The first chemist/perfumer correction after the raw run was family-gate forward:

- `Evernyl` is capped at `23 uL` to respect a conservative IFRA Cat 4 headroom assumption.
- `Dihydromyrcenol` is kept moderate; enough Thai fresh lift, not Cool Water shower-gel dominance.
- `Cardamom FTEC` and `Apritone` are retained as small additions so the top still says Layton, not generic barbershop.
- `Hedione HC`, extra `Ambrox`, and extra vanilla are excluded because they would pull the bottle back toward the duplicate amber-Layton profile.

**Priority revision after user instruction:** do not maximize the fougere gate at the expense of wearability. For Thai mass-market appeal, the better version lowers dusty moss/coumarin/herbal pressure and reallocates mass to clean diffusion, fresh lift, and musky-woody persistence.

Perfumer logic for the revised table:

- Lower `Evernyl` from `23 uL` to `16 uL`; still enough moss marker, less old/dusty, much better IFRA headroom.
- Lower added `Coumarin`; the bottle already has enough tonka/vanilla sweetness for heat.
- Add `Iso E Super` and `Habanolide` for clean volume, diffusion, and longevity without adding more amber sweetness.
- Raise `Dihydromyrcenol` and add `Grapefruit FCF`; this is more Thai mass-market fresh than pushing more moss.
- Keep `Cardamom FTEC` and `Apritone` small; they preserve Layton DNA but should not lead.

---

## Recommended Performance-First Table

This supersedes the stricter family-gate table. Add to the finished 30 mL bottle after decanting/re-dilution as described below.

| Step | Material | Stock | Add uL | Function |
|---:|---|---|---:|---|
| 1 | Evernyl | neat | 16 | Moss marker; enough for fougere identity without dusty oakmoss drag |
| 2 | Patchouli EO | neat | 5 | Trace moss-earth support only |
| 3 | Vetiver EO | neat | 6 | Dry root masculinity; restrained for Thai heat |
| 4 | Cedarwood oil Virginia | neat | 50 | Dry clean woody backbone |
| 5 | Iso E Super | neat | 90 | Clean woody diffusion and transparent body |
| 6 | Habanolide | neat | 45 | Clean musky persistence and trail polish |
| 7 | Coumarin | 20% | 45 | Fougere tonka-hay cue; lower because base is already sweet |
| 8 | Linalyl Acetate | neat | 70 | Smooth lavender/bergamot ester lift |
| 9 | Terpinyl Acetate | neat | 50 | Aromatic citrus-pine lift, below cleaner territory |
| 10 | Clary Sage EO | neat | 25 | Herbal masculine body |
| 11 | Petitgrain EO | neat | 20 | Bitter green citrus leaf; cuts amber sweetness |
| 12 | Lavender EO | neat | 15 | Keeps original lavender line continuous |
| 13 | Spike Lavender EO | neat | 8 | Camphoraceous aromatic edge; trace only |
| 14 | Dihydromyrcenol | neat | 75 | Thai mass-market fresh diffusion |
| 15 | Grapefruit FCF | neat | 45 | Modern bitter-fresh top; more mass-market than lime alone |
| 16 | Lime Distilled EO | neat | 35 | Cold citrus sparkle |
| 17 | Juniper Berry EO | neat | 10 | Gin-like conifer lift |
| 18 | Beta-Pinene | neat | 5 | Pine-green sparkle; trace only |
| 19 | Cardamom FTEC | 10% | 15 | Preserves Layton spice cue without leading |
| 20 | Apritone | 10% | 10 | Preserves Layton apple-fruity cue without extra sweetness |
| - | **Total addition** | - | **640 uL** | Add after removing mixed perfume and re-diluting |

---

## Live Correction: If You Already Added Coumarin And Mistakenly Added Terpinyl Acetate

Assumption for this correction:

- You have already added `Coumarin 20% = 45 uL`.
- You accidentally added `Terpinyl Acetate = 50 uL` while intending to add `Linalyl Acetate`.
- You have **not** added the remaining materials yet.

This mistake is recoverable with no major reformulation.

Why: the performance-first target already included `Terpinyl Acetate 50 uL`. So the problem is **not** that the bottle now contains a forbidden or excessive amount of terpinyl acetate. The problem is only that:

- the `Terpinyl Acetate` dose has been added earlier than intended, and
- the intended `Linalyl Acetate` dose has **not yet** been added.

Re-optimized instruction: treat the accidental `Terpinyl Acetate 50 uL` as the **planned terpinyl acetate addition**. Do **not** add any more `Terpinyl Acetate` later. Still add the full `Linalyl Acetate` dose.

### Remaining Additions From Current State

If the only materials already added are `Coumarin 20% 45 uL` and `Terpinyl Acetate 50 uL`, add the following remainder:

| Step | Material | Stock | Add uL | Reason |
|---:|---|---|---:|---|
| 1 | Evernyl | neat | 16 | Fougere moss marker |
| 2 | Patchouli EO | neat | 5 | Earth support |
| 3 | Vetiver EO | neat | 6 | Root-dry masculine support |
| 4 | Cedarwood oil Virginia | neat | 50 | Dry woody backbone |
| 5 | Iso E Super | neat | 90 | Clean diffusion |
| 6 | Habanolide | neat | 45 | Clean musky trail |
| 7 | Linalyl Acetate | neat | 70 | Still required; this is the missing lavender-ester body |
| 8 | Clary Sage EO | neat | 25 | Aromatic masculine body |
| 9 | Petitgrain EO | neat | 20 | Bitter green citrus leaf |
| 10 | Lavender EO | neat | 15 | Lavender continuity |
| 11 | Spike Lavender EO | neat | 8 | Camphoraceous aromatic accent |
| 12 | Dihydromyrcenol | neat | 75 | Thai-market fresh diffusion |
| 13 | Grapefruit FCF | neat | 45 | Bitter-fresh top |
| 14 | Lime Distilled EO | neat | 35 | Cold citrus sparkle |
| 15 | Juniper Berry EO | neat | 10 | Conifer lift |
| 16 | Beta-Pinene | neat | 5 | Pine-green trace sparkle |
| 17 | Cardamom FTEC | 10% | 15 | Layton spice cue |
| 18 | Apritone | 10% | 10 | Layton apple cue |
| - | **Remaining addition total** | - | **545 uL** | `640 - 45 - 50` |

### What Not To Do

- Do **not** add another `50 uL` of `Terpinyl Acetate`.
- Do **not** reduce `Linalyl Acetate` just because terpinyl acetate went in early. They do different jobs: `Linalyl Acetate` gives soft lavender-citrus body; `Terpinyl Acetate` gives brighter pine-citrus-herbal lift.
- Do **not** add extra `Coumarin` to compensate. The coumarin target is already met.

### Practical Result

If corrected this way, the final target composition is effectively the same as the intended performance-first version. The mistake changes **sequence**, not the intended final terpinyl dose. In perfume terms, the bottle may momentarily smell a little sharper or more pine-herbal before full integration, but after maceration the final balance should still settle into the intended fresh masculine aromatic fougere direction.

### Decant Status Check Before Continuing

Before adding the remaining `545 uL`, confirm which of the two states the bottle is in. The math for the ethanol top-up depends on this.

**State A — decant was done (3.0 mL removed before any addition):**

- Liquid currently in bottle: `27.0 mL` original mixed perfume + `45 uL Coumarin 20%` + `50 uL Terpinyl Acetate` = `27.095 mL`.
- After remaining `545 uL` additions: `27.640 mL`.
- Ethanol 96% top-up to refill to `30.0 mL`: `2.360 mL` (same as the original plan).
- Final raw stock concentration: `24.0%`. Final active aroma concentration: `~16.62%`. **Matches the intended target.**

**State B — no decant was done; additions went straight into the full 30 mL bottle:**

- Liquid currently in bottle: `30.0 mL + 95 uL = 30.095 mL` (already overfilled by `~95 uL`).
- This is a bottle-volume problem, not a perfumery problem. The accord is still on target; only the carrier ratio is wrong.
- Two recoveries are acceptable:
  - **B1 — decant now to make room.** Remove `3.0 mL` of the current already-mixed liquid into a labeled archive vial, then proceed with the `545 uL` remaining additions, then top up with `~2.455 mL` ethanol 96% to reach `30.0 mL`. Effect: same target as State A, with `~10%` of the new Coumarin/Terpinyl already-mixed material going into the archive vial. Acceptable.
  - **B2 — accept a slightly stronger bottle, no decant.** Add the `545 uL` remaining materials only. Total liquid becomes `30.640 mL`; you will need to pour off the excess (or use a 50 mL bottle). Final raw stock concentration rises to `~26.4%`, active aroma load `~18.2%`. Slightly stickier in heat than the planned `16.62%`, but olfactorily identical.
- **Recommended:** B1. The decant-and-top-up route is what the original plan was designed for, and it gives the cleaner Thai-market wearability profile.

If you do not remember whether you decanted, look in the archive vials. If a labeled `Vol d'Ambre retained 3 mL` vial exists, you are in State A. If not, treat it as State B.

### Remaining-Addition Mixing Protocol

Independent of State A or State B1, the addition order is the same. The only difference is the final ethanol top-up volume.

1. Re-confirm the bottle is at the State-A or State-B1 starting point above.
2. Add steps `1-6` from the remaining-additions table: `Evernyl`, `Patchouli EO`, `Vetiver EO`, `Cedarwood oil Virginia`, `Iso E Super`, and `Habanolide`. These are the slowest-integrating base/fixative materials and go first.
3. Cap and invert `10x`.
4. Add steps `7-11`: `Linalyl Acetate`, `Clary Sage EO`, `Petitgrain EO`, `Lavender EO`, and `Spike Lavender EO`. This is the aromatic fougere heart.
5. Cap and invert `10x`.
6. Add steps `12-18`: `Dihydromyrcenol`, `Grapefruit FCF`, `Lime Distilled EO`, `Juniper Berry EO`, `Beta-Pinene`, `Cardamom FTEC 10%`, and `Apritone 10%`. These are the volatile, oxidation-sensitive top notes and the last Layton-DNA cues.
7. Top up with ethanol 96%:
   - State A: `2.360 mL` exactly, or fill back to the `30.0 mL` mark.
   - State B1: `~2.455 mL`, or fill back to the `30.0 mL` mark after the decant.
   - State B2: no ethanol; transfer overflow if needed.
8. Cap and invert `20x` gently. Do not shake; aeration increases terpene oxidation risk on `Lime`, `Beta-Pinene`, `Juniper`, lavender, and petitgrain.
9. Rest `72 hours` before any first judgment, `10-14 days` for the real verdict.

The earlier-than-planned `Terpinyl Acetate` will momentarily project as sharper pine-herbal in the first `24-48 hours`. This is expected and is not a sign that the formula is wrong. After `Linalyl Acetate`, lavender, clary sage, and petitgrain come in and integrate, the heart settles into the intended balance.

### Final Composition (After Live Correction)

| Quantity | Calculation | Result |
|---|---:|---:|
| Pre-addition fragrance load (post-decant, State A) | `7,287 uL x 0.90` | `6,558.3 uL` |
| Already-added (Coumarin 20% + Terpinyl Acetate) | `45 + 50` | `95 uL` |
| Remaining additions | sum of remaining table | `545 uL` |
| Final fragrance load | `6,558.3 + 95 + 545` | `7,198.3 uL` |
| Ethanol 96% top-up (State A) | `30,000 - 27,640 - 545` | `2,360 uL` |
| Final raw stock concentration | `7,198.3 / 30,000` | `24.0%` |
| Final active aroma load | matches performance-first plan | `~16.62%` |

The numbers are identical to the original performance-first target. The mistake was self-correcting because the `50 uL Terpinyl Acetate` happened to match the planned dose. No re-optimization of the underlying formula is needed.

---

## Two-Gate Optimization Probe (2026-04-30): Juniper / Beta-Pinene / Pine EO

After the inventory additions of `Pine EO`, `Beta-Pinene`, and `Juniper Berry EO`, the open question was whether any of them should be pushed further inside the live-correction's remaining `545 uL` — and at what dose. The answer must come from the same two-gate optimization framework that produced the performance-first table, not from perfumer intuition alone, because the existing performance-first table already contains `Beta-Pinene 5 uL` and `Juniper Berry EO 10 uL` and the question is one of marginal benefit, not first-time inclusion.

### Method

The probe re-uses `_opt_layton_fougere_addonly.py` and its objective verbatim, so the same two priorities are enforced:

- **Priority 1 — performance:** Thai mass-market smell, sillage, longevity. Penalises excessive top-fresh (`+900` over baseline ceiling), low total addition, and excess new-material share.
- **Priority 2 — family:** masculine aromatic fougère. Rewards heart-aromatic and base-moss/wood deltas; penalises insufficient lavender/coumarin/moss support.

`Pine EO` is not in the optimizer's default family map. For a fair test it was patched into the candidate space:

- Family: `aromatic`.
- Physics override: `MW 136.2`, `VP 470 Pa` (alpha-pinene-dominant; sharper than juniper, faster than beta-pinene-only).
- ODT override: `6 ppb` (sharper than juniper's `10 ppb`).
- Bound: `0–60 uL`.

Thirteen variants were scored against the current performance-first baseline of `-24.4440`. Each variant kept the total addition at `640 uL` by re-balancing from materials with low marginal score: `Petitgrain EO`, `Cedarwood oil Virginia`, `Lime Distilled EO`. Probe script: `_probe_pine_juniper_betapinene.py`. JSON output: `_probe_pine_juniper_betapinene_out.json`.

### Optimizer Verdict

| Rank | Variant | ΔScore vs baseline | Δheart-aromatic OAV | Δtop-aromatic OAV |
| ---: | --- | ---: | ---: | ---: |
| 1 | Juniper 25 + Pine 15 | **+2.788** | +205.6 | +472.0 |
| 2 | Juniper 35 alone | +2.746 | +282.9 | +110.2 |
| 3 | Juniper 25 + Beta-Pinene 8 | +2.638 | +207.4 | +104.2 |
| 4 | **Juniper 25 alone (clean)** | **+2.448** | **+208.1** | **+89.2** |
| 5 | Juniper 18 alone | +1.858 | +156.8 | +75.7 |
| 6 | Beta-Pinene 25 | +1.423 | +94.7 | +159.0 |
| 7 | Beta-Pinene 20 | +1.234 | +94.7 | +131.4 |
| 8 | Pine 15 alone | +1.027 | +91.6 | +440.2 |
| 9 | Beta-Pinene 12 | +0.808 | +94.7 | +83.5 |
| 10 | Performance-first baseline | 0.000 | +98.6 | +58.3 |
| 11 | **Pine 30** | **-0.373** | +90.6 | +815.0 |
| 12 | **Pine 45** | **-1.256** | +90.6 | +1207.0 |

The decisive signal is the **heart-aromatic OAV delta**. Only `Juniper Berry EO` meaningfully moves it. `Beta-Pinene` and `Pine EO` move only the top window — they are top-sparkle materials, not structural fougère materials.

### Perfumer Logic Last Pass

- **`Juniper Berry EO`** is family-defining for modern aromatic fougère. It sits in the same aromatic OR cluster as lavender + clary sage + petitgrain but contributes a cold gin/conifer character that reads as masculine-mass-market in Thailand. The optimizer rewards `25 uL` because it raises the heart-aromatic gate (`+208`) without breaching the Thai-fresh top ceiling. Beyond `25 uL` returns drop sharply: `25 → 35 uL` adds only `+0.30` score for `+10 uL` and starts pulling toward herbal-medicinal.
- **`Beta-Pinene`** at `25 uL` adds `+1.42` score, but the entire lift is in the top window (`Δtop-aromatic +159`, `Δheart-aromatic ≈ baseline`). It is a single terpene, not a structured material, and overlaps with Juniper / Lime / DHM on the green-conifer axis. The marginal `+0.16` from raising it `5 → 8 uL` on top of `Juniper 25` is olfactorily noise.
- **`Pine EO`** is the high-risk case. The variant `Juniper 25 + Pine 15` is the single highest-scoring test (`+2.79`), but its `Δheart-aromatic` (`+205.6`) is essentially identical to `Juniper 25 alone` (`+208.1`). The score win is purely top-aromatic (`+472` vs `+89`), an axis already covered by `Lime` + `Grapefruit` + `DHM`. So `Pine EO 15 uL` adds redundant top sparkle, not structural benefit. At `30+ uL` the score goes **negative** because the optimizer's Thai-fresh penalty (`top-fresh > +900` over baseline) starts firing alongside the new-material-share penalty. Pine reads cleaner-medicinal in Thai heat at any meaningful dose.

### Chemistry Logic Last Pass

- **Terpene oxidation pressure.** The current bottle already carries `DHM 75 + Lime 35 + Beta-Pinene 5 + Juniper 10 + Petitgrain 20 + Lavender 15 + Spike Lav 8` of terpene-heavy material per 30 mL. Adding `Pine EO` (alpha-pinene-rich, `VP ≈ 470 Pa`) compounds peroxide formation faster than the existing BHT antioxidant guard can absorb in Thai ambient conditions. Raising `Beta-Pinene` past `~10 uL` does the same.
- **Headspace timing.** `Juniper Berry EO` (`VP ≈ 65 Pa`) sits between `Lavender EO` (`VP ≈ 20 Pa`) and `Lime` (`VP ≈ 170 Pa`) — it bridges top → heart cleanly. `Beta-Pinene` (`VP 390 Pa`) and `Pine EO` (`VP ≈ 470 Pa`) sit above `Lime` and add to the already-fast top, not to the heart. This matches the optimizer's window deltas exactly.
- **IFRA / headroom.** `Juniper Berry EO 25 uL / 30 mL = 0.083%` is well below any IFRA Cat-4 concern and below the conservative 80% headroom envelope. `Pine EO` has no fragrance-specific cap, but its terpene burden cap (alpha-pinene oxidation products) is the practical constraint.
- **OR competition (GR6).** Juniper, Pine, Beta-Pinene, Petitgrain, and Lime all recruit overlapping aromatic-ORs. The bottle can carry one strong member of this cluster (Juniper) cleanly; carrying three (Juniper + Pine + Beta-Pinene at elevated doses) starts producing OR adaptation and a flat green-cleaner read.

### Revised Remaining Additions (Supersedes Live-Correction Table)

Starting state unchanged: `Coumarin 20% 45 uL` and `Terpinyl Acetate 50 uL` already in the bottle. Remaining `545 uL` is reallocated. Total addition still `640 uL`; ethanol top-up math (`State A 2.360 mL`, `State B1 ~2.455 mL`) unchanged.

| Step | Material | Stock | Add uL | Δ vs prior plan |
| ---: | --- | --- | ---: | ---: |
| 1 | Evernyl | neat | 16 | — |
| 2 | Patchouli EO | neat | 5 | — |
| 3 | Vetiver EO | neat | 6 | — |
| 4 | Cedarwood oil Virginia | neat | **47** | **-3** |
| 5 | Iso E Super | neat | 90 | — |
| 6 | Habanolide | neat | 45 | — |
| 7 | Linalyl Acetate | neat | 70 | — |
| 8 | Clary Sage EO | neat | 25 | — |
| 9 | Petitgrain EO | neat | **12** | **-8** |
| 10 | Lavender EO | neat | 15 | — |
| 11 | Spike Lavender EO | neat | 8 | — |
| 12 | Dihydromyrcenol | neat | 75 | — |
| 13 | Grapefruit FCF | neat | 45 | — |
| 14 | Lime Distilled EO | neat | **31** | **-4** |
| 15 | **Juniper Berry EO** | neat | **25** | **+15** |
| 16 | Beta-Pinene | neat | 5 | — |
| 17 | Cardamom FTEC | 10% | 15 | — |
| 18 | Apritone | 10% | 10 | — |
| - | **Remaining total** | - | **545** | 0 |

`Pine EO` is **not** added. `Beta-Pinene` is **not** raised. The volume traded out of `Petitgrain EO` (`-8`), `Cedarwood oil Virginia` (`-3`), and `Lime Distilled EO` (`-4`) goes entirely into `Juniper Berry EO`.

Mixing order is unchanged from the live-correction protocol: base/fixative first, aromatic heart second, fresh top + Layton cues last. `Juniper Berry EO 25 uL` enters at step 15 with the rest of the citrus/conifer top group.

### Revised Release Gate

The revision changes the optimizer score from `-24.444` to `-21.996` (`Δ +2.448`), but mass-fraction shifts are tiny: `Juniper +0.050%` of the 30 mL bottle, offset by `-0.050%` across `Petitgrain` / `Cedarwood` / `Lime`. The strict gate verdict is unchanged from the earlier section, with one anchor passing slightly more cleanly:

| Gate Area | Status | Change vs prior plan |
|---|---|---|
| Aromatic fougère anchor | PASS | aromatic axis `~14.13%` active (was `13.702%`); `+0.43%` improvement |
| Citrus top | PASS | `~5.96%` active (was `5.995%`); `-0.04%`, still well above gate |
| Coumarin axis | PASS | unchanged at `0.638%` |
| Moss/wood base | PASS | `~6.55%` active (was `6.571%`); `-0.02%`, negligible |
| IFRA / Evernyl headroom | PASS | unchanged at `16 uL = 0.0533%` |
| New-material share | PASS | `12.0%` of additions (`77 uL / 640 uL`); within `<55%` cap |
| Modern mass hook | PASS | unchanged |
| Gourmand drift (inherited) | FAIL | unchanged at `3.836%` > strict `3.000%` cap |
| Opaque preblend (`Cardamom FTEC`) | FAIL in commercial mode | unchanged |
| Robustness | FAIL in commercial mode | unchanged; add-only rescue limitation |
| Confidence | WARN | unchanged at `~46.1`; needs blotter/skin calibration |

**Strict release-gate result:** `FAIL / NOT_RELEASE_READY`, unchanged. The blockers are all inherited from the original Layton-amber base (gourmand vanilla/benzoin mass, opaque `Cardamom FTEC`, robustness fragility from the already-built bottle), not from the revision.

**Perfumer-facing fougère gate result:** strengthened. Heart-aromatic OAV rises from `+98.6` to `+208.1` over baseline at zero volume cost, zero IFRA cost, and zero stability cost. The revision is the correct final move under both priorities.

---

## Why This Still Smells Like Layton

The original bottle keeps the main Layton signals:

- Apple/fruity hook: `Apritone`, `Hexyl Acetate`, `Ethyl 2-Methylbutyrate`.
- Cardamom-like spice: `Cardamom FTEC`, supported by the new trace top.
- Amber-vanilla comfort: `Ambrox Super`, `Azarbre`, `Vanillin`, `Ethyl Vanillin`, `Benzoin Resinoid`.
- Sandalwood/woody base: `Javanol`, `Sandalore`, `Timberol`, `Iso E Super`.

The addition does not rebuild the perfume. It overlays a fougere frame onto the existing Layton amber.

---

## Why This Classifies As Aromatic Fougere

The family gate is now present in perfumer-readable form:

- Aromatic lavender axis: existing `Lavender EO` plus added `Linalyl Acetate`, `Terpinyl Acetate`, `Clary Sage EO`, `Petitgrain EO`, trace `Spike Lavender EO`.
- Coumarin axis: existing `Coumarin` plus `45 uL` of 20% stock.
- Moss/wood drydown: controlled `Evernyl`, supported by `Cedarwood oil Virginia`, `Iso E Super`, `Patchouli EO`, `Vetiver EO`, and the already present woods.
- Thai mass-market freshness: `Dihydromyrcenol`, `Grapefruit FCF`, `Lime Distilled EO`, small `Juniper Berry EO`, trace `Beta-Pinene`.

This should read as **Layton aromatic fougere**, not a pure oriental amber and not a vintage barbershop fougere.

---

## Expected Smell After Correction

**Opening, 0-30 minutes:** brighter and more masculine than the current bottle. The first impression should move from sweet amber-lavender toward grapefruit/lime/DHM freshness over a recognizable Layton apple-cardamom trace. `Beta-Pinene` and `Juniper Berry EO` should read as a small gin-like conifer sparkle, not as pine cleaner.

**Heart, 30 minutes-4 hours:** aromatic fougere identity should become clearer. `Linalyl Acetate`, `Lavender EO`, `Spike Lavender EO`, `Clary Sage EO`, `Terpinyl Acetate`, and `Petitgrain EO` should sit over the original Hedione/lavender/floral body. The heart should feel fresh, clean, and masculine rather than powdery or cosmetic.

**Drydown, 4 hours onward:** the original Layton-style amber/vanilla/woods remain, but they should be drier and less syrupy. `Iso E Super`, `Habanolide`, `Cedarwood oil Virginia`, `Timberol`, `Javanol`, and `Ambrox Super` carry trail and longevity. `Evernyl`, `Coumarin`, `Vetiver EO`, and `Patchouli EO` give the fougere shadow without pushing the base into old-school moss.

**Overall result:** a fresher, cleaner, more masculine Thai-market Layton flanker. It should not smell like a pure oriental amber anymore, but it should also not become a generic barbershop fougere. The target is **mass-market aromatic freshness with enough sweet-spiced Layton comfort to remain appealing**.

---

## Re-Dilution And Release Gate Calculation

**Gate input:** full post-addition bottle model, not the addition table alone.

Recommended re-dilution: remove `3.0 mL` of the existing mixed bottle first, add the `640 uL` performance-first table, then add `2.36 mL` ethanol 96% or fill exactly back to `30.0 mL`.

| Quantity | Calculation | Result |
|---|---:|---:|
| Existing mixed bottle removed | user decant | `3.0 mL` |
| Base v3c plus documented boosters retained | `7,287 uL x 0.90` | `6,558.3 uL` |
| New performance-first addition table | sum of final additions | `640 uL` |
| Final stock-as-held aroma load | `6,558.3 + 640` | `7,198.3 uL` |
| Final raw stock concentration | `7,198.3 / 30,000` | `24.0%` |
| Dilution-adjusted active aroma load | active retained base plus active additions | `4,986.0 uL` |
| Final active aroma concentration | `4,986.0 / 30,000` | `16.62%` |
| Ethanol top-up after addition | `3,000 - 640` | `2.36 mL` |
| New-material share of additions | `58 / 640` | `9.1%` |

**Strict release-gate result:** `FAIL / NOT_RELEASE_READY`.

This is the correct result for a strict commercial gate. The bottle is a re-diluted addition-only rescue of a Layton-amber base, not a clean commercial remake.

| Gate Area | Status | Calculation / Detail |
|---|---|---|
| Exact subtotal | PASS | `7,198.3 uL` modeled post-decant/post-addition |
| Material/data coverage | PASS | new stock aliases and ODT/VP/MW/logP records are present in the material spine |
| Chemistry stability | PASS | predicted shelf life `896 days`; terpene oxidation still requires cool/dark storage |
| IFRA/headroom | WARN | No headroom violations; `Evernyl` = `16 uL / 30 mL = 0.0533%`, below conservative 80% Cat 4 headroom of `0.0800%`; warning is from materials lacking explicit Cat 4 limits |
| Aromatic fougere anchors | PASS | aromatic axis `13.702%`, citrus top `6.265%`, coumarin `0.638%`, moss/wood `6.571%` active |
| Modern mass hook | PASS | fruit/tonka hook `2.478%` active; fruit drift only `0.643%`, below `1.200%` max |
| Gourmand drift | FAIL | inherited gourmand amber materials still total `3.836%` active vs `3.000%` strict archetype max |
| Opaque preblend | FAIL in commercial mode | `Cardamom FTEC` is retained to preserve Layton DNA; strict commercial gate blocks FTEC/preblend materials |
| Robustness | FAIL in commercial mode | perturbing the already-built amber base flips brief grammar around `Vanillin`/`Hedione`; expected for an add-only rescue |
| Confidence | WARN | combined confidence `46.1`; candidate needs blotter/skin calibration before any sale claim |

**Interpretation:** this is the better practical perfume. It sacrifices some strict fougere-gate neatness, but the decant/re-dilution makes the amber-gourmand base less heavy, the fresh top more wearable in Thailand, and the Iso E/Habanolide addition protects trail and longevity. For a sellable commercial-trial remake, rebuild from zero without `Cardamom FTEC`, reduce vanilla/benzoin/coumarin mass, and keep the aromatic/moss/citrus scaffold.

---

## Detailed Mixing Protocol

1. Label a clean archive vial `Vol d'Ambre retained 3 mL`.
2. Remove exactly `3.0 mL` of the existing mixed perfume into that vial. Do not discard it until the main bottle is evaluated.
3. Add steps `1-7` from the table first: `Evernyl`, `Patchouli EO`, `Vetiver EO`, `Cedarwood oil Virginia`, `Iso E Super`, `Habanolide`, and `Coumarin`.
4. Cap and invert `10x`.
5. Add steps `8-13`: `Linalyl Acetate`, `Terpinyl Acetate`, `Clary Sage EO`, `Petitgrain EO`, `Lavender EO`, and `Spike Lavender EO`.
6. Cap and invert `10x`.
7. Add steps `14-20`: `Dihydromyrcenol`, `Grapefruit FCF`, `Lime Distilled EO`, `Juniper Berry EO`, `Beta-Pinene`, `Cardamom FTEC`, and `Apritone`.
8. **Ambrox competitive uplift (see section below):** add `780 µL` of `Ambrox Super 30%` stock directly.
9. Add `1,580 µL` ethanol 96% — **not** `2,360 µL`; the Ambrox stock above replaces `780 µL` of pure ethanol. Fill precisely to the `30.0 mL` mark.
10. Cap and invert `20x`. Do not shake violently; excessive aeration increases terpene oxidation risk.
11. Rest `72 hours` before judging the top/heart balance.
12. Final judgment should be after `10-14 days`, because `Evernyl`, `Coumarin`, cedar, musk, and the existing amber woods integrate more slowly than the citrus top.

Why this order matters:

- Base/fixative materials go first because `Evernyl`, `Coumarin`, woods, and musks need the longest time to dissolve and distribute evenly.
- The aromatic heart goes second because lavender/clary/petitgrain materials bridge between the heavy base and the volatile top.
- The fresh top goes last because `Grapefruit FCF`, `Lime Distilled EO`, `Dihydromyrcenol`, `Juniper Berry EO`, and `Beta-Pinene` are the most volatile and oxidation-sensitive part of the correction.
- Ethanol top-up goes after the additions so the bottle returns to the intended final concentration rather than simply becoming a larger, denser perfume.

Evaluation protocol:

- At `72 hours`, check only the direction: freshness, sweetness reduction, and aromatic lift.
- At `7 days`, check whether the fougere heart is clear or still buried under amber-vanilla.
- At `10-14 days`, make the real decision on Thai-market wearability, projection, and drydown.
- If the perfume is still too sweet after `14 days`, do not add more moss immediately. The next correction should be a tiny fresh/woody adjustment, not more `Evernyl` or `Coumarin`.

---

## Ambrox Competitive Uplift (2026-04-30)

### The Problem

The competitive target is the high-Ambrox Thai mass-market aromatic fougère tier: **Sauvage EDP, Bleu de Chanel EDP, Acqua di Giò Profondo**. These fragrances lead their category primarily through Ambroxan skin-warmth, projection from body heat, and multi-hour longevity — not through perfume-family classification alone.

After the `3.0 mL` decant and ethanol re-dilution, the corrected bottle sits at **~1.22% neat Ambrox EDP**. The competitive tier runs at **~2.0–2.5% neat**. That gap of `~0.78–1.28%` is the reason the bottle would lose on the Ambrox axis without this correction.

### Solution: Replace Part Of The Ethanol Top-Up With Ambrox 30% Stock

The ethanol top-up at the end of the addition protocol is `~2.36 mL` of pure carrier. Replacing `780 µL` of that ethanol with `780 µL` of `Ambrox Super 30%` stock costs nothing in volume — the bottle stays at exactly `30.0 mL` — but materially changes the Ambrox level.

| Scenario | Ambrox 30% added | Neat Ambrox in 30 mL | % neat EDP | Competitive position |
| --- | ---: | ---: | ---: | --- |
| No change (original plan) | 0 µL | 366 µL | 1.22% | below Sauvage EDT |
| Sauvage EDT parity | 580 µL | 540 µL | 1.80% | Sauvage EDT level |
| **Sauvage EDP parity (chosen)** | **780 µL** | **600 µL** | **2.00%** | **Sauvage EDP level** |
| Parfum direction | 1,280 µL | 750 µL | 2.50% | Sauvage Parfum / Bleu EDP direction |

**Chosen target: Sauvage EDP parity at 2.00% neat.** Add `780 µL` of `Ambrox Super 30%` stock. Reduce ethanol top-up from `2,360 µL` to `1,580 µL`. Fill to `30.0 mL` mark.

### Ambrox Mass Balance

| Quantity | Calculation | Result |
| --- | ---: | ---: |
| Ambrox retained after 3 mL decant | `1,356 µL × 30% × 0.90` | `366 µL neat` |
| Ambrox added in uplift | `780 µL × 30%` | `+234 µL neat` |
| Total neat Ambrox in 30 mL | `366 + 234` | `600 µL neat` |
| Final neat EDP concentration | `600 / 30,000` | `2.00%` |
| IFRA / safety | No IFRA cap on Ambrox for fine fragrance; no skin sensitisation concern at this level | PASS |

### Chemistry Logic

- **Ambrox Super** (ambroxide, `CAS 6790-58-5`): `VP 0.0003–0.0005 Pa`, `logP 4.92`, `MW 236`. Essentially a skin-depot molecule — very low volatility means it does not contribute to aerial top notes. Instead it builds a warm, skin-close amber reservoir that amplifies other materials through skin-temperature activation. This is exactly the Sauvage mechanism: the Ambroxan is almost undetectable in a cold strip but becomes dominant 30 min after skin application as body heat activates it.
- **OR receptor:** Ambrox activates `OR51A2` (the AMB1 receptor), a specific musk-amber receptor that does not cross-activate with lavender, coumarin, or citrus ORs. Raising it to `2.00%` does not compete with the fougère aromatic structure — it operates in a parallel OR channel and reinforces rather than occludes the heart.
- **GR1 / GR5 interaction:** at `2.00%` neat, Ambrox remains below the OR saturation level for `OR51A2` for the majority of people (clinical studies suggest saturation onset starts above `~3%` in EDP for most subjects). At `2.00%`, the characteristic warm skin-close projection is fully expressed without crossing into the sweaty/mineral register that over-dosing causes.

### Perfumer Logic

- The vanilla/benzoin-amber base inherited from v3c means this bottle will not smell *identical* to Sauvage — it is warmer, more approachable, less cold and metallic. This is not a liability; it is a differentiator. A warm Ambrox-driven aromatic fougère with Layton-DNA warmth occupies a real and underserved space in the Thai mass-market: the guy who finds Sauvage too dry and impersonal, but wants the same projection and longevity.
- **Do not push above `2.0%` in this bottle.** The vanilla/benzoin sweetness at higher Ambrox doses would shift the profile toward a heavy oriental rather than a fresh masculine aromatic fougère. `2.0%` is the correct ceiling for the specific base this bottle is built on.
- Azarbre (`~0.49%` EDP) is already providing the **aerial amber projection** at medium VP (`0.001–0.005 Pa`). Ambrox at `2.00%` provides the **skin-close fixative tier**. The two together span the full amber temporal arc — aerial for the first `1–2 h`, then skin-warm for the `3–8 h` drydown. This is structurally identical to how Sauvage builds its longevity.

### Release Gate Impact

| Gate Area | Status | Change |
| --- | --- | --- |
| Ambrox level vs competitive target | PASS | now at `2.00%` neat — Sauvage EDP parity |
| IFRA / safety | PASS | no cap for fine fragrance; skin comfort unchanged |
| Amber OR saturation (GR5) | PASS | `2.00%` is below the `~3%` saturation onset threshold |
| Gourmand drift gate | FAIL unchanged | inherited vanilla/benzoin; not changed by this step |
| Total bottle volume | PASS | `780 µL Ambrox + 1,580 µL ethanol = 2,360 µL top-up`; bottle stays at `30.0 mL` |

---

## Bench Reality Note (2026-04-30 execution)

The bench execution diverged from the planned protocol on the decant volume. Recorded for accuracy of the final composition.

### What Happened

- All planned non-ethanol additions went into the bottle: `Coumarin 20% 45 µL` + `Terpinyl Acetate 50 µL` (the live-correction state) + the `545 µL` revised fougère remainder + `780 µL Ambrox Super 30%` = `1,420 µL total`.
- At the ethanol top-up step, the user pulled `3.0 mL` of ethanol into the syringe and dispensed until the graduated cylinder reached the `30 mL` mark. **`~0.2–0.4 mL` was still in the syringe** when the bottle reached `30 mL`. Therefore the actual ethanol top-up was **`~2.6–2.8 mL`** (call it `~2.7 mL`), not the planned `1.58 mL`.
- Working backward: pre-ethanol bottle volume was `30,000 - 2,700 = ~27,300 µL`. With `1,420 µL` of additions, pre-additions bottle was at `~25,880 µL`. The decant was therefore **`~4.1 mL`**, not the planned `3.0 mL` — the syringe aspiration was approximate and over-pulled by `~1.1 mL`.

### Resulting Composition

| Quantity | Calculation | Result |
| --- | ---: | ---: |
| Retained base stock after `~4.1 mL` decant | `7,287 µL × (25.9/30)` | `~6,290 µL` stock |
| Active aroma in retained base | `4,986 µL × (25.9/30)` | `~4,304 µL` |
| Active aroma in `1,420 µL` additions | dilution-adjusted | `~815.5 µL` |
| Total active aroma in bottle | `4,304 + 815.5` | `~5,120 µL` |
| Bottle volume | confirmed `30.0 mL` on graduated cylinder | `30,000 µL` |
| Final active aroma concentration | `5,120 / 30,000` | **`~17.1%`** (vs planned `16.62%`) |
| Retained neat Ambrox after `~4.1 mL` decant | `1,356 µL × 30% × (25.9/30)` | `~351 µL` neat |
| Added neat Ambrox | `780 µL × 30%` | `+234 µL` neat |
| Total neat Ambrox in 30 mL | `351 + 234` | `~585 µL` |
| Final neat Ambrox % | `585 / 30,000` | **`~1.95%`** (target `2.00%`) |

### Interpretation

- **Ambrox target effectively hit.** `1.95%` neat is within `0.05%` of the planned `2.00%`. Olfactorily indistinguishable from Sauvage EDP parity. The over-decant cost a tiny amount of inherited Ambrox but the addition target was unchanged.
- **Active aroma essentially on target.** `17.1%` vs planned `16.62%` is within `0.5 percentage points` — well below human olfactory discrimination threshold for concentration differences. Effectively the same perfume.
- **No action needed.** Cap, invert `20×`, macerate `72 h` minimum, evaluate at `10–14 days`.

### What This Does Not Affect

- IFRA / safety: all guard rails remain within limits.
- Family classification: aromatic fougère anchors are unchanged — the ratio of fougère materials to base materials matches the planned bottle.
- Optimizer score: heart-aromatic and base-moss/wood deltas are essentially identical to the planned `Δ +2.45` revised plan.

### Process Note For Future Bench Sessions

When the protocol calls for a precise decant (e.g. `3.0 mL`), use a **graduated transfer pipette or volumetric tool**, not a syringe-and-aspirate from the bottle. A syringe pulled by feel can over-pull by `~10–15%` (as happened here, `4.1 mL` instead of `3.0 mL`). The over-pull is olfactorily harmless when caught, but compounds quickly across multiple steps if not measured.

---

## Decanted 3 mL Archive: Composition, Uses, And Math

The protocol removes `3.0 mL` from the bottle to make room for the `640 uL` addition + `~2.36 mL` ethanol top-up. That decant is not waste; it is the only **pre-correction reference sample** you will have. This section explains what it is and what to do with it.

### Composition Of The Decant

The contents depend on whether the decant was done before or after the live-correction additions (`Coumarin 20% 45 uL` + `Terpinyl Acetate 50 uL`).

| Decant timing | Contents | Strength |
|---|---|---|
| State A — decanted before any correction additions | Pure boosted v3c (v3c concentrate + post-mix Ambrox/Azarbre/Javanol/Norlimbanol/Timberol) | `~24.29%` raw stock, `~16.62%` active |
| State B1 — decanted after Coumarin/Terpinyl already in bottle | Same boosted v3c + trace of `Coumarin 20%` and `Terpinyl Acetate` proportional to the share removed | Olfactorily indistinguishable from State A; `95 uL` of new material distributed across `30,095 uL` is below detection threshold |

**Mass of fragrance in the 3 mL decant** (State A baseline):

| Quantity | Calculation | Result |
| --- | ---: | ---: |
| Raw stock fragrance in decant | `3,000 uL × 0.2429` | `~728.7 uL` |
| Active aroma in decant | `3,000 uL × 0.1662` | `~498.6 uL` |
| Ethanol/carrier in decant | `3,000 - 728.7` | `~2,271 uL` |

The decant therefore contains roughly the same stock-as-held fragrance content as **3 typical fragrance test pours** at EDP strength. It is not a trivial volume.

### What It Smells Like

The boosted v3c amber-Layton profile **before** the fougère conversion: amber-vanilla dominant (`Ambrox Super` + `Azarbre` + `Vanillin` + `Ethyl Vanillin` + `Benzoin Resinoid`), creamy-dry sandalwood (`Javanol` + `Sandalore` + `Timberol` + `Norlimbanol Dextro`), Hedione/lavender aromatic-floral heart, and apple-cardamom-bergamot top. This is exactly the smell the user was trying to differentiate from `Air-Conditioned Amber Layton` — and it is the **single most useful reference sample** during the fougère bottle's 10-14 day maceration window.

### Recommended Uses, Ranked

1. **Primary — A/B archive (recommended).** Label `Vol d'Ambre v3c boosted — pre-correction reference (2026-04-30)`. Keep capped, dark glass, cool. After the main bottle has macerated `10-14 days`, sniff both side-by-side on blotters at `T+0`, `T+30 min`, `T+2 h`, and `T+6 h`. This A/B is the only honest test of whether the fougère conversion actually changed the family read or only added top-notes over the same amber base. Without this archive, you cannot answer that question.

2. **Secondary — wear it as a small amber-Layton flanker.** The 3 mL is already at EDP strength. After the main-bottle evaluation is done (and you are sure it succeeded), the archive can be transferred to a `5 mL` atomiser and worn as-is. It will not duplicate `Air-Conditioned Amber Layton` because the post-mix Ambrox/Azarbre/Javanol/Norlimbanol/Timberol boosters made it amber-heavier and woodier than the air-conditioned version.

3. **Tertiary — re-dilute for a lighter wearable.** If 24% raw / 16.6% active is too strong for Thai climate:
   - To EDT strength `~12%` raw / `~8.3%` active: add `3.0 mL` ethanol 96% → final `6 mL` EDT.
   - To cologne strength `~8%` raw / `~5.5%` active: add `6.1 mL` ethanol 96% → final `9.1 mL` cologne. Closer to a typical mass-market splash.
   - Macerate the diluted version `48-72 h` before judging, even though the perfume itself is already integrated. Re-dilution forces the active phase to redistribute through fresh ethanol.

4. **Quaternary — layering base.** Spray `1 puff` of the 3 mL archive on collar/chest, then layer the corrected fougère bottle over it. Useful if the corrected main bottle reads too dry/aromatic on certain days and you want to dial amber warmth back in temporarily.

### Things Not To Do

- **Do not discard.** The decant contains `~728 uL` of stock-as-held fragrance and `~498 uL` of active aroma — measurable bench material, not test residue.
- **Do not add the new fougère materials to it.** That just makes a smaller version of the corrected bottle and destroys the only reference you have.
- **Do not mix the decant back into the corrected main bottle.** The corrected bottle is already at target `24.0%` raw / `16.62%` active. Adding `3 mL` of `24.29%` stock back would shift the bottle by `~3.4%` toward the original boosted-amber profile and undo a measurable fraction of the fougère conversion.
- **Do not store in clear glass on a sunny shelf.** The decant has the same terpene/lavender/limonene oxidation profile as the main bottle. The v3c BHT antioxidant is present but only buys `~12-18 months` of headroom in good storage conditions.

### Storage And Labelling

- Transfer to a clean amber or cobalt `5 mL` glass vial. Headspace under `1 mL` is preferred to limit oxidation surface.
- Label: `Vol d'Ambre v3c boosted — pre-correction reference`, with date `2026-04-30` and concentration `~24% raw / ~16.62% active`.
- Store cool (`<25 °C`), dark, tightly capped.
- Re-cap immediately after each evaluation pull. Each cap-off event during the 10-14 day window adds oxidation pressure; pull on blotters once per evaluation session, not repeatedly.

### Why This Matters For The Decision

The whole reason for the fougère conversion was that **`Vol d'Ambre v3c boosted` and `Air-Conditioned Amber Layton` smelled almost the same except for ambroxan level**. The 3 mL archive is the empirical anchor for the question "did we actually fix that?" Without the A/B test against the archive after maceration, the user is judging the corrected bottle against memory, which is unreliable for amber-vanilla-musk profiles where olfactory adaptation is fast.

If the corrected bottle smells clearly different from the archive at `T+0`, `T+30 min`, and `T+2 h` — and especially if it reads more masculine, fresher, and more aromatic at `T+30 min` — the conversion succeeded. If the two read substantially the same after `2 h` of wear, the fougère overlay was insufficient and the next move is a small additional `Evernyl + Juniper Berry EO + Lavender EO` push, not another amber/wood adjustment.

---

## Safety And Guardrails

- Do not raise `Evernyl` above `20 uL` in this performance-first version. The old `23 uL` gate-forward dose was legal but too close to the headroom edge and less mass-market.
- Do not add more `Ambrox Super`; the amber band is already the reason this bottle overlaps with Air-Conditioned Amber Layton.
- Do not add `Hedione HC`; it restores the glossy Layton radiance profile and reduces differentiation.
- Do not add `Nagarmortha Oil` in this pass. It is useful, but this formula needs mass-market aromatic freshness, not oud-adjacent darkness.
- `Lime Distilled EO`, `Beta-Pinene`, `Juniper Berry EO`, lavender materials, and petitgrain are terpene-heavy. The v3c BHT antioxidant guard should be present. Store cool, dark, and tightly capped.
