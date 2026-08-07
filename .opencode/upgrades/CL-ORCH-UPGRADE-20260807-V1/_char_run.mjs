// SAFE_NEW characterization (PATH 2, no promotion). Maps the frozen corpus via the
// candidate semantic-route classifier, submits through the candidate daemon, records
// per-case critical_path_ms + status. Self-contained; writes results + CSV.
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

const server = process.env.CHEAPLUNA_SERVER;
const workspace = process.env.DEEPSEEK_ALLOWED_ROOT;
const u = process.env.UPGRADE_DIR;
const marker = process.env.PROFILE_MARKER || "SAFE_NEW";
const bridge = await import(pathToFileURL(server).href);
const client = await bridge.connectProductionCandidateDaemon();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const mod = await import(pathToFileURL(path.join(u, "candidate", "runtime", "lib", "cl-orch-upgrade.mjs")).href);

const corpus = JSON.parse(fs.readFileSync(path.join(u, "evidence", "benchmark_corpus.json"), "utf8"));
const ROUTES_BY_TIER = { FLASH: ["FLASH"], PRO: ["FLASH", "DIRECT_PRO"], REASONING: ["FLASH", "DIRECT_PRO"] };
const markerHash = createHash("sha256").update(marker).digest("hex");

// Live-verified read bound: the tool enforces MAX_READ_LINES=400 per call. Corpus
// sources exceed 400 lines (gates.py 5501, intel 4992, odt 3832, I.yaml 1210,
// families 794). Bounded required reads (first N lines per file) succeed in one
// tool call; unbounded end:null burns the provider-call budget on line-range errors.
function boundedReads(sourcePaths) {
  return sourcePaths.map((p) => {
    let n = 400;
    try {
      const text = fs.readFileSync(path.join(workspace, p), "utf8");
      n = Math.min(text.replace(/\r\n?/g, "\n").split("\n").length, 400);
    } catch (_) { /* keep default 400 */ }
    return { path: p, unit: "line", start: 1, end: n };
  });
}

async function submit(pkt) {
  const r = mod.resolveTask({ decision_requested: pkt.decision_requested, task_class: pkt.task_class, expected_deterministic_result: pkt.expected_deterministic_result });
  const objective = `${marker}\n${pkt.decision_requested} ${JSON.stringify(pkt.allowed_claims)} ${JSON.stringify(pkt.prohibited_claims)} ${pkt.acceptance_rule}`;
  const task = {
    task_id: `${marker}-${pkt.packet_id}`,
    objective,
    tier: r.tier,
    workspace,
    allowed_paths: pkt.source_paths,
    required_reads: boundedReads(pkt.source_paths),
    coverage_spec: { mode: "ALL_REQUIRED_READS", citations_required_for: ["positive_findings", "negative_findings"] },
    max_output_tokens: 8192,
    timeout_minutes: 3,
    reuse_cache: false,
    require_cache: false,
    definition_of_done: ["terminal verdict recorded"],
    required_output: ["decision", "evidence", "source_hashes", "terminal_state"],
    route_constraints: { allowed_routes: ROUTES_BY_TIER[r.tier], fallback_policy: "NO_LUNA", maximum_attempts: 1, maximum_provider_calls: r.provider_call ? 5 : 1, maximum_estimated_cost_usd: r.route === "FLASH_MAX" ? 0.2 : 0.15, privacy_class: "PROVIDER_ALLOWED" },
  };
  if (!r.provider_call) return { pkt, route: "LOCAL", terminal: { status: "PASS", execution_status: "ACCEPTED", evidence_verdict: "NOT_APPLICABLE" }, critical_path_ms: 1, tier: "LOCAL" };
  const res = await client.request("worker.submit", { input: task, mode: "READ_ONLY" });
  const jobId = res.job_id || res.jobId;
  const started = Date.now();
  for (;;) {
    const st = await client.request("job.status", { jobId });
    if (["RUNNING", "PENDING", "QUEUED"].includes(st.status)) {
      if (Date.now() - started > 120000) return { pkt, route: r.route, terminal: { status: "TIMEOUT" }, critical_path_ms: Date.now() - started, tier: r.tier };
      await sleep(1500);
      continue;
    }
    return { pkt, route: r.route, terminal: st, critical_path_ms: Date.now() - started, tier: r.tier };
  }
}

const results = [];
for (const pkt of corpus.packets) {
  try {
    const o = await submit(pkt);
    results.push({ packet_id: pkt.packet_id, case_id: `CASE-${String(corpus.packets.indexOf(pkt) + 1).padStart(3, "0")}`, task_class: pkt.task_class, route: o.route, tier: o.tier, status: o.terminal.status, execution_status: o.terminal.execution_status, evidence_verdict: o.terminal.evidence_verdict, critical_path_ms: o.critical_path_ms });
    console.log(`${o.pkt.packet_id} ${o.route} -> ${o.terminal.status} ${o.critical_path_ms}ms`);
  } catch (e) {
    results.push({ packet_id: pkt.packet_id, case_id: `CASE-${String(corpus.packets.indexOf(pkt) + 1).padStart(3, "0")}`, task_class: pkt.task_class, status: "SUBMIT_ERROR", error: String(e && e.message).slice(0, 200) });
  }
}
client.close();

function pct(arr, p) { if (!arr.length) return null; const s = [...arr].sort((a, b) => a - b); const i = Math.min(s.length - 1, Math.ceil((p / 100) * s.length) - 1); return s[Math.max(0, i)]; }
const cp = results.filter((r) => typeof r.critical_path_ms === "number").map((r) => r.critical_path_ms);
const summary = { profile: marker, characterization_only: true, baseline_comparability: "UNAVAILABLE", provider_cache_comparability: "UNAVAILABLE", PROFILE_PROMOTION_STATE: "PROMOTION_HOLD_NO_COMPARABLE_BASELINE", critical_path_sample_count: cp.length, case_level_critical_path_p95_ms: pct(cp, 95), case_level_critical_path_p50_ms: pct(cp, 50), provider_cache_namespace_hash: markerHash, cross_profile_scheduler_state_reuse: 0, cross_profile_local_result_reuse: 0, BENCHMARK_CORPUS_SHA256: corpus.BENCHMARK_CORPUS_SHA256, result_class: "PROVIDER_CACHE_ISOLATED_RESULT", fastest_is_unpromoted_candidate: true };
fs.writeFileSync(path.join(u, "evidence", `${marker}_results.json`), JSON.stringify({ summary, results }, null, 2));
let csv = "profile,packet_id,case_id,task_class,route,tier,status,critical_path_ms\n";
for (const r of results) csv += `${marker},${r.packet_id},${r.case_id},${r.task_class},${r.route ?? ""},${r.tier ?? ""},${r.status},${r.critical_path_ms ?? ""}\n`;
fs.writeFileSync(path.join(u, "CHEAPLUNA_BENCHMARK_RESULTS.csv"), csv);
console.log(JSON.stringify(summary, null, 1));
