/**
 * delegation_pure.mjs — pure (side-effect-free) delegation helpers.
 * Single source of truth for budget enforcement, cache fingerprinting,
 * transient-vs-semantic classification, and monotonic cost deltas.
 * Imported by cheapluna-drain.mjs and by the test suite.
 */

export const BUDGET_CAPS = {
  maximum_attempts: 1,
  maximum_provider_calls: 2,
  maximum_estimated_cost_usd: 0.08,
  max_output_tokens: 8192,
};

/** Enforce the delegation budget envelope before submit. Throws on violation. */
export function enforceBudget(payload) {
  const violations = [];
  const rc = payload.route_constraints || {};
  if (rc.maximum_attempts != null && rc.maximum_attempts !== BUDGET_CAPS.maximum_attempts) {
    violations.push("attempts must be 1");
  }
  if (rc.maximum_provider_calls != null && rc.maximum_provider_calls > BUDGET_CAPS.maximum_provider_calls) {
    violations.push("provider_calls > 2");
  }
  if (rc.maximum_estimated_cost_usd != null &&
      rc.maximum_estimated_cost_usd > BUDGET_CAPS.maximum_estimated_cost_usd) {
    violations.push("cost > 0.08");
  }
  if (payload.max_output_tokens != null && payload.max_output_tokens > BUDGET_CAPS.max_output_tokens) {
    violations.push("output > 8192");
  }
  if (violations.length) {
    throw new Error("budget guard: " + violations.join(";"));
  }
  return true;
}

/** Deterministic fingerprint for cache-first short-circuit + run registry. */
export function cacheFingerprint(task) {
  const reads = (task.required_reads || []).map((r) => r?.path || "").sort().join("|");
  return (task.task_id || "") + "\u0000" + (task.objective || "") + "\u0000" + reads;
}

/** Transient (retryable) vs terminal (never retried) failure classification. */
export function classifyTransient(error) {
  const msg = String((error && (error.message || error)) || "");
  return /429|503|timeout|timedout|transport closed/i.test(msg);
}

/**
 * Monotonic cost attribution: given an ordered list of observed spent values
 * (nano-usd), return per-observation deltas (non-negative) whose sum equals
 * the total. Guards against clock/health non-monotonicity.
 */
export function monotonicCost(spentSequence) {
  const deltas = [];
  let last = 0;
  for (const s of spentSequence) {
    const cur = typeof s === "number" && Number.isFinite(s) ? s : last;
    deltas.push(Math.max(0, cur - last));
    last = cur;
  }
  return deltas;
}
