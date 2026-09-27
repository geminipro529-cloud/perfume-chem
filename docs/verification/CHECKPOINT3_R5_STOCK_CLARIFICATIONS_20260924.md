# Checkpoint 3 R5 stock-clarification successor receipt — 2026-09-24

Status: `PARTIAL_BLOCKER_CLOSURE_VERIFIED`

This receipt supersedes only the stock-fact portion of
`CHECKPOINT3_R5_READINESS_20260924.md`. It does not rewrite the original frozen
readiness protocol or its receipt. The original R5 design comparator and formula
rows remain unchanged.

## User-authoritative stock corrections

The direct user message confirms:

- Ambrox Super crystals are physically held.
- Vetiveryl Acetate is neat/as supplied.
- The current Norlimbanol 10% stock uses DPG.
- The current Hay Absolute 10% stock uses DPG.

The resulting inventory successor preserves the previous Ambrox Super 25% w/w
solution as a distinct stock, adds the crystals as a weighed-solid stock,
retires the prior Vetiveryl 10% w/w in DEP record, and replaces the old
Norlimbanol/Hay materializations with carrier-corrected DPG records.

The user did not state whether the Norlimbanol or Hay percentages are w/w or
v/v, did not provide a solution density, and did not confirm solution
homogeneity. Those two records therefore remain `execution_ready=false` with
`fraction_basis=unspecified`.

No formula rebase, dose conversion, transfer, reservation, purchase, physical
compounding, safety, or release action is authorized by these corrections.

## Aroma & More product resolution

The exact public catalog product was identified from the supplier's official
English and Thai pages and its Shopee listing:

```text
brand                       = AROMA & MORE
supplier_product_name       = Lavender 40/42 Essential Oil, France
supplier_reference          = Lav420811P
supplier_claimed_class      = 100% Natural Essential Oil
supplier_claimed_origin     = France
supplier_claimed_botanical  = Lavandula angustifolia
supplier_claimed_extraction = Steam Distilled
supplier_claimed_part       = Flowers
supplier_listed_CAS         = 8000-28-0
```

The supplier explicitly describes `40/42` as a compositional/standard-grade
designation, not a 40% working dilution. The supplier also describes the
product as standardized across lavender/lavandin inputs with high-altitude
lavender added. It must therefore remain a supplier product/blend identity, not
an assumed universal single-lot molecular composition.

Online catalog identity does not prove that a physical bottle is owned. Bottle
size, label, lot, acquisition receipt, COA/GC profile, and homogeneity remain
unconfirmed. The product is consequently recorded as
`EXACT_CATALOG_PRODUCT_IDENTIFIED_PHYSICAL_STOCK_UNBOUND`, not as live stock.

## Blocker transition

Retired as current blockers:

- `AMBROX_FORM_CONFLICT`
- `VETIVERYL_STRENGTH_CONFLICT`
- `NORLIMBANOL_CARRIER_BASIS_CONFLICT` (replaced by a narrower blocker)
- `AROMA_AND_MORE_STOCK_NOT_BOUND` (replaced by a narrower blocker)

Current blocker order:

1. `HOLD_PARENT_BYTES_MISSING`
2. `HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING`
3. `NORLIMBANOL_BASIS_AND_DESIGN_CARRIER_MISMATCH`
4. `AROMA_AND_MORE_PRODUCT_IDENTIFIED_PHYSICAL_STOCK_UNBOUND`
5. `HAY_STOCK_BASIS_UNRESOLVED`
6. `BOTTLE_LOT_AND_HOMOGENEITY_RECEIPTS_MISSING`
7. `HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED`
8. `HOLD_EXACT_CURVE_APPLICABILITY`
9. `HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED`
10. `PLEASANTNESS_NOT_ESTABLISHED`
11. `PHYSICAL_LIKING_NOT_TESTED`

The overall readiness outcome remains:

```text
status             = HOLD
input_integrity    = VERIFIED
formula_action     = NO_CHANGE
inventory_updated  = true (stock authority only)
formula_modified   = false
compounding        = NOT_AUTHORIZED
```

## Governed fingerprints

- Original design-comparator manifest:
  `d7f5904bd9437cb61589a1a535423eedb6786641ccc70f109d3e1516bc222f86`
- Original R5 workbook:
  `027ec1cf8712c6aaac123d896942eee308efa18bea9056da975566e095bc3e67`
- Canonical R5 formula rows:
  `28284674560179b536f2e797a3b1a50ef0421e61435132f47704cda590ead15e`
- Original Checkpoint 3 protocol predecessor:
  `d11e6cc22688c9249a9799073eb58817d4b24a9c3519d408949984208538c274`
- Checkpoint 3 successor protocol:
  `d8da68003d99439dd17d3236cf61411d1822c4c8d3c14ff3af800be1c523199e`
- Current inventory text, raw bytes:
  `83f9289de98ed0d0fa72a71b474663b475a518c665a155a09711a7c8bf3e3c34`
- Current inventory successor overlay:
  `3f4ef634e2bd299a8463559364a03a7805b1198e14396567dce3e7f8caaf4df5`
- Direct user confirmation receipt:
  `cd993a027e2c164028dda77a048b3abc5cd1f36cbf8fb7f6712367f9a2bcc273`
- Aroma & More product-resolution receipt:
  `3a725f2337e992015878924a8a87ab1af2f846e711c615da1b70b04f4a95e435`
- Deterministic successor readiness report:
  `b9187a1d432e4694c428ee711403042366d96376e32ea7cf3f4e64c6ecab009e`

## Candidate audit after correction

| Candidate state | Rows |
|---|---:|
| `CANDIDATE_FORM_MATCH` | 45 |
| `CANDIDATE_FORM_CONFLICT` | 1 |
| `CANDIDATE_BASIS_UNRESOLVED` | 6 |
| `CANDIDATE_PREPARATION_REQUIRED` | 3 |
| `NO_AUTHORITY_STOCK` | 5 |
| `PRODUCT_IDENTIFIED_NO_PHYSICAL_STOCK` | 1 |
| `CURRENT_TEXT_ONLY_NOT_MATERIALIZED` | 1 |
| `CURRENT_TEXT_SNAPSHOT_CONFLICT` | 1 |
| **Total** | **63** |

There remain 55 read-only candidate stock IDs and zero authoritative build-plan
bindings.

## Verification

- Inventory, successor-overlay, R5 readiness, and comparator tests:
  `46 passed in 4.67s`.
- Backend durable-job tests: `9 passed in 12.80s`.
- Additional focused successor tranche: `12 passed in 1.32s`.
- Root Ruff for all changed engine/test surfaces: passed.
- Root mypy with explicit package bases: passed.
- Backend Ruff: passed.
- Backend mypy: passed.

The broader inventory-identity suite still contains unrelated historical stale
expectations and legacy failures; it was not rewritten to obtain a clean result.
No full verifier or release-level claim was attempted.
