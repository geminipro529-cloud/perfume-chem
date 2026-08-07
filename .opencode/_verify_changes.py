"""Verify .opencode/oh-my-openagent.json matches the fast-first routing contract.

Current policy is DeepSeek-V4-Flash on DeepInfra for all categories and agents,
with NO fallback providers.

Run:
    python .opencode/_verify_changes.py
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

fast_model = "deepinfra/deepseek-ai/DeepSeek-V4-Flash"
fast_fallback = []

for c in sorted(required_categories):
    if cats.get(c, {}).get("model") != fast_model:
        errors.append(f"category {c} model: {cats.get(c, {}).get('model')} (expected {fast_model})")
    if cats.get(c, {}).get("fallback_models") != fast_fallback:
        errors.append(
            f"category {c} fallback: {cats.get(c, {}).get('fallback_models')} "
            f"(expected {fast_fallback})"
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
required_agents = [
    "sisyphus",
    "prometheus",
    "sisyphus-junior",
    "oracle",
    "metis",
    "momus",
    "librarian",
    "explore",
    "multimodal-looker",
    "atlas",
    "build",
    "plan",
    "OpenCode-Builder",
]

for a in required_agents:
    if agents.get(a, {}).get("model") != fast_model:
        errors.append(f"agent {a} model: {agents.get(a, {}).get('model')} (expected {fast_model})")
    if agents.get(a, {}).get("fallback_models") != fast_fallback:
        errors.append(
            f"agent {a} fallback: {agents.get(a, {}).get('fallback_models')} "
            f"(expected {fast_fallback})"
        )

if errors:
    print("FAILURES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
