# Checkpoint 4 — Lavande Ambre Profond R6 AIMI design successor

Date: 2026-09-26
Status: `SOFTWARE_COMPLETE_DESIGN_SUCCESSOR_ADMITTED_PHYSICAL_READINESS_HOLD`

## Outcome

The user selected the owned Givaudan AIMI stock as the replacement path for the
depleted R5 Methyl Ionone Gamma Coeur row. Exact R5 remains the immutable
standalone comparator. The result is a separately identified design successor:

```text
successor_id                 = lavande-ambre-profond-r6-aimi-design-successor-20260926
design_successor_state       = ADMITTED_DESIGN_SUCCESSOR_ONLY
parent_lineage_state         = EXACT_R5_STANDALONE_BASELINE_BOUND
substitution_state           = AIMI_SELECTED_NOMINAL_50_UL_TRANSFER
active_equivalence_state     = NOT_CLAIMED_INTENDED_MATERIAL_CHANGE
formula_action               = DESIGN_SUCCESSOR_RECORDED
physical_build_state         = HOLD_STOCK_BINDING_AND_PREPARATION_LINEAGE
input_integrity_state        = VERIFIED
```

## Exact design delta

Only source row 47 changes:

| Field | R5 standalone baseline | R6 AIMI design successor |
|---|---|---|
| Basket | B5 | B5 |
| Material | Methyl Ionone Gamma Coeur | Givaudan AIMI |
| Required stock | Same neat IFF stock used in the iris formula | Owned Givaudan AIMI, neat/as supplied |
| Nominal transfer | 50 µL | 50 µL |
| Stock fraction | neat | neat |

The 50 µL transfer is the minimum-change engineering implementation of the
user-selected material, not a claim of chemical, active-dose, OAV, intensity,
or sensory equivalence. All 62 other rows are unchanged. The successor remains
63 rows: 62 liquid transfers totaling exactly 5,600 µL plus a separate 300 mg
Ambrox Super solid row. The two-lavender block remains 700 µL Bontoux and
300 µL Aroma&More, preserving the fixed 70:30 split.

No ppm w/w value is reported for the AIMI row because the owned bottle's exact
chemical identity and density are not independently bound. Consequently no
exact compatible ODT or OAV is asserted. A nominal supplier reference cannot
replace those missing applicability inputs.

## Stock and reference boundary

The selected current stock is:

```text
label                         = Givaudan AIMI
stock_id                      = inventory:user-20260904:a45ff6250b56cec5bbad
fraction                      = 1.0
fraction_basis                = neat
carrier                       = none
physical availability         = owned
quantitative stock dosing     = ready
nominal property model ready  = false
```

The local PerfumersWorld archive for SKU `3IW00300` identifies an Alpha
Isomethyl Ionone reference, CAS `127-51-5`, and describes violet, orris,
powdery, floral, and woody character. That supports the target-linked design
hypothesis. It does not prove that the user's Givaudan-labeled bottle is the
same product, assay, isomer distribution, or property set. Therefore:

```text
chemical_identity_state = HOLD_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED
headspace_state         = HOLD_EXACT_PRODUCT_RELEASE_APPLICABILITY
odt_oav_state           = HOLD_EXACT_PRODUCT_THRESHOLD_APPLICABILITY
intensity_state         = HOLD_EXACT_CURVE_APPLICABILITY
character_state         = TARGET_LINKED_HYPOTHESIS_ONLY
pleasantness_state      = NOT_ESTABLISHED
physical_liking_state   = NOT_TESTED
```

## Current blockers

The depleted-Methyl-Ionone blocker is retired for the R6 design successor. The
remaining ordered blockers are:

1. `HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING`
2. `HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED`
3. `BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING`
4. `HOLD_AIMI_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED`
5. `HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING`
6. `HOLD_EXACT_CURVE_APPLICABILITY`
7. `HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED`
8. `PLEASANTNESS_NOT_ESTABLISHED`
9. `PHYSICAL_LIKING_NOT_TESTED`

## Pinned evidence

| Artifact | SHA-256 |
|---|---|
| Direct AIMI substitution decision | `d65af483aaaaad6beebfb5d827fc3e569ee15123b98e7bc2e4277c3a8390c944` |
| R6 AIMI successor manifest | `1a0ce117fa67f98c854b4d849131abcea0f836f16092c1e4eefb1a9dfa5e2fd1` |
| R5 parent comparator | `d7f5904bd9437cb61589a1a535423eedb6786641ccc70f109d3e1516bc222f86` |
| R5 parent canonical rows | `28284674560179b536f2e797a3b1a50ef0421e61435132f47704cda590ead15e` |
| R6 successor canonical rows | `40889e8a43a780bf60d35a10fe4861a56f20d1a2a66e72141a5ceb8b8000eb4b` |
| Deterministic Checkpoint 4 report | `b1e56efff97c852931c5ff0eca97eb2fa240d8d04e82142a04fc9433766e8011` |

## Durable execution and authority

The durable engine-job capability fingerprint and shortlist executor pin the
user decision and R6 successor manifest. A missing, malformed, hash-drifted, or
authority-escalating successor fails closed. The asynchronous result exposes
Checkpoint 4 state but remains withheld on the unresolved constant-total and
scientific-applicability inputs.

The successor record grants no evidence-admission, experiment, compounding,
purchase, inventory-mutation, physical-formula-mutation, safety, regulatory, or
release authority. No build plan, reservation, mixer command, transfer,
prepared-stock receipt, or physical instruction was created.

## Focused verification

- Checkpoint 4 evaluator tests: `8 passed`.
- Combined R5/R6 readiness, stock, comparator, and name-resolution tranche:
  `64 passed`.
- Backend durable engine-job tests: `11 passed`.
- Root and backend focused Ruff checks: passed.
- Root and backend focused mypy checks: passed.
- Python compilation, JSON parsing, deterministic report replay, and diff
  hygiene: passed.
- Quick project verification passed engine compile, canonical lint/type checks,
  scientific audit, material-data validation, knowledge-rule validation, golden
  formula/API regression, and the golden lock. Its global gate remains `FAIL`
  solely on the repository's pre-existing historical formula-artifact backlog;
  no artifacts were rebound or promoted by this checkpoint.
