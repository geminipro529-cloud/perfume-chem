# Build C6 dynamic release implementation plan

> Execute test-first in the authoritative `D:\chatbots\perfume-chem` repository.
> Preserve the existing dirty worktree, use only supported runtimes, capture
> stdout/stderr separately without a PTY, disable ANSI output, and apply explicit
> timeouts. Do not begin C7 until the C6 exit gate is sealed and replayed.

## Baseline

- Phase parent: `59582f7314bfe90bed9096fd534777c9e1a71dce`.
- C5 decision: PASS; C6 open.
- C5 empirical status: `BLOCKED_PENDING_DATA`.
- Recovery archive:
  `D:\.backups\perfume-chem\build-c6-prewrite-20260803T015345+0700.tar`.
- Archive SHA-256:
  `3947df81ab4825c05ff2ccc679f853146a8217b92de75f4268b0cc538a553454`.
- Archive verification: PASS, 432 files, all 429 existing dirty/untracked files
  preserved, zero unsafe/duplicate/content/current-state mismatches.
- DeepLuna contract audit: `DS-29057cb3a871275b1d35503fc664a037`,
  PASS/POSITIVE, one FLASH call, `NO_LUNA`, no scope deviation.

## Task 1: Freeze the red contract

Create `tests/test_c6_dynamic_release.py` before implementation. Cover:

- exact closed process layers and honest output labels;
- component, substrate-model, initial-mass, and input-set validation;
- strict mapping round trips and hash-tamper rejection;
- no defaults and exact parameter-source hashes;
- sealed-vial versus finite-film parameter rules;
- exact C3 release, selector, operation, input-reference, and context binding;
- applicability abstention for missing, partial, wrong-unit, cross-substrate,
  component-mismatched, or tampered requests;
- analytic sealed-compartment transfer;
- finite-film mass conservation and nonnegativity;
- high-rate/large-step stability;
- explicit sink accounting;
- changing film thickness and matrix composition;
- solvent-fraction feedback into later component rates;
- three deterministic uncertainty scenarios and sensitivity envelope;
- complete substrate-kind parameterization without cross-transfer;
- reproducibility and canonical ordering;
- physical persistence as residual mass only;
- no sensory or measured-performance claim labels;
- no legacy/runtime/database imports; and
- package export plus project-verifier registration.

Run focused C6 tests and record the expected collection/import failure. Run a
C3 compatibility check to prove the red state is isolated to the missing C6
implementation.

Commit only the design, plan, and red test contract.

## Task 2: Implement immutable C6 input contracts

Create `engine/physics/dynamic_release.py` with:

- validation helpers and `DynamicReleaseContractError`;
- `PhysicalProcessLayer`, `PhysicalTrajectoryLabel`,
  `DynamicParameterAuthority`, and `RateScenario` enums;
- immutable `DynamicComponentParameters`;
- immutable `SubstrateModelParameters`;
- immutable `InitialCompartmentMass`;
- immutable `DynamicReleaseInputSet` with canonical parser, hash, and exact C3
  input-reference conversion.

Use `stable_json_hash`; reject booleans/non-finite values, invalid ranges,
duplicates, wrong optional-field combinations, unknown mapping keys, and content
hash drift. Parameter authority is only `SIMULATION_ONLY_UNCALIBRATED` and cannot
carry a calibration receipt or cross-substrate permission.

Run the contract-validation and serialization subset until green.

## Task 3: Implement the conservative state machine

Add immutable result types:

- `ComponentCompartmentState`;
- `DynamicTrajectoryFrame`;
- `ScenarioTrajectory`; and
- `DynamicReleaseSimulation`.

Implement private helpers for exact hazard fractions, environment factors,
finite-film resistance, matrix solvent fraction, current film thickness,
machine-roundoff normalization, and per-step closure checks.

Implement `simulate_dynamic_release()` to produce lower-rate, nominal, and
upper-rate trajectories plus a pointwise sensitivity envelope. Verify closure
inside the implementation on every component and frame; never rely on tests
alone to detect conservation failure.

Run analytic, conservation, nonnegativity, solvent-feedback, uncertainty, and
reproducibility subsets until green.

## Task 4: Bind the state machine to C3

Implement `DynamicReleaseAdapter` with an immutable C3 release:

- family `DYNAMIC_SEMI_EMPIRICAL_MODEL`;
- selector version composed from `c6-conservative-compartment-v1`, the exact
  substrate kind, and the substrate-parameter hash prefix;
- operations `PREDICT_DYNAMIC_RELEASE` and `PROPAGATE_UNCERTAINTY`;
- evidence `UNVALIDATED`;
- OAV authority false;
- training-data hash absent;
- exact permitted and forbidden claim wording.

Applicability must bind the exact C2 matrix/environment hashes, exact C6 input
reference, component IDs, absolute `mg` mass closure, environment kind, required
finite-film or sealed context, units, and substrate-model kind. Outside or
insufficient requests abstain before compute through C3.

Run router, applicability, substrate-separation, claim, and C3 compatibility
subsets until green.

## Task 5: Export and register verification

Update `engine/physics/__init__.py` with explicit C6 imports and `__all__`
entries. Update `engine/project_verification.py` to include the new module and
test shard. Touch `tests/test_c3_model_interface.py` only if an explicit export
compatibility assertion is needed.

Do not add a production caller or modify a legacy dynamic implementation.

Run focused C6 and C0-C5 compatibility tests. Run Ruff, basedpyright, and mypy
on the exact changed paths.

## Task 6: Mutation evidence

On the unstaged exact implementation source, temporarily apply and restore one
mutation at a time:

1. bypass per-step closure enforcement;
2. remove exact substrate-kind binding;
3. replace bounded exponential hazard with unbounded `k * dt`; and
4. allow a sensory output label.

Each matching focused test must fail under mutation and pass after byte-exact
restoration. Record source hashes before and after. Never mutate protected data,
databases, production callers, or unrelated dirty files.

## Task 7: Full local gate

Capture a non-PTY matrix with separate UTF-8 stdout/stderr and explicit
timeouts for:

- runtime versions;
- protected-state snapshot before;
- C6 focused tests;
- C5/C4/C3/C2/C1/C0 compatibility tests;
- C0 standalone inventory verifier;
- complete root tests;
- C6 no-legacy-dependency invariant;
- `pip check`;
- Ruff;
- basedpyright;
- mypy;
- scope verification;
- recovery-archive verification;
- protected-state snapshot after and comparison; and
- ANSI/credential-shaped log scan.

The gate fails on any timeout, nonzero exit, nonempty stderr, ANSI escape,
credential-shaped match, source-restoration mismatch, protected-state drift,
or scope escape.

## Task 8: DeepLuna and Sol acceptance

Run a fresh exact-project `deepseek_check`. If and only if readiness is `READY`,
submit one bounded read-only DeepLuna Fast audit over the C6 design,
implementation, focused tests, gate metadata, scope result, and C5 empirical
boundary. Enforce FLASH-only, one provider call, `NO_LUNA`, and no Codex/GLM
workers.

Sol must independently reproduce every provider finding against local source
and run a targeted test subset. DeepLuna cannot approve architecture,
scientific promotion, scope, or final acceptance.

## Task 9: Seal evidence and exact-commit replay

Write `docs/verification/c6/**` with:

- the software-gate decision;
- implementation and evidence commits;
- test/static/mutation counts;
- exact archive and protected-state hashes;
- replay manifests;
- DeepLuna provenance and Sol reconciliation;
- C5 empirical boundary retained as `BLOCKED_PENDING_DATA`;
- explicit simulation-only authority and prohibited claims; and
- `c7_open = false` until the postcommit replay passes.

Commit only C6 evidence paths. Replay the exact evidence commit with an empty
index and preserved dirty worktree. Record final decision receipts, update the
gate to PASS, commit only C6 decision evidence, and verify that commit's direct
parent and path scope.

## C6 done criteria

C7 opens only after all of the following are true:

- conservation, nonnegativity, reproducibility, solvent feedback, uncertainty,
  and substrate-separation tests pass;
- output labels remain physical and simulation-only;
- exact C3 routing and fail-closed applicability pass;
- no legacy, database, migration, production, or scientific-artifact path is
  changed;
- full local and mutation gates pass;
- DeepLuna Fast audit and Sol reconciliation pass;
- evidence is committed and replayed at the exact commit; and
- protected files and all pre-existing dirty/untracked work remain unchanged.
