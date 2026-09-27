# Checkpoint 3 R5 Stock Clarifications v2 — 2026-09-24

Status: `PARTIAL_BLOCKER_CLOSURE_VERIFIED`

This receipt records direct user clarifications received after the first
2026-09-24 R5 stock-form reconciliation. It does not authorize physical
compounding, build-plan binding, measurement execution, scientific promotion,
safety clearance, regulatory clearance, or formula release.

## Facts admitted

- Norlimbanol Dextro is a homogeneous 10% w/w solution in DPG.
- The R5 Norlimbanol row may use DPG rather than the workbook's earlier ethanol
  carrier description. No dose change was authorized.
- Hay Absolute is a homogeneous 10% w/w solution in DPG.
- The user physically owns 10 mL of undiluted/as-supplied homogeneous Aroma &
  More Lavender 40/42, bound to supplier catalog reference `Lav420811P`.
- The selected future common-total basis is active odorant mass (`active_mass_g`,
  w/w interpretation); older w/v stocks remain present.

## Facts not supplied

- Norlimbanol and Hay exact preparation masses, preparation dates, parent lots,
  and carrier lots.
- Aroma & More lot/batch, purchase source, and label receipt.
- The constant active-mass total and the transfer masses or densities needed to
  convert every volume-dosed w/w stock onto that basis.
- Exact R4 parent bytes.
- Applicable headspace/intensity evidence, measurement execution parameters,
  a pleasantness target, or physical liking evidence.

A fresh filename-targeted read-only search found no R4 candidate in the user's
Downloads directory or Codex attachment store. The expected parent remains
`Lavande_Ambre_Profond_R4_30mL_Fixed_Doses.json`, SHA-256
`5b0a012b88ca5c1cea45ea8a704cf3b9e5d799d66e9f9d28b2a5d21efa9f4129`.

## Blocker changes

Retired:

- `NORLIMBANOL_BASIS_AND_DESIGN_CARRIER_MISMATCH`
- `AROMA_AND_MORE_PRODUCT_IDENTIFIED_PHYSICAL_STOCK_UNBOUND`
- `HAY_STOCK_BASIS_UNRESOLVED`
- `BOTTLE_LOT_AND_HOMOGENEITY_RECEIPTS_MISSING`
- `HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED`

Current ordered blockers:

1. `HOLD_PARENT_BYTES_MISSING`
2. `HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING`
3. `BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING`
4. `HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING`
5. `HOLD_EXACT_CURVE_APPLICABILITY`
6. `HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED`
7. `PLEASANTNESS_NOT_ESTABLISHED`
8. `PHYSICAL_LIKING_NOT_TESTED`

## Current read-only stocks

| Material | Stock ID | Quantitative state | Physical-build state |
|---|---|---|---|
| Norlimbanol Dextro | `inventory:user-20260924:571e42bc68ae8b3de5ec` | 10% w/w in DPG, homogeneous | receipt incomplete |
| Hay Absolute | `inventory:user-20260924:32d522588baeb5a0d0cd` | 10% w/w in DPG, homogeneous | receipt incomplete |
| Lavender 40/42, Aroma&More | `inventory:user-20260924:38a9eff2ae4d6803f3ba` | neat/as supplied, 10 mL, homogeneous | lot/source/label receipt incomplete |

All three are read-only analysis candidates. None is a bound physical-build
line or a mixer command.

## Fingerprints

- `inventory.txt`: `6f8de068a71893d6be13815b5ca468ff6f4d2b9436b91930c41c0a3173e9b89a`
- Direct user confirmation v2: `5179974ec3c64a4c48be310b530b9670b08fa07099f663f5c480f446b0290992`
- Inventory successor overlay v16: `9a10cd2f99af1c960a77bd0a7270c25daa24657b790707ecb76c365898b747df`
- Checkpoint 3 readiness protocol v3: `f83b8af0bb1a2bd4bc28a90b247e35bc91e5c518319b75dd5771940014b6dbbe`
- Deterministic readiness report: `b7a9fb67f4ebab41b248260eb70b35de1fca716471076c7791c897088fede9fd`

## Verification

- Focused inventory and Checkpoint 3 regression tranche: `57 passed`.
- Backend Ruff on changed engine-job surfaces: passed.
- Backend mypy on changed engine-job services: passed.
- Backend engine-job unit tranche: `10 passed`.

No formula pipeline, full verifier, physical experiment, or compounding run was
performed or claimed.
