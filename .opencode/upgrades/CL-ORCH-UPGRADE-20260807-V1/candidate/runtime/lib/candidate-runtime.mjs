import { createHash } from "node:crypto";

import {
  resolveCapacityPolicy,
  validateCapacityPolicy,
  WeightedFairScheduler,
} from "./capacity-policy.mjs";
import {
  propagateBlocked,
  readyNodes,
  validateBatchDag,
} from "./batch-dag.mjs";
import {
  executeAttempt,
  validateAttemptResultPacket,
} from "./execution-kernel.mjs";

export const CANDIDATE_RUNTIME_MODE = "PRODUCTION";
export const CANDIDATE_DURABLE_ACCOUNTING_MODE = "DURABLE_TRANSMISSION";

function runtimeError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function requireSafeInteger(value, name, minimum = 0) {
  if (!Number.isSafeInteger(value) || value < minimum) {
    throw new TypeError(`${name} must be a bounded safe integer`);
  }
  return value;
}

function requireText(value, name) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TypeError(`${name} must be a nonblank string`);
  }
  return value;
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function attemptIdentity(lease, fence) {
  return Object.freeze({
    jobId: lease.jobId,
    generation: lease.generation,
    attemptId: lease.attemptId,
    workerId: lease.workerId,
    epoch: lease.epoch,
    fence,
  });
}

function exactLease(identity) {
  return {
    jobId: identity.jobId,
    generation: identity.generation,
    attemptId: identity.attemptId,
    workerId: identity.workerId,
    epoch: identity.epoch,
  };
}

function isDeterministicContractError(error) {
  return (
    error?.deterministic === true &&
    ["HTTP_400", "HTTP_422", "CONTRACT_400", "CONTRACT_422"].includes(error?.code)
  );
}

function isAccountingUncertain(error) {
  return error?.code === "ACCOUNTING_UNCERTAIN" && error?.accountingUncertain === true;
}

function isCandidateCancellation(error) {
  return error?.code === "CANDIDATE_ATTEMPT_CANCELLED";
}

function isCommittedCancellationRace(store, dispatch, originalError, terminalizationError) {
  if (
    !isCandidateCancellation(originalError) ||
    terminalizationError?.code !== "STALE_ATTEMPT_LEASE"
  ) {
    return false;
  }
  try {
    return store.getGeneration(dispatch.jobId, dispatch.generation).state === "CANCELED";
  } catch {
    return false;
  }
}

export function candidatePublicResultPacket(attemptPacket) {
  const result = attemptPacket?.outcome?.result;
  const source =
    result !== null &&
    typeof result === "object" &&
    !Array.isArray(result) &&
    result.handoff !== null &&
    typeof result.handoff === "object" &&
    !Array.isArray(result.handoff)
      ? result.handoff
      : result;
  const requestedStatus =
    typeof source?.status === "string" ? source.status.toUpperCase() : "FAIL";
  const status = ["PASS", "CACHED", "FAIL", "BLOCKED"].includes(requestedStatus)
    ? requestedStatus
    : "FAIL";
  const accepted = status === "PASS" || status === "CACHED";
  const requestedExecutionStatus =
    typeof source?.execution_status === "string"
      ? source.execution_status.toUpperCase()
      : null;
  const executionStatus = accepted
    ? "ACCEPTED"
    : status === "BLOCKED"
      ? requestedExecutionStatus === "CANCELLED"
        ? "CANCELLED"
        : "BLOCKED"
      : ["INCOMPLETE", "PROVIDER_ERROR", "CONTRACT_ERROR"].includes(
            requestedExecutionStatus,
          )
        ? requestedExecutionStatus
        : "INCOMPLETE";
  const requestedEvidenceVerdict =
    typeof source?.evidence_verdict === "string"
      ? source.evidence_verdict.toUpperCase()
      : null;
  const evidenceVerdict = accepted &&
      ["POSITIVE", "NEGATIVE", "NULL", "MIXED", "NOT_APPLICABLE"].includes(
        requestedEvidenceVerdict,
      )
    ? requestedEvidenceVerdict
    : accepted
      ? "NOT_APPLICABLE"
      : "UNRESOLVED";
  const textArray = (value) => {
    if (!Array.isArray(value)) return [];
    return value.map((item) => {
      if (typeof item === "string") return item;
      if (
        item !== null &&
        typeof item === "object" &&
        !Array.isArray(item) &&
        typeof item.text === "string"
      ) {
        return item.text;
      }
      throw new TypeError("candidate public finding must be text or typed text");
    });
  };
  return {
    schema_version: 1,
    result_protocol: 3,
    status,
    execution_status: executionStatus,
    evidence_verdict: evidenceVerdict,
    cache_hit: status === "CACHED",
    summary:
      typeof source?.summary === "string"
        ? source.summary
        : "Candidate attempt completed.",
    positive_findings: textArray(source?.positive_findings),
    negative_findings: textArray(source?.negative_findings),
    residual_risks: textArray(source?.residual_risks),
    recommended_next_action:
      typeof source?.recommended_next_action === "string"
        ? source.recommended_next_action
        : "Return the validated result to the authenticated caller.",
    scientific_uncertainty: source?.scientific_uncertainty === true,
    architecture_uncertainty: source?.architecture_uncertainty === true,
    scope_deviation: source?.scope_deviation === true,
  };
}

function verifiedLocalExactWriteRebindOutputs(dispatch, result, writerAdmission) {
  const input = dispatch?.payload?.input;
  const constraints = input?.route_constraints;
  const verification = Array.isArray(input?.write_verifications) &&
      input.write_verifications.length === 1
    ? input.write_verifications[0]
    : null;
  const source =
    result !== null &&
    typeof result === "object" &&
    !Array.isArray(result) &&
    result.handoff !== null &&
    typeof result.handoff === "object" &&
    !Array.isArray(result.handoff)
      ? result.handoff
      : result;
  if (
    dispatch?.role !== "WRITER" ||
    dispatch?.payload?.mode !== "WRITE" ||
    source?.status !== "PASS" ||
    source?.execution_status !== "ACCEPTED" ||
    !Array.isArray(constraints?.allowed_routes) ||
    constraints.allowed_routes.length !== 1 ||
    constraints.allowed_routes[0] !== "LOCAL" ||
    constraints.fallback_policy !== "NO_LUNA" ||
    constraints.privacy_class !== "LOCAL_ONLY" ||
    !Array.isArray(input?.commands_tests) ||
    input.commands_tests.length !== 0 ||
    verification === null ||
    typeof verification.sha256 !== "string" ||
    !/^[a-f0-9]{64}$/.test(verification.sha256) ||
    !Number.isSafeInteger(verification.byte_length) ||
    verification.byte_length < 0 ||
    !Array.isArray(writerAdmission?.canonicalOutputPaths) ||
    writerAdmission.canonicalOutputPaths.length !== 1
  ) {
    return null;
  }
  return Object.freeze([Object.freeze({
    path: writerAdmission.canonicalOutputPaths[0],
    sha256: verification.sha256,
    byteLength: verification.byte_length,
  })]);
}

function candidateTerminalFailurePacket({
  status = "FAIL",
  executionStatus = "CONTRACT_ERROR",
} = {}) {
  const blocked = status === "BLOCKED";
  return Object.freeze({
    schema_version: 1,
    result_protocol: 3,
    status: blocked ? "BLOCKED" : "FAIL",
    execution_status: blocked
      ? executionStatus === "CANCELLED"
        ? "CANCELLED"
        : "BLOCKED"
      : "CONTRACT_ERROR",
    evidence_verdict: "UNRESOLVED",
    cache_hit: false,
    summary: blocked
      ? "The bounded candidate worker was blocked before publishing an accepted result."
      : "The bounded candidate worker failed before publishing an accepted result.",
    positive_findings: Object.freeze([]),
    negative_findings: Object.freeze([
      "No accepted result was produced.",
    ]),
    residual_risks: Object.freeze([
      "Review the owning task's local diagnostics before resubmission.",
    ]),
    recommended_next_action:
      "Return the bounded failure packet to the authenticated owning task.",
    scientific_uncertainty: false,
    architecture_uncertainty: false,
    scope_deviation: false,
  });
}

function captureRuntimeOptions(options) {
  if (
    options === null ||
    typeof options !== "object" ||
    Array.isArray(options) ||
    Object.getPrototypeOf(options) !== Object.prototype
  ) {
    throw new TypeError("invalid candidate runtime options");
  }
  const descriptors = Object.getOwnPropertyDescriptors(options);
  const common = [
    "mode",
    "store",
    "runner",
    "now",
    "leaseMs",
  ];
  const commonWithCapacity = [...common, "capacityPolicy"];
  const legacy = [
    ...common,
    "projectCeilingNanoUsd",
    "pricingVersion",
  ];
  const legacyWithCapacity = [
    ...commonWithCapacity,
    "projectCeilingNanoUsd",
    "pricingVersion",
  ];
  const durable = [
    ...common,
    "accountingMode",
    "projectId",
    "budgetControllerFactory",
  ];
  const durableWithCapacity = [
    ...commonWithCapacity,
    "accountingMode",
    "projectId",
    "budgetControllerFactory",
  ];
  const ownKeys = Reflect.ownKeys(descriptors);
  const selected =
    ownKeys.length === legacy.length &&
    ownKeys.every((key) => typeof key === "string" && legacy.includes(key))
      ? legacy
      : ownKeys.length === legacyWithCapacity.length &&
          ownKeys.every(
            (key) => typeof key === "string" && legacyWithCapacity.includes(key),
          )
        ? legacyWithCapacity
      : ownKeys.length === durable.length &&
          ownKeys.every((key) => typeof key === "string" && durable.includes(key))
        ? durable
        : ownKeys.length === durableWithCapacity.length &&
            ownKeys.every(
              (key) => typeof key === "string" && durableWithCapacity.includes(key),
            )
          ? durableWithCapacity
        : null;
  if (
    selected === null ||
    selected.some(
      (key) =>
        descriptors[key] === undefined ||
        descriptors[key].enumerable !== true ||
        !Object.hasOwn(descriptors[key], "value"),
    )
  ) {
    throw new TypeError("invalid candidate runtime options");
  }
  return Object.freeze({
    accountingMode:
      selected === durable || selected === durableWithCapacity
        ? descriptors.accountingMode.value
        : "LEGACY_ATTEMPT",
    capacityPolicy:
      descriptors.capacityPolicy?.value ?? resolveCapacityPolicy(),
    ...Object.fromEntries(
      selected.map((key) => [key, descriptors[key].value]),
    ),
  });
}

function requireDurableBudgetController(value) {
  if (
    value === null ||
    typeof value !== "object" ||
    value.isDurableTransmissionController !== true ||
    value.cumulativeBudgetSafe !== true ||
    typeof value.reserveNextCall !== "function" ||
    typeof value.reconcile !== "function" ||
    typeof value.snapshot !== "function"
  ) {
    throw runtimeError(
      "CANDIDATE_BUDGET_CONTROLLER_UNSAFE",
      "candidate runtime requires a durable cumulative budget controller",
    );
  }
  return value;
}

export class CandidateProjectRuntime {
  #store;
  #runner;
  #now;
  #leaseMs;
  #projectCeilingNanoUsd;
  #pricingVersion;
  #accountingMode;
  #projectId;
  #budgetControllerFactory;
  #scheduler;
  #tracked = new Map();
  #active = new Map();
  #activeControllers = new Map();
  #outcomes = new Map();
  #workerSequence = 0;

  constructor(options) {
    const captured = captureRuntimeOptions(options);
    if (captured.mode !== CANDIDATE_RUNTIME_MODE) {
      throw runtimeError(
        "CANDIDATE_RUNTIME_INACTIVE",
        "candidate runtime mode is inactive",
      );
    }
    const durableAccounting =
      captured.accountingMode === CANDIDATE_DURABLE_ACCOUNTING_MODE;
    if (
      captured.store === null ||
      typeof captured.store !== "object" ||
      typeof captured.store.listQueuedGenerations !== "function" ||
      typeof captured.store.leaseGeneration !== "function" ||
      typeof captured.store.getGeneration !== "function" ||
      (durableAccounting
        ? typeof captured.store.recoverUncertainProviderTransmissions !== "function" ||
          typeof captured.store.acceptAndPublishCandidateWorkerResult !== "function"
        : typeof captured.store.reserveCost !== "function")
    ) {
      throw new TypeError("candidate runtime store is invalid");
    }
    if (typeof captured.runner !== "function" || typeof captured.now !== "function") {
      throw new TypeError("candidate runtime dependencies are invalid");
    }
    this.#store = captured.store;
    this.#runner = captured.runner;
    this.#now = captured.now;
    this.#leaseMs = requireSafeInteger(captured.leaseMs, "leaseMs", 1);
    this.#accountingMode = captured.accountingMode;
    if (!validateCapacityPolicy(captured.capacityPolicy)) {
      throw new TypeError("candidate runtime capacity policy is invalid");
    }
    if (durableAccounting) {
      this.#projectId = requireText(captured.projectId, "projectId");
      if (typeof captured.budgetControllerFactory !== "function") {
        throw new TypeError("budgetControllerFactory must be a function");
      }
      this.#budgetControllerFactory = captured.budgetControllerFactory;
      try {
        this.#store.recoverUncertainProviderTransmissions({
          projectId: this.#projectId,
        });
      } catch (error) {
        if (error?.code !== "PROVIDER_ACCOUNTING_NOT_CONFIGURED") throw error;
      }
    } else {
      this.#projectCeilingNanoUsd = requireSafeInteger(
        captured.projectCeilingNanoUsd,
        "projectCeilingNanoUsd",
      );
      this.#pricingVersion = requireText(captured.pricingVersion, "pricingVersion");
    }
    this.#scheduler = new WeightedFairScheduler(captured.capacityPolicy);
  }

  refresh() {
    for (const generation of this.#store.listQueuedGenerations()) {
      const schedulerJobId = `${generation.jobId}:${generation.generation}`;
      if (this.#tracked.has(schedulerJobId) || this.#active.has(schedulerJobId)) continue;
      this.#scheduler.enqueue({
        jobId: schedulerJobId,
        taskId: generation.taskId,
        poolId: generation.poolId,
        priority: generation.priority,
        createdAtMs: generation.createdAtMs,
        role: generation.role,
      });
      this.#tracked.set(schedulerJobId, {
        jobId: generation.jobId,
        generation: generation.generation,
      });
    }
  }

  recoverExpired() {
    const recovered = this.#store.recoverExpiredLeases();
    this.refresh();
    return Object.freeze(recovered.map((entry) => Object.freeze({ ...entry })));
  }

  abortCancelled() {
    const aborted = [];
    for (const [schedulerJobId, active] of this.#activeControllers) {
      if (active.controller.signal.aborted) continue;
      const generation = this.#store.getGeneration(
        active.jobId,
        active.generation,
      );
      if (generation.state !== "CANCELED") continue;
      active.controller.abort(
        runtimeError(
          "CANDIDATE_ATTEMPT_CANCELLED",
          "candidate attempt was durably cancelled",
        ),
      );
      aborted.push(schedulerJobId);
    }
    return Object.freeze(aborted.sort());
  }

  dispatchQueued() {
    this.refresh();
    this.#dispatchAvailable("deepluna-read");
    this.#dispatchAvailable("deepluna-write");
    return this.#active.size;
  }

  async runUntilIdle() {
    while (true) {
      this.dispatchQueued();
      if (this.#active.size === 0) {
        if (this.#store.listQueuedGenerations().length === 0) break;
        throw runtimeError(
          "CANDIDATE_RUNTIME_STALLED",
          "candidate runtime cannot dispatch queued work",
        );
      }
      await Promise.race([...this.#active.values()]);
    }
    await Promise.all([...this.#active.values()]);
    return Object.freeze(
      [...this.#outcomes.entries()]
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, value]) => Object.freeze({ key, ...value })),
    );
  }

  async runBatch({ dag, executeNode }) {
    if (typeof executeNode !== "function") {
      throw new TypeError("executeNode must be a function");
    }
    const nodes = validateBatchDag(dag);
    let statuses = Object.create(null);
    while (Object.keys(statuses).length < nodes.length) {
      statuses = { ...propagateBlocked(nodes, statuses) };
      const ready = readyNodes(nodes, statuses);
      if (ready.length === 0) {
        if (Object.keys(statuses).length === nodes.length) break;
        throw runtimeError("CANDIDATE_BATCH_STALLED", "candidate batch cannot make progress");
      }
      const completed = await Promise.all(
        ready.map(async (nodeId) => {
          const status = await executeNode(nodeId);
          if (!["PASS", "CACHED", "FAIL", "BLOCKED", "INCOMPLETE"].includes(status)) {
            throw new TypeError("candidate batch node returned an invalid status");
          }
          return [nodeId, status];
        }),
      );
      for (const [nodeId, status] of completed) statuses[nodeId] = status;
    }
    return Object.freeze(
      Object.fromEntries(
        Object.entries(statuses).sort(([left], [right]) => left.localeCompare(right)),
      ),
    );
  }

  #dispatchAvailable(poolId) {
    while (true) {
      const scheduled = this.#scheduler.dispatchNext(poolId);
      if (scheduled === null) return;
      const storeIdentity = this.#tracked.get(scheduled.jobId);
      if (storeIdentity === undefined) {
        this.#scheduler.release(scheduled.jobId);
        throw runtimeError(
          "CANDIDATE_RUNTIME_CORRUPT",
          "scheduled work has no durable identity",
        );
      }
      const controller = new AbortController();
      this.#activeControllers.set(scheduled.jobId, {
        controller,
        jobId: storeIdentity.jobId,
        generation: storeIdentity.generation,
      });
      const promise = this.#runGeneration(
        scheduled.jobId,
        storeIdentity,
        controller.signal,
      )
        .catch((error) => {
          this.#outcomes.set(scheduled.jobId, {
            code: error?.code ?? "RUNTIME_ERROR",
            status: "FAIL",
          });
        })
        .finally(() => {
          this.#scheduler.release(scheduled.jobId);
          this.#active.delete(scheduled.jobId);
          this.#activeControllers.delete(scheduled.jobId);
          this.#tracked.delete(scheduled.jobId);
        });
      this.#active.set(scheduled.jobId, promise);
    }
  }

  async #runGeneration(schedulerJobId, storeIdentity, signal) {
    const dispatch = this.#store.getDispatchGeneration(
      storeIdentity.jobId,
      storeIdentity.generation,
    );
    if (dispatch === null || dispatch.state !== "QUEUED") {
      throw runtimeError("STALE_GENERATION", "queued generation is no longer dispatchable");
    }
    this.#workerSequence += 1;
    const workerId = `candidate-worker-${this.#workerSequence}`;
    const lease = this.#store.leaseGeneration({
      jobId: dispatch.jobId,
      generation: dispatch.generation,
      workerId,
      leaseMs: this.#leaseMs,
    });
    if (lease === null) {
      throw runtimeError(
        "STALE_GENERATION",
        "queued generation was leased by another runtime",
      );
    }
    let writerAdmission = null;
    let estimatedNanoUsd = 0;
    let reservationId = null;
    let reservationOpened = false;
    let reservationTerminal = false;
    let reconcileReservation = null;
    let budgetController = null;
    try {
      if (dispatch.role === "WRITER") {
        const scope = dispatch.payload?.writerScope;
        if (
          scope === null ||
          typeof scope !== "object" ||
          !Array.isArray(scope.outputPaths)
        ) {
          throw runtimeError("INVALID_WRITER_SCOPE", "writer scope is required");
        }
        writerAdmission = this.#store.acquireCandidateWriterAdmission({
          originId: dispatch.originId,
          projectId: dispatch.projectId,
          jobId: dispatch.jobId,
          generation: dispatch.generation,
          leaseEpoch: lease.epoch,
          worktreeRoot: scope.worktreeRoot,
          outputPaths: scope.outputPaths,
        });
      }
      const fence = writerAdmission?.fencingToken ?? lease.epoch;
      const kernelLease = attemptIdentity(lease, fence);
      const nowMs = () => requireSafeInteger(this.#now(), "nowMs");
      let attemptBudget;
      let attemptRunner = this.#runner;
      if (this.#accountingMode === CANDIDATE_DURABLE_ACCOUNTING_MODE) {
        if (dispatch.projectId !== this.#projectId) {
          throw runtimeError(
            "PROJECT_MISMATCH",
            "queued work does not match the candidate runtime project",
          );
        }
        budgetController = requireDurableBudgetController(
          this.#budgetControllerFactory(
            Object.freeze({
              store: this.#store,
              projectId: dispatch.projectId,
              originId: dispatch.originId,
              jobId: dispatch.jobId,
              generation: dispatch.generation,
              attemptId: lease.attemptId,
            }),
          ),
        );
        const accountingSnapshot = (status) => {
          let snapshot;
          try {
            snapshot = budgetController.snapshot(dispatch.jobId);
          } catch (error) {
            if (error?.code !== "PROVIDER_ACCOUNTING_NOT_CONFIGURED") throw error;
            snapshot = {
              activeCount: 0,
              reconciledCount: 0,
              releasedCount: 0,
              transmissionCount: 0,
              unknownCount: 0,
            };
          }
          const uncertain =
            status === "UNKNOWN" ||
            snapshot.activeCount > 0 ||
            snapshot.unknownCount > 0;
          return Object.freeze({
            status: uncertain ? "UNKNOWN" : "ACTUAL",
            activeCount: snapshot.activeCount,
            reconciledCount: snapshot.reconciledCount,
            releasedCount: snapshot.releasedCount,
            transmissionCount: snapshot.transmissionCount,
            unknownCount: snapshot.unknownCount,
          });
        };
        attemptBudget = {
          reserve: async () => Object.freeze({
            accountingMode: CANDIDATE_DURABLE_ACCOUNTING_MODE,
            attemptId: lease.attemptId,
            jobId: dispatch.jobId,
          }),
          reconcile: async () => accountingSnapshot("ACTUAL"),
          preserveUnknown: async () => accountingSnapshot("UNKNOWN"),
        };
        attemptRunner = (input) =>
          this.#runner(
            Object.freeze({
              ...input,
              budgetController,
            }),
          );
      } else {
        estimatedNanoUsd = requireSafeInteger(
          dispatch.payload?.estimatedNanoUsd ?? 0,
          "estimatedNanoUsd",
        );
        reservationId = `candidate-${sha256(
          `${dispatch.jobId}\0${dispatch.generation}\0${lease.attemptId}`,
        )}`;
        reconcileReservation = (outcome, actualNanoUsd) => {
          const reconciled = this.#store.reconcileCost({
            reservationId,
            projectId: dispatch.projectId,
            originId: dispatch.originId,
            actualNanoUsd,
            outcome,
            nowMs: nowMs(),
          });
          if (["RECONCILED", "RELEASED"].includes(reconciled.state)) {
            reservationTerminal = true;
          }
          return reconciled;
        };
        attemptBudget = {
          reserve: async () => {
            const reservation = this.#store.reserveCost({
              reservationId,
              projectId: dispatch.projectId,
              originId: dispatch.originId,
              jobId: dispatch.jobId,
              attemptId: lease.attemptId,
              ceilingNanoUsd: this.#projectCeilingNanoUsd,
              estimatedNanoUsd,
              pricingVersion: this.#pricingVersion,
              nowMs: nowMs(),
            });
            reservationOpened = true;
            return reservation;
          },
          reconcile: async ({ usage }) => {
            const actualNanoUsd = requireSafeInteger(
              usage?.actualNanoUsd ?? estimatedNanoUsd,
              "actualNanoUsd",
            );
            const reservation = reconcileReservation("RECONCILED", actualNanoUsd);
            return {
              status: "ACTUAL",
              actualNanoUsd: reservation.actualNanoUsd,
            };
          },
          preserveUnknown: async () => {
            reconcileReservation("UNKNOWN", null);
            return { code: "ACCOUNTING_UNCERTAIN", status: "UNKNOWN" };
          },
        };
      }
      const assertCurrent = async ({ phase, result }) => {
        if (
          !this.#store.heartbeat({
            ...exactLease(kernelLease),
            leaseMs: this.#leaseMs,
          })
        ) {
          throw runtimeError("STALE_ATTEMPT_LEASE", "attempt lease is stale");
        }
        if (writerAdmission !== null) {
          const writerFenceRequest = {
            originId: dispatch.originId,
            projectId: dispatch.projectId,
            jobId: dispatch.jobId,
            generation: dispatch.generation,
            leaseEpoch: lease.epoch,
            fencingToken: writerAdmission.fencingToken,
          };
          try {
            this.#store.assertCandidateWriterFence(writerFenceRequest);
          } catch (error) {
            const outputs = phase === "BEFORE_PUBLISH" &&
                error?.code === "STALE_WRITER_FENCE"
              ? verifiedLocalExactWriteRebindOutputs(
                  dispatch,
                  result,
                  writerAdmission,
                )
              : null;
            if (
              outputs === null ||
              typeof this.#store.rebindCandidateWriterOutputs !== "function"
            ) {
              throw error;
            }
            this.#store.rebindCandidateWriterOutputs({
              ...writerFenceRequest,
              outputs,
            });
            this.#store.assertCandidateWriterFence(writerFenceRequest);
          }
        }
        if (
          phase === "BEFORE_PUBLISH" &&
          !this.#store.beginValidation(exactLease(kernelLease))
        ) {
          throw runtimeError("STALE_ATTEMPT_LEASE", "attempt cannot enter validation");
        }
        return kernelLease;
      };
      const heartbeatPeriodMs = Math.max(1, Math.floor(this.#leaseMs / 3));
      const heartbeatTimer = setInterval(() => {
        try {
          this.#store.heartbeat({
            ...exactLease(kernelLease),
            leaseMs: this.#leaseMs,
          });
        } catch {
          // The publish-time assertion remains the fail-closed authority.
        }
      }, heartbeatPeriodMs);
      heartbeatTimer.unref?.();
      let packet;
      try {
        packet = await executeAttempt({
          contract: {
            jobId: dispatch.jobId,
            generation: dispatch.generation,
            projectId: dispatch.projectId,
            role: dispatch.role,
            payload: dispatch.payload,
          },
          lease: { assertCurrent },
          runner: attemptRunner,
          budget: attemptBudget,
          validator: validateAttemptResultPacket,
          artifactStore: {
            publish: async ({ packet: acceptedPacket }) => {
              const resultHash = sha256(JSON.stringify(acceptedPacket));
              if (this.#accountingMode === CANDIDATE_DURABLE_ACCOUNTING_MODE) {
                this.#store.acceptAndPublishCandidateWorkerResult({
                  originId: dispatch.originId,
                  projectId: dispatch.projectId,
                  ...exactLease(kernelLease),
                  resultHash,
                  inputFingerprint: dispatch.inputFingerprint,
                  packet: candidatePublicResultPacket(acceptedPacket),
                  ...(writerAdmission === null
                    ? {}
                    : { writerFencingToken: writerAdmission.fencingToken }),
                });
              } else {
                const accepted = this.#store.acceptCandidateResult({
                  originId: dispatch.originId,
                  projectId: dispatch.projectId,
                  ...exactLease(kernelLease),
                  resultHash,
                  inputFingerprint: dispatch.inputFingerprint,
                  ...(writerAdmission === null
                    ? {}
                    : { writerFencingToken: writerAdmission.fencingToken }),
                });
                if (accepted.accepted !== true) {
                  throw runtimeError(
                    "STALE_ATTEMPT_LEASE",
                    "result acceptance was fenced",
                  );
                }
              }
            },
          },
          signal,
        });
      } finally {
        clearInterval(heartbeatTimer);
      }
      if (packet.authoritative !== true) {
        if (this.#accountingMode === CANDIDATE_DURABLE_ACCOUNTING_MODE) {
          this.#store.quarantineAndPublishCandidateWorkerFailure({
            originId: dispatch.originId,
            projectId: dispatch.projectId,
            ...lease,
            failureClass: "ACCOUNTING_UNCERTAIN",
            packet: candidateTerminalFailurePacket({ status: "BLOCKED" }),
          });
        } else {
          this.#store.quarantineAttempt({
            ...lease,
            failureClass: "ACCOUNTING_UNCERTAIN",
          });
        }
        this.#outcomes.set(schedulerJobId, {
          code: "ACCOUNTING_UNCERTAIN",
          status: "BLOCKED",
        });
      } else {
        this.#outcomes.set(schedulerJobId, {
          code: "ACCEPTED",
          status: "PASS",
        });
      }
    } catch (error) {
      let reconciliationFailure = null;
      const failureClass = isDeterministicContractError(error)
        ? "DETERMINISTIC_CONTRACT_ERROR"
        : error?.code ?? "RUNTIME_ERROR";
      try {
        if (
          reservationOpened &&
          !reservationTerminal &&
          reconcileReservation !== null
        ) {
          if (isDeterministicContractError(error)) {
            reconcileReservation(
              "RECONCILED",
              Number.isSafeInteger(error?.actualNanoUsd) && error.actualNanoUsd >= 0
                ? error.actualNanoUsd
                : estimatedNanoUsd,
            );
          } else if (isAccountingUncertain(error) || error?.transmitted === true) {
            reconcileReservation("UNKNOWN", null);
          } else {
            reconcileReservation("RELEASED", 0);
          }
        }
      } catch (caught) {
        reconciliationFailure = caught;
      } finally {
        if (this.#accountingMode === CANDIDATE_DURABLE_ACCOUNTING_MODE) {
          const blocked =
            isCandidateCancellation(error) || isAccountingUncertain(error);
          try {
            this.#store.quarantineAndPublishCandidateWorkerFailure({
              originId: dispatch.originId,
              projectId: dispatch.projectId,
              ...lease,
              failureClass,
              packet: candidateTerminalFailurePacket({
                status: blocked ? "BLOCKED" : "FAIL",
                executionStatus: isCandidateCancellation(error)
                  ? "CANCELLED"
                  : blocked
                    ? "BLOCKED"
                    : "CONTRACT_ERROR",
              }),
            });
          } catch (terminalizationError) {
            if (
              !isCommittedCancellationRace(
                this.#store,
                dispatch,
                error,
                terminalizationError,
              )
            ) {
              throw terminalizationError;
            }
          }
        } else {
          this.#store.quarantineAttempt({
            ...lease,
            failureClass,
          });
        }
      }
      this.#outcomes.set(schedulerJobId, {
        code:
          reconciliationFailure?.code ??
          error?.code ??
          "RUNTIME_ERROR",
        status:
          isDeterministicContractError(error) || isCandidateCancellation(error)
            ? "BLOCKED"
            : "FAIL",
      });
    }
  }
}

export function createCandidateProjectRuntime(options) {
  return new CandidateProjectRuntime(options);
}
