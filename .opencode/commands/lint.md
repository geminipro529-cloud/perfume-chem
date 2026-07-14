---
description: Run ruff + mypy linting (CI order)
agent: build
---

Run lint and type checking in the exact CI order.

1. Backend lint (Poetry environment):
```bash
cd backend && poetry run ruff check app
```

2. Backend type check:
```bash
cd backend && poetry run mypy app --ignore-missing-imports
```

Report any failures clearly. Suggest fixes for lint/type errors.
