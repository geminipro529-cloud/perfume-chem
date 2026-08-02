# Build C1 Thermophysical Data Contracts Design

Date: 2026-08-02
Status: accepted by Sol under the user's delegated implementation authority
Scope: Build C, Phase C1 only

## Objective

Create a condition-aware, provenance-rich, fail-closed property contract that
consumes Build B selected assertions without allowing generic JSON, hard-coded
scalars, extrapolation, or invented uncertainty to become authoritative physical
data. C1 defines representation and selection behavior only. It does not evaluate
thermodynamic equations, change a physical-model caller, migrate the database, or
promote an existing heuristic.

## Evidence and constraints

The C1 master contract requires:

- six explicit vapor-pressure representation families;
- coefficients plus their convention and units;
- valid temperature range, phase, purity, source, fit evidence, uncertainty,
  extrapolation policy, and identity scope;
- condition-exact requests backed by Build B selected assertions;
- selected value/model, unit, source, conditions, uncertainty,
  interpolation/extrapolation state, applicability, or a missing-data reason;
- standard uncertainty, interval, empirical distribution, covariance, bounded
  range, and unknown uncertainty states;
- withholding rather than release-grade extrapolation or false precision.

Current repository evidence:

- `LabPropertyObservation` already stores typed value shapes, canonical units,
  temperature, pressure, humidity, matrix, phase, purity, method, source links,
  uncertainty, applicability, provenance, and an immutable content hash.
- `LabSelectedAssertion` already stores exact requested identity/property/
  conditions, selection kind, interpolation state, propagated uncertainty,
  applicability, authority, and an immutable content hash.
- `selected_model_json` is intentionally generic and therefore cannot be trusted
  as a C1 model without a closed C1 schema.
- selected-assertion reconstruction currently exposes only a subset of the
  selected observation's condition, source, and uncertainty fields.
- `engine.uncertainty` assigns coarse source-name bands. Those are legacy gate
  heuristics and are not C1 measurement uncertainty.
- DeepLuna Fast job `DS-650cd3d41b1b6a799efa29ae1816d3b3` independently
  identified the same generic-model, reconstruction, fit-evidence, and heuristic-
  uncertainty gaps. Sol reproduced them from the working tree.

Primary-source checks support the representation choices without selecting an
equation:

- The [NIST Chemistry WebBook Antoine presentation](https://webbook.nist.gov/cgi/cbook.cgi?ID=C124389&Mask=1EFF&Plot=on&Type=ANTOINE&Units=CAL)
  declares the exact equation convention, pressure and temperature units,
  coefficient set, reference, and valid temperature range. C1 therefore cannot
  infer a coefficient convention from the word `ANTOINE`.
- [NIST Technical Note 1297](https://www.nist.gov/pml/nist-technical-note-1297)
  distinguishes standard, combined, expanded, and interval reporting and requires
  the evaluation basis to remain explicit.
- [NIST TN 1297 section 5](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-5-combined-standard-uncertainty)
  treats covariance as part of uncertainty propagation when appropriate.
- The [BIPM JCGM 100:2008 GUM](https://doi.org/10.59161/JCGM100-2008E)
  defines covariance-matrix semantics. C1 stores covariance only when names,
  dimensions, symmetry, and finite values are declared; it never manufactures a
  diagonal covariance from scalar confidence labels.

## Considered approaches

### A. Pure contracts plus a Build B reconstruction adapter — selected

Add immutable, validated records under `engine.physics`. A pure adapter consumes
the existing `lab-selected-assertion-reconstruction-v1` payload. The backend
reconstruction method is extended only to expose B2 fields already stored in the
database. No ORM table or migration changes.

Benefits:

- preserves Laboratory Beta as persistence authority;
- keeps `engine.physics` independent of SQLAlchemy and backend imports;
- rejects or withholds legacy/free-form model JSON;
- creates the stable contract needed by C2-C4;
- limits the backend change to additive reconstruction fields.

Cost: one explicit adapter must stay synchronized with the versioned B2
reconstruction schema.

### B. Add C1 columns and tables to Laboratory Beta — rejected for C1

This could enforce equation fields in SQL, but it would require a migration,
duplicate data already representable in `selected_model_json`, and couple the
future engine boundary to one storage layout. No inspected requirement proves a
migration is needed for C1.

### C. Validate generic dictionaries inside the backend service — rejected

This is smaller initially but leaves no pure canonical boundary, permits ambiguous
model payloads to spread, and risks inheriting heuristic uncertainty. It fails the
C0 ADR direction and makes later model routing persistence-dependent.

## Chosen architecture

```text
Laboratory Beta selected assertion
  -> reconstruct_selected_assertion (additive complete B2 fields)
  -> engine.physics B2 reconstruction adapter
  -> immutable SelectedPropertyAssertion
  -> PropertySelectionService.select(exact request, assertion)
  -> selected/advisory/withheld PropertySelectionResult
```

There is no database read inside `engine.physics`. The caller supplies one
explicitly identified B2 selected assertion. C1 does not silently search multiple
assertions or choose among conflicting authorities; B2 already owns that decision.

## Components

### `engine.physics.properties`

Owns the general property vocabulary and immutable records:

- `ThermophysicalProperty` covers vapor pressure, molecular weight, density,
  boiling point, enthalpy of vaporization, solvent/water solubility, logP/logKow,
  Henry constant, activity-coefficient parameters, diffusion/mass-transfer
  parameters, substrate sorption, heat capacity, and phase data.
- `CanonicalScope` stores canonical JSON plus SHA-256 for identity, conditions,
  applicability, source locators, distributions, and other nested declarations.
  This avoids mutable dictionaries inside frozen records and makes exact matching
  deterministic.
- `PropertyIdentity` carries the Build B identity scope and subject hash.
- `PropertyConditions` carries canonical conditions plus validated convenience
  fields for temperature, pressure, relative humidity, matrix, phase, and purity.
  Equality is exact canonical-scope equality.
- `PropertyDatum` preserves B2 numeric, categorical, interval, distribution, and
  censored value shapes with canonical unit and shape validation.
- `SourceReference` requires the B2 source-version/extraction identifiers or an
  explicit model-source declaration. A selected result without source authority
  is withheld.
- `UncertaintyDescriptor` is a closed tagged union for `STANDARD_UNCERTAINTY`,
  `INTERVAL`, `EMPIRICAL_DISTRIBUTION`, `PARAMETER_COVARIANCE`, `BOUNDED_RANGE`,
  and `UNKNOWN`. Numeric fields must be finite and shape-consistent. `UNKNOWN`
  carries no invented number.

### `engine.physics.vapor_pressure`

Owns `VaporPressureRepresentation` and these exact equation tags:

```text
MEASURED_TABLE
ANTOINE
WAGNER
DIPPR_STYLE
CLAUSIUS_CLAPEYRON
OTHER_DECLARED_FORM
```

Every representation includes:

- stable model identifier and version;
- identity scope;
- coefficient names, values, and units;
- a non-empty equation/convention declaration;
- pressure and temperature units;
- valid inclusive temperature range;
- phase and purity assumptions;
- source reference;
- optional measured table and fit evidence;
- uncertainty;
- `FORBID` or `ADVISORY_ONLY_WITH_WARNING` extrapolation policy;
- a deterministic content hash.

`MEASURED_TABLE` requires points and forbids equation coefficients. Other equation
types require coefficients. C1 stores the representation but never evaluates it.

### `engine.physics.selection`

Owns:

- `SelectedPropertyAssertion`, a persistence-neutral snapshot of one B2 selected
  assertion;
- `selected_assertion_from_b2_reconstruction`, the closed versioned adapter;
- `PropertyRequest`, including exact identity, property, conditions, claim grade,
  and explicit exploratory extrapolation permission;
- `PropertySelectionResult`, including selected value/model, unit, source,
  conditions, uncertainty, interpolation state, applicability, authority,
  missing-data reason, warnings, request hash, and assertion hash;
- `PropertySelectionService.select`, a deterministic fail-closed selector.

## Build B reconstruction extension

`reconstruct_selected_assertion` will add fields already present on
`LabPropertyObservation` to each candidate observation:

- pressure, relative humidity, phase, and purity;
- source version, extraction record, and source locator;
- replicate count and statistic;
- standard uncertainty and interval declaration;
- evidence class and review state;
- applicability domain and provenance activity.

The reconstruction schema name remains `lab-selected-assertion-reconstruction-v1`
because this is an additive response extension. Existing keys and meanings are
unchanged. Tests lock the added fields so a future incompatible change must use a
new schema version.

## Selection behavior

| Evidence state | Release-grade request | Exploratory request |
| --- | --- | --- |
| Exact, authorized, applicable, source-complete | select | select |
| Interpolated, authorized, applicable, explicitly represented uncertainty | select with interpolation status | select with interpolation status |
| Extrapolated model | withhold by default | select only if request opts in and model policy is `ADVISORY_ONLY_WITH_WARNING`; result is advisory and warned |
| Advisory B2 authority | withhold | advisory result only when the request allows advisory evidence |
| Withheld conflict/unknown, selection `NONE`, not applicable, identity/property/condition mismatch | withhold with exact reason | withhold with exact reason |
| Free-form or invalid selected model | withhold as unsupported model schema | withhold as unsupported model schema |
| Missing source or unknown required unit | withhold | withhold |

No branch substitutes a registry/profile scalar or calls a legacy estimator.

## Error and withholding model

Malformed contract construction raises `ThermophysicalContractError`. Expected
scientific absence does not raise; it returns a `WITHHELD` result with one of the
closed `MissingDataReason` values. This separates programmer/schema errors from
legitimate missing evidence.

All hashes are derived from canonical JSON using the repository's existing
`engine.calibration.hashing` implementation. Unknown fields in the B2 adapter are
ignored only at nested provenance payload boundaries; unknown top-level schema or
assertion fields fail closed.

## Testing and C1 exit gate

Tests will prove:

- every required property and equation tag exists;
- all six uncertainty shapes validate and malformed shapes fail;
- coefficient conventions/units/ranges are mandatory;
- measured tables and equation models have mutually exclusive required shapes;
- canonical hashes are stable across mapping order;
- B2 reconstruction maps complete observation and model evidence;
- exact and interpolated authorized assertions select;
- release-grade extrapolation withholds;
- exploratory extrapolation requires both request permission and explicit model
  policy and produces a warning/advisory result;
- identity, property, conditions, source, unit, authority, applicability, and
  model-schema failures return exact withholding reasons;
- no legacy property estimator is imported or called;
- the existing B2 focused suite remains green;
- no migration file or database is changed.

C1 passes only when the focused verifier/tests, lint/format, staged-scope check,
fresh DeepLuna Fast audit, and Sol reproduction are green. C2 remains closed until
that checkpoint is committed and post-commit verification passes.

## Explicit non-goals

- no equation evaluation or interpolation algorithm;
- no unit conversion engine;
- no thermodynamic model implementation;
- no activity-coefficient or diffusion model;
- no caller migration to `engine.physics`;
- no database migration or canonical data write;
- no change to current headspace, temporal, optimizer, or release behavior;
- no replacement of the honest C0 legacy skin-accounting fixture.

## Approval record

The user delegated implementation and permission decisions to Sol and explicitly
requested uninterrupted strict-phase execution without permission prompts. Sol
selected Approach A after local repository inspection, primary-source review, and
bounded DeepLuna gap audit. This approval does not waive any C1 executable gate.
