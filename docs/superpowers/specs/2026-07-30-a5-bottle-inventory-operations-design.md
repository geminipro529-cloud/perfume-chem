# Build A Phase A5 bottle and inventory operations design

Date: 2026-07-30

## Objective

Close the physical-operation boundary without creating a second truth store.
Canonical writes remain in the SQLAlchemy laboratory schema and
`LabService`; engine objects remain immutable replay and decision helpers.

## Verified starting point

The repository already provides:

- immutable bottle event/effect rows with per-stream sequence and command
  uniqueness;
- transactional stock additions and paired bottle transfers;
- append-only reservation events;
- proposal -> human confirmation -> measurement -> commit;
- database-serialized stock and stream concurrency tests;
- backup/restore digest and migration checks.

The verified gaps are:

- the engine enum exposes legacy `DOSE_STOCK`, not canonical
  `ADD_MATERIAL`;
- `DILUTE` directly adds solvent during replay instead of deriving
  concentration from actual addition events;
- engine `TRANSFER` is explicitly a no-op;
- close/tare semantics are not enforced by the canonical write service;
- persisted inventory movements omit movement type, build-plan cause,
  raw/active quantities, basis, before/after balance, uncertainty, actor,
  transaction, and correction/reversal links;
- lot selection blindly prioritizes concentration and does not evaluate the
  declared twelve factors;
- the persisted state diff lacks target/build/reservation/measurement fields.

The bounded DeepLuna audit did not identify these source-visible gaps and
omitted its required citation table. It is historical input only, not
acceptance evidence.

## Architecture

### Domain semantics

`engine.bottle.events` remains the read-only replay compatibility boundary.
It gains canonical `ADD_MATERIAL`, a complete event-semantics table,
contiguous sequence and idempotency validation, committed-only physical
effects, event-derived tare metadata, closed-stream enforcement, and
derived-only dilution markers. `DOSE_STOCK` remains a readable legacy alias.

`engine.inventory.operations` is a pure, typed domain module for:

- the eight inventory movement types;
- complete immutable movement records;
- deterministic balance replay;
- twelve-factor lot eligibility and ranking;
- typed target-to-stock state deltas;
- transfer-pair validation.

It owns no persistence.

### Canonical persistence

Alembic revision `20260730_0004` expands
`lab_inventory_movements` in place. Existing movement rows are backfilled
deterministically and remain readable. New rows require:

- movement type and idempotency key;
- build-plan line, reservation, bottle-event/effect, or administrative cause;
- raw and active quantity in a declared unit and basis;
- before and after physical balance;
- uncertainty, actor, transaction, and correction/reversal references.

Database checks prevent negative balances, impossible active quantities,
unknown movement types, ambiguous correction/reversal links, and duplicate
idempotency keys. Append-only triggers remain active after migration.

### Transaction service

`LabService` remains the single transaction owner.

- reservations append `RESERVATION` audit movements without changing physical
  stock;
- release appends `RESERVATION_RELEASE`;
- bottle additions append `CONSUMPTION`;
- compensation appends `REVERSAL` linked to the original movement;
- reconciliation appends `ADJUSTMENT`;
- bottle transfer records one transaction, two stream events, measured loss,
  and linked source/destination effects;
- tare and close commands append events without changing chemical contents;
- ordinary physical additions to a closed bottle fail before any row is
  written.

The lifecycle commit passes build-line, actor, uncertainty, and action state
to both movement persistence and the structured state diff.

## Invariants

- Events and movements are never updated or deleted.
- Every new physical write is idempotent and optimistic-concurrency checked.
- Stream sequences are contiguous.
- A failed transaction writes neither bottle nor inventory half.
- Physical stock balance is movement replay, not an opaque decrement.
- Reservation movements do not alter physical balance.
- Dilution concentration is derived from material and solvent additions.
- Tare changes reference metadata only.
- Corrections and reversals append and cannot form cycles.
- Unknown units, bases, densities, identity, safety, or expiry fail closed.
- Lot ranking never promotes an ineligible lot.

## Verification boundary

A5 passes only after domain, migration, service, concurrency, failure,
backup/restore, deterministic replay, and full target-to-bottle lifecycle
tests pass, followed by the canonical project verifier and protected database
restoration.
