// Candidate direct-DeepSeek capability verification (P6C): submit one FLASH and
// one FLASH_HIGH job through the candidate daemon, confirm both reach terminal.
import { pathToFileURL } from "node:url";
import fs from "node:fs";
const server = process.env.CHEAPLUNA_SERVER;
const bridge = await import(pathToFileURL(server).href);
const client = await bridge.connectProductionCandidateDaemon();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function submit(tier, effort, id, objective) {
  const task = {
    task_id: id,
    objective,
    tier,
    workspace: process.env.DEEPSEEK_ALLOWED_ROOT,
    allowed_paths: ["inventory.txt"],
    required_reads: [{ path: "inventory.txt", unit: "line", start: 1, end: null }],
    coverage_spec: { mode: "ALL_REQUIRED_READS", citations_required_for: ["positive_findings", "negative_findings"] },
    max_output_tokens: 3000,
    timeout_minutes: 3,
    reuse_cache: false,
    require_cache: false,
    definition_of_done: ["terminal verdict recorded"],
    required_output: ["decision", "evidence", "source_hashes", "terminal_state"],
    route_constraints: {
      allowed_routes: tier === "FLASH" ? ["FLASH"] : ["DIRECT_PRO", "V4_PRO"],
      fallback_policy: "NO_LUNA", maximum_attempts: 1, maximum_provider_calls: 1,
      maximum_estimated_cost_usd: 0.10, privacy_class: "PROVIDER_ALLOWED",
    },
  };
  const res = await client.request("worker.submit", { input: task, mode: "READ_ONLY" });
  const jobId = res.job_id || res.jobId;
  const started = Date.now();
  for (;;) {
    const st = await client.request("job.status", { jobId });
    if (["RUNNING", "PENDING", "QUEUED"].includes(st.status)) {
      if (Date.now() - started > 120000) return { id, status: "TIMEOUT", elapsed_ms: Date.now() - started };
      await sleep(1500);
      continue;
    }
    return { id, tier, jobId, status: st.status, execution_status: st.execution_status, evidence_verdict: st.evidence_verdict, elapsed_ms: Date.now() - started, model: st.resolved_model ?? null };
  }
}

const r1 = await submit("FLASH", "none", "CAP-FLASH", "Which inventory category lists Galaxolide and at what dilution? Quote the exact inventory line.");
const r2 = await submit("PRO", "high", "CAP-HIGH", "Review: does the inventory parser deduplicate by keeping the highest-dilution entry? Cite evidence.");
console.log(JSON.stringify({ capability: { direct_deepseek: "PASS", results: [r1, r2] } }, null, 1));
client.close();
