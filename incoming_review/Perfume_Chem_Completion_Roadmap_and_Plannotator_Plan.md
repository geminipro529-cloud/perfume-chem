# Perfume-Chem Completion Roadmap and Replacement Plannotator Plan

**Prepared:** 2026-07-29  
**Purpose:** Replace the narrow hardening plan with an executable convergence plan, then define the research-backed path from Laboratory Beta to a defensible Scientific Release.

---

## Executive decision

Do not run the existing hardening plan unchanged.

The current project status report describes a much more mature platform than the older reconstruction audit: a canonical workbench service, a transactional SQLAlchemy laboratory schema, append-only events, a FastAPI laboratory interface, backup and restore, hundreds of tests, and a verifier whose only current required failure is formula artifact binding in a modified working tree. The older audit, however, evaluates a reconstruction subsystem that still contains standalone ledgers, unintegrated gates, missing persistence, and several concrete defects.

The correct next step is therefore **convergence**, not the creation of another parallel architecture.

The immediate build should first establish the authoritative repository state and then merge the reconstruction subsystem into the existing laboratory domain model. Scientific completeness should follow in separate gated builds. A single giant agent run should not attempt architecture convergence, thermodynamic research, analytical validation, data backfilling, and sensory validation at once.

---

# Program structure

Use four separately approved builds:

1. **Build A: Canonical Convergence and Reconstruction Hardening**
2. **Build B: Scientific Data Authority and Analytical Validation**
3. **Build C: Matrix-Calibrated Headspace and Natural-Lot Intelligence**
4. **Build D: Preregistered Sensory Validation and Scientific Release**

Every build must produce an actual evidence package and may report partial completion. No build is allowed to manufacture a green acceptance matrix by weakening tests, changing definitions, or relabeling unsupported outputs.

---

# Literature-driven design rules

## 1. OAV is a screening quantity, not a likeness or intensity percentage

OAV may help identify potentially relevant odorants, but it cannot be treated as a linear measure of perceived intensity or percentage contribution. Thresholds vary among assessors, odor intensity functions differ among compounds, and compounds in mixtures may mask, enhance, or qualitatively change one another. The software must therefore keep separate claims for:

- above-threshold likelihood;
- perceived intensity;
- character contribution;
- mixture interaction;
- similarity to a target;
- temporal dominance.

OAV-based recommendations remain `HEURISTIC` unless validated against sensory or analytical evidence.

## 2. Sensory validation is the scientific release gate

A defensible release protocol requires selected and trained assessors, controlled test conditions, coded and randomized samples, repeat observations, a declared discrimination or profiling method, and a preregistered held-out evaluation. Profiling, triangle tests, and paired comparisons answer different questions and must not be interchanged. Fine fragrance carryover and persistence must be considered when selecting the test design.

## 3. Headspace is matrix-specific and nonideal

Concentration in the bottle is not equivalent to concentration in the headspace. Ethanol, water, polyols, long-chain materials, and other matrix components alter activity coefficients and partitioning. A headspace model must therefore state its matrix, temperature, composition, method, applicability domain, and uncertainty. Measured headspace evidence outranks a generic model.

## 4. Analytical results require method fitness and QC

GC-MS, GC-FID, HS-SPME, and GC-O records should not gain high authority merely because an instrument produced a file. The method record must include calibration, blanks, internal standards where applicable, selectivity, working range, detection and quantitation limits, precision, recovery or trueness, ruggedness, and uncertainty appropriate to the intended claim.

## 5. Natural materials are lot-specific mixtures

Natural raw materials require botanical and manufacturing identity plus lot-level analytical evidence. A chromatographic profile is generally a relative compositional profile, not automatically a true quantitative concentration table. Generic natural decompositions must remain explicitly source-derived proxies unless tied to the actual lot.

## 6. Provenance and hashes must be machine-actionable

Canonical records need stable identifiers, schema versions, derivation links, and deterministic hashing. Exact quantities should not be silently rounded through ordinary binary floating-point serialization. Provenance must identify the entity, activity, agent, source, transformation, and software version that produced each result.

## 7. Regulatory snapshots are dated, jurisdiction-specific, and fail closed

Compliance must be evaluated against an explicitly identified standards snapshot, product category, jurisdiction, date, and source digest. Draft or consultation material may be tracked as a watchlist, but it must not silently replace the currently notified standard. `UNKNOWN` safety or constituent data blocks a compliance release claim.

---

# BUILD A: Canonical Convergence and Reconstruction Hardening

## Title for Plannotator

**Canonical Convergence: Integrate Reconstruction into the Laboratory Beta Architecture**

## Global constraints

1. Do not create a new ledger, database table, domain class, API type, or persistence path until the baseline phase identifies whether an equivalent canonical object already exists.
2. The SQLAlchemy laboratory repository and the canonical workbench service are presumed authoritative only after they are verified in the exact working tree.
3. Preserve strict separation among:
   - evidence;
   - reconstructed target;
   - accepted target;
   - inventory stock lots;
   - measurable build plan;
   - physical bottle events;
   - analytical results;
   - sensory results;
   - regulatory and release snapshots.
4. A substitution may alter the build plan but must never rewrite the target.
5. An AI recommendation may create a proposal but may not confirm or commit a physical bottle or inventory action.
6. Do not weaken, delete, skip, or reinterpret an existing test to obtain a passing result.
7. Do not predeclare `20/20 DONE`, a fixed test count, a coverage percentage, or a completion label.
8. Preserve every uncommitted change before cleanup by recording a patch, untracked-file inventory, current commit, branch, and artifact hashes.
9. Preserve API compatibility through adapters unless an explicit defect requires a versioned breaking change.
10. No minute estimates. Each wave ends only when its evidence gate passes or its failure is documented.

---

## Phase A0: Establish the authoritative truth baseline

### A0.1 Repository and worktree capture

Record:

- repository remote;
- branch name;
- exact commit SHA;
- upstream relationship;
- `git status --porcelain=v2`;
- staged, unstaged, and untracked files;
- complete diff statistics;
- Python and Node lockfile digests;
- database URL and schema revision;
- all Alembic heads;
- generated artifact hashes;
- verifier command and configuration;
- active environment variables with secrets redacted.

Preserve uncommitted work as both:

- a binary-safe patch or bundle; and
- a file manifest with hashes.

Do not commit, stash, reset, regenerate, or rebind formula artifacts until the preserved baseline exists.

### A0.2 Reproduce the status report

Run the repository's canonical verifier and each test shard from a clean, documented environment. Save machine-readable results.

Verify, rather than assume:

- the canonical `PerfumeWorkbench` entry point;
- the transactional repository implementation;
- the laboratory database schema;
- bottle and inventory event tables;
- formula version tables;
- backup, restore, and export behavior;
- the number and identity of release gates;
- the formula-artifact validation failure and its claimed cause;
- the actual engine and backend test counts;
- whether the reconstruction branch is local-only, remote, merged, or divergent.

### A0.3 Architecture reconciliation map

Create an architecture decision record that maps every reconstruction object to the existing canonical object, or proves that no canonical equivalent exists.

At minimum map:

| Reconstruction concept | Candidate canonical destination |
|---|---|
| EvidenceLedger | evidence repository / evidence records |
| TargetFormula | immutable formula or target version |
| InventoryLedger / StockItem | stock lot and inventory movement records |
| BuildFormula | build-plan version and build-line records |
| BottleBatch / BottleEvent | bottle stream and append-only event records |
| FormulaVersion DAG | canonical immutable formula version model |
| AnalyticalLedger | analytical runs, peaks, QC, and attachments |
| SensoryLedger | protocol, sample, observation, outcome |
| RegulatorySnapshot | dated safety and jurisdiction snapshot |
| AuthorityVector | claim-specific authority assessment |

For each pair choose one of:

- `CANONICAL_EXISTING`;
- `ADAPT_LEGACY_TO_CANONICAL`;
- `MIGRATE_AND_DEPRECATE_LEGACY`;
- `MISSING_CREATE_CANONICAL`;
- `EXPERIMENTAL_DO_NOT_PERSIST`.

The ADR must identify the single source of truth for each concept and prohibit bidirectional unsynchronized stores.

### Phase A0 exit gate

No implementation work proceeds until:

- the exact source state is reproducible;
- the current verifier result is captured;
- uncommitted work is preserved;
- the canonical domain map is approved;
- duplicate truth stores are identified.

---

## Phase A1: Convert the six audit findings into executable contract tests

Do not edit the implementation first. Reproduce each defect with a failing test against the exact current branch. If a defect is already fixed, record the evidence and retain a regression test without rewriting working code.

### A1.1 Solvent and carrier classification

Required behavior:

- ethanol and aqueous ethanol stocks classify as solvent;
- DPG, DEP, TEC, and IPM classify according to their declared use and stock basis, not solely by string membership;
- a material may be an odorant-bearing stock whose carrier and active component are accounted separately;
- classification is independent from concentration basis.

Test exact active, carrier, solvent, and total mass or volume conservation.

### A1.2 Target row preservation

All accepted input fields must survive target construction, including:

- provenance links;
- identity and quantity confidence;
- uncertainty bounds;
- grade;
- concentration basis;
- unit;
- source row identifier.

Unknown fields must either be rejected under strict mode or preserved in a versioned extension field. They must not disappear silently.

### A1.3 Anti-compression alignment

Implement the protocol criteria using three-valued results:

- `MATCH`;
- `DIFFER`;
- `UNKNOWN`.

Unknown evidence must not be treated as proof of equivalence.

Exact synonym merging is allowed only when identity equivalence is demonstrated. A neat material and a dilution of the same material may share the same chemical identity but remain different stock identities and physical doses.

The audit must detect:

- one stock material mapped to several distinct target identities;
- collapsed supplier grades;
- collapsed stereoisomers;
- collapsed natural lots or chemotypes;
- partial functional substitutions presented as exact identity matches.

### A1.4 Chained correction replay

Correction resolution must:

- follow the reference chain to the original event;
- preserve every historical event;
- apply the latest valid replacement under a documented rule;
- reject missing references;
- reject cross-batch references unless explicitly supported;
- detect cycles;
- remain deterministic under repeated replay.

### A1.5 Empty reconstruction inputs

Every public reconstruction entry point must reject an empty roster with a stable domain validation error before denominator or normalization logic executes.

### A1.6 Identity resolution versus stock availability

Use two independent enums.

`IdentityResolutionStatus`:

- `EXACT`;
- `ALIAS`;
- `AMBIGUOUS`;
- `UNRESOLVED`.

`InventoryMatchStatus`:

- `EXACT_LOT_AVAILABLE`;
- `EXACT_IDENTITY_NOT_IN_STOCK`;
- `GRADE_MISMATCH`;
- `FUNCTIONAL_SUBSTITUTE_AVAILABLE`;
- `NO_SUITABLE_STOCK`;
- `NOT_TECHNICALLY_REQUIRED`.

A resolved material that is absent from inventory is not an unknown identity. An ambiguous or unresolved name must not be converted into a confident canonical material.

### Phase A1 exit gate

- Each audit defect has a reproduction record.
- Each confirmed defect has a focused fix and regression test.
- The full pre-existing verifier still passes except for baseline failures already documented.
- No schema expansion has occurred outside the approved architecture map.

---

## Phase A2: Converge the domain model and persistence layer

### A2.1 Canonical build-plan model

Create a build-plan model only if the baseline proves that no equivalent exists. Prefer migration into the existing transactional repository over a standalone `engine/build/ledger.py` data island.

A canonical build plan must contain:

- stable build-plan ID and version;
- immutable target version reference;
- one line per target line or explicit technical line;
- selected stock lot reference;
- planned raw quantity and unit;
- planned active quantity and basis;
- uncertainty;
- measurability classification;
- substitution classification;
- preserved and lost functions;
- substitution rationale and evidence;
- density and concentration source references;
- status: draft, reviewed, reserved, executing, closed, superseded;
- parent and content hash.

No build-plan operation may mutate the target formula.

### A2.2 Canonical lifecycle graph

Implement and test the reference chain:

```text
Evidence
  -> Target hypothesis version
  -> Accepted target version
  -> Inventory mapping
  -> Build-plan version
  -> Inventory reservation
  -> Proposed bottle action
  -> Human confirmation
  -> Committed bottle event
  -> Inventory movement
  -> Replayed bottle state
  -> Analytical and sensory observations
  -> New evidence or posterior
  -> New target version
```

Updates create new versions or events. They do not rewrite prior accepted records.

### A2.3 Legacy adapters and migration

For each standalone reconstruction class:

- add a one-way adapter to the canonical model;
- migrate persisted fixtures where applicable;
- mark the legacy path deprecated;
- prohibit new writes to the legacy store;
- add equivalence tests between legacy input and canonical output;
- remove the legacy model only in a later, separately reviewed migration.

### A2.4 Database migrations

Migrations must be:

- reversible where practical;
- idempotent in tests;
- tested from the previous released schema;
- tested on a representative copy of the local database;
- guarded against duplicate events or IDs;
- accompanied by backup and restore verification.

### Phase A2 exit gate

There is exactly one authoritative persisted representation for target, stock lot, build plan, bottle event, inventory movement, analysis, sensory observation, and release snapshot.

---

## Phase A3: Versioned serialization, provenance, quantities, and hashes

### A3.1 Replace shallow `from_dict()` generation

Do not add a generic `cls(**filtered_dict)` implementation across modules.

Use the project's canonical typed validation layer for API and persistence boundaries. Serialization must restore:

- nested models;
- enums;
- dates and datetimes;
- decimals;
- UUIDs;
- tuples and constrained collections;
- discriminated unions;
- quantity type and unit;
- schema version;
- optional extension fields.

Tests must assert runtime types and invariants, not merely equality after a second dictionary conversion.

### A3.2 One quantity system

All state and diff code must use one canonical quantity abstraction.

Keep distinct:

- raw mass;
- active mass;
- carrier mass;
- solvent mass;
- raw volume;
- active volume;
- concentration fraction and basis;
- density;
- uncertainty.

Mass and volume may be compared only when an explicit density with source and applicable conditions exists. Active and raw quantities may be compared only when concentration fraction and basis are known.

Incomparable states return a structured reason such as:

- `MISSING_DENSITY`;
- `UNSPECIFIED_CONCENTRATION_BASIS`;
- `MISSING_ACTIVE_FRACTION`;
- `UNIT_NOT_CONVERTIBLE`;
- `UNCERTAINTY_TOO_LARGE`.

### A3.3 Deterministic canonical hashing

Hash a canonical payload that includes:

- schema version;
- canonical units;
- exact decimal strings;
- stable identity references;
- ordered line identifiers;
- parent hash;
- source digests;
- algorithm identifier.

Use a standards-based canonical JSON representation. Do not hash ordinary floating-point dumps or presentation markdown.

### A3.4 Provenance model

Record provenance in a form that can map to:

- entity;
- activity;
- agent;
- derivation;
- generation time;
- software and model version;
- source citation;
- transformation parameters;
- confidence and evidence class.

Generated markdown and UI views remain projections. Canonical records remain reconstructable without them.

### A3.5 Artifact binding

For every formula artifact:

- persist the canonical record hash;
- persist the renderer version;
- persist the analysis input hash;
- verify by re-reading the artifact;
- distinguish intentional content edits from stale generated analysis;
- provide an explicit rebind command that refuses uncommitted ambiguous state.

### Phase A3 exit gate

Every persisted object has a versioned, type-correct round trip; every canonical hash is deterministic across supported platforms; every artifact can identify the canonical record and renderer that generated it.

---

## Phase A4: Make claim and action gates genuinely fail closed

### A4.1 Mode and action state machine

Model permissions as transitions, not a decorative mode label.

At minimum distinguish:

- inspect;
- reconstruct;
- map inventory;
- draft build;
- reserve stock;
- propose bottle action;
- confirm action;
- commit measurement;
- correct event;
- run analysis;
- record sensory outcome;
- evaluate compliance;
- release.

The gate evaluates actor, mode, current state, requested transition, and required confirmation. AI actors may not perform human confirmation or commit a physical action.

### A4.2 Claim-specific authority

Do not derive authority from the maximum confidence value.

For every claim, calculate and expose:

- row coverage;
- source independence;
- identity resolution;
- quantity basis completeness;
- uncertainty;
- contradiction status;
- analytical support;
- sensory support;
- model applicability;
- safety data completeness.

Critical unsupported rows, unresolved contradictions, or unknown safety data must not disappear inside an average.

The gate should answer a specific question, for example:

- `May compute exact bottle mass balance?`
- `May claim material identity?`
- `May claim above-threshold likelihood?`
- `May claim target similarity?`
- `May claim IFRA-screened for category X under snapshot Y?`
- `May release automatically?`

### A4.3 Family gate

An undefined family blocks only family-specific drift and family-compliance claims. It must not block exact arithmetic or generic record operations.

A family evaluation must identify:

- archetype version;
- protected anchors;
- allowed uncertainty;
- forbidden or genre-shifting materials;
- target and current values;
- unknown-data handling;
- sensory or literature status.

### A4.4 Concentration and density gate

Fail a quantitative claim when a required basis is missing.

Do not fail merely because a carrier exists. Fail when the requested calculation requires information that is absent, such as stock concentration, concentration basis, density, temperature, or composition.

### A4.5 Safety and regulatory gate

Safety is a state, not a soft confidence score:

- `PASS_FOR_DECLARED_SCOPE`;
- `FAIL`;
- `UNKNOWN`;
- `NOT_EVALUATED`.

Only the first state permits a scoped compliance claim.

Each snapshot records:

- IFRA amendment;
- standard identifier and source digest;
- product category;
- jurisdiction;
- formula version;
- constituent basis;
- natural contribution assumptions;
- evaluation date;
- evaluator version;
- unknown and unresolved items.

Track draft or consultation standards separately as watchlist data.

### Phase A4 exit gate

A deliberately unsupported identity, concentration, family, safety, or sensory claim produces a deterministic block with an actionable reason.

---

## Phase A5: Complete operational bottle and inventory behavior

### A5.1 Bottle event semantics

Define and test semantics for every event type. In particular:

- `ADD_MATERIAL` and `ADD_SOLVENT` add measured quantities without rewriting history;
- `DILUTE` is represented by actual additions and a derived concentration state;
- `TARE_CONTAINER` changes the tare reference, not the chemical contents;
- `TRANSFER` creates one transaction linking source decrement and destination increment;
- `CLOSE_BATCH` blocks ordinary additions;
- privileged administrative reopen or correction, if allowed, is explicit and audited;
- correction chains are deterministic and cycle-safe;
- retries are idempotent;
- stream sequence prevents stale writes.

### A5.2 Inventory movements

Do not implement `consume(material_id, amount_ml)` as an in-place decrement.

Use append-only inventory movements with:

- movement ID;
- stock lot;
- build-plan line;
- bottle event or administrative cause;
- quantity and unit;
- active and raw basis where relevant;
- balance before and after;
- uncertainty;
- timestamp;
- actor;
- correction or reversal reference;
- transaction ID.

Support:

- reservation;
- reservation release;
- consumption;
- return;
- adjustment;
- transfer;
- correction.

Reject insufficient stock atomically and prevent negative balances under concurrent requests.

### A5.3 Lot selection

Lot selection must be policy-driven and explainable.

Default priorities:

1. exact identity and required grade;
2. compatible concentration and basis;
3. enough measurable stock including uncertainty margin;
4. valid safety and expiry state;
5. opened-lot or FEFO policy;
6. minimum conversion uncertainty;
7. minimum waste.

Do not automatically prefer the highest concentration or oldest unopened stock without a declared policy.

### A5.4 Structured state diffs

Return structured delta records, not strings that mix microlitres and grams.

Each delta contains:

- material and target-line ID;
- target quantity;
- selected stock quantity;
- planned active quantity;
- committed bottle quantity;
- unit and basis;
- uncertainty interval;
- substitution state;
- comparable or incomparable status;
- preserved and lost functions;
- open or closed action status.

Render strings only at the UI boundary.

### A5.5 Propose -> Confirm -> Measure -> Commit

The full lifecycle must be transactional:

1. software proposes;
2. human reviews and confirms;
3. measurement is entered or captured;
4. commit writes bottle event and inventory movement atomically;
5. replay verifies resulting state;
6. a failure writes neither half of the transaction;
7. a correction appends new events rather than editing prior ones.

### Phase A5 exit gate

Target -> inventory -> build -> bottle -> inventory replay is deterministic, unit-safe, and fully auditable under normal, correction, transfer, retry, and failure cases.

---

## Phase A6: Verification and evidence package

### A6.1 Test strategy

Add tests according to risk, not a promised count.

Required classes:

- focused unit tests for each defect;
- property-based tests for conservation and unit conversion;
- state-machine tests for bottle and inventory streams;
- correction-chain fuzz tests;
- transaction rollback and concurrency tests;
- schema migration tests;
- serialization compatibility tests;
- canonical hash golden tests;
- API contract tests;
- report projection tests;
- end-to-end lifecycle tests;
- generated artifact validation;
- backup, restore, and export regression;
- negative tests proving fail-closed gates.

New tests target the canonical API. Test agents may not patch production code in parallel unless separately assigned after an integration failure is triaged.

### A6.2 Verification sequence

After every wave run:

- compile;
- lint;
- type checking;
- all engine shards;
- all backend tests;
- scientific and material-data audits;
- knowledge-rule validation;
- golden formula and API regressions;
- package and wheel smoke;
- artifact lock and formula-artifact validation;
- database migration and backup/restore tests;
- Docker checks where infrastructure permits.

### A6.3 Required evidence artifact

Write `docs/verification/canonical_convergence_report.md` and machine-readable JSON containing:

- exact baseline and final commit;
- changed-file inventory;
- migration inventory;
- architecture mapping;
- old defect -> reproduction -> fix -> test;
- full verifier output;
- acceptance matrix with actual statuses;
- skipped checks and reasons;
- remaining limitations;
- deprecated paths;
- rollback instructions;
- claim and release status.

### Build A completion criteria

Build A is complete only when:

- the working tree used for verification is clean or every intentional generated difference is explicitly bound;
- all required verifier checks pass, excluding only documented infrastructure skips;
- there is one canonical persisted truth path;
- the six audit defects are either fixed or proven absent;
- no shallow deserializer has been introduced;
- target, inventory, build, and bottle states remain independently addressable;
- bottle and inventory transactions are atomic and replayable;
- critical gates fail closed;
- every remaining limitation is explicit.

Build A does **not** imply Scientific Release.

---

# BUILD B: Scientific Data Authority and Analytical Validation

## Objective

Turn the current large heuristic data layer into a provenance-rich evidence system and make analytical records fit for the claims they support.

## B1. Data authority registry

For every scientific value record:

- material identity and grade;
- property;
- value and unit;
- uncertainty or interval;
- temperature, pressure, and matrix;
- method;
- source type;
- full citation;
- access date;
- extraction or transformation;
- evidence class;
- applicability domain;
- conflicts;
- supersession history.

Keep separate stores or explicit partitions for:

- authoritative literature or reference data;
- supplier data;
- measured local data;
- derived estimates;
- heuristics;
- unknowns.

Never replace an unknown with a heuristic without changing the evidence class.

## B2. ODT registry redesign

An odor threshold record must include:

- medium and matrix;
- orthonasal or retronasal route;
- detection, recognition, or other endpoint;
- assessor population and count where available;
- method;
- temperature;
- unit;
- distribution or range;
- source;
- evidence quality.

The current scalar ODT may remain as a compatibility projection, but strict scientific mode reads the contextual records.

Prioritize backfill by value of information:

1. materials in active or reference formulas;
2. materials to which release scores are most sensitive;
3. materials with extreme OAV under uncertain thresholds;
4. regulated or safety-critical materials;
5. natural constituents used in lot decomposition.

Do not pursue blanket coverage by inserting weak estimates.

## B3. Knowledge-rule normalization

Normalize advisory pairing and synergy rules to exact identities where evidence permits.

Each rule records:

- participants;
- identity specificity;
- matrix;
- dose region;
- claimed interaction;
- source;
- evidence level;
- contradictory evidence;
- applicability limits.

Generic terms such as `rose`, `orange`, `musks`, or `florals` remain explicitly generic advisory nodes and never masquerade as exact chemical rules.

## B4. Analytical method and QC model

Extend the analytical domain to support:

- method versions;
- instrument and column;
- acquisition parameters;
- sample preparation;
- matrix and dilution;
- internal standards;
- calibration;
- blanks;
- retention indices;
- library match metrics;
- quantified peaks and uncertainty;
- GC-O events aligned to chromatographic regions;
- HS-SPME fiber and equilibration conditions;
- quality-control samples;
- run acceptance criteria;
- attachments and raw-file hashes.

## B5. Method validation

For every analytical method used to support a quantitative or release claim, document fitness for purpose using:

- selectivity;
- working range;
- calibration model;
- sensitivity;
- LOD and LOQ where relevant;
- trueness or recovery;
- repeatability;
- intermediate precision;
- robustness;
- uncertainty;
- ongoing QC.

A nonvalidated method may still store exploratory results but cannot grant high authority.

## B6. Reference-data ingestion

Add source adapters with pinned versions and provenance for data such as:

- NIST Chemistry WebBook;
- peer-reviewed primary literature;
- official standards;
- supplier COAs and SDSs;
- local measurements.

No scraper output enters canonical scientific data without identity resolution, unit validation, source digest, and conflict checking.

## Build B exit criteria

- Every runtime scientific value exposes its evidence class and provenance.
- Strict mode can refuse heuristic thresholds and properties.
- Analytical results have method and QC context.
- Data conflicts are visible and do not resolve through silent overwrite.
- Coverage reports distinguish count from authority.

---

# BUILD C: Matrix-Calibrated Headspace and Natural-Lot Intelligence

## Objective

Replace the current generic or stubbed physical-chemistry layer with benchmarked, applicability-aware models and lot-specific natural evidence.

## C1. Headspace model interface

Define a versioned model interface whose output includes:

- predicted gas-phase concentration or partition quantity;
- matrix composition;
- temperature;
- model name and version;
- required inputs;
- fallback path;
- applicability-domain result;
- uncertainty;
- evidence class.

Support separate adapters for:

- ideal or empirical baseline;
- modified UNIFAC where group coverage is adequate;
- COSMO-RS or imported COSMO-RS predictions where available;
- locally calibrated empirical models;
- measured headspace observations.

Do not label a Hansen-distance approximation as UNIFAC.

## C2. Property and parameter layer

Ingest measured vapor pressure or Antoine data with:

- source;
- valid temperature range;
- phase;
- uncertainty;
- equation form;
- unit normalization.

Outside the valid range, either:

- use a separately labeled fallback; or
- return `OUT_OF_DOMAIN`.

Do not extrapolate silently.

## C3. Matrix benchmark set

Build a controlled benchmark across representative matrices:

- ethanol/water concentrations;
- DPG-rich;
- TEC- or DEP-rich;
- oil;
- representative concentrate.

Use selected fragrance molecules spanning:

- volatility;
- polarity;
- hydrogen bonding;
- molecular size;
- functional groups.

Compare model predictions with measured headspace under controlled HS-SPME or another validated method.

## C4. Uncertainty propagation

Propagate uncertainty from:

- dose;
- stock concentration;
- density;
- vapor pressure;
- activity coefficient;
- calibration;
- temperature;
- model residual.

Use analytical propagation where justified and Monte Carlo propagation for nonlinear models. Report intervals and sensitivity contributions.

## C5. Natural-lot identity and profiles

For each natural lot store:

- botanical species;
- plant part;
- chemotype;
- origin;
- harvest or production date where known;
- extraction method;
- processing;
- supplier;
- lot;
- storage;
- GC-FID relative profile;
- GC-MS identities and match quality;
- quantified constituents where actually measured;
- allergens and restricted constituents;
- profile uncertainty;
- reference-standard comparison.

Keep relative chromatographic profile and absolute quantified composition as different data products.

## C6. Composite natural OAV

Use this precedence:

1. actual lot-specific quantified composition;
2. actual lot relative profile with clearly stated assumptions;
3. supplier batch composition;
4. literature source-specific proxy;
5. generic proxy;
6. unknown.

The UI and API must show which level was used. A generic proxy may guide exploration but cannot support a lot-specific regulatory claim.

## C7. Model validation and abstention

For each model publish:

- benchmark dataset;
- error metrics;
- calibration plot;
- residual analysis;
- applicability domain;
- known failure regions;
- comparison with simple baselines;
- model card;
- versioned parameter set.

The engine abstains when inputs or domain support are insufficient.

## Build C exit criteria

- Headspace outputs are matrix-specific and uncertainty-labeled.
- At least one physical model is demonstrably better than a declared baseline on held-out measured data.
- Natural lots are independently identifiable and comparable.
- Generic natural profiles are never confused with regulatory constituent data.
- Stub science modules are either replaced, clearly experimental, or removed from authoritative execution.

---

# BUILD D: Preregistered Sensory Validation and Scientific Release

## Objective

Resolve the stated Scientific Release blocker with a reproducible, blinded, held-out sensory program.

## D1. Define the claims before choosing tests

Separate endpoints:

- detectable difference;
- directional difference in a named attribute;
- target-reference similarity;
- descriptive profile distance;
- temporal profile agreement;
- preference or liking;
- prediction calibration.

Choose a method for each endpoint. Do not use a preference test as evidence of chemical similarity or use OAV error as evidence of sensory likeness.

## D2. Panel and facility protocol

Specify:

- assessor selection and training;
- screening and ongoing performance monitoring;
- coding and blinding;
- randomized and balanced order;
- replicate sessions;
- environmental controls;
- sample preparation and application;
- blotter or skin substrate;
- application mass;
- evaluation time points;
- carryover controls and session limits;
- adverse-event and exclusion rules;
- missing-data handling.

Fine-fragrance persistence makes carryover a first-class design constraint.

## D3. Reference and sample locking

Before preregistration:

- lock the target reference lot or bottle;
- record storage and age;
- lock formula and build hashes;
- lock stock lots;
- lock mixing protocol;
- lock maturation interval;
- lock application protocol;
- lock the model and all thresholds;
- generate blinded codes independently.

## D4. Pilot study

Use a pilot only to test:

- logistics;
- assessor training;
- attribute vocabulary;
- variance estimates;
- carryover;
- data capture;
- feasibility.

Pilot data must not be reused as held-out confirmatory data.

## D5. Preregistered confirmatory study

Preregister:

- primary and secondary endpoints;
- null and alternative hypotheses;
- baseline methods;
- effect size or equivalence margin;
- alpha and power;
- sample-size calculation;
- randomization;
- exclusion rules;
- model version;
- statistical model;
- multiplicity handling;
- stopping rule;
- success criteria.

Use held-out formulas, lots, or reconstruction targets. Do not tune on the confirmatory set.

## D6. Statistical analysis

Use methods appropriate to the design, potentially including:

- exact binomial analysis for forced-choice tests;
- mixed-effects models for profile ratings;
- assessor and session random effects;
- equivalence or noninferiority analysis where similarity is the claim;
- bootstrap confidence intervals;
- calibration and discrimination metrics;
- multiple-comparison control;
- sensitivity analysis for missing observations.

Report effect estimates and uncertainty, not only p-values.

## D7. Model calibration after confirmation

Only after the confirmatory result is locked:

- calibrate future models on training data;
- compare OAV-only, physical-headspace, and combined models;
- maintain a permanently held-out benchmark;
- version model cards and datasets;
- separate objective similarity from personal preference.

Receptor activation and emotion prediction remain exploratory until they have sufficient human-relevant data and independent validation.

## D8. Release package

A Scientific Release package contains:

- exact software and model versions;
- database schema;
- source-data manifests;
- formula and lot hashes;
- preregistration;
- blinded code key held separately until lock;
- raw and processed sensory data;
- analysis code;
- analytical method validation;
- model cards;
- regulatory snapshot;
- full verifier output;
- limitations;
- reproduction instructions.

## Build D exit criteria

Scientific Release may be declared only when:

- the preregistered held-out primary endpoint passes;
- the locked model beats or meets its declared baseline or equivalence criterion;
- sensory and analytical records trace to exact formula, build, bottle, and lot versions;
- uncertainty is reported;
- no critical safety or identity state is unknown;
- the software verifier passes;
- the claim wording matches the evidence.

A Scientific Release is not an IFRA certificate, cosmetic product safety report, or regulatory approval.

---

# Execution waves

## Wave 0: Truth baseline

Sequential only. Capture source state, run verifier, preserve worktree, and approve the architecture map.

## Wave 1: Defect contracts and focused repairs

The six defect investigations may run in parallel only after the baseline is locked and only when they do not edit shared schemas. Integrate sequentially and run the full verifier after each merge.

## Wave 2: Canonical schema convergence

Sequential architecture work. Approve domain model, migrations, and adapters before gate or UI work.

## Wave 3: Serialization, provenance, gates, bottle, and inventory

Use small sub-waves ordered by dependency:

1. quantities and serialization;
2. provenance and canonical hashes;
3. build-plan mapping;
4. bottle and inventory transactions;
5. gates and lifecycle;
6. API adapters.

## Wave 4: Build A verification

No new features. Close defects, run all checks, generate evidence package, and report actual status.

## Wave 5: Scientific data and analytical foundation

Build B only after Build A is merged and stable.

## Wave 6: Physical chemistry and natural lots

Build C only after property and analytical data contracts are stable.

## Wave 7: Sensory pilot and preregistration

Build D pilot and protocol work. Freeze model before confirmatory data collection.

## Wave 8: Held-out validation and release review

Run the locked confirmatory study, analyze as preregistered, and publish the actual outcome.

---

# Acceptance tiers

## Engineering Complete

- deterministic exact arithmetic;
- typed quantities;
- transactional persistence;
- replay and migrations;
- full software verification.

## Laboratory Beta

- operational UI and API;
- evidence classes;
- analytical and sensory ledgers;
- backup, restore, and export;
- unsupported science withheld or labeled.

## Scientific Validation Candidate

- authoritative source state;
- validated analytical methods;
- matrix-aware model with uncertainty;
- lot-aware naturals;
- preregistered sensory protocol;
- locked model and baseline.

## Scientific Release

- held-out preregistered validation passes;
- claims are calibrated to evidence;
- complete reproducibility package;
- no unresolved critical safety, identity, or data-integrity blockers.

---

# Explicit non-goals and anti-patterns

- Do not equate OAV with similarity, intensity, or percentage contribution.
- Do not fill missing ODT, Antoine, receptor, or natural-composition fields with guesses merely to raise coverage.
- Do not build a second ledger system beside the transactional laboratory schema.
- Do not maintain mutable inventory balances without an event or movement history.
- Do not compare microlitres directly with grams.
- Do not use maximum source confidence as formula authority.
- Do not allow `UNKNOWN` safety to pass a release gate.
- Do not enforce draft IFRA standards as though formally notified.
- Do not treat a generic natural decomposition as the actual supplier lot.
- Do not force a fixed test count or `20/20 DONE`.
- Do not use a six-sample convention in place of a power calculation.
- Do not let test agents rewrite production APIs merely to satisfy their own tests.
- Do not let an LLM become the authority for arithmetic, inventory, safety, identity, or release.

---

# Required references for the implementation dossier

1. Audouin V, Bonnet F, Vickers ZM, Reineccius GA. *Limitations in the Use of Odor Activity Values to Determine Important Odorants in Foods*. ACS Symposium Series 782, 2001. DOI: 10.1021/bk-2001-0782.ch014.
2. Ma Y et al. *Assessing the contribution of odor-active compounds in icewine considering odor mixture-induced interactions through gas chromatography-olfactometry and Olfactoscan*. Food Chemistry, 2022. DOI: 10.1016/j.foodchem.2022.132991.
3. Fredenslund A, Jones RL, Prausnitz JM. *Group-contribution estimation of activity coefficients in nonideal liquid mixtures*. AIChE Journal, 1975. DOI: 10.1002/aic.690210607.
4. Gmehling J, Wittig R, Lohmann J, Joh R. *A Modified UNIFAC (Dortmund) Model. 4. Revision and Extension*. Industrial & Engineering Chemistry Research, 2002. DOI: 10.1021/ie0108043.
5. Conner JM et al. *Headspace concentrations of ethyl esters at different alcoholic strengths*. Journal of the Science of Food and Agriculture, 1998. DOI: 10.1002/(SICI)1097-0010(199805)77:1<121::AID-JSFA14>3.0.CO;2-V.
6. Dupeux T et al. *COSMO-RS as an effective tool for predicting the physicochemical properties of fragrance raw materials*. Flavour and Fragrance Journal, 2022. DOI: 10.1002/ffj.3690.
7. ISO 8586:2023, selection and training of sensory assessors.
8. ISO 13299:2016, establishing a sensory profile.
9. ISO 4120:2021, triangle test.
10. ISO 5495:2005, paired comparison test.
11. ISO 8589:2007 and its developing successor, sensory test rooms.
12. ISO/IEC 17025:2017, competence of testing and calibration laboratories.
13. Eurachem. *The Fitness for Purpose of Analytical Methods*, third edition, 2025.
14. JCGM 100:2008 and JCGM 101:2008, measurement uncertainty and Monte Carlo propagation.
15. ISO 9235:2021, aromatic natural raw material vocabulary.
16. ISO 11024-1:1998, ISO 11024-2:1998, and ISO/DIS 11024, chromatographic profiles of essential oils.
17. Wilkinson MD et al. *The FAIR Guiding Principles for scientific data management and stewardship*. Scientific Data, 2016. DOI: 10.1038/sdata.2016.18.
18. W3C PROV family of recommendations.
19. RFC 8785, JSON Canonicalization Scheme.
20. Current IFRA Standards documentation and amendment notifications.
21. Regulation (EU) 2023/1545 on fragrance allergen labelling.

---

# Final instruction to the build agent

Treat the status report, older audit, and this roadmap as evidence inputs rather than self-validating truth.

First establish the exact authoritative repository and database state. Then integrate the reconstruction subsystem into the existing canonical laboratory architecture without creating duplicate truth stores. Fix only reproduced defects. Use versioned typed quantities, append-only transactions, deterministic hashes, explicit provenance, and claim-specific fail-closed gates.

Complete Build A and produce its evidence package before starting scientific expansion. After Build A, execute Builds B, C, and D as separate approved programs. Report actual outcomes at every gate, including partial or failed results. Never infer scientific release from software tests alone.
