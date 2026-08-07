import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { containsUnsafePublicText } from "./public-text-security.mjs";

function deepFreeze(value, seen = new Set()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (descriptor && Object.hasOwn(descriptor, "value")) {
      deepFreeze(descriptor.value, seen);
    }
  }
  return Object.freeze(value);
}

export const CANDIDATE_RUNTIME_MANIFEST_FILES = deepFreeze([
  "lib/batch-dag.mjs",
  "lib/candidate-runtime.mjs",
  "lib/capacity-policy.mjs",
  "lib/daemon-protocol-v2.mjs",
  "lib/deepseek-v4-tokenizer.mjs",
  "lib/evidence-protocol.mjs",
  "lib/execution-kernel.mjs",
  "lib/identity.mjs",
  "lib/provider-pools.mjs",
  "lib/public-text-security.mjs",
  "lib/result-protocol.mjs",
  "lib/scheduler-store.mjs",
  "lib/security.mjs",
  "lib/transmission-budget-controller.mjs",
  "local-executor.mjs",
  "orchestrator-daemon.mjs",
  "package-lock.json",
  "package.json",
  "server.mjs",
  "vendor/deepseek-v4-flash/60d8d70770c6776ff598c94bb586a859a38244f1/encoding/encoding_dsv4.py",
  "vendor/deepseek-v4-flash/60d8d70770c6776ff598c94bb586a859a38244f1/tokenizer.json",
  "vendor/deepseek-v4-flash/60d8d70770c6776ff598c94bb586a859a38244f1/tokenizer_config.json",
]);

function candidateRuntimeBuildHash() {
  const runtimeRoot = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
  );
  const digest = crypto.createHash("sha256");
  digest.update("DEEPLUNA_RUNTIME_MANIFEST_V1\0", "utf8");
  for (const relative of CANDIDATE_RUNTIME_MANIFEST_FILES) {
    const bytes = readFileSync(path.join(runtimeRoot, relative));
    digest.update(relative, "utf8");
    digest.update("\0", "utf8");
    digest.update(String(bytes.byteLength), "utf8");
    digest.update("\0", "utf8");
    digest.update(bytes);
    digest.update("\0", "utf8");
  }
  return digest.digest("hex");
}

export const CANDIDATE_RUNTIME_BUILD_HASH = candidateRuntimeBuildHash();
export const CANDIDATE_PROCESS_BOOT_ID =
  `DI-${crypto.randomBytes(16).toString("hex")}`;
export const CANDIDATE_PROCESS_STARTED_AT_MS = Math.max(
  1,
  Math.floor(Date.now() - (process.uptime() * 1000)),
);

export const CANDIDATE_DAEMON_RELEASE = "0.9.9";
export const CANDIDATE_DAEMON_PROTOCOL_VERSION = 3;
export const CANDIDATE_DAEMON_RPC_SCHEMA_VERSION = 2;
export const CANDIDATE_DAEMON_REQUIRED_STORE_SCHEMA_VERSION = 5;
export const CANDIDATE_DAEMON_RUNTIME_ACCEPTED = true;
export const CANDIDATE_DAEMON_HANDSHAKE_DOMAIN = "DEEPLUNA_DAEMON_V3";

export const CANDIDATE_DAEMON_REQUIRED_CAPABILITIES = deepFreeze([
  "accounting-policy-transition-v1",
  "batch-dag-v1",
  "detach-without-cancel-v1",
  "durable-sol-head-producer-v1",
  "durable-mutation-replay-v1",
  "max-one-shot-v1",
  "normalized-result-packet-v1",
  "origin-bound-session-v1",
  "public-identities-v1",
  "runtime-build-identity-v1",
  "sol-head-v1",
  "typed-rpc-v1",
]);

export const CANDIDATE_DAEMON_RPC_METHODS = deepFreeze([
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

export const CANDIDATE_DAEMON_ALLOWED_ERROR_CODES = deepFreeze([
  "ACTIVATION_DISABLED",
  "AUTH_FAILED",
  "CAPABILITY_MISMATCH",
  "DAEMON_BUSY",
  "DAEMON_TIMEOUT",
  "INTERNAL_ERROR",
  "INVALID_REQUEST",
  "JOB_TERMINAL",
  "MAX_ATTEMPT_EXHAUSTED",
  "NOT_FOUND_OR_NOT_OWNED",
  "PROTOCOL_MISMATCH",
  "REQUEST_ID_CONFLICT",
  "REQUEST_IN_PROGRESS",
  "REQUEST_TOO_LARGE",
  "UNKNOWN_METHOD",
]);

const CANDIDATE_DAEMON_PUBLIC_ERROR_POLICY = deepFreeze({
  AUTH_FAILED: { message: "authentication failed", retryable: false },
  PROTOCOL_MISMATCH: { message: "protocol mismatch", retryable: false },
  CAPABILITY_MISMATCH: { message: "capability mismatch", retryable: false },
  ACTIVATION_DISABLED: { message: "daemon activation is disabled", retryable: false },
  INVALID_REQUEST: { message: "request rejected", retryable: false },
  UNKNOWN_METHOD: { message: "unknown request method", retryable: false },
  REQUEST_TOO_LARGE: {
    message: "request exceeds the allowed size",
    retryable: false,
  },
  REQUEST_ID_CONFLICT: {
    message: "request conflicts with durable identity",
    retryable: false,
  },
  REQUEST_IN_PROGRESS: { message: "request is in progress", retryable: true },
  NOT_FOUND_OR_NOT_OWNED: { message: "resource not found", retryable: false },
  JOB_TERMINAL: { message: "job is terminal", retryable: false },
  MAX_ATTEMPT_EXHAUSTED: {
    message: "maximum effort attempt is exhausted",
    retryable: false,
  },
  DAEMON_BUSY: { message: "daemon capacity is busy", retryable: true },
  DAEMON_TIMEOUT: { message: "daemon request timed out", retryable: true },
  INTERNAL_ERROR: { message: "daemon request failed", retryable: false },
});

const CANDIDATE_PUBLIC_STATUSES = deepFreeze([
  "QUEUED",
  "RUNNING",
  "PASS",
  "CACHED",
  "FAIL",
  "BLOCKED",
]);
const CANDIDATE_PUBLIC_EXECUTION_STATUSES = deepFreeze([
  "ACCEPTED",
  "INCOMPLETE",
  "BLOCKED",
  "PROVIDER_ERROR",
  "CONTRACT_ERROR",
  "CANCELLED",
]);
const CANDIDATE_PUBLIC_EVIDENCE_VERDICTS = deepFreeze([
  "POSITIVE",
  "NEGATIVE",
  "NULL",
  "MIXED",
  "UNRESOLVED",
  "NOT_APPLICABLE",
]);
const CANDIDATE_HEAD_DECISIONS = deepFreeze([
  "DELEGATE_DEEPLUNA",
  "HANDLE_CURRENT",
  "START_SOL_HEAD",
]);
const CANDIDATE_SOL_EFFORTS = deepFreeze(["medium", "high", "xhigh", "max"]);
const CANDIDATE_HEAD_REASON_CODES = deepFreeze([
  "active-effort-matches",
  "authority-domain",
  "delegation-overhead-dominates",
  "deterministic-deepluna-eligible",
  "max-one-shot-eligible",
  "reasoning-score",
]);

export const CANDIDATE_DAEMON_LIMITS = deepFreeze({
  maxFrameBytes: 65536,
  maxRpcResultBytes: 57344,
  maxResultPacketBytes: 49152,
  maxBatchNodes: 20,
  maxPendingRequests: 128,
});

export const CANDIDATE_DAEMON_WIRE_LIMITS = deepFreeze({
  maxFrameBytes: 65536,
  maxHandshakeBytes: 8192,
  maxRpcResultBytes: 57344,
  maxResultPacketBytes: 49152,
  maxRequestIdBytes: 128,
  maxMethodBytes: 32,
  maxErrorMessageBytes: 512,
  maxProjectIdBytes: 256,
  maxBatchNodes: 20,
  maxPendingRequests: 128,
});

const CANDIDATE_DAEMON_ACTIVATION = deepFreeze({
  hmacRequired: true,
  windowsAcl: "PROVEN",
  productionActivationEligible: true,
});

export const CANDIDATE_DAEMON_PROFILE = deepFreeze({
  protocol: 3,
  rpcSchema: 2,
  serverRelease: "0.9.9",
  storeSchema: CANDIDATE_DAEMON_REQUIRED_STORE_SCHEMA_VERSION,
  contractProtocol: 3,
  evidenceProtocol: 2,
  resultProtocol: 3,
  capabilities: CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
  methods: CANDIDATE_DAEMON_RPC_METHODS,
  limits: CANDIDATE_DAEMON_LIMITS,
  activation: CANDIDATE_DAEMON_ACTIVATION,
});

function captureExactObject(value, expectedKeys, label) {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new TypeError(`invalid ${label}`);
  }
  const ownKeys = Reflect.ownKeys(value);
  if (
    ownKeys.length !== expectedKeys.length ||
    ownKeys.some((key) => typeof key !== "string" || !expectedKeys.includes(key))
  ) {
    throw new TypeError(`invalid ${label}`);
  }
  const captured = new Map();
  for (const key of expectedKeys) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError(`invalid ${label}`);
    }
    captured.set(key, descriptor.value);
  }
  return captured;
}

function captureDenseArray(value, label) {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw new TypeError(`invalid ${label}`);
  }
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const lengthDescriptor = descriptors.length;
  if (
    lengthDescriptor === undefined ||
    !Object.hasOwn(lengthDescriptor, "value") ||
    !Number.isSafeInteger(lengthDescriptor.value) ||
    lengthDescriptor.value < 0
  ) {
    throw new TypeError(`invalid ${label}`);
  }
  const length = lengthDescriptor.value;
  const ownKeys = Reflect.ownKeys(descriptors);
  if (
    ownKeys.some((key) => typeof key !== "string") ||
    ownKeys.length !== length + 1 ||
    !ownKeys.includes("length")
  ) {
    throw new TypeError(`invalid ${label}`);
  }
  const captured = [];
  for (let index = 0; index < length; index += 1) {
    const key = String(index);
    const descriptor = descriptors[key];
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError(`invalid ${label}`);
    }
    captured.push(descriptor.value);
  }
  return captured;
}

const MAX_CANONICAL_DEPTH = 64;
const MAX_CANONICAL_NODES = 10000;

function encodeCanonical(value, state, depth) {
  if (depth > MAX_CANONICAL_DEPTH) {
    throw new TypeError("candidate canonical JSON depth limit exceeded");
  }
  state.nodes += 1;
  if (state.nodes > MAX_CANONICAL_NODES) {
    throw new TypeError("candidate canonical JSON node limit exceeded");
  }
  if (value === null) return "null";
  if (typeof value === "string" || typeof value === "boolean") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value) || Object.is(value, -0)) {
      throw new TypeError("candidate canonical JSON rejects unsafe numbers");
    }
    return JSON.stringify(value);
  }
  if (typeof value !== "object") {
    throw new TypeError("candidate canonical JSON requires JSON-safe values");
  }
  if (state.active.has(value)) {
    throw new TypeError("candidate canonical JSON rejects cyclic values");
  }
  state.active.add(value);
  try {
    if (Array.isArray(value)) {
      const captured = captureDenseArray(value, "candidate canonical JSON array");
      return `[${captured
        .map((entry) => encodeCanonical(entry, state, depth + 1))
        .join(",")}]`;
    }
    const ownKeys = Reflect.ownKeys(value);
    const stringKeys = ownKeys.filter((key) => typeof key === "string");
    const captured = captureExactObject(
      value,
      [...stringKeys].sort(),
      "candidate canonical JSON object",
    );
    const entries = [...captured]
      .map(
        ([key, entry]) =>
          `${JSON.stringify(key)}:${encodeCanonical(entry, state, depth + 1)}`,
      );
    return `{${entries.join(",")}}`;
  } finally {
    state.active.delete(value);
  }
}

export function canonicalCandidateDaemonJson(value) {
  return encodeCanonical(value, { active: new Set(), nodes: 0 }, 0);
}

export function candidateUtf8Bytes(value) {
  if (typeof value !== "string") throw new TypeError("candidate UTF-8 value must be a string");
  return Buffer.byteLength(value, "utf8");
}

function requireByteLimit(maxBytes) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0) {
    throw new TypeError("candidate byte limit must be a nonnegative safe integer");
  }
  return maxBytes;
}

export function assertCandidateUtf8ByteLimit(value, maxBytes) {
  const limit = requireByteLimit(maxBytes);
  if (candidateUtf8Bytes(value) > limit) {
    throw new TypeError("candidate UTF-8 byte limit exceeded");
  }
  return value;
}

export function candidateCanonicalJsonUtf8Bytes(value) {
  return Buffer.byteLength(canonicalCandidateDaemonJson(value), "utf8");
}

export function assertCandidateCanonicalJsonByteLimit(value, maxBytes) {
  const limit = requireByteLimit(maxBytes);
  if (candidateCanonicalJsonUtf8Bytes(value) > limit) {
    throw new TypeError("candidate canonical JSON byte limit exceeded");
  }
  return value;
}

export function candidateCanonicalSha256(value) {
  return crypto
    .createHash("sha256")
    .update(canonicalCandidateDaemonJson(value), "utf8")
    .digest("hex");
}

function captureSecret(secret) {
  if (!(secret instanceof Uint8Array) || secret.byteLength < 32) {
    throw new TypeError("invalid candidate daemon secret");
  }
  return Buffer.from(secret);
}

function hmacCandidateTranscript(secret, transcript) {
  return crypto
    .createHmac("sha256", captureSecret(secret))
    .update(canonicalCandidateDaemonJson(transcript), "utf8")
    .digest("hex");
}

function isLowerHex64(value) {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}

function timingSafeMacMatches(expected, actual) {
  const expectedValid = isLowerHex64(expected);
  const actualValid = isLowerHex64(actual);
  const expectedBytes = expectedValid ? Buffer.from(expected, "hex") : Buffer.alloc(32);
  const actualBytes = actualValid ? Buffer.from(actual, "hex") : Buffer.alloc(32);
  const equal = crypto.timingSafeEqual(expectedBytes, actualBytes);
  return expectedValid && actualValid && equal;
}

function requireLowerHex64(value, label) {
  if (!isLowerHex64(value)) throw new TypeError(`invalid ${label}`);
  return value;
}

function requireProjectId(value) {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    value.trim() !== value ||
    !/^[A-Za-z0-9._:-]+$/.test(value) ||
    value === "." ||
    value === ".."
  ) {
    throw new TypeError("invalid candidate project id");
  }
  assertCandidateUtf8ByteLimit(value, CANDIDATE_DAEMON_WIRE_LIMITS.maxProjectIdBytes);
  return value;
}

function requireExactStringArray(value, expected, label) {
  const captured = captureDenseArray(value, label);
  if (
    captured.length !== expected.length ||
    captured.some((entry, index) => entry !== expected[index])
  ) {
    throw new TypeError(`invalid ${label}`);
  }
  return value;
}

export function validateCandidateCapabilityProfile(value) {
  const profile = captureExactObject(
    value,
    [
      "protocol",
      "rpcSchema",
      "serverRelease",
      "storeSchema",
      "contractProtocol",
      "evidenceProtocol",
      "resultProtocol",
      "capabilities",
      "methods",
      "limits",
      "activation",
    ],
    "candidate daemon profile",
  );
  if (
    profile.get("protocol") !== CANDIDATE_DAEMON_PROTOCOL_VERSION ||
    profile.get("rpcSchema") !== CANDIDATE_DAEMON_RPC_SCHEMA_VERSION ||
    profile.get("serverRelease") !== CANDIDATE_DAEMON_RELEASE ||
    profile.get("storeSchema") !== CANDIDATE_DAEMON_REQUIRED_STORE_SCHEMA_VERSION ||
    profile.get("contractProtocol") !== 3 ||
    profile.get("evidenceProtocol") !== 2 ||
    profile.get("resultProtocol") !== 3
  ) {
    throw new TypeError("invalid candidate daemon profile");
  }
  requireExactStringArray(
    profile.get("capabilities"),
    CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
    "candidate capabilities",
  );
  requireExactStringArray(
    profile.get("methods"),
    CANDIDATE_DAEMON_RPC_METHODS,
    "candidate RPC methods",
  );
  const limits = captureExactObject(
    profile.get("limits"),
    [
      "maxFrameBytes",
      "maxRpcResultBytes",
      "maxResultPacketBytes",
      "maxBatchNodes",
      "maxPendingRequests",
    ],
    "candidate limits",
  );
  for (const [key, expected] of Object.entries(CANDIDATE_DAEMON_LIMITS)) {
    if (limits.get(key) !== expected) throw new TypeError("invalid candidate limits");
  }
  const activation = captureExactObject(
    profile.get("activation"),
    ["hmacRequired", "windowsAcl", "productionActivationEligible"],
    "candidate activation",
  );
  if (
    activation.get("hmacRequired") !== true ||
    activation.get("windowsAcl") !== "PROVEN" ||
    activation.get("productionActivationEligible") !== true
  ) {
    throw new TypeError("invalid candidate activation");
  }
  return value;
}

function captureClientHello(value, includeMac) {
  const keys = [
    "protocol",
    "rpcSchema",
    "projectId",
    "originThreadHash",
    "originCapabilityHash",
    "clientRelease",
    "runtimeBuildHash",
    "clientNonce",
    "requiredCapabilities",
  ];
  if (includeMac) keys.push("mac");
  const hello = captureExactObject(value, keys, "candidate client hello");
  if (
    hello.get("protocol") !== CANDIDATE_DAEMON_PROTOCOL_VERSION ||
    hello.get("rpcSchema") !== CANDIDATE_DAEMON_RPC_SCHEMA_VERSION ||
    hello.get("clientRelease") !== CANDIDATE_DAEMON_RELEASE ||
    hello.get("runtimeBuildHash") !== CANDIDATE_RUNTIME_BUILD_HASH
  ) {
    throw new TypeError("invalid candidate client hello");
  }
  requireProjectId(hello.get("projectId"));
  requireLowerHex64(hello.get("originThreadHash"), "origin thread hash");
  requireLowerHex64(hello.get("originCapabilityHash"), "origin capability hash");
  requireLowerHex64(hello.get("clientNonce"), "client nonce");
  requireExactStringArray(
    hello.get("requiredCapabilities"),
    CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
    "required capabilities",
  );
  assertCandidateCanonicalJsonByteLimit(
    value,
    CANDIDATE_DAEMON_WIRE_LIMITS.maxHandshakeBytes,
  );
  return hello;
}

function clientHelloWithoutMac(hello) {
  const captured = captureClientHello(hello, true);
  return {
    protocol: captured.get("protocol"),
    rpcSchema: captured.get("rpcSchema"),
    projectId: captured.get("projectId"),
    originThreadHash: captured.get("originThreadHash"),
    originCapabilityHash: captured.get("originCapabilityHash"),
    clientRelease: captured.get("clientRelease"),
    runtimeBuildHash: captured.get("runtimeBuildHash"),
    clientNonce: captured.get("clientNonce"),
    requiredCapabilities: captured.get("requiredCapabilities"),
  };
}

function candidateClientHelloMacTranscript(hello) {
  const captured = captureClientHello(hello, false);
  return [
    CANDIDATE_DAEMON_HANDSHAKE_DOMAIN,
    "CLIENT_HELLO",
    captured.get("protocol"),
    captured.get("rpcSchema"),
    captured.get("projectId"),
    captured.get("originThreadHash"),
    captured.get("originCapabilityHash"),
    captured.get("clientRelease"),
    captured.get("runtimeBuildHash"),
    captured.get("clientNonce"),
    candidateCanonicalSha256(captured.get("requiredCapabilities")),
  ];
}

export function createCandidateClientHello(secret, fields) {
  const captured = captureClientHello(fields, false);
  const hello = {
    protocol: captured.get("protocol"),
    rpcSchema: captured.get("rpcSchema"),
    projectId: captured.get("projectId"),
    originThreadHash: captured.get("originThreadHash"),
    originCapabilityHash: captured.get("originCapabilityHash"),
    clientRelease: captured.get("clientRelease"),
    runtimeBuildHash: captured.get("runtimeBuildHash"),
    clientNonce: captured.get("clientNonce"),
    requiredCapabilities: [...captured.get("requiredCapabilities")],
  };
  return deepFreeze({
    ...hello,
    mac: hmacCandidateTranscript(secret, candidateClientHelloMacTranscript(hello)),
  });
}

export function verifyCandidateClientHello(secret, hello) {
  try {
    const captured = captureClientHello(hello, true);
    const withoutMac = clientHelloWithoutMac(hello);
    const expected = hmacCandidateTranscript(
      secret,
      candidateClientHelloMacTranscript(withoutMac),
    );
    return timingSafeMacMatches(expected, captured.get("mac"));
  } catch {
    return false;
  }
}

function captureServerFields(value) {
  const fields = captureExactObject(
    value,
    [
      "serverNonce",
      "serverInstanceId",
      "serverStartedAtMs",
      "runtimeBuildHash",
      "originId",
    ],
    "candidate server hello fields",
  );
  requireLowerHex64(fields.get("serverNonce"), "server nonce");
  if (!Number.isSafeInteger(fields.get("originId")) || fields.get("originId") < 1) {
    throw new TypeError("invalid origin id");
  }
  if (
    typeof fields.get("serverInstanceId") !== "string" ||
    !/^DI-[a-f0-9]{32}$/.test(fields.get("serverInstanceId"))
  ) {
    throw new TypeError("invalid server instance id");
  }
  if (
    !Number.isSafeInteger(fields.get("serverStartedAtMs")) ||
    fields.get("serverStartedAtMs") < 1
  ) {
    throw new TypeError("invalid server start time");
  }
  if (fields.get("runtimeBuildHash") !== CANDIDATE_RUNTIME_BUILD_HASH) {
    throw new TypeError("invalid runtime build hash");
  }
  return fields;
}

function captureServerHello(clientHello, value, includeMac) {
  const keys = [
    "ok",
    "protocol",
    "rpcSchema",
    "projectId",
    "originThreadHash",
    "originCapabilityHash",
    "originId",
    "clientRelease",
    "serverRelease",
    "storeSchema",
    "clientNonce",
    "serverNonce",
    "serverInstanceId",
    "serverStartedAtMs",
    "runtimeBuildHash",
    "grantedCapabilities",
    "methods",
    "limits",
    "activation",
  ];
  if (includeMac) keys.push("mac");
  const client = captureClientHello(clientHello, true);
  const server = captureExactObject(value, keys, "candidate server hello");
  if (
    server.get("ok") !== true ||
    server.get("protocol") !== CANDIDATE_DAEMON_PROTOCOL_VERSION ||
    server.get("rpcSchema") !== CANDIDATE_DAEMON_RPC_SCHEMA_VERSION ||
    server.get("projectId") !== client.get("projectId") ||
    server.get("originThreadHash") !== client.get("originThreadHash") ||
    server.get("originCapabilityHash") !== client.get("originCapabilityHash") ||
    server.get("clientRelease") !== client.get("clientRelease") ||
    server.get("serverRelease") !== CANDIDATE_DAEMON_RELEASE ||
    server.get("storeSchema") !== CANDIDATE_DAEMON_REQUIRED_STORE_SCHEMA_VERSION ||
    server.get("clientNonce") !== client.get("clientNonce") ||
    server.get("runtimeBuildHash") !== client.get("runtimeBuildHash")
  ) {
    throw new TypeError("invalid candidate server hello");
  }
  if (!Number.isSafeInteger(server.get("originId")) || server.get("originId") < 1) {
    throw new TypeError("invalid origin id");
  }
  requireLowerHex64(server.get("serverNonce"), "server nonce");
  if (
    typeof server.get("serverInstanceId") !== "string" ||
    !/^DI-[a-f0-9]{32}$/.test(server.get("serverInstanceId"))
  ) {
    throw new TypeError("invalid server instance id");
  }
  if (
    !Number.isSafeInteger(server.get("serverStartedAtMs")) ||
    server.get("serverStartedAtMs") < 1
  ) {
    throw new TypeError("invalid server start time");
  }
  requireExactStringArray(
    server.get("grantedCapabilities"),
    CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
    "granted capabilities",
  );
  requireExactStringArray(
    server.get("methods"),
    CANDIDATE_DAEMON_RPC_METHODS,
    "candidate RPC methods",
  );
  validateCandidateCapabilityProfile({
    ...CANDIDATE_DAEMON_PROFILE,
    capabilities: server.get("grantedCapabilities"),
    methods: server.get("methods"),
    limits: server.get("limits"),
    activation: server.get("activation"),
  });
  assertCandidateCanonicalJsonByteLimit(
    value,
    CANDIDATE_DAEMON_WIRE_LIMITS.maxHandshakeBytes,
  );
  return server;
}

function serverHelloWithoutMac(clientHello, serverHello) {
  const captured = captureServerHello(clientHello, serverHello, true);
  return {
    ok: captured.get("ok"),
    protocol: captured.get("protocol"),
    rpcSchema: captured.get("rpcSchema"),
    projectId: captured.get("projectId"),
    originThreadHash: captured.get("originThreadHash"),
    originCapabilityHash: captured.get("originCapabilityHash"),
    originId: captured.get("originId"),
    clientRelease: captured.get("clientRelease"),
    serverRelease: captured.get("serverRelease"),
    storeSchema: captured.get("storeSchema"),
    clientNonce: captured.get("clientNonce"),
    serverNonce: captured.get("serverNonce"),
    serverInstanceId: captured.get("serverInstanceId"),
    serverStartedAtMs: captured.get("serverStartedAtMs"),
    runtimeBuildHash: captured.get("runtimeBuildHash"),
    grantedCapabilities: captured.get("grantedCapabilities"),
    methods: captured.get("methods"),
    limits: captured.get("limits"),
    activation: captured.get("activation"),
  };
}

function candidateServerHelloMacTranscript(clientHello, serverHello) {
  const client = captureClientHello(clientHello, true);
  const server = captureServerHello(clientHello, serverHello, false);
  return [
    CANDIDATE_DAEMON_HANDSHAKE_DOMAIN,
    "SERVER_HELLO",
    server.get("protocol"),
    server.get("rpcSchema"),
    server.get("projectId"),
    server.get("originThreadHash"),
    server.get("originCapabilityHash"),
    server.get("originId"),
    server.get("clientRelease"),
    server.get("serverRelease"),
    server.get("storeSchema"),
    server.get("clientNonce"),
    server.get("serverNonce"),
    server.get("serverInstanceId"),
    server.get("serverStartedAtMs"),
    server.get("runtimeBuildHash"),
    candidateCanonicalSha256(client.get("requiredCapabilities")),
    candidateCanonicalSha256(server.get("grantedCapabilities")),
    candidateCanonicalSha256(server.get("methods")),
    candidateCanonicalSha256(server.get("limits")),
    candidateCanonicalSha256(server.get("activation")),
  ];
}

export function createCandidateServerHello(secret, clientHello, fields) {
  const capturedClient = captureClientHello(clientHello, true);
  const clientSnapshot = deepFreeze({
    protocol: capturedClient.get("protocol"),
    rpcSchema: capturedClient.get("rpcSchema"),
    projectId: capturedClient.get("projectId"),
    originThreadHash: capturedClient.get("originThreadHash"),
    originCapabilityHash: capturedClient.get("originCapabilityHash"),
    clientRelease: capturedClient.get("clientRelease"),
    runtimeBuildHash: capturedClient.get("runtimeBuildHash"),
    clientNonce: capturedClient.get("clientNonce"),
    requiredCapabilities: captureDenseArray(
      capturedClient.get("requiredCapabilities"),
      "required capabilities",
    ),
    mac: capturedClient.get("mac"),
  });
  if (!verifyCandidateClientHello(secret, clientSnapshot)) {
    throw new TypeError("invalid authenticated candidate client hello");
  }
  const serverFields = captureServerFields(fields);
  const serverHello = {
    ok: true,
    protocol: CANDIDATE_DAEMON_PROFILE.protocol,
    rpcSchema: CANDIDATE_DAEMON_PROFILE.rpcSchema,
    projectId: clientSnapshot.projectId,
    originThreadHash: clientSnapshot.originThreadHash,
    originCapabilityHash: clientSnapshot.originCapabilityHash,
    originId: serverFields.get("originId"),
    clientRelease: clientSnapshot.clientRelease,
    serverRelease: CANDIDATE_DAEMON_PROFILE.serverRelease,
    storeSchema: CANDIDATE_DAEMON_PROFILE.storeSchema,
    clientNonce: clientSnapshot.clientNonce,
    serverNonce: serverFields.get("serverNonce"),
    serverInstanceId: serverFields.get("serverInstanceId"),
    serverStartedAtMs: serverFields.get("serverStartedAtMs"),
    runtimeBuildHash: serverFields.get("runtimeBuildHash"),
    grantedCapabilities: CANDIDATE_DAEMON_PROFILE.capabilities,
    methods: CANDIDATE_DAEMON_PROFILE.methods,
    limits: CANDIDATE_DAEMON_PROFILE.limits,
    activation: CANDIDATE_DAEMON_PROFILE.activation,
  };
  return deepFreeze({
    ...serverHello,
    mac: hmacCandidateTranscript(
      secret,
      candidateServerHelloMacTranscript(clientSnapshot, serverHello),
    ),
  });
}

export function verifyCandidateServerHello(secret, clientHello, serverHello) {
  try {
    if (!verifyCandidateClientHello(secret, clientHello)) return false;
    const captured = captureServerHello(clientHello, serverHello, true);
    const withoutMac = serverHelloWithoutMac(clientHello, serverHello);
    const expected = hmacCandidateTranscript(
      secret,
      candidateServerHelloMacTranscript(clientHello, withoutMac),
    );
    return timingSafeMacMatches(expected, captured.get("mac"));
  } catch {
    return false;
  }
}

export function candidateHandshakeTranscriptHash(clientHello, serverHello) {
  return candidateCanonicalSha256([
    clientHelloWithoutMac(clientHello),
    serverHelloWithoutMac(clientHello, serverHello),
  ]);
}

function finishMacTranscript(phase, transcriptHash) {
  requireLowerHex64(transcriptHash, "handshake transcript hash");
  return [
    CANDIDATE_DAEMON_HANDSHAKE_DOMAIN,
    phase,
    CANDIDATE_DAEMON_PROTOCOL_VERSION,
    transcriptHash,
  ];
}

export function createCandidateClientFinish(secret, transcriptHash) {
  return deepFreeze({
    transcriptHash: requireLowerHex64(transcriptHash, "handshake transcript hash"),
    clientFinishMac: hmacCandidateTranscript(
      secret,
      finishMacTranscript("CLIENT_FINISH", transcriptHash),
    ),
  });
}

export function verifyCandidateClientFinish(secret, expectedTranscriptHash, value) {
  try {
    const expectedHash = requireLowerHex64(
      expectedTranscriptHash,
      "expected handshake transcript hash",
    );
    const captured = captureExactObject(
      value,
      ["transcriptHash", "clientFinishMac"],
      "candidate client finish",
    );
    const transcriptHash = requireLowerHex64(
      captured.get("transcriptHash"),
      "handshake transcript hash",
    );
    const expected = hmacCandidateTranscript(
      secret,
      finishMacTranscript("CLIENT_FINISH", expectedHash),
    );
    const macMatches = timingSafeMacMatches(expected, captured.get("clientFinishMac"));
    return transcriptHash === expectedHash && macMatches;
  } catch {
    return false;
  }
}

export function createCandidateServerFinish(secret, transcriptHash) {
  return deepFreeze({
    ok: true,
    authenticated: true,
    transcriptHash: requireLowerHex64(transcriptHash, "handshake transcript hash"),
    serverFinishMac: hmacCandidateTranscript(
      secret,
      finishMacTranscript("SERVER_FINISH", transcriptHash),
    ),
  });
}

export function verifyCandidateServerFinish(secret, expectedTranscriptHash, value) {
  try {
    const expectedHash = requireLowerHex64(
      expectedTranscriptHash,
      "expected handshake transcript hash",
    );
    const captured = captureExactObject(
      value,
      ["ok", "authenticated", "transcriptHash", "serverFinishMac"],
      "candidate server finish",
    );
    if (captured.get("ok") !== true || captured.get("authenticated") !== true) return false;
    const transcriptHash = requireLowerHex64(
      captured.get("transcriptHash"),
      "handshake transcript hash",
    );
    const expected = hmacCandidateTranscript(
      secret,
      finishMacTranscript("SERVER_FINISH", expectedHash),
    );
    const macMatches = timingSafeMacMatches(expected, captured.get("serverFinishMac"));
    return transcriptHash === expectedHash && macMatches;
  } catch {
    return false;
  }
}

function requireRequestId(value) {
  if (typeof value !== "string" || !/^[\x21-\x7e]+$/.test(value)) {
    throw new TypeError("invalid candidate request id");
  }
  assertCandidateUtf8ByteLimit(value, CANDIDATE_DAEMON_WIRE_LIMITS.maxRequestIdBytes);
  return value;
}

function requireMethod(value) {
  if (!CANDIDATE_DAEMON_RPC_METHODS.includes(value)) {
    throw new TypeError("unknown candidate RPC method");
  }
  assertCandidateUtf8ByteLimit(value, CANDIDATE_DAEMON_WIRE_LIMITS.maxMethodBytes);
  return value;
}

function requireTrustedLegacyValidators(value) {
  const validators = captureExactObject(
    value,
    ["workerSubmit", "batchSubmit", "headPlan"],
    "candidate Legacy validator registry",
  );
  for (const validator of validators.values()) {
    if (typeof validator !== "function") {
      throw new TypeError("invalid candidate Legacy validator registry");
    }
  }
  return validators;
}

function requireValidatedLegacyInput(value, label, validator, ...validatorArguments) {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new TypeError(`invalid ${label}`);
  }
  const before = canonicalCandidateDaemonJson(value);
  let accepted;
  try {
    // Task8B Step10 must bind a wrapper around the existing v0.9.1 strict Zod
    // parser that proves canonical equality with the original before returning true.
    accepted = validator(value, ...validatorArguments);
  } catch {
    throw new TypeError(`invalid ${label}`);
  }
  if (accepted !== true || canonicalCandidateDaemonJson(value) !== before) {
    throw new TypeError(`invalid ${label}`);
  }
  return value;
}

function requirePublicId(value, pattern, label) {
  if (typeof value !== "string" || !pattern.test(value)) {
    throw new TypeError(`invalid public ${label}`);
  }
  return value;
}

const DS_ID = /^DS-[a-f0-9]{32}$/;
const DLB_ID = /^DLB-[a-f0-9]{32}$/;
const SRP_ID = /^SRP-[a-f0-9]{32}$/;
const SH_ID = /^SH-[a-f0-9]{32}$/;

function validateEmptyPayload(value, label) {
  captureExactObject(value, [], label);
}

function validateRpcPayload(method, payload, legacyValidators) {
  switch (method) {
    case "health":
    case "metrics":
    case "batch.metrics":
    case "head.metrics":
      validateEmptyPayload(payload, `${method} payload`);
      break;
    case "worker.submit": {
      const validators = requireTrustedLegacyValidators(legacyValidators);
      const fields = captureExactObject(
        payload,
        ["input", "mode"],
        "worker.submit payload",
      );
      const mode = fields.get("mode");
      if (!["READ_ONLY", "WRITE"].includes(mode)) {
        throw new TypeError("invalid worker mode");
      }
      requireValidatedLegacyInput(
        fields.get("input"),
        "LegacyWorkerInputV091",
        validators.get("workerSubmit"),
        mode,
      );
      break;
    }
    case "job.status":
    case "job.cancel": {
      const fields = captureExactObject(payload, ["jobId"], `${method} payload`);
      requirePublicId(fields.get("jobId"), DS_ID, "worker job id");
      break;
    }
    case "batch.submit": {
      const validators = requireTrustedLegacyValidators(legacyValidators);
      const fields = captureExactObject(payload, ["input"], "batch.submit payload");
      requireValidatedLegacyInput(
        fields.get("input"),
        "LegacyBatchInputV091",
        validators.get("batchSubmit"),
      );
      break;
    }
    case "batch.status": {
      const fields = captureExactObject(payload, ["batchId"], "batch.status payload");
      requirePublicId(fields.get("batchId"), DLB_ID, "batch id");
      break;
    }
    case "head.plan": {
      const validators = requireTrustedLegacyValidators(legacyValidators);
      const fields = captureExactObject(payload, ["input"], "head.plan payload");
      requireValidatedLegacyInput(
        fields.get("input"),
        "LegacySolRouteInputV091",
        validators.get("headPlan"),
      );
      break;
    }
    case "head.submit": {
      const fields = captureExactObject(payload, ["planId"], "head.submit payload");
      requirePublicId(fields.get("planId"), SRP_ID, "Sol route plan id");
      break;
    }
    case "head.status":
    case "head.cancel": {
      const fields = captureExactObject(payload, ["jobId"], `${method} payload`);
      requirePublicId(fields.get("jobId"), SH_ID, "Sol head job id");
      break;
    }
    default:
      throw new TypeError("unknown candidate RPC method");
  }
}

export function validateCandidateRpcRequestEnvelope(value, legacyValidators = undefined) {
  const envelope = captureExactObject(
    value,
    ["seq", "requestId", "type", "payload"],
    "candidate RPC request envelope",
  );
  if (!Number.isSafeInteger(envelope.get("seq")) || envelope.get("seq") < 0) {
    throw new TypeError("invalid candidate RPC sequence");
  }
  requireRequestId(envelope.get("requestId"));
  const method = requireMethod(envelope.get("type"));
  validateRpcPayload(method, envelope.get("payload"), legacyValidators);
  assertCandidateCanonicalJsonByteLimit(
    value,
    CANDIDATE_DAEMON_WIRE_LIMITS.maxFrameBytes,
  );
  return value;
}

function validatePublicResultIdentity(method, result, responseContext) {
  const requireSchemaVersion = (fields) => {
    if (fields.get("schema_version") !== 1) {
      throw new TypeError("invalid public result schema version");
    }
  };
  const requireExactMember = (value, allowed, label) => {
    if (!allowed.includes(value)) {
      throw new TypeError(`invalid public ${label}`);
    }
  };
  const requireBoolean = (value, label) => {
    if (typeof value !== "boolean") throw new TypeError(`invalid public ${label}`);
  };
  const requirePublicText = (value, label, maximumBytes) => {
    if (
      typeof value !== "string" ||
      value.trim() === "" ||
      candidateUtf8Bytes(value) > maximumBytes ||
      containsUnsafePublicText(value)
    ) {
      throw new TypeError(`invalid public ${label}`);
    }
  };
  const requirePublicTextArray = (value, label) => {
    const entries = captureDenseArray(value, label);
    if (entries.length > 32) throw new TypeError(`invalid public ${label}`);
    for (const entry of entries) requirePublicText(entry, `${label} entry`, 2048);
  };
  const validatePublicResultPacket = (value) => {
    const fields = captureExactObject(
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
      "public result packet",
    );
    requireSchemaVersion(fields);
    if (fields.get("result_protocol") !== 3) {
      throw new TypeError("invalid public result protocol");
    }
    requireExactMember(
      fields.get("status"),
      ["PASS", "CACHED", "FAIL", "BLOCKED"],
      "result status",
    );
    requireExactMember(
      fields.get("execution_status"),
      CANDIDATE_PUBLIC_EXECUTION_STATUSES,
      "result execution status",
    );
    requireExactMember(
      fields.get("evidence_verdict"),
      CANDIDATE_PUBLIC_EVIDENCE_VERDICTS,
      "result evidence verdict",
    );
    requireBoolean(fields.get("cache_hit"), "result cache flag");
    const packetStatus = fields.get("status");
    const packetExecutionStatus = fields.get("execution_status");
    const packetEvidenceVerdict = fields.get("evidence_verdict");
    const packetCacheHit = fields.get("cache_hit");
    const packetUnresolved = packetEvidenceVerdict === "UNRESOLVED";
    const packetCoherent =
      (packetStatus === "CACHED" &&
        packetExecutionStatus === "ACCEPTED" &&
        !packetUnresolved &&
        packetCacheHit === true) ||
      (packetStatus === "PASS" &&
        packetExecutionStatus === "ACCEPTED" &&
        !packetUnresolved &&
        packetCacheHit === false) ||
      (packetStatus === "FAIL" &&
        ["INCOMPLETE", "PROVIDER_ERROR", "CONTRACT_ERROR"].includes(
          packetExecutionStatus,
        ) &&
        packetUnresolved &&
        packetCacheHit === false) ||
      (packetStatus === "BLOCKED" &&
        ["BLOCKED", "CANCELLED"].includes(packetExecutionStatus) &&
        packetUnresolved &&
        packetCacheHit === false);
    if (!packetCoherent) {
      throw new TypeError("incoherent public result packet");
    }
    requirePublicText(fields.get("summary"), "result summary", 4096);
    requirePublicTextArray(fields.get("positive_findings"), "positive findings");
    requirePublicTextArray(fields.get("negative_findings"), "negative findings");
    requirePublicTextArray(fields.get("residual_risks"), "residual risks");
    requirePublicText(
      fields.get("recommended_next_action"),
      "recommended next action",
      4096,
    );
    requireBoolean(
      fields.get("scientific_uncertainty"),
      "scientific uncertainty",
    );
    requireBoolean(
      fields.get("architecture_uncertainty"),
      "architecture uncertainty",
    );
    requireBoolean(fields.get("scope_deviation"), "scope deviation");
    assertCandidateCanonicalJsonByteLimit(
      value,
      CANDIDATE_DAEMON_WIRE_LIMITS.maxResultPacketBytes,
    );
    return fields;
  };
  const captureJobSubmission = (expectedMethod, expectedIdPattern, extraKeys = []) => {
    const fields = captureExactObject(
      result,
      [
        "schema_version",
        "job_id",
        "status",
        "execution_status",
        "evidence_verdict",
        "cache_hit",
        "coalesced",
        ...extraKeys,
      ],
      `${expectedMethod} result`,
    );
    requireSchemaVersion(fields);
    requirePublicId(fields.get("job_id"), expectedIdPattern, `${expectedMethod} job id`);
    requireExactMember(fields.get("status"), CANDIDATE_PUBLIC_STATUSES, "job status");
    requireExactMember(
      fields.get("execution_status"),
      CANDIDATE_PUBLIC_EXECUTION_STATUSES,
      "execution status",
    );
    requireExactMember(
      fields.get("evidence_verdict"),
      CANDIDATE_PUBLIC_EVIDENCE_VERDICTS,
      "evidence verdict",
    );
    requireBoolean(fields.get("cache_hit"), "cache flag");
    requireBoolean(fields.get("coalesced"), "coalesced flag");
    const status = fields.get("status");
    const executionStatus = fields.get("execution_status");
    const evidenceVerdict = fields.get("evidence_verdict");
    const cacheHit = fields.get("cache_hit");
    const unresolved = evidenceVerdict === "UNRESOLVED";
    const coherent =
      (["QUEUED", "RUNNING"].includes(status) &&
        executionStatus === "INCOMPLETE" &&
        unresolved &&
        cacheHit === false) ||
      (status === "CACHED" &&
        executionStatus === "ACCEPTED" &&
        !unresolved &&
        cacheHit === true) ||
      (status === "PASS" &&
        executionStatus === "ACCEPTED" &&
        !unresolved &&
        cacheHit === false) ||
      (status === "FAIL" &&
        ["INCOMPLETE", "PROVIDER_ERROR", "CONTRACT_ERROR"].includes(executionStatus) &&
        unresolved &&
        cacheHit === false) ||
      (status === "BLOCKED" &&
        ["BLOCKED", "CANCELLED"].includes(executionStatus) &&
        unresolved &&
        cacheHit === false);
    if (!coherent) throw new TypeError("incoherent public job submission");
    return fields;
  };
  const requirePublicCount = (value, label) => {
    if (
      !Number.isSafeInteger(value) ||
      Object.is(value, -0) ||
      value < 0
    ) {
      throw new TypeError(`invalid public ${label}`);
    }
    return value;
  };
  const validateMetricsCounts = ({
    fields,
    totalKey,
    statusKeys,
    cacheHitsKey = undefined,
  }) => {
    for (const key of [
      totalKey,
      ...statusKeys,
      ...(cacheHitsKey === undefined ? [] : [cacheHitsKey]),
      "provider_transmissions",
      "spent_nano_usd",
      "reserved_nano_usd",
      "unknown_transmissions",
    ]) {
      requirePublicCount(fields.get(key), key);
    }
    if (
      fields.get(totalKey) !==
        statusKeys.reduce((total, key) => total + fields.get(key), 0) ||
      fields.get("unknown_transmissions") >
        fields.get("provider_transmissions") ||
      (cacheHitsKey !== undefined &&
        fields.get(cacheHitsKey) > fields.get("terminal_jobs"))
    ) {
      throw new TypeError("incoherent public metrics");
    }
  };
  const validatePublicStatusIdentity = ({
    status,
    executionStatus,
    evidenceVerdict,
    cacheHit,
    resultPacket,
    allowMissingFailedPacket = false,
  }) => {
    requireExactMember(status, CANDIDATE_PUBLIC_STATUSES, "job status");
    requireExactMember(
      executionStatus,
      CANDIDATE_PUBLIC_EXECUTION_STATUSES,
      "execution status",
    );
    requireExactMember(
      evidenceVerdict,
      CANDIDATE_PUBLIC_EVIDENCE_VERDICTS,
      "evidence verdict",
    );
    requireBoolean(cacheHit, "cache flag");
    const terminal = ["PASS", "CACHED", "FAIL", "BLOCKED"].includes(status);
    const unresolved = evidenceVerdict === "UNRESOLVED";
    const coherent =
      (["QUEUED", "RUNNING"].includes(status) &&
        executionStatus === "INCOMPLETE" &&
        unresolved &&
        cacheHit === false &&
        resultPacket === null) ||
      (status === "CACHED" &&
        executionStatus === "ACCEPTED" &&
        !unresolved &&
        cacheHit === true &&
        resultPacket !== null) ||
      (status === "PASS" &&
        executionStatus === "ACCEPTED" &&
        !unresolved &&
        cacheHit === false &&
        resultPacket !== null) ||
      (["FAIL", "BLOCKED"].includes(status) &&
        unresolved &&
        cacheHit === false &&
        (allowMissingFailedPacket || resultPacket !== null));
    if (!coherent) throw new TypeError("incoherent public status");
    if (resultPacket !== null) {
      const packet = validatePublicResultPacket(resultPacket);
      for (const [outerValue, packetKey] of [
        [status, "status"],
        [executionStatus, "execution_status"],
        [evidenceVerdict, "evidence_verdict"],
        [cacheHit, "cache_hit"],
      ]) {
        if (outerValue !== packet.get(packetKey)) {
          throw new TypeError("public result packet identity mismatch");
        }
      }
    }
    return terminal;
  };
  switch (method) {
    case "metrics": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "total_jobs",
          "queued_jobs",
          "running_jobs",
          "validating_jobs",
          "terminal_jobs",
          "provider_transmissions",
          "input_tokens",
          "cached_input_tokens",
          "output_tokens",
          "total_tokens",
          "spent_nano_usd",
          "reserved_nano_usd",
          "unknown_transmissions",
        ],
        "metrics result",
      );
      requireSchemaVersion(fields);
      for (const key of [
        "total_jobs",
        "queued_jobs",
        "running_jobs",
        "validating_jobs",
        "terminal_jobs",
        "provider_transmissions",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
        "spent_nano_usd",
        "reserved_nano_usd",
        "unknown_transmissions",
      ]) {
        const amount = fields.get(key);
        if (
          !Number.isSafeInteger(amount) ||
          Object.is(amount, -0) ||
          amount < 0
        ) {
          throw new TypeError("invalid public metric");
        }
      }
      if (
        fields.get("total_jobs") !==
          fields.get("queued_jobs") +
            fields.get("running_jobs") +
            fields.get("validating_jobs") +
            fields.get("terminal_jobs") ||
        fields.get("unknown_transmissions") >
          fields.get("provider_transmissions") ||
        fields.get("cached_input_tokens") > fields.get("input_tokens") ||
        fields.get("total_tokens") !==
          fields.get("input_tokens") + fields.get("output_tokens")
      ) {
        throw new TypeError("incoherent public metrics");
      }
      break;
    }
    case "job.status": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "job_id",
          "status",
          "execution_status",
          "evidence_verdict",
          "cache_hit",
          "subscriber_state",
          "result_packet",
        ],
        "job.status result",
      );
      requireSchemaVersion(fields);
      requirePublicId(fields.get("job_id"), DS_ID, "worker job id");
      requireExactMember(fields.get("status"), CANDIDATE_PUBLIC_STATUSES, "job status");
      requireExactMember(
        fields.get("execution_status"),
        CANDIDATE_PUBLIC_EXECUTION_STATUSES,
        "execution status",
      );
      requireExactMember(
        fields.get("evidence_verdict"),
        CANDIDATE_PUBLIC_EVIDENCE_VERDICTS,
        "evidence verdict",
      );
      requireBoolean(fields.get("cache_hit"), "cache flag");
      requireExactMember(
        fields.get("subscriber_state"),
        ["ATTACHED", "DETACHED", "TERMINAL"],
        "subscriber state",
      );
      const status = fields.get("status");
      const executionStatus = fields.get("execution_status");
      const evidenceVerdict = fields.get("evidence_verdict");
      const cacheHit = fields.get("cache_hit");
      const resultPacket = fields.get("result_packet");
      const terminal = ["PASS", "CACHED", "FAIL", "BLOCKED"].includes(status);
      const unresolved = evidenceVerdict === "UNRESOLVED";
      const coherent =
        (["QUEUED", "RUNNING"].includes(status) &&
          executionStatus === "INCOMPLETE" &&
          unresolved &&
          cacheHit === false &&
          fields.get("subscriber_state") !== "TERMINAL" &&
          resultPacket === null) ||
        (terminal &&
          fields.get("subscriber_state") === "TERMINAL" &&
          resultPacket !== null);
      if (!coherent) throw new TypeError("incoherent public job status");
      if (resultPacket !== null) {
        const packet = validatePublicResultPacket(resultPacket);
        for (const [outerKey, packetKey] of [
          ["status", "status"],
          ["execution_status", "execution_status"],
          ["evidence_verdict", "evidence_verdict"],
          ["cache_hit", "cache_hit"],
        ]) {
          if (fields.get(outerKey) !== packet.get(packetKey)) {
            throw new TypeError("public result packet identity mismatch");
          }
        }
      }
      break;
    }
    case "worker.submit": {
      captureJobSubmission(method, DS_ID);
      break;
    }
    case "batch.submit": {
      const fields = captureExactObject(
        result,
        ["schema_version", "batch_id", "status", "node_count", "concurrency"],
        "batch.submit result",
      );
      requireSchemaVersion(fields);
      requirePublicId(fields.get("batch_id"), DLB_ID, "batch id");
      if (fields.get("status") !== "QUEUED") {
        throw new TypeError("invalid batch submission status");
      }
      if (
        !Number.isSafeInteger(fields.get("node_count")) ||
        fields.get("node_count") < 1 ||
        fields.get("node_count") > CANDIDATE_DAEMON_LIMITS.maxBatchNodes ||
        !Number.isSafeInteger(fields.get("concurrency")) ||
        fields.get("concurrency") < 1 ||
        fields.get("concurrency") > CANDIDATE_DAEMON_LIMITS.maxBatchNodes
      ) {
        throw new TypeError("invalid batch submission result");
      }
      break;
    }
    case "batch.status": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "batch_id",
          "status",
          "node_count",
          "concurrency",
          "subscriber_state",
          "nodes",
        ],
        "batch.status result",
      );
      requireSchemaVersion(fields);
      requirePublicId(fields.get("batch_id"), DLB_ID, "batch id");
      const nodeCount = requirePublicCount(fields.get("node_count"), "batch node count");
      const concurrency = requirePublicCount(
        fields.get("concurrency"),
        "batch concurrency",
      );
      if (
        nodeCount < 1 ||
        nodeCount > CANDIDATE_DAEMON_LIMITS.maxBatchNodes ||
        concurrency < 1 ||
        concurrency > nodeCount
      ) {
        throw new TypeError("invalid public batch bounds");
      }
      requireExactMember(
        fields.get("subscriber_state"),
        ["ATTACHED", "DETACHED", "TERMINAL"],
        "batch subscriber state",
      );
      const nodes = captureDenseArray(fields.get("nodes"), "batch nodes");
      if (nodes.length !== nodeCount) {
        throw new TypeError("incoherent public batch node count");
      }
      const nodeIds = new Set();
      const statuses = [];
      for (const node of nodes) {
        const nodeFields = captureExactObject(
          node,
          [
            "node_id",
            "status",
            "execution_status",
            "evidence_verdict",
            "cache_hit",
            "job_id",
            "result_packet",
          ],
          "batch node",
        );
        const nodeId = nodeFields.get("node_id");
        if (
          typeof nodeId !== "string" ||
          !/^[A-Za-z0-9._:-]{1,128}$/.test(nodeId) ||
          [".", ".."].includes(nodeId) ||
          nodeIds.has(nodeId)
        ) {
          throw new TypeError("invalid public batch node id");
        }
        nodeIds.add(nodeId);
        const jobId = nodeFields.get("job_id");
        if (jobId !== null) requirePublicId(jobId, DS_ID, "batch worker job id");
        const nodeStatus = nodeFields.get("status");
        const terminal = validatePublicStatusIdentity({
          status: nodeStatus,
          executionStatus: nodeFields.get("execution_status"),
          evidenceVerdict: nodeFields.get("evidence_verdict"),
          cacheHit: nodeFields.get("cache_hit"),
          resultPacket: nodeFields.get("result_packet"),
          allowMissingFailedPacket: true,
        });
        if (
          (nodeStatus === "RUNNING" && jobId === null) ||
          (["PASS", "CACHED"].includes(nodeStatus) && jobId === null) ||
          (!terminal && nodeFields.get("result_packet") !== null)
        ) {
          throw new TypeError("incoherent public batch node");
        }
        statuses.push(nodeStatus);
      }
      const allTerminal = statuses.every((status) =>
        ["PASS", "CACHED", "FAIL", "BLOCKED"].includes(status)
      );
      let derivedStatus;
      if (allTerminal) {
        derivedStatus = statuses.every((status) => status === "CACHED")
          ? "CACHED"
          : statuses.every((status) => ["PASS", "CACHED"].includes(status))
            ? "PASS"
            : statuses.includes("BLOCKED")
              ? "BLOCKED"
              : "FAIL";
      } else {
        derivedStatus =
          statuses.some((status) => status !== "QUEUED")
            ? "RUNNING"
            : "QUEUED";
      }
      if (
        fields.get("status") !== derivedStatus ||
        (allTerminal && fields.get("subscriber_state") !== "TERMINAL") ||
        (!allTerminal && fields.get("subscriber_state") === "TERMINAL")
      ) {
        throw new TypeError("incoherent public batch status");
      }
      break;
    }
    case "batch.metrics": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "total_batches",
          "queued_batches",
          "running_batches",
          "terminal_batches",
          "total_nodes",
          "waiting_nodes",
          "queued_nodes",
          "running_nodes",
          "terminal_nodes",
          "provider_transmissions",
          "spent_nano_usd",
          "reserved_nano_usd",
          "unknown_transmissions",
        ],
        "batch.metrics result",
      );
      requireSchemaVersion(fields);
      validateMetricsCounts({
        fields,
        totalKey: "total_batches",
        statusKeys: ["queued_batches", "running_batches", "terminal_batches"],
      });
      for (const key of [
        "total_nodes",
        "waiting_nodes",
        "queued_nodes",
        "running_nodes",
        "terminal_nodes",
      ]) {
        requirePublicCount(fields.get(key), key);
      }
      if (
        fields.get("total_nodes") !==
        fields.get("waiting_nodes") +
          fields.get("queued_nodes") +
          fields.get("running_nodes") +
          fields.get("terminal_nodes")
      ) {
        throw new TypeError("incoherent public batch metrics");
      }
      break;
    }
    case "head.plan": {
      const fields = captureExactObject(
        result,
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
        ],
        "head.plan result",
      );
      requireSchemaVersion(fields);
      requirePublicId(fields.get("plan_id"), SRP_ID, "Sol route plan id");
      const decision = fields.get("decision");
      const selectedEffort = fields.get("selected_effort");
      const maxEligible = fields.get("max_eligible");
      requireBoolean(maxEligible, "Max eligibility");
      if (!CANDIDATE_HEAD_DECISIONS.includes(decision)) {
        throw new TypeError("invalid Sol route decision");
      }
      if (
        (decision === "DELEGATE_DEEPLUNA" &&
          (selectedEffort !== null || maxEligible !== false)) ||
        (decision !== "DELEGATE_DEEPLUNA" &&
          (!CANDIDATE_SOL_EFFORTS.includes(selectedEffort) ||
            (selectedEffort === "max") !== maxEligible))
      ) {
        throw new TypeError("invalid Sol route decision");
      }
      const reasons = captureDenseArray(fields.get("reasons"), "Sol route reasons");
      if (
        reasons.length < 1 ||
        reasons.length > 32 ||
        new Set(reasons).size !== reasons.length ||
        reasons.some(
          (reason) =>
            typeof reason !== "string" ||
            !/^[a-z][a-z0-9-]{0,63}$/.test(reason) ||
            candidateUtf8Bytes(reason) > 64 ||
            !CANDIDATE_HEAD_REASON_CODES.includes(reason)
        )
      ) {
        throw new TypeError("invalid Sol route reasons");
      }
      const reasonSet = new Set(reasons);
      const hasMaxReason = reasonSet.has("max-one-shot-eligible");
      const hasActiveReason = reasonSet.has("active-effort-matches");
      const hasAuthorityReason = reasonSet.has("authority-domain");
      const hasOverheadReason = reasonSet.has("delegation-overhead-dominates");
      const hasDeterministicReason = reasonSet.has(
        "deterministic-deepluna-eligible",
      );
      const hasReasoningScore = reasonSet.has("reasoning-score");
      const coherentReasons =
        hasMaxReason === maxEligible &&
        (!maxEligible || hasAuthorityReason) &&
        (!hasAuthorityReason ||
          selectedEffort === "xhigh" ||
          selectedEffort === "max") &&
        ((decision === "DELEGATE_DEEPLUNA" &&
          reasons.length === 1 &&
          hasDeterministicReason) ||
          (decision === "HANDLE_CURRENT" &&
            hasReasoningScore &&
            hasActiveReason !== hasOverheadReason &&
            (selectedEffort !== "max" || hasActiveReason) &&
            !hasDeterministicReason) ||
          (decision === "START_SOL_HEAD" &&
            hasReasoningScore &&
            !hasActiveReason &&
            !hasOverheadReason &&
            !hasDeterministicReason));
      if (!coherentReasons) {
        throw new TypeError("incomplete Sol route reasons");
      }
      canonicalCandidateDaemonJson(fields.get("reasons"));
      requireLowerHex64(fields.get("attempt_fingerprint"), "attempt fingerprint");
      requireLowerHex64(fields.get("input_fingerprint"), "input fingerprint");
      requireBoolean(fields.get("cache_eligible"), "cache eligibility");
      break;
    }
    case "head.submit": {
      const fields = captureJobSubmission(
        method,
        SH_ID,
        ["plan_id", "requested_effort"],
      );
      requirePublicId(fields.get("plan_id"), SRP_ID, "Sol route plan id");
      if (!CANDIDATE_SOL_EFFORTS.includes(fields.get("requested_effort"))) {
        throw new TypeError("invalid requested effort");
      }
      break;
    }
    case "head.status": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "job_id",
          "plan_id",
          "status",
          "execution_status",
          "evidence_verdict",
          "cache_hit",
          "requested_effort",
          "subscriber_state",
          "result_packet",
        ],
        "head.status result",
      );
      requireSchemaVersion(fields);
      requirePublicId(fields.get("job_id"), SH_ID, "Sol head job id");
      requirePublicId(fields.get("plan_id"), SRP_ID, "Sol route plan id");
      requireExactMember(
        fields.get("requested_effort"),
        CANDIDATE_SOL_EFFORTS,
        "requested effort",
      );
      requireExactMember(
        fields.get("subscriber_state"),
        ["ATTACHED", "DETACHED", "TERMINAL"],
        "head subscriber state",
      );
      const terminal = validatePublicStatusIdentity({
        status: fields.get("status"),
        executionStatus: fields.get("execution_status"),
        evidenceVerdict: fields.get("evidence_verdict"),
        cacheHit: fields.get("cache_hit"),
        resultPacket: fields.get("result_packet"),
      });
      if (
        (terminal && fields.get("subscriber_state") !== "TERMINAL") ||
        (!terminal && fields.get("subscriber_state") === "TERMINAL")
      ) {
        throw new TypeError("incoherent public head status");
      }
      break;
    }
    case "head.cancel": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "job_id",
          "detached",
          "remaining_subscribers",
          "producer_cancelled",
          "subscriber_state",
          "status",
          "execution_status",
        ],
        "head.cancel result",
      );
      requireSchemaVersion(fields);
      requirePublicId(fields.get("job_id"), SH_ID, "Sol head job id");
      requireBoolean(fields.get("detached"), "detach flag");
      requireBoolean(fields.get("producer_cancelled"), "producer cancellation flag");
      const remaining = requirePublicCount(
        fields.get("remaining_subscribers"),
        "remaining subscriber count",
      );
      const producerCancelled = fields.get("producer_cancelled");
      const detachedOnly =
        producerCancelled === false &&
        fields.get("subscriber_state") === "DETACHED" &&
        ["QUEUED", "RUNNING"].includes(fields.get("status")) &&
        fields.get("execution_status") === "INCOMPLETE";
      const producerStopped =
        producerCancelled === true &&
        remaining === 0 &&
        fields.get("subscriber_state") === "TERMINAL" &&
        fields.get("status") === "BLOCKED" &&
        fields.get("execution_status") === "CANCELLED";
      if (!detachedOnly && !producerStopped) {
        throw new TypeError("incoherent public head cancellation");
      }
      break;
    }
    case "head.metrics": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "total_jobs",
          "queued_jobs",
          "running_jobs",
          "terminal_jobs",
          "cache_hits",
          "provider_transmissions",
          "spent_nano_usd",
          "reserved_nano_usd",
          "unknown_transmissions",
        ],
        "head.metrics result",
      );
      requireSchemaVersion(fields);
      validateMetricsCounts({
        fields,
        totalKey: "total_jobs",
        statusKeys: ["queued_jobs", "running_jobs", "terminal_jobs"],
        cacheHitsKey: "cache_hits",
      });
      break;
    }
    case "job.cancel": {
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "job_id",
          "detached",
          "remaining_subscribers",
          "producer_cancelled",
          "subscriber_state",
          "status",
          "execution_status",
        ],
        "job.cancel result",
      );
      requireSchemaVersion(fields);
      requirePublicId(fields.get("job_id"), DS_ID, "worker job id");
      requireBoolean(fields.get("detached"), "detach flag");
      requireBoolean(fields.get("producer_cancelled"), "producer cancellation flag");
      const remaining = requirePublicCount(
        fields.get("remaining_subscribers"),
        "remaining subscriber count",
      );
      const producerCancelled = fields.get("producer_cancelled");
      const detachedOnly =
        producerCancelled === false &&
        fields.get("subscriber_state") === "DETACHED" &&
        ["QUEUED", "RUNNING"].includes(fields.get("status")) &&
        fields.get("execution_status") === "INCOMPLETE";
      const producerStopped =
        producerCancelled === true &&
        remaining === 0 &&
        fields.get("subscriber_state") === "TERMINAL" &&
        fields.get("status") === "BLOCKED" &&
        fields.get("execution_status") === "CANCELLED";
      if (!detachedOnly && !producerStopped) {
        throw new TypeError("invalid cancellation receipt");
      }
      break;
    }
    case "health": {
      const context = captureExactObject(
        responseContext,
        [
          "projectId",
          "originId",
          "profile",
          "runtimeBuildHash",
          "serverInstanceId",
          "serverStartedAtMs",
        ],
        "trusted health response context",
      );
      requireProjectId(context.get("projectId"));
      if (!Number.isSafeInteger(context.get("originId")) || context.get("originId") < 1) {
        throw new TypeError("invalid trusted health origin id");
      }
      validateCandidateCapabilityProfile(context.get("profile"));
      const fields = captureExactObject(
        result,
        [
          "schema_version",
          "readiness",
          "reason_codes",
          "runtime_mode",
          "server_release",
          "runtime_build_hash",
          "process_boot_id",
          "process_started_at_ms",
          "protocol_version",
          "rpc_schema_version",
          "store_schema_version",
          "project_id",
          "origin_id",
          "capabilities",
          "activation",
          "capacity",
          "migration",
          "budget",
          "circuits",
        ],
        "health result",
      );
      requireSchemaVersion(fields);
      if (
        fields.get("runtime_mode") !== "CANDIDATE_V2" ||
        fields.get("server_release") !== CANDIDATE_DAEMON_RELEASE ||
        fields.get("runtime_build_hash") !==
          context.get("runtimeBuildHash") ||
        fields.get("process_boot_id") !== context.get("serverInstanceId") ||
        fields.get("process_started_at_ms") !==
          context.get("serverStartedAtMs") ||
        fields.get("protocol_version") !== CANDIDATE_DAEMON_PROTOCOL_VERSION ||
        fields.get("rpc_schema_version") !== CANDIDATE_DAEMON_RPC_SCHEMA_VERSION ||
        fields.get("store_schema_version") !==
          CANDIDATE_DAEMON_REQUIRED_STORE_SCHEMA_VERSION
      ) {
        throw new TypeError("invalid health runtime identity");
      }
      if (
        context.get("runtimeBuildHash") !== CANDIDATE_RUNTIME_BUILD_HASH ||
        typeof context.get("serverInstanceId") !== "string" ||
        !/^DI-[a-f0-9]{32}$/.test(context.get("serverInstanceId")) ||
        !Number.isSafeInteger(context.get("serverStartedAtMs")) ||
        context.get("serverStartedAtMs") < 1
      ) {
        throw new TypeError("invalid trusted health runtime identity");
      }
      requireProjectId(fields.get("project_id"));
      if (
        fields.get("project_id") !== context.get("projectId") ||
        !Number.isSafeInteger(fields.get("origin_id")) ||
        fields.get("origin_id") !== context.get("originId")
      ) {
        throw new TypeError("invalid health session identity");
      }
      requireExactStringArray(
        fields.get("capabilities"),
        CANDIDATE_DAEMON_REQUIRED_CAPABILITIES,
        "health capabilities",
      );

      const activation = captureExactObject(
        fields.get("activation"),
        ["runtime_accepted", "production_eligible", "windows_acl"],
        "health activation",
      );
      requireBoolean(activation.get("runtime_accepted"), "runtime acceptance");
      requireBoolean(activation.get("production_eligible"), "production eligibility");
      const trustedProfile = context.get("profile");
      if (
        activation.get("runtime_accepted") !== CANDIDATE_DAEMON_RUNTIME_ACCEPTED ||
        activation.get("production_eligible") !==
          trustedProfile.activation.productionActivationEligible ||
        activation.get("windows_acl") !== trustedProfile.activation.windowsAcl
      ) {
        throw new TypeError("invalid health activation authority");
      }

      const capacity = captureExactObject(
        fields.get("capacity"),
        ["read_limit", "write_limit", "active_reads", "active_writes", "queued"],
        "health capacity",
      );
      if (
        ![2, 5].includes(capacity.get("read_limit")) ||
        capacity.get("write_limit") !== 1 ||
        !Number.isSafeInteger(capacity.get("active_reads")) ||
        capacity.get("active_reads") < 0 ||
        capacity.get("active_reads") > capacity.get("read_limit") ||
        !Number.isSafeInteger(capacity.get("active_writes")) ||
        capacity.get("active_writes") < 0 ||
        capacity.get("active_writes") > capacity.get("write_limit") ||
        !Number.isSafeInteger(capacity.get("queued")) ||
        capacity.get("queued") < 0
      ) {
        throw new TypeError("invalid health capacity");
      }

      const migration = captureExactObject(
        fields.get("migration"),
        [
          "attested",
          "attestation_id",
          "source_set_hash",
          "unresolved_collisions",
          "operational_imports",
        ],
        "health migration",
      );
      requireBoolean(migration.get("attested"), "migration attestation");
      if (
        !Number.isSafeInteger(migration.get("unresolved_collisions")) ||
        migration.get("unresolved_collisions") < 0 ||
        !Number.isSafeInteger(migration.get("operational_imports")) ||
        migration.get("operational_imports") < 0
      ) {
        throw new TypeError("invalid health migration counts");
      }
      if (migration.get("attested")) {
        if (
          typeof migration.get("attestation_id") !== "string" ||
          !/^[0-9a-f]{64}$/.test(migration.get("attestation_id")) ||
          typeof migration.get("source_set_hash") !== "string" ||
          !/^[0-9a-f]{64}$/.test(migration.get("source_set_hash")) ||
          migration.get("unresolved_collisions") !== 0 ||
          migration.get("operational_imports") !== 0
        ) {
          throw new TypeError("invalid attested health migration");
        }
      } else if (
        migration.get("attestation_id") !== null ||
        migration.get("source_set_hash") !== null
      ) {
        throw new TypeError("invalid unattested health migration");
      }

      const budget = captureExactObject(
        fields.get("budget"),
        [
          "spent_nano_usd",
          "open_reserved_nano_usd",
          "next_call_estimate_nano_usd",
          "project_ceiling_nano_usd",
          "unknown_reservations",
        ],
        "health budget",
      );
      for (const key of [
        "spent_nano_usd",
        "open_reserved_nano_usd",
        "next_call_estimate_nano_usd",
        "project_ceiling_nano_usd",
        "unknown_reservations",
      ]) {
        if (
          !Number.isSafeInteger(budget.get(key)) ||
          Object.is(budget.get(key), -0) ||
          budget.get(key) < 0
        ) {
          throw new TypeError("invalid health budget amount");
        }
      }
      if (
        budget.get("project_ceiling_nano_usd") <= 0
      ) {
        throw new TypeError("invalid health budget ceiling");
      }
      const budgetSafe =
        BigInt(budget.get("spent_nano_usd")) +
          BigInt(budget.get("open_reserved_nano_usd")) +
          BigInt(budget.get("next_call_estimate_nano_usd")) <=
        BigInt(budget.get("project_ceiling_nano_usd"));

      const circuits = captureExactObject(
        fields.get("circuits"),
        ["provider_calls_enabled", "unavailable_pools"],
        "health circuits",
      );
      requireBoolean(circuits.get("provider_calls_enabled"), "provider-call enablement");
      if (
        !Number.isSafeInteger(circuits.get("unavailable_pools")) ||
        circuits.get("unavailable_pools") < 0
      ) {
        throw new TypeError("invalid health unavailable-pool count");
      }

      const hardReasons = [];
      if (!activation.get("runtime_accepted")) hardReasons.push("activation-disabled");
      if (!activation.get("production_eligible")) {
        hardReasons.push("production-ineligible");
      }
      if (activation.get("windows_acl") !== "PROVEN") {
        hardReasons.push("windows-acl-unproven");
      }
      if (!migration.get("attested")) hardReasons.push("migration-unattested");
      if (migration.get("unresolved_collisions") > 0) {
        hardReasons.push("migration-collision");
      }
      if (migration.get("operational_imports") > 0) {
        hardReasons.push("operational-imports-present");
      }
      const suppliedReasonCodes = captureDenseArray(
        fields.get("reason_codes"),
        "health reason codes",
      );
      for (const reason of suppliedReasonCodes) {
        if (typeof reason !== "string") {
          throw new TypeError("invalid health reason codes");
        }
      }
      for (const reason of [
        "cost-policy-mismatch",
        "cost-accounting-inconsistent",
      ]) {
        if (suppliedReasonCodes.includes(reason)) hardReasons.push(reason);
      }
      if (!budgetSafe || budget.get("unknown_reservations") > 0) {
        hardReasons.push("budget-unsafe");
      }
      for (const reason of [
        "head-validator-inactive",
        "head-producer-inactive",
      ]) {
        if (suppliedReasonCodes.includes(reason)) hardReasons.push(reason);
      }
      const softReasons = [];
      if (
        capacity.get("active_reads") === capacity.get("read_limit") ||
        capacity.get("active_writes") === capacity.get("write_limit") ||
        capacity.get("queued") > 0
      ) {
        softReasons.push("capacity-pressure");
      }
      if (circuits.get("unavailable_pools") > 0) {
        softReasons.push("provider-circuit-open");
      }
      const reasonCodes = [...hardReasons, ...softReasons];
      requireExactStringArray(
        suppliedReasonCodes,
        reasonCodes,
        "health reason codes",
      );
      const expectedReadiness =
        hardReasons.length > 0
          ? "BLOCKED"
          : softReasons.length > 0
            ? "DEGRADED"
            : "READY";
      if (
        fields.get("readiness") !== expectedReadiness ||
        circuits.get("provider_calls_enabled") !== (expectedReadiness === "READY")
      ) {
        throw new TypeError("incoherent health readiness");
      }
      break;
    }
    default:
      throw new TypeError(`candidate success schema is not implemented for ${method}`);
  }
}

function validatePublicError(value) {
  const hasRetryAfter =
    value !== null &&
    typeof value === "object" &&
    Object.hasOwn(value, "retryAfterMs");
  const allowedKeys = hasRetryAfter
    ? ["code", "message", "retryable", "retryAfterMs"]
    : ["code", "message", "retryable"];
  const error = captureExactObject(value, allowedKeys, "candidate RPC error");
  const code = error.get("code");
  if (!Object.hasOwn(CANDIDATE_DAEMON_PUBLIC_ERROR_POLICY, code)) {
    throw new TypeError("invalid candidate RPC error code");
  }
  const policy = CANDIDATE_DAEMON_PUBLIC_ERROR_POLICY[code];
  if (
    error.get("message") !== policy.message ||
    error.get("retryable") !== policy.retryable
  ) {
    throw new TypeError("invalid candidate RPC public error");
  }
  if (hasRetryAfter) {
    const retryAfterMs = error.get("retryAfterMs");
    if (
      policy.retryable !== true ||
      !Number.isSafeInteger(retryAfterMs) ||
      retryAfterMs < 1 ||
      retryAfterMs > 60000
    ) {
      throw new TypeError("invalid candidate RPC retry delay");
    }
  }
}

export function validateCandidateRpcResponseEnvelope(
  method,
  value,
  responseContext = undefined,
) {
  requireMethod(method);
  const okDescriptor =
    value !== null && typeof value === "object"
      ? Object.getOwnPropertyDescriptor(value, "ok")
      : undefined;
  if (
    okDescriptor === undefined ||
    okDescriptor.enumerable !== true ||
    !Object.hasOwn(okDescriptor, "value")
  ) {
    throw new TypeError("invalid candidate RPC response envelope");
  }
  const outer = captureExactObject(
    value,
    okDescriptor.value === true
      ? ["seq", "requestId", "ok", "result"]
      : ["seq", "requestId", "ok", "error"],
    "candidate RPC response envelope",
  );
  if (!Number.isSafeInteger(outer.get("seq")) || outer.get("seq") < 0) {
    throw new TypeError("invalid candidate RPC sequence");
  }
  requireRequestId(outer.get("requestId"));
  if (outer.get("ok") === true) {
    validatePublicResultIdentity(method, outer.get("result"), responseContext);
    assertCandidateCanonicalJsonByteLimit(
      outer.get("result"),
      CANDIDATE_DAEMON_WIRE_LIMITS.maxRpcResultBytes,
    );
  } else if (outer.get("ok") === false) {
    validatePublicError(outer.get("error"));
  } else {
    throw new TypeError("invalid candidate RPC response outcome");
  }
  assertCandidateCanonicalJsonByteLimit(
    value,
    CANDIDATE_DAEMON_WIRE_LIMITS.maxFrameBytes,
  );
  return value;
}

export function candidateDaemonPipeNameForProject(projectId) {
  const exactProjectId = requireProjectId(projectId);
  const digest = crypto
    .createHash("sha256")
    .update(exactProjectId, "utf8")
    .digest("hex")
    .slice(0, 20);
  return `\\\\.\\pipe\\codex-deepluna-${digest}-v${CANDIDATE_DAEMON_PROTOCOL_VERSION}`;
}
