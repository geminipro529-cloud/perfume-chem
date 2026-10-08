# Remaining subtype coverage: implementation plan

Date: 2026-10-07. Scope: finish the remaining subtype-to-formulation work first;
do not perform the separately excluded speed optimization. Preserve all dirty
work, formula comparators, inventory, physical bottle streams and held stocks.

## Baseline and definition of done

The accepted v4 bridge has 47 mappings / 93 comparison options against 179
partial subtype cards. The remaining 132 are not interchangeable missing JSON
entries. They include architectural additions, exact-product comparisons,
controlled omissions and experiments requiring evidence not currently present.

Every remaining card must receive a source-bound disposition and a locally
testable outcome. A disposition is not an executable mapping, and an executable
mapping is not sensory validation. Counts must report those states separately.
No blanket generic template will count as resolving a specific botanical,
stereochemical, extract-grade, named-fruit or omission question.

## Sequence

1. Census every unmapped card with its exact source bindings, identity limits,
   comparison question and prerequisites. Review floral, fruit/tea/gourmand and
   structural families independently; parent verifies admissions locally.
2. Introduce a versioned v5 operation contract without changing v1-v4 bytes or
   template semantics. Support registered own-odor eligibility and narrow role
   refinement. Refinement may only strengthen an eligible canonical role's
   predicate; it may not change quantities, explicit materials, anchors, role
   function, protected negative space or the user's request.
3. Keep controlled physical omission separate from role deletion/re-solving.
   Re-solving reallocates the other materials and does not establish a matched
   omission experiment. Until a fixed-row, comparable-basis transformation is
   available, explicitly withhold that experiment rather than falsely execute it.
4. Add source-supported mappings in reviewed family tranches. Exact identity
   comparisons must select the exact reviewed product/grade or return a specific
   missing-binding/stock hold. A source's uses, partners, botanical origin or name
   cannot supply its own-odor eligibility.
5. Bind successor manifests, operations, templates, eligibility and disposition
   files into runtime receipts and durable job fingerprints. Preserve control,
   max-two unordered alternatives, source drift withholding, stock holds, and
   independent false action-authority flags.
6. Verify in ascending cost order: schema/invariants and mutation tests; focused
   planner/solver/receipt tests; frozen staged case expectations; current-inventory
   end-to-end checks; relevant backend fingerprint checks; scoped lint/types and
   diff checks. Do not rerun broad historical suites without changed dependencies.
7. Only after coverage work, handle app/environment handoff and recoverable
   campaign inputs. CHIMIE L'HOMME requires its actual accepted brief/formula.
   Orris Liquid remains excluded until the user explicitly clears that hold.
   Sensory usefulness requires observations; software cannot invent them.

## Literature findings governing this change

- IFF's Meth Ionone Gamma Coeur description supports powdery orris/violet with
  woody/tobacco facets, not equivalence to every methyl-ionone stock.
- dsm-firmenich describes Exaltolide with subtle fruity undertones and Helvetolide
  with pear-like facets. A generic "non-fruity versus fruity" binary would
  misstate those products. Compare exact supported routes or bounded descriptors.
- IFF explicitly describes labdanum resinoid as slightly smoky, leathery and
  animalic as well as resinous. Zero smoke weighting in a template cannot certify
  a smoke-free ingredient or result.
- Tea/food studies support bounded odor hypotheses, not perfume doses. An
  identity-only paper does not support an odor-role mapping.

Primary pages reviewed this turn:

- https://www.iff.com/scent/ingredients-compendium/meth-ionone-gamma-coeur/
- https://studio.dsm-firmenich.com/product/exaltolider-pe-941962
- https://studio.dsm-firmenich.com/product/helvetolider-pe-947650
- https://www.iff.com/scent/lmr-compendium/labdanum-resinoid/

## Authority and exclusions

### Read-only omission handoff

The verified omission transformation will be reachable through one closed
`OMISSION_COMPARISON_PLAN` durable job, not a new pipeline script or a bottle
addition. Its strict data payload carries the unchanged mass-basis control,
protected/omitted stock IDs and an explicitly identified carrier blank. It may
combine the result with the existing lightweight personal protocol builder.
Both candidate hashes, the omission receipt and the protocol are bound together;
the result remains planning-only and is not an executable blinded session.
Public planning must not leak or pretend to persist a private code mapping.

The type is added through an additive database constraint migration, with a
populated-graph upgrade/downgrade/upgrade test. The UI entry stays optional in
the experiment area. A plain-language clue or casual observation still needs no
photograph, lot paperwork or mass conversion. Missing mass/stock/blank evidence
withholds only the quantitative omission experiment. Existing protocol-profile
and omission source summaries support this experimental distinction, not perfume
doses, sensory superiority or standard certification.

All generated designs remain untested hypotheses. No empirical model admission,
dose calibration, performance/liking claim, physical compounding, purchase,
safety clearance or release is authorized by this work. No new pipeline script,
inventory mutation, historical rewrite or speed-optimization change is planned.

### Live handoff finding

The first real worker job used a diagnostic title ending in "not a physical
formula". Joining that title and the separate brief with a space allowed the
existing clause-level negation mask to erase the brief's subtype vocabulary.
The same brief with a neutral title worked. Preserve a clause boundary between
those two fields for literature retrieval and canonical replay; explicit avoid
constraints must still apply to both fields. This repairs input separation, not
the source science, doses or speed. Add both positive and exclusion regressions.

### Chat recovery and compatibility message

The user's request to look in the chats recovered the exact CHIMIE L'HOMME
Terre-heart reference and its explicit naming handoff. Preserve local normalized
source copies and original-byte hashes, with selected later user corrections.
The earlier Sport Citrus association and the withdrawn measured-30-mL answer
must not govern this campaign. Keep the historical formula separate from live
stock and bottle truth. Bind a read-only recovery manifest into retrieval and
durable fingerprints; report the recovered reference instead of asking for the
file again. This does not bypass the existing campaign-generation hold, silently
select a revision, rebase historical stocks, or create a physical action.
Legacy hold codes remain compatibility identifiers until explicit target binding
is supported; the user-facing reason and recovery context must be truthful.
