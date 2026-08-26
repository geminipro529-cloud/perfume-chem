# Legacy Domain Deprecation Boundary

Status: active as of A2 Slice 3

The append-oriented backend `lab_*` model is the only persistence and mutation
authority for the overlapping domains below. Engine objects remain available
for deterministic calculations, compatibility reads, and explicit import
review. They are not independent truth stores.

| Legacy surface | Canonical write authority | Allowed legacy use |
| --- | --- | --- |
| `EvidenceLedger` | `LabEvidenceRecord` through `LabService` | Read-only contradiction/authority calculations; deterministic import draft |
| `InventoryLedger` | `LabStockSolution` and append-only `LabInventoryMovement` | Read-only stock lookup and target mapping |
| `BottleBatch` | `LabBottleEvent`, effects, measurements, and inventory movements | Read-only replay of projected canonical events |
| `FormulaVersion` | `LabFormulaVersion` and canonical parent edges | Immutable DAG projection and proposal calculation |
| `AnalyticalLedger` | `LabAnalytical*` and `LabGCOEvent` | Read-only search/analysis; deterministic import draft |
| `SensoryTrial` | `LabExperiment`, sample, application, and observation rows | Read-only summary and mismatch calculation |
| `RegulatorySnapshot` | Dated restrictions and regulatory-assessment versions | Immutable calculation view |

## Prohibited write methods

The following methods now raise `LegacyWriteProhibitedError` with stable code
`LEGACY_WRITE_PROHIBITED`:

- `BottleBatch.add_event`;
- `InventoryLedger.add_stock`;
- `InventoryLedger.remove_stock`;
- `InventoryLedger.consume`;
- `EvidenceLedger.add_source`;
- `EvidenceLedger.add_claim`;
- `AnalyticalLedger.add_gcms_run`;
- `AnalyticalLedger.add_hsspme_run`;
- `AnalyticalLedger.add_gco_event`;
- `SensoryTrial.add_sample`;
- `SensoryTrial.record_observation`.

Compatibility payloads are hydrated with dedicated read-only constructors:

- `BottleBatch.from_events`;
- `EvidenceLedger.from_records`;
- `AnalyticalLedger.from_records`;
- `SensoryTrial.from_records`;
- their strict `from_dict` readers.

Tests may use isolated mutable fixture subclasses to exercise historical
calculation behavior. Those subclasses do not exist in production modules and
have no persistence authority.

## One-way adapter policy

`backend/app/adapters/lab_legacy.py` contains pure transformations only:

- canonical rows to engine read projections;
- legacy evidence/analytical payloads to deterministic `LegacyImportDraft`
  objects.

An import draft is not a database command. It carries a destination, stable
key, canonical JSON payload, SHA-256 digest, and limitations. Persisting it
requires a separate explicit application-service operation.

The adapter rejects missing density, missing method fields, ambiguous event
effects, missing sensory context, missing regulatory dates, malformed hashes,
cross-linked rows, and non-finite values. It does not assume `1 g/mL`, invent
measurements, infer assessors, or promote unknown authority.

## Executable guard

`backend/app/verification/legacy_write_guard.py` parses backend source files.
It rejects:

- imports of duplicate mutable ledger classes outside the adapter boundary;
- calls to legacy mutation methods inside adapters;
- session, repository, service, commit, or rollback authority inside adapters.

Legacy deletion is intentionally deferred. No historical table or engine file
is removed by this slice.
