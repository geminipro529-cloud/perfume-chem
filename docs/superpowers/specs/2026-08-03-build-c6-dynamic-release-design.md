# Build C6 dynamic release and temporal physical model design

## Decision

Build C6 will add a new conservative compartment state machine behind the
existing Build C3 versioned-model router. It will not adapt, import, modify, or
silently replace any legacy temporal, trajectory, diffusion, skin, workbench,
optimizer, or production runtime.

The executable model is a simulation-only physical calculation. Its parameter
sets are explicit, immutable, hash-bound, substrate-specific, and uncalibrated.
No default transport coefficient, substrate transfer, sensory mapping, OAV
authority, or empirical promotion is permitted.

## Authority and prerequisites

The authoritative C5 software gate is PASS and opens C6. Its separate empirical
status remains `BLOCKED_PENDING_DATA`: no actual instrument dataset, empirical
metric, measured-domain completion, or promoted model exists. C6 therefore may
prove software and numerical invariants, but it cannot claim empirical accuracy.

Build C2 remains the authority for matrix and application-environment snapshots.
Build C3 remains the authority for exact model selection, immutable release
binding, applicability, abstention, uncertainty envelopes, evidence class, and
claim wording. C6 consumes those contracts rather than creating parallel context
or routing systems.

## Repository findings

The repository contains several incompatible historical dynamic answers:

- `engine/pipeline/simulator.py` is the current compatibility temporal screen,
  based on bounded uncalibrated exponential loss. It is not a physical release
  rate or wear-duration model.
- `engine/thermo/trajectory.py` is a disconnected explicit-Euler open-surface
  calculation with unvalidated transport assumptions.
- `engine/temporal_graph.py` mixes evaporation, intensity, note evolution, and
  projection-distance outputs without held-out perfume validation.
- `engine/temporal_volatility.py` is a reconstruction-timeline heuristic, not a
  physical-release model.
- `engine/diffusion_model.py` emits sillage and reach classes from heuristic
  thresholds without complete geometry, dose, airflow, or distance validation.
- `engine/skin_interaction.py` is an advisory scorer with a frozen duplicate-
  accounting defect that can produce reservoir percentages above 100 percent.

DeepLuna Fast independently reproduced these boundaries in one bounded FLASH
read audit (`DS-29057cb3a871275b1d35503fc664a037`, PASS, `NO_LUNA`). Sol verified
the findings directly against the C0 inventory and source. None of these modules
is a coefficient source or dependency for the new C6 implementation.

## Options considered

### Approach A: adapt the standalone legacy trajectory

This would be small, but would inherit fixed-area assumptions, explicit-Euler
negativity risk, unvalidated coefficients, and a competing historical authority.
It is rejected.

### Approach B: add a standalone conservative state machine

This could prove mass balance, but would bypass C3 release/version binding,
applicability abstention, and no-fallback routing. It would create another model
entry point. It is rejected.

### Approach C: pure state machine plus exact C3 adapter

This keeps numerical logic independently testable while binding every routed
answer to an immutable release, C2 context, exact parameter-set reference, and
explicit applicability result. It is selected.

## Process-layer separation

The C6 contract will expose a closed `PhysicalProcessLayer` enum containing:

- `EQUILIBRIUM_PARTITION`;
- `MASS_TRANSFER_AND_EVAPORATION`;
- `SUBSTRATE_SORPTION`;
- `PHYSICAL_HEADSPACE_TRAJECTORY`;
- `OLFACTORY_ADAPTATION`;
- `PERCEIVED_INTENSITY`; and
- `TEMPORAL_ATTRIBUTE_PROFILE`.

The executable simulation declares only the first four as modeled physical
layers. The final three remain explicit excluded sensory layers. A physical
trajectory is never renamed as a sensory result.

## Honest output vocabulary

The only public trajectory labels are:

- `PREDICTED_HEADSPACE_TRAJECTORY`;
- `PREDICTED_RELEASE_TRAJECTORY`; and
- `ESTIMATED_PHYSICAL_PERSISTENCE`.

The last label means residual condensed-plus-sorbed physical mass fraction over
the declared time grid. It is not odor detectability or wear duration. Model
release wording forbids exact longevity, sillage, projection distance, perceived
intensity, measured headspace, and calibrated release claims.

## Immutable parameter contract

### `DynamicComponentParameters`

Each component parameter record contains:

- exact component ID;
- dimensionless equilibrium release factor;
- positive activity coefficient;
- either a sealed-compartment transfer rate or finite-film diffusion and
  boundary mass-transfer coefficients, selected by substrate kind;
- substrate sorption and desorption rates;
- explicit gas-to-sink rate;
- nonnegative solvent-composition feedback exponent;
- relative parameter-uncertainty fraction;
- non-blank declared parameter-source ID and lowercase source SHA-256; and
- deterministic content SHA-256.

No coefficient has a default. Sealed-vial parameters cannot contain a gas sink,
substrate sorption, film diffusion, or boundary-transfer coefficient. Open
surfaces cannot contain substrate sorption. Blotter, skin/surrogate, fabric, and
product-matrix records may contain substrate terms but remain bound to one exact
environment kind.

### `SubstrateModelParameters`

One immutable substrate model binds:

- stable model ID and version;
- one exact C2 `ApplicationEnvironmentKind`;
- `SIMULATION_ONLY_UNCALIBRATED` authority;
- no calibration receipt;
- `cross_substrate_transfer_allowed = false`;
- reference temperature, airflow, and humidity;
- explicit temperature, airflow, and humidity sensitivity coefficients;
- one exact component-parameter set; and
- deterministic content SHA-256.

No skin model can answer a blotter request, no blotter model can answer a fabric
request, and no sealed-vial parameterization can answer an open-surface request.
A future calibrated parameterization requires a new authority contract and
actual C5/B5-bound evidence; it cannot be represented by changing a string.

### `DynamicReleaseInputSet`

The input set binds:

- stable input-set ID;
- exact C2 matrix and environment content hashes;
- the exact substrate model;
- explicit initial gas and sorbed mass for every matrix component;
- duration and fixed time step;
- mass-closure tolerance; and
- deterministic content SHA-256.

It converts to exactly one C3 `ModelInputReference` with role
`c6_dynamic_release_input_set`. Ordering is canonical, duplicate components are
rejected, and mapping parsers reject missing, unknown, or hash-tampered fields.

## C2 applicability boundary

The first C6 release supports only exact C2 matrices whose components use
absolute mass basis and `mg`, whose total mass uses `mg`, and whose component
sum closes against total mass. Matrix and environment hashes must match the
input set exactly.

For finite-film environments, C6 requires explicit dose, area, film thickness,
temperature, relative humidity, and airflow with exact units. Blotter,
skin/surrogate, fabric, and product-matrix environments also require a declared
substrate. Sealed vials use the C2 apparatus and sampling requirements and may
report gas concentration only when exact headspace volume is present.

Missing, partial, unit-incompatible, selector-mismatched, component-mismatched,
or cross-substrate requests abstain through C3 before computation. No implicit
unit conversion or compatibility fallback exists.

## Conservative state machine

For each component, the tracked compartments are:

- condensed mass;
- gas mass;
- substrate-sorbed mass; and
- explicit escaped/sink mass.

Each step is deterministic and uses bounded exponential hazard fractions,
`1 - exp(-k * dt)`, rather than unbounded explicit-Euler subtraction.

The transition order is:

1. derive current condensed composition, solvent fraction, and film thickness;
2. derive the component condensed-to-gas hazard from the declared sealed rate
   or finite-film diffusion/boundary resistances;
3. apply declared activity, matrix-composition, temperature, airflow, and
   humidity factors;
4. transfer bounded condensed mass to gas;
5. transfer bounded sorbed mass back to gas;
6. split bounded gas outflow proportionally between substrate sorption and the
   explicit sink; and
7. verify per-component and total closure within tolerance.

Every compartment is clamped only for machine-scale negative roundoff. A real
negative, non-finite value, or closure failure raises a C6 contract error. Mass
may leave the modeled local system only through the explicit sink, which remains
inside the accounting total.

## Finite-film behavior

For non-sealed environments, current film thickness scales with remaining
condensed mass under the declared constant-area/constant-density approximation.
Finite-film condensed-to-gas transfer combines:

- diffusion resistance from declared diffusion coefficient and current film
  thickness;
- boundary resistance from declared mass-transfer coefficient and thickness;
- explicit activity coefficient;
- changing solvent fraction through the declared component feedback exponent;
- temperature, airflow, and humidity factors; and
- substrate absorption/desorption where the exact substrate model permits it.

These are transparent simulation equations, not fitted perfume truth. The output
records the assumptions and effective rates used at each frame.

## Uncertainty propagation

Every simulation runs three deterministic parameter scenarios:

- `LOWER_RATE`;
- `NOMINAL`; and
- `UPPER_RATE`.

Each component's relative uncertainty scales its declared rates around the
nominal value. The result reports the three complete conservative trajectories
and a pointwise min/max sensitivity envelope. This envelope is explicitly not a
confidence or credible interval. The C3 uncertainty descriptor remains
`UNKNOWN` until actual C5/B5-bound calibration can support statistical coverage.

## Versioned C3 release

`DynamicReleaseAdapter` uses `ModelFamily.DYNAMIC_SEMI_EMPIRICAL_MODEL` and
supports `PREDICT_DYNAMIC_RELEASE` plus `PROPAGATE_UNCERTAINTY`. The release is:

- available for simulation;
- evidence class `UNVALIDATED`;
- training-data SHA-256 `null`;
- OAV screening disabled;
- parameter hash bound to the transparent C6 equation declaration; and
- claim-restricted to simulation-only physical trajectory language.

The adapter never selects another model, never imports legacy equations, and
never promotes a result based on a label.

## Scope

Authorized implementation paths are:

- this design;
- one C6 implementation plan;
- `engine/physics/dynamic_release.py`;
- `engine/physics/__init__.py`;
- `engine/project_verification.py`;
- `tests/test_c3_model_interface.py` only if C3 compatibility requires an
  explicit C6 export assertion;
- `tests/test_c6_dynamic_release.py`; and
- `docs/verification/c6/**` for gate evidence.

No production caller, legacy model, database, migration, inventory, formula,
scientific dataset, optimizer, workbench, temporal runtime, or C0 authority
record is changed.

## Exit gate

C6 passes only when committed-tree property and state-machine tests prove:

- per-component and total mass conservation;
- nonnegative finite compartments under normal and extreme rates;
- deterministic hashes and trajectories;
- solvent-loss feedback into later matrix state and release rates;
- propagated parameter sensitivity without fabricated statistical coverage;
- exact substrate separation and no calibration transfer;
- sealed-vial and finite-film boundary behavior;
- exact C3 selector/input/context binding and fail-closed abstention;
- the honest output vocabulary and excluded sensory layers; and
- no dependency on legacy dynamic, diffusion, skin, database, or production
  paths.

Focused C6, C0-C5 compatibility, full-suite, static, archive, protected-state,
scope, mutation, DeepLuna, Sol-reconciliation, evidence-commit, and exact-commit
replay gates must be green before C7 opens.
