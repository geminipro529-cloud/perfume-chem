# Build A Phase A2 authoritative exit gate

Date: 2026-08-02

Status: implementation, repository, and bounded Fast gates PASS; final closure
is made immutable by the bounded checkpoint described below.

Authority is the current `D:\chatbots\perfume-chem` tree, the A0 ADR, the A2
master requirements, executable tests, Alembic, SQLAlchemy metadata, and the
canonical project verifier. The earlier report's 1,000/272 counts and
`20260730_0003` head statement were historical and are superseded here.

## Baseline and recovery

- Starting checkpoint:
  `9f14fe923625a076030e5253b0d35a8b1a108efa`.
- Prior A2 implementation commits `7e0dc59` and `3e012f2` were treated as
  hypotheses and independently rechecked against the live tree.
- A2 pre-edit archive:
  `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\a2_preedit_20260802_035345.tar`.
- Archive SHA-256:
  `9f1cd8f613832426b773496779fce6ee1bf889ead608577f688f03ae6527398e`.
- Recovery verification: five path-preserved affected files restored with
  zero length or SHA-256 mismatches.
- The pre-A2 full-verifier report and five JUnit files were separately archived
  before regeneration at `a2_pre_full_verifier_20260802_040056.tar`, SHA-256
  `8daea8bb1fa90cee8b7fb5c873ad0517e3e879d787258708df704e99b860f31d`,
  with six of six restored files matching.

## Fresh A2 baseline and reproduced gap

All 19 `test_a2_*.py` files initially passed 82 tests under the repository
Poetry/Python 3.11 environment. JUnit SHA-256:
`ba0597fbe4d59765636f29639102a13a4afd3d31d7f004c27aa6e2c28503c280`.

The baseline was not accepted as complete because
`add_material_alias` still constructed `LabMaterialAlias` and directly called
`session.add`, `session.commit`, and `session.refresh`. That was the exact A0
ADR exception to the endpoint -> `LabService` -> `LabRepository` write rule.
The compatibility test checked HTTP behavior but not transaction ownership.

Bounded read-only DeepLuna Fast job
`DS-8b881df2226af08f61df46bd57d38317` confirmed only this mechanical
discrepancy. Sol independently read the complete service and repository and
confirmed that no alias-write service method existed. Two earlier oversized
audit envelopes terminalized locally before provider transmission and were not
used as evidence.

## RED/GREEN sequence

| Stage | Result | Evidence |
|---|---:|---|
| New endpoint-transaction guard contract before scanner change | 3 passed, 1 failed | Expected empty violation list instead of five `ENDPOINT_TRANSACTION_CALL` records; JUnit SHA-256 `cc300ccae751dccf6829f3ae57015bf9afa7951546a1f383397700279ee2f744` |
| Guard implemented against live tree before route fix | 3 passed, 1 failed | Live scanner found `session.add`, `session.commit`, and `session.refresh` at the alias route; JUnit SHA-256 `343057a202f6818fe6eeacea4e9eee7d4a537eb0bed89ed0d3cdfc7b18aa1e0c` |
| First focused implementation run | 8 passed, 2 failed | Removing the model import broke read-only alias resolution; the import was restored without changing the service-routed write |
| Final guard plus material lifecycle | 10 passed | JUnit SHA-256 `49855f89310917b7345e4d6f8ab51870415e1dfef0fa1bb90149e2cf51325c0b` |
| Final 19-file A2 suite | 83 passed | JUnit SHA-256 `65e7aba643b27c0e20a235db53eae72c1bbed79c80e7996328e8e5d58a76a433` |

The minimal source change adds `LabService.create_material_alias`, validates a
nonempty alias, checks material existence inside `_transaction`, and persists
through `LabRepository.add`. The existing v1 URL, 201 status, response payload,
and alias-resolution behavior are preserved. The AST guard now rejects direct
endpoint calls to `session`/`db` `add`, `flush`, `commit`, `refresh`, or
`rollback`. No model, schema, migration, or database file changed.

## A2 contract disposition

| Contract | Current authoritative evidence | Result |
|---|---|---:|
| A2.1 canonical objects | A0 ADR maps each overlapping domain to Laboratory Beta SQLAlchemy authority. Engine ledgers reject public mutation and hydrate only as read projections. | PASS |
| A2.2 canonical build-plan layer | Runtime SQLAlchemy metadata exposes all eight required statuses; the version header and line tables contain stable/versioned identities, target/acceptance links, hashes, provenance, inventory snapshot, quantities/bases, density, uncertainty, measurement, loss, substitution/function, rationale, reservation, and execution fields. Evidence links are a separate constrained table. | PASS |
| A2.3 lifecycle graph | Planning and lifecycle services persist explicit target, acceptance, mapping, plan, reservation, proposal, confirmation, measurement, commit, bottle replay, analytical, sensory, regulatory, and release-review references. Prior records are immutable/append-only. | PASS |
| A2.4 one-way legacy adapters | Legacy bottle, inventory, analytical, sensory, and evidence mutators raise stable `LEGACY_WRITE_PROHIBITED`; adapters remain read-only. The live scanner returns zero prohibited paths after the alias repair. | PASS |
| A2.5 migrations | `poetry run alembic heads` returns the single current head `20260731_0012`. A2 migration tests cover empty/current and representative-copy upgrade, downgrade/re-upgrade, constraints, append-only triggers, rollback, backup/restore, and export/import through the current chain. | PASS |
| A2.6 workbench/API integration | Existing `/api/v1/lab/*` compatibility remains. Twenty introspected v2 planning/lifecycle operations cover every named A2 operation with thin service calls and stable domain error handling. | PASS |

Target hypothesis, accepted target, inventory mapping, and build plan remain
independent immutable records connected by foreign keys; no dual persistence
write remains.

## Verification evidence

- Fresh Alembic-head stdout SHA-256:
  `5fcf196b72fe87a1e67189933e7b91d4e46c1ee04cba6ff43a63bb40398d969d`;
  stderr was empty.
- Backend Ruff: all checks passed.
- Backend mypy: no issues in 116 source files.
- Canonical command:
  `.venv_py311_a0\Scripts\python.exe scripts\pipeline_audit.py project-verify --json`.
- Duration: 668 seconds; stderr empty.
- Canonical stdout/report SHA-256:
  `732e4883a59861de6e3241ec6ea8c63c856bfcbab30e268e6717c1936225d04b`.
- Completion gate: `PASS_WITH_SKIPS`, full scope, 19 PASS, 0 FAIL, 2 Docker
  skips, 0 omitted.

| Executable set | Tests | Failures | Errors | Skips |
|---|---:|---:|---:|---:|
| engine truth core | 189 | 0 | 0 | 0 |
| engine data/knowledge | 235 | 0 | 0 | 0 |
| engine gates/families | 602 | 0 | 0 | 0 |
| engine legacy | 69 | 0 | 0 | 0 |
| **engine total** | **1,095** | **0** | **0** | **0** |
| backend complete | 630 | 0 | 0 | 0 |
| **combined** | **1,725** | **0** | **0** | **0** |

## Final DeepLuna Fast validation

After a fresh exact-project `READY` preflight for `project_id=perfume-chem`,
read-only job `DS-5dbc129197c7b763f5f5427517b5a628` audited this current
report against the plan, alias endpoint/service delta, AST guard and regression
test, and canonical verifier JSON.

- route: `FLASH` only, one provider call, `NO_LUNA`, no alternate provider;
- terminal status: `PASS` / `POSITIVE` / `ACCEPTED`;
- contradictions or unsupported claims: none;
- count reconciliation: 19 required checks passed, 2 Docker skips, and 1,725
  combined executable tests;
- service-boundary reconciliation: alias writes route through
  `LabService.create_material_alias`, and the scanner covers direct endpoint
  transaction calls;
- scope deviation: false.

Sol independently re-read the supplied ranges, parsed the verifier and JUnit
artifacts, and accepted this mechanical result. DeepLuna did not grant A2
acceptance.

## Exit decision

All A2 exit requirements are PASS. The checkpoint commit containing only the
A2 plan, report, guard, service, endpoint, and regression test is the external
immutable gate identifier. Generated verification logs and unrelated dirty
work are excluded from that commit and preserved in place.

This gate does not promote scientific or commercial release; held-out sensory
validation remains independent.
