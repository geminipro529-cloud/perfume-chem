# Perfume-Chem fragrance knowledge expansion plan — 6 October 2026

## Decision and scope

Build a source-bound construction library, not a flat list of notes and not a universal perfume-beauty model. Lavender is the first completed advisory tranche. The broader library must distinguish botanical/product identity, odor profile, construction roles, chassis, temporal behavior and empirical applicability.

A classification wheel, an official note pyramid, a manufacturer's odor description, a demonstration formula and a measured sensory study are different evidence objects. They may complement one another; none can silently substitute for another.

“All structures” is an open-ended research ambition, not a finite fact that can be certified from one session. This plan defines an auditable initial coverage target and a continuing update process. It does not claim that every historical fragrance, floral chemotype, commercial captive or regional style has been reviewed.

No formula, bottle, inventory, stock preparation or physical experiment is changed or authorized by this plan. Existing R5/R6 and other formulas remain comparators. The new lavender pack is advisory; numeric calibration and release, safety, compounding and evidence-admission authority remain false.

## 1. Current-source baseline and real gaps

The audit used local files and AST/JSON inspection, not historical coverage claims. The pinned repository HEAD is 1ed79650313c23b1a2fe1c36c2e90a606c64833b; the worktree already contains unrelated user modifications, which this task does not reset or rewrite.

| Surface | Current representation | What the count does not establish |
|---|---|---|
| engine/families/registry.py | 38 archetype keys; 14 brief defaults | Thirty-eight empirically validated families or complete reconstruction recipes |
| docs/fragrance_families_reference.md | 22 broad numbered family chapters | Current stock buildability or reviewed quantitative claims |
| data/knowledge_graph/accords.json | 18 family categories, 20 accord sketches, five modern-niche categories, excluding metadata keys | Licensed, calibrated or source-complete executable capabilities |
| engine/research/composition_planner.py | Ten curated concepts, including one dry-lavender concept | Coverage of all lavender styles; that concept is not a universal chassis |
| Prior research corpus index | 128 source-byte-indexed records | Full-text review, empirical evidence admission or runtime authority |
| Reviewed literature pack before this work | 31 sources, 36 claims, 11 profiles, 11 material descriptions | Broad reviewed lavender coverage |
| Reviewed literature pack after this work | 66 sources, 62 claims, 30 profiles, 17 material descriptions | Validated doses, brand replicas or complete generative coverage |

The counts are different views of the project and must not be added together as a scientific coverage number.

The largest gap is not that Perfume-Chem has never heard of rose, citrus or amber. Broad labels already exist. The gap is the lack of consistently source-bound subtype, identity, functional-role, chassis and negative-space records that the compiler can use without defaulting to a familiar generic recipe.

### Gap labels to use

- ABSENT_REVIEWED_PROFILE: no corresponding profile in the reviewed offline pack.
- LEGACY_SKETCH_ONLY: a family/accord exists but lacks the new evidence and construction contract.
- SUBTYPE_COMPRESSED: different flowers, species, products, textures or chassis share one coarse descriptor.
- SOURCE_OR_VERSION_UNBOUND: an asserted fact is not pinned to exact source/edition scope.
- QUANTITATIVE_CAPABILITY_UNAVAILABLE: useful architecture clues exist, but no applicable calibrated endpoint exists.
- COMPILER_CONSTRAINT_NOT_WIRED: retrieved advice is not yet enforced as a protected recognizer, forbidden drift or role constraint.

A subtype can have more than one gap. Existing iris/violet and orchard-fruit profiles are useful; they still require quantitative applicability and generic compiler work.

## 2. Replace a flat taxonomy with six linked axes

Use six independent axes rather than forcing every perfume into one mutually exclusive bucket:

1. **Identity/recognizers:** lavender, rose, pear, iris root, violet petal, citrus peel, etc.
2. **Chassis:** cologne, classical fougere, modern aromatic, chypre, resinous amber, floral bouquet, woody musk, gourmand, leather, etc.
3. **Material/product identity:** chemical/isomer, natural species/plant part/extraction, commercial grade, base and exact stock lot.
4. **Texture and modifier:** green, powdery, creamy, metallic, watery, dry, resinous, lactonic, animalic, saline, etc.
5. **Temporal and delivery scenario:** opening, heart, drydown; bottle, film, headspace and delivered concentration remain separate.
6. **Evidence/authority:** official architecture clue, source-defined material description, heuristic construction hypothesis, measured endpoint and calibrated capability.

“Lavender iris amber” can therefore preserve lavender as recognizer, iris as a bridge and resinous warmth as a base without mistaking all three words for interchangeable material families.

The [official Fragrances of the World wheel](https://www.fragrancesoftheworld.com/Docs/Fragrance-Wheels-2024.pdf) is useful classification provenance, not a source of formula proportions. Historical terminology remains searchable. Modern labels do not rewrite older evidence.

## 3. Detailed family and subtype research backlog

This is the initial comprehensive backlog, not a claim that the following reviews have already been completed. The first release should aim at approximately 120–160 nonredundant subtype cards after deduplication; the exact number is determined by useful distinctions, not a score or ingredient-count target.

### 3.1 Aromatic and lavender structures

| Work package | Required distinctions | Present gap and questions |
|---|---|---|
| Lavender material register | L. angustifolia, lavandin cultivar, spike lavender, EO versus absolute/extract, standardized/blended product | First advisory review completed; lot compositions and whole-product endpoint applicability remain unbound |
| Classical fougere | Lavender/aromatic recognizer, coumarinic contrast, moss/wood foundation, geranium bridges | Legacy archetypes exist; review exact historical/demo sources and modern restricted-material alternatives |
| Green barbershop fougere | Rosemary/petitgrain/clary-sage lift, geranium clarity, dry moss/woods | New lavender profile is advisory; determine when green support becomes medicinal or bitter |
| Modern mineral aromatic | Lavender plus pepper/citrus, Ambrox-grade bridge and transparent woods | New advisory profile; Ambrox dose, delivered exposure and receptor/liking claims unavailable |
| Soft vanillic or resinous lavender | Vanilla/coumarin warmth versus benzoin/labdanum/styrax/opoponax | New profile; separate resin identities and sweetness from actual persistence |
| Clean musky lavender | Linen, skin, powder, metallic versus warm musk textures | New profile; no “more musk is better” default |
| Lavender floral | Orange blossom, jasmine/sandalwood, iris/powder, rose/geranium branches | New profiles preserve differences; larger floral subtype library still missing |
| Lavender fruit/gourmand | Apple, pineapple, vanilla, coffee/milk, licorice | New distinct profiles; prevent fruit soup, sweetness drift and dessert defaults |
| Lavender resin/wood | Incense, oud/dark wood, dry spice/vetiver, conifer, tea, hay/tobacco, suede | Incense/oud/spiced profiles added; several linked subbranches need their own source review |
| Non-lavender aromatics | Clary sage, rosemary, basil, thyme, mint, shiso, tarragon, anise/fennel | Broad aromatic vocabulary is not a complete botanical/role library; no automatic lavender substitution |

Primary questions: which sensory descriptors are observed, which trace constituents or product methods are relevant, how does the reference use lavender structurally, and what is explicitly unknown? Include a declared Ambrox-free design branch, not an unsupported “brand contains no Ambrox” assertion.

### 3.2 Floral structures

| Work package | Subtypes and product distinctions | Specific review needed |
|---|---|---|
| Rose | Damask EO versus centifolia absolute; fresh/dewy, lemony, green, jammy, honeyed, powdery, metallic, spicy, dark patchouli rose | GC-O/recombination evidence by product; role differences among rose alcohols, rose oxides and ionone/damascone bridges; exact grades |
| Jasmine | Grandiflorum versus sambac; fresh tea/green, fruity, petal, indolic, banana/tropical, leathery richness | Flower headspace versus absolute; extraction effects; methyl jasmonate/dihydrojasmonate grades and indole boundaries |
| Orange blossom / neroli | Flower absolute, distilled neroli, petitgrain leaf/twig; fresh citrus-floral versus honeyed/indolic | Plant-part identity, product composition, bridging roles and sensory masking |
| Tuberose / gardenia | Green watery tuberose, creamy white floral, salicylate/benzoate texture, indolic/animalic, modern transparent bases | Distinct flowers and bases; lactonic side-character limits; no base-to-natural equivalence |
| Ylang / tropical white floral | Ylang fractions, complete oil, cananga, tiaré, frangipani/plumeria | Extraction/fraction identity; banana, salicylate, phenolic and creamy axes; solar versus tropical drift |
| Muguet / cyclamen / watery floral | Historical hydroxycitronellal structures, modern muguet substitutes, cyclamen, wet-petal, watery musk | Exact material identity, current restrictions, demonstration formulas and how alternatives preserve or lose functions |
| Peony / magnolia / freesia | Rose-adjacent transparency, citrus-petal magnolia, peppery freesia hypotheses | No assumption that a flower-name base supplies a complete natural composition; source role maps |
| Hyacinth / narcissus / jonquil | Green stem, phenylacetaldehyde-like effects, narcissus absolute, hay/leather/animalic tones | Sensomics and limits of trace impact; prevent generic white-floral compression |
| Carnation / lily / spicy floral | Eugenolic carnation, rosy-spice, salicylate lily, lily-of-the-valley homonym separation | Appropriate botanical and construction identities; restricted-material-aware alternatives |
| Mimosa / cassie / heliotrope / linden | Pollen, honey, powder, anisic/balsamic, almond, green tea | Distinguish actual naturals from heliotropin/ionone simulations; avoid blanket powder defaults |
| Iris / orris / violet | Root/butter, irone isomers, cosmetic powder, transparent woody iris; violet petals versus violet leaf | Existing reviewed pack retained; exact grade and stock holds continue; no CAS-only or role-only substitutions |
| Floral aldehydic / bouquet | Fatty/waxy/soapy aldehydes, rose/jasmine/muguet balance, classical and modern transparent bouquets | Chassis documentation, recognizer preservation, compatible examples and ingredient-removal sensitivity |

The primary [Damask-rose trace-odorant study](https://pubmed.ncbi.nlm.nih.gov/31185719/) illustrates why a flower profile is not reducible to its largest GC peaks. SciSpace indexed a supporting-information DOI; the primary article DOI is 10.1021/acs.jafc.9b03391. Its blooming-flower stimulus is not automatically a rose-oil, absolute or finished-perfume profile.

### 3.3 Amber and musk structures

| Work package | Required separation | Review questions |
|---|---|---|
| Resinous amber | Labdanum/benzoin/vanilla; styrax, opoponax, tolu/peru balsam; resin versus distilled oil | Which resin/product/stock contributes warmth, smoke, animalic, sweetness or texture? What is a demonstrated accord versus an inferred one? |
| Soft or powdery amber | Coumarin, heliotrope, iris, musks; vanilla without heavy resin | How is softness achieved without excessive sugar or powder? |
| Floral / spicy amber | Rose or white-floral/resin bridge; cardamom/cinnamon/clove and balsamic support | Preserve flower/spice recognizers and relevant safety scope; no universal “oriental” recipe |
| Ambergris / ambroxide | Natural ambergris tincture versus ambroxide stereochemistry/grades, Cetalox, Ambrofix, Ambrox Super and newer products | Exact supplier identity; salty/mineral/warm descriptors, grade differences, solubility and applicable measured evidence |
| High-impact amberwoods | Individual woody-amber products and grades; dry, sharp, velvety, mineral, sandal/cedar-like facets | Supplier and primary chemistry; trace role, masking, fatigue, measurement floor; not resinous amber or proof of projection |
| Musk architecture | Macrocyclic, alicyclic, polycyclic and other identities; clean/metallic, fruity, powdery, warm/skin, animalic | Human sensitivity variation, exact grades, pairwise role nonredundancy, fruit/wood/floral bridges and omission controls |

A resinous amber, Ambrox-type effect, strong amberwood and a musk are not interchangeable fixes. This distinction is the next high-priority implementation tranche because “amber” currently hides several incompatible interventions.

### 3.4 Citrus and freshness structures

| Work package | Required distinctions | Review questions |
|---|---|---|
| Species / peel identity | Bergamot, lemon, lime, orange, mandarin, grapefruit, bitter orange, citron/cedrat, yuzu and regional citrus | Species, plant part, origin and product-specific odorants; peel bitterness, zest, juice and pith are distinct |
| Processing / grade | Expressed, distilled, folded, terpeneless, FCF, rectified, fractional products | Composition and oxidation; FCF label scope does not mean blanket safety or identical scent |
| Citrus cologne / aromatic | Classical eau de cologne, aromatic citrus, citrus/neroli/petitgrain, modern fresh woods | Chassis and heart bridges; distinguish lightness from short life and source concentration from delivery |
| Persistent citrus illusion | Citrus-associated long-lived materials, aldehydes, floral/woody bridge materials | A citrus-family label or low vapor pressure does not prove a fixative or preserve the same citrus recognizer |
| Green / leafy freshness | cis-3-hexenol/esters, galbanum, violet leaf, leaf/stem effects, cut grass, conifer | Exact chemistry and products; juicy peel versus vegetal drift; no all-green-material equivalence |
| Aquatic / ozonic / mineral / solar | Marine/saline, melon-water, rain/ozone, airy mineral, sun-warmed salicylate textures | Named effects often are constructed metaphors; source-bound material roles, no fabricated “sea receptor” map |

### 3.5 Other structural coverage

| Work package | Subtypes to cover | Missing or under-specified layer |
|---|---|---|
| Chypre | Classical moss/labdanum/citrus, floral, fruity, green, leathery, modern moss substitutes, patchouli musk | Legacy examples exist; “chypre” and any patchouli perfume must not collapse together |
| Woods | Cedar dry/pencil, sandal creamy/dry, vetiver root/smoke/citrus, patchouli earthy/clean, guaiac smoky, conifer resin | Species, fractions, commercial grades and functional bridges |
| Oud | Natural species/processing/age, clean woody reconstructions, medicinal/animalic, rose/amber/spice styles | Product/authentication uncertainty and substitute roles; “oud base” is not analytical equivalence |
| Leather / suede | Smoky tar, quinoline bitter-green, soft suede, saffron/iris/floral leather | Exact identities, current restrictions and grades; texture versus smoke/animalic dominance |
| Incense / resins | Frankincense oil/resinoid, myrrh, opoponax, elemi, church smoke, dry mineral incense | Extraction and heat-context distinction; burning resin is not bottled oil |
| Tobacco / hay | Leaf, cured/dry tobacco, sweet pipe, smoke, coumarinic hay, beeswax | Product identities and separate sweet/smoky/green axes |
| Fruit | Orchard pear/apple, lychee/rose, berries, peach/apricot lactonic skin, plum, grape, tropical, rhubarb, dried fruit | Existing orchard claims expanded by exact odorant, facet, persistent bridge and off-target risk |
| Tea / coffee / cacao | Black/green tea, mate, brewed versus roasted coffee, cacao/nut, milk modifiers | Brew/headspace/extract distinctions; food evidence is transfer research, not direct perfume proof |
| Gourmand / edible | Vanilla/tonka, caramel, toasted sugar, nuts, chocolate, bread, dairy, honey/maple | Sweetness versus edible recognizer; no ingredient-count or generic pleasure default |
| Boozy | Rum/cognac/whisky, wine/cider, fermentation traces, aromatic “liqueur” construction | Solvent flash versus intended boozy odor; no ethanol-smell realism shortcut |
| Animalic / skin | Civet/castoreum/ambergris identities, animalic substitutes, skin musk, sweaty/salty facets | Material provenance, ethical/legal scope, dose-specific roles and personal variability |
| Aldehydic / powder / abstract | Waxy/citrus aldehydes, cosmetic powder, paper/chalk/metal/mineral metaphors | Distinguish recognizer, texture and mechanism; abstract descriptor is not a chemical family |
| Cultural / emerging hybrids | Attar, cologne/fougere/amber hybrids, incense-floral, tea-musk, modern regional styles | Document exact product/context rather than adding invented universal categories |

## 4. How to conduct every work package

Use one common evidence workflow. It prevents both superficial catalog copying and endless re-review of unchanged sources.

### A. Source discovery and research questions

For each card, answer:

1. What is the exact chemical/product/flower/reference identity?
2. Which traits are observed versus marketed versus hypothesized?
3. What are the recognizable facets and unwanted drifts?
4. Which materials play recognizer, bridge, texture, diffusion-support and base roles?
5. Are interactions measured, demonstrated in a published formula, or heuristic?
6. Which preparation, concentration, matrix, scale and time window support the evidence?
7. What cannot be concluded, and what small comparison would resolve the largest uncertainty?

Search question templates:

- “Which compounds are aroma-active in [exact species/product] according to GC-O and recombination or omission experiments?”
- “How do [extraction/grade A] and [B] differ in composition and sensory character?”
- “Which primary human studies examine [descriptor/intensity/liking] for [stimulus] across concentration?”
- “What exact marketed architecture and edition does [reference] disclose?”
- “What licensed demonstration formula documents [chassis], and what recognizer changes under omission?”
- “What corrections, retractions or source-identity conflicts apply to [DOI/dataset]?”

Use exact names, synonyms, identifiers and multiple languages where helpful. A search returning mostly aromatherapy or antimicrobial papers does not answer a fine-fragrance construction question.

### B. Source priority and acceptance

1. Primary chemistry/sensomics and human sensory studies.
2. Official manufacturer technical sheets, exact product identity and licensed demonstration formulas.
3. Official brand pages for advertised architecture only.
4. Author/publisher repositories and licensed historical sources.
5. Reviews and established books for discovery and context, followed by primary checks.
6. Retailer/user note tables for leads only, never quantitative or sensory authority.

Check corrections/retractions before admission. Do not infer permission to train, reproduce full tables or distribute numerical data from a page being viewable.

For inaccessible texts: record ABSTRACT_ONLY or SELECTED_SECTIONS, access date and the unanswered question. Do not write “full literature reviewed” or derive constants from an abstract.

### C. Versioned evidence objects

Extend the existing contracts additively; do not create a parallel script pipeline:

- SourceArtifact: canonical URL/DOI, publication/correction status, capture type, actual artifact hash when captured, license, access/review scope.
- ClaimCard: exact original summary, source IDs, identity/product/condition scope, uncertainty and excluded conclusions.
- MaterialRoleCard: scaffold/product, odor facets, functional roles, compatible bridges and prohibited automatic substitutions.
- StructureCard: recognizer, chassis, anchors, mobile sockets, negative space, temporal hypothesis and reference-edition scope.
- DemonstrationFormulaCard: exact licensed source, active-material basis, working-stock mapping and reproduction status.
- EvaluationCard: endpoint, study domain, splits, observations and applicable capability; independent of an architecture card.
- ReviewConflict: contradictory pages, reformulation/grade uncertainty and adjudication status.

Never invent a source-byte hash. A hash of an original summary is a summary hash, not a publisher PDF or authenticated brand-page hash. Page updates make new source versions.

### D. Construction reasoning

For each structure, produce:

- Brief and recognizer map.
- Identity/evidence matrix.
- Chemical-family-to-odor-to-role graph with heuristic edges marked.
- Chassis and protected-anchor description.
- Conservative, literal, interaction-aware, minimalist and exploratory alternatives when useful.
- Hard-gate/negative-space report.
- Separate endpoint/Pareto comparison, not a hidden weighted beauty sum.
- Target-independent inventory mapping.
- Small experiment and stop conditions.

Architecture evidence can justify “try this bridge” or “this risks vanilla drift.” It cannot supply a measured intensity, optimal dose, consumer preference or four-hour skin claim.

## 5. Integration into existing code

### 5.1 Immediate work completed

- Added nineteen lavender profiles and their bounded claims/sources to data/formulation_knowledge/literature_v1.json.
- Kept source-based material descriptions independent of owned stock facts.
- Repaired returned-profile/claim/source integrity above the former twelve-claim cut-off.
- Added no-Ambrox prefix/suffix handling without erasing the positive lavender request.
- Added dedicated retrieval, identity, offline and authority regression tests.

This reaches the existing literature consumers. It is not a new quantitatively validated formula generator.

### 5.2 Next integration surfaces

| Existing surface | Required change | Acceptance |
|---|---|---|
| literature_knowledge.py and pack | Versioned cards; exact source/conflict scopes; preserve all required links while limiting irrelevant context | Referential integrity; no missing source silently presented as authoritative |
| semantic_brief_adapter.py | Resolve identity, chassis, modifier and negative space separately; preserve the user's exact words | “Lavender” cannot force fougere; “amber” cannot force Ambrox; negation preserved |
| family_architecture.py and adapters | Populate source-bound recognizers, anchors, module envelopes, forbidden drift and temporal relations | Generic structures, not one-off formula-name branches |
| material_capability_index.py | Exact grade/product/role compatibility and applicability; distinguish not owned, held, depleted and unknown | No chemical-family, CAS-only or supplier-name auto-substitution |
| constraint_solver.py / candidate critic | Hard constraints before ranking; protected recognizers and sensory-risk hypotheses distinct from measured gates | Never trade an explicit prohibition for a better heuristic score |
| composition_planner.py | Migrate curated concepts into data-driven structure cards, retaining compatibility | No new fixed default multi-musk/floral/amber stack |
| Formula Studio / goal analysis | Short interpretation card, selected clues, target/build distinction, source expansion on demand | Same request yields consistent evidence context; no runtime web calls |
| engine/families/registry.py | Versioned source-bound archetype metadata and scoped legacy adapters | Historical numbers do not become calibrated sensory gates |
| prior_research_corpus_v1.json | Explicit reviewed-versus-indexed states and source-byte drift | Indexing cannot promote a document to empirical evidence |
| Scientific capability path | Independent admission of release, intensity, descriptor and liking models | Architecture knowledge cannot bypass unit, identity, range or matrix gates |

Actual module/class names must be verified at the implementation checkpoint; this table is not permission to overwrite user-modified files.

### 5.3 Target, inventory build and bottle modes

- Ideal targets are stock-independent active amounts.
- Current builds bind exact products, stocks, bases and carriers.
- Dilution recommendations are not claims that stocks were prepared.
- w/w active mass from a volume requires a bound density, or use measured stock mass.
- Liquid µL and crystal mg remain separate.
- Evolving-bottle proposals contain only additions; subtraction-dependent requests return an explicit limitation.
- A known user compounding hold remains active even if literature/product identity becomes clearer.
- No arbitrary laboratory-photo/lot requirement is added to informal personal clue generation.

A source-bound profile cannot bypass inventory or physical-action checks. Conversely, missing empirical calibration must not block a clearly labeled creative hypothesis.

## 6. Scientific capabilities and validation

Keep this path separate:

stock/constituent accounting → matrix equilibrium → finite transfer/depletion → delivered gas concentration → detection diagnostic → individual intensity → mixture intensity challengers → character → pleasantness → personal liking.

For every endpoint, require exact identity, unit, phase, range and preparation/scenario applicability. Missing vapor pressure, MW, density, threshold or composition remains unknown, not zero/default.

The [Wakayama correction](https://doi.org/10.1021/acs.iecr.0c05822) requires explicit ng/L-to-µg/L threshold round trips. A lavender-oil dose cannot be supplied directly to a molecular gas-intensity curve. OAV is a diagnostic only, not importance, beauty or an optimization weight.

The [finite skin evaporation/permeation study](https://ciencia.ucp.pt/pt/publications/evaporation-and-permeation-of-fragrance-applied-to-the-skin/) supports a physical modeling direction, not universal parameter transfer.

The [2026 component/mixture character preprint](https://pubmed.ncbi.nlm.nih.gov/42465471/) is a baseline challenger in its experimental domain, not validated sixty-row drydown prediction. Keep strongest-component, partial-addition and primacy intensity alternatives individually inspectable.

[Johnson, Hirson and Ebeler's primary GC recomposition-olfactometry study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0042693) supports testing emergent mixture interactions through selective recombination. A chemical peak list is not a finished scent: full recombination, omission/addition and sensory checks address different questions.

### Practical validation ladder

1. **Source and contract checks:** identity, grade, version, license, links, corrections and false action-authority flags.
2. **Request interpretation:** explicit materials, negations, direction, preserve/avoid and temporal windows.
3. **Arithmetic/build invariants:** split-row/order/equivalent-stock invariance, active mass, carrier contributions and measurable quantities.
4. **Architecture regression:** matched requests must select different structures, not one generic high-scoring recipe.
5. **Licensed formula reproduction:** exact source target and active/raw arithmetic; no empirical similarity claim from arithmetic alone.
6. **Small blind comparisons:** recognizer, bridge or base omission/alternative tests, only after user authorization.
7. **Applicable instrumental and sensory capabilities:** hold out studies/molecules/palettes/lots/sessions as required.
8. **Selection validation:** random and simple-local comparators, equal budgets, selected outcomes and clustered uncertainty.
9. **Physical/commercial boundaries:** exact action authority and separately qualified safety/compliance work where requested.

Normal playful personal work can stop at a small hypothesis and short sensory reaction. Extensive formal protocols are required only for the stronger claim, not every experiment.

## 7. Staged work plan with explicit exit criteria

These knowledge tranches supplement, rather than rename or claim completion of, the earlier project checkpoints.

### K0 — Freeze the ontology and evidence inventory

Deliverables: current-source coverage audit, gap matrix, vocabulary/alias conflict list, reviewed-versus-indexed states and source contracts.

Exit: every current surface has a reproducible count; unsupported legacy numerical claims identified; no formula or inventory mutation.

Status here: audit and plan completed; comprehensive legacy-claim adjudication remains future work.

### K1 — Lavender advisory library

Deliverables: material-register review, representative current-edition matrix, nineteen distinct profiles, reference-scope limits and offline retrieval tests.

Exit: no generic lavender-to-fougere/Ambrox default; no unsupported chemical-absence claim; supporting claims/sources retained.

Status here: first advisory tranche implemented and focused-tested. Exhaustive historical census and calibrated construction remain open.

### K2 — Amber/musk and aromatic chassis

Priority: highest next step, because confusing resinous amber, Ambrox and strong amberwoods causes large formulation drift.

Deliverables: exact grade cards, resin/ambergris/amberwood/musk separation, classical/modern fougere and aromatic role graphs; no default musk stack.

Exit: requests such as “lavender vanilla without Ambrox,” “mineral lavender without vanilla,” “dry green fougere” and “soft skin lavender without laundry” follow genuinely different constraint paths.

### K3 — Floral subtype library

Deliverables: the twelve floral work packages above, exact botanical/product distinctions and restrained versus dominant floral roles.

Exit: jasmine is not tuberose, neroli is not orange-blossom absolute/petitgrain, violet leaf is not violet petal, iris grades stay separate, and user-held materials remain excluded.

### K4 — Citrus, green, watery and fruit continuity

Deliverables: six freshness packages plus fruit-facet cards; peel/juice/pith and matrix/processing differences; persistent-bridge hypotheses with no invented longevity.

Exit: sour peel, sweet flesh, green leaf, tropical/lactonic drift and clean-shampoo drift remain distinguishable. No “low VP therefore fixes citrus” shortcut.

### K5 — Woods, chypre, resins and specialty structures

Deliverables: the remaining structural work packages, cultural/historical scope and emerging hybrids.

Exit: subtype recognizers and negatives are source-bound; leather/oud/incense/gourmand cannot be generic dark-base synonyms.

### K6 — Construction compiler and comparative proof

Deliverables: populated generic family graphs; brief/compiler/solver/critic integration; target/build/bottle adapters; deterministic, balanced regression corpus.

Initial regression target: 120 reviewed prompts, provisionally 40 lavender, 12 amber/musk, 32 floral, 16 citrus/fresh and 20 specialty/hybrid. Include positive/negative matched pairs, equivalents, ambiguity and unavailable-data cases.

Acceptance goals (not results claimed here):

- 100% preservation of explicit material, unit, quantity, prohibition and execution-mode constraints.
- At least 95% agreement on predeclared recognizer/chassis/time-window labels.
- 100% abstention on high-risk predeclared ambiguities.
- Zero chemical/grade/stock-hold bypass.
- Zero actions before required confirmation.
- Serial/parallel canonical equivalence.
- No network during normal request execution.
- Local interpretation and knowledge retrieval p95 at most 500 ms on a frozen corpus.
- Preserve the existing five-second warm formula-analysis target; retrieval timing alone cannot certify it.

Exit: a new request changes the structure for the right reasons; evidence can be inspected; no hidden beauty score or unsupported scientific default.

### K7 — Optional empirical improvement loop

Deliverables: authorized small controls/alternatives, blinded time-resolved observations, applicable headspace/character/intensity data and selected-outcome comparisons.

Exit: a model or proposal is promoted only for its tested endpoint/domain. Personal liking remains personal. No evidence means hypotheses, an unordered set or NO_CHANGE.

Physical purchases, mixing, skin testing and safety/release work require separate authorization. Software-complete and empirically validated remain separate completion states.

## 8. Research and plugin execution policy

- Local repository evidence and unchanged caches first.
- SciSpace/Consensus for discovery, followed by primary-source verification.
- GitHub for pinned source/dataset/implementation reads and license provenance; a repository existing is not a model being validated.
- MotherDuck only if a relevant user-owned dataset and the correct account are identified. Do not migrate JSON evidence, upload private inventory or create a database/flight just because the connector is present.
- Elicit/Scite access or plugin availability is not evidence; disclose access failures.
- Direct DeepSeek delegation only if the exact permitted route and completed receipt can be verified. If unavailable, continue locally; no provider/model substitution.
- Root Codex retains synthesis, final edits, evidence admission and verification.
- No web or literature scan during normal formula analysis. Reviewed manifests are local and versioned.
- No new standalone pipeline scripts; use existing engine/backend modules and existing CLI surfaces.

This turn's GitHub read successfully recovered the pinned baseline pack. SciSpace supplied paper leads, including a correction warning. MotherDuck did not produce a usable authenticated result after the requested retry; no remote dataset was read or written.

## 9. What would count as finished

For the knowledge expansion: the declared initial subtype scope has source-bound cards, conflict states, compiler constraints and passing regressions; remaining unreviewed domains are visibly unknown rather than omitted or invented.

For practical creative formulation: the system understands the brief, preserves recognizers and negative space, explains every ingredient's job, maps a target to exact available stocks and proposes a small measurable comparison without bureaucracy.

For scientific prediction: applicable, governed release and sensory capabilities demonstrate held-out endpoint improvement. Literature cards alone cannot confer this state.

For commercial release: separate qualified safety, regulatory, stability and manufacturing work. Perfume-Chem can organize evidence but cannot certify it automatically.

The next implementation checkpoint is K2 plus the generic recognizer/chassis/negative-space compiler wiring—not an attempt to train a universal perfume-beauty model or to expose hundreds of family names without construction knowledge.

