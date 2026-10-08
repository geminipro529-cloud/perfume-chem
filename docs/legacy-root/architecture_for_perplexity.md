# Perfume Chemistry Engine — Complete Architecture & Module Map

## Overview

Two separate Python environments sharing no package manager:

| Scope | Entry | Package Manager | Location |
|-------|-------|----------------|----------|
| `engine/` + root scripts & pipelines | `import engine.xxx` | pip (`requirements.txt`) | repo root |
| `backend/` FastAPI app | `import app.xxx` | Poetry | `backend/` |

Engine is a namespace package (no `__init__.py`). All root scripts and pipelines manually add repo root to `sys.path` to resolve `engine.xxx` imports.

---

## MODULE MAP: Engine (`engine/`)

### CORE DATA LAYERS

| Module | File | What it does | Depends on |
|--------|------|-------------|------------|
| **ingredient_intelligence.py** | `engine/ingredient_intelligence.py` (2246 lines) | Master material profile DB: 13 perceptual character dimensions (0-10), physical properties (MW, VP, cLogP, ODT), functional tags (note, role, texture, synergies, avoid). Every material scored on warmth/sweetness/freshness/powdery/green/animalic/radiance/woody/spicy/floral/smoky/creamy/transparency. Sources: Arctander, PerfumersWorld, Carles method, Roudnitska, Jellinek quadrants. | `material_identity`, `name_utils`, `odor_thresholds` |
| **odor_thresholds.py** | `engine/odor_thresholds.py` (1180 lines) | ODT_DATA dict (material→odt_air_ppb, odt_eth_ppm) with verification tags (PEER_CROSS, PEER_SINGLE, PEER_EST, DERIVED, UNVERIFIED). ODT_VERIFICATION dict (metadata only). Used by pipeline formula_state._lookup_odt() and ingredient_intelligence auto-populate. Critical: last entry wins in ODT_DATA, so dict order matters. | `name_utils` |
| **material_resolver.py** | `engine/material_resolver.py` (63 lines) | Shared resolver: bridges profile spine + structured registry for material lookups. Returns ResolvedMaterial with canonical_name, profile, registry data. Used by gates, scoring, IFRA, formula_state. | `data_spine.loader`, `ingredient_intelligence`, `name_utils` |
| **name_utils.py** | `engine/name_utils.py` (100 lines) | Central name normalization. _ALIASES dict maps spelling variants→canonical form (e.g. "d-limonene"→"limonene", "iso-e-super"→"iso e super"). normalize_name() lowercases, strips whitespace, applies aliases. Used by EVERY module that does lookups. | None |
| **inventory_parser.py** | `engine/inventory_parser.py` (170 lines) | Parses `inventory.txt` into InventoryMaterial records. Deduplicates by keeping highest-dilution entry. _canonical_name() strips trailing parentheticals. Detects solvents. | None |
| **science_data.py** | `engine/science_data.py` (262 lines) | ScienceProfile dataclass: olfactory adaptation timescales, chemical stability flags (autoxidation, Schiff base, photodegradation), Hansen solubility parameters, skin partition coefficients. Sources: Ohloff, Sell, RIFM. | None |
| **chemical_data_validator.py** | `engine/chemical_data_validator.py` | Blocked/reason validation for chemicals. Used by optimizer, gates. | None |
| **material_identity.py** | `engine/material_identity.py` | resolve_material_identity() — used by ingredient_intelligence for profile resolution. | unknown |
| **schema_validator.py** | `engine/schema_validator.py` | Schema validation for material data | None |

### DATA_SPINE SUBPACKAGE (`engine/data_spine/`)

| File | What it does |
|------|-------------|
| `loader.py` | load_registry() — loads YAML material registry from `data/materials/<LETTER>.yaml` |
| `material.py` | Material data models |
| `migrate.py` | Data migration utilities |
| `perfumersworld_parser.py` | Parser for PerfumersWorld data |
| `audit.py` | Data spine audit utilities |

### THERMO SUBPACKAGE (`engine/thermo/`)

| File | What it does | Used by |
|------|-------------|---------|
| `activity.py` | `gamma()` — activity coefficient calculation (Modified Raoult's Law). Gamma ranges: non-polar hydrocarbons 3.0-3.2, polar esters 1.5-2.0, H-bond donors 0.5-0.7, macrocyclic musks 0.4-0.6. NEVER returns 1.0 silently. | `formula_state.py`, `oav_guard.py` |
| `antoine.py` | `vp_pa()` — vapor pressure via Antoine equation, `R_GAS` constant. Also Clausius-Clapeyron temperature correction (ΔHvap ≈ 60 kJ/mol, 10°C rise→VP×~1.9). | `formula_state.py` |
| `headspace.py` | Headspace concentration computation | simulator, gates |
| `phase.py` | `micro_phase_risk()` — phase separation risk assessment | `gates.py` |
| `trajectory.py` | Evaporation trajectory modeling | simulator, temporal |

### CHEMISTRY SUBPACKAGE (`engine/chemistry/`)

| File | What it does | Used by |
|------|-------------|---------|
| `maturation.py` | `predict_shelf_life_days()` — chemical maturation/shelf life prediction | `gates.py` |
| `photochem.py` | `photolysis_remaining_fraction()` — photodegradation assessment | `gates.py` |

### PERCEPTION SUBPACKAGE (`engine/perception/`)

| File | What it does | Used by |
|------|-------------|---------|
| `oav.py` | `oav()` — core OAV calculation (C/ODT), `perceived_intensity_stevens()` — Stevens Power Law intensity (I = k × C^n, n=0.2-0.6) | `formula_state.py` |
| `bulb.py` | Olfactory bulb signal processing models | pipeline |

### RECEPTOR SUBPACKAGE (`engine/receptor/`)

| File | What it does | Used by |
|------|-------------|---------|
| `binding.py` | `ligands_from_family()`, `or_occupancy()` — olfactory receptor binding models | `simulator.py` |
| `adaptation.py` | Olfactory adaptation timescale models | temporal analysis |
| `bulb.py` | Olfactory bulb processing | pipeline |

### DELIVERY SUBPACKAGE (`engine/delivery/`)

| File | What it does |
|------|-------------|
| `spray.py` | Spray physics/atomization models |
| `sniff.py` | Sniffing dynamics/airflow models |

### BIOLOGY SUBPACKAGE (`engine/biology/`)

| File | What it does |
|------|-------------|
| `genetics.py` | Olfactory genetics / receptor gene analysis |
| `microbiome.py` | Skin microbiome interaction models |

---

## MODULE MAP: Pipeline (`engine/pipeline/`)

This is the **central orchestrator** — the release gate pipeline that all formulas flow through.

```
                    ┌────────────────────────┐
                    │   formula_state.py      │  ◄── Core physics engine
                    │  (MaterialState,        │       builds canonical state from raw µL
                    │   FormulaState,          │       → active µL → mass → moles → mole fraction
                    │   build_formula_state)   │       → headspace ppm → OAV per material
                    └──────────┬─────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   simulator.py   │  │   gates.py       │  │  oav_authority   │
│  (5-window       │  │  (Release gates: │  │  (Canonical OAV  │
│   temporal       │  │   odt_coverage,  │  │   authority      │
│   evaporation)   │  │   oav_legibility,│  │   verdict        │
│  → opening, top, │  │   oav_scaling,   │  │   surface for    │
│    heart,        │  │   pyramid,       │  │   candidates)    │
│    late_heart,   │  │   safety_ifra,   │  │                  │
│    drydown)      │  │   robustness,    │  └──────────────────┘
└──────────────────┘  │   confidence,    │
                      │   family_drift,  │
                      │   perfumer_logic)│
                      └──────────┬───────┘
                                 │
                    ┌────────────▼───────────┐
                    │     oav_intelligence   │
                    │  (Secondary OAV bridge │
                    │   → family targets,    │
                    │     shift zones,       │
                    │     balance, synergy,  │
                    │     performance)       │
                    └────────────────────────┘
                    ┌────────────────────────┐
                    │     robustness.py       │
                    │  (Perturbation audits  │
                    │   → ±5% per-material   │
                    │     family drift,      │
                    │     safety checks)     │
                    └────────────────────────┘
                    ┌────────────────────────┐
                    │     audit_log.py        │
                    │  (JSONL audit trail    │
                    │   → all gate runs,     │
                    │     optimizer passes,  │
                    │     events)            │
                    └────────────────────────┘
```

### Pipeline Module Details

| Module | Lines | What it does | Depends on |
|--------|-------|-------------|------------|
| `gates.py` | 1021 | **MASTER GATE ORCHESTRATOR**. `gate_formula()` runs all release gates sequentially: ODT coverage, OAV legibility, OAV scaling, pyramid balance, IFRA safety, robustness, confidence, family drift, perfumer logic. Each gate produces PASS/WARN/FAIL. Configurable via `ReleaseGateConfig` (brief, archetype, temperature, concentration bracket, IFRA headroom, commercial mode). Imports from nearly every engine module. | Everything |
| `formula_state.py` | 448 | **PHYSICS ENGINE**. `build_formula_state()` — converts raw formula (ingredient µL + dilutions) → MaterialState list per material. Chain: raw_ul → active_ul → mass → moles → mole_fraction → partial_pressure → vapor_ppm → OAV → intensity. Uses gamma() (activity), vp_pa() (vapor pressure), oav() from perception module. | `thermo.activity`, `thermo.antoine`, `perception.oav`, `odor_thresholds`, `material_resolver`, `ingredient_intelligence`, `ifra_safety`, `mixer.prebonding` |
| `simulator.py` | 140 | **TEMPORAL SIMULATION**. `simulate_formula()` — 5-window evaporation simulation (opening 0s, top 5min, heart 30min, late_heart 2hr, drydown 4hr). Each window creates a new FormulaState with adjusted µL (evaporation model). Also computes receptor_activation via `receptor.binding`. | `formula_state`, `receptor.binding` |
| `oav_intelligence.py` | 600 | **SECONDARY OAV ANALYSIS**. `analyze_oav_intelligence()` — consumes FormulaState + simulation frames, adds: family-target evaluation, shift-zone analysis, balance/contrast scoring, performance projection, synergy/antagonist pair detection. Bridges to `future_modules/` for family_hedonic_optimizer, synergy_matrix, performance_profiles, balance_axes, character_shift_zones. | `formula_state`, `simulator`, `future_modules.*` |
| `oav_authority.py` | 522 | **CANONICAL OAV AUTHORITY**. `analyze_oav_authority()` — end-to-end OAV verdict surface for candidate formulas. Runs: build_formula_state → simulate → OAV intelligence → robustness → family envelope → gate verdicts. Produces a single OAVAuthorityResult with headspace table, family envelope, temporal analysis, gate summaries. Designed as the "single source of truth" for formula evaluation. | `formula_state`, `gates`, `oav_intelligence`, `robustness`, `simulator` |
| `robustness.py` | 300 | **PERTURBATION AUDIT**. `audit_formula_robustness()` — ±5% perturbation per material, checks family envelope drift, top leader changes, safety failures, brief failures. Configurable drift threshold (default 0.25). | `ifra_safety`, `optimizer.perfumer_logic`, `simulator` |
| `audit_log.py` | 302 | **AUDIT TRAIL**. JSONL append-only log at `data/pipeline_audit/events.jsonl`. Each event has event_id, timestamp, source. `load_events()` for inspection, `summarize_events()` for aggregation, `suggest_repairs()` for recommendations. Used by CLI `pipeline_audit.py`. | None (stdlib only) |

---

## MODULE MAP: Optimizer (`engine/optimizer/`)

| Module | Lines | What it does | Depends on |
|--------|-------|-------------|------------|
| `models.py` | 1402 | FormulaVector, ObjectiveWeights, OptimizationConstraints, optimization data models. Also houses material DB loading, theory rules, accord library access, material lookup functions, knowledge graph integration. | data/knowledge_graph*, perfume_chem.db |
| `scoring.py` | 2302 | **MULTI-AXIS SCORING ENGINE**. FormulaScorer — 10-axis scoring: longevity (×0.8), sillage (×0.8), synergy (×0.5), luxury (×0.8), texture (×0.8), stacking (×0.8), safety (×1.2), skin_perf (×0.7), hedonic (×0.5), perceptual (×0.6). Composite = weighted geometric mean. Calls ifra_safety, skin_interaction, trigeminal, dose_response, hedonic_model, psychophysics, diffusion_model. | Everything in engine |
| `optimizer.py` | 706 | **CORE OPTIMIZER**. Carles grid search, constrained optimization, suggestion engine. FormulaOptimizer class with material suggestion, dose adjustment, style presets (classical, cologne, skin_scent, oriental, soliflore, fougere). | `models`, `scoring`, `inventory_parser`, `chemical_data_validator` |
| `gate_aware.py` | 793 | **GATE-AWARE REPAIR LOOP**. Wraps optimizer output, runs release gates, applies deterministic repairs for repairable gates (safety_ifra, pipette_floor, subtotal, robustness). Records blocked reruns for non-repairable gates. `optimize_until_release_ready()` — iterative loop until all gates pass. | `gates`, `audit_log`, `ifra_safety` |
| `oav_guard.py` | 266 | **OAV BATCH-SCALING GUARD**. Checks per-material OAV shifts when scaling batch volumes. Three failure modes: integer pipetting floor, dilution re-prep, threshold crossing. `check_proportional_scaling()` — used by gates. | `name_utils`, `odor_thresholds` |
| `oav_objective.py` | Unknown | OAV-based optimization objective function | Unknown |
| `perfumer_logic.py` | Unknown | `evaluate_perfumer_logic()` — perfumer craft rules evaluation. Used by gates and robustness. | Unknown |

---

## MODULE MAP: Knowledge (`engine/knowledge/`)

| Module | What it does | Depends on |
|--------|-------------|------------|
| `perfume_knowledge.py` | Family/archetype knowledge — `evaluate_pyramid_balance()`, `evaluate_oav_family_targets()`, `suggest_accord()`, `resolve_family_key()`. _FAMILY_TOKEN_MAP for family→material token mapping. | families.registry |
| `pyramid_targets.py` | Pyramid ratio targets per family archetype | None |
| `accord_library.py` | Known accord definitions for formula construction | None |
| `embeddings.py` | Material/text embedding utilities | sentence-transformers |
| `performance_engineering.py` | Performance engineering / optimization helpers | None |
| `perfume_taxonomy.py` | Perfume taxonomy/classification | None |
| `soliflore_structures.py` | Soliflore (single-flower) structural templates | None |

---

## MODULE MAP: Families (`engine/families/`)

| File | What it does | Depends on |
|------|-------------|------------|
| `registry.py` (473 lines) | ArchetypeSpec definitions, GroupRule anchors/drift limits, FamilyEvaluation/FamilyCheck dataclasses. `evaluate_family_archetype()` — checks formula against archetype anchors + drift limits. `infer_archetype()` — auto-detect archetype from formula. `novelty_assessment()`. BRIEF_DEFAULTS table. Material group tuples: AROMATIC, FOUGERE, CHYPRE_CORE, etc. | `name_utils` |

---

## MODULE MAP: Future Modules (`future_modules/`)

External module directory used by `oav_intelligence.py` for advanced analysis:

| File | What it does |
|------|-------------|
| `_shared_types.py` | ConcentrationBracket, FragranceFamily enums |
| `balance_axes.py` | evaluate_diffusion_layers, evaluate_material_class_distribution, evaluate_oav_contrast, evaluate_volatility_balance |
| `character_shift_zones.py` | check_zone_boundaries, get_zone_by_oav |
| `family_hedonic_optimizer.py` | check_family_cliffs, get_cliff_oav, get_oav_targets, list_family_performance_tips/pitfalls |
| `synergy_matrix.py` | get_all_antagonist_pairs, get_all_synergy_pairs, get_synergy_factor |
| `performance_profiles.py` | estimate_tropical_performance_shift, get_performance |
| `accord_library.py` | Advanced accord library |
| `captive_materials.py` | Captive/exclusive material definitions |
| `blending_protocol.py` | Blending process instructions |
| `brief_translation.py` | Creative brief translation to parameters |
| `skin_chemistry.py` | Skin chemistry interaction models |
| `somatosensory.py` | Somatosensory perception models |
| `chemical_compatibility.py` | Chemical compatibility checks |
| `construction_methodology.py` | Formula construction methodology |
| `dosing_tables.py` | Standard dosing reference tables |
| `edge_cases.py` | Edge case handling |
| `evaluation_protocol.py` | Evaluation/assessment protocols |
| `iconic_formulas.py` | Reference iconic formula structures |
| `literature_references.py` | Literature citation database |
| `niche_construction.py` | Niche perfume construction patterns |
| `advanced_musk_intelligence.py` | Specialized musk material analysis |
| `iteration_protocol.py` | Iterative refinement protocols |

---

## MODULE MAP: Other Engine Modules

| Module | What it does | Depends on |
|--------|-------------|------------|
| `ifra_safety.py` (505 lines) | IFRA_CAT4_LIMITS dict + score_ifra_compliance() — compliance scoring per IFRA 51st Amendment. Calculates dermal exposure estimates. | `material_resolver`, `skin_compartments` |
| `ifra_constraints.py` (261 lines) | IFRA concentration windows for allergen-declared materials. EU 1223/2009 Annex III. Bayesian posterior constraints. | None |
| `reconstruction_pipeline.py` (883 lines) | **MASTER RECONSTRUCTION ORCHESTRATOR**. Runs ALL evidence-analysis modules for fragrance reconstruction: reverse_engineer (Bayesian), ifra_constraints (allergen evidence), allergen_solver (chemistry), perfumer_signature (attribution), cost_analysis (economic plausibility), odor_thresholds (perceptual consistency), material_interactions. Category-based scoring (not geometric mean). | `reverse_engineer`, `ifra_constraints`, `allergen_solver`, `perfumer_signature`, `cost_analysis`, `odor_thresholds`, `material_interactions`, `tracing` |
| `formulator.py` (105 lines) | Simple formula construction with validation. Formula dataclass with add/remove/get_balance. | `validator` |
| `formula_analyzer.py` | Formula analysis and profiling | |
| `formula_rating.py` | Formula rating/ranking | |
| `formula_recommendations.py` | Formula recommendation engine | |
| `validator.py` | Formula validation | |
| `confidence.py` | ConfidenceScorer — formula confidence scoring | |
| `diffusion_model.py` | Diffusion/projection modeling | |
| `dose_response.py` | Dose-response curve modeling | |
| `hedonic_model.py` | Hedonic (pleasantness) modeling | |
| `psychophysics.py` | Cross-adaptation groups, psychophysical models | |
| `trigeminal.py` | Trigeminal nerve sensation scoring | |
| `skin_interaction.py` | Skin interaction/reservoir kinetics | |
| `skin_compartments.py` | Skin partition modeling (stratum corneum) | |
| `temporal_graph.py` | Temporal evolution graph | |
| `temporal_volatility.py` | Volatility-based temporal modeling | |
| `volatility.py` | Volatility classification | |
| `vapor_pressure_modeling.py` | Advanced vapor pressure models | |
| `synergy_graph.py` | Material synergy/antagonist graph | |
| `material_interactions.py` | Material interaction detection | |
| `cost_analysis.py` | Economic cost analysis for reconstruction | |
| `perfumer_signature.py` | Perfumer attribution analysis | |
| `reverse_engineer.py` | Bayesian posterior reconstruction | |
| `fingerprint.py` | Formula fingerprinting | |
| `gap_detector.py` | Formula gap/weakness detection | |
| `science_audit.py` | Science audit utilities | |
| `calibration.py` + `calibration/` | Feedback calibration: hashing, store, models | |
| `captive_availability.py` | Captive material availability checking | |
| `emotional_mapping.py` | Emotional/perceptual mapping | |
| `corrections_patch.py` | Data correction patching | |
| `family_scorer.py` | Family-specific scoring | |
| `intervention_context.py` | Intervention context management | |
| `intervention_profiles.py` | Intervention profiles for optimization | |
| `molecular_weight_distribution.py` | MW distribution analysis | |
| `odor_ontology.py` | Odor ontology classification | |
| `odt_verifier.py` | ODT verification utilities | |
| `opus_v_workbook.py` | Opus V workbook/sheet processing | |
| `pattern_miner.py` | Pattern mining in formulas | |
| `perspectives.py` | Perspective/shift analysis | |
| `regulatory_timeline.py` | Regulatory timeline tracking | |
| `tracing.py` | Execution tracing/debugging | |
| `uncertainty.py` | Uncertainty quantification (FieldUncertainty, FormulaUncertainty) | |
| `allergen_solver.py` | Allergen chemistry solver for reconstruction | |
| `aromachemical_expansion.py` | Aromachemical expansion/suggestion | |
| `recommendation_safety_protocol.md` | Documentation only | |
| `trusted_sources.yaml` | Trusted data source definitions | |

---

## PIPELINE / SCRIPT FLOW DIAGRAMS

### Flow 1: Release Gate (Main Pipeline)

```
formulas/My_Formula_30mL_EDP.md
         │
         ▼
scripts/formula_release_gate.py     ← CLI entry point
  └─ parse_formula_markdown()       ← scripts/verify_formula_workflow.py
  └─ ReleaseGateConfig              ← engine/pipeline/gates.py
  └─ gate_formula()                 ← engine/pipeline/gates.py
       │
       ├─ build_formula_state()     ← engine/pipeline/formula_state.py
       │    ├─ resolve_material()   ← engine/material_resolver.py
       │    ├─ gamma()              ← engine/thermo/activity.py
       │    ├─ vp_pa()              ← engine/thermo/antoine.py
       │    ├─ oav()                ← engine/perception/oav.py
       │    └─ _lookup_odt()        ← engine/odor_thresholds.py (ODT_DATA)
       │
       ├─ _gate_odt_coverage()      ← gates.py (checks ODT data exists)
       ├─ _gate_oav_legibility()    ← gates.py (OAV ≥ 1 checks)
       ├─ _gate_oav_scaling()       ← gates.py + oav_guard.check_proportional_scaling()
       ├─ _gate_pyramid_balance()   ← gates.py + perfume_knowledge.evaluate_pyramid_balance()
       │    └─ pyramid_targets.py
       ├─ _gate_family_drift()      ← gates.py + families/registry.evaluate_family_archetype()
       ├─ _gate_safety_ifra()       ← gates.py + ifra_safety.score_ifra_compliance()
       ├─ _gate_confidence()        ← gates.py + confidence.ConfidenceScorer
       ├─ _gate_perfumer_logic()    ← gates.py + perfumer_logic.evaluate_perfumer_logic()
       ├─ _gate_robustness()        ← gates.py + robustness.audit_formula_robustness()
       │    └─ simulate_formula()   ← engine/pipeline/simulator.py
       │
       ├─ simulate_formula()        ← engine/pipeline/simulator.py (temporal windows)
       │    └─ build_formula_state() per window (adjusted µL for evaporation)
       │    └─ ligands_from_family() ← engine/receptor/binding.py
       │
       ├─ analyze_oav_intelligence() ← engine/pipeline/oav_intelligence.py
       │    └─ future_modules/*     ← (balance_axes, synergy_matrix, etc.)
       │
       └─ audit_log.append_event()  ← engine/pipeline/audit_log.py
```

### Flow 2: OAV Authority (Optimized Analysis)

```
engine/pipeline/oav_authority.py :: analyze_oav_authority()
  └─ build_formula_state()
  └─ simulate_formula()              ← 5 temporal windows
  └─ analyze_oav_intelligence()      ← family targets, balance, synergy
  └─ audit_formula_robustness()      ← perturbation tests
  └─ family envelope computation     ← per-family OAV aggregation
  └─ gate-level verdicts (from gates.py)
  └─ OAVAuthorityResult
```

### Flow 3: Optimizer Loop (Formula Creation)

```
engine/optimizer/optimizer.py :: FormulaOptimizer
  └─ models.py (FormulaVector, etc.)
  └─ scoring.py :: FormulaScorer (10-axis)
  └─ inventory_parser.py (available materials)
  │
  └─ engine/optimizer/gate_aware.py :: optimize_until_release_ready()
       └─ gate_formula()             ← full gate pipeline
       └─ applies repairs for gate failures
       └─ iterates until PASS or max_passes
```

### Flow 4: Reconstruction Pipeline (Reverse Engineering)

```
engine/reconstruction_pipeline.py :: run_reconstruction_pipeline()
  ├─ reverse_engineer.py             → BAYESIAN_POSTERIOR score
  ├─ ifra_constraints.py             → ALLERGEN_EVIDENCE score
  ├─ allergen_solver.py              → ALLERGEN_CHEMISTRY score
  ├─ perfumer_signature.py           → PERFUMER_ATTRIBUTION score
  ├─ cost_analysis.py                → ECONOMIC_PLAUSIBILITY score
  ├─ odor_thresholds.py              → PERCEPTUAL_CONSISTENCY score
  ├─ material_interactions.py        → MATERIAL_INTERACTIONS score
  └─ tracing.py (instrumentation)
```

### Flow 5: Scripts (CLI Entry Points)

```
scripts/
├── formula_release_gate.py          ─── gate_formula() + parse_formula_markdown()
├── pipeline_audit.py                ─── load_events() + gate_formula() for scan
├── format_pipeline_analysis.py      ─── reads JSON → formatted perfumer analysis
├── score_designer_prestige_18.py    ─── FormulaScorer for collection
├── score_collection_formulas.py     ─── batch formula scoring
├── audit_collection_ppm_odt.py      ─── per-material ppm/ODT/OAV audit tables
├── oav_headspace_analyze.py         ─── headspace OAV analysis
├── generate_ingredient_catalog.py   ─── generates ingredient catalog
├── optimize_cobalt_cedar_air.py     ─── targeted optimizer run
├── optimize_orris_damascone_deep_luxury.py
├── opus_v_workbook_pipeline.py      ─── Opus V workbook pipeline
├── verify_formula_workflow.py       ─── formula markdown parser
├── verify_db.py                     ─── database verification
├── init_db.py                       ─── database initialization
├── record_calibration.py            ─── calibration recording
├── record_verification_outcome.py   ─── verification outcomes
├── intervention_recommend.py        ─── intervention recommendations
├── _gate_*.py                       ─── experimental gate scripts
├── _audit_odt.py, _check_missing_odt.py, _recalc_oav.py  ─── ODT audit tools
```

### Flow 6: Pipeline Orchestrators

```
pipelines/
├── luxury_niche_pipeline.py         ─── FormulaVector + FormulaScorer + FormulaOptimizer + ConfidenceScorer
├── luxury_v2_pipeline.py            ─── v2 luxury pipeline
├── masculine_luxury_pipeline.py     ─── gate_formula() + oav_authority + gate_aware optimizer
├── niche_discovery_pipeline.py      ─── niche discovery
├── niche_ideas_pipeline.py          ─── niche ideas generation
├── niche_texture_collection.py      ─── texture-specific niche collection
├── accord_pipeline.py               ─── accord-based pipeline
├── iris_cathedral_formula.py        ─── targeted Iris Cathedral formula
├── opus_v/run_opus_v_pipeline.py    ─── Opus V pipeline runner
├── temporal/                        ─── temporal analysis pipelines
├── utilities/                       ─── pipeline utility scripts
└── analysis/
    ├── analyze_formulas.py          ─── batch formula analysis
    ├── rate_all_formulas.py         ─── rate all formulas in collection
    ├── score_iris.py                ─── iris formula scoring
    ├── run_custom_score.py          ─── custom scoring runs
    ├── perfume_b_odt_analysis.py    ─── formula B ODT analysis
    └── iris_texture_analysis.py     ─── iris texture analysis
```

---

## BACKEND (`backend/`) — FastAPI Application

### Architecture

```
backend/app/
├── main.py                          ← FastAPI app, CORS, lifespan, rate limiter
├── db_session.py                    ← async SQLAlchemy engine + session factory
├── core/
│   ├── config.py                    ← Pydantic Settings (DB, Redis, AI providers)
│   ├── security.py                  ← API security
│   ├── logging.py                   ← Logging setup
│   ├── tracing.py                   ← Tracing setup
│   ├── exceptions.py                ← Exception handlers
│   └── models_config.py             ← Model configuration
├── api/
│   ├── deps.py                      ← Dependency injection
│   └── v1/
│       ├── router.py                ← API router (prefix /api/v1)
│       └── endpoints/
│           ├── ai.py                ← AI endpoints (OpenAI, Cerebras, etc.)
│           ├── formulas.py          ← Formula CRUD endpoints
│           ├── mixer.py             ← Mixing/sequencing endpoints
│           ├── optimizer.py         ← Optimization endpoints
│           ├── knowledge.py         ← Knowledge graph endpoints
│           ├── reference.py         ← Reference data endpoints
│           ├── outcomes.py          ← Outcome tracking endpoints
│           └── enhancements.py      ← Enhancement endpoints
├── models/
│   ├── base.py                      ← SQLAlchemy Base
│   ├── perfume.py                   ← Perfume ORM model
│   ├── ingredient.py                ← Ingredient ORM model
│   └── knowledge_graph.py           ← Knowledge graph ORM models
├── schemas/
│   ├── perfume.py                   ← Pydantic schemas for perfumes
│   └── chemical.py                  ← Pydantic schemas for chemicals
├── services/
│   ├── validation_pipeline.py       ← Validation pipeline
│   ├── chemistry_validator.py       ← Chemistry validation
│   ├── context_builder.py           ← Context building
│   ├── data_loader.py               ← Data loading
│   ├── outcome_store.py             ← Outcome tracking
│   └── ai/
│       ├── base.py                  ← Base AI service
│       ├── factory.py               ← AI service factory
│       ├── enhanced_factory.py      ← Enhanced factory
│       ├── openai_service.py        ← OpenAI provider
│       ├── cerebras_service.py      ← Cerebras provider
│       ├── ollama_service.py        ← Ollama provider
│       ├── huggingface_service.py   ← HuggingFace provider
│       ├── baseten_service.py       ← Baseten provider
│       ├── llama_cpp_service.py     ← Local LLM provider
│       └── prompts/                 ← Prompt templates
├── domain/
│   ├── ingredients/chemistry.py     ← Ingredient chemistry domain logic
│   ├── formulas/                    ← (empty — formulas handled via models+services)
│   ├── analysis/                    ← (empty)
│   └── perfumes/                    ← (empty)
└── repositories/
    └── base.py                      ← Base repository pattern
```

### API Endpoints

| Endpoint File | Prefix | What it does |
|--------------|--------|-------------|
| `formulas.py` | `/api/v1/formulas` | Formula CRUD, create/read/update/delete, list |
| `ai.py` | `/api/v1/ai` | AI-assisted formula generation, analysis |
| `optimizer.py` | `/api/v1/optimizer` | Formula optimization endpoints |
| `mixer.py` | `/api/v1/mixer` | Mixing instructions, sequencing |
| `knowledge.py` | `/api/v1/knowledge` | Knowledge graph queries |
| `reference.py` | `/api/v1/reference` | Reference data (materials, thresholds) |
| `outcomes.py` | `/api/v1/outcomes` | Outcome tracking |
| `enhancements.py` | `/api/v1/enhancements` | Formula enhancement |

### Backend AI Provider Architecture

```
AI Service Factory ─┬─ OpenAI (GPT-4, etc.)
                    ├─ Azure OpenAI
                    ├─ Cerebras
                    ├─ Ollama (local)
                    ├─ HuggingFace
                    ├─ Baseten
                    └─ llama_cpp (local)
```

The backend does NOT depend on `engine/` — they run in separate processes. The backend has its own DB models, schemas, and services.

---

## DATA FLOW MAP (End-to-End)

### Formula Creation → Analysis → Release

```
[Formulator writes markdown formula]
              │
              ▼
scripts/formula_release_gate.py --formula-file formulas/X.md
              │
              ▼
parse_formula_markdown() → dict {name, ingredients_ul, dilutions, family}
              │
              ▼
gate_formula(formula, config)
              │
              ├─► build_formula_state()
              │     ├─ resolve_material() per ingredient
              │     ├─ gamma() from thermo.activity
              │     ├─ vp_pa() from thermo.antoine
              │     ├─ oav() = vapor_ppm / odt_ppm
              │     └─ MaterialState[] (full headspace physics)
              │
              ├─► Run all gates (odt, oav, pyramid, safety, etc.)
              │
              ├─► simulate_formula() (5 temporal windows)
              │
              ├─► analyze_oav_intelligence()
              │     └─ future_modules (balance, synergy, performance)
              │
              └─► GateReport {status, gates[], formula_state, time_series, ...}
                     │
                     ▼
              JSON output (6000 lines) → scripts/format_pipeline_analysis.py
                     │
                     └─► Formatted perfumer analysis
                           ├─ Presented in chat
                           └─ Appended to formula markdown file
```

### Optimizer Loop (Iterative)

```
[Initial formula idea]
         │
         ▼
FormulaOptimizer.optimize()
  ├─ scores via FormulaScorer (10 axes)
  ├─ adjusts doses per constraints
  └─ returns optimized FormulaVector
         │
         ▼
optimize_until_release_ready()
  ├─ gate_formula() → GateReport
  ├─ applies repairs for gate failures
  ├─ re-runs gates iteratively
  └─ returns when all gates pass (or max passes reached)
         │
         ▼
[Release-ready formula]
```

---

## CRITICAL DATA QUALITY ISSUES (from AGENTS.md + analysis)

1. **ODT_DATA vs ODT_VERIFICATION duplication** — Two dicts in odor_thresholds.py. Numeric values need to exist in both. Last entry in ODT_DATA wins.

2. **Hedione/Hedione HC ODT collision** — `name_utils.py` aliases "hedione hc" → "hedione". ODT_DATA entries for both normalize to same key. Peer-reviewed pure-isomer ODT (0.05 ppb) overwritten by practical value (20.0 ppb).

3. **Three unsynchronized data paths**: `material_properties.json`, `_PROFILES` in ingredient_intelligence.py, `ODT_DATA` in odor_thresholds.py. Changes to one do NOT propagate. Must run `_generate_material_properties.py` to resync.

4. **Pipeline pyramid bug**: Mixed-case keys in note_map, `.lower()` lookup returns "heart" default; uses `raw_percentages()` instead of `active_percentages()`. Fix at `engine/pipeline/gates.py:720-722`.

5. **Non-inventory legacy entries** in `material_properties.json` with `in_inventory: false`.

6. **Name normalization inconsistency**: `inventory_parser._canonical_name()` strips trailing parentheticals; `normalize_name()` in name_utils.py preserves them.

7. **`_generate_material_properties.py` NOT import-safe** — module-level execution triggers full generation + PubChem API calls.

---

## SUMMARY OF MODULE CONNECTIONS

```
                                    ┌───────────────────┐
                                    │   name_utils.py   │  ← EVERY module uses this
                                    └────────┬──────────┘
                                             │
            ┌────────────────────────────────┼────────────────────────────────┐
            ▼                                ▼                                ▼
   ┌────────────────┐              ┌──────────────────┐            ┌──────────────────┐
   │  inventory_    │              │   odor_          │            │  ingredient_     │
   │  parser.py     │              │   thresholds.py  │            │  intelligence.py │
   └────────┬───────┘              └────────┬─────────┘            └────────┬─────────┘
            │                               │                              │
            ▼                               ▼                              ▼
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │                         material_resolver.py                                     │
   │         (bridges profile spine + structured registry)                            │
   └─────────────────────────────────────┬───────────────────────────────────────────┘
                                         │
                                         ▼
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │                            formula_state.py                                      │
   │         (core physics: raw µL → OAV per material, used by ALL pipeline modules) │
   └───────────┬─────────────────┬──────────────────┬──────────────────┬─────────────┘
               │                 │                  │                  │
               ▼                 ▼                  ▼                  ▼
        ┌──────────┐     ┌──────────┐      ┌────────────┐      ┌──────────────┐
        │ gates.py │     │simulator │      │  oav_      │      │  robustness  │
        │          │     │  .py     │      │intelligence│      │    .py       │
        └──────────┘     └──────────┘      └────────────┘      └──────────────┘
               │                            │
               ▼                            ▼
        ┌──────────────────────────────────────────────────────────────────────────┐
        │                       oav_authority.py                                   │
        │     (canonical OAV verdict surface — end-to-end formula evaluation)      │
        └──────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
        ┌──────────────────────────────────────────────────────────────────────────┐
        │                    optimizer/gate_aware.py                               │
        │     (wraps optimizer + gates for iterative repair loop)                  │
        └──────────────────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  ┌──────────┐      ┌──────────────┐      ┌──────────────┐
  │optimizer │      │ scoring.py   │      │ models.py    │
  │  .py     │      │ (10 axes)    │      │ (data models)│
  └──────────┘      └──────────────┘      └──────────────┘

  Backend (separate process):
  ┌───────────────────────────────────────────────────────────────────────────────┐
  │  FastAPI app (No engine imports — independent Poetry project)                 │
  │  ├─ API endpoints ←→ AI Services (OpenAI, Cerebras, Ollama, etc.)            │
  │  ├─ API endpoints ←→ SQLAlchemy ORM (perfume_chem.db)                        │
  │  └─ API endpoints ←→ Validation pipeline (chemistry_validator)                │
  └───────────────────────────────────────────────────────────────────────────────┘
```
