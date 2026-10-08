# Next source-bound wave: chypre, cologne, iris and musk bridges

Date: 2026-10-07. Status: reviewed implementation design, **not activated**.
Parent Codex reviewed current local cards and fresh primary pages. A native
read-only census supplied candidates; its conclusions were checked against
the local cards and supplier/publication sources. No DeepSeek or external
language-model route was available or used. No formula, inventory, empirical
capability, purchase or physical-compounding authority changes follow.

## Why this wave

The current library has 179 subtype cards and 44 executable mappings. The next
useful increment should extend dry floral, green and fresh-woody structures,
not inflate coverage by relabeling every wood or flower as interchangeable.
Market-reference descriptions remain structural examples, never liking labels.

### Fresh primary review

1. [Givaudan's perfumer account of chypres](https://patchouli.givaudan.com/staticweb/patchouli/)
   describes contrasting citrus and dry moss/resin/wood structures, followed by
   green and floral developments. It also discusses patchouli-associated modern
   interpretations. This supports separate bridge experiments, not a universal
   recipe or the claim that every patchouli/floral fragrance is a chypre.
   Its proprietary consumer descriptions are not an admitted liking dataset.
2. [IFF Rose Essential Low ME For Life](https://www.iff.com/scent/lmr-compendium/rose-essential-low-me-for-life/)
   is a specific Turkish Rosa damascena product with petal, powder-associated
   and green descriptors. It is obtained through a particular sequence of
   physical processing steps. Do not treat it as Rose de Mai absolute, rose
   otto, or a calibrated substitute for an owned stock.
3. [IFF Egyptian grandiflorum absolute](https://www.iff.com/scent/lmr-compendium/jasmin-absolute-egypt/)
   supplies floral/fruity, indolic, spicy and green/hay descriptors. The exact
   species, flowers and extraction are stated. A jasmine bridge must not
   silently become sambac, an unrequested white-floral bouquet or an indole dose.
4. [IFF Tunisian petitgrain bigarade](https://www.iff.com/scent/lmr-compendium/petitgrain-bigarade-oil-tunisia/)
   is a distilled leaf/twig product with bitter-green, orange-flower and citrus
   aspects. It motivates a citrus-to-heart link distinct from fruit-peel oil.
   It does not bind the user's Paraguayan product to the Tunisian grade.
5. [IFF Egyptian violet-leaf absolute](https://www.iff.com/scent/lmr-compendium/violet-leaf-absolute-egypt/)
   has leafy/watery-floral and moss/leather-associated descriptors. This is
   leaf extract, not violet petals or an ionone reconstruction. The proposed
   watery-leaf comparison must retain cucumber/vegetal drift as a question.
6. [Miyazawa et al., galbanum oil](https://pubs.acs.org/doi/10.1021/jf803157j),
   DOI 10.1021/jf803157j, used odor-directed multidimensional analysis and
   synthesis to identify two unsaturated ketones. Its abstract distinguishes
   abundant monoterpenes from important trace odorants. This supports rejecting
   GC abundance as a sensory-importance ranking. It does not supply a perfume
   dosage rule, an exact resinoid composition, or a universal green accord.
7. [IFF Italian FCR bergamot](https://www.iff.com/scent/lmr-compendium/bergamot-oil-cp-italy-org-fcr-csm/)
   distinguishes fruit peel, extraction/processing and floral/herbal citrus
   facets. An FCR label on this page is not evidence for every supplier bottle,
   nor a safety clearance for a finished fragrance.
8. [IFF Iso E Super](https://www.iff.com/scent/ingredients-compendium/iso-e-super/)
   has a smooth woody/amber description and a stated trade-product identity.
   It supports a restrained woody connector, not an exact cedar oil substitute.
   Supplier substantivity and use guidance are not measured skin persistence
   or a universal finished-perfume dose ceiling.
9. [IFF Meth Ionone Gamma Coeur](https://www.iff.com/scent/ingredients-compendium/meth-ionone-gamma-coeur/)
   combines woody, tobacco, orris/violet and powder-associated descriptions.
   This supports testing an identified texture socket. The page's CAS does not
   erase grade differences or establish equivalence to AIMI or whole orris.

Review scope: supplier description/identity sections and the galbanum paper's
public abstract/metadata. The DOI-specific ACS/PubMed correction/retraction
search returned the original paper and citations, not a notice. This is a
bounded check, not certification that no notice exists anywhere. Full paid
text was not acquired. No publisher text is redistributed, no license to train
or reproduce full databases is inferred, and no source record is promoted.

Existing Clearwood and Exaltolide records remain additional bounded sources;
their official product URLs resolved during this review. No new quantitative
or full-text claim is made from those page opens alone.

## First implementation tranche

| Card | Comparison operation | Protected target | Explicit rejection cases |
|---|---|---|---|
| CHYPRE_FLORAL | Separate restrained rose-associated and jasmine-associated bridge options | Citrus/dry contrast and any explicitly named flower | No floral softness; no rose; no jasmine; no replacement by a bouquet |
| CHYPRE_GREEN | Bitter-green contour versus watery-leaf contour | Same citrus/dry structure; requested green identity | No green; no galbanum; no watery/cucumber drift; no exact oil/resinoid swap claim |
| COLOGNE_WOOD | One leaf/floral bridge versus unchanged direct citrus-to-wood control | Citrus recognizer and restrained wood | No citrus/cologne; no green/floral bridge; no extra wood that erases peel |

Implementation requirements:

- Add a v4 successor, preserving ordered v1-v3 mappings and raw-byte pins.
- Use only existing numerical role templates for these broad alternatives.
  Literature supplies the question and qualitative constraints, not shares.
- Preserve the unchanged control; allow at most two unordered alternatives.
  COLOGNE_WOOD needs only one new option, not a padded second recipe.
- Bind source cards, review receipts, template bytes, implementation and inventory.
- Suppress physically duplicate alternatives without forcing arbitrary doses.
- Add positive, paraphrase, combined-facet and negation cases before execution.
  A diagnostic title must not reactivate an explicitly excluded facet.
- Require verified role/stock assignments, allocation, critique and authority
  receipts. A returned formula alone does not prove the comparison was executed.
- Inspect the selected material's own odor evidence for the proposed modifier.
  Current generic term ranking also sees context and synergy text; that alone
  cannot establish a bitter-resin, watery-leaf, rose or jasmine intervention.
  If the existing role representation cannot enforce a meaningful distinction,
  withhold that mapping or implement a separately reviewed eligibility contract
  first. A renamed role or a higher freshness score is not the missing facet.
- Reuse no historical passing corpus as a test of new source or inventory.
- Do not label architecture differences as sensory improvement or market appeal.

The adapter and diagnostic successor must remain inactive until current v3
acceptance is settled, then pass a separately frozen expanded comparison.

## Representation work required for later tranches

| Candidate | Needed before executable admission |
|---|---|
| MUSK_POWDER | Bind an ionone-associated texture role rather than an arbitrary generic powder material; keep a single-musk control |
| LAV_IRIS | Preserve requested root/cosmetic/transparent/woody iris profile and exact grade where named; Orris Liquid stays held |
| HY_TEA_MUSK | Exact soft-musk versus fruit-associated-musk role binding; preserve tea type and food-to-perfume uncertainty |
| FOUGERE_LEATHER | Non-smoky suede and non-smoky resin templates; existing smoke-weighted templates are not faithful substitutes |
| WOOD_MINERAL | Preserve the bound addendum: mineral descriptors cannot automatically be assigned to Ambrox or metallic descriptors to Habanolide |
| WOOD_SANDAL_CEDAR | Distinguish broad textural options from actual sandalwood species, cedar species and named synthetics |
| FLORAL_AMBER_WHITE | Neutral resin support without automatically increasing smoke; retain the requested single flower |
| BOUQUET_CLASSICAL / NARCISSUS_ABS / CHYPRE_LEATHER | Real omission operations; an appended role is not an omission experiment |

Keep the prior deferrals for ylang fractions, tiare/frangipani species, rosemary
chemotypes, vetiver heart grades, ambergris stereochemistry and creamy magnolia.
The exact CHIMIE L'HOMME campaign remains unavailable; nearby perfume references
cannot supply its missing brief or accepted formula.

## Frozen local basis for this review

```
subtype_research_v4.json
14eef313a501262a63c839577d3b9cf48124441c1dbc1a03a2fcda1f17225c83
architecture_adapters_v3.json
70ec8bd60abefa7d5e09556fece34067caecacba539e6db1fcdea5d7d2f0111c
literature_v1.json
94659e7167cd23dbc7df6e7b4ee527ef3f792ab2940c653beacaa671ea55db39
source_reviews_v1.json
50627e5999064128792f67be198e395af5376ec7b8b08e8e7ac8c82d5fe19453
```

All proposed comparisons remain untested. Action-authority flags stay false.
