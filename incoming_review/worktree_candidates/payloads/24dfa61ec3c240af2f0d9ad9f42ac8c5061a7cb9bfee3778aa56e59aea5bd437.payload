# Task 3 temporal OAV field and test digest

Scope: low-level inventory only. Sol owns architecture, implementation, science, and acceptance.

## Frozen request fields

- `TemporalOAVEvidenceRequest`: `formula_sha256`, `dose_receipt_sha256`, `protocol_sha256`, `measurement_context_sha256`, `cells`.
- `OAVTimepointEvidenceInput`: `key`, `exact_stock_ref`, `active_mass_g`, `headspace_interval`, `threshold_interval`, `model_tier`, `context_sha256`.
- `OAVTimepointKey`: `protocol_sha256`, `sample_id`, `material_id`, `time_seconds`, `endpoint`.
- `OAVIntervalEvidence`: `p05`, `p50`, `p95`, each a `QuantitativeEvidence`.
- Model tiers: `T0_UNKNOWN`, `T1_TRANSFERRED`, `T2_MODELED`, `T3_CALIBRATED_MODELED`, `T4_MEASURED`.

## Existing V2 behavior that must remain compatible

- `OAVMaterialEvidenceInput`, `OAVEvidenceRequest`, `OAVEvidenceResult`, and `evaluate_oav_evidence` remain unchanged.
- Existing V2 states are `STRICT_MEASURED`, `MODELED_SCREEN`, `PARTIAL`, `ABSTAINED`, `INVALID`.
- Existing row checks cover duplicate material rows, request-context mismatch, unit mismatch, nonpositive threshold, incomplete stock/active-dose lineage, transferred evidence, and natural/preblend uncertainty.
- Existing authority is always false for sensory, hedonic, and release.
- Existing `oav_evidence_request_from_formula_state` labels simulator headspace modeled and absent thresholds unknown.

## Task 3 required observable behaviors

- Temporal result states: `STRICT_MEASURED_TIME_SERIES`, `MODELED_SCREEN`, `PARTIAL`, `ABSTAINED`, `INVALID`.
- Duplicate canonical cells and undeclared cells fail closed; declared-but-absent cells remain missing.
- Time uses nonnegative integer seconds and protocol-declared timepoints.
- Headspace/threshold interval units and exact threshold scope must be compatible.
- OAV interval is `headspace p05 / threshold p95`, `headspace p50 / threshold p50`, `headspace p95 / threshold p05`.
- Known interval values are positive and ordered; missing intervals remain unknown.
- Measured and modeled cells remain in separate output collections.
- Naturals/preblends are whole-material screens or explicit constituent evidence; never silently summed.
- Missing exact-stock/active-dose lineage cannot become strict measured evidence.
- Canonical bytes, result hash, lineage hashes, export/import round trip, blockers, limitations, and all-false authority are required.

## Required negative-test inventory

1. Duplicate canonical cell.
2. Cell outside the declared protocol schedule.
3. Declared cell absent from observations.
4. Fractional or negative time.
5. Headspace/threshold unit mismatch.
6. Threshold source/matrix/method/temperature/application/endpoint incompatibility.
7. Nonpositive, inverted, or mixed-known/unknown interval.
8. Natural/preblend constituent ambiguity.
9. Missing exact-stock or active-dose lineage.
10. Mixed measured/modeled series kept separate and downgraded to partial.
11. Same logical input in different row order produces identical canonical result bytes.
12. Serialized result restores exactly and retains all-false authority.
