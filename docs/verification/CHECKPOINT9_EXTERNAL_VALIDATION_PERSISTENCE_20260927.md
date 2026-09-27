# Checkpoint 9 — canonical external-validation persistence

Date: 27 September 2026

Status: `SOFTWARE_COMPLETE_CANONICAL_EXTERNAL_VALIDATION_PERSISTENCE_HOLD`

## Decision

Checkpoint 9 is complete at the software and evidence-boundary level. The
backend can now accept a strictly predeclared temporal observation or scoped
pairwise preference, bind it to immutable protocol, sample, application,
condition, order, pseudonymous assessor, qualification, session, repeat,
timepoint, endpoint, and provenance snapshots, and return a narrow receipt.
It cannot treat the stored record as admitted evidence, run a model, rank R6,
authorize a human study, or authorize physical, safety, compounding, or release
action.

```text
canonical_persistence_state = PASS_SOFTWARE_CONTRACT
physical_validation_state   = NOT_PERFORMED
human_observation_state      = NOT_COLLECTED
pleasantness_state           = NOT_ESTABLISHED
physical_liking_state        = NOT_TESTED
formula_action               = NO_CHANGE
formula_modified             = false
inventory_modified           = false
```

No production external-validation record, physical sample, participant
interaction, sensory result, model fit, formula ranking, inventory mutation, or
formula mutation was created by this checkpoint. Test records existed only in
isolated temporary databases.

## What was added

The additive `lab_external_validation_records` table stores one canonical
temporal cell or pairwise outcome per immutable row. Database constraints and
SQLite triggers reject invalid shapes, any authority bit set to true, updates,
and deletes. Migration `20260927_0019` is linear after
`20260923_0018` and has a tested downgrade.

The server now exposes:

- `POST /api/v1/lab/v2/external-validation/temporal-observations`
- `POST /api/v1/lab/v2/external-validation/pairwise-preferences`
- `GET /api/v1/lab/v2/external-validation/records/{record_id}`

Caller-supplied scientific or action authority is rejected by strict request
schemas. The server derives all hashes and snapshots, preserves explicit
missingness and pairwise ties, requires canonical finite decimal strings, and
rejects values outside the locked endpoint scale. Raw assessor identity fields
are prohibited; the public receipt does not expose pseudonymous assessor tokens
or protocol snapshot bytes.

Exact replay under the same requester and idempotency key returns the original
record. Reusing a key for different bytes, or trying to overwrite a declared
canonical cell, returns a conflict. The canonical cell is also unique at the
database layer.

`lab-export-v5` now round-trips the complete durable graph: the existing
physical-lineage tables, engine jobs/events/results, and the new external
validation rows. Earlier export revisions remain readable through sequential,
explicit migration.

## Frozen inputs and implementation hashes

The machine-readable authority record is
`data/governance/lavande_ambre_profond_r6_cp9_external_validation_persistence_20260927.json`.
It pins the Checkpoint 8 manifest and repair report, the primary-source-backed C0
panel contract already selected by the repository, and the following current
implementation bytes:

| Surface | SHA-256 |
|---|---|
| model | `6d9f4d0d35191bae7fed7e8f7bf224e2432f4de3e2c5f233e79a1f7d26ac3fed` |
| repository | `034b9e6612f96cf0c1d3bbf76969c0cd5a823c02d44901a3c9dcb46ac8976906` |
| request/response schemas | `f5f98807095d62316a0a33f1d69428a1e81e9095215605567f8532c1343f354b` |
| validation service | `ca1c5ead4055a8ba15e2142e674798c74ae2514dc82115b97214ed4eff103c6d` |
| API | `0227ae5c73f3ba52ef22c48b001b230398ee9545e0061644f71e32eefe03fa1f` |
| migration | `276070c54f1d51b81f9a7d9a3b1159abaff88cf24a9a39582145356cc99e73db` |
| logical export | `d35578a6e96d2b37ee5495ba8b51e34b1d7b45213885bf0631d446b6c2800bac` |

## Verification

- Focused CP9 unit/API/migration/export tests: 15 passed.
- Existing temporal, sensory-ledger, panel, preference, and Checkpoint 8
  regressions: 102 passed.
- Wider backend Lab, persistence, backup, migration, physical-lineage, and
  engine-job regression: 58 passed. One unrelated legacy hypothesis assertion
  remains stale because it expects Hydroxycitronellal to be absent even though
  the live inventory now contains that owned material; the Checkpoint 9 paths
  are not involved.
- Focused Ruff: passed.
- Focused mypy: passed with third-party imports ignored under the repository's
  documented backend command.
- Quick project verification passed nine checks. Its sole failure was the
  pre-existing formula-artifact validation for stale/quarantined formula
  artifacts. The reviewed golden fixture remained byte-identical at
  `9cf31e92d3c8e814f3bc2654ffba6f3fbd766de8c705630ae78fb5c24a1dfc61`.
- Scoped whitespace validation passed. A repository-wide invocation could not
  traverse two pre-existing permission-locked C10 replay scratch trees, but it
  reported no whitespace defect before returning success.

The strict physical-completion tolerance was not weakened. A separately
reproduced pre-existing execution-export test still attempts to complete a
reserved `1 g` transfer with `0.96 g` and is correctly rejected by the current
production tolerance.

## Authority boundary and remaining project work

Every persisted row and response fixes these fields to false:

```text
processing_allowed             = false
scientific_authority           = false
sensory_authority              = false
model_calibration_authority    = false
evidence_admission_authorized  = false
release_authority              = false
safety_authority               = false
compounding_authority          = false
```

This checkpoint closes the persistence gap identified in the Checkpoint 8
repair. It does not close the physical project. Before meaningful R6 evidence
can enter this path, the project still needs the exact physical build and stock
lineage, aging/storage/stability execution, applicable measurement and curve
evidence, a separately authorized locked human protocol, qualified assessors,
physical samples, and observed rows. Those rows would then require a separate
evidence-admission and analysis checkpoint; storage alone cannot establish
pleasantness, liking, superiority, safety, or a winning formula.

The literature-first constraint affected this design by retaining the frozen
C0/Checkpoint 8 protocol bindings and endpoint separation instead of inventing
a new sensory score or translating persisted rows directly into optimizer
authority. No new literature question was introduced, so the already reviewed
primary-source-backed contract was reused rather than redundantly searched.
