# Perfume Intelligence Plane Synthesis — Implementation and Admission Plan

**Status:** ACTIVE; PARTIALLY IMPLEMENTED; NON-RUNTIME; BENCHMARK HOLD
**Date:** 2026-08-31
**Owner:** master coordinator `/root`
**Governing design:**
`docs/superpowers/specs/2026-08-31-perfume-intelligence-plane-synthesis-design.md`

This plan implements the complete requested formulation-intelligence system. It
does not authorize a dose formula, inventory mutation, physical compounding,
purchase, observed smell, liking, similarity, performance, safety, stability,
or release. Every worker result remains untrusted until the parent verifies its
live bytes, hashes, contracts, tests, provenance, and authority ceiling.

## 1. Non-negotiable operating constraints

1. Use only true OpenAI Codex-native child agents for hidden worker lanes.
   Worktrees, shell processes, plugins, forks, and peer tasks are not subagents.
2. Preserve every dirty worktree and uncommitted byte. No reset, deletion,
   merge, push, or silent conflict resolution is in scope.
3. One writer owns a path or semantic contract at a time.
4. Keep `TARGET / IDEAL` independent of `CURRENT-INVENTORY BUILD`.
5. Do not rewrite historical formulas or rebase their embedded diagnostics.
6. Do not create new pipeline scripts.
7. OAV/headspace remains a physical screening hypothesis, never percent
   perceived contribution, observed smell, target fit, liking, or beauty.
8. Naturals remain composite mixtures with source/lot/composition uncertainty;
   they cannot be treated as monomolecular graph nodes for sensory inference.
9. Complexity means target-linked relations, temporal reveal, contrast,
   transformation, negative space, and hedonic possibility—not ingredient count.
10. Runtime admission requires a frozen blinded benchmark against plain Sol and
    a complete hash-bound transitive import closure.

## 2. End-state dependency map

```text
verified evidence + exact target request + exact inventory authority
                              |
                    target_compiler.py
                              |
          +-------------------+-------------------+
          |                   |                   |
 family_architecture.py  floral_lattice.py  capability_ontology.py
          |                   |                   |
          +----------+--------+---------+---------+
                     |                  |
             accord_graph.py     candidate_selector.py
                     |                  |
          +----------+------+-----------+------------------+
          |                 |                              |
 mixture_hypotheses.py temporal_architecture.py spatial_architecture.py
          |                 |                              |
          +----------+------+------------------------------+
                     |
          biological_sensitivity.py
                     |
              hedonic_platform.py
                     |
             plane_synthesis.py
                     |
             candidate_assembler.py
                     |
             inventory_projection.py
                     |
          whole_perfume_assembler.py
                     |
             experiment_selector.py
                     |
            read-only adapters.py
                     |
          frozen admission benchmark
```

The graph is not a scalar pipeline. Each module emits its native
`PlaneAssessment`; synthesis preserves incompatible scopes, criteria, unknowns,
and conflicts. Downstream nodes may narrow authority but never raise it.

## 3. Current authoritative state

### Completed and parent-verified

- `contracts.py`, `plane_synthesis.py`, package exports, and focused tests.
- Thirteen plane IDs, including the parent-corrected
  `biological_sensitivity` plane and the separately audited first-class
  `relation`/accord plane.
- Exact target/temporal/matrix scopes, immutable records, deterministic hashes,
  explicit UNKNOWN, native Pareto criteria, non-voting exact-scope synthesis,
  duplicate-heuristic non-amplification, conflict preservation, and hard-false
  downstream authority flags.
- Focused parent verification: 9 tests passed; Ruff clean; Mypy clean.

### Active native implementation lanes

- `/root/floral_lattice_ultra`: exclusive new floral lattice and focused tests.
- `/root/mixture_temporal_ultra`: exclusive new mixture/temporal modules and
  focused tests.
- `/root/architecture_critic_ultra`: read-only whole-system/admission audit.

### Completed evidence lane awaiting parent synthesis

- `/root/primary_research_ultra`: primary human-mixture, floral, temporal,
  hedonic, heterogeneity, calibration, and standards evidence matrix.

### Read-only user-owned peer evidence tasks

- Floral evidence: `01a0574f-8748-7130-80eb-a474ec40a4e8`.
- Hedonic evidence: `01a0574f-cbde-7bd0-a71e-5fe1f42a34c4`.
- Benchmark corpus: `01a05750-1cb6-7010-ab29-084f6442aeb9`.

These are peers, not subagents. Their outputs are leads only.

## 4. Work packages and acceptance gates

### WP-00 — Census, leases, and preservation

**Artifacts**

- `docs/governance/perfume_intelligence_worktree_registry_20260831.md`
- current worktree/task/branch/HEAD/dirty/inventory registry
- explicit semantic ownership table

**Done when**

- every known worktree has a verified path, branch/detached state, HEAD, dirty
  count, inventory hash, owner, readiness, and overlap note;
- active Cypress and 6992 tasks retain sole ownership of their leased dirty
  paths;
- no worktree is merged, deleted, pruned, reset, or overwritten.

### WP-01 — Evidence and authority ledger

**Inputs**

- primary research child packet;
- the three read-only peer evidence packets;
- existing Ma-2021 binary-mixture benchmark;
- existing C0 sensory-panel contract;
- current inventory and source-authority governance.

**Deliverables**

- source matrix keyed by DOI/stable URL, tested population, endpoint, mixture,
  concentration, matrix, time, protocol, limitations, and exact `may authorize`
  / `cannot authorize` fields;
- explicit distinction among physical model, instrumental observation, human
  perception, target fit, preference, and release authority;
- contradictions and missing evidence remain first-class records.

**Gate**

- no claim is promoted from an abstract/title alone;
- unverified panel size or method is `UNKNOWN`;
- preprints are provisional and cannot establish admission defaults.

### WP-02 — Target compiler

**Paths**

- `engine/formulation_intelligence/target_compiler.py`
- `tests/test_formulation_intelligence_target_compiler.py`

**Contracts**

- immutable `TargetIntent`, `IdealTargetId`, and separate `BuildProjectionId`;
- named subject, family neighborhood, abstraction, expression, exclusions,
  protected recognizers, forbidden drift, transformations, temporal requests,
  matrix/context, criterion vocabulary, and evidence tier;
- unresolved explicit brief fails closed rather than becoming `generic` or
  `not requested`;
- inventory cannot mutate the ideal target.

**Tests**

- named reference, concept-only, hybrid, sparse, and deliberately incomplete
  briefs;
- case/order normalization without semantic flattening;
- inventory metamorphism changes only build identity;
- no formula/material/default-ratio output;
- deterministic serialization/hash and all authority false.

### WP-03 — Cross-family architecture ontology

**Paths**

- `engine/formulation_intelligence/family_architecture.py`
- `tests/test_formulation_intelligence_family_architecture.py`

**Coverage**

- floral, citrus/cologne, aromatic/fougere, green, chypre, leather, woody,
  amber, gourmand, marine/ozonic, musk, incense/resin, tobacco, fruit-centered,
  aldehydic, powdery/cosmetic, tea, mineral, and justified hybrids;
- identity, morphology, temporal transformations, spatial shape, protected
  recognizers, forbidden drift, deliberate omissions, and adversarial decoys;
- no family is a canned ratio or fixed ingredient list.

**Gate**

- a new family packet is structural until cross-family benchmark admission;
- a generic family cannot pass named-reference or explicit-brief identity.

### WP-04 — Floral morphology lattice

**Paths**

- `floral_lattice.py` and focused test file under active child lease.

**Coverage**

- rose; jasmine; tuberose; muguet/lily; orange blossom/neroli; iris/orris/violet;
  magnolia/champaca; ylang/gardenia/frangipani; osmanthus; mimosa/cassie;
  narcissus, hyacinth, lilac, carnation, peony, linden; bouquets and hybrids;
- optional petal, pollen, nectar, stem, leaf, dew, spice, fruit, tea, wax,
  lactone, indole, earth/rhizome, senescence, shadow, and air facets;
- no facet-count reward and no generic white-floral template.

**Gate**

- catches generic floral heart, takeover, caricature, disconnected fruit,
  anonymous drydown, prestige-as-fit, natural-as-monomolecule, and modeled
  persistence-as-observation.

### WP-05 — Condition-bound mixture and temporal hypotheses

**Paths**

- `mixture_hypotheses.py`, `temporal_architecture.py`, and focused tests under
  active child lease.

**Contracts**

- weighted-component, strongest-component, masking, suppression, unmasking,
  and configural-residual alternatives stay separate;
- interaction key binds component set, active concentration/ratio, matrix,
  delivery, time, population/assessor, endpoint, and protocol;
- opening, 5m, 30m, 2h, 4h, 8h, and 24h remain explicit windows;
- predicted physical evolution is separate from observed participant evidence;
- missing windows are UNKNOWN, never interpolated or converted to zero.

### WP-06 — Spatial composition and biological/sensitivity firewall

**Paths**

- `spatial_architecture.py`
- `biological_sensitivity.py`
- `tests/test_formulation_intelligence_spatial_biological.py`

**Spatial contract**

- focus, width, density, aperture, edge, distance, texture, contrast, shadow,
  air, projection field, and residue;
- density and airiness remain independent;
- predicted diffusion cannot become observed space or sillage.

**Biological contract**

- binds exact molecule, stereochemistry, grade/product basis, receptor/genotype
  evidence, task, population, and specific-anosmia risk;
- opaque trade products cannot inherit isolated-isomer mechanisms;
- receptor diversity is not perceptual nonredundancy, mixture quality, target
  fit, liking, sensuality, projection, or longevity evidence.

### WP-07 — Hedonic evidence platform

**Paths**

- `hedonic_platform.py`
- `tests/test_formulation_intelligence_hedonic_platform.py`

**Views**

- material prior, mixture expectation, interaction residual, temporal liking,
  criterion-specific preference, population/assessor structure, and decision;
- retain `PREFER_A`, `PREFER_B`, `NO_PREFERENCE`,
  `NO_PERCEPTIBLE_DIFFERENCE`, `CANNOT_JUDGE`, and protocol/missing outcomes;
- retain realized order, predecessor, session, repeat, participant, context,
  concentration, time, matrix, uncertainty, ties, abstentions, and opposed
  clusters.

**Gate**

- no global `hedonic_score`;
- no averaging of liking, comfort, sensuality, elegance, interest, naturalness,
  fidelity, depth, richness, coherence, aversion, and defect intensity;
- pooled mean cannot erase stable opposing assessor clusters.

### WP-08 — Capability ontology and candidate selection

**Paths**

- `capability_ontology.py`
- `candidate_selector.py`
- focused tests

**Contracts**

- candidate capability is contextual: identity, role, temporal window, matrix,
  concentration range, interaction uncertainty, exact product/stock identity,
  evidence class, failure mode, omission loss, and resolving comparison;
- every candidate is `SELECT`, `REJECT`, or `HOLD` for a named target function;
- one precise material is valid; multiple materials require distinct roles and
  pairwise nonredundancy;
- availability, supplier prestige, recipe frequency, OAV, and generic hedonic
  prior cannot prove target fit.

### WP-09 — Accord graph, spatial relations, and assembly frontier

**Paths**

- `accord_graph.py`
- `candidate_assembler.py`
- focused tests

**Contracts**

- graph nodes are target functions/facets, not merely ingredients;
- emitted packets use `PlaneId.RELATION`, not a hidden function-plane score;
- edges encode support, bridge, contrast, shadow, handoff, recurrence,
  opposition, suppression risk, takeover risk, and omission loss;
- hard-coded historical accord ratios are quarantined priors;
- native criteria remain separate Pareto axes;
- zero-intervention and precise-simplicity candidates are always permitted.

### WP-10 — Inventory projection and whole-perfume blueprint

**Paths**

- `inventory_projection.py`
- `whole_perfume_assembler.py`
- focused tests

**Contracts**

- project an immutable ideal proposal onto exact `ExactStockRef`, basis,
  carrier, fraction, availability, and aliquot state;
- Magnolia EO neat/as supplied; Alpha Irone only 10% w/w DEP; Black Agarwood
  Artificial 10% w/w DPG only; Ambrofix liquid gone while historical 7.27%
  provenance remains and crystals stay distinct; Castoreum 10% DEP with basis
  unspecified and quantitative HOLD; Bacdanol owned with unresolved fraction;
  Clearwood neat; Guaiacwood EO 33% with unresolved basis/carrier;
- no invented active amount, ppm, OAV, or carrier displacement on held stock;
- whole-perfume output is a versioned plane blueprint and experiment proposal,
  not a compounding formula.

### WP-11 — Experiment selector

**Paths**

- `experiment_selector.py`
- focused tests

**Contracts**

- choose the minimum decision-resolving comparison: zero intervention,
  carrier-matched A/B, complete omission, recombination, ratio/load sweep,
  temporal observation, independent preparation, or assessor replication;
- constant-total and carrier displacement are explicit;
- AB/BA/Williams sequence, realized order, washout, repeats, missingness, and
  stopping conditions are preserved;
- protocol output grants no authority to execute a physical test.

### WP-12 — Read-only legacy adapters and quarantine

**Paths**

- `adapters.py`
- adapter-focused tests and import-isolation tests

**Rules**

- adapters preserve exact source state: admitted, guardrail, shadow, future,
  research-only, historical, unsupported, or retired;
- no adapter promotes a legacy scalar, old recipe, or retired module;
- historical formulas remain byte-identical;
- every adapter binds exact file hash and transitive import closure;
- import of one adapter must not eagerly import Torch, FAISS, sentence
  transformers, plotting, network clients, formula parser, or full pipeline.

### WP-13 — Frozen benchmark and admission

**Artifacts**

- sealed corpus, answer keys, anonymization map, model/run receipts, prompt and
  output hashes, scorer identities, rubric, ablations, statistics, tombstones,
  and generated transitive import manifests.

**Corpus**

- all cross-family cases in the governing design;
- floral object, bouquet, white-floral takeover, sparse/no-change, ambiguous
  stock, natural-composite, carrier conflict, named-reference, user-sensory
  contradiction, heterogeneity, order confounding, and attractive numeric decoy;
- held-out families and new targets not present in implementation prompts.

**Arms**

1. plain GPT-5.6 Sol at the frozen reasoning level;
2. integrated plane architecture;
3. length-matched placebo guidance;
4. module ablations;
5. safe countercases and critical traps.

**Non-compensatory admission gates**

- zero critical authority, inventory, natural-mixture, protocol, or safety
  errors;
- exact keyed correctness cannot be offset by prose quality;
- blinded usefulness, calibration, stability, and efficiency are separate;
- superiority to plain and placebo on preregistered endpoints;
- no regression on safe no-change cases;
- held-out family performance and seed/order stability;
- complete recursive import closure with every executed source/config/data file
  hash-bound and no retired/research-only leakage;
- cold import, warm synthesis, incremental recomputation, peak memory, and
  scaling meet the performance budget.

Failure retains the module as `FUTURE_CANDIDATE_NOT_VALIDATED` and records a
provenance tombstone. Benchmark success grants only the exact computational
runtime scope measured; it cannot grant sensory, physical, hedonic, safety,
stability, purchase, formula, compounding, or release authority.

## 5. Verification ladder

For every work package:

1. demonstrate the missing module or failing invariant with the smallest test;
2. run only the focused new tests;
3. run Ruff on leased paths;
4. run Mypy on leased source paths;
5. run cross-module contract and metamorphic tests after each dependency layer;
6. verify import isolation and generated dependency closure;
7. check `.venv\Scripts\python.exe -m build --version` once before broad checks;
8. run `scripts/pipeline_audit.py project-verify --quick --json` before any
   push-level decision;
9. run full project verification without `--quick` before integration,
   publication, or completion;
10. run the frozen benchmark only after the corpus, keys, identities, hashes,
    and judging protocol are sealed.

No focused test can support a full-project, runtime, benchmark, or release claim.

## 6. Native-agent rotation queue

The current runtime permits three active child turns in addition to the parent.
Completed slots rotate in this order unless new evidence changes dependencies:

1. hedonic platform;
2. target compiler plus cross-family architecture;
3. spatial plus biological/sensitivity firewall;
4. capability ontology plus candidate selector;
5. accord graph plus candidate assembler;
6. inventory projection plus whole-perfume assembler;
7. experiment selector;
8. legacy adapter/import-closure lane;
9. independent test/adversarial reviewer;
10. performance and frozen-benchmark harness review.

Children may draft only their leased files. The parent owns architecture,
scientific adjudication, cross-module edits, final integration, full
verification, Git acceptance, and the user-facing result.

## 7. Current blockers and holds

- Cypress V6 admission is not a transitive import closure and remains generic
  runtime `HOLD`; exact CYP-02 behavior is bounded predecessor evidence only.
- Cypress 4046 inventory/test/pre-push work is not yet accepted or integrated.
- 6992 reference/gate work remains dirty and inventory-divergent.
- 3289 floral-depth libraries are valuable but untracked and not integration
  ready as whole modules.
- No human sensory, target-fit, liking, performance, stability, or release
  evidence exists for this new architecture.
- The frozen cross-family benchmark has not yet been sealed or executed.

These holds do not block structural implementation, focused tests, research
synthesis, or benchmark design. They do block runtime admission and completion.
