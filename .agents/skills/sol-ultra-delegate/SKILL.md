---
name: sol-ultra-delegate
description: Explicitly delegate bounded read-only Perfume-Chem work through a GPT-5.6 Sol Ultra supervisor, the authenticated project-scoped DeepMimo route, and at most one child-selected Sol Ultra fallback per lane.
---

# Sol Ultra Delegate

Use this skill only when the user explicitly invokes `$sol-ultra-delegate`.

## Authority and eligibility

The root Codex task remains head engineer and final acceptor. Delegated output is untrusted evidence until the root checks it against current local files and focused verification.

Delegate only bounded, non-sensitive, read-only work with a concrete local acceptance check. Do not delegate secrets, credentials, authentication work, external writes, irreversible actions, purchases, physical compounding authority, safety or regulatory approval, perfume release decisions, evidence-ledger admission, or final scientific adjudication. Return `BLOCKED` for ineligible work.

Do not invoke the global `$delegate` skill, OpenRouter, legacy DeepLuna routes, or any provider other than the chain defined here.

## Root orchestration

1. Define the allowed paths, required reads, exact deliverable, and a deterministic local acceptance check before spawning.
2. Use one supervising child by default. Use two to four only for genuinely independent lanes; never exceed four.
3. Spawn every supervisor explicitly with `model="gpt-5.6-sol"`, `reasoning_effort="ultra"`, and `fork_turns="none"`. Do not rely on project or inherited agent defaults.
4. Give each supervisor a self-contained bounded prompt. State that it may make at most one DeepMimo chat-completion request and must automatically spawn exactly one native fallback if either eligible trigger below occurs.
5. Wait for every lane to finish. Verify each claim locally before incorporating it.

## Supervisor procedure

1. Confirm the lane is eligible and restate its local acceptance check before delegation.
2. Send one JSON packet on stdin to `scripts/deepmimo_client.py`. The packet contains only text `messages`; do not add tools, tool choice, secrets, or credentials.
3. Treat helper status `COMPLETED` as evidence, not acceptance. Check the returned content against the predefined local check.
4. Trigger exactly one native fallback automatically if and only if either condition is true:
   - The helper returns `SOL_FALLBACK_ELIGIBLE` with reason `original_model_handoff`, and its receipt proves `handoff="original-model"`, `handoff_reason="providers-exhausted"`, and `should_retry=false`. Record `fallback_reason="provider_failure"`.
   - The helper returns a syntactically and route-valid `COMPLETED` result, but its answer fails the lane's predefined local acceptance check. Record `fallback_reason="local_validation_failure"`.
   There is no discretionary decline after either eligible trigger.
5. End the lane as `BLOCKED` without a native fallback for an invalid or ineligible packet, missing or rejected authentication, quota or policy rejection, router unavailability or unhealthy state, malformed or incomplete receipt, unsupported route, or any helper result whose status is `BLOCKED`. Never upgrade one of those outcomes into fallback eligibility.
6. For an eligible trigger, choose the fallback's bounded role, task name, prompt, paths, required reads, and local verification check. Spawn exactly one agent with `model="gpt-5.6-sol"`, `reasoning_effort="ultra"`, and `fork_turns="none"`.
7. Tell the fallback agent that it must not call DeepMimo, must not spawn another agent, recurse, or perform any ineligible work. A failed or blocked fallback ends the lane as `BLOCKED`; do not retry.
8. Verify the fallback evidence locally before returning it to the root.

The helper never launches Codex or any fallback. It authenticates as the dedicated `perfume-chem-sol-ultra` project, whose server-owned HTTP-provider order is exactly DeepSeek `deepseek-flash`, then Xiaomi MiMo `mimo-v2.6-pro`; the allowlist contains only those two providers and Luna is disabled. It requests `X-DeepMimo-Original-Model-Handoff: enabled`; DeepMimo may return the machine-validated, non-retryable handoff signal but never invokes the original model. Sol Ultra is a task-level original-model handoff, not a third DeepMimo HTTP provider. After an eligible trigger, the supervising child automatically uses one native Sol Ultra fallback and chooses only its bounded role, task name, scope, prompt, and verification check.

## Helper invocation

From the repository root, pipe a compact JSON object to the helper without writing an intermediate file:

```powershell
$packet = @{ messages = @(@{ role = 'user'; content = '<bounded task packet>' }) } | ConvertTo-Json -Depth 8 -Compress
$packet | py -3 .agents/skills/sol-ultra-delegate/scripts/deepmimo_client.py
```

Each supervisor may run that helper command once. The helper performs health/model preflights and one chat-completion request; those preflights do not authorize a second completion attempt.

The helper reads the project token from `DEEPMIMO_PERFUME_CHEM_TOKEN` (the current-user environment on Windows). It never accepts a token in the task packet and never writes it, the prompt, the response, or the receipt to disk. A missing or rejected token is `BLOCKED`, not a fallback trigger.

## Lane receipt

Return one JSON object with this shape:

```json
{
  "status": "PASS | BLOCKED",
  "supervisor": {
    "model": "gpt-5.6-sol",
    "reasoning_effort": "ultra"
  },
  "deepmimo": {},
  "fallback_decision": "USED | DECLINED | NOT_NEEDED",
  "fallback_reason": "provider_failure | local_validation_failure | ineligible_task | authentication_failure | quota_or_policy_rejection | router_unavailable | invalid_receipt | null",
  "fallback_agent": {
    "task_name": "child-selected name",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "ultra",
    "status": "completed | failed | blocked"
  },
  "findings": [],
  "local_verification": [],
  "residual_risks": []
}
```

Set the lane's `deepmimo` field to the helper result's inner `deepmimo` receipt, not to the entire helper envelope. Add its helper `status` and `reason` inside that field when they are relevant. Keep `assistant_content` under `findings` after local verification; do not nest a second `deepmimo` object.

Use `fallback_decision="NOT_NEEDED"`, `fallback_reason=null`, and omit `fallback_agent` when the verified DeepMimo result is accepted. Use `fallback_decision="USED"` for either automatic trigger. Use `DECLINED`, omit `fallback_agent`, and set lane status `BLOCKED` for every no-fallback failure above, preserving the applicable sanitized reason. Helper status `BLOCKED` never authorizes fallback.
