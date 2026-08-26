# Build B6 Safety and Regulatory Authority Implementation Plan

> **Authority:** Execute this plan in the canonical
> `D:\chatbots\perfume-chem` workspace. Preserve unrelated dirty and untracked
> work. Stage and commit only named B6 paths. Use supported Python 3.11.15,
> non-interactive commands, disabled ANSI output, captured stdout/stderr, and
> explicit timeouts.

**Goal:** Implement the frozen B6 date-aware, fail-closed regulatory screening
authority and pass the B6 exit gate without connecting production consumers.

**Architecture:** Add seven append-only SQLAlchemy/Alembic tables and a
transactional service mixin. B1 remains artifact/workflow authority; formulas,
build plans, stocks, and materials remain identity authority. B6 resolves and
hashes exact upstream versions, performs regulatory-only constituent
aggregation, persists per-rule findings, and derives one four-state snapshot.

**Runtime:** Python 3.11.15 at
`D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe`;
SQLAlchemy 2; Alembic; pytest; Ruff; mypy.

---

## Task 1: Establish RED schema and migration contracts

**Create:**

- `backend/tests/unit/test_b6_regulatory_schema.py`
- `backend/tests/integration/test_b6_regulatory_migration.py`

**Test first:**

1. Assert the seven table names are present in `Base.metadata` and
   `APPEND_ONLY_TABLES`.
2. Assert exact enum checks, SHA-256 checks, uniqueness, version chains,
   subject shape, projection family, pass-wording shape, and foreign keys.
3. Upgrade a fresh database from B5 head to B6 head and assert zero B6 rows.
4. Assert all B6 update/delete triggers exist.
5. Downgrade to B5 and re-upgrade without touching B5 rows.

**Run RED:**

```powershell
& $py -m pytest tests/unit/test_b6_regulatory_schema.py tests/integration/test_b6_regulatory_migration.py --color=no -q --basetemp=../output/pytest-temp-backend/b6-schema-red
```

Expected: import/table/migration failures because B6 does not exist.

## Task 2: Implement models, registration, and zero-backfill migration

**Create:**

- `backend/app/models/lab_regulatory.py`
- `backend/alembic/versions/20260731_0010_b6_regulatory_authority.py`

**Modify:**

- `backend/app/models/lab.py`

**Implement:**

1. Define exact constant vocabularies and the seven mapped classes.
2. Mirror every model constraint and index in the migration.
3. Add all B6 tables to `REGULATORY_AUTHORITY_TABLE_NAMES` and
   `APPEND_ONLY_TABLES`.
4. Create SQLite append-only triggers and PostgreSQL trigger-function support
   using the established B1-B5 pattern.
5. Keep upgrade zero-backfill and downgrade B6-only.

**Run GREEN:**

```powershell
& $py -m pytest tests/unit/test_b6_regulatory_schema.py tests/integration/test_b6_regulatory_migration.py --color=no -q --basetemp=../output/pytest-temp-backend/b6-schema-green
```

## Task 3: Establish RED source, rule, and supplier-scope behavior

**Create/extend:**

- `backend/tests/unit/test_b6_regulatory_service.py`

**Test first:**

1. Official sources require exact accepted B1 scope and matching digest.
2. All six statuses are accepted with valid date shapes.
3. Draft/consultation/watchlist cannot supersede or become enforceable.
4. Superseded source selection fails deterministically.
5. Same-day source verification is required.
6. Rule source/jurisdiction/category/use and threshold shapes are exact.
7. EU leave-on/rinse-off thresholds and inclusive transition boundaries are
   action-aware.
8. Supplier bindings reject cross-supplier, product, code, grade, version, lot,
   type, digest, expiry, and B1-scope mismatches.

**Run RED:**

```powershell
& $py -m pytest tests/unit/test_b6_regulatory_service.py -k "source or rule or supplier or transition" --color=no -q --basetemp=../output/pytest-temp-backend/b6-authority-red
```

## Task 4: Implement repository and authority registration services

**Create:**

- `backend/app/repositories/lab_regulatory.py`
- `backend/app/services/lab_regulatory.py`

**Modify:**

- `backend/app/repositories/lab.py`
- `backend/app/services/lab_service.py`

**Implement:**

1. Typed immutable inputs with strict normalization and timezone validation.
2. Canonical JSON and SHA-256 helpers local to the B6 module.
3. Repository reads for exact IDs, latest version chains, superseding source
   checks, formula/build lines, profiles, entries, and snapshot findings.
4. Source/rule registration with B1 type, digest, workflow-scope, status, date,
   parent, and supersession validation.
5. Supplier-document binding with exact normalized stock identity and expiry.
6. Stable typed conflict codes; no ambient unscoped latest selection.

**Run GREEN:**

```powershell
& $py -m pytest tests/unit/test_b6_regulatory_service.py -k "source or rule or supplier or transition" --color=no -q --basetemp=../output/pytest-temp-backend/b6-authority-green
```

## Task 5: Establish RED composition and projection separation

**Extend:**

- `backend/tests/unit/test_b6_regulatory_service.py`

**Test first:**

1. Lot-specific natural profiles require a matching lot-scoped composition
   document.
2. Documented proxies require a product-scoped source and assumptions.
3. Known profiles require entries and exact fraction basis.
4. Unknown profiles require no entries.
5. Partial/unknown/missing natural composition cannot support pass.
6. Composition entries reject `OLFACTORY` and `IDENTITY_AUTHENTICITY`
   projection families.
7. Version chain and duplicate hash behavior are deterministic.

**Run RED then implement in `lab_regulatory.py`, and run GREEN.**

## Task 6: Establish RED formula/build evaluation and result lattice

**Extend:**

- `backend/tests/unit/test_b6_regulatory_service.py`

**Test first:**

1. Formula components aggregate direct and natural constituents with stock
   active fraction and finished concentration.
2. Build-plan lines produce the same regulatory basis from planned active/raw
   quantities.
3. Contributions aggregate by canonical material/CAS identity.
4. A known over-limit rule yields `FAIL`.
5. Unknown authority/composition/document state yields `UNKNOWN`.
6. Known failure outranks simultaneous unknown state.
7. All enforceable rules passing yields `PASS_FOR_DECLARED_SCOPE`.
8. Draft/consultation/watchlist/future-not-applicable rules persist
   `NOT_EVALUATED` findings and do not affect the enforced result.
9. Only a pass stores service-generated scoped wording.
10. Caller wording, certificate wording, naive times, non-finite numbers, and
    unsupported bases are rejected.
11. An A2 `PASS` without a B6 snapshot remains non-authoritative.

**Implement:**

1. Exact subject resolution for formula and build-plan versions.
2. Current-state, transition, supplier-document, and profile gates.
3. Regulatory-only contribution calculation and aggregation.
4. Stable finding reason codes and deterministic final result lattice.
5. Atomic persistence of snapshot plus all findings.

**Run GREEN:**

```powershell
& $py -m pytest tests/unit/test_b6_regulatory_service.py --color=no -q --basetemp=../output/pytest-temp-backend/b6-service-green
```

## Task 7: Prove migrated-database end-to-end behavior

**Create:**

- `backend/tests/integration/test_b6_regulatory_e2e.py`

**Test first:**

1. Upgrade an on-disk database to B6.
2. Register accepted official and supplier B1 sources.
3. Record current IFRA, IFRA 52 consultation, and EU source states.
4. Record restriction and allergen rules with transition windows.
5. Bind exact supplier documents and natural-lot composition.
6. Evaluate one formula and one build-plan pass.
7. Reproduce unknown natural composition and failed restriction paths.
8. Prove IFRA 52 consultation remains non-enforced.
9. Prove an exact supplier-grade or lot mismatch fails closed.
10. Prove A2 `PASS` alone yields no B6 authority record or wording.

**Run focused compatibility:**

```powershell
& $py -m pytest tests/unit/test_a2_science_schema.py tests/unit/test_a2_science_service.py tests/integration/test_a2_science_migration.py tests/unit/test_b1_source_schema.py tests/unit/test_b1_source_service.py tests/integration/test_b1_source_migration.py tests/unit/test_b2_property_schema.py tests/unit/test_b2_property_service.py tests/integration/test_b2_property_migration.py tests/unit/test_b3_threshold_schema.py tests/unit/test_b3_threshold_service.py tests/integration/test_b3_threshold_migration.py tests/unit/test_b4_rule_schema.py tests/unit/test_b4_rule_service.py tests/integration/test_b4_rule_migration.py tests/unit/test_b5_analytical_schema.py tests/unit/test_b5_analytical_service.py tests/integration/test_b5_analytical_migration.py tests/integration/test_b5_analytical_e2e.py tests/unit/test_b6_regulatory_schema.py tests/unit/test_b6_regulatory_service.py tests/integration/test_b6_regulatory_migration.py tests/integration/test_b6_regulatory_e2e.py tests/integration/test_lab_migration.py tests/integration/test_backup_restore.py --color=no -q --basetemp=../output/pytest-temp-backend/b6-compat
```

## Task 8: Static checks, protected-state proof, and B6 report

**Create:**

- `docs/verification/b6/regulatory_authority_gate.md`
- `docs/verification/b6/regulatory_authority_gate.json`
- captured logs under `docs/verification/b6/logs/`

**Run:**

1. Exact B6 plus B1-B6 compatibility pytest with stdout/stderr files.
2. Ruff over exact touched Python files with `--no-cache` and concise,
   non-colored output.
3. mypy over B6 model/repository/service with an explicit writable cache and
   non-colored output.
4. Alembic current-head, fresh-upgrade, downgrade/re-upgrade, integrity, and
   backup/restore checks.
5. Protected database byte length, SHA-256, and immutable integrity checks.
6. `git diff --check`, staged-scope checks, and inventory of remaining
   unrelated dirty/untracked work.

The report must include exact commands, timeouts, exit codes, test counts,
runtime versions, log digests, migration head, archive digest, protected
database before/after fingerprints, known limits, and the statement that B6
is a scoped screening authority rather than legal or certificate issuance.

## Task 9: DeepLuna Fast final audit and Sol reproduction

1. Run a fresh exact-project `deepseek_check`.
2. If and only if readiness is `READY`, submit one bounded read-only FLASH
   audit over the frozen design, B6 implementation, tests, migration, and
   draft report, with `NO_LUNA`, one attempt, one provider call, no commands,
   no writes, no secrets, and no final authority.
3. Reproduce every concrete DeepLuna finding locally.
4. Fix verified defects test-first; reject unsupported findings with evidence.
5. Re-run affected focused checks and the final compatibility gate.
6. Finalize the machine-readable and Markdown reports.

## Task 10: Commit and stop at the B6 phase gate

1. Confirm the index contains only named B6 implementation/report paths.
2. Commit implementation and report in intentional exact-path commits.
3. Confirm protected databases are unchanged and the index is empty.
4. Update the plan status.
5. Continue to B7 only after the B6 exit gate is demonstrably passed.
