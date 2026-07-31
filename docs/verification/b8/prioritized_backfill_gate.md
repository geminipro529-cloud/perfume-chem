# Build B8 prioritized scientific-data backfill gate

Status: **PASS**

Recorded: 2026-07-31 (Asia/Bangkok)

Branch: `codex/add-inventory-materials`

Pre-implementation checkpoint:
`3c160e3266a9288791d8680e23145903976bc2d8`

Verified implementation checkpoint before this report:
`3cb554f1ab242ec6c517329504867fe5b502ba70`

## Outcome

Build B8 now provides an append-only, reconstructable campaign ledger for
prioritizing scientific-data gaps by current decision value. Priority is
strictly lexicographic and code-owned:

1. current physical inventory;
2. active or shipped formula;
3. high-dose structure;
4. potent trace use;
5. regulatory or family impact;
6. analytical standard;
7. natural constituent; and
8. model sensitivity.

The campaign records exact canonical signal links and ten gap requirements:
identity, grade, molecular weight, density, vapor pressure, contextual
threshold, safety documentation, retention index, analytical reference, and
natural-lot composition. Accepted gaps reconstruct through compatible B7
authority; missing, weak, contradictory, stale, cross-material, wrong-scope,
wrong-identity, and wrong-property evidence fails closed.

The dashboard is stratified by evidence class, property, current inventory,
active formula, chemical family, regulatory impact, and model sensitivity.
The policy and schema prohibit an overall coverage score.

This is planning authority only. B8 does not create evidence authority,
release authority, legal approval, a safety certificate, or proof of
real-world performance.

## Persistence and reconstruction

Additive migration `20260731_0012`, down revision `20260731_0011`, creates
five empty append-only tables:

1. `lab_backfill_campaign_versions`
2. `lab_backfill_material_priorities`
3. `lab_backfill_priority_signal_links`
4. `lab_backfill_gap_items`
5. `lab_backfill_dashboard_cells`

Campaign creation is one transaction. Revision creation requires the latest
parent, hashes the input snapshot and policy, persists the ranked material
rows, typed signal links, gaps, and dashboard cells, and then reconstructs
those rows deterministically. SQLite append-only triggers reject updates and
deletes.

## Defects found and closed

- Typed resolvers replaced caller-supplied priority values. All eleven signal
  kinds now resolve from canonical records; nonfinite and out-of-range values
  fail closed.
- Accepted property gaps now require the exact B7 claim type and compatible
  property subtype, preventing authority reuse across molecular weight,
  density, and vapor pressure.
- Cross-material signals roll back atomically, and stale campaign parents are
  rejected.
- Case-only alias ties in the workspace projection gained a deterministic
  secondary ordering key. Two separate Python processes then produced the
  same artifact bytes and SHA-256.
- The canonical migration and backup tests initially reproduced three
  stale-head failures at `20260731_0011`. Only their two `CURRENT_HEAD`
  constants changed to `20260731_0012`; all twelve focused cases and the full
  compatibility gate then passed.
- The first Ruff evidence recapture used an unsupported `--no-color` option.
  It was replaced by Ruff's supported `--color never`; the final result exits
  zero and contains no ANSI escape bytes.

## Verification evidence

Supported runtime:

- Python `3.11.15`
- Node `v26.3.0`
- Alembic head `20260731_0012`

All commands ran without a PTY, with explicit timeouts and captured stdout and
stderr.

Exact B8 schema, policy, migration, and end-to-end gate:

```powershell
python -m pytest tests/unit/test_b8_backfill_schema.py tests/unit/test_b8_backfill_service.py tests/integration/test_b8_backfill_migration.py tests/integration/test_b8_backfill_e2e.py --color=no -q
```

Result: `30 passed in 16.60s`, exit `0`; wrapper duration `21.06s`.

Workspace projection gate:

```powershell
python -m pytest tests/test_b8_backfill_dashboard.py --color=no -q
```

Result: `2 passed in 0.05s`, exit `0`; wrapper duration `0.644s`.

Complete A2 through B8 compatibility, migration, and backup/restore gate:

```powershell
python -m pytest <55 exact A2-B8 test files> --color=no -q
```

Result: `439 passed in 447.12s`, exit `0`; wrapper duration `453.399s`.

Static and migration gates:

- Ruff: `All checks passed!`, exit `0`, no ANSI bytes.
- mypy: `Success: no issues found in 3 source files`, exit `0`.
- Alembic: `20260731_0012 (head)`, exit `0`.
- every captured stderr stream is empty.

The exact commands, start and finish times, timeouts, exit codes, and stream
paths are retained in `docs/verification/b8/logs/*.result.json`.

## Current-workspace projection

`current_inventory_gap_projection.json` is explicitly
`PLANNING_ONLY_NON_PROMOTING`.

- SHA-256:
  `e04a3daf31e09d13d5cf377fa13a4c31d4d7c5d52a36320890039493bccb94fe`
- byte-identical across two independent Python processes;
- raw entries: `232`;
- unique normalized entries: `216`;
- unique fragrance materials: `211`;
- owned unique fragrance materials: `208`;
- unavailable unique fragrance materials: `3`;
- duplicate canonical entries: `16`;
- matched owned materials: `196`;
- unmatched owned materials: `12`;
- matched unavailable materials: `2`;
- property requirements: `4048`;
- dashboard cells: `30`; and
- legacy promotions: `0`.

The frozen inputs cannot prove active-formula, chemical-family, or
model-sensitivity signals, so those dimensions remain `UNKNOWN`. The
projection cannot create B1-B7 authority or authorize release.

## Recovery and protected state

The pre-write archive is:

`D:\.backups\perfume-chem\build-b8-prewrite-20260731T081641+0700.tar`

- bytes: `97180160`;
- SHA-256:
  `e6e6ce1ece19c0cf698c77b21a32d12c641f4af14cb8c082610f83f2e7d7ff4f`;
- tar entries: `404`;
- restored files whose hashes were verified: `402`;
- pre-existing non-runtime dirty or untracked paths preserved: `397`;
- runtime paths excluded: `481`;
- planned absent paths recorded: `14`; and
- path-preserving extraction and every archived-file hash verified.

The archive hash was rechecked at the final gate.

Protected database state remained:

- `perfume_chem.db`: `0` bytes,
  SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- `data/perfumery_kb.db`: `2084864` bytes,
  SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`;
  and
- immutable read-only `PRAGMA quick_check`: `ok`.

No protected database was migrated or backfilled.

## DeepLuna Fast audits

Both audits followed a fresh exact-project `READY` check and used
FLASH/`NO_LUNA`, one provider call, and no Codex subagents.

Pre-implementation inventory:

- job `DS-30ef482e3b3a9bd2152c84b28e1c07f5`;
- `PASS`;
- `64,193` prompt, `761` completion, `64,954` total tokens; and
- measured spend delta `$0.008871525`.

Final adversarial audit:

- job `DS-a18df7187bed3044a0954faccf921ebb`;
- `PASS`;
- no negative findings, residual risks, architecture uncertainty, scientific
  uncertainty, or scope deviation;
- `107,016` prompt, `798` completion, `107,814` total tokens; and
- measured spend delta `$0.014662620`.

Sol independently reproduced the migration state, tests, hashes, deterministic
artifact, database integrity, and negative paths before accepting the result.

## Exit decision

The canonical implementation, executable tests, append-only constraints,
reproducible projection, protected-state checks, and bounded independent audit
agree. The B8 exit gate passes.

B9 may begin only after the B8 gate package is committed with the two
canonical migration-head test updates. Public API, UI, and
strict-versus-exploratory reporting remain out of B8 scope.
