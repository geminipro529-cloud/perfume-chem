# PerfumersWorld chemical intelligence — 7 October 2026

This is a public-supplier research snapshot. Exact product forms and source hashes are retained; supplier claims are not admitted as runtime, sensory, safety or release authority.

## Verified collection coverage

| Measure | Count |
|---|---:|
| official sitemap ids | 2740 |
| live listing ids | 1335 |
| accounted product ids | 2765 |
| materials with cas | 1223 |
| unique supplier cas | 640 |
| materials with description | 1688 |
| materials with specs | 1728 |
| materials with typical use | 1728 |
| document records | 2618 |
| document header matches | 2610 |
| inventory rows | 294 |
| compounding hold rows | 1 |

Scope dispositions: `{"CATEGORY_UNKNOWN_REVIEW": 11, "COMPOUND_PRODUCT_SCOPE_REVIEW": 808, "EXCLUDED_NON_MATERIAL": 92, "MATERIAL_OR_SUPPLIED_PREPARATION": 1728, "UNRESOLVED_PRODUCT": 126}`.
Product states: `{"EXACT_SKU_PAGE_PARSED": 2639, "FETCH_ERROR": 4, "HTTP_ERROR": 24, "PRODUCT_IDENTITY_UNRESOLVED": 98}`.
Latest public fetch outcomes: `{"FETCH_ERROR": 10, "HTTP_ERROR": 24, "SAVED": 5349}`.

## Use the collection

- Open `explorer.html` for offline search, filters and record inspection.
- `intelligence_v1.json` contains the complete structured product and document observations.
- `chemicals.csv` is a compact spreadsheet export; `intelligence_v1.jsonl` supports line-oriented search.
- `inventory_crosswalk.json` preserves each stock row, source line, documented SKU selection or exact-name candidates, and active compounding holds.
- `coverage_verified.json` contains availability, identity, CAS checksum and extraction accounting.
- `sources/<SKU>/*.html.gz` preserves original supplier HTML bytes; `document_texts_refined.jsonl.gz` stores the extracted available document text.
- `discovery_corrected.json` fixes the four hyphenated non-material IDs and removes two truncated pseudo-IDs; the initial discovery is retained for audit.

## Evidence boundaries

Supplier names, aliases and CAS values are candidate identity information. Natural mixtures, proprietary compounds, neat-looking labels, supplied dilutions and user-prepared stocks remain distinct. Supplier typical-use percentages do not authorize compounding. Specific gravity and temperature-related specifications retain unstated reference conditions and units when the source does not provide them. Zero values and TBA remain review states.

Odor impact, smelling-strip life, note tiers and olfactory percentages are supplier descriptions with unreviewed calibration. They are not air thresholds, OAV, perceived contribution, skin longevity or hedonic evidence. Repeated IFRA text is flagged as template-like; an available document does not prove applicability to the user's bottle or current regulation. User Orris Liquid hold remains active.

## Requested research plugins

Firecrawl supplied independent URL mapping and sample page extraction. Undermind, Amass, SciSpace and Consensus supplied literature leads; Life Sciences Literature supplied direct PubMed/PMC identity and availability records. Life Science Research supplied ChEBI linalool identity, and Wolfram independently returned its CAS. Context7 supplied official Beautiful Soup parser documentation. Plugin Management resolved capabilities. Adaptyv Bio's installed index and skill descriptions were assessed: its protein-experiment workflows have no applicable chemical-catalogue research tool; no experiment was created.

Independent literature collection is selective, centered on linalool/linalyl acetate, linalool/limonene oxidation, defined odorants and mixtures, and measurement methodology. Full-text review of all supplier chemicals was not performed. Several compact plugin outputs truncate strings even when record-level truncated=false; these remain metadata/partial excerpts.

Useful primary reference pages:

- [Linalool and oxygenated derivatives](https://pmc.ncbi.nlm.nih.gov/articles/PMC4594031/): material-specific structure/odor study; no PW grade transfer.
- [Background odors and sensitivity testing](https://pubmed.ncbi.nlm.nih.gov/29782885/): protocol-dependent threshold observations.
- [Making scents: dynamic olfactometry](https://doi.org/10.1093/chemse/bjp088): measurement-methodology reference found via Undermind.
- [ChEBI linalool](https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:17580): generic molecule identity; enantiomers and commercial grades remain distinct.

## Category census

| Supplier category | Product pages |
|---|---:|
| Category blank | 2 |
| API | 1 |
| Aroma Ingredients | 950 |
| Bottles | 6 |
| COMPOUND | 808 |
| Carrier Oils | 16 |
| Equipment | 10 |
| Essential Oils | 398 |
| Online Courses | 2 |
| Others | 2 |
| Perfume Kits | 5 |
| Pumps | 6 |
| Software | 3 |
| Specialty | 350 |
| Toiletry Bases | 14 |
| UNRESOLVED | 126 |
| Workshops | 66 |

## Catalogue quality observations

- 911 categories were recovered from explicit product-page badges absent from the input/listing field. These are literal supplier classifications.
- 7 products have differing percentage/carrier statements or multiple form statements requiring review. Neither statement is chosen as user-stock truth.
- 7 supplier CAS candidates fail checksum validation; the original text is retained.
- 159 typical-use guides contain only zero values and remain unavailable/default candidates.
- 1166 document records share an identical IFRA body with another product; these are flagged for applicability review.

Exact findings and source hashes are stored in `quality_review.json`; the explorer shows supplied-form review markers. Product categories marked COMPOUND retain a separate scope-review state because the label does not resolve preparation versus recipe identity.

## Plugin accounting

See `research/plugin_usage.json` for every requested plugin, returned artifact, capability limit and the Undermind workspace. Literature results are source leads rather than catalogue-wide scientific adjudication.

Literature accounting is stored in `research/bibliography.json`: 32 returned rows, 31 normalized title leads and 13 DOI/PMID-bound records. Eighteen title leads lack identifier binding in the search captures. One common paper appears in both SciSpace and Undermind; duplicate response envelopes are not counted again.

## Verification

Every parsed product and document was re-extracted from its captured compressed source and checked against its recorded compressed and decompressed SHA-256. Recovery performs one additional attempt for network failures and preserves both attempts. All discovered IDs reconcile to an explicit record; unresolved pages remain explicit. Raw-byte and final-artifact checksums are recorded in artifact_manifest.json. Canonical inventory, formula data, material profiles, thresholds, evidence ledgers and runtime were not modified by this task.

Collection code is disposable under `output/perfumersworld_intelligence_20261007_01a1152f/`; no pipeline script was added.

Complete data and explorer: `data/research/perfumersworld/20261007_01a1152f/intelligence_v1.json` and `explorer.html`.
