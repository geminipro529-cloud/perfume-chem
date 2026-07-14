---
description: Run engine-level tests from repo root
agent: build
---

Run the engine-level test suite from the repo root.

```bash
pytest tests/
```

Report test counts (passed/failed) and any failures with stack traces. Note that engine tests use pip environment (requirements.txt), not Poetry.
