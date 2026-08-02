# Build C5 calibration-program implementation plan

Design: `docs/superpowers/specs/2026-08-03-build-c5-calibration-program-design.md`
Phase parent: `085512ec620fd5a8f192fc6298a6fa1acce2d7b0`

## Preconditions

1. Confirm the C4 gate is `PASS` with `c5_open=true`.
2. Confirm actual instrument/calibration data are absent and keep the empirical
   phase `BLOCKED_PENDING_DATA`.
3. Preserve all current tracked modifications and untracked files in a
   restorable path-preserving archive before repository edits.
4. Keep production callers, databases, migrations, generated artifacts, and
   legacy calibration/analytical code unchanged.
5. Use Python 3.11, non-PTY execution, no ANSI, separate stdout/stderr, and
   explicit timeouts.

The prewrite archive is
`D:\.backups\perfume-chem\build-c5-prewrite-20260803T005146+0700.tar`, SHA-256
`baf09fe70d8b8e7691ea966b0b8c4c7e39d31965006f212151c062b4ffda9e72`.
Verification passed for 431 manifest files, including all 429 current
dirty/untracked files, with zero unsafe names, duplicates, content mismatches,
or current-work mismatches.

## Task 1: freeze executable tests (RED)

Create `tests/test_c5_calibration_program.py` first. Cover:

- current inventory digest and representative material-domain coverage;
- matrix coverage, exact closure, owned carriers, and DEP/water holds;
- immutable canonical serialization and tamper detection;
- complete protocol fields and exact B5 authority/hash binding;
- strict real JSONL import and rejection of simulated or incomplete evidence;
- all six leakage dimensions and all three required partitions;
- evaluation-plan metric vocabulary and absence of R-squared authority;
- model lock before held-out release;
- linear/log metric calculations and grouped summaries;
- baseline comparison, abstention, catastrophic outliers, and interval coverage;
- explicit acceptance PASS/FAIL behavior;
- simulation-only non-promotion; and
- empirical `BLOCKED_PENDING_DATA` with no actual observations.

Run only the new test and capture the expected import failure as RED evidence.
Commit only the C5 design, plan, and RED test.

## Task 2: implement the pure C5 contract

Create `engine/physics/calibration_program.py` with immutable enums/dataclasses,
strict constructors, exact mapping schemas, stable hashes, the pinned material
and matrix panels, B5 receipts and protocol binding, strict JSONL import,
leakage validation, split/evaluation/model locks, metric analysis, and distinct
real/simulation evaluation entry points.

No function may import or call the legacy calibration or analytical ledgers.
Run the focused suite to GREEN, then run Ruff, basedpyright, and mypy.

## Task 3: export and verifier integration

Update only:

- `engine/physics/__init__.py` to export accepted C5 contracts; and
- `engine/project_verification.py` to add the C5 test to `truth-core` and the
  module to bounded lint/typecheck slices.

Run C5 and C0-C4 focused tests plus project-verifier contract tests.

## Task 4: adversarial and mutation evidence

Use temporary mutation/restore cycles and prove tests catch:

1. allowing simulated observations through the real importer;
2. omitting one leakage dimension from cross-partition validation; and
3. permitting held-out release without a matching pre-release model lock.

Verify the exact source SHA-256 is restored after every mutation.

## Task 5: C5 evidence matrix

Capture separate stdout/stderr, return code, duration, timeout state, and
command identity for focused C5, ancestor C0-C4, the root suite, dependency
consistency, Ruff, basedpyright, mypy, project verification, archive
verification, protected database hashes/quick checks, scope validation, and
evidence-manifest validation.

The gate must explicitly record that actual instrument data are absent and
that empirical calibration remains `BLOCKED_PENDING_DATA` with no metrics or
promotion.

## Task 6: bounded DeepLuna audit and Sol acceptance

After local evidence is green:

1. run a fresh exact-project `deepseek_check`;
2. submit one bounded read-only DeepLuna Fast audit, `FLASH`, `NO_LUNA`;
3. locally reproduce every negative or gate-bearing finding;
4. commit the evidence seal;
5. replay the gate against that exact commit with a clean index and preserved
   unrelated worktree changes;
6. write and commit the C5 gate only if software/protocol criteria pass while
   empirical authority remains blocked; and
7. verify decision-parent identity, changed-path scope, focused tests,
   evidence validator, protected state, and empty index.

C6 opens only when the canonical C5 software gate passes. It does not inherit
empirical calibration authority.
