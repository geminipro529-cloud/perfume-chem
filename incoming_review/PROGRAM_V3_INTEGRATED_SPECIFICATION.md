# Complex Perfumery Program v3 — Integrated Specification

**Artifact ID:** `PCV3-C00-F001`  
**Integrator:** `PCV3-INTEGRATOR`  
**Integration state:** `COMPLETE_WITH_HOLDS`  
**Prepared:** `2026-08-07`  
**Program approval:** `NOT ISSUED`  
**Empirical perfume release:** `NOT AUTHORIZED`  
**Inherited Phase G:** `LOCKED / NOT AUTHORIZED`

## 1. Executive disposition

Program v3 now has one integrated control specification spanning the eight specialist lanes:

1. meaningful complexity;
2. experimental and sensory data;
3. real-engine qualification planning;
4. physical interaction tranche design;
5. exact-stock material behavior;
6. floral expansion and interfaces;
7. hedonic, commercial, and manufacturing evaluation;
8. next-best-experiment and purchase intelligence.

All 58 required specialist artifacts assigned immutable IDs `PCV3-C01-A001` through `PCV3-C08-A008` were located at their declared scope and mapped into the final artifact register. Forty-four required specialist artifacts carry worker-declared SHA-256 values from surfaced ledgers or hash tables. The fourteen required artifacts belonging to Chat 1 and Chat 3 remain under `PARTIAL_HASH_CLOSURE`: their content and declared completion state were located, but a separately surfaced package-level hash ledger was not available for independent byte closure during this integration.

This is a completed **architecture, schema, governance, queue, protocol, and integration** release. It is not an empirical perfume release. No missing source bytes, physical observations, measured headspace, strict empirical OAV, similarity pass, stability result, broad-appeal result, target-engine execution, or safety approval has been manufactured by the integration.

## 2. Source authority and conflict handling

### 2.1 Canonical authority order

The following hierarchy is normative:

1. Latest terminal-state, completion, addendum, and source-gap reports.
2. `Kenny_Current_Perfumery_Inventory_Master_Aug2026_v3.xlsx`.
3. `PROTOCOL.md`, `Meaningful_Complexity_Audit_v2.md`, and `SOL_5_6_PRO_Strict_Perfume_Reverification_V2.md`.
4. Exact `SYNCED` CrossBrand audit, formula book, and concentration register.
5. Literature, interaction, floral-coverage, style, and pilot-architecture sources.
6. The newest active brand-specific workbook.
7. Historical workbooks, archived formulas, prompts, and worker logs.

At equal scope, a newer authority supersedes an older one. A conflict is never averaged or silently fused. The final conflict register records the higher authority, resolution, residual hold, and required action. Where authority cannot be established, the canonical response is `HOLD` or the stronger decision-engine abstention:

`NO ACTION UNTIL AUTHORITY RESOLVED`

### 2.2 Authority anchors

The integrated map preserves these declared source anchors:

| Source | Role | SHA-256 state |
|---|---|---|
| `FINAL_VERIFICATION_REPORT.md` | terminal empirical/release boundary | declared `c294ef8294b6811ea15c70f9d295378a348ee5a5bf84e8db41c3303e903f979c` |
| `PHASE_C_F_TERMINAL_CHECKPOINT.md` | detailed C–F terminal state | declared `9687f179311f5a643413bc41a51e5de6e8a2f8688cbf11c90d8a47ade8058074` |
| `Kenny_Current_Perfumery_Inventory_Master_Aug2026_v3.xlsx` | exact-stock operational authority | declared `90049fd0445a1c69eea52ea1fb88909f51a49810ea77503e6aee690f4a00b21f` |
| `PROTOCOL.md` | non-compressed reconstruction and evidence separation | locally verified `f192fdea259052d445f39f2264b1907e92e1139ee8ddf112f57d2a7a99558961` |
| `Meaningful_Complexity_Audit_v2.md` | inherited G0–G14 governance | locally verified `07d84574365abb6a8e505fdcaf4e496ee1ac1d90f1397053d41f20b0a9394ff3` |
| `meaningful_complexity_schema.json` | inherited machine contract | locally verified `d0117d31e2f9e5383b92ddc21c71d44d5e4935a8ab431055e0b85ca20c75ee8a` |
| `SOL_5_6_PRO_Strict_Perfume_Reverification_V2.md` | strict empirical boundary | declared `ba048e0fc3687eef1a5aa3ed652075b3f02d8433bb317ab08a539dec4af3c51f` |
| `PERFUME_CHEM_LITERATURE_VERIFICATION_LEDGER.md` | literature claim ledger | locally verified `4f2206893d6f8d682aa6df798a3a5c8c9b2a815b8ed2c4025c20cd108544b9e7` |
| `Perfumery_Interaction_Layering_Atlas_v1.json` | interaction vocabulary and hypotheses | locally verified `321766b1892d6e684474aece142991d588a8719d0d7f5626e4cbf3254a3a5e90` |
| `experimental_data_model.schema.json` | canonical experimental schema | worker-ledger hash `ea8b84e03297bacf1d253c6a9d5d1467a103c9c9f6271693ed7c50fcbe5a8710` |

A declared File Library hash is retained as provenance, but it is not described as independently recomputed unless exact bytes were mounted in the final integration runtime.

## 3. Program-wide scientific invariants

These rules are noncompensatory:

1. **Notes are not molecules.** A note, accord label, public note pyramid, family name, or sensory descriptor cannot be converted directly into a molecular identity without evidence.
2. **Target and build are distinct.** Inventory availability may constrain a build, but it may not rewrite the evidence-faithful target.
3. **Formulas are not physical samples.** A `TargetFormula` or `BuildFormula` does not prove that a batch exists.
4. **Designed screens are not results.** A protocol, matrix, empty template, or expected outcome remains `PROPOSED` or `DESIGNED / NOT RUN`.
5. **Computed outputs are not measurements.** Computed headspace, simulated OAV, modeled release, and computational ablation belong in `ModelEstimate` or a computational `Decision`.
6. **Source reports are not direct observations.** Supplier or literature descriptions remain `REPORTED` and scoped.
7. **Blind identity stays separate.** A `CodedSample` exposes no true source identity; the true mapping lives in a restricted `BlindDecode`.
8. **Raw records are append-only.** Corrections supersede; they do not overwrite locked observations or measurements.
9. **Zero is not missing.** Missingness uses an explicit state and reason.
10. **One score cannot cancel a hard failure.** Complexity, liking, commercial appeal, manufacturability, similarity, and evidence authority remain multidimensional.
11. **Naturals are lot-scoped.** Species, origin, extraction, grade, supplier, and lot differences are not silently merged.
12. **Opaque product bases count once.** Their internal composition and active fraction are not invented.
13. **Physical chemistry is a hard gate.** Solubility, precipitation, crystallization, haze, oxidation, color, resin load, and solvent compatibility cannot be passed by desk prose.
14. **Software qualification is not perfume validation.** A qualified engine may evaluate declared logic; it cannot smell, establish beauty, prove headspace, or authorize skin use.
15. **No release without release evidence.** Program architecture completion cannot be promoted into formula, consumer, safety, or commercial release.

## 4. Canonical identity and data architecture

### 4.1 Identity layers

Chat 2 is the canonical common data model for physical and empirical work.

| Entity | Prefix | Meaning |
|---|---|---|
| `ReferenceSample` | `REF-` | exact commercial, historical, or retained physical reference |
| `TargetFormula` | `TF-` | immutable evidence-faithful, inventory-independent target snapshot |
| `BuildFormula` | `BF-` | immutable executable stock mapping linked to target and inventory snapshot |
| `PhysicalBatch` | `PB-` | material actually compounded from a build formula |
| `BottleOrVial` / container | `CNT-` | physical vessel containing material |
| `CodedSample` | `CS-` | blind presentation identity |
| `Experiment` | `EXP-` | bounded experimental protocol or execution record |
| `Condition` | `COND-` | exact experimental condition |
| `Substrate` | `SUB-` | blotter, surface, or other application substrate |
| `ApplicationAmount` | `APP-` | controlled application definition |
| `Assessor` | `ASSR-` | pseudonymous assessor |
| `AssessorCalibration` | `ACAL-` | calibration and sensitivity record |
| `Observation` | `OBS-` | append-only human sensory response |
| `Timepoint` | `TP-` | protocol-specific temporal point and tolerance |
| `Replicate` | `REP-` | replicate identity |
| `BlindDecode` | schema-defined | restricted true-identity mapping |
| `Decision` | schema-defined | scoped decision linked to locked inputs |
| `ProvenanceRecord` | schema-defined | entity/activity/agent provenance |
| `InteractionHypothesis` | schema-defined | scoped interaction hypothesis |
| `InteractionHypothesisRevision` | schema-defined | evidence-linked hypothesis revision |

Implementations must read the exact Chat 2 schema for every prefix not explicitly exposed in the integration sources. No prefix is invented merely to make an importer convenient.

### 4.2 Required referential integrity

- Every foreign key resolves to exactly one entity of the declared type.
- `PB-` requires a `BF-`; a target formula is never used as a physical batch ID.
- A `CNT-` contents reference points to physical material, not a formula snapshot.
- `CS-` records contain no true-origin identity.
- Sensory observations reference experiment, condition, coded sample, assessor, session, timepoint, replicate, and attribute.
- Time-dependent analytical measurements require timepoint and replicate unless the method is explicitly time-independent.
- Quantitative analytical claims require calibrated quantitation and an uncertainty record.
- Decode release records the observation-lock hash, release event, reason, and compromise state.
- A decision records exact evidence inputs, rule version, authority, blind state, limitations, and next action.
- An interaction hypothesis can be upgraded only through a scoped decision linked to actual observations or measurements.

### 4.3 Evidence categories

The canonical top-level categories are:

- `MEASURED`: instrumental or GC-O result tied to an analytical run;
- `OBSERVED`: human sensory response tied to assessor, coded sample, timepoint, and replicate;
- `INFERRED`: model output, documentary inference, or role prior;
- `PROPOSED`: protocol, hypothesis, or decision rule not yet executed;
- `REPORTED`: claim from a source, standard, official page, supplier, or secondary record;
- `DERIVED`: deterministic or statistical result, or human decision, derived from identified inputs.

Legacy labels are retained as metadata, not used to silently strengthen the canonical category.

### 4.4 Missingness and numeric policy

Canonical missing states:

`PRESENT`, `NOT_COLLECTED`, `NOT_APPLICABLE`, `BELOW_DETECTION_LIMIT`, `BELOW_QUANTIFICATION_LIMIT`, `INVALIDATED`, `LOST`, `WITHHELD_BLIND`, `UNKNOWN`

Every non-present state needs a reason. Exact decimal values are serialized as strings for deterministic canonicalization and stable hashing. Binary floating output is never treated as a canonical hash representation without an explicit normalization policy.

## 5. Meaningful Complexity Model v3

### 5.1 Classification model

Meaningful complexity is a noncompensatory vector:

1. recognizer complexity;
2. structural complexity;
3. interaction complexity;
4. temporal complexity;
5. textural complexity;
6. contrast complexity;
7. resilience complexity;
8. effective post-ablation complexity;
9. execution complexity;
10. hedonic complexity boundary.

The human-readable classes are:

- `COMPACT`
- `LAYERED`
- `HIGH_COMPLEXITY`
- `ORCHESTRAL`

A low row count does not automatically fail a legitimate compact composition. A high row count does not automatically establish complexity. Duplicate strengths, aliases, carriers, technical rows, opaque internal ingredients, and unconfirmed microtexture cannot inflate effective complexity.

### 5.2 V2 compatibility and G0–G14

The v2 minima of 50 distinct odor materials for a standalone accord and 65 for a full perfume remain hard only when:

- the artifact explicitly claims v2 compatibility; or
- an authoritative target-specific roster or function graph requires that many independent identities.

Otherwise they remain legacy row bands and compression-review triggers.

The G0–G14 gate system is preserved through an explicit crosswalk. No v2 gate is silently deleted. Chat 1 supplies the semantic replacement for row-count dominance, while Chat 3 supplies executable qualification fixtures. G14 cannot establish beauty, broad appeal, similarity, stability, or release.

### 5.3 Evidence cap

Designed recognizer paths, interaction graphs, temporal windows, texture axes, contrast axes, ablation candidates, and resilience scenarios may be computed. Claims of actual recognizability, full-mixture interaction, temporal perception, texture, contrast, resilience, and hedonic value require the corresponding physical and sensory evidence.

## 6. Interaction and exact-stock behavior layers

### 6.1 Interaction hypotheses

The group-level Interaction Atlas is a controlled hypothesis vocabulary, not a database of 253 empirically confirmed relationships. Its legacy scalar confidence is retained only as metadata.

Canonical effect types:

`ENHANCEMENT`, `SUPPRESSION`, `MASKING`, `CONFIGURATION`, `ROUNDING`, `PHASE_SHIFT`, `COLLISION`, `NULL`, `UNCERTAIN`

Canonical hypothesis evidence states:

`STRUCTURED_HYPOTHESIS`, `LITERATURE_SUPPORTED`, `PHYSICALLY_OBSERVED_SCOPED`, `ANALYTICALLY_SUPPORTED_SCOPED`, `CONTRADICTED_SCOPED`, `NULL_WITHIN_TESTED_SCOPE`

Canonical revision actions:

`RETAIN`, `REFINE`, `RESTRICT_SCOPE`, `UPGRADE_EVIDENCE`, `DOWNGRADE_EVIDENCE`, `REJECT`, `REPLACE`

A null result is reported only within the tested material, ratio, load, matrix, substrate, timepoint, assessor, and replicate scope.

### 6.2 Chat 4 tranche

Chat 4 provides a designed first tranche of twelve decisive material-pair tests and 120 condition definitions. It separates ratio from total load and includes A-alone and B-alone controls.

Current state:

- protocol design: complete;
- exact stock/lot reconciliation: held;
- assessor-specific P5 calibration: not run;
- physical compounding: not run;
- blind code/decode creation: not run;
- assessor sessions: not run;
- raw observations: absent;
- Atlas evidence update: not authorized.

The source state `COMPLETE_WITH_EXECUTION_HOLDS` is normalized to `COMPLETE_WITH_HOLDS` while its execution holds remain intact.

### 6.3 Chat 5 exact-stock atlas

The exact-stock layer distinguishes:

- canonical molecule or identity;
- supplier product;
- natural material;
- lot;
- stock dilution;
- product-basis material;
- physical preparation.

The 57-row priority register is a work queue, not a result set. Unsupported empirical fields remain `NOT_TESTED`. A planned dilution is not a prepared stock. Supplier or literature odor prose is not an observed exact-stock behavior.

The Ambrofix conflict is resolved operationally: the canonical 30% authority governs. Historical 40% execution rows stay quarantined and must be regenerated if that stock is not independently proven.

## 7. Floral coverage and interfaces

Chat 6 integrates a 25-family draft registry:

- 9 inherited families;
- 16 proposed families;
- 48 proposed branches;
- a 12-function spine;
- 32 cross-family interfaces;
- 16 explicit evidence-gap records.

Protected distinctions include:

- violet flower ≠ violet leaf ≠ iris flower ≠ orris root;
- magnolia ≠ muguet/floral air;
- orange-blossom-absolute direction ≠ neroli-oil direction;
- gardenia ≠ tuberose ≠ jasmine;
- ylang Complete ≠ ylang Grade III;
- peony ≠ freesia;
- lotus ≠ water lily;
- mimosa ≠ cassie without branch evidence;
- narcissus ≠ jonquil without species/cultivar scope.

All proposed floral families remain architecture and evidence queues. The lane has zero target-specific source closure, zero measured dose response, zero physical family-screen results, zero strict OAV, zero measured headspace, and zero safety release.

## 8. Hedonic, commercial, manufacturing, and lineage model

### 8.1 Scope separation

The following axes remain independent:

- reference identity and similarity;
- individual liking;
- broad appeal;
- artistic value;
- negative wear response;
- production practicality;
- stability evidence;
- cost and supply;
- safety and regulatory status.

Beauty is not computed from formula rows, complexity count, OAV, modeled headspace, ingredient price, or G14.

Similarity and beauty are orthogonal. A faithful reconstruction may be disliked; an attractive perfume may be unlike the reference.

### 8.2 Release classes

Permitted lineage classes:

- `ARTISTIC MASTER`
- `BROAD_APPEAL EDIT`
- `COST_CONTROLLED EDIT`
- `INVENTORY_FIT PILOT`
- `STABILITY_OPTIMIZED EDIT`
- `REFERENCE RECONSTRUCTION`

A release-class label states purpose, not proof. Every formula-changing edit creates a new child formula ID and hash. Manufacturing constraints may create a derivative build, but cannot silently mutate the evidence-faithful target.

### 8.3 Current empirical status

No existing perfume received:

- populated hedonic results;
- broad-appeal validation;
- formula-specific stability confirmation;
- current-cost and current-supply closure;
- overall hedonic/commercial/manufacturing score;
- release approval.

Chat 7’s provisional identifier fields must be adapted to Chat 2 rather than redefining Chat 2’s objects.

## 9. Real target-engine qualification

Chat 3 produced an implementation-ready qualification plan, adapter contract, fixture register, expected-gate matrix, mutation plan, regression policy, holds report, v2 fixture payload, and mismatch-resolution record.

The reference checker is an oracle-development tool. It is not the target engine.

**Authoritative target-engine state:** `NOT RUN`

Qualification requires:

1. target repository path and immutable source hash;
2. entry point and dependency lock;
3. implemented adapter with zero required-field loss;
4. exact expected terminal state;
5. exact sorted failed-gate set;
6. exact isolated failure codes;
7. complete positive, isolated, composite, Monte Carlo, mutation, and regression runs;
8. 100% kill of mandatory mutations;
9. independent clean-environment reproduction;
10. immutable inputs, outputs, seeds, environments, and hashes.

Even `QUALIFIED` would authorize only software behavior. It would not authorize perfume release, skin use, similarity, headspace, stability, beauty, or safety claims.

## 10. Decision intelligence

The next-best-experiment system supports exactly ten action types:

- `ADDITION_TEST`
- `ENGINE_IMPLEMENTATION_TASK`
- `INTERACTION_EXPERIMENT`
- `MATERIAL_DOSE_LADDER`
- `MATERIAL_PURCHASE`
- `OMISSION_TEST`
- `STABILITY_TEST`
- `STOCK_PREPARATION`
- `SUPPLIER_DOCUMENT_RETRIEVAL`
- `TARGET_COMPARISON`

It evaluates multidimensional profiles rather than one compensating score. Dimensions include expected information gain, expected sensory impact, formulas affected, uncertainty, cost, time, material consumption, reuse value, decision clarity, physical feasibility, and dependency unblocking.

Purchase classifications are exactly:

- `ESSENTIAL UNBLOCKER`
- `HIGH_VALUE ARCHITECTURAL EXPANSION`
- `USEFUL SPECIALIST`
- `REDUNDANT WITH CURRENT STOCK`
- `EVIDENCE GAP, NOT INVENTORY GAP`

A material is not purchased merely because it sounds interesting. An evidence deficit is not relabeled as an inventory gap. When supplier, lot, inventory, source, dependency, method, or physical authority is inadequate, the system abstains.

## 11. Current program holds

### 11.1 Open program holds

- Authentic 18/18 inherited Phase G source bytes and the complete full-hash PRE_DEF ledger have not been recovered.
- Designed physical work has not generated coded observations or measurements.
- No empirical perfume release gate has passed.

### 11.2 Open lane holds

- Target engine repository, adapter implementation, runtime execution, and qualification are missing.
- Chat 1 and Chat 3 package-level hash closure remains partial.
- Exact `SYNCED` portfolio bytes and final SHA-256 closure were not independently available in this integration runtime.
- Exact supplier, lot, label, density, solvent, and handling documents remain incomplete for physical execution.
- Assessor calibration, physical interaction tests, material ladders, floral screens, hedonic panels, stability studies, and matched target comparisons remain unrun.
- Safety and regulatory authorization remains external to this architecture package.

### 11.3 Nonblocking integration holds

- Some upstream files were integrated through File Library discovery, worker manifests, validation reports, and declared hash ledgers rather than copied raw bytes.
- Chat 7’s actual manifest is Markdown despite a later readiness summary referring to a JSON name. The Markdown manifest is retained as the located authority; no synthetic JSON upstream manifest is invented.
- The ZIP hash for this final package is stored in an external sidecar to avoid recursive self-reference.

## 12. Final state

```text
SPECIALIST LANES:             8 / 8 INTEGRATED
REQUIRED SPECIALIST ARTIFACTS: 58 / 58 LOCATED
ORIGINAL REQUIRED ARTIFACT IDs: 71 / 71 TERMINAL
INTEGRATION BUILD:            COMPLETE
WORKER STATE:                 COMPLETE_WITH_HOLDS
PROGRAM APPROVAL:             NOT ISSUED
EMPIRICAL RELEASE:            NOT AUTHORIZED
TARGET ENGINE:                NOT RUN
PHYSICAL RESULTS:             NOT CREATED BY THIS INTEGRATION
PHASE G:                      LOCKED / NOT AUTHORIZED
```

The next legitimate work is not another desk-only declaration of completion. It is the controlled closure of authority and implementation gaps, followed by actual coded physical work under the canonical data model.
