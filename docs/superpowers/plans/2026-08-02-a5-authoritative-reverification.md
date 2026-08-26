# Build A Phase A5 authoritative reverification plan

Date: 2026-08-02

## Goal

Reproduce the complete target-to-inventory-to-bottle operation boundary from
the live tree and create the missing A5 exit report. Historical implementation
notes and commits are leads only.

## Constraints

- Preserve the dirty tree; do not clean, rewrite, or stage unrelated files.
- Do not modify production code, migrations, databases, or release artifacts
  unless a reproducible A5 contract failure requires a test-first repair.
- Use supported Python 3.11 environments, non-PTY commands, disabled ANSI,
  explicit timeouts, writable isolated test directories, and machine-readable
  test output.
- Use only a fresh exact-project, read-only, Fast-only DeepLuna audit. Sol
  retains architecture, transaction, safety, and final-acceptance authority.

## Execution

1. Read the complete A5 contract and inventory the event, inventory, service,
   migration, concurrency, backup, restore, and test surfaces in the live tree.
2. Run the bottle-event and inventory-operation root tests.
3. Run A5 schema, migration, transaction, concurrency, failure-injection,
   backup, and restore tests in the supported backend environment.
4. Run focused Ruff and MyPy checks and confirm the one current Alembic head.
5. Audit event semantics, stream guarantees, movement completeness, lot
   selection, structured diffs, lifecycle atomicity, and recovery through one
   bounded DeepLuna Fast task.
6. Repair any reproduced gap test-first. If none exists, add documentation
   only, rerun focused tests, inspect the exact diff, and checkpoint A5.

## Exit decision

A5 passes only when target-to-inventory-to-build-to-reservation-to-bottle
replay is deterministic, unit-safe, append-only, idempotent, atomic,
concurrency-safe, recoverable, and auditable for normal, correction, transfer,
retry, failure, backup, and restore paths.
