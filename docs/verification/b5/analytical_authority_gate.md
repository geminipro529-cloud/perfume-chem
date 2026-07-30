# Build B5 Analytical Authority Gate

Decision: **PASS**

Implementation authority:
`40751831f65da8de464d45fbd3ceb4b53d53536d`.

This gate covers Build B Phase B5 only. It does not implement regulatory
authority (B6), claim sufficiency (B7), decision-value backfill (B8),
production consumers (B9), or the Build B release audit (B10).

## Implemented canonical contract

- Eight zero-backfill, append-only tables bind analytical methods,
  claim-specific validation, ordered sequences, one primary run subject,
  vendor and open raw files, peak identity/quantity authority, GC-O events,
  and persisted claim decisions.
- Required method objects reject missing, unknown, non-finite, blank, empty
  object, and empty array placeholders. Method and validation provenance
  digests are database-constrained.
- A supported claim selects a matching `PASS` validation with a nonempty
  acceptance criterion for the requested identity or quantity claim.
- Peak and claim applicability are exact three-key objects and are checked
  against the selected validation scope, A2 analyte, and run method rather
  than trusted as caller declarations.
- Calibrated quantities match the preserved A2 quantity, response factor,
  unit, basis, working range, uncertainty, matrix, analyte, and method.
  HS-SPME additionally requires complete extraction conditions.
- Blocking QC persists a withheld decision with SQL `NULL` result; qualifying
  QC persists advisory-only authority. GC-O cannot promote exact identity.
- An A2 exact analytical claim now requires the exact supported B5 run,
  mapped claim type, policy version, and direct evidence record.

## Fresh canonical verification

All accepted commands ran non-interactively under supported Python 3.11.15,
with ANSI disabled, explicit timeouts, and separate stdout/stderr logs under
`docs/verification/b5/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr |
|---|---:|---|---|
| A2 science + B1-B5 compatibility pytest | 248 passed in 249.32 s | `79C6CF3A...68662` | empty |
| Ruff, exact B5 paths | all checks passed | `AF352A86...2D9AF` | empty |
| Mypy, four B5/A2 bridge modules | no issues | `9A7B872E...C9400` | empty |

The reconstructed prior gate contained 236 tests. Twelve new regression cases
cover the post-audit defects. The main RED run produced 13 expected failures
and 75 passes; its unchanged GREEN counterpart passed 88/88. A separate
general calibration-scope test was also observed RED and then GREEN.

The protected root `perfume_chem.db` remains zero bytes with SHA-256
`E3B0C442...B855`. `data/perfumery_kb.db` remains 2,084,864 bytes with
SHA-256 `5A779F9D...3FE1`; an immutable read-only SQLite connection reports
integrity `ok`.

## Independent review and DeepLuna boundary

DeepLuna remained Fast-only (`FLASH`, `NO_LUNA`) and no Codex subagent was
used. Job `DS-76cea2b9f1bc4250e38d5f2580e33623` identified the legacy A2 exact
claim bypass; Sol reproduced and closed it.

The final advisory audit
`DS-ae24d8b17460b62519ec7c04a3efa92b` returned PASS and positively reported
three migration properties. Sol reproduced those properties with 3/3 tests.
The audit nevertheless missed seven authority defects:

- mismatched claim type, policy, or direct evidence could reuse a supported
  B5 assessment;
- self-consistent false applicability could pass;
- validation selection ignored claim-specific acceptance criteria;
- required policy objects accepted empty collection placeholders;
- validation source digests lacked a database constraint;
- the nominal matching HS-SPME path used the wrong matrix digest; and
- non-HS calibration identifiers were not compared with canonical scope.

Each defect was closed under local RED/GREEN evidence. No third provider call
was made because the B5 Fast stage had reached its two-call cap. DeepLuna
evidence remains supplemental; canonical source, tests, constraints,
reproducible artifacts, and Sol's independent verification are final
authority.

## B5 exit decision

The end-to-end gate proves:

```text
method authority
-> claim-specific validation
-> acquired ordered sequence
-> exact run subject and raw files
-> required QC
-> A2 peak
-> B5 identity/calibrated quantity authority
-> persisted supported, advisory, or withheld assessment
-> exactly matching A2 analytical claim bridge
```

Supported, blocking-QC, and qualifying-QC migrated-database paths pass.
Migration creates eight empty tables, installs update/delete guards, preserves
prior rows, downgrades only B5, and re-upgrades empty. Model/migration columns,
checks, indexes, unique constraints, foreign keys, and triggers agree.

Therefore B5 passes without promoting legacy analytical rows, equating area
percent with formula weight percent, treating GC-O as exact identity, or
connecting production consumers.

## Protected state and recovery

- The A0 full recovery package remains preserved.
- Three path-preserving B5 archives cover scratch preimplementation,
  canonical prepromotion, and the post-audit hardening prefix.
- Archive SHA-256 values are recorded in the machine-readable report.
- Every archive was extracted separately and every archived path hash matched.
- After the implementation commit, the pre-existing worktree still had 105
  tracked dirty paths, 673 untracked files, and zero staged entries.

## Limitations and claim boundary

- B5 authority is valid only for the exact method, validation, run, peak,
  matrix, analyte, policy, evidence, and review scope.
- No legacy analytical row is backfilled or promoted.
- No production API, UI, optimizer, or release consumer is connected before
  B9.
- Build B remains incomplete until B6 through B10 pass.
- Scientific release remains **BLOCKED**.

B6 may begin under its own RED tests and exit gate.
