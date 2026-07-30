# Build A Canonical Convergence Report

Date: 2026-07-30

Build: A — Canonical Convergence and Reconstruction Hardening

Decision: **PASS_WITH_SKIPS**

Laboratory Beta: **READY**

Scientific release: **BLOCKED**

## Authority and scope

This report is an independent reconciliation of the actual
`D:\chatbots\perfume-chem` working tree. Historical project and GLM reports were
used only as hypotheses. Acceptance is based on repository state, executable
tests, database constraints, reproducible artifacts, and the evidence listed
below.

The tested Build A source checkpoint is:

- branch: `codex/add-inventory-materials`
- A0 baseline commit: `2e46e4ce5795014e92924102c38c1358d7a9fdca`
- full-verifier source commit: `cbb0dbd9d1f2a0c5023adc35dd81da9902c77bd8`
- post-verifier documentation-consistency commit: `68f7024`
- committed Build A paths reviewed: 128
- full path list: `canonical_convergence_report.json`

The verifier ran against the authoritative dirty working tree. It is therefore
incorrect to treat the commit SHA alone as a restorable representation of the
tested state. At the report checkpoint the preserved workspace contained 105
tracked dirty paths, 505 untracked files, and no staged files. These were not
cleaned, reset, or silently absorbed into Build A commits.

## Recovery boundary

The pre-implementation state remains recoverable at:

`C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a2-slice1-preimplementation-recovery\perfume-chem-a0-20260729T194130Z`

The package contains path-preserving and independently hashed recovery media:

| Object | SHA-256 |
|---|---|
| committed repository bundle | `95A88496568B5C7382F03F251B9C5F9EBF306D682B059865CE6302E0C55560E7` |
| tracked binary patch | `C84B4AB871BC6E3F2112BA305EF39902AF19345E2575A26680BF9DD3FF506054` |
| tracked byte-exact overlay ZIP | `4A5F20232DFC63DEA597A0570185157C95FCA2270CBF5C65281EB77F63A47E0D` |
| all-untracked path-preserving ZIP | `F819DF4C4B421202255954DBE7380B3951C641BF4DBC1579D329BB634C2E7EB4` |
| local-only sensitive/ignored ZIP | `01BBC4F0D71F9EB0222F56B0BB471C048D8B5A995D894AD72B778434D721DB02` |

The bundle and archives were structurally verified. Sensitive archive contents
remain local-only and are not displayed or transmitted.

## Canonical architecture after convergence

The converged truth path is:

1. source evidence and evidence claims remain versioned records;
2. identity resolution and inventory availability are separate typed decisions;
3. an accepted target formula is immutable and distinct from a measurable build
   plan;
4. build-plan versions and inventory reservations are persisted before physical
   execution;
5. AI actors may propose actions but cannot confirm measurements;
6. confirmed actions commit append-only bottle events and inventory movements in
   one database transaction;
7. bottle and stock state are replayed projections, not editable authority;
8. analytical, sensory, regulatory, and release records retain independent
   claim-specific authority;
9. reports and Markdown are projections, never canonical records.

Canonical persisted models, repositories, and services live under
`backend/app/models`, `backend/app/repositories`, and `backend/app/services`.
The engine domain objects are typed calculation and replay projections. Legacy
interfaces are one-way adapters into canonical services and are guarded against
direct writes.

## Six original defect dispositions

| ID | Finding | Independent reproduction | Final disposition | Fix and executable contract |
|---|---|---|---|---|
| A1.1 | Diluent-aware concentration and category conservation | **REPRODUCED.** Inactive stock mass was assigned generically, producing a conservation gap and misclassifying ethanol or unknown diluent. | **FIXED.** Declared composition and diluent role now partition active, carrier, ethanol, water, other solvent, and unallocated mass conservatively. | `engine/units/concentration.py`, `engine/quantities.py`; `tests/test_a1_audit_contract_gaps.py`, `tests/test_a1_authoritative_contracts.py`, `tests/test_canonical_quantities.py` |
| A1.2 | Target-row preservation | **PARTIAL.** Several fields survived already, but the strict all-field round trip and unknown-field policy were not complete executable contracts. | **FIXED.** Accepted fields round-trip; strict mode rejects unknowns and permissive mode preserves versioned extensions. | `engine/target/formula.py`; authoritative target-row tests in `tests/test_a1_authoritative_contracts.py` |
| A1.3 | Twelve-axis anti-compression | **REPRODUCED.** The compatibility surface used booleans and did not make missing evidence independently authoritative as `UNKNOWN`. | **FIXED.** Twelve named axes use `MATCH`, `DIFFER`, or `UNKNOWN`; merge requires all conclusive matches and scoped equivalence is explicit. | `engine/reconstruction/anti_compression.py`; anti-compression tests in both A1 contract files |
| A1.4 | Chained correction replay | **REPRODUCED.** Missing-reference and cross-stream strictness were absent from the earlier compatibility behavior. | **FIXED.** Immutable chains reject missing/cross-stream references, cycles, conflicting retries, and stale sequences; latest valid correction wins with a trace to the original. | `engine/bottle/events.py`; A1 correction contracts plus 128 seeded chains and 32 seeded cycles in `tests/test_bottle_events.py` |
| A1.5 | Empty reconstruction inputs | **REPRODUCED.** Public entry points returned empty projections instead of the required stable pre-normalization domain error. | **FIXED.** Empty rosters, targets, ordered events, zero budgets, and zero denominators fail before mathematical normalization. | `engine/domain_errors.py` and reconstruction entry points; A1 empty-input contracts |
| A1.6 | Identity resolution versus stock availability | **REPRODUCED.** Earlier flat compatibility statuses conflated identity and stock state. | **FIXED.** Canonical mappings expose independent `IdentityResolutionStatus` and `InventoryMatchStatus`; legacy flat constants remain non-authoritative projections. | `engine/identity/resolver.py`, `engine/inventory/stock_model.py`; authoritative identity/inventory tests |

The untracked `docs/verification/a1_exit_gate.md` is preserved as historical
workspace material, but it is not the final authority: it reports obsolete
939-test and single-enum-gap conclusions. The contracts and completed A6
verifier supersede those statements.

## Independent diff review

The committed range `2e46e4c..68f7024` contains 128 paths:

| Area | Paths |
|---|---:|
| backend | 55 |
| docs | 19 |
| engine | 29 |
| scripts | 2 |
| tests | 23 |

Review results:

- every path is listed in the JSON companion report;
- no Build A changed file exceeds 1 MiB;
- seven tracked repository files exceed 5 MiB, but none changed in Build A;
- high-confidence scans found zero committed private-key markers or literal
  credential patterns;
- the legacy-write AST guard found zero direct legacy write violations;
- no forbidden shallow `cls(**filtered)` deserialization path remains;
- public legacy `/api/v1/lab/*` routes remain mounted and tested;
- versioned `/api/v1/lab/v2/*` planning, execution, science, replay, diff, and
  release-review routes are mounted and integration-tested;
- the migration chain is linear and every Build A revision has upgrade and
  downgrade logic:
  `20260716_0001 -> 20260717_0001 -> 20260730_0001 -> 0002 -> 0003 -> 0004`;
- migrations include the declared constraints and trigger-level invariants;
- generated and golden artifacts were not silently regenerated;
- the golden fixture SHA-256 remained
  `0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec`;
- stale A1 compatibility comments were corrected after review and the 39-test
  focused file passed.

No reviewed expected value was changed merely to match implementation output.
Inventory-dependent tests were reconciled to the actual current inventory
semantics while `inventory.txt` itself remained untouched. The current inventory
hash is `6cab4998523dfbd224cb8be7973d977a706d9fc56f8d1f0c84e31e806f509c66`
with 208 available entries. These inventory test reconciliations remain part of
the preserved dirty workspace and were not swept into Build A commits.

## Verification evidence

Canonical verifier report:
`verification_runs/a6-project-verification.json`

Report SHA-256:
`B4C2ECCAB4C4C4741EE85F739D9F585B9356354AB15EFA2A3A9C55DDBB939677`

| Gate | Result |
|---|---|
| direct full root suite | **1062 passed** in 92.09 s |
| engine truth-core shard | **189 passed** |
| engine data/knowledge shard | **225 passed** |
| engine gates/families shard | **580 passed** |
| engine legacy shard | **68 passed** |
| engine shard total | **1062 passed** |
| backend suite | **291 passed** |
| engine Ruff blocking slice | **PASS** |
| engine MyPy | **PASS**, 33 source files |
| backend Ruff | **PASS** |
| backend MyPy | **PASS**, 86 source files |
| scientific audit | **22 passed** |
| material validation | **79 passed** |
| knowledge rules | **76 passed** |
| golden formula regression | **13 passed** |
| golden API regression | **1 passed**, 8 deselected |
| package build | **PASS** |
| wheel smoke | **PASS** |
| formula artifact validation | **PASS** |
| required verifier checks | **19 passed, 0 failed** |
| Docker build/smoke | **SKIPPED**, optional and not requested by the canonical command |

The current `Y_LHomme_Luxe_30mL_EDT.md` artifact correctly remains
`QUARANTINED` and `STALE` with `release_authority=false`; a passing artifact
validator does not promote it.

## Protected database state

After the direct suite and again after the canonical verifier, the knowledge
database was restored byte-for-byte from the verified recovery candidate:

- `data/perfumery_kb.db` SHA-256:
  `5A779F9D6850345D72DE3C8265D4330C50DAC529968B38BC9B08720B5DA63FE1`
- read-only immutable SQLite `PRAGMA integrity_check`: `ok`
- `perfume_chem.db` SHA-256:
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
  (expected zero-byte canonical file)

## Known limitations and deprecated projections

- Full-engine Ruff cleanup outside the blocking truth-core slice remains legacy
  debt.
- `remaining_mass_g` assignments in the backend are compatibility projections
  performed after append-only movement writes; they are not stock authority.
- Engine-only single-batch transfer replay remains a limited projection; atomic
  cross-stream transfer authority is the backend transaction service.
- Solvent-matrix compatibility can be omitted in compatibility requests; strict
  mode requires it. Headspace is modeled rather than measured.
- Temporal evolution remains heuristic and is not calibrated to skin or blotter
  measurements.
- Longevity, sillage, receptor activation, emotion, and preference-fit claims
  remain unsupported or `UNKNOWN`.
- Composite-natural OAV is olfactory headspace evidence, not regulatory
  constituent composition.
- Docker was not exercised by this verifier run.
- The exact accepted state is the source checkpoint plus the preserved dirty
  overlay and verifier evidence, not a clean-checkout claim.

## Release and boundary decision

Build A satisfies its canonical-convergence gate:

- one persisted truth path is defined;
- legacy write paths are one-way and guarded;
- planning, execution, science, and inventory migrations are constrained and
  reversible;
- event replay, correction chains, rollback, concurrency, API, import/export,
  backup/restore, hashing, serialization, and negative claim gates are covered;
- all required verifier checks pass;
- protected databases are restored and verified;
- the recovery package is restorable and path-preserving;
- known limitations remain explicit.

Therefore Build A exits **PASS_WITH_SKIPS** and Build B may begin.

This decision authorizes Laboratory Beta operation only. Scientific release
remains **BLOCKED** because held-out sensory validation has not passed. No Build
A software result can substitute for Build B, C, or D evidence.
