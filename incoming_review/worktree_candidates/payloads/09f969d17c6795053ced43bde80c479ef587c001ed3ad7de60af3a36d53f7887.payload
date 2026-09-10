# PERFUME-CHEM OPERATIONAL SMOKE TEST ADDENDUM

**Plan ID:** PC-SMOKE-PRADA-C1-20260806  
**Insert after:** recovery verification and input/inventory locks, before governing-formula hash work and reviewer delegation.  
**Project:** `perfume-chem`  
**Target data:** recovered current-version Prada L’Homme EDT C1 artifacts.

## 1. Purpose

Run one bounded, isolated, non-mutating operational smoke test to determine how the recovered Prada C1 program actually connects to the current `perfume-chem` repository.

The smoke test answers only:

1. Can the repository’s declared Python entrypoints import?
2. Can the canonical workbench be instantiated using a repository-supported fixture/configuration?
3. Can at least one documented workbench operation complete?
4. Can the standalone reconstruction CLI start and expose its actual commands?
5. Can one existing Prada formula or fixture enter the existing validation/gate-dispatch path?
6. Can the FastAPI application start on localhost and expose its actual documented routes, when an API entrypoint exists?
7. Is there an existing supported ingestion path from the recovered C1 XLSX workbook into the project’s FormulaState/formula-markdown/workbench path?
8. Does the repository remain unchanged after the test?

This smoke test is NOT:

- a D3 engine requalification;
- a reference-harness rerun;
- an EQ-15 stochastic-integration run;
- a full test-suite run;
- a formula revision;
- a screen-package modification;
- a physical smell test;
- an analytical validation;
- a similarity pass;
- a Phase-G authorization.

The prior D3 state remains unchanged unless a separately authorized qualification pass later proves otherwise:

`PARTIALLY QUALIFIED AT GATE-DISPATCH ONLY`

The smoke test may prove that a route starts and returns an honest state. It may not convert that observation into `END_TO_END_QUALIFIED`.

## 2. Repository and write boundary

1. Resolve the actual Git root with the repository’s own tooling. The historical candidate path is `D:\chatbots\perfume-chem`, but do not assume it when Git reports another root.
2. Record:
   - absolute repository root;
   - current branch;
   - HEAD commit;
   - Git status;
   - tracked modifications;
   - untracked files;
   - Python version;
   - active virtual environment;
   - Node/package-manager versions when present;
   - detected lockfiles and project manifests.
3. Create a new run directory only:

   `runs/Prada_LHomme_C1_Program_Merge_<timestamp>/smoke_test/`

4. Direct all temporary files, databases, caches, bytecode, logs, and generated outputs into that run directory or the operating-system temporary directory.
5. Set `PYTHONDONTWRITEBYTECODE=1` where practical and redirect pytest/cache paths away from the source tree.
6. Do not modify:
   - `engine/`;
   - `backend/`;
   - `frontend/`;
   - `scripts/`;
   - `tests/`;
   - `configs/`;
   - `data/`;
   - `formulas/`;
   - project lockfiles;
   - the canonical database;
   - recovered source workbooks.
7. Do not run formatters, migrations against the canonical database, package upgrades, auto-fix commands, or code-generation commands.
8. If dependencies are missing, first report the active-environment failure. An isolated disposable environment may be created only from an exact repository lockfile and only outside the tracked source tree. Never upgrade or rewrite the project environment during this smoke test.

## 3. Stage SMK-00 — command and architecture discovery

Read the actual repository before running commands.

Inspect, when present:

- `README.md`;
- `AGENTS.md`;
- `pyproject.toml`;
- `pytest.ini`;
- `tox.ini`;
- `Makefile`;
- `requirements*.txt`;
- `poetry.lock`;
- `uv.lock`;
- `package.json` and package-manager lockfiles;
- backend/app startup documentation;
- tests that exercise the canonical workbench, reconstruction CLI, gates, and API.

Look for these candidate surfaces, but verify their existence and current signatures rather than assuming them:

- `engine.workbench.PerfumeWorkbench`;
- `engine/reconstruction/`;
- `scripts/reconstruct.py`;
- `engine/pipeline/gates.py`;
- `engine/pipeline/formula_state.py`;
- `engine/families/registry.py`;
- `configs/module_envelopes.json`;
- `configs/reconstruction/prada_lhomme_envelope.json`;
- `data/reconstruction/manifest.sha256`;
- `formulas/Prada_LHomme_From_Scratch_30mL_EdP.md`;
- Prada reconstruction fixtures under `tests/fixtures/reconstruction/`;
- the actual FastAPI application entrypoint.

Create:

- `SMOKE_COMMAND_DISCOVERY.json`
- `SMOKE_COMPONENT_MAP.json`

For every discovered command or entrypoint record:

- source file;
- exact symbol or script;
- documented invocation;
- required inputs;
- write behavior;
- expected output;
- whether it is safe for this smoke test.

Do not invent a command merely because it is conventional.

## 4. Stage SMK-01 — environment and import smoke

Run the smallest documented environment checks.

Required attempts:

1. Import the top-level `engine` package.
2. Import `engine.workbench.PerfumeWorkbench` when present.
3. Import the formula-state and gate modules discovered in SMK-00.
4. Import the reconstruction package when present.
5. Import the FastAPI app module when present, without starting it yet.

Capture for every attempt:

- exact command;
- working directory;
- environment;
- exit code;
- stdout;
- stderr;
- duration;
- traceback when present.

Do not modify code to make an import succeed.

## 5. Stage SMK-02 — canonical workbench smoke

When `engine.workbench.PerfumeWorkbench` exists:

1. Inspect its current constructor signature and documented initialization path.
2. Locate an existing repository fixture, test helper, or documented minimal configuration.
3. Instantiate the workbench using only that supported path.
4. Use a temporary database or transaction rollback where persistence is required.
5. Enumerate its actual public operations.
6. Run at least one non-mutating analysis operation using an existing repository fixture.
7. When a documented exact bottle/addition operation exists, run one tiny fixture-backed arithmetic call and capture the result.
8. Preserve evidence labels exactly as returned.

Candidate historical operation names include `analyze` and `calculate_addition`, but use them only when the current object actually exposes them.

Pass condition for this stage:

- the canonical workbench imports;
- it can be instantiated by a repository-supported path;
- at least one real operation returns a structured result;
- no canonical database or source file changes.

When instantiation requires undocumented or unavailable configuration, report:

`WORKBENCH ENTRYPOINT PRESENT / RUNTIME INITIALIZATION BLOCKED`

Do not fabricate constructor arguments.

## 6. Stage SMK-03 — reconstruction CLI smoke

When `scripts/reconstruct.py` exists:

1. Run its actual help command.
2. Record the subcommands and options it truly exposes.
3. Run the safest documented read-only or validation command against a copied repository fixture or copied existing Prada formula.
4. Prefer a validation command over a formula-generation command.
5. When a dry-run option exists, use it and write only to the smoke-test directory.
6. When `formulas/Prada_LHomme_From_Scratch_30mL_EdP.md` exists, copy it into the smoke directory before validation.
7. When a Prada reconstruction envelope exists, copy it into the smoke directory before use.
8. Verify the original files remain unchanged.

Do not create a new canonical Prada formula during the smoke test.

Report one of:

- `RECONSTRUCTION CLI SMOKE PASS`
- `RECONSTRUCTION CLI PRESENT / VALIDATION BLOCKED`
- `RECONSTRUCTION CLI NOT PRESENT`
- `RECONSTRUCTION CLI FAIL`

## 7. Stage SMK-04 — existing targeted test smoke

Do not run the full test suite.

Discover the smallest existing test subset that exercises the same surfaces. Candidate historical files, only when present, include:

- `tests/test_target_formula.py`;
- `tests/test_reconstruction_chassis.py`;
- `tests/test_reconstruction_identity.py`;
- `tests/test_reconstruction_bridge.py`;
- `tests/test_units_concentration.py`;
- a workbench smoke test;
- a gate-dispatch test;
- an API health test.

Run no more than the minimal relevant subset.

Rules:

- do not add tests;
- do not edit tests;
- do not mark failures xfail;
- do not rerun repeatedly until a flaky result passes;
- preserve the first result and allow one diagnostic rerun only when the first failure is environmental or clearly nondeterministic;
- record test collection count, pass/fail/skip count, duration, and exact node IDs.

A historical claim that tests once passed is not evidence that they pass in the current tree.

## 8. Stage SMK-05 — gate-dispatch smoke

Discover the current public or test-supported gate entrypoint from source and tests.

Use only:

- a copied existing Prada formula;
- a copied repository Prada fixture;
- or a FormulaState produced through an already supported repository importer.

Run one gate-dispatch attempt in a fresh process.

Capture:

- raw input identity and hash;
- entrypoint;
- gate vector;
- PASS/FAIL/SKIP/REJECT states;
- upstream rejection reason;
- material-spine coverage;
- physics-data coverage;
- confidence gate;
- preflight state;
- final returned state;
- whether values were engine-computed or adapter-precomputed;
- writes performed;
- source-tree immutability result.

The result must be labelled:

`GATE-DISPATCH SMOKE ONLY`

Also state explicitly:

- `D3 QUALIFICATION STATE UNCHANGED`
- `END_TO_END_COMPUTED QUALIFICATION NOT ESTABLISHED`
- `EQ-15 STOCHASTIC INTEGRATION NOT TESTED`

An honest upstream rejection may still count as a successful dispatch smoke when the invocation reaches the real dispatcher and returns the expected structured rejection. It does not count as an end-to-end formula pass.

Do not patch the engine, register fixture-only materials, bypass upstream gates, precompute missing metrics, or relax thresholds.

## 9. Stage SMK-06 — recovered C1 integration-path smoke

Use the hash-verified recovered file:

`Prada_LHomme_Current_EDT_Pilot_C1_CORRECTED.xlsx`

First independently verify the external workbook identity already required by the merge plan:

- UID `PLH-CURRENT-EDT-INV-C1-20260806-BA4366B26231`;
- 44 formula rows;
- 1,000.000 supplied-stock parts;
- governing status labels;
- recovered file hash.

Then inspect the repository for an existing supported route that accepts:

- XLSX directly;
- normalized JSON;
- standard formula markdown;
- CSV rows;
- or an existing FormulaState builder.

Do not write a new importer or adapter during the smoke test.

If a supported path exists:

1. copy the recovered workbook into the smoke directory;
2. run the existing importer/converter into the smoke directory or in memory;
3. verify row count, totals, stock strengths, carriers, and product-basis state survive the conversion;
4. pass the resulting supported representation into the workbench or gate dispatcher;
5. capture exact results without promoting them.

If no supported path exists, record:

`NO SUPPORTED C1 XLSX → PERFUME-CHEM INGESTION PATH`

That result is an integration finding, not permission to build an adapter in this pass.

Also distinguish:

- `EXTERNAL C1 WORKBOOK VALID`
- `PROJECT INGESTION PATH PRESENT or ABSENT`
- `WORKBENCH ROUTE REACHED or NOT REACHED`
- `GATE DISPATCH REACHED or NOT REACHED`

## 10. Stage SMK-07 — FastAPI and optional UI smoke

When an actual FastAPI entrypoint is discovered:

1. start it in a fresh process on an ephemeral localhost port;
2. use a temporary database and temporary data directory;
3. capture startup logs;
4. query `/openapi.json` only when the application exposes it;
5. query any repository-documented health endpoint;
6. enumerate routes from the OpenAPI document when available;
7. perform no mutating API call unless a repository-provided test fixture wraps it in rollback and no canonical data can change;
8. terminate the server cleanly.

When no current FastAPI entrypoint is discoverable, record:

`API ENTRYPOINT NOT DISCOVERED`

When a frontend/package manifest exists, record its documented commands. Run only a repository-declared non-mutating build or test smoke when dependencies are already available and outputs can be redirected or cleaned without touching tracked files. Frontend failure is optional-layer failure unless the project declares it part of the canonical smoke path.

## 11. Stage SMK-08 — source-tree immutability and cleanup

After every smoke stage:

1. capture Git status and diff;
2. compare critical source hashes against the pre-smoke snapshot;
3. list all new files;
4. verify all allowed new files are confined to the smoke-test directory or OS temporary directory;
5. remove disposable caches outside the preserved smoke logs;
6. do not remove or modify pre-existing user files.

Any tracked source modification produces:

`SMOKE FAIL / SOURCE TREE MUTATED`

Do not silently restore or reset the user’s pre-existing modifications. Distinguish pre-existing changes from smoke-created changes using the pre-smoke snapshot.

## 12. Required outputs

Create:

- `PERFUME_CHEM_SMOKE_TEST_REPORT.md`
- `PERFUME_CHEM_SMOKE_TEST_RESULTS.json`
- `PERFUME_CHEM_SMOKE_TEST_COMMANDS.csv`
- `PERFUME_CHEM_SMOKE_TEST_ENVIRONMENT.json`
- `PERFUME_CHEM_SMOKE_TEST_SOURCE_IMMUTABILITY.json`
- `PERFUME_CHEM_SMOKE_TEST_ARTIFACT_MANIFEST.json`
- `PERFUME_CHEM_SMOKE_TEST_SHA256.json`
- `PERFUME_CHEM_HOW_IT_WORKS.md`
- `logs/` containing raw stdout/stderr per command

`PERFUME_CHEM_HOW_IT_WORKS.md` must be based on the actual current repository and explain, in plain language:

1. the canonical entrypoint;
2. how a formula enters the system;
3. how reconstruction differs from validation/gating;
4. the exact command that starts the backend, when discovered;
5. the exact command that invokes the workbench, when discovered;
6. the exact command that runs a formula validation, when discovered;
7. the exact command that runs the targeted smoke tests;
8. where temporary and canonical data live;
9. whether the recovered C1 workbook can currently enter the project;
10. where the route stops when it cannot continue;
11. which outputs are exact, heuristic, speculative, or unknown;
12. what the smoke test proves and does not prove.

Use a non-self-referential manifest strategy and an external final SHA receipt.

## 13. Smoke status classification

Issue exactly one primary smoke verdict:

### `SMOKE PASS`

Required:

- repository root and environment discovered;
- canonical engine/workbench import succeeds;
- workbench initializes through a supported path;
- at least one real workbench operation completes;
- reconstruction CLI or the repository’s declared equivalent starts;
- one real gate-dispatch attempt reaches the actual dispatcher;
- source tree remains unchanged.

API/UI may be separately partial when they are optional.

### `SMOKE PARTIAL`

Use when the core import and at least one real operation work, but an optional or integration layer is unavailable, such as:

- FastAPI startup blocked;
- frontend unavailable;
- reconstruction validation blocked;
- no supported C1 XLSX ingestion path;
- real gate dispatcher returns an expected upstream rejection.

### `ENVIRONMENT BLOCKED`

Use when the source cannot be meaningfully exercised because the active environment lacks locked dependencies, the interpreter is incompatible, or required runtime configuration is absent.

Do not classify that as a scientific or formula failure.

### `SMOKE FAIL`

Use when:

- the canonical entrypoint cannot import despite a correctly restored locked environment;
- the documented minimal workbench route crashes from a code defect;
- the documented CLI cannot start;
- the real dispatcher crashes rather than returning a structured state;
- a tracked source file is changed;
- recovered input identity is corrupted;
- the report fabricates a successful path.

## 14. Effect on the Prada merge

- `SMOKE PASS`: continue the merge contract.
- `SMOKE PARTIAL`: continue documentary and workbook merge work; preserve the exact runtime limitation. Do not claim full project integration.
- `ENVIRONMENT BLOCKED`: continue read-only/documentary merge lanes where valid; place engine/runtime integration on `PERFUME-CHEM RUNTIME HOLD`.
- `SMOKE FAIL`: continue only evidence-preserving documentary audits. Place all engine-derived and project-integration claims on `PERFUME-CHEM INTEGRATION HOLD` until separately repaired.

A smoke verdict never changes:

- the governing C1 formula;
- C1 pilot authorization;
- empirical result count;
- D3 qualification;
- Phase G state;
- commercial-similarity state;
- release state.

## 15. Required final language

The smoke report must state:

> This smoke test evaluated software reachability and integration wiring only. It did not validate perfume odor, commercial similarity, analytical chemistry, strict OAV, stability, safety, or release readiness. It did not requalify the actual engine end to end.

Then report:

- actual repository root;
- commit and branch;
- environment;
- exact commands run;
- canonical workbench result;
- reconstruction CLI result;
- targeted test result;
- gate-dispatch result;
- C1 ingestion-path result;
- API/UI result;
- source-tree immutability result;
- primary smoke verdict;
- effect on the Prada merge;
- unresolved runtime gaps.

Do not merely say “it works.”
