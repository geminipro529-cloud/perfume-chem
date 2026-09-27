# Checkpoint 3 — R5 standalone-baseline decision

> The selected AIMI successor is recorded in
> `CHECKPOINT4_R6_AIMI_DESIGN_SUCCESSOR_20260926.md`. This receipt remains the
> authority for R5's standalone-baseline decision.

Date: 2026-09-26
Status: `STANDALONE_BASELINE_ACCEPTED_PHYSICAL_READINESS_HOLD`

## Decision

The user designated Lavande Ambre Profond R5 as the standalone baseline. Exact
R4 bytes are therefore not required to identify or evaluate future successors
against R5. The unavailable R4 reference and expected hash remain preserved as
historical evidence, but no R4 equivalence or improvement claim is made.

The user also selected a revised-successor path for the depleted Methyl Ionone
Gamma Coeur row. No substitute, omission, successor identifier, or dose change
has yet been selected or authorized. Exact R5 remains the immutable design
comparator; a future buildable revision must receive a distinct formula
identity.

## Current deterministic state

```text
status                         = HOLD
input_integrity_state          = VERIFIED
design_comparator_state        = ADMITTED_DESIGN_ONLY
baseline_state                 = R5_STANDALONE_BASELINE_ACCEPTED
parent_equivalence_state       = NOT_CLAIMED_STANDALONE_BASELINE
revision_state                 = REVISED_SUCCESSOR_REQUIRED_SPECIFIC_CHANGE_UNRESOLVED
stock_binding_state            = HOLD_STOCK_BINDING
constant_total_basis_state     = HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING
intensity_state                = HOLD_EXACT_CURVE_APPLICABILITY
measurement_protocol_state     = FROZEN_SCHEMA_HOLD_EXECUTION_PARAMETERS
pleasantness_state             = NOT_ESTABLISHED
physical_liking_state          = NOT_TESTED
formula_action                 = NO_CHANGE
```

The retired blocker is:

- `HOLD_PARENT_BYTES_MISSING`

The current ordered blockers are:

1. `HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING`
2. `HOLD_REQUIRED_STOCK_DEPLETED_METHYL_IONONE_GAMMA_COEUR`
3. `HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED`
4. `BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING`
5. `HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING`
6. `HOLD_EXACT_CURVE_APPLICABILITY`
7. `HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED`
8. `PLEASANTNESS_NOT_ESTABLISHED`
9. `PHYSICAL_LIKING_NOT_TESTED`

## Pinned evidence

| Artifact | SHA-256 |
|---|---|
| Direct standalone-baseline decision | `ede92d7c1c9b496ec5da9834493117fdcdd1197bc9ade746b25d3d931bef644d` |
| Checkpoint 3 protocol successor v5 | `6b96354a14c637860155463f20fa996c0cc57c56a00cd0c12156f6a9755ae15c` |
| Deterministic readiness report | `29ad948f03df4b35c14d435f0dc26dc8b2b0fab543a986e73d3bc3728de348be` |
| Historical R4 expected reference | `5b0a012b88ca5c1cea45ea8a704cf3b9e5d799d66e9f9d28b2a5d21efa9f4129` |

The v5 successor pins the v4 protocol rather than rewriting it. The durable
engine-job capability fingerprint and shortlist executor now pin v5 and the
direct decision receipt.

## Authority boundary

All evidence-admission, experiment, compounding, purchase, inventory-mutation,
formula-mutation, safety, and release authority fields remain `false`. This
decision changes ancestry governance only. It does not create a build plan,
reservation, mixer instruction, transfer, prepared-stock receipt, formula
revision, inventory update, sensory result, or release claim.

## Focused verification

- Root Checkpoint 3 readiness tests: `13 passed`.
- Backend durable-engine-job tests: `10 passed`.
