# Checkpoint 8 maintenance — external-validation intake contract repair

Date: 26 September 2026

Status: `SOFTWARE_CONTRACT_REPAIR_COMPLETE_EXTERNAL_VALIDATION_STILL_ON_HOLD`

## Decision

The read-only temporal-observation and scoped pairwise-preference contracts are
again executable. This closes two source/test interface drifts that prevented
the repository from collecting and evaluating bounded external-validation
records. It does not create evidence, authorize a human study, persist a
canonical observation, validate a preference model for R6, rank a formula, or
change the Checkpoint 8 `NO_CHANGE` decision.

```text
temporal_observation_contract = PASS_READ_ONLY_OBSERVED_ONLY
scoped_preference_contract    = PASS_EVIDENCE_ONLY_DIAGNOSTIC
canonical_persistence_state   = HOLD_NOT_WIRED_BY_THIS_REPAIR
physical_sample_state         = NOT_AVAILABLE
human_observation_state       = NOT_COLLECTED
pleasantness_state            = NOT_ESTABLISHED
physical_liking_state         = NOT_TESTED
formula_action                = NO_CHANGE
formula_modified              = false
inventory_modified            = false
```

## Provenance and scope

The missing interfaces were recovered from the repository's own historical
implementation at commit `5d032baa` (`feat: add evidence-gated complexity
replacement candidates`) and reconciled with the current read-only ledger.
The current tests were already written against that base contract. The repair
does not copy the later V2/V3 evidence-promotion layers, Davidson preference
model, or retired temporal-observation generator.

Current repaired source hashes:

| Surface | SHA-256 |
|---|---|
| `engine/sensory/ledger.py` | `46fc9fa63c4dc6878ace417b08b16232b729822554f3ba4049aa4654e924883c` |
| `engine/preference.py` | `20ecbfe90e838361d08d8236f3325f124630d4fe8a50677f45223e76b00cc575` |
| `tests/test_temporal_sensory_evidence.py` | `25d5558e89d0de790b658efdbdb4f948fd3030fecf720d82bffcbee48acf1d60` |
| `tests/test_scoped_preference.py` | `3e54094a89426257b276c66c3d91e00e302ede9bca38161ad2e29dbc615b02c8` |

## Repaired temporal-observation boundary

The ledger now provides immutable types for:

- a canonical cell key bound to protocol, sample, assessor, repeat, timepoint,
  and endpoint;
- an observed value plus presentation sequence and position;
- a declared protocol grid and presentation-schedule hash;
- completeness, duplicate-cell, order-balance, and within-sniff qualification
  checks; and
- deterministic observed-only endpoint summaries and temporal deltas.

Missing cells remain missing. No interpolation is performed. A schedule hash
mismatch, duplicate canonical cell, unbalanced order, unqualified within-sniff
protocol, or out-of-scope observation produces `HOLD`. Boolean/nonfinite
numeric inputs and nonintegral presentation positions are rejected.

Every temporal result retains:

```text
interpolated_cell_count       = 0
physical_execution_authorized = false
sensory_authority              = false
release_authority              = false
```

## Repaired scoped-preference boundary

`PairwisePreference` again accepts and round-trips optional comparison,
assessor, protocol, criterion, time, and presentation-order fields without
breaking the three-argument legacy constructor. The preference diagnostic now:

- withholds mixed criteria instead of pooling them;
- treats ties as retained descriptive observations while fitting the legacy
  Bradley-Terry utility only to decisive rows;
- uses deterministic seeded bootstrap intervals;
- cluster-resamples by assessor when assessor identifiers are complete;
- reports assessor disagreement, a descriptive order-effect statistic, and a
  deterministic next comparison; and
- refuses `VALIDATED` status when required scope metadata or pairwise order
  balance is incomplete, even if held-out accuracy beats the declared baseline.

The word `VALIDATED` is local to this model's declared held-out comparison
contract. It is not R6 liking evidence, a population claim, a sensory-release
decision, or authority to optimize or compound.

## Verification

- Temporal evidence contract alone: 12 tests passed.
- Temporal ledger, legacy sensory ledger, and order balance: 48 tests passed.
- Preference and scoped-preference contracts: 7 tests passed.
- Checkpoint 8 plus temporal intake: 28 tests passed.
- Broader sensory, panel, preference, and hedonic boundary regression: 145
  tests passed.
- Focused Ruff: passed.
- Focused mypy with third-party imports skipped: passed.
- Quick project verification passed 9 checks and failed only the pre-existing
  formula-artifact validation for stale/quarantined formula artifacts. The
  reviewed golden fixture remained byte-identical at
  `9cf31e92d3c8e814f3bc2654ffba6f3fbd766de8c705630ae78fb5c24a1dfc61`.
- Scoped `git diff --check`: passed; Git reported only the repository's normal
  LF-to-CRLF working-copy warnings.

These checks are not used to expand the scientific authority above.

## Remaining boundary

The design document correctly described both type/test and persistence work as
outstanding. This maintenance closes the type/test drift only. A later,
separately reviewed change may add an additive server-owned persistence path
that binds observations to exact protocol, sample, condition, order, assessor,
and provenance receipts. It must not revive `SensoryTrial` mutation, accept
caller-created scientific authority, or convert stored rows into an R6 winner.

Before any real R6 sensory record can be evaluated, Checkpoints 5–7 still need
their exact physical build, aging/storage, measurement, and curve-applicability
receipts, and participant-facing work needs separate explicit authority. Until
then, the truthful endpoint remains `NO_CHANGE`.
