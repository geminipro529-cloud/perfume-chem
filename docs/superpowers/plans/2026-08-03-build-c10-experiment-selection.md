# Build C10 Constrained Experiment Selection Implementation Plan

> **For agentic execution:** use `superpowers:executing-plans` inline. Codex
> subagents are prohibited; bounded DeepLuna Fast work is read-only and
> advisory. Sol retains architecture, science, scope, and final acceptance.

**Goal:** Build a deterministic, constraint-first mixture-design and
experiment-selection authority that preserves controls, exposes uncertainty,
enforces C9 quarantines, and cannot bypass safety, scientific, or human gates.

**Architecture:** A new pure `engine.optimization` package separates immutable
contracts, composition feasibility, selection, and historical-regression
evidence. Legacy optimizer and experiment-planner code remains untouched and
quarantined. TDD commits precede implementation commits, and final acceptance
requires exact-commit replay.

**Tech Stack:** Python 3.11 frozen/slotted dataclasses, enums, canonical JSON
SHA-256 hashing, deterministic integer-lattice enumeration, pytest, Ruff,
mypy, basedpyright, PowerShell non-PTY evidence capture, and Git exact-commit
replay.

---

**Authoritative parent:**
`a2aaad783ddd03d13c8f72cc277db0da7e139814`

**Verified prewrite archive:**
`D:\.backups\perfume-chem\build-c10-prewrite-20260803T080045+0700.tar`
with SHA-256
`1e66410f37b4c6cf3efa96423d7d182a7ebbca60a5079e50277c66f30a81acf9`.

## File map

- `engine/optimization/contracts.py`: immutable C10 records, closed
  vocabularies, canonical identities, and validators.
- `engine/optimization/mixture_design.py`: constrained lattice generation and
  composition/hard-gate assessment.
- `engine/optimization/selection.py`: authority filtering, Pareto selection,
  acquisition utility, controls/replicates, stop policy, and human approval.
- `engine/optimization/historical.py`: reported historical-search claim and
  fail-closed reproducibility assessment.
- `engine/optimization/__init__.py`: exact public C10 API.
- `tests/test_c10_mixture_design.py`: composition and hard-gate RED/GREEN
  contract.
- `tests/test_c10_selection.py`: authority, Pareto, utility, control,
  replicate, stop, human-gate, and determinism contract.
- `tests/test_c10_historical.py`: historical-regression evidence boundary.
- `engine/project_verification.py`: C10 truth-core and focused static scope.
- `docs/verification/c10/**`: generated C10 verification and replay evidence.

### Task 1: Freeze the design checkpoint

**Files:**

- Create: `docs/superpowers/specs/2026-08-03-build-c10-experiment-selection-design.md`
- Create: `docs/superpowers/plans/2026-08-03-build-c10-experiment-selection.md`

- [ ] Verify HEAD is the C9 final decision commit and the index is empty.
- [ ] Reverify the C10 archive and require zero archive or current-work
  mismatch.
- [ ] Confirm `engine/optimizer/models.py`, `engine/optimizer/scoring.py`, and
  `tests/test_experiments_planner.py` retain their current hashes.
- [ ] Scan both documents for placeholders, contradictory authority, and
  paths outside C10 scope.
- [ ] Stage only the two documents and commit
  `docs(c10): define constrained experiment-selection boundary`.

### Task 2: Write the complete RED contract

**Files:**

- Create: `tests/test_c10_mixture_design.py`
- Create: `tests/test_c10_selection.py`
- Create: `tests/test_c10_historical.py`

- [ ] Freeze the exact public API, enums, and package exports.
- [ ] Test stock fractions sum to one and raw/active/carrier totals conserve.
- [ ] Test unknown stocks, duplicate rows, minimum measurement, integer step,
  inventory overdraw, total-active range, module ranges, recognizer floors,
  family bounds, and negative-space caps.
- [ ] Test safety and action receipts are PASS, current, and bound to the exact
  formula state before any acquisition term is evaluated.
- [ ] Test deterministic constrained-lattice generation and bounded
  truncation; every emitted point must satisfy the composition domain.
- [ ] Test all 19 C9 surfaces: 15 forbidden numeric, two capability-only, one
  calibrated-model-required, and one abstention-only.
- [ ] Test longevity, sillage, projection, emotion, and hedonic remain
  withheld without exact Build D receipts.
- [ ] Test uncertainty, unit, scope, source/model identity, and common
  objective schema are mandatory.
- [ ] Test Pareto dominance precedes utility and utility publishes every
  explicit normalized contribution.
- [ ] Test feasible controls and exact-composition replicates are retained,
  and missing or mismatched controls/replicates block selection.
- [ ] Test every stop condition and require no proposed new experiment after
  stop.
- [ ] Test proposals are non-executable and only an exact-hash PASS human
  receipt authorizes them.
- [ ] Test the historical claim is `REPORTED_UNVERIFIED`, missing artifacts
  block, and mismatched replay values cannot pass.
- [ ] Add AST dependency tests forbidding legacy optimizer/planner, unsupported
  calculators, backend, database, environment, network, clock, and random.
- [ ] Run all three files and require RED collection failure because
  `engine.optimization` does not exist; capture separate empty stderr.
- [ ] Commit only the RED tests as
  `test(c10): freeze constrained experiment-selection contract`.

### Task 3: Implement immutable contracts

**Files:**

- Create: `engine/optimization/contracts.py`
- Create: `engine/optimization/__init__.py`
- Test: all C10 tests

- [ ] Implement closed enums for stages, roles, gates, objective authority and
  direction, selection state, and stop reasons.
- [ ] Implement validated immutable stock, dose, candidate, domain, objective,
  acquisition, policy, campaign, proposal, and authorization records.
- [ ] Normalize all mappings to sorted tuples and reject duplicate keys.
- [ ] Implement canonical JSON and SHA-256 content identities.
- [ ] Run the contract-only test subset until green.

### Task 4: Implement constrained mixture feasibility

**Files:**

- Create: `engine/optimization/mixture_design.py`
- Modify: `engine/optimization/__init__.py`
- Test: `tests/test_c10_mixture_design.py`

- [ ] Implement candidate formula-state hashing over exact stock definitions
  and composition.
- [ ] Implement independent raw, active, named-carrier, cost, and inventory
  accounting.
- [ ] Implement every composition, module, recognizer, family, negative-space,
  safety, and action hard gate with stable reason codes.
- [ ] Implement bounded deterministic integer-lattice generation that filters
  composition constraints before returning candidates.
- [ ] Run the complete mixture test file and static checks until green.

### Task 5: Implement authority-aware selection

**Files:**

- Create: `engine/optimization/selection.py`
- Modify: `engine/optimization/__init__.py`
- Test: `tests/test_c10_selection.py`

- [ ] Enforce C9 `C10Use` rules and Build D unsupported-outcome assessment.
- [ ] Require common objective schema, explicit direction/unit/scope/source,
  and finite standard uncertainty.
- [ ] Retain the nondominated Pareto frontier without scalar collapse.
- [ ] Compute only caller-versioned acquisition terms with visible bounds,
  weights, normalized values, and contributions.
- [ ] Preserve feasible controls and exact replicates; deterministically select
  bounded new candidates by utility and candidate identifier.
- [ ] Implement all preregistered stop reasons.
- [ ] Return non-executable proposals and exact-hash human authorization.
- [ ] Prove repeat runs and different `PYTHONHASHSEED` values serialize
  identically.

### Task 6: Implement the historical regression boundary

**Files:**

- Create: `engine/optimization/historical.py`
- Modify: `engine/optimization/__init__.py`
- Test: `tests/test_c10_historical.py`

- [ ] Record the reported values as an immutable unverified claim, not a
  baseline.
- [ ] Require implementation/input/result hashes, exact replay command,
  verifier identity, exit status, candidate count, guardrail count, separate
  DNA threshold, passed guardrails, and winner DNA score.
- [ ] Return stable missing-artifact or mismatch states.
- [ ] Do not synthesize the missing historical implementation or inputs.

### Task 7: Register and statically verify C10

**Files:**

- Modify: `engine/project_verification.py`
- Test: all C10 tests and `tests/test_project_verification.py`

- [ ] Add the three C10 test files to the truth-core shard.
- [ ] Add all C10 modules/tests to focused Ruff and mypy coverage.
- [ ] Run Ruff format/check, mypy, basedpyright, compileall, and `pip check`.
- [ ] Prove no dirty legacy optimizer/planner path is staged.
- [ ] Commit implementation and verifier registration as
  `feat(optimization): add constrained experiment selection`.

### Task 8: Mutation evidence

**Generated evidence:** `docs/verification/c10/logs/mutation/**`

- [ ] Record source SHA-256 before every mutation.
- [ ] Remove stock/carrier conservation; require its guard test to fail.
- [ ] bypass a formula-bound safety gate; require its guard test to fail.
- [ ] allow a forbidden C9 objective; require its guard test to fail.
- [ ] scalar-rank before Pareto filtering; require its guard test to fail.
- [ ] drop controls or accept a mismatched replicate; require guard failure.
- [ ] authorize without a bound human receipt; require guard failure.
- [ ] promote the historical reported result without artifacts; require guard
  failure.
- [ ] Restore bytes after every mutation and require exact source hashes.

### Task 9: Local verification matrix

**Generated evidence:** `docs/verification/c10/logs/final/**`

- [ ] Capture C10 focused, C9 through C0 compatibility, C0 inventory,
  project-verification, backend compatibility, and complete-root tests.
- [ ] Capture dependency, package-export, Ruff, Ruff-format, basedpyright,
  mypy, compile, and `pip check` results.
- [ ] Reverify the C10 archive and all preserved dirty/untracked paths.
- [ ] Snapshot protected database/WAL/SHM files before and after and run
  immutable database quick checks.
- [ ] Re-run the C5 actual-data boundary and require
  `BLOCKED_PENDING_DATA` with no empirical promotion.
- [ ] Scan strict UTF-8 logs for zero ANSI and zero credential-shaped matches.
- [ ] Fail on timeout, nonzero exit, unexpected stderr, protected-state drift,
  forbidden dependency/path, nondeterminism, or accidental user-hunk staging.

### Task 10: DeepLuna Fast audit and Sol reconciliation

- [ ] Run a fresh exact-project `deepseek_check`.
- [ ] Only when `READY`, submit one bounded C10 read-only audit using `FLASH`,
  `NO_LUNA`, and one provider call maximum.
- [ ] Exclude secrets, environment values, databases, unrelated dirty files,
  architecture decisions, scientific promotion, and final acceptance.
- [ ] Sol mechanically reproduce each gate-bearing finding and reject worker
  count or interpretation errors.
- [ ] Capture settled postflight readiness, zero reservations, queue/lane
  state, accounting, and no-fallback metrics.

### Task 11: Seal and replay the C10 gate

**Files:**

- Create: `docs/verification/c10/experiment_selection_gate.json`
- Create: `docs/verification/c10/experiment_selection_gate.md`
- Create: `docs/verification/c10/logs/log-manifest.json`
- Create: `docs/verification/c10/postcommit/**`

- [ ] Generate and validate evidence with decision
  `PENDING_EXACT_COMMIT_REPLAY` and `c11_open=false`.
- [ ] Commit only `docs/verification/c10/**` as the evidence commit.
- [ ] Replay the bounded matrix at that exact commit in a clean detached
  worktree, with the verified preserved authoritative overlay only if the
  committed baseline independently proves it is required.
- [ ] Preserve failed harness attempts instead of erasing them.
- [ ] Set `decision=PASS` and `c11_open=true` only when every replay job passes
  with zero timeout, stderr, ANSI, credential, protected-state, or scope issue.
- [ ] Commit only final C10 decision evidence and run final scope/evidence
  validators.

C11 may begin only when the C10 final decision commit is the direct child of
the C10 evidence commit and every postcommit validator passes.
