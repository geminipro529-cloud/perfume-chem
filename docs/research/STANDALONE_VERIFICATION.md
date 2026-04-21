# Standalone Verification Harness

This project now has a standalone verifier that does not modify or integrate with the main pipeline.

Script:
- [`scripts/verify_formula_workflow.py`](/d:/chatbots/perfume-chem/scripts/verify_formula_workflow.py)

## Purpose

Generate a self-contained verification bundle for one formula:

- predicted score report
- chemistry and mixing notes
- wear-test template
- comparison template for predicted vs observed results
- observations CSV for real-world results

## Usage

Verify a numbered formula from a markdown collection:

```powershell
python scripts\verify_formula_workflow.py --formula-file luxury_formulas_2026-03-26.md --formula 1
```

Verify by partial name:

```powershell
python scripts\verify_formula_workflow.py --formula-file luxury_formulas_2026-03-26.md --name "Iris"
```

## Output

Each run creates a new folder under [`verification_runs/`](/d:/chatbots/perfume-chem/verification_runs).

Files created:

- `metadata.json`
- `bundle_manifest.json`
- `verification_summary.json`
- `predicted_report.md`
- `mixing_protocol.txt`
- `wear_test_template.md`
- `comparison_template.md`
- `observations.csv`

## Intended Workflow

1. Generate a verification bundle for a candidate formula.
2. Mix the formula and follow the generated protocol as a starting point.
3. Log real observations in `wear_test_template.md` and `observations.csv`.
4. Compare observed results against `comparison_template.md`, using `predicted_report.md` as the reference baseline.
5. Decide whether the formula is acceptable, needs revision, or should be discarded.

## Limits

- This harness only packages existing engine outputs. It does not validate them against external literature or live panel data.
- Confidence remains limited until real outcomes are collected and used for calibration.
- The comparison file is a template, not a scored evaluator. You still need to enter observed values manually before deltas become meaningful.
