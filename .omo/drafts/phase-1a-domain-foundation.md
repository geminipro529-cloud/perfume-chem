# Draft: Phase 1A Domain Foundation

## Current-State Findings

### Repository State
- Branch: `codex/add-inventory-materials` (Phase 0 PR not yet merged)
- Git status: uncommitted changes from Phase 0 work
- No dirty working tree issues — the changes are staged or tracked

### Phase 0 Already Delivers
1. Packaged `perfume-chem-engine` (editable install via `pip install -e .`)
2. `engine.workbench.PerfumeWorkbench` — canonical evidence-labeled analysis
3. `engine.bottle_addition.AdditionSolver` — exact one-stock bottle mass balance
4. `engine.scientific_contract` — EvidenceDescriptor + ScientificClass
5. `engine.quantities` — typed volume/density/molar-mass
6. `engine.mixture.MixtureState` — solvent-inclusive mixture model
7. All the evidence-classification, golden-fixture, and verification infrastructure

### Alembic Already Configured
- `backend/alembic/alembic.ini` and `env.py` exist and work
- Initial migration `20260716_0001_lab_beta.py` creates the FULL Laboratory Beta schema (20+ tables):
  - `lab_evidence_records` — evidence provenance
  - `lab_materials` — canonical materials (UUID PK, canonical_name unique)
  - `lab_material_aliases` — alias -> material resolution (normalized_alias unique)
  - `lab_material_properties` — evidence-backed property values
  - `lab_constituents` — natural composition decomposition
  - `lab_restrictions` — IFRA/safety restrictions
  - `lab_stock_solutions` — physical stock solutions (material_id FK, active_fraction, density, solvent, initial_mass)
  - `lab_formulas` — formula identity (name)
  - `lab_formula_versions` — immutable snapshots (formula_id, version_number unique, brief_json, constraints_json, concentration_fraction)
  - `lab_formula_components` — normalized components (formula_version_id, stock_solution_id, position, requested_mass_g, requested_volume_ul)
  - `lab_batches` — physical batches
  - `lab_bottles` — physical bottles
  - `lab_bottle_events` — append-only event stream
  - `lab_bottle_event_effects` — material deltas per event
  - `lab_bottle_measurements` — quantity measurements
  - `lab_inventory_movements` — stock tracking
  - `lab_experiments`, `lab_samples`, `lab_applications` — experiment protocol
  - `lab_observations` — timed observations
  - `lab_pairwise_comparisons` — preference data
  - `lab_predictions`, `lab_outcomes` — model predictions

- Append-only triggers on 11 tables prevent UPDATE/DELETE
- Uses UUID string IDs, UTCDateTime timezone-aware timestamps
- `db_bootstrap.py` has robust `prepare_database_upgrade` (backup-before-migration) workflow

### Existing Legacy Models
- `backend/app/models/perfume.py` — `Perfume` and `Formula` with JSON `ingredients` column
- `backend/app/models/knowledge_graph.py` — `Material`, `PairingRule`, `SynergyRule`, `TheoryFramework`, `FormulationOutcome`, `PairwisePreference`, `ScoreCalibration`
- `backend/app/models/ingredient.py` — `Ingredient` model

### Existing Lab Service
- `backend/app/services/lab_service.py` — 698 lines of transactional lab commands (materials, stock, bottle events, experiments)
- Already has bottle-event stream semantics, optimistic concurrency, idempotency

### Existing API Endpoints
- `backend/app/api/v1/endpoints/formulas.py` — analyze-formula, calculate-addition, dilute
- `backend/app/api/v1/endpoints/lab.py` — lab endpoints (new, probably from current Phase 0 work)
- `backend/app/api/v1/router.py` — router wiring

### Test Infrastructure
- Engine tests: `tests/` with conftest.py (sys.path manipulation)
- Backend tests: `backend/tests/` with conftest.py (async SQLite, httpx test client)
- Golden formula regression tests exist
- Project verifier in `engine/project_verification.py` with shard manifests

### Key Architectural Decisions Already Made
1. UUID primary keys for lab tables (not auto-increment integers)
2. Timezone-aware UTC timestamps with custom UTCDateTime type
3. Separate `id` (UUID) and `canonical_name` (unique string) for materials
4. Stock solutions separate from canonical materials
5. Formula versions immutable by database triggers
6. `requested_mass_g` as primary component quantity (not volume)
7. Evidence-backed properties via lab_material_properties + lab_evidence_records

## Planning Decisions

### Migration Strategy
- Keep existing `20260716_0001` migration as-is (it's frozen and already committed)
- Create a NEW migration `20260717_0001_phase_1a_domain` on top that adjusts schema if needed
- The full lab schema exists but only domain-foundation tables and endpoints will be operational in Phase 1A
- Bottle/event/experiment tables exist in DB but have NO new API code in Phase 1A

### Schema Adjustments for Phase 1A
- The existing lab tables need minor adjustments for Phase 1A completeness:
  - `lab_formula_components`: add `role` column (top/heart/base)
  - `lab_formula_components`: add `unit` column (mass/volume/drops)
  - `lab_formula_versions`: ensure `version_number` auto-increments per formula
  - `lab_stock_solutions`: add `remaining_mass_g` for current stock tracking
- These changes go in the new migration

### Compatibility Strategy
- Old `Perfume`/`Formula` models remain untouched
- A new `LegacyFormulaAdapter` in `backend/app/adapters/` converts between legacy JSON ingredients and `LabFormulaComponent` rows
- Legacy API payloads remain readable through the adapter
- The adapter preserves round-trip fidelity: legacy -> lab -> legacy produces equivalent JSON

### ID Resolution
- Materials identified by `canonical_name` (unique) or UUID `id`
- Aliases resolved through `lab_material_aliases` normalized_alias lookup
- Formula Markdown import will fuzzy-match material names against aliases
- Collision errors raised for ambiguous resolutions

### Immutability Enforcement
- `lab_formula_versions` already has append-only trigger (no UPDATE, no DELETE)
- New versions are created by INSERT with incremented `version_number`
- `lab_formula_components` also append-only — old component sets persist with their version
- `lab_formulas` row is mutable (name, metadata) but versions are not

### Unit Representation
- Phase 1A stores primary component quantity as `requested_mass_g` (matching existing schema)
- `requested_volume_ul` stored alongside when available
- Unit metadata stored in `source_json` or a future `unit` column
- No typed-unit system in the persistence layer (engine/quantities.py handles typed conversions)

### Provenance Links
- `lab_evidence_records` exists but Phase 1A does NOT require full evidence for every row
- Formula `source_json` stores provenance metadata as freeform JSON
- Material import from inventory.txt records `source_json: {"source": "inventory_txt", "date": "..."}`
- Comprehensive evidence database is a later phase

### Rollback
- `db_bootstrap.upgrade_database` already handles backup-before-migration
- `alembic downgrade` supported for the new migration
- Legacy tables untouched — rollback is restoring old database from backup

### Which Legacy Tables Remain
- `perfumes` — kept for backward compat
- `formulas` — kept for backward compat
- `materials` — kept for backward compat (knowledge_graph)
- All `lab_*` tables — created by migration, domain subset operational
- All `pairing_rules`, `synergy_rules`, `theory_frameworks`, `formulation_outcomes`, `pairwise_preferences`, `score_calibrations` — untouched

### Code Paths That Must NOT Change
- `engine/workbench.py` — no changes
- `engine/bottle_addition.py` — no changes
- `engine/scientific_contract.py` — no changes
- `engine/pipeline/formula_state.py` — no changes
- `engine/pipeline/simulator.py` — no changes
- `engine/quantities.py` — no changes
- `engine/mixture.py` — no changes
- All engine test golden fixtures — no changes
- Legacy `Perfume`/`Formula` model files — no structural changes (only add adapter import)
- Project verifier test expectations — no changes

## Risks and Unresolved Questions

1. **Existing lab migration creates ALL tables including bottles/events**. This means Phase 1A operates on a schema that includes tables for future phases. The unused tables are harmless but add complexity. Acceptable for now; a future refactor could lazily split migrations.

2. **Lab service partially implements bottle events**. The existing `lab_service.py` has bottle-event transaction logic. Phase 1A must NOT add new bottle/event code paths but also must not break existing lab service tests. Solution: the Phase 1A PR does NOT touch lab_service.py.

3. **Formula Markdown parser is new**. The format is documented in `luxury_formulas_2026-03-26.md` and `AGENTS.md`. Parser must handle the established format and normalize to lab components. Risk: edge cases in parsing (accord headers, comments, non-standard tables). Mitigation: parse as best-effort with clear error reporting.

4. **Alias collision**. Inventory names like "Bergamot FCF" vs computed normalized names could collide. The `lab_material_aliases` table has a unique constraint on `normalized_alias`. Collision errors are surfaced to the user with the conflicting names.

5. **SQLite compatibility**. Alembic already handles batch mode for SQLite. All new migrations must be SQLite-compatible (no ALTER COLUMN, ADD CONSTRAINT requires table recreation).

Status: awaiting-approval
