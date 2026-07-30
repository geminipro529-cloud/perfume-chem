# Build B2 Observation Authority Implementation Plan

**Goal:** Implement the approved B2 observation, conflict, and selected
assertion authority without beginning B3.

**Stack:** Python 3.11, SQLAlchemy 2 async ORM, Alembic, SQLite,
pytest/pytest-asyncio, Ruff, mypy, existing stable JSON hashing.

## Task 1 — Freeze schema and legacy contracts

- Create `backend/tests/unit/test_b2_property_schema.py` first.
- Assert exact constants, five canonical tables, named checks/uniqueness/FKs,
  append-only registration, and legacy authority columns.
- Run the test to RED because `app.models.lab_properties` does not exist.
- Create `backend/app/models/lab_properties.py`.
- Modify `backend/app/models/lab.py` only to add legacy columns, import B2
  models, and register append-only tables.
- Run focused schema tests and Ruff; commit exact paths.

## Task 2 — Add migration `20260730_0006`

- Create `backend/tests/integration/test_b2_property_migration.py` first.
- Test empty upgrade, representative B1 preservation, legacy labeling with
  zero observation promotion, constraints/triggers, downgrade, and re-upgrade.
- Create explicit Alembic DDL with no metadata reflection or hidden canonical
  backfill.
- Update only current-head compatibility constants in
  `test_lab_migration.py` and `test_backup_restore.py`; historical phase tests
  remain pinned.
- Run migration/compatibility tests; commit exact paths.

## Task 3 — Implement validated observation writes

- Create `backend/tests/unit/test_b2_property_service.py` RED cases for
  identity scope, typed value shapes, censored values, B1 linkage, exact
  workflow scope, hashes, and duplicate protection.
- Create `backend/app/repositories/lab_properties.py`.
- Create `backend/app/services/lab_properties.py`.
- Compose focused mixins into `LabRepository` and `LabService`.
- Run focused tests, Ruff, and mypy; commit exact paths.

## Task 4 — Implement conflicts and selected assertions

- Extend RED tests for computed difference dimensions, source independence,
  candidate decisions, unresolved blocking conflicts, no averaging,
  explicit-ID retrieval, no latest-value API, and full reconstruction.
- Implement the minimal service/repository behavior.
- Confirm no B3 threshold/OAV condition matcher appears.
- Run focused tests, lint, typing, and relevant B1 regression tests; commit.

## Task 5 — Close the B2 gate

- Run B2 schema/service/migration tests plus B1 and current-head
  backup/restore compatibility under supported Python 3.11 with no PTY, no
  ANSI, explicit timeouts, and writable temp/cache roots.
- Run Ruff and scoped mypy.
- Verify canonical database and knowledge-base hashes remain unchanged.
- Write `docs/verification/b2/property_authority_gate.md` and `.json` with
  exact commands, counts, log hashes, migrated legacy count, promoted
  observation count, remaining unknowns, and scientific-release block.
- Run fresh `deepseek_check`; if READY, submit one bounded DeepLuna Fast
  read-only validation of changed paths, report, and preserved logs.
- Sol independently reproduce-checks every finding and passes or blocks B2.
