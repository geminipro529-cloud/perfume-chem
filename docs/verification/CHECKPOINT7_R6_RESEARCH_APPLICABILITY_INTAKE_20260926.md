# Checkpoint 7 — R6 Research Applicability Intake

Date: 2026-09-26

Formula lineage: Lavande Ambre Profond R6, design successor only

Checkpoint status: `SOFTWARE_COMPLETE_RESEARCH_APPLICABILITY_INTAKE_HOLD`

Research applicability: `HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE`

Formula action: `DESIGN_SUCCESSOR_UNCHANGED`

## Decision

Checkpoint 7 is complete as a software and evidence-boundary checkpoint. It is
not complete as a physical research execution checkpoint. The repository now
has a frozen, deterministic, read-only intake contract and evaluator that bind
the exact Checkpoint 6 state, the unresolved Checkpoint 5 measurement schema,
the governed Wakayama curve capability, the cached source artifacts, and the
release-model implementations. The result truthfully abstains for every R6 row
and prevents durable shortlist jobs from presenting a curve, release
simulation, OAV, mixture challenger, pleasantness estimate, or formula ranking
as applicable evidence.

No formula, inventory, stock, build plan, reservation, mixer command, transfer
record, research sample, measurement, sensory result, or canonical evidence
record was created or changed.

## Frozen artifacts and fingerprints

| Artifact | SHA-256 |
|---|---|
| `data/governance/lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json` | `80765f37c144e64252c3e60e597e906822def4954a2c8356ecee237a6a98d6f8` |
| `engine/experiments/checkpoint7_readiness.py` | `c0f1cb6d8805344f7b092587f045337e22dfd58818cde35886324340ef0dc62d` |
| Deterministic Checkpoint 7 readiness report | `98a7537c82007a267fc408d7c6231b8e98d688c40b2222e676f3304e789373d0` |
| Checkpoint 6 protocol | `213c256a7ec7c16578bb0556cb9f12258d757191217d4e6a3a0ffe0033265823` |
| Checkpoint 6 deterministic report | `ac0a43d37f723b3efa368618783c7178f082d75efe6f9c0549bd24efaeb60e92` |
| Checkpoint 5 protocol | `8707eecdc09a360b9a09d9b363bc7476ed9024a5f78ffe10d1b2732a84d24af0` |
| R6 canonical rows | `40889e8a43a780bf60d35a10fe4861a56f20d1a2a66e72141a5ceb8b8000eb4b` |

The Checkpoint 7 protocol also pins the following scientific surface:

| Scientific input | SHA-256 |
|---|---|
| Measured-intensity capability manifest | `fee99f21290212cc0c46df0c464130117eb5c41b8a5dc89db75270d71bfbc464` |
| Source manifest | `2022427c6247c07d27dd01e387bf35fb431cb9ff4f53742bc20f4773879a34fa` |
| Wakayama supplementary PDF | `b62f567840ddcc8b1b305784aa8245f2b5c53b07a820c42613482134cd567104` |
| Wakayama transcription | `739243c505187b5384ddacbbe2ab674b53fb8cd0b58e25733bd6bae5547c23eb` |
| `engine/dose_response.py` | `d6d788877cf7a873b41482ff37f07ba705be0199d349512ffde531ed0fec2338` |
| `engine/physics/dynamic_release.py` | `3ca7601c3f648b373f8f5890e0681c6ee86b3e198ff9c2ebed8386519c83a978` |
| `engine/physics/headspace_oav.py` | `e75414febeb7bd01baad0633d64763904151ea1ba81222344a4f624ad0f9d902` |

Any drift in a pinned file, authority field, evidence array, identity rule,
curve-input rule, mixture rule, endpoint state, or predecessor fingerprint
invalidates the intake instead of silently changing the result.

## Current evidence census

| Item | Current value |
|---|---:|
| R6 formula rows evaluated | 63 |
| Rows backed by a physical R6 research sample | 0 |
| Rows with measured gas-concentration input | 0 |
| Rows with an exact applicable curve | 0 |
| Rows with an exact curve and observed-range binding | 0 |
| Rows with exact matrix, delivery, and scenario binding | 0 |
| Whole-formula curve applicability | false |
| Executable mixture challengers | false |

The source parameter table contains 314 rows. Of those, 313 have positive
evaluable slopes; one row, CAS `121-33-5`, has a nonpositive slope. The current
governed capability has 313 unadjudicated identities, one identity conflict,
zero exact material bindings, and zero per-curve observed-range bindings. This
is mathematical availability, not R6 applicability.

## Scientific boundary

The admitted curve input is gas mass concentration in `ug/L_air`. Liquid stock
dose, stock fraction, concentrate percentage, OAV, or an unvalidated modeled
release result cannot be substituted for that measurement. The dynamic-release
implementation remains `SIMULATION_ONLY_UNCALIBRATED`; it is neither measured
headspace nor a calibrated release model and cannot establish curve input.

The strongest-component, fitted partial-addition, and primacy-transfer models
remain separate challengers. None may execute for R6 while component
calibration is incomplete, and their outputs cannot be averaged into an
unvalidated ensemble. No mixture challenger has formula-optimization authority.

Endpoint states remain independent:

- Physical release: `NOT_MEASURED`
- Sensory intensity: `NOT_ESTABLISHED`
- Character: `NOT_ESTABLISHED`
- Pleasantness: `NOT_ESTABLISHED`
- Personal liking: `NOT_TESTED`
- Population liking: `NOT_TESTED`
- Beauty: `PROHIBITED_DERIVED_ENDPOINT`

The Wakayama source and its December 2020 correction are retained for
attributed noncommercial research under the recorded `CC BY-NC 4.0` scope.
Commercial use is not authorized by this checkpoint, and source-fit overlap
remains `UNKNOWN`.

## Durable job integration

`SHORTLIST_EVALUATION` now loads the frozen Checkpoint 7 intake only after the
Checkpoint 3 through Checkpoint 6 contracts pass their own integrity checks.
The returned receipt contains the research-sample state, measurement state,
curve inventory, gas-input contract, release boundary, applicability census,
mixture boundary, endpoint states, blockers, authority, and zero side effects.

The engine-job capability fingerprint now includes the Checkpoint 7 protocol
and evaluator plus the exact governed curve, source, release, and headspace
surfaces. Missing input returns `HOLD_CP7_RESEARCH_PROTOCOL_UNAVAILABLE`;
malformed input returns `HOLD_CP7_RESEARCH_PROTOCOL_INVALID`; scientific or
contract drift returns `HOLD_CP7_RESEARCH_PROTOCOL_DRIFT`; and an authority
escalation returns `HOLD_CP7_RESEARCH_PROTOCOL_AUTHORITY_ESCALATION`.

## Active blockers

1. `HOLD_CP7_CP6_PHYSICAL_READINESS_INCOMPLETE`
2. `HOLD_CP7_RESEARCH_SAMPLE_NOT_COMPOUNDED`
3. `HOLD_CP7_MEASUREMENT_EXECUTION_PARAMETERS_UNRESOLVED`
4. `HOLD_CP7_MEASURED_GAS_INPUTS_UNAVAILABLE`
5. `HOLD_EXACT_CURVE_APPLICABILITY`

Checkpoint 5 still has 17 unresolved physical execution parameters and eight
unresolved sensory controls. Blotter and skin remain separate domains.

## Delegation and research disposition

The permitted exact-project DeepLuna/DeepSeek route was checked before the
implementation work. It is disabled in the current project configuration and
its token is recorded as off. No task packet or repository content was sent,
and no DeepMimo, Luna, OpenRouter, alternate provider, legacy route, or cached
answer was substituted. The literature review therefore reused the already
hashed local source bundle and was verified against current repository bytes.

## Verification

- Root readiness and measured-curve suite: **85 passed**.
- Durable engine-job suite: **17 passed**.
- Root Ruff focused check: passed.
- Backend Ruff focused check: passed.
- Checkpoint 7 evaluator mypy check with imported-module traversal skipped:
  passed with no issues.
- Backend changed-service mypy check: passed with no issues.
- Quick project verification passed nine checks, failed one, and retained
  unchanged golden output. Its completion gate remains `FAIL` solely because
  the pre-existing formula-artifact validation contains stale/quarantined
  formula artifacts. This checkpoint does not rewrite or release those formula
  artifacts.
- Full release verification was not run because this checkpoint makes no merge
  or release-readiness claim.

## Stop boundary and next checkpoint

Checkpoint 7 stops here. Its future pass state is
`PASS_CP7_R6_RESEARCH_SAMPLE_CHARACTERIZED`, but software alone cannot produce
that state.

Before a later checkpoint may characterize or compare R6, the project needs:

1. a genuine Checkpoint 6 pass with all 63 stock bindings and required
   preparation, lot, density/conversion, and lineage receipts;
2. separately authorized physical compounding and traceable R6 research
   samples, replicate, blank, and justified reference;
3. all 25 measurement and sensory execution parameters resolved before work;
4. calibrated instrument and matrix methods plus measured gas observations;
5. exact curve identity, observed range, matrix, delivery, scenario, license,
   and source-fit adjudication;
6. a new immutable evidence receipt reviewed by local authority.

Until those conditions are met, the correct result remains `HOLD` and the
formula remains unchanged.
