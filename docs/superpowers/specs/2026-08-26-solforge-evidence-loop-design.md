# SolForge Evidence Loop Design

**Date:** 2026-08-26

**Status:** design approved in chat; implementation not yet authorized by written-spec review

**Scope:** replace the prompt-module complexity ensemble with one evidence-producing
decision loop around Sol xhigh

**Authority ceiling:** analysis and experiment design only. Formula mutation,
compounding, inventory reservation, sensory truth, safety clearance, purchase,
publication, and release remain separately authorized.

## 1. Purpose

SolForge will make Perfume-Chem better than plain Sol xhigh as a working system,
not by adding more advisory prose, but by turning Sol's aesthetic hypotheses into
controlled, reproducible, evidence-producing decisions.

Sol remains the creative head perfumer and proposes target-faithful hypotheses.
Deterministic Perfume-Chem code owns:

- source, target, formula, inventory, and stock-lineage identity;
- ideal-versus-current-inventory separation;
- zero-change and experimental-design legality;
- physical-execution boundaries;
- blinded temporal evidence completeness;
- criterion-specific preference learning;
- authority and promotion gates; and
- reproducible benchmark receipts.

The system does not calculate a universal complexity or beauty score. In this
program, complexity means target-linked perceptual depth, coherent richness,
relations, transitions, texture, restraint, and hedonic potential. A sparse
formula may be richer than a long formula when every material has a precise,
nonredundant role.

## 2. Problem Statement

The current complexity work is organized as independently callable modules and
prompt packets. Fresh benchmarking showed that this organization can make Sol
xhigh worse: modules can add plausible but uncontrolled interventions, confuse
supporting ingredients with primary identity, and reward action when `NO_CHANGE`
is correct.

The strongest current pieces are not competing perfumers. They are narrower
deterministic capabilities:

- `engine/perception/architectural_delta.py` can validate controlled deltas;
- `engine/sensory/ledger.py` can validate observed temporal evidence; and
- `engine/preference.py` can learn scoped pairwise preference.

They should become consecutive stages in one decision loop. The old module
committee must become unreachable from production orchestration.

## 3. Goals

1. Produce zero or one target-faithful, nonredundant experiment at a time.
2. Make `NO_CHANGE` a successful first-class result.
3. Permit n-ary work only through complete, focused interaction designs.
4. Reparse the authoritative V5 inventory for each run and preserve exact stock
   lineage.
5. Keep target/ideal architecture independent from the current-inventory build.
6. Store only physical observations as sensory evidence.
7. Learn target fidelity, depth, richness, temporal coherence, and liking as
   separate criteria.
8. Turn missing scientific support into a traceable literature-research queue.
9. Improve over plain Sol xhigh in critical-error rate, experimental validity,
   evidence efficiency, and target usefulness.
10. Preserve every failed predecessor as a provenance tombstone without making
    it runtime reachable.

## 4. Non-goals

SolForge will not:

- autonomously compound, purchase, reserve stock, or release a perfume;
- convert OAV, vapor pressure, predicted volatility, formula frequency, supplier
  copy, prestige, novelty, or price into liking or perceived contribution;
- infer sensory observations from formula composition;
- treat a literature citation as proof that a formula is beautiful or liked;
- expose retired complexity modules as independent runtime advisers;
- train a global universal beauty model;
- rewrite frozen registry, benchmark, source, or package bytes; or
- add a second formula, inventory, laboratory, or safety authority system.

## 5. Architectural Choice

The selected design is an evidence loop around Sol xhigh.

The rejected alternatives are:

1. A prompt-module committee. It is easy to assemble but duplicates reasoning,
   encourages interventions, and has already produced critical experimental
   errors.
2. A fully deterministic perfumer. It is reproducible but cannot legitimately
   replace high-level aesthetic judgment with the current evidence base.

The selected architecture keeps creative and deterministic responsibilities
separate:

```text
Research evidence ───────────────────────────────┐
                                                 v
A. AIM & AUTHORITY -> B1. SOL HYPOTHESES -> B2. EXPERIMENT COMPILER
        ^                                             |
        |                                             v
D2. GOVERNOR <- D1. SCOPED LEARNER <- C2. SENSORY LEDGER
        ^                                             ^
        |                                             |
        └──────── C1. LAB PLAN / PHYSICAL RECEIPT ────┘
```

## 6. Runtime Modes

The public orchestrator supports five explicit modes:

| Mode | Purpose | Maximum result |
|---|---|---|
| `ANALYZE` | Build a canonical case and identify evidence gaps | `ANALYSIS_ONLY` |
| `DESIGN_EXPERIMENT` | Compile zero/one delta or a complete interaction design | `EXPERIMENT_READY` |
| `RECORD_OBSERVATION` | Validate and summarize physical sensory cells | `OBSERVED_UNVALIDATED` |
| `LEARN_PREFERENCE` | Fit one declared criterion from valid comparisons | `DIAGNOSTIC` or `VALIDATED_EXACT_SCOPE` |
| `PROMOTE` | Apply software/model governance to a frozen candidate | `RUNTIME_ADMITTED` |

No mode implies the authority of a later mode. `EXPERIMENT_READY` does not
permit compounding. `VALIDATED_EXACT_SCOPE` does not permit formula release.

## 7. Typed Contracts

All cross-component and cross-environment communication uses canonical JSON.
Canonicalization sorts object keys, preserves list order, rejects non-finite
numbers, encodes UTF-8, and terminates with one newline before SHA-256 hashing.

### 7.1 `SolForgeCaseV1`

Required fields:

- `case_id` and `created_at`;
- `target_identity` and `forbidden_drift`;
- `target_ideal_ref` and `target_ideal_sha256`;
- optional `current_build_ref` and `current_build_sha256`;
- `inventory_authority_ref`, workbook SHA-256, and refresh time;
- stock-basis and formula-dose receipt references when a build exists;
- source/evidence references and hashes;
- declared criteria and claim ceiling;
- known physical observations, represented only by evidence references; and
- unresolved conflicts, missing evidence, and explicit blockers.

The target is defined before inventory mapping. A missing current build is
allowed. An unresolved authority conflict produces `HOLD`.

### 7.2 `SolHypothesisSetV1`

Sol's output is data, not authority. It contains:

- exact model identity and reasoning setting;
- exact input-envelope SHA-256;
- zero or more candidate hypotheses;
- an explicit `NO_CHANGE` hypothesis;
- target-linked purpose and predicted failure mode per hypothesis;
- affected formula lines or target functions;
- requested intervention kind;
- uncertainty and missing-evidence statements; and
- no asserted physical, sensory, safety, purchase, or release result.

The system rejects unknown fields, missing `NO_CHANGE`, unbound formula
references, and model-output text that cannot be parsed into the closed schema.

### 7.3 `CompiledExperimentV1`

The deterministic compiler returns:

- `NO_CHANGE`, `PROPOSED`, or `HOLD`;
- zero or one selected intervention;
- intervention kind: `OMISSION`, `ADDITION`, `RATIO`, or `NARY_DESIGN`;
- target/ideal and current-inventory representations kept separately;
- controlled arms with exact formula/build references;
- isolated factors and constant-total constraints;
- inventory status per required material;
- blockers, omission loss, expected failure mode, and next comparison;
- all input, policy, inventory, and output hashes; and
- false authority flags.

For a two-factor interaction hypothesis A x B, the minimal valid core is:

- reference or null;
- A only;
- B only; and
- A+B.

Additional factors cannot appear in those arms. If another factor is relevant,
it must be a separately declared block or a new complete design. Pairwise
evidence cannot establish three-way or layered synergy.

### 7.4 `ExecutionReceiptV1`

Physical execution remains in the backend laboratory domain. The receipt binds:

- approved immutable build-plan version;
- inventory reservation events;
- ExactStockRef values;
- planned and measured raw/active quantities;
- operator confirmations;
- sample/blind codes;
- deviations and incidents; and
- parent experiment SHA-256.

No engine-side result can fabricate this receipt.

### 7.5 `TemporalEvidencePacketV1`

This packet binds protocol, sample, assessor, repeat, timepoint, endpoint,
presentation sequence, schedule hash, apparatus qualification, safety events,
and execution receipt.

Canonical cell identity is:

```text
(protocol, sample, assessor, repeat, timepoint, endpoint)
```

Missing cells remain missing. Duplicate cells, schedule mismatch, order
confounding, unqualified within-sniff timing, unsafe exposure, or failed declared
repeatability produce `HOLD`.

### 7.6 `CriterionFitPacketV1`

One packet fits exactly one criterion and protocol scope. Supported initial
criteria are:

- `TARGET_FIDELITY`;
- `DEPTH`;
- `RICHNESS`;
- `LIKING`.

The packet includes utilities and intervals, ties, assessor-cluster bootstrap
method and seed, heterogeneity, order diagnostics, held-out baseline, connected
comparison graph status, and deterministic next-pair recommendation.

Criteria are never combined into an overall beauty or complexity score.

### 7.7 `DecisionReceiptV1`

The governor records:

- exact case and evidence hashes;
- state and blockers;
- accepted findings at their exact scope;
- rejected or unresolved claims;
- recommended next operation;
- authority flags; and
- runtime/admission provenance, required in `PROMOTE` mode and forbidden in all
  other modes.

## 8. Components and Responsibilities

### 8.1 SolForge orchestrator

A new `engine/solforge/` package will own only orchestration and contracts:

- `contracts.py` — closed typed packets and canonical hashing;
- `orchestrator.py` — mode transitions and stage composition;
- `research.py` — literature-gap and evidence-record contracts;
- `governance.py` — state, authority, and promotion rules; and
- `adapters.py` — narrow adapters to existing engine capabilities.

It will not contain formula heuristics, a new optimizer, a new sensory model, or
a new inventory parser.

### 8.2 Architectural Delta Engine

`engine/perception/architectural_delta.py` becomes an internal experiment
compiler. Its required changes are:

- accept `SolForgeCaseV1` and `SolHypothesisSetV1` through an adapter;
- rank `NO_CHANGE` alongside interventions;
- reject multiple unrelated factors in an n-ary design;
- bind every arm to target, formula, inventory, and policy hashes;
- produce deterministic tie-breaking; and
- remain unable to mutate a formula or authorize execution.

Internal target-first policy includes:

- zero citrus is valid;
- primary citrus follows target identity;
- Neroli 10% is support-only unless neroli/orange blossom is central;
- zero or one precise musk is the default;
- musk layering requires distinct target-linked functions and nonredundancy
  evidence;
- Habanolide and Romandolide follow refreshed exact inventory;
- Ambrettolide 10% may be design-available while procurement is pending;
- Ethylene Brassylate remains missing unless refreshed authority proves
  otherwise; and
- Tonalide, Macrolide, and Musk Ketone remain exception-only.

These are compiler policies, not standalone intelligence modules.

### 8.3 Temporal Sensory Ledger

`engine/sensory/ledger.py` remains the observed-evidence analyzer. It will:

- hydrate canonical cells from existing backend observation/comparison context;
- validate execution and protocol bindings;
- report counts, medians, dispersion, disagreement, order balance, transitions,
  repeatability, and next discriminator;
- preserve missingness and ties; and
- reject predicted volatility as sensory evidence.

The older `SensoryTrial` compatibility API remains available but does not become
a second persistence layer.

### 8.4 Preference Learner

`engine/preference.py` remains the scoped learner. It will:

- preserve the existing three-argument `PairwisePreference` constructor;
- consume validated comparison context through an adapter;
- fit one criterion per request;
- use deterministic assessor-cluster bootstrap when identities exist;
- keep ties as indifference evidence but outside directional fitting;
- withhold sparse, disconnected, unscoped, order-confounded, or baseline-failing
  fits; and
- recommend the most informative next pair deterministically.

### 8.5 Backend laboratory boundary

The backend remains independent of the root `engine/` environment. It will not
import `engine.solforge`.

Integration uses canonical JSON packets and existing domain services:

- `lab_assistant.py` routes intents and describes the required SolForge mode;
- laboratory planning persists target, inventory mapping, build plans, and
  evidence links;
- laboratory execution persists reservations, actions, measurements, and
  receipts; and
- existing observation and pairwise-comparison context fields carry protocol
  metadata without a new database migration in the first vertical slice.

The backend validates packet schema and hash references before linking them to
an immutable plan. It cannot silently reinterpret engine output.

### 8.6 Existing command surface

The initial command-line integration extends
`scripts/intervention_recommend.py` rather than adding a new pipeline script.
The command accepts canonical case and hypothesis JSON and emits a
`DecisionReceiptV1` plus referenced stage packets. It performs no network call
and no physical mutation.

A live model adapter is excluded from the Gate Foundation and SolForge Vertical
Slice subprojects. It can be designed in Scientific Maturation and Admission
only after the deterministic slice is accepted. Until then, Sol hypothesis
packets are externally generated and hash-bound.

## 9. Mandatory OAV and Hedonic Gate Rebuild

The preimplementation audit found that the existing tests enforce useful
authority labels but do not make the current scoring scientifically valid.
Twenty focused OAV, release-scoring, and preference tests pass when pytest uses a
clean temporary directory. The structural audit nevertheless identifies
mandatory replacement work:

- `engine/hedonic_model.py` assigns fixed material valences and calculates a
  formula pleasantness/harmony score without formula-specific blinded liking
  evidence;
- `engine/optimizer/scoring.py` imports that score as an optimization axis;
- `engine/pipeline/release_scoring.py` carries the optimizer output into unified
  release diagnostics, even though its provenance correctly labels the numbers
  heuristic and non-authoritative;
- OAV diagnostics use aggregate OAV-derived indices and an authority rank that
  can reward the number of perceptible materials; and
- strict OAV currently abstains while modeled quantities can still produce a
  `PASS`, `WARN`, or `FAIL` primary status.

These systems are therefore unsuitable as SolForge hedonic or sensory gates.
SolForge integration is blocked until versioned replacements pass the contracts
below.

### 9.1 OAV Evidence Gate V2

The replacement OAV gate reports evidence state rather than a 0-100 authority
rank:

- `STRICT_MEASURED` — exact dose/stock lineage, measured headspace at declared
  conditions, applicable measured or peer-reviewed threshold, and complete
  units/provenance;
- `MODELED_SCREEN` — exact dose basis with explicitly modeled headspace or
  activity;
- `PARTIAL` — one or more required values are derived, transferred, or missing;
- `ABSTAINED` — the gate cannot compute an applicable OAV; and
- `INVALID` — units, stock basis, formula binding, natural/preblend handling, or
  source lineage is contradictory.

Every material row binds:

- ExactStockRef and active-dose receipt;
- material identity, supplied strength, carrier, density, active mass, and
  formula matrix;
- air or solution concentration with explicit units and context;
- ODT value, units, measurement method, medium, population, temperature when
  known, and source;
- vapor-pressure/activity/headspace source and uncertainty;
- natural-mixture or opaque-preblend treatment; and
- `MEASURED`, `MODELED`, `TRANSFERRED`, or `UNKNOWN` classification for every
  quantitative field.

The V2 gate enforces these firewalls:

- OAV is reported per material or validated constituent system; OAV values are
  not summed into total odor, percent contribution, balance, diffusion, impact,
  liking, or beauty;
- `OAV >= 1` is a threshold-screening result only in the declared measurement or
  model context, not proof that a material is recognizable in the mixture;
- unknown ODT or headspace remains unknown and is never coerced to zero;
- modeled temporal OAV is a prediction screen and never an observed transition;
- composite natural calculations preserve the natural as one formula row and
  expose constituent uncertainty internally;
- count of perceptible materials never increases evidence authority; and
- mixture synergy, masking, suppression, and hedonism require separate physical
  evidence.

The existing `engine/pipeline/oav_authority.py` remains a compatibility surface
until consumers migrate. SolForge and the release command use the V2 evidence
contract only.

### 9.2 Hedonic Evidence Gate V2

The replacement hedonic gate accepts only validated `LIKING` observations and
preference fits. Its states are:

- `NOT_TESTED`;
- `INSUFFICIENT_EVIDENCE`;
- `DIAGNOSTIC`;
- `VALIDATED_EXACT_SCOPE`;
- `FAILED_HELDOUT_BASELINE`; and
- `INVALID_OR_CONFOUNDED`.

There is no default neutral score. Missing evidence returns `NOT_TESTED`, not
50. The gate binds exact samples, formula/build hashes, protocol, assessors,
repeats, order, timepoint, criterion, ties, safety events, model configuration,
bootstrap seed, and held-out baseline.

Individual-owner, trained-panel, and consumer-population results are different
scopes. None may be generalized to another. Literature or molecular descriptors
may define a prior or research question, but cannot supply a formula liking
observation.

The legacy `HEDONIC_VALENCE` table and `score_hedonic` result are reclassified as
`LEGACY_HEURISTIC_PROVENANCE`. They remain available for historical replay only
and are removed from active optimization, SolForge decisions, release status,
and purchase recommendations.

### 9.3 Release Evidence Gate V2

The release path is rebuilt as typed evidence axes rather than one aggregate
score.

Hard deterministic axes include:

- source and rights provenance;
- target/formula identity;
- inventory and ExactStockRef lineage;
- active-dose and stock-rebase equivalence;
- OAV evidence state and missing-data firewall;
- applicable safety/IFRA constraints;
- laboratory execution and deviation state;
- sensory protocol/evidence state; and
- hedonic evidence state.

Modeled performance, OAV distribution, topology, cost, novelty, luxury,
photorealism, and similar indices remain separately labeled diagnostics. They
cannot compensate for a failed hard axis and are not averaged into release,
hedonic, or beauty scores.

`scripts/formula_release_gate.py` migrates to a versioned release-evidence
payload. The legacy unified score payload may remain in an explicitly named
compatibility section, but the new status logic cannot read it.

Release authority remains false until all required hard axes pass at the exact
scope and the existing human review/release action occurs. A high modeled or
hedonic diagnostic can never authorize release.

### 9.4 Gate rebuild migration and verification

The implementation introduces versioned evidence modules and migrates callers
test-first. It does not silently reinterpret historical outputs.

Required migration checks include:

- repository-wide import and call census for the legacy hedonic score;
- optimizer behavior with no validated hedonic evidence;
- hard rejection of a numeric hedonic objective without a valid fit receipt;
- exact stock-strength, active-dose, carrier, and natural-composite cases;
- unit and context mismatch cases for ODT and headspace;
- strict measured, modeled, partial, abstained, and invalid OAV cases;
- proof that perceptible count and aggregate OAV cannot improve authority;
- proof that OAV cannot produce liking, synergy, similarity, temporal-perception,
  or release claims;
- `NOT_TESTED` propagation through the optimizer and release gate;
- criterion-, assessor-, protocol-, and timepoint-specific hedonic validation;
- held-out baseline failure and order-confounding cases;
- compatibility replay of frozen legacy receipts; and
- release output containing no operative aggregate beauty or hedonic score.

The gate rebuild must pass before the SolForge four-case vertical slice begins.

## 10. Research Evidence Lane

Scientific research is a first-class but non-promoting lane.

An unsupported decision creates `EvidenceQuestionV1` with:

- exact unresolved claim;
- affected target/function/material scope;
- required evidence type;
- preferred study design and endpoint;
- result that would change software behavior;
- result that would not grant authority; and
- search status.

Literature becomes `ResearchEvidenceRecordV1` containing citation, stable
identifier, source URI, retrieval date, source hash when available, study type,
stimuli, population, apparatus, endpoints, result summary, limitations,
applicability, and rights/provenance.

Evidence is classified as:

| Class | Permitted use |
|---|---|
| `DIRECT_PERFUMERY_PSYCHOPHYSICS` | protocol or hypothesis support at matching scope |
| `GENERAL_OLFACTION_PSYCHOPHYSICS` | method support and cautious priors |
| `ADJACENT_FLAVOR_OR_PRODUCT_SENSORY` | method transfer only with stated limitation |
| `RECEPTOR_OR_IN_VITRO` | mechanistic hypothesis only |
| `PHYSICOCHEMICAL` | exposure/headspace or experiment selection only |
| `SUPPLIER_OR_TRADE_DESCRIPTION` | discovery metadata, never proof |

Initial research queues are:

1. mixture masking, suppression, enhancement, elemental/configural perception,
   and focused n-ary designs;
2. temporal olfactory perception, adaptation, washout, order, and within-sniff
   apparatus qualification;
3. assessor selection, training, repeatability, disagreement, and sensory-panel
   validity;
4. psychometric separation of fidelity, depth, richness, coherence, intensity,
   and liking;
5. paired-comparison models, assessor heterogeneity, order effects, and active
   next-pair selection;
6. citrus persistence and heart echoes;
7. amber/resin/incense architectures, including storax, benzoin, myrrh,
   frankincense, and olibanum;
8. soliflores and two-, three-, and four-flower interaction architectures;
9. sweet orris root and iris/rhizome differentiation;
10. target-linked specialist musk and wood-depth interactions; and
11. limits of OAV/headspace predictions as perceptual evidence.

Research may alter compiler policy, experiment priority, protocol design, or
uncertainty. Only valid physical evidence from the exact case may alter learned
preference or establish a formula-specific sensory result.

### 10.1 Initial verified methodological seeds

The first research ledger will include these source seeds, with full study-level
applicability and limitation extraction during implementation:

- Frank et al., component recognition and selective adaptation in odor mixtures:
  https://academic.oup.com/chemse/article/42/7/537/3876319
- Zak et al., mixture and concentration effects on receptor responses and human
  perception: https://doi.org/10.1093/chemse/bjaa032
- Labbé et al., Temporal Dominance of Sensations versus conventional profiling:
  https://doi.org/10.1016/j.foodqual.2008.10.001
- Zhou et al., within-sniff temporal discrimination using a qualified
  sniff-triggered apparatus: https://doi.org/10.1038/s41562-024-01984-8
- Arshamian et al., cross-cultural and individual variation in odor pleasantness:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11672226/
- Liu et al., pairwise hedonic odor assessment and test-retest design:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC7581750/
- NIST mixture-process experiment guidance:
  https://www.itl.nist.gov/div898/handbook/pri/section5/pri54.htm
- ISO 8586, ISO 13299, and ISO 11136 public standard metadata for assessor,
  descriptive-profile, and controlled hedonic methodology.

These seeds support research questions and protocol design. They do not validate
any specific perfume, material combination, target identity, or hedonic result.

## 11. Scientific Conclusion Programs

Every retained module is run as a bounded scientific program rather than frozen
at plausible advice. Each claim advances through this ladder:

1. `RESEARCH_MAPPED` — relevant literature, conflicts, applicability, and gaps
   are recorded;
2. `HYPOTHESIS_OPERATIONALIZED` — the claim has measurable endpoints, controls,
   failure criteria, and an exact scope;
3. `PROTOCOL_VALIDATED` — the apparatus, blinding, order, repeatability, and data
   contract can test the claim;
4. `OBSERVED_EFFECT` — the exact controlled comparison produced valid physical
   observations;
5. `REPLICATED_EXACT_SCOPE` — the effect repeated under the same declared scope;
6. `HEDONIC_PREDICTIVE_VALIDATED` — when the claim concerns liking, it predicts
   held-out blinded preferences above a declared baseline; and
7. `GENERALIZATION_TESTED` — optional transfer to a new formula, material family,
   protocol, or assessor population has been tested rather than assumed.

Each transition creates a hash-bound `ScientificConclusionReceiptV1` containing
the claim, scope, direct evidence, contrary evidence, inference, uncertainty,
failed tests, permitted use, and forbidden extrapolations. Skipping a ladder
stage is not allowed.

Hedonic conclusions have additional restrictions:

- only direct blinded `LIKING` comparisons count as liking evidence;
- target fidelity, depth, richness, intensity, familiarity, and technical
  elegance cannot substitute for liking;
- ties remain evidence of indifference;
- individual and panel-level conclusions are stored separately;
- personalization to the owner is not described as universal preference;
- order, intensity, adaptation, and assessor effects must be diagnosed;
- held-out performance must exceed the declared baseline; and
- literature can support a mechanism or protocol but cannot establish that a
  particular formula is liked.

The initial module programs are:

| Module/program | Scientific question | Required conclusion test |
|---|---|---|
| Architectural Delta | Does constrained one-delta selection produce more interpretable, target-faithful experiments than unconstrained advice? | blinded software cases followed by physical experiment-yield comparison |
| Temporal Ledger | Are depth, emergence, recurrence, and transition findings repeatable across assessors and sessions? | protocol-complete temporal observations with disagreement and repeatability bounds |
| Preference Learner | Can criterion-specific fits predict held-out owner or panel choices? | connected, order-balanced, assessor-scoped comparisons above baseline |
| Perceptual Topology | Do proposed relational features correspond to discriminable or repeatable perceptual structures? | controlled ratio/omission studies; no score-only promotion |
| Art Composition Topology | Do constant-total perturbations identify target-faithful structural windows? | blinded matched-total comparisons and replicated boundaries |
| Wood Depth | Which wood ratios and textures increase observed depth without darkness, volume, or material count acting as proxies? | target-matched ratio/omission trials with depth and liking kept separate |
| Citrus architecture | Which primary citrus and support echoes preserve the declared target into the heart? | target-specific citrus omission/alternative trials across timepoints |
| Musk architecture | When does one precise musk outperform layering, and when is a focused interaction real? | single-musks, omissions, and complete focused interaction designs |
| Floral/Orris architecture | Which soliflore and multi-flower relations create identity, depth, or richness rather than blur? | single, pair, and selected higher-order controlled designs, including sweet orris |
| Amber/resin/incense architecture | Which storax, benzoin, myrrh, frankincense/olibanum, balsamic, vanilla, labdanum, and wood relations create distinct amber types? | literature-grounded recognizers followed by ratio, omission, and temporal trials |

A program is retained only when it produces one of these outcomes:

- a validated constraint that prevents critical error;
- a more informative controlled experiment;
- a repeatable scoped sensory finding;
- a held-out predictive hedonic improvement; or
- a clearly documented negative result that prevents repeated waste.

If a module cannot reach `HYPOTHESIS_OPERATIONALIZED`, repeatedly fails its
protocol, or does not improve the SolForge system against plain Sol xhigh, it is
reclassified as `PROVENANCE_TOMBSTONE` or `RESEARCH_ONLY`. Its sources and
negative results remain preserved.

## 12. Registry and Runtime Governance

Historical registry bytes remain immutable.

A V3 capability/evidence overlay introduces these states:

- `PROVENANCE_TOMBSTONE`;
- `CATALOG_ONLY`;
- `RESEARCH_ONLY`;
- `DIAGNOSTIC_ONLY`;
- `EXPERIMENT_COMPILER`;
- `OBSERVATION_ANALYZER`;
- `LEARNER_DIAGNOSTIC`;
- `SHADOW_RUNTIME`; and
- `RUNTIME_ADMITTED`.

The old construction, expansion, citrus, musk, temporal, panel, admission, and
lifecycle cards remain source-visible but runtime-unreachable. Shared utilities
may remain importable by unrelated validated code.

The only new public capability is the SolForge orchestrator. It invokes internal
components according to registry state and mode. It rejects unregistered,
hash-drifted, tombstoned, or directly requested internal modules.

Perceptual Topology, Art Composition Topology, and Wood Depth remain advisory
feature extractors. They may contribute candidate features or experiment ideas
only after their own hashes and prerequisites are valid. They cannot mutate
formulas or claim sensory depth.

## 13. Failure Handling

Every stage fails closed.

| Condition | Required result |
|---|---|
| source, formula, inventory, or stock hash drift | `HOLD` |
| target/ideal missing or redefined by inventory | `HOLD` |
| unparseable or unknown-field Sol output | `HOLD` |
| no useful nonredundant intervention | `NO_CHANGE` |
| count-based complexity rationale | reject candidate |
| more than one unrelated first intervention | `HOLD` |
| incomplete or contaminated n-ary design | `HOLD` |
| missing physical execution receipt | no sensory promotion |
| duplicate/missing sensory cells | `HOLD` or `INCOMPLETE` |
| order imbalance or unqualified within-sniff data | `HOLD` |
| sparse/disconnected/confounded preference graph | `WITHHELD` |
| held-out result at or below baseline | `DIAGNOSTIC` |
| runtime registry/hash mismatch | runtime unreachable |
| model, prompt, or benchmark identity not frozen | benchmark invalid |

No exception path silently relaxes an authority boundary.

## 14. Benchmark Redesign

The former benchmark primarily compared prose responses. The new benchmark
isolates the value of deterministic orchestration.

For each case, one frozen Sol hypothesis output is reused across:

1. plain Sol interpretation with no compiler;
2. a length-matched/no-op control; and
3. the SolForge deterministic compiler and governor.

This prevents model-sampling differences from being mistaken for compiler
improvement.

### 14.1 Deterministic primary endpoints

- target/ideal versus inventory separation;
- exact inventory and stock-lineage handling;
- correct `NO_CHANGE`;
- zero/one intervention legality;
- complete focused interaction arms;
- no unrelated ingredient invention;
- missing-evidence and order-confounding holds;
- criterion isolation;
- false authority flags;
- stable canonical hashes and replay; and
- valid next-comparison selection.

All critical invariants must pass. A single authority escalation, uncontrolled
first experiment, invented stock fact, sensory fabrication, or contaminated
n-ary design is a critical failure.

### 14.2 Blinded secondary endpoints

Fresh projectless Sol xhigh judges compare target fidelity, experimental
usefulness, restraint, clarity, and evidence efficiency. Exact model identity,
reasoning setting, envelopes, outputs, scores, and hashes are frozen.

The software screen uses at least 12 balanced cases and confirmation uses at
least 12 unseen cases. Both sets include safe countercases, ingredient-count
traps, inventory mismatches, missing evidence, order confounding, citrus-free
targets, Neroli misuse, precise single-musks, focused musk interactions,
amber/resin cases, floral-combination cases, and unseen variants.

Admission requires:

- zero critical errors;
- 100% deterministic invariant compliance;
- at least 90% valid action or justified-withholding yield;
- no material regression against plain Sol on target fidelity;
- a positive median paired gain against plain and no-op controls on experimental
  usefulness; and
- reproducible receipts from a clean checkout.

Judge score alone cannot override a deterministic critical failure.

### 14.3 Prospective physical validation

Software admission permits shadow use only. Full runtime admission additionally
requires prospective blinded physical trials whose sample size, repeats,
assessors, washout, order balance, endpoints, and stopping rules are
preregistered. Sample size is justified by precision or power; the old three-case
screen is not physical validation.

Prospective outcomes include:

- interpretable-experiment yield;
- protocol completion and disagreement;
- target-fidelity and criterion-specific effects;
- no-change calibration;
- interval calibration and held-out prediction; and
- reduction in repeated or redundant experiments.

## 15. First Vertical Slice

The first implementation ends at shadow-mode decision receipts and contains four
cases:

1. a target requiring zero citrus and correct `NO_CHANGE`;
2. Neroli used only as a target-linked support bridge;
3. one precise musk with generic layering rejected; and
4. a focused Habanolide x Romandolide interaction with exactly the required
   isolated arms.

For each case the slice performs:

```text
case intake
-> exact V5 refresh
-> hypothesis packet validation
-> deterministic compile
-> backend-compatible experiment export
-> synthetic test-only execution/observation fixtures
-> temporal evidence validation
-> one-criterion preference fit
-> decision receipt and next comparison
```

Synthetic fixtures test software only and are always marked nonphysical. They
cannot promote sensory or hedonic claims.

The slice is complete when:

- all new focused tests pass;
- existing architectural-delta, temporal-ledger, preference, registry, and
  ensemble compatibility tests pass;
- canonical export/import replay is byte-stable;
- retired modules cannot be invoked through the orchestrator;
- every authority flag remains false;
- project verification passes at the appropriate scope; and
- shadow benchmark receipts are generated without a critical error.

## 16. Implementation Boundaries

This design is intentionally broader than one safe code change. It is executed
as three ordered implementation subprojects, each with its own detailed plan and
acceptance run:

1. **Gate Foundation** — rebuild OAV, hedonic, and release evidence gates and
   isolate legacy heuristic scoring;
2. **SolForge Vertical Slice** — implement contracts, orchestration, controlled
   experiments, sensory evidence, preference learning, registry isolation, and
   backend-compatible packets; and
3. **Scientific Maturation and Admission** — run the literature queues, module
   conclusion programs, prospective evidence, and final Sol xhigh comparisons.

Later subprojects cannot start by assuming an earlier one passed. They consume
hash-bound acceptance receipts. This avoids an oversized unreviewable change
while still defining the complete program in one architecture.

Across those subprojects, implementation is decomposed into independently
testable changes:

1. OAV Evidence Gate V2 and legacy compatibility;
2. Hedonic Evidence Gate V2 and removal of legacy hedonic optimization;
3. Release Evidence Gate V2 and CLI migration;
4. canonical SolForge contracts and hashing;
5. orchestrator state machine and adapters;
6. architectural-delta n-ary repair and compiler integration;
7. temporal-ledger packet adapter;
8. preference packet adapter and criterion extension;
9. research-evidence contracts and gap queue;
10. V3 registry overlay and runtime isolation;
11. backend-compatible packet validation/export without migration;
12. vertical-slice fixtures and integration tests;
13. deterministic and blinded shadow benchmark; and
14. governance receipt and Git/GitHub handoff after acceptance.

Each change uses test-driven development. Existing unrelated working-tree changes
must be preserved. No merge, push, runtime promotion, or deletion of failed
sources occurs until the relevant tests and review gates pass.

## 17. Verification Strategy

### Unit and property tests

- strict schemas, canonical hashes, unknown-field rejection, and round trips;
- strict/measured versus modeled/partial/abstained OAV evidence;
- absence of operative aggregate OAV, beauty, and hedonic scores;
- `NOT_TESTED` hedonic propagation and legacy-valence runtime isolation;
- authority conflicts and inventory drift;
- zero-change and count traps;
- redundant additions and target/inventory separation;
- all inventory states and exact-stock exceptions;
- Neroli and musk policies;
- focused two-factor and complete higher-order interaction designs;
- duplicate/missing/order-confounded sensory cells;
- repeatability, disagreement, safety events, and within-sniff qualification;
- criterion isolation, ties, bootstrap determinism, graph connectivity,
  heterogeneity, order bias, and baseline failure;
- orchestrator transition legality; and
- runtime isolation of tombstones and advisory modules.

### Integration tests

- case -> hypothesis -> compiler -> export;
- export -> backend-compatible validation -> execution receipt fixture;
- observation context -> temporal evidence;
- pairwise context -> criterion fit;
- complete end-to-end vertical-slice replay; and
- unchanged legacy constructors and existing valid call paths.

### Regression and project verification

- focused root-engine tests first;
- repository namespace disambiguation when root and backend `tests` conflict;
- backend lint, type check, and focused tests when backend files change;
- quick project verification during development;
- full project verification before merge or publication; and
- clean-checkout replay before admission.

## 18. Completion and Promotion

Implementation completion means the accepted design is present, tests and
verification pass at declared scope, the vertical slice runs end to end, and the
benchmark receipt truthfully records its result.

It does not automatically mean runtime admission. Promotion proceeds:

```text
NONRUNTIME -> SHADOW_RUNTIME -> PROSPECTIVE_VALIDATION -> RUNTIME_ADMITTED
```

Any critical error returns the candidate to runtime-unreachable state while
preserving source, outputs, hashes, and failure evidence.

GitHub integration occurs only from the isolated implementation branch after
local acceptance. The review contains the specification, plan, code, tests,
benchmark receipts, and explicit remaining physical-evidence holds. No raw chats,
secrets, protected stores, or unnecessary generated artifacts are pushed.

## 19. Design Acceptance Criteria

This design is ready for implementation planning when the user confirms:

- Sol remains the creative head and deterministic code remains the evidence
  governor;
- complexity is not reduced to ingredient count or one scalar score;
- research evidence is useful but non-promoting;
- retained modules run toward explicit scientific and hedonic conclusion
  receipts rather than remaining advisory indefinitely;
- the legacy hedonic score is runtime-ineligible and OAV/hedonic/release evidence
  gates are rebuilt before SolForge depends on them;
- first runtime work is the four-case shadow vertical slice;
- old failed modules stay as tombstones;
- backend and engine remain separate and communicate through typed packets; and
- GitHub promotion waits for verified software and benchmark evidence.
