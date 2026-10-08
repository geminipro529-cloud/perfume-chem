---
name: perfume-gate-run
description: Run perfume-chem's formula release gate read-only on a formula file and report the OAV headspace table and gate results without changing the formula or audit log.
---

# Read-only release gate run

> **Status: DRAFT (2026-10-08).** Not yet proven over many runs. If any step here
> is wrong or missing when you use it, fix this file in the same change and add a
> line under "Known issues / change log". Keep `.claude/skills/` and
> `.agents/skills/` copies identical (`tests/test_skill_mirrors.py` checks this).

Use whenever a formula .md needs gating with `scripts/formula_release_gate.py`.

## Before the run
1. Record `sha256sum` of every formula file you will gate (and its parent).
2. Check names and dilution cells against the gate's inventory labels (V5 workbook
   plus dated overlays, not `inventory.txt`). Dilution cells must read `neat`,
   `10% w/w in DPG`, `10% v/v in ethanol` and so on; a naked `10%` or
   "neat / as supplied" fails `concentration_basis` on master. Known spellings:
   Hedione, Lavender EO (BONTAUX SAS), Petitgrain EO Paraguay, Coriander Essential
   Oil, Pink Pepper EO, Vetiver EO (Haiti), Dihydromyrcenol, Heliotropal. The
   workbook spells DBCA as "Dimethyl Benzyl Carbonyl Acetate".
3. Use one flat table: section headers containing numbers get parsed as rows.
   Sum the µL yourself for `--expected-concentrate-ul`.

## Run
```bash
PERFUME_PIPELINE_AUDIT_PATH=<scratch>/audit.jsonl PYTHONDONTWRITEBYTECODE=1 \
python scripts/formula_release_gate.py --formula-file <file.md> \
  --expected-concentrate-ul <sum> --brief <generic|auto|...> \
  [--parent-formula-file <parent.md>] \
  --json --no-append-analysis --no-audit > <scratch>/out.json
python scripts/format_pipeline_analysis.py --input <scratch>/out.json > <scratch>/analysis.md
```
Never omit `--no-append-analysis --no-audit`: without them the gate rewrites the
formula file and appends to the large audit log. Always pass
`--parent-formula-file` for a revision (Rule 5 pre-mix guard).

## After the run
1. Re-check the sha256 of the formula files and say they are unchanged.
2. Check `exact_subtotal` matches the expected concentrate; if larger, headers were
   parsed as materials.
3. Keep the JSON and analysis as an immutable artifact named with the first 12 hex
   digits of the JSON's sha256 (never inside `formulas/`).
4. Report in this order: the OAV table from `formulas[0].formula_state.materials[]`
   (`| Material | Dil | Raw µL | Act µL | MW | MF% | VP Pa | γ | Vapor ppm | ODT ppm | OAV | Note |`),
   `note_distribution` and the `time_series` windows, then the overall verdict with
   PASS/WARN/FAIL/SKIP counts and each FAIL with its reason.
5. Classify FAILs. Data holes (`natural_composite_coverage`,
   `physics_data_coverage`, `odt_coverage`, `inventory_stock_contract`,
   `phase_compatibility`) are fail-closed data gaps, not formula problems. Today no
   formula can reach an overall PASS (several gates always WARN), so never chase one.
6. OAV is a heuristic, matrix-omitted screen. Never present it as intensity,
   liking or perceived share (Rule 1).

In chat give a short summary plus the artifact path; paste the full analysis only
when asked.

## Known issues / change log
- 2026-10-08: first draft, from the R6 lavender ladder and Femme R6 review runs.
