# FC-1 BUNDLE RECONCILIATION + RESUME GATE

**Plan ID:** `PC-FC1-RECON-20260806-R1`  
**Mode:** metadata and artifact reconciliation only  
**Formula authority:** none  
**Canonical `perfume-chem` integration:** blocked  
**Phase G:** not authorized

## 0. Verified starting facts

The authoritative external bundle is:

```text
FLORAL_COVERAGE_FC1_READINESS_BUNDLE.zip
size: 24,308 bytes
SHA-256: e106030d546a58f26f9a68ef84ec9102a5f4e1e8635f81611f05f1e9b591d9e1
members: 23
```

The bundle's non-self-referential manifest declares 21 governed artifacts. The two additional ZIP members are the manifest itself and its external SHA receipt, so `21 + 2 = 23` is consistent.

The mounted local run contains 15 artifacts that are also present in the bundle. All 15 are byte-identical. There is no content divergence and no task-ledger divergence.

The bundle adds eight members not unpacked beside the local run:

- `ADVISORY_SOURCE_CANDIDATE_QUEUE.json`
- `FLORAL_COVERAGE_FC1_EXTERNAL_SHA256.json`
- `JASMINE_DEMO_REPORT.json`
- `JASMINE_DEMO_REPORT.md`
- `WORKER_TASK_LEDGER.jsonl`
- `logs/family_listing.log`
- `logs/jasmine_cli.log`
- `logs/unit_tests.log`

The local directory also contains the separate bundle receipt:

- `FLORAL_COVERAGE_FC1_READINESS_BUNDLE.sha256.txt`

The historical task graph is already consistent in both the local and bundle copies:

```text
12 tasks = 9 COMPLETE + 2 HOLD + 1 BLOCKED
```

Do not state that the local ledger had six tasks.

## 1. Preserve three strata

Create a new directory:

```text
runs/Floral_Coverage_FC1_Reconciliation_20260806/
```

Treat the records as three immutable strata:

### A. External execution stratum

The external bundle is authoritative for what happened during the external FC-1 execution.

### B. Local execution stratum

The existing local run is authoritative for artifacts and environment observations actually produced locally.

### C. Reconciliation stratum

All new comparison, current-capability, and effective-state artifacts are written only to the new reconciliation directory.

Do not overwrite either parent stratum.

## 2. Verify and extract the external bundle

1. Recalculate the ZIP size and SHA-256.
2. Confirm the expected SHA exactly.
3. If a `(1)` copy exists, classify it as a byte-identical duplicate only after an independent size/hash check.
4. Extract into:

```text
runs/Floral_Coverage_FC1_Reconciliation_20260806/
  bundle_extracted/
    e106030d546a58f26f9a68ef84ec9102a5f4e1e8635f81611f05f1e9b591d9e1/
```

5. Reject path traversal, duplicate path collisions, undeclared members, missing members, size mismatches, and hash mismatches.
6. Verify the original manifest SHA against `FLORAL_COVERAGE_FC1_EXTERNAL_SHA256.json`.
7. Preserve the original manifest and external SHA receipt unchanged.

Any failure produces:

```text
EXTERNAL BUNDLE QUARANTINED
RECONCILIATION STOPPED
PARENT STRATA UNCHANGED
```

## 3. Create the reconciliation index

Create:

- `FLORAL_COVERAGE_FC1_RECONCILIATION_INDEX.json`
- `FLORAL_COVERAGE_FC1_RECONCILIATION_INDEX.csv`
- `FLORAL_COVERAGE_FC1_RECONCILIATION_REPORT.md`

For each logical artifact, record:

```text
logical_artifact_id
bundle_path
bundle_size
bundle_sha256
local_path
local_size
local_sha256
relationship
historical_authority
current_authority
state_difference
supersession
current_action
notes
```

Allowed relationships:

```text
IDENTICAL
BUNDLE_ONLY
LOCAL_ONLY
CONTENT_DIVERGENCE
STATE_DIVERGENCE
SUPERSEDED_BY_RECONCILIATION
```

Expected observed result for the currently mounted artifacts:

```text
15 IDENTICAL shared members
8 BUNDLE_ONLY members
1 LOCAL_ONLY bundle SHA text receipt
0 CONTENT_DIVERGENCE
```

The independently computed index remains authoritative.

## 4. Keep historical, effective, and reconciliation task graphs separate

### 4.1 Historical graph

Verify and preserve:

```text
12 = 9 COMPLETE + 2 HOLD + 1 BLOCKED
```

Create:

- `FLORAL_COVERAGE_FC1_HISTORICAL_TASK_GRAPH_CHECK.json`

This describes only the historical external run.

### 4.2 Effective FC-1 state projection

Create:

- `FLORAL_COVERAGE_FC1_EFFECTIVE_STATE_PROJECTION.json`

This maps each original FC1 task to its current effective state without altering the historical ledger.

When Cheapluna preflight passes, the historical `FC1-011 BLOCKED` may be shown as:

```text
historical_state: BLOCKED
effective_state: COMPLETE
superseded_by: FC1-RECON-CHEAPLUNA-PREFLIGHT
```

When preflight fails, effective state remains BLOCKED.

### 4.3 Reconciliation task graph

Create a new task ledger for the reconciliation work itself:

- `FLORAL_COVERAGE_FC1_RECON_TASK_LEDGER.json`
- `FLORAL_COVERAGE_FC1_RECON_TASK_LEDGER.csv`
- `FLORAL_COVERAGE_FC1_RECON_ARITHMETIC_CHECK.json`

Do not force the reconciliation graph to have 12 tasks. Derive its count from its own explicit task rows.

## 5. Re-evaluate the upstream resume gate

Perform one bounded exact-name and path-aware search for:

1. `Counterbrand_Input_File_Manifest.xlsx`
2. `extracted_formulas/All_Formula_Rows.jsonl`
3. `Counterbrand_Target_Version_Matrix.xlsx`
4. `Counterbrand_Formula_Lineage_Map.xlsx`
5. `Counterbrand_Governing_Formula_Index.xlsx`

Record search roots, candidates, hashes, exact-match status, authority status, and rejection reasons.

If all five remain absent:

```text
CLAIM REGISTER: HOLD — ESTATE MANIFEST NOT READY
READINESS QUEUE: HOLD — NORMALIZED FORMULA LEDGER NOT READY
RESUME GATE: CLOSED
```

Resume point remains `FC1-009 CLAIM_REGISTER` after all five are hash-locked.

## 6. Record non-substitutes

Create:

- `FLORAL_COVERAGE_FC1_NON_SUBSTITUTION_RECORD.json`

If discovered, explicitly reject these as substitutes:

```text
CrossBrand_120_All_Formula_Rows.csv
Modern_Violet_*_All_Formula_Rows.csv
```

They differ from the required JSONL ledger in format, scope, canonicalization, extraction lineage, path, and authority. Using them would create a second formula-estate truth path.

## 7. Reconcile Cheapluna conditionally

Do not predeclare Cheapluna available merely because a prior report says so.

OpenCode must independently verify:

```text
exact cheapluna-drain.mjs path
script SHA-256
exact test command
observed 19/19 receipt
receipt SHA-256
budget envelope
provider/model route
event-log destination
cost-ledger destination
cache path and state
write-isolation boundary
```

Create:

- `CHEAPLUNA_ADVISORY_PREFLIGHT.json`
- `CHEAPLUNA_ADVISORY_PREFLIGHT.md`
- `ADVISORY_SOURCE_CANDIDATE_QUEUE.json`

When every preflight item passes and no advisory query is required:

```text
CHEAPLUNA PREFLIGHT VERIFIED
ADVISORY SOURCE QUEUE MATERIALIZED EMPTY
NO CANONICAL CLAIMS ADDED
```

When any item fails:

```text
CHEAPLUNA ADVISORY LANE BLOCKED
```

Cheapluna may never write to the claim register, readiness queue, formula ledger, evidence ledger, governing target records, or canonical task ledgers.

## 8. Preserve claim and readiness holds

Verify, but do not populate or rewrite, the bundle's zero-record ledgers:

```text
FLORAL_COVERAGE_CLAIM_REGISTER.json
state: HOLD — ESTATE MANIFEST NOT READY
records: 0

FLORAL_COVERAGE_READINESS_QUEUE.json
state: HOLD — NORMALIZED FORMULA LEDGER NOT READY
records: 0
```

Do not populate them from note lists, scattered formula books, CrossBrand CSVs, model memory, original-design files, or advisory architecture.

## 9. Verify execution evidence

Verify directly from the bundle artifacts:

```text
unit tests: 10/10 PASS
family listing: PASS
Jasmine CLI: PASS
formula mutations: 0
physical results: 0
similarity passes: 0
Phase G authorized: false
```

Use observed logs and records, not literal booleans.

## 10. Preserve two terminal states

### 10.1 Historical external terminal state

Keep the original terminal-state JSON unchanged.

### 10.2 Current reconciled terminal state

Create:

- `FLORAL_COVERAGE_FC1_RECONCILED_TERMINAL_STATE.json`

When Cheapluna preflight passes but the five estate inputs remain absent:

```text
FC-1 VALIDATED EXTERNAL CANDIDATE
CLAIM REGISTER: HOLD — ESTATE MANIFEST NOT READY
READINESS QUEUE: HOLD — NORMALIZED FORMULA LEDGER NOT READY
CHEAPLUNA PREFLIGHT VERIFIED
ADVISORY SOURCE QUEUE MATERIALIZED EMPTY
CANONICAL PERFUME-CHEM INTEGRATION BLOCKED
NO FORMULA AUTHORITY
PHYSICAL TEST REQUIRED
```

When Cheapluna preflight fails, replace the two Cheapluna lines with:

```text
CHEAPLUNA ADVISORY LANE BLOCKED
```

## 11. Reconciliation manifest and bundle

Do not update the original FC-1 manifest or external SHA receipt.

Create:

- `FLORAL_COVERAGE_FC1_RECONCILIATION_MANIFEST.json`
- `FLORAL_COVERAGE_FC1_RECONCILIATION_EXTERNAL_SHA256.json`
- `FLORAL_COVERAGE_FC1_RECONCILIATION_BUNDLE.zip`

The reconciliation manifest must reference:

```text
parent external bundle SHA
parent external manifest SHA
parent local manifest SHA
reconciliation index SHA
historical task-graph check SHA
effective state projection SHA
reconciliation task ledger SHA
reconciliation arithmetic SHA
upstream resume-gate check SHA
non-substitution record SHA
Cheapluna preflight SHA
advisory queue SHA
reconciled terminal-state SHA
all new reconciliation artifacts
```

The manifest excludes its own hash. Seal it with the external SHA receipt.

## 12. Source-authority and scope boundary

This reconciliation pass is governed by the latest FC-1 terminal and addendum records at this exact scope.

The newly supplied reconstruction protocol, meaningful-complexity audit, interaction atlas, architecture lattice, literature ledger, and engine-qualification package are preserved as future floral-program and verification inputs. They do not alter the historical FC-1 execution, populate the held claim/readiness ledgers, or authorize canonical integration during this pass.

## 13. Non-negotiable boundaries

```text
No perfume-chem installation
No engine/florals changes
No delegation/orchestration changes
No formula changes
No inventory changes
No gate changes
No note-to-material creation
No coverage-to-similarity conversion
No commercial molecular-presence claim
No formula-state promotion
No empirical-state promotion
No physical-result creation
No safety or stability claim
No Phase G authorization
```

The main Counterbrand Formula Estate Audit continues independently.

## 14. Final response requirements

Report:

- bundle size and SHA verification;
- member count and manifest-count explanation;
- identical, bundle-only, local-only, and divergent counts;
- historical task graph;
- effective FC-1 state projection;
- reconciliation task-graph arithmetic;
- five-artifact resume-gate result;
- Cheapluna preflight result;
- claim/readiness record counts;
- formula and physical mutation counts;
- current reconciled terminal state;
- reconciliation output directory;
- manifest, SHA receipt, bundle, and handoff paths.

Do not merely say `done`.
