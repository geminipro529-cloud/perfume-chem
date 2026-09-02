# PERFUME-CHEM — All-Chat Latest Detailed Report Request

**Collection cut:** 2026-08-09, Asia/Bangkok  
**Purpose:** recover every project lane at byte, semantic, functional, evidentiary, and operational fidelity before any installation or cutover into `perfume-chem`.  
**Mode:** `READ_ONLY_REPORTING`. `mutation_authorized=false`. Do not mutate formulas, inventory, databases, repository branches, releases, or physical-work status in response to this request.

## Message to send unchanged to every project chat

Please produce your **latest authoritative-state, detailed handoff report** for your complete scope in the perfume-chem project. Call it terminal only if the lane is truly terminal; otherwise report `IN_PROGRESS`, `PARTIAL`, `BLOCKED`, or `REJECTED` accurately. This is a lossless integration collection: the report must make it possible to install or preserve everything you produced without losing information, functions, calculations, schemas, tests, provenance, uncertainty, conflict history, failed attempts, or meaningful complexity.

Use the current authority rules below. Do not silently resolve conflicts and do not promote hypotheses, models, screens, or planned work into measured facts. **Do not run tests, migrations, installs, commits, pushes, uploads, regenerations, or physical work for this request.** Report only historically executed actions and proposed future actions, clearly separated.

### 1. Identity and terminal state

- Give the exact chat title/identifier, lane, role, scope, report timestamp and timezone.
- State the latest authoritative status using one of: `COMPLETE`, `PASS_WITH_HOLDS`, `FROZEN_FOR_REVIEW`, `IN_PROGRESS`, `PARTIAL`, `BLOCKED`, `REJECTED`, `SUPERSEDED`, `HISTORICAL_ONLY`, or `UNKNOWN`.
- Name the exact latest completion/addendum messages that govern your lane and every earlier report they supersede. Give message/chat IDs, permalinks and timestamps when available; otherwise declare a message-byte `HOLD` and explain why.
- Separate: designed, source-recovered, normalized, code-implemented, locally tested, committed, pushed, CI-tested, runtime-installed, physically executed, measured, reviewed, and released.

### 2. Complete artifact and provenance ledger

For every input, output, package, workbook, CSV, JSON, schema, SQL migration, patch, source file, test, report, manifest, receipt, and generated export in your scope, provide:

- exact filename and canonical location or retrievable identifier;
- role: source evidence, authoritative input, normalized source, runtime code, test, generated view, report, or historical artifact;
- exact byte size and SHA-256 when available;
- archive member list/count, CRC/integrity result, and internal manifest relationship for containers;
- canonical/current, superseded, duplicate, derived, missing-byte, or historical status;
- upstream and downstream dependencies;
- whether the exact bytes are currently retrievable;
- the consequence if omitted, transformed, deduplicated, or regenerated.

Never invent an unavailable hash, size, count, path, destination, timestamp, result, or identifier. Use `UNKNOWN` with the reason.

Attach or expose exact terminal artifacts and manifests where possible. A prose summary alone is not an artifact recovery.

### 3. Semantic and functional inventory

Enumerate every capability and data concept you introduced or changed:

- functions/classes/modules/CLI commands/API routes, with signatures, inputs, outputs, invariants, units, failure modes, and dependencies;
- tables/views/columns/keys/enums/constraints/triggers/indexes and row counts;
- workbook sheets, named ranges, formulas, validations, formatting with semantic meaning, hidden sheets, comments, and blank-but-intentional evaluation fields;
- equations, algorithms, transforms, thresholds, scoring rules, gates, decision logic, and rounding/unit conventions;
- vocabulary/ontology additions, aliases, crosswalks, IDs, and mappings;
- test fixtures, negative cases, regression cases, expected results, and exact test counts;
- UI, reporting, or export behavior;
- tacit assumptions and known limitations.
- environment, runtime, OS/architecture, toolchain and package/lock versions; list secret **variable names only**, never credential values;
- intentional blanks, placeholders, deferred fields and the semantics their emptiness preserves;
- chat-only reasoning, rejected approaches, failed attempts and decisions that are not represented in an artifact.

For each item, propose a canonical destination in `perfume-chem`, but do not install or mutate it yet. Identify anything that must remain an immutable source record rather than becoming executable runtime truth.

### 4. Evidence and claim classification

Classify every material conclusion on **two independent axes**:

- epistemic evidence class: `MEASURED`, `SOURCE_VERIFIED`, `MODELED`, `HYPOTHESIS`, `SCREEN`, `PLANNED`, or `UNKNOWN`;
- workflow state: `COMPLETE`, `NOT_RUN`, `NOT_TESTED`, `HOLD`, `BLOCKED`, `SUPERSEDED`, or `NOT_APPLICABLE`.

Give the supporting artifact and exact location for each nontrivial claim. A workflow state such as `COMPLETE` does not upgrade its evidence class, and a `HOLD` does not describe what kind of evidence exists.

Preserve these hard boundaries:

- notes or descriptors are not molecules;
- material presence is not dose or ratio;
- modeled headspace/OAV/interaction is not measured perception, liking, safety, stability, release, or manufacturing readiness;
- ingredient count, cost, complexity score, or screen rank is not similarity or preference;
- designed formulas are not physical builds; physical builds are not bottle outcomes;
- software-gate success is not empirical qualification;
- missing evidence stays `UNKNOWN` or `HOLD` and must not be filled by inference.

### 5. Inventory, formula, and stock authority

- Treat `Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx` as current inventory authority unless a newer explicitly governing artifact is identified with exact bytes and provenance.
- Bind that authority to 199,635 bytes and SHA-256 `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`; a same-name file with different bytes is a conflict, not a substitute.
- Inventory constrains the build; it does not redefine the ideal target.
- Keep ideal target, inventory-constrained build, and physical bottle/measurement as separate objects.
- Treat planned Ambrettolide as design-available but physical-procurement pending.
- Identify every formula/material through stable IDs and `ExactStockRef`-style concentration/solvent/source/lot assumptions; report any implicit `1.0`, neat, density, dilution, unit, or availability fallback.
- Flag all formulas or computations needing V5 rebase, stock resolution, source-byte binding, or physical verification.

### 6. Conflicts, supersession, and integration risks

Apply this precedence while preserving every predecessor and conflict: newest lane-specific completion/closure/freeze/remediation/superseding receipt; then Inventory V5 for stock/build facts; then current protocol/complexity/strict-reverification controls; then exact synchronized CrossBrand/cutover sources; then research, interaction, floral, style and pilot materials; then newest target-specific workbook; then historical artifacts. A later timestamp does not override a different scope.

- List every contradiction with another chat, artifact, repository state, inventory version, schema version, or completion report.
- For each conflict, provide both sides, evidence, proposed precedence, and safe current disposition. Keep unresolved conflicts as `HOLD`.
- Identify parallel sources of truth, fail-open behavior, destructive migrations, silent coercions/defaults, lossy conversions, incompatible IDs/units, generated files mistaken for sources, and uncommitted/local-only code.
- Describe exactly what information, behavior, or evidentiary status would be lost under a naive copy/merge/import.
- Provide a chronological decision log, including rejected alternatives, failed attempts, reversals, and the evidence/rationale for each choice.

### 7. Installation proposal and verification

Provide a dependency-ordered, reversible installation proposal containing:

1. immutable source-byte ingestion;
2. hash/manifest verification;
3. supersession and conflict registration;
4. lossless normalization and stable-ID mapping;
5. schema/code/data migration order;
6. feature flags and read-only shadow mode where appropriate;
7. unit, schema, property, regression, migration, and round-trip tests;
8. exact-head CI requirements;
9. runtime/host qualification;
10. rollback plan and acceptance criteria.

Report historically executed commands as structured verification runs, including working directory, exact commit, environment/lock identity, input hashes, exit code, pass/fail/skip counts, result artifacts and timestamp. Report proposed commands separately and do not execute them for this request. State all remaining blockers, owners, required source bytes, and next actions.

### Required response files

Return both:

1. `LATEST_DETAILED_REPORT_<CHAT_ID>_2026-08-09.md` — complete human-readable report.
2. `LATEST_DETAILED_REPORT_<CHAT_ID>_2026-08-09.json` — machine-readable report conforming to `perfume_chem_chat_report.schema.json`.

Also return an exact artifact bundle or retrieval manifest if any terminal artifact is not already durably retrievable. End with an explicit attestation listing what is complete, what is preserved but inactive, what remains held, and whether any information/function/complexity is known to be absent from the handoff.

The collector will attach `perfume_chem_chat_report.schema.json` with this message. Every required inventory section must be exhaustive. Do not satisfy the contract with empty arrays. If a category is genuinely empty, record a specific zero-count explanation in the coverage section; the collector will reconcile declared counts, identifiers, references and evidence before accepting the report. JSON Schema validation alone is not acceptance.

## Collector acceptance rule

A chat is not considered collected merely because it replied. Collection is complete only when:

- the reply identifies terminal and superseded state;
- all claimed terminal artifacts have retrievable exact bytes or explicit byte holds;
- hashes/manifests and dependency relationships reconcile;
- capabilities, schemas, formulas, tests, and evidence levels are inventoried;
- unresolved contradictions are retained as conflicts/HOLDs;
- installation and rollback steps are reproducible;
- no modeled, planned, or software-only result is promoted to measured or released truth.
