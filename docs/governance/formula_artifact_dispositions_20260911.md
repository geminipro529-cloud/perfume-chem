# Formula artifact dispositions (lane evidence)

Provenance: lane `D:\chatbots\.lanes2-20260910\14-formula-artifacts`, detached worktree of the
integration repository at `cc2693eb7b76ddac9b0c208c0507b13b7be4ba7f`. Produced by
`D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe scripts/pipeline_audit.py artifact-verify --json`
(83,244 bytes raw JSON, exit 1 with blockers present; independent confirming re-run returned identical counts).
The body below is the lane deliverable verbatim; it was not re-derived during harvesting.

Decision recorded by the repository owner on 2026-09-11: the seven STALE artifacts are quarantined
(not regenerated), and the fourteen QUARANTINED plus forty-nine UNBOUND_LEGACY artifacts are
classified historical/inactive with no successor artifacts.

---

## Appendix — Guaiacwood EO knowledge-base identity row (2026-09-11)

`tests/test_kb_migration.py::test_every_inventory_material_exists` failed because the owned stock
`Guaiacwood EO` (inventory.txt row 200) had no entry in `materials` or `material_aliases`, while
`Guaiacol` — a different material — already existed. The migration was completing the inventory
contract but not the identity contract.

`engine/kb_migrate.py` now has an explicit inventory-identity reconciliation stage that runs after
the YAML, profile-only and ODT-only inserts and before `name_to_id` is returned. It inserts a
declared identity-only material with every physical and ODT field NULL, so the knowledge base can
resolve the identity without asserting unmeasured chemistry:

```
INSERT OR REPLACE INTO materials (
    canonical_name, cas, smiles, inchikey, mw_g_mol, density_25c_g_ml, logp, vp_25c_pa,
    odt_air_ppb, odt_eth_ppm, note, role, texture, character_json, synergies_json,
    activity_coef, hedonic, odor_family, ifra_cat4_limit_pct, user_stock_dilution,
    user_in_inventory, stevens_n, vp_source, vp_flag
) VALUES ('Guaiacwood EO', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
          NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL)
```

Verified on a disposable database: `Guaiacwood EO` id 1295 carries NULL `mw_g_mol`, `odt_air_ppb`
and `vp_25c_pa` with `user_in_inventory = 1`, and `Guaiacol` id 527 keeps its own measured values —
the two identities stay distinct rows.

The exact one-third w/w Guaiacwood EO / ethanol / DEP preparation is **not** expressed here; it is
carried by the inventory stock-authority contract in `engine/inventory_parser.py`, which validates
the fraction, mass-fraction basis, `ethanol + dep` carrier and execution readiness from the
inventory rows themselves.

## Appendix — quarantine action taken (2026-09-11)

The seven STALE artifacts were quarantined in place by replacing each formula's header status line
with the validator's fail-closed lifecycle marker `**Status**: QUARANTINED — do not mix or release.`
plus the reason and the previous status text. The embedded stale analysis blocks were left intact as
historical record; no formula arithmetic, dilution, or inventory row changed. Files:

- `formulas/AHS_2004_Reference_First_From_Zero_30mL_EDT_v2_Neat_Neroli.md`
- `formulas/DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP.md` and `..._R2.md`
- `formulas/DPP_02_Tuberose_Sandal_Cream_30mL_EDP.md` and `..._R2.md`
- `formulas/DPP_03_Tobacco_Resin_Amber_Reserve_30mL_EDP.md` and `..._R2.md`

Measured result of `scripts/pipeline_audit.py artifact-verify --json` after the change: exit code 0,
status WARN, `NONE 456`, `QUARANTINED 21` (14 + 7), `UNBOUND_LEGACY 49`, and **zero STALE or
TAMPERED** rows, against the blocking policy `[STALE, TAMPERED]`. Raw output:
`_state/artifact_verify_post_quarantine.json` in the audit workspace.

Unrelated pre-existing hold observed while verifying this step, recorded here rather than silently
absorbed: `scripts/verify_d0_claim_matrix.py::build_gate_payload` raises
`ValueError: control formula binding changed` (line 120) because
`formulas/Prada_LHomme_Architecture_Control_30mL_EdT.md` does not match `EXPECTED_CONTROL_SHA256`.
It reproduces with this step's formula edits stashed, so it is independent of the quarantine, and it
is not part of the quick-verifier groups.
# L14 — Formula artifact disposition review

Lane: `D:\chatbots\.lanes2-20260910\14-formula-artifacts` (detached worktree of the integration repo at `cc2693eb7b76ddac9b0c208c0507b13b7be4ba7f`).
This review is read-only with respect to formulas and artifacts: nothing was regenerated, repinned, edited, committed, or pushed. The only writes are inside `_lane_out`.

## Method and provenance

Command (interpreter by absolute path, lane as cwd):

```
D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe scripts/pipeline_audit.py artifact-verify --json
```

- Runtime 30.5 s (first run) and 3.1 s (confirming re-run), exit code 1 both times (blockers present), 83,244 bytes of raw JSON.
- Raw output: `_lane_out\L14_artifact_verify_raw.json`; confirming re-run `_lane_out\_scratch\L14_verify_rerun.json` returned the identical counts. stderr was empty.
- Per-record provenance extracted read-only into `_lane_out\L14_artifact_details.json` by `_lane_out\_scratch\L14_extract.py` (uses the repository's own `split_generated_pipeline_analysis`, `parse_pipeline_analysis_manifest`, `parse_formula_markdown`, `stable_formula_definition_hash`).
- Worktree content: byte-identical to `cc2693eb` for every tracked file. During the review, at 2026-09-11 00:29:21, an external process re-wrote 13 `data/governance/*.json` files in this lane; `git hash-object` matches the `HEAD` blobs for all 13, so they are stat-dirty only, not content changes, and none of them is part of the artifact-evidence set. The only new content in the lane is `_lane_out/`.

The independent run reproduces the acceptance record exactly — the counts are not taken on trust:

| status | count | blocks `artifact-verify` | evidence role |
| --- | --- | --- | --- |
| NONE | 456 | no | no persisted analysis artifact at all (`none_is_current: false`) |
| QUARANTINED | 14 | no | explicit do-not-mix/release quarantine in the formula source |
| STALE | 7 | **yes** | persisted analysis whose inputs no longer match the repository |
| UNBOUND_LEGACY | 49 | no | analysis text with no valid binding manifest |
| TAMPERED | 0 | (yes) | none observed |

Total scanned: 526 formula files. Policy block emitted by the tool: `blocking = [STALE, TAMPERED]`, `unbound_legacy_is_current = false`, `none_is_current = false`, `quarantined_is_current = false`, `quarantined_release_authority = false`. **The only artifact blockers today are the seven STALE rows.**

Current repository evidence hashes used for comparison (from the same run):

- `inventory_sha256 = 28a71fda7af3549c09127f269892b393581053e29f2f824f273a2f654bc0c2ec`
- `scientific_inputs_sha256 = 88937422f3191610405c7b7cd1ed265af0a476d406291888bf91d3812bf07fad`
- `pipeline_source_sha256 = e66ed366d96fc15c603325677f15bb37cde17c961a73c5cd35bb83d19b3dc301`

Lineage limitation that applies to almost every row below: only 4 of the 70 non-current artifacts carry `g15_parent_formula_definitions`. For the other 66 the artifacts record no immediate parent, so the parent column says `none recorded` — that is a property of the older renderers, not an inference.

## 1. The seven STALE artifacts (the only blockers)

### 1.1 Provenance

| # | file | generated (UTC) | generator | stored def hash | current def hash | def | parent | input hash (`analysis_input_sha256`) | artifact sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `AHS_2004_Reference_First_From_Zero_30mL_EDT_v2_Neat_Neroli.md` | 2026-09-06T06:37:18.817471+00:00 | `e7002d4d` | `24a55d353461` | `24a55d353461` | same | AHS-2004 Reference-First — From-Zero 30 mL EDT Study v1 | `18b3add4ba0e93d290bd17530110d5f804024df492aa8b94537e242dcaea31eb` | `481979c6dfc3d2e3d755266fb2b5c5256e6ed56a52e163e0758e307cb78d0576` |
| 2 | `DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP.md` | 2026-09-02T12:10:31.435234+00:00 | `8c2a6071` | `5482eedb6479` | `72a4cbd73b7c` | CHANGED | none recorded | `c6bffd6e85fb1e56431cb5c494a9d59780676f98de53dcfbe67f3a89fb03f20a` | `5f1fba47927b23c8fefac7525ac37c1855ce439f4c32e378c951ab25417bce8d` |
| 3 | `DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP_R2.md` | 2026-09-02T12:05:59.813127+00:00 | `8c2a6071` | `70ba3edda5fd` | `42cd396bad0a` | CHANGED | DPP-01-R1 Mandarin Ember Sandalwood — 30 mL EDP | `bd7d89d6444f7ba4d3aa7c36c15bcf55a7ebf9941735ae46965c1e119299b51a` | `355694555ab26fd4462ce4c399522d6293039a1e55b31ad7a839e13646cee2ae` |
| 4 | `DPP_02_Tuberose_Sandal_Cream_30mL_EDP.md` | 2026-09-02T12:10:26.562666+00:00 | `8c2a6071` | `b23011bc88f4` | `b23011bc88f4` | same | none recorded | `e81dfb3d7220d41f9fa7c3bc687eb74d81d35da9d16d18c9d60a6778a3a3728c` | `148b7b484b8fe01cd79bf7cb7e943e0108be7707688d2c3f6a2c38c2fa7f9a04` |
| 5 | `DPP_02_Tuberose_Sandal_Cream_30mL_EDP_R2.md` | 2026-09-02T12:05:52.935490+00:00 | `8c2a6071` | `ecdf0d20630c` | `ecdf0d20630c` | same | DPP-02-R1 Tuberose Sandal Cream — 30 mL EDP | `ad75b0d0d4f44da54a8d36bee31e249f4c5b179e6b061d5a1d127f349ad4fe1b` | `2e9940ea80bea24079d849a3844554efe184797faeec733265323cadd76f37b4` |
| 6 | `DPP_03_Tobacco_Resin_Amber_Reserve_30mL_EDP.md` | 2026-09-02T12:10:29.422745+00:00 | `8c2a6071` | `691906e6404a` | `cef0bbf85869` | CHANGED | none recorded | `ab09534b249c413f28699b968b0aa63b0b9e78eed19f59fb21da19f1ddc6e090` | `7677f1552f51db599992cdbd1cc1b52923b20bcb7b69be42987b1477b92affb3` |
| 7 | `DPP_03_Tobacco_Resin_Amber_Reserve_30mL_EDP_R2.md` | 2026-09-02T12:05:57.160033+00:00 | `8c2a6071` | `30ee0a199c50` | `8b4a73c88129` | CHANGED | DPP-03-R1 Tobacco Resin Amber Reserve — 30 mL EDP | `6c9c8314bb678a0ae689d82a2205c2b9fd1169100c29ac37355e295884921133` | `50f89b388a2f566dba429571c9552bba9bcf54538edf577a0795bee7901bc130` |

Last commit touching each file: the six DPP files `2026-09-02T19:12:59+07:00 e58f8431`; the AHS file `2026-09-10T16:28:55+07:00 8414de16` (committed after its analysis was generated).

### 1.2 Why each one is stale

| file | stored inventory | stored scientific | stored pipeline | current inventory | current scientific | current pipeline | stale axes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AHS_2004_Reference_First_From_Zero_30mL_EDT_v2_Neat_Neroli.md` | `d103b7950859` | `09596a0dda10` | `c0dd00b636cf` | `28a71fda7af3` | `88937422f319` | `e66ed366d96f` | inventory, scientific_inputs, pipeline_source |
| `DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP.md` | `41cae9d8b65b` | `5fa4ff5ba58e` | `88b272c7c739` | `28a71fda7af3` | `88937422f319` | `e66ed366d96f` | inventory, scientific_inputs, pipeline_source, formula_definition |
| `DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP_R2.md` | `41cae9d8b65b` | `5fa4ff5ba58e` | `88b272c7c739` | `28a71fda7af3` | `88937422f319` | `e66ed366d96f` | inventory, scientific_inputs, pipeline_source, formula_definition |
| `DPP_02_Tuberose_Sandal_Cream_30mL_EDP.md` | `41cae9d8b65b` | `5fa4ff5ba58e` | `88b272c7c739` | `28a71fda7af3` | `88937422f319` | `e66ed366d96f` | inventory, scientific_inputs, pipeline_source |
| `DPP_02_Tuberose_Sandal_Cream_30mL_EDP_R2.md` | `41cae9d8b65b` | `5fa4ff5ba58e` | `88b272c7c739` | `28a71fda7af3` | `88937422f319` | `e66ed366d96f` | inventory, scientific_inputs, pipeline_source |
| `DPP_03_Tobacco_Resin_Amber_Reserve_30mL_EDP.md` | `41cae9d8b65b` | `5fa4ff5ba58e` | `88b272c7c739` | `28a71fda7af3` | `88937422f319` | `e66ed366d96f` | inventory, scientific_inputs, pipeline_source, formula_definition |
| `DPP_03_Tobacco_Resin_Amber_Reserve_30mL_EDP_R2.md` | `41cae9d8b65b` | `5fa4ff5ba58e` | `88b272c7c739` | `28a71fda7af3` | `88937422f319` | `e66ed366d96f` | inventory, scientific_inputs, pipeline_source, formula_definition |

All seven share the three repository-evidence drifts (inventory, scientific inputs, pipeline source). Four of the seven additionally describe formula bytes that have since changed.

### 1.3 Individual review and disposition

1. **`formulas\DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP.md`** — R1 base of the DPP-01 pair. Input hash `c6bffd6e…f20a`, artifact hash `5f1fba47…ce8d`, no parent recorded. Formula definition changed (`5482eedb…` → `72a4cbd7…`), so the stored analysis describes different bytes; status header reads "Pending bench — blotter evaluation only; safety, stability, and sensory performance NOT TESTED". Disposition: **new successor artifact required before any bench or scoring claim** (blocking today; alternative is an explicit inactive entry).

2. **`formulas\DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP_R2.md`** — basket-form revision. Input hash `bd7d89d6…b51a`, artifact hash `35569455…e2ae`. Definition changed (`70ba3edd…` → `42cd396b…`), and its recorded parent `DPP-01-R1` is bound at `5482eedb…`, which is the **superseded** R1 hash (current R1 is `72a4cbd7…`). Lineage therefore points at an older base. Disposition: **new successor artifact, ordered after DPP-01-R1 is finalized/regenerated so the parent binding resolves to the current base**.

3. **`formulas\DPP_02_Tuberose_Sandal_Cream_30mL_EDP.md`** — definition unchanged (`b23011bc…`), so only evidence drift applies. Input hash `e81dfb3d…728c`, artifact hash `148b7b48…f9a4`. Disposition: **successor if the line is live; otherwise inactive** — the analysis still describes the current bytes but its numbers were computed against older inventory/science/pipeline evidence.

4. **`formulas\DPP_02_Tuberose_Sandal_Cream_30mL_EDP_R2.md`** — definition unchanged, parent `DPP-02-R1` bound at `b23011bc…`, which matches the current R1 definition, so the lineage is intact. Input hash `ad75b0d0…fe1b`, artifact hash `2e9940ea…37b4`. Disposition: **successor if the line is live; otherwise inactive**.

5. **`formulas\DPP_03_Tobacco_Resin_Amber_Reserve_30mL_EDP.md`** — definition changed (`691906e6…` → `cef0bbf8…`). Input hash `ab09534b…e090`, artifact hash `7677f155…affb3`. Disposition: **new successor artifact required** (same reasoning as DPP-01-R1).

6. **`formulas\DPP_03_Tobacco_Resin_Amber_Reserve_30mL_EDP_R2.md`** — definition changed (`30ee0a19…` → `8b4a73c8…`), parent bound at the superseded R1 hash `691906e6…` (current R1 `cef0bbf8…`). Input hash `6c9c8314…1133`, artifact hash `50f89b38…c130`. Disposition: **new successor artifact, ordered after DPP-03-R1 is finalized**.

7. **`formulas\AHS_2004_Reference_First_From_Zero_30mL_EDT_v2_Neat_Neroli.md`** — definition unchanged; parent `AHS-2004 Reference-First — From-Zero 30 mL EDT Study v1` bound at `166304e4…cf23`. Input hash `18b3add4…31eb`, artifact hash `481979c6…0576`. Status header: "USER-CONFIRMED-STOCK DESIGN CANDIDATE / CANONICAL INVENTORY SYNC HOLD / NOT COMPOUNDED / NOT TESTED / RELEASE HOLD". The formula file was committed (`8414de16`, 2026-09-10) after the analysis (`e7002d4d`, 2026-09-06) without changing the definition hash. Disposition: **cannot be regenerated safely while the canonical inventory sync hold stands; either keep blocking until the sync resolves or record it as inactive/hold**.

Order of operations if successors are chosen: DPP-01-R1 → DPP-01-R2 → DPP-03-R1 → DPP-03-R2 → DPP-02-R1 → DPP-02-R2 (order within the DPP-02 pair is free); AHS v2 last, only after the inventory sync hold is lifted. Each successor is one bounded `scripts/formula_release_gate.py --formula-file …` run plus a re-run of `artifact-verify`. Regeneration was **not** performed in this lane.

## 2. The fourteen QUARANTINED artifacts

All 14 carry an explicit `**Status:** QUARANTINED — do not mix or release…` header in the formula source, so the validator reports `quarantine_explicit = true` and `release_authority = false`. They are stale-bound but non-blocking purely because they are already fail-closed. Last commit for all 14: `2026-08-07T09:15:42+07:00 dd567b47` (the quarantine commit).

| # | file | binding | generated (UTC) | input hash | artifact sha256 | def | quarantine header (truncated) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Allure_Extreme_AHSEE_30mL_EdP.md` | pre-binding v1 (no binding schema) | 2026-07-23T19:04:31.919873+00:00 | UNKNOWN (not computed by that renderer) | `620b389e6e7a` | CHANGED | Status: QUARANTINED — do not mix or release. The live inventory cannot … |
| 2 | `Cassis_Iris_Smoke_30mL_EdP.md` | pre-binding v1 (no binding schema) | 2026-07-23T19:04:42.857773+00:00 | UNKNOWN | `2c0312cdfc8f` | CHANGED | Status: QUARANTINED — do not mix or release. Romandolide and Habanolide are … |
| 3 | `Cassis_Iris_Smoke_30mL_EdP_v2_MIXABLE.md` | pre-binding v1 (no binding schema) | 2026-07-23T19:04:52.628463+00:00 | UNKNOWN | `136ead90394e` | CHANGED | Status: QUARANTINED — do not mix or release. The dose table parses as 40 … |
| 4 | `L_Homme_Realistic_Reconstruction_30mL_EDT.md` | pre-binding v1 (no binding schema) | 2026-07-27T17:20:44.921284+00:00 | UNKNOWN | `26856dca6c9a` | CHANGED | Status: QUARANTINED — do not mix or release. The persisted pipeline artifact is stale … |
| 5 | `L_Homme_Structural_Chassis_30mL_EDT.md` | pre-binding v1 (no binding schema) | 2026-07-29T00:25:33.254193+00:00 | UNKNOWN | `177ca5348c3c` | CHANGED | Status: QUARANTINED — do not mix or release. The persisted pipeline artifact is stale … |
| 6 | `La_Nuit_de_LHomme_Realistic_Reconstruction_30mL_EDT.md` | pre-binding v1 (no binding schema) | 2026-07-27T17:20:51.210325+00:00 | UNKNOWN | `b4c0ac25400a` | CHANGED | Status: QUARANTINED — do not mix or release. The persisted pipeline artifact is stale … |
| 7 | `La_Nuit_de_LHomme_Structural_Chassis_30mL_EDT.md` | pre-binding v1 (no binding schema) | 2026-07-29T00:26:09.367015+00:00 | UNKNOWN | `1d91ce9706c9` | CHANGED | Status: QUARANTINED — do not mix or release. The persisted pipeline artifact is stale … |
| 8 | `Osmanthus_Aventus_Explorer_30mL_EdP.md` | pre-binding v1 (no binding schema) | 2026-07-23T19:04:58.499956+00:00 | UNKNOWN | `cc329fbecdc2` | CHANGED | Status: QUARANTINED — do not mix or release. Allyl Cyclohexyl Propionate is … |
| 9 | `Osmanthus_Dark_Crystal_30mL_EdP.md` | pre-binding v1 (no binding schema) | 2026-07-26T23:30:37.704053+00:00 | UNKNOWN | `ec87f1c59c3f` | same | Status: QUARANTINED — current modeled headspace contradicts the osmanthus-led … |
| 10 | `Osmanthus_Explorer_30mL_EdP.md` | pre-binding v1 (no binding schema) | 2026-07-23T19:05:28.023211+00:00 | UNKNOWN | `ebad7dc947c0` | CHANGED | Status: QUARANTINED — do not mix or release. Osmanthus Absolute (volume … |
| 11 | `Prada_LHomme_Architecture_Control_30mL_EdT.md` | formula-artifact-binding-v1 | 2026-08-03T02:32:34.724937+00:00 | `9c75aa2a7f2da0dcc6fa87d79dd1b2c59c990a08a98e77d2a82a1244fa45253c` | `4390b955cf0a` | same | Status: QUARANTINED — do not mix or release. The persisted pipeline artifact is stale … |
| 12 | `Prada_LHomme_From_Scratch_30mL_EdP.md` | pre-binding v1 (no binding schema) | 2026-07-28T11:01:46.976907+00:00 | UNKNOWN | `332d1e98ede9` | CHANGED | Status: QUARANTINED — do not mix or release. The persisted pipeline artifact is stale … |
| 13 | `Prada_LHomme_Luxury_Orris_30mL_EdT.md` | pre-binding v1 (no binding schema) | 2026-07-27T02:28:07.772080+00:00 | UNKNOWN | `74b9ca5d2d72` | CHANGED | Status: QUARANTINED — do not mix or release. The persisted pipeline artifact is stale … |
| 14 | `Y_LHomme_Luxe_30mL_EDT.md` | pre-binding v1 (no binding schema) | 2026-07-27T03:50:21.671871+00:00 | UNKNOWN | `d75e25e0f813` | CHANGED | Status: QUARANTINED — do not mix or release. The live stock contract fails … |

Notes:

- Immediate parent: `none recorded` for all 14 (the artifacts' renderers did not bind parents).
- Exact composite input hash: `UNKNOWN` for 13 of 14 — the pre-binding `perfume_pipeline_run_evidence_v1` renderer stored per-axis hashes (`inventory_sha256`, `scientific_inputs_sha256`, `pipeline_source_sha256`, `config_sha256`) and an artifact hash, but never a composite `analysis_input_sha256`. Those per-axis values are preserved in `_lane_out\L14_artifact_details.json`.
- 12 of 14 formula definitions have changed since the analysis; 2 (`Osmanthus_Dark_Crystal`, `Prada_LHomme_Architecture_Control`) still describe the current bytes.
- Disposition for all 14: **historical/inactive registry entry.** They are already quarantined for their own stock/identity/claim reasons (not merely staleness), so no successor should be created without an explicit user decision to revive the line. Regenerating them would not clear those reasons.

## 3. The forty-nine UNBOUND_LEGACY artifacts

Uniform cause: the formula carries an embedded `## Pipeline Analysis` block but no parseable binding manifest, so the validator returns `UNBOUND_LEGACY` / `missing_or_invalid_manifest`. None of the 49 carries any 64-hex provenance hash inside the analysis block. They are non-blocking but must never be cited as current evidence.

Composition: 21 `classical_study` files, 1 `competitors` file, 6 stubs with no analysis content, 1 pointer (analysis stored outside the formula file), 42 full legacy analyses (counted mechanically from `L14_artifact_details.json`). Last commit: 48 files `2026-07-15T02:51:55+07:00 00bbc816`; `La_Nuit_de_Bleu_Chamomile_30mL_EDP.md` `2026-07-23T08:35:48+07:00 95b79216`.

| # | file | artifact chars | artifact kind | last commit | disposition |
| --- | --- | --- | --- | --- | --- |
| 1 | `Bleu_Carbon_Ellena_30mL_EDP.md` | 8736 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 2 | `Bleu_Carbon_Ellena_v2_30mL_EDP.md` | 3150 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 3 | `classical_study\01_Eau_de_Cologne_4711_30mL_EdC.md` | 10954 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 4 | `classical_study\02_Citrus_Aromatic_Eau_Sauvage_30mL_EdT.md` | 161 | stub | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 5 | `classical_study\03_Rose_Soliflore_30mL_EdP.md` | 12883 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 6 | `classical_study\04_Floral_Bouquet_Quelques_Fleurs_30mL_EdP.md` | 14397 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 7 | `classical_study\05_White_Floral_Fracas_30mL_EdP.md` | 13798 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 8 | `classical_study\06_Muguet_Diorissimo_30mL_EdP.md` | 12086 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 9 | `classical_study\07_Carnation_Bellodgia_30mL_EdP.md` | 11973 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 10 | `classical_study\08_Powdery_Floral_Apres_LOndee_30mL_EdP.md` | 13065 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 11 | `classical_study\09_Green_Floral_No19_30mL_EdP.md` | 12365 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 12 | `classical_study\10_Floral_Aldehydic_No5_30mL_EdP.md` | 13500 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 13 | `classical_study\10_No5_Niche_House.md` | 14733 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 14 | `classical_study\11_Classic_Fougere_Fougere_Royale_30mL_EdT.md` | 11140 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 15 | `classical_study\12_Aromatic_Fougere_Azzaro_30mL_EdT.md` | 2187 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 16 | `classical_study\13_Classic_Chypre_Coty_30mL_EdP.md` | 13938 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 17 | `classical_study\14_Floral_Chypre_Miss_Dior_30mL_EdP.md` | 14035 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 18 | `classical_study\15_Fruity_Chypre_Mitsouko_30mL_EdP.md` | 14766 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 19 | `classical_study\16_Green_Chypre_Vent_Vert_30mL_EdP.md` | 12756 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 20 | `classical_study\17_Leather_Chypre_Bandit_30mL_EdP.md` | 14770 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 21 | `classical_study\18_Classic_Oriental_Shalimar_30mL_EdP.md` | 13794 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 22 | `classical_study\19_Soft_Oriental_Jicky_30mL_EdP.md` | 13967 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 23 | `classical_study\20_Floral_Oriental_LHeure_Bleue_30mL_EdP.md` | 14774 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 24 | `competitors\MITH_Legend_30mL_EDP.md` | 3961 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 25 | `Cuir_Obscur_GCMS_DHP_30mL_Extrait.md` | 217 | stub | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 26 | `Cuir_Obscur_Luxe_DHP_30mL_Parfum.md` | 198 | stub | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 27 | `Cuir_Obscur_Profond_DHP2014_Niche_30mL_EdP.md` | 16122 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 28 | `Demachy_DHC_EDP_Optimized_30mL.md` | 13397 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 29 | `DHI_2025_Niche_House_30mL_EdP.md` | 13463 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 30 | `DHI_Niche_House_30mL_EdP.md` | 44 | stub | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 31 | `DHP_2025_Niche_House_30mL_EdP.md` | 13929 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 32 | `DHP_Niche_House_30mL_EdP.md` | 14355 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 33 | `Fougere_Herbier_30mL_EDP.md` | 5672 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 34 | `Iris_Lumiere_Profonde_DHI2025_Niche_30mL_EdP.md` | 15329 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 35 | `Iris_Sable_Profond_DHP2025_Niche_30mL_EdP.md` | 13043 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 36 | `Iris_Sombre_Niche_House_30mL_EdP.md` | 19604 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 37 | `L_Homme_Luxe_30mL_EdP.md` | 12993 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 38 | `La_Nuit_de_Bleu_Chamomile_30mL_EDP.md` | 17091 | legacy analysis (unbound) | 2026-07-23 95b79216 | historical/inactive registry entry |
| 39 | `La_Nuit_de_LHomme_Luxe_30mL_EDT.md` | 12285 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 40 | `La_Part_des_Anges_30mL_Extrait.md` | 4321 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 41 | `LHomme_Iris_Poudree_30mL_EdP.md` | 3999 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 42 | `MM5_Bangkok_Blossom_30mL_EDP.md` | 6302 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 43 | `Opus_V_Woods_Symphony_30mL_EdP.md` | 70 | stub | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 44 | `Osmanthus_Iris_Jasmine_Triptych_15mL_EdP.md` | 10941 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 45 | `osmanthus_tuberose_cocoa.md` | 8844 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 46 | `Pineapple_Chypre_Luxe_30mL_Extrait.md` | 70 | stub | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 47 | `Reflection_Man_Luxe_30mL_Extrait.md` | 1962 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |
| 48 | `Vetiver_Classique_V5_50mL_EDP.md` | 266 | pointer | 2026-07-15 00bbc816 | historical/inactive registry entry (analysis lives outside the artifact at `_vetiver_classique_v5_analysis.txt`) |
| 49 | `White_Suede_Honey_Opoponax_Amber_30mL_EdP.md` | 12854 | legacy analysis (unbound) | 2026-07-15 00bbc816 | historical/inactive registry entry |

Exception rule for this group: the disposition is *historical/inactive by default*. If the user names any of these as a live line — the likely candidates by content are `L_Homme_Luxe`, `La_Nuit_de_LHomme_Luxe`, `Iris_Sombre_Niche_House`, `DHI_2025_Niche_House`, `DHP_2025_Niche_House`, `MM5_Bangkok_Blossom`, `White_Suede_Honey_Opoponax_Amber`, `Opus_V_Woods_Symphony`, `Vetiver_Classique_V5` — that entry needs a **new successor artifact** before any of its numbers are used, because nothing in the current file binds the analysis to today's evidence.

## 4. Minimal action list

1. **Decide the seven STALE rows.** This is the only change needed to clear the artifact gate's FAIL, because `STALE`/`TAMPERED` is the entire blocking set:
   - Option A (successor): regenerate DPP-01-R1 → DPP-01-R2 → DPP-03-R1 → DPP-03-R2 → DPP-02-R1 → DPP-02-R2, then AHS v2 (only after its canonical inventory sync hold lifts); re-run `artifact-verify` and expect `STALE 0`.
   - Option B (retire): record the line as inactive in the registry; the artifact stops being a live claim and stops blocking.
   - Do not repin or hand-edit the manifests; the repair must come from a real run.
2. **Classify the 14 QUARANTINED as historical/inactive.** No regeneration, no repinning; they stay fail-closed and non-blocking. Successors only on explicit revival of a line.
3. **Classify the 49 UNBOUND_LEGACY as historical/inactive**, except any line the user declares live, which then needs a successor. The 21 `classical_study` entries and the 6 stubs need no further work.
4. **Fix the structural gaps the report exposes** (bookkeeping, not science): 13 quarantined artifacts have no composite input hash because they predate the binding schema; 66 of 70 have no parent binding; and `Vetiver_Classique_V5` keeps its analysis outside the formula file so no validator can bind it.
5. **Keep the historical receipts byte-for-byte** (per the acceptance record). This review changed none of them.

Estimated effort: seven bounded pipeline runs (only if the successor option is chosen), one registry-classification pass over 63 records, zero backend/adapter work.

## What this means for the approach

The artifact problem is far smaller than "526 artifacts" suggests. Of the 70 non-current artifacts, **63 are non-blocking** (`14 QUARANTINED + 49 UNBOUND_LEGACY`) and the right disposal for them is almost certainly a single registry classification pass, not regeneration; the 456 `NONE` rows are not artifacts at all and are explicitly non-blocking. Only the seven `STALE` rows hold the gate red, and their disposition hinges on one user decision the local files cannot make for me: are the six bench-pending DPP formulas and the AHS reference still live lines?

The sharpest sub-finding is lineage: `DPP-01-R2` and `DPP-03-R2` are bound to R1 hashes that have since been superseded, so regenerating the R2 artifacts before the R1 bases are finalized would silently rebind them to different parents. Any successor plan must order R1 before R2. The AHS row is the one stale artifact that is *not* safe to regenerate yet, because its own header declares a canonical inventory sync hold.

If the answer to "are these lines live?" is no, the cheapest correct finish is: retire the seven to inactive, classify the 63, and stop — a bookkeeping day, not a consolidation project. If the answer is yes, seven pipeline runs plus one re-verification is still bounded. What would be the wrong use of effort is regenerating all 70, or treating `UNBOUND_LEGACY` noise as a defect to fix.
