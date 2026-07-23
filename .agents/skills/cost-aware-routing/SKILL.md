---
name: cost-aware-routing
description: Use before invoking plugins, MCP servers, web research, subagents, or broad test suites in Perfume-Chem; selects the least expensive path that preserves required quality and evidence.
---

# Cost-Aware Routing

1. Define the evidence needed for the next decision.
2. Prefer existing local files, `rg`, focused tests, and built-in tools.
3. Use a plugin or MCP only when it provides unique data, authorization, or execution capability.
4. Compare accuracy risk, latency, paid tokens, context growth, and state-change risk.
5. Choose the cheapest option that still meets the acceptance criteria. Skip lower-value calls.
6. Use at most one heavy external path at a time; inspect its evidence before escalating.
7. Plugins are off by default in this project. For a justified CLI-only session, opt in with `codex -c features.plugins=true`.
8. Keep Codex on the standard service tier by default; GPT-5.6 Fast mode costs 2.5x credits and needs a concrete latency benefit.
9. Never replace fresh completion verification with cached or delegated claims.
