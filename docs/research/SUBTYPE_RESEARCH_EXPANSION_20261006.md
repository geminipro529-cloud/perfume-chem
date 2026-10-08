# Subtype research expansion — 6 October 2026

Status: implemented offline advisory research extension. This is not a claim that the full research programme, empirical perfume prediction, personal selection or commercial release is complete.

## Outcome

Added **26 subtype cards across nine construction packages**, backed by **18 new source records**: eight primary studies and ten manufacturer pages. Seventeen new sources support bounded summaries; the remaining manufacturer page is explicitly held. The extension also reuses 31 existing source records under their existing review limitations. Each card distinguishes source evidence from a formulation hypothesis, identifies functional roles and unwanted drift, and proposes a comparison question.

The knowledge pack now contains **133 source records, 126 claims, 43 profiles and 25 exact material cards**. Source-review states are 68 reviewed advisory, 64 legacy advisory and one HOLD. These are not 133 research papers or 68 validated models.

## What was deepened

| Package | Added distinctions |
|---|---|
| Lavender | Cologne; green barbershop; vanillic resin; soft musk; orange blossom; iris texture; incense; licorice |
| Citrus products | Green versus ripe mandarin; grapefruit peel versus juice facets; yuzu-specific identity |
| Green | Galbanum bitter-green resin; watery violet leaf separate from petal powder |
| Orange flower | Distilled neroli; petitgrain flower-to-leaf bridge |
| Jasmine | Grandiflorum texture; tea-green jasmine |
| Muguet | Soft muguet versus green-watery floral support |
| Orchard fruit | Ripe apple/cider boundaries; pear-to-musk continuity; restrained fruit-to-floral heart |
| Berry | Cassis bud-green versus juice; floral-green raspberry complexity |
| Tea | Floral-green tea; sun-dried black tea; roasted Dong Ding oolong |

These are functional distinctions, not new numerical scores. Existing 49-package and 275-scope planning records remain unchanged. Of the initial 155 gap entries, 26 now have additional partial research cards and 129 do not. None has been declared exhaustively reviewed or empirically validated.

## Research that changed the guidance

- **Galbanum:** odor-directed analytical work supports investigating character-impact trace compounds instead of reconstructing odor from the largest chromatographic peaks. Oil and resinoid remain different. [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/19173603/).
- **Grapefruit and yuzu:** separate source matrix and specific citrus identity; neither juice observations nor a generic terpene profile calibrates an alcoholic perfume. [Grapefruit study](https://pubmed.ncbi.nlm.nih.gov/11312864/), [yuzu study](https://pubmed.ncbi.nlm.nih.gov/19203264/).
- **Raspberry:** realism includes more than sweet berry character; the food-domain findings motivate a floral/green omission comparison, not a perfume formula. [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/32763731/).
- **Jasmine:** species-specific flower emissions and a manufacturer's extracted product description answer different questions. [Species study](https://pubmed.ncbi.nlm.nih.gov/25583067/), [exact grandiflorum absolute](https://www.iff.com/scent/lmr-compendium/jasmin-absolute-egypt/).
- **Tea:** cultivar-dependent floral character, sun-dried black tea and roasted Dong Ding require separate targets. Selected recombination/omission sections are more useful than treating analytical abundance as aesthetic importance, but their matrix transfer is unresolved. [Floral tea study](https://pubmed.ncbi.nlm.nih.gov/35566160/), [black tea section 3.4](https://pmc.ncbi.nlm.nih.gov/articles/PMC9222254/), [oolong section 3.5](https://pmc.ncbi.nlm.nih.gov/articles/PMC10486682/).
- **Apple:** manufacturer descriptions expose side-character risks in Manzanate and Fructone. Their names do not establish pure apple or pear identity, nor a reseller's exact grade. [Manzanate](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/manzanate), [Fructone](https://www.iff.com/scent/ingredients-compendium/fructone/).
- **Product identity:** flower oil, leaf/twig oil and flower absolute must not be collapsed. Violet leaf is not violet powder. [Neroli](https://www.iff.com/scent/lmr-compendium/neroli-oil-tunisia/), [petitgrain](https://www.iff.com/scent/lmr-compendium/petitgrain-bigarade-oil-tunisia/), [violet leaf](https://www.iff.com/scent/lmr-compendium/violet-leaf-absolute-egypt/).

Commercial lavender examples reuse the existing bounded local review; they were not re-certified as current bestseller evidence. A design may omit Ambrox without claiming that a referenced proprietary perfume contains none.

## Source conflict retained

The IFF Key Distilled Lime Mexico Org page names a distilled product and lists hydrodistillation, but its expertise paragraph describes cold pressing. It is recorded as `iff_lime_conflict_subtypes`, **HOLD**, not selectable evidence. Clarification from the supplier is needed; this is not a safety finding and does not mark any owned material depleted. [Source](https://www.iff.com/scent/lmr-compendium/lime-oil-key-distilled-mexico-org/).

## Runtime integration

- New immutable extension: `data/formulation_knowledge/subtype_research_v1.json`.
- Validated loader: `engine/formulation_intelligence/subtype_research.py`.
- The extension binds exact parent-library, plan and source-record hashes.
- Retrieval requires all concept groups: “lavender incense” selects that branch; plain “lavender” does not activate all eight additions. Existing explicit-avoid and negation masking remains upstream.
- Up to four cards are returned by default. Relevance orders retrieval, not perfume quality.
- Changed, missing or withheld source records remove their dependent cards. A malformed extension does not erase independent valid literature.
- Formula Studio, goal analysis and durable-job fingerprints include the extension. The UI displays evidence, hypothesis, comparison question and limitations only in optional research details.
- No runtime web requests, new pipeline scripts, automatic material aliases, density assumptions, dose rules, liking labels or physical actions were introduced.
- New sources use original summaries only. Six new research records use primary abstracts; two use selected full-text sections. No full-text review of all eight, exhaustive correction/retraction census, publisher-page byte archive, empirical dataset license or calibrated model admission is claimed.
- Firecrawl metadata retrieval was tried for the black-tea paper; its passage tool returned no full text. Selected primary sections were subsequently verified directly on PMC. No delegated model or forbidden fallback was used.

## Verification

The first focused engine run had 292 passes and one outdated registry test failure: it assumed all retained sources must be usable. The production HOLD was correct. The test now checks the exact lime HOLD, exact source binding and false authority, while still requiring all other current sources to be usable. Its complete 23-test file passed on rerun. Across the ten selected files there are **293 distinct passing engine tests**, including 63 new subtype tests.

Selected backend tests: **15 passed, 9 deselected**, covering source/reference fingerprints, knowledge jobs, the existing Formula Studio path and a new lavender-incense API case. A separate exact-node served-UI/assets check also passed: **16 distinct backend checks** in total. This is not the full backend suite.

Focused Ruff passed; mypy passed for the new engine module and two changed backend services; JavaScript syntax passed. Scoped tracked-file `git diff --check` passed. Initial pytest cache write warnings were avoided in subsequent runs by disabling that cache; no cache directories or unrelated user files were deleted.

Offline knowledge retrieval benchmark: 26 requests, ten measured repetitions each (260 calls), p50 **23.24 ms**, p95 **33.79 ms**, maximum **41.37 ms**. Serial and four-thread canonical results were identical. These measurements cover knowledge retrieval only, not full-formula execution or sensory performance.

No migration was needed. Docker, full project verifier, live UI restart, model training, sensory trials and physical compounding were not performed. No merge/release readiness or empirical improvement is claimed.

## Preserved state and next work

Inventory, compounding exclusions, the three commercial registries, the original construction library, frozen plan, both earlier progress records and prior-research index remain byte-identical to the prior checkpoint. Existing formulas were not edited; the Orris Liquid exclusion remains active. No Git commit or push was made.

The successor progress record keeps the outstanding work explicit. Highest-value later tranches are remaining orchard/tropical fruit distinctions; floral extraction/fraction variation; woods/resins/leather; and the remaining lavender branches. Quantitative transfer or physical validation requires its own scope and authorization, not merely more written cards.
