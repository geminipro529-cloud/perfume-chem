# Build C0 Physical-Model Consolidation Design

Date: 2026-08-02
Status: accepted by Sol for C0 implementation
Scope: metadata, architecture, frozen legacy outputs, and verification only

## Objective

Build C0 must make every physical-model implementation and caller visible before
Build C changes scientific behavior. It must also choose a single future runtime
boundary for each supported physical claim and preserve the current behavior as
explicitly non-promoting `LEGACY_HEURISTIC` fixtures.

C0 does not implement a new physical model, alter a production call path, change
database state, create a migration, or promote any scientific claim.

## Verified current-state findings

The working tree contains several materially different calculation families:

- `engine.pipeline.formula_state.build_formula_state` is the current workbench
  entry for composition-dependent headspace and OAV screening. It performs
  modified-Raoult arithmetic but depends on mixed-authority property lookups,
  Hansen-distance activity-coefficient estimates, defaults, and generic natural
  profiles. Its own result labels headspace as `HEURISTIC_NOT_MEASURED`.
- `engine.pipeline.simulator.simulate_formula` is the current workbench temporal
  path. It applies uncalibrated exponential loss and is not a wear-duration model.
- `engine.thermo.headspace` and `engine.thermo.trajectory` form a second standalone
  headspace/release family with different inputs and assumptions.
- reconstruction, optimizer, report-script, backend-domain, receptor, maturation,
  psychophysics, skin, diffusion, vapor-pressure, and temporal-graph modules expose
  additional heuristic or speculative outputs. Several can answer similarly named
  longevity, sillage, projection, headspace, or temporal questions differently.
- the canonical workbench already withholds longevity, sillage distance/category,
  and receptor activation where supporting measurements are absent. Those
  abstentions are retained.
- the activity module explicitly reports that UNIFAC is not implemented or active.
  DIPPR-style vapor-pressure equations and COSMO-RS are absent. Their absence is a
  first-class `UNSUPPORTED` inventory record, not silently inferred capability.
- Build B property observations and selected assertions are persisted through the
  Laboratory Beta property service, but current engine model paths still read
  registry/profile scalars directly. Build C must bridge to selected assertions;
  C0 only records this boundary.

## Decision

### One versioned interface

Later C phases will add an `engine.physics` package with a versioned request/result
envelope. The conceptual contract is:

```text
PhysicalModelRequest
  claim_type
  formula_state_ref
  property_snapshot_ref
  matrix
  application_environment
  conditions
  requested_model_version

PhysicalModelResult
  claim_type
  model_id + model_version
  classification
  status = COMPUTED | WITHHELD | NOT_APPLICABLE
  value(s) + units
  conditions
  applicability
  uncertainty
  property/evidence references
  assumptions + warnings
  input_hash + result_hash
```

The model router will permit exactly one selected implementation for a claim type
and version. A claim cannot be answered by fallback to a differently named engine.
Unavailable prerequisites produce `WITHHELD`; they do not trigger an unlabeled
heuristic.

### One runtime route

The allowed future route is:

```text
endpoint/report/optimizer
  -> PerfumeWorkbench or a canonical Laboratory Beta application service
  -> engine.physics model router
  -> one versioned model implementation
  -> immutable result envelope
```

Physical property inputs come from a condition-aware adapter over Build B selected
assertions. Laboratory Beta SQL records remain persistence authority. Model code is
pure computation and cannot write canonical records directly.

Until the relevant C-phase gate passes:

- `build_formula_state` remains the compatibility adapter for current headspace;
- `simulate_formula` remains the compatibility adapter for current temporal frames;
- current workbench abstentions remain authoritative for unsupported outputs;
- standalone and optimizer models remain advisory, legacy, or non-runtime exactly
  as declared by the C0 inventory;
- no caller is silently switched by C0.

### Claim ownership

| Claim family | Future canonical owner | C0 disposition |
|---|---|---|
| thermophysical property selection | Build B adapter under `engine.physics` | inventory direct lookups; no runtime change |
| equilibrium partition/headspace | versioned equilibrium model | preserve formula-state and standalone outputs as legacy fixtures |
| dynamic release | versioned dynamic-release model | preserve simulator/trajectory/temporal outputs as legacy fixtures |
| matrix/phase compatibility | versioned matrix and phase model | label Hansen-distance rules heuristic |
| natural composition/headspace | lot-aware natural model | label generic constituent profiles low-authority proxies |
| OAV/intensity | separate threshold and sensory layer | retain modeled-screening label; never equate with measurement |
| longevity/sillage/projection | calibrated endpoint-specific models | canonical outputs remain withheld until held-out evidence exists |
| receptor/adaptation/hedonic | evidence-specific perception models | quarantine family priors and fixed constants from production claims |

## Inventory contract

`docs/verification/c0/physical_model_inventory.json` is the machine authority for
C0. Each implementation record has a stable ID and records:

- category and exact source symbol or explicit absence query;
- one C0 classification from the master contract;
- inputs, outputs, conditions, consumers, evidence labels, tests, and claim impact;
- runtime status and consolidation disposition;
- SHA-256 of every source file used to support the record;
- caller edges that name both caller and callee;
- an explanation whenever a compound implementation is split into separately
  classified branches, such as Antoine, Clausius-Clapeyron, and constant fallback.

The verifier fails closed on unknown classifications, duplicate IDs, missing
required categories, missing paths/symbols/tests, stale source digests, dangling
call edges, or an unsupported capability that becomes present without an inventory
update.

## Legacy fixture contract

`tests/fixtures/c0_legacy_physical_model_cases.json` freezes representative outputs
from every deterministic legacy calculation family that can influence a listed C0
claim. Each case contains:

- implementation ID and callable selector;
- canonical JSON input and its SHA-256;
- normalized output and tolerances where floating arithmetic requires them;
- source-file SHA-256;
- classification `LEGACY_HEURISTIC`;
- a non-empty warning that it is regression evidence, not scientific validation.

The companion `.sha256` file locks the canonical fixture bytes. Tests replay each
case through a read-only capture function and compare normalized outputs. Missing
optional libraries must be represented as an explicit fixture status rather than a
fabricated number.

## Alternatives rejected

1. Implementing `engine.physics` during C0 was rejected because the C0 gate forbids
   new model implementation before inventory, ADR, and fixtures are complete.
2. Renaming or deleting legacy modules during C0 was rejected because callers and
   the dirty overlay must first be preserved and proven; removal belongs after a
   later phase establishes a replacement and migration evidence.
3. Treating modified-Raoult arithmetic as sufficient scientific authority was
   rejected because the authority of the result is bounded by matrix completeness,
   input provenance, model applicability, and validation data.
4. Treating empty UNIFAC/COSMO-RS/DIPPR interfaces as capability was rejected;
   unsupported paths remain fail-closed.

## C0 exit gate

C0 passes only when all of the following are fresh and reproducible:

1. machine inventory and rendered call-graph report are complete;
2. this decision is mirrored by the architecture ADR;
3. every legacy fixture has verified input/source hashes and a warning;
4. fixture replay, inventory verifier, focused tests, and repository-scope checks
   pass without changing model behavior;
5. the diff contains no production model edits, database migration, generated
   database mutation, or unrelated user work.

Only after this gate is committed may C1 implementation begin.
