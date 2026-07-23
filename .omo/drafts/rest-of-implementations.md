---
slug: rest-of-implementations
status: approved
intent: clear — "plan the rest of the implementations" = plan all unfinished drafts as ONE decision-complete plan
review_required: false
pending-action: AFTER user fixes .opencode/oh-my-openagent.json + restarts OpenCode, write .omo/plans/rest-of-implementations.md covering all 6 unfinished drafts as parallel tracks
approach: Unified 6-track plan. Track A=cassis-iris-smoke (approved, ready), B=aventus-chypre-fruity (approved, ready), C=perfumery-ai-engine (approved, 11 todos/6 waves), D=final-audit-polish-v1 (approved, review_required=true, 4 waves), E=phase-1a-domain-foundation (awaiting-approval -> plan fully inside), F=pipeline-improvement (awaiting-approval -> plan fully inside).
---

# Draft: rest-of-implementations

## Blocker (must clear before planning)
`.opencode/oh-my-openagent.json` references `deepinfra/deepseek-v4-flash` and `deepinfra/deepseek-v4-pro` (~20 slots, lines 38-101). DeepInfra rejects these. Correct IDs: `deepseek-ai/DeepSeek-V4-Flash` and `deepseek-ai/DeepSeek-V4-Pro`. Without this fix, every `task(subagent_type=...)` call fails with `ProviderModelNotFoundError` — planning cannot be delegated, so it's slow and expensive (the user's stated concern).

User authorized fix ("2 FIRST"). Prometheus plan-mode guard blocks editing outside `.omo/*.md`, so the user runs the one-shot PowerShell replace-all themselves, then restarts OpenCode.

## Scope decision (user chose)
Fork 1a (recommended): ALL 6 unfinished drafts, unified into one execution plan. Approved drafts = ready tracks; awaiting-approval drafts = fully planned inside.

## Track ledger
| id | draft | status | what |
|---|---|---|---|
| A | cassis-iris-smoke | approved, clear | Write formulas/Cassis_Iris_Smoke_30mL_EdP.md (verbatim from draft) + gate with --brief generic. Prereq: Cade Oil Rectified 1% added to inventory system (4 locations) OR substitute. 44 materials, 6000 µL, 20% EdP. |
| B | aventus-chypre-fruity | approved, clear | 5 tasks / 3 waves. Adapt Pineapple_Chypre_Luxe → 30mL EdP 20%, ~47 materials. Sub Hydroxycitronellal→Mayol+Farnesol. Correct Ambrox target. Reduce Damascone Beta ≤12µL. Gate --brief generic. Momus review already APPROVED with 8 fixes folded. |
| C | perfumery-ai-engine | approved (unclear→resolved), Momus APPROVED | 11 todos / 6 waves. SQLite knowledge engine consolidating 7 data sources + 8 rule locations + interaction graph + property estimator + formula memory + 10 science domains. Additive (generates Python dicts, pipeline unchanged). T1 schema/migrate, T2/T3/T4 parallel query APIs, T5/T6 parallel graph+estimator, T7-T10 memory/failure-registry/brain/sync. |
| D | final-audit-polish-v1 | approved 2026-07-21, review_required=true | 4 waves. A=Literature/Data gap survey + ≥500 truths, B=Pipeline mass-testing ALL 100+ formulas, C=Gap remediation (depends A+B), D=Weakness report. Stopping condition ≥500 meta-verified truths (max 1 retry). High-accuracy review round 1 already incorporated. Awaiting start-or-review decision. |
| E | phase-1a-domain-foundation | awaiting-approval | 158-line Alembic/domain plan. New migration 20260717_0001_phase_1a_domain on top of frozen 20260716_0001. Schema adjustments: lab_formula_components add role+unit, lab_stock_solutions add remaining_mass_g. LegacyFormulaAdapter. No bottle/event/experiment API code. Plan file NOT yet written. |
| F | pipeline-improvement | awaiting-approval | 7 components C1-C7. C1 physics (UNIFAC stub, ethanol in mole fractions, mixture-shifted ODT, evaporation model, density), C2 gate logic (17 dead gates, _safe_gate, hedione standardize, skeleton threshold 0.5→1.0), C3 scoring (8 misnamed axes), C4 intervention (dose-reduction, perturbation bias, temperature), C5 data quality (sentinel ODTs, density, farnesene), C6 architecture (split gates.py 4710 lines, remove dead oav_intelligence 95% dead), C7 analysis output (hardcoded longevity, block balance, cost). Librarian research already done (HANNA, UNIFAC-Dortmund, competitive binding, Stevens, two-stage evap, skin temp, ALETHEIA, OpenMix, Pyrfume, POMMix, VIANA). |

## Verification approach (per track)
- A, B: pipeline gate JSON must PASS or PASS_WITH_SKIPS; OAV headspace table + temporal evolution presented; IFRA watchpoints resolved (Oakmoss ≤0.1% active, Damascone Beta ≤12µL).
- C: T10 sync script + pipeline parity tests = zero regression vs current dicts. One commit per todo. Independent Momus review already APPROVED.
- D: ≥500 meta-verified truths ledger. Pipeline mass-test coverage 100+ formulas. Wave dependency A+B→C→D enforced.
- E: db_bootstrap.upgrade_database succeeds; alembic downgrade works; LegacyFormulaAdapter round-trips; engine/workbench.py + golden fixtures unchanged.
- F: Each Cx has regression tests pinning current behavior FIRST (per decision 4), then behavior change. JSON output schema preserved (rename with deprecation aliases). No new pipeline scripts (RULE 2).

## Not started
Plan file `.omo/plans/rest-of-implementations.md` — pending config fix + restart + user "proceed".

## Approval gate
status: awaiting-approval (blocked on config fix first)