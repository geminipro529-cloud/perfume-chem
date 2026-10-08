# All-fragrance-domain research and implementation plan — 6 October 2026

## Outcome and authority boundary

Extend Perfume-Chem through a source-bounded, composable construction library and separately validated scientific capabilities. Do not choose a single impressive-sounding model as a universal formulation or perfume-quality oracle.

This is a research and planning artifact. It creates a backlog of **49 construction packages, 275 overlapping subtype scope entries, 14 scientific fronts, eight market segments, 13 delivery formats and 14 commercial-reference panel tracks**. The source inventory contains 28 scoped records, including reused reviews, abstracts, selected primary sections and discovery-only leads. It does not mean 28 full-text reviews, 275 validated fragrance families or 49 newly implemented runtime capabilities.

The companion machine-readable file is `data/formulation_knowledge/research_coverage_plan_v1.json`. It is not loaded into the runtime literature pack. Every proposed package remains explicitly not newly implemented by this plan. All release, safety, compounding and evidence-admission flags remain false.

The existing lavender review and offline knowledge changes remain intact. This plan extends the earlier `FRAGRANCE_KNOWLEDGE_EXPANSION_PLAN_20261006.md` without rewriting it. Its former approximate card-count target is not a quota: deduplicate the 275 scope entries into genuinely useful distinctions, never pad cards or ingredients to reach a number.

No formula, inventory, bottle, working dilution, purchase, empirical model, canonical evidence admission or physical experiment is changed or authorized here. No new pipeline script is introduced. Preserve unrelated worktree changes.

## 1. Recommended implementation: what to keep, build and compare

The strongest currently supportable starting point is a hybrid. “Best” means demonstrably useful for the requested endpoint and domain, not winner by model name or paper headline.

| Layer | Preferred first implementation | Challenger or alternative | Required boundary |
|---|---|---|---|
| Brief and family knowledge | Versioned local source cards, exact identities, typed role relationships, recognizers, protected anchors and negative space | Bounded semantic interpretation adapter | Explicit quantities, materials, negation, preservation and execution strategy cannot be overridden |
| Formulation construction | Reuse generic family/chassis and role-to-stock machinery; select a small set of meaningful alternative architectures | More elaborate constrained solver when existing search cannot satisfy a locked brief | Structural coverage is not sensory quality; target remains separate from inventory build |
| Gas release | Same-scenario measurements or parameter-complete equilibrium, finite mass balance, transfer and delivery models | Ideal Raoult and explicitly qualified Hansen scenarios | Matrix, geometry, substrate, time and unknown inputs remain visible |
| Intensity | Exact governed human gas-dose curves; strongest, fitted partial-addition and primacy alternatives kept separate | Small dose-aware model or frozen representation adapter | No direct liquid-dose-to-gas-curve shortcut, no universal OAV intensity transform |
| Character | Measured component-profile averaging baseline; separately test its concentration/intensity-aware variant | Frozen molecular/mixture encoders, then a small residual interaction model | Descriptor or distance performance does not become liking, beauty or full drydown validation |
| Pleasantness and preference | Applicable population prior and separately observed personal pairwise preference with ties | More complex preference model only after sufficient independent observations | Sales, branded notes and ingredient valence cannot supply human liking labels |
| Search | Hard feasibility and identity constraints, low-dimensional block search, separate Pareto endpoints | Equal-budget random, local and conservative adaptive arms | Evaluate selected outcomes and support, not only regression fit |
| User workflow | Offline interpretation card, strongest clue, one small evolving-bottle addition hypothesis and one observation | Optional expanded diagnostics or controlled experimental mode | No default photos, lots, paperwork, new bottles or lengthy questionnaires |

Use the existing implementation as a substrate, not as proof that these endpoints are validated. In particular, role-assignment scores and Pareto coverage in construction code are not empirical sensory scores. Do not replace missing labels with zero or 50/100.

## 2. Cover all perfume types through independent axes

A floral amber EDP positioned for mainstream consumers is simultaneously a flower-led identity, an amber construction, a delivery matrix and a market proposition. A single flat family label loses that information.

Store independent, linkable axes:

1. **Recognizers and negative space:** dominant identity, protected anchors, what must not appear.
2. **Chassis:** cologne, fougere, chypre, amber, bouquet, woody musk, leather, gourmand, abstract or declared hybrid.
3. **Exact material/product identity:** molecule/isomer, botanical species and part, extraction, commercial grade, specialty base and stock preparation.
4. **Texture and secondary facets:** green, watery, powdery, creamy, dry, metallic, resinous, smoky, animalic and similar terms.
5. **Temporal/delivery scenario:** opening, heart, late heart and drydown; bottle, film, interfacial equilibrium, headspace and delivered concentration remain separate.
6. **Market/consumer scope:** mass-retail, mainstream designer/prestige, niche and other positioning; not a sensory family.
7. **Product format and use context:** hydroalcoholic fragrance, oil, solid, mist and other matrices.
8. **Evidence and authority:** documentary clue, manufacturer description, construction hypothesis, human observation or applicable numerical capability.

Gendered commercial positioning is recorded as positioning, not inferred as a biological odor rule. An unusual hybrid can be represented without being forced into the nearest pre-existing recipe. Unknown or unsupported branches remain visible.

The official [Fragrances of the World taxonomy](https://www.fragrancesoftheworld.com/Docs/Fragrance-Wheels-2024.pdf) is classification provenance, not formula percentages. This turn checked official index/file metadata, but PDF screenshot extraction failed; no claim is made to have reviewed every wheel label visually or reproduced the wheel.

## 3. Complete initial construction-research backlog

Priority 1 means shared infrastructure or immediate project relevance; it does not imply that lower-priority fragrances are inferior. “Reviewed advisory partial” retains the useful existing review but is not an empirical promotion. “Legacy sketch review required” means a family exists in older code/documentation, not that the current construction contract is complete.

| Package | Research subject | Proposed subtype scope | Priority | Current review state |
|---|---|---|---|---|
| AR_LAVENDER | Lavender material registers and structures | soliflore; cologne; classical fougere; green barbershop; vanillic resin; soft musk; orange blossom; iris; apple; pineapple; incense; coffee milk; licorice; mineral ambrox; spiced wood | 1 | REVIEWED_ADVISORY_PARTIAL |
| AR_FOUGERE | Fougere chassis | classical; green dry; modern mineral; tonka sweet; floral fougere; leathery | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| AR_HERBS | Other aromatic/herbal structures | clary sage; rosemary; basil thyme; mint; anise tarragon; tea herbal | 2 | REVIEW_REQUIRED |
| FL_ROSE | Rose structures | fresh dewy; green; lemony; jammy fruity; honeyed; powdery; metallic spicy; dark patchouli | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| FL_JASMINE | Jasmine structures | grandiflorum; sambac; tea green; fruity petal; indolic; leathery | 1 | REVIEW_REQUIRED |
| FL_ORANGE | Orange-flower structures | distilled neroli; orange blossom absolute; petitgrain bridge; honeyed indolic; transparent citrus floral | 1 | REVIEW_REQUIRED |
| FL_TUBEROSE | Tuberose structures | green watery; creamy; indolic animalic; modern transparent | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| FL_GARDENIA | Gardenia structures | green petal; creamy white floral; modern reconstruction | 2 | REVIEW_REQUIRED |
| FL_TROPICAL | Ylang and tropical floral structures | ylang fractions; ylang complete; cananga; tiare; frangipani; solar floral | 2 | REVIEW_REQUIRED |
| FL_MUGUET | Muguet/cyclamen/watery flowers | classical muguet; modern muguet; cyclamen; wet petal; transparent floral; watery musk | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| FL_LIGHT | Peony, freesia and magnolia | dewy peony; rose adjacent peony; peppery freesia; transparent freesia; citrus magnolia; creamy magnolia | 2 | REVIEW_REQUIRED |
| FL_GREEN | Hyacinth, narcissus and jonquil | green hyacinth; narcissus absolute; jonquil; hay leathery flower | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| FL_SPICY | Carnation and lily | carnation; rose spice; salicylate lily; green lily | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| FL_POLLEN | Pollen/powder/honey flowers | mimosa; cassie; heliotrope; linden; pollen honey | 2 | REVIEW_REQUIRED |
| FL_IRIS | Iris, orris and violet | root butter; cosmetic powder; transparent woody iris; violet petals; violet powder; violet leaf; orris grade differences | 1 | REVIEWED_ADVISORY_PARTIAL |
| FL_BOUQUET | Bouquets and floral aldehydic structures | classical bouquet; transparent bouquet; floral aldehydic; soft floral; woody floral musk | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| AM_RESIN | Resinous amber | labdanum benzoin vanilla; styrax; opoponax; tolu peru balsam; dry resinous; animalic resinous | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| AM_SOFT | Soft/powdery amber | coumarinic; heliotropic; iris musky; soft vanillic | 1 | REVIEW_REQUIRED |
| AM_FLORAL | Floral/spicy amber | rose amber; white floral amber; dry spice amber; balsamic amber | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| AM_AMBERGRIS | Ambergris and ambroxide | natural tincture; ambroxide stereochemistry; commercial grade differences; mineral warm construction | 1 | REVIEWED_ADVISORY_PARTIAL |
| AM_WOODS | High-impact amberwoods | dry sharp; velvety woody; mineral; sandal cedar associated; trace support | 1 | REVIEW_REQUIRED |
| MU_MUSK | Musk identities and architectures | macrocyclic; alicyclic; polycyclic; metallic clean; fruity; powdery; warm skin | 1 | REVIEW_REQUIRED |
| CI_PRODUCTS | Citrus species and product processing | bergamot; lemon lime; orange mandarin; grapefruit bitter orange; citron cedrat; yuzu regional citrus; processing grades; peel juice pith | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| CI_CHASSIS | Citrus construction styles | classical cologne; aromatic citrus; neroli petitgrain; fresh woody; persistent citrus illusion | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| GR_GREEN | Green leafy structures | cut grass; leaf stem; galbanum; violet leaf; fig green; conifer green | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| WA_AQUATIC | Aquatic/ozonic/mineral/solar structures | marine saline; melon watery; rain ozone; airy mineral; solar salicylate; dry mineral | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| FR_ORCHARD | Orchard-fruit structures | pear peel; pear juice flesh; pear persistent bridge; apple skin; apple juicy body; ripe apple; lychee floral; fruit heart continuity | 1 | REVIEWED_ADVISORY_PARTIAL |
| FR_BERRY | Berry/rhubarb/grape structures | blackcurrant; red berries; raspberry; rhubarb; grape; berry floral | 2 | REVIEW_REQUIRED |
| FR_TROPICAL | Tropical/melon fruit structures | pineapple; mango; passionfruit; melon; banana; tropical citrus | 2 | REVIEW_REQUIRED |
| FR_STONE | Stone/dried fruit structures | peach skin; apricot osmanthus; plum; cherry; dried fruit; lactonic flesh | 2 | REVIEW_REQUIRED |
| CH_CHYPRE | Chypre structures | classical; floral; fruity; green; leathery; modern moss alternatives | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| WO_CEDAR | Cedar/conifer/dry woods | cedar pencil; dry transparent woods; conifer resin; guaiac smoke; pale woods | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| WO_SANDAL | Sandalwood structures | natural species; creamy; dry transparent; synthetic grade alternatives | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| WO_VETIVER | Vetiver structures | root earthy; citrus fresh; smoky dry; fractionated clean | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| WO_PATCH | Patchouli structures | earthy leaf; clean fractions; amber bridge; floral chypre bridge | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| WO_OUD | Oud structures | natural product variation; clean woody; medicinal animalic; rose amber; spiced | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| LE_LEATHER | Leather and suede | smoky tar; bitter green; soft suede; saffron leather; iris leather; floral leather | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| RE_INCENSE | Incense and resin structures | frankincense oil; frankincense resinoid; myrrh opoponax; elemi; church smoke; mineral incense | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| TO_HAY | Tobacco, hay and beeswax | dry leaf; sweet pipe; smoky tobacco; coumarinic hay; beeswax | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| GO_VANILLA | Vanilla/tonka/sugar gourmand | vanilla botanical products; tonka coumarinic; caramel toasted; dry edible; sweet floral gourmand | 1 | LEGACY_SKETCH_REVIEW_REQUIRED |
| GO_ROAST | Roasted coffee/cacao/nuts | brewed coffee; roasted coffee; cacao chocolate; almond; hazelnut; toasted grain | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| GO_DAIRY | Dairy/honey/gourmand textures | milk cream; honey; maple; buttery texture | 3 | REVIEW_REQUIRED |
| BO_BOOZY | Boozy and fermentation structures | rum cognac; whisky; wine cider; liqueur aromatic | 3 | REVIEW_REQUIRED |
| SP_SPICE | Dry/warm/fresh spice structures | cardamom; pepper; ginger; cinnamon clove; saffron; cool spice | 2 | LEGACY_SKETCH_REVIEW_REQUIRED |
| TE_TEA | Tea, mate and aromatic infusions | green tea; black tea; oolong; mate; smoky tea; floral tea | 2 | REVIEW_REQUIRED |
| AN_SKIN | Animalic and skin structures | civet castoreum identities; animalic substitutes; skin musk; salty sweaty; ambergris associated | 3 | LEGACY_SKETCH_REVIEW_REQUIRED |
| AB_ABSTRACT | Aldehydic/powder/abstract effects | waxy aldehydic; citrus aldehydic; cosmetic powder; paper chalk; metal mineral; conceptual atmosphere | 3 | LEGACY_SKETCH_REVIEW_REQUIRED |
| CU_TRADITIONS | Regional/traditional perfume constructions | exact attar traditions; hydrodistillation carrier context; regional floral oils; rose oud traditions; historical materials | 2 | REVIEW_REQUIRED |
| HY_HYBRIDS | Custom and hybrid structures | floral gourmand; tea musk; incense floral; fruity fougere; rose mineral; leather floral | 2 | REVIEW_REQUIRED |

These entries overlap by design: lavender-iris can be reached from both aromatic and iris work. Canonical relationships should prevent duplicate cards while preserving distinct recognizer, modifier and chassis roles.

For every package produce:

- A locked recognizer/negative-space card with temporal intent.
- An exact material/product roster, source status, uncertainty and unavailable functions.
- A chemical-family-to-function map; heuristic interactions are explicitly marked.
- At least a conventional control and one meaningfully different construction alternative where useful. Do not invent many variants merely for volume.
- Masking/drift risks and the smallest informative omission, addition or range experiment.
- A parser/compiler regression packet and explicit quantitative applicability limits.

Naturals require species, plant part, extraction and grade distinctions. Trade bases require exact product evidence; a family name on the bottle does not establish composition. No botanical or commercial product automatically inherits a molecular curve.

## 4. Research on all scientific and practical fronts

| Front | Subject | Minimum required decision boundary |
|---|---|---|
| RF01_IDENTITY | Chemical, stereochemical, botanical, commercial-grade and stock identity | Exact identities, admitted aliases, carriers/bases, source conflicts and separation of target from build |
| RF02_SENSOMICS | GC-MS, GC-O, recombination and omission/addition | Peak amount is not sensory importance; unknown constituents and unknown odor events retained |
| RF03_PHYSICS | Equilibrium, finite release, delivery and substrate | Matrix/geometry/time-specific mass conservation; no missing-property defaults |
| RF04_INTENSITY | Detection and human gas-dose intensity | Compatible OAV diagnostic; admitted exact gas curves; corrected threshold equation; separate mixture challengers |
| RF05_CHARACTER | Concentration-aware character and temporal identity | Simple profile baseline first; endpoint/coverage limits and human labels |
| RF06_LIKING | Population pleasantness and personal preference | Independent human labels, individual variability, blinded protocol and explicit ties |
| RF07_EXPECTATION | Brand, familiarity, language, packaging and context | Separate blinded sensory result from branded consumer concept/market response |
| RF08_SEARCH | Experiment design and conservative optimization | Leakage-safe splits, equal-budget random/local/adaptive arms, Pareto endpoints and selected-outcome metrics |
| RF09_STABILITY | Solubility, crystallization, oxidation and packaging | Exact product/matrix behavior and measured homogeneity; no universal shelf-life/solubility claim |
| RF10_SAFETY | Safety/regulatory and supplier documentation | Independent current reviewed policy, exact limits/aliases and finished-product assessment; never creative beauty authority |
| RF11_MARKET | Mass, mainstream/prestige, niche and regional positioning | Time/region/channel/franchise scope; no sales-derived liking label |
| RF12_FORMAT | Delivery formats and use scenarios | Hydroalcoholic EDP/EDT, oil, solid, mist, hair/textile and functional matrices are not interchangeable |
| RF13_ENGINEERING | Offline retrieval, versioning, compiler and deterministic execution | Exact fingerprints, explicit source/review states, no runtime web calls and focused tests |
| RF14_PRACTICE | Measurable compounding and evolving-bottle workflow | µL liquids/mg solids, proper stock arithmetic, additive-only deltas, no duplicate transfer and proportionate questions |

These fronts apply across the family packages rather than being repeated as independent mini-engines for each perfume.

### Essential literature conclusions

**Character should start simple, then earn complexity.** The 2026 [linear-mixture preprint](https://pmc.ncbi.nlm.nih.gov/articles/PMC13371102/) tests 432 mixtures, with no more than ten components at moderate intensities. It supports testing component-vector averaging; it does not prove a 63-stock perfume drydown model. Its displayed manuscript license is CC BY-NC 4.0. Dataset, code and model rights require separate review before commercial reuse; no data or weights were imported here. An independently implemented method and a licensed dataset are different objects.

**Learned representations are challengers, not a substitute for dose evidence.** The [Principal Odor Map paper](https://pubmed.ncbi.nlm.nih.gov/37651511/) prospectively evaluates single-molecule descriptor prediction. [Sisson et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC11904650/) study labeled molecular pairs. These support representation research, not automatic complete-perfume liking or concentration calibration. Source/split/artifact review is needed before an adapter can compete locally.

**Finite release is necessary for performance research.** [Teixeira et al.](https://sigarra.up.pt/fmup/pt/pub_geral.pub_view?pi_pub_base_id=64696) validate diffusion in controlled systems up to eleven chemicals. [Almeida et al.](https://ciencia.ucp.pt/en/publications/evaporation-and-permeation-of-fragrance-applied-to-the-skin/) study three odorants in ethanol using porcine-skin cells. The [radial diffusion study](https://aiche.onlinelibrary.wiley.com/doi/10.1002/aic.17351) covers limited pure/binary/ternary systems. These are useful physical precedents, not blanket validation of human skin projection or longevity.

**Matrix coefficients must stay in their domain.** The [DPG matrix study](https://pubs.acs.org/doi/10.1021/acs.iecr.5b03852) measures one-to-four-ingredient systems in DPG. Its partition relations cannot be silently substituted for ethanol/water EDP behavior. UNIFAC used in a paper does not mean the installed Hansen heuristic is UNIFAC.

**Population and personal liking remain separate.** [Cross-cultural monomolecular research](https://pubmed.ncbi.nlm.nih.gov/35381183/), [perfume/body-odor interaction research](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0033810), [binary-mixture pleasantness](https://pubmed.ncbi.nlm.nih.gov/32188973/) and [regional human ratings](https://pubmed.ncbi.nlm.nih.gov/41169516/) have different stimuli and endpoints. A predictor that takes measured component sensations is conditional, not a formula-only predictor. None supplies a ready-made global finished-perfume beauty label.

**Brand effects need their own experiment.** The [odor-label experiment](https://pubmed.ncbi.nlm.nih.gov/15944134/) supports separating blinded sensory results from named/branded concept tests. Market familiarity and packaging are not folded into an alleged chemical pleasantness score.

**Analytical clues need reconstruction and omission.** The [orange-peel reconstitution/omission study](https://pubmed.ncbi.nlm.nih.gov/19061307/) and earlier [recomposition methodology](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0042693) support a mismatch loop. Peak area, molecule count and OAV alone cannot decide sensory importance or deletion.

**Selection quality needs a benchmark.** [Conservative objective modeling](https://proceedings.mlr.press/v139/trabucco21a.html) and [learning-to-rank optimization](https://proceedings.iclr.cc/paper_files/paper/2025/hash/768c19273e20fa09147885d03da7550f-Abstract-Conference.html) justify support control and selected-outcome evaluation. They do not validate a perfume optimizer by themselves. Keep random and simple-local comparators, fixed seeds and equal numbers of unique feasible evaluations.

The Wakayama corrected threshold and forward intensity evaluator remain mathematically separate. Wolfram's explicit symbolic calculation returned 7/5 for the threshold round trip and 1000 for the microgram-to-nanogram factor. This is algebra/unit verification only, not measured intensity admission or sensory validity.

### Standards, books and manufacturer sources

Use sensory standards for protocol metadata and scope, never copied standards text. Check current editions before implementation: profiling, paired direction, discrimination, threshold and hedonic protocols answer different questions.

The publisher page for [Calkin and Jellinek's Perfumery: Practice and Principles](https://www.wiley-vch.de/de/fachgebiete/naturwissenschaften/perfumery-978-0-471-58934-1) provides a useful chapter-level review queue. Only its description and contents were read here; no full-book review is claimed. Historical formula/palette and regulatory statements need modern corroboration.

[Exact manufacturer resources](https://www.dsm-firmenich.com/en/businesses/perfumery-beauty/ingredients.html) can establish grade, extraction and stated odor roles. Supplier claims are not independent consumer evidence. PerfumersWorld sourcing/prices/stock must be checked only for an actual shopping/build request, not assumed from a research card.

The [IFRA transparency list](https://ifrafragrance.org/transparency-list) and [standards library](https://ifrafragrance.org/standards-library) belong to distinct palette and safety-policy work. No new amendment-effective-date or compliance claim is made by this review.

## 5. Mass-market perfume coverage is a first-class research lane

“Mass market” has two meanings relevant to this project:

- **Mass-retail/value:** broad retail distribution and accessible price.
- **Mainstream popular designer/prestige:** familiar commercial perfumes such as Libre, Sauvage and Paradoxe, often what the user means by mass-market competitors.

Support both without turning either into a liking score. Also distinguish masstige, luxury designer, niche/artisan, ultra-premium, regional mainstream and affordable alternatives. These are planning axes, not verified assignments or value judgments.

### Current gap and required repair

The current commercial registry has five products and one lavender–amber panel, `global-lavender-amber-2026-v1`. It cannot supply family-matched references for every fragrance. The panel loader is intentionally closed; an unmatched concept must not inherit the lavender panel.

Separate these evidence dates:

```text
published_on
source_period_start / source_period_end
captured_on
reviewed_on
current_selection_expires_on
```

Also bind region, channel, metric and exact product/line/franchise scope. The existing registry has a historical FY24 source reviewed in 2026; review date cannot renew the age of that observation. Keep historical launch results as historical. Review the newer period before selecting a “current leader.”

A stored local summary hash is not a hash of raw webpage bytes. Preserve the actual capture basis, and leave raw artifact hashes unavailable when no raw artifact was archived.

### Fresh documentary market findings

The [L'Oréal 2025 Luxe report](https://www.loreal-finance.com/en/annual-report-2025/luxe/) and [annual results](https://www.loreal-finance.com/eng/press-release/2025-annual-results) identify major fragrance lines including Libre, MYSLF, Born in Roma and Paradoxe. They support mainstream reference selection, not exact-flanker liking or formula ratios.

The current [LVMH report](https://www.lvmh.com/static/letter-to-shareholders-january-2026/perfumes-and-cosmetics.html) describes Sauvage's **men's-fragrance** market position. Retain that narrower scope; do not relabel it as every fragrance worldwide or as the EDP's independent rank.

The [Coty FY2026 results](https://v2.coty.com/news/coty-announces-fourth-quarter-fiscal-year-2026-results) help distinguish prestige and mass-fragrance portfolios. They do not supply a global best-liked scent list.

The retracted original “Social success of perfumes,” DOI 10.1371/journal.pone.0218664, remains rejected. The actual [retraction notice](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0222524) has DOI **10.1371/journal.pone.0222524**. Commercial data availability and reproducibility problems disqualify the original as optimizer evidence.

### Family-matched commercial panel research queue

Every row below is **PLANNED_NOT_ADMITTED**. Product names are research leads, not new market/sales assertions or purchase recommendations. Exact concentration, edition/year, region and primary pages must be verified before panel admission. Niche examples are structural contrasts, never assumed mass-retail leaders.

| Track | Comparison subject | Proposed reference research queue |
|---|---|---|
| MP01_FRUITY_FLORAL | Mainstream feminine fruity-floral | Prada Paradoxe EDP; Marc Jacobs Daisy EDT; Versace Bright Crystal EDT; Chanel Chance Eau Tendre EDP |
| MP02_SWEET_FLORAL | Mainstream sweet-floral/gourmand | Lancome La Vie Est Belle EDP; YSL Black Opium EDP; Carolina Herrera Good Girl EDP; Viktor&Rolf Flowerbomb EDP |
| MP03_ROSE_PETAL | Rose/peony/fresh petal | Chloe EDP; Dior Miss Dior Blooming Bouquet EDT; PDM Delina EDP (structural neighbour, not an assumed mass-retail leader) |
| MP04_WHITE_FLORAL | White-floral volume and restraint | Dior J'adore EDP; Dior Pure Poison EDP; Gucci Bloom EDP |
| MP05_LAVENDER_AMBER | Lavender/aromatic/amber | YSL Libre EDP; Dior Sauvage EDP; Prada Luna Rossa Carbon EDT; Burberry Goddess EDP |
| MP06_MALE_FRESH | Mainstream masculine aromatic/fresh woody | Bleu de Chanel EDP; YSL MYSLF EDP; Armani Acqua di Gio EDP; Dior Sauvage EDP |
| MP07_MALE_SWEET | Mainstream masculine sweet/spiced | Armani Stronger With You EDT; JPG Le Male Le Parfum EDP Intense; Hugo Boss Bottled EDP; YSL La Nuit de L'Homme EDT |
| MP08_CLEAN_UNISEX | Clean/fresh broadly accessible unisex | Calvin Klein CK One EDT; Calvin Klein CK Be EDT; Exact family-matched contemporary sample to be selected |
| MP09_VALUE_MASS | Value/mass-retail fragrance | Adidas Ice Dive EDT; Nautica Voyage EDT; Bruno Banani Man EDT; David Beckham Instinct EDT |
| MP10_MISTS | Body/hair mist comparison | Sol de Janeiro Cheirosa 62 Perfume Mist; Bath & Body Works Japanese Cherry Blossom Fine Fragrance Mist; Victoria's Secret Bare Vanilla Fragrance Mist |
| MP11_IRIS_POLISHED | Iris/clean polished mainstream | Prada L'Homme EDT; Dior Homme Intense EDP (edition/year must be specified); Dior Homme Parfum (edition/year must be specified) |
| MP12_NICHE_NEIGHBOURS | Niche structural contrasts | Le Labo Santal 33 EDP; MFK Baccarat Rouge 540 EDP; Creed Aventus EDP; Frederic Malle Portrait of a Lady EDP |
| MP13_HERITAGE | Historical/classical structural controls | Chanel No. 5 EDP; Guerlain Shalimar EDP; Lanvin Arpege EDP; Houbigant Fougere Royale Extrait |
| MP14_REGIONAL_VALUE | Regional/value/alternative comparisons | Zara Red Temptation EDP; Lattafa Khamrah EDP; Armaf Club de Nuit Intense Man EDT; Al-Rehab Choco Musk perfume oil |

Build a panel from exact products, current market-selection provenance and family relevance, with no unnecessary franchise duplication. Keep personal comparison to at most four references. A target-centred comparison need not test every reference against every other reference.

Return separate documentary architecture, analytical composition, measured character/intensity, personal liking and target-population liking channels. DOCUMENT_ONLY gives architecture clues and questions to smell for, not a sensory winner. A consumer claim requires a suitable recruited population; one owner's ratings cannot establish broad market appeal.

## 6. Literature-first gate: internal work, not a burden on every bottle

The gate is for changing project behavior, publishing knowledge cards and promoting empirical capabilities. It must not make every playful formulation wait for a literature review or physical certification.

For each proposed package or behavior change:

1. Scope the question, endpoint, matrix, material/product and use case.
2. Read exact local prior artifacts first. Reuse them only when bytes, source revision and question still match.
3. Discover primary studies, official technical sources and exact product/edition pages. Select sources for the claim; a target publication count is not evidence quality.
4. Fetch and read the portions actually needed. Record abstract-only, selected-sections, full-text, paywall, extraction failure or unavailable status truthfully.
5. Check identity, source version, correction/retraction, rights, stimulus domain, concentrations, matrix, delivery conditions and population.
6. Separate source facts, literature-derived assumptions, manufacturer descriptions, architecture hypotheses and unknowns. Record contradictory evidence.
7. Bind source/transcription/capture hashes where artifacts exist. A hash of a short tool summary is not a publisher PDF hash.
8. Write the proposed behavior, alternatives, authority ceiling and tests before runtime edits.
9. Run focused checks for affected contracts, then integrate locally. Never let a discovery service or worker admit canonical evidence.
10. Promote numerical capability only after rights, exact applicability and held-out performance pass. Otherwise retain an advisory clue or explicit unavailable endpoint.

Proposed states:

```text
RESEARCH_SCOPED
SOURCE_REVIEWED
ARCHITECTURE_ADVISORY_READY
IMPLEMENTATION_REVIEWED
FOCUSED_VERIFIED
EMPIRICAL_CAPABILITY_HOLD
OUT_OF_DOMAIN
RETRACTED_REJECTED
```

This state machine is planned, not newly runtime-enforced by this document. Advisory software completion and empirical capability completion remain different.

Creative hypotheses remain possible when quantitative intensity or liking is unavailable. Missing gas data withholds gas prediction, not all creative work. Photos, invoice, lot, density and safety paperwork are requested only when the selected conversion, physical action or stronger claim genuinely depends on them.

## 7. Integrate into existing modules; avoid another parallel architecture

| Existing surface | Planned integration | Guard |
|---|---|---|
| `literature_v1.json` and `literature_knowledge.py` | Add reviewed source-bound family cards and exact role descriptions after each package review | Do not load the entire planning backlog as admitted runtime knowledge |
| `prior_research_corpus_v1.json` | Discover prior byte-pinned documents and identify review coverage | Indexing remains distinct from full-text review |
| `family_architecture.py` and `target_compiler.py` | Link recognizers, protected anchors, negative space, module relationships and temporal intent | No formula-name hard-coded scientific outcomes or latest-version fallback |
| `material_capability_index.py`, `formula_solver.py` and `composition_planner.py` | Map target roles to exact candidate products, preserve missing functions and alternative builds | Structural role coverage is not a beauty objective; target is not rewritten by inventory |
| `engine/research/perception.py` and capability manifests | Separate detection, intensity, character and liking applicability | No endpoint substitution, source-scale confusion or silent numerical default |
| `engine/research/selection.py` | Use feasible block candidates, equal budgets, uncertainty and selected-outcome metrics | No OAV, counts, popularity or generic valence in final liking selection |
| `commercial_references.py` and commercial registry | Add edition-scoped family panels and date/metric/source-scope handling | No sales-to-liking promotion; current panel closure preserved until tested |
| Existing durable engine jobs | Bind exact cards, references, capabilities, scenario, inputs, implementation and seeds | No arbitrary execution or runtime network research |
| Existing sensory/bottle lifecycle | Link optional quick observations and controlled evidence; additive-only exact-once delta flow | Analysis cannot physically commit a dose |

No new pipeline script, external reasoning provider dependency, mandatory plugin at runtime or universal “family beauty score” is proposed.

## 8. Ordered research and implementation batches

These are work batches within the existing project roadmap, not retrospective renumbering or declarations that earlier checkpoints passed.

| Batch | Research and implementation scope | Exit before dependent promotion |
|---|---|---|
| R0 — current baseline | Preserve existing lavender/iris/fruit work; inventory coverage and source access; publish this backlog | Planning counts and hashes reconcile; omissions and access limits visible |
| R1 — shared governance | Exact identities, source/capture/rights states, literature-first contract, market observation-versus-review dates | Invalid source/rights/version states cannot produce calibrated claims; historical records preserved |
| R2 — shared foundations | Distinct amber, ambergris, amberwood and musk roles; citrus product identity; core finite-release/intensity domain review | Source-bound cards and physical applicability contracts reviewed; no generic defaults |
| R3 — major flowers | Rose, jasmine, orange blossom, tuberose, muguet; extend iris/violet, gardenia and light-flower branches | Natural/grade/texture distinctions and recognizer/negative-space regressions |
| R4 — commercial fruit | Pear/apple/lychee, berry, stone/tropical fruit, citrus lift and fruit-to-floral/musk transitions | Realistic functional facets stay distinct; tropical, candy, shampoo and floral drift visible |
| R5 — aromatic/wood chassis | Fougere, chypre, sandalwood, cedar, vetiver, patchouli, oud and leather; reuse lavender review | No universal aromatic/mineral/amber chassis forced on other requests |
| R6 — specialist/cultural/format | Incense, spices, tea, hay/tobacco, gourmand, animalic, traditional constructions, custom hybrids; format-specific reviews | Unsupported traditional/format claims remain marked; no cross-matrix formula transfer |
| R7 — integrated compiler and panels | Wire reviewed roles/constraints into generic candidate generation and family-matched commercial evaluation | Topic-stratified request/generation tests and authority invariants pass |
| R8 — empirical learning | Separately authorized measurements and blind observations, representation challengers and search benchmarks | Rights-cleared, leakage-safe held-out improvement for the claimed endpoint |
| R9 — coverage acceptance | Freeze artifacts, omissions, regressions, performance and comparison results | Software coverage declared only for reviewed implemented scope; empirical gaps remain explicit |

Market-source collection runs alongside R2–R6, but panel admission waits for exact product/edition and freshness review. Do not make every family wait for all other reviews: admit small reviewed tranches independently.

The first implementation batch should be **R1 plus a bounded R2 foundation tranche and expanded fruity-floral/mainstream panel review**. It repairs the shared source/date/authority boundary before many cards inherit it, while supplying immediate CHIMIE Femme and lavender/amber value.

Rights or full-text gaps block the affected empirical import, not every other package. No automatic model training, purchase, physical compounding or sensory session is authorized by this plan.

## 9. Acceptance tests and enjoyable default workflow

### Planned development acceptance

- At least four reviewed positive/negative/constraint/hybrid prompt cases per construction package: a minimum initial 196-case architecture corpus, not synthetic sensory validation.
- Preserve explicit material identities, quantities, units, prohibitions and NEW_FORMULA/EVOLVING_BOTTLE strategy in 100% of applicable gold cases.
- Predeclare soft direction/time/reference labels and require at least 95% exact match on a held-out reviewed interpretation corpus. Do not let the same generator label and grade its own prompts.
- Predeclared high-risk ambiguity cases abstain; no action while confirmation is required.
- Exact aliases work; chemical family/CAS convenience must not merge product/grade conflicts.
- Out-of-domain, unsupported, retracted, unreviewed or unlicensed source states cannot become quantitative capability.
- No neutral fabricated result for missing intensity, pleasantness, liking, physics or restriction data.
- Market franchise scope does not become a flanker claim; expiration uses source period, not a refreshed review date.
- A family without an admitted panel returns a truthful missing panel, not lavender references by default.
- Direct and hybrid constraints remain inspectable; inferred relationships never acquire receptor or safety authority.
- Same-input/hash/seed results are deterministic; source, policy, capability and inventory drift invalidate exact caches.
- Runtime parsing/retrieval/panel comparison stays offline; proposed added-overhead target is p95 at most 500 ms and warm whole-formula target remains 5 seconds. These are future acceptance targets, not measurements claimed here.
- Focused schema/unit/integration/invariant checks precede affected performance tests. Run the full verifier only for merge/release-level claims.

### User-facing personal mode

Keep the default screen or chat answer short:

```text
Understood: the desired direction, preserve/avoid constraints and bottle mode
Strongest clue: one source-bounded formulation insight
Proposal: one measurable additive hypothesis, or a clear NO_CHANGE
Smell for: one or two observations at useful times
Limit: the relevant uncertainty or stop condition
```

A user may continue with one evolving bottle. Controlled comparison, retained pre-delta samples, analytical tests and population panels are optional stronger evidence paths, not mandatory for every experiment. Negative physical additions are never proposed; dilution or a new formula is offered only when the chosen goal requires it.

## 10. Research tools used and limits

The requested tools have distinct jobs. Using more plugins does not make weak evidence independent or scientific.

| Tool/provider | Actual use in this review | Limit |
|---|---|---|
| Local repository tools | Current contracts, coverage, commercial registry, affected modules and focused tests | Existing dirty worktree preserved; no whole-project empirical claim |
| Plugin Management | Named-provider discovery, including Undermind, Proto and Life Sciences Literature | Exact requested new providers did not expose callable tools; directory search is not exhaustive |
| Parallel Search | Two targeted market/taxonomy discovery queries | Discovery results checked against primary sources; no private formula or inventory transmitted |
| Firecrawl | One fresh bounded L'Oréal official-page scrape | No whole-site crawl, autonomous long research job or monitoring |
| Life Science Research / Amass | Topic abstracts and DOI-level records for POM and pair-GNN research | This is the available Amass tool, not a claim that the exact Life Sciences Literature connector ran |
| Consensus | One mixture-model discovery query and three paper-record fetches | Required fetches performed; paper methods and rights still need primary review |
| SciSpace | One finite-release/transfer literature query | Used for discovery; source scope independently checked where accessible |
| Wolfram | Explicit symbolic threshold and unit-factor verification | Initial context requests gave no useful result; later symbolic call succeeded; no empirical calibration |
| HAPI MCP Registry | Read-only PubMed-related server metadata discovery | No server installed, paid, authenticated or used as evidence; untrusted activation/payment instructions ignored |
| Undermind / Proto | Names and exact supplied plugin identifiers searched | No corresponding callable tool exposed; neither claimed as executed |
| DeepSeek / DeepLuna route | Health admission checked; failed transport | No prompt/model request transmitted, no alternate provider or fallback used |

No unnecessary provider was installed or connected. GitHub/MotherDuck/Computer and other unrelated actions were not invoked merely to increase plugin count. Current local source is the authority for repository behavior.

### Source inventory and review depth

The following records are a scoped bibliography, not a corpus admission. Null raw-artifact hashes in the JSON mean no publisher artifact was archived.

| Source record | Primary/official source or technical lead | Actual review scope |
|---|---|---|
| SRC01_WHEEL | [Official fragrance taxonomy](https://www.fragrancesoftheworld.com/Docs/Fragrance-Wheels-2024.pdf) | OFFICIAL INDEX AND FILE METADATA ONLY |
| SRC02_IFRA_PALETTE | [IFRA transparency list](https://ifrafragrance.org/transparency-list) | SELECTED PRIMARY PAGE SCOPE |
| SRC03_IFRA_STANDARDS | [IFRA standards library](https://ifrafragrance.org/standards-library) | SELECTED PRIMARY PAGE SCOPE |
| SRC04_LOREAL_MARKET | [L'Oreal 2025 Luxe annual report](https://www.loreal-finance.com/en/annual-report-2025/luxe/) | PRIMARY PAGE SCRAPED AND SELECTED SECTIONS |
| SRC05_LOREAL_RESULTS | [L'Oreal 2025 annual results](https://www.loreal-finance.com/eng/press-release/2025-annual-results) | SELECTED PRIMARY SECTIONS |
| SRC06_COTY_FY26 | [Coty Q4 fiscal 2026 results](https://v2.coty.com/news/coty-announces-fourth-quarter-fiscal-year-2026-results) | SELECTED PRIMARY SECTIONS |
| SRC07_LVMH_2025 | [LVMH 2025 fragrance report](https://www.lvmh.com/static/letter-to-shareholders-january-2026/perfumes-and-cosmetics.html) | SELECTED PRIMARY SECTIONS |
| SRC08_CULTURE | [Arshamian et al. cross-cultural pleasantness](https://pubmed.ncbi.nlm.nih.gov/35381183/) | PRIMARY ABSTRACT VIA LIFE SCIENCE INDEX AND PRIOR REVIEW |
| SRC09_BODY | [Lenochova et al. fragrance/body-odor interactions](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0033810) | PRIMARY ABSTRACT VIA LIFE SCIENCE INDEX AND PRIOR REVIEW |
| SRC10_BINARY | [Ma et al. binary-mixture pleasantness](https://pubmed.ncbi.nlm.nih.gov/32188973/) | PRIMARY ABSTRACT RECORD |
| SRC11_REGIONS | [Drnovsek et al. 909 individuals/16 regions](https://pubmed.ncbi.nlm.nih.gov/41169516/) | PRIMARY ABSTRACT RECORD |
| SRC12_LABELS | [de Araujo et al. cognitive odor-label effects](https://pubmed.ncbi.nlm.nih.gov/15944134/) | PRIMARY ABSTRACT RECORD |
| SRC13_CITRUS | [Dharmawan et al. orange peel reconstitution/omission](https://pubmed.ncbi.nlm.nih.gov/19061307/) | PRIMARY INDEXED ABSTRACT |
| SRC14_JASMINE | [Zhang et al. Jasminum sambac concrete](https://onlinelibrary.wiley.com/doi/10.1002/ffj.3631) | DISCOVERY ONLY PRIMARY FULL TEXT ACCESS FAILED |
| SRC15_INTENSITY_CORRECTION | [Wakayama 2020 correction](https://doi.org/10.1021/acs.iecr.0c05822) | REUSED PRIOR PRIMARY REVIEW |
| SRC16_RECOMBINATION | [Johnson et al. GC recomposition olfactometry](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0042693) | REUSED PRIOR PRIMARY REVIEW |
| SRC17_CONSERVATIVE | [Trabucco et al. conservative objective models](https://proceedings.mlr.press/v139/trabucco21a.html) | REUSED PRIOR PRIMARY REVIEW |
| SRC18_RANK | [Tan et al. offline optimization by learning to rank](https://proceedings.iclr.cc/paper_files/paper/2025/hash/768c19273e20fa09147885d03da7550f-Abstract-Conference.html) | REUSED PRIOR PRIMARY REVIEW |
| SRC19_RETRACTION | [Retraction: Social success of perfumes](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0222524) | PRIMARY NOTICE VERIFIED |
| SRC20_LINEAR_CHARACTER | [Pellegrino et al. 2026 linear mixture character preprint](https://pmc.ncbi.nlm.nih.gov/articles/PMC13371102/) | SELECTED PRIMARY RESULTS LIMITATIONS AND METHODS |
| SRC21_PAIR_GNN | [Sisson et al. 2025 deep learning for aroma-chemical blends](https://pmc.ncbi.nlm.nih.gov/articles/PMC11904650/) | PRIMARY INDEXED EXCERPTS AND AMASS ABSTRACT |
| SRC22_POM | [Lee et al. 2023 Principal Odor Map](https://pubmed.ncbi.nlm.nih.gov/37651511/) | PRIMARY ABSTRACT VIA AMASS AND FETCHED CONSENSUS RECORD |
| SRC23_DIFFUSION_2013 | [Teixeira et al. fragrance diffusion prediction and validation](https://sigarra.up.pt/fmup/pt/pub_geral.pub_view?pi_pub_base_id=64696) | AUTHOR INSTITUTION INDEXED ABSTRACT AND SCISPACE DISCOVERY |
| SRC24_DPG_2015 | [Costa et al. fragrance release from simplified DPG matrix](https://pubs.acs.org/doi/10.1021/acs.iecr.5b03852) | PRIMARY INDEXED ABSTRACT AND SUPPORTING INFORMATION SCOPE |
| SRC25_SKIN_2019 | [Almeida et al. evaporation and permeation applied to skin](https://ciencia.ucp.pt/en/publications/evaporation-and-permeation-of-fragrance-applied-to-the-skin/) | SELECTED AUTHOR INSTITUTION RECORD AND SCISPACE DISCOVERY |
| SRC26_RADIAL_2021 | [Almeida et al. radial fragrance diffusion prediction and validation](https://aiche.onlinelibrary.wiley.com/doi/10.1002/aic.17351) | SCISPACE ABSTRACT AND REUSED PRIOR PRIMARY REVIEW |
| SRC27_CALKIN_JELLINEK | [Calkin and Jellinek, Perfumery: Practice and Principles](https://www.wiley-vch.de/de/fachgebiete/naturwissenschaften/perfumery-978-0-471-58934-1) | PRIMARY PUBLISHER DESCRIPTION AND TABLE OF CONTENTS ONLY |
| SRC28_MANUFACTURER_RESOURCES | [dsm-firmenich exact ingredient and extraction resources](https://www.dsm-firmenich.com/en/businesses/perfumery-beauty/ingredients.html) | SELECTED PRIMARY RESOURCE PAGE SCOPE |

Paywalled jasmine full-text, failed taxonomy PDF extraction, direct publisher access errors and abstract-only learned-model reviews remain visible. A fetched paper record or indexed abstract is not silently relabeled full-text review.

## 11. Completed now versus future work

Completed now: all-domain coverage inventory; current commercial coverage/freshness audit; targeted primary research and tool availability checks; implementation choices and alternatives; staged work sequence; machine-readable planning artifact; focused current-source tests and plan-contract checks.

Not completed by this plan: all 49 full literature packages, runtime enforcement of the new proposed gate, new family panel admission, commercial rights clearance for external datasets/weights, training, full finite-release calibration, measured full-formula character/liking, sensory superiority, physical compounding, current IFRA clearance or commercial release.

The useful finish line is reviewed architecture software coverage plus explicit empirical coverage, not “we know every perfume.” An honest clue, qualified hypothesis, unordered set or NO_CHANGE is valid. Commercial and sensory claims advance only when matching evidence exists.

Verification details and exact local hashes are in `ALL_FRAGRANCE_DOMAINS_RESEARCH_AUDIT_20261006.json`.

