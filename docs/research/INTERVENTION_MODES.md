# Intervention Modes

`scripts/intervention_recommend.py` is a standalone operator CLI for three
types of recommendations.

## Modes

- `pre_mix` - use before the formula is finalized. This is the normal
  formulation-time optimization mode.
- `post_mix` - use after a bottle is already mixed. The engine stays add-only
  and conservative.
- `between_mix` - use after a trial or wear test, before the next batch. This
  mode accepts observations and intent tags as input.

## Inputs

The CLI accepts either:

- `--formula-file <markdown>` with optional `--formula` or `--name`, or
- `--bundle-dir <verification_runs/...>` pointing at a verification bundle.

Observation hints:

- `--intent-tag` can be repeated.
- `--observation` can be repeated.

## Examples

```powershell
python scripts\intervention_recommend.py --formula-file luxury_formulas_2026-03-26.md --formula 1 --mode all
python scripts\intervention_recommend.py --bundle-dir verification_runs\20260402-180755-iris-imperiale-powdery-iris-suede --mode between_mix
python scripts\intervention_recommend.py --formula-file Orange_Blood_Optimized_30mL_Mixing_Guide.md --mode post_mix --top-n 3
```

## Current Shared Dependencies

The CLI currently uses these shared engine APIs when they are available:

- `engine.formula_recommendations.generate_intervention_recommendations`
- `engine.formula_recommendations.format_recommendations`
- `engine.optimizer.scoring.FormulaScorer`
- `engine.optimizer.optimizer.FormulaOptimizer`
- `engine.optimizer.models.FormulaVector`
- optional `engine.intervention_profiles` if the module is present

The script also has local fallback parsing for formula markdown files and
verification bundles, so it can still run if some shared APIs change.
