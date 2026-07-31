# Build B8 Prioritized Scientific-Data Backfill Design

## Decision

Build B8 adds an append-only campaign snapshot over the canonical B1-B7
authority graph. It does not copy legacy YAML/JSON values into authority
tables, infer active formula status from filenames, or turn a planning rank
into scientific evidence.

Each campaign freezes:

1. the exact materials in scope;
2. eight separate decision-value signals and their source records;
3. a deterministic lexicographic priority order;
4. one normalized row for every required scientific-data gap;
5. exact B7 claim-authority links for resolved gaps; and
6. stratified dashboard cells with explicit counts and denominators.

No campaign stores or returns one overall coverage percentage. A priority rank
controls research order only. It cannot promote a claim, mutate a scientific
value, or authorize release.

This design follows the master prompt, the live repository at
`3c160e3266a9288791d8680e23145903976bc2d8`, the B0 scientific-truth
inventory, the implemented B1-B7 authority graph, and the bounded DeepLuna
Fast inventory audit `DS-30ef482e3b3a9bd2152c84b28e1c07f5`.
DeepLuna was advisory; Sol selected the architecture and retains scientific,
security, provenance, scope, and final acceptance authority.

## Recovery and preservation gate

Before this design changed the repository, the complete non-runtime dirty and
untracked state plus all existing shared B8 targets was archived at:

`D:\.backups\perfume-chem\build-b8-prewrite-20260731T081641+0700.tar`

The path-preserving archive contains 402 files plus its manifest and
absent-planned-path list, is 97,180,160 bytes, and has SHA-256
`e6e6ce1ece19c0cf698c77b21a32d12c641f4af14cb8c082610f83f2e7d7ff4f`.
It was extracted to a separate verification directory and every restored file
was re-hashed successfully. Live `.deepluna-home/` and `.cheapluna-home/`
scheduler/runtime trees were excluded because they contain volatile and
potentially secret-bearing state, not implementation work.

## Repository findings that constrain B8

The B0 baseline inventories 1,262 material rows and 23,869 property cells.
It classifies 20,949 cells as `UNKNOWN`, 1,987 as
`UNATTRIBUTED_LEGACY`, and 505 as `LEGACY_HEURISTIC`. Those labels are
historical inventory classifications, not B1-B7 authority.

The current inventory parser reports:

- 232 raw stock entries;
- 216 normalized unique entries;
- 211 unique fragrance materials when unavailable entries are retained;
- 208 owned unique fragrance materials; and
- 16 duplicate canonical entries.

Of the 208 owned unique fragrance materials, 196 map to a B0 subject using the
existing alias-aware normalizer and 12 remain unmatched. The matched rows
contain 4,048 legacy property cells, all with review state
`LEGACY_UNREVIEWED`. Therefore the current-workspace baseline has zero values
that B8 may call promoted merely because they are non-null or have a familiar
source label.

`LabStockSolution`, `LabFormulaVersion`, `LabFormulaComponent`, B3 OAV
assessments, B4 rules, B5 analytical sequences, B6 regulatory/composition
records, and `LabPrediction` provide potential priority signals. However,
`LabFormulaVersion` has no canonical active/shipped/reference lifecycle
field. B8 must preserve that status as an explicit reviewed operational
declaration or report it `UNKNOWN`; formula filenames and prose do not prove
status.

## Considered approaches

### Static repository report only

This could rank the current `inventory.txt` and B0 inventory quickly.
Rejected as the authority design because it cannot provide database foreign
keys, immutable campaign history, exact B7 resolution links, or a reusable B9
API surface. A static report remains useful as a B8 verification projection.

### Live computed view only

This would query the latest B1-B7 rows on demand. Rejected because results
could change between calls, operational formula declarations would not be
frozen, and a later result could not be reconstructed from the exact inputs
used at the time.

### Append-only campaign snapshot

Selected. It combines reproducible planning with exact upstream links,
preserves unknowns, lets B9 expose stable dashboard records, and keeps all
scientific authority in B1-B7.

## Schema

Migration `20260731_0012` adds five empty append-only tables and performs no
legacy backfill.

### `lab_backfill_campaign_versions`

One immutable campaign version records:

- a stable campaign ID, positive version number, and optional latest parent;
- name, purpose, as-of UTC time, reviewer pseudonym, and review time;
- code-owned priority-policy version, full policy snapshot, and SHA-256;
- input snapshot SHA-256;
- exact counts for materials, signals, gaps, and dashboard cells;
- explicit counts for exact, scoped, weak, conflicted, unknown, missing, and
  not-applicable gap states;
- content and parent SHA-256 values; and
- a permanently false `release_authority` flag.

A revision must use the latest parent. Its stable campaign ID and policy
identity remain unchanged. A new scope starts a new campaign.

### `lab_backfill_material_priorities`

One immutable row per campaign/material records:

- material ID;
- deterministic one-based rank;
- primary priority class;
- the complete eight-dimension signal vector;
- a canonical lexicographic rank key and SHA-256;
- critical and total unresolved gap counts;
- exact source-reference hashes; and
- content SHA-256.

Ranks are unique and contiguous within the campaign. Material IDs are unique
within the campaign.

### `lab_backfill_priority_signal_links`

Each signal link has exactly one typed upstream reference:

- current inventory -> `lab_stock_solutions`;
- active/shipped/reference formula or high-dose structure ->
  `lab_formula_components`;
- potent trace -> `lab_oav_assessments`;
- family driver -> `lab_knowledge_rules`;
- regulatory driver -> `lab_regulatory_snapshot_versions`;
- analytical standard -> `lab_analytical_sequence_entries`;
- natural constituent -> `lab_regulatory_composition_entries`; or
- model sensitivity -> `lab_predictions`.

The row stores signal type, evidence class, exact source hash, normalized
signal value, applicability/limitation payloads, reviewer provenance where an
operational formula status is declared, and content SHA-256.

The service derives scientific and database facts from the upstream row.
Caller JSON cannot change a source hash, turn a failed/unknown B3/B6 record
into a positive signal, or make a model-derived signal measured. An explicit
active/shipped/reference designation remains a `LOCAL_RECORD` planning fact
and never scientific authority.

### `lab_backfill_gap_items`

One immutable row per campaign/material/requirement records one of:

- `MISSING`
- `UNKNOWN`
- `WEAK`
- `CONFLICTED`
- `ACCEPTED_SCOPED`
- `ACCEPTED_EXACT`
- `NOT_APPLICABLE`

The required data classes are:

1. `EXACT_IDENTITY`
2. `GRADE_IDENTITY`
3. `MOLECULAR_WEIGHT`
4. `DENSITY`
5. `VAPOR_PRESSURE`
6. `CONTEXTUAL_THRESHOLD`
7. `SAFETY_DOCUMENTATION`
8. `RETENTION_INDEX`
9. `ANALYTICAL_REFERENCE`
10. `NATURAL_LOT_COMPOSITION`

Every row preserves evidence class, exact applicability scope, conflict and
missing-requirement details, source references, and content SHA-256.

`ACCEPTED_EXACT` and `ACCEPTED_SCOPED` require an exact foreign key to
`lab_claim_authority_versions`. The service reconstructs that B7 decision,
checks its hashes, claim type, subject, identity/condition scope, and permitted
decision, and verifies that the linked claim satisfies the gap requirement.
All other states must have no B7 promotion link.

### `lab_backfill_dashboard_cells`

Dashboard cells are normalized rather than flattened into a confidence score.
The required dimensions are:

- `EVIDENCE_CLASS`
- `PROPERTY`
- `CURRENT_INVENTORY`
- `ACTIVE_FORMULA`
- `CHEMICAL_FAMILY`
- `REGULATORY_IMPACT`
- `MODEL_SENSITIVITY`

Each cell records a dimension key, material count, requirement denominator,
and separate exact, scoped, weak, conflicted, unknown, missing, and
not-applicable counts. Counts must reconcile to the denominator. `OVERALL`,
`TOTAL_CONFIDENCE`, `COVERAGE_SCORE`, and equivalent aggregate keys are
rejected.

## Priority policy

B8 uses a code-owned, content-hashed policy. The priority vector follows the
master prompt in strict order:

1. current physical inventory;
2. active or shipped formula;
3. high-dose structural use;
4. very potent trace use;
5. regulatory or family-gate impact;
6. analytical-standard use;
7. natural-constituent use; and
8. model sensitivity.

The sort is lexicographic, not a weighted sum. Every dimension remains visible
in the persisted vector. Within an otherwise equal vector, critical unresolved
gap count, total unresolved gap count, canonical material name, and material
ID provide deterministic tie breaks.

Known values rank ahead of unknown values only inside their own dimension.
An unknown later dimension cannot erase a positive earlier dimension, and a
large model-sensitivity number cannot outrank current inventory or an active
formula. No rank is interpreted as evidence quality.

Signal rules are deliberately narrow:

- current inventory requires a stock row with a positive reconstructable
  balance;
- active/shipped/reference formula status requires a reviewed operational
  declaration bound to an exact formula component;
- high dose uses active material mass share derived from formula component,
  stock active fraction, and complete formula totals;
- potent trace uses only a strict, context-compatible B3 OAV assessment;
- regulatory and family impact use exact B6 and approved B4 rows;
- analytical-standard status uses an exact B5 sequence-entry role;
- natural-constituent status uses an exact B6 composition entry and preserves
  profile completeness; and
- model sensitivity requires a versioned prediction record, bounded normalized
  sensitivity, model identity, and explicit `MODEL_ESTIMATED` evidence class.

Missing prerequisites produce an unknown signal plus a prioritized gap. They
are never replaced with legacy constants.

## Campaign creation and reconstruction

The service creates a campaign in one transaction:

1. validate campaign metadata and latest-parent lineage;
2. load the code-owned policy and hash it;
3. resolve every material and typed signal source;
4. derive and canonicalize each signal while preserving evidence class and
   limitations;
5. reconstruct every proposed B7 resolution link;
6. classify all ten data requirements for every material;
7. compute the strict lexicographic ranks;
8. build every required dashboard dimension from normalized rows;
9. verify count reconciliation and reject aggregate-score fields;
10. hash the complete input snapshot, rows, and campaign; and
11. persist the campaign and all child rows atomically.

Reconstruction reloads all children, re-resolves typed upstream records and B7
claims, recomputes ranks and dashboard cells, and verifies every hash. A
changed upstream row is not possible for append-only B1-B7 records; a missing
or corrupted link fails reconstruction.

## Current-workspace projection

A deterministic repository script will project `inventory.txt` against the
frozen B0 scientific-truth inventory without writing to a database. It reports:

- raw, normalized, owned, matched, and unmatched inventory counts;
- per-property and per-evidence-class gap counts;
- current-inventory strata;
- blocking-gate impact;
- explicit `UNKNOWN` cells for active formula, chemical family, or model
  sensitivity when the frozen inputs cannot prove them; and
- no overall coverage percentage.

This projection is a planning input and verification artifact. It cannot
create B1-B7 rows or mark a legacy value accepted.

## Compatibility and boundaries

- B1-B7 remain the only scientific authority stores.
- Existing legacy YAML, JSON, SQLite, and formula Markdown remain readable and
  unchanged.
- B8 does not migrate any protected database in place.
- B8 does not perform web research implicitly. New values enter through the B1
  source/extraction and B2-B7 review path before a B8 gap can resolve.
- B8 does not add public API/UI routes; that is B9.
- B8 does not authorize formula release, safety certification, legal
  compliance, sensory similarity, or model validity.

## Verification

The B8 gate requires:

- schema tests for all five tables, enums, checks, indexes, foreign keys,
  uniqueness, hashes, and append-only triggers;
- migration tests for prior-head upgrade, zero backfill, current head,
  downgrade/re-upgrade, and model parity;
- policy tests proving exactly eight ordered signal dimensions and ten gap
  requirements;
- deterministic rank tests proving strict lexicographic priority and stable
  tie breaks;
- negative tests for caller-inflated inventory, formula, B3/B6, analytical,
  natural, and model signals;
- negative tests proving legacy/unreviewed values cannot resolve a gap;
- exact and scoped B7 resolution tests with subject, claim-type, identity,
  condition, and hash mismatch cases;
- stale campaign parent and immutable-scope tests;
- dashboard reconciliation and aggregate-score rejection tests;
- atomic rollback tests;
- reconstruction and content-hash determinism;
- current-workspace projection tests;
- A2/B1-B8 compatibility, migration, and backup/restore tests;
- Ruff and scoped mypy;
- protected-database hash and read-only integrity checks; and
- a final bounded DeepLuna Fast audit followed by Sol's independent
  reproduction.

## B8 exit gate

B8 passes only when every `ACCEPTED_EXACT` or `ACCEPTED_SCOPED` gap
reconstructs through an accepted, scope-compatible B7 authority record; every
remaining gap is explicit and deterministically prioritized; all seven
required dashboard dimensions preserve separate evidence classes and gap
states; and no overall coverage score or scientific-release claim is emitted.
