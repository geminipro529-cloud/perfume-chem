# Complete YSL LNDL Bleu Chamomile — Fix + Full Pipeline Integration

## Summary
Fix API regression from ruff cleanup, upgrade formula format to Prada L'Homme standard, integrate ALL pipeline outputs, address gate failures, and produce a decision-complete analysis.

**Reference format**: `formulas/Prada_LHomme_Luxury_Orris_30mL_EdT.md` (354 lines, Prada-tier)
**Current state**: Formula gated once but FAIL (chemistry_stability API break + confidence minimum)

---

## TODOs

- [x] 1. Fix API regression: `predict_shelf_life_days(T_K=...)` → `t_k=...` in gates.py:526
- [x] 2. Upgrade formula file format to Prada L'Homme standard (Active uL, ppm proxy, matrix inputs, selection audit)
- [x] 3. Run formula_release_gate with --json to get full pipeline output
- [ ] 4. Run format_pipeline_analysis.py to get perfumer assessment
- [ ] 5. Run format_oav_report.py for headspace breakdown
- [x] 6. Address formula WARNs: bergamot phototoxicity, Zenolide OAV=0, missing fougere oakmoss
- [x] 7. Re-gate with formula fixes, verify chemistry_stability PASS + confidence improves
- [ ] 8. Append complete pipeline analysis to formula file (Prada L'Homme format)
- [ ] 9. Present full analysis in chat with OAV headspace table, temporal evolution, perfumer assessment, structural OAV

---

## Task 1: Fix API Regression (HIGH)
- **File**: `engine/pipeline/gates.py` line 526
- **Change**: `T_K=config.temperature_K` → `t_k=config.temperature_K`
- **Verify**: `python -c "from engine.chemistry.maturation import predict_shelf_life_days; print(predict_shelf_life_days({}, t_k=295))"`

## Task 2: Upgrade Formula Format
Reference: Prada L'Homme format. Add to Bleu Chamomile:
- Active uL column in formula table
- Active ppm v/v proxy column
- Finished Matrix Inputs section (ethanol 96% + water)
- Selection/Rejection Audit section
- Specific function column (like Prada)

## Task 3: Run formula_release_gate
```bash
python scripts/formula_release_gate.py \
  --formula-file formulas/La_Nuit_de_Bleu_Chamomile_30mL_EDP.md \
  --expected-concentrate-ul 3305 \
  --brief aromatic_fougere \
  --json > output/chamomile_v2.json
```

## Task 4: Run format_pipeline_analysis
```bash
python scripts/format_pipeline_analysis.py --input output/chamomile_v2.json
```
Present the output IN CHAT first, then append to formula file.

## Task 5: Run format_oav_report
```bash
python scripts/format_oav_report.py output/chamomile_v2.json
```
Paste OAV table IN CHAT before discussing gates.

## Task 6: Address Formula Issues
Based on pipeline findings:
- **Bergamot phototoxic** (6.12% > IFRA 2%): Reduce from 180→60 µL. Add Cedrat FCF 40 µL or Methyl Pamplemousse 10% 60 µL for citrus lift without phototoxicity.
- **Zenolide OAV=0.02** (VP=0.0001 Pa too low): Swap Zenolide→Romandolide (depleted? Check inventory) or increase Zenolide to 200 µL. Alternatively, accept "structural-only" role.
- **Missing fougere oakmoss**: Add Evernyl 5-10 µL (oakmoss replacement).
- Check inventory.txt for Romandolide stock.

## Task 7: Re-gate with Fixes
Re-run pipeline with corrected formula. Expected: chemistry_stability PASS, confidence >25, bergamot phototoxic WARN resolved.

## Task 8: Append Analysis to Formula File
Replace existing <!-- PIPELINE_ANALYSIS_START --> section with fresh output. Include:
- Run Evidence Contract
- Gate Summary
- Authority Dimensions
- Headspace OAV table (Opening 0s)
- Note Distribution (T/H/B split + per-material OAV ranking)
- Sub-threshold Materials
- Temporal Evolution (5 windows)
- Perfumer's Assessment (Character, Opening, Heart, Drydown, Sillage, Longevity, Balance, Flags)
- Structural OAV Analysis
- OAV by Odor Family

## Task 9: Chat Presentation
Present analysis verbatim in chat per AGENTS.md rule:
1. OAV headspace table FIRST
2. Note distribution + temporal evolution
3. Perfumer analysis (all 8 sections)
4. Gate outcomes last

---

## Pre-Flight Checklist
- [ ] Read inventory.txt (RULE ZERO) — check for Romandolide stock
- [ ] Check every material has physics data (ODT, MW, VP, logP)
- [ ] Check for duplicate ODT entries
- [ ] Confirm `docs/fragrance_families_reference.md` has aromatic_fougere family

## Verification
```bash
# API regression fix
python -c "from engine.chemistry.maturation import predict_shelf_life_days; print('OK')"

# Formula gate
python scripts/formula_release_gate.py --formula-file formulas/La_Nuit_de_Bleu_Chamomile_30mL_EDP.md --expected-concentrate-ul 3305 --brief aromatic_fougere --json | python -c "import sys,json; d=json.load(sys.stdin); print('Overall:', d.get('overall','?')); [print(f'  {g[\"name\"]}: {g[\"status\"]}') for g in d.get('formulas',[{}])[0].get('gates',[])]"

# Full analysis
python scripts/format_pipeline_analysis.py --input output/chamomile_v2.json
```
