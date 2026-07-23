# Fix YSL LNDL Bleu Chamomile — API Regression + Formula Issues

## Summary
Ruff cleanup renamed `T_K→t_k` in `maturation.py` which broke the `predict_shelf_life_days` call in `gates.py`. Additionally, the formula has phototoxic bergamot overload, Zenolide underperformance, and missing fougere oakmoss. Fix the API break first, then address formula issues.

---

## TODOs

- [ ] 1. Fix API regression: `predict_shelf_life_days(T_K=...)` → `t_k=...`
- [ ] 2. Re-gate La Nuit de Bleu Chamomile to confirm chemistry_stability passes
- [ ] 3. Address critical WARNs: phototoxic bergamot (>IFRA 2%), Zenolide OAV=0, missing oakmoss
- [ ] 4. Final re-gate and verify all gates pass

---

## Task 1: Fix API Regression
- **File**: `engine/pipeline/gates.py` line 526
- **Change**: `T_K=config.temperature_K` → `t_k=config.temperature_K`
- **Verify**: `python -c "from engine.chemistry.maturation import predict_shelf_life_days; print(predict_shelf_life_days({}, t_k=295))"`

## Task 2: Re-gate Formula
```bash
python scripts/formula_release_gate.py \
  --formula-file formulas/La_Nuit_de_Bleu_Chamomile_30mL_EDP.md \
  --expected-concentrate-ul 3305 \
  --brief aromatic_fougere \
  --json > output/chamomile_gate.json
```
- Confirm `chemistry_stability` passes
- Check `confidence_minimum` (should improve if chemistry_stability adds points)

## Task 3: Formula Fixes
Based on pipeline findings:
- **Bergamot phototoxic**: 6.12% > IFRA 2% → reduce bergamot from 180→60 µL, add Cedrat FCF or Methyl Pamplemousse for citrus lift
- **Missing oakmoss**: Fougere skeleton requires oakmoss/evernyl → add Evernyl 5-10 µL
- **Zenolide OAV=0**: VP=0.0001 Pa too low to project → swap for Romandolide (higher VP for projection)
- **Confidence penalty**: preflight science penalty 28.9 — likely from missing fougere skeleton + phototoxic

## Task 4: Final Re-gate
- Re-run with fixes, confirm all gates PASS or WARN (no FAIL)
