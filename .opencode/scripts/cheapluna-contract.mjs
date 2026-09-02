/**
 * Host-side DeepLuna Chat contract preflight.
 *
 * The runtime repository tool accepts at most 400 lines per read. Chat jobs
 * reserve their final provider call for the evidence handoff, so oversized
 * ranges must be split before submission rather than repaired by the worker.
 */

import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

export const MAX_REQUIRED_READ_LINES = 400;
export const MAX_REQUIRED_READ_BYTES = 15 * 1024;
export const MIN_CHAT_OUTPUT_TOKENS = 3000;
export const MAX_CHAT_OUTPUT_TOKENS = 8192;
export const MIN_REPOSITORY_OUTPUT_TURNS = 2;
export const REPOSITORY_INPUT_BASE_TOKENS = 28_000;
export const REPOSITORY_COMMAND_RESULT_TOKENS = 64_000;
export const DEFAULT_MAXIMUM_INPUT_TOKENS = 131_072;
export const DEFAULT_MAXIMUM_CACHED_INPUT_TOKENS = 65_536;
export const DEFAULT_MAXIMUM_OUTPUT_TOKENS_TOTAL = 16_384;
export const DEEPSEEK_UNCACHED_INPUT_NANO_USD = 140;
export const DEEPSEEK_OUTPUT_NANO_USD = 280;

function portableRelativePath(value) {
  const raw = String(value ?? "").trim().replaceAll("\\", "/").replace(/^\.\//, "");
  if (!raw || path.posix.isAbsolute(raw) || /^[a-z]:\//i.test(raw)) {
    throw new Error(`required read path is outside workspace: ${value}`);
  }
  const normalized = path.posix.normalize(raw);
  if (normalized === ".." || normalized.startsWith("../")) {
    throw new Error(`required read path is outside workspace: ${value}`);
  }
  return normalized;
}

function isWithin(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== "..");
}

function readUtf8Lines(root, relativePath) {
  const rootReal = fs.realpathSync(root);
  const requested = path.resolve(rootReal, relativePath);
  if (!isWithin(requested, rootReal)) {
    throw new Error(`required read path is outside workspace: ${relativePath}`);
  }
  const realPath = fs.realpathSync(requested);
  if (!isWithin(realPath, rootReal)) {
    throw new Error(`required read resolves outside workspace: ${relativePath}`);
  }
  if (!fs.statSync(realPath).isFile()) {
    throw new Error(`required read is not a regular file: ${relativePath}`);
  }
  const raw = fs.readFileSync(realPath);
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(raw);
  } catch {
    throw new Error(`required read is not valid UTF-8: ${relativePath}`);
  }
  return text.replace(/\r\n?/g, "\n").split("\n");
}

function normalizedRanges(requiredReads, root) {
  if (!Array.isArray(requiredReads)) throw new Error("required_reads must be an array");
  const linesByPath = new Map();
  const ranges = requiredReads.map((read) => {
    if (!read || typeof read !== "object" || Array.isArray(read)) {
      throw new Error("required_reads entries must be objects");
    }
    const relativePath = portableRelativePath(read.path);
    if (read.unit !== "line") throw new Error("required_reads unit must be line");
    const start = Number(read.start);
    if (!Number.isInteger(start) || start < 1) {
      throw new Error("required_reads start must be a positive integer");
    }
    let lines = linesByPath.get(relativePath);
    if (!lines) {
      lines = readUtf8Lines(root, relativePath);
      linesByPath.set(relativePath, lines);
    }
    const end = read.end === null ? lines.length : Number(read.end);
    if (!Number.isInteger(end) || end < start) {
      throw new Error("required_reads end must be null or an integer at least start");
    }
    if (start > lines.length || end > lines.length) {
      throw new Error(`required range exceeds line count for ${relativePath}`);
    }
    return { path: relativePath, unit: "line", start, end };
  });

  ranges.sort((left, right) =>
    left.path.localeCompare(right.path) || left.start - right.start || left.end - right.end,
  );

  const merged = [];
  for (const range of ranges) {
    const previous = merged.at(-1);
    if (previous && previous.path === range.path && range.start <= previous.end + 1) {
      previous.end = Math.max(previous.end, range.end);
    } else {
      merged.push({ ...range });
    }
  }
  return { merged, linesByPath };
}

export function inspectRequiredReads(
  requiredReads,
  {
    root,
    maxLines = MAX_REQUIRED_READ_LINES,
    maxBytes = MAX_REQUIRED_READ_BYTES,
  } = {},
) {
  if (!root) throw new Error("DeepLuna contract preflight requires a project root");
  if (!Number.isInteger(maxLines) || maxLines < 1) throw new Error("maxLines must be positive");
  if (!Number.isInteger(maxBytes) || maxBytes < 1) throw new Error("maxBytes must be positive");

  const original = Array.isArray(requiredReads) ? requiredReads : [];
  if (original.length === 0) {
    return Object.freeze({
      requiredReads: Object.freeze([]),
      selectedBytes: 0,
      originalRangeCount: 0,
      normalizedRangeCount: 0,
      changed: false,
    });
  }

  const { merged, linesByPath } = normalizedRanges(original, root);
  let selectedBytes = 0;
  for (const range of merged) {
    const lines = linesByPath.get(range.path);
    selectedBytes += Buffer.byteLength(
      lines.slice(range.start - 1, range.end).join("\n"),
      "utf8",
    );
  }
  if (selectedBytes > maxBytes) {
    throw new Error(
      `required_reads selected UTF-8 evidence ${selectedBytes} bytes exceeds ${maxBytes}-byte cap; ` +
        "split the audit into separate bounded Chat tasks",
    );
  }

  const chunks = [];
  for (const range of merged) {
    for (let start = range.start; start <= range.end; start += maxLines) {
      chunks.push(Object.freeze({
        path: range.path,
        unit: "line",
        start,
        end: Math.min(range.end, start + maxLines - 1),
      }));
    }
  }

  return Object.freeze({
    requiredReads: Object.freeze(chunks),
    selectedBytes,
    originalRangeCount: original.length,
    normalizedRangeCount: chunks.length,
    changed: JSON.stringify(original) !== JSON.stringify(chunks),
  });
}

function requiredReadEvidenceHash(merged, linesByPath) {
  const hash = createHash("sha256");
  for (const range of merged) {
    const lines = linesByPath.get(range.path);
    for (let line = range.start; line <= range.end; line += 1) {
      hash.update(JSON.stringify([range.path, line]));
      hash.update("\0");
      hash.update(lines[line - 1], "utf8");
      hash.update("\0");
    }
  }
  return hash.digest("hex");
}

/**
 * Partition an exhaustive set of line reads into independently admissible
 * Chat tasks. The worker protocol is line-addressed, so a single line above
 * the byte ceiling is indivisible and must fail closed instead of truncating.
 */
export function planRequiredReadShards(
  requiredReads,
  {
    root,
    maxLines = MAX_REQUIRED_READ_LINES,
    maxBytes = MAX_REQUIRED_READ_BYTES,
  } = {},
) {
  if (!root) throw new Error("DeepLuna shard planning requires a project root");
  if (!Number.isInteger(maxLines) || maxLines < 1) throw new Error("maxLines must be positive");
  if (!Number.isInteger(maxBytes) || maxBytes < 1) throw new Error("maxBytes must be positive");

  const original = Array.isArray(requiredReads) ? requiredReads : [];
  const { merged, linesByPath } = normalizedRanges(original, root);
  const planned = [];
  let currentRanges = [];
  let currentBytes = 0;

  const flush = () => {
    if (currentRanges.length === 0) return;
    planned.push({
      requiredReads: currentRanges.map((read) => Object.freeze({ ...read })),
      selectedBytes: currentBytes,
    });
    currentRanges = [];
    currentBytes = 0;
  };

  for (const range of merged) {
    const lines = linesByPath.get(range.path);
    for (let line = range.start; line <= range.end; line += 1) {
      const lineBytes = Buffer.byteLength(lines[line - 1], "utf8");
      if (lineBytes > maxBytes) {
        const error = new Error(
          `UNSHARDABLE_REQUIRED_READ_LINE path=${range.path} line=${line} ` +
            `bytes=${lineBytes} cap=${maxBytes}`,
        );
        error.code = "UNSHARDABLE_REQUIRED_READ_LINE";
        error.path = range.path;
        error.line = line;
        error.bytes = lineBytes;
        error.cap = maxBytes;
        throw error;
      }

      let previous = currentRanges.at(-1);
      let extendsPrevious = Boolean(
        previous &&
          previous.path === range.path &&
          previous.end + 1 === line &&
          previous.end - previous.start + 1 < maxLines,
      );
      let addedBytes = lineBytes + (extendsPrevious ? 1 : 0);
      if (currentRanges.length > 0 && currentBytes + addedBytes > maxBytes) {
        flush();
        previous = undefined;
        extendsPrevious = false;
        addedBytes = lineBytes;
      }

      if (extendsPrevious) {
        previous.end = line;
      } else {
        currentRanges.push({ path: range.path, unit: "line", start: line, end: line });
      }
      currentBytes += addedBytes;
    }
  }
  flush();
  if (planned.length === 0) planned.push({ requiredReads: [], selectedBytes: 0 });

  const count = planned.length;
  const shards = planned.map((shard, index) => Object.freeze({
    ordinal: index + 1,
    count,
    requiredReads: Object.freeze(shard.requiredReads),
    selectedBytes: shard.selectedBytes,
  }));
  const evidenceSha256 = requiredReadEvidenceHash(merged, linesByPath);
  const planSha256 = createHash("sha256").update(JSON.stringify({
    evidenceSha256,
    shards: shards.map(({ requiredReads: reads, selectedBytes }) => ({
      requiredReads: reads,
      selectedBytes,
    })),
  })).digest("hex");

  return Object.freeze({
    shards: Object.freeze(shards),
    shardCount: count,
    evidenceSha256,
    planSha256,
    originalRangeCount: original.length,
  });
}

export function minimumRepositoryInputTokens({
  selectedBytes = 0,
  commandCount = 0,
} = {}) {
  if (!Number.isSafeInteger(selectedBytes) || selectedBytes < 0) {
    throw new Error("selectedBytes must be a nonnegative safe integer");
  }
  if (!Number.isSafeInteger(commandCount) || commandCount < 0) {
    throw new Error("commandCount must be a nonnegative safe integer");
  }
  const raw =
    REPOSITORY_INPUT_BASE_TOKENS +
    selectedBytes +
    commandCount * REPOSITORY_COMMAND_RESULT_TOKENS;
  if (!Number.isSafeInteger(raw)) {
    throw new Error("repository input floor exceeds the safe integer bound");
  }
  return Math.ceil(raw / 1024) * 1024;
}

function autosizeRepositoryRoute(route, {
  aggregateOutputTokens,
  commandCount,
  maximumCostUsd,
  selectedBytes,
}) {
  const minimumInputTokens = minimumRepositoryInputTokens({
    selectedBytes,
    commandCount,
  });
  const configuredInput = Number(
    route.maximum_input_tokens ?? DEFAULT_MAXIMUM_INPUT_TOKENS,
  );
  const configuredCachedInput = Number(
    route.maximum_cached_input_tokens ?? DEFAULT_MAXIMUM_CACHED_INPUT_TOKENS,
  );
  const configuredTotal = Number(
    route.maximum_total_tokens ?? configuredInput + aggregateOutputTokens,
  );
  if (!Number.isSafeInteger(configuredInput) || configuredInput < 1) {
    throw new Error("maximum_input_tokens must be a positive safe integer");
  }
  if (!Number.isSafeInteger(configuredCachedInput) || configuredCachedInput < 0) {
    throw new Error("maximum_cached_input_tokens must be a nonnegative safe integer");
  }
  if (!Number.isSafeInteger(configuredTotal) || configuredTotal < 1) {
    throw new Error("maximum_total_tokens must be a positive safe integer");
  }
  const maximumInputTokens = Math.max(configuredInput, minimumInputTokens);
  const maximumCachedInputTokens = Math.min(configuredCachedInput, maximumInputTokens);
  const maximumTotalTokens = Math.max(
    configuredTotal,
    maximumInputTokens + aggregateOutputTokens,
  );
  const estimatedNanoUsd =
    maximumInputTokens * DEEPSEEK_UNCACHED_INPUT_NANO_USD +
    aggregateOutputTokens * DEEPSEEK_OUTPUT_NANO_USD;
  const maximumNanoUsd = Math.floor(maximumCostUsd * 1_000_000_000);
  if (!Number.isSafeInteger(estimatedNanoUsd) || estimatedNanoUsd > maximumNanoUsd) {
    throw new Error(
      `repository evidence requires at least ${minimumInputTokens} cumulative input tokens, ` +
        `which exceeds the ${maximumCostUsd} USD contract; split the task`,
    );
  }
  return Object.freeze({
    ...route,
    maximum_input_tokens: maximumInputTokens,
    maximum_cached_input_tokens: maximumCachedInputTokens,
    maximum_output_tokens_total: aggregateOutputTokens,
    maximum_total_tokens: maximumTotalTokens,
  });
}

export function prepareDeepLunaInput(input, options = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new Error("DeepLuna task input must be an object");
  }
  const tier = String(input.tier ?? "");
  if (!new Set(["PRO", "REASONING"]).has(tier)) {
    throw new Error("DeepLuna Chat tier must be PRO or REASONING");
  }
  const outputTokens = Number(input.max_output_tokens ?? 4000);
  if (
    !Number.isInteger(outputTokens) ||
    outputTokens < MIN_CHAT_OUTPUT_TOKENS ||
    outputTokens > MAX_CHAT_OUTPUT_TOKENS
  ) {
    throw new Error(
      `max_output_tokens must be an integer between ${MIN_CHAT_OUTPUT_TOKENS} and ` +
        `${MAX_CHAT_OUTPUT_TOKENS}`,
    );
  }
  const route = input.route_constraints;
  if (!route || typeof route !== "object" || Array.isArray(route)) {
    throw new Error("DeepLuna Chat route_constraints must be an object");
  }
  if (
    !Array.isArray(route.allowed_routes) ||
    route.allowed_routes.length !== 1 ||
    route.allowed_routes[0] !== "DIRECT_PRO"
  ) {
    throw new Error("DeepLuna Chat allows only DIRECT_PRO");
  }
  if (route.fallback_policy !== "NO_LUNA") {
    throw new Error("DeepLuna Chat fallback_policy must be NO_LUNA");
  }
  if (route.maximum_attempts !== 1) {
    throw new Error("DeepLuna Chat maximum_attempts must be 1");
  }
  const providerCalls = Number(route.maximum_provider_calls);
  if (!Number.isInteger(providerCalls) || providerCalls < 1 || providerCalls > 2) {
    throw new Error("DeepLuna Chat maximum_provider_calls must be between 1 and 2");
  }
  const maximumCost = Number(route.maximum_estimated_cost_usd);
  if (!Number.isFinite(maximumCost) || maximumCost <= 0 || maximumCost > 0.08) {
    throw new Error("DeepLuna Chat maximum_estimated_cost_usd must be in (0, 0.08]");
  }
  const inspection = inspectRequiredReads(input.required_reads ?? [], options);
  const repositoryWork =
    inspection.requiredReads.length > 0 ||
    (Array.isArray(input.allowed_paths) && input.allowed_paths.length > 0) ||
    (Array.isArray(input.commands_tests) && input.commands_tests.length > 0);
  if (repositoryWork && providerCalls !== MIN_REPOSITORY_OUTPUT_TURNS) {
    throw new Error("DeepLuna Chat repository work requires exactly 2 provider calls");
  }
  const aggregateOutputTokens = Number(
    route.maximum_output_tokens_total ?? DEFAULT_MAXIMUM_OUTPUT_TOKENS_TOTAL,
  );
  if (!Number.isSafeInteger(aggregateOutputTokens) || aggregateOutputTokens < 1) {
    throw new Error("maximum_output_tokens_total must be a positive safe integer");
  }
  if (
    repositoryWork &&
    aggregateOutputTokens < outputTokens * MIN_REPOSITORY_OUTPUT_TURNS
  ) {
    throw new Error(
      `DeepLuna Chat repository work requires maximum_output_tokens_total >= ` +
      `${outputTokens * MIN_REPOSITORY_OUTPUT_TURNS}`,
    );
  }
  const preparedRoute = repositoryWork
    ? autosizeRepositoryRoute(route, {
        aggregateOutputTokens,
        commandCount: Array.isArray(input.commands_tests)
          ? input.commands_tests.length
          : 0,
        maximumCostUsd: maximumCost,
        selectedBytes: inspection.selectedBytes,
      })
    : route;
  return Object.freeze({
    input: Object.freeze({
      ...input,
      required_reads: inspection.requiredReads,
      route_constraints: preparedRoute,
    }),
    inspection,
  });
}

/**
 * Build a client-fanout plan while preserving every per-worker route fence and
 * enforcing the original request's cost ceiling across all evidence shards.
 */
export function prepareDeepLunaShardPlan(input, options = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new Error("DeepLuna task input must be an object");
  }
  const taskId = String(input.task_id ?? "").trim();
  const objective = String(input.objective ?? "").trim();
  if (!taskId) throw new Error("DeepLuna sharded task requires task_id");
  if (!objective) throw new Error("DeepLuna sharded task requires objective");

  const readPlan = planRequiredReadShards(input.required_reads ?? [], options);
  const provisional = readPlan.shards.map((shard) => {
    const suffix = `-s${shard.ordinal}-of-${shard.count}`;
    const boundedTaskId = taskId.length + suffix.length <= 64
      ? `${taskId}${suffix}`
      : `${taskId.slice(0, 64 - suffix.length - 9)}-` +
        `${createHash("sha256").update(taskId).digest("hex").slice(0, 8)}${suffix}`;
    const candidate = {
      ...input,
      task_id: boundedTaskId,
      objective:
        `${objective}\n\nEvidence shard ${shard.ordinal}/${shard.count}. ` +
        "Analyze only the supplied required_reads; do not infer unseen shard content. " +
        "Return findings with exact path and line locators for deterministic Sol aggregation.",
      required_reads: shard.requiredReads,
      route_constraints: { ...input.route_constraints },
    };
    const prepared = prepareDeepLunaInput(candidate, options).input;
    const route = prepared.route_constraints;
    const estimatedNanoUsd =
      route.maximum_input_tokens * DEEPSEEK_UNCACHED_INPUT_NANO_USD +
      route.maximum_output_tokens_total * DEEPSEEK_OUTPUT_NANO_USD;
    return { shard, prepared, estimatedNanoUsd };
  });

  const maximumCostUsd = Number(input.route_constraints?.maximum_estimated_cost_usd);
  if (!Number.isFinite(maximumCostUsd) || maximumCostUsd <= 0 || maximumCostUsd > 0.08) {
    throw new Error("DeepLuna Chat maximum_estimated_cost_usd must be in (0, 0.08]");
  }
  const aggregateEstimatedNanoUsd = provisional.reduce(
    (total, shard) => total + shard.estimatedNanoUsd,
    0,
  );
  const aggregateCapNanoUsd = Math.floor(maximumCostUsd * 1_000_000_000);
  if (aggregateEstimatedNanoUsd > aggregateCapNanoUsd) {
    throw new Error(
      `sharded repository evidence requires an aggregate ceiling of ` +
        `${(aggregateEstimatedNanoUsd / 1_000_000_000).toFixed(9)} USD, which exceeds ` +
        `${maximumCostUsd} USD; reduce per-shard token ceilings or use a separately justified plan`,
    );
  }

  const shards = provisional.map(({ shard, prepared, estimatedNanoUsd }) => {
    const finalInput = prepareDeepLunaInput({
      ...prepared,
      route_constraints: {
        ...prepared.route_constraints,
        maximum_estimated_cost_usd: estimatedNanoUsd / 1_000_000_000,
      },
    }, options).input;
    return Object.freeze({
      ordinal: shard.ordinal,
      count: shard.count,
      selectedBytes: shard.selectedBytes,
      estimatedNanoUsd,
      input: finalInput,
    });
  });

  return Object.freeze({
    execution: "CLIENT_FANOUT_EVIDENCE_SHARDS",
    baseTaskId: taskId,
    shardCount: readPlan.shardCount,
    evidenceSha256: readPlan.evidenceSha256,
    planSha256: readPlan.planSha256,
    aggregateEstimatedNanoUsd,
    maximumEstimatedCostUsd: maximumCostUsd,
    shards: Object.freeze(shards),
  });
}
