# Build C3 Versioned Model Interface and Applicability Design

Date: 2026-08-02
Status: accepted by Sol under the user's standing delegation
Phase parent: `f5ae19227e75dee30fe101b4324e1f54283174e3`
DeepLuna inventory: `DS-4ee6afcbb8f56c86578301d1ec1b2bd2` (`PASS`,
`FLASH`, `NO_LUNA`; supplemental only)

## Purpose

C3 adds the versioned contract and routing boundary required before any new
equilibrium, partition, dynamic-release, uncertainty, or comparison model can
become canonical. It does not implement a scientific equation, validate a model,
change a production caller, create persistence, or authorize C4.

The design satisfies the authoritative C3 requirements while preserving the C0
ownership decision: one exact model family and version is selected, its complete
identity and applicability are bound into every result, and an out-of-domain
request abstains before model computation.

## Current authority and reusable contracts

- `engine.physics.properties` supplies canonical mappings, closed
  `ThermophysicalProperty` identifiers, and six immutable uncertainty shapes.
- `engine.physics.selection` supplies fail-closed Build B assertion selection.
- `engine.physics.matrix_environment` supplies complete, hashed formula, matrix,
  and application-environment context through `MatrixAwareModelRequest`.
- The C0 ADR keeps existing headspace and temporal behavior as compatibility or
  advisory paths until their later Build C gates pass.
- C0 records UNIFAC as an inactive/data-only stub and COSMO-RS as unsupported.
  C3 must represent those family names without claiming executable capability.

DeepLuna independently found the same reusable boundaries and gaps. Its compact
terminal packet truncated some findings and exposed no source citations, so Sol
accepts no provider claim as authority; the canonical files above were checked
locally.

## Public vocabulary

C3 introduces `engine.physics.model_interface` with these closed enums.

`ModelOperation` values:

- `predict_equilibrium_headspace`
- `predict_dynamic_release`
- `estimate_partition_coefficient`
- `evaluate_applicability`
- `propagate_uncertainty`
- `compare_models`

`ModelFamily` values:

- `IDEAL_RAOULT_BASELINE`
- `HENRY_LAW_DILUTE_BASELINE`
- `MEASURED_LOOKUP_INTERPOLATION`
- `EMPIRICAL_MATRIX_CORRECTION`
- `UNIFAC_OR_MODIFIED_UNIFAC`
- `IMPORTED_COSMO_RS`
- `MEASURED_PARTITION_MODEL`
- `DYNAMIC_SEMI_EMPIRICAL_MODEL`
- `LEGACY_HEURISTIC_ADAPTER`

`ApplicabilityState` values are exactly:

- `IN_DOMAIN`
- `NEAR_DOMAIN_WITH_WARNING`
- `OUTSIDE_APPLICABILITY_DOMAIN`
- `INSUFFICIENT_INPUT`
- `MODEL_NOT_VALIDATED`

Additional closed states distinguish model availability, result computation vs
abstention, and evidence class. An unavailable family is visible and cannot be
selected as if it were an implementation.

## Immutable model release

`ModelSelector` identifies one exact family and model-version string.

`ModelRelease` embeds:

- selector;
- parameter-set version;
- Git code commit;
- implementation and parameter-set hashes;
- optional coefficient-set, decomposition, and training-data hashes;
- a complete `ApplicabilityDomain` snapshot and hash;
- supported operations;
- availability and any unavailability reason;
- evidence class;
- OAV-screening permission;
- permitted and forbidden claim wording; and
- a deterministic content hash.

All release fields are immutable. The release hash changes if code, parameters,
coefficients, decomposition, training data, applicability, operations, evidence,
or claim policy changes. A router rejects two different releases bound to the
same selector. The changed release must use a new model version before it can be
registered. Results embed the complete old release snapshot, not a mutable
registry pointer, so old predictions remain linked to the old version.

## Applicability domain

`ApplicabilityDomain` is typed and versioned. It contains:

- domain ID and version;
- supported identity IDs and chemical classes;
- supported functional groups;
- supported matrix stages plus an explicit canonical matrix-range mapping;
- optional concentration, temperature, and pressure ranges with units;
- supported phase behaviors;
- supported application-environment kinds;
- required thermophysical properties;
- a canonical training/calibration-domain mapping;
- known failure modes; and
- a content hash.

`ApplicabilityContext` carries the request-side identities, classes, functional
groups, optional concentration, phase behavior, available property identifiers,
and training/calibration tags. Formula, matrix, environment, temperature, and
pressure remain embedded in the C2 context rather than being duplicated as an
unlinked string.

`ApplicabilityResult` binds one state to the model-domain hash and request hash,
with reasons, missing inputs, and warnings. Shape invariants are fail-closed:

- `NEAR_DOMAIN_WITH_WARNING` requires a warning;
- `OUTSIDE_APPLICABILITY_DOMAIN` requires a reason;
- `INSUFFICIENT_INPUT` requires a missing-input entry; and
- `MODEL_NOT_VALIDATED` requires a reason.

Domain interpretation remains model-specific. C3 does not invent one generic
chemical-class or concentration inference algorithm. A model adapter evaluates
its own declared domain; the router validates and enforces the returned state.

## Request and result envelopes

`ModelInputReference` is a nonblank role/ID plus a lowercase SHA-256. References
are sorted and unique.

`VersionedModelRequest` contains:

- request ID;
- exact operation;
- exact requested selector;
- the complete C2 `MatrixAwareModelRequest` snapshot;
- `ApplicabilityContext`;
- all extra input IDs and hashes; and
- a deterministic request hash.

`ModelOutput` contains an output quantity name, canonical unit, canonical payload,
and content hash. It is deliberately shape-neutral so later phases can carry a
scalar, component map, time series, or comparison without C3 pretending those
scientific schemas already exist.

`VersionedModelResult` contains every authoritative C3 field:

- operation and computed/abstained status;
- requested selector and complete bound `ModelRelease`;
- full request and input hashes;
- full matrix/environment conditions through the embedded C2 request;
- output quantity/unit/payload when computed;
- `UncertaintyDescriptor`;
- `ApplicabilityResult`;
- missing inputs and warnings;
- evidence class and OAV-screening permission;
- permitted and forbidden claim wording;
- optional explicit `FallbackDisclosure`; and
- deterministic result hash.

A computed result requires an output and applicability of `IN_DOMAIN` or
`NEAR_DOMAIN_WITH_WARNING`. An abstained result has no output and cannot feed OAV
screening. `OUTSIDE_APPLICABILITY_DOMAIN`, `INSUFFICIENT_INPUT`, and
`MODEL_NOT_VALIDATED` always require abstention.

## Fallback disclosure

The canonical router never chooses a fallback. It resolves the exact requested
selector or fails closed.

`FallbackDisclosure` exists only so an imported or legacy result cannot hide a
fallback. If a result's bound model differs from the requested selector, the
result is invalid unless it includes all four required fields:

- requested model;
- reason unavailable;
- fallback model;
- authority downgrade.

The disclosure must match both selectors and they must differ. C3 adds no route
that automatically creates such a result.

## Adapter and router boundary

`VersionedModelAdapter` is a runtime-checkable protocol with:

- immutable `release`;
- `evaluate_applicability(request)`; and
- `compute(request, applicability)` returning a typed computation payload.

`VersionedModelRouter` receives a closed tuple of adapters at construction. It
rejects duplicate selectors and release drift. Its typed methods are:

- `predict_equilibrium_headspace()`;
- `predict_dynamic_release()`;
- `estimate_partition_coefficient()`;
- `evaluate_applicability()`;
- `propagate_uncertainty()`; and
- `compare_models()`.

For an answer-producing method, the router:

1. verifies that the request names the matching operation;
2. resolves only the exact selector;
3. rejects an unsupported operation;
4. returns `MODEL_NOT_VALIDATED`/abstained for an unavailable release;
5. calls applicability before computation;
6. abstains without calling compute for outside, insufficient, or unvalidated
   states; and
7. constructs the result from the immutable release and request snapshots.

`compare_models()` accepts already explicit, compatible versioned results and
returns their selectors and result hashes. It does not rank, average, replace,
or select a model and therefore cannot become a hidden fallback.

## Model-family capability truth in C3

| Family | C3 status |
| --- | --- |
| Ideal Raoult baseline | Interface/adapter slot only; C4 implements and tests arithmetic |
| Henry-law dilute baseline | Interface/adapter slot only; later implementation must prove applicability |
| Measured lookup/interpolation | Interface/adapter slot only; no measured headspace capability is promoted |
| Empirical matrix correction | Interface/adapter slot only; C5 requires calibration evidence |
| UNIFAC or modified UNIFAC | Explicitly unavailable; C0 stub remains inactive |
| Imported COSMO-RS | Explicitly unavailable; no interface/import exists yet |
| Measured partition model | Interface/adapter slot only; no endpoint is promoted |
| Dynamic semi-empirical model | Interface/adapter slot only; C6 owns implementation/validation |
| Legacy heuristic adapter | Representable only with legacy evidence and claim restrictions; no caller is migrated in C3 |

An enum member or adapter slot is not an implementation claim.

## Serialization and validation

Every C3 value object is frozen and uses an exact-key parser. Mapping parsers
reject missing keys, unknown keys, wrong schemas, invalid enums, booleans where a
number is required, non-finite values, malformed hashes, duplicate entries, and
content-hash mismatches. Collection ordering is canonical before hashing.

C3 reuses C1 `CanonicalScope`, `UncertaintyDescriptor`, and
`ThermophysicalProperty`, and C2 context types. It imports no backend,
SQLAlchemy, database, workbench, optimizer, legacy estimator, headspace, or
temporal implementation.

## Test and mutation strategy

Focused tests will prove:

- the six operation names, nine families, and five applicability states are
  closed and exact;
- all applicability-domain fields affect the hash and round-trip strictly;
- all model release/version inputs affect the hash;
- duplicate selector registration rejects release drift while a new version is
  accepted;
- result envelopes bind complete model, parameter, code, input, matrix,
  environment, uncertainty, applicability, evidence, OAV, and claim state;
- parser tampering fails;
- no requested selector is replaced by a different model;
- a represented fallback cannot omit any disclosure field;
- outside/insufficient/unvalidated applicability abstains and never calls the
  adapter's compute method;
- near-domain computation requires and preserves a warning;
- old results retain their old release snapshot after another version exists;
- comparison is explicit and non-ranking; and
- C0-C2 compatibility and package exports remain intact.

Mutation checks temporarily remove duplicate-version protection and the
out-of-domain compute guard; the matching tests must fail before restoration.

## Scope

Authorized implementation paths:

- this design;
- one C3 implementation plan;
- `engine/physics/model_interface.py`;
- `engine/physics/__init__.py`;
- `tests/test_c3_model_interface.py`;
- the C0-C3 verifier shard manifest if the complete suite requires it; and
- `docs/verification/c3/**` for the gate.

No production caller, compatibility model, database, migration, generated
scientific artifact, Laboratory Beta record, optimizer, workbench, headspace,
temporal, mixture, or solvent-ledger path is authorized.

## Exit gate

C3 passes only when committed-tree tests prove exact model selection, no silent
fallback, stable immutable version binding, and mandatory out-of-domain
abstention; all C0-C2 compatibility, full-suite, static, archive, protected-state,
scope, DeepLuna, Sol-reconciliation, and postcommit gates must also be green.

C4 remains closed until that evidence is committed and the C3 decision is PASS.
