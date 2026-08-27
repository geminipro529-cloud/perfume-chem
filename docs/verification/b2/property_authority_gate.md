# Build B2 Property Authority Gate

Decision: **PASS**

This report independently re-verifies Build B Phase B2 against the current
authoritative checkout. Historical reports and agent claims are discovery notes
only. The executable tests, migration graph, protected databases, restored
archives, current source hashes, and final reconciled audit decide the gate.

## Authority and scope

- Initial B2 implementation: `aa91cda113931e85e318227dc9816bc091ed614d`.
- Sol gate fixes: `bdf839982fb4255488895bc091f16ad53bac8714`.
- Verification head before this report:
  `1736e2627fded33067fa0f18000b5bfe9d3bb632`.
- B2 phase revision: `20260730_0006`.
- Current single repository Alembic head: `20260731_0012`.

This gate covers observation-first property authority only. Contextual threshold
and OAV policy remain B3; rule compilation remains B4; analytical, regulatory,
claim, backfill, and API/report authority remain B5-B9.

## Implemented canonical contract

- Five append-only canonical tables store typed observations, explicit conflict
  sets and members, versioned selected assertions, and one decision with
  rationale for every candidate.
- Identity scope preserves chemical entity, stereoisomer or mixture, trade
  grade, supplier product, supplier lot, stock solution, physical dose, and
  natural material. Natural identity requires all ten frozen dimensions.
- Numeric, categorical, interval, distribution, and censored values are
  mutually exclusive. `NOT_DETECTED` has no numeric value and is never zero.
- Observation creation requires an exact B1 source, extraction, locator,
  accepted workflow scope, and content hash.
- Conflicts retain values, conditions, methods, units, identities, and source
  independence; no incompatible value is averaged or silently overwritten.
- Assertions use explicit IDs and versioned policy. Observation, model, and
  explicit-none selections are separately validated. Blocking unresolved
  conflicts withhold authority.
- Legacy `lab_material_properties` rows remain separate and are labeled
  `LEGACY_HEURISTIC`; the B2 migration creates zero canonical observations.

## Current deterministic verification

All commands ran non-interactively under supported Python 3.11.15 with ANSI
disabled, explicit timeouts, external writable temp state, and separate
stdout/stderr logs under `docs/verification/b2/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr |
|---|---:|---|---|
| B1+B2+compatibility pytest | 73 passed in 130.75 s | `D96BC26A...1550703` | empty |
| Ruff, exact B2 paths | all checks passed | `82B3E6A6...56B4F18` | empty |
| Mypy, three B2 modules | no issues | `281A094C...627A24` | empty |

The cumulative pytest gate includes B1/B2 schema and service tests, both phase
migration tests, downgrade/re-upgrade coverage, the current linear migration
head, and backup/restore coverage. Every command exited zero. All six current
logs contain no ANSI escape sequence.

The broader import-graph mypy result retained in the directory is explicitly a
historical diagnostic. It reported four errors in
`engine/calibration/store.py:83-86` outside the scoped B2 modules and was not
rerun as part of this seal.

## Protected database state

| Database | Bytes | SHA-256 before and after | `quick_check` | Alembic rows |
|---|---:|---|---|---:|
| `perfume_chem.db` | 12,288 | `02B64BE8...0DA5E` | `ok` | 0 |
| `data/perfumery_kb.db` | 2,084,864 | `5A779F9D...63FE1` | `ok` | 0 |

Both databases were inspected through immutable read-only SQLite connections.
Their hashes were unchanged by the cumulative test, lint, and typing gates.

## DeepLuna boundary and reconciliation

- Route is Fast-only `FLASH` with `NO_LUNA`; Codex subagents used: zero.
- Fresh exact-project preflight was `READY` on runtime `CANDIDATE_V2`, release
  `0.9.9`, with no active or queued work and zero reserved/unknown accounting.
- Oversized packet `DS-594497e1f5036b27886aa2f018f94672` was rejected
  locally before transmission; provider calls and spend were zero.
- Bounded implementation audit `DS-f24ca72817d9c63d42ea0896bf2af152`
  returned terminal PASS / POSITIVE / ACCEPTED with no negative finding or
  scope deviation. Sol independently reproduced its gate claims locally.
- Cached planning audit `DS-fcfff19c1d33820b1d5045eacad539c7`
  incorrectly called the old reports current. Sol rejected that statement after
  live hashes proved staleness.
- Final report audit `DS-3bb4335da7dd30e98231776f20ee0b59`
  returned PASS / POSITIVE / ACCEPTED with one `FLASH` provider call, no cache
  hit, no negative finding, and no scope deviation. Sol reconciled every
  finding against the current logs, source ranges, tests, migration, protected
  state, and report hashes; no correction was required.
- The normalized audit receipt is
  `docs/verification/b2/logs/deepluna-final-audit.json`, SHA-256
  `C257FF1550FA5C5EC7DF1AB4D7EAFE271C2ED0D242B24278DB8DD27E83669B0E`.

Historical packets that omitted required detailed citations remain
supplemental and are not final authority.

## Recovery and dirty-work preservation

- Reports and prior pytest output:
  `outputs/b2-authoritative-recovery/20260802T062638/b2-evidence-before-refresh.zip`,
  SHA-256 `C63351820BDBEE6AD2E714AF16A7677D41C3A9CEB7722F04F513C17C65400946`.
  All three extracted paths matched their expected hashes.
- Complete 16-file B2 log directory before final refresh:
  `outputs/b2-log-recovery/20260802T063943/b2-logs-before-final-refresh.zip`,
  SHA-256 `AEC26005EF1C4F0FB74224C955FCC12BA472136627C9EA2415B084D48EFE0F78`.
  Every extracted path matched its source hash.
- Before report editing, 107 tracked paths were dirty. The final pre-commit
  state is 109 tracked dirty paths, 1,176 untracked files, and zero staged
  entries. No cleanup, reset, or unrelated modification was performed.

## Exit decision and claim boundary

The local B2 gate passes: every migrated runtime property is either traceable
to an observation and selected assertion or explicitly labeled legacy
heuristic. This migration promotes no runtime property, so every pre-B2 scalar
remains quarantined as `LEGACY_HEURISTIC`. Synthetic records prove exact B1
linkage, typed values, visible conflicts, complete candidate decisions,
assertion reconstruction, and authority withholding.

Final B2 decision is **PASS**. Scientific release remains **BLOCKED**. This gate
proves observation and selection mechanics only; it does not establish real
literature-property truth, contextual OAV authority, claim sufficiency, or
release readiness. B3 may begin only after this exact B2 evidence set is
committed without unrelated paths.
