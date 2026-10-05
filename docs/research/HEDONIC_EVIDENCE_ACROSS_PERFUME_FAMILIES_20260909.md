# Hedonic evidence across perfume families

Research date: 2026-09-09. Scope: human liking, preference and mixture
perception relevant to computer-only perfume development. This is a targeted
evidence map, not an exhaustive systematic review or a fitted prediction model.
No formula, inventory or runtime scoring weights changed.

## Evidence register

1. **Barbosa et al., NEOS (2024 issue; online 2023)**.
   [Publisher](https://doi.org/10.1111/ics.12894),
   [PubMed](https://pubmed.ncbi.nlm.nih.gov/37594727/),
   [author-uploaded full article](https://www.researchgate.net/publication/373215551_NEOS_An_odour-induced_affect_scale_for_use_in_the_cosmetic_industry).
   Human affect and pleasantness data for commercial perfumes and odor samples.
   Table 1 provides useful family-labelled observations, not family optima or
   disclosed formulation ratios. Author affiliations include the manufacturer.
   Publisher access was intermittent; the table was checked in the author's copy.

2. **Pichon et al. (2015)**.
   [Full article](https://pmc.ncbi.nlm.nih.gov/articles/PMC4664615/).
   Nine commercial perfumes include citrus-aromatic, floral-aldehydic,
   floral-fruity, rose-violet, vanilla-amber, woody-amber and musky styles.
   Subjective pleasantness differentiated perfumes where physiological
   measures generally did not. Useful complete-product evidence; no formula
   disclosure or direct optimization of ingredient ratios.

3. **Apaolaza et al. (2014)**.
   [Publisher abstract and preview](https://www.sciencedirect.com/science/article/pii/S0950329314000512).
   112 participants evaluated floral, citrus and woody perfumes. Informing
   participants of natural origin improved hedonic evaluations. Supports
   controlling labels and expectations, not a chemical naturalness bonus.

4. **Lapid, Harel and Sobel (2008)**.
   [Full article](https://pmc.ncbi.nlm.nih.gov/articles/PMC2533422/).
   84 participants; five binary pairings tested at varying proportions.
   Mixture pleasantness usually lay between constituent pleasantness values
   and depended on perceived relative intensity. Candidate model: measured
   intensity-weighted pleasantness. Authors restrict scope and require
   concentration-specific psychophysical data; raw-volume averaging is not
   this model, and arbitrary large perfumes were not validated.

5. **Odors Smell Like Their Components (July 2026 preprint)**.
   [Primary preprint](https://www.biorxiv.org/content/10.64898/2026.07.03.736426v1.full).
   432 mixtures and 144 component odorants; descriptor-vector averaging is
   a promising quality-prediction baseline. Main quality analysis excludes
   pleasantness and intensity; binary pleasantness is a separate analysis.
   Experimental model candidate only, not peer-reviewed proof of an arbitrary
   EDP's liking or evaporation trajectory.

6. **Arshamian et al. (2022)**.
   [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/35381183/).
   Cross-cultural monomolecular rankings support both shared preferences and
   substantial individual variation. Useful population priors, not complete
   perfume or user-specific labels.

7. **Sorokowska et al. (2024)**.
   [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/38863390/).
   Cross-cultural/ecological results emphasize contextual differences as well
   as similarities. Retain population provenance; do not flatten studies into
   one supposedly universal preference vector.

8. **Genetic variation in OR5AN1 and musk perception (2023)**.
   [Full article](https://pmc.ncbi.nlm.nih.gov/articles/PMC9874024/).
   Human musk intensity/pleasantness ratings and receptor/genotype experiments.
   Tested musks and concentrations must remain explicit. Evidence supports
   individual-response variability, not a claim that all musks share one
   receptor or that an untested musk pair is complementary.

9. **Triscoli et al. (2014)**.
   [Primary abstract](https://pubmed.ncbi.nlm.nih.gov/24910630/),
   [full article](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.00526/full).
   Eighteen participants repeatedly evaluated three pleasant odors. Liking
   and wanting evolved differently. Repetition is not the same experiment
   as a perfume's chemically changing drydown; no fixed longevity bonus follows.

10. **Delplanque et al. (2008)**.
    [Author-hosted paper](https://www.unige.ch/fapse/e3lab/static/pdf/Delplanque_et_al_2008_chemsenses.pdf).
    Broad odor stimulus set includes leather and resinoid incense. Useful
    contextual odor-level evidence; not equivalent to leather/incense perfume
    preference or a prohibition on those materials.

11. **Fragrance-family loyalty study (2012 industry report)**.
    [Researcher's report](https://img.perfumerflavorist.com/files/base/allured/all/document/2012/01/pf.PF_37_02_026_07.pdf).
    372 women, retrospective favorites and retail sampling, classified by
    fragrance families. Preference clustering is useful exploratory evidence.
    Convenience selection, exposure and market composition limit inference;
    aromatic/fougere and green observations are especially sparse. Not a
    randomized blinded ranking of all families or a source of formula weights.

## Coverage map

Direct means an example of a complete perfume was evaluated, not that the
family's preferred formulation is known. Family labels can overlap.

| Requested territory | Evidence found | Ceiling |
|---|---|---|
| Citrus / cologne | Complete perfumes, sources 1-3 | No EDP versus EDT optimum |
| Aromatic / fougere | Aromatic perfume examples, 1-2; sparse fougere observations, 11 | Aromatic is not proof for every classical fougere |
| Floral / aldehydic / powdery | Complete perfumes, 1-2 | No universal floral benefit |
| White floral | Adjacent floral product evidence, 2 | Dedicated white-floral subgroup preference unresolved |
| Fruity | Complete fruity-floral and fruity-sweet products, 1-2 | No universal sweetness target |
| Woody / vetiver | Complete woody products, 1-3; odor-level vetiver data, 1 | No exact gin-vetiver preference surface |
| Amber / resinous | Amber/vanilla and woody products, 2; resin odor data, 1,10 | Not all resin combinations covered |
| Gourmand | Vanilla and fruity-sweet products, 1-2; repeated coconut exposure, 9 | Coffee/chocolate subtypes not established |
| Chypre / mossy | Complete chypre-fruity example, 1; observational families, 11 | No classical-chypre optimum |
| Musk / skin scent | Musky complete-product example, 2; material/genetic study, 8 | Untested musk blends unresolved |
| Green | Odor-level evidence, 1; sparse observations, 11 | Weak whole-perfume coverage |
| Leather / animalic | Odor-level ratings, 1,10; individual musk response, 8 | No whole-family pleasantness penalty justified |
| Incense / smoky | Incense odor samples, 1,10 | Dedicated smoky-perfume preference unresolved |
| Aquatic / ozonic | Insufficient directly verified product evidence in this search | Open evidence gap, not demonstrated dislike |

## Engineering conclusions (our interpretation, not published coefficients)

- Preserve complete-perfume, mixture, single-odorant and marketing-context
  evidence as separate record types.
- Bind records to exact stimulus identity, solvent/concentration basis,
  presentation, cohort, endpoint, spread, publication status and access level.
- Predict quality/identity separately from liking. Protect the declared brief
  while optimizing supported preference outcomes.
- Benchmark intensity-weighted hedonic models and descriptor-vector models
  against held-out human mixture data. Do not treat their outputs as equally
  validated or use raw OAV share as percent perceived contribution.
- Evaluate omissions and deliberately excessive support as identity checks.
  Such checks test design coherence; they are not invented human liking labels.
- Keep individual and population predictions separate. A user's stated dislike
  of coffee outranks a population tendency to like sweet odors.
- Do not reward naturalness, luxury labels, high ingredient count or duration
  of exposure as automatic chemical pleasantness gains.
- Missing coverage remains uncertainty and cannot be silently dropped from
  the denominator as if it had no relevance to the requested identity.

These findings support further computer-only model development. They do not
require this user to prepare preliminary samples. No safety or IFRA work was
performed as part of this hedonic evidence search.
