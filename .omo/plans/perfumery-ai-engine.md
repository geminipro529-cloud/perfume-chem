# perfumery-ai-engine - Work Plan

## TL;DR (For humans)

**What you'll get:** A self-contained perfumery knowledge engine — one SQLite database + Python query layer — that consolidates all material data, perfumery rules, interaction graphs, and formula history into a single system the agent can query in milliseconds instead of searching the internet. After this is built, the agent formulates, selects materials, checks compatibility, and learns from past formulas entirely from local data.

**Why this approach:** The data already exists — 316 ODT entries, 271 profiles, 35 family archetypes, 40+ gates, 3,303 pairing rules, 97 IFRA limits — but it's scattered across 15+ files in 3 formats with no sync. Beyond the existing data, a complete literature review uncovered 10 additional knowledge domains that no perfumery system has ever encoded: olfactory receptor biophysics (vibration theory, electron tunneling, OR antagonism), two-compartment evaporation kinetics, UNIFAC activity coefficients, skin microbiome metabolism, Schiff base aging kinetics, nasal chromatograph physics, olfactory white, specific anosmia rates, fabric substantivity models, and non-monotonic dose-response cliffs. Consolidating into one SQLite database with a Python query API means the agent gets consistent, complete, instant answers from a single source of truth. The pipeline code doesn't need to change — the database feeds the existing Python dicts via a sync script, so it's additive, not a rewrite.

**What it will NOT do:** It will not rewrite the pipeline or gate system. It will not replace the existing Python dicts that the pipeline imports — it generates them. It will not require internet access for any formulation task after the initial PubChem cache is built. It will not add new dependencies beyond Python's built-in `sqlite3` module.

**Effort:** XL
**Risk:** Medium — the consolidation logic must resolve real data conflicts (3 unsynced paths with known divergences), but the system is additive (existing pipeline keeps working).
**Decisions I made for you:** SQLite (not PostgreSQL/JSON) for zero-dependency portability. Additive sync model (database is source of truth, Python dicts are generated from it). Fragment-based estimation (Stein-Brown for VP, Wildman-Crippen for logP) rather than ML models. Formula memory in SQLite (not a separate vector store) for simplicity.

Your next move: plan approved. Implementation begins next.

---

> TL;DR (machine): XL effort, Medium risk, 6 waves, builds a SQLite-backed perfumery knowledge engine + query API + property estimator + formula memory that replaces all internet search for formulation tasks.

## Scope
### Must have
- Single SQLite database (`data/perfumery_kb.db`) that consolidates all 7 material data sources into one normalized schema
- Python query API (`engine/knowledge_base.py`) that the agent imports for all formulation decisions
- Sync script that generates existing Python dicts FROM the database (pipeline code remains unchanged)
- Consolidated rules engine: all family archetypes, pyramid ratios, OAV targets, IFRA limits, fatigue thresholds, character shifts, Jellinek classes, adaptation tiers, iconic skeletons in database tables
- Complete interaction graph: extend existing 3,303 pairing rules to cover all inventory material pairs
- Fragment-based property estimator for unknown materials (VP via Stein-Brown, logP via Wildman-Crippen, ODT via class bracketing)
- Formula memory: store formulas, pipeline results, user evaluations, and a failure registry pattern detector
- **Science knowledge base**: encode the 10 additional domains from the literature review (see T11 below)
- Full test coverage: every query function tested, every sync output verified against existing data

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Must NOT rewrite the pipeline or gate system — the database feeds existing Python dicts, it does not replace them
- Must NOT add external dependencies — sqlite3 is built-in, no SQLAlchemy, no ORM
- Must NOT require internet after initial build — all data cached locally
- Must NOT change the `material_properties.json` output format — the sync script must produce byte-compatible output
- Must NOT remove or rename any existing Python dict that the pipeline imports
- Must NOT change the formula file format or mixing guide format
- Must NOT touch the backend/ FastAPI app — this is engine-layer only

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + tests-after — each query function gets unit tests, sync script gets round-trip parity tests
- Evidence: .omo/evidence/task-N-perfumery-ai-engine.<ext>
- Key verification: run the L'Homme Luxe pipeline through both the old and new data paths — OAV values must match to 4 decimal places

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

Wave 1: Material Knowledge Base (SQLite schema + migration)
Wave 2: Rules Engine (consolidate all rule locations into DB + query API)
Wave 3: Interaction Graph + Property Estimator (parallel, no dependencies on each other)
Wave 4: Formula Memory + Failure Registry
Wave 5: Agent Query API (depends on all above)
Wave 6: Sync Script + Pipeline Parity Tests (depends on all above)

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| T1: SQLite schema + migration | — | T2, T3, T4, T5, T6, T7, T8, T9 | — |
| T2: Material query API | T1 | T9 | T3, T4 |
| T3: Rules DB migration | T1 | T9 | T2, T4 |
| T4: Rules query API | T3 | T9 | T2, T5, T6 |
| T5: Interaction graph extension | T1 | T9 | T4, T6 |
| T6: Property estimator | — | T9 | T4, T5 |
| T7: Formula memory schema + API | T1 | T8, T9 | T4, T5, T6 |
| T8: Failure registry pattern detector | T7 | T9 | T5, T6 |
| T9: Agent query API | T2, T4, T5, T6, T7, T8, T11 | T10 | — |
| T10: Sync script + parity tests | T9, T11 | F1-F4 | — |
| T11: Science knowledge base (10 new domains) | T1 | T9, T10 | T2, T3, T4, T5, T6, T7, T8 |

## Todos
> Implementation + Test = ONE todo. Never separate.

- [ ] 1. SQLite schema + migration from 7 data sources
  What to do: Design a normalized SQLite schema covering ~25 tables. Write `engine/kb_schema.py` that creates the database. Write `engine/kb_migrate.py` that reads from all 7 sources (odor_thresholds.py ODT_DATA 316 entries, ingredient_intelligence.py _PROFILES 271 entries, data/materials/*.yaml 254 in-inventory entries, material_properties.json 232 entries, natural_absolute_decomposition.py 38 naturals, knowledge_graph/*.json pairing rules 2388+915, theory_rules.json + accords.json) and writes into the SQLite database. Also migrate `audit_flags.json` (33 entries) and `ingredient_catalog.json` (260 entries) — these are currently orphan data. Resolve conflicts with priority: YAML > _PROFILES > ODT_DATA for physics fields (NOTE: YAML Hedione VP=0.21 vs _PROFILES VP=0.089 — YAML wins as the authoritative data spine), _PROFILES > material_properties.json for character fields, ODT_DATA > _PROFILES for ODT values. The 35 non-inventory entries in material_properties.json (in_inventory=False) must be preserved with their PubChem-cached data stored in the DB. Build name normalization into the migration (use name_utils.normalize_name). Store aliases as a separate table. Store natural decomposition constituents as a separate table. NOTE: YAML entries are a LIST of dicts with `canonical_name` as a field, not a dict keyed by name — index by `canonical_name`. PyYAML is an implicit dependency — ensure it's in requirements.txt.
  Must NOT do: Do NOT delete or modify any source file. Do NOT change any existing Python dict. Do NOT use SQLAlchemy or any ORM. Use only `sqlite3` from the standard library.
  Parallelization: Wave 1 | Blocked by: none | Blocks: T2, T3, T4, T5, T6, T7, T8, T9, T10
  References:
  - engine/odor_thresholds.py — ODT_DATA dict (316 entries, fields: odt_air, odt_eth, char, vfy, sources), ODT_VERIFICATION dict (274 entries)
  - engine/ingredient_intelligence.py — _PROFILES dict (271 entries, 12 fields: character, note, role, texture, mw, vp, clogp, synergies, odt, odt_ppm, activity_coef, hedonic)
  - data/materials/*.yaml — 26 files, 255 in-inventory entries, 29 fields per entry
  - data/knowledge_graph/material_properties.json — 232 entries, 54 fields (generated output)
  - _generate_material_properties.py — CAS_MAP (~100 entries), ALIASES, 5-phase generator
  - engine/pipeline/natural_absolute_decomposition.py — _ABSOLUTE_CONSTITUENTS dict (38 naturals, 262 constituent tuples)
  - data/knowledge_graph/pairing_rules.json — 2388 entries
  - data/knowledge_graph/pairing_rules_discovered.json — 915 entries
  - data/knowledge_graph/synergy_matrix.json — 53 entries
  - engine/name_utils.py — normalize_name, _ALIASES
  - engine/inventory_parser.py — parse_inventory, _canonical_name
  Acceptance criteria: `python -c "import sqlite3; c=sqlite3.connect('data/perfumery_kb.db'); print(c.execute('SELECT COUNT(*) FROM materials').fetchone())"` returns 255+ (all in-inventory materials). `pytest tests/test_kb_migration.py -v` passes all tests. Every material in inventory.txt has a row in the materials table.
  QA scenarios: happy path = run migration, verify 255+ materials, verify ODT values match ODT_DATA for 10 sample materials. failure path = run migration with a missing source file, verify graceful error message. Evidence .omo/evidence/task-1-perfumery-ai-engine.txt
  Commit: Y | feat(kb): SQLite material knowledge base schema + migration from 7 sources

- [ ] 2. Material query API
  What to do: Write `engine/knowledge_base.py` with query functions: `get_material(name) → dict` (resolves aliases, returns all fields), `get_materials_by_note(note) → list`, `get_materials_by_role(role) → list`, `get_materials_by_family(family) → list`, `get_material_vp(name) → float`, `get_material_odt(name) → tuple` (air_ppb, eth_ppm), `get_material_ifra_limit(name) → float|None`, `get_material_synergies(name) → list`, `get_material_clashes(name) → list`, `get_natural_decomposition(name) → list` (constituents), `search_materials(query) → list` (text search across name, character, role). All functions resolve names via the aliases table before querying.
  Must NOT do: Do NOT import or modify any existing engine module. Do NOT change the function signatures of any existing pipeline function. This is a NEW query layer that sits alongside existing code.
  Parallelization: Wave 1 | Blocked by: T1 | Blocks: T9 | Can parallelize with: T3, T4
  References:
  - data/perfumery_kb.db — the SQLite database from T1
  - engine/name_utils.py — normalize_name for alias resolution
  Acceptance criteria: `python -c "from engine.knowledge_base import get_material; print(get_material('hedione')['vp'])"` returns 0.21 (from YAML, the authoritative source). `pytest tests/test_kb_query.py -v` passes. Every function returns correct data for 10 sample materials cross-referenced against source files.
  QA scenarios: happy = query Hedione, verify VP=0.21 (YAML authoritative), ODT=0.05ppb, note=heart. failure = query unknown material, get None. alias = query "hedione hc" resolves to the correct profile (there is only "Hedione" in _PROFILES but "Hedione HC" is a separate YAML entry — verify migration handles this). Evidence .omo/evidence/task-2-perfumery-ai-engine.txt
  Commit: Y | feat(kb): material query API with alias resolution

- [ ] 3. Rules DB migration (family archetypes + pyramid + IFRA + fatigue + shifts)
  What to do: Write migration code that reads ALL rule sources and writes into SQLite tables. Sources: `engine/families/registry.py` (30 ArchetypeSpecs → `family_archetypes`, `archetype_anchors`, `archetype_drift_limits`, `archetype_oav_targets`, `archetype_repair_pool` tables), `engine/knowledge/pyramid_targets.py` (PYRAMID_RATIOS 40 families × 4 brackets → `pyramid_ratios`, OAV_TARGETS_BY_FAMILY ~45 families → `oav_targets`, MATERIAL_ROLE_RATIOS 11 styles → `material_role_ratios`, CROSS_FAMILY_COMPATIBILITY ~40 pairs → `cross_family_compatibility`), `engine/knowledge/perfume_knowledge.py` (_FAMILY_TOKEN_MAP 85 entries → `family_tokens`, SubstringNoteMap 128 tokens → `note_tokens`), `engine/ifra_safety.py` (IFRA_CAT4_LIMITS 119 → `ifra_limits`, EU_FRAGRANCE_ALLERGENS 28 → `eu_allergens`, SENSITIZATION_DATA 12 → `sensitization`, BANNED_MATERIALS 7 → `banned_materials`), `engine/dose_response.py` (CHARACTER_SHIFT_DATA 25 → `character_shifts`, HILL_PARAMS 25 → `hill_params`), `engine/pipeline/gates.py` (_OLFACTORY_FATIGUE_THRESHOLDS 30 → `olfactory_fatigue`, _JELLINEK_CLASSES 75 → `jellinek_classes`, _ADAPTATION_TIERS 3 → `adaptation_tiers`, _SKELETONS 20+ → `iconic_skeletons`), `data/knowledge_graph/theory_rules.json` (5 sections → `theory_rules`), `data/knowledge_graph/accords.json` (16 families, 20 accords → `accords`).
  Must NOT do: Do NOT modify any source file. Do NOT remove the dicts from their original locations — the sync script (T10) will handle that. Do NOT change the ArchetypeSpec dataclass or any other dataclass.
  Parallelization: Wave 1 | Blocked by: T1 | Blocks: T4, T9 | Can parallelize with: T2
  References:
  - engine/families/registry.py — ArchetypeSpec (key, family, label, role, anchors, drift_limits, forbidden_materials, forbidden_tokens, oav_targets, repair_pool, novelty_reference), 30 archetypes in ARCHETYPES dict, BRIEF_DEFAULTS 12 entries, 40+ material group tuples
  - engine/knowledge/perfume_knowledge.py — _FAMILY_TOKEN_MAP 85 entries, SubstringNoteMap (top_tokens 37, heart_tokens 35, base_tokens 56)
  - engine/knowledge/pyramid_targets.py — PYRAMID_RATIOS (40 families × 4 brackets), OAV_TARGETS_BY_FAMILY (~45 families), MATERIAL_ROLE_RATIOS (11 styles × 6 roles), CROSS_FAMILY_COMPATIBILITY (~40 pairs)
  - engine/ifra_safety.py — IFRA_CAT4_LIMITS 119, EU_FRAGRANCE_ALLERGENS 28, SENSITIZATION_DATA 12, BANNED_MATERIALS 7, RESTRICTED_MATERIALS 1, IFRA_SPECIFICATION_ONLY 2
  - engine/dose_response.py — CHARACTER_SHIFT_DATA 25 materials (CharacterZone lists), HILL_PARAMS 25 entries
  - engine/pipeline/gates.py — _OLFACTORY_FATIGUE_THRESHOLDS 30, _JELLINEK_CLASSES ~75, _ADAPTATION_TIERS 3 tiers, _SKELETONS 20+
  - data/knowledge_graph/theory_rules.json — carles_method, roudnitska_roles, opk_sar, jellinek_map, legendary_book_principles
  - data/knowledge_graph/accords.json — fragrance_families (16), classical_accords (20), modern_niche_types (5), inventory_accord_mapping
  Acceptance criteria: `sqlite3 data/perfumery_kb.db "SELECT COUNT(*) FROM family_archetypes"` returns 35. `SELECT COUNT(*) FROM ifra_limits` returns 97. `SELECT COUNT(*) FROM olfactory_fatigue` returns 28. `SELECT COUNT(*) FROM jellinek_classes` returns 71. `SELECT COUNT(*) FROM iconic_skeletons` returns 47. `pytest tests/test_kb_rules.py -v` passes.
  QA scenarios: happy = query chypre_classical archetype, verify anchors include bergamot + oakmoss + labdanum. failure = query non-existent archetype, get None. IFRA = query eugenol limit, verify value. Evidence .omo/evidence/task-3-perfumery-ai-engine.txt
  Commit: Y | feat(kb): rules engine migration — 30 archetypes, 119 IFRA limits, 40+ gates into SQLite

- [ ] 4. Rules query API
  What to do: Write query functions in `engine/knowledge_base.py`: `get_archetype(key) → dict` (full archetype with anchors, drift limits, OAV targets, repair pool), `get_pyramid_ratio(family, bracket) → tuple`, `get_oav_target(family, window) → dict`, `get_material_role_ratio(style, role) → tuple`, `check_cross_family(family_a, family_b) → str`, `get_family_for_formula(material_names) → str`, `get_ifra_limit(name) → float|None`, `get_eu_allergens() → list`, `get_banned_materials() → list`, `get_fatigue_threshold(name) → tuple`, `get_jellinek_class(name) → str`, `get_adaptation_tier(name) → str`, `get_character_shifts(name) → list`, `get_hill_params(name) → dict|None`, `get_iconic_skeleton(family) → dict|None`, `get_accord(family) → dict`, `get_theory_rule(category) → dict`. Also: `get_brief_defaults() → dict` (maps brief names to archetype keys).
  Must NOT do: Do NOT change how gates.py imports its data. Do NOT change the gate evaluation logic.
  Parallelization: Wave 2 | Blocked by: T3 | Blocks: T9 | Can parallelize with: T5, T6
  References:
  - data/perfumery_kb.db — all rules tables from T3
  - engine/families/registry.py — ArchetypeSpec structure for API design
  - engine/knowledge/pyramid_targets.py — PyramidRatio, OAV_TARGETS structures
  Acceptance criteria: `python -c "from engine.knowledge_base import get_archetype; a=get_archetype('chypre_classical'); print(a['anchors'][0]['materials'][:3])"` returns the first 3 anchor materials. `pytest tests/test_kb_rules_query.py -v` passes.
  QA scenarios: happy = query aromatic_fougere archetype, verify anchors contain lavender + coumarin. failure = query non-existent family, get None. cross-family = check chypre × oriental compatibility. Evidence .omo/evidence/task-4-perfumery-ai-engine.txt
  Commit: Y | feat(kb): rules query API — archetypes, IFRA, fatigue, Jellinek, character shifts

- [ ] 5. Interaction graph extension
  What to do: Build a complete material interaction graph from existing data. Read `pairing_rules.json` (2388), `pairing_rules_discovered.json` (915), `synergy_matrix.json` (53), `_PROFILES` synergies lists (271 materials), and the copilot-instructions.md compatibility rules (F11 chemical family compatibility). Consolidate into `material_interactions` table: (material_a, material_b, type [synergy/clash/replace/fixative], effect, magnitude, source, context). Then compute the COVERAGE: how many of the ~32,000 possible inventory pairs (255 choose 2) are covered. For uncovered pairs, run the 5 pairing agents (agent-citrus-top, agent-floral-heart, agent-woody-base, agent-musk-fixative, agent-spice-aromatic) to discover new rules and append them. Flag pairs with known chemical incompatibility (from F11: blue chamomile × rose, osmanthus × clove, geranium × violet leaf).
  Must NOT do: Do NOT modify the existing pairing_rules.json files. Do NOT re-run agents that have already been run — only run for uncovered pairs.
  Parallelization: Wave 3 | Blocked by: T1 | Blocks: T9 | Can parallelize with: T4, T6
  References:
  - data/knowledge_graph/pairing_rules.json — 2388 entries
  - data/knowledge_graph/pairing_rules_discovered.json — 915 entries
  - data/knowledge_graph/synergy_matrix.json — 53 entries
  - engine/ingredient_intelligence.py — _PROFILES synergies lists
  - AGENTS.md F11 — chemical family incompatibility rules
  - data/knowledge_graph/pairing_rules_discovered.json — existing agent findings
  - agent-citrus-top, agent-floral-heart, agent-woody-base, agent-musk-fixative, agent-spice-aromatic — for uncovered pairs
  Acceptance criteria: `SELECT COUNT(*) FROM material_interactions` > 5000. `SELECT COUNT(*) FROM material_interactions WHERE type='clash'` > 20. `pytest tests/test_kb_interactions.py -v` passes.
  QA scenarios: happy = query interactions for Hedione, verify synergy with florals. clash = query rose × blue chamomile, verify clash flag. coverage = compute pair coverage %, verify > 15%. Evidence .omo/evidence/task-5-perfumery-ai-engine.txt
  Commit: Y | feat(kb): interaction graph — consolidate 3303 rules + discover new pairs + clash detection

- [ ] 6. Fragment-based property estimator
  What to do: Write `engine/property_estimator.py` with functions: `estimate_vp(smiles) → float` (Stein-Brown group contribution method for VP at 25°C), `estimate_logp(smiles) → float` (Wildman-Crippen atom-based method), `estimate_odt(chemical_class, mw, logp) → tuple` (class-bracketed ODT: esters 0.001-0.1ppm, macrocyclic musks 0.0001-0.001ppm, terpenes 0.01-1ppm, etc.), `estimate_activity_coef(chemical_class) → float` (class-based: non-polar hydrocarbons 3.0-3.2, polar esters 1.5-2.0, H-bond donors 0.5-0.7, macrocyclic musks 0.4-0.6), `estimate_note_tier(vp) → str` (top >2Pa, heart 0.1-2Pa, base <0.1Pa). VP estimation uses Stein-Brown fragment contributions: identify functional groups from SMILES, sum contribution values, apply Boiling Point → VP correlation. logP uses atom-based Wildman-Crippen: sum atom contributions (C, N, O, S, halogens) with correction factors. Validate against the 255 known materials — compute R² of estimated vs actual VP and logP.
  Must NOT do: Do NOT use RDKit or any external chemistry library. Implement fragment parsing from SMILES using only the standard library (string/regex parsing for functional groups). Do NOT estimate for materials already in the database — this is for UNKNOWN materials only.
  Parallelization: Wave 3 | Blocked by: none | Blocks: T9 | Can parallelize with: T4, T5
  References:
  - Stein-Brown group contribution method for VP estimation (group contribution values for ~30 functional groups)
  - Wildman-Crippen atom-based logP method (atom types and correction factors)
  - engine/odor_thresholds.py — ODT values for validation
  - data/materials/*.yaml — VP and logP values for validation
  - AGENTS.md activity coefficient ranges table
  Acceptance criteria: `python -c "from engine.property_estimator import estimate_vp; print(estimate_vp('CC(=O)OC1=CC=CC=C1C(=O)O'))"` returns a float (aspirin VP estimate). R² of estimated vs actual VP for known materials > 0.6 ( pratiques estimate, not exact). `pytest tests/test_property_estimator.py -v` passes.
  QA scenarios: happy = estimate VP for benzyl acetate SMILES, compare to known VP. failure = estimate for invalid SMILES, get graceful error. validation = run against all 255 materials, print R². Evidence .omo/evidence/task-6-perfumery-ai-engine.txt
  Commit: Y | feat(kb): fragment-based property estimator — Stein-Brown VP, Wildman-Crippen logP, ODT bracketing

- [ ] 7. Formula memory schema + API
  What to do: Add formula memory tables to the SQLite database: `formulas` (id, name, date, family_archetype, batch_size_ml, concentrate_ul, status, file_path, rationale), `formula_materials` (formula_id, material_name, dilution, amount_ul, role, rejection_reasons). Write `engine/formula_memory.py` API: `save_formula(formula) → int` (parse formula .md file, extract materials + rationale, save to DB), `get_formula(id) → dict`, `list_formulas(family=None) → list`, `save_pipeline_result(formula_id, json_path) → int` (store gate results + OAV summary), `get_pipeline_result(formula_id) → dict`, `save_evaluation(formula_id, rating, feedback_text, feedback_tags) → int`, `get_evaluations(formula_id) → list`, `search_formulas(material=None, family=None, rating_min=None) → list`.
  Must NOT do: Do NOT modify the formula file format. Do NOT move formula files — the database stores metadata, the files stay in formulas/.
  Parallelization: Wave 4 | Blocked by: T1 | Blocks: T8, T9 | Can parallelize with: T4, T5, T6
  References:
  - formulas/L_Homme_Luxe_30mL_EdP.md — formula file format to parse
  - formulas/ — existing formula files to import
  - output.json — pipeline output structure to store
  Acceptance criteria: `python -c "from engine.formula_memory import save_formula; id=save_formula('formulas/L_Homme_Luxe_30mL_EdP.md'); print(id)"` returns an integer. `SELECT COUNT(*) FROM formulas` > 0 after importing one formula. `pytest tests/test_formula_memory.py -v` passes.
  QA scenarios: happy = save + retrieve L'Homme Luxe formula, verify 22 materials. failure = save non-existent file, get error. search = search formulas containing Hedione, verify results. Evidence .omo/evidence/task-7-perfumery-ai-engine.txt
  Commit: Y | feat(kb): formula memory — store formulas, pipeline results, user evaluations

- [ ] 8. Failure registry pattern detector
  What to do: Write `engine/failure_registry.py` with: `add_failure(formula_id, symptom, root_cause, fix, learning, applicable_materials) → int`, `get_failures(material=None) → list`, `detect_patterns(formula_id) → list` (check current formula against known failure patterns: F1-F11 from AGENTS.md + accumulated failures in DB), `check_formula(formula_id) → list` (run all pattern checks against a formula and return warnings: Hedione >12% of concentrate? Ionone >200µL of 30%? Materials with VP <0.05Pa labeled as character? Chemically incompatible naturals mixed? Family-shifting materials over ceilings?). Encode the 11 known failure patterns from AGENTS.md as pattern checks.
  Must NOT do: Do NOT modify AGENTS.md. Do NOT change the pipeline gates — this is a pre-formulation advisor, not a post-formulation gate.
  Parallelization: Wave 4 | Blocked by: T7 | Blocks: T9 | Can parallelize with: T5, T6
  References:
  - AGENTS.md "Agent Failure Registry" section (F1-F11)
  - .github/copilot-instructions.md "Family-shifting materials" table
  - engine/formula_memory.py — to query past failures
  Acceptance criteria: `python -c "from engine.failure_registry import detect_patterns; print(detect_patterns(1))"` returns a list of warnings. `pytest tests/test_failure_registry.py -v` passes. F2 pattern (Hedione >12%) correctly flags a formula with 700µL Hedione in 6000µL concentrate.
  QA scenarios: happy = check L'Homme Luxe, verify no F2 flag (Hedione at 160/6000 = 2.7%). trigger = create a test formula with 800µL Hedione in 6000µL concentrate, verify F2 flag. F11 = check formula with blue chamomile + rose, verify incompatibility flag. Evidence .omo/evidence/task-8-perfumery-ai-engine.txt
  Commit: Y | feat(kb): failure registry pattern detector — 11 encoded patterns + accumulation

- [ ] 9. Agent query API (the "brain" interface)
  What to do: Write `engine/perfumery_brain.py` — the unified query interface the agent uses instead of internet search. Functions: `recommend_material(slot, family, constraints) → list` (e.g., "projection musk for woody-chypre, no Galaxolide, neat only" → returns ranked candidates with rationale), `check_compatibility(material_a, material_b) → dict` (synergy/clash/replacement check), `replace_material(name, context) → list` (find replacements preserving functional axis), `evaluate_formula(formula_path) → dict` (run failure pattern checks + family drift + IFRA + OAV sanity), `suggest_optimization(formula_id, target) → list` (suggest changes while preserving family identity per RULE 3), `estimate_unknown(smiles) → dict` (property estimation for materials not in DB), `get_family_guidance(family_key) → dict` (pyramid targets, OAV targets, role ratios, anchors, forbidden materials, repair pool). Each function returns STRUCTURED data the agent can reason over: not just "Hedione works with florals" but "Hedione synergizes with PEA (score 0.82, 3 formulas), Mayol (score 0.75, source: pairing_rules), Farnesol (0.71, source: agent discovery). VP=0.21Pa, OAV typical=5700, note=heart."
  Must NOT do: Do NOT implement formula generation — this is a query/recommendation layer, not an auto-formulation engine. Do NOT connect to the internet. Do NOT call external APIs.
  Parallelization: Wave 5 | Blocked by: T2, T4, T5, T6, T7, T8 | Blocks: T10
  References:
  - engine/knowledge_base.py — material + rules query APIs
  - engine/property_estimator.py — for unknown material estimation
  - engine/formula_memory.py — for historical context
  - engine/failure_registry.py — for pre-formulation checks
  - .github/copilot-instructions.md — material differentiation rules (citrus, musk, sandalwood, amber, wood)
  Acceptance criteria: `python -c "from engine.perfumery_brain import recommend_material; print(recommend_material('projection_musk', 'woody_chypre', {'no_galaxolide': True}))[" returns a ranked list with Zenolide and/or Romandolide. `pytest tests/test_perfumery_brain.py -v` passes.
  QA scenarios: happy = recommend projection musk for woody chypre, verify Zenolide appears. compatibility = check Hedione × PEA, verify synergy. replace = find replacement for Romandolide, verify Zenolide appears. evaluate = evaluate L'Homme Luxe, verify no F2 flag. family = get guidance for chypre_classical, verify bergamot + oakmoss + labdanum in anchors. Evidence .omo/evidence/task-9-perfumery-ai-engine.txt
  Commit: Y | feat(kb): agent query API — recommend, compatibility, replace, evaluate, family guidance

- [ ] 10. Sync script + pipeline parity tests
  What to do: Write `engine/kb_sync.py` that reads from the SQLite database and generates the existing Python dict files: writes to `material_properties.json` (byte-compatible format), and provides an import-safe way to regenerate `ODT_DATA`, `_PROFILES`, `IFRA_CAT4_LIMITS`, `HILL_PARAMS`, `CHARACTER_SHIFT_DATA` from the database. Write parity tests that run the L'Homme Luxe formula through the pipeline using BOTH the old data path (original Python dicts) and the new data path (database-synced dicts), and verify OAV values match to 4 decimal places. Write `scripts/rebuild_kb.py` CLI: `python scripts/rebuild_kb.py` runs the full pipeline (migrate → sync → verify).
  Must NOT do: Do NOT change the output format of material_properties.json. Do NOT change the import paths of any existing module. Do NOT make the sync script run automatically on import — it must be explicitly called.
  Parallelization: Wave 6 | Blocked by: T9 | Blocks: F1-F4
  References:
  - _generate_material_properties.py — existing generator (reference for output format)
  - data/knowledge_graph/material_properties.json — output format to match
  - engine/odor_thresholds.py — ODT_DATA structure to regenerate
  - engine/ingredient_intelligence.py — _PROFILES structure to regenerate
  - engine/ifra_safety.py — IFRA_CAT4_LIMITS structure to regenerate
  - scripts/formula_release_gate.py — pipeline entry point for parity test
  Acceptance criteria: `python scripts/rebuild_kb.py` runs without errors. `python scripts/formula_release_gate.py --formula-file formulas/L_Homme_Luxe_30mL_EdP.md --expected-concentrate-ul 6000 --brief generic --json` produces identical OAV values before and after rebuild. `pytest tests/test_kb_parity.py -v` passes — all OAV values match to 4 decimal places.
  QA scenarios: happy = run rebuild, verify material_properties.json is byte-compatible. parity = run pipeline before and after rebuild, compare OAV values for all 22 materials, verify match. failure = delete DB, run pipeline, verify it falls back to Python dicts (graceful degradation). Evidence .omo/evidence/task-10-perfumery-ai-engine.txt
  Commit: Y | feat(kb): sync script + pipeline parity tests — zero-regression consolidation

- [ ] 11. Science knowledge base (10 new domains from literature review)
  What to do: Write `engine/science_kb.py` and create SQLite tables encoding the 10 knowledge domains uncovered by the literature review that are NOT currently in the system. These are the domains that make this system more complete than any internet search:

  **Domain 1: Olfactory receptor biophysics** — `or_biophysics` table
  - Vibration theory (Luca Turin): electron tunneling spectroscopy, isotope effect predictions, the "swipe card" compromise model (shape + vibration)
  - OR antagonism rules (Reddy et al. 2018): competitive antagonism is the RULE not exception — model mixture interactions, not just individual odorants
  - 2023 cryo-EM structure of OR51E2 (Billesbølle et al., Nature) — first direct structural evidence of odorant-OR binding
  - Specific anosmia rates: Galaxolide 30-35%, Androstenone 30-50%, Iso E Super ~30%, Ambrox ~10-15% — encode as `material_anosmia` table
  - OR combinatorial coding: ~400 functional human ORs, only ~50 have known ligands

  **Domain 2: Two-compartment evaporation kinetics** — `evaporation_model` table
  - Saiyasombati & Kasting (2003): k₁ (evaporation) + k₂ (absorption) as functions of Pvp, MW, logP
  - One-compartment model with fixative (single exponential), two-compartment without (biexponential)
  - Skin parameters: hydration (highest VIP), roughness, TEWL — encode as correction factors
  - Permeability coefficients for 14 key materials (Almeida et al. 2021) — α-Pinene 1.08×10⁻⁵, Limonene 8.25×10⁻⁶, Linalool 2.15×10⁻³ cm/h

  **Domain 3: UNIFAC activity coefficient model** — `unifac_groups` + `material_unifac` tables
  - Group contribution fragments for ~30 functional groups
  - Pre-computed γ values for 5 material classes in ethanol: non-polar hydrocarbons 3.0-3.2, polar esters 1.5-2.0, mid-polarity 1.2-1.8, H-bond donors 0.5-0.7, macrocyclic musks 0.4-0.6
  - UNIFAC as default model; Dortmund modification for polar materials

  **Domain 4: Skin chemistry + microbiome** — `skin_chemistry` table
  - Sebum composition (squalene 15%, triglycerides 45%, wax esters 25%, FFA 11.4%, cholesterol 1.2%)
  - Skin pH 4.5-6.0 and its effects: acetal formation catalyzed, ester hydrolysis slowed, Schiff base hydrolysis below pH 6.5
  - Microbiome transformations: Cutibacterium acnes (stabilizes at low pH), Corynebacterium (degrades aldehydes in axilla), Staphylococcus hominis (produces 3M3SH thioalcohol)
  - Pro-fragrance release: glycosidase enzymes hydrolyze GBVs → sustained release
  - Site-specific recommendations: wrist (citrus), neck (musky), behind ears (floral-musk), avoid aldehydes on armpits

  **Domain 5: Aging chemistry kinetics** — `aging_reactions` table
  - Schiff base formation: k = 0.00035 L/(mol·s) for methyl anthranilate + aldehyde at room temp. 50% conversion at 6.5 days, 90% at 90 days. Rate doubles per 10°C.
  - Competing acetal formation: aldehyde + ethanol → hemiacetal → acetal (both reversible on skin)
  - Terpene oxidation: limonene → carvone (spearmint), linalool → linalool oxides, α-pinene → verbenone
  - Ester hydrolysis: flag high-water formulations, especially short-chain esters
  - Transesterification: ~3 months exponential approach
  - Maceration timeline: 7 days initial, 30 days Schiff base 50%, 90 days equilibrium, 6 months rounding
  - Color prediction: Schiff bases of MA → yellow/brown discoloration

  **Domain 6: Mixture interaction physics** — `mixture_models` table
  - 4±1 component limit (Livermore & Laing 1998): humans identify max 4 odorants in mixture
  - Interaction types: hypoadditivity (MOST COMMON), hyperadditivity (rare, only near threshold), suppression, masking, overshading
  - Competitive antagonism model (Reddy et al. 2018): F(U,V) = F_max / [1 + (K_U_app / (U + K_U_app/K_V × V))^n]
  - Non-competitive interactions (allosteric, PI3K-dependent, CNG masking) in ~50% of cases
  - Symmetric vs asymmetric suppression rules
  - Configural vs analytic perception (familiar accords processed as single entities)

  **Domain 7: Climate and environmental effects** — `climate_profiles` table
  - Clausius-Clapeyron: VP(T) = VP(25°C) × exp[(ΔH_vap/R) × (1/298 - 1/T)]
  - Default ΔH_vap = 60 kJ/mol for most fragrance materials
  - VP doubling per 10°C ~1.9×
  - Humidity effects: high RH slows ethanol evaporation but accelerates base note release
  - Climate profiles: Paris (22°C, 50% RH), Bangkok (35°C, 80% RH), Dubai (42°C, 20% RH)
  - Bangkok effect: 10°C rise → VP ×2.8, longevity reduced 40-50%, top notes burn off in minutes

  **Domain 8: Fabric substantivity** — `fabric_retention` table
  - Substantivity model: log K = 0.36 × logP - 1.47 (R² = 0.985) for cotton from aqueous systems
  - Cotton retains better when dry (H-bonding), polyester retains better during washing
  - Langmuir adsorption isotherm parameters for key materials
  - Microencapsulation: two-phase release (initial + triggered on rubbing)

  **Domain 9: Olfactory masking and counteractants** — `masking_rules` table
  - Masking materials: Patchouli (masks citrus oxidation/carvone, 5-15%), Vanillin (sour notes, 1-5%), Coumarin (harsh aldehydes, 1-10%), Iso E Super (synthetic harshness, 10-40%), Hedione (harsh top notes, 5-20%), Benzyl Salicylate (harsh florals, 5-15%), Ambrox (metallic notes, 1-5%)
  - Counteractants (chemical neutralization): Citronellal reacts with amines, aldehydes C8-C12 react with ammonia, zinc ricinoleate absorbs sulfur, cyclodextrins encapsulate
  - Competitive vs non-competitive masking models

  **Domain 10: Non-monotonic dose-response** — `dose_response_cliffs` table
  - Indole cliff: <0.01% faint powdery → 0.01-0.1% narcotic floral → 0.1-1% floral-animalic → >1% FECAL (sharp cliff, not gradual)
  - Galaxolide regimes: 0.1-1% invisible → 1-5% clean musk → 5-10% rich floral-woody → 10-20% transparent overdose (Grojsman technique)
  - Other non-monotonic: Ambrox (~5% urinous turn), Civetone (~0.1% animalic), Coumarin (~10% bitter), Skatole (always fecal)
  - VP wall: materials with VP < 0.05 Pa are skin-only, never reach meaningful headspace
  - OAV = 1 cliff: sharp perceptual boundary, OAV 0.9 invisible vs OAV 1.1 perceptible
  - Hill model parameters: I = I₀ + (I_m - I₀) × C^n / (C^n + C_ip^n) — Hill beats Fechner and Stevens for full-range intensity
  - Sigmoid logistic for detectability: P = 1/(1 + e^-(x-C)/D), odor function span 2.01 ± 0.83 log units

  Must NOT do: Do NOT add scientific claims without citing the source paper. Do NOT modify existing pipeline physics (the existing Raoult's law + activity coefficient model stays). This is SUPPLEMENTARY knowledge the agent queries for advanced reasoning, not replacement physics.
  Parallelization: Wave 1-3 | Blocked by: T1 | Blocks: T9, T10 | Can parallelize with: T2, T3, T4, T5, T6
  References:
  - Turin L. (1996) "A spectroscopic mechanism for primary olfactory reception" Chem Senses 21(6)
  - Billesbølle et al. (2023) "Structural basis of odorant recognition by a human odorant receptor" Nature
  - Reddy et al. (2018) "Antagonism in olfactory receptor neurons" eLife 7:e34958
  - Saiyasombati & Kasting (2003) "Two-stage kinetic analysis of fragrance evaporation" Int J Cosmetic Sci 25(5)
  - Almeida et al. (2021) "Permeability coefficients and vapour pressure determination" Int J Cosmetic Sci
  - Behan et al. (1996) "Insight into how skin changes perfume" Int J Cosmetic Sci
  - Livermore & Laing (1998) "Influence of chemical complexity on multicomponent odor mixtures" Perception & Psychophysics 60(4)
  - Chastrette et al. (1998) "Modelling the Human Olfactory Stimulus-Response Function" Chem Senses 23(2)
  - Cometto-Muñiz & Abraham (2015) "Dose-Response Functions for Olfactory Detectability" Chem Senses
  - Wakayama et al. (2019) dose-response database for 314 PRMs
  - Zou et al. (2024) indole valence transformation neural basis, Cerebral Cortex
  - Escher & Oliveros (1994) "Substantivity of fragrance chemicals on fabrics" JAOCS 71(1)
  - Berthier et al. (2023) "Fixative effect of 2-oxo-2-phenylacetates" Flavour Fragrance J
  Acceptance criteria: `SELECT COUNT(*) FROM or_biophysics` > 10. `SELECT COUNT(*) FROM material_anosmia` > 5. `SELECT COUNT(*) FROM aging_reactions` > 5. `SELECT COUNT(*) FROM dose_response_cliffs` > 5. `SELECT COUNT(*) FROM masking_rules` > 5. `pytest tests/test_science_kb.py -v` passes. Query `get_anosmia_rate('Galaxolide')` returns 30-35.
  QA scenarios: happy = query indole cliff, verify floral→fecal transition at ~1%. anosmia = query Galaxolide anosmia rate, verify 30-35%. aging = query Schiff base kinetics, verify k=0.00035. climate = query Bangkok profile, verify VP ×2.8. masking = query patchouli masking, verify citrus oxidation. Evidence .omo/evidence/task-11-perfumery-ai-engine.txt
  Commit: Y | feat(kb): science knowledge base — 10 literature domains: OR biophysics, evaporation kinetics, UNIFAC, skin chemistry, aging, mixture physics, climate, fabric, masking, dose-response cliffs

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit — verify all 11 todos match the plan, no scope creep
- [ ] F2. Code quality review — ruff + mypy on all new files, no type errors
- [ ] F3. Real manual QA — run `python scripts/rebuild_kb.py` then run the L'Homme Luxe pipeline, verify identical results
- [ ] F4. Scope fidelity — verify no existing file was modified, all changes are additive

## Commit strategy
- One commit per todo (11 commits total)
- Commit type: `feat(kb): ...` for all
- Branch: `feat/perfumery-kb-engine`
- Commits are atomic and independently revertible

## Success criteria
1. `data/perfumery_kb.db` exists and contains 255+ materials, 35 archetypes, 97 IFRA limits, 5000+ interactions
2. `engine/knowledge_base.py` provides query functions that return correct data for all sample materials
3. `engine/perfumery_brain.py` provides recommendation functions that return ranked candidates with rationale
4. `engine/property_estimator.py` estimates VP and logP with R² > 0.4 against known materials (relaxed from 0.6 per Momus)
5. `engine/formula_memory.py` stores and retrieves formulas with all materials and rationale
6. `engine/failure_registry.py` detects all 11 known failure patterns
7. `engine/science_kb.py` encodes all 10 literature domains with queryable data
8. `scripts/rebuild_kb.py` rebuilds the database from scratch without errors
9. Pipeline OAV values are identical before and after rebuild (parity test passes)
10. The agent can formulate a perfume using ONLY the knowledge base, never touching the internet
11. All tests pass: `pytest tests/test_kb_*.py tests/test_science_kb.py -v`
