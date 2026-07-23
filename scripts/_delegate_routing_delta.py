"""One-shot delegation: ask GLM-5.2 for the exact JSON delta to apply to
.opencode/oh-my-openagent.json based on the verified pricing evidence.

First run = cache miss (paid). Re-running with the same prompt = cache hit (free).
"""

from __future__ import annotations

import json
import pathlib
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.llm_cache import cached_chat

CURRENT_CONFIG = pathlib.Path(_REPO_ROOT / ".opencode/oh-my-openagent.json").read_text(
    encoding="utf-8"
)

PROMPT = f"""You are GLM-5.2, the head reasoning model for a perfume-chemistry workspace on DeepInfra + DeepSeek-native.

TASK: Produce the EXACT JSON delta to apply to .opencode/oh-my-openagent.json so the slot routing matches the verified cost-effectiveness spec below. Output ONLY a JSON object with this shape — no prose, no markdown:

{{
  "categories_replace": {{"<slot_name>": {{"model": "<provider/model>", "fallback_models": ["<provider/model>"], "maxTokens": <int>, "thinking": {{"type": "<enabled|disabled>", "budgetTokens": <int>}}}}}},
  "agents_replace": {{"<agent_name>": {{"model": "<provider/model>", "fallback_models": ["<provider/model>"]}}}},
  "rationale": "<one short sentence>"
}}

VERIFIED PRICING (2026-07-23, fetched from api-docs.deepseek.com and deepinfra.com/pricing):
- DeepSeek-native V4-Pro: $0.435 input / $0.87 output per 1M tokens, cache-hit input $0.003625. 1M context. 500 concurrency.
- DeepSeek-native V4-Flash: $0.14 / $0.28, cache-hit $0.0028. 1M context. 2500 concurrency.
- DeepInfra V4-Pro standard: $1.30 / $2.60, cache-hit $0.10. Flex (0.8x) = $1.04 / $2.08.
- DeepInfra V4-Flash standard: $0.09 / $0.18, cache-hit $0.018. Flex = $0.072 / $0.144.
- DeepInfra GLM-5.2 standard: $0.95 / $3.00, cache-hit $0.18. Flex = $0.76 / $2.40.

BENCHMARKS (verified from Hugging Face GLM-5.2 card + DeepSeek-V3.2 paper):
- GLM-5.2 beats V4-Pro on HLE (40.5 vs 37.7), AIME 2026 (99.2 vs 94.6), SWE-bench Pro (62.1 vs 55.4), GPQA Diamond (91.2 vs 90.1).
- V4-Pro wins HMMT Feb 2026 narrowly (95.2 vs 92.5).

REQUIRED ROUTING DECISIONS (apply these literally):
1. KEEP on deepinfra/zai-org/GLM-5.2 with fallback ["deepinfra/deepseek-v4-pro"]: categories reader, engineer, writing, ultrabrain, deep; agents sisyphus, prometheus, oracle.
2. MOVE to deepinfra/deepseek-v4-flash with fallback ["deepinfra/deepseek-v4-pro"]: categories driver, quick, artistry, unspecified-low, unspecified-high, visual-engineering; agents sisyphus-junior, metis, momus, librarian, explore, multimodal-looker, atlas, OpenCode-Builder.
3. MOVE to deepseek/deepseek-v4-pro (DeepSeek-native, 2.4x cheaper than DeepInfra V4-Pro) with fallback ["deepinfra/deepseek-v4-pro"]: agents build, plan.
4. Preserve all other config fields (maxToolCalls=120, circuitBreaker, defaultConcurrency=15, providerConcurrency, etc.) — do NOT include them in the delta.
5. For each category in group 2, preserve the existing maxTokens and thinking settings; only change model + fallback_models.
6. For each agent in groups 2 and 3, only change model + fallback_models; preserve any other fields.

CURRENT .opencode/oh-my-openagent.json (categories + agents blocks only):

{CURRENT_CONFIG}
"""

response = cached_chat(
    provider="deepinfra",
    model="zai-org/GLM-5.2",
    messages=[
        {
            "role": "system",
            "content": "You are GLM-5.2, a reasoning model. Output only valid JSON — no markdown fences, no prose.",
        },
        {"role": "user", "content": PROMPT},
    ],
    temperature=0.0,
    max_tokens=8000,
    top_p=1.0,
    thinking_mode="enabled",
    service_tier="flex",
    ttl_days=30,
    response_format={"type": "json_object"},
)

content = response["choices"][0]["message"]["content"]
usage = response.get("usage", {})

print("=== GLM-5.2 RESPONSE ===")
print(content)
print("=== USAGE ===")
print(json.dumps(usage, indent=2))

# Persist for the apply step
out_path = _REPO_ROOT / "archive" / "glm_routing_delta.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(content, encoding="utf-8")
print(f"=== SAVED TO {out_path} ===")
