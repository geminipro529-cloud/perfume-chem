# Build B9 science-reporting gate

Status: `PASS`
B10 authorized: `true`

This package was refreshed from the authoritative working tree on 2026-08-02 and passed current local reconciliation. Historical 2026-07-31 PASS receipts are retained only as history and did not pass this gate.

## Current implementation result

No B9 production defect was reproduced. The eleven B9-owned source and test files have no worktree changes and no committed deltas from implementation head `596a90eaa4b7a6492137d15a77d7f006e16f6035` to the current pre-report head `cf85718d0db50506044fae58011033c2e240d0a9`. Reverification changed evidence files only; it added no production code and no migration.

The implementation exposes two GET-only surfaces:

- `/api/v1/lab/science/authority?view=strict|exploratory`
- `/api/v1/lab/science/report.md?view=strict|exploratory`

The repository has a query-only `snapshot` method over 25 explicitly named collections. The service publishes 20 ordered sections through per-collection fact, provenance, and authority allowlists. It recursively rejects credential-like fields, local database/artifact paths, and aggregate score fields. UI record data is inserted through DOM `textContent`.

## Evidence contract

The exact evidence vocabulary remains:

- `MEASURED`
- `LITERATURE_DERIVED`
- `SUPPLIER_PROVIDED`
- `EMPIRICALLY_CALIBRATED`
- `MODEL_ESTIMATED`
- `HEURISTIC`
- `SPECULATIVE`
- `UNKNOWN`

Strict mode partitions records into included and withheld while keeping withheld records and reason codes visible. Exploratory mode changes only the partition: it preserves each record's evidence class and `strict_eligible` result. Neither view emits a confidence/coverage percentage or obtains release authority.

## Fresh executable evidence

All commands were non-PTY, color-disabled, explicitly timed, and captured with separate stdout and stderr.

- B9 exact targets: `9 passed in 10.78s`; wrapper 24.99s; exit 0; no timeout; empty stderr.
- A2-through-B9 compatibility manifest: `463 passed in 639.47s`; 60 files; wrapper 651.756s; exit 0; no timeout; empty stderr.
- Ruff: `All checks passed!`; exit 0; empty stderr.
- mypy: `Success: no issues found in 4 source files`; exit 0; empty stderr.
- Node syntax check: exit 0; empty stdout and stderr.
- Alembic: `20260731_0012 (head)`; exit 0; empty stderr.
- Root and knowledge SQLite files: immutable read-only `quick_check=ok`; empty stderr.
- Runtime: Python 3.11.15 and Node v26.3.0.

The historical cumulative count of 462 is stale. The current count is 463 because commit `f941ad8a41d2a6ff5c968753458d3fc0f0901197` added `test_guard_rejects_endpoint_owned_transaction_calls` to the existing 60-file manifest. The preserved working-tree edit to `backend/tests/integration/test_lab_api.py` changes no test-function count.

## Preservation and database state

Before refreshing evidence, the complete 33-file prior B9 package was archived at `outputs/b9-authoritative-recovery/20260802T102000/b9-evidence-before-refresh.zip`. The ZIP is 20,094 bytes with SHA-256 `cb0bccbd23c5fd0757450dd1b1fb108714588b331ac62752d90b6de03942146e`; all 33 paths restored, all 33 hashes matched, and zero unsafe paths were found. The archive remains untracked.

Current protected databases were read only:

- `perfume_chem.db`: 12,288 bytes; SHA-256 `02b64be88e4a8881c968ec9ef7f0185ed7b1bcedc6ed33885f07d7de70a0da5e`; quick-check `ok`.
- `data/perfumery_kb.db`: 2,084,864 bytes; SHA-256 `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`; quick-check `ok`.

No production migration or backfill was run. Database-backed tests used external temporary databases.

## DeepLuna reconciliation

Fresh exact-project readiness was `READY` for `perfume-chem`, runtime `CANDIDATE_V2`, server 0.9.9, with idle lanes and zero reserved or unknown cost. Fast job `DS-b6e01a2109066d46826243bce80a940a` used FLASH/NO_LUNA and one provider call. Sol rejected its PASS for gate acceptance because it repeated the stale 462 count, failed to identify the historical database/archive fields, and crossed the Sol-only authorization boundary. Its bounded implementation observations are retained separately in `logs/deepluna_current_preaudit_rejected.json`.

## Authority and gate decision

B9 remains read-only presentation authority over canonical stored Build B records. It cannot create evidence, promote a claim, authorize release, certify safety, provide legal approval, or prove real-world performance.

Current Fast job `DS-7c595bfbde9754997a8e126505ef03d6` matched the corrected 9/463 execution evidence, reported no negative findings or scope deviation, and closed with zero reserved or unknown cost. Its textual citation matrix was sparse, so Sol accepted it only as bounded corroboration and independently reverified the full contract, source/log digests, databases, archive, and fail-closed transition.

The B9 exit gate passes. B10 is authorized; Build C remains unauthorized until B10 passes and the Build B boundary report is delivered.
