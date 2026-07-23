# phase-1a-domain-foundation - Work Plan

## TL;DR (For humans)

**What you'll get:** A normalized, migration-safe database foundation for materials, stock solutions, formulas, and formula versions — plus API endpoints to create and query them, backward compatibility with old JSON formula records, and a formula Markdown file importer.

**Why this approach:** The existing Alembic lab schema already defines the right tables (lab_materials, lab_stock_solutions, lab_formulas, lab_formula_versions, lab_formula_components). Phase 1A builds the API and adapter layer on top of those existing tables without touching bottles, events, experiments, or engine code. This keeps the PR narrow, independently reviewable, and safe to merge alongside the Phase 0 PR.

**What it will NOT do:** Implement bottle-event persistence, bottle reconstruction, intervention generation, optimizer migration, chat orchestration, new headspace equations, solvent-inclusive MixtureState changes, longevity/sillage prediction, preference learning, frontend redesign, or receptor/mood speculation. It will NOT change engine calculation behavior, alter golden fixtures, or remove legacy models.

**Effort:** Medium
**Risk:** Medium — existing Alembic migration creates 20+ tables including non-domain tables (bottles, events); Phase 1A only operates on ~6 of them. Care needed to avoid accidentally triggering bottle/event code paths.
**Decisions to sanity-check:** 1) Using the full lab schema (including bottle/event tables) as the Phase 1A database foundation rather than creating a narrower schema. 2) Keeping legacy models in place and adding a compatibility adapter rather than migrating data. 3) Adding a `role` and `unit` column to lab_formula_components via a new migration rather than using the existing frozen migration.

Your next move: Approve the plan and run `/start-work`. Full execution detail follows below.

---

> TL;DR (machine): Effort=Medium, Risk=Medium. Build API+adapter layer on existing lab schema tables. New Alembic migration for schema additions. Legacy models preserved. No engine changes. 8 implementation todos + final verification wave.

## Scope
### Must have
1. New Alembic migration adding `role` and `unit` columns to `lab_formula_components`; add `remaining_mass_g` to `lab_stock_solutions`
2. Material CRUD API endpoint (create, read, list; resolve by name, alias, or ID)
3. StockSolution CRUD API endpoint (create, read, list; linked to material)
4. Formula CRUD API endpoint (create with initial version, read, list)
5. FormulaVersion immutable creation (auto-increment version_number, append-only)
6. FormulaComponent read/write alongside FormulaVersion
7. Legacy formula compatibility adapter (LabFormula <-> old Formula/Perfume JSON)
8. Formula Markdown import parser (reads `formulas/*.md` format, creates LabFormula + LabFormulaVersion + LabFormulaComponent rows)
9. Test suite: migration from empty DB, migration from current schema, legacy JSON import, version immutability, version ordering, component reconstruction, stock-vs-material identity, alias collision, dilution preservation, export/import round trips, rollback/downgrade, SQLite compatibility, API backward compat, workbench analysis preservation, golden fixture preservation
10. First-time database bootstrap that creates initial lab tables if absent

### Must NOT have (guardrails, anti-slop, scope boundaries)
- NO bottle-event persistence or bottle API endpoints
- NO bottle reconstruction logic
- NO intervention generation
- NO optimizer migration
- NO chat orchestration
- NO new headspace or mixture equations
- NO solvent-inclusive MixtureState changes
- NO longevity or sillage prediction
- NO preference learning
- NO frontend changes
- NO speculative receptor or mood systems
- NO changes to engine/workbench.py, engine/bottle_addition.py, engine/scientific_contract.py, engine/pipeline/formula_state.py, engine/pipeline/simulator.py, engine/quantities.py, engine/mixture.py
- NO changes to golden fixtures, golden test expectations, or project verifier expected outputs
- NO removal of legacy tables Perfume, Formula, Material, or knowledge_graph models
- NO second copy of formula analysis — workbench.py is the sole analysis path
- NO new package dependencies beyond what's already in backend/pyproject.toml
- NO destructive operations on existing databases — backup-before-migration via db_bootstrap

## Verification strategy
- Test decision: Tests-after for infrastructure (migration, endpoints, adapters) with TDD on immutability enforcement and collision handling
- Framework: pytest (backend tests via Poetry, standard output capture)
- Evidence: .omo/evidence/task-<N>-phase-1a-domain-foundation.jsonl

### Verification sequence
1. Each todo produces focused tests run via `cd backend && poetry run pytest tests/unit/test_<area>.py -v`
2. After ALL todos: full backend suite, engine test shards, golden regressions, project-verify
3. Final verification wave runs in parallel

## Execution strategy
### Parallel execution waves
**Wave 0** (infrastructure, parallel):
- T1: New Alembic migration (schema additions)
- T2: Legacy compatibility adapter
- T3: Database bootstrap wiring

**Wave 1** (domain implementation, parallel after Wave 0):
- T4: Material API endpoints + repository
- T5: StockSolution API endpoints + repository

**Wave 2** (formula domain, parallel after T4/T5):
- T6: Formula + FormulaVersion + FormulaComponent API
- T7: Formula Markdown import parser

**Wave 3** (final integration):
- T8: Formula Markdown round-trip and import API

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| T1. Migration | — | T3, T4, T5, T6, T7 | T2 |
| T2. Legacy adapter | — | T6 | T1 |
| T3. Bootstrap wiring | T1 | — | — |
| T4. Material API | T1 | T6 | T5 |
| T5. StockSolution API | T1 | T6 | T4 |
| T6. Formula API | T2, T4, T5 | T7 | — |
| T7. Markdown import | T1, T4, T6 | T8 | — |
| T8. Round-trip test | T7 | F1-F4 | — |

## Todos

<!-- APPEND TASK BATCHES BELOW THIS LINE. -->

- [x] 1. New Alembic migration for schema additions
  What to do / Must NOT do:
  Create a new Alembic migration `20260717_0001_phase_1a_domain.py` that adds:
  - `lab_formula_components.role` column (String(40), nullable, default None) — stores "top", "heart", "base", or None
  - `lab_formula_components.unit` column (String(20), nullable, default None) — stores "mass", "volume", "drops", or None
  - `lab_stock_solutions.remaining_mass_g` column (Float, nullable, default=`initial_mass_g`)
  
  Must NOT change the existing frozen migration `20260716_0001_lab_beta.py`.
  Must NOT remove columns or tables.
  Must be SQLite-compatible (batch-able ALTER TABLE).
  Must include a downgrade that reverses the additions.

  References:
  - `backend/alembic/versions/20260716_0001_lab_beta.py` (existing frozen migration)
  - `backend/app/models/lab.py:149-162` (LabStockSolution)
  - `backend/app/models/lab.py:194-208` (LabFormulaComponent)
  - `backend/app/db_bootstrap.py` (migration runner)

  Acceptance criteria:
  - `alembic upgrade head` succeeds on both empty and current-schema databases
  - `alembic downgrade -1` removes added columns
  - New columns visible in SQLite schema after upgrade
  - Backend model classes include the new fields as optional Mapped columns

  QA scenarios:
  - Happy: Create fresh SQLite DB, run upgrade, verify columns exist via `PRAGMA table_info`
  - Happy: Run upgrade on DB with existing full lab schema, verify columns added
  - Failure: Verify downgrade removes columns
  - Evidence: `.omo/evidence/t1-migration.txt`

  Commit: Y | `feat(db): add role/unit to lab_formula_components, remaining_mass to lab_stock_solutions`

- [x] 2. Legacy formula compatibility adapter
  What to do / Must NOT do:
  Create `backend/app/adapters/legacy_formula.py` with:
  - `LegacyFormulaAdapter.to_lab(perfume_dict: dict, formula_dict: dict) -> tuple[str, str, list[dict]]` that converts old `Perfume`/`Formula` JSON ingredients to `(formula_id, version_id, component_rows)`
  - `LegacyFormulaAdapter.from_lab(lab_formula, lab_version, lab_components) -> dict` that reconstructs the legacy JSON format
  - Round-trip test demonstrating that legacy -> lab -> legacy produces equivalent JSON within floating-point tolerance
  - The adapter materializes `stock_active_fraction` from stock_solution data when available
  
  Must NOT modify existing legacy model files.
  Must NOT require a database connection to function (pure transformation).

  References:
  - `backend/app/models/perfume.py` (Perfume and Formula models)
  - `backend/app/api/v1/endpoints/formulas.py` (existing analyze-formula API)
  - `backend/app/schemas/perfume.py` (FormulaCreate schema)

  Acceptance criteria:
  - Adapter converts a known legacy JSON ingredient list to lab component rows
  - Round-trip preserves ingredient names, percentages, and roles within 1e-10 tolerance
  - Adapter handles edge cases: empty ingredients, missing roles, duplicate names

  QA scenarios:
  - Happy: Convert `{"ingredients": [{"name": "Hedione", "percentage": 60, "role": "heart"}]}` to lab component row and back
  - Happy: Verify stock_active_fraction gets incorporated
  - Edge: Empty ingredient list raises clear error
  - Evidence: `.omo/evidence/t2-legacy-adapter.txt`

  Commit: Y | `feat(api): add legacy formula compatibility adapter`

- [x] 3. Database bootstrap wiring
  What to do / Must NOT do:
  Ensure `db_bootstrap.upgrade_database()` is called on backend startup. Verify that:
  - `backend/app/main.py` calls the bootstrap on startup lifecycle
  - The bootstrap uses the mandatory backup-before-migration path for file-backed SQLite
  - The bootstrap does NOT run for in-memory test databases (test conftest creates tables directly)
  - First-time database creation works (no pre-existing file)
  
  Must NOT change `db_bootstrap.py` itself (it's already correct).
  Must NOT break the existing test conftest that uses `Base.metadata.create_all`.

  References:
  - `backend/app/main.py` (app startup)
  - `backend/app/db_bootstrap.py` (existing bootstrap)
  - `backend/alembic.ini` (database URL config)
  - `backend/tests/conftest.py` (test DB setup)

  Acceptance criteria:
  - `uvicorn app.main:app` starts and triggers lab schema creation
  - First-time run creates all lab tables
  - Subsequent runs skip creation (upgrade detects current head)
  - Tests continue to pass (they use in-memory/create_all)

  QA scenarios:
  - Happy: Run backend with fresh SQLite file, verify all lab tables exist
  - Happy: Run backend again with same file, verify no errors
  - Regression: Run existing backend tests, all pass
  - Evidence: `.omo/evidence/t3-bootstrap.txt`

  Commit: Y | `feat(db): wire database bootstrap into application startup`

- [x] 4. Material API endpoints + repository
  What to do / Must NOT do:
  Create `backend/app/repositories/lab_material.py` with CRUD for `LabMaterial` and `LabMaterialAlias`.
  Create `backend/app/api/v1/endpoints/materials.py` with:
  - `POST /api/v1/lab/materials` — create material with optional aliases
  - `GET /api/v1/lab/materials` — list materials (with search/filter)
  - `GET /api/v1/lab/materials/{id_or_name}` — get by UUID or canonical_name
  - `GET /api/v1/lab/materials/resolve?name=<alias>` — resolve alias to canonical material
  - `POST /api/v1/lab/materials/{id}/aliases` — add alias
  
  Must NOT implement material properties or evidence records (future phase).
  Must NOT modify existing lab_service.py.
  Must use async SQLAlchemy sessions.
  Must validate that `canonical_name` is unique.
  Must reject duplicate aliases with clear error.

  References:
  - `backend/app/models/lab.py:81-97` (LabMaterial, LabMaterialAlias)
  - `backend/app/repositories/lab.py` (existing lab repository pattern)
  - `backend/app/repositories/base.py` (base repository)
  - `backend/app/db_session.py` (session management)

  Acceptance criteria:
  - POST creates material and returns 201 with material ID
  - GET list returns paginated results
  - GET by name resolve works
  - GET resolve alias returns canonical material
  - Duplicate name returns 409
  - Tests exist for all CRUD operations

  QA scenarios:
  - Happy: Create material, verify response has UUID and canonical_name
  - Happy: List materials, verify created material appears
  - Happy: Resolve by alias
  - Failure: Duplicate canonical_name returns 409
  - Evidence: `.omo/evidence/t4-materials-api.txt`

  Commit: Y | `feat(api): material CRUD with alias resolution`

- [x] 5. StockSolution API endpoints + repository
  What to do / Must NOT do:
  Create `backend/app/repositories/lab_stock.py` with CRUD for `LabStockSolution`.
  Create `backend/app/api/v1/endpoints/stock.py` with:
  - `POST /api/v1/lab/stock` — create stock solution linked to existing material
  - `GET /api/v1/lab/stock` — list stock solutions
  - `GET /api/v1/lab/stock/{id}` — get by ID
  - `PATCH /api/v1/lab/stock/{id}/remaining` — update remaining_mass_g
  - `GET /api/v1/lab/stock?material_id=<id>` — filter by material
  
  Must NOT implement stock movement events or bottle transactions (future phase).
  Must verify linked material exists via foreign key.
  Must validate active_fraction in (0, 1].
  Must default remaining_mass_g to initial_mass_g on create.

  References:
  - `backend/app/models/lab.py:149-162` (LabStockSolution)
  - `engine/bottle_addition.py:56-85` (StockSolution dataclass — note this is the engine type, not the DB model)
  - `engine/addition_solver.py` (consumes engine StockSolution, not DB model)

  Acceptance criteria:
  - POST creates stock and returns 201
  - GET lists with optional material filter
  - PATCH remaining updates in-place
  - Invalid material_id returns 404
  - Tests pass for all operations

  QA scenarios:
  - Happy: Create stock with valid material_id, verify response
  - Happy: Filter stocks by material
  - Failure: Create with unknown material_id returns 404
  - Evidence: `.omo/evidence/t5-stock-api.txt`

  Commit: Y | `feat(api): stock solution CRUD`

- [x] 6. Formula + FormulaVersion + FormulaComponent API
  What to do / Must NOT do:
  Create `backend/app/repositories/lab_formula.py` with:
  - Create formula (creates LabFormula row + initial LabFormulaVersion + LabFormulaComponent rows)
  - Create new version (increments version_number, creates new immutable snapshot)
  - Read formula by ID with latest version
  - Read formula by ID with specific version
  - List formulas with version metadata
  - List all versions of a formula
  
  Create `backend/app/api/v1/endpoints/formulas_lab.py` with:
  - `POST /api/v1/lab/formulas` — create formula with initial version and components
  - `GET /api/v1/lab/formulas` — list formulas
  - `GET /api/v1/lab/formulas/{id}` — get formula with latest version
  - `GET /api/v1/lab/formulas/{id}/versions` — list all versions
  - `GET /api/v1/lab/formulas/{id}/versions/{v}` — get specific version
  - `POST /api/v1/lab/formulas/{id}/versions` — create new version
  
  Component rows specify: stock_solution_id (or material_id + inline dilution), requested_mass_g, role, position.
  
  Must enforce immutability: after creation, a version cannot be modified (read-only).
  Must auto-increment version_number.
  Must record `source_json` with provenance info.
  Must allow creating a formula from legacy adapter output.
  Must NOT implement bottle-event persistence.
  Must NOT modify existing formulas.py endpoint (the old one remains for backward compat).

  References:
  - `backend/app/models/lab.py:165-208` (LabFormula, LabFormulaVersion, LabFormulaComponent)
  - `backend/app/api/v1/endpoints/formulas.py` (existing analyze API — no changes)
  - `backend/tests/conftest.py` (test DB setup)

  Acceptance criteria:
  - POST formula creates formula + version 1 + components
  - POST version creates version 2+ with incremented number
  - GET specific version returns immutable snapshot
  - Attempting to modify a version via PUT/PATCH returns 405 (or append-only trigger blocks it)
  - Version list returns ordered by version_number
  - Components include role and position ordering

  QA scenarios:
  - Happy: Create formula, verify version_number=1
  - Happy: Add version, verify version_number=2
  - Immutability: After creating version 2, GET version 1 still returns original components
  - Immutability: Attempted PUT on version returns 405
  - Edge: Create formula with empty component list
  - Evidence: `.omo/evidence/t6-formula-api.txt`

  Commit: Y | `feat(api): formula, formula version, and component CRUD with immutability`

- [x] 7. Formula Markdown import parser
  What to do / Must NOT do:
  Create `backend/app/services/formula_import.py` with:
  - `import_formula_markdown(file_path: Path) -> ImportResult` that:
    1. Reads a formula Markdown file following the established format (`luxury_formulas_2026-03-26.md` style)
    2. Parses ingredient table rows (name, dilution, amount uL, section header)
    3. Resolves material names to LabMaterial IDs (via canonical_name or aliases)
    4. Resolves dilutions to StockSolution active_fraction (creates in-memory or finds by matching)
    5. Creates LabFormula + LabFormulaVersion + LabFormulaComponent rows
  - `ImportResult` dataclass: formula_id, version_number, component_count, warnings, errors
  
  Parser must handle:
  - Top/Heart/Base section headers as role assignments
  - `#`, `Ingredient`, Dilution, Amount (µL), Amount (mL) columns
  - Accord breakdown text (ignored for components, stored in source_json)
  - Dilution percentages (e.g., "10%") → active_fraction = 0.1
  - Neat materials (no dilution specified) → active_fraction = 1.0
  - Comments and blank lines
  
  Must NOT modify existing formula files.
  Must be idempotent (same file → same formula structure, but new version).
  Must report unresolvable material names as errors, not silently skip.

  References:
  - `luxury_formulas_2026-03-26.md` (established formula format)
  - `AGENTS.md` (formula structure rules)
  - `backend/app/services/lab_service.py` (existing lab service pattern)
  - `engine/material_resolver.py` (engine-side material name resolution — don't duplicate, call it)

  Acceptance criteria:
  - Parser extracts table rows and section headers from a known formula Markdown file
  - Creates LabFormula + version 1 + components in database
  - Unresolvable material name in file returns ImportResult with error entry
  - Round-trip: export imported formula as Markdown produces equivalent content within structural tolerance

  QA scenarios:
  - Happy: Parse `formulas/Some_Formula_30mL_EDP.md` (or a test fixture), verify components match expected
  - Happy: Verify section headers map to roles (Top→top, Heart→heart, Base→base)
  - Edge: File with no ingredient table returns empty result + warning
  - Failure: File referencing material not in database returns error
  - Evidence: `.omo/evidence/t7-markdown-import.txt`

  Commit: Y | `feat(api): formula Markdown import parser`

- [x] 8. Round-trip and integration test
  What to do / Must NOT do:
  Add integration tests that:
  1. Create material via API
  2. Create stock solution via API
  3. Create formula via API with components referencing stock
  4. Verify formula has version_number=1
  5. Create a new version with updated components
  6. Verify version_number=2
  7. Verify GET version 1 returns original, version 2 returns updated
  8. Export formula Markdown, re-import, verify round-trip
  9. Load a legacy JSON formula through the adapter, verify lab components match
  10. Verify rollback via alembic downgrade
  
  Must NOT rely on any external services.
  Must create and tear down test database in each test.
  Must verify that existing workbench and bottle-addition tests still pass.

  References:
  - `backend/tests/conftest.py` (test DB fixture)
  - `backend/tests/integration/` (existing integration test pattern)
  - `tests/test_workbench.py` (workbench tests — verify unchanged)
  - `tests/test_bottle_addition.py` (bottle tests — verify unchanged)

  Acceptance criteria:
  - 10+ integration tests covering the full domain lifecycle
  - All existing engine and backend tests still pass
  - Evidence file captures test outputs

  QA scenarios:
  - Happy: Full CRUD lifecycle test
  - Happy: Round-trip Markdown import->export->import
  - Regression: Run engine test shards, verify no changes
  - Regression: Run project-verify --quick, verify PASS
  - Evidence: `.omo/evidence/t8-integration.txt`

  Commit: Y | `test(api): comprehensive domain foundation integration tests`

## Final verification wave

- [x] F1. Plan compliance audit
  Check: every Must Have is addressed, every Must NOT Have is absent from the diff.
  Command: review diff for scope violations (bottles, events, engine changes, golden fixture changes)
  Evidence: `.omo/evidence/f1-plan-compliance.txt`

- [x] F2. Backend test suite
  Run: `cd backend && poetry run pytest --cov=app --cov-report=term -v`
  Verify: all tests pass, minimum 80% coverage on new code
  Evidence: `.omo/evidence/f2-backend-tests.txt`

- [x] F3. Engine + golden regression test suite
  Run: `python -m pytest tests/test_workbench.py tests/test_bottle_addition.py tests/test_scientific_contract.py tests/test_golden_formula_regression.py -v`
  Verify: all tests pass, golden fixture checksums unchanged
  Evidence: `.omo/evidence/f3-engine-regression.txt`

- [x] F4. Project verification
  Run: `python scripts/pipeline_audit.py project-verify --quick --json`
  Verify: returns PASS or NOT_EVALUATED (quick scope), no FAIL
  Evidence: `.omo/evidence/f4-project-verify.txt`

- [x] F5. Migration rollback test
  Run: `alembic downgrade -1`, then `alembic upgrade head`
  Verify: both succeed, database state consistent
  Evidence: `.omo/evidence/f5-rollback.txt`

- [x] F6. Scope fidelity review
  Manual diff review: no changes to engine/ (except project_verification test exclusions), no new bottle/event code, no golden fixture changes
  Evidence: `.omo/evidence/f6-scope-fidelity.txt`

## Commit strategy
- One commit per todo (8 commits total) for clean review
- Commits are ordered to maintain a working state at each step
- Squash NOT requested — reviewer can squash at merge time if preferred

## Success criteria
1. All new migration tests pass (empty DB, current schema, rollback)
2. All material CRUD operations work via API
3. All stock solution CRUD operations work via API
4. Formula versions are immutable (no in-place modification possible)
5. Legacy JSON formula round-trips through the adapter faithfully
6. Formula Markdown files import correctly with material resolution
7. All existing engine tests, workbench tests, bottle-addition tests pass unchanged
8. All existing backend tests pass
9. Golden fixtures and project verifier expectations unchanged
10. The diff touches NO engine calculation code, NO bottle/event code, NO golden fixtures

