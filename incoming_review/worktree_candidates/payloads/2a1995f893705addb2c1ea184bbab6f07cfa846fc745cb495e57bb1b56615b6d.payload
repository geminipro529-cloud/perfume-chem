# Gin Vetiver evidence-portfolio implementation and run

Date: 2026-09-09. Engineering outcome: operational bounded portfolio search and
existing-CLI integration. Scientific outcome: EVIDENCE_BOUNDARY, no dose winner.

## Implemented

- `engine/optimizer/gate_aware.py`: `optimize_evidence_portfolio`; independent
  enumeration even at zero baseline loss, bounded archive, parallel evaluations,
  interval dominance, retained alternatives, recursive robust advancement,
  explicit budget/plateau/uncertainty/coverage stops. Existing exact-loss APIs
  remain available and are not silently redefined.
- `engine/hedonic_model.py`: `evaluate_design_roles`; exact changed stocks,
  sourced material roles, explicit missing-profile diagnostics, no fabricated
  mixture strength, richness, layering or liking.
- `scripts/verify_formula_workflow.py`: `--design-plan` JSON-record branch,
  source hashes, exact current stock binding and frozen carrier-bearing stocks.
- `data/design_briefs/gin_vetiver_edp_evidence_v1.json`: source-linked plan with
  manufacturer descriptions separated from original baseline design intentions.
- Family skeleton repair requests now identify `BRIEF_FIT` rather than falsely
  calling missing architecture an unknown/forbidden-material problem. A legacy
  test had assumed a missing fougere skeleton could not trigger a rerun. The test
  now preserves advisory-only non-trigger behavior while checking that the actual
  hard architecture failure requests a brief-grammar repair. No gate was demoted.

## Verification

Red/green observed for new search, role adapter, CLI integration, identical
uncertain intervals, preserved missing-data diagnostics, and architecture-action
classification. Independent read-only review identified the uncertainty and
diagnostic issues; parent reproduced and fixed them.

Focused suite: **76 passed**:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_evidence_design_portfolio.py tests/test_concurrent_hedonic_design.py tests/test_hedonic_design_loop.py tests/test_targeted_hedonic_evidence.py tests/test_gate_aware_optimizer.py -q --tb=short
```

Includes 20 evidence-portfolio cases; old targeted/concurrent/scalar/repair tests
also run. Third-party pytest-asyncio deprecation warnings remain under Python3.14.
Scoped Ruff passed after the architecture repair; final source-hash addition
is checked again at handoff. Build frontend: `build 1.5.0` available.
Full project audit: **10 PASS, 9 FAIL, 2 SKIPPED**, completion gate FAIL.
Report: `verification_runs/project_verification.json`. The audit started before
the last small action-classification/receipt changes; the final focused run
covers those changes. Package build and wheel smoke passed during that audit.
No clean repository release is claimed.

Failing checks: formula-artifact-validation, engine-tests-truth-core,
engine-tests-data-knowledge, engine-tests-gates-families, engine-tests-legacy,
backend-typecheck, backend-tests, scientific-audit, material-data-validation.
Observed causes include Python metaclass dependency collection errors, missing
backend SourceUseRequest/contracts, stale formula/inventory artifacts, runtime
stock-data assertions, and OAV audit coverage84.959 versus an85 threshold. These
were not repaired by weakening gates or expanding this change into a repository
reconciliation. Current golden fixture lock remains unchanged.

## Real formula run

```powershell
.venv/Scripts/python.exe scripts/verify_formula_workflow.py --formula-file formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json --design-plan data/design_briefs/gin_vetiver_edp_evidence_v1.json
```

Final receipt: `output/design_portfolios/20260909_175311_045775.json`.
It includes SHA256 hashes of the executing optimizer, role adapter and CLI,
in addition to the formula, inventory and plan hashes. The earlier receipt
`output/design_portfolios/20260909_174757_080399.json` is preserved as history.
Formula SHA256 remains
`426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`.

- 18/18 exact current fragrance stocks match.
- 72 archived compositions: baseline plus 71 feasible proposals.
- The earlier 56 tied candidates are present; removing the unsupported raw-group
  retention objectives admits 15 further candidates. Admission is not a benefit.
- Hypothesis groups: Hedione -> Iso E Super, steps50/25/10; Iso E Super -> Vetikon,
  steps50/25/10; Hedione -> Clearwood, steps25/10. All steps explicitly unranked.
- No numerical endpoint available from this qualitative plan; numeric frontier
  empty, predicted liking null. Baseline stays unchanged, not promoted as a winner.
- No release pipeline, skin-safety certification, new DEP carrier, automatic
  bottle edit, preliminary physical-mixing requirement, or new worktree.

## Remaining evidence boundary

This is not completion of a calibrated full-perfume hedonic model. The sources
support different design functions but do not supply concentration-conditioned,
matrix-matched human response curves and uncertainty estimates for these exact
18-stock mixtures. Supplier-role text cannot fill those numerical fields. The
software can optimize supplied applicable interval predictions, as tested on
hand-checkable fixtures, but the actual perfume plan intentionally cannot claim
a measured or calibrated richness, layering or liking improvement.

Further model admission requires real held-out evidence and exact endpoint
coverage, not relaxation of thresholds or substitution of a generic score.
It does not require the user to mix a preliminary trial. See the research report
`docs/research/GIN_VETIVER_RICHNESS_LAYERING_EVIDENCE_20260909.md`.
