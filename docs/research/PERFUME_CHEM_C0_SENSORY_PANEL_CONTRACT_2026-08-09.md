# Perfume-Chem C0 sensory-panel contract

Date: 2026-08-09  
Status: implemented planning contract; empirical work not authorized  
Scope: vocabulary, blinding/privacy schema, evidence bindings, and C0 stop/go

## Outcome

The highest-value dependency for the construction-complexity program is now a
strict parallel sensory contract. It does not modify the permissive legacy
`PanelResult` or `SensoryObservation` records and does not reinterpret old rows
as qualified panel evidence.

The implementation is in `engine/sensory/panel_contract.py`. It provides:

- a versioned and content-hashed C0 lexicon;
- eight construction attributes plus a separate hedonic endpoint;
- pseudonymous qualification receipts without raw identity or health data;
- blind-code-only observations with session, repeat, and sniff-time identity;
- exact hashes for sample, dose, OAV, randomization, anchors, participants,
  environment, analysis, and applicable ethics/privacy/safety review;
- independent discrimination, agreement, and repeatability gates;
- explicit `GO`, `HOLD`, and `STOP` decisions that never grant study, release,
  or model-calibration authority.

Current deterministic identities:

- lexicon SHA-256:
  `5a0804a923cc312d9075ee8614cd1aa79941e65bba7bba35922f40148043c490`
- fail-closed draft protocol SHA-256:
  `f795e561bf075a2a8ac4e7c7f131e87e37f9df3865b089068c403c2d40895441`
- current draft decision: `HOLD` with 18 explicit blockers

The hashes bind the exact canonical payload. They are not evidence that a
human study occurred or that any sensory hypothesis is true.

## Literature and standards review

Only public ISO metadata was used. The proprietary standards were not
reproduced, and Perfume-Chem does not claim ISO compliance.

| Evidence | What it supports here | What it does not authorize |
|---|---|---|
| ISO 8586:2023 public abstract | Explicit assessor selection and training evidence | A universal screening threshold or an ISO-compliant panel |
| ISO 11132:2021 public abstract | Individual scores and separate discrimination, agreement, and repeatability performance dimensions | Substitution of one panel metric for another |
| ISO 13299:2016 public abstract | A common attribute list and anchored quantitative profile | The eight Perfume-Chem attributes as universally validated constructs |
| ISO 8589:2007 public abstract | Controlled test-environment planning | A claim that the current room or procedure conforms to ISO 8589 |
| ISO 5495:2005 public abstract | Directional or paired discrimination when that is the preregistered question | Magnitude, similarity, pleasantness, or construction-complexity claims |
| Barkat et al. (2012) | Expertise can alter elemental/configural odor perception | Pooling expert and untrained responses |
| Morquecho-Campos et al. (2019) | Odor identification can improve with training, with limits for complex mixtures | Treating training as proof of mixture decomposition ability |
| Laor et al. (2011) | Screening can examine multiple assessor capabilities | Importing its task-specific cutoffs as universal perfume thresholds |
| Latreille et al. (2006) | Discriminability, repeatability, and agreement should be evaluated separately | A single undifferentiated panel-quality score |
| Green et al. (1996) | Anchored magnitude scaling is psychophysically motivated | A claim that 0-10 intervals are ratio-scale measurements |
| Pellegrino et al. (2026 preprint) | A recent example using physical references, training sessions, repeats, and RATA ratings | A universal minimum panel size or correlation threshold |

The 2026 Pellegrino preprint is provisional and has disclosed industry
conflicts. Its reported design choices are useful examples, not defaults. No
sample-size, test-retest, effect-size, or significance threshold from that
study was copied into the software.

As of this review, the ISO page reports ISO 11132:2021 under systematic review,
and ISO 8589:2007 as current but expected to be revised. Any eventual protocol
must re-check current versions before preregistration.

## Frozen vocabulary

All attributes use explicit 0, 5, and 10 anchors. Missingness is never encoded
as zero; it requires a written not-applicable reason.

| Attribute | Operational boundary |
|---|---|
| Airiness | Spatial openness or room between concurrent impressions; not strength or diffusion |
| Separability | Ease of perceiving concurrent impressions as distinct; not descriptor count |
| Density | Compactness or filled sensory mass; measured independently from airiness |
| Coherence | Perceived integration or intentional relation among parts; not liking |
| Target fidelity | Match to a preregistered description or physical reference; not applicable without a target |
| Contrast | Differentiation between preregistered foreground/background roles or adjacent regions |
| Emergence | A whole-mixture quality beyond separately presented components; requires the planned comparison |
| Recognition | Confidence in a target choice; objective correctness comes from the separate choice response |
| Pleasantness | Personal hedonic response, stored separately and never treated as complexity evidence |

Airiness and density are deliberately not encoded as mathematical inverses.
A perfume can be dense yet preserve local space around distinct heavy notes,
or be sparse but blurred. The panel must be allowed to report those cases.

## Strict data boundary

### Participant qualification receipt

The repository stores only opaque SHA-256 tokens and receipts for:

- participant pseudonym;
- exact protocol;
- consent and privacy notice;
- eligibility;
- olfactory screening;
- specific-anosmia screening when the participant plan says it is relevant;
- training for trained descriptive or perfumer-expert strata.

Raw names, contact information, medical details, screening responses, and
consent documents are outside this contract. Trained descriptive,
perfumer-expert, and untrained participants remain separate strata.

### Panel observation

An observation contains only:

- an opaque observation token;
- an uppercase blind code;
- participant and qualification receipt hashes;
- exact protocol and lexicon hashes;
- session and repeat identity;
- locked sniff time;
- one explicit response for every lexicon attribute;
- an optional target-choice identifier.

It cannot contain a formula ID, batch ID, or raw assessor name. Formula-to-code
mapping belongs in the separately bound, custodian-only sample manifest.

## Evidence bindings required before protocol lock

| Binding | Required content |
|---|---|
| `sample_manifest` | Blind-code allocation and custodian-only sample identity |
| `preparation_dose_ppm_manifest` | Matrix, concentrate ppm, active dose, substrate, and preparation procedure |
| `formula_oav_manifest` | Formula-level ODT/OAV screening receipt for every dosed sample |
| `randomization_manifest` | Sequence generation, concealment, carryover, and order controls |
| `anchor_reference_manifest` | Physical references and training anchors for every attribute |
| `participant_plan` | Eligibility, strata, screening, training, repeat, and attrition rules |
| `environment_timing_manifest` | Room conditions, ventilation, sniff times, and session limits |
| `analysis_plan` | Estimands, missingness, multiplicity, uncertainty, and stop/go rules |
| `ethics_privacy_safety_review` | Applicable consent, privacy, exposure-safety, and review receipts |

This keeps Rule 1 intact for eventual physical samples: concentration is bound
in ppm, active dose is explicit, and formula ODT/OAV evidence must exist. No
formula or physical dose was created by this C0 implementation.

## Stop/go contract

### `HOLD`

`HOLD` is the default. It applies when any protocol evidence is unbound, a
sniff or repeat plan is absent, a gate threshold is provisional or unbound, a
result is missing or inconclusive, or any protocol/specification/analysis hash
or pilot partition does not match.

The software intentionally ships with no universal threshold. Each of these
must be selected from the exact prepilot design and then preregistered:

1. discrimination;
2. agreement;
3. repeatability.

### `STOP`

`STOP` applies when at least one valid, exact-protocol panel-performance result
fails its preregistered gate. A mismatched or unbound result cannot produce a
valid stop; it produces `HOLD`.

### `GO`

`GO` requires all nine evidence manifests bound, the exact lexicon bound,
blinding and randomization, individual responses retained, strata separated,
pilot and confirmatory partitions separated, at least two planned repeats,
locked sniff times, and valid `PASS` results for all three independent panel
performance gates.

Even then, `GO` means only: **the exact C0 exit contract is satisfied**.
`study_authorized`, `release_authority`, and `model_calibration_authority`
remain hard-coded `false`.

## Why the legacy records were not extended

Legacy `PanelResult` and `SensoryObservation` rows lack exact protocol,
lexicon, qualification, repeat, analysis, and panel-performance bindings.
Their loaders also default absent fields permissively. Making new fields
mandatory there would either break old data or, worse, silently elevate it.

A parallel strict contract therefore preserves backward compatibility while
making the evidence boundary explicit. Legacy observations can remain useful
as exploratory notes, but they cannot satisfy C0 gates without a new,
prospectively bound study.

## C1 handoff

The next safe work is not formula optimization. It is to prepare the exact C0
prepilot package:

1. create physical anchor-reference candidates for each attribute;
2. specify assessor eligibility, training, screening, and privacy handling;
3. define controlled room, dosing, ppm, ODT/OAV, timing, repeat, and
   randomization manifests;
4. select statistical estimands and provisional thresholds using prepilot
   variance and effect information;
5. preregister and lock the protocol without using pilot outcomes for
   confirmatory claims;
6. run the qualified-panel C0 exit assessment only after applicable human
   research, safety, consent, and privacy approvals are obtained;
7. if and only if C0 returns `GO`, prepare a separately authorized C1
   complete/gap-filled/omission negative-space triad study.

## Verification completed

- RED test: missing strict module failed collection as expected.
- Focused contract tests: 12 passed.
- The tests cover vocabulary hashing, separate hedonics, fail-closed drafts,
  lock rejection, independent gates, `GO/HOLD/STOP`, pilot/confirmatory
  separation, training receipts, blind-code-only observations, complete
  lexicon responses, explicit missingness, and hard authority boundaries.
  They also prove that a failure from an unlocked protocol or mismatched
  lexicon cannot create a valid `STOP` decision.

## References

- ISO. [ISO 8586:2023](https://www.iso.org/standard/76667.html).
- ISO. [ISO 11132:2021](https://www.iso.org/standard/76669.html).
- ISO. [ISO 13299:2016](https://www.iso.org/standard/58042.html).
- ISO. [ISO 8589:2007](https://www.iso.org/standard/36385.html).
- ISO. [ISO 5495:2005](https://www.iso.org/standard/31621.html).
- Barkat S, et al. [Odor expertise induces configural perception of odor mixtures](https://pubmed.ncbi.nlm.nih.gov/21873604/). 2012.
- Morquecho-Campos P, et al. [Odor identification is trainable](https://academic.oup.com/chemse/article/44/3/197/5306142). 2019.
- Laor Y, et al. [Sensory analysis of odors with a trained panel](https://pubmed.ncbi.nlm.nih.gov/22263423/). 2011.
- Latreille J, et al. [Measurement of the reliability of sensory panel performances](https://www.sciencedirect.com/science/article/pii/S0950329305000704). 2006.
- Green BG, et al. [Evaluating the labeled magnitude scale](https://doi.org/10.1093/chemse/21.3.323). 1996.
- Pellegrino R, et al. [Odors smell like their components](https://pmc.ncbi.nlm.nih.gov/articles/PMC13371102/). 2026 preprint.
