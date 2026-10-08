# Floral and adjacent woody research expansion — 6 October 2026

## Outcome

Implemented an offline, source-bound research expansion for all 13 existing floral packages and broader fruity-woody, fougere, chypre and ambergris/musk structures. These are construction clues and comparison hypotheses, not validated perfume recipes or a complete model of floral perception.

- Added **40 subtype cards**: **28 floral** and **12 adjacent-style** cards.
- The extension now contains **66 cards across 25 packages**, retaining the previous 26 cards unchanged.
- Added **21 sources**: eight primary papers and thirteen manufacturer or official-brand sources. The literature pack now contains 154 sources, 147 claims, 43 architecture profiles and 25 exact-material cards.
- **33 of the 34 initial floral gap entries** now have partial research cards. Cananga remains without a dedicated extension.
- No subtype was promoted to empirical validation. “Partial research” does not mean complete botanical, formulation or sensory coverage.
- The exact accepted CHIMIE L'HOMME brief/formula was **not recovered**. A generic data-driven identity hold preserves this uncertainty; nearby Aventus records and unrelated Prada/YSL L'Homme files are not substituted.

Current knowledge: [subtype successor](../../data/formulation_knowledge/subtype_research_v2.json). Coverage accounting: [progress v4](../../data/formulation_knowledge/research_coverage_progress_v4.json). Verification and source hashes: [audit](FLORAL_WOODY_RESEARCH_AUDIT_20261006.json).

## What each floral package gained

| Existing package | New detailed branches in this pass |
|---|---|
| Rose | Lemony, jammy/fruity, honeyed, metallic/spicy, dark patchouli |
| Jasmine | Leathery jasmine, alongside the existing grandiflorum and tea-green extension |
| Orange blossom / neroli | Honeyed-indolic bridge; distilled neroli and petitgrain were already in the preceding extension |
| Tuberose | Indolic/animalic versus modern transparent construction |
| Gardenia | Creamy white-floral construction, separate from a complete natural-extract identity |
| Tropical florals | Ylang fractions, tiare and frangipani; cananga still unresolved |
| Muguet / watery petal | Cyclamen and watery-musk variants; true lilies are excluded from muguet matching |
| Light florals | Dewy peony, rose-adjacent peony, peppery freesia, creamy magnolia |
| Green florals | Exact-product narcissus absolute; not automatically jonquil |
| Spicy / lily | Salicylate-associated lily and green lily; Lilium remains distinct from Convallaria |
| Pollen / honey | Pollen-honey texture without automatically making the perfume sugary or animalic |
| Iris / violet | Violet powder and violet leaf, retaining the existing iris/orris distinctions |
| Bouquets | Classical, aldehydic and soft-floral architectures |

“All 13 floral packages” refers to this repository's frozen taxonomy. It does not mean every scented plant or commercial floral style is represented. Lilac, honeysuckle, sweet pea, champaca/michelia and other targets remain candidates for a separately reviewed taxonomy expansion.

Each card includes a bounded evidence summary, a separately labeled construction hypothesis, functional connections, forbidden drift, a control/alternative comparison, a question and stop condition, source-record hashes and false action-authority flags. No card invents a percentage, threshold, receptor affinity or liking score.

## Research distinctions that change construction reasoning

1. **Rose is not one fixed analytical profile.** The four-cultivar rose study supports retaining cultivar and profile differences. The new lemony, jammy, honeyed and darker registers are design hypotheses anchored to those distinctions, not claimed reconstructions of a universal rose oil. Rose Oxide L's supplier description supports green/rose/geranium facets; a “metallic” interpretation still needs its own comparison.

2. **Ylang fractions are not interchangeable.** The fractionation study distinguishes early and later distillates and reports changes in the constituent distribution. A later fraction must not be called lighter merely because it is a later grade. GC abundance is not proportional odor contribution.

3. **Peony and freesia require actual targets.** Cultivar studies support several floral profiles rather than a single botanical accord. Peonile is a named manufacturer's material, not the chemical identity of peony. A peppery freesia direction is an optional construction experiment, not a mandatory natural-freesia marker.

4. **Lily is not lily-of-the-valley.** Lilium profiles and muguet/Convallaria construction remain separate. Retrieval explicitly excludes the new Lilium cards when the brief says “lily of the valley” or “muguet.” Salicynile is a nitrile; its name does not make it a salicylate or a complete natural-lily reconstruction.

5. **Tuberose changes with development.** The developmental study gives reasons to distinguish benzenoid, green and indolic facets. Its analytical values do not become perfume proportions. Transparent versus animalic versions remain alternatives to compare.

6. **Natural-product identity matters.** The Narcisse Abs Conscious CSM source describes an exact IFF product. Its green/hay/tobacco/fruity facets do not establish equivalence with all narcissus products or jonquil. Likewise, Atlas cedar remains a different source identity from Virginia, Texas or Chinese cedar.

7. **Clean patchouli need not mean a distilled natural fraction.** The Clearwood source is a biotechnology-derived product description. It is not evidence that Clearwood, Clearwood Prisma and all clean patchouli fractions are interchangeable.

8. **Food-aroma work supplies investigation methods, not perfume recipes.** The pineapple study supports recombination/omission as a way to interrogate fruity character. Its food matrix, ratios and odor thresholds cannot directly specify a hydroalcoholic perfume.

9. **Official perfume architecture is not a formula.** CHANEL No. 5 EDP and Creed Aventus pages provide marketed structural descriptions only. Differences between Creed's official descriptions are retained as wording/reference uncertainty, not merged into a supposedly authenticated quantitative formula.

Primary abstracts and selected sections were reviewed to the scope recorded in each source record. Some publisher pages were inaccessible; indexed primary abstracts were used where specified. An exhaustive correction/retraction search was **not** completed for the eight new research papers. Their records retain `NOT_INDEPENDENTLY_RECHECKED`, and none is admitted for numerical calibration or reuse of empirical datasets.

## CHIMIE L'HOMME and adjacent architectures

The following new cards improve research around a broad masculine fruity-woody direction without asserting that it is CHIMIE's accepted identity:

- Pineapple-to-wood continuity.
- Apple/lavender, pineapple/lavender and spiced-wood/lavender bridges.
- Floral and leathery fougere alternatives.
- Floral, green and leathery chypre alternatives.
- Clean patchouli and mineral woody-amber texture.
- Ambergris-associated musk transitions.

They permit questions such as “does the floral bridge keep the fruit recognizable?” or “does added mineral wood erase the fruit/softness?” They do not default to more Ambrox, superamber or musk, and cannot authorize a changed formula.

An exact-name request for CHIMIE L'HOMME now returns `HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED` with no inferred family IDs. Explicit user descriptors may still retrieve their own bounded research. The UI displays the unresolved identity in the optional evidence view. The only campaign-specific input needed is the accepted brief or latest formula, not photographs or inventory paperwork.

## Runtime and provenance

- Normal Formula Studio and goal analysis read local knowledge; no runtime literature search was added.
- `subtype_research_v2.json` pins the frozen construction library, coverage plan and exact bytes of its v1 predecessor.
- The loader rejects missing/drifted predecessors and any rewrite of the earlier cards.
- Source-binding failures withhold the affected card; independent, adequately supported cards remain usable.
- Matching stays conjunctive and respects negated/avoided phrases. Generic family names do not indiscriminately activate all subtypes.
- The default output remains bounded to four retrieved subtype cards; detailed evidence stays expandable.
- Durable job fingerprints include both subtype manifest versions.
- Scientific facts, supplier descriptions and untested construction hypotheses remain separate.
- Release, safety, compounding and evidence-admission authority remain false.
- Orris Liquid's temporary compounding exclusion is unchanged. No exact material card, inventory entry or formula was added or edited by this expansion.

## Verification on the current source

### Focused correctness and integration

- **361 engine tests passed** in the selected subtype, source-review, construction, literature, lavender/foundation, commercial-panel, Formula Studio and goal-analysis surfaces.
- **16 backend/API tests passed**, with 11 unrelated nodes deselected, covering research fingerprints, job knowledge and the served UI/API path.
- Root Ruff on the changed subtype module/tests: passed.
- Root mypy on the subtype module: passed.
- Backend Ruff on changed service and selected tests: passed.
- Backend mypy on the service: passed.
- `node --check backend/app/static/lab.js`: passed.
- Changed-path `git diff --check` and whitespace checks for the added files: passed. The unrestricted whole-worktree check encountered permission-denied paths in pre-existing C10 test artifacts; it is not reported as a whole-worktree pass. Existing Markdown hard-break spaces in unchanged AGENTS.md lines were left intact.
- Forty explicit new prompt-to-card checks pass; additional tests cover botanical exclusions, negation, source drift, predecessor preservation and unresolved campaign identity.
- The initial focused run had 84 passes and two failures caused by old fixture assumptions: a fixed count of 26 cards and an assumption that the first review row was legacy. Tests now explicitly preserve the old 26 cards and select the actual legacy source by ID. Production admission gates were not loosened.

### Retrieval-only performance

Fresh Python 3.14.6 process, monotonic `perf_counter`, forty distinct new prompts repeated five times:

| Measurement | Observed |
|---|---:|
| First in-process retrieval, after imports | 102.380 ms |
| Warm calls | 200 |
| Correct expected-card retrievals | 200/200 |
| Warm median | 16.435 ms |
| Warm p95, nearest-rank | 18.571 ms |
| Warm maximum | 21.267 ms |

The benchmark prohibited the socket connection helper; the focused regression also verifies offline operation and deterministic parallel retrieval. These are **knowledge-retrieval measurements**, not a new full-formula p95, fresh-process startup benchmark, live-browser test or sensory-quality benchmark.

### Preservation

The inventory, compounding-hold manifest, frozen construction library, initial research plan and v1 subtype extension match their starting hashes. All **573 discoverable formula files** also match the starting ordered path/hash manifest (`3a9bfd2c17c74b7ea365537fdaaeef52a905eef93b0ecb1dedf058d5ec99ab8b`). Existing unrelated dirty work remains in place.

The source and tests were verified locally. No full project verifier, Docker smoke, live app restart, model training, physical trial, sensory evaluation, purchase, compounding, commit or push was performed. This is not merge/release-level acceptance.

## Remaining work

1. Recover the exact accepted CHIMIE L'HOMME brief/formula, then select relevant existing cards and identify its real gaps.
2. Complete a dedicated cananga/ylang product comparison. Do not manufacture an equivalent grade.
3. Deepen abstract-limited tropical, peony and freesia findings with exact species/cultivar/product evidence.
4. Review missing botanical families before extending the frozen taxonomy.
5. Continue the 89 original non-extended gap entries. Existing cards can also be deepened; a card count is not scientific completeness.
6. Any numerical calibration or sensory-performance promotion needs a separate applicable-data, rights, correction/retraction and controlled-observation review.

## New source register

Descriptions below identify the bounded material reviewed, not a claim that the complete articles or every page section were read. Source metadata hashes are local record hashes, **not publisher-page byte hashes**.

1. [Quan et al. (2023): volatile differences among four Rosa chinensis cultivars](https://pubmed.ncbi.nlm.nih.gov/37251764/) — `rose_cultivars_floral_v2`; primary indexed abstract; research finding.

2. [Improvement of Ylang-Ylang Essential Oil Characterization by GCxGC-TOFMS](https://pmc.ncbi.nlm.nih.gov/articles/PMC6270406/) — `ylang_fractions_floral_v2`; selected primary sections; research finding.

3. [Weng et al. (2021): volatile compounds in 26 Freesia cultivars and eight hybrids](https://pubmed.ncbi.nlm.nih.gov/34361635/) — `freesia_cultivars_floral_v2`; primary indexed abstract; research finding.

4. [Volatile Composition and Classification of Paeonia lactiflora Flower Aroma Types (2023)](https://pubmed.ncbi.nlm.nih.gov/37298360/) — `peony_cultivars_floral_v2`; primary indexed abstract; research finding.

5. [Volatile composition and classification of Lilium flower aroma types (2019)](https://pubmed.ncbi.nlm.nih.gov/31645964/) — `lily_cultivars_floral_v2`; primary indexed abstract; research finding.

6. [Joulain (2008): Flower scents from the Pacific](https://pubmed.ncbi.nlm.nih.gov/18618387/) — `pacific_flowers_floral_v2`; primary indexed abstract; research finding.

7. [Transcriptome analysis of Polianthes tuberosa during floral scent formation (2018)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6124719/) — `tuberose_development_floral_v2`; selected primary sections; research finding.

8. [Tokitomo et al. (2005): odor-active constituents in fresh pineapple](https://pubmed.ncbi.nlm.nih.gov/16041138/) — `pineapple_recombination_floral_v2`; primary indexed abstract; research finding.

9. [IFF LMR: Narcisse Abs Conscious CSM](https://www.iff.com/scent/lmr-compendium/narcisse-abs-conscious-csm/) — `iff_narcisse_floral_v2`; selected primary sections; manufacturer/official-brand description.

10. [Givaudan: Cyclamen Aldehyde Extra](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/cyclamen-aldehyde-extra) — `givaudan_cyclamen_floral_v2`; selected primary sections; manufacturer/official-brand description.

11. [Givaudan: Peonile](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/peoniletm) — `givaudan_peonile_floral_v2`; selected primary sections; manufacturer/official-brand description.

12. [dsm-firmenich: Clearwood 970953](https://studio.dsm-firmenich.com/product/clearwoodr-pe-970953) — `dsm_clearwood_floral_v2`; selected primary sections; manufacturer/official-brand description.

13. [IFF LMR: Cedarwood Oil Atlas Org](https://www.iff.com/scent/lmr-compendium/cedarwood-oil-atlas-org/) — `iff_cedar_atlas_floral_v2`; selected primary sections; manufacturer/official-brand description.

14. [Givaudan: Orcinyl 3](https://www.givaudan.com/fragrance-beauty/eindex/orcinyl-3) — `givaudan_orcinyl_floral_v2`; selected primary sections; manufacturer/official-brand description.

15. [dsm-firmenich: Salicynile 981050](https://studio.dsm-firmenich.com/product/salicyniler-pe-981050) — `dsm_salicynile_floral_v2`; selected primary sections; manufacturer/official-brand description.

16. [Givaudan: The Journey of Patchouli, chypre architecture account](https://patchouli.givaudan.com/staticweb/patchouli/) — `givaudan_chypre_floral_v2`; selected primary sections; manufacturer/official-brand description.

17. [Symrise: Rose Oxide L technical sheet](https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Rose_Oxide_L.pdf) — `symrise_roseoxide_floral_v2`; selected primary sections; manufacturer/official-brand description.

18. [IFF: Hexenyl Salicylate CIS-3](https://www.iff.com/scent/ingredients-compendium/hexenyl-salicylate-cis-3/) — `iff_hexenylsal_floral_v2`; selected primary sections; manufacturer/official-brand description.

19. [CHANEL: No. 5 Eau de Parfum, US product 125430](https://www.chanel.com/us/fragrance/p/125430/n5-eau-de-parfum-spray/) — `chanel_n5_floral_v2`; selected primary sections; manufacturer/official-brand description.

20. [Creed: Aventus Cut Different, Aventus architecture description](https://www.creedfragrance.com/c/journal/aventus-cut-different/) — `creed_aventus_current_floral_v2`; selected primary sections; manufacturer/official-brand description.

21. [Creed: Aventus collection, Aventus-specific description](https://www.creedfragrance.com/c/fragrances/aventus-collection/) — `creed_aventus_collection_floral_v2`; selected primary sections; manufacturer/official-brand description.
