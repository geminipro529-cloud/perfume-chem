---
name: pipeline-analysis
description: Format pipeline JSON output and append the full analysis section to a formula file. MUST USE after every pipeline gate run.
---

## What I do
- Take a pipeline JSON output file and run `scripts/format_pipeline_analysis.py` on it
- Present the full formatted analysis verbatim in chat (per AGENTS.md requirement)
- Append the analysis to the formula markdown file under a `## Pipeline Analysis` section
- Archive the JSON output to `archive/json_runs/` with a timestamped filename

## When to use me
Use AFTER every successful `scripts/formula_release_gate.py` run:
- Gate passed or failed — the analysis is diagnostic either way
- Run BEFORE discussing gate outcomes (raw headspace physics first)

## Workflow

### Step 1: Ensure JSON output exists
If you ran the gate with `--json`, ensure the output was captured:
```
python scripts/formula_release_gate.py \
    --formula-file formulas/My_Formula_30mL_EDP.md \
    --expected-concentrate-ul 6000 \
    --brief generic \
    --json > output.json
```
If the JSON is in a temp file, save it first.

### Step 2: Run the analysis script
```
python scripts/format_pipeline_analysis.py --input output.json
```
Capture the full output — this is the perfumer analysis.

### Step 3: Present in chat
Copy the full analysis output verbatim into the conversation. Do NOT summarize or paraphrase it.

### Step 4: Append to formula file
Add a `## Pipeline Analysis` section with the full analysis text to the formula markdown file:
```
formulas/My_Formula_30mL_EDP.md
```

### Step 5: Archive the JSON
```
copy output.json archive/json_runs/My_Formula_30mL_EDP_<date>.json
```

## Required: Always extract these sections from raw JSON first
Before running the analysis script, read these from the raw JSON:
- **OAV headspace table** from `formulas[0].formula_state.materials[]`
- **Temporal evolution** from `formulas[0].time_series[]`
- **Note distribution** from `formulas[0].formula_state.note_distribution`
- **Gate results** — pyramid, OAV intelligence, IFRA, config summary

Present the OAV table BEFORE discussing gate outcomes.
