# Gin Vetiver Cypress Air EDP: bounded optimizer closure

> **Reopened, 2026-09-09:** The user correctly rejected this bounded no-change pass as completion of the requested optimizer. Retaining v4 below is a historical search outcome, not a recommendation established by comparative sensory evidence. New measured-data research and implementation are recorded in `docs/research/OPTIMIZER_MEASURED_DATA_REOPENING_20260909.md`. The original receipt remains intact.

Date: 2026-09-09. Parent engineer acceptance of the current computer-only search.

## Outcome

**NO_SUPPORTED_CHANGE. Retain the existing v4 EDP formula.** The finite evidence-adjudication and candidate-search pass is complete. A validated full-perfume hedonic optimizer is **not** achieved. These are separate conclusions; completion of this pass is not proof of optimality, improved smell, richness, layering, or skin-use clearance.

Formula: `formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json`.

Final receipt: `output/design_portfolios/20260909_183043_783069.json`.

Receipt SHA-256: `a9f16e723b1459252c363fc82be391318bff8ec1d37b202054699b917d71d9d8`.

Unchanged formula SHA-256: `426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`.

## Finish-line tasks and evidence

| Task | Final disposition |
|---|---|
| Freeze formula, target, carrier-bearing stocks and search bounds | DONE: hash-bound plan; no formulation edits |
| Bind actual inventory authority, not only inventory.txt | DONE: workbook, snapshot and overlay digests checked against one materialization used for all 18 stock validations |
| Decide every proposed evaluator's admission | DONE: nine explicit, source-hashed decisions; no pending reviews |
| Resolve DREAM preparation question | DONE: official equal-volume component-stock preparation confirmed; exact active mass fractions and delivery conditions remain unavailable |
| Account for every generated proposal | DONE: complete 156-event ledger, including rejection reasons and archive links |
| Separate finished no-change from failures and unfinished work | DONE: explicit final decision contract; evaluator errors, budget exhaustion, pending reviews and inconsistent/pending ledger cannot close as success |
| Independent code review | Inventory authority, pending ledger and contradictory budget-summary findings fixed with failing-then-passing regression tests |
| Verify affected behavior | DONE: 99 focused tests passed; targeted Ruff passed |
| Run on the actual formula | DONE: receipt above; baseline retained |

## Evaluator decisions

The full review is `data/design_briefs/gin_vetiver_edp_evaluator_review_v1.json`. Evidence hashes are verified before the final decision is produced.

| Method | Admission to this run | Reason |
|---|---|---|
| Source-backed material roles | Qualitative only | Explains proposed functional changes, not preferred dose or predicted liking |
| Raw group retention | Excluded | Within-group transfers leave its scored sums unchanged |
| Generic hedonic prior | Excluded | No validated mixture-level liking or target-fit mapping |
| DREAM Task 2 identity graph model | Excluded | Omits dose and drops intensity/pleasantness; cannot rank same-palette transfers |
| Simple Task 1 concentration translation | Excluded | Frozen holdout RMSE worse than unchanged-profile baseline; wrong input/domain for this perfume |
| Author Task 1 model | Excluded | Requires measured source odor profiles absent for these exact natural-mixture stocks |
| DREAM raw concentration groups | Excluded from numeric selection | Equal-volume preparation known, but no validated transport to this EDP or its richness/layering endpoints |
| Ma 2021 binary-mixture model | Excluded | Requires measured component perceptions; not a validated 18-stock concentration-to-perception model |
| OAV as a hedonic score | Excluded | Threshold/headspace screening is not liking, richness, layering or perceived contribution |

Downloaded research remains available. Exclusion is scoped to numerical selection in this version, not a claim that the datasets are worthless. See `docs/research/DREAM_2025_PROTOCOL_CLOSURE_20260909.md` for the resolved primary-source detail.

## Actual search accounting

- 52 directed transfers at three proposed sizes: 50, 25 and 10 microlitres.
- 156 attempted proposal events in the visited baseline neighborhood.
- 67 excluded by declared stock/design bounds.
- 18 excluded by composition constraints.
- 71 unique feasible alternatives evaluated, plus the baseline = 72 archived candidates.
- Zero pending proposals; zero evaluator errors; zero pending evaluator reviews.
- All 18 exact formula stocks resolved against the current materialized inventory.
- No numerical liking estimate or supported dose winner.
- Neighborhood exhausted; configured candidate budget was not the stopping cause.

For example, Hedione-to-Clearwood at 50 microlitres is explicitly rejected because the resulting Clearwood dose exceeds the declared 240-microlitre bound. The 25- and 10-microlitre alternatives remain evaluated but unranked. The bound is a declared design constraint, not a measured sensory threshold.

## Recursion and stopping

The existing controller can recurse when an admitted quantitative evaluator supplies a robust improvement across protected criteria/scenarios. Its tests exercise that behavior with hand-checkable objectives. Those tests do not validate perfume perception.

For this formula, only qualitative role evidence survived admission. Therefore no numerical improvement authorizes advancing to a new parent. Recursing repeatedly on unchanged qualitative information would not resolve the dose comparison. This pass stops at **EVIDENCE_BOUNDARY**, with final decision **NO_SUPPORTED_CHANGE** and `bounded_run_complete=true`.

Do not automatically repeat research or searches on the same inputs. Reopen only for a changed brief, stocks or candidate domain, or genuinely new applicable validated evidence. No preliminary physical mix is required by this workflow. No claim is made that the retained formula is the best possible formula or that a validated full-perfume predictor has been completed.

## Verification and remaining project boundary

Final focused command:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_evidence_design_portfolio.py tests/test_concurrent_hedonic_design.py tests/test_hedonic_design_loop.py tests/test_gate_aware_optimizer.py tests/test_targeted_hedonic_evidence.py -q
```

Result: **99 passed**, with existing pytest-asyncio Python 3.14 deprecation warnings. Targeted Ruff passed for the modified Python files.

The full project audit in this turn reported **10 PASS / 9 FAIL / 2 SKIP**; see `verification_runs/project_verification.json`. That audit began before the final inventory-binding and ledger-consistency patches; those patches were subsequently covered by the focused tests and final formula execution. It is not evidence of a clean final project release.

Failed project areas: formula-artifact validation, truth-core test collection (protobuf runtime incompatibility), data/knowledge tests, gates/family tests, legacy census, backend typing/tests (including missing source contracts), scientific audit and material-data validation. No unrelated inventory values, thresholds, backend contracts or tests were changed to force these checks green. No merge or release was performed.

This is the qualitative design-portfolio CLI branch, not a release/headspace pipeline run. It produces no new OAV table, ppm claim, temporal sensory prediction, mixing card or skin-safety authorization. The formula's nominal 18% fragrance-stock volume loading is not asserted to be an exact active w/w concentration.

## Reproduce

```powershell
.venv/Scripts/python.exe scripts/verify_formula_workflow.py --formula-file formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json --design-plan data/design_briefs/gin_vetiver_edp_evidence_v1.json --evaluator-review data/design_briefs/gin_vetiver_edp_evaluator_review_v1.json
```

Current result is a retained baseline, not a newly optimized dosing card. The literature-first and verification workflow governed evaluator admission and required explicit incomplete/error outcomes instead of promoting an unsupported score.
