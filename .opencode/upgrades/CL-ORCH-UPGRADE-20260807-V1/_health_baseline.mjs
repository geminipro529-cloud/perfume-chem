import { pathToFileURL } from "node:url";
const serverPath = process.env.CHEAPLUNA_SERVER;
if (!serverPath) { console.error("CHEAPLUNA_SERVER required"); process.exit(2); }
const bridge = await import(pathToFileURL(serverPath).href);
const client = await bridge.connectProductionCandidateDaemon();
try {
  const h = await client.request("health", {});
  console.log(JSON.stringify({ readiness: h.readiness, project_id: h.project_id, capacity: h.capacity }));
  if (h.readiness !== "READY" || h.project_id !== process.env.DEEPLUNA_PROJECT_ID) process.exitCode = 2;
} finally { client.close(); }
