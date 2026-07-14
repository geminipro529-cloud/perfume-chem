---
description: Run pipeline audit for historical scanning
agent: build
---

Run the pipeline audit for historical formula scanning.

```bash
python scripts/pipeline_audit.py
```

If the user provides a brief argument, pass it:
```bash
python scripts/pipeline_audit.py --brief $1
```

Summarize: which formulas pass/fail, any recurring issues, data quality gaps, and material stock anomalies across the history.
