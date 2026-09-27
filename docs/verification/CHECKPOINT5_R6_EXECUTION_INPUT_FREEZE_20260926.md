# Checkpoint 5 — R6 execution-input freeze and gap census

Date: 2026-09-26
Status: `SOFTWARE_COMPLETE_INPUT_COLLECTION_HOLD`

## Outcome

Checkpoint 5 is complete as a software and evidence-boundary checkpoint. It
freezes the exact non-executing input contract for the Lavande Ambre Profond R6
AIMI design successor, joins every design row to one current-inventory stock
candidate, records every still-missing physical input, and makes that contract
part of the durable engine-job capability fingerprint.

The correct outcome remains a hold:

```text
checkpoint5_state             = SOFTWARE_COMPLETE_INPUT_COLLECTION_HOLD
input_completion_state        = HOLD_CP5_INPUTS_INCOMPLETE
input_integrity_state         = VERIFIED
formula_action                = DESIGN_SUCCESSOR_UNCHANGED
candidate_stock_rows          = 63 / 63
physical_binding_eligible     = 0 / 63
constant_total_basis          = active_mass_g
constant_total_amount         = UNRESOLVED
measurement_execution_ready  = false
formula_modified              = false
inventory_modified            = false
```

This is a successful truthful result. It is not a physical-build readiness
claim and does not convert documentary stock candidates into executable stock
bindings.

## Frozen design identity

The input contract is bound to the existing R6 successor and preserves its
single design change:

- Source row 47 is Givaudan AIMI, 50 µL, replacing the depleted R5 Methyl
  Ionone Gamma Coeur row.
- No chemical, active-dose, OAV, intensity, or sensory equivalence is claimed.
- All other design rows remain unchanged.
- There are 63 rows: 62 liquid rows totaling exactly 5,600 µL and one separate
  300 mg Ambrox Super crystal row.
- The two-lavender design block remains fixed at 700 µL Bontoux and 300 µL
  Aroma&More, a 70:30 nominal-volume split.
- Mass and volume are never added to produce a fictional common total.

No ppm w/w or OAV result is generated for R6 at this checkpoint. The required
row-specific mass conversions and applicable gas-concentration inputs do not
exist yet, and supplying a liquid transfer directly to a gas-response curve
would violate the frozen dimensional contract.

## Exact row census

| Census item | Result |
|---|---:|
| R6 design rows | 63 |
| Rows with one intended current-inventory candidate | 63 |
| Direct/form-matched candidates | 45 |
| Existing-stock candidates with incomplete receipt evidence | 14 |
| Required child-stock preparations | 3 |
| AIMI bottle-specific candidate with reference use withheld | 1 |
| Liquid rows | 62 |
| Separate solid-mass rows | 1 |
| Liquid rows missing lot-specific density or exact target weighed mass | 62 |
| Rows with verified bottle/lot evidence complete in this contract | 0 |
| Rows eligible for a physical build-plan binding | 0 |

The census intentionally distinguishes a candidate stock from an executable
binding. An inventory label, dilution, and carrier can make a row a useful
candidate without establishing bottle lot, preparation lineage, density,
weighed transfer, reservation, or physical authority.

## AIMI applicability decision

The owned Givaudan AIMI stock is governed as:

```text
stock_id                       = inventory:user-20260904:a45ff6250b56cec5bbad
scope_state                    = BOTTLE_SPECIFIC_EMPIRICAL_REQUIRED
reference_disposition          = REFERENCE_NOT_USED_FOR_QUANTITATIVE_APPLICABILITY
reference_linked_properties    = prohibited
family_equivalence             = prohibited
exact_curve_applicability      = HOLD_BOTTLE_SPECIFIC_MEASUREMENTS_MISSING
```

This reframes the former bottle-to-reference identity blocker without
pretending it was empirically resolved. Supplier or family descriptions may
support a qualitative design hypothesis, but they cannot donate density,
threshold, release, or response-curve values to the owned bottle.

## Constant-total and transfer boundary

The future comparison basis is `active_mass_g`, interpreted as active odorant
mass under verified w/w conversions. The total is deliberately not a
user-supplied round number: it must be derived from verified row inputs.

For each of the 62 liquid rows, one of these routes is required before deriving
the common mass total:

1. a lot-specific density with provenance; or
2. the exact weighed stock mass used for that transfer.

Generic densities are forbidden. The 300 mg Ambrox Super crystal row remains a
direct mass dimension and is never converted into an inferred volume.

Three nominal 5 µL transfers are also explicitly held because they are below
the governed 10 µL direct-transfer floor:

| Source row | Material | Nominal transfer | Allowed future route |
|---:|---|---:|---|
| 20 | Haitian Vetiver EO | 5 µL | governed child dilution or qualified direct measurement |
| 43 | Linalool Oxide | 5 µL | governed child dilution or qualified direct measurement |
| 68 | Rosemary EO | 5 µL | governed child dilution or qualified direct measurement |

No route was selected and no active dose was rebased in Checkpoint 5.

## Required working-stock preparations

The inventory census identifies exactly three intended working stocks that do
not yet have an executable child-preparation receipt:

| Source row | Material | Required child stock |
|---:|---|---|
| 31 | Heliotropal / piperonal | 10% w/w in DPG |
| 59 | Black Pepper EO | 10% v/v in ethanol |
| 63 | Nutmeg EO | 10% v/v in ethanol |

These are requirements, not preparation instructions or evidence that a stock
was prepared. A later authorized preparation receipt must bind the exact parent
stock, carrier, fraction basis, measured quantities, conservation, homogeneity,
label, operator, and timestamp.

## Frozen R6 measurement schema

The protocol separates four physical sample roles:

- R6 primary research sample;
- an independently prepared R6 replicate;
- carrier or matrix blank; and
- a justified physical reference, only if one is actually available.

The documentary R5 workbook is not treated as a physical comparator. Blotter
and skin remain separate domains. Physical release, sensory intensity,
character, pleasantness, and liking remain separate endpoints; beauty is a
prohibited derived endpoint.

Twenty-five execution parameters remain unresolved:

- Physical: authorized sample scale; application amount and basis; surface
  area; substrate; temperature; relative humidity; airflow; enclosure;
  sampling schedule; headspace method; available instrument method;
  instrument and matrix calibration; replicate structure; aging; and storage.
- Sensory: qualified panel or reviewer scope; randomized codes; blinding;
  balanced order; predeclared scales; rest intervals; session identity; and
  retained missingness.

Accordingly, no experiment, headspace collection, sensory evaluation, curve
admission, pleasantness model, or liking assessment was executed.

## Blocker ownership after Checkpoint 5

The nine inherited R6 blockers are assigned exactly once so later checkpoints
do not blur software readiness with physical or scientific authority.

### Checkpoint 5 — recorded disposition

- `HOLD_AIMI_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED` is reframed as
  bottle-specific empirical scope; external reference properties are not used.
- `HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING` remains unresolved
  at row level and no active-mass total is fabricated.
- `HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED` now has a frozen
  schema and an explicit 25-field input list, but remains unresolved.

### Checkpoint 6 — physical lineage inputs

- `HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING`
- `HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED`
- `BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING`

### Checkpoint 7 — release and intensity applicability

- `HOLD_EXACT_CURVE_APPLICABILITY`

### Checkpoint 8 — sensory evidence

- `PLEASANTNESS_NOT_ESTABLISHED`
- `PHYSICAL_LIKING_NOT_TESTED`

## Durable job integration

`SHORTLIST_EVALUATION` now requires the Checkpoint 5 protocol in addition to
the R5 comparator, Checkpoint 3 protocol, and R6 successor. The capability
fingerprint includes the CP5 protocol and its underlying measurement schema.

The executor fails closed with distinct stable states when CP5 is unavailable,
invalid, drifted, or authority-escalating. A successful read still returns an
unordered, empty shortlist with
`HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING`; it cannot promote a
candidate while the active-mass basis is underived.

## Pinned evidence

| Artifact | SHA-256 |
|---|---|
| R6 AIMI successor manifest | `1a0ce117fa67f98c854b4d849131abcea0f836f16092c1e4eefb1a9dfa5e2fd1` |
| R6 successor canonical rows | `40889e8a43a780bf60d35a10fe4861a56f20d1a2a66e72141a5ceb8b8000eb4b` |
| Checkpoint 5 input protocol | `8707eecdc09a360b9a09d9b363bc7476ed9024a5f78ffe10d1b2732a84d24af0` |
| Deterministic Checkpoint 5 report | `4ea649f77f6740abc5a8e03a85ed00e0f69baddc45b4e74a668a5e252af85592` |
| Inventory text pinned by the protocol | `0546ab83862557a4e604536f6282f3978bf24351a29848e0e91292c71d90bdf4` |
| Materialized inventory snapshot | `f81c7b277bb1b56d4b2045c98355754449be11fc9d6f121ce4e8de4539e35d99` |
| Materialized inventory overlay | `0bccf890ee05487b20daca94d02c65103c2a22ed4c6435ba8cb311cd041575fb` |

## Authority and side effects

The only affirmative authority is permission to record this Checkpoint 5 input
contract. Evidence admission, stock preparation, reservation, experimentation,
compounding, purchasing, inventory mutation, physical-formula mutation, safety,
regulatory, and release authority remain false.

No build plan, physical stock binding, reservation, mixer command, transfer,
prepared-stock receipt, physical sample, formula mutation, inventory mutation,
measurement, or sensory evaluation was created.

## Verification

- Checkpoint 5 evaluator invariants: `9 passed`.
- Combined R5 comparator, Checkpoint 3, Checkpoint 4, Checkpoint 5, and relevant
  stock-governance tranche: `60 passed`.
- Durable engine-job tests: `13 passed`, including absent, malformed, drifted,
  and authority-escalated CP5 inputs.
- Focused root and backend Ruff checks: passed.
- Focused root and backend mypy checks: passed.
- Python compilation, JSON parsing, deterministic report replay, and source
  hash checks: passed.
- Quick project verification passed engine compile, canonical lint/type checks,
  scientific audit, material-data validation, knowledge-rule validation,
  golden formula/API regression, and the golden lock. The quick completion gate
  remains `FAIL`; its only executed failing check was
  `formula-artifact-validation`, which reports the existing historical artifact
  backlog. The checks omitted by quick mode were not represented as passing,
  and no artifact was rebound or promoted by this checkpoint.

## Next checkpoint boundary

Checkpoint 6 can begin only as an authority-safe physical-lineage intake. It
must collect and validate bottle/lot evidence, exact row conversion evidence,
and the three missing child-stock preparation receipts before any build-plan
line can become eligible. It must not prepare stocks, reserve inventory, emit a
mixer command, or compound R6 unless the user separately authorizes those
physical actions.
