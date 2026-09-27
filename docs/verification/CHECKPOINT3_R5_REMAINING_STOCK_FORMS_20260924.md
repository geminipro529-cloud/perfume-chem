# Checkpoint 3 — R5 Remaining Stock Forms and Mass-Basis Correction

> Baseline ancestry was superseded on 2026-09-26 by
> `CHECKPOINT3_R5_STANDALONE_BASELINE_20260926.md`. This receipt remains the
> authority for the stock-form and depletion facts recorded below.

Date: 2026-09-24
Scope: read-only inventory authority and R5 readiness reconciliation
Result: `VERIFIED_HOLD`

## Direct user facts admitted

The following current prepared stocks are mass-fraction solutions:

| Material | Current stock |
|---|---|
| Labdanum Resinoid | 10% w/w in DPG |
| Tonka Bean Absolute | 10% w/w in DPG |
| Olibanum Resinoid | 50% w/w in DPG |
| Opoponax Resinoid | 50% w/w in DEP |
| Mimosa Absolute | 10% w/w in DPG |

The Tonka confirmation supersedes the older nominal-volumetric record. The five
stocks are calculation-ready as mass-fraction facts, but they remain held from
physical execution until their bottle/lot and preparation lineage is complete.

The following exact products were reported owned in their correct neat or
as-supplied form and ready for raw transfer: Ethyl Linalool, Geranyl Acetate,
Spike Lavender EO, Linalool Oxide, Hedione HC, and Cedrat FCF Sicilian. Their
current records still fail closed on missing bottle/lot or label evidence.

Methyl Ionone Gamma Coeur is depleted. No family, alias, or Givaudan AIMI
substitution was admitted.

Heliotropal/piperonal, Black Pepper EO, and Nutmeg EO are present neat. This
does not create the separately required R5 working stocks. Preparation remains
required and was not authorized by this reconciliation.

## Frozen R5 readiness outcome

- Required design rows: 63.
- Exact read-only stock candidates: 62.
- Exact required stock depleted: 1, Methyl Ionone Gamma Coeur.
- Candidate state counts:
  - `CANDIDATE_FORM_MATCH`: 45
  - `CANDIDATE_PREPARATION_REQUIRED`: 3
  - `CANDIDATE_RECEIPT_INCOMPLETE`: 14
  - `REQUIRED_STOCK_DEPLETED`: 1
- Build-plan-bound rows: 0.
- Formula action: `NO_CHANGE`.
- Inventory quantity mutation: none.
- Formula mutation: none.
- Compounding, purchase, evidence-admission, safety, and release authority:
  all false.

The former fraction-basis uncertainty for the five listed stocks is retired.
The common-total study remains held because selecting `active_mass_g` does not
supply a constant total amount, weighed transfer masses or valid densities for
volume-dosed w/w stocks, or complete receipts for older w/v preparations.

Active blockers, in order:

1. `HOLD_PARENT_BYTES_MISSING`
2. `HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING`
3. `HOLD_REQUIRED_STOCK_DEPLETED_METHYL_IONONE_GAMMA_COEUR`
4. `HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED`
5. `BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING`
6. `HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING`
7. `HOLD_EXACT_CURVE_APPLICABILITY`
8. `HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED`
9. `PLEASANTNESS_NOT_ESTABLISHED`
10. `PHYSICAL_LIKING_NOT_TESTED`

## Pinned artifacts

| Artifact | SHA-256 |
|---|---|
| `inventory.txt`, raw bytes | `0546ab83862557a4e604536f6282f3978bf24351a29848e0e91292c71d90bdf4` |
| `inventory.txt`, normalized text | `1b4324da5a35cebe8c59959e58276d84ac8f2f0e0e6f3239fdef0a4250d8df71` |
| Direct confirmation v3 | `0b76c0480f43ae355c74abd9803850218efcc14773046102f15eab43c63f6178` |
| Current inventory overlay v17 | `0bccf890ee05487b20daca94d02c65103c2a22ed4c6435ba8cb311cd041575fb` |
| Overlay canonical records | `fc2c9e9a355bb407a8d2b9d25c1c0e8b548043d1f158d3cb143b40c292470280` |
| Checkpoint 3 protocol v4 | `f5087e2a575d0ac642cd8617071ff590af82aa56a124c524eb489a7b5838181c` |
| Deterministic readiness report | `0c7760a4607cd4b2f2cf275439b2a5bee93a869b58cc30e07770bc3641e4f14e` |

The materialized current inventory contains 244 owned stock records: 183 marked
execution-ready under their pre-existing stock contracts and 61 held. These
counts describe software authority records, not measured remaining quantities.

## Focused verification

- Root inventory, comparator, and readiness tests: 75 passed.
- Root Ruff check on changed inventory/readiness surfaces: passed.
- Root mypy with explicit package bases: passed for the two changed engine
  modules.
- Backend Ruff: passed for 139 application source files.
- Backend mypy: passed for 139 application source files.
- Backend focused engine-job tests: 10 passed.

No full verifier, formula release gate, optimizer run, model training, mixer
instruction generation, stock preparation, compounding, or sensory test was
performed.
