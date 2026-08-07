import { pathToFileURL } from 'node:url';
const b = await import(pathToFileURL(process.env.CHEAPLUNA_SERVER).href);
const c = await b.connectProductionCandidateDaemon();
try { const h = await c.request('health', {}); console.log(JSON.stringify({ready: h.readiness, pid: h.project_id, build: h.runtime_build_hash ?? null})); if (h.readiness!=='READY') process.exitCode=2; } finally { c.close(); }
