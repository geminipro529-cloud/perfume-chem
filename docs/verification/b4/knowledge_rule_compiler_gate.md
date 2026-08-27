# Build B4 Knowledge-Rule Compiler Gate

Decision: **PASS**

This report independently re-verifies Build B Phase B4 against the current
authoritative checkout. Historical reports and agent claims are notes only;
current executable tests, source and migration constraints, protected state,
frozen inputs, restored artifacts, and the reconciled final audit decide the
gate.

## Authority and scope

- B4 implementation authority:
  `edab5112d69ca34fc96e2af15e7e5ee30f7e34e4` and
  `0b274a4b5ef8648c795e37ebdab1baabc8192b81`.
- Verification head before this report:
  `bc93ebafd105378c06470b2210dedec23d667b93`.
- B4 phase revision: `20260731_0008`.
- Current single repository Alembic head: `20260731_0012`.

This gate covers versioned knowledge-rule compilation and transparent runtime
projection only. Analytical, regulatory, claim, backfill, and production
consumer authority remain B5-B9.

## Implemented canonical contract

- Six append-only tables store versioned rule groups and members, rules,
  contradictions, controlled support evidence, and compilation runs.
- Exact endpoints require canonical identity scope; groups require explicit,
  versioned membership. Generic prose and unresolved references may be
  explanatory or advisory but cannot become authoritative, blocking, or
  numerical.
- Database checks require every authoritative rule or group to carry exact
  source-version, extraction, locator, and approved-review provenance.
- Only authoritative rules can block. Numerical interaction models require
  controlled evidence matching identity, matrix, and dose domains.
- Stable diagnostics retain invalid and duplicate inventory, label only edges
  inside cyclic strongly connected components, reject null required digests,
  and expose status, source, scope, uncertainty, contradictions, and role.
- Migration imports zero legacy rows, and no production consumer is connected
  before B9.

## Frozen corpus regression

The frozen corpus fixture contains 3,381 records, an invalid-exact ceiling of
137, 68 duplicates, one cycle diagnostic, zero blocking rules, and zero
numerical models. Its SHA-256 is
`6249FC3E6DE3EB50AE753064E741FF68257FFE5A4E446758D479253F805DA6C5`.

The identity-resolution fixture contains 454 case-sensitive raw labels and has
SHA-256
`51D4A70EE763A2DB3EA97FC86B658599A77D5C8DBE61ADFD310D14627B909014`.
It explicitly declares
`REGRESSION_FIXTURE_ONLY_NOT_CANONICAL_IDENTITY_AUTHORITY`; it is not a
runtime registry and cannot confer authority.

The host PowerShell JSON parser was rejected for label counting because it
collapses case-variant keys. A standards-compliant Node JSON parser reproduced
the 454-label count and all frozen scalar values without modifying either
fixture.

## Current deterministic verification

All commands ran non-interactively under supported Python 3.11.15 with ANSI
disabled, explicit timeouts, external writable temp/cache state, and separate
stdout/stderr logs under `docs/verification/b4/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr |
|---|---:|---|---|
| B1+B2+B3+B4+compatibility pytest | 129 passed in 175.10 s | `924DE992...1BBC6` | empty |
| Ruff, exact B4 paths | all checks passed | `82B3E6A6...B4F18` | empty |
| Mypy, four B4 modules | no issues | `D9A5631F...7BB76` | empty |

The cumulative suite includes B1-B4 schemas and services, all four phase
migrations, current-head migration coverage, downgrade/re-upgrade behavior,
and backup/restore. Every accepted command exited zero and current logs contain
no ANSI sequences.

## Protected database and migration state

| Database | Bytes | SHA-256 before and after | `quick_check` | Alembic rows |
|---|---:|---|---|---:|
| `perfume_chem.db` | 12,288 | `02B64BE8...0DA5E` | `ok` | 0 |
| `data/perfumery_kb.db` | 2,084,864 | `5A779F9D...63FE1` | `ok` | 0 |

Both databases were inspected through immutable read-only SQLite connections;
their hashes were unchanged by this gate. The B4 phase revision is
intentionally distinguished from current linear head `20260731_0012`.

## DeepLuna boundary and reconciliation

- Route is Fast-only `FLASH` with `NO_LUNA`; Codex subagents used: zero.
- Fresh exact-project health was `READY` on CANDIDATE_V2/release 0.9.9 with no
  active or queued work and zero reserved or unknown accounting.
- Gap audit `DS-16dbed00c38fe1ce3ca29a2998dbaf99` returned
  PASS / POSITIVE / ACCEPTED with no negative finding or scope deviation.
- The first fixture-audit contract was rejected locally because its packed
  estimate exceeded its explicit 18,000-token ceiling. It made zero provider
  calls, spent zero, and is not gate evidence.
- Corrected bounded fixture audit
  `DS-b24c046e14cf4ba43d64b5eb4be310c2` returned
  PASS / POSITIVE / ACCEPTED with one Fast call, no negative finding, and no
  scope deviation. Sol independently reproduced its fixture values and test
  mapping.
- Historical Fast PASS packets remain supplemental; one missed three defects
  later reproduced and fixed by Sol.

Final report audit `DS-9de010f25661d420054ba2b48ff25344` returned
PASS / POSITIVE / ACCEPTED with one Fast call, no cache hit, no negative
finding, no scope deviation, and no required report correction. Sol reconciled
the packet against current logs, source constraints, frozen fixtures,
migration state, protected databases, and hashes. The normalized receipt is
`docs/verification/b4/logs/deepluna-final-audit.json`, SHA-256
`BCEED79BB07CD34DD967D3F52A9867FCD9A9470255AC43B8A94988EDBD956FED`.

## Recovery and dirty-work preservation

The complete prior B4 report/log tree is preserved at
`outputs/b4-authoritative-recovery/20260802T071809/b4-evidence-before-refresh.zip`,
SHA-256 `A146B04D5DA1FF6C31EE4FEEB0E720FD4FBADE7EAE2BDA917CCEFF36E58F56D8`.
The archive contains all eight files; separate extraction reproduced every
path and SHA-256 exactly.

Before report editing, 105 tracked paths were dirty, 1,229 files were
untracked, and zero entries were staged. No cleanup, reset, database mutation,
or unrelated edit was performed.

## Exit decision and claim boundary

The local B4 gate is green: exact rules resolve only to canonical identities or
explicit groups; generic, unresolved, invalid, and advisory records cannot
silently block or mutate a formula; numerical interaction promotion requires
controlled matching evidence; frozen corpus regression is deterministic; and
protected databases remain unchanged.

Final B4 decision is **PASS**. Scientific release remains **BLOCKED**. B5 may
begin only after the exact B4 evidence set is committed without unrelated
paths.
