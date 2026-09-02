# Replacement Plannotator Plan

**Use this plan for the current build.** It deliberately completes canonical convergence and hardening first. The broader scientific roadmap is in the companion completion document.

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
