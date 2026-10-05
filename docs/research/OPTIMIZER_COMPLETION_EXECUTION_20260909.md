# Optimizer completion execution — 2026-09-09

## Binding requirement

Develop the pre-mixing optimizer for Gin Vétiver Cypress Air EDP. Explore proportions independently of the arbitrary starting recipe; do not require a physical mixture before computational work finishes. Preserve the named gin/vetiver identity and light cypress. Do not manufacture liking from OAV, ingredient count, material-role prose or a generic pleasantness prior.

## Current defects verified in code

1. `run_design_portfolio` always calls a qualitative-only evaluator. Its output has no numerical response surface, so the existing search cannot rank doses.
2. The existing search explores only transfers around its incumbent and stops at its first non-advancing neighbourhood.
3. The legacy DREAM training command fits no estimator and incorrectly combines incompatible training and leaderboard schemas.

## Implementation tasks

1. Add an opt-in global search in the existing optimizer module. Preserve old evidence-only behavior. Use baseline-independent bounded constant-total proposals, multistart refinement, deterministic concurrent evaluation, an equal-budget random comparator, and explicit finite-budget/exhaustion statuses. Never describe finite-budget completion as a global optimum.
2. Implement an actual measured DREAM dose diagnostic in the existing training CLI. Keep molecule identity groups intact across held-out folds, preserve dilution, separate each measured endpoint, retain missing responses, serialize fitted coefficients and source hashes, and compare dose-aware models against an intercept baseline. Do not use uncleared Dragon features or pretend a dose-only curve predicts full perfumes.
3. Connect the existing stock-bound formula CLI to global search with an explicit evaluator declaration. Reject missing numerical evidence rather than silently reusing the qualitative evaluator or legacy invented valences. Retain evaluated alternatives and distinguish search execution from endpoint-model admission.
4. Run the new route on the current Gin formula and inspect its actual result. Preserve source formula and inventory. Report any unsupported inference as a specific failure, not an unchanged-baseline victory or a successful hedonic optimization.
5. Review the code and execute focused regressions, followed by a fresh full project verification. Keep unrelated checkout failures separate from these changes.

## Decisions and boundaries

- Ruling: work in the existing dirty checkout without a new worktree or new pipeline script, as explicitly requested. Only scoped files are edited; unrelated work is preserved.
- Ruling: native workers own disjoint search and data-loader files; the parent owns integration and scientific acceptance. No non-OpenAI delegation.
- Ruling: an experimental numerical objective must be explicit and auditable. A missing full-formula model cannot be replaced by hand-selected target ratios and then advertised as research-backed hedonic optimization.
- Ruling: carrier-bearing stocks remain fixed where their raw-volume to active-mass conversion is unresolved. A wider computational domain does not create compounding authority.

## Acceptance distinctions

Search implementation, measured-data benchmark, and full-formula hedonic inference are separate deliverables. The first two can finish without sensory feedback. The third requires a usable formula-input-to-endpoint model; merely loading a dataset, passing software tests, or consuming a search budget does not supply one. This document does not redefine the user's requested full optimizer as already complete.

## Execution ledger

- Tasks 1–3 implemented and exercised: global search, actual DREAM2017 dose regressions, actual DREAM2025 structure-plus-concentration mixture regressions, and the registered hash-bound stock-runner integration.
- Task 4 executed four seeded partial-mixture experiments (128 adaptive +128 random +1 baseline each). Source-domain prediction varies with dose; random search wins three of four comparisons. No full-perfume formula is promoted.
- Ruling: add a separately labeled five-material partial-support experiment, not an imputed whole-perfume model. This lets measured evidence influence an actual numerical search while keeping the 13 unmodeled stocks fixed. Cost if misread: a partial-mixture rating would falsely imply full-perfume quality; the runner therefore suppresses full recommendations and returns a failing full-perfume gate.
- Review fixes: reject arbitrary caller callbacks even with matching version strings; bind actual model and source bytes; suppress recommendations on partial evaluator failure; keep optional downloaded-evidence integration tests explicitly conditional; return failure exit status while full-perfume coverage fails.
- Ruling: retain downloaded data in the existing local `output/` evidence bundle rather than redistribute it as source code. Cost: the optional integration path requires that local bundle and is not a portable model package. Synthetic unit tests remain independent of it.
- Task 5: 158 scoped tests passed and scoped Ruff passed. Full project audit remains failing in nine broader checks; a later targeted code/golden verification passed. See `GIN_VETIVER_MEASURED_OPTIMIZER_RESULT_20260909.md` for measurements and receipt paths.
- Unfinished requirement: an evidence-supported numerical objective covering the whole gin-vetiver-cypress perfume's character, body, layering and liking. This is not certified by the completed software work and is not replaced by a physical-premix prerequisite.
