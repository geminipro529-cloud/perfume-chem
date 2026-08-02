# Build B6 regulatory authority gate

Status: **PASS**

Recorded: 2026-08-02 (Asia/Bangkok)

Branch: `codex/add-inventory-materials`

Implementation commit: `26137df654b8f2fdb729280678fd8c1ef2355eb0`

Verification checkpoint before this report:
`2e5724fe1075498477e22e2a6657ecc264c570c2`

## Current outcome

The local B6 gate, bounded final report audit, and Sol postflight are green.
The exact B6 evidence commit remains the seal required before B7 begins.

B6 is an append-only, dated, jurisdiction-, product-, use-, formula-,
concentration-basis-, natural-assumption-, source-version-, and
evaluation-date-scoped regulatory screening authority. Its exact result
vocabulary is:

- `PASS_FOR_DECLARED_SCOPE`
- `FAIL`
- `UNKNOWN`
- `NOT_EVALUATED`

Only `PASS_FOR_DECLARED_SCOPE` receives service-generated scoped wording.
Nothing in B6 is legal advice, an IFRA certificate, or a certificate of legal
conformity. Legacy A2 `PASS` rows remain historical context and do not become
B6 authority without a linked passing B6 snapshot.

## Authority and fail-closed behavior

The additive migration `20260731_0010` creates seven empty append-only tables
for official source versions, rule versions, exact supplier-document bindings,
composition profiles and entries, immutable snapshots, and per-rule findings.
It imports or promotes zero legacy rows.

Executable tests verify that B6:

- distinguishes current, future, draft, consultation, watchlist, superseded,
  and not-yet-applicable records;
- never enforces draft, consultation, watchlist, superseded, or future rules;
- evaluates action-specific placement and availability transition dates;
- binds supplier evidence to exact supplier, product, code, grade, document
  version, and lot scope;
- accepts only complete, current, scope-matching regulatory composition data;
- returns `UNKNOWN` for missing, partial, stale, or unknown natural
  composition;
- preserves a known over-limit `FAIL` even when other composition is unknown;
- emits scoped wording only for `PASS_FOR_DECLARED_SCOPE`; and
- refuses to promote a legacy A2 pass into B6 authority.

## Current official-source observations

Official primary sources were checked on 2026-08-02:

- IFRA reports that the 52nd Amendment consultation closed on 2026-06-12 and
  that formal Notification was expected near the end of November 2026. It is
  therefore recorded as `CONSULTATION`, not an enforced published amendment:
  <https://ifrafragrance.org/latest-updates/ifra-news/ifra-52nd-amendment-consultation-closed>
- IFRA's Standards page still identifies the 51st Amendment as the latest
  formally published amendment. It also distinguishes the voluntary IFRA
  product-stewardship system from law and explains the mixture-manufacturer
  scope of an IFRA certificate:
  <https://ifrafragrance.org/initiatives-positions/safe-use-fragrance-science/ifra-standards>
- Regulation (EU) 2023/1545 states 0.001% leave-on and 0.01% rinse-off
  declaration thresholds. Its transition permitted placement on the Union
  market through 2026-07-31 and permits making available through 2028-07-31.
  On 2026-08-02, the placement transition has ended while the availability
  transition remains active:
  <https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng>

These are dated screening inputs, not a legal opinion. A later evaluation must
refresh current-source state instead of silently reusing this observation.

## Current executable evidence

Supported runtime and repository migration state:

- Python `3.11.15`
- Node `v26.3.0`
- phase revision `20260731_0010`
- single current Alembic head `20260731_0012`
- non-PTY execution, ANSI disabled, explicit timeouts, and separate stdout and
  stderr captures

Focused B6 gate:

```text
30 passed in 86.61s (0:01:26)
```

The focused command covered the B6 schema, service, migration, and end-to-end
test files. Exit code was `0`; stderr is empty.

Cumulative A2 plus B1-B6 compatibility, migration, and backup/restore gate:

```text
266 passed in 469.43s (0:07:49)
```

Exit code was `0`; stderr is empty.

Static gates:

- Ruff exact B6/shared-registration scope: `All checks passed!`, exit `0`
- mypy B6 model/repository/service: `Success: no issues found in 3 source
  files`, exit `0`

The accepted logs are stored under `docs/verification/b6/logs/` as UTF-8
without BOM. Their original PowerShell captures remain outside the repository,
and report hashes bind every accepted stream.

## Migration and database proof

Executable tests cover prior-head upgrade, seven empty B6 tables, constraints,
foreign keys, indexes, append-only guards, downgrade/re-upgrade, current-head
tracking, and backup/restore. Current repository migration state is the later
linear head `20260731_0012`; B6 remains revision `20260731_0010` in that chain.

Both protected databases were inspected read-only and remained byte-identical
before and after the B6 gate:

| Path | Bytes | SHA-256 | Integrity |
|---|---:|---|---|
| `perfume_chem.db` | 12288 | `02B64BE88E4A8881C968EC9EF7F0185ED7B1BCEDC6ED33885F07D7DE70A0DA5E` | `quick_check=ok`; no Alembic rows |
| `data/perfumery_kb.db` | 2084864 | `5A779F9D6850345D72DE3C8265D4330C50DAC529968B38BC9B08720B5DA63FE1` | immutable read-only `quick_check=ok`; no Alembic rows |

No migration was applied to either protected database.

## Recovery and worktree preservation

The complete prior B6 report/log tree was archived before refresh:

`outputs/b6-authoritative-recovery/20260802T081549/b6-evidence-before-refresh.zip`

- bytes: `11930`
- SHA-256:
  `50A9CA495AA67C489E78D5D283705C0A1ADBA6A9C65D9081DB56ED4A099A6486`
- path-preserving files: `18`
- unsafe archive members: `0`
- restore verification: `18/18` extracted files matched archived SHA-256

Before the report edit, the preserved overlay had 107 tracked dirty paths,
1,281 untracked files, and zero staged entries. No cleanup, reset, migration,
artifact regeneration, or production-code edit was performed for this B6
reverification. The eight phase-owned B6 implementation/test paths have no
delta from implementation commit `26137df`.

## DeepLuna use and authority boundary

A fresh exact-project check returned `READY` for `perfume-chem`, runtime
`CANDIDATE_V2`, release `0.9.9`, with zero active reads/writes, an empty queue,
zero open or unknown reservations, and provider calls enabled.

The bounded gap audit `DS-ac4f843d8d218582d5744da72f374f6e` returned
`PASS/POSITIVE/ACCEPTED` through Fast-only `FLASH` with `NO_LUNA`. Sol
independently reproduced the tests, hashes, migration state, protected database
state, and current official-source observations.

A later resume audit, `DS-785c7ddcfb833884a770173a6e102cb7`, was rejected
locally before provider transmission because 36,058 estimated input tokens
exceeded its 18,000-token cap. It made zero provider calls, spent zero, and is
excluded from gate evidence; there was no retry or fallback.

The final report audit `DS-9008c70e11660085e9fe922c986cc9f5`
returned `PASS/POSITIVE/ACCEPTED` with one Fast provider call, no negative
findings, no scope deviation, and no required correction. Its measured usage
was 13,492 prompt tokens, 709 completion tokens, and 2,012,850 nano-USD. The
redacted receipt is `docs/verification/b6/logs/deepluna-final-audit.json`
(1,556 bytes; SHA-256
`BE34D87E3CB2D2929B38D07B97462F463C2A5A4C26F7D5F566DA7D6FCE775F9B`).

A fresh post-provider check again returned exact-project `READY` with zero
active reads/writes, an empty queue, and zero open or unknown reservations.
DeepLuna remains supplemental: Sol retains legal interpretation, architecture,
provenance, safety, scope, and final acceptance.

## Exit gate

The B6 evidence package passes its substantive exit gate:

1. fresh exact-project DeepLuna preflight and postflight are `READY`;
2. the bounded Fast-only report audit returned accepted positive evidence;
3. Sol reproduced every worker finding locally;
4. focused, cumulative, lint, typing, migration, database, report, log, source,
   and archive checks pass; and
5. no production code or protected database changed during reverification.

The exact B6 evidence paths must now be committed with no unrelated staging.
B7 must not begin before that seal commit exists.
