# Hedonic Evidence, Perceptual Richness, and Release Gate Rebuild

Status: implemented evidence contract; physical perfume outcomes remain `NOT TESTED`.

Claim ceiling: `EXACT_SCOPE_OBSERVATIONAL_EVIDENCE_ONLY`. Nothing in this document or its code grants formula, compounding, purchase, safety, stability, sensory-success, publication, runtime-promotion, or release authority.

## 1. The central correction

Perfume hedonism is not a molecular lookup table, a weighted sum of ingredients, a prestige score, or a synonym for technical complexity. It is an observed evaluative response by a declared assessor population to an exact physical sample, under a declared presentation and exposure context, for one precisely worded criterion.

The program may design a perfume to create depth, richness, contrast, configurational integration, temporal development, comfort, fascination, tension, or relief. Those are architectural intentions and sensory hypotheses. They do not become liking merely because a model gives a persuasive explanation. The only admissible liking evidence is a real blinded comparison whose item labels, formula or reference builds, physical samples, protocol, assessor identities, repetition structure, timepoint, presentation sequence, substrate, environment, and analysis plan are frozen and hash-bound.

This correction preserves the user's intended meaning of complexity:

- complexity can come from a sparse formula when each material creates a distinct, target-faithful relation;
- complexity can come from deep layering when foreground, background, surface, interior, shadow, radiance, texture, and temporal transitions remain perceptually differentiated;
- more materials can instead create redundancy, masking, muddiness, sensory fatigue, or the undifferentiated convergence sometimes described as an olfactory white;
- richness and depth can raise hedonic potential for a particular target and assessor, but neither is a substitute measurement for liking;
- exact target recognition can itself be hedonically important, yet target fidelity and liking remain separate endpoints because a faithful reconstruction can be disliked and a less faithful variation can be liked.

## 2. Constructs that must never be collapsed

The closed registry in `configs/solforge/complexity_construct_registry_v1.json` defines the wording, anchors, required scope, outcomes, and forbidden inferences for each construct. Each comparison fits one construct only.

### 2.1 Identity and perceptual architecture

- `TARGET_FIDELITY` asks whether the sample corresponds to the frozen target identity. It is not liking, quality, or formula identity truth.
- `PERCEIVED_DEPTH` asks about experienced relational dimensionality: foreground/background, near/far, surface/interior, shadow/radiance, persistence and layering. It is not material count or longevity.
- `PERCEIVED_RICHNESS` asks about differentiated but integrated perceptual information. It is not chemical peak count, concentration, or ingredient count.
- `CONFIGURATIONAL_INTEGRATION` asks whether facets form a coherent perceptual object instead of a list of separable components. It does not prove molecular synergy.
- `HIERARCHY_CONTRAST` asks whether focal, supporting, and background functions are perceptually organized. It does not imply that a hierarchy is preferred.
- `TEMPORAL_DIFFERENTIATION` records observed transitions across qualified timepoints. Predicted volatility is not an observation.
- `PERSISTENCE` records continued perception of one endpoint. Vapor pressure, modeled OAV, boiling point, and substantivity remain mechanistic screens, not observed persistence.

### 2.2 Evaluation and motivation

- `LIKING` is the current positive evaluation of an exact sample in one context.
- `WANTING_TO_RESMELL` is desire for another exposure after a declared exposure history. Repetition can change wanting and liking differently, so one cannot stand in for the other.
- `WEAR_ACCEPTANCE` is willingness to wear the exact sample under a declared body site, dose, duration, climate, social setting, and wearer/body-odor context. Blotter liking cannot establish it.
- `COMFORT` is reported affective and perceptual ease. It is not liking, familiarity, non-irritancy, or physical safety.
- `FASCINATION` is sustained attentional pull or curiosity. A perfume may be fascinating but uncomfortable, tense, or only moderately liked.
- `TENSION` is unresolved contrast, instability, pressure, or expectancy. It has no fixed positive or negative hedonic sign.
- `RELIEF` is experienced resolution after an earlier tension observation in the same sequence. A static low-tension rating is not relief.
- `FATIGUE` is reported weariness after a declared cumulative exposure schedule. It must remain separate from sensory adaptation, loss of detectability, boredom, irritation, and falling wanting.
- `AVERSION` is an explicit negative or avoidance response. It is retained directly rather than calculated as `1 - liking`.

### 2.3 Control constructs

`INTENSITY`, `FAMILIARITY`, and `DETECTABILITY` are separate controls. Familiar odors can be liked or disliked. An intense odor can be rich or flat. A detectable difference can produce preference, indifference, or aversion. None of these controls may be used as a hidden liking proxy.

There is deliberately no total beauty score. There is no averaging across the constructs above. A decision report may show them side by side, with separate uncertainties and conflicts, but cannot compensate a failure or missing endpoint on one axis with a high value on another.

## 3. What the literature supports—and what it does not

The source registry retains metadata and derived summaries, not copyrighted article text. Each result below has an explicit transfer ceiling.

### 3.1 Paired preference and ties

Davidson's extension of Bradley–Terry provides a probability model for left wins, right wins, and ties ([Davidson 1970](https://doi.org/10.1080/01621459.1970.10481082)). In this program:

- directional comparison count includes only left and right choices;
- ties never become half-wins or fabricated directional victories;
- `NO_PREFERENCE` contributes to the Davidson indifference parameter and remains visible as a tie rate;
- `NO_PERCEPTIBLE_DIFFERENCE`, `CANNOT_JUDGE`, and `PROTOCOL_ABORT` are not preference ties and are excluded from the liking likelihood;
- utilities are relative to the connected item set and have no absolute origin;
- a fitted utility is not an intrinsic beauty property of a perfume.

The legacy three-argument `PairwisePreference(left, right, preferred)` constructor remains supported, but legacy rows cannot promote exact-scope liking because they lack the full evidence context.

### 3.2 Assessors are not interchangeable replicates

Lancaster and Quade's paired-comparison random-effects work explicitly treats judge-specific preferences as variable and repeated outcomes from the same judge as correlated ([Lancaster and Quade 1983](https://pubmed.ncbi.nlm.nih.gov/6871353/)). The implementation consequence is strict:

- uncertainty is resampled by assessor when assessor identity is present;
- repeated rows from one assessor cannot masquerade as independent population evidence;
- assessor heterogeneity is reported rather than averaged away;
- a trained-panel result applies to the exact bound panel unless a separate sampling design justifies a broader population claim;
- an owner result can establish that owner's scoped preference, not consumer preference.

Genetic and cross-cultural olfaction work reinforces this limit. Arshamian et al. found both shared structure and large individual variation in monomolecular pleasantness rankings across cultures ([Arshamian et al. 2022](https://pubmed.ncbi.nlm.nih.gov/35381183/)). This supports neither pure universalism nor pure relativism. It supports binding population and assessor scope and refusing to convert group-average molecular valence into an individual's perfume preference.

### 3.3 Order and carryover are evidence variables

Sensory order and carryover effects can be product- and attribute-specific. Balanced design is useful, but a planned balance is not proof that collected rows are balanced. The implementation follows the methodological consequence of work on presentation rank and carryover ([Huon de Kermadec and Pagès 2005](https://doi.org/10.1016/j.foodqual.2005.01.004)) and the existing MacFie evidence record:

- realized first-position counts are reported for every unordered item pair;
- both members of a pair must actually appear first under the declared balance tolerance;
- the first-position outcome effect is calculated only from directional outcomes;
- perfect first-position/outcome alignment is labeled confounded;
- assessor/session positions must be unique and contiguous;
- every position after the first binds the previous item and previous physical sample;
- a declared carryover or washout control must be qualified when the design has sequential exposure;
- missing previous-item lineage, duplicate positions, noncontiguous sequences, unqualified carryover, pair-order imbalance, or excessive first-position effect blocks promotion.

The receipt does not claim that this deterministic audit is a complete mixed-effects carryover model. Instead, it fails closed when the available evidence cannot separate item, order, and sequence effects.

### 3.4 Liking and wanting are different

Repeated-exposure work measured liking and wanting separately and observed different change patterns ([Triscoli et al. 2014](https://pubmed.ncbi.nlm.nih.gov/24910630/)). Therefore:

- wanting-to-resmell has its own criterion wording and fit;
- exposure count, spacing, and schedule are part of the evidence scope;
- declining wanting cannot be relabeled fatigue without a fatigue question;
- stable liking cannot be interpreted as stable wanting;
- sex- or subgroup-specific effects from one small study are not hard-coded as universal perfume rules.

### 3.5 Blotter and skin are different contexts

Lenochová et al. found individual donor-by-perfume interactions and a preference effect for owner-chosen perfume/body-odor blends even when the pure perfumes did not differ in pleasantness ([Lenochová et al. 2012](https://doi.org/10.1371/journal.pone.0033810)). The code consequence is not a claim that all skin effects follow that experiment. It is a transfer firewall:

- a skin result requires pseudonymous wearer identity and body-odor context hashes;
- application dose, site, environment, maturation, and wear context remain bound;
- a blotter result cannot silently become wear acceptance;
- another person's skin result cannot become the owner's result;
- an exact skin result still grants no dermatological or toxicological safety authority.

### 3.6 Composition and pleasantness have narrow transfer limits

Monomolecular structure work can predict part of group-average pleasantness under the studied intensity and odorant domain. Binary-mixture studies by Lapid et al. and Ma et al. support limited panel-level prediction from measured component psychophysics in tested binary mixtures ([Lapid et al. 2008](https://doi.org/10.1093/chemse/bjn026); [Ma et al. 2020](https://doi.org/10.1093/chemse/bjaa020)). These results do not authorize a general fine-fragrance beauty function because:

- monomolecular odorants are not finished perfumes;
- binary mixtures are not unrestricted multicomponent formulas;
- panel-average response is not owner preference;
- component pleasantness and intensity must be physically measured in the relevant scope;
- only a minority of mixtures in some studies showed departures from the tested component rules;
- skin, application, temporal transformation, adaptation, and cultural/personal familiarity can change the response.

Accordingly, `engine/hedonic_model.py` remains legacy provenance. Active optimization weights for composition-derived hedonics remain zero. A predicted OAV or molecular descriptor can prioritize a mechanistic experiment but cannot enter a liking fit, a release axis, or a formula rank.

## 4. The V3 evidence chain

### 4.1 Item identity

Every compared item has exactly one `PreferenceItemEvidenceBinding`:

- `item_id`: the opaque code used in comparisons;
- `build_sha256`: the exact compounded formula build, commercial reference identity record, or control build;
- `sample_sha256`: the exact physical sample identity;
- `provenance_manifest_sha256`: the frozen stock/source lineage;
- `sampling_or_dose_receipt_sha256`: how the test sample was drawn or dosed;
- `batch_id`: the declared preparation or reference batch.

The binding set must exactly equal the set of compared item IDs. Missing and extra bindings are both invalid. Every row contains separate left- and right-sample hashes; each must match the binding for that item. A label/sample swap is therefore either rejected or produces a different receipt hash. A single unordered list of sample hashes is no longer promotion evidence.

One item is declared focal. The focal item's build hash must match the formula build evaluated by the hedonic and release request. Other items remain fully bound comparison controls; their utilities do not become attributes of the focal formula.

### 4.2 Physical evaluation context

`SensoryEvaluationContext` binds:

- substrate: blotter, skin, air, or qualified apparatus;
- application protocol;
- environment;
- sample maturation state;
- carryover/washout control and its qualification state;
- apparatus identity when an apparatus is the presentation domain;
- wearer and body-odor context when the substrate is skin.

Every comparison row carries the same context hash for a single exact-scope fit. Context pooling requires a separately specified hierarchical design; it cannot occur implicitly.

### 4.3 Predeclared adequacy

`PreferenceEvidenceAdequacyContract` binds the analysis plan and sampling frame plus declared minimums for:

- assessor identities;
- directional training comparisons;
- frozen held-out groups;
- held-out observations;
- assessor-cluster bootstrap replicates;
- grouped held-out bootstrap replicates.

These declared minima are necessary conditions, not scientific guarantees. The program does not pretend that one universal sample-size threshold applies to an owner comparison, a trained descriptive panel, and a consumer population. The protocol must justify its scope and power before data collection. Zero held-out bootstrap replicates can no longer create a degenerate point interval that passes promotion.

### 4.4 Fit and validation

The V3 chain requires all of the following:

1. one isolated criterion, with `LIKING` required for the hedonic release axis;
2. unique comparison identities and complete scoped metadata;
3. a connected comparison graph;
4. a converged Davidson fit with visible tie parameter;
5. assessor-cluster uncertainty that is stable under the declared resampling contract;
6. a frozen group split with no assessor, session, or matrix leakage according to the declared split unit;
7. multinomial log loss and Brier scoring on held-out left/right/tie outcomes;
8. a predeclared baseline probability vector;
9. a paired grouped-bootstrap gain interval whose lower bound exceeds the practical margin;
10. no unresolved temporal crossover or stable majority cycle that would make a global winner misleading;
11. complete item/build/sample/context binding;
12. realized order and sequence checks passing;
13. the predeclared adequacy contract passing;
14. no unresolved sensory safety event.

Failure modes remain distinct:

- structurally invalid, scope-mismatched, leaked, or order-confounded evidence is `INVALID_OR_CONFOUNDED`;
- too little or unstable evidence is `INSUFFICIENT_EVIDENCE`;
- failure to beat the held-out baseline is `FAILED_HELDOUT_BASELINE`;
- valid but non-promotable compatibility evidence is `DIAGNOSTIC`;
- absence of observations is `NOT_TESTED`;
- only the complete V3 path can return `VALIDATED_EXACT_SCOPE`.

V1 and V2 receipts remain readable provenance. V1 accuracy-only validation cannot establish liking. V2 adds proper scoring and clustered diagnostics but lacks exact item-label-to-build/sample and physical-context binding, so it is capped at `DIAGNOSTIC` with `V3_ITEM_CONTEXT_BINDING_REQUIRED`.

## 5. Relationship to DHP-style and other perfume architectures

The architecture compiler has eight non-ranked strategies. Dior Homme Parfum 2025-style carved dark/radiant wood depth is one instance of `CHIAROSCURO_DUAL_STATE`, not the universal path to luxury or hedonism.

The hedonic system must support different causal stories without choosing one globally:

- a DHP-like dark/radiant design may test depth, hierarchy, tension, relief, target fidelity, liking, and wear acceptance separately;
- a minimal-precision iris or cologne may test whether sparse exact selection improves target fidelity and comfort without requiring maximal richness;
- a polyphonic floral may test configurational integration and differentiated richness while watching for muddiness and fatigue;
- a saturated amber or resin enclosure may seek warmth and immersion while explicitly measuring fatigue, aversion, and temporal compression;
- a spatial-field musk or mineral design may seek near/far separation and diffusion while using zero or one precise musk by default;
- an object-anatomy soliflore may separate petal, pollen, stem, wax, root, humidity, and shadow without assuming that more represented anatomy is more liked;
- a temporal metamorphosis may be liked at one timepoint and disliked at another, requiring window-specific results rather than one global winner.

For every architecture, the smallest target-faithful nonredundant intervention remains the default experiment. Constant-total omission, addition, or ratio arms protect against the false conclusion that a stronger, larger, or more ingredient-rich sample is intrinsically better.

## 6. OAV and release firewall

The OAV gate and hedonic gate are adjacent but independent.

OAV can answer a bounded chemical or measurement question: under the exact stock, dose, threshold source, matrix, and measurement context, is a material or constituent modeled or measured above a detection ratio? It cannot answer:

- what percentage of the perfume is perceived as that material;
- whether the material creates the intended relation;
- whether a transition is observed;
- whether the perfume is rich, deep, faithful, comfortable, fascinating, or liked;
- whether a predicted temporal OAV curve is an observed temporal sensory curve.

The release conjunction is noncompensatory. It requires independent source-rights, target identity, inventory lineage, active-dose rebase, strict OAV evidence, safety/IFRA, laboratory execution, sensory evidence, and V3 hedonic evidence axes. A high diagnostic score cannot compensate for a missing or failed axis. Even when every axis passes, the state is only `READY_FOR_HUMAN_REVIEW`; `release_authority` remains false.

Legacy heuristic gates in `engine/pipeline/gates.py` may remain importable for compatibility and provenance, but they cannot supply the hedonic release axis. Composition-derived neuroscience flags, family heuristics, material-count rules, prestige language, and old fixed-valence scores are advisory or tombstoned, not evidence.

## 7. Model-tier retirement and speed policy

The goal is not to use the slowest model forever. The goal is to stop paying for high reasoning effort only after the program has made the judgment deterministic and empirically safe.

### 7.1 Ultra remains required when

- a new architecture, scientific transfer, construct, or causal interpretation is being designed;
- sources conflict or their transfer ceiling is ambiguous;
- a new active gate, criterion, protocol, or release authority boundary is proposed;
- a failure may be caused by cross-module interaction rather than a local deterministic defect;
- benchmark cases expose a critical regression, criterion leakage, provenance gap, or new adversarial class;
- final admission or destructive retirement of a module is being decided.

### 7.2 xhigh may replace Ultra when

- architecture, construct, evidence, and authority schemas are frozen and hash-bound;
- the task is an application of those schemas rather than a change to their meaning;
- the xhigh candidate passes fresh blinded screening on unseen cases against Ultra with no critical regression;
- it meets the declared win and paired-gain thresholds against both the Ultra reference and a length-matched placebo control;
- failures, holds, and abstentions are preserved rather than optimized away;
- deterministic local verification reproduces the same receipts and hashes.

### 7.3 normal or faster Sol may replace xhigh when

- the work is deterministic parsing, schema validation, hashing, rendering, inventory joining, test execution, or a frozen rule lookup;
- no scientific transfer, architecture choice, formula aesthetic judgment, conflict resolution, or promotion decision is involved;
- adversarial non-inferiority testing shows zero critical regressions on the frozen task class;
- a higher-tier escalation trigger is explicit and automatically produces `HOLD` rather than a lower-quality guess.

Cost and latency never lower the model tier for a hedonic or architecture judgment. Speed is optimized only after the truth conditions are explicit, testable, and frozen. The practical endpoint is a mostly deterministic program in which Ultra is exceptional, xhigh handles bounded judgment, and normal/Fast handles mechanical execution without being asked to invent taste.

## 8. Remaining limits

The implementation closes major provenance and validation gaps, but it does not create physical data. No current formula becomes liked, rich, deep, stable, safe, or releasable because these contracts exist. The next scientific step is prospective use:

1. freeze criterion wording and an exact architecture hypothesis;
2. compound isolated constant-total arms from ExactStockRef-bound materials;
3. assign opaque item codes and exact sample hashes;
4. execute a qualified balanced protocol with real observations;
5. preserve all missing, tied, aborted, and adverse rows;
6. fit and validate only after the frozen held-out partition remains untouched;
7. use the result to choose at most one next comparison or intervention;
8. repeat until the target decision resolves or evidence remains insufficient.

The program can make that process more economical. It cannot replace the nose, the wearer, the sample, or the experiment.
