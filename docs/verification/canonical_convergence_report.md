# Build A canonical convergence report

Date: 2026-08-02

Build: A - Canonical convergence and reconstruction hardening

Decision: **PASS_WITH_SKIPS**

Product status: **Laboratory Beta**

Scientific release: **BLOCKED**

## Authority and tested state

This report independently reconciles the actual
`D:\chatbots\perfume-chem` repository. Historical project, GLM, and earlier
Build A reports were treated as leads only. Acceptance is based on the current
repository, executable tests, migration structure, database constraints,
artifact verification, recovery proof, and collected evidence.

| Field | Authoritative value |
|---|---|
| A0 baseline SHA | `0fa0adff1533ffca1ad74e6e6904b1afc1b1d435` |
| final tested source SHA | `f6ba7c3bf5a4a644b5ac03fc09fd447b67247f4d` |
| branch | `codex/add-inventory-materials` |
| upstream | `origin/codex/add-inventory-materials` |
| local divergence | ahead 90, behind 0 |
| committed Build A paths | 29, including these two final reports |
| preserved post-report worktree | 104 unrelated tracked changes, 1,075 non-ignored untracked paths, 0 staged paths |

The tested state is the final source SHA plus the preserved dirty overlay.
Neither the SHA alone nor a clean checkout represents all files exercised by
the verifier. No worktree cleanup, reset, migration, artifact rebinding, or
secret-file inspection was performed.

## Recovery and rollback

The A0 path-preserving recovery package remains the rollback authority:

- complete source archive: 4,366 files, SHA-256
  `4b1a4c325d1d69c5d54535b6ad14acda9872698c8bf00f9847753c0bdadb223b`;
- source manifest SHA-256
  `8e05bf58670d2bdb452c16961e0c78cb8b270d5479274463294535111e2f606a`;
- all-refs Git bundle SHA-256
  `4d10101200fa321a1f44923f989c62ec35814fcc6ab8100d8b1504dfa89506ef`;
- formula/fixture archive: 535 artifacts, zero mismatches, SHA-256
  `e58681bf79e34677d17c341d08701d9444dc2e3ac52c7e793eab7c5bb5b2772c`;
- proven clean restore: `C:\A0S_full_20260801_011431`, zero source or
  restore mismatches.

Restoration instructions are in
`docs/verification/a0_restoration_instructions_2026-08-01.md`. Ignored
secret-bearing files were excluded and never opened.

Every subsequently edited tracked evidence or source set was also archived
outside Git and restore-verified. The final pre-report archive is
`a6_pre_final_reports_20260802_045811.tar`, SHA-256
`5238cc7f1710f71acc3a957d99b52e5dbaf71706fca410afbdce63fb8cdca952`,
with three of three restored files matching. The pre-ANSI-fix source/report
archive is `a6_pre_ansi_fix_20260802_051831.tar`, SHA-256
`dbd38350bec18169b1ba2223e08d74368b9475358626914d7062310d04ad4625`,
also with zero mismatches.

Rollback means restoring into a new directory from the A0 bundle/archive, then
applying only explicitly selected Build A commits. An active database must be
validated, staged, and restored in maintenance mode; it must never be blindly
overwritten.

## Canonical architecture and truth path

The one persisted Laboratory Beta path is:

1. immutable evidence/source records;
2. explicit identity resolution, independent of stock availability;
3. immutable target hypothesis and accepted target version;
4. immutable inventory mapping and measurable build-plan version;
5. append-only inventory reservation;
6. software proposal, human confirmation, and measured action;
7. one transaction committing bottle event and inventory movement;
8. deterministic bottle and stock replay projections;
9. claim-specific analytical, sensory, regulatory, and release assessments;
10. reports and artifacts as bound projections, never canonical records.

Canonical persisted models, repositories, and transaction-owning services live
under `backend/app/models`, `backend/app/repositories`, and
`backend/app/services`. Engine records are typed calculation, gating, and replay
domains. The ADR and import/call/persistence graph assign each legacy or
duplicate surface a disposition. The endpoint transaction scanner and legacy
write-closure tests report zero violations; adapters remain one-way and cannot
own canonical writes.

Target, inventory mapping, build plan, reservation, bottle event, and inventory
movement remain separate records. AI may propose but cannot confirm physical
execution or self-release.

## Six original defects

| ID | Reproduction | Disposition | Fix and executable evidence |
|---|---|---|---|
| A1.1 diluent-aware concentration | Reproduced inactive-stock category loss and misclassification. | **FIXED** | Active, carrier, ethanol, water, other solvent, and unallocated quantities conserve exactly; A1 and canonical-quantity tests pass. |
| A1.2 target-row preservation | Reproduced incomplete all-field and unknown-field contracts. | **FIXED** | Typed rows preserve every accepted field; strict unknowns reject and namespaced extensions round-trip. |
| A1.3 twelve-axis anti-compression | Reproduced boolean/missing-evidence compression. | **FIXED** | Twelve independent `MATCH`/`DIFFER`/`UNKNOWN` axes and scoped equivalence prevent unsupported merging. |
| A1.4 chained correction replay | Reproduced missing-reference, cross-stream, cycle, and stale-sequence gaps. | **FIXED** | Immutable correction chains reject invalid references/cycles/conflicts and deterministically trace latest replacement to original. |
| A1.5 empty reconstruction inputs | Reproduced empty rosters, empty uncertainty targets, and zero normalization acceptance. | **FIXED** | Public entry points and quantity reconciliation raise stable `ReconstructionInputError` before mathematical normalization. |
| A1.6 identity versus inventory | Reproduced conflated identity and stock statuses. | **FIXED** | Independent typed identity and availability decisions preserve ambiguity, substitutions, and no-stock states. |

The final A1 pair passes 97 contracts. A2 closes the last independently
reproduced endpoint-owned write: the material-alias route now delegates to
`LabService`, while an AST guard rejects endpoint `add`, `flush`, `commit`,
`refresh`, and `rollback` calls. The full A2 suite passes 83 tests.

A3, A4, and A5 production implementations already existed in the A0 tree and
were not assumed correct. Fresh focused tests, source inspection, database
checks, and bounded Fast audits independently accepted typed serialization,
quantities/hashing/provenance/artifact binding; eleven mode and claim gates;
and atomic bottle/inventory operations. Their current evidence is in
`a3_exit_gate.md`, `a4_exit_gate.md`, and `a5_exit_gate.md`.

## Independent diff review

The committed Build A range plus these reports contains 29 paths: 4 backend, 4
engine, 3 test, and 18 architecture/plan/evidence files. Every path was
enumerated and reviewed.

- no changed file exceeds 1 MiB;
- high-confidence added-line secret scan found zero matches;
- ignored environment and credential files were never opened;
- no duplicate SQLAlchemy `__tablename__` value exists;
- no forbidden shallow `cls(**filtered)` deserialization path exists;
- no endpoint-owned transaction call remains;
- six legacy-write guard/closure tests pass;
- changed assertions strengthen missing contracts or preserve complete row
  equality; no expected value was merely changed to mirror output;
- public legacy and versioned Laboratory Beta API surfaces remain in the full
  backend/API suite;
- no release artifact or golden fixture was regenerated;
- source and phase-report claims reconcile with live tests and database state.

Alembic has one linear 14-revision chain, no branch, and head
`20260731_0012`. Every revision defines both `upgrade()` and `downgrade()`.
This authoritative Build A run created no migration and did not migrate the
default root database. Later Build B-named revisions were already present at
A0 and receive no scientific promotion from this Build A decision.

## Risk-based coverage

All A6 categories map to executable tests in the canonical shards/backend
suite: the six original defects; quantity conservation; unit conversion;
typed/versioned serialization; canonical hash stability; migration
upgrade/downgrade; event state machines; seeded correction chains and cycles;
concurrency and rollback; API contracts; report/artifact projection;
backup/restore/export/import; target-to-bottle lifecycle; and negative claim
gates. The JSON companion records representative test files for each category.

## Final canonical verifier

Command: supported Python 3.11.15 running
`scripts/pipeline_audit.py project-verify --json` without a PTY, with separate
stdout/stderr capture and an explicit 30-minute timeout.

Final machine report: `verification_runs/project_verification.json`

| Evidence | Result |
|---|---|
| completion gate | `PASS_WITH_SKIPS` |
| required checks | 19 passed, 0 failed, 0 omitted |
| optional checks | Docker build and smoke skipped because not requested |
| engine shards | 190 truth-core + 235 data/knowledge + 602 gates/families + 69 legacy = 1,096 |
| backend suite | 630 passed |
| combined canonical tests | 1,726 passed |
| engine/backend Ruff | PASS |
| engine/backend MyPy | 33 / 116 source files, PASS |
| scientific audit | 22 passed |
| material validation | 80 passed |
| knowledge rules | 77 passed |
| golden formula/API | 13 passed / 1 passed with 8 deselected |
| package build/wheel smoke | PASS / PASS |
| artifact validation | PASS with non-promoting warnings detailed below |
| golden fixture lock | PASS, `0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec` |
| elapsed | 823.2 seconds |
| report SHA-256 | `030046c26417dd23cb3208e0a46224d9a052bc75263ccd9b59fc63f3099d2350` |
| stdout SHA-256 | `7e4f05d2c48a1565ef974845e0e9ec308d8020ca7d384c58b2b6acadccf569df` |
| stderr | empty, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| ANSI markers | zero in report, stdout, and stderr |

The first A6 full run passed but exposed escaped Ruff color codes inside its
JSON evidence. A new regression test failed as expected, both Ruff commands
were given explicit `--color never`, 16 verifier tests plus Ruff and exact MyPy
passed, and the complete verifier was rerun. Only the ANSI-clean second run is
final authority.

The current artifact verifier exits 0 with status `WARN`: 452 `NONE`, 14
explicitly `QUARANTINED`, 49 `UNBOUND_LEGACY`, and zero blocking unquarantined
`STALE` or `TAMPERED` files. Its JSON SHA-256 is
`3e5eadb78c598d2c751ce8a7fa8919f3be26a2da7afc7cd5874c8f0ef6247e2d`;
stderr is empty. A passing artifact check does not promote quarantined or
legacy-unbound output.

## Protected database state

After the final verifier, both files are byte-identical to the pre-A6 state and
pass read-only SQLite `PRAGMA quick_check`:

- `data/perfumery_kb.db`: 2,084,864 bytes, SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`;
- `perfume_chem.db`: 12,288 bytes, SHA-256
  `02b64be88e4a8881c968ec9ef7f0185ed7b1bcedc6ed33885f07d7de70a0da5e`.

The default root database contains only an empty `alembic_version` table. It is
an observed backed-up pre-startup state, not migration authority. No migration
was applied.

## Acceptance matrix

| Gate | Decision |
|---|---|
| A0 recoverable authoritative baseline | PASS |
| A1 six executable reconstruction contracts | PASS |
| A2 canonical persistence and migration boundary | PASS |
| A3 serialization, quantity, hash, provenance, artifact binding | PASS |
| A4 operating modes and claim/action gates | PASS |
| A5 bottle and inventory operations | PASS |
| A6 independent review and canonical verification | PASS_WITH_SKIPS |
| Laboratory Beta software status | READY |
| scientific/product release | BLOCKED |

## Limitations and deprecated paths

- Docker build/smoke were not requested in the canonical command; they are the
  only skipped checks.
- Held-out sensory validation has not passed. Scientific/product release,
  certification, blanket similarity, and preference claims remain blocked.
- The root application database is intentionally unmigrated; startup migration
  and any restore require the documented safety workflow.
- Artifact `WARN`, quarantine, and legacy-unbound states are non-promoting.
- Legacy adapters and compatibility fields are projections only. They cannot
  own writes or outrank canonical replay.
- Existing Build B/C/D-named code, migrations, reports, or historical claims in
  the A0 overlay are not accepted by Build A and must be independently
  reverified in strict order.
- The dirty overlay remains necessary to reproduce the tested state and is
  preserved rather than absorbed or cleaned.

## DeepLuna Fast final audit

A fresh exact-project check returned `READY` for `project_id=perfume-chem`,
runtime `CANDIDATE_V2`, server 0.9.9, with no active, queued, open-reserved, or
unknown-reserved work. Bounded read-only final audit job
`DS-d3c82263dd3cea7cb6496005b9022604` used route `FLASH`, fallback policy
`NO_LUNA`, and one allowed provider call.

The job returned `PASS`, execution status `ACCEPTED`, and evidence verdict
`POSITIVE`, with no negative findings, scope deviation, architecture
uncertainty, or acceptance-blocking gap. It reconciled the Markdown report,
JSON report, A0 recovery evidence, machine verifier, and ANSI regression
contract. Its residual risks were exactly the three already declared here:
optional Docker skips, missing held-out sensory validation, and non-promoting
artifact warnings. DeepLuna supplied bounded review evidence only; Sol retained
and exercised final authority.

## Exit decision

Build A satisfies the canonical convergence criteria: recovery is proven; one
persisted truth path and canonical build plan exist; serialization is typed;
legacy dual writes fail closed; target, inventory, build, and bottle remain
separate; physical writes are atomic and replayable; critical gates fail
closed; artifacts are bound; and every known limitation is explicit.

Build A remains **Laboratory Beta**. Scientific release remains **BLOCKED**.
This report is sealed and must now be presented at the Build A boundary. No
Build B work begins in this run.
