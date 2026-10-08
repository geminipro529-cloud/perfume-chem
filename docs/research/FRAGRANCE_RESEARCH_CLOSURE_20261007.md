# Fragrance research closure — 2026-10-07

## Outcome

The remaining **first-pass advisory knowledge coverage and integration work is complete**. The frozen 155-gap scope now has 155 partial subtype cards, plus five explicitly declared botanical additions: **160 cards across 49 packages**. This does not mean all perfumery, full-text review, empirical modeling or sensory validation is complete.

This pass added **94 cards**: the 89 previously uncovered frozen entries and five botanicals. It added **58 source-review records**, eight source-bound deeper-review addenda, strict v3 predecessor validation, durable-job fingerprint coverage and optional UI rendering.

No formula, inventory, bottle event, purchase, physical experiment, numerical calibration or scientific/release authority was changed. The dirty worktree was preserved; no commit or push was made.

## What is covered

| Area | What this pass adds |
|---|---|
| Floral breadth | Cananga, lilac, honeysuckle, sweet pea, champaca and white Michelia alba |
| Floral specificity | Deeper ylang, tiare, frangipani, peony and freesia review; species, cultivar, cut-flower/heating and extract limits retained |
| Aromatic and citrus | Rosemary, basil/thyme, mint, anise/tarragon, cedrat, partial lemon/lime, neroli/petitgrain and fresh woody transitions |
| Fruit and gourmand | Rhubarb, grape, berry bridges, mango, passionfruit, melon, banana, stone fruits, vanilla products, caramel, coffee, cacao, nuts, honey and maple |
| Woods, resins and leather | Named cedar, guaiac and vetiver products; sandal textures; oud branches; distinct balsams; leather, incense and tobacco links |
| Musk, amber and abstract styles | Musk-class identity, restrained amber branches, mineral/solar interpretations, aldehydes, skin concepts, paper/atmosphere |
| Tradition and hybrids | Carefully dated attar/material evidence, modern rose-oud interpretations, tea-musk, incense-floral and rose-mineral comparisons |

Every new card has a protected target, a comparison against a control, a question, a stop condition, negative space and identity/evidence limits. These are **testable design hypotheses**, not supplier-derived dose recipes or sensory rankings.

## Source quality and limits

The library now contains **212 source metadata records, 205 bounded claims, 43 existing profiles and 25 exact material cards**. The profile and exact-material counts are unchanged: research prose has not been promoted to stock aliases or calibrated material properties.

Review states: **147 reviewed-advisory, 64 legacy-advisory, one HOLD**. The contradictory older lime source remains withheld. The 58 additions comprise 33 research records, 22 manufacturer/brand records and three institutional documents. Three records are deeper method reviews of papers already indexed; they are **not three new independent experiments**.

Some reviews are abstract-only or selected-section reviews. An exhaustive current correction/retraction audit and full empirical-data rights clearance were **not** completed. No numerical thresholds, food OAVs, analytical peak percentages, receptor affinities or supplier use levels were admitted to perfume optimization.

Important distinctions retained:

- Cananga and ylang products can share an INCI without being interchangeable fractions or grades.
- Gardenia taitensis concrete is not living-flower headspace, monoi or a coconut accord.
- Peony and freesia cultivar/sampling variation prevents one universal floral profile. Peony water-threshold references are not gas-dose intensity data.
- Fresh and dried Magnolia alba preparations used different sampling conditions; analytical differences do not demonstrate a superior perfume ingredient.
- Food aroma studies provide bounded clues and useful experimental methods, not ethanol-perfume formulas.
- Supplier mineral, metallic, smoky and clean descriptors are attached only to their exact products. Mineral is not automatically assigned to Ambrox, nor metallic to Habanolide.
- Historical documents and exhibition interpretations do not establish exact recipes or cultural/population preference.

Not selected: the internally inconsistent anise/tarragon candidate DOI 10.4103/drj.drj_390_24; inaccessible full-text stereochemistry work DOI 10.1002/hlca.19800630721 was not promoted; the retracted Boswellia review DOI 10.1155/2013/140509 was not used. The EMA item is explicitly a **historical draft identity section**, not a current effective safety policy.

## What actually changes in Formula Studio

The new registry is active in offline retrieval. The API returns its source-bound cards and addenda; the UI displays them under **Research behind this design · optional details**. Normal output remains bounded. Durable job reference fingerprints include v3 so cached jobs cannot silently reuse a different research revision.

The v1 and v2 files remain byte-identical. V3 verifies both predecessors and the original construction/coverage plan, preserves all 66 prior cards and preserves the unresolved CHIMIE L'HOMME identity hold. Addenda bind both their exact earlier card and their own source records; a failed addendum does not erase independently supported older evidence.

The research is **not yet a new subtype-aware numerical composition solver**. It does not automatically change stock choices, roles or amounts. Turning qualitative source findings into automatic doses would require a separate justified and tested integration.

## Paired benchmark: advice versus composition

The corpus was frozen before execution: 12 prompts, DEEP_COMPOSE, one variant, maximum 12 materials, nominal 6,000 µL design basket, unchanged inventory, no conversation history. Both arms used the **same current code, literature and reviews**; only the immutable v2 versus active v3 subtype registry changed. This is a controlled registry ablation, not a replay of an old installation.

| Result | Observation |
|---|---:|
| Prompts | 12 |
| Actual design calls, including reverse-order repeat | 48 |
| New research guidance | 11/12 |
| Generic floral prompt with no invented botanical specificity | 1/1 |
| Material/physical-row changes | 0/12 |
| Role-assignment changes | 0/12 |
| Complete formula object changes | 0/12 |
| Identical reverse-order reruns | All |
| Network calls | None permitted |
| Watched source/formula/inventory changes during run | None |
| Sensory improvement | NOT TESTED |

Diagnostic warm p95: **2.933 s for v2 and 2.844 s for v3**. These twelve prompts are not a full-corpus performance certification; the small difference is not a speedup claim.

Conclusion: **more specific and auditable advice, with no demonstrated composition improvement**. All 12 outputs remained design hypotheses, not physical-build or sensory-success certificates.

- [Frozen corpus](../../tests/fixtures/subtype_comparison_v1.json)
- [Complete paired receipts](subtype_comparison_20261007.json)
- [Reproducible diagnostic module](../../engine/research/subtype_benchmark.py)

Run the diagnostic in a separate process: `python -m engine.research.subtype_benchmark`. It prints JSON, writes no files and forbids network calls. Do not run its temporary registry override inside a shared API process.

## Acceptance evidence

- Baseline before this pass: 154 focused tests passed.
- Current final engine slice: **434 passed** in 91.93 s.
- Current backend/API/UI contract slice: **16 passed**, 29 deselected, in 45.94 s.
- Targeted Ruff: passed.
- Changed engine-module mypy: passed, using explicit namespace-package bases.
- Changed backend-module mypy: passed in its Poetry environment.
- JavaScript syntax: passed.
- Quick project verification: **10 checks passed, no failed checks**; golden output unchanged.
- Changed-file `git diff --check`: passed.
- Full verifier, Docker, migration cycle and browser visual interaction were not run for this scoped research change. No schema migration was added and no merge/release readiness is claimed.

The initial backend test attempt failed before executing test bodies because an older pytest scratch directory was inaccessible. A fresh unique scratch directory resolved this without weakening production gates. Whole-worktree Git inspection also encountered inaccessible historical verification scratch; the exact changed-file diff check passed. These warnings are not hidden test successes.

Quick report: `output/research_closure_20261007/project_verification_quick.json` (scope partial; completion gate NOT_EVALUATED).

## Preserved state

- `inventory.txt`: a07a862febe2e6da3b6301a1189b2cb330a55a801f5126b89ccd57751f0591bb
- 573 formula files: aggregate 3a9bfd2c17c74b7ea365537fdaaeef52a905eef93b0ecb1dedf058d5ec99ab8b
- Orris Liquid compounding hold unchanged.
- V2: 6a7da23c4dbc7f205390cc2502f2b4d451025741eb3aa2cc1b60d89eb9e4d6c2
- V3: e70ddbfcb56b026003dc91785441e2da58c9292584112d2ae3afa66f86499f22
- Literature: 767e188b161fab7dd907a6a7668b5f80a9ea3a6ce2e7b2443922e7f71fa31338
- Source reviews: 22e7922f72bdf907c6b7451763727f425836c54a0884899f86bc330172e30bdd
- Paired artifact: 3534834fc72f7d2f2cf4c4169241f6cc46281c9ec47a8909e8ca8f05392f3b41

Hashes bind local bytes/metadata; they are not hashes of archived publisher page contents.

## Remaining boundaries

1. **Exact CHIMIE L'HOMME identity:** the accepted brief/formula was not recovered from accessible sources. Give the accepted brief or latest formula to bind this named campaign; no photographs, purchase receipts or exhaustive stock questionnaire are needed for that.
2. **Composition integration:** the controlled test found no stock, role or dose changes. A future compiler bridge must translate explicit target constraints into candidate architectures, preserve control alternatives and be evaluated separately; more citations alone are not better formulation.
3. **Narrow evidence gaps:** natural ambergris tinctures, medicinal oud, literal tar grades, chalk, detailed polycyclic-musk odor, the lemon side of lemon/lime and exact historical recipes remain partial or unavailable.
4. **Empirical outcomes:** no measured projection, stability, skin performance, personal liking or market superiority has been established by this work.

The coverage file deliberately keeps `full_research_program_complete=false`. The completed boundary is the planned **advisory pass and its software contracts**, not unlimited research or a universally correct perfume program.

## Added source-review register

Titles below describe the reviewed scope. Follow each source's local claim and review record for its exact limitation. No standards text, full paper or proprietary formula has been copied.

| Source record | Primary/official location | Review scope |
|---|---|---|
| `indesso_cananga_finish` | [Indesso: Cananga Oil product identity](https://www.indesso.com/en/our-catalog/cananga-oil) | selected primary sections |
| `cananga_ylang_identity_finish` | [Wijekoon et al. (2025): cananga and ylang preparation identity, conference abstract](https://academic.oup.com/bjd/article/193/Supplement_1/ljaf085.276/8162132) | primary abstract |
| `tiare_concrete_finish` | [Gardenia taitensis concrete: composition study (1992)](https://www.tandfonline.com/doi/full/10.1080/10412905.1992.9698082) | primary abstract |
| `frangipani_benzenoids_finish` | [Plumeria rubra floral benzenoid biosynthesis (2019)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6501094/) | selected primary sections |
| `ylang_methods_finish` | [Brokl et al. (2013): review of ylang fraction sampling](https://www.mdpi.com/1420-3049/18/2/1783) | selected primary sections |
| `peony_methods_finish` | [Peony cultivar study (2023): analytical and threshold methods review](https://www.mdpi.com/1422-0067/24/11/9410) | selected primary sections |
| `freesia_methods_finish` | [Freesia cultivar study (2021): sampling methods review](https://www.mdpi.com/1420-3049/26/15/4482) | selected primary sections |
| `lilac_isomers_finish` | [Lilac aldehyde/alcohol stereoisomers in floral scent (2006)](https://www.sciencedirect.com/science/article/pii/S0021967306003554) | primary abstract |
| `honeysuckle_anthesis_finish` | [Lonicera japonica floral emission across anthesis (2023)](https://www.jse.ac.cn/EN/10.1111/jse.12916) | primary abstract |
| `sweet_pea_methods_finish` | [Lathyrus odoratus floral volatile study (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11644040/) | selected primary sections |
| `champaca_flowers_finish` | [Magnolia champaca flower volatile biosynthesis (2017)](https://link.springer.com/article/10.1186/s12864-017-3846-8) | selected primary sections |
| `alba_drying_finish` | [Magnolia alba fresh and dried flower volatile study (2026)](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2026.1780030/full) | selected primary sections |
| `symrise_perfumers_finish` | [Symrise Perfumers' Compendium: selected qualitative product entries](https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/Perfumers_Compendium/index.html) | selected primary sections |
| `symrise_flavor_finish` | [Symrise Flavor Ingredients Compendium: selected identities and flavor uses](https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/Flavor_Ingredients_Compendium/index.html) | selected primary sections |
| `mango_cultivars_finish` | [Major aroma-active compounds in five mango cultivars (2014)](https://portal.fis.tum.de/en/publications/characterization-of-the-major-aroma-active-compounds-in-mango-man/) | primary abstract |
| `passionfruit_products_finish` | [Yellow passion-fruit juice and aqueous essence aroma (2002)](https://pubmed.ncbi.nlm.nih.gov/11879031/) | primary abstract |
| `vanilla_products_finish` | [Vanilla species and origin aroma comparison (2024)](https://pubs.acs.org/doi/10.1021/acs.jafc.4c04775) | primary abstract |
| `coffee_roasting_finish` | [Ayseli et al.: medium and dark Turkish coffee aroma (2021)](https://www.sciencedirect.com/science/article/pii/S0308814620316836) | primary abstract |
| `chocolate_recombination_finish` | [Dark chocolate aroma recombination study (2019)](https://pubmed.ncbi.nlm.nih.gov/31066267/) | primary abstract |
| `maple_model_finish` | [Maple syrup aroma model study (1991)](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1745-459X.1991.tb00506.x) | primary abstract |
| `rum_sensomics_finish` | [Two commercial rums: sensomics comparison (2016)](https://pubs.acs.org/doi/10.1021/acs.jafc.5b05426) | primary abstract |
| `cognac_terpenes_finish` | [Aged Cognac terpenoids in multicomponent mixtures (2020)](https://pubs.acs.org/doi/10.1021/acs.jafc.9b06656) | primary abstract |
| `bourbon_recombination_finish` | [American bourbon: recombination and omission (2008)](https://pubs.acs.org/doi/abs/10.1021/jf800383v) | primary abstract |
| `smoked_tea_finish` | [Smoked black tea processing and aroma (2024)](https://www.sciencedirect.com/science/article/pii/S2590157524010307) | primary abstract |
| `cedar_virginia_finish` | [Firmenich Cedarwood Virginia EO 922044 marketing sheet](https://www.firmenich.com/sites/default/files/uploads/files/ingredients/marketing-sheet/perfumery/CEDARWOOD_VIRGINIA_EO_922044.pdf) | selected primary sections |
| `fir_balsam_finish` | [Robertet Fir Balsam Resinoid 99050023](https://matieres-premieres.robertet.com/fir-balsam-resinoid) | selected primary sections |
| `guaiac_finish` | [Robertet Gaiacwood Dehydrated Oil 00020994](https://matieres-premieres.robertet.com/gaiacwood-dehydrated-oil) | selected primary sections |
| `vetiver_heart_finish` | [IFF LMR Vetiver Heart 221163](https://www.iff.com/scent/lmr-compendium/vetiver-heart/) | selected primary sections |
| `agarwood_reco_finish` | [Robertet Agarwood Reco 99253846](https://matieres-premieres.robertet.com/agarwood-reco) | selected primary sections |
| `styrax_finish` | [IFF Styrax Resinoid Low Styrene 191857](https://www.iff.com/scent/lmr-compendium/styrax-resinoid-low-styrene/) | selected primary sections |
| `opoponax_finish` | [Biolandes Opoponax F1828](https://biolandes.com/en/product/opoponax/) | selected primary sections |
| `peru_tolu_identity_finish` | [EMA draft assessment: Peru and Tolu botanical identity](https://www.ema.europa.eu/en/documents/herbal-report/draft-assessment-report-myroxylon-balsamum-l-harms-var-pereirae-royle-harms-balsamum_en.pdf) | selected primary sections |
| `myrrh_finish` | [IFF LMR Myrrh Oil Organic 135639](https://www.iff.com/scent/lmr-compendium/myrrh-oil-org/) | selected primary sections |
| `elemi_finish` | [IFF LMR Elemi Oil 50620](https://www.iff.com/scent/lmr-compendium/elemi-oil/) | selected primary sections |
| `tobacco_finish` | [Biolandes Tobacco Absolute F2951 technical sheet](https://biolandes.com/wp-content/uploads/fiche-technique-F2951.pdf) | selected primary sections |
| `beeswax_finish` | [IFF LMR Beeswax Absolute 23712](https://www.iff.com/scent/lmr-compendium/beeswax-abs/) | selected primary sections |
| `herb_chemotypes_finish` | [Truzzi et al. (2022): selected herb essential-oil chemotypes](https://pmc.ncbi.nlm.nih.gov/articles/PMC9458032/) | selected primary sections |
| `basil_cultivars_finish` | [Basil cultivars: volatile composition and variation (2017)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6152153/) | selected primary sections |
| `anise_tarragon_finish` | [Anise and tarragon aroma-active compounds (2007)](https://onlinelibrary.wiley.com/doi/10.1002/ffj.1765) | primary abstract |
| `ambergris_jetsam_finish` | [Jetsam ambergris volatile composition (2019)](https://pubmed.ncbi.nlm.nih.gov/31084225/) | primary abstract |
| `ambroxide_grades_finish` | [Ambroxide preparations and receptor response study (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12102163/) | selected primary sections |
| `musk_classes_finish` | [Experimental study with different chemical classes of musk (2016)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6601836/) | selected primary sections |
| `key_lime_finish` | [Extracted and distilled key lime oils (2003)](https://onlinelibrary.wiley.com/doi/abs/10.1002/ffj.1172) | primary abstract |
| `cedrat_finish` | [Elixens organic cedrat peel oil CED00001](https://www.elixens.com/fiche-produit/huile-essentielle-cedrat-bio-ced00001) | selected primary sections |
| `zeon_green_finish` | [Zeon green fragrance materials: product table](https://www.zeon.co.jp/en/business/enterprise/fragrance/green/) | selected primary sections |
| `fir_needle_finish` | [Berje Fir Needle Oil Siberian](https://berjeinc.com/products/fir-needle-oil-siberian/) | selected primary sections |
| `spice_identities_finish` | [Spice essential oils study (2022): material-identity section](https://pmc.ncbi.nlm.nih.gov/articles/PMC9609062/) | selected primary sections |
| `saffron_finish` | [Italian saffron sensory characterization (2021)](https://www.mdpi.com/2304-8158/10/11/2604) | selected primary sections |
| `pcw_melolal_finish` | [PCW Melolal product page](https://directpcw.com/products/mel-1) | selected primary sections |
| `mfk_solar_finish` | [Maison Francis Kurkdjian: solar-note vocabulary](https://www.franciskurkdjian.com/eu-en/surrender-to-sunny-notes/PDFN01.html) | selected primary sections |
| `civettone_finish` | [dsm-firmenich Civettone PE 926851](https://studio.dsm-firmenich.com/product/civettone-pe-926851) | selected primary sections |
| `castoreum_finish` | [Tang et al. (1995): neutral compounds of castoreum](https://link.springer.com/article/10.1007/BF02033674) | primary abstract |
| `axillary_finish` | [Natsch et al. (2004): human axillary odor compounds](https://onlinelibrary.wiley.com/doi/abs/10.1002/cbdv.200490079) | primary abstract |
| `decanal_finish` | [Kao Aldehyde C-10 / decanal](https://chemical.kao.com/global/fragrances-and-aromas/products/aldehyde_c-10/) | selected primary sections |
| `dodecanal_finish` | [Kao Aldehyde C-12 Lauryl / n-dodecanal](https://www.kaochemicals-eu.com/our-products/aldehyde-c-12-lauryl-n-dodecanal) | selected primary sections |
| `historic_paper_finish` | [Bembibre and Strlic (2017): heritage smell framework](https://discovery.ucl.ac.uk/id/eprint/1554653/) | primary abstract |
| `unido_attar_finish` | [UNIDO historical report on Indian essential oils and attar production (1986)](https://downloads.unido.org/ot/48/13/4813119/15001-20000_16030.pdf) | selected primary sections |
| `ima_history_finish` | [Institut du Monde Arabe: Parfums d'Orient exhibition](https://www.imarabe.org/fr/agenda/expositions-musee/parfums-orient) | selected primary sections |

## Newly covered card register

All entries retain UNTESTED_SUBTYPE_HYPOTHESIS and false action authority.

| Package | Scope | Card |
|---|---|---|
| FL_TROPICAL | cananga | `TROP_CANANGA` |
| FL_LIGHT | lilac | `LIGHT_LILAC` |
| FL_LIGHT | honeysuckle | `LIGHT_HONEYSUCKLE` |
| FL_LIGHT | sweet pea | `LIGHT_SWEET_PEA` |
| FL_TROPICAL | champaca | `TROP_CHAMPACA` |
| FL_TROPICAL | white michelia alba | `TROP_ALBA` |
| AR_LAVENDER | coffee milk | `LAV_COFFEE_MILK` |
| FR_BERRY | rhubarb | `BERRY_RHUBARB` |
| FR_BERRY | grape | `BERRY_GRAPE` |
| FR_BERRY | berry floral | `BERRY_FLORAL_BRIDGE` |
| FR_TROPICAL | mango | `TROP_MANGO` |
| FR_TROPICAL | passionfruit | `TROP_PASSIONFRUIT` |
| FR_TROPICAL | melon | `TROP_MELON` |
| FR_TROPICAL | banana | `TROP_BANANA` |
| FR_STONE | peach skin | `STONE_PEACH_SKIN` |
| FR_STONE | plum | `STONE_PLUM` |
| FR_STONE | cherry | `STONE_CHERRY` |
| GO_VANILLA | vanilla botanical products | `VAN_BOTANICAL` |
| GO_VANILLA | caramel toasted | `VAN_CARAMEL_TOAST` |
| GO_VANILLA | sweet floral gourmand | `VAN_FLORAL_GOURMAND` |
| GO_ROAST | brewed coffee | `ROAST_COFFEE` |
| GO_ROAST | cacao chocolate | `ROAST_CACAO` |
| GO_ROAST | almond | `ROAST_ALMOND` |
| GO_ROAST | hazelnut | `ROAST_HAZELNUT` |
| GO_DAIRY | honey | `DAIRY_HONEY` |
| GO_DAIRY | maple | `DAIRY_MAPLE` |
| BO_BOOZY | rum cognac | `BO_RUM_COGNAC` |
| BO_BOOZY | whisky | `BO_WHISKY` |
| TE_TEA | smoky tea | `TEA_SMOKED` |
| WO_CEDAR | cedar pencil | `CEDAR_PENCIL` |
| WO_CEDAR | conifer resin | `CEDAR_CONIFER_RESIN` |
| WO_CEDAR | guaiac smoke | `CEDAR_GUAIAC` |
| WO_SANDAL | dry transparent | `SANDAL_DRY` |
| WO_VETIVER | smoky dry | `VETIVER_SMOKY` |
| WO_VETIVER | fractionated clean | `VETIVER_HEART` |
| WO_OUD | medicinal animalic | `OUD_ANIMALIC` |
| WO_OUD | rose amber | `OUD_ROSE_AMBER` |
| WO_OUD | spiced | `OUD_SPICED` |
| AM_RESIN | styrax | `RESIN_STYRAX` |
| AM_RESIN | opoponax | `RESIN_OPOPONAX` |
| AM_RESIN | tolu peru balsam | `RESIN_TOLU_PERU` |
| AM_RESIN | animalic resinous | `RESIN_ANIMALIC` |
| LE_LEATHER | smoky tar | `LEATHER_SMOKY` |
| LE_LEATHER | bitter green | `LEATHER_GREEN` |
| LE_LEATHER | floral leather | `LEATHER_FLORAL` |
| RE_INCENSE | myrrh opoponax | `INCENSE_MYRRH` |
| RE_INCENSE | elemi | `INCENSE_ELEMI` |
| RE_INCENSE | church smoke | `INCENSE_CHURCH` |
| TO_HAY | dry leaf | `TOBACCO_DRY` |
| TO_HAY | sweet pipe | `TOBACCO_PIPE` |
| TO_HAY | smoky tobacco | `TOBACCO_SMOKY` |
| TO_HAY | beeswax | `TOBACCO_BEESWAX` |
| AR_FOUGERE | tonka sweet | `FOUGERE_TONKA` |
| AR_HERBS | rosemary | `HERB_ROSEMARY` |
| AR_HERBS | basil thyme | `HERB_BASIL_THYME` |
| AR_HERBS | mint | `HERB_MINT` |
| AR_HERBS | anise tarragon | `HERB_ANISE_TARRAGON` |
| AM_SOFT | coumarinic | `SOFT_COUMARIN` |
| AM_SOFT | soft vanillic | `SOFT_VANILLA` |
| AM_FLORAL | white floral amber | `FLORAL_AMBER_WHITE` |
| AM_FLORAL | balsamic amber | `FLORAL_AMBER_BALSAM` |
| AM_AMBERGRIS | natural tincture | `AMBERGRIS_TINCTURE` |
| AM_AMBERGRIS | ambroxide stereochemistry | `AMBERGRIS_STEREO` |
| AM_WOODS | sandal cedar associated | `WOOD_SANDAL_CEDAR` |
| MU_MUSK | alicyclic | `MUSK_ALICYCLIC` |
| MU_MUSK | polycyclic | `MUSK_POLYCYCLIC` |
| MU_MUSK | powdery | `MUSK_POWDER` |
| CI_PRODUCTS | lemon lime | `CIT_LEMON_LIME` |
| CI_PRODUCTS | citron cedrat | `CIT_CEDRAT` |
| CI_CHASSIS | neroli petitgrain | `COLOGNE_NEROLI` |
| CI_CHASSIS | fresh woody | `COLOGNE_WOOD` |
| GR_GREEN | cut grass | `GREEN_GRASS` |
| GR_GREEN | conifer green | `GREEN_CONIFER` |
| SP_SPICE | pepper | `SPICE_PEPPER` |
| SP_SPICE | ginger | `SPICE_GINGER` |
| SP_SPICE | cinnamon clove | `SPICE_CINNAMON_CLOVE` |
| SP_SPICE | saffron | `SPICE_SAFFRON` |
| WA_AQUATIC | melon watery | `AQUA_MELON` |
| WA_AQUATIC | airy mineral | `AQUA_AIRY_MINERAL` |
| WA_AQUATIC | solar salicylate | `AQUA_SOLAR` |
| WA_AQUATIC | dry mineral | `AQUA_DRY_MINERAL` |
| AN_SKIN | civet castoreum identities | `SKIN_CIVET_CASTOR` |
| AN_SKIN | salty sweaty | `SKIN_SWEAT` |
| AB_ABSTRACT | waxy aldehydic | `AB_WAXY` |
| AB_ABSTRACT | citrus aldehydic | `AB_CITRUS` |
| AB_ABSTRACT | paper chalk | `AB_PAPER_CHALK` |
| AB_ABSTRACT | conceptual atmosphere | `AB_ATMOSPHERE` |
| CU_TRADITIONS | exact attar traditions | `CU_ATTAR` |
| CU_TRADITIONS | regional floral oils | `CU_FLORAL_OILS` |
| CU_TRADITIONS | rose oud traditions | `CU_ROSE_OUD` |
| CU_TRADITIONS | historical materials | `CU_HISTORICAL` |
| HY_HYBRIDS | tea musk | `HY_TEA_MUSK` |
| HY_HYBRIDS | incense floral | `HY_INCENSE_FLORAL` |
| HY_HYBRIDS | rose mineral | `HY_ROSE_MINERAL` |

