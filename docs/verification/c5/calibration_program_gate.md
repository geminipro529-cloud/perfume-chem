# Build C5 calibration-program gate

Decision: **PENDING**

The C5 software and protocol harness is locally green, but this record has not
yet been sealed in an evidence commit and replayed at that exact commit. C6
therefore remains closed until those final evidence steps pass.

The empirical result is a separate, deliberate block:
`BLOCKED_PENDING_DATA`. No actual GC-MS/HS-SPME instrument dataset was found,
no empirical metric is reported, no measured domain is complete, and no model
is promoted. Passing the software gate does not change that status.

## What C5 implements

- A 19-material inventory-derived panel spanning the required chemical,
  volatility, polarity, hydrogen-bond, trace-potent, and bulk-structural
  domains.
- Eight matrix templates covering current stock, 10% and 20% finished
  strengths, high ethanol, DPG, TEC, DEP, and IPM/oil. DEP and water retain
  explicit source holds; unknown stock basis/carrier is never guessed.
- An immutable protocol contract recording sample mass/volume, vial/headspace,
  matrix batch, temperature, equilibration, extraction, SPME fiber and age,
  agitation, desorption, internal standard, calibration, blanks, carryover,
  QC, replicates, randomization, and drift.
- A strict real-data importer requiring the exact Build B5
  method-validation-run-peak-claim chain, matching matrix/analyte/method
  calibration, raw vendor and open-export hashes, clear blocking QC, and
  measurement uncertainty.
- A separate simulation-only path that cannot enter the real importer or
  authorize empirical promotion.
- Locked calibration, validation, and held-out partitions with cross-partition
  checks for identity, close analog, formula, supplier lot, matrix batch, and
  measurement session.
- A model lock that binds the split, prespecified evaluation plan, and
  validation dataset before held-out release.
- Bias, MAE, RMSE, median fold error, rank agreement, calibration
  slope/intercept, interval coverage, catastrophic outliers,
  missing/abstention rates, and baseline comparison overall and by material
  class, matrix, and condition. R-squared is not an acceptance metric.

## Executable evidence

- C5 focused: 38 passed.
- C4/C3/C2/C1/C0 compatibility: 41 / 105 / 79 / 96 / 24 passed.
- Complete root suite: 1,481 passed.
- Dependency invariant: 1 passed; `pip check` passed.
- Ruff, basedpyright, and mypy: passed.
- C0 standalone inventory verifier: PASS, 48 implementations, 29 call edges,
  24 fixtures.
- Scope check: exactly seven C5 implementation paths, with no production,
  database, migration, scientific-artifact, or legacy-ledger path.
- Three mutation checks caught simulation-origin bypass, leakage-dimension
  omission, and held-out-lock bypass; the exact source SHA-256 was restored.
- The 118,255,616-byte path-preserving recovery archive reverified with all
  429 pre-existing dirty/untracked files intact and zero unsafe, duplicate, or
  mismatched members.
- Protected database/WAL/SHM hashes and immutable SQLite quick checks were
  unchanged before and after the matrix.
- All 76 captured log files are UTF-8, ANSI-free, and free of credential-shaped
  matches; stdout and stderr were captured separately and every matrix stderr
  file is empty.

## Actual-data check

Five relevant SQLite databases were opened read-only and immutable; all passed
`quick_check` and none contained analytical or calibration table names. No raw
analytical file candidate, named analytical dataset, `data/calibration`
directory, or wear-test JSONL exists. The GCMS-named output is a failed formula
release-gate artifact, not an instrument measurement.

## DeepLuna Fast and Sol reconciliation

Fresh exact-project health was `READY`. One bounded DeepLuna Fast FLASH audit
completed PASS with `NO_LUNA`, no negative findings, no scope deviation, and
no Codex/GLM/Luna worker fallback. Sol independently reran 11 gate-bearing
tests and the actual-data absence check. Postflight reservations are zero.

## Current boundary

C5's reproducible harness, leak controls, and prespecified metric machinery are
green. Empirical calibration remains blocked pending real, B5-bound instrument
data. C6 remains closed until the evidence commit and exact-commit replay pass;
this pending record makes no claim that either has happened.
