# Gin Vétiver Cypress Air — measured optimizer implementation and run

Date: 2026-09-09. **The global-search implementation and measured-model experiments are complete. The full-perfume hedonic optimization is not complete.** No physical premix is required by this workflow, and no formula or inventory was changed.

## What changed

- Added baseline-independent bounded composition generation, multistart refinement, concurrent deterministic evaluation and an equal-budget independent random comparator to `engine/optimizer/gate_aware.py`.
- Preserved the legacy evidence-only mode. The stock-bound runner now fails explicitly when no numerical evaluator exists, instead of interpreting qualitative material roles as a response surface or naming the original formula a winner.
- Added actual fitted numerical models to the existing `scripts/train_odor_predictor.py`. The old default command now honestly reports dataset preparation only; it no longer concatenates incompatible leaderboard rows or treats chemical names as sensory attributes.
- Added a registered, hash-bound partial-mixture model route. Arbitrary caller callbacks cannot bypass its admission. Model JSON, source files and PubChem structure records are checked before use. Unknown stocks remain frozen and explicitly unmodeled.
- Failed searches retain valid observations but publish no recommendation. The partial-mixture experiment also publishes no full-perfume recommendation even when its numerical search completes.

## Human data, not invented hedonic constants

### DREAM single-molecule diagnostic

338 molecules, 676 molecule/dose means and 21 endpoints; five molecule-disjoint folds. Both concentrations of each molecule stay in one fold. Missing responses are excluded, not filled with zeros. The published descriptor derivative has known blank-to-zero transformations, separately flagged.

| Endpoint | Intercept RMSE | Linear dose-only RMSE | Decision |
|---|---:|---:|---|
| Intensity | 25.73584 | 22.90107 | Dose carries information about intensity |
| Pleasantness | 12.62382 | 12.62672 | Do not use a generic dose-only liking law |

Source: DREAM/Keller, DOI `10.1126/science.aal2014`, locally preserved `TrainSet.txt` and license. Receipt: `output/optimizer_research_20260909/dream_dose_benchmark_v1.json`. Absolute dilution is confounded by molecule-specific preparation choices. These numbers are not perfume ratings.

### DREAM 2025 mixture model

393 source mixtures, 392 included, 354 canonical ingredient palettes. One complete mixture is excluded because a component lacks a structure; it is not modeled after silently dropping that component. Five palette-disjoint folds keep ratio variants together. Shared individual molecules can occur across folds: this is not molecule-disjoint validation.

Native RDKit structural features feed fixed-alpha ridge regressions. The dose-aware version additionally uses nominal-fraction-weighted structure means/spreads and concentration features. Scalers are fitted inside each training fold. No measured perception label is an input. Coefficients and scalers are stored as numerical JSON, not executable serialized objects.

| Endpoint | Dose-blind RMSE | Dose-aware RMSE | Held-out same-palette, same-solvent dose ordering |
|---|---:|---:|---:|
| Pleasantness | 0.75035 | 0.73337 | 32/53 correct |
| Intensity | 0.77463 | 0.76604 | 32/54 correct |
| Woody | 0.28466 | 0.28427 | 26/52 correct |
| Pine | 0.18267 | 0.18634 | 24/42 correct; overall RMSE worsens |
| Citrus | 0.37768 | 0.36050 | 33/50 correct |

Pleasantness comparisons come from 12 clustered palette/solvent groups and 40 stimuli, **not 53 independent experiments**. The dose-blind model ties the ratio comparisons; its tie count must not be portrayed as a 0%-accurate directional classifier. Improvements are modest point estimates, not established statistical superiority or personal preference prediction.

Source preparation uses equal volumes of component solutions, confirmed in the official Synapse discussion: https://www.synapse.org/Synapse:syn64743570/discussion/threadId=12185 . Nominal source fraction is stock dilution divided by aliquot count; unknown solution densities prevent exact mass fractions. Solvent/delivery transfer to an ethanol EDP is unvalidated.

Receipt and fitted model: `output/optimizer_research_20260909/dream_mixture_benchmark_v1.json`. This is a newly fitted local baseline, not the challenge authors' model. Local research use does not establish dataset redistribution or commercial rights.

## Actual Gin experiment

The full-model plan returns `FAIL_NUMERICAL_EVALUATOR_UNAVAILABLE`. A separate explicitly partial plan can run a real measured surrogate:

- Five mapped stocks: Iso E Super, Hedione, Benzyl Benzoate, Terpinyl Acetate and the user-inventory CAS-bound Vetikon branch.
- Their combined amount is fixed at **2,080 raw microlitres**. This is **38.52% of the 5,400 raw-microlitre fragrance-stock basket**, not an active-mass, odor or perceptual coverage percentage.
- The other **13 stocks / 3,320 raw microlitres** remain frozen and unmodeled. Freezing them does not make their interactions disappear or validate their starting doses.
- All 18 live stock identity/form checks pass. Carrier-bearing stocks are not rebased. No DEP-containing stock is added.
- Representative connectivity does not resolve supplied isomer distributions. In this branch Vetikon uses PubChem CAS 7403-42-1 / CID 81898. The local legacy “methyl cedryl ketone” structure conflicts with that record; the discrepancy is explicit and the canonical material tables were not silently rewritten.

Four seeded runs each evaluated 128 optimizer proposals and 128 random proposals, plus the baseline: **1,028 evaluations across four runs**. Each retained constant raw stock total and the same fixed stocks.

| Seed | Starting partial-model pleasantness | Best adaptive-search value | Best equal-budget random value |
|---|---:|---:|---:|
| 20260909 | 5.68662 | 6.17087 | 6.13997 |
| 17 | 5.68662 | 6.13430 | 6.15881 |
| 31 | 5.68662 | 6.12813 | 6.17817 |
| 73 | 5.68662 | 6.17688 | 6.17741 |

These are **predictions for the isolated mapped subcomposition**, not measured observations and not whole-perfume ratings. Random search wins three of four comparisons; the adaptive strategy has not demonstrated superiority. The nominal best candidates concentrate approximately 1,855–2,016 raw microlitres into Iso E Super. That is an optimizer/model stress-test result, not evidence of a richer, better-layered gin-vetiver perfume. The weak woody ratio-ranking result and missing whole-mixture interactions cannot support that aesthetic promotion.

Receipts:

- `output/design_portfolios/20260909_192644_517543.json`
- `output/design_portfolios/20260909_192715_448721.json`
- `output/design_portfolios/20260909_192717_568587.json`
- `output/design_portfolios/20260909_192719_487488.json`

Each reports `FINITE_BUDGET_COMPLETE` for the partial search, **`FAIL_TARGET_AND_MIXTURE_COVERAGE` for the full perfume**, `predicted_liking: null`, `experimental_recommendation: null`, and `formula_modified: false`. The original recipe is not declared optimal. The final CLI returns exit code 2 while that full-perfume gate fails; numerical budget completion cannot signal full-workflow success.

### Local-data dependency

This is an installed local research experiment, not a self-contained distributable model package. The downloaded model, PubChem records and raw source data are in gitignored `output/`; the plan binds their exact bytes and refuses missing or changed files. The synthetic model/search unit tests run without these data. Four optional stock-runner integration cases explicitly skip when the local evidence bundle is absent; they passed with the bundle present in this session. A clean checkout must separately obtain the source data and reproduce/review its hashes before using this plan. No dataset redistribution permission is inferred from a code license.

## Verification and remaining work

158 focused tests pass; scoped Ruff passes. The full project audit was run during this turn: 10 checks passed, 9 failed, 2 Docker checks were skipped. Broader failures include legacy inventory/artifact contracts, Python metaclass collection errors and backend source contracts. The full audit is not a clean release certificate for this dirty checkout; final scoped changes were tested separately afterward. A subsequent targeted project check passed engine compilation, lint, typing, both golden regressions and the golden fixture lock (`output/optimizer_research_20260909/final_code_verification.json`). The final CLI receipt is `output/design_portfolios/20260909_193154_484747.json`. The original formula SHA-256 remains `426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`.

The remaining scientific work is specific: build and test a concentration-to-perception representation covering the gin/vetiver/natural and proprietary-material context; distinguish brief-specific character/body/layering from generic pleasantness; and demonstrate candidate-ranking benefit on independent measured mixture conditions. Broader structural inputs and representative natural compositions can be investigated computationally without asking the user to premix. Missing endpoints must not be manufactured to force a completion flag.

Independent native re-review found no remaining P1/P2 issues in this scoped implementation after the binding, recommendation, local-data and exit-status fixes. Its fresh 42-test scoped run passed and its actual partial CLI run returned exit code 2. This is a code-review result, not acceptance of the incomplete whole-perfume predictor.

This result replaces neither the user's requested complete optimizer with a “no change” machine nor uncertain predictions with a claim of proven scent quality. It establishes a real searchable, fitted baseline and exposes exactly where it fails to justify a finished perfume.
