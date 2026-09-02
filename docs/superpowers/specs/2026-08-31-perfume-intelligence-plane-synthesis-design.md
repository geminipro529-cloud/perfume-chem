# Perfume Intelligence Plane Synthesis — Design and Execution Contract

**Status:** DRAFT; NON-RUNTIME; NOT BENCHMARKED; NOT EMPIRICALLY VALIDATED
**Date:** 2026-08-31
**Scope:** target-first perfume design intelligence for every perfume family, with
special depth for floral construction and evidence-scoped hedonic learning
**Authority:** architecture and experiment-design hypotheses only

This document does not authorize a formula, physical compounding, purchasing,
safety clearance, sensory similarity, liking, stability, performance, or release.
Modeled OAV, vapor pressure, graph connectivity, recipe precedent, agreement among
agents, and benchmark scores remain diagnostics rather than observed smell.

## 1. Outcome

Perfume-Chem needs a synthesis brain, not a larger pile of recipes and scores.
The intended system must:

1. translate an explicit perfume request into a target identity and a changing
   whole-perfume shape;
2. reason over several native architectural planes without flattening them into
   one scalar score;
3. assemble candidate functions and ingredients from target-linked capabilities,
   not from copied donor formulas;
4. treat mixture interaction, time, concentration, inventory, evidence, and
   assessor preference as separate but related sources of uncertainty;
5. support all major perfume families and a deep floral lattice rather than a
   single generic `floral` bucket;
6. learn hedonic preferences only from scoped, blinded, participant-linked
   observations;
7. emit alternatives, tensions, counterfactuals, and experiments rather than a
   false universal beauty verdict; and
8. earn runtime admission only by beating a frozen plain-Sol control without
   critical regressions.

## 2. Evidence boundary

Primary human-mixture evidence makes a binary recipe/gate architecture unsafe:

- Human subjects have difficulty identifying more than two components in many
  mixtures, while qualities can remain present without component recognition.
  This supports an odor-object layer distinct from a material-list layer.
  See Jinks and Laing, 2001, DOI `10.1016/S0031-9384(00)00407-8`.
- Mixture quality can be elemental, configural, overshadowed, or ratio-dependent;
  no single composition rule is universal. See Thomas-Danguin et al., 2014,
  DOI `10.3389/fpsyg.2014.00504`, and Kay et al., 2005,
  DOI `10.1093/chemse/bji011`.
- Binary perceived intensity can show asymmetric masking and synergy and requires
  component-specific interaction parameters. See Thomas-Danguin and Chastrette,
  2002, DOI `10.1016/S1631-0691(02)01485-3`.
- Binary-mixture pleasantness is often intermediate and intensity-weighted, but
  that model depends on psychophysical measurements of the separated components
  and does not establish finished-perfume beauty. See Lapid et al., 2008,
  DOI `10.1093/chemse/bjn026`.
- In 222 binary mixtures made from 72 food odorants, the strongest component
  described whole-mixture intensity in most tested cases, masking was common,
  and reported synergy was rare. This supports separate strongest-component,
  masking, and residual hypotheses under the tested ratio/matrix/panel—not a
  permanent interaction graph. See Ma et al., 2021,
  DOI `10.1016/j.foodchem.2021.129483`.
- Dynamic sensory methods can expose time-local drivers of liking that an overall
  endpoint hides. The available evidence is largely food-sensory rather than
  perfume-specific, so it authorizes a measurement contract, not perfume
  predictions. See Ares et al., 2017, DOI `10.1016/j.foodres.2016.12.016`.
- Many intensity-equalized components can converge perceptually rather than become
  richer. See Weiss et al., 2012, DOI `10.1073/pnas.1208110109`.

Consequences for implementation:

- component count is never depth, richness, or beauty evidence;
- fixed material valences are priors with no mixture-hedonic authority;
- concentration and temporal window are part of every sensory hypothesis key;
- predicted headspace is never substituted for observed time-resolved perception;
- higher-order emergence is a residual to test after linear/dominance baselines;
- conflicts are preserved as distributions or separate fronts, not averaged away.

Two existing local evidence contracts remain intact rather than being rewritten:

- `docs/research/PERFUME_CHEM_MA2021_BINARY_MIXTURE_BASELINE_BENCHMARK_2026-08-12.md`
  is a source-internal baseline/falsification receipt. It does not establish
  independent transportability, high-order perfume behavior, or sensory truth.
- `docs/research/PERFUME_CHEM_C0_SENSORY_PANEL_CONTRACT_2026-08-09.md`
  provides strict blinded observation and panel-quality planning contracts. Its
  current state is empirical `HOLD`; its hashes prove bytes, not that a study
  occurred or that any perfume succeeded.

## 3. Existing capabilities to retain, quarantine, or replace

### Reuse only as governed, admission-aware primitives

- `engine/perception/construction_complexity.py`: useful authority-labeled
  construction axes and explicit UNKNOWN states, but the live registry classifies
  its current module generation as retired. It is a reference implementation,
  not an admitted runtime dependency.
- `engine/perception/perceptual_topology.py` and
  `engine/perception/perfumery_art_topology.py`: useful target-first functions,
  layers, anti-collapse rules, separate endpoints, hierarchy, composition
  operators, constant-total comparisons, and OAV firewall. Their live v2 registry
  state is `FUTURE_CANDIDATE_NOT_VALIDATED`, so adapters must preserve that state.
- `engine/preference.py`: useful scoped pairwise preference fitting, assessor
  heterogeneity, order-effect detection, and abstention on inadequate data. It is
  an evidence-only/future candidate, not a current hedonic runtime authority.
- `engine/sensory/ledger.py`: useful participant- and time-linked observations
  after the outstanding type/test and persistence boundaries are repaired. It is
  evidence-only/nonruntime under the current admitted Cypress scope.
- `engine/sensory/temporal_observations.py`: useful observation contracts, but its
  registered module generation is retired and must not be reactivated merely by
  importing it.
- `engine/optimization/mixture_design.py` and `engine/optimization/selection.py`:
  constrained candidate generation and multi-objective selection.
- `engine/graphs/accord_graph.py`: relation representation, after every edge gains
  evidence class, scope, direction, concentration domain, and authority ceiling.
- inventory identity, stock, target, evidence, build, bottle, analytical, and
  sensory ledgers as separate states.

Source availability, direct imports elsewhere in the repository, and passing
unit tests do not override registry state. Every adapter must report both the
source module's state and the adapter's own admission state.

### Quarantine as priors or historical controls

- `engine/hedonic_model.py`: fixed molecule valences and formula-level harmony
  cannot produce a current perfume beauty score. Preserve only as an explicitly
  labeled historical prior/control. It is still imported by
  `engine/optimizer/scoring.py`, `engine/data_spine/migrate.py`, and a verification
  script, so quarantine requires a deliberate compatibility plan rather than an
  unsupported claim that it is already inactive.
- `engine/family_scorer.py`: statements such as “flowers = beauty” and static
  family hedonic weights are design prose, not evidence. They must not gate or
  optimize a formula.
- `engine/knowledge/accord_library.py` and
  `engine/knowledge/soliflore_structures.py`: hard-coded ratios described as
  verified must be treated as provenance-bearing historical hypotheses unless
  exact source, matrix, concentration, inventory identity, and sensory evidence
  are attached.
- supplier prose, commercial note pyramids, unmeasured reference reconstructions,
  old formulas, and chat/task claims: evidence leads only.
- legacy formula prose that assigns receptor adjacency, pheromone channels,
  thermoreceptor persistence, fixed synergy ratios, or multi-day skin behavior
  without exact primary-source and stock-isomer binding is unsupported historical
  content. It must never populate the biological, temporal, hedonic, or
  performance planes merely because the formula file exists.
- committed Cypress Harmonic modules: retain their exact `c89e6a87...` bounded
  admission for CYP-02 computational architecture only. They do not constitute a
  generic whole-perfume runtime and grant no sensory, hedonic, physical, safety,
  stability, compounding, purchase, or release authority.

### Missing integration capabilities

1. A typed plane packet and uncertainty vocabulary shared across modules.
2. A target-language compiler that keeps name, brief, exclusions, reference
   evidence, desired transformations, and ideal-versus-build distinction intact.
3. A capability ontology for materials and systems that separates identity,
   odor facets, physical behavior, structural function, contextual role,
   evidence scope, stock state, and uncertainty.
4. A floral morphology lattice that models flower-specific facets and
   transformations instead of selecting one canned soliflore recipe.
5. An accord hypothesis engine that proposes relational systems, not stored
   recipes, and requires omission/recombination evidence for admission.
6. A mixture-perception hypothesis layer with linear, dominance, suppression,
   masking, and configural alternatives.
7. A temporal transformation planner that represents subject continuity and
   handoffs, not only evaporation curves or top/heart/base bins.
8. A spatial/compositional plane connecting focus, width, density, edge, texture,
   contrast, shadow, negative space, projection field, and residue identity.
9. A hedonic platform that keeps liking, target fidelity, coherence, interest,
   comfort, aversion, defect intensity, and preference scope separate.
10. A conflict-preserving synthesis engine that returns Pareto fronts,
    unresolved tensions, and minimum-information experiments.
11. A target-native ingredient assembler that searches capabilities and
    nonredundant relations without importing donor perfume identity.
12. A benchmark/admission layer comparing integrated intelligence to plain Sol,
    a length-matched placebo, and ablated variants on frozen cases.

## 4. Plane model

Each plane returns a `PlaneAssessment`, never an unqualified PASS:

```text
PlaneAssessment
  plane_id
  target_scope
  temporal_scope
  matrix_scope
  claims[]
  support_intervals[]
  conflicts[]
  unknowns[]
  failure_modes[]
  proposed_experiments[]
  provenance_refs[]
  authority_ceiling
  freshness_hashes[]
```

The planes are:

1. **Identity plane** — the named subject, family neighborhood, reference claims,
   forbidden drift, protected recognizers, and intended abstraction level.
2. **Morphology plane** — facets of the subject and their internal relations.
   For florals: petal, pollen/stamen, nectar/honey, green stem/leaf, aqueous/dew,
   spice, fruit, tea, wax, lactone/cream, indolic/animalic, earth/root/rhizome,
   and senescent/dried facets as target-appropriate—not a required checklist.
3. **Function plane** — subject, support, bridge, contrast, shadow, lift,
   diffusion, fixation, texture, residue, and deliberate omission.
4. **Relation/accord plane** — directed or n-ary support, bridge, contrast,
   shadow, handoff, recurrence, opposition, suppression/takeover risk, and
   omission loss among target functions or facets. Every relation binds exact
   claim IDs, scope, evidence, uncertainty, provenance, and authority; historical
   accord ratios remain quarantined priors rather than graph truth.
5. **Mixture plane** — weighted-component baseline, strongest-component baseline,
   masking/suppression, unmasking, and configural residual hypotheses.
6. **Temporal plane** — opening, 5m, 30m, 2h, 4h, 8h, and 24h hypotheses plus
   within-sniff onset/peak/offset when measured; tracks transformed subject
   continuity and generic-residue failure.
7. **Spatial-composition plane** — focus, width, density, aperture, edge, distance,
   texture, contrast, shadow, air, projection field, and residue.
8. **Physicochemical plane** — active dose, ppm, composite-natural OAV,
   volatility, activity coefficient, matrix, diffusion, and uncertainty; this
   plane is diagnostic and cannot claim perception.
9. **Biological/sensitivity hypothesis plane** — exact molecule, stereochemistry,
   product-basis identity, receptor or genotype evidence, specific-anosmia risk,
   and population-transfer limits. Receptor diversity is not perceptual
   nonredundancy, mixture quality, target fit, or liking evidence. Commercial
   trade names and opaque products cannot inherit research-isomer mechanisms.
10. **Hedonic plane** — participant- and criterion-scoped preferences, uncertainty,
   heterogeneity, order effects, concentration, time, and context.
11. **Inventory/build plane** — exact user stock, basis, carrier, availability,
   quantitative holds, substitutions, carrier displacement, aliquot limits, and
   TARGET/IDEAL versus CURRENT-INVENTORY BUILD.
12. **Evidence/authority plane** — source class, directness, independence,
    provenance, contradictions, claim scope, and promotion ceiling.
13. **Experiment plane** — the smallest controlled comparison that can resolve a
    decision-relevant unknown.

Hard arithmetic, identity, inventory, safety, and provenance gates remain hard.
Design planes remain graded and conflict-preserving.

## 5. Floral intelligence lattice

### 5.1 Subject families

The lattice must cover at least:

- rose: tea, fresh garden, dewy, peppery, fruity/damask, dark, jammy,
  green-stemmed, leathery, mineral, and dried/potpourri expressions;
- jasmine: luminous, tea-like, green, fruity, narcotic, creamy, indolic, and
  nocturnal expressions;
- tuberose: green/camphoraceous, creamy/lactonic, solar, mentholic, rubbery,
  animalic, and narcotic expressions;
- muguet/lily: watery, green, airy, soapy, waxy, pollen, and stem expressions;
- orange blossom/neroli: citrus-flower, leafy, honeyed, indolic, waxy, and
  solar expressions;
- iris/orris/violet: petal, powder, cosmetic, root/rhizome, carrot, suede,
  mineral, cool, buttery, woody, and concrete-like contrasts;
- magnolia/champaca: lemony, watery, waxy, creamy, tea, fruity, pollen, spicy,
  humid, green, and shadowed expressions;
- ylang/gardenia/frangipani: banana-fruity, creamy, solar, waxy, green,
  lactonic, mushroomy, indolic, and tropical expressions;
- osmanthus: apricot, tea, leather/suede, floral, honey, and hay facets;
- mimosa/cassie/acacia: pollen, powder, honey, green, almond, and suede facets;
- narcissus/hyacinth/lilac/carnation/peony/linden: flower-specific green,
  spicy, watery, honeyed, phenolic, pollen, and textural systems;
- bouquets and hybrids: relationships among subjects must declare hierarchy,
  overlap, bridge, contrast, and anti-takeover constraints.

This is an ontology of possible target facets, not a demand to include more
materials. A convincing flower may use fewer rows when each relation is doing
target-specific work.

### 5.2 Floral construction stages

1. Parse the requested flower and abstraction level.
2. Declare the protected recognizer set and prohibited caricatures.
3. Choose the minimum subject facets needed for identity.
4. Describe the intended transformations over time.
5. Add only target-linked bridges, contrast, shadow, texture, and projection
   functions.
6. Generate capability candidates independently of inventory.
7. Project the ideal onto exact inventory without redefining the target.
8. Produce nonredundancy, omission, ratio, and takeover tests.
9. Keep predicted and observed outcomes in separate ledgers.

### 5.3 Required floral failure detectors

- generic floral-heart substitution;
- canned rose/jasmine/muguet ratio reuse without target evidence;
- white-floral takeover;
- fruit/citrus foreground disconnected from the flower;
- sweet/musk comfort substituted for hedonic development;
- anonymous wood-musk-amber drydown;
- petal-to-base discontinuity;
- indole, lactone, salicylate, ionone, aldehyde, or green-stem caricature;
- material-count inflation;
- natural-product label treated as a monomolecule;
- prestige material used as target-fit evidence;
- modeled persistence used as observed flower continuity.

## 6. Hedonic platform

The system must not expose a universal `hedonic_score` as truth. It should
provide distinct evidence-scoped views:

1. **Material prior view** — literature or panel priors at an exact concentration
   and matrix; never mixture beauty.
2. **Mixture expectation view** — linear/intensity-weighted and dominance
   baselines with uncertainty.
3. **Interaction residual view** — observed deviation from baselines; labels
   possible suppression, enhancement, or emergence without causal overclaim.
4. **Temporal liking view** — participant-linked liking/aversion by time window.
5. **Criterion-specific preference view** — liking, comfort, sensuality,
   elegance, interest, naturalness, target fidelity, depth, richness, and
   coherence remain separate criteria.
6. **Population view** — assessor clusters, expertise, anosmia/low sensitivity,
   day, order, and carryover are preserved.
7. **Decision view** — a Pareto set with confidence intervals, explicit
   dominated candidates, and unresolved tradeoffs.

No averaging across criteria is permitted unless the user explicitly supplies
criterion weights for that decision and the output retains all native values.

## 7. Synthesis logic

The synthesis engine operates in five passes:

### Pass A — compile the target

Produce a versioned `TargetIntent` with identity, abstraction, exclusions,
required transformations, protected functions, reference evidence tiers, and
separate ideal/build IDs.

### Pass B — generate plane hypotheses

Each specialized module emits candidates and counterfactuals. Modules cannot
write formulas or promote their own authority.

### Pass C — harmonize without voting

Combine compatible support intervals; preserve incompatible scopes and explicit
conflicts. Do not count module agreement as evidence. A minority module with
strong direct evidence outranks repeated heuristic agreement within its scope.

### Pass D — construct a Pareto frontier

Candidates are compared on target fidelity, recognizer integrity, transition
continuity, nonredundancy, uncertainty burden, inventory executability, safety
screen state, experimental cost, and scoped hedonic evidence. No candidate is
called best unless the decision rule is explicit.

### Pass E — choose the next information gain

If evidence cannot discriminate candidates, propose the smallest constant-total
ratio sweep, omission/recombination, matched-carrier comparison, or temporal
sensory observation that resolves the highest-value uncertainty.

## 8. Proposed module package

New code should live under `engine/formulation_intelligence/` and compose current
primitives instead of creating another pipeline script:

| Module | Responsibility | Initial authority |
|---|---|---|
| `contracts.py` | typed intervals, scoped claims, plane packets, conflicts, authority ceilings | structural only |
| `target_compiler.py` | request-to-target intent with ideal/build separation | design only |
| `family_architecture.py` | cross-family identities, morphologies, transformations, recognizers, and drift boundaries without recipes | design only |
| `capability_ontology.py` | ingredient/system capabilities, contextual roles, exclusions, and evidence-qualified nonredundancy | hypothesis only |
| `floral_lattice.py` | flower facets, transformations, failure modes, test templates | design only |
| `mixture_hypotheses.py` | linear, dominance, masking, suppression, emergence alternatives | hypothesis only |
| `temporal_architecture.py` | subject continuity, handoffs, delayed reveal, residue identity | design only |
| `spatial_architecture.py` | focus, width, density, aperture, edge, distance, texture, contrast, shadow, air, field, and residue | design only |
| `biological_sensitivity.py` | exact-molecule/receptor/genotype hypotheses and specific-anosmia/population-transfer firewall | evidence limited |
| `plane_synthesis.py` | scope-aware harmonization and conflict preservation | structural only |
| `hedonic_platform.py` | scoped observations, priors, residuals, cluster-aware preferences | evidence limited |
| `candidate_selector.py` | target-linked candidate capability matching with inventory/identity/evidence holds | proposal only |
| `accord_graph.py` | relational accord/function graph, interfaces, bridges, contrasts, omission losses, and counterfactuals | design only |
| `candidate_assembler.py` | target-native functional assemblies and non-scalar Pareto frontier | proposal only |
| `inventory_projection.py` | immutable TARGET/IDEAL to exact-stock CURRENT-BUILD projection with quantitative holds | proposal only |
| `whole_perfume_assembler.py` | versioned whole-perfume plane blueprint and alternatives without a dose formula | proposal only |
| `experiment_selector.py` | minimum-information controlled comparisons | protocol only |
| `adapters.py` | read-only adapters to current topology, preference, inventory, OAV, sensory, and optimization modules | no authority gain |
| `admission.py` | frozen benchmark and module state transitions | admission governance |

The package must not import hard-coded accord or soliflore ratios by default.
Historical recipe modules may be accessed only through a quarantined adapter
that labels them `HISTORICAL_PRIOR_NOT_TARGET_EVIDENCE`.

### 8.1 Performance contract

- The structural contracts and synthesis hot path use the Python standard
  library only. They must not import Torch, sentence transformers, FAISS, plotting,
  PubChem/network clients, the formula parser, or full pipeline state at import.
- Plane packets are content-addressed. Unchanged target, inventory, evidence, and
  module hashes reuse their prior normalized packet; a changed inventory hash
  invalidates only the build/executability projection, not the ideal target.
- Adapters are lazy and explicit. Opening a target request does not load every
  recipe, formula, knowledge package, or historical receipt.
- Runtime admission binds the complete transitive import closure, including
  package `__init__.py` side effects and data/config dependencies. Hashing only
  declared top-level modules is insufficient; an unbound, retired, or
  research-only dependency anywhere in the normal import path forces `HOLD`.
- Claim/provenance normalization is deterministic and at most `O(n log n)` for
  the number of supplied assertions; repeated heuristic packets are canonicalized
  before synthesis.
- Cross-family and material capability indexes are versioned artifacts built from
  admitted records, not recomputed by scanning the repository on every request.
- Performance admission is separate from design-quality admission. Measure cold
  import, warm packet synthesis, incremental one-plane recomputation, peak memory,
  and large-packet scaling against the predecessor. A faster unsafe answer fails;
  a better but pathologically slow system also remains nonruntime.

## 9. Test and benchmark architecture

### 9.1 Deterministic contract tests

- serialization and hash stability;
- scope mismatch never merges silently;
- conflicts survive round-trip;
- unknowns are not converted to zero;
- authority never increases through composition;
- ideal target cannot be redefined by inventory;
- held stock cannot become quantitatively executable;
- old recipes cannot enter the default candidate path;
- fixed hedonic priors cannot become a final mixture score.
- every runtime entrypoint's generated transitive import closure matches its
  hash-bound admission manifest and contains no retired/research-only dependency.

### 9.2 Metamorphic tests

- permuting input module order does not change the frontier;
- duplicating a heuristic module does not increase confidence;
- adding redundant ingredients cannot increase complexity;
- changing only inventory availability changes the build projection but not the
  ideal target;
- replacing an exact stock with ambiguous basis forces quantitative HOLD;
- reversing a temporal sequence changes transition hypotheses while preserving
  mass arithmetic;
- removing a bridge produces a declared discontinuity hypothesis;
- filling deliberate negative space does not automatically improve any endpoint.

### 9.3 Cross-family adversarial corpus

The frozen corpus must include at least:

- rose soliflore, narcotic white floral, translucent muguet, iris contrast,
  magnolia/champaca, and multi-floral bouquet;
- citrus cologne, aromatic fougere, green, chypre, leather, woody, amber,
  gourmand, marine/ozonic, musk, incense/resin, tobacco, and fruit-centered cases;
- named-reference and concept-only briefs;
- sparse versus dense solutions;
- unavailable, ambiguous, diluted, natural-composite, and carrier-conflicted stock;
- attractive numeric decoys that fail identity;
- target-faithful candidates with modest numeric scores;
- user sensory reports that contradict modeled headspace;
- heterogeneous participant preferences and order-confounded trials.

### 9.4 Admission arms

For every module and for the integrated system:

1. plain Sol 5.6 at the frozen reasoning level;
2. integrated plane packet;
3. length-matched placebo guidance;
4. relevant ablations;
5. safe countercases and critical traps.

Admission requires blinded judging, exact prompt/output hashes, independent
scorers, no critical authority or safety regression, superiority to both
controls, and held-out cross-family performance. Until then the module state is
`FUTURE_CANDIDATE_NOT_VALIDATED`.

The existing Cypress benchmark is evidence for a narrow predecessor only. Its
rendered prompts explicitly expose `INTEGRATED`, `PLAIN`, and `PLACEBO` condition
labels; the receipt does not bind a blinded scorer identity or complete execution
provenance; and all six cases remain inside the Cypress neighborhood. Its reported
wins therefore cannot admit this generic plane architecture. The new benchmark
must anonymize conditions before judging, keep scorer-only answer keys out of
every arm, bind model/reasoning/execution receipts, and include held-out families
and florals that cannot be solved by carrying Cypress or Magnolia/Orris context.

The Cypress V6 registry also does not bind an exact executable import closure.
Normal imports of `engine.solforge.harmonic_runtime` and `engine.perception.*`
execute package initializers and direct dependencies absent from V6
`source_bindings`; those paths include retired modules, and
`depth_family_adapters.py` directly imports `floral_depth.py` even though V6
marks that library `RESEARCH_ONLY` with no runtime import path. The V6 loader
verifies declared bindings, not every transitively executed source. Therefore
generic Cypress runtime admission is `HOLD`; only its exact CYP-02 behavioral
results may be retained as bounded predecessor evidence until a recursive,
hash-bound closure and isolated import test exist.

## 10. Execution plan

### Phase 0 — census and leases

- finish exact worktree/task registry;
- hash every candidate source and record dirty overlaps;
- identify the sole writer for each shared semantic contract;
- preserve all user-owned uncommitted bytes.

### Phase 1 — evidence and omission map

- produce a canonical capability matrix across current modules/worktrees;
- classify every surface as admitted, guardrail, shadow, future candidate,
  historical prior, unsupported, or retired;
- identify missing contracts, tests, deserializers, ledgers, and call sites.

### Phase 2 — foundational implementation

- implement `contracts.py` and `plane_synthesis.py` first;
- write fail-closed tests before adapters;
- do not connect to runtime or formulas.

### Phase 3 — floral and mixture intelligence

- implement the cross-family architecture ontology, floral lattice, and
  target-native capability matching;
- implement mixture alternatives and failure detectors;
- import only worktree concepts whose exact files, hashes, tests, provenance,
  authority ceilings, and compatibility are accepted.

### Phase 4 — temporal and hedonic intelligence

- implement transformed-subject continuity and residue identity;
- implement spatial composition and the biological/sensitivity evidence
  firewall without receptor-mechanism inheritance from trade names;
- bind sensory observations and scoped preferences;
- keep fixed priors and unobserved simulations quarantined.

### Phase 5 — candidate assembly and experiments

- build target-linked candidate selection, relational accord graphs,
  nonredundant functional assemblies, and Pareto frontiers;
- project ideal assemblies into exact-stock current builds without allowing
  inventory to rewrite the target, then assemble versioned whole-perfume plane
  blueprints without dose formulas;
- select controlled comparisons when evidence is insufficient;
- emit proposals, never physical instructions.

### Phase 6 — verification and admission

- focused tests, type checks, metamorphic tests, cross-family corpus, and
  integration tests;
- quick then full project verification when the worktree permits;
- execute the frozen benchmark against plain Sol and placebo;
- admit only proven improvements and retain failures as provenance tombstones.

## 11. Initial acceptance criteria

The first implementation milestone is acceptable only when it:

1. introduces no runtime formula changes;
2. has no dependency on external model providers;
3. preserves every authority ceiling through composition;
4. represents all thirteen independent planes;
5. preserves contradictions and scope-specific uncertainty;
6. supports the floral lattice without importing recipe ratios;
7. produces a deterministic Pareto frontier and experiment proposal;
8. has targeted, metamorphic, and adversarial tests;
9. remains unadmitted until the frozen benchmark completes; and
10. leaves current dirty overlapping paths untouched.

## 12. Open decisions to resolve from live manifests

- whether the Cypress Harmonic Synthesis primitives should be adapted or kept as
  an independent admitted subsystem;
- whether the dirty `3289` floral-depth modules satisfy whole-module manifest,
  provenance, authority, and test requirements;
- whether the `6992` reference/temporal gates are generic enough for a read-only
  adapter without importing SUKHUM identity;
- which historical knowledge packages contain reusable theory versus donor
  formula contamination;
- whether current benchmark infrastructure can be safely extended or requires a
  separate, frozen v2 corpus;
- which canonical writer owns each new package path after the lease census.
