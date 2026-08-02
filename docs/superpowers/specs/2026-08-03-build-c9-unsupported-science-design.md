# Build C9 Unsupported-Science Triage Design

## Decision

Build C9 will add one deterministic, fail-closed authority module at
`engine/evidence/unsupported_science.py`. The module will represent the
minimum evidence needed for narrow receptor, adaptation, aging, and Build D
outcome claims; withhold every broader transfer; and publish an executable
quarantine registry for the C0 legacy surfaces in C9 scope.

C9 will also remove the generic Arrhenius shelf-life number from the canonical
`chemistry_stability` release gate. That gate will continue to screen explicit
aldehyde/amine contact, oxidation, and photolability hazards, but formula shelf
life and maturation will remain `UNKNOWN` until process-specific evidence
exists.

The existing numerical receptor, adaptation, maturation, hedonic, longevity,
sillage, projection, and optimizer modules remain visible as historical or
exploratory code. C9 does not silently validate, delete, or reinterpret them.
The canonical workbench abstention remains authoritative, and C10 must consume
the C9 registry instead of treating a legacy number as experimental truth.

## Alternatives considered

### Rewrite every legacy scientific module

Rejected. The C9 requirement is evidence triage, not a new receptor,
adaptation, aging, or sensory model. Rewriting the legacy implementations
would expand scope, obscure their historical behavior, and create unsupported
new numerical claims.

### Record the defects only in a document

Rejected. A prose-only quarantine cannot be enforced by C10 or by production
tests. The dispositions, allowed use, and abstention behavior must be
executable.

### Add an isolated authority contract and repair the canonical shelf-life gate

Selected. A pure evidence module can reject missing metadata and cross-context
transfer without importing legacy calculators. A narrow release-gate change
removes the one canonical path that currently presents generic kinetics as a
formula shelf-life prediction.

## Authoritative boundaries

### Receptor evidence

`ReceptorAssayEvidence` records all of the following:

- tested material identity;
- receptor identity and species;
- cell system;
- at least three ordered concentration-response points;
- potency and efficacy parameters with explicit roles and units;
- agonism or antagonism context;
- source;
- applicability statement.

Only a complete `Homo sapiens` record may support the narrow claim that the
tested material produced the recorded response at the recorded receptor and
cell system. It does not support a human-repertoire model or perfume
perception. The latter claims remain answerless and `WITHHELD` regardless of
how persuasive a tiny receptor subset appears.

### Adaptation evidence

`AdaptationContext` records species, preparation, nervous-system level,
stimulus protocol, and timescale. `AdaptationEvidence` binds that context to a
stimulus, endpoint, source, and applicability statement.

Only an exact context match may support the recorded-context response. Any
species, preparation, nervous-system, protocol, or timescale mismatch is
withheld. A single-cell or animal result never authorizes a generic human
fine-fragrance adaptation claim.

### Aging evidence

`AgingProcess` contains exactly:

1. `CHEMICAL_TRANSFORMATION`;
2. `DISSOLUTION_PHYSICAL_EQUILIBRATION`;
3. `PRECIPITATION_PHASE_BEHAVIOR`;
4. `OXIDATION`;
5. `SENSORY_MATURATION`.

`AgingEvidence` binds one process to a formula or material, matrix,
temperature, duration, protocol, endpoint, source, and applicability. One
record can support only its exact process and recorded scope. Universal aging,
generic shelf life, and generic sensory maturation remain `WITHHELD`. Exact
Arrhenius arithmetic is not, by itself, a calibrated aging model.

### Build D outcome validation

Longevity, sillage, projection, emotion, and hedonic output are the exact C9
unsupported outcomes. `BuildDValidationReceipt` must bind one outcome to a
versioned immutable model release, endpoint, narrow scope, held-out dataset,
comparator, and passing acceptance metrics.

Without a matching passing receipt, the outcome is `WITHHELD`. A passing
receipt authorizes only its exact outcome and exact requested scope; it cannot
promote a generic perfume-performance or preference claim.

### Legacy-surface registry

`C9_LEGACY_SURFACES` covers exactly C0-PM-022, C0-PM-023, and C0-PM-032
through C0-PM-048.

- C0-PM-022 and C0-PM-023 are capability boundaries only; they do not claim an
  active UNIFAC implementation.
- C0-PM-032 is exact arithmetic whose parameters and applicability remain
  external.
- C0-PM-033 through C0-PM-043 and C0-PM-045, C0-PM-046, and C0-PM-048 are
  quarantined from numerical claim authority.
- C0-PM-044 is the canonical abstention that C10 may preserve.
- C0-PM-047 is a disconnected legacy fixture.

Every record declares a disposition and a C10-use boundary. Merely finding a
record or importing a legacy function never authorizes its numerical output.

## Canonical chemistry-stability behavior

`engine.pipeline.gates._gate_chemistry_stability` will no longer import or call
`predict_shelf_life_days`. It will no longer emit `shelf_life_days`, use a
generic Arrhenius result to change PASS/WARN/FAIL, or describe a number as
predicted shelf life or maturation.

Its retained authority is deliberately narrower:

- aldehyde/amine contact screening;
- source-labeled oxidation-prone material screening;
- source-labeled photolability screening.

The result data will carry a C9 aging decision with `WITHHELD` status and no
numeric answer. A stable formula may pass those explicit hazard screens while
the detail still states that aging, maturation, and shelf life are unknown.

## Dirty-file preservation protocol

`engine/pipeline/gates.py` contains unrelated pre-existing user changes. The
chemistry-stability section was independently compared with the authoritative
parent and is unchanged apart from line displacement. C9 will:

1. preserve the current file in the verified path-preserving C9 archive;
2. edit only the maturation import and chemistry-stability hunk;
3. stage that hunk with an explicit index patch rather than staging the whole
   file;
4. prove that no unrelated `gates.py` hunk entered the commit;
5. leave the working-tree user hunks unstaged;
6. replay the resulting exact commit in a clean detached worktree so the C9
   commit is independently self-contained.

## Determinism and dependency isolation

All public evidence and decision records are frozen, slotted dataclasses with
validated finite values and immutable tuples. Evidence identities and
decisions use canonical SHA-256 hashes. Closed vocabularies use enums.

The C9 authority module imports no receptor calculator, maturation calculator,
hedonic model, diffusion model, pipeline, optimizer, backend, database,
environment, network, clock, random source, or mutable registry. It performs
no persistence and computes no receptor, aging, longevity, sillage,
projection, emotion, or hedonic score.

## Verification

Focused tests will prove:

- exact public exports and closed vocabularies;
- complete human receptor-assay metadata and answerless broad-claim
  withholding;
- no promotion from a tiny receptor subset;
- exact adaptation context matching and no animal/single-cell transfer;
- the exact five aging processes and process-specific evidence only;
- universal aging, shelf life, and generic sensory maturation withholding;
- the exact five unsupported outcomes and exact-scope Build D receipts;
- complete legacy-surface registry coverage and C10-use boundaries;
- canonical chemistry-stability output contains no shelf-life number or claim;
- canonical workbench abstention remains intact;
- no forbidden legacy/runtime dependency enters the C9 authority module;
- source bytes are restored after deliberate authority-removal mutations.

## Exit gate

C9 passes only when the focused contract, pipeline compatibility, C8-C0
compatibility, complete-root, static, dependency, mutation, archive,
protected-state, log-hygiene, DeepLuna Fast, Sol-reconciliation,
evidence-commit, and exact-commit replay gates pass.

Passing C9 opens C10 software work only. It does not validate a receptor model,
an adaptation transfer, a universal aging model, a shelf-life prediction, or
any longevity, sillage, projection, emotion, hedonic, or consumer-preference
claim.
