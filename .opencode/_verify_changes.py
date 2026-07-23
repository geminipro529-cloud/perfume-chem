"""Verify .opencode/oh-my-openagent.json matches the 2026-07-23 cost-effectiveness
routing contract derived from GLM-5.2's review of verified pricing + benchmarks.

Three routing tiers:
- GLM-5.2 on DeepInfra: reasoning slots (best on HLE/AIME/SWE-bench; floor price)
- DeepSeek V4-Flash on DeepInfra: bulk slots (~9x cheaper input than V4-Pro DeepInfra)
- DeepSeek V4-Pro on DeepSeek-native: hard-build slots (2.4x cheaper than DeepInfra-V4-Pro-flex)

Run: python .opencode/_verify_changes.py
"""

import json
import sys

with open(".opencode/oh-my-openagent.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

errors = []

# --- background_task / circuitBreaker gate (unchanged) ---
bt = cfg["background_task"]
if bt["defaultConcurrency"] != 15:
    errors.append(f"background_task.defaultConcurrency: {bt['defaultConcurrency']}")
if bt["maxToolCalls"] != 120:
    errors.append(f"background_task.maxToolCalls: {bt['maxToolCalls']}")
if bt["providerConcurrency"].get("deepinfra") != 12:
    errors.append(f"providerConcurrency.deepinfra: {bt['providerConcurrency']}")
if bt["circuitBreaker"]["maxToolCalls"] != 120:
    errors.append(f"circuitBreaker.maxToolCalls: {bt['circuitBreaker']['maxToolCalls']}")

# --- categories ---
cats = cfg["categories"]
required_categories = {
    "reader",
    "driver",
    "engineer",
    "ultrabrain",
    "deep",
    "quick",
    "artistry",
    "unspecified-low",
    "unspecified-high",
    "visual-engineering",
    "writing",
}
missing_cats = required_categories - set(cats)
if missing_cats:
    errors.append(f"Missing categories: {sorted(missing_cats)}")

# GLM-5.2 primary: heavy reasoning categories.
glm_cats = ["reader", "engineer", "writing", "ultrabrain", "deep"]
# V4-Flash on DeepInfra: cheap bulk categories.
flash_cats = [
    "driver",
    "quick",
    "artistry",
    "unspecified-low",
    "unspecified-high",
    "visual-engineering",
]

glm_model = "deepinfra/zai-org/GLM-5.2"
glm_fallback = ["deepinfra/deepseek-ai/DeepSeek-V4-Pro"]
flash_model = "deepinfra/deepseek-ai/DeepSeek-V4-Flash"
flash_fallback = ["deepinfra/deepseek-ai/DeepSeek-V4-Pro"]

for c in glm_cats:
    if cats.get(c, {}).get("model") != glm_model:
        errors.append(f"category {c} model: {cats.get(c, {}).get('model')} (expected {glm_model})")
    if cats.get(c, {}).get("fallback_models") != glm_fallback:
        errors.append(
            f"category {c} fallback: {cats.get(c, {}).get('fallback_models')} "
            f"(expected {glm_fallback})"
        )

for c in flash_cats:
    if cats.get(c, {}).get("model") != flash_model:
        errors.append(
            f"category {c} model: {cats.get(c, {}).get('model')} (expected {flash_model})"
        )
    if cats.get(c, {}).get("fallback_models") != flash_fallback:
        errors.append(
            f"category {c} fallback: {cats.get(c, {}).get('fallback_models')} "
            f"(expected {flash_fallback})"
        )

# driver.maxTokens and thinking budget preserved
if cats.get("driver", {}).get("maxTokens") != 16000:
    errors.append(f"driver.maxTokens: {cats.get('driver', {}).get('maxTokens')}")
if cats.get("driver", {}).get("thinking", {}).get("budgetTokens") != 8000:
    errors.append(
        f"driver.thinking.budgetTokens: "
        f"{cats.get('driver', {}).get('thinking', {}).get('budgetTokens')}"
    )

# --- agents ---
agents = cfg["agents"]

# Reasoning agents still on GLM-5.2 (DeepInfra), fallback deepinfra/deepseek-v4-pro.
glm_agents = ["sisyphus", "prometheus", "oracle"]
# Bulk agents on DeepInfra V4-Flash, fallback deepinfra/deepseek-v4-pro.
flash_agents = [
    "sisyphus-junior",
    "metis",
    "momus",
    "librarian",
    "explore",
    "multimodal-looker",
    "atlas",
    "OpenCode-Builder",
]
# build / plan on DeepSeek-native V4-Pro (2.4x cheaper than DeepInfra-V4-Pro-flex).
deepseek_native_agents = ["build", "plan"]

deepseek_native_model = "deepseek/deepseek-v4-pro"
deepseek_native_fallback = ["deepinfra/deepseek-ai/DeepSeek-V4-Pro"]

for a in glm_agents:
    if agents.get(a, {}).get("model") != glm_model:
        errors.append(f"agent {a} model: {agents.get(a, {}).get('model')} (expected {glm_model})")
    if agents.get(a, {}).get("fallback_models") != glm_fallback:
        errors.append(
            f"agent {a} fallback: {agents.get(a, {}).get('fallback_models')} "
            f"(expected {glm_fallback})"
        )

for a in flash_agents:
    if agents.get(a, {}).get("model") != flash_model:
        errors.append(f"agent {a} model: {agents.get(a, {}).get('model')} (expected {flash_model})")
    if agents.get(a, {}).get("fallback_models") != flash_fallback:
        errors.append(
            f"agent {a} fallback: {agents.get(a, {}).get('fallback_models')} "
            f"(expected {flash_fallback})"
        )

for a in deepseek_native_agents:
    if agents.get(a, {}).get("model") != deepseek_native_model:
        errors.append(
            f"agent {a} model: {agents.get(a, {}).get('model')} (expected {deepseek_native_model})"
        )
    if agents.get(a, {}).get("fallback_models") != deepseek_native_fallback:
        errors.append(
            f"agent {a} fallback: {agents.get(a, {}).get('fallback_models')} "
            f"(expected {deepseek_native_fallback})"
        )

if errors:
    print("FAILURES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
