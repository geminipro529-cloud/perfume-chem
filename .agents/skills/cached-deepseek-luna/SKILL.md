---
name: cached-deepseek-luna
description: Use for bounded DeepSeek and Luna delegation in Perfume-Chem through the direct orchestrator MCP, with local cache reuse, explicit path scopes, and independent verification.
---

# Cached DeepSeek/Luna Delegation

1. Start with `deepseek_read_submit` on `FLASH`; allow no more than two independent reads.
2. Put stable instructions first, dynamic state last, set `reuse_cache: true`, and bound output tokens.
3. Allow only repository-relative paths and exact read-only commands.
4. Poll `deepseek_job_status`; never submit a duplicate while a job is active.
5. Stop for local review on architecture, scientific, or scope uncertainty.
6. Use at most one `deepseek_write_submit` job, with `PRO` and the smallest explicit write allowlist.
7. Let the orchestrator choose Luna only through its cost/failure gate; do not force paid retries.
8. Inspect the live diff and run focused tests locally before accepting any worker claim.
