# Build C0 Physical-Model Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Codex subagents are prohibited by project policy; bounded mechanical audits may use DeepLuna Fast after an exact-project readiness gate. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a verified, source-hash-bound inventory/call graph, consolidation ADR, and replayable `LEGACY_HEURISTIC` fixture set without changing production model behavior.

**Architecture:** Keep C0 metadata-first. A Python verifier owns schema checks, source/symbol/caller validation, unsupported-capability absence checks, canonical hashing, and deterministic fixture replay. The current workbench and model modules are read-only inputs; later C phases implement the accepted `engine.physics` boundary.

**Tech Stack:** Python 3.11, pytest, standard-library `ast`, `hashlib`, `json`, `pathlib`, Git, Markdown/JSON.

---

### Task 1: Freeze the C0 verification contract with failing tests

**Files:**
- Create: `tests/test_c0_physical_model_inventory.py`
- Test: `tests/test_c0_physical_model_inventory.py`

- [x] **Step 1: Write tests for required categories, classifications, record fields, call-edge integrity, source hashes, ADR disposition, fixture warnings, fixture hashes, replay, and the no-production-edit boundary.**

  The tests import `scripts.verify_c0_physical_model_inventory` and call its
  `load_inventory`, `validate_inventory`, `load_legacy_fixtures`,
  `validate_legacy_fixtures`, and `capture_legacy_case` functions. Required C0
  categories are the exact bullets at master-prompt lines 3158-3174. Every
  classification must belong to the eight-value C0 vocabulary.

- [x] **Step 2: Run the focused test and verify RED.**

  Run:

  ```powershell
  $env:NO_COLOR='1'; $env:TERM='dumb'; D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe -m pytest -q tests/test_c0_physical_model_inventory.py
  ```

  Expected: collection fails because `scripts.verify_c0_physical_model_inventory`
  does not exist. This is the required TDD failure.

### Task 2: Add the machine inventory and human call-graph report

**Files:**
- Create: `docs/verification/c0/physical_model_inventory.json`
- Create: `docs/verification/c0/physical_model_inventory.md`
- Create: `docs/architecture/ADR-2026-08-02-c0-physical-model-consolidation.md`
- Test: `tests/test_c0_physical_model_inventory.py`

- [x] **Step 1: Create the C0 directory and add one record for every discovered implementation plus explicit `UNSUPPORTED` records for absent DIPPR-style equations and COSMO-RS.**

  Each record must include `id`, `category`, `name`, `classification`,
  `source`, `inputs`, `outputs`, `conditions`, `consumers`, `evidence_labels`,
  `tests`, `claim_impact`, `runtime_status`, `disposition`, and `source_sha256`.
  Split multi-branch functions where branches have different authority.

- [x] **Step 2: Add caller edges and a rendered Markdown report.**

  Each edge records `caller`, `callee`, `kind`, and `evidence`. The report groups
  canonical runtime, competing runtime, advisory legacy, disconnected legacy,
  stubs, and unsupported capabilities, and lists every claim family required by
  C0.

- [x] **Step 3: Add the ADR.**

  The ADR declares the future `engine.physics` request/result router, one selected
  implementation per claim/version, Build B selected-assertion adapter, Laboratory
  Beta persistence authority, current compatibility adapters, and fail-closed
  abstention policy. It explicitly states that C0 changes no production route.

### Task 3: Implement the minimum verifier to make inventory tests green

**Files:**
- Create: `scripts/verify_c0_physical_model_inventory.py`
- Test: `tests/test_c0_physical_model_inventory.py`

- [x] **Step 1: Implement canonical JSON hashing and inventory loading.**

  Use UTF-8, sorted keys, compact separators, and a trailing newline only for the
  locked fixture file. Resolve paths against the repository root and reject path
  traversal.

- [x] **Step 2: Implement fail-closed inventory validation.**

  Check schema fields, IDs, categories, classifications, file hashes, source
  symbols through `ast`, call-edge references/evidence, test paths, dispositions,
  required category coverage, ADR presence, and absence queries for unsupported
  capabilities.

- [x] **Step 3: Run focused tests.**

  Run the Task 1 command. Expected: inventory tests pass; legacy fixture tests
  remain RED because the fixture files do not yet exist.

### Task 4: Freeze and replay legacy physical-model outputs

**Files:**
- Create: `.gitattributes` (C0 fixture paths only)
- Create: `tests/fixtures/c0_legacy_physical_model_cases.json`
- Create: `tests/fixtures/c0_legacy_physical_model_cases.sha256`
- Modify: `scripts/verify_c0_physical_model_inventory.py`
- Test: `tests/test_c0_physical_model_inventory.py`

- [x] **Step 1: Implement read-only capture functions for representative legacy families.**

  Cover formula-state headspace, pipeline temporal frames, standalone thermo
  headspace/trajectory, natural composite headspace, phase/Hansen risk, diffusion,
  skin interaction, vapor-pressure classification, temporal consistency, dose
  response, psychophysics, maturation, receptor/adaptation, hedonic scoring, and
  backend longevity/sillage. Normalize dataclasses, mappings, tuples, arrays,
  non-finite floats, and optional-dependency abstentions.

- [x] **Step 2: Run the capture functions locally and add the frozen JSON with `apply_patch`.**

  Every case must use classification `LEGACY_HEURISTIC`, contain a non-empty
  non-promotion warning, input SHA-256, relevant implementation source SHA-256,
  and normalized expected output. Add the SHA-256 of canonical fixture bytes to
  the companion file.

- [x] **Step 3: Run focused tests and verify GREEN.**

  Run the Task 1 command. Expected: all C0 tests pass and every fixture replays.

### Task 5: Run the C0 exit gate and commit only C0 files

**Files:**
- Create: `docs/verification/c0/logs/c0-verifier.stdout.txt`
- Create: `docs/verification/c0/logs/c0-verifier.stderr.txt`
- Create: `docs/verification/c0/logs/c0-focused-pytest.stdout.txt`
- Create: `docs/verification/c0/logs/c0-focused-pytest.stderr.txt`
- Modify: `docs/superpowers/plans/2026-08-02-build-c0-physical-model-consolidation.md`

- [x] **Step 1: Run the verifier non-interactively with explicit timeout and separate streams.**

  Run through `work/run_captured_command.mjs` with `NO_COLOR=1`, `TERM=dumb`, and
  a 120-second timeout:

  ```powershell
  D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe scripts/verify_c0_physical_model_inventory.py --inventory docs/verification/c0/physical_model_inventory.json --fixtures tests/fixtures/c0_legacy_physical_model_cases.json --fixture-sha tests/fixtures/c0_legacy_physical_model_cases.sha256
  ```

  Expected: exit 0 and a summary containing zero validation errors.

- [x] **Step 2: Run the focused pytest file with the same capture boundary.**

  Expected: exit 0, zero failures, and no warning promoted to a scientific claim.

- [x] **Step 3: Verify scope and requirements.**

  Confirm target-file status, inspect `git diff --check`, verify source hashes once
  more, and assert that no `engine/**`, `backend/**`, migration, database, or
  unrelated path is staged. Re-read master-prompt lines 3154-3208 and map every
  requirement to an artifact/test.

- [x] **Step 4: Perform a fresh exact-project DeepLuna Fast read-only validation and reproduce all gate-bearing findings locally.**

  Permit one bounded read, `FLASH` and `NO_LUNA`, with only the C0 artifacts,
  verifier, test, master-prompt C0 range, and compact logs. Sol retains final gate
  authority and rejects unsupported worker interpretation.

- [x] **Step 5: Commit the C0 checkpoint.**

  Stage only the files listed in this plan and commit with:

  ```powershell
  git -c safe.directory=D:/chatbots/perfume-chem commit -m "build(c0): inventory and freeze physical model paths"
  ```

  Re-run `git status --short` and confirm the pre-existing dirty overlay remains
  present and unstaged. Do not begin C1 unless all C0 evidence is green.
