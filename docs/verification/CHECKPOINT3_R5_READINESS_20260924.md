# Checkpoint 3 R5 physical-readiness receipt — 2026-09-24

> Baseline ancestry was superseded on 2026-09-26 by
> `CHECKPOINT3_R5_STANDALONE_BASELINE_20260926.md`. R5 is now the standalone
> baseline; missing R4 bytes remain historical evidence but are no longer a
> readiness blocker. The physical and scientific holds below remain historical
> evidence of the 2026-09-24 evaluation.

Status: `CHECKPOINT3_SOFTWARE_COMPLETE_PHYSICAL_READINESS_HOLD`

Checkpoint 3 now has a deterministic, read-only readiness contract for the
Lavande Ambre Profond R5 design comparator. The contract is intentionally
non-executable: it inventories candidate stock relationships, verifies current
input fingerprints, freezes the minimum measurement schema, and returns the
exact unresolved conditions without creating a build plan, reservation, mixer
command, transfer, prepared-stock receipt, formula change, inventory change, or
physical instruction.

This is a successful fail-closed Checkpoint 3 software outcome. It is not a
successful physical-readiness outcome and does not authorize compounding,
experimentation, evidence admission, safety, purchase, regulatory, or release
action.

## DeepMimo advisory review

One bounded, non-sensitive, read-only architecture packet was sent to the local
DeepMimo endpoint after its health and model surfaces were checked. The receipt
reported:

- service health: `ok`
- advertised response model: `deepmimo`
- response model: `deepmimo`
- provider: `deepseek`
- backend model: `deepseek-flash`
- fallback count: `0`
- provider calls: `1`
- finish reason: `stop`

DeepMimo recommended the smallest Checkpoint 3 implementation: an immutable
protocol artifact, a pure deterministic evaluator, and focused contract tests,
reusing the Checkpoint 2 durable-job surface rather than adding another database
subsystem. The parent task verified all claims locally before implementation.
One advisory labeling error was rejected: DeepMimo described
`027ec1cf...` as the governance-manifest hash, but it is the source-workbook
hash. The design-comparator JSON and workbook remain separately fingerprinted.

DeepMimo did not receive or gain inventory mutation, formula mutation,
compounding, scientific-promotion, safety, purchase, or release authority.

## Frozen inputs and result

- Design-comparator JSON SHA-256:
  `d7f5904bd9437cb61589a1a535423eedb6786641ccc70f109d3e1516bc222f86`
- Source workbook SHA-256:
  `027ec1cf8712c6aaac123d896942eee308efa18bea9056da975566e095bc3e67`
- Canonical formula-row SHA-256:
  `28284674560179b536f2e797a3b1a50ef0421e61435132f47704cda590ead15e`
- Checkpoint 3 protocol SHA-256:
  `d11e6cc22688c9249a9799073eb58817d4b24a9c3519d408949984208538c274`
- Current `inventory.txt` SHA-256:
  `0b5642c9489678ddc8a077bc1e347123c94d90a1075b901f2c6de954bb737d81`
- Materialized inventory snapshot SHA-256:
  `f81c7b277bb1b56d4b2045c98355754449be11fc9d6f121ce4e8de4539e35d99`
- Materialized inventory overlay SHA-256:
  `d0ee1d77b015152c4ffc76a351a693067bf61475eb71a9bf60aecf3fcb9842a2`
- Expected R4 parent SHA-256:
  `5b0a012b88ca5c1cea45ea8a704cf3b9e5d799d66e9f9d28b2a5d21efa9f4129`
- Deterministic readiness-report SHA-256:
  `0d9b7a9a943c4eca6974337ae17e95dd24820c9708a1c4ac3a0a45533ec85849`

The evaluator reports:

```text
status                         = HOLD
input_integrity_state          = VERIFIED
design_comparator_state        = ADMITTED_DESIGN_ONLY
parent_equivalence_state       = HOLD_PARENT_BYTES_MISSING
stock_binding_state            = HOLD_STOCK_BINDING
constant_total_basis_state     = HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED
intensity_state                = HOLD_EXACT_CURVE_APPLICABILITY
measurement_protocol_state     = FROZEN_SCHEMA_HOLD_EXECUTION_PARAMETERS
pleasantness_state             = NOT_ESTABLISHED
physical_liking_state          = NOT_TESTED
formula_action                 = NO_CHANGE
```

All authority and side-effect fields are `false`.

## Comparator and candidate-stock audit

The comparator remains 63 unique rows: 62 liquid rows totaling exactly
`5,600 µL`, plus one separate `300 mg` Ambrox Super solid row. Mass and
volume are never summed.

Every design row now has exactly one non-executable candidate-audit state:

| Candidate state | Rows |
|---|---:|
| `CANDIDATE_FORM_MATCH` | 43 |
| `CANDIDATE_FORM_CONFLICT` | 3 |
| `CANDIDATE_BASIS_UNRESOLVED` | 6 |
| `CANDIDATE_PREPARATION_REQUIRED` | 3 |
| `NO_AUTHORITY_STOCK` | 6 |
| `CURRENT_TEXT_ONLY_NOT_MATERIALIZED` | 1 |
| `CURRENT_TEXT_SNAPSHOT_CONFLICT` | 1 |

There are 55 read-only candidate stock IDs and zero authoritative build-plan
bindings. Candidate IDs are evidence for reconciliation, never permission to
transfer material.

The five headline stock-form conflicts remain verified:

- R5 Ambrox crystals versus the current `25% w/w` carrier stock.
- R5 neat Vetiveryl Acetate versus the current `10% w/w in DEP` stock.
- R5 Norlimbanol `10% v/v in ethanol` versus the current `10% in DEP` stock
  with unresolved fraction basis.
- No authoritative Aroma&More Lavender 40/42 stock.
- Hay Absolute carrier/fraction basis unresolved and not execution-ready.

The R4 parent bytes were not found in the repository, repository history,
Downloads, Documents, or the inspected Codex attachment store. The evaluator
preserves `HOLD_PARENT_BYTES_MISSING`; it does not reconstruct a parent from R5.

## Exact blocker order

1. `HOLD_PARENT_BYTES_MISSING`
2. `HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING`
3. `AMBROX_FORM_CONFLICT`
4. `VETIVERYL_STRENGTH_CONFLICT`
5. `NORLIMBANOL_CARRIER_BASIS_CONFLICT`
6. `AROMA_AND_MORE_STOCK_NOT_BOUND`
7. `HAY_STOCK_BASIS_UNRESOLVED`
8. `BOTTLE_LOT_AND_HOMOGENEITY_RECEIPTS_MISSING`
9. `HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED`
10. `HOLD_EXACT_CURVE_APPLICABILITY`
11. `HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED`
12. `PLEASANTNESS_NOT_ESTABLISHED`
13. `PHYSICAL_LIKING_NOT_TESTED`

The measurement contract defines separate physical-release, sensory-intensity,
character, pleasantness, and liking endpoints. It requires explicit application,
surface, environmental, collection, calibration, replication, aging, blinding,
and missingness controls. It remains non-executable until its scale, substrate,
schedule, instrument method, reviewer or panel scope, and physical-experiment
authority are separately supplied.

## Durable-job integration

The Checkpoint 3 protocol is included in the durable engine capability
fingerprint. A `SHORTLIST_EVALUATION` job now fails closed if the protocol is
missing, malformed, grants authority, or no longer points to the exact R5
comparator. The current successful execution path still returns a withheld,
`NO_CHANGE` result and exposes the Checkpoint 3 readiness state with all
authority flags false.

## Verification

- Root readiness and comparator tests: `11 passed in 0.40s`.
- Backend durable-job tests: `9 passed in 20.69s`.
- Root Ruff: passed.
- Root mypy for the evaluator: passed.
- Backend Ruff for the changed job surfaces and test: passed.
- Backend mypy for both changed job services: passed.
- Quick project verification: nine selected checks passed; the overall quick
  gate remained `FAIL` solely because `formula-artifact-validation` reported
  the repository's broader artifact backlog (`414 NONE`, `14 QUARANTINED`,
  `36 STALE`, `1 TAMPERED`, and `50 UNBOUND_LEGACY`). The single tampered
  artifact is `Prada_LHomme_Architecture_Control_30mL_EdT.md`, already
  quarantined with release authority false. No artifact was rebound or
  rewritten as part of Checkpoint 3.

The first backend attempt did not execute tests because the repository's shared
pytest scratch parent contained a locked directory. The same focused suite was
rerun with a fresh, explicit, repository-local base directory and passed 9/9.
No existing scratch directory was deleted or modified to force the result.

The quick verifier therefore does not support merge- or release-level
readiness. It does show that engine compile, the canonical lint and typecheck
slices, scientific audit, material validation, knowledge rules, golden formula
regression, golden API regression, and the golden fixture lock all passed. The
artifact backlog remains a separate explicit repository-level blocker.

## Checkpoint boundary

Checkpoint 3 is complete only as a software and evidence-boundary checkpoint.
The formula stays unchanged and R5 stays design-only. Progress to a physical
checkpoint requires separately authorized recovery of the exact R4 parent or a
documented waiver, live stock/lot and prepared-stock reconciliation for all 63
rows, a common active-mass basis, and completed execution parameters for an
applicable measurement protocol. Until then, the correct result is `HOLD` and
`NO_CHANGE`.
