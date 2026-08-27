# Build B3 Contextual Threshold and OAV Implementation Plan

## Goal

Implement the frozen B3 design without modifying the dirty legacy ODT/OAV
engine paths and without beginning B4.

## Task 1: Prove schema and service behavior RED

Create focused unit tests for:

- threshold-context validation and persistence;
- all ten stable OAV mismatch codes and deterministic ordering;
- compatible unit-scale conversion and ratio computation;
- forbidden cross-basis and solution-to-air conversion;
- strict authority and model applicability;
- screening-only permitted and prohibited claims;
- legacy status preservation and non-promotion; and
- explicit-ID retrieval with no latest-value query.

Run only the new unit tests and preserve their expected failures.

## Task 2: Add B3 models and repository composition

Add:

- `backend/app/models/lab_thresholds.py`;
- `backend/app/repositories/lab_thresholds.py`; and
- imports/mixins in the canonical lab model and repository composition.

Keep all records append-only and all reads explicit by ID or content hash.

## Task 3: Add the deterministic B3 service

Add:

- typed threshold-context, assessment, and legacy-import commands;
- exact compatibility and unit-convention checks;
- stable mismatch ordering;
- strict authority gates;
- deterministic hashes; and
- screening-only claim surfaces.

Compose the service into `LabService`. Run the focused unit tests GREEN.

## Task 4: Add the reversible migration

Create `20260730_0007_b3_contextual_thresholds.py` after B2 head. The migration
must:

- create exactly the three B3 tables;
- install append-only SQLite triggers;
- enforce model-equivalent checks and foreign keys;
- import zero legacy values;
- downgrade in reverse dependency order; and
- leave all earlier tables and data unchanged.

Add upgrade/downgrade and database-guard tests.

## Task 5: Verify legacy quarantine and compatibility

Add a legacy adapter that converts supplied ODT dictionaries into quarantine
commands while preserving exact status. It must not import the engine module
at migration time and must not produce B2 observations or assertions.

Update only current-head expectations in backup/migration compatibility tests.
Run B1, B2, B3, migration, backup/restore, and export/import tests.

## Task 6: Canonical promotion and acceptance

In the scratch clone:

- run focused tests;
- run the B1+B2+B3 compatibility slice;
- run Ruff on exact changed paths;
- run scoped mypy;
- verify database upgrade/downgrade and integrity.

Then:

- compare every promoted file hash;
- batch-promote exact verified paths to the authoritative repository;
- rerun the same commands in the authoritative repository;
- preserve stdout/stderr and hashes;
- run a fresh exact-project DeepLuna health gate;
- run one bounded Fast-only B3 read audit; and
- have Sol independently verify each finding.

Write the B3 gate report and commit only exact B3 paths. Stop before B4 unless
the B3 exit gate passes.
