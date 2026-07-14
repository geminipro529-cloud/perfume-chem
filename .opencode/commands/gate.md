---
description: Run formula release gate with full analysis
agent: build
---

Read inventory.txt to verify all materials are in stock before proceeding.

Run the pipeline gate for the formula file at $ARGUMENTS. The user should provide arguments in the format: `<formula-file> <concentrate-ul> <brief>`.

1. If arguments are provided (format: `$1` = formula file, `$2` = concentrate uL, `$3` = brief), run:
```bash
python scripts/formula_release_gate.py --formula-file $1 --expected-concentrate-ul $2 --brief $3 --json > output/pipeline_result.json
```

2. Then run the analysis formatter:
```bash
python scripts/format_pipeline_analysis.py --input output/pipeline_result.json
```

3. After running, present the full analysis output verbatim in the chat.
4. Append the analysis under a `## Pipeline Analysis` section at the end of the formula markdown file.

If no arguments provided, ask the user for: formula file path, expected concentrate uL, and brief family.
