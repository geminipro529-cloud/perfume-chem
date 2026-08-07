import crypto from "node:crypto";
import { existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import path from "node:path";

const PROJECT_ID = /^[a-z0-9][a-z0-9._-]{2,63}$/;
const PROJECT_STORE_SCOPE = Object.freeze({
  project: "project",
  thread: "thread",
});
const PROJECT_SCOPE_THREAD_TOKEN = /^[a-f0-9]{16,64}$/;

function hmacHex(projectSecret, value) {
  return crypto.createHmac("sha256", projectSecret).update(value).digest("hex");
}

export function resolveProjectId(value, workspace = process.cwd()) {
  const raw = String(value ?? "").trim().toLowerCase();
  const normalized = raw
    ? raw.replace(/\s+/g, "-")
    : `workspace-${crypto.createHash("sha256").update(path.resolve(workspace)).digest("hex").slice(0, 20)}`;
  if (!PROJECT_ID.test(normalized) || normalized.includes("..")) {
    throw new Error("project id must be 3-64 lowercase letters, digits, dot, underscore, or hyphen");
  }
  return normalized;
}

export function resolveProjectScope(value = "project") {
  const normalized = String(value ?? "project").trim().toLowerCase();
  if (!Object.values(PROJECT_STORE_SCOPE).includes(normalized)) {
    throw new Error("project scope must be one of: project, thread");
  }
  return normalized;
}

function resolveThreadScope(threadScope) {
  const normalized = String(threadScope ?? "").trim().toLowerCase();
  if (!PROJECT_SCOPE_THREAD_TOKEN.test(normalized)) {
    throw new Error("thread scope must be 16-64 lower-case hex characters");
  }
  return normalized;
}

function scopedProjectId(projectId, scope, threadScope) {
  if (scope === PROJECT_STORE_SCOPE.project) return projectId;
  return `${projectId}-thread-${resolveThreadScope(threadScope)}`;
}

export function projectStorePaths(storeRoot, projectId, {
  scope = PROJECT_STORE_SCOPE.project,
  threadScope = null,
} = {}) {
  const normalizedProjectId = resolveProjectId(projectId);
  const resolvedScope = resolveProjectScope(scope);
  const projectRootId = scopedProjectId(normalizedProjectId, resolvedScope, threadScope);
  const projectRoot = path.join(path.resolve(storeRoot), "projects", projectRootId);
  return Object.freeze({
    projectRoot,
    jobsRoot: path.join(projectRoot, "jobs"),
    cacheRoot: path.join(projectRoot, "cache", "results"),
    lockRoot: path.join(projectRoot, "locks"),
    batchesRoot: path.join(projectRoot, "batches"),
    headsRoot: path.join(projectRoot, "heads"),
    workerStatePath: path.join(projectRoot, "worker-state-v5.json"),
    workerStateLockPath: path.join(projectRoot, "worker-state-v5.lock"),
    legacyRoot: path.resolve(storeRoot),
  });
}

export function ensureProjectSecret(projectRoot, randomBytes = crypto.randomBytes) {
  mkdirSync(projectRoot, { recursive: true });
  const secretPath = path.join(projectRoot, ".project-secret");
  if (!existsSync(secretPath)) {
    writeFileSync(secretPath, randomBytes(32).toString("hex"), {
      encoding: "utf8",
      mode: 0o600,
      flag: "wx",
    });
  }
  const secret = readFileSync(secretPath, "utf8").trim();
  if (!/^[a-f0-9]{64}$/.test(secret)) throw new Error("project secret is invalid");
  return secret;
}

export function deriveOriginContext(threadId, projectSecret) {
  const id = String(threadId ?? "").trim();
  if (!id) throw new Error("CODEX_THREAD_ID is required for task ownership");
  return Object.freeze({
    originThreadHash: hmacHex(projectSecret, `thread:${id}`),
    originCapabilityHash: hmacHex(projectSecret, `capability:${id}`),
  });
}

export function deriveWorkspaceInstanceId(workspace, projectSecret) {
  const canonical = realpathSync(path.resolve(workspace));
  const identity = process.platform === "win32" ? canonical.toLowerCase() : canonical;
  return `WS-${hmacHex(projectSecret, `workspace:${identity}`).slice(0, 32)}`;
}

export function deriveAttemptId(jobId, ordinal, route, projectSecret) {
  if (!Number.isInteger(ordinal) || ordinal < 1 || ordinal > 99) {
    throw new Error("attempt ordinal must be 1 to 99");
  }
  const normalizedJobId = String(jobId ?? "").trim();
  const normalizedRoute = String(route ?? "").trim().toUpperCase();
  if (!normalizedJobId || !normalizedRoute) {
    throw new Error("job id and route are required for attempt identity");
  }
  const digest = hmacHex(
    projectSecret,
    `attempt:${normalizedJobId}:${ordinal}:${normalizedRoute}`,
  );
  return `AT-${String(ordinal).padStart(2, "0")}-${digest.slice(0, 16)}`;
}

export function assertOriginOwns(record, origin) {
  if (
    record?.originThreadHash !== origin.originThreadHash ||
    record?.originCapabilityHash !== origin.originCapabilityHash
  ) {
    throw new Error("job is not owned by this Codex task");
  }
}
