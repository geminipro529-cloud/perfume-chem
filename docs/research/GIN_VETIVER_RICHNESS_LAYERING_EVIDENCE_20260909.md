# Gin Vetiver - Cypress Air EDP: research-led proposal discrimination

Date: 2026-09-09. Status: RESEARCH PRIORITIZATION; not a calibrated sensory ranking.

## Scope and provenance

Assess the 56 proposals tied by the existing stock-retention evaluator. Develop
computer-only ways to compare body, target-linked richness, layering and liking.
No preliminary user mixing is required by this research workflow. No formula,
inventory, engine, gate threshold or release status is changed by this report.
Safety is not an optimization objective here; this report does not certify it.

Baseline: `formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json`.
SHA256: `426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`.
Receipt: `output/gin_vetiver_concurrent_structural_20260909.json`.
Live formula hash was checked again while preparing this report.
Inventory hash previously verified in this research pass:
`d6f7ff5389fbd5e807b98fee3ce6a87ce2c70dd6253b26a82f49a0872da42369`.

The saved composition has 18 stocks, 5400 uL nominal fragrance-stock volume and
24600 uL ethanol stock. Raw-volume loading is not exact active w/w concentration.
Transfers below are existing computational proposals, not instructions to add
materials to a bottle. Grapefruit FCF, juniper and light cypress remain in scope;
Hedione is allowed, jasmine accords are not. No new DEP carrier is proposed.

Research used primary manufacturer documents and original perception studies.
Consensus search plus fetched paper record and SciSpace search supplemented the
primary-source search. MotherDuck returned reauthentication-required; Wolfram
returned connection/internal errors. No database data or Wolfram calculation was
obtained, no cloud writes were made, and neither tool is credited with findings.
Manufacturer descriptions establish plausible functions,
not measured benefits at our ratios. Two native read-only reviewers mapped the
candidate groups and audited local model scope; parent checked the run receipt
and relevant implementation. No non-OpenAI model delegation was used.

## Why the old evaluator cannot choose

Both objectives penalize only reductions in a group's raw-volume sum:
`L = max(0, (B - S)/B)`.
For a transfer d between two ingredients in that group,
`(v_i-d)+(v_j+d) = v_i+v_j`; therefore S and L are unchanged.
This identity holds independently of the chemical or sensory effects. The
baseline already has zero loss. The ties are an objective-design limitation,
not evidence that the proposals smell alike.

The 56 candidates comprise 31 directed choices at different step sizes.
The fixed natural-vetiver floor permits increases but not decreases; the cypress
ceiling permits decreases but not increases. Those asymmetries are inherited
design policies, not evidence of sensory improvement. Grapefruit, musks, Vetival,
Ambrox Super and carriers were not explored by this neighborhood.

## Primary evidence and the claims it supports

### Material functions

- **Iso E Super:** IFF describes a smooth woody-amber material contributing
  fullness and subtle strength. Supports a woody-body hypothesis, not a numerical
  liking increment. [IFF](https://www.iff.com/scent/ingredients-compendium/iso-e-super/)
- **Hedione:** manufacturer describes presence and diffusion without necessarily
  increasing strength. Retain its transparent support; more volume is not by
  itself evidence of denser body. [DSM-Firmenich](https://studio.dsm-firmenich.com/product/hedioner-pe-964898)
- **Vetikon:** Symrise describes woody/vetiver/grapefruit facets and a connection
  from natural vetiver into the opening. Supports testing continuity and vetiver
  identity, not simply treating it as another persistent base material.
  [Symrise technical sheet](https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Vetikon.pdf)
- **Clearwood:** soft patchouli, woody and amber warmth support a conditional
  depth hypothesis. This is Clearwood, not Clearwood Prisma. Warmth is a tradeoff
  against this brief's dry botanical character, not an automatic defect.
  [DSM-Firmenich](https://studio.dsm-firmenich.com/product/clearwoodr-pe-970953)
- **Timberol:** powerful, substantive woody-amber modification is distinct from
  the subtle fullness of Iso E Super. Potency alone does not establish richness.
  [Symrise technical sheet](https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Timberol.pdf)
- **Coriander seed EO:** aromatic, spicy, peppery and slightly lemony/woody;
  generic seed-oil evidence, not coriander leaf or a measured user-lot analysis.
  [DSM-Firmenich](https://studio.dsm-firmenich.com/product/coriander-seed-eo-pe-928143)
- **Petitgrain Paraguay:** green/floral facets provide a different direction
  from seed spice; not simply a promise of persistent grapefruit.
  [Robertet](https://matieres-premieres.robertet.com/petitgrain-oil)
- **Terpinyl acetate:** supplier application data describes herbal, citrus,
  woody, lavender and floral aspects at 10% in DPG. This is not the dihydro
  material, and the evaluation matrix is not our finished ethanol perfume.
  [Sigma application guide](https://www.sigmaaldrich.com/deepweb/assets/sigmaaldrich/marketing/global/documents/295/364/application-guide-9-scents-of-fall-and-winter-ms.pdf)

Supplier use ranges are neither optimum ratios nor hard aesthetic limits.
Generic natural-oil descriptions do not resolve lot-dependent constituent levels.

### Perception and model evidence

1. **Pellegrino et al., 2026 preprint:** 432 mixtures, 2-10 components, were
   well predicted by averages of component quality profiles under the studied
   conditions. This supports a simple quality-vector benchmark. It does not
   establish full-perfume liking or our concentration-response curves. A fixed,
   unweighted average over the same ingredients would also tie ratio-only
   proposals; concentration-conditioned profiles or validated weights are needed.
   Preprint, not peer-reviewed; raw dataset not downloaded or fitted here.
   [Primary record](https://pubmed.ncbi.nlm.nih.gov/42465471/)
   [Fetched Consensus record](https://consensus.app/papers/odors-smell-like-their-components-a-linear-framework-for-pellegrino-mayhew/004229f777a4530d82d4292f9b4d0f67/)
2. **Sinding et al., 2013:** the human portion of a six-component mixture study
   found that blending depended on both component identities and proportions.
   This motivates ratio-sensitive and omission benchmarks, not assumed synergy
   for our ingredients. It also cautions against interpreting descriptor-vector
   fit as complete prediction of recognition or blending.
   [PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0053534)
3. **Lapid, Harel and Sobel, 2008:** intensity-weighted pleasantness modeling of
   five binary pairings supports separating perceived intensity from liking.
   It requires relevant measured inputs; it is not validated on this 18-stock
   perfume. [Chemical Senses](https://academic.oup.com/chemse/article/33/7/599/330603)
4. **Livermore and Laing, 1998:** trained subjects identified only a limited
   number of object odors in mixtures. This argues against ingredient count as
   a layering score, not for a four-ingredient formulation limit.
   [Original study](https://doi.org/10.3758/BF03206052)
5. **POMMix, 2025 preprint version 1:** explicitly does not model concentration
   or intensity, and uses intensity-balanced mixtures. Its similarity task is
   not a calibrated liking endpoint. Do not drop it unchanged into this
   ratio-optimization problem. [Primary manuscript](https://arxiv.org/html/2501.16271v1)
6. **Evaporation/absorption modeling:** published validation against human
   measurements supports physical modeling within tested domains. It does not
   turn simulated composition change into measured perceived layering or skin
   longevity. [Original model abstract](https://pubmed.ncbi.nlm.nih.gov/18503438/)

## Resolve the proposals into distinct design questions

Arrows mean remove the stated raw volume from the left stock and allocate the
same raw volume to the right stock. These are hypothesis families; their step
sizes remain unranked. No claim that 50 uL is perceptibly better than 25 or 10.

### Vetiver/body: 16 directed choices, 41 candidates

| Existing directions | Steps per direction, uL | Count | Research interpretation |
|---|---|---:|---|
| Hedione -> Iso E Super; reverse | 10,25,50 | 6 | First body-focused comparison: woody fullness versus transparent support. Prefer investigating the forward direction for this brief, not declaring it a sensory winner. |
| Iso E Super -> Vetikon; reverse | 10,25,50 | 6 | Vetiver/grapefruit continuity versus smooth woody fullness; neither dominates both objectives a priori. |
| Hedione -> Vetikon; reverse | 10,25,50 | 6 | Target-specific vetiver continuity versus airy support. Direct alternative to the two choices above, not a reason to stack all three. |
| Hedione -> Clearwood; reverse | 10,25 | 4 | Conditional warmer patchouli/amber depth versus transparency. Lower priority if it drifts away from dry gin-vetiver. |
| Iso E Super -> Clearwood; reverse | 10,25 | 4 | Patchouli/amber texture versus smooth abstract woody fullness. Evidence supplies roles, not an optimum. |
| Vetikon -> Clearwood; reverse | 10,25 | 4 | Warm depth versus vetiver/citrus continuity. Forward is not an automatic richness improvement. |
| Clearwood -> natural vetiver | 10,25 | 2 | More natural-vetiver stock, less patchouli/amber support. Root character depends on the actual oil. |
| Hedione -> natural vetiver | 10,25,50 | 3 | Natural-vetiver emphasis at the expense of transparency; not a generic quality bonus. |
| Iso E Super -> natural vetiver | 10,25,50 | 3 | Natural character versus smooth supporting wood. |
| Vetikon -> natural vetiver | 10,25,50 | 3 | Natural-root emphasis versus the documented opening bridge. |

### Botanical middle: six directed choices, six candidates

| Directions | Steps, uL | Count | Research interpretation |
|---|---|---:|---|
| Petitgrain -> coriander seed; reverse | 10 | 2 | Seed spice versus green/floral leaf. Distinguish aromatic identity from generic citrus-stock retention. |
| Terpinyl acetate -> coriander seed; reverse | 10 | 2 | Seed-spice specificity versus broader herbal/citrus/lavender support. |
| Terpinyl acetate -> petitgrain; reverse | 10 | 2 | Natural green/floral-leaf emphasis versus herbal ester support. No validated ratio preference. |

### Finish: nine directed choices, nine candidates

| Directions | Steps, uL | Count | Research interpretation |
|---|---|---:|---|
| Virginia cedar -> Iso E Super; reverse | 10 | 2 | Test natural woody texture versus documented smooth fullness; exact cedar role remains a formulation hypothesis. |
| Virginia cedar -> Timberol; reverse | 10 | 2 | Powerful woody-amber modification versus natural woody texture; strength is not richness. |
| Timberol -> Iso E Super; reverse | 10 | 2 | Compare woody power with subtle fullness. Do not reward either merely for persistence. |
| Cypress -> Virginia cedar | 10 | 1 | Deprioritize absent evidence that current cypress is too strong; loses part of the named accent. |
| Cypress -> Iso E Super | 10 | 1 | Same identity tradeoff; body-stock arithmetic alone cannot justify it. |
| Cypress -> Timberol | 10 | 1 | Same identity tradeoff plus a different woody-amber direction. |

Priority is **body / continuity / conditional depth**, not a total ordering of
56 formulas. This resolves design meaning; it does not pretend to resolve
unmeasured dose differences or a user's eventual preference.

## Defensible computer-only evaluator design

Separate endpoints instead of renaming one generic score:

1. **Identity:** gin/juniper, vetiver, restrained cypress and grapefruit direction.
   Hard bookkeeping rules remain labeled design constraints, not sensory proof.
2. **Quality and body:** common-lexicon, source-linked material quality vectors;
   distinguish transparent support, smooth wood, natural root and warm depth.
   Manufacturer prose may support hypotheses, not fitted effect sizes.
3. **Richness:** candidate proxy for simultaneous target-relevant facets and
   their contrast/coherence. This is a proposed design metric, not an established
   psychometric scale. Do not maximize count, entropy, intensity or heavy-stock
   amount as a substitute.
4. **Layering:** distinguish simultaneous facets from development over time.
   Model whether target identity persists while emphasis changes. Larger temporal
   change is not automatically better; uncalibrated simulator frames are not
   measured perception. Propagate natural composition and physical uncertainty.
5. **Liking:** a separate endpoint requiring applicable human ratings. Do not
   manufacture a hedonic increment from supplier descriptions or OAV. Keep
   quantitative preference unavailable outside demonstrated coverage while
   continuing evidence-directed design comparisons.

Concentration effects require stock-aware active mass/ppm, matrix-matched ODT,
and explicit concentration-response assumptions. Headspace OAV is a screening
quantity, not perceived share, intensity, richness or liking. Natural mixtures
must retain constituent-based treatment and its uncertainty. Missing density or
carrier information must not become a silent density-of-one conversion.

Compare simple mean-quality, concentration-conditioned quality and any nonlinear
alternative on held-out human data before choosing complexity. Hold out studies,
formulas and component identities to expose leakage. Require a same-ingredient,
different-ratio test; an evaluator insensitive to that cannot resolve this run.
Keep quality, intensity, recognition and liking evaluation labels separate.

Use Pareto comparisons with uncertainty, not invented weighted points. Admit an
evaluator revision only if it improves relevant held-out predictions and passes
frozen identity/units/data-coverage challenges. Compare candidates under that
fixed version; do not loosen acceptance criteria because the baseline ties.

Recursive sequence: frozen benchmark -> parallel body/continuity/depth proposals
-> uncertainty-aware comparison -> retain defensible alternatives -> smaller
steps around supported improvements -> stop at robust target attainment, plateau,
coverage boundary or budget. Physical mixing is not an admission requirement.
Stopping computationally does not imply a smelled or personally liked perfume.

## Local implementation assessment

`engine/optimizer/gate_aware.py` already supplies bounded concurrent candidate
search and evaluator-version admission mechanics. This research does not alter it.
`engine/hedonic_model.py` has scoped observed-data logic; its legacy generic score
must not replace missing target evidence. `engine/fingerprint.py` mixes quality,
role and physics features, so its vector is not a standardized human odor profile.
`engine/perception/construction_complexity.py` separates useful axes but does not
authorize inferred mixture gradients from descriptor geometry alone.
`engine/pipeline/simulator.py` explicitly describes its trajectory as uncalibrated.

Outcome: the candidate set now has a source-linked, target-specific comparison
plan. No revised formula, trained model, new hedonic score or pipeline PASS is
claimed. The first body hypothesis is Hedione -> Iso E Super; the main competing
continuity hypothesis is Iso E Super -> Vetikon, with Hedione -> Clearwood as a
conditional depth alternative rather than an assumed universal improvement.
