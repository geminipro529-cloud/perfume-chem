# Build C7 Lot-Aware Natural Materials Implementation Plan

> Execute with the repository Python 3.11 environment, non-PTY capture,
> disabled ANSI output, separate stdout/stderr, explicit timeouts, and an empty
> index at every replay gate. Preserve all unrelated tracked and untracked work.

**Goal:** Add a deterministic, fail-closed C7 natural-lot contract that keeps
exact-lot, supplier-batch, literature-proxy, generic-proxy, unresolved,
regulatory, olfactory, and identity/authenticity meanings separate.

**Architecture:** One pure module under `engine.physics`, exported explicitly
and included in repository verification. No production caller, database,
migration, legacy-stub edit, generic-profile edit, or C8 computation.

**Authoritative parent:**
`aa2276fbf0ecf15e59565ba2f2f586869ffbfe09`

**Verified prewrite archive:**
`D:\.backups\perfume-chem\build-c7-prewrite-20260803T031627+0700.tar`
with SHA-256
`0d71b7e4d84041488789f4184ec3daf7faf266651674524faff76701a265136a`.

## Task 1: Freeze design and phase scope

Files:

- add `docs/superpowers/specs/2026-08-03-build-c7-natural-lots-design.md`;
- add this plan.

Checks:

- confirm HEAD is the C6 decision commit;
- confirm the index contains only the two C7 documents;
- run `git diff --check` for the documents;
- commit the design checkpoint.

## Task 2: Write the complete RED contract

Files:

- add `tests/test_c7_natural_lots.py`.

Test groups:

1. closed vocabularies and strict helper behavior;
2. exact lot, source document, and analytical-run identity;
3. all nine constituent bases, calibration state, uncertainty, LOD/LOQ, and
   censoring;
4. explicit unresolved disclosure and non-closing named totals;
5. profile authority constraints and deterministic hash identity;
6. six-level precedence, exact match, fallback, ambiguity, and abstention;
7. separate olfactory, regulatory, and authenticity projections;
8. basis-compatible authenticity comparison;
9. immutable aging snapshots and hash-chain validation;
10. strict mapping round trips and tamper rejection;
11. no legacy/backend/database/OAV/sensory imports.

Run the focused file and record the expected collection/import failure. Commit
only the RED test.

## Task 3: Implement identity and observation primitives

Files:

- add `engine/physics/natural_lots.py`.

Implement first:

- contract error and closed vocabularies;
- finite/text/date/datetime/hash/canonicalization helpers;
- `SourceDocumentReference` and `AnalyticalRunReference`;
- `NaturalMaterialLot`;
- `ConstituentObservation`;
- `UnresolvedFractionObservation` and
  `UnresolvedFractionDisclosure`.

Run only the corresponding focused test groups until green. Keep original
values and bases unchanged; do not add concentration conversion helpers.

## Task 4: Implement profiles and precedence

Implement:

- `NaturalCompositionProfile`;
- `NaturalCompositionRequest`;
- `NaturalCompositionSelection`;
- `select_natural_composition`.

Enforce exact authority-level bindings and deterministic ambiguity/abstention.
Expose named totals by original basis without normalization. Run profile and
selection tests after each slice.

## Task 5: Implement projections, authenticity, and aging

Implement:

- projection entry/result records and `build_natural_projection`;
- authenticity reference/assessment records and
  `assess_authenticity_profile`;
- `LotAgingObservation` and `validate_aging_series`.

Regulatory projection must be answerless unless all exact authority,
completeness, calibrated-mass-fraction, and unresolved-review gates pass.

## Task 6: Export and register C7

Files:

- modify `engine/physics/__init__.py`;
- modify `tests/test_c3_model_interface.py`;
- modify `engine/project_verification.py`.

Actions:

- export the exact C7 public set;
- add `PUBLIC_C7_NAMES` to the union assertion;
- add the C7 test to the truth-core shard;
- add the C7 module/test to focused Ruff and mypy verification paths;
- preserve the existing package disclaimer and all C0-C6 exports.

Run C7 focused plus C3 compatibility. Commit implementation only after these
tests pass.

## Task 7: Local verification matrix

Capture with explicit timeouts:

- C7 focused tests;
- C6, C5, C4, C3, C2, C1, and C0 compatibility tests;
- C0 inventory verifier;
- complete root tests;
- C7 no-legacy/backend/database/OAV/sensory dependency test;
- `pip check`;
- Ruff check and format check for all C7 phase files;
- basedpyright and mypy for the C7 phase files;
- exact phase-scope verification;
- recovery-archive re-verification;
- protected database/WAL/SHM before/after snapshots and immutable quick checks;
- C5 actual-data boundary retention;
- UTF-8, ANSI, and credential-shaped log scan.

Any timeout, stderr output, count drift, protected-state drift, forbidden path,
or unverified raw log fails closed.

## Task 8: Mutation evidence

Use byte-preserving source restoration. Kill and restore four mutations:

1. permit normalized area percent to satisfy an absolute-concentration basis;
2. remove exact lot matching from precedence selection;
3. permit a profile without unresolved disclosure;
4. permit a relative/generic profile to emit a regulatory answer.

Record each caught failure and restored pass, then verify the source SHA-256 is
identical before and after.

## Task 9: DeepLuna Fast audit and Sol reconciliation

Run a fresh exact-project `deepseek_check`. Only when READY, submit one bounded
read-only Fast audit over the exact implementation and captured evidence with:

- route `FLASH`;
- fallback policy `NO_LUNA`;
- one provider call maximum;
- no Codex, Luna, or GLM workers;
- no secret, environment, database, inventory-comment, or unrelated-file read;
- no architecture, scope, scientific promotion, or acceptance decision.

Sol will inspect every finding and mechanically reproduce all gate-bearing
claims locally. Capture a settled READY postflight with zero reservations.

## Task 10: Seal and replay the C7 gate

Generate C7 evidence with decision `PENDING_EXACT_COMMIT_REPLAY` and `c8_open`
false. Validate and commit only `docs/verification/c7/**`.

At that exact evidence commit, with the dirty worktree preserved and index
empty, replay the bounded matrix. Generate replay manifest, exact-commit
receipt, and final decision receipt. Change the gate to PASS and `c8_open=true`
only if every replay job passes with zero timeout/stderr/secret/ANSI/protected
state issue. Commit only the C7 decision evidence.

C8 may begin only after the final C7 decision commit has the exact evidence
commit as its direct parent and the postcommit validator passes.
