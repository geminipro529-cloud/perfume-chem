---
name: provider-routing
description: Cost-benefit tier decision matrix for model routing in perfume-chem sessions
---

## Tier Structure (verified 2026-07-23)

Pricing fetched live from `api-docs.deepseek.com/quick_start/pricing` and
`deepinfra.com/pricing`. IQ scores from Artificial Analysis Intelligence Index v4.1.

All $/Mtok figures are **standard tier**. DeepInfra flex = ×0.8; DeepInfra priority = ×1.5.
DeepSeek-native has no service tier — cache-hit pricing applies automatically based on prompt prefix reuse.

| Tier | Model | IQ | Input $/Mtok (cache miss / hit) | Output $/Mtok | Context | Role |
|---|---|---|---|---|---|---|
| 0A | `deepinfra/deepseek-v4-flash` | 40 | $0.09 / $0.018 | $0.18 | 1M | Bulk reads, grep over inventory, file extraction, pipeline brute-force |
| 0B | `deepseek/deepseek-v4-pro` (DeepSeek-native) | 44 | $0.435 / $0.003625 | $0.87 | 1M | Hard build/plan slots — 2.4× cheaper than DeepInfra-V4-Pro-flex on cache miss |
| 1 | `deepinfra/deepseek-v4-flash` (standard, enabling) | 40 | $0.09 / $0.018 | $0.18 | 1M | Orchestrator bulk traffic, pipeline gate runs, subagent shells |
| 2 | `deepinfra/zai-org/GLM-5.2` (flex preferred) | 51 | $0.95 / $0.18 → flex $0.76 / $0.144 | $3.00 → flex $2.40 | 1.05M | Head perfumer/scientist/engineer. First-pass formula, final gate, reader/engineer/writing/deep/ultrabrain slots |
| 3 | `deepseek/deepseek-v4-pro` (priority) | 44 | $0.435 / $0.003625 | $0.87 | 1M | Reserved as Tier 2 fallback — GLM aborts twice → escalate. Same model as Tier 0B but with priority scheduling intent. |

Benchmarks (Hugging Face GLM-5.2 card, DeepSeek-V3.2 paper) justifying the
GLM-5.2 reasoning assignment: HLE 40.5 vs V4-Pro 37.7; AIME 2026 99.2 vs 94.6; SWE-bench Pro 62.1 vs 55.4; GPQA Diamond 91.2 vs 90.1.

## Slot Routing (matches `.opencode/oh-my-openagent.json`)

| Model | Categories | Agents |
|---|---|---|
| `deepinfra/zai-org/GLM-5.2` | reader, engineer, writing, ultrabrain, deep | sisyphus, prometheus, oracle |
| `deepinfra/deepseek-v4-flash` | driver, quick, artistry, unspecified-low, unspecified-high, visual-engineering | sisyphus-junior, metis, momus, librarian, explore, multimodal-looker, atlas, OpenCode-Builder |
| `deepseek/deepseek-v4-pro` (DeepSeek-native) | — | build, plan |

Verifiable via `python .opencode/_verify_changes.py` → must print "ALL CHECKS PASSED".

## Trigger Table

| User message pattern | Route to | Max/session |
|---|---|---|
| "what is hedione?" | Tier 0A | unlimited |
| "what about this Explorer variant's heart?" | Tier 0B | unlimited |
| "build a formula for X" | Tier 2 | 1-2x |
| "run the gate on X" | Tier 1 | unlimited |
| "fix this bug" (mechanical code) | Tier 1 | unlimited |
| "re-check osmanthus OAV" (perfumer judgment) | Tier 2 | 1-2x |
| 2+ failed fix attempts | Tier 2 | 1-2x |
| Tier 2 aborts 2x | Tier 3 | <1x weekly |

## Hard Rules

1. Flash NEVER makes perfumer decisions. Escalate to Tier 2.
2. Tier 2 invoked 1-2x max per session unless routed through `engine.llm_cache.cached_chat` (where cache hits are free).
3. Tier 3 only when Tier 2 aborts twice.
4. Tier 2 gates use FLEX tier (×0.8) per user directive — `service_tier="flex"` in cached_chat.
5. Flash is OK for pipeline brute-force testing (user explicit).
6. Bulk slots (Tier 0A / Tier 1) MUST use `engine.llm_cache.cached_chat` for any read that might repeat — identical YAML/JSON extractions, gate runs on unchanged formulas, etc. Cache hits cost $0; misses at Tier 0A are ~$0.009 per 100K tokens. No excuse for a cache-miss on a repeat.

## Service Tier

| Condition | Default | Escalate |
|---|---|---|
| User chatting | Tier 0A | Tier 0B if quality dip |
| Formula construction | Tier 2 (flex) | Priority if user waiting |
| Pipeline gate (async) | Tier 1 | Priority only on critical block |
| GLM-5.2 final gate | flex | Standard only if user waiting |
| V4 Pro build/plan (Tier 0B) | DeepSeek-native auto | Fall back to DeepInfra-V4-Pro if DeepSeek-native 429 / 5xx |

## Local Response Cache (engine.llm_cache)

In addition to the provider's own prefix-cache hit pricing (above), the workspace
ships a SQLite-backed local response cache that skips the API call entirely on
duplicate calls. Cost-reduction surface:

| Mechanism | Where | Savings |
|---|---|---|
| Local response cache | `engine/llm_cache.py` → `cache/llm_cache.db` | Identical calls = $0 after first |
| Prompt-prefix normalization | `_normalize_messages` hoists system-first; `_normalize_tools` sorts tool defs | Triggers provider cache-hit pricing (DeepSeek-native V4-Pro: 120× cheaper cached input; DeepInfra ×5–13) |
| Savings ledger | `cache/llm_cache_ledger.jsonl` | Per-call $ saved aggregated in `get_stats()` |
| CLI stats | `python scripts/llm_cache_stats.py stats` | Hit rate + est savings + per-model breakdown |
| CLI clear | `python scripts/llm_cache_stats.py clear --older-than 30d` | Evict stale rows |
| TTL expiry | Per-row `ttl_days=7` default | Backdate or `ttl_days=0` (never expires) |
| Temperature gate | Only `temperature=0` cached by default | Use `force_cache=True` to override (not recommended for T>0) |

Calling pattern — every Python hook into a paid model MUST go through this:

```python
from engine.llm_cache import cached_chat

resp = cached_chat(
    provider="deepinfra",  # or "deepseek" for DeepSeek-native
    model="zai-org/GLM-5.2",
    messages=[{"role": "system", "content": "..."},
              {"role": "user", "content": "..."}],
    temperature=0.0,
    max_tokens=4000,
    service_tier="flex",  # DeepInfra only; DeepSeek-native ignores
    thinking_mode="enabled",  # auto / enabled / disabled
    ttl_days=7,
)
content = resp["choices"][0]["message"]["content"]
```

Repeating the same call returns instantly from SQLite — provider is NOT contacted.