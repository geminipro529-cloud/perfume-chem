# Build C1 Thermophysical Contracts Gate

Decision: **PENDING POST-COMMIT**

The current C1 executable/static evidence and final exact-project DeepLuna Fast
audit are green, but this report does not yet pass the phase. The evidence-only
commit and post-commit verification remain required. C2 is closed.

## Authority and scope

- Phase parent: `fddc07c12d914b8de9f81f2ecbb5c9423a6880a6`.
- Verification head before this report:
  `8c29acd6aaed4a1324ee925b743ce131f9875d15`.
- Branch: `codex/add-inventory-materials`.
- Scope: Build C, Phase C1 only.

C1 defines condition-aware evidence contracts and fail-closed selection. It does
not evaluate thermodynamic equations, migrate a runtime caller, write a database,
promote real property data, or authorize scientific release.

## Implemented contract boundary

- Sixteen closed thermophysical property identifiers are represented.
- Six vapor-pressure representation tags are closed:
  `MEASURED_TABLE`, `ANTOINE`, `WAGNER`, `DIPPR_STYLE`,
  `CLAUSIUS_CLAPEYRON`, and `OTHER_DECLARED_FORM`.
- Six uncertainty shapes are closed: standard uncertainty, interval,
  empirical distribution, parameter covariance, bounded range, and unknown.
- Identity, conditions, units, source, applicability, authority, uncertainty,
  interpolation state, and exact missing reasons survive selection.
- Measured tables and equation coefficients have mutually exclusive shapes.
- Coefficient convention, units, valid range, phase/purity assumptions, source,
  fit evidence, uncertainty, and extrapolation policy are explicit.
- B2 selected assertions adapt through a closed schema. Unknown program/schema
  fields fail; absence of scientific evidence returns `WITHHELD`.
- Release-grade extrapolation always withholds. Exploratory extrapolation
  requires both request permission and explicit model policy and remains
  advisory with a warning.
- Advisory B2 authority is never silently promoted.

The public package exports the C1 contract only. Its AST boundary test prohibits
backend/SQLAlchemy/legacy-estimator dependencies and equation-evaluation
functions.

## Current executable seal

All commands ran non-interactively with supported runtimes, ANSI disabled,
explicit timeouts, external pytest temp state, and separate stdout/stderr.

| Gate | Result | Process duration | Stdout SHA-256 | Stderr |
|---|---:|---:|---|---|
| C1+C0 pytest | 120 passed in 2.27 s | 2,958 ms | `9168CAFD...2BF3078` | empty |
| B1+B2 compatibility pytest | 48 passed in 41.02 s | 44,715 ms | `529882FE...535DF3F` | empty |
| Ruff, root C1 paths | all checks passed | 191 ms | `82B3E6A6...56B4F18` | empty |
| Ruff, backend C1 paths | all checks passed | 140 ms | `82B3E6A6...56B4F18` | empty |
| BasedPyright, `engine/physics` | 0 errors/warnings/notes | 1,475 ms | `56882E01...BD91C` | empty |
| Mypy, scoped backend service | no issues in 1 file | 330 ms | `8E63AE22...FC4FF` | empty |

The complete command arrays, working directories, tool versions, timeouts, exit
codes, durations, and log hashes are in
`docs/verification/c1/logs/seal-run-metadata.stdout.txt`, SHA-256
`E829BA36...58716D`. A strict scan of 37 current log files found zero invalid
UTF-8 files, zero ANSI escape bytes, and zero credential-shaped matches; matched
values were never recorded.

## Protected state and recovery

| Database | Bytes | SHA-256 before and after | `quick_check` | Mutated |
|---|---:|---|---|---|
| `perfume_chem.db` | 12,288 | `02B64BE8...0DA5E` | `ok` | no |
| `data/perfumery_kb.db` | 2,084,864 | `5A779F9D...63FE1` | `ok` | no |

The path-preserving C1 prewrite archive remains
`D:\.backups\perfume-chem\build-c1-prewrite-20260802T163623+0700.tar`,
118,418,432 bytes, SHA-256 `EE3F9963...05237`. It contains 444 creation
source files plus two archive-control members; all creation extraction and file
hash checks passed, and no unsafe member was found.

Before normalizing the two protected-state logs, their exact UTF-16LE bytes were
preserved in
`D:\.backups\perfume-chem\c1-log-encoding-prewrite-20260802T175916+0700.tar`,
SHA-256 `32453659...9AA3E`. Both extracted hashes matched. The logs were then
rewritten as UTF-8 without BOM with equal decoded JSON content.

## Closed phase scope

The diff from the C1 parent contains exactly ten allowlisted paths: the design,
plan, C0 compatibility record, four `engine/physics` files, one root test, the B2
service adapter, and its unit test. It contains no migration, database, C2,
headspace, temporal, or optimizer path. The changed backend service does not
import, invoke, or switch a production caller to `engine.physics`. No legacy
estimator import exists in `engine/physics`, and the scoped diff check is clean.

`C0-PM-017` now excludes only `engine/physics/vapor_pressure.py` from its
historical executable-DIPPR absence query. This does not claim executable DIPPR
support: C1 adds a declared `DIPPR_STYLE` representation tag but no evaluator,
and the C1 AST test independently enforces that boundary. The combined C0+C1
gate passes.

## DeepLuna boundary

- Route is exact-project DeepLuna Fast: `FLASH`, DeepSeek V4 Flash on DeepInfra
  Priority, with `NO_LUNA`; Codex subagents used: zero.
- The task-global MCP was bound to the scratch workspace and was rejected as
  perfume-chem authority. No repository content was transmitted through it.
- The repository-supported project launcher independently returned `READY` for
  project `perfume-chem`, runtime `CANDIDATE_V2` 0.9.9, accepted build
  `32973174...bc4f11`, five idle read lanes, one idle write lane, an enabled
  circuit, and zero queued/reserved/unknown work.
- The first C1 audit submission was rejected locally before provider use because
  two protected-state logs were not UTF-8. Provider calls: zero.
- Pre-gate inventory audit `DS-8a3ed3ab020815193ce65d3494408c44`
  used one `FLASH` call and correctly found that this JSON and Markdown did not
  yet exist. Sol reproduced both findings and accepted no unsupported claim.
- Final report/code/log audit `DS-52255c807ef88e1d592d31cbdf17d9d7`
  returned `PASS / POSITIVE / ACCEPTED` after one 70,712-input-token `FLASH`
  call. All required reads were receipted; there were zero negative findings,
  no scope deviation, and no architecture or scientific uncertainty.
- Sol reproduced its contract counts, source/test boundaries, report/log hashes,
  scope diff, protected state, and archive evidence locally. Unsupported
  findings accepted: zero.
- The normalized receipt is
  `docs/verification/c1/logs/deepluna-final-audit.json`, 3,007 bytes, SHA-256
  `B52B5C12...15F16EC`.
- DeepLuna remains supplemental; Sol and executable evidence retain final
  authority.

## Transparent rejected evidence

- The first final-log capture produced green output but null child exit codes.
  Those logs were rejected and preserved under the scratch recovery directory.
- The first archive recheck confused 446 total members with 444 source files.
  The corrected record explicitly accounts for the two control members.
- The first fresh seal matrix exposed two C1-introduced backend import-order
  failures and a mypy invocation-root mismatch. Ruff's exact diff drove the
  formatting-only commit `8c29acd6aaed4a1324ee925b743ce131f9875d15`;
  mypy was rerun from the supported repository root. All 14 rejected-attempt
  files were preserved in
  `c1-seal-attempt1-20260802T180733+0700`, and the full seal then passed.

## Known limitations and claim boundary

- No vapor-pressure equation or measured-table interpolation is evaluated.
- No unit-conversion engine exists; this boundary declares temperature in K.
- No production caller has migrated to `engine.physics`.
- No migration, canonical database write, or real-property promotion occurs.
- Headspace, temporal release, optimizer, and release behavior are unchanged.
- Contract validity is not scientific validation of coefficients,
  measurements, models, or perfume performance.
- Scientific release remains **BLOCKED**.

Current C1 decision remains **PENDING POST-COMMIT**. Only C1 evidence paths may
now be committed. C1 passes only after the post-commit verifier is green; until
then C2 remains closed.
