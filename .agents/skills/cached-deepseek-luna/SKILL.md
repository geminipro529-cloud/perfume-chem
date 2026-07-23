---
name: cached-deepseek-luna
description: Use for bounded DeepSeek and Luna delegation in Perfume-Chem through the direct orchestrator MCP, with local cache reuse, explicit path scopes, and independent verification.
---

# Cached DeepSeek/Luna Delegation

1. Prefer local `rg`, parsing, diffs, and focused tests before any model call.
2. Use `deepseek_read_submit` on `FLASH` for one bounded read; allow no more than two independent reads.
3. Use `deepseek_batch_submit` only for two or more evidence nodes; default concurrency to one and gate descendants on `PASS` or `CACHED`.
4. Put stable instructions first, dynamic state last, set `reuse_cache: true`, and bound output tokens.
5. Allow only repository-relative paths and exact read-only commands. Poll status and never duplicate an active job.
6. Stop for local review on architecture, scientific, policy, or scope uncertainty.
7. Use at most one `deepseek_write_submit` job, with `PRO` and the smallest explicit write allowlist.
8. Let the orchestrator choose Luna only through its cost/failure gate. Retry once only for a transient read failure.
9. Read `deepseek_metrics` after paid batches or periodic audits, not before every task.
10. Inspect the live diff and run focused tests locally before accepting any worker claim.
