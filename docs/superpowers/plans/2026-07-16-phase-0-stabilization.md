# Phase 0 Research Preview Stabilization Plan

**Design:** `docs/superpowers/specs/2026-07-16-phase-0-stabilization-design.md`
**Roadmap:** `docs/legacy-root/Perfume-Chem Completion Roadmap.txt`

## Task 1: Lock The Contract With Failing Tests

Create regression tests before implementation for:

1. whole-engine byte compilation;
2. CI branch and required-job contract;
3. complete, non-overlapping engine test-shard assignment;
4. verifier pass/fail/skip aggregation and stable JSON shape;
5. golden workbench arithmetic, evidence labels, composite natural OAV, refusal, and null semantics.

Run only the new tests and record the expected failures.

## Task 2: Repair Proven Baseline Defects

Make the minimum production/test corrections supported by evidence:

1. remove the orphaned malformed mapping fragment in `engine/emotional_mapping.py`;
2. remove the unused truth-core import reported by the canonical Ruff slice;
3. update family tests to assert advisory `WARN` plus preserved `original_status=FAIL`;
4. update the optimizer test so an advisory brief warning does not trigger an automatic rewrite;
5. correct the Indole science-KB test to inspect its selected notes column.

Run each corrected test file directly before proceeding.

## Task 3: Implement Project Verification

Add `engine/project_verification.py` and wire `project-verify` into `scripts/pipeline_audit.py`.

The verifier will:

- define named check specifications;
- use `.venv` tools locally when present and normal executable names in CI;
- run subprocesses with bounded timeouts;
- support `--quick`, repeated `--only`, `--include-docker`, and `--json`;
- save a machine-readable report under `verification_runs/`;
- record required failures and optional skips separately;
- expose the shard manifest for tests and CI.

Unit tests will inject a fake command runner. No verifier unit test may recursively launch the repository's complete suite.

## Task 4: Add Golden Scientific Cases

Create a compact JSON fixture and test module. Use only inventory-backed materials and existing workbench APIs.

Assert:

- mass/volume arithmetic and ppm conversion;
- diluted-stock active amount equivalence;
- explicit refusal when density is required but absent;
- ODT/OAV fields and evidence classes;
- composite natural OAV provenance;
- explicit solvent handling;
- unsupported longevity, sillage, receptor, and regulatory claims remain null/unverified;
- modeled values stay within documented tolerances.

Do not snapshot timestamps, ordering that is not contractual, or the entire response.

## Task 5: Replace CI With Phase 0 Gates

Update `.github/workflows/ci.yml` to target `master`, all pull requests, and manual dispatch.

Add the required named jobs and JUnit artifact upload for engine shards. Use Python 3.11 in CI, standard package caching, explicit timeouts, and `python -m build` for distribution artifacts. Keep scoped lint/typecheck commands visible so the legacy-debt boundary cannot be mistaken for full coverage.

## Task 6: Document Research Preview Boundaries

Update README and the scientific/model documentation with:

- the one-command verifier;
- meaning of `PASS`, `PASS_WITH_SKIPS`, `NOT_EVALUATED`, and `FAIL`;
- canonical versus legacy-debt checks;
- the composite-OAV/regulatory-composition distinction;
- unsupported-output null policy;
- the Phase 0 completion gate and deferred roadmap phases.

Ignore generated verification reports while retaining committed golden fixtures.

## Task 7: Verify And Publish

Run, in order:

1. new regression tests;
2. corrected focused tests;
3. canonical Ruff and mypy checks;
4. every engine shard separately;
5. backend lint, scoped typecheck, and tests;
6. scientific/data/knowledge/golden checks;
7. source/wheel build and installed-wheel smoke test;
8. Docker build and health smoke test when Docker is available;
9. `project-verify --json` as the final evidence record.

Review the diff for unrelated changes, commit intentionally, push the current public branch, and refresh the existing draft PR description if credentials permit.
