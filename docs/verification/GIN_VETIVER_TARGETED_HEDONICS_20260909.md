# Targeted hedonic evaluation: Gin Vetiver Cypress EDP

Date: 2026-09-09. No formula or inventory changes. Computer-only evaluation.

Source record: `formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json`.
SHA256: `426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`.

## Implemented boundary

The existing `engine/hedonic_model.py` now exposes
`evaluate_targeted_hedonics` and `targeted_hedonic_losses`. Legacy
`score_hedonic` callers and their scores remain unchanged; the new path does
not consult that legacy table. This is an API implementation, not a CLI-wide
replacement or a trained full-perfume preference model.

Three separate outputs:

- Target identity: explicit composition constraints. Perceptual fit remains
  NOT_ESTABLISHED even when the constraints pass.
- Predicted liking: optional experimental intensity-weighted binary estimate
  using sourced, context- and concentration-matched observations. No match
  means no score. More than two active stimuli is outside this estimator's
  admitted scope; the 2026 descriptor model is not implemented here.
- Confidence: count coverage and mismatch reasons, separate from validation.
  Coverage is not a probability of being correct.

An explicit allow_experimental option permits binary-model hypothesis search;
it never fills missing inputs or converts them into zero loss. No physical
trial requirement is introduced.

## Actual formula retest

Required anchors: juniper, natural Indian vetiver, cypress, grapefruit FCF.
For this diagnostic, cypress/juniper raw-volume ratio may not exceed the
baseline 50/750. This is a conservative baseline-preservation constraint,
NOT a published perceptual threshold or proof that this ratio is optimal.

| Case | Design-constraint result | Liking estimate |
|---|---|---|
| Current 18-stock EDP | PASS_DESIGN_CONSTRAINTS | Unavailable |
| Remove juniper; transfer 750 uL to Iso E Super | FAIL_DESIGN_CONSTRAINTS | Unavailable |
| Remove natural vetiver; transfer 700 uL to Iso E Super | FAIL_DESIGN_CONSTRAINTS | Unavailable |
| Cypress 50 to 500 uL; juniper 750 to 300 uL | FAIL_DESIGN_CONSTRAINTS | Unavailable |

No matched component intensity/pleasantness observation set was supplied from
the research packet for these exact stocks and conditions: baseline coverage
is 0/18. This does NOT claim no literature exists for these materials.
The packet's complete-perfume ratings are not ratings of this formula.

The controller invocation evaluated the baseline once, returned
EVALUATION_UNAVAILABLE, and preserved all amounts. It did not perform a
candidate tournament after that stop. There is no new hedonic winner.

## Verification

54 focused tests passed under `.venv/Scripts/python.exe`, including 19 new
targeted-evidence tests. The environment emits pytest-asyncio deprecation
warnings. Focused Ruff passed after import formatting. Full repository,
packaging, release pipeline and physical evaluations were not run.

## Remaining scientific work

The new contract prevents known misleading outputs, but does not supply the
missing predictive model. A usable full-perfume optimizer still needs a
mixture-quality model and an evidence-bound liking estimator with relevant
data and out-of-sample discrimination checks. Existing human data may be
used for that work; this user is not required to mix preliminary samples.
