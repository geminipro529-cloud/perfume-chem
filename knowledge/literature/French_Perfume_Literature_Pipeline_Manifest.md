# French Perfume Literature for Pipeline Ingestion

Purpose: identify French-language or French-institution perfume literature that can be encoded into the existing pipeline without inventing new ingestion surfaces.

Current repo targets:

- `knowledge/**/*.md`
  - searchable by `engine.knowledge.embeddings.KnowledgeIndex`
- `data/knowledge_graph/theory_rules.json`
  - doctrine, method, aesthetic frameworks
- `data/knowledge_graph/accords.json`
  - families, benchmark perfumes, accord archetypes
- `data/knowledge_graph/pairing_rules.json`
  - positive/negative material pairings
- `data/knowledge_graph/synergy_matrix.json`
  - ratio-sensitive synergy or antagonism claims
- `data/knowledge_graph/material_properties.json`
  - descriptor fields such as odor profile, role, best-with, avoid, historical craft notes

Important boundary:

- This is not "all books ever published in France about perfume."
- It is the subset with real extraction yield for the current pipeline.
- Public-domain and open-access items are highest priority because they can be OCRed or manually abstracted now.

## Tier A — Ready for direct ingestion now

### 1. Simon Barbe — *Le parfumeur françois qui enseigne toutes les manières de tirer les odeurs des fleurs...* (1693/1698)

- Link: https://openlibrary.org/books/OL26230929M
- BnF trail: https://catalogue.bnf.fr/rechercher.do?index=TOUS3&motRecherche=Le+parfumeur+fran%C3%A7ois+Barbe
- Best pipeline target:
  - `accords.json`
  - `pairing_rules.json`
  - `knowledge/art/classic_accords.md`
- Extraction yield:
  - historical formula patterns
  - flower extraction methods
  - pommades, powders, scented tobacco, orange-flower, violet, jasmine, neroli style compositions
- Why it matters:
  - earliest major French practical perfume manual
  - strong source for benchmark accord lineage rather than modern safety or ODT data

### 2. Simon Barbe — *Le parfumeur royal, ou, l'art de parfumer avec les fleurs...*

- Link: https://search.worldcat.org/title/Le-parfumeur-royal-ou-L%27art-de-parfumer-avec-les-fleurs-and-composer-toutes-sortes-de-parfums-tant-pour-l%27odeur-que-pour-le-gout-.../oclc/17332812
- Supplemental view: https://books.google.com/books/about/Le_parfumeur_royal.html?id=0kQFAQAAIAAJ
- Best pipeline target:
  - `accords.json`
  - `pairing_rules.json`
- Extraction yield:
  - trade-oriented recipes
  - historical ingredient combinations
  - base-perfume construction habits from the French guild era

### 3. Pradal, Malepeyre, A.-M. Villon — *Nouveau manuel complet du parfumeur* (19th c.)

- Link: https://gallica.bnf.fr/ark:/12148/bpt6k9376761
- Best pipeline target:
  - `knowledge/practical/measurement_guide.md`
  - `accords.json`
  - `pairing_rules.json`
- Extraction yield:
  - nomenclature of essences
  - composition of perfumes, extracts, eaux, vinegars, powders
  - preparation protocols and practical shop formulas
- Why it matters:
  - broad manual with enough concrete recipe content to justify manual abstraction

### 4. Marius-Paul Otto — *L'industrie des parfums d'après les théories de la chimie moderne: notations et formules, les parfums naturels, les parfums artificiels*

- BnF trail: https://catalogue.bnf.fr/rechercher.do?critereRecherche=0&motRecherche=Marius-P.+Otto+%281870-1939%29
- Best pipeline target:
  - `knowledge/science/*.md`
  - `theory_rules.json`
  - `material_properties.json` craft notes
- Extraction yield:
  - chemistry-grounded formulation logic
  - notation systems
  - natural vs synthetic material treatment
- Why it matters:
  - unusually close to the repo's chemistry-plus-perfumery framing

### 5. Eugène Charabot — *Les parfums artificiels* (1900)

- BnF author trail: https://catalogue.bnf.fr/rechercher.do?index=AUT3&numNotice=13077602
- Google Books / Play entry: https://play.google.com/store/books/details/Eug%C3%A8ne_Charabot_Les_parfums_artificiels?id=IhbrAAAAMAAJ
- Best pipeline target:
  - `material_properties.json`
  - `knowledge/science/advanced_blending_theory.md`
  - `pairing_rules.json`
- Extraction yield:
  - synthetic raw material descriptions
  - functional uses of classic aroma chemicals
  - historical synthetic-vs-natural substitution logic

### 6. R.-M. Gattefossé — *Formulaire de savonnerie et de parfumerie* (1923)

- Link: https://openlibrary.org/works/OL43001159W/Formulaire_de_savonnerie_et_de_parfumerie
- Best pipeline target:
  - `accords.json`
  - `knowledge/practical/measurement_guide.md`
  - `pairing_rules.json`
- Extraction yield:
  - compounding recipes
  - dosage conventions
  - soap and perfume overlap where odor materials recur

### 7. R.-M. Gattefossé — *Formulaire de parfumerie et de cosmétologie*

- Google Books entry: https://books.google.com/books/about/Formulaire_de_parfumerie_et_de_cosm%C3%A9tol.html?id=2IQHAi6ZMpoC
- BnF author trail: https://catalogue.bnf.fr/rechercher.do?index=AUT3&numNotice=11266644
- Best pipeline target:
  - `material_properties.json`
  - `pairing_rules.json`
  - `knowledge/practical/*.md`
- Extraction yield:
  - named material usages
  - classic preparation and dilution patterns
  - compatibility clues across floral, citrus, balsamic, musky constructions

### 8. René Cerbelaud — *Formulaire de parfumerie*

- Link: https://books.google.com/books/about/Formulaire_de_parfumerie.html?id=PyR63NrFu10C
- Best pipeline target:
  - `pairing_rules.json`
  - `synergy_matrix.json`
  - `material_properties.json`
- Extraction yield:
  - incompatibilités olfactives
  - formula families
  - usage examples for ionones, heliotropin, hydroxycitronellal, musks, salicylates, citrus materials
- Why it matters:
  - especially valuable for negative rules and "avoid" fields

### 9. Charles Régismanset — *Philosophie des parfums* (1907)

- Link: https://www.hachettebnf.fr/livre/philosophie-des-parfums-9782329300306/
- BnF author trail: https://catalogue.bnf.fr/ark:/12148/cb12127130x/PUBLIC
- Best pipeline target:
  - `theory_rules.json`
  - `knowledge/art/emotional_mapping.md`
  - `knowledge/art/olfactory_perception.md`
- Extraction yield:
  - philosophical and affective language around odor
  - emotional classification
  - aesthetic framing not reducible to chemistry
- Why it matters:
  - useful for hedonic and narrative layers, not for quantitative physics

### 10. Gallica professional perfume press set

- Link: https://gallica.bnf.fr/selections/fr/html/presse-professionnelle-coiffure-parfumerie
- Includes:
  - `Journal de la parfumerie`
  - `Moniteur de la parfumerie`
  - `La Parfumerie moderne`
  - `Revue des marques de la parfumerie et de la savonnerie`
- Best pipeline target:
  - `knowledge/literature/`
  - `pairing_rules.json`
  - `material_properties.json`
  - `trusted historical citations inside research docs`
- Extraction yield:
  - period technical notes
  - commercial material descriptions
  - formula trends by era

## Tier B — High-value French doctrine, manual extraction required

### 11. Edmond Roudnitska — *L'Esthétique en question: introduction à une esthétique de l'odorat* (1977)

- Link: https://search.worldcat.org/title/L%27Esthetique-en-question-%3A-introduction-a-une-esthetique-de-l%27odorat/oclc/4518508
- Best pipeline target:
  - `theory_rules.json`
  - `material_properties.json` via `roudnitska_function` and craft-note fields
  - `engine/formula_recommendations.py` provenance comments
- Extraction yield:
  - transparence / chaleur / noblesse / peau / profondeur style role logic
  - composition aesthetics
  - anti-heaviness and material-role reasoning
- Status:
  - bibliographic source confirmed
  - full text not confirmed as open-access in this pass

### 12. *Sous le signe du parfum: Edmond Roudnitska, compositeur-parfumeur* (1991)

- Link: https://catalogue.bnf.fr/ark:/12148/cb35502818p
- Best pipeline target:
  - `knowledge/literature/`
  - `accords.json`
  - `perfumer_signature` notes
- Extraction yield:
  - contextual material choices
  - benchmark perfume references
  - secondary interpretation of Roudnitska's compositional practice

### 13. Jean-Claude Ellena — *Le parfum*

- Link: https://catalogue.bnf.fr/ark:/12148/cb473780110
- Best pipeline target:
  - `theory_rules.json`
  - `accords.json`
  - `knowledge/art/composition_techniques.md`
- Extraction yield:
  - stripped-down structure logic
  - transparency and minimalism
  - perfumer-facing explanation of how fragrance is composed

### 14. Jean-Claude Ellena — *Journal d'un parfumeur ; suivi d'un Abrégé d'odeurs*

- Link: https://catalogue.bnf.fr/ark:/12148/cb42407820z
- Best pipeline target:
  - `knowledge/literature/`
  - `material_properties.json` craft notes
  - `perfumer_signature` rules
- Extraction yield:
  - practical creative heuristics
  - odor-language snippets
  - benchmark references from a major French perfumer

### 15. Jean-Claude Ellena — *L'Écrivain d'odeurs*

- Collection listing: https://www.nez-editions.us/collections/books-in-french
- Best pipeline target:
  - `knowledge/literature/`
  - `perfumer_signature`
- Extraction yield:
  - writing-based odor description patterns
  - lexicon enrichment for analysis surfaces

### 16. Dominique Ropion — *Aphorismes d'un parfumeur*

- Link: https://www.nez-editions.us/products/nez-litterature-aphorismes-dun-parfumeur-dominique-ropion?variant=30892687491126
- Best pipeline target:
  - `pairing_rules.json`
  - `perfumer_signature`
  - `knowledge/art/composition_techniques.md`
- Extraction yield:
  - dosage sensibility
  - floral architecture
  - modern French high-precision composition logic

### 17. Mathilde Laurent — *Sentir le sens*

- Collection listing: https://www.nez-editions.us/collections/nez-litterature-fr
- Best pipeline target:
  - `knowledge/art/emotional_mapping.md`
  - `knowledge/literature/`
- Extraction yield:
  - interpretive smell language
  - conceptual odor-to-meaning links

## Tier C — French raw-material and benchmark sources with immediate operational value

### 18. Société Française des Parfumeurs — *Guide des matières premières pour la parfumerie*

- Link: https://guidesfp.fr/
- SFP announcement: https://www.parfumeurs-createurs.org/fr/article/le-guide-des-matieres-premieres-26
- Best pipeline target:
  - `material_properties.json`
  - `ingredient_catalog.json`
  - `engine/trusted_sources.yaml`
- Extraction yield:
  - commercial names
  - CAS lookups
  - origin
  - olfactive-note metadata
  - supplier normalization
- Why it matters:
  - this is the cleanest modern French industry data source for material indexing

### 19. Nez + LMR / Nez material monographs

- Collection listing: https://www.nez-editions.us/collections/books-in-french
- Examples:
  - patchouli: https://www.nez-editions.us/products/nez-lmr-cahiers-des-naturels-le-patchouli-en-parfumerie
  - sandalwood: https://www.nez-editions.us/products/nez-lmr-the-naturals-notebook-sandalwood-in-perfumery
  - vetiver: https://www.nez-editions.us/products/nez-lmr-the-naturals-notebook-vetiver
- Best pipeline target:
  - `material_properties.json`
  - `ingredient_catalog.json`
  - `pairing_rules.json`
- Extraction yield:
  - raw-material odor descriptions
  - origin variation
  - classic perfume appearances
  - best-with / contrast-with patterns

### 20. Osmothèque sources

- Jean Carles method page: https://www.osmotheque.fr/calendrier/conference-thematique-jean-carles-lhomme-sa-vie-et-sa-methode/
- Collection PDF: https://www.osmotheque.fr/wp-content/uploads/2016/04/Collection-Osmotheque-Juin-2015.pdf
- Best pipeline target:
  - `accords.json`
  - benchmark perfume databases
  - `perfumer_signature` and family reference docs
- Extraction yield:
  - benchmark perfume names, families, perfumers, years
  - French heritage canon for release-gate reference sets

### 21. Jean-Claude Ellena / Nez / MIP history titles

- *Cologne: la fabuleuse histoire de l'eau de Cologne*: https://catalogue.bnf.fr/ark:/12148/cb45743264q
- *Le grand livre du parfum*: https://catalogue.bnf.fr/ark:/12148/cb456053456
- Best pipeline target:
  - `accords.json`
  - `docs/fragrance_families_reference.md`
  - benchmark cologne / fresh family historical notes
- Extraction yield:
  - family history
  - benchmark perfume sets
  - canonical examples by era

## Best ingestion mapping by source type

### Best for `theory_rules.json`

- Régismanset
- Roudnitska
- Ellena
- Jean Carles secondary French sources from Osmothèque

### Best for `accords.json`

- Simon Barbe
- Gattefossé
- Cerbelaud
- Cologne / Ellena
- Osmothèque benchmark collections

### Best for `pairing_rules.json` and `synergy_matrix.json`

- Cerbelaud
- Charabot
- Gattefossé
- Nez raw-material notebooks
- professional press from Gallica

### Best for `material_properties.json`

- SFP raw-material guide
- Nez raw-material notebooks
- Charabot
- Otto
- Cerbelaud

## Priority order for actual ingestion work

1. SFP raw-material guide
2. Nez raw-material monographs
3. Cerbelaud
4. Gattefossé
5. Charabot
6. Otto
7. Simon Barbe
8. Roudnitska
9. Ellena
10. Gallica perfume press

Rationale:

- 1-6 give the highest yield for material metadata, pairings, and practical formula heuristics.
- 7 gives strong historical accord/family structure.
- 8-9 give aesthetic doctrine and perfumer logic.
- 10 is broad but labor-intensive and better mined selectively.

## Caveats

- Public-domain does not mean quantitatively trustworthy for modern safety, IFRA, or ODT values.
- Historical manuals are best for accords, roles, combinations, and craft practice, not for ppm/ODT/OAV calibration.
- Modern French perfumer memoirs are extremely valuable for `perfumer_logic`, but they usually need manual extraction because full text is not openly exposed.
- The current repo can ingest this manifest immediately because it lives under `knowledge/`, but semantic search only sees it after a knowledge-index rebuild.

## Minimal next step

If the goal is to operationalize this list rather than just catalog it:

1. Start with SFP + Nez material monographs for `material_properties.json`.
2. Mine Cerbelaud + Gattefossé for `pairing_rules.json` and `accords.json`.
3. Mine Roudnitska + Ellena for `theory_rules.json` and `perfumer_logic` provenance.
