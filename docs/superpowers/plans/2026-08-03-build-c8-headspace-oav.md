# Build C8 Headspace OAV and Mixture-Interaction Implementation Plan

> **For agentic execution:** REQUIRED SUB-SKILL: use
> `superpowers:executing-plans` inline. Codex subagents are prohibited for this
> project; bounded DeepLuna Fast work remains read-only and advisory.

**Goal:** Add a deterministic, fail-closed C8 authority contract that keeps
physical gas concentration, threshold-screening OAV, mixture-interaction
evidence, sensomics evidence, and unsupported sensory claims separate.

**Architecture:** One pure module under `engine.physics`, exported explicitly
and included in project verification. It consumes immutable evidence records,
performs only bounded OAV arithmetic and authorization checks, applies no
interaction multiplier, and has no production caller or persistence effect.

**Tech Stack:** Python 3.11 frozen/slotted dataclasses, enums, canonical JSON
SHA-256 hashing, pytest, Ruff, mypy, basedpyright, PowerShell non-PTY evidence
capture, Git exact-commit replay.

---

**Authoritative parent:**
`cae5b2652e58181a95f4dd1618057041b14d645f`

**Verified prewrite archive:**
`D:\.backups\perfume-chem\build-c8-prewrite-20260803T043741+0700.tar`
with SHA-256
`09fc1acf0d90f586e420f2eff5e9534f823f0d81292d4ba792eaefd3de9c5f5f`.

## File map

- `engine/physics/headspace_oav.py`: all C8 evidence, arithmetic,
  interaction-authorization, sensomics, and claim-boundary contracts.
- `tests/test_c8_headspace_oav.py`: complete C8 RED/GREEN contract and
  dependency isolation.
- `engine/physics/__init__.py`: explicit C8 package exports only.
- `tests/test_c3_model_interface.py`: package-export union assertion.
- `engine/project_verification.py`: C8 truth-core and static-check inventory.
- `docs/verification/c8/**`: generated verification and exact-replay evidence.

### Task 1: Freeze the design checkpoint

**Files:**

- Create: `docs/superpowers/specs/2026-08-03-build-c8-headspace-oav-design.md`
- Create: `docs/superpowers/plans/2026-08-03-build-c8-headspace-oav.md`

- [ ] Verify HEAD equals the authoritative C7 decision commit and the index is
  empty.
- [ ] Run `git diff --check` on both documents and scan them for unresolved
  markers, contradictory claim lists, and any legacy import proposal.
- [ ] Stage only the two C8 documents and commit
  `docs(c8): define headspace OAV authority boundary`.

### Task 2: Write the complete RED contract

**Files:**

- Create: `tests/test_c8_headspace_oav.py`

- [ ] Add import and exact `PUBLIC_C8_NAMES` assertions for the frozen public
  API.
- [ ] Add tests for `EvidenceReference`, `GasPhaseContext`, and
  `BoundedQuantity`, including non-finite, non-positive, partial-bound, unknown
  field, duplicate, and hash-tamper cases.
- [ ] Add measured/predicted gas-evidence tests proving model fields are
  mutually exclusive and predicted evidence carries explicit domain state.
- [ ] Add threshold tests for kind, authority, method, assessor population,
  context, uncertainty, and strict mappings.
- [ ] Add OAV tests for exact identity/context/unit matching, direct and
  peer-reviewed threshold authority, out-of-domain abstention, missing-bound
  abstention, conservative interval propagation, and below/above/straddling
  classifications.
- [ ] Assert every abstained OAV is answerless and every computed result states
  that OAV is not intensity, percent contribution, similarity, or preference.
- [ ] Add interaction tests for all six kinds, required concentration/matrix/
  method/population/model/source/uncertainty/range fields, strict mappings, and
  deterministic hashes.
- [ ] Add tests proving uncalibrated-generic and observation-only records reject
  numerical effects and cannot authorize an adjustment.
- [ ] Add calibrated authorization tests for exact identity, context, target,
  unit, and applicable-range matching without applying a multiplier.
- [ ] Add sensomics tests for the exact eight-stage order, contiguous completed
  prefix, evidence on completed stages, candidate-prioritization gate, and
  complete-sequence causal/recombination gates.
- [ ] Add all five permitted and eight always-withheld claim-boundary cases.
- [ ] Add an AST dependency test forbidding legacy OAV/intensity, heuristic
  headspace, synergy, database, backend, pipeline, optimizer, production, C9,
  and sensory-scoring imports.
- [ ] Run:

  ```powershell
  & D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --color=no tests/test_c8_headspace_oav.py
  ```

  Expected RED result: collection fails with `ModuleNotFoundError` for
  `engine.physics.headspace_oav`, with separate empty stderr.
- [ ] Commit only the RED test as
  `test(c8): freeze headspace OAV and interaction contract`.

### Task 3: Implement evidence and OAV primitives

**Files:**

- Create: `engine/physics/headspace_oav.py`
- Test: `tests/test_c8_headspace_oav.py`

- [ ] Implement the contract error, exact helper validators, closed enums,
  constants, and stable-hash helper.
- [ ] Implement `EvidenceReference`, `GasPhaseContext`, and `BoundedQuantity`
  with strict mapping round trips and canonical content hashes.
- [ ] Run only the primitive/hash/mapping tests until green.
- [ ] Implement `GasConcentrationEvidence` and `OdorThresholdEvidence` with
  origin- and authority-specific structural rules.
- [ ] Run only the gas/threshold evidence tests until green.
- [ ] Implement `HeadspaceOAVAssessment` and `calculate_headspace_oav` with the
  seven preconditions and conservative ratio bounds from the design.
- [ ] Run only the OAV tests until green. Do not implement intensity,
  contribution, similarity, threshold shifting, or implicit unit conversion.

### Task 4: Implement interaction evidence and authorization

**Files:**

- Modify: `engine/physics/headspace_oav.py`
- Test: `tests/test_c8_headspace_oav.py`

- [ ] Implement immutable concentration, applicable-range, numerical-effect,
  evidence, request, and decision records.
- [ ] Enforce exact identity coverage, matrix/context binding, range units,
  source/uncertainty requirements, and calibration-state rules in constructors
  and parsers.
- [ ] Implement `authorize_interaction_adjustment` as an authorization check
  only. `WITHHELD` must contain no numerical effect; `AUTHORIZED` may expose the
  bounded calibrated effect but must not change concentration or intensity.
- [ ] Run all interaction tests until green.

### Task 5: Implement the sensomics and claim boundaries

**Files:**

- Modify: `engine/physics/headspace_oav.py`
- Test: `tests/test_c8_headspace_oav.py`

- [ ] Implement `SensomicsStageRecord`, `SensomicsProgram`,
  `SensomicsAssessment`, and `evaluate_sensomics_claim` with the exact ordered
  stage constant and contiguous-prefix rule.
- [ ] Implement `C8ClaimDecision` and `evaluate_c8_claim` from the exact five
  permitted and eight withheld claim constants.
- [ ] Run sensomics and claim-boundary tests, then the complete C8 focused file.

### Task 6: Export and register C8

**Files:**

- Modify: `engine/physics/__init__.py`
- Modify: `tests/test_c3_model_interface.py`
- Modify: `engine/project_verification.py`
- Test: `tests/test_c8_headspace_oav.py`

- [ ] Export the exact C8 public set without colliding with C1-C7 names.
- [ ] Add `PUBLIC_C8_NAMES` to the package-union assertion while preserving all
  prior exports.
- [ ] Add the C8 test to the truth-core shard and the C8 module/test to focused
  Ruff and mypy paths.
- [ ] Run C8 focused and C3 compatibility tests.
- [ ] Run Ruff format, Ruff check, basedpyright, and mypy on exactly the C8 phase
  files; fix only C8-owned findings.
- [ ] Commit implementation as
  `feat(physics): add C8 headspace OAV authority contracts`.

### Task 7: Mutation evidence

**Files:**

- Generated evidence only under: `docs/verification/c8/logs/mutation/`

- [ ] Record the source SHA-256 before mutation.
- [ ] Mutate predicted-domain/context compatibility enforcement; run the exact
  guard test and require exit 1.
- [ ] Restore bytes; run the guard test and require exit 0.
- [ ] Repeat for uncertainty-bound enforcement, generic numerical-effect
  withholding, and unsupported-claim withholding.
- [ ] Require zero timeouts, separate stdout/stderr, empty stderr, four killed
  mutations, four restored passes, and source SHA-256 equality before/after.

### Task 8: Local verification matrix

**Files:**

- Generated evidence only under: `docs/verification/c8/logs/final/`

- [ ] Capture C8 focused; C7, C6, C5, C4, C3, C2, C1, and C0 compatibility;
  C0 inventory verifier; and the complete root suite.
- [ ] Capture the isolated C8 forbidden-dependency test.
- [ ] Capture `pip check`, Ruff check/format, basedpyright, and mypy.
- [ ] Verify exact phase scope from the C7 decision parent, with no production,
  database, migration, scientific-artifact, or legacy OAV/synergy path.
- [ ] Reverify the C8 recovery archive.
- [ ] Snapshot protected database/WAL/SHM files before and after and run
  immutable database quick checks.
- [ ] Re-run the C5 actual-data boundary and require
  `BLOCKED_PENDING_DATA` with no instrument data.
- [ ] Scan every log as strict UTF-8 with zero ANSI and zero credential-shaped
  matches.
- [ ] Fail on any timeout, nonzero exit, unexpected stderr, count drift,
  protected-state drift, or forbidden path.

### Task 9: DeepLuna Fast audit and Sol reconciliation

**Files:**

- Generated C8 audit evidence only.

- [ ] Run a fresh exact-project `deepseek_check`.
- [ ] Only when `READY`, submit one bounded read-only audit using `FLASH`,
  `NO_LUNA`, one provider call maximum, and no Codex/Luna/GLM fallback.
- [ ] Exclude secrets, environment values, databases, unrelated dirty files,
  architecture decisions, scientific promotion, and final acceptance.
- [ ] Sol must inspect every finding and mechanically reproduce every
  gate-bearing claim locally.
- [ ] Capture settled postflight `READY`, queue/active lanes zero, reservations
  zero, reconciled accounting, and no fallback route.

### Task 10: Seal and replay the C8 gate

**Files:**

- Create: `docs/verification/c8/headspace_oav_gate.json`
- Create: `docs/verification/c8/headspace_oav_gate.md`
- Create: `docs/verification/c8/logs/log-manifest.json`
- Create: `docs/verification/c8/postcommit/**`

- [ ] Generate and validate C8 evidence with decision
  `PENDING_EXACT_COMMIT_REPLAY` and `c9_open=false`.
- [ ] Commit only `docs/verification/c8/**` as the immutable evidence commit.
- [ ] At that exact commit and an empty index, replay the bounded matrix with
  non-PTY execution, explicit timeouts, and separate stdout/stderr.
- [ ] Generate replay manifest, exact-commit receipt, and final decision
  receipt. Preserve any failed harness attempt rather than erasing it.
- [ ] Set `decision=PASS` and `c9_open=true` only when every replay job passes
  with zero timeout/stderr/ANSI/credential/protected-state issue.
- [ ] Commit only the C8 postcommit decision evidence and run the final scope
  and evidence validators.

C9 may begin only when the C8 final decision commit is the direct child of the
C8 evidence commit and every postcommit validator passes.
