# Checkpoint 6 — R6 Documentary Physical-Lineage Intake

Date: 2026-09-26

Scope: read-only software and authority checkpoint

Physical formula: unchanged

Inventory: unchanged

## Decision

Checkpoint 6 is complete as a non-executing documentary-intake implementation.
Physical readiness remains truthfully withheld:

```text
status                                      = HOLD
checkpoint6_state                           = SOFTWARE_COMPLETE_DOCUMENTARY_INTAKE_HOLD
documentary_input_completion_state          = HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE
input_integrity_state                       = VERIFIED
candidate_stock_rows                        = 63/63
row_documentary_preconditions_complete      = 0/63
all_line_documentary_preconditions_complete = false
physical_binding_eligible_rows              = 0/63
formula_action                              = DESIGN_SUCCESSOR_UNCHANGED
formula_modified                            = false
inventory_modified                          = false
```

The deterministic report hash is:

```text
ac0a43d37f723b3efa368618783c7178f082d75efe6f9c0549bd24efaeb60e92
```

This is a successful software checkpoint and not a physical-build pass.

## DeepMimo review disposition

The requested project-scoped DeepMimo review was attempted through the
Sol Ultra Delegate boundary. Health and project admission succeeded, but the
single completion returned `INVALID_RESPONSE`; it did not provide a valid
provider/backend receipt. No DeepMimo content was admitted.

The skill-authorized supervising GPT-5.6 Sol Ultra child used its one permitted
native GPT-5.6 Sol Ultra fallback. The fallback proposed a frozen,
non-executing documentary intake and identified the physical-lineage interface
risks listed below. The root task independently checked those claims against
the current repository bytes before implementation. Delegation granted no
scientific, evidence-admission, inventory, compounding, safety, or release
authority.

## Implemented contract

The immutable governance manifest is:

```text
data/governance/lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json
SHA-256 213c256a7ec7c16578bb0556cb9f12258d757191217d4e6a3a0ffe0033265823
```

It binds:

- the exact Checkpoint 5 protocol, evaluator, deterministic report, R6 row-set,
  inventory text, inventory snapshot, and inventory overlay hashes;
- the existing physical-lineage service, schema, model, and migration bytes;
- a strict boundary between an `intended_stock_id` candidate and a backend
  `LabStockSolution.id`;
- the documentary fields required for bottle/lot, inventory-to-backend stock
  mapping, lot-specific density or exact weighed-stock-mass conversion, child
  preparation, and sub-10 µL route evidence;
- the three exact required child preparations and three exact sub-10 µL rows;
- empty canonical evidence arrays and false operational authority.

The deterministic evaluator is:

```text
engine/experiments/checkpoint6_readiness.py
SHA-256 ecc1ebc5c79c761be615876e8bd6c9862eebe03b0ca0868f39d11bd3b0cea19f
```

It reruns and verifies the pinned Checkpoint 5 evaluation, checks all governed
source bytes, derives a 63-row intake census, and fails closed on authority,
evidence, implementation, prerequisite, identity-boundary, dimensional, or
hash drift. It imports no backend operational service and performs no database
or filesystem write.

The durable shortlist/job result now includes a
`checkpoint6_documentary_intake` receipt. Its capability fingerprint binds the
Checkpoint 6 manifest/evaluator and the existing physical-lineage service,
schema, model, and migration. This does not turn shortlist evaluation into a
stock-binding operation.

## Current documentary census

| Evidence class | Complete | Missing | Required scope |
|---|---:|---:|---:|
| Candidate stock row identified | 63 | 0 | 63 |
| Bottle/lot receipt | 0 | 63 | 63 |
| Candidate-to-backend stock mapping receipt | 0 | 63 | 63 |
| Liquid conversion receipt | 0 | 62 | 62 liquid rows |
| Direct solid-mass row | 1 | 0 | 1 Ambrox Super row |
| Child-stock preparation receipt | 0 | 3 | rows 31, 59, 63 |
| Sub-10 µL route receipt | 0 | 3 | rows 20, 43, 68 |
| Complete per-row documentary preconditions | 0 | 63 | 63 |
| Physical binding eligible | 0 | 63 | 63 |
| Build-plan bindings | 0 | — | none authorized |
| Inventory reservations | 0 | — | none authorized |

Required child preparations remain:

1. Row 31, Heliotropal / piperonal: parent candidate
   `inventory:v5:593f575b080f30401f9b`, target `0.1 W_W` in DPG.
2. Row 59, Black Pepper EO: parent candidate
   `inventory:v5:4bb69da9b62fe8fbd8bb`, target `0.1 V_V` in ethanol.
3. Row 63, Nutmeg EO: parent candidate
   `inventory:user-20260830:caa7c7f7418d43c86660`, target `0.1 V_V` in
   ethanol.

The sub-10 µL rows are Haitian Vetiver EO, Linalool Oxide, and Rosemary EO,
each at a nominal 5 µL. The intake records the missing route receipts; it does
not select, prepare, or authorize a dilution.

## Existing operational interface audit

The current backend already supplies useful arithmetic and ordering
invariants, including finite decimals, basis-specific preparation quantities,
preparation conservation, exact stock fraction/basis matching, density plus
provenance for volume binding, complete all-line binding, basket-first order,
and append-only false-authority receipts.

It is not yet an admissible automatic bridge from the R6 inventory candidates:

1. Inventory candidate IDs do not automatically identify backend stock rows.
2. Plan-level stock-lineage and release-authority references are unchecked
   strings at the current boundary.
3. A per-line preparation receipt is optional when no receipt is supplied.
4. Per-row bottle and lot evidence is not represented by the line-binding
   input.
5. Carrier provenance is not resolved against a canonical receipt.
6. Density provenance is caller text rather than a receipt-bound identity.
7. The documented exact-target-weighed-stock-mass route is not accepted by the
   current volume binder.
8. Requesting the next compounding command creates a compounding-run record;
   it is state-changing and therefore outside this read-only checkpoint.

Because a physical binding is append-only and unique, creating one before
these documentary gaps are closed would turn unresolved assumptions into
durable operational state.

## Active blockers

```text
HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING
HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED
BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING
```

These blockers are not treated as software failures. They are truthful physical
input and authority boundaries.

## Authority and side effects

Only recording the Checkpoint 6 intake contract is authorized. Every other
authority is false, including evidence admission, stock preparation,
reservation, physical experiment, compounding, purchase, inventory mutation,
physical formula mutation, safety, and release.

Observed side effects are all false:

```text
backend_record_created          = false
build_plan_created              = false
physical_binding_created        = false
prepared_stock_receipt_created  = false
reservation_created             = false
compounding_run_created         = false
mixer_command_created           = false
transfer_record_created         = false
inventory_modified              = false
physical_formula_modified       = false
```

## Verification

Focused checks completed on the current worktree:

- Checkpoint 5 + Checkpoint 6 evaluator tests: `20 passed`.
- Checkpoint 3 through Checkpoint 6 readiness tests: `41 passed`.
- Backend engine-job unit tests: `15 passed`.
- Backend physical-lineage unit/API plus engine-job regression tests:
  `20 passed`.
- Root Ruff for the new evaluator/test: passed.
- Backend Ruff for the changed services/test: passed.
- Root mypy for the new evaluator: passed.
- Backend mypy for the changed services: passed.
- Python compile checks for all changed Python surfaces: passed.
- Quick project verification passed 9 checks and failed the pre-existing broad
  formula-artifact validation because the dirty worktree contains stale or
  quarantined formula artifacts. Golden output bytes were unchanged. This is
  not promoted to a repository completion or release pass.
- Scoped `git diff --check` for every Checkpoint 6 file: passed. The unscoped
  command could not traverse unrelated pre-existing verification scratch
  paths because Windows returned permission errors.

No full repository verifier, model training, formula pipeline execution,
inventory reservation, physical compounding, sensory trial, safety review, or
release review was performed or implied.

## Next admissible boundary

The future physical-readiness state is
`PASS_CP6_PHYSICAL_READINESS_BOUND_NOT_COMPOUNDED`, but it may not be emitted
until all 63 rows have admitted bottle/lot and backend-stock mapping receipts,
all 62 liquid rows have an admitted conversion route, the three child stocks
and three sub-10 µL routes have admissible receipts, the Checkpoint 5
prerequisite is genuinely satisfied, and any necessary operational-interface
changes have their own reviewed authority and tests.

Even that future state would mean “documented and bound, not compounded.” It
would not grant mixer-command, transfer, safety, regulatory, sensory, or
release authority.
