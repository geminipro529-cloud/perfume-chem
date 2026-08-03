# Build D0 Scientific Claim Matrix Design

**Status:** SOL-APPROVED FOR D0 IMPLEMENTATION

**Scope:** Build D0 only. This design does not begin D1, authorize a study,
authorize sample preparation, alter a database, or grant scientific release.
The user's standing delegation assigns design approval and review to Sol, so no
additional permission prompt is required.

## Authority and preserved baseline

The governing Build D contract is
`D:\.prompts\perfume chem\SOL_5_6_PERFUME_CHEM_MASTER_A_D_PROMPT.md`, SHA-256
`7050f2e77160e9039241e8925f844beb3d32374ad075742fe958518ac0eca349`.
Its D0 exit gate requires the first claim, comparator, endpoint, margin,
assessor population, and required evidence to be defined before study-design
code is finalized.

The prewrite repository boundary is:

- branch `codex/add-inventory-materials`;
- HEAD `b8cd0cbba47792624ba73b41327d193f30f0bb66`;
- 1,782 status entries and zero staged entries;
- normalized status SHA-256
  `4487309377de170c3dc1edf71022f16133806be81f142c305fa894e14efdf532`;
- no existing `engine/scientific_validation`, `engine/validation`, or
  `engine/studies` package.

All 429 non-runtime dirty or untracked paths plus three existing clean D0
targets were preserved in the path-preserving archive
`D:\.backups\perfume-chem\build-d0-prewrite-20260803T115425+0700.tar`.
The 118,281,728-byte archive has SHA-256
`a94928628805538cf34138de92bb0dda4886f3d1216b934057e9ed4138ee76b2`.
The archive verifier reported zero unsafe members, duplicate members, content
mismatches, or current-work mismatches. An actual extraction to the short
Windows restore root `D:\.backups\perfume-chem\d0rv-20260803T115425`
restored all 432 manifest files with zero byte mismatches. A first diagnostic
extraction under a much longer scratch path missed two deeply nested files due
to the Windows path-length boundary; extracting the identical archive at the
short recovery root proved that the archive itself is intact and restorable.

The authoritative checkout is intentionally not moved to a clean worktree.
A clean worktree would omit the preserved 1,782-entry overlay that this task is
required to treat as authoritative. D0 writes will instead remain narrowly
scoped, staged by exact path, and checked against the preserved status digest.

DeepLuna Fast job `DS-8b6743b373d10da24e2b71bd5331dcfe` performed a
bounded mechanical prewrite review. Sol independently verified its findings:
B7 is append-only and cannot convey release authority; C9 requires a passing
exact-scope Build D receipt; C10 excludes legacy numeric/planning authority;
the legacy sensory/planner/release modules are not Build D authority; and both
candidate Prada formula documents are stale and quarantined.

## Decision and alternatives

### Selected: a pure Build D authority package

Create `engine/scientific_validation` as a pure Python package containing
immutable D0 contracts, the complete claim-family registry, method-alignment
rules, and a factory for the first planning claim. The package accepts explicit
version bindings and produces canonical hashes. It performs no filesystem,
database, network, clock, random, environment, or release mutation.

This boundary is selected because Build D needs a new scientific-study
authority layer without changing the semantics of B7 or inheriting legacy
assumptions. Later D phases may add append-only persistence and protocol
objects around these contracts, but D0 does not pre-implement them.

### Rejected: extend the B7 database authority layer

B7 records claim-specific decisions from canonical B1-B6 evidence and has a
database constraint forcing `release_authority = 0`. Extending it for sensory
study planning would blur existing authority, require premature persistence
and migration decisions, and risk making a B7 row appear to authorize a study
or release. D0 may reference B7 evidence identifiers, but it does not mutate or
reinterpret B7.

### Rejected: promote the legacy sensory/planner/release stack

`engine/sensory/ledger.py`, `engine/experiments/planner.py`, and
`engine/release_readiness.py` are compatibility or legacy surfaces. The first
two use ambient random codes, and the planner accepts caller-declared sensory
values without preregistration or authority. They remain quarantined from D0.
No D0 implementation imports or edits them.

### Rejected: a data-only JSON registry

A JSON-only registry would not enforce immutability, method compatibility,
canonical version hashing, or fail-closed construction. JSON will be an export
form, not the source of executable invariants.

## Package boundary

### `engine/scientific_validation/contracts.py`

This module owns:

- `ClaimFamily`, with exactly the 17 master-prompt families;
- `ValidationMethodFamily`;
- `ClaimAuthorityState`;
- `AssessorType`, `BindingState`, `MarginAuthority`, and `EndpointRole`;
- immutable `VersionBinding`, `ScopeValue`, `ClaimScope`,
  `ComparatorDefinition`, `DecisionCriterion`, `EndpointDefinition`,
  `EvidenceRequirement`, and `ClaimDefinition` dataclasses;
- deterministic canonical JSON and SHA-256 functions.

All identifiers are non-empty, versions are positive integers, hashes are
lowercase 64-character SHA-256 values, tuple collections are unique, and
`REQUIRED_UNBOUND` scope values carry an explicit reason but no fabricated
value. Decimal margins serialize as strings. A claim cannot carry release
authority.

### `engine/scientific_validation/claim_registry.py`

This module owns immutable `ClaimFamilyPolicy` records and the canonical
registry. Every family declares the method families that can provide its
primary authority and the shortcuts that cannot. The module validates that a
claim's primary endpoint is method-compatible with its family.

### `engine/scientific_validation/first_claim.py`

This module owns a pure factory for claim
`D0-PRADA-ORRIS-INTERVENTION-001`, version 1. The caller supplies exact control
and intervention `VersionBinding` objects. The factory contains no file reads
and cannot silently rebind a formula after its hash changes.

### `engine/scientific_validation/__init__.py`

This module exposes only the supported D0 public API. No legacy planner or
release-readiness object is re-exported.

## Canonical claim-family matrix

The registry contains all 17 families below. “Primary authority” means a
method family capable of supporting that claim; it does not mean evidence
already exists.

| Claim family | Primary authority method families | Explicitly insufficient shortcut |
|---|---|---|
| Exact bottle arithmetic | deterministic arithmetic verification | sensory testing |
| Event replay | deterministic event-stream replay | assessor recollection |
| Analytical identity | analytical identity measurement | odour description alone |
| Analytical quantity | validated analytical quantitation | liking or intensity rating |
| Equilibrium headspace prediction | held-out headspace benchmark; analytical quantitation | in-sample model fit |
| Physical release trajectory | held-out physical-release benchmark; analytical quantitation | equilibrium-only output |
| Above-threshold screening | contextual threshold screening with qualified inputs | raw concentration alone |
| Perceptible difference | sensory discrimination or directional paired comparison | model score alone |
| Sensory similarity/equivalence | trained quantitative descriptive profile | discrimination non-significance |
| Descriptive-profile accuracy | trained quantitative descriptive profile | consumer liking |
| Temporal-profile accuracy | repeated temporal intensity profile | one static endpoint |
| Reconstruction similarity | trained descriptive profile; sensomics recombination where claimed | formula arithmetic |
| Intervention effectiveness | trained quantitative descriptive profile | unblinded anecdote |
| Protected-attribute preservation | trained quantitative descriptive equivalence | “no significant difference” |
| Preference/liking prediction | controlled consumer hedonic evaluation | trained-panel intensity |
| Longevity or projection proxy | temporal intensity profile; held-out physical-release benchmark | equilibrium headspace alone |
| Regulatory screening | current rule/evidence review | sensory or model prediction |

The registry fails closed for the three master-prompt category errors:
sensory methods cannot revalidate exact arithmetic, analytical concentration
cannot prove liking, and discrimination cannot prove descriptive equivalence.

## First confirmatory claim

### Claim statement

The planning claim is:

> Under one locked hydroalcoholic matrix, standardized blotter application,
> controlled evaluation condition, and a 30-minute post-application endpoint,
> the Prada Luxury Orris intervention increases trained-panel iris/orris
> intensity relative to the Prada Architecture Control by the prespecified
> minimum effect while preserving clean pressed-shirt/soapy character,
> wood-amber structure, and dryness/balance within prespecified equivalence
> margins.

This is a question to test, not a result. Its primary family is
`INTERVENTION_EFFECTIVENESS`; the protected secondary endpoints are governed
by `PROTECTED_ATTRIBUTE_PRESERVATION` policy.

### Comparator and claimant versions

The planning comparator is
`formulas/Prada_LHomme_Architecture_Control_30mL_EdT.md`, current authoritative
overlay SHA-256
`151de70b2983a7902a67daf8ddd43e0692bfea4ee5f8c92e553c3174827e1d00`.
The intervention is
`formulas/Prada_LHomme_Luxury_Orris_30mL_EdT.md`, current authoritative overlay
SHA-256
`c05661384d53c27aa7a50b50e14e62cf245ee5aa8d3974e0829a56f873d5eb4d`.
The software planning version is repository HEAD
`b8cd0cbba47792624ba73b41327d193f30f0bb66` plus the D0 claim-definition
version created from this design.

Both formula documents explicitly say `QUARANTINED — do not mix or release`.
The control artifact is stale and stock-blocked. The intervention artifact is
stale, and the Orris Liquid carrier is unrecorded. These hashes identify the
planning inputs only; they do not authorize those bytes as study samples.
Any formula-byte change supersedes claim version 1 and requires a new claim
version before D1 locking.

### Assessor population and method

The assessor population is a trained quantitative descriptive panel whose
members later pass the D3 selection, training, discrimination, agreement, and
repeatability gates. Individual scores and a common anchored attribute lexicon
are required. Consumer participants are outside this first claim.

The primary authority method is replicated quantitative descriptive profiling.
A directional paired comparison may be supportive in a later protocol, but it
cannot supply the primary magnitude estimate: ISO 5495 states that paired
comparison can establish direction for an attribute but not the extent of the
difference. The design uses the current published ISO 8586:2023 assessor
selection/training page, ISO 11132:2021 panel-performance page, ISO 13299:2016
profiling page, and ISO 20784:2021 claim-substantiation page as public guidance.
It makes no claim of ISO compliance because the complete standards and an
implemented locked protocol have not been verified.

Official references checked on 2026-08-03:

- https://www.iso.org/standard/76667.html
- https://www.iso.org/standard/76669.html
- https://www.iso.org/standard/58042.html
- https://www.iso.org/standard/31621.html
- https://www.iso.org/standard/69080.html

### Endpoints and provisional margins

The primary endpoint is the model-adjusted paired mean difference
`Luxury Orris - Control` in iris/orris intensity at 30 minutes on a locked
0-to-10 anchored scale.

The planning minimum-effect margin is `+0.50` scale points. The primary outcome
is:

- **success** when the two-sided 95% confidence interval lies wholly at or
  above `+0.50`;
- **failure** when the interval lies wholly at or below `0.00`;
- **inconclusive** otherwise.

The three protected endpoints use the same locked scale and direction
`Luxury Orris - Control`:

1. clean pressed-shirt/soapy character;
2. wood-amber structure;
3. dryness/balance.

Each planning equivalence margin is `[-0.75, +0.75]` scale points. Protected
preservation succeeds only when multiplicity-controlled two-one-sided
equivalence intervals lie wholly within that band. It fails only when an
interval lies wholly beyond either equivalence boundary; all overlapping cases
are inconclusive. Overall claim success requires primary success and all three
protected successes. Overall failure requires primary failure or any protected
failure. Every other pattern is inconclusive.

The `0.50` and `0.75` values have
`MarginAuthority.PROVISIONAL_PREPILOT`. They are concrete planning constants,
not empirically justified sensory facts. D6 and D7 must independently assess
panel repeatability, practical relevance, power, and feasibility. If those
phases do not ratify the values, claim version 1 is superseded and a new claim
version must be locked before confirmatory data collection. Outcome data can
never be used to revise the margins.

### Scope state

The following are defined now:

- product family: Prada L'Homme architecture research study;
- formula roles: exact control and luxury-orris intervention bindings;
- assessor type: trained quantitative descriptive panel;
- substrate: standardized fragrance blotter;
- evaluation time: 30 minutes post-application;
- primary and protected attributes;
- comparison direction and decision margins.

The following are mandatory `REQUIRED_UNBOUND` scope values, not placeholders:

- regenerated formula/build identifiers;
- exact control and intervention lots;
- common final concentration and hydroalcoholic matrix;
- stock carrier, basis, density, and safety identity, including Orris Liquid;
- bottle/sample preparation records;
- exact application dose and environmental condition;
- qualified assessor roster and panel-performance receipt;
- randomization, blinding, session, and carryover records.

Any unbound required scope keeps `study_authorized = false`.

### Required evidence

The claim cannot advance beyond planning without all of the following:

1. regenerated and revalidated formula artifacts bound to exact hashes;
2. exact ingredient and stock-lot identity, basis, carrier, density, and
   concentration records;
3. actual-dose safety and regulatory screening appropriate to the study;
4. locked common matrix, concentration, substrate, dose, maturation, storage,
   and environmental conditions;
5. assessor consent/ethics/privacy clearance and a qualified trained-panel
   performance receipt;
6. a pilot dataset kept separate from confirmatory observations;
7. a prespecified margin and power rationale ratified before outcome access;
8. immutable protocol, sample, prediction, randomization, and analysis locks;
9. blinded, randomized, replicated, append-only confirmatory observations;
10. a locked analysis with effect sizes, intervals, deviations, and explicit
    pass/fail/inconclusive output;
11. analytical or safety evidence wherever the final scoped wording requires
    it;
12. authorized human review and a scoped release decision.

No item can be synthesized from a model prediction or an agent statement.

## Authority, transitions, and revalidation

Claim version 1 starts in `ClaimAuthorityState.PLANNING_ONLY` with
`release_authority = false`, `study_authorized = false`, and
`observed_outcome = unmeasured`. D0 code has no transition that can mark it
supported, validated, or released.

At minimum, a new claim version or revalidation is required by any change to:

- claimant formula, software, model, or canonical serialization hash;
- target, comparator, formula build, ingredient lot, bottle, matrix, substrate,
  dose, maturation, storage, or condition;
- assessor population, screening, training, lexicon, performance standard, or
  panel composition;
- endpoint, attribute definition, scale, time point, margin, decision rule,
  sample-size rationale, exclusion rule, or analysis;
- randomization, blinding, carryover, or data-lock procedure;
- analytical, safety, regulatory, or adverse-event evidence;
- a major/critical deviation, contradictory study, or evidence expiration.

History is append-only. Superseded, failed, and inconclusive versions remain
visible and cannot be overwritten by a later result.

## Error handling and determinism

Construction fails closed for malformed IDs, nonpositive versions, invalid
hashes, duplicate endpoints/evidence requirements, an unbound value without a
reason, a bound value without a value, nonpositive margins, unsupported method
families, empty criteria, or any claim carrying release authority.

Canonical hashes depend only on normalized contract data. They do not depend
on dict insertion order, filesystem order, locale, clock, environment, random
state, process identity, or Python object repr. Unknown facts remain explicit
unknowns and are never converted to empty strings or zero.

## D0 test and evidence gate

D0 implementation must prove:

1. the registry contains exactly the 17 required families and no aliases;
2. every family has an executable method policy;
3. the three category-error examples fail closed;
4. contracts are immutable and canonical hashes are deterministic;
5. invalid IDs, hashes, versions, margins, bindings, and duplicates fail;
6. the first claim has the exact comparator, endpoint, provisional margins,
   assessor population, evidence list, and revalidation triggers above;
7. current formula receipts match the recorded planning hashes and remain
   quarantined;
8. the first claim cannot authorize a study or release;
9. no D1 object, database migration, legacy planner edit, sample record,
   assessor, observation, or scientific result is created;
10. focused tests, scoped lint/type checks, status preservation, and an
    independent bounded DeepLuna Fast audit are recorded.

D0 passes as a **software planning gate** when these contracts are executable
and the master-prompt exit fields are all present. The scientific claim remains
unmeasured, the formulas remain quarantined, and physical study execution
remains blocked until later Build D gates provide real authority.

## Explicit D0 exclusions

D0 does not:

- create or migrate a database;
- finalize a D1 protocol or preregistration;
- generate randomization codes or schedules;
- create people, consent, samples, lots, sessions, observations, or outcomes;
- mix, regenerate, mutate, or release either formula;
- calculate sample size or claim the provisional margins are validated;
- issue a C9 passing receipt;
- upgrade B7 authority;
- claim ISO compliance, equivalence, improvement, preference, safety, or
  scientific release.
