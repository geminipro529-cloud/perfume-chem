# Checkpoint 8 — R6 sensory-evidence intake

Date: 26 September 2026

Formula scope: Lavande Ambre Profond R6

Checkpoint type: read-only software and evidence-boundary completion

Physical study status: not authorized and not performed

## Decision

Checkpoint 8 is software-complete and remains scientifically held:

```text
checkpoint8_state    = SOFTWARE_COMPLETE_SENSORY_EVIDENCE_INTAKE_HOLD
sensory_evidence     = HOLD_CP8_PHYSICAL_STUDY_OR_EXACT_SCOPE_EVIDENCE_INCOMPLETE
project_phase        = SOFTWARE_CHECKPOINT_SEQUENCE_COMPLETE_EXTERNAL_VALIDATION_PENDING
pleasantness_state   = NOT_ESTABLISHED
personal_liking      = NOT_TESTED
population_liking    = NOT_TESTED
formula_action       = NO_CHANGE
ranked_candidates    = []
best_candidate       = null
```

This is the intended truthful result. The checkpoint completes the repository
contract for receiving and evaluating future exact-condition sensory evidence;
it does not manufacture evidence that has not been collected.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `data/governance/lavande_ambre_profond_r6_cp8_sensory_evidence_intake_20260926.json` | `dfc4a19fd4031f7caa51a5a62b73446a1931c07eafefbde790b285c78eb51a9a` |
| `engine/experiments/checkpoint8_readiness.py` | `a1445d0ad2b2a4441282e57cd1c6689101af24a2b1bca1b315c450929084e13c` |
| deterministic Checkpoint 8 report | `9e2d99971d863dcbd83ea1e207347189a237afd1fe45c308f94cb4dd82466888` |

The intake pins Checkpoint 7 protocol hash
`80765f37c144e64252c3e60e597e906822def4954a2c8356ecee237a6a98d6f8`,
Checkpoint 7 evaluator hash
`c0f1cb6d8805344f7b092587f045337e22dfd58818cde35886324340ef0dc62d`,
and Checkpoint 7 report hash
`98a7537c82007a267fc408d7c6231b8e98d688c40b2222e676f3304e789373d0`.
Checkpoint 7 is still a HOLD, so it cannot be bypassed to create sensory
authority.

## Human-data literature boundary

The repository already contains two useful human-data sources, but neither is
an R6 result.

### Bierling 2025

The pinned source manifest records CC BY 4.0 data, 1,227 included participant
codes, 12,005 included non-empty numeric pleasantness rows, and 73 included odor
codes. The publication headline refers to 74 odors, so the identity mapping
requires reconciliation before modeling. More importantly, the dataset is a
monomolecular-odor population resource, not mixture-level R6 liking evidence
and not a systematic full-perfume multi-dose study.

### Ma 2021

The governed benchmark contains 198 unique binary-mixture groups and 222 source
trial rows. Squared-intensity weighting is descriptively best among the three
predeclared pleasantness baselines in that source, with RMSE
`0.394525286290`. Its authority remains `SOURCE_INTERNAL_CALIBRATION_ONLY`.
Formula prediction, cross-study generalization, participant inference, R6
sensory claims, and physical or release actions are all false.

No public-source result is relabeled as R6 pleasantness or liking.

## Exact-scope hedonic platform result

Checkpoint 8 executes the repository's real eight-view hedonic platform with
an empty R6 exact-scope packet:

```text
platform schema       = hedonic_evidence_platform_v4
platform views        = 0
decision states       = 0
authority ceiling     = withheld
native criteria       = 12, all UNKNOWN
ranked winner          = unavailable
```

The platform content hash is
`999ead7dab43cb7b5ec26b1610d4c23311eaf4fb885f00db9b706d9fd6b3c336`;
the R6 unresolved scope hash is
`14fbf97e65a18e0058af06d6aa508554a57856181adb9ded1e609fca0e9577c1`;
and the resulting assessment hash is
`c67c1f8122eed1cce59a667b8cda639a435299ff7925f74db2c9379e00b48a5a`.

The platform preserves exact sample, concentration, matrix, time, participant,
assessor, session, order, predecessor, carryover, repeat, missingness, cluster,
and provenance scope. It cannot derive a Pareto decision without linked human
observations. Ties, abstentions, missing outcomes, and opposing clusters remain
explicit rather than being converted into zeroes or an averaged winner.

## Panel-readiness result

Checkpoint 8 evaluates the existing strict C0 sensory-panel draft rather than
inventing a new protocol:

```text
exit decision          = HOLD
protocol locked        = false
required bindings      = 9
bound bindings         = 0
locked panel gates     = 0 of 3
sniff timepoints       = unbound
repeat count           = 0
study authority        = false
release authority      = false
model-calibration      = false
```

The nine required bindings are:

1. sample manifest;
2. preparation, dose, ppm, matrix, substrate, and procedure manifest;
3. formula ODT/OAV screening manifest;
4. randomization, concealment, and carryover manifest;
5. physical anchor and reference manifest;
6. participant eligibility, expertise, screening, training, and repeat plan;
7. environment and sniff-timing manifest;
8. preregistered estimand, missing-data, multiplicity, and decision plan; and
9. applicable ethics, privacy, exposure-safety, and review receipts.

Discrimination, agreement, and repeatability remain separate gates. Their
thresholds must be selected from prepilot evidence and preregistered; no
universal threshold is fabricated. Blotter and skin evidence must remain
separate.

## Legacy hedonic quarantine

The legacy fixed-valence implementation returns `50` for empty input. That
value is verified and explicitly quarantined as:

```text
classification                   = HEURISTIC_DIAGNOSTIC_INDEX
ranking_status                   = WITHHELD
formula_optimization_authority   = false
sensory_validation_status        = NOT_ESTABLISHED
full_formula_pleasantness        = NOT_ESTABLISHED
scope                            = FIXED_VALENCE_TABLE_SUBSET_ONLY
```

The value cannot populate a human observation, break a tie, select R6, or enter
an optimizer objective. OAV, log-OAV, ingredient count, descriptor distance,
and hand-assigned valence likewise remain prohibited as pleasantness or beauty
substitutes.

## Durable-job integration

`SHORTLIST_EVALUATION` now includes a
`checkpoint8_sensory_evidence_intake` receipt after its Checkpoint 7 receipt.
The job capability fingerprint includes the CP8 manifest and evaluator, the
hedonic platform and contracts, the panel contract, the source manifest, the Ma
benchmark, the legacy hedonic implementation, optimizer scoring, and the panel
review. Missing, malformed, drifted, evidence-injected, or authority-escalated
CP8 inputs fail closed before shortlist output.

The receipt remains advisory. It cannot create samples, contact participants,
admit evidence, train or calibrate a model, rank a formula, change inventory,
compound, purchase, make safety claims, or release a formula.

## Verification

Focused verification performed for this checkpoint:

- Checkpoint 8 evaluator tests: 16 passed.
- Durable engine-job tests, including CP8 omission, drift, evidence-injection,
  and authority-escalation cases: 19 passed.
- Checkpoint 3–8 plus measured-intensity, strict-panel, exact-scope hedonic,
  legacy-hedonic-authority, and targeted-hedonic regressions: 170 passed.
- Focused Ruff checks passed for every changed Python surface.
- Focused backend mypy passed for both changed services. The Checkpoint 8
  evaluator also passed mypy with imports skipped; unrestricted checking is
  currently blocked by a syntax error in the installed third-party
  `rdkit-stubs` package.
- The evaluator was run twice with byte-identical protocol input and returned
  the same report hash.
- Quick project verification passed 9 checks and failed only the existing
  formula-artifact validation because quarantined formula artifacts are stale.
  The reviewed golden fixture remained byte-identical at
  `9cf31e92d3c8e814f3bc2654ffba6f3fbd766de8c705630ae78fb5c24a1dfc61`.
- A broader legacy temporal-sensory test was not collectable because it imports
  `ObservationCellKey`, which is absent from the current sensory ledger. That
  unrelated pre-existing interface drift was not changed or hidden by CP8.

Post-checkpoint maintenance on 26 September 2026 restored that read-only
interface and the neighboring scoped-preference contract without changing this
checkpoint's frozen manifest or authority. See
`docs/verification/CHECKPOINT8_EXTERNAL_VALIDATION_INTAKE_REPAIR_20260926.md`.

The full release verifier is intentionally not required because this checkpoint
does not claim merge or release readiness.

## What remains after the software checkpoints

The remaining work is external validation, not another computational shortcut:

1. close Checkpoints 5–7 with exact stock, parent, preparation, build, aging,
   storage, matrix, calibration, measured gas, and curve-applicability receipts;
2. obtain separate authority for participant-facing sensory work;
3. preregister and lock the nine panel bindings and three performance gates;
4. prepare traceable coded physical samples and retain exact condition/order
   metadata;
5. collect and retain exact-condition pleasantness, target-fidelity, aversion,
   defect, and pairwise-preference observations without deleting ties or
   missingness;
6. evaluate evidence within its exact scope and preserve an unordered result
   if it does not discriminate candidates; and
7. perform separate stability, safety, regulatory, and release review.

Until those steps occur, the scientifically correct project endpoint is
`NO_CHANGE`, not a winner.
