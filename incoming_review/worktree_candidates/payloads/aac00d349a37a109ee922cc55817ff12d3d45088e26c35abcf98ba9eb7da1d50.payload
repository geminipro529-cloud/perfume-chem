# Perfume-Chem C0 prepilot evidence package

Date: 2026-08-10  
Status: planning-only validator implemented; all physical work remains on HOLD  
Scope: minimum content and review receipts behind the nine C0 evidence hashes

## Outcome

`engine/sensory/prepilot.py` now closes the gap between "a hash exists" and
"the hash represents a minimally complete prepilot artifact." It adds an
immutable, canonical C0 prepilot bundle without changing the accepted panel
contract or permissive legacy sensory records.

The implementation:

- stores each manifest payload as immutable canonical JSON;
- validates the minimum fields behind every existing C0 binding ID;
- rejects raw participant names, contact details, birth dates, medical records,
  consent documents, and raw screening responses;
- requires separate technical-review receipts before a manifest can become a
  lock candidate;
- preserves exact manifest order when producing `EvidenceBinding` objects;
- applies reviewed timing and repeat values to an unlocked protocol draft;
- cannot select statistical thresholds, lock a protocol, authorize a human
  study, release a perfume, or authorize model calibration.

Current deterministic draft identity:

- bundle SHA-256:
  `8db3003befe66062c63c1b0a1207f5e6d9ec123a9d6f407aacd2a349824df939`
- decision: `HOLD`
- held manifests: 9 of 9
- explicit missing, review, and semantic blockers: 97
- `study_authorized=false`

The blocker count is intentionally granular. It is not a quality score and
must not be optimized as one.

## Evidence refresh

Only public standard metadata and primary research were used. No proprietary
standard text was reproduced, and no claim of ISO or ASTM compliance is made.

| Evidence | Boundary adopted |
|---|---|
| ISO 8586:2023 public abstract | Selection and training need explicit prospective evidence for trained and expert assessors |
| ISO 11132:2021 public abstract | Common attributes and individual scores are required; discrimination, agreement, and repeatability remain separate |
| ISO 8589:2007 public abstract | Test-room and preparation-area conditions require an exact local SOP; the standard is under revision |
| ASTM E2049-20 public scope | Fragrance attribute intensity can be evaluated through time under laboratory conditions with trained assessors; safety applicability remains the operator's responsibility |
| Krasner (1995) | Physical odor references can help establish shared vocabulary, but candidate references must be validated for the exact panel and context |
| Turek (2021) | Recruitment, training, consent, health-state exclusions, blinded samples, and ongoing performance monitoring materially affect panel precision |

No sample count, training duration, intensity cutoff, statistical metric, or
pass threshold from these sources was copied into the contract. Those choices
remain exact-study decisions and require prepilot evidence.

## Nine validated manifest envelopes

| Binding | Minimum content checked before binding |
|---|---|
| `sample_manifest` | Blind-code format and length, custodian role, identity-map receipt, allocation concealment, collision check |
| `preparation_dose_ppm_manifest` | Matrix, concentrate ppm, active application mass, substrate, carrier, SOP receipt, dose tolerance |
| `formula_oav_manifest` | Formula, ODT dataset, OAV report, composite-natural policy, time windows, data-quality review |
| `randomization_manifest` | Sequence method, seed commitment, allocation receipt, carryover rule, blinded roles |
| `anchor_reference_manifest` | Exact lexicon hash, all nine attribute anchors, reference-preparation SOP |
| `participant_plan` | Expertise strata, eligibility, screening, anosmia policy, training, repeats, attrition, privacy separation, receipt schema |
| `environment_timing_manifest` | Room SOP, temperature/humidity ranges, ventilation, session limit, sniff times, rest interval, confounders |
| `analysis_plan` | Estimands, missingness, multiplicity, uncertainty, three independent gate receipts, partition separation, implementation receipt |
| `ethics_privacy_safety_review` | Applicability determination, consent/privacy plans, exposure review, withdrawal/adverse-event processes, jurisdiction |

All nested fields ending in `_sha256` are checked as lowercase SHA-256
digests. `False` and zero remain explicit values rather than being confused
with missing data; empty strings, empty collections, and `null` remain unbound.

## Anchor-reference strategy frozen without materials

The draft defines the kind of evidence required but deliberately selects no
physical material, formula, concentration, or dose.

| Attribute | Draft reference mode | Physical reference status |
|---|---|---|
| Airiness | Graded sample set | Required, unbound |
| Separability | Graded sample set | Required, unbound |
| Density | Graded sample set | Required, unbound |
| Coherence | Graded sample set | Required, unbound |
| Target fidelity | Target-reference task | Required, unbound |
| Contrast | Graded sample set | Required, unbound |
| Emergence | Component-versus-mixture comparison | Required, unbound |
| Recognition | Blind target-choice task | Required, unbound |
| Pleasantness | Verbal scale only | Physical training references prohibited |

Pleasantness is personal hedonic evidence. Training participants toward a
physical "pleasant" sample would redefine the endpoint and bias it toward the
trainer's preference, so the validator rejects that configuration.

No inventory-dependent work occurred in this increment. Before any physical
anchor sample is selected or compounded, the live `inventory.txt` and
formulation instructions must be read, every dose must be expressed in ppm,
and the exact formula must carry ODT/OAV evidence. Naturals must use composite
OAV or document that no natural mixture is present.

## State model

Each manifest is one of:

- `draft`: no review receipt and never bindable;
- `technical_reviewed`: review receipt present but still not bindable;
- `lock_candidate`: potentially bindable only when every required field is
  populated, no unresolved item remains, and all semantic checks pass.

`lock_candidate` is not ethical approval, study authorization, or scientific
validation. It means only that the exact artifact is complete enough to become
one content-addressed input to the existing protocol.

## Applying a complete bundle

`apply_prepilot_bundle()` requires the exact base protocol and lexicon hashes.
It then:

1. emits the nine `EvidenceBinding` objects in existing contract order;
2. copies reviewed sniff timepoints from the environment manifest;
3. copies reviewed repeat count from the participant plan;
4. leaves `protocol_locked=false`;
5. leaves all study, release, and model-calibration authority flags false.

The resulting protocol remains C0 `HOLD` until the separate discrimination,
agreement, and repeatability gate specifications are selected from prepilot
evidence, preregistered, locked, and actually passed.

## DeepLuna Chat result

A fresh exact-project check returned `READY` with settled accounting. One
bounded `DIRECT_PRO`-only read audit was requested. It failed closed with zero
evidence receipts because its repository-read budget was exhausted. No worker
claim was accepted, no retry or alternate provider was used, and Sol completed
the implementation from locally inspected evidence.

## Verification

Local acceptance completed on 2026-08-10:

- Ruff passed for the sensory exports, prepilot validator, and prepilot tests;
- 77 focused sensory, panel-contract, construction-complexity, and calibration
  tests passed;
- Python bytecode compilation passed for the touched sensory modules and tests;
- `git diff --check` found no whitespace errors on the exact changed paths;
- independent processes using `PYTHONHASHSEED=1` and `987654` produced the
  same lexicon, protocol, and bundle identities.

Deterministic identities replayed in both processes:

- lexicon SHA-256:
  `5a0804a923cc312d9075ee8614cd1aa79941e65bba7bba35922f40148043c490`;
- base protocol SHA-256:
  `f795e561bf075a2a8ac4e7c7f131e87e37f9df3865b089068c403c2d40895441`;
- draft bundle SHA-256:
  `8db3003befe66062c63c1b0a1207f5e6d9ec123a9d6f407aacd2a349824df939`.

The focused test contract covers:

- deterministic draft identity and default `HOLD`;
- immutable canonical payload copies;
- raw-participant-data rejection;
- common PII-key alias rejection and malformed-strata fail-closed handling;
- review-receipt and unresolved-item gates;
- exact ordered evidence bindings;
- binding without protocol lock or C0 `GO`;
- base-protocol identity protection;
- complete lexicon anchor coverage;
- exact construction-anchor modes and hashed gate-specification receipts;
- prohibition on pleasantness training references;
- composite-natural OAV policy enforcement;
- formula OAV coverage of every sensory sniff timepoint.

## Next high-value work

The next increment is laboratory-authoring work, not another schema:

1. inspect live inventory and safety/physics coverage;
2. propose the smallest candidate graded sample sets for airiness,
   separability, density, coherence, and contrast;
3. define target, emergence, and recognition task stimuli;
4. calculate every candidate in ppm with ODT/OAV and active-dose evidence;
5. create preparation and room SOP candidates;
6. retain all manifests as drafts until applicable safety, privacy, ethics,
   and technical reviews are represented by real receipts.

## References

- ISO. [ISO 8586:2023](https://www.iso.org/standard/76667.html).
- ISO. [ISO 11132:2021](https://www.iso.org/standard/76669.html).
- ISO. [ISO 8589:2007](https://www.iso.org/standard/36385.html).
- ASTM. [E2049-20](https://store.astm.org/e2049-20.html).
- Krasner SW. [The use of reference materials in sensory analysis](https://doi.org/10.1016/0273-1223(95)00486-7). 1995.
- Turek P. [Recruiting, training and managing a sensory panel in odor nuisance testing](https://doi.org/10.1371/journal.pone.0258057). 2021.
