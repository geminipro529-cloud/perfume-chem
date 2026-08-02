# Build C3 Versioned Model Interface Implementation Plan

> Execution owner: Sol. Execute inline with test-driven development. Do not use
> Codex subagents, do not alter production callers, and do not begin C4 until the
> committed C3 exit gate passes.

**Goal:** Add a pure, versioned `engine.physics` model-contract and exact-routing
boundary that proves explicit model selection, no silent fallback, immutable
version binding, and out-of-domain abstention without implementing a scientific
equation or changing runtime callers.

**Accepted design:**
`docs/superpowers/specs/2026-08-02-build-c3-model-interface-design.md`

**Phase parent:** `f5ae19227e75dee30fe101b4324e1f54283174e3`

**Recovery archive:**
`D:\.backups\perfume-chem\build-c3-prewrite-20260802T202227+0700.tar`,
118,286,848 bytes, SHA-256
`fd4e38ff22b9a611fe46b61454f8705eb4b989615c7780a526bf2b813ef3196e`.
The streamed verifier found 0 unsafe members, duplicates, archive mismatches, or
current preserved-work mismatches across 429 Git-visible dirty/untracked paths.

**DeepLuna inventory:** `DS-4ee6afcbb8f56c86578301d1ec1b2bd2`, one
`FLASH`/`NO_LUNA` call, `PASS`. Its findings are supplemental and must be
reproduced locally.

## Fixed implementation boundary

Authorized source and compatibility paths:

- create `engine/physics/model_interface.py`;
- create `tests/test_c3_model_interface.py`;
- modify `engine/physics/__init__.py`;
- modify only the C2 aggregate-export assertion in
  `tests/test_c2_matrix_environment.py` if required;
- modify only the explicit truth-core shard list in
  `engine/project_verification.py` if the complete suite proves C3 is omitted;
- create `docs/verification/c3/**` during the gate.

No backend, migration, database, workbench, optimizer, headspace, thermo,
temporal, mixture, solvent-ledger, Laboratory Beta, generated scientific
artifact, or production-caller path is authorized.

## Fixed public API

`engine.physics.model_interface` will expose:

```text
ModelInterfaceContractError
ModelOperation
ModelFamily
ApplicabilityState
ModelAvailability
ModelResultStatus
ModelEvidenceClass
ModelSelector
DomainRange
ApplicabilityDomain
ApplicabilityContext
ApplicabilityResult
ModelInputReference
ModelRelease
VersionedModelRequest
ModelOutput
FallbackDisclosure
ModelComputation
VersionedModelResult
ModelComparisonResult
VersionedModelAdapter
VersionedModelRouter
```

Exact enum values are those in the accepted design. `ModelResultStatus` is
`COMPUTED` or `ABSTAINED`. `ModelAvailability` is `AVAILABLE` or `UNAVAILABLE`.
`ModelEvidenceClass` is closed as:

```text
THEORETICAL_BASELINE
MEASURED
EMPIRICAL
COMPUTATIONAL_IMPORT
LITERATURE_DERIVED
LEGACY_HEURISTIC
UNVALIDATED
```

## Shared validation rules

All persisted C3 contracts are frozen dataclasses with slots, exact-key parsers,
canonical `to_mapping()` output, and deterministic SHA-256 content hashes.

- strip and require nonblank text;
- require lowercase 64-character SHA-256 strings;
- allow Git commits only as lowercase 40- or 64-character hexadecimal strings;
- reject booleans as numbers and reject non-finite values;
- sort and deduplicate unordered string/enum collections;
- reject duplicate input references and duplicate model selectors;
- verify every supplied nested and top-level content hash;
- never convert units or infer a scientific domain;
- never query persistence or import a model implementation.

Schema tags:

```text
c3-model-selector-v1
c3-domain-range-v1
c3-applicability-domain-v1
c3-applicability-context-v1
c3-applicability-result-v1
c3-model-input-reference-v1
c3-model-release-v1
c3-versioned-model-request-v1
c3-model-output-v1
c3-fallback-disclosure-v1
c3-versioned-model-result-v1
c3-model-comparison-result-v1
```

### Task 1: Add applicability and immutable model-release contracts

**Files:**

- Create: `tests/test_c3_model_interface.py`
- Create: `engine/physics/model_interface.py`

- [ ] **Step 1: Write RED vocabulary, domain, and release tests**

Lock the six `ModelOperation` values, nine `ModelFamily` values, five exact
`ApplicabilityState` values, availability/result states, and seven evidence
classes.

Create fixtures for:

- an exact ideal-Raoult selector at model version `1.0.0`;
- typed concentration/temperature/pressure `DomainRange` objects;
- an `ApplicabilityDomain` spanning a finished-perfume matrix and sealed-vial
  environment, with identity/class/group, phase, required-property,
  training-domain, and failure-mode entries; and
- an available `ModelRelease` with all version/hash fields populated.

Tests must prove:

- `DomainRange` requires finite ordered bounds, a unit, and explicit inclusion
  flags;
- every required applicability field participates in the domain hash;
- domain collection ordering is canonical and duplicates fail;
- exact mapping round trips preserve hashes and reject nested tampering;
- release code/parameter/implementation/coefficient/decomposition/training/domain
  changes alter the release hash;
- an unavailable release requires a reason, uses `UNVALIDATED`, and cannot feed
  OAV screening;
- an available release rejects an unavailability reason;
- model and parameter versions, claim wording, and supported operations are
  nonblank and explicit; and
- answer-producing operations are distinct from router-only applicability and
  comparison operations.

- [ ] **Step 2: Run focused tests to prove RED**

```powershell
$env:NO_COLOR='1'; $env:TERM='dumb'
D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe -B -m pytest `
  -q -p no:cacheprovider --color=no `
  tests/test_c3_model_interface.py
```

Expected: collection fails because `engine.physics.model_interface` is absent.

- [ ] **Step 3: Implement the minimal Task 1 API**

Implement local strict helpers plus these contracts:

```text
ModelSelector:
  family; model_version; content_sha256

DomainRange:
  lower; upper; unit; lower_inclusive; upper_inclusive; content_sha256

ApplicabilityDomain:
  domain_id; domain_version;
  supported_identity_ids; supported_chemical_classes;
  supported_functional_groups; supported_matrix_stages; matrix_range;
  concentration_range; temperature_range; pressure_range;
  supported_phase_behaviors; supported_environment_kinds;
  required_properties; training_calibration_domain;
  known_failure_modes; content_sha256

ModelRelease:
  selector; parameter_set_version; code_commit;
  implementation_sha256; parameter_set_sha256;
  coefficient_set_sha256; decomposition_sha256; training_data_sha256;
  applicability_domain; supported_operations; availability;
  unavailable_reason; evidence_class; may_feed_oav_screening;
  permitted_claim_wording; forbidden_claim_wording; content_sha256
```

Use `CanonicalScope`, `ThermophysicalProperty`, `MatrixStage`, and
`ApplicationEnvironmentKind`; do not duplicate their vocabularies.

- [ ] **Step 4: GREEN, mutation-check, static-check, and commit**

Run the Task 1 tests. Temporarily remove one release hash input and prove the
corresponding mutation test fails; restore with `apply_patch` and rerun GREEN.
Run Ruff and basedpyright on the two Task 1 paths. Stage only those paths, inspect
the staged diff, run `git diff --cached --check`, and commit:

```text
feat(c3): add model applicability contracts
```

### Task 2: Add versioned request, output, result, and fallback envelopes

**Files:**

- Modify: `tests/test_c3_model_interface.py`
- Modify: `engine/physics/model_interface.py`

- [ ] **Step 1: Add RED request and result tests**

Create reusable C2 exact-matrix and sealed-vial context fixtures locally in the
C3 test. Do not import test helpers from another test module.

Add tests for:

```text
ApplicabilityContext:
  identity_ids; chemical_classes; functional_groups; concentration;
  phase_behavior; available_properties; training_calibration_tags;
  content_sha256

ApplicabilityResult:
  state; domain_sha256; request_sha256; reasons; missing_inputs;
  warnings; content_sha256

ModelInputReference:
  role; input_id; content_sha256

VersionedModelRequest:
  request_id; operation; requested_model; context;
  applicability_context; input_references; content_sha256

ModelOutput:
  quantity; unit; payload; content_sha256

FallbackDisclosure:
  requested_model; reason_unavailable; fallback_model;
  authority_downgrade; content_sha256

VersionedModelResult:
  status; operation; requested_model; bound_model; request; output;
  uncertainty; applicability; missing_inputs; warnings; evidence_class;
  may_feed_oav_screening; permitted_claim_wording;
  forbidden_claim_wording; fallback; content_sha256
```

Tests must prove:

- request mappings embed complete C2 formula/matrix/environment snapshots and
  repeated hashes;
- input references are canonical, unique by role/ID, and tamper-evident;
- all five applicability result shapes enforce their required reason,
  missing-input, and warning fields;
- output quantity/unit/payload are explicit and hash-bound;
- a computed result requires output plus `IN_DOMAIN` or
  `NEAR_DOMAIN_WITH_WARNING`;
- outside, insufficient, and unvalidated states reject a computed result;
- abstained results have no output and cannot feed OAV screening;
- result model, parameter set, code commit, inputs, context, uncertainty,
  applicability, missing inputs, warnings, evidence, OAV policy, and claim
  wording are visible in one mapping;
- a bound selector different from the request is invalid without a complete
  `FallbackDisclosure`;
- fallback disclosure selectors must match the result and differ from each
  other; and
- every parser rejects schema/key/hash/nested tampering.

- [ ] **Step 2: Prove RED and implement minimal envelopes**

Run `pytest -k 'request or result or fallback or applicability_result'` and
require failures for missing C3 types. Implement only the contracts and their
strict mapping behavior. Reuse `UncertaintyDescriptor` and `CanonicalScope`.

- [ ] **Step 3: GREEN, mutation-check, and commit**

Temporarily allow an outside-domain computed result and prove the guard test
fails; restore and rerun the complete C3 test file. Run Ruff, basedpyright, and
scoped mypy. Stage only the module and C3 test, inspect, and commit:

```text
feat(c3): add immutable model result envelopes
```

### Task 3: Enforce exact routing and mandatory abstention

**Files:**

- Modify: `tests/test_c3_model_interface.py`
- Modify: `engine/physics/model_interface.py`

- [ ] **Step 1: Add RED adapter/router tests**

Define a deterministic fake adapter only in the test file. It records
applicability and compute call counts and returns caller-selected applicability
states; it is not scientific evidence.

Add tests proving:

- `VersionedModelAdapter` is a runtime-checkable protocol;
- router construction rejects duplicate selectors even when one release differs
  only in coefficients, code, training data, or applicability;
- the same family with a new model version is accepted;
- an unknown model/version fails closed and never calls another adapter;
- each answer-producing method rejects a request naming another operation;
- unsupported operations fail closed;
- `evaluate_applicability()` resolves only the exact requested release;
- `OUTSIDE_APPLICABILITY_DOMAIN`, `INSUFFICIENT_INPUT`, and
  `MODEL_NOT_VALIDATED` return `ABSTAINED` without calling compute;
- an unavailable release returns `MODEL_NOT_VALIDATED` and never calls the
  adapter;
- `NEAR_DOMAIN_WITH_WARNING` computes only with its warning preserved;
- computed results carry the exact immutable release snapshot;
- adding a new release cannot change a prior result mapping/hash;
- no canonical router method creates a fallback disclosure; and
- `compare_models()` requires at least two unique explicit selectors, the same
  compared operation and C2 context hash, and returns complete result snapshots
  without ranking or selecting a winner.

- [ ] **Step 2: Implement protocol, computation payload, and router**

`ModelComputation` is a frozen runtime payload containing typed output,
uncertainty, and warnings. It has no scientific logic.

`VersionedModelAdapter` exposes immutable `release`,
`evaluate_applicability(request)`, and `compute(request, applicability)`.

`VersionedModelRouter` stores an immutable selector map and provides the six
named methods from the design. Router-created results never contain fallback.

`ModelComparisonResult` embeds a comparison ID, `compare_models` operation,
the compared operation, all complete results, and a content hash. It has no
score, rank, winner, average, or default model.

- [ ] **Step 3: GREEN and run two mutation checks**

Run the C3 test file. Then independently prove:

1. removing exact selector lookup makes the no-silent-fallback test fail; and
2. allowing compute after an outside-domain result makes the abstention/call-count
   test fail.

Restore both changes using `apply_patch` and rerun GREEN.

- [ ] **Step 4: Static-check and commit**

Run Ruff check/format, basedpyright, and scoped mypy. Stage only the C3 module and
test, inspect, and commit:

```text
feat(c3): enforce explicit model routing
```

### Task 4: Publish C3 exports and preserve C0-C2 compatibility

**Files:**

- Modify: `engine/physics/__init__.py`
- Modify: `tests/test_c3_model_interface.py`
- Modify only if required: `tests/test_c2_matrix_environment.py`
- Modify only if complete-suite failure proves omission:
  `engine/project_verification.py`

- [ ] **Step 1: Add RED public-boundary tests**

Import every fixed C3 public name from `engine.physics`. Assert the package
`__all__` is exactly the union of the frozen C1, C2, and C3 name sets, with no
duplicates. Change the C2 public test only from an exact combined allowlist to a
subset assertion; C3 owns the new exact combined allowlist.

Parse `model_interface.py` with `ast` and prove it imports no backend,
SQLAlchemy, persistence, workbench, optimizer, mixture, solvent-ledger,
headspace, thermo, temporal, or legacy estimator/model module. Prove it contains
no database, network, file-write, equation, or model-coefficient code.

- [ ] **Step 2: Implement explicit package exports**

Add explicit imports and `__all__` entries. Preserve every C1/C2 export and the
package statements that no equation is evaluated and no scientific release is
authorized.

- [ ] **Step 3: Run compatibility and complete-suite verification**

Run separately with non-PTY output, `NO_COLOR=1`, `TERM=dumb`, `--color=no`,
external pytest temp roots, and explicit timeouts:

```text
tests/test_c3_model_interface.py
tests/test_c2_matrix_environment.py
tests/test_c1_thermophysical_contracts.py
tests/test_c0_physical_model_inventory.py
complete root tests
```

If and only if the complete suite fails because the explicit truth-core shard
omits `tests/test_c3_model_interface.py`, add that one path to
`engine/project_verification.py`, rerun the invariant and complete suite, and
record the initial failure. Do not make unrelated verifier changes.

- [ ] **Step 4: Static, dependency, scope, and commit**

Run Ruff check/format, basedpyright, mypy, AST dependency checks, archive hash,
protected database hashes/quick checks, and the 429-file preservation replay.
Prove no forbidden path changed from the C3 phase parent. Stage only the export,
compatibility, test, module, and isolated verifier paths; inspect and commit:

```text
test(c3): publish model interface contracts
```

### Task 5: Seal the C3 executable gate

**Files:**

- Create: `docs/verification/c3/model_interface_gate.json`
- Create: `docs/verification/c3/model_interface_gate.md`
- Create mechanically: `docs/verification/c3/logs/**`
- Create after evidence commit: `docs/verification/c3/postcommit/**`

- [ ] **Step 1: Capture fresh verification**

Capture versions and separate stdout/stderr for focused C3, C2/C1/C0
compatibility, complete root pytest, Ruff check/format, basedpyright, mypy, and
dependency/scope validators. Preserve exit codes, timeouts, byte lengths, and
SHA-256 values. Empty stderr remains an explicit empty file. ANSI or credential
matches fail the authoritative log set.

- [ ] **Step 2: Reverify recovery and protected state**

Stream the C3 tar archive, verify member safety/uniqueness/content, and recheck all
429 preserved dirty/untracked files. Re-hash `perfume_chem.db` and
`data/perfumery_kb.db`; run read-only SQLite `quick_check`. Prove no migration,
database, scientific artifact, production caller, compatibility-model, or
legacy-implementation path changed.

- [ ] **Step 3: Write machine and human gate reports**

Use JSON schema `build-c3-model-interface-gate-v1`. Include exact enum/type
counts, implementation commits, test/static results, mutation evidence, explicit
selection/no-fallback/version-binding/abstention results, archive/protected-state,
scope, DeepLuna call/cost/fallback data, limitations, and a closed exit map with
`c4_open`.

The Markdown must state that C3 implements contracts/router enforcement only,
not Raoult, Henry, UNIFAC, COSMO-RS, partition, release, calibration, prediction
validation, Build C completion, or scientific release.

- [ ] **Step 4: Run one fresh exact-project DeepLuna final audit**

After a fresh `deepseek_check` returns `READY`, submit one read-only
`FLASH`/`NO_LUNA`/one-call audit over only C3 design, plan, implementation, tests,
and sanitized summaries. Sol reproduces every finding locally and remains final
authority. No secret, environment value, database content, unrelated dirty file,
or credential-bearing log may be transmitted.

- [ ] **Step 5: Commit evidence, verify the exact commit, and decide**

Stage only `docs/verification/c3/**`, inspect every path, run focused staged-tree
tests and `git diff --cached --check`, then commit:

```text
test(c3): seal model interface gate
```

Replay focused/compatibility/full/static/dependency/archive/protected-state/scope
checks against that exact commit. Commit postcommit receipts and the decision
separately:

```text
docs(c3): record model interface gate decision
```

C3 is `PASS` only if every result is current and green and the four authoritative
exit behaviors are proven. Otherwise record `BLOCKED/UNKNOWN`, keep `c4_open`
false, and do not begin C4.

## Inline execution decision

The user delegated implementation choices to Sol, prohibited permission pauses,
and prohibited Codex subagents. Execute this plan inline now; do not ask for an
execution-mode choice.
