// PATH 1 acceptance gate: 20 consecutive fresh-store bootstraps, each in a fresh
// attempt subdirectory, bounded mitigation maximum_attempts=3 with settle [1s,1s,2s].
// Records per-run fresh_store_outcome + bootstrap_attempts_used (retry distribution visible).
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const smPath = process.argv[2];
const gateRoot = process.argv[3]; // preferred temp benchmark-state root
const workspaceRoot = process.argv[4];
const runtimeRoot = process.argv[5];
const oldRuntimeFile = process.argv[6]; // server.mjs absolute path (hash check)
const oldSchedulerFile = process.argv[7]; // scheduler-store.mjs absolute path
const outPath = process.argv[8];
const sm = await import(pathToFileURL(smPath).href);
const now = Date.now;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const sha256 = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");

async function bootstrapOnce(storeDir, projectId) {
  const db = path.join(storeDir, "scheduler.sqlite3");
  let s = sm.openSchedulerStore({ filename: db, now });
  s.close();
  await sm.migrateSchedulerStoreToCandidateV3({ filename: db, backupFilename: db + ".b3" });
  await sm.migrateSchedulerStoreToCandidateV4({ filename: db, backupFilename: db + ".b4" });
  await sm.migrateSchedulerStoreToCandidateV5({ filename: db, backupFilename: db + ".b5" });
  s = sm.openCandidateSchedulerStoreV5({ filename: db, now });
  const daemonRoot = path.dirname(db);
  const copyRoot = path.join(daemonRoot, "migration-copy");
  const copiedRoot = path.join(copyRoot, "fresh-state");
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

const oldRuntimeSha = sha256(oldRuntimeFile);
const oldSchedulerSha = sha256(oldSchedulerFile);
const settle = [1000, 1000, 2000];
const stores = [];
let gatePass = true;

for (let i = 1; i <= 20; i++) {
  const storeRoot = path.join(gateRoot, "BASELINE-gate");
  let outcome = { store_index: i, fresh_store_outcome: "FAIL", bootstrap_attempts_used: 0, attempts: [] };
  for (let attempt = 1; attempt <= 3; attempt++) {
    const attemptDir = path.join(storeRoot, `store-${i}`, `attempt-${attempt}`);
    fs.rmSync(attemptDir, { recursive: true, force: true });
    fs.mkdirSync(attemptDir, { recursive: true });
    const started = Date.now();
    try {
      await bootstrapOnce(attemptDir, "perfume-chem-cheapluna-baseline");
      outcome.fresh_store_outcome = "SUCCESS";
      outcome.bootstrap_attempts_used = attempt;
      outcome.attempts.push({ attempt, ok: true, settle_ms: attempt > 1 ? settle[attempt - 2] : 0, elapsed_ms: Date.now() - started, errcode: null });
      break;
    } catch (e) {
      outcome.attempts.push({ attempt, ok: false, settle_ms: attempt > 1 ? settle[attempt - 2] : 0, elapsed_ms: Date.now() - started, err: e.message, code: e.code, errcode: e.errcode, errstr: e.errstr });
      if (attempt < 3) await sleep(settle[attempt - 1]);
    }
  }
  if (outcome.fresh_store_outcome !== "SUCCESS") gatePass = false;
  stores.push(outcome);
}

const runtimeShaAfter = sha256(oldRuntimeFile);
const schedulerShaAfter = sha256(oldSchedulerFile);
const report = {
  gate: "PATH_1",
  gate_result: gatePass ? "PASS" : "FAIL",
  PATH_1_BOOTSTRAP_STABLE: gatePass ? "PASS" : "FAIL",
  runs: 20,
  successes: stores.filter((s) => s.fresh_store_outcome === "SUCCESS").length,
  retry_distribution: {
    attempts_used_1: stores.filter((s) => s.bootstrap_attempts_used === 1).length,
    attempts_used_2: stores.filter((s) => s.bootstrap_attempts_used === 2).length,
    attempts_used_3: stores.filter((s) => s.bootstrap_attempts_used === 3).length,
    failures: stores.filter((s) => s.fresh_store_outcome === "FAIL").length,
  },
  old_runtime_bytes_changed: runtimeShaAfter === oldRuntimeSha ? 0 : 1,
  old_scheduler_code_changed: schedulerShaAfter === oldSchedulerSha ? 0 : 1,
  failed_db_reuse: 0,
  stores,
};
fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
console.log(JSON.stringify({
  PATH_1_BOOTSTRAP_STABLE: report.PATH_1_BOOTSTRAP_STABLE,
  successes: `${report.successes}/${report.runs}`,
  retry_distribution: report.retry_distribution,
  old_runtime_bytes_changed: report.old_runtime_bytes_changed,
  old_scheduler_code_changed: report.old_scheduler_code_changed,
  report: outPath,
}, null, 1));
