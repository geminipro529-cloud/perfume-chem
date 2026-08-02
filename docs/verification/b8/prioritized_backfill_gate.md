# Build B8 prioritized scientific-data backfill gate

Status: **PASS**

Recorded: 2026-08-02 (Asia/Bangkok)

Branch: `codex/add-inventory-materials`

Current revalidation baseline and tested source commit:
`428684fa987b673856fd533e2dba617cf0705e6e`

Historical B8 implementation head:
`3cb554f1ab242ec6c517329504867fe5b502ba70`

## Current outcome

The live B8 implementation still satisfies the planning-authority contract in
the current tree. No B8 production-code or migration defect was reproduced, so
this revalidation changes only the deterministic workspace projection and gate
evidence.

B8 ranks scientific-data gaps by decision value using code-owned strict
lexicographic policy: current inventory; active, shipped, or reference formula;
high-dose structure; potent trace use; regulatory or family impact; analytical
standard; natural constituent; and model sensitivity. It records typed signal
links and ten gap requirements while preserving `MISSING`, `UNKNOWN`, `WEAK`,
`CONFLICTED`, `ACCEPTED_SCOPED`, `ACCEPTED_EXACT`, and `NOT_APPLICABLE` as
distinct states.

The dashboard remains stratified by evidence class, property, current
inventory, active formula, chemical family, regulatory impact, and model
sensitivity. There is no overall coverage score.

This is planning authority only. It cannot create B1-B7 evidence authority,
authorize release, provide legal approval or a safety certificate, or prove
real-world performance.

## Persistence and source state

Migration `20260731_0012`, down revision `20260731_0011`, remains the single
Alembic head and defines five empty append-only tables. No protected database
was migrated or backfilled during this revalidation.

All phase-owned files match the digests recorded in the JSON report. The only
phase-file delta since the historical implementation head is the later A2
canonical material-alias write path in `backend/app/services/lab_service.py`
from commit `f941ad8`. It does not change the B8 contract and is covered by the
current cumulative gate.

## Verification evidence

Supported runtime and execution policy:

- Python `3.11.15` from the supported Python 3.11 verification environment;
- Node `v26.3.0`;
- non-PTY execution with `NO_COLOR=1`, `TERM=dumb`, separated stdout/stderr,
  and explicit timeouts; and
- Alembic head `20260731_0012`.

Current results:

- exact B8 schema, policy, migration, and end-to-end suite: `30 passed in
  30.05s`, exit `0`, wrapper `38.69s`;
- deterministic workspace-projection suite: `2 passed in 0.53s`, exit `0`;
- exact 55-file A2-through-B8 compatibility suite: `440 passed in 742.50s`,
  exit `0`, wrapper `752.17s`;
- Ruff: `All checks passed!`, exit `0`, no ANSI output;
- mypy: `Success: no issues found in 3 source files`, exit `0`;
- Alembic: `20260731_0012 (head)`, exit `0`;
- immutable read-only knowledge-database `quick_check`: `ok`; and
- every accepted stderr stream: empty.

The historical compatibility report contained 439 tests. The current count is
440 because commit `f941ad8` added
`test_guard_rejects_endpoint_owned_transaction_calls` to the already-listed
`test_a2_legacy_write_guard.py`; the 55-file manifest is unchanged and this is
not B8 scope drift.

## Current-workspace projection

`current_inventory_gap_projection.json` is
`PLANNING_ONLY_NON_PROMOTING`, 39,695 bytes, SHA-256
`8c62d33452e894fc9e869f9c1a4f6b52e7f9db60326e2e8c059a0cb31ed45a7d`.
Two independent external generations were byte-identical.

Its current input hashes exactly match `inventory.txt` and the sealed B0
scientific inventory. Current inventory counts are:

- raw entries: `234`;
- raw fragrance entries: `229`;
- unique normalized entries: `218`;
- unique fragrance materials: `213`;
- owned unique fragrance materials: `210`;
- unavailable unique fragrance materials: `3`;
- duplicate canonical entries: `16`;
- matched owned materials: `197`;
- unmatched owned materials: `13`; and
- matched unavailable materials: `2`.

The projection contains 4,067 requirements across 19 property rows: 2,457
missing, 1,020 weak, 278 unknown, and 312 conflicted; no requirement is silently
promoted to accepted authority. It has 30 dashboard cells and zero legacy
promotions. JSON validation, secret-like scanning, prohibited aggregate-key
scanning, and absolute-path scanning all returned zero findings.

## Recovery and protected state

Before refreshing B8 evidence, a path-preserving archive was created at
`outputs/b8-authoritative-recovery/20260802T092149/b8-evidence-before-refresh.zip`.
It is 23,853 bytes with SHA-256
`0c8c2339b5978cd641ff3057258e3d2fa867dd0c45e96bbdc6cc063f467da3e7`.
All 28 file entries are safe, and all 28 restored paths matched their archived
hashes. The archive remains outside the B8 commit scope.

Protected state remains byte-identical to sealed B7:

- `perfume_chem.db`: 12,288 bytes, SHA-256
  `02b64be88e4a8881c968ec9ef7f0185ed7b1bcedc6ed33885f07d7de70a0da5e`,
  `quick_check=ok`;
- `data/perfumery_kb.db`: 2,084,864 bytes, SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`,
  immutable read-only `quick_check=ok`; and
- neither database contains an Alembic version row and neither was opened for
  migration by this gate.

## DeepLuna Fast disposition

Historical DeepLuna B8 receipts remain historical notes only. Current job
`DS-32ea809bd7db053cc21132e84f1161e8` used FLASH with `NO_LUNA`, but Sol
rejected its worker `PASS`: it repeated the stale 439-test count and missed the
changed projection, archive, protected-state, date, and timing fields. The
rejection is preserved in
`logs/deepluna_current_preaudit_rejected.json`.

Corrected final audit `DS-f7c89f252169cb53ce950fcc1b693c01` used DeepSeek
V4 Flash on DeepInfra Priority with `NO_LUNA` and one provider call. It covered
all 23 required current reads, found the package mutually consistent, reported
no negative findings or scope deviation, and left zero unknown or open
reservations. Sol independently rechecked the artifact inputs, 19 property
rows, 4,067 requirements, 30/2/440 tests, receipt digests, protected databases,
and archive before accepting that bounded audit. The first local archive-byte
comparison then caught a one-segment SHA transcription error in the report and
archive receipt (`e96bddc` versus verified `e96bbdc`). The archive itself had
not changed; Sol corrected the evidence metadata and reran the local package
checks rather than retrying the provider.

## Exit decision

The canonical implementation, executable tests, deterministic projection,
append-only migration constraints, protected-state checks, restorable archive,
and reconciled current Fast audit agree. The B8 exit gate passes. B9 may begin
only after this exact B8 evidence package is committed; the commit does not
authorize any broader cleanup or unrelated work.
