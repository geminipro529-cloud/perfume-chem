# Chypre and citrus-wood architecture v4: reviewed implementation plan

Date: 2026-10-07. Status: implementation protocol, not empirical admission.

## Research and current-system finding

The parent reviewed `CHYPRE_COLOGNE_AND_TEXTURE_NEXT_WAVE_20261007.md`
(SHA-256 `ddb9bc7dc1f53bcb88a88c3d88d8b7d6123cae5aabfacbd4dc74b3976afd8fd3`)
and the existing v3 planning, solver, critic, benchmark and durable fingerprint
paths before this change. The 44 existing mappings and their source records are
immutable predecessors. The descriptor-eligibility prerequisite is recorded in
`ARCHITECTURE_V4_ELIGIBILITY_REVIEW_20261007.md`; it did not activate new mappings.

Fresh primary-source checks:

- [PW Fructone B, 3FG00196](https://www.perfumersworld.com/view.php?pro_id=3FG00196):
  the supplier combines an odor description with applications. Jasmine,
  tuberose and gardenia in the applications section do not establish that this
  product itself has those odors. Retain its fruity/floral, sweet, wine-like,
  fermented/strawberry-preserve descriptors; remove the application-only flower
  tokens from the runtime own-odor field. This is an evidence interpretation,
  not a new sensory measurement. CAS 6290-17-1 is not ordinary Fructone.
- [PW Berry Hexanoate / BerryFlor, 3FG19149](https://www.perfumersworld.com/view.php?pro_id=3FG19149):
  the own-odor prose explicitly includes jasmine-associated aspects. Some of
  that prose follows `Use:`; a blanket text split at that word would be wrong.
  Preserve the separate applications versus own-odor distinction by review.
- [Hedione, original manufacturer](https://studio.dsm-firmenich.com/product/hedioner-pe-964898):
  standard Hedione has floral/jasmine/citrus descriptors. Do not transfer a
  standard-grade description into an exact HC-grade empirical capability.
- [Aroma & More Petitgrain Paraguay](https://aromaandmore.com/en/essential-oil-100-pure-/97-petitgrain-essential-oil-paraguay-fresh-floral-woody-and-slightly-citrus-.html):
  leaves/twigs are the plant part; the supplier describes fresh, floral, woody
  and slightly citrus odor. Neither the plant organ nor the name bitter orange
  proves leafy or bitter odor. This catalog match is not exact-lot analysis.

Supplier descriptions remain qualitative. No dose, strip-life, medicinal claim,
gas release, sensory strength, safety or preference calibration is admitted.
The raw supplier caches and inventory receipt are not rewritten.

## Bounded implementation

1. Correct only the reviewed Fructone B own-odor field, preserving other intake
   edits. Regression-test Fructone versus BerryFlor versus standard Hedione.
2. Register an immutable v4 successor containing the unchanged ordered v3
   prefix plus three subtype mappings and five options:
   floral chypre (rose / jasmine-associated), green chypre (bitter-resin-green /
   watery leaf), citrus-wood cologne (one citrus-leaf-floral bridge).
3. Bind each new option to a closed descriptor requirement. All conjunctions
   must be satisfied by own-material annotations; category, stock name,
   botanical organ, synergy partner or application prose is not evidence.
4. Retain existing numeric heuristic templates, protected recognizers, exact
   doses, trace limits and inventory exclusions. Never invent source doses or
   alias an absent natural to a loosely related stock. Keep v3 active until the
   staged v4 protocol passes.
5. Extend the offline benchmark with a frozen v3-prefix successor corpus and
   per-option expectations. A positive request must attempt every planned
   option once. Every option must either yield a distinct viable comparison or
   be proven to have an empty admissible stock pool. A consumed stock, generic
   solver failure or critic rejection is not an empty-pool proof.
6. Preflight corpus bytes, exact configuration, prefix and closed fields before
   any design call. Check control preservation, replay, source closure,
   cancellation-free read-only execution, no network, authority and exact
   current inventory. Empty-pool holds do not inflate executable coverage.
7. Bind the new manifest into durable references. Run focused schema, solver,
   receipt-mutation and job-fingerprint tests before the paired/reverse offline
   corpus. Record actual failures and timings rather than weakening gates.

## Frozen expectations for the new positive cases

- Floral chypre: both rose and jasmine-associated options must be viable.
- Green chypre: watery-leaf must be viable; bitter-resin-green may be withheld
  only with a verified empty admissible pool.
- Citrus-wood cologne: the single bridge may be withheld only with the same
  verified empty-pool proof. Owned Paraguayan petitgrain is not relabeled to
  manufacture a match.
- Negated, missing-facet and exact-campaign-hold cases must not gain an
  unrequested new architecture. CHIMIE L'HOMME remains unbound.

The new design corpus will be hashed before the first v4 solver run. Historical
corpora remain byte-identical. Staging, current-source acceptance and runtime
activation are separate recorded states. No formulas, inventory, bottle events,
purchase, safety or release authority are changed. Orris Liquid remains held.

## Pre-activation failure and bounded repair

The first v4 focused execution passed 39 tests and failed the predeclared green
chypre viability test. Its watery-leaf pool was not empty: Violet Leaf Absolute
10% was admitted, but all surviving beam states had already used that identity
in a broad earlier role. The new pool audit correctly refused an empty-pool
excuse. Do not change the frozen corpus, descriptor predicate or stock gates.

[UC Berkeley CS188 filtering](https://inst.eecs.berkeley.edu/~cs188/textbook/csp/filtering.html)
describes forward checking of remaining variable domains after assignments.
Use that algorithmic principle as a bounded beam-priority improvement: prefer
states that leave candidates for future required descriptor-constrained roles,
then retain the existing lexicographic ordering. Do not drop states solely on
this look-ahead heuristic; it is not a complete constraint solver or proof of
infeasibility. Reuse existing unary pools, avoid constraints and admission rules.
No sensory objective, ingredient-count objective, new dose or relaxed gate is
introduced. The unchanged control and all historical cases must still be tested
on current source. Record this solver change in the implementation fingerprint.

The existing offline benchmark CLI may optionally write its generated result
to a new explicit `--output` artifact using exclusive creation. It must refuse
overwrite, write only after the closing input snapshot, and print a compact
receipt. This adds no pipeline script and does not edit any source formula.
