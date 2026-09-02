# Perfume-Chem Literature and Standards Verification Ledger

**Prepared:** 2026-07-29  
**Purpose:** Provide Sol 5.6 with a claim-to-source ledger for the A → D program. This is not a replacement for reading the primary sources. It records what each source supports, what it does not support, and the implementation consequence.

## Evidence labels used here

- **OFFICIAL_STANDARD**: official standards or regulatory body
- **PRIMARY**: peer-reviewed primary research
- **REVIEW**: peer-reviewed review or authoritative technical review
- **GUIDANCE**: recognized laboratory or metrology guidance
- **PREPRINT**: not treated as settled authority
- **PROJECT_SOURCE**: evidence from the user-provided project report or audit

---

## 1. Project-source evidence

### P1. First comprehensive project status report

**Source:** user-provided `Perfume-Chem Project Status Report for 5.6 Sol`  
**Classification:** PROJECT_SOURCE

Supports the historical claim that Perfume-Chem had:

- a canonical `engine.workbench.PerfumeWorkbench`;
- a SQLAlchemy laboratory schema;
- append-only bottle and inventory events;
- formula versions, evidence, experiments, predictions, and outcomes;
- FastAPI laboratory views;
- backup, restore, and export;
- 388 engine tests and 154 backend tests at the documented committed baseline;
- 18 required verifier checks passing;
- a Scientific Release block caused by absent preregistered held-out sensory validation;
- substantial heuristic-data limitations.

Does not prove that the restored tree still has exactly that state. Sol must verify it.

### P2. Reconstruction implementation audit

**Source:** user-provided `Perfume-Chem Reconstruction System — Implementation Audit`  
**Classification:** PROJECT_SOURCE

Supports the existence of a newer reconstruction subsystem with:

- standalone evidence, target, inventory, bottle, analysis, sensory, and regulatory dataclasses;
- six audited defects;
- no independent build ledger;
- unpopulated authority logic;
- incomplete event semantics;
- identity-equivalence risks;
- many untested modules;
- 9 DONE, 5 PARTIAL, 6 NOT STARTED acceptance results.

The audit is a defect hypothesis list, not proof that every defect exists in the restored tree.

---

## 2. OAV, odor intensity, and mixture interaction

### L1. Audouin, Bonnet, Vickers, and Reineccius, 2001

**Title:** “Limitations in the Use of Odor Activity Values to Determine Important Odorants in Foods”  
**Type:** PRIMARY  
**DOI:** `10.1021/bk-2001-0782.ch014`  
**URL:** https://pubs.acs.org/doi/10.1021/bk-2001-0782.ch014

**Supports:**

- thresholds vary within and among individuals;
- odor intensity functions differ among odorants;
- OAV was not a useful direct measure of intensity in the tested panels;
- OAV was not a good indicator of percent contribution to overall binary-mixture intensity.

**Implementation consequence:**

OAV may rank candidate relevance but must not be rendered as percent sensory contribution, exact intensity, or similarity.

### L2. Ferreira, 2012

**Title:** “Revisiting psychophysical work on the quantitative and qualitative odour properties of simple odour mixtures: Part 1, intensity and detectability”  
**Type:** REVIEW  
**DOI:** `10.1002/ffj.2090`  
**URL:** https://onlinelibrary.wiley.com/doi/10.1002/ffj.2090

**Supports:**

- supra-threshold mixture intensity is often hypoadditive;
- suppression can be asymmetric;
- adding more isointense components may not increase intensity;
- sub- and peri-threshold compounds may alter mixture perception;
- synergy is context-dependent and not universally predictable.

**Implementation consequence:**

Use interaction hypotheses and sensory tests. Do not sum OAV or single-component intensity into an unquestioned mixture score.

### L3. Cain, Schiet, Olsson, and de Wijk, 1995

**Title:** “Comparison of Models of Odor Interaction”  
**Type:** PRIMARY  
**DOI:** `10.1093/chemse/20.6.625`

**Supports:**

- different interaction models fit different mixtures;
- strongest-component behavior can be useful but incomplete;
- simple additive psychophysical models can overestimate mixture intensity.

**Implementation consequence:**

Keep several baseline models and compare them empirically rather than hard-coding one universal mixture law.

### L4. Johnson, Hirson, and Ebeler, 2012

**Title:** “Perceptual Characterization and Analysis of Aroma Mixtures Using Gas Chromatography Recomposition-Olfactometry”  
**Type:** PRIMARY  
**DOI:** `10.1371/journal.pone.0042693`  
**URL:** https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0042693

**Supports:**

- recomposed lavender mixtures displayed additive, masking, and synergistic effects;
- recognizable lavender character emerged from specific mixtures;
- selective recombination is useful for investigating causal odor subsets.

**Implementation consequence:**

Support recombination, omission, block omission, and addition experiments.

### L5. Brossard, Rousseau, and Dumont, 2007

**Title:** “Perceptual interactions between characteristic notes smelled above aqueous solutions of odorant mixtures”  
**Type:** PRIMARY  
**DOI:** `10.1093/chemse/bjm002`

**Supports:**

- component odor intensity may fall in mixtures;
- behavior in binary mixtures may not extrapolate to ternary mixtures;
- dominance and suppression can change with mixture context.

**Implementation consequence:**

Store interaction records with concentration and matrix. Never create universal pair constants from one experiment.

### L6. Romagny, Coureaud, and Thomas-Danguin, 2018

**Title:** “Key odorants or key associations? Insights into elemental and configural odour processing”  
**Type:** PRIMARY  
**DOI:** `10.1002/ffj.3429`  
**URL:** https://onlinelibrary.wiley.com/doi/10.1002/ffj.3429

**Supports:**

- elemental perception can depend on recognizable key odorants;
- configural perception can depend on specific associations in strict concentration ratios;
- omission impact does not always mean the omitted odorant resembles the whole mixture.

**Implementation consequence:**

Model both key materials and key associations. Anti-compression and ratio preservation are essential.

### L7. Laing and Francis, 1989

**Title:** “The capacity of humans to identify odors in mixtures”  
**Type:** PRIMARY  
**Journal:** Physiology & Behavior 46:809–814

**Supports:**

- humans have limited ability to identify individual components in multicomponent mixtures.

**Implementation consequence:**

Do not confuse component identifiability with mixture distinctness. A formula can contain essential low-identifiability components.

---

## 3. Perfume engineering, release, and formulation optimization

### L8. Rodrigues, Nogueira, and Faria, 2021

**Title:** “Perfume and Flavor Engineering: A Chemical Engineering Perspective”  
**Type:** REVIEW  
**DOI:** `10.3390/molecules26113095`  
**URL:** https://www.mdpi.com/1420-3049/26/11/3095

**Supports:**

- perfume design can combine vapor-liquid equilibrium, diffusion, odor classification, and performance modeling;
- matrix and skin/substrate effects matter;
- engineering models can support, but not replace, fragrance design.

**Implementation consequence:**

Separate physical release, diffusion, odor models, and sensory validation. Preserve model scope.

### L9. Costa et al., 2015

**Title:** “Modeling Fragrance Components Release from a Simplified Matrix Used in Toiletries and Household Products”  
**Type:** PRIMARY  
**DOI:** `10.1021/acs.iecr.5b03852`

**Supports:**

- Henry-law measurements can characterize release from DPG;
- single-component and multicomponent partition behavior can be compared;
- UNIFAC plus modified Raoult’s law can be evaluated against experimental headspace.

**Implementation consequence:**

A DPG model is matrix-specific. Use experimental Henry constants where available and benchmark multicomponent predictions.

### L10. Teixeira, Rodríguez, and Rodrigues, 2013

**Title:** “Diffusion and performance of fragranced products: Prediction and validation”  
**Type:** PRIMARY  
**DOI:** `10.1002/aic.14106`

**Supports:**

- diffusion models can be tested against measured gas-phase concentration;
- physical concentration profiles and psychophysical intensity transformations are distinct layers.

**Implementation consequence:**

Validate physical predictions first. Label perceptual transformations separately and retain their assumptions.

### L11. Almeida et al., 2021

**Title:** “Radial diffusion model for fragrance materials: Prediction and validation”  
**Type:** PRIMARY  
**DOI:** `10.1002/aic.17351`

**Supports:**

- Fickian radial diffusion can be coupled with liquid nonideality;
- SPME/GC-FID can provide validation data;
- model validity is apparatus- and domain-specific.

**Implementation consequence:**

Store substrate/apparatus identity and avoid transferring a chamber model directly to skin longevity.

### L12. Zhang et al., 2021

**Title:** “Optimization-based cosmetic formulation: Integration of mechanistic model, surrogate model, and heuristics”  
**Type:** PRIMARY  
**DOI:** `10.1002/aic.17064`

**Supports:**

- a hierarchy of mechanistic, surrogate, and heuristic models can accelerate formulation;
- sensorial and physical attributes create a multiobjective problem;
- iterative refinement is preferable to one-shot optimization.

**Implementation consequence:**

Use hard constraints plus Pareto candidates. Do not let one scalar score become the product brief.

### L13. Zhang et al., 2024

**Title:** “Design of Fragrance Formulations with Antiviral Activity Using Bayesian Optimization”  
**Type:** PRIMARY, but endpoint is antiviral activity rather than odor quality  
**DOI:** `10.3390/microorganisms12081568`

**Supports:**

- Bayesian optimization can efficiently navigate combinatorial mixture spaces when an experimentally measurable endpoint exists.

**Does not support:**

- Bayesian optimization alone can optimize fine-fragrance quality.

**Implementation consequence:**

Bayesian optimization may choose sensory experiments after enough valid data exist. It cannot invent a validated odor-quality objective.

---

## 4. Matrix effects, vapor-liquid equilibrium, and thermodynamic models

### L14. Ickes and Cadwallader, 2017

**Title:** “Effects of Ethanol on Flavor Perception in Alcoholic Beverages”  
**Type:** REVIEW  
**DOI:** `10.1007/s12078-017-9238-2`

**Supports:**

- ethanol changes water/ethanol matrix structure;
- ethanol concentration affects aroma release and sensory profile;
- static and dynamic headspace effects can differ.

**Implementation consequence:**

Matrix composition and measurement mode are mandatory model inputs.

### L15. Le Thanh, Lamer, Voilley, and Jose, 1993

**Title:** Vapor-liquid partition and activity coefficients of aroma compounds  
**Type:** PRIMARY  
**DOI:** `10.1051/jcp/1993900545`

**Supports:**

- measured and property-derived partition estimates can differ substantially;
- UNIFAC estimates showed meaningful average error against measured values in the studied compounds.

**Implementation consequence:**

UNIFAC is not ground truth. Report benchmark error and uncertainty.

### L16. Dupeux et al., 2022

**Title:** “COSMO-RS as an effective tool for predicting the physicochemical properties of fragrance raw materials”  
**Type:** PRIMARY  
**DOI:** `10.1002/ffj.3690`

**Supports:**

- COSMO-RS was evaluated on 166 fragrance-related organic compounds for boiling point, logP, vapor pressure, water solubility, and Henry-law constant.

**Implementation consequence:**

COSMO-RS can be a model adapter with exact version, inputs, and validation metrics. It is not measured data.

### L17. Cetti et al., 2017

**Title:** “Modeling the Vapor–Liquid Equilibria of Ionic Liquids Containing Perfume Raw Materials”  
**Type:** PRIMARY  
**DOI:** `10.1021/acs.jced.7b00116`

**Supports:**

- UNIFAC and COSMO-RS have different applicability limits;
- COSMO-RS can cover systems where group parameters are absent, but still requires validation.

**Implementation consequence:**

Model selection and abstention must be explicit.

---

## 5. Natural materials, lots, and authenticity

### L18. ISO 9235:2021

**Title:** “Aromatic natural raw materials — Vocabulary”  
**Type:** OFFICIAL_STANDARD  
**URL:** https://www.iso.org/standard/78908.html

**Supports:**

- controlled terminology for aromatic natural raw materials.

**Implementation consequence:**

Natural material identity should use standardized material and process vocabulary.

### L19. ISO 11024-1:1998 and ISO 11024-2:1998

**Title:** General guidance on essential-oil chromatographic profiles  
**Type:** OFFICIAL_STANDARD  
**URLs:**
- https://www.iso.org/standard/19008.html
- https://www.iso.org/standard/19009.html

**Supports:**

- chromatographic profiles are quality specifications;
- relative proportions are not automatically true component concentrations;
- profile compliance can be compared with reference profiles.

**Current-status note:**

ISO/DIS 11024 was registered in 2026 to replace the two 1998 parts. Draft status must not be treated as a published replacement.

**Implementation consequence:**

Store `relative_area_profile` separately from calibrated composition.

### L20. Do et al., 2015

**Title:** “Authenticity of essential oils”  
**Type:** REVIEW  
**DOI:** `10.1016/j.trac.2014.10.007`

**Supports:**

- adulteration can require chiral GC, isotope-ratio MS, NMR, multidimensional chromatography, and chemometrics;
- ordinary GC-MS may not detect all authenticity problems.

**Implementation consequence:**

Authenticity is a scoped analytical conclusion, not a checkbox derived from one chromatogram.

### L21. Yang et al., 2024

**Title:** “Advanced analytical techniques for authenticity identification and quality evaluation in essential oils”  
**Type:** REVIEW  
**DOI:** `10.1016/j.foodchem.2024.139340`

**Supports:**

- harvest, extraction, separation, volatility, oxidation, and adulteration affect quality;
- sensory, physical, and chemical approaches are complementary.

**Implementation consequence:**

Naturals require lot, storage, process, and analytical state.

### L22. Upton et al., 2019

**Title:** “Botanical ingredient identification and quality assessment: strengths and limitations of analytical techniques”  
**Type:** REVIEW  
**DOI:** `10.1007/s11101-019-09625-z`

**Supports:**

- no single technique is universally sufficient;
- orthogonal botanical and chemical methods give stronger identity confidence.

**Implementation consequence:**

Authority aggregation should reward independent methods rather than maximum confidence.

### L23. Lebanov et al., 2019

**Title:** “Multidimensional Gas Chromatography in Essential Oil Analysis. Part 2”  
**Type:** REVIEW  
**DOI:** `10.1007/s10337-018-3651-9`

**Supports:**

- coelution, chiral constituents, low-abundance compounds, chemotype, plant organ, environment, age, and distillation complicate EO characterization.

**Implementation consequence:**

Preserve unresolved peaks and method limits. Do not force a complete named composition.

---

## 6. Analytical identification, quantitation, and method validation

### L24. ISO/IEC 17025:2017

**Title:** “General requirements for the competence of testing and calibration laboratories”  
**Type:** OFFICIAL_STANDARD  
**URL:** https://www.iso.org/standard/66912.html

**Supports:**

- laboratory competence, impartiality, consistent operation, and valid results;
- risk-based quality systems and method control.

**Implementation consequence:**

Analytical authority requires method, instrument, personnel, QC, and scope records.

### L25. Eurachem, 2025

**Title:** “The Fitness for Purpose of Analytical Methods — A Laboratory Guide to Method Validation and Related Topics,” 3rd ed.  
**Type:** GUIDANCE  
**URL:** https://www.eurachem.org/index.php/component/content/article/3-publications/guides/144-gdmv2014

**Supports:**

- fit-for-purpose validation;
- performance characteristics;
- validation and verification planning;
- scope-dependent extent of validation.

**Implementation consequence:**

Method state must include selectivity, calibration, range, detection/quantitation, precision, trueness/recovery, robustness, matrix effects, and uncertainty as applicable.

### L26. Wong and Marriott, 2017

**Title:** “Approaches and Challenges for Analysis of Flavor and Fragrance Volatiles”  
**Type:** REVIEW  
**DOI:** `10.1021/acs.jafc.7b03112`

**Supports:**

- complex fragrance matrices contain many isomers and coelutions;
- GC-MS spectra may be insufficiently specific;
- authentic standards and multidimensional separation increase confidence but do not erase all ambiguity.

**Implementation consequence:**

Identification confidence must preserve RI, authentic-standard, spectrum, coelution, and manual-review evidence independently.

### L27. Mahmoud and Zhang, 2024

**Title:** “Enhancing Odor Analysis with Gas Chromatography-Olfactometry: Recent Breakthroughs and Challenges”  
**Type:** REVIEW  
**DOI:** `10.1021/acs.jafc.3c08129`

**Supports:**

- GC-O is valuable for odor-active compounds;
- repeatability, trace odorants, matrix effects, and interlaboratory consistency remain challenges.

**Implementation consequence:**

GC-O events need assessor, replicate, detection frequency, and uncertainty. They must not be forced into exact chemical IDs.

### L28. Biniecka and Caroli, 2011

**Title:** “Analytical methods for the quantification of volatile aromatic compounds”  
**Type:** REVIEW  
**DOI:** `10.1016/j.trac.2011.06.015`

**Supports:**

- volatile analysis needs fit-for-purpose quality systems;
- instrumental and sensory methods are complementary.

**Implementation consequence:**

Analytical ledgers and sensory ledgers must connect without merging their evidence types.

---

## 7. Measurement uncertainty and provenance

### L29. JCGM 100:2008

**Title:** “Guide to the expression of uncertainty in measurement”  
**Type:** OFFICIAL_GUIDANCE  
**DOI:** `10.59161/JCGM100-2008E`  
**URL:** https://www.bipm.org/en/doi/10.59161/jcgm100-2008e

**Supports:**

- general rules for evaluating and expressing measurement uncertainty.

### L30. JCGM 101:2008

**Title:** “Propagation of distributions using a Monte Carlo method”  
**Type:** OFFICIAL_GUIDANCE  
**DOI:** `10.59161/JCGM101-2008`  
**URL:** https://www.bipm.org/en/doi/10.59161/jcgm101-2008

**Supports:**

- Monte Carlo propagation through nonlinear measurement models.

**Implementation consequence for L29–L30:**

Quantities carry uncertainty. Nonlinear conversions may require distribution propagation rather than first-order arithmetic.

### L31. NIST Policy on Metrological Traceability

**Type:** OFFICIAL_GUIDANCE  
**URL:** https://www.nist.gov/calibrations/traceability

**Supports:**

- traceability is a property of a measurement result;
- an unbroken calibration chain contributes to uncertainty;
- traceability alone does not guarantee fitness for purpose.

**Implementation consequence:**

Do not label an instrument, laboratory, or record “traceable” without a result-specific chain and uncertainty.

### L32. W3C PROV-DM

**Type:** OFFICIAL_STANDARD  
**URL:** https://www.w3.org/TR/prov-dm/

**Supports:**

- provenance entities, activities, agents, derivations, generation, use, and responsibility.

**Implementation consequence:**

Canonical provenance should map naturally to these concepts.

### L33. Wilkinson et al., 2016

**Title:** “The FAIR Guiding Principles for scientific data management and stewardship”  
**Type:** PRIMARY/CONSENSUS PRINCIPLES  
**DOI:** `10.1038/sdata.2016.18`

**Supports:**

- findable, accessible, interoperable, and reusable data and workflows;
- machine-actionable metadata.

**Implementation consequence:**

Export schema, IDs, metadata, and provenance should support reuse without relying on generated markdown.

### L34. RFC 8785

**Title:** “JSON Canonicalization Scheme”  
**Type:** OFFICIAL_TECHNICAL_STANDARD  
**URL:** https://www.rfc-editor.org/rfc/rfc8785.html

**Supports:**

- deterministic JSON canonicalization for hashing/signing;
- property sorting and strict primitive serialization;
- large or high-precision numbers may need string representation.

**Implementation consequence:**

Represent exact decimals as canonical strings or another rigorously specified form. Do not hash unstable float output.

---

## 8. Sensory science and preregistration

### L35. ISO 8586:2023

**Title:** “Sensory analysis — Selection and training of sensory assessors”  
**Type:** OFFICIAL_STANDARD  
**URL:** https://www.iso.org/standard/76667.html

**Supports:**

- assessor selection and training for food, beverage, home, and personal-care products.

**Implementation consequence:**

Assessor qualification and monitoring are canonical records.

### L36. ISO 13299:2016

**Title:** “Sensory analysis — General guidance for establishing a sensory profile”  
**Type:** OFFICIAL_STANDARD  
**URL:** https://www.iso.org/standard/58042.html

**Supports:**

- development of sensory profiles;
- comparison with references;
- linking perceived attributes to chemical or physical data;
- cosmetics and odors are within scope.

**Implementation consequence:**

Use descriptive profiling for attribute magnitude and reference-profile comparison.

### L37. ISO 4120:2021

**Title:** “Sensory analysis — Triangle test”  
**Type:** OFFICIAL_STANDARD  
**URL:** https://www.iso.org/standard/76666.html

**Supports:**

- forced-choice difference or similarity testing;
- limited use for products with strong carryover or lingering effects.

**Implementation consequence:**

Do not default to triangle tests for fine fragrance. Select based on persistence and claim.

### L38. ISO 5495:2005

**Title:** “Sensory analysis — Paired comparison test”  
**Type:** OFFICIAL_STANDARD  
**URL:** https://www.iso.org/standard/31621.html

**Supports:**

- directional difference and paired similarity questions;
- lower sample burden than three-sample designs;
- absence of an attribute difference does not prove total product identity.

**Implementation consequence:**

Use paired designs when the question and carryover conditions fit.

### L39. Marques et al., 2022

**Title:** “An Overview of Sensory Characterization Techniques”  
**Type:** REVIEW  
**DOI:** `10.3390/foods11030255`

**Supports:**

- discriminative, descriptive, and temporal methods answer different questions;
- time-intensity approaches capture changing perception.

### L40. Ballester and Schoumacker, 2023

**Title:** “Dynamic Instrumental and Sensory Methods Used to Link Aroma Release and Aroma Perception”  
**Type:** REVIEW  
**DOI:** `10.3390/molecules28176308`

**Supports:**

- temporal sensory methods and instrumental release measurements can be paired;
- interindividual differences remain important.

**Implementation consequence for L39–L40:**

Store temporal sensory observations separately from physical headspace; link them through analysis, not identity.

### L41. Nosek et al., 2018

**Title:** “The preregistration revolution”  
**Type:** PRIMARY/OPEN SCIENCE METHODOLOGY  
**DOI:** `10.1073/pnas.1708274114`  
**URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC5856500/

**Supports:**

- preregistration distinguishes hypothesis generation from prediction testing;
- defining questions and analysis before outcomes improves claim credibility.

**Implementation consequence:**

Lock confirmatory protocol, endpoint, analysis, formula, lot, and code hashes before collecting held-out sensory outcomes.

---

## 9. Regulatory snapshots

### L42. IFRA 51st Amendment

**Type:** OFFICIAL_INDUSTRY_STANDARD  
**Notification:** 30 June 2023  
**URLs:**
- https://ifrafragrance.org/latest-updates/press-releases/notification-of-the-51st-amendment-to-the-ifra-standards
- https://ifrafragrance.org/initiatives-positions/safe-use-fragrance-science/ifra-standards/ifra-standards-documentation
- https://ifrafragrance.org/publications/guidanceReferenceDocument/51st-amendment-document

**Supports:**

- the 51st Amendment is the latest formally notified complete set as of 2026-07-29;
- documentation includes guidance, standard index, and contributions from other sources.

### L43. IFRA 52nd Amendment consultation status

**Type:** OFFICIAL_CURRENT_STATUS  
**URL:** https://ifrafragrance.org/latest-updates/ifra-news/ifra-52nd-amendment-consultation-closed

**Verified status on 2026-07-29:**

- consultation closed 12 June 2026;
- IFRA reported formal notification expected near the end of November 2026.

**Implementation consequence:**

Store 52nd consultation material as `DRAFT/CONSULTATION/WATCHLIST`, not the active enforced snapshot.

### L44. Commission Regulation (EU) 2023/1545

**Type:** OFFICIAL_REGULATION  
**URL:** https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng

**Supports:**

- expanded fragrance-allergen labeling under the EU cosmetics framework;
- transition periods for new restrictions and withdrawal of noncompliant products.

**Implementation consequence:**

Allergen labeling, IFRA limits, and jurisdictional legal compliance are separate rule families.

---

## 10. Verification rules derived from the literature

Sol must verify that the implementation:

1. never renders OAV as percent sensory contribution;
2. stores threshold context and uncertainty;
3. permits masking, synergy, suppression, and configural associations;
4. keeps target ratios and associations versioned;
5. separates static from dynamic headspace;
6. identifies matrix, temperature, and substrate;
7. labels actual UNIFAC separately from heuristic similarity models;
8. abstains outside model domains;
9. separates natural relative profiles from calibrated composition;
10. preserves unknown peaks and coelutions;
11. requires calibration for quantitative analytical claims;
12. links QC to analytical runs;
13. propagates measurement uncertainty;
14. produces deterministic canonical hashes;
15. records entity/activity/agent provenance;
16. uses trained-panel records for descriptive claims;
17. uses claim-appropriate difference tests;
18. locks preregistered confirmatory studies;
19. versions IFRA and legal rules;
20. releases only claim-specific scopes.

---

## 11. Source-quality cautions

- Food and beverage aroma research is highly relevant to mixture perception and headspace, but perfume matrices and application substrates differ. Treat cross-domain transfer as literature-derived, not direct validation.
- Engineering papers that transform gas concentration into predicted odor intensity do not prove human fine-fragrance performance without sensory validation.
- Preprints and machine-learning fragrance papers can inform architecture but should not become runtime authority without replication.
- ISO abstracts summarize standards but do not replace licensed full-text standards where detailed procedural compliance is required.
- IFRA is an industry product-stewardship standard, not a substitute for national or regional law.
