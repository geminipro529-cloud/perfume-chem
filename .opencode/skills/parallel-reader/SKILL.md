---
name: parallel-reader
description: Document the .opencode/parallel/runner.py contract for session-isolated parallel jobs
---

## Location

`.opencode/parallel/runner.py` — stdlib-only CLI.

## Contract

- Every job scoped to `OPENCODE_SESSION_ID` env. Refuses if missing.
- Atomic writes: `.tmp` -> `os.replace()`.
- Cross-process lock via `msvcrt.locking` (Windows).
- Stale lock reclaim after 30 min if PID not alive.
- `collect` refuses unless status is `complete` or `stale_reclaimed`.

## Reader Jobs (free)

Local file reads with sha256 capture. No model call.

```bash
python .opencode/parallel/runner.py submit --kind read --path <file> --reader flash
python .opencode/parallel/runner.py status <job_id>
python .opencode/parallel/runner.py collect <job_id>
```

Output: `{path, lines, sha256, captured_at, line_count, reader}`

## Brain Jobs (paid, Tier 2)

Calls DeepInfra GLM-5.2 max flex via urllib.request.

```bash
python .opencode/parallel/runner.py submit --kind brain --prompt "<text>" --files <paths...> --reader glm-max-flex
```

Output: `{reasoning, decision, references, usage}`. Token spend logged to `brain_ledger.jsonl`.

## Administration

```bash
python .opencode/parallel/runner.py list [--session <id>]
python .opencode/parallel/runner.py cleanup [--stale-minutes 30]
```
