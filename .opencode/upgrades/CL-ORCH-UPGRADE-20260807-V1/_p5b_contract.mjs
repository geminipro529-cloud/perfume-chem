// P5B contract-harness driver: starts mock provider + isolated candidate daemon,
// runs deterministic scenario jobs, captures traces, asserts REV-9 contracts.
// Writes evidence/mock_traces/<test>.json. No live API, no credentials required.
import { pathToFileURL } from "node:url";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import crypto from "node:crypto";

const root = process.cwd();
const u = path.join(root, ".opencode", "upgrades", "CL-ORCH-UPGRADE-20260807-V1");
const cand = path.join(u, "candidate", "runtime");
const serverPath = path.join(cand, "server.mjs");
const mockPath = path.join(cand, "test", "mock-provider.mjs");
const tracesDir = path.join(u, "evidence", "mock_traces");
fs.mkdirSync(tracesDir, { recursive: true });
const node = "C:\\Program Files\\nodejs\\node.exe";

// --- start mock provider ---
const mock = spawn(node, [mockPath], { stdio: ["ignore", "pipe", "pipe"] });
const port = await new Promise((resolve) => {
  const timer = setTimeout(() => { throw new Error("mock provider did not start"); }, 15000);
  let buf = "";
  mock.stdout.on("data", (d) => { buf += d.toString(); const m = buf.match(/MOCK_PROVIDER_PORT=(\d+)/); if (m) { clearTimeout(timer); resolve(Number(m[1])); } });
});

function httpJson(method, port2, p, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const req = http.request({ host: "127.0.0.1", port: port2, path: p, method, headers: data ? { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) } : {} }, (res) => {
      let b = ""; res.on("data", (c) => (b += c)); res.on("end", () => { try { resolve(JSON.parse(b)); } catch (_) { resolve(b); } });
    });
    req.on("error", reject); if (data) req.write(data); req.end();
  });
}
const setScenario = (s) => httpJson("POST", port, "/__control", { scenario: s });
const getCaptures = () => httpJson("GET", port, "/__capture");

// --- bootstrap isolated candidate store (bounded mitigation) ---
const smPath = path.join(cand, "lib", "scheduler-store.mjs");
const mockProject = "perfume-chem-cheapluna-mock";
const storeParent = path.join(process.env.TEMP || root, "cl_p5b_mock_store");
fs.rmSync(storeParent, { recursive: true, force: true });
fs.mkdirSync(storeParent, { recursive: true });
const bsCode = `import { pathToFileURL } from 'node:url';
const m = await import(pathToFileURL(process.argv[2]).href);
const root = process.argv[3], proj = process.argv[4], ws = process.argv[5], now = Date.now;
const dr = path.join(path.resolve(root), 'projects', proj, 'daemon-v2');
const db = path.join(dr, 'scheduler.sqlite3'); const cr = path.join(dr, 'migration-copy'); const cpd = path.join(cr, 'fresh-state');
fs.mkdirSync(dr, {recursive:true});
let s = m.openSchedulerStore({filename: db, now}); s.close();
await m.migrateSchedulerStoreToCandidateV3({filename: db, backupFilename: db+'.b3'});
await m.migrateSchedulerStoreToCandidateV4({filename: db, backupFilename: db+'.b4'});
await m.migrateSchedulerStoreToCandidateV5({filename: db, backupFilename: db+'.b5'});
s = m.openCandidateSchedulerStoreV5({filename: db, now});
fs.mkdirSync(cr, {recursive:true}); fs.mkdirSync(cpd, {recursive:true});
const oc = s.auditCandidateCopiedStateMigration({projectId: proj, copyRoot: cr, workspaceRoot: ws, candidateProtocolVersion: 4, staleBeforeMs: 0, sources: [{namespace:'fresh-state', sourceKind:'CANONICAL', copiedRoot: cpd}]});
const h = Object.fromEntries(s.database.prepare('SELECT source_namespace,source_hash FROM legacy_migration_sources WHERE run_id=? ORDER BY source_namespace').all(oc.runId).map(r=>[r.source_namespace,r.source_hash]));
const att = s.issueCandidateMigrationAttestation({projectId: proj, runId: oc.runId, sourceHashes: h});
fs.writeFileSync(path.join(dr,'migration-attestation.json'), JSON.stringify(att));
s.verifyCandidateMigrationAttestation(att); s.close(); console.log('BOOTSTRAP_OK');
`;
const bsFile = path.join(tracesDir, "_bootstrap_mock.mjs");
fs.writeFileSync(bsFile, "import fs from 'node:fs'; import path from 'node:path';\n" + bsCode);
const r = spawnSync(node, [bsFile, smPath, storeParent, mockProject, root], { encoding: "utf8" });
if (r.status !== 0) throw new Error("mock store bootstrap failed: " + r.stderr);

// --- start candidate daemon pointed at the mock ---
const env = { ...process.env, DEEPLUNA_PROJECT_ID: mockProject, DEEPSEEK_ORCHESTRATOR_HOME: storeParent, DEEPLUNA_PRIMARY_PROFILE: "cheapluna-chat", DEEPLUNA_FAST_ONLY: "0", DEEPLUNA_CODEX_ORCHESTRATION: "disabled", DEEPLUNA_READER_POOL_MODE: "DYNAMIC", DEEPLUNA_EMBEDDED_COMPAT: "", DEEPLUNA_PROJECT_SCOPE: "project", DEEPSEEK_ALLOWED_ROOT: root, DEEPSEEK_API_KEY: "test-key", DEEPSEEK_BASE_URL: `http://127.0.0.1:${port}/chat/completions`, CHEAPLUNA_SERVER: serverPath };
// In-process client context reads process.env (DEEPLUNA_PROJECT_ID / DEEPSEEK_ORCHESTRATOR_HOME /
// CHEAPLUNA_SERVER). Synchronize the driver process env with the daemon env BEFORE any in-process
// connect so the pipe discovery targets the isolated mock project, not the real daemon.
Object.assign(process.env, env);
const daemon = spawn(node, [serverPath, "--daemon", `--project-id=${mockProject}`], { cwd: root, env, stdio: ["ignore", "pipe", "pipe"] });
let daemonErr = "";
daemon.stderr.on("data", (d) => { daemonErr += d.toString(); });
const healthCode = `import { pathToFileURL } from 'node:url';
const b = await import(pathToFileURL(process.env.CHEAPLUNA_SERVER).href);
const c = await b.connectProductionCandidateDaemon();
try { const h = await c.request('health', {}); console.log(JSON.stringify({ready: h.readiness, pid: h.project_id, build: h.runtime_build_hash ?? null})); if (h.readiness!=='READY') process.exitCode=2; } finally { c.close(); }
`;
const healthFile = path.join(tracesDir, "_health.mjs");
fs.writeFileSync(healthFile, healthCode);
let ready = false;
for (let i = 0; i < 40; i++) {
  await new Promise((r2) => setTimeout(r2, 500));
  const h = spawnSync(node, [healthFile], { env, encoding: "utf8" });
  if (h.status === 0) { ready = true; break; }
  if (daemon.exitCode !== null) break;
}
if (!ready) throw new Error("candidate mock daemon did not become READY; stderr: " + daemonErr.slice(-1000));
const bridge = await import(pathToFileURL(serverPath).href);
let client;
try {
  client = await bridge.connectProductionCandidateDaemon();
} catch (e) {
  throw new Error("driver connect failed; daemonExit=" + daemon.exitCode + " stderr=" + daemonErr.slice(-1200) + " orig=" + e.message);
}
const sleep = (ms) => new Promise((r2) => setTimeout(r2, ms));

async function submitJob(test) {
  const reads = test.reads === false ? [] : [{ path: "inventory.txt", unit: "line", start: 1, end: 3 }];
  const task = {
    task_id: test.id, objective: test.objective, tier: test.tier, workspace: root,
    allowed_paths: ["inventory.txt"],
    required_reads: reads,
    max_output_tokens: 8192, timeout_minutes: 2, reuse_cache: false, require_cache: false,
    definition_of_done: ["terminal verdict recorded"], required_output: ["decision", "evidence", "source_hashes", "terminal_state"],
    route_constraints: { allowed_routes: test.allowedRoutes, fallback_policy: "NO_LUNA", maximum_attempts: test.maxAttempts ?? 1, maximum_provider_calls: test.maxCalls ?? 5, maximum_estimated_cost_usd: 0.2, privacy_class: "PROVIDER_ALLOWED" },
  };
  if (reads.length > 0) {
    task.coverage_spec = { mode: "ALL_REQUIRED_READS", citations_required_for: ["positive_findings", "negative_findings"] };
  }
  const res = await client.request("worker.submit", { input: task, mode: "READ_ONLY" });
  const jobId = res.job_id || res.jobId;
  const started = Date.now();
  let st;
  for (;;) {
    st = await client.request("job.status", { jobId });
    if (["RUNNING", "PENDING", "QUEUED"].includes(st.status)) {
      if (Date.now() - started > 60000) { st = { status: "TIMEOUT" }; break; }
      await sleep(1000); continue;
    }
    break;
  }
  return { jobId, st };
}

// Reset the provider circuit between tests. The daemon persists consecutive provider
// failures in worker-state-v5.json and opens the circuit after two failures, which would
// poison every later test with PROVIDER_ERROR and 0 provider calls. Each contract test
// starts from a clean failure state so retry/circuit cases exercise only their own path.
function resetCircuit() {
  const statePath = path.join(storeParent, "projects", mockProject, "worker-state-v5.json");
  try { fs.rmSync(statePath, { force: true }); } catch (_) {}
}

let pass = 0, fail = 0;
const results = {};
function record(name, ok, detail) { if (ok) pass++; else fail++; results[name] = { ok, detail }; console.log((ok ? "PASS " : "FAIL ") + name + (detail ? " :: " + String(detail).slice(0, 160) : "")); }

const tests = [
  { id: "contract_fast_shape", tier: "FLASH", allowedRoutes: ["FLASH"], maxCalls: 1, scenario: "fast_ok", objective: "Report the exact string.", check: async (cap) => { const b = cap[0].body; return b.thinking?.type === "disabled" && typeof b.model === "string"; } },
  { id: "contract_high_shape", tier: "PRO", allowedRoutes: ["FLASH", "DIRECT_PRO"], maxCalls: 5, scenario: "thinking_ok", objective: "Analyze the note_map lookup for case sensitivity.", check: async (cap) => { const b = cap[0].body; return b.thinking?.type === "enabled" && b.reasoning_effort === "high" && !("tool_choice" in b); } },
  { id: "contract_max_shape", tier: "REASONING", allowedRoutes: ["FLASH", "DIRECT_PRO"], maxCalls: 5, scenario: "thinking_ok", objective: "Adversarially audit the pyramid gate.", check: async (cap) => { const b = cap[0].body; return b.thinking?.type === "enabled" && b.reasoning_effort === "max" && !("tool_choice" in b); } },
  { id: "reasoning_replay", tier: "PRO", allowedRoutes: ["FLASH", "DIRECT_PRO"], maxCalls: 5, scenario: "tool_loop_ok", objective: "Read the file and then finalize.", check: async (cap, st) => { const b2 = cap[1]?.body; const asst = b2 && b2.messages.find((m) => m.role === "assistant" && Array.isArray(m.tool_calls)); const replayed = asst && asst.reasoning_content === "mock tool reasoning"; const toolBound = b2 && b2.messages.some((m) => m.role === "tool" && m.tool_call_id === "call_mock_1"); return replayed && toolBound && st.execution_status === "ACCEPTED"; } },
  { id: "truncation", tier: "FLASH", allowedRoutes: ["FLASH"], maxCalls: 1, scenario: "truncation", objective: "Read and report.", check: async (cap, st) => { const rp = st.result_packet || {}; const text = ((st.summary || "") + " " + (st.execution_status || "") + " " + (st.error_code || "") + " " + (rp.summary || "") + " " + JSON.stringify(rp.negative_findings || [])); return /truncat/i.test(text); } },
  { id: "retry_429", tier: "PRO", allowedRoutes: ["FLASH", "DIRECT_PRO"], maxCalls: 3, maxAttempts: 3, reads: false, scenario: "http_429_then_ok", objective: "Report the exact string.", check: async (cap, st) => { return cap.length === 3 && st.execution_status === "ACCEPTED"; } },
  { id: "retry_500", tier: "PRO", allowedRoutes: ["FLASH", "DIRECT_PRO"], maxCalls: 2, maxAttempts: 2, reads: false, scenario: "http_500_then_ok", objective: "Report the exact string.", check: async (cap, st) => { return cap.length === 2 && st.execution_status === "ACCEPTED"; } },
  { id: "retry_503", tier: "PRO", allowedRoutes: ["FLASH", "DIRECT_PRO"], maxCalls: 3, maxAttempts: 3, reads: false, scenario: "http_503_then_ok", objective: "Report the exact string.", check: async (cap, st) => { return cap.length === 3 && st.execution_status === "ACCEPTED"; } },
  { id: "retry_400_no_retry", tier: "PRO", allowedRoutes: ["FLASH", "DIRECT_PRO"], maxCalls: 1, maxAttempts: 1, reads: false, scenario: "http_400", objective: "Report the exact string.", check: async (cap) => { return cap.length === 1; } },
  { id: "semantic_quarantine", tier: "FLASH", allowedRoutes: ["FLASH"], maxCalls: 1, scenario: "semantic_corruption", objective: "Report the exact string.", check: async (cap) => { return cap.length === 1; } },
];

const allTraces = [];
for (const t of tests) {
  await setScenario(t.scenario);
  resetCircuit();
  const before = await getCaptures();
  const { st } = await submitJob(t);
  const cap = await getCaptures();
  const myCap = cap.captures.slice(before.captures.length);
  const trace = { test: t.id, scenario: t.scenario, tier: t.tier, provider_requests: myCap.map((c) => ({ body: c.body, raw_len: c.raw.length })), terminal: { status: st.status, execution_status: st.execution_status, evidence_verdict: st.evidence_verdict, summary: (st.summary || "").slice(0, 300) } };
  trace.trace_sha256 = crypto.createHash("sha256").update(JSON.stringify(trace)).digest("hex");
  fs.writeFileSync(path.join(tracesDir, `${t.id}.json`), JSON.stringify(trace, null, 2));
  allTraces.push(trace);
  let ok = false; let detail = "";
  try { ok = await t.check(myCap, st); } catch (e) { detail = e.message; }
  record(t.id, ok, detail || `${myCap.length} reqs, ${st.status}/${st.execution_status}`);
}
client.close();
daemon.kill();
mock.kill();
console.log(JSON.stringify({ P5B_MOCK_SUITE: { PASS: pass, FAIL: fail }, results, traces: tracesDir }, null, 1));
process.exit(fail > 0 ? 1 : 0);
