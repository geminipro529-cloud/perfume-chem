# Reopening the perfume optimizer with measured sensory data

Date: 2026-09-09. Target: Gin Vetiver Cypress Air EDP, with body and layering, light cypress, Hedione permitted, no jasmine accord. Computational development must not require a new physical mix.

## Engineering conclusion

The earlier finite no-change search did not satisfy the optimizer request. It called a qualitative evaluator that could not produce numerical dose preferences, searched close to the starting recipe, and imposed several starting doses as design floors. Those properties cannot establish that the initial proportions are good. The starting formula is an unvalidated comparator, not ground truth.

This pass found and downloaded additional human sensory data, implemented an opt-in measured intensity component, and reproduced source calculations. These are working components, not a completed full-perfume optimizer. No new formula or claim of improved smell has been issued.

## Data recovered and inspected

### Concentration-dependent human intensity

[Wakayama et al. (2019)](https://doi.org/10.1021/acs.iecr.9b01225) provide fitted intensity curves and single-material/mixture observations. The publisher's supporting PDF was downloaded with a matching publisher MD5. A commit-pinned Pyrfume transcription supplies 314 parameter rows; 313 have evaluable positive slopes. The printed vanillin slope is zero and was not repaired by guessing. Parameters are intensity, not pleasantness. Source licensing is CC BY-NC 4.0.

The benchmark uses 46 single-component observations and 20 observations from five five-component mixtures at four dilution levels. Raw observations remain distinct from printed model predictions. These source-series checks are not asserted to be held-out from source fitting. [Publisher metadata and download](https://api.figshare.com/v2/articles/9172283).

One source identity issue is already confirmed: PDF page 5 pairs CAS 140-88-5 with 2,6-nonadienal. The transcription repeats it. Do not automatically turn all 313 mathematical curves into verified stock calibrations.

### Independent human ratings

The complete six-file [Bierling 2025 Zenodo release](https://zenodo.org/records/14727277) was downloaded and every publisher MD5 checked. It contains main ratings, intensity piloting, stimulus metadata, a variable dictionary, translated descriptions and an analysis notebook. The notebook was not executed. License: CC BY 4.0.

Read-only inspection found main-table pleasantness, intensity and descriptor columns, plus inclusion flags. The pilot contains 966 rows across 100 CAS identifiers and 100 participant codes, but only two CAS identifiers with multiple concentration strings. Consequently it is not a broad concentration-response training set. Its dictionary defines 1/100 as one odor portion to 100 DPG portions, not 1% of the total. [Associated paper](https://doi.org/10.1038/s41597-025-04644-2).

The workbook skill was used to preserve raw workbooks and inspect the dictionary before interpreting concentrations. It did not change the research files.

## Implemented and executed

Existing module `engine/dose_response.py` now includes explicit gas-ppm to micrograms/litre conversion, stable measured curves, parameter parsing, strongest-component and primacy mixture hypotheses, and the frozen source-observation benchmark. Existing CLI `scripts/train_odor_predictor.py` has an opt-in benchmark mode. Legacy prediction behavior is unchanged. No new pipeline script was created.

Measured curve:

`I(g) = Imax / (1 + exp(-(log10(g) - C) / D))`

Here `g` is gas mass concentration in micrograms/litre air, not liquid dose. The ideal-gas conversion is `g = ppm(v/v) * pressure * molecular_weight / (R * temperature) * 0.001`. Direct application to raw stock microlitres would be wrong.

The [Pellegrino et al. 2025 preprint](https://pmc.ncbi.nlm.nih.gov/articles/PMC12363845/) supplies a different mixture rule: log-sum-exp of component intensity evaluated at 20% concentration. Its transfer to the 2019 curves was compared without fitting. That transfer is not reproduction of the original 2025 model or data. The full primary XML was retrieved through [Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12363845/fullTextXML).

| Test | This implementation | Published reference / interpretation |
|---|---:|---|
| Single-material mean of group RMSE | 6.20487 | Published rounded reference 6.22 |
| Single-material pooled RMSE | 6.37757 | Different weighting from mean-group RMSE |
| Strongest-component mixture mean of group RMSE | 6.70439 | Published rounded reference 6.69 |
| Strongest-component mixture pooled RMSE | 6.86376 | Different weighting from mean-group RMSE |
| Primacy transfer mixture mean of group RMSE | 7.68130 | Worse on these observations than strongest-component |

The maximum discrepancy from printed predictions is approximately 0.170 for single-material curves and 0.096 for strongest-component mixtures. Printed source coefficients are rounded. No parameters were fitted in this run. These errors measure intensity on the source scale, not a perfume hedonic score.

Execution:

```powershell
.venv/Scripts/python.exe scripts/train_odor_predictor.py --intensity-benchmark data/benchmarks/wakayama_2019_validation_v1.json --output output/optimizer_research_20260909/wakayama_benchmark_v1.json
```

The receipt binds parameter, observation and implementation hashes. Source locations, licenses, downloads and caveats are in `data/source_manifests/optimizer_sensory_research_20260909.json`.

## Implications for the actual perfume

Nominal curve matches include Iso E Super, methyl dihydrojasmonate/Hedione, benzyl benzoate and terpinyl acetate. An Ambroxan curve is a potential proxy, not proof of equivalence to this Ambrox Super stock. Natural-material constituents such as pinenes, limonene and linalool have curves, but that does not establish whole-vetiver, whole-juniper or whole-cypress perception. Exact chemical/isomer identity and source preparation must be checked before applying any match.

The practical integration is: stock amount and carrier accounting, constituent gas-concentration estimates with uncertainty, measured dose-response where available, then a separate character/pleasantness representation. Intensity is one modeling input or constraint; maximizing it is not the design objective. Missing whole-material calibration should be exposed without forcing all experimental candidates to tie at an invented hedonic score.

## Required optimizer changes, not yet implemented by this component

1. Replace baseline-relative aesthetic floors with independently justified brief bounds. Keep actual arithmetic and stock constraints. Preserve the user's light-cypress identity without treating today's juniper/vetiver amounts as learned truths.
2. Generate reproducible global candidates and several starting compositions at constant total. Keep the original as one comparator. Freeze carrier-bearing stocks whose active mass conversion is unresolved instead of fabricating a conversion.
3. Add concentration-aware sensory features and a tested quantitative objective for the endpoints actually supported by the data. Separate intensity, target character, predicted pleasantness and temporal/body hypotheses.
4. Evaluate generalization by molecule/mixture groups and external datasets, not random rows that leak the same material into training and test. Preserve preparation differences across studies.
5. Compare optimization against equal-budget random search and against changed starting seeds. A search method that always retains its initial recipe has not demonstrated useful dose optimization.
6. Produce ranked computational candidates with model disagreement and missing coverage. Distinguish a proposed improvement from a sensory-verified improvement; do not substitute OAV, material count or generic priors for liking.

## Verification

Seventeen focused new tests and the existing optimizer suite passed together: 116 tests. Targeted Ruff passed. An independent native reviewer checked units, curve math and mixture aggregation; its reporting/validation findings were incorporated. The code refuses missing active-component calibrations rather than silently dropping them. The formula itself remains unchanged.

The full project verification was also executed fresh. It returned 10 passing checks, 9 failing checks and 2 skipped Docker checks. Broader failures include formula artifacts, engine test groups, backend typing/tests, scientific audit and material data. The package build and wheel smoke check passed; golden outputs remained unchanged. This is not a clean repository release, and the focused passing tests must not be described as one.

All five user-requested GPT-5.6 Luna extra-high research lanes completed: dose-pleasantness data, mixture interactions, modern prediction models, body/layering endpoints and offline search algorithms. Their strongest claims were checked against primary sources and available assets by the parent. The summaries below are engineering adjudication, not automatic admission of every agent proposal.

## Five-agent literature review: parent synthesis

### Dose and pleasantness

The dose-pleasantness lane identified [Moskowitz et al. 1976](https://doi.org/10.3758/BF03204218) and [Doty 1975](https://doi.org/10.3758/BF03203300). The parent verified the publisher abstracts: concentration-intensity relations are better behaved than concentration-pleasantness relations, and individual hedonic variation matters. These justify testing separate dose-sensitive endpoints, not imposing a universal inverted-U or importing arbitrary preferred doses. The 1976 paper has an [erratum](https://doi.org/10.3758/BF03204173), which must be reconciled before extracting its numeric parameters.

The lane also returned the already-known Ma binary-mixture dataset. Its within-mixture component intensity measurements can support an upper-bound/conditional model benchmark, but they are unavailable inputs for a formula-only prediction. Repeating that benchmark without a new concentration-to-component-perception bridge is not the next engineering step. No additional broad repeated-dose pleasantness raw dataset was established in this lane.

### Offline search

Two parent-verified primary sources directly address the algorithmic task:

- [Conservative Objective Models, ICML 2021](https://proceedings.mlr.press/v139/trabucco21a.html): optimize from a fixed labeled dataset while addressing overly optimistic extrapolation. Useful model-training principle, not proof that an arbitrary uncertainty penalty is calibrated.
- [Offline Model-Based Optimization by Learning to Rank, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/768c19273e20fa09147885d03da7550f-Abstract-Conference.html): ranking quality can be more relevant than score MSE to selecting good designs. [Official code](https://github.com/lamda-bbo/Offline-RaM) is available; it has not been installed or executed here.

Engineering choice: test a global, constant-total candidate generator and a small endpoint-specific ranking model before adopting a large optimization framework. Compare held-out selected outcomes against equal-budget random selection and the existing local search. Keep the original formula as a comparator, not the center of all generation.

One agent recommendation needs correction: automatically ending every uncertain run with the original recipe would recreate the user's complaint. Preserve the original executable file while still producing a ranked experimental shortlist wherever models discriminate. Candidate exploration, model-based recommendation and sensory-confirmed improvement are distinct decisions. Unavailable liking remains unavailable, but it must not silently erase supported intensity/descriptor comparisons or make an arbitrary starting recipe the winner.

### Mixture interactions and ratio-sensitive descriptors

[de-la-Fuente-Blanco et al. 2023](https://doi.org/10.20870/oeno-one.2023.57.2.7089) measured woody-fruity interactions across 21 semi-synthetic wine models. The parent retrieved the article and all four supplementary pages. Table A4 contains 14-panelist mean ratings for ten descriptors. The resulting `data/benchmarks/woody_fruity_2023_descriptor_means_v1.json` preserves these 21 response vectors and the printed spreads, whose precise statistical definition is not stated in the table caption. Three no-wood controls printed repeatedly under different wood headings were verified identical and retained once.

This is usable ratio-sensitive descriptor evidence. It is not individual-level data, and experimental level labels are not liquid ppm. The next dataset-specific step is joining exact chemical-composition metadata before fitting a concentration model. The supplement SHA-256 is `6221afaf67f5a70c6597f2c6f9d1b2afc293b916ed6186a2a4961606dcfa56ee`.

[Atanasova et al. 2005](https://pubmed.ncbi.nlm.nih.gov/15741601/) supplies a useful failure case: woody-fruity quality dominance was not fully explained by a model based on relative unmixed intensity, particularly at equal-intensity conditions. Thus intensity-weighted descriptor averaging should be a testable baseline, not a guaranteed blending law. Wine-specific response coefficients will not be assigned to the gin-vetiver formula.

### Modern model assets

Parent inspection confirmed the [AROMMA primary paper](https://arxiv.org/html/2601.19561v1), its one-/two-molecule descriptor task and the public Hugging Face listing of four checkpoints. The weight repository metadata has no license field, so code licensing must not be presumed to cover weights. The published architecture has no concentration input and uses non-stereochemical molecular structures. It is a candidate encoder, not a ready dose optimizer.

The parent also checked the [POMMix paper](https://arxiv.org/html/2501.16271v1) and public [repository asset tree](https://github.com/chemcognition-lab/pom-mix), which contains small mixture-model checkpoints. Its native task is mixture similarity, not liking or dose-dependent character. A concentration-conditioned adapter on a frozen molecular encoder is a feasible experiment. It still needs measured endpoints and a simple baseline comparison. Neither model was installed or its checkpoints executed during this pass.

Engineering priority: test the small-backbone approach only after a low-dimensional concentration-aware baseline. Large catalog-derived blend-label sets can supply weak descriptor pretraining, but they are not controlled human ratio measurements. Do not treat pseudo-labels as new human observations.

### Body, layering and temporal perception

The lane did not establish a downloadable, general-purpose human label set for perfume body/richness/layering. That is a targeted search result, not proof that none exists. Its most relevant sources concern recognizer stability and adaptation, rather than a universal body score.

[Le Berre et al. 2008](https://doi.org/10.1093/chemse/bjn006) found that small component-concentration changes can alter the typicality of a ternary blend. This argues for perturbation tests around candidate ratios. It does **not** justify discarding every change below a single-component JND; the reported result itself includes effects below one JND.

[Frank et al. 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2955077/) supports separating sensory adaptation from physical evaporation: component recognition changes with adapted state. It does not calibrate the current five-window EDP simulator or establish skin longevity. A physical sniffing protocol suggested by the lane is not accepted as a prerequisite for this pre-mixing task.

For now, body/layering should be explicit target-linked computational hypotheses, such as sustained woody-vetiver support without loss of gin identity, descriptor transitions and robustness to small ratio perturbations. No universal scalar richness number was established by this research.

## Practical order after this research pass

1. Use the new measured intensity component and ratio-descriptor benchmark to compare simple concentration-aware baselines against dose-blind ones. Join preparation and exact chemical metadata before fitting.
2. Test a small frozen-encoder adapter only if it beats those baselines on grouped held-out data. Keep conditional models requiring measured within-mixture component intensity distinct from deployable formula-only models.
3. Implement global candidate generation independent of today's ratios, with separate model objectives and an experimental shortlist even when sensory confirmation remains unavailable.
4. Test ranking quality and selected outcomes against equal-budget random search, multiple starting compositions and parameter uncertainty. A higher self-generated score is not the validation criterion.

These steps require computation and existing published data, not a new physical mix. This pass completed research collection and a measured intensity component; it did not finish the full optimizer or choose new perfume proportions.
