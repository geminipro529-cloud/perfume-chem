# Build C11 Evidence Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Codex subagents are prohibited for this project; Sol executes inline and may delegate only bounded read-only checks to DeepLuna Fast after a fresh exact-project readiness gate.

**Goal:** Produce the complete Build C evidence package, prove every C11 software gate with fresh executable evidence, state empirical and historical gaps without promotion, and stop before Build D.

**Architecture:** C11 is documentation and verification only. It aggregates the committed C0-C10 contracts through deterministic test logs, protected-state snapshots, a requirement crosswalk, and two canonical reports; it does not alter runtime behavior, migrations, databases, scientific data, or claim authority. Sol owns all gate decisions, validates committed Git blobs, and replays the final state in a clean detached worktree.

**Tech Stack:** Python 3.11.15, pytest, PowerShell non-PTY process capture, Git committed-blob hashing, SQLite read-only checks, JSON/Markdown evidence, DeepLuna Fast on DeepInfra Priority with `FLASH` and `NO_LUNA`.

---

## Scope and immutable decisions

- Authoritative repository: `D:\chatbots\perfume-chem`.
- Read-only handoff: `D:\.prompts\perfume chem\SOL_5_6_PERFUME_CHEM_MASTER_A_D_PROMPT.md`, C11 lines 4090-4165.
- Predecessor: `docs/verification/c10/final_decision.json` must keep `c10_exit_gate_passed=true`, `c11_authorized=true`, `build_d_authorized=false`, and `build_d_started=false`.
- Permitted repository writes are limited to this plan, `docs/verification/c11/**`, and the two required `matrix_headspace_natural_lot_report` files.
- Existing tracked and untracked work is immutable input. The index must remain empty outside intentional scoped commits, and the inherited status fingerprint must remain unchanged after filtering C11-owned paths.
- Historical 30,000-candidate results remain `BLOCKED_MISSING_REPRODUCIBLE_ARTIFACT_BUNDLE` unless a complete implementation/input/result bundle is found and replayed. No such bundle may be inferred from prose.
- Empirical calibration, held-out predictive performance, uncertainty calibration rate, abstention rate, natural-lot empirical coverage, sensory outcomes, longevity, sillage, similarity, and preference remain blocked or withheld when no real observations exist.
- Build D must not start during this plan.

## Files

- Create: `docs/superpowers/plans/2026-08-03-build-c11-evidence-package.md`
- Create: `docs/verification/matrix_headspace_natural_lot_report.json`
- Create: `docs/verification/matrix_headspace_natural_lot_report.md`
- Create: `docs/verification/c11/archive_verification.json`
- Create: `docs/verification/c11/requirement_crosswalk.json`
- Create: `docs/verification/c11/run_manifest.json`
- Create: `docs/verification/c11/committed_evidence_manifest.json`
- Create: `docs/verification/c11/final_audit.json`
- Create: `docs/verification/c11/logs/**`
- Scratch-only tooling: `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\run_c11_gate_matrix.ps1`
- Scratch-only tooling: `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\write_c11_evidence.py`
- Scratch-only tooling: `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\validate_c11_evidence.py`
- Scratch-only tooling: `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\write_c11_committed_manifest.py`
- Scratch-only tooling: `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\validate_c11_committed_state.py`

### Task 1: Preserve and bind the C11 baseline

- [x] **Step 1: Verify the live predecessor and branch state**

Run:

```powershell
git -c safe.directory=D:/chatbots/perfume-chem -C D:\chatbots\perfume-chem rev-parse HEAD
git -c safe.directory=D:/chatbots/perfume-chem -C D:\chatbots\perfume-chem branch --show-current
git -c safe.directory=D:/chatbots/perfume-chem -C D:\chatbots\perfume-chem diff --cached --name-only
```

Expected: HEAD `f8d8c6836643cf8bd7693d1e6672daded9629c69`, branch `codex/add-inventory-materials`, empty index.

- [x] **Step 2: Create and verify the path-preserving prewrite archive**

Archive: `D:\.backups\perfume-chem\build-c11-prewrite-20260803T100914+0700.tar`.

Expected verification: `PASS`, `restorable=true`, `path_preserving=true`, 429 preserved files, no unsafe/duplicate members, no hash/current-state mismatches, SHA-256 `b2af01c9143e73751490b550bc935e4f21089a578895540393c3b5972cadcf3e`.

- [ ] **Step 3: Copy the verified archive receipt into C11 evidence**

Copy the exact UTF-8 JSON receipt from scratch to `docs/verification/c11/archive_verification.json`; do not rewrite archive facts manually.

### Task 2: Build the C11 requirement crosswalk

- [ ] **Step 1: Bind every required category to executable nodes or an explicit abstention gate**

The crosswalk must cover:

1. property range and condition selection;
2. vapor-pressure equation validity range;
3. trusted UNIFAC reference or abstention;
4. group-decomposition coverage;
5. COSMO-RS import integrity;
6. explicit fallback;
7. ideal baseline;
8. matrix mass/mole conservation;
9. uncertainty propagation;
10. dynamic conservation and nonnegativity;
11. substrate separation;
12. train/validation/test leakage prevention;
13. benchmark reproducibility;
14. applicability and abstention;
15. natural-lot identity/composition precedence;
16. area-percent safeguards;
17. projection separation;
18. interaction-context enforcement;
19. constrained optimizer feasibility;
20. historical 30,000-candidate regression;
21. negative claim gates;
22. API/report provenance;
23. export/import/backup/restore.

Each record must contain `category`, `status`, `test_nodes`, `artifact_paths`, `evidence_kind`, `claim_effect`, and `limitations`. `PASS` means the cited executable contract passed; unavailable scientific implementations use `PASS_ABSTENTION` only when the cited tests prove fail-closed abstention. Missing real data or replay bundles use `BLOCKED`, never `PASS`.

- [ ] **Step 2: Bind all required report sections**

The report-section map must include model inventory, consolidation ADR, deprecated/misnamed stubs, data and parameter digests, property coverage, applicability domains, calibration/validation/held-out split, metrics by class/matrix, baselines, uncertainty calibration, abstention rate, natural-lot coverage, interactions, optimizer benchmark, blocked real-data work, and exact permitted wording.

- [ ] **Step 3: Validate crosswalk completeness**

Run:

```powershell
D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe -B C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\validate_c11_evidence.py --crosswalk-only
```

Expected: exit 0 and an exact count of 23 unique required categories with no missing report section.

### Task 3: Run fresh aggregate verification

- [ ] **Step 1: Capture supported runtime versions and protected state**

Use Python 3.11.15 from `.venv_py311_a0` and `output/verification-envs/a2-slice2-py311`; Node is v26.3.0. Capture protected database/state snapshots before tests. Remove sensitive environment variables from each child process without logging values.

- [ ] **Step 2: Run the focused C0-C10 suite**

Run all of these explicit files in one pytest invocation:

```text
tests/test_c0_physical_model_inventory.py
tests/test_c1_thermophysical_contracts.py
tests/test_c2_matrix_environment.py
tests/test_c3_model_interface.py
tests/test_c4_equilibrium_models.py
tests/test_c5_calibration_program.py
tests/test_c6_dynamic_release.py
tests/test_c7_natural_lots.py
tests/test_c8_headspace_oav.py
tests/test_c9_unsupported_science.py
tests/test_c10_mixture_design.py
tests/test_c10_selection.py
tests/test_c10_historical.py
```

Command requirements: `python -B -m pytest -q -p no:cacheprovider --color=no --basetemp <external> ...`; expected exit 0, no failures, no timeout, empty stderr.

- [ ] **Step 3: Run the explicit root suite**

Run `python -B -m pytest -q -p no:cacheprovider --color=no --basetemp <external> tests` from the repository root. The explicit `tests` target is mandatory. Expected exit 0, no failures, no timeout, empty stderr.

- [ ] **Step 4: Run backend portability and provenance gates**

From `backend`, run the full backend suite and a separately captured focused invocation containing:

```text
tests/integration/test_a2_planning_export.py
tests/integration/test_a2_execution_export.py
tests/integration/test_a2_science_export.py
tests/integration/test_backup_restore.py
tests/integration/test_b9_science_reporting_api.py
```

Expected: both invocations exit 0 with no failures or timeout and empty stderr.

- [ ] **Step 5: Run deterministic integrity checks**

Run the C0 inventory verifier, C10 evidence/final-decision validators, read-only SQLite quick checks for `perfume_chem.db` and `data/perfumery_kb.db`, archive-verifier contract tests, the C11 archive verifier, `pip check` in both Python environments, broad C0-C10 Ruff/format/type/compile checks, and protected-state comparison.

- [ ] **Step 6: Scan logs and write `run_manifest.json`**

Every process must be non-PTY, no-ANSI, timeout-bounded, with separate UTF-8 stdout/stderr. Nonempty stderr is a failure. The manifest records command arguments, working directory, timestamps, duration, exit code, timeout state, byte length, and SHA-256 for each stream. Scan all logs for ANSI and credential-like values without recording matched secret text.

### Task 4: Generate the canonical reports

- [ ] **Step 1: Generate the JSON report from evidence only**

The JSON must state a conditional software decision, not scientific validation. It must include all C11 required sections, test counts from fresh logs, exact file/blob digests, C0-C10 phase decisions, known unavailable model families, explicit fallback/abstention behavior, and machine-readable `NOT_COMPUTED_NO_REAL_DATA` values for empirical metrics.

- [ ] **Step 2: Generate the Markdown projection from the JSON**

Markdown must be a deterministic human-readable projection of the JSON. It must not introduce claims or numbers absent from JSON.

- [ ] **Step 3: Encode exact wording boundaries**

Permitted wording must be limited to verified software contracts, analytic/theoretical baselines, explicit abstention, simulation-only conservation behavior, and evidence-gated experimental selection. Forbidden wording must include reproduced historical 30k/35/97.76 results, empirically validated headspace prediction, calibrated longevity/sillage, exact intensity/contribution, pleasantness, similarity, preference, or sensory/scientific outcomes.

### Task 5: Validate and commit only C11 evidence

- [ ] **Step 1: Run the independent C11 validator**

The validator must check schema, 23-category completeness, report parity, evidence-path existence, SHA-256 values, test outcomes, blocked/withheld empirical fields, C10 predecessor binding, Build D closure, UTF-8, ANSI absence, sensitive-pattern absence without printing matches, and no unexpected changed paths.

- [ ] **Step 2: Verify the inherited overlay is unchanged**

Recompute the filtered status fingerprint excluding only C11-owned paths. It must equal the pre-C11 1,782-entry digest `4487309377de170c3dc1edf71022f16133806be81f142c305fa894e14efdf532`; the Git index must be empty before staging.

- [ ] **Step 3: Commit the scoped C11 source/evidence package**

Stage only this plan, `docs/verification/c11/**`, and the two required reports. Inspect `git diff --cached --name-status`, run `git diff --cached --check`, commit with an explicit C11 evidence message, and verify all inherited paths remain untouched.

- [ ] **Step 4: Create and commit the canonical Git-blob manifest**

Hash each committed blob using `git cat-file blob <commit>:<path>`, compare working-tree transforms explicitly, record CRLF-to-LF transforms separately, and reject every other mismatch. Validate the manifest before its scoped commit.

### Task 6: Detached replay and final acceptance

- [ ] **Step 1: Verify the replay worktree is clean, then detach it at the final C11 commit**

Use `D:\.worktrees\perfume-chem\c10-replay-19b993a1`; do not reset, clean, or delete. Checkout is allowed only after `git status --porcelain` is empty.

- [ ] **Step 2: Replay focused tests and committed-state validators**

Run the focused C0-C10 suite, the C11 report validator, and the committed-blob manifest validator in the detached worktree with external temp/cache paths. Expected: exit 0, no failures, empty stderr, clean replay worktree afterward.

- [ ] **Step 3: Run a fresh exact-project DeepLuna Fast audit**

Run `deepseek_check`; only if `READY`, submit one bounded read-only `FLASH`/`NO_LUNA` audit over the final reports, crosswalk, run manifest, and committed manifest. Sol must verify and may reject unsupported worker interpretation. Run settled postflight accounting with zero unknown reservations.

- [ ] **Step 4: Stop at the Build C boundary**

Set `build_d_started=false` and `build_d_authorized=false` in the final C11 evidence. Report the exact Build C decision, tests, archive, commits, replay, blocked empirical/historical claims, and limitations. Do not execute any Build D command or create any Build D artifact.
