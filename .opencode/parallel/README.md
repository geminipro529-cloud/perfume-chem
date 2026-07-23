# Parallel Reader/Brain Framework

Session-isolated job runner for multi-window OpenCode.

## Contract

- Every job is scoped to `OPENCODE_SESSION_ID` (env). Runner refuses if missing.
- Atomic writes: `.tmp` -> `os.replace()` on every output file.
- Cross-process lock: `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX) on `job.lock`.
- Stale lock reclaim after 30 min if holding PID no longer alive.
- Status enum: `pending`, `running`, `complete`, `failed`, `stale_reclaimed`.
- `collect` refuses output unless status is `complete` or `stale_reclaimed`.

## CLI

```
python .opencode/parallel/runner.py submit --kind read --path <file> --reader flash
python .opencode/parallel/runner.py submit --kind brain --prompt "<text>" --files <paths...> --reader glm-max-flex
python .opencode/parallel/runner.py status <job_id>
python .opencode/parallel/runner.py collect <job_id>
python .opencode/parallel/runner.py list [--session <id>]
python .opencode/parallel/runner.py cleanup [--stale-minutes 30]
```

## Reader (Tier 1 - free)

Local file read with atomic sha256. No model call. Output: `{path, lines, sha256, captured_at, line_count, reader}`.

## Brain (Tier 2 - paid)

Calls DeepInfra GLM-5.2 max (flex tier) via `urllib.request`. Logs token spend to `brain_ledger.jsonl`. Output: `{reasoning, decision, references, usage}`.
