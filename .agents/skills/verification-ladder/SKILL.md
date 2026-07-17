---
name: verification-ladder
description: Use when validating Perfume-Chem changes; orders checks from focused and cheap to full release verification while preventing redundant runs and stale success claims.
---

# Verification Ladder

1. Reproduce a defect with the smallest relevant test or command.
2. Run focused lint, type, and test checks for changed modules.
3. Use `.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on POSIX; do not silently fall back to an interpreter missing project dev dependencies.
4. Before a full run, check the interpreter once with `-m build --version` to avoid a late packaging-only failure.
5. Run `scripts/pipeline_audit.py project-verify --quick --json` with that interpreter before push-level decisions.
6. Run the full command without `--quick` before merge, publication, or completion claims.
7. Add `--include-docker` only when Docker is available and the release decision needs it.
8. Do not repeat an unchanged expensive command during diagnosis; record its worktree fingerprint and result.
9. Completion claims always require a fresh applicable verification run, even when earlier output was cached.
