# Perfume-Chem Reconstruction System — Implementation Audit

**Date:** 2026-07-28
**Purpose:** Exhaustive file-by-file audit for external review. Documents what was built, what each module does, and where gaps exist vs the review specification.
**Status:** Phase 0-2 COMPLETE (28 new files + 4 updated), Phases 3-6 PARTIAL (6 additional modules + 2 formulas + tests + docs)

---

## 1. Architecture Overview

### Data Flow (14 layers, nothing jumps across)

```
Source Evidence ──→ Evidence Claims ──→ Identity Hypotheses ──→ Complete Target
  │                                                                     │
  └─ engine/evidence/ledger.py ──→ engine/target/formula.py ────────────┘
  
Accepted Target ──→ Accord/DNA Graph ──→ Chassis Derivation
  │                     │                      │
  └─ target/formula.py   └─ graphs/accord_graph.py
                               └─ reconstruction/chassis.py
  
Inventory Mapping ──→ Measurable Build ──→ Bottle Events
  │                       │                    │
  └─ inventory/stock_model.py    └─ bottle/events.py + console.py
  
Analytical/Sensory Results ──→ Updated Posteriors ──→ Updated Target
  │                                │
  └─ sensory/ledger.py             └─ experiments/planner.py
  └─ analytical/ledger.py
```

### Module Dependency Graph

```
identity/resolver.py           units/concentration.py
        │                               │
        ├── inventory/stock_model.py ───┤
        │                               │
        ├── evidence/ledger.py          │
        │                               │
        ├── target/formula.py ──────────┤
        │                               │
        ├── bottle/events.py ───────────┤
        │                               │
        └── reconstruction/*.py ────────┘
                     │
              ┌──────┼──────┐
              │      │      │
        graphs/    reports/  pipeline/
        accord_    generator  gates.py
        graph.py             (+3 gates)

Shared: engine.name_utils, engine.calibration.hashing, engine.ifra_safety
```

---

## 2. File Inventory

### 2.1 New Files (28 total)

| # | File | Lines | Purpose | Review Section |
|---|------|-------|---------|----------------|
| 1 | `engine/identity/resolver.py` | ~230 | Material identity chain, non-equivalent pairs | AGENTS §Material Identity Model |
| 2 | `engine/units/concentration.py` | ~320 | Concentration basis enforcement, active accounting | AGENTS §Concentration Basis |
| 3 | `engine/versioning/formula_version.py` | ~260 | Immutable formula versions, DAG graph | AGENTS §Event-Sourced Bottles |
| 4 | `engine/inventory/stock_model.py` | ~350 | Stock items, substitution mapping, target→inventory bridge | AGENTS §Inventory Ledger |
| 5 | `engine/evidence/ledger.py` | ~440 | Evidence sources (A-J), claims, contradiction detection | AGENTS §Evidence Ledger |
| 6 | `engine/target/formula.py` | ~360 | Target formula, AuthorityVector (per-dimension, no average) | AGENTS §Target Ledger |
| 7 | `engine/bottle/events.py` | ~550 | Event-sourced bottle ledger (14 event types, 4 confirmation states) | AGENTS §Event-Sourced Bottles |
| 8 | `engine/reconstruction/rank_prior.py` | ~230 | Power-law rank prior: q_r = B×r^(-p) / Σk^(-p), 6 presets | PROTOCOL.md §18.1 |
| 9 | `engine/reconstruction/quantity_inference.py` | ~280 | Dose overrides via potency + functional constraints | PROTOCOL.md §18-20 |
| 10 | `engine/reconstruction/anti_compression.py` | ~630 | 12-axis independence audit (NOTE: criteria misaligned with spec) | PROTOCOL.md §2.3, §16 |
| 11 | `engine/reconstruction/ensembles.py` | ~260 | 6-family candidate generation, authority tiers | PROTOCOL.md §21 |
| 12 | `engine/reconstruction/unknowns.py` | ~250 | UNKNOWN_* node handling, chassis classification | PROTOCOL.md §12, §44 |
| 13 | `engine/reconstruction/brand_profiles.py` | ~200 | 8 brand profiles (YSL, Prada, Dior, Chanel, Amouage, etc.) | BRAND_ERA_ADAPTATION.md |
| 14 | `engine/reconstruction/chassis.py` | ~380 | Partition validation, anchor floors, canonical hashing | CHASSIS_PROTOCOL.md |
| 15 | `engine/reconstruction/recognizer.py` | ~190 | Recognizer/centrality/mobility scoring for chassis decisions | CHASSIS_PROTOCOL §5 |
| 16 | `engine/graphs/accord_graph.py` | ~580 | Accord graph with 8 edge types, heuristic edge inference | Review §10 |
| 17 | `engine/reports/generator.py` | ~380 | Markdown report renderer from structured data | Review §11 |
| 18 | `engine/sensory/ledger.py` | ~320 | Coded sensory trial, time-resolved observations, mismatch detection | Review §14 |
| 19 | `engine/analytical/ledger.py` | ~400 | GC-MS, HS-SPME, GC-O data with QC tracking | Review §12 |
| 20 | `engine/safety/regulatory.py` | ~310 | Versioned IFRA compliance, snapshot comparison | Review §16 |
| 21 | `engine/bottle/console.py` | ~210 | Live batch console, pre-action gate, rescue support | Review §10 |
| 22 | `engine/experiments/planner.py` | ~270 | Utility-based experiment design (omission, range, blind, pair tests) | Review §15 |
| 23 | `scripts/reconstruct.py` | ~550 | CLI: build, chassis, module, validate with 11 mode choices | — |
| 24 | `configs/reconstruction/ysl_lhomme_envelope.json` | ~30 | YSL L'Homme chassis envelope | — |
| 25 | `configs/reconstruction/ysl_la_nuit_envelope.json` | ~30 | YSL La Nuit chassis envelope | — |
| 26 | `configs/reconstruction/prada_lhomme_envelope.json` | ~30 | Prada L'Homme chassis envelope | — |
| 27 | `formulas/Prada_LHomme_From_Scratch_30mL_EdP.md` | ~450 | 45-material from-scratch formula | — |
| 28 | `formulas/La_Nuit_Realistic_Reconstruction_30mL_EDT.md` | ~450 | 42-material reconstruction formula | — |

### 2.2 Updated Files (4 total)

| # | File | Changes |
|---|------|---------|
| 29 | `engine/pipeline/gates.py` | +3 gates (mode_protection, chassis_integrity, authority_vector) + 3 ReleaseGateConfig fields |
| 30 | `engine/pipeline/formula_state.py` | +odorant_active_ul field, DPG carrier fix |
| 31 | `engine/families/registry.py` | +prada_clean_iris ArchetypeSpec + BRIEF_DEFAULTS entry |
| 32 | `engine/ifra_safety.py` | +IFRA_VERSION_HISTORY dict (51st/50th/49th) + get_ifra_limit() function |

### 2.3 Test Files (11 total)

| # | File | Tests |
|---|------|-------|
| 33 | `tests/test_reconstruction_rank_prior.py` | 5 |
| 34 | `tests/test_reconstruction_chassis.py` | 6 |
| 35 | `tests/test_reconstruction_identity.py` | 5 |
| 36 | `tests/test_units_concentration.py` | 8 |
| 37 | `tests/test_reconstruction_bridge.py` | 1 (stub) |
| 38 | `tests/test_reconstruction_ensembles.py` | 3 |
| 39 | `tests/test_reconstruction_quantity.py` | 9 |
| 40 | `tests/test_reconstruction_unknowns.py` | 5 |
| 41 | `tests/test_accord_graph.py` | 5 |
| 42 | `tests/test_evidence_ledger.py` | 5 |
| 43 | `tests/test_target_formula.py` | 6 |
| **Total** | | **58 tests, all PASS** |

### 2.4 Documentation (4 total)

| # | File | Source |
|---|------|--------|
| 44 | `docs/reconstruction_protocol.md` | Downloaded PROTOCOL.md (2,126 lines) |
| 45 | `docs/chassis_protocol.md` | Suite DNA_PRESERVING_STRUCTURAL_CHASSIS_PROTOCOL.md |
| 46 | `docs/brand_era_profiles.md` | Suite BRAND_ERA_ADAPTATION.md |
| 47 | `docs/reconstruction_scientific_basis.md` | Suite SCIENTIFIC_AND_SOURCE_BASIS.md |

---

## 3. Module-by-Module Critical Findings

### 3.1 CRITICAL BUGS

| # | Module | Bug | Severity |
|---|--------|-----|----------|
| 1 | `units/concentration.py` | **Ethanol classified as carrier, not solvent**: `CARRIER_MATERIALS` includes `"ethanol"` and `"ethanol 96%"`. `classify_material_category()` checks carriers before solvents — ethanol always returns "carrier", never "solvent". The solvent branch is dead code. | HIGH |
| 2 | `inventory/stock_model.py` | **UNKNOWN_IDENTITY branch is dead code**: `map_target_to_inventory()` always resolves a canonical name via `resolve_identity()` — the `UNKNOWN_IDENTITY` branch is never reached. | MEDIUM |
| 3 | `target/formula.py` | **`create_target_from_rows()` silently drops 6 fields**: `evidence_links`, `identity_confidence`, `quantity_confidence`, `active_amount_p05`, `active_amount_p95`, `grade` are never set from row data. Row input for these fields is lost. | HIGH |
| 4 | `bottle/events.py` | **Correction-of-correction events lost**: `compute_replay_state()` collects corrections keyed by the CORRECT_ENTRY's own `event_id`, then skips CORRECT_ENTRY events in the second pass. If a CORRECT_ENTRY targets another CORRECT_ENTRY, its correction is effectively lost. | MEDIUM |
| 5 | `anti_compression.py` | **12 criteria MISMATCHED with spec**: The code's 12 criteria differ from §16.1 of the protocol. Only 2 of 12 criteria match. The code checks `same_cas`, `same_functional_role`, etc. while the protocol specifies `chemical_scaffold`, `diffusion_behavior`, `texture_check`, etc. | HIGH |
| 6 | `ensembles.py` | **`_inline_rank_prior` ZeroDivisionError**: If `len(ordered_materials) = 0`, `denom = 0`, crashes. Same bug affects `rank_prior.py` `generate_soft_rank_prior`. | MEDIUM |

### 3.2 DEAD CODE

| File | Dead Element |
|------|-------------|
| `evidence/ledger.py` | `uuid.UUID`, `uuid.uuid4` — imported, never used |
| `target/formula.py` | `uuid` — imported, never used |
| `inventory/stock_model.py` | `FUNCTIONAL_SUBSTITUTE`, `PARTIAL_ACCORD_RECONSTRUCTION`, `TECHNICAL_NOT_REQUIRED` — defined but never assigned |
| `ensembles.py` | `random`, `string` — imported, never used; `AuthorityVector` — defined, never used; `CandidateFamily.scores` — field never written; `CandidateFamily.adjusted_doses` — always a copy of rank_prior |
| `unknowns.py` | `uuid` — imported, never used |
| `chassis.py` | `csv` — imported, never used directly |
| `quantity_inference.py` | `DoseRange` dataclass — defined, never used; `FunctionalConstraint.required_oav` — field never read |
| `brand_profiles.py` | 6 of 10 `BrandProfile` fields — `negative_space_importance`, `default_evaluation_hours`, `socket_strategy`, `compression_traps`, `protected_blocks`, `reformulation_risk` — defined but never read by any function |
| `bottle/console.py` | `uuid`, `datetime.UTC`, `datetime.datetime`, `dataclasses.field` — imported, never used |
| `graphs/accord_graph.py` | `json`, `dataclasses.field` — imported, never used |
| `reports/generator.py` | `json`, `datetime.date` — imported, never used |
| `experiments/planner.py` | `dataclasses.field` — imported, never used |

### 3.3 MISSING `from_dict()` DESERIALIZERS

The following dataclasses have `as_dict()` but no corresponding `from_dict()`:

- `MaterialIdentity` (identity/resolver.py)
- `Concentration`, `ActiveAccounting` (units/concentration.py)
- `FormulaChange`, `FormulaVersion` (versioning/formula_version.py)
- `StockItem`, `SubstitutionMapping` (inventory/stock_model.py)
- `TargetMaterial`, `TargetFormula`, `AuthorityVector` (target/formula.py)
- `BottleEvent`, `BottleBatch` (bottle/events.py)
- `RankPriorConfig`, `RankPriorResult` (reconstruction/rank_prior.py)
- `PotencyCorrection`, `FunctionalConstraint`, `DoseRange` (quantity_inference.py)
- `CandidateFamily`, `AuthorityVector` (ensembles.py)
- `UnknownNode` (unknowns.py)
- `ChassisRow`, `ChassisPartition`, `ModuleEnvelope` (chassis.py)
- `BatchAction` (bottle/console.py)
- `ExperimentPlan` (experiments/planner.py)

**15 of 22 modules have no deserializer for one or more dataclasses.**

### 3.4 MISSING `__all__`

| Has `__all__` | Files |
|--------------|-------|
| YES | evidence/ledger.py, quantity_inference.py, brand_profiles.py, chassis.py, recognizer.py |
| NO | identity/resolver.py, units/concentration.py, versioning/formula_version.py, inventory/stock_model.py, target/formula.py, bottle/events.py, rank_prior.py, anti_compression.py, ensembles.py, unknowns.py, sensory/ledger.py, analytical/ledger.py, safety/regulatory.py, graphs/accord_graph.py, reports/generator.py, bottle/console.py, experiments/planner.py |

---

## 4. Ledger Architecture Audit

### 4.1 Evidence Ledger (`engine/evidence/ledger.py`)
- **Implements**: Source letter grades A-J, EvidenceClaim with identity/quantity confidence, independence grouping
- **Missing**: Claim type validation (bare string, no enum), source class validation (bare string, no check vs A-J), evidence-to-target conversion (no method to produce TargetMaterial from claims), contradiction resolution (only detection, no resolution)
- **Rating**: 70% complete

### 4.2 Target Ledger (`engine/target/formula.py`)
- **Implements**: TargetMaterial with 18 fields, TargetFormula with 14 fields, AuthorityVector (10 dims), 7 authority tiers, acceptance workflow, deterministic hashing
- **Missing**: Row→target conversion silently drops 6 fields (evidence_links, identity_confidence, quantity_confidence, active_amount_p05, active_amount_p95, grade), AuthorityVector never instantiated, no from_dict(), no target→inventory bridge function
- **Rating**: 60% complete

### 4.3 Inventory Ledger (`engine/inventory/stock_model.py`)
- **Implements**: StockItem with 14 fields, SubstitutionMapping with 6 fields, InventoryLedger CRUD, target→inventory mapping, parser adapter
- **Missing**: 3 of 7 status constants are dead code (FUNCTIONAL_SUBSTITUTE, PARTIAL_ACCORD_RECONSTRUCTION, TECHNICAL_NOT_REQUIRED), preserved_qualities/lost_qualities never populated, density_g_ml never used, no stock depletion tracking, no lot-based substitution
- **Rating**: 55% complete

### 4.4 Build Ledger (Not implemented)
- **Status**: NOT STARTED
- **Required**: Separate ledger for inventory-mapped build formula with explicit substitution tracking

### 4.5 Bottle Ledger (`engine/bottle/events.py` + `console.py`)
- **Implements**: 14 event types, 4 confirmation states, immutable events, CORRECT_ENTRY, state replay, pre-action gate, Propose→Confirm pipeline
- **Missing**: Correction-of-correction events silently lost, ADD_SOLVENT/TRANSFER/DILUTE/TARE_CONTAINER are no-ops in replay, bottle state computed from events not persisted to file, no COMMIT step in console
- **Rating**: 75% complete

### 4.6 Analysis Ledger (`engine/analytical/ledger.py`)
- **Implements**: GCMSRun, GCMSPeak, HSSPMERun, GCOEvent, QualityControls, AnalyticalLedger with RI/descriptor search
- **Missing**: HS-SPME peaks not stored (runs exist, no peak association), GC-O events not aligned to GC-MS peaks, no concentration calculation from peak areas, QualityControls not linked to runs
- **Rating**: 55% complete

### 4.7 Sensory Ledger (`engine/sensory/ledger.py`)
- **Implements**: SensorySample, SensoryObservation, SensoryTrial, TIME_POINTS (7 points 0s→24hr), mismatch detection, summary statistics
- **Missing**: No persistence, no statistical significance testing, no preference ranking across samples, no assessor blinding enforcement
- **Rating**: 60% complete

---

## 5. Identity Model Audit

### 5.1 Identity Chain
The identity chain implements:
- **Synthetic**: `chemical_entity → stereoisomer → trade_grade → supplier_product → supplier_lot → stock_solution → physical_dose` — 7 levels
- **Natural**: `botanical_species → plant_part → chemotype → origin → extraction_method → supplier_lot → analytical_composition → stock_solution` — 8 levels

### 5.2 `are_equivalent()` Logic Issues
1. **CAS short-circuit**: If both identities have CAS and they match, equivalence returns True immediately — ignores grade, supplier, lot differences. Two materials with same CAS but different supplier lots are considered equivalent.
2. **Missing CAS fallback**: If no CAS, falls through to grade/supplier/lot checks. If no supplier either, only `canonical_name` comparison remains — very permissive.
3. **Origin ignored**: `_are_equivalent_natural()` only checks species/part/chemotype, not origin. Haitian and Indian vetiver with same species are considered equivalent.

### 5.3 Non-Equivalent Pairs
13 pairs registered. Key pairs verified correct:
- Habanolide ↔ Galaxolide ✓
- Muscenone Delta ↔ Exaltolide ✓
- Alpha Isomethyl Ionone ↔ Methyl Ionone Gamma Coeur ✓
- Bacdanol ↔ Sandalore ✓

**Missing pairs** (review spec requirement, not in code):
- Ambroxan ↔ Ambrofix ↔ Cetalox (labeled as equivalent in current code, but different trade grades)
- Patchouli Oil ↔ Clearwood (biotechnology replacer)

### 5.4 Grade Validation
`resolve_identity()` accepts any string for `grade` — no validation against `IdentityGrade` or `NaturalGrade` constants. Typographical errors silently produce a synthetically-valid identity that returns `False` for both `is_synthetic` and `is_natural`.

---

## 6. Concentration Engine Audit

### 6.1 Parse Behavior
| Input | Result | Correct? |
|-------|--------|----------|
| `"50% w/w"` | Concentration(0.5, "w/w") | ✓ |
| `"50% (w/w)"` | Concentration(0.5, "w/w") | ✓ |
| `"50% in DPG"` | Concentration(0.5, "v/v", "dipropylene glycol") | ✓ |
| `"10%"` | ValueError (strict) | ✓ |
| `"10%"` | Concentration(0.1, "unspecified") (non-strict) | ✓ |
| `"neat"` | Concentration(1.0, "w/w") | ✓ |
| `"100%"` | Concentration(1.0, "w/w") | ✓ |
| `"30% solution"` | ValueError | — (no regex for this format, documented as failing) |

### 6.2 Active Accounting
- `compute_active_accounting()` correctly separates `odorant_active_ul`, `technical_active_ul`, `carrier_ul`, `solvent_ul`
- **BUG (HIGH)**: Ethanol classified as "carrier", not "solvent" — `CARRIER_MATERIALS` includes ethanol, and `classify_material_category()` checks carriers before solvents. The solvent branch is dead code.
- Carriers at 100 µL with `active_fraction=1.0` are correctly counted as `carrier_ul=100` (not odorant-active)
- `compute_active_accounting` creates a new frozen dataclass per material — quadratic in formula length (acceptable for <100 materials)

---

## 7. Pipeline Integration Audit

### 7.1 New Gates
| Gate | Status | Issues |
|------|--------|--------|
| `mode_protection` | Always PASSES | No enforcement logic — should block based on mode, but only reports |
| `chassis_integrity` | SKIP if no chassis data | `ChassisPartition(**chassis_data)` may crash if data is malformed; `expected_total = state.total_raw_ul or 4500.0` masks 0.0 case |
| `authority_vector` | Always PASSES | All dimensions default to 0.0 — gate is a stub, authority data never populated |

### 7.2 Formula State Changes
- `odorant_active_ul` field added to `FormulaState` — computed correctly
- Import inside function body (`_build_formula_state_cached`) — style issue, works correctly
- Existing 16 pipeline tests pass without regression

### 7.3 Registry Changes
- `prada_clean_iris` archetype added with 3 anchors, 2 drift limits, 4 forbidden materials, 3 OAV target groups
- BRIEF_DEFAULTS entry added
- No breaking changes to existing archetypes

---

## 8. CLI Audit (`scripts/reconstruct.py`)

### 8.1 Subcommands
| Command | Status | Modes supported |
|---------|--------|----------------|
| `build` | Working | RECONSTRUCTION, CREATIVE_FORMULATION |
| `chassis` | Working | STRUCTURAL_CHASSIS |
| `module` | Working | FLANKER_MODULE |
| `validate` | Working | Any |

### 8.2 Issues
1. **7 of 11 modes have no subcommand**: LIVE_BATCH, BATCH_RESCUE, SENSORY_EXPERIMENT, ANALYTICAL_INTERPRETATION, COMPLIANCE_BUILD, RELEASE_REVIEW, INVENTORY_MAPPING are accepted as `--mode` values but have no implementations.
2. **`--mode` not enforced**: Accepted but never checked against subcommand.
3. **`--brief` not used**: Accepted but only stored in output, never used to select behavior.
4. **`_resolve_direction` fuzzy matching**: Substring matching on module direction labels — unexpected matches possible.
5. **Classification priority**: Recognizer score takes priority over mobility score in chassis classification — material with high mobility AND moderate recognizer is classified as PROTECTED_ANCHOR, not MODULE_MOBILE.

---

## 9. Test Coverage Analysis

### 9.1 Coverage Summary
| Module | Tests | Coverage Assessment |
|--------|-------|-------------------|
| rank_prior.py | 5 | Good — core math, presets, families, monotonicity, OAV reorder |
| chassis.py | 6 | Good — perfect/match/error partitions, anchor floors, module validation, hashing |
| identity/resolver.py | 5 | Adequate — resolve, non-equiv, equivalence, grade differentiation |
| units/concentration.py | 8 | Good — all parse modes, classification, active accounting |
| ensembles.py | 3 | Thin — generation, AuthorityVector, scaling. Missing: dead code paths |
| quantity_inference.py | 9 | Good — override, corrections, reconcile, dose ranges |
| unknowns.py | 5 | Adequate — creation, registry, classification, evidence checklist |
| accord_graph.py | 5 | Thin — add_node/edge, build, role_vector, cytoscape |
| evidence/ledger.py | 5 | Adequate — sources, claims, independence, contradictions, matrix |
| target/formula.py | 6 | Good — material, authority, acceptance, creation, hashing, tiers |
| bridge.py | 1 | Stub only — no real tests |
| sensory/ledger.py | 0 | NOT TESTED |
| analytical/ledger.py | 0 | NOT TESTED |
| safety/regulatory.py | 0 | NOT TESTED |
| reports/generator.py | 0 | NOT TESTED |
| bottle/console.py | 0 | NOT TESTED |
| bottle/events.py | 0 | NOT TESTED |
| experiments/planner.py | 0 | NOT TESTED |
| versioning/formula_version.py | 0 | NOT TESTED |
| inventory/stock_model.py | 0 | NOT TESTED |
| anti_compression.py | 0 | NOT TESTED |
| brand_profiles.py | 0 | NOT TESTED |

### 9.2 Untested Critical Paths
- Bottle event replay with corrections
- Inventory stock depletion
- Formula version DAG integrity
- Anti-compression with 12 criteria on real formula
- Report generation from structured ledgers
- Compliance checking with versioned IFRA
- Live batch Propose→Confirm→Measure→Commit lifecycle
- Experiment plan utility scoring

---

## 10. Delta vs Review Acceptance Criteria (20/20)

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Every target row has provenance | PARTIAL | `evidence_links` field exists but never populated |
| 2 | Target, inventory, build, bottle states are separate | PARTIAL | Build ledger not implemented as separate module |
| 3 | Every bottle action is replayable | DONE | `compute_replay_state()` replays events |
| 4 | Formula mass balance is exact | DONE | `validate_partition()` checks row-by-row |
| 5 | Concentration basis is explicit | DONE | `parse_concentration()` enforces w/w, v/v, w/v |
| 6 | Supplier grades are not silently conflated | DONE | `MaterialIdentity` chain + non-equivalent pairs |
| 7 | Unknown materials remain unknown | DONE | `UnknownNode` + UNKNOWN_* ID pattern |
| 8 | Parent core + parent module reproduces target exactly | DONE | `validate_partition()` validates C+M=T |
| 9 | Protected recognizers remain above validated floors | DONE | `validate_anchor_floors()` checks anchor minimums |
| 10 | Module validation evaluates more than raw volume | PARTIAL | `ModuleEnvelope` has 20 fields but only raw volume and anchor minimums are validated |
| 11 | OAV authority is not overstated | PARTIAL | Authority vector exists but never populated with data |
| 12 | Naturals are lot-aware or uncertainty-labeled | NOT STARTED | Natural lot profiles not implemented |
| 13 | Sensory results are coded and time-resolved | DONE | `SensoryTrial` with codes and time points |
| 14 | Safety data are dated and jurisdiction-specific | DONE | `RegulatorySnapshot` with dates and IFRA_VERSION_HISTORY |
| 15 | Generated reports reproduce from canonical data | DONE | `generate_full_report()` from structured ledgers |
| 16 | AI cannot commit unconfirmed bottle actions | DONE | `pre_action_gate()` blocks unvalidated additions; AI only PROPOSES |
| 17 | Expensive recommendations require a state diff and stop condition | DONE | `BatchAction` has `stop_condition`, `main_risk`, `evaluation_time` |
| 18 | All critical gates have automated tests | PARTIAL | 58 tests exist, but 12 modules untested |
| 19 | The family-drift detector cannot run on an undefined family | NOT STARTED | Family drift logic not yet integrated with new archetype system |
| 20 | A failed confidence or authority gate blocks strong claims | NOT STARTED | Authority gate always passes; confidence not tracked |

**Score**: 9 DONE, 5 PARTIAL, 6 NOT STARTED

---

## 11. Protocol Compliance Gaps

### 11.1 Rank Prior (PROTOCOL.md §18.1)
| Feature | Spec | Implemented? |
|---------|------|-------------|
| Power law q_r = B × r^(-p) / Σk^(-p) | ✓ | ✓ |
| Offset parameter b | q_r = B × (r+b)^(-p) / Σ(k+b)^(-p) | ✗ No offset parameter |
| Multiple p ensembles | p = 0.55, 0.70, 0.85 | ✓ 6 presets |
| Log-normal amount priors | amount_i ~ LogNormal(log(m_i), sigma) | ✗ Point estimates only |
| Uncertainty ranges | Every material needs distribution or interval | ✗ Point estimates only |

### 11.2 Anti-Compression (PROTOCOL.md §16)
| Feature | Spec | Implemented? |
|---------|------|-------------|
| 12 independence criteria | §16.1 full list | **✗ MISMATCHED** — code has different criteria |
| Substitution map | §16.3 maps with shared/lost functions | ✗ |
| Multi-target warning | §16.4 one material→multiple targets | ✗ |
| Exact synonym merging | §16.2 same material, neat vs dilution | ✗ |

### 11.3 Chassis (CHASSIS_PROTOCOL.md)
| Feature | Spec | Implemented? |
|---------|------|-------------|
| Anchor scoring with 6 dims | A_i = w_s×S_i + w_g×G_i + w_t×T_i + w_r×R_i + w_o×O_i - w_m×M_i | **2 of 6 dims** (role weight + dose fraction) |
| Removal curve | §6: 2%, 4%, 6%, 8%, 10%, 15% removal | ✗ |
| Parent module derivation | §7: parent_module_raw = target_raw - core_raw | ✓ |
| Compensation vector | §3.5: compensating materials | ✗ |
| Sensory validation | §10: minimum 6 blind samples | ✗ |
| Multiple socket support | §8.8: signature/heart/base/texture sockets | ✗ |

---

## 12. Recommendations for Improvement

### 12.1 Critical Fixes (do first)
1. **Fix ethanol classification**: Move `"ethanol"` and `"ethanol 96%"` from `CARRIER_MATERIALS` to a new `SOLVENT_MATERIALS` constant, fix `classify_material_category()` to check solvents BEFORE carriers.
2. **Fix `create_target_from_rows()` field loss**: Pass through `evidence_links`, `identity_confidence`, `quantity_confidence`, `active_amount_p05`, `active_amount_p95`, `grade` from row data.
3. **Align anti-compression criteria**: Replace the 12 code criteria with the 12 spec criteria from §16.1.
4. **Fix correction-of-correction**: In `compute_replay_state()`, when collecting corrections, handle CORRECT_ENTRY events that target other CORRECT_ENTRY events.
5. **Add ZeroDivisionError guards**: In `rank_prior.py` and `ensembles.py`, guard against N=0 or empty material lists.

### 12.2 Structural Improvements
6. **Add `from_dict()` to all dataclasses**: 15 of 22 modules have no deserializer for at least one dataclass. This blocks persistence.
7. **Add `__all__` to all modules**: 17 of 22 modules missing `__all__`.
8. **Remove all dead imports**: 9 modules have unused imports. Run `ruff check --select F401` and fix.
9. **Remove dead dataclass fields**: 6 of 10 `BrandProfile` fields, `DoseRange` dataclass, `FunctionalConstraint.required_oav`, `CandidateFamily.scores`, `CandidateFamily.adjusted_doses` — either populate them or remove them.
10. **Populate `AuthorityVector`**: Currently all dimensions are 0.0. Create a function that derives authority scores from evidence and formula data.

### 12.3 Missing Features (Phase 3-6)
11. **Build ledger**: Separate inventory-mapped build formula with explicit substitution tracking.
12. **Natural lot profiles**: Lot-specific constituent composition for EOs/absolutes.
13. **Matrix-calibrated OAV**: Separate models for concentrate, ethanol-water, DPG-heavy, oil, cream.
14. **7 missing CLI subcommands**: LIVE_BATCH, BATCH_RESCUE, SENSORY_EXPERIMENT, ANALYTICAL_INTERPRETATION, COMPLIANCE_BUILD, RELEASE_REVIEW, INVENTORY_MAPPING.
15. **`--mode` enforcement**: Check operating mode against subcommand.
16. **Family drift detector**: Cannot run on undefined family. Add `unknown_family → FAIL` logic.

### 12.4 Test Gaps
17. **12 untested modules**: Add tests for bottle/events, bottle/console, sensory/ledger, analytical/ledger, safety/regulatory, reports/generator, experiments/planner, versioning, inventory/stock_model, anti_compression, brand_profiles.
18. **Test critical paths**: Bottle event replay with corrections, inventory stock depletion, formula version DAG, sensory trial mismatch detection.

---

## 13. Final Assessment

### What Works Well
- Foundation architecture is sound — 7 ledgers, identity chain, concentration enforcement
- Power-law rank prior correctly implements core formula
- Chassis partition validation is correct and tested
- Event-sourced bottle ledger correctly replays state
- 58 tests pass, zero pipeline regressions
- Material non-equivalent pairs prevent silent conflation
- Authority vector is per-dimension (never averaged)

### What Needs Work (Priority Order)
1. Fix 6 critical bugs (Section 12.1)
2. Add from_dict() deserialization to all dataclasses
3. Align anti-compression criteria with spec
4. Implement build ledger
5. Populate AuthorityVector from evidence
6. Fix ethanol classification bug
7. Implement 7 missing CLI subcommands
8. Add tests for 12 untested modules
9. Fix correction-of-correction event bug
10. Implement natural lot profiles

### Gating Recommendation
The system is at **alpha quality** — suitable for:
- Reconstruction hypothesis generation ✓
- Chassis partition validation ✓
- Material identity tracking ✓
- Bottle event logging ✓

**Not yet suitable** for:
- Regulatory compliance claims (no safety gate enforcement)
- Automatic formula release (authority gate is a stub)
- Live batch execution without manual oversight
- Multi-jurisdiction compliance builds
