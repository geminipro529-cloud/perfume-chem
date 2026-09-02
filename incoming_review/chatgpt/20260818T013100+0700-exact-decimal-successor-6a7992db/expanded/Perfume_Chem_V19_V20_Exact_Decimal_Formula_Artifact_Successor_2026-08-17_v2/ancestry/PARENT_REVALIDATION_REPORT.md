# V19/V20 Formula-Artifact Revalidation Report

**Packet ID:** `PC-V19-V20-FORMULA-ARTIFACT-REVALIDATION-20260817-v1`  
**Packet hash:** `1e05c1a655458fbffadd848dfac3d582a500f7ef2b45afd734953d500cc52e44`  
**Parent formula package:** `Nine_Finished_Hedonic_High_Complexity_Perfumes_2026-08-16_v1.zip`  
**Parent SHA-256:** `f1e0f2aae2143fe2638c151032f686ee7b36579280445e86e1878c79b54f240b`  
**Current result:** `ARTIFACT_REPAIR_REQUIRED`  
**Quick verification:** `HOLD`  
**Release:** `BLOCKED`

## Decision

The nine-formula parent package passes byte identity, package CRC, source-hash, formula-file presence, formula/target hash binding, exact 1,000-part arithmetic, and active-fraction/product-basis structural checks. Exact-decimal validation found derived 30 mL dose-export residuals in six formulas; DHI12, EB, and EE reconcile exactly, while DHP25, AHS, ELIXIR, LHOMME, LANUIT, and BDCP require a successor export that recomputes dose fields from canonical Decimal parts. Quick verification also remains blocked by preparation, verification, lot, label-strength, species, planned-acquisition, and physical-pending holds.

The earlier row-count minimum, microtexture threshold PASS, anti-collapse PASS, and any aggregate quality score are now non-governing. V19/V20 requires complexity dimensions to remain separate.

## Parent artifact checks

| Check | Result |
|---|---|
| parent_zip_hash_matches_receipt | PASS |
| parent_zip_size_matches_receipt | PASS |
| parent_zip_crc_pass | PASS |
| parent_sidecar_matches_parent_zip | PASS |
| inventory_v5_hash_matches_formula_pack | PASS |
| formula_pack_parseable | PASS |

## Formula-artifact states

| Perfume | Artifact state | Quick verification | Stock holds | Product-basis rows | Signature hash |
|---|---|---|---:|---:|---|
| DHI12 | `STRUCTURAL_ARTIFACT_PASS__OPERATIONAL_HOLD` | `HOLD` | 8 | 2 | `9b38cd161ae286ba482e50293d29bb5612503c7eebc1246a5ff0f88567f23e5a` |
| DHP25 | `ARTIFACT_FAIL` | `HOLD` | 8 | 2 | `1388d0edd746b18f9c887a88c748b3a039c8acb470c57659adfb6f8b62d00bdc` |
| AHS | `ARTIFACT_FAIL` | `HOLD` | 7 | 1 | `9dbf5fc4fefa551038e0612e5c8c8e910b7f73897ae70f2681440fdff11bc810` |
| EB | `STRUCTURAL_ARTIFACT_PASS__OPERATIONAL_HOLD` | `HOLD` | 6 | 2 | `6c4610e0d665317462d2148245c106977d006648793f4cab8740575c7f7a3fd2` |
| EE | `STRUCTURAL_ARTIFACT_PASS__OPERATIONAL_HOLD` | `HOLD` | 9 | 1 | `9d060541cb1e2f1f7d5d3a0b5c5c9ac547d71a8ecedb25431cfa62dcbdb7fa5c` |
| ELIXIR | `ARTIFACT_FAIL` | `HOLD` | 7 | 3 | `81c9ef860d21a4deb6292285e0505201a249d31fcc7ab10d439f54954a117611` |
| LHOMME | `ARTIFACT_FAIL` | `HOLD` | 7 | 1 | `7a060f392c343494515f3821da00146258a4c42b69413e04a325c29167704b0c` |
| LANUIT | `ARTIFACT_FAIL` | `HOLD` | 4 | 3 | `9fe292830a9440e8c2086e9a60ee5abe3658c520e349c5aa90ec95607569489e` |
| BDCP | `ARTIFACT_FAIL` | `HOLD` | 7 | 2 | `b076d96f8137f364bab7897d48d5ddc28dbab9fe16fd500b321a331d41ccf6b5` |

## Exact-decimal arithmetic deltas

| Perfume | Stored dose total µL | Expected concentrate µL | Residual µL | State |
|---|---:|---:|---:|---|
| DHI12 | 6000.0000 | 6000.0 | 0.0000 | `PASS` |
| DHP25 | 7499.9993 | 7500.0 | -0.0007 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| AHS | 4499.9988 | 4500.0 | -0.0012 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| EB | 6000.0000 | 6000.0 | 0.0000 | `PASS` |
| EE | 6000.0000 | 6000.0 | 0.0000 | `PASS` |
| ELIXIR | 7499.9999 | 7500.0 | -0.0001 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| LHOMME | 4499.9982 | 4500.0 | -0.0018 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| LANUIT | 4499.9998 | 4500.0 | -0.0002 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| BDCP | 7500.0001 | 7500.0 | 0.0001 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |

These are derived export-field defects, not authorization to alter the canonical formula parts. Repair must be versioned and rehashed.

## Complexity dimensions, reported separately

| Perfume | Rows (diagnostic) | Systems | Phases | Bridges | Microtexture | Interactions | Stock holds | Aggregate authority |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| DHI12 | 74 | 9 | 6 | 11 | 18.9% | 9 | 8 | `WITHHELD` |
| DHP25 | 75 | 8 | 6 | 6 | 20.0% | 9 | 8 | `WITHHELD` |
| AHS | 72 | 7 | 6 | 8 | 19.4% | 9 | 7 | `WITHHELD` |
| EB | 73 | 10 | 6 | 12 | 19.2% | 9 | 6 | `WITHHELD` |
| EE | 72 | 9 | 6 | 8 | 19.4% | 9 | 9 | `WITHHELD` |
| ELIXIR | 75 | 8 | 6 | 6 | 16.0% | 9 | 7 | `WITHHELD` |
| LHOMME | 70 | 8 | 6 | 10 | 20.0% | 9 | 7 | `WITHHELD` |
| LANUIT | 73 | 8 | 6 | 12 | 19.2% | 9 | 4 | `WITHHELD` |
| BDCP | 79 | 10 | 6 | 10 | 19.0% | 9 | 7 | `WITHHELD` |

## Formula-signature and anti-chassis views

Formula signatures are preserved as separate material, sensory-system, family, phase, ablation, and stock-state vectors. Pairwise anti-chassis output reports each metric separately. No combined score, sensory-similarity claim, or PASS/FAIL threshold is applied.

## Ratio-bound n-ary records

27 clean-room ratio-bound records were derived from exact formula parts: dominant-system triads, temporal-relay triads, and bridge triads where available. They are formula-signature artifacts only and remain non-empirical.

## Stock-lineage gate

Open formula-row stock/preparation holds: **63**. Any row with preparation, verification, label-strength conflict, lot detail, species resolution, planned acquisition, or physical-pending status keeps quick verification on HOLD.

Product-basis rows remain valid named products but do not receive invented molecular composition or active fraction.

## Missing dependencies

- `UNIVERSAL_ACCORD_INTELLIGENCE_MODULE_v1.zip` — `EXACT_ORIGINAL_BYTES_UNAVAILABLE`
- `PERFUME_CHEM_CANONICAL_CUTOVER_READY_20260808_v2.zip` — `EXACT_ORIGINAL_BYTES_UNAVAILABLE`
- `Perfume_Chem_Physics_OAV_Decision_Model_v3_4_0_CALIBRATION_READY.zip` — `EXACT_ORIGINAL_BYTES_UNAVAILABLE`
- `perfume_chem_physics_oav_v3-3.4.0-py3-none-any.whl` — `EXACT_ORIGINAL_BYTES_UNAVAILABLE`

## Runtime and source-use boundary

- Runtime hardening remains diagnosed but undeployed.
- Only DeepLuna Chat is permitted for `perfume-chem-cheapluna-isolated`, using `cheapluna-chat / DIRECT_PRO / NO_LUNA`.
- DeepLuna Fast and alternate fallbacks remain disabled.
- The recovered Floral Heart Complexity Discovery Atlas and Complexity Model Discovery/Admission Engine parents remain quarantined and were not imported or used.
- This packet performs no repository write, package installation, canonical promotion, formula mutation, inventory mutation, or physical execution.

## Next closure

Close bound stock/preparation evidence first, then run repository-native formula-artifact quick verification only after an evidence-accepted V20 hardening implementation is deployed. Complexity reporting must remain dimensional throughout.
