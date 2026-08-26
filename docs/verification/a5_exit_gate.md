# Build A Phase A5 exit gate

Date: 2026-08-02

Authoritative source baseline:
`c472f9f8c214265430762790a93671cc669b423e`.

Status: PASS for the local bottle and inventory operations software boundary.
This does not grant physical execution or product release authority.

## Reverification method

The historical A5 implementation plan promised an exit report, but no tracked
A5 exit report existed in the authoritative tree. The implementation commit
`d75a164e9a9f9373ef921cb8b528ee425c6a907c` was therefore treated as a lead and
reproduced against the current working tree.

No production source, migration, database, or release artifact was changed by
this reverification.

## Implemented boundary

- `engine/bottle/events.py` defines explicit semantics for every one of its 15
  event values. `ADD_MATERIAL` separates active, carrier, solvent, and
  unallocated composition; `ADD_SOLVENT` remains solvent; `DILUTE` is derived
  from actual source additions; `TARE_CONTAINER` changes reference metadata;
  `TRANSFER` links streams; `CLOSE_BATCH` closes ordinary additions; and
  `CORRECT_ENTRY` appends a replacement reference.
- Bottle streams enforce positive contiguous sequence, event identity,
  idempotency, deterministic replay, closed-stream restrictions, and acyclic
  correction references without editing prior events.
- `engine/inventory/operations.py` defines all eight movement types:
  `RESERVATION`, `RESERVATION_RELEASE`, `CONSUMPTION`, `RETURN`, `ADJUSTMENT`,
  `TRANSFER`, `CORRECTION`, and `REVERSAL`. Every immutable movement carries
  lot and build-line identity, raw and active quantities, unit and basis,
  before/after balance, uncertainty, actor, timestamp, transaction and
  idempotency identity, and correction or reversal linkage where applicable.
- Replay rejects stale balances, duplicate commands, invalid correction or
  reversal references, malformed transfer pairs, and negative balances.
- Lot selection evaluates identity, grade, basis, amount, uncertainty margin,
  expiry/safety, opened policy, FEFO, measurement uncertainty, waste,
  substitution cost, and user preference with explicit rejection reasons and
  score components.
- Structured state deltas keep target, stock, planned, reserved, and committed
  quantities typed with unit, basis, uncertainty, density source,
  comparability reason, substitution state, functions, and action state.
- Backend lifecycle services implement propose -> human confirm -> measure ->
  atomic bottle-event and inventory-movement commit -> replay verification.
  Retries are idempotent, stale sequences fail, insufficient stock fails
  atomically, and corrections remain append-only.
- Transfers share one transaction across source decrement, destination
  increment, measured loss, and both event-stream references. Failure
  injection proves neither ledger half persists alone.
- Backup and restore preserve active streams and open reservations, require
  staged maintenance-mode restore, create a pre-restore backup, and reproduce
  post-restore bottle and reservation replay.

## Fresh local evidence

- `tests/test_bottle_events.py` plus `tests/test_inventory_operations.py`: 24
  passed; JUnit SHA-256
  `60ea134b7b914f04dab0847e59b1c34bf05feedf41f5a103911ad7e51039f178`.
- A5 schema, migration, transaction, concurrency, failure-injection, backup,
  and restore backend modules: 20 passed; JUnit SHA-256
  `5bdf78c0b6903168004f871f5f20397c20047ce5cf198b24d71528996fc52b5d`.
- Focused engine and backend Ruff checks: passed.
- Focused MyPy checks: two engine and three backend source files passed with no
  issues.
- Alembic reports exactly one current head: `20260731_0012`.

## Canonical verifier

The latest full current-tree verifier at
`verification_runs/project_verification.json` records engine 1,095 tests,
backend 630 tests, 1,725 combined tests, 19 passed required checks, zero failed
or omitted checks, and two optional Docker skips because Docker was not
requested. Completion gate is `PASS_WITH_SKIPS`; report SHA-256 is
`52491a72415ba34881d13c212269325add6b183b56e74071f4f08e58ebb4e95a`.

## Protected database state

Both databases remained byte-identical across the A5 checks and passed
read-only SQLite `PRAGMA quick_check`:

- `data/perfumery_kb.db`: 2,084,864 bytes, SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`;
- `perfume_chem.db`: 12,288 bytes, SHA-256
  `02b64be88e4a8881c968ec9ef7f0185ed7b1bcedc6ed33885f07d7de70a0da5e`.

The root `perfume_chem.db` contains only an empty `alembic_version` table and
is not migration authority. The repository Alembic command and migration tests
provide that authority.

## DeepLuna Fast audit

An initial audit packet was rejected locally before provider execution because
its estimated 33,385 input tokens exceeded the 30,000-token ceiling. It is not
acceptance evidence.

After reducing the packet and running a fresh exact-project readiness check,
bounded read-only Fast job `DS-686f8429498307a2666cc18ee082fe5d` used route
`FLASH`, fallback policy `NO_LUNA`, and one allowed provider call. It returned
`PASS`, execution status `ACCEPTED`, and evidence verdict `POSITIVE`, with no
negative findings, residual risks, scope deviation, contradiction, or
acceptance-blocking gap. DeepLuna supplied review evidence only; Sol retained
final authority.

## Exit decision

A5 passes. Target -> inventory -> build -> reservation -> bottle -> inventory
replay is deterministic, unit-safe, atomic, recoverable, and auditable under
normal, correction, transfer, retry, concurrency, failure, backup, and restore
paths. Physical execution and scientific release remain outside this software
gate.
