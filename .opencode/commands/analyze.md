---
description: Format pipeline analysis from existing JSON output
agent: build
---

Read a pipeline JSON output file and run the analysis formatter.

If the user provides a file path as $1, use it:
```bash
python scripts/format_pipeline_analysis.py --input $1
```

If no file path given, default to the most recent output:
```bash
python scripts/format_pipeline_analysis.py --input output/pipeline_result.json
```

Present the full analysis verbatim in the chat — do not summarize or paraphrase.
