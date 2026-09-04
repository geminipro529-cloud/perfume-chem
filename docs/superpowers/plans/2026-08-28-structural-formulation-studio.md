# Structural Formulation Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Codex subagents are prohibited by project policy, so execution is inline and locally verified.

**Goal:** Build a reusable theory-only structural formulation studio and its first original sporty aromatic woody-amber application, Silver Traverse.

**Architecture:** Keep permanent studio governance, reusable method, formula, and blind-validation responsibilities in separate Markdown artifacts under one formula subdirectory. The formula has an inventory-independent TARGET / IDEAL representation and a distinct 6,000 uL CURRENT-INVENTORY representation; repository pipeline output is diagnostic and appended only after local verification.

**Tech Stack:** Markdown formula artifacts; live `inventory.txt`; repository ppm/ODT/OAV/composite-natural pipeline; PowerShell; Python CLI already present in the repository.

**Spec:** `docs/superpowers/specs/2026-08-28-structural-formulation-studio-design.md`

## Global Constraints

- Work is **THEORY ONLY / NOT TESTED / NO COMPOUNDING AUTHORIZED**.
- Do not procure, physically prepare a working stock, or compound a test article.
- Re-read the authoritative batch-start set before every new formula batch.
- Current user physical overrides outrank repository history and modeled defaults.
- TARGET / IDEAL and CURRENT-INVENTORY must remain separate.
- Normalize concentrate ppm to 1,000,000 and use ODT/OAV only as diagnostics.
- Naturals use composite OAV when covered; absent or conflicting coverage is HOLD.
- Every direct formula or module-stock aliquot is at least 10 uL.
- Use zero or one functionally exact musk by default; V1.3 uses only Habanolide, while V1.4 uses only Romandolide. Alternatives remain separate one-musk or no-musk arms.
- Every material must own a nonredundant identity function and an omission control.
- Preserve NOT TESTED and HOLD ceilings for every unobserved sensory, safety, stability, and data-quality outcome.
- Do not use `$delegate`, OpenRouter, DeepLuna Fast, provider fallback, or Codex subagents.
- Do not touch the pre-existing untracked `.codex/` directory.
- Do not commit or publish; the final diff is the user-reviewable handoff unit.

---

### Task 1: Studio Index and Reusable Method

**Files:**
- Create: `formulas/structural_formulation_studio/README.md`
- Create: `formulas/structural_formulation_studio/METHOD.md`

**Interfaces:**
- Consumes: authority and design contract in the spec.
- Produces: batch-start checklist, evidence taxonomy, architecture worksheet, calculation contract, material admission gate, omission discipline, blind-validation template, and completion checklist used by every formula packet.

- [x] **Step 1: Create the studio directory and index**

Create `formulas/structural_formulation_studio/` and write `README.md` with:

- theory-only authority boundary;
- exact seven-item batch-start reading sequence;
- latest physical overrides;
- links to `METHOD.md`, the Silver Traverse formula, and its blind protocol;
- definition of TARGET / IDEAL versus CURRENT-INVENTORY;
- no-procurement/no-compounding warning;
- formula-batch ledger fields: date, source hashes or commit, inventory overrides, formula status, diagnostics status, physical evidence status.

- [x] **Step 2: Write the identity-first architecture worksheet**

Write `METHOD.md` sections in this order:

1. named identity contract;
2. one-subject/multiple-state anatomy;
3. front/near/middle/rear/echo spatial planes;
4. opening/heart/base recurrence chain;
5. opposed texture and pressure/release map;
6. identity-bearing base test;
7. comfort/tension/release hedonic hypothesis;
8. takeover exclusions;
9. formula representation and gap map.

Each section must contain a short fillable template and a pass/fail question tied to the perfume name.

- [x] **Step 3: Write material admission and calculation rules**

Include:

- live-inventory and stock-basis checks;
- the 10 uL direct aliquot rule;
- conventional stock active-uL and ppm formulas;
- explicit nominal-only treatment for w/v or density-unknown stocks;
- ODT duplicate, alias, activity coefficient, and physics coverage checks;
- natural-mixture composite-OAV rule;
- one-musk functional-exactness gate;
- material row schema: stock, raw uL, nominal active uL, ppm, plane, time, identity function, predicted omission consequence, omission test;
- HOLD and NOT TESTED ceilings.

- [x] **Step 4: Write the disciplined finishing and validation template**

Specify this sequence:

1. protect the minimum recognizable identity nucleus;
2. run a constant-total 2x2 module test;
3. inspect takeover failures before preference;
4. compare the surviving high-count formula with a constant-total compressed version;
5. run isolated omission arms for remaining secondary rows;
6. retain only rows with observed nonredundant value;
7. assess at 0, 5, 30, 120 minutes, 6 hours, and 24 hours on blotter and skin separately.

- [x] **Step 5: Verify the reusable artifacts**

Run:

```powershell
rg -n "AGENTS.md|inventory.txt|copilot-instructions|fragrance_families_reference|DHP2025|10 uL|composite OAV|one musk|NOT TESTED|HOLD|TARGET / IDEAL|CURRENT-INVENTORY" formulas/structural_formulation_studio/README.md formulas/structural_formulation_studio/METHOD.md
```

Expected: every authority, stock, calculation, and evidence constraint is present; no physical-action language is framed as authorization.

---

### Task 2: Silver Traverse V1.1 Formula Packet

**Files:**

- Create/modify: formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_30mL_20pct_THEORY.md
- Modify: formulas/structural_formulation_studio/README.md
- Modify: docs/superpowers/specs/2026-08-28-structural-formulation-studio-design.md

**Interfaces:**

- Consumes: the studio method, the 2026-08-28 live inventory sync, official Luna Rossa/Explorer axes, and the DHP structural grammar.
- Produces: one parseable 6,000 uL current formula, a separate 1,000,000 ppm ideal, a gap map, row ownership/omission controls, and an evidence ceiling.

- [x] **Step 1: Protect the Pink Pepper main note**

Set Pink Pepper EO at 25,000 active ppm in TARGET / IDEAL. Because it is absent from live inventory, keep Black Pepper EO under its own name in CURRENT and label the Bergamot/Geraniol/lavender/Cashmeran/patchouli/vetiver chord as a non-equivalent proxy. Add hot/dry/culinary pepper as a takeover exclusion.

- [x] **Step 2: Deepen citrus by dimension, not loudness**

Add Bergamot FCF 100 uL and reduce Dihydromyrcenol 300 -> 160 uL. The causal job is dimensional peel and a pepper-to-lavender bridge, not higher top-note intensity. Do not add Petitgrain in this batch.

- [x] **Step 3: Deepen the base with one far-rear shadow**

Add Labdanum Resinoid 10% in DPG at 100 uL and reduce Benzyl Benzoate 200 -> 100 uL. The causal job is low-vapor far-rear depth. Do not add another musk, Vertofix, Norlimbanol, Kephalis, or another dry-wood booster in this batch.

- [x] **Step 4: Preserve constant total and architecture**

Use this net-zero V1 -> V1.1 change budget:

| Change | Raw uL delta |
|---|---:|
| Bergamot FCF | +100 |
| Black Pepper EO | +80 |
| Labdanum Resinoid 10% | +100 |
| Dihydromyrcenol | -140 |
| Lavender EO (BONTAUX SAS) | -20 |
| Hedione | -20 |
| Benzyl Benzoate | -100 |
| **NET** | **0** |

The resulting CURRENT formula has 34 rows, totals 6,000 uL, has a 20 uL minimum direct aliquot, and uses only Romandolide as musk. The TARGET / IDEAL table has 34 rows totaling 1,000,000 active ppm.

- [x] **Step 5: Synchronize current physical authority**

Update only this worktree's inventory and derived stock metadata for the user-authoritative 2026-08-28 delta. Preserve Cedarwood oil Virginia and Lemon FCF oil Sicilian as owned neat records. Do not silently rebase existing formulas; stock conflicts become next-batch work or HOLD.

- [x] **Step 6: Write ownership, gap, and safety ledgers**

Record nominal active ppm, planes, time, nonredundant function, predicted omission, test owner, Black Pepper composite-OAV HOLD, Ambrox basis HOLD, Pink Pepper proxy HOLD, and full NOT TESTED ceilings.

---

### Task 3: Blinded Validation and Local Diagnostics

**Files:**

- Create/modify: formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_BLIND_VALIDATION.md
- Modify: formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_30mL_20pct_THEORY.md
- Generate, ignored: output/structural_formulation_studio/silver_traverse_v1_pipeline.json
- Generate, ignored: output/structural_formulation_studio/silver_traverse_v1_analysis.txt

- [x] **Step 1: Define protected pepper-proxy controls**

Define P80, P40, and P00 Black Pepper arms at constant 6,000 uL using Benzyl Benzoate compensation. State that this can test the CURRENT proxy's contribution but cannot establish Pink Pepper material equivalence.

- [x] **Step 2: Define the surface/interior 2x2**

Keep the 5,840 uL common core and four 160 uL module masters. The V1.1 common core includes Bergamot, Black Pepper, and Labdanum while preserving a 10 uL minimum module-master aliquot.

- [x] **Step 3: Define citrus-depth/base-depth controls**

Define C1B1, C1B0, C0B1, and C0B0 at constant total. Separate dimensional peel from citrus loudness and far-rear shadow from raw base strength.

- [x] **Step 4: Define compression, add-back, and musk controls**

On the full branch, remove Terpinyl Acetate, Geraniol 10%, Dihydrojasmone, and Vetival; move 150 uL to Benzyl Benzoate (100 -> 250 uL), producing a 30-material compressed arm. Use isolated add-backs and a Romandolide-versus-compensator control.

- [x] **Step 5: Run focused formula and inventory diagnostics**

Verify:

- inventory parser counts and all user-authoritative stock fractions;
- YAML and generated metadata consistency for updated rows;
- CURRENT raw total 6,000 uL, TARGET total 1,000,000 ppm, 34 rows, minimum 20 uL;
- common core 5,840 uL and each module 160 uL;
- only one musk;
- no unavailable row in the dosing table.

Run the existing formula release gate with brief aromatic_fougere. No full release verifier is needed because no release claim is made.

- [x] **Step 6: Produce and append required full analysis**

Run the existing formatter against the new JSON, save its exact output, and append it verbatim under a Pipeline Analysis section. Prefix it with the modeled-diagnostic / NOT TESTED claim ceiling.

- [x] **Step 7: Review final diff and evidence labels**

Run git diff --check, focused tests, and a scoped diff. Preserve pre-existing unrelated changes and the untracked .codex directory. Confirm no procurement, stock preparation, physical compounding, skin application, commit, or publication action occurred.

---

### Task 4: Silver Traverse V1.2 Pink-Pepper Leadership Successor

**Files:**

- Create: formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_2_30mL_20pct_THEORY.md
- Create: formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_2_BLIND_VALIDATION.md
- Modify: formulas/structural_formulation_studio/METHOD.md
- Modify: formulas/structural_formulation_studio/README.md
- Modify: docs/superpowers/specs/2026-08-28-structural-formulation-studio-design.md
- Generate, ignored: output/structural_formulation_studio/silver_traverse_v1_2_pipeline.json
- Generate, ignored: output/structural_formulation_studio/silver_traverse_v1_2_analysis.txt

- [x] **Step 1: Re-read the full batch authorities and preserve V1.1**

Re-open AGENTS, live inventory, Copilot instructions, the aromatic-fougere family section, authoritative DHP2025 learning protocol, V1.1 formula/blind plan, and relevant DHP/Opus/sporty comparison formulas. Record hashes. Preserve V1.1 unchanged as historical computational evidence.

- [x] **Step 2: Add a reusable lead-note ownership gate**

Require the named lead to own the first recognizable object, a transformed heart state, and a late identity echo. Require explicit competitor budgets, no/half-lead controls, time-specific lead ranking, and an exact-material comparison for non-equivalent reconstructions.

- [x] **Step 3: Rebase TARGET / IDEAL around Pink Pepper**

Raise exact Pink Pepper from 25,000 to 80,000 active ppm. Reduce lavender 65,000 -> 45,000, Dihydromyrcenol 35,000 -> 20,000, Bergamot 30,000 -> 18,000, Cedrat 12,000 -> 8,000, and Linalyl Acetate 50,000 -> 44,000; raise Geraniol 2,000 -> 4,000. Keep 34 target rows and exactly 1,000,000 ppm.

- [x] **Step 4: Build the non-equivalent CURRENT reconstruction**

Separate Black Pepper spicy pressure, Rose Oxide metallic-rosy effervescence, Damascone Beta berry-woody echo, and Geraniol seam functions. Preserve every V1.1 row/function, rebase 15 doses, add only two rows, total exactly 6,000 uL across 36 rows, keep a 10 uL minimum, and retain Romandolide as the only musk.

- [x] **Step 5: Control citrus and base depth**

Reduce citrus/fresh competition instead of adding more citrus. Add no new base material or musk; reallocate 110 uL among existing ambrox/wood/pepper-echo owners. Define citrus x base-echo constant-total controls and a zero/half/full citrus refinement.

- [x] **Step 6: Define blinded identity and compression tests**

Define spicy-pressure x rosy-facet 2x2, half-pepper rescue, isolated Damascone omission, contingent exact-Pink-Pepper 480 uL comparison, surface x interior 2x2, 36-versus-31-row compression, isolated add-backs, and one-musk necessity.

- [x] **Step 7: Complete fresh final verification**

Verify TARGET/CURRENT arithmetic, blind-arm totals, inventory/metadata authority, exact formatter embedding, focused tests, hashes, and git diff --check. Rerun the final local pipeline after the last formula-byte change. Keep all physical and release claims at NOT TESTED/HOLD.

---

### Task 5: Silver Traverse V1.3 Hedonic Rebase

**Files:**

- Create: `formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_3_30mL_20pct_THEORY.md`
- Create: `formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_3_BLIND_VALIDATION.md`
- Modify: `formulas/structural_formulation_studio/METHOD.md`
- Modify: `formulas/structural_formulation_studio/README.md`
- Modify: `docs/superpowers/specs/2026-08-28-structural-formulation-studio-design.md`
- Generate, ignored: `output/structural_formulation_studio/silver_traverse_v1_3_pipeline.json`
- Generate, ignored: `output/structural_formulation_studio/silver_traverse_v1_3_analysis.txt`

- [x] **Step 1: Refresh authorities and conserve V1.2 lineage**

Re-read the complete batch-start set, V1.1/V1.2 formulas and blind plans, current DHP protocol, and relevant DHP/Opus/sporty formulas. Preserve V1.2 unchanged. Keep 34 TARGET rows, 36 CURRENT rows, five planes, two states, all transition/recurrence functions, and an individual disposition for every predecessor row.

- [x] **Step 2: Add the reusable hedonic-successor gate**

Require a subtraction-first rebase, fixed protected lead, explicit glare/rigidity/fatigue budgets, release/cushion/negative-space reallocation, predecessor confirmation, and one-musk-per-arm tournament. Keep identity, liking, comfort, re-smell desire, harshness, fatigue, and takeovers separate.

- [x] **Step 3: Build the net-zero V1.3 rebase**

Keep exact Pink Pepper at 80,000 TARGET ppm. Define `G` as 230 raw uL of reduced citrus/fresh/aromatic/muguet glare moved to Benzyl Benzoate negative space. Define `S` as 110 raw uL removed from abstract/rigid rear pressure and reallocated to Hedione, Helional, Dihydrojasmone, and Hexyl Salicylate. Retain rounded Clearwood/Azarbre rear body at V1.2 levels. Add no material row and no second musk.

- [x] **Step 4: Select one controlled comfort-musk hypothesis**

Use Habanolide 250 uL as the sole V1.3 musk candidate. Preserve Romandolide 250, Ethylene Brassylate 250, and no musk as equal-volume blind alternatives. Do not combine winners or infer that inventory ownership supports a musk chord.

- [x] **Step 5: Define the controlled validation ladder**

Retain the protected reconstruction factorial and exact-Pink-Pepper contingent comparison. Add `G x S`, the single-musk tournament, fresh-block V1.2 confirmation, full/half/zero citrus, isolated Hexyl Salicylate and Labdanum omissions, 36-versus-31 compression, and isolated add-backs. Keep every arm at 6,000 uL and every direct aliquot at least 10 uL.

- [x] **Step 6: Complete final local diagnostics and evidence handoff**

Verify formula/arm arithmetic, inventory and stock bases, one-musk count, ODT/physics/composite-natural holds, formula parsing, focused tests, required formatter embedding, hashes, and `git diff --check`. Run no provider, procurement, physical compounding, commit, merge, or publication action. Report the final formula as theory only and every sensory result as NOT TESTED.

---

### Task 6: Silver Traverse V1.4 Aventus / Absolu Hedonic-Sport Re-Axis

**Files:**

- Create: `formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_4_AVENTUS_ABSOLU_HEDONIC_SPORT_30mL_20pct_THEORY.md`
- Create: `formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_4_AVENTUS_ABSOLU_HEDONIC_SPORT_BLIND_VALIDATION.md`
- Modify: `formulas/structural_formulation_studio/METHOD.md`
- Modify: `formulas/structural_formulation_studio/README.md`
- Modify: `docs/superpowers/specs/2026-08-28-structural-formulation-studio-design.md`
- Generate, ignored: `output/structural_formulation_studio/silver_traverse_v1_4_pipeline.json`
- Generate, ignored: `output/structural_formulation_studio/silver_traverse_v1_4_analysis.txt`

- [x] **Step 1: Finalize and freeze V1.3**

Correct the Cyclamen narrative mismatch, verify 34 TARGET rows / 1,000,000 ppm, 36 CURRENT rows / 6,000 uL, 10 uL minimum, one Habanolide row, focused parser tests, fresh pipeline output, and exact formatter embedding. Record the finalized predecessor hashes.

- [x] **Step 2: Replace the reference interval without cloning**

Retire Explorer/Explorer Extreme for V1.4. Use official Prada Luna Rossa, Creed Aventus, and Creed Absolu Aventus descriptions to extract only athletic sailcloth, fruit-lit fresh-to-dry propulsion, and sharper ginger/grapefruit-to-warm-root contrast. Exclude pineapple, apple, cassis, birch, oakmoss/chypre, cinnamon/cardamom signature, sweet labdanum takeover, and recognizable Aventus resemblance.

- [x] **Step 3: Add the reusable reference-axis gate**

Version the method to SFSM-1.3. Require a frozen predecessor, protected lead, abstract structural translation, donor-signature exclusions, net-zero module localization, one-musk controls, fresh predecessor confirmation, and full-count-versus-compressed testing.

- [x] **Step 4: Build the V1.4 target and current formula**

Keep Pink Pepper at 80,000 TARGET ppm. Build a 36-row TARGET totaling 1,000,000 ppm and a 37-row CURRENT totaling 6,000 uL. Define `F` as +20 Methyl Pamplemousse stock, +30 Ginger, +20 Hedione, -70 Benzyl Benzoate; `P` as -250 Habanolide, +300 Romandolide, -30 Iso E, -20 Ambrox stock; and `D` as +20 each Azarbre/vetiver/patchouli, -60 Benzyl Benzoate. Keep Romandolide as the sole musk and every direct aliquot at least 10 uL.

- [x] **Step 5: Reject the non-earning preliminary row**

Screen Paradisamide at nominal 10% / 60 uL. Because the stock basis and ODT conflict and modeled OAV is 0.0029, reject it from default CURRENT, preserve the desired long-lived tart-fruit function in TARGET, and quarantine Paradisamide to a separately gated contingent arm.

- [x] **Step 6: Define blinded localization and compression**

Inherit the V1.3 Pink-Pepper identity veto. Define `F x D`, projection transfer, rear-pressure relief, equal-volume one-musk tournament, Methyl-Pamplemousse x Ginger, zero-modifier/Hedione controls, contingent Paradisamide quarantine, rear-depth leave-one-out, fresh V1.3 confirmation, 37-versus-31 compression, and isolated add-backs. Keep every arm at 6,000 uL.

- [x] **Step 7: Complete final local verification and handoff**

Verify final parser arithmetic, TARGET sum, one-musk count, direct floor, arm arithmetic, exact formatter embedding, focused tests, hashes, scoped diff, and `git diff --check`. Report the complete analysis and every readiness limit without making sensory, safety, stability, release, procurement, or compounding claims.

---

### Task 7: Immortelle Ambre Fossile V1 Queue Completion

**Files:**

- Modify: `formulas/structural_formulation_studio/IMMORTELLE_AMBRE_FOSSILE_V1_30mL_24pct_THEORY.md`
- Modify: `formulas/structural_formulation_studio/IMMORTELLE_AMBRE_FOSSILE_V1_BLIND_VALIDATION.md`
- Modify: `formulas/structural_formulation_studio/README.md`
- Generate, ignored: `output/structural_formulation_studio/immortelle_ambre_fossile_v1_pipeline.json`
- Generate, ignored: `output/structural_formulation_studio/immortelle_ambre_fossile_v1_analysis.txt`

- [x] **Step 1: Reconcile the studio-local queue and preserve ownership boundaries**

Confirm that Immortelle Ambre Fossile V1 is the sole unfinished in-scope packet. Do not duplicate or mutate formula work actively owned by sibling tasks. Preserve all pre-existing user changes and make no commit, merge, push, procurement, stock preparation, or compounding action.

- [x] **Step 2: Refresh authorities and relevant comparison formulas**

Re-read the complete batch-start set, current inventory overrides, amber/resinous/tobacco/gourmand family sections, authoritative DHP2025 protocol, studio method, Immortelle packet, blind plan, and the cited legacy Immortelle/DHP/Opus comparison formulas. Record the current inventory SHA-256 and retain the exact external protocol provenance.

- [x] **Step 3: Close formula geometry and parser truth**

Correct the summary-row label that the repository parser mistook for a 43rd material. Verify exactly 42 parsed materials, 7,200 uL CURRENT total, 1,000,000 TARGET ppm, a 20 uL minimum direct aliquot, one Ethylene Brassylate row, and no ingredient deletion or dose change.

- [x] **Step 4: Run deterministic local diagnostics**

Run the existing release pipeline with 7,200 uL expected concentrate, 30 mL context, 305 K, generic brief, deterministic hash seed, and audit writing disabled. Save the JSON and required formatter output; present the full analysis in chat before interpretation and append it to the formula artifact.

- [x] **Step 5: Preserve computational and physical claim ceilings**

Record the 102 PASS / 26 WARN / 1 FAIL result, confidence-minimum failure, ODT authority limits, exact composite-natural coverage and HOLD set, w/w/w/v stock holds, software-gate limitations, modeled IFRA warnings, and the fact that immortelle audibility does not establish leadership. Add the same pre-execution holds to the blind plan. Do not rebase the named formula merely to improve generic numerical gates.

- [x] **Step 6: Close the studio queue**

Index the Immortelle formula and protocol, add the missing V1.3.1 exact-Pink-Pepper links, and record the studio-local queue as empty. State that a new perfume requires a new explicit concept or revival.

- [x] **Step 7: Complete fresh final verification**

Verify exact formatter embedding, formula and blind-plan arithmetic, inventory/data-spine resolution, generated receipt hashes, focused parser tests, scoped artifact diff, and `git diff --check`. Keep completion limited to a theory packet with every sensory, safety, stability, release, procurement, and physical-compounding result at NOT TESTED/HOLD.
