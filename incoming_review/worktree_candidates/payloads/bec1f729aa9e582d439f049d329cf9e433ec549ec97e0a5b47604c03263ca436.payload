# XHIGH Stock-Basis Local Integration — 2026-08-09

State: `LOCAL_WORKTREE_INTEGRATED__TESTS_NOT_RUN__REMOTE_NOT_VISIBLE__XHIGH_NOT_FROZEN`

This receipt records integrator-only local work on `codex/add-inventory-materials`. It is not a freeze receipt, release approval, PRO-review authorization, CI receipt, or claim of GitHub publication.

## Repository state

- Historical remote control SHA: `a7bacff3539bf5e60c94d1fbe48df3d0f1f90da3`.
- Local branch ref discovered during this run: `c876ab128845c2e055251fdce4fb1c3f5d661045`.
- GitHub did not independently expose that commit when queried; no remote commit is claimed.
- The canonical GitHub branch still serves old `backend/app/services/formula_import.py` blob `0aad016326c66db01b6f6e67101431065f389fa9`, which retains the fail-open missing-dilution-to-neat and invalid-dilution-warning-skip behavior. This independently proves the local stock-basis repair is not yet remotely integrated.
- The working tree was modified after that local ref, so the edits described below are uncommitted unless a later repository receipt proves otherwise.

## Implemented locally

1. Exact V5 inventory authority pin using local workbook SHA-256 `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`.
2. Formula import now rejects missing, blank, dash, or unparseable stock strength instead of defaulting to neat or silently skipping the row.
3. Formula-version edges require `STOCK_NORMALIZATION` or `DESIGN_REVISION`.
4. `STOCK_NORMALIZATION` preserves per-material active-equivalent mass and rejects material-set changes. `DESIGN_REVISION` cannot also change retained-material stock solutions.
5. Revision 2+ is draftable, but cannot drive physical execution or pass workspace invariant replay without exactly one revalidated parent edge.
6. Permanent Prada L'Homme Citronellol regression is encoded: `14.363 × 0.10 = 1.4363` active versus `14 × 1.0 = 14` active, approximately `9.747267283993594×`, required hard fail.
7. Build-plan concentration fraction and basis must equal the exact selected `LabStockSolution`.
8. Exact-identity mapping preserves immutable target active quantity and unit.
9. Reservations are independently capped to immutable build-line mass. Volume lines require density authority before conversion to a mass ceiling.
10. Action proposals and committed measurements independently re-check immutable line mass; cumulative committed consumption is capped too.
11. Batch/formula-bound bottles reject freeform direct additions and transfers. Governed physical additions revalidate formula lineage.
12. Workspace import replays stock lineage, exact V5 build authority, build arithmetic, reservation/commit binding and ceilings, and bound-bottle execution invariants before commit.
13. The exact 261-row / 104-target V5 stock-strength triage is represented as repository quarantine metadata with zero compounding-authorized rows. Candidate DRAFT/UNDER_REVIEW rebuilds are allowed; APPROVED/executable state and reservations remain blocked until explicit clearance receipts exist.
14. Reconstruction-side neat-by-omission paths were hardened in target/inventory/build models and preflight. Depleted or quantitatively insufficient inventory lots no longer qualify as available in lot selection.

## Test work added or updated

Regression coverage was added for the Citronellol active-equivalence failure and positive compatible rebase, illegal mixed transition classes, unknown strength import, V5 pinning, exact stock fraction/basis, exact target-active preservation, over-line reservation, corrupted reservation action cap, cumulative commit cap, bound-bottle bypass, orphan revision physical execution, workspace-import rollback, quarantine approval blocking, depleted/insufficient stock, target unknown concentration, and preflight no-neat-default behavior.

## Not yet proven

No test runner is exposed by the current Perfume-Chem tunnel. Therefore none of the new/updated suites has been executed in this run. Ruff, mypy, backend pytest, root pytest, database roundtrip, and the full project verifier remain required.

The exact user-mandated `Perfume_Chem_Stock_Basis_Hardening_v2_Rebased.zip` / extracted directory still has not been recovered into the active runtime as exact bytes. v1 remains historical and `STALE_REBASE_REQUIRED`. Newer candidate packages do not erase that provenance requirement.

A File Library byte recheck of V5 was attempted after the local hash was obtained, but retrieval returned HTTP 401 during this run. The local pin is therefore implemented but still requires independent byte re-verification before freeze.

## Decision

`DO_NOT_FREEZE`.

Do not emit `XHIGH_FROZEN_FOR_PRO_REVIEW` until the repository-native tests and full verifier pass after rebase and the resulting commit is independently visible on the canonical GitHub branch with the remaining provenance/authority receipts closed.
