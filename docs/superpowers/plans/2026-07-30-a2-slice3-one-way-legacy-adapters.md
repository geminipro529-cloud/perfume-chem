# A2 Slice 3 One-Way Legacy Adapters and Write Closure Plan

> **Execution rule:** Sol is the sole head engineer and final approver. No
> Codex subagents are permitted. DeepLuna Fast may perform bounded read-only
> review, but architecture, scientific meaning, security, provenance, scope,
> and acceptance remain local Sol decisions.

**Goal:** Make the append-oriented backend the only persistence and mutation
authority for every overlapping A2 domain while retaining deterministic
engine calculations as read-only projections or explicit import DTOs.

**Architecture:** Add a pure adapter boundary between canonical `lab_*`
records and legacy engine representations. Canonical rows may be projected
into engine objects for replay and analysis. Legacy engine payloads may be
converted into typed, non-persisting import drafts for review by the
application service. No adapter owns a session, commits a transaction, or
mutates a legacy ledger. Public mutation methods on duplicate engine ledgers
fail closed with one stable domain error. An AST-based regression guard rejects
future backend call sites that invoke those legacy mutators.

**Tech stack:** Python 3.11, SQLAlchemy 2, pytest, Ruff, MyPy.

---

Status: approved for autonomous execution by the user's standing A through D
authorization.

Starting implementation checkpoint:
`95380e440318994c6eed23ac2144143569f169fe`

Required predecessor gate: `A2_SLICE2_PASS`

## Scope boundary

This slice covers only:

1. canonical `LabBottleEvent`/effect to read-only `BottleBatch` projection;
2. canonical `LabStockSolution` to read-only `StockItem` projection;
3. canonical `LabFormulaVersion` to immutable engine formula-version
   projection;
4. canonical analytical rows to read-only `AnalyticalLedger` projection;
5. canonical experiment rows to read-only `SensoryTrial` projection;
6. canonical restrictions/assessments to regulatory snapshot projections;
7. explicit legacy evidence and analytical import drafts that do not write;
8. fail-closed legacy mutation methods;
9. an executable no-dual-write source guard;
10. deprecation and verification evidence.

This slice does not:

- delete a legacy table or historical engine file;
- create or run a database migration;
- modify the canonical database;
- expose new API routes;
- change formula, bottle, inventory, analytical, sensory, or regulatory
  scientific meaning;
- fabricate a missing density, method field, source, measurement, assessor,
  effective date, or authority class;
- begin A2 Slice 4, A3, or a later build before this slice passes.

## Canonical mapping

| Legacy object | Canonical authority | Allowed direction |
| --- | --- | --- |
| `EvidenceLedger` | `LabEvidenceRecord` | Legacy payload to non-persisting import drafts |
| `InventoryLedger` / `StockItem` | `LabStockSolution` + `LabInventoryMovement` | Canonical stock to read-only item |
| `BottleBatch` / `BottleEvent` | `LabBottleEvent` + effects + measurements | Canonical stream to read-only replay |
| `FormulaVersion` | `LabFormulaVersion` + version edges | Canonical version to immutable projection |
| `AnalyticalLedger` | `LabAnalytical*` + `LabGCOEvent` | Canonical rows to read-only analysis projection; legacy payload to import drafts |
| `SensoryTrial` | `LabExperiment` + sample/application/observation rows | Canonical rows to read-only analysis projection |
| `RegulatorySnapshot` | `LabRestriction` + dated assessment | Canonical rows to immutable snapshot projection |

## Fail-closed conversion rules

- A stock mass is converted to legacy volume only when a positive finite
  density exists. Missing density is an adapter error, never an assumed
  `1 g/mL`.
- Bottle replay is derived from canonical event effects. Positive effects
  become read-only dose events and negative effects become read-only removal
  events. Synthetic event identifiers bind both canonical event and effect
  IDs. No projection writes back.
- Formula projection requires canonical source metadata for any legacy-only
  field. Missing hashes or unsupported changes are reported rather than
  invented.
- Analytical projection requires the method/run parameter fields needed by
  the legacy dataclasses. Missing fields are an explicit adapter error.
- Sensory observation JSON is validated field by field. Missing assessor or
  score fields are not defaulted into scientific observations.
- Regulatory grouping requires one jurisdiction, category, amendment, and
  effective date. Mixed or unknown groups remain separate or fail closed.
- Import drafts are deterministic immutable payloads. Persisting them still
  requires an explicit `LabService` command in Slice 4 or later.

## TDD execution

### Task 1: Lock the write-closure contract

Create failing tests that require:

- `BottleBatch.add_event()` to raise `LegacyWriteProhibitedError`;
- `InventoryLedger.add_stock()`, `remove_stock()`, and `consume()` to raise;
- analytical `add_*` methods to raise;
- sensory `add_sample()` and `record_observation()` to raise;
- evidence `add_source()` and `add_claim()` to raise;
- deserialization and canonical projection factories to hydrate internal
  state without calling public mutators.

Run the focused tests and record the RED failures.

### Task 2: Implement stable read-only hydration

Add private/internal hydration paths and public read-only constructors:

- `BottleBatch.from_events(...)`;
- `AnalyticalLedger.from_records(...)`;
- `SensoryTrial.from_records(...)`;
- `EvidenceLedger.from_records(...)`.

Public duplicate-store mutators raise the stable domain error with code
`LEGACY_WRITE_PROHIBITED` and direct callers to `LabService`.

Update historical engine tests to build projections with the new constructors.
Mutation-specific tests must assert rejection.

### Task 3: Add canonical adapters

Create:

- `backend/app/adapters/__init__.py`;
- `backend/app/adapters/lab_legacy.py`.

Adapters are pure functions. They may import ORM row types and engine
dataclasses but may not import `AsyncSession`, `LabRepository`, or call any
legacy mutation method.

Add focused equivalence tests for:

- bottle mass and stock composition against `LabRepository.reconstruct_bottle`;
- stock amount conversion with exact density;
- formula parent/hash/change metadata;
- analytical run/peak/GC-O field preservation;
- sensory sample and observation field preservation;
- regulatory snapshot identity and date;
- deterministic legacy import draft hashes;
- rejection of lossy or ambiguous conversion.

### Task 4: Add the dual-write guard

Create `backend/app/verification/legacy_write_guard.py`.

The guard parses Python AST under `backend/app` and fails when application
code calls:

```text
BottleBatch.add_event
InventoryLedger.add_stock
InventoryLedger.remove_stock
InventoryLedger.consume
EvidenceLedger.add_source
EvidenceLedger.add_claim
AnalyticalLedger.add_gcms_run
AnalyticalLedger.add_hsspme_run
AnalyticalLedger.add_gco_event
SensoryTrial.add_sample
SensoryTrial.record_observation
```

The guard also verifies that adapter modules contain no transaction/session
ownership. Tests exercise positive and negative fixtures.

### Task 5: Document deprecation and verify

Create:

- `docs/verification/a2_slice3/README.md`;
- `docs/verification/a2_slice3/legacy_domain_deprecation.md`.

Run, without PTY and with explicit timeouts:

1. focused adapter/write-closure tests;
2. all affected engine tests;
3. full backend tests;
4. full root tests under supported Python 3.11;
5. Ruff over changed production and test paths;
6. MyPy over `backend/app` and changed engine modules;
7. canonical verifier;
8. artifact verifier;
9. protected database hash/integrity checks;
10. bounded diff and DeepLuna read-only review.

## Exit gate

`A2_SLICE3_PASS` requires:

- backend SQL remains the only persistent write authority;
- duplicate legacy ledger mutations fail closed;
- canonical-to-engine projections are read-only and deterministic;
- legacy imports produce drafts only and cannot persist;
- no new backend dual-write call site exists;
- every priority domain has an explicit mapping or a documented fail-closed
  exclusion;
- no legacy table/file is deleted;
- no migration or canonical database mutation occurred;
- focused, backend, root, lint, type, verifier, and artifact checks pass or
  report only already-authorized optional skips;
- a bounded implementation checkpoint exists.

Failure of any item keeps A2 Slice 4 prohibited.
