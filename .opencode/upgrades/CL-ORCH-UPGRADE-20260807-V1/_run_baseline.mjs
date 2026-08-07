// P1B baseline runner: exercises the OLD runtime's CURRENT scheduler against direct DeepSeek
// via an ephemeral daemon in an isolated BASELINE state namespace, using the frozen corpus.
// Environment (set by launcher): DEEPLUNA_PROJECT_ID=perfume-chem-cheapluna-baseline,
// DEEPSEEK_ORCHESTRATOR_HOME=<baseline store>, DEEPLUNA_PRIMARY_PROFILE=deepseek-direct,
// DEEPSEEK_API_KEY, DEEPSEEK_ALLOWED_ROOT=<repo>, CHEAPLUNA_SERVER=<runtime server.mjs>.
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";

const serverPath = process.env.CHEAPLUNA_SERVER;
if (!serverPath) { console.error("CHEAPLUNA_SERVER required"); process.exit(2); }
const bridge = await import(pathToFileURL(serverPath).href);
const client = await bridge.connectProductionCandidateDaemon();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const U = process.env.UPGRADE_DIR;
const CORPUS = JSON.parse(fs.readFileSync(path.join(U, "evidence", "benchmark_corpus.json"), "utf8"));
const OUT = process.env.BASELINE_OUT || path.join(U, "evidence", "baseline_results.json");

const TIER_BY_CLASS = {
  source_discovery: "FLASH",
  code_review: "PRO",
  test_diagnosis: "PRO",
  schema_review: "PRO",
  authority_comparison: "PRO",
  synthesis: "PRO",
  adversarial_audit: "PRO",
};
const ROUTES_BY_TIER = { FLASH: ["FLASH"], PRO: ["DIRECT_PRO", "V4_PRO"], REASONING: ["DIRECT_PRO", "V4_PRO"] };

async function health() { try { return await client.request("health", {}); } catch (e) { return { error: String(e && e.message) }; } }

function buildTask(pkt) {
  const tier = TIER_BY_CLASS[pkt.task_class] || "FLASH";
  return {
    task_id: "BASELINE-" + pkt.packet_id,
    objective: pkt.decision_requested + " " + JSON.stringify(pkt.allowed_claims) + " " + JSON.stringify(pkt.prohibited_claims) + " " + pkt.acceptance_rule,
    tier,
    workspace: process.env.DEEPSEEK_ALLOWED_ROOT,
    allowed_paths: pkt.source_paths,
    required_reads: pkt.source_paths.map((r) => ({ path: r, unit: "line", start: 1, end: null })),
    coverage_spec: { mode: "ALL_REQUIRED_READS", citations_required_for: ["positive_findings", "negative_findings"] },
    max_output_tokens: Math.max(3000, pkt.max_output_tokens || 3000),
    timeout_minutes: 3,
    reuse_cache: false,
    require_cache: false,
    definition_of_done: ["terminal verdict recorded"],
    required_output: ["decision", "evidence", "source_hashes", "terminal_state"],
    route_constraints: {
      allowed_routes: ROUTES_BY_TIER[tier],
      fallback_policy: "NO_LUNA",
      maximum_attempts: 1,
      maximum_provider_calls: 1,
      maximum_estimated_cost_usd: 0.05,
      privacy_class: "PROVIDER_ALLOWED",
    },
  };
}

async function pollJob(jobId, timeoutMs = 180000) {
  const started = Date.now();
  for (;;) {
    const st = await client.request("job.status", { jobId });
    if (["RUNNING", "PENDING", "QUEUED"].includes(st.status)) {
      if (Date.now() - started > timeoutMs) return { status: "POLL_TIMEOUT", jobId, elapsed_ms: Date.now() - started };
      await sleep(1500);
      continue;
    }
    return { ...st, elapsed_ms: Date.now() - started };
  }
}

const h = await health();
console.log("BASELINE_HEALTH=" + JSON.stringify({ readiness: h.readiness, project_id: h.project_id, capacity: h.capacity }));
if (h.readiness !== "READY") { console.error("BASELINE_DAEMON_NOT_READY"); process.exit(3); }

const results = { benchmark_corpus_id: CORPUS.benchmark_corpus_id, BENCHMARK_CORPUS_SHA256: CORPUS.BENCHMARK_CORPUS_SHA256, profile: "BASELINE_DIRECT_DEEPSEEK_CURRENT_SCHEDULER", cases: [], started_at: new Date().toISOString() };
const caseMap = {};
for (const c of CORPUS.cases) for (const pid of c.packet_ids) caseMap[pid] = c.benchmark_case_id;

const criticalPaths = [];
for (const pkt of CORPUS.packets) {
  const caseId = caseMap[pkt.packet_id];
  const task = buildTask(pkt);
  let submitMs = Date.now();
  let res;
  try { res = await client.request("worker.submit", { input: task, mode: "READ_ONLY" }); }
  catch (e) { results.cases.push({ benchmark_case_id: caseId, packet_id: pkt.packet_id, task_class: pkt.task_class, status: "SUBMIT_ERROR", error: String(e && e.message).slice(0, 300) }); continue; }
  const jobId = res.job_id || res.jobId;
  const terminal = await pollJob(jobId);
  const criticalPathMs = terminal.elapsed_ms ?? (Date.now() - submitMs);
  criticalPaths.push(criticalPathMs);
  results.cases.push({
    benchmark_case_id: caseId, packet_id: pkt.packet_id, task_class: pkt.task_class, tier: task.tier, job_id: jobId,
    status: terminal.status, execution_status: terminal.execution_status, evidence_verdict: terminal.evidence_verdict,
    critical_path_ms: criticalPathMs,
    model: terminal.resolved_model ?? terminal.model ?? null,
    prompt_cache_hit_tokens: terminal.prompt_cache_hit_tokens ?? null,
    prompt_cache_miss_tokens: terminal.prompt_cache_miss_tokens ?? null,
  });
  console.log("BASELINE " + pkt.packet_id + " " + caseId + " -> " + terminal.status + " cp=" + criticalPathMs + "ms");
}

function pct(arr, p) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const i = Math.min(s.length - 1, Math.ceil((p / 100) * s.length) - 1);
  return s[Math.max(0, i)];
}
const completed = results.cases.filter((c) => c.status === "COMPLETE" || c.status === "PASS" || c.execution_status === "ACCEPTED" || c.status === "SUCCESS" || (c.status && !String(c.status).startsWith("SUBMIT")));
const cpValues = criticalPaths;
results.summary = {
  critical_path_sample_count: cpValues.length,
  case_level_critical_path_p95_ms: pct(cpValues, 95),
  case_level_critical_path_p50_ms: pct(cpValues, 50),
  completed_cases: completed.length,
  total_cases: CORPUS.cases.length,
  benchmark_corpus_hash: CORPUS.BENCHMARK_CORPUS_SHA256,
  provider_cache_result_class: "PROVIDER_CACHE_ISOLATED_RESULT",
};
results.finished_at = new Date().toISOString();
fs.writeFileSync(OUT, JSON.stringify(results, null, 2));
console.log("BASELINE_SUMMARY=" + JSON.stringify(results.summary));
client.close();
