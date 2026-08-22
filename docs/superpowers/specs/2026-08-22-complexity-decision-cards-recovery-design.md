# Complexity Decision Cards Recovery Design

- **Date:** 2026-08-22
- **Status:** Approved by the user
- **Repository:** `D:\chatbots\perfume-chem`
- **Predecessor decision:** `data/governance/complexity_xhigh_benchmark_CXB-20260822T144500Z-v2-7f31c0a2.json`
- **Control:** normal projectless ChatGPT 5.6 Sol Extra High with the same case evidence and no module card

## 1. Decision

The first combined complexity packet did not outperform normal ChatGPT xhigh.
It delivered three wins, two losses, eleven ties, and a zero median gain across
sixteen paired cases. The scientific engines remain preserved, but their large
raw prompt projections stay retired.

The recovery replaces those raw projections with ten compact, module-specific
decision cards. A card must change one consequential decision, expose the
decisive evidence or blocker, name the controlled comparison, and stop at its
claim ceiling. It must not summarize every field emitted by the native engine.

Complexity means identity-linked perceptual depth that creates richness and
supports hedonic potential. It does not mean complication. Exact simplicity,
restraint, omission, spacing, and negative space are valid routes to depth.
Ingredient count, module count, novelty, jargon, response length, formula
frequency, supplier copy, and modeled percentages are invalid proxies for
richness, beauty, liking, or hedonic success.

The registry remains retired while candidate cards are implemented and frozen.
Only a module that passes its individual unseen xhigh benchmark may be restored
to runtime eligibility. A failure is preserved as a recoverably retired module;
its source is not deleted.

## 2. Decision-card contract

Every card uses `complexity_decision_card_v1` and contains only:

1. `module_id` and `decision_kind`;
2. `state`: `DECIDE`, `HOLD`, or `NONE`;
3. `decision_question`: the one choice the model must resolve;
4. `decisive_evidence`: no more than three short, source-bound facts;
5. `preserve`: the target-linked feature that must survive;
6. `reject`: the most likely wrong move or unsupported inference;
7. `controlled_comparison`: the exact contrast needed to decide;
8. `claim_ceiling`; and
9. `source_result_sha256`, binding the card to the native result bytes.

A serialized card may not exceed 1,600 UTF-8 bytes. It may not contain raw
engine dumps, repeated authority booleans, an aggregate complexity score, an
overall beauty score, or a physical sensory conclusion. `HOLD` and `NONE` are
successful outputs when evidence or target fit does not justify intervention.

## 3. Ten module-specific cards

### 3.1 Construction complexity

The card identifies the single relation most responsible for target depth:
facet-to-facet contrast, foreground/background ownership, temporal handoff,
texture, or negative space. It states what must be preserved and what becomes
flatter, muddier, or less recognizable if that relation is lost. Raw material
counts and unavailable axes are omitted. When the native evidence cannot select
a relation, the card returns `HOLD` and requests one omission/addition test.

### 3.2 Complexity expansion

The card proposes the minimum nonredundant move that opens a new perceptual
plane, transition, or testable mechanism. It returns `NONE` when the target is
already coherent or every candidate duplicates an existing function. It must
not reward novelty or frontier size. It names the strongest current design as
the control and the first discriminator that would justify expansion.

### 3.3 Musk design

The card starts from zero musk and the strongest-single-musk baseline. It adds a
second musk only for a distinct tonal, spatial, textural, temporal, fixative, or
character-echo function that survives an omission test. Tonalide, Macrolide,
and Musk Ketone stay out of the proposed image unless a complete exception call
shows why admitted alternatives fail, what is lost by omission, the likely
failure mode, and both omission and strongest-alternative controls. Inventory
and target/ideal architecture remain separate.

### 3.4 Model admission

The card emits only `ADMIT`, `HOLD`, or `REJECT` for the exact claim scope. It
names the decisive missing or failed gate and never allows a passing design gate
to imply formula, sensory, safety, or release authority. Scalar compensation is
forbidden.

### 3.5 Model lifecycle

The card chooses `RETAIN`, `QUARANTINE`, `SUPERSEDE`, or `ROLLBACK` for the exact
release, data partition, preprocessing, endpoint, and calibration scope. It
binds drift to those exact identities and never lets a newer version silently
inherit authority from a predecessor.

### 3.6 Within-sniff design

The card separates a modeled pulse-order design from an observed perfume
effect. It names the apparatus and delivered-mass control that decides whether
an order claim is interpretable. Unqualified apparatus, unmatched mass, or an
unbound delivery receipt produces `HOLD`.

### 3.7 Temporal observations

The card reports only observed time cells, missing cells, and participant or
replicate disagreement. It does not invent a smooth sequence, narrative arc,
dominance handoff, or longevity claim between observations. Its decision is the
minimum next observation needed to distinguish competing temporal accounts.

### 3.8 Order balance

The card checks first-position frequency and immediate-predecessor carryover.
It returns `REBUILD` when either is imbalanced and identifies the exact alias.
A balanced schedule is still design-only and does not authorize allocation,
washout adequacy, execution, or inference.

### 3.9 Panel contract

The card names the estimand and claim ceiling before choosing endpoints. It
keeps richness/depth, target fidelity, and liking as separate outcomes. A
pleasantness endpoint cannot compensate for failed discrimination,
repeatability, agreement, or target-recognition requirements.

### 3.10 Citrus architecture

Citrus is selected by function and transition, not by a generic citrus label.
The card defines the required identity on five axes: dry/juicy, peel/pulp,
bitter/sweet, cold/warm, and naturalistic/abstract. It chooses one primary
citrus and at most one support or bridge when their roles are distinct. `NONE`
is valid when citrus would reduce depth or when brightness already comes from a
non-citrus mechanism.

The selector distinguishes flash, prism, peel, pith, bitter edge, juicy body,
aromatic bridge, floral transition, and green tension. Volatility alone does
not establish target fit. Bergamot is not a universal default, and generic
citrus stacking is rejected.

The target/ideal selection is made before inventory is consulted. The current
inventory build is then derived separately. Red Mandarin EO and Cedrat FCF Oil
Sicilian remain explicit target-specific gaps and may not be silently replaced.
Any substitution is a separate controlled branch. FCF, oxidation, lot,
phototoxicity, and dose issues are gates requiring the relevant authority; the
selector itself grants no safety conclusion.

`DHC_CITRUS_SCORING.txt` is evidence-only legacy material. Its computed
hedonism and count-derived complexity values cannot enter the selector or its
benchmark.

## 4. Individual benchmark

Each repaired module is compared with normal ChatGPT xhigh on six fresh,
projectless paired cases: three screening cases and, only after a credible
screen, three unseen confirmation cases. Both arms receive identical target,
inventory, evidence, output limit, and claim ceiling. The treatment arm receives
one decision card; the control does not.

Each module's cases include:

- one positive case where its specialist decision should improve the answer;
- one safe countercase where `NONE`, `HOLD`, or restraint is correct;
- one critical trap that the module must prevent;
- one target/current-inventory mismatch where relevant;
- one strongest-single or omission control where relevant; and
- one unseen variant with changed names, values, and surface wording.

An additional length-matched placebo card is tested for every passing module.
The real card must outperform the placebo; added tokens alone are not evidence
of module value.

## 5. Scoring and retention

The blinded rubric scores decision correctness, target-linked depth, restraint,
test quality, evidence fidelity, and claim discipline. Module-specific critical
errors are noncompensatory.

A module passes only with:

- at least four treatment wins across six valid pairs;
- median paired gain of at least five rubric points;
- no new critical regression;
- correct restraint or abstention on the safe countercase;
- prevention of the module-specific critical trap; and
- a positive result against the length-matched placebo.

Musk additionally must beat the strongest-single baseline without routine use
of Tonalide, Macrolide, or Musk Ketone. Citrus additionally must pass a `NONE`
case, an inventory-mismatch case, and a temporal-handoff case.

No post-hoc prompt repair is allowed on the six scored cases. A failed module is
returned to `RETIRED_BENCHMARK_UNDERPERFORMER`. A passing module receives a new
candidate hash and registry revision linked to the exact benchmark receipt.

## 6. Combined-survivor test

Only individually passing cards are combined with the already retained
experimental-design module. The combined prompt includes only cards relevant to
the case. An interaction test compares:

1. normal xhigh control;
2. the best single relevant card;
3. the combined relevant cards; and
4. a length-matched placebo bundle.

The combination is retained only when it adds a decision-changing benefit over
the best single card without introducing contradiction, verbosity-driven
padding, or critical regressions. Passing individual cards remain separately
usable if the combined interaction fails.

## 7. Authority and preservation

These benchmarks evaluate model assistance, not perfume truth. Physical liking,
richness, similarity, stability, safety, measured headspace, strict empirical
OAV, procurement, compounding, publication, and release remain `NOT TESTED` or
`HOLD` without their own evidence.

All prior source engines, failed prompt projections, benchmark bytes, and
receipts remain recoverable. Registry activation is the only runtime promotion
mechanism. No file is deleted merely because a card fails.
