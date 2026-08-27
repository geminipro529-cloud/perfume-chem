# A1R to A2 Staged Convergence Design

Status: approved by the user on 2026-07-30  
Repository: `D:\chatbots\perfume-chem`  
Starting checkpoint: `f55d4b3b2e4ccf23105045b25ab1628fa4b67a54`

## Decision

Build A continues through a corrective A1R checkpoint before Phase A2.
A1R closes a verifier-coverage defect discovered by a fresh live-tree health
check: the canonical verifier did not lint or type-check every A1 production
module, and expanded Ruff found six naming violations in three A1 modules.

A1R is limited to verifier coverage, behavior-preserving lint remediation,
tests, verification evidence, and a bounded checkpoint. It creates no database
migration and no A2 domain object.

After A1R passes, A2 proceeds through four sequential vertical slices:

1. canonical target, acceptance, formula-DAG, inventory-mapping, build-plan,
   build-line, and reservation persistence;
2. analytical method/run/peak/QC/attachment, dated regulatory assessment, and
   claim-specific authority persistence;
3. one-way legacy adapters and closure of dual-write paths without deleting
   legacy tables;
4. thin versioned API/workbench integration and complete migration,
   rollback, backup/restore, and verifier evidence.

## Authority and provenance

The accepted A0 architecture decision remains the governing architecture:

- persistent authority is the append-oriented `lab_*` SQLAlchemy schema;
- ordinary writes flow through `LabService` and `LabRepository`;
- `PerfumeWorkbench` is the calculation facade, not a database;
- engine dataclasses, Markdown, JSON, and reports are inputs or projections;
- absent canonical objects have no persistent release authority.

The accepted ADR is retained in the verified A0 evidence package and is bound
by that package's manifest. It is not silently reinterpreted from handoff
documents.

DeepLuna Fast may perform bounded mechanical inventories. Sol retains schema,
transaction, compatibility, scientific, security, provenance, and final
acceptance decisions. Provider output never establishes a phase gate.

## Dirty-work and isolation policy

The live repository contains authoritative uncommitted inputs and user-owned
changes. A clean Git worktree would omit that verification surface, so work is
performed in place only after a path-preserving recovery package is created
and restoration-tested.

The A1R pre-edit archive is:

`C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a1r-preedit-recovery\perfume-chem-a0-20260729T185259Z`

The package captured 104 tracked overlays, 507 untracked files, 6,652
important ignored files, the canonical database, and committed history.
Restoration verification passed with zero source changes during capture.
Secret-bearing archive content remains local-only and must never be displayed,
committed, or transmitted.

Existing user changes in these paths are preserved:

- `backend/app/api/v1/endpoints/lab.py`
- `backend/app/schemas/lab.py`
- `backend/tests/integration/test_lab_api.py`

A2 should prefer new focused lifecycle schema/router modules where that avoids
overwriting those changes.

## A1R behavior

A1R adds every A1 production module to both canonical `engine-lint` and
`engine-typecheck` commands. A regression test makes this coverage explicit.

The six Ruff findings are repaired without changing calculations:

- private and local mathematical variables use descriptive lowercase names;
- the public `generate_ensemble(..., N=...)` keyword remains compatible and
  receives a narrow `N803` suppression because existing callers use it;
- the recognizer's function-local role-weight mapping becomes lowercase.

No output values, error contracts, authority labels, or serialization formats
change.

## A1R verification and exit gate

A1R passes only when:

- the verifier-coverage regression is observed RED before implementation;
- the regression and focused A1 tests pass after implementation;
- expanded Ruff over every A1 module passes;
- MyPy over every A1 module passes;
- all 999 root tests and all 190 backend tests pass;
- formula artifacts have no blocking `STALE` or `TAMPERED` status;
- the canonical top-level verifier passes, with Docker skips reported rather
  than promoted;
- recovery evidence and deliverable manifests validate;
- one bounded A1R checkpoint SHA exists.

A2 remains prohibited until this gate passes. A3 remains prohibited until the
A2 exit gate passes.

## A2 migration safety

The zero-byte canonical SQLite database is the recorded A0 baseline. It is not
initialized during A1R.

A2 migrations must:

- extend the existing single Alembic chain from `20260717_0001`;
- be tested on empty and representative released-schema copies first;
- preserve one current head;
- provide downgrade/rollback evidence where practical;
- enforce uniqueness, foreign keys, append-only records, nonnegative
  reservations/inventory, event sequencing, and idempotency;
- pass backup/restore/export/import tests before any canonical database
  migration;
- retain legacy tables for compatibility reads until a later reviewed
  deletion migration.

## Rejected alternatives

A single wide A2 migration couples unrelated failure modes and increases
rollback risk. Adapter-only convergence cannot satisfy A2 because several
canonical persisted objects do not exist. Neither approach is accepted.
