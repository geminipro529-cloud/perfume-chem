# Gin Vetiver Cypress EDP: computer-only search attempt

Date: 2026-09-09. Decision: NO_FORMULA_CHANGE; generic evaluator rejected
for target-specific selection. No physical trial requested.

## Source and method

- Source: `formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json`
- SHA256: `426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`
- 18 fragrance stocks, total 5400 uL; ethanol excluded from scoring.
- Existing scorer: `engine.hedonic_model.score_hedonic`.
- Existing controller: `engine.optimizer.gate_aware.optimize_hedonic_design`.
- Loss: 100 minus generic hedonic score. Diagnostic only, not admitted as
  gin-vetiver target fit or sensory preference.
- Stock fractions passed exactly as recorded. Multiplication of raw volume
  by a mass fraction is only the old scorer's nominal screening convention,
  not exact active mass accounting.
- Search varied only four neat stocks: juniper, natural Indian vetiver,
  Iso E Super and Hedione. Bounds were baseline +/-20%, chosen as exploratory
  search limits, not scientifically established perceptual optima.
- Every directed transfer among those four stocks was enabled. Other stocks,
  including both diluted stocks, FCF grapefruit and cypress, stayed fixed.
  Each transfer retained the 5400 uL raw total and existing declared carrier
  additions. No new ingredient or deliberately introduced DEP was added.
- These were nominal evaluator runs, not temperature/evaporation robustness
  tests. This scorer has no scenario inputs for those effects. Repeating the
  same model under different labels would not constitute robustness evidence.

## Evaluator discrimination challenge

All challenges preserved raw total; they are diagnostic counterexamples,
not proposed formulas.

| Case | Change from baseline (uL) | Generic score |
|---|---|---:|
| Baseline | None | 80.5 |
| Remove juniper | Juniper -750, Iso E +750 | 80.5 |
| Remove natural vetiver | Natural vetiver -700, Iso E +700 | 81.0 |
| Heavy cypress | Juniper -450, cypress +450 (50 to 500) | 80.5 |
| More abstract support | Natural vetiver -350, Hedione +350 | 81.5 |

The scorer performs exact-name lookups and silently excludes unrated rows
from its rated-weight mean. Eight supplied formula names are absent:
Cedarwood Virginia, Cypress EO, Vetikon, Ambrettolide, Juniper Berry EO,
Coriander Seed EO, Grapefruit FCF oil Sicilian, Petitgrain EO Paraguay.
Some absences may be alias gaps; fixing aliases alone cannot make a generic
pleasantness mean measure this perfume's identity. The score is rounded to
one decimal before returning to the optimizer.

## Search results

| Step schedule (uL) | Evaluated candidates | Rounds | Stop | Score |
|---|---:|---:|---|---:|
| 25, 10, 5 | 37 | 3 | PLATEAU | 80.5 |
| 100, 50, 25, 10, 5 | 71 | 9 | PLATEAU | 80.8 |

The coarse-to-fine run accepted two numerical moves: natural vetiver -100
to Hedione, then natural vetiver -25 to Iso E Super. Its proposed endpoint
was natural vetiver 575, Hedione 700 and Iso E Super 875 uL, with all other
stocks unchanged. This endpoint is REJECTED FOR PROMOTION: the score increase
does not establish better gin-vetiver identity, layering or preference.

An earlier six-transfer probe evaluated 19 candidates and also plateaued
unchanged at 80.5. The table above uses the complete twelve-transfer search.

## Conclusion

The controller executes on the actual formula, but the available generic
evaluator fails the identity challenge. The baseline remains the selected
saved composition. No mixing card, formula record, inventory, authority pin
or bottle was altered. No release pipeline was run in this diagnostic.

Next needed: a target-specific evaluator with disclosed computational
proxies and discrimination checks for gin identity, vetiver body, cypress
prominence, citrus continuity and support dominance. Do not fix this outcome
by relaxing thresholds, inventing subjective ratings, or calling 80.8 a
better perfume. No prerequisite physical mix is required for that engineering.
