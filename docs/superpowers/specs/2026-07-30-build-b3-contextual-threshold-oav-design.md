# Build B3 Contextual Threshold and OAV Authority Design

## Status and boundary

This design freezes Build B3 only. Build B4 and later work remain blocked.
Build B2 is the canonical observation and selected-assertion substrate. B3
specializes that substrate; it does not create a parallel scientific source
store and does not promote the legacy ODT dictionaries.

The existing `engine/odor_thresholds.py`,
`engine/pipeline/oav_intelligence.py`, `tests/test_oav_authority.py`, and
`tests/test_oav_intelligence.py` paths contain user work. B3 leaves those paths
unchanged. The current engine remains legacy/exploratory until a later,
separately gated integration consumes B3 authority records.

## Decisions

### 1. Context is attached to a B2 observation

`lab_threshold_observation_contexts` is append-only and has a one-to-one
foreign key to `lab_property_observations`.

A threshold context can be created only when the linked B2 observation:

- has `property_type = ODOR_THRESHOLD`;
- contains explicit `grade`, `purity`, and `stereochemistry` identity
  dimensions in the hashed B2 subject identity;
- has the exact B1 source/extraction/locator authority already enforced by B2;
- has positive finite threshold support when it is numeric; and
- is addressed by its immutable observation ID.

The context stores:

- endpoint: detection, recognition, difference, rejection, or other;
- route;
- medium;
- matrix specification state and exact matrix composition;
- concentration basis;
- apparatus;
- psychophysical procedure;
- population;
- training state;
- sample size; and
- a content digest.

Temperature, pressure, relative humidity, statistic, uncertainty, evidence
class, review state, source, locator, method, and quality flags remain on the
linked B2 observation and are not duplicated.

### 2. OAV is an explicit append-only assessment

`lab_oav_assessments` records an assessment by immutable ID. It links:

- one B2 concentration observation;
- one B2 selected threshold assertion; and
- the selected threshold observation and contextual record resolved by that
  assertion.

The concentration observation must have `property_type = CONCENTRATION`, a
positive numeric value, the same exact B2 identity scope and identity digest
as the threshold observation, and an applicability payload containing
`medium`, `matrix_specification_state`, `matrix_composition`,
`concentration_basis`, `route`, and `model_context`.

The assessment stores either:

- `COMPUTED` with one finite nonnegative OAV and no mismatch codes; or
- `WITHHELD` with no OAV and one or more stable mismatch codes.

The assessment is append-only, content-addressed, and never resolved through a
"latest" query.

### 3. Compatibility is fail-closed

Mismatch codes have this stable order:

1. `MISSING_THRESHOLD`
2. `IDENTITY_SCOPE_MISMATCH`
3. `THRESHOLD_MEDIUM_MISMATCH`
4. `THRESHOLD_ENDPOINT_MISMATCH`
5. `THRESHOLD_ROUTE_MISMATCH`
6. `THRESHOLD_UNIT_INCOMPARABLE`
7. `THRESHOLD_MATRIX_UNSPECIFIED`
8. `THRESHOLD_AUTHORITY_TOO_LOW`
9. `CONCENTRATION_NOT_COMPARABLE`
10. `MODEL_OUTSIDE_APPLICABILITY_DOMAIN`

Every applicable code is returned once in that order. Any code withholds OAV.
There is no heuristic fallback.

Compatibility requires:

- equal B2 identity scope and subject-identity digest;
- equal endpoint and route;
- equal medium and exact canonical matrix composition;
- a specified threshold matrix;
- equal concentration basis;
- units in one explicit directly convertible convention family;
- compatible temperature, pressure, and humidity;
- an accepted high-authority threshold assertion and observation;
- a comparable high-authority concentration observation; and
- an exact/in-domain selection rather than an unsupported model or
  extrapolation.

Direct convention conversion is limited to scale changes within one declared
basis:

- fraction, ppm, ppb, and ppt; or
- mg/m3 and ug/m3.

Cross-basis conversion is withheld. Solution thresholds never become air
thresholds by conversion alone. The assessment preserves explicit conversion
prerequisites for future audited converters: molecular weight, temperature,
pressure, gas-behavior assumption, density, concentration definition, and
partition model.

### 4. Strict science and claim limits

Strict mode is mandatory for canonical OAV assessments. Threshold assertions
must be `AUTHORIZED_FOR_SCOPED_PROPERTY`; observations must be accepted and
must have evidence class `MEASURED`, `LITERATURE_DERIVED`, or
`EMPIRICALLY_CALIBRATED`.

An OAV assessment permits screening only:

- prioritizing GC-O work;
- prioritizing recombination, omission, or addition experiments;
- finding gross anomalies; and
- comparing candidates under identical assumptions.

OAV alone never authorizes exact intensity, percentage contribution,
pleasantness, similarity, family assignment, longevity, sillage, skin
performance, release, or deletion because OAV is below one. These prohibited
claims are persisted on every assessment.

### 5. Legacy ODT records remain quarantined

`lab_legacy_threshold_records` is an append-only quarantine for deterministic
legacy imports. Each air and ethanol scalar becomes a separate record with:

- the original material key, medium, value, and unit;
- the exact original verification token;
- the original source and note payload;
- `LEGACY_CONTEXT_INCOMPLETE` authority; and
- a content digest.

The importer preserves `DERIVED`, `UNVERIFIED`, `HEURISTIC`, and `UNKNOWN`
verbatim. Missing verification becomes `UNKNOWN`; no status is upgraded.
Legacy records do not reference B1 extraction records, do not become B2
observations, cannot be selected assertions, and cannot support canonical OAV.
The Alembic migration creates schema only and imports no runtime dictionary
values.

## Schema invariants

- All three B3 tables are append-only at the database level.
- Threshold context observation IDs and content digests are unique.
- Assessment shapes enforce OAV XOR mismatch codes.
- Assessment links use `ON DELETE RESTRICT`.
- Legacy values are positive finite scalars and retain original status.
- All JSON collections are canonicalized before hashing.
- Repository reads are explicit-ID or exact-hash reads only.

## Compatibility strategy

B3 changes only backend canonical authority modules, the B3 migration, and
focused backend tests. It does not alter current engine ODT/OAV results. The
current engine's unconditional scalar division remains classified as legacy
heuristic behavior and gains no release authority from B3.

## Exit gate

B3 passes only when:

- RED tests prove every mismatch code and every claim prohibition;
- compatible contexts compute the expected dimensionless ratio;
- every context mismatch produces `WITHHELD` with no OAV;
- legacy status preservation and non-promotion are tested;
- migration upgrade/downgrade, append-only guards, backup/restore, and B1/B2
  compatibility tests pass;
- Ruff and scoped mypy pass; and
- a bounded Fast-only read audit finds no blocking B3 defect, followed by
  independent Sol verification.
