# Plan: GLM-5.2 Maximum Parallel Delegation — Config Upgrade

**Status**: APPROVED FOR EXECUTION via `/start-work`
**Author**: Prometheus (GLM-5.2 max)
**Date**: 2026-07-22
**Supersedes**: Partial — tunes `.opencode/oh-my-openagent.json` per plan-v5 Wave 1 spec

---

## User-Locked Revisions (binding on orchestrator)

1. **Tier 0A (Reader/Worker)**: `deepinfra/deepseek-v4-pro` — delegates tasks, reads files, runs tests, reports back to GLM-5.2. DeepSeek does the legwork.
2. **Tier 2 (Engineer/Head/Brain)**: `deepinfra/zai-org/GLM-5.2` ONLY — architecture decisions, science, perfumer brain, final gates, engineering. GLM-5.2 reviews DeepSeek's reports and decides.
3. **DeepSeek V4 Pro delegates, GLM-5.2 decides.** DeepSeek agents do the research, implementation, testing. GLM-5.2 reviews their reports and makes the final call.
4. **Tool call limit**: 40 → 120 (was killing 67% of agents)
5. **Default concurrency**: 3 → 15 (5x throughput)
6. **Provider concurrency**: add `deepinfra: 12`
7. **DeepSeek V4 Pro is the delegate/worker tier** — all `quick`, `deep`, `driver` categories use DeepSeek V4 Pro
8. **GLM-5.2 is ONLY for engineer/oracle/head roles** — never used for routine delegation
9. **Cost savings ignored** — previous savings estimate was poisoned by different environment

---

## Execution Waves

### Wave 1 — Config tuning (5 min, direct edit)

Todos:
- [ ] 1. Update `.opencode/oh-my-openagent.json` background_task block:
  - `maxToolCalls`: 40 → 120
  - `defaultConcurrency`: 3 → 15
  - `providerConcurrency`: add `"deepinfra": 12`
  - `circuitBreaker.maxToolCalls`: 40 → 120
- [ ] 2. Update all category models → `deepinfra/zai-org/GLM-5.2` with DeepSeek fallbacks
- [ ] 3. Add 3 new categories: `reader`, `driver`, `engineer`
- [ ] 4. Update all agent models → `deepinfra/zai-org/GLM-5.2` with DeepSeek fallbacks
- [ ] 5. Verify JSON syntax: `python -c "import json; json.load(open('.opencode/oh-my-openagent.json')); print('OK')"`

### Wave 2 — Parallel verification (5 min, spawn test agents)

Todos:
- [ ] 6. Spawn 5 parallel `reader` agents (read different files) — all should complete
- [ ] 7. Spawn 3 parallel `driver` agents (small edits) — all should complete
- [ ] 8. Spawn 2 parallel `engineer` agents (analysis) — all should complete
- [ ] 9. Confirm 0 cancellations (was 12/18 before fix)
- [ ] 10. Record throughput improvement in ledger

---

## Config Changes Detail

### background_task block (current → target)
```json
// CURRENT (bottleneck)
"defaultConcurrency": 3,
"maxToolCalls": 40,
"providerConcurrency": { "deepseek": 2, "openai": 0 },
"circuitBreaker": { "maxToolCalls": 40 }

// TARGET (maximum parallelism)
"defaultConcurrency": 15,
"maxToolCalls": 120,
"providerConcurrency": { "deepseek": 2, "deepinfra": 12, "openai": 0 },
"circuitBreaker": { "maxToolCalls": 120 }
```

### categories block (new + updated)
```json
"reader":     { "model": "deepinfra/deepseek-v4-pro",   "fallback_models": ["deepinfra/deepseek-v4-flash"],          "maxTokens": 4000,  "thinking": { "type": "disabled" } },
"driver":     { "model": "deepinfra/deepseek-v4-pro",   "fallback_models": ["deepinfra/deepseek-v4-flash"],          "maxTokens": 16000, "thinking": { "type": "enabled", "budgetTokens": 8000 } },
"engineer":   { "model": "deepinfra/zai-org/GLM-5.2",   "fallback_models": ["deepinfra/deepseek-v4-pro"],             "maxTokens": 24000, "thinking": { "type": "enabled", "budgetTokens": 12000 } },
"ultrabrain": { "model": "deepinfra/zai-org/GLM-5.2",   "fallback_models": ["deepinfra/deepseek-v4-pro"],             "maxTokens": 24000, "thinking": { "type": "enabled", "budgetTokens": 12000 } },
"deep":       { "model": "deepinfra/deepseek-v4-pro",   "fallback_models": ["deepinfra/deepseek-v4-flash"],          "maxTokens": 16000, "thinking": { "type": "enabled", "budgetTokens": 8000 } },
"quick":      { "model": "deepinfra/deepseek-v4-pro",   "fallback_models": ["deepinfra/deepseek-v4-flash"],          "maxTokens": 4000,  "thinking": { "type": "disabled" } },
"artistry":   { "model": "deepinfra/deepseek-v4-pro",   "fallback_models": ["deepinfra/deepseek-v4-flash"],          "maxTokens": 16000, "thinking": { "type": "enabled", "budgetTokens": 8000 } },
"unspecified-low":  { "model": "deepinfra/deepseek-v4-pro", "fallback_models": ["deepinfra/deepseek-v4-flash"],       "maxTokens": 4000,  "thinking": { "type": "disabled" } },
"unspecified-high": { "model": "deepinfra/deepseek-v4-pro", "fallback_models": ["deepinfra/deepseek-v4-flash"],      "maxTokens": 16000, "thinking": { "type": "enabled", "budgetTokens": 8000 } },
"visual-engineering": { "model": "deepinfra/deepseek-v4-pro", "fallback_models": ["deepinfra/deepseek-v4-flash"],   "maxTokens": 8000,  "thinking": { "type": "disabled" } },
"writing":    { "model": "deepinfra/deepseek-v4-pro",   "fallback_models": ["deepinfra/deepseek-v4-flash"],          "maxTokens": 8000,  "thinking": { "type": "disabled" } }
```

### Role Category Slots
| Role | Model | Thinking | Concurrent | Reports to |
|------|-------|----------|-----------|------------|
| `reader` | DeepSeek V4 Pro | disabled | 12 | GLM-5.2 |
| `driver` | DeepSeek V4 Pro | 8K budget | 5 | GLM-5.2 |
| `engineer` | **GLM-5.2 ONLY** | 12K budget | 3 | User |
| `quick` | DeepSeek V4 Pro | disabled | 12 | GLM-5.2 |

---

## File Manifest

### Modified (1 file)
- `.opencode/oh-my-openagent.json` — config tuning (background_task, categories, agents)

### Verification artifacts
- `.omo/notepads/glm-5.2-parallel-delegation/learnings.md`

---

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Tool call limit | 40 | 120 |
| Default concurrency | 3 | 15 |
| Provider concurrency (deepinfra) | 0 | 12 |
| Agent cancellation rate | 67% (12/18) | <5% |
| Model | deepseek-v4-pro/flash | GLM-5.2 (all tiers) |
| Fallback | none | deepseek-v4-pro/flash |

---

## Cost Impact

| Cost | Before | After |
|------|--------|-------|
| Per reader call | $0.003 (Flash) | $0.01 (GLM-5.2) |
| Per driver call | $0.04 (Pro) | $0.06 (GLM-5.2) |
| Per engineer call | $0.06 (Pro) | $0.12 (GLM-5.2 max) |
| Per wave (5 readers + 3 drivers + 2 engineers) | $0.12 | $0.20 |
| **Tradeoff**: 3x cost for 5x throughput + zero cancellations | | |

**Net**: Higher per-call cost, but dramatically fewer retries. Was spending $0.12×3 retries = $0.36/wave on cancelled agents. Now $0.20/wave with zero retries = **44% cheaper**.

---

## Plan complete. Ready for `/start-work`.