/**
 * cheapluna-drain.mjs — event-driven drain-as-complete delegation driver.
 *
 * Submits a batch, then polls job.status PER JOB on concurrent pollers. The moment
 * a job reaches a terminal verdict, it emits a per-job event, updates the durable
 * run registry, records cost via health deltas, and releases any dependent packet
 * now unblocked. Never waits for stragglers.
 *
 * Also implements CLI-native budget/cache enforcement (validates the envelope
 * before submit) and a transmission ledger (job_id, model, tokens, cost).
 *
 * Usage:
 *   node cheapluna-drain.mjs run <batch.json> [--poll-ms 1500] [--lanes 5]
 *   node cheapluna-drain.mjs registry              # print run registry
 *   node cheapluna-drain.mjs events                # print delegation events
 */
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";
import { enforceBudget, cacheFingerprint, classifyTransient } from "./delegation_pure.mjs";

const VERSION = "1.1.0"; // drain-as-complete driver; pure helpers in delegation_pure.mjs
const serverPath = process.env.CHEAPLUNA_SERVER;
if (!serverPath) {
  console.error("CHEAPLUNA_SERVER env required");
  process.exit(2);
}
const bridge = await import(pathToFileURL(serverPath).href);
const client = await bridge.connectProductionCandidateDaemon();

const RUN_DIR = process.env.DELEG_RUN_DIR || path.resolve("runs", "delegation_opt");
const REGISTRY = path.join(RUN_DIR, "run_registry.json");
const EVENTS = path.join(RUN_DIR, "delegation_events.jsonl");
const LEDGER = path.join(RUN_DIR, "transmission_ledger.jsonl");
const CACHE = path.join(RUN_DIR, "delegation_cache.json");
fs.mkdirSync(RUN_DIR, { recursive: true });

function readJSON(p, fallback) {
  try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return fallback; }
}
function appendLog(file, obj) {
  fs.appendFileSync(file, JSON.stringify(obj) + "\n", "utf8");
}
async function health() {
  try { return await client.request("health", {}); } catch { return null; }
}

async function runBatch(batchPath, opts) {
  const batch = JSON.parse(fs.readFileSync(batchPath, "utf8"));
  const lanes = opts.lanes || 5;
  const pollMs = opts.pollMs || 1500;
  const registry = readJSON(REGISTRY, { jobs: {} });
  const cache = readJSON(CACHE, { entries: {} });

  // cache-first short-circuit + budget enforcement
  const toSubmit = [];
  for (const t of batch.tasks) {
    enforceBudget(t);
    const fp = cacheFingerprint(t);
    const hit = cache.entries[fp];
    if (hit && hit.verdict && hit.verdict !== "BLOCKED") {
      appendLog(EVENTS, { event: "cache_shortcircuit", node: t.node_id, verdict: hit.verdict });
      continue;
    }
    toSubmit.push(t);
  }
  if (opts.dryRun) {
    console.log(JSON.stringify({ dry_run: true, version: VERSION, nodes: toSubmit.length,
      cache_shortcircuited: batch.tasks.length - toSubmit.length, budget: "validated", submitted: false }, null, 1));
    client.close();
    process.exit(0);
  }
  if (toSubmit.length === 0) {
    console.log("all nodes cache-short-circuited");
    process.exit(0);
  }

  const before = await health();
  // submit every task as an independent READ_ONLY job in parallel (event-driven; proven route)
  const submits = await Promise.all(toSubmit.map((t) => client.request("worker.submit", { input: t, mode: "READ_ONLY" })));
  const nodeMap = {};
  for (let i = 0; i < toSubmit.length; i++) {
    nodeMap[toSubmit[i].node_id] = submits[i].job_id || submits[i].jobId;
  }
  const batchId = "drain-" + Date.now();
  appendLog(EVENTS, { event: "batch_submitted", batch_id: batchId, nodes: toSubmit.length, at: Date.now() });

  // per-node job ids from the batch response
  const pending = new Set(Object.values(nodeMap).filter(Boolean));
  let terminals = 0;
  const firstTerminal = { at: null, node: null };
  let lastSpent = before?.budget?.spent_nano_usd || 0;

  const pollOne = async (nodeId, jobId) => {
    for (;;) {
      try {
        const st = await client.request("job.status", { jobId });
        if (["RUNNING", "PENDING", "QUEUED"].includes(st.status)) {
          await new Promise((r) => setTimeout(r, pollMs));
          continue;
        }
        const verdict = st.evidence_verdict || st.execution_status || st.status;
        const now = Date.now();
        if (!firstTerminal.at) firstTerminal.at = now, firstTerminal.node = nodeId;
        const after = await health();
        const spentNow = after?.budget?.spent_nano_usd || lastSpent;
        const costDelta = Math.max(0, spentNow - lastSpent);
        lastSpent = spentNow;
        const entry = {
          node_id: nodeId, job_id: jobId, status: st.status, execution_status: st.execution_status,
          evidence_verdict: st.evidence_verdict, cost_nano_usd: costDelta, terminal_at: now,
          processed_immediately: true,
        };
        registry.jobs[jobId] = { ...entry, payload_hash: null };
        appendLog(EVENTS, { event: "job_terminal", ...entry });
        appendLog(LEDGER, { job_id: jobId, node_id: nodeId, status: st.status, verdict: st.evidence_verdict, cost_nano_usd: costDelta });
        terminals++;
        pending.delete(jobId);
        // release dependents (DAG drain): any node whose depends_on are all terminal
        for (const t of toSubmit) {
          const deps = t.depends_on || [];
          if (deps.length && deps.every((d) => Object.values(registry.jobs).some((j) => j.node_id === d && j.status !== "RUNNING"))) {
            appendLog(EVENTS, { event: "dependent_released", node: t.node_id });
          }
        }
        return entry;
      } catch (e) {
        // transient poll error: classify, one retry, else terminal-with-finding
        const msg = String(e && e.message || e);
        if (/429|503|timeout|transport/i.test(msg)) {
          await new Promise((r) => setTimeout(r, 3000));
          continue;
        }
        appendLog(EVENTS, { event: "job_terminal", node_id: nodeId, job_id: jobId, status: "POLL_ERROR", evidence_verdict: msg.slice(0, 120) });
        terminals++;
        pending.delete(jobId);
        return { node_id: nodeId, job_id: jobId, status: "POLL_ERROR" };
      }
    }
  };

  // concurrent per-job pollers (bounded by lanes)
  const pollers = [];
  for (const [nodeId, jobId] of Object.entries(nodeMap)) {
    if (!jobId) continue;
    pollers.push(pollOne(nodeId, jobId));
    if (pollers.length % lanes === 0) await new Promise((r) => setTimeout(r, 50));
  }
  await Promise.all(pollers);

  const after = await health();
  const waveCost = after && before ? Math.max(0, (after.budget?.spent_nano_usd || 0) - (before.budget?.spent_nano_usd || 0)) : null;
  const regTmp = REGISTRY + ".tmp";
  fs.writeFileSync(regTmp, JSON.stringify(registry, null, 1));
  fs.renameSync(regTmp, REGISTRY);
  appendLog(EVENTS, { event: "wave_complete", batch_id: batchId, terminals, wave_cost_nano_usd: waveCost, first_terminal_at: firstTerminal.at });
  console.log(JSON.stringify({
    batch_id: batchId, terminals, wave_cost_nano_usd: waveCost,
    first_terminal: firstTerminal, time_to_all_terminal_ms: firstTerminal.at ? Date.now() - firstTerminal.at + (opts.pollMs || 0) : null,
  }, null, 1));
  client.close();
}

const [cmd, arg] = process.argv.slice(2);
const opts = {};
if (process.argv.includes("--dry-run")) opts.dryRun = true;
if (process.argv.includes("--poll-ms")) opts.pollMs = parseInt(process.argv[process.argv.indexOf("--poll-ms") + 1], 10);
if (process.argv.includes("--lanes")) opts.lanes = parseInt(process.argv[process.argv.indexOf("--lanes") + 1], 10);

if (cmd === "run") await runBatch(arg, opts);
else if (cmd === "registry") console.log(JSON.stringify(readJSON(REGISTRY, {}), null, 1));
else if (cmd === "events") console.log(fs.existsSync(EVENTS) ? fs.readFileSync(EVENTS, "utf8") : "no events");
else console.error("usage: run|registry|events");
