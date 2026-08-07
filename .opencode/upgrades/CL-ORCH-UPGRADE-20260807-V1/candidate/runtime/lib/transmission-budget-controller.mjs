import { createHash } from "node:crypto";

// Durable ordinal stride; retain six for compatibility with already persisted jobs.
// New submissions are capped at five by result-protocol and server validation.
const MAX_PROVIDER_CALLS = 6;
const MAX_SAFE_BIGINT = BigInt(Number.MAX_SAFE_INTEGER);

function controllerError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function requireDataObject(value, label) {
  if (
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new TypeError(`${label} must be a plain object`);
  }
  return value;
}

function captureOwnFields(value, fields, label) {
  requireDataObject(value, label);
  const captured = {};
  for (const field of fields) {
    const descriptor = Object.getOwnPropertyDescriptor(value, field);
    if (
      descriptor === undefined ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError(`${label} has an invalid ${field}`);
    }
    captured[field] = descriptor.value;
  }
  return captured;
}

function captureOptionalOwnField(value, field, label) {
  requireDataObject(value, label);
  const descriptor = Object.getOwnPropertyDescriptor(value, field);
  if (descriptor === undefined) return undefined;
  if (
    descriptor.enumerable !== true ||
    !Object.hasOwn(descriptor, "value")
  ) {
    throw new TypeError(`${label} has an invalid ${field}`);
  }
  return descriptor.value;
}

function captureExactObject(value, fields, label) {
  const captured = captureOwnFields(value, fields, label);
  const descriptors = Object.getOwnPropertyDescriptors(value);
  if (
    Reflect.ownKeys(descriptors).length !== fields.length ||
    Reflect.ownKeys(descriptors).some(
      (key) => typeof key !== "string" || !fields.includes(key),
    )
  ) {
    throw new TypeError(`${label} has an invalid shape`);
  }
  return captured;
}

function requireSafeInteger(value, name, minimum = 0, maximum = Number.MAX_SAFE_INTEGER) {
  if (
    !Number.isSafeInteger(value) ||
    value < minimum ||
    value > maximum
  ) {
    throw new TypeError(`${name} must be a bounded safe integer`);
  }
  return value;
}

function requireText(value, name, maximumLength) {
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

function requireProjectId(value) {
  if (
    typeof value !== "string" ||
    value === "." ||
    value === ".." ||
    !/^[A-Za-z0-9._:-]{1,256}$/.test(value)
  ) {
    throw new TypeError("projectId must be an exact project identity");
  }
  return value;
}

function requireSha256(value, name) {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/.test(value)) {
    throw new TypeError(`${name} must be a lowercase SHA-256 value`);
  }
  return value;
}

function safeProduct(left, right, code, message) {
  const product = BigInt(left) * BigInt(right);
  if (product > MAX_SAFE_BIGINT) throw controllerError(code, message);
  return Number(product);
}

function safeSum(values, code, message) {
  const total = values.reduce((sum, value) => sum + BigInt(value), 0n);
  if (total > MAX_SAFE_BIGINT) throw controllerError(code, message);
  return Number(total);
}

function maximumCostUsdToNanoUsd(value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    throw new TypeError(
      "maximumEstimatedCostUsd must be a finite nonnegative number",
    );
  }
  const scaled = Math.floor(value * 1_000_000_000);
  return requireSafeInteger(scaled, "maximumEstimatedNanoUsd");
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function captureRates(value, label) {
  const rates = captureExactObject(
    value,
    ["cached_input", "uncached_input", "output"],
    label,
  );
  return Object.freeze({
    cached_input: requireSafeInteger(
      rates.cached_input,
      `${label}.cached_input`,
    ),
    uncached_input: requireSafeInteger(
      rates.uncached_input,
      `${label}.uncached_input`,
    ),
    output: requireSafeInteger(rates.output, `${label}.output`),
  });
}

function capturePricingCatalog(value) {
  requireDataObject(value, "pricingCatalog");
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const keys = Reflect.ownKeys(descriptors);
  if (keys.length < 1 || keys.length > 32) {
    throw new TypeError("pricingCatalog must contain one to thirty-two tuples");
  }
  const catalog = Object.create(null);
  for (const key of keys) {
    const descriptor = descriptors[key];
    if (
      typeof key !== "string" ||
      descriptor.enumerable !== true ||
      !Object.hasOwn(descriptor, "value")
    ) {
      throw new TypeError("pricingCatalog contains an invalid tuple");
    }
    const pricingVersion = requireText(key, "pricingVersion", 128);
    const tuple = captureExactObject(
      descriptor.value,
      [
        "route",
        "provider",
        "model",
        "serviceTier",
        "reasoningEffort",
        "rates",
      ],
      `pricingCatalog.${pricingVersion}`,
    );
    const route = requireText(tuple.route, "route", 32);
    const reasoningEffort = requireText(
      tuple.reasoningEffort,
      "reasoningEffort",
      32,
    );
    if (
      !/^[A-Z0-9_-]+$/.test(route) ||
      !/^[A-Za-z0-9_-]+$/.test(reasoningEffort)
    ) {
      throw new TypeError("pricingCatalog contains an invalid route identity");
    }
    catalog[pricingVersion] = Object.freeze({
      route,
      provider: requireText(tuple.provider, "provider", 128),
      model: requireText(tuple.model, "model", 256),
      serviceTier: requireText(tuple.serviceTier, "serviceTier", 64),
      reasoningEffort,
      rates: captureRates(tuple.rates, `pricingCatalog.${pricingVersion}.rates`),
    });
  }
  return Object.freeze(catalog);
}

function captureControllerOptions(options) {
  const captured = captureExactObject(
    options,
    [
      "store",
      "projectId",
      "originId",
      "projectCeilingNanoUsd",
      "costPolicyVersion",
      "pricingCatalog",
      "maximumInputTokensPerCall",
      "maximumOutputTokensPerCall",
    ],
    "durable transmission controller options",
  );
  const store = captured.store;
  if (
    store === null ||
    typeof store !== "object" ||
    typeof store.configureProviderAccounting !== "function" ||
    typeof store.reserveProviderTransmission !== "function" ||
    typeof store.reconcileProviderTransmission !== "function" ||
    typeof store.getProviderAccountingSnapshot !== "function"
  ) {
    throw new TypeError("durable transmission controller store is invalid");
  }
  return Object.freeze({
    store,
    projectId: requireProjectId(captured.projectId),
    originId: requireSafeInteger(captured.originId, "originId", 1),
    projectCeilingNanoUsd: requireSafeInteger(
      captured.projectCeilingNanoUsd,
      "projectCeilingNanoUsd",
    ),
    costPolicyVersion: requireText(
      captured.costPolicyVersion,
      "costPolicyVersion",
      128,
    ),
    pricingCatalog: capturePricingCatalog(captured.pricingCatalog),
    maximumInputTokensPerCall: requireSafeInteger(
      captured.maximumInputTokensPerCall,
      "maximumInputTokensPerCall",
      1,
    ),
    maximumOutputTokensPerCall: requireSafeInteger(
      captured.maximumOutputTokensPerCall,
      "maximumOutputTokensPerCall",
      1,
    ),
  });
}

function captureReserveRequest(request) {
  const captured = captureOwnFields(
    request,
    [
      "task",
      "projectId",
      "jobId",
      "attemptId",
      "turn",
      "requestIdentityHash",
      "maximumOutputTokens",
      "maximumInputTokens",
      "estimatedNanoUsd",
      "pricing",
      "costPolicyVersion",
    ],
    "provider call reservation request",
  );
  const task = requireDataObject(captured.task, "task");
  const attemptOrdinalDescriptor = Object.getOwnPropertyDescriptor(
    task,
    "attemptOrdinal",
  );
  const attemptOrdinal =
    attemptOrdinalDescriptor === undefined
      ? 1
      : attemptOrdinalDescriptor.enumerable === true &&
          Object.hasOwn(attemptOrdinalDescriptor, "value")
        ? requireSafeInteger(
            attemptOrdinalDescriptor.value,
            "attemptOrdinal",
            1,
          )
        : (() => {
            throw new TypeError("task has an invalid attemptOrdinal");
          })();
  const rawRouteConstraints = captureOwnFields(
    task,
    ["routeConstraints"],
    "task",
  ).routeConstraints;
  const routeConstraints = captureOwnFields(
    rawRouteConstraints,
    ["maximumProviderCalls", "maximumEstimatedCostUsd"],
    "task.routeConstraints",
  );
  const aggregateTokenFields = [
    "maximumInputTokens",
    "maximumCachedInputTokens",
    "maximumOutputTokensTotal",
    "maximumTotalTokens",
  ];
  const aggregateTokenValues = Object.fromEntries(
    aggregateTokenFields.map((field) => [
      field,
      captureOptionalOwnField(rawRouteConstraints, field, "task.routeConstraints"),
    ]),
  );
  const suppliedAggregateFields = aggregateTokenFields.filter(
    (field) => aggregateTokenValues[field] !== undefined,
  );
  if (
    suppliedAggregateFields.length !== 0 &&
    suppliedAggregateFields.length !== aggregateTokenFields.length
  ) {
    throw new TypeError(
      "task.routeConstraints aggregate token caps must be supplied together",
    );
  }
  const aggregateTokenLimits = suppliedAggregateFields.length === 0
    ? null
    : Object.freeze({
        maximumInputTokens: requireSafeInteger(
          aggregateTokenValues.maximumInputTokens,
          "maximumInputTokens",
          1,
        ),
        maximumCachedInputTokens: requireSafeInteger(
          aggregateTokenValues.maximumCachedInputTokens,
          "maximumCachedInputTokens",
          1,
        ),
        maximumOutputTokensTotal: requireSafeInteger(
          aggregateTokenValues.maximumOutputTokensTotal,
          "maximumOutputTokensTotal",
          1,
        ),
        maximumTotalTokens: requireSafeInteger(
          aggregateTokenValues.maximumTotalTokens,
          "maximumTotalTokens",
          1,
        ),
      });
  if (
    aggregateTokenLimits !== null &&
    aggregateTokenLimits.maximumCachedInputTokens >
      aggregateTokenLimits.maximumInputTokens
  ) {
    throw new TypeError(
      "maximumCachedInputTokens must not exceed maximumInputTokens",
    );
  }
  if (
    aggregateTokenLimits !== null &&
    BigInt(aggregateTokenLimits.maximumTotalTokens) <
      BigInt(aggregateTokenLimits.maximumInputTokens) +
        BigInt(aggregateTokenLimits.maximumOutputTokensTotal)
  ) {
    throw new TypeError(
      "maximumTotalTokens must cover aggregate input and output caps",
    );
  }
  const pricing = captureOwnFields(
    captured.pricing,
    [
      "model",
      "serviceTier",
      "reasoningEffort",
      "pricingVersion",
      "rates",
    ],
    "pricing",
  );
  return Object.freeze({
    projectId: requireProjectId(captured.projectId),
    jobId: requireText(captured.jobId, "jobId", 256),
    attemptId: requireText(captured.attemptId, "attemptId", 256),
    attemptOrdinal,
    turn: requireSafeInteger(captured.turn, "turn", 1, MAX_PROVIDER_CALLS),
    requestIdentityHash: requireSha256(
      captured.requestIdentityHash,
      "requestIdentityHash",
    ),
    maximumProviderCalls: requireSafeInteger(
      routeConstraints.maximumProviderCalls,
      "maximumProviderCalls",
      1,
      MAX_PROVIDER_CALLS,
    ),
    maximumEstimatedNanoUsd: maximumCostUsdToNanoUsd(
      routeConstraints.maximumEstimatedCostUsd,
    ),
    aggregateTokenLimits,
    maximumOutputTokens: requireSafeInteger(
      captured.maximumOutputTokens,
      "maximumOutputTokens",
      1,
    ),
    maximumInputTokens: requireSafeInteger(
      captured.maximumInputTokens,
      "maximumInputTokens",
    ),
    estimatedNanoUsd: requireSafeInteger(
      captured.estimatedNanoUsd,
      "estimatedNanoUsd",
    ),
    pricing: Object.freeze({
      model: requireText(pricing.model, "pricing.model", 256),
      serviceTier: requireText(
        pricing.serviceTier,
        "pricing.serviceTier",
        64,
      ),
      reasoningEffort: requireText(
        pricing.reasoningEffort,
        "pricing.reasoningEffort",
        32,
      ),
      pricingVersion: requireText(
        pricing.pricingVersion,
        "pricing.pricingVersion",
        128,
      ),
      rates: captureRates(pricing.rates, "pricing.rates"),
    }),
    costPolicyVersion: requireText(
      captured.costPolicyVersion,
      "costPolicyVersion",
      128,
    ),
  });
}

function captureReservation(value) {
  const captured = captureOwnFields(
    value,
    [
      "transmissionId",
      "projectId",
      "originId",
      "jobId",
      "pricingVersion",
    ],
    "provider transmission reservation",
  );
  return Object.freeze({
    transmissionId: requireText(
      captured.transmissionId,
      "transmissionId",
      256,
    ),
    projectId: requireProjectId(captured.projectId),
    originId: requireSafeInteger(captured.originId, "originId", 1),
    jobId: requireText(captured.jobId, "jobId", 256),
    pricingVersion: requireText(
      captured.pricingVersion,
      "pricingVersion",
      128,
    ),
  });
}

function captureSettlement(value) {
  const captured = captureOwnFields(
    value,
    [
      "outcome",
      "usage",
      "actualNanoUsd",
      "costPolicyVersion",
      "pricingVersion",
    ],
    "provider transmission settlement",
  );
  if (!["UNKNOWN", "RECONCILED", "RELEASED"].includes(captured.outcome)) {
    throw new TypeError("provider transmission settlement has an invalid outcome");
  }
  return Object.freeze({
    ...captured,
    costPolicyVersion: requireText(
      captured.costPolicyVersion,
      "costPolicyVersion",
      128,
    ),
    pricingVersion: requireText(
      captured.pricingVersion,
      "pricingVersion",
      128,
    ),
  });
}

function captureProviderUsage(value) {
  const captured = captureExactObject(
    value,
    [
      "prompt_tokens",
      "completion_tokens",
      "total_tokens",
      "prompt_cache_hit_tokens",
      "prompt_cache_miss_tokens",
    ],
    "provider usage",
  );
  const usage = Object.fromEntries(
    Object.entries(captured).map(([key, tokenCount]) => [
      key,
      requireSafeInteger(tokenCount, key),
    ]),
  );
  if (
    usage.prompt_cache_hit_tokens + usage.prompt_cache_miss_tokens !==
      usage.prompt_tokens ||
    usage.prompt_tokens + usage.completion_tokens !== usage.total_tokens
  ) {
    throw new TypeError("provider usage is internally inconsistent");
  }
  return Object.freeze(usage);
}

export class DurableTransmissionBudgetController {
  #store;
  #projectId;
  #originId;
  #projectCeilingNanoUsd;
  #costPolicyVersion;
  #pricingCatalog;
  #maximumInputTokensPerCall;
  #maximumOutputTokensPerCall;

  constructor(options) {
    const captured = captureControllerOptions(options);
    this.#store = captured.store;
    this.#projectId = captured.projectId;
    this.#originId = captured.originId;
    this.#projectCeilingNanoUsd = captured.projectCeilingNanoUsd;
    this.#costPolicyVersion = captured.costPolicyVersion;
    this.#pricingCatalog = captured.pricingCatalog;
    this.#maximumInputTokensPerCall = captured.maximumInputTokensPerCall;
    this.#maximumOutputTokensPerCall = captured.maximumOutputTokensPerCall;
    Object.freeze(this);
  }

  get isDurableTransmissionController() {
    return true;
  }

  get cumulativeBudgetSafe() {
    return true;
  }

  supportsRoute(route) {
    if (typeof route !== "string") return false;
    const normalized = route.toUpperCase();
    return Object.values(this.#pricingCatalog).some(
      (tuple) => tuple.route === normalized,
    );
  }

  async reserveNextCall(request) {
    const captured = captureReserveRequest(request);
    if (captured.projectId !== this.#projectId) {
      throw controllerError(
        "PROJECT_MISMATCH",
        "provider call project does not match the durable controller",
      );
    }
    if (captured.costPolicyVersion !== this.#costPolicyVersion) {
      throw controllerError(
        "COST_POLICY_VERSION_MISMATCH",
        "provider call cost policy does not match",
      );
    }
    const tuple = this.#pricingCatalog[captured.pricing.pricingVersion];
    if (
      tuple === undefined ||
      tuple.model !== captured.pricing.model ||
      tuple.serviceTier !== captured.pricing.serviceTier ||
      tuple.reasoningEffort !== captured.pricing.reasoningEffort ||
      tuple.rates.cached_input !== captured.pricing.rates.cached_input ||
      tuple.rates.uncached_input !== captured.pricing.rates.uncached_input ||
      tuple.rates.output !== captured.pricing.rates.output
    ) {
      throw controllerError(
        "UNSUPPORTED_PRICE_TUPLE",
        "provider call price tuple is not in the frozen catalog",
      );
    }
    if (
      captured.maximumInputTokens > this.#maximumInputTokensPerCall ||
      captured.maximumOutputTokens > this.#maximumOutputTokensPerCall
    ) {
      throw controllerError(
        "PROVIDER_TOKEN_LIMIT_EXCEEDED",
        "provider call exceeds the controller per-call token ceiling: " +
          `input=${captured.maximumInputTokens}/` +
          `${this.#maximumInputTokensPerCall} output=${captured.maximumOutputTokens}/` +
          `${this.#maximumOutputTokensPerCall}`,
      );
    }
    const estimatedNanoUsd = safeSum(
      [
        safeProduct(
          captured.maximumInputTokens,
          tuple.rates.uncached_input,
          "PRICE_ESTIMATE_OVERFLOW",
          "provider input price estimate overflowed",
        ),
        safeProduct(
          captured.maximumOutputTokens,
          tuple.rates.output,
          "PRICE_ESTIMATE_OVERFLOW",
          "provider output price estimate overflowed",
        ),
      ],
      "PRICE_ESTIMATE_OVERFLOW",
      "provider price estimate overflowed",
    );
    if (captured.estimatedNanoUsd !== estimatedNanoUsd) {
      throw controllerError(
        "PRICE_ESTIMATE_MISMATCH",
        "provider call estimate does not match the frozen price tuple",
      );
    }
    const derivedMaximumInputTokens = safeProduct(
      this.#maximumInputTokensPerCall,
      captured.maximumProviderCalls,
      "PROVIDER_TOKEN_LIMIT_OVERFLOW",
      "provider input token limit overflowed",
    );
    const derivedMaximumOutputTokensTotal = safeProduct(
      this.#maximumOutputTokensPerCall,
      captured.maximumProviderCalls,
      "PROVIDER_TOKEN_LIMIT_OVERFLOW",
      "provider output token limit overflowed",
    );
    const maximumInputTokens =
      captured.aggregateTokenLimits?.maximumInputTokens ??
      derivedMaximumInputTokens;
    const maximumCachedInputTokens =
      captured.aggregateTokenLimits?.maximumCachedInputTokens ??
      derivedMaximumInputTokens;
    const maximumOutputTokensTotal =
      captured.aggregateTokenLimits?.maximumOutputTokensTotal ??
      derivedMaximumOutputTokensTotal;
    const maximumTotalTokens =
      captured.aggregateTokenLimits?.maximumTotalTokens ??
      safeSum(
        [maximumInputTokens, maximumOutputTokensTotal],
        "PROVIDER_TOKEN_LIMIT_OVERFLOW",
        "provider total token limit overflowed",
      );
    this.#store.configureProviderAccounting({
      projectId: this.#projectId,
      originId: this.#originId,
      jobId: captured.jobId,
      ceilingNanoUsd: this.#projectCeilingNanoUsd,
      pricingVersion: this.#costPolicyVersion,
      maximumProviderCalls: captured.maximumProviderCalls,
      maximumInputTokens,
      maximumCachedInputTokens,
      maximumOutputTokensTotal,
      maximumTotalTokens,
    });
    const ordinalBigInt =
      BigInt(captured.attemptOrdinal - 1) * BigInt(MAX_PROVIDER_CALLS) +
      BigInt(captured.turn);
    if (ordinalBigInt > MAX_SAFE_BIGINT) {
      throw controllerError(
        "PROVIDER_TRANSMISSION_ORDINAL_OVERFLOW",
        "provider transmission ordinal overflowed",
      );
    }
    const transmissionId = `PT-${sha256(
      [
        "deepluna-provider-transmission-v1",
        this.#projectId,
        captured.jobId,
        captured.attemptId,
        String(captured.attemptOrdinal),
        String(captured.turn),
        captured.requestIdentityHash,
        captured.pricing.pricingVersion,
      ].join("\0"),
    )}`;
    return this.#store.reserveProviderTransmission({
      transmissionId,
      projectId: this.#projectId,
      originId: this.#originId,
      jobId: captured.jobId,
      attemptId: captured.attemptId,
      transmissionOrdinal: Number(ordinalBigInt),
      route: tuple.route,
      provider: tuple.provider,
      model: tuple.model,
      serviceTier: tuple.serviceTier,
      reasoningEffort: tuple.reasoningEffort,
      pricingVersion: captured.pricing.pricingVersion,
      maximumEstimatedNanoUsd: captured.maximumEstimatedNanoUsd,
      estimatedNanoUsd,
      estimatedInputTokens: captured.maximumInputTokens,
      estimatedOutputTokens: captured.maximumOutputTokens,
    });
  }

  async reconcile(reservation, settlement) {
    const capturedReservation = captureReservation(reservation);
    const capturedSettlement = captureSettlement(settlement);
    if (
      capturedReservation.projectId !== this.#projectId ||
      capturedReservation.originId !== this.#originId
    ) {
      throw controllerError(
        "NOT_FOUND_OR_NOT_OWNED",
        "provider transmission was not found",
      );
    }
    if (capturedSettlement.costPolicyVersion !== this.#costPolicyVersion) {
      throw controllerError(
        "COST_POLICY_VERSION_MISMATCH",
        "provider settlement cost policy does not match",
      );
    }
    if (
      capturedSettlement.pricingVersion !==
        capturedReservation.pricingVersion
    ) {
      throw controllerError(
        "PRICING_VERSION_MISMATCH",
        "provider settlement pricing identity does not match its reservation",
      );
    }
    const common = {
      transmissionId: capturedReservation.transmissionId,
      projectId: this.#projectId,
      originId: this.#originId,
      pricingVersion: capturedReservation.pricingVersion,
      outcome: capturedSettlement.outcome,
    };
    if (capturedSettlement.outcome !== "RECONCILED") {
      const expectedActual =
        capturedSettlement.outcome === "RELEASED" ? 0 : null;
      if (
        capturedSettlement.usage !== null ||
        capturedSettlement.actualNanoUsd !== expectedActual
      ) {
        throw new TypeError(
          `${capturedSettlement.outcome} settlement must not claim usage`,
        );
      }
      return this.#store.reconcileProviderTransmission({
        ...common,
        actualNanoUsd: expectedActual,
        inputTokens: null,
        cachedInputTokens: null,
        outputTokens: null,
        totalTokens: null,
      });
    }
    const usage = captureProviderUsage(capturedSettlement.usage);
    const tuple = this.#pricingCatalog[capturedReservation.pricingVersion];
    if (tuple === undefined) {
      throw controllerError(
        "UNSUPPORTED_PRICE_TUPLE",
        "provider settlement price tuple is not in the frozen catalog",
      );
    }
    const actualNanoUsd = safeSum(
      [
        safeProduct(
          usage.prompt_cache_hit_tokens,
          tuple.rates.cached_input,
          "PROVIDER_COST_OVERFLOW",
          "provider cached-input cost overflowed",
        ),
        safeProduct(
          usage.prompt_cache_miss_tokens,
          tuple.rates.uncached_input,
          "PROVIDER_COST_OVERFLOW",
          "provider uncached-input cost overflowed",
        ),
        safeProduct(
          usage.completion_tokens,
          tuple.rates.output,
          "PROVIDER_COST_OVERFLOW",
          "provider output cost overflowed",
        ),
      ],
      "PROVIDER_COST_OVERFLOW",
      "provider cost overflowed",
    );
    if (capturedSettlement.actualNanoUsd !== actualNanoUsd) {
      throw controllerError(
        "PROVIDER_ACTUAL_COST_MISMATCH",
        "provider actual cost does not match reconciled usage",
      );
    }
    return this.#store.reconcileProviderTransmission({
      ...common,
      actualNanoUsd,
      inputTokens: usage.prompt_tokens,
      cachedInputTokens: usage.prompt_cache_hit_tokens,
      outputTokens: usage.completion_tokens,
      totalTokens: usage.total_tokens,
    });
  }

  snapshot(jobId) {
    return this.#store.getProviderAccountingSnapshot({
      projectId: this.#projectId,
      originId: this.#originId,
      jobId: requireText(jobId, "jobId", 256),
    });
  }
}

export function createDurableTransmissionBudgetController(options) {
  return new DurableTransmissionBudgetController(options);
}
