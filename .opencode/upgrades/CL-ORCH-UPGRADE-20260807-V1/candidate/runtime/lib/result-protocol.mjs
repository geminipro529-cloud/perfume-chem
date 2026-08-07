export const EXECUTION_STATUSES = Object.freeze(new Set([
  "ACCEPTED",
  "INCOMPLETE",
  "BLOCKED",
  "PROVIDER_ERROR",
  "CONTRACT_ERROR",
  "CANCELLED",
]));

export const EVIDENCE_VERDICTS = Object.freeze(new Set([
  "POSITIVE",
  "NEGATIVE",
  "NULL",
  "MIXED",
  "UNRESOLVED",
  "NOT_APPLICABLE",
]));

export const ROUTES = Object.freeze(new Set([
  "LOCAL",
  "FLASH",
  "DIRECT_PRO",
  "V4_PRO",
  "NEMOTRON",
  "GLM",
  "LUNA",
  "SOL",
]));

export const DETERMINISTIC_REQUEST_REJECTION = "DETERMINISTIC_REQUEST_REJECTED";
export const CONTRACT_ERROR_CODE = "CONTRACT_ERROR";
export const NEGATIVE_ADMISSION_CODE = "NEGATIVE_ADMISSION";
export const DEFAULT_ROUTE_LIMITS = Object.freeze({
  maximumProviderCalls: 2,
  maximumInputTokens: 131_072,
  maximumCachedInputTokens: 65_536,
  maximumOutputTokensTotal: 16_384,
  maximumTotalTokens: 147_456,
});
const MAXIMUM_PROVIDER_CALLS_LIMIT = 5;
const ROUTE_CONSTRAINT_KEYS = Object.freeze(new Set([
  "allowed_routes",
  "fallback_policy",
  "maximum_attempts",
  "maximum_estimated_cost_usd",
  "privacy_class",
  "maximum_provider_calls",
  "maximum_input_tokens",
  "maximum_cached_input_tokens",
  "maximum_output_tokens_total",
  "maximum_total_tokens",
]));

export function isDeterministicRequestRejection(value = {}) {
  const status = Number(value?.status ?? value?.httpStatus);
  const failureClass = String(
    value?.failureClass ?? value?.deepseekFailureClass ?? value?.code ?? "",
  ).toUpperCase();
  return status === 400 ||
    status === 422 ||
    failureClass === DETERMINISTIC_REQUEST_REJECTION ||
    failureClass === CONTRACT_ERROR_CODE ||
    failureClass === NEGATIVE_ADMISSION_CODE;
}

export function contractErrorSemantics({
  summary = "The exact provider request was deterministically rejected.",
  code = DETERMINISTIC_REQUEST_REJECTION,
  httpStatus = null,
  negativeAdmission = false,
} = {}) {
  const boundedSummary = String(summary).trim().slice(0, 2_000) ||
    "The exact provider request was deterministically rejected.";
  const normalizedStatus = httpStatus == null ? null : Number(httpStatus);
  if (
    normalizedStatus !== null &&
    (!Number.isInteger(normalizedStatus) || ![400, 422].includes(normalizedStatus))
  ) {
    throw new TypeError("deterministic contract error status must be 400 or 422");
  }
  return Object.freeze({
    status: "FAIL",
    execution_status: "CONTRACT_ERROR",
    evidence_verdict: "UNRESOLVED",
    error_code: String(code),
    http_status: normalizedStatus,
    negative_admission: Boolean(negativeAdmission),
    summary: boundedSummary,
  });
}

function routeConstraintData(raw) {
  if (
    !raw ||
    typeof raw !== "object" ||
    Array.isArray(raw) ||
    ![Object.prototype, null].includes(Object.getPrototypeOf(raw))
  ) {
    throw new Error("route_constraints must be a plain object");
  }
  const descriptors = Object.getOwnPropertyDescriptors(raw);
  const data = {};
  for (const key of Reflect.ownKeys(descriptors)) {
    if (typeof key !== "string" || !ROUTE_CONSTRAINT_KEYS.has(key)) {
      throw new Error(`unsupported route constraint key: ${String(key)}`);
    }
    const descriptor = descriptors[key];
    if (!Object.hasOwn(descriptor, "value")) {
      throw new Error(`route_constraints accessor is not allowed: ${key}`);
    }
    data[key] = descriptor.value;
  }
  return data;
}

function positiveSafeInteger(value, defaultValue, field) {
  const normalized = value === undefined ? defaultValue : value;
  if (!Number.isSafeInteger(normalized) || normalized < 1) {
    throw new Error(`${field} must be a positive safe integer`);
  }
  return normalized;
}

export function normalizeRouteConstraints(raw = {}) {
  const data = routeConstraintData(raw);
  const allowedRoutes = [...new Set(data.allowed_routes ?? ["LOCAL", "FLASH", "LUNA"])];
  if (!allowedRoutes.length || allowedRoutes.some((route) => !ROUTES.has(route))) {
    throw new Error("allowed_routes contains an unsupported route");
  }
  const fallbackPolicy = String(data.fallback_policy ?? "LUNA_ELIGIBLE").toUpperCase();
  if (!new Set(["NO_LUNA", "LUNA_ELIGIBLE"]).has(fallbackPolicy)) {
    throw new Error("fallback_policy must be NO_LUNA or LUNA_ELIGIBLE");
  }
  const maximumAttempts = Number(data.maximum_attempts ?? 2);
  const maximumEstimatedCostUsd = Number(data.maximum_estimated_cost_usd ?? 1);
  if (!Number.isInteger(maximumAttempts) || maximumAttempts < 1 || maximumAttempts > 3) {
    throw new Error("maximum_attempts must be 1 to 3");
  }
  if (!Number.isFinite(maximumEstimatedCostUsd) || maximumEstimatedCostUsd < 0) {
    throw new Error("maximum_estimated_cost_usd must be nonnegative");
  }
  const privacyClass = String(data.privacy_class ?? "PROVIDER_ALLOWED").toUpperCase();
  if (!new Set(["LOCAL_ONLY", "PROVIDER_ALLOWED"]).has(privacyClass)) {
    throw new Error("privacy_class must be LOCAL_ONLY or PROVIDER_ALLOWED");
  }
  const maximumProviderCalls = positiveSafeInteger(
    data.maximum_provider_calls,
    DEFAULT_ROUTE_LIMITS.maximumProviderCalls,
    "maximum_provider_calls",
  );
  if (maximumProviderCalls > MAXIMUM_PROVIDER_CALLS_LIMIT) {
    throw new Error(
      `maximum_provider_calls must be between 1 and ${MAXIMUM_PROVIDER_CALLS_LIMIT}`,
    );
  }
  const maximumInputTokens = positiveSafeInteger(
    data.maximum_input_tokens,
    DEFAULT_ROUTE_LIMITS.maximumInputTokens,
    "maximum_input_tokens",
  );
  const maximumCachedInputTokens = positiveSafeInteger(
    data.maximum_cached_input_tokens,
    DEFAULT_ROUTE_LIMITS.maximumCachedInputTokens,
    "maximum_cached_input_tokens",
  );
  const maximumOutputTokensTotal = positiveSafeInteger(
    data.maximum_output_tokens_total,
    DEFAULT_ROUTE_LIMITS.maximumOutputTokensTotal,
    "maximum_output_tokens_total",
  );
  const maximumTotalTokens = positiveSafeInteger(
    data.maximum_total_tokens,
    DEFAULT_ROUTE_LIMITS.maximumTotalTokens,
    "maximum_total_tokens",
  );
  if (maximumCachedInputTokens > maximumInputTokens) {
    throw new Error(
      "maximum_cached_input_tokens must not exceed maximum_input_tokens",
    );
  }
  if (
    BigInt(maximumTotalTokens) <
      BigInt(maximumInputTokens) + BigInt(maximumOutputTokensTotal)
  ) {
    throw new Error(
      "maximum_total_tokens must be at least maximum_input_tokens plus " +
        "maximum_output_tokens_total",
    );
  }
  return Object.freeze({
    allowedRoutes: Object.freeze(allowedRoutes),
    fallbackPolicy,
    maximumAttempts,
    maximumEstimatedCostUsd,
    privacyClass,
    maximumProviderCalls,
    maximumInputTokens,
    maximumCachedInputTokens,
    maximumOutputTokensTotal,
    maximumTotalTokens,
  });
}

export function normalizeResult(raw = {}) {
  let executionStatus = raw.execution_status;
  let evidenceVerdict = raw.evidence_verdict;
  if (!executionStatus && raw.status === "PASS") executionStatus = "ACCEPTED";
  if (!executionStatus && raw.status === "BLOCKED") executionStatus = "BLOCKED";
  if (!executionStatus && raw.status === "FAIL") executionStatus = "INCOMPLETE";
  evidenceVerdict ??= executionStatus === "ACCEPTED" ? "NOT_APPLICABLE" : "UNRESOLVED";
  if (!EXECUTION_STATUSES.has(executionStatus)) throw new Error("invalid execution_status");
  if (!EVIDENCE_VERDICTS.has(evidenceVerdict)) throw new Error("invalid evidence_verdict");
  return Object.freeze({
    ...raw,
    execution_status: executionStatus,
    evidence_verdict: evidenceVerdict,
  });
}

export function isAcceptedResult(result) {
  return result.execution_status === "ACCEPTED";
}

export function legacyStatus(result) {
  if (result.execution_status === "ACCEPTED") return "PASS";
  if (new Set(["BLOCKED", "CANCELLED"]).has(result.execution_status)) return "BLOCKED";
  return "FAIL";
}

export function isFallbackEligible(
  result,
  constraints,
  attempts = 1,
  estimatedNextCostUsd = 0,
  fallbackRoute = "LUNA",
) {
  const route = String(fallbackRoute).toUpperCase();
  if (!ROUTES.has(route)) {
    throw new Error(`unsupported fallback route: ${fallbackRoute}`);
  }
  if (
    result.execution_status === "CONTRACT_ERROR" ||
    isDeterministicRequestRejection(result)
  ) return false;
  return result.execution_status === "PROVIDER_ERROR" &&
    constraints.fallbackPolicy === "LUNA_ELIGIBLE" &&
    (route === "LUNA" || route === "GLM") &&
    constraints.allowedRoutes.includes(route) &&
    constraints.privacyClass === "PROVIDER_ALLOWED" &&
    attempts < constraints.maximumAttempts &&
    Number.isFinite(estimatedNextCostUsd) &&
    estimatedNextCostUsd >= 0 &&
    estimatedNextCostUsd <= constraints.maximumEstimatedCostUsd;
}

export function dependencySatisfied(result, acceptedVerdicts) {
  return isAcceptedResult(result) && acceptedVerdicts.includes(result.evidence_verdict);
}
