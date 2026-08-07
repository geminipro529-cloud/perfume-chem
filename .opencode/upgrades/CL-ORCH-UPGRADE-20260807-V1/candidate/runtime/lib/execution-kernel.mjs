const DEFAULT_MAX_PACKET_BYTES = 49_152;
const MAX_CANONICAL_DEPTH = 64;
const MAX_CANONICAL_NODES = 10_000;
const PROTOTYPE_TRAP_KEYS = new Set(["__proto__", "constructor", "prototype"]);
const EXECUTE_ATTEMPT_KEYS = Object.freeze([
  "contract",
  "lease",
  "runner",
  "budget",
  "validator",
  "artifactStore",
  "signal",
]);
const LEASE_IDENTITY_KEYS = Object.freeze([
  "jobId",
  "generation",
  "attemptId",
  "workerId",
  "epoch",
  "fence",
]);
const ZERO_ATTEMPT_USAGE = Object.freeze({
  inputTokens: 0,
  outputTokens: 0,
  transmitted: false,
});

function attemptError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

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

function captureExactObject(value, expectedKeys, label) {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new TypeError(`invalid ${label}`);
  }
  const keys = Reflect.ownKeys(value);
  if (
    keys.length !== expectedKeys.length ||
    keys.some((key) => typeof key !== "string" || !expectedKeys.includes(key))
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

function captureDenseArray(value, state, depth) {
  if (Object.getPrototypeOf(value) !== Array.prototype) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains an invalid array");
  }
  const keys = Reflect.ownKeys(value);
  if (
    keys.some((key) => typeof key !== "string") ||
    keys.length !== value.length + 1 ||
    !keys.includes("length")
  ) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains a sparse array");
  }
  const captured = [];
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index));
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains an accessor");
    }
    captured.push(canonicalClone(descriptor.value, state, depth + 1));
  }
  return captured;
}

function capturePlainObject(value, state, depth) {
  if (Object.getPrototypeOf(value) !== Object.prototype) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains an invalid object");
  }
  const keys = Reflect.ownKeys(value);
  if (
    keys.some(
      (key) => typeof key !== "string" || PROTOTYPE_TRAP_KEYS.has(key),
    )
  ) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains a symbol key");
  }
  const captured = {};
  for (const key of [...keys].sort()) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains an accessor");
    }
    captured[key] = canonicalClone(descriptor.value, state, depth + 1);
  }
  return captured;
}

function canonicalClone(value, state = { nodes: 0, seen: new Set() }, depth = 0) {
  if (depth > MAX_CANONICAL_DEPTH) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data exceeds its depth limit");
  }
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains a non-finite number");
    }
    return value;
  }
  if (typeof value !== "object") {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data is not canonical JSON");
  }
  state.nodes += 1;
  if (state.nodes > MAX_CANONICAL_NODES) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data exceeds its node limit");
  }
  if (state.seen.has(value)) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt data contains a cycle");
  }
  state.seen.add(value);
  try {
    return Array.isArray(value)
      ? captureDenseArray(value, state, depth)
      : capturePlainObject(value, state, depth);
  } finally {
    state.seen.delete(value);
  }
}

function captureLeaseIdentity(value) {
  const captured = captureExactObject(value, LEASE_IDENTITY_KEYS, "attempt lease");
  const identity = {};
  for (const key of LEASE_IDENTITY_KEYS) identity[key] = captured.get(key);
  for (const key of ["jobId", "attemptId", "workerId"]) {
    if (typeof identity[key] !== "string" || identity[key].trim() === "") {
      throw new TypeError("invalid attempt lease");
    }
  }
  for (const key of ["generation", "epoch", "fence"]) {
    if (!Number.isSafeInteger(identity[key]) || identity[key] < 1) {
      throw new TypeError("invalid attempt lease");
    }
  }
  return deepFreeze(canonicalClone(identity));
}

function captureInterface(value, expectedMethods, label) {
  const captured = captureExactObject(value, expectedMethods, label);
  const methods = {};
  for (const method of expectedMethods) {
    if (typeof captured.get(method) !== "function") {
      throw new TypeError(`invalid ${label}`);
    }
    methods[method] = captured.get(method);
  }
  return Object.freeze(methods);
}

function requireAbortSignal(signal) {
  if (typeof AbortSignal !== "function" || !(signal instanceof AbortSignal)) {
    throw new TypeError("signal must be an AbortSignal");
  }
  return signal;
}

function assertSameLease(expected, actual) {
  if (JSON.stringify(expected) !== JSON.stringify(actual)) {
    throw attemptError("STALE_ATTEMPT_LEASE", "attempt lease is no longer current");
  }
}

function requirePacketLimit(value) {
  if (!Number.isSafeInteger(value) || value < 1 || value > DEFAULT_MAX_PACKET_BYTES) {
    throw new TypeError("maxPacketBytes must be a positive bounded safe integer");
  }
  return value;
}

function isAccountingUnknown(accounting) {
  return (
    accounting !== null &&
    typeof accounting === "object" &&
    !Array.isArray(accounting) &&
    accounting.status === "UNKNOWN"
  );
}

function isTypedAccountingUncertain(error) {
  return (
    error?.code === "ACCOUNTING_UNCERTAIN" &&
    error?.accountingUncertain === true
  );
}

function accountingBlockedError(causeMessage = "accounting uncertainty was not preserved") {
  const error = new Error("attempt blocked by accounting uncertainty", {
    cause: new Error(causeMessage),
  });
  error.code = "ACCOUNTING_UNCERTAIN";
  error.accountingUncertain = true;
  error.status = "BLOCKED";
  error.retryable = false;
  return error;
}

async function preserveUnknownAccounting(budget, reservation, error) {
  let accounting;
  try {
    accounting = deepFreeze(
      canonicalClone(
        await budget.preserveUnknown(
          Object.freeze({ error, reservation }),
        ),
      ),
    );
  } catch {
    throw accountingBlockedError("accounting uncertainty persistence failed");
  }
  if (!isAccountingUnknown(accounting)) {
    throw accountingBlockedError("accounting uncertainty persistence was invalid");
  }
  return accounting;
}

export function validateAttemptResultPacket(value) {
  const captured = captureExactObject(
    value,
    ["contract", "lease", "result", "accounting", "maxPacketBytes"],
    "attempt packet input",
  );
  const maxPacketBytes = requirePacketLimit(captured.get("maxPacketBytes"));
  canonicalClone(captured.get("contract"));
  const lease = captureLeaseIdentity(captured.get("lease"));
  const result = deepFreeze(canonicalClone(captured.get("result")));
  const accounting = deepFreeze(canonicalClone(captured.get("accounting")));
  if (
    accounting === null ||
    typeof accounting !== "object" ||
    Array.isArray(accounting) ||
    typeof accounting.status !== "string"
  ) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "attempt accounting is invalid");
  }
  const unknown = isAccountingUnknown(accounting);
  const packet = deepFreeze(
    canonicalClone({
      accounting,
      authoritative: !unknown,
      lease,
      outcome: {
        result,
        status: unknown ? "BLOCKED" : result.status ?? "COMPLETED",
      },
      published: !unknown,
      schema_version: 1,
    }),
  );
  if (Buffer.byteLength(JSON.stringify(packet), "utf8") > maxPacketBytes) {
    throw attemptError("ATTEMPT_PACKET_TOO_LARGE", "attempt packet exceeds its byte limit");
  }
  return packet;
}

function assertDeeplyFrozenPacket(value, seen = new Set()) {
  if (value === null || typeof value !== "object" || seen.has(value)) return;
  if (Object.isFrozen(value) !== true) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "validator packet is not deeply immutable");
  }
  seen.add(value);
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (
      descriptor === undefined ||
      (key !== "length" &&
        (descriptor.enumerable !== true || !Object.hasOwn(descriptor, "value")))
    ) {
      throw attemptError("INVALID_ATTEMPT_PACKET", "validator packet contains an accessor");
    }
    if (Object.hasOwn(descriptor, "value")) {
      assertDeeplyFrozenPacket(descriptor.value, seen);
    }
  }
}

function requireValidatedPacket(packet, accounting, maxPacketBytes) {
  const canonical = canonicalClone(packet);
  assertDeeplyFrozenPacket(packet);
  if (JSON.stringify(packet) !== JSON.stringify(canonical)) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "validator packet is not canonical");
  }
  if (Buffer.byteLength(JSON.stringify(canonical), "utf8") > maxPacketBytes) {
    throw attemptError("ATTEMPT_PACKET_TOO_LARGE", "attempt packet exceeds its byte limit");
  }
  if (
    packet === null ||
    typeof packet !== "object" ||
    Array.isArray(packet) ||
    Object.getPrototypeOf(packet) !== Object.prototype ||
    Object.isFrozen(packet) !== true ||
    typeof packet.authoritative !== "boolean" ||
    packet.outcome === null ||
    typeof packet.outcome !== "object" ||
    Object.isFrozen(packet.outcome) !== true
  ) {
    throw attemptError("INVALID_ATTEMPT_PACKET", "validator returned an invalid packet");
  }
  if (
    isAccountingUnknown(accounting) &&
    (packet.authoritative !== false || packet.outcome.status !== "BLOCKED")
  ) {
    throw attemptError(
      "INVALID_ATTEMPT_PACKET",
      "unknown accounting must remain non-authoritative and blocked",
    );
  }
  return packet;
}

export async function executeAttempt(options) {
  const captured = captureExactObject(
    options,
    EXECUTE_ATTEMPT_KEYS,
    "executeAttempt options",
  );
  const contract = deepFreeze(canonicalClone(captured.get("contract")));
  const leaseInterface = captureInterface(
    captured.get("lease"),
    ["assertCurrent"],
    "lease interface",
  );
  const runner = captured.get("runner");
  if (typeof runner !== "function") throw new TypeError("runner must be a function");
  const budget = captureInterface(
    captured.get("budget"),
    ["reserve", "reconcile", "preserveUnknown"],
    "budget interface",
  );
  const validator = captured.get("validator");
  if (typeof validator !== "function") throw new TypeError("validator must be a function");
  const artifactStore = captureInterface(
    captured.get("artifactStore"),
    ["publish"],
    "artifact store interface",
  );
  const signal = requireAbortSignal(captured.get("signal"));

  signal.throwIfAborted();
  const lease = captureLeaseIdentity(
    await leaseInterface.assertCurrent(
      deepFreeze({ contract, phase: "BEFORE_RUN" }),
    ),
  );
  signal.throwIfAborted();
  const reservation = deepFreeze(
    canonicalClone(await budget.reserve(deepFreeze({ contract, lease }))),
  );
  try {
    signal.throwIfAborted();
  } catch (abortError) {
    let settlement;
    try {
      settlement = deepFreeze(
        canonicalClone(
          await budget.reconcile(
            deepFreeze({ reservation, usage: ZERO_ATTEMPT_USAGE }),
          ),
        ),
      );
    } catch (error) {
      if (!isTypedAccountingUncertain(error)) throw error;
      await preserveUnknownAccounting(budget, reservation, error);
      throw accountingBlockedError("aborted attempt settlement remained uncertain");
    }
    if (isAccountingUnknown(settlement)) {
      throw accountingBlockedError("aborted attempt settlement remained unknown");
    }
    throw abortError;
  }

  let result;
  let usage;
  let accounting;
  try {
    const runnerOutput = await runner(
      Object.freeze({ contract, lease, reservation, signal }),
    );
    const runnerFields = captureExactObject(
      runnerOutput,
      ["result", "usage"],
      "runner result",
    );
    result = deepFreeze(canonicalClone(runnerFields.get("result")));
    usage = deepFreeze(canonicalClone(runnerFields.get("usage")));
  } catch (error) {
    if (!isTypedAccountingUncertain(error)) throw error;
    result = deepFreeze({
      code: "ACCOUNTING_UNCERTAIN",
      status: "BLOCKED",
    });
    accounting = await preserveUnknownAccounting(budget, reservation, error);
  }

  if (accounting === undefined) {
    try {
      accounting = deepFreeze(
        canonicalClone(
          await budget.reconcile(deepFreeze({ reservation, usage })),
        ),
      );
    } catch (error) {
      if (!isTypedAccountingUncertain(error)) throw error;
      accounting = await preserveUnknownAccounting(budget, reservation, error);
    }
  }

  const validationInput = deepFreeze({
    accounting,
    contract,
    lease,
    maxPacketBytes: DEFAULT_MAX_PACKET_BYTES,
    result,
  });
  const candidatePacket = requireValidatedPacket(
    await validator(validationInput),
    accounting,
    DEFAULT_MAX_PACKET_BYTES,
  );
  const packet = validateAttemptResultPacket(validationInput);
  if (JSON.stringify(candidatePacket) !== JSON.stringify(packet)) {
    throw attemptError(
      "INVALID_ATTEMPT_PACKET",
      "validator packet does not match the captured attempt",
    );
  }
  if (packet.authoritative !== true) return packet;

  signal.throwIfAborted();
  const currentLease = captureLeaseIdentity(
    await leaseInterface.assertCurrent(
      deepFreeze({ contract, phase: "BEFORE_PUBLISH", result }),
    ),
  );
  assertSameLease(lease, currentLease);
  signal.throwIfAborted();
  await artifactStore.publish(deepFreeze({ contract, lease, packet }));
  return packet;
}
