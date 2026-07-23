# rest-of-implementations - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** All 6 unfinished implementation drafts executed in 6 parallel waves — 2 perfume formulas gated through the pipeline, the perfumery AI knowledge engine built, a 100+ formula audit completed, Phase 1A domain migration deployed, and a comprehensive pipeline physics/scoring/gate overhaul applied. Subagent delegation now works (config fixed), so execution is parallel and cheap.

**Why this approach:** The 6 drafts are all independently scoped — no cross-contamination — so they can be fanned out. Tracks C and D already have approved, Momus-reviewed plan files; tracks E and F get fully planned here from their exploration drafts. Ruff is already clean (verified 2026-07-23), so all tracks start from a green baseline.

**What it will NOT do:** No new pipeline scripts (RULE 2), no auto-formulation, no changes to engine workflow or scientific contract, no new formula family archetypes, no backend/ changes beyond migration + adapter.

**Effort:** Large (6 tracks, 10+ implementation waves total)
**Risk:** Medium — tracks E & F modify pipeline physics (formula_state.py, simulator.py, gates.py); TDD regression tests required as floor, zero-regression on golden fixtures
**Decisions to sanity-check:** Cade Oil Rectified 1% prerequisite (add 4-location integration or substitute — blocks Track A); pipeline architecture split (4710-line gates.py split — Track F); skin temperature raise 25°→32°C for skin applications (Track F physics)

Your next move: approve (yes/proceed), or ask about a specific track. High-accuracy review NOT required (user didn't request it; Tracks C and D already reviewed). Full execution detail follows below.

---

> TL;DR (machine): Large — 6-track parallel wave execution of all unfinished drafts. Effort ~30+ todos across 6 waves. Risk medium (physics changes need TDD). Delegation now viable post-config fix.

## Scope
### Must have
- **P0 prerequisite:** Cade Oil Rectified 1% in 4 data locations (inventory.txt, data/materials/C.yaml, engine/ingredient_intelligence.py, engine/odor_thresholds.py) — blocks Track A
- **Track A:** Write `formulas/Cassis_Iris_Smoke_30mL_EdP.md` (verbatim from `.omo/drafts/cassis-iris-smoke.md`, 44 materials, 6,000 µL, 20% EdP), then gate with `--brief generic`. Resolve Oakmoss IFRA edge (72→60 µL of 10% if needed).
- **Track B:** Reformulate Aventus Chypre Fruity per `.omo/drafts/aventus-chypre-fruity.md` approved plan: 3 changes (Hydroxycitronellal→Mayol+Farnesol, Ambrox 3-5%, Damascone Beta ≤12µL), then gate with `--brief generic`. ~47 materials.
- **Track C:** Execute `.omo/plans/perfumery-ai-engine.md` (Momus APPROVED, 11 todos, 6 waves) — SQLite knowledge engine, additive to pipeline.
- **Track D:** Execute `.omo/plans/final-audit-polish-v1.md` (approved 2026-07-21, 4 waves, review_required=true) — literature survey, 100+ formula pipeline mass-testing, gap remediation, weakness report. ≥500 meta-verified truths.
- **Track E:** Plan and execute Phase 1A Domain Foundation — new migration `20260717_0001_phase_1a_domain` on top of frozen `20260716_0001_lab_beta`, `LegacyFormulaAdapter`, formula markdown parser. From `.omo/drafts/phase-1a-domain-foundation.md` exploration (158 lines). No bottle/event/experiment API code, no engine/ workbench changes.
- **Track F:** Plan and execute Pipeline Improvement — 7 components C1-C7 from `.omo/drafts/pipeline-improvement.md` exploration (137 lines): physics accuracy, gate logic cleanup, scoring recalibration, intervention engine, data quality, architecture, analysis output.
### Must NOT have (guardrails, anti-slop, scope boundaries)
- No new pipeline scripts (RULE 2 from AGENTS.md)
- No changes to `engine/workbench.py`, `engine/bottle_addition.py`, `engine/scientific_contract.py` (Track E constraint)
- No backend/ changes beyond migration + adapter (Track E constraint)
- No auto-formulation engine (Track C constraint — query/recommendation only)
- No changes to inventory.txt or material YAML files outside Track A prerequisite
- No changes to engine test golden fixtures without pinning current behavior first
- No subagent delegation if config fix hasn't taken effect in session (fallback to inline execution)

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD for physics/changes (Tracks C, D, E, F — regression tests pinning current behavior FIRST, then behavior change); tests-after for formula creation (Tracks A, B — pipeline gate JSON confirms PASS)
- Framework: pytest (engine-level from repo root), ruff check, basedpyright CLI
- Evidence: `.omo/evidence/rest-of-implementations/task-<N>.<ext>`

## Execution strategy
### Parallel execution waves
- **Wave 0 (sequential):** Cade Oil Rectified 1% prerequisite — blocks Track A
- **Wave 1 (parallel — 5 tracks):** Track A formula file + gate, Track B reformulation + gate, Track C Wave 1 (T1: schema+migrate, `perfumery-ai-engine.md`), Track E migration + adapter, Track F C5 (data quality: sentinel ODTs, density, farnesene) + C7 (analysis output: hardcoded longevity, block balance, cost)
- **Wave 2 (parallel — 3 tracks):** Track C Waves 2-3 (T2-T6: query APIs, rules DB, graph extension, property estimator), Track D Wave A (literature + data gap survey + ≥500 truths accumulation), Track F C2 (gate logic: dead gates, _safe_gate, hedione standardize, skeleton threshold)
- **Wave 3 (parallel — 3 tracks):** Track C Waves 4-5 (T7-T10: formula memory, failure registry, brain, sync script), Track D Wave B (pipeline mass-testing: ALL 100+ formulas), Track F C1 (physics: UNIFAC stub, ethanol mole fractions, mixture-shifted ODT, evaporation model)
- **Wave 4 (parallel — 3 tracks):** Track C Wave 6 (T11: pipeline parity tests, zero-regression), Track D Waves C-D (gap remediation + weakness report, depends on A+B), Track F C3-C4 (scoring recalibration + intervention engine)
- **Wave 5 (sequential):** Track F C6 (architecture: split gates.py 4710 lines, remove dead oav_intelligence 95% dead)
- **Wave 6 (parallel final):** F1 plan compliance, F2 code quality, F3 real QA (ruff + pytest + basedpyright), F4 scope fidelity

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| T0-Cade | none | T1-A | none |
| T1-A | T0-Cade | none | T2-B, T3-C-1, T5-E, T7-F-C57 |
| T2-B | none | none | T1-A, T3-C-1, T5-E, T7-F-C57 |
| T3-C-1 | none | T3-C-23 | T1-A, T2-B, T5-E, T7-F-C57 |
| T3-C-23 | T3-C-1 | T3-C-45 | T4-D-A, T8-F-C2 |
| T3-C-45 | T3-C-23 | T3-C-6 | T4-D-B, T9-F-C1 |
| T3-C-6 | T3-C-45 | none (final) | T4-D-CD, T10-F-C34 |
| T4-D-A | none | T4-D-C | T3-C-23, T8-F-C2 |
| T4-D-B | none | T4-D-C | T3-C-45, T9-F-C1 |
| T4-D-CD | T4-D-A, T4-D-B | none (final) | T3-C-6, T10-F-C34 |
| T5-E | none | none | T1-A, T2-B, T3-C-1, T7-F-C57 |
| T7-F-C57 | none | none | T1-A, T2-B, T3-C-1, T5-E |
| T8-F-C2 | T7-F-C57 | none | T3-C-23, T4-D-A |
| T9-F-C1 | T7-F-C57 | none | T3-C-45, T4-D-B |
| T10-F-C34 | T8-F-C2, T9-F-C1 | none | T3-C-6, T4-D-CD |
| T11-F-C6 | T10-F-C34 | none (final) | none |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->

- [ ] **0. Cade Oil Rectified 1% — prerequisite data integration (Wave 0)**
  What to do: Add Cade Oil Rectified 1% to all 4 data locations: (1) inventory.txt under a category header, (2) data/materials/C.yaml with mw_g_mol/logp/vp_25c_pa/odt_air_ppb/odt_eth_ppm/user_stock_dilution: 0.01/user_in_inventory: true, (3) engine/ingredient_intelligence.py _PROFILES (character/note/role/texture/mw/vp/clogp/synergies) + _TYPICAL_DOSE + _ODOR_FAMILY_MAP + _ACTIVITY_COEF_MAP, (4) engine/odor_thresholds.py ODT_DATA entry. Also check name_utils._ALIASES for needed alias.
  Must NOT do: skip any of the 4 locations, use placeholder values, add duplicate ODT that overrides existing entry
  Parallelization: Wave 0 | Blocked by: none | Blocks: T1-A
  References: AGENTS.md "Adding a new material to inventory" section (4-location checklist); `.omo/drafts/cassis-iris-smoke.md` line 55 "Cade Oil Rectified 1% not yet in inventory system"
  Acceptance criteria: `python -c "from engine.ingredient_intelligence import _PROFILES; assert 'cade oil rectified' in {k.lower() for k in _PROFILES}"` passes; `python -c "from engine.odor_thresholds import ODT_DATA; print(ODT_DATA.get('cade oil rectified', 'MISSING'))"` prints numeric ODT; `python -c "from engine.inventory_parser import parse_inventory; inv = parse_inventory(); assert any('cade oil' in m.name.lower() for m in inv)"` passes
  QA scenarios: happy — all 4 locations populated, no duplicate ODT, ruff clean; failure — missing any location → gate on Track A will flag missing material
  Evidence: `.omo/evidence/rest-of-implementations/task-0-cade.md`
  Commit: Y | feat(inventory): add Cade Oil Rectified 1% (4-location integration)

- [ ] **1. Track A — Cassis Iris Smoke formula file + pipeline gate (Wave 1)**
  What to do: Write `formulas/Cassis_Iris_Smoke_30mL_EdP.md` verbatim from `.omo/drafts/cassis-iris-smoke.md` lines 14-163 (the `## FORMULA FILE CONTENT` block). Then run pipeline gate: `python scripts/formula_release_gate.py --formula-file formulas/Cassis_Iris_Smoke_30mL_EdP.md --expected-concentrate-ul 6000 --brief generic --json > .omo/evidence/rest-of-implementations/task-1-gate.json`. Run analysis: `python scripts/format_pipeline_analysis.py --input .omo/evidence/rest-of-implementations/task-1-gate.json`. Append analysis to formula file under `## Pipeline Analysis`. Check IFRA watchpoints: Oakmoss Absolute ≤0.1% active (target 60 µL of 10% = 6 µL active / 6000 µL = 0.1%, current draft has 72 µL = 0.12% — reduce to 60 µL if gate flags it).
  Must NOT do: modify the formula's accord architecture or material selection (name-locked per draft)
  Parallelization: Wave 1 | Blocked by: T0-Cade | Blocks: none
  References: `.omo/drafts/cassis-iris-smoke.md` lines 14-163; `AGENTS.md` "Running Formulas Through the Pipeline"; `AGENTS.md` "Required: perfumer analysis format"
  Acceptance criteria: pipeline gate PASS or PASS_WITH_SKIPS; OAV headspace table + temporal evolution produced; IFRA Oakmoss resolved (either gate passes at 72 µL or formula reduced to 60 µL of 10%); formula file has `## Pipeline Analysis` section appended
  QA scenarios: happy — gate JSON `gates[*].status in {"PASS", "WARN"}` for all hard gates; failure — IFRA violation → reduce Oakmoss or document it as advisory WARN
  Evidence: `.omo/evidence/rest-of-implementations/task-1-gate.json`, `.omo/evidence/rest-of-implementations/task-1-analysis.md`
  Commit: Y | feat(formula): Cassis Iris Smoke 30mL EdP — gated chypre

- [ ] **2. Track B — Aventus Chypre Fruity reformulation + gate (Wave 1)**
  What to do: Load existing formula (check `formulas/` for the most recent Pineapple_Chypre or Aventus variant), then apply 3 changes from `.omo/drafts/aventus-chypre-fruity.md`: (1) substitute Hydroxycitronellal → Mayol + Farnesol at specific doses from draft, (2) correct Ambrox Super (30%) dose to 3-5% active of concentrate, (3) reduce Damascone Beta to ≤12 µL. Write updated formula file as `formulas/Aventus_Chypre_Fruity_30mL_EdP.md`. Gate with `--brief generic --json`. Run analysis, append to formula file.
  Must NOT do: add pineapple (explicitly excluded in draft), add birch tar (differentiation from original Aventus), change from chypre family
  Parallelization: Wave 1 | Blocked by: none | Blocks: none
  References: `.omo/drafts/aventus-chypre-fruity.md` (approved, Momus 8 issues fixed); `AGENTS.md` "Brief defaults"; RULE 16 "Never Change the Fragrance Family"
  Acceptance criteria: 3 changes applied and documented; pipeline gate PASS or PASS_WITH_SKIPS; Ambrox active mass 3-5% of 6000 µL concentrate; Damascone Beta ≤12 µL total
  QA scenarios: happy — gate passes, OAV headspace table shows chypre character (Evernyl + labdanum + bergamot + patchouli backbone); failure — gate flags if Ambrox over 5% or Damascone Beta over 12 µL → re-dose
  Evidence: `.omo/evidence/rest-of-implementations/task-2-gate.json`, `.omo/evidence/rest-of-implementations/task-2-analysis.md`
  Commit: Y | feat(formula): Aventus Chypre Fruity 30mL EdP — reformulated

- [ ] **3. Track C — perfumery-ai-engine Wave 1: T1 schema + migration (Wave 1)**
  What to do: Execute T1 from `.omo/plans/perfumery-ai-engine.md` (Momus APPROVED). Implement `engine/kb_schema.py` with ~25 SQLite tables (materials, aliases, properties, constituents, restrictions, rules: archetypes + IFRA + fatigue + shifts + skeletons, interactions, formula_memory, failure_patterns). Implement `engine/kb_migrate.py` to populate from 7 scattered data sources (ODT_DATA 316 entries, _PROFILES 271, YAML 255 in-inventory, material_properties.json 232, natural decomposition 38, knowledge_graph 9 files, pairing rules).
  Must NOT do: rewrite pipeline — additive only; generate Python dicts from DB (pipeline code unchanged)
  Parallelization: Wave 1 | Blocked by: none | Blocks: T3-C-23 (subsequent Track C waves)
  References: `.omo/plans/perfumery-ai-engine.md` (approved, 11 todos); `.omo/drafts/perfumery-ai-engine.md` findings section; AGENTS.md "Adding a new material" 4-location pattern
  Acceptance criteria: `engine/kb_schema.py` exists with CREATE TABLE statements; `engine/kb_migrate.py` exists; `python -c "from engine.kb_schema import MATERIALS_TABLE; print(MATERIALS_TABLE)"` succeeds; ruff check clean on new files
  QA scenarios: happy — schema validates (no syntax errors, all FK constraints consistent); failure — missing source → migration skips gracefully
  Evidence: `.omo/evidence/rest-of-implementations/task-3-kb-schema.md`
  Commit: Y | feat(engine): kb_schema + kb_migrate — SQLite knowledge base

- [ ] **4. Track C continued (Wave 2): T2-T6 query APIs + rules + graph + estimator**
  What to do: Execute T2-T6 from `.omo/plans/perfumery-ai-engine.md`. T2: material query API with alias resolution (`engine/kb_rules_api.py`). T3: rules DB migration (archetypes from registry.py 30 archetypes, IFRA 119 limits, fatigue 30, shifts 25, skeletons 20+). T4: rules query API (`get_archetype`, `check_cross_family`, etc.). T5: interaction graph extension via pairing agents for uncovered material pairs (check inventory for uncovered pairs before spawning agents). T6: fragment-based property estimator (`engine/property_estimator.py` — Stein-Brown VP, Wildman-Crippen logP, deterministic).
  Must NOT do: run pairing agents for already-covered pairs (waste tokens); add ML or external dependencies
  Parallelization: Wave 2 | Blocked by: T3-C-1 | Blocks: T4-C-45
  References: `.omo/plans/perfumery-ai-engine.md` todos T2-T6; engine/thermo/antoine.py VP estimation patterns; engine/thermo/activity.py UNIFAC stub (for contrast with T6's Stein-Brown)
  Acceptance criteria: each module imports cleanly; `python -c "from engine.kb_rules_api import get_archetype; print(get_archetype('aromatic_fougere'))"` returns valid spec; fragment estimator gives deterministic VP/logP within known ranges for test materials
  QA scenarios: happy — `ruff check engine/kb_*.py engine/property_estimator.py` clean; pytest test files pass; failure — estate estimator produces negative VP on edge case → clamp to 1e-6 Pa floor
  Evidence: `.omo/evidence/rest-of-implementations/task-4-kb-t2t6.md`
  Commit: Y | feat(engine): kb_rules_api + kb_sync + property_estimator

- [ ] **5. Track C continued (Wave 3-4): T7-T10 formula memory + failure registry + brain + sync**
  What to do: Execute T7-T10 from `.omo/plans/perfumery-ai-engine.md`. T7: formula memory schema + API (store formulas, pipeline results, evaluations). T8: failure registry pattern detector (11 encoded patterns from AGENTS.md F1-F11, auto-accumulation). T9: agent query API / "perfumery brain" (`engine/perfumery_brain.py` — recommend, compatibility, replace, evaluate). T10: sync script + pipeline parity tests (`scripts/rebuild_kb.py` or similar — zero-regression from existing dicts).
  Must NOT do: implement auto-formulation (brain is query/recommend only)
  Parallelization: Wave 3 (T7-T9) → Wave 4 (T10 with pipeline parity) | Blocked by: T4-C-23 | Blocks: T6-C-6
  References: `.omo/plans/perfumery-ai-engine.md` todos T7-T10; AGENTS.md "Agent Failure Registry" F1-F11
  Acceptance criteria: T10 sync script run → all existing pipeline dicts regenerate identically; pytest parity test: `tests/test_kb_parity.py` comparing direct-dict vs DB-generated for all 7 sources
  QA scenarios: happy — `python scripts/rebuild_kb.py` exits 0, `pytest tests/test_kb_parity.py -q` all pass; failure — any mismatch → diff reported, fix migration
  Evidence: `.omo/evidence/rest-of-implementations/task-5-kb-t7t10.md`
  Commit: Y | feat(engine): formula_memory + failure_registry + perfumery_brain + kb_sync

- [ ] **6. Track C final (Wave 4): T11 pipeline parity tests**
  What to do: Execute T11 from `.omo/plans/perfumery-ai-engine.md`. Comprehensive pipeline parity: run `pytest tests/test_kb_parity.py` covering all 7 data sources, zero-regression. Run full engine test suite: `pytest tests/ -q`. Run ruff check.
  Must NOT do: skip golden fixture tests
  Parallelization: Wave 4 | Blocked by: T5-C-710 | Blocks: none (final)
  References: `.omo/plans/perfumery-ai-engine.md` T11; tests/test_golden_formula_regression.py
  Acceptance criteria: `pytest tests/ -q` all pass; `ruff check engine/` clean; `python scripts/pipeline_audit.py project-verify --quick --json` PASS
  QA scenarios: happy — full test suite green with new kb_* modules; failure — any regressions → roll back that todo, keep others
  Evidence: `.omo/evidence/rest-of-implementations/task-6-kb-verify.md`
  Commit: N (part of T5 commit or separate verification-only commit)

- [ ] **7. Track D — final-audit-polish Wave A: literature/data gap survey + truths (Wave 2)**
  What to do: Execute Wave A from `.omo/plans/final-audit-polish-v1.md`. Systematic literature survey: PubChem + PubMed + Pyrfume for material ODT gaps, receptor data, hedonic data. Data gap survey: audit all YAML files, ODT_DATA dict, _PROFILES for completeness. Accumulate ≥500 meta-verified truths (each truth: material, property, value, source, evidence class). Write to `data/knowledge_graph/verified_truths.jsonl` or similar ledger.
  Must NOT do: skip verification — every truth needs cited source + evidence class
  Parallelization: Wave 2 | Blocked by: none | Blocks: T8-D-C
  References: `.omo/plans/final-audit-polish-v1.md` Wave A; AGENTS.md "Material Audit Checklist"; `engine/odor_thresholds.py` ODT_DATA; `data/materials/` YAML files
  Acceptance criteria: ≥500 truths ledger populated; each truth has source field (URL/DOI/file:line) and evidence class (EXACT/LITERATURE_DERIVED/EMPIRICALLY_CALIBRATED/HEURISTIC); gap report generated listing materials missing any key property
  QA scenarios: happy — `python -c "import json; truths = json.load(open('data/knowledge_graph/verified_truths.jsonl')); assert len(truths) >= 500"`; failure — <500 truths → continue accumulation
  Evidence: `.omo/evidence/rest-of-implementations/task-7-audit-waveA.md`
  Commit: Y | feat(data): verified truths ledger — 500+ meta-verified entries

- [ ] **8. Track D continued (Wave 3): Wave B — pipeline mass-testing 100+ formulas**
  What to do: Execute Wave B from `.omo/plans/final-audit-polish-v1.md`. Batch-test ALL 100+ formulas under `formulas/*.md` through pipeline: `python scripts/formula_release_gate.py --formula-file <path> --expected-concentrate-ul <ul> --brief auto --json` for each. Collate failures by category (IFRA, parse_error, missing_material, OAV_anomaly). Write batch report to `.omo/evidence/rest-of-implementations/task-8-mass-test-report.json`.
  Must NOT do: fix formulas inline — just COLLECT failures
  Parallelization: Wave 3 | Blocked by: none (independent of Wave A) | Blocks: T9-D-C
  References: `.omo/plans/final-audit-polish-v1.md` Wave B; scripts/formula_release_gate.py; formulas/*.md (100+ files)
  Acceptance criteria: all parsable formulas have gate JSON output (even if FAIL); failure report categorized; edge cases documented (accord headers parsing bug from AGENTS.md F4)
  QA scenarios: happy — mass-test script runs to completion, report JSON contains `n_total`, `n_parse_error`, `n_gate_fail`, `n_gate_pass`; failure — mass-test hangs on malformed formula → timeout + skip, report includes skipped
  Evidence: `.omo/evidence/rest-of-implementations/task-8-mass-test-report.json`
  Commit: Y | test(pipeline): mass-test 100+ formulas — batch gate audit

- [ ] **9. Track D continued (Wave 4): Waves C-D — gap remediation + weakness report**
  What to do: Execute Waves C-D from `.omo/plans/final-audit-polish-v1.md`. Wave C: remediate gaps from Wave A (literature survey) AND Wave B (pipeline failures). Every fix must be supported by literature, perfumer knowledge, chemistry, or thermodynamic logic. Wave D: weakness report — rank gaps by impact, assign effort, recommend next actions. Write to `docs/pipeline_weakness_report.md`.
  Must NOT do: leave gaps unremediated without documenting why; exceed max 1 retry per gap (stopping condition from draft)
  Parallelization: Wave 4 | Blocked by: T7-D-A, T8-D-B | Blocks: none (final)
  References: `.omo/plans/final-audit-polish-v1.md` Waves C-D; draft line 20 "≥500 meta-verified truths as stopping condition"; draft line 21 "every fix supported by literature, perfumer knowledge, chemistry, thermodynamic logic"
  Acceptance criteria: weakness report ranked by impact; ≥500 truths persisted; pipeline mass-test failure rate <50% (remediation target from draft)
  QA scenarios: happy — `python scripts/pipeline_audit.py project-verify --quick --json` PASS or PASS_WITH_SKIPS post-remediation; failure — stuck gap → document as limitation and continue
  Evidence: `.omo/evidence/rest-of-implementations/task-9-audit-waveCD.md`
  Commit: Y | docs: pipeline weakness report + gap remediation summary

- [ ] **10. Track E — Phase 1A domain foundation: migration + adapter + parser (Wave 1)**
  What to do: From `.omo/drafts/phase-1a-domain-foundation.md` exploration. Create new Alembic migration `20260717_0001_phase_1a_domain` in `backend/alembic/versions/`. Schema adjustments: (1) `lab_formula_components` add `role` VARCHAR (top/heart/base), (2) `lab_formula_components` add `unit` VARCHAR (mass/volume/drops), (3) `lab_formula_versions` ensure `version_number` auto-increments, (4) `lab_stock_solutions` add `remaining_mass_g` REAL. Implement `backend/app/adapters/legacy_formula_adapter.py` converting legacy `Perfume`/`Formula` JSON ingredients ↔ `LabFormulaComponent` rows. Implement `backend/app/services/formula_parser.py` for formula markdown parsing (handle established format from `luxury_formulas_2026-03-26.md`). Register material aliases from existing inventory.
  Must NOT do: add bottle/event/experiment API code (future phases); modify legacy `Perfume`/`Formula` models; change engine/workbench.py, engine/bottle_addition.py, engine/scientific_contract.py
  Parallelization: Wave 1 | Blocked by: none | Blocks: T11-E
  References: `.omo/drafts/phase-1a-domain-foundation.md` (158 lines); `backend/alembic/versions/20260716_0001_lab_beta.py` (existing migration to emulate); `backend/app/services/lab_service.py` (698 lines, bottle-event semantics); `luxury_formulas_2026-03-26.md` (formula format)
  Acceptance criteria: `poetry run alembic upgrade head` succeeds in backend/; `poetry run alembic downgrade -1` works; `poetry run pytest backend/tests/ -q` passes; `LegacyFormulaAdapter` round-trip test: legacy JSON → components → legacy JSON produces equivalent output
  QA scenarios: happy — migration applies cleanly, adapter round-trips 10 sample legacy formulas; failure — migration conflicts with existing DB → backup-before-migration catches it
  Evidence: `.omo/evidence/rest-of-implementations/task-10-phase1a.md`
  Commit: Y | feat(backend): Phase 1A domain foundation — migration + adapter + parser

- [ ] **11. Track E continued: endpoints + tests (Wave 2)**
  What to do: Add API endpoints in `backend/app/api/v1/endpoints/lab.py` (or new `domain.py`): (1) `POST /materials/import` — import materials from inventory.txt with alias registration, (2) `POST /formulas/import` — import formula markdown, parse to components, store as version, (3) `GET /materials/` — list materials with properties and aliases, (4) `GET /formulas/{id}/versions/` — list versions with components. Wire through router. Write tests in `backend/tests/unit/test_phase1a_endpoints.py`.
  Must NOT do: add bottle/event endpoints; add experiment/sample/observation endpoints; change existing `/api/v1/formulas/analyze-formula` or `/api/v1/formulas/calculate-addition` endpoints
  Parallelization: Wave 2 | Blocked by: T10-E | Blocks: none
  References: `.omo/drafts/phase-1a-domain-foundation.md` migration decisions; `backend/app/api/v1/endpoints/formulas.py` (existing endpoint pattern); `backend/tests/conftest.py` (async SQLite + httpx client setup)
  Acceptance criteria: all 4 endpoints return 200 with valid schema; `poetry run pytest backend/tests/unit/test_phase1a_endpoints.py -q` passes; `poetry run ruff check app` clean; `poetry run mypy app --ignore-missing-imports` clean
  QA scenarios: happy — import 255 materials, import formula markdown, list materials, list versions — all return valid JSON; failure — missing material in import → 400 with clear error message listing the missing names
  Evidence: `.omo/evidence/rest-of-implementations/task-11-phase1a-endpoints.md`
  Commit: Y | feat(backend): Phase 1A domain endpoints + tests

- [ ] **12. Track F — pipeline data quality (C5) + analysis output (C7) quick fixes (Wave 1)**
  What to do: From `.omo/drafts/pipeline-improvement.md`. C5 fixes: (1) fix sentinel ODTs: `engine/odor_thresholds.py` entries for "amber core" and "amber core accord" have odt_air=0.0 — set to reasonable estimate or mark as UNKNOWN, (2) fix "farnesene" ODT 100.0 → check Pyrfume/PubChem for better value, (3) add density data where available from PubChem/evaluation. C7 fixes: (1) replace hardcoded "Est. skin life: 6-8h" in `scripts/format_pipeline_analysis.py:272` with computed value from `engine/pipeline/release_scoring.py:1091-1096` temporal profile, (2) generalize IFRA check in `scripts/format_pipeline_analysis.py:306-315` (currently only Evernyl and Hedione HC hardcoded), (3) add cost-per-bottle section using price data from `engine/pipeline/release_scoring.py:130-143`, (4) fix block balance substring matching in `scripts/format_pipeline_analysis.py:365-369`.
  Must NOT do: modify formula_state.py or simulator.py physics (those are C1, Wave 3)
  Parallelization: Wave 1 | Blocked by: none | Blocks: T13-F-C2, T14-F-C1
  References: `.omo/drafts/pipeline-improvement.md` C5 and C7 findings (lines 76-93); `engine/odor_thresholds.py` lines 738, 743, 446; `scripts/format_pipeline_analysis.py` lines 272, 306-315, 365-369; `engine/pipeline/release_scoring.py` lines 130-143, 1091-1096
  Acceptance criteria: ODT 0.0 entries fixed (amber core, amber core accord); computed longevity renders (not hardcoded string); cost section added to analysis output; ruff check clean; pytest pass
  QA scenarios: happy — run a gated formula through format_pipeline_analysis, verify output has computed longevity + cost + generalized IFRA; failure — missing price data for a material → show "N/A" not crash
  Evidence: `.omo/evidence/rest-of-implementations/task-12-F-C57.md`
  Commit: Y | fix(pipeline): data quality fixes (C5) + analysis output fixes (C7)

- [ ] **13. Track F — gate logic cleanup (C2) + scoring recalibration (C3) (Wave 2)**
  What to do: From `.omo/drafts/pipeline-improvement.md`. C2: (1) remove 17 dead future_modules gates from `engine/pipeline/gates.py:4337-4682` (all return WARN because future_modules never installed), (2) fix `_safe_gate()` in `gates.py:199-211` — bare except clutch → log exception + convert to WARN with trace, (3) standardize 4 hedione checks with 3 conflicting ranges (gates.py:1320,1734,3470) → one range 5-20%, (4) raise skeleton OAV threshold from 0.5 to 1.0 (gates.py:3096), (5) fix "noise" gate references to missing modules. C3: (1) fix `opening_oav = total_oav` in `release_scoring.py:83` → use top-note window, (2) fix tenacity including heart (release_scoring.py:84) → base-only, (3) rename lift→top_dominance, character→family_alignment, versatility→oav_balance (add deprecation aliases preserving JSON output), (4) fix temporal_coherence penalizing linear profiles (division by 0.01 → use max delta).
  Must NOT do: change JSON output schema break fully (use deprecation aliases for renamed fields)
  Parallelization: Wave 2 | Blocked by: T12-F-C57 | Blocks: T14-F-C1, T15-F-C34
  References: `.omo/drafts/pipeline-improvement.md` C2 lines 47-55 and C3 lines 57-67; `engine/pipeline/gates.py` lines 199-211, 462, 1320, 1734, 3096, 3470, 4038, 4337-4682; `engine/pipeline/release_scoring.py` lines 83-157
  Acceptance criteria: 17 dead gates removed; ruff check clean (no undefined references to deleted gate functions); scoring test: `pytest tests/test_pipeline_gates.py tests/test_gate_aware_optimizer.py -q` passes with renamed axes; hedione check unified; skeleton threshold 1.0 → one existing formula that was "skeleton-ready" at 0.5 may now show as not-ready (TBD — document)
  QA scenarios: happy — pipeline gate on `--brief generic` still produces valid JSON with renamed scoring fields + deprecation aliases; failure — scoring mismatch on golden fixture → fix scoring to match fixture OR update fixture with justification
  Evidence: `.omo/evidence/rest-of-implementations/task-13-F-C23.md`
  Commit: Y | fix(pipeline): gate logic cleanup (C2) + scoring recalibration (C3)

- [ ] **14. Track F — physics accuracy (C1): UNIFAC + ethanol + ODT + evaporation (Wave 3)**
  What to do: From `.omo/drafts/pipeline-improvement.md` C1. (1) Implement UNIFAC subgroup decomposition in `engine/thermo/activity.py:66-76` (currently `pass` — stub) for ~130 inventory materials. Use subgroup table from published UNIFAC parameters. (2) Include ethanol in mole fractions in `engine/pipeline/formula_state.py:431-506` (currently fragrance-only, ethanol is 70-80% of final product). (3) Enable mixture-shifted ODT in pipeline OAV path at `engine/pipeline/formula_state.py:563` (calls `engine/perception/oav.py:64-85` which is implemented but never called). (4) Upgrade evaporation model in `engine/pipeline/simulator.py:67-79` from single-exponential to two-stage (ethanol-dominated rapid release 0-5min → diffusion-controlled fragrance release 5min+). (5) Raise skin temperature from 25°C to 32°C for skin applications (Clausius-Clapeyron: 7°C rise = 50-100% VP increase).
  Must NOT do: remove Hansen heuristic (keep as fallback if UNIFAC params missing for a material); break golden formula fixtures — pin current behavior with regression tests FIRST
  Parallelization: Wave 3 | Blocked by: T12-F-C57 | Blocks: T15-F-C34
  References: `.omo/drafts/pipeline-improvement.md` C1 lines 38-46 and librarian research lines 116-129; `engine/thermo/activity.py:66-76`; `engine/pipeline/formula_state.py:431-506, 563`; `engine/perception/oav.py:64-85`; `engine/pipeline/simulator.py:67-79`; `engine/thermo/antoine.py:36-43` (CC fallback); literature: Teixeira 2009-2010 two-stage evaporation, Almeida 2021 skin temperature 32°C, UNIFAC-Dortmund 95.4% agreement on 65 mixtures
  Acceptance criteria: UNIFAC γ ≠ Hansen heuristic for at least 80% of materials (measurable difference); ethanol mole fraction changes all mole fraction values; mixture-shifted ODT produces different OAVs; two-stage evaporation shows ethanol spike in window 1; `pytest tests/test_pipeline_formula_state.py tests/test_diffusion_regression.py -q` passes (regression tests pinning pre-change behavior FIRST)
  QA scenarios: happy — golden formula fixture OAV values shift (but π relative ranking preserved); failure — UNIFAC param missing for >40 materials → keep Hansen fallback, document coverage
  Evidence: `.omo/evidence/rest-of-implementations/task-14-F-C1.md`
  Commit: Y | feat(pipeline): UNIFAC γ + ethanol mole fractions + mixture-shifted ODT + two-stage evaporation + skin temp 32°C

- [ ] **15. Track F — intervention engine (C4) + scoring finalization (Wave 4)**
  What to do: From `.omo/drafts/pipeline-improvement.md` C4. (1) Add dose-reduction path to `engine/formula_recommendations.py:1089-1100` (currently only ADD/INCREASE/REBALANCE — `safety` axis has empty candidates). (2) Fix perturbation floor `engine/pipeline/robustness.py:100` — `max(5.0, amount * 0.05)` is 500% for 1µL trace materials → use `max(0.5, amount * 0.05)` or proportional floor. (3) Fix single-donor bias `engine/pipeline/robustness.py:141-154` — largest material always absorbs all perturbation cost → distribute proportionally. (4) Extend robustness testing from top-window-only to include heart and drydown windows. (5) Add temperature perturbation (±5°C test alongside dosing ±5%). (6) Fill 3 empty recommendation axes: perceptual_clarity (OAV ratio analysis), luxury (premium-material indicators), safety (IFRA edge detection).
  Must NOT do: break existing intervention trial test expectations
  Parallelization: Wave 4 | Blocked by: T13-F-C23, T14-F-C1 | Blocks: T16-F-C6
  References: `.omo/drafts/pipeline-improvement.md` C4 lines 68-74; `engine/formula_recommendations.py:1089-1100`; `engine/pipeline/robustness.py:100, 141-154, 248-271`
  Acceptance criteria: recommendation engine returns DECREASE candidates for overdose materials; perturbation tests for trace materials are proportional (not 500%); temperature perturbation tests run alongside dosing; `pytest tests/test_interventions.py tests/test_pipeline_interventions.py tests/test_pipeline_robustness.py -q` passes
  QA scenarios: happy — `python scripts/intervention_recommend.py --formula-file formulas/Bleu_Carbon_Max_30mL_EDP.md` returns safety/cost/hedonic recommendations; failure — empty recommendation → trace warning, not crash
  Evidence: `.omo/evidence/rest-of-implementations/task-15-F-C4.md`
  Commit: Y | feat(pipeline): intervention dose-reduction + robustness fixes + temperature perturbation

- [ ] **16. Track F — architecture (C6): split gates.py + remove dead code (Wave 5)**
  What to do: From `.omo/drafts/pipeline-improvement.md` C6. (1) Split `engine/pipeline/gates.py` (4710 lines) into: `engine/pipeline/gates/__init__.py` (re-exports), `engine/pipeline/gates/_core.py` (_safe_gate, _result, GateRegistry, gate runner), `engine/pipeline/gates/_safety.py` (IFRA, allergen, dermal), `engine/pipeline/gates/_physics.py` (OAV, headspace, pyramid, volatility), `engine/pipeline/gates/_family.py` (family drift, perfume_knowledge, pyramid_targets), `engine/pipeline/gates/_intelligence.py` (oav_intelligence, hedonic, emotional), `engine/pipeline/gates/_quality.py` (data quality, citation, coverage). (2) Remove dead oav_intelligence.py code — 752 lines, 95% dead (only `_minimal_intelligence_result()` executes). (3) Add gate phasing: preflight → safety → OAV physics → family/literature → future_modules (short-circuit on FAIL in early phases). (4) Write test for gate runner phasing: `tests/test_gate_phasing.py`.
  Must NOT do: change gate behavior — split is structural only (verify with gate parity test against current monolithic output)
  Parallelization: Wave 5 | Blocked by: T15-F-C34 | Blocks: none (final)
  References: `.omo/drafts/pipeline-improvement.md` C6 lines 82-87; `engine/pipeline/gates.py` (4710 lines); `engine/pipeline/oav_intelligence.py` (752 lines); `engine/pipeline/__init__.py` existing gate exports
  Acceptance criteria: all existing tests pass with new module structure (imports unchanged on caller side); `python scripts/formula_release_gate.py --formula-file formulas/Bleu_Carbon_Max_30mL_EDP.md --expected-concentrate-ul 6000 --brief vetiver_woody --json` produces identical JSON to monolithic version (gate parity test); ruff check clean; dead oav_intelligence removed
  QA scenarios: happy — gate parity test passes bit-for-bit; failure — any import error → fix re-exports in `__init__.py`; any behavioral difference → regression test catches it
  Evidence: `.omo/evidence/rest-of-implementations/task-16-F-C6.md`
  Commit: Y | refactor(pipeline): split gates.py into gates/ subpackage + remove dead oav_intelligence

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] **F1. Plan compliance audit** — every todo has references + acceptance criteria + QA; no skipped dependency; wave dependency matrix consistent. Run: `python scripts/pipeline_audit.py project-verify --quick --json | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('completion_gate','CHECK_FAILED'))"` returns PASS.
- [ ] **F2. Code quality review** — ruff check engine/ scripts/ tests/ backend/app/ clean; basedpyright on all changed files 0 errors; mypy on backend/app/ (per AGENTS.md: `cd backend && poetry run mypy app --ignore-missing-imports`).
- [ ] **F3. Real manual QA** — pipeline gate on 3 representative formulas (one from each family): `python scripts/formula_release_gate.py --formula-file formulas/<formula>.md --expected-concentrate-ul 6000 --brief <family> --json > output.json && python scripts/format_pipeline_analysis.py --input output.json` — all produce valid analysis. Backend: `curl http://localhost:8000/docs` returns OpenAPI.
- [ ] **F4. Scope fidelity** — verify no new pipeline scripts were created; engine/workbench.py + engine/bottle_addition.py + engine/scientific_contract.py unchanged (git diff against master); verify track C no auto-formulation code; verify track E no bottle/event API code.

## Commit strategy
- One commit per todo (atomic, independently revertible)
- T0 (Cade prerequisite) → `feat(inventory): add Cade Oil Rectified 1%`
- T1 (Cassis Iris) → `feat(formula): Cassis Iris Smoke 30mL EdP`
- T2 (Aventus Chypre) → `feat(formula): Aventus Chypre Fruity 30mL EdP`
- T3-T6 (perfumery-ai-engine) → 4 atomic commits per the referenced plan
- T7-T9 (final-audit-polish) → 3 atomic commits per the referenced plan
- T10-T11 (Phase 1A domain) → 2 commits
- T12-T16 (pipeline improvement) → 5 commits per component

Total: ~20 commits across 6 tracks.

## Success criteria
1. `ruff check engine/ scripts/ tests/ backend/app/` = All checks passed
2. `pytest tests/ -q` from repo root = all pass (engine tests)
3. `cd backend && poetry run pytest --cov=app --cov-report=term` = all pass (backend tests)
4. `python scripts/pipeline_audit.py project-verify --quick --json` → completion_gate PASS
5. Track A: Cassis_Iris_Smoke_30mL_EdP.md exists + gated + analysis appended
6. Track B: Aventus_Chypre_Fruity_30mL_EdP.md exists + gated + analysis appended
7. Track C: `python -c "from engine.kb_schema import *; from engine.perfumery_brain import *; print('KB OK')"` succeeds
8. Track D: ≥500 verified truths ledger populated; weakness report written
9. Track E: `cd backend && poetry run alembic upgrade head` succeeds; all 4 endpoints return 200
10. Track F: gate parity test passes (split gates.py produces identical JSON to monolithic); scoring axes renamed with deprecation aliases; UNIFAC γ ≠ Hansen for >80% of materials
