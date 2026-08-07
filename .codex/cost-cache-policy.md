# Perfume-Chem Cost And Cache Policy

Use this workspace policy as the default route for Codex sessions in this repo.

## Local First

- Prefer `rg`, bounded file reads, `git diff`, focused tests, and existing scripts.
- Exclude generated or bulky paths from exploratory scans: `.git`, `.venv`, `.codex/runtime`, `.opencode/node_modules`, `.omo/evidence`, `archive`, `output`, `verification_runs`, caches, and coverage output.
- Do not load plugins, MCPs, browser sessions, or subagents unless they provide evidence that local tools cannot provide cheaply.

## DeepLuna Cache

- Use DeepLuna only for bounded mechanical work: extraction, comparison, fixture enumeration, predefined check analysis, or frozen-interface leaf drafts.
- Set `reuse_cache: true` for delegated jobs and keep stable instructions before volatile repository state.
- Prefer Flash reads; batch independent reads when there are two or more related evidence nodes.
- Let the orchestrator own cache, DeepSeek, and Luna fallback. Do not start a parallel fallback path for the same job.

## Verification Ladder

- Run focused checks for touched modules first.
- Run `scripts/pipeline_audit.py project-verify --quick --json` before push-level decisions.
- Run full project verification only for merge, publication, scientific release, or cross-system behavior changes.
- Cached or delegated evidence can shorten diagnosis, but it cannot replace fresh final verification.

