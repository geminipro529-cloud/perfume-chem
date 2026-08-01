# A0 authoritative baseline - 2026-08-01

Status: **A0 EXIT GATE PASS**. This document supersedes the historical 2026-07-29 A0 reports. It records the working tree as found; it does not claim that the earlier reports were correct.

## Repository identity

| Field | Current evidence |
|---|---|
| Repository root | `D:\chatbots\perfume-chem` |
| Remote | `https://github.com/geminipro529-cloud/perfume-chem.git` |
| Branch | `codex/add-inventory-materials` |
| HEAD / exact A1 starting SHA | `0fa0adff1533ffca1ad74e6e6904b1afc1b1d435` |
| Upstream | `origin/codex/add-inventory-materials` |
| Divergence | ahead 84, behind 0 |
| Worktrees | one: `D:/chatbots/perfume-chem` |
| Porcelain-v2 state | 105 unstaged tracked paths, 0 staged paths, 937 individual non-ignored untracked paths |

The machine capture contains the full porcelain-v2 output, diff statistics, binary paths, recent commits, submodule state, ignored-path counts, lock digests, verifier configuration, and shard manifest. Sensitive environment values were never recorded. Ignored secret-bearing files, including `.env`, were not opened or archived.

## Supported runtime and locks

The gate ran under Python 3.11.15 at `D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe`. Root `pyproject.toml` requires Python 3.11 or newer and the backend Poetry project requires Python 3.11. Poetry was 2.4.1, Node 26.3.0, npm 11.16.0, and Git 2.54.0.windows.1.

The pre-existing Python 3.14 environment is not accepted as baseline evidence because its mypy launcher fails on `librt.internal`. The supported 3.11 environment resolves that tooling defect without weakening checks.

Lock digests are retained in the machine capture. In particular, `backend/poetry.lock` is `f48137c28c52f7a24f11b6186ce3b4e9a3b161b6f6b570db7e2b56b30de41ffd` and `package-lock.json` is `38a0bd7c215848b671711ad985d06f927ed1969ba781e9c56521d94c104daffc`.

## Recovery proof

The original partial archive is retained as historical evidence, but it is not used as the final recovery authority. The final source package contains every Git-tracked file plus every non-ignored untracked file as raw bytes.

| Evidence | Result |
|---|---|
| Complete source archive | 4,366 files, SHA-256 `4b1a4c325d1d69c5d54535b6ad14acda9872698c8bf00f9847753c0bdadb223b` |
| Source manifest | SHA-256 `8e05bf58670d2bdb452c16961e0c78cb8b270d5479274463294535111e2f606a` |
| All-refs Git bundle | complete history, 17 refs, SHA-256 `4d10101200fa321a1f44923f989c62ec35814fcc6ab8100d8b1504dfa89506ef` |
| Clean restore | `C:\A0S_full_20260801_011431`, 0 source mismatches, 0 restore mismatches |
| Binary tracked diff | source and restore SHA-256 `0f0c17c7786c83cd7f0ee89370b3127c4175deca29aa9c28e49be3fe0598cc8d` |
| Formula/fixture archive | 535 artifacts, 0 mismatches, SHA-256 `e58681bf79e34677d17c341d08701d9444dc2e3ac52c7e793eab7c5bb5b2772c` |
| SQLite backups | four current databases, all `PRAGMA quick_check=ok`, source/backup metadata equal |

The clean restore reports more transient modified paths than the source because global `core.autocrlf=true` causes the clone to revalidate LF files while the source index retains stat-cache entries. This is not treated as content equality. Raw-byte manifests, tracked/untracked path lists, HEAD, and byte-captured `git diff --binary --full-index` are equal.

Restoration instructions are in `docs/verification/a0_restoration_instructions_2026-08-01.md`.

## Database and migration state

`DATABASE_URL` was not set. The application default therefore resolves to `D:\chatbots\perfume-chem\perfume_chem.db`. The file passes SQLite integrity checks but has no `alembic_version` row. This is the observed pre-startup state; application lifespan startup would create a safety snapshot and run Alembic to head.

Alembic has one linear 14-revision history, no branches, and head `20260731_0012`. `alembic current` completed with no current revision for the default file. No migration was applied during A0.

Transaction-consistent backups were created for the default application database, `data/perfumery_kb.db`, and both current test database files. Cache contents were not opened. The legacy archived database and cache databases remain covered by source/archive evidence but are not current write authorities.

## Canonical verification

Canonical top-level command:

```powershell
$env:NO_COLOR='1'
$env:TERM='dumb'
$env:PY_COLORS='0'
$env:FORCE_COLOR='0'
$env:PYTHONUTF8='1'
& 'D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe' scripts\pipeline_audit.py project-verify --json
```

The run was noninteractive, had a 30-minute outer timeout, preserved stdout and stderr separately, and completed in 1,172 seconds.

| Result | Count |
|---|---:|
| Passed checks | 19 |
| Failed checks | 0 |
| Skipped checks | 2 |
| Unique JUnit tests | 1,702 |
| JUnit failures/errors/skips | 0 / 0 / 0 |

The JUnit total is 189 truth-core, 235 data-knowledge, 580 gates-families, 69 legacy, and 629 backend tests. Formula-artifact validation and golden-fixture-lock pass. Docker build and smoke are the only skips because the Docker executable is unavailable. The canonical report gate is therefore `PASS_WITH_SKIPS`, while the A0 exit gate is `PASS` because Docker was attempted and infrastructure does not permit it.

Focused runtime/persistence verification adds 35 passing tests over engine packaging, legacy-write closure, planning and lifecycle APIs, bottle/inventory transactions, backup/restore, and planning/science/execution export-import.

The verifier distinguishes software readiness from scientific release: Laboratory Beta is ready, but scientific release remains blocked until held-out sensory validation passes.

## Architecture authority

The runtime probe imports 97 SQLAlchemy tables and resolves 62 Laboratory Beta routes. `PerfumeWorkbench` resolves to `engine.workbench`, the exact addition solver to `engine.bottle_addition.AdditionSolver`, and persistence to `app.services.lab_service.LabService` plus `app.repositories.lab.LabRepository`. The AST legacy dual-write scanner reports zero violations.

The accepted source-of-truth map and duplicate-store dispositions are in `docs/architecture/ADR-2026-08-01-a0-canonical-reconciliation.md`. The import, API, call, event, persistence, report, and legacy-consumer graph is in `docs/architecture/a0_import_call_persistence_graph.md`.

One boundary exception is recorded rather than concealed: `/api/v1/lab/materials/{material_id}/aliases` directly calls `session.add/commit` for `LabMaterialAlias`. It writes the canonical table, so it is not a second store, but it bypasses `LabService` transaction ownership and is an A1 hardening defect.

## Baseline conditions that do not invalidate A0

- `git diff --check` finds pre-existing trailing blank lines in `future_modules/iconic_formulas.py:507` and `future_modules/skin_chemistry.py:402`.
- The default application database is not migrated yet; that state is backed up and recorded.
- Docker is unavailable.
- Historical A0 reports contain stale SHA, migration counts, and verifier counts and are not authoritative.

## A0 exit gate

- [x] Complete raw-byte recovery demonstrated on a clean clone.
- [x] Canonical commands, environment, stdout, stderr, reports, and hashes captured.
- [x] Backend tests completed: 629 passed.
- [x] Canonical top-level verifier completed: 19 passed, 0 failed, 2 infrastructure skips.
- [x] Current databases and all formula/fixture artifacts backed up and restored.
- [x] ADR assigns one canonical source of truth to every required domain and names duplicate stores.
- [x] Import/call/persistence graph captured and runtime-import checked.
- [x] Exact A1 starting SHA recorded: `0fa0adff1533ffca1ad74e6e6904b1afc1b1d435`.
- [x] No production behavior, migration, cleanup, artifact rebinding, or commit performed in A0.

Machine-readable authority: `docs/verification/a0_authoritative_baseline_2026-08-01.json`.
