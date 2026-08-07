/**
 * CheapLuna direct daemon CLI — drives the project daemon over its named pipe
 * without the MCP bridge. Reuse when the MCP server is unavailable.
 *
 * Usage:
 *   node .opencode/scripts/cheapluna-cli.mjs health
 *   node .opencode/scripts/cheapluna-cli.mjs submit <input.json> [--mode READ_ONLY] [--poll]
 *   node .opencode/scripts/cheapluna-cli.mjs batch-submit <batch.json> [--poll]
 *   node .opencode/scripts/cheapluna-cli.mjs status <jobId>
 *   node .opencode/scripts/cheapluna-cli.mjs cancel <jobId>
 *   node .opencode/scripts/cheapluna-cli.mjs metrics
 *
 * Environment (must match the bridge): DEEPLUNA_PROJECT_ID,
 * DEEPSEEK_ALLOWED_ROOT, DEEPSEEK_ORCHESTRATOR_HOME, DEEPINFRA_API_TOKEN, ...
 * Run through the PowerShell wrapper below if env setup is needed.
 */
import { pathToFileURL } from "node:url";
import fs from "node:fs";

const serverPath = process.env.CHEAPLUNA_SERVER;
if (!serverPath) {
  console.error("CHEAPLUNA_SERVER env must point at the runtime server.mjs");
  process.exit(2);
}

const bridge = await import(pathToFileURL(serverPath).href);
const client = await bridge.connectProductionCandidateDaemon();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pollJob(jobId, timeoutMs = 30 * 60 * 1000) {
  const started = Date.now();
  for (;;) {
    const st = await client.request("job.status", { jobId });
    if (st.status === "RUNNING" || st.status === "PENDING" || st.status === "QUEUED") {
      if (Date.now() - started > timeoutMs) {
        console.log(JSON.stringify({ jobId, poll: "TIMEOUT", status: st.status }, null, 1));
        process.exit(3);
      }
      await sleep(3000);
      continue;
    }
    return st;
  }
}

const [cmd, arg] = process.argv.slice(2);
if (!cmd) {
  console.error("missing command");
  process.exit(2);
}

if (cmd === "health") {
  const h = await client.request("health", {});
  console.log(JSON.stringify({
    readiness: h.readiness,
    project_id: h.project_id,
    capacity: h.capacity,
    circuits: h.circuits,
    budget: h.budget,
    server_release: h.server_release,
  }, null, 1));
} else if (cmd === "submit") {
  const input = JSON.parse(fs.readFileSync(arg, "utf8"));
  const mode = process.argv.includes("--mode")
    ? process.argv[process.argv.indexOf("--mode") + 1]
    : "READ_ONLY";
  const res = await client.request("worker.submit", { input, mode });
  const jobId = res.job_id || res.jobId;
  console.log(JSON.stringify(res, null, 1));
  if (process.argv.includes("--poll") && jobId) {
    const st = await pollJob(jobId);
    console.log(JSON.stringify(st, null, 1));
  }
} else if (cmd === "batch-submit") {
  const input = JSON.parse(fs.readFileSync(arg, "utf8"));
  const res = await client.request("batch.submit", input);
  console.log(JSON.stringify(res, null, 1));
  if (process.argv.includes("--poll")) {
    const bid = res.batch_id;
    for (;;) {
      const st = await client.request("batch.status", { batchId: bid });
      if (st.status === "RUNNING" || st.status === "PENDING") {
        await sleep(3000);
        continue;
      }
      console.log(JSON.stringify(st, null, 1));
      break;
    }
  }
} else if (cmd === "status") {
  const st = await client.request("job.status", { jobId: arg });
  console.log(JSON.stringify(st, null, 1));
} else if (cmd === "cancel") {
  const st = await client.request("job.cancel", { jobId: arg });
  console.log(JSON.stringify(st, null, 1));
} else if (cmd === "metrics") {
  const st = await client.request("metrics", {});
  console.log(JSON.stringify(st, null, 1));
} else {
  console.error("unknown command", cmd);
  process.exit(2);
}

client.close();
