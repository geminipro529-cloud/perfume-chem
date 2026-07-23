---
name: deepseek-delegation
description: Parallel delegation protocol for Deepseek-only agents — multi-reader, multi-driver, persistent tracking
---

## Deepseek-Only Parallel Delegation Protocol

### Problem We're Solving

The explore/librarian agents from oh-my-openagent consistently abort (40 tool call limit, timeouts, context overflow). We need a reliable system using ONLY Deepseek provider agents (via deepinfra) that don't abort and produce trackable results.

### Architecture

```
                    Orchestrator (V4 Pro, Tier 1)
                          │
            ┌─────────────┼──────────────┐
            │             │              │
        Reader 1      Reader 2      Reader 3     ← task(category="quick") bg
       (file A)      (file B)      (file C)        deepseek-v4-flash
            │             │              │
            └─────────────┼──────────────┘
                          │
                     Collect Results
                          │
                    Driver 1         Driver 2     ← task(category="deep") bg
                   (Task X)         (Task Y)        deepseek-v4-flash
                          │              │
                    Collect Results
                          │
                    Orchestrator synthesizes
                          │
                    Run verification
```

### Tier Assignments

| Role | Model | Category | Purpose |
|---|---|---|---|
| Orchestrator | deepinfra/deepseek-v4-pro | (this session) | Planning, synthesis, verification |
| Reader | deepinfra/deepseek-v4-flash | category="quick" | Read files, extract facts, return structured data — NO code modifications |
| Driver | deepinfra/deepseek-v4-flash | category="deep" | Autonomous task completion — ONE goal per driver |
| Debugger | deepinfra/deepseek-v4-pro | category="oracle" | When 2+ driver attempts fail, debug the root cause |

### Protocol Rules

**Rule 1: Readers only read, never write.**
Reader prompt format: "Read {file_paths}. Extract {specific_data}. Return JSON or bullet list. Do NOT modify any files."

**Rule 2: One goal per driver.**
Driver prompt format: "Your ONLY task is: {specific_goal}. The output should be: {format}. You may modify ANY files needed to complete this task. Return: {verification_criteria}. If you encounter blockers, report them — do NOT abort."

**Rule 3: Collect before proceeding.**
Always call `background_output(task_id)` for ALL completed tasks before making decisions. Never assume a background task's result without reading it.

**Rule 4: 3-attempt escalation.**
Driver fails 1st attempt → read output, determine root cause.
Driver fails 2nd attempt → escalate to `category="oracle"` for debugging.
Driver fails 3rd attempt → task_id continuation with explicit fix instruction.

**Rule 5: Cancel before new wave.**
Between waves, cancel stale background tasks: `background_cancel(all=true)`.

**Rule 6: Timeout handling.**
If a task runs >5 min with no result, kill it and restart with smaller scope.

### Task Templates

**Reader template:**
```
task(
    category="quick",
    load_skills=["memory"],  # optional
    description="Read {file}: {purpose}",
    prompt="Read file: {path}. Extract: {what_to_extract}. Format: {format}. Do NOT modify files.",
    run_in_background=true
)
```

**Driver template:**
```
task(
    category="deep",
    load_skills=[],
    description="{action}: {target}",
    prompt="Goal: {goal}. Files you may modify: {files}. Expected output: {output}. Verification: {check}.",
    run_in_background=true
)
```

**Debugger template:**
```
task(
    category="oracle",  # uses V4 Pro, more reliable
    load_skills=[],
    description="Debug: {problem}",
    prompt="The driver task '{id}' failed with: {error}. Analyze and give EXACT fix instructions.",
    run_in_background=false  # sync — we need this result NOW
)
```

### Load Guidelines

| Task type | Max concurrent | Why |
|---|---|---|
| Readers | 3-5 | Lightweight — each reads 1-3 files |
| Drivers | 2-3 | Heavier — each modifies code + runs tests |
| Debuggers | 1 | Synchronous — we wait for this |

### Verification Protocol

After each driver task completes:
1. Read the driver's output
2. Check the files it modified
3. Run the verification command from the driver's prompt
4. If verification fails, escalate to debugger
5. On debugger success, re-drive with fix instructions

### Session Cost Tracking

| Task | Tokens est. | Cost (Flash) |
|---|---|---|
| Reader (3 files) | 5K in / 2K out | $0.003 |
| Driver (implement) | 20K in / 5K out | $0.04 |
| Debugger (oracle) | 10K in / 3K out | $0.02 (V4 Pro) |
| Orchestrator overhead | 15K in / 3K out | $0.04 (V4 Pro) |
| **Typical wave (3 readers + 2 drivers)** | | **~$0.12** |
