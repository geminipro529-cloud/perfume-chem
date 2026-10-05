# Whole-inventory chemical congruence audit — 2026-09-07

## Verdict and scope

**The inventory data are not yet chemically congruent across the program.** The full text inventory was reparsed without losing stock rows. The audit found confirmed chemical-identity/molecular-weight errors, stock-authority contradictions, missing runtime mappings, invalid YAML types and misleading ODT provenance. No stock declaration, formula, engine module, historical diagnostic, or Git commit was changed.

This is a completed whole-row **audit**, not a declaration that every physical property has been experimentally verified. A field can be present, internally consistent, and still chemically wrong. A PubChem match does not authenticate a supplier grade or the contents of an owned bottle. No safety, sensory, stability, similarity or release authority is promoted.

Checkout: D:/chatbots/perfume-chem; branch codex/astra; HEAD e7002d4dacde0ae4c6b92db454fa4034c830e8f4. Existing broad dirty work was preserved.

Read-only Codex-native lanes covered stock parsing, identity/property checks, and ODT units/provenance. Parent independently reran important findings and checked primary sources. Local-first/context/verification skills kept the work to an audit and focused tests; no provider delegation, generator, broad release verifier, or formula pipeline ran.

## Deliverables

- [All 280 stock rows with local numerical values](../verification/INVENTORY_CHEMICAL_AUDIT_20260907_rows.md).
- [Machine-readable row matrix](../verification/INVENTORY_CHEMICAL_AUDIT_20260907_rows.json): row-preserving stock records; YAML/profile/cache/ODT comparisons; density, CAS, ownership and stock fields; model/provenance flags.
- [Full source-value snapshot, gzip/base64 JSON](../verification/INVENTORY_CHEMICAL_AUDIT_20260907_snapshot.json.gz.b64): complete matched source records, runtime lookup records and SHA-256 input manifest. Decode base64, then gzip, then JSON; this is data, not an executable script.
- [Parent reproductions, test output and CAS comparisons](../verification/INVENTORY_CHEMICAL_AUDIT_20260907_checks.json).
- [149 CAS query receipts](../verification/INVENTORY_CHEMICAL_AUDIT_20260907_pubchem_cas.json) and [107 existing-CID re-fetch receipts](../verification/INVENTORY_CHEMICAL_AUDIT_20260907_pubchem_cids.json).
- [Final integrity receipt](../verification/INVENTORY_CHEMICAL_AUDIT_20260907_integrity.json).

## What was actually checked

| Surface / check | Result |
|---|---:|
| Original inventory stock rows, including unavailable/planned rows | 280 |
| Legacy name-deduplicated view | 259 |
| Rows lost by that default deduplication | 21 |
| All material-spine YAML records inspected | 1,270 |
| Generated material-property cache records inspected | 293 |
| Current authority materialized physical-stock records | 227 |
| Current authority distinct identity strings | 204 |
| Current authority requirements | 280 |
| Text rows with a YAML alias candidate | 265 |
| Text rows with direct registry lookup | 262 |
| Text rows with a runtime ingredient profile | 236 |
| Text rows with a normalized runtime ODT entry | 259 |
| Text rows with a generated-cache candidate | 272 |
| Existing cache CIDs re-fetched from PubChem | 107 |
| Unique local CAS identifiers queried independently | 149 |
| CAS queries returning compound data | 114 |
| CAS queries returning no compound record | 35 |
| Text rows connected to at least one successful CAS candidate query | 131 |

CAS results are **candidate evidence, not 114 verified materials**. A CAS search can return an isomer family, a multicomponent entity, or an unrelated indexed synonym. Essential oils and other UVCBs need not have a pure-compound record. Failed CAS queries are recorded, not filled with guessed substitutes.

Raw text statuses: 267 owned, 4 out of stock, 1 not owned, 6 depleted, 1 owned/non-executable, 1 planned preparation. These counts describe parsing, not final execution authority. Current materialization reports 157 execution-ready stocks and 70 not ready, but the readiness contradictions below mean that flag cannot independently authorize dosing.

Across the five core scalar comparisons, **125 stock rows have at least one local disagreement or invalid value**. These are row-level review flags, not 125 independently proven wrong chemical identities. Repeated concentrations and alias-candidate/grade ambiguities can appear more than once.

| Field | Local conflicts | Invalid | No numeric value in compared surfaces |
|---|---:|---:|---:|
| Molecular weight | 26 | 0 | 15 |
| Vapor pressure | 34 | 1 | 15 |
| logP/cLogP | 112 | 0 | 15 |
| Air ODT | 12 | 0 | 13 |
| Ethanol ODT | 11 | 1 | 14 |

Scalar disagreement uses a 1% relative screening tolerance, not a scientific acceptance criterion. Different logP calculation methods, source temperatures, grades and isomers require adjudication. Full raw values are preserved even below this screening tolerance. Missing individual fields are still visible when another surface supplies a number.

Additional YAML candidate coverage is sparse: only 34 text rows have a density value, 20 a nonempty vp_source, 14 SMILES, 13 InChIKey, 2 vaporization-enthalpy values, and 2 Stevens-exponent values. There are 67 rows with a non-null CAS field, but that count includes invalid literal "None" strings and checksum problems. None of these coverage counts establishes an owned-lot measurement.

## 1. Chemical identity and molecular-weight findings

Values are g/mol unless noted. “Entity MW” is not an assertion of 100% purity for a commercial product.

| Material | Current local values | External identity evidence / finding |
|---|---|---|
| Florol | YAML/profile 154.25; cache 138.21 | CAS 63500-71-0, C10H20O2, PubChem 172.26. **Both current values are wrong for the named chemical.** The cache points to CID 93375, a different C9H14O compound. [Manufacturer](https://studio.dsm-firmenich.com/product/florolr-pe-966458), [PubChem entity](https://pubchem.ncbi.nlm.nih.gov/compound/3017432). |
| Bourgeonal | YAML/profile 176.25; cache 190.28 | CAS 18127-01-0, C13H18O, 190.28. Main profile/YAML are wrong; the cache MW agrees with this entity. [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/64832). |
| Floralozone | YAML/profile 192.26; cache 184.27 | IFF gives C13H18O and CAS 67634-15-5 / 67634-14-4. Conventional formula mass is about 190.28; IFF displays 190.1. Neither local value represents that formula. Cache CID 91375 is C11H20O2, not this aldehyde. Preserve the source's displayed mass convention separately. [IFF](https://www.iff.com/scent/ingredients-compendium/floralozone/). |
| Mayol | YAML/profile 166.3; cache 156.26 | Manufacturer identifies cis-4-isopropylcyclohexanemethanol, CAS 13828-37-0, rounded MW156. Supports about 156.26, not166.3; cis/product identity still matters. [Manufacturer](https://studio.dsm-firmenich.com/product/mayolr-pe-957230). |
| Apritone | YAML/profile178.27; cache220.35 | Manufacturer specifies C15H24O, CAS68133-79-9, MW220.35. The grade contains an isomer distribution and additive, not one perfectly pure stereoisomer. [Bedoukian specification](https://bedoukian.com/wp-content/uploads/FR-410-spec-sheet.pdf). |
| Allyl Amyl Glycolate | YAML158.2/profile158.19; cache186.25 | C10H18O3 entity MW186.25. IFF's product SDS includes two methylbutoxy isomers plus BHT, so the product cannot be fully described by one CID. [IFF-authored SDS](https://www.johndwalsh.com/wp-content/uploads/2017/12/ALLYL-AMYL-GLYCOLATE-GHS-SDS.pdf), [PubChem entity](https://pubchem.ncbi.nlm.nih.gov/compound/106729). |
| Ebanol | YAML220.4/profile220.35; cache208.34 | Givaudan identifies C14H24O, CAS67801-20-1, MW208.3. Main profile/YAML are inconsistent with the named product's formula. [Givaudan](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/ebanoltm). |
| Ethyl Safranate | YAML/profile168.23; cache194.27 | Givaudan identifies C12H18O2, rounded MW194 and three product/isomer CAS identifiers. Supports about194.27, not168.23. [Givaudan](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/ethyl-safranate). |
| Peonile | YAML/profile197.27; cache192.3 | Givaudan gives C14H15N, CAS10461-98-0, rounded MW197. **The profile entity MW is supported; the cache is not.** Do not overwrite the profile from the cache. [Givaudan](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/peoniletm). |
| Aurantiol | YAML/profile305.4; cache254.26 | C18H27NO3 / CAS89-43-0 supports the profile entity mass. The cache CID66638 is an unrelated nitrogen/sulfur compound. The manufacturer's assay is >65% Schiff base, so commercial reaction-product composition must remain distinct from the entity mass. [Manufacturer](https://www.prodasynth.com/index.php/en/producto/983/AURANTIOL). |
| Dipropylene Glycol | YAML/profile134.17; cache268.35 | Cache CID134692469 contains two disconnected C6H14O3 isomer components and reports their summed formula mass. That is not the molar mass to use for one mole of DPG molecules. DPG isomers have MW about134.17. [NIST](https://webbook.nist.gov/cgi/cbook.cgi?ID=R410156&Mask=200), [chemical supplier](https://labchem-wako.fujifilm.com/europe/product/detail/W01W0104-2898.html). |
| Vertofix / Vertofix Coeur | YAML234.4/profile234.38; cache246.4 | IFF Coeur is C17H26O, CAS32388-55-9; conventional formula mass about246.4, while manufacturer display is246.2. Identity correction is conditional on the owned “Vertofix” being this Coeur grade. [IFF](https://www.iff.com/scent/ingredients-compendium/vertofix-coeur/). |
| Damascone Beta | Cache190.3 | Its own CAS23726-91-2/CID5374527 returns C13H20O, MW192.30. This is an internal cache-versus-live-entity discrepancy; do not conflate damascone and damascenone. [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/5374527). |
| Amber Xtreme | Cache236 | Its own CAS476332-65-7 resolves to C18H32O, MW264.4. Confirm exact manufacturer product/grade before replacing the proxy; do not treat CAS lookup alone as complete product authentication. [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/92030006). |
| Verdox | YAML/profile170.25; cache198.3 | CAS88-41-5 entity is C12H22O2, MW198.30. Direct current manufacturer/owned-grade binding remains pending; the high-cis supplier sheet was not reproducibly retrieved by the parent. [PubChem entity](https://pubchem.ncbi.nlm.nih.gov/compound/62334). |

The generated cache is not uniformly better or worse. Some values are correct there and wrong in the profile; others are wrong in the cache and correct in the profile. The existing generator is not import-safe and was deliberately not run.

## 2. Vapor-pressure and physical-property evidence cannot be flattened

- **Nympheal:** local0.01Pa; Givaudan0.001hPa =0.1Pa, a tenfold displayed discrepancy. Manufacturer page does not state temperature for that field, so it is not an automatically valid replacement for vp_25c_pa. Local logP3.0/profile3.8 also differs from manufacturer3.7. [Givaudan](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/nympheal).
- **Florol:** manufacturer website0.00712Pa at20C, but manufacturer marketing PDF0.95Pa at20C, about133-fold apart. Local0.007 is labeled25C. Do not silently choose a convenient source. [Website](https://studio.dsm-firmenich.com/product/florolr-pe-966458), [manufacturer PDF](https://www.firmenich.com/sites/default/files/uploads/files/ingredients/marketing-sheet/perfumery/FLOROL_966458.pdf?908a31e=).
- **Apritone:** Bedoukian's2024 sheet displays786.5Pa at21.1C; its2023 sheet0.0009mmHg at20C, approximately0.120Pa. Both are primary sources, yet disagree by about6,550-fold. Source conflict stays unresolved. [2024](https://bedoukian.com/wp-content/uploads/FR-410-spec-sheet.pdf), [2023](https://bedoukian.com/wp-content/uploads/410-FLAVOR-Sheet-2023.pdf).
- **Ebanol:** local0.89Pa versus manufacturer0.0013hPa =0.13Pa; **Peonile:** local0.0056Pa versus manufacturer0.0004hPa =0.04Pa; **Ethyl Safranate:** local0.05Pa versus manufacturer0.0933hPa =9.33Pa. Manufacturer temperature/method must be established before declaring replacement25C values. The corresponding Givaudan sources are linked in the identity table.
- Pure-material density is not a measured density for a prepared20% or10% stock. Mass-fraction declarations cannot be converted to exact active grams from raw microlitres without defensible stock-solution density. Missing data remain missing.

## 3. Mixtures and malformed records

**Lilyreal ND:** exact supplier SKU6MG22777 is explicitly a mixture/replacement base. YAML and profile assign MW192.3, logP3.5 and VP0.01Pa without a demonstrated composition-derived basis. Parent reproduced opaque-preblend detection as false for the exact name. There is no justified single “correct molecule MW” to insert. [Supplier](https://www.perfumersworld.com/view.php?pro_id=6MG22777).

Naturals, absolutes, resinoids and commercial accords require product/composite identities. A single guessed MW may be a documented model surrogate, but must not be labeled a verified pure-compound property. Partial literature GC composition does not verify an owned lot.

Other reproduced structural defects:

- Labdanum variants have four VP values stored as strings "1e-05", not numeric values: L.yaml123,146,158,180.
- T.yaml3991 nests stock, ownership, supplier and provenance records **inside ifra_max_pct_edp**. This makes the limit a dictionary and removes the intended top-level stock fields for that tuberose record.
- B.yaml contains user_in_inventory: inventory.txt for a Birch Tar Rectified record: a truthy string, not a Boolean. Across all YAML rows there are283 literal true flags plus this malformed truthy value; neither total is the current inventory.
- Six CAS fields contain literal "None" strings instead of null: Vietnamese Benzoin tincture, Helichrysum EO, Sandalwood Base3X, Tuberlia Base, Turkish Storax tincture and Tuberose EO volume grade.
- Osmanthus Absolute volume-grade CAS92347-17-4 fails its checksum. Do not “repair” the last digit without identifying the substance.
- Labdanum Resinoid is assigned CAS8016-36-2, also used for Olibanum. The cited Labdanum supplier specifies8016-26-0. Exact owned product binding remains necessary. [Supplier](https://www.perfumersworld.com/view.php?pro_id=2UQ00264).
- Phenethyl Alcohol has user_stock_dilution: PEA at P.yaml1315. A chemical alias is not a stock fraction.
- Supplier tables contain placeholders such as specific gravity0.0000. These must not be imported as measured physical values.

## 4. Physical-stock authority contradictions

These are data synchronization problems, not requests for the user to reconfirm already supplied corrections.

- **Coumarin:** latest user correction is20% inDEP, basis unspecified. inventory.txt229 still says DPG-saturated approximately25–30%, plus powder230. Current authority instead materializes20% inDPG from source row85. The legacy parser turns the range into0.3, no carrier, and ready=true. DEP must not be treated as DPG.
- **Unavailable stocks remain marked ready:** Polysantol, Nagarmortha/Nagamortha Oil, Tonalide10% and Musk Ketone10% are depleted in current text but materialized as owned/execution-ready.
- **Hydroxycitronellol versus Hydroxycitronellal:** current text owns the former and explicitly distinguishes them. YAML marks the latter unavailable. Current authority nevertheless exposes neat/ready Hydroxycitronellal and no Hydroxycitronellol stock. This is not an alias correction.
- **Siam Benzoin:** text50%DPG; materialized stock50%ethanol through a source descriptor that combines Siam and Vietnamese benzoin/tincture wording.
- **Evernyl:** text records crystals plus20%w/wDPG; current authority retains nominal20% unspecified-basisDPG without the distinct crystals.
- **Correctly materialized latest corrections:** Neroli neat only; Bacdanol neat; Benzyl Salicylate neat; Guaiacwood exactly1/3w/w with ethanol+DEP and equal thirds by mass. Guaiacwood nevertheless has **no material-spine YAML record**.

The default legacy parser keys by canonical material name and picks the highest dilution, regardless of available status. It selects the unavailable neat Black Agarwood row instead of owned10%w/wDPG. It also collapses real grades and concentrations. Use lossless raw rows and stable stock IDs for execution; chemical identity alone cannot identify a physical stock.

Thirteen mappings expected by the focused identity test currently fail direct registry lookup, including Hexyl Acetate1%, Helional10%v/v, PADMA, Cinnamyl alcohol50%DPG, PCME, Cypress EO, Cabreuva EO, Anisaldehyde10%, Ethyl Maltol1%, two historical tincture labels, AldehydeC-18 and Caraway Seed Oil. The complete row matrix also distinguishes missing candidates from missing direct lookups.

Latest inventory hash binding succeeds. Raw-byte SHA256 is d103b79508592f74bb368f27507874b9fd3493acc9e872150e768449b2a02ef7; normalized-text SHA256 is214b2ef6bc84a04ae2e3318088a8d5d0f559bdee3dcd7afcc95ff272ff480243. CRLF normalization explains the difference; this is not a hash-drift finding.

## 5. ODT, OAV and hedonic authority

Parent reproduced:

- Runtime ODT_DATA339 entries, verification300.
- No duplicate literal dictionary keys in odor_thresholds.py or name_utils.py.
- No normalized numeric ODT collision. Verification metadata separately has five normalized collision groups.
- Nine zero threshold fields across six blend identities. Zero placeholders are not measured zero thresholds.
- flag_unverified and oav_reliability both raise KeyError('vfy') for Geranium EO.
- Verification fallback matches the first eight characters and can borrow metadata across distinct identities, including tuberose absolute versus volume-grade EO and Tonka Bean Absolute versus FO.
- _lookup_odt labels BHT and Ginger EO as literature despite missing verification records.
- Linalool runtime1.5ppb retains source metadata describing0.51ppb. Numeric patches and source claims are not consistently synchronized.
- The principal formula_state and composite consumers correctly convert air ppb to ppm before OAV division. **AGENTS.md402 is wrong by1000:** its printed numerator is ppm while denominator is ppb. Correct OAV = vapor_ppm/(ODT_air_ppb/1000).

OAV is a conditional model output, not percent perceived contribution, a universal perceptibility guarantee, or proof of a full muguet heart. Constituent composite OAV is a sum of constituent ratios and need not equal bulk vapor divided by one displayed surrogate threshold.

Gamma and hedonic scores also need authority labels. ingredient_intelligence.py4410 onwards fills missing gamma with1.0 and can derive hedonic scores arithmetically from descriptive character dimensions. Those are heuristics, not measured activity coefficients or human liking data. Receptor activity, thresholds, pleasantness, diffusion and stability require separate evidence rather than mutual promotion.

No all-material literature verification of every ODT, density, VP, receptor parameter, IFRA field or supplier lot was completed. The row matrix preserves these limitations instead of inventing replacement values.

## 6. Fresh verification and the next repair sequence

Focused command:

    .venv/Scripts/python.exe -B -m pytest tests/test_data_spine_loader.py tests/test_inventory_stock_model.py tests/test_inventory_material_additions.py tests/test_inventory_identity_reconciliation.py tests/test_inventory_neroli_stock_2026_09_06.py -q --tb=short -p no:cacheprovider

Result: **118 passed,5 failed,2,847 deprecation warnings;6.36seconds test time.**

Four failures assert superseded declarations: neat Black Agarwood, neat Castoreum, Alpha Irone30%, and Orris Liquid30%. The fifth is the unresolved direct alias mapping test. Tests were not changed to hide these results.

Recommended staged repair, not performed by this audit:

1. Create a supported successor stock-authority correction for already confirmed user facts, retaining every physical stock/grade and historical state. Fix contradictory depleted/owned states and no-loss parsing.
2. Add regression fixtures for confirmed chemical IDs/MW and the malformed record types. Resolve wrong cache mappings before regenerating anything. Preserve correct profile values where the cache is wrong.
3. Separate chemical-entity, commercial-grade, natural-composite and opaque-product models. Bind uncertainty/provenance to each field; remove false literature promotion and cross-identity fuzzy metadata borrowing.
4. Resolve primary-source VP/ODT conflicts; leave unavailable measurements and undisclosed product compositions explicitly unknown.
5. Run focused regressions, then relevant integration tests. Only after inputs are reconciled should a new versioned formula analysis be used to reconsider a bottle correction. Do not silently rewrite old doses or embedded diagnostic history.

**No new addition to the user's perfume is authorized by this audit.** It explains why earlier numerical balance claims require caution; it does not establish the cause of the user's sensory experience.

