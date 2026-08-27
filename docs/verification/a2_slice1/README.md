# A2 Slice 1 verification record

Status: `A2_SLICE1_PASS`

This record covers only Build A, A2 Slice 1 (A2.1), canonical planning
persistence. It does not promote the full A2 build, scientific release, or A3.

## Checkpoint identity

- Branch: `codex/add-inventory-materials`
- A1R accepted checkpoint: `c52e4933aa0ee7a9d79f6f595cf3d3e1b7973049`
- Committed A2.1 plan checkpoint and implementation parent:
  `672d1a7c8358d9d061d14cbbe3ca63abf6d3f5ad`
- Plan file SHA-256:
  `ac003c8b1bbb719ef96e97f4afc8bf58283c2da5f1e6220bf79e347f47067329`
- Ending implementation checkpoint: this record is committed in the bounded
  checkpoint whose message is
  `build(a2): add canonical planning persistence`. A commit cannot contain its
  own literal SHA without changing that SHA; resolve the immutable value with
  `git rev-parse HEAD` and verify that its parent is `672d1a7...`.

## Recovery package

Before implementation, a path-preserving recovery package was created at:

`C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a2-slice1-preimplementation-recovery\perfume-chem-a0-20260729T194130Z`

The package recorded 104 changed tracked paths, 507 untracked paths, and 6,593
important ignored paths. Eight sensitive local paths were archived without
displaying or transmitting their values. The source-change count during
capture was zero and restoration verification passed. A hash list alone was
not treated as the backup.

## Changed paths

The bounded checkpoint contains only:

- `backend/alembic/env.py`
- `backend/alembic/versions/20260730_0001_a2_planning_core.py`
- `backend/app/api/v1/endpoints/lab_planning.py`
- `backend/app/api/v1/router.py`
- `backend/app/models/lab.py`
- `backend/app/models/lab_planning.py`
- `backend/app/repositories/lab.py`
- `backend/app/repositories/lab_planning.py`
- `backend/app/schemas/lab_planning.py`
- `backend/app/services/lab_export.py`
- `backend/app/services/lab_planning.py`
- `backend/app/services/lab_service.py`
- `backend/tests/a2_planning_fixtures.py`
- `backend/tests/integration/test_a2_planning_api.py`
- `backend/tests/integration/test_a2_planning_export.py`
- `backend/tests/integration/test_a2_planning_migration.py`
- `backend/tests/integration/test_a2_planning_transactions.py`
- `backend/tests/integration/test_backup_restore.py`
- `backend/tests/integration/test_lab_migration.py`
- `backend/tests/unit/test_a2_planning_schema.py`
- `backend/tests/unit/test_a2_planning_service.py`
- `backend/tests/unit/test_lab_schema.py`
- `backend/tests/unit/test_phase1a_migration.py`
- `docs/verification/a2_slice1/README.md`

The existing dirty worktree was not cleaned. The protected legacy endpoint,
schema, and API test were not modified.

## Implementation decisions

- Eleven append-only canonical planning tables are represented in ORM metadata
  and the explicit `20260730_0001` migration.
- The migration is based on `20260717_0001`, installs named foreign-key,
  uniqueness, status, quantity, sequence, idempotency, and append-only
  constraints, and downgrades in reverse dependency order.
- SQLAlchemy 2 migration execution required an explicit online connection
  commit after `context.run_migrations()`; without it, the version-row update
  rolled back even though SQLite DDL persisted.
- The existing `LabService._transaction()` remains the write owner.
  Repositories do not own commits.
- Target identity and build identity remain independent. Target acceptance,
  formula lineage, mapping revisions, build-plan revisions, and reservation
  events are immutable/hash-chained where required.
- Reservation commands are atomic and idempotent, reject stale or mismatched
  authority, and serialize availability checks so concurrent requests cannot
  make available stock negative. They do not create inventory movements.
- The untouched legacy `/api/v1/lab/export` contract continues to use the v1
  no-argument export. Canonical planning export is explicit v2; its byte form
  is deterministic and its import is idempotent. V1 import does not invent
  planning authority.
- New `/api/v1/lab/v2` routes are thin service adapters with stable error
  envelopes.

## Test-driven evidence

All commands used non-PTY execution, disabled ANSI output, and had explicit
timeouts.

Observed RED states:

- Schema/migration contracts: 8 failed, 2 passed before tables and migration.
- Planning service: collection failed because `app.services.lab_planning` did
  not exist.
- Reservation transaction contracts: collection failed because
  `InsufficientAvailableStockError` did not exist.
- Export contracts: 1 failed and 3 passed before v2 planning export.
- API contracts: 2 failed before the versioned routes existed.

Progressive GREEN states:

- Schema/migration group: 14 passed.
- Planning service group: 14 passed.
- Reservation plus legacy transaction group: 18 passed.
- Export plus backup group: 9 passed.
- Versioned API plus legacy compatibility group: 13 passed.
- Final six-file A2.1 group on supported Python 3.11.15: 34 passed in 22.81
  seconds, zero failures, errors, or skips.

Two final rerun attempts made under a read-only repository sandbox produced
SQLite setup errors because the existing test fixture intentionally creates
`backend/test_perfume_chem.db`. These were environment failures, not acceptance
runs. The identical gate was then rerun with write access on supported Python
3.11.15 and passed 34/34.

## Complete gates

- Ruff: `poetry run ruff check app alembic tests` passed.
- MyPy: `poetry run mypy app --ignore-missing-imports` passed for 75 source
  files.
- Full backend: 226 passed, 0 failed, 0 errors, 0 skipped in 82.474 seconds.
- Full root suite on Python 3.11.15: 1,000 passed, 0 failed, 0 errors, 0
  skipped in 60.059 seconds.
- Artifact verifier: exit 0, status `WARN`, with 452 `NONE`, 14
  `QUARANTINED`, 49 `UNBOUND_LEGACY`, and no blocking `STALE` or `TAMPERED`.
- Canonical project verifier: 19 passed, 0 failed, 2 optional checks skipped;
  completion gate `PASS_WITH_SKIPS`.
- Optional skips: `docker-build` and `docker-smoke-test` because Docker was
  unavailable.
- Release axes: code ready, data ready, infrastructure ready, validation
  blocked. Held-out sensory validation remains required.

JUnit evidence:

- `verification_runs/a2-slice1-backend.xml`
- `verification_runs/a2-slice1-root.xml`

Verifier evidence:

- `verification_runs/a2-slice1-artifact-verify.stdout.json`
- `verification_runs/a2-slice1-project-verify.stdout.json`

These generated verification outputs remain uncommitted.

## Migration and database evidence

- `alembic heads`: exactly `20260730_0001 (head)`.
- History:
  `20260716_0001 -> 20260717_0001 -> 20260730_0001`.
- Tests passed for upgrade from an empty database, upgrade from a released
  `20260717_0001` copy, downgrade to `20260717_0001`, legacy-table
  preservation, append-only triggers, and database-level invalid-row
  rejection.
- The canonical `perfume_chem.db` was not migrated. It remains zero bytes with
  SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- The verifier changed `data/perfumery_kb.db`. Only that exact entry was
  extracted to a separate candidate from the verified recovery archive. The
  candidate matched the baseline hash and passed `PRAGMA integrity_check`.
  The authoritative file was restored and rechecked:
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`,
  SQLite integrity `ok`.

Protected file hashes after verification:

- `backend/app/api/v1/endpoints/lab.py`:
  `001ad5bd79aa8439070eb6273b2cb2362da5ab162c2f722fb7c57324ac74e5c5`
- `backend/app/schemas/lab.py`:
  `d1f450e5668830ffdfbf91a5f54ab2b45daaef6250c4a4545816f2fd01055aa8`
- `backend/tests/integration/test_lab_api.py`:
  `04bce8fff450b5fa8ef8ace049960cfca5a19c20b8ae6d81bf81cfeef04241a6`

## DeepLuna Fast review

DeepLuna was advisory only; Sol independently verified all accepted claims.
Fast-only/no-fallback jobs:

- `DS-16e8c5e4690d24c9d19d8d1a05e78787`: accepted bounded plan review.
- `DS-1f5ef550f146c93ffc6fac4ee4b97ad3`: accepted preimplementation review.
- `DS-dd96f0a003e1c00401b92f41448d9088`: accepted final critical-range audit;
  no concrete blocker found.
- `DS-ffe9f8147152309791abb7880dd40bab`: rejected because the requested read set
  was too broad.
- `DS-5d9fd5dfef1d2681178090501c47f438`: rejected locally because the packed
  evidence exceeded the declared input ceiling.

No claim from a rejected or incomplete job was used for acceptance.

## Boundary

- `A2_SLICE1_PASS`
- `A2_COMPLETE=false`
- `A3_STARTED=false`
- `SCIENTIFIC_RELEASE_BLOCKED=true`

Remaining A2 work includes analytical/regulatory persistence, legacy adapters,
and the later migration-acceptance slice. The canonical database remains
unmigrated. Work stops at this A2.1 boundary.
