---
description: Run backend tests with coverage (Poetry)
agent: build
---

Run the backend test suite with coverage.

```bash
cd backend && poetry run pytest --cov=app --cov-report=term
```

Report test counts (passed/failed), coverage percentage, and any failures with stack traces.
