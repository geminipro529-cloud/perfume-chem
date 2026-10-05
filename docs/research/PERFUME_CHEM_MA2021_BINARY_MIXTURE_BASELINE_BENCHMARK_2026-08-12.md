# Ma 2021 Binary-Mixture Baseline Benchmark

Decision: `DATA_AMBER_MA2021_SOURCE_INTERNAL_BASELINES_QUANTIFIED_NONLINEAR_ESCALATION_NOT_AUTHORIZED`

## Scope

This benchmark uses the exact public Ma et al. V2 workbook (DOI
`10.15454/51OVY6`, file PID `doi:10.15454/51OVY6/COAY4H`, SHA-256
`c540f18ba71b778c36756810fff38bdf177c2af9d593567a6dba57a30503c950`).
The 222 source aggregate trials were collapsed to 198 unique binary-mixture
keys by averaging the 24 source-declared repeat pairs. No participant rows were
used and no model was fitted.

## Result

The strongest-component intensity baseline, `max(IA, IB)`, has RMSE
`0.468534976465` for `IAB`. The source repeat-pair `IAB` RMSE is
`0.459045542563` (95% grouped-bootstrap interval `0.338781577707` to
`0.576630813621`). Their ratio is `1.020672096823`; the simple intensity
baseline is already at approximately the source repeat-disagreement scale.

For pleasantness, squared-intensity weighting is best among the three frozen
closed-form candidates: RMSE `0.394525286290` versus `0.418151070790` for
intensity weighting and `0.448986508730` for arithmetic averaging. In a
20,000-draw mixture-key bootstrap, the arithmetic-minus-squared RMSE advantage
is `0.054461222440` (95% interval `0.031269285912` to `0.078107275333`), and
the intensity-weighted-minus-squared advantage is `0.023625784501` (95%
interval `0.012685213376` to `0.034746459299`).

## Literature and novelty boundary

The dataset article is DOI `10.1016/j.dib.2021.107143`. The same source family
already underlies pleasantness and intensity analyses (DOIs
`10.1093/chemse/bjaa020` and `10.1016/j.foodchem.2021.129483`), while the
closed-form pleasantness framework predates this dataset (DOI
`10.1093/chemse/bjn026`). A recent intensity framework is a preprint (DOI
`10.1101/2025.08.08.668954`) and is prior art, not promotion evidence here.

Accordingly, this is a low-cost source-internal calibration and falsification
gate, not a novel mixture law. It does not test odor quality, independent-source
transportability, formula performance, or physical reproducibility.

## Cost gate

A nonlinear same-source residual model is not authorized: it would add
complexity where the intensity baseline error is already approximately the
repeat-disagreement scale, and the pleasantness result reproduces established
same-family/prior-art structure. The next defensible investment is either an
independent-source transportability test or closure of physical stock and label
gates before a preregistered local replication.

All database, participant-level, nonlinear-training, generalization, formula,
physical-experiment, stock, sensory, safety, novelty, publication, and release
authorizations remain false.
