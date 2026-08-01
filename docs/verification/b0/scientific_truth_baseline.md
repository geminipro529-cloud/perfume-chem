# B0 Scientific Truth Baseline

Date: 2026-08-02

Build: B — Scientific Data Authority and Analytical Validation

Phase: B0 — Scientific truth baseline

Decision: **PASS**

## Authority

This baseline was generated from the exact
`D:\chatbots\perfume-chem` working tree after the final Build A boundary commit
`073ee8eaf66bd97a4894063c2f3ffc01c874e7b2`. Generation ran at B0 repair head
`eb980e6`, including the preserved dirty overlay. Historical B0-B10 reports are
compatibility evidence only.

No scientific value was promoted because a test passed or because it appeared
in a better-shaped file.

## Machine-readable inventory

Full inventory:
`docs/verification/b0/scientific_truth_inventory.json.gz`

- schema: `scientific-truth-inventory-v1`
- compressed SHA-256:
  `3F287B86C29E645D879E3B2AF59DDCF53D059C11509ECF85576A7C126F9DAEBC`
- decompressed JSON SHA-256:
  `1EB930343B33DB9A60395567FA97748C428B416D46447BECA9991448B4F7B779`
- compressed bytes: 1,506,865
- decompressed bytes: 26,221,111
- secret, credential, generated-cache, SQLite-sidecar, wheel-smoke, B0-output,
  and embedded-Git paths: 0

The scanner and its tests are:

- `scripts/scientific_truth_inventory.py`
- `tests/test_scientific_truth_inventory.py`

Scanner verification: **3 passed**; Ruff: **PASS**. Two independent full-tree
generations were byte-identical.

## Inventory summary

| Item | Count |
|---|---:|
| source/content digests | 1,043 |
| material rows | 1,262 |
| material-property cells | 23,869 |
| scientific code constants | 300 |
| structured/advisory knowledge rules | 3,381 |
| material-property conflict sets | 226 |

Material-property authority labels:

| Authority label | Cells |
|---|---:|
| `UNKNOWN` | 20,949 |
| `UNATTRIBUTED_LEGACY` | 1,987 |
| `LEGACY_HEURISTIC` | 505 |
| `LEGACY_TRACEABLE` | 311 |
| `LOCAL_RECORD` | 69 |
| `LITERATURE_DERIVED` | 39 |
| `SUPPLIER_PROVIDED` | 9 |

These labels are a baseline classification, not a final B1/B2 evidence review.
Most cells are null or lack observation-grade provenance.

Selected non-null coverage:

| Property | Non-null |
|---|---:|
| molecular weight | 289 |
| density at 25 °C | 32 |
| logP | 211 |
| vapor pressure at 25 °C | 286 |
| Antoine coefficients | 0 |
| enthalpy of vaporization | 2 |
| air ODT | 92 |
| ethanol ODT | 81 |
| IFRA maximum field | 15 |
| SMILES | 15 |
| InChIKey | 14 |
| receptor targets | 1,260, mostly empty lists |
| TRP targets | 50 |
| hedonic valence | 137 |

## High-impact baseline findings

1. `engine/odor_thresholds.py` contains a 301-entry `ODT_DATA` table and a
   separate 276-entry `ODT_VERIFICATION` table. Many consumers still read these
   legacy surfaces directly; their values remain non-authoritative unless a
   current B3 contextual gate accepts them.
2. `MIXTURE_SUPPRESSION_FACTOR = 5.0` is a global legacy code parameter used by
   formula analysis, OAV guards, and temporal volatility code. It is not a
   measured universal constant.
3. Two separate `IFRA_CAT4_LIMITS` dictionaries exist with 27 and 97 entries.
   They have overlapping consumers and are a duplicate/conflict risk.
4. `engine/safety/regulatory.py` treats an absent limit as unrestricted in a
   legacy compatibility helper. That behavior is not acceptable for B6
   authority and must become `UNKNOWN` behind the canonical gate.
5. `data/knowledge_graph/material_properties.json` duplicates property values
   used by multiple runtime modules in addition to the YAML material spine and
   SQLite knowledge database.
6. The 3,381 extracted knowledge rules are predominantly advisory legacy
   records. Generic, poetic, or unresolved references cannot become exact
   identities or numerical formula mutations.
7. Historical B1-B9 typed authority implementations and reports are present in
   the inherited tree. They remain unaccepted compatibility inputs until their
   gates are independently reproduced in strict order.
8. The in-memory evidence and analytical ledgers are read-only compatibility
   projections. Canonical writes already route through `LabService`.
9. Existing GC-MS identity states are too coarse for B5, and a fixed “four of
   seven QC checks” compatibility score cannot establish method-specific
   fitness for purpose.
10. The current science audit correctly exposes sparse coverage, but its output
    is a legacy regression fixture, not evidence that individual values are
    authoritative.

## Source digest baseline

Selected preserved digests:

| Path | SHA-256 |
|---|---|
| `verification_runs/science_audit.json` | `569C4DD700DC7AA6525861875530866D3636DD1A42FD48CBEE64C0A005739B0A` |
| `docs/oav_analysis_Bleu_Luxe_vF_2026-05-09.txt` | `8D31330BBB41EC0F564CFDA1B49991539AE29B14E1A87B1096C62072C6C917C3` |
| `data/knowledge_graph/material_properties.json` | `1FCCCD43D41520D62CA4D3CCC4C8653357B7D4545676C10AE10DCCC9CBFF0726` |
| `data/knowledge_graph/pairing_rules.json` | `FC4370B8017334E070B873463BCEC1DB8CD781B156DB214A8B1C0382483CF8D1` |
| `data/knowledge_graph/pairing_rules_discovered.json` | `2DD23D496CDA1B6DBD61FF147F977D4BBB7D919048B591E018785BA0BDE9E044` |
| `data/knowledge_graph/synergy_matrix.json` | `7B194C2F7EA19EFCFBCC1BAFEF5E4C0DFDCAC69739DFF5720B1C91FE0B7D7B9D` |
| `data/knowledge_graph/theory_rules.json` | `4237619F7FDDDBFC15B373C42F40E2D30FC587537AC8F782B2111D6F61F53B90` |
| `data/perfumery_kb.db` | `5A779F9D6850345D72DE3C8265D4330C50DAC529968B38BC9B08720B5DA63FE1` |
| `tests/fixtures/golden_formula_cases.json` | `193C0BFA868C1C0A4E92F75AE6B1B4FA99C3268C3F6C5C9C3EBB404FE3C4BEB7` |
| `tests/fixtures/golden_formula_cases.sha256` | `C16FC7419B77F7BAC52D0642698E21FE44252C129B6D6A1C175AD4CD3B86287B` |

The full set of 1,043 path/size/SHA records is in the compressed inventory.

## Before-migration runtime call graph

```text
data/materials/*.yaml
  -> engine.data_spine.loader
  -> material/formula state
  -> quantities, thermo, OAV, safety, family, optimizer, release gates

engine.odor_thresholds.ODT_DATA + ODT_VERIFICATION
  -> lookup/verification helpers
  -> formula analyzer, OAV authority, optimizers, temporal models, reports

data/knowledge_graph/*.json
  -> kb_migrate / init_db
  -> data/perfumery_kb.db
  -> knowledge_base, interaction_graph, rule APIs, recommendations

engine.ifra_constraints.IFRA_CAT4_LIMITS
engine.ifra_safety.IFRA_CAT4_LIMITS
  -> IFRA checks, pipeline gates, robustness, optimizer, scripts

backend LabEvidenceRecord + LabMaterialProperty
  -> analytical/regulatory/claim science tables
  -> LabScienceService
  -> /api/v1/lab/v2 science endpoints
```

The full item-to-consumer links and claim-impact counts are machine-readable.

## Claim-impact map

| Claim | Inventoried inputs |
|---|---:|
| identity | 5,025 |
| quantity | 2,527 |
| mass-volume conversion | 3,785 |
| threshold screening | 2,587 |
| headspace prediction | 10,112 |
| sensory intensity | 2,516 |
| formula similarity | 1 |
| natural authenticity | 74 |
| analytical identification | 38 |
| analytical quantitation | 75 |
| safety/compliance screening | 2,556 |
| family classification | 3,403 |
| intervention recommendation | 5,896 |
| release | 1,285 |

Counts are references/impact links, not distinct authoritative values.

## Compatibility matrix

| Legacy surface | Must remain readable | B migration treatment | Authority after migration |
|---|---|---|---|
| YAML material fields | yes | create observations or explicit heuristic records; do not overwrite source files | scoped by selected-assertion policy |
| `ODT_DATA` / `ODT_VERIFICATION` | yes | migrate actual status and context limitations | exploratory unless context and source gates pass |
| old OAV/headspace text and outputs | yes | preserve as labeled fixtures | no scientific authority |
| `EvidenceSource` / `EvidenceClaim` serialization | yes | one-way adapter into SourceDocument/extraction/observation records | source-class and review-state dependent |
| `LabMaterialProperty` | yes | compatibility projection of selected assertions | never last-write-wins |
| old analytical exports | yes | missing method/QC/calibration fields become unknown | advisory or withheld |
| fixed four-of-seven QC score | yes | keep as historical projection only | cannot unlock analytical claim |
| legacy IFRA helpers | yes | missing limit becomes `UNKNOWN`; dated snapshot required | scoped screening only |
| knowledge JSON and SQLite rules | yes | compile into exact group/identity schema; invalid rules quarantined | advisory unless promoted by evidence |
| golden formula/API fixtures | yes | unchanged unless separately reviewed and relocked | regression only |

## Protected database state

Both SQLite files were inspected read-only with immutable connections:

| Path | Bytes | SHA-256 | `quick_check` | Alembic rows |
|---|---:|---|---|---:|
| `data/perfumery_kb.db` | 2,084,864 | `5A779F9D6850345D72DE3C8265D4330C50DAC529968B38BC9B08720B5DA63FE1` | `ok` | 0 |
| `perfume_chem.db` | 12,288 | `02B64BE88E4A8881C968EC9EF7F0185ED7B1BCEDC6ED33885F07D7DE70A0DA5E` | `ok` | 0 |

No migration or write was performed against either protected file.

## Reproduced defect and repair

The fresh scanner initially included `data/perfumery_kb.db-wal` and
`data/perfumery_kb.db-shm` as source evidence. The focused regression failed for
that exact reason. Commit `eb980e6` excludes both transient sidecar classes; the
regression and full scanner suite now pass, Ruff is clean, and two full-tree
outputs are byte-identical with zero sidecar entries.

DeepLuna Fast audit `DS-5f2065755e51abc684bfb387ba590ed2` independently
identified the same missing exclusion under `FLASH` / `NO_LUNA`; Sol reproduced
and accepted the root cause locally. The prior three-artifact B0 set is preserved
in the path-restorable archive
`outputs/b0-authoritative-recovery/20260802T060025/b0-artifacts-before-refresh.zip`
with SHA-256
`70CBBBDC93EF0B387417279B13818D40855FEB27DB0F998C5B055669C3EACF8A`.

Final Fast review `DS-8f323c479ecabfd38987e8403cabc134` returned
`PASS` / `POSITIVE` / `ACCEPTED` with no negative findings, no scope deviation,
and no architecture or scientific uncertainty. Sol accepted it only after the
local report-to-artifact, scanner, Ruff, and protected-database checks passed.

## B0 exit-gate review

- scientific input inventory: complete and machine-readable;
- runtime consumers: linked for data files and code constants;
- source digest baseline: complete for 1,043 allowlisted inputs;
- legacy science behavior and fixtures: frozen by hash;
- known heuristics and conflicts: recorded;
- compatibility matrix: complete;
- claim-impact map: complete;
- secret-bearing and transient SQLite paths: excluded;
- migrations/backfills performed during B0: none.

Phase B0 exits **PASS**. B1 may begin from this reviewed baseline.
