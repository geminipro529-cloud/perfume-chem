# Build B3 Contextual Threshold and OAV Gate

Decision: **PASS**

This report independently re-verifies Build B Phase B3 against the current
authoritative checkout. Historical reports and agent claims are notes only;
current executable tests, source and migration constraints, protected state,
restored artifacts, and the reconciled final audit decide the gate.

## Authority and scope

- B3 implementation authority: `3a61de2acd9a658ebba4600c29ffe22cff02b7cc`.
- Verification head before this report:
  `1688a132758814d9e0e5f37ae5ccc123c3d59767`.
- B3 phase revision: `20260730_0007`.
- Current single repository Alembic head: `20260731_0012`.

This gate covers contextual threshold and screening-OAV authority only. Rule
compilation remains B4; analytical, regulatory, claim, backfill, and API/report
authority remain B5-B9.

## Implemented canonical contract

- Three append-only tables store contextual threshold specialization,
  deterministic OAV assessments, and quarantined legacy threshold records.
- Threshold context preserves exact identity, grade, purity, stereochemistry,
  endpoint, route, medium, matrix composition, basis, apparatus, temperature,
  humidity, assessor population and training, sample size, psychophysical
  procedure, statistic, typed value, unit, uncertainty, source, locator,
  evidence class, and quality flags.
- Conversion requires an explicitly supported compatible convention and every
  required input. A solution threshold never becomes an air threshold through
  unit conversion alone.
- OAV is computed only when concentration and threshold match identity, basis,
  medium/matrix, endpoint, route, conditions, model applicability, authority,
  and unit convention.
- Every incompatible path fails closed with an ordered subset of the ten stable
  codes: `MISSING_THRESHOLD`, `IDENTITY_SCOPE_MISMATCH`,
  `THRESHOLD_MEDIUM_MISMATCH`, `THRESHOLD_ENDPOINT_MISMATCH`,
  `THRESHOLD_ROUTE_MISMATCH`, `THRESHOLD_UNIT_INCOMPARABLE`,
  `THRESHOLD_MATRIX_UNSPECIFIED`, `THRESHOLD_AUTHORITY_TOO_LOW`,
  `CONCENTRATION_NOT_COMPARABLE`, and
  `MODEL_OUTSIDE_APPLICABILITY_DOMAIN`.
- A supplied assertion must exist. Its selected observation and both context
  identifiers must match the unique threshold context.
- Strict-science mode has no heuristic fallback. Computed OAV is screening
  evidence only and cannot authorize exact intensity, percentage contribution,
  pleasantness, similarity, family, longevity, sillage, skin performance,
  release, or deletion below OAV 1.
- The migration creates no observation, assertion, assessment, or legacy
  import. The explicit adapter preserves the original verification status and
  produces quarantine commands without promotion.

## Current deterministic verification

All commands ran non-interactively under supported Python 3.11.15 with ANSI
disabled, explicit timeouts, external writable temp/cache state, and separate
stdout/stderr logs under `docs/verification/b3/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr |
|---|---:|---|---|
| B1+B2+B3+compatibility pytest | 100 passed in 211.26 s | `7E1AFD7A...7324E14` | empty |
| Ruff, exact B3 paths | all checks passed | `82B3E6A6...56B4F18` | empty |
| Mypy, four B3 modules | no issues | `D9A5631F...07BB76` | empty |

The cumulative suite includes B1-B3 schemas and services, all three phase
migrations, downgrade/re-upgrade behavior, current-head migration coverage,
and backup/restore. Every command exited zero, and all current logs are free of
ANSI escapes.

## Protected database and migration state

| Database | Bytes | SHA-256 before and after | `quick_check` | Alembic rows |
|---|---:|---|---|---:|
| `perfume_chem.db` | 12,288 | `02B64BE8...0DA5E` | `ok` | 0 |
| `data/perfumery_kb.db` | 2,084,864 | `5A779F9D...63FE1` | `ok` | 0 |

Both databases were inspected through immutable read-only SQLite connections;
their hashes were unchanged by the gate. The phase revision is intentionally
distinguished from the current linear repository head `20260731_0012`.

## DeepLuna boundary and reconciliation

- Route is Fast-only `FLASH` with `NO_LUNA`; Codex subagents used: zero.
- Fresh exact-project health was `READY` on runtime `CANDIDATE_V2`, release
  `0.9.9`, with no active/queued work or reserved/unknown accounting.
- Current bounded gap audit `DS-e69a5d0b601e4298bd76d19cb3fde602`
  returned PASS / POSITIVE / ACCEPTED with no negative finding or scope
  deviation. Sol independently reproduced its implementation claims with the
  current 100-test gate and direct source/migration inspection.
- Historical Fast audits remain supplemental. The initial historical PASS
  missed three defects later found and reproduced by Sol.
- Final report audit `DS-41cc36cf491df51c4172fc56212dd5dc`
  returned PASS / POSITIVE / ACCEPTED with one `FLASH` call, no cache hit, no
  negative finding, and no scope deviation. Sol reconciled all findings against
  the current tests, source, migration, protected state, and hashes; no report
  correction was required.
- The normalized audit receipt is
  `docs/verification/b3/logs/deepluna-final-audit.json`, SHA-256
  `821C3C22CEBD5DD58EC9897233A482C8DA92FAEB006E5D277EA3731A73FA956B`.

## Recovery and dirty-work preservation

The complete prior B3 report/log tree is preserved at
`outputs/b3-authoritative-recovery/20260802T065815/b3-evidence-before-refresh.zip`,
SHA-256 `E6AF3364A48C72941F116A0C354329DF67D3CD365CCE6D1B715446C8F6675F18`.
The archive contains all 14 files; a separate extraction reproduced every
path and SHA-256 exactly.

Before report editing, 107 tracked paths were dirty. The expected pre-commit
state is 109 tracked dirty paths, 1,199 untracked files, and zero staged
entries. No cleanup, reset, database mutation, or unrelated edit was performed.
Dirty legacy `engine/odor_thresholds.py`,
`engine/pipeline/oav_intelligence.py`, `tests/test_oav_authority.py`, and
`tests/test_oav_intelligence.py` remain untouched and non-authoritative.

## Exit decision and claim boundary

The local B3 gate passes: all ten context mismatches withhold OAV, and a
computed OAV exposes screening-only permitted use plus explicit stronger-claim
prohibitions. Strict science has no silent fallback, supplied missing
assertions are rejected, observation/assertion contexts must match, legacy
status is never upgraded, and migration promotes zero legacy values.

Final B3 decision is **PASS**. Scientific release remains **BLOCKED**. This gate
does not establish the scientific truth of any threshold value or make any
formula release-ready. B4 may begin only after this exact B3 evidence set is
committed without unrelated paths.
