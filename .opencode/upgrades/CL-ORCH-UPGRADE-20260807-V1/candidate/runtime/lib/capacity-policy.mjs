/*
 * Pure in-memory capacity simulation. It does not start workers or alter live lane counts.
 *
 * Design sources:
 * - Fair per-flow service: https://dl.acm.org/doi/10.1145/75246.75248
 * - Guaranteed capacity, idle borrowing, and reclaim as work completes:
 *   https://hadoop.apache.org/docs/r3.4.1/hadoop-yarn/hadoop-yarn-site/CapacityScheduler.html
 * - Bounded queues and backpressure:
 *   https://github.com/reactive-streams/reactive-streams-jvm
 * - Descriptor capture and Proxy trap semantics:
 *   https://tc39.es/ecma262/multipage/fundamental-objects.html#sec-object.getownpropertydescriptors
 */

const ERROR_MESSAGES = Object.freeze({
  INVALID_CAPACITY_POLICY: "invalid capacity policy",
  INVALID_JOB: "invalid job",
  UNKNOWN_POOL: "unknown pool",
  DUPLICATE_JOB: "duplicate job",
  ACTIVE_TASK_LIMIT: "active task limit",
  QUEUE_LIMIT: "queue limit",
  DIAGNOSTIC_ONLY: "diagnostic-only pool",
  REENTRANT_MUTATION: "scheduler mutation during eligibility check",
});

function schedulerError(code) {
  const error = new Error(ERROR_MESSAGES[code]);
  error.code = code;
  return error;
}

function deepFreeze(value) {
  if (value === null || typeof value !== "object" || Object.isFrozen(value)) {
    return value;
  }
  for (const child of Object.values(value)) {
    deepFreeze(child);
  }
  return Object.freeze(value);
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isNonNegativeSafeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function isPositiveSafeInteger(value) {
  return Number.isSafeInteger(value) && value > 0;
}

function captureOwnDataMap(value) {
  if (!isRecord(value)) throw new TypeError();
  const descriptorObject = Object.getOwnPropertyDescriptors(value);
  const values = new Map();
  for (const key of Reflect.ownKeys(descriptorObject)) {
    if (typeof key !== "string") throw new TypeError();
    const descriptor = descriptorObject[key];
    if (!Object.hasOwn(descriptor, "value") || descriptor.enumerable !== true) {
      throw new TypeError();
    }
    values.set(key, descriptor.value);
  }
  return values;
}

function requiredCapturedValue(values, key) {
  if (!values.has(key)) throw new TypeError();
  return values.get(key);
}

function capturedPolicyIsValid(policy) {
  if (!isPositiveSafeInteger(policy.maxActiveTasks)) return false;
  if (!isPositiveSafeInteger(policy.globalQueueLimit)) return false;
  if (!isPositiveSafeInteger(policy.perTaskQueueLimit)) return false;

  const poolEntries = Object.entries(policy.pools);
  if (poolEntries.length === 0) return false;

  let totalCapacity = 0;
  let totalPerTaskReservation = 0;
  let maximumPoolCapacity = 0;
  for (const [poolId, pool] of poolEntries) {
    if (poolId.trim().length === 0 || poolId.trim() !== poolId) return false;
    if (!isNonNegativeSafeInteger(pool.capacity)) return false;
    if (!isNonNegativeSafeInteger(pool.reservedPerTask)) return false;
    if (!isNonNegativeSafeInteger(pool.shared)) return false;
    if (typeof pool.diagnosticOnly !== "boolean") return false;

    const reservedCapacity = pool.reservedPerTask * policy.maxActiveTasks;
    if (!Number.isSafeInteger(reservedCapacity)) return false;
    const computedCapacity = reservedCapacity + pool.shared;
    if (!Number.isSafeInteger(computedCapacity) || computedCapacity !== pool.capacity) {
      return false;
    }
    if (pool.diagnosticOnly && pool.shared !== 0) return false;

    totalCapacity += pool.capacity;
    totalPerTaskReservation += pool.reservedPerTask;
    if (!Number.isSafeInteger(totalCapacity)) return false;
    if (!Number.isSafeInteger(totalPerTaskReservation)) return false;
    maximumPoolCapacity = Math.max(maximumPoolCapacity, pool.capacity);
  }

  if (policy.globalQueueLimit < totalCapacity) return false;
  // One task must be able to queue a full single pool or all of its cross-pool guarantees.
  const minimumPerTaskLimit = Math.max(maximumPoolCapacity, totalPerTaskReservation);
  return policy.perTaskQueueLimit >= minimumPerTaskLimit;
}

function captureCapacityPolicy(policy) {
  try {
    const policyValues = captureOwnDataMap(policy);
    const poolValues = captureOwnDataMap(requiredCapturedValue(policyValues, "pools"));
    const pools = Object.fromEntries(
      [...poolValues.entries()].map(([poolId, poolValue]) => {
        const pool = captureOwnDataMap(poolValue);
        return [
          poolId,
          {
            capacity: requiredCapturedValue(pool, "capacity"),
            reservedPerTask: requiredCapturedValue(pool, "reservedPerTask"),
            shared: requiredCapturedValue(pool, "shared"),
            diagnosticOnly: requiredCapturedValue(pool, "diagnosticOnly"),
          },
        ];
      }),
    );
    const snapshot = {
      maxActiveTasks: requiredCapturedValue(policyValues, "maxActiveTasks"),
      globalQueueLimit: requiredCapturedValue(policyValues, "globalQueueLimit"),
      perTaskQueueLimit: requiredCapturedValue(policyValues, "perTaskQueueLimit"),
      pools,
    };
    if (!capturedPolicyIsValid(snapshot)) throw new TypeError();
    return deepFreeze(snapshot);
  } catch {
    throw schedulerError("INVALID_CAPACITY_POLICY");
  }
}

export function validateCapacityPolicy(policy) {
  captureCapacityPolicy(policy);
  return true;
}

function configuredPool(policy, poolId) {
  if (typeof poolId !== "string" || poolId.trim().length === 0) return undefined;
  return Object.hasOwn(policy.pools, poolId) ? policy.pools[poolId] : undefined;
}

function starvationThreshold(policy, pool) {
  return BigInt(policy.maxActiveTasks) + BigInt(pool.capacity);
}

function compareAging(left, right) {
  if (left.enqueuedAtDispatch !== right.enqueuedAtDispatch) {
    return left.enqueuedAtDispatch < right.enqueuedAtDispatch ? -1 : 1;
  }
  if (left.enqueueOrdinal !== right.enqueueOrdinal) {
    return left.enqueueOrdinal < right.enqueueOrdinal ? -1 : 1;
  }
  return 0;
}

function agingState() {
  return {
    dispatchCount: 0n,
    nextEnqueueOrdinal: 0n,
  };
}

function newAgingMetadata(state) {
  const metadata = {
    enqueuedAtDispatch: state.dispatchCount,
    enqueueOrdinal: state.nextEnqueueOrdinal,
  };
  state.nextEnqueueOrdinal += 1n;
  return metadata;
}

function isStarved(metadata, state, threshold) {
  return state.dispatchCount - metadata.enqueuedAtDispatch >= threshold;
}

export const DEFAULT_CAPACITY_POLICY = deepFreeze({
  maxActiveTasks: 5,
  globalQueueLimit: 100,
  perTaskQueueLimit: 20,
  pools: {
    "deepluna-read": {
      capacity: 2,
      reservedPerTask: 0,
      shared: 2,
      diagnosticOnly: false,
    },
    "deepluna-write": {
      capacity: 1,
      reservedPerTask: 0,
      shared: 1,
      diagnosticOnly: false,
    },
  },
});

export const FAST_ONLY_CAPACITY_POLICY = deepFreeze({
  maxActiveTasks: 5,
  globalQueueLimit: 100,
  perTaskQueueLimit: 20,
  pools: {
    "deepluna-read": {
      capacity: 5,
      reservedPerTask: 0,
      shared: 5,
      diagnosticOnly: false,
    },
    "deepluna-write": {
      capacity: 1,
      reservedPerTask: 0,
      shared: 1,
      diagnosticOnly: false,
    },
  },
});

export function resolveCapacityPolicy({
  fastOnly = process.env.DEEPLUNA_FAST_ONLY === "1",
} = {}) {
  if (typeof fastOnly !== "boolean") {
    throw new TypeError("capacity policy fastOnly must be boolean");
  }
  return fastOnly ? FAST_ONLY_CAPACITY_POLICY : DEFAULT_CAPACITY_POLICY;
}

export function capacityLaneForRole(role) {
  if (role === "READER" || role === "REVIEWER" || role === "DIAGNOSTIC") {
    return "deepluna-read";
  }
  if (role === "WRITER") return "deepluna-write";
  throw schedulerError("INVALID_JOB");
}

function requiredNormalizedString(value) {
  if (typeof value !== "string") throw schedulerError("INVALID_JOB");
  const normalized = value.trim();
  if (normalized.length === 0) throw schedulerError("INVALID_JOB");
  return normalized;
}

function normalizeJob(input) {
  try {
    if (!isRecord(input)) throw schedulerError("INVALID_JOB");
    const rawRole = input.role;
    const normalized = {
      jobId: requiredNormalizedString(input.jobId),
      taskId: requiredNormalizedString(input.taskId),
      poolId: requiredNormalizedString(input.poolId),
      priority: input.priority,
      createdAtMs: input.createdAtMs,
    };
    if (!Number.isSafeInteger(normalized.priority)) {
      throw schedulerError("INVALID_JOB");
    }
    if (!isNonNegativeSafeInteger(normalized.createdAtMs)) {
      throw schedulerError("INVALID_JOB");
    }
    if (rawRole !== undefined) {
      normalized.role = requiredNormalizedString(rawRole);
    }
    return { normalized, rawRole };
  } catch {
    throw schedulerError("INVALID_JOB");
  }
}

function compareStrings(left, right) {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function compareJobs(left, right) {
  if (left.priority !== right.priority) return right.priority - left.priority;
  if (left.createdAtMs !== right.createdAtMs) {
    return left.createdAtMs - right.createdAtMs;
  }
  return compareStrings(left.jobId, right.jobId);
}

function copyJob(job) {
  const copy = {
    jobId: job.jobId,
    taskId: job.taskId,
    poolId: job.poolId,
    priority: job.priority,
    createdAtMs: job.createdAtMs,
  };
  if (job.role !== undefined) copy.role = job.role;
  return copy;
}

export class WeightedFairScheduler {
  #policy;

  #queues = new Map();

  #queuedById = new Map();

  #runningById = new Map();

  #queuedPerTask = new Map();

  #taskJobs = new Map();

  #rotation = new Map();

  #deferredTasks = new Map();

  #normalProbeNext = new Map();

  #poolAging = new Map();

  #agingByJobId = new Map();

  #queuedCount = 0;

  #eligibilityCallbackActive = false;

  #reentrantMutationAttempted = false;

  constructor(policy = DEFAULT_CAPACITY_POLICY) {
    this.#policy = captureCapacityPolicy(policy);
    for (const poolId of Object.keys(this.#policy.pools)) {
      this.#queues.set(poolId, []);
      this.#rotation.set(poolId, { order: [], cursor: 0 });
      this.#deferredTasks.set(poolId, []);
      this.#normalProbeNext.set(poolId, false);
      this.#poolAging.set(poolId, agingState());
    }
  }

  enqueue(input) {
    this.#assertMutationAllowed();
    const { normalized: job, rawRole } = normalizeJob(input);
    const pool = configuredPool(this.#policy, job.poolId);
    if (pool === undefined) throw schedulerError("UNKNOWN_POOL");
    if (this.#queuedById.has(job.jobId) || this.#runningById.has(job.jobId)) {
      throw schedulerError("DUPLICATE_JOB");
    }
    if (pool.diagnosticOnly && rawRole !== "DIAGNOSTIC") {
      throw schedulerError("DIAGNOSTIC_ONLY");
    }

    const taskIsActive = this.#taskJobs.has(job.taskId);
    if (!taskIsActive && this.#taskJobs.size >= this.#policy.maxActiveTasks) {
      throw schedulerError("ACTIVE_TASK_LIMIT");
    }
    const taskQueued = this.#queuedPerTask.get(job.taskId) ?? 0;
    if (
      this.#queuedCount >= this.#policy.globalQueueLimit ||
      taskQueued >= this.#policy.perTaskQueueLimit
    ) {
      throw schedulerError("QUEUE_LIMIT");
    }

    this.#queues.get(job.poolId).push(job);
    this.#queuedById.set(job.jobId, job);
    this.#queuedCount += 1;
    this.#queuedPerTask.set(job.taskId, taskQueued + 1);
    this.#taskJobs.set(job.taskId, (this.#taskJobs.get(job.taskId) ?? 0) + 1);
    this.#addTaskToRotation(job.poolId, job.taskId);
    this.#agingByJobId.set(
      job.jobId,
      newAgingMetadata(this.#poolAging.get(job.poolId)),
    );
    return copyJob(job);
  }

  dispatchNext(poolId) {
    this.#assertMutationAllowed();
    const queue = this.#queues.get(poolId);
    return this.dispatchNextEligible(
      poolId,
      () => true,
      { scanLimit: queue === undefined ? 1 : Math.max(1, queue.length) },
    );
  }

  dispatchNextEligible(poolId, isEligible, { scanLimit } = {}) {
    this.#assertMutationAllowed();
    const pool = configuredPool(this.#policy, poolId);
    if (pool === undefined) throw schedulerError("UNKNOWN_POOL");
    if (typeof isEligible !== "function" || !isPositiveSafeInteger(scanLimit)) {
      throw schedulerError("INVALID_JOB");
    }
    const runningInPool = this.#runningCount(poolId);
    if (runningInPool >= pool.capacity) return null;

    const queue = this.#queues.get(poolId);
    if (queue.length === 0) return null;

    const rotation = this.#rotation.get(poolId);
    const rotationBefore = {
      order: [...rotation.order],
      cursor: rotation.cursor,
    };
    const deferredBefore = [...this.#deferredTasks.get(poolId)];
    const normalProbeBefore = this.#normalProbeNext.get(poolId);
    let selectedIndex = -1;
    let selectedRotationIndex = -1;
    let selectedFromDeferred = false;
    let selectedJobId;
    let scanned = 0;
    try {
      this.#pruneRotation(poolId);
      this.#pruneDeferred(poolId);
      let deferred = [...this.#deferredTasks.get(poolId)];
      const hadDeferredAtStart = deferred.length > 0;
      const normalProbeFirst =
        hadDeferredAtStart && this.#normalProbeNext.get(poolId);
      let lastProbePhase;

      const probeDeferred = () => {
        const probeOrder = [...deferred];
        let nextDeferredTaskId;
        for (let taskIndex = 0; taskIndex < probeOrder.length; taskIndex += 1) {
          const taskId = probeOrder[taskIndex];
          const candidates = this.#orderedQueuedIndexes(
            poolId,
            queue,
            (job) => job.taskId === taskId,
            pool,
          );
          let taskWasProbed = false;
          for (const candidateIndex of candidates) {
            if (scanned >= scanLimit) break;
            scanned += 1;
            taskWasProbed = true;
            lastProbePhase = "DEFERRED";
            if (this.#evaluateEligibility(queue[candidateIndex], isEligible)) {
              selectedIndex = candidateIndex;
              selectedJobId = queue[candidateIndex].jobId;
              selectedFromDeferred = true;
              break;
            }
          }
          if (taskWasProbed && probeOrder.length > 1) {
            nextDeferredTaskId =
              probeOrder[(taskIndex + 1) % probeOrder.length];
          }
          if (selectedIndex !== -1 || scanned >= scanLimit) break;
        }
        if (selectedIndex === -1 && nextDeferredTaskId !== undefined) {
          const nextIndex = deferred.indexOf(nextDeferredTaskId);
          deferred = [
            ...deferred.slice(nextIndex),
            ...deferred.slice(0, nextIndex),
          ];
        }
      };

      const probeNormal = () => {
        const deferredSet = new Set(deferred);
        for (let offset = 0; offset < rotation.order.length; offset += 1) {
          const rotationIndex =
            (rotation.cursor + offset) % rotation.order.length;
          const taskId = rotation.order[rotationIndex];
          if (deferredSet.has(taskId)) continue;
          const candidates = this.#orderedQueuedIndexes(
            poolId,
            queue,
            (job) => job.taskId === taskId,
            pool,
          );
          let taskWasSkipped = false;
          for (const candidateIndex of candidates) {
            if (scanned >= scanLimit) break;
            scanned += 1;
            lastProbePhase = "NORMAL";
            if (this.#evaluateEligibility(queue[candidateIndex], isEligible)) {
              selectedIndex = candidateIndex;
              selectedJobId = queue[candidateIndex].jobId;
              selectedRotationIndex = rotationIndex;
              break;
            }
            taskWasSkipped = true;
          }
          if (
            selectedIndex === -1 &&
            taskWasSkipped &&
            !deferredSet.has(taskId)
          ) {
            deferred.push(taskId);
            deferredSet.add(taskId);
          }
          if (selectedIndex !== -1 || scanned >= scanLimit) break;
        }
      };

      if (normalProbeFirst) {
        probeNormal();
        if (selectedIndex === -1 && scanned < scanLimit) probeDeferred();
      } else {
        probeDeferred();
        if (selectedIndex === -1 && scanned < scanLimit) probeNormal();
      }

      if (selectedIndex === -1) {
        this.#deferredTasks.set(poolId, deferred);
        if (lastProbePhase === "DEFERRED") {
          this.#normalProbeNext.set(poolId, true);
        } else if (lastProbePhase === "NORMAL") {
          this.#normalProbeNext.set(poolId, !hadDeferredAtStart);
        }
        return null;
      }
      if (
        queue[selectedIndex]?.jobId !== selectedJobId ||
        this.#queuedById.get(selectedJobId) !== queue[selectedIndex]
      ) {
        throw schedulerError("REENTRANT_MUTATION");
      }
      if (selectedFromDeferred) {
        this.#deferredTasks.set(
          poolId,
          deferred.filter((taskId) => taskId !== queue[selectedIndex].taskId),
        );
        this.#normalProbeNext.set(poolId, true);
      } else {
        this.#deferredTasks.set(poolId, deferred);
        this.#normalProbeNext.set(poolId, false);
        rotation.cursor = (selectedRotationIndex + 1) % rotation.order.length;
      }
    } catch (error) {
      rotation.order = rotationBefore.order;
      rotation.cursor = rotationBefore.cursor;
      this.#deferredTasks.set(poolId, deferredBefore);
      this.#normalProbeNext.set(poolId, normalProbeBefore);
      throw error;
    }

    const [job] = queue.splice(selectedIndex, 1);
    this.#queuedById.delete(job.jobId);
    this.#agingByJobId.delete(job.jobId);
    this.#queuedCount -= 1;
    this.#decrementMapCount(this.#queuedPerTask, job.taskId);
    this.#runningById.set(job.jobId, job);
    this.#poolAging.get(poolId).dispatchCount += 1n;
    this.#pruneDeferred(poolId);
    return copyJob(job);
  }

  release(jobId) {
    this.#assertMutationAllowed();
    if (typeof jobId !== "string") return false;
    const job = this.#runningById.get(jobId);
    if (job === undefined) return false;

    this.#runningById.delete(jobId);
    this.#decrementTaskJobs(job.taskId);
    this.#pruneRotation(job.poolId);
    this.#pruneDeferred(job.poolId);
    return true;
  }

  remove(jobId) {
    this.#assertMutationAllowed();
    if (typeof jobId !== "string") return false;
    const job = this.#queuedById.get(jobId);
    if (job === undefined) return false;

    const queue = this.#queues.get(job.poolId);
    const index = queue.findIndex((queued) => queued.jobId === jobId);
    if (index === -1) return false;
    queue.splice(index, 1);
    this.#queuedById.delete(jobId);
    this.#agingByJobId.delete(jobId);
    this.#queuedCount -= 1;
    this.#decrementMapCount(this.#queuedPerTask, job.taskId);
    this.#decrementTaskJobs(job.taskId);
    this.#pruneRotation(job.poolId);
    this.#pruneDeferred(job.poolId);
    return true;
  }

  snapshot() {
    const poolEntries = [];
    for (const poolId of Object.keys(this.#policy.pools).sort(compareStrings)) {
      const policyPool = this.#policy.pools[poolId];
      const taskIds = new Set();
      for (const job of this.#queues.get(poolId)) taskIds.add(job.taskId);
      for (const job of this.#runningById.values()) {
        if (job.poolId === poolId) taskIds.add(job.taskId);
      }

      let reservedRunning = 0;
      let borrowed = 0;
      const taskEntries = [];
      for (const taskId of [...taskIds].sort(compareStrings)) {
        const queued = this.#queues
          .get(poolId)
          .filter((job) => job.taskId === taskId).length;
        const running = this.#runningCount(poolId, taskId);
        const taskReservedRunning = Math.min(running, policyPool.reservedPerTask);
        const taskBorrowed = Math.max(0, running - policyPool.reservedPerTask);
        reservedRunning += taskReservedRunning;
        borrowed += taskBorrowed;
        taskEntries.push([
          taskId,
          {
            queued,
            running,
            reservation: policyPool.reservedPerTask,
            reservedRunning: taskReservedRunning,
            borrowed: taskBorrowed,
          },
        ]);
      }

      poolEntries.push([
        poolId,
        {
          capacity: policyPool.capacity,
          reservedPerTask: policyPool.reservedPerTask,
          shared: policyPool.shared,
          diagnosticOnly: policyPool.diagnosticOnly,
          queued: this.#queues.get(poolId).length,
          running: this.#runningCount(poolId),
          reservedRunning,
          borrowed,
          tasks: Object.fromEntries(taskEntries),
        },
      ]);
    }

    return {
      queued: this.#queuedCount,
      running: this.#runningById.size,
      activeTasks: [...this.#taskJobs.keys()].sort(compareStrings),
      pools: Object.fromEntries(poolEntries),
    };
  }

  #addTaskToRotation(poolId, taskId) {
    const rotation = this.#rotation.get(poolId);
    if (!rotation.order.includes(taskId)) rotation.order.push(taskId);
  }

  #assertMutationAllowed() {
    if (!this.#eligibilityCallbackActive) return;
    this.#reentrantMutationAttempted = true;
    throw schedulerError("REENTRANT_MUTATION");
  }

  #evaluateEligibility(job, isEligible) {
    this.#eligibilityCallbackActive = true;
    this.#reentrantMutationAttempted = false;
    try {
      const eligible = isEligible(copyJob(job)) === true;
      if (this.#reentrantMutationAttempted) {
        throw schedulerError("REENTRANT_MUTATION");
      }
      return eligible;
    } finally {
      this.#eligibilityCallbackActive = false;
      this.#reentrantMutationAttempted = false;
    }
  }

  #bestQueuedIndex(queue, predicate) {
    let bestIndex = -1;
    for (let index = 0; index < queue.length; index += 1) {
      if (!predicate(queue[index])) continue;
      if (bestIndex === -1 || compareJobs(queue[index], queue[bestIndex]) < 0) {
        bestIndex = index;
      }
    }
    return bestIndex;
  }

  #orderedQueuedIndexes(poolId, queue, predicate, pool) {
    const state = this.#poolAging.get(poolId);
    const threshold = starvationThreshold(this.#policy, pool);
    const indexes = [];
    for (let index = 0; index < queue.length; index += 1) {
      if (predicate(queue[index])) indexes.push(index);
    }
    indexes.sort((leftIndex, rightIndex) => {
      const leftMetadata = this.#agingByJobId.get(queue[leftIndex].jobId);
      const rightMetadata = this.#agingByJobId.get(queue[rightIndex].jobId);
      const leftStarved =
        leftMetadata !== undefined && isStarved(leftMetadata, state, threshold);
      const rightStarved =
        rightMetadata !== undefined && isStarved(rightMetadata, state, threshold);
      if (leftStarved !== rightStarved) return leftStarved ? -1 : 1;
      if (leftStarved && rightStarved) {
        const aged = compareAging(leftMetadata, rightMetadata);
        if (aged !== 0) return aged;
      }
      return compareJobs(queue[leftIndex], queue[rightIndex]);
    });
    return indexes;
  }

  #oldestStarvedIndex(poolId, queue, pool) {
    const state = this.#poolAging.get(poolId);
    const threshold = starvationThreshold(this.#policy, pool);
    let bestIndex = -1;
    for (let index = 0; index < queue.length; index += 1) {
      const metadata = this.#agingByJobId.get(queue[index].jobId);
      if (metadata === undefined || !isStarved(metadata, state, threshold)) continue;
      if (
        bestIndex === -1 ||
        compareAging(
          metadata,
          this.#agingByJobId.get(queue[bestIndex].jobId),
        ) < 0
      ) {
        bestIndex = index;
      }
    }
    return bestIndex;
  }

  #decrementMapCount(counts, key) {
    const next = (counts.get(key) ?? 0) - 1;
    if (next <= 0) {
      counts.delete(key);
    } else {
      counts.set(key, next);
    }
  }

  #decrementTaskJobs(taskId) {
    this.#decrementMapCount(this.#taskJobs, taskId);
  }

  #pruneRotation(poolId) {
    const rotation = this.#rotation.get(poolId);
    if (rotation.order.length === 0) return;
    const oldOrder = rotation.order;
    const nextCandidates = [
      ...oldOrder.slice(rotation.cursor),
      ...oldOrder.slice(0, rotation.cursor),
    ];
    const activeInPool = new Set(this.#queues.get(poolId).map((job) => job.taskId));
    for (const job of this.#runningById.values()) {
      if (job.poolId === poolId) activeInPool.add(job.taskId);
    }
    rotation.order = oldOrder.filter((taskId) => activeInPool.has(taskId));
    if (rotation.order.length === 0) {
      rotation.cursor = 0;
      return;
    }
    const nextTaskId = nextCandidates.find((taskId) => activeInPool.has(taskId));
    rotation.cursor = Math.max(0, rotation.order.indexOf(nextTaskId));
  }

  #pruneDeferred(poolId) {
    const activeQueued = new Set(
      this.#queues.get(poolId).map((job) => job.taskId),
    );
    const seen = new Set();
    this.#deferredTasks.set(
      poolId,
      this.#deferredTasks
        .get(poolId)
        .filter((taskId) => {
          if (!activeQueued.has(taskId) || seen.has(taskId)) return false;
          seen.add(taskId);
          return true;
        }),
    );
  }

  #runningCount(poolId, taskId = undefined) {
    let count = 0;
    for (const job of this.#runningById.values()) {
      if (job.poolId === poolId && (taskId === undefined || job.taskId === taskId)) {
        count += 1;
      }
    }
    return count;
  }
}
