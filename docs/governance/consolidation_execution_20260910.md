# Local worktree consolidation — completion handoff

**Consolidation complete for the captured cutoff; release remains HOLD.**

This is the user-selected preservation-and-reconciliation finish line, not a
claim that every preserved feature has been implemented, activated, or released.

## Working repository and local commits

- Repository: `D:/chatbots/perfume-chem-integration-20260909`
- Branch: `codex/integration-20260909`
- `8414de16`: consolidated inventory, exact receipts, Deep Plane diagnostics,
  registry transport/overlay repairs, standalone evidence primitives, and explicit
  concentration basis-plus-carrier parsing, with associated tests and provenance.
- `5ba148fd`: remaining source variants preserved as inert candidates, complete
  source accounting, candidate isolation tests, and full-verifier test coverage.
- A final documentation commit contains this handoff and the acceptance record.

No merge, push, publication, live database migration, physical compounding, or
production activation was performed. Original worktrees and private backups are
retained; no worktree cleanup or removal was performed.

## Cutoff and complete accounting

The capture finished at **2026-09-10 08:58:15 UTC / 15:58:15 Bangkok**. It preserves
the existing integration progress plus the 19 source checkouts without replacing
the original September 9 snapshots. Private execution records are under
`D:/codex-preservation/perfume-chem-20260909/execution-20260910T085554Z`.

The committed `worktree_consolidation_ledger_20260910.json` accounts for **25,793
source records**: net committed changes from each source merge base, staged and
unstaged changes, cutoff files, changed older preserved versions, and exclusions.
Repeated provenance references are retained; these are not 25,793 distinct features.
Intermediate Git history remains recoverable through the verified private bundle.

| Final disposition | Records |
|---|---:|
| Already present, byte-equal or exact EOL-only equivalent | 3,143 |
| Reconciled explicit basis/carrier source variants | 2 |
| Preserved disabled | 10,308 |
| Excluded with recovery/scope rationale | 10,716 |
| Deletion/absence intent reconciled | 1,624 |

All records have dispositions, source/recovery information, reasons, and verification
descriptions. A literal-path/module reference scan across 624 active source/test
files checked 649 distinct deletion/absence paths. Deletions from divergent source
trees were not blindly applied globally; the integration's selected versions remain,
and original deletion patches/index state remain recoverable. This is conservative
retention, not an assertion that dynamic consumers were exhaustively analyzed.

## Active implementation versus preserved candidates

The previously tested current-stock authority, exact dose receipts, frame/parent
provenance, separate Deep Plane implementations, and immutable registry foundation
remain in place. Diagnostics are disabled by default and cannot confer release
authority. Existing scientific values and acceptance thresholds were not fabricated
or weakened.

Two bounded additions were accepted in this execution:

1. Standard-library evidence primitives distinguish measured, modeled, transferred,
   and unknown values; require explicit known-value context/source/unit metadata;
   reject nonfinite values; and provide deterministic serialization/hashing. Declared
   source metadata is not proof that source content was independently verified.
2. Concentration labels may retain both explicit basis and carrier, for example
   `10% w/w in DPG`. All three existing bases are preserved. Balanced parentheses
   are required; conversion/default semantics were not broadened into new dosing
   or scientific authority.

`incoming_review/worktree_candidates/` contains **3,051 deduplicated inert payloads**
(102,141,737 bytes), with original paths/hashes mapped by the ledger. Conflicting
versions are retained separately. No payload has an executable Python extension,
and there are no candidate imports, routes, test-discovery entries or runtime
registrations. The package's tests verify byte identity and isolation.

The eleven reviewed groups are inventory/material/dose lineage; evidence/release
contracts; SolForge; temporal/preference evidence; perceptual architecture; Cypress;
protected evidence/workbench; unified/Deep Plane adapters; backend/persistence/
packaging; formula/study collections; and theory/history. Their exact blockers and
preservation decisions are in the ledger. Key blockers include missing dependency
bundles, incompatible historical registry admission states, removal of stronger V3
bindings in some publish variants, and incomplete backend process-boundary review.
Preserving these candidates is not runtime acceptance.

Generated audit logs were moved from the provisional review package back to private
preservation. No original log was deleted. Sensitive/tool-policy files and external
binary datasets remain excluded from commits. Redacted local credential-pattern
scans passed on both staged groups; this is not credential authentication, exhaustive
secret assurance, or sanitization of shared historical Git objects.

## Verification and remaining holds

The full verifier completed after the active implementation changes:

- **12 groups PASS, 8 FAIL, 2 optional Docker groups SKIPPED.**
- Root shard results: **2,834 passed, 18 failed, 4 setup errors** across 2,856 cases.
- The integration-extension shard passed **937 tests**; this is included in the root
  count and must not be added to it.
- Backend: **629 passed, 1 failed**. Backend lint and type checking passed before
  backend pytest; backend suites were not run concurrently.
- Compilation, engine lint/types, material-data validation, golden formula/API
  checks, package build, wheel smoke, and fixture lock passed.
- Post-commit focused verification: **232 passed**, covering candidate isolation,
  verifier coverage, evidence primitives, units, inventory/preflight, pre-mix,
  registry, Deep Plane and OAV binding. These overlap the full-run tests.

The full report is `output/verification/consolidation-full-20260910.json`; its exact
hash and check results are recorded in `consolidation_acceptance_20260910.json`.
The candidate package was refined to exclude generated logs while verification
was in progress; the final package and ledger were reverified by the subsequent
post-commit focused suite. No active implementation changed during the full run.

The isolated pre-implementation control restores the captured 88 files over the
base, plus the captured explicit LF transport rules for unchanged historical blobs.
The first control attempt produced transport-related errors and was superseded.
The corrected control reproduces the same failure family for **all 22 failing root
nodes**, and the backend's exact frozen-corpus mismatch also reproduces. Both
artifact checks have identical per-file status/issue sets: 7 stale, 49 unbound
legacy, 14 quarantined, and 456 without an analysis artifact.

Remaining holds include:

- OAV coverage **84.553%**, below the unchanged `>85%` criterion. This predates this
  execution but was introduced relative to the older base by the expanded inventory;
  it is an inherited data hold, not an old-base-preexisting success claim.
- Missing Guaiacwood database migration coverage and prose-valued character profiles.
- Historical C0/C5/D0, panel, corpus, and formula source/receipt mismatches.
- Existing stock/scenario and export-set expectations that do not match the retained
  current authority/contracts.
- Docker runtime behavior was not accepted or tested; optional checks remain skipped.

No unexplained new failing test node was found relative to the pre-implementation
control. The full verifier remains FAIL: consolidation acceptance does not override
its completion gate or grant release readiness.

## Recovery and post-cutoff changes

Representative isolated recovery passed for the history bundle, tracked content,
an index snapshot, a real staged deletion applied from its saved patch, a binary,
an untracked file, and an unstaged file. Candidate payload hashes were independently
read back. Index-only objects may require the recorded HEAD plus binary staged
patch; do not assume every uncommitted object exists in the history bundle.

The original source HEADs and indexes still matched at final inspection. The
canonical checkout acquired post-cutoff changes, including `engine/name_utils.py`,
`engine/odor_thresholds.py`, `engine/pipeline/natural_absolute_decomposition.py`,
and its audit log, plus Git-visible status changes. They are recorded separately
in the acceptance record/private source audit and are **not included in this cutoff**.
No attribution to another task is inferred merely from the changed hashes.

Use the integration branch for the consolidated result. Do not delete the original
worktrees or backups based on this handoff. Capture exclusions—oversized files,
ignored historical archive/output content, environments, unreachable objects and
reflogs—retain their documented limitations; the representative rehearsal is not
a claim of a full restore of every original directory.
