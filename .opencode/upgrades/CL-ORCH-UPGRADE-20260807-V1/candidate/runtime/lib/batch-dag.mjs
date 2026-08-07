const MAX_BATCH_NODES = 20;
const SAFE_NODE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const PROTOTYPE_TRAPS = new Set(["__proto__", "constructor", "prototype"]);
const ACCEPTED_TERMINAL = new Set(["PASS", "CACHED"]);
const NONACCEPTED_TERMINAL = new Set([
  "FAIL",
  "BLOCKED",
  "CANCELED",
  "CANCELLED",
  "PROVIDER_ERROR",
  "CONTRACT_ERROR",
  "QUARANTINED",
  "INCOMPLETE",
]);
const KNOWN_STATUSES = new Set([
  ...ACCEPTED_TERMINAL,
  ...NONACCEPTED_TERMINAL,
  "INCOMPLETE",
  "QUEUED",
  "RUNNING",
]);

function ordinalCompare(left, right) {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function dagError() {
  const error = new TypeError("invalid batch DAG");
  error.code = "INVALID_BATCH_DAG";
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

function captureDenseArray(value) {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw dagError();
  }
  const keys = Reflect.ownKeys(value);
  if (
    keys.some((key) => typeof key !== "string") ||
    keys.length !== value.length + 1 ||
    !keys.includes("length")
  ) {
    throw dagError();
  }
  const captured = [];
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index));
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw dagError();
    }
    captured.push(descriptor.value);
  }
  return captured;
}

function captureNode(value) {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw dagError();
  }
  const keys = Reflect.ownKeys(value);
  if (
    keys.length !== 2 ||
    keys.some(
      (key) =>
        typeof key !== "string" || (key !== "nodeId" && key !== "dependsOn"),
    )
  ) {
    throw dagError();
  }
  const nodeIdDescriptor = Object.getOwnPropertyDescriptor(value, "nodeId");
  const dependenciesDescriptor = Object.getOwnPropertyDescriptor(value, "dependsOn");
  if (
    nodeIdDescriptor === undefined ||
    dependenciesDescriptor === undefined ||
    nodeIdDescriptor.enumerable !== true ||
    dependenciesDescriptor.enumerable !== true ||
    !Object.hasOwn(nodeIdDescriptor, "value") ||
    !Object.hasOwn(dependenciesDescriptor, "value")
  ) {
    throw dagError();
  }
  const nodeId = nodeIdDescriptor.value;
  if (
    typeof nodeId !== "string" ||
    !SAFE_NODE_ID.test(nodeId) ||
    PROTOTYPE_TRAPS.has(nodeId)
  ) {
    throw dagError();
  }
  const dependsOn = captureDenseArray(dependenciesDescriptor.value);
  if (
    dependsOn.length > MAX_BATCH_NODES ||
    dependsOn.some(
      (dependency) =>
        typeof dependency !== "string" ||
        !SAFE_NODE_ID.test(dependency) ||
        PROTOTYPE_TRAPS.has(dependency),
    ) ||
    new Set(dependsOn).size !== dependsOn.length ||
    dependsOn.includes(nodeId)
  ) {
    throw dagError();
  }
  return { dependsOn: [...dependsOn].sort(ordinalCompare), nodeId };
}

function assertAcyclic(nodes, nodeById) {
  const visited = new Set();
  const active = new Set();
  const visit = (nodeId) => {
    if (active.has(nodeId)) throw dagError();
    if (visited.has(nodeId)) return;
    active.add(nodeId);
    for (const dependency of nodeById.get(nodeId).dependsOn) visit(dependency);
    active.delete(nodeId);
    visited.add(nodeId);
  };
  for (const node of nodes) visit(node.nodeId);
}

function captureStatuses(value, nodeIds) {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    ![Object.prototype, null].includes(Object.getPrototypeOf(value))
  ) {
    throw dagError();
  }
  const captured = Object.create(null);
  for (const key of Reflect.ownKeys(value).sort()) {
    if (typeof key !== "string" || !nodeIds.has(key)) throw dagError();
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value") ||
      typeof descriptor.value !== "string" ||
      !KNOWN_STATUSES.has(descriptor.value)
    ) {
      throw dagError();
    }
    captured[key] = descriptor.value;
  }
  return captured;
}

export function validateBatchDag(value) {
  const rawNodes = captureDenseArray(value);
  if (rawNodes.length < 1 || rawNodes.length > MAX_BATCH_NODES) throw dagError();
  const nodes = rawNodes
    .map(captureNode)
    .sort((left, right) => ordinalCompare(left.nodeId, right.nodeId));
  const nodeById = new Map();
  for (const node of nodes) {
    if (nodeById.has(node.nodeId)) throw dagError();
    nodeById.set(node.nodeId, node);
  }
  for (const node of nodes) {
    if (node.dependsOn.some((dependency) => !nodeById.has(dependency))) {
      throw dagError();
    }
  }
  assertAcyclic(nodes, nodeById);
  return deepFreeze(nodes);
}

export function readyNodes(value, statusByNodeId) {
  const nodes = validateBatchDag(value);
  const nodeIds = new Set(nodes.map((node) => node.nodeId));
  const statuses = captureStatuses(statusByNodeId, nodeIds);
  return deepFreeze(
    nodes
      .filter(
        (node) =>
          !Object.hasOwn(statuses, node.nodeId) &&
          node.dependsOn.every((dependency) =>
            ACCEPTED_TERMINAL.has(statuses[dependency]),
          ),
      )
      .map((node) => node.nodeId),
  );
}

export function propagateBlocked(value, statusByNodeId) {
  const nodes = validateBatchDag(value);
  const nodeIds = new Set(nodes.map((node) => node.nodeId));
  const statuses = captureStatuses(statusByNodeId, nodeIds);
  let changed = true;
  while (changed) {
    changed = false;
    for (const node of nodes) {
      if (
        !Object.hasOwn(statuses, node.nodeId) &&
        node.dependsOn.some((dependency) =>
          NONACCEPTED_TERMINAL.has(statuses[dependency]),
        )
      ) {
        statuses[node.nodeId] = "BLOCKED";
        changed = true;
      }
    }
  }
  const ordered = {};
  for (const nodeId of Object.keys(statuses).sort()) ordered[nodeId] = statuses[nodeId];
  return deepFreeze(ordered);
}
