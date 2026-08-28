# Evidence Value, Material Economy, and Model-Tier Retirement

Status: implemented candidate on `codex/perceptual-architecture-v1`; not admitted to the complexity runtime and not yet benchmark-authorized to retire xhigh or Ultra for judgment.

Claim ceiling: `COMPUTATIONAL_EXPERIMENT_SELECTION_AND_MODEL_ROUTING_ONLY`.

Every formula, sensory, hedonic, safety, purchase, physical-execution, compounding, and release authority flag remains false. A selected experiment is permission to review one design, not permission to compound it. A selected model tier is permission to execute one frozen task class, not evidence that any perfume smells good.

## 1. The two problems this phase solves

The architecture and hedonic rebuilds created a better theory of what must be observed. They did not yet solve two operational problems:

1. **Which unresolved question should be tested next?** A program can contain dozens of plausible omissions, additions, ratios, timepoint observations, panel comparisons, inventory audits, and n-ary designs. Running all of them wastes material and assessor attention. Choosing the cheapest one first can also waste material if the cheap result cannot change the decision.
2. **When can a faster reasoning tier safely replace a slower one?** Saying “xhigh should be enough now” or “normal/Fast is cheaper” is not evidence. The exact task contract, held-out cases, reference output, regressions, abstentions, and authority behavior must be frozen before a lower tier is allowed to replace a higher one.

The two new contracts answer these questions without converting speed, cost, ingredient count, or model eloquence into truth.

- `engine/perception/experiment_value.py` selects zero or one next evidence-producing experiment.
- `engine/solforge/model_tier_router.py` selects deterministic code, normal/Fast, xhigh, Ultra, or a human-authority hold.
- `configs/solforge/model_tier_policy_v1.json` contains the executable retirement thresholds.

Neither contract is a new complexity score. Neither is wired into the admitted complexity ensemble. They are governance infrastructure awaiting fresh benchmark evidence.

## 2. Why the selector does not calculate fake expected value

Expected information gain and Bayesian expected utility are powerful only when their required inputs are real. Lindley’s information-from-experiment formulation depends on prior knowledge represented as a probability distribution. The decision-theoretic review by Chaloner and Verdinelli likewise makes the prior, sampling model, utility, and decision problem part of one coherent design. Atkinson and Fedorov provide a different but related model-discrimination tradition: choose experiments that separate explicitly competing models.

Primary methodological sources:

- D. V. Lindley, [“On a Measure of the Information Provided by an Experiment”](https://doi.org/10.1214/aoms/1177728069), *The Annals of Mathematical Statistics* 27 (1956), 986–1005.
- K. Chaloner and I. Verdinelli, [“Bayesian Experimental Design: A Review”](https://doi.org/10.1214/ss/1177009939), *Statistical Science* 10 (1995), 273–304.
- A. C. Atkinson and V. V. Fedorov, [“The Design of Experiments for Discriminating Between Two Rival Models”](https://doi.org/10.1093/biomet/62.1.57), *Biometrika* 62 (1975), 57–70.

These sources do **not** provide a perfume-specific hedonic utility, a formula prior, or calibrated outcome probabilities for this inventory. Therefore the implementation refuses to produce a numeric “expected beauty,” “expected liking,” or “expected information” value. It would be mathematically decorative and scientifically false to assign, for example, a 70% chance that increasing a woody counterform will deepen Dior Homme Parfum architecture when no calibrated prospective model supports that probability.

The version-one selector instead uses a conservative, prior-free rule over a finite set of predeclared hypotheses and outcomes:

1. require every candidate outcome to eliminate at least one currently unresolved hypothesis or resolve the exact decision;
2. maximize the number of hypotheses eliminated under the candidate’s **least discriminating** declared outcome;
3. then maximize how many outcomes directly resolve the decision;
4. then maximize distinct hypothesis coverage;
5. then prefer blocking over primary over secondary decision impact;
6. only after evidentiary quality is tied, minimize physical work, scarce material, total active material, assessor sessions, and instrument time;
7. break any remaining tie by stable candidate identifier.

This is a deterministic maximin discrimination policy. It is deliberately not called Bayesian expected utility. A later version may add calibrated Bayesian design only after prior and likelihood provenance, calibration performance, and criterion-specific utility are available at the exact perfume and protocol scope.

## 3. What an evidence-value candidate must contain

Every `EvidenceValueCandidate` is a pre-result contract. It contains:

- a stable candidate identifier;
- the SHA-256 of the source receipt that created the candidate;
- the exact decision-scope SHA-256;
- one criterion identifier;
- one experiment domain;
- a declared decision impact;
- every possible result category the protocol intends to distinguish;
- the hypotheses eliminated by each result category;
- whether each category would resolve the decision;
- protocol qualification status;
- sample and formula lineage completeness;
- inventory executability where a physical formula is involved;
- constant-total status;
- blinding status;
- isolated-arm completeness;
- whether physical work is required;
- explicit burden quantities;
- safety-review requirement and completion state; and
- any unresolved blocker codes.

The outcome categories must be declared before observations exist. An outcome cannot be added after seeing the result merely to make an experiment look informative.

The exact scope and criterion must match the request. A DEPTH experiment does not resolve LIKING. A DHP 2025 current-inventory build does not resolve an Opus V target. A blotter comparison does not resolve skin wear acceptance. A test conducted with one stock basis does not resolve a silently rebased formula.

## 4. Five experiment domains and their limits

### 4.1 `EVIDENCE_AUDIT`

An evidence audit checks bytes, sample lineage, stock identity, protocol completeness, duplicate cells, missing observations, source conflicts, or another evidentiary dependency. It may require no physical material.

An audit may outrank a physical experiment only when it provides equal or greater discrimination. This is important. If two possible outcomes of an inventory-basis audit would determine whether the apparent formula difference is real, compounding more samples before resolving that audit is wasteful. But a cheap audit cannot defeat a physical comparison merely because it is cheap if the audit cannot separate the competing perceptual hypotheses.

### 4.2 `FORMULA_DELTA`

A formula delta is one isolated omission, addition, or ratio intervention produced by Architectural Delta. It requires:

- exact current-stock lineage;
- inventory executability;
- constant total or a declared justified exception outside this selector;
- opaque blinding;
- complete isolated arms;
- a nonzero physical sample count;
- completed required safety review; and
- outcomes tied to a single criterion.

The selector does not choose a dose and does not authorize compounding. It chooses among already complete experimental candidates.

### 4.3 `TEMPORAL_OBSERVATION`

A temporal observation uses the qualified Temporal Sensory Ledger. It must preserve actual missingness, bind every canonical observation cell, and avoid turning volatility predictions into perceived transitions. The selector can choose between, for example, an early-heart transition comparison and a late-drydown persistence comparison only when each candidate declares what unresolved hypotheses its possible observations can remove.

### 4.4 `PAIRWISE_PREFERENCE`

A pairwise preference experiment isolates one criterion such as LIKING, DEPTH, RICHNESS, TARGET_FIDELITY, COMFORT, or WANTING_TO_RESMELL. The candidate’s lineage must connect item, build, physical sample, assessor, protocol, timepoint, substrate, realized order, and evaluation context.

The selector never uses a model-derived liking prediction as the value of the comparison. It can use the declared comparison graph and unresolved alternatives to identify which real comparison could discriminate most, but the result remains unknown until people evaluate exact samples.

### 4.5 `NARY_INTERACTION`

An n-ary interaction candidate cannot be selected unless all isolated arms are complete. Pairwise evidence cannot establish three-way or layered synergy. For two factors, the minimum causal structure normally includes control, factor A, factor B, and A×B under constant-total conditions. For more factors, the design must preserve the corresponding main-effect and interaction estimability required by the existing n-ary contract.

An eloquent story about “layering” is not an arm.

## 5. Admissibility is checked before burden

A candidate is rejected before ranking when any applicable condition fails:

- exact scope mismatch;
- criterion mismatch;
- unknown hypothesis reference;
- a declared outcome that neither eliminates a hypothesis nor resolves the decision;
- unqualified protocol;
- incomplete lineage;
- explicit blocker;
- nonexecutable inventory for physical work;
- missing constant-total control;
- missing blinding where required;
- incomplete isolated formula or n-ary arms;
- required safety review not completed;
- physical work with no declared sample count; or
- a hard resource ceiling exceeded.

If no candidate survives, the result is `HOLD`, not a guess. If the decision is already resolved, the result is `NO_CHANGE`, even if attractive experiments remain. If one or more candidates survive, the result is `SELECTED` and contains exactly one selected candidate plus the complete auditable ranking and rejection ledger.

This prevents three waste modes:

1. **Cheap ambiguity:** selecting an inexpensive experiment whose likely result leaves every important hypothesis unresolved.
2. **Expensive theater:** selecting an elaborate panel or instrumental study whose outcome cannot change the decision.
3. **Premature formula work:** compounding before an audit could establish that the apparent question is caused by missing lineage, wrong stock basis, duplicate observations, or another evidentiary defect.

## 6. The lexicographic ranking is not a beauty score

The score has only auditable design quantities:

- worst-case hypotheses eliminated;
- decision-resolving outcome count;
- distinct unresolved hypotheses covered;
- declared decision impact;
- whether physical work is required; and
- physical sample, scarce-material, active-material, assessor-session, and instrument burden.

There is no field for:

- ingredient count;
- molecular count;
- note count;
- “luxury”;
- prestige;
- naturalness;
- supplier price;
- formula complexity;
- predicted beauty;
- predicted liking;
- model confidence; or
- explanation length.

The ranking is lexicographic rather than a weighted sum. A material-saving benefit cannot compensate for losing one unit of worst-case discrimination. This avoids arbitrary exchange rates such as “one eliminated hypothesis equals 20 mg of scarce material” or “one assessor session equals 0.2 depth points.” Such exchange rates have no evidentiary basis here.

## 7. How this applies to perfume architectures

### 7.1 DHP-style carved dark–radiant depth

For a DHP 2025 target, the Chiaroscuro architecture may contain an orris recognizer, leather shadow, carved wood gravity, radiant counterform, and tactile continuity. Several next actions might appear plausible:

- audit whether the current sample truly uses the declared Alpha Irone 10% stock and exact carrier basis;
- omit one woody pressure material to test whether carved grain becomes clearer;
- adjust one shadow-to-radiance ratio;
- compare two temporal drydown windows;
- add a musk intended to bridge tactile continuity; or
- run a multi-musk layered design.

The selector does not assume that the multi-material design is deeper. If an exact-stock audit can distinguish “formula architecture failure” from “stock-basis mismatch” under every declared outcome, it should precede compounding. If the audit cannot resolve the perceptual question but a one-factor omission can, the omission wins despite costing material. A multi-musk design remains blocked unless its isolated arms are complete and every musk has a distinct target-linked function.

### 7.2 Minimal Precision

For a sparse citrus-floral or orris design, a candidate addition receives no reward for increasing material count. A `NO_CHANGE` decision is valid when every target function is already owned and no nonredundant intervention remains. If two ratio arms can discriminate whether a tiny bridge preserves identity, that small experiment can outrank a broad expansion screen.

### 7.3 Polyphonic floral combinations

For a two-, three-, or four-flower design, the hypotheses must distinguish at least:

- independent floral voices retained;
- one flower taking over;
- collapse into one coherent bloom object;
- muddy or indeterminate floral mass; and
- target identity drift.

Whether “independent voices” is success depends on the locked architecture. It is success for Polyphonic Counterpoint and may be failure for Object Anatomy Transformation. The selector therefore binds the exact criterion and architecture scope rather than awarding general floral complexity.

### 7.4 Object-anatomy gourmand realism

For an apple-pie fine-fragrance target, a cheap spice adjustment may be less informative than an omission distinguishing crust realism from generic cinnamon warmth. Conversely, an evidence audit of the AP-T1 cinnamon substitution can precede physical work if stock preparation and sample lineage are unresolved. The AP-T1-only sensory substitution authority does not become general chemical or OAV equivalence.

### 7.5 Saturated amber and resin systems

For an amber using benzoin, storax, myrrh, opoponax, frankincense, or olibanum, resin count and concentration do not establish enclosure, richness, or beauty. Candidate experiments must separate target functions such as balsamic body, smoke/mineral aperture, leathery shadow, ambery continuity, sweetness, and fatigue. If all outcomes of a proposed “add another resin” test leave those hypotheses entangled, the candidate is rejected as nondiscriminating.

## 8. OAV, sensory, hedonic, and release remain separate

The selector does not repair OAV by pretending OAV predicts pleasure. The correct chain is:

1. exact material and stock identity;
2. exact formula and active-equivalent dose receipt;
3. applicable physicochemical or OAV diagnostics with source and uncertainty;
4. qualified physical experiment design;
5. exact physical sample and execution lineage;
6. observed sensory cells for the declared endpoint;
7. criterion-specific preference or hedonic evidence;
8. held-out validation and assessor/order diagnostics;
9. safety, stability, and release review by their own authorities.

Modeled OAV may identify an analytical risk or support experiment planning. It cannot establish detectability, depth, richness, persistence, liking, similarity, safety, or release. Hedonic evidence can establish only its exact criterion, population, sample, substrate, and context. Release remains a later human-governed review state.

## 9. The model-tier hierarchy

The router has four execution tiers plus a human hold:

| Tier | Intended work | What it cannot do |
|---|---|---|
| `NO_MODEL_DETERMINISTIC` | parsing, hashing, closed-schema validation, test execution, exact inventory joins when contract and output are machine-checkable | interpret science, choose architecture, judge smell, resolve ambiguous evidence |
| `SOL_NORMAL_FAST` | frozen rendering or frozen rule application after exact-agreement proof | change a rule, interpret hedonics, resolve conflict, admit a module |
| `SOL_XHIGH` | frozen bounded judgment after exact-scope noninferiority to Ultra | create new architecture/scientific meaning, alter gates, resolve open critical regressions without escalation |
| `SOL_ULTRA` | new architecture, hedonic interpretation, scientific transfer, source conflict, cross-module synthesis, gate change, module admission or retirement | grant physical, safety, compounding, purchase, or release authority |
| `HOLD_HUMAN_AUTHORITY` | final safety or release decision | no model is selected |

The practical target is not “use normal Sol everywhere.” The practical target is:

1. use deterministic local code for the large mechanical majority;
2. use normal/Fast only for frozen machine-checkable language tasks after exact agreement;
3. use xhigh for bounded judgment after it has matched or exceeded Ultra on unseen cases;
4. reserve Ultra for genuinely new or conflicted reasoning; and
5. keep human physical and release authority outside every model.

This is both faster and less degrading than asking a cheap model to perform tasks it cannot reliably verify.

## 10. Immediate Ultra retirement: what is already allowed

Ultra can be turned off **now** for these tasks when the exact contract is frozen and the output is fully machine-checkable:

- deterministic parsing;
- exact-byte hashing;
- strict schema validation;
- deterministic test execution;
- exact inventory joins;
- canonical serialization;
- manifest comparison;
- closed-rule lookup that is executed by code rather than interpreted by a model.

The preferred tier for those operations is not normal Sol. It is `NO_MODEL_DETERMINISTIC`, because model generation adds latency and possible variation without adding information.

Ultra cannot yet be turned off for frozen language-based rule application in this branch because no fresh xhigh-versus-Ultra benchmark receipt exists. The router reports `XHIGH_NONINFERIORITY_NOT_PROVEN` and selects Ultra. This is an evidence gap, not a claim that xhigh is necessarily worse.

## 11. The xhigh retirement gate

For one exact frozen task class and contract, xhigh may replace Ultra only if a frozen receipt records at least:

- three screening cases;
- two screening wins and a screening win fraction of at least 2/3 when more than three cases are used;
- six confirmation cases;
- four confirmation wins and a confirmation win fraction of at least 4/6 when more than six cases are used;
- five confirmation nonlosses and a confirmation nonloss fraction of at least 5/6 when more than six cases are used;
- nonnegative median paired delta;
- unseen variants;
- mutation cases;
- adversarial cases;
- deterministic replay;
- zero critical errors;
- zero improper `HOLD` regressions; and
- zero authority regressions.

The candidate and reference model identities, contract hash, benchmark corpus hash, raw output bundle hash, counts, and outcomes must all be frozen. A receipt from another task class, another contract hash, or another model pair is irrelevant.

This gate is intentionally a minimum. The Python loader independently enforces the version-one floor, so editing the JSON to lower case counts, win fractions, coverage requirements, replay requirements, or zero-regression rules fails closed. High-risk task families may adopt stronger thresholds. Architecture creation, scientific transfer, hedonic interpretation, source-conflict resolution, gate changes, and module admission remain Ultra-only in version one even if a frozen-rule receipt passes.

## 12. The normal/Fast retirement gate

Normal/Fast may replace xhigh only after the xhigh stage is already proven and the task is machine-checkable. It requires at least:

- six screening cases with all six wins or exact successes;
- twelve confirmation cases;
- all twelve confirmation wins;
- all twelve confirmation nonlosses;
- exact confirmation agreement on all twelve;
- unseen variants;
- mutation cases;
- adversarial cases;
- deterministic replay;
- zero critical errors;
- zero `HOLD` regressions; and
- zero authority regressions.

A normal-versus-xhigh receipt cannot bypass the xhigh-versus-Ultra receipt. This preserves a transitive evidence chain rather than comparing a cheap tier only to an unvalidated middle tier.

The Python loader also prevents task-class reassignment inside version one. A configuration edit cannot move architecture design, hedonics, scientific transfer, conflicts, gate changes, or admission into a cheaper route without a new reviewed schema and code change.

If normal/Fast fails, the router stops at xhigh. If xhigh fails, it stops at Ultra. If the user explicitly requests a lower unproven tier, the router returns `ESCALATE` and the minimum accepted tier rather than silently obeying the cheaper request.

## 13. Automatic Ultra escalation triggers

Even a task with passing lower-tier receipts returns to Ultra when any of these is true:

- the contract is not frozen;
- a scientific source conflict is open;
- a critical regression is open;
- the task changes authority;
- the output is not machine-checkable where normal/Fast is requested;
- a new construct, architecture, rule, gate, criterion, transfer claim, or compatibility interpretation is needed;
- cross-module behavior makes the local rule ambiguous; or
- module admission or retirement is being decided.

Safety and release authority do not escalate to Ultra. They move to `HOLD_HUMAN_AUTHORITY`, because more model reasoning cannot manufacture human or regulated authority.

## 14. Benchmark anti-gaming rules

A valid retirement benchmark must prevent these shortcuts:

- reusing cases seen during implementation;
- changing the prompt or output schema by tier;
- giving one tier extra context;
- dropping ties, holds, or failures;
- scoring explanation length as quality;
- treating refusal to overclaim as a loss;
- omitting inventory mismatches or missing-evidence countercases;
- allowing an authority regression to be offset by wins elsewhere;
- selecting a favorable random seed after seeing results;
- comparing unbound summaries instead of exact output bytes;
- changing model identity or reasoning mode without a new receipt; or
- importing a receipt from another contract, repository state, or task class.

The fresh module-admission benchmark requested for Architectural Delta, Temporal Sensory Ledger, and Hedonic Preference is a separate gate. Each replacement module must still beat plain Sol xhigh and a length-matched placebo in fresh projectless conversations under the declared 3-screen/6-confirmation admission rule. The model-tier router does not pre-admit those modules and cannot convert their unit-test success into benchmark success.

## 15. Current operational answer

At this checkpoint:

- deterministic local operations may stop using Ultra immediately;
- xhigh may **not yet** replace Ultra for the frozen rule-application class because no passing exact-scope retirement receipt exists;
- normal/Fast may **not yet** replace xhigh for language rule application because neither stage of the required receipt chain is complete;
- Ultra remains required for new architecture, hedonic meaning, scientific transfer, source conflicts, gate changes, and admission;
- no model may make final safety or release decisions.

This answer will change only when new frozen receipts satisfy the executable policy. It will not change because a chat says the work “looks good.”

## 16. Runtime and provenance status

The evidence-value selector and tier router are candidate infrastructure. They are not current complexity capabilities. They do not appear in the admitted complexity registry or ensemble wiring. Historical failed modules and benchmark outputs remain provenance tombstones.

Before runtime promotion:

1. focused software tests must pass;
2. relevant integration and governance tests must pass;
3. policy and source bytes must be hashed;
4. fresh exact model outputs must be frozen;
5. module admission and model retirement must be scored independently;
6. all critical-error and authority-regression counts must remain zero;
7. the canonical repository must be compared against this isolated worktree;
8. only the reviewed manifest may be integrated; and
9. physical claims remain `NOT TESTED` after code admission.

## 17. Executable artifacts

- `engine/perception/experiment_value.py`: immutable candidates, outcome discrimination, admissibility, burden, deterministic ranking, and all-false selection receipt.
- `tests/test_experiment_value.py`: resolved decisions, evidence-audit dominance, truth-before-burden, scope and criterion mismatch, unknown hypotheses, design blockers, n-ary isolation, deterministic tie-breaking, and forbidden proxy checks.
- `engine/solforge/model_tier_router.py`: strict policy loading, frozen benchmark receipts, tier routing, escalation, and human-authority hold.
- `configs/solforge/model_tier_policy_v1.json`: exact task routes and retirement thresholds.
- `tests/test_model_tier_router.py`: deterministic routing, Ultra-only classes, xhigh and normal pass/fail matrices, chain enforcement, risk escalation, strict policy loading, and stable hashes.
- `configs/solforge/research_source_seeds_v1.json`: method-only source seeds for information-from-experiment, Bayesian design, and model discrimination.

The JSON policy is executable authority. This document explains the policy but cannot override it. Any threshold, task-class, or authority change requires a new reviewed policy version, tests, exact hashes, and Ultra-level admission review.
