# Laboratory Beta Completion Implementation Plan

**Goal:** Deliver every software-controllable item in the completion roadmap as a tested local-first laboratory beta while preserving explicit empirical release blockers.

**Architecture:** Strict engine value objects and a solvent-inclusive mixture contract feed `PerfumeWorkbench`. SQLAlchemy lab tables persist immutable versions and append-only events. Thin FastAPI routes expose deterministic operations to a static offline interface.

**Method:** Every behavior follows red, green, refactor. Each increment ends with focused tests and an independent review checkpoint.

## Task 0: Truth Baseline and Exception Ledger

**Status:** Completed in commit `0566978` before this plan.

**Evidence:**
- Phase 0 golden fixtures and scientific-class contracts are locked.
- Full local verification reported 18 verifier checks passed, 0 failed, and 2 declared Docker skips; engine test shards totaled 354 tests and backend totaled 61.
- Hosted GitHub jobs were created but blocked before steps by the account billing state; this is an infrastructure exception, not a test result.

**Continuation gate:** Re-run focused golden and verification checks after each model change. Do not defer behavior classification to Task 9.

## Task 1: Strict Quantities and Finished Mixtures

**Files:**
- Create `engine/quantities.py`
- Create `engine/mixture.py`
- Modify `engine/workbench.py`
- Test `tests/test_quantities.py`
- Test `tests/test_mixture.py`
- Modify `tests/test_workbench.py`

**Acceptance:**
- Invalid and ambiguous quantities fail.
- Explicit mass/volume/amount fraction conversions preserve basis.
- Solvent-inclusive mixtures change mole fractions and modeled headspace.
- Missing required physical data yields `UNKNOWN`, never an invented exact value.
- Existing compatibility requests remain supported with disclosed limitations.
- Requests declare `strict` or `compatibility`; compatibility assumptions cannot authorize ledger, safety, or dosing writes.

## Task 2: Canonical Lab Schema and Migration

**Files:**
- Create `backend/app/models/lab.py`
- Modify `backend/app/models/__init__.py`
- Modify `backend/app/core/config.py`
- Modify `backend/app/db_session.py`
- Create `backend/alembic.ini`
- Create `backend/alembic/env.py`
- Create `backend/alembic/script.py.mako`
- Create `backend/alembic/versions/20260716_0001_lab_beta.py`
- Modify `backend/pyproject.toml`
- Test `backend/tests/unit/test_lab_schema.py`
- Test `backend/tests/integration/test_lab_migration.py`

**Acceptance:**
- Fresh and legacy SQLite databases upgrade without dropping legacy tables.
- Runtime, migration, backup, and restore resolve the same absolute database path and enable SQLite foreign keys.
- A pre-upgrade snapshot and schema fingerprint are created before migration.
- New tables use `lab_*` names and legacy import uses an explicit crosswalk.
- Formula versions, evidence, stocks, bottle events, inventory movements, experiments, predictions, and outcomes have explicit foreign keys and units.
- Immutable/append-only records reject update/delete at repository and database levels.
- Empty, populated-current, partially migrated, corrupted, and newer-than-supported databases have focused outcomes.

**Review checkpoint:** Verify migration rollback and legacy preservation before Task 3.

## Task 3: Transactional Lab Repository

**Files:**
- Create `backend/app/repositories/lab.py`
- Create `backend/app/services/lab_service.py`
- Test `backend/tests/unit/test_lab_repository.py`
- Test `backend/tests/integration/test_lab_transactions.py`

**Acceptance:**
- Formula version creation is immutable and sequential.
- Bottle state is reconstructed from ordered events.
- Stream sequence, expected sequence, and idempotency prevent stale writes and duplicate retries.
- Additions, transfers, splits, combines, corrections, and inventory effects commit atomically.
- One mass conservation basis is used per stock; volume remains measured metadata unless density is explicit.
- Insufficient stock and unit mismatch roll back completely.
- Corrections are linked compensating events and history tables reject update/delete.

**Review checkpoint:** Replay, retry, stale-write, transfer, compensation, and rollback tests pass before Task 4.

## Task 4: Evidence, Safety, and Intervention Contracts

**Files:**
- Create `engine/safety_assessment.py`
- Create `engine/interventions.py`
- Modify `engine/workbench.py`
- Test `tests/test_safety_assessment.py`
- Test `tests/test_interventions.py`

**Acceptance:**
- Safety requires named standard version, category, basis, and constituent coverage.
- Unresolved natural/preblend constituents produce `unverified`, not pass.
- Candidate additions are inventory-valid, measurable, satisfy explicit brief constraints, and are non-dominated; sensory identity preservation is `HEURISTIC`.
- Workbench is the only API-facing entry point.
- A synthetic versioned restriction dataset tests the contract; no result says compliant/pass without complete source revision, category, basis, and constituent coverage.

**Review checkpoint:** Adversarially test missing categories, stale standards, opaque naturals, and unsafe candidates.

## Task 5: Experiment and Preference Loop

**Files:**
- Create `engine/preference.py`
- Extend `backend/app/services/lab_service.py`
- Test `tests/test_preference.py`
- Test `backend/tests/integration/test_experiment_loop.py`

**Acceptance:**
- Protocol, applications, timed observations, predictions, outcomes, and comparisons persist.
- Predictions cannot be edited after outcomes.
- Preference fitting is withheld below sample/connectivity gates.
- Diagnostic fits include regularization, training rows, comparison graph status, and baseline evaluation status.
- Prediction claims remain `UNKNOWN/not_validated` until held-out evaluation beats declared baselines.

## Task 6: Deterministic Assistant and Lab API

**Files:**
- Create `backend/app/services/lab_assistant.py`
- Create `backend/app/schemas/lab.py`
- Create `backend/app/api/v1/endpoints/lab.py`
- Modify `backend/app/api/v1/router.py`
- Test `backend/tests/unit/test_lab_assistant.py`
- Test `backend/tests/integration/test_lab_api.py`

**Acceptance:**
- Supported intents map to deterministic tool plans.
- Responses contain facts, calculations, evidence, assumptions, limitations, and next action.
- Same state and request produce byte-stable packets.
- Byte stability applies to canonical template JSON with declared decimal, ordering, and revision rules; volatile timestamps are outside the hashed payload.
- Unsupported/free-form scientific claims are refused or labeled unknown.

**Review checkpoint:** Fuzz aliases, ordering, decimals, ambiguity, and repeated requests before UI work.

## Task 7: Offline Lab Interface

**Files:**
- Create `backend/app/static/index.html`
- Create `backend/app/static/lab.css`
- Create `backend/app/static/lab.js`
- Modify `backend/app/main.py`
- Test `backend/tests/integration/test_lab_ui.py`

**Acceptance:**
- FastAPI serves the app locally without a Node runtime or network dependency.
- Dashboard, bottle, formula, materials, experiment, and assistant views are reachable.
- Mobile and desktop layouts remain usable.
- Evidence classes and missing-data warnings are visible.
- Browser smoke test covers formula creation through bottle event, analysis, observation, and outcome at desktop and mobile viewports.

## Task 8: Backup, Restore Validation, Export, and Readiness

**Files:**
- Create `backend/app/services/backup_service.py`
- Extend `backend/app/api/v1/endpoints/lab.py`
- Create `engine/release_readiness.py`
- Extend `engine/project_verification.py`
- Test `backend/tests/integration/test_backup_restore.py`
- Test `tests/test_release_readiness.py`

**Acceptance:**
- Live SQLite backup produces a consistent snapshot, manifest, and digest.
- Restore validates integrity, digest, and schema revision before replacement.
- Restore stages while running and applies only in maintenance mode or a stopped-server command after a pre-restore snapshot.
- JSON exports preserve stable UUIDs, units, provenance, versions, and event order; re-import is idempotent.
- Backup and restore UI controls are added only after these endpoints exist.
- Readiness reports code, data, validation, and infrastructure axes separately.
- Empirical and hosted-CI blockers remain explicit.

**Review checkpoint:** Corrupt digest, open-handle, rollback, duplicate-import, and newer-schema cases are adversarially tested.

## Task 9: Integrated Verification and Publication

**Commands:**
- `python -m pytest tests -q`
- `cd backend && poetry run ruff check app tests`
- `cd backend && poetry run mypy app --ignore-missing-imports`
- `cd backend && poetry run pytest --cov=app --cov-report=term`
- `python -m engine.project_verification --scope full`
- Docker compose health smoke when Docker is available

**Acceptance:**
- Independent Sol xhigh review, or the approved DeepSeek/Luna fallback when Sol
  is quota-blocked, has no unresolved critical or important findings.
- Local verification has zero unexplained failures.
- Documentation states external empirical and GitHub billing blockers without calling them code failures.
- Changes are committed, pushed, and the public draft PR is updated.

### Browser Smoke Evidence (2026-07-17)

- Ran the FastAPI application against a fresh ignored SQLite database and used
  the local interface to create a material, explicitly based stock, formula,
  immutable formula version, bottle, bottle addition, experiment, blind sample,
  blotter application, timed observation, and outcome.
- Ran canonical evidence analysis and confirmed that unavailable physical,
  regulatory, longevity, sillage, and receptor evidence remained explicitly
  `UNKNOWN` or `unverified` rather than being guessed.
- Confirmed the persisted ledger contained one experiment, sample, application,
  observation, and outcome, plus append-only bottle events and paired inventory
  movements.
- Verified the dashboard at 1440 x 900 and 390 x 844. Both viewports had no
  document-level horizontal overflow; the mobile media query was active and all
  six laboratory views remained reachable.
- The smoke test exposed an invalid HTML step grid for the default 0.1 g bottle
  addition. A regression test reproduced the failure before the input minimum
  was corrected from 0.000001 g to the declared 0.001 g dispensing increment.

### Independent Review Evidence (2026-07-17)

- Sol xhigh delegation was attempted first and was blocked by the delegated
  account's usage quota. The approved bounded Luna fallback reviewed only the
  science, migration, transaction, backup, API, and UI authority surfaces.
- No critical findings were reported. Two important findings reproduced: the
  HTTP backup service pinned the previous Alembic revision, and liquid mass
  concentration was absent from the strict quantity model.
- Backup compatibility now derives from Alembic's single current script head,
  and a regression test compares the HTTP service contract to that head.
- Liquid mass concentration is now a separate unit-bearing g/L quantity with
  mg/L conversion, matching IUPAC's mass-per-mixture-volume definition rather
  than being mislabeled as a dimensionless fraction.
- A third review concern was rejected with a regression test: a known category
  limit exceedance remains `fail` when other constituents are unresolved.
  Missing evidence prevents `pass`, but cannot reverse a demonstrated failure.

### Full Verification Evidence (2026-07-17)

- `.venv\Scripts\python.exe scripts\pipeline_audit.py project-verify --json`
  completed in 1104.1 seconds with `PASS_WITH_SKIPS`.
- 18 required checks passed, zero failed, and the two optional Docker checks
  were skipped because `--include-docker` was not requested.
- Engine tests passed: 101 truth-core, 158 data/knowledge, 69 gates/families,
  and 60 legacy tests. Backend lint and typecheck passed, followed by 154 backend
  tests.
- Scientific audit, material-data validation, knowledge-rule validation,
  golden formula/API regression, source/wheel build, and isolated wheel smoke
  all passed. The golden fixture SHA-256 remained
  `f47b79a6e4aeaa6e9e72aa3a6934264806cbb349b5bcad853a8b8e5bac9d0996`.
- Release readiness reported Laboratory Beta `ready` with code, data, and
  infrastructure axes ready. Scientific Release remains `blocked` because
  preregistered held-out sensory validation has not passed.
