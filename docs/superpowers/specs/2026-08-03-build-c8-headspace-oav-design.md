# Build C8 Headspace OAV and Mixture-Interaction Design

## Decision

Build C8 will add one deterministic, fail-closed authority module at
`engine/physics/headspace_oav.py`. The module will calculate bounded headspace
OAV only when the gas concentration and detection threshold are admissible for
the same context. It will also record context-specific mixture-interaction
evidence, represent the ordered sensomics evidence sequence, and expose an
explicit Build C claim boundary.

C8 will not import, adapt, or promote the existing heuristic intensity,
mixture-shift, synergy-factor, or production OAV paths. It will not alter a
production caller, database, migration, inventory, formula, or scientific-data
artifact.

## Alternatives considered

### Extend the legacy perception and synergy modules

Rejected. `engine/perception/oav.py` calculates Stevens/Weber intensity and a
generic mixture-shifted threshold. `future_modules/synergy_matrix.py` contains
generic pair multipliers and range heuristics. The C8 literature boundary says
that OAV is not exact intensity or percent contribution and that pair effects
cannot be universalized from one context. Extending those modules would blur
the authority boundary and overlap pre-existing user work.

### Add OAV as another C3 physical-model operation

Rejected. C3 routes versioned physical models. C8 consumes a measured or
already-authorized predicted gas concentration and compares it with a sensory
threshold. Treating this screening ratio as another equilibrium or release
model would combine physical prediction, threshold evidence, and sensory claim
authority in one model result.

### Add an isolated C8 authority contract

Selected. A pure module can accept immutable evidence records, abstain on any
incompatibility, preserve uncertainty and provenance, and expose no production
side effect. It follows the established C1-C7 pattern and leaves legacy paths
visible for later unsupported-science triage.

## Evidence basis

The authoritative C8 prompt requires:

- measured gas concentration or an in-domain model prediction;
- context-compatible concentration and threshold;
- matching units and conditions;
- claim-adequate threshold authority;
- propagated uncertainty;
- context-specific interaction records;
- no uncalibrated numerical mixture rule;
- the ordered molecular-sensory-science sequence;
- a strict boundary between physical prediction, OAV screening, interaction
  evidence, and sensory claims.

The literature verification ledger adds these implementation consequences:

- OAV can prioritize candidate odorants but is not exact intensity, percent
  contribution, or similarity;
- additive, masking, suppressive, synergistic, and configural behavior depends
  on matrix and concentration;
- binary behavior does not automatically transfer to larger mixtures;
- recombination, omission, block-omission, and addition experiments are the
  evidence bridge for causal sensory claims;
- physical concentration profiles and psychophysical transforms remain
  separate layers.

A bounded DeepLuna Fast inventory independently identified the same legacy
collision risks and the required package-export and verification integration
points. Its findings are advisory; Sol owns this design and acceptance.

## Scope

C8 may change only:

- this design;
- `docs/superpowers/plans/2026-08-03-build-c8-headspace-oav.md`;
- `engine/physics/headspace_oav.py`;
- `engine/physics/__init__.py`;
- `engine/project_verification.py`;
- `tests/test_c8_headspace_oav.py`;
- the C8 export assertion in `tests/test_c3_model_interface.py`;
- C8 verification evidence after implementation.

C8 will not change:

- production API, service, UI, workbench, pipeline, optimizer, or orchestration
  callers;
- `engine/perception/oav.py`, `engine/thermo/headspace.py`,
  `engine/pipeline/oav_authority.py`, `engine/pipeline/oav_intelligence.py`,
  `engine/synergy_graph.py`, `engine/interaction_graph.py`, or
  `future_modules/synergy_matrix.py`;
- databases, migrations, WAL/SHM state, inventory, formulas, or generated
  scientific artifacts;
- C9 unsupported-science triage or any release/promotion decision.

## Public contract

### Closed vocabularies

The module will define closed enums for:

- gas concentration origin: `MEASURED`, `PREDICTED`;
- threshold kind: `DETECTION`, `RECOGNITION`;
- threshold authority: `DIRECT_CONTEXT_MEASUREMENT`,
  `PEER_REVIEWED_CONTEXT_MATCHED`, `CONTEXT_MISMATCHED`, `PROXY`, `UNKNOWN`;
- OAV status: `COMPUTED`, `ABSTAINED`;
- screening class: `ABOVE_THRESHOLD`, `BELOW_THRESHOLD`,
  `STRADDLES_THRESHOLD`, `UNKNOWN`;
- interaction kind: `ADDITIVE`, `SYNERGISTIC`, `MASKING`, `SUPPRESSIVE`,
  `QUALITATIVE_TRANSFORMATION`, `UNKNOWN`;
- interaction evidence kind: `OBSERVATION`, `MODEL`;
- interaction calibration state: `CONTEXT_CALIBRATED`, `OBSERVED_ONLY`,
  `UNCALIBRATED_GENERIC`;
- interaction adjustment target: `HEADSPACE_CONCENTRATION`,
  `PERCEIVED_INTENSITY`;
- interaction authorization status: `AUTHORIZED`, `WITHHELD`;
- sensomics stage status: `COMPLETED`, `FAILED`, `NOT_PERFORMED`;
- sensomics claim: `CANDIDATE_ODORANT_PRIORITIZATION`,
  `RECOMBINATION_MATCH_IN_TESTED_CONTEXT`,
  `MATERIAL_EFFECT_IN_TESTED_CONTEXT`;
- C8 claim status: `PERMITTED_WITH_EVIDENCE`, `WITHHELD`;
- all permitted and withheld C8 claims.

Unknown enum values and unknown mapping fields fail closed.

The exact public API is:

- constants: `C8_SENSOMICS_SEQUENCE`, `PERMITTED_C8_CLAIMS`,
  `WITHHELD_C8_CLAIMS`;
- enums: `GasConcentrationOrigin`, `ThresholdKind`, `ThresholdAuthority`,
  `OAVAssessmentStatus`, `OAVScreeningClass`, `InteractionKind`,
  `InteractionEvidenceKind`, `InteractionCalibrationState`,
  `InteractionAdjustmentTarget`, `InteractionAdjustmentStatus`,
  `SensomicsStage`, `SensomicsStageStatus`, `SensomicsClaim`, `C8Claim`,
  `C8ClaimStatus`;
- records: `EvidenceReference`, `GasPhaseContext`, `BoundedQuantity`,
  `GasConcentrationEvidence`, `OdorThresholdEvidence`,
  `HeadspaceOAVAssessment`, `InteractionConcentration`,
  `InteractionApplicableRange`, `InteractionNumericalEffect`,
  `InteractionEvidence`, `InteractionAdjustmentRequest`,
  `InteractionAdjustmentDecision`, `SensomicsStageRecord`,
  `SensomicsProgram`, `SensomicsAssessment`, `C8ClaimDecision`;
- operations: `calculate_headspace_oav`,
  `authorize_interaction_adjustment`, `evaluate_sensomics_claim`,
  `evaluate_c8_claim`;
- error: `HeadspaceOAVContractError`.

### Evidence reference and context

`EvidenceReference` records a stable source ID, source kind, citation/locator,
version, and exact content SHA-256. It contains no live lookup.

`GasPhaseContext` records a stable context ID plus:

- gas phase or sampling regime;
- matrix ID;
- temperature in kelvin;
- pressure in pascals;
- relative humidity when known;
- exposure route;
- substrate or apparatus ID when applicable.

Compatibility is determined from the canonical scientific-condition mapping,
not from a friendly label. Matrix, phase, temperature, pressure, humidity,
route, and substrate/apparatus must match exactly. An unknown condition cannot
silently match a known one.

### Bounded quantities and uncertainty

`BoundedQuantity` records a finite positive point value, exact unit, optional
lower and upper bounds, and an explicit uncertainty basis. Bounds are either
both present or both absent. Missing numeric bounds remain representable but
cannot support an OAV computation.

C8 performs no implicit unit conversion. Concentration and threshold units
must match exactly. A later conversion contract may produce a new bounded
quantity before C8, but C8 will not guess a conversion basis.

### Gas concentration evidence

`GasConcentrationEvidence` records analyte identity, bounded concentration,
origin, context, source, and origin-specific authority.

- Measured evidence must not claim a model ID, model version, release hash, or
  domain result.
- Predicted evidence must record model ID, model version, immutable release
  hash, and an explicit in-domain result.
- An out-of-domain prediction is retained as evidence but causes OAV
  abstention.

### Threshold evidence

`OdorThresholdEvidence` records analyte identity, bounded threshold, threshold
kind, authority, context, method, assessor population, and source.

Only a detection threshold with `DIRECT_CONTEXT_MEASUREMENT` or
`PEER_REVIEWED_CONTEXT_MATCHED` authority can support the Build C
above-threshold screening claim. Recognition thresholds, proxies, context
mismatches, and unknown authority remain visible but cannot produce OAV.

### Headspace OAV

`calculate_headspace_oav` returns `HeadspaceOAVAssessment`.

It computes only when:

1. analyte identities match;
2. measured evidence is valid or predicted evidence is explicitly in-domain;
3. the requested claim is `ABOVE_THRESHOLD_SCREENING`;
4. threshold kind and authority are admissible;
5. scientific contexts match;
6. units match;
7. both quantities contain numeric uncertainty bounds.

The point estimate is:

```text
OAV = gas concentration / detection threshold
```

The conservative bounded interval is:

```text
lower = gas lower / threshold upper
upper = gas upper / threshold lower
```

The result is `ABOVE_THRESHOLD` only when the complete interval is at or above
one, `BELOW_THRESHOLD` only when the complete interval is below one, and
`STRADDLES_THRESHOLD` otherwise. An abstained result has no OAV value or
answer-bearing interval. Every result records limitations stating that OAV is
screening, not intensity, percent contribution, similarity, or preference.

### Interaction evidence and numerical authorization

`InteractionEvidence` records:

- two or more exact identities;
- bounded concentrations for every identity;
- exact matrix and condition context;
- interaction kind and sensory attribute;
- sensory method and assessor population;
- evidence kind and model/formula when applicable;
- source and an explicit qualitative uncertainty statement;
- applicable concentration ranges;
- calibration state;
- an optional bounded numerical effect.

An uncalibrated generic or observation-only record cannot contain a numerical
effect. A numerical effect is structurally valid only for a context-calibrated
model with a source, explicit formula, uncertainty, exact identities, and an
applicable range for every component.

`InteractionNumericalEffect` records an adjustment target, a positive
dimensionless bounded multiplier, and the exact calibrated formula. The
bounded multiplier supplies the numerical uncertainty; every interaction also
retains a nonblank qualitative uncertainty statement.

`authorize_interaction_adjustment` never modifies concentration, headspace, or
intensity. It returns an answerless `WITHHELD` decision unless identity,
context, target, units, ranges, calibration, and numerical-effect authority all
match. An `AUTHORIZED` decision exposes the bounded effect for a separate
explicit consumer; C8 itself applies no multiplier.

### Sensomics bridge

`C8_SENSOMICS_SEQUENCE` is exactly:

1. `REPRESENTATIVE_SAMPLING_EXTRACTION`;
2. `ODOR_ACTIVE_SCREENING`;
3. `IDENTITY_CONFIRMATION`;
4. `QUANTITATIVE_MEASUREMENT`;
5. `CONTEXT_MATCHED_OAV_PRIORITIZATION`;
6. `FULL_RECOMBINATION`;
7. `OMISSION_ADDITION_EXPERIMENTS`;
8. `SENSORY_COMPARISON`.

`SensomicsProgram` contains one record for every stage in that exact order.
Completed stages form a contiguous prefix; a later stage cannot be completed
after a failed or unperformed earlier stage. Every completed stage requires at
least one immutable evidence reference.

`evaluate_sensomics_claim` allows candidate prioritization after the first five
completed stages. Recombination-match and material-effect claims require the
complete eight-stage sequence and remain limited to the recorded tested
context. Omission impact never means that the omitted odorant resembles the
whole mixture.

### C8 claim boundary

The permitted-with-evidence claims are exactly:

- `PREDICTED_EQUILIBRIUM_HEADSPACE`;
- `PREDICTED_PHYSICAL_RELEASE`;
- `ABOVE_THRESHOLD_SCREENING`;
- `CANDIDATE_ODORANT_PRIORITIZATION`;
- `EXPERIMENT_SELECTION`.

The always-withheld claims are exactly:

- `EXACT_PERCEIVED_INTENSITY`;
- `PERCENT_MIXTURE_CONTRIBUTION`;
- `PLEASANTNESS`;
- `TARGET_SIMILARITY`;
- `FAMILY_IDENTITY`;
- `LONGEVITY`;
- `SILLAGE`;
- `CONSUMER_PREFERENCE`.

`evaluate_c8_claim` requires immutable supporting evidence for a permitted
claim and withholds every unsupported claim even when the caller supplies an
evidence reference. It does not validate an upstream physical model or sensory
study by existence alone; it enforces only the C8 boundary and records that
limitation.

## Determinism and serialization

All public records are frozen, slotted dataclasses. Major artifacts have strict
mapping parsers, canonical mappings, and SHA-256 content identities using the
repository stable JSON hash. Ordered scientific sequences retain order;
unordered reason/evidence sets are canonicalized. Duplicate semantic IDs,
tampered hashes, non-finite numbers, unknown fields, and ambiguous partial
uncertainty fail closed.

No registry, cache, current-time lookup, random UUID, environment value,
database, network call, or mutable global state participates in a C8 result.

## Verification

Focused tests will prove:

- all closed vocabularies and public exports;
- measured versus predicted concentration invariants;
- exact context and unit compatibility;
- threshold-kind and threshold-authority gating;
- bounded uncertainty propagation and threshold-straddling classification;
- abstention is answerless for every failed precondition;
- OAV is never intensity or percent contribution;
- all six interaction kinds and every required context field round-trip;
- generic and observation-only interactions cannot carry or authorize a
  numerical effect;
- context-calibrated authorization still requires exact identity, context,
  target, unit, and applicable range;
- the sensomics stage sequence cannot be skipped or reordered;
- candidate prioritization and causal/recombination claims have different
  evidence gates;
- all five permitted and eight withheld Build C claims;
- deterministic hashes and strict tamper rejection;
- the module imports no legacy OAV/intensity, headspace heuristic, synergy,
  database, backend, production, C9, or sensory-scoring runtime.

Mutation evidence will deliberately remove:

1. predicted-domain or context compatibility enforcement;
2. bounded-uncertainty enforcement;
3. generic-interaction numerical-effect withholding;
4. unsupported-sensory-claim withholding.

Each mutation must be killed and the original bytes restored exactly.

## Exit gate

C8 passes only when focused, C7-C0 compatibility, complete-root, dependency,
static, mutation, archive, protected-state, log-hygiene, DeepLuna Fast,
Sol-reconciliation, evidence-commit, and exact-commit replay gates pass.
Passing C8 opens C9 software work only. It does not validate an existing OAV
table, interaction graph, threshold database, sensory study, or production
formula, and it does not promote any empirical claim.
