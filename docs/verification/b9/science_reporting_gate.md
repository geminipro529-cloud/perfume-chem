# Build B9 API, UI, and science-authority reporting gate

Status: **PASS**

Recorded: 2026-07-31 (Asia/Bangkok)

Branch: `codex/add-inventory-materials`

Pre-implementation checkpoint:
`ca8731a3cd6d59ef9de38f29add2c42f6d5eb07e`

Verified implementation checkpoint before this report:
`596a90eaa4b7a6492137d15a77d7f006e16f6035`

## Outcome

Build B9 now exposes the canonical Build B science ledger through two
read-only endpoints:

- `GET /api/v1/lab/science/authority?view=strict|exploratory`
- `GET /api/v1/lab/science/report.md?view=strict|exploratory`

The JSON contract is `lab-science-authority-report-v1`; its authority state
is always `READ_ONLY_NON_PROMOTING`. The report queries 25 canonical model
collections and publishes 20 ordered sections covering source documents and
exact locators, observations and selected assertions, conflict sets,
contextual thresholds and OAV, knowledge rules and contradictions,
analytical methods through run/QC evidence, regulatory snapshots/findings,
and claim-authority decisions/support.

No migration was added. Both endpoints are query-only, and executable tests
verify that representative B1/B2 table counts do not change across requests.

## Strict and exploratory views

Every stored report record remains visible.

- Strict mode partitions eligible records under `included` and keeps every
  non-eligible record under `withheld`, including exact reason codes.
- Exploratory mode places every record under `included` but preserves each
  record's original `strict_eligible` flag and reasons.
- Neither mode creates, promotes, releases, or alters authority.

The API, Markdown, and UI preserve exactly eight evidence labels:

1. `MEASURED`
2. `LITERATURE_DERIVED`
3. `SUPPLIER_PROVIDED`
4. `EMPIRICALLY_CALIBRATED`
5. `MODEL_ESTIMATED`
6. `HEURISTIC`
7. `SPECULATIVE`
8. `UNKNOWN`

The policy forbids numeric aggregation. No confidence, coverage, or overall
score is emitted, and evidence classes are never flattened into one
confidence percentage.

## Serialization and UI boundaries

Each canonical collection has an explicit field allowlist. Generic ORM
serialization is not used. Exact source/extraction locators and provenance
round-trip, while local artifact paths, raw source paths, database details,
environment or credential fields, and score-like fields remain excluded.

The dependency-free Science view provides strict/exploratory selection, JSON
and Markdown downloads, all eight visible labels, explicit
`READ_ONLY_NON_PROMOTING` language, and visible strict-withheld partitions.
Record-provided values are inserted through DOM `textContent`, not dynamic
HTML.

JSON and Markdown generation are deterministic. The JSON report carries a
SHA-256 over its canonical unsigned payload.

## Verification evidence

Supported runtime:

- Python `3.11.15`
- Node `v26.3.0`
- Alembic head `20260731_0012`

All commands ran without a PTY, with ANSI disabled, explicit timeouts, and
separate stdout/stderr capture.

Exact B9 schema, projection, API, Markdown, and UI contract:

```powershell
python -m pytest tests/unit/test_b9_science_reporting.py tests/integration/test_b9_science_reporting_api.py tests/integration/test_lab_ui.py::test_science_authority_view_preserves_labels_modes_and_unknowns --color=no -q
```

Result: `9 passed in 5.88s`, exit `0`; wrapper duration `10.188s`.

Complete A2 through B9 compatibility, migration, backup/restore, lab API, and
UI gate:

```powershell
python -m pytest <60 exact A2-B9 test files> --color=no -q
```

Result: `462 passed in 523.51s`, exit `0`; wrapper duration `529.611s`.

Static and persistence gates:

- Ruff: `All checks passed!`, exit `0`.
- mypy: `Success: no issues found in 4 source files`, exit `0`.
- Node JavaScript syntax: exit `0`.
- Alembic: `20260731_0012 (head)`, exit `0`.
- immutable read-only SQLite `PRAGMA quick_check`: `ok`.
- every captured stderr stream is empty.

Negative-path coverage includes invalid view rejection, empty-database closed
output, strict withholding of heuristic evidence, exploratory preservation of
strict ineligibility, exact locator round-trips, recursive exclusion of
score/local-path fields, read-only row counts, deterministic JSON/Markdown,
all eight UI labels, and DOM-safe record rendering.

Exact commands, timestamps, timeouts, exit codes, and stream paths are
retained in `docs/verification/b9/logs/*.result.json`.

## Recovery and protected state

The pre-write archive is:

`D:\.backups\perfume-chem\build-b9-prewrite-20260731T094431+0700.tar`

- bytes: `97126400`;
- SHA-256:
  `24d6a306025f6ec43cfc751590ae6ec8c0cab3b28e89894011d3ff37ca838118`;
- tar entries: `404`;
- restored files whose hashes were verified: `402`;
- pre-existing non-runtime dirty or untracked paths preserved: `397`;
- runtime paths excluded: `501`;
- planned absent paths recorded: `10`; and
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

No protected database was migrated or populated.

## DeepLuna Fast audits

Both audits followed a fresh exact-project `READY` check and used
FLASH/`NO_LUNA`, one provider call, and no Codex subagents.

Pre-implementation inventory:

- job `DS-a135a09a9756d541f0a602054852c339`;
- `PASS`;
- all 23 bounded source files inspected;
- no negative finding, residual risk, architecture uncertainty, scientific
  uncertainty, or scope deviation; and
- `108527` prompt, `708` completion, `109235` total tokens.

Final adversarial audit:

- job `DS-44810686be33907accaa5cfa39f91fb5`;
- `PASS`;
- no defect, negative finding, residual risk, architecture uncertainty,
  scientific uncertainty, scope deviation, or changed file;
- `69119` prompt, `704` completion, `69823` total tokens; and
- one DeepInfra `deepseek-ai/DeepSeek-V4-Flash` call with zero Luna runs.

The first final-audit submission was rejected locally before transmission
because a declared log range exceeded EOF. The range was corrected from
measured file lengths, a fresh exact-project check ran, and the one accepted
provider call passed.

Sol independently reproduced the API behavior, tests, static checks,
migration state, archive hash, protected database state, and negative paths
before accepting the result.

## Exit decision

The canonical implementation, executable tests, deterministic reports,
explicit serialization boundaries, visible evidence distinctions,
protected-state checks, and bounded independent audit agree. The B9 exit gate
passes.

B10 may begin only after this gate package is validated and committed.
