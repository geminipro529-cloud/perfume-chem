import { createHash, randomUUID } from "node:crypto";
import {
  existsSync,
  linkSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  statSync,
  unlinkSync,
} from "node:fs";
import path from "node:path";
import { backup as backupDatabase, DatabaseSync } from "node:sqlite";

import { containsUnsafePublicText } from "./public-text-security.mjs";

export const STORE_SCHEMA_VERSION = 2;
export const CANDIDATE_STORE_SCHEMA_V3_VERSION = 3;
export const CANDIDATE_STORE_SCHEMA_V4_VERSION = 4;
export const CANDIDATE_STORE_SCHEMA_VERSION = 5;
export const CANDIDATE_STORE_MIGRATION_PHASES = Object.freeze([
  "SOURCE_ATTESTED",
  "BACKUP_COMPLETE",
  "BACKUP_VALIDATED",
  "TRANSACTION_STARTED",
  "SOURCE_REATTESTED",
  "SCHEMA_CREATED",
  "LEGACY_ROWS_VERIFIED",
  "FOREIGN_KEYS_VERIFIED",
  "INTEGRITY_VERIFIED",
  "VERSION_UPDATED",
  "SCHEMA_VERIFIED",
  "BEFORE_COMMIT",
  "COMMIT_COMPLETE",
]);
const MAX_PROTOCOL_RESPONSE_BYTES = 60 * 1024;
const MAX_CANDIDATE_PROTOCOL_REQUEST_BYTES = 65_536;
const MAX_CANDIDATE_PROTOCOL_OUTCOME_BYTES = 57_344;
const CANDIDATE_PROTOCOL_METHODS = Object.freeze([
  "batch.metrics",
  "batch.status",
  "batch.submit",
  "head.cancel",
  "head.metrics",
  "head.plan",
  "head.status",
  "head.submit",
  "health",
  "job.cancel",
  "job.status",
  "metrics",
  "worker.submit",
]);
const CANDIDATE_COST_CAPABILITY = Symbol("candidate-cost-capability");
const CANDIDATE_TRANSMISSION_COST_CAPABILITY = Symbol(
  "candidate-transmission-cost-capability",
);

const REQUIRED_TEXT_FIELDS = [
  "projectId",
  "taskId",
  "idempotencyKey",
  "contractHash",
  "inputFingerprint",
  "role",
  "poolId",
];

const GENERATION_STATES = Object.freeze([
  "QUEUED",
  "RUNNING",
  "VALIDATING",
  "SUCCEEDED",
  "FAILED",
  "CANCELED",
  "QUARANTINED",
]);
const ATTEMPT_STATES = Object.freeze(["RUNNING", "SUCCEEDED", "FAILED", "CANCELED"]);
const EVENT_TYPES = Object.freeze([
  "ENQUEUED",
  "LEASED",
  "RESULT_QUARANTINED",
  "RESULT_ACCEPTED",
  "LEASE_EXPIRED",
  "RETRY_CREATED",
  "CANCELED",
]);
const V1_GENERATION_STATES = Object.freeze([
  "QUEUED",
  "RUNNING",
  "VALIDATING",
  "SUCCEEDED",
  "FAILED",
  "QUARANTINED",
]);
const V1_ATTEMPT_STATES = Object.freeze(["RUNNING", "SUCCEEDED", "FAILED"]);
const V1_EVENT_TYPES = Object.freeze([
  "ENQUEUED",
  "LEASED",
  "RESULT_QUARANTINED",
  "RESULT_ACCEPTED",
  "LEASE_EXPIRED",
  "RETRY_CREATED",
]);
const RETRY_REASON_CODES = new Set([
  "MANUAL_RETRY",
  "TRANSIENT_FAILURE",
  "VALIDATION_FAILED",
  "OPERATOR_APPROVED",
]);
const TERMINAL_GENERATION_STATES = new Set([
  "SUCCEEDED",
  "FAILED",
  "CANCELED",
  "QUARANTINED",
]);

const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS logical_jobs (
  job_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL
    CHECK (
      typeof(created_at_ms) = 'integer'
      AND created_at_ms BETWEEN 0 AND 9007199254740991
    ),
  UNIQUE (project_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS generations (
  job_id TEXT NOT NULL REFERENCES logical_jobs(job_id),
  generation INTEGER NOT NULL
    CHECK (
      typeof(generation) = 'integer'
      AND generation BETWEEN 1 AND 9007199254740991
    ),
  task_id TEXT NOT NULL,
  role TEXT NOT NULL,
  pool_id TEXT NOT NULL,
  priority INTEGER NOT NULL
    CHECK (
      typeof(priority) = 'integer'
      AND priority BETWEEN -9007199254740991 AND 9007199254740991
    ),
  state TEXT NOT NULL
    CHECK (
      typeof(state) = 'text'
      AND state IN (${GENERATION_STATES.map((state) => `'${state}'`).join(", ")})
    ),
  contract_hash TEXT NOT NULL,
  input_fingerprint TEXT NOT NULL,
  maximum_attempts INTEGER NOT NULL
    CHECK (
      typeof(maximum_attempts) = 'integer'
      AND maximum_attempts BETWEEN 1 AND 9007199254740991
    ),
  contract_json TEXT NOT NULL,
  accepted_result_hash TEXT,
  diagnostic_enqueued INTEGER NOT NULL DEFAULT 0
    CHECK (typeof(diagnostic_enqueued) = 'integer' AND diagnostic_enqueued IN (0, 1)),
  created_at_ms INTEGER NOT NULL
    CHECK (
      typeof(created_at_ms) = 'integer'
      AND created_at_ms BETWEEN 0 AND 9007199254740991
    ),
  updated_at_ms INTEGER NOT NULL
    CHECK (
      typeof(updated_at_ms) = 'integer'
      AND updated_at_ms BETWEEN 0 AND 9007199254740991
    ),
  PRIMARY KEY (job_id, generation)
);

CREATE TABLE IF NOT EXISTS attempts (
  job_id TEXT NOT NULL
    CHECK (typeof(job_id) = 'text' AND length(trim(job_id)) > 0),
  generation INTEGER NOT NULL
    CHECK (
      typeof(generation) = 'integer'
      AND generation BETWEEN 1 AND 9007199254740991
    ),
  attempt_id TEXT NOT NULL
    CHECK (typeof(attempt_id) = 'text' AND length(trim(attempt_id)) > 0),
  worker_id TEXT NOT NULL
    CHECK (typeof(worker_id) = 'text' AND length(trim(worker_id)) > 0),
  epoch INTEGER NOT NULL
    CHECK (
      typeof(epoch) = 'integer'
      AND epoch BETWEEN 1 AND 9007199254740991
    ),
  state TEXT NOT NULL
    CHECK (
      typeof(state) = 'text'
      AND state IN (${ATTEMPT_STATES.map((state) => `'${state}'`).join(", ")})
    ),
  started_at_ms INTEGER NOT NULL
    CHECK (
      typeof(started_at_ms) = 'integer'
      AND started_at_ms BETWEEN 0 AND 9007199254740991
    ),
  finished_at_ms INTEGER
    CHECK (
      finished_at_ms IS NULL
      OR (
        typeof(finished_at_ms) = 'integer'
        AND finished_at_ms BETWEEN 0 AND 9007199254740991
      )
    ),
  failure_class TEXT
    CHECK (
      failure_class IS NULL
      OR (typeof(failure_class) = 'text' AND length(trim(failure_class)) > 0)
    ),
  PRIMARY KEY (job_id, generation, attempt_id),
  UNIQUE (job_id, generation, attempt_id, worker_id, epoch),
  FOREIGN KEY (job_id, generation) REFERENCES generations(job_id, generation)
);

CREATE TABLE IF NOT EXISTS leases (
  job_id TEXT NOT NULL
    CHECK (typeof(job_id) = 'text' AND length(trim(job_id)) > 0),
  generation INTEGER NOT NULL
    CHECK (
      typeof(generation) = 'integer'
      AND generation BETWEEN 1 AND 9007199254740991
    ),
  attempt_id TEXT NOT NULL
    CHECK (typeof(attempt_id) = 'text' AND length(trim(attempt_id)) > 0),
  worker_id TEXT NOT NULL
    CHECK (typeof(worker_id) = 'text' AND length(trim(worker_id)) > 0),
  epoch INTEGER NOT NULL
    CHECK (
      typeof(epoch) = 'integer'
      AND epoch BETWEEN 1 AND 9007199254740991
    ),
  heartbeat_at_ms INTEGER NOT NULL
    CHECK (
      typeof(heartbeat_at_ms) = 'integer'
      AND heartbeat_at_ms BETWEEN 0 AND 9007199254740991
    ),
  expires_at_ms INTEGER NOT NULL
    CHECK (
      typeof(expires_at_ms) = 'integer'
      AND expires_at_ms BETWEEN 0 AND 9007199254740991
      AND expires_at_ms >= heartbeat_at_ms
  ),
  PRIMARY KEY (job_id, generation),
  FOREIGN KEY (job_id, generation, attempt_id, worker_id, epoch)
    REFERENCES attempts(job_id, generation, attempt_id, worker_id, epoch),
  FOREIGN KEY (job_id, generation) REFERENCES generations(job_id, generation)
);

CREATE TABLE IF NOT EXISTS events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  generation INTEGER NOT NULL
    CHECK (
      typeof(generation) = 'integer'
      AND generation BETWEEN 1 AND 9007199254740991
    ),
  event_type TEXT NOT NULL
    CHECK (
      typeof(event_type) = 'text'
      AND event_type IN (${EVENT_TYPES.map((eventType) => `'${eventType}'`).join(", ")})
    ),
  event_json TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL
    CHECK (
      typeof(created_at_ms) = 'integer'
      AND created_at_ms BETWEEN 0 AND 9007199254740991
    ),
  FOREIGN KEY (job_id, generation) REFERENCES generations(job_id, generation)
);

CREATE TABLE IF NOT EXISTS protocol_responses (
  request_id TEXT PRIMARY KEY
    CHECK (typeof(request_id) = 'text' AND length(request_id) BETWEEN 1 AND 256),
  request_fingerprint TEXT NOT NULL
    CHECK (
      typeof(request_fingerprint) = 'text'
      AND length(request_fingerprint) = 64
      AND request_fingerprint NOT GLOB '*[^0-9a-f]*'
    ),
  response_json TEXT,
  created_at_ms INTEGER NOT NULL
    CHECK (
      typeof(created_at_ms) = 'integer'
      AND created_at_ms BETWEEN 0 AND 9007199254740991
    )
);

CREATE INDEX IF NOT EXISTS idx_generations_queue
  ON generations (
    pool_id,
    state,
    priority DESC,
    created_at_ms ASC,
    job_id ASC,
    generation ASC
  );

CREATE INDEX IF NOT EXISTS idx_leases_expiry
  ON leases (expires_at_ms ASC, job_id ASC, generation ASC);
`;

function quotedSqlList(values) {
  return values.map((value) => `'${value}'`).join(", ");
}

const V1_SCHEMA_SQL = (() => {
  let sql = SCHEMA_SQL.replace(
    `state IN (${quotedSqlList(GENERATION_STATES)})`,
    `state IN (${quotedSqlList(V1_GENERATION_STATES)})`,
  )
    .replace(
      `state IN (${quotedSqlList(ATTEMPT_STATES)})`,
      `state IN (${quotedSqlList(V1_ATTEMPT_STATES)})`,
    )
    .replace(
      `event_type IN (${quotedSqlList(EVENT_TYPES)})`,
      `event_type IN (${quotedSqlList(V1_EVENT_TYPES)})`,
    );
  const protocolStart = sql.indexOf(
    "\nCREATE TABLE IF NOT EXISTS protocol_responses (",
  );
  const nextIndex = sql.indexOf(
    "\nCREATE INDEX IF NOT EXISTS idx_generations_queue",
    protocolStart,
  );
  if (protocolStart < 0 || nextIndex < 0) {
    throw new Error("invalid scheduler schema definition");
  }
  sql = `${sql.slice(0, protocolStart)}${sql.slice(nextIndex)}`;
  return sql;
})();

const CANDIDATE_V3_SCHEMA_ADDITIONS_SQL = `
CREATE TABLE projects (
  project_id TEXT PRIMARY KEY CHECK (
    length(project_id) BETWEEN 1 AND 256
    AND project_id NOT GLOB '*[^A-Za-z0-9._:-]*'
    AND project_id NOT IN ('.', '..')
  ),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991)
) STRICT;

CREATE TABLE origins (
  origin_id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  origin_thread_hash TEXT NOT NULL CHECK (
    length(origin_thread_hash) = 64
    AND origin_thread_hash NOT GLOB '*[^0-9a-f]*'
  ),
  origin_capability_hash TEXT NOT NULL CHECK (
    length(origin_capability_hash) = 64
    AND origin_capability_hash NOT GLOB '*[^0-9a-f]*'
  ),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  UNIQUE (project_id, origin_thread_hash, origin_capability_hash),
  UNIQUE (origin_id, project_id)
) STRICT;

CREATE TABLE logical_job_origins (
  job_id TEXT NOT NULL,
  origin_id INTEGER NOT NULL CHECK (
    typeof(origin_id) = 'integer'
    AND origin_id BETWEEN 1 AND 9007199254740991
  ),
  project_id TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  ),
  FOREIGN KEY (job_id, project_id) REFERENCES logical_jobs(job_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (origin_id, project_id) REFERENCES origins(origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  PRIMARY KEY (job_id,origin_id),
  UNIQUE (job_id, origin_id, project_id)
) STRICT;

CREATE TABLE legacy_migration_runs (
  run_id TEXT PRIMARY KEY CHECK (
    length(run_id) = 42
    AND substr(run_id,1,10) = 'migration-'
    AND substr(run_id,11) NOT GLOB '*[^0-9a-f]*'
  ),
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  canonical_workspace TEXT NOT NULL CHECK (
    length(canonical_workspace) BETWEEN 1 AND 32767
    AND instr(canonical_workspace,char(0)) = 0
  ),
  workspace_identity_hash TEXT NOT NULL CHECK (
    length(workspace_identity_hash) = 64
    AND workspace_identity_hash NOT GLOB '*[^0-9a-f]*'
  ),
  candidate_protocol_version INTEGER NOT NULL CHECK (
    typeof(candidate_protocol_version) = 'integer'
    AND candidate_protocol_version BETWEEN 1 AND 9007199254740991
  ),
  stale_before_ms INTEGER NOT NULL CHECK (
    typeof(stale_before_ms) = 'integer'
    AND stale_before_ms BETWEEN 0 AND 9007199254740991
  ),
  run_state TEXT NOT NULL CHECK (run_state IN ('MIGRATING','READY','BLOCKED')),
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  )
) STRICT;

CREATE TABLE legacy_migration_sources (
  run_id TEXT NOT NULL REFERENCES legacy_migration_runs(run_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  source_namespace TEXT NOT NULL CHECK (
    length(source_namespace) BETWEEN 1 AND 256
    AND source_namespace NOT GLOB '*[^A-Za-z0-9._:-]*'
    AND source_namespace NOT IN ('.','..')
  ),
  source_kind TEXT NOT NULL CHECK (
    source_kind IN ('CANONICAL','UNDERSCORE_VARIANT','WORKSPACE_DERIVED','THREAD_SCOPED')
  ),
  source_hash TEXT NOT NULL CHECK (
    length(source_hash) = 64
    AND source_hash NOT GLOB '*[^0-9a-f]*'
  ),
  entry_count INTEGER NOT NULL CHECK (
    typeof(entry_count) = 'integer'
    AND entry_count BETWEEN 0 AND 9007199254740991
  ),
  PRIMARY KEY (run_id,source_namespace)
) STRICT;

CREATE TABLE legacy_migration_entries (
  run_id TEXT NOT NULL,
  source_namespace TEXT NOT NULL,
  entry_kind TEXT NOT NULL CHECK (
    entry_kind IN ('STATE','JOB','CACHE','BATCH','NEGATIVE_ADMISSION')
  ),
  logical_identity_hash TEXT NOT NULL CHECK (
    length(logical_identity_hash) = 64
    AND logical_identity_hash NOT GLOB '*[^0-9a-f]*'
  ),
  relative_path_hash TEXT NOT NULL CHECK (
    length(relative_path_hash) = 64
    AND relative_path_hash NOT GLOB '*[^0-9a-f]*'
  ),
  content_hash TEXT NOT NULL CHECK (
    length(content_hash) = 64
    AND content_hash NOT GLOB '*[^0-9a-f]*'
  ),
  byte_count INTEGER NOT NULL CHECK (
    typeof(byte_count) = 'integer'
    AND byte_count BETWEEN 0 AND 1048576
  ),
  protocol_version INTEGER CHECK (
    protocol_version IS NULL
    OR (
      typeof(protocol_version) = 'integer'
      AND protocol_version BETWEEN 1 AND 9007199254740991
    )
  ),
  terminal_state TEXT NOT NULL CHECK (
    terminal_state IN (
      'PASS','CACHED','FAIL','BLOCKED','INCOMPLETE','UNKNOWN','NOT_APPLICABLE'
    )
  ),
  disposition TEXT NOT NULL CHECK (
    disposition IN ('AUDIT_ONLY','QUARANTINED')
  ),
  reason_code TEXT NOT NULL CHECK (
    reason_code IN (
      'STATE_METADATA_ONLY','JOB_METADATA_ONLY','NEGATIVE_ADMISSION_ONLY',
      'SAFE_TERMINAL_AUDIT_ONLY','STALE','UNSAFE_TERMINAL','INCOMPATIBLE_PROTOCOL',
      'MALFORMED','AMBIGUOUS_IDENTITY','COLLISION'
    )
  ),
  PRIMARY KEY (run_id,source_namespace,relative_path_hash),
  FOREIGN KEY (run_id,source_namespace)
    REFERENCES legacy_migration_sources(run_id,source_namespace)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE legacy_migration_collisions (
  run_id TEXT NOT NULL REFERENCES legacy_migration_runs(run_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  collision_kind TEXT NOT NULL CHECK (collision_kind IN ('JOB','CACHE')),
  logical_identity_hash TEXT NOT NULL CHECK (
    length(logical_identity_hash) = 64
    AND logical_identity_hash NOT GLOB '*[^0-9a-f]*'
  ),
  source_count INTEGER NOT NULL CHECK (
    typeof(source_count) = 'integer'
    AND source_count BETWEEN 2 AND 64
  ),
  disposition TEXT NOT NULL CHECK (
    disposition IN ('IDENTICAL_COMPATIBLE','QUARANTINED','UNRESOLVED')
  ),
  reason_code TEXT NOT NULL CHECK (
    reason_code IN (
      'IDENTICAL_PROTOCOL_COMPATIBLE','PROTOCOL_MISMATCH',
      'CONTENT_MISMATCH','AMBIGUOUS_IDENTITY'
    )
  ),
  PRIMARY KEY (run_id,collision_kind,logical_identity_hash)
) STRICT;

CREATE TABLE writer_fence_counters (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  current_fencing_token INTEGER NOT NULL CHECK (
    typeof(current_fencing_token) = 'integer'
    AND current_fencing_token BETWEEN 0 AND 9007199254740991
  )
) STRICT;

CREATE TABLE writer_locks (
  project_id TEXT PRIMARY KEY,
  origin_id INTEGER NOT NULL CHECK (
    typeof(origin_id) = 'integer'
    AND origin_id BETWEEN 1 AND 9007199254740991
  ),
  owner_job_id TEXT NOT NULL,
  owner_generation INTEGER NOT NULL CHECK (
    typeof(owner_generation) = 'integer'
    AND owner_generation BETWEEN 1 AND 9007199254740991
  ),
  owner_lease_epoch INTEGER NOT NULL CHECK (
    typeof(owner_lease_epoch) = 'integer'
    AND owner_lease_epoch BETWEEN 1 AND 9007199254740991
  ),
  fencing_token INTEGER NOT NULL CHECK (
    typeof(fencing_token) = 'integer'
    AND fencing_token BETWEEN 1 AND 9007199254740991
  ),
  canonical_worktree TEXT NOT NULL CHECK (
    length(canonical_worktree) BETWEEN 1 AND 32767
    AND instr(canonical_worktree,char(0)) = 0
  ),
  worktree_identity TEXT NOT NULL CHECK (
    length(worktree_identity) BETWEEN 3 AND 256
    AND worktree_identity NOT GLOB '*[^!-~]*'
  ),
  acquired_at_ms INTEGER NOT NULL CHECK (
    typeof(acquired_at_ms) = 'integer'
    AND acquired_at_ms BETWEEN 0 AND 9007199254740991
  ),
  expires_at_ms INTEGER NOT NULL CHECK (
    typeof(expires_at_ms) = 'integer'
    AND expires_at_ms BETWEEN acquired_at_ms AND 9007199254740991
  ),
  FOREIGN KEY (owner_job_id,origin_id,project_id)
    REFERENCES logical_job_origins(job_id,origin_id,project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (owner_job_id,owner_generation)
    REFERENCES generations(job_id,generation)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE (project_id,fencing_token)
) STRICT;

CREATE TABLE writer_lock_outputs (
  project_id TEXT NOT NULL,
  fencing_token INTEGER NOT NULL CHECK (
    typeof(fencing_token) = 'integer'
    AND fencing_token BETWEEN 1 AND 9007199254740991
  ),
  canonical_output_path TEXT NOT NULL CHECK (
    length(canonical_output_path) BETWEEN 1 AND 32767
    AND instr(canonical_output_path,char(0)) = 0
  ),
  filesystem_identity TEXT NOT NULL CHECK (
    length(filesystem_identity) BETWEEN 3 AND 256
    AND filesystem_identity NOT GLOB '*[^!-~]*'
  ),
  PRIMARY KEY (project_id,canonical_output_path),
  FOREIGN KEY (project_id,fencing_token)
    REFERENCES writer_locks(project_id,fencing_token)
    ON UPDATE RESTRICT ON DELETE CASCADE
) STRICT;

CREATE TABLE cost_budgets (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  ceiling_nano_usd INTEGER NOT NULL CHECK (
    typeof(ceiling_nano_usd) = 'integer'
    AND ceiling_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  spent_nano_usd INTEGER NOT NULL DEFAULT 0 CHECK (
    typeof(spent_nano_usd) = 'integer'
    AND spent_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  reserved_nano_usd INTEGER NOT NULL DEFAULT 0 CHECK (
    typeof(reserved_nano_usd) = 'integer'
    AND reserved_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  pricing_version TEXT NOT NULL CHECK (
    length(pricing_version) BETWEEN 1 AND 128
    AND pricing_version NOT GLOB '*[^!-~]*'
  ),
  updated_at_ms INTEGER NOT NULL CHECK (
    typeof(updated_at_ms) = 'integer'
    AND updated_at_ms BETWEEN 0 AND 9007199254740991
  )
) STRICT;

CREATE TABLE cost_reservations (
  reservation_id TEXT PRIMARY KEY CHECK (
    length(reservation_id) BETWEEN 1 AND 256
    AND reservation_id NOT GLOB '*[^!-~]*'
  ),
  project_id TEXT NOT NULL,
  origin_id INTEGER NOT NULL CHECK (
    typeof(origin_id) = 'integer'
    AND origin_id BETWEEN 1 AND 9007199254740991
  ),
  job_id TEXT NOT NULL CHECK (
    length(job_id) BETWEEN 1 AND 256 AND job_id NOT GLOB '*[^!-~]*'
  ),
  attempt_id TEXT NOT NULL CHECK (
    length(attempt_id) BETWEEN 1 AND 256 AND attempt_id NOT GLOB '*[^!-~]*'
  ),
  state TEXT NOT NULL CHECK (
    state IN ('OPEN', 'UNKNOWN', 'RECONCILED', 'RELEASED')
  ),
  reserved_nano_usd INTEGER NOT NULL CHECK (
    typeof(reserved_nano_usd) = 'integer'
    AND reserved_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  actual_nano_usd INTEGER CHECK (
    actual_nano_usd IS NULL
    OR (
      typeof(actual_nano_usd) = 'integer'
      AND actual_nano_usd BETWEEN 0 AND 9007199254740991
    )
  ),
  pricing_version TEXT NOT NULL CHECK (
    length(pricing_version) BETWEEN 1 AND 128
    AND pricing_version NOT GLOB '*[^!-~]*'
  ),
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  ),
  updated_at_ms INTEGER NOT NULL CHECK (
    typeof(updated_at_ms) = 'integer'
    AND updated_at_ms BETWEEN 0 AND 9007199254740991
  ),
  FOREIGN KEY (project_id) REFERENCES cost_budgets(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (origin_id, project_id) REFERENCES origins(origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE public_resources (
  public_id TEXT PRIMARY KEY,
  resource_kind TEXT NOT NULL CHECK (
    resource_kind IN ('WORKER_JOB', 'HEAD_JOB', 'BATCH', 'SOL_PLAN')
  ),
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  CHECK (
    (resource_kind = 'WORKER_JOB' AND length(public_id) = 35
      AND substr(public_id, 1, 3) = 'DS-'
      AND substr(public_id, 4) NOT GLOB '*[^0-9a-f]*')
    OR (resource_kind = 'HEAD_JOB' AND length(public_id) = 35
      AND substr(public_id, 1, 3) = 'SH-'
      AND substr(public_id, 4) NOT GLOB '*[^0-9a-f]*')
    OR (resource_kind = 'BATCH' AND length(public_id) = 36
      AND substr(public_id, 1, 4) = 'DLB-'
      AND substr(public_id, 5) NOT GLOB '*[^0-9a-f]*')
    OR (resource_kind = 'SOL_PLAN' AND length(public_id) = 36
      AND substr(public_id, 1, 4) = 'SRP-'
      AND substr(public_id, 5) NOT GLOB '*[^0-9a-f]*')
  ),
  FOREIGN KEY (origin_id, project_id) REFERENCES origins(origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE (public_id, origin_id, project_id)
) STRICT;

CREATE TABLE protocol_requests (
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  request_id TEXT NOT NULL CHECK (
    length(request_id) BETWEEN 1 AND 128 AND request_id NOT GLOB '*[^!-~]*'
  ),
  method TEXT NOT NULL CHECK (method IN (
    'batch.metrics', 'batch.status', 'batch.submit', 'head.cancel', 'head.metrics',
    'head.plan', 'head.status', 'head.submit', 'health', 'job.cancel', 'job.status',
    'metrics', 'worker.submit'
  )),
  request_fingerprint TEXT NOT NULL CHECK (
    length(request_fingerprint) = 64
    AND request_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  normalization_source_json TEXT NOT NULL CHECK (
    json_valid(normalization_source_json)
    AND json_type(normalization_source_json) = 'object'
  ),
  normalization_source_hash TEXT NOT NULL CHECK (
    length(normalization_source_hash) = 64
    AND normalization_source_hash NOT GLOB '*[^0-9a-f]*'
  ),
  normalization_source_bytes INTEGER NOT NULL CHECK (
    normalization_source_bytes BETWEEN 2 AND 65536
    AND length(CAST(normalization_source_json AS BLOB)) = normalization_source_bytes
  ),
  request_state TEXT NOT NULL CHECK (
    request_state IN ('ACCEPTED', 'NORMALIZING', 'COMMITTED')
  ),
  normalization_epoch INTEGER NOT NULL DEFAULT 0 CHECK (
    normalization_epoch BETWEEN 0 AND 9007199254740991
  ),
  outcome_json TEXT,
  outcome_hash TEXT,
  outcome_bytes INTEGER,
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  PRIMARY KEY (origin_id, request_id),
  FOREIGN KEY (origin_id, project_id) REFERENCES origins(origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE (origin_id, request_id, project_id),
  CHECK (
    (request_state = 'COMMITTED' AND outcome_json IS NOT NULL
      AND json_valid(outcome_json) AND json_type(outcome_json) = 'object'
      AND length(outcome_hash) = 64 AND outcome_hash NOT GLOB '*[^0-9a-f]*'
      AND outcome_bytes BETWEEN 2 AND 57344
      AND length(CAST(outcome_json AS BLOB)) = outcome_bytes)
    OR (request_state <> 'COMMITTED' AND outcome_json IS NULL
      AND outcome_hash IS NULL AND outcome_bytes IS NULL)
  )
) STRICT;

CREATE TABLE protocol_request_normalization_claims (
  origin_id INTEGER NOT NULL,
  request_id TEXT NOT NULL,
  epoch INTEGER NOT NULL CHECK (epoch BETWEEN 1 AND 9007199254740991),
  owner_token_hash TEXT NOT NULL CHECK (
    length(owner_token_hash) = 64 AND owner_token_hash NOT GLOB '*[^0-9a-f]*'
  ),
  claim_state TEXT NOT NULL CHECK (
    claim_state IN ('CLAIMED', 'COMMITTED', 'EXPIRED', 'ABANDONED')
  ),
  claimed_at_ms INTEGER NOT NULL CHECK (claimed_at_ms BETWEEN 0 AND 9007199254740991),
  expires_at_ms INTEGER NOT NULL CHECK (
    expires_at_ms BETWEEN claimed_at_ms AND 9007199254740991
  ),
  finished_at_ms INTEGER,
  PRIMARY KEY (origin_id, request_id, epoch),
  FOREIGN KEY (origin_id, request_id) REFERENCES protocol_requests(origin_id, request_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CHECK (
    (claim_state = 'CLAIMED' AND finished_at_ms IS NULL)
    OR (claim_state <> 'CLAIMED'
      AND finished_at_ms BETWEEN claimed_at_ms AND 9007199254740991)
  )
) STRICT;

CREATE TABLE protocol_request_resources (
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  relationship TEXT NOT NULL CHECK (relationship IN ('PRIMARY', 'TARGET')),
  public_id TEXT NOT NULL,
  PRIMARY KEY (origin_id, request_id, relationship),
  FOREIGN KEY (origin_id, request_id, project_id)
    REFERENCES protocol_requests(origin_id, request_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (public_id, origin_id, project_id)
    REFERENCES public_resources(public_id, origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE worker_bindings (
  binding_id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  execution_fingerprint TEXT NOT NULL CHECK (
    length(execution_fingerprint) = 64
    AND execution_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  binding_epoch INTEGER NOT NULL CHECK (binding_epoch BETWEEN 1 AND 9007199254740991),
  job_id TEXT NOT NULL,
  generation INTEGER NOT NULL CHECK (generation BETWEEN 1 AND 9007199254740991),
  binding_state TEXT NOT NULL CHECK (
    binding_state IN ('ACTIVE', 'SEALED', 'SUPERSEDED')
  ),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  UNIQUE (project_id, execution_fingerprint, binding_epoch),
  UNIQUE (job_id, generation),
  UNIQUE (binding_id, project_id),
  FOREIGN KEY (job_id, generation) REFERENCES generations(job_id, generation)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (job_id, project_id) REFERENCES logical_jobs(job_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE worker_claims (
  public_id TEXT PRIMARY KEY,
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  binding_id INTEGER NOT NULL,
  claim_state TEXT NOT NULL CHECK (claim_state IN ('ATTACHED', 'DETACHED', 'TERMINAL')),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  CHECK (
    length(public_id) = 35
    AND substr(public_id, 1, 3) = 'DS-'
    AND substr(public_id, 4) NOT GLOB '*[^0-9a-f]*'
  ),
  FOREIGN KEY (public_id, origin_id, project_id)
    REFERENCES public_resources(public_id, origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (binding_id, project_id) REFERENCES worker_bindings(binding_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE (public_id, origin_id, project_id),
  UNIQUE (public_id, origin_id, project_id, binding_id)
) STRICT;

CREATE TABLE head_runs (
  head_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  attempt_fingerprint TEXT NOT NULL CHECK (
    length(attempt_fingerprint) = 64 AND attempt_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  binding_epoch INTEGER NOT NULL CHECK (binding_epoch BETWEEN 1 AND 9007199254740991),
  selected_effort TEXT NOT NULL CHECK (
    selected_effort IN ('medium', 'high', 'xhigh', 'max')
  ),
  run_state TEXT NOT NULL CHECK (
    run_state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELED', 'QUARANTINED')
  ),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  UNIQUE (project_id, attempt_fingerprint, binding_epoch),
  UNIQUE (head_run_id, project_id),
  UNIQUE (head_run_id, project_id, attempt_fingerprint, selected_effort)
) STRICT;

CREATE TABLE result_packets (
  packet_hash TEXT PRIMARY KEY CHECK (
    length(packet_hash) = 64 AND packet_hash NOT GLOB '*[^0-9a-f]*'
  ),
  result_protocol INTEGER NOT NULL CHECK (result_protocol = 3),
  public_status TEXT NOT NULL CHECK (
    public_status IN ('QUEUED', 'RUNNING', 'PASS', 'CACHED', 'FAIL', 'BLOCKED')
  ),
  execution_status TEXT NOT NULL CHECK (
    execution_status IN (
      'ACCEPTED', 'INCOMPLETE', 'BLOCKED', 'PROVIDER_ERROR',
      'CONTRACT_ERROR', 'CANCELLED'
    )
  ),
  evidence_verdict TEXT NOT NULL CHECK (
    evidence_verdict IN (
      'POSITIVE', 'NEGATIVE', 'NULL', 'MIXED', 'UNRESOLVED', 'NOT_APPLICABLE'
    )
  ),
  cache_hit INTEGER NOT NULL CHECK (cache_hit IN (0, 1)),
  canonical_json TEXT NOT NULL CHECK (
    json_valid(canonical_json) AND json_type(canonical_json) = 'object'
  ),
  byte_count INTEGER NOT NULL CHECK (
    byte_count BETWEEN 2 AND 49152
    AND length(CAST(canonical_json AS BLOB)) = byte_count
  ),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  CHECK (
    (public_status IN ('QUEUED', 'RUNNING')
      AND execution_status = 'INCOMPLETE'
      AND evidence_verdict = 'UNRESOLVED'
      AND cache_hit = 0)
    OR (public_status = 'CACHED'
      AND execution_status = 'ACCEPTED'
      AND evidence_verdict <> 'UNRESOLVED'
      AND cache_hit = 1)
    OR (public_status = 'PASS'
      AND execution_status = 'ACCEPTED'
      AND evidence_verdict <> 'UNRESOLVED'
      AND cache_hit = 0)
    OR (public_status = 'FAIL'
      AND execution_status IN ('INCOMPLETE', 'PROVIDER_ERROR', 'CONTRACT_ERROR')
      AND evidence_verdict = 'UNRESOLVED'
      AND cache_hit = 0)
    OR (public_status = 'BLOCKED'
      AND execution_status IN ('BLOCKED', 'CANCELLED')
      AND evidence_verdict = 'UNRESOLVED'
      AND cache_hit = 0)
  )
) STRICT;

CREATE TABLE result_subjects (
  result_subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_kind TEXT NOT NULL CHECK (subject_kind IN ('WORKER', 'HEAD')),
  worker_binding_id INTEGER REFERENCES worker_bindings(binding_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  head_run_id INTEGER REFERENCES head_runs(head_run_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  normalization_source_json TEXT NOT NULL CHECK (
    json_valid(normalization_source_json)
    AND json_type(normalization_source_json) = 'object'
  ),
  normalization_source_hash TEXT NOT NULL CHECK (
    length(normalization_source_hash) = 64
    AND normalization_source_hash NOT GLOB '*[^0-9a-f]*'
  ),
  normalization_source_bytes INTEGER NOT NULL CHECK (
    normalization_source_bytes BETWEEN 2 AND 49152
    AND length(CAST(normalization_source_json AS BLOB)) = normalization_source_bytes
  ),
  normalization_epoch INTEGER NOT NULL DEFAULT 0 CHECK (
    normalization_epoch BETWEEN 0 AND 9007199254740991
  ),
  subject_state TEXT NOT NULL CHECK (
    subject_state IN ('PENDING', 'NORMALIZING', 'NORMALIZED', 'QUARANTINED')
  ),
  accepted_packet_hash TEXT REFERENCES result_packets(packet_hash)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  CHECK (
    (subject_kind = 'WORKER' AND worker_binding_id IS NOT NULL AND head_run_id IS NULL)
    OR (subject_kind = 'HEAD' AND worker_binding_id IS NULL AND head_run_id IS NOT NULL)
  ),
  CHECK (
    (subject_state = 'NORMALIZED' AND accepted_packet_hash IS NOT NULL)
    OR (subject_state <> 'NORMALIZED' AND accepted_packet_hash IS NULL)
  ),
  UNIQUE (worker_binding_id),
  UNIQUE (head_run_id)
) STRICT;

CREATE TABLE result_normalization_claims (
  result_subject_id INTEGER NOT NULL REFERENCES result_subjects(result_subject_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  epoch INTEGER NOT NULL CHECK (epoch BETWEEN 1 AND 9007199254740991),
  owner_token_hash TEXT NOT NULL CHECK (
    length(owner_token_hash) = 64 AND owner_token_hash NOT GLOB '*[^0-9a-f]*'
  ),
  claim_state TEXT NOT NULL CHECK (
    claim_state IN ('CLAIMED', 'COMMITTED', 'EXPIRED', 'ABANDONED')
  ),
  claimed_at_ms INTEGER NOT NULL CHECK (claimed_at_ms BETWEEN 0 AND 9007199254740991),
  expires_at_ms INTEGER NOT NULL CHECK (
    expires_at_ms BETWEEN claimed_at_ms AND 9007199254740991
  ),
  finished_at_ms INTEGER,
  PRIMARY KEY (result_subject_id, epoch),
  CHECK (
    (claim_state = 'CLAIMED' AND finished_at_ms IS NULL)
    OR (claim_state <> 'CLAIMED'
      AND finished_at_ms BETWEEN claimed_at_ms AND 9007199254740991)
  )
) STRICT;

CREATE TABLE sol_plans (
  plan_id TEXT PRIMARY KEY,
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  input_fingerprint TEXT NOT NULL CHECK (
    length(input_fingerprint) = 64 AND input_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  attempt_fingerprint TEXT NOT NULL CHECK (
    length(attempt_fingerprint) = 64 AND attempt_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  decision TEXT NOT NULL CHECK (
    decision IN ('DELEGATE_DEEPLUNA', 'HANDLE_CURRENT', 'START_SOL_HEAD')
  ),
  selected_effort TEXT CHECK (
    selected_effort IS NULL OR selected_effort IN ('medium', 'high', 'xhigh', 'max')
  ),
  max_eligible INTEGER NOT NULL CHECK (max_eligible IN (0, 1)),
  cache_eligible INTEGER NOT NULL CHECK (cache_eligible IN (0, 1)),
  policy_hash TEXT NOT NULL CHECK (
    length(policy_hash) = 64 AND policy_hash NOT GLOB '*[^0-9a-f]*'
  ),
  evidence_hash TEXT NOT NULL CHECK (
    length(evidence_hash) = 64 AND evidence_hash NOT GLOB '*[^0-9a-f]*'
  ),
  governance_hash TEXT NOT NULL CHECK (
    length(governance_hash) = 64 AND governance_hash NOT GLOB '*[^0-9a-f]*'
  ),
  plan_json TEXT NOT NULL CHECK (json_valid(plan_json) AND json_type(plan_json) = 'object'),
  plan_bytes INTEGER NOT NULL CHECK (
    plan_bytes BETWEEN 2 AND 57344 AND length(CAST(plan_json AS BLOB)) = plan_bytes
  ),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  CHECK (
    length(plan_id) = 36
    AND substr(plan_id, 1, 4) = 'SRP-'
    AND substr(plan_id, 5) NOT GLOB '*[^0-9a-f]*'
  ),
  FOREIGN KEY (plan_id, origin_id, project_id)
    REFERENCES public_resources(public_id, origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CHECK (
    (decision = 'DELEGATE_DEEPLUNA' AND selected_effort IS NULL AND max_eligible = 0)
    OR (decision <> 'DELEGATE_DEEPLUNA' AND selected_effort IS NOT NULL
      AND ((selected_effort = 'max') = max_eligible))
  ),
  UNIQUE (plan_id, origin_id, project_id),
  UNIQUE (plan_id, project_id, attempt_fingerprint, selected_effort),
  UNIQUE (
    plan_id,
    project_id,
    attempt_fingerprint,
    decision,
    max_eligible,
    selected_effort
  )
) STRICT;

CREATE TABLE sol_plan_reasons (
  plan_id TEXT NOT NULL REFERENCES sol_plans(plan_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 31),
  reason_code TEXT NOT NULL CHECK (
    reason_code IN (
      'active-effort-matches', 'authority-domain', 'delegation-overhead-dominates',
      'deterministic-deepluna-eligible', 'max-one-shot-eligible', 'reasoning-score'
    )
  ),
  PRIMARY KEY (plan_id, ordinal),
  UNIQUE (plan_id, reason_code)
) STRICT;

CREATE TABLE head_claims (
  public_id TEXT PRIMARY KEY,
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  attempt_fingerprint TEXT NOT NULL CHECK (
    length(attempt_fingerprint) = 64 AND attempt_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  selected_effort TEXT NOT NULL CHECK (
    selected_effort IN ('medium', 'high', 'xhigh', 'max')
  ),
  head_run_id INTEGER NOT NULL,
  claim_state TEXT NOT NULL CHECK (claim_state IN ('ATTACHED', 'DETACHED', 'TERMINAL')),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  CHECK (
    length(public_id) = 35
    AND substr(public_id, 1, 3) = 'SH-'
    AND substr(public_id, 4) NOT GLOB '*[^0-9a-f]*'
  ),
  FOREIGN KEY (public_id, origin_id, project_id)
    REFERENCES public_resources(public_id, origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (plan_id, origin_id, project_id)
    REFERENCES sol_plans(plan_id, origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (plan_id, project_id, attempt_fingerprint, selected_effort)
    REFERENCES sol_plans(plan_id, project_id, attempt_fingerprint, selected_effort)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (head_run_id, project_id, attempt_fingerprint, selected_effort)
    REFERENCES head_runs(head_run_id, project_id, attempt_fingerprint, selected_effort)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE (public_id, origin_id, project_id)
) STRICT;

CREATE TABLE max_attempt_claims (
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  attempt_fingerprint TEXT NOT NULL CHECK (
    length(attempt_fingerprint) = 64 AND attempt_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  plan_id TEXT NOT NULL REFERENCES sol_plans(plan_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  decision TEXT NOT NULL CHECK (decision = 'START_SOL_HEAD'),
  max_eligible INTEGER NOT NULL CHECK (max_eligible = 1),
  selected_effort TEXT NOT NULL CHECK (selected_effort = 'max'),
  head_run_id INTEGER NOT NULL,
  claimed_at_ms INTEGER NOT NULL CHECK (claimed_at_ms BETWEEN 0 AND 9007199254740991),
  PRIMARY KEY (project_id, attempt_fingerprint),
  FOREIGN KEY (
    plan_id,
    project_id,
    attempt_fingerprint,
    decision,
    max_eligible,
    selected_effort
  ) REFERENCES sol_plans(
    plan_id,
    project_id,
    attempt_fingerprint,
    decision,
    max_eligible,
    selected_effort
  ) ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (head_run_id, project_id, attempt_fingerprint, selected_effort)
    REFERENCES head_runs(head_run_id, project_id, attempt_fingerprint, selected_effort)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE batch_runs (
  batch_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  batch_fingerprint TEXT NOT NULL CHECK (
    length(batch_fingerprint) = 64 AND batch_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  binding_epoch INTEGER NOT NULL CHECK (binding_epoch BETWEEN 1 AND 9007199254740991),
  node_count INTEGER NOT NULL CHECK (node_count BETWEEN 1 AND 20),
  requested_concurrency INTEGER NOT NULL CHECK (requested_concurrency BETWEEN 1 AND 20),
  run_state TEXT NOT NULL CHECK (
    run_state IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELED', 'BLOCKED')
  ),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  UNIQUE (project_id, batch_fingerprint, binding_epoch),
  UNIQUE (batch_run_id, project_id)
) STRICT;

CREATE TABLE batch_claims (
  public_id TEXT PRIMARY KEY,
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  batch_run_id INTEGER NOT NULL,
  claim_state TEXT NOT NULL CHECK (claim_state IN ('ATTACHED', 'DETACHED', 'TERMINAL')),
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  CHECK (
    length(public_id) = 36
    AND substr(public_id, 1, 4) = 'DLB-'
    AND substr(public_id, 5) NOT GLOB '*[^0-9a-f]*'
  ),
  FOREIGN KEY (public_id, origin_id, project_id)
    REFERENCES public_resources(public_id, origin_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (batch_run_id, project_id) REFERENCES batch_runs(batch_run_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE (public_id, origin_id, project_id, batch_run_id)
) STRICT;

CREATE TABLE batch_nodes (
  batch_run_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  node_key TEXT NOT NULL CHECK (
    length(node_key) BETWEEN 1 AND 128
    AND node_key NOT GLOB '*[^A-Za-z0-9._:-]*'
    AND node_key NOT IN ('.', '..')
  ),
  ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 19),
  template_fingerprint TEXT NOT NULL CHECK (
    length(template_fingerprint) = 64
    AND template_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  node_state TEXT NOT NULL CHECK (
    node_state IN (
      'WAITING', 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'BLOCKED', 'CANCELED'
    )
  ),
  worker_binding_id INTEGER,
  created_at_ms INTEGER NOT NULL CHECK (created_at_ms BETWEEN 0 AND 9007199254740991),
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  PRIMARY KEY (batch_run_id, node_key),
  UNIQUE (batch_run_id, ordinal),
  UNIQUE (batch_run_id, node_key, project_id),
  UNIQUE (batch_run_id, node_key, project_id, worker_binding_id),
  FOREIGN KEY (batch_run_id, project_id) REFERENCES batch_runs(batch_run_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (worker_binding_id, project_id)
    REFERENCES worker_bindings(binding_id, project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE batch_edges (
  batch_run_id INTEGER NOT NULL,
  source_node_key TEXT NOT NULL,
  target_node_key TEXT NOT NULL,
  PRIMARY KEY (batch_run_id, source_node_key, target_node_key),
  FOREIGN KEY (batch_run_id, source_node_key) REFERENCES batch_nodes(batch_run_id, node_key)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (batch_run_id, target_node_key) REFERENCES batch_nodes(batch_run_id, node_key)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CHECK (source_node_key <> target_node_key)
) STRICT;

CREATE TABLE batch_dependency_states (
  batch_run_id INTEGER NOT NULL,
  source_node_key TEXT NOT NULL,
  target_node_key TEXT NOT NULL,
  epoch INTEGER NOT NULL DEFAULT 0 CHECK (epoch BETWEEN 0 AND 9007199254740991),
  dependency_state TEXT NOT NULL CHECK (
    dependency_state IN ('WAITING', 'SATISFIED', 'BLOCKED')
  ),
  reason_code TEXT,
  observed_packet_hash TEXT REFERENCES result_packets(packet_hash)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  updated_at_ms INTEGER NOT NULL CHECK (updated_at_ms BETWEEN 0 AND 9007199254740991),
  PRIMARY KEY (batch_run_id, source_node_key, target_node_key),
  FOREIGN KEY (batch_run_id, source_node_key, target_node_key)
    REFERENCES batch_edges(batch_run_id, source_node_key, target_node_key)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CHECK (
    (dependency_state = 'WAITING' AND reason_code IS NULL AND observed_packet_hash IS NULL)
    OR (dependency_state <> 'WAITING' AND reason_code IS NOT NULL
      AND length(reason_code) BETWEEN 1 AND 64
      AND reason_code NOT GLOB '*[^A-Z0-9_]*')
  )
) STRICT;

CREATE TABLE batch_node_accepted_verdicts (
  batch_run_id INTEGER NOT NULL,
  node_key TEXT NOT NULL,
  evidence_verdict TEXT NOT NULL CHECK (
    evidence_verdict IN ('POSITIVE', 'NEGATIVE', 'NULL', 'MIXED', 'NOT_APPLICABLE')
  ),
  PRIMARY KEY (batch_run_id, node_key, evidence_verdict),
  FOREIGN KEY (batch_run_id, node_key) REFERENCES batch_nodes(batch_run_id, node_key)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE batch_claim_nodes (
  batch_public_id TEXT NOT NULL,
  origin_id INTEGER NOT NULL,
  project_id TEXT NOT NULL,
  batch_run_id INTEGER NOT NULL,
  node_key TEXT NOT NULL,
  worker_public_id TEXT NOT NULL,
  worker_binding_id INTEGER NOT NULL,
  PRIMARY KEY (batch_public_id, node_key),
  FOREIGN KEY (batch_public_id, origin_id, project_id, batch_run_id)
    REFERENCES batch_claims(public_id, origin_id, project_id, batch_run_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (batch_run_id, node_key, project_id, worker_binding_id)
    REFERENCES batch_nodes(batch_run_id, node_key, project_id, worker_binding_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (worker_public_id, origin_id, project_id, worker_binding_id)
    REFERENCES worker_claims(public_id, origin_id, project_id, binding_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE UNIQUE INDEX idx_logical_jobs_project_job ON logical_jobs(job_id, project_id);
CREATE INDEX idx_origins_project ON origins(project_id, origin_id);
CREATE INDEX idx_logical_job_origins_origin
  ON logical_job_origins(origin_id, project_id, job_id);
CREATE INDEX idx_legacy_migration_runs_project
  ON legacy_migration_runs(project_id,created_at_ms,run_id);
CREATE INDEX idx_legacy_migration_entries_identity
  ON legacy_migration_entries(run_id,entry_kind,logical_identity_hash);
CREATE INDEX idx_legacy_migration_collisions_disposition
  ON legacy_migration_collisions(run_id,disposition,collision_kind);
CREATE INDEX idx_writer_locks_expiry
  ON writer_locks(expires_at_ms,project_id);
CREATE INDEX idx_writer_lock_outputs_path
  ON writer_lock_outputs(canonical_output_path,project_id);
CREATE INDEX idx_public_resources_origin_kind
  ON public_resources(origin_id, resource_kind, created_at_ms, public_id);
CREATE INDEX idx_protocol_requests_state
  ON protocol_requests(request_state, updated_at_ms, origin_id, request_id);
CREATE UNIQUE INDEX idx_protocol_request_claim_active
  ON protocol_request_normalization_claims(origin_id, request_id)
  WHERE claim_state = 'CLAIMED';
CREATE INDEX idx_protocol_request_claim_expiry
  ON protocol_request_normalization_claims(expires_at_ms, origin_id, request_id, epoch)
  WHERE claim_state = 'CLAIMED';
CREATE INDEX idx_protocol_request_resources_public
  ON protocol_request_resources(public_id, origin_id);
CREATE UNIQUE INDEX idx_worker_bindings_active
  ON worker_bindings(project_id, execution_fingerprint)
  WHERE binding_state = 'ACTIVE';
CREATE INDEX idx_worker_claims_origin_state
  ON worker_claims(origin_id, claim_state, public_id);
CREATE INDEX idx_worker_claims_binding
  ON worker_claims(binding_id, claim_state, public_id);
CREATE UNIQUE INDEX idx_head_runs_active
  ON head_runs(project_id, attempt_fingerprint)
  WHERE run_state IN ('QUEUED', 'RUNNING');
CREATE INDEX idx_head_claims_origin_state
  ON head_claims(origin_id, claim_state, public_id);
CREATE INDEX idx_result_subjects_state
  ON result_subjects(subject_state, updated_at_ms, result_subject_id);
CREATE UNIQUE INDEX idx_result_claim_active
  ON result_normalization_claims(result_subject_id)
  WHERE claim_state = 'CLAIMED';
CREATE INDEX idx_result_claim_expiry
  ON result_normalization_claims(expires_at_ms, result_subject_id, epoch)
  WHERE claim_state = 'CLAIMED';
CREATE UNIQUE INDEX idx_batch_runs_active
  ON batch_runs(project_id, batch_fingerprint)
  WHERE run_state IN ('QUEUED', 'RUNNING');
CREATE INDEX idx_batch_claims_origin_state
  ON batch_claims(origin_id, claim_state, public_id);
CREATE INDEX idx_batch_nodes_state
  ON batch_nodes(batch_run_id, node_state, ordinal, node_key);
CREATE INDEX idx_batch_dependencies_target
  ON batch_dependency_states(
    batch_run_id, target_node_key, dependency_state, source_node_key
  );

CREATE TRIGGER trg_protocol_responses_v3_read_only_insert
BEFORE INSERT ON protocol_responses
BEGIN
  SELECT RAISE(ABORT, 'legacy protocol audit is read-only');
END;

CREATE TRIGGER trg_protocol_responses_v3_read_only_update
BEFORE UPDATE ON protocol_responses
BEGIN
  SELECT RAISE(ABORT, 'legacy protocol audit is read-only');
END;

CREATE TRIGGER trg_protocol_responses_v3_read_only_delete
BEFORE DELETE ON protocol_responses
BEGIN
  SELECT RAISE(ABORT, 'legacy protocol audit is read-only');
END;
`;

const CANDIDATE_V4_SCHEMA_ADDITIONS_SQL = `
CREATE TABLE transmission_project_budgets (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  ceiling_nano_usd INTEGER NOT NULL CHECK (
    typeof(ceiling_nano_usd) = 'integer'
    AND ceiling_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  spent_nano_usd INTEGER NOT NULL DEFAULT 0 CHECK (
    typeof(spent_nano_usd) = 'integer'
    AND spent_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  reserved_nano_usd INTEGER NOT NULL DEFAULT 0 CHECK (
    typeof(reserved_nano_usd) = 'integer'
    AND reserved_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  pricing_version TEXT NOT NULL CHECK (
    length(pricing_version) BETWEEN 1 AND 128
    AND pricing_version NOT GLOB '*[^!-~]*'
  ),
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  ),
  updated_at_ms INTEGER NOT NULL CHECK (
    typeof(updated_at_ms) = 'integer'
    AND updated_at_ms BETWEEN created_at_ms AND 9007199254740991
  ),
  CHECK (
    spent_nano_usd <= ceiling_nano_usd
    AND reserved_nano_usd <= ceiling_nano_usd - spent_nano_usd
  )
) STRICT;

CREATE TABLE provider_job_limits (
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  job_id TEXT NOT NULL CHECK (
    length(job_id) BETWEEN 1 AND 256 AND job_id NOT GLOB '*[^!-~]*'
  ),
  maximum_provider_calls INTEGER NOT NULL CHECK (
    typeof(maximum_provider_calls) = 'integer'
    AND maximum_provider_calls BETWEEN 1 AND 6
  ),
  maximum_input_tokens INTEGER NOT NULL CHECK (
    typeof(maximum_input_tokens) = 'integer'
    AND maximum_input_tokens BETWEEN 1 AND 9007199254740991
  ),
  maximum_cached_input_tokens INTEGER NOT NULL CHECK (
    typeof(maximum_cached_input_tokens) = 'integer'
    AND maximum_cached_input_tokens BETWEEN 0 AND maximum_input_tokens
  ),
  maximum_output_tokens_total INTEGER NOT NULL CHECK (
    typeof(maximum_output_tokens_total) = 'integer'
    AND maximum_output_tokens_total BETWEEN 1 AND 9007199254740991
  ),
  maximum_total_tokens INTEGER NOT NULL CHECK (
    typeof(maximum_total_tokens) = 'integer'
    AND maximum_total_tokens BETWEEN maximum_input_tokens AND 9007199254740991
    AND maximum_total_tokens >= maximum_output_tokens_total
  ),
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  ),
  updated_at_ms INTEGER NOT NULL CHECK (
    typeof(updated_at_ms) = 'integer'
    AND updated_at_ms BETWEEN created_at_ms AND 9007199254740991
  ),
  PRIMARY KEY (project_id,job_id)
) STRICT;

CREATE TABLE provider_transmissions (
  transmission_id TEXT PRIMARY KEY CHECK (
    length(transmission_id) BETWEEN 1 AND 256
    AND transmission_id NOT GLOB '*[^!-~]*'
  ),
  project_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  origin_id INTEGER NOT NULL CHECK (
    typeof(origin_id) = 'integer'
    AND origin_id BETWEEN 1 AND 9007199254740991
  ),
  transmission_ordinal INTEGER NOT NULL CHECK (
    typeof(transmission_ordinal) = 'integer'
    AND transmission_ordinal BETWEEN 1 AND 9007199254740991
  ),
  attempt_id TEXT NOT NULL CHECK (
    length(attempt_id) BETWEEN 1 AND 256 AND attempt_id NOT GLOB '*[^!-~]*'
  ),
  route TEXT NOT NULL CHECK (
    length(route) BETWEEN 1 AND 32 AND route NOT GLOB '*[^A-Z0-9_-]*'
  ),
  provider TEXT NOT NULL CHECK (
    length(provider) BETWEEN 1 AND 128 AND provider NOT GLOB '*[^!-~]*'
  ),
  model TEXT NOT NULL CHECK (
    length(model) BETWEEN 1 AND 256 AND model NOT GLOB '*[^!-~]*'
  ),
  service_tier TEXT NOT NULL CHECK (
    length(service_tier) BETWEEN 1 AND 64 AND service_tier NOT GLOB '*[^!-~]*'
  ),
  reasoning_effort TEXT NOT NULL CHECK (
    length(reasoning_effort) BETWEEN 1 AND 32
    AND reasoning_effort NOT GLOB '*[^A-Za-z0-9_-]*'
  ),
  pricing_version TEXT NOT NULL CHECK (
    length(pricing_version) BETWEEN 1 AND 128
    AND pricing_version NOT GLOB '*[^!-~]*'
  ),
  state TEXT NOT NULL CHECK (
    state IN ('RESERVED','TRANSMITTING','RECONCILED','UNKNOWN','RELEASED')
  ),
  reserved_nano_usd INTEGER NOT NULL CHECK (
    typeof(reserved_nano_usd) = 'integer'
    AND reserved_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  actual_nano_usd INTEGER CHECK (
    actual_nano_usd IS NULL
    OR (
      typeof(actual_nano_usd) = 'integer'
      AND actual_nano_usd BETWEEN 0 AND 9007199254740991
    )
  ),
  estimated_input_tokens INTEGER NOT NULL CHECK (
    typeof(estimated_input_tokens) = 'integer'
    AND estimated_input_tokens BETWEEN 0 AND 9007199254740991
  ),
  estimated_output_tokens INTEGER NOT NULL CHECK (
    typeof(estimated_output_tokens) = 'integer'
    AND estimated_output_tokens BETWEEN 1 AND 9007199254740991
  ),
  input_tokens INTEGER CHECK (
    input_tokens IS NULL
    OR (typeof(input_tokens) = 'integer' AND input_tokens BETWEEN 0 AND 9007199254740991)
  ),
  cached_input_tokens INTEGER CHECK (
    cached_input_tokens IS NULL
    OR (
      typeof(cached_input_tokens) = 'integer'
      AND cached_input_tokens BETWEEN 0 AND 9007199254740991
    )
  ),
  output_tokens INTEGER CHECK (
    output_tokens IS NULL
    OR (typeof(output_tokens) = 'integer' AND output_tokens BETWEEN 0 AND 9007199254740991)
  ),
  total_tokens INTEGER CHECK (
    total_tokens IS NULL
    OR (typeof(total_tokens) = 'integer' AND total_tokens BETWEEN 0 AND 9007199254740991)
  ),
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  ),
  transmitted_at_ms INTEGER CHECK (
    transmitted_at_ms IS NULL
    OR (
      typeof(transmitted_at_ms) = 'integer'
      AND transmitted_at_ms BETWEEN created_at_ms AND 9007199254740991
    )
  ),
  finished_at_ms INTEGER CHECK (
    finished_at_ms IS NULL
    OR (
      typeof(finished_at_ms) = 'integer'
      AND finished_at_ms BETWEEN created_at_ms AND 9007199254740991
    )
  ),
  updated_at_ms INTEGER NOT NULL CHECK (
    typeof(updated_at_ms) = 'integer'
    AND updated_at_ms BETWEEN created_at_ms AND 9007199254740991
  ),
  FOREIGN KEY (project_id) REFERENCES transmission_project_budgets(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (project_id,job_id) REFERENCES provider_job_limits(project_id,job_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (origin_id,project_id) REFERENCES origins(origin_id,project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  UNIQUE (project_id,job_id,transmission_ordinal),
  CHECK (
    (state = 'RESERVED'
      AND transmitted_at_ms IS NULL AND finished_at_ms IS NULL
      AND actual_nano_usd IS NULL AND input_tokens IS NULL
      AND cached_input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL)
    OR (state = 'TRANSMITTING'
      AND transmitted_at_ms IS NOT NULL AND finished_at_ms IS NULL
      AND actual_nano_usd IS NULL AND input_tokens IS NULL
      AND cached_input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL)
    OR (state = 'UNKNOWN'
      AND transmitted_at_ms IS NOT NULL AND finished_at_ms IS NOT NULL
      AND actual_nano_usd IS NULL AND input_tokens IS NULL
      AND cached_input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL)
    OR (state = 'RELEASED'
      AND finished_at_ms IS NOT NULL AND actual_nano_usd = 0
      AND input_tokens IS NULL AND cached_input_tokens IS NULL
      AND output_tokens IS NULL AND total_tokens IS NULL)
    OR (state = 'RECONCILED'
      AND transmitted_at_ms IS NOT NULL AND finished_at_ms IS NOT NULL
      AND actual_nano_usd IS NOT NULL AND input_tokens IS NOT NULL
      AND cached_input_tokens IS NOT NULL AND output_tokens IS NOT NULL
      AND total_tokens = input_tokens + output_tokens
      AND cached_input_tokens <= input_tokens)
  )
) STRICT;

CREATE INDEX idx_provider_job_limits_project
  ON provider_job_limits(project_id,job_id);
CREATE INDEX idx_provider_transmissions_project_job
  ON provider_transmissions(project_id,job_id,transmission_ordinal);
CREATE INDEX idx_provider_transmissions_project_state
  ON provider_transmissions(project_id,state,updated_at_ms,transmission_id);
CREATE UNIQUE INDEX idx_worker_claims_origin_binding
  ON worker_claims(origin_id,binding_id);

CREATE TRIGGER trg_cost_budgets_v4_read_only_insert
BEFORE INSERT ON cost_budgets
BEGIN
  SELECT RAISE(ABORT, 'legacy cost tables are read-only under schema v4');
END;
CREATE TRIGGER trg_cost_budgets_v4_read_only_update
BEFORE UPDATE ON cost_budgets
BEGIN
  SELECT RAISE(ABORT, 'legacy cost tables are read-only under schema v4');
END;
CREATE TRIGGER trg_cost_budgets_v4_read_only_delete
BEFORE DELETE ON cost_budgets
BEGIN
  SELECT RAISE(ABORT, 'legacy cost tables are read-only under schema v4');
END;
CREATE TRIGGER trg_cost_reservations_v4_read_only_insert
BEFORE INSERT ON cost_reservations
BEGIN
  SELECT RAISE(ABORT, 'legacy cost tables are read-only under schema v4');
END;
CREATE TRIGGER trg_cost_reservations_v4_read_only_update
BEFORE UPDATE ON cost_reservations
BEGIN
  SELECT RAISE(ABORT, 'legacy cost tables are read-only under schema v4');
END;
CREATE TRIGGER trg_cost_reservations_v4_read_only_delete
BEFORE DELETE ON cost_reservations
BEGIN
  SELECT RAISE(ABORT, 'legacy cost tables are read-only under schema v4');
END;
`;

const CANDIDATE_V5_SCHEMA_ADDITIONS_SQL = `
CREATE TABLE accounting_policy_transitions (
  transition_id TEXT PRIMARY KEY CHECK (
    length(transition_id) = 36
    AND substr(transition_id, 1, 4) = 'APT-'
    AND substr(transition_id, 5) NOT GLOB '*[^0-9a-f]*'
  ),
  project_id TEXT NOT NULL REFERENCES projects(project_id)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  source_pricing_version TEXT NOT NULL CHECK (
    length(source_pricing_version) BETWEEN 1 AND 128
    AND source_pricing_version NOT GLOB '*[^!-~]*'
  ),
  target_pricing_version TEXT NOT NULL CHECK (
    length(target_pricing_version) BETWEEN 1 AND 128
    AND target_pricing_version NOT GLOB '*[^!-~]*'
  ),
  transition_fingerprint TEXT NOT NULL UNIQUE CHECK (
    length(transition_fingerprint) = 64
    AND transition_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  ceiling_before_nano_usd INTEGER NOT NULL CHECK (
    typeof(ceiling_before_nano_usd) = 'integer'
    AND ceiling_before_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  ceiling_after_nano_usd INTEGER NOT NULL CHECK (
    typeof(ceiling_after_nano_usd) = 'integer'
    AND ceiling_after_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  spent_before_nano_usd INTEGER NOT NULL CHECK (
    typeof(spent_before_nano_usd) = 'integer'
    AND spent_before_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  spent_after_nano_usd INTEGER NOT NULL CHECK (
    typeof(spent_after_nano_usd) = 'integer'
    AND spent_after_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  reserved_before_nano_usd INTEGER NOT NULL CHECK (
    typeof(reserved_before_nano_usd) = 'integer'
    AND reserved_before_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  reserved_after_nano_usd INTEGER NOT NULL CHECK (
    typeof(reserved_after_nano_usd) = 'integer'
    AND reserved_after_nano_usd BETWEEN 0 AND 9007199254740991
  ),
  reconciled_transmissions INTEGER NOT NULL CHECK (
    typeof(reconciled_transmissions) = 'integer'
    AND reconciled_transmissions BETWEEN 0 AND 9007199254740991
  ),
  released_transmissions INTEGER NOT NULL CHECK (
    typeof(released_transmissions) = 'integer'
    AND released_transmissions BETWEEN 0 AND 9007199254740991
  ),
  active_transmissions INTEGER NOT NULL CHECK (
    typeof(active_transmissions) = 'integer'
    AND active_transmissions BETWEEN 0 AND 9007199254740991
  ),
  unknown_transmissions INTEGER NOT NULL CHECK (
    typeof(unknown_transmissions) = 'integer'
    AND unknown_transmissions BETWEEN 0 AND 9007199254740991
  ),
  active_workers INTEGER NOT NULL CHECK (
    typeof(active_workers) = 'integer'
    AND active_workers BETWEEN 0 AND 9007199254740991
  ),
  active_heads INTEGER NOT NULL CHECK (
    typeof(active_heads) = 'integer'
    AND active_heads BETWEEN 0 AND 9007199254740991
  ),
  precondition_hash TEXT NOT NULL CHECK (
    length(precondition_hash) = 64
    AND precondition_hash NOT GLOB '*[^0-9a-f]*'
  ),
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  ),
  UNIQUE (project_id, source_pricing_version, target_pricing_version),
  CHECK (source_pricing_version <> target_pricing_version),
  CHECK (ceiling_before_nano_usd = ceiling_after_nano_usd),
  CHECK (spent_before_nano_usd = spent_after_nano_usd),
  CHECK (reserved_before_nano_usd = 0 AND reserved_after_nano_usd = 0),
  CHECK (active_transmissions = 0 AND unknown_transmissions = 0),
  CHECK (active_workers = 0 AND active_heads = 0)
) STRICT;

CREATE TABLE head_producer_attempts (
  head_run_id INTEGER PRIMARY KEY,
  project_id TEXT NOT NULL,
  producer_job_id TEXT NOT NULL UNIQUE CHECK (
    length(producer_job_id) = 35
    AND substr(producer_job_id, 1, 3) = 'SH-'
    AND substr(producer_job_id, 4) NOT GLOB '*[^0-9a-f]*'
  ),
  attempt_fingerprint TEXT NOT NULL CHECK (
    length(attempt_fingerprint) = 64
    AND attempt_fingerprint NOT GLOB '*[^0-9a-f]*'
  ),
  plan_id TEXT NOT NULL CHECK (
    length(plan_id) = 36
    AND substr(plan_id, 1, 4) = 'SRP-'
    AND substr(plan_id, 5) NOT GLOB '*[^0-9a-f]*'
  ),
  selected_effort TEXT NOT NULL CHECK (
    selected_effort IN ('medium', 'high', 'xhigh', 'max')
  ),
  producer_state TEXT NOT NULL CHECK (
    producer_state IN (
      'QUEUED','CLAIMED','RUNNING','SUCCEEDED','FAILED',
      'BLOCKED','UNKNOWN','CANCELED'
    )
  ),
  external_start_possible INTEGER NOT NULL CHECK (
    external_start_possible IN (0, 1)
  ),
  process_boot_id TEXT CHECK (
    process_boot_id IS NULL
    OR (
      length(process_boot_id) = 35
      AND substr(process_boot_id, 1, 3) = 'DI-'
      AND substr(process_boot_id, 4) NOT GLOB '*[^0-9a-f]*'
    )
  ),
  owner_pid INTEGER CHECK (
    owner_pid IS NULL
    OR (
      typeof(owner_pid) = 'integer'
      AND owner_pid BETWEEN 1 AND 9007199254740991
    )
  ),
  terminal_result_hash TEXT CHECK (
    terminal_result_hash IS NULL
    OR (
      length(terminal_result_hash) = 64
      AND terminal_result_hash NOT GLOB '*[^0-9a-f]*'
    )
  ),
  claimed_at_ms INTEGER CHECK (
    claimed_at_ms IS NULL
    OR (
      typeof(claimed_at_ms) = 'integer'
      AND claimed_at_ms BETWEEN 0 AND 9007199254740991
    )
  ),
  started_at_ms INTEGER CHECK (
    started_at_ms IS NULL
    OR (
      typeof(started_at_ms) = 'integer'
      AND started_at_ms BETWEEN 0 AND 9007199254740991
    )
  ),
  finished_at_ms INTEGER CHECK (
    finished_at_ms IS NULL
    OR (
      typeof(finished_at_ms) = 'integer'
      AND finished_at_ms BETWEEN 0 AND 9007199254740991
    )
  ),
  created_at_ms INTEGER NOT NULL CHECK (
    typeof(created_at_ms) = 'integer'
    AND created_at_ms BETWEEN 0 AND 9007199254740991
  ),
  updated_at_ms INTEGER NOT NULL CHECK (
    typeof(updated_at_ms) = 'integer'
    AND updated_at_ms BETWEEN created_at_ms AND 9007199254740991
  ),
  FOREIGN KEY (
    head_run_id, project_id, attempt_fingerprint, selected_effort
  ) REFERENCES head_runs(
    head_run_id, project_id, attempt_fingerprint, selected_effort
  ) ON UPDATE RESTRICT ON DELETE RESTRICT,
  FOREIGN KEY (
    plan_id, project_id, attempt_fingerprint, selected_effort
  ) REFERENCES sol_plans(
    plan_id, project_id, attempt_fingerprint, selected_effort
  ) ON UPDATE RESTRICT ON DELETE RESTRICT,
  CHECK (
    (producer_state = 'QUEUED'
      AND external_start_possible = 0
      AND process_boot_id IS NULL AND owner_pid IS NULL
      AND terminal_result_hash IS NULL
      AND claimed_at_ms IS NULL AND started_at_ms IS NULL AND finished_at_ms IS NULL)
    OR (producer_state = 'CLAIMED'
      AND external_start_possible = 0
      AND process_boot_id IS NOT NULL AND owner_pid IS NOT NULL
      AND terminal_result_hash IS NULL
      AND claimed_at_ms IS NOT NULL AND started_at_ms IS NULL AND finished_at_ms IS NULL)
    OR (producer_state = 'RUNNING'
      AND external_start_possible = 1
      AND process_boot_id IS NOT NULL AND owner_pid IS NOT NULL
      AND terminal_result_hash IS NULL
      AND claimed_at_ms IS NOT NULL AND started_at_ms IS NOT NULL
      AND finished_at_ms IS NULL)
    OR (producer_state IN ('SUCCEEDED','FAILED','BLOCKED','UNKNOWN','CANCELED')
      AND terminal_result_hash IS NOT NULL
      AND finished_at_ms IS NOT NULL)
  )
) STRICT;

CREATE INDEX idx_accounting_policy_transitions_project
  ON accounting_policy_transitions(project_id,created_at_ms,transition_id);
CREATE INDEX idx_head_producer_attempts_project_state
  ON head_producer_attempts(project_id,producer_state,updated_at_ms,producer_job_id);
`;

const GENERATION_SELECT = `
SELECT
  g.job_id,
  g.generation,
  g.task_id,
  g.role,
  g.pool_id,
  g.priority,
  g.state,
  g.contract_hash,
  g.input_fingerprint,
  g.maximum_attempts,
  g.contract_json,
  g.accepted_result_hash,
  g.diagnostic_enqueued,
  g.created_at_ms,
  g.updated_at_ms
FROM generations AS g
`;

function requireContractIdentity(contract) {
  if (contract === null || typeof contract !== "object") {
    throw new TypeError("contract must be an object");
  }
  for (const field of REQUIRED_TEXT_FIELDS) {
    if (typeof contract[field] !== "string" || contract[field].trim() === "") {
      throw new TypeError(`${field} must be a nonblank string`);
    }
  }
}

function requireSafeInteger(value, message, minimum = Number.MIN_SAFE_INTEGER) {
  if (!Number.isSafeInteger(value) || value < minimum) {
    throw new TypeError(message);
  }
  return value;
}

function requireNonblankString(value, message) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TypeError(message);
  }
  return value;
}

function requireBoundedString(value, message, maximumLength) {
  const exact = requireNonblankString(value, message);
  if (exact.length > maximumLength || exact.includes("\0")) {
    throw new TypeError(message);
  }
  return exact;
}

function requireNow(now) {
  return requireSafeInteger(now, "now must return a finite nonnegative safe integer", 0);
}

function requireLeaseIdentity(identity) {
  if (identity === null || typeof identity !== "object") {
    throw new TypeError("lease identity must be an object");
  }
  return {
    jobId: requireNonblankString(identity.jobId, "jobId must be a nonblank string"),
    generation: requireSafeInteger(
      identity.generation,
      "generation must be a positive safe integer",
      1,
    ),
    attemptId: requireNonblankString(
      identity.attemptId,
      "attemptId must be a nonblank string",
    ),
    workerId: requireNonblankString(identity.workerId, "workerId must be a nonblank string"),
    epoch: requireSafeInteger(identity.epoch, "epoch must be a positive safe integer", 1),
  };
}

function safeLeaseExpiry(now, leaseMs) {
  return requireSafeInteger(
    now + leaseMs,
    "lease expiry must be a finite nonnegative safe integer",
    0,
  );
}

function stateError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function unsupportedSchemaVersion() {
  return stateError("UNSUPPORTED_SCHEMA_VERSION", "unsupported scheduler schema version");
}

function requireRetryReasonCode(value) {
  if (typeof value !== "string" || !RETRY_REASON_CODES.has(value)) {
    throw stateError("INVALID_RETRY_REASON", "invalid retry reason code");
  }
  return value;
}

function canonicalPayloadJson(payload) {
  const ancestors = new Set();

  function serialize(value) {
    if (value === null) return "null";
    if (typeof value === "string" || typeof value === "boolean") {
      return JSON.stringify(value);
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) throw new TypeError("nonfinite number");
      return JSON.stringify(value);
    }
    if (typeof value !== "object") throw new TypeError("unsupported value");
    if (ancestors.has(value)) throw new TypeError("cyclic value");
    if (Object.getOwnPropertySymbols(value).length !== 0) {
      throw new TypeError("symbol property");
    }

    ancestors.add(value);
    try {
      if (Array.isArray(value)) {
        const keys = Object.keys(value);
        if (
          keys.length !== value.length ||
          keys.some((key, index) => key !== String(index))
        ) {
          throw new TypeError("sparse or extended array");
        }
        return `[${keys
          .map((key) => {
            const descriptor = Object.getOwnPropertyDescriptor(value, key);
            if (!descriptor?.enumerable || !("value" in descriptor)) {
              throw new TypeError("accessor array element");
            }
            return serialize(descriptor.value);
          })
          .join(",")}]`;
      }

      const prototype = Object.getPrototypeOf(value);
      if (prototype !== Object.prototype && prototype !== null) {
        throw new TypeError("non-plain object");
      }
      const keys = Object.keys(value);
      if (Object.getOwnPropertyNames(value).length !== keys.length) {
        throw new TypeError("non-enumerable property");
      }
      return `{${keys
        .sort()
        .map((key) => {
          const descriptor = Object.getOwnPropertyDescriptor(value, key);
          if (!descriptor?.enumerable || !("value" in descriptor)) {
            throw new TypeError("accessor property");
          }
          return `${JSON.stringify(key)}:${serialize(descriptor.value)}`;
        })
        .join(",")}}`;
    } finally {
      ancestors.delete(value);
    }
  }

  try {
    return serialize(payload);
  } catch {
    throw new TypeError("payload must be JSON-safe");
  }
}

function idempotencyConflict() {
  const error = new Error("idempotency key conflicts with immutable contract");
  error.code = "IDEMPOTENCY_CONFLICT";
  return error;
}

function immutableContractMatches(row, contract) {
  return (
    row.task_id === contract.taskId &&
    row.role === contract.role &&
    row.pool_id === contract.poolId &&
    row.priority === contract.priority &&
    row.contract_hash === contract.contractHash &&
    row.input_fingerprint === contract.inputFingerprint &&
    row.maximum_attempts === contract.maximumAttempts &&
    row.contract_json === contract.contractJson
  );
}

function publicGeneration(row) {
  if (row === undefined) return null;
  return {
    jobId: row.job_id,
    generation: row.generation,
    taskId: row.task_id,
    role: row.role,
    poolId: row.pool_id,
    priority: row.priority,
    state: row.state,
    contractHash: row.contract_hash,
    inputFingerprint: row.input_fingerprint,
    maximumAttempts: row.maximum_attempts,
    acceptedResultHash: row.accepted_result_hash,
    diagnosticEnqueued: Boolean(row.diagnostic_enqueued),
    createdAtMs: row.created_at_ms,
    updatedAtMs: row.updated_at_ms,
  };
}

function requireCostText(value, name, maximumLength) {
  if (
    typeof value !== "string" ||
    value.length < 1 ||
    value.length > maximumLength ||
    !/^[!-~]+$/.test(value)
  ) {
    throw new TypeError(`${name} must be bounded printable ASCII`);
  }
  return value;
}

function requireCostProjectId(value) {
  if (
    typeof value !== "string" ||
    value === "." ||
    value === ".." ||
    !/^[A-Za-z0-9._:-]{1,256}$/.test(value)
  ) {
    throw new TypeError("projectId must be a candidate project identity");
  }
  return value;
}

function requireNanoUsd(value, name) {
  return requireSafeInteger(
    value,
    `${name} must be a finite nonnegative safe integer`,
    0,
  );
}

function safeNanoUsdAdd(left, right) {
  const total = BigInt(left) + BigInt(right);
  if (total > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw stateError("COST_AMOUNT_OVERFLOW", "cost amount exceeds the safe integer bound");
  }
  return Number(total);
}

function captureCostReservationRequest(request) {
  if (request === null || typeof request !== "object") {
    throw new TypeError("cost reservation request must be an object");
  }
  return {
    reservationId: requireCostText(request.reservationId, "reservationId", 256),
    projectId: requireCostProjectId(request.projectId),
    originId: requireSafeInteger(
      request.originId,
      "originId must be a positive safe integer",
      1,
    ),
    jobId: requireCostText(request.jobId, "jobId", 256),
    attemptId: requireCostText(request.attemptId, "attemptId", 256),
    ceilingNanoUsd: requireNanoUsd(request.ceilingNanoUsd, "ceilingNanoUsd"),
    estimatedNanoUsd: requireNanoUsd(
      request.estimatedNanoUsd,
      "estimatedNanoUsd",
    ),
    pricingVersion: requireCostText(
      request.pricingVersion,
      "pricingVersion",
      128,
    ),
    nowMs: requireNanoUsd(request.nowMs, "nowMs"),
  };
}

function captureCostReconciliationRequest(request) {
  if (request === null || typeof request !== "object") {
    throw new TypeError("cost reconciliation request must be an object");
  }
  const outcome = request.outcome;
  if (!["UNKNOWN", "RECONCILED", "RELEASED"].includes(outcome)) {
    throw new TypeError("outcome must be UNKNOWN, RECONCILED, or RELEASED");
  }
  let actualNanoUsd;
  if (outcome === "UNKNOWN") {
    if (request.actualNanoUsd !== null) {
      throw new TypeError("UNKNOWN cost must have a null actualNanoUsd");
    }
    actualNanoUsd = null;
  } else {
    actualNanoUsd = requireNanoUsd(request.actualNanoUsd, "actualNanoUsd");
    if (outcome === "RELEASED" && actualNanoUsd !== 0) {
      throw new TypeError("RELEASED cost must have zero actualNanoUsd");
    }
  }
  return {
    reservationId: requireCostText(request.reservationId, "reservationId", 256),
    projectId: requireCostProjectId(request.projectId),
    originId: requireSafeInteger(
      request.originId,
      "originId must be a positive safe integer",
      1,
    ),
    actualNanoUsd,
    outcome,
    nowMs: requireNanoUsd(request.nowMs, "nowMs"),
  };
}

function publicCostReservation(row) {
  if (row === undefined) return null;
  return Object.freeze({
    reservationId: row.reservation_id,
    projectId: row.project_id,
    originId: row.origin_id,
    jobId: row.job_id,
    attemptId: row.attempt_id,
    state: row.state,
    reservedNanoUsd: row.reserved_nano_usd,
    actualNanoUsd: row.actual_nano_usd,
    pricingVersion: row.pricing_version,
    createdAtMs: row.created_at_ms,
    updatedAtMs: row.updated_at_ms,
  });
}

function immutableCostReservationMatches(row, request) {
  return (
    row.project_id === request.projectId &&
    row.origin_id === request.originId &&
    row.job_id === request.jobId &&
    row.attempt_id === request.attemptId &&
    row.reserved_nano_usd === request.estimatedNanoUsd &&
    row.pricing_version === request.pricingVersion
  );
}

function captureProviderAccountingPolicyRequest(request) {
  const captured = captureCandidateDataObject(
    request,
    [
      "projectId",
      "originId",
      "jobId",
      "ceilingNanoUsd",
      "pricingVersion",
      "maximumProviderCalls",
      "maximumInputTokens",
      "maximumCachedInputTokens",
      "maximumOutputTokensTotal",
      "maximumTotalTokens",
    ],
    undefined,
    "provider accounting policy request",
  );
  const maximumInputTokens = requireSafeInteger(
    captured.maximumInputTokens,
    "maximumInputTokens must be a positive safe integer",
    1,
  );
  const maximumCachedInputTokens = requireSafeInteger(
    captured.maximumCachedInputTokens,
    "maximumCachedInputTokens must be a nonnegative safe integer",
    0,
  );
  if (maximumCachedInputTokens > maximumInputTokens) {
    throw new TypeError("maximumCachedInputTokens must not exceed maximumInputTokens");
  }
  const maximumOutputTokensTotal = requireSafeInteger(
    captured.maximumOutputTokensTotal,
    "maximumOutputTokensTotal must be a positive safe integer",
    1,
  );
  const maximumTotalTokens = requireSafeInteger(
    captured.maximumTotalTokens,
    "maximumTotalTokens must be a positive safe integer",
    1,
  );
  const minimumTotal =
    BigInt(maximumInputTokens) + BigInt(maximumOutputTokensTotal);
  if (
    minimumTotal > BigInt(Number.MAX_SAFE_INTEGER) ||
    maximumTotalTokens < Number(minimumTotal)
  ) {
    throw new TypeError(
      "maximumTotalTokens must cover maximum input plus maximum output tokens",
    );
  }
  const maximumProviderCalls = requireSafeInteger(
    captured.maximumProviderCalls,
    "maximumProviderCalls must be a positive safe integer",
    1,
  );
  if (maximumProviderCalls > 6) {
    throw new TypeError("maximumProviderCalls must not exceed six");
  }
  return Object.freeze({
    projectId: requireCostProjectId(captured.projectId),
    originId: requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    ),
    jobId: requireCostText(captured.jobId, "jobId", 256),
    ceilingNanoUsd: requireNanoUsd(captured.ceilingNanoUsd, "ceilingNanoUsd"),
    pricingVersion: requireCostText(
      captured.pricingVersion,
      "pricingVersion",
      128,
    ),
    maximumProviderCalls,
    maximumInputTokens,
    maximumCachedInputTokens,
    maximumOutputTokensTotal,
    maximumTotalTokens,
  });
}

function captureProviderTransmissionReservationRequest(request) {
  const captured = captureCandidateDataObject(
    request,
    [
      "transmissionId",
      "projectId",
      "originId",
      "jobId",
      "attemptId",
      "transmissionOrdinal",
      "route",
      "provider",
      "model",
      "serviceTier",
      "reasoningEffort",
      "pricingVersion",
      "maximumEstimatedNanoUsd",
      "estimatedNanoUsd",
      "estimatedInputTokens",
      "estimatedOutputTokens",
    ],
    undefined,
    "provider transmission reservation request",
  );
  const route = requireCostText(captured.route, "route", 32);
  if (!/^[A-Z0-9_-]+$/.test(route)) {
    throw new TypeError("route must be uppercase printable ASCII");
  }
  const reasoningEffort = requireCostText(
    captured.reasoningEffort,
    "reasoningEffort",
    32,
  );
  if (!/^[A-Za-z0-9_-]+$/.test(reasoningEffort)) {
    throw new TypeError("reasoningEffort must be an exact policy identity");
  }
  return Object.freeze({
    transmissionId: requireCostText(
      captured.transmissionId,
      "transmissionId",
      256,
    ),
    projectId: requireCostProjectId(captured.projectId),
    originId: requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    ),
    jobId: requireCostText(captured.jobId, "jobId", 256),
    attemptId: requireCostText(captured.attemptId, "attemptId", 256),
    transmissionOrdinal: requireSafeInteger(
      captured.transmissionOrdinal,
      "transmissionOrdinal must be a positive safe integer",
      1,
    ),
    route,
    provider: requireCostText(captured.provider, "provider", 128),
    model: requireCostText(captured.model, "model", 256),
    serviceTier: requireCostText(captured.serviceTier, "serviceTier", 64),
    reasoningEffort,
    pricingVersion: requireCostText(
      captured.pricingVersion,
      "pricingVersion",
      128,
    ),
    maximumEstimatedNanoUsd: requireNanoUsd(
      captured.maximumEstimatedNanoUsd,
      "maximumEstimatedNanoUsd",
    ),
    estimatedNanoUsd: requireNanoUsd(
      captured.estimatedNanoUsd,
      "estimatedNanoUsd",
    ),
    estimatedInputTokens: requireSafeInteger(
      captured.estimatedInputTokens,
      "estimatedInputTokens must be a nonnegative safe integer",
      0,
    ),
    estimatedOutputTokens: requireSafeInteger(
      captured.estimatedOutputTokens,
      "estimatedOutputTokens must be a positive safe integer",
      1,
    ),
  });
}

function captureProviderTransmissionReconciliationRequest(request) {
  const captured = captureCandidateDataObject(
    request,
    [
      "transmissionId",
      "projectId",
      "originId",
      "pricingVersion",
      "outcome",
      "actualNanoUsd",
      "inputTokens",
      "cachedInputTokens",
      "outputTokens",
      "totalTokens",
    ],
    undefined,
    "provider transmission reconciliation request",
  );
  if (!["UNKNOWN", "RECONCILED", "RELEASED"].includes(captured.outcome)) {
    throw new TypeError("outcome must be UNKNOWN, RECONCILED, or RELEASED");
  }
  const common = {
    transmissionId: requireCostText(
      captured.transmissionId,
      "transmissionId",
      256,
    ),
    projectId: requireCostProjectId(captured.projectId),
    originId: requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    ),
    pricingVersion: requireCostText(
      captured.pricingVersion,
      "pricingVersion",
      128,
    ),
    outcome: captured.outcome,
  };
  if (captured.outcome !== "RECONCILED") {
    const expectedActual = captured.outcome === "RELEASED" ? 0 : null;
    if (
      captured.actualNanoUsd !== expectedActual ||
      captured.inputTokens !== null ||
      captured.cachedInputTokens !== null ||
      captured.outputTokens !== null ||
      captured.totalTokens !== null
    ) {
      throw new TypeError(
        `${captured.outcome} transmission must not claim provider token usage`,
      );
    }
    return Object.freeze({
      ...common,
      actualNanoUsd: expectedActual,
      inputTokens: null,
      cachedInputTokens: null,
      outputTokens: null,
      totalTokens: null,
    });
  }
  const inputTokens = requireSafeInteger(
    captured.inputTokens,
    "inputTokens must be a nonnegative safe integer",
    0,
  );
  const cachedInputTokens = requireSafeInteger(
    captured.cachedInputTokens,
    "cachedInputTokens must be a nonnegative safe integer",
    0,
  );
  const outputTokens = requireSafeInteger(
    captured.outputTokens,
    "outputTokens must be a nonnegative safe integer",
    0,
  );
  const totalTokens = requireSafeInteger(
    captured.totalTokens,
    "totalTokens must be a nonnegative safe integer",
    0,
  );
  if (
    cachedInputTokens > inputTokens ||
    BigInt(inputTokens) + BigInt(outputTokens) !== BigInt(totalTokens)
  ) {
    throw new TypeError("provider token usage is internally inconsistent");
  }
  return Object.freeze({
    ...common,
    actualNanoUsd: requireNanoUsd(captured.actualNanoUsd, "actualNanoUsd"),
    inputTokens,
    cachedInputTokens,
    outputTokens,
    totalTokens,
  });
}

function publicProviderTransmission(row) {
  if (row === undefined) return null;
  return Object.freeze({
    transmissionId: row.transmission_id,
    projectId: row.project_id,
    originId: row.origin_id,
    jobId: row.job_id,
    attemptId: row.attempt_id,
    transmissionOrdinal: row.transmission_ordinal,
    route: row.route,
    provider: row.provider,
    model: row.model,
    serviceTier: row.service_tier,
    reasoningEffort: row.reasoning_effort,
    pricingVersion: row.pricing_version,
    state: row.state,
    reservedNanoUsd: row.reserved_nano_usd,
    actualNanoUsd: row.actual_nano_usd,
    estimatedInputTokens: row.estimated_input_tokens,
    estimatedOutputTokens: row.estimated_output_tokens,
    inputTokens: row.input_tokens,
    cachedInputTokens: row.cached_input_tokens,
    outputTokens: row.output_tokens,
    totalTokens: row.total_tokens,
    createdAtMs: row.created_at_ms,
    transmittedAtMs: row.transmitted_at_ms,
    finishedAtMs: row.finished_at_ms,
    updatedAtMs: row.updated_at_ms,
  });
}

function immutableProviderTransmissionMatches(row, request) {
  return (
    row.transmission_id === request.transmissionId &&
    row.project_id === request.projectId &&
    row.origin_id === request.originId &&
    row.job_id === request.jobId &&
    row.attempt_id === request.attemptId &&
    row.transmission_ordinal === request.transmissionOrdinal &&
    row.route === request.route &&
    row.provider === request.provider &&
    row.model === request.model &&
    row.service_tier === request.serviceTier &&
    row.reasoning_effort === request.reasoningEffort &&
    row.pricing_version === request.pricingVersion &&
    row.reserved_nano_usd === request.estimatedNanoUsd &&
    row.estimated_input_tokens === request.estimatedInputTokens &&
    row.estimated_output_tokens === request.estimatedOutputTokens
  );
}

function providerReconciliationMatches(row, request) {
  return (
    row.state === request.outcome &&
    row.actual_nano_usd === request.actualNanoUsd &&
    row.input_tokens === request.inputTokens &&
    row.cached_input_tokens === request.cachedInputTokens &&
    row.output_tokens === request.outputTokens &&
    row.total_tokens === request.totalTokens
  );
}

function providerJobLimitMatches(row, policy) {
  return (
    row.project_id === policy.projectId &&
    row.job_id === policy.jobId &&
    row.maximum_provider_calls === policy.maximumProviderCalls &&
    row.maximum_input_tokens === policy.maximumInputTokens &&
    row.maximum_cached_input_tokens === policy.maximumCachedInputTokens &&
    row.maximum_output_tokens_total === policy.maximumOutputTokensTotal &&
    row.maximum_total_tokens === policy.maximumTotalTokens
  );
}

function publicProviderAccountingSnapshot(budget, limit, counts) {
  if (budget === undefined || limit === undefined) return null;
  return Object.freeze({
    projectId: budget.project_id,
    jobId: limit.job_id,
    ceilingNanoUsd: budget.ceiling_nano_usd,
    spentNanoUsd: budget.spent_nano_usd,
    reservedNanoUsd: budget.reserved_nano_usd,
    pricingVersion: budget.pricing_version,
    maximumProviderCalls: limit.maximum_provider_calls,
    maximumInputTokens: limit.maximum_input_tokens,
    maximumCachedInputTokens: limit.maximum_cached_input_tokens,
    maximumOutputTokensTotal: limit.maximum_output_tokens_total,
    maximumTotalTokens: limit.maximum_total_tokens,
    transmissionCount: counts?.transmission_count ?? 0,
    reconciledCount: counts?.reconciled_count ?? 0,
    unknownCount: counts?.unknown_count ?? 0,
    activeCount: counts?.active_count ?? 0,
    releasedCount: counts?.released_count ?? 0,
    createdAtMs: Math.min(budget.created_at_ms, limit.created_at_ms),
    updatedAtMs: Math.max(budget.updated_at_ms, limit.updated_at_ms),
  });
}

function captureAccountingPolicyTransitionPreviewRequest(request) {
  const captured = captureCandidateDataObject(
    request,
    [
      "projectId",
      "sourcePricingVersion",
      "targetPricingVersion",
      "ceilingNanoUsd",
    ],
    undefined,
    "accounting policy transition preview request",
  );
  return Object.freeze({
    projectId: requireCostProjectId(captured.projectId),
    sourcePricingVersion: requireCostText(
      captured.sourcePricingVersion,
      "sourcePricingVersion",
      128,
    ),
    targetPricingVersion: requireCostText(
      captured.targetPricingVersion,
      "targetPricingVersion",
      128,
    ),
    ceilingNanoUsd: requireNanoUsd(
      captured.ceilingNanoUsd,
      "ceilingNanoUsd",
    ),
  });
}

function captureCandidateAccountingHealthRequest(request) {
  const captured = captureCandidateDataObject(
    request,
    ["projectId", "expectedPricingVersion", "expectedCeilingNanoUsd"],
    undefined,
    "candidate accounting health request",
  );
  return Object.freeze({
    projectId: requireCostProjectId(captured.projectId),
    expectedPricingVersion: requireCostText(
      captured.expectedPricingVersion,
      "expectedPricingVersion",
      128,
    ),
    expectedCeilingNanoUsd: requireNanoUsd(
      captured.expectedCeilingNanoUsd,
      "expectedCeilingNanoUsd",
    ),
  });
}

function requireCandidateSha256(value, name) {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/.test(value)) {
    throw new TypeError(`${name} must be lowercase SHA-256`);
  }
  return value;
}

function captureAccountingPolicyTransitionRequest(request) {
  const captured = captureCandidateDataObject(
    request,
    [
      "projectId",
      "sourcePricingVersion",
      "targetPricingVersion",
      "ceilingNanoUsd",
      "transitionFingerprint",
      "operatorAuthorized",
    ],
    undefined,
    "accounting policy transition request",
  );
  if (captured.operatorAuthorized !== true) {
    throw new TypeError("accounting policy transition requires operator authorization");
  }
  return Object.freeze({
    ...captureAccountingPolicyTransitionPreviewRequest({
      projectId: captured.projectId,
      sourcePricingVersion: captured.sourcePricingVersion,
      targetPricingVersion: captured.targetPricingVersion,
      ceilingNanoUsd: captured.ceilingNanoUsd,
    }),
    transitionFingerprint: requireCandidateSha256(
      captured.transitionFingerprint,
      "transitionFingerprint",
    ),
  });
}

function publicAccountingPolicyTransition(row) {
  if (row === undefined) return null;
  return Object.freeze({
    transitionId: row.transition_id,
    projectId: row.project_id,
    sourcePricingVersion: row.source_pricing_version,
    targetPricingVersion: row.target_pricing_version,
    transitionFingerprint: row.transition_fingerprint,
    ceilingBeforeNanoUsd: row.ceiling_before_nano_usd,
    ceilingAfterNanoUsd: row.ceiling_after_nano_usd,
    spentBeforeNanoUsd: row.spent_before_nano_usd,
    spentAfterNanoUsd: row.spent_after_nano_usd,
    reservedBeforeNanoUsd: row.reserved_before_nano_usd,
    reservedAfterNanoUsd: row.reserved_after_nano_usd,
    reconciledTransmissions: row.reconciled_transmissions,
    releasedTransmissions: row.released_transmissions,
    activeTransmissions: row.active_transmissions,
    unknownTransmissions: row.unknown_transmissions,
    activeWorkers: row.active_workers,
    activeHeads: row.active_heads,
    preconditionHash: row.precondition_hash,
    createdAtMs: row.created_at_ms,
  });
}

function captureCandidateOriginRequest(request) {
  if (
    request === null ||
    typeof request !== "object" ||
    Array.isArray(request) ||
    Object.getPrototypeOf(request) !== Object.prototype
  ) {
    throw new TypeError("candidate origin request must be a plain object");
  }
  const keys = ["projectId", "originThreadHash", "originCapabilityHash"];
  const ownKeys = Reflect.ownKeys(request);
  if (
    ownKeys.length !== keys.length ||
    ownKeys.some((key) => typeof key !== "string" || !keys.includes(key))
  ) {
    throw new TypeError("invalid candidate origin request");
  }
  const captured = {};
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(request, key);
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError("invalid candidate origin request");
    }
    captured[key] = descriptor.value;
  }
  captured.projectId = requireCostProjectId(captured.projectId);
  for (const key of ["originThreadHash", "originCapabilityHash"]) {
    if (
      typeof captured[key] !== "string" ||
      !/^[0-9a-f]{64}$/.test(captured[key])
    ) {
      throw new TypeError("candidate origin hashes must be lowercase SHA-256 values");
    }
  }
  return captured;
}

function captureCandidateDataObject(
  value,
  allowedKeys,
  requiredKeys = allowedKeys,
  label = "candidate request",
) {
  try {
    if (
      value === null ||
      typeof value !== "object" ||
      Array.isArray(value) ||
      Object.getPrototypeOf(value) !== Object.prototype
    ) {
      throw new TypeError();
    }
    const descriptors = Object.getOwnPropertyDescriptors(value);
    const keys = Reflect.ownKeys(descriptors);
    if (
      keys.some(
        (key) =>
          typeof key !== "string" ||
          !allowedKeys.includes(key),
      ) ||
      requiredKeys.some((key) => !Object.hasOwn(descriptors, key))
    ) {
      throw new TypeError();
    }
    const captured = {};
    for (const key of keys) {
      const descriptor = descriptors[key];
      if (
        descriptor.enumerable !== true ||
        !Object.hasOwn(descriptor, "value")
      ) {
        throw new TypeError();
      }
      captured[key] = descriptor.value;
    }
    return captured;
  } catch {
    throw new TypeError(`invalid ${label}`);
  }
}

function captureCandidateContract(contract) {
  const required = [
    "projectId",
    "taskId",
    "idempotencyKey",
    "contractHash",
    "inputFingerprint",
    "role",
    "poolId",
  ];
  const captured = captureCandidateDataObject(
    contract,
    [...required, "priority", "maximumAttempts", "payload"],
    required,
    "candidate contract",
  );
  requireContractIdentity(captured);
  return captured;
}

function captureCandidateDenseArray(value, label, maximumLength = 64) {
  try {
    if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
      throw new TypeError();
    }
    const descriptors = Object.getOwnPropertyDescriptors(value);
    const lengthDescriptor = descriptors.length;
    if (
      lengthDescriptor === undefined ||
      !Object.hasOwn(lengthDescriptor, "value") ||
      !Number.isSafeInteger(lengthDescriptor.value) ||
      lengthDescriptor.value < 1 ||
      lengthDescriptor.value > maximumLength
    ) {
      throw new TypeError();
    }
    const length = lengthDescriptor.value;
    const keys = Reflect.ownKeys(descriptors);
    if (
      keys.length !== length + 1 ||
      keys.some(
        (key) =>
          key !== "length" &&
          (typeof key !== "string" || !/^(0|[1-9]\d*)$/.test(key)),
      )
    ) {
      throw new TypeError();
    }
    const captured = [];
    for (let index = 0; index < length; index += 1) {
      const descriptor = descriptors[String(index)];
      if (
        descriptor === undefined ||
        descriptor.enumerable !== true ||
        !Object.hasOwn(descriptor, "value")
      ) {
        throw new TypeError();
      }
      captured.push(descriptor.value);
    }
    return captured;
  } catch {
    throw new TypeError(`invalid ${label}`);
  }
}

function candidatePathContains(root, target) {
  const relative = path.relative(root, target);
  return (
    relative === "" ||
    (relative !== ".." &&
      !relative.startsWith(`..${path.sep}`) &&
      !path.isAbsolute(relative))
  );
}

function candidatePathsOverlap(left, right) {
  return candidatePathContains(left, right) || candidatePathContains(right, left);
}

function candidateFilesystemIdentity(canonicalPath) {
  const stats = statSync(canonicalPath, { bigint: true });
  if (stats.isFile() && stats.nlink !== 1n) {
    throw new TypeError("hard-linked writer outputs are not admitted");
  }
  return `${stats.dev.toString(16)}:${stats.ino.toString(16)}`;
}

function canonicalizeCandidateWriterScope(worktreeRoot, outputPaths) {
  try {
    if (
      typeof worktreeRoot !== "string" ||
      !path.isAbsolute(worktreeRoot) ||
      worktreeRoot.includes("\0")
    ) {
      throw new TypeError();
    }
    const canonicalWorktree = realpathSync.native(worktreeRoot);
    if (!statSync(canonicalWorktree).isDirectory()) throw new TypeError();
    const worktreeIdentity = candidateFilesystemIdentity(canonicalWorktree);
    const outputs = captureCandidateDenseArray(
      outputPaths,
      "candidate writer output paths",
    ).map((outputPath) => {
      if (
        typeof outputPath !== "string" ||
        !path.isAbsolute(outputPath) ||
        outputPath.includes("\0")
      ) {
        throw new TypeError();
      }
      const canonical = realpathSync.native(outputPath);
      statSync(canonical);
      if (!candidatePathContains(canonicalWorktree, canonical)) {
        throw new TypeError();
      }
      return Object.freeze({
        path: canonical,
        filesystemIdentity: candidateFilesystemIdentity(canonical),
      });
    });
    const pathIdentities = outputs.map((output) =>
      filesystemPathIdentity(output.path),
    );
    if (new Set(pathIdentities).size !== pathIdentities.length) {
      throw new TypeError();
    }
    const filesystemIdentities = outputs.map(
      (output) => output.filesystemIdentity,
    );
    if (new Set(filesystemIdentities).size !== filesystemIdentities.length) {
      throw new TypeError();
    }
    for (let left = 0; left < outputs.length; left += 1) {
      for (let right = left + 1; right < outputs.length; right += 1) {
        if (candidatePathsOverlap(outputs[left].path, outputs[right].path)) {
          throw new TypeError();
        }
      }
    }
    outputs.sort((left, right) =>
      filesystemPathIdentity(left.path).localeCompare(
        filesystemPathIdentity(right.path),
      ),
    );
    return Object.freeze({
      canonicalWorktree,
      worktreeIdentity,
      canonicalOutputs: Object.freeze(outputs),
      canonicalOutputPaths: Object.freeze(outputs.map((output) => output.path)),
    });
  } catch {
    throw stateError("INVALID_WRITER_SCOPE", "invalid writer scope");
  }
}

function publicCandidateWriterAdmission(row, outputPaths) {
  return Object.freeze({
    projectId: row.project_id,
    originId: row.origin_id,
    jobId: row.owner_job_id,
    generation: row.owner_generation,
    leaseEpoch: row.owner_lease_epoch,
    fencingToken: row.fencing_token,
    canonicalWorktree: row.canonical_worktree,
    canonicalOutputPaths: Object.freeze([...outputPaths]),
    acquiredAtMs: row.acquired_at_ms,
    expiresAtMs: row.expires_at_ms,
  });
}

const MAX_CANDIDATE_WRITER_REBIND_BYTES = 1024 * 1024;

function captureCandidateWriterRebindOutputs(value) {
  const outputs = captureCandidateDenseArray(
    value,
    "candidate writer rebind outputs",
  ).map((entry) => {
    const captured = captureCandidateDataObject(
      entry,
      ["path", "sha256", "byteLength"],
      ["path", "sha256", "byteLength"],
      "candidate writer rebind output",
    );
    if (
      typeof captured.path !== "string" ||
      !path.isAbsolute(captured.path) ||
      captured.path.includes("\0") ||
      typeof captured.sha256 !== "string" ||
      !/^[a-f0-9]{64}$/.test(captured.sha256) ||
      !Number.isSafeInteger(captured.byteLength) ||
      captured.byteLength < 0 ||
      captured.byteLength > MAX_CANDIDATE_WRITER_REBIND_BYTES
    ) {
      throw stateError(
        "WRITER_OUTPUT_ATTESTATION_MISMATCH",
        "writer output attestation is invalid",
      );
    }
    return Object.freeze({
      path: captured.path,
      sha256: captured.sha256,
      byteLength: captured.byteLength,
    });
  });
  const totalBytes = outputs.reduce((total, output) => total + output.byteLength, 0);
  if (
    !Number.isSafeInteger(totalBytes) ||
    totalBytes > MAX_CANDIDATE_WRITER_REBIND_BYTES
  ) {
    throw stateError(
      "WRITER_OUTPUT_ATTESTATION_MISMATCH",
      "writer output attestation exceeds its byte limit",
    );
  }
  return outputs;
}

function publicCandidateOrigin(row) {
  return Object.freeze({
    originId: row.origin_id,
    projectId: row.project_id,
    originThreadHash: row.origin_thread_hash,
    originCapabilityHash: row.origin_capability_hash,
  });
}

const CANDIDATE_PUBLIC_TERMINAL_STATUSES = Object.freeze([
  "PASS",
  "CACHED",
  "FAIL",
  "BLOCKED",
]);
const CANDIDATE_PUBLIC_EXECUTION_STATUSES = Object.freeze([
  "ACCEPTED",
  "INCOMPLETE",
  "BLOCKED",
  "PROVIDER_ERROR",
  "CONTRACT_ERROR",
  "CANCELLED",
]);
const CANDIDATE_PUBLIC_EVIDENCE_VERDICTS = Object.freeze([
  "POSITIVE",
  "NEGATIVE",
  "NULL",
  "MIXED",
  "UNRESOLVED",
  "NOT_APPLICABLE",
]);
function candidateDeepFreeze(value, seen = new Set()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (descriptor && Object.hasOwn(descriptor, "value")) {
      candidateDeepFreeze(descriptor.value, seen);
    }
  }
  return Object.freeze(value);
}

function requireCandidatePublicText(value, label, maximumBytes) {
  if (
    typeof value !== "string" ||
    value.trim() === "" ||
    Buffer.byteLength(value, "utf8") > maximumBytes ||
    containsUnsafePublicText(value)
  ) {
    throw stateError(
      "INVALID_PUBLIC_RESULT_PACKET",
      `invalid ${label}`,
    );
  }
  return value;
}

function captureCandidatePublicTextArray(value, label) {
  try {
    if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
      throw new TypeError();
    }
    const descriptors = Object.getOwnPropertyDescriptors(value);
    const length = descriptors.length?.value;
    if (
      !Number.isSafeInteger(length) ||
      length < 0 ||
      length > 32 ||
      Reflect.ownKeys(descriptors).length !== length + 1
    ) {
      throw new TypeError();
    }
    const captured = [];
    for (let index = 0; index < length; index += 1) {
      const descriptor = descriptors[String(index)];
      if (
        descriptor === undefined ||
        descriptor.enumerable !== true ||
        !Object.hasOwn(descriptor, "value")
      ) {
        throw new TypeError();
      }
      captured.push(
        requireCandidatePublicText(
          descriptor.value,
          `${label} entry`,
          2048,
        ),
      );
    }
    return captured;
  } catch (error) {
    if (error?.code === "INVALID_PUBLIC_RESULT_PACKET") throw error;
    throw stateError("INVALID_PUBLIC_RESULT_PACKET", `invalid ${label}`);
  }
}

function captureCandidatePublicResultPacket(value) {
  const captured = captureCandidateDataObject(
    value,
    [
      "schema_version",
      "result_protocol",
      "status",
      "execution_status",
      "evidence_verdict",
      "cache_hit",
      "summary",
      "positive_findings",
      "negative_findings",
      "residual_risks",
      "recommended_next_action",
      "scientific_uncertainty",
      "architecture_uncertainty",
      "scope_deviation",
    ],
    undefined,
    "candidate public result packet",
  );
  const status = captured.status;
  const executionStatus = captured.execution_status;
  const evidenceVerdict = captured.evidence_verdict;
  const cacheHit = captured.cache_hit;
  const unresolved = evidenceVerdict === "UNRESOLVED";
  const coherent =
    (status === "CACHED" &&
      executionStatus === "ACCEPTED" &&
      !unresolved &&
      cacheHit === true) ||
    (status === "PASS" &&
      executionStatus === "ACCEPTED" &&
      !unresolved &&
      cacheHit === false) ||
    (status === "FAIL" &&
      ["INCOMPLETE", "PROVIDER_ERROR", "CONTRACT_ERROR"].includes(
        executionStatus,
      ) &&
      unresolved &&
      cacheHit === false) ||
    (status === "BLOCKED" &&
      ["BLOCKED", "CANCELLED"].includes(executionStatus) &&
      unresolved &&
      cacheHit === false);
  if (
    captured.schema_version !== 1 ||
    captured.result_protocol !== 3 ||
    !CANDIDATE_PUBLIC_TERMINAL_STATUSES.includes(status) ||
    !CANDIDATE_PUBLIC_EXECUTION_STATUSES.includes(executionStatus) ||
    !CANDIDATE_PUBLIC_EVIDENCE_VERDICTS.includes(evidenceVerdict) ||
    typeof cacheHit !== "boolean" ||
    !coherent
  ) {
    throw stateError(
      "INVALID_PUBLIC_RESULT_PACKET",
      "invalid public result identity",
    );
  }
  for (const key of [
    "scientific_uncertainty",
    "architecture_uncertainty",
    "scope_deviation",
  ]) {
    if (typeof captured[key] !== "boolean") {
      throw stateError(
        "INVALID_PUBLIC_RESULT_PACKET",
        "invalid public result uncertainty",
      );
    }
  }
  const packet = {
    schema_version: 1,
    result_protocol: 3,
    status,
    execution_status: executionStatus,
    evidence_verdict: evidenceVerdict,
    cache_hit: cacheHit,
    summary: requireCandidatePublicText(captured.summary, "public summary", 4096),
    positive_findings: captureCandidatePublicTextArray(
      captured.positive_findings,
      "positive findings",
    ),
    negative_findings: captureCandidatePublicTextArray(
      captured.negative_findings,
      "negative findings",
    ),
    residual_risks: captureCandidatePublicTextArray(
      captured.residual_risks,
      "residual risks",
    ),
    recommended_next_action: requireCandidatePublicText(
      captured.recommended_next_action,
      "recommended next action",
      4096,
    ),
    scientific_uncertainty: captured.scientific_uncertainty,
    architecture_uncertainty: captured.architecture_uncertainty,
    scope_deviation: captured.scope_deviation,
  };
  const canonicalJson = canonicalPayloadJson(packet);
  const byteCount = Buffer.byteLength(canonicalJson, "utf8");
  if (byteCount < 2 || byteCount > 49152) {
    throw stateError(
      "INVALID_PUBLIC_RESULT_PACKET",
      "public result packet exceeds its byte limit",
    );
  }
  return Object.freeze({
    packet: candidateDeepFreeze(JSON.parse(canonicalJson)),
    canonicalJson,
    byteCount,
    packetHash: candidateSha256(canonicalJson),
  });
}

function candidateWorkerPublicId(projectId, originId, bindingId) {
  return `DS-${candidateSha256(
    [
      "candidate-worker-public-id-v1",
      projectId,
      String(originId),
      String(bindingId),
    ].join("\0"),
  ).slice(0, 32)}`;
}

const CANDIDATE_SOL_PLAN_DECISIONS = Object.freeze([
  "DELEGATE_DEEPLUNA",
  "HANDLE_CURRENT",
  "START_SOL_HEAD",
]);
const CANDIDATE_SOL_EFFORTS = Object.freeze([
  "medium",
  "high",
  "xhigh",
  "max",
]);
const CANDIDATE_SOL_REASON_CODES = Object.freeze([
  "active-effort-matches",
  "authority-domain",
  "delegation-overhead-dominates",
  "deterministic-deepluna-eligible",
  "max-one-shot-eligible",
  "reasoning-score",
]);

function requireCandidateLowerHex64(value, label) {
  if (typeof value !== "string" || !/^[a-f0-9]{64}$/.test(value)) {
    throw stateError("INVALID_SOL_PLAN", `invalid ${label}`);
  }
  return value;
}

function captureCandidateSolPlan(value) {
  const captured = captureCandidateDataObject(
    value,
    [
      "schema_version",
      "plan_id",
      "decision",
      "selected_effort",
      "reasons",
      "max_eligible",
      "attempt_fingerprint",
      "input_fingerprint",
      "cache_eligible",
      "policy_hash",
      "evidence_hash",
      "governance_hash",
      "plan_payload",
    ],
    undefined,
    "candidate Sol plan",
  );
  const reasons = captureCandidateDenseArray(
    captured.reasons,
    "candidate Sol plan reasons",
    32,
  );
  const uniqueReasons = new Set(reasons);
  const decision = captured.decision;
  const selectedEffort = captured.selected_effort;
  const maxEligible = captured.max_eligible;
  if (
    captured.schema_version !== 1 ||
    typeof captured.plan_id !== "string" ||
    !/^SRP-[a-f0-9]{32}$/.test(captured.plan_id) ||
    !CANDIDATE_SOL_PLAN_DECISIONS.includes(decision) ||
    (selectedEffort !== null && !CANDIDATE_SOL_EFFORTS.includes(selectedEffort)) ||
    typeof maxEligible !== "boolean" ||
    typeof captured.cache_eligible !== "boolean" ||
    uniqueReasons.size !== reasons.length ||
    reasons.some((reason) => !CANDIDATE_SOL_REASON_CODES.includes(reason)) ||
    (decision === "DELEGATE_DEEPLUNA" &&
      (selectedEffort !== null || maxEligible !== false)) ||
    (decision !== "DELEGATE_DEEPLUNA" &&
      (selectedEffort === null ||
        (selectedEffort === "max") !== maxEligible))
  ) {
    throw stateError("INVALID_SOL_PLAN", "invalid candidate Sol plan identity");
  }
  const reasonSet = new Set(reasons);
  const coherentReasons =
    reasonSet.has("max-one-shot-eligible") === maxEligible &&
    (!maxEligible || reasonSet.has("authority-domain")) &&
    (!reasonSet.has("authority-domain") ||
      selectedEffort === "xhigh" ||
      selectedEffort === "max") &&
    ((decision === "DELEGATE_DEEPLUNA" &&
      reasons.length === 1 &&
      reasonSet.has("deterministic-deepluna-eligible")) ||
      (decision === "HANDLE_CURRENT" &&
        reasonSet.has("reasoning-score") &&
        reasonSet.has("active-effort-matches") !==
          reasonSet.has("delegation-overhead-dominates") &&
        (selectedEffort !== "max" ||
          reasonSet.has("active-effort-matches")) &&
        !reasonSet.has("deterministic-deepluna-eligible")) ||
      (decision === "START_SOL_HEAD" &&
        reasonSet.has("reasoning-score") &&
        !reasonSet.has("active-effort-matches") &&
        !reasonSet.has("delegation-overhead-dominates") &&
        !reasonSet.has("deterministic-deepluna-eligible")));
  if (!coherentReasons) {
    throw stateError("INVALID_SOL_PLAN", "incomplete candidate Sol plan reasons");
  }
  const planJson = canonicalPayloadJson(captured.plan_payload);
  const planBytes = Buffer.byteLength(planJson, "utf8");
  if (planBytes < 2 || planBytes > 57344) {
    throw stateError("INVALID_SOL_PLAN", "candidate Sol plan exceeds its byte limit");
  }
  return Object.freeze({
    schemaVersion: 1,
    planId: captured.plan_id,
    decision,
    selectedEffort,
    reasons: Object.freeze([...reasons]),
    maxEligible,
    attemptFingerprint: requireCandidateLowerHex64(
      captured.attempt_fingerprint,
      "attempt fingerprint",
    ),
    inputFingerprint: requireCandidateLowerHex64(
      captured.input_fingerprint,
      "input fingerprint",
    ),
    cacheEligible: captured.cache_eligible,
    policyHash: requireCandidateLowerHex64(captured.policy_hash, "policy hash"),
    evidenceHash: requireCandidateLowerHex64(
      captured.evidence_hash,
      "evidence hash",
    ),
    governanceHash: requireCandidateLowerHex64(
      captured.governance_hash,
      "governance hash",
    ),
    planJson,
    planBytes,
  });
}

function candidateHeadPublicId(projectId, originId, planId, headRunId) {
  return `SH-${candidateSha256(
    [
      "candidate-head-public-id-v1",
      projectId,
      String(originId),
      planId,
      String(headRunId),
    ].join("\0"),
  ).slice(0, 32)}`;
}

export function deterministicCandidateHeadProducerId({
  projectId,
  attemptFingerprint,
  bindingEpoch,
} = {}) {
  const exactProjectId = requireCostProjectId(projectId);
  const exactAttemptFingerprint = requireCandidateLowerHex64(
    attemptFingerprint,
    "attempt fingerprint",
  );
  const exactBindingEpoch = requireSafeInteger(
    bindingEpoch,
    "bindingEpoch must be a positive safe integer",
    1,
  );
  return `SH-${candidateSha256(
    [
      "candidate-head-producer-id-v1",
      exactProjectId,
      exactAttemptFingerprint,
      String(exactBindingEpoch),
    ].join("\0"),
  ).slice(0, 32)}`;
}

function requireCandidateHeadProducerId(value) {
  const producerJobId = requireCostText(value, "producerJobId", 35);
  if (!/^SH-[a-f0-9]{32}$/.test(producerJobId)) {
    throw new TypeError("producerJobId must be a deterministic candidate head id");
  }
  return producerJobId;
}

function requireCandidateProcessBootId(value) {
  const processBootId = requireCostText(value, "processBootId", 35);
  if (!/^DI-[a-f0-9]{32}$/.test(processBootId)) {
    throw new TypeError("processBootId must be a candidate daemon boot id");
  }
  return processBootId;
}

function candidateHeadProducerSnapshot(row) {
  if (row === undefined) {
    throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
  }
  const expectedProducerJobId = deterministicCandidateHeadProducerId({
    projectId: row.project_id,
    attemptFingerprint: row.attempt_fingerprint,
    bindingEpoch: row.binding_epoch,
  });
  if (row.producer_job_id !== expectedProducerJobId) {
    throw stateError(
      "HEAD_PRODUCER_IDENTITY_CONFLICT",
      "candidate head producer identity is incoherent",
    );
  }
  return Object.freeze({
    headRunId: row.head_run_id,
    projectId: row.project_id,
    producerJobId: row.producer_job_id,
    attemptFingerprint: row.attempt_fingerprint,
    bindingEpoch: row.binding_epoch,
    planId: row.plan_id,
    selectedEffort: row.selected_effort,
    producerState: row.producer_state,
    runState: row.run_state,
    externalStartPossible: Boolean(row.external_start_possible),
    processBootId: row.process_boot_id,
    ownerPid: row.owner_pid,
    terminalResultHash: row.terminal_result_hash,
    claimedAtMs: row.claimed_at_ms,
    startedAtMs: row.started_at_ms,
    finishedAtMs: row.finished_at_ms,
    createdAtMs: row.created_at_ms,
    updatedAtMs: row.updated_at_ms,
  });
}

function candidateUnknownHeadPacket(reasonCode) {
  return Object.freeze({
    schema_version: 1,
    result_protocol: 3,
    status: "BLOCKED",
    execution_status: "BLOCKED",
    evidence_verdict: "UNRESOLVED",
    cache_hit: false,
    summary:
      "The Sol head may have crossed the external start boundary before ownership was lost.",
    positive_findings: [],
    negative_findings: [
      `The durable producer entered fail-closed recovery state ${reasonCode}.`,
    ],
    residual_risks: [
      "Provider execution may have started, so the attempt cannot be retried automatically.",
    ],
    recommended_next_action:
      "Reconcile the provider attempt and submit a new plan only with explicit authority.",
    scientific_uncertainty: false,
    architecture_uncertainty: true,
    scope_deviation: false,
  });
}

function candidatePublicStateFromGeneration(state) {
  switch (state) {
    case "QUEUED":
      return Object.freeze({
        status: "QUEUED",
        executionStatus: "INCOMPLETE",
        evidenceVerdict: "UNRESOLVED",
        cacheHit: false,
      });
    case "RUNNING":
    case "VALIDATING":
      return Object.freeze({
        status: "RUNNING",
        executionStatus: "INCOMPLETE",
        evidenceVerdict: "UNRESOLVED",
        cacheHit: false,
      });
    case "CANCELED":
      return Object.freeze({
        status: "BLOCKED",
        executionStatus: "CANCELLED",
        evidenceVerdict: "UNRESOLVED",
        cacheHit: false,
      });
    case "FAILED":
      return Object.freeze({
        status: "FAIL",
        executionStatus: "INCOMPLETE",
        evidenceVerdict: "UNRESOLVED",
        cacheHit: false,
      });
    case "QUARANTINED":
      return Object.freeze({
        status: "FAIL",
        executionStatus: "CONTRACT_ERROR",
        evidenceVerdict: "UNRESOLVED",
        cacheHit: false,
      });
    default:
      throw stateError(
        "RESULT_PACKET_MISSING",
        "terminal generation has no accepted public result",
      );
  }
}

const CANDIDATE_MIGRATION_SOURCE_KINDS = new Set([
  "CANONICAL",
  "UNDERSCORE_VARIANT",
  "WORKSPACE_DERIVED",
  "THREAD_SCOPED",
]);
const MAX_CANDIDATE_MIGRATION_SOURCES = 64;
const MAX_CANDIDATE_MIGRATION_ENTRIES = 10_000;
const MAX_CANDIDATE_MIGRATION_FILE_BYTES = 1024 * 1024;
const CANDIDATE_MIGRATION_OPERATIONAL_TABLES = Object.freeze([
  "logical_jobs",
  "generations",
  "attempts",
  "leases",
  "events",
  "protocol_responses",
  "origins",
  "logical_job_origins",
  "writer_fence_counters",
  "writer_locks",
  "writer_lock_outputs",
  "cost_budgets",
  "cost_reservations",
  "public_resources",
  "protocol_requests",
  "protocol_request_normalization_claims",
  "protocol_request_resources",
  "worker_bindings",
  "worker_claims",
  "head_runs",
  "result_packets",
  "result_subjects",
  "result_normalization_claims",
  "sol_plans",
  "sol_plan_reasons",
  "head_claims",
  "max_attempt_claims",
  "batch_runs",
  "batch_claims",
  "batch_nodes",
  "batch_edges",
  "batch_dependency_states",
  "batch_node_accepted_verdicts",
  "batch_claim_nodes",
]);

function candidateSha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function candidateUtf8Compare(left, right) {
  return Buffer.compare(Buffer.from(left, "utf8"), Buffer.from(right, "utf8"));
}

function candidateMigrationWorkspaceIdentity(canonicalWorkspace) {
  const durablePath =
    process.platform === "win32"
      ? canonicalWorkspace.replaceAll("\\", "/").toLowerCase()
      : canonicalWorkspace;
  return candidateSha256(`deepluna-workspace-v1\0${durablePath}`);
}

function candidateMigrationOwnValue(value, key) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }
  const descriptor = Object.getOwnPropertyDescriptor(value, key);
  return descriptor !== undefined && Object.hasOwn(descriptor, "value")
    ? descriptor.value
    : undefined;
}

function candidateMigrationTerminalState(value) {
  if (typeof value !== "string") return "UNKNOWN";
  const normalized = value.trim().toUpperCase();
  if (["PASS", "CACHED", "FAIL", "BLOCKED", "INCOMPLETE"].includes(normalized)) {
    return normalized;
  }
  return "UNKNOWN";
}

function candidateMigrationProtocolVersion(value) {
  return Number.isSafeInteger(value) && value >= 1 ? value : null;
}

function candidateMigrationFinishedAtMs(value) {
  if (Number.isSafeInteger(value) && value >= 0) return value;
  if (typeof value !== "string" || value.trim() === "") return null;
  const parsed = Date.parse(value);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : null;
}

function listCandidateMigrationDirectory(copiedRoot, relativePath) {
  const segments = relativePath.split("/");
  let directory = copiedRoot;
  for (const segment of segments) {
    directory = path.join(directory, segment);
    if (!existsSync(directory)) return [];
    const stats = lstatSync(directory);
    if (!stats.isDirectory() || stats.isSymbolicLink()) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "copied migration source contains a path alias",
      );
    }
  }
  const canonicalDirectory = realpathSync.native(directory);
  if (!candidatePathContains(copiedRoot, canonicalDirectory)) {
    throw candidateMigrationError(
      "MIGRATION_COPY_ROOT_ESCAPE",
      "copied migration source contains a path alias",
    );
  }
  if (!existsSync(directory)) return [];
  return readdirSync(canonicalDirectory, { withFileTypes: true }).sort((left, right) =>
    candidateUtf8Compare(left.name, right.name),
  );
}

function candidateMigrationRecognizedFiles(copiedRoot) {
  const files = [];
  const addFile = (relativePath, entryKind, logicalIdentity) => {
    const absolutePath = path.join(copiedRoot, ...relativePath.split("/"));
    if (!existsSync(absolutePath)) return;
    files.push({ absolutePath, entryKind, logicalIdentity, relativePath });
  };
  addFile("worker-state-v5.json", "STATE", "worker-state-v5");
  for (const directory of listCandidateMigrationDirectory(copiedRoot, "jobs")) {
    if (directory.isSymbolicLink()) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "copied migration source contains a path alias",
      );
    }
    if (!directory.isDirectory()) continue;
    addFile(`jobs/${directory.name}/job.json`, "JOB", directory.name);
  }
  for (const directory of listCandidateMigrationDirectory(
    copiedRoot,
    "heads/jobs",
  )) {
    if (directory.isSymbolicLink()) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "copied migration source contains a path alias",
      );
    }
    if (!directory.isDirectory()) continue;
    addFile(`heads/jobs/${directory.name}/job.json`, "JOB", directory.name);
  }
  for (const file of listCandidateMigrationDirectory(
    copiedRoot,
    "cache/results",
  )) {
    if (file.isSymbolicLink()) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "copied migration source contains a path alias",
      );
    }
    if (!file.isFile() || !file.name.endsWith(".json")) continue;
    addFile(
      `cache/results/${file.name}`,
      "CACHE",
      file.name.slice(0, -".json".length),
    );
  }
  for (const directory of listCandidateMigrationDirectory(
    copiedRoot,
    "batches",
  )) {
    if (directory.isSymbolicLink()) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "copied migration source contains a path alias",
      );
    }
    if (!directory.isDirectory()) continue;
    addFile(`batches/${directory.name}/batch.json`, "BATCH", directory.name);
  }
  listCandidateMigrationDirectory(copiedRoot, "negative-admission-v1");
  addFile(
    "negative-admission-v1/admission.sqlite",
    "NEGATIVE_ADMISSION",
    "negative-admission-v1",
  );
  if (files.length > MAX_CANDIDATE_MIGRATION_ENTRIES) {
    throw candidateMigrationError(
      "MIGRATION_SOURCE_TOO_LARGE",
      "copied migration source has too many audit entries",
    );
  }
  return files;
}

function readCandidateMigrationFile({
  canonicalSourceRoot,
  absolutePath,
  entryKind,
  logicalIdentity,
  relativePath,
  candidateProtocolVersion,
  staleBeforeMs,
}) {
  const pathStats = lstatSync(absolutePath);
  if (
    !pathStats.isFile() ||
    pathStats.isSymbolicLink() ||
    pathStats.nlink !== 1 ||
    pathStats.size > MAX_CANDIDATE_MIGRATION_FILE_BYTES
  ) {
    throw candidateMigrationError(
      "MIGRATION_INVALID_COPIED_FILE",
      "copied migration file is not an isolated bounded regular file",
    );
  }
  const canonicalFile = realpathSync.native(absolutePath);
  if (!candidatePathContains(canonicalSourceRoot, canonicalFile)) {
    throw candidateMigrationError(
      "MIGRATION_COPY_ROOT_ESCAPE",
      "copied migration file escapes its source root",
    );
  }
  const before = statSync(canonicalFile, { bigint: true });
  const bytes = readFileSync(canonicalFile);
  const after = statSync(canonicalFile, { bigint: true });
  if (
    before.dev !== after.dev ||
    before.ino !== after.ino ||
    before.size !== after.size ||
    before.mtimeNs !== after.mtimeNs ||
    BigInt(bytes.byteLength) !== after.size
  ) {
    throw candidateMigrationError(
      "MIGRATION_SOURCE_CHANGED",
      "copied migration source changed during audit",
    );
  }

  const entry = {
    absolutePath: canonicalFile,
    byteCount: bytes.byteLength,
    contentHash: candidateSha256(bytes),
    disposition: "AUDIT_ONLY",
    entryKind,
    logicalIdentityHash: candidateSha256(`${entryKind}\0${logicalIdentity}`),
    protocolVersion: null,
    reasonCode: "STATE_METADATA_ONLY",
    relativePathHash: candidateSha256(relativePath),
    terminalState: "NOT_APPLICABLE",
  };
  if (entryKind === "NEGATIVE_ADMISSION") {
    entry.reasonCode = "NEGATIVE_ADMISSION_ONLY";
    return entry;
  }
  if (entryKind === "STATE" || entryKind === "BATCH") return entry;

  let parsed;
  try {
    parsed = JSON.parse(bytes.toString("utf8"));
  } catch {
    entry.disposition = "QUARANTINED";
    entry.reasonCode = "MALFORMED";
    entry.terminalState = "UNKNOWN";
    return entry;
  }
  const embeddedIdentity = candidateMigrationOwnValue(
    parsed,
    entryKind === "JOB" ? "job_id" : "cache_key",
  );
  const embeddedIdentityValid =
    typeof embeddedIdentity === "string" &&
    embeddedIdentity.length >= 1 &&
    embeddedIdentity.length <= 512 &&
    !embeddedIdentity.includes("\0");
  if (embeddedIdentityValid) {
    entry.logicalIdentityHash = candidateSha256(
      `${entryKind}\0${embeddedIdentity}`,
    );
  }
  const identityMatches =
    embeddedIdentityValid && embeddedIdentity === logicalIdentity;
  const protocolValue =
    candidateMigrationOwnValue(parsed, "result_protocol") ??
    candidateMigrationOwnValue(parsed, "schema_version");
  entry.protocolVersion = candidateMigrationProtocolVersion(protocolValue);
  entry.terminalState = candidateMigrationTerminalState(
    candidateMigrationOwnValue(parsed, "status"),
  );
  const finishedAtMs = candidateMigrationFinishedAtMs(
    candidateMigrationOwnValue(parsed, "finished_at_ms") ??
      candidateMigrationOwnValue(parsed, "finished_at"),
  );
  if (!identityMatches) {
    entry.disposition = "QUARANTINED";
    entry.reasonCode = "AMBIGUOUS_IDENTITY";
  } else if (entry.protocolVersion !== candidateProtocolVersion) {
    entry.disposition = "QUARANTINED";
    entry.reasonCode = "INCOMPATIBLE_PROTOCOL";
  } else if (!["PASS", "CACHED"].includes(entry.terminalState)) {
    entry.disposition = "QUARANTINED";
    entry.reasonCode = "UNSAFE_TERMINAL";
  } else if (finishedAtMs === null || finishedAtMs < staleBeforeMs) {
    entry.disposition = "QUARANTINED";
    entry.reasonCode = "STALE";
  } else if (entryKind === "JOB") {
    entry.reasonCode = "JOB_METADATA_ONLY";
  } else {
    entry.reasonCode = "SAFE_TERMINAL_AUDIT_ONLY";
  }
  return entry;
}

function scanCandidateMigrationSource(canonicalSourceRoot, options) {
  const entries = candidateMigrationRecognizedFiles(canonicalSourceRoot).map((file) =>
    readCandidateMigrationFile({
      canonicalSourceRoot,
      ...file,
      ...options,
    }),
  );
  const sourceHash = candidateSha256(
    canonicalPayloadJson(
      entries.map((entry) => ({
        byteCount: entry.byteCount,
        contentHash: entry.contentHash,
        entryKind: entry.entryKind,
        logicalIdentityHash: entry.logicalIdentityHash,
        relativePathHash: entry.relativePathHash,
      })),
    ),
  );
  return { entries, sourceHash };
}

function captureCandidateMigrationSources(sources, canonicalCopyRoot, options) {
  const capturedSources = captureCandidateDenseArray(
    sources,
    "candidate migration sources",
    MAX_CANDIDATE_MIGRATION_SOURCES,
  ).map((source) => {
    const captured = captureCandidateDataObject(
      source,
      ["namespace", "sourceKind", "copiedRoot"],
      ["namespace", "sourceKind", "copiedRoot"],
      "candidate migration source",
    );
    if (
      typeof captured.namespace !== "string" ||
      !/^[A-Za-z0-9._:-]{1,256}$/.test(captured.namespace) ||
      [".", ".."].includes(captured.namespace) ||
      !CANDIDATE_MIGRATION_SOURCE_KINDS.has(captured.sourceKind) ||
      typeof captured.copiedRoot !== "string" ||
      !path.isAbsolute(captured.copiedRoot) ||
      captured.copiedRoot.includes("\0")
    ) {
      throw new TypeError("invalid candidate migration source");
    }
    const rootStats = lstatSync(captured.copiedRoot);
    if (!rootStats.isDirectory() || rootStats.isSymbolicLink()) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "copied migration source is not an isolated directory",
      );
    }
    const canonicalSourceRoot = realpathSync.native(captured.copiedRoot);
    if (
      filesystemPathIdentity(canonicalSourceRoot) ===
        filesystemPathIdentity(canonicalCopyRoot) ||
      !candidatePathContains(canonicalCopyRoot, canonicalSourceRoot)
    ) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "copied migration source escapes the copy root",
      );
    }
    const { entries, sourceHash } = scanCandidateMigrationSource(
      canonicalSourceRoot,
      options,
    );
    return {
      canonicalSourceRoot,
      entries,
      namespace: captured.namespace,
      sourceHash,
      sourceKind: captured.sourceKind,
    };
  });
  capturedSources.sort((left, right) =>
    candidateUtf8Compare(left.namespace, right.namespace),
  );
  if (
    new Set(capturedSources.map((source) => source.namespace)).size !==
    capturedSources.length
  ) {
    throw candidateMigrationError(
      "MIGRATION_DUPLICATE_NAMESPACE",
      "copied migration source namespace is duplicated",
    );
  }
  return capturedSources;
}

function resolveCandidateMigrationCollisions(sources, candidateProtocolVersion) {
  const groups = new Map();
  for (const source of sources) {
    for (const entry of source.entries) {
      if (!["JOB", "CACHE"].includes(entry.entryKind)) continue;
      const key = `${entry.entryKind}:${entry.logicalIdentityHash}`;
      const group = groups.get(key) ?? [];
      group.push(entry);
      groups.set(key, group);
    }
  }
  const collisions = [];
  for (const entries of groups.values()) {
    if (entries.length < 2) continue;
    const byteIdentical =
      new Set(entries.map((entry) => entry.contentHash)).size === 1;
    const protocolCompatible = entries.every(
      (entry) => entry.protocolVersion === candidateProtocolVersion,
    );
    let disposition;
    let reasonCode;
    if (byteIdentical && protocolCompatible) {
      disposition = "IDENTICAL_COMPATIBLE";
      reasonCode = "IDENTICAL_PROTOCOL_COMPATIBLE";
    } else if (byteIdentical) {
      disposition = "QUARANTINED";
      reasonCode = "PROTOCOL_MISMATCH";
    } else {
      disposition = "QUARANTINED";
      reasonCode = "CONTENT_MISMATCH";
    }
    if (disposition === "QUARANTINED") {
      for (const entry of entries) {
        entry.disposition = "QUARANTINED";
        entry.reasonCode = "COLLISION";
      }
    }
    collisions.push({
      collisionKind: entries[0].entryKind,
      disposition,
      logicalIdentityHash: entries[0].logicalIdentityHash,
      reasonCode,
      sourceCount: entries.length,
    });
  }
  collisions.sort((left, right) =>
    candidateUtf8Compare(
      `${left.collisionKind}:${left.logicalIdentityHash}`,
      `${right.collisionKind}:${right.logicalIdentityHash}`,
    ),
  );
  return collisions;
}

function candidateMigrationOperationalRowCount(database) {
  let count = 0;
  for (const table of CANDIDATE_MIGRATION_OPERATIONAL_TABLES) {
    count += database.prepare(`SELECT COUNT(*) AS count FROM "${table}"`).get().count;
  }
  return count;
}

function captureCandidateMigrationHashMap(value) {
  try {
    if (
      value === null ||
      typeof value !== "object" ||
      Array.isArray(value) ||
      Object.getPrototypeOf(value) !== Object.prototype
    ) {
      throw new TypeError();
    }
    const descriptors = Object.getOwnPropertyDescriptors(value);
    const keys = Reflect.ownKeys(descriptors);
    if (keys.length > MAX_CANDIDATE_MIGRATION_SOURCES) throw new TypeError();
    const captured = new Map();
    for (const key of keys) {
      const descriptor = descriptors[key];
      if (
        typeof key !== "string" ||
        descriptor.enumerable !== true ||
        !Object.hasOwn(descriptor, "value") ||
        !/^[A-Za-z0-9._:-]{1,256}$/.test(key) ||
        typeof descriptor.value !== "string" ||
        !/^[0-9a-f]{64}$/.test(descriptor.value)
      ) {
        throw new TypeError();
      }
      captured.set(key, descriptor.value);
    }
    return captured;
  } catch {
    throw new TypeError("invalid candidate migration source hashes");
  }
}

function captureCandidateBindingIds(value) {
  if (!Array.isArray(value)) {
    throw new TypeError("bindingIds must be a nonempty array");
  }
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const keys = Reflect.ownKeys(descriptors);
  const lengthDescriptor = descriptors.length;
  if (
    !Object.hasOwn(descriptors, "length") ||
    !Object.hasOwn(lengthDescriptor, "value") ||
    !Number.isSafeInteger(lengthDescriptor.value) ||
    lengthDescriptor.value < 1 ||
    lengthDescriptor.value > 100 ||
    keys.length !== lengthDescriptor.value + 1
  ) {
    throw new TypeError("bindingIds must contain 1 to 100 exact identities");
  }
  const ids = [];
  const seen = new Set();
  for (let index = 0; index < lengthDescriptor.value; index += 1) {
    const descriptor = descriptors[String(index)];
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value") ||
      !Number.isSafeInteger(descriptor.value) ||
      descriptor.value < 1 ||
      seen.has(descriptor.value)
    ) {
      throw new TypeError(
        "bindingIds must contain unique positive safe integers",
      );
    }
    seen.add(descriptor.value);
    ids.push(descriptor.value);
  }
  return Object.freeze(ids.sort((left, right) => left - right));
}

function candidateMigrationAttestation(
  database,
  projectId,
  runId,
  storeSchemaVersion = readExactSchemaVersion(database, [
    String(CANDIDATE_STORE_SCHEMA_V3_VERSION),
    String(CANDIDATE_STORE_SCHEMA_V4_VERSION),
    String(CANDIDATE_STORE_SCHEMA_VERSION),
  ]),
) {
  if (
    ![
      CANDIDATE_STORE_SCHEMA_V3_VERSION,
      CANDIDATE_STORE_SCHEMA_V4_VERSION,
      CANDIDATE_STORE_SCHEMA_VERSION,
    ].includes(storeSchemaVersion)
  ) {
    throw stateError(
      "MIGRATION_ATTESTATION_UPGRADE_REJECTED",
      "migration attestation store schema is unsupported",
    );
  }
  const run = database
    .prepare(
      `SELECT run_id,project_id,workspace_identity_hash,candidate_protocol_version,
              run_state
       FROM legacy_migration_runs
       WHERE run_id=? AND project_id=?`,
    )
    .get(runId, projectId);
  if (run === undefined || run.run_state !== "READY") {
    throw stateError("MIGRATION_UNATTESTED", "migration attestation is not READY");
  }
  const sources = database
    .prepare(
      `SELECT source_namespace,source_kind,source_hash,entry_count
       FROM legacy_migration_sources
       WHERE run_id=?
       ORDER BY source_namespace`,
    )
    .all(runId)
    .map((source) => ({
      entryCount: source.entry_count,
      namespace: source.source_namespace,
      sourceHash: source.source_hash,
      sourceKind: source.source_kind,
    }));
  const collisions = database
    .prepare(
      `SELECT
         COUNT(*) AS collision_count,
         SUM(CASE WHEN disposition='UNRESOLVED' THEN 1 ELSE 0 END)
           AS unresolved_count
       FROM legacy_migration_collisions
       WHERE run_id=?`,
    )
    .get(runId);
  const unresolvedCollisions = collisions.unresolved_count ?? 0;
  if (sources.length === 0 || unresolvedCollisions !== 0) {
    throw stateError("MIGRATION_UNATTESTED", "migration attestation is incomplete");
  }
  const operationalImports = database
    .prepare(
      `SELECT COUNT(*) AS count
       FROM legacy_migration_entries
       WHERE run_id=? AND disposition NOT IN ('AUDIT_ONLY','QUARANTINED')`,
    )
    .get(runId).count;
  if (operationalImports !== 0) {
    throw stateError("MIGRATION_UNATTESTED", "migration imported operational state");
  }
  if (database.prepare("PRAGMA foreign_key_check").all().length !== 0) {
    throw stateError("MIGRATION_UNATTESTED", "migration foreign-key check failed");
  }
  const integrityRows = database.prepare("PRAGMA integrity_check").all();
  if (
    integrityRows.length !== 1 ||
    Object.values(integrityRows[0])[0] !== "ok"
  ) {
    throw stateError("MIGRATION_UNATTESTED", "migration integrity check failed");
  }
  const sourceSetHash = candidateSha256(
    canonicalPayloadJson({
      protocol: "DEEPLUNA_CANDIDATE_MIGRATION_SOURCE_SET_V1",
      sources,
    }),
  );
  const attestationId = candidateSha256(
    canonicalPayloadJson({
      candidateProtocolVersion: run.candidate_protocol_version,
      projectId,
      protocol: "DEEPLUNA_CANDIDATE_MIGRATION_ATTESTATION_V1",
      runId,
      sourceSetHash,
      storeSchemaVersion,
      workspaceIdentityHash: run.workspace_identity_hash,
    }),
  );
  return Object.freeze({
    attested: true,
    attestationId,
    operationalImports,
    projectId,
    runId,
    sourceSetHash,
    unresolvedCollisions,
  });
}

function captureCandidateMigrationAttestation(value) {
  const captured = captureCandidateDataObject(
    value,
    [
      "attested",
      "attestationId",
      "operationalImports",
      "projectId",
      "runId",
      "sourceSetHash",
      "unresolvedCollisions",
    ],
    [
      "attested",
      "attestationId",
      "operationalImports",
      "projectId",
      "runId",
      "sourceSetHash",
      "unresolvedCollisions",
    ],
    "candidate migration attestation",
  );
  if (
    captured.attested !== true ||
    typeof captured.projectId !== "string" ||
    !/^[A-Za-z0-9._:-]{1,256}$/.test(captured.projectId) ||
    typeof captured.runId !== "string" ||
    !/^migration-[0-9a-f]{32}$/.test(captured.runId) ||
    typeof captured.attestationId !== "string" ||
    !/^[0-9a-f]{64}$/.test(captured.attestationId) ||
    typeof captured.sourceSetHash !== "string" ||
    !/^[0-9a-f]{64}$/.test(captured.sourceSetHash) ||
    captured.unresolvedCollisions !== 0 ||
    captured.operationalImports !== 0
  ) {
    throw new TypeError("invalid candidate migration attestation");
  }
  return captured;
}

function publicCandidateMigrationOutcome(database, runRow) {
  const sourceCount = database
    .prepare(
      "SELECT COUNT(*) AS count FROM legacy_migration_sources WHERE run_id=?",
    )
    .get(runRow.run_id).count;
  const entryCounts = database
    .prepare(
      `SELECT
         COUNT(*) AS entry_count,
         SUM(CASE WHEN disposition='QUARANTINED' THEN 1 ELSE 0 END)
           AS quarantined_count
       FROM legacy_migration_entries
       WHERE run_id=?`,
    )
    .get(runRow.run_id);
  const collisionCounts = database
    .prepare(
      `SELECT
         COUNT(*) AS collision_count,
         SUM(CASE WHEN disposition='UNRESOLVED' THEN 1 ELSE 0 END)
           AS unresolved_count
       FROM legacy_migration_collisions
       WHERE run_id=?`,
    )
    .get(runRow.run_id);
  return Object.freeze({
    runId: runRow.run_id,
    state: runRow.run_state,
    canonicalWorkspace: runRow.canonical_workspace,
    sourceCount,
    entryCount: entryCounts.entry_count,
    collisionCount: collisionCounts.collision_count,
    unresolvedCollisionCount: collisionCounts.unresolved_count ?? 0,
    promotableCount: 0,
    quarantinedCount: entryCounts.quarantined_count ?? 0,
  });
}

export class SchedulerStore {
  #protocolRequestDepth = 0;
  #legacyProtocolWritable;
  #candidateCostWritable;
  #candidateLegacyCostWritable;
  #candidateTransmissionCostWritable;

  constructor(
    database,
    now,
    {
      legacyProtocolWritable = true,
      candidateCostCapability,
      candidateTransmissionCostCapability,
    } = {},
  ) {
    if (typeof legacyProtocolWritable !== "boolean") {
      throw new TypeError("legacyProtocolWritable must be a boolean");
    }
    if (
      candidateCostCapability !== undefined &&
      candidateCostCapability !== CANDIDATE_COST_CAPABILITY
    ) {
      throw new TypeError("invalid candidate cost capability");
    }
    if (
      candidateTransmissionCostCapability !== undefined &&
      candidateTransmissionCostCapability !== CANDIDATE_TRANSMISSION_COST_CAPABILITY
    ) {
      throw new TypeError("invalid candidate transmission cost capability");
    }
    this.database = database;
    this.now = now;
    this.#legacyProtocolWritable = legacyProtocolWritable;
    this.#candidateLegacyCostWritable =
      candidateCostCapability === CANDIDATE_COST_CAPABILITY;
    this.#candidateTransmissionCostWritable =
      candidateTransmissionCostCapability ===
      CANDIDATE_TRANSMISSION_COST_CAPABILITY;
    this.#candidateCostWritable =
      this.#candidateLegacyCostWritable || this.#candidateTransmissionCostWritable;
  }

  getCandidateStoreSchemaVersion() {
    this.#requireCandidateSchemaWritable();
    const row = this.database
      .prepare("SELECT value FROM schema_meta WHERE key='schema_version'")
      .get();
    const version = Number(row?.value);
    if (
      !Number.isSafeInteger(version) ||
      ![
        CANDIDATE_STORE_SCHEMA_V3_VERSION,
        CANDIDATE_STORE_SCHEMA_V4_VERSION,
        CANDIDATE_STORE_SCHEMA_VERSION,
      ].includes(version)
    ) {
      throw stateError(
        "UNSUPPORTED_SCHEMA_VERSION",
        "candidate schema version is unsupported",
      );
    }
    return version;
  }

  registerCandidateOrigin(request) {
    this.#requireCandidateSchemaWritable();
    const origin = captureCandidateOriginRequest(request);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO projects (project_id,created_at_ms)
           VALUES (?,?)
           ON CONFLICT(project_id) DO NOTHING`,
        )
        .run(origin.projectId, now);
      this.database
        .prepare(
          `INSERT INTO origins
             (project_id,origin_thread_hash,origin_capability_hash,created_at_ms)
           VALUES (?,?,?,?)
           ON CONFLICT(project_id,origin_thread_hash,origin_capability_hash)
           DO NOTHING`,
        )
        .run(
          origin.projectId,
          origin.originThreadHash,
          origin.originCapabilityHash,
          now,
        );
      const row = this.database
        .prepare(
          `SELECT origin_id,project_id,origin_thread_hash,origin_capability_hash
           FROM origins
           WHERE project_id=? AND origin_thread_hash=? AND origin_capability_hash=?`,
        )
        .get(
          origin.projectId,
          origin.originThreadHash,
          origin.originCapabilityHash,
        );
      if (row === undefined) {
        throw stateError("ORIGIN_REGISTRATION_FAILED", "candidate origin registration failed");
      }
      this.database.exec("COMMIT");
      return publicCandidateOrigin(row);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  authenticateCandidateOrigin(request) {
    this.#requireCandidateSchemaWritable();
    const origin = captureCandidateOriginRequest(request);
    const row = this.database
      .prepare(
        `SELECT origin_id,project_id,origin_thread_hash,origin_capability_hash
         FROM origins
         WHERE project_id=? AND origin_thread_hash=? AND origin_capability_hash=?`,
      )
      .get(
        origin.projectId,
        origin.originThreadHash,
        origin.originCapabilityHash,
      );
    if (row === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
    return publicCandidateOrigin(row);
  }

  submitCandidateWorker(request) {
    this.#requireCandidateTransmissionCostWritable();
    const capturedRequest = captureCandidateDataObject(
      request,
      ["originId", "contract"],
      undefined,
      "candidate worker submission",
    );
    const originId = requireSafeInteger(
      capturedRequest.originId,
      "originId must be a positive safe integer",
      1,
    );
    const contract = captureCandidateContract(capturedRequest.contract);
    const projectId = requireCostProjectId(contract.projectId);
    const priority = requireSafeInteger(
      contract.priority === undefined ? 0 : contract.priority,
      "priority must be a finite safe integer",
    );
    const maximumAttempts = requireSafeInteger(
      contract.maximumAttempts === undefined ? 1 : contract.maximumAttempts,
      "maximumAttempts must be a positive safe integer",
      1,
    );
    const executionFingerprint = candidateSha256(
      canonicalPayloadJson({
        contractHash: contract.contractHash,
        inputFingerprint: contract.inputFingerprint,
        maximumAttempts,
        payload: contract.payload === undefined ? null : contract.payload,
        poolId: contract.poolId,
        priority,
        projectId,
        role: contract.role,
      }),
    );
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const priorBinding = this.database
        .prepare(
          `SELECT *
           FROM worker_bindings
           WHERE project_id=? AND execution_fingerprint=?
             AND binding_state IN ('ACTIVE','SEALED')
           ORDER BY binding_epoch DESC
           LIMIT 1`,
        )
        .get(projectId, executionFingerprint);
      const generation = this.enqueueCandidateJob({
        originId,
        contract,
      });
      let binding = priorBinding;
      if (binding === undefined) {
        const bindingEpoch = this.database
          .prepare(
            `SELECT COALESCE(MAX(binding_epoch),0)+1 AS next_epoch
             FROM worker_bindings
             WHERE project_id=? AND execution_fingerprint=?`,
          )
          .get(projectId, executionFingerprint).next_epoch;
        const now = requireNow(this.now());
        this.database
          .prepare(
            `INSERT INTO worker_bindings
               (project_id,execution_fingerprint,binding_epoch,job_id,generation,
                binding_state,created_at_ms,updated_at_ms)
             VALUES (?,?,?,?,?,'ACTIVE',?,?)`,
          )
          .run(
            projectId,
            executionFingerprint,
            bindingEpoch,
            generation.jobId,
            generation.generation,
            now,
            now,
          );
        binding = this.database
          .prepare(
            `SELECT *
             FROM worker_bindings
             WHERE project_id=? AND execution_fingerprint=?
               AND binding_state='ACTIVE'`,
          )
          .get(projectId, executionFingerprint);
      }
      if (
        binding.job_id !== generation.jobId ||
        binding.generation !== generation.generation
      ) {
        throw stateError(
          "WORKER_BINDING_CONFLICT",
          "active worker binding conflicts with the exact producer",
        );
      }
      const publicId = candidateWorkerPublicId(
        projectId,
        originId,
        binding.binding_id,
      );
      const claimState =
        binding.binding_state === "SEALED" ? "TERMINAL" : "ATTACHED";
      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO public_resources
             (public_id,resource_kind,origin_id,project_id,created_at_ms)
           VALUES (?,'WORKER_JOB',?,?,?)
           ON CONFLICT(public_id) DO NOTHING`,
        )
        .run(publicId, originId, projectId, now);
      const publicResource = this.database
        .prepare(
          `SELECT resource_kind,origin_id,project_id
           FROM public_resources WHERE public_id=?`,
        )
        .get(publicId);
      if (
        publicResource?.resource_kind !== "WORKER_JOB" ||
        publicResource.origin_id !== originId ||
        publicResource.project_id !== projectId
      ) {
        throw stateError(
          "PUBLIC_ID_CONFLICT",
          "candidate public identity conflicts with an existing resource",
        );
      }
      this.database
        .prepare(
          `INSERT INTO worker_claims
             (public_id,origin_id,project_id,binding_id,claim_state,
              created_at_ms,updated_at_ms)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(origin_id,binding_id) DO UPDATE SET
             claim_state=CASE
               WHEN excluded.claim_state='TERMINAL' THEN 'TERMINAL'
               WHEN worker_claims.claim_state='DETACHED' THEN 'ATTACHED'
               ELSE worker_claims.claim_state
             END,
             updated_at_ms=excluded.updated_at_ms`,
        )
        .run(
          publicId,
          originId,
          projectId,
          binding.binding_id,
          claimState,
          now,
          now,
        );
      const status = this.#candidateWorkerStatusRow(
        originId,
        projectId,
        publicId,
      );
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        schema_version: 1,
        jobId: publicId,
        producerJobId: generation.jobId,
        generation: generation.generation,
        status: status.status,
        execution_status: status.executionStatus,
        evidence_verdict: status.evidenceVerdict,
        cache_hit: status.cacheHit,
        coalesced: priorBinding !== undefined,
      });
    } catch (error) {
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  getCandidateWorkerStatus(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "jobId"],
      undefined,
      "candidate worker status request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const publicId = requireCostText(captured.jobId, "jobId", 35);
    const row = this.#candidateWorkerStatusRow(originId, projectId, publicId);
    const packet =
      row.canonicalJson === null
        ? null
        : candidateDeepFreeze(JSON.parse(row.canonicalJson));
    return Object.freeze({
      schema_version: 1,
      job_id: publicId,
      status: row.status,
      execution_status: row.executionStatus,
      evidence_verdict: row.evidenceVerdict,
      cache_hit: row.cacheHit,
      subscriber_state: row.claimState,
      result_packet: packet,
    });
  }

  detachCandidateWorker(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "jobId"],
      undefined,
      "candidate worker detach request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const publicId = requireCostText(captured.jobId, "jobId", 35);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const before = this.#candidateWorkerStatusRow(
        originId,
        projectId,
        publicId,
      );
      const now = requireNow(this.now());
      const changed = this.database
        .prepare(
          `UPDATE worker_claims
           SET claim_state='DETACHED',updated_at_ms=?
           WHERE public_id=? AND origin_id=? AND project_id=?
             AND claim_state='ATTACHED'`,
        )
        .run(now, publicId, originId, projectId);
      const remaining = this.database
        .prepare(
          `SELECT COUNT(*) AS count
           FROM worker_claims
           WHERE binding_id=? AND claim_state='ATTACHED'`,
        )
        .get(before.bindingId).count;
      this.database.exec("COMMIT");
      return Object.freeze({
        detached: changed.changes === 1,
        jobId: publicId,
        remainingAttached: remaining,
        status: before.status,
      });
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  reconcileCandidateQuarantinedWorkerBindings(request) {
    this.#requireCandidateTransmissionCostWritable();
    if (this.getCandidateStoreSchemaVersion() !== CANDIDATE_STORE_SCHEMA_VERSION) {
      throw stateError(
        "CANDIDATE_RECONCILIATION_UNAVAILABLE",
        "historical worker reconciliation requires candidate schema v5",
      );
    }
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "bindingIds", "operatorAuthorized"],
      ["projectId", "bindingIds", "operatorAuthorized"],
      "candidate quarantined worker reconciliation request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const bindingIds = captureCandidateBindingIds(captured.bindingIds);
    if (captured.operatorAuthorized !== true) {
      throw new TypeError(
        "operatorAuthorized must be true for historical worker reconciliation",
      );
    }
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      let reconciled = 0;
      let replayed = 0;
      for (const bindingId of bindingIds) {
        const binding = this.database
          .prepare(
            `SELECT binding.binding_id,binding.binding_state,binding.job_id,
                    binding.generation,generation.state AS generation_state
             FROM worker_bindings AS binding
             JOIN generations AS generation
               ON generation.job_id=binding.job_id
              AND generation.generation=binding.generation
             WHERE binding.project_id=? AND binding.binding_id=?`,
          )
          .get(projectId, bindingId);
        if (binding === undefined) {
          throw stateError(
            "NOT_FOUND_OR_NOT_OWNED",
            "candidate worker binding was not found",
          );
        }
        const claims = this.database
          .prepare(
            `SELECT claim_state,COUNT(*) AS count
             FROM worker_claims
             WHERE project_id=? AND binding_id=?
             GROUP BY claim_state
             ORDER BY claim_state`,
          )
          .all(projectId, bindingId);
        const claimCount = claims.reduce(
          (total, claim) => total + claim.count,
          0,
        );
        const terminalClaimCount =
          claims.find((claim) => claim.claim_state === "TERMINAL")?.count ?? 0;
        const detachedClaimCount =
          claims.find((claim) => claim.claim_state === "DETACHED")?.count ?? 0;
        const subject = this.database
          .prepare(
            `SELECT subject.subject_state,subject.accepted_packet_hash,
                    packet.public_status,packet.execution_status,
                    packet.evidence_verdict,packet.cache_hit
             FROM result_subjects AS subject
             LEFT JOIN result_packets AS packet
               ON packet.packet_hash=subject.accepted_packet_hash
             WHERE subject.worker_binding_id=?`,
          )
          .get(bindingId);
        if (binding.binding_state === "SEALED") {
          if (
            binding.generation_state !== "QUARANTINED" ||
            claimCount < 1 ||
            terminalClaimCount !== claimCount ||
            subject?.subject_state !== "NORMALIZED" ||
            subject.public_status !== "FAIL" ||
            subject.execution_status !== "CONTRACT_ERROR" ||
            subject.evidence_verdict !== "UNRESOLVED" ||
            subject.cache_hit !== 0
          ) {
            throw stateError(
              "CANDIDATE_RECONCILIATION_CONFLICT",
              "candidate worker binding has a conflicting terminal state",
            );
          }
          replayed += 1;
          continue;
        }
        const leaseCount = this.database
          .prepare(
            `SELECT COUNT(*) AS count
             FROM leases
             WHERE job_id=? AND generation=?`,
          )
          .get(binding.job_id, binding.generation).count;
        const runningAttemptCount = this.database
          .prepare(
            `SELECT COUNT(*) AS count
             FROM attempts
             WHERE job_id=? AND generation=? AND state='RUNNING'`,
          )
          .get(binding.job_id, binding.generation).count;
        const writerLockCount = this.database
          .prepare(
            `SELECT COUNT(*) AS count
             FROM writer_locks
             WHERE owner_job_id=? AND owner_generation=?`,
          )
          .get(binding.job_id, binding.generation).count;
        const failure = this.database
          .prepare(
            `SELECT failure_class
             FROM attempts
             WHERE job_id=? AND generation=? AND state='FAILED'
             ORDER BY started_at_ms DESC,attempt_id DESC
             LIMIT 1`,
          )
          .get(binding.job_id, binding.generation);
        if (
          binding.binding_state !== "ACTIVE" ||
          binding.generation_state !== "QUARANTINED" ||
          claimCount < 1 ||
          detachedClaimCount !== claimCount ||
          subject !== undefined ||
          leaseCount !== 0 ||
          runningAttemptCount !== 0 ||
          writerLockCount !== 0 ||
          failure === undefined
        ) {
          throw stateError(
            "CANDIDATE_RECONCILIATION_UNSAFE",
            "candidate worker binding is not an exact detached quarantined orphan",
          );
        }
        const failureClass =
          typeof failure.failure_class === "string" &&
          /^[A-Z][A-Z0-9_:-]{0,127}$/.test(failure.failure_class)
            ? failure.failure_class
            : "HISTORICAL_WORKER_FAILURE";
        const normalized = captureCandidatePublicResultPacket({
          schema_version: 1,
          result_protocol: 3,
          status: "FAIL",
          execution_status: "CONTRACT_ERROR",
          evidence_verdict: "UNRESOLVED",
          cache_hit: false,
          summary:
            "A historical worker failure was quarantined before a public result packet was committed.",
          positive_findings: [],
          negative_findings: [
            `The terminal failure class was ${failureClass}.`,
          ],
          residual_risks: [
            "No provider result from the quarantined worker was accepted as evidence.",
          ],
          recommended_next_action:
            "Submit a new bounded task only after the original contract failure is corrected.",
          scientific_uncertainty: false,
          architecture_uncertainty: true,
          scope_deviation: false,
        });
        const existingPacket = this.database
          .prepare(
            "SELECT canonical_json FROM result_packets WHERE packet_hash=?",
          )
          .get(normalized.packetHash);
        if (
          existingPacket !== undefined &&
          existingPacket.canonical_json !== normalized.canonicalJson
        ) {
          throw stateError(
            "RESULT_PACKET_CONFLICT",
            "historical worker result hash conflicts with stored content",
          );
        }
        const now = requireNow(this.now());
        this.database
          .prepare(
            `INSERT INTO result_packets
               (packet_hash,result_protocol,public_status,execution_status,
                evidence_verdict,cache_hit,canonical_json,byte_count,
                created_at_ms)
             VALUES (?,3,'FAIL','CONTRACT_ERROR','UNRESOLVED',0,?,?,?)
             ON CONFLICT(packet_hash) DO NOTHING`,
          )
          .run(
            normalized.packetHash,
            normalized.canonicalJson,
            normalized.byteCount,
            now,
          );
        const normalizationSourceJson = canonicalPayloadJson({
          bindingId,
          failureClass,
          generation: binding.generation,
          jobId: binding.job_id,
          protocol: "DEEPLUNA_QUARANTINED_WORKER_RECONCILIATION_V1",
        });
        this.database
          .prepare(
            `INSERT INTO result_subjects
               (subject_kind,worker_binding_id,head_run_id,
                normalization_source_json,normalization_source_hash,
                normalization_source_bytes,normalization_epoch,subject_state,
                accepted_packet_hash,created_at_ms,updated_at_ms)
             VALUES ('WORKER',?,NULL,?,?,?,1,'NORMALIZED',?,?,?)`,
          )
          .run(
            bindingId,
            normalizationSourceJson,
            candidateSha256(normalizationSourceJson),
            Buffer.byteLength(normalizationSourceJson, "utf8"),
            normalized.packetHash,
            now,
            now,
          );
        const bindingUpdate = this.database
          .prepare(
            `UPDATE worker_bindings
             SET binding_state='SEALED',updated_at_ms=?
             WHERE project_id=? AND binding_id=? AND binding_state='ACTIVE'`,
          )
          .run(now, projectId, bindingId);
        const claimUpdate = this.database
          .prepare(
            `UPDATE worker_claims
             SET claim_state='TERMINAL',updated_at_ms=?
             WHERE project_id=? AND binding_id=? AND claim_state='DETACHED'`,
          )
          .run(now, projectId, bindingId);
        if (
          bindingUpdate.changes !== 1 ||
          claimUpdate.changes !== claimCount
        ) {
          throw stateError(
            "CANDIDATE_RECONCILIATION_CONFLICT",
            "candidate worker reconciliation lost its state race",
          );
        }
        reconciled += 1;
      }
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        projectId,
        bindingIds,
        reconciled,
        replayed,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  quarantineAndPublishCandidateWorkerFailure(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "attemptId",
        "workerId",
        "epoch",
        "failureClass",
        "packet",
      ],
      undefined,
      "candidate worker failure terminalization",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const identity = requireLeaseIdentity(captured);
    const failureClass = requireBoundedString(
      captured.failureClass,
      "failureClass must be a bounded nonblank string",
      128,
    );
    if (!/^[A-Z][A-Z0-9_:-]*$/.test(failureClass)) {
      throw new TypeError("failureClass must be a stable failure code");
    }
    const normalized = captureCandidatePublicResultPacket(captured.packet);
    if (
      !["FAIL", "BLOCKED"].includes(normalized.packet.status) ||
      normalized.packet.evidence_verdict !== "UNRESOLVED" ||
      normalized.packet.cache_hit !== false
    ) {
      throw stateError(
        "INVALID_PUBLIC_RESULT_PACKET",
        "candidate failure terminalization requires a nonaccepted packet",
      );
    }
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const binding = this.database
        .prepare(
          `SELECT binding.binding_id,binding.binding_state
           FROM worker_bindings AS binding
           WHERE binding.project_id=?
             AND binding.job_id=?
             AND binding.generation=?
             AND EXISTS (
               SELECT 1
               FROM worker_claims AS claim
               WHERE claim.binding_id=binding.binding_id
                 AND claim.origin_id=?
                 AND claim.project_id=?
             )`,
        )
        .get(
          projectId,
          identity.jobId,
          identity.generation,
          originId,
          projectId,
        );
      if (binding === undefined || binding.binding_state !== "ACTIVE") {
        throw stateError(
          "STALE_ATTEMPT_LEASE",
          "candidate failure binding is no longer active",
        );
      }
      const now = requireNow(this.now());
      const updated = this.database
        .prepare(
          `UPDATE generations
           SET state='QUARANTINED',
               accepted_result_hash=NULL,
               diagnostic_enqueued=0,
               updated_at_ms=?
           WHERE job_id=?
             AND generation=?
             AND state IN ('RUNNING','VALIDATING')
             AND EXISTS (
               SELECT 1
               FROM leases AS lease
               WHERE lease.job_id=generations.job_id
                 AND lease.generation=generations.generation
                 AND lease.attempt_id=?
                 AND lease.worker_id=?
                 AND lease.epoch=?
             )`,
        )
        .run(
          now,
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      if (updated.changes !== 1) {
        throw stateError(
          "STALE_ATTEMPT_LEASE",
          "candidate failure attempt is no longer current",
        );
      }
      this.database
        .prepare(
          `UPDATE attempts
           SET state='FAILED',finished_at_ms=?,failure_class=?
           WHERE job_id=?
             AND generation=?
             AND attempt_id=?
             AND worker_id=?
             AND epoch=?`,
        )
        .run(
          now,
          failureClass,
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      const existingPacket = this.database
        .prepare("SELECT canonical_json FROM result_packets WHERE packet_hash=?")
        .get(normalized.packetHash);
      if (
        existingPacket !== undefined &&
        existingPacket.canonical_json !== normalized.canonicalJson
      ) {
        throw stateError(
          "RESULT_PACKET_CONFLICT",
          "public result hash conflicts with stored content",
        );
      }
      this.database
        .prepare(
          `INSERT INTO result_packets
             (packet_hash,result_protocol,public_status,execution_status,
              evidence_verdict,cache_hit,canonical_json,byte_count,created_at_ms)
           VALUES (?,3,?,?,?,?,?,?,?)
           ON CONFLICT(packet_hash) DO NOTHING`,
        )
        .run(
          normalized.packetHash,
          normalized.packet.status,
          normalized.packet.execution_status,
          normalized.packet.evidence_verdict,
          0,
          normalized.canonicalJson,
          normalized.byteCount,
          now,
        );
      const normalizationSourceJson = canonicalPayloadJson({
        failureClass,
        generation: identity.generation,
        jobId: identity.jobId,
        terminalState: "QUARANTINED",
      });
      const existingSubject = this.database
        .prepare(
          `SELECT subject_state,accepted_packet_hash
           FROM result_subjects
           WHERE worker_binding_id=?`,
        )
        .get(binding.binding_id);
      if (existingSubject === undefined) {
        this.database
          .prepare(
            `INSERT INTO result_subjects
               (subject_kind,worker_binding_id,head_run_id,
                normalization_source_json,normalization_source_hash,
                normalization_source_bytes,normalization_epoch,subject_state,
                accepted_packet_hash,created_at_ms,updated_at_ms)
             VALUES ('WORKER',?,NULL,?,?,?,1,'NORMALIZED',?,?,?)`,
          )
          .run(
            binding.binding_id,
            normalizationSourceJson,
            candidateSha256(normalizationSourceJson),
            Buffer.byteLength(normalizationSourceJson, "utf8"),
            normalized.packetHash,
            now,
            now,
          );
      } else if (
        existingSubject.subject_state !== "NORMALIZED" ||
        existingSubject.accepted_packet_hash !== normalized.packetHash
      ) {
        throw stateError(
          "RESULT_PACKET_CONFLICT",
          "producer already has a different public result",
        );
      }
      this.database
        .prepare(
          `UPDATE worker_bindings
           SET binding_state='SEALED',updated_at_ms=?
           WHERE binding_id=? AND binding_state='ACTIVE'`,
        )
        .run(now, binding.binding_id);
      this.database
        .prepare(
          `UPDATE worker_claims
           SET claim_state='TERMINAL',updated_at_ms=?
           WHERE binding_id=?
             AND claim_state IN ('ATTACHED','DETACHED','TERMINAL')`,
        )
        .run(now, binding.binding_id);
      this.#deleteCandidateWriterLockForTerminal(
        identity.jobId,
        identity.generation,
        identity.epoch,
      );
      this.database
        .prepare(
          `DELETE FROM leases
           WHERE job_id=?
             AND generation=?
             AND attempt_id=?
             AND worker_id=?
             AND epoch=?`,
        )
        .run(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      this.database
        .prepare(
          `INSERT INTO events
             (job_id,generation,event_type,event_json,created_at_ms)
           VALUES (?,?,'RESULT_QUARANTINED',?,?)`,
        )
        .run(
          identity.jobId,
          identity.generation,
          canonicalPayloadJson({ failureClass }),
          now,
        );
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        packetHash: normalized.packetHash,
        byteCount: normalized.byteCount,
        status: normalized.packet.status,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  cancelCandidateWorker(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "cancelWhenUnobserved",
      ],
      undefined,
      "candidate worker cancellation request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const publicId = requireCostText(captured.jobId, "jobId", 35);
    if (typeof captured.cancelWhenUnobserved !== "boolean") {
      throw new TypeError("cancelWhenUnobserved must be a boolean");
    }
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const before = this.#candidateWorkerStatusRow(
        originId,
        projectId,
        publicId,
      );
      if (CANDIDATE_PUBLIC_TERMINAL_STATUSES.includes(before.status)) {
        throw stateError("JOB_TERMINAL", "job is terminal");
      }
      const now = requireNow(this.now());
      const changed = this.database
        .prepare(
          `UPDATE worker_claims
           SET claim_state='DETACHED',updated_at_ms=?
           WHERE public_id=? AND origin_id=? AND project_id=?
             AND claim_state='ATTACHED'`,
        )
        .run(now, publicId, originId, projectId);
      const remaining = this.database
        .prepare(
          `SELECT COUNT(*) AS count
           FROM worker_claims
           WHERE binding_id=? AND claim_state='ATTACHED'`,
        )
        .get(before.bindingId).count;
      let producerCancelled = false;
      if (remaining === 0 && captured.cancelWhenUnobserved) {
        this.cancelGeneration({
          jobId: before.producerJobId,
          generation: before.generation,
          actor: "authenticated-origin",
          reason: "final authorized subscriber detached",
        });
        const normalized = captureCandidatePublicResultPacket({
          schema_version: 1,
          result_protocol: 3,
          status: "BLOCKED",
          execution_status: "CANCELLED",
          evidence_verdict: "UNRESOLVED",
          cache_hit: false,
          summary:
            "The shared producer was cancelled after its final subscriber detached.",
          positive_findings: [],
          negative_findings: [
            "No authorized subscriber remained for the shared producer.",
          ],
          residual_risks: [
            "Cancelled work has no accepted evidence result.",
          ],
          recommended_next_action:
            "Submit a new bounded request if the work is still required.",
          scientific_uncertainty: false,
          architecture_uncertainty: false,
          scope_deviation: false,
        });
        this.database
          .prepare(
            `INSERT INTO result_packets
               (packet_hash,result_protocol,public_status,execution_status,
                evidence_verdict,cache_hit,canonical_json,byte_count,created_at_ms)
             VALUES (?,3,?,?,?,?,?,?,?)
             ON CONFLICT(packet_hash) DO NOTHING`,
          )
          .run(
            normalized.packetHash,
            normalized.packet.status,
            normalized.packet.execution_status,
            normalized.packet.evidence_verdict,
            0,
            normalized.canonicalJson,
            normalized.byteCount,
            now,
          );
        const normalizationSourceJson = canonicalPayloadJson({
          cancellation: "UNOBSERVED_SUBSCRIBER_POLICY",
          generation: before.generation,
          jobId: before.producerJobId,
        });
        this.database
          .prepare(
            `INSERT INTO result_subjects
               (subject_kind,worker_binding_id,head_run_id,
                normalization_source_json,normalization_source_hash,
                normalization_source_bytes,normalization_epoch,subject_state,
                accepted_packet_hash,created_at_ms,updated_at_ms)
             VALUES ('WORKER',?,NULL,?,?,?,1,'NORMALIZED',?,?,?)`,
          )
          .run(
            before.bindingId,
            normalizationSourceJson,
            candidateSha256(normalizationSourceJson),
            Buffer.byteLength(normalizationSourceJson, "utf8"),
            normalized.packetHash,
            now,
            now,
          );
        this.database
          .prepare(
            `UPDATE worker_bindings
             SET binding_state='SEALED',updated_at_ms=?
             WHERE binding_id=? AND binding_state='ACTIVE'`,
          )
          .run(now, before.bindingId);
        this.database
          .prepare(
            `UPDATE worker_claims
             SET claim_state='TERMINAL',updated_at_ms=?
             WHERE binding_id=?`,
          )
          .run(now, before.bindingId);
        producerCancelled = true;
      }
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        schema_version: 1,
        job_id: publicId,
        detached: changed.changes === 1,
        remaining_subscribers: remaining,
        producer_cancelled: producerCancelled,
        subscriber_state: producerCancelled ? "TERMINAL" : "DETACHED",
        status: producerCancelled ? "BLOCKED" : before.status,
        execution_status: producerCancelled
          ? "CANCELLED"
          : before.executionStatus,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  publishCandidateWorkerResult(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "jobId", "generation", "packet"],
      undefined,
      "candidate worker result publication",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const jobId = requireCostText(captured.jobId, "jobId", 256);
    const generation = requireSafeInteger(
      captured.generation,
      "generation must be a positive safe integer",
      1,
    );
    const normalized = captureCandidatePublicResultPacket(captured.packet);
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const binding = this.database
        .prepare(
          `SELECT binding.*,generation.state,generation.accepted_result_hash
           FROM worker_bindings AS binding
           JOIN generations AS generation
             ON generation.job_id=binding.job_id
            AND generation.generation=binding.generation
           WHERE binding.project_id=? AND binding.job_id=?
             AND binding.generation=?`,
        )
        .get(projectId, jobId, generation);
      if (
        binding === undefined ||
        binding.state !== "SUCCEEDED" ||
        binding.accepted_result_hash === null
      ) {
        throw stateError(
          "RESULT_NOT_ACCEPTED",
          "public result requires an accepted producer generation",
        );
      }
      const existingPacket = this.database
        .prepare("SELECT canonical_json FROM result_packets WHERE packet_hash=?")
        .get(normalized.packetHash);
      if (
        existingPacket !== undefined &&
        existingPacket.canonical_json !== normalized.canonicalJson
      ) {
        throw stateError(
          "RESULT_PACKET_CONFLICT",
          "public result hash conflicts with stored content",
        );
      }
      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO result_packets
             (packet_hash,result_protocol,public_status,execution_status,
              evidence_verdict,cache_hit,canonical_json,byte_count,created_at_ms)
           VALUES (?,3,?,?,?,?,?,?,?)
           ON CONFLICT(packet_hash) DO NOTHING`,
        )
        .run(
          normalized.packetHash,
          normalized.packet.status,
          normalized.packet.execution_status,
          normalized.packet.evidence_verdict,
          normalized.packet.cache_hit ? 1 : 0,
          normalized.canonicalJson,
          normalized.byteCount,
          now,
        );
      let subject = this.database
        .prepare(
          `SELECT * FROM result_subjects
           WHERE worker_binding_id=?`,
        )
        .get(binding.binding_id);
      if (subject === undefined) {
        const normalizationSourceJson = canonicalPayloadJson({
          acceptedResultHash: binding.accepted_result_hash,
          generation,
          jobId,
        });
        this.database
          .prepare(
            `INSERT INTO result_subjects
               (subject_kind,worker_binding_id,head_run_id,
                normalization_source_json,normalization_source_hash,
                normalization_source_bytes,normalization_epoch,subject_state,
                accepted_packet_hash,created_at_ms,updated_at_ms)
             VALUES ('WORKER',?,NULL,?,?,?,1,'NORMALIZED',?,?,?)`,
          )
          .run(
            binding.binding_id,
            normalizationSourceJson,
            candidateSha256(normalizationSourceJson),
            Buffer.byteLength(normalizationSourceJson, "utf8"),
            normalized.packetHash,
            now,
            now,
          );
        subject = this.database
          .prepare(
            `SELECT * FROM result_subjects
             WHERE worker_binding_id=?`,
          )
          .get(binding.binding_id);
      } else if (
        subject.subject_state !== "NORMALIZED" ||
        subject.accepted_packet_hash !== normalized.packetHash
      ) {
        throw stateError(
          "RESULT_PACKET_CONFLICT",
          "producer already has a different public result",
        );
      }
      this.database
        .prepare(
          `UPDATE worker_bindings
           SET binding_state='SEALED',updated_at_ms=?
           WHERE binding_id=? AND binding_state IN ('ACTIVE','SEALED')`,
        )
        .run(now, binding.binding_id);
      this.database
        .prepare(
          `UPDATE worker_claims
           SET claim_state='TERMINAL',updated_at_ms=?
           WHERE binding_id=? AND claim_state IN ('ATTACHED','DETACHED','TERMINAL')`,
        )
        .run(now, binding.binding_id);
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        packetHash: normalized.packetHash,
        byteCount: normalized.byteCount,
        status: normalized.packet.status,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  acceptAndPublishCandidateWorkerResult(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "attemptId",
        "workerId",
        "epoch",
        "resultHash",
        "inputFingerprint",
        "writerFencingToken",
        "packet",
      ],
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "attemptId",
        "workerId",
        "epoch",
        "resultHash",
        "inputFingerprint",
        "packet",
      ],
      "candidate accepted public result",
    );
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const acceptance = this.acceptCandidateResult({
        originId: captured.originId,
        projectId: captured.projectId,
        jobId: captured.jobId,
        generation: captured.generation,
        attemptId: captured.attemptId,
        workerId: captured.workerId,
        epoch: captured.epoch,
        resultHash: captured.resultHash,
        inputFingerprint: captured.inputFingerprint,
        ...(captured.writerFencingToken === undefined
          ? {}
          : { writerFencingToken: captured.writerFencingToken }),
      });
      if (acceptance.accepted !== true) {
        throw stateError(
          "STALE_ATTEMPT_LEASE",
          "result acceptance was fenced",
        );
      }
      const publication = this.publishCandidateWorkerResult({
        projectId: captured.projectId,
        jobId: captured.jobId,
        generation: captured.generation,
        packet: captured.packet,
      });
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({ acceptance, publication });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  recordCandidateSolPlan(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "plan"],
      undefined,
      "candidate Sol plan persistence request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const plan = captureCandidateSolPlan(captured.plan);
    this.#requireCandidateOriginMembership(originId, projectId);
    const parsedPlan = JSON.parse(plan.planJson);
    if (
      parsedPlan.plan_id !== plan.planId ||
      parsedPlan.project_id !== projectId
    ) {
      throw stateError(
        "INVALID_SOL_PLAN",
        "candidate Sol plan payload identity does not match its scope",
      );
    }
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO public_resources
             (public_id,resource_kind,origin_id,project_id,created_at_ms)
           VALUES (?,'SOL_PLAN',?,?,?)
           ON CONFLICT(public_id) DO NOTHING`,
        )
        .run(plan.planId, originId, projectId, now);
      const publicResource = this.database
        .prepare(
          `SELECT resource_kind,origin_id,project_id
           FROM public_resources WHERE public_id=?`,
        )
        .get(plan.planId);
      if (
        publicResource?.resource_kind !== "SOL_PLAN" ||
        publicResource.origin_id !== originId ||
        publicResource.project_id !== projectId
      ) {
        throw stateError(
          "PUBLIC_ID_CONFLICT",
          "candidate public identity conflicts with an existing resource",
        );
      }
      this.database
        .prepare(
          `INSERT INTO sol_plans
             (plan_id,origin_id,project_id,input_fingerprint,attempt_fingerprint,
              decision,selected_effort,max_eligible,cache_eligible,policy_hash,
              evidence_hash,governance_hash,plan_json,plan_bytes,created_at_ms)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(plan_id) DO NOTHING`,
        )
        .run(
          plan.planId,
          originId,
          projectId,
          plan.inputFingerprint,
          plan.attemptFingerprint,
          plan.decision,
          plan.selectedEffort,
          plan.maxEligible ? 1 : 0,
          plan.cacheEligible ? 1 : 0,
          plan.policyHash,
          plan.evidenceHash,
          plan.governanceHash,
          plan.planJson,
          plan.planBytes,
          now,
        );
      const stored = this.database
        .prepare("SELECT * FROM sol_plans WHERE plan_id=?")
        .get(plan.planId);
      const coherent =
        stored?.origin_id === originId &&
        stored.project_id === projectId &&
        stored.input_fingerprint === plan.inputFingerprint &&
        stored.attempt_fingerprint === plan.attemptFingerprint &&
        stored.decision === plan.decision &&
        stored.selected_effort === plan.selectedEffort &&
        Boolean(stored.max_eligible) === plan.maxEligible &&
        Boolean(stored.cache_eligible) === plan.cacheEligible &&
        stored.policy_hash === plan.policyHash &&
        stored.evidence_hash === plan.evidenceHash &&
        stored.governance_hash === plan.governanceHash &&
        stored.plan_json === plan.planJson &&
        stored.plan_bytes === plan.planBytes;
      if (!coherent) {
        throw stateError(
          "SOL_PLAN_CONFLICT",
          "candidate Sol plan conflicts with stored identity",
        );
      }
      const reasonInsert = this.database.prepare(
        `INSERT INTO sol_plan_reasons (plan_id,ordinal,reason_code)
         VALUES (?,?,?)
         ON CONFLICT(plan_id,ordinal) DO NOTHING`,
      );
      for (const [ordinal, reason] of plan.reasons.entries()) {
        reasonInsert.run(plan.planId, ordinal, reason);
      }
      const storedReasons = this.database
        .prepare(
          `SELECT ordinal,reason_code
           FROM sol_plan_reasons WHERE plan_id=? ORDER BY ordinal`,
        )
        .all(plan.planId);
      if (
        storedReasons.length !== plan.reasons.length ||
        storedReasons.some(
          (row, ordinal) =>
            row.ordinal !== ordinal ||
            row.reason_code !== plan.reasons[ordinal],
        )
      ) {
        throw stateError(
          "SOL_PLAN_CONFLICT",
          "candidate Sol plan reasons conflict with stored identity",
        );
      }
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        schema_version: 1,
        plan_id: plan.planId,
        decision: plan.decision,
        selected_effort: plan.selectedEffort,
        reasons: plan.reasons,
        max_eligible: plan.maxEligible,
        attempt_fingerprint: plan.attemptFingerprint,
        input_fingerprint: plan.inputFingerprint,
        cache_eligible: plan.cacheEligible,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  submitCandidateHead(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "planId"],
      undefined,
      "candidate head submission request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const planId = requireCostText(captured.planId, "planId", 36);
    if (!/^SRP-[a-f0-9]{32}$/.test(planId)) {
      throw stateError("INVALID_SOL_PLAN", "invalid candidate Sol plan id");
    }
    this.#requireCandidateOriginMembership(originId, projectId);
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const plan = this.database
        .prepare(
          `SELECT * FROM sol_plans
           WHERE plan_id=? AND origin_id=? AND project_id=?`,
        )
        .get(planId, originId, projectId);
      if (plan === undefined) {
        throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
      }
      if (plan.decision !== "START_SOL_HEAD") {
        throw stateError(
          "HEAD_PLAN_NOT_LAUNCHABLE",
          "candidate Sol plan is not launch eligible",
        );
      }
      let run = this.database
        .prepare(
          `SELECT * FROM head_runs
           WHERE project_id=? AND attempt_fingerprint=?
             AND run_state IN ('QUEUED','RUNNING')
           ORDER BY binding_epoch DESC LIMIT 1`,
        )
        .get(projectId, plan.attempt_fingerprint);
      const coalesced = run !== undefined;
      if (
        run !== undefined &&
        run.selected_effort !== plan.selected_effort
      ) {
        throw stateError(
          "HEAD_BINDING_CONFLICT",
          "active candidate head conflicts with the exact effort",
        );
      }
      const priorMaxAttempt =
        plan.max_eligible === 1
          ? this.database
              .prepare(
                `SELECT * FROM max_attempt_claims
                 WHERE project_id=? AND attempt_fingerprint=?`,
              )
              .get(projectId, plan.attempt_fingerprint)
          : undefined;
      if (run === undefined && priorMaxAttempt !== undefined) {
        throw stateError(
          "MAX_ATTEMPT_EXHAUSTED",
          "one-shot Max attempt already recorded for this route",
        );
      }
      const now = requireNow(this.now());
      if (run === undefined) {
        const bindingEpoch = this.database
          .prepare(
            `SELECT COALESCE(MAX(binding_epoch),0)+1 AS next_epoch
             FROM head_runs
             WHERE project_id=? AND attempt_fingerprint=?`,
          )
          .get(projectId, plan.attempt_fingerprint).next_epoch;
        const headRunId = this.database
          .prepare(
            `INSERT INTO head_runs
               (project_id,attempt_fingerprint,binding_epoch,selected_effort,
                run_state,created_at_ms,updated_at_ms)
             VALUES (?,?,?,?,'QUEUED',?,?)`,
          )
          .run(
            projectId,
            plan.attempt_fingerprint,
            bindingEpoch,
            plan.selected_effort,
            now,
            now,
          ).lastInsertRowid;
        run = this.database
          .prepare("SELECT * FROM head_runs WHERE head_run_id=?")
          .get(headRunId);
      }
      let producerJobId = null;
      if (
        this.getCandidateStoreSchemaVersion() ===
        CANDIDATE_STORE_SCHEMA_VERSION
      ) {
        producerJobId = deterministicCandidateHeadProducerId({
          projectId,
          attemptFingerprint: run.attempt_fingerprint,
          bindingEpoch: run.binding_epoch,
        });
        if (!coalesced) {
          this.database
            .prepare(
              `INSERT INTO head_producer_attempts
                 (head_run_id,project_id,producer_job_id,attempt_fingerprint,
                  plan_id,selected_effort,producer_state,external_start_possible,
                  process_boot_id,owner_pid,terminal_result_hash,claimed_at_ms,
                  started_at_ms,finished_at_ms,created_at_ms,updated_at_ms)
               VALUES (?,?,?,?,?,?,'QUEUED',0,NULL,NULL,NULL,NULL,NULL,NULL,?,?)`,
            )
            .run(
              run.head_run_id,
              projectId,
              producerJobId,
              run.attempt_fingerprint,
              planId,
              run.selected_effort,
              now,
              now,
            );
        }
        const producer = this.database
          .prepare(
            `SELECT producer.*,run.binding_epoch,run.run_state
             FROM head_producer_attempts AS producer
             JOIN head_runs AS run ON run.head_run_id=producer.head_run_id
             WHERE producer.head_run_id=? AND producer.project_id=?`,
          )
          .get(run.head_run_id, projectId);
        const producerSnapshot = candidateHeadProducerSnapshot(producer);
        if (
          producerSnapshot.producerJobId !== producerJobId ||
          producerSnapshot.attemptFingerprint !== plan.attempt_fingerprint ||
          producerSnapshot.selectedEffort !== plan.selected_effort ||
          !["QUEUED", "CLAIMED", "RUNNING"].includes(
            producerSnapshot.producerState,
          )
        ) {
          throw stateError(
            "HEAD_PRODUCER_IDENTITY_CONFLICT",
            "active candidate head producer conflicts with the durable run",
          );
        }
      }
      if (plan.max_eligible === 1) {
        if (priorMaxAttempt === undefined) {
          this.database
            .prepare(
              `INSERT INTO max_attempt_claims
                 (project_id,attempt_fingerprint,plan_id,decision,max_eligible,
                  selected_effort,head_run_id,claimed_at_ms)
               VALUES (?, ?,?,'START_SOL_HEAD',1,'max',?,?)`,
            )
            .run(
              projectId,
              plan.attempt_fingerprint,
              planId,
              run.head_run_id,
              now,
            );
        } else if (priorMaxAttempt.head_run_id !== run.head_run_id) {
          throw stateError(
            "MAX_ATTEMPT_EXHAUSTED",
            "one-shot Max attempt already recorded for this route",
          );
        }
      }
      const publicId = candidateHeadPublicId(
        projectId,
        originId,
        planId,
        run.head_run_id,
      );
      this.database
        .prepare(
          `INSERT INTO public_resources
             (public_id,resource_kind,origin_id,project_id,created_at_ms)
           VALUES (?,'HEAD_JOB',?,?,?)
           ON CONFLICT(public_id) DO NOTHING`,
        )
        .run(publicId, originId, projectId, now);
      const publicResource = this.database
        .prepare(
          `SELECT resource_kind,origin_id,project_id
           FROM public_resources WHERE public_id=?`,
        )
        .get(publicId);
      if (
        publicResource?.resource_kind !== "HEAD_JOB" ||
        publicResource.origin_id !== originId ||
        publicResource.project_id !== projectId
      ) {
        throw stateError(
          "PUBLIC_ID_CONFLICT",
          "candidate public identity conflicts with an existing resource",
        );
      }
      this.database
        .prepare(
          `INSERT INTO head_claims
             (public_id,origin_id,project_id,plan_id,attempt_fingerprint,
              selected_effort,head_run_id,claim_state,created_at_ms,updated_at_ms)
           VALUES (?,?,?,?,?,?,?,'ATTACHED',?,?)
           ON CONFLICT(public_id) DO UPDATE SET
             claim_state=CASE
               WHEN head_claims.claim_state='DETACHED' THEN 'ATTACHED'
               ELSE head_claims.claim_state
             END,
             updated_at_ms=excluded.updated_at_ms`,
        )
        .run(
          publicId,
          originId,
          projectId,
          planId,
          plan.attempt_fingerprint,
          plan.selected_effort,
          run.head_run_id,
          now,
          now,
        );
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        schema_version: 1,
        jobId: publicId,
        producerHeadRunId: run.head_run_id,
        ...(producerJobId === null ? {} : { producerJobId }),
        status: run.run_state,
        execution_status: "INCOMPLETE",
        evidence_verdict: "UNRESOLVED",
        cache_hit: false,
        coalesced,
        plan_id: planId,
        requested_effort: plan.selected_effort,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  listQueuedCandidateHeadProducers(request) {
    this.#requireCandidateTransmissionCostWritable();
    this.#requireCandidateHeadProducerWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "limit"],
      undefined,
      "candidate queued head producers request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const limit = requireSafeInteger(
      captured.limit,
      "limit must be a positive safe integer",
      1,
    );
    if (limit > 100) throw new TypeError("limit must not exceed 100");
    return Object.freeze(
      this.database
        .prepare(
          `SELECT producer.*,run.binding_epoch,run.run_state
           FROM head_producer_attempts AS producer
           JOIN head_runs AS run
             ON run.head_run_id=producer.head_run_id
            AND run.project_id=producer.project_id
           WHERE producer.project_id=? AND producer.producer_state='QUEUED'
             AND run.run_state='QUEUED'
           ORDER BY producer.created_at_ms,producer.producer_job_id
           LIMIT ?`,
        )
        .all(projectId, limit)
        .map((row) => candidateHeadProducerSnapshot(row)),
    );
  }

  claimCandidateHeadProducer(request) {
    this.#requireCandidateTransmissionCostWritable();
    this.#requireCandidateHeadProducerWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "producerJobId", "processBootId", "ownerPid"],
      undefined,
      "candidate head producer claim request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const producerJobId = requireCandidateHeadProducerId(
      captured.producerJobId,
    );
    const processBootId = requireCandidateProcessBootId(
      captured.processBootId,
    );
    const ownerPid = requireSafeInteger(
      captured.ownerPid,
      "ownerPid must be a positive safe integer",
      1,
    );
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const current = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (current.producerState === "CLAIMED") {
        if (
          current.processBootId === processBootId &&
          current.ownerPid === ownerPid
        ) {
          if (ownsTransaction) this.database.exec("COMMIT");
          return current;
        }
        throw stateError(
          "HEAD_PRODUCER_OWNERSHIP_CONFLICT",
          "candidate head producer is owned by another process",
        );
      }
      if (
        current.producerState !== "QUEUED" ||
        current.runState !== "QUEUED"
      ) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head producer cannot be claimed from its current state",
        );
      }
      const now = requireNow(this.now());
      const updated = this.database
        .prepare(
          `UPDATE head_producer_attempts
           SET producer_state='CLAIMED',process_boot_id=?,owner_pid=?,
               claimed_at_ms=?,updated_at_ms=?
           WHERE project_id=? AND producer_job_id=?
             AND producer_state='QUEUED' AND external_start_possible=0`,
        )
        .run(
          processBootId,
          ownerPid,
          now,
          now,
          projectId,
          producerJobId,
        );
      if (updated.changes !== 1) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head producer claim lost its state race",
        );
      }
      const snapshot = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (ownsTransaction) this.database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  markCandidateHeadProducerStarted(request) {
    this.#requireCandidateTransmissionCostWritable();
    this.#requireCandidateHeadProducerWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "producerJobId", "processBootId", "ownerPid"],
      undefined,
      "candidate head producer start request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const producerJobId = requireCandidateHeadProducerId(
      captured.producerJobId,
    );
    const processBootId = requireCandidateProcessBootId(
      captured.processBootId,
    );
    const ownerPid = requireSafeInteger(
      captured.ownerPid,
      "ownerPid must be a positive safe integer",
      1,
    );
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const current = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (
        current.processBootId !== processBootId ||
        current.ownerPid !== ownerPid
      ) {
        throw stateError(
          "HEAD_PRODUCER_OWNERSHIP_CONFLICT",
          "candidate head producer is owned by another process",
        );
      }
      if (current.producerState === "RUNNING") {
        if (ownsTransaction) this.database.exec("COMMIT");
        return current;
      }
      if (
        current.producerState !== "CLAIMED" ||
        current.runState !== "QUEUED"
      ) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head producer cannot start from its current state",
        );
      }
      const now = requireNow(this.now());
      const runUpdate = this.database
        .prepare(
          `UPDATE head_runs
           SET run_state='RUNNING',updated_at_ms=?
           WHERE head_run_id=? AND project_id=? AND run_state='QUEUED'`,
        )
        .run(now, current.headRunId, projectId);
      const producerUpdate = this.database
        .prepare(
          `UPDATE head_producer_attempts
           SET producer_state='RUNNING',external_start_possible=1,
               started_at_ms=?,updated_at_ms=?
           WHERE project_id=? AND producer_job_id=?
             AND producer_state='CLAIMED'
             AND process_boot_id=? AND owner_pid=?`,
        )
        .run(
          now,
          now,
          projectId,
          producerJobId,
          processBootId,
          ownerPid,
        );
      if (runUpdate.changes !== 1 || producerUpdate.changes !== 1) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head producer start lost its state race",
        );
      }
      const snapshot = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (ownsTransaction) this.database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  completeCandidateHeadProducer(request) {
    this.#requireCandidateTransmissionCostWritable();
    this.#requireCandidateHeadProducerWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "producerJobId", "processBootId", "ownerPid", "packet"],
      undefined,
      "candidate head producer completion request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const producerJobId = requireCandidateHeadProducerId(
      captured.producerJobId,
    );
    const processBootId = requireCandidateProcessBootId(
      captured.processBootId,
    );
    const ownerPid = requireSafeInteger(
      captured.ownerPid,
      "ownerPid must be a positive safe integer",
      1,
    );
    const normalized = captureCandidatePublicResultPacket(captured.packet);
    let producerState;
    let runState;
    if (["PASS", "CACHED"].includes(normalized.packet.status)) {
      producerState = "SUCCEEDED";
      runState = "SUCCEEDED";
    } else if (normalized.packet.execution_status === "CANCELLED") {
      producerState = "CANCELED";
      runState = "CANCELED";
    } else if (normalized.packet.status === "BLOCKED") {
      producerState = "BLOCKED";
      runState = "FAILED";
    } else {
      producerState = "FAILED";
      runState = "FAILED";
    }
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const current = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (
        current.processBootId !== processBootId ||
        current.ownerPid !== ownerPid
      ) {
        throw stateError(
          "HEAD_PRODUCER_OWNERSHIP_CONFLICT",
          "candidate head producer is owned by another process",
        );
      }
      if (
        ["SUCCEEDED", "FAILED", "BLOCKED", "CANCELED"].includes(
          current.producerState,
        )
      ) {
        if (
          current.producerState === producerState &&
          current.terminalResultHash === normalized.packetHash
        ) {
          if (ownsTransaction) this.database.exec("COMMIT");
          return current;
        }
        throw stateError(
          "HEAD_PRODUCER_RESULT_CONFLICT",
          "candidate head producer already has a different terminal result",
        );
      }
      const preStartCompletion =
        current.producerState === "CLAIMED" &&
        current.runState === "QUEUED" &&
        !current.externalStartPossible;
      const runningCompletion =
        current.producerState === "RUNNING" &&
        current.runState === "RUNNING" &&
        current.externalStartPossible;
      if (!preStartCompletion && !runningCompletion) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head producer cannot complete from its current state",
        );
      }
      if (
        preStartCompletion &&
        producerState === "SUCCEEDED" &&
        normalized.packet.cache_hit !== true
      ) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "a non-cache success cannot complete before external start",
        );
      }
      const now = requireNow(this.now());
      const runUpdate = this.database
        .prepare(
          `UPDATE head_runs
           SET run_state=?,updated_at_ms=?
           WHERE head_run_id=? AND project_id=? AND run_state=?`,
        )
        .run(
          runState,
          now,
          current.headRunId,
          projectId,
          current.runState,
        );
      if (runUpdate.changes !== 1) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head run completion lost its state race",
        );
      }
      const publication = this.publishCandidateHeadResult({
        projectId,
        headRunId: current.headRunId,
        packet: normalized.packet,
      });
      const producerUpdate = this.database
        .prepare(
          `UPDATE head_producer_attempts
           SET producer_state=?,terminal_result_hash=?,finished_at_ms=?,
               updated_at_ms=?
           WHERE project_id=? AND producer_job_id=?
             AND producer_state=?
             AND process_boot_id=? AND owner_pid=?`,
        )
        .run(
          producerState,
          publication.packetHash,
          now,
          now,
          projectId,
          producerJobId,
          current.producerState,
          processBootId,
          ownerPid,
        );
      if (producerUpdate.changes !== 1) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head producer completion lost its state race",
        );
      }
      const snapshot = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (ownsTransaction) this.database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  markCandidateHeadProducerUnknown(request) {
    this.#requireCandidateTransmissionCostWritable();
    this.#requireCandidateHeadProducerWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "producerJobId", "reasonCode"],
      undefined,
      "candidate head producer unknown request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const producerJobId = requireCandidateHeadProducerId(
      captured.producerJobId,
    );
    const reasonCode = requireCostText(captured.reasonCode, "reasonCode", 64);
    if (!/^[a-z][a-z0-9-]{0,63}$/.test(reasonCode)) {
      throw new TypeError("reasonCode must be a stable lower-case token");
    }
    const normalized = captureCandidatePublicResultPacket(
      candidateUnknownHeadPacket(reasonCode),
    );
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const current = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (current.producerState === "UNKNOWN") {
        if (current.terminalResultHash === normalized.packetHash) {
          if (ownsTransaction) this.database.exec("COMMIT");
          return current;
        }
        throw stateError(
          "HEAD_PRODUCER_RESULT_CONFLICT",
          "candidate head producer already has a different unknown result",
        );
      }
      if (
        current.producerState !== "RUNNING" ||
        current.runState !== "RUNNING" ||
        !current.externalStartPossible
      ) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head producer cannot become unknown before external start",
        );
      }
      const now = requireNow(this.now());
      const runUpdate = this.database
        .prepare(
          `UPDATE head_runs
           SET run_state='FAILED',updated_at_ms=?
           WHERE head_run_id=? AND project_id=? AND run_state='RUNNING'`,
        )
        .run(now, current.headRunId, projectId);
      if (runUpdate.changes !== 1) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head recovery lost its run-state race",
        );
      }
      const publication = this.publishCandidateHeadResult({
        projectId,
        headRunId: current.headRunId,
        packet: normalized.packet,
      });
      const producerUpdate = this.database
        .prepare(
          `UPDATE head_producer_attempts
           SET producer_state='UNKNOWN',terminal_result_hash=?,
               finished_at_ms=?,updated_at_ms=?
           WHERE project_id=? AND producer_job_id=?
             AND producer_state='RUNNING' AND external_start_possible=1`,
        )
        .run(
          publication.packetHash,
          now,
          now,
          projectId,
          producerJobId,
        );
      if (producerUpdate.changes !== 1) {
        throw stateError(
          "HEAD_PRODUCER_STATE_CONFLICT",
          "candidate head recovery lost its producer-state race",
        );
      }
      const snapshot = candidateHeadProducerSnapshot(
        this.#candidateHeadProducerRow(projectId, producerJobId),
      );
      if (ownsTransaction) this.database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  recoverCandidateHeadProducers(request) {
    this.#requireCandidateTransmissionCostWritable();
    this.#requireCandidateHeadProducerWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "currentProcessBootId", "isProcessAlive"],
      undefined,
      "candidate head producer recovery request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const currentProcessBootId = requireCandidateProcessBootId(
      captured.currentProcessBootId,
    );
    if (typeof captured.isProcessAlive !== "function") {
      throw new TypeError("isProcessAlive must be a function");
    }
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const active = this.database
        .prepare(
          `SELECT producer.*,run.binding_epoch,run.run_state
           FROM head_producer_attempts AS producer
           JOIN head_runs AS run
             ON run.head_run_id=producer.head_run_id
            AND run.project_id=producer.project_id
           WHERE producer.project_id=?
             AND producer.producer_state IN ('CLAIMED','RUNNING')
           ORDER BY producer.created_at_ms,producer.producer_job_id`,
        )
        .all(projectId)
        .map((row) => candidateHeadProducerSnapshot(row));
      let requeued = 0;
      let unknown = 0;
      let activeOwners = 0;
      for (const producer of active) {
        const alive =
          producer.processBootId === currentProcessBootId &&
          Reflect.apply(captured.isProcessAlive, undefined, [
            producer.ownerPid,
          ]) === true;
        if (alive) {
          activeOwners += 1;
          continue;
        }
        if (
          producer.producerState === "CLAIMED" &&
          !producer.externalStartPossible
        ) {
          const now = requireNow(this.now());
          const update = this.database
            .prepare(
              `UPDATE head_producer_attempts
               SET producer_state='QUEUED',process_boot_id=NULL,owner_pid=NULL,
                   claimed_at_ms=NULL,updated_at_ms=?
               WHERE project_id=? AND producer_job_id=?
                 AND producer_state='CLAIMED'
                 AND external_start_possible=0`,
            )
            .run(now, projectId, producer.producerJobId);
          if (update.changes !== 1) {
            throw stateError(
              "HEAD_PRODUCER_STATE_CONFLICT",
              "candidate head recovery lost its claim-state race",
            );
          }
          requeued += 1;
          continue;
        }
        this.markCandidateHeadProducerUnknown({
          projectId,
          producerJobId: producer.producerJobId,
          reasonCode: "owner-lost-after-external-start",
        });
        unknown += 1;
      }
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        projectId,
        inspected: active.length,
        activeOwners,
        requeued,
        unknown,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  publishCandidateHeadResult(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "headRunId", "packet"],
      undefined,
      "candidate head result publication",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const headRunId = requireSafeInteger(
      captured.headRunId,
      "headRunId must be a positive safe integer",
      1,
    );
    const normalized = captureCandidatePublicResultPacket(captured.packet);
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const run = this.database
        .prepare(
          `SELECT * FROM head_runs
           WHERE head_run_id=? AND project_id=?`,
        )
        .get(headRunId, projectId);
      if (run === undefined) {
        throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
      }
      const coherent =
        (run.run_state === "SUCCEEDED" &&
          ["PASS", "CACHED"].includes(normalized.packet.status)) ||
        (run.run_state === "FAILED" &&
          ["FAIL", "BLOCKED"].includes(normalized.packet.status)) ||
        (run.run_state === "CANCELED" &&
          normalized.packet.status === "BLOCKED" &&
          normalized.packet.execution_status === "CANCELLED") ||
        (run.run_state === "QUARANTINED" &&
          normalized.packet.status === "FAIL" &&
          normalized.packet.execution_status === "CONTRACT_ERROR");
      if (!coherent) {
        throw stateError(
          "RESULT_NOT_ACCEPTED",
          "public head result does not match the terminal head run",
        );
      }
      const existingPacket = this.database
        .prepare("SELECT canonical_json FROM result_packets WHERE packet_hash=?")
        .get(normalized.packetHash);
      if (
        existingPacket !== undefined &&
        existingPacket.canonical_json !== normalized.canonicalJson
      ) {
        throw stateError(
          "RESULT_PACKET_CONFLICT",
          "public result hash conflicts with stored content",
        );
      }
      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO result_packets
             (packet_hash,result_protocol,public_status,execution_status,
              evidence_verdict,cache_hit,canonical_json,byte_count,created_at_ms)
           VALUES (?,3,?,?,?,?,?,?,?)
           ON CONFLICT(packet_hash) DO NOTHING`,
        )
        .run(
          normalized.packetHash,
          normalized.packet.status,
          normalized.packet.execution_status,
          normalized.packet.evidence_verdict,
          normalized.packet.cache_hit ? 1 : 0,
          normalized.canonicalJson,
          normalized.byteCount,
          now,
        );
      const normalizationSourceJson = canonicalPayloadJson({
        headRunId,
        runState: run.run_state,
        selectedEffort: run.selected_effort,
      });
      const subject = this.database
        .prepare("SELECT * FROM result_subjects WHERE head_run_id=?")
        .get(headRunId);
      if (subject === undefined) {
        this.database
          .prepare(
            `INSERT INTO result_subjects
               (subject_kind,worker_binding_id,head_run_id,
                normalization_source_json,normalization_source_hash,
                normalization_source_bytes,normalization_epoch,subject_state,
                accepted_packet_hash,created_at_ms,updated_at_ms)
             VALUES ('HEAD',NULL,?,?,?, ?,1,'NORMALIZED',?,?,?)`,
          )
          .run(
            headRunId,
            normalizationSourceJson,
            candidateSha256(normalizationSourceJson),
            Buffer.byteLength(normalizationSourceJson, "utf8"),
            normalized.packetHash,
            now,
            now,
          );
      } else if (
        subject.subject_state !== "NORMALIZED" ||
        subject.accepted_packet_hash !== normalized.packetHash
      ) {
        throw stateError(
          "RESULT_PACKET_CONFLICT",
          "head run already has a different public result",
        );
      }
      this.database
        .prepare(
          `UPDATE head_claims
           SET claim_state='TERMINAL',updated_at_ms=?
           WHERE head_run_id=?`,
        )
        .run(now, headRunId);
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        packetHash: normalized.packetHash,
        byteCount: normalized.byteCount,
        status: normalized.packet.status,
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  getCandidateHeadStatus(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "jobId"],
      undefined,
      "candidate head status request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const publicId = requireCostText(captured.jobId, "jobId", 35);
    const row = this.database
      .prepare(
        `SELECT claim.plan_id,claim.selected_effort,claim.claim_state,
                run.run_state,packet.public_status,packet.execution_status,
                packet.evidence_verdict,packet.cache_hit,packet.canonical_json
         FROM head_claims AS claim
         JOIN head_runs AS run
           ON run.head_run_id=claim.head_run_id
          AND run.project_id=claim.project_id
         LEFT JOIN result_subjects AS subject
           ON subject.head_run_id=run.head_run_id
          AND subject.subject_state='NORMALIZED'
         LEFT JOIN result_packets AS packet
           ON packet.packet_hash=subject.accepted_packet_hash
         WHERE claim.public_id=? AND claim.origin_id=? AND claim.project_id=?`,
      )
      .get(publicId, originId, projectId);
    if (row === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
    let identity;
    if (row.canonical_json !== null) {
      identity = {
        status: row.public_status,
        execution_status: row.execution_status,
        evidence_verdict: row.evidence_verdict,
        cache_hit: Boolean(row.cache_hit),
      };
    } else if (row.run_state === "QUEUED") {
      identity = {
        status: "QUEUED",
        execution_status: "INCOMPLETE",
        evidence_verdict: "UNRESOLVED",
        cache_hit: false,
      };
    } else if (row.run_state === "RUNNING") {
      identity = {
        status: "RUNNING",
        execution_status: "INCOMPLETE",
        evidence_verdict: "UNRESOLVED",
        cache_hit: false,
      };
    } else {
      throw stateError(
        "RESULT_PACKET_MISSING",
        "terminal head run has no public result",
      );
    }
    return Object.freeze({
      schema_version: 1,
      job_id: publicId,
      plan_id: row.plan_id,
      ...identity,
      requested_effort: row.selected_effort,
      subscriber_state: row.claim_state,
      result_packet:
        row.canonical_json === null
          ? null
          : candidateDeepFreeze(JSON.parse(row.canonical_json)),
    });
  }

  cancelCandidateHead(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "cancelWhenUnobserved",
      ],
      undefined,
      "candidate head cancellation request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const publicId = requireCostText(captured.jobId, "jobId", 35);
    if (typeof captured.cancelWhenUnobserved !== "boolean") {
      throw new TypeError("cancelWhenUnobserved must be a boolean");
    }
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const head = this.database
        .prepare(
          `SELECT claim.head_run_id,claim.claim_state,run.run_state
           FROM head_claims AS claim
           JOIN head_runs AS run
             ON run.head_run_id=claim.head_run_id
            AND run.project_id=claim.project_id
           WHERE claim.public_id=? AND claim.origin_id=? AND claim.project_id=?`,
        )
        .get(publicId, originId, projectId);
      if (head === undefined) {
        throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
      }
      if (!["QUEUED", "RUNNING"].includes(head.run_state)) {
        throw stateError("JOB_TERMINAL", "job is terminal");
      }
      const now = requireNow(this.now());
      const changed = this.database
        .prepare(
          `UPDATE head_claims
           SET claim_state='DETACHED',updated_at_ms=?
           WHERE public_id=? AND origin_id=? AND project_id=?
             AND claim_state='ATTACHED'`,
        )
        .run(now, publicId, originId, projectId);
      const remaining = this.database
        .prepare(
          `SELECT COUNT(*) AS count
           FROM head_claims
           WHERE head_run_id=? AND claim_state='ATTACHED'`,
        )
        .get(head.head_run_id).count;
      let producerCancelled = false;
      if (remaining === 0 && captured.cancelWhenUnobserved) {
        const updated = this.database
          .prepare(
            `UPDATE head_runs
             SET run_state='CANCELED',updated_at_ms=?
             WHERE head_run_id=? AND project_id=?
               AND run_state IN ('QUEUED','RUNNING')`,
          )
          .run(now, head.head_run_id, projectId);
        if (updated.changes !== 1) {
          throw stateError("JOB_TERMINAL", "job is terminal");
        }
        const publication = this.publishCandidateHeadResult({
          projectId,
          headRunId: head.head_run_id,
          packet: {
            schema_version: 1,
            result_protocol: 3,
            status: "BLOCKED",
            execution_status: "CANCELLED",
            evidence_verdict: "UNRESOLVED",
            cache_hit: false,
            summary:
              "The shared Sol head was cancelled after its final subscriber detached.",
            positive_findings: [],
            negative_findings: [
              "No authorized subscriber remained for the shared Sol head.",
            ],
            residual_risks: [
              "Cancelled head work has no accepted evidence result.",
            ],
            recommended_next_action:
              "Submit a new bounded route plan if the head work is still required.",
            scientific_uncertainty: false,
            architecture_uncertainty: false,
            scope_deviation: false,
          },
        });
        if (
          this.getCandidateStoreSchemaVersion() ===
          CANDIDATE_STORE_SCHEMA_VERSION
        ) {
          const producerUpdate = this.database
            .prepare(
              `UPDATE head_producer_attempts
               SET producer_state='CANCELED',terminal_result_hash=?,
                   finished_at_ms=?,updated_at_ms=?
               WHERE project_id=? AND head_run_id=?
                 AND producer_state IN ('QUEUED','CLAIMED','RUNNING')`,
            )
            .run(
              publication.packetHash,
              now,
              now,
              projectId,
              head.head_run_id,
            );
          if (producerUpdate.changes !== 1) {
            throw stateError(
              "HEAD_PRODUCER_STATE_CONFLICT",
              "candidate head cancellation lost its producer-state race",
            );
          }
        }
        producerCancelled = true;
      }
      if (ownsTransaction) this.database.exec("COMMIT");
      return Object.freeze({
        schema_version: 1,
        job_id: publicId,
        detached: changed.changes === 1,
        remaining_subscribers: remaining,
        producer_cancelled: producerCancelled,
        subscriber_state: producerCancelled ? "TERMINAL" : "DETACHED",
        status: producerCancelled
          ? "BLOCKED"
          : head.run_state === "QUEUED"
            ? "QUEUED"
            : "RUNNING",
        execution_status: producerCancelled ? "CANCELLED" : "INCOMPLETE",
      });
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  getCandidateHeadMetrics(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId"],
      undefined,
      "candidate head metrics request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    this.#requireCandidateOriginMembership(originId, projectId);
    const row = this.database
      .prepare(
        `SELECT
           COUNT(*) AS total_jobs,
           COALESCE(SUM(CASE WHEN run.run_state='QUEUED' THEN 1 ELSE 0 END),0)
             AS queued_jobs,
           COALESCE(SUM(CASE WHEN run.run_state='RUNNING' THEN 1 ELSE 0 END),0)
             AS running_jobs,
           COALESCE(SUM(CASE
             WHEN run.run_state IN ('SUCCEEDED','FAILED','CANCELED','QUARANTINED')
             THEN 1 ELSE 0 END),0) AS terminal_jobs,
           COALESCE(SUM(CASE WHEN packet.cache_hit=1 THEN 1 ELSE 0 END),0)
             AS cache_hits
         FROM head_claims AS claim
         JOIN head_runs AS run
           ON run.head_run_id=claim.head_run_id
          AND run.project_id=claim.project_id
         LEFT JOIN result_subjects AS subject
           ON subject.head_run_id=run.head_run_id
          AND subject.subject_state='NORMALIZED'
         LEFT JOIN result_packets AS packet
           ON packet.packet_hash=subject.accepted_packet_hash
         WHERE claim.origin_id=? AND claim.project_id=?`,
      )
      .get(originId, projectId);
    const costs = this.database
      .prepare(
        `WITH transmissions AS (
           SELECT DISTINCT transmission.transmission_id,transmission.state,
                  transmission.reserved_nano_usd,transmission.actual_nano_usd
           FROM head_claims AS claim
           JOIN provider_transmissions AS transmission
             ON transmission.job_id=claim.public_id
            AND transmission.origin_id=claim.origin_id
            AND transmission.project_id=claim.project_id
           WHERE claim.origin_id=? AND claim.project_id=?
         )
         SELECT
           COUNT(*) AS provider_transmissions,
           COALESCE(SUM(CASE WHEN state='RECONCILED'
             THEN actual_nano_usd ELSE 0 END),0) AS spent_nano_usd,
           COALESCE(SUM(CASE
             WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
             THEN reserved_nano_usd ELSE 0 END),0) AS reserved_nano_usd,
           COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
             AS unknown_transmissions
         FROM transmissions`,
      )
      .get(originId, projectId);
    return Object.freeze({
      schema_version: 1,
      total_jobs: row.total_jobs,
      queued_jobs: row.queued_jobs,
      running_jobs: row.running_jobs,
      terminal_jobs: row.terminal_jobs,
      cache_hits: row.cache_hits,
      provider_transmissions: costs.provider_transmissions,
      spent_nano_usd: costs.spent_nano_usd,
      reserved_nano_usd: costs.reserved_nano_usd,
      unknown_transmissions: costs.unknown_transmissions,
    });
  }

  getCandidateBatchStatus(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "batchId"],
      undefined,
      "candidate batch status request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const publicId = requireCostText(captured.batchId, "batchId", 36);
    const batch = this.database
      .prepare(
        `SELECT claim.batch_run_id,claim.claim_state,run.node_count,
                run.requested_concurrency
         FROM batch_claims AS claim
         JOIN batch_runs AS run
           ON run.batch_run_id=claim.batch_run_id
          AND run.project_id=claim.project_id
         WHERE claim.public_id=? AND claim.origin_id=? AND claim.project_id=?`,
      )
      .get(publicId, originId, projectId);
    if (batch === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
    const rows = this.database
      .prepare(
        `SELECT node.node_key,node.node_state,claim_node.worker_public_id,
                packet.public_status,packet.execution_status,
                packet.evidence_verdict,packet.cache_hit,packet.canonical_json
         FROM batch_nodes AS node
         LEFT JOIN batch_claim_nodes AS claim_node
           ON claim_node.batch_run_id=node.batch_run_id
          AND claim_node.node_key=node.node_key
          AND claim_node.batch_public_id=?
          AND claim_node.origin_id=?
          AND claim_node.project_id=?
         LEFT JOIN result_subjects AS subject
           ON subject.worker_binding_id=claim_node.worker_binding_id
          AND subject.subject_state='NORMALIZED'
         LEFT JOIN result_packets AS packet
           ON packet.packet_hash=subject.accepted_packet_hash
         WHERE node.batch_run_id=?
         ORDER BY node.ordinal,node.node_key`,
      )
      .all(
        publicId,
        originId,
        projectId,
        batch.batch_run_id,
      );
    const nodes = rows.map((row) => {
      let identity;
      if (row.canonical_json !== null) {
        identity = {
          status: row.public_status,
          execution_status: row.execution_status,
          evidence_verdict: row.evidence_verdict,
          cache_hit: Boolean(row.cache_hit),
        };
      } else {
        switch (row.node_state) {
          case "WAITING":
          case "QUEUED":
            identity = {
              status: "QUEUED",
              execution_status: "INCOMPLETE",
              evidence_verdict: "UNRESOLVED",
              cache_hit: false,
            };
            break;
          case "RUNNING":
            identity = {
              status: "RUNNING",
              execution_status: "INCOMPLETE",
              evidence_verdict: "UNRESOLVED",
              cache_hit: false,
            };
            break;
          case "FAILED":
            identity = {
              status: "FAIL",
              execution_status: "INCOMPLETE",
              evidence_verdict: "UNRESOLVED",
              cache_hit: false,
            };
            break;
          case "BLOCKED":
            identity = {
              status: "BLOCKED",
              execution_status: "BLOCKED",
              evidence_verdict: "UNRESOLVED",
              cache_hit: false,
            };
            break;
          case "CANCELED":
            identity = {
              status: "BLOCKED",
              execution_status: "CANCELLED",
              evidence_verdict: "UNRESOLVED",
              cache_hit: false,
            };
            break;
          default:
            throw stateError(
              "RESULT_PACKET_MISSING",
              "successful batch node has no public result",
            );
        }
      }
      return Object.freeze({
        node_id: row.node_key,
        ...identity,
        job_id: row.worker_public_id ?? null,
        result_packet:
          row.canonical_json === null
            ? null
            : candidateDeepFreeze(JSON.parse(row.canonical_json)),
      });
    });
    if (nodes.length !== batch.node_count) {
      throw stateError("BATCH_STATE_INVALID", "batch node count is inconsistent");
    }
    const statuses = nodes.map((node) => node.status);
    const allTerminal = statuses.every((status) =>
      CANDIDATE_PUBLIC_TERMINAL_STATUSES.includes(status)
    );
    const status = allTerminal
      ? statuses.every((value) => value === "CACHED")
        ? "CACHED"
        : statuses.every((value) => ["PASS", "CACHED"].includes(value))
          ? "PASS"
          : statuses.includes("BLOCKED")
            ? "BLOCKED"
            : "FAIL"
      : statuses.some((value) => value !== "QUEUED")
        ? "RUNNING"
        : "QUEUED";
    return Object.freeze({
      schema_version: 1,
      batch_id: publicId,
      status,
      node_count: batch.node_count,
      concurrency: batch.requested_concurrency,
      subscriber_state: batch.claim_state,
      nodes: Object.freeze(nodes),
    });
  }

  getCandidateBatchMetrics(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId"],
      undefined,
      "candidate batch metrics request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    this.#requireCandidateOriginMembership(originId, projectId);
    const batches = this.database
      .prepare(
        `SELECT
           COUNT(*) AS total_batches,
           COALESCE(SUM(CASE WHEN run.run_state='QUEUED' THEN 1 ELSE 0 END),0)
             AS queued_batches,
           COALESCE(SUM(CASE WHEN run.run_state='RUNNING' THEN 1 ELSE 0 END),0)
             AS running_batches,
           COALESCE(SUM(CASE
             WHEN run.run_state IN ('SUCCEEDED','FAILED','CANCELED','BLOCKED')
             THEN 1 ELSE 0 END),0) AS terminal_batches
         FROM batch_claims AS claim
         JOIN batch_runs AS run
           ON run.batch_run_id=claim.batch_run_id
          AND run.project_id=claim.project_id
         WHERE claim.origin_id=? AND claim.project_id=?`,
      )
      .get(originId, projectId);
    const nodes = this.database
      .prepare(
        `SELECT
           COUNT(*) AS total_nodes,
           COALESCE(SUM(CASE WHEN node.node_state='WAITING' THEN 1 ELSE 0 END),0)
             AS waiting_nodes,
           COALESCE(SUM(CASE WHEN node.node_state='QUEUED' THEN 1 ELSE 0 END),0)
             AS queued_nodes,
           COALESCE(SUM(CASE WHEN node.node_state='RUNNING' THEN 1 ELSE 0 END),0)
             AS running_nodes,
           COALESCE(SUM(CASE
             WHEN node.node_state IN ('SUCCEEDED','FAILED','BLOCKED','CANCELED')
             THEN 1 ELSE 0 END),0) AS terminal_nodes
         FROM batch_claims AS claim
         JOIN batch_nodes AS node ON node.batch_run_id=claim.batch_run_id
         WHERE claim.origin_id=? AND claim.project_id=?`,
      )
      .get(originId, projectId);
    const costs = this.database
      .prepare(
        `WITH batch_jobs AS (
           SELECT DISTINCT binding.job_id
           FROM batch_claim_nodes AS claim
           JOIN worker_bindings AS binding
             ON binding.binding_id=claim.worker_binding_id
            AND binding.project_id=claim.project_id
           WHERE claim.origin_id=? AND claim.project_id=?
         ),
         transmissions AS (
           SELECT DISTINCT transmission.transmission_id,transmission.state,
                  transmission.reserved_nano_usd,transmission.actual_nano_usd
           FROM provider_transmissions AS transmission
           JOIN batch_jobs AS job ON job.job_id=transmission.job_id
           WHERE transmission.origin_id=? AND transmission.project_id=?
         )
         SELECT
           COUNT(*) AS provider_transmissions,
           COALESCE(SUM(CASE WHEN state='RECONCILED'
             THEN actual_nano_usd ELSE 0 END),0) AS spent_nano_usd,
           COALESCE(SUM(CASE
             WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
             THEN reserved_nano_usd ELSE 0 END),0) AS reserved_nano_usd,
           COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
             AS unknown_transmissions
         FROM transmissions`,
      )
      .get(originId, projectId, originId, projectId);
    return Object.freeze({
      schema_version: 1,
      total_batches: batches.total_batches,
      queued_batches: batches.queued_batches,
      running_batches: batches.running_batches,
      terminal_batches: batches.terminal_batches,
      total_nodes: nodes.total_nodes,
      waiting_nodes: nodes.waiting_nodes,
      queued_nodes: nodes.queued_nodes,
      running_nodes: nodes.running_nodes,
      terminal_nodes: nodes.terminal_nodes,
      provider_transmissions: costs.provider_transmissions,
      spent_nano_usd: costs.spent_nano_usd,
      reserved_nano_usd: costs.reserved_nano_usd,
      unknown_transmissions: costs.unknown_transmissions,
    });
  }

  enqueueCandidateJob(request) {
    this.#requireCandidateSchemaWritable();
    const capturedRequest = captureCandidateDataObject(
      request,
      ["originId", "contract"],
      ["originId", "contract"],
      "candidate enqueue request",
    );
    const originId = capturedRequest.originId;
    const contract = captureCandidateContract(capturedRequest.contract);
    const exactOriginId = requireSafeInteger(
      originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(contract.projectId);
    const originTaskId = `origin:${exactOriginId}`;
    const priority = requireSafeInteger(
      contract.priority === undefined ? 0 : contract.priority,
      "priority must be a finite safe integer",
    );
    const maximumAttempts = requireSafeInteger(
      contract.maximumAttempts === undefined ? 1 : contract.maximumAttempts,
      "maximumAttempts must be a positive safe integer",
      1,
    );
    const exactExecutionFingerprint = candidateSha256(
      canonicalPayloadJson({
        contractHash: contract.contractHash,
        inputFingerprint: contract.inputFingerprint,
        maximumAttempts,
        payload: contract.payload === undefined ? null : contract.payload,
        poolId: contract.poolId,
        priority,
        projectId,
        role: contract.role,
      }),
    );
    const scopedContract = {
      ...contract,
      taskId: originTaskId,
      idempotencyKey: `candidate-exact:${exactExecutionFingerprint}`,
      priority,
      maximumAttempts,
    };
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const registered = this.database
        .prepare(
          `SELECT 1
           FROM origins
           WHERE origin_id=? AND project_id=?`,
        )
        .get(exactOriginId, projectId);
      if (registered === undefined) {
        throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
      }

      const existing = this.#getLatestRowByIdentity(
        projectId,
        scopedContract.idempotencyKey,
      );
      if (existing !== undefined) {
        const ownership = this.database
          .prepare(
            `SELECT 1
             FROM logical_job_origins
             WHERE job_id=? AND origin_id=? AND project_id=?`,
          )
          .get(existing.job_id, exactOriginId, projectId);
        if (ownership !== undefined) {
          if (ownsTransaction) this.database.exec("COMMIT");
          return publicGeneration(existing);
        }
      }

      const admission = this.database
        .prepare(
          `WITH latest_generations AS (
             SELECT generation.job_id,generation.state
             FROM logical_jobs AS job
             JOIN generations AS generation ON generation.job_id=job.job_id
             WHERE job.project_id=?
               AND NOT EXISTS (
                 SELECT 1
                 FROM generations AS newer
                 WHERE newer.job_id=generation.job_id
                   AND newer.generation>generation.generation
               )
           ),
           latest_owners AS (
             SELECT ownership.origin_id,latest.state
             FROM logical_job_origins AS ownership
             JOIN latest_generations AS latest ON latest.job_id=ownership.job_id
             WHERE ownership.project_id=?
           )
           SELECT
             (SELECT COUNT(*) FROM latest_generations WHERE state='QUEUED')
               AS global_queued,
             COUNT(DISTINCT CASE
               WHEN state IN ('QUEUED','RUNNING','VALIDATING') THEN origin_id
               ELSE NULL END) AS active_origins,
             COALESCE(MAX(CASE
                WHEN origin_id=?
                  AND state IN ('QUEUED','RUNNING','VALIDATING')
                THEN 1 ELSE 0 END),0) AS requesting_origin_active
           FROM latest_owners`,
        )
        .get(projectId, projectId, exactOriginId);
      if (existing === undefined && admission.global_queued >= 100) {
        throw stateError("GLOBAL_QUEUE_LIMIT", "project queue limit reached");
      }
      if (
        admission.requesting_origin_active === 0 &&
        admission.active_origins >= 5
      ) {
        throw stateError("ACTIVE_ORIGIN_LIMIT", "active origin limit reached");
      }

      const queued = this.database
        .prepare(
          `SELECT COUNT(*) AS count
           FROM logical_job_origins AS ownership
           JOIN generations AS generation
             ON generation.job_id=ownership.job_id
           WHERE ownership.origin_id=?
             AND ownership.project_id=?
             AND generation.state='QUEUED'
             AND NOT EXISTS (
               SELECT 1
               FROM generations AS newer
               WHERE newer.job_id=generation.job_id
                 AND newer.generation>generation.generation
             )`,
        )
        .get(exactOriginId, projectId).count;
      if (queued >= 20) {
        throw stateError("ORIGIN_QUEUE_LIMIT", "origin queue limit reached");
      }

      if (existing !== undefined) {
        this.database
          .prepare(
            `INSERT INTO logical_job_origins
               (job_id,origin_id,project_id,created_at_ms)
             VALUES (?,?,?,?)`,
          )
          .run(
            existing.job_id,
            exactOriginId,
            projectId,
            requireNow(this.now()),
          );
        if (ownsTransaction) this.database.exec("COMMIT");
        return publicGeneration(existing);
      }

      const generation = this.enqueue(scopedContract);
      this.database
        .prepare(
          `INSERT INTO logical_job_origins
             (job_id,origin_id,project_id,created_at_ms)
           VALUES (?,?,?,?)`,
        )
        .run(
          generation.jobId,
          exactOriginId,
          projectId,
          generation.createdAtMs,
        );
      if (ownsTransaction) this.database.exec("COMMIT");
      return generation;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  getCandidateGeneration(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "jobId", "generation"],
      ["originId", "projectId", "jobId", "generation"],
      "candidate generation request",
    );
    const exactOriginId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const exactProjectId = requireCostProjectId(captured.projectId);
    const exactJobId = requireBoundedString(
      captured.jobId,
      "jobId must be a bounded nonblank string",
      256,
    );
    const exactGeneration = requireSafeInteger(
      captured.generation,
      "generation must be a positive safe integer",
      1,
    );
    const row = this.database
      .prepare(
        `${GENERATION_SELECT}
         JOIN logical_job_origins AS ownership
           ON ownership.job_id=g.job_id
         WHERE ownership.origin_id=?
           AND ownership.project_id=?
           AND g.job_id=?
           AND g.generation=?`,
      )
      .get(exactOriginId, exactProjectId, exactJobId, exactGeneration);
    if (row === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
    return publicGeneration(row);
  }

  listCandidateEvents(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "jobId", "afterSequence", "limit"],
      ["originId", "projectId", "jobId"],
      "candidate event request",
    );
    const exactOriginId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const exactProjectId = requireCostProjectId(captured.projectId);
    const exactJobId = requireBoundedString(
      captured.jobId,
      "jobId must be a bounded nonblank string",
      256,
    );
    this.#requireCandidateJobOwnership(
      exactOriginId,
      exactProjectId,
      exactJobId,
    );
    return this.listEvents(
      exactJobId,
      captured.afterSequence ?? 0,
      captured.limit ?? 1000,
    );
  }

  cancelCandidateGeneration(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId", "jobId", "generation", "actor", "reason"],
      ["originId", "projectId", "jobId", "generation", "actor", "reason"],
      "candidate cancellation request",
    );
    const exactOriginId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const exactProjectId = requireCostProjectId(captured.projectId);
    const exactJobId = requireBoundedString(
      captured.jobId,
      "jobId must be a bounded nonblank string",
      256,
    );
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      this.#requireCandidateJobOwnership(
        exactOriginId,
        exactProjectId,
        exactJobId,
      );
      const ownerCount = this.database
        .prepare(
          `SELECT COUNT(*) AS count
           FROM logical_job_origins
           WHERE job_id=? AND project_id=?`,
        )
        .get(exactJobId, exactProjectId).count;
      if (ownerCount > 1) {
        throw stateError(
          "INVALID_CANCEL_STATE",
          "shared work cannot be canceled by one subscriber",
        );
      }
      const canceled = this.cancelGeneration({
        jobId: exactJobId,
        generation: captured.generation,
        actor: captured.actor,
        reason: captured.reason,
      });
      if (ownsTransaction) this.database.exec("COMMIT");
      return canceled;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  getCandidateOriginMetrics(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId"],
      ["originId", "projectId"],
      "candidate origin metrics request",
    );
    const exactOriginId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const exactProjectId = requireCostProjectId(captured.projectId);
    const registered = this.database
      .prepare(
        `SELECT 1 FROM origins WHERE origin_id=? AND project_id=?`,
      )
      .get(exactOriginId, exactProjectId);
    if (registered === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
    const jobs = this.database
      .prepare(
         `WITH latest AS (
           SELECT DISTINCT generation.job_id,generation.state
           FROM logical_job_origins AS ownership
           JOIN generations AS generation
             ON generation.job_id=ownership.job_id
           WHERE ownership.origin_id=?
             AND ownership.project_id=?
             AND NOT EXISTS (
               SELECT 1
               FROM generations AS newer
               WHERE newer.job_id=generation.job_id
                 AND newer.generation>generation.generation
             )
         )
         SELECT
           COUNT(*) AS total_jobs,
           COALESCE(SUM(CASE WHEN state='QUEUED' THEN 1 ELSE 0 END),0)
             AS queued_jobs,
           COALESCE(SUM(CASE WHEN state='RUNNING' THEN 1 ELSE 0 END),0)
             AS running_jobs,
           COALESCE(SUM(CASE WHEN state='VALIDATING' THEN 1 ELSE 0 END),0)
             AS validating_jobs,
           COALESCE(SUM(CASE
             WHEN state IN ('SUCCEEDED','FAILED','CANCELED','QUARANTINED')
             THEN 1 ELSE 0 END),0) AS terminal_jobs
         FROM latest`,
      )
      .get(exactOriginId, exactProjectId);
    const costs = this.#candidateTransmissionCostWritable
      ? this.database
          .prepare(
            `SELECT
               COUNT(*) AS reservation_count,
               COALESCE(SUM(CASE
                 WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
                 THEN reserved_nano_usd ELSE 0 END),0)
                 AS open_reserved_nano_usd,
               COALESCE(SUM(CASE
                 WHEN state='RECONCILED' THEN actual_nano_usd ELSE 0 END),0)
                 AS actual_nano_usd,
               COALESCE(SUM(CASE
                 WHEN state='RECONCILED' THEN input_tokens ELSE 0 END),0)
                 AS input_tokens,
               COALESCE(SUM(CASE
                 WHEN state='RECONCILED' THEN cached_input_tokens ELSE 0 END),0)
                 AS cached_input_tokens,
               COALESCE(SUM(CASE
                 WHEN state='RECONCILED' THEN output_tokens ELSE 0 END),0)
                 AS output_tokens,
               COALESCE(SUM(CASE
                 WHEN state='RECONCILED' THEN total_tokens ELSE 0 END),0)
                 AS total_tokens,
               COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
                 AS unknown_cost_reservations
             FROM provider_transmissions
             WHERE origin_id=? AND project_id=?`,
          )
          .get(exactOriginId, exactProjectId)
      : this.database
          .prepare(
            `SELECT
               COUNT(*) AS reservation_count,
               COALESCE(SUM(CASE WHEN state='OPEN' THEN reserved_nano_usd ELSE 0 END),0)
                 AS open_reserved_nano_usd,
               COALESCE(SUM(COALESCE(actual_nano_usd,0)),0) AS actual_nano_usd,
               COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
                 AS unknown_cost_reservations
             FROM cost_reservations
             WHERE origin_id=? AND project_id=?`,
          )
          .get(exactOriginId, exactProjectId);
    return Object.freeze({
      originId: exactOriginId,
      totalJobs: jobs.total_jobs,
      queuedJobs: jobs.queued_jobs,
      runningJobs: jobs.running_jobs,
      validatingJobs: jobs.validating_jobs,
      terminalJobs: jobs.terminal_jobs,
      costReservationCount: costs.reservation_count,
      openReservedNanoUsd: costs.open_reserved_nano_usd,
      actualNanoUsd: costs.actual_nano_usd,
      inputTokens: costs.input_tokens ?? 0,
      cachedInputTokens: costs.cached_input_tokens ?? 0,
      outputTokens: costs.output_tokens ?? 0,
      totalTokens: costs.total_tokens ?? 0,
      unknownCostReservations: costs.unknown_cost_reservations,
    });
  }

  getCandidateProjectMetrics(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      ["originId", "projectId"],
      ["originId", "projectId"],
      "candidate project metrics request",
    );
    const exactOriginId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const exactProjectId = requireCostProjectId(captured.projectId);
    const membership = this.database
      .prepare(
        `SELECT 1 FROM origins WHERE origin_id=? AND project_id=?`,
      )
      .get(exactOriginId, exactProjectId);
    if (membership === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
    const jobs = this.database
      .prepare(
         `WITH latest AS (
           SELECT DISTINCT generation.job_id,generation.state
           FROM logical_job_origins AS ownership
           JOIN generations AS generation
             ON generation.job_id=ownership.job_id
           WHERE ownership.project_id=?
             AND NOT EXISTS (
               SELECT 1
               FROM generations AS newer
               WHERE newer.job_id=generation.job_id
                 AND newer.generation>generation.generation
             )
         )
         SELECT
           COUNT(*) AS total_jobs,
           COALESCE(SUM(CASE WHEN state='QUEUED' THEN 1 ELSE 0 END),0)
             AS queued_jobs,
           COALESCE(SUM(CASE WHEN state='RUNNING' THEN 1 ELSE 0 END),0)
             AS running_jobs,
           COALESCE(SUM(CASE WHEN state='VALIDATING' THEN 1 ELSE 0 END),0)
             AS validating_jobs,
           COALESCE(SUM(CASE
             WHEN state IN ('SUCCEEDED','FAILED','CANCELED','QUARANTINED')
             THEN 1 ELSE 0 END),0) AS terminal_jobs
         FROM latest`,
      )
      .get(exactProjectId);
    const aggregate = this.database
      .prepare(
        `SELECT
           (SELECT COUNT(*) FROM origins WHERE project_id=?) AS origin_count,
           COALESCE((
             SELECT ceiling_nano_usd FROM cost_budgets WHERE project_id=?
           ),0) AS ceiling_nano_usd,
           COALESCE((
             SELECT spent_nano_usd FROM cost_budgets WHERE project_id=?
           ),0) AS spent_nano_usd,
           COALESCE((
             SELECT reserved_nano_usd FROM cost_budgets WHERE project_id=?
           ),0) AS reserved_nano_usd,
           (SELECT COUNT(*) FROM cost_reservations WHERE project_id=?)
             AS reservation_count,
           (SELECT COUNT(*) FROM cost_reservations
             WHERE project_id=? AND state='UNKNOWN')
             AS unknown_cost_reservations`,
      )
      .get(
        exactProjectId,
        exactProjectId,
        exactProjectId,
        exactProjectId,
        exactProjectId,
        exactProjectId,
      );
    return Object.freeze({
      originCount: aggregate.origin_count,
      totalJobs: jobs.total_jobs,
      queuedJobs: jobs.queued_jobs,
      runningJobs: jobs.running_jobs,
      validatingJobs: jobs.validating_jobs,
      terminalJobs: jobs.terminal_jobs,
      ceilingNanoUsd: aggregate.ceiling_nano_usd,
      spentNanoUsd: aggregate.spent_nano_usd,
      reservedNanoUsd: aggregate.reserved_nano_usd,
      costReservationCount: aggregate.reservation_count,
      unknownCostReservations: aggregate.unknown_cost_reservations,
    });
  }

  auditCandidateCopiedStateMigration(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "projectId",
        "copyRoot",
        "workspaceRoot",
        "candidateProtocolVersion",
        "staleBeforeMs",
        "sources",
      ],
      [
        "projectId",
        "copyRoot",
        "workspaceRoot",
        "candidateProtocolVersion",
        "staleBeforeMs",
        "sources",
      ],
      "candidate copied-state migration request",
    );
    if (
      typeof captured.projectId !== "string" ||
      !/^[A-Za-z0-9._:-]{1,256}$/.test(captured.projectId) ||
      [".", ".."].includes(captured.projectId) ||
      typeof captured.copyRoot !== "string" ||
      !path.isAbsolute(captured.copyRoot) ||
      typeof captured.workspaceRoot !== "string" ||
      !path.isAbsolute(captured.workspaceRoot) ||
      captured.copyRoot.includes("\0") ||
      captured.workspaceRoot.includes("\0")
    ) {
      throw new TypeError("invalid candidate copied-state migration request");
    }
    const candidateProtocolVersion = requireSafeInteger(
      captured.candidateProtocolVersion,
      "candidate protocol version must be a positive safe integer",
      1,
    );
    const staleBeforeMs = requireSafeInteger(
      captured.staleBeforeMs,
      "stale cutoff must be a nonnegative safe integer",
      0,
    );
    const copyRootStats = lstatSync(captured.copyRoot);
    const workspaceStats = lstatSync(captured.workspaceRoot);
    if (
      !copyRootStats.isDirectory() ||
      copyRootStats.isSymbolicLink() ||
      !workspaceStats.isDirectory() ||
      workspaceStats.isSymbolicLink()
    ) {
      throw candidateMigrationError(
        "MIGRATION_COPY_ROOT_ESCAPE",
        "migration roots must be isolated directories",
      );
    }
    const canonicalCopyRoot = realpathSync.native(captured.copyRoot);
    const canonicalWorkspace = realpathSync.native(captured.workspaceRoot);
    const workspaceIdentityHash =
      candidateMigrationWorkspaceIdentity(canonicalWorkspace);
    const sources = captureCandidateMigrationSources(
      captured.sources,
      canonicalCopyRoot,
      { candidateProtocolVersion, staleBeforeMs },
    );
    const collisions = resolveCandidateMigrationCollisions(
      sources,
      candidateProtocolVersion,
    );
    const migrationFingerprint = candidateSha256(
      canonicalPayloadJson({
        candidateProtocolVersion,
        projectId: captured.projectId,
        sources: sources.map((source) => ({
          namespace: source.namespace,
          sourceHash: source.sourceHash,
          sourceKind: source.sourceKind,
        })),
        staleBeforeMs,
        workspaceIdentityHash,
      }),
    );
    const runId = `migration-${migrationFingerprint.slice(0, 32)}`;

    this.database.exec("BEGIN IMMEDIATE");
    try {
      if (candidateMigrationOperationalRowCount(this.database) !== 0) {
        throw candidateMigrationError(
          "MIGRATION_TARGET_NOT_EMPTY",
          "copied-state migration requires a fresh audit-only target",
        );
      }
      for (const source of sources) {
        const attested = scanCandidateMigrationSource(source.canonicalSourceRoot, {
          candidateProtocolVersion,
          staleBeforeMs,
        });
        if (
          attested.sourceHash !== source.sourceHash ||
          attested.entries.length !== source.entries.length
        ) {
          throw candidateMigrationError(
            "MIGRATION_SOURCE_CHANGED",
            "copied migration source changed before commit",
          );
        }
      }
      const existing = this.database
        .prepare(
          `SELECT run_id,project_id,canonical_workspace,workspace_identity_hash,
                  candidate_protocol_version,stale_before_ms,run_state,created_at_ms
           FROM legacy_migration_runs
           WHERE run_id=?`,
        )
        .get(runId);
      if (existing !== undefined) {
        if (
          existing.project_id !== captured.projectId ||
          existing.canonical_workspace !== canonicalWorkspace ||
          existing.workspace_identity_hash !== workspaceIdentityHash ||
          existing.candidate_protocol_version !== candidateProtocolVersion ||
          existing.stale_before_ms !== staleBeforeMs
        ) {
          throw candidateMigrationError(
            "MIGRATION_IDENTITY_COLLISION",
            "copied-state migration identity collision",
          );
        }
        const existingSources = this.database
          .prepare(
            `SELECT source_namespace,source_kind,source_hash,entry_count
             FROM legacy_migration_sources
             WHERE run_id=?
             ORDER BY source_namespace`,
          )
          .all(runId);
        if (
          existingSources.length !== sources.length ||
          existingSources.some((source, index) => {
            const expected = sources[index];
            return (
              source.source_namespace !== expected.namespace ||
              source.source_kind !== expected.sourceKind ||
              source.source_hash !== expected.sourceHash ||
              source.entry_count !== expected.entries.length
            );
          })
        ) {
          throw candidateMigrationError(
            "MIGRATION_SOURCE_CHANGED",
            "copied-state migration replay source changed",
          );
        }
        this.database.exec("COMMIT");
        return publicCandidateMigrationOutcome(this.database, existing);
      }

      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO projects(project_id,created_at_ms)
           VALUES (?,?)
           ON CONFLICT(project_id) DO NOTHING`,
        )
        .run(captured.projectId, now);
      this.database
        .prepare(
          `INSERT INTO legacy_migration_runs
             (run_id,project_id,canonical_workspace,workspace_identity_hash,
              candidate_protocol_version,stale_before_ms,run_state,created_at_ms)
           VALUES (?,?,?,?,?,?,'MIGRATING',?)`,
        )
        .run(
          runId,
          captured.projectId,
          canonicalWorkspace,
          workspaceIdentityHash,
          candidateProtocolVersion,
          staleBeforeMs,
          now,
        );
      const insertSource = this.database.prepare(
        `INSERT INTO legacy_migration_sources
           (run_id,source_namespace,source_kind,source_hash,entry_count)
         VALUES (?,?,?,?,?)`,
      );
      const insertEntry = this.database.prepare(
        `INSERT INTO legacy_migration_entries
           (run_id,source_namespace,entry_kind,logical_identity_hash,
            relative_path_hash,content_hash,byte_count,protocol_version,
            terminal_state,disposition,reason_code)
         VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
      );
      for (const source of sources) {
        insertSource.run(
          runId,
          source.namespace,
          source.sourceKind,
          source.sourceHash,
          source.entries.length,
        );
        for (const entry of source.entries) {
          insertEntry.run(
            runId,
            source.namespace,
            entry.entryKind,
            entry.logicalIdentityHash,
            entry.relativePathHash,
            entry.contentHash,
            entry.byteCount,
            entry.protocolVersion,
            entry.terminalState,
            entry.disposition,
            entry.reasonCode,
          );
        }
      }
      const insertCollision = this.database.prepare(
        `INSERT INTO legacy_migration_collisions
           (run_id,collision_kind,logical_identity_hash,source_count,
            disposition,reason_code)
         VALUES (?,?,?,?,?,?)`,
      );
      for (const collision of collisions) {
        insertCollision.run(
          runId,
          collision.collisionKind,
          collision.logicalIdentityHash,
          collision.sourceCount,
          collision.disposition,
          collision.reasonCode,
        );
      }
      const unresolved = collisions.filter(
        (collision) => collision.disposition === "UNRESOLVED",
      ).length;
      this.database
        .prepare(
          `UPDATE legacy_migration_runs
           SET run_state=?
           WHERE run_id=? AND run_state='MIGRATING'`,
        )
        .run(unresolved === 0 ? "READY" : "BLOCKED", runId);
      const runRow = this.database
        .prepare(
          `SELECT run_id,project_id,canonical_workspace,workspace_identity_hash,
                  candidate_protocol_version,stale_before_ms,run_state,created_at_ms
           FROM legacy_migration_runs
           WHERE run_id=?`,
        )
        .get(runId);
      this.database.exec("COMMIT");
      return publicCandidateMigrationOutcome(this.database, runRow);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  getCandidateMigrationReadiness(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "runId", "sourceHashes"],
      ["projectId", "runId", "sourceHashes"],
      "candidate migration readiness request",
    );
    if (
      typeof captured.projectId !== "string" ||
      !/^[A-Za-z0-9._:-]{1,256}$/.test(captured.projectId) ||
      typeof captured.runId !== "string" ||
      !/^migration-[0-9a-f]{32}$/.test(captured.runId)
    ) {
      throw new TypeError("invalid candidate migration readiness request");
    }
    const sourceHashes = captureCandidateMigrationHashMap(captured.sourceHashes);
    const run = this.database
      .prepare(
        `SELECT run_id,run_state
         FROM legacy_migration_runs
         WHERE run_id=? AND project_id=?`,
      )
      .get(captured.runId, captured.projectId);
    if (run === undefined) {
      throw stateError("MIGRATION_RUN_NOT_FOUND", "migration run not found");
    }
    const sources = this.database
      .prepare(
        `SELECT source_namespace,source_hash
         FROM legacy_migration_sources
         WHERE run_id=?
         ORDER BY source_namespace`,
      )
      .all(captured.runId);
    const sourceHashesMatch =
      sources.length === sourceHashes.size &&
      sources.every(
        (source) =>
          sourceHashes.get(source.source_namespace) === source.source_hash,
      );
    const collisions = this.database
      .prepare(
        `SELECT
           COUNT(*) AS collision_count,
           SUM(CASE WHEN disposition='UNRESOLVED' THEN 1 ELSE 0 END)
             AS unresolved_count
         FROM legacy_migration_collisions
         WHERE run_id=?`,
      )
      .get(captured.runId);
    const operational = candidateMigrationOperationalRowCount(this.database);
    const foreignKeysGreen =
      this.database.prepare("PRAGMA foreign_key_check").all().length === 0;
    const integrityRows = this.database.prepare("PRAGMA integrity_check").all();
    const integrityGreen =
      integrityRows.length === 1 && Object.values(integrityRows[0])[0] === "ok";
    const unresolvedCollisionCount = collisions.unresolved_count ?? 0;
    return Object.freeze({
      collisionCount: collisions.collision_count,
      runId: captured.runId,
      sourceCount: sources.length,
      state:
        run.run_state === "READY" &&
        sourceHashesMatch &&
        unresolvedCollisionCount === 0 &&
        operational === 0 &&
        foreignKeysGreen &&
        integrityGreen
          ? "READY"
          : "BLOCKED",
      unresolvedCollisionCount,
    });
  }

  issueCandidateMigrationAttestation(request) {
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "runId", "sourceHashes"],
      ["projectId", "runId", "sourceHashes"],
      "candidate migration attestation request",
    );
    const readiness = this.getCandidateMigrationReadiness(captured);
    if (readiness.state !== "READY") {
      throw stateError("MIGRATION_UNATTESTED", "migration readiness is BLOCKED");
    }
    return candidateMigrationAttestation(
      this.database,
      captured.projectId,
      captured.runId,
    );
  }

  upgradeCandidateMigrationAttestation(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "previousAttestation",
        "sourceStoreSchemaVersion",
        "targetStoreSchemaVersion",
      ],
      [
        "previousAttestation",
        "sourceStoreSchemaVersion",
        "targetStoreSchemaVersion",
      ],
      "candidate migration attestation upgrade request",
    );
    const sourceStoreSchemaVersion = requireSafeInteger(
      captured.sourceStoreSchemaVersion,
      "sourceStoreSchemaVersion must be a positive safe integer",
      1,
    );
    const targetStoreSchemaVersion = requireSafeInteger(
      captured.targetStoreSchemaVersion,
      "targetStoreSchemaVersion must be a positive safe integer",
      1,
    );
    if (
      sourceStoreSchemaVersion !== CANDIDATE_STORE_SCHEMA_V4_VERSION ||
      targetStoreSchemaVersion !== CANDIDATE_STORE_SCHEMA_VERSION ||
      this.getCandidateStoreSchemaVersion() !== targetStoreSchemaVersion
    ) {
      throw stateError(
        "MIGRATION_ATTESTATION_UPGRADE_REJECTED",
        "migration attestation upgrade does not match the supported schema transition",
      );
    }
    const previous = captureCandidateMigrationAttestation(
      captured.previousAttestation,
    );
    const expectedPrevious = candidateMigrationAttestation(
      this.database,
      previous.projectId,
      previous.runId,
      sourceStoreSchemaVersion,
    );
    if (
      previous.attestationId !== expectedPrevious.attestationId ||
      previous.sourceSetHash !== expectedPrevious.sourceSetHash ||
      previous.unresolvedCollisions !==
        expectedPrevious.unresolvedCollisions ||
      previous.operationalImports !== expectedPrevious.operationalImports
    ) {
      throw stateError(
        "MIGRATION_ATTESTATION_MISMATCH",
        "prior migration attestation does not match the durable source audit",
      );
    }
    return candidateMigrationAttestation(
      this.database,
      previous.projectId,
      previous.runId,
      targetStoreSchemaVersion,
    );
  }

  verifyCandidateMigrationAttestation(value) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateMigrationAttestation(value);
    const expected = candidateMigrationAttestation(
      this.database,
      captured.projectId,
      captured.runId,
    );
    if (
      captured.attestationId !== expected.attestationId ||
      captured.sourceSetHash !== expected.sourceSetHash ||
      captured.unresolvedCollisions !== expected.unresolvedCollisions ||
      captured.operationalImports !== expected.operationalImports
    ) {
      throw stateError(
        "MIGRATION_ATTESTATION_MISMATCH",
        "migration attestation does not match durable state",
      );
    }
    return expected;
  }

  acquireCandidateWriterAdmission(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "worktreeRoot",
        "outputPaths",
      ],
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "worktreeRoot",
        "outputPaths",
      ],
      "candidate writer admission request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const jobId = requireBoundedString(
      captured.jobId,
      "jobId must be a bounded nonblank string",
      256,
    );
    const generation = requireSafeInteger(
      captured.generation,
      "generation must be a positive safe integer",
      1,
    );
    const leaseEpoch = requireSafeInteger(
      captured.leaseEpoch,
      "leaseEpoch must be a positive safe integer",
      1,
    );
    let scope = canonicalizeCandidateWriterScope(
      captured.worktreeRoot,
      captured.outputPaths,
    );

    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const attestedScope = canonicalizeCandidateWriterScope(
        captured.worktreeRoot,
        captured.outputPaths,
      );
      if (
        filesystemPathIdentity(attestedScope.canonicalWorktree) !==
          filesystemPathIdentity(scope.canonicalWorktree) ||
        attestedScope.worktreeIdentity !== scope.worktreeIdentity ||
        attestedScope.canonicalOutputPaths.length !==
          scope.canonicalOutputPaths.length ||
        attestedScope.canonicalOutputPaths.some(
          (outputPath, index) =>
            filesystemPathIdentity(outputPath) !==
              filesystemPathIdentity(scope.canonicalOutputPaths[index]) ||
            attestedScope.canonicalOutputs[index].filesystemIdentity !==
              scope.canonicalOutputs[index].filesystemIdentity,
        )
      ) {
        throw stateError("INVALID_WRITER_SCOPE", "invalid writer scope");
      }
      scope = attestedScope;

      const lease = this.database
        .prepare(
          `SELECT lease.expires_at_ms,generation_row.role,generation_row.state
           FROM leases AS lease
           JOIN generations AS generation_row
             ON generation_row.job_id=lease.job_id
            AND generation_row.generation=lease.generation
           JOIN logical_job_origins AS ownership
             ON ownership.job_id=lease.job_id
           WHERE ownership.origin_id=?
             AND ownership.project_id=?
             AND lease.job_id=?
             AND lease.generation=?
             AND lease.epoch=?`,
        )
        .get(originId, projectId, jobId, generation, leaseEpoch);
      if (
        lease === undefined ||
        lease.role !== "WRITER" ||
        lease.state !== "RUNNING" ||
        lease.expires_at_ms < now
      ) {
        throw stateError("STALE_WRITER_LEASE", "writer lease is not current");
      }

      const existing = this.database
        .prepare("SELECT * FROM writer_locks WHERE project_id=?")
        .get(projectId);
      if (existing !== undefined) {
        const existingOutputs = this.database
          .prepare(
            `SELECT canonical_output_path,filesystem_identity
             FROM writer_lock_outputs
             WHERE project_id=? AND fencing_token=?`,
          )
          .all(projectId, existing.fencing_token)
          .sort((left, right) =>
            filesystemPathIdentity(left.canonical_output_path).localeCompare(
              filesystemPathIdentity(right.canonical_output_path),
            ),
          );
        const exactReplay =
          existing.origin_id === originId &&
          existing.owner_job_id === jobId &&
          existing.owner_generation === generation &&
          existing.owner_lease_epoch === leaseEpoch &&
          filesystemPathIdentity(existing.canonical_worktree) ===
            filesystemPathIdentity(scope.canonicalWorktree) &&
          existing.worktree_identity === scope.worktreeIdentity &&
          existingOutputs.length === scope.canonicalOutputPaths.length &&
          existingOutputs.every(
            (output, index) =>
              filesystemPathIdentity(output.canonical_output_path) ===
                filesystemPathIdentity(scope.canonicalOutputPaths[index]) &&
              output.filesystem_identity ===
                scope.canonicalOutputs[index].filesystemIdentity,
          );
        const oldLease = this.database
          .prepare(
            `SELECT expires_at_ms
             FROM leases
             WHERE job_id=? AND generation=? AND epoch=?`,
          )
          .get(
            existing.owner_job_id,
            existing.owner_generation,
            existing.owner_lease_epoch,
          );
        const oldLeaseIsCurrent =
          oldLease !== undefined && oldLease.expires_at_ms >= now;
        if (exactReplay && oldLeaseIsCurrent) {
          this.database.exec("COMMIT");
          return publicCandidateWriterAdmission(
            existing,
            existingOutputs.map((output) => output.canonical_output_path),
          );
        }
        if (oldLeaseIsCurrent) {
          throw stateError("WRITER_LOCKED", "writer lane is already owned");
        }
      }

      const activeLocks = this.database
        .prepare(
          `SELECT writer.project_id,writer.canonical_worktree,
                  writer.worktree_identity
           FROM writer_locks AS writer
           JOIN leases AS lease
             ON lease.job_id=writer.owner_job_id
            AND lease.generation=writer.owner_generation
            AND lease.epoch=writer.owner_lease_epoch
           WHERE writer.project_id<>?
             AND writer.expires_at_ms>=?
             AND lease.expires_at_ms>=?`,
        )
        .all(projectId, now, now);
      if (
        activeLocks.some(
          (lock) =>
            lock.worktree_identity === scope.worktreeIdentity ||
            candidatePathsOverlap(
              lock.canonical_worktree,
              scope.canonicalWorktree,
            ),
        )
      ) {
        throw stateError("WRITER_SCOPE_CONFLICT", "writer scope overlaps");
      }
      const requestedOutputIdentities = new Set(
        scope.canonicalOutputs.map((output) => output.filesystemIdentity),
      );
      for (const activeLock of activeLocks) {
        const aliases = this.database
          .prepare(
            `SELECT filesystem_identity
             FROM writer_lock_outputs
             WHERE project_id=?`,
          )
          .all(activeLock.project_id);
        if (
          aliases.some((output) =>
            requestedOutputIdentities.has(output.filesystem_identity),
          )
        ) {
          throw stateError("WRITER_SCOPE_CONFLICT", "writer scope overlaps");
        }
      }

      this.database
        .prepare(
          `INSERT INTO writer_fence_counters(project_id,current_fencing_token)
           VALUES (?,0)
           ON CONFLICT(project_id) DO NOTHING`,
        )
        .run(projectId);
      const counterUpdate = this.database
        .prepare(
          `UPDATE writer_fence_counters
           SET current_fencing_token=current_fencing_token+1
           WHERE project_id=?
             AND current_fencing_token<9007199254740991`,
        )
        .run(projectId);
      if (counterUpdate.changes !== 1) {
        throw stateError("WRITER_FENCE_EXHAUSTED", "writer fence is exhausted");
      }
      const fencingToken = this.database
        .prepare(
          `SELECT current_fencing_token
           FROM writer_fence_counters
           WHERE project_id=?`,
        )
        .get(projectId).current_fencing_token;
      if (existing !== undefined) {
        this.database
          .prepare("DELETE FROM writer_locks WHERE project_id=?")
          .run(projectId);
      }
      this.database
        .prepare(
          `INSERT INTO writer_locks
             (project_id,origin_id,owner_job_id,owner_generation,
              owner_lease_epoch,fencing_token,canonical_worktree,
              worktree_identity,acquired_at_ms,expires_at_ms)
           VALUES (?,?,?,?,?,?,?,?,?,?)`,
        )
        .run(
          projectId,
          originId,
          jobId,
          generation,
          leaseEpoch,
          fencingToken,
          scope.canonicalWorktree,
          scope.worktreeIdentity,
          now,
          lease.expires_at_ms,
        );
      const insertOutput = this.database.prepare(
        `INSERT INTO writer_lock_outputs
           (project_id,fencing_token,canonical_output_path,filesystem_identity)
         VALUES (?,?,?,?)`,
      );
      for (const output of scope.canonicalOutputs) {
        insertOutput.run(
          projectId,
          fencingToken,
          output.path,
          output.filesystemIdentity,
        );
      }
      const row = this.database
        .prepare("SELECT * FROM writer_locks WHERE project_id=?")
        .get(projectId);
      this.database.exec("COMMIT");
      return publicCandidateWriterAdmission(
        row,
        scope.canonicalOutputPaths,
      );
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  assertCandidateWriterFence(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "fencingToken",
      ],
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "fencingToken",
      ],
      "candidate writer fence request",
    );
    const identity = {
      originId: requireSafeInteger(
        captured.originId,
        "originId must be a positive safe integer",
        1,
      ),
      projectId: requireCostProjectId(captured.projectId),
      jobId: requireBoundedString(
        captured.jobId,
        "jobId must be a bounded nonblank string",
        256,
      ),
      generation: requireSafeInteger(
        captured.generation,
        "generation must be a positive safe integer",
        1,
      ),
      leaseEpoch: requireSafeInteger(
        captured.leaseEpoch,
        "leaseEpoch must be a positive safe integer",
        1,
      ),
      fencingToken: requireSafeInteger(
        captured.fencingToken,
        "fencingToken must be a positive safe integer",
        1,
      ),
    };
    const now = requireNow(this.now());
    const row = this.database
      .prepare(
        `SELECT writer.*
         FROM writer_locks AS writer
         JOIN leases AS lease
           ON lease.job_id=writer.owner_job_id
          AND lease.generation=writer.owner_generation
          AND lease.epoch=writer.owner_lease_epoch
         WHERE writer.project_id=?
           AND writer.origin_id=?
           AND writer.owner_job_id=?
           AND writer.owner_generation=?
           AND writer.owner_lease_epoch=?
           AND writer.fencing_token=?
           AND writer.expires_at_ms>=?
           AND lease.expires_at_ms>=?`,
      )
      .get(
        identity.projectId,
        identity.originId,
        identity.jobId,
        identity.generation,
        identity.leaseEpoch,
        identity.fencingToken,
        now,
        now,
      );
    if (row === undefined) {
      throw stateError("STALE_WRITER_FENCE", "writer fence is stale");
    }
    const outputs = this.database
      .prepare(
        `SELECT canonical_output_path,filesystem_identity
         FROM writer_lock_outputs
         WHERE project_id=? AND fencing_token=?`,
      )
      .all(identity.projectId, identity.fencingToken)
      .sort((left, right) =>
        filesystemPathIdentity(left.canonical_output_path).localeCompare(
          filesystemPathIdentity(right.canonical_output_path),
        ),
      );
    try {
      const currentWorktree = realpathSync.native(row.canonical_worktree);
      if (
        filesystemPathIdentity(currentWorktree) !==
          filesystemPathIdentity(row.canonical_worktree) ||
        candidateFilesystemIdentity(currentWorktree) !== row.worktree_identity
      ) {
        throw new TypeError();
      }
      for (const output of outputs) {
        const currentOutput = realpathSync.native(output.canonical_output_path);
        if (
          filesystemPathIdentity(currentOutput) !==
            filesystemPathIdentity(output.canonical_output_path) ||
          candidateFilesystemIdentity(currentOutput) !==
            output.filesystem_identity
        ) {
          throw new TypeError();
        }
      }
    } catch {
      throw stateError("STALE_WRITER_FENCE", "writer fence is stale");
    }
    return publicCandidateWriterAdmission(
      row,
      outputs.map((output) => output.canonical_output_path),
    );
  }

  rebindCandidateWriterOutputs(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "fencingToken",
        "outputs",
      ],
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "fencingToken",
        "outputs",
      ],
      "candidate writer rebind request",
    );
    const identity = {
      originId: requireSafeInteger(
        captured.originId,
        "originId must be a positive safe integer",
        1,
      ),
      projectId: requireCostProjectId(captured.projectId),
      jobId: requireBoundedString(
        captured.jobId,
        "jobId must be a bounded nonblank string",
        256,
      ),
      generation: requireSafeInteger(
        captured.generation,
        "generation must be a positive safe integer",
        1,
      ),
      leaseEpoch: requireSafeInteger(
        captured.leaseEpoch,
        "leaseEpoch must be a positive safe integer",
        1,
      ),
      fencingToken: requireSafeInteger(
        captured.fencingToken,
        "fencingToken must be a positive safe integer",
        1,
      ),
    };
    const attestations = captureCandidateWriterRebindOutputs(captured.outputs);
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const now = requireNow(this.now());
      const row = this.database
        .prepare(
          `SELECT writer.*
           FROM writer_locks AS writer
           JOIN leases AS lease
             ON lease.job_id=writer.owner_job_id
            AND lease.generation=writer.owner_generation
            AND lease.epoch=writer.owner_lease_epoch
           WHERE writer.project_id=?
             AND writer.origin_id=?
             AND writer.owner_job_id=?
             AND writer.owner_generation=?
             AND writer.owner_lease_epoch=?
             AND writer.fencing_token=?
             AND writer.expires_at_ms>=?
             AND lease.expires_at_ms>=?`,
        )
        .get(
          identity.projectId,
          identity.originId,
          identity.jobId,
          identity.generation,
          identity.leaseEpoch,
          identity.fencingToken,
          now,
          now,
        );
      if (row === undefined) {
        throw stateError("STALE_WRITER_FENCE", "writer fence is stale");
      }
      const storedOutputs = this.database
        .prepare(
          `SELECT canonical_output_path,filesystem_identity
           FROM writer_lock_outputs
           WHERE project_id=? AND fencing_token=?`,
        )
        .all(identity.projectId, identity.fencingToken)
        .sort((left, right) =>
          filesystemPathIdentity(left.canonical_output_path).localeCompare(
            filesystemPathIdentity(right.canonical_output_path),
          ),
        );
      const sortedAttestations = [...attestations].sort((left, right) =>
        filesystemPathIdentity(left.path).localeCompare(
          filesystemPathIdentity(right.path),
        ),
      );
      if (storedOutputs.length !== sortedAttestations.length) {
        throw stateError(
          "WRITER_OUTPUT_ATTESTATION_MISMATCH",
          "writer output attestation does not match the admitted scope",
        );
      }
      const canonicalWorktree = realpathSync.native(row.canonical_worktree);
      if (
        filesystemPathIdentity(canonicalWorktree) !==
          filesystemPathIdentity(row.canonical_worktree) ||
        candidateFilesystemIdentity(canonicalWorktree) !== row.worktree_identity
      ) {
        throw stateError("STALE_WRITER_FENCE", "writer fence is stale");
      }
      const rebound = [];
      for (let index = 0; index < storedOutputs.length; index += 1) {
        const stored = storedOutputs[index];
        const attestation = sortedAttestations[index];
        try {
          const canonicalOutput = realpathSync.native(attestation.path);
          if (
            filesystemPathIdentity(canonicalOutput) !==
              filesystemPathIdentity(stored.canonical_output_path) ||
            !candidatePathContains(canonicalWorktree, canonicalOutput)
          ) {
            throw new TypeError();
          }
          const before = lstatSync(canonicalOutput, { bigint: true });
          if (
            before.isSymbolicLink() ||
            !before.isFile() ||
            before.nlink !== 1n ||
            before.size !== BigInt(attestation.byteLength)
          ) {
            throw new TypeError();
          }
          const beforeIdentity = candidateFilesystemIdentity(canonicalOutput);
          const bytes = readFileSync(canonicalOutput);
          const afterCanonical = realpathSync.native(attestation.path);
          const after = lstatSync(afterCanonical, { bigint: true });
          const afterIdentity = candidateFilesystemIdentity(afterCanonical);
          if (
            filesystemPathIdentity(afterCanonical) !==
              filesystemPathIdentity(canonicalOutput) ||
            after.isSymbolicLink() ||
            !after.isFile() ||
            after.nlink !== 1n ||
            after.size !== BigInt(attestation.byteLength) ||
            afterIdentity !== beforeIdentity ||
            bytes.length !== attestation.byteLength ||
            createHash("sha256").update(bytes).digest("hex") !==
              attestation.sha256
          ) {
            throw new TypeError();
          }
          rebound.push({
            path: canonicalOutput,
            filesystemIdentity: afterIdentity,
          });
        } catch (error) {
          if (error?.code === "WRITER_OUTPUT_ATTESTATION_MISMATCH") throw error;
          throw stateError(
            "WRITER_OUTPUT_ATTESTATION_MISMATCH",
            "writer output attestation does not match current content",
          );
        }
      }
      const update = this.database.prepare(
        `UPDATE writer_lock_outputs
         SET filesystem_identity=?
         WHERE project_id=? AND fencing_token=? AND canonical_output_path=?`,
      );
      for (const output of rebound) {
        const changed = update.run(
          output.filesystemIdentity,
          identity.projectId,
          identity.fencingToken,
          output.path,
        ).changes;
        if (changed !== 1) {
          throw stateError(
            "STALE_WRITER_FENCE",
            "writer output identity update was fenced",
          );
        }
      }
      if (ownsTransaction) this.database.exec("COMMIT");
      return publicCandidateWriterAdmission(
        row,
        rebound.map((output) => output.path),
      );
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  releaseCandidateWriterAdmission(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "fencingToken",
      ],
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "leaseEpoch",
        "fencingToken",
      ],
      "candidate writer release request",
    );
    const identity = {
      originId: requireSafeInteger(
        captured.originId,
        "originId must be a positive safe integer",
        1,
      ),
      projectId: requireCostProjectId(captured.projectId),
      jobId: requireBoundedString(
        captured.jobId,
        "jobId must be a bounded nonblank string",
        256,
      ),
      generation: requireSafeInteger(
        captured.generation,
        "generation must be a positive safe integer",
        1,
      ),
      leaseEpoch: requireSafeInteger(
        captured.leaseEpoch,
        "leaseEpoch must be a positive safe integer",
        1,
      ),
      fencingToken: requireSafeInteger(
        captured.fencingToken,
        "fencingToken must be a positive safe integer",
        1,
      ),
    };
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const deleted = this.database
        .prepare(
          `DELETE FROM writer_locks
           WHERE project_id=?
             AND origin_id=?
             AND owner_job_id=?
             AND owner_generation=?
             AND owner_lease_epoch=?
             AND fencing_token=?
             AND expires_at_ms>=?
             AND EXISTS (
               SELECT 1
               FROM leases AS lease
               WHERE lease.job_id=writer_locks.owner_job_id
                 AND lease.generation=writer_locks.owner_generation
                 AND lease.epoch=writer_locks.owner_lease_epoch
                 AND lease.expires_at_ms>=?
             )`,
        )
        .run(
          identity.projectId,
          identity.originId,
          identity.jobId,
          identity.generation,
          identity.leaseEpoch,
          identity.fencingToken,
          now,
          now,
        );
      if (deleted.changes !== 1) {
        throw stateError("STALE_WRITER_FENCE", "writer fence is stale");
      }
      this.database.exec("COMMIT");
      return Object.freeze({
        released: true,
        fencingToken: identity.fencingToken,
      });
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  enqueue(contract) {
    requireContractIdentity(contract);
    const priority = requireSafeInteger(
      contract.priority === undefined ? 0 : contract.priority,
      "priority must be a finite safe integer",
    );
    const maximumAttempts = requireSafeInteger(
      contract.maximumAttempts === undefined ? 1 : contract.maximumAttempts,
      "maximumAttempts must be a finite safe integer greater than or equal to 1",
      1,
    );
    const contractJson = canonicalPayloadJson(
      contract.payload === undefined ? null : contract.payload,
    );
    const immutableContract = {
      taskId: contract.taskId,
      role: contract.role,
      poolId: contract.poolId,
      priority,
      contractHash: contract.contractHash,
      inputFingerprint: contract.inputFingerprint,
      maximumAttempts,
      contractJson,
    };

    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    try {
      const existing = this.#getLatestRowByIdentity(contract.projectId, contract.idempotencyKey);
      if (existing !== undefined) {
        if (!immutableContractMatches(existing, immutableContract)) {
          throw idempotencyConflict();
        }
        if (ownsTransaction) this.database.exec("COMMIT");
        return publicGeneration(existing);
      }

      const jobId = `DJ-${randomUUID()}`;
      const createdAtMs = requireSafeInteger(
        this.now(),
        "now must return a finite nonnegative safe integer",
        0,
      );
      this.database
        .prepare(
          `INSERT INTO logical_jobs
             (job_id, project_id, idempotency_key, created_at_ms)
           VALUES (?, ?, ?, ?)`,
        )
        .run(jobId, contract.projectId, contract.idempotencyKey, createdAtMs);
      this.database
        .prepare(
          `INSERT INTO generations
             (job_id, generation, task_id, role, pool_id, priority, state, contract_hash,
              input_fingerprint, maximum_attempts, contract_json, accepted_result_hash,
              diagnostic_enqueued, created_at_ms, updated_at_ms)
           VALUES (?, 1, ?, ?, ?, ?, 'QUEUED', ?, ?, ?, ?, NULL, 0, ?, ?)`,
        )
        .run(
          jobId,
          contract.taskId,
          contract.role,
          contract.poolId,
          priority,
          contract.contractHash,
          contract.inputFingerprint,
          maximumAttempts,
          contractJson,
          createdAtMs,
          createdAtMs,
        );
      this.database
        .prepare(
          `INSERT INTO events
             (job_id, generation, event_type, event_json, created_at_ms)
           VALUES (?, 1, 'ENQUEUED', '{}', ?)`,
        )
        .run(jobId, createdAtMs);
      if (ownsTransaction) this.database.exec("COMMIT");
      return this.getGeneration(jobId, 1);
    } catch (error) {
      if (!ownsTransaction) throw error;
      let rollbackError;
      if (this.database.isTransaction) {
        try {
          this.database.exec("ROLLBACK");
        } catch (caughtRollbackError) {
          rollbackError = caughtRollbackError;
        }
      }
      if (rollbackError !== undefined) {
        throw new AggregateError(
          [error, rollbackError],
          "scheduler transaction and rollback both failed",
          { cause: error },
        );
      }
      throw error;
    }
  }

  leaseNext({ poolId, workerId, leaseMs } = {}) {
    requireNonblankString(poolId, "poolId must be a nonblank string");
    requireNonblankString(workerId, "workerId must be a nonblank string");
    const validatedLeaseMs = requireSafeInteger(
      leaseMs,
      "leaseMs must be a positive safe integer",
      1,
    );

    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const expiresAtMs = safeLeaseExpiry(now, validatedLeaseMs);
      const generationRow = this.database
        .prepare(
          `SELECT job_id, generation
           FROM generations INDEXED BY idx_generations_queue
           WHERE pool_id = ? AND state = 'QUEUED'
           ORDER BY priority DESC, created_at_ms ASC, job_id ASC, generation ASC
           LIMIT 1`,
        )
        .get(poolId);
      if (generationRow === undefined) {
        this.database.exec("COMMIT");
        return null;
      }

      const epochRow = this.database
        .prepare(
          `SELECT MAX(epoch) AS maximum_epoch
           FROM attempts
           WHERE job_id = ? AND generation = ?`,
        )
        .get(generationRow.job_id, generationRow.generation);
      const previousEpoch = epochRow.maximum_epoch === null ? 0 : epochRow.maximum_epoch;
      const epoch = requireSafeInteger(
        previousEpoch + 1,
        "next lease epoch exceeds the safe integer bound",
        1,
      );
      const attemptId = `DA-${randomUUID()}`;
      const identity = {
        jobId: generationRow.job_id,
        generation: generationRow.generation,
        attemptId,
        workerId,
        epoch,
      };

      this.database
        .prepare(
          `INSERT INTO attempts
             (job_id, generation, attempt_id, worker_id, epoch, state, started_at_ms,
              finished_at_ms, failure_class)
           VALUES (?, ?, ?, ?, ?, 'RUNNING', ?, NULL, NULL)`,
        )
        .run(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
          now,
        );
      this.database
        .prepare(
          `INSERT INTO leases
             (job_id, generation, attempt_id, worker_id, epoch, heartbeat_at_ms,
              expires_at_ms)
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
        )
        .run(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
          now,
          expiresAtMs,
        );
      const generationUpdate = this.database
        .prepare(
          `UPDATE generations
           SET state = 'RUNNING', updated_at_ms = ?
           WHERE job_id = ? AND generation = ? AND state = 'QUEUED'`,
        )
        .run(now, identity.jobId, identity.generation);
      if (generationUpdate.changes !== 1) {
        throw stateError("LEASE_STATE_CONFLICT", "queued generation changed during lease");
      }
      this.database
        .prepare(
          `INSERT INTO events
             (job_id, generation, event_type, event_json, created_at_ms)
           VALUES (?, ?, 'LEASED', '{}', ?)`,
        )
        .run(identity.jobId, identity.generation, now);
      this.database.exec("COMMIT");
      return identity;
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  leaseGeneration({ jobId, generation, workerId, leaseMs } = {}) {
    requireNonblankString(jobId, "jobId must be a nonblank string");
    requireSafeInteger(generation, "generation must be a positive safe integer", 1);
    requireNonblankString(workerId, "workerId must be a nonblank string");
    const validatedLeaseMs = requireSafeInteger(
      leaseMs,
      "leaseMs must be a positive safe integer",
      1,
    );

    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const expiresAtMs = safeLeaseExpiry(now, validatedLeaseMs);
      const generationRow = this.database
        .prepare(
          `SELECT job_id, generation
           FROM generations
           WHERE job_id = ? AND generation = ? AND state = 'QUEUED'`,
        )
        .get(jobId, generation);
      if (generationRow === undefined) {
        this.database.exec("COMMIT");
        return null;
      }
      const epochRow = this.database
        .prepare(
          `SELECT MAX(epoch) AS maximum_epoch
           FROM attempts
           WHERE job_id = ? AND generation = ?`,
        )
        .get(jobId, generation);
      const previousEpoch = epochRow.maximum_epoch === null ? 0 : epochRow.maximum_epoch;
      const epoch = requireSafeInteger(
        previousEpoch + 1,
        "next lease epoch exceeds the safe integer bound",
        1,
      );
      const identity = {
        jobId,
        generation,
        attemptId: `DA-${randomUUID()}`,
        workerId,
        epoch,
      };
      this.database
        .prepare(
          `INSERT INTO attempts
             (job_id, generation, attempt_id, worker_id, epoch, state, started_at_ms,
              finished_at_ms, failure_class)
           VALUES (?, ?, ?, ?, ?, 'RUNNING', ?, NULL, NULL)`,
        )
        .run(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
          now,
        );
      this.database
        .prepare(
          `INSERT INTO leases
             (job_id, generation, attempt_id, worker_id, epoch, heartbeat_at_ms,
              expires_at_ms)
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
        )
        .run(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
          now,
          expiresAtMs,
        );
      const updated = this.database
        .prepare(
          `UPDATE generations
           SET state = 'RUNNING', updated_at_ms = ?
           WHERE job_id = ? AND generation = ? AND state = 'QUEUED'`,
        )
        .run(now, identity.jobId, identity.generation);
      if (updated.changes !== 1) {
        throw stateError("LEASE_STATE_CONFLICT", "queued generation changed during lease");
      }
      this.database
        .prepare(
          `INSERT INTO events
             (job_id, generation, event_type, event_json, created_at_ms)
           VALUES (?, ?, 'LEASED', '{}', ?)`,
        )
        .run(identity.jobId, identity.generation, now);
      this.database.exec("COMMIT");
      return identity;
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  heartbeat(request) {
    const identity = requireLeaseIdentity(request);
    const leaseMs = requireSafeInteger(
      request.leaseMs,
      "leaseMs must be a positive safe integer",
      1,
    );

    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const expiresAtMs = safeLeaseExpiry(now, leaseMs);
      const result = this.database
        .prepare(
          `UPDATE leases
           SET heartbeat_at_ms = ?, expires_at_ms = MAX(expires_at_ms, ?)
           WHERE job_id = ?
             AND generation = ?
             AND attempt_id = ?
             AND worker_id = ?
             AND epoch = ?
             AND expires_at_ms >= ?
             AND EXISTS (
               SELECT 1
               FROM generations AS g
               WHERE g.job_id = leases.job_id
                 AND g.generation = leases.generation
                 AND g.state IN ('RUNNING', 'VALIDATING')
             )`,
        )
        .run(
          now,
          expiresAtMs,
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
          now,
        );
      if (result.changes === 1 && this.#candidateCostWritable) {
        this.database
          .prepare(
            `UPDATE writer_locks
             SET expires_at_ms=MAX(expires_at_ms,?)
             WHERE owner_job_id=?
               AND owner_generation=?
               AND owner_lease_epoch=?`,
          )
          .run(
            expiresAtMs,
            identity.jobId,
            identity.generation,
            identity.epoch,
          );
      }
      this.database.exec("COMMIT");
      return result.changes === 1;
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  beginValidation(request) {
    const identity = requireLeaseIdentity(request);

    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const result = this.database
        .prepare(
          `UPDATE generations
           SET state = 'VALIDATING', updated_at_ms = ?
           WHERE job_id = ?
             AND generation = ?
             AND state = 'RUNNING'
             AND EXISTS (
               SELECT 1
               FROM leases AS l
               WHERE l.job_id = generations.job_id
                 AND l.generation = generations.generation
                 AND l.attempt_id = ?
                 AND l.worker_id = ?
                 AND l.epoch = ?
                 AND l.expires_at_ms >= ?
             )`,
        )
        .run(
          now,
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
          now,
        );
      this.database.exec("COMMIT");
      return result.changes === 1;
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  acceptCandidateResult(request) {
    this.#requireCandidateSchemaWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "attemptId",
        "workerId",
        "epoch",
        "resultHash",
        "inputFingerprint",
        "writerFencingToken",
      ],
      [
        "originId",
        "projectId",
        "jobId",
        "generation",
        "attemptId",
        "workerId",
        "epoch",
        "resultHash",
        "inputFingerprint",
      ],
      "candidate result acceptance request",
    );
    const identity = requireLeaseIdentity(captured);
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const resultHash = requireNonblankString(
      captured.resultHash,
      "resultHash must be a nonblank string",
    );
    const inputFingerprint = requireNonblankString(
      captured.inputFingerprint,
      "inputFingerprint must be a nonblank string",
    );
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const generation = this.database
        .prepare(
          `SELECT generation.role
           FROM generations AS generation
           JOIN logical_job_origins AS ownership
             ON ownership.job_id=generation.job_id
           WHERE ownership.origin_id=?
             AND ownership.project_id=?
             AND generation.job_id=?
             AND generation.generation=?`,
        )
        .get(originId, projectId, identity.jobId, identity.generation);
      if (generation === undefined) {
        throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
      }
      if (generation.role === "WRITER") {
        const writerFencingToken = requireSafeInteger(
          captured.writerFencingToken,
          "writerFencingToken must be a positive safe integer",
          1,
        );
        const now = requireNow(this.now());
        const writer = this.database
          .prepare(
            `SELECT 1
             FROM writer_locks AS writer
             JOIN leases AS lease
               ON lease.job_id=writer.owner_job_id
              AND lease.generation=writer.owner_generation
              AND lease.epoch=writer.owner_lease_epoch
             WHERE writer.project_id=?
               AND writer.origin_id=?
               AND writer.owner_job_id=?
               AND writer.owner_generation=?
               AND writer.owner_lease_epoch=?
               AND writer.fencing_token=?
               AND writer.expires_at_ms>=?
               AND lease.expires_at_ms>=?`,
          )
          .get(
            projectId,
            originId,
            identity.jobId,
            identity.generation,
            identity.epoch,
            writerFencingToken,
            now,
            now,
          );
        if (writer === undefined) {
          throw stateError("STALE_WRITER_FENCE", "writer fence is stale");
        }
      } else if (captured.writerFencingToken !== undefined) {
        throw new TypeError("read result cannot carry a writer fencing token");
      }
      const accepted = this.acceptResult({
        ...identity,
        resultHash,
        inputFingerprint,
      });
      if (ownsTransaction) this.database.exec("COMMIT");
      return accepted;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  acceptResult(request) {
    const identity = requireLeaseIdentity(request);
    const resultHash = requireNonblankString(
      request.resultHash,
      "resultHash must be a nonblank string",
    );
    const inputFingerprint = requireNonblankString(
      request.inputFingerprint,
      "inputFingerprint must be a nonblank string",
    );

    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const current = this.database
        .prepare(
          `SELECT g.state, g.input_fingerprint
           FROM generations AS g
           JOIN leases AS l
             ON l.job_id = g.job_id AND l.generation = g.generation
           WHERE g.job_id = ?
             AND g.generation = ?
             AND l.attempt_id = ?
             AND l.worker_id = ?
             AND l.epoch = ?
             AND l.expires_at_ms >= ?`,
        )
        .get(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
          now,
        );
      if (current === undefined) {
        if (ownsTransaction) this.database.exec("COMMIT");
        return { accepted: false, reason: "STALE_EPOCH" };
      }

      if (current.input_fingerprint !== inputFingerprint) {
        this.database
          .prepare(
            `UPDATE generations
             SET state = 'QUARANTINED', accepted_result_hash = NULL, updated_at_ms = ?
             WHERE job_id = ? AND generation = ?`,
          )
          .run(now, identity.jobId, identity.generation);
        this.database
          .prepare(
            `UPDATE attempts
             SET state = 'FAILED',
                 finished_at_ms = ?,
                 failure_class = 'INPUT_FINGERPRINT_CHANGED'
             WHERE job_id = ?
               AND generation = ?
               AND attempt_id = ?
               AND worker_id = ?
               AND epoch = ?`,
          )
          .run(
            now,
            identity.jobId,
            identity.generation,
            identity.attemptId,
            identity.workerId,
            identity.epoch,
          );
        this.#deleteCandidateWriterLockForTerminal(
          identity.jobId,
          identity.generation,
          identity.epoch,
        );
        this.database
          .prepare(
            `DELETE FROM leases
             WHERE job_id = ?
               AND generation = ?
               AND attempt_id = ?
               AND worker_id = ?
               AND epoch = ?`,
          )
          .run(
            identity.jobId,
            identity.generation,
            identity.attemptId,
            identity.workerId,
            identity.epoch,
          );
        this.database
          .prepare(
            `INSERT INTO events
               (job_id, generation, event_type, event_json, created_at_ms)
             VALUES (?, ?, 'RESULT_QUARANTINED', '{}', ?)`,
          )
          .run(identity.jobId, identity.generation, now);
        if (ownsTransaction) this.database.exec("COMMIT");
        return { accepted: false, reason: "INPUT_FINGERPRINT_CHANGED" };
      }

      if (current.state !== "VALIDATING") {
        if (ownsTransaction) this.database.exec("COMMIT");
        return { accepted: false, reason: "INVALID_STATE" };
      }

      this.database
        .prepare(
          `UPDATE generations
           SET state = 'SUCCEEDED', accepted_result_hash = ?, updated_at_ms = ?
           WHERE job_id = ? AND generation = ? AND state = 'VALIDATING'`,
        )
        .run(resultHash, now, identity.jobId, identity.generation);
      this.database
        .prepare(
          `UPDATE attempts
           SET state = 'SUCCEEDED', finished_at_ms = ?, failure_class = NULL
           WHERE job_id = ?
             AND generation = ?
             AND attempt_id = ?
             AND worker_id = ?
             AND epoch = ?`,
        )
        .run(
          now,
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      this.#deleteCandidateWriterLockForTerminal(
        identity.jobId,
        identity.generation,
        identity.epoch,
      );
      this.database
        .prepare(
          `DELETE FROM leases
           WHERE job_id = ?
             AND generation = ?
             AND attempt_id = ?
             AND worker_id = ?
             AND epoch = ?`,
        )
        .run(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      this.database
        .prepare(
          `INSERT INTO events
             (job_id, generation, event_type, event_json, created_at_ms)
           VALUES (?, ?, 'RESULT_ACCEPTED', '{}', ?)`,
        )
        .run(identity.jobId, identity.generation, now);
      if (ownsTransaction) this.database.exec("COMMIT");
      return { accepted: true, reason: "ACCEPTED" };
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    }
  }

  quarantineAttempt(request) {
    const identity = requireLeaseIdentity(request);
    const failureClass = requireBoundedString(
      request.failureClass,
      "failureClass must be a bounded nonblank string",
      128,
    );
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const updated = this.database
        .prepare(
          `UPDATE generations
           SET state = 'QUARANTINED',
               accepted_result_hash = NULL,
               diagnostic_enqueued = 0,
               updated_at_ms = ?
           WHERE job_id = ?
             AND generation = ?
             AND state IN ('RUNNING', 'VALIDATING')
             AND EXISTS (
               SELECT 1
               FROM leases AS l
               WHERE l.job_id = generations.job_id
                 AND l.generation = generations.generation
                 AND l.attempt_id = ?
                 AND l.worker_id = ?
                 AND l.epoch = ?
             )`,
        )
        .run(
          now,
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      if (updated.changes !== 1) {
        this.database.exec("COMMIT");
        return false;
      }
      this.database
        .prepare(
          `UPDATE attempts
           SET state = 'FAILED', finished_at_ms = ?, failure_class = ?
           WHERE job_id = ?
             AND generation = ?
             AND attempt_id = ?
             AND worker_id = ?
             AND epoch = ?`,
        )
        .run(
          now,
          failureClass,
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      this.#deleteCandidateWriterLockForTerminal(
        identity.jobId,
        identity.generation,
        identity.epoch,
      );
      this.database
        .prepare(
          `DELETE FROM leases
           WHERE job_id = ?
             AND generation = ?
             AND attempt_id = ?
             AND worker_id = ?
             AND epoch = ?`,
        )
        .run(
          identity.jobId,
          identity.generation,
          identity.attemptId,
          identity.workerId,
          identity.epoch,
        );
      this.database
        .prepare(
          `INSERT INTO events
             (job_id, generation, event_type, event_json, created_at_ms)
           VALUES (?, ?, 'RESULT_QUARANTINED', ?, ?)`,
        )
        .run(
          identity.jobId,
          identity.generation,
          canonicalPayloadJson({ failureClass }),
          now,
        );
      this.database.exec("COMMIT");
      return true;
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  recoverExpiredLeases() {
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const expiredLeases = this.database
        .prepare(
          `SELECT
             l.job_id,
             l.generation,
             l.attempt_id,
             l.worker_id,
             l.epoch,
             l.expires_at_ms,
             g.maximum_attempts
           FROM leases AS l INDEXED BY idx_leases_expiry
           JOIN generations AS g
             ON g.job_id = l.job_id AND g.generation = l.generation
           WHERE l.expires_at_ms < ?
             AND g.state IN ('RUNNING', 'VALIDATING')
           ORDER BY l.expires_at_ms ASC, l.job_id ASC, l.generation ASC`,
        )
        .all(now);
      const recovered = [];
      for (const lease of expiredLeases) {
        if (this.#candidateCostWritable) {
          this.database
            .prepare(
              `UPDATE cost_reservations
               SET state='UNKNOWN',updated_at_ms=?
               WHERE job_id=?
                 AND attempt_id=?
                 AND state='OPEN'`,
            )
            .run(now, lease.job_id, lease.attempt_id);
        }
        this.database
          .prepare(
            `UPDATE attempts
             SET state = 'FAILED',
                 finished_at_ms = ?,
                 failure_class = 'LEASE_EXPIRED'
             WHERE job_id = ?
               AND generation = ?
               AND attempt_id = ?
               AND worker_id = ?
               AND epoch = ?`,
          )
          .run(
            now,
            lease.job_id,
            lease.generation,
            lease.attempt_id,
            lease.worker_id,
            lease.epoch,
          );
        const attemptCount = this.database
          .prepare(
            `SELECT COUNT(*) AS count
             FROM attempts
             WHERE job_id = ? AND generation = ?`,
          )
          .get(lease.job_id, lease.generation).count;
        const action = attemptCount < lease.maximum_attempts ? "REQUEUED" : "FAILED";
        const nextState = action === "REQUEUED" ? "QUEUED" : "FAILED";
        this.database
          .prepare(
            `UPDATE generations
             SET state = ?, accepted_result_hash = NULL, updated_at_ms = ?
             WHERE job_id = ?
               AND generation = ?
               AND state IN ('RUNNING', 'VALIDATING')`,
          )
          .run(nextState, now, lease.job_id, lease.generation);
        this.#deleteCandidateWriterLockForTerminal(
          lease.job_id,
          lease.generation,
          lease.epoch,
        );
        this.database
          .prepare(
            `DELETE FROM leases
             WHERE job_id = ?
               AND generation = ?
               AND attempt_id = ?
               AND worker_id = ?
               AND epoch = ?`,
          )
          .run(
            lease.job_id,
            lease.generation,
            lease.attempt_id,
            lease.worker_id,
            lease.epoch,
          );
        this.database
          .prepare(
            `INSERT INTO events
               (job_id, generation, event_type, event_json, created_at_ms)
             VALUES (?, ?, 'LEASE_EXPIRED', ?, ?)`,
          )
          .run(
            lease.job_id,
            lease.generation,
            canonicalPayloadJson({ action }),
            now,
          );
        recovered.push({
          jobId: lease.job_id,
          generation: lease.generation,
          action,
        });
      }
      this.database.exec("COMMIT");
      return recovered;
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  createRetry(request) {
    if (request === null || typeof request !== "object") {
      throw new TypeError("retry request must be an object");
    }
    const jobId = requireNonblankString(request.jobId, "jobId must be a nonblank string");
    const expectedGeneration = requireSafeInteger(
      request.expectedGeneration,
      "expectedGeneration must be a positive safe integer",
      1,
    );
    const reasonCode = requireRetryReasonCode(request.reasonCode);
    const eventJson = canonicalPayloadJson({ reasonCode });

    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const latest = this.#getLatestRowByJobId(jobId);
      if (latest === undefined) {
        throw stateError("INVALID_RETRY_STATE", "retry requires a terminal generation");
      }
      if (latest.generation !== expectedGeneration) {
        throw stateError("STALE_GENERATION", "expected generation is stale");
      }
      if (!TERMINAL_GENERATION_STATES.has(latest.state)) {
        throw stateError("INVALID_RETRY_STATE", "retry requires a terminal generation");
      }
      const nextGeneration = requireSafeInteger(
        expectedGeneration + 1,
        "next generation exceeds the safe integer bound",
        1,
      );
      this.database
        .prepare(
          `INSERT INTO generations
             (job_id, generation, task_id, role, pool_id, priority, state, contract_hash,
              input_fingerprint, maximum_attempts, contract_json, accepted_result_hash,
              diagnostic_enqueued, created_at_ms, updated_at_ms)
           VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', ?, ?, ?, ?, NULL, 0, ?, ?)`,
        )
        .run(
          latest.job_id,
          nextGeneration,
          latest.task_id,
          latest.role,
          latest.pool_id,
          latest.priority,
          latest.contract_hash,
          latest.input_fingerprint,
          latest.maximum_attempts,
          latest.contract_json,
          now,
          now,
        );
      this.database
        .prepare(
          `INSERT INTO events
             (job_id, generation, event_type, event_json, created_at_ms)
           VALUES (?, ?, 'RETRY_CREATED', ?, ?)`,
        )
        .run(jobId, nextGeneration, eventJson, now);
      this.database.exec("COMMIT");
      return this.getGeneration(jobId, nextGeneration);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  cancelGeneration(request) {
    if (request === null || typeof request !== "object") {
      throw new TypeError("cancellation request must be an object");
    }
    const jobId = requireBoundedString(
      request.jobId,
      "jobId must be a bounded nonblank string",
      256,
    );
    const generation = requireSafeInteger(
      request.generation,
      "generation must be a positive safe integer",
      1,
    );
    const actor = requireBoundedString(
      request.actor,
      "actor must be a bounded nonblank string",
      128,
    );
    const reason = requireBoundedString(
      request.reason,
      "reason must be a bounded nonblank string",
      256,
    );

    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const latest = this.#getLatestRowByJobId(jobId);
      if (latest === undefined || latest.generation !== generation) {
        throw stateError("STALE_GENERATION", "cancellation generation is stale");
      }
      if (latest.state === "CANCELED") {
        if (ownsTransaction) this.database.exec("COMMIT");
        return { ...publicGeneration(latest), idempotent: true };
      }
      if (!["QUEUED", "RUNNING", "VALIDATING"].includes(latest.state)) {
        throw stateError("INVALID_CANCEL_STATE", "generation is already terminal");
      }
      this.database
        .prepare(
          `UPDATE attempts
           SET state = 'CANCELED',
               finished_at_ms = ?,
               failure_class = 'CANCELLATION'
           WHERE job_id = ?
             AND generation = ?
             AND state = 'RUNNING'`,
        )
        .run(now, jobId, generation);
      this.#deleteCandidateWriterLockForTerminal(jobId, generation);
      this.database
        .prepare("DELETE FROM leases WHERE job_id = ? AND generation = ?")
        .run(jobId, generation);
      this.database
        .prepare(
          `UPDATE generations
           SET state = 'CANCELED',
               accepted_result_hash = NULL,
               diagnostic_enqueued = 0,
               updated_at_ms = ?
           WHERE job_id = ?
             AND generation = ?
             AND state IN ('QUEUED', 'RUNNING', 'VALIDATING')`,
        )
        .run(now, jobId, generation);
      this.database
        .prepare(
          `INSERT INTO events
             (job_id, generation, event_type, event_json, created_at_ms)
           VALUES (?, ?, 'CANCELED', ?, ?)`,
        )
        .run(
          jobId,
          generation,
          canonicalPayloadJson({ actor, canceledAtMs: now, reason }),
          now,
        );
      const canceled = this.#getLatestRowByJobId(jobId);
      if (ownsTransaction) this.database.exec("COMMIT");
      return { ...publicGeneration(canceled), idempotent: false };
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    }
  }

  listQueuedGenerations() {
    if (this.#candidateCostWritable) {
      return this.database
        .prepare(
          `SELECT g.*,CAST(substr(g.task_id,8) AS INTEGER) AS origin_id
           FROM generations AS g
           WHERE g.state='QUEUED'
           ORDER BY g.created_at_ms ASC, g.job_id ASC, g.generation ASC`,
        )
        .all()
        .map((row) => ({
          ...publicGeneration(row),
          taskId: `origin:${row.origin_id}`,
        }));
    }
    return this.database
      .prepare(
        `${GENERATION_SELECT}
         WHERE g.state = 'QUEUED'
         ORDER BY g.created_at_ms ASC, g.job_id ASC, g.generation ASC`,
      )
      .all()
      .map(publicGeneration);
  }

  getDispatchGeneration(jobId, generation) {
    requireNonblankString(jobId, "jobId must be a nonblank string");
    requireSafeInteger(generation, "generation must be a positive safe integer", 1);
    const row = this.#candidateCostWritable
      ? this.database
          .prepare(
            `SELECT g.*,j.project_id,
                    CAST(substr(g.task_id,8) AS INTEGER) AS origin_id
             FROM generations AS g
             JOIN logical_jobs AS j ON j.job_id=g.job_id
             WHERE g.job_id=? AND g.generation=?`,
          )
          .get(jobId, generation)
      : this.database
          .prepare(
            `SELECT g.*, j.project_id
             FROM generations AS g
             JOIN logical_jobs AS j ON j.job_id = g.job_id
             WHERE g.job_id = ? AND g.generation = ?`,
          )
          .get(jobId, generation);
    if (row === undefined) return null;
    return {
      ...publicGeneration(row),
      ...(this.#candidateCostWritable
        ? { taskId: `origin:${row.origin_id}`, originId: row.origin_id }
        : {}),
      projectId: row.project_id,
      payload: JSON.parse(row.contract_json),
    };
  }

  listEvents(jobId, afterSequence = 0, limit = 1000) {
    requireBoundedString(jobId, "jobId must be a bounded nonblank string", 256);
    requireSafeInteger(afterSequence, "afterSequence must be a nonnegative safe integer", 0);
    const boundedLimit = requireSafeInteger(limit, "limit must be a positive safe integer", 1);
    if (boundedLimit > 1000) throw new TypeError("limit must not exceed 1000");
    return this.database
      .prepare(
        `SELECT sequence, job_id, generation, event_type, event_json, created_at_ms
         FROM events
         WHERE job_id = ? AND sequence > ?
         ORDER BY sequence ASC
         LIMIT ?`,
      )
      .all(jobId, afterSequence, boundedLimit)
      .map((row) => ({
        sequence: row.sequence,
        jobId: row.job_id,
        generation: row.generation,
        eventType: row.event_type,
        payload: JSON.parse(row.event_json),
        createdAtMs: row.created_at_ms,
      }));
  }

  executeCandidateProtocolRequest(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      [
        "originId",
        "projectId",
        "requestId",
        "method",
        "payload",
        "execute",
      ],
      undefined,
      "candidate protocol request",
    );
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const projectId = requireCostProjectId(captured.projectId);
    const requestId = requireCostText(captured.requestId, "requestId", 128);
    const method = requireCostText(captured.method, "method", 32);
    if (!CANDIDATE_PROTOCOL_METHODS.includes(method)) {
      throw new TypeError("invalid candidate protocol method");
    }
    if (typeof captured.execute !== "function") {
      throw new TypeError("execute must be a function");
    }
    const normalizationSourceJson = canonicalPayloadJson({
      method,
      payload: captured.payload,
    });
    const normalizationSourceBytes = Buffer.byteLength(
      normalizationSourceJson,
      "utf8",
    );
    if (normalizationSourceBytes > MAX_CANDIDATE_PROTOCOL_REQUEST_BYTES) {
      throw new TypeError("candidate protocol request is too large");
    }
    const normalizationSourceHash = candidateSha256(normalizationSourceJson);

    this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      this.#requireCandidateOriginMembership(originId, projectId);
      const existing = this.database
        .prepare(
          `SELECT project_id,method,normalization_source_json,
                  normalization_source_hash,request_state,outcome_json
           FROM protocol_requests
           WHERE origin_id=? AND request_id=?`,
        )
        .get(originId, requestId);
      if (existing !== undefined) {
        if (
          existing.project_id !== projectId ||
          existing.method !== method ||
          existing.normalization_source_hash !== normalizationSourceHash ||
          existing.normalization_source_json !== normalizationSourceJson
        ) {
          throw stateError(
            "REQUEST_ID_CONFLICT",
            "request id conflicts with prior request",
          );
        }
        if (
          existing.request_state !== "COMMITTED" ||
          existing.outcome_json === null
        ) {
          throw stateError(
            "REQUEST_IN_PROGRESS",
            "protocol request is in progress",
          );
        }
        const outcome = candidateDeepFreeze(JSON.parse(existing.outcome_json));
        this.database.exec("COMMIT");
        return Object.freeze({ replayed: true, outcome });
      }

      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO protocol_requests
             (origin_id,project_id,request_id,method,request_fingerprint,
              normalization_source_json,normalization_source_hash,
              normalization_source_bytes,request_state,normalization_epoch,
              outcome_json,outcome_hash,outcome_bytes,created_at_ms,updated_at_ms)
           VALUES (?,?,?,?,?,?,?,?, 'ACCEPTED',0,NULL,NULL,NULL,?,?)`,
        )
        .run(
          originId,
          projectId,
          requestId,
          method,
          normalizationSourceHash,
          normalizationSourceJson,
          normalizationSourceHash,
          normalizationSourceBytes,
          now,
          now,
        );
      const outcomeJson = canonicalPayloadJson(captured.execute());
      const outcomeBytes = Buffer.byteLength(outcomeJson, "utf8");
      if (outcomeBytes > MAX_CANDIDATE_PROTOCOL_OUTCOME_BYTES) {
        throw new TypeError("candidate protocol outcome is too large");
      }
      const outcomeHash = candidateSha256(outcomeJson);
      const committed = this.database
        .prepare(
          `UPDATE protocol_requests
           SET request_state='COMMITTED',outcome_json=?,outcome_hash=?,
               outcome_bytes=?,updated_at_ms=?
           WHERE origin_id=? AND request_id=? AND project_id=?
             AND request_state='ACCEPTED'
             AND normalization_source_hash=?`,
        )
        .run(
          outcomeJson,
          outcomeHash,
          outcomeBytes,
          now,
          originId,
          requestId,
          projectId,
          normalizationSourceHash,
        );
      if (committed.changes !== 1) {
        throw stateError(
          "REQUEST_IN_PROGRESS",
          "protocol request could not be committed",
        );
      }
      this.database.exec("COMMIT");
      return Object.freeze({
        replayed: false,
        outcome: candidateDeepFreeze(JSON.parse(outcomeJson)),
      });
    } catch (error) {
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  executeProtocolRequest({ requestId, requestFingerprint, execute } = {}) {
    if (!this.#legacyProtocolWritable) {
      throw stateError(
        "LEGACY_PROTOCOL_AUDIT_ONLY",
        "legacy protocol responses are read-only audit data",
      );
    }
    const exactRequestId = requireBoundedString(
      requestId,
      "requestId must be a bounded nonblank string",
      256,
    );
    if (
      typeof requestFingerprint !== "string" ||
      !/^[0-9a-f]{64}$/.test(requestFingerprint)
    ) {
      throw new TypeError("request fingerprint must be lowercase sha256");
    }
    if (typeof execute !== "function") throw new TypeError("execute must be a function");
    this.database.exec("BEGIN IMMEDIATE");
    this.#protocolRequestDepth += 1;
    try {
      const existing = this.database
        .prepare(
          `SELECT request_fingerprint, response_json
           FROM protocol_responses
           WHERE request_id = ?`,
        )
        .get(exactRequestId);
      if (existing !== undefined) {
        if (existing.request_fingerprint !== requestFingerprint) {
          throw stateError("REQUEST_ID_CONFLICT", "request id conflicts with prior request");
        }
        this.database.exec("COMMIT");
        if (existing.response_json === null) {
          throw stateError(
            "PROTOCOL_RESPONSE_INCOMPLETE",
            "protocol response transaction is incomplete",
          );
        }
        return { replayed: true, responseJson: existing.response_json };
      }
      const responseJson = execute();
      if (
        typeof responseJson !== "string" ||
        Buffer.byteLength(responseJson, "utf8") > MAX_PROTOCOL_RESPONSE_BYTES
      ) {
        throw new TypeError("invalid protocol response");
      }
      const now = requireNow(this.now());
      this.database
        .prepare(
          `INSERT INTO protocol_responses
             (request_id, request_fingerprint, response_json, created_at_ms)
           VALUES (?, ?, ?, ?)`,
        )
        .run(exactRequestId, requestFingerprint, responseJson, now);
      this.database.exec("COMMIT");
      return { replayed: false, responseJson };
    } catch (error) {
      this.#rollbackTransaction(error);
    } finally {
      this.#protocolRequestDepth -= 1;
    }
  }

  configureProviderAccounting(request) {
    this.#requireCandidateTransmissionCostWritable();
    const policy = captureProviderAccountingPolicyRequest(request);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      this.#assertOriginOwnsProject(policy.originId, policy.projectId);
      this.#requireCandidateJobOwnership(
        policy.originId,
        policy.projectId,
        policy.jobId,
      );
      let budget = this.#getTransmissionProjectBudget(policy.projectId);
      if (budget === undefined) {
        this.database
          .prepare(
            `INSERT INTO transmission_project_budgets
               (project_id,ceiling_nano_usd,spent_nano_usd,reserved_nano_usd,
                pricing_version,created_at_ms,updated_at_ms)
             VALUES (?,?,0,0,?,?,?)`,
          )
          .run(
            policy.projectId,
            policy.ceilingNanoUsd,
            policy.pricingVersion,
            now,
            now,
          );
        budget = this.#getTransmissionProjectBudget(policy.projectId);
      } else if (
        budget.ceiling_nano_usd !== policy.ceilingNanoUsd ||
        budget.pricing_version !== policy.pricingVersion
      ) {
        throw stateError(
          "PROJECT_BUDGET_CONFLICT",
          "project transmission budget conflicts with frozen policy",
        );
      }

      let limit = this.#getProviderJobLimit(policy.projectId, policy.jobId);
      if (limit === undefined) {
        this.database
          .prepare(
            `INSERT INTO provider_job_limits
               (project_id,job_id,maximum_provider_calls,maximum_input_tokens,
                maximum_cached_input_tokens,maximum_output_tokens_total,
                maximum_total_tokens,created_at_ms,updated_at_ms)
             VALUES (?,?,?,?,?,?,?,?,?)`,
          )
          .run(
            policy.projectId,
            policy.jobId,
            policy.maximumProviderCalls,
            policy.maximumInputTokens,
            policy.maximumCachedInputTokens,
            policy.maximumOutputTokensTotal,
            policy.maximumTotalTokens,
            now,
            now,
          );
        limit = this.#getProviderJobLimit(policy.projectId, policy.jobId);
      } else if (!providerJobLimitMatches(limit, policy)) {
        throw stateError(
          "PROVIDER_JOB_LIMIT_CONFLICT",
          "provider job limit conflicts with frozen policy",
        );
      }

      const counts = this.#getProviderTransmissionCounts(
        policy.projectId,
        policy.jobId,
      );
      this.database.exec("COMMIT");
      return publicProviderAccountingSnapshot(budget, limit, counts);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  reserveProviderTransmission(request) {
    this.#requireCandidateTransmissionCostWritable();
    const reservation = captureProviderTransmissionReservationRequest(request);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      this.#assertOriginOwnsProject(
        reservation.originId,
        reservation.projectId,
      );
      this.#requireCandidateJobOwnership(
        reservation.originId,
        reservation.projectId,
        reservation.jobId,
      );
      const budget = this.#getTransmissionProjectBudget(reservation.projectId);
      const limit = this.#getProviderJobLimit(
        reservation.projectId,
        reservation.jobId,
      );
      if (budget === undefined || limit === undefined) {
        throw stateError(
          "PROVIDER_ACCOUNTING_NOT_CONFIGURED",
          "provider accounting policy is not configured",
        );
      }
      const existing = this.#getProviderTransmission(
        reservation.transmissionId,
      );
      if (existing !== undefined) {
        if (!immutableProviderTransmissionMatches(existing, reservation)) {
          throw stateError(
            "PROVIDER_TRANSMISSION_CONFLICT",
            "provider transmission identity conflicts with prior request",
          );
        }
        this.database.exec("COMMIT");
        return publicProviderTransmission(existing);
      }
      const ordinalOwner = this.database
        .prepare(
          `SELECT transmission_id
           FROM provider_transmissions
           WHERE project_id=? AND job_id=? AND transmission_ordinal=?`,
        )
        .get(
          reservation.projectId,
          reservation.jobId,
          reservation.transmissionOrdinal,
        );
      if (ordinalOwner !== undefined) {
        throw stateError(
          "PROVIDER_TRANSMISSION_ORDINAL_CONFLICT",
          "provider transmission ordinal is already occupied",
        );
      }

      const aggregate = this.#getProviderTransmissionUsage(
        reservation.projectId,
        reservation.jobId,
      );
      if (aggregate.call_count >= limit.maximum_provider_calls) {
        throw stateError(
          "PROVIDER_CALL_LIMIT_EXCEEDED",
          "provider job call limit is exhausted",
        );
      }
      const proposedInput =
        BigInt(aggregate.input_tokens) +
        BigInt(reservation.estimatedInputTokens);
      const proposedOutput =
        BigInt(aggregate.output_tokens) +
        BigInt(reservation.estimatedOutputTokens);
      const proposedTotal = proposedInput + proposedOutput;
      if (
        proposedInput > BigInt(limit.maximum_input_tokens) ||
        BigInt(aggregate.cached_input_tokens) >
          BigInt(limit.maximum_cached_input_tokens) ||
        proposedOutput > BigInt(limit.maximum_output_tokens_total) ||
        proposedTotal > BigInt(limit.maximum_total_tokens)
      ) {
        throw stateError(
          "PROVIDER_TOKEN_LIMIT_EXCEEDED",
          "provider job token limit would be exceeded: " +
            `input=${proposedInput}/${limit.maximum_input_tokens} ` +
            `output=${proposedOutput}/${limit.maximum_output_tokens_total} ` +
            `total=${proposedTotal}/${limit.maximum_total_tokens}`,
        );
      }
      const jobCumulativeCost =
        BigInt(aggregate.spent_nano_usd) +
        BigInt(aggregate.reserved_nano_usd) +
        BigInt(reservation.estimatedNanoUsd);
      if (jobCumulativeCost > BigInt(reservation.maximumEstimatedNanoUsd)) {
        throw stateError(
          "JOB_COST_BUDGET_EXCEEDED",
          "provider job declared cost ceiling would be exceeded",
        );
      }
      const cumulativeCost =
        BigInt(budget.spent_nano_usd) +
        BigInt(budget.reserved_nano_usd) +
        BigInt(reservation.estimatedNanoUsd);
      if (cumulativeCost > BigInt(budget.ceiling_nano_usd)) {
        throw stateError(
          "COST_BUDGET_EXCEEDED",
          "project transmission budget would be exceeded",
        );
      }
      const nextReserved = safeNanoUsdAdd(
        budget.reserved_nano_usd,
        reservation.estimatedNanoUsd,
      );
      const budgetUpdate = this.database
        .prepare(
          `UPDATE transmission_project_budgets
           SET reserved_nano_usd=?,updated_at_ms=?
           WHERE project_id=?
             AND spent_nano_usd=?
             AND reserved_nano_usd=?
             AND pricing_version=?`,
        )
        .run(
          nextReserved,
          now,
          reservation.projectId,
          budget.spent_nano_usd,
          budget.reserved_nano_usd,
          budget.pricing_version,
        );
      if (budgetUpdate.changes !== 1) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "project transmission budget changed during reservation",
        );
      }
      this.database
        .prepare(
          `INSERT INTO provider_transmissions
             (transmission_id,project_id,job_id,origin_id,transmission_ordinal,
              attempt_id,route,provider,model,service_tier,reasoning_effort,
              pricing_version,state,reserved_nano_usd,actual_nano_usd,
              estimated_input_tokens,estimated_output_tokens,input_tokens,
              cached_input_tokens,output_tokens,total_tokens,created_at_ms,
              transmitted_at_ms,finished_at_ms,updated_at_ms)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'TRANSMITTING',?,NULL,?,?,NULL,NULL,
                   NULL,NULL,?,?,NULL,?)`,
        )
        .run(
          reservation.transmissionId,
          reservation.projectId,
          reservation.jobId,
          reservation.originId,
          reservation.transmissionOrdinal,
          reservation.attemptId,
          reservation.route,
          reservation.provider,
          reservation.model,
          reservation.serviceTier,
          reservation.reasoningEffort,
          reservation.pricingVersion,
          reservation.estimatedNanoUsd,
          reservation.estimatedInputTokens,
          reservation.estimatedOutputTokens,
          now,
          now,
          now,
        );
      const opened = this.#getProviderTransmission(
        reservation.transmissionId,
      );
      this.database.exec("COMMIT");
      return publicProviderTransmission(opened);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  reconcileProviderTransmission(request) {
    this.#requireCandidateTransmissionCostWritable();
    const reconciliation =
      captureProviderTransmissionReconciliationRequest(request);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const now = requireNow(this.now());
      const transmission = this.#getProviderTransmission(
        reconciliation.transmissionId,
      );
      if (transmission === undefined) {
        throw stateError(
          "PROVIDER_TRANSMISSION_NOT_FOUND",
          "provider transmission was not found",
        );
      }
      if (
        transmission.project_id !== reconciliation.projectId ||
        transmission.origin_id !== reconciliation.originId
      ) {
        throw stateError(
          "NOT_FOUND_OR_NOT_OWNED",
          "provider transmission was not found",
        );
      }
      this.#assertOriginOwnsProject(
        reconciliation.originId,
        reconciliation.projectId,
      );
      this.#requireCandidateJobOwnership(
        reconciliation.originId,
        reconciliation.projectId,
        transmission.job_id,
      );
      if (transmission.pricing_version !== reconciliation.pricingVersion) {
        throw stateError(
          "PRICING_VERSION_MISMATCH",
          "provider transmission pricing version does not match",
        );
      }
      if (["RECONCILED", "RELEASED"].includes(transmission.state)) {
        if (!providerReconciliationMatches(transmission, reconciliation)) {
          throw stateError(
            "PROVIDER_RECONCILIATION_CONFLICT",
            "terminal provider reconciliation conflicts with prior outcome",
          );
        }
        this.database.exec("COMMIT");
        return publicProviderTransmission(transmission);
      }
      if (
        transmission.state === "UNKNOWN" &&
        reconciliation.outcome === "UNKNOWN"
      ) {
        this.database.exec("COMMIT");
        return publicProviderTransmission(transmission);
      }
      if (!["TRANSMITTING", "UNKNOWN"].includes(transmission.state)) {
        throw stateError(
          "PROVIDER_RECONCILIATION_CONFLICT",
          "provider transmission is not reconcilable",
        );
      }
      const budget = this.#getTransmissionProjectBudget(
        reconciliation.projectId,
      );
      const limit = this.#getProviderJobLimit(
        reconciliation.projectId,
        transmission.job_id,
      );
      if (budget === undefined || limit === undefined) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "provider accounting policy is missing",
        );
      }
      if (reconciliation.outcome === "UNKNOWN") {
        const unknownUpdate = this.database
          .prepare(
            `UPDATE provider_transmissions
             SET state='UNKNOWN',finished_at_ms=?,updated_at_ms=?
             WHERE transmission_id=? AND state='TRANSMITTING'`,
          )
          .run(now, now, reconciliation.transmissionId);
        if (unknownUpdate.changes !== 1) {
          throw stateError(
            "PROVIDER_RECONCILIATION_CONFLICT",
            "provider transmission cannot transition to UNKNOWN",
          );
        }
        const budgetTouch = this.database
          .prepare(
            `UPDATE transmission_project_budgets
             SET updated_at_ms=?
             WHERE project_id=? AND spent_nano_usd=? AND reserved_nano_usd=?`,
          )
          .run(
            now,
            reconciliation.projectId,
            budget.spent_nano_usd,
            budget.reserved_nano_usd,
          );
        if (budgetTouch.changes !== 1) {
          throw stateError(
            "COST_ACCOUNTING_CORRUPT",
            "project transmission budget changed during UNKNOWN preservation",
          );
        }
        const unknown = this.#getProviderTransmission(
          reconciliation.transmissionId,
        );
        this.database.exec("COMMIT");
        return publicProviderTransmission(unknown);
      }

      const nextReserved =
        budget.reserved_nano_usd - transmission.reserved_nano_usd;
      if (!Number.isSafeInteger(nextReserved) || nextReserved < 0) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "project transmission reservation aggregate is invalid",
        );
      }
      let nextSpent = budget.spent_nano_usd;
      if (reconciliation.outcome === "RECONCILED") {
        if (reconciliation.actualNanoUsd > transmission.reserved_nano_usd) {
          throw stateError(
            "PROVIDER_COST_ESTIMATE_EXCEEDED",
            "actual provider cost exceeded its reservation",
          );
        }
        const aggregate = this.#getProviderTransmissionUsage(
          reconciliation.projectId,
          transmission.job_id,
          reconciliation.transmissionId,
        );
        const proposedInput =
          BigInt(aggregate.input_tokens) +
          BigInt(reconciliation.inputTokens);
        const proposedCached =
          BigInt(aggregate.cached_input_tokens) +
          BigInt(reconciliation.cachedInputTokens);
        const proposedOutput =
          BigInt(aggregate.output_tokens) +
          BigInt(reconciliation.outputTokens);
        const proposedTotal =
          BigInt(aggregate.total_tokens) +
          BigInt(reconciliation.totalTokens);
        if (
          proposedInput > BigInt(limit.maximum_input_tokens) ||
          proposedCached > BigInt(limit.maximum_cached_input_tokens) ||
          proposedOutput > BigInt(limit.maximum_output_tokens_total) ||
          proposedTotal > BigInt(limit.maximum_total_tokens)
        ) {
          throw stateError(
            "PROVIDER_TOKEN_LIMIT_EXCEEDED",
            "reconciled provider usage exceeds the frozen job limit",
          );
        }
        nextSpent = safeNanoUsdAdd(
          budget.spent_nano_usd,
          reconciliation.actualNanoUsd,
        );
      }
      if (
        BigInt(nextSpent) + BigInt(nextReserved) >
        BigInt(budget.ceiling_nano_usd)
      ) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "reconciled project transmission budget exceeds its ceiling",
        );
      }
      const budgetUpdate = this.database
        .prepare(
          `UPDATE transmission_project_budgets
           SET spent_nano_usd=?,reserved_nano_usd=?,updated_at_ms=?
           WHERE project_id=?
             AND spent_nano_usd=?
             AND reserved_nano_usd=?
             AND pricing_version=?`,
        )
        .run(
          nextSpent,
          nextReserved,
          now,
          reconciliation.projectId,
          budget.spent_nano_usd,
          budget.reserved_nano_usd,
          budget.pricing_version,
        );
      if (budgetUpdate.changes !== 1) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "project transmission budget changed during reconciliation",
        );
      }
      const rowUpdate =
        reconciliation.outcome === "RECONCILED"
          ? this.database
              .prepare(
                `UPDATE provider_transmissions
                 SET state='RECONCILED',actual_nano_usd=?,input_tokens=?,
                     cached_input_tokens=?,output_tokens=?,total_tokens=?,
                     finished_at_ms=?,updated_at_ms=?
                 WHERE transmission_id=? AND state IN ('TRANSMITTING','UNKNOWN')`,
              )
              .run(
                reconciliation.actualNanoUsd,
                reconciliation.inputTokens,
                reconciliation.cachedInputTokens,
                reconciliation.outputTokens,
                reconciliation.totalTokens,
                now,
                now,
                reconciliation.transmissionId,
              )
          : this.database
              .prepare(
                `UPDATE provider_transmissions
                 SET state='RELEASED',actual_nano_usd=0,input_tokens=NULL,
                     cached_input_tokens=NULL,output_tokens=NULL,total_tokens=NULL,
                     finished_at_ms=?,updated_at_ms=?
                 WHERE transmission_id=? AND state IN ('TRANSMITTING','UNKNOWN')`,
              )
              .run(now, now, reconciliation.transmissionId);
      if (rowUpdate.changes !== 1) {
        throw stateError(
          "PROVIDER_RECONCILIATION_CONFLICT",
          "provider transmission changed during reconciliation",
        );
      }
      const reconciled = this.#getProviderTransmission(
        reconciliation.transmissionId,
      );
      this.database.exec("COMMIT");
      return publicProviderTransmission(reconciled);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  getProviderAccountingSnapshot(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId", "originId", "jobId"],
      undefined,
      "provider accounting snapshot request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    const originId = requireSafeInteger(
      captured.originId,
      "originId must be a positive safe integer",
      1,
    );
    const jobId = requireCostText(captured.jobId, "jobId", 256);
    this.database.exec("BEGIN");
    try {
      this.#assertOriginOwnsProject(originId, projectId);
      this.#requireCandidateJobOwnership(originId, projectId, jobId);
      const budget = this.#getTransmissionProjectBudget(projectId);
      const limit = this.#getProviderJobLimit(projectId, jobId);
      if (budget === undefined || limit === undefined) {
        throw stateError(
          "PROVIDER_ACCOUNTING_NOT_CONFIGURED",
          "provider accounting policy is not configured",
        );
      }
      const counts = this.#getProviderTransmissionCounts(projectId, jobId);
      this.database.exec("COMMIT");
      return publicProviderAccountingSnapshot(budget, limit, counts);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  getActivationQuiescenceSnapshot(projectId) {
    this.#requireCandidateTransmissionCostWritable();
    if (this.getCandidateStoreSchemaVersion() !== CANDIDATE_STORE_SCHEMA_VERSION) {
      throw stateError(
        "ACTIVATION_PREFLIGHT_UNAVAILABLE",
        "activation preflight requires candidate schema v5",
      );
    }
    const exactProjectId = requireCostProjectId(projectId);
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN");
    try {
      const projectCount = this.database
        .prepare("SELECT COUNT(*) AS count FROM projects WHERE project_id=?")
        .get(exactProjectId).count;
      if (projectCount !== 1) {
        throw stateError(
          "ACTIVATION_PROJECT_NOT_FOUND",
          "activation preflight project is unavailable",
        );
      }
      const capturedAtMs = requireNow(this.now());
      const jobs = this.database
        .prepare(
          `WITH latest AS (
             SELECT generation.*
             FROM generations AS generation
             JOIN (
               SELECT job_id,MAX(generation) AS generation
               FROM generations
               GROUP BY job_id
             ) AS newest
               ON newest.job_id=generation.job_id
              AND newest.generation=generation.generation
             JOIN logical_jobs AS job ON job.job_id=generation.job_id
             WHERE job.project_id=?
           )
           SELECT
             COUNT(*) AS total,
             COALESCE(SUM(
               CASE WHEN state IN ('SUCCEEDED','FAILED','CANCELED','QUARANTINED')
                 THEN 1 ELSE 0 END
             ),0) AS terminal,
             COALESCE(SUM(
               CASE WHEN state IN ('QUEUED','RUNNING','VALIDATING')
                 THEN 1 ELSE 0 END
             ),0) AS nonterminal
           FROM latest`,
        )
        .get(exactProjectId);
      const attempts = this.database
        .prepare(
          `SELECT
             COUNT(*) AS total,
             COALESCE(SUM(CASE WHEN attempt.state='RUNNING' THEN 0 ELSE 1 END),0)
               AS terminal,
             COALESCE(SUM(CASE WHEN attempt.state='RUNNING' THEN 1 ELSE 0 END),0)
               AS nonterminal
           FROM attempts AS attempt
           JOIN logical_jobs AS job ON job.job_id=attempt.job_id
           WHERE job.project_id=?`,
        )
        .get(exactProjectId);
      const leaseOwners = this.database
        .prepare(
          `SELECT lease.job_id,lease.generation,lease.attempt_id,lease.worker_id,
                  lease.epoch,lease.heartbeat_at_ms,lease.expires_at_ms
           FROM leases AS lease
           JOIN logical_jobs AS job ON job.job_id=lease.job_id
           WHERE job.project_id=?
           ORDER BY lease.job_id,lease.generation,lease.attempt_id,lease.epoch`,
        )
        .all(exactProjectId)
        .map((lease) =>
          Object.freeze({
            jobId: lease.job_id,
            generation: lease.generation,
            attemptId: lease.attempt_id,
            workerId: lease.worker_id,
            epoch: lease.epoch,
            heartbeatAtMs: lease.heartbeat_at_ms,
            expiresAtMs: lease.expires_at_ms,
            current: lease.expires_at_ms >= capturedAtMs,
          }),
        );
      const writerLockOwners = this.database
        .prepare(
          `SELECT origin_id,owner_job_id,owner_generation,owner_lease_epoch,
                  fencing_token,acquired_at_ms,expires_at_ms
           FROM writer_locks
           WHERE project_id=?
           ORDER BY fencing_token`,
        )
        .all(exactProjectId)
        .map((writer) =>
          Object.freeze({
            originId: writer.origin_id,
            jobId: writer.owner_job_id,
            generation: writer.owner_generation,
            leaseEpoch: writer.owner_lease_epoch,
            fencingToken: writer.fencing_token,
            acquiredAtMs: writer.acquired_at_ms,
            expiresAtMs: writer.expires_at_ms,
            current: writer.expires_at_ms >= capturedAtMs,
          }),
        );
      const workerCapacity = this.database
        .prepare(
          `WITH latest AS (
             SELECT generation.*
             FROM generations AS generation
             JOIN (
               SELECT job_id,MAX(generation) AS generation
               FROM generations
               GROUP BY job_id
             ) AS newest
               ON newest.job_id=generation.job_id
              AND newest.generation=generation.generation
             JOIN logical_jobs AS job ON job.job_id=generation.job_id
             WHERE job.project_id=?
           )
           SELECT
             COALESCE(SUM(
               CASE WHEN role='READER' AND state IN ('RUNNING','VALIDATING')
                 THEN 1 ELSE 0 END
             ),0) AS active_reads,
             COALESCE(SUM(
               CASE WHEN role='WRITER' AND state IN ('RUNNING','VALIDATING')
                 THEN 1 ELSE 0 END
             ),0) AS active_writes,
             COALESCE(SUM(CASE WHEN state='QUEUED' THEN 1 ELSE 0 END),0)
               AS queued
           FROM latest`,
        )
        .get(exactProjectId);
      const headCapacity = this.database
        .prepare(
          `SELECT
             (SELECT COUNT(*) FROM (
               SELECT head_run_id FROM head_runs
               WHERE project_id=? AND run_state IN ('RUNNING')
               UNION
               SELECT head_run_id FROM head_producer_attempts
               WHERE project_id=? AND producer_state IN ('CLAIMED','RUNNING')
             )) AS active_heads,
             (SELECT COUNT(*) FROM (
               SELECT head_run_id FROM head_runs
               WHERE project_id=? AND run_state='QUEUED'
               UNION
               SELECT head_run_id FROM head_producer_attempts
               WHERE project_id=? AND producer_state='QUEUED'
             )) AS queued_heads`,
        )
        .get(exactProjectId, exactProjectId, exactProjectId, exactProjectId);
      const legacyReservations = this.database
        .prepare(
          `SELECT
             COALESCE(SUM(CASE WHEN state='OPEN' THEN 1 ELSE 0 END),0)
               AS open_count,
             COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
               AS unknown_count,
             COALESCE(SUM(
               CASE WHEN state IN ('OPEN','UNKNOWN') THEN reserved_nano_usd ELSE 0 END
             ),0) AS reserved_nano_usd
           FROM cost_reservations
           WHERE project_id=?`,
        )
        .get(exactProjectId);
      const transmissions = this.database
        .prepare(
          `SELECT
             COUNT(*) AS total,
             COALESCE(SUM(CASE WHEN state='RECONCILED' THEN 1 ELSE 0 END),0)
               AS reconciled,
             COALESCE(SUM(CASE WHEN state='RELEASED' THEN 1 ELSE 0 END),0)
               AS released,
             COALESCE(SUM(
               CASE WHEN state IN ('RESERVED','TRANSMITTING') THEN 1 ELSE 0 END
             ),0) AS active,
             COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
               AS unknown,
             COALESCE(SUM(
               CASE WHEN state='RECONCILED' THEN actual_nano_usd ELSE 0 END
             ),0) AS aggregate_spent_nano_usd,
             COALESCE(SUM(
               CASE WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
                 THEN reserved_nano_usd ELSE 0 END
             ),0) AS aggregate_reserved_nano_usd
           FROM provider_transmissions
           WHERE project_id=?`,
        )
        .get(exactProjectId);
      const budget = this.#getTransmissionProjectBudget(exactProjectId);
      const accounting = Object.freeze({
        configured: budget !== undefined,
        pricingVersion: budget?.pricing_version ?? null,
        ceilingNanoUsd: budget?.ceiling_nano_usd ?? null,
        spentNanoUsd: budget?.spent_nano_usd ?? 0,
        reservedNanoUsd: budget?.reserved_nano_usd ?? 0,
        aggregateSpentNanoUsd: transmissions.aggregate_spent_nano_usd,
        aggregateReservedNanoUsd: transmissions.aggregate_reserved_nano_usd,
        consistent:
          budget !== undefined &&
          budget.spent_nano_usd === transmissions.aggregate_spent_nano_usd &&
          budget.reserved_nano_usd === transmissions.aggregate_reserved_nano_usd,
      });
      const snapshot = Object.freeze({
        schemaVersion: 1,
        projectId: exactProjectId,
        storeSchemaVersion: CANDIDATE_STORE_SCHEMA_VERSION,
        capturedAtMs,
        jobs: Object.freeze({ ...jobs }),
        attempts: Object.freeze({ ...attempts }),
        leases: Object.freeze({
          count: leaseOwners.length,
          owners: Object.freeze(leaseOwners),
        }),
        writerLocks: Object.freeze({
          count: writerLockOwners.length,
          owners: Object.freeze(writerLockOwners),
        }),
        capacity: Object.freeze({
          activeHeads: headCapacity.active_heads,
          activeReads: workerCapacity.active_reads,
          activeWrites: workerCapacity.active_writes,
          queued: workerCapacity.queued + headCapacity.queued_heads,
        }),
        reservations: Object.freeze({
          openCount: legacyReservations.open_count + transmissions.active,
          unknownCount: legacyReservations.unknown_count + transmissions.unknown,
          openReservedNanoUsd:
            legacyReservations.reserved_nano_usd +
            transmissions.aggregate_reserved_nano_usd,
        }),
        transmissions: Object.freeze({
          total: transmissions.total,
          reconciled: transmissions.reconciled,
          released: transmissions.released,
          active: transmissions.active,
          unknown: transmissions.unknown,
          aggregateSpentNanoUsd: transmissions.aggregate_spent_nano_usd,
          aggregateReservedNanoUsd: transmissions.aggregate_reserved_nano_usd,
        }),
        accounting,
      });
      const reasons = [];
      if (snapshot.jobs.nonterminal !== 0) reasons.push("NONTERMINAL_JOBS");
      if (snapshot.attempts.nonterminal !== 0) reasons.push("NONTERMINAL_ATTEMPTS");
      if (snapshot.leases.count !== 0) reasons.push("LEASES_PRESENT");
      if (snapshot.leases.owners.some((owner) => !owner.current)) {
        reasons.push("STALE_LEASES_PRESENT");
      }
      if (snapshot.writerLocks.count !== 0) reasons.push("WRITER_LOCKS_PRESENT");
      if (snapshot.writerLocks.owners.some((owner) => !owner.current)) {
        reasons.push("STALE_WRITER_LOCKS_PRESENT");
      }
      if (snapshot.capacity.activeReads !== 0) reasons.push("ACTIVE_READS");
      if (snapshot.capacity.activeWrites !== 0) reasons.push("ACTIVE_WRITES");
      if (snapshot.capacity.activeHeads !== 0) reasons.push("ACTIVE_HEADS");
      if (snapshot.capacity.queued !== 0) reasons.push("QUEUE_NONEMPTY");
      if (snapshot.reservations.openCount !== 0) reasons.push("OPEN_RESERVATIONS");
      if (snapshot.reservations.unknownCount !== 0) {
        reasons.push("UNKNOWN_RESERVATIONS");
      }
      if (snapshot.transmissions.active !== 0) reasons.push("ACTIVE_TRANSMISSIONS");
      if (snapshot.transmissions.unknown !== 0) reasons.push("UNKNOWN_TRANSMISSIONS");
      if (!snapshot.accounting.configured) reasons.push("ACCOUNTING_UNCONFIGURED");
      if (!snapshot.accounting.consistent) reasons.push("ACCOUNTING_INCONSISTENT");
      if (snapshot.accounting.reservedNanoUsd !== 0) {
        reasons.push("ACCOUNTING_RESERVED_NONZERO");
      }
      const frozenReasons = Object.freeze(reasons);
      const precondition = Object.freeze({
        schemaVersion: snapshot.schemaVersion,
        projectId: snapshot.projectId,
        storeSchemaVersion: snapshot.storeSchemaVersion,
        jobs: snapshot.jobs,
        attempts: snapshot.attempts,
        leases: snapshot.leases,
        writerLocks: snapshot.writerLocks,
        capacity: snapshot.capacity,
        reservations: snapshot.reservations,
        transmissions: snapshot.transmissions,
        accounting: snapshot.accounting,
        reasons: frozenReasons,
      });
      const result = Object.freeze({
        ...snapshot,
        quiescent: frozenReasons.length === 0,
        reasons: frozenReasons,
        preconditionHash: candidateSha256(
          `deepluna-activation-quiescence-v1\0${canonicalPayloadJson(precondition)}`,
        ),
      });
      if (ownsTransaction) this.database.exec("COMMIT");
      return result;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    }
  }

  getCandidateAccountingHealth(request) {
    this.#requireCandidateTransmissionCostWritable();
    if (this.getCandidateStoreSchemaVersion() !== CANDIDATE_STORE_SCHEMA_VERSION) {
      throw stateError(
        "ACCOUNTING_HEALTH_UNAVAILABLE",
        "accounting health requires candidate schema v5",
      );
    }
    const health = captureCandidateAccountingHealthRequest(request);
    const ownsTransaction = this.#protocolRequestDepth === 0;
    if (ownsTransaction) this.database.exec("BEGIN");
    try {
      const budget = this.#getTransmissionProjectBudget(health.projectId);
      const aggregate = this.database
        .prepare(
          `SELECT
             COALESCE(SUM(
               CASE WHEN state='RECONCILED' THEN actual_nano_usd ELSE 0 END
             ),0) AS spent_nano_usd,
             COALESCE(SUM(
               CASE
                 WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
                   THEN reserved_nano_usd
                 ELSE 0
               END
             ),0) AS reserved_nano_usd,
             COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
               AS unknown_transmissions,
             COALESCE(SUM(
               CASE WHEN state IN ('RESERVED','TRANSMITTING') THEN 1 ELSE 0 END
             ),0) AS active_transmissions
           FROM provider_transmissions
           WHERE project_id=?`,
        )
        .get(health.projectId);
      const snapshot =
        budget === undefined
          ? Object.freeze({
              projectId: health.projectId,
              configured: false,
              pricingVersion: null,
              policyMatches: false,
              ceilingMatches: false,
              aggregatesConsistent:
                aggregate.spent_nano_usd === 0 &&
                aggregate.reserved_nano_usd === 0,
              ceilingNanoUsd: null,
              spentNanoUsd: 0,
              reservedNanoUsd: 0,
              aggregateSpentNanoUsd: aggregate.spent_nano_usd,
              aggregateReservedNanoUsd: aggregate.reserved_nano_usd,
              unknownTransmissions: aggregate.unknown_transmissions,
              activeTransmissions: aggregate.active_transmissions,
            })
          : Object.freeze({
              projectId: health.projectId,
              configured: true,
              pricingVersion: budget.pricing_version,
              policyMatches:
                budget.pricing_version === health.expectedPricingVersion,
              ceilingMatches:
                budget.ceiling_nano_usd === health.expectedCeilingNanoUsd,
              aggregatesConsistent:
                budget.spent_nano_usd === aggregate.spent_nano_usd &&
                budget.reserved_nano_usd === aggregate.reserved_nano_usd,
              ceilingNanoUsd: budget.ceiling_nano_usd,
              spentNanoUsd: budget.spent_nano_usd,
              reservedNanoUsd: budget.reserved_nano_usd,
              aggregateSpentNanoUsd: aggregate.spent_nano_usd,
              aggregateReservedNanoUsd: aggregate.reserved_nano_usd,
              unknownTransmissions: aggregate.unknown_transmissions,
              activeTransmissions: aggregate.active_transmissions,
            });
      if (ownsTransaction) this.database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      if (!ownsTransaction) throw error;
      this.#rollbackTransaction(error);
    }
  }

  previewCandidateAccountingPolicyTransition(request) {
    this.#requireCandidateTransmissionCostWritable();
    if (this.getCandidateStoreSchemaVersion() !== CANDIDATE_STORE_SCHEMA_VERSION) {
      throw stateError(
        "ACCOUNTING_TRANSITION_UNAVAILABLE",
        "accounting policy transitions require candidate schema v5",
      );
    }
    const transition = captureAccountingPolicyTransitionPreviewRequest(request);
    this.#assertCandidateAccountingPolicyTransitionPair(transition);
    this.database.exec("BEGIN");
    try {
      const snapshot = this.#candidateAccountingPolicyTransitionSnapshot(
        transition,
      );
      this.database.exec("COMMIT");
      return snapshot;
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  transitionCandidateAccountingPolicy(request) {
    this.#requireCandidateTransmissionCostWritable();
    if (this.getCandidateStoreSchemaVersion() !== CANDIDATE_STORE_SCHEMA_VERSION) {
      throw stateError(
        "ACCOUNTING_TRANSITION_UNAVAILABLE",
        "accounting policy transitions require candidate schema v5",
      );
    }
    const transition = captureAccountingPolicyTransitionRequest(request);
    this.#assertCandidateAccountingPolicyTransitionPair(transition);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const existing = this.database
        .prepare(
          `SELECT * FROM accounting_policy_transitions
           WHERE project_id=?
             AND source_pricing_version=?
             AND target_pricing_version=?`,
        )
        .get(
          transition.projectId,
          transition.sourcePricingVersion,
          transition.targetPricingVersion,
        );
      if (existing !== undefined) {
        if (
          existing.transition_fingerprint !== transition.transitionFingerprint ||
          existing.ceiling_before_nano_usd !== transition.ceilingNanoUsd ||
          existing.ceiling_after_nano_usd !== transition.ceilingNanoUsd
        ) {
          throw stateError(
            "ACCOUNTING_TRANSITION_CONFLICT",
            "accounting policy transition conflicts with its durable receipt",
          );
        }
        this.database.exec("COMMIT");
        return publicAccountingPolicyTransition(existing);
      }

      const snapshot = this.#candidateAccountingPolicyTransitionSnapshot(
        transition,
      );
      if (
        snapshot.pricingVersion !== transition.sourcePricingVersion ||
        snapshot.ceilingNanoUsd !== transition.ceilingNanoUsd
      ) {
        throw stateError(
          "ACCOUNTING_TRANSITION_POLICY_REJECTED",
          "accounting policy transition does not match the durable budget",
        );
      }
      if (
        !snapshot.aggregatesConsistent ||
        snapshot.reservedNanoUsd !== 0 ||
        snapshot.activeTransmissions !== 0 ||
        snapshot.unknownTransmissions !== 0 ||
        snapshot.activeWorkers !== 0 ||
        snapshot.activeHeads !== 0
      ) {
        throw stateError(
          "ACCOUNTING_TRANSITION_UNSAFE",
          "accounting policy transition requires a consistent quiescent project",
        );
      }
      if (snapshot.transitionFingerprint !== transition.transitionFingerprint) {
        throw stateError(
          "ACCOUNTING_TRANSITION_FINGERPRINT_MISMATCH",
          "accounting policy transition preconditions changed",
        );
      }

      const now = requireNow(this.now());
      const transitionId =
        `APT-${candidateSha256(
          `deepluna-accounting-transition-id-v1\0${transition.projectId}` +
          `\0${transition.transitionFingerprint}`,
        ).slice(0, 32)}`;
      this.database
        .prepare(
          `INSERT INTO accounting_policy_transitions
             (transition_id,project_id,source_pricing_version,
              target_pricing_version,transition_fingerprint,
              ceiling_before_nano_usd,ceiling_after_nano_usd,
              spent_before_nano_usd,spent_after_nano_usd,
              reserved_before_nano_usd,reserved_after_nano_usd,
              reconciled_transmissions,released_transmissions,
              active_transmissions,unknown_transmissions,
              active_workers,active_heads,precondition_hash,created_at_ms)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        )
        .run(
          transitionId,
          transition.projectId,
          transition.sourcePricingVersion,
          transition.targetPricingVersion,
          transition.transitionFingerprint,
          snapshot.ceilingNanoUsd,
          snapshot.ceilingNanoUsd,
          snapshot.spentNanoUsd,
          snapshot.spentNanoUsd,
          snapshot.reservedNanoUsd,
          snapshot.reservedNanoUsd,
          snapshot.reconciledTransmissions,
          snapshot.releasedTransmissions,
          snapshot.activeTransmissions,
          snapshot.unknownTransmissions,
          snapshot.activeWorkers,
          snapshot.activeHeads,
          snapshot.preconditionHash,
          now,
        );
      const updated = this.database
        .prepare(
          `UPDATE transmission_project_budgets
           SET pricing_version=?,updated_at_ms=?
           WHERE project_id=?
             AND pricing_version=?
             AND ceiling_nano_usd=?
             AND spent_nano_usd=?
             AND reserved_nano_usd=?`,
        )
        .run(
          transition.targetPricingVersion,
          now,
          transition.projectId,
          transition.sourcePricingVersion,
          snapshot.ceilingNanoUsd,
          snapshot.spentNanoUsd,
          snapshot.reservedNanoUsd,
        );
      if (updated.changes !== 1) {
        throw stateError(
          "ACCOUNTING_TRANSITION_CONFLICT",
          "accounting policy changed during its transition",
        );
      }
      const receipt = this.database
        .prepare(
          "SELECT * FROM accounting_policy_transitions WHERE transition_id=?",
        )
        .get(transitionId);
      this.database.exec("COMMIT");
      return publicAccountingPolicyTransition(receipt);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  recoverUncertainProviderTransmissions(request) {
    this.#requireCandidateTransmissionCostWritable();
    const captured = captureCandidateDataObject(
      request,
      ["projectId"],
      undefined,
      "provider transmission recovery request",
    );
    const projectId = requireCostProjectId(captured.projectId);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const budget = this.#getTransmissionProjectBudget(projectId);
      if (budget === undefined) {
        throw stateError(
          "PROVIDER_ACCOUNTING_NOT_CONFIGURED",
          "provider accounting policy is not configured",
        );
      }
      this.#assertProviderCostAggregates(budget);
      const now = requireNow(this.now());
      const recovered = this.database
        .prepare(
          `UPDATE provider_transmissions
           SET state='UNKNOWN',
               transmitted_at_ms=COALESCE(transmitted_at_ms,?),
               finished_at_ms=?,
               updated_at_ms=?
           WHERE project_id=? AND state IN ('RESERVED','TRANSMITTING')`,
        )
        .run(now, now, now, projectId);
      if (recovered.changes > 0) {
        const touched = this.database
          .prepare(
            `UPDATE transmission_project_budgets
             SET updated_at_ms=?
             WHERE project_id=?
               AND spent_nano_usd=?
               AND reserved_nano_usd=?`,
          )
          .run(
            now,
            projectId,
            budget.spent_nano_usd,
            budget.reserved_nano_usd,
          );
        if (touched.changes !== 1) {
          throw stateError(
            "COST_ACCOUNTING_CORRUPT",
            "project transmission budget changed during recovery",
          );
        }
      }
      const currentBudget = this.#getTransmissionProjectBudget(projectId);
      this.#assertProviderCostAggregates(currentBudget);
      this.database.exec("COMMIT");
      return Object.freeze({
        projectId,
        recoveredCount: recovered.changes,
        spentNanoUsd: currentBudget.spent_nano_usd,
        reservedNanoUsd: currentBudget.reserved_nano_usd,
        recoveredAtMs: now,
      });
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  reserveCost(request) {
    this.#requireCandidateLegacyCostWritable();
    const reservation = captureCostReservationRequest(request);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      this.#assertOriginOwnsProject(
        reservation.originId,
        reservation.projectId,
      );
      const existing = this.#getCostReservation(reservation.reservationId);
      if (existing !== undefined) {
        if (existing.project_id !== reservation.projectId) {
          throw stateError(
            "PROJECT_MISMATCH",
            "cost reservation project does not match",
          );
        }
        if (existing.origin_id !== reservation.originId) {
          throw stateError(
            "ORIGIN_FORBIDDEN",
            "cost reservation belongs to another origin",
          );
        }
        if (existing.pricing_version !== reservation.pricingVersion) {
          throw stateError(
            "PRICING_VERSION_MISMATCH",
            "cost reservation pricing version does not match",
          );
        }
        if (!immutableCostReservationMatches(existing, reservation)) {
          throw stateError(
            "COST_RESERVATION_CONFLICT",
            "cost reservation identity conflicts with prior request",
          );
        }
        const establishedBudget = this.#getCostBudget(reservation.projectId);
        this.#assertCostBudgetIdentity(establishedBudget, reservation);
        this.database.exec("COMMIT");
        return publicCostReservation(existing);
      }

      if (reservation.estimatedNanoUsd > reservation.ceilingNanoUsd) {
        throw stateError(
          "COST_BUDGET_EXCEEDED",
          "cost budget ceiling would be exceeded",
        );
      }
      let budget = this.#getCostBudget(reservation.projectId);
      if (budget === undefined) {
        this.database
          .prepare(
            `INSERT INTO cost_budgets
               (project_id,ceiling_nano_usd,spent_nano_usd,reserved_nano_usd,
                pricing_version,updated_at_ms)
             VALUES (?,?,0,0,?,?)`,
          )
          .run(
            reservation.projectId,
            reservation.ceilingNanoUsd,
            reservation.pricingVersion,
            reservation.nowMs,
          );
        budget = this.#getCostBudget(reservation.projectId);
      } else {
        this.#assertCostBudgetIdentity(budget, reservation);
      }
      const cumulative =
        BigInt(budget.spent_nano_usd) +
        BigInt(budget.reserved_nano_usd) +
        BigInt(reservation.estimatedNanoUsd);
      if (cumulative > BigInt(budget.ceiling_nano_usd)) {
        throw stateError(
          "COST_BUDGET_EXCEEDED",
          "cost budget ceiling would be exceeded",
        );
      }
      const nextReserved = safeNanoUsdAdd(
        budget.reserved_nano_usd,
        reservation.estimatedNanoUsd,
      );
      const budgetUpdate = this.database
        .prepare(
          `UPDATE cost_budgets
           SET reserved_nano_usd=?,updated_at_ms=?
           WHERE project_id=?
             AND ceiling_nano_usd=?
             AND spent_nano_usd=?
             AND reserved_nano_usd=?
             AND pricing_version=?`,
        )
        .run(
          nextReserved,
          reservation.nowMs,
          reservation.projectId,
          budget.ceiling_nano_usd,
          budget.spent_nano_usd,
          budget.reserved_nano_usd,
          budget.pricing_version,
        );
      if (budgetUpdate.changes !== 1) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "cost budget changed during reservation",
        );
      }
      this.database
        .prepare(
          `INSERT INTO cost_reservations
             (reservation_id,project_id,origin_id,job_id,attempt_id,state,
              reserved_nano_usd,actual_nano_usd,pricing_version,
              created_at_ms,updated_at_ms)
           VALUES (?,?,?,?,?,'OPEN',?,NULL,?,?,?)`,
        )
        .run(
          reservation.reservationId,
          reservation.projectId,
          reservation.originId,
          reservation.jobId,
          reservation.attemptId,
          reservation.estimatedNanoUsd,
          reservation.pricingVersion,
          reservation.nowMs,
          reservation.nowMs,
        );
      const opened = this.#getCostReservation(reservation.reservationId);
      this.database.exec("COMMIT");
      return publicCostReservation(opened);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  reconcileCost(request) {
    this.#requireCandidateLegacyCostWritable();
    const reconciliation = captureCostReconciliationRequest(request);
    this.database.exec("BEGIN IMMEDIATE");
    try {
      const reservation = this.#getCostReservation(
        reconciliation.reservationId,
      );
      if (reservation === undefined) {
        throw stateError(
          "COST_RESERVATION_NOT_FOUND",
          "cost reservation was not found",
        );
      }
      if (reservation.project_id !== reconciliation.projectId) {
        throw stateError(
          "PROJECT_MISMATCH",
          "cost reservation project does not match",
        );
      }
      if (reservation.origin_id !== reconciliation.originId) {
        throw stateError(
          "ORIGIN_FORBIDDEN",
          "cost reservation belongs to another origin",
        );
      }
      this.#assertOriginOwnsProject(
        reconciliation.originId,
        reconciliation.projectId,
      );
      const budget = this.#getCostBudget(reconciliation.projectId);
      if (budget === undefined) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "cost reservation budget is missing",
        );
      }
      if (budget.pricing_version !== reservation.pricing_version) {
        throw stateError(
          "PRICING_VERSION_MISMATCH",
          "cost reservation pricing version does not match its budget",
        );
      }

      if (
        reservation.state === "RECONCILED" ||
        reservation.state === "RELEASED"
      ) {
        if (
          reservation.state !== reconciliation.outcome ||
          reservation.actual_nano_usd !== reconciliation.actualNanoUsd
        ) {
          throw stateError(
            "COST_RECONCILIATION_CONFLICT",
            "terminal cost reconciliation conflicts with prior outcome",
          );
        }
        this.database.exec("COMMIT");
        return publicCostReservation(reservation);
      }
      if (
        reservation.state === "UNKNOWN" &&
        reconciliation.outcome === "UNKNOWN"
      ) {
        this.database.exec("COMMIT");
        return publicCostReservation(reservation);
      }
      if (reconciliation.outcome === "UNKNOWN") {
        const unknownUpdate = this.database
          .prepare(
            `UPDATE cost_reservations
             SET state='UNKNOWN',updated_at_ms=?
             WHERE reservation_id=? AND state='OPEN'`,
          )
          .run(reconciliation.nowMs, reconciliation.reservationId);
        if (unknownUpdate.changes !== 1) {
          throw stateError(
            "COST_RECONCILIATION_CONFLICT",
            "cost reservation cannot transition to UNKNOWN",
          );
        }
        const unknown = this.#getCostReservation(
          reconciliation.reservationId,
        );
        this.database.exec("COMMIT");
        return publicCostReservation(unknown);
      }

      const nextReserved =
        budget.reserved_nano_usd - reservation.reserved_nano_usd;
      if (!Number.isSafeInteger(nextReserved) || nextReserved < 0) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "cost budget reservation aggregate is invalid",
        );
      }
      const nextSpent =
        reconciliation.outcome === "RECONCILED"
          ? safeNanoUsdAdd(
              budget.spent_nano_usd,
              reconciliation.actualNanoUsd,
            )
          : budget.spent_nano_usd;
      const budgetUpdate = this.database
        .prepare(
          `UPDATE cost_budgets
           SET spent_nano_usd=?,reserved_nano_usd=?,updated_at_ms=?
           WHERE project_id=?
             AND spent_nano_usd=?
             AND reserved_nano_usd=?
             AND pricing_version=?`,
        )
        .run(
          nextSpent,
          nextReserved,
          reconciliation.nowMs,
          reconciliation.projectId,
          budget.spent_nano_usd,
          budget.reserved_nano_usd,
          budget.pricing_version,
        );
      if (budgetUpdate.changes !== 1) {
        throw stateError(
          "COST_ACCOUNTING_CORRUPT",
          "cost budget changed during reconciliation",
        );
      }
      const reservationUpdate = this.database
        .prepare(
          `UPDATE cost_reservations
           SET state=?,actual_nano_usd=?,updated_at_ms=?
           WHERE reservation_id=? AND state IN ('OPEN','UNKNOWN')`,
        )
        .run(
          reconciliation.outcome,
          reconciliation.actualNanoUsd,
          reconciliation.nowMs,
          reconciliation.reservationId,
        );
      if (reservationUpdate.changes !== 1) {
        throw stateError(
          "COST_RECONCILIATION_CONFLICT",
          "cost reservation terminal transition failed",
        );
      }
      const reconciled = this.#getCostReservation(
        reconciliation.reservationId,
      );
      this.database.exec("COMMIT");
      return publicCostReservation(reconciled);
    } catch (error) {
      this.#rollbackTransaction(error);
    }
  }

  getGeneration(jobId, generation) {
    requireNonblankString(jobId, "jobId must be a nonblank string");
    requireSafeInteger(generation, "generation must be a positive safe integer", 1);
    const row = this.database
      .prepare(`${GENERATION_SELECT} WHERE g.job_id = ? AND g.generation = ?`)
      .get(jobId, generation);
    return publicGeneration(row);
  }

  close() {
    this.database.close();
  }

  #getLatestRowByIdentity(projectId, idempotencyKey) {
    return this.database
      .prepare(
        `${GENERATION_SELECT}
         JOIN logical_jobs AS j ON j.job_id = g.job_id
         WHERE j.project_id = ? AND j.idempotency_key = ?
         ORDER BY g.generation DESC
         LIMIT 1`,
       )
      .get(projectId, idempotencyKey);
  }

  #getLatestRowByJobId(jobId) {
    return this.database
      .prepare(
        `${GENERATION_SELECT}
         WHERE g.job_id = ?
         ORDER BY g.generation DESC
         LIMIT 1`,
      )
      .get(jobId);
  }

  #candidateWorkerStatusRow(originId, projectId, publicId) {
    const row = this.database
      .prepare(
        `SELECT
           claim.claim_state,
           claim.binding_id,
           binding.job_id AS producer_job_id,
           binding.generation,
           generation.state AS generation_state,
           packet.public_status,
           packet.execution_status,
           packet.evidence_verdict,
           packet.cache_hit,
           packet.canonical_json
         FROM worker_claims AS claim
         JOIN worker_bindings AS binding
           ON binding.binding_id=claim.binding_id
          AND binding.project_id=claim.project_id
         JOIN generations AS generation
           ON generation.job_id=binding.job_id
          AND generation.generation=binding.generation
         LEFT JOIN result_subjects AS subject
           ON subject.worker_binding_id=binding.binding_id
          AND subject.subject_state='NORMALIZED'
         LEFT JOIN result_packets AS packet
           ON packet.packet_hash=subject.accepted_packet_hash
         WHERE claim.public_id=?
           AND claim.origin_id=?
           AND claim.project_id=?`,
      )
      .get(publicId, originId, projectId);
    if (row === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
    const identity =
      row.canonical_json === null
        ? candidatePublicStateFromGeneration(row.generation_state)
        : Object.freeze({
            status: row.public_status,
            executionStatus: row.execution_status,
            evidenceVerdict: row.evidence_verdict,
            cacheHit: Boolean(row.cache_hit),
          });
    return Object.freeze({
      bindingId: row.binding_id,
      producerJobId: row.producer_job_id,
      generation: row.generation,
      generationState: row.generation_state,
      claimState: row.claim_state,
      canonicalJson: row.canonical_json,
      ...identity,
    });
  }

  #requireCandidateJobOwnership(originId, projectId, jobId) {
    const ownership = this.database
      .prepare(
        `SELECT 1
         FROM (
           SELECT 1
           FROM logical_job_origins
           WHERE origin_id=? AND project_id=? AND job_id=?
           UNION ALL
           SELECT 1
           FROM head_claims
           WHERE origin_id=? AND project_id=? AND public_id=?
         )
         LIMIT 1`,
      )
      .get(originId, projectId, jobId, originId, projectId, jobId);
    if (ownership === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
  }

  #candidateHeadProducerRow(projectId, producerJobId) {
    return this.database
      .prepare(
        `SELECT producer.*,run.binding_epoch,run.run_state
         FROM head_producer_attempts AS producer
         JOIN head_runs AS run
           ON run.head_run_id=producer.head_run_id
          AND run.project_id=producer.project_id
         WHERE producer.project_id=? AND producer.producer_job_id=?`,
      )
      .get(projectId, producerJobId);
  }

  #requireCandidateOriginMembership(originId, projectId) {
    const membership = this.database
      .prepare(
        `SELECT 1
         FROM origins
         WHERE origin_id=? AND project_id=?`,
      )
      .get(originId, projectId);
    if (membership === undefined) {
      throw stateError("NOT_FOUND_OR_NOT_OWNED", "resource not found");
    }
  }

  #deleteCandidateWriterLockForTerminal(jobId, generation, leaseEpoch) {
    if (!this.#candidateCostWritable) return;
    if (leaseEpoch === undefined) {
      this.database
        .prepare(
          `DELETE FROM writer_locks
           WHERE owner_job_id=? AND owner_generation=?`,
        )
        .run(jobId, generation);
      return;
    }
    this.database
      .prepare(
        `DELETE FROM writer_locks
         WHERE owner_job_id=?
           AND owner_generation=?
           AND owner_lease_epoch=?`,
      )
      .run(jobId, generation, leaseEpoch);
  }

  #requireCandidateLegacyCostWritable() {
    if (!this.#candidateLegacyCostWritable) {
      throw stateError(
        "CANDIDATE_COST_UNAVAILABLE",
        "legacy candidate cost accounting is unavailable",
      );
    }
  }

  #requireCandidateSchemaWritable() {
    if (!this.#candidateCostWritable) {
      throw stateError(
        "CANDIDATE_SCHEMA_UNAVAILABLE",
        "candidate schema operations are unavailable",
      );
    }
  }

  #requireCandidateTransmissionCostWritable() {
    if (!this.#candidateTransmissionCostWritable) {
      throw stateError(
        "CANDIDATE_TRANSMISSION_COST_UNAVAILABLE",
        "candidate per-transmission cost accounting is unavailable",
      );
    }
  }

  #requireCandidateHeadProducerWritable() {
    if (
      this.getCandidateStoreSchemaVersion() !==
      CANDIDATE_STORE_SCHEMA_VERSION
    ) {
      throw stateError(
        "CANDIDATE_HEAD_PRODUCER_UNAVAILABLE",
        "durable candidate head producers require schema v5",
      );
    }
  }

  #assertCandidateAccountingPolicyTransitionPair(transition) {
    if (
      transition.sourcePricingVersion !== "cost-policy-v7" ||
      transition.targetPricingVersion !== "cost-policy-v8"
    ) {
      throw stateError(
        "ACCOUNTING_TRANSITION_POLICY_REJECTED",
        "only the authorized cost-policy-v7 to cost-policy-v8 transition is supported",
      );
    }
  }

  #candidateAccountingPolicyTransitionSnapshot(transition) {
    const budget = this.#getTransmissionProjectBudget(transition.projectId);
    if (budget === undefined) {
      throw stateError(
        "PROVIDER_ACCOUNTING_NOT_CONFIGURED",
        "provider accounting policy is not configured",
      );
    }
    const transmissions = this.database
      .prepare(
        `SELECT
           COALESCE(SUM(CASE WHEN state='RECONCILED' THEN 1 ELSE 0 END),0)
             AS reconciled_transmissions,
           COALESCE(SUM(CASE WHEN state='RELEASED' THEN 1 ELSE 0 END),0)
             AS released_transmissions,
           COALESCE(SUM(
             CASE WHEN state IN ('RESERVED','TRANSMITTING') THEN 1 ELSE 0 END
           ),0) AS active_transmissions,
           COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
             AS unknown_transmissions,
           COALESCE(SUM(
             CASE
               WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
                 THEN reserved_nano_usd
               ELSE 0
             END
           ),0) AS aggregate_reserved_nano_usd,
           COALESCE(SUM(
             CASE WHEN state='RECONCILED' THEN actual_nano_usd ELSE 0 END
           ),0) AS aggregate_spent_nano_usd
         FROM provider_transmissions
         WHERE project_id=?`,
      )
      .get(transition.projectId);
    const activeWorkers = this.database
      .prepare(
        `SELECT COUNT(*) AS count
         FROM (
           SELECT 'generation:' || generation.job_id || ':' ||
                  CAST(generation.generation AS TEXT) AS identity
           FROM generations AS generation
           JOIN logical_jobs AS job ON job.job_id=generation.job_id
           WHERE job.project_id=?
             AND generation.state IN ('QUEUED','RUNNING','VALIDATING')
           UNION
           SELECT 'binding:' || CAST(binding.binding_id AS TEXT) AS identity
           FROM worker_bindings AS binding
           WHERE binding.project_id=? AND binding.binding_state='ACTIVE'
         )`,
      )
      .get(transition.projectId, transition.projectId).count;
    const activeHeads = this.database
      .prepare(
        `SELECT COUNT(*) AS count
         FROM (
           SELECT head_run_id
           FROM head_runs
           WHERE project_id=? AND run_state IN ('QUEUED','RUNNING')
           UNION
           SELECT head_run_id
           FROM head_producer_attempts
           WHERE project_id=?
             AND producer_state IN ('QUEUED','CLAIMED','RUNNING')
         )`,
      )
      .get(transition.projectId, transition.projectId).count;
    const precondition = Object.freeze({
      schemaVersion: 1,
      projectId: transition.projectId,
      sourcePricingVersion: transition.sourcePricingVersion,
      targetPricingVersion: transition.targetPricingVersion,
      requestedCeilingNanoUsd: transition.ceilingNanoUsd,
      pricingVersion: budget.pricing_version,
      ceilingNanoUsd: budget.ceiling_nano_usd,
      spentNanoUsd: budget.spent_nano_usd,
      reservedNanoUsd: budget.reserved_nano_usd,
      aggregateSpentNanoUsd: transmissions.aggregate_spent_nano_usd,
      aggregateReservedNanoUsd: transmissions.aggregate_reserved_nano_usd,
      reconciledTransmissions: transmissions.reconciled_transmissions,
      releasedTransmissions: transmissions.released_transmissions,
      activeTransmissions: transmissions.active_transmissions,
      unknownTransmissions: transmissions.unknown_transmissions,
      activeWorkers,
      activeHeads,
    });
    const canonicalPrecondition = canonicalPayloadJson(precondition);
    return Object.freeze({
      ...precondition,
      aggregatesConsistent:
        budget.spent_nano_usd === transmissions.aggregate_spent_nano_usd &&
        budget.reserved_nano_usd === transmissions.aggregate_reserved_nano_usd,
      preconditionHash: candidateSha256(canonicalPrecondition),
      transitionFingerprint: candidateSha256(
        `deepluna-accounting-policy-transition-v1\0${canonicalPrecondition}`,
      ),
    });
  }

  #getCostBudget(projectId) {
    return this.database
      .prepare(
        `SELECT project_id,ceiling_nano_usd,spent_nano_usd,reserved_nano_usd,
                pricing_version,updated_at_ms
         FROM cost_budgets WHERE project_id=?`,
      )
      .get(projectId);
  }

  #getCostReservation(reservationId) {
    return this.database
      .prepare(
        `SELECT reservation_id,project_id,origin_id,job_id,attempt_id,state,
                reserved_nano_usd,actual_nano_usd,pricing_version,
                created_at_ms,updated_at_ms
         FROM cost_reservations WHERE reservation_id=?`,
      )
      .get(reservationId);
  }

  #getTransmissionProjectBudget(projectId) {
    return this.database
      .prepare(
        `SELECT project_id,ceiling_nano_usd,spent_nano_usd,reserved_nano_usd,
                pricing_version,created_at_ms,updated_at_ms
         FROM transmission_project_budgets
         WHERE project_id=?`,
      )
      .get(projectId);
  }

  #getProviderJobLimit(projectId, jobId) {
    return this.database
      .prepare(
        `SELECT project_id,job_id,maximum_provider_calls,maximum_input_tokens,
                maximum_cached_input_tokens,maximum_output_tokens_total,
                maximum_total_tokens,created_at_ms,updated_at_ms
         FROM provider_job_limits
         WHERE project_id=? AND job_id=?`,
      )
      .get(projectId, jobId);
  }

  #getProviderTransmission(transmissionId) {
    return this.database
      .prepare(
        `SELECT transmission_id,project_id,job_id,origin_id,transmission_ordinal,
                attempt_id,route,provider,model,service_tier,reasoning_effort,
                pricing_version,state,reserved_nano_usd,actual_nano_usd,
                estimated_input_tokens,estimated_output_tokens,input_tokens,
                cached_input_tokens,output_tokens,total_tokens,created_at_ms,
                transmitted_at_ms,finished_at_ms,updated_at_ms
         FROM provider_transmissions
         WHERE transmission_id=?`,
      )
      .get(transmissionId);
  }

  #getProviderTransmissionCounts(projectId, jobId) {
    return this.database
      .prepare(
        `SELECT
           COUNT(*) AS transmission_count,
           COALESCE(SUM(CASE WHEN state='RECONCILED' THEN 1 ELSE 0 END),0)
             AS reconciled_count,
           COALESCE(SUM(CASE WHEN state='UNKNOWN' THEN 1 ELSE 0 END),0)
             AS unknown_count,
           COALESCE(SUM(
             CASE WHEN state IN ('RESERVED','TRANSMITTING') THEN 1 ELSE 0 END
           ),0) AS active_count,
           COALESCE(SUM(CASE WHEN state='RELEASED' THEN 1 ELSE 0 END),0)
             AS released_count
         FROM provider_transmissions
         WHERE project_id=? AND job_id=?`,
      )
      .get(projectId, jobId);
  }

  #getProviderTransmissionUsage(projectId, jobId, excludedTransmissionId = null) {
    return this.database
      .prepare(
        `SELECT
           COUNT(*) AS call_count,
           COALESCE(SUM(
             CASE
               WHEN state='RELEASED' THEN 0
               WHEN state='RECONCILED' THEN input_tokens
               ELSE estimated_input_tokens
             END
           ),0) AS input_tokens,
           COALESCE(SUM(
             CASE WHEN state='RECONCILED' THEN cached_input_tokens ELSE 0 END
           ),0) AS cached_input_tokens,
           COALESCE(SUM(
             CASE
               WHEN state='RELEASED' THEN 0
               WHEN state='RECONCILED' THEN output_tokens
               ELSE estimated_output_tokens
             END
           ),0) AS output_tokens,
           COALESCE(SUM(
             CASE
               WHEN state='RELEASED' THEN 0
               WHEN state='RECONCILED' THEN total_tokens
               ELSE estimated_input_tokens + estimated_output_tokens
             END
           ),0) AS total_tokens
           ,COALESCE(SUM(
             CASE WHEN state='RECONCILED' THEN actual_nano_usd ELSE 0 END
           ),0) AS spent_nano_usd
           ,COALESCE(SUM(
             CASE
               WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
                 THEN reserved_nano_usd
               ELSE 0
             END
           ),0) AS reserved_nano_usd
         FROM provider_transmissions
         WHERE project_id=? AND job_id=?
           AND (? IS NULL OR transmission_id<>?)`,
      )
      .get(
        projectId,
        jobId,
        excludedTransmissionId,
        excludedTransmissionId,
      );
  }

  #assertProviderCostAggregates(budget) {
    const aggregate = this.database
      .prepare(
        `SELECT
           COALESCE(SUM(
             CASE
               WHEN state IN ('RESERVED','TRANSMITTING','UNKNOWN')
                 THEN reserved_nano_usd
               ELSE 0
             END
           ),0) AS reserved_nano_usd,
           COALESCE(SUM(
             CASE WHEN state='RECONCILED' THEN actual_nano_usd ELSE 0 END
           ),0) AS spent_nano_usd
         FROM provider_transmissions
         WHERE project_id=?`,
      )
      .get(budget.project_id);
    if (
      aggregate.reserved_nano_usd !== budget.reserved_nano_usd ||
      aggregate.spent_nano_usd !== budget.spent_nano_usd
    ) {
      throw stateError(
        "COST_ACCOUNTING_CORRUPT",
        "project transmission aggregates do not match the durable budget",
      );
    }
  }

  #assertOriginOwnsProject(originId, projectId) {
    const origin = this.database
      .prepare("SELECT project_id FROM origins WHERE origin_id=?")
      .get(originId);
    if (origin === undefined || origin.project_id !== projectId) {
      throw stateError(
        "ORIGIN_FORBIDDEN",
        "origin is not bound to the requested project",
      );
    }
  }

  #assertCostBudgetIdentity(budget, request) {
    if (budget === undefined) {
      throw stateError(
        "COST_ACCOUNTING_CORRUPT",
        "cost reservation budget is missing",
      );
    }
    if (budget.pricing_version !== request.pricingVersion) {
      throw stateError(
        "PRICING_VERSION_MISMATCH",
        "cost budget pricing version does not match",
      );
    }
    if (budget.ceiling_nano_usd !== request.ceilingNanoUsd) {
      throw stateError(
        "COST_BUDGET_CONFLICT",
        "cost budget ceiling conflicts with established budget",
      );
    }
  }

  #rollbackTransaction(error) {
    let rollbackError;
    if (this.database.isTransaction) {
      try {
        this.database.exec("ROLLBACK");
      } catch (caughtRollbackError) {
        rollbackError = caughtRollbackError;
      }
    }
    if (rollbackError !== undefined) {
      throw new AggregateError(
        [error, rollbackError],
        "scheduler transaction and rollback both failed",
        { cause: error },
      );
    }
    throw error;
  }
}

const SCHEMA_COLUMNS = Object.freeze({
  schema_meta: ["key", "value"],
  logical_jobs: ["job_id", "project_id", "idempotency_key", "created_at_ms"],
  generations: [
    "job_id",
    "generation",
    "task_id",
    "role",
    "pool_id",
    "priority",
    "state",
    "contract_hash",
    "input_fingerprint",
    "maximum_attempts",
    "contract_json",
    "accepted_result_hash",
    "diagnostic_enqueued",
    "created_at_ms",
    "updated_at_ms",
  ],
  attempts: [
    "job_id",
    "generation",
    "attempt_id",
    "worker_id",
    "epoch",
    "state",
    "started_at_ms",
    "finished_at_ms",
    "failure_class",
  ],
  leases: [
    "job_id",
    "generation",
    "attempt_id",
    "worker_id",
    "epoch",
    "heartbeat_at_ms",
    "expires_at_ms",
  ],
  events: [
    "sequence",
    "job_id",
    "generation",
    "event_type",
    "event_json",
    "created_at_ms",
  ],
  protocol_responses: [
    "request_id",
    "request_fingerprint",
    "response_json",
    "created_at_ms",
  ],
});

const CANDIDATE_V3_SCHEMA_COLUMNS = Object.freeze({
  ...SCHEMA_COLUMNS,
  projects: ["project_id", "created_at_ms"],
  origins: [
    "origin_id",
    "project_id",
    "origin_thread_hash",
    "origin_capability_hash",
    "created_at_ms",
  ],
  logical_job_origins: [
    "job_id",
    "origin_id",
    "project_id",
    "created_at_ms",
  ],
  legacy_migration_runs: [
    "run_id",
    "project_id",
    "canonical_workspace",
    "workspace_identity_hash",
    "candidate_protocol_version",
    "stale_before_ms",
    "run_state",
    "created_at_ms",
  ],
  legacy_migration_sources: [
    "run_id",
    "source_namespace",
    "source_kind",
    "source_hash",
    "entry_count",
  ],
  legacy_migration_entries: [
    "run_id",
    "source_namespace",
    "entry_kind",
    "logical_identity_hash",
    "relative_path_hash",
    "content_hash",
    "byte_count",
    "protocol_version",
    "terminal_state",
    "disposition",
    "reason_code",
  ],
  legacy_migration_collisions: [
    "run_id",
    "collision_kind",
    "logical_identity_hash",
    "source_count",
    "disposition",
    "reason_code",
  ],
  writer_fence_counters: ["project_id", "current_fencing_token"],
  writer_locks: [
    "project_id",
    "origin_id",
    "owner_job_id",
    "owner_generation",
    "owner_lease_epoch",
    "fencing_token",
    "canonical_worktree",
    "worktree_identity",
    "acquired_at_ms",
    "expires_at_ms",
  ],
  writer_lock_outputs: [
    "project_id",
    "fencing_token",
    "canonical_output_path",
    "filesystem_identity",
  ],
  cost_budgets: [
    "project_id",
    "ceiling_nano_usd",
    "spent_nano_usd",
    "reserved_nano_usd",
    "pricing_version",
    "updated_at_ms",
  ],
  cost_reservations: [
    "reservation_id",
    "project_id",
    "origin_id",
    "job_id",
    "attempt_id",
    "state",
    "reserved_nano_usd",
    "actual_nano_usd",
    "pricing_version",
    "created_at_ms",
    "updated_at_ms",
  ],
  public_resources: [
    "public_id",
    "resource_kind",
    "origin_id",
    "project_id",
    "created_at_ms",
  ],
  protocol_requests: [
    "origin_id",
    "project_id",
    "request_id",
    "method",
    "request_fingerprint",
    "normalization_source_json",
    "normalization_source_hash",
    "normalization_source_bytes",
    "request_state",
    "normalization_epoch",
    "outcome_json",
    "outcome_hash",
    "outcome_bytes",
    "created_at_ms",
    "updated_at_ms",
  ],
  protocol_request_normalization_claims: [
    "origin_id",
    "request_id",
    "epoch",
    "owner_token_hash",
    "claim_state",
    "claimed_at_ms",
    "expires_at_ms",
    "finished_at_ms",
  ],
  protocol_request_resources: [
    "origin_id",
    "project_id",
    "request_id",
    "relationship",
    "public_id",
  ],
  worker_bindings: [
    "binding_id",
    "project_id",
    "execution_fingerprint",
    "binding_epoch",
    "job_id",
    "generation",
    "binding_state",
    "created_at_ms",
    "updated_at_ms",
  ],
  worker_claims: [
    "public_id",
    "origin_id",
    "project_id",
    "binding_id",
    "claim_state",
    "created_at_ms",
    "updated_at_ms",
  ],
  head_runs: [
    "head_run_id",
    "project_id",
    "attempt_fingerprint",
    "binding_epoch",
    "selected_effort",
    "run_state",
    "created_at_ms",
    "updated_at_ms",
  ],
  result_packets: [
    "packet_hash",
    "result_protocol",
    "public_status",
    "execution_status",
    "evidence_verdict",
    "cache_hit",
    "canonical_json",
    "byte_count",
    "created_at_ms",
  ],
  result_subjects: [
    "result_subject_id",
    "subject_kind",
    "worker_binding_id",
    "head_run_id",
    "normalization_source_json",
    "normalization_source_hash",
    "normalization_source_bytes",
    "normalization_epoch",
    "subject_state",
    "accepted_packet_hash",
    "created_at_ms",
    "updated_at_ms",
  ],
  result_normalization_claims: [
    "result_subject_id",
    "epoch",
    "owner_token_hash",
    "claim_state",
    "claimed_at_ms",
    "expires_at_ms",
    "finished_at_ms",
  ],
  sol_plans: [
    "plan_id",
    "origin_id",
    "project_id",
    "input_fingerprint",
    "attempt_fingerprint",
    "decision",
    "selected_effort",
    "max_eligible",
    "cache_eligible",
    "policy_hash",
    "evidence_hash",
    "governance_hash",
    "plan_json",
    "plan_bytes",
    "created_at_ms",
  ],
  sol_plan_reasons: ["plan_id", "ordinal", "reason_code"],
  head_claims: [
    "public_id",
    "origin_id",
    "project_id",
    "plan_id",
    "attempt_fingerprint",
    "selected_effort",
    "head_run_id",
    "claim_state",
    "created_at_ms",
    "updated_at_ms",
  ],
  max_attempt_claims: [
    "project_id",
    "attempt_fingerprint",
    "plan_id",
    "decision",
    "max_eligible",
    "selected_effort",
    "head_run_id",
    "claimed_at_ms",
  ],
  batch_runs: [
    "batch_run_id",
    "project_id",
    "batch_fingerprint",
    "binding_epoch",
    "node_count",
    "requested_concurrency",
    "run_state",
    "created_at_ms",
    "updated_at_ms",
  ],
  batch_claims: [
    "public_id",
    "origin_id",
    "project_id",
    "batch_run_id",
    "claim_state",
    "created_at_ms",
    "updated_at_ms",
  ],
  batch_nodes: [
    "batch_run_id",
    "project_id",
    "node_key",
    "ordinal",
    "template_fingerprint",
    "node_state",
    "worker_binding_id",
    "created_at_ms",
    "updated_at_ms",
  ],
  batch_edges: ["batch_run_id", "source_node_key", "target_node_key"],
  batch_dependency_states: [
    "batch_run_id",
    "source_node_key",
    "target_node_key",
    "epoch",
    "dependency_state",
    "reason_code",
    "observed_packet_hash",
    "updated_at_ms",
  ],
  batch_node_accepted_verdicts: [
    "batch_run_id",
    "node_key",
    "evidence_verdict",
  ],
  batch_claim_nodes: [
    "batch_public_id",
    "origin_id",
    "project_id",
    "batch_run_id",
    "node_key",
    "worker_public_id",
    "worker_binding_id",
  ],
});

const CANDIDATE_V4_SCHEMA_COLUMNS = Object.freeze({
  ...CANDIDATE_V3_SCHEMA_COLUMNS,
  transmission_project_budgets: [
    "project_id",
    "ceiling_nano_usd",
    "spent_nano_usd",
    "reserved_nano_usd",
    "pricing_version",
    "created_at_ms",
    "updated_at_ms",
  ],
  provider_job_limits: [
    "project_id",
    "job_id",
    "maximum_provider_calls",
    "maximum_input_tokens",
    "maximum_cached_input_tokens",
    "maximum_output_tokens_total",
    "maximum_total_tokens",
    "created_at_ms",
    "updated_at_ms",
  ],
  provider_transmissions: [
    "transmission_id",
    "project_id",
    "job_id",
    "origin_id",
    "transmission_ordinal",
    "attempt_id",
    "route",
    "provider",
    "model",
    "service_tier",
    "reasoning_effort",
    "pricing_version",
    "state",
    "reserved_nano_usd",
    "actual_nano_usd",
    "estimated_input_tokens",
    "estimated_output_tokens",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "total_tokens",
    "created_at_ms",
    "transmitted_at_ms",
    "finished_at_ms",
    "updated_at_ms",
  ],
});

const CANDIDATE_V5_SCHEMA_COLUMNS = Object.freeze({
  ...CANDIDATE_V4_SCHEMA_COLUMNS,
  accounting_policy_transitions: [
    "transition_id",
    "project_id",
    "source_pricing_version",
    "target_pricing_version",
    "transition_fingerprint",
    "ceiling_before_nano_usd",
    "ceiling_after_nano_usd",
    "spent_before_nano_usd",
    "spent_after_nano_usd",
    "reserved_before_nano_usd",
    "reserved_after_nano_usd",
    "reconciled_transmissions",
    "released_transmissions",
    "active_transmissions",
    "unknown_transmissions",
    "active_workers",
    "active_heads",
    "precondition_hash",
    "created_at_ms",
  ],
  head_producer_attempts: [
    "head_run_id",
    "project_id",
    "producer_job_id",
    "attempt_fingerprint",
    "plan_id",
    "selected_effort",
    "producer_state",
    "external_start_possible",
    "process_boot_id",
    "owner_pid",
    "terminal_result_hash",
    "claimed_at_ms",
    "started_at_ms",
    "finished_at_ms",
    "created_at_ms",
    "updated_at_ms",
  ],
});

const BASE_SCHEMA_INDEXES = Object.freeze([
  "idx_generations_queue",
  "idx_leases_expiry",
]);

const CANDIDATE_V3_SCHEMA_INDEXES = Object.freeze([
  ...BASE_SCHEMA_INDEXES,
  "idx_logical_jobs_project_job",
  "idx_origins_project",
  "idx_logical_job_origins_origin",
  "idx_legacy_migration_runs_project",
  "idx_legacy_migration_entries_identity",
  "idx_legacy_migration_collisions_disposition",
  "idx_writer_locks_expiry",
  "idx_writer_lock_outputs_path",
  "idx_public_resources_origin_kind",
  "idx_protocol_requests_state",
  "idx_protocol_request_claim_active",
  "idx_protocol_request_claim_expiry",
  "idx_protocol_request_resources_public",
  "idx_worker_bindings_active",
  "idx_worker_claims_origin_state",
  "idx_worker_claims_binding",
  "idx_head_runs_active",
  "idx_head_claims_origin_state",
  "idx_result_subjects_state",
  "idx_result_claim_active",
  "idx_result_claim_expiry",
  "idx_batch_runs_active",
  "idx_batch_claims_origin_state",
  "idx_batch_nodes_state",
  "idx_batch_dependencies_target",
]);

const CANDIDATE_V4_SCHEMA_INDEXES = Object.freeze([
  ...CANDIDATE_V3_SCHEMA_INDEXES,
  "idx_provider_job_limits_project",
  "idx_provider_transmissions_project_job",
  "idx_provider_transmissions_project_state",
  "idx_worker_claims_origin_binding",
]);

const CANDIDATE_V5_SCHEMA_INDEXES = Object.freeze([
  ...CANDIDATE_V4_SCHEMA_INDEXES,
  "idx_accounting_policy_transitions_project",
  "idx_head_producer_attempts_project_state",
]);

const CANDIDATE_V3_SCHEMA_TRIGGERS = Object.freeze([
  "trg_protocol_responses_v3_read_only_insert",
  "trg_protocol_responses_v3_read_only_update",
  "trg_protocol_responses_v3_read_only_delete",
]);

const CANDIDATE_V4_SCHEMA_TRIGGERS = Object.freeze([
  ...CANDIDATE_V3_SCHEMA_TRIGGERS,
  "trg_cost_budgets_v4_read_only_insert",
  "trg_cost_budgets_v4_read_only_update",
  "trg_cost_budgets_v4_read_only_delete",
  "trg_cost_reservations_v4_read_only_insert",
  "trg_cost_reservations_v4_read_only_update",
  "trg_cost_reservations_v4_read_only_delete",
]);

function normalizeSchemaSql(sql) {
  if (typeof sql !== "string") return null;
  let normalized = "";
  let closingQuote = null;
  for (let index = 0; index < sql.length; index += 1) {
    const character = sql[index];
    if (closingQuote !== null) {
      normalized += character;
      if (character === closingQuote) {
        if (sql[index + 1] === closingQuote && closingQuote !== "]") {
          normalized += sql[index + 1];
          index += 1;
        } else {
          closingQuote = null;
        }
      }
      continue;
    }
    if (/\s/.test(character)) continue;
    if (character === "'" || character === '"' || character === "`") {
      closingQuote = character;
      normalized += character;
      continue;
    }
    if (character === "[") {
      closingQuote = "]";
      normalized += character;
      continue;
    }
    normalized += character.toLowerCase();
  }
  if (closingQuote !== null) throw unsupportedSchemaVersion();
  return normalized;
}

function schemaDdlSignature(database) {
  return JSON.stringify(
    database
      .prepare(
        `SELECT type, name, tbl_name, sql
         FROM sqlite_master
         WHERE type IN ('table', 'index', 'view', 'trigger')
           AND name NOT GLOB 'sqlite_*'
         ORDER BY type ASC, name ASC`,
      )
      .all()
      .map((row) => ({
        type: row.type,
        name: row.name,
        tableName: row.tbl_name,
        sql: normalizeSchemaSql(row.sql),
      })),
  );
}

function validateKnownSchema(database, version) {
  if (
    ![
      1,
      STORE_SCHEMA_VERSION,
      CANDIDATE_STORE_SCHEMA_V3_VERSION,
      CANDIDATE_STORE_SCHEMA_V4_VERSION,
      CANDIDATE_STORE_SCHEMA_VERSION,
    ].includes(version)
  ) {
    throw unsupportedSchemaVersion();
  }
  const schemaColumns = version === CANDIDATE_STORE_SCHEMA_VERSION
    ? CANDIDATE_V5_SCHEMA_COLUMNS
    : version === CANDIDATE_STORE_SCHEMA_V4_VERSION
      ? CANDIDATE_V4_SCHEMA_COLUMNS
      : version === CANDIDATE_STORE_SCHEMA_V3_VERSION
        ? CANDIDATE_V3_SCHEMA_COLUMNS
        : SCHEMA_COLUMNS;
  const tableNames =
    version === 1
      ? Object.keys(schemaColumns).filter((name) => name !== "protocol_responses")
      : Object.keys(schemaColumns);
  const indexNames = version === CANDIDATE_STORE_SCHEMA_VERSION
    ? CANDIDATE_V5_SCHEMA_INDEXES
    : version === CANDIDATE_STORE_SCHEMA_V4_VERSION
      ? CANDIDATE_V4_SCHEMA_INDEXES
      : version === CANDIDATE_STORE_SCHEMA_V3_VERSION
        ? CANDIDATE_V3_SCHEMA_INDEXES
        : BASE_SCHEMA_INDEXES;
  const triggerNames =
    version >= CANDIDATE_STORE_SCHEMA_V4_VERSION
      ? CANDIDATE_V4_SCHEMA_TRIGGERS
      : version === CANDIDATE_STORE_SCHEMA_V3_VERSION
        ? CANDIDATE_V3_SCHEMA_TRIGGERS
        : [];
  const expectedObjects = new Set([
    ...tableNames,
    ...indexNames,
    ...triggerNames,
  ]);
  const actualObjects = database
    .prepare(
      `SELECT name
       FROM sqlite_master
       WHERE type IN ('table', 'index', 'view', 'trigger')
         AND name NOT GLOB 'sqlite_*'`,
    )
    .all()
    .map((row) => row.name);
  if (
    actualObjects.length !== expectedObjects.size ||
    actualObjects.some((name) => !expectedObjects.has(name))
  ) {
    throw unsupportedSchemaVersion();
  }
  for (const tableName of tableNames) {
    const columns = database
      .prepare(`PRAGMA table_info("${tableName}")`)
      .all()
      .map((row) => row.name);
    const expected = schemaColumns[tableName];
    if (
      columns.length !== expected.length ||
      columns.some((column, index) => column !== expected[index])
    ) {
      throw unsupportedSchemaVersion();
    }
  }
  const expected = new DatabaseSync(":memory:");
  let expectedSignature;
  try {
    if (version === 1) expected.exec(V1_SCHEMA_SQL);
    else {
      expected.exec(SCHEMA_SQL);
      if (version >= CANDIDATE_STORE_SCHEMA_V3_VERSION) {
        expected.exec(CANDIDATE_V3_SCHEMA_ADDITIONS_SQL);
      }
      if (version >= CANDIDATE_STORE_SCHEMA_V4_VERSION) {
        expected.exec(CANDIDATE_V4_SCHEMA_ADDITIONS_SQL);
      }
      if (version === CANDIDATE_STORE_SCHEMA_VERSION) {
        expected.exec(CANDIDATE_V5_SCHEMA_ADDITIONS_SQL);
      }
    }
    expectedSignature = schemaDdlSignature(expected);
  } finally {
    expected.close();
  }
  if (schemaDdlSignature(database) !== expectedSignature) {
    throw unsupportedSchemaVersion();
  }
}

function readEventsAutoincrementSequence(database) {
  const rows = database
    .prepare(
      `SELECT typeof(seq) AS value_type, CAST(seq AS TEXT) AS sequence_text
       FROM sqlite_sequence
       WHERE name='events'`,
    )
    .all();
  const liveMaximumText = database
    .prepare("SELECT CAST(COALESCE(MAX(sequence),0) AS TEXT) AS maximum FROM events")
    .get().maximum;
  if (rows.length === 0) {
    if (liveMaximumText !== "0") throw unsupportedSchemaVersion();
    return null;
  }
  if (
    rows.length !== 1 ||
    rows[0].value_type !== "integer" ||
    !/^(0|[1-9][0-9]*)$/.test(rows[0].sequence_text)
  ) {
    throw unsupportedSchemaVersion();
  }
  if (BigInt(rows[0].sequence_text) < BigInt(liveMaximumText)) {
    throw unsupportedSchemaVersion();
  }
  return rows[0].sequence_text;
}

function restoreEventsAutoincrementSequence(database, sequenceText) {
  if (sequenceText === null) return;
  database.prepare("DELETE FROM sqlite_sequence WHERE name='events'").run();
  database
    .prepare(
      `INSERT INTO sqlite_sequence(name,seq)
       VALUES ('events',CAST(? AS INTEGER))`,
    )
    .run(sequenceText);
  if (readEventsAutoincrementSequence(database) !== sequenceText) {
    throw unsupportedSchemaVersion();
  }
}

function rebuildV1ToV2WithinTransaction(database) {
  if (!database.isTransaction) throw new Error("scheduler migration transaction required");
  const eventsAutoincrementSequence = readEventsAutoincrementSequence(database);
  database.exec(`
    DROP INDEX idx_generations_queue;
    DROP INDEX idx_leases_expiry;
    ALTER TABLE events RENAME TO events_v1;
    ALTER TABLE leases RENAME TO leases_v1;
    ALTER TABLE attempts RENAME TO attempts_v1;
    ALTER TABLE generations RENAME TO generations_v1;
    ALTER TABLE logical_jobs RENAME TO logical_jobs_v1;
  `);
  database.exec(SCHEMA_SQL);
  database.exec(`
    INSERT INTO logical_jobs SELECT * FROM logical_jobs_v1;
    INSERT INTO generations SELECT * FROM generations_v1;
    INSERT INTO attempts SELECT * FROM attempts_v1;
    INSERT INTO leases SELECT * FROM leases_v1;
    INSERT INTO events SELECT * FROM events_v1;
  `);
  const foreignKeyFailures = database.prepare("PRAGMA foreign_key_check").all();
  if (foreignKeyFailures.length !== 0) throw unsupportedSchemaVersion();
  database.exec(`
    DROP TABLE events_v1;
    DROP TABLE leases_v1;
    DROP TABLE attempts_v1;
    DROP TABLE generations_v1;
    DROP TABLE logical_jobs_v1;
  `);
  restoreEventsAutoincrementSequence(database, eventsAutoincrementSequence);
}

function migrateV1ToV2(database) {
  validateKnownSchema(database, 1);
  database.exec("PRAGMA foreign_keys=OFF;");
  let failure = null;
  try {
    database.exec("BEGIN IMMEDIATE");
    rebuildV1ToV2WithinTransaction(database);
    database
      .prepare("UPDATE schema_meta SET value = ? WHERE key = 'schema_version'")
      .run("2");
    database.exec("COMMIT");
  } catch (error) {
    failure = error;
    if (database.isTransaction) {
      try {
        database.exec("ROLLBACK");
      } catch (rollbackError) {
        failure = new AggregateError(
          [error, rollbackError],
          "scheduler migration and rollback failed",
          { cause: error },
        );
      }
    }
  }
  try {
    database.exec("PRAGMA foreign_keys=ON;");
  } catch (foreignKeyError) {
    failure =
      failure === null
        ? foreignKeyError
        : new AggregateError(
            [failure, foreignKeyError],
            "scheduler migration cleanup failed",
            { cause: failure },
          );
  }
  if (failure !== null) throw failure;
  validateKnownSchema(database, STORE_SCHEMA_VERSION);
}

function candidateMigrationError(code, message) {
  const error = new Error(message);
  Object.defineProperty(error, "code", {
    value: code,
    enumerable: true,
    configurable: false,
    writable: false,
  });
  return error;
}

function readExactSchemaVersion(database, allowedVersions) {
  let rows;
  try {
    rows = database
      .prepare("SELECT key,value FROM schema_meta ORDER BY key")
      .all()
      .map((row) => ({ key: row.key, value: row.value }));
  } catch {
    throw unsupportedSchemaVersion();
  }
  if (
    rows.length !== 1 ||
    rows[0].key !== "schema_version" ||
    !allowedVersions.includes(rows[0].value)
  ) {
    throw unsupportedSchemaVersion();
  }
  return Number(rows[0].value);
}

function databaseDataVersion(database) {
  const row = database.prepare("PRAGMA data_version").get();
  if (!Number.isSafeInteger(row?.data_version) || row.data_version < 1) {
    throw unsupportedSchemaVersion();
  }
  return row.data_version;
}

function assertCandidateDatabaseHealth(database) {
  const integrityRows = database.prepare("PRAGMA integrity_check").all();
  if (
    integrityRows.length !== 1 ||
    Object.values(integrityRows[0]).length !== 1 ||
    Object.values(integrityRows[0])[0] !== "ok"
  ) {
    throw unsupportedSchemaVersion();
  }
  if (database.prepare("PRAGMA foreign_key_check").all().length !== 0) {
    throw unsupportedSchemaVersion();
  }
}

function legacyTablesForVersion(version) {
  if (version === CANDIDATE_STORE_SCHEMA_V4_VERSION) {
    return Object.keys(CANDIDATE_V4_SCHEMA_COLUMNS);
  }
  if (version === CANDIDATE_STORE_SCHEMA_V3_VERSION) {
    return Object.keys(CANDIDATE_V3_SCHEMA_COLUMNS);
  }
  const tables = [
    "schema_meta",
    "logical_jobs",
    "generations",
    "attempts",
    "leases",
    "events",
  ];
  if (version >= STORE_SCHEMA_VERSION) tables.push("protocol_responses");
  return tables;
}

function legacyRowCounts(database, version) {
  const counts = {};
  for (const tableName of legacyTablesForVersion(version)) {
    counts[tableName] = database
      .prepare(`SELECT COUNT(*) AS count FROM "${tableName}"`)
      .get().count;
  }
  return counts;
}

function assertSameRowCounts(actual, expected, code = "MIGRATION_SOURCE_CHANGED") {
  const actualEntries = Object.entries(actual);
  const expectedEntries = Object.entries(expected);
  if (
    actualEntries.length !== expectedEntries.length ||
    actualEntries.some(
      ([name, count], index) =>
        expectedEntries[index]?.[0] !== name || expectedEntries[index]?.[1] !== count,
    )
  ) {
    throw candidateMigrationError(code, "scheduler migration source changed");
  }
}

function assertCandidateLegacyData(database, version) {
  const invalidProject = database
    .prepare(
      `SELECT 1
       FROM logical_jobs
       WHERE length(project_id) NOT BETWEEN 1 AND 256
          OR project_id GLOB '*[^A-Za-z0-9._:-]*'
          OR project_id IN ('.', '..')
       LIMIT 1`,
    )
    .get();
  const invalidJson = database
    .prepare(
      `SELECT 1 FROM generations WHERE NOT json_valid(contract_json)
       UNION ALL
       SELECT 1 FROM events WHERE NOT json_valid(event_json)
       LIMIT 1`,
    )
    .get();
  if (invalidProject !== undefined || invalidJson !== undefined) {
    throw unsupportedSchemaVersion();
  }
  if (version >= STORE_SCHEMA_VERSION) {
    const incompleteReplay = database
      .prepare("SELECT 1 FROM protocol_responses WHERE response_json IS NULL LIMIT 1")
      .get();
    if (incompleteReplay !== undefined) {
      throw candidateMigrationError(
        "MIGRATION_LEGACY_REPLAY_INCOMPLETE",
        "legacy protocol replay is incomplete",
      );
    }
    const invalidReplay = database
      .prepare(
        `SELECT 1 FROM protocol_responses
         WHERE NOT json_valid(response_json)
         LIMIT 1`,
      )
      .get();
    if (invalidReplay !== undefined) throw unsupportedSchemaVersion();
  }
}

function attestCandidateMigrationSource(database, version) {
  validateKnownSchema(database, version);
  assertCandidateDatabaseHealth(database);
  const activeWork = database
    .prepare(
      `SELECT
         (SELECT COUNT(*) FROM leases) AS leases,
         (SELECT COUNT(*) FROM attempts WHERE state='RUNNING') AS running_attempts,
         (SELECT COUNT(*) FROM generations
          WHERE state IN ('QUEUED','RUNNING','VALIDATING')) AS nonterminal_generations`,
    )
    .get();
  if (
    activeWork.leases !== 0 ||
    activeWork.running_attempts !== 0 ||
    activeWork.nonterminal_generations !== 0
  ) {
    throw candidateMigrationError(
      "MIGRATION_NOT_QUIESCENT",
      "scheduler migration requires a quiescent store",
    );
  }
  assertCandidateLegacyData(database, version);
  return legacyRowCounts(database, version);
}

function attestCandidateV4MigrationSource(database) {
  const counts = attestCandidateMigrationSource(
    database,
    CANDIDATE_STORE_SCHEMA_V3_VERSION,
  );
  const unresolvedLegacyCost = database
    .prepare(
      `SELECT 1
       FROM cost_reservations
       WHERE state IN ('OPEN','UNKNOWN')
       UNION ALL
       SELECT 1
       FROM cost_budgets
       WHERE reserved_nano_usd <> 0
       LIMIT 1`,
    )
    .get();
  if (unresolvedLegacyCost !== undefined) {
    throw candidateMigrationError(
      "MIGRATION_LEGACY_COST_NONTERMINAL",
      "legacy cost reservations must be terminal before schema-v4 migration",
    );
  }
  const duplicateOriginBinding = database
    .prepare(
      `SELECT 1
       FROM worker_claims
       GROUP BY origin_id,binding_id
       HAVING COUNT(*) > 1
       LIMIT 1`,
    )
    .get();
  if (duplicateOriginBinding !== undefined) {
    throw candidateMigrationError(
      "MIGRATION_WORKER_CLAIM_COLLISION",
      "worker claims contain duplicate origin and binding identities",
    );
  }
  return counts;
}

function attestCandidateV5MigrationSource(database) {
  const counts = attestCandidateMigrationSource(
    database,
    CANDIDATE_STORE_SCHEMA_V4_VERSION,
  );
  const unresolvedWork = database
    .prepare(
      `SELECT
         (SELECT COUNT(*) FROM provider_transmissions
          WHERE state IN ('RESERVED','TRANSMITTING','UNKNOWN')) AS transmissions,
         (SELECT COUNT(*) FROM transmission_project_budgets
          WHERE reserved_nano_usd <> 0) AS reserved_budgets,
         (SELECT COUNT(*) FROM head_runs
          WHERE run_state IN ('QUEUED','RUNNING')) AS heads`,
    )
    .get();
  if (
    unresolvedWork.transmissions !== 0 ||
    unresolvedWork.reserved_budgets !== 0 ||
    unresolvedWork.heads !== 0
  ) {
    throw candidateMigrationError(
      "MIGRATION_NOT_QUIESCENT",
      "schema-v5 migration requires terminal provider and head work",
    );
  }
  return counts;
}

function invokeCandidateMigrationPhase(onMigrationPhase, phase) {
  if (onMigrationPhase === undefined) return;
  const result = onMigrationPhase(phase);
  if (result !== undefined) {
    throw new TypeError("onMigrationPhase must be synchronous and return undefined");
  }
}

const SQLITE_SIDECAR_SUFFIXES = Object.freeze(["-journal", "-wal", "-shm"]);

function sqliteArtifactNamespace(filename) {
  return [filename, ...SQLITE_SIDECAR_SUFFIXES.map((suffix) => `${filename}${suffix}`)];
}

function filesystemPathIdentity(filename) {
  return process.platform === "win32" ? filename.toLowerCase() : filename;
}

function assertCandidateBackupDestinationAvailable(backup) {
  if (sqliteArtifactNamespace(backup).some((filename) => existsSync(filename))) {
    throw candidateMigrationError(
      "MIGRATION_BACKUP_EXISTS",
      "scheduler migration backup namespace already exists",
    );
  }
}

function assertCandidateBackupNamespacesDisjoint(source, backup) {
  const sourceNamespace = new Set(
    sqliteArtifactNamespace(source).map(filesystemPathIdentity),
  );
  if (
    sqliteArtifactNamespace(backup)
      .map(filesystemPathIdentity)
      .some((filename) => sourceNamespace.has(filename))
  ) {
    throw new TypeError("backup SQLite namespace must differ from source");
  }
}

function canonicalCandidateBackupPath(backup) {
  return path.join(realpathSync.native(path.dirname(backup)), path.basename(backup));
}

function attestCandidateMigrationPathAliases(paths) {
  const canonicalSource = realpathSync.native(paths.source);
  const canonicalBackup = canonicalCandidateBackupPath(paths.backup);
  if (
    filesystemPathIdentity(canonicalSource) !== paths.canonicalSourceIdentity ||
    filesystemPathIdentity(canonicalBackup) !== paths.canonicalBackupIdentity
  ) {
    throw candidateMigrationError(
      "MIGRATION_PATH_CHANGED",
      "scheduler migration path identity changed",
    );
  }
  assertCandidateBackupNamespacesDisjoint(paths.source, paths.backup);
  assertCandidateBackupNamespacesDisjoint(canonicalSource, canonicalBackup);
}

function assertCandidateBackupHasNoSidecars(backup) {
  if (SQLITE_SIDECAR_SUFFIXES.some((suffix) => existsSync(`${backup}${suffix}`))) {
    throw candidateMigrationError(
      "MIGRATION_BACKUP_EXISTS",
      "scheduler migration backup sidecar already exists",
    );
  }
}

function resolveCandidateMigrationPaths(filename, backupFilename) {
  if (
    typeof filename !== "string" ||
    filename.trim() === "" ||
    filename === ":memory:" ||
    typeof backupFilename !== "string" ||
    backupFilename.trim() === "" ||
    backupFilename === ":memory:"
  ) {
    throw new TypeError("file-backed migration and backup paths are required");
  }
  const source = path.resolve(filename);
  const backup = path.resolve(backupFilename);
  if (!existsSync(source) || !statSync(source).isFile()) {
    throw new TypeError("scheduler migration source must exist");
  }
  const backupParent = path.dirname(backup);
  if (!existsSync(backupParent) || !statSync(backupParent).isDirectory()) {
    throw new TypeError("scheduler migration backup directory must exist");
  }
  const canonicalSource = realpathSync.native(source);
  const canonicalBackup = canonicalCandidateBackupPath(backup);
  assertCandidateBackupNamespacesDisjoint(source, backup);
  assertCandidateBackupNamespacesDisjoint(canonicalSource, canonicalBackup);
  assertCandidateBackupDestinationAvailable(backup);
  return {
    source,
    backup,
    canonicalSourceIdentity: filesystemPathIdentity(canonicalSource),
    canonicalBackupIdentity: filesystemPathIdentity(canonicalBackup),
  };
}

function rollbackCandidateMigration(database, error) {
  if (!database.isTransaction) return error;
  try {
    database.exec("ROLLBACK");
    return error;
  } catch (rollbackError) {
    return new AggregateError(
      [error, rollbackError],
      "candidate scheduler migration and rollback failed",
      { cause: error },
    );
  }
}

function restoreCandidateForeignKeys(database, failure) {
  try {
    database.exec("PRAGMA foreign_keys=ON;");
    return failure;
  } catch (foreignKeyError) {
    if (failure === null) return foreignKeyError;
    return new AggregateError(
      [failure, foreignKeyError],
      "candidate scheduler migration cleanup failed",
      { cause: failure },
    );
  }
}

function seedCandidateProjects(database) {
  database.exec(`
    INSERT INTO projects(project_id,created_at_ms)
    SELECT project_id,MIN(created_at_ms)
    FROM logical_jobs
    GROUP BY project_id;
  `);
}

function assertCandidateAdditiveRows(database, sourceVersion, sourceCounts) {
  const targetCounts = legacyRowCounts(database, STORE_SCHEMA_VERSION);
  for (const [tableName, count] of Object.entries(sourceCounts)) {
    if (targetCounts[tableName] !== count) {
      throw candidateMigrationError(
        "MIGRATION_ROW_CHECK_FAILED",
        "scheduler migration row check failed",
      );
    }
  }
  if (sourceVersion === 1 && targetCounts.protocol_responses !== 0) {
    throw candidateMigrationError(
      "MIGRATION_ROW_CHECK_FAILED",
      "scheduler migration row check failed",
    );
  }
  const projectCounts = database
    .prepare(
      `SELECT
         (SELECT COUNT(*) FROM projects) AS projects,
         (SELECT COUNT(DISTINCT project_id) FROM logical_jobs) AS source_projects`,
    )
    .get();
  if (projectCounts.projects !== projectCounts.source_projects) {
    throw candidateMigrationError(
      "MIGRATION_ROW_CHECK_FAILED",
      "scheduler migration project check failed",
    );
  }
  for (const tableName of Object.keys(CANDIDATE_V3_SCHEMA_COLUMNS)) {
    if (tableName in SCHEMA_COLUMNS || tableName === "projects") continue;
    const count = database
      .prepare(`SELECT COUNT(*) AS count FROM "${tableName}"`)
      .get().count;
    if (count !== 0) {
      throw candidateMigrationError(
        "MIGRATION_ROW_CHECK_FAILED",
        "scheduler migration created unexpected rows",
      );
    }
  }
}

function assertCandidateV4AdditiveRows(database, sourceCounts) {
  assertSameRowCounts(
    legacyRowCounts(database, CANDIDATE_STORE_SCHEMA_V3_VERSION),
    sourceCounts,
    "MIGRATION_ROW_CHECK_FAILED",
  );
  for (const tableName of Object.keys(CANDIDATE_V4_SCHEMA_COLUMNS)) {
    if (tableName in CANDIDATE_V3_SCHEMA_COLUMNS) continue;
    const count = database
      .prepare(`SELECT COUNT(*) AS count FROM "${tableName}"`)
      .get().count;
    if (count !== 0) {
      throw candidateMigrationError(
        "MIGRATION_ROW_CHECK_FAILED",
        "scheduler migration created unexpected schema-v4 rows",
      );
    }
  }
}

function assertCandidateV5AdditiveRows(database, sourceCounts) {
  assertSameRowCounts(
    legacyRowCounts(database, CANDIDATE_STORE_SCHEMA_V4_VERSION),
    sourceCounts,
    "MIGRATION_ROW_CHECK_FAILED",
  );
  for (const tableName of Object.keys(CANDIDATE_V5_SCHEMA_COLUMNS)) {
    if (tableName in CANDIDATE_V4_SCHEMA_COLUMNS) continue;
    const count = database
      .prepare(`SELECT COUNT(*) AS count FROM "${tableName}"`)
      .get().count;
    if (count !== 0) {
      throw candidateMigrationError(
        "MIGRATION_ROW_CHECK_FAILED",
        "scheduler migration created unexpected schema-v5 rows",
      );
    }
  }
}

function cleanupCandidateBackupArtifacts(temporaryBackup, { includeMain = true } = {}) {
  const filenames = [
    ...(includeMain ? [temporaryBackup] : []),
    `${temporaryBackup}-journal`,
    `${temporaryBackup}-wal`,
    `${temporaryBackup}-shm`,
  ];
  const errors = [];
  for (const filename of filenames) {
    try {
      unlinkSync(filename);
    } catch (error) {
      if (error?.code !== "ENOENT") errors.push(error);
    }
  }
  return errors;
}

export async function migrateSchedulerStoreToCandidateV3({
  filename,
  backupFilename,
  onMigrationPhase,
  backupFunction = backupDatabase,
} = {}) {
  if (onMigrationPhase !== undefined && typeof onMigrationPhase !== "function") {
    throw new TypeError("onMigrationPhase must be a function");
  }
  if (typeof backupFunction !== "function") {
    throw new TypeError("backupFunction must be a function");
  }
  const paths = resolveCandidateMigrationPaths(filename, backupFilename);
  const database = new DatabaseSync(paths.source, { timeout: 5000 });
  let sourceVersion;
  let sourceCounts;
  let sourceDataVersion;
  try {
    sourceVersion = readExactSchemaVersion(database, ["1", "2"]);
    sourceCounts = attestCandidateMigrationSource(database, sourceVersion);
    sourceDataVersion = databaseDataVersion(database);
    invokeCandidateMigrationPhase(onMigrationPhase, "SOURCE_ATTESTED");

    let temporaryBackup = `${paths.backup}.candidate-${randomUUID()}.tmp`;
    let publishedBackupOwned = false;
    try {
      await backupFunction(database, temporaryBackup);
      invokeCandidateMigrationPhase(onMigrationPhase, "BACKUP_COMPLETE");

      const backup = new DatabaseSync(temporaryBackup, { timeout: 5000 });
      try {
        const backupVersion = readExactSchemaVersion(backup, [String(sourceVersion)]);
        const backupCounts = attestCandidateMigrationSource(backup, backupVersion);
        assertSameRowCounts(backupCounts, sourceCounts, "MIGRATION_BACKUP_INVALID");
        const journalMode = backup.prepare("PRAGMA journal_mode=DELETE").get();
        if (String(journalMode?.journal_mode).toLowerCase() !== "delete") {
          throw candidateMigrationError(
            "MIGRATION_BACKUP_INVALID",
            "scheduler migration backup is not self-contained",
          );
        }
      } finally {
        backup.close();
      }
      const sidecarCleanupErrors = cleanupCandidateBackupArtifacts(temporaryBackup, {
        includeMain: false,
      });
      if (sidecarCleanupErrors.length > 0) {
        throw new AggregateError(
          sidecarCleanupErrors,
          "candidate scheduler backup sidecar cleanup failed",
        );
      }
      attestCandidateMigrationPathAliases(paths);
      assertCandidateBackupDestinationAvailable(paths.backup);
      try {
        linkSync(temporaryBackup, paths.backup);
      } catch (error) {
        if (existsSync(paths.backup)) {
          throw candidateMigrationError(
            "MIGRATION_BACKUP_EXISTS",
            "scheduler migration backup already exists",
          );
        }
        throw error;
      }
      publishedBackupOwned = true;
      assertCandidateBackupHasNoSidecars(paths.backup);
      unlinkSync(temporaryBackup);
      temporaryBackup = null;
      publishedBackupOwned = false;
      invokeCandidateMigrationPhase(onMigrationPhase, "BACKUP_VALIDATED");
    } catch (error) {
      const cleanupErrors = [];
      if (publishedBackupOwned) {
        try {
          unlinkSync(paths.backup);
        } catch (cleanupError) {
          if (cleanupError?.code !== "ENOENT") cleanupErrors.push(cleanupError);
        }
      }
      if (temporaryBackup !== null) {
        cleanupErrors.push(...cleanupCandidateBackupArtifacts(temporaryBackup));
      }
      if (cleanupErrors.length > 0) {
        throw new AggregateError(
          [error, ...cleanupErrors],
          "candidate scheduler backup and cleanup failed",
          { cause: error },
        );
      }
      throw error;
    }

    database.exec("PRAGMA foreign_keys=OFF;");
    let failure = null;
    try {
      database.exec("BEGIN IMMEDIATE");
      invokeCandidateMigrationPhase(onMigrationPhase, "TRANSACTION_STARTED");
      if (databaseDataVersion(database) !== sourceDataVersion) {
        throw candidateMigrationError(
          "MIGRATION_SOURCE_CHANGED",
          "scheduler migration source changed",
        );
      }
      const currentVersion = readExactSchemaVersion(database, [String(sourceVersion)]);
      const currentCounts = attestCandidateMigrationSource(database, currentVersion);
      assertSameRowCounts(currentCounts, sourceCounts);
      invokeCandidateMigrationPhase(onMigrationPhase, "SOURCE_REATTESTED");

      if (sourceVersion === 1) rebuildV1ToV2WithinTransaction(database);
      database.exec(CANDIDATE_V3_SCHEMA_ADDITIONS_SQL);
      seedCandidateProjects(database);
      invokeCandidateMigrationPhase(onMigrationPhase, "SCHEMA_CREATED");

      assertCandidateAdditiveRows(database, sourceVersion, sourceCounts);
      invokeCandidateMigrationPhase(onMigrationPhase, "LEGACY_ROWS_VERIFIED");

      if (database.prepare("PRAGMA foreign_key_check").all().length !== 0) {
        throw unsupportedSchemaVersion();
      }
      invokeCandidateMigrationPhase(onMigrationPhase, "FOREIGN_KEYS_VERIFIED");

      const integrityRows = database.prepare("PRAGMA integrity_check").all();
      if (
        integrityRows.length !== 1 ||
        Object.values(integrityRows[0])[0] !== "ok"
      ) {
        throw unsupportedSchemaVersion();
      }
      invokeCandidateMigrationPhase(onMigrationPhase, "INTEGRITY_VERIFIED");

      const versionUpdate = database
        .prepare("UPDATE schema_meta SET value='3' WHERE key='schema_version'")
        .run();
      if (versionUpdate.changes !== 1) throw unsupportedSchemaVersion();
      invokeCandidateMigrationPhase(onMigrationPhase, "VERSION_UPDATED");

      validateKnownSchema(database, CANDIDATE_STORE_SCHEMA_V3_VERSION);
      invokeCandidateMigrationPhase(onMigrationPhase, "SCHEMA_VERIFIED");
      invokeCandidateMigrationPhase(onMigrationPhase, "BEFORE_COMMIT");
      database.exec("COMMIT");
      invokeCandidateMigrationPhase(onMigrationPhase, "COMMIT_COMPLETE");
    } catch (error) {
      failure = rollbackCandidateMigration(database, error);
    }
    failure = restoreCandidateForeignKeys(database, failure);
    if (failure !== null) throw failure;
  } finally {
    database.close();
  }

  const verification = openCandidateSchedulerStoreV3({ filename: paths.source });
  verification.close();
  return Object.freeze({
    sourceVersion,
    targetVersion: CANDIDATE_STORE_SCHEMA_V3_VERSION,
    backupFilename: paths.backup,
  });
}

export function openCandidateSchedulerStoreV3({ filename, now = Date.now } = {}) {
  if (
    typeof filename !== "string" ||
    filename.trim() === "" ||
    filename === ":memory:"
  ) {
    throw new TypeError("candidate schema-v3 filename is required");
  }
  if (typeof now !== "function") throw new TypeError("now must be a function");
  const databaseFilename = path.resolve(filename);
  if (!existsSync(databaseFilename) || !statSync(databaseFilename).isFile()) {
    throw new TypeError("candidate schema-v3 database must exist");
  }
  const database = new DatabaseSync(databaseFilename, { timeout: 5000 });
  try {
    readExactSchemaVersion(database, [String(CANDIDATE_STORE_SCHEMA_V3_VERSION)]);
    validateKnownSchema(database, CANDIDATE_STORE_SCHEMA_V3_VERSION);
    assertCandidateDatabaseHealth(database);
    database.exec("PRAGMA journal_mode=WAL;");
    database.exec("PRAGMA synchronous=FULL;");
    database.exec("PRAGMA foreign_keys=ON;");
    database.exec("PRAGMA busy_timeout=5000;");
  } catch (error) {
    database.close();
    throw error;
  }
  return new SchedulerStore(database, now, {
    legacyProtocolWritable: false,
    candidateCostCapability: CANDIDATE_COST_CAPABILITY,
  });
}

export async function migrateSchedulerStoreToCandidateV4({
  filename,
  backupFilename,
  onMigrationPhase,
  backupFunction = backupDatabase,
} = {}) {
  if (onMigrationPhase !== undefined && typeof onMigrationPhase !== "function") {
    throw new TypeError("onMigrationPhase must be a function");
  }
  if (typeof backupFunction !== "function") {
    throw new TypeError("backupFunction must be a function");
  }
  const paths = resolveCandidateMigrationPaths(filename, backupFilename);
  const database = new DatabaseSync(paths.source, { timeout: 5000 });
  let sourceVersion;
  let sourceCounts;
  let sourceDataVersion;
  try {
    sourceVersion = readExactSchemaVersion(database, [
      String(CANDIDATE_STORE_SCHEMA_V3_VERSION),
    ]);
    sourceCounts = attestCandidateV4MigrationSource(database);
    sourceDataVersion = databaseDataVersion(database);
    invokeCandidateMigrationPhase(onMigrationPhase, "SOURCE_ATTESTED");

    let temporaryBackup = `${paths.backup}.candidate-${randomUUID()}.tmp`;
    let publishedBackupOwned = false;
    try {
      await backupFunction(database, temporaryBackup);
      invokeCandidateMigrationPhase(onMigrationPhase, "BACKUP_COMPLETE");

      const backup = new DatabaseSync(temporaryBackup, { timeout: 5000 });
      try {
        const backupVersion = readExactSchemaVersion(backup, [
          String(CANDIDATE_STORE_SCHEMA_V3_VERSION),
        ]);
        if (backupVersion !== sourceVersion) throw unsupportedSchemaVersion();
        const backupCounts = attestCandidateV4MigrationSource(backup);
        assertSameRowCounts(backupCounts, sourceCounts, "MIGRATION_BACKUP_INVALID");
        const journalMode = backup.prepare("PRAGMA journal_mode=DELETE").get();
        if (String(journalMode?.journal_mode).toLowerCase() !== "delete") {
          throw candidateMigrationError(
            "MIGRATION_BACKUP_INVALID",
            "scheduler migration backup is not self-contained",
          );
        }
      } finally {
        backup.close();
      }
      const sidecarCleanupErrors = cleanupCandidateBackupArtifacts(temporaryBackup, {
        includeMain: false,
      });
      if (sidecarCleanupErrors.length > 0) {
        throw new AggregateError(
          sidecarCleanupErrors,
          "candidate scheduler backup sidecar cleanup failed",
        );
      }
      attestCandidateMigrationPathAliases(paths);
      assertCandidateBackupDestinationAvailable(paths.backup);
      try {
        linkSync(temporaryBackup, paths.backup);
      } catch (error) {
        if (existsSync(paths.backup)) {
          throw candidateMigrationError(
            "MIGRATION_BACKUP_EXISTS",
            "scheduler migration backup already exists",
          );
        }
        throw error;
      }
      publishedBackupOwned = true;
      assertCandidateBackupHasNoSidecars(paths.backup);
      unlinkSync(temporaryBackup);
      temporaryBackup = null;
      publishedBackupOwned = false;
      invokeCandidateMigrationPhase(onMigrationPhase, "BACKUP_VALIDATED");
    } catch (error) {
      const cleanupErrors = [];
      if (publishedBackupOwned) {
        try {
          unlinkSync(paths.backup);
        } catch (cleanupError) {
          if (cleanupError?.code !== "ENOENT") cleanupErrors.push(cleanupError);
        }
      }
      if (temporaryBackup !== null) {
        cleanupErrors.push(...cleanupCandidateBackupArtifacts(temporaryBackup));
      }
      if (cleanupErrors.length > 0) {
        throw new AggregateError(
          [error, ...cleanupErrors],
          "candidate scheduler backup and cleanup failed",
          { cause: error },
        );
      }
      throw error;
    }

    database.exec("PRAGMA foreign_keys=OFF;");
    let failure = null;
    try {
      database.exec("BEGIN IMMEDIATE");
      invokeCandidateMigrationPhase(onMigrationPhase, "TRANSACTION_STARTED");
      if (databaseDataVersion(database) !== sourceDataVersion) {
        throw candidateMigrationError(
          "MIGRATION_SOURCE_CHANGED",
          "scheduler migration source changed",
        );
      }
      const currentVersion = readExactSchemaVersion(database, [
        String(CANDIDATE_STORE_SCHEMA_V3_VERSION),
      ]);
      if (currentVersion !== sourceVersion) throw unsupportedSchemaVersion();
      const currentCounts = attestCandidateV4MigrationSource(database);
      assertSameRowCounts(currentCounts, sourceCounts);
      invokeCandidateMigrationPhase(onMigrationPhase, "SOURCE_REATTESTED");

      database.exec(CANDIDATE_V4_SCHEMA_ADDITIONS_SQL);
      invokeCandidateMigrationPhase(onMigrationPhase, "SCHEMA_CREATED");

      assertCandidateV4AdditiveRows(database, sourceCounts);
      invokeCandidateMigrationPhase(onMigrationPhase, "LEGACY_ROWS_VERIFIED");

      if (database.prepare("PRAGMA foreign_key_check").all().length !== 0) {
        throw unsupportedSchemaVersion();
      }
      invokeCandidateMigrationPhase(onMigrationPhase, "FOREIGN_KEYS_VERIFIED");

      const integrityRows = database.prepare("PRAGMA integrity_check").all();
      if (
        integrityRows.length !== 1 ||
        Object.values(integrityRows[0])[0] !== "ok"
      ) {
        throw unsupportedSchemaVersion();
      }
      invokeCandidateMigrationPhase(onMigrationPhase, "INTEGRITY_VERIFIED");

      const versionUpdate = database
        .prepare("UPDATE schema_meta SET value='4' WHERE key='schema_version'")
        .run();
      if (versionUpdate.changes !== 1) throw unsupportedSchemaVersion();
      invokeCandidateMigrationPhase(onMigrationPhase, "VERSION_UPDATED");

      validateKnownSchema(database, CANDIDATE_STORE_SCHEMA_V4_VERSION);
      invokeCandidateMigrationPhase(onMigrationPhase, "SCHEMA_VERIFIED");
      invokeCandidateMigrationPhase(onMigrationPhase, "BEFORE_COMMIT");
      database.exec("COMMIT");
      invokeCandidateMigrationPhase(onMigrationPhase, "COMMIT_COMPLETE");
    } catch (error) {
      failure = rollbackCandidateMigration(database, error);
    }
    failure = restoreCandidateForeignKeys(database, failure);
    if (failure !== null) throw failure;
  } finally {
    database.close();
  }

  const verification = openCandidateSchedulerStoreV4({ filename: paths.source });
  verification.close();
  return Object.freeze({
    sourceVersion,
    targetVersion: CANDIDATE_STORE_SCHEMA_V4_VERSION,
    backupFilename: paths.backup,
  });
}

export function openCandidateSchedulerStoreV4({ filename, now = Date.now } = {}) {
  if (
    typeof filename !== "string" ||
    filename.trim() === "" ||
    filename === ":memory:"
  ) {
    throw new TypeError("candidate schema-v4 filename is required");
  }
  if (typeof now !== "function") throw new TypeError("now must be a function");
  const databaseFilename = path.resolve(filename);
  if (!existsSync(databaseFilename) || !statSync(databaseFilename).isFile()) {
    throw new TypeError("candidate schema-v4 database must exist");
  }
  const database = new DatabaseSync(databaseFilename, { timeout: 5000 });
  try {
    readExactSchemaVersion(database, [String(CANDIDATE_STORE_SCHEMA_V4_VERSION)]);
    validateKnownSchema(database, CANDIDATE_STORE_SCHEMA_V4_VERSION);
    assertCandidateDatabaseHealth(database);
    database.exec("PRAGMA journal_mode=WAL;");
    database.exec("PRAGMA synchronous=FULL;");
    database.exec("PRAGMA foreign_keys=ON;");
    database.exec("PRAGMA busy_timeout=5000;");
  } catch (error) {
    database.close();
    throw error;
  }
  return new SchedulerStore(database, now, {
    legacyProtocolWritable: false,
    candidateTransmissionCostCapability: CANDIDATE_TRANSMISSION_COST_CAPABILITY,
  });
}

export async function migrateSchedulerStoreToCandidateV5({
  filename,
  backupFilename,
  onMigrationPhase,
  backupFunction = backupDatabase,
} = {}) {
  if (onMigrationPhase !== undefined && typeof onMigrationPhase !== "function") {
    throw new TypeError("onMigrationPhase must be a function");
  }
  if (typeof backupFunction !== "function") {
    throw new TypeError("backupFunction must be a function");
  }
  const paths = resolveCandidateMigrationPaths(filename, backupFilename);
  const database = new DatabaseSync(paths.source, { timeout: 5000 });
  let sourceVersion;
  let sourceCounts;
  let sourceDataVersion;
  try {
    sourceVersion = readExactSchemaVersion(database, [
      String(CANDIDATE_STORE_SCHEMA_V4_VERSION),
    ]);
    sourceCounts = attestCandidateV5MigrationSource(database);
    sourceDataVersion = databaseDataVersion(database);
    invokeCandidateMigrationPhase(onMigrationPhase, "SOURCE_ATTESTED");

    let temporaryBackup = `${paths.backup}.candidate-${randomUUID()}.tmp`;
    let publishedBackupOwned = false;
    try {
      await backupFunction(database, temporaryBackup);
      invokeCandidateMigrationPhase(onMigrationPhase, "BACKUP_COMPLETE");

      const backup = new DatabaseSync(temporaryBackup, { timeout: 5000 });
      try {
        const backupVersion = readExactSchemaVersion(backup, [
          String(CANDIDATE_STORE_SCHEMA_V4_VERSION),
        ]);
        if (backupVersion !== sourceVersion) throw unsupportedSchemaVersion();
        const backupCounts = attestCandidateV5MigrationSource(backup);
        assertSameRowCounts(backupCounts, sourceCounts, "MIGRATION_BACKUP_INVALID");
        const journalMode = backup.prepare("PRAGMA journal_mode=DELETE").get();
        if (String(journalMode?.journal_mode).toLowerCase() !== "delete") {
          throw candidateMigrationError(
            "MIGRATION_BACKUP_INVALID",
            "scheduler migration backup is not self-contained",
          );
        }
      } finally {
        backup.close();
      }
      const sidecarCleanupErrors = cleanupCandidateBackupArtifacts(temporaryBackup, {
        includeMain: false,
      });
      if (sidecarCleanupErrors.length > 0) {
        throw new AggregateError(
          sidecarCleanupErrors,
          "candidate scheduler backup sidecar cleanup failed",
        );
      }
      attestCandidateMigrationPathAliases(paths);
      assertCandidateBackupDestinationAvailable(paths.backup);
      try {
        linkSync(temporaryBackup, paths.backup);
      } catch (error) {
        if (existsSync(paths.backup)) {
          throw candidateMigrationError(
            "MIGRATION_BACKUP_EXISTS",
            "scheduler migration backup already exists",
          );
        }
        throw error;
      }
      publishedBackupOwned = true;
      assertCandidateBackupHasNoSidecars(paths.backup);
      unlinkSync(temporaryBackup);
      temporaryBackup = null;
      publishedBackupOwned = false;
      invokeCandidateMigrationPhase(onMigrationPhase, "BACKUP_VALIDATED");
    } catch (error) {
      const cleanupErrors = [];
      if (publishedBackupOwned) {
        try {
          unlinkSync(paths.backup);
        } catch (cleanupError) {
          if (cleanupError?.code !== "ENOENT") cleanupErrors.push(cleanupError);
        }
      }
      if (temporaryBackup !== null) {
        cleanupErrors.push(...cleanupCandidateBackupArtifacts(temporaryBackup));
      }
      if (cleanupErrors.length > 0) {
        throw new AggregateError(
          [error, ...cleanupErrors],
          "candidate scheduler backup and cleanup failed",
          { cause: error },
        );
      }
      throw error;
    }

    database.exec("PRAGMA foreign_keys=OFF;");
    let failure = null;
    try {
      database.exec("BEGIN IMMEDIATE");
      invokeCandidateMigrationPhase(onMigrationPhase, "TRANSACTION_STARTED");
      if (databaseDataVersion(database) !== sourceDataVersion) {
        throw candidateMigrationError(
          "MIGRATION_SOURCE_CHANGED",
          "scheduler migration source changed",
        );
      }
      const currentVersion = readExactSchemaVersion(database, [
        String(CANDIDATE_STORE_SCHEMA_V4_VERSION),
      ]);
      if (currentVersion !== sourceVersion) throw unsupportedSchemaVersion();
      const currentCounts = attestCandidateV5MigrationSource(database);
      assertSameRowCounts(currentCounts, sourceCounts);
      invokeCandidateMigrationPhase(onMigrationPhase, "SOURCE_REATTESTED");

      database.exec(CANDIDATE_V5_SCHEMA_ADDITIONS_SQL);
      invokeCandidateMigrationPhase(onMigrationPhase, "SCHEMA_CREATED");

      assertCandidateV5AdditiveRows(database, sourceCounts);
      invokeCandidateMigrationPhase(onMigrationPhase, "LEGACY_ROWS_VERIFIED");

      if (database.prepare("PRAGMA foreign_key_check").all().length !== 0) {
        throw unsupportedSchemaVersion();
      }
      invokeCandidateMigrationPhase(onMigrationPhase, "FOREIGN_KEYS_VERIFIED");

      const integrityRows = database.prepare("PRAGMA integrity_check").all();
      if (
        integrityRows.length !== 1 ||
        Object.values(integrityRows[0])[0] !== "ok"
      ) {
        throw unsupportedSchemaVersion();
      }
      invokeCandidateMigrationPhase(onMigrationPhase, "INTEGRITY_VERIFIED");

      const versionUpdate = database
        .prepare("UPDATE schema_meta SET value='5' WHERE key='schema_version'")
        .run();
      if (versionUpdate.changes !== 1) throw unsupportedSchemaVersion();
      invokeCandidateMigrationPhase(onMigrationPhase, "VERSION_UPDATED");

      validateKnownSchema(database, CANDIDATE_STORE_SCHEMA_VERSION);
      invokeCandidateMigrationPhase(onMigrationPhase, "SCHEMA_VERIFIED");
      invokeCandidateMigrationPhase(onMigrationPhase, "BEFORE_COMMIT");
      database.exec("COMMIT");
      invokeCandidateMigrationPhase(onMigrationPhase, "COMMIT_COMPLETE");
    } catch (error) {
      failure = rollbackCandidateMigration(database, error);
    }
    failure = restoreCandidateForeignKeys(database, failure);
    if (failure !== null) throw failure;
  } finally {
    database.close();
  }

  const verification = openCandidateSchedulerStoreV5({ filename: paths.source });
  verification.close();
  return Object.freeze({
    sourceVersion,
    targetVersion: CANDIDATE_STORE_SCHEMA_VERSION,
    backupFilename: paths.backup,
  });
}

export function openCandidateSchedulerStoreV5({ filename, now = Date.now } = {}) {
  if (
    typeof filename !== "string" ||
    filename.trim() === "" ||
    filename === ":memory:"
  ) {
    throw new TypeError("candidate schema-v5 filename is required");
  }
  if (typeof now !== "function") throw new TypeError("now must be a function");
  const databaseFilename = path.resolve(filename);
  if (!existsSync(databaseFilename) || !statSync(databaseFilename).isFile()) {
    throw new TypeError("candidate schema-v5 database must exist");
  }
  const database = new DatabaseSync(databaseFilename, { timeout: 5000 });
  try {
    readExactSchemaVersion(database, [String(CANDIDATE_STORE_SCHEMA_VERSION)]);
    validateKnownSchema(database, CANDIDATE_STORE_SCHEMA_VERSION);
    assertCandidateDatabaseHealth(database);
    database.exec("PRAGMA journal_mode=WAL;");
    database.exec("PRAGMA synchronous=FULL;");
    database.exec("PRAGMA foreign_keys=ON;");
    database.exec("PRAGMA busy_timeout=5000;");
  } catch (error) {
    database.close();
    throw error;
  }
  return new SchedulerStore(database, now, {
    legacyProtocolWritable: false,
    candidateTransmissionCostCapability: CANDIDATE_TRANSMISSION_COST_CAPABILITY,
  });
}

export function readCandidateActivationQuiescenceSnapshot({
  filename,
  projectId,
  now = Date.now,
} = {}) {
  if (
    typeof filename !== "string" ||
    filename.trim() === "" ||
    filename === ":memory:"
  ) {
    throw new TypeError("candidate activation-preflight filename is required");
  }
  if (typeof now !== "function") throw new TypeError("now must be a function");
  const exactProjectId = requireCostProjectId(projectId);
  const databaseFilename = path.resolve(filename);
  if (!existsSync(databaseFilename) || !statSync(databaseFilename).isFile()) {
    throw new TypeError("candidate activation-preflight database must exist");
  }
  const canonicalFilename = realpathSync.native(databaseFilename);
  const before = statSync(canonicalFilename, { bigint: true });
  const database = new DatabaseSync(canonicalFilename, {
    readOnly: true,
    timeout: 5000,
  });
  let snapshot;
  try {
    readExactSchemaVersion(database, [String(CANDIDATE_STORE_SCHEMA_VERSION)]);
    validateKnownSchema(database, CANDIDATE_STORE_SCHEMA_VERSION);
    assertCandidateDatabaseHealth(database);
    database.exec("PRAGMA query_only=ON;");
    database.exec("PRAGMA foreign_keys=ON;");
    database.exec("PRAGMA busy_timeout=5000;");
    const store = new SchedulerStore(database, now, {
      legacyProtocolWritable: false,
      candidateTransmissionCostCapability:
        CANDIDATE_TRANSMISSION_COST_CAPABILITY,
    });
    try {
      snapshot = store.getActivationQuiescenceSnapshot(exactProjectId);
    } finally {
      store.close();
    }
  } catch (error) {
    try {
      database.close();
    } catch {
      // The exact read-only handle may already have been closed.
    }
    throw error;
  }
  const after = statSync(canonicalFilename, { bigint: true });
  return Object.freeze({
    ...snapshot,
    storePath: canonicalFilename,
    storeIdentityHash: candidateSha256(
      `deepluna-activation-store-v1\0${filesystemPathIdentity(canonicalFilename)}`,
    ),
    readOnlyUnchanged:
      before.size === after.size && before.mtimeNs === after.mtimeNs,
    fileSizeBytes: Number(after.size),
    fileMtimeNs: after.mtimeNs.toString(),
  });
}

export function openSchedulerStore({ filename, now = Date.now } = {}) {
  if (typeof filename !== "string" || filename.trim() === "") {
    throw new TypeError("filename is required");
  }
  if (typeof now !== "function") throw new TypeError("now must be a function");

  const databaseFilename = filename === ":memory:" ? filename : path.resolve(filename);
  if (databaseFilename !== ":memory:") {
    mkdirSync(path.dirname(databaseFilename), { recursive: true });
  }

  const database = new DatabaseSync(databaseFilename, { timeout: 5000 });
  try {
    const schemaMetaExists =
      database
        .prepare(
          `SELECT 1 AS present
           FROM sqlite_master
           WHERE type = 'table' AND name = 'schema_meta'`,
        )
        .get() !== undefined;
    let existingVersion = null;
    if (schemaMetaExists) {
      let versionRows;
      try {
        versionRows = database
          .prepare("SELECT value FROM schema_meta WHERE key = 'schema_version'")
          .all();
      } catch {
        throw unsupportedSchemaVersion();
      }
      if (versionRows.length !== 1 || !["1", "2"].includes(versionRows[0].value)) {
        throw unsupportedSchemaVersion();
      }
      existingVersion = Number(versionRows[0].value);
      if (existingVersion === 1) migrateV1ToV2(database);
      else validateKnownSchema(database, STORE_SCHEMA_VERSION);
    } else {
      const existingObject = database
        .prepare(
          `SELECT 1 AS present
           FROM sqlite_master
           WHERE type IN ('table', 'index', 'view', 'trigger')
             AND name NOT GLOB 'sqlite_*'
           LIMIT 1`,
        )
        .get();
      if (existingObject !== undefined) {
        throw unsupportedSchemaVersion();
      }
    }

    database.exec("PRAGMA journal_mode=WAL;");
    database.exec("PRAGMA synchronous=FULL;");
    database.exec("PRAGMA foreign_keys=ON;");
    database.exec("PRAGMA busy_timeout=5000;");
    database.exec("BEGIN IMMEDIATE");
    try {
      database.exec(SCHEMA_SQL);
      if (!schemaMetaExists) {
        database
          .prepare(
            `INSERT INTO schema_meta (key, value)
             VALUES ('schema_version', ?)`,
          )
          .run(String(STORE_SCHEMA_VERSION));
      }
      database.exec("COMMIT");
      validateKnownSchema(database, STORE_SCHEMA_VERSION);
    } catch (error) {
      let rollbackError;
      if (database.isTransaction) {
        try {
          database.exec("ROLLBACK");
        } catch (caughtRollbackError) {
          rollbackError = caughtRollbackError;
        }
      }
      if (rollbackError !== undefined) {
        throw new AggregateError(
          [error, rollbackError],
          "scheduler transaction and rollback both failed",
          { cause: error },
        );
      }
      throw error;
    }
  } catch (error) {
    database.close();
    throw error;
  }

  return new SchedulerStore(database, now);
}
