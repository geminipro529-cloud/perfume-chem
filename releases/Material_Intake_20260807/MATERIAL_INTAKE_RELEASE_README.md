# Material Intake Release Bundle - 2026-08-07 (FINAL RE-SEAL)

## Status
- **Uncommitted.** This release packages the working-tree state of the
  2026-08-07 material-intake batch. No commit was created; the sources
  snapshotted here are the live, patched working-tree files.

## Contents
- `MATERIAL_INTAKE_RELEASE_BUNDLE.zip` - artifacts + source snapshots
- `MATERIAL_INTAKE_RELEASE_MANIFEST.json` - per-member path / size / SHA-256
  (`manifest_self_hash_included: false`)
- `MATERIAL_INTAKE_RELEASE_EXTERNAL_SHA256.json` - seals the manifest
  {path, size, sha256}
- `MATERIAL_INTAKE_RELEASE_README.md` - this file

### Bundle members
- `artifacts/` (14) - intake artifacts from
  `runs/External_Module_Intake_Integration_20260807_015204`:
  MATERIAL_INTAKE_PARSE_REPORT.json, MATERIAL_CONSISTENCY_RESULTS.json/.md,
  MATERIAL_INTAKE_AUDIT_FINDINGS.md, MATERIAL_INTAKE_REAUDIT_FINDINGS.md,
  MATERIAL_INTAKE_REMEDIATION.json, MATERIAL_INTAKE_FIX_20260807.json/.md,
  MATERIAL_SMOKE_TEST_RESULTS.json/.md, MATERIAL_YAML_REAUDIT_RESULTS.json/.md,
  PROPERTY_SOURCE_REGISTER.json/.md
- `source_snapshots/` (16) - patched source locations, relative paths preserved:
  - `engine/odor_thresholds.py` (batch + remediation blocks)
  - `engine/ingredient_intelligence.py` (batch + remediation blocks)
  - `engine/name_utils.py` (intake aliases)
  - `_generate_material_properties.py` (generator robustness fix)
  - `inventory.txt`
  - `data/materials/C.yaml`, `N.yaml`, `V.yaml`, `P.yaml`, `E.yaml`,
    `S.yaml`, `T.yaml`, `H.yaml`, `B.yaml`
  - `data/knowledge_graph/material_properties.json` (regenerated, 293 entries)
  - `data/knowledge_graph/audit_flags.json` (32 PubChem divergence flags)

## Scope of changes
- **Additive data + alias + generator-robustness changes only.** New material
  entries, ODT backfills, intake aliases, inventory stock entries introduced by
  the batch, plus the fixed `_generate_material_properties.py`.
- **7 YAML flag fixes** (2026-08-07 material-intake batch):
  `user_in_inventory: false -> true` + `user_stock_dilution` set for
  Cypress Essential Oil (1.0), Cabreuva Essential Oil (0.5),
  Caraway Seed Essential Oil (0.1), Nerolidol (1.0), Verdyl Acetate (1.0),
  Phenyl Acetaldehyde Dimethyl Acetal (padma) (1.0), Elemi EO (1.0)
  across C.yaml / N.yaml / V.yaml / P.yaml / E.yaml.
- **Generator robustness fix** in `_generate_material_properties.py`:
  `infer_odor_profile()` now handles `character` as either a dict or a str
  (isinstance guard, no crash on string-valued profiles); zero-ODT guard in
  the `oav_typical` division; generator also derives `in_inventory`,
  `stock_form` from live inventory records and adds intake CAS_MAP entries
  (2-acetyl pyrazine, adoxal, black agarwood artificial, castoreum
  synthetic, champignol, coriander essential oil, jasmine absolute,
  safraleine, violet leaf absolute).
- **No formula/gate/inventory-truth changes beyond the batch.** No formula
  files, pipeline gates, or pre-existing inventory facts were altered by this
  package; the snapshots capture only the batch's touch points.

## REQUIRED POST-STEP - DONE
- **material_properties.json generator sync is COMPLETE.**
  `python _generate_material_properties.py` was run from the repo root:
  - **Status: SUCCESS** - 293 entries written (267 before the batch)
  - **Intake coverage: 19/19** (13 direct keys + 6 via
    normalized/canonical keys)
  - **32 pre-existing PubChem divergences** flagged in
    `data/knowledge_graph/audit_flags.json` (not caused by the intake batch;
    e.g. Adoxal logp, Allyl Amyl Glycolate mw/logp, Alpha Irone logp)
  - The regenerated `material_properties.json` and `audit_flags.json` are
    snapshotted into this bundle.

## Boundaries
- This package makes **no formula, gate, or inventory-truth change**.
- This package makes **no empirical, safety, similarity, or Phase-G claims**.
  It is a data/alias intake bundle; sensory, IFRA-safety, structural-similarity,
  and Phase-G (gate) assertions are out of scope and not implied.
