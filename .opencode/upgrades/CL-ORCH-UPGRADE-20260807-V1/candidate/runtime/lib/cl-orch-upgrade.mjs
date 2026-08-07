// Candidate orchestration upgrade module (P2-P5) for CheapLuna.
// Pure, testable orchestration behaviors: semantic routes, deterministic-local
// classifier, invocation identity, stable prompt prefix, resolved-model semantic
// cache key, retry policy, circuit breakers, packet/structured-output contract.
// Does NOT modify the old runtime; the candidate runtime wires this in.

import crypto from "node:crypto";

export const INTERNAL_MODEL_LABEL = "DS-V4-FLASH-3107";
export const ROUTES = Object.freeze({
  LOCAL: { provider_call: false },
  FLASH_FAST: { provider: "deepseek", model: "deepseek-v4-flash", thinking: "disabled", reasoning_effort: null, tier: "FLASH" },
  FLASH_HIGH: { provider: "deepseek", model: "deepseek-v4-flash", thinking: "enabled", reasoning_effort: "high", tier: "PRO" },
  FLASH_MAX: { provider: "deepseek", model: "deepseek-v4-flash", thinking: "enabled", reasoning_effort: "max", tier: "REASONING" },
});

const DETERMINISTIC_KEYWORDS = new Set([
  "sha256", "byte count", "byte_count", "file count", "file_count", "path check", "zip validate", "zip validation",
  "traversal", "duplicate detection", "json", "json schema", "schema validate", "validate schema", "csv validate", "csv validation", "sort", "sorting",
  "git status", "git diff", "shard membership", "test collection", "pytest", "count reconcile", "exact arithmetic",
  "checksum", "hash", "arithmetic",
]);

export function classifyRoute({ decision_requested = "", task_class = "", expected_deterministic_result } = {}) {
  const text = `${decision_requested} ${task_class}`.toLowerCase();
  if (expected_deterministic_result !== undefined && expected_deterministic_result !== null) return "LOCAL";
  for (const k of DETERMINISTIC_KEYWORDS) {
    if (text.includes(k)) return "LOCAL";
  }
  if (task_class === "adversarial_audit" || task_class === "authority_adjudication") return "FLASH_MAX";
  if (["code_review", "test_diagnosis", "schema_review", "authority_comparison", "architecture_comparison", "patch_proposal", "failure_diagnosis", "synthesis"].includes(task_class)) return "FLASH_HIGH";
  return "FLASH_FAST";
}

export function semanticRouteToTier(route) {
  const r = ROUTES[route];
  if (!r) throw new Error(`unsupported semantic route: ${route}`);
  return r.tier ?? (route === "FLASH_FAST" ? "FLASH" : "PRO");
}

export function resolveTask(task) {
  const route = classifyRoute(task);
  if (route === "LOCAL") {
    return { route, provider_call: false, tier: "LOCAL", reasoning_effort: null };
  }
  const spec = ROUTES[route];
  return { route, provider_call: true, tier: spec.tier, reasoning_effort: spec.reasoning_effort, model: spec.model, thinking: spec.thinking };
}

let _seq = 0;
export function nextInvocationId(date = new Date()) {
  const stamp = date.toISOString().slice(0, 10).replace(/-/g, "");
  _seq += 1;
  return `CL-${stamp}-${String(_seq).padStart(6, "0")}`;
}

export function provenanceRecord({ invocation_id, logical_role, parent_invocation_id, packet_id, session_or_job_id, provider, requested_model, resolved_model, thinking_state, reasoning_effort, source_hashes, prompt_hash, output_hash, start_timestamp, end_timestamp, latency_ms, prompt_cache_hit_tokens, prompt_cache_miss_tokens, terminal_state }) {
  return Object.freeze({
    invocation_id, logical_role, parent_invocation_id: parent_invocation_id ?? null, packet_id: packet_id ?? null,
    session_or_job_id: session_or_job_id ?? null, provider, requested_model, resolved_model: resolved_model ?? requested_model,
    internal_model_label: INTERNAL_MODEL_LABEL, thinking_state, reasoning_effort: reasoning_effort ?? null,
    source_hashes: source_hashes ?? [], prompt_hash, output_hash, start_timestamp, end_timestamp, latency_ms,
    prompt_cache_hit_tokens: prompt_cache_hit_tokens ?? 0, prompt_cache_miss_tokens: prompt_cache_miss_tokens ?? 0,
    terminal_state,
  });
}

export function promptPrefix({ governance, scientific_boundary, role, output_schema, sources, task_question, run_id, invocation_id, timestamp, nonce }) {
  const stable = [governance, scientific_boundary, role, output_schema, sources]
    .filter(Boolean)
    .map((x) => (typeof x === "string" ? x : JSON.stringify(x)));
  const volatileParts = [task_question, run_id, invocation_id, timestamp, nonce].filter(Boolean);
  return { stable, volatile: volatileParts, joined: [...stable, ...volatileParts].join("\n") };
}

export function cacheKey({ provider, api_model, returned_model, system_fingerprint, capability_probe_identity_hash, thinking_state, reasoning_effort, governance_prompt_sha256, worker_contract_sha256, output_schema_sha256, ordered_source_hashes, task_contract_version, decision_request_sha256 }) {
  const parts = [provider, api_model, returned_model ?? api_model, system_fingerprint ?? "", capability_probe_identity_hash ?? "", thinking_state, reasoning_effort ?? "", governance_prompt_sha256, worker_contract_sha256, output_schema_sha256, JSON.stringify(ordered_source_hashes ?? []), task_contract_version, decision_request_sha256];
  return crypto.createHash("sha256").update(parts.join("\x1f")).digest("hex");
}

export const RETRY_POLICY = Object.freeze({
  "400": { retries: 0 }, "422": { retries: 0 }, "401": { hold: "AUTHENTICATION_HOLD", retries: 0 }, "402": { hold: "BALANCE_HOLD", retries: 0 },
  "429": { retries: 2, backoff: "exp", jitter: true }, "500": { retries: 1 }, "503": { retries: 2 },
  timeout: { retries: 1, idempotent_only: true }, schema_format: { repairs: 1 }, semantic_corruption: { retries: 0 }, hash_disagreement: { retries: 0 },
});

export const CIRCUIT_TRIGGERS = Object.freeze([
  "semantic_corruption", "source_hash_mismatch", "nested_worker_launch", "worker_invocation_id_collision",
  "canonical_write_attempt", "overlapping_canonical_write_attempt",
]);

export function checkCircuitBreaker(events = {}) {
  for (const t of CIRCUIT_TRIGGERS) {
    if (Number(events[t] ?? 0) >= 1) return { tripped: true, trigger: t };
  }
  return { tripped: false, trigger: null };
}

export const PACKET_SCHEMA = Object.freeze({
  packet_id: "string", decision_requested: "string", logical_role: "string", source_hashes: "array",
  source_material: "string", allowed_claims: "array", prohibited_claims: "array", output_schema: "string",
  abstention_conditions: "array", acceptance_rule: "string", timeout: "number", max_output_tokens: "number",
});

export const RESULT_SCHEMA = Object.freeze({
  decision: "string", evidence: "array", source_hashes: "array", conflicts: "array", unknowns: "array",
  abstention_reason: "string|null", proposed_action: "string|null", confidence_scope: "string", terminal_state: "string",
});
export const TERMINAL_STATES = Object.freeze(["COMPLETE", "VALIDATED", "QUARANTINED", "HOLD", "PARTIAL", "INSUFFICIENT_EVIDENCE", "UNKNOWN"]);

export function validateResult(result) {
  if (!result || typeof result !== "object" || Array.isArray(result)) return { ok: false, code: "STRUCTURED_OUTPUT_SCHEMA_FAIL" };
  for (const [k, t] of Object.entries(RESULT_SCHEMA)) {
    if (!(k in result)) return { ok: false, code: "STRUCTURED_OUTPUT_SCHEMA_FAIL", field: k };
    const v = result[k];
    if (t === "array" && !Array.isArray(v)) return { ok: false, code: "STRUCTURED_OUTPUT_SCHEMA_FAIL", field: k };
    if (t === "string" && typeof v !== "string") return { ok: false, code: "STRUCTURED_OUTPUT_SCHEMA_FAIL", field: k };
    if (t === "string|null" && v !== null && typeof v !== "string") return { ok: false, code: "STRUCTURED_OUTPUT_SCHEMA_FAIL", field: k };
  }
  if (!TERMINAL_STATES.includes(result.terminal_state)) return { ok: false, code: "STRUCTURED_OUTPUT_SCHEMA_FAIL", field: "terminal_state" };
  return { ok: true };
}

export function cacheHitRatio(hit, miss) {
  const d = hit + miss;
  return d > 0 ? hit / d : null;
}
