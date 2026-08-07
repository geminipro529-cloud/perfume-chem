// Offline unit validation of the candidate orchestration upgrade module (P5B).
import { pathToFileURL } from "node:url";
const m = await import(pathToFileURL(process.argv[2]).href);
let pass = 0, fail = 0;
function check(name, cond) { if (cond) { pass++; } else { fail++; console.log("FAIL: " + name); } }

// 1. routing: deterministic-local
check("det_json_parse_local", m.classifyRoute({ decision_requested: "parse this json and validate schema", task_class: "schema_review" }) === "LOCAL");
check("det_sha_local", m.classifyRoute({ decision_requested: "compute sha256 and byte count", task_class: "source_discovery" }) === "LOCAL");
check("det_expected_local", m.classifyRoute({ decision_requested: "anything", task_class: "code_review", expected_deterministic_result: "42" }) === "LOCAL");
// 2. semantic routes
check("max_adversarial", m.classifyRoute({ decision_requested: "audit the gate for weaknesses", task_class: "adversarial_audit" }) === "FLASH_MAX");
check("high_code_review", m.classifyRoute({ decision_requested: "review the function", task_class: "code_review" }) === "FLASH_HIGH");
check("fast_discovery", m.classifyRoute({ decision_requested: "which materials are present", task_class: "source_discovery" }) === "FLASH_FAST");
// 3. resolveTask
const t = m.resolveTask({ decision_requested: "review", task_class: "code_review" });
check("resolve_high_tier", t.tier === "PRO" && t.reasoning_effort === "high" && t.thinking === "enabled");
const tl = m.resolveTask({ decision_requested: "sort this list", task_class: "source_discovery" });
check("resolve_local_no_call", tl.route === "LOCAL" && tl.provider_call === false);
// 4. invocation ids unique + format
const ids = new Set();
for (let i = 0; i < 100; i++) ids.add(m.nextInvocationId());
check("invocation_unique_100", ids.size === 100);
check("invocation_format", [...ids][0].startsWith("CL-") && /^CL-\d{8}-\d{6}$/.test([...ids][0]));
// 5. prompt prefix stable-first
const p = m.promptPrefix({ governance: "GOV", scientific_boundary: "SCI", role: "ROLE", output_schema: "SCHEMA", sources: "SRC", task_question: "Q", run_id: "R", invocation_id: "I", timestamp: "T", nonce: "N" });
check("prefix_stable_before_volatile", p.stable.length === 5 && p.volatile.length === 5);
check("prefix_order", p.joined.indexOf("GOV") === 0 && p.joined.indexOf("Q") > p.joined.indexOf("SCHEMA"));
// 6. semantic cache key: content-addressed, excludes volatile
const k1 = m.cacheKey({ provider: "deepseek", api_model: "deepseek-v4-flash", returned_model: "deepseek-v4-flash", system_fingerprint: "fp_x", capability_probe_identity_hash: "h", thinking_state: "enabled", reasoning_effort: "high", governance_prompt_sha256: "g", worker_contract_sha256: "w", output_schema_sha256: "o", ordered_source_hashes: ["a", "b"], task_contract_version: "v1", decision_request_sha256: "d" });
const k2 = m.cacheKey({ provider: "deepseek", api_model: "deepseek-v4-flash", returned_model: "deepseek-v4-flash", system_fingerprint: "fp_x", capability_probe_identity_hash: "h", thinking_state: "enabled", reasoning_effort: "high", governance_prompt_sha256: "g", worker_contract_sha256: "w", output_schema_sha256: "o", ordered_source_hashes: ["a", "b"], task_contract_version: "v1", decision_request_sha256: "d" });
check("cachekey_deterministic", k1 === k2);
const k3 = m.cacheKey({ provider: "deepseek", api_model: "deepseek-v4-flash", returned_model: "deepseek-v4-flash", system_fingerprint: "fp_y", capability_probe_identity_hash: "h", thinking_state: "enabled", reasoning_effort: "high", governance_prompt_sha256: "g", worker_contract_sha256: "w", output_schema_sha256: "o", ordered_source_hashes: ["a", "b"], task_contract_version: "v1", decision_request_sha256: "d" });
check("cachekey_sensitive_to_model_identity", k1 !== k3);
// 7. retry policy
check("retry_429_2", m.RETRY_POLICY["429"].retries === 2);
check("retry_400_0", m.RETRY_POLICY["400"].retries === 0);
check("retry_401_hold", m.RETRY_POLICY["401"].hold === "AUTHENTICATION_HOLD");
// 8. circuit breaker
check("circuit_trip", m.checkCircuitBreaker({ semantic_corruption: 1 }).tripped === true);
check("circuit_clean", m.checkCircuitBreaker({}).tripped === false);
// 9. result schema validation
check("result_ok", m.validateResult({ decision: "x", evidence: [], source_hashes: [], conflicts: [], unknowns: [], abstention_reason: null, proposed_action: null, confidence_scope: "local", terminal_state: "COMPLETE" }).ok === true);
check("result_missing_field", m.validateResult({ decision: "x" }).ok === false);
check("result_bad_terminal", m.validateResult({ decision: "x", evidence: [], source_hashes: [], conflicts: [], unknowns: [], abstention_reason: null, proposed_action: null, confidence_scope: "local", terminal_state: "BOGUS" }).ok === false);
// 10. cache hit ratio
check("ratio_0_denom_null", m.cacheHitRatio(0, 0) === null);
check("ratio_half", m.cacheHitRatio(50, 50) === 0.5);
// 11. provenance record
const pr = m.provenanceRecord({ invocation_id: "CL-1", logical_role: "TEST_SCOUT", provider: "deepseek", requested_model: "deepseek-v4-flash", thinking_state: "enabled", reasoning_effort: "high", source_hashes: ["a"], prompt_hash: "p", output_hash: "o", start_timestamp: 1, end_timestamp: 2, latency_ms: 1, terminal_state: "COMPLETE" });
check("provenance_label", pr.internal_model_label === "DS-V4-FLASH-3107");

console.log(JSON.stringify({ PASS: pass, FAIL: fail }));
process.exit(fail > 0 ? 1 : 0);
