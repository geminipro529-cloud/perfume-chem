/*
 * Deterministic provider/model/tier bulkheads. This module is intentionally unwired from the
 * v0.9.1 MCP runtime.
 *
 * Design sources:
 * - Closed/open/half-open circuits with limited recovery trials:
 *   https://learn.microsoft.com/azure/architecture/patterns/circuit-breaker
 * - Separate resource pools contain cascading failures:
 *   https://learn.microsoft.com/azure/architecture/patterns/bulkhead
 * - Retry safety, idempotency, bounded backoff, and jitter:
 *   https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
 * - Full-jitter window:
 *   https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
 * - DeepInfra uses a per-model concurrent-request limit and returns HTTP 429 when exceeded:
 *   https://docs.deepinfra.com/account/rate-limits
 */

const ERROR_MESSAGES = Object.freeze({
  INVALID_POLICY: "invalid provider pool policy",
  INVALID_OPTIONS: "invalid provider pool options",
  INVALID_POOL_ID: "invalid pool id",
  INVALID_JOB_ID: "invalid job id",
  UNKNOWN_POOL: "unknown provider pool",
  INVALID_OUTCOME: "invalid provider outcome",
  INVALID_CLOCK: "invalid provider pool clock",
  INVALID_RETRY_INPUT: "invalid retry classification input",
  INVALID_JITTER_INPUT: "invalid full jitter input",
  INVALID_DIAGNOSTIC_INPUT: "invalid diagnostic routing input",
});

const CIRCUIT_FAILURE_CLASSES = new Set([
  "PROVIDER_TRANSIENT",
  "PROVIDER_AUTHENTICATION",
  "PROVIDER_RATE_LIMIT",
  "PROVIDER_NETWORK",
]);

const RETRYABLE_FAILURE_CLASSES = new Set([
  "PROVIDER_TRANSIENT",
  "PROVIDER_RATE_LIMIT",
  "PROVIDER_NETWORK",
]);

const DETERMINISTIC_FAILURE_CLASSES = new Set([
  "CONTRACT_FAILURE",
  "CONTRACT_ERROR",
  "ASSERTION_FAILURE",
  "DETERMINISTIC_TEST_FAILURE",
  "TOOL_TEST_FAILURE",
  "SCHEMA_FAILURE",
  "SCHEMA_OUTPUT_FAILURE",
  "PATH_FAILURE",
  "PATH_WRITE_CONFLICT",
  "DISK_FAILURE",
  "DISK_STAGING_FAILURE",
  "CACHE_FAILURE",
  "LOCAL_PREFLIGHT_FAILURE",
  "CANCELLATION",
  "CANCELLED",
  "STALE_EPOCH",
  "STALE_RESULT",
  "USER_INPUT_REQUIRED",
]);

const DIAGNOSTIC_POOLS = new Set([
  "deepseek-flash-diagnostic",
  "deepinfra-gpt-oss-20b-diagnostic",
]);

const EXTERNAL_DIAGNOSTIC_PROVIDERS = new Set([
  "deepinfra",
  "deepseek",
  "local",
  "daemon",
]);

const LOCAL_ONLY_FAILURE_CLASSES = new Set([
  "PROVIDER_AUTHENTICATION",
  "ACCOUNT_WIDE_AUTHENTICATION",
  "NETWORK_ISOLATION",
]);

const PROVIDER_EXTERNAL_DIAGNOSTIC_FAILURE_CLASSES = new Set([
  "PROVIDER_TRANSIENT",
  "PROVIDER_RATE_LIMIT",
  "PROVIDER_NETWORK",
]);

const LOCAL_EXTERNAL_DIAGNOSTIC_FAILURE_CLASSES = new Set([
  "CONTRACT_FAILURE",
  "CONTRACT_ERROR",
  "ASSERTION_FAILURE",
  "DETERMINISTIC_TEST_FAILURE",
  "TOOL_TEST_FAILURE",
  "SCHEMA_FAILURE",
  "SCHEMA_OUTPUT_FAILURE",
  "PATH_FAILURE",
  "PATH_WRITE_CONFLICT",
  "DISK_FAILURE",
  "DISK_STAGING_FAILURE",
  "CACHE_FAILURE",
  "LOCAL_PREFLIGHT_FAILURE",
  "STALE_EPOCH",
  "STALE_RESULT",
  "DAEMON_DEFECT",
]);

const CAPACITY_LANE_IDS = new Set(["deepluna-read", "deepluna-write"]);

export const DEFAULT_PROVIDER_POOL_POLICY = deepFreeze({
  pools: {
    "gpt-5.6-sol": { capacity: 5 },
    "gpt-5.6-luna": { capacity: 5 },
    "deepinfra-flash-priority": { capacity: 25 },
    "deepseek-flash": { capacity: 25 },
    "deepseek-flash-diagnostic": { capacity: 5 },
    "deepinfra-gpt-oss-20b-diagnostic": { capacity: 5 },
    "deepinfra-glm-5.2": { capacity: 15 },
    "deepinfra-kimi-k2.7-code": { capacity: 10 },
    "deepseek-v4-pro": { capacity: 10 },
    "deepinfra-nemotron-ultra": { capacity: 10 },
  },
});

function providerPoolError(code) {
  const error = new Error(ERROR_MESSAGES[code]);
  error.code = code;
  return error;
}

function deepFreeze(value) {
  if (value === null || typeof value !== "object" || Object.isFrozen(value)) {
    return value;
  }
  for (const descriptor of Object.values(Object.getOwnPropertyDescriptors(value))) {
    if (Object.hasOwn(descriptor, "value")) deepFreeze(descriptor.value);
  }
  return Object.freeze(value);
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function captureOwnData(value, allowedKeys) {
  if (!isRecord(value)) throw new TypeError();
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const captured = new Map();
  for (const key of Reflect.ownKeys(descriptors)) {
    if (typeof key !== "string" || !allowedKeys.has(key)) throw new TypeError();
    const descriptor = descriptors[key];
    if (
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError();
    }
    captured.set(key, descriptor.value);
  }
  return captured;
}

function requiredCapturedValue(captured, key) {
  if (!captured.has(key)) throw new TypeError();
  return captured.get(key);
}

function isNonnegativeSafeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function isPositiveSafeInteger(value) {
  return Number.isSafeInteger(value) && value > 0;
}

function requireExactIdentifier(value, code) {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    value.trim().length === 0
  ) {
    throw providerPoolError(code);
  }
  return value;
}

function immutableDecision(value) {
  return Object.freeze(value);
}

function captureRegistryOptions(options) {
  try {
    const captured = captureOwnData(
      options,
      new Set(["now", "failureThreshold", "cooldownMs"]),
    );
    const now = captured.has("now") ? captured.get("now") : Date.now;
    const failureThreshold = captured.has("failureThreshold")
      ? captured.get("failureThreshold")
      : 2;
    const cooldownMs = captured.has("cooldownMs")
      ? captured.get("cooldownMs")
      : 120_000;
    if (
      typeof now !== "function" ||
      !isPositiveSafeInteger(failureThreshold) ||
      !isNonnegativeSafeInteger(cooldownMs)
    ) {
      throw new TypeError();
    }
    return { now, failureThreshold, cooldownMs };
  } catch {
    throw providerPoolError("INVALID_OPTIONS");
  }
}

function capturePolicyCapacities(policy) {
  try {
    const policyFields = captureOwnData(policy, new Set(["pools"]));
    const poolFields = captureOwnData(
      requiredCapturedValue(policyFields, "pools"),
      new Set(
        Object.keys(requiredCapturedValue(policyFields, "pools")),
      ),
    );
    const entries = [...poolFields.entries()].map(([poolId, poolValue]) => {
      if (
        poolId.trim().length === 0 ||
        poolId.trim() !== poolId ||
        CAPACITY_LANE_IDS.has(poolId)
      ) {
        throw new TypeError();
      }
      const pool = captureOwnData(poolValue, new Set(["capacity"]));
      const capacity = requiredCapturedValue(pool, "capacity");
      if (!isPositiveSafeInteger(capacity)) throw new TypeError();
      return [poolId, capacity];
    });
    if (entries.length === 0) throw new TypeError();
    return entries;
  } catch {
    throw providerPoolError("INVALID_POLICY");
  }
}

function captureOutcome(outcome) {
  try {
    const captured = captureOwnData(outcome, new Set(["class", "jobId"]));
    const failureClass = requiredCapturedValue(captured, "class");
    const jobId = captured.has("jobId") ? captured.get("jobId") : undefined;
    if (
      typeof failureClass !== "string" ||
      failureClass.trim().length === 0 ||
      (jobId !== undefined &&
        (typeof jobId !== "string" ||
          jobId.length === 0 ||
          jobId.trim().length === 0))
    ) {
      throw new TypeError();
    }
    return { failureClass, jobId };
  } catch {
    throw providerPoolError("INVALID_OUTCOME");
  }
}

function captureRetryInput(input) {
  try {
    const captured = captureOwnData(
      input,
      new Set([
        "failureClass",
        "attempt",
        "maximumAttempts",
        "idempotent",
      ]),
    );
    const failureClass = requiredCapturedValue(captured, "failureClass");
    const attempt = requiredCapturedValue(captured, "attempt");
    const maximumAttempts = requiredCapturedValue(
      captured,
      "maximumAttempts",
    );
    const idempotent = captured.has("idempotent")
      ? captured.get("idempotent")
      : true;
    if (
      typeof failureClass !== "string" ||
      failureClass.trim().length === 0 ||
      !isPositiveSafeInteger(attempt) ||
      !isPositiveSafeInteger(maximumAttempts) ||
      attempt > maximumAttempts ||
      typeof idempotent !== "boolean"
    ) {
      throw new TypeError();
    }
    return { failureClass, attempt, maximumAttempts, idempotent };
  } catch {
    throw providerPoolError("INVALID_RETRY_INPUT");
  }
}

function captureJitterInput(input) {
  try {
    const captured = captureOwnData(
      input,
      new Set(["attempt", "baseMs", "capMs", "random"]),
    );
    const attempt = requiredCapturedValue(captured, "attempt");
    const baseMs = captured.has("baseMs") ? captured.get("baseMs") : 250;
    const capMs = captured.has("capMs") ? captured.get("capMs") : 10_000;
    const random = captured.has("random") ? captured.get("random") : Math.random;
    if (
      !isNonnegativeSafeInteger(attempt) ||
      !isNonnegativeSafeInteger(baseMs) ||
      !isNonnegativeSafeInteger(capMs) ||
      typeof random !== "function"
    ) {
      throw new TypeError();
    }
    return { attempt, baseMs, capMs, random };
  } catch {
    throw providerPoolError("INVALID_JITTER_INPUT");
  }
}

function captureDiagnosticInput(input) {
  try {
    const captured = captureOwnData(
      input,
      new Set(["provider", "failureClass", "healthiestPoolId"]),
    );
    const provider = requiredCapturedValue(captured, "provider");
    const failureClass = requiredCapturedValue(captured, "failureClass");
    const healthiestPoolId = captured.has("healthiestPoolId")
      ? captured.get("healthiestPoolId")
      : undefined;
    if (
      typeof provider !== "string" ||
      !EXTERNAL_DIAGNOSTIC_PROVIDERS.has(provider) ||
      typeof failureClass !== "string" ||
      failureClass.trim().length === 0 ||
      (healthiestPoolId !== undefined &&
        typeof healthiestPoolId !== "string")
    ) {
      throw new TypeError();
    }
    return { provider, failureClass, healthiestPoolId };
  } catch {
    throw providerPoolError("INVALID_DIAGNOSTIC_INPUT");
  }
}

function cappedExponentialWindow(attempt, baseMs, capMs) {
  if (baseMs === 0 || capMs === 0) return 0;
  if (baseMs >= capMs) return capMs;
  const attemptsToCap = Math.ceil(Math.log2(capMs / baseMs));
  if (attempt >= attemptsToCap) return capMs;
  return Math.min(capMs, baseMs * 2 ** attempt);
}

export class ProviderPoolRegistry {
  #now;

  #failureThreshold;

  #cooldownMs;

  #pools = new Map();

  #jobPools = new Map();

  constructor(policy = DEFAULT_PROVIDER_POOL_POLICY, options = {}) {
    const capturedOptions = captureRegistryOptions(options);
    const capacities = capturePolicyCapacities(policy);
    this.#now = capturedOptions.now;
    this.#failureThreshold = capturedOptions.failureThreshold;
    this.#cooldownMs = capturedOptions.cooldownMs;
    for (const [poolId, capacity] of capacities) {
      this.#pools.set(poolId, {
        capacity,
        leases: new Set(),
        status: "CLOSED",
        failures: 0,
        openUntilMs: null,
        halfOpenCanaryJobId: null,
      });
    }
  }

  tryAcquire(poolId, jobId) {
    const state = this.#requirePool(poolId);
    const exactJobId = requireExactIdentifier(jobId, "INVALID_JOB_ID");
    if (this.#jobPools.has(exactJobId)) {
      return immutableDecision({
        acquired: false,
        reason: "DUPLICATE_JOB",
      });
    }

    const decision = this.#dispatchDecision(state);
    if (!decision.allowed) {
      return immutableDecision({
        acquired: false,
        reason: decision.reason,
      });
    }

    state.leases.add(exactJobId);
    this.#jobPools.set(exactJobId, poolId);
    if (state.status === "HALF_OPEN") {
      state.halfOpenCanaryJobId = exactJobId;
    }
    return immutableDecision({ acquired: true });
  }

  release(poolId, jobId) {
    const state = this.#requirePool(poolId);
    const exactJobId = requireExactIdentifier(jobId, "INVALID_JOB_ID");
    if (!state.leases.has(exactJobId)) return false;

    state.leases.delete(exactJobId);
    if (state.halfOpenCanaryJobId !== exactJobId) {
      this.#jobPools.delete(exactJobId);
    }
    return true;
  }

  canDispatch(poolId) {
    return this.#dispatchDecision(this.#requirePool(poolId));
  }

  validatePoolId(poolId) {
    this.#requirePool(poolId);
    return true;
  }

  recordOutcome(poolId, outcome) {
    const state = this.#requirePool(poolId);
    const { failureClass, jobId } = captureOutcome(outcome);

    if (state.status === "OPEN") {
      if (
        failureClass === "SUCCESS" ||
        !CIRCUIT_FAILURE_CLASSES.has(failureClass)
      ) {
        return;
      }
      this.#refreshCircuit(state, this.#sampleNow());
      if (state.status === "OPEN") return;
    }

    if (state.status === "HALF_OPEN") {
      const canaryJobId = state.halfOpenCanaryJobId;
      if (canaryJobId === null || jobId !== canaryJobId) return;

      const canaryWasReleased = !state.leases.has(canaryJobId);
      if (failureClass === "SUCCESS") {
        this.#closeCircuit(state);
        if (canaryWasReleased) this.#jobPools.delete(canaryJobId);
        return;
      }
      if (DETERMINISTIC_FAILURE_CLASSES.has(failureClass)) {
        state.halfOpenCanaryJobId = null;
        if (canaryWasReleased) this.#jobPools.delete(canaryJobId);
        return;
      }
      if (!CIRCUIT_FAILURE_CLASSES.has(failureClass)) return;

      const now = this.#sampleNow();
      this.#openCircuit(state, now);
      if (canaryWasReleased) this.#jobPools.delete(canaryJobId);
      return;
    }

    if (failureClass === "SUCCESS") {
      this.#closeCircuit(state);
      return;
    }
    if (!CIRCUIT_FAILURE_CLASSES.has(failureClass)) return;

    const now = this.#sampleNow();
    const nextFailures = state.failures + 1;
    if (!Number.isSafeInteger(nextFailures)) {
      throw providerPoolError("INVALID_CLOCK");
    }
    if (nextFailures >= this.#failureThreshold) {
      this.#openCircuit(state, now);
    } else {
      state.failures = nextFailures;
    }
  }

  snapshot() {
    const openStates = [...this.#pools.values()].filter(
      (state) => state.status === "OPEN",
    );
    if (openStates.length > 0) {
      const now = this.#sampleNow();
      for (const state of openStates) this.#refreshCircuit(state, now);
    }

    const entries = [...this.#pools.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([poolId, state]) => [
        poolId,
        {
          capacity: state.capacity,
          active: state.leases.size,
          available: Math.max(0, state.capacity - state.leases.size),
          status: state.status,
          failures: state.failures,
          halfOpenCanaryInFlight:
            state.status === "HALF_OPEN" &&
            state.halfOpenCanaryJobId !== null,
        },
      ]);
    return deepFreeze({ pools: Object.fromEntries(entries) });
  }

  #requirePool(poolId) {
    const exactPoolId = requireExactIdentifier(poolId, "INVALID_POOL_ID");
    const state = this.#pools.get(exactPoolId);
    if (state === undefined) throw providerPoolError("UNKNOWN_POOL");
    return state;
  }

  #dispatchDecision(state) {
    if (state.status === "OPEN") {
      this.#refreshCircuit(state, this.#sampleNow());
    }
    if (state.status === "OPEN") {
      return immutableDecision({
        allowed: false,
        reason: "CIRCUIT_OPEN",
      });
    }
    if (
      state.status === "HALF_OPEN" &&
      state.halfOpenCanaryJobId !== null
    ) {
      return immutableDecision({
        allowed: false,
        reason: "HALF_OPEN_CANARY_IN_FLIGHT",
      });
    }
    if (state.leases.size >= state.capacity) {
      return immutableDecision({ allowed: false, reason: "CAPACITY" });
    }
    return immutableDecision({ allowed: true });
  }

  #sampleNow() {
    let now;
    try {
      now = this.#now();
    } catch {
      throw providerPoolError("INVALID_CLOCK");
    }
    if (!isNonnegativeSafeInteger(now)) {
      throw providerPoolError("INVALID_CLOCK");
    }
    return now;
  }

  #refreshCircuit(state, now) {
    if (
      state.status === "OPEN" &&
      state.openUntilMs !== null &&
      now >= state.openUntilMs
    ) {
      state.status = "HALF_OPEN";
      state.openUntilMs = null;
      state.halfOpenCanaryJobId = null;
    }
  }

  #openCircuit(state, now) {
    const openUntilMs = now + this.#cooldownMs;
    if (!isNonnegativeSafeInteger(openUntilMs)) {
      throw providerPoolError("INVALID_CLOCK");
    }
    state.status = "OPEN";
    state.failures = this.#failureThreshold;
    state.openUntilMs = openUntilMs;
    state.halfOpenCanaryJobId = null;
  }

  #closeCircuit(state) {
    state.status = "CLOSED";
    state.failures = 0;
    state.openUntilMs = null;
    state.halfOpenCanaryJobId = null;
  }
}

export function classifyRetry(input) {
  const {
    failureClass,
    attempt,
    maximumAttempts,
    idempotent,
  } = captureRetryInput(input);
  if (!RETRYABLE_FAILURE_CLASSES.has(failureClass)) {
    return immutableDecision({
      retry: false,
      reason: DETERMINISTIC_FAILURE_CLASSES.has(failureClass)
        ? "DETERMINISTIC_FAILURE"
        : "NON_RETRYABLE_FAILURE",
    });
  }
  if (!idempotent) {
    return immutableDecision({ retry: false, reason: "NON_IDEMPOTENT" });
  }
  if (attempt >= maximumAttempts) {
    return immutableDecision({
      retry: false,
      reason: "ATTEMPTS_EXHAUSTED",
    });
  }
  return immutableDecision({
    retry: true,
    reason: "TRANSIENT_WITH_ATTEMPT_AVAILABLE",
  });
}

export function fullJitterDelay(input) {
  const { attempt, baseMs, capMs, random } = captureJitterInput(input);
  let sample;
  try {
    sample = random();
  } catch {
    throw providerPoolError("INVALID_JITTER_INPUT");
  }
  if (
    typeof sample !== "number" ||
    !Number.isFinite(sample) ||
    sample < 0 ||
    sample >= 1
  ) {
    throw providerPoolError("INVALID_JITTER_INPUT");
  }

  const windowMs = cappedExponentialWindow(attempt, baseMs, capMs);
  if (windowMs === Number.MAX_SAFE_INTEGER) {
    return Math.floor(sample * windowMs);
  }
  return Math.min(windowMs, Math.floor(sample * (windowMs + 1)));
}

export function diagnosticPoolForFailure(input) {
  const { provider, failureClass, healthiestPoolId } =
    captureDiagnosticInput(input);
  if (LOCAL_ONLY_FAILURE_CLASSES.has(failureClass)) {
    return "LOCAL_DIAGNOSTIC_ONLY";
  }
  if (provider === "deepinfra") {
    return PROVIDER_EXTERNAL_DIAGNOSTIC_FAILURE_CLASSES.has(failureClass)
      ? "deepseek-flash-diagnostic"
      : "LOCAL_DIAGNOSTIC_ONLY";
  }
  if (provider === "deepseek") {
    return PROVIDER_EXTERNAL_DIAGNOSTIC_FAILURE_CLASSES.has(failureClass)
      ? "deepinfra-gpt-oss-20b-diagnostic"
      : "LOCAL_DIAGNOSTIC_ONLY";
  }
  if (!LOCAL_EXTERNAL_DIAGNOSTIC_FAILURE_CLASSES.has(failureClass)) {
    return "LOCAL_DIAGNOSTIC_ONLY";
  }
  return DIAGNOSTIC_POOLS.has(healthiestPoolId)
    ? healthiestPoolId
    : "LOCAL_DIAGNOSTIC_ONLY";
}
