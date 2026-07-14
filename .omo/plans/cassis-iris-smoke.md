# cassis-iris-smoke - Work Plan

## TL;DR

Execute the Cassis Iris Smoke formula designed collaboratively. Add Cade Oil Rectified 1% to inventory, create formula file, inventory guard, pipeline gate with `--brief generic`, present OAV analysis, iterate.

## Todos

- [x] 1. Integrate Cade Oil Rectified 1% into inventory system — add to all 4 data files (inventory.txt, YAML, ingredient_intelligence.py, odor_thresholds.py)
- [x] 2. Create formula file `formulas/Cassis_Iris_Smoke_30mL_EdP.md` from draft content
- [ ] 3. Run inventory guard — verify all 44 materials against inventory.txt
- [ ] 4. Run pipeline gate: `python scripts/formula_release_gate.py --formula-file formulas/Cassis_Iris_Smoke_30mL_EdP.md --expected-concentrate-ul 6000 --brief generic --json`
- [ ] 5. Run pipeline analysis: `python scripts/format_pipeline_analysis.py --input output/cassis_iris_smoke_gate.json` — present OAV table, temporal evolution, perfumer analysis
- [ ] 6. Evaluate results — check OAV headspace, IFRA (Oakmoss at 0.12%), temporal windows. Recommend dose adjustments.

## Final Verification Wave

- [ ] F1. All materials in inventory, no depleted used
- [ ] F2. Concentrate total = 6,000 µL ± 100
- [ ] F3. IFRA compliance verified (especially Oakmoss)
- [ ] F4. OAV analysis complete — all sections presented

## Success criteria

1. Cade Oil Rectified 1% integrated into 4 data files
2. Formula file created with all 44 materials, correct doses, mixing protocol
3. Pipeline exits clean, JSON output produced
4. Full perfumer analysis presented (8 sections)
5. Iteration recommendations based on OAV data
