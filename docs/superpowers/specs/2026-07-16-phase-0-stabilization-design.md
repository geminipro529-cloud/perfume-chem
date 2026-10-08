# Phase 0 Research Preview Stabilization Design

**Date:** 2026-07-16
**Status:** Approved for autonomous implementation
**Authority:** `docs/legacy-root/Perfume-Chem Completion Roadmap.txt`

## Objective

Establish an honest, reproducible Research Preview baseline before any later product phase is attempted. Phase 0 succeeds when the repository has one bounded verification command, branch-correct CI, stable scientific regression fixtures, and documented limitations that cannot be mistaken for validated predictions.

This design deliberately does not implement the roadmap's full 15 phases in one change. The roadmap itself makes Phase 0 a hard prerequisite, and the independent GPT-5.6 Sol Extra High review found that attempting the full product roadmap now would compound existing test, typing, packaging, and scientific-contract debt.

## Evidence And Literature

- GitHub recommends `setup-python`, explicit Python versions, dependency caching, and test artifacts for Python CI: <https://docs.github.com/en/actions/tutorials/build-and-test-code/python?learn=continuous_integration>
- GitHub workflow filters are branch-specific; checks that target a non-default branch can silently miss the actual release branch: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>
- PyPA's standard source/wheel path is `python -m build`, followed by installation/testing of the built distribution: <https://packaging.python.org/en/latest/flow/>
- Docker's GitHub Actions guidance treats image build provenance and reproducibility as release concerns, not substitutes for application smoke tests: <https://docs.docker.com/build/ci/github-actions/attestations/>
- The repository's scientific contract requires ppm, ODT, OAV, explicit evidence classes, and null outputs for unsupported predictions.

## Current-System Findings

1. CI watches `main`/`develop`, while the repository's release branch is `master`.
2. CI validates only the backend and does not gate the engine truth core, scientific audit, material data, knowledge rules, package, or Docker path.
3. A monolithic root test run is too slow and opaque for reliable diagnosis. Bounded shards with timeouts and JUnit output are required.
4. Full legacy Ruff and backend mypy currently contain substantial pre-existing debt. Pretending they are green would be less safe than defining a canonical blocking slice and recording the debt explicitly.
5. Several failing tests encode obsolete policy: non-hard creative guidance is intentionally advisory (`WARN`), while confidence and robustness remain hard gates.
6. `engine/emotional_mapping.py` contains a syntax defect that prevents whole-engine byte compilation.
7. Exact full-JSON golden snapshots would be brittle. Stable invariants, evidence classes, null semantics, and numerical tolerances are the correct regression surface.

## Chosen Architecture

### One Verification Entry Point

Extend the existing `scripts/pipeline_audit.py` with a `project-verify` subcommand. Do not create a new pipeline script.

The command delegates to a non-pipeline orchestration module, `engine/project_verification.py`, which defines named checks and engine test shards. It emits both human-readable and JSON summaries with:

- passed, failed, and skipped checks;
- known legacy limitations;
- scientific data coverage;
- golden output changes;
- Docker status;
- verification scope plus selected and omitted checks;
- an explicit completion gate.

Required checks fail the command. Only the full canonical scope can produce `PASS` or `PASS_WITH_SKIPS`; successful quick, selected, and custom scopes produce `NOT_EVALUATED`. Environment-dependent Docker checks may be skipped with a reason, never a false `PASS`.

### Deterministic Test Shards

Every collected root `tests/test_*.py` file belongs to exactly one engine shard:

- `truth-core`: arithmetic, workbench, contracts, and verifier behavior;
- `data-knowledge`: material records, ODT, decomposition, and rule validation;
- `gates-families`: family policy and pipeline gate behavior;
- `legacy`: remaining compatibility and workflow tests.

A manifest test prevents omissions and duplicate assignments.

### Golden Scientific Regression

Golden cases cover representative calculation contracts without claiming odor identity:

- direct aromachemical addition;
- diluted-stock equivalence;
- missing-density refusal;
- missing formula physical data and conditional ppm availability;
- tolerance-locked modeled vapor-ppm and OAV outputs;
- a covered natural using composite OAV;
- iris, leather, and citrus representative inputs;
- a solvent-bearing API case that exercises the percentage adapter;
- a real restricted inventory material at its stored limit that remains explicitly unverified when versioned regulatory evidence is unavailable;
- unsupported longevity, sillage, and receptor outputs remaining null.

Assertions use exact values only for arithmetic identities and tolerances for modeled floating-point outputs. Full response snapshots are prohibited.

### CI Contract

CI targets `master`, pull requests, and manual dispatch. It exposes explicit jobs for:

- backend lint, scoped typecheck, and tests;
- engine compile/lint, scoped typecheck, and sharded tests;
- scientific audit;
- material-data validation;
- knowledge-rule validation;
- golden formula regression;
- package build and installed-wheel smoke test;
- Docker build and health smoke test.

Canonical lint/typecheck slices are blocking. Known legacy debt is documented and must not expand silently.

## Scientific Boundaries

1. Composite OAV for naturals is headspace/perceptibility evidence. It is not regulatory composition data.
2. OAV supports perceptibility reasoning, not pleasantness, identity, longevity, or consumer preference.
3. Temporal, diffusion, longevity, sillage, receptor, and emotion outputs remain advisory or null unless their evidence requirements are met.
4. IFRA conclusions require category, concentration basis, source version, and constituent/allergen composition. Missing evidence produces `unverified`, not `safe`.
5. Golden fixtures guard software behavior and truth-labeling. They are not sensory validation.

## Completion Criteria

Phase 0 is complete when:

1. the roadmap is committed as project authority;
2. the deterministic verifier passes all required local checks;
3. all root tests are assigned to exactly one bounded shard;
4. CI targets the real release branch and contains all required jobs;
5. golden scientific invariants pass;
6. package and Docker paths are either verified or explicitly skipped with reasons;
7. README and scientific docs state the Research Preview boundary;
8. the implementation is committed and pushed to the existing public draft PR.
