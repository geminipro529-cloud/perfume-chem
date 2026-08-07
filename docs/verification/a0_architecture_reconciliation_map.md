# A0.3 Architecture Reconciliation Map (ADR)

**Date:** 2026-07-29
**Phase:** A0 — Establish the Authoritative Truth Baseline
**Status:** PROPOSED (awaiting approval)

---

## Purpose

This Architecture Decision Record maps every reconstruction engine object to the existing canonical backend object, or proves that no canonical equivalent exists. It identifies the single source of truth for each concept and prohibits bidirectional unsynchronized stores.

---

## Mapping

### 1. EvidenceLedger

| Field | Value |
|-------|-------|
| Engine module | `engine/evidence/ledger.py` |
| Engine classes | `EvidenceSource`, `EvidenceClaim`, `ContradictionReport`, `EvidenceLedger` |
| Candidate canonical | `backend/app/models/lab.py` → `LabEvidenceRecord` |
| Decision | **ADAPT_LEGACY_TO_CANONICAL** |
| Canonical source of truth | `LabEvidenceRecord` (SQL persistence) |
| Rationale | Engine `EvidenceLedger` is a richer in-memory model (contradiction detection, independence groups, A–J grading). Backend `LabEvidenceRecord` is the canonical append-only persistence table. The engine model's `to_dict()` output can be serialized into backend records. The engine model should NOT maintain its own separate persistence path. |
| Adaptation plan | Add a one-way adapter: `EvidenceLedger.to_dict()` → `LabEvidenceRecord` rows. Engine evidence remains in-memory for computation; backend is the persistence authority. |

### 2. TargetFormula

| Field | Value |
|-------|-------|
| Engine module | `engine/target/formula.py` |
| Engine classes | `TargetMaterial`, `TargetFormula`, `AuthorityVector` |
| Candidate canonical | `backend/app/models/lab.py` → `LabFormula` + `LabFormulaVersion` + `LabFormulaComponent` |
| Decision | **ADAPT_LEGACY_TO_CANONICAL** |
| Canonical source of truth | `LabFormulaVersion` (immutable versioned formula) |
| Rationale | Engine `TargetFormula` is a richer hypothesis model (confidence intervals, evidence links, authority tiers TIER_0–TIER_6). Backend `LabFormulaVersion` is the canonical immutable version. The target is conceptually upstream — it represents the hypothesis before inventory mapping. Substitutions live in the build layer, not the target. |
| Adaptation plan | When a `TargetFormula` is `accepted=True`, serialize it into a `LabFormulaVersion` with components. The engine model remains the computation engine; the backend is the persistence authority. |

### 3. InventoryLedger / StockItem

| Field | Value |
|-------|-------|
| Engine module | `engine/inventory/stock_model.py` |
| Engine classes | `StockItem`, `SubstitutionMapping`, `ConsumptionRecord`, `InventoryLedger` |
| Candidate canonical | `backend/app/models/lab.py` → `LabStockSolution` + `LabInventoryMovement` |
| Decision | **ADAPT_LEGACY_TO_CANONICAL** |
| Canonical source of truth | `LabStockSolution` (stock) + `LabInventoryMovement` (movements) |
| Rationale | Engine `StockItem` is a flat in-memory model. Backend `LabStockSolution` has richer lot/supplier tracking. Engine `InventoryLedger.consume()` does in-place decrement — this MUST be replaced by append-only `LabInventoryMovement` records. Engine `SubstitutionMapping` has no backend equivalent and should remain an engine computation. |
| Adaptation plan | Adapter: `StockItem` ↔ `LabStockSolution` (bidirectional read). Consumption: engine proposes → backend records `LabInventoryMovement` (append-only). Engine must NOT maintain its own consumption ledger. |

### 4. BottleBatch / BottleEvent

| Field | Value |
|-------|-------|
| Engine module | `engine/bottle/events.py` |
| Engine classes | `BottleEvent`, `BottleBatch` |
| Candidate canonical | `backend/app/models/lab.py` → `LabBottle` + `LabBottleEvent` + `LabBottleEventEffect` + `LabBottleMeasurement` |
| Decision | **MIGRATE_AND_DEPRECATE_LEGACY** |
| Canonical source of truth | `LabBottleEvent` (event-sourced, SQL-persisted, stream-sequence guarded) |
| Rationale | Engine `BottleBatch`/`BottleEvent` is a simplified in-memory version of the same event-sourced concept. The backend model is strictly more capable: it has SQL constraints, foreign keys, stream-sequence enforcement, transaction IDs, event effects, and inventory movements. The engine model is a **duplicate truth store** for bottle state. |
| Adaptation plan | Add a one-way adapter: `LabBottleEvent` → `BottleEvent` (for in-session replay). Engine `BottleBatch` becomes a read-only projection of backend events. Prohibit new writes to engine `BottleBatch._events` — all writes go through the backend repository. Deprecate `BottleBatch.add_event()`. |

### 5. FormulaVersion DAG

| Field | Value |
|-------|-------|
| Engine module | `engine/versioning/formula_version.py` |
| Engine classes | `FormulaChange`, `FormulaVersion` |
| Candidate canonical | `backend/app/models/lab.py` → `LabFormulaVersion` |
| Decision | **ADAPT_LEGACY_TO_CANONICAL** |
| Canonical source of truth | `LabFormulaVersion` (immutable, sequentially numbered) |
| Rationale | Engine `FormulaVersion` has DAG parent tracking and change lists — richer than backend's sequential version numbers. However, the backend is the persistence authority. The engine DAG is a computation overlay for the version graph. |
| Adaptation plan | Adapter: `LabFormulaVersion` → `FormulaVersion` (reconstruct DAG from parent references). Engine `FormulaVersion.derive()` creates a new version proposal → backend persists it as a new `LabFormulaVersion` row. Engine must NOT persist its own version graph. |

### 6. AnalyticalLedger

| Field | Value |
|-------|-------|
| Engine module | `engine/analytical/ledger.py` |
| Engine classes | `GCMSRun`, `GCMSPeak`, `HSSPMERun`, `GCOEvent`, `QualityControls`, `AnalyticalLedger` |
| Candidate canonical | None (no backend equivalent) |
| Decision | **MISSING_CREATE_CANONICAL** |
| Canonical source of truth | To be created in backend (Phase A2) |
| Rationale | No backend table stores GC-MS, HS-SPME, or GC-O data. The engine model is the only representation. For canonical convergence, a backend persistence path must be created — either as new `lab_analytical_*` tables or as `LabEvidenceRecord` entries with structured payloads. |
| Adaptation plan | Phase A2: Create backend tables for analytical runs, peaks, and QC. Add adapter from engine `AnalyticalLedger` to backend. Until then, engine `AnalyticalLedger` remains `EXPERIMENTAL_DO_NOT_PERSIST`. |

### 7. SensoryLedger

| Field | Value |
|-------|-------|
| Engine module | `engine/sensory/ledger.py` |
| Engine classes | `SensorySample`, `SensoryObservation`, `SensoryTrial` |
| Candidate canonical | `backend/app/models/lab.py` → `LabExperiment` + `LabSample` + `LabApplication` + `LabObservation` + `LabPairwiseComparison` |
| Decision | **ADAPT_LEGACY_TO_CANONICAL** |
| Canonical source of truth | `LabExperiment` / `LabObservation` (SQL-persisted) |
| Rationale | Engine `SensoryTrial` is specialized for reconstruction validation (identity matching against reference). Backend is more general (supports arbitrary experiments, pairwise comparisons, predictions, outcomes). Engine model should become a computation overlay on backend data. |
| Adaptation plan | Adapter: `LabObservation` → `SensoryObservation`. Engine `SensoryTrial` becomes a read-only projection of backend experiment data. New observations are persisted via backend first, then loaded into engine for analysis. |

### 8. RegulatorySnapshot

| Field | Value |
|-------|-------|
| Engine module | `engine/safety/regulatory.py` |
| Engine classes | `RegulatorySnapshot`, `ComplianceResult` |
| Candidate canonical | `backend/app/models/lab.py` → `LabRestriction` |
| Decision | **ADAPT_LEGACY_TO_CANONICAL** |
| Canonical source of truth | `LabRestriction` (per-material restriction records) |
| Rationale | Engine `RegulatorySnapshot` groups restrictions into versioned snapshots by jurisdiction. Backend `LabRestriction` stores raw per-material restriction data. The engine model is a higher-level abstraction. |
| Adaptation plan | Adapter: `LabRestriction` rows → `RegulatorySnapshot`. The snapshot remains an engine computation (grouping, compliance checking). Backend is the persistence authority for individual restrictions. |

### 9. AuthorityVector

| Field | Value |
|-------|-------|
| Engine module | `engine/reconstruction/authority.py` (computation functions) + `engine/target/formula.py` (data class) |
| Engine classes | `AuthorityVector` (data class) |
| Candidate canonical | None (no backend equivalent) |
| Decision | **EXPERIMENTAL_DO_NOT_PERSIST** |
| Canonical source of truth | Not persisted — pure computation |
| Rationale | `AuthorityVector` is a derived computation from `TargetFormula` + `EvidenceLedger`. It is never independently persisted. It is recalculated on demand. This is correct behavior — authority is a function of the current evidence state, not a stored fact. |
| Adaptation plan | No persistence path needed. Ensure `derive_authority_from_evidence()` is the only computation path. Add tests proving authority changes when evidence changes. |

### 10. Anti-Compression (CompressionCheck)

| Field | Value |
|-------|-------|
| Engine module | `engine/reconstruction/anti_compression.py` |
| Engine classes | `CompressionCheck` |
| Candidate canonical | None |
| Decision | **EXPERIMENTAL_DO_NOT_PERSIST** |
| Canonical source of truth | Not persisted — pure computation |
| Rationale | Anti-compression is a 12-criterion audit function. It runs on demand against a material list. Results are advisory (warnings), not persisted facts. |
| Adaptation plan | No persistence path needed. Ensure `should_merge()` and `audit_formula()` are the only entry points. Add tests proving all 12 criteria are evaluated. |

### 11. Chassis (ChassisPartition)

| Field | Value |
|-------|-------|
| Engine module | `engine/reconstruction/chassis.py` |
| Engine classes | `ChassisRow`, `ChassisPartition`, `ModuleEnvelope` |
| Candidate canonical | None |
| Decision | **EXPERIMENTAL_DO_NOT_PERSIST** |
| Canonical source of truth | Not persisted — derived from a `TargetFormula` |
| Rationale | A chassis partition is a structural analysis of a target formula. It is derived, not authored. It can be recalculated from the target. Persisting it separately would create a duplicate truth store. |
| Adaptation plan | No persistence path needed. `ChassisPartition` is a projection of `TargetFormula`. If chassis state must be saved, it should be serialized as part of the target's extension fields, not as a separate table. |

### 12. Concentration (units)

| Field | Value |
|-------|-------|
| Engine module | `engine/units/concentration.py` |
| Engine classes | `Concentration`, `ConcentrationBasis`, `ActiveAccounting` |
| Candidate canonical | `backend/app/models/lab.py` → `LabStockSolution` (`active_fraction`, `fraction_basis`) |
| Decision | **CANONICAL_EXISTING** (complementary) |
| Canonical source of truth | `LabStockSolution` (persisted parsed result). Engine `Concentration` (parsing/validation logic). |
| Rationale | The engine provides the parsing/validation layer; the backend stores the parsed result. They are complementary, not competing. The engine `parse_concentration()` feeds into `LabStockSolution.active_fraction` + `fraction_basis`. |
| Adaptation plan | No migration needed. Ensure all stock creation paths go through `parse_concentration()` before persisting to backend. Add tests proving round-trip: `parse_concentration("10% w/w")` → `LabStockSolution(active_fraction=0.1, fraction_basis="w/w")` → `Concentration.from_dict()` reproduces the same value. |

### 13. Build-Plan Model

| Field | Value |
|-------|-------|
| Engine module | Not yet created |
| Candidate canonical | `backend/app/models/lab.py` → potential `LabBuildPlan` + `LabBuildLine` |
| Decision | **MISSING_CREATE_CANONICAL** |
| Canonical source of truth | To be created in Phase A2 |
| Rationale | A build plan (target → inventory mapping with substitutions) has no canonical equivalent. The engine `SubstitutionMapping` is a partial implementation but lacks lifecycle (draft → reviewed → reserved → executing → closed → superseded). A build plan is the bridge between the accepted target and the physical bottle. |
| Adaptation plan | Phase A2: Add `LabBuildPlan` and `LabBuildLine` tables to the backend. One line per target line or explicit technical line. Fields per plan spec: stable build-plan ID and version, immutable target version reference, selected stock lot reference, planned raw/active quantity and basis, uncertainty, substitution classification, preserved/lost functions, status lifecycle. No build-plan operation may mutate the target formula. |

---

## Duplicate Truth Stores Identified

| Concept | Engine store | Backend store | Risk |
|---------|-------------|---------------|------|
| Bottle event state | `BottleBatch._events` (mutable list) | `LabBottleEvent` (SQL, append-only) | **HIGH** — bidirectional writes can desynchronize |
| Stock consumption | `InventoryLedger.consume()` (in-place decrement) | `LabInventoryMovement` (append-only) | **HIGH** — in-place decrement bypasses audit trail |
| Formula version | `FormulaVersion` (in-memory DAG) | `LabFormulaVersion` (SQL, sequential) | **MEDIUM** — engine DAG is a projection, not a separate store if read-only |

## Prohibited Patterns

1. **No bidirectional writes.** Engine models may read from backend models but may not write to their own separate persistence. All writes go through the backend repository.
2. **No in-place stock decrement.** `InventoryLedger.consume()` must be replaced by append-only `LabInventoryMovement` records.
3. **No silent field loss.** `from_dict()` must preserve all fields or reject unknown fields under strict mode.
4. **No shallow deserialization.** `cls(**filtered_dict)` is prohibited. Use the canonical typed validation layer.

---

## Single Source of Truth Summary

| Domain concept | Canonical authority |
|----------------|-------------------|
| Evidence | `LabEvidenceRecord` (backend SQL) |
| Target formula | `LabFormulaVersion` (backend SQL) |
| Stock lot | `LabStockSolution` (backend SQL) |
| Build plan | `LabBuildPlan` / `LabBuildLine` (to be created) |
| Bottle event | `LabBottleEvent` (backend SQL) |
| Inventory movement | `LabInventoryMovement` (backend SQL) |
| Formula version DAG | `LabFormulaVersion` (backend SQL); engine `FormulaVersion` is read-only projection |
| Analytical data | To be created (backend SQL) |
| Sensory data | `LabExperiment` / `LabObservation` (backend SQL) |
| Regulatory restriction | `LabRestriction` (backend SQL) |
| Authority vector | Not persisted (derived computation) |
| Anti-compression | Not persisted (derived computation) |
| Chassis partition | Not persisted (derived computation) |
| Concentration parsing | Engine `parse_concentration()` (logic); parsed result in `LabStockSolution` |

---

## Phase A0 Exit Gate Checklist

- [x] Exact source state is reproducible (commit `2e46e4c`, branch `codex/add-inventory-materials`)
- [x] Current verifier result is captured (18 passed, 1 failed, 2 skipped)
- [x] Uncommitted work is preserved (patch + manifest)
- [x] Canonical domain map is proposed (this ADR — awaiting approval)
- [x] Duplicate truth stores identified (bottle events, stock consumption, formula version)
- [x] Branch identity confirmed (`codex/add-inventory-materials`)