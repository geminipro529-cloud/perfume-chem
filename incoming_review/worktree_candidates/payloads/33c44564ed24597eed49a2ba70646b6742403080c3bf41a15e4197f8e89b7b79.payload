# DNA-Preserving Perfume Reconstruction and Chassis Suite

## Rebuilt download archive

This archive was rebuilt because the earlier download link referred to a file that was not present in active storage.

## Included

### Protocols

- `protocol/MASTER_PROTOCOL_V2.md`
- `protocol/UNIVERSAL_NONCOMPRESSED_RECONSTRUCTION_PROTOCOL_V1.md`
- `protocol/DNA_PRESERVING_STRUCTURAL_CHASSIS_PROTOCOL.md`
- `protocol/FROM_SCRATCH_RECONSTRUCTION_ADDENDUM.md`
- `protocol/BRAND_ERA_ADAPTATION.md`

### Case studies

- YSL L'Homme 70-row expanded target and 4,200 + 300 µL chassis
- YSL La Nuit de L'Homme 50-row expanded target and 4,200 + 300 µL chassis
- Prada L'Homme 54-row from-scratch Tier 1-2 hypothesis and 4,150 + 350 µL chassis

### Formula files

CSV target formulas, row-wise chassis partitions, parent modules, and alternative module examples.

### Machine-readable configuration

- target hashes;
- protected-anchor floors;
- module envelope files;
- brand and era profiles.

### Scripts and tests

- deterministic partition and module validation;
- original universal reconstruction toolkit;
- pytest tests;
- `VALIDATION_REPORT.json`.

## Validation result

`PASS`

- all target totals equal 4,500 µL;
- every fixed core plus parent module recombines row by row;
- every parent and alternative module matches its declared socket total;
- protected anchor floors pass;
- automated tests pass.

## Authority boundaries

The YSL cases use user-supplied secondary identity rosters with inferred dosages. Prada L'Homme is a from-scratch functional hypothesis based on official notes, label evidence, and perfumery priors. None of the formulas is an authenticated manufacturer recipe, a safety authorization, or a measured sensory-equivalence claim.

## Primary hashes

```json
{
  "YSL_LHomme_target": "6a81b871565b77287e49963f8254f46f18f443dc8dde6857695739b4e76e3c80",
  "YSL_LHomme_partition": "26a551f6ac1d84740019400d5c9a988a6c56f3e576c42eb8aecf5e1cc3965e73",
  "YSL_La_Nuit_target": "8fb817a60f94023e970c38acd283b0839d3ec1a004d446b1acd7d9b0818d1400",
  "YSL_La_Nuit_partition": "552b4c3c02203142e90ad2639962b0f0b1752fd0b146c3e0a58caa6028494e73",
  "Prada_LHomme_target": "5cc1f7e696d17ad805e104310f419644be9ba5dde9e548c7149e1225039e3618",
  "Prada_LHomme_partition": "af3f47b45585a2e2d23cb375faacba0a36b84e2e84dc9a879d1b36d7932f8c8b"
}
```

Run:

```bash
python src/validate_suite.py
python -m pytest -q tests
```
