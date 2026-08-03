# Build C10 Constrained Experiment Selection Design

## Decision

Build C10 will introduce a new canonical package at `engine/optimization` for
constraint-first mixture design and auditable experiment selection. It will not
extend or import the legacy `engine.optimizer` scorer, and it will not promote
`engine.experiments.planner` to scientific authority.

The canonical package will be deterministic and pure: no database, network,
environment, clock, random source, mutable registry, pipeline execution, or
legacy optimizer import. It will produce proposals for human review, never an
automatic instruction to compound or test a formula.

## Alternatives considered

### Extend `engine.optimizer`

Rejected. `engine/optimizer/scoring.py` is C0-PM-048 and C9 explicitly marks
its numerical output `FORBIDDEN_NUMERIC_AUTHORITY`. `models.py` and
`scoring.py` also contain substantial pre-existing user changes. Extending
that package would mix the new authority contract with quarantined scores and
risk overwriting unrelated work.

### Upgrade `engine.experiments.planner`

Rejected. The current planner uses caller-declared sensory values, fixed
utility arithmetic, random sample codes, and no C9 authority boundary. It does
not represent formula mass balance, stock/carrier composition, safety-bound
formula state, inventory feasibility, measurement increments, module or
recognizer envelopes, family limits, or protected negative space.

### Generalize `engine.interventions`

Rejected as the canonical location. That module contains useful deterministic
patterns for inventory, measurable dose, safety binding, and Pareto filtering,
but its contract is addition-only and intentionally heuristic. Expanding it to
full compositional experiment design would blur a stable existing API.

### Add an isolated canonical package

Selected. A separate `engine.optimization` package makes the authority change
visible, keeps legacy behavior reproducible, and gives C11 a small dependency
surface to audit and mutate.

## Authority boundary

The package will consume the C9 legacy-surface registry. A numerical objective
may not use a surface classified as `FORBIDDEN_NUMERIC_AUTHORITY`,
`CAPABILITY_BOUNDARY_ONLY`, or `ABSTENTION_ONLY`. C0-PM-032 may be used only
with an immutable calibrated-model release and held-out validation receipt.

Longevity, sillage, projection, emotion, and hedonic objectives remain
withheld unless `assess_unsupported_outcome` accepts an exact-outcome,
exact-scope passing Build D receipt. Build C has no such receipt, so these
objectives cannot influence C10 selection now.

Measured and calibrated objectives must name their unit, direction,
applicability scope, immutable source or model identity, and standard
uncertainty. Resource quantities such as material cost, waste, preparation
time, and irreversibility remain explicitly labeled computed or declared
inputs; they are not sensory measurements.

## Package boundaries

- `engine/optimization/contracts.py` owns closed enums, immutable input/output
  records, canonical hashes, and validation shared by the other modules.
- `engine/optimization/mixture_design.py` owns stock/carrier accounting,
  composition feasibility, integer-increment constrained-mixture generation,
  and hard-gate assessments.
- `engine/optimization/selection.py` owns objective-authority checks, Pareto
  filtering, explicit acquisition policy, controls and replicates, stop
  conditions, and human authorization.
- `engine/optimization/historical.py` owns the reported historical-search
  claim and its fail-closed reproducibility receipt.
- `engine/optimization/__init__.py` exposes only the canonical C10 API.

No C10 runtime module imports `engine.optimizer`,
`engine.experiments.planner`, receptor/adaptation/aging calculators, hedonic
or diffusion models, the backend, database code, network code, environment
access, time, or random.

## Composition and stock model

`StockDefinition` records an exact stock and material identity, chemical
family, active mass fraction, named carrier fractions, available raw mass,
minimum measurable raw mass, dispensing increment, and raw-mass cost. Active
plus carrier fractions must sum to one; missing or unallocated composition is
an error.

`CandidateDose` records one stock, raw mass, and module assignment.
`MixtureCandidate` records a stable candidate identifier, design stage, role,
doses, optional replicate target, and formula-bound gate receipts. Candidate
formula state is hashed from the domain stock definitions and the complete
ordered composition, not from a display name.

`MixtureDomain` declares:

- a total active-mass interval;
- stock availability and measurement increments;
- module active-mass intervals;
- protected-recognizer active-mass floors;
- family active-fraction intervals or caps;
- protected-negative-space material caps;
- required exact formula-bound gate identifiers;
- a finite candidate ceiling.

Composition assessment computes raw, active, and carrier mass independently.
It rejects unknown stocks, duplicate dose rows, nonpositive or nonfinite
amounts, amounts below the measurable minimum, nonintegral dispensing steps,
inventory overdraw, active-mass mismatch, module-envelope breach, recognizer
floor breach, family breach, protected-negative-space breach, and any missing,
unknown, failed, stale, or formula-mismatched safety/action gate.

## Constrained mixture design

`generate_mixture_design` accepts bounded stock axes expressed as integer
dispensing units. It enumerates only lattice points that satisfy the declared
mixture domain and returns a deterministic manifest of considered, feasible,
rejected, and truncated points. It does not create an unconstrained
independent-factor grid and does not score infeasible points.

Generated compositions are proposals without safety or action receipts. They
must receive formula-bound gate evidence before entering acquisition scoring.
This two-step boundary permits design generation without pretending that a
new formula has already passed safety review.

## Multiobjective and acquisition selection

`CandidateEvaluation` binds one candidate to an objective vector and named
acquisition estimates. All feasible non-control candidates must share the
same objective schema. Objective directions remain separate, and the engine
retains the nondominated Pareto set before acquisition scoring.

`AcquisitionPolicy` is immutable and versioned. Each utility term declares a
name, maximize/minimize direction, normalization bounds, and public weight.
The result records every normalized term and weighted contribution. No default
or hidden user-priority weights exist.

Hard gates and scientific authority are checked before any utility value is
calculated. Missing objective evidence, invalid uncertainty, forbidden C9
authority, unsupported Build D outcome, schema mismatch, or out-of-domain
candidate produces a stable abstention/rejection reason rather than a score.

## Controls, replicates, and human gate

Every non-stopped experiment set requires at least one feasible `CONTROL` and
one feasible `REPLICATE`. A replicate must name an existing candidate and have
the exact same formula-state hash. Controls and valid replicates are preserved
independently of acquisition rank.

Selection returns a non-executable `ExperimentProposal`. The proposal can be
converted to an `AuthorizedExperimentSet` only by an explicit PASS human-review
receipt bound to the proposal content hash. This prevents a caller from using
the optimizer output as automatic permission to compound or test.

## Stop conditions

`StopPolicy` and `CampaignState` expose versioned thresholds and evidence for:

- no feasible improvement beyond tolerance;
- expected information gain below threshold;
- uncertainty dominated by unavailable data;
- budget exhaustion;
- protected-attribute risk;
- sensory plateau;
- absence of candidates inside the validated domain.

A triggered stop condition returns `STOPPED`, the exact reasons, and no new
experiment proposal. Missing evidence for a claimed sensory plateau or
unavailable-data condition is itself fail-closed.

## Historical regression boundary

The repository and allowed historical files do not contain a reproducible
implementation/input/result bundle for the reported La Nuit de L'Homme search.
The numbers "approximately 30,000 candidates", "35 guardrails", and
"approximately 97.76/100 DNA" therefore remain `REPORTED_UNVERIFIED`.

`assess_historical_regression` will require path-independent SHA-256 digests
for implementation, input, and result artifacts; the exact noninteractive
replay command; exit status; candidate and guardrail counts; separate DNA
threshold and score; and verifier identity. Missing artifacts return
`BLOCKED_MISSING_ARTIFACTS`; mismatched numbers return `MISMATCH`. Merely
constructing a receipt cannot replace C11's independent replay.

C10 will not synthesize a fake 30,000-point dataset or universalize the
reported thresholds to another fragrance family.

## Determinism and auditability

All public records are frozen and slotted. Mappings become sorted immutable
tuples at boundaries. Canonical JSON SHA-256 identities cover domains,
candidate formula states, policies, proposals, and authorizations. Ties are
resolved by stable candidate identifier. Repeated runs and different Python
hash seeds must produce byte-identical serialized results.

## Dirty-work preservation

The verified prewrite archive is:

`D:\.backups\perfume-chem\build-c10-prewrite-20260803T080045+0700.tar`

SHA-256:

`1e66410f37b4c6cf3efa96423d7d182a7ebbca60a5079e50277c66f30a81acf9`

It contains 430 path-preserving files and preserves all 429 current
dirty/untracked paths with zero mismatch. C10 will not edit or stage the dirty
legacy optimizer files or the untracked legacy planner tests.

## Verification and exit gate

C10 verification will prove:

- exact stock/carrier and active-mass conservation;
- integer-increment constrained-mixture generation;
- every required hard constraint rejects before acquisition scoring;
- C9 legacy numerical authority cannot enter an objective;
- unsupported outcomes remain withheld without exact Build D receipts;
- uncertainty and objective directions remain visible;
- Pareto nondominance precedes explicit utility ranking;
- controls and exact replicates are retained;
- stop conditions are deterministic and evidence-bound;
- proposals are non-executable without a bound human-review receipt;
- the historical reported result remains unverified without the real bundle;
- no forbidden dependency or nondeterministic source enters the package;
- deliberate mutations of each authority boundary are killed and bytes are
  restored.

C10 passes only when the focused, compatibility, complete-root, static,
dependency, mutation, archive, protected-state, log-hygiene, DeepLuna Fast,
Sol-reconciliation, evidence-commit, and exact-commit replay gates pass. A C10
PASS means the software contract is ready; it does not validate a perfume,
sensory outcome, historical score, or permission to run an experiment.
