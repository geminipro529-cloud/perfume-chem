# Build B4 Knowledge-Rule Compiler Design

## Decision

Build B4 adds a separate append-only laboratory rule-authority layer and a
deterministic legacy-corpus adapter. It does not upgrade, rewrite, or delete
the current JSON corpus, the protected knowledge database, the mutable
`PairingRule`/`SynergyRule` compatibility models, or existing optimizer
consumers.

No legacy record becomes authoritative, blocking, or numerical merely because
the compiler can parse it. The migration imports zero groups, rules,
contradictions, support records, or compilation runs.

## Current-state evidence

The source corpus frozen for B4 inventory contains:

| Source | Shape | Records | SHA-256 |
|---|---|---:|---|
| `theory_rules.json` | object | 5 | `4237619F...3B90` |
| `pairing_rules.json` | array | 2,408 | `FC4370B8...F8D1` |
| `pairing_rules_discovered.json` | array | 915 | `2DD23D49...044` |
| `synergy_matrix.json` | array | 53 | `7B194C2F...B9D` |

The total is 3,381 source records. The protected legacy knowledge database has
3,602 `material_interactions` rows. It includes 162 `test_dup` rows, 81
`test` rows, three `AGENTS.md F11` rows, 241 exact duplicate rows, and 743
material-pair/type keys with more than one record. Those rows remain evidence
of legacy state, not a source of authority.

The existing literature normalizer can default a synergy/conflict row to
`hard` even when metadata was missing. That behavior is forbidden in B4 and
will not be reused. Existing generic-label detection and exact material
resolution may inform inventory diagnostics, but neither may decide canonical
authority.

Because resolver state changes inventory diagnostics, the B4 regression also
freezes the 454 raw-label resolution outcomes used to generate its baseline.
That snapshot is a test input only, is explicitly non-authoritative, and never
becomes a runtime identity registry. Updating it requires an intentional
baseline review rather than an implicit dependency on mutable resolver state.

## Canonical model

### Versioned groups

`lab_rule_groups` stores immutable group versions:

- stable group key and positive version;
- label and definition;
- exact B1 source-document version, extraction, and locator when the group is
  evidence-backed;
- review state, status, and content hash; and
- optional superseded-group reference.

`lab_rule_group_members` stores ordered members. A member is either one exact
identity-scope digest or one nested group version, never a free-text material
name. Cyclic group membership is rejected by the service.

### Rules

`lab_knowledge_rules` stores one immutable rule version with:

- stable rule key and positive version;
- subject and object endpoint kind: `EXACT_IDENTITY`, `GROUP`,
  `GENERIC_PROSE`, or `UNRESOLVED`;
- exact identity digest, group-version reference, or raw label according to
  endpoint kind;
- one explicit relation from the frozen B4 vocabulary;
- directionality;
- canonical matrix/product, dose/concentration, temporal, expected-effect,
  attribute, and rationale payloads;
- exact B1 source-document version, extraction, and locator when available;
- evidence class, uncertainty, review state, and rule status;
- runtime role: `EXPLANATORY`, `ADVISORY`, or `BLOCKING`;
- optional numerical-model reference;
- raw source path, JSON pointer, payload digest, and compiler diagnostics; and
- optional superseded-rule reference.

The relation vocabulary is:

`REINFORCES`, `MASKS`, `SUPPRESSES`, `SYNERGIZES`, `ADDS`, `EXTENDS`,
`BRIDGES`, `BRIGHTENS`, `ROUNDS`, `DRIES`, `WARMS`, `COOLS`, `DIFFUSES`,
`TEMPORALLY_HANDS_OFF`, `FUNCTIONALLY_SUBSTITUTES`, `NON_EQUIVALENT`,
`MATRIX_DEPENDENT_INTERACTION`, and `SAFETY_CONTRIBUTION`.

Rule status is one of `AUTHORITATIVE`, `SUPPORTED`, `ADVISORY`,
`SPECULATIVE`, `INVALID`, or `SUPERSEDED`.

### Contradictions and support

`lab_rule_contradictions` links two different rule versions with a typed
reason and blocking flag. Both directions cannot be inserted independently;
the service stores a canonical ordered pair.

`lab_rule_support_evidence` links a rule to a B2 property observation, a lab
observation, a lab experiment, a test artifact, or a versioned numerical
model. It stores the exact matrix and dose-domain hashes used by that support.

`lab_rule_compilation_runs` records the compiler version, four source hashes,
source and compiled counts, invalid-exact count, duplicate/cycle/orphan/
generic counts, baseline ceiling, pass/fail result, and a deterministic report
hash.

All six tables are append-only and included in migration downgrade,
backup/restore head checks, and model/migration parity tests.

## Endpoint and authority rules

Endpoint shape is fail-closed:

- exact identity requires a 64-character identity-scope digest and forbids a
  group reference;
- group requires an existing immutable group version and forbids an identity
  digest;
- generic prose or unresolved input retains its raw label and cannot claim an
  exact identity or group.

Generic labels never auto-create groups. A string such as `rose`, `orange`,
`woods`, `musks`, or `florals` resolves to a group only when the caller
supplies an explicit reviewed group version. Parenthetical examples do not
convert a generic label into exact endpoints.

Only an `AUTHORITATIVE` rule may be `BLOCKING`. Creating that combination
requires:

- exact or explicit-group endpoints;
- accepted B1 source and extraction with exact locator;
- declared matrix/product, dose, and temporal domains;
- explicit uncertainty and approved review state;
- no unresolved blocking contradiction; and
- supporting evidence appropriate to the claimed role.

`SUPPORTED`, `ADVISORY`, `SPECULATIVE`, `INVALID`, and `SUPERSEDED` rules are
never blocking. Generic prose is explanatory or advisory only. Invalid and
superseded rules cannot be returned as active recommendations.

## Numerical interaction boundary

A numerical model reference is rejected unless controlled support evidence:

- names the exact subject/object scope;
- uses a declared matrix and dose range matching the rule;
- links to a versioned experiment or observation set;
- records test/model version and uncertainty; and
- has an approved review state.

Legacy `magnitude`, `ratio`, `2-3x projection`, and similar text remain raw
legacy payload. They do not become numerical rule parameters.

## Deterministic compiler

The compiler accepts explicit identity and group resolutions plus raw
candidates. It never reaches into mutable global registries while deciding
authority.

The full-corpus regression supplies the committed non-authoritative resolution
snapshot as an explicit input. This makes the two compilation runs
reproducible even when unrelated working-tree resolver code differs.

Diagnostics have stable ordering and codes for:

- malformed record;
- missing or weak source;
- missing exact locator;
- unresolved exact identity;
- generic prose;
- missing group definition;
- unsupported relation/generalization;
- invalid unit or dose domain;
- missing matrix;
- duplicate rule or key;
- contradiction;
- directed cycle;
- orphan reference;
- numerical claim without controlled evidence; and
- authority or runtime-role promotion rejected.

Duplicate candidates are retained as inventory evidence but only one
deterministic representative may compile as active. No duplicate is silently
declared superseded.

Compilation output includes a recommendation projection exposing rule status,
source, locator, matrix/product, dose, temporal scope, uncertainty,
contradictions, and runtime role. It contains no formula mutation command.

## Legacy corpus adapter and CI baseline

The adapter inventories every one of the 3,381 frozen source records with a
stable source path and JSON pointer. It:

- treats the five theory records as explanatory/advisory prose;
- preserves legacy material labels and source strings;
- never reuses the legacy `hard` determinism override;
- strips no numeric claims from raw evidence but promotes none;
- separates generic prose from unresolved exact claims;
- emits duplicate, contradiction, cycle, and orphan diagnostics; and
- returns candidate records without database writes.

A checked fixture records source hashes, record counts, and the compiler's
invalid-exact count. CI recompiles the same source set and fails if:

- a source hash changes without an explicit baseline review;
- a source record disappears without review;
- the invalid-exact count increases; or
- any generic/advisory record becomes blocking or numerical.

The protected knowledge database is inventoried separately. Its test-sourced
and duplicate rows are reported but not copied into canonical tables.

## Legacy coexistence

`backend/app/models/knowledge_graph.py`, `engine/knowledge_base.py`,
`engine/knowledge/literature_rules.py`, `engine/optimizer/models.py`, and
their JSON/SQLite consumers remain compatibility projections. They have no B4
authority. Existing optimizer synergy output is a textual legacy suggestion,
not an automatic formula mutation; B4 does not expand its authority.

B9 will decide and test production API/runtime routing. Until then the B4
service is the only canonical rule authority and has no production consumer.

## Rejected alternatives

1. Updating the existing `PairingRule` and `SynergyRule` tables was rejected:
   they are mutable, have weak source strings, nullable identity links, and no
   matrix, dose, uncertainty, contradiction, or review contract.
2. Rebuilding the protected knowledge database was rejected: it would mutate
   baseline evidence and could erase test contamination or duplicates needed
   for reconciliation.
3. Importing all 3,381 records as advisory rows in the migration was rejected:
   Alembic must not depend on mutable corpus files, and parseability is not
   authority.
4. Expanding parenthetical examples into exact material pairs was rejected:
   a generic taxonomy label is not equivalent to its examples.

## B4 exit gate

B4 passes only when tests prove:

- exact endpoints resolve only to canonical identity digests or explicit
  reviewed group versions;
- generic prose never becomes an exact endpoint, blocking rule, numerical
  model, or formula mutation;
- invalid, advisory, explanatory, blocking, and superseded behavior is
  separated;
- every recommendation projection exposes status and full applicable scope;
- contradictions, duplicates, cycles, and orphan references remain visible;
- the 3,381-record adapter inventory is deterministic and source-hash bound;
- invalid exact rules do not increase above the frozen baseline;
- model, migration, append-only, downgrade/re-upgrade, and backup/restore
  tests pass; and
- no legacy data or protected database is modified or promoted.
