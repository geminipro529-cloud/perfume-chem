# Repository verification comparison — 2026-09-09

**Full verifier executed; completion gate FAIL. Deep Plane remains disabled by default. Nothing was merged, committed, or published.**

## Executed checks

The existing canonical project verifier was run with the existing Python environment, first with --quick and then without --quick. Build prerequisite passed (build 1.5.0). A detached clean-base worktree was created at the integration base commit, with LF checkout settings passed only to that creation command; no saved Git settings were changed. The same full verifier ran there to provide a control.

| Run | Check groups passed | Failed | Optional Docker groups skipped | Result |
|---|---:|---:|---:|---|
| Integration quick | 5 | 5 | 0 | FAIL |
| Integration full | 8 | 11 | 2 | FAIL |
| Clean-base full | 8 | 11 | 2 | FAIL |

Group counts are not test counts, and matching group totals do not mean identical causes. The canonical full verifier uses its explicit shard manifest; it is not an exhaustive pytest run over every repository file. The earlier 255-test integration run remains separate evidence and is not added to these overlapping counts.

Passed full groups: engine compilation, canonical engine lint/typecheck, backend lint, golden formula regression, golden fixture lock, package build, and installed-wheel smoke test.

## Paired engine test results

| Shard | Base failures / errors | Integration failures / errors |
|---|---:|---:|
| Truth core | 0 / 2 | 0 / 2 |
| Data and knowledge | 46 / 4 | 48 / 4 |
| Gates and families | 56 / 0 | 12 / 0 |
| Legacy | 3 / 26 | 2 / 26 |

The truth-core shard stops at collection errors, so this does not establish that its uncollected tests pass. The clean base also has stale inventory authority which prevents some tests from reaching later assertions. A test failing in both checkouts is not, by itself, proof of an identical cause.

Exactly two integration failures have a comparable passing test on the clean base:

1. **Orris metadata assertion:** the dated test requires a label starting with 30%; the integrated, versioned stock authority states **9% w/w in DEP**. The authority must not be reverted to satisfy an obsolete assertion.
2. **Live OAV-coverage assertion:** the threshold is greater than 85%. Clean base: 207 supported, 35 unknown out of 242 materials (85.537%). Integration: 204 supported, 42 unknown out of 246 (82.927%). This is a real coverage gap in the integrated inventory population; it does not justify inventing missing physical data or lowering the threshold without reviewing the contract.

## Confirmed older or environment failures

- The original canonical checkout contains data/perfumery_kb.db (2,084,864 bytes), but Git ignores it. It is absent in both new worktrees. Read-only database tests consequently fail. No database was copied, rewritten, or repaired during verification.
- Both newly created backend environments cannot import pytest_asyncio. Both backend typechecks report **142 errors in 19 files**. These are not corrected by the engine integration tests.
- Both truth-core runs hit the same Python 3.14 / protobuf native-extension import error through tracing. No environment dependency was upgraded or downgraded to hide it.
- Black Agarwood and Castoreum stock assertions, other historical stock assumptions, missing preflight monkeypatch targets, and natural-coverage expectations also fail on the clean base. Some other errors remain masked by the base inventory-authority failure.
- Six DPP historical formula artifacts are already STALE on the base and remain so in the integration worktree.

## Artifact writer/validator defect

The unchanged scripts/formula_release_gate.py includes g15_parent_formula_definitions in the writer's analysis-input hash, but the validator recomputes that hash without the field. A read-only probe against the clean base reproduces unequal writer/validator hashes even with an empty parent list. The script contents match between the two worktrees after line-ending normalization.

This inherited defect is exposed by integration CLI persistence tests. The imported AHS v2 Neat Neroli historical fixture additionally fails artifact binding and is labelled TAMPERED by the validator because of hash inconsistency; that label is not evidence of malicious alteration. No artifact was repinned, regenerated, or promoted during verification.

## Preservation and verification side effects

All 48 entries from the inventory and opt-in checkpoint manifests still match their hashes. No implementation files were edited during this verification phase. A clean detached baseline checkout, local reports, test temporary/cache output, package wheels, and backend Poetry environments were created by the verification workflow. Original source checkouts remain in place.

Baseline: D:/chatbots/perfume-chem-verification-baseline-20260909
Base commit: 45cd79cd01b6ac30c8acc5f2875bc272e1f3e488

## Recommended repair sequence

1. Make the test environment reproducible: validate and stage the required ignored database as an explicit local dependency; resolve backend test dependencies and the tracing/protobuf compatibility issue without silently changing the shared environment.
2. Repair the artifact writer/validator contract with version-aware tests preserving parent lineage. Do not relabel stale history as fresh evidence.
3. Update obsolete stock assertions against the actual current authority. Keep missing OAV/composite information unknown until supported; investigate the expanded inventory's coverage gap separately.
4. Address remaining backend/default-caller failures, rerun the affected checks, then rerun the full verifier before considering production admission.

These are findings and repair priorities, not completed repairs. Production activation, release, and publication remain blocked.

## Evidence

- Integration quick: output/verification/deep-plane-integration-quick-20260909.json
- Integration full: output/verification/deep-plane-integration-full-20260909.json
- Clean-base full: D:/chatbots/perfume-chem-verification-baseline-20260909/output/verification/base-revision-full-20260909.json
- Paired engine test XML: verification_runs/engine-*.xml in each worktree
- Targeted clean-base control: D:/codex-preservation/perfume-chem-20260909/verification-baseline-focused.xml
- Machine-readable summary and report hashes: repository_verification_comparison_20260909.json
