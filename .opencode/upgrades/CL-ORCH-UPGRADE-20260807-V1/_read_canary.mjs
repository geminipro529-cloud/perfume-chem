// P6D READ-integrity canary: host creates unpredictable controlled bytes + nonce,
// submits a controlled READ_ONLY packet through the candidate daemon, and verifies
// the returned content reproduces the exact nonce (byte identity, no substitution).
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const server = process.env.CHEAPLUNA_SERVER;
const workspace = process.env.DEEPSEEK_ALLOWED_ROOT;
const bridge = await import(pathToFileURL(server).href);
const client = await bridge.connectProductionCandidateDaemon();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const nonce = "NONCE-" + crypto.randomBytes(16).toString("hex");
const canaryPath = path.join(workspace, ".opencode", "upgrades", "CL-ORCH-UPGRADE-20260807-V1", "evidence", "_read_canary.txt");
fs.writeFileSync(canaryPath, nonce, "utf8");
const expectedSha = crypto.createHash("sha256").update(nonce, "utf8").digest("hex");
const rel = path.relative(workspace, canaryPath).replace(/\\/g, "/");

const task = {
  task_id: "READ-CANARY",
  objective: `Report verbatim the exact single string contained in the file ${rel}. Output the string inside double quotes and nothing else.`,
  tier: "FLASH",
  workspace,
  allowed_paths: [rel],
  required_reads: [{ path: rel, unit: "line", start: 1, end: 1 }],
  coverage_spec: { mode: "ALL_REQUIRED_READS", citations_required_for: ["positive_findings", "negative_findings"] },
  max_output_tokens: 8192,
  timeout_minutes: 3,
  reuse_cache: false,
  require_cache: false,
  definition_of_done: ["terminal verdict recorded"],
  required_output: ["decision", "evidence", "source_hashes", "terminal_state"],
  route_constraints: { allowed_routes: ["FLASH"], fallback_policy: "NO_LUNA", maximum_attempts: 1, maximum_provider_calls: 1, maximum_estimated_cost_usd: 0.05, privacy_class: "PROVIDER_ALLOWED" },
};
const res = await client.request("worker.submit", { input: task, mode: "READ_ONLY" });
const jobId = res.job_id || res.jobId;
const started = Date.now();
let st;
for (;;) {
  st = await client.request("job.status", { jobId });
  if (["RUNNING", "PENDING", "QUEUED"].includes(st.status)) {
    if (Date.now() - started > 120000) { st = { status: "TIMEOUT" }; break; }
    await sleep(1500);
    continue;
  }
  break;
}
client.close();

const resultText = JSON.stringify(st);
const containsExact = resultText.includes(nonce);
const containsSha = resultText.includes(expectedSha);
const pass = containsExact; // exact byte identity of the controlled content is the canary requirement
const report = {
  READ_CANARY_RESULT: pass ? "PASS" : "FAIL",
  nonce_present_exact: containsExact,
  expected_sha_present: containsSha,
  job_status: st.status,
  expected_sha256: expectedSha,
  canary_file_sha256: expectedSha,
  canary_path: rel,
};
fs.writeFileSync(path.join(workspace, ".opencode", "upgrades", "CL-ORCH-UPGRADE-20260807-V1", "evidence", "read_canary_result.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 1));
process.exit(pass ? 0 : 2);
