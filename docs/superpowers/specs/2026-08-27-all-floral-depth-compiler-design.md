# All-Floral Target-First Depth Compiler Design

**Date:** 2026-08-27
**Status:** User-approved architecture; implementation not started
**Branch:** `codex/all-floral-depth-candidate`
**Authority ceiling:** Computational experiment design only. No formula, compounding, procurement, sensory, hedonic, safety, stability, publication, release, or runtime-admission authority.

## 1. Decision Summary

Perfume-Chem will gain one target-first floral design compiler that covers every
floral-dominant perfume rather than one White Champi special case. It will not
install a universal floral recipe, a fixed DHP pattern, or a beauty score.

For each perfume, the compiler will first define the named identity, emotional
tone, floral subject, realism target, and functional architecture. It will then
select a flower-specific depth strategy, preserve TARGET/IDEAL independently of
CURRENT-INVENTORY, bind any proposed change to one controlled comparison, and
keep modeled OAV separate from sensory and hedonic truth.

The compiler will be layered over the already admitted Architectural Delta
engine. It will enter the complexity registry as
`FUTURE_CANDIDATE_NOT_VALIDATED` with no runtime import. Runtime admission will
be a later, evidence-gated change only if a blinded benchmark demonstrates that
the installed stack plus this compiler outperforms plain Sol XHIGH, the current
installed-authority stack, and a length-matched placebo without critical
regressions.

The three previously tested generic topology candidates will remain provenance
tombstones. They will not be revived or silently repackaged.

## 2. Why This Is Needed

The White Champi redesign exposed a specific failure in generic floral work:
putting a pleasant floral core in front of woods, amber, sweetness, or musk can
make a deep perfume without making the flower itself deep. The transferable DHP
function is an identity-bearing relationship inside the flower, but even that
is not universal. Rose, muguet, tuberose, iris, osmanthus, and a floral bouquet
do not obtain depth through the same anatomy, tension, or temporal behavior.

The existing program already contains important pieces:

- `engine/target/formula.py` keeps target formula truth independent of stock;
- `engine/graphs/accord_graph.py` represents contrast, reinforcement, and
  temporal handoff relationships;
- `engine/perception/architectural_delta.py` admits zero or one closed,
  target-faithful experiment and rejects ingredient-count rationales;
- `engine/solforge/architectural_adapter.py` binds experiments to exact current
  inventory authority;
- `engine/perception/complexity_registry.py` keeps unadmitted candidates
  runtime-unreachable; and
- the SolForge evidence loop already separates design, execution receipts,
  observations, conclusions, and promotion.

The missing piece is a concise floral-domain compiler that gives these general
systems a flower-specific target contract without repeating the failed generic
topology stack.

## 3. Scope: What “All Florals” Means

The compiler applies whenever the named identity is a flower, a flower accord,
or a perfume family whose principal identity is floral.

### 3.1 Included

1. **Soliflores and named-flower studies**
   - rose;
   - jasmine and jasmine sambac;
   - tuberose;
   - ylang-ylang;
   - champaca and White Champi;
   - magnolia;
   - orange blossom or neroli when central;
   - osmanthus;
   - muguet, lily, freesia, peony, cyclamen, hyacinth, and gardenia;
   - iris, orris, and violet;
   - mimosa, heliotrope, immortelle, carnation, geranium, and other explicitly
     named floral subjects.

2. **Floral ensembles**
   - floral bouquet;
   - white-floral bouquet;
   - rose-jasmine or other explicitly co-led compositions;
   - abstract floral where the abstraction itself is the named target.

3. **Floral-dominant families**
   - soft, powdery, aldehydic, green, and amber florals;
   - floral chypre;
   - fruity floral;
   - woody floral musk;
   - floral aquatic;
   - floral leather, floral fougère, gourmand floral, or incense floral only
     when the floral identity remains the declared lead.

### 3.2 Excluded by default

A perfume is not in scope merely because it contains a floral material. Neroli
in a cologne, geranium in a fougère, rose in an amber, or jasmine in a chypre is
outside this compiler when it is only support. These cases stay with their
controlling non-floral architecture unless the brief explicitly promotes the
flower to a named co-lead.

The scope test is therefore semantic and target-first, not a material-name
search or a percentage threshold.

## 4. Governing Design Principles

### 4.1 The perfume name remains the authority

The compiler will never optimize toward a generic “floral” score. A material,
facet, relation, or transition is valid only when its omission would change the
named flower or the declared emotional/architectural effect.

### 4.2 Flower facets are optional functions, not a checklist

The vocabulary may include petal, flesh, pollen, nectar, green stem or leaf,
humidity, diffusion, shadow, root or rhizome, wax, fruit, spice, tea, leather,
powder, or temporal transition. No design must contain all of them. Every
included facet must declare:

- its flower-specific target function;
- evidence or explicit design authority for using it;
- what is lost if it is omitted;
- its collision or drift risk; and
- the controlled comparison that can distinguish it from filler.

Facet count is never complexity evidence.

### 4.3 The DHP hedonic function is a strategy, not a template

The DHP-derived mechanism is **autogenous polarity**: two perceptibly different
states belong to one named floral identity and become more pleasurable or
engaging through their coupling. It is not “add a heavy base behind a flower.”

For White Champi, the approved hypothesis is cool bud/distillate pressure
coupled to warm open-flower benzenoid/indolic flesh, with shared White Champi
identity and temporal recurrence. Other flowers may use different mechanisms
or no polarity at all.

### 4.4 Precise simplicity is valid

If the target is already complete through one clear relationship, the compiler
must return `NO_CHANGE`. It must not invent a second pole, add a shadow, or pad
the formula to demonstrate sophistication.

### 4.5 Performance is designed and tested, never inferred as success

Every proposal must identify its intended opening, heart, and drydown carriers
and preserve the flower’s identity through the declared time contour. Modeled
vapor, OAV, and temporal loss can expose a weak performance hypothesis. They
cannot establish sillage, longevity, three-dimensional depth, or DHP-grade
hedonism. Those outcomes remain `NOT_TESTED` until a valid physical protocol is
observed.

## 5. Typed Contracts

### 5.1 `FloralIdentityContractV1`

The target contract will contain:

- `target_identity`;
- `emotional_tone`;
- `floral_subjects` and lead/co-lead/support roles;
- `floral_scope` (`SOLIFLORE`, `BOUQUET`, `FLORAL_DOMINANT_FAMILY`, or
  `FLOWER_LED_HYBRID`);
- `realism_target`;
- `ideal_formula_ref` or accepted target reference;
- `current_inventory_build_ref`, kept distinct from the ideal;
- `allowed_source_classes`;
- explicit forbidden drift directions;
- claim ceiling; and
- exact evidence/source bindings.

The current user policy sets `allowed_source_classes` to essential oils,
absolutes, and known chemicals. Opaque fragrance oils, FTECs, undisclosed bases,
and supplier accords are rejected unless the user later changes that policy
for a named design. A supplier name or marketing description does not make a
material a known chemical.

### 5.2 `FloralFacetV1`

Each facet will declare:

- stable `facet_id`;
- facet class;
- target-linked function;
- subject ownership;
- omission loss;
- failure or overdose mode;
- required temporal windows;
- evidence references;
- ideal materials or material classes when known; and
- current-build bindings when available.

Ideal material declarations never imply ownership.

### 5.3 `FloralDepthStrategyV1`

Every case chooses exactly one primary strategy. A secondary strategy is
allowed only when it has a distinct function and an isolated comparison.

| Strategy | Meaning | Typical use, not a default |
|---|---|---|
| `AUTOGENOUS_POLARITY` | Opposed states inside one flower are reciprocally coupled | White Champi cool shell/warm flesh; iris petal/root |
| `ANATOMICAL_CONTINUUM` | Depth comes from believable movement through parts or bloom stages | bud to petal to pollen to floral skin |
| `TEMPORAL_METAMORPHOSIS` | The same identity changes character through time | fresh jasmine to indolic warmth; green rose to dried petal |
| `ATMOSPHERIC_RELIEF` | Space, humidity, air, or negative space reveals the subject | muguet, magnolia, transparent freesia |
| `TEXTURAL_COUNTERPOINT` | Contrasting textures enrich one identity without splitting it | wax/flesh, powder/root, satin/green thorn |
| `INTERFLOWER_POLYPHONY` | Distinct flowers remain legible while creating one hierarchy | bouquets and co-led florals |
| `PRECISE_SIMPLICITY` | One exact relation is sufficient | restrained soliflore or deliberate negative space |

The evaluator rejects strategy selection based only on ingredient count,
material prestige, availability, a generic floral base, or an unrelated
wood/amber/musk backplane.

### 5.4 `FloralCouplingContractV1`

Strategies that claim depth through relationships must declare:

- the participating facets or floral voices;
- shared recognizers that prove they belong to the same target;
- directional reinforcement, contrast, or temporal-handoff edges;
- a bridge or reciprocal echo when coupling is claimed;
- collision and masking risks;
- a carrier-matched ablation or alternative arm; and
- identity-retention endpoints.

Merely coexisting in the same formula is not coupling.

### 5.5 `FloralTemporalContourV1`

The contour declares the target state at fixed design windows. The default
software windows are opening, 5 minutes, 30 minutes, 2 hours, 4 hours, and 8
hours; a case may add a 24-hour blotter window when relevant. Each window states
which recognizers, facets, and relationships should remain or transform.

These are hypotheses for evaluation. Modeled temporal frames do not satisfy a
physical observation requirement.

### 5.6 `FloralDosePreparationV1`

When a formula-bound proposal would require less than 10 µL of raw stock, the
compiler must not emit an unmeasurable instruction. It must either:

- bind an existing exact stock solution whose delivered volume is at least
  10 µL; or
- produce an explicit preparation record containing source stock identity,
  concentration basis, carrier, source and carrier quantities, total prepared
  volume, mixing instruction, final stock strength, delivered volume, and
  delivered active amount.

If those fields cannot be completed, the candidate is `HOLD_SUB_10_UL`.

Stock rebasing must preserve active dose unless a dose change is explicitly
declared. Existing concentration and dose-receipt utilities remain the
arithmetic authority; the floral module will not create duplicate dose math.

### 5.7 `FloralDesignResultV1`

The result contains:

- normalized target contract;
- selected strategy or `NO_CHANGE`;
- ideal facets, couplings, and temporal contour;
- current-inventory projection;
- missing-chemical impact ordered by target consequence;
- source-authority and dose-preparation findings;
- native OAV/headspace diagnostic binding;
- zero or one proposed closed experiment;
- blockers and abstentions;
- claim ceiling; and
- all authority flags set explicitly.

It does not contain a beauty score, hedonic score, complexity score, guaranteed
performance, or formula-mutation authorization.

## 6. Component Architecture

### 6.1 Floral compiler

`engine/perception/floral_depth.py` will define the typed contracts and the pure
evaluation function. It receives target and build references plus explicit
facet and relationship declarations. It does not search for ingredients,
mutate formulas, or infer a flower profile from its name.

### 6.2 SolForge adapter

`engine/solforge/floral_adapter.py` will translate a valid floral design result
into the existing Architectural Delta request. It may compile zero or one
highest-priority constant-total experiment. Multiple independent changes cause
a hold rather than a bundled test.

The adapter must preserve the admitted Architectural Delta invariants:

- target and current build remain separate;
- exact inventory is refreshed at execution;
- only one closed comparison is emitted;
- candidate evidence and source hashes remain bound;
- formula mutation and physical execution remain unauthorized; and
- a missing target deficiency returns `NO_AUGMENTATION`.

### 6.3 Explicit accord relations

Floral relations may serialize through the existing accord-graph vocabulary,
but they must be explicitly supplied by the design contract. Generic keyword
inference from `build_functional_graph()` cannot establish reinforcement,
contrast, masking, or temporal handoff for admission purposes.

### 6.4 Evidence and case memory

“Learning” will mean preserving exact, target-scoped evidence, not training a
hidden liking model. A floral observation binding will require the formula,
stock/lot, protocol, schedule, environment, assessor/session, randomization,
and result hashes before an observation can update the same target case.

The first implementation may record and retrieve case-specific findings. It
must not generalize a result across flowers or populations. Cross-floral or
population-level learning requires a separate approved validation protocol and
held-out evaluation. Retired temporal and hedonic learners remain
runtime-unreachable.

### 6.5 Registry isolation

The implementation will add an immutable registry overlay after the current V8
registry. The new module starts as:

```text
module_id: all-floral-depth-compiler
state: FUTURE_CANDIDATE_NOT_VALIDATED
import_path: null
runtime_reachable: false
```

Exact source, test, fixture, and parent-registry hashes will be bound. Existing
registry files and topology tombstones remain unchanged.

## 7. Data Flow

1. Accept the named perfume brief and evidence references.
2. Build and validate `FloralIdentityContractV1` before reading stock into the
   design decision.
3. Declare flower-specific facets and select one primary depth strategy.
4. Validate couplings, omission losses, drift risks, and temporal contour.
5. Bind the accepted ideal target to `TargetFormula` or an exact ideal reference.
6. Refresh current physical inventory and user-authority overlays.
7. Produce CURRENT-INVENTORY mappings and a missing-chemical impact gate without
   rewriting the ideal.
8. Enforce essential-oil/absolute/known-chemical source policy, musk restraint,
   exact concentration basis, active-dose equivalence, and sub-10 µL preparation.
9. Attach native composite-natural OAV and temporal diagnostics only where
   authoritative coverage exists.
10. Select zero or one discriminating constant-total experiment through
    Architectural Delta.
11. Emit the design result with all unsupported physical outcomes as
    `NOT_TESTED` or `HOLD`.
12. If physical observations are later authorized and collected, bind them as
    immutable target-specific evidence. Do not silently promote claims.

## 8. Floral-Specific Guardrails

The compiler fails closed for these conditions:

| Condition | Result |
|---|---|
| Missing named floral subject or realism target | `HOLD_TARGET_INCOMPLETE` |
| Floral material is merely support in a non-floral target | `NOT_APPLICABLE` |
| Inventory determines or rewrites the ideal | `HOLD_TARGET_BUILD_COLLAPSE` |
| DHP/autogenous polarity is forced without flower-specific justification | `HOLD_STRATEGY_UNSUPPORTED` |
| Generic wood, amber, sweetness, or musk is presented as flower depth | `HOLD_EXTERNALIZED_DEPTH` |
| Facet lacks omission loss or discriminating test | `HOLD_DECORATIVE_FACET` |
| Multiple naturals are combined only for prestige or count | `HOLD_NATURAL_KITCHEN_SINK` |
| Opaque FO, FTEC, captive base, or unknown blend enters under current source policy | `HOLD_SOURCE_CLASS` |
| Natural lacks lot identity or composite coverage | quantitative natural OAV `HOLD`; whole natural identity preserved |
| Raw-stock delivery is below 10 µL without a complete dilution record | `HOLD_SUB_10_UL` |
| Stock-strength change alters active dose silently | hard arithmetic failure |
| Character role depends on a sub-threshold diagnostic with no physical test | role remains unproven; no automatic dose increase |
| More than one musk lacks distinct roles and pairwise controls | `HOLD_MUSK_REDUNDANCY` |
| Tonalide, Macrolide, or Musk Ketone lacks the full exception contract | reject from design |
| Physical liking, realism, depth, similarity, performance, or safety is claimed from design/model output | critical failure |
| Candidate or registry bytes drift | runtime unreachable |

Current physical authority overrides stale inventory prose only through an
explicit dated record. As of 2026-08-27, user authority states that Ambrettolide
10% and Ethylene Brassylate are on hand; Cedarwood Virginia and Lemon FCF are
depleted; all tinctures are lost; and a separately sourced material sold as
Magnolia essential oil (White Champi), described by its supplier as *Michelia
alba* flower oil, is on hand. Its exact lot composition, strength, safety, and
composite OAV remain unresolved.

## 9. Musk and Performance Policy

The default is zero or one functionally exact musk. A second musk is allowed
only when it supplies a distinct flower-linked spatial, textural, temporal, or
character-echo role and wins a controlled omission/alternative comparison.

Performance design must be flower-specific. The compiler will ask which
recognizers must carry the opening, heart, and drydown rather than adding a
generic long-lasting base. Low-volatility materials from every category may be
considered, but they must preserve the flower’s identity. A modeled persistence
floor is a diagnostic screen, not evidence that performance is acceptable.

For a physical protocol, the default evaluation records identity, depth,
coherence, liking, drift penalties, and fixed-distance detection at predefined
times. DHP 2025 may be included as a blinded geometry/performance anchor when an
authentic sample is physically available. It is never the realism reference for
a non-iris flower.

## 10. Benchmark and Admission Program

### 10.1 Provider-free gate

Before any external generation, local verification must prove:

- contract schemas and closed enums;
- target/build separation;
- exact source and registry hashes;
- source-class, musk, natural-OAV, active-dose, and sub-10 µL guardrails;
- no runtime import for the candidate;
- deterministic case and request serialization;
- anonymous labels and no answer-key leakage; and
- zero formula, sensory, procurement, safety, or release authority.

No new pipeline script will be created. Existing benchmark and registry
libraries will be extended through library code, fixtures, and tests.

### 10.2 Frozen floral corpus

The benchmark will be staged and relevance-balanced.

**Six-case screen:** one case for each principal mechanism class, including:

1. White Champi autogenous polarity;
2. rose precise simplicity or textural counterpoint;
3. jasmine or tuberose temporal metamorphosis;
4. muguet/freesia atmospheric relief;
5. iris/orris anatomical or petal-root structure; and
6. a bouquet requiring interflower hierarchy without blur.

**Twelve unseen confirmation cases:** coverage must include white floral,
osmanthus, orange blossom/neroli-central, green or aldehydic floral, floral
amber/chypre, and at least one flower-led hybrid. Cases must include missing
chemicals, stale inventory conflict, unknown natural composition, sub-10 µL
dosing, unsupported DHP transfer, precise-simplicity `NO_CHANGE`, and a
performance request that tempts an unsupported claim.

The corpus tests general procedure. It does not freeze ingredient recipes for
each flower.

### 10.3 Arms

Each case uses fresh, isolated, exact-input arms:

1. plain Sol XHIGH;
2. the current installed-authority stack, including admitted Architectural
   Delta;
3. a length-matched no-op/placebo packet; and
4. the installed-authority stack plus the candidate floral compiler.

The candidate is not compared only with the weaker plain baseline. It must add
value beyond what the installed program already supplies.

### 10.4 Scoring

Critical failures are noncompensatory. They include target/build collapse,
unsupported physical claims, invented stock, unmeasurable dosing, unbound
natural OAV, unauthorized source classes, generic chassis substitution, and
runtime promotion before evidence.

Blinded scoring covers:

- named-target fidelity;
- flower-specific depth mechanism;
- relational coherence and restraint;
- temporal and performance testability;
- practical inventory/dilution correctness;
- controlled-comparison quality;
- claim and provenance discipline; and
- clarity without verbosity padding.

The six-case screen passes only with at least four strict wins against each
control, median paired gain of at least five against each control, zero new
critical failures, and no mechanism-class paired median worse than -2 points
against any control.

The twelve-case confirmation passes only with at least eight strict wins
against each control, median paired gain of at least five against each control,
zero new critical failures, no included floral scope with a negative median,
and valid exact receipts. These thresholds are frozen before observing outputs.

### 10.5 Admission

Passing software tests creates a nonruntime candidate, not an admission.
Passing the screen authorizes confirmation, not runtime. Passing confirmation
authorizes a separate immutable registry overlay and minimal runtime adapter
change. The admission receipt must bind model identity, effort, prompts, cases,
responses, judges, rubric, source bytes, registry bytes, and all authority
flags.

Runtime authority remains computational experiment design. Physical liking,
realism, depth, DHP-equivalence, performance, safety, and release remain outside
software admission.

## 11. Other Pending Applications

No module will be bulk-admitted because it once beat plain Sol on selected
cases. The current evidence supports these dispositions:

- Architectural Delta remains the sole admitted complexity runtime module;
- Universal Perceptual Topology, Perfumery Art Topology, and Wood Depth remain
  provenance tombstones after failed screening;
- the Hedonic Preference Learner and Temporal Sensory Ledger remain retired;
- `complexity-experimental-design` has promising associated gains but lacks an
  independent admission result; and
- future hedonic, temporal, and musk modules remain nonruntime until separately
  validated.

The implementation plan will include an exact pending-candidate census. Any
candidate with credible but incomplete evidence receives its own relevance-
gated screen against plain Sol, installed authority, and placebo. It is never
bundled with the floral compiler for admission because one strong module could
hide a weaker one. Existing tombstones are retested only after a bounded repair
at the demonstrated failure locus and with unseen holdouts.

## 12. Planned Files

Initial nonruntime candidate work is expected to touch:

- `engine/perception/floral_depth.py`;
- `engine/solforge/floral_adapter.py`;
- `tests/test_floral_depth.py`;
- `tests/test_solforge_floral_adapter.py`;
- floral benchmark fixtures under `tests/fixtures/`;
- focused benchmark and registry tests; and
- a new immutable complexity-registry overlay.

Existing target, dose, OAV, inventory, Architectural Delta, benchmark, and
registry components should be reused. No new pipeline script, hidden score,
formula mutation route, or parallel orchestration subsystem is planned.

Runtime files are not changed in the candidate stage. If and only if
confirmation passes, a later admission commit may update the current registry
overlay and `engine/solforge/runtime.py` or its narrow adapter dispatch.

## 13. Test Strategy

Implementation will be test-first.

### Unit tests

- every included floral scope parses;
- non-floral support use returns `NOT_APPLICABLE`;
- all depth strategies validate without flower-name defaults;
- DHP/autogenous polarity is optional and requires coupling evidence;
- unused facets are not required;
- decorative facets and generic externalized depth are held;
- precise simplicity returns `NO_CHANGE`;
- source-class restrictions reject opaque materials;
- ideal and current inventory cannot collapse;
- user physical-authority overlays remain explicit;
- natural OAV holds propagate without deleting the natural;
- one-musk and exception policies hold;
- sub-10 µL additions require a complete preparation record; and
- all unsupported authority flags remain false.

### Integration tests

- valid floral results compile through Architectural Delta into no more than one
  closed constant-total experiment;
- exact inventory refresh and stock-strength basis are preserved;
- current-build absence cannot rewrite the ideal;
- accord relationships are explicit rather than keyword-inferred;
- benchmark serialization is deterministic and blinded;
- registry census passes with the candidate runtime-unreachable; and
- admitted runtime output is byte-for-byte unchanged during candidate work.

### Benchmark tests

- frozen case and rubric hashes;
- four-arm common-input equivalence;
- anonymous labels and answer-key separation;
- exact win, median, category, and critical-failure thresholds;
- capture-defect and ambiguous-request tombstones;
- no aggregate admission when one floral scope regresses; and
- admission overlay creation remains impossible without a valid confirmation
  receipt.

Focused tests, Ruff, type checking, and compile checks are required for the
changed surfaces. The quick verifier is appropriate for candidate acceptance;
the full verifier is reserved for a release or merge claim.

## 14. Implementation Stages

1. **Contracts and evaluator** — implement pure floral target, facet, strategy,
   coupling, contour, dose-preparation, and result contracts.
2. **Architectural adapter** — compile zero or one closed experiment through
   the admitted engine.
3. **Registry isolation** — add exact nonruntime overlay and census tests.
4. **Provider-free benchmark corpus** — freeze cases, controls, rubric, and
   deterministic gates.
5. **External screen and confirmation** — run only when exact XHIGH identity,
   isolation, accounting, and duplicate-work gates are valid.
6. **Admission or tombstone** — admit through a separate overlay only on pass;
   otherwise preserve source and receipt as nonruntime provenance.
7. **Pending-candidate reconciliation** — independently evaluate credible
   unadmitted applications without bundling.

Stages 1-4 can be completed locally. Stages 5-7 depend on valid external
execution evidence and cannot be declared complete from code alone.

## 15. Acceptance Criteria

The design is successfully implemented when:

1. every floral-dominant target can be represented without a flower-specific
   hard-coded recipe;
2. the compiler distinguishes soliflore, bouquet, floral family, and flower-led
   hybrid scope;
3. White Champi’s autogenous DHP function is representable without making it a
   universal floral requirement;
4. precise simplicity and `NO_CHANGE` remain first-class outcomes;
5. TARGET/IDEAL cannot be rewritten by CURRENT-INVENTORY;
6. EO/absolute/known-chemical source policy is enforced;
7. every otherwise sub-10 µL raw-stock dose has an explicit measurable
   preparation or is held;
8. naturals retain whole-material identity and composite-OAV claim limits;
9. OAV, modeled headspace, and temporal diagnostics cannot become beauty,
   liking, realism, similarity, depth, or performance truth;
10. default musk use is zero or one exact material and exceptions remain
    controlled;
11. no candidate runtime path exists before exact benchmark admission;
12. the new compiler beats plain Sol XHIGH, installed authority, and placebo
    under the frozen screen and confirmation thresholds before activation;
13. every other pending application is admitted, retained, retired, or held by
    its own exact evidence rather than a bundle inference; and
14. the program-integration and publish branches remain unmodified by this
    isolated worktree.

## 16. Explicit Holds

- No procurement is authorized.
- No physical compounding is authorized.
- No formula is accepted for skin use or release by this design.
- White Champi composition, composite OAV, IFRA/allergen status, safety,
  realism, liking, performance, and DHP-equivalent depth remain unresolved.
- “All florals” describes representational coverage, not proof that one model or
  formula succeeds physically for all flowers.
- Better-than-XHIGH and runtime-admission status remain `NOT_TESTED` until exact
  blinded benchmark receipts exist.
