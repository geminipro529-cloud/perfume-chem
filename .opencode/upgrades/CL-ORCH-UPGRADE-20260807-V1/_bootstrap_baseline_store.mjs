// Standalone bootstrap of an isolated BASELINE production candidate store,
// replicating server.mjs openProductionCandidateStore created=true path.
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const smPath = process.argv[2];
const storeRoot = process.argv[3];
const projectId = process.argv[4];
const workspaceRoot = process.argv[5];
const sm = await import(pathToFileURL(smPath).href);
const now = Date.now;

const projectRoot = path.join(path.resolve(storeRoot), 'projects', projectId);
const daemonRoot = path.join(projectRoot, 'daemon-v2');
const databasePath = path.join(daemonRoot, 'scheduler.sqlite3');
const attestationPath = path.join(daemonRoot, 'migration-attestation.json');
const copyRoot = path.join(daemonRoot, 'migration-copy');
const copiedRoot = path.join(copyRoot, 'fresh-state');
fs.mkdirSync(daemonRoot, { recursive: true });

function atomicJson(file, value) {
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(value));
  fs.renameSync(tmp, file);
}
const sha256 = (v) => crypto.createHash('sha256').update(typeof v === 'string' ? v : JSON.stringify(v)).digest('hex');

// Windows Defender real-time scanning holds transient handles on freshly created SQLite
// files, which surfaces as intermittent SQLITE_CANTOPEN (errcode 14) from node:sqlite
// backup/migration. Bounded retry with backoff is the documented remediation (same
// pattern as the provider 429 retry table). Verified root cause 2026-08-07.
const CANTOPEN_RETRIES = 4;
const CANTOPEN_BACKOFF_MS = 750;
async function migrateWithRetry(fn, label) {
  let lastError = null;
  for (let attempt = 1; attempt <= CANTOPEN_RETRIES; attempt += 1) {
    try {
      await fn();
      return;
    } catch (error) {
      lastError = error;
      const transient = error?.errcode === 14 || /unable to open database file/i.test(String(error?.message ?? ""));
      if (!transient || attempt === CANTOPEN_RETRIES) throw error;
      console.error(`[bootstrap] ${label} transient CANTOPEN on attempt ${attempt}/${CANTOPEN_RETRIES}; retrying in ${CANTOPEN_BACKOFF_MS}ms`);
      await new Promise((resolve) => setTimeout(resolve, CANTOPEN_BACKOFF_MS));
    }
  }
  throw lastError;
}

let store = sm.openSchedulerStore({ filename: databasePath, now });
store.close();
await migrateWithRetry(
  () => sm.migrateSchedulerStoreToCandidateV3({ filename: databasePath, backupFilename: path.join(daemonRoot, `scheduler.schema-v2.${Date.now()}-bootstrap.backup.sqlite3`) }),
  "migrateV3",
);
await migrateWithRetry(
  () => sm.migrateSchedulerStoreToCandidateV4({ filename: databasePath, backupFilename: path.join(daemonRoot, `scheduler.schema-v3.${Date.now()}-bootstrap.backup.sqlite3`) }),
  "migrateV4",
);
await migrateWithRetry(
  () => sm.migrateSchedulerStoreToCandidateV5({ filename: databasePath, backupFilename: path.join(daemonRoot, `scheduler.schema-v4.${Date.now()}-bootstrap.backup.sqlite3`) }),
  "migrateV5",
);
store = sm.openCandidateSchedulerStoreV5({ filename: databasePath, now });
try {
  fs.mkdirSync(copyRoot, { recursive: true });
  fs.mkdirSync(copiedRoot, { recursive: true });
  const outcome = store.auditCandidateCopiedStateMigration({
    projectId,
    copyRoot,
    workspaceRoot,
    candidateProtocolVersion: 4,
    staleBeforeMs: 0,
    sources: [{ namespace: 'fresh-state', sourceKind: 'CANONICAL', copiedRoot }],
  });
  const sourceHashes = Object.fromEntries(
    store.database
      .prepare(`SELECT source_namespace,source_hash FROM legacy_migration_sources WHERE run_id=? ORDER BY source_namespace`)
      .all(outcome.runId)
      .map((row) => [row.source_namespace, row.source_hash]),
  );
  const attestation = store.issueCandidateMigrationAttestation({ projectId, runId: outcome.runId, sourceHashes });
  atomicJson(attestationPath, attestation);
  store.verifyCandidateMigrationAttestation(attestation);
  console.log('BOOTSTRAP_OK attestation=' + attestation.attestationId + ' project=' + projectId + ' db=' + fs.statSync(databasePath).size);
} finally {
  store.close();
}
