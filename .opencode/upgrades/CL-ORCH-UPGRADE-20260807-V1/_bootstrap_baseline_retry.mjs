// Bootstrap one isolated BASELINE store under a parent root using the approved bounded
// mitigation: maximum_attempts=3, fresh attempt subdirectories, settle [1s,1s,2s].
// Prints the successful storeRoot (for the daemon env) and attempts_used.
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";

const smPath = process.argv[2];
const parentRoot = process.argv[3]; // e.g. temp bench root; storeRoot = parentRoot/attempt-N
const projectId = process.argv[4];
const workspaceRoot = process.argv[5];
const sm = await import(pathToFileURL(smPath).href);
const now = Date.now;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const settle = [1000, 1000, 2000];

async function bootstrapOnce(storeRoot) {
  const daemonRoot = path.join(path.resolve(storeRoot), "projects", projectId, "daemon-v2");
  const db = path.join(daemonRoot, "scheduler.sqlite3");
  const copyRoot = path.join(daemonRoot, "migration-copy");
  const copiedRoot = path.join(copyRoot, "fresh-state");
  fs.mkdirSync(daemonRoot, { recursive: true });
  let s = sm.openSchedulerStore({ filename: db, now });
  s.close();
  await sm.migrateSchedulerStoreToCandidateV3({ filename: db, backupFilename: db + ".b3" });
  await sm.migrateSchedulerStoreToCandidateV4({ filename: db, backupFilename: db + ".b4" });
  await sm.migrateSchedulerStoreToCandidateV5({ filename: db, backupFilename: db + ".b5" });
  s = sm.openCandidateSchedulerStoreV5({ filename: db, now });
  fs.mkdirSync(copyRoot, { recursive: true });
  fs.mkdirSync(copiedRoot, { recursive: true });
  const outcome = s.auditCandidateCopiedStateMigration({
    projectId, copyRoot, workspaceRoot, candidateProtocolVersion: 4, staleBeforeMs: 0,
    sources: [{ namespace: "fresh-state", sourceKind: "CANONICAL", copiedRoot }],
  });
  const sourceHashes = Object.fromEntries(
    s.database.prepare("SELECT source_namespace,source_hash FROM legacy_migration_sources WHERE run_id=? ORDER BY source_namespace")
      .all(outcome.runId).map((r) => [r.source_namespace, r.source_hash]),
  );
  const att = s.issueCandidateMigrationAttestation({ projectId, runId: outcome.runId, sourceHashes });
  fs.writeFileSync(path.join(daemonRoot, "migration-attestation.json"), JSON.stringify(att));
  s.verifyCandidateMigrationAttestation(att);
  s.close();
}

let ok = false;
let attemptsUsed = 0;
let storeRoot = null;
for (let attempt = 1; attempt <= 3; attempt++) {
  attemptsUsed = attempt;
  storeRoot = path.join(parentRoot, `BASELINE-attempt-${attempt}`);
  fs.rmSync(storeRoot, { recursive: true, force: true });
  fs.mkdirSync(storeRoot, { recursive: true });
  try {
    await bootstrapOnce(storeRoot);
    ok = true;
    break;
  } catch (e) {
    console.log(`BASELINE_ATTEMPT_${attempt}_FAIL errcode=${e.errcode ?? e.code ?? "?"} err=${e.message}`);
    if (attempt < 3) await sleep(settle[attempt - 1]);
  }
}
if (!ok) { console.error("BASELINE_BOOTSTRAP_FAILED_ALL_ATTEMPTS"); process.exit(2); }
console.log(JSON.stringify({ BASELINE_BOOTSTRAP_STABLE: "PASS", bootstrap_attempts_used: attemptsUsed, store_root: storeRoot }));
