# Build B5 Analytical Authority Gate

Decision: **PASS**

This report independently re-verifies Build B Phase B5 against the current
authoritative checkout. Historical reports and agent claims are notes only;
current executable tests, source and migration constraints, protected state,
restored artifacts, and the reconciled final audit decide the gate.

## Authority and scope

- B5 implementation authority:
  `40751831f65da8de464d45fbd3ceb4b53d53536d`.
- Verification head before this report:
  `cc6cc950df23a0d332636cf4e3b85a74de4db529`.
- B5 phase revision: `20260731_0009`.
- Current single repository Alembic head: `20260731_0012`.

The B5-owned analytical model, repository, service, migration, and four test
files are unchanged since the implementation commit. Shared laboratory files
have later-phase hashes and are verified as part of the current cumulative
gate. This phase does not implement B6-B10.

## Implemented canonical contract

- Eight append-only tables bind immutable analytical methods, claim-specific
  validation, ordered sequences, one primary run subject, vendor and open raw
  files, peak identity and quantity authority, GC-O events, and persisted claim
  decisions.
- Required method objects reject missing, unknown, non-finite, blank, empty
  object, and empty array placeholders. Method and validation provenance
  digests are database-constrained.
- Supported claims select a matching PASS validation with nonempty criteria for
  the requested identity or quantity claim.
- Peak and claim applicability are exact matrix/analyte/method scopes checked
  against canonical validation, A2 analyte, and run method records.
- Calibrated quantities preserve A2 quantity, response factor, unit, basis,
  working range, uncertainty, matrix, analyte, and method. HS-SPME additionally
  requires complete extraction conditions and matching calibration scope.
- Blocking QC persists a withheld result as SQL NULL; qualifying QC caps the
  result at advisory. GC-O cannot confer exact identity.
- An A2 exact analytical claim requires the exact supported B5 run, mapped
  claim type, policy version, and direct evidence record.

## Current deterministic verification

All accepted commands ran non-interactively under supported Python 3.11.15
with ANSI disabled, explicit timeouts, external writable temp/cache state, and
separate stdout/stderr logs under `docs/verification/b5/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr |
|---|---:|---|---|
| A2 science + B1-B5 compatibility pytest | 248 passed in 349.74 s | `603F4A3D...A79DB1` | empty |
| Ruff, exact B5 paths | all checks passed | `A4443AFD...D26B0` | empty |
| Mypy, four B5/A2 bridge modules | no issues | `D9A5631F...7BB76` | empty |

The accepted 25-file suite returned direct exit code zero and covers A2
science persistence/export/transactions, B1-B5 schemas and services, every
phase migration through B5, B5 supported/blocking/qualifying end-to-end twins,
current-head migration coverage, and backup/restore.

PowerShell's raw UTF-16LE captures remain preserved in the external accepted
run directory. The repository evidence copies are the same text normalized to
UTF-8 without BOM so Git and bounded readers treat them as text.

Three launch attempts are excluded transparently: one PowerShell wrapper
terminated before tests and left empty logs; one complete 248-pass run failed
to expose the child exit property; and one malformed inline basetemp argument
returned pytest usage exit 4 without running tests. A five-test wrapper probe
then returned direct exit zero before the unchanged accepted full rerun.

## Protected database and migration state

| Database | Bytes | SHA-256 before and after | `quick_check` | Alembic rows |
|---|---:|---|---|---:|
| `perfume_chem.db` | 12,288 | `02B64BE8...0DA5E` | `ok` | 0 |
| `data/perfumery_kb.db` | 2,084,864 | `5A779F9D...63FE1` | `ok` | 0 |

Both databases were inspected through immutable read-only SQLite connections;
their hashes were unchanged. The B5 phase revision is intentionally
distinguished from current linear head `20260731_0012`.

## DeepLuna boundary and reconciliation

- Route is Fast-only `FLASH` with `NO_LUNA`; Codex subagents used: zero.
- Fresh exact-project health was `READY` on CANDIDATE_V2/release 0.9.9 with no
  active or queued work and zero reserved or unknown accounting.
- Current high-risk audit `DS-1793498b9b079fe95226659f8cd5059a`
  returned PASS / POSITIVE / ACCEPTED with no negative finding or scope
  deviation. Sol independently reproduced the relevant claims through the
  current 248-test gate and direct source, migration, hash, and database checks.
- Historical Fast PASS packets remain supplemental; one missed seven authority
  defects later reproduced and fixed by Sol.

Final report audit `DS-d27821a338c0d79720f0df5038bdc9f7` returned
PASS / POSITIVE / ACCEPTED with one Fast call, no cache hit, no negative
finding, no scope deviation, and no required correction. Sol reconciled it
against current logs, source constraints, migration behavior, protected
databases, and hashes. The normalized receipt is
`docs/verification/b5/logs/deepluna-final-audit.json`, SHA-256
`BDF0D215637985B069C3D45BF6804B3F9534E80D3CB47922EE831C5E19FE5303`.

## Recovery and dirty-work preservation

The complete prior B5 report/log tree is preserved at
`outputs/b5-authoritative-recovery/20260802T074522/b5-evidence-before-refresh.zip`,
SHA-256 `72F6471154DFEDAA0C58DABC8CE1C2F9851679933343B0FCC6912E36D5EA3935`.
The archive contains all 12 files; separate extraction reproduced every path
and SHA-256 exactly.

Before report editing, 105 tracked paths were dirty, 1,250 files were
untracked, and zero entries were staged. No cleanup, reset, database mutation,
or unrelated edit was performed.

## Exit decision and claim boundary

The local B5 gate is green end to end:

```text
method authority
-> claim-specific validation
-> ordered sequence
-> exact run subject and raw files
-> required QC
-> A2 peak
-> B5 identity or calibrated quantity authority
-> supported, advisory, or withheld assessment
-> exactly matching A2 analytical claim bridge
```

Final B5 decision is **PASS**. Scientific release remains **BLOCKED**. B6 may
begin only after the exact B5 evidence set is committed without unrelated
paths.
