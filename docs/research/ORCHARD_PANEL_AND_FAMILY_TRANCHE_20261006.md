# Orchard reference panel and family-foundation continuation

Date: 6 October 2026.
Status: bounded implementation and focused verification complete; the full 49-package research plan is not complete.

## Outcome

Continued all four remaining lanes from the R1/R2 foundation report:

1. Extended manufacturer-bounded resin, musk and citrus-grade guidance and freshly reproduced measured-curve applicability.
2. Added an exact-edition, global orchard/floral reference panel for CHIMIE Femme.
3. Repaired the seven reproduced historical shortlist fixture failures without changing live inventory or weakening production drift checks.
4. Added introductory transparent-floral, sandalwood, green, chypre, leather and gourmand guidance.

The runtime remains offline and advisory. No perfume formula, stock truth, inventory receipt, purchase, compounding run, trained empirical model, safety review or release was created or changed by this continuation.

## Scientific and source boundary

The local knowledge pack now contains 84 sources, 78 claims, 43 profiles and 25 exact material cards. This tranche adds 15 selected-section source summaries, 13 claims, 10 profiles and six material cards. Source-review states are 20 REVIEWED_ADVISORY and 64 LEGACY_ADVISORY.

"Reviewed advisory" means the stated primary/manufacturer sections were checked for the bounded claim. It does not mean a complete paper review, measurement validation, data/weight license admission, complete retraction census or quantitative calibration. Source-record hashes bind local metadata and original summaries; publisher-page bytes were not archived and are not claimed to be hashed.

The ten new profiles cover:

- Resin amber: benzoin Siam and labdanum remain distinct extraction/product roles.
- Musk roundness: Exaltolide and the exact IFF Ambrettolide description supplement existing musk guidance. Generic owned Ambrettolide is not silently equated with that manufacturer's grade.
- Bergamot grade: one exact FCR manufacturer grade is distinguished; no cross-supplier phototoxicity or compliance certificate is inferred.
- Transparent floral support: Hedione is not automatically Hedione HC or a mandatory jasmine bouquet.
- Sandalwood: Sandalore is a named role alternative, not an equal-dose replacement for Ebanol or natural sandalwood.
- Green leaf: Stemone requires explicit leafy intent; generic freshness is insufficient.
- Chypre: relationships from the exact marketed Mitsouko EDP are not a recovered proprietary or historical formula.
- Leather: Safraleine's leather/spice role is distinct from an automatic smoke/tar recipe.
- Gourmand: tonka's botanical/extraction and associated facets do not become a generic sweetness objective.
- Orchard references: pear/freesia/osmanthus bridges and lychee/rose contrast preserve fruit recognizers and negative space.

Ingredient count, raw/log OAV, arbitrary valence, descriptor distance and sales rank remain unavailable as beauty or liking labels. No numerical dose or physical-property table was admitted from product marketing.

## Current commercial panel and changed decisions

A v3 commercial registry preserves the v1/v2 files and their existing records. It adds a separate global-orchard-floral-2026-v1 panel:

| Role | Exact reference | Evidence boundary |
|---|---|---|
| Global feminine anchor / white-floral contrast | YSL Libre Eau de Parfum | Issuer-reported Libre line leadership, not a variant-specific sensory liking label. |
| Global feminine anchor / neroli-amber-musk contrast | Prada Paradoxe original Eau de Parfum | Issuer global top-15 product-line evidence; not a verified apple/pear reference. |
| Pear-citrus-osmanthus neighbour | Guerlain Aqua Allegoria Pera Granita Eau de Toilette | Official pear/citrus/osmanthus architecture, not formula proportions or measured similarity. |
| Pear-freesia-patchouli neighbour | Jo Malone English Pear & Freesia Cologne | Official architecture, not a measured whole-product curve. |
| Reserve lychee/rose drift contrast | Parfums de Marly Delina original Eau de Parfum | Reference for negative space; not a newly established global bestseller. |

Reasons for changes:

- Paradoxe is useful as a current market-selected contrast, but the checked original EDP page does not establish the requested apple/pear architecture. Treating it as such would conflate a market claim with sensory evidence.
- Pera Granita and English Pear & Freesia directly fit the orchard brief. A lavender panel is not selected merely because a pear perfume also contains amber, musk, vanilla or floral support.
- Delina remains reserve-only, so its rose-led character does not silently drive CHIMIE Femme toward rose.
- Review time cannot renew old sales observations. Current panel selection requires admissible, non-expired evidence for both market anchors and official architecture for structural neighbours.

Selection now has specific required concept tags. Expired matches are excluded before ranking; explicit expired or mismatched panels withhold rather than silently substitute. Named reference matching uses token boundaries, respects avoidance/negation, and rejects the explicitly tested wrong concentrations and flankers. Bare documentary mentions do not authenticate a physical sample. This is a bounded resolver, not a claim of exhaustive worldwide flanker recognition.

Reference clues use active members only. A reserve's facets cannot leak into the active architecture result.

The goal-analysis default comparison date is now the current date, not a fixed September 2026 date. Backend source fingerprints include the new registry and affected implementation paths. No normal-runtime network lookup is introduced.

## Historical fixture repair

The failures were caused by a frozen September protocol being executed against subsequently changed live inventory. Recovered the exact historical inventory from Git:

- Commit: 9e501074e0046717c447d5e1404c85e653274769.
- Blob: 9fc3d906ec35662f55c804494736e35c9c5cca17.
- LF-normalized bytes: 28,251.
- SHA-256: 1b4324da5a35cebe8c59959e58276d84ac8f2f0e0e6f3239fdef0a4250d8df71.

Only tests that intentionally exercise that frozen historical contract opt into the fixture. Production continues to read current inventory. Tests do not stub the hash function or rewrite old protocol records. A new test changes actual inventory bytes and confirms HOLD_CP3_READINESS_PROTOCOL_DRIFT, empty ranking and NO_CHANGE.

The controlled fixture is historical test input only; it is not current ownership, a stock update or an executable build instruction.

## Measured-intensity applicability audit

Fresh execution of the existing governed Wakayama adjudicator reports:

- 314 source rows; 313 positive curves.
- 11 exact chemical-identity bindings.
- One CAS/name conflict, two ambiguous products/grades, one not-applicable row and 299 without local identities.
- Zero exact stock bindings and zero observed-range bindings.
- HOLD_EXACT_STOCK_RANGE_MATRIX_BINDING.

Chemical adjudication and raw capability-loading states are separate reports; 11 chemical bindings do not mean 11 executable current-stock calibrations.

The official 2020 correction was freshly checked. The corrected derived threshold in ng/L air is:

`10 ** (3 + C - D * ln((Imax - 1.4) / 1.4))`

Converting that result to micrograms/L before evaluating the matching forward curve returns 1.4 in the round-trip test. This verifies algebra and units, not universal human validity, receptor affinity or a finished-product intensity prediction.

No source curve, release model, natural-mixture composition, commercial product identity or empirical license was newly admitted by this audit.

## Verification receipts

Runs overlap and must not be added as a unique-test total.

| Check | Current-source result |
|---|---|
| Broad focused engine/formulation regression | 262 passed, 73.48 s |
| Final knowledge, panel, parser and governance regression after latest small changes | 113 passed, 2.25 s |
| Backend durable job/unit/API and source-fingerprint regression | 40 passed, 45.08 s |
| Final backend fingerprint and durable API smoke after source-review update | 8 passed, 14.77 s |
| Historical shortlist cases, before the added drift regression | 11 passed |
| Changed engine/backend Ruff and targeted mypy checks | Passed |
| Changed-path diff check | Recorded in adjacent audit after final documentation |
| Final offline retrieval plus reference selection and documentary comparison | p95 approximately 24.7 ms; max approximately 68.0 ms, 36 calls |

The microbenchmark covers local knowledge retrieval plus panel comparison, not the complete formula engine, a 368-formula corpus, deployment, browser rendering or four/eight-worker memory. Existing full-system performance targets are not claimed newly met.

No new migration was needed. No full project verifier, merge readiness, empirical superiority, live service restart or commercial-release readiness is claimed.

## Remaining work and next research batch

The frozen 49-package coverage plan is unchanged. The separate progress index records partial reviewed coverage and exact dependency hashes; none of the 49 packages is declared fully reviewed.

The next useful primary-source batch is:

1. Rose, orange blossom, tuberose/gardenia and modern muguet identities, recognizers, bridges and forbidden drift.
2. Cedar, vetiver, patchouli and oud product/fraction distinctions.
3. Aquatic, berry/tropical/stone fruit, roasted/dairy gourmand, incense, spice and tea structures.
4. Remaining regional traditions, hybrids, market tracks and scientific endpoint/protocol gaps.

Each package still needs source-specific chemistry/sensory evidence, exact product/grade identities, corrections/retractions/rights checks, applicability and regression tests. New material descriptions alone do not complete those obligations.

A stronger scientific claim needs applicable release data, exact curve stock/range/matrix bindings or matching human observations. These requirements do not block playful, clearly labelled formulation hypotheses and do not require photos or formal receipts for ordinary personal exploration.

## Primary sources freshly used

Manufacturer sections support bounded descriptions, not a quantitative formulation:

- [IFF Benzoin Siam](https://www.iff.com/scent/lmr-compendium/benzoin-resoid-siam/), [IFF Labdanum](https://www.iff.com/scent/lmr-compendium/labdanum-resinoid/).
- [dsm-firmenich Exaltolide](https://studio.dsm-firmenich.com/product/exaltolider-pe-941962), [IFF Ambrettolide](https://www.iff.com/scent/ingredients-compendium/ambrettolide/).
- [IFF exact bergamot FCR grade](https://www.iff.com/scent/lmr-compendium/bergamot-oil-cp-italy-org-fcr-csm/).
- [dsm-firmenich Hedione](https://studio.dsm-firmenich.com/product/hedioner-pe-964898).
- [Givaudan Sandalore](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/sandaloretm), [Stemone](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/stemonetm), [Safraleine](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/safraleinetm).
- [IFF Tonka absolute](https://www.iff.com/scent/lmr-compendium/tonka-bean-absolute/).
- [Guerlain Mitsouko EDP](https://www.guerlain.com/nl/nl-nl/p/mitsouko-eau-de-parfum-P024104.html).

Reference and market sources:

- [L'Oréal Luxe 2025 issuer report](https://www.loreal-finance.com/en/annual-report-2025/luxe/).
- [Prada Paradoxe original EDP](https://www.prada-beauty.com/fragrance/paradoxe/paradoxe-eau-de-parfum/MPL01610.html).
- [Guerlain Pera Granita EDT](https://www.guerlain.com/us/en-us/p/aqua-allegoria-pera-granita---eau-de-toilette-P014403.html).
- [Jo Malone English Pear & Freesia Cologne](https://www.jomalone.es/product/english-pear-freesia-cologne).
- [Parfums de Marly Delina original EDP](https://parfums-de-marly.com/products/delina).

Numerical boundary:

- [Wakayama official correction](https://pubs.acs.org/doi/10.1021/acs.iecr.0c05822).
- [Pellegrino mixture-intensity preprint](https://pmc.ncbi.nlm.nih.gov/articles/PMC12363845/) remains a challenger, not a newly admitted universal mixture rule.

All outputs retain release_authority=false, safety_authority=false, compounding_authority=false and evidence_admission_authorized=false.
