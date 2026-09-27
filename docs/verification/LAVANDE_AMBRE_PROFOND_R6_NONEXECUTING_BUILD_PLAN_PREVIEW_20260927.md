# Lavande Ambre Profond R6 — non-executing personal build-plan preview

Date: 27 September 2026

Status: `PASS_PERSONAL_NONEXECUTING_PLAN_DRAFT_WITH_TARGETED_HOLDS`

This document is a planning view, not a mixer instruction, stock-preparation
recipe, reservation, transfer record, or authorization to compound. It leaves
the formula and inventory unchanged.

## Decision

The current information is sufficient to preserve a practical personal-use R6
plan without demanding complete commercial or scientific lineage for every
bottle. It is not sufficient to issue physical commands. The remaining
execution issues are specific and visible rather than a blanket rejection of
the formula:

- three required working stocks do not yet exist;
- three nominal `5 µL` rows are below the reported `10 µL` pipette minimum;
- the exact metering capability for the `300 mg` solid operation is not
  established from the balance description;
- there is no supported route for exact active-mass conversion of every
  volume-dosed `w/w` stock; and
- no explicit physical-compounding authority was granted.

Unknown bottle lots and missing supplier receipts remain relevant to future
scientific or commercial claims, but they do not invalidate this personal
planning preview.

```text
personal_plan_state          = PASS_NONEXECUTING_DRAFT
all_rows_execution_bound     = false
physical_build_state         = HOLD_TARGETED_PREPARATION_AND_TRANSFER_ROUTES
constant_active_mass_state   = HOLD_NO_DENSITY_OR_TRANSFER_MASS_ROUTE
formula_action               = NO_CHANGE
formula_modified             = false
inventory_modified           = false
reservation_created          = false
mixer_commands_created       = false
```

## Frozen formula identity

The authoritative row set is not duplicated or rewritten here. The plan is the
63-row R5 comparator plus the single admitted R6 substitution at source row 47:

| Frozen input | SHA-256 |
|---|---|
| `data/governance/lavande_ambre_profond_r5_design_comparator_20260923.json` | `d7f5904bd9437cb61589a1a535423eedb6786641ccc70f109d3e1516bc222f86` |
| R5 canonical rows | `28284674560179b536f2e797a3b1a50ef0421e61435132f47704cda590ead15e` |
| `data/governance/lavande_ambre_profond_r6_aimi_design_successor_20260926.json` | `1a0ce117fa67f98c854b4d849131abcea0f836f16092c1e4eefb1a9dfa5e2fd1` |
| R6 canonical rows | `40889e8a43a780bf60d35a10fe4861a56f20d1a2a66e72141a5ceb8b8000eb4b` |
| `inventory.txt` used for this preview | `0546ab83862557a4e604536f6282f3978bf24351a29848e0e91292c71d90bdf4` |
| user input and authority receipt | `c4c1c4a0ffe17c46863586b78749a06a980c94a06416b87885f03b5b402e6247` |

The R6 row set contains 62 liquid operations totaling exactly `5,600 µL` and
one separate Ambrox Super operation of `300 mg`. Those amounts are never added
together as though mass were volume. The stated `6 mL` compound endpoint
remains a physical endpoint; this preview does not infer a solid displacement
or prescribe a fixed TEC top-up.

## Practical row classification

| Class | Rows | Planning state | What remains |
|---|---:|---|---|
| Ordinary liquid rows, nominal dose `10–700 µL` | 56 | `PLAN_REFERENCE_READY` | Later explicit authority and normal at-use stock check |
| Required but unprepared child stocks | 3 | `PREPARATION_REQUIRED` | A separately authorized preparation and its label/receipt |
| Neat liquid rows at `5 µL` | 3 | `CHILD_ROUTE_REQUIRED` | A governed dilution route; no recipe is selected here |
| Ambrox Super crystals, `300 mg` | 1 | `SEPARATE_MASS_OPERATION_PLANNED` | Confirm suitable balance resolution at execution time |

The reported pipette range covers every ordinary liquid row by nominal dose;
this is a range check, not a calibration certificate. User-confirmed stock
labels, forms, bases, carriers, and homogeneity are sufficient for this
personal preview. They are not silently promoted into lot-specific assays.

## Targeted holds

### Working stocks that do not yet exist

| Source row | Basket | Formula material | Required working stock | Current parent state | Decision |
|---:|---|---|---|---|---|
| 31 | B3 | Heliotropal / piperonal | `10% w/w in DPG` | neat parent owned | `PREPARATION_REQUIRED` |
| 59 | B6 | Black Pepper EO | `10% v/v in ethanol` | neat parent owned | `PREPARATION_REQUIRED` |
| 63 | B6 | Nutmeg EO | `10% v/v in ethanol` | neat Aroma&More parent owned | `PREPARATION_REQUIRED` |

No preparation quantities are calculated and no preparation is authorized by
this document.

### Transfers below the pipette minimum

| Source row | Basket | Material | Nominal neat dose | Decision |
|---:|---|---|---:|---|
| 20 | B1 | Haitian Vetiver EO | `5 µL` | `GOVERNED_CHILD_DILUTION_REQUIRED_RECIPE_NOT_SELECTED` |
| 43 | B4 | Linalool Oxide | `5 µL` | `GOVERNED_CHILD_DILUTION_REQUIRED_RECIPE_NOT_SELECTED` |
| 68 | B6 | Rosemary EO | `5 µL` | `GOVERNED_CHILD_DILUTION_REQUIRED_RECIPE_NOT_SELECTED` |

Direct transfer is not supported by a pipette whose reported minimum is
`10 µL`. A future child-dilution route must preserve the intended active dose
and record the added carrier. This preview deliberately does not choose the
dilution fraction, carrier, preparation quantity, or recipe.

### Stock facts accepted for planning but not for stronger claims

- Norlimbanol Dextro: `10% w/w in DPG`, homogeneous, with preparation details
  and lots unknown. This is the current candidate stock fact; it does not prove
  equivalence to the frozen design row's older wording.
- Hay Absolute: `10% w/w in DPG`, homogeneous, with preparation details and
  lots unknown.
- Lavender 40/42 Aroma&More: owned neat stock, previously recorded as `10 mL`
  and homogeneous; lot and label receipt remain unknown.
- Givaudan AIMI: owned quantity reported as `4 g`; the PerfumersWorld Alpha
  Methyl Ionone document remains a product reference, not proof of the owned
  bottle's exact identity.
- Ambrox Super crystals: PerfumersWorld supplier reported; bottle size, lot,
  and remaining mass are unknown.

These unknowns are retained. They should not be asked again unless the user
requests an action or claim that genuinely depends on them.

## Future sequence contract

If physical execution is separately authorized after the targeted holds are
closed, the server-owned sequence remains:

1. keep the Ambrox solid as a separate mass operation;
2. process baskets in order `B1 → B2 → B3 → B4 → B5 → B6`;
3. within each basket, process liquid rows from highest to lowest nominal raw
   transfer;
4. use exactly the R6 row identity above, including Givaudan AIMI at source row
   47;
5. never convert stock amount to active mass without an admitted measured mass
   or lot-specific density route;
6. never restart a completed logical plan or repeat a receipted transfer; and
7. stop on stock, order, amount, or formula-hash drift.

No item in this sequence grants compounding, safety, regulatory, scientific,
commercial, or release authority.
