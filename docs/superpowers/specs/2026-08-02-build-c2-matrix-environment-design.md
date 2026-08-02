# Build C2 Matrix and Application-Environment Design

Date: 2026-08-02
Status: accepted by Sol under the user's delegated implementation authority
Scope: Build C, Phase C2 only

## Objective

Add a thin, immutable, versioned contract layer that makes matrix composition and
application environment impossible to omit from a traceable physical-model
request. The same formula in a different matrix or environment must produce a
different canonical request hash.

C2 represents declared physical context. It does not evaluate an equation,
predict headspace or perception, migrate a database, reinterpret a stock dilution,
or move any production caller onto the new contract.

## Authoritative requirements and inspected baseline

The C2 master contract requires:

- actual matrix components and their declared quantity bases, including ethanol,
  water, DPG, DEP, TEC, IPM, other carriers, fragrance actives, dissolved solids,
  and other product phases as applicable;
- temperature, pressure, humidity for gas comparisons, totals, uncertainty, and
  phase assumptions;
- separate stock-solution, concentrate, finished-perfume, application-film, and
  sampled-headspace identities;
- the nine closed application-environment kinds in the master prompt;
- dose, area, film geometry, substrate, environmental conditions, airflow,
  equilibration or drying time, sampling time and method, and vessel/headspace
  volumes, with absence made explicit;
- versioned matrix and environment hashes on every traceable request;
- distinguishable requests when either matrix or environment changes.

Repository inspection found three relevant but narrower mechanisms:

- `engine.mixture.MixtureState` performs finished-liquid arithmetic from volumes,
  density, and molar mass. It has no stage, version, environment, uncertainty, or
  content hash.
- `engine.solvent_matrix.SolventLedger` is deliberately a reconciliation ledger.
  It preserves residual-volume proxies and explicitly refuses to promote them to
  canonical headspace composition.
- `engine.calibration.hashing.stable_json_hash` and the C1 contracts already
  provide deterministic canonical JSON and immutable content-hash patterns.

No inspected module defines `MatrixComposition`, a closed application-environment
kind, a versioned matrix/environment hash, or a request that requires both. The
read-only literature-verification ledger also treats matrix, substrate,
temperature, and apparatus as claim-scoping variables rather than interchangeable
metadata. DeepLuna Fast job `DS-63764ed4c2065fe47300595218a67b82` independently
identified the same contract gaps; Sol reproduced them in the working tree.

Before this design write, the repository's Git-visible dirty and untracked work
was archived path-preservingly at head
`e6c6d5bed3a41362e21bf07752a98fd952781a59`. An independent verifier checked all
444 manifest files, lengths, SHA-256 digests, tar path safety, and duplicate
members. DeepLuna runtime directories were explicitly excluded and counted; they
are regenerable scheduler state, not repository work.

## Considered approaches

### A. Extend `SolventLedger` into the canonical matrix model - rejected

This would mix reconciliation/proxy semantics with exact physical context. A
residual stock-carrier estimate could be mistaken for a measured or declared
quantity basis, contradicting the ledger's existing fail-closed boundary.

### B. Retrofit `MixtureState` and migrate callers immediately - rejected

`MixtureState` is useful arithmetic, but it represents one finished-liquid view.
Adding stage history, application geometry, apparatus, and sampled headspace would
couple C2 to an existing runtime path before C3 and C4 define model interfaces and
equations. It would also alter production behavior inside a representation phase.

### C. Add a focused `engine.physics` contract layer - selected

Create immutable matrix, environment, and request records beside the C1 property
contracts. Reuse canonical hashing and C1's closed uncertainty descriptor, but do
not import backend persistence or call a legacy estimator. Existing mixture and
ledger facts remain authoritative only for their present purposes. A later phase
may add an explicit adapter once it can prove basis, provenance, and completeness
without upgrading proxies.

This is the smallest approach that passes C2 without creating a second physical
engine or changing current predictions.

## Chosen architecture

```text
declared formula identity (hash)
        +
versioned MatrixComposition (full canonical snapshot + hash)
        +
versioned ApplicationEnvironment (full canonical snapshot + hash)
        |
        v
MatrixAwareModelRequest (full snapshots, both hashes, request hash)
```

The request stores complete canonical snapshots, not only foreign-key-like
digests. This prevents a report serializer from displaying a matrix-specific
result while silently dropping the matrix description. Future outputs can retain
the request hash plus the two context hashes without redefining identity.

## Contract module

`engine.physics.matrix_environment` owns the C2 vocabulary. The public types are
re-exported from `engine.physics`; the module does not import SQLAlchemy, backend
services, `MixtureState`, `SolventLedger`, or any physical estimator.

### Closed vocabulary

`MatrixStage` has exactly:

```text
STOCK_SOLUTION
CONCENTRATE
FINISHED_PERFUME
APPLICATION_FILM
SAMPLED_HEADSPACE
```

`MatrixComponentRole` has exactly:

```text
ETHANOL
WATER
DPG
DEP
TEC
IPM
OTHER_CARRIER
ACTIVE_FRAGRANCE
DISSOLVED_SOLID
OTHER_PRODUCT_PHASE
```

The role is not the identity. Every component also has a stable component ID and
declared name, so `OTHER_CARRIER` cannot serve as an anonymous composition.

`MatrixQuantityBasis` distinguishes mass fraction, volume fraction, mole
fraction, mass, volume, and amount. Fractions use the canonical unit `1` and must
fall in `[0, 1]`; absolute quantities carry an explicit non-blank unit. C2 does
not convert units or normalize fractions.

`CompositionCompleteness` is `EXACT`, `PARTIAL`, or `UNRESOLVED`. Exact matrices
must have no declared missing fields. Partial and unresolved matrices must name at
least one missing field. This permits honest incomplete records without allowing a
generic label to masquerade as exact composition.

`ApplicationEnvironmentKind` has exactly the nine values from the master prompt:

```text
SEALED_EQUILIBRIUM_VIAL
OPEN_LIQUID_SURFACE
BLOTTER
SKIN
SKIN_SURROGATE
FABRIC
CREAM_OR_EMULSION
SOAP_OR_CLEANSER
OTHER_PRODUCT_MATRIX
```

### `DeclaredQuantity`

`DeclaredQuantity` is a finite numeric value plus an explicit unit. It performs
no conversion and never guesses a default unit. Context-specific constructors
enforce non-negative quantities and valid fractions where required.

### `MatrixComponent`

Each immutable component contains:

- stable component ID and declared name;
- closed role;
- closed quantity basis and declared quantity;
- explicit source reference string;
- a C1 `UncertaintyDescriptor`, including `UNKNOWN` when no numeric uncertainty is
  justified;
- a deterministic component content hash.

Duplicate component IDs are rejected case-insensitively. Component order is
canonicalized by stable ID before matrix hashing, so input mapping/list order does
not change identity.

### `MatrixComposition`

Each immutable matrix contains:

- schema, stable matrix ID, and caller-declared matrix version;
- one closed matrix stage;
- one or more typed components;
- declared temperature and pressure;
- relative humidity when `gas_comparison` is true;
- total mass and total volume, or explicit missing-field declarations;
- matrix-level uncertainty;
- one or more phase assumptions;
- completeness and explicit missing fields;
- a deterministic matrix content hash.

An exact matrix requires temperature, pressure, total mass, and total volume and
cannot have missing fields. A gas-comparison matrix additionally requires relative
humidity. Partial or unresolved matrices retain `null` values only when the exact
field names appear in `missing_fields`. C2 records phase assumptions but does not
test phase equilibrium.

Stock solution, concentrate, finished perfume, application film, and sampled
headspace are different stages and therefore different hashes even if their
declared components happen to match. Time evolution is represented as a new
versioned matrix snapshot; C2 does not infer evaporation between snapshots.

### `ApplicationEnvironment`

Each immutable environment contains stable ID and version, closed kind, and typed
fields for:

- dose and application area;
- film thickness and/or declared geometry;
- substrate;
- temperature, relative humidity, and airflow;
- equilibration or drying time;
- sampling time and method;
- vessel and headspace volume;
- environment-level uncertainty.

Every absent context field must be classified in one of two disjoint closed sets:
`missing_fields` or `not_applicable_fields`. A field may not be both, and a field
with a value may not appear in either set. This prevents an omitted value from
silently meaning either unknown or irrelevant. A sealed-equilibrium-vial
environment always requires vessel volume, headspace volume, sampling time, and
sampling method. Other model-specific sufficiency rules remain for later model
contracts; C2 avoids inventing universal skin, blotter, or fabric physics.

### `MatrixAwareModelRequest`

A request contains:

- schema and non-blank request purpose;
- stable formula ID and lowercase SHA-256 formula hash;
- the full `MatrixComposition` snapshot and its hash;
- the full `ApplicationEnvironment` snapshot and its hash;
- a deterministic request content hash.

Neither matrix nor environment is optional. Canonical serialization repeats each
context hash adjacent to its full snapshot. Request identity excludes timestamps
and process-local IDs, making equivalent inputs reproducible across runs.

## Validation and error behavior

Malformed construction raises `MatrixEnvironmentContractError`; scientific
unknowns are represented explicitly rather than raised as runtime absence.
Validation rejects:

- blank IDs, versions, units, source references, phase assumptions, and purpose;
- booleans or non-finite numeric values;
- negative physical quantities where negative values are nonsensical;
- fraction values outside `[0, 1]` or fractions with a unit other than `1`;
- empty matrices, duplicate component IDs, and inconsistent completeness;
- unclassified absent environment fields or contradictory classifications;
- missing sealed-vial apparatus/sampling fields;
- malformed formula hashes;
- unknown enum values or unknown fields in versioned mapping parsers.

Canonical hashes use the existing `stable_json_hash`; no new hashing algorithm or
floating-point rounding rule is introduced.

## Test strategy and C2 exit gate

Test-driven implementation will prove:

- every required stage, component role, basis, and environment kind exists;
- quantities, fractions, IDs, versions, uncertainty, and duplicate identities
  fail closed;
- exact, partial, and unresolved matrix completeness cannot be confused;
- gas-comparison humidity and sealed-vial apparatus fields are enforced;
- all absent environment fields are explicitly classified;
- matrix and environment hashes are deterministic across component input order;
- matrix stage, component amount/basis, conditions, phase assumptions, apparatus,
  substrate, and sampling changes alter the appropriate content hash;
- the same formula with a different matrix changes the request hash;
- the same formula with a different environment changes the request hash;
- serialized requests contain both full snapshots and both versioned hashes;
- no legacy estimator, database model, migration, or production caller is touched;
- existing C1 and focused repository tests remain green.

C2 passes only after focused tests, lint/type checks, path-scoped scope checks,
fresh DeepLuna Fast review, Sol reproduction, committed evidence, and post-commit
verification are green. C3 remains closed until that exit gate passes.

## Explicit non-goals

- no activity-coefficient, evaporation, diffusion, mass-transfer, or headspace
  equation;
- no prediction or measurement value;
- no matrix interpolation, unit conversion, or solvent-loss simulation;
- no automatic adapter from `SolventLedger` or `MixtureState`;
- no production caller migration;
- no database table, migration, write, or regenerated scientific artifact;
- no change to C0 legacy authority labels or C1 property selection;
- no scientific-release claim.

## Approval record

The user delegated implementation and permission decisions to Sol and explicitly
requested uninterrupted strict-phase execution without permission prompts. Sol
selected Approach C after inspecting the repository, the authoritative C2
contract, the read-only literature ledger, and a bounded DeepLuna Fast gap audit.
This approval authorizes the design and plan commits only; it does not waive the
executable C2 exit gate.
