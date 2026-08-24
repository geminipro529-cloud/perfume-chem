# Meaningful Complexity Audit v2

## Purpose

This contract governs any perfume or standalone accord described as complex, high-complexity, deeply layered, orchestral, or meaningfully layered.

It prevents three recurring failures:

1. A short compact module being mislabeled as a high-complexity accord.
2. A long formula reaching its row target through duplicate stocks, carriers, invisible traces, or redundant materials.
3. A formula receiving a computational pass even though its added rows do not materially change identity, texture, phase behavior, diffusion, persistence, contrast, or failure-mode control.

This document is an independent chemistry and quality-control lane. It does not claim that OpenCode, DeepSeek, GLM, or another external model has run.

---

## 1. Formula classes

### 1.1 Compact functional module

A compact module may contain fewer than 50 odor materials.

It must be labeled:

`COMPACT FUNCTIONAL MODULE`

It must never be called a high-complexity accord.

### 1.2 High-complexity standalone accord

Minimum after deduplication and pruning:

`50 distinct odor materials`

Preferred range:

`55 to 70 distinct odor materials`

The accord must remain coherent and recognizable when tested alone and at its intended use level.

### 1.3 High-complexity full perfume

Minimum after deduplication and pruning:

`65 distinct odor materials`

Preferred range:

`70 to 90 distinct odor materials`

More than 90 is allowed only when the audit demonstrates that additional rows create a distinct function or temporal effect.

---

## 2. Counting rules

A row counts toward meaningful complexity only when all of the following are true:

- It is an odor-active material or named product-basis perfume material.
- It has a unique canonical identity.
- It has a documented perceptual or structural function.
- It is not a duplicate strength or solvent form of another counted row.
- It is not removed by the redundancy or ablation review.
- Its stock and active fraction are executable from the canonical inventory.
- It belongs to a defined module, phase, bridge, or modifier system.
- Its role is supported by evidence or explicitly labeled as a physical-confirmation hypothesis.

The following do not increase the count:

- ethanol;
- DPG;
- DEP;
- TEC;
- IPM;
- water;
- carrier balance;
- the same molecule at neat and diluted strengths;
- aliases;
- duplicate supplier entries;
- hidden ingredients imagined inside a proprietary base;
- a formula subtotal;
- a premix name when the premix components are already counted;
- a one-part trace with no function;
- a material retained only to meet the row minimum.

A proprietary base, tincture, or product-basis material counts as one material. Its undisclosed internal composition may not be expanded.

---

## 3. Required architecture for a 50-plus-row accord

The following counts are functional targets, not independent additive totals. A material may serve more than one function, but it may only count once as a distinct material.

| System | Recommended distinct materials | Requirement |
|---|---:|---|
| Primary recognizer | 6 to 14 | The named odor remains identifiable |
| Secondary recognizer | 4 to 10 | Adds species, color, or style specificity |
| Body and volume | 8 to 16 | Prevents a thin note sketch |
| Texture | 8 to 16 | Creates wax, grain, cream, root, leaf, suede, powder, mineral air, smoke, or skin |
| Bridges | 6 to 12 | Connects otherwise separate modules |
| Opening | 5 to 12 | Establishes lift, contrast, and entry |
| Heart persistence | 8 to 16 | Maintains identity after the opening |
| Drydown structure | 10 to 20 | Provides a distinct late identity |
| Diffusion controls | 5 to 12 | Shapes projection without genericizing |
| Microtexture | Maximum 20% of final counted rows | Must be physically confirmed |

Minimum functional-system coverage:

- at least 5 distinct sensory systems;
- at least 3 temporal phases;
- at least 2 bridge mechanisms;
- at least 1 explicit anti-defect system;
- at least 1 late drydown identity mechanism.

---

## 4. Row-level evidence contract

Every formula row must answer the following questions.

### Identity

- What is the canonical material?
- What exact stock is used?
- What is its active fraction?
- Is it neat, diluted, a tincture, a suspension, or product basis?
- Does the canonical inventory permit its use?

### Function

- What does the material smell like at this dosage?
- What is its primary perceptual function?
- What is its structural function?
- Which phase does it affect?
- Which system does it belong to?
- Which material or system does it bridge?

### Interaction

- Which other materials or groups does it enhance?
- Which materials or groups can suppress it?
- What can it mask?
- What can it cause to become generic?
- Does it change dryness, sweetness, warmth, coolness, diffusion, or texture?
- Is the effect additive, synergistic, suppressive, contrasting, or uncertain?

### Selection

- Why was this material chosen?
- Which alternatives were considered?
- Why is it not redundant with an existing row?
- Why is this dose plausible?
- What defect appears if it is overdosed?
- What is lost if it is underdosed?

### Evidence

- What evidence class supports the role?
- Which sources support it?
- What is the confidence?
- What uncertainty remains?
- Does physical smelling need to confirm the row?

### Verification

- What happens when the material is removed?
- What happens at minus 20 percent?
- What happens at plus 20 percent?
- Is it identity-critical, structural, textural, or microtexture?
- Does it survive the final audit?

---

## 5. Allowed final row classifications

### IDENTITY CRITICAL

Removing the material breaks the named odor, target identity, essential contrast, or defining temporal behavior.

### STRUCTURALLY IMPORTANT

Removing the material materially changes diffusion, balance, architecture, persistence, or module integration.

### TEXTURAL SUPPORT

Removing the material preserves broad identity but measurably weakens grain, wax, cream, leaf, suede, root, mineral air, powder, skin, smoke, or another intended texture.

### MICROTEXTURE / PHYSICAL CONFIRMATION

The row has a plausible chemical and sensory purpose, but the computational model cannot establish its perceptibility in the complete mixture.

Rules:

- maximum 20 percent of final counted rows;
- must have a written hypothesis;
- must have a specific physical test;
- may not be used to pad the row count;
- must be removed if the matured physical comparison shows no benefit.

### REDUNDANT / REMOVE

The row duplicates another material, has no measurable or defensible function, fails ablation, or exists only to inflate complexity.

### TECHNICAL

Carrier, solvent, stabilizer, or process material. It does not count toward odor complexity.

---

## 6. Hard gates

### G0: Canonical lock

Required:

- formula ID;
- version;
- target class;
- inventory version;
- source manifest;
- formula hash;
- worker packet ID.

Failure state:

`HOLD`

### G1: Stock and identity

Required:

- exact canonical name;
- exact stock;
- exact solvent;
- exact active fraction where known;
- product-basis label where exact composition is unknown;
- no gap, banned, out-of-stock, or unconfirmed material.

Failure state:

`REBUILD OR STOCK HOLD`

### G2: Arithmetic

Required:

- exactly 1,000 formula parts;
- correct 30 mL, 5 mL, and 1 mL calculations;
- no unresolved sub-1 microliter direct dose in the 5 mL pilot;
- premix carrier correction included.

Failure state:

`FAIL`

### G3: Meaningful row count

Required after deduplication and pruning:

- accord: at least 50;
- perfume: at least 65.

Additional requirements:

- microtexture rows no more than 20 percent;
- technical rows excluded;
- product bases counted once;
- same material at multiple strengths counted once.

Failure state:

`REBUILD`

### G4: Functional coverage

Required:

- at least 5 sensory systems;
- at least 3 temporal phases;
- at least 6 bridge or cross-module materials;
- explicit late-drydown mechanism;
- explicit anti-defect mechanism;
- no unassigned odor row.

Failure state:

`REVISE`

### G5: Interaction coherence

Required:

- every major module has an interaction map;
- each bridge identifies both systems it connects;
- suppression and masking risks are documented;
- incompatible systems have dose or phase separation;
- no major interaction is justified only by note-pyramid language.

Failure state:

`REVISE`

### G6: Dominance control

Required unless a written target exception is approved:

- no single modeled odor contributor above 22 percent;
- no single wood above 35 percent of the wood block;
- no single musk above 45 percent of the musk block;
- no single amberwood above 35 percent of the amberwood block;
- no single carrier-heavy product basis silently dominates the stock volume.

Failure state:

`REVISE OR REBUILD`

### G7: Temporal architecture

Required:

- opening identity;
- heart identity;
- drydown identity;
- 8-hour recognizer;
- 24-hour residue hypothesis;
- at least one material or bridge supporting each transition.

Failure state:

`REVISE`

### G8: Monte Carlo robustness

Required:

- uncertainty in stock, natural potency, dilution, dose, release, matrix, threshold, and application;
- at least 10,000 simulations for ordinary release;
- at least 20,000 simulations for high-complexity canonical release;
- hard-gate pass probability at least 90 percent.

States:

- 90 percent or above: `ROBUST`
- 70 to 89.99 percent: `CONDITIONAL`
- below 70 percent: `REBUILD`

### G9: Material ablation

Required:

- remove every row one at a time;
- recalculate recognizer, balance, temporal shape, dominance, and separation;
- classify every row;
- remove all redundant rows;
- rerun all previous gates after pruning.

If pruning lowers the accord below 50 or the perfume below 65:

`REBUILD THE MISSING FUNCTIONAL LAYER`

Do not pad.

### G10: Dose perturbation

Required:

- minus 30 percent;
- minus 20 percent;
- minus 10 percent;
- plus 10 percent;
- plus 20 percent;
- plus 30 percent for major controls.

Classify:

- fragile control;
- moderate control;
- robust control;
- overdose hazard;
- underdose hazard.

### G11: Anti-collapse

Required for every sibling pair:

- material-vector comparison;
- sensory-system comparison;
- temporal comparison;
- recognizer comparison;
- drydown comparison.

Default thresholds:

- collision similarity below 0.76;
- Jensen-Shannon or equivalent structural distance at or above the declared family threshold;
- no concentration-only distinction;
- no top-note-only distinction;
- no cloned wood or musk chassis without a written lineage reason.

Failure state:

`REBUILD OR MERGE AS ONE FORMULA`

### G12: Physical chemistry

Required:

- solubility check;
- precipitation check;
- crystallization check;
- haze and suspension check;
- oxidation risk;
- resin loading;
- color risk;
- solvent compatibility;
- aging requirement;
- storage requirement.

Failure state:

`FORMULATION HOLD`

### G13: Evidence integrity

Required:

- notes are not mapped directly to molecules without evidence;
- every factual scientific claim is sourced;
- patents are precedent, not formula proof;
- public formulas are ancestry, not factory evidence;
- computed headspace is not measured headspace;
- computational OAV is not strict empirical OAV;
- product-basis active fraction is not invented.

Failure state:

`EVIDENCE HOLD`

### G14: Final quality gate

Score domains:

| Domain | Points |
|---|---:|
| Evidence integrity | 15 |
| Inventory and execution | 10 |
| Meaningful complexity | 20 |
| Recognizer architecture | 15 |
| Interaction coherence | 15 |
| Temporal architecture | 10 |
| Robustness and sensitivity | 10 |
| Physical chemistry readiness | 5 |
| Total | 100 |

Minimum score:

`92 / 100`

A score cannot override a hard-gate failure.

Allowed outcomes:

- `COMPUTATIONAL DESIGN PASS`
- `CONDITIONAL`
- `HOLD`
- `REBUILD`

---

## 7. Complexity integrity ratios

The final audit must report:

### Functional-row ratio

`counted functional odor rows / total odor rows`

Minimum:

`0.90`

### Microtexture ratio

`microtexture rows / counted odor rows`

Maximum:

`0.20`

### Evidence-supported ratio

`rows with primary, patent, official, supplier, or clearly labeled hypothesis evidence / counted odor rows`

Minimum:

`1.00`

Every row must have an evidence class, including hypothesis rows.

### Bridge ratio

`materials with a documented cross-module bridge / counted odor rows`

Recommended:

`0.10 to 0.25`

### Dominant-block concentration

The audit must show the fraction of the formula occupied by:

- the largest material;
- the largest sensory system;
- the largest wood;
- the largest musk;
- the largest amberwood;
- the largest product-basis material.

---

## 8. Interaction-aware layering requirements

For every major sensory system, create a group interaction record.

Required interaction types:

- enhancement;
- suppression;
- masking;
- rounding;
- sharpening;
- diffusion change;
- persistence change;
- texture change;
- sweetness change;
- dryness change;
- warmth or coolness;
- bridge formation;
- collision risk;
- uncertainty.

Each interaction record must include:

- source group;
- target group;
- materials involved;
- dose range;
- expected phase;
- expected effect;
- evidence;
- confidence;
- failure mode;
- physical test.

A formula cannot pass G5 when its modules are independently plausible but their cross-group effects are undocumented.

---

## 9. Worker protocol

A worker may construct or audit only one bounded formula packet at a time.

Worker output must include:

1. formula JSON;
2. row audit JSON;
3. interaction map JSON;
4. arithmetic ledger;
5. meaningful-complexity summary;
6. ablation ledger;
7. perturbation ledger;
8. blockers;
9. formula hash;
10. exact artifact paths.

Workers may not issue the overall final pass.

The integrator must independently verify artifacts rather than trusting the worker summary.

---

## 10. Stop conditions

Stop and mark `HOLD` when:

- the canonical inventory is unavailable;
- the exact stock is unresolved;
- a required product-basis identity is uncertain;
- authoritative target/version evidence is missing;
- physical chemistry makes the formula non-executable;
- a requested empirical claim has no physical data.

Stop and mark `REBUILD` when:

- the formula falls below its row threshold after pruning;
- the recognizer depends on one oversized row;
- sibling formulas collapse;
- the third bounded revision fails;
- complexity is concentrated in one generic chassis;
- more than 20 percent of rows are unproven microtexture;
- the formula reaches the row count only through padding.

---

## 11. Physical validation boundary

No computational audit can establish:

- beauty;
- bottle equivalence;
- measured headspace;
- strict empirical OAV;
- skin evolution;
- stability;
- current IFRA compliance;
- supplier-specific safety.

The final physical program must include:

- compounding;
- maturation;
- coded blotter testing;
- repeated evaluation days;
- skin testing only after safety review;
- stability and precipitation review;
- supplier documents;
- bounded revisions.

The formula remains a computational candidate until those gates are completed.
