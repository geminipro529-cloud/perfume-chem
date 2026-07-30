# Build B4 Knowledge-Rule Compiler Implementation Plan

## Goal

Implement the frozen B4 design without modifying the legacy rule corpus,
protected knowledge database, mutable compatibility models, dirty optimizer
paths, or any B5+ surface.

## Task 1: Prove canonical schema behavior RED

Create focused unit tests for:

- six-table model shape and model/migration index parity;
- exact/group/generic/unresolved endpoint one-of constraints;
- frozen relation, status, directionality, review, and runtime-role enums;
- authoritative-blocking prerequisites;
- generic/advisory/non-authoritative blocking rejection;
- numerical-model controlled-evidence prerequisites; and
- append-only and deterministic hash invariants.

Run only the new schema/service tests and preserve the expected failures.

## Task 2: Add canonical models and repository composition

Add:

- `backend/app/models/lab_rules.py`;
- `backend/app/repositories/lab_rules.py`; and
- exact imports/mixins in the existing lab model and repository composition.

All retrieval is by explicit ID, version key, or content hash. There is no
`latest` query and no update/delete method.

## Task 3: Implement the fail-closed compiler service

Add `backend/app/services/lab_rules.py` with:

- typed group, rule, contradiction, support, and compilation commands;
- canonical JSON and content hashing;
- endpoint, source, matrix, dose, temporal, review, and authority checks;
- controlled-evidence numerical promotion checks;
- stable diagnostics and duplicate/cycle/contradiction handling; and
- transparent recommendation projections with no mutation command.

Compose it into `LabService` and run the focused tests GREEN.

## Task 4: Inventory the legacy corpus

Add `backend/app/adapters/legacy_rules.py` and tests that:

- read supplied payloads only;
- inventory exactly 5 + 2,408 + 915 + 53 records;
- preserve source path, JSON pointer, raw value, and digest;
- classify generic prose separately from unresolved exact identities;
- reject the legacy implicit `hard` promotion;
- expose duplicate, contradiction, cycle, orphan, and unsupported-numerical
  diagnostics; and
- perform no database write or runtime connection.

Generate and verify
`backend/tests/fixtures/b4_rule_corpus_baseline.json` from the deterministic
compiler result. Add a non-increase test for invalid exact rules and
non-promotion tests for generic and numerical legacy claims.

## Task 5: Add the reversible migration

Create `20260731_0008_b4_knowledge_rules.py` after B3 head. It must:

- create exactly the six B4 tables;
- enforce model-equivalent checks and foreign keys;
- install append-only SQLite triggers;
- import zero legacy groups or rules;
- downgrade in reverse dependency order; and
- leave all B1-B3 and protected legacy data unchanged.

Add upgrade/downgrade, database-guard, current-head, and backup/restore tests.

## Task 6: Verify and promote

In the scratch clone:

- run focused B4 tests;
- run the B1-B4 compatibility slice;
- run Ruff on exact B4 paths;
- run scoped mypy;
- compile the full 3,381-record source corpus twice and compare reports;
- verify invalid-exact non-increase;
- verify model/migration table, column, constraint, index, and trigger parity;
- verify downgrade/re-upgrade and protected database hashes.

Then:

- build and verify a canonical prepromotion recovery archive;
- compare every promoted path hash;
- promote only exact B4 paths;
- rerun the same commands in the authoritative repository;
- preserve stdout/stderr and hashes;
- run a fresh exact-project DeepLuna health gate;
- run one bounded Fast-only implementation audit; and
- have Sol independently reproduce every finding.

Write and commit the B4 gate report only if all exit criteria pass. Do not
begin B5 until B4 is closed PASS.
