# A2 Slice 2 verification record

Status: `A2_SLICE2_PASS`

This record covers only Build A, A2 Slice 2 (A2.2), canonical analytical,
dated regulatory-assessment, and claim-specific authority persistence. It does
not promote full A2 completion, A3, or scientific release.

## Checkpoint identity

- Branch: `codex/add-inventory-materials`
- Accepted A2.1 implementation checkpoint:
  `7e0dc59ef031301a19561f7d167fa863ad8b5c14`
- A2.2 plan checkpoint and implementation parent:
  `bfaf1b6c556dc7b0f8ab6eda0ba30f6e3af7f2a0`
- Plan SHA-256:
  `bdd69f1c74561815b37f6833f9ea4c56bec514e7ea3721f3a6d38b625ed24269`
- Ending implementation checkpoint: this record is committed in the bounded
  checkpoint whose message is
  `build(a2): add science authority persistence`. A commit cannot contain its
  own literal SHA without changing that SHA; resolve it with
  `git rev-parse HEAD` and verify that its parent is `bfaf1b6...`.

## Recovery and protected state

Implementation reused the verified, path-preserving A2 recovery package at:

`C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a2-slice1-preimplementation-recovery\perfume-chem-a0-20260729T194130Z`

The package was already restoration-verified, recorded zero source changes
during capture, and contains restorable tracked, untracked, ignored-important,
and database state. Sensitive archive contents were not transmitted.

The preexisting dirty worktree was not cleaned or rewritten.

Protected state after verification:

- `perfume_chem.db`: zero bytes, SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `data/perfumery_kb.db`: SQLite integrity `ok`, restored SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`.
- `backend/app/api/v1/endpoints/lab.py`: unchanged SHA-256
  `001ad5bd79aa8439070eb6273b2cb2362da5ab162c2f722fb7c57324ac74e5c5`.
- `backend/app/schemas/lab.py`: unchanged SHA-256
  `d1f450e5668830ffdfbf91a5f54ab2b45daaef6250c4a4545816f2fd01055aa8`.
- `backend/tests/integration/test_lab_api.py`: unchanged SHA-256
  `04bce8fff450b5fa8ef8ace049960cfca5a19c20b8ae6d81bf81cfeef04241a6`.

The canonical verifier changed the knowledge database during its test run.
The changed copy had SQLite integrity `ok`, but did not match the protected
hash. A separate candidate was extracted by exact path from the verified local
recovery archive, checked for the protected SHA-256 and SQLite integrity, and
only then copied over the authoritative path. The restored database was
rechecked after replacement.

## Changed paths

The bounded implementation checkpoint contains only:

- `backend/alembic/versions/20260730_0002_a2_science_authority.py`
- `backend/app/models/lab.py`
- `backend/app/models/lab_science.py`
- `backend/app/repositories/lab.py`
- `backend/app/repositories/lab_science.py`
- `backend/app/services/lab_export.py`
- `backend/app/services/lab_science.py`
- `backend/app/services/lab_service.py`
- `backend/tests/integration/test_a2_planning_export.py`
- `backend/tests/integration/test_a2_planning_migration.py`
- `backend/tests/integration/test_a2_science_export.py`
- `backend/tests/integration/test_a2_science_migration.py`
- `backend/tests/integration/test_a2_science_transactions.py`
- `backend/tests/integration/test_backup_restore.py`
- `backend/tests/integration/test_lab_migration.py`
- `backend/tests/unit/test_a2_science_schema.py`
- `backend/tests/unit/test_a2_science_service.py`
- `docs/verification/a2_slice2/README.md`

No API, legacy engine analytical, heuristic regulatory, formula artifact,
canonical database, or A2 Slice 3 path is included.

## Canonical implementation

Ten append-only canonical tables were added:

- analytical method versions;
- analytical runs;
- analytical peaks;
- analytical QC records;
- analytical attachment digests;
- GC-olfactometry events;
- regulatory assessment versions;
- regulatory findings;
- claim assessment versions;
- claim-assessment evidence links.

The explicit `20260730_0002` migration:

- has parent `20260730_0001`;
- creates the ten tables in foreign-key order;
- installs named uniqueness, state, range, subject, quantity/basis, and
  composite ownership constraints;
- installs SQLite update/delete denial triggers for every new table;
- downgrades to the planning head in reverse dependency order;
- does not import ORM metadata or mutate legacy rows.

There is exactly one Alembic head:

```text
20260730_0002 (head)
```

## Authority and fail-closed decisions

- Dedicated analytical tables are canonical. Generic `LabObservation` was not
  overloaded with chromatographic or method-version semantics.
- Analytical method, regulatory assessment, and claim assessment revisions
  preserve stable identities, monotonically increasing versions, parent IDs,
  content hashes, and parent hashes.
- Runs require a versioned method and at least one existing canonical subject.
- Peaks preserve identity state, explicit quantitation basis/unit, uncertainty,
  and material identity when confirmed.
- QC `UNKNOWN` and `FAIL` remain explicit and cannot support exact analytical
  authority.
- Attachments store metadata, byte length, locator, and SHA-256 only. Raw bytes
  are not accepted or exported.
- GC-O events use pseudonymous assessor identity and enforce same-run peak
  ownership.
- Regulatory `PASS` requires current named authority, source evidence, no
  unresolved items, and scoped permitted wording.
- Regulatory finding `PASS` requires comparable explicit fractions and a
  concentration basis, with observed fraction no greater than the limit.
- `ALLOW_EXACT` requires direct evidence, no missing evidence, no conflicts,
  permitted wording, and satisfied review. Exact analytical claims also
  require passing QC.
- The two legacy `AuthorityVector` implementations remain derived engine
  computations. No averaged or per-axis legacy vector fields are persisted.
- Claim assessments are authority records, not release decisions.

`LabService` remains the transaction owner. Repository mixins issue
deterministic queries and flush inserts; they do not commit, roll back, or make
scientific decisions.

## Export and compatibility

- The protected default export remains `lab-export-v1`.
- `export_planning_workspace()` remains explicit `lab-export-v2`.
- `export_science_workspace()` and canonical bytes use `lab-export-v3`.
- Imports accept v1, v2, and v3.
- V1 and v2 imports do not invent science-authority rows.
- V3 order follows all foreign-key dependencies and stable identity/version
  keys.
- V3 round-trip bytes are deterministic and import is idempotent.
- Date, timezone-aware datetime, JSON, IDs, and attachment digest metadata
  round-trip without embedded attachment bytes.

## Test-driven evidence

All acceptance commands used non-PTY execution, disabled ANSI output, and
explicit executor timeouts. Stdout and stderr were retained by the executor
and canonical verifier report.

Observed RED states:

- Schema metadata: 3 expected failures before science-authority tables existed.
- Migration: 5 expected failures and 1 pass before
  `20260730_0002` existed.
- Service: collection failed because `app.services.lab_science` did not exist.
- V3 export: 2 expected failures and 1 pass before
  `export_science_workspace()` existed.
- Combined compatibility exposed one date/time import regression:
  43 passed and 1 failed because the importer did not recognize the repository
  `UTCDateTime` type decorator. The importer was corrected at the type boundary
  and the failing test then passed.

Progressive GREEN states:

- Science schema plus migration: 9 passed.
- Science service: 8 passed.
- Science transaction/concurrency: 3 passed.
- Science v3 plus planning v2 export: 6 passed.
- Combined A2.2 and A2.1 compatibility: 70 passed.
- Ruff: `poetry run ruff check app alembic tests` passed.
- MyPy: `poetry run mypy app --ignore-missing-imports` passed for 78 app
  source files.
- Full backend: 249 passed, 0 failed, 0 errors, 0 skipped in 122.65 seconds.
- Full root suite on Python 3.11.15: 1,000 passed, 0 failed, 0 errors, 0
  skipped in 85.54 seconds.

JUnit evidence:

- `verification_runs/a2-slice2-backend.xml`
- `verification_runs/a2-slice2-root.xml`

## Root-runtime and verifier diagnosis

An initial plain root `pytest` invocation was rejected as acceptance evidence.
It omitted the authoritative `tests` target, traversed preserved archive and
output directories, and used the global environment. This produced duplicate
module collection and inaccessible preserved-temp errors, not product test
failures.

Collection restricted to `tests` proved the intended boundary. The existing
root `.venv` then reproduced the known Python 3.14/protobuf incompatibility on
two modules. A disposable verification environment was created under
`output/verification-envs/a2-slice2-py311` using CPython 3.11.15. It received
only root test, typecheck, lint, and package-build dependencies. Existing
environments and preserved archives were not deleted or rewritten.

The first complete canonical verifier run found two environment failures:

- engine MyPy resolved to the stale root `.venv`, where `librt.internal` was
  unavailable;
- the disposable uv environment did not initially include pip/setuptools for
  the verifier's no-build-isolation wheel command.

The verifier's documented local-tool precedence was confirmed from executable
code and tests. MyPy, Ruff, pip, setuptools, and wheel were installed only in
the disposable Python 3.11 environment. The two failed checks then passed
independently, and the full verifier was rerun from the beginning.

## Canonical project verifier

Final `verification_runs/project_verification.json`:

- SHA-256:
  `d30b774b460923bd7fadebf74b358ff19d663ae09ccaf11a32ce04692421547b`;
- 19 required checks passed;
- 0 checks failed;
- 2 optional checks skipped;
- skipped checks: Docker build and Docker smoke, because Docker was not
  requested;
- completion gate: `PASS_WITH_SKIPS`;
- code axis: ready;
- data axis: ready;
- infrastructure axis: ready;
- local validation evidence: passed;
- scientific release: blocked by missing held-out sensory validation.

Artifact verifier:

- status `WARN`;
- 515 formula files classified;
- 452 `NONE`;
- 14 explicitly `QUARANTINED`;
- 49 `UNBOUND_LEGACY`;
- quarantined stale artifacts remain non-promoting;
- no artifact classification was converted into scientific release authority.

Golden fixture SHA-256 was unchanged:

`0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec`

## DeepLuna use and local acceptance

- Planning-pattern extraction:
  `DS-03d4ee6e30d9674454bc52d7089f2c0c` (`PASS`).
- An earlier oversized extraction request failed locally at its token ceiling
  and was not used as evidence.
- Final bounded mechanical audit:
  `DS-c6a285e365f5129ce0ec1556153c99c0` (result recorded below before commit).

DeepLuna remained read-only and Fast-only. Sol independently inspected the
live files, rejected persistence of legacy `AuthorityVector` objects, ran all
acceptance commands, restored verifier side effects, and retained final
architecture, science, provenance, security, scope, and acceptance authority.

Final bounded audit result:

`PASS`, with no negative findings, architecture uncertainty, scientific
uncertainty, or scope deviation. Sol locally verified the cited schema,
service, and test branches and accepted the bounded result.

## Rollback

Database-copy rollback:

```powershell
cd backend
poetry run alembic downgrade 20260730_0001
```

This removes only A2.2 triggers, indexes, and tables in reverse dependency
order. The migration test proves planning and legacy rows remain intact and
SQLite integrity is `ok`.

Git rollback is checkpoint-based:

1. preserve any later dirty work in a new path-preserving recovery package;
2. identify the bounded A2.2 checkpoint by commit message;
3. revert that commit non-destructively;
4. rerun migration-copy, backup/restore, backend, root, and canonical verifier
   gates.

Do not use a destructive hard reset on the authoritative dirty workspace.

## Exit posture

```text
A2_SLICE2_PASS=true
A2_COMPLETE=false
A3_STARTED=false
SCIENTIFIC_RELEASE_BLOCKED=true
```

Remaining A2 work:

1. A2 Slice 3: one-way legacy adapters and closure of dual-write paths without
   deleting legacy tables.
2. A2 Slice 4: thin versioned integration, canonical database
   backup/migration/restore acceptance, and full A2 report.

No held-out sensory observations or human release authorization were created
or inferred in this slice.
