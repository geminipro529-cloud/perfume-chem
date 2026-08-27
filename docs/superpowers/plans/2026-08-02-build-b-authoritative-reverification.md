# Build B Authoritative Reverification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` for inline execution. The user explicitly forbids
> Codex subagents, so do not use `subagent-driven-development`.

**Goal:** Independently prove and seal Build B scientific-data authority from
the final Build A checkpoint, repairing only defects reproduced in the current
authoritative tree.

**Architecture:** Execute B0 through B10 as a fail-closed chain. Each phase uses
the existing canonical source/observation/claim database rather than creating a
parallel authority store. Historical reports provide test-path discovery only;
live code, disposable-database migrations, protected-state checks, and current
test output decide every gate.

**Tech Stack:** CPython 3.11, pytest, Ruff, mypy, SQLAlchemy/Alembic, SQLite,
Node.js, deterministic JSON/gzip artifacts, PowerShell orchestration, DeepLuna
Fast on DeepInfra Priority with `FLASH` and `NO_LUNA`.

---

## File map

- `scripts/scientific_truth_inventory.py`: deterministic B0 inventory scanner.
- `tests/test_scientific_truth_inventory.py`: B0 scope/determinism regression.
- `docs/verification/b0/`: current B0 machine and human evidence.
- `backend/app/models/lab_sources.py`, `backend/app/repositories/lab_sources.py`,
  `backend/app/services/lab_sources.py`: B1 source/extraction authority.
- `backend/app/models/lab_properties.py`,
  `backend/app/repositories/lab_properties.py`,
  `backend/app/services/lab_properties.py`: B2 observation/assertion authority.
- `backend/app/models/lab_thresholds.py`,
  `backend/app/repositories/lab_thresholds.py`,
  `backend/app/services/lab_thresholds.py`,
  `backend/app/adapters/legacy_thresholds.py`: B3 contextual threshold/OAV.
- `backend/app/models/lab_rules.py`, `backend/app/repositories/lab_rules.py`,
  `backend/app/services/lab_rules.py`, `backend/app/adapters/legacy_rules.py`:
  B4 rule compiler and advisory boundary.
- `backend/app/models/lab_analytical.py`,
  `backend/app/repositories/lab_analytical.py`,
  `backend/app/services/lab_analytical.py`: B5 analytical authority.
- `backend/app/models/lab_regulatory.py`,
  `backend/app/repositories/lab_regulatory.py`,
  `backend/app/services/lab_regulatory.py`: B6 regulatory authority.
- `backend/app/models/lab_claims.py`,
  `backend/app/repositories/lab_claims.py`,
  `backend/app/services/lab_claims.py`: B7 claim decisions.
- `backend/app/models/lab_backfill.py`,
  `backend/app/repositories/lab_backfill.py`,
  `backend/app/services/lab_backfill.py`, `scripts/b8_backfill_dashboard.py`: B8
  decision-value backfill.
- `backend/app/api/v1/endpoints/lab.py`, `backend/app/services/lab_science.py`,
  and B9 tests: B9 API/report projections.
- `engine/project_verification.py`, `tests/test_scientific_data_authority_report.py`,
  and `docs/verification/scientific_data_authority_report.{md,json}`: B10 seal.

### Task 1: Close the reproduced B0 scanner defect

**Files:**

- Modify: `tests/test_scientific_truth_inventory.py`
- Modify: `scripts/scientific_truth_inventory.py`
- Verify: `outputs/b0-debug-recovery/20260802T055309/`

- [x] Add `data/perfumery_kb.db-wal` and `data/perfumery_kb.db-shm` to the
  miniature repository and assert that neither enters `source_digests`.
- [x] Run the focused regression and record the expected failure showing both
  sidecars are inventoried.
- [x] Exclude `.db-wal` and `.db-shm` in `_is_generated_or_metadata`.
- [x] Rerun the focused test, the complete three-test scanner suite, and Ruff.
- [x] Generate two fresh full-tree inventories outside the repository and prove
  byte identity and zero sidecar entries.
- [ ] Review `git diff --check`, verify the recovery archive again, and commit
  only the scanner and its test.

### Task 2: Rebuild and review the current B0 baseline

**Files:**

- Modify: `docs/verification/b0/scientific_truth_inventory.json.gz`
- Modify: `docs/verification/b0/scientific_truth_baseline.json`
- Modify: `docs/verification/b0/scientific_truth_baseline.md`

- [ ] Archive the three current B0 artifacts with path-preserving extraction and
  SHA-256 comparison.
- [ ] Generate the canonical inventory with:

```powershell
$env:NO_COLOR='1'
$env:TERM='dumb'
& 'D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe' -B `
  scripts/scientific_truth_inventory.py `
  --repo-root 'D:\chatbots\perfume-chem' `
  --output docs/verification/b0/scientific_truth_inventory.json.gz
```

Expected: exit 0; no stderr; a second external generation is byte-identical;
no credential, cache, SQLite-sidecar, embedded-Git, or B0-output path occurs.

- [ ] Recompute summary, authority, conflict, source-digest, compatibility, and
  claim-impact facts directly from the artifact; update both reports to name
  Build A checkpoint `073ee8eaf66bd97a4894063c2f3ffc01c874e7b2` and the preserved
  working-tree overlay.
- [ ] Run the scanner tests, JSON validation, selected digest checks, protected
  database `quick_check`, and `git diff --check`.
- [ ] Run a fresh exact-project DeepLuna check and one bounded read-only B0 report
  audit; reconcile every finding locally.
- [ ] Commit only the B0 artifact/report paths and any accepted scanner repair.

### Task 3: Reverify B1 source and provenance authority

**Files:**

- Verify: `backend/app/models/lab_sources.py`
- Verify: `backend/app/repositories/lab_sources.py`
- Verify: `backend/app/services/lab_sources.py`
- Verify: `backend/alembic/versions/20260730_0005_b1_source_provenance.py`
- Verify: `backend/tests/unit/test_b1_source_schema.py`
- Verify: `backend/tests/unit/test_b1_source_service.py`
- Verify: `backend/tests/integration/test_b1_source_migration.py`
- Update only if live evidence changes: `docs/verification/b1/source_provenance_gate.{md,json}`

- [ ] Confirm immutable versions, exact locators, extraction hashes, review-state
  transitions, independence groups, and no AI auto-promotion by code inspection.
- [ ] Run B1 schema/service/migration tests plus `test_lab_migration.py` and
  `test_backup_restore.py` under the supported backend Python with a 300-second
  timeout. Expected: exit 0; all selected tests pass; count recorded fresh.
- [ ] Run Ruff and scoped mypy on the B1 modules, then disposable Alembic
  upgrade/downgrade/upgrade with one linear head.
- [ ] If a defect appears, stop B1 descendants, archive the exact affected paths,
  write one failing regression in the owning B1 test file, prove RED, implement
  one root-cause fix, and rerun the same gate.
- [ ] Refresh and commit the B1 report only after the live gate passes.

### Task 4: Reverify B2 observation-first property authority

**Files:** B1 files plus `lab_properties.py` model/repository/service,
`20260730_0006_b2_property_authority.py`, B2 schema/service/migration tests, and
`docs/verification/b2/property_authority_gate.{md,json}`.

- [ ] Verify typed numeric/categorical/interval/distribution/censored values,
  exact identity scope, source/extraction linkage, append-only history, conflict
  visibility, selected-assertion policy, uncertainty, and `LEGACY_HEURISTIC`
  non-promotion.
- [ ] Run the eight-file cumulative B1/B2/compatibility pytest gate from the
  current B2 report with a 300-second timeout; run exact-path Ruff and scoped
  mypy; run disposable migration and backup/restore checks.
- [ ] Apply the phase-owned RED/GREEN defect protocol if any current failure is
  reproduced; otherwise make no production edit.
- [ ] Refresh and commit the B2 gate evidence with current counts and hashes.

### Task 5: Reverify B3 contextual threshold and OAV authority

**Files:** B1-B2 files plus threshold model/repository/service/legacy adapter,
`20260730_0007_b3_contextual_thresholds.py`, B3 unit/integration tests, and the
B3 gate reports.

- [ ] Verify all ten structured mismatch reasons, cross-medium and cross-basis
  conversion refusal, strict-science no-fallback behavior, preserved legacy
  status, and screening-only OAV wording.
- [ ] Run the twelve-file cumulative B1-B3 pytest gate with a 300-second timeout,
  exact-path Ruff, scoped mypy, and disposable migration checks.
- [ ] Apply RED/GREEN only for a reproduced B3 defect; refresh and commit the B3
  evidence only after the cumulative gate passes.

### Task 6: Reverify B4 knowledge-rule compilation

**Files:** B1-B3 files plus rule model/repository/service/legacy adapter,
`20260731_0008_b4_knowledge_rules.py`, B4 fixtures/tests, and B4 gate reports.

- [ ] Verify canonical identity/group resolution, relation vocabulary,
  directionality, dose/matrix/source requirements, stable duplicate/cycle/
  contradiction diagnostics, and separation of advisory from blocking logic.
- [ ] Run the fifteen-file cumulative B1-B4 gate with a 360-second timeout,
  exact-path Ruff, scoped mypy, and corpus regression comparison.
- [ ] Apply RED/GREEN only for a reproduced B4 defect; refresh and commit B4
  evidence after the gate passes.

### Task 7: Reverify B5 analytical authority

**Files:** A2 science bridge plus analytical model/repository/service,
`20260731_0009_b5_analytical_authority.py`, B5 schema/service/migration/e2e tests,
and B5 gate reports.

- [ ] Verify immutable method versions; fitness-for-purpose validation;
  sequence/run/raw-file chains; calibration, response factors, uncertainty and
  QC propagation; GC-MS identity tiers; FID quantity scope; HS-SPME matrix
  dependence; and GC-O non-identity boundaries.
- [ ] Run the current 25-file A2+B1-B5 compatibility gate with a 600-second
  timeout, exact-path Ruff, scoped mypy, migration lifecycle, and protected-state
  hash comparison.
- [ ] Apply RED/GREEN only for a reproduced B5 defect; refresh and commit B5
  evidence after the cumulative gate passes.

### Task 8: Reverify B6-B7 regulatory and claim authority in order

**Files:** B6/B7 model/repository/service files, migrations `20260731_0010` and
`20260731_0011`, their unit/integration tests, and B6/B7 gate reports.

- [ ] For B6, browse only primary official sources to recheck current IFRA and
  EU status, effective dates, supersession, supplier scope, and permitted
  screening wording; store no inaccessible clauses or certification claim.
- [ ] Run B6 focused and cumulative tests, Ruff, mypy, disposable migrations,
  and unknown-natural/future/draft/watchlist negative paths. Seal B6 before B7.
- [ ] For B7, verify all claim types, evidence roles, independence/conflict/
  uncertainty sufficiency, ALLOW_EXACT/ALLOW_SCOPED/ADVISORY_ONLY/
  WITHHOLD_UNKNOWN/BLOCK decisions, and scoped upgrades.
- [ ] Run B7 focused and cumulative tests, Ruff, mypy, disposable migrations,
  and negative promotion cases. Apply phase-owned RED/GREEN repair if needed,
  then seal B7.

### Task 9: Reverify B8-B9 backfill and reporting in order

**Files:** B8 model/repository/service, `scripts/b8_backfill_dashboard.py`,
`20260731_0012_b8_prioritized_backfill.py`, B8 tests/projection/gate reports,
B9 endpoint/service/tests, and B9 gate reports.

- [ ] Verify B8 priority ordering, authority-preserving gap states, dashboard
  dimensions, deterministic projection, and zero silent migration/backfill of
  legacy values. Seal B8 before B9.
- [ ] Verify B9 source/locator/observation/conflict/threshold/analytical/
  regulatory/claim projections, strict versus exploratory views, all eight
  evidence labels, read-only APIs, and non-promoting Markdown serialization.
- [ ] Run each phase's focused and cumulative tests, Ruff, mypy, migration-head,
  protected-database, and deterministic projection/report checks. Apply
  phase-owned RED/GREEN repair only to reproduced defects, then seal each phase.

### Task 10: Execute B10 and stop at the Build B boundary

**Files:** `engine/project_verification.py`,
`tests/test_scientific_data_authority_report.py`, B10 logs, and
`docs/verification/scientific_data_authority_report.{md,json}`.

- [ ] Archive the current B10 logs and final reports before replacement.
- [ ] Run the complete required Build B matrix named in
  `required_test_matrix`, including source, observation, conflict, contextual
  OAV, rule, analytical, regulatory, negative promotion, API/report, export,
  backup, and restore coverage. Expected: exit 0; every named test passes.
- [ ] Verify one Alembic head at `20260731_0012`, disposable upgrade/restore,
  protected SQLite `quick_check=ok`, byte-identical protected databases, and
  no unauthorized migrated/backfilled scientific row.
- [ ] Run `python -B -m engine.project_verification --full` non-interactively
  with `NO_COLOR=1`, `TERM=dumb`, separated stdout/stderr, and an 1,800-second
  timeout. Expected: every mandatory check passes; only declared optional Docker
  checks may skip.
- [ ] Rebuild the Markdown and JSON authority reports from current evidence,
  including baseline/final SHA, inventories, conflicts, policies, call graphs,
  test/verifier counts, unknowns, and exact permitted wording.
- [ ] Run the report-contract test, JSON validation, `git diff --check`, and one
  fresh exact-project Fast-only final audit. Reconcile the audit locally and
  reject unsupported findings.
- [ ] Commit only the B10 report/evidence paths, confirm the final tested SHA and
  preserved dirty-work counts, present the Build B boundary report, and do not
  begin Build C.
